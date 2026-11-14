---
name: marswalk-browser-acceptance
description: >-
  Automates end-to-end browser verification of the MarsWalk 2.0 / Project Atlas frontend.
  Uses Chrome DevTools Protocol (CDP) to audit live UI state transitions, responsive layouts,
  cockpit HUD telemetry, timeline scrubbing, and captures visual screenshot evidence.
---

# MarsWalk Browser Acceptance Skill

## Purpose
Provide repeatable, automated browser acceptance testing for Project Atlas web interfaces via Chrome DevTools Protocol (CDP), validating that real UI elements, state machines, and visual components function correctly across desktop and laptop viewports.

## Core Directives & Guardrails
1. **Never Assume Code Equals Working UI:** An API test passing does not prove that DOM events, Three.js canvases, or CSS stylesheets render without defects. Always verify the live browser.
2. **Prevent Duplicate Daemon Servers:** Before launching an Atlas server instance, verify if port 3000 is already responding. Reuse active daemons whenever possible.
3. **Viewport Responsiveness Checks:** Test interfaces across both:
   - Full Desktop: $1920 \times 1080$
   - Compact Laptop: $1366 \times 768$
   - Ensure horizontal overflow is strictly `False` (`document.body.scrollWidth <= window.innerWidth`).
4. **Capture Visual Proof:** Always capture and save high-resolution PNG screenshots to `outputs/` for evidence packs and reviewer auditability.

## Standard CDP Automation Workflow (Python + websockets)

```python
import asyncio
import base64
import json
import subprocess
import tempfile
import urllib.request
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:3000"
DEBUG_PORT = 9497

async def audit_workflow():
    tmp_profile = tempfile.mkdtemp(prefix="chrome_audit_")
    proc = subprocess.Popen([
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={tmp_profile}",
        "--headless=new",
        "--disable-gpu",
        "--window-size=1920,1080",
        "about:blank",
    ])
    await asyncio.sleep(1.5)

    try:
        # Connect to CDP
        req = urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json/list")
        targets = json.loads(req.read().decode())
        ws_url = targets[0]["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url, max_size=25 * 1024 * 1024) as ws:
            # Send Page.navigate, evaluate expressions, assert state, capture screenshot
            pass
    finally:
        proc.terminate()
```

## Browser Acceptance Checklist
- [ ] Atlas server verified online on port 3000 without duplicate processes.
- [ ] `window.MarsWalk` object initialized cleanly without unhandled JavaScript exceptions.
- [ ] Inspector panels adopt `.cockpit-mode` when switching to wide analytical tabs.
- [ ] UI telemetry values match backend API payloads.
- [ ] Responsive layouts scale cleanly at $1920 \times 1080$ and $1366 \times 768$ with no horizontal overflow.
- [ ] Visual PNG screenshot captured and stored in `outputs/`.
