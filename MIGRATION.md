# Migration Notice

## Consolidated from nethermind

This repository has been consolidated with **nethermind** (previously a separate network switch management platform). All unique features from nethermind have been merged into hermes-switch-manager:

### Features Merged

| Feature | Source | Description |
|---------|--------|-------------|
| Serial Console Support | nethermind | Out-of-band management via RS-232/USB serial |
| Jinja2 Template Engine | nethermind | 8 built-in config templates (HP ArubaOS-Switch) |
| Template CRUD | nethermind | Create, render, and apply configuration templates |

### New Services

- `serial_client.py` - Serial console client for out-of-band management
- `template_engine.py` - Jinja2-based configuration template engine

### Template Categories (8 built-in)

| Category | Count |
|----------|-------|
| Initial Setup | 1 |
| VLAN | 1 |
| Interfaces | 2 |
| Security | 2 |
| Routing | 1 |
| Maintenance | 1 |

All built-in templates target HP ArubaOS-Switch. The engine itself is vendor-agnostic.

### Deprecated Repository

The `nethermind` repository is now deprecated. All development continues in this repository.
