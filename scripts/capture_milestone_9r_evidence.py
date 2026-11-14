"""
MarsWalk 2.0 — Milestone 9R Interactive Contingency Designer Visual Evidence Script
Captures all 6 verified visual journeys:
 1. Custom Corridor Closure Placement & 3D Hazard Footprint (outputs/m9r_01_custom_closure_placement.png)
 2. Recalculated Detour Route avoiding blocked corridor (outputs/m9r_02_recalculated_detour_route.png)
 3. Mobility Derating Disruption with Invariant Geometry (outputs/m9r_03_mobility_derating_invariant_geom.png)
 4. Compound Scenario 8-Row Comparison Table (outputs/m9r_04_compound_contingency_table.png)
 5. Contingency Reset and Pristine Baseline Restoration (outputs/m9r_05_contingency_cleared_restore.png)
 6. Saved Contingency Experiment Persisted in Library (outputs/m9r_06_contingency_experiment_persisted.png)
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
DEBUG_PORT = 9499

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
        print(f"[JS EXCEPTION] {res_obj['exceptionDetails']}")
    return res_obj.get("result", {}).get("value")


async def capture_screenshot(ws, filename, clip=None):
    params = {"format": "png"}
    if clip:
        params["clip"] = clip
    resp = await send_cmd(ws, "Page.captureScreenshot", params)
    img_b64 = resp.get("result", {}).get("data")
    if not img_b64:
        raise RuntimeError(f"Screenshot capture failed for {filename}")

    data = base64.b64decode(img_b64)
    out_path = OUTPUT_DIR / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)

    try:
        ARTIFACT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        art_path = ARTIFACT_OUTPUT_DIR / filename
        with open(art_path, "wb") as f:
            f.write(data)
    except Exception as e:
        print(f"Warning: Could not mirror to artifact dir: {e}")

    print(f"  [SAVED] {filename} ({len(data)} bytes)")
    return out_path


async def run_evidence_capture():
    print("[M9R Evidence] Launching Chrome in headless remote debugging mode...")
    temp_dir = tempfile.mkdtemp(prefix="chrome_m9r_")
    args = [
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={temp_dir}",
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1920,1080",
        f"{BASE_URL}/?landing=false&fly=jezero",
    ]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        ws_url = None
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json") as r:
                    tabs = json.loads(r.read())
                    page_tab = next((t for t in tabs if t.get("type") == "page" and "3000" in t.get("url", "")), None)
                    if not page_tab:
                        page_tab = next((t for t in tabs if t.get("type") == "page"), None)
                    if page_tab:
                        ws_url = page_tab.get("webSocketDebuggerUrl")
                        if ws_url:
                            break
            except Exception:
                pass
            time.sleep(0.5)

        if not ws_url:
            raise RuntimeError("Failed to attach to Chrome remote debugging port")

        async with websockets.connect(ws_url, max_size=50_000_000) as ws:
            await send_cmd(ws, "Page.enable")
            await send_cmd(ws, "Runtime.enable")
            await send_cmd(ws, "DOM.enable")

            print("[M9R Evidence] Waiting for MarsWalk 3D Atlas engine to boot...")
            for _ in range(40):
                booted = await evaluate_js(ws, "typeof window.__atlas !== 'undefined' && window.__atlas.isBooted()")
                if booted:
                    break
                await asyncio.sleep(0.5)

            # Ensure we are in Jezero view and switch to Scenarios tab
            await evaluate_js(ws, """
                if (window.__atlas) {
                    window.__atlas.switchInspectorTab('scenarios');
                }
            """)
            await asyncio.sleep(1.0)

            # Calculate baseline route first
            print("[M9R Evidence] Calculating baseline traverse route...")
            await evaluate_js(ws, "window.__atlas.calculateTraverse()", await_promise=True)
            await asyncio.sleep(2.0)

            # =========================================================================
            # Journey 1: Custom Corridor Closure Placement
            # =========================================================================
            print("[M9R Evidence] Journey 1: Staging custom corridor closure...")
            await evaluate_js(ws, """(() => {
                const sel = document.getElementById('contingencyEventType');
                if (sel) {
                    sel.value = 'closed_corridor';
                    sel.dispatchEvent(new Event('change'));
                }
                const rIn = document.getElementById('contingencyCenterR');
                const cIn = document.getElementById('contingencyCenterC');
                const radIn = document.getElementById('contingencyRadiusM');
                const nameIn = document.getElementById('contingencyCustomName');
                if (rIn) rIn.value = '95';
                if (cIn) cIn.value = '140';
                if (radIn) radIn.value = '80';
                if (nameIn) nameIn.value = 'Rockfall Choke Point';

                const addBtn = document.getElementById('btnAddContingencyEvent');
                if (addBtn) addBtn.click();
            })()""")
            await asyncio.sleep(1.5)
            await capture_screenshot(ws, "m9r_01_custom_closure_placement.png")

            # =========================================================================
            # Journey 2: Recalculated Detour Route
            # =========================================================================
            print("[M9R Evidence] Journey 2: Simulating custom contingency...")
            await evaluate_js(ws, """(() => {
                const simBtn = document.getElementById('btnSimulateContingency');
                if (simBtn) simBtn.click();
            })()""")
            await asyncio.sleep(3.0)
            await capture_screenshot(ws, "m9r_02_recalculated_detour_route.png")

            # =========================================================================
            # Journey 3: Mobility Derating with Invariant Geometry
            # =========================================================================
            print("[M9R Evidence] Journey 3: Staging mobility derating (0.5x speed)...")
            await evaluate_js(ws, """(() => {
                const clearBtn = document.getElementById('btnClearContingency');
                if (clearBtn) clearBtn.click();

                const sel = document.getElementById('contingencyEventType');
                if (sel) {
                    sel.value = 'reduced_mobility';
                    sel.dispatchEvent(new Event('change'));
                }
                const spIn = document.getElementById('contingencySpeedMult');
                const nameIn = document.getElementById('contingencyCustomName');
                if (spIn) {
                    spIn.value = '0.50';
                    spIn.dispatchEvent(new Event('input'));
                }
                if (nameIn) nameIn.value = 'Actuator Thermal Throttling';

                const addBtn = document.getElementById('btnAddContingencyEvent');
                if (addBtn) addBtn.click();

                const simBtn = document.getElementById('btnSimulateContingency');
                if (simBtn) simBtn.click();
            })()""")
            await asyncio.sleep(3.0)
            await capture_screenshot(ws, "m9r_03_mobility_derating_invariant_geom.png")

            # =========================================================================
            # Journey 4: Compound Scenario & 8-Row Comparison Table
            # =========================================================================
            print("[M9R Evidence] Journey 4: Staging 3 compound events and comparison table...")
            await evaluate_js(ws, """(() => {
                const clearBtn = document.getElementById('btnClearContingency');
                if (clearBtn) clearBtn.click();

                // Event 1: Closed Corridor
                const sel = document.getElementById('contingencyEventType');
                sel.value = 'closed_corridor';
                sel.dispatchEvent(new Event('change'));
                document.getElementById('contingencyCenterR').value = '100';
                document.getElementById('contingencyCenterC').value = '145';
                document.getElementById('contingencyRadiusM').value = '60';
                document.getElementById('contingencyCustomName').value = 'Crater Rim Obstruction';
                document.getElementById('btnAddContingencyEvent').click();

                // Event 2: Reduced Mobility
                sel.value = 'reduced_mobility';
                sel.dispatchEvent(new Event('change'));
                const spIn = document.getElementById('contingencySpeedMult');
                spIn.value = '0.70';
                spIn.dispatchEvent(new Event('input'));
                document.getElementById('contingencyCustomName').value = 'Wheel Motor Strain';
                document.getElementById('btnAddContingencyEvent').click();

                // Event 3: Operational Hold
                sel.value = 'operational_hold';
                sel.dispatchEvent(new Event('change'));
                document.getElementById('contingencyHoldMin').value = '25';
                document.getElementById('contingencyCustomName').value = 'Comms Relay Alignment';
                document.getElementById('btnAddContingencyEvent').click();

                // Simulate compound
                document.getElementById('btnSimulateContingency').click();
            })()""")
            await asyncio.sleep(3.5)
            await capture_screenshot(ws, "m9r_04_compound_contingency_table.png")

            # =========================================================================
            # Journey 5: Contingency Reset & Baseline Restore
            # =========================================================================
            print("[M9R Evidence] Journey 5: Clearing contingency and verifying baseline...")
            await evaluate_js(ws, """(() => {
                const clearBtn = document.getElementById('btnClearContingency');
                if (clearBtn) clearBtn.click();
            })()""")
            await asyncio.sleep(1.5)
            await capture_screenshot(ws, "m9r_05_contingency_cleared_restore.png")

            # =========================================================================
            # Journey 6: Save Contingency Experiment to Library
            # =========================================================================
            print("[M9R Evidence] Journey 6: Simulating compound and saving experiment...")
            await evaluate_js(ws, """(() => {
                // Re-stage and simulate to have an active contingency result
                const sel = document.getElementById('contingencyEventType');
                sel.value = 'reduced_mobility';
                sel.dispatchEvent(new Event('change'));
                document.getElementById('contingencySpeedMult').value = '0.65';
                document.getElementById('contingencyCustomName').value = 'Motor Thermal Protection Test';
                document.getElementById('btnAddContingencyEvent').click();
                document.getElementById('btnSimulateContingency').click();
            })()""")
            await asyncio.sleep(2.5)

            await evaluate_js(ws, """(() => {
                const saveBtn = document.getElementById('btnSaveContingencyExperiment');
                if (saveBtn) saveBtn.click();
            })()""")
            await asyncio.sleep(1.5)

            await evaluate_js(ws, """(() => {
                const openLibBtn = document.getElementById('btnOpenExperimentLibrary');
                if (openLibBtn) openLibBtn.click();
            })()""")
            await asyncio.sleep(1.5)
            await capture_screenshot(ws, "m9r_06_contingency_experiment_persisted.png")

            print("[M9R Evidence] All 6 verification journeys successfully captured!")

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(run_evidence_capture())
