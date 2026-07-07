"""Security audit endpoints.

CVE scanning, ACL/AAA audits, compliance checks, and finding management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import SecurityFinding, AuditLog
from schemas import SecurityFindingOut, SecurityFindingUpdate
from services.security_auditor import audit_switch, audit_all_switches, resolve_finding

router = APIRouter(prefix="/api/security", tags=["security"])


@router.get("/findings", response_model=list[SecurityFindingOut])
def list_findings(
    switch_id: Optional[int] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    finding_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List security findings with optional filters."""
    query = db.query(SecurityFinding)
    if switch_id:
        query = query.filter_by(switch_id=switch_id)
    if severity:
        query = query.filter_by(severity=severity)
    if status:
        query = query.filter_by(status=status)
    if finding_type:
        query = query.filter_by(finding_type=finding_type)
    return query.order_by(SecurityFinding.created_at.desc()).limit(100).all()


@router.get("/findings/stats")
def get_finding_stats(db: Session = Depends(get_db)):
    """Get aggregate stats for security findings."""
    from sqlalchemy import func
    total = db.query(SecurityFinding).count()
    by_severity = db.query(SecurityFinding.severity, func.count(SecurityFinding.id))\
        .group_by(SecurityFinding.severity).all()
    by_status = db.query(SecurityFinding.status, func.count(SecurityFinding.id))\
        .group_by(SecurityFinding.status).all()
    by_type = db.query(SecurityFinding.finding_type, func.count(SecurityFinding.id))\
        .group_by(SecurityFinding.finding_type).all()
    return {
        "total": total,
        "by_severity": {s: c for s, c in by_severity},
        "by_status": {s: c for s, c in by_status},
        "by_type": {t: c for t, c in by_type},
    }


@router.post("/audit/{switch_id}")
def run_audit(switch_id: int, db: Session = Depends(get_db)):
    """Run a comprehensive security audit on a single switch."""
    result = audit_switch(switch_id, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/audit-all")
def run_audit_all(db: Session = Depends(get_db)):
    """Run security audit on all online switches."""
    return audit_all_switches(db)


@router.put("/findings/{finding_id}")
def update_finding(finding_id: int, data: SecurityFindingUpdate, db: Session = Depends(get_db)):
    """Resolve or mark a finding as false positive."""
    result = resolve_finding(finding_id, data.status, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/checks")
def list_available_checks():
    """List all available security checks."""
    return {
        "checks": [
            {"id": "aaa_config", "name": "AAA Configuration", "severity": "high",
             "description": "Checks if AAA is enabled and properly configured"},
            {"id": "insecure_protocols", "name": "Insecure Protocols", "severity": "high",
             "description": "Checks for Telnet, HTTP, SNMPv1/v2c, TFTP"},
            {"id": "password_policy", "name": "Password Policy", "severity": "medium",
             "description": "Checks password encryption and minimum length"},
            {"id": "acl_review", "name": "ACL Review", "severity": "low",
             "description": "Reviews ACLs for missing deny-all and excessive entries"},
            {"id": "compliance", "name": "Compliance Checks", "severity": "medium",
             "description": "Checks logging, NTP, DNS, SSH version"},
            {"id": "cve_scan", "name": "CVE Scan", "severity": "critical",
             "description": "Scans OS version against known CVE database"},
        ]
    }
