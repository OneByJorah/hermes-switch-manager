"""Security Auditing Service.

Performs automated security audits on network devices:
- CVE scanning (OS version checks against known vulnerabilities)
- ACL policy review (default deny, order, rule analysis)
- AAA configuration audits (authentication, authorization, accounting)
- Compliance checks (password policies, insecure protocols, management plane hardening)
- Best practice violations

Inspired by: NetClaw security auditing capabilities.
"""
import re
from typing import Optional
from sqlalchemy.orm import Session

from models import Switch, ConfigBackup, SecurityFinding, AuditLog
from services.netmiko_client import execute_commands


# Known vulnerable OS versions (simplified CVE database)
# In production, you'd integrate with NVD API or similar
KNOWN_CVES = {
    "cisco_ios": [
        {
            "cve_id": "CVE-2023-20198",
            "affected_versions": ["15.2", "16.1", "16.2", "16.3", "16.4", "16.5", "16.6", "16.7", "16.8", "16.9", "16.10", "16.11", "16.12",
                                  "17.1", "17.2", "17.3", "17.4", "17.5", "17.6", "17.7", "17.8", "17.9"],
            "title": "Cisco IOS XE Web UI Privilege Escalation Vulnerability",
            "description": "A vulnerability in the web UI feature of Cisco IOS XE Software could allow an unauthenticated, remote attacker to create an account with full privileges.",
            "remediation": "Upgrade to IOS XE 17.9.1a or later. Disable HTTP Server if not needed.",
            "severity": "critical",
        },
        {
            "cve_id": "CVE-2023-20273",
            "affected_versions": ["17.9", "17.10", "17.11", "17.12"],
            "title": "Cisco IOS XE Web UI Command Injection",
            "description": "A vulnerability in the web UI feature of Cisco IOS XE Software could allow an authenticated, remote attacker to inject commands.",
            "remediation": "Apply recommended Cisco patches. Disable HTTP Server if not needed.",
            "severity": "high",
        },
    ],
}


# Security checks to run on configs
def _check_aaa_config(config: str) -> list[dict]:
    """Check AAA configuration for best practices."""
    findings = []

    # Check if AAA is enabled
    if "aaa new-model" not in config:
        findings.append({
            "finding_type": "aaa_misconfig",
            "severity": "high",
            "title": "AAA new-model not configured",
            "description": "AAA (Authentication, Authorization, and Accounting) is not enabled on this device.",
            "remediation": "Configure 'aaa new-model' and set up authentication, authorization, and accounting.",
        })

    # Check for local login fallback
    if "aaa authentication login" in config:
        if "local" not in config.lower().split("aaa authentication")[1].split("\n")[0] if "aaa authentication" in config else "":
            findings.append({
                "finding_type": "aaa_misconfig",
                "severity": "medium",
                "title": "No local fallback for AAA authentication",
                "description": "AAA login authentication does not include a local fallback method. If the AAA server is unreachable, administrative access may be lost.",
                "remediation": "Add 'local' as a fallback method: e.g., 'aaa authentication login default group tacacs+ local'",
            })

    # Check for enable secret
    if "enable secret" not in config:
        findings.append({
            "finding_type": "aaa_misconfig",
            "severity": "critical",
            "title": "No enable secret configured",
            "description": "The device does not have an 'enable secret' configured, which is required for privileged mode access.",
            "remediation": "Configure 'enable secret <strong-password>' on the device.",
        })

    return findings


def _check_insecure_protocols(config: str) -> list[dict]:
    """Check for insecure protocols enabled on the device."""
    findings = []
    insecure_checks = [
        {"protocol": "Telnet", "pattern": r"^line vty.*\n(?:.*\n)*?\s*transport input telnet", "severity": "high",
         "remediation": "Disable telnet with 'transport input ssh' and use SSHv2 only."},
        {"protocol": "HTTP server", "pattern": r"^ip http server", "severity": "medium",
         "remediation": "Disable HTTP server with 'no ip http server'. Use HTTPS with 'ip http secure-server' if needed."},
        {"protocol": "SNMP v1/v2c", "pattern": r"^snmp-server.*community.*(?:public|private)", "severity": "high",
         "remediation": "Use SNMPv3 with authentication and encryption. Remove community strings."},
        {"protocol": "TFTP", "pattern": r"tftp-server", "severity": "low",
         "remediation": "Use SCP or SFTP instead of TFTP for file transfers."},
    ]

    for check in insecure_checks:
        if re.search(check["pattern"], config, re.MULTILINE):
            findings.append({
                "finding_type": "protocol_insecure",
                "severity": check["severity"],
                "title": f"Insecure protocol: {check['protocol']}",
                "description": f"{check['protocol']} is enabled on the device.",
                "remediation": check["remediation"],
            })

    return findings


def _check_password_policy(config: str) -> list[dict]:
    """Check password and credential policies."""
    findings = []

    # Check for weak service password encryption
    if "service password-encryption" not in config:
        findings.append({
            "finding_type": "password_weakness",
            "severity": "medium",
            "title": "Password encryption not enabled",
            "description": "Service password-encryption is not configured. Passwords will be stored in plaintext in the configuration.",
            "remediation": "Enable with 'service password-encryption' and consider migrating to 'enable secret' or type 8/9 passwords.",
        })

    # Check for minimum password length
    if "security passwords min-length" not in config:
        findings.append({
            "finding_type": "password_weakness",
            "severity": "medium",
            "title": "No minimum password length configured",
            "description": "A minimum password length has not been set on the device.",
            "remediation": "Configure 'security passwords min-length 8' to enforce minimum password length.",
        })

    return findings


def _check_acls(config: str) -> list[dict]:
    """Review ACL configurations for security issues."""
    findings = []
    acl_sections = re.findall(r"^ip access-list (?:extended|standard) (\S+).*?\n(.*?)(?=^ip access-list|\Z)", config, re.MULTILINE | re.DOTALL)

    for acl_name, acl_body in acl_sections:
        lines = acl_body.strip().splitlines()
        if not lines:
            continue

        # Check if ACL has a deny all at the end
        has_explicit_deny = any("deny any" in line or "deny ip any any" in line or "deny any any" in line for line in lines)

        # Check for any permit statements
        has_permit = any(line.strip().startswith(("permit", "remark")) for line in lines)

        if has_permit and not has_explicit_deny:
            findings.append({
                "finding_type": "acl_vulnerability",
                "severity": "low",
                "title": f"ACL '{acl_name}' missing explicit deny-all",
                "description": f"ACL '{acl_name}' has permit entries but no explicit 'deny any' at the end. While ACLs have an implicit deny, an explicit deny is a best practice for documentation and clarity.",
                "remediation": "Add 'deny any any' or 'deny ip any any' at the end of the ACL.",
            })

        # Check ACL line count
        entry_count = sum(1 for l in lines if l.strip().startswith(("permit", "deny")))
        if entry_count > 100:
            findings.append({
                "finding_type": "acl_vulnerability",
                "severity": "info",
                "title": f"ACL '{acl_name}' has {entry_count} entries",
                "description": f"ACL '{acl_name}' contains {entry_count} entries, which may impact performance and manageability.",
                "remediation": "Consider using object groups or refactoring the ACL to reduce entry count.",
            })

    return findings


def _check_compliance(config: str) -> list[dict]:
    """Check compliance with common benchmarks (CIS, NIST)."""
    findings = []

    # Check logging
    if "logging " not in config:
        findings.append({
            "finding_type": "compliance",
            "severity": "medium",
            "title": "No logging configured",
            "description": "The device does not have logging configured, making incident investigation difficult.",
            "remediation": "Configure logging: 'logging host <syslog-server>', 'logging trap informational'",
        })

    # Check NTP
    if "ntp server" not in config:
        findings.append({
            "finding_type": "compliance",
            "severity": "medium",
            "title": "No NTP configured",
            "description": "NTP is not configured. Inaccurate timestamps affect logging and certificate validation.",
            "remediation": "Configure NTP: 'ntp server <ntp-server-ip>'",
        })

    # Check DNS
    if "ip domain-lookup" in config and "ip name-server" not in config:
        findings.append({
            "finding_type": "compliance",
            "severity": "low",
            "title": "DNS lookup enabled but no DNS servers configured",
            "description": "DNS lookup is enabled but no name servers are configured, which may cause delays.",
            "remediation": "Configure DNS servers: 'ip name-server <dns-ip>' or disable 'no ip domain-lookup'",
        })

    # Check SSH version
    if "ip ssh version 2" not in config and "ip ssh version" in config:
        findings.append({
            "finding_type": "compliance",
            "severity": "high",
            "title": "SSH version 1 is enabled",
            "description": "SSH version 1 has known vulnerabilities. SSHv2 should be used.",
            "remediation": "Configure 'ip ssh version 2' to enforce SSHv2.",
        })

    return findings


def audit_switch(switch_id: int, db: Session) -> dict:
    """Run a comprehensive security audit on a single switch.

    Retrieves the latest running config and runs all security checks.
    Stores findings in the SecurityFinding model.
    """
    switch = db.query(Switch).filter_by(id=switch_id).first()
    if not switch:
        return {"error": "Switch not found"}

    # Get latest config
    backup = db.query(ConfigBackup).filter_by(switch_id=switch_id)\
        .order_by(ConfigBackup.created_at.desc()).first()
    if not backup:
        # Try to pull a fresh config
        from services.netmiko_client import pull_running_config
        result = pull_running_config(switch_id)
        if "error" in result:
            return {"error": f"Cannot audit without config: {result['error']}"}
        backup = db.query(ConfigBackup).filter_by(switch_id=switch_id)\
            .order_by(ConfigBackup.created_at.desc()).first()

    if not backup:
        return {"error": "No config available for audit"}

    config = backup.running_config
    all_findings = []

    # Run all checks
    all_findings.extend(_check_aaa_config(config))
    all_findings.extend(_check_insecure_protocols(config))
    all_findings.extend(_check_password_policy(config))
    all_findings.extend(_check_acls(config))
    all_findings.extend(_check_compliance(config))

    # Check for known CVEs based on OS version
    if switch.os_version and switch.vendor in KNOWN_CVES:
        for cve in KNOWN_CVES[switch.vendor]:
            for affected in cve["affected_versions"]:
                if affected in switch.os_version:
                    all_findings.append({
                        "finding_type": "cve",
                        "severity": cve["severity"],
                        "title": cve["title"],
                        "description": cve["description"],
                        "remediation": cve["remediation"],
                        "cve_id": cve["cve_id"],
                        "affected_component": f"OS {switch.os_version}",
                    })

    # Save findings
    findings_created = 0
    for finding_data in all_findings:
        finding = SecurityFinding(
            switch_id=switch_id,
            finding_type=finding_data["finding_type"],
            severity=finding_data["severity"],
            title=finding_data["title"],
            description=finding_data.get("description", ""),
            remediation=finding_data.get("remediation", ""),
            cve_id=finding_data.get("cve_id"),
            affected_component=finding_data.get("affected_component"),
            status="open",
        )
        db.add(finding)
        findings_created += 1

    db.commit()

    # Audit log
    db.add(AuditLog(
        action="security_audit", actor="security_auditor",
        target_type="switch", target_id=switch_id,
        status="success", details={"findings": findings_created}
    ))
    db.commit()

    return {
        "success": True,
        "switch_id": switch_id,
        "hostname": switch.hostname,
        "findings_created": findings_created,
        "critical": sum(1 for f in all_findings if f.get("severity") == "critical"),
        "high": sum(1 for f in all_findings if f.get("severity") == "high"),
        "medium": sum(1 for f in all_findings if f.get("severity") == "medium"),
        "low": sum(1 for f in all_findings if f.get("severity") == "low"),
    }


def audit_all_switches(db: Session) -> dict:
    """Run security audit on all switches."""
    switches = db.query(Switch).filter(Switch.status.in_(["online", "unknown"])).all()
    results = []
    for sw in switches:
        result = audit_switch(sw.id, db)
        results.append(result)
    return {"audited": len(results), "results": results}


def resolve_finding(finding_id: int, status: str, db: Session) -> dict:
    """Resolve or mark a security finding as false positive."""
    finding = db.query(SecurityFinding).filter_by(id=finding_id).first()
    if not finding:
        return {"error": "Finding not found"}
    finding.status = status
    if status == "resolved":
        from datetime import datetime
        finding.resolved_at = datetime.utcnow()
    db.commit()
    return {"success": True, "finding_id": finding_id, "status": status}
