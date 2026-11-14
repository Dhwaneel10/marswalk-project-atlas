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
DEBUG_PORT = 9529

REPO_ROOT = os.path.abspath(r"E:\Python\NASA-Spaceapps\Marswalk")
RELAYNET_SHOWCASE_DIR = os.path.join(REPO_ROOT, "outputs", "conference_showcase", "relaynet")
ARTIFACT_DIR = r"C:\Users\dhwan\.gemini\antigravity\brain\0a1bc6e9-d3cc-4c3b-b1fe-4875c358b144\outputs\conference_showcase\relaynet"

os.makedirs(RELAYNET_SHOWCASE_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

async def run_verification():
    print("=" * 80)
    print("  MARSWALK 2.0 / PROJECT ATLAS — MILESTONE 13D RELAYNET CDP VERIFICATION")
    print("=" * 80)

    tmp_profile = tempfile.mkdtemp(prefix="chrome_relaynet_cdp_")
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

            # Step 1: Navigate to Demo & Theater Mode URL with relaynet=1
            print("\n[Step 1] Navigating to http://127.0.0.1:3000/?mode=demo&theater=1&relaynet=1...")
            await set_viewport(1920, 1080)
            await send_cmd("Page.navigate", {"url": f"{BASE_URL}/?mode=demo&theater=1&relaynet=1"})
            await asyncio.sleep(4.5)

            # Check if Theater Mode and RelayNet are active
            state_check = await evaluate_js("""(() => {
                const hud = document.getElementById('missionTheaterHUD');
                const panel = document.getElementById('relayNetPanel');
                const btn = document.getElementById('btnToggleRelayNet');
                return {
                    theaterHUD: hud && !hud.classList.contains('hidden'),
                    relayNetPanel: panel && !panel.classList.contains('hidden'),
                    btnToggleActive: btn && btn.classList.contains('active'),
                    atlasReady: typeof window.__atlas !== 'undefined'
                };
            })()""")
            print(f"  -> State check: {state_check}")

            # Ensure we are in Jezero view with director mode 'overview'
            await evaluate_js("""(() => {
                if (typeof flyToJezeroView === 'function') flyToJezeroView();
                if (typeof setCameraDirectorMode === 'function') setCameraDirectorMode('overview');
            })()""")
            await asyncio.sleep(1.5)

            # -------------------------------------------------------------
            # Screenshot 1: 01_relaynet_los_blocked_baseline.png
            # Direct Rover-to-Base link occluded by ridge, red dashed ray + impact marker
            # -------------------------------------------------------------
            print("\n[Step 2] Setting up Occluded Baseline (Rover at Three Forks [138, 114])...")
            await evaluate_js("""(() => {
                // Seek playback to when rover is blocked behind ridge (Three Forks)
                const state = {
                    rc: [138, 114],
                    elevation_m: -2518.4,
                    cumulative_distance_m: 918.0,
                    slope_deg: 4.2,
                    speed_m_s: 0.55
                };
                if (typeof updateRelayNetPlayback === 'function') {
                    updateRelayNetPlayback(600, state);
                }
                const panel = document.getElementById('relayNetPanel');
                if (panel) panel.classList.remove('hidden');
            })()""")
            await asyncio.sleep(1.2)
            shot1 = os.path.join(RELAYNET_SHOWCASE_DIR, "01_relaynet_los_blocked_baseline.png")
            await capture_png(shot1)

            # -------------------------------------------------------------
            # Screenshot 2: 02_relaynet_candidate_promontories.png
            # Jezero crater rim with 12 amber holographic candidate pins
            # -------------------------------------------------------------
            print("\n[Step 3] Loading & Displaying Candidate Promontories...")
            await evaluate_js("""(() => {
                if (typeof loadRelayNetCandidates === 'function') loadRelayNetCandidates();
                const chk = document.getElementById('chkRelayCandidates');
                if (chk) chk.checked = true;
                if (typeof relayNetCandidatesGroup !== 'undefined' && relayNetCandidatesGroup) {
                    relayNetCandidatesGroup.visible = true;
                }
            })()""")
            await asyncio.sleep(1.5)
            shot2 = os.path.join(RELAYNET_SHOWCASE_DIR, "02_relaynet_candidate_promontories.png")
            await capture_png(shot2)

            # -------------------------------------------------------------
            # Screenshot 3: 03_relaynet_optimized_mesh.png
            # Deployed emerald relay towers restoring coverage with active carrier beam
            # -------------------------------------------------------------
            print("\n[Step 4] Executing Submodular Greedy Relay Optimization...")
            await evaluate_js("""(() => {
                if (typeof autoPlanOptimalRelays === 'function') autoPlanOptimalRelays();
            })()""")
            await asyncio.sleep(2.5)

            # Re-evaluate playback state with active relays to show carrier beam
            await evaluate_js("""(() => {
                const state = {
                    rc: [138, 114],
                    elevation_m: -2518.4,
                    cumulative_distance_m: 918.0,
                    slope_deg: 4.2,
                    speed_m_s: 0.55
                };
                if (typeof updateRelayNetPlayback === 'function') {
                    updateRelayNetPlayback(600, state);
                }
            })()""")
            await asyncio.sleep(1.0)
            shot3 = os.path.join(RELAYNET_SHOWCASE_DIR, "03_relaynet_optimized_mesh.png")
            await capture_png(shot3)

            # -------------------------------------------------------------
            # Screenshot 4: 04_relaynet_dynamic_mission_timeline.png
            # Cockpit HUD showing active hops, propagation delay, and availability %
            # -------------------------------------------------------------
            print("\n[Step 5] Capturing Dynamic Mission Timeline & Telemetry...")
            shot4 = os.path.join(RELAYNET_SHOWCASE_DIR, "04_relaynet_dynamic_mission_timeline.png")
            await capture_png(shot4)

            # -------------------------------------------------------------
            # Screenshot 5: 05_relaynet_raycast_spatial_inspector.png
            # Clicking relay tower displaying #theaterInspectorCard telemetry
            # -------------------------------------------------------------
            print("\n[Step 6] Triggering Spatial Inspector for Surface Relay Tower...")
            await evaluate_js("""(() => {
                const relayData = {
                    node_id: 'MRN-TOWER-01',
                    row: 78,
                    col: 134,
                    elevation_m: -2464.3,
                    antenna_height_m: 10.0,
                    effective_z_m: -2454.3,
                    node_type: 'relay_node'
                };
                if (typeof showTheaterSpatialInspector === 'function') {
                    showTheaterSpatialInspector('relay_node', relayData, { x: 0, y: 0, z: 0 });
                }
            })()""")
            await asyncio.sleep(0.8)
            shot5 = os.path.join(RELAYNET_SHOWCASE_DIR, "05_relaynet_raycast_spatial_inspector.png")
            await capture_png(shot5)

            # -------------------------------------------------------------
            # Screenshot 6: 06_relaynet_multi_hop_path.png
            # Multi-hop path perspective
            # -------------------------------------------------------------
            print("\n[Step 7] Capturing Multi-Hop Constellation View...")
            await evaluate_js("""(() => {
                if (typeof setCameraDirectorMode === 'function') setCameraDirectorMode('slant');
            })()""")
            await asyncio.sleep(1.5)
            shot6 = os.path.join(RELAYNET_SHOWCASE_DIR, "06_relaynet_multi_hop_path.png")
            await capture_png(shot6)

            # Step 8: Responsive Check at 1366x768
            print("\n[Step 8] Checking 1366x768 Responsive Layout...")
            await set_viewport(1366, 768)
            await asyncio.sleep(1.0)
            responsive_shot = os.path.join(RELAYNET_SHOWCASE_DIR, "07_relaynet_responsive_1366x768.png")
            await capture_png(responsive_shot)

            # Check Console Errors
            print("\n" + "=" * 80)
            print("  AUDIT REPORT: BROWSER CONSOLE ERRORS")
            print("=" * 80)
            if console_errors:
                print(f"  [FAIL] {len(console_errors)} console errors detected:")
                for err in console_errors:
                    print(f"    - {err}")
            else:
                print("  [PASS] 0 console errors detected during full interactive RelayNet session!")

            listen_task.cancel()

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        shutil.rmtree(tmp_profile, ignore_errors=True)
        print("  -> Cleaned up Chrome CDP test profile.")

if __name__ == "__main__":
    asyncio.run(run_verification())
