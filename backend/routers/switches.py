"""Switch management endpoints.

CRUD operations for network switches, plus config backup and sync.
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Switch, AuditLog
from schemas import SwitchCreate, SwitchUpdate, SwitchOut
from services.netmiko_client import pull_running_config, check_health, execute_commands, bulk_backup_all

router = APIRouter(prefix="/api/switches", tags=["switches"])


@router.get("/", response_model=list[SwitchOut])
def list_switches(status: Optional[str] = None, vendor: Optional[str] = None, db: Session = Depends(get_db)):
    """List all switches with optional filtering."""
    query = db.query(Switch)
    if status:
        query = query.filter_by(status=status)
    if vendor:
        query = query.filter_by(vendor=vendor)
    return query.order_by(Switch.hostname).all()


@router.post("/", response_model=SwitchOut, status_code=201)
def add_switch(data: SwitchCreate, db: Session = Depends(get_db)):
    """Add a new switch to the inventory."""
    # Check for duplicate hostname
    existing = db.query(Switch).filter_by(hostname=data.hostname).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Switch with hostname '{data.hostname}' already exists")

    sw = Switch(
        hostname=data.hostname,
        ip_address=data.ip_address,
        vendor=data.vendor,
        device_type=data.device_type or data.vendor,
        ssh_port=data.ssh_port,
        ssh_username=data.ssh_username,
        ssh_password=data.ssh_password,
        location=data.location,
        tags=data.tags,
        notes=data.notes,
    )
    db.add(sw)
    db.commit()
    db.refresh(sw)

    db.add(AuditLog(
        action="switch_add", actor="api",
        target_type="switch", target_id=sw.id,
        status="success", details={"hostname": sw.hostname, "ip": sw.ip_address}
    ))
    db.commit()
    return sw


@router.get("/{switch_id}", response_model=SwitchOut)
def get_switch(switch_id: int, db: Session = Depends(get_db)):
    """Get details for a specific switch."""
    sw = db.query(Switch).filter_by(id=switch_id).first()
    if not sw:
        raise HTTPException(status_code=404, detail="Switch not found")
    return sw


@router.put("/{switch_id}", response_model=SwitchOut)
def update_switch(switch_id: int, data: SwitchUpdate, db: Session = Depends(get_db)):
    """Update switch attributes."""
    sw = db.query(Switch).filter_by(id=switch_id).first()
    if not sw:
        raise HTTPException(status_code=404, detail="Switch not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(sw, key, value)

    db.commit()
    db.refresh(sw)

    db.add(AuditLog(
        action="switch_update", actor="api",
        target_type="switch", target_id=switch_id,
        status="success", details={"updated_fields": list(update_data.keys())}
    ))
    db.commit()
    return sw


@router.delete("/{switch_id}")
def delete_switch(switch_id: int, db: Session = Depends(get_db)):
    """Remove a switch from the inventory."""
    sw = db.query(Switch).filter_by(id=switch_id).first()
    if not sw:
        raise HTTPException(status_code=404, detail="Switch not found")
    db.delete(sw)
    db.commit()

    db.add(AuditLog(
        action="switch_delete", actor="api",
        target_type="switch", target_id=switch_id,
        status="success", details={}
    ))
    db.commit()
    return {"message": "Switch deleted"}


@router.post("/{switch_id}/sync")
def sync_config(switch_id: int, bg: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger a live config backup via SSH for a switch."""
    sw = db.query(Switch).filter_by(id=switch_id).first()
    if not sw:
        raise HTTPException(status_code=404, detail="Switch not found")
    bg.add_task(pull_running_config, switch_id)
    return {"status": "sync_started", "hostname": sw.hostname, "message": "Config backup started in background"}


@router.post("/{switch_id}/health")
def health_check(switch_id: int, db: Session = Depends(get_db)):
    """Run a live health check on a switch (CPU, memory, interfaces)."""
    sw = db.query(Switch).filter_by(id=switch_id).first()
    if not sw:
        raise HTTPException(status_code=404, detail="Switch not found")
    return check_health(switch_id)


@router.post("/{switch_id}/commands")
def run_commands(switch_id: int, commands: list[str], db: Session = Depends(get_db)):
    """Execute read-only show commands on a switch."""
    sw = db.query(Switch).filter_by(id=switch_id).first()
    if not sw:
        raise HTTPException(status_code=404, detail="Switch not found")
    return execute_commands(switch_id, commands)


@router.post("/bulk-backup")
def bulk_backup(bg: BackgroundTasks):
    """Trigger config backup for all online switches."""
    bg.add_task(bulk_backup_all)
    return {"status": "bulk_backup_started", "message": "Backup started for all online switches"}
