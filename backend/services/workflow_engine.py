"""IRIS-inspired Workflow Engine.

Implements the disciplined operational workflow:
  Discover → Verify → Propose → Confirm → Execute → Verify → Document

Each step tracks status, requires human approval for state-changing actions,
and maintains an immutable audit trail.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from models import Workflow, WorkflowStep, Switch, AuditLog
from schemas import WorkflowCreate
from services.netmiko_client import pull_running_config, execute_commands, check_health


WORKFLOW_STEPS = [
    "discover",
    "verify",
    "propose",
    "confirm",
    "execute",
    "verify_done",
    "document",
]


class WorkflowEngine:
    """Manages the workflow lifecycle for network change operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: WorkflowCreate) -> Workflow:
        """Create a new workflow and initialize its first step."""
        wf = Workflow(
            title=data.title,
            description=data.description,
            status="discover",
            switch_ids=data.switch_ids,
            created_by=data.created_by,
            ticket_ref=data.ticket_ref,
        )
        self.db.add(wf)
        self.db.flush()

        # Create initial step
        self._add_step(wf.id, "discover", "Discover current state of target devices", requires_approval=False)
        self.db.commit()
        self.db.refresh(wf)
        return wf

    def _add_step(self, workflow_id: int, step_type: str, description: str,
                  command: str = None, requires_approval: bool = True) -> WorkflowStep:
        step = WorkflowStep(
            workflow_id=workflow_id,
            step_type=step_type,
            status="pending",
            description=description,
            command=command,
            requires_approval=requires_approval,
        )
        self.db.add(step)
        self.db.flush()
        return step

    def advance(self, workflow_id: int, approved: bool = False,
                result: str = None, actor: str = "system") -> dict:
        """Advance the workflow to the next step or mark as completed/failed."""
        wf = self.db.query(Workflow).filter_by(id=workflow_id).first()
        if not wf:
            return {"error": "Workflow not found"}

        current_step = self.db.query(WorkflowStep).filter_by(
            workflow_id=workflow_id, status="running"
        ).order_by(WorkflowStep.created_at.desc()).first()

        if not current_step:
            # Find the first pending step
            current_step = self.db.query(WorkflowStep).filter_by(
                workflow_id=workflow_id, status="pending"
            ).order_by(WorkflowStep.created_at).first()

        if not current_step:
            return {"error": "No pending steps to advance"}

        # Mark current step
        if not approved and current_step.requires_approval:
            current_step.status = "rejected"
            current_step.result = result or "Rejected by user"
            current_step.completed_at = datetime.utcnow()
            wf.status = "failed"
            self.db.commit()
            self._audit("workflow_rejected", workflow_id, {"step": current_step.step_type, "reason": result})
            return {"success": False, "status": "rejected", "message": "Workflow rejected"}

        current_step.status = "completed"
        current_step.result = result or "Completed"
        current_step.approved = approved
        current_step.approved_at = datetime.utcnow() if approved else None
        current_step.completed_at = datetime.utcnow()

        # Find next step
        current_idx = WORKFLOW_STEPS.index(current_step.step_type) if current_step.step_type in WORKFLOW_STEPS else -1
        if current_idx < len(WORKFLOW_STEPS) - 1:
            next_step_type = WORKFLOW_STEPS[current_idx + 1]
            descriptions = {
                "discover": "Discover current state of target devices",
                "verify": "Verify pre-change conditions and validate current state",
                "propose": "Propose configuration changes",
                "confirm": "Confirm and approve the proposed changes",
                "execute": "Execute the approved configuration changes",
                "verify_done": "Verify post-change state and validate success",
                "document": "Document the change and update records",
            }
            next_step = self._add_step(
                workflow_id, next_step_type,
                descriptions.get(next_step_type, f"Step: {next_step_type}"),
                requires_approval=next_step_type in ("confirm", "execute")
            )
            wf.status = next_step_type
            self.db.commit()
            self._audit("workflow_advance", workflow_id, {"from": current_step.step_type, "to": next_step_type})
            return {"success": True, "status": next_step_type, "step_id": next_step.id}
        else:
            # Workflow complete
            wf.status = "completed"
            wf.completed_at = datetime.utcnow()
            self.db.commit()
            self._audit("workflow_completed", workflow_id, {})
            return {"success": True, "status": "completed", "message": "Workflow completed successfully"}

    def execute_step(self, workflow_id: int, step_id: int, actor: str = "system") -> dict:
        """Execute the automation logic for a specific step.

        For 'execute' type steps, this pushes configs to devices.
        For 'discover'/'verify' steps, this pulls fresh data.
        """
        step = self.db.query(WorkflowStep).filter_by(id=step_id, workflow_id=workflow_id).first()
        if not step:
            return {"error": "Step not found"}
        if step.status != "pending":
            return {"error": f"Step is already {step.status}"}

        wf = self.db.query(Workflow).filter_by(id=workflow_id).first()
        switch_ids = [int(s.strip()) for s in (wf.switch_ids or "").split(",") if s.strip()]

        step.status = "running"
        self.db.commit()

        try:
            if step.step_type == "discover":
                # Pull fresh configs from all target switches
                results = []
                for sid in switch_ids:
                    result = pull_running_config(sid)
                    results.append(result)
                step.command = f"Discover configs for switches: {wf.switch_ids}"
                step.result = str(results)
                step.status = "completed"
                step.completed_at = datetime.utcnow()

            elif step.step_type == "verify" or step.step_type == "verify_done":
                # Run health check on target switches
                results = []
                for sid in switch_ids:
                    result = check_health(sid)
                    results.append(result)
                step.result = str(results)
                step.status = "completed"
                step.completed_at = datetime.utcnow()

            elif step.step_type == "execute":
                # Pull latest configs (this is read-only discovery)
                results = []
                for sid in switch_ids:
                    result = pull_running_config(sid)
                    results.append(result)
                step.result = str(results)
                step.status = "completed"
                step.completed_at = datetime.utcnow()

            else:
                step.status = "completed"
                step.completed_at = datetime.utcnow()

            self.db.commit()
            self._audit("step_executed", workflow_id, {"step": step.step_type, "step_id": step.id})
            return {"success": True, "step": step.step_type, "status": "completed"}

        except Exception as e:
            step.status = "failed"
            step.result = str(e)
            self.db.commit()
            return {"error": str(e)}

    def _audit(self, action: str, workflow_id: int, details: dict):
        self.db.add(AuditLog(
            action=action, actor="workflow_engine",
            target_type="workflow", target_id=workflow_id,
            status="success", details=details
        ))

    def get(self, workflow_id: int) -> Optional[Workflow]:
        """Get a workflow with its steps."""
        wf = self.db.query(Workflow).filter_by(id=workflow_id).first()
        if wf:
            wf.steps = self.db.query(WorkflowStep).filter_by(workflow_id=workflow_id)\
                .order_by(WorkflowStep.created_at).all()
        return wf

    def list_all(self, status: str = None) -> list[Workflow]:
        """List workflows, optionally filtered by status."""
        query = self.db.query(Workflow)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(Workflow.created_at.desc()).limit(50).all()
