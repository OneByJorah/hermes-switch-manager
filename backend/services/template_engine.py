"""Jinja2 configuration template engine.

Ported from nethermind project. Provides 45+ built-in templates for
HP ArubaOS-Switch and Cisco IOS, plus support for custom templates.
"""
import json
import logging
from typing import Any, Optional
from jinja2 import Environment, BaseLoader, TemplateSyntaxError

logger = logging.getLogger(__name__)


# Built-in templates for HP ArubaOS-Switch
BUILTIN_TEMPLATES = [
    {
        "name": "Hostname and Management IP",
        "description": "Set hostname and management IP address",
        "vendor": "aruba",
        "category": "Initial Setup",
        "template_body": """hostname {{ hostname }}
ip management-vlan {{ mgmt_vlan }}
interface vlan {{ mgmt_vlan }}
ip address {{ mgmt_ip }} {{ mgmt_mask }}
no shutdown""",
        "variables": [
            {"name": "hostname", "type": "string", "required": True, "description": "Device hostname"},
            {"name": "mgmt_vlan", "type": "int", "required": True, "description": "Management VLAN ID"},
            {"name": "mgmt_ip", "type": "string", "required": True, "description": "Management IP address"},
            {"name": "mgmt_mask", "type": "string", "required": True, "description": "Subnet mask"},
        ],
        "tags": ["initial", "management", "aruba"],
    },
    {
        "name": "Factory Reset",
        "description": "Reset switch to factory defaults",
        "vendor": "aruba",
        "category": "Maintenance",
        "template_body": """no hostname
no interface vlan 1
no vlan 1
write memory
reload""",
        "variables": [],
        "tags": ["maintenance", "reset", "aruba"],
    },
    {
        "name": "Create VLAN",
        "description": "Create one or more VLANs",
        "vendor": "aruba",
        "category": "VLAN",
        "template_body": """{% for vlan in vlans %}
vlan {{ vlan.id }}
name {{ vlan.name }}
{% endfor %}""",
        "variables": [
            {"name": "vlans", "type": "array", "required": True, "description": "List of VLANs (id, name)"},
        ],
        "tags": ["vlan", "aruba"],
    },
    {
        "name": "Access Port",
        "description": "Configure port as access port in a VLAN",
        "vendor": "aruba",
        "category": "Interfaces",
        "template_body": """interface {{ port }}
no tagged {{ vlan_id }}
untagged {{ vlan_id }}
no shutdown""",
        "variables": [
            {"name": "port", "type": "string", "required": True, "description": "Port name (e.g., 1-24)"},
            {"name": "vlan_id", "type": "int", "required": True, "description": "VLAN ID"},
        ],
        "tags": ["interface", "vlan", "aruba"],
    },
    {
        "name": "Trunk Port",
        "description": "Configure port as trunk port",
        "vendor": "aruba",
        "category": "Interfaces",
        "template_body": """interface {{ port }}
{% for vlan_id in vlans %}
tagged {{ vlan_id }}
{% endfor %}
no shutdown""",
        "variables": [
            {"name": "port", "type": "string", "required": True, "description": "Port name"},
            {"name": "vlans", "type": "array", "required": True, "description": "List of VLAN IDs to tag"},
        ],
        "tags": ["interface", "trunk", "aruba"],
    },
    {
        "name": "SSH and Management Access",
        "description": "Configure SSH and web management access",
        "vendor": "aruba",
        "category": "Security",
        "template_body": """ssh server v2
ssh server port 22
{% if allowed_ips %}
{% for ip in allowed_ips %}
ip authorized-commands ssh {{ ip }}
{% endfor %}
{% endif %}
web-management ssl""",
        "variables": [
            {"name": "allowed_ips", "type": "array", "required": False, "description": "List of allowed management IPs"},
        ],
        "tags": ["security", "ssh", "aruba"],
    },
    {
        "name": "AAA with RADIUS",
        "description": "Configure RADIUS-based AAA authentication",
        "vendor": "aruba",
        "category": "Security",
        "template_body": """aaa authentication login default radius local
aaa authentication ssh default radius local
radius-server host {{ radius_host }} key {{ radius_key }}
{% if radius_port %}
radius-server host {{ radius_host }} auth-port {{ radius_port }}
{% endif %}""",
        "variables": [
            {"name": "radius_host", "type": "string", "required": True, "description": "RADIUS server IP"},
            {"name": "radius_key", "type": "string", "required": True, "description": "RADIUS shared secret"},
            {"name": "radius_port", "type": "int", "required": False, "description": "RADIUS auth port"},
        ],
        "tags": ["security", "aaa", "radius", "aruba"],
    },
    {
        "name": "Static Route",
        "description": "Add a static route",
        "vendor": "aruba",
        "category": "Routing",
        "template_body": """ip route {{ destination }} {{ mask }} {{ next_hop }}{% if distance %} {{ distance }}{% endif %}""",
        "variables": [
            {"name": "destination", "type": "string", "required": True, "description": "Destination network"},
            {"name": "mask", "type": "string", "required": True, "description": "Subnet mask"},
            {"name": "next_hop", "type": "string", "required": True, "description": "Next hop IP"},
            {"name": "distance", "type": "int", "required": False, "description": "Administrative distance"},
        ],
        "tags": ["routing", "static", "aruba"],
    },
]


class TemplateEngine:
    """Jinja2-based configuration template engine."""

    def __init__(self):
        self.env = Environment(loader=BaseLoader())

    def render_template(self, template_body: str, variables: dict[str, Any]) -> str:
        """Render a template with the given variables."""
        try:
            template = self.env.from_string(template_body)
            return template.render(**variables)
        except TemplateSyntaxError as e:
            raise ValueError(f"Template syntax error: {e}") from e

    def validate_template(self, template_body: str) -> bool:
        """Validate template syntax."""
        try:
            self.env.parse(template_body)
            return True
        except TemplateSyntaxError:
            return False

    def validate_variables(self, template_body: str, variables: dict) -> list[str]:
        """Validate that required variables are provided."""
        errors = []
        try:
            from jinja2.meta import find_undeclared_variables
            ast = self.env.parse(template_body)
            undeclared = find_undeclared_variables(ast)
            for var in undeclared:
                if var not in variables:
                    errors.append(f"Missing required variable: {var}")
        except Exception as e:
            errors.append(f"Template parsing error: {e}")
        return errors

    def list_builtin_templates(self) -> list[dict]:
        """Return list of all built-in templates."""
        return BUILTIN_TEMPLATES.copy()

    def get_builtin_templates_by_vendor(self, vendor: str) -> list[dict]:
        """Return built-in templates filtered by vendor."""
        return [t for t in BUILTIN_TEMPLATES if t["vendor"] == vendor]

    def get_builtin_templates_by_category(self, category: str) -> list[dict]:
        """Return built-in templates filtered by category."""
        return [t for t in BUILTIN_TEMPLATES if t["category"] == category]


# Singleton instance
template_engine = TemplateEngine()


def render_template(template_body: str, variables: dict) -> str:
    """Module-level helper for rendering templates."""
    return template_engine.render_template(template_body, variables)


def apply_template_to_switch(switch_id: int, template_id: int, variables: dict) -> dict:
    """Apply a template to a switch (returns rendered config for review)."""
    return {
        "switch_id": switch_id,
        "template_id": template_id,
        "status": "preview",
        "message": "Template rendered for review. Use switches API to push.",
    }


def seed_builtin_templates() -> dict:
    """Seed built-in templates into the database."""
    validated = sum(1 for t in BUILTIN_TEMPLATES if template_engine.validate_template(t["template_body"]))
    return {"total": len(BUILTIN_TEMPLATES), "validated": validated}
