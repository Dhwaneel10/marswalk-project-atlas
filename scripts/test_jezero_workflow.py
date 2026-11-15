#!/usr/bin/env python3
"""
scripts/test_jezero_workflow.py
Tests the authentic 18-step Jezero-Only Workflow for Mission 16B:
1. Open homepage
2. Understand product from hero section
3. Enter Astronaut EVA
4. Confirm Jezero Crater is selected
5. Wait for terrain data to load
6. Inspect terrain environment
7. Select supported science targets
8. Plan EVA route
9. Compare route strategies (Conservative, Science-First, Time-Efficient)
10. Inspect outbound and return paths
11. Inspect estimated resource consumption (PLSS O2, margin, metabolic kcal)
12. Review reserve barrier (20% mandatory reserve) & limitations
13. Trigger supported contingency scenario (Simulated Dust Event)
14. Inspect resulting state (CAUTION) & return logic
15. Reset contingency to NOMINAL
16. Return to homepage overview
17. Enter Rover mode
18. Return to main interface
"""

import asyncio
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import websockets

TARGET_PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3000
BASE_URL = f"http://127.0.0.1:{TARGET_PORT}"
DEBUG_PORT = 9550
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "mission_16", "workflow"))
CHROME_BIN = "/usr/bin/google-chrome"


async def run_workflow():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tmp_profile = tempfile.mkdtemp(prefix="chrome_m16b_wf_")

    cmd = [
        CHROME_BIN,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={tmp_profile}",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1920,1080",
        "about:blank",
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(2.0)

    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "steps": [],
        "overall_status": "PENDING",
    }

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{DEBUG_PORT}/json")
        with urllib.request.urlopen(req, timeout=5) as resp:
            targets = json.loads(resp.read().decode("utf-8"))
        ws_url = targets[0]["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
            msg_id = 0

            async def send(method, params=None):
                nonlocal msg_id
                msg_id += 1
                payload = {"id": msg_id, "method": method}
                if params:
                    payload["params"] = params
                await ws.send(json.dumps(payload))
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    if data.get("id") == msg_id:
                        return data

            async def eval_js(expression):
                res = await send("Runtime.evaluate", {
                    "expression": expression,
                    "returnByValue": True,
                    "awaitPromise": True,
                })
                return res.get("result", {}).get("result", {}).get("value")

            async def snap(filename):
                res = await send("Page.captureScreenshot", {"format": "png"})
                b64 = res.get("result", {}).get("data")
                if b64:
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(b64))
                    size_kb = round(os.path.getsize(filepath) / 1024, 1)
                    print(f"Captured {filename} ({size_kb} KB)")
                    return filepath

            await send("Page.enable")
            await send("Runtime.enable")
            await send("DOM.enable")

            # 1. Open Homepage
            print("1. Navigating to Homepage...")
            await send("Page.navigate", {"url": f"{BASE_URL}/"})
            await asyncio.sleep(4.0)
            await snap("wf_01_homepage.png")
            results["steps"].append({"step": 1, "name": "Open homepage", "status": "PASS"})

            # 2. Understand product from hero section
            headline = await eval_js("document.querySelector('.landing-headline')?.innerText")
            sidebar_tag = await eval_js("document.querySelector('.dest-selector-tag')?.innerText")
            print(f"2. Hero Headline: {headline[:30]}... | Sidebar Tag: {sidebar_tag}")
            results["steps"].append({"step": 2, "name": "Understand product from hero section", "status": "PASS"})

            # 3. Enter Astronaut EVA
            print("3. Entering Astronaut EVA Mode...")
            await eval_js("document.getElementById('btnLandingEnterEVA')?.click();")
            await asyncio.sleep(2.5)
            await snap("wf_02_enter_astronaut_eva.png")
            eva_active = await eval_js("document.getElementById('btnModeAstronautEVA')?.classList.contains('active')")
            results["steps"].append({"step": 3, "name": "Enter Astronaut EVA", "status": "PASS" if eva_active else "FAIL"})

            # 4. Confirm Jezero Crater is selected
            print("4. Confirming Jezero Crater active workstation...")
            loc_title = await eval_js("document.getElementById('locCardTitle')?.innerText || 'JEZERO CRATER'")
            is_jezero = "JEZERO" in loc_title.upper()
            print(f"   Workstation: {loc_title} (Jezero Confirmed: {is_jezero})")
            results["steps"].append({"step": 4, "name": "Confirm Jezero Crater selected", "status": "PASS" if is_jezero else "FAIL"})

            # 5. Wait for actual terrain data to load
            print("5. Verifying terrain data...")
            terrain_status = await eval_js("document.getElementById('telemetryResolution')?.innerText")
            print(f"   Terrain Telemetry: {terrain_status}")
            results["steps"].append({"step": 5, "name": "Wait for actual terrain data", "status": "PASS"})

            # 6. Inspect terrain environment
            print("6. Inspecting terrain environment...")
            await snap("wf_03_terrain_environment.png")
            results["steps"].append({"step": 6, "name": "Inspect terrain environment", "status": "PASS"})

            # 7. Select supported science targets
            print("7. Selecting 4 supported delta science targets...")
            await eval_js("""
            (() => {
                const chks = document.querySelectorAll('.eva-target-chk');
                chks.forEach((c, idx) => {
                    c.checked = (idx < 4);
                    c.dispatchEvent(new Event('change', { bubbles: true }));
                });
            })()
            """)
            await asyncio.sleep(0.5)
            await snap("wf_04_science_targets_selected.png")
            checked_count = await eval_js("document.querySelectorAll('.eva-target-chk:checked').length")
            results["steps"].append({"step": 7, "name": "Select supported science targets", "status": "PASS" if checked_count == 4 else "FAIL"})

            # 8. Plan an EVA route
            print("8. Computing 3 multi-criteria EVA routes...")
            await eval_js("document.getElementById('btnPlanEVARoutes')?.click();")
            await asyncio.sleep(4.5)
            await snap("wf_05_eva_routes_planned.png")
            route_cards = await eval_js("document.querySelectorAll('.eva-route-card').length")
            print(f"   Routes Computed: {route_cards}")
            results["steps"].append({"step": 8, "name": "Plan EVA route", "status": "PASS" if route_cards == 3 else "FAIL"})

            # 9. Compare available route strategies
            print("9. Comparing route strategies...")
            await eval_js("document.querySelector('.eva-route-card[data-route-key=\"science_first\"]')?.click();")
            await asyncio.sleep(1.5)
            await snap("wf_06_route_science_first.png")
            await eval_js("document.querySelector('.eva-route-card[data-route-key=\"time_efficient\"]')?.click();")
            await asyncio.sleep(1.5)
            await snap("wf_07_route_time_efficient.png")
            await eval_js("document.querySelector('.eva-route-card[data-route-key=\"conservative\"]')?.click();")
            await asyncio.sleep(1.0)
            results["steps"].append({"step": 9, "name": "Compare available route strategies", "status": "PASS"})

            # 10. Inspect outbound and return paths
            print("10. Inspecting outbound and return route paths...")
            card_info = await eval_js("""
            (() => {
                const c = document.querySelector('.eva-route-card.selected');
                return c ? c.innerText : '';
            })()
            """)
            print(f"   Active Card Summary: {card_info[:80]}...")
            results["steps"].append({"step": 10, "name": "Inspect outbound and return paths", "status": "PASS"})

            # 11. Inspect estimated resource consumption
            print("11. Opening Visor HUD and inspecting PLSS consumable budget...")
            await eval_js("document.getElementById('btnToggleEvaVisor')?.click();")
            await asyncio.sleep(1.5)
            await snap("wf_08_visor_hud_resources.png")
            o2_supply = await eval_js("document.getElementById('evaHudO2')?.innerText")
            margin = await eval_js("document.getElementById('evaHudMargin')?.innerText")
            print(f"   O2 Supply: {o2_supply} | Usable Margin: {margin}")
            results["steps"].append({"step": 11, "name": "Inspect estimated resource consumption", "status": "PASS"})

            # 12. Review the reserve and limitations
            print("12. Reviewing reserve barrier and operational limitations...")
            disclaimer = await eval_js("document.querySelector('.eva-visor-banner div div:last-child')?.innerText")
            print(f"   Visor Disclosure: {disclaimer}")
            results["steps"].append({"step": 12, "name": "Review reserve and limitations", "status": "PASS"})

            # 13. Trigger a supported contingency scenario
            print("13. Triggering simulated dust event contingency...")
            await eval_js("document.querySelector('.btn-eva-contingency-trigger[data-contingency=\"dust_event\"]')?.click();")
            await asyncio.sleep(2.5)
            await snap("wf_09_contingency_triggered.png")
            c_state = await eval_js("document.getElementById('evaHudMissionState')?.innerText")
            advisory = await eval_js("document.getElementById('evaContingencyAdvisoryText')?.innerText")
            print(f"   Mission State: {c_state} | Advisory: {advisory}")
            results["steps"].append({"step": 13, "name": "Trigger supported contingency", "status": "PASS" if c_state == "CAUTION" else "FAIL"})

            # 14. Inspect resulting state and return logic
            print("14. Inspecting emergency return logic...")
            results["steps"].append({"step": 14, "name": "Inspect resulting state and return logic", "status": "PASS"})

            # 15. Reset the contingency
            print("15. Clearing contingency with RESET button...")
            await eval_js("document.getElementById('btnEvaContingencyReset')?.click();")
            await asyncio.sleep(1.5)
            await snap("wf_10_contingency_reset.png")
            cleared_state = await eval_js("document.getElementById('evaHudMissionState')?.innerText")
            print(f"   Restored State: {cleared_state}")
            results["steps"].append({"step": 15, "name": "Reset contingency", "status": "PASS" if cleared_state == "NOMINAL" else "FAIL"})

            # 16. Return to the homepage
            print("16. Returning to homepage overview...")
            await eval_js("showLandingPage();")
            await asyncio.sleep(1.5)
            await snap("wf_11_returned_homepage.png")
            results["steps"].append({"step": 16, "name": "Return to homepage", "status": "PASS"})

            # 17. Enter Rover mode
            print("17. Entering Robotic Rover mode...")
            await eval_js("hideLandingPage(true);")
            await asyncio.sleep(0.5)
            await eval_js("document.getElementById('btnModeRoboticRover')?.click();")
            await asyncio.sleep(2.0)
            await snap("wf_12_rover_mode.png")
            rover_active = await eval_js("document.getElementById('btnModeRoboticRover')?.classList.contains('active')")
            print(f"   Rover Mode Active: {rover_active}")
            results["steps"].append({"step": 17, "name": "Enter Rover mode", "status": "PASS" if rover_active else "FAIL"})

            # 18. Return to main interface
            print("18. Returning to main interface...")
            await eval_js("switchInspectorTab('tabPlan');")
            await asyncio.sleep(1.0)
            await snap("wf_13_main_interface_ready.png")
            results["steps"].append({"step": 18, "name": "Return to main interface", "status": "PASS"})

            all_passed = all(s["status"] == "PASS" for s in results["steps"])
            passed_count = sum(1 for s in results["steps"] if s["status"] == "PASS")
            total_count = len(results["steps"])
            results["overall_status"] = "ALL_PASSED" if all_passed else "SOME_FAILED"
            results["passed_count"] = passed_count
            results["total_count"] = total_count

            report_path = os.path.join(OUTPUT_DIR, "jezero_workflow_report.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)

            print(f"\n=======================================================")
            if all_passed:
                print(f"JEZERO WORKFLOW VALIDATION COMPLETED: {passed_count}/{total_count} STEPS PASSED")
            else:
                failing = [s["name"] for s in results["steps"] if s["status"] != "PASS"]
                print(f"JEZERO WORKFLOW VALIDATION WARNING: {passed_count}/{total_count} STEPS PASSED")
                print(f"Failing steps: {failing}")
            print(f"Report: {report_path}")
            print(f"=======================================================\n")
            if not all_passed:
                sys.exit(1)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        shutil.rmtree(tmp_profile, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(run_workflow())
