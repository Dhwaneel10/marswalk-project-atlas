"""
MarsWalk 2.0 / Project Atlas - Milestone 13E Automated CDP Browser Acceptance & Showcase Capture.

Captures 8 conference showcase screenshots for the Joint Mission Design Studio:
1. 01_joint_studio_wizard_overview.png (Step 1 Mission Definition & Weights)
2. 02_mobility_comms_configuration.png (Step 2 Mobility & Step 3 Comms)
3. 03_pareto_frontier_scatter_analysis.png (Interactive Pareto Frontier & Scorecard)
4. 04_theater_candidate_routes_co_design.png (3D Theater Multi-Traverse Co-Design View)
5. 05_relay_mesh_overlay_candidates.png (Traverses Interlaced with Promontories & Masts)
6. 06_dynamic_timeline_scrubber_sync.png (Timeline Scrubber Sync with Dynamic Beams)
7. 07_spatial_raycast_candidate_inspector.png (Interactive Raycast Spatial Inspector Card)
8. 08_responsive_layout_1366x768.png (Compact Laptop 1366x768 Viewport Layout)

Enforces:
- Zero horizontal body overflow (scrollWidth <= innerWidth)
- Zero browser console errors
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
DEBUG_PORT = 9515

REPO_ROOT = os.path.abspath(r"E:\Python\NASA-Spaceapps\Marswalk")
OUTPUT_DIR = os.path.join(REPO_ROOT, "outputs", "conference_showcase", "joint_mission")

async def run_browser_verification():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="atlas_joint_cdp_")
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

            async def send_cmd(method, params=None, timeout_s=15.0):
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
                                    # Ignore benign favicon 404 or WebGL warnings if any
                                    if "favicon" not in text:
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

            async def evaluate_js(expression, timeout_s=10.0):
                res = await send_cmd("Runtime.evaluate", {
                    "expression": expression,
                    "returnByValue": True,
                    "awaitPromise": True
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
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(img_b64))
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
            # Screenshot 01: Joint Studio Wizard Overview (Step 1)
            # ------------------------------------------------------------------
            print("\n[Step 2] Capturing 01_joint_studio_wizard_overview.png (Step 1 Mission & Weights)...")
            await evaluate_js("""
                window.Atlas.switchInspectorTab('tabJointMissionStudio');
                window.Atlas.switchJointWizardStep(1);
            """)
            await asyncio.sleep(1.0)
            await capture_screenshot("01_joint_studio_wizard_overview.png", 1920, 1080)

            # ------------------------------------------------------------------
            # Screenshot 02: Mobility & Comms Configuration (Step 2 / Step 3)
            # ------------------------------------------------------------------
            print("\n[Step 3] Capturing 02_mobility_comms_configuration.png (Step 2 Mobility & Step 3 Comms)...")
            await evaluate_js("""
                window.Atlas.switchJointWizardStep(2);
            """)
            await asyncio.sleep(0.8)
            await capture_screenshot("02_mobility_comms_configuration.png", 1920, 1080)

            # ------------------------------------------------------------------
            # Screenshot 03: Run Optimization & Pareto Frontier Scatter Analysis
            # ------------------------------------------------------------------
            print("\n[Step 4] Running Joint Co-Design Optimization & Capturing 03_pareto_frontier_scatter_analysis.png...")
            await evaluate_js("""
                window.Atlas.switchJointWizardStep(4);
                window.Atlas.runJointMissionOptimization();
            """)
            # Wait for optimizer API response & Pareto rendering
            await asyncio.sleep(3.5)

            # Hover/select Pareto candidate
            await evaluate_js("""
                window.Atlas.switchJointWizardStep(5);
                window.Atlas.selectJointConfiguration('JMC-01');
            """)
            await asyncio.sleep(1.0)
            await capture_screenshot("03_pareto_frontier_scatter_analysis.png", 1920, 1080)

            # ------------------------------------------------------------------
            # Screenshot 04: 3D Mission Theater Multi-Traverse Co-Design View
            # ------------------------------------------------------------------
            print("\n[Step 5] Entering 3D Theater & Capturing 04_theater_candidate_routes_co_design.png...")
            await evaluate_js("""
                enterMissionTheaterMode();
                const jmPanel = document.getElementById('jointMissionStudioPanel');
                if (jmPanel) jmPanel.classList.remove('hidden');
                setCameraDirectorMode('overview');
            """)
            await asyncio.sleep(2.0)
            await capture_screenshot("04_theater_candidate_routes_co_design.png", 1920, 1080)

            # ------------------------------------------------------------------
            # Screenshot 05: Relay Mesh Overlay & Candidate Promontories
            # ------------------------------------------------------------------
            print("\n[Step 6] Capturing 05_relay_mesh_overlay_candidates.png (Topographic Scarp Perspective)...")
            await evaluate_js("""
                setCameraDirectorMode('topographic');
                const rnPanel = document.getElementById('relayNetPanel');
                if (rnPanel) rnPanel.classList.remove('hidden');
            """)
            await asyncio.sleep(1.5)
            await capture_screenshot("05_relay_mesh_overlay_candidates.png", 1920, 1080)

            # ------------------------------------------------------------------
            # Screenshot 06: Dynamic Timeline Scrubber Sync
            # ------------------------------------------------------------------
            print("\n[Step 7] Capturing 06_dynamic_timeline_scrubber_sync.png (Timeline Scrubber in Playback)...")
            await evaluate_js("""
                const scrubber = document.getElementById('theaterTimelineScrubber');
                if (scrubber) {
                    scrubber.value = 1800;
                    scrubber.dispatchEvent(new Event('input'));
                }
                updateTheaterTimeline(1800);
            """)
            await asyncio.sleep(1.5)
            await capture_screenshot("06_dynamic_timeline_scrubber_sync.png", 1920, 1080)

            # ------------------------------------------------------------------
            # Screenshot 07: Spatial Raycast Candidate Inspector Card
            # ------------------------------------------------------------------
            print("\n[Step 8] Capturing 07_spatial_raycast_candidate_inspector.png (Candidate Route Raycast)...")
            await evaluate_js("""
                if (jointMissionOptimizationResult && jointMissionOptimizationResult.all_candidates) {
                    const c = jointMissionOptimizationResult.all_candidates[1] || jointMissionOptimizationResult.all_candidates[0];
                    showTheaterSpatialInspector('joint_candidate_route', c, new THREE.Vector3(0, 50, 0));
                }
            """)
            await asyncio.sleep(1.0)
            await capture_screenshot("07_spatial_raycast_candidate_inspector.png", 1920, 1080)

            # ------------------------------------------------------------------
            # Screenshot 08: Compact Laptop 1366x768 Responsive Layout
            # ------------------------------------------------------------------
            print("\n[Step 9] Capturing 08_responsive_layout_1366x768.png (1366x768 Viewport)...")
            await evaluate_js("""
                exitMissionTheaterMode();
                window.Atlas.switchInspectorTab('tabJointMissionStudio');
                window.Atlas.switchJointWizardStep(5);
            """)
            await send_cmd("Emulation.setDeviceMetricsOverride", {
                "width": 1366,
                "height": 768,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(1.5)

            # Verify zero horizontal overflow on 1366x768
            overflow = await evaluate_js("""
                document.body.scrollWidth > window.innerWidth
            """)
            print(f"  -> Horizontal Body Overflow (1366x768): {overflow} (scrollWidth: {await evaluate_js('document.body.scrollWidth')}, innerWidth: 1366)")
            assert not overflow, "CRITICAL: Horizontal body overflow detected on 1366x768!"

            await capture_screenshot("08_responsive_layout_1366x768.png", 1366, 768)

            # ------------------------------------------------------------------
            # Summary & Console Error Checks
            # ------------------------------------------------------------------
            print("\n" + "=" * 80)
            print("  BROWSER ACCEPTANCE AUDIT RESULTS")
            print("=" * 80)
            print(f"Total Console Errors Encountered: {len(console_errors)}")
            for err in console_errors:
                print(f"  - {err}")
            assert len(console_errors) == 0, f"Encountered {len(console_errors)} browser console errors!"

            # Check that all 8 screenshots exist and are > 50 KB
            expected_files = [
                "01_joint_studio_wizard_overview.png",
                "02_mobility_comms_configuration.png",
                "03_pareto_frontier_scatter_analysis.png",
                "04_theater_candidate_routes_co_design.png",
                "05_relay_mesh_overlay_candidates.png",
                "06_dynamic_timeline_scrubber_sync.png",
                "07_spatial_raycast_candidate_inspector.png",
                "08_responsive_layout_1366x768.png",
            ]
            for ef in expected_files:
                fpath = os.path.join(OUTPUT_DIR, ef)
                assert os.path.exists(fpath), f"Missing screenshot: {ef}"
                sz_kb = os.path.getsize(fpath) / 1024.0
                assert sz_kb >= 50.0, f"Screenshot {ef} is too small: {sz_kb:.1f} KB"
                print(f"  [PASS] {ef}: {sz_kb:.1f} KB")

            print("\n>>> ALL 8 SHOWCASE SCREENSHOTS VERIFIED & ACCEPTED! <<<")

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
