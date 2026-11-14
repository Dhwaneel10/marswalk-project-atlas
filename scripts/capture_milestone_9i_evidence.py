"""
MarsWalk 2.0 - Milestone 9I Visual Evidence & Mission Analysis Laboratory Automation
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
DEBUG_PORT = 9460

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
            # Journey A: Baseline Mission & Stale Simulation Invalidation
            # -------------------------------------------------------------
            print("\n--- Journey A: Baseline Mission & Stale Simulation Invalidation ---")
            await evaluate_js(ws, """
                (() => {
                    const missionData = window.__atlas.getMissionData();
                    const wps = missionData.waypoints;
                    const landing = wps.find(w => w.id === 'octavia_butler_landing');
                    const hawksbill = wps.find(w => w.id === 'hawksbill_gap');
                    const deltaRim = wps.find(w => w.id === 'delta_rim_overlook') || wps.find(w => w.id === 'kodiak_butte');

                    window.__atlas.clearIntermediateStops();
                    window.__atlas.setCustomStart(landing);
                    window.__atlas.addIntermediateStop(hawksbill);
                    window.__atlas.setCustomGoal(deltaRim);
                    window.__atlas.setVehicleMode('crew_eva');
                })()
            """)
            await asyncio.sleep(0.5)
            await evaluate_js(ws, "window.__atlas.calculateTraverse()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")
            await asyncio.sleep(1.0)

            # Trigger stale simulation state to test invalidation banner
            await evaluate_js(ws, """
                (() => {
                    window.__atlas.setSimulationStale(true);
                })()
            """)
            await asyncio.sleep(0.5)

            is_stale = await evaluate_js(ws, "window.__atlas.isSimulationStale()")
            banner_visible = await evaluate_js(ws, "!document.getElementById('staleStateBanner').classList.contains('hidden')")
            print(f"[Journey A] Stale State: is_stale={is_stale}, banner_visible={banner_visible}")
            assert is_stale and banner_visible, "Stale state banner failed to display."

            await capture_screenshot(ws, "m9i_01_baseline_and_stale_invalidation.png")

            # -------------------------------------------------------------
            # Journey B: Multi-Stop 2-Opt Heuristic & Algorithm Disclosure
            # -------------------------------------------------------------
            print("\n--- Journey B: Multi-Stop 2-Opt Heuristic & Disclosure (k=9 > 7) ---")
            await evaluate_js(ws, """
                (() => {
                    const missionData = window.__atlas.getMissionData();
                    const wps = missionData.waypoints;
                    const landing = wps.find(w => w.id === 'octavia_butler_landing');
                    const goal = wps.find(w => w.id === 'kodiak_butte');

                    window.__atlas.clearIntermediateStops();
                    window.__atlas.setCustomStart(landing);
                    window.__atlas.setCustomGoal(goal);

                    // Add 9 intermediate targets (k=9 stops, requiring 2-Opt heuristic)
                    const candidateStops = wps.filter(w => w.id !== landing.id && w.id !== goal.id);
                    for (let i = 0; i < Math.min(9, candidateStops.length); i++) {
                        window.__atlas.addIntermediateStop(candidateStops[i]);
                    }
                })()
            """)
            await asyncio.sleep(0.5)
            await evaluate_js(ws, "window.__atlas.calculateTraverse()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")
            await asyncio.sleep(1.0)

            # Run 2-Opt optimization
            print("[Journey B] Executing optimizeMissionStops() for 9 targets...")
            await evaluate_js(ws, "window.__atlas.optimizeMissionStops()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnOptimizeStops').disabled")
            await asyncio.sleep(1.5)

            opt_status = await evaluate_js(ws, "document.getElementById('planningStatus').textContent")
            print(f"[Journey B] Optimizer Status: {opt_status}")
            assert "2-Opt heuristic" in opt_status or "approx" in opt_status.lower(), f"Expected heuristic disclosure, got: {opt_status}"

            await capture_screenshot(ws, "m9i_02_multistop_2opt_heuristic_disclosure.png")

            # -------------------------------------------------------------
            # Journey C: Scenario Comparison Matrix Lab
            # -------------------------------------------------------------
            print("\n--- Journey C: Scenario Comparison Matrix Lab ---")
            # Set standard 3-target mission for comparative analysis
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

            print("[Journey C] Executing runScenarioComparison()...")
            await evaluate_js(ws, "window.__atlas.runScenarioComparison()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnRunComparison').disabled")
            await asyncio.sleep(1.5)

            comp_state = await evaluate_js(ws, "window.__atlas.getComparisonState()")
            num_scenarios = len(comp_state.get("lastComparisonResult", {}).get("scenarios", []))
            print(f"[Journey C] Evaluated {num_scenarios} scenarios in comparison lab.")
            assert num_scenarios >= 4, f"Expected at least 4 scenarios evaluated, got {num_scenarios}"

            # Scroll comparison matrix into view
            await evaluate_js(ws, "document.getElementById('comparisonLabCard').scrollIntoView({ behavior: 'instant', block: 'start' })")
            await asyncio.sleep(0.5)

            await capture_screenshot(ws, "m9i_03_scenario_comparison_matrix.png")

            # -------------------------------------------------------------
            # Journey D: Scenario Comparison 3D Detour & Hazard Switching
            # -------------------------------------------------------------
            print("\n--- Journey D: Scenario Comparison 3D Switching ---")
            # Click row 1 (Corridor Rockfall) in table body
            await evaluate_js(ws, """
                (() => {
                    const tbody = document.getElementById('scenarioComparisonTableBody');
                    const rows = tbody.querySelectorAll('tr');
                    if (rows.length > 1) {
                        rows[1].click(); // Click first scenario row (after baseline)
                    }
                })()
            """)
            await asyncio.sleep(1.0)

            active_scen_label = await evaluate_js(ws, "document.getElementById('comparisonActiveScenarioLabel').textContent")
            print(f"[Journey D] Active Scenario Selected in 3D: {active_scen_label}")

            # Keep comparison matrix scrolled so row selection and active label are visible
            await evaluate_js(ws, "document.getElementById('comparisonLabCard').scrollIntoView({ behavior: 'instant', block: 'start' })")
            await asyncio.sleep(0.5)

            await capture_screenshot(ws, "m9i_04_scenario_comparison_3d_switching.png")

            # -------------------------------------------------------------
            # Journey E: Scenario Sensitivity Parameter Sweep Analysis
            # -------------------------------------------------------------
            print("\n--- Journey E: Scenario Sensitivity Sweep ---")
            print("[Journey E] Executing runScenarioSensitivity(scen_corridor_rockfall, radius_m)...")
            await evaluate_js(
                ws,
                "window.__atlas.runScenarioSensitivity('scen_corridor_rockfall', 'radius_m', [20.0, 40.0, 60.0, 80.0, 100.0, 120.0])",
                await_promise=True
            )
            await wait_for_condition(ws, "!document.getElementById('btnRunSensitivity').disabled")
            await asyncio.sleep(1.5)

            sens_state = await evaluate_js(ws, "window.__atlas.getComparisonState()")
            num_evals = (sens_state.get("lastSensitivityResult") or {}).get("num_evaluations", 0)
            print(f"[Journey E] Sensitivity sweep evaluated {num_evals} steps.")
            assert num_evals == 6, f"Expected 6 sweep steps, got {num_evals}"

            # Scroll sensitivity table card into view
            await evaluate_js(ws, "document.getElementById('sensitivityResultCard').scrollIntoView({ behavior: 'instant', block: 'start' })")
            await asyncio.sleep(0.5)

            await capture_screenshot(ws, "m9i_05_scenario_sensitivity_sweep.png")

            # -------------------------------------------------------------
            # Journey F: 3-Way Recovery Plan Comparison
            # -------------------------------------------------------------
            print("\n--- Journey F: 3-Way Recovery Plan Comparison ---")
            # Click Compound Rockfall & Mobility Degradation row in Comparison Table
            await evaluate_js(ws, """
                (() => {
                    const tbody = document.getElementById('scenarioComparisonTableBody');
                    const rows = tbody.querySelectorAll('tr');
                    let targetRow = rows[rows.length - 1];
                    for (const r of rows) {
                        if (r.textContent.includes('Compound') || r.textContent.includes('Rockfall')) {
                            targetRow = r;
                            break;
                        }
                    }
                    targetRow.click();
                })()
            """)
            await asyncio.sleep(1.0)

            rec_boxes = await evaluate_js(ws, "document.querySelectorAll('#recoveryThreeWayTable .recovery-stat-box').length")
            rec_gain = await evaluate_js(ws, "document.getElementById('recoveryMarginGain').textContent")
            print(f"[Journey F] Recovery Comparison: {rec_boxes} comparison boxes rendered. Gain: {rec_gain}")
            assert rec_boxes == 3, f"Expected 3 stat boxes in 3-way recovery grid, got {rec_boxes}"

            # Scroll recovery plan card into view
            await evaluate_js(ws, "document.getElementById('recoveryPlanCard').scrollIntoView({ behavior: 'instant', block: 'start' })")
            await asyncio.sleep(0.5)

            await capture_screenshot(ws, "m9i_06_threeway_recovery_comparison.png")

            # -------------------------------------------------------------
            # Journey G: Recovery Route Applied & Stale Marked
            # -------------------------------------------------------------
            print("\n--- Journey G: Apply Recommended Recovery Route ---")
            await evaluate_js(ws, "window.__atlas.applyRecoveryPlan()")
            await asyncio.sleep(1.5)

            is_stale_after_rec = await evaluate_js(ws, "window.__atlas.isSimulationStale()")
            print(f"[Journey G] Post-Recovery State: is_stale={is_stale_after_rec}")
            assert is_stale_after_rec, "Mission should be marked stale after applying recovery route."

            # Scroll stale state banner into view
            await evaluate_js(ws, "document.getElementById('staleStateBanner').scrollIntoView({ behavior: 'instant', block: 'start' })")
            await asyncio.sleep(0.5)

            await capture_screenshot(ws, "m9i_07_recovery_applied_and_stale_marked.png")

            # -------------------------------------------------------------
            # Journey H: Technical Mission Briefing Export
            # -------------------------------------------------------------
            print("\n--- Journey H: Technical Mission Briefing Export ---")
            await evaluate_js(ws, "window.__atlas.exportMissionBriefing('md')", await_promise=True)
            await asyncio.sleep(1.0)

            briefing_status = await evaluate_js(ws, "document.getElementById('planningStatus').textContent")
            print(f"[Journey H] Briefing Export Status: {briefing_status}")
            assert "BRIEFING DOWNLOADED" in briefing_status, f"Expected download confirmation, got: {briefing_status}"

            # Scroll export briefing buttons into view
            await evaluate_js(ws, "document.getElementById('btnExportBriefingMd').scrollIntoView({ behavior: 'instant', block: 'center' })")
            await asyncio.sleep(0.5)

            await capture_screenshot(ws, "m9i_08_mission_briefing_export.png")

            print("\n=======================================================")
            print(" Milestone 9I Visual Evidence Journeys Complete! ")
            print("=======================================================")

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    asyncio.run(run_evidence_pipeline())
