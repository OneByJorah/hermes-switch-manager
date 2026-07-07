"""Configuration management endpoints.

List, view, diff, and compare configuration backups.
"""
import difflib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import ConfigBackup, ConfigDiff, Switch, AuditLog
from schemas import ConfigBackupOut, ConfigDiffOut

router = APIRouter(prefix="/api/configs", tags=["configs"])


@router.get("/", response_model=list[ConfigBackupOut])
def list_configs(switch_id: int = None, limit: int = 50, db: Session = Depends(get_db)):
    """List configuration backups, optionally filtered by switch."""
    query = db.query(ConfigBackup)
    if switch_id:
        query = query.filter_by(switch_id=switch_id)
    return query.order_by(desc(ConfigBackup.created_at)).limit(limit).all()


@router.get("/{backup_id}", response_model=ConfigBackupOut)
def get_config(backup_id: int, db: Session = Depends(get_db)):
    """Get a specific config backup by ID."""
    backup = db.query(ConfigBackup).filter_by(id=backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Config backup not found")
    return backup


@router.get("/{switch_id}/latest")
def get_latest_config(switch_id: int, db: Session = Depends(get_db)):
    """Get the most recent config backup for a switch."""
    sw = db.query(Switch).filter_by(id=switch_id).first()
    if not sw:
        raise HTTPException(status_code=404, detail="Switch not found")
    backup = db.query(ConfigBackup).filter_by(switch_id=switch_id)\
        .order_by(desc(ConfigBackup.created_at)).first()
    if not backup:
        return {"switch_id": switch_id, "hostname": sw.hostname, "config": None, "timestamp": None}
    return {
        "switch_id": switch_id,
        "hostname": sw.hostname,
        "config": backup.running_config,
        "config_hash": backup.config_hash,
        "backup_id": backup.id,
        "config_type": backup.config_type,
        "timestamp": str(backup.created_at),
    }


@router.post("/diff")
def diff_configs(backup_id_a: int, backup_id_b: int, db: Session = Depends(get_db)):
    """Generate a unified diff between two config backups."""
    ba = db.query(ConfigBackup).filter_by(id=backup_id_a).first()
    bb = db.query(ConfigBackup).filter_by(id=backup_id_b).first()

    if not ba or not bb:
        raise HTTPException(status_code=404, detail="One or both backups not found")
    if ba.switch_id != bb.switch_id:
        raise HTTPException(status_code=400, detail="Backups must be from the same switch")

    diff_lines = list(difflib.unified_diff(
        ba.running_config.splitlines(keepends=True),
        bb.running_config.splitlines(keepends=True),
        fromfile=f"Backup #{ba.id} ({ba.created_at})",
        tofile=f"Backup #{bb.id} ({bb.created_at})"
    ))
    diff_content = "".join(diff_lines)

    # Save diff
    config_diff = ConfigDiff(
        switch_id=ba.switch_id,
        from_backup_id=backup_id_a,
        to_backup_id=backup_id_b,
        diff_content=diff_content,
        summary=f"Diff between backup #{backup_id_a} and #{backup_id_b}",
    )
    db.add(config_diff)
    db.commit()
    db.refresh(config_diff)

    db.add(AuditLog(
        action="config_diff", actor="api",
        target_type="config", target_id=config_diff.id,
        status="success", details={"backup_a": backup_id_a, "backup_b": backup_id_b}
    ))
    db.commit()

    return {
        "diff_id": config_diff.id,
        "switch_id": ba.switch_id,
        "diff": diff_content,
        "additions": sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++")),
        "deletions": sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---")),
    }


@router.get("/diffs/list", response_model=list[ConfigDiffOut])
def list_diffs(switch_id: int = None, limit: int = 20, db: Session = Depends(get_db)):
    """List config diffs."""
    query = db.query(ConfigDiff)
    if switch_id:
        query = query.filter_by(switch_id=switch_id)
    return query.order_by(desc(ConfigDiff.created_at)).limit(limit).all()


@router.get("/diffs/{diff_id}")
def get_diff(diff_id: int, db: Session = Depends(get_db)):
    """Get a specific config diff."""
    diff = db.query(ConfigDiff).filter_by(id=diff_id).first()
    if not diff:
        raise HTTPException(status_code=404, detail="Diff not found")
    return diff
