"""Containerlab integration endpoints.

Parse .clab.yml topology files, discover lab devices, and sync into the switch database.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import ContainerlabTopology
from schemas import ContainerlabTopologyOut
from services.containerlab_service import discover_clab_topologies, sync_topology_to_db, scan_and_sync

router = APIRouter(prefix="/api/containerlab", tags=["containerlab"])


@router.get("/topologies", response_model=list[ContainerlabTopologyOut])
def list_topologies(db: Session = Depends(get_db)):
    """List all synced Containerlab topologies."""
    return db.query(ContainerlabTopology).order_by(desc(ContainerlabTopology.created_at)).all()


@router.get("/topologies/{topology_id}", response_model=ContainerlabTopologyOut)
def get_topology(topology_id: int, db: Session = Depends(get_db)):
    """Get a specific Containerlab topology."""
    topo = db.query(ContainerlabTopology).filter_by(id=topology_id).first()
    if not topo:
        raise HTTPException(status_code=404, detail="Topology not found")
    return topo


@router.post("/scan")
def scan_topologies(db: Session = Depends(get_db)):
    """Scan for Containerlab topology files and import found devices."""
    result = scan_and_sync(db)
    return result


@router.post("/parse")
def parse_topology_file(file_path: str, db: Session = Depends(get_db)):
    """Parse a specific Containerlab topology file and sync devices."""
    import os
    import yaml

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(file_path) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse YAML: {e}")

    from services.containerlab_service import parse_topology_yaml
    topology = parse_topology_yaml(file_path, data)
    result = sync_topology_to_db(db, topology)
    return result


@router.delete("/topologies/{topology_id}")
def delete_topology(topology_id: int, db: Session = Depends(get_db)):
    """Delete a Containerlab topology record."""
    topo = db.query(ContainerlabTopology).filter_by(id=topology_id).first()
    if not topo:
        raise HTTPException(status_code=404, detail="Topology not found")
    db.delete(topo)
    db.commit()
    return {"message": "Topology deleted"}
