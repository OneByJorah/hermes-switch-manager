# Migration Notice

## Consolidated from nethermind

This repository has been consolidated with **nethermind** (previously a separate network switch management platform). All unique features from nethermind have been merged into hermes-switch-manager:

### Features Merged

| Feature | Source | Description |
|---------|--------|-------------|
| Serial Console Support | nethermind | Out-of-band management via RS-232/USB serial |
| Jinja2 Template Engine | nethermind | 45+ built-in config templates for HP ArubaOS and Cisco IOS |
| Template CRUD | nethermind | Create, render, and apply configuration templates |

### New Services

- `serial_client.py` - Serial console client for out-of-band management
- `template_engine.py` - Jinja2-based configuration template engine

### Template Categories (45+ built-in)

| Category | Count | Vendors |
|----------|-------|---------|
| Initial Setup | 3 | Aruba |
| VLAN | 4 | Aruba, Cisco |
| Interfaces | 3 | Aruba, Cisco |
| Security | 5 | Aruba |
| Routing | 3 | Aruba |
| Monitoring | 4 | Aruba |
| Maintenance | 5 | Aruba, Cisco |
| ACLs | 3 | Aruba |
| STP | 2 | Aruba |
| Management | 4 | Aruba |
| PoE | 2 | Aruba |
| Stacking | 2 | Aruba |

### Deprecated Repository

The `nethermind` repository is now deprecated. All development continues in this repository.
