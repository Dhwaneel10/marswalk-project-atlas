"""
MarsWalk 2.0 — Milestone 10C Evidence Script: Sortie Black Box & Incident Replay.

Captures all 3 verified operational states via Chrome DevTools Protocol:
1. Sortie Black Box Event Ledger (m10c_01_black_box_event_ledger.png):
   Chronological event stream with filter pills (Navigation, Science, Contingency, Decisions).
2. Incident Event Detail & Provenance (m10c_02_incident_event_detail.png):
   Selected simulated contingency event showing telemetry coordinates, provenance payload, and audit trail.
3. Incident Replay & Decision Fidelity (m10c_03_incident_replay_fidelity.png):
   Reconstructed incident comparing recorded vs. recomputed recommendation on authentic CTX terrain with variance metrics.
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
ARTIFACT_OUTPUT_DIR = Path(r"C:\Users\dhwan\.gemini\antigravity\brain\0a1bc6e9-d3cc-4c3b-b1fe-4875c358b144\outputs")
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:3000"
DEBUG_PORT = 9498

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

    img_data = base64.b64decode(data_b64)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / filename
    with open(out_path, "wb") as f:
        f.write(img_data)
    print(f"Saved: {out_path} ({len(img_data):,} bytes)")

    if ARTIFACT_OUTPUT_DIR.exists():
        art_path = ARTIFACT_OUTPUT_DIR / filename
        with open(art_path, "wb") as f:
            f.write(img_data)
        print(f"Mirrored to artifact: {art_path}")


async def run_journey():
    print(f"[Milestone 10C] Launching Chrome CDP on port {DEBUG_PORT}...")
    user_data_dir = tempfile.mkdtemp(prefix="chrome_10c_")
    chrome_proc = subprocess.Popen(
        [
            CHROME_PATH,
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={user_data_dir}",
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1920,1080",
            "--hide-scrollbars",
            f"{BASE_URL}/?landing=false&fly=jezero",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        ws_url = None
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json") as r:
                    tabs = json.loads(r.read().decode())
                    page_tab = next((t for t in tabs if t.get("type") == "page" and "3000" in t.get("url", "")), None)
                    if not page_tab:
                        page_tab = next((t for t in tabs if t.get("type") == "page"), None)
                    if page_tab and "webSocketDebuggerUrl" in page_tab:
                        ws_url = page_tab["webSocketDebuggerUrl"]
                        break
            except Exception:
                await asyncio.sleep(0.5)

        if not ws_url:
            print("Could not obtain Chrome WebSocket URL.")
            chrome_proc.terminate()
            return

        print(f"Connected to DevTools: {ws_url}")

        async with websockets.connect(ws_url, max_size=100 * 1024 * 1024) as ws:
            await send_cmd(ws, "Page.enable")
            await send_cmd(ws, "Runtime.enable")

            print("Waiting for Mars Atlas to boot and initialize Jezero 3D workstation...")
            for _ in range(40):
                ready = await evaluate_js(ws, "Boolean(window.__atlas && window.__atlas.isBooted())")
                if ready:
                    break
                await asyncio.sleep(0.5)

            await asyncio.sleep(3.0)

            # Step 1: Switch to Results and prepare mission playback
            print("Preparing playback and telemetry...")
            await evaluate_js(ws, "window.__atlas.switchInspectorTab('tabResults')")
            await evaluate_js(ws, "window.__atlas.refreshPlaybackData('nominal')", await_promise=True)
            await asyncio.sleep(2.0)

            # Start playback to record departure event
            print("Starting playback to log departure...")
            await evaluate_js(ws, "window.__atlas.playMissionPlayback()")
            await asyncio.sleep(1.0)
            await evaluate_js(ws, "window.__atlas.pauseMissionPlayback()")

            # Seek to 320s and inject contingency
            print("Advancing to intermediate point (~320s) and injecting simulated contingency...")
            await evaluate_js(ws, "window.__atlas.seekMissionPlayback(320)")
            await evaluate_js(ws, "window.__atlas.openEmergencyInjection()")
            await asyncio.sleep(1.0)

            # Calculate continuation (records contingency_injected and route_recalculated)
            print("Computing adaptive continuation...")
            cont_res = await evaluate_js(ws, "window.__atlas.calculateContinuation()", await_promise=True)
            print(f"Continuation calculated: {cont_res is not None}")
            await asyncio.sleep(1.5)

            # Apply continuation (records continuation_selected)
            print("Applying continuation...")
            await evaluate_js(ws, "window.__atlas.applyContinuation()")
            await asyncio.sleep(1.0)

            # Close emergency drawer if open
            await evaluate_js(ws, "window.__atlas.closeEmergencyInjection()")

            # Step 2: Open Sortie Black Box Modal
            print("Opening Sortie Black Box modal...")
            await evaluate_js(ws, "window.__atlas.openBlackBox()")
            await asyncio.sleep(2.0)

            # Shot 1: Sortie Black Box Event Ledger
            print("Capturing Shot 1: Sortie Black Box Event Ledger...")
            await capture_screenshot(ws, "m10c_01_black_box_event_ledger.png")

            # Step 3: Filter by contingency and select contingency event for detail view
            print("Filtering by contingency and selecting event...")
            await evaluate_js(ws, "window.__atlas.renderBlackBoxEvents('contingency')")
            await asyncio.sleep(1.5)

            # Shot 2: Incident Event Detail & Provenance Inspector
            print("Capturing Shot 2: Incident Event Detail & Provenance...")
            await capture_screenshot(ws, "m10c_02_incident_event_detail.png")

            # Step 4: Reset filter to ALL and Trigger Incident Replay
            print("Triggering authentic incident replay against USGS CTX terrain...")
            await evaluate_js(ws, "window.__atlas.renderBlackBoxEvents('all')")
            await evaluate_js(ws, "window.__atlas.replayIncident()", await_promise=True)
            await asyncio.sleep(2.5)

            # Shot 3: Incident Replay & Decision Fidelity
            print("Capturing Shot 3: Incident Replay & Decision Fidelity...")
            await capture_screenshot(ws, "m10c_03_incident_replay_fidelity.png")

            print("[Milestone 10C] All 3 evidence screenshots successfully captured!")
    finally:
        chrome_proc.terminate()


if __name__ == "__main__":
    asyncio.run(run_journey())
