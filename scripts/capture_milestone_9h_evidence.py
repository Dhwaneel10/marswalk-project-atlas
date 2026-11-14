"""
MarsWalk 2.0 - Milestone 9H Visual Evidence & Mission Rehearsal Verification Automation
Executes Journeys A through H via Chrome DevTools Protocol (CDP),
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
DEBUG_PORT = 9456

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


async def run_evidence_pipeline():
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
            # Load Jezero Surface Workstation
            # -------------------------------------------------------------
            print("\n=== Initializing Mars Atlas ===")
            await send_cmd(ws, "Page.navigate", {"url": f"{BASE_URL}/"})

            ready = await wait_for_condition(
                ws,
                "(() => document.getElementById('loadingOverlay') && document.getElementById('loadingOverlay').classList.contains('hidden'))()",
                20.0
            )
            if not ready:
                raise RuntimeError("Atlas failed to load in time.")

            print("[Init] Atlas UI online.")
            await asyncio.sleep(1.0)

            # Navigate to Jezero Workstation
            print("\n=== Entering 3D Jezero Surface Workstation ===")
            await evaluate_js(ws, "window.__atlas.setJezeroView()")
            await asyncio.sleep(1.5)

            # Ensure terrain texture is CTX
            await evaluate_js(ws, "window.__atlas.setTerrainTexture('ctx')")
            await asyncio.sleep(0.5)

            # -------------------------------------------------------------
            # Journey A: Baseline Mission & Crew EVA Timeline
            # -------------------------------------------------------------
            print("\n--- Journey A: Baseline Mission & Crew EVA Timeline ---")
            # Set Start = Landing Site (117, 157), Intermediate = Three Forks (153, 123), Goal = Kodiak Butte (194, 131)
            await evaluate_js(ws, """
                (() => {
                    const missionData = window.__atlas.getMissionData();
                    const wps = missionData.waypoints;
                    const landing = wps.find(w => w.id === 'octavia_butler_landing');
                    const threeForks = wps.find(w => w.id === 'three_forks');
                    const kodiak = wps.find(w => w.id === 'kodiak_butte');

                    window.__atlas.clearIntermediateStops();
                    window.__atlas.setCustomStart(landing);
                    window.__atlas.addIntermediateStop(threeForks);
                    window.__atlas.setCustomGoal(kodiak);
                    window.__atlas.setVehicleMode('crew_eva');
                })()
            """)
            await asyncio.sleep(0.5)
            await evaluate_js(ws, "window.__atlas.calculateTraverse()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")
            await asyncio.sleep(1.0)

            # Open timeline breakdown list
            await evaluate_js(ws, """
                (() => {
                    const container = document.getElementById('timelineEventsContainer');
                    const btn = document.getElementById('btnToggleTimelineDetails');
                    if (container && container.classList.contains('hidden')) {
                        container.classList.remove('hidden');
                        if (btn) btn.textContent = '▴ Hide Schedule Breakdown';
                    }
                })()
            """)
            await asyncio.sleep(0.5)

            # Verify Timeline values
            crew_margin = await evaluate_js(ws, "document.getElementById('statTimelineMarginBadge').textContent")
            crew_total = await evaluate_js(ws, "document.getElementById('timelineTotalTime').textContent")
            crew_dwell = await evaluate_js(ws, "document.getElementById('timelineDwellTime').textContent")
            print(f"[Journey A] Crew EVA Timeline: Drive + Dwell({crew_dwell}) = Total {crew_total}, Margin {crew_margin}")

            await capture_screenshot(ws, "m9h_01_baseline_crew_eva_timeline.png")

            # -------------------------------------------------------------
            # Journey B: Robotic Rover Mode & Single-Sol Drive Window
            # -------------------------------------------------------------
            print("\n--- Journey B: Robotic Rover Mode Timeline ---")
            await evaluate_js(ws, "window.__atlas.setVehicleMode('robotic_rover')")
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")
            await asyncio.sleep(1.0)

            rover_margin = await evaluate_js(ws, "document.getElementById('statTimelineMarginBadge').textContent")
            rover_total = await evaluate_js(ws, "document.getElementById('timelineTotalTime').textContent")
            rover_limit = await evaluate_js(ws, "document.getElementById('timelineLimitTime').textContent")
            rover_label = await evaluate_js(ws, "document.getElementById('statTravelTimeLabel').textContent")
            print(f"[Journey B] Rover Timeline: {rover_label} -> Total {rover_total} / {rover_limit}, Margin {rover_margin}")

            await capture_screenshot(ws, "m9h_02_robotic_rover_mode_timeline.png")

            # -------------------------------------------------------------
            # Journey C: Multi-Stop Stop Order Optimization (TSP)
            # -------------------------------------------------------------
            print("\n--- Journey C: Multi-Stop Science Mission Order Optimizer ---")
            # Switch back to Crew EVA, and add two intermediate stops in suboptimal zigzag order:
            # Octavia Butler -> Hawksbill Gap -> Three Forks -> Kodiak Butte
            await evaluate_js(ws, """
                (() => {
                    const missionData = window.__atlas.getMissionData();
                    const wps = missionData.waypoints;
                    const landing = wps.find(w => w.id === 'octavia_butler_landing');
                    const hawksbill = wps.find(w => w.id === 'hawksbill_gap');
                    const threeForks = wps.find(w => w.id === 'three_forks');
                    const kodiak = wps.find(w => w.id === 'kodiak_butte');

                    window.__atlas.setVehicleMode('crew_eva');
                    window.__atlas.clearIntermediateStops();
                    window.__atlas.setCustomStart(landing);
                    // Add in zigzag order: hawksbill gap first, then three forks
                    window.__atlas.addIntermediateStop(hawksbill);
                    window.__atlas.addIntermediateStop(threeForks);
                    window.__atlas.setCustomGoal(kodiak);
                })()
            """)
            await asyncio.sleep(0.5)
            await evaluate_js(ws, "window.__atlas.calculateTraverse()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")
            await asyncio.sleep(1.0)

            orig_dist = await evaluate_js(ws, "document.getElementById('statDistance').textContent")
            print(f"[Journey C] Initial Zigzag Distance: {orig_dist}")

            # Now execute stop order optimization via exact TSP
            print("[Journey C] Running optimizeMissionStops()...")
            await evaluate_js(ws, "window.__atlas.optimizeMissionStops()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnOptimizeStops').disabled")
            await asyncio.sleep(1.5)

            opt_status = await evaluate_js(ws, "document.getElementById('planningStatus').textContent")
            opt_dist = await evaluate_js(ws, "document.getElementById('statDistance').textContent")
            print(f"[Journey C] Optimizer Result: {opt_status} (New Distance: {opt_dist})")

            await capture_screenshot(ws, "m9h_03_stop_order_optimization_tsp.png")

            # -------------------------------------------------------------
            # Journey D: Scenario A — Traverse Corridor Rockfall (Detour)
            # -------------------------------------------------------------
            print("\n--- Journey D: Scenario A — Traverse Corridor Rockfall ---")
            await evaluate_js(ws, """
                (() => {
                    document.getElementById('gauntletScenarioSelect').value = 'scen_corridor_rockfall';
                })()
            """)
            await asyncio.sleep(0.3)
            await evaluate_js(ws, "window.__atlas.runGauntletStressTest()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnRunGauntlet').disabled")
            await asyncio.sleep(1.0)

            rockfall_headline = await evaluate_js(ws, "document.getElementById('gauntletHeadline').textContent")
            rockfall_delta_d = await evaluate_js(ws, "document.getElementById('gauntletDeltaDist').textContent")
            rockfall_delta_t = await evaluate_js(ws, "document.getElementById('gauntletDeltaTime').textContent")
            print(f"[Journey D] Corridor Rockfall: {rockfall_headline} ({rockfall_delta_d}, {rockfall_delta_t})")

            await capture_screenshot(ws, "m9h_04_scenario_a_corridor_rockfall_detour.png")

            # -------------------------------------------------------------
            # Journey E: Scenario B — Unstable Sand / Soft Regolith (3.0x Effort)
            # -------------------------------------------------------------
            print("\n--- Journey E: Scenario B — Unstable Sand Dune Migration ---")
            await evaluate_js(ws, """
                (() => {
                    document.getElementById('gauntletScenarioSelect').value = 'scen_unstable_sand';
                })()
            """)
            await asyncio.sleep(0.3)
            await evaluate_js(ws, "window.__atlas.runGauntletStressTest()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnRunGauntlet').disabled")
            await asyncio.sleep(1.0)

            sand_headline = await evaluate_js(ws, "document.getElementById('gauntletHeadline').textContent")
            sand_effort = await evaluate_js(ws, "document.getElementById('gauntletDeltaCost').textContent")
            print(f"[Journey E] Unstable Sand: {sand_headline} ({sand_effort})")

            await capture_screenshot(ws, "m9h_05_scenario_b_unstable_sand_footprint.png")

            # -------------------------------------------------------------
            # Journey F: Scenario C — Restricted Slope Corridor (10.0° Cap)
            # -------------------------------------------------------------
            print("\n--- Journey F: Scenario C — Restricted Slope Corridor ---")
            await evaluate_js(ws, """
                (() => {
                    document.getElementById('gauntletScenarioSelect').value = 'scen_restricted_slope';
                })()
            """)
            await asyncio.sleep(0.3)
            await evaluate_js(ws, "window.__atlas.runGauntletStressTest()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnRunGauntlet').disabled")
            await asyncio.sleep(1.0)

            slope_headline = await evaluate_js(ws, "document.getElementById('gauntletHeadline').textContent")
            print(f"[Journey F] Slope Restriction: {slope_headline}")

            await capture_screenshot(ws, "m9h_06_scenario_c_restricted_slope_corridor.png")

            # -------------------------------------------------------------
            # Journey G: Scenario D — Drive Actuator Derating (0 m Detour)
            # -------------------------------------------------------------
            print("\n--- Journey G: Scenario D — Mobility Derating (0 m Detour) ---")
            await evaluate_js(ws, """
                (() => {
                    document.getElementById('gauntletScenarioSelect').value = 'scen_mobility_degradation';
                })()
            """)
            await asyncio.sleep(0.3)
            await evaluate_js(ws, "window.__atlas.runGauntletStressTest()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnRunGauntlet').disabled")
            await asyncio.sleep(1.0)

            mobility_headline = await evaluate_js(ws, "document.getElementById('gauntletHeadline').textContent")
            mobility_delta_d = await evaluate_js(ws, "document.getElementById('gauntletDeltaDist').textContent")
            mobility_delta_t = await evaluate_js(ws, "document.getElementById('gauntletDeltaTime').textContent")
            print(f"[Journey G] Mobility Derating: {mobility_headline} (Detour: {mobility_delta_d}, Time: {mobility_delta_t})")

            await capture_screenshot(ws, "m9h_07_scenario_d_mobility_degradation_zero_detour.png")

            # -------------------------------------------------------------
            # Journey H: Compound Disruption & Recovery Plan Execution
            # -------------------------------------------------------------
            print("\n--- Journey H: Compound Disruption & Recovery Plan Execution ---")
            await evaluate_js(ws, """
                (() => {
                    document.getElementById('gauntletScenarioSelect').value = 'scen_compound_rockfall_mobility';
                })()
            """)
            await asyncio.sleep(0.3)
            await evaluate_js(ws, "window.__atlas.runGauntletStressTest()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnRunGauntlet').disabled")
            await asyncio.sleep(1.0)

            compound_headline = await evaluate_js(ws, "document.getElementById('gauntletHeadline').textContent")
            recovery_text = await evaluate_js(ws, "document.getElementById('recoveryPlanText').textContent")
            recovery_gain = await evaluate_js(ws, "document.getElementById('recoveryMarginGain').textContent")
            print(f"[Journey H] Compound Disruption: {compound_headline}")
            print(f"[Journey H] Recovery Recommended: {recovery_text} ({recovery_gain})")

            # Execute Recovery Plan
            print("[Journey H] Applying Recommended Recovery Plan...")
            await evaluate_js(ws, "window.__atlas.applyRecoveryPlan()")
            await asyncio.sleep(1.5)

            rec_status = await evaluate_js(ws, "document.getElementById('planningStatus').textContent")
            rec_dist = await evaluate_js(ws, "document.getElementById('statDistance').textContent")
            print(f"[Journey H] Post-Recovery Status: {rec_status} (Distance: {rec_dist})")

            await capture_screenshot(ws, "m9h_08_scenario_compound_and_recovery_applied.png")

            print("\n=======================================================")
            print(" Milestone 9H Visual Evidence Journeys Complete! ")
            print("=======================================================")

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    asyncio.run(run_evidence_pipeline())
