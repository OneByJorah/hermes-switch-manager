"""Containerlab topology integration.

Parses Containerlab topology files (.clab.yml) to discover lab devices,
extract management IPs, and populate the switch database automatically.

Inspired by: github.com/zerxen/AINetworkHelperForContainerLab
"""
import os
import json
import yaml
from typing import Optional
from pathlib import Path

from sqlalchemy.orm import Session
from models import Switch, ContainerlabTopology, AuditLog
from config import settings


def discover_clab_topologies() -> list[dict]:
    """Search for Containerlab topology files in common locations.

    Returns a list of parsed topology dictionaries.
    """
    search_paths = [
        settings.CLAB_DIR,
        "/etc/containerlab",
        os.path.expanduser("~/clab"),
        os.path.expanduser("~/containerlab"),
        os.getcwd(),
    ]

    topologies = []
    for base_path in search_paths:
        if not os.path.isdir(base_path):
            continue
        for root, dirs, files in os.walk(base_path):
            for f in files:
                if f.endswith(".clab.yml") or f.endswith(".clab.yaml"):
                    full_path = os.path.join(root, f)
                    try:
                        with open(full_path) as fh:
                            data = yaml.safe_load(fh)
                        if data and "name" in data and "topology" in data:
                            topology = parse_topology_yaml(full_path, data)
                            topologies.append(topology)
                    except Exception as e:
                        print(f"  ⚠ Error parsing {full_path}: {e}")
    return topologies


def parse_topology_yaml(file_path: str, data: dict) -> dict:
    """Parse a Containerlab topology definition into a structured format."""
    name = data.get("name", "unknown")
    topology = data.get("topology", {})
    nodes = topology.get("nodes", {}) if isinstance(topology, dict) else {}
    links = topology.get("links", []) if isinstance(topology, list) else topology.get("links", [])

    node_list = []
    for node_name, node_data in nodes.items():
        if isinstance(node_data, str):
            node_data = {"kind": node_data}
        kind = node_data.get("kind", "unknown")
        mgmt_ip = node_data.get("mgmt-ipv4", "")
        image = node_data.get("image", "")
        node_list.append({
            "name": node_name,
            "kind": kind,
            "mgmt_ip": mgmt_ip,
            "image": image,
            "type": node_data.get("type", ""),
            "group": node_data.get("group", ""),
            "labels": node_data.get("labels", {}),
        })

    # Parse links
    link_list = []
    for link in links:
        if isinstance(link, dict):
            endpoints = link.get("endpoints", [])
        else:
            endpoints = str(link).split(":")
        link_list.append({
            "endpoints": endpoints if isinstance(endpoints, list) else [str(link)]
        })

    return {
        "name": name,
        "file_path": file_path,
        "nodes": node_list,
        "links": link_list,
        "node_count": len(node_list),
        "link_count": len(link_list),
        "mgmt_network": topology.get("mgmt", {}).get("network", "") if isinstance(topology, dict) else "",
    }


def sync_topology_to_db(db: Session, topology_data: dict) -> dict:
    """Sync a parsed Containerlab topology into the switch database.

    Creates Switch entries for each node that has a management IP.
    """
    name = topology_data["name"]
    file_path = topology_data.get("file_path", "")

    # Check if topology already exists
    existing = db.query(ContainerlabTopology).filter_by(name=name).first()
    if existing:
        existing.topology_data = topology_data
        existing.last_synced_at = None  # will set after processing
        existing.node_count = topology_data["node_count"]
        existing.link_count = topology_data["link_count"]
        db.flush()
        topology_id = existing.id
    else:
        ct = ContainerlabTopology(
            name=name,
            topology_data=topology_data,
            file_path=file_path,
            node_count=topology_data["node_count"],
            link_count=topology_data["link_count"],
        )
        db.add(ct)
        db.flush()
        topology_id = ct.id

    # Create/update Switch entries
    switches_created = 0
    for node in topology_data["nodes"]:
        mgmt_ip = node.get("mgmt_ip", "")
        if not mgmt_ip:
            continue

        # Map Containerlab kinds to Netmiko device types
        kind = node.get("kind", "").lower()
        vendor_map = {
            "cisco_ios": "cisco_ios",
            "cisco_xr": "cisco_xr",
            "juniper_junos": "juniper_junos",
            "arista_eos": "arista_eos",
            "linux": "linux",
            "srl": "nokia_srl",
            "nokia_srl": "nokia_srl",
            "frr": "linux",
            "keysight": "linux",
        }
        vendor = vendor_map.get(kind, kind)

        # Check if switch already exists by hostname
        hostname = node["name"]
        existing_switch = db.query(Switch).filter_by(hostname=hostname).first()
        if existing_switch:
            existing_switch.ip_address = mgmt_ip
            existing_switch.vendor = vendor
            existing_switch.location = f"Containerlab: {name}"
        else:
            sw = Switch(
                hostname=hostname,
                ip_address=mgmt_ip,
                vendor=vendor,
                device_type=vendor,
                status="unknown",
                location=f"Containerlab: {name}",
                tags="containerlab,auto-discovered",
            )
            db.add(sw)
            switches_created += 1

    # Use python datetime
    from datetime import datetime
    ct = db.query(ContainerlabTopology).filter_by(id=topology_id).first()
    if ct:
        ct.last_synced_at = datetime.utcnow()

    db.commit()

    # Audit
    db.add(AuditLog(
        action="topology_synced", actor="containerlab_service",
        target_type="topology", target_id=topology_id,
        status="success",
        details={"name": name, "nodes": topology_data["node_count"], "switches_created": switches_created}
    ))
    db.commit()

    return {
        "topology_id": topology_id,
        "name": name,
        "nodes": topology_data["node_count"],
        "switches_created": switches_created,
    }


def scan_and_sync(db: Session) -> dict:
    """Scan for all Containerlab topologies and sync them into the database."""
    topologies = discover_clab_topologies()
    results = []
    for topo in topologies:
        result = sync_topology_to_db(db, topo)
        results.append(result)
    return {"topologies_found": len(topologies), "results": results}
