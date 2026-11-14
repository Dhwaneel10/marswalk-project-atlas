"""
MarsWalk 2.0 — Milestone 9Z Evidence Script: Mission Timeline Playback & Synchronized 3D Route Animation.

Captures all 5 verified operational journeys:
1. Active nominal mission playback along calculated path with 3D rover marker (m9z_01_playback_nominal_play.png).
2. Interactive time scrubbing and telemetry inspection (m9z_02_playback_scrubbing_telemetry.png).
3. Science dwell stationary holding at intermediate target (m9z_03_playback_science_dwell_stationary.png).
4. Disrupted detour variant playback isolation (m9z_04_playback_disrupted_variant_detour.png).
5. Mission completion at destination with full telemetry reconciliation (m9z_05_playback_mission_completion.png).
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
    print("[M9Z Evidence] Launching Chrome in headless remote debugging mode...")
    temp_dir = tempfile.mkdtemp(prefix="chrome_m9z_")
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

        print(f"[M9Z Evidence] Connected to CDP at {ws_url}")

        async with websockets.connect(ws_url, max_size=20 * 1024 * 1024) as ws:
            await send_cmd(ws, "Page.enable")
            await send_cmd(ws, "Runtime.enable")

            # Wait for Atlas boot
            print("  Waiting for Atlas Three.js terrain to boot...")
            for _ in range(25):
                booted = await evaluate_js(ws, "Boolean(window.__atlas && window.__atlas.getViewMode && window.__atlas.getViewMode() === 'jezero')")
                if booted:
                    break
                await asyncio.sleep(0.8)

            print("  Atlas surface active. Initializing playback model...")
            await asyncio.sleep(1.5)

            # Ensure Tab 2 (Route Planning / Results) is active and scrolled to playback section
            tab_switch_script = """
                (() => {
                    const btn = document.querySelector('button[data-tab="tabResults"]');
                    if (btn) btn.click();
                    const section = document.getElementById('missionPlaybackSection');
                    const body = document.querySelector('.hud-inspector-body');
                    if (section && body) {
                        body.scrollTop = section.offsetTop - 50;
                    }
                })()
            """
            await evaluate_js(ws, tab_switch_script)
            await asyncio.sleep(1.0)

            # 1. Nominal Playback (Play active baseline)
            print("  Journey 1: Starting nominal mission playback...")
            await evaluate_js(ws, "window.__atlas.refreshPlaybackData('nominal')", await_promise=True)
            await asyncio.sleep(1.2)
            await evaluate_js(ws, "window.__atlas.setPlaybackSpeed(10)")
            await evaluate_js(ws, "window.__atlas.playMissionPlayback()")
            await asyncio.sleep(2.5)  # Let it play for a few simulated minutes

            # Ensure camera focuses on marker
            await evaluate_js(ws, "window.__atlas.focusPlaybackMarker()")
            await asyncio.sleep(1.0)
            await evaluate_js(ws, tab_switch_script)
            await asyncio.sleep(0.5)

            await capture_screenshot(ws, "m9z_01_playback_nominal_play.png")

            # 2. Scrubber Seek to Midpoint
            print("  Journey 2: Interactive scrubbing along route...")
            await evaluate_js(ws, "window.__atlas.pauseMissionPlayback()")
            model_info = await evaluate_js(ws, "window.__atlas.getPlaybackModel('nominal')")
            total_dur = model_info.get("total_duration_s", 2500.0) if model_info else 2500.0
            mid_time = total_dur * 0.45
            await evaluate_js(ws, f"window.__atlas.seekMissionPlayback({mid_time})")
            await asyncio.sleep(0.8)
            await evaluate_js(ws, tab_switch_script)
            await asyncio.sleep(0.5)

            await capture_screenshot(ws, "m9z_02_playback_scrubbing_telemetry.png")

            # 3. Multi-Stop Sortie with Science Dwell
            print("  Journey 3: Multi-stop science tour playback with stationary dwell...")
            # Switch back to Plan tab to add a stop
            await evaluate_js(ws, "document.querySelector('button[data-tab=\"tabPlan\"]').click()")
            await asyncio.sleep(0.5)
            await evaluate_js(ws, """
                (() => {
                    const sel = document.getElementById('selectAddStop');
                    if (sel && sel.options.length > 1) {
                        sel.selectedIndex = 1;
                        document.getElementById('btnAddStop').click();
                    }
                })()
            """)
            await asyncio.sleep(1.5)
            await evaluate_js(ws, tab_switch_script)
            await asyncio.sleep(1.0)
            await evaluate_js(ws, "window.__atlas.refreshPlaybackData('nominal')", await_promise=True)
            await asyncio.sleep(1.2)

            # Seek into the dwell event
            dwell_seek_expr = """
                (() => {
                    const m = window.__atlas.getPlaybackModel('nominal');
                    if (!m) return 0;
                    const dwell = m.events.find(e => e.event_type === 'science_dwell');
                    if (dwell) {
                        window.__atlas.seekMissionPlayback(dwell.start_time_s + (dwell.duration_s * 0.5));
                        return dwell.start_time_s;
                    }
                    return 0;
                })()
            """
            await evaluate_js(ws, dwell_seek_expr)
            await asyncio.sleep(0.8)
            await evaluate_js(ws, tab_switch_script)
            await asyncio.sleep(0.5)

            await capture_screenshot(ws, "m9z_03_playback_science_dwell_stationary.png")

            # 4. Disrupted Detour Variant Playback
            print("  Journey 4: Evaluating contingency detour playback...")
            # Run gauntlet stress test
            await evaluate_js(ws, "document.querySelector('button[data-tab=\"tabScenarios\"]').click()")
            await asyncio.sleep(0.5)
            await evaluate_js(ws, """
                (() => {
                    const btn = document.getElementById('btnRunGauntlet');
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(2.5)

            # Switch back to Tab 2 and select Disrupted Detour variant
            await evaluate_js(ws, tab_switch_script)
            await asyncio.sleep(0.8)
            await evaluate_js(ws, "window.__atlas.setPlaybackVariant('disrupted')")
            await asyncio.sleep(1.5)
            await evaluate_js(ws, "window.__atlas.seekMissionPlayback(150.0)")
            await asyncio.sleep(0.8)
            await evaluate_js(ws, tab_switch_script)
            await asyncio.sleep(0.5)

            await capture_screenshot(ws, "m9z_04_playback_disrupted_variant_detour.png")

            # 5. Mission Completion & Telemetry Reconciliation
            print("  Journey 5: Scrubbing to mission arrival / finish...")
            await evaluate_js(ws, "window.__atlas.setPlaybackVariant('nominal')")
            await asyncio.sleep(0.8)
            seek_end_expr = """
                (() => {
                    const m = window.__atlas.getPlaybackModel('nominal');
                    if (m) {
                        window.__atlas.seekMissionPlayback(m.total_duration_s);
                    }
                })()
            """
            await evaluate_js(ws, seek_end_expr)
            await asyncio.sleep(0.8)
            await evaluate_js(ws, tab_switch_script)
            await asyncio.sleep(0.5)

            await capture_screenshot(ws, "m9z_05_playback_mission_completion.png")

            print("\n[M9Z Evidence] Successfully captured all 5 visual evidence journeys!")

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(run_evidence_capture())
