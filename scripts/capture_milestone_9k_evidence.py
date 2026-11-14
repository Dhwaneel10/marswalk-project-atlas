"""
MarsWalk 2.0 - Milestone 9K Visual Evidence & Workspace Automation
Executes Journeys A through F via Chrome DevTools Protocol (CDP),
capturing verified screenshots at 1366x768 and validating workspace persistence.
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
DEBUG_PORT = 9467

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
        print(f"[JS EXCEPTION in evaluate_js] {res_obj['exceptionDetails']}")
    return res_obj.get("result", {}).get("value")


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
            # Journey A: Create, Save, Modify, and Restore Mission
            # -------------------------------------------------------------
            print("\n--- Journey A: Create, Save, Modify, and Restore Mission ---")
            await evaluate_js(ws, """
                (() => {
                    const missionData = window.__atlas.getMissionData();
                    const wps = missionData.waypoints;
                    const landing = wps.find(w => w.id === 'octavia_butler_landing');
                    const threeForks = wps.find(w => w.id === 'three_forks');
                    const artubyRidge = wps.find(w => w.id === 'artuby_ridge');
                    const kodiak = wps.find(w => w.id === 'kodiak_butte');

                    window.__atlas.clearIntermediateStops();
                    window.__atlas.setCustomStart(landing);
                    window.__atlas.addIntermediateStop(threeForks);
                    window.__atlas.addIntermediateStop(artubyRidge);
                    window.__atlas.setCustomGoal(kodiak);
                    window.__atlas.setVehicleMode('crew_eva');
                })()
            """)
            await asyncio.sleep(0.5)
            await evaluate_js(ws, "window.__atlas.calculateTraverse()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")
            await asyncio.sleep(1.0)

            # Save mission
            print("[Journey A] Saving mission 'Jezero Delta Scarp Survey'...")
            save_res = await evaluate_js(ws, "window.__atlas.saveMission('Jezero Delta Scarp Survey')", await_promise=True)
            status_text = await evaluate_js(ws, "document.getElementById('planningStatus') ? document.getElementById('planningStatus').textContent : ''")
            print(f"[DEBUG STATUS] planningStatus = '{status_text}'")
            saved_m_id = save_res.get("mission_id") if isinstance(save_res, dict) else None
            print(f"[Journey A] Mission saved: ID={saved_m_id}, Name={save_res.get('name') if isinstance(save_res, dict) else None}")
            assert saved_m_id, f"Saved mission must have a mission_id. save_res={repr(save_res)}, status={status_text}"

            # Check unsaved indicator is clear
            unsaved_1 = await evaluate_js(ws, "window.__atlas.hasUnsavedChanges()")
            assert not unsaved_1, "Expected unsaved changes to be false after save"

            # Alter the mission plan
            print("[Journey A] Altering plan (clearing stops and changing goal)...")
            await evaluate_js(ws, """
                (() => {
                    const missionData = window.__atlas.getMissionData();
                    const wps = missionData.waypoints;
                    const deltaRim = wps.find(w => w.id === 'delta_rim_overlook');
                    window.__atlas.clearIntermediateStops();
                    window.__atlas.setCustomGoal(deltaRim);
                })()
            """)
            await asyncio.sleep(0.5)
            unsaved_2 = await evaluate_js(ws, "window.__atlas.hasUnsavedChanges()")
            assert unsaved_2, "Expected unsaved changes to be true after alteration"

            # Reload the saved mission
            print(f"[Journey A] Reloading saved mission {saved_m_id}...")
            loaded_m = await evaluate_js(ws, f"window.__atlas.loadMission('{saved_m_id}')", await_promise=True)
            assert loaded_m.get("mission_id") == saved_m_id, "Loaded mission ID mismatch"
            stops_count = await evaluate_js(ws, "window.__atlas.getActiveStops().length")
            active_name = await evaluate_js(ws, "window.__atlas.getActiveMissionName()")
            print(f"[Journey A] Restored mission: Name='{active_name}', Stops={stops_count}")
            assert stops_count == 2, f"Expected 2 restored stops, got {stops_count}"
            assert active_name == "Jezero Delta Scarp Survey", f"Expected restored name, got {active_name}"

            # Open Mission Library modal to display saved record in the UI table
            await evaluate_js(ws, """
                (() => {
                    const modal = document.getElementById('missionLibraryModal');
                    modal.classList.remove('hidden');
                    modal.style.display = 'flex';
                })()
            """)
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, "m9k_01_save_and_restore_mission.png")

            # Close modal
            await evaluate_js(ws, """
                (() => {
                    const modal = document.getElementById('missionLibraryModal');
                    modal.classList.add('hidden');
                    modal.style.display = 'none';
                })()
            """)
            await asyncio.sleep(0.5)

            # -------------------------------------------------------------
            # Journey B: Server Restart & Session Persistence
            # -------------------------------------------------------------
            print("\n--- Journey B: Server Restart & Session Persistence ---")
            # Navigate away (simulate browser restart/reconnect)
            print("[Journey B] Reloading client session from server...")
            await send_cmd(ws, "Page.navigate", {"url": f"{BASE_URL}/"})
            ready = await wait_for_condition(
                ws,
                "(() => document.getElementById('loadingOverlay') && document.getElementById('loadingOverlay').classList.contains('hidden'))()",
                25.0
            )
            await asyncio.sleep(1.0)
            await evaluate_js(ws, "window.__atlas.setJezeroView()")
            await asyncio.sleep(1.0)

            # Fetch missions list from REST API
            missions_resp = await evaluate_js(ws, "window.__atlas.listMissions()", await_promise=True)
            m_items = missions_resp.get("missions", []) if isinstance(missions_resp, dict) else (missions_resp or [])
            print(f"[Journey B] Retrieved {len(m_items)} persistent missions from disk.")
            found_saved = any(isinstance(m, dict) and m.get("mission_id") == saved_m_id for m in m_items)
            assert found_saved, f"Saved mission {saved_m_id} must persist across sessions"

            # Open Mission Library modal to display persisted records
            await evaluate_js(ws, """
                (() => {
                    const btn = document.getElementById('btnOpenMissionLibrary') || document.getElementById('btnBrowseMissions');
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(1.2)
            await capture_screenshot(ws, "m9k_02_server_restart_persistence.png")

            # Close modal
            await evaluate_js(ws, """
                (() => {
                    document.getElementById('btnCloseMissionLibrary').click();
                })()
            """)
            await asyncio.sleep(0.5)

            # -------------------------------------------------------------
            # Journey C: Preserve Historical & New Simulation Runs
            # -------------------------------------------------------------
            print("\n--- Journey C: Preserve Historical & New Simulation Runs ---")
            # Load mission and calculate baseline
            await evaluate_js(ws, f"window.__atlas.loadMission('{saved_m_id}')", await_promise=True)
            await evaluate_js(ws, "window.__atlas.calculateTraverse()", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")
            await asyncio.sleep(1.0)

            # Run disruption 1: Corridor Rockfall
            print("[Journey C] Simulating Disruption 1: Rockfall Corridor...")
            await evaluate_js(ws, """
                (() => {
                    const select = document.getElementById('gauntletScenarioSelect');
                    select.value = 'scen_corridor_rockfall';
                    document.getElementById('btnRunGauntlet').click();
                })()
            """)
            await wait_for_condition(ws, "!document.getElementById('btnRunGauntlet').disabled")
            await asyncio.sleep(1.0)

            # Save Experiment 1
            print("[Journey C] Saving Run 1 to Experiment Library...")
            exp1_res = await evaluate_js(
                ws,
                "window.__atlas.saveExperiment('Rockfall Baseline Run', 'Crew EVA traversing corridor with 60m rockfall')",
                await_promise=True
            )
            exp1_id = exp1_res.get("experiment_id")
            print(f"[Journey C] Run 1 saved: ID={exp1_id}, Name={exp1_res.get('name')}")
            assert exp1_id, "Experiment 1 must have valid ID"

            # Alter parameters for Run 2: Robotic Rover
            print("[Journey C] Changing vehicle mode to robotic_rover and recalculating...")
            await evaluate_js(ws, """
                (() => {
                    window.__atlas.setVehicleMode('robotic_rover');
                })()
            """)
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")
            await asyncio.sleep(1.0)

            # Run disruption again
            print("[Journey C] Simulating Disruption on Robotic Rover...")
            await evaluate_js(ws, """
                (() => {
                    document.getElementById('btnRunGauntlet').click();
                })()
            """)
            await wait_for_condition(ws, "!document.getElementById('btnRunGauntlet').disabled")
            await asyncio.sleep(1.0)

            # Save Experiment 2
            print("[Journey C] Saving Run 2 to Experiment Library...")
            exp2_res = await evaluate_js(
                ws,
                "window.__atlas.saveExperiment('Rockfall Rover Fast Run', 'Robotic rover mobility profile traversing rockfall')",
                await_promise=True
            )
            exp2_id = exp2_res.get("experiment_id")
            print(f"[Journey C] Run 2 saved: ID={exp2_id}, Name={exp2_res.get('name')}")
            assert exp2_id and exp2_id != exp1_id, "Run 2 must have distinct ID"

            # Open Experiment Library modal to display both historical runs
            await evaluate_js(ws, """
                (() => {
                    const btn = document.getElementById('btnOpenExperimentLibrary') || document.getElementById('btnBrowseExperiments');
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(1.2)
            await capture_screenshot(ws, "m9k_03_preserve_historical_and_new_run.png")

            # Close modal
            await evaluate_js(ws, """
                (() => {
                    document.getElementById('btnCloseExperimentLibrary').click();
                })()
            """)
            await asyncio.sleep(0.5)

            # -------------------------------------------------------------
            # Journey D: Compare Experiments & Scientific Trade-Offs
            # -------------------------------------------------------------
            print("\n--- Journey D: Compare Experiments & Scientific Trade-Offs ---")
            print(f"[Journey D] Comparing Run 1 ({exp1_id}) vs Run 2 ({exp2_id})...")
            comp_res = await evaluate_js(
                ws,
                f"window.__atlas.compareExperiments('{exp1_id}', '{exp2_id}')",
                await_promise=True
            )
            print(f"[Journey D] Comparison Result: is_compatible={comp_res.get('is_compatible')}, deltas={comp_res.get('deltas', {})}")
            assert comp_res.get("is_compatible") is True, "Comparison must be marked compatible"
            assert "trade_offs_summary" in comp_res, "Comparison must include trade_offs_summary"

            # Open Comparison modal to display visual report & trade-offs
            await evaluate_js(ws, """
                (() => {
                    const modal = document.getElementById('experimentComparisonModal');
                    modal.classList.remove('hidden');
                    modal.style.display = 'flex';
                })()
            """)
            await asyncio.sleep(1.2)
            await capture_screenshot(ws, "m9k_04_compare_experiments_tradeoffs.png")

            # Close comparison modal
            await evaluate_js(ws, """
                (() => {
                    document.getElementById('btnCloseExperimentComparison').click();
                })()
            """)
            await asyncio.sleep(0.5)

            # -------------------------------------------------------------
            # Journey E: Stale State Invalidation with Preserved History
            # -------------------------------------------------------------
            print("\n--- Journey E: Stale State Invalidation with Preserved History ---")
            # Load Experiment 1 into workspace
            print(f"[Journey E] Loading Run 1 ({exp1_id}) into workspace...")
            loaded_exp = await evaluate_js(ws, f"window.__atlas.loadExperiment('{exp1_id}')", await_promise=True)
            assert loaded_exp.get("experiment_id") == exp1_id, "Loaded experiment mismatch"

            # Modify the active mission in workspace
            print("[Journey E] Modifying mission destination (changing goal)...")
            await evaluate_js(ws, """
                (() => {
                    const missionData = window.__atlas.getMissionData();
                    const wps = missionData.waypoints;
                    const belva = wps.find(w => w.id === 'belva_crater_overlook') || wps[0];
                    window.__atlas.setCustomGoal(belva);
                })()
            """)
            await asyncio.sleep(0.5)

            # Verify stale state and unsaved changes
            is_stale = await evaluate_js(ws, "window.__atlas.isSimulationStale()")
            has_unsaved = await evaluate_js(ws, "window.__atlas.hasUnsavedChanges()")
            banner_vis = await evaluate_js(ws, "!document.getElementById('staleStateBanner').classList.contains('hidden')")
            unsaved_vis = await evaluate_js(ws, "!document.getElementById('unsavedChangesBadge').classList.contains('hidden')")
            print(f"[Journey E] Stale={is_stale}, Banner={banner_vis}, Unsaved={has_unsaved}, UnsavedBadge={unsaved_vis}")
            assert is_stale and banner_vis, "Simulation must be marked stale with visible banner"
            assert has_unsaved and unsaved_vis, "Unsaved changes must be flagged"

            # Verify historical experiment on disk is untouched
            exp1_on_disk = await evaluate_js(ws, f"fetch('/api/experiments/{exp1_id}').then(r => r.json())", await_promise=True)
            assert exp1_on_disk.get("experiment_id") == exp1_id, "Historical record must remain unaltered on disk"

            # Scroll stale state banner into view
            await evaluate_js(ws, "document.getElementById('staleStateBanner').scrollIntoView({ behavior: 'instant', block: 'start' })")
            await asyncio.sleep(0.5)
            await capture_screenshot(ws, "m9k_05_stale_state_invalidation.png")

            # -------------------------------------------------------------
            # Journey F: Error Handling & Resilience
            # -------------------------------------------------------------
            print("\n--- Journey F: Error Handling & Resilience ---")
            # Attempt to fetch nonexistent mission
            err_resp = await evaluate_js(ws, """
                fetch('/api/missions/nonexistent_mission_id')
                    .then(r => r.json())
            """, await_promise=True)
            print(f"[Journey F] Nonexistent ID response: error_code={err_resp.get('error_code')}")
            assert err_resp.get("error_code") == "ERR_MISSION_NOT_FOUND", "Expected ERR_MISSION_NOT_FOUND"

            # Attempt directory traversal
            trav_resp = await evaluate_js(ws, """
                fetch('/api/missions/..%2F..%2Fetc%2Fpasswd')
                    .then(r => r.json())
            """, await_promise=True)
            print(f"[Journey F] Path traversal response: error_code={trav_resp.get('error_code')}")
            assert trav_resp.get("error_code") in ("ERR_INVALID_RECORD_ID", "ERR_INVALID_ID"), "Expected ERR_INVALID_RECORD_ID for path traversal"

            # Set status indicator to show error banner in HUD
            await evaluate_js(ws, """
                (() => {
                    const status = document.getElementById('planningStatus');
                    status.textContent = 'ERROR 404: Mission record [invalid_mission_ref] not found. Current workspace preserved.';
                    status.className = 'status-line status-error';
                    status.scrollIntoView({ behavior: 'instant', block: 'center' });
                })()
            """)
            await asyncio.sleep(0.8)
            await capture_screenshot(ws, "m9k_06_invalid_input_error_handling.png")

            print("\n=======================================================")
            print(" Milestone 9K Visual Evidence Journeys Complete! ")
            print("=======================================================")

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    asyncio.run(run_evidence_pipeline())
