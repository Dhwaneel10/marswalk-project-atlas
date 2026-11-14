"""
MarsWalk 2.0 — Milestone 10H Evidence Capture:
V1 Release Candidate, Reproducible Setup & Demonstration Package.

Captures all 3 verified operational states via Chrome DevTools Protocol:
1. V1 Workstation Ready (m10h_01_v1_workstation_ready.png):
   Atlas 3D workstation displaying Jezero Crater 20m CTX DTM, baseline traverse,
   waypoint pins, and real-time telemetry HUD.
2. Mission Science Report Export (m10h_02_v1_science_report_export.png):
   Mission Science Report modal with HTML/JSON download actions, mobility metrics,
   and USGS CTX reproducibility manifest.
3. Decision Gate V1 Sign-Off (m10h_03_v1_decision_gate_signoff.png):
   Mission Readiness Decision Gate modal showing verified green score,
   4 category summary status cards, and actionable audit findings.
"""

import os
import sys
import time
import json
import base64
import tempfile
import subprocess
import urllib.request
import asyncio
from pathlib import Path
import websockets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"
# Optional artifact directory fallback
ARTIFACT_OUTPUT_DIR = Path(
    os.environ.get(
        "MARSWALK_ARTIFACT_DIR",
        r"C:\Users\dhwan\.gemini\antigravity\brain\0a1bc6e9-d3cc-4c3b-b1fe-4875c358b144\outputs"
    )
)
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:3000"
DEBUG_PORT = 9508

cmd_id = [1]


async def send_cmd(ws, method, params=None):
    cid = cmd_id[0]
    cmd_id[0] += 1
    payload = {"id": cid, "method": method}
    if params:
        payload["params"] = params
    await ws.send(json.dumps(payload))
    while True:
        raw = await ws.recv()
        data = json.loads(raw)
        if data.get("id") == cid:
            return data


async def evaluate_js(ws, expr, await_promise=False):
    params = {"expression": expr, "returnByValue": True}
    if await_promise:
        params["awaitPromise"] = True
    resp = await send_cmd(ws, "Runtime.evaluate", params)
    res_obj = resp.get("result", {})
    if "exceptionDetails" in res_obj:
        print(f"[JS EXCEPTION] {res_obj['exceptionDetails']}")
    return res_obj.get("result", {}).get("value")


async def capture_screenshot(ws, filename):
    params = {"format": "png"}
    resp = await send_cmd(ws, "Page.captureScreenshot", params)
    data_b64 = resp.get("result", {}).get("data", "")
    if not data_b64:
        print(f"Failed to capture {filename}")
        return

    raw_bytes = base64.b64decode(data_b64)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / filename
    with open(out_file, "wb") as f:
        f.write(raw_bytes)
    print(f"Saved: {out_file} ({len(raw_bytes):,} bytes)")

    if ARTIFACT_OUTPUT_DIR.exists():
        art_file = ARTIFACT_OUTPUT_DIR / filename
        with open(art_file, "wb") as f:
            f.write(raw_bytes)
        print(f"Mirrored artifact: {art_file}")


async def main():
    print("=== Milestone 10H Evidence Capture: V1 Release Candidate Sign-Off ===")

    # Check server
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=3) as r:
            print("Atlas server is online.")
    except Exception as e:
        print(f"Error connecting to Atlas: {e}")
        return

    user_data_dir = tempfile.mkdtemp(prefix="chrome_m10h_")
    chrome_proc = subprocess.Popen([
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={user_data_dir}",
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1440,900",
        f"{BASE_URL}/?landing=false&fly=jezero"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    ws_url = None
    for _ in range(30):
        await asyncio.sleep(0.5)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=2) as resp:
                tabs = json.loads(resp.read().decode())
                for t in tabs:
                    if t.get("type") == "page" and "webSocketDebuggerUrl" in t:
                        ws_url = t["webSocketDebuggerUrl"]
                        break
            if ws_url:
                break
        except Exception:
            pass

    if not ws_url:
        print("Failed to attach to Chrome debug port.")
        chrome_proc.terminate()
        return

    async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
        await send_cmd(ws, "Page.enable")
        await send_cmd(ws, "Runtime.enable")
        print("Connected to CDP. Waiting for Atlas app initialization...")
        for _ in range(30):
            ready = await evaluate_js(ws, "typeof window.__atlas !== 'undefined' && typeof window.__atlas.openReadiness === 'function'")
            if ready:
                print("Atlas workstation ready.")
                break
            await asyncio.sleep(1)

        # 1. Load Jezero Delta Scarp Survey mission
        print("Loading Jezero Delta Scarp Survey mission...")
        await evaluate_js(ws, """
            if (window.__atlas && window.__atlas.loadMission) {
                window.__atlas.loadMission('m_jezero_delta_scarp_surve_090607');
            } else {
                const sel = document.getElementById('savedMissionsSelect');
                if (sel) {
                    sel.value = 'm_jezero_delta_scarp_surve_090607';
                    sel.dispatchEvent(new Event('change'));
                }
            }
        """)
        await asyncio.sleep(3)

        # Calculate baseline route
        await evaluate_js(ws, """
            const planBtn = document.getElementById('btnCalculateRoute') || document.getElementById('btnPlanRoute');
            if (planBtn) planBtn.click();
        """)
        await asyncio.sleep(4)

        # Capture State 1: Workstation Overview
        print("[1/3] Capturing: m10h_01_v1_workstation_ready.png...")
        await capture_screenshot(ws, "m10h_01_v1_workstation_ready.png")

        # 2. Open Mission Science Report Modal
        print("Opening Mission Science Report modal...")
        await evaluate_js(ws, """
            if (window.__atlas && window.__atlas.openMissionReport) {
                window.__atlas.openMissionReport('m_jezero_delta_scarp_surve_090607');
            } else {
                const btnReport = document.getElementById('btnHeaderReport') || document.getElementById('btnShowReport');
                if (btnReport) btnReport.click();
            }
        """)
        await asyncio.sleep(3.0)

        # Capture State 2: Mission Science Report
        print("[2/3] Capturing: m10h_02_v1_science_report_export.png...")
        await capture_screenshot(ws, "m10h_02_v1_science_report_export.png")

        # Close report modal
        await evaluate_js(ws, """
            const closeBtn = document.querySelector('#missionReportModal .modal-close') || document.querySelector('.modal.active .modal-close');
            if (closeBtn) closeBtn.click();
        """)
        await asyncio.sleep(1.0)

        # 3. Open Decision Gate / Mission Readiness Modal
        print("Opening Mission Readiness & Decision Gate modal...")
        await evaluate_js(ws, """
            if (window.__atlas && window.__atlas.openReadiness) {
                window.__atlas.openReadiness('m_jezero_delta_scarp_surve_090607');
            } else {
                const btn = document.getElementById('btnHeaderReadiness');
                if (btn) btn.click();
            }
        """)
        await asyncio.sleep(4)

        # Capture State 3: Decision Gate Readiness Audit
        print("[3/3] Capturing: m10h_03_v1_decision_gate_signoff.png...")
        await capture_screenshot(ws, "m10h_03_v1_decision_gate_signoff.png")

        print("=== Milestone 10H Evidence Capture Complete ===")

    chrome_proc.terminate()


if __name__ == "__main__":
    asyncio.run(main())
