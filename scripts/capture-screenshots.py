#!/usr/bin/env python3
"""Capture hermes-switch-manager screenshots using Playwright HTML mockups.

Usage:
    python scripts/capture-screenshots.py

Prerequisites:
    pip install playwright
    python -m playwright install chromium

Screenshots are saved to docs/screenshots/ for use in the README.
"""
from playwright.sync_api import sync_playwright
import time
import os

SCREENSHOT_DIR = os.environ.get("SCREENSHOT_DIR", "docs/screenshots")

DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hermes Switch Manager - Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #0f172a; color: #e2e8f0; height: 100vh; display: flex; }
        .sidebar { width: 260px; background: #1e293b; padding: 20px; border-right: 1px solid #334155; }
        .logo { font-size: 20px; font-weight: 700; color: #f59e0b; margin-bottom: 32px; }
        .logo span { color: #8b5cf6; }
        .nav-item { padding: 12px 16px; border-radius: 8px; margin-bottom: 4px; font-size: 14px; color: #94a3b8; }
        .nav-item.active { background: #f59e0b; color: #0f172a; font-weight: 600; }
        .main { flex: 1; padding: 24px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
        .header h1 { font-size: 24px; }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
        .stat-card { background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; }
        .stat-label { font-size: 12px; color: #94a3b8; text-transform: uppercase; margin-bottom: 8px; }
        .stat-value { font-size: 28px; font-weight: 700; }
        .stat-value.green { color: #10b981; }
        .stat-value.yellow { color: #f59e0b; }
        .stat-value.red { color: #ef4444; }
        .stat-value.blue { color: #3b82f6; }
        .recent-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }
        .card { background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; }
        .card-title { font-weight: 600; margin-bottom: 16px; font-size: 14px; }
        .switch-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #334155; }
        .switch-name { font-weight: 500; }
        .switch-ip { color: #94a3b8; font-size: 12px; }
        .status { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
        .status.online { background: #065f46; color: #10b981; }
        .status.offline { background: #7f1d1d; color: #ef4444; }
        .log-entry { font-size: 12px; color: #94a3b8; padding: 8px 0; border-bottom: 1px solid #334155; }
        .log-time { color: #64748b; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo">Hermes <span>Switch Manager</span></div>
        <div class="nav-item active">📊 Dashboard</div>
        <div class="nav-item">🔌 Switches</div>
        <div class="nav-item">📋 Configs</div>
        <div class="nav-item">🔧 Templates</div>
        <div class="nav-item">🔄 Workflows</div>
        <div class="nav-item">🔒 Security</div>
        <div class="nav-item">🤖 AI Chat</div>
    </div>
    <div class="main">
        <div class="header"><h1>Network Dashboard</h1></div>
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-label">Total Switches</div><div class="stat-value blue">12</div></div>
            <div class="stat-card"><div class="stat-label">Online</div><div class="stat-value green">10</div></div>
            <div class="stat-card"><div class="stat-label">Offline</div><div class="stat-value red">2</div></div>
            <div class="stat-card"><div class="stat-label">Config Backups</div><div class="stat-value yellow">847</div></div>
        </div>
        <div class="recent-grid">
            <div class="card">
                <div class="card-title">Recent Switches</div>
                <div class="switch-row"><div><div class="switch-name">core-sw-01</div><div class="switch-ip">10.0.0.1 • Cisco IOS</div></div><span class="status online">Online</span></div>
                <div class="switch-row"><div><div class="switch-name">dist-sw-02</div><div class="switch-ip">10.0.1.2 • HP ArubaOS</div></div><span class="status online">Online</span></div>
                <div class="switch-row"><div><div class="switch-name">lab-sw-04</div><div class="switch-ip">192.168.1.10 • Juniper</div></div><span class="status offline">Offline</span></div>
            </div>
            <div class="card">
                <div class="card-title">Recent Activity</div>
                <div class="log-entry"><span class="log-time">14:32</span> Config backup completed for core-sw-01</div>
                <div class="log-entry"><span class="log-time">14:28</span> Security audit passed for dist-sw-02</div>
                <div class="log-entry"><span class="log-time">13:50</span> Health check failed for lab-sw-04</div>
            </div>
        </div>
    </div>
</body></html>
"""

SWITCHES_HTML = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Hermes Switch Manager - Switches</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #0f172a; color: #e2e8f0; padding: 40px; }
        h1 { font-size: 24px; margin-bottom: 24px; }
        table { width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; }
        th { text-align: left; padding: 14px 16px; background: #334155; font-size: 12px; text-transform: uppercase; color: #94a3b8; }
        td { padding: 14px 16px; border-bottom: 1px solid #334155; font-size: 14px; }
        .hostname { font-weight: 600; }
        .vendor { color: #8b5cf6; font-size: 12px; }
        .status { padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; }
        .online { background: #065f46; color: #10b981; }
        .offline { background: #7f1d1d; color: #ef4444; }
    </style>
</head>
<body>
    <h1>🔌 Switch Inventory</h1>
    <table>
        <thead><tr><th>Hostname</th><th>IP Address</th><th>Vendor</th><th>Status</th><th>Last Backup</th></tr></thead>
        <tbody>
            <tr><td class="hostname">core-sw-01</td><td>10.0.0.1</td><td class="vendor">Cisco IOS</td><td><span class="status online">Online</span></td><td>2 hours ago</td></tr>
            <tr><td class="hostname">dist-sw-02</td><td>10.0.1.2</td><td class="vendor">HP ArubaOS</td><td><span class="status online">Online</span></td><td>5 hours ago</td></tr>
            <tr><td class="hostname">access-sw-03</td><td>10.0.2.3</td><td class="vendor">Cisco IOS</td><td><span class="status online">Online</span></td><td>1 day ago</td></tr>
            <tr><td class="hostname">lab-sw-04</td><td>192.168.1.10</td><td class="vendor">Juniper JunOS</td><td><span class="status offline">Offline</span></td><td>3 days ago</td></tr>
        </tbody>
    </table>
</body></html>
"""

CHAT_HTML = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Hermes Switch Manager - AI Chat</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #0f172a; color: #e2e8f0; height: 100vh; display: flex; flex-direction: column; }
        .header { padding: 16px 24px; border-bottom: 1px solid #334155; display: flex; align-items: center; gap: 12px; }
        .header h1 { font-size: 20px; }
        .ai-badge { background: #8b5cf6; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
        .messages { flex: 1; padding: 24px; overflow-y: auto; }
        .message { margin-bottom: 20px; display: flex; gap: 12px; }
        .avatar { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
        .avatar.ai { background: #8b5cf6; }
        .avatar.user { background: #f59e0b; }
        .content { flex: 1; line-height: 1.6; font-size: 14px; }
        .content pre { background: #1e293b; padding: 12px; border-radius: 8px; margin-top: 8px; font-size: 12px; }
        .input-area { padding: 20px 24px; border-top: 1px solid #334155; }
        .input-wrapper { display: flex; gap: 12px; background: #1e293b; border-radius: 12px; padding: 12px 16px; }
        .input-wrapper input { flex: 1; background: transparent; border: none; color: #e2e8f0; font-size: 14px; outline: none; }
        .send-btn { background: #f59e0b; color: #0f172a; border: none; width: 40px; height: 40px; border-radius: 8px; font-weight: 600; }
    </style>
</head>
<body>
    <div class="header"><h1>🤖 Network Assistant</h1><span class="ai-badge">Hermes AI</span></div>
    <div class="messages">
        <div class="message"><div class="avatar user">J</div><div class="content">Show me the status of all Cisco switches</div></div>
        <div class="message"><div class="avatar ai">🤖</div><div class="content">Here are your Cisco switches:<br><br><strong>core-sw-01</strong> (10.0.0.1) — ✅ Online, CPU: 45%<br><strong>access-sw-03</strong> (10.0.2.3) — ✅ Online, CPU: 28%<br><br>All Cisco switches are healthy.</div></div>
        <div class="message"><div class="avatar user">J</div><div class="content">Run a security audit on core-sw-01</div></div>
        <div class="message"><div class="avatar ai">🤖</div><div class="content">Running security audit...<br><pre>Audit: core-sw-01
✅ SSH v2 enabled
✅ AAA configured
⚠️  Telnet still enabled
✅ Password encryption enabled
Score: 85/100</pre></div></div>
    </div>
    <div class="input-area"><div class="input-wrapper"><input type="text" placeholder="Ask about your network..."><button class="send-btn">→</button></div></div>
</body></html>
"""

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def capture_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        for name, html in [("dashboard.png", DASHBOARD_HTML), ("switches.png", SWITCHES_HTML), ("chat.png", CHAT_HTML)]:
            print(f"Capturing {name}...")
            page.set_content(html)
            page.wait_for_load_state("networkidle")
            time.sleep(1)
            path = os.path.join(SCREENSHOT_DIR, name)
            page.screenshot(path=path, full_page=False)
            print(f"Saved: {path} ({os.path.getsize(path):,} bytes)")
        
        browser.close()
    print("\nAll screenshots captured successfully!")

if __name__ == "__main__":
    capture_screenshots()
