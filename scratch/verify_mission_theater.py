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
THEATER_SHOWCASE_DIR = os.path.join(REPO_ROOT, "outputs", "conference_showcase", "mission_theater")
ARTIFACT_DIR = r"C:\Users\dhwan\.gemini\antigravity\brain\0a1bc6e9-d3cc-4c3b-b1fe-4875c358b144\outputs\conference_showcase\mission_theater"

os.makedirs(THEATER_SHOWCASE_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

async def run_verification():
    print("=" * 80)
    print("  MARSWALK 2.0 / PROJECT ATLAS — 3D MISSION THEATER CDP VERIFICATION")
    print("=" * 80)

    tmp_profile = tempfile.mkdtemp(prefix="chrome_theater_cdp_")
    proc = subprocess.Popen([
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={tmp_profile}",
        "--headless=new",
        "--disable-gpu",
        "--disable-extensions",
        "--window-size=1920,1080",
        "about:blank",
    ])
    await asyncio.sleep(2.0)

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{DEBUG_PORT}/json/list")
        with urllib.request.urlopen(req, timeout=3) as resp:
            targets = json.loads(resp.read().decode("utf-8"))

        page_targets = [t for t in targets if t.get("type") == "page"]
        if not page_targets:
            raise RuntimeError(f"No page target found: {targets}")
        ws_url = page_targets[0]["webSocketDebuggerUrl"]
        print(f"  -> Connected to CDP Page Target: {page_targets[0].get('title')}")

        async with websockets.connect(ws_url, max_size=35 * 1024 * 1024) as ws:
            msg_id = 0
            pending_responses = {}
            console_errors = []

            async def send_cmd(method, params=None, timeout_s=15.0):
                nonlocal msg_id
                msg_id += 1
                mid = msg_id
                fut = asyncio.get_event_loop().create_future()
                pending_responses[mid] = fut
                payload = {"id": mid, "method": method, "params": params or {}}
                await ws.send(json.dumps(payload))
                try:
                    return await asyncio.wait_for(fut, timeout=timeout_s)
                finally:
                    pending_responses.pop(mid, None)

            async def listen_loop():
                try:
                    async for raw in ws:
                        data = json.loads(raw)
                        if "id" in data and data["id"] in pending_responses:
                            pending_responses[data["id"]].set_result(data.get("result", {}))
                        elif data.get("method") == "Runtime.consoleAPICalled":
                            args = data.get("params", {}).get("args", [])
                            text = " ".join([str(a.get("value", a.get("description", ""))) for a in args])
                            t = data.get("params", {}).get("type", "")
                            if t == "error":
                                console_errors.append(text)
                                print(f"    [Browser Console ERROR]: {text}")
                            elif "warning" not in t and "debug" not in t and len(text) < 120:
                                pass
                        elif data.get("method") == "Runtime.exceptionThrown":
                            details = data.get("params", {}).get("exceptionDetails", {})
                            exc_text = details.get("text", "") + " " + str(details.get("exception", {}).get("description", ""))
                            console_errors.append(exc_text)
                            print(f"    [Browser Exception]: {exc_text}")
                except asyncio.CancelledError:
                    pass

            listen_task = asyncio.create_task(listen_loop())

            await send_cmd("Page.enable")
            await send_cmd("Runtime.enable")
            await send_cmd("DOM.enable")

            async def evaluate_js(expression, await_promise=False):
                res = await send_cmd("Runtime.evaluate", {
                    "expression": expression,
                    "returnByValue": True,
                    "awaitPromise": await_promise
                })
                if "exceptionDetails" in res:
                    print(f"JS Error: {res['exceptionDetails']}")
                return res.get("result", {}).get("value")

            async def set_viewport(width, height):
                await send_cmd("Emulation.setDeviceMetricsOverride", {
                    "width": width,
                    "height": height,
                    "deviceScaleFactor": 1,
                    "mobile": False,
                })
                await asyncio.sleep(0.3)

            async def capture_png(filepath):
                res = await send_cmd("Page.captureScreenshot", {"format": "png"})
                b64 = res.get("data", "")
                data = base64.b64decode(b64)
                with open(filepath, "wb") as f:
                    f.write(data)
                # Copy to brain artifact directory as well
                artifact_copy = os.path.join(ARTIFACT_DIR, os.path.basename(filepath))
                shutil.copy2(filepath, artifact_copy)
                print(f"  [Screenshot Captured]: {os.path.basename(filepath)} ({len(data):,} bytes)")

            # Step 1: Navigate to Demo & Theater Mode URL
            print("\n[Step 1] Navigating to http://127.0.0.1:3000/?mode=demo&theater=1...")
            await set_viewport(1920, 1080)
            await send_cmd("Page.navigate", {"url": f"{BASE_URL}/?mode=demo&theater=1"})
            await asyncio.sleep(4.0)

            # Check if Theater Mode is active
            theater_active = await evaluate_js("""(() => {
                const hud = document.getElementById('missionTheaterHUD');
                const isBodyActive = document.body.classList.contains('theater-mode-active');
                const isHudVisible = hud && !hud.classList.contains('hidden');
                return { isBodyActive, isHudVisible };
            })()""")
            print(f"  -> Theater Mode Status: {theater_active}")

            if not (theater_active and theater_active.get("isBodyActive")):
                print("  -> Invoking enterMissionTheaterMode() directly...")
                await evaluate_js("window.MarsWalk.enterTheaterMode();")
                await asyncio.sleep(1.5)

            # Ensure Jezero surface view is rendered
            await evaluate_js("""(() => {
                if (typeof window.MarsWalk.flyToJezero === 'function') {
                    window.MarsWalk.flyToJezero();
                }
            })()""")
            await asyncio.sleep(2.5)

            # -------------------------------------------------------------
            # Shot 1: Regional Mission Overview with CTX Orthomosaic Drape
            # -------------------------------------------------------------
            print("\n[Shot 1] Capturing Regional Mission Overview (ORBIT / OVERVIEW)...")
            await evaluate_js("""(() => {
                if (window.MarsWalk.setTheaterCameraMode) window.MarsWalk.setTheaterCameraMode('overview');
                const btnLayerOrtho = document.querySelector('#theaterLayerPills [data-layer="ortho"]');
                if (btnLayerOrtho) btnLayerOrtho.click();
            })()""")
            await asyncio.sleep(2.0)
            shot1_path = os.path.join(THEATER_SHOWCASE_DIR, "01_theater_overview_ctx.png")
            await capture_png(shot1_path)

            # -------------------------------------------------------------
            # Shot 2: Oblique Topographic Perspective with Horn 3x3 Slope Shading
            # -------------------------------------------------------------
            print("\n[Shot 2] Capturing Oblique Topographic Scarp Relief with Slope Shading...")
            await evaluate_js("""(() => {
                if (window.MarsWalk.setTheaterCameraMode) window.MarsWalk.setTheaterCameraMode('topographic');
                const btnLayerSlope = document.querySelector('#theaterLayerPills [data-layer="slope"]');
                if (btnLayerSlope) btnLayerSlope.click();
            })()""")
            await asyncio.sleep(2.0)
            shot2_path = os.path.join(THEATER_SHOWCASE_DIR, "02_theater_topographic_slope.png")
            await capture_png(shot2_path)

            # -------------------------------------------------------------
            # Shot 3: Follow Unit Chase Camera tracking exploration vehicle
            # -------------------------------------------------------------
            print("\n[Shot 3] Capturing Follow Unit Chase Camera tracking exploration unit...")
            await evaluate_js("""(() => {
                const btnLayerOrtho = document.querySelector('#theaterLayerPills [data-layer="ortho"]');
                if (btnLayerOrtho) btnLayerOrtho.click();
                if (window.MarsWalk.setTheaterCameraMode) window.MarsWalk.setTheaterCameraMode('follow');
                // Seek timeline to 25s
                const scrub = document.getElementById('theaterTimelineScrubber');
                if (scrub) {
                    scrub.value = 25;
                    scrub.dispatchEvent(new Event('input'));
                }
            })()""")
            await asyncio.sleep(2.0)
            shot3_path = os.path.join(THEATER_SHOWCASE_DIR, "03_theater_follow_unit.png")
            await capture_png(shot3_path)

            # -------------------------------------------------------------
            # Shot 4: Tri-Track Trajectory Comparison with Detour & Obstacle Zone
            # -------------------------------------------------------------
            print("\n[Shot 4] Capturing Tri-Track Trajectory (Nominal, Disturbed, Detour)...")
            await evaluate_js("""(() => {
                if (window.MarsWalk.setTheaterCameraMode) window.MarsWalk.setTheaterCameraMode('topographic');
                // Trigger Rockfall obstacle injection / detour in engine
                const selectDisturbance = document.getElementById('rehearsalDisturbanceSelect');
                if (selectDisturbance) {
                    selectDisturbance.value = 'rockfall_obstacle';
                    selectDisturbance.dispatchEvent(new Event('change'));
                }
                const btnRunRehearsal = document.getElementById('btnRunRehearsal');
                if (btnRunRehearsal) btnRunRehearsal.click();
            })()""")
            await asyncio.sleep(2.5)
            shot4_path = os.path.join(THEATER_SHOWCASE_DIR, "04_theater_tri_track_detour.png")
            await capture_png(shot4_path)

            # -------------------------------------------------------------
            # Shot 5: Raycast Spatial Object Inspector Card
            # -------------------------------------------------------------
            print("\n[Shot 5] Capturing Raycast Spatial Object Inspector Card...")
            await evaluate_js("""(() => {
                // Simulate raycast inspector on Jezero Delta Scarp terrain
                if (typeof showTheaterSpatialInspector === 'function') {
                    showTheaterSpatialInspector('terrain', { row: 120, col: 145, lat: 18.44115, lon: 77.43984 }, { x: 0, y: 15, z: 0 });
                }
            })()""")
            await asyncio.sleep(1.0)
            shot5_path = os.path.join(THEATER_SHOWCASE_DIR, "05_theater_raycast_inspector.png")
            await capture_png(shot5_path)

            # -------------------------------------------------------------
            # Shot 6: Forensic Causal Decision Ledger Event Sync
            # -------------------------------------------------------------
            print("\n[Shot 6] Capturing Causal Event Synchronization & Focus Mode...")
            await evaluate_js("""(() => {
                if (window.MarsWalk.setTheaterCameraMode) window.MarsWalk.setTheaterCameraMode('focus');
                if (typeof showTheaterSpatialInspector === 'function') {
                    showTheaterSpatialInspector('hazard', {}, { x: 0, y: 15, z: 0 });
                }
            })()""")
            await asyncio.sleep(1.5)
            shot6_path = os.path.join(THEATER_SHOWCASE_DIR, "06_theater_causal_event_sync.png")
            await capture_png(shot6_path)

            # -------------------------------------------------------------
            # Responsive Layout Checks: 1920x1080 and 1366x768
            # -------------------------------------------------------------
            print("\n[Step 2] Checking Responsive Layouts (1920x1080 & 1366x768)...")
            res_1920 = await evaluate_js("""(() => {
                return {
                    scrollWidth: document.body.scrollWidth,
                    innerWidth: window.innerWidth,
                    overflow: document.body.scrollWidth > window.innerWidth
                };
            })()""")
            print(f"  -> 1920x1080: scrollWidth={res_1920.get('scrollWidth')}px, innerWidth={res_1920.get('innerWidth')}px, overflow={res_1920.get('overflow')}")

            await set_viewport(1366, 768)
            await asyncio.sleep(1.0)
            res_1366 = await evaluate_js("""(() => {
                return {
                    scrollWidth: document.body.scrollWidth,
                    innerWidth: window.innerWidth,
                    overflow: document.body.scrollWidth > window.innerWidth
                };
            })()""")
            print(f"  -> 1366x768: scrollWidth={res_1366.get('scrollWidth')}px, innerWidth={res_1366.get('innerWidth')}px, overflow={res_1366.get('overflow')}")

            # Console Error Summary
            print("\n[Step 3] Console Error Summary:")
            real_errors = [e for e in console_errors if "favicon" not in e and "WebGL" not in e and "Cesium" not in e]
            print(f"  -> Total Uncaught Critical Console Errors: {len(real_errors)}")
            for err in real_errors:
                print(f"     * {err}")

            assert len(real_errors) == 0, f"Uncaught console errors detected: {real_errors}"
            assert res_1920.get("overflow") is False, "Horizontal overflow detected on 1920x1080"
            assert res_1366.get("overflow") is False, "Horizontal overflow detected on 1366x768"

            listen_task.cancel()

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        shutil.rmtree(tmp_profile, ignore_errors=True)

    print("\n" + "=" * 80)
    print("  3D MISSION THEATER VERIFICATION & SHOWCASE CAPTURE: ALL PASSED")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_verification())
