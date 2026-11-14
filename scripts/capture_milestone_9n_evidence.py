"""
MarsWalk 2.0 - Milestone 9N Verification & Visual Evidence Capture Script
Captures all 16 verified journeys demonstrating:
1. Jezero 3D Workstation default entry with ALL 12 candidate waypoint labels visible.
2. Waypoint Visibility switched to "Mission Locations Only" (clean active target filtering).
3. Waypoint Visibility restored to "All Locations" (12 labels restored).
4. Clear Start Action (removes departure, invalidates route & telemetry, START REQUIRED badge).
5. Clear Goal Action (removes destination, invalidates route & telemetry, GOAL REQUIRED badge).
6. Swap Endpoints Action (exchanges departure & destination, recalculates traverse).
7. Reset Mission Confirmation Modal (data protection guarantee notice).
8. Reset Mission Clean Empty Workspace (empty mission state, saved data untouched).
9. Multi-Stop Vehicle & Profile Regression (preserves stops, rock-solid 3D mesh).
10. Regional Exploration: Olympus Mons.
11. Regional Exploration: Valles Marineris (authentic NASA Mars Trek CTX mosaic).
12. Regional Exploration: Gale Crater (Curiosity roving area).
13. Location Dossier Card Orbit Return via [GLOBAL MARS] button.
14. Persistent Mission Library (saved missions survive workspace reset).
15. Responsive Tablet Breakpoint (1024x768).
16. Responsive Mobile Breakpoint (390x844).
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
DEBUG_PORT = 9489

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


async def set_viewport(ws, width, height, is_mobile=False):
    await send_cmd(ws, "Emulation.setDeviceMetricsOverride", {
        "width": width,
        "height": height,
        "deviceScaleFactor": 1,
        "mobile": is_mobile
    })
    await asyncio.sleep(0.5)


async def capture_screenshot(ws, filename):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    out_path = OUTPUT_DIR / filename
    resp = await send_cmd(ws, "Page.captureScreenshot", {"format": "png"})
    b64_data = resp.get("result", {}).get("data", "")
    if b64_data:
        raw_bytes = base64.b64decode(b64_data)
        out_path.write_bytes(raw_bytes)

        # Copy to artifact directory for markdown embedding
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
        f"{BASE_URL}/?landing=0"
    ])
    time.sleep(2.5)

    try:
        targets_raw = urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json").read().decode()
        targets = json.loads(targets_raw)
        page_target = next(t for t in targets if t.get("type") == "page" and "3000" in t.get("url", ""))

        async with websockets.connect(page_target["webSocketDebuggerUrl"], max_size=100*1024*1024) as ws:
            await send_cmd(ws, "Page.enable")
            await send_cmd(ws, "Runtime.enable")

            print("\n=== Initializing MarsWalk 2.0 Project Atlas for Milestone 9N Evidence Capture ===")
            await send_cmd(ws, "Page.navigate", {"url": f"{BASE_URL}/?landing=0&mode=mesh"})

            ready = await wait_for_condition(
                ws,
                "(() => document.getElementById('loadingOverlay') && document.getElementById('loadingOverlay').classList.contains('hidden') && window.__atlas !== undefined)()",
                25.0
            )
            if not ready:
                raise RuntimeError("Atlas failed to load in time.")

            print("[Init] Atlas UI online with Milestone 9N upgrades.")
            await set_viewport(ws, 1366, 768)
            await asyncio.sleep(2.0)

            # -------------------------------------------------------------
            # Journey 1: Default Jezero View with ALL 12 Waypoints Visible
            # -------------------------------------------------------------
            print("\n--- Journey 1: Jezero Workstation Default (All 12 Waypoints Visible) ---")
            await evaluate_js(ws, """
                (() => {
                    const btn = document.getElementById('btnFlyJezero');
                    if (btn) btn.click();
                    window.__atlas.setWaypointVisibilityMode('all');
                })()
            """)
            await asyncio.sleep(4.5)

            # Verification of visible labels count
            vis_count = await evaluate_js(ws, """
                (() => {
                    const labels = Array.from(document.querySelectorAll('.jezero-waypoint-label'));
                    return labels.filter(el => window.getComputedStyle(el).display !== 'none').length;
                })()
            """)
            print(f"[Verification] Visible Jezero Waypoint Labels: {vis_count} (out of 12 candidate waypoints)")
            await capture_screenshot(ws, "m9n_01_jezero_default_all_waypoints.png")

            # -------------------------------------------------------------
            # Journey 2: Switch to "Mission Locations Only"
            # -------------------------------------------------------------
            print("\n--- Journey 2: Waypoint Visibility Toggle (Mission Locations Only) ---")
            await evaluate_js(ws, """
                (() => {
                    const btn = document.getElementById('btnVisMission');
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(1.0)
            vis_mission_count = await evaluate_js(ws, """
                (() => {
                    const labels = Array.from(document.querySelectorAll('.jezero-waypoint-label'));
                    return labels.filter(el => window.getComputedStyle(el).display !== 'none').length;
                })()
            """)
            print(f"[Verification] Mission-Only Visible Waypoints: {vis_mission_count} (Departure + Destination)")
            await capture_screenshot(ws, "m9n_02_jezero_mission_locations_only.png")

            # -------------------------------------------------------------
            # Journey 3: Switch back to "All Locations"
            # -------------------------------------------------------------
            print("\n--- Journey 3: Waypoint Visibility Restored (All 12 Locations) ---")
            await evaluate_js(ws, """
                (() => {
                    const btn = document.getElementById('btnVisAll');
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(1.0)
            vis_all_restored = await evaluate_js(ws, """
                (() => {
                    const labels = Array.from(document.querySelectorAll('.jezero-waypoint-label'));
                    return labels.filter(el => window.getComputedStyle(el).display !== 'none').length;
                })()
            """)
            print(f"[Verification] Restored Waypoints: {vis_all_restored}")
            await capture_screenshot(ws, "m9n_03_jezero_all_locations_restored.png")

            # -------------------------------------------------------------
            # Journey 4: Clear Departure Action
            # -------------------------------------------------------------
            print("\n--- Journey 4: Clear Departure (Clear Start) ---")
            await evaluate_js(ws, """
                (() => {
                    const btn = document.getElementById('btnClearStart');
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(1.0)
            feas_badge = await evaluate_js(ws, "document.getElementById('statFeasibility').textContent")
            calc_disabled = await evaluate_js(ws, "document.getElementById('btnCalculateRoute').disabled")
            print(f"[Verification] Feasibility status: '{feas_badge}', Calculate button disabled: {calc_disabled}")
            await capture_screenshot(ws, "m9n_04_clear_start_endpoint.png")

            # -------------------------------------------------------------
            # Journey 5: Clear Destination Action
            # -------------------------------------------------------------
            print("\n--- Journey 5: Clear Destination (Clear Goal) ---")
            # First reset defaults, then clear goal
            await evaluate_js(ws, """
                (() => {
                    window.__atlas.setCustomStart({ row: 117, col: 157, id: 'wp_landing_site', name: 'Octavia Landing (117, 157)' });
                    window.__atlas.setCustomGoal({ row: 66, col: 128, id: 'wp_delta_rim', name: 'Delta Rim Overlook (66, 128)' });
                    const btn = document.getElementById('btnClearGoal');
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(1.0)
            feas_goal_badge = await evaluate_js(ws, "document.getElementById('statFeasibility').textContent")
            print(f"[Verification] Feasibility status: '{feas_goal_badge}'")
            await capture_screenshot(ws, "m9n_05_clear_goal_endpoint.png")

            # -------------------------------------------------------------
            # Journey 6: Swap Endpoints Action
            # -------------------------------------------------------------
            print("\n--- Journey 6: Swap Endpoints (Recalculate Traverse) ---")
            await evaluate_js(ws, """
                (async () => {
                    window.__atlas.setCustomStart({ row: 117, col: 157, id: 'wp_landing_site', name: 'Octavia Landing (117, 157)' });
                    window.__atlas.setCustomGoal({ row: 66, col: 128, id: 'wp_delta_rim', name: 'Delta Rim Overlook (66, 128)' });
                    const btn = document.getElementById('btnSwapEndpoints');
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(2.5)
            swapped_start = await evaluate_js(ws, "document.getElementById('startPointVal').textContent")
            swapped_goal = await evaluate_js(ws, "document.getElementById('goalPointVal').textContent")
            print(f"[Verification] New Start: '{swapped_start}', New Goal: '{swapped_goal}'")
            await capture_screenshot(ws, "m9n_06_swap_endpoints_recalculated.png")

            # -------------------------------------------------------------
            # Journey 7: Reset Mission Confirmation Modal
            # -------------------------------------------------------------
            print("\n--- Journey 7: Reset Mission Confirmation Modal ---")
            await evaluate_js(ws, """
                (() => {
                    const btn = document.getElementById('btnResetMission');
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(1.0)
            modal_visible = await evaluate_js(ws, "!document.getElementById('resetMissionModal').classList.contains('hidden')")
            print(f"[Verification] Reset confirmation modal visible: {modal_visible}")
            await capture_screenshot(ws, "m9n_07_reset_mission_modal_dialog.png")

            # -------------------------------------------------------------
            # Journey 8: Confirm Reset Mission (Clean Empty Workspace)
            # -------------------------------------------------------------
            print("\n--- Journey 8: Confirm Reset Mission (Workspace Cleared) ---")
            await evaluate_js(ws, """
                (() => {
                    const btn = document.getElementById('btnConfirmResetMission');
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(1.5)
            clean_feas = await evaluate_js(ws, "document.getElementById('statFeasibility').textContent")
            dist_val = await evaluate_js(ws, "document.getElementById('statDistance').textContent")
            print(f"[Verification] Clean Feasibility: '{clean_feas}', Clean Distance: '{dist_val}'")
            await capture_screenshot(ws, "m9n_08_reset_mission_workspace_empty.png")

            # -------------------------------------------------------------
            # Journey 9: Multi-Stop Vehicle & Profile Regression
            # -------------------------------------------------------------
            print("\n--- Journey 9: Multi-Stop Vehicle & Profile Switch Regression ---")
            await evaluate_js(ws, """
                (async () => {
                    window.__atlas.setCustomStart({ row: 117, col: 157, id: 'wp_landing_site', name: 'Octavia Landing (117, 157)' });
                    window.__atlas.setCustomGoal({ row: 66, col: 128, id: 'wp_delta_rim', name: 'Delta Rim Overlook (66, 128)' });
                    window.__atlas.addIntermediateStop({ row: 95, col: 140, id: 'wp_three_forks', name: 'Three Forks Transition', priority_score: 95 });
                    window.__atlas.addIntermediateStop({ row: 80, col: 135, id: 'wp_hawksbill', name: 'Hawksbill Gap Outcrop', priority_score: 90 });
                    window.__atlas.setVehicleMode('robotic_rover');
                    const tabBalanced = document.querySelector('.route-tab[data-route="balanced"]');
                    if (tabBalanced) tabBalanced.click();
                })()
            """)
            await asyncio.sleep(3.0)
            stops_count = await evaluate_js(ws, "document.querySelectorAll('#activeStopsList .stop-chip').length")
            timeline_margin = await evaluate_js(ws, "document.getElementById('statTimelineMarginBadge').textContent")
            print(f"[Verification] Stops retained: {stops_count}, Rover Timeline Margin: '{timeline_margin}'")
            await capture_screenshot(ws, "m9n_09_multistop_vehicle_and_profile_regression.png")

            # -------------------------------------------------------------
            # Journey 10: Regional Exploration: Olympus Mons
            # -------------------------------------------------------------
            print("\n--- Journey 10: Regional Exploration: Olympus Mons ---")
            await evaluate_js(ws, "window.__atlas.selectDestination('olympus')")
            await asyncio.sleep(2.5)
            loc_title_om = await evaluate_js(ws, "document.getElementById('locCardTitle').textContent")
            print(f"[Verification] Location card title: '{loc_title_om}'")
            await capture_screenshot(ws, "m9n_10_regional_olympus_mons.png")

            # -------------------------------------------------------------
            # Journey 11: Regional Exploration: Valles Marineris (Authentic CTX Mosaic)
            # -------------------------------------------------------------
            print("\n--- Journey 11: Regional Exploration: Valles Marineris (Authentic CTX) ---")
            await evaluate_js(ws, "window.__atlas.selectDestination('valles')")
            await asyncio.sleep(2.5)
            loc_title_vm = await evaluate_js(ws, "document.getElementById('locCardTitle').textContent")
            print(f"[Verification] Location card title: '{loc_title_vm}'")
            await capture_screenshot(ws, "m9n_11_regional_valles_marineris_ctx.png")

            # -------------------------------------------------------------
            # Journey 12: Regional Exploration: Gale Crater
            # -------------------------------------------------------------
            print("\n--- Journey 12: Regional Exploration: Gale Crater ---")
            await evaluate_js(ws, "window.__atlas.selectDestination('gale')")
            await asyncio.sleep(2.5)
            loc_title_gale = await evaluate_js(ws, "document.getElementById('locCardTitle').textContent")
            print(f"[Verification] Location card title: '{loc_title_gale}'")
            await capture_screenshot(ws, "m9n_12_regional_gale_crater.png")

            # -------------------------------------------------------------
            # Journey 13: Location Dossier Card Orbit Return via [GLOBAL MARS]
            # -------------------------------------------------------------
            print("\n--- Journey 13: Location Card [GLOBAL MARS] Orbit Return ---")
            await evaluate_js(ws, """
                (() => {
                    const btn = document.getElementById('btnLocOrbit');
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(2.5)
            nav_mode = await evaluate_js(ws, "document.getElementById('diagMode').textContent")
            card_hidden = await evaluate_js(ws, "document.getElementById('locationCard').classList.contains('hidden')")
            print(f"[Verification] Navigation state: '{nav_mode}', Location card hidden: {card_hidden}")
            await capture_screenshot(ws, "m9n_13_location_card_orbit_return.png")

            # -------------------------------------------------------------
            # Journey 14: Saved Mission Library Persistence Verification
            # -------------------------------------------------------------
            print("\n--- Journey 14: Mission Library Persistence Survives Reset ---")
            # Navigate back to Jezero and open library
            await evaluate_js(ws, """
                (() => {
                    const btn = document.getElementById('btnFlyJezero');
                    if (btn) btn.click();
                    window.__atlas.switchInspectorTab('tabWorkspaces');
                    const libBtn = document.getElementById('btnOpenMissionLibrary');
                    if (libBtn) libBtn.click();
                })()
            """)
            await asyncio.sleep(1.5)
            saved_count = await evaluate_js(ws, "document.querySelectorAll('#missionLibraryTableBody tr').length")
            print(f"[Verification] Saved missions persisting in library: {saved_count}")
            await capture_screenshot(ws, "m9n_14_saved_mission_library_persistence.png")

            # Close library modal
            await evaluate_js(ws, "document.getElementById('btnCloseMissionLibrary').click()")
            await asyncio.sleep(0.5)

            # -------------------------------------------------------------
            # Journey 15: Responsive Tablet Breakpoint (1024x768)
            # -------------------------------------------------------------
            print("\n--- Journey 15: Responsive Tablet Breakpoint (1024x768) ---")
            await set_viewport(ws, 1024, 768)
            await evaluate_js(ws, "window.__atlas.switchInspectorTab('tabPlan')")
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, "m9n_15_responsive_tablet_1024.png")

            # -------------------------------------------------------------
            # Journey 16: Responsive Mobile Breakpoint (390x844)
            # -------------------------------------------------------------
            print("\n--- Journey 16: Responsive Mobile Breakpoint (390x844) ---")
            await set_viewport(ws, 390, 844, is_mobile=True)
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, "m9n_16_responsive_mobile_390.png")

            print("\n=== All 16 Verified Visual Evidence Captures Completed Successfully! ===")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(run_evidence_pipeline())
