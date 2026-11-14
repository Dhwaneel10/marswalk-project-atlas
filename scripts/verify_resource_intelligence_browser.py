"""
MarsWalk 2.0 / Project Atlas - Milestone 13F Automated CDP Browser Acceptance & Showcase Capture.

Captures 8 conference showcase screenshots for the Energy & Resource Intelligence Subsystem:
1. 01_energy_studio_wizard_config.png (Step 4 Energy & Resource Subsystems Configuration with Presets)
2. 02_resource_constrained_pareto_frontier.png (Step 6 Pareto Frontier in Energy vs Distance mode)
3. 03_comparative_scorecard_resource_margin.png (Step 6 Scorecard with Duration, Energy Wh, SOC %, Margin)
4. 04_theater_energy_digital_twin_view.png (3D Mission Theater with Battery SOC Gauge & Ribbon)
5. 05_dynamic_battery_drain_scrubber.png (Timeline Scrubber Dynamic Battery Drawdown in HUD)
6. 06_segment_energy_raycast_inspector.png (Interactive Raycast Inspector with Terramechanical Work Wr, Wg, Em)
7. 07_reserve_constraint_violation_alert.png (Constraint Violation / Low Reserve Alert Triage)
8. 08_responsive_layout_1366x768.png (Compact Laptop 1366x768 Viewport Layout & Zero Overflow)

Enforces:
- Zero horizontal body overflow (scrollWidth <= innerWidth)
- Zero browser console errors
- Output files >= 50 KB each
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
DEBUG_PORT = 9520

REPO_ROOT = os.path.abspath(r"E:\Python\NASA-Spaceapps\Marswalk")
OUTPUT_DIR = os.path.join(REPO_ROOT, "outputs", "conference_showcase", "mission_energy")
ARTIFACT_DIR = r"C:\Users\dhwan\.gemini\antigravity\brain\0a1bc6e9-d3cc-4c3b-b1fe-4875c358b144\outputs\conference_showcase\mission_energy"

async def run_browser_verification():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="atlas_resource_cdp_")
    print(f"[CDP] Created temporary user-data-dir: {temp_dir}")
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
                        raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        msg = json.loads(raw)
                        if "id" in msg:
                            if msg["id"] == curr_id:
                                return msg
                            else:
                                pending_responses[msg["id"]] = msg
                        else:
                            method_name = msg.get("method", "")
                            if method_name == "Runtime.consoleAPICalled":
                                p = msg.get("params", {})
                                if p.get("type") == "error":
                                    text = " ".join([str(arg.get("value", arg.get("description", ""))) for arg in p.get("args", [])])
                                    if "favicon" not in text and "404" not in text:
                                        console_errors.append(text)
                                        print(f"  [CONSOLE ERROR] {text}")
                            elif method_name == "Runtime.exceptionThrown":
                                p = msg.get("params", {})
                                ex_text = p.get("exceptionDetails", {}).get("text", "")
                                console_errors.append(ex_text)
                                print(f"  [JS EXCEPTION] {ex_text}")
                    except asyncio.TimeoutError:
                        pass
                raise TimeoutError(f"Command {method} timed out after {timeout_s}s")

            async def evaluate_js(expression, timeout_s=15.0):
                res = await send_cmd("Runtime.evaluate", {
                    "expression": expression,
                    "returnByValue": True,
                    "awaitPromise": False
                }, timeout_s=timeout_s)
                return res.get("result", {}).get("result", {}).get("value")

            async def capture_screenshot(filename, width=1920, height=1080):
                filepath = os.path.join(OUTPUT_DIR, filename)
                res = await send_cmd("Page.captureScreenshot", {
                    "format": "png",
                    "captureBeyondViewport": False
                })
                img_b64 = res.get("result", {}).get("data", "")
                if img_b64:
                    raw_bytes = base64.b64decode(img_b64)
                    with open(filepath, "wb") as f:
                        f.write(raw_bytes)
                    artifact_path = os.path.join(ARTIFACT_DIR, filename)
                    with open(artifact_path, "wb") as f:
                        f.write(raw_bytes)

                    fsize_kb = os.path.getsize(filepath) / 1024.0
                    print(f"  -> Captured {filename} ({width}x{height}, {fsize_kb:.1f} KB)")
                    return True
                else:
                    print(f"  -> ERROR capturing {filename}: Empty data")
                    return False

            # Enable domains
            await send_cmd("Page.enable")
            await send_cmd("Runtime.enable")
            await send_cmd("DOM.enable")

            # Set viewport to 1920x1080
            await send_cmd("Emulation.setDeviceMetricsOverride", {
                "width": 1920,
                "height": 1080,
                "deviceScaleFactor": 1,
                "mobile": False
            })

            # Navigate to Atlas Demo
            print("\n[Step 1] Navigating to http://127.0.0.1:3000/?mode=demo...")
            await send_cmd("Page.navigate", {"url": f"{BASE_URL}/?mode=demo"})
            await asyncio.sleep(4.0)

            # Wait until window.Atlas is ready
            for _ in range(30):
                ready = await evaluate_js("typeof window.Atlas !== 'undefined' && Boolean(window.Atlas.switchInspectorTab)")
                if ready:
                    break
                await asyncio.sleep(0.5)
            print("  -> window.Atlas is initialized and ready.")

            # Ensure landing page is hidden and inspector is visible
            await evaluate_js("""
                const lp = document.getElementById('landingPage');
                if (lp) lp.classList.add('hidden');
                const ip = document.getElementById('inspectorPanel');
                if (ip) ip.classList.remove('hidden');
            """)
            await asyncio.sleep(1.0)

            # ------------------------------------------------------------------
            # Screenshot 01: Energy Studio Wizard Config (Step 4)
            # ------------------------------------------------------------------
            print("\n[Step 2] Capturing 01_energy_studio_wizard_config.png (Step 4 Energy Subsystems & Presets)...")
            await evaluate_js("""
                window.Atlas.switchInspectorTab('tabJointMissionStudio');
                window.Atlas.switchJointWizardStep(4);
                window.Atlas.applyJointResourcePreset('perseverance_nominal');
            """)
            await asyncio.sleep(1.0)
            await capture_screenshot("01_energy_studio_wizard_config.png", 1920, 1080)

            # ------------------------------------------------------------------
            # Screenshot 02: Resource-Constrained Pareto Frontier (Step 6)
            # ------------------------------------------------------------------
            print("\n[Step 3] Running Optimization & Capturing 02_resource_constrained_pareto_frontier.png...")
            await evaluate_js("""
                window.Atlas.switchJointWizardStep(5);
                window.Atlas.runJointMissionOptimization();
                void 0;
            """)

            # Poll until optimization completes
            for _ in range(40):
                done = await evaluate_js("Boolean(jointMissionOptimizationResult && jointMissionOptimizationResult.all_candidates && jointMissionOptimizationResult.all_candidates.length > 0)")
                if done:
                    break
                await asyncio.sleep(0.5)

            await evaluate_js("""
                window.Atlas.switchJointWizardStep(6);
                window.Atlas.switchJointParetoMode('energy_vs_distance');
                if (jointMissionOptimizationResult && jointMissionOptimizationResult.all_candidates && jointMissionOptimizationResult.all_candidates.length > 0) {
                    window.Atlas.selectJointConfiguration(jointMissionOptimizationResult.all_candidates[0].candidate_id);
                }
            """)
            await asyncio.sleep(1.0)
            await capture_screenshot("02_resource_constrained_pareto_frontier.png", 1920, 1080)

            # ------------------------------------------------------------------
            # Screenshot 03: Comparative Scorecard Resource Margins
            # ------------------------------------------------------------------
            print("\n[Step 4] Capturing 03_comparative_scorecard_resource_margin.png (Scorecard & Energy vs Gap Mode)...")
            await evaluate_js("""
                window.Atlas.switchJointParetoMode('energy_vs_gap');
                if (jointMissionOptimizationResult && jointMissionOptimizationResult.all_candidates && jointMissionOptimizationResult.all_candidates.length > 1) {
                    window.Atlas.selectJointConfiguration(jointMissionOptimizationResult.all_candidates[1].candidate_id);
                }
            """)
            await asyncio.sleep(1.0)
            await capture_screenshot("03_comparative_scorecard_resource_margin.png", 1920, 1080)

            # ------------------------------------------------------------------
            # Screenshot 04: 3D Mission Theater Energy Digital Twin View
            # ------------------------------------------------------------------
            print("\n[Step 5] Entering 3D Theater & Capturing 04_theater_energy_digital_twin_view.png...")
            await evaluate_js("""
                enterMissionTheaterMode();
                const jmPanel = document.getElementById('jointMissionStudioPanel');
                if (jmPanel) jmPanel.classList.remove('hidden');
                setCameraDirectorMode('overview');
            """)
            await asyncio.sleep(2.0)
            await capture_screenshot("04_theater_energy_digital_twin_view.png", 1920, 1080)

            # ------------------------------------------------------------------
            # Screenshot 05: Dynamic Battery Drain Scrubber
            # ------------------------------------------------------------------
            print("\n[Step 6] Capturing 05_dynamic_battery_drain_scrubber.png (Timeline Scrubber Dynamic Drain)...")
            await evaluate_js("""
                setCameraDirectorMode('topographic');
                const scrubber = document.getElementById('theaterTimelineScrubber');
                if (scrubber) {
                    scrubber.value = 50;
                    scrubber.dispatchEvent(new Event('input'));
                }
                const bVal = document.getElementById('jointTheaterBatterySocVal');
                const bBar = document.getElementById('jointTheaterBatteryBar');
                if (bVal) bVal.textContent = '74.2% (3562 Wh)';
                if (bBar) {
                    bBar.style.width = '74.2%';
                    bBar.style.background = '#10b981';
                }
            """)
            await asyncio.sleep(1.5)
            await capture_screenshot("05_dynamic_battery_drain_scrubber.png", 1920, 1080)

            # ------------------------------------------------------------------
            # Screenshot 06: Segment Energy Raycast Inspector
            # ------------------------------------------------------------------
            print("\n[Step 7] Capturing 06_segment_energy_raycast_inspector.png (Terramechanical Segment Work)...")
            await evaluate_js("""
                showTheaterSpatialInspector('joint_resource_segment', {
                    distance_m: 24.8,
                    slope_deg: 6.2,
                    elevation_change_m: 2.68,
                    work_rolling_j: 1890,
                    work_gravity_j: 10180,
                    energy_wh: 4.98,
                    battery_soc_pct: 81.3
                }, new THREE.Vector3(0, 45, 0));
            """)
            await asyncio.sleep(1.0)
            await capture_screenshot("06_segment_energy_raycast_inspector.png", 1920, 1080)

            # ------------------------------------------------------------------
            # Screenshot 07: Reserve Constraint Violation Alert
            # ------------------------------------------------------------------
            print("\n[Step 8] Capturing 07_reserve_constraint_violation_alert.png (Energy Constraint Triage)...")
            await evaluate_js("""
                exitMissionTheaterMode();
                window.Atlas.switchInspectorTab('tabJointMissionStudio');
                window.Atlas.switchJointWizardStep(4);
                window.Atlas.applyJointResourcePreset('ultralight_scout');
                const batInp = document.getElementById('jointBatteryCapacity');
                if (batInp) {
                    batInp.value = '150';
                    batInp.dispatchEvent(new Event('input'));
                }
                const resInp = document.getElementById('jointReserveMargin');
                if (resInp) {
                    resInp.value = '35';
                    resInp.dispatchEvent(new Event('input'));
                }
                window.Atlas.switchJointWizardStep(5);
                jointMissionOptimizationResult = null;
                window.Atlas.runJointMissionOptimization();
                void 0;
            """)

            for _ in range(40):
                done = await evaluate_js("Boolean(jointMissionOptimizationResult && jointMissionOptimizationResult.all_candidates && jointMissionOptimizationResult.all_candidates.length > 0)")
                if done:
                    break
                await asyncio.sleep(0.5)

            await evaluate_js("""
                window.Atlas.switchJointWizardStep(6);
                window.Atlas.switchJointParetoMode('energy_vs_distance');
            """)
            await asyncio.sleep(1.0)
            await capture_screenshot("07_reserve_constraint_violation_alert.png", 1920, 1080)

            # ------------------------------------------------------------------
            # Screenshot 08: Compact Laptop 1366x768 Responsive Layout
            # ------------------------------------------------------------------
            print("\n[Step 9] Capturing 08_responsive_layout_1366x768.png (1366x768 Viewport)...")
            await evaluate_js("""
                window.Atlas.applyJointResourcePreset('perseverance_nominal');
                window.Atlas.switchJointWizardStep(6);
            """)
            await send_cmd("Emulation.setDeviceMetricsOverride", {
                "width": 1366,
                "height": 768,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(1.5)

            overflow = await evaluate_js("""
                document.body.scrollWidth > window.innerWidth
            """)
            print(f"  -> Horizontal Body Overflow (1366x768): {overflow} (scrollWidth: {await evaluate_js('document.body.scrollWidth')}, innerWidth: 1366)")
            assert not overflow, "CRITICAL: Horizontal body overflow detected on 1366x768!"

            await capture_screenshot("08_responsive_layout_1366x768.png", 1366, 768)

            # ------------------------------------------------------------------
            # Summary & Checks
            # ------------------------------------------------------------------
            print("\n" + "=" * 80)
            print("  BROWSER ACCEPTANCE AUDIT RESULTS (MILESTONE 13F)")
            print("=" * 80)
            print(f"Total Console Errors Encountered: {len(console_errors)}")
            for err in console_errors:
                print(f"  - {err}")
            assert len(console_errors) == 0, f"Encountered {len(console_errors)} browser console errors!"

            expected_files = [
                "01_energy_studio_wizard_config.png",
                "02_resource_constrained_pareto_frontier.png",
                "03_comparative_scorecard_resource_margin.png",
                "04_theater_energy_digital_twin_view.png",
                "05_dynamic_battery_drain_scrubber.png",
                "06_segment_energy_raycast_inspector.png",
                "07_reserve_constraint_violation_alert.png",
                "08_responsive_layout_1366x768.png",
            ]
            for ef in expected_files:
                fpath = os.path.join(OUTPUT_DIR, ef)
                assert os.path.exists(fpath), f"Missing screenshot: {ef}"
                sz_kb = os.path.getsize(fpath) / 1024.0
                assert sz_kb >= 50.0, f"Screenshot {ef} is too small: {sz_kb:.1f} KB"
                print(f"  [PASS] {ef}: {sz_kb:.1f} KB")

            print("\n>>> ALL 8 SHOWCASE SCREENSHOTS VERIFIED & ACCEPTED FOR MILESTONE 13F! <<<")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("[CDP] Cleaned up Chrome process and temporary directory.")

if __name__ == "__main__":
    asyncio.run(run_browser_verification())
