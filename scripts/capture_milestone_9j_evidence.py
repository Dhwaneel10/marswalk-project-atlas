"""
MarsWalk 2.0 - Milestone 9J Visual Evidence & Contract Verification Automation
Executes Journeys A through G via Chrome DevTools Protocol (CDP),
capturing verified screenshots at 1366x768 and validating contract integrity.
"""

import os
import sys
import time
import json
import shutil
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
DEBUG_PORT = 9465

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


async def wait_for_condition(ws, expr, timeout_s=25.0, poll_interval=0.3):
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
    ARTIFACT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    out_path = OUTPUT_DIR / filename
    resp = await send_cmd(ws, "Page.captureScreenshot", {"format": "png"})
    b64_data = resp.get("result", {}).get("data", "")
    if b64_data:
        raw_bytes = base64.b64decode(b64_data)
        out_path.write_bytes(raw_bytes)

        # Copy to artifact directory for rendering
        art_path = ARTIFACT_OUTPUT_DIR / filename
        art_path.write_bytes(raw_bytes)

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
                25.0
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
            # Journey A: Canonical Single-Leg Mission Contract
            # -------------------------------------------------------------
            print("\n--- Journey A: Canonical Single-Leg Mission Contract ---")
            await evaluate_js(ws, """
                (() => {
                    const missionData = window.__atlas.getMissionData();
                    const wps = missionData.waypoints;
                    const landing = wps.find(w => w.id === 'octavia_butler_landing');
                    const kodiak = wps.find(w => w.id === 'kodiak_butte');

                    window.__atlas.clearIntermediateStops();
                    window.__atlas.setCustomStart(landing);
                    window.__atlas.setCustomGoal(kodiak);
                    window.__atlas.setVehicleMode('crew_eva');
                })()
            """)
            await asyncio.sleep(0.5)
            await evaluate_js(ws, "window.__atlas.calculateTraverse()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")
            await asyncio.sleep(1.0)

            baseline_res = await evaluate_js(ws, "window.__atlas.getBaselineRouteResult()")
            fingerprint = await evaluate_js(ws, "window.__atlas.getMissionFingerprint()")
            print(f"[Journey A] Baseline Result Loaded: schema_version={baseline_res.get('schema_version')}, fingerprint={fingerprint[:12]}...")
            assert baseline_res.get("schema_version") == "1.0.0", "Baseline schema version mismatch"
            assert len(fingerprint) == 64, "Input fingerprint must be 64-char hex string"
            ground_dist = baseline_res.get("route_metrics", {}).get("ground_distance_m") or baseline_res.get("distance_m", 0)
            assert ground_dist is not None and ground_dist > 0, f"Distance must be positive, got: {ground_dist}"

            await capture_screenshot(ws, "m9j_01_canonical_mission_contract.png")

            # -------------------------------------------------------------
            # Journey B: Multi-Stop Mission with 2-Opt TSP Optimization
            # -------------------------------------------------------------
            print("\n--- Journey B: Multi-Stop Mission with 2-Opt TSP Optimization ---")
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
            assert "2-Opt" in opt_status or "approx" in opt_status.lower() or "heuristic" in opt_status.lower(), (
                f"Expected heuristic disclosure, got: {opt_status}"
            )

            await capture_screenshot(ws, "m9j_02_multistop_2opt_optimization.png")

            # -------------------------------------------------------------
            # Journey C: Multi-Scenario Comparison Matrix & Safe Deltas
            # -------------------------------------------------------------
            print("\n--- Journey C: Multi-Scenario Comparison Matrix & Safe Deltas ---")
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

            await capture_screenshot(ws, "m9j_03_scenario_comparison_safe_deltas.png")

            # -------------------------------------------------------------
            # Journey D: Scenario Parameter Sensitivity Sweep
            # -------------------------------------------------------------
            print("\n--- Journey D: Scenario Parameter Sensitivity Sweep ---")
            print("[Journey D] Executing runScenarioSensitivity(scen_corridor_rockfall, radius_m)...")
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

            await capture_screenshot(ws, "m9j_04_scenario_sensitivity_sweep.png")

            # -------------------------------------------------------------
            # Journey E: Three-Way Recovery Comparison Contract
            # -------------------------------------------------------------
            print("\n--- Journey E: Three-Way Recovery Comparison Contract ---")
            # Click Corridor Rockfall row in Comparison Table
            await evaluate_js(ws, """
                (() => {
                    const tbody = document.getElementById('scenarioComparisonTableBody');
                    const rows = tbody.querySelectorAll('tr');
                    let targetRow = rows[1]; // default to first scenario
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
            print(f"[Journey E] Recovery Comparison: {rec_boxes} comparison boxes rendered. Gain: {rec_gain}")
            assert rec_boxes == 3, f"Expected 3 stat boxes in 3-way recovery grid, got {rec_boxes}"

            # Scroll recovery plan card into view
            await evaluate_js(ws, "document.getElementById('recoveryPlanCard').scrollIntoView({ behavior: 'instant', block: 'start' })")
            await asyncio.sleep(0.5)

            await capture_screenshot(ws, "m9j_05_threeway_recovery_contract.png")

            # -------------------------------------------------------------
            # Journey F: Stale Simulation Invalidation Workflow
            # -------------------------------------------------------------
            print("\n--- Journey F: Stale Simulation Invalidation Workflow ---")
            # Alter endpoint by setting a different goal to invalidate simulation
            await evaluate_js(ws, """
                (() => {
                    const missionData = window.__atlas.getMissionData();
                    const wps = missionData.waypoints;
                    const deltaRim = wps.find(w => w.id === 'delta_rim_overlook') || wps[wps.length - 1];
                    window.__atlas.setCustomGoal(deltaRim);
                })()
            """)
            await asyncio.sleep(0.5)

            is_stale = await evaluate_js(ws, "window.__atlas.isSimulationStale()")
            banner_visible = await evaluate_js(ws, "!document.getElementById('staleStateBanner').classList.contains('hidden')")
            print(f"[Journey F] Invalidation State: is_stale={is_stale}, banner_visible={banner_visible}")
            assert is_stale and banner_visible, "Stale state banner failed to display after endpoint modification."

            # Scroll stale state banner into view
            await evaluate_js(ws, "document.getElementById('staleStateBanner').scrollIntoView({ behavior: 'instant', block: 'start' })")
            await asyncio.sleep(0.5)

            await capture_screenshot(ws, "m9j_06_stale_invalidation_workflow.png")

            # -------------------------------------------------------------
            # Journey G: Technical Mission Briefing Export Contract
            # -------------------------------------------------------------
            print("\n--- Journey G: Technical Mission Briefing Export Contract ---")
            # Recalculate traverse to obtain authoritative fresh state
            await evaluate_js(ws, "window.__atlas.calculateTraverse()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")
            await asyncio.sleep(1.0)

            # Export Markdown briefing
            await evaluate_js(ws, "window.__atlas.exportMissionBriefing('md')", await_promise=True)
            await asyncio.sleep(1.0)

            briefing_status = await evaluate_js(ws, "document.getElementById('planningStatus').textContent")
            print(f"[Journey G] Briefing Export Status: {briefing_status}")
            assert "BRIEFING DOWNLOADED" in briefing_status, f"Expected download confirmation, got: {briefing_status}"

            # Scroll export briefing buttons into view
            await evaluate_js(ws, "document.getElementById('btnExportBriefingMd').scrollIntoView({ behavior: 'instant', block: 'center' })")
            await asyncio.sleep(0.5)

            await capture_screenshot(ws, "m9j_07_briefing_export_contract.png")

            print("\n=======================================================")
            print(" Milestone 9J Visual Evidence Journeys Complete! ")
            print("=======================================================")

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    asyncio.run(run_evidence_pipeline())
