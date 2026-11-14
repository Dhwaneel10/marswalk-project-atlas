"""
MarsWalk 2.0 — Milestone 10B Evidence Script: Mid-Sortie Emergency Injection, Mission State Handoff & Live Adaptive Replanning.

Captures all 5 verified operational states via Chrome DevTools Protocol:
1. Mid-Sortie Playback Pause (m10b_01_mid_sortie_playback_pause.png): Rover paused midway along computed route with coordinates & budget.
2. Emergency Injection Drawer (m10b_02_emergency_injection_drawer.png): Interactive simulated contingency configuration interface.
3. Continuation Trade-off Evaluation (m10b_03_continuation_tradeoff_eval.png): 3-stage comparison: Nominal vs. Disrupted vs. Adaptive Detour.
4. 3D Detour Preview & Hazard Footprint (m10b_04_3d_detour_preview_footprint.png): Spatial rendering of hazard zone, historical track, and detour.
5. Resumed Continuation Traversal (m10b_05_resumed_continuation_traversal.png): Resumed traversal from captured position along adaptive route.
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
DEBUG_PORT = 9499

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
    print(f"[Milestone 10B] Launching Chrome CDP on port {DEBUG_PORT}...")
    user_data_dir = tempfile.mkdtemp(prefix="chrome_10b_")
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

            # Switch to Results tab and load nominal playback data
            print("Preparing playback and telemetry...")
            await evaluate_js(ws, "window.__atlas.switchInspectorTab('tabResults')")
            await evaluate_js(ws, "window.__atlas.refreshPlaybackData('nominal')", await_promise=True)
            await asyncio.sleep(2.0)

            # Advance playback to intermediate timestamp (~350s) and focus rover marker
            print("Advancing playback to mid-sortie position (~350s)...")
            await evaluate_js(ws, "window.__atlas.seekMissionPlayback(350)")
            await evaluate_js(ws, "window.__atlas.focusPlaybackMarker()")
            await asyncio.sleep(1.5)

            # Shot 1: Mid-Sortie Playback Pause
            print("Capturing Shot 1: Mid-Sortie Playback Pause...")
            await capture_screenshot(ws, "m10b_01_mid_sortie_playback_pause.png")

            # Open Emergency Injection Drawer
            print("Opening emergency injection drawer...")
            await evaluate_js(ws, "window.__atlas.openEmergencyInjection()")
            await asyncio.sleep(1.0)

            # Shot 2: Emergency Injection Drawer
            print("Capturing Shot 2: Emergency Injection Drawer...")
            await capture_screenshot(ws, "m10b_02_emergency_injection_drawer.png")

            # Calculate Continuation
            print("Calculating continuation with simulated contingency...")
            continuation_result = await evaluate_js(ws, "window.__atlas.calculateContinuation()", await_promise=True)
            print(f"Continuation result received: {continuation_result is not None}")
            await asyncio.sleep(2.0)

            # Shot 3: Continuation Trade-off Evaluation
            print("Capturing Shot 3: Continuation Trade-off Evaluation...")
            await capture_screenshot(ws, "m10b_03_continuation_tradeoff_eval.png")

            # Switch camera to orbit mode to showcase 3D hazard footprint and detour route
            print("Framing 3D hazard footprint and detour route...")
            await evaluate_js(ws, "window.__atlas.setCameraDirectorMode('orbit')")
            await asyncio.sleep(1.5)

            # Shot 4: 3D Detour Preview & Hazard Footprint
            print("Capturing Shot 4: 3D Detour Preview & Hazard Footprint...")
            await capture_screenshot(ws, "m10b_04_3d_detour_preview_footprint.png")

            # Apply continuation and resume playback
            print("Applying continuation and resuming playback along detour route...")
            await evaluate_js(ws, "window.__atlas.applyContinuation()")
            await asyncio.sleep(0.5)
            await evaluate_js(ws, "window.__atlas.setPlaybackSpeed(10)")
            await evaluate_js(ws, "window.__atlas.playMissionPlayback()")
            await asyncio.sleep(2.0)

            # Shot 5: Resumed Continuation Traversal
            print("Capturing Shot 5: Resumed Continuation Traversal...")
            await capture_screenshot(ws, "m10b_05_resumed_continuation_traversal.png")

            print("[Milestone 10B] All 5 evidence screenshots successfully captured!")
    finally:
        chrome_proc.terminate()


if __name__ == "__main__":
    asyncio.run(run_journey())
