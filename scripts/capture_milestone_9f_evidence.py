"""
MarsWalk 2.0 - Milestone 9F Visual Evidence & Journey Automation Script
Executes Journeys A, B, C, D, and E in headless Chrome via Chrome DevTools Protocol (CDP),
capturing verified screenshots at 1366x768 and validating UI state.
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
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:3000"
DEBUG_PORT = 9450

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

async def evaluate_js(ws, expr):
    resp = await send_cmd(ws, "Runtime.evaluate", {"expression": expr, "returnByValue": True})
    return resp.get("result", {}).get("result", {}).get("value")

async def wait_for_condition(ws, expr, timeout_s=15.0, poll_interval=0.3):
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            val = await evaluate_js(ws, expr)
            if val:
                return True
        except Exception:
            pass
        await asyncio.sleep(poll_interval)
    return False

async def capture_screenshot(ws, filename):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / filename
    resp = await send_cmd(ws, "Page.captureScreenshot", {"format": "png"})
    b64_data = resp.get("result", {}).get("data", "")
    if b64_data:
        out_path.write_bytes(base64.b64decode(b64_data))
        print(f"[Evidence] Saved {filename} ({len(b64_data)//1024} KB)")
        return str(out_path)
    raise RuntimeError(f"Failed to capture screenshot: {filename}")

async def run_journeys():
    tmp_dir = tempfile.mkdtemp()
    proc = subprocess.Popen([
        CHROME_PATH,
        "--headless=new",
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={tmp_dir}",
        "--disable-gpu",
        "--window-size=1366,768",
        BASE_URL
    ])
    time.sleep(2.5)

    try:
        targets_raw = urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json").read().decode()
        targets = json.loads(targets_raw)
        page_target = next(t for t in targets if t.get("type") == "page" and "3000" in t.get("url", ""))
        
        async with websockets.connect(page_target["webSocketDebuggerUrl"], max_size=100*1024*1024) as ws:
            await send_cmd(ws, "Page.enable")
            await send_cmd(ws, "Runtime.enable")
            
            # -------------------------------------------------------------
            # JOURNEY A: Global Orbit View (Clean & Restrained)
            # -------------------------------------------------------------
            print("\n=== Executing Journey A: Global Orbit View ===")
            await send_cmd(ws, "Page.navigate", {"url": f"{BASE_URL}/"})
            
            ready = await wait_for_condition(ws, "(() => document.getElementById('loadingOverlay') && document.getElementById('loadingOverlay').classList.contains('hidden'))()", 15.0)
            assert ready, "Loading overlay did not hide"
            await asyncio.sleep(2.0)
            
            state_a = await evaluate_js(ws, """(() => ({
                layer: document.getElementById('telemetryLayer').textContent,
                elev: document.getElementById('telemetryElevStatus').textContent,
                inspectorHidden: document.getElementById('inspectorPanel').classList.contains('hidden'),
                diagHidden: document.getElementById('devDiagnosticsPanel').classList.contains('hidden'),
                waypointHidden: document.getElementById('waypointSelect').classList.contains('hidden')
            }))()""")
            print("Journey A State:", state_a)
            assert "Viking MDIM" in state_a["layer"] and "4.88" not in state_a["layer"], f"Invalid layer: {state_a['layer']}"
            assert "Global Datum" in state_a["elev"], f"Invalid elev: {state_a['elev']}"
            assert state_a["inspectorHidden"] is True, "Inspector panel should be hidden in orbit view"
            assert state_a["diagHidden"] is True, "Diagnostics panel should be hidden by default"
            assert state_a["waypointHidden"] is True, "Waypoint select should be hidden in orbit view"
            
            await capture_screenshot(ws, "m9f_01_global_orbit_restrained.png")

            # -------------------------------------------------------------
            # JOURNEY B: Navigation to Olympus Mons
            # -------------------------------------------------------------
            print("\n=== Executing Journey B: Navigation to Olympus Mons ===")
            await send_cmd(ws, "Page.navigate", {"url": f"{BASE_URL}/?place=iau_4453"})
            
            card_ready = await wait_for_condition(ws, """(() => {
                const card = document.getElementById('locationCard');
                const title = document.getElementById('locCardTitle');
                return card && !card.classList.contains('hidden') && title && title.textContent.includes('OLYMPUS');
            })()""", 15.0)
            assert card_ready, "Olympus Mons location card did not appear"
            await asyncio.sleep(2.5)

            state_b = await evaluate_js(ws, """(() => ({
                title: document.getElementById('locCardTitle').textContent,
                category: document.getElementById('locCardCategory').textContent,
                imagery: document.getElementById('locCardImagery').textContent,
                elevation: document.getElementById('locCardElevation').textContent,
                isElevAvailable: document.getElementById('locCardElevation').classList.contains('available'),
                telemetryLayer: document.getElementById('telemetryLayer').textContent,
                telemetryElev: document.getElementById('telemetryElevStatus').textContent,
                telemetryLon: document.getElementById('telemetryLon').textContent,
                telemetryLat: document.getElementById('telemetryLat').textContent,
                inspectorHidden: document.getElementById('inspectorPanel').classList.contains('hidden')
            }))()""")
            print("Journey B State:", state_b)
            assert "OLYMPUS" in state_b["title"]
            assert "MRO CTX" in state_b["imagery"] and "6" in state_b["imagery"]
            assert "GLOBAL DATUM ONLY" in state_b["elevation"]
            assert state_b["isElevAvailable"] is False, "Elevation must NOT claim available high-res DTM"
            assert "MRO CTX Regional" in state_b["telemetryLayer"]
            assert state_b["inspectorHidden"] is True, "Inspector must remain hidden outside Jezero"
            
            await capture_screenshot(ws, "m9f_02_olympus_mons_navigation.png")

            # -------------------------------------------------------------
            # JOURNEY C: Transition to Gale Crater
            # -------------------------------------------------------------
            print("\n=== Executing Journey C: Transition to Gale Crater ===")
            await send_cmd(ws, "Page.navigate", {"url": f"{BASE_URL}/?place=iau_2071"})
            
            gale_ready = await wait_for_condition(ws, """(() => {
                const title = document.getElementById('locCardTitle');
                return title && title.textContent.includes('GALE');
            })()""", 15.0)
            assert gale_ready, "Gale Crater location card did not appear"
            await asyncio.sleep(2.5)

            state_c = await evaluate_js(ws, """(() => ({
                title: document.getElementById('locCardTitle').textContent,
                imagery: document.getElementById('locCardImagery').textContent,
                elevation: document.getElementById('locCardElevation').textContent,
                telemetryLayer: document.getElementById('telemetryLayer').textContent,
                telemetryLon: document.getElementById('telemetryLon').textContent,
                telemetryLat: document.getElementById('telemetryLat').textContent,
                inspectorHidden: document.getElementById('inspectorPanel').classList.contains('hidden')
            }))()""")
            print("Journey C State:", state_c)
            assert "GALE" in state_c["title"]
            assert "MRO CTX" in state_c["imagery"]
            assert "GLOBAL DATUM ONLY" in state_c["elevation"]
            assert state_c["inspectorHidden"] is True

            await capture_screenshot(ws, "m9f_03_gale_crater_navigation.png")

            # -------------------------------------------------------------
            # JOURNEY D: Jezero Surface Workstation & Traversal Planning
            # -------------------------------------------------------------
            print("\n=== Executing Journey D: Jezero Surface Workstation & Traversal Planning ===")
            await send_cmd(ws, "Page.navigate", {"url": f"{BASE_URL}/?mode=mesh&action=plan"})
            
            jez_ready = await wait_for_condition(ws, """(() => {
                const inspector = document.getElementById('inspectorPanel');
                const statDist = document.getElementById('statDistance');
                return inspector && !inspector.classList.contains('hidden') && statDist && !statDist.textContent.includes('0.0');
            })()""", 15.0)
            assert jez_ready, "Jezero surface workstation and plan did not load"
            await asyncio.sleep(2.0)

            state_d1 = await evaluate_js(ws, """(() => ({
                telemetryLayer: document.getElementById('telemetryLayer').textContent,
                telemetryElev: document.getElementById('telemetryElevStatus').textContent,
                inspectorHidden: document.getElementById('inspectorPanel').classList.contains('hidden'),
                waypointHidden: document.getElementById('waypointSelect').classList.contains('hidden'),
                distance: document.getElementById('statDistance').textContent,
                effort: document.getElementById('statEffort').textContent,
                climb: document.getElementById('statClimb').textContent,
                slope: document.getElementById('statSlope').textContent
            }))()""")
            print("Journey D (Planning) State:", state_d1)
            assert "CTX" in state_d1["telemetryLayer"]
            assert "20 m CTX DTM" in state_d1["telemetryElev"]
            assert state_d1["inspectorHidden"] is False, "Inspector must be visible in Jezero workstation"
            assert state_d1["waypointHidden"] is False, "Waypoint select must be visible in Jezero workstation"
            assert "m" in state_d1["distance"]

            await capture_screenshot(ws, "m9f_04_jezero_workstation_planning.png")

            # Execute Stress Test Simulation
            print("Executing Stress Test Simulation...")
            await evaluate_js(ws, "(() => { document.getElementById('btnRunGauntlet').click(); })()")
            stress_ready = await wait_for_condition(ws, """(() => {
                const card = document.getElementById('gauntletResultCard');
                return card && !card.classList.contains('hidden');
            })()""", 15.0)
            assert stress_ready, "Stress test card did not appear"
            await asyncio.sleep(1.5)

            state_d2 = await evaluate_js(ws, """(() => ({
                cardHidden: document.getElementById('gauntletResultCard').classList.contains('hidden'),
                headline: document.getElementById('gauntletHeadline').textContent,
                deltaDist: document.getElementById('gauntletDeltaDist').textContent,
                deltaCost: document.getElementById('gauntletDeltaCost').textContent
            }))()""")
            print("Journey D (Stress Test) State:", state_d2)
            assert state_d2["cardHidden"] is False
            assert len(state_d2["headline"]) > 0

            await capture_screenshot(ws, "m9f_05_jezero_stress_test_simulation.png")

            # -------------------------------------------------------------
            # JOURNEY E: Return to Orbit & Honest Fallback (Elysium Planitia)
            # -------------------------------------------------------------
            print("\n=== Executing Journey E: Return to Orbit & Honest Fallback ===")
            await send_cmd(ws, "Page.navigate", {"url": f"{BASE_URL}/?place=iau_1784"})
            
            elys_ready = await wait_for_condition(ws, """(() => {
                const title = document.getElementById('locCardTitle');
                return title && title.textContent.includes('ELYSIUM');
            })()""", 15.0)
            assert elys_ready, "Elysium Planitia location card did not appear"
            await asyncio.sleep(2.5)

            state_e = await evaluate_js(ws, """(() => ({
                title: document.getElementById('locCardTitle').textContent,
                imagery: document.getElementById('locCardImagery').textContent,
                elevation: document.getElementById('locCardElevation').textContent,
                isElevAvailable: document.getElementById('locCardElevation').classList.contains('available'),
                telemetryLayer: document.getElementById('telemetryLayer').textContent,
                telemetryElev: document.getElementById('telemetryElevStatus').textContent,
                inspectorHidden: document.getElementById('inspectorPanel').classList.contains('hidden')
            }))()""")
            print("Journey E State:", state_e)
            assert "ELYSIUM" in state_e["title"]
            assert "VIKING MDIM 2.1 (232 m/px)" in state_e["imagery"]
            assert "GLOBAL DATUM (NO HIGH-RES DTM)" in state_e["elevation"]
            assert state_e["isElevAvailable"] is False
            assert "Viking MDIM" in state_e["telemetryLayer"] and "4.88" not in state_e["telemetryLayer"]
            assert state_e["inspectorHidden"] is True, "Inspector panel must remain hidden in Elysium exploration"

            await capture_screenshot(ws, "m9f_06_elysium_honest_fallback.png")

            print("\n>>> ALL 5 JOURNEYS COMPLETED AND VERIFIED SUCCESSFULLY! <<<")
            return True

    finally:
        proc.terminate()

if __name__ == "__main__":
    success = asyncio.run(run_journeys())
    sys.exit(0 if success else 1)
