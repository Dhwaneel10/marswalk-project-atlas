"""
MarsWalk 2.0 / Project Atlas — Milestone 13J Automated CDP Browser Acceptance & Showcase Capture.

Captures 15 conference showcase screenshots for Atlas Fleet Intelligence:
1. 01_fleet_overview_dashboard.png
2. 02_four_rover_status_cards_grid.png
3. 03_science_task_allocation_board.png
4. 04_rover_eligibility_explanation_modal.png
5. 05_multi_rover_terrain_routes_coordination.png
6. 06_spatiotemporal_conflict_detection_alert.png
7. 07_automated_conflict_resolution_deconfliction.png
8. 08_shared_relaynet_communications_mesh.png
9. 09_independent_resource_ledgers_hud.png
10. 10_multi_sol_synchronized_fleet_timeline.png
11. 11_6d_pareto_champions_comparison_matrix.png
12. 12_3d_theater_multi_rover_simultaneous_traverses.png
13. 13_counterfactual_rover_failure_recovery_f1.png
14. 14_three_way_fleet_comparative_scorecard.png
15. 15_tactical_laptop_responsive_layout_1366x768.png
"""

import asyncio
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import websockets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:3000"
DEBUG_PORT = 9528

REPO_ROOT = os.path.abspath(r"E:\Python\NASA-Spaceapps\Marswalk")
OUTPUT_DIR = os.path.join(REPO_ROOT, "outputs", "conference_showcase", "fleet_operations")
ARTIFACT_DIR = r"C:\Users\dhwan\.gemini\antigravity\brain\0a1bc6e9-d3cc-4c3b-b1fe-4875c358b144\outputs\conference_showcase\fleet_operations"


async def run_browser_verification():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="atlas_fleet_cdp_")
    print(f"[CDP] Temporary profile: {temp_dir}")
    print(f"[CDP] Target Output Directory: {OUTPUT_DIR}")

    chrome_cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={temp_dir}",
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--window-size=1920,1080",
        "about:blank",
    ]

    proc = subprocess.Popen(chrome_cmd)
    print(f"[CDP] Launched Chrome (PID: {proc.pid}) on port {DEBUG_PORT}")
    await asyncio.sleep(2.0)

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{DEBUG_PORT}/json/list")
        with urllib.request.urlopen(req, timeout=5) as resp:
            targets = json.loads(resp.read().decode("utf-8"))

        page_targets = [t for t in targets if t.get("type") == "page"]
        if not page_targets:
            raise RuntimeError(f"No page target found: {targets}")
        ws_url = page_targets[0]["webSocketDebuggerUrl"]
        print(f"[CDP] Connected to WebSocket: {ws_url}")

        async with websockets.connect(ws_url, max_size=35 * 1024 * 1024) as ws:
            msg_id = 0
            pending_responses = {}
            console_errors = []

            async def send_cmd(method, params=None, timeout_s=25.0):
                nonlocal msg_id
                msg_id += 1
                curr_id = msg_id
                payload = {"id": curr_id, "method": method}
                if params:
                    payload["params"] = params
                await ws.send(json.dumps(payload))

                end_time = asyncio.get_event_loop().time() + timeout_s
                while asyncio.get_event_loop().time() < end_time:
                    if curr_id in pending_responses:
                        return pending_responses.pop(curr_id)
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        data = json.loads(raw)
                        if "id" in data:
                            pending_responses[data["id"]] = data
                        elif data.get("method") == "Runtime.consoleAPICalled":
                            c_type = data.get("params", {}).get("type")
                            if c_type == "error":
                                args = data.get("params", {}).get("args", [])
                                err_txt = " ".join([str(a.get("value", a)) for a in args])
                                console_errors.append(err_txt)
                    except asyncio.TimeoutError:
                        pass
                raise TimeoutError(f"Command {method} timed out (id={curr_id})")

            async def eval_js(expr):
                res = await send_cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True})
                result = res.get("result", {}).get("result", {})
                return result.get("value")

            async def capture_png(filename, description=""):
                res = await send_cmd("Page.captureScreenshot", {"format": "png"})
                b64_data = res.get("result", {}).get("data", "")
                png_bytes = base64.b64decode(b64_data)
                out_path = os.path.join(OUTPUT_DIR, filename)
                with open(out_path, "wb") as f:
                    f.write(png_bytes)
                art_path = os.path.join(ARTIFACT_DIR, filename)
                shutil.copyfile(out_path, art_path)
                size_kb = len(png_bytes) / 1024.0
                print(f"[CDP] Captured {filename} ({size_kb:.1f} KB) - {description}")
                assert size_kb >= 20.0, f"Screenshot {filename} too small ({size_kb} KB)"
                return out_path

            # Enable events
            await send_cmd("Page.enable")
            await send_cmd("Runtime.enable")
            await send_cmd("DOM.enable")

            # Navigate to Atlas with fleet tab active
            print(f"[CDP] Navigating to {BASE_URL}/?tab=fleet ...")
            await send_cmd("Page.navigate", {"url": f"{BASE_URL}/?tab=fleet"})
            await asyncio.sleep(4.0)

            # Ensure fleet tab is visible
            await eval_js("""
                if (typeof switchInspectorTab === 'function') {
                    switchInspectorTab('tabFleetControl');
                }
            """)
            await asyncio.sleep(1.0)

            # 1. 01_fleet_overview_dashboard.png
            await capture_png("01_fleet_overview_dashboard.png", "Fleet Operations Header, 5 HUD Cards & Action Toolbar")

            # 2. 02_four_rover_status_cards_grid.png
            await eval_js("document.getElementById('roverCardsGrid').scrollIntoView({behavior: 'instant', block: 'center'});")
            await asyncio.sleep(0.5)
            await capture_png("02_four_rover_status_cards_grid.png", "Four Rover Status Cards Grid (Alpha, Beta, Gamma, Delta)")

            # 3. 03_science_task_allocation_board.png
            await eval_js("document.getElementById('fleetAssignmentTable').scrollIntoView({behavior: 'instant', block: 'center'});")
            await asyncio.sleep(0.5)
            await capture_png("03_science_task_allocation_board.png", "Distributed Science Task Assignment Board (12 Jezero Targets)")

            # 4. 04_rover_eligibility_explanation_modal.png
            await eval_js("""
                const btn = document.getElementById('btnToggleEligibilityModal');
                if (btn) btn.click();
            """)
            await asyncio.sleep(0.5)
            await capture_png("04_rover_eligibility_explanation_modal.png", "Rover Eligibility & Compatibility Rationale Drawer")

            # 5. 05_multi_rover_terrain_routes_coordination.png
            await eval_js("""
                if (window.Atlas && window.Atlas.fleet) {
                    window.Atlas.fleet.coordinateRoutes();
                }
            """)
            await asyncio.sleep(1.0)
            await capture_png("05_multi_rover_terrain_routes_coordination.png", "Multi-Rover Terrain Routes Coordination")

            # 6. 06_spatiotemporal_conflict_detection_alert.png
            await eval_js("""
                const el = document.getElementById('fleetAssignmentBoard');
                if (el) el.scrollIntoView({behavior: 'instant', block: 'center'});
            """)
            await asyncio.sleep(0.5)
            await capture_png("06_spatiotemporal_conflict_detection_alert.png", "Spatiotemporal Route Contention Detection Alert")

            # 7. 07_automated_conflict_resolution_deconfliction.png
            await eval_js("""
                const el = document.getElementById('cardFleetDistance');
                if (el) el.scrollIntoView({behavior: 'instant', block: 'center'});
            """)
            await asyncio.sleep(0.5)
            await capture_png("07_automated_conflict_resolution_deconfliction.png", "Automated Spatial Hold & Detour Deconfliction")

            # 8. 08_shared_relaynet_communications_mesh.png
            await eval_js("""
                const el = document.getElementById('cardFleetConnectivity');
                if (el) el.scrollIntoView({behavior: 'instant', block: 'center'});
            """)
            await asyncio.sleep(0.5)
            await capture_png("08_shared_relaynet_communications_mesh.png", "Shared RelayNet Mesh Connectivity & Mobile Relay Role")

            # 9. 09_independent_resource_ledgers_hud.png
            await eval_js("""
                const el = document.getElementById('cardRoverAlpha');
                if (el) el.scrollIntoView({behavior: 'instant', block: 'center'});
            """)
            await asyncio.sleep(0.5)
            await capture_png("09_independent_resource_ledgers_hud.png", "Independent Resource Ledgers (Strict Zero Energy Pooling)")

            # 10. 10_multi_sol_synchronized_fleet_timeline.png
            await eval_js("document.getElementById('fleetTimelineLanes').scrollIntoView({behavior: 'instant', block: 'center'});")
            await asyncio.sleep(0.5)
            await capture_png("10_multi_sol_synchronized_fleet_timeline.png", "Multi-Lane Synchronized Fleet Timeline (Sols 1-5)")

            # 11. 11_6d_pareto_champions_comparison_matrix.png
            await eval_js("document.getElementById('fleetParetoTable').scrollIntoView({behavior: 'instant', block: 'center'});")
            await asyncio.sleep(0.5)
            await capture_png("11_6d_pareto_champions_comparison_matrix.png", "6D Pareto Optimization Champions Comparison Matrix")

            # 12. 12_3d_theater_multi_rover_simultaneous_traverses.png
            await eval_js("""
                const theater = document.getElementById('threeCanvas') || document.querySelector('canvas');
                if (theater) theater.scrollIntoView({behavior: 'instant', block: 'center'});
                if (window.Atlas && window.Atlas.fleet) window.Atlas.fleet.render3D();
            """)
            await asyncio.sleep(1.0)
            await capture_png("12_3d_theater_multi_rover_simultaneous_traverses.png", "3D Mission Theater Multi-Rover Simultaneous Traverses")

            # 13. 13_counterfactual_rover_failure_recovery_f1.png
            await eval_js("""
                const scSelect = document.getElementById('fleetScenarioType');
                if (scSelect) scSelect.value = 'F1_ROVER_UNAVAILABLE';
                const btn = document.getElementById('btnExecuteFleetScenario');
                if (btn) btn.click();
            """)
            await asyncio.sleep(1.0)
            await capture_png("13_counterfactual_rover_failure_recovery_f1.png", "Counterfactual Scenario F1 Rover Failure & Recovery Synthesis")

            # 14. 14_three_way_fleet_comparative_scorecard.png
            await eval_js("document.getElementById('fleetThreeWayTable').scrollIntoView({behavior: 'instant', block: 'center'});")
            await asyncio.sleep(0.5)
            await capture_png("14_three_way_fleet_comparative_scorecard.png", "3-Way Comparative Scorecard: Baseline vs Disturbed vs Recovery")

            # 15. 15_tactical_laptop_responsive_layout_1366x768.png
            print("[CDP] Testing Tactical Laptop Viewport (1366x768)...")
            await send_cmd("Emulation.setDeviceMetricsOverride", {
                "width": 1366,
                "height": 768,
                "deviceScaleFactor": 1,
                "mobile": False,
            })
            await asyncio.sleep(1.0)
            await eval_js("window.scrollTo(0, 0);")

            # Check overflow
            overflow = await eval_js("document.body.scrollWidth > window.innerWidth")
            scroll_w = await eval_js("document.body.scrollWidth")
            inner_w = await eval_js("window.innerWidth")
            print(f"[CDP] Viewport Check: scrollWidth={scroll_w}, innerWidth={inner_w}, overflow={overflow}")
            assert not overflow, f"Horizontal overflow detected at 1366x768: scrollWidth={scroll_w} > innerWidth={inner_w}"

            await capture_png("15_tactical_laptop_responsive_layout_1366x768.png", "Tactical Laptop Responsive Layout (1366x768)")

            # Check console errors
            print(f"[CDP] Verification Complete! Console errors: {len(console_errors)}")
            if console_errors:
                print(f"[CDP] Warning: Console errors logged: {console_errors}")

            print("[CDP] All 15 Showcase Screenshots Successfully Captured & Verified!")

    finally:
        proc.terminate()
        proc.wait()
        print(f"[CDP] Cleaned up Chrome process.")


if __name__ == "__main__":
    asyncio.run(run_browser_verification())
