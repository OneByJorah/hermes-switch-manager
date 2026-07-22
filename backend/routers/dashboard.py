"""Dashboard and monitoring endpoints.

Returns aggregate stats, device metrics, and audit log views.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional

from database import get_db
from models import Switch, ConfigBackup, SecurityFinding, Workflow, AuditLog, DeviceMetric, ContainerlabTopology
from schemas import DashboardStats, DeviceMetricOut, AuditLogOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get aggregate dashboard statistics."""
    return DashboardStats(
        total_switches=db.query(Switch).count(),
        online_switches=db.query(Switch).filter_by(status="online").count(),
        offline_switches=db.query(Switch).filter_by(status="offline").count(),
        total_configs=db.query(ConfigBackup).count(),
        open_security_findings=db.query(SecurityFinding).filter_by(status="open").count(),
        active_workflows=db.query(Workflow).filter(
            ~Workflow.status.in_(["completed", "failed"])
        ).count(),
        total_topologies=db.query(ContainerlabTopology).count(),
    )


@router.get("/metrics/{switch_id}", response_model=list[DeviceMetricOut])
def get_device_metrics(switch_id: int, limit: int = 100, db: Session = Depends(get_db)):
    """Get recent metrics for a specific switch."""
    return db.query(DeviceMetric).filter_by(switch_id=switch_id)\
        .order_by(desc(DeviceMetric.recorded_at)).limit(limit).all()


@router.get("/audit-log", response_model=list[AuditLogOut])
def get_audit_logs(limit: int = 50, action: str = None, target_type: str = None, db: Session = Depends(get_db)):
    """Get recent audit log entries."""
    query = db.query(AuditLog)
    if action:
        query = query.filter_by(action=action)
    if target_type:
        query = query.filter_by(target_type=target_type)
    return query.order_by(desc(AuditLog.created_at)).limit(limit).all()


@router.get("/health-summary")
def get_health_summary(db: Session = Depends(get_db)):
    """Get a health summary across all devices."""
    switches = db.query(Switch).all()
    summary = []
    for sw in switches:
        recent_metric = db.query(DeviceMetric).filter_by(switch_id=sw.id)\
            .order_by(desc(DeviceMetric.recorded_at)).first()
        findings_count = db.query(SecurityFinding).filter_by(
            switch_id=sw.id, status="open"
        ).count()
        summary.append({
            "switch_id": sw.id,
            "hostname": sw.hostname,
            "ip_address": sw.ip_address,
            "status": sw.status,
            "vendor": sw.vendor,
            "cpu_usage": recent_metric.cpu_usage if recent_metric else None,
            "memory_usage": recent_metric.memory_usage if recent_metric else None,
            "interfaces_up": recent_metric.interfaces_up if recent_metric else None,
            "interfaces_down": recent_metric.interfaces_down if recent_metric else None,
            "open_findings": findings_count,
            "last_updated": str(recent_metric.recorded_at) if recent_metric else None,
        })
    return summary
