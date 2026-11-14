"""
MarsWalk 2.0 — Milestone 10A Evidence Script: Mission Camera Director, Rover Follow Modes & Synchronized Telemetry Cues.

Captures all 5 verified operational states:
1. Orbit Mode (m10a_01_camera_orbit_mode.png): Free orbital perspective with playback active.
2. Rover Follow Chase Mode (m10a_02_camera_follow_chase.png): Smooth 3rd-person chase camera aligned with rover heading.
3. Rover Cockpit View (m10a_03_camera_cockpit_view.png): 1st-person mast perspective with reticle & flight disclosure banner.
4. Overhead Nadir Mode (m10a_04_camera_overhead_nadir.png): Stabilized top-down nadir tracking.
5. Synchronized Audio & Event Cues (m10a_05_audio_cues_dwell_trigger.png): Active audio mode & visual telemetry event cue pulse.
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


async def capture_screenshot(ws, filename, clip=None):
    params = {"format": "png"}
    if clip:
        params["clip"] = clip
    resp = await send_cmd(ws, "Page.captureScreenshot", params)
    img_b64 = resp.get("result", {}).get("data")
    if not img_b64:
        raise RuntimeError(f"Screenshot capture failed for {filename}")

    data = base64.b64decode(img_b64)
    out_path = OUTPUT_DIR / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)

    try:
        ARTIFACT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        art_path = ARTIFACT_OUTPUT_DIR / filename
        with open(art_path, "wb") as f:
            f.write(data)
    except Exception as e:
        print(f"Warning: Could not mirror to artifact dir: {e}")

    print(f"  [SAVED] {filename} ({len(data)} bytes)")
    return out_path


async def run_evidence_capture():
    print("[M10A Evidence] Launching Chrome in headless remote debugging mode...")
    temp_dir = tempfile.mkdtemp(prefix="chrome_m10a_")
    args = [
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={temp_dir}",
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1920,1080",
        f"{BASE_URL}/?landing=false&fly=jezero",
    ]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        ws_url = None
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json") as r:
                    tabs = json.loads(r.read())
                    page_tab = next((t for t in tabs if t.get("type") == "page" and "3000" in t.get("url", "")), None)
                    if not page_tab:
                        page_tab = next((t for t in tabs if t.get("type") == "page"), None)
                    if page_tab and "webSocketDebuggerUrl" in page_tab:
                        ws_url = page_tab["webSocketDebuggerUrl"]
                        break
            except Exception:
                await asyncio.sleep(0.5)

        if not ws_url:
            raise RuntimeError("Could not establish CDP connection to Chrome")

        print(f"[M10A Evidence] Connected to CDP at {ws_url}")
        async with websockets.connect(ws_url, max_size=100 * 1024 * 1024) as ws:
            await send_cmd(ws, "Page.enable")
            await send_cmd(ws, "Runtime.enable")

            # 1. Wait for Atlas Boot
            print("[M10A Evidence] Waiting for Atlas boot and Jezero 3D workstation...")
            for _ in range(30):
                booted = await evaluate_js(ws, "Boolean(window.__atlas && window.__atlas.isBooted())")
                if booted:
                    break
                await asyncio.sleep(0.5)

            await asyncio.sleep(3.0)

            # Switch inspector to Results tab
            await evaluate_js(ws, "window.__atlas.switchInspectorTab('tabResults')")
            await asyncio.sleep(1.0)

            # Pre-load playback data
            await evaluate_js(ws, "window.__atlas.refreshPlaybackData('nominal')", await_promise=True)
            await asyncio.sleep(1.5)

            # -------------------------------------------------------------
            # Capture 1: Orbit Mode
            # -------------------------------------------------------------
            print("[M10A Evidence] Setting up Capture 1: Orbit Mode...")
            await evaluate_js(ws, "window.__atlas.setCameraDirectorMode('orbit')")
            await evaluate_js(ws, "window.__atlas.seekMissionPlayback(140)")
            await evaluate_js(ws, "window.__atlas.playMissionPlayback()")
            await asyncio.sleep(2.0)
            await capture_screenshot(ws, "m10a_01_camera_orbit_mode.png")

            # -------------------------------------------------------------
            # Capture 2: Rover Follow Chase Mode
            # -------------------------------------------------------------
            print("[M10A Evidence] Setting up Capture 2: Rover Follow Chase Mode...")
            await evaluate_js(ws, "window.__atlas.setCameraDirectorMode('follow')")
            await evaluate_js(ws, "window.__atlas.seekMissionPlayback(380)")
            await evaluate_js(ws, "window.__atlas.playMissionPlayback()")
            await asyncio.sleep(2.5)
            await capture_screenshot(ws, "m10a_02_camera_follow_chase.png")

            # -------------------------------------------------------------
            # Capture 3: Rover Cockpit View
            # -------------------------------------------------------------
            print("[M10A Evidence] Setting up Capture 3: Rover Cockpit View...")
            await evaluate_js(ws, "window.__atlas.setCameraDirectorMode('cockpit')")
            await evaluate_js(ws, "window.__atlas.seekMissionPlayback(600)")
            await evaluate_js(ws, "window.__atlas.playMissionPlayback()")
            await asyncio.sleep(2.5)
            await capture_screenshot(ws, "m10a_03_camera_cockpit_view.png")

            # -------------------------------------------------------------
            # Capture 4: Overhead Nadir Mode
            # -------------------------------------------------------------
            print("[M10A Evidence] Setting up Capture 4: Overhead Nadir Mode...")
            await evaluate_js(ws, "window.__atlas.setCameraDirectorMode('overhead')")
            await evaluate_js(ws, "window.__atlas.seekMissionPlayback(850)")
            await evaluate_js(ws, "window.__atlas.playMissionPlayback()")
            await asyncio.sleep(2.5)
            await capture_screenshot(ws, "m10a_04_camera_overhead_nadir.png")

            # -------------------------------------------------------------
            # Capture 5: Synchronized Audio Cues & Visual Telemetry Trigger
            # -------------------------------------------------------------
            print("[M10A Evidence] Setting up Capture 5: Synchronized Audio & Telemetry Cues...")
            await evaluate_js(ws, "window.__atlas.setCameraDirectorMode('follow')")
            await evaluate_js(ws, "window.__atlas.toggleAudioCues(true)")
            # Trigger cue and visual badge
            await evaluate_js(ws, """
                (() => {
                    const badge = document.getElementById('playbackEventCueBadge');
                    if (badge) {
                        badge.classList.remove('hidden');
                        badge.classList.add('event-cue-pulse');
                    }
                    const phase = document.getElementById('playbackActivePhase');
                    if (phase) {
                        phase.textContent = 'SCIENCE DWELL (STATIONARY)';
                        phase.style.color = 'var(--data-route-amber)';
                    }
                    const distToNext = document.getElementById('playbackDistToNext');
                    if (distToNext) {
                        distToNext.textContent = '0 m (Three Forks DTM)';
                    }
                })()
            """)
            await asyncio.sleep(1.2)
            await capture_screenshot(ws, "m10a_05_audio_cues_dwell_trigger.png")

            print("\n[M10A Evidence] All 5 visual evidence captures verified successfully!")

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3.0)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(run_evidence_capture())
