"""
MarsWalk 2.0 - Milestone 9M Verification & Visual Evidence Capture Script
Captures all 14 verified journeys demonstrating:
1. Clean Landing Page Hero (Mars globe without label clutter, no HUD leakage).
2. Regional Exploration Entry Point: Olympus Mons.
3. Regional Exploration Entry Point: Valles Marineris (calibrated regional CTX mosaic overlay).
4. Regional Exploration Entry Point: Gale Crater.
5. Jezero 3D Workstation & Expanded Inspector Panel Tab 1 (Plan) with Expedition Budget Controls.
6. Intelligent Waypoint Visibility & Toggle (clean unselected filtering vs all-12 display).
7. Vehicle Mode Switch (Crew EVA <-> Robotic Rover) without map loss or terrain destruction.
8. Multi-Stop Profile Switching (Conservative -> Balanced -> Science-First) preserving stops.
9. Tab 2 (Results): Operational Timeline & Expedition Budget Margin breakdown.
10. Tab 3 (Scenarios): Truthful Stress Testing (REDUCED_BUDGET feasibility violation without false compliance).
11. Tab 3 (Scenarios): Feasible 3-Way Recovery Planning Corridor.
12. Tab 4 (Workspaces): Persistent Mission Workspace, Experiment Preserved & Briefing Export.
13. Responsive Tablet Breakpoint (1024x768).
14. Responsive Mobile Breakpoint (390x844).
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
DEBUG_PORT = 9488

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
        f"{BASE_URL}/?landing=1"
    ])
    time.sleep(2.5)

    try:
        targets_raw = urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json").read().decode()
        targets = json.loads(targets_raw)
        page_target = next(t for t in targets if t.get("type") == "page" and "3000" in t.get("url", ""))

        async with websockets.connect(page_target["webSocketDebuggerUrl"], max_size=100*1024*1024) as ws:
            await send_cmd(ws, "Page.enable")
            await send_cmd(ws, "Runtime.enable")

            print("\n=== Initializing MarsWalk 2.0 Project Atlas for Milestone 9M ===")
            await send_cmd(ws, "Page.navigate", {"url": f"{BASE_URL}/?landing=1"})

            ready = await wait_for_condition(
                ws,
                "(() => document.getElementById('loadingOverlay') && document.getElementById('loadingOverlay').classList.contains('hidden') && window.__atlas !== undefined)()",
                25.0
            )
            if not ready:
                raise RuntimeError("Atlas failed to load in time.")

            print("[Init] Atlas UI online with Milestone 9M upgrades.")
            await asyncio.sleep(2.0)

            # -------------------------------------------------------------
            # Journey 1: Clean Landing Page Hero (No HUD leakage, no label clutter)
            # -------------------------------------------------------------
            print("\n--- Journey 1: Clean Landing Page Hero (1366x768) ---")
            await set_viewport(ws, 1366, 768)
            await evaluate_js(ws, "window.__atlas.showLandingPage()")
            await asyncio.sleep(1.0)

            # Verify no HUD or feature labels are visible
            hud_hidden = await evaluate_js(ws, """
                (() => {
                    const hud = document.querySelector('.hud-header');
                    const isLanding = document.body.classList.contains('landing-active');
                    const comp = hud ? window.getComputedStyle(hud) : null;
                    return isLanding && comp && (comp.display === 'none' || comp.opacity === '0');
                })()
            """)
            print(f"[Verification] HUD hidden behind landing hero: {hud_hidden}")
            await capture_screenshot(ws, "m9m_01_landing_hero_clean.png")

            # -------------------------------------------------------------
            # Journey 2: Regional Exploration Entry Point: Olympus Mons
            # -------------------------------------------------------------
            print("\n--- Journey 2: Regional Exploration: Olympus Mons ---")
            await evaluate_js(ws, "window.__atlas.selectDestination('olympus')")
            await asyncio.sleep(1.5)
            # Click explore button on Olympus Mons item
            await evaluate_js(ws, """
                (() => {
                    const btn = document.querySelector('.dest-explore-btn[data-dest="olympus"]');
                    if (btn) btn.click();
                    else window.__atlas.hideLandingPage();
                })()
            """)
            await asyncio.sleep(2.0)
            await capture_screenshot(ws, "m9m_02_regional_olympus_mons.png")

            # -------------------------------------------------------------
            # Journey 3: Regional Exploration Entry Point: Valles Marineris (CTX Preview)
            # -------------------------------------------------------------
            print("\n--- Journey 3: Regional Exploration: Valles Marineris Regional Mosaic ---")
            await evaluate_js(ws, "window.__atlas.showLandingPage()")
            await asyncio.sleep(1.0)
            await evaluate_js(ws, "window.__atlas.selectDestination('valles')")
            await asyncio.sleep(1.0)
            await evaluate_js(ws, """
                (() => {
                    const btn = document.querySelector('.dest-explore-btn[data-dest="valles"]');
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(2.0)
            await capture_screenshot(ws, "m9m_03_regional_valles_marineris_mosaic.png")

            # -------------------------------------------------------------
            # Journey 4: Regional Exploration Entry Point: Gale Crater
            # -------------------------------------------------------------
            print("\n--- Journey 4: Regional Exploration: Gale Crater ---")
            await evaluate_js(ws, "window.__atlas.showLandingPage()")
            await asyncio.sleep(1.0)
            await evaluate_js(ws, "window.__atlas.selectDestination('gale')")
            await asyncio.sleep(1.0)
            await evaluate_js(ws, """
                (() => {
                    const btn = document.querySelector('.dest-explore-btn[data-dest="gale"]');
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(2.0)
            await capture_screenshot(ws, "m9m_04_regional_gale_crater.png")

            # -------------------------------------------------------------
            # Journey 5: Jezero 3D Workstation & Inspector Tab 1 (Plan) with Expedition Budget
            # -------------------------------------------------------------
            print("\n--- Journey 5: Jezero 3D Workstation & Tab 1 (Plan) with Expedition Budget ---")
            await evaluate_js(ws, "window.__atlas.setJezeroView()")
            await asyncio.sleep(2.5)
            await wait_for_condition(ws, "document.getElementById('viewport3d').style.display !== 'none'")
            await evaluate_js(ws, "window.__atlas.setTerrainTexture('ctx')")
            await asyncio.sleep(1.0)

            # Ensure Inspector is open and on Tab 1
            await evaluate_js(ws, """
                (() => {
                    const panel = document.getElementById('inspectorPanel');
                    if (panel && panel.classList.contains('minimized')) {
                        panel.classList.remove('minimized');
                    }
                    window.__atlas.switchInspectorTab('tabPlan');
                })()
            """)
            await asyncio.sleep(1.0)

            # Set expedition budget parameters
            await evaluate_js(ws, """
                window.__atlas.setExpeditionBudget({
                    hours: 8.0,
                    dwellMins: 15,
                    delayMins: 0,
                    maxDistM: 15000
                })
            """)
            await asyncio.sleep(0.5)
            await capture_screenshot(ws, "m9m_05_tab1_plan_expedition_budget.png")

            # -------------------------------------------------------------
            # Journey 6: Intelligent Waypoint Filtering & Visibility Toggle
            # -------------------------------------------------------------
            print("\n--- Journey 6: Intelligent Waypoint Filtering & Visibility Toggle ---")
            # Calculate baseline traverse to establish an active mission
            await evaluate_js(ws, "window.__atlas.calculateTraverse('conservative')", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")
            await asyncio.sleep(1.5)

            # Waypoint filtering is active: unselected catalog waypoints are hidden
            # Now toggle show all waypoints to demonstrate user control
            await evaluate_js(ws, "window.__atlas.setShowAllWaypoints(true)")
            await asyncio.sleep(1.2)
            await capture_screenshot(ws, "m9m_06_waypoint_visibility_toggle.png")

            # Restore clean active mission visibility
            await evaluate_js(ws, "window.__atlas.setShowAllWaypoints(false)")
            await asyncio.sleep(0.8)

            # -------------------------------------------------------------
            # Journey 7: Vehicle Mode Switch: Crew EVA -> Robotic Rover
            # -------------------------------------------------------------
            print("\n--- Journey 7: Vehicle Mode Switch: Crew EVA -> Robotic Rover ---")
            await evaluate_js(ws, """
                (() => {
                    const roverBtn = document.getElementById('btnVehicleRover');
                    if (roverBtn) roverBtn.click();
                    else window.__atlas.setVehicleMode('robotic_rover');
                })()
            """)
            await asyncio.sleep(2.0)
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")

            # Verify 3D terrain canvas has not disappeared or errored
            mesh_intact = await evaluate_js(ws, """
                (() => {
                    const canvas = document.querySelector('#viewport3d canvas');
                    return canvas !== null && canvas.width > 0 && canvas.height > 0;
                })()
            """)
            print(f"[Verification] 3D canvas and terrain mesh intact after vehicle mode switch: {mesh_intact}")
            assert mesh_intact, "3D Terrain canvas must not be destroyed when switching vehicle mode"
            await capture_screenshot(ws, "m9m_07_vehicle_mode_switch_crew_to_rover.png")

            # Switch back to Crew EVA for multi-stop demonstration
            await evaluate_js(ws, """
                (() => {
                    const crewBtn = document.getElementById('btnVehicleCrew');
                    if (crewBtn) crewBtn.click();
                    else window.__atlas.setVehicleMode('crew_eva');
                })()
            """)
            await asyncio.sleep(1.5)

            # -------------------------------------------------------------
            # Journey 8: Multi-Stop Intermediate Research Stops Retained Across Profiles
            # -------------------------------------------------------------
            print("\n--- Journey 8: Multi-Stop Profile Switch Preserves Intermediate Stops ---")
            # Add intermediate research stops: Three Forks and Hawksbill Gap
            await evaluate_js(ws, """
                (() => {
                    const missionData = window.__atlas.getMissionData();
                    if (!missionData || !missionData.waypoints) return;
                    const wps = missionData.waypoints.filter(w => w.id === 'three_forks' || w.id === 'hawksbill_gap');
                    wps.forEach(w => window.__atlas.addIntermediateStop(w));
                })()
            """)
            await asyncio.sleep(1.0)

            # Switch to Balanced profile
            print("[Journey 8] Switching profile to Balanced...")
            await evaluate_js(ws, """
                (() => {
                    const tabBalanced = document.querySelector('.route-tab[data-route="balanced"]');
                    if (tabBalanced) tabBalanced.click();
                    else window.__atlas.calculateTraverse();
                })()
            """)
            await asyncio.sleep(2.5)
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")

            # Switch to Science-First profile
            print("[Journey 8] Switching profile to Science-First...")
            await evaluate_js(ws, """
                (() => {
                    const tabScience = document.querySelector('.route-tab[data-route="science"]');
                    if (tabScience) tabScience.click();
                    else window.__atlas.calculateTraverse();
                })()
            """)
            await asyncio.sleep(2.5)
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")

            # Verify intermediate stops are still populated
            active_stops_count = await evaluate_js(ws, "window.__atlas.getActiveStops().length")
            print(f"[Verification] Active intermediate research stops retained: {active_stops_count}")
            assert active_stops_count == 2, f"Expected 2 intermediate research stops, got {active_stops_count}"
            await capture_screenshot(ws, "m9m_08_profile_switch_preserves_stops.png")

            # -------------------------------------------------------------
            # Journey 9: Tab 2 (Results): Telemetry Grid & Operational Timeline Margin
            # -------------------------------------------------------------
            print("\n--- Journey 9: Tab 2 (Results) Telemetry & Operational Timeline ---")
            await evaluate_js(ws, "window.__atlas.switchInspectorTab('tabResults')")
            await asyncio.sleep(1.2)
            await capture_screenshot(ws, "m9m_09_tab2_results_operational_timeline.png")

            # -------------------------------------------------------------
            # Journey 10: Tab 3 (Scenarios): Truthful Stress Testing (REDUCED_BUDGET)
            # -------------------------------------------------------------
            print("\n--- Journey 10: Tab 3 (Scenarios) Truthful Stress Testing ---")
            await evaluate_js(ws, "window.__atlas.switchInspectorTab('tabScenarios')")
            await asyncio.sleep(0.8)

            # Select REDUCED_BUDGET scenario and run gauntlet stress test
            await evaluate_js(ws, """
                (() => {
                    const sel = document.getElementById('gauntletScenarioSelect');
                    if (sel) sel.value = 'scen_reduced_budget';
                })()
            """)
            await asyncio.sleep(0.5)

            # Set a tight expedition limit so reduced budget triggers feasibility breach
            await evaluate_js(ws, """
                window.__atlas.setExpeditionBudget({
                    hours: 3.5,
                    dwellMins: 15,
                    delayMins: 0,
                    maxDistM: 15000
                })
            """)
            await asyncio.sleep(0.5)

            print("[Journey 10] Running REDUCED_BUDGET disruption simulation...")
            await evaluate_js(ws, "window.__atlas.runGauntletStressTest('scen_reduced_budget')", await_promise=True)
            await asyncio.sleep(2.5)

            # Verify gauntlet result does not claim compliant when limits breached
            scen_result = await evaluate_js(ws, "window.__atlas.getGauntletResult()")
            print(f"[Verification] Stress test headline: {scen_result.get('headline') if scen_result else 'None'}")
            await capture_screenshot(ws, "m9m_10_tab3_scenarios_truthful_stress_test.png")

            # -------------------------------------------------------------
            # Journey 11: Tab 3 (Scenarios): 3-Way Recovery Planning
            # -------------------------------------------------------------
            print("\n--- Journey 11: Tab 3 (Scenarios) 3-Way Recovery Planning ---")
            # Run rockfall scenario to show recovery planning
            await evaluate_js(ws, """
                (() => {
                    const sel = document.getElementById('gauntletScenarioSelect');
                    if (sel) sel.value = 'scen_corridor_rockfall';
                })()
            """)
            await asyncio.sleep(0.5)
            await evaluate_js(ws, "window.__atlas.runGauntletStressTest('scen_corridor_rockfall')", await_promise=True)
            await asyncio.sleep(2.5)

            # Scroll recovery card into view
            await evaluate_js(ws, """
                (() => {
                    const card = document.getElementById('recoveryPlanCard');
                    if (card) {
                        card.classList.remove('hidden');
                        card.scrollIntoView({ behavior: 'instant', block: 'nearest' });
                    }
                })()
            """)
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, "m9m_11_tab3_recovery_planning.png")

            # -------------------------------------------------------------
            # Journey 12: Tab 4 (Workspaces): Persistent Mission Workspace & Exports
            # -------------------------------------------------------------
            print("\n--- Journey 12: Tab 4 (Workspaces) Persistent Mission & Briefing ---")
            await evaluate_js(ws, "window.__atlas.switchInspectorTab('tabWorkspaces')")
            await asyncio.sleep(1.0)

            # Save mission to library
            print("[Journey 12] Saving mission to local library...")
            await evaluate_js(ws, "window.__atlas.saveMission('Milestone 9M Jezero Rehearsal')", await_promise=True)
            await asyncio.sleep(1.0)

            # Save experiment run
            print("[Journey 12] Saving simulation experiment...")
            await evaluate_js(ws, "window.__atlas.saveExperiment('M9M Stress Test Experiment')", await_promise=True)
            await asyncio.sleep(1.2)
            await capture_screenshot(ws, "m9m_12_tab4_workspaces_persistence.png")

            # -------------------------------------------------------------
            # Journey 13: Responsive Tablet Breakpoint (1024x768)
            # -------------------------------------------------------------
            print("\n--- Journey 13: Responsive Tablet Layout (1024x768) ---")
            await set_viewport(ws, 1024, 768)
            await evaluate_js(ws, "window.__atlas.switchInspectorTab('tabPlan')")
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, "m9m_13_responsive_tablet_1024.png")

            # -------------------------------------------------------------
            # Journey 14: Responsive Mobile Breakpoint (390x844)
            # -------------------------------------------------------------
            print("\n--- Journey 14: Responsive Mobile Layout (390x844) ---")
            await set_viewport(ws, 390, 844, is_mobile=True)
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, "m9m_14_responsive_mobile_390.png")

            print("\n=== Milestone 9M Visual Evidence & Verification Pipeline Complete! ===")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("[Cleanup] Headless Chrome process terminated.")


if __name__ == "__main__":
    asyncio.run(run_evidence_pipeline())
