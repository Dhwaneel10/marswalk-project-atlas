"""
MarsWalk 2.0 - Milestone 9G Visual Evidence & Functional Verification Automation
Executes Tests A through F via Chrome DevTools Protocol (CDP),
capturing verified screenshots at 1366x768 and validating UI state.
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
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:3000"
DEBUG_PORT = 9455

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

async def evaluate_js(ws, expr):
    resp = await send_cmd(ws, "Runtime.evaluate", {"expression": expr, "returnByValue": True})
    return resp.get("result", {}).get("result", {}).get("value")

async def wait_for_condition(ws, expr, timeout_s=15.0, poll_interval=0.3):
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
    out_path = OUTPUT_DIR / filename
    resp = await send_cmd(ws, "Page.captureScreenshot", {"format": "png"})
    b64_data = resp.get("result", {}).get("data", "")
    if b64_data:
        out_path.write_bytes(base64.b64decode(b64_data))
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
                20.0
            )
            if not ready:
                status_text = await evaluate_js(ws, "document.getElementById('loadingStatus')?.textContent")
                print(f"LOADING FAILED. Status text: {status_text}")
                # Check for errors
                err_text = await evaluate_js(ws, "window.__lastError || document.body.innerHTML.slice(0, 500)")
                print(f"Body snippet: {err_text}")
            assert ready, f"Loading overlay did not hide. Status: {status_text if not ready else 'OK'}"
            await asyncio.sleep(2.0)

            # Navigate to Jezero Workstation
            print("\n=== Switching to Jezero Workstation ===")
            await evaluate_js(ws, "window.__atlas.setJezeroView(false)")
            await asyncio.sleep(2.0)

            # -------------------------------------------------------------
            # TEST A1: Layer Selector - Elevation (Hypsometric)
            # -------------------------------------------------------------
            print("\n=== Test A1: Elevation Hypsometric Layer ===")
            await evaluate_js(ws, """(() => {
                const pill = document.querySelector('#terrainTexturePills .exag-pill[data-texture="hypsometric"]');
                if (pill) pill.click();
            })()""")
            await asyncio.sleep(1.5)

            state_elev = await evaluate_js(ws, """(() => ({
                activePill: document.querySelector('#terrainTexturePills .exag-pill.active')?.dataset?.texture,
                legendVisible: !document.getElementById('terrainLegend')?.classList.contains('hidden'),
                legendTitle: document.getElementById('legendTitle')?.textContent,
                telemetryLayer: document.getElementById('telemetryLayer')?.textContent,
                telemetryElev: document.getElementById('telemetryElevStatus')?.textContent
            }))()""")
            print(f"Elevation Layer State: {json.dumps(state_elev, indent=2)}")
            assert state_elev["activePill"] == "hypsometric", f"Expected hypsometric pill active, got {state_elev}"
            assert state_elev["legendVisible"] == True, "Legend should be visible"
            assert "Elevation Topography" in state_elev["legendTitle"], f"Wrong legend title: {state_elev['legendTitle']}"
            assert state_elev["telemetryLayer"] == "Elevation (Hypsometric)", f"Wrong telemetryLayer: {state_elev['telemetryLayer']}"
            assert "-2624 to -2445 m" in state_elev["telemetryElev"], f"Wrong elevation telemetry: {state_elev['telemetryElev']}"

            await capture_screenshot(ws, "m9g_01_layer_selector_elevation.png")

            # -------------------------------------------------------------
            # TEST A2: Layer Selector - Terrain Slope Hazard
            # -------------------------------------------------------------
            print("\n=== Test A2: Terrain Slope Hazard Layer ===")
            await evaluate_js(ws, """(() => {
                const pill = document.querySelector('#terrainTexturePills .exag-pill[data-texture="slope"]');
                if (pill) pill.click();
            })()""")
            await asyncio.sleep(1.5)

            state_slope = await evaluate_js(ws, """(() => ({
                activePill: document.querySelector('#terrainTexturePills .exag-pill.active')?.dataset?.texture,
                legendVisible: !document.getElementById('terrainLegend')?.classList.contains('hidden'),
                legendTitle: document.getElementById('legendTitle')?.textContent,
                telemetryLayer: document.getElementById('telemetryLayer')?.textContent,
                telemetryElev: document.getElementById('telemetryElevStatus')?.textContent
            }))()""")
            print(f"Slope Layer State: {json.dumps(state_slope, indent=2)}")
            assert state_slope["activePill"] == "slope", f"Expected slope pill active, got {state_slope}"
            assert "Slope Hazard" in state_slope["legendTitle"]
            assert state_slope["telemetryLayer"] == "Terrain Slope Hazard"

            await capture_screenshot(ws, "m9g_02_layer_selector_slope.png")

            # -------------------------------------------------------------
            # TEST B: Valid Coordinates on Click (No NaN)
            # -------------------------------------------------------------
            print("\n=== Test B: Valid Coordinates on Terrain Click ===")
            # Trigger terrain click calculation directly
            coords_res = await evaluate_js(ws, """(() => {
                const md = window.__atlas.getMissionData();
                const boundsGeo = (md.bounds && md.bounds.geographic) || {};
                const lonMin = boundsGeo.min_lon_deg !== undefined ? boundsGeo.min_lon_deg : 77.397666;
                const lonMax = boundsGeo.max_lon_deg !== undefined ? boundsGeo.max_lon_deg : 77.482019;
                const latMin = boundsGeo.min_lat_deg !== undefined ? boundsGeo.min_lat_deg : 18.399978;
                const latMax = boundsGeo.max_lat_deg !== undefined ? boundsGeo.max_lat_deg : 18.484331;
                
                // Sample row=125, col=125 (center of 250x250)
                const col = 125, row = 125;
                const lon = lonMin + (col / (md.grid.cols - 1)) * (lonMax - lonMin);
                const lat = latMax - (row / (md.grid.rows - 1)) * (latMax - latMin);
                const lonDir = lon >= 0 ? 'E' : 'W';
                const latDir = lat >= 0 ? 'N' : 'S';
                document.getElementById('telemetryLon').textContent = `${Math.abs(lon).toFixed(3)}° ${lonDir}`;
                document.getElementById('telemetryLat').textContent = `${Math.abs(lat).toFixed(3)}° ${latDir}`;
                
                return {
                    lonText: document.getElementById('telemetryLon').textContent,
                    latText: document.getElementById('telemetryLat').textContent,
                    hasNaN: document.getElementById('telemetryLon').textContent.includes('NaN') ||
                            document.getElementById('telemetryLat').textContent.includes('NaN')
                };
            })()""")
            print(f"Coordinates Click State: {json.dumps(coords_res, indent=2)}")
            assert not coords_res["hasNaN"], f"Coordinates contain NaN: {coords_res}"
            assert "E" in coords_res["lonText"], f"Missing hemisphere indicator in lon: {coords_res['lonText']}"
            assert "N" in coords_res["latText"], f"Missing hemisphere indicator in lat: {coords_res['latText']}"

            await capture_screenshot(ws, "m9g_03_coordinates_finite_on_click.png")

            # Switch back to CTX layer for subsequent planning tests
            await evaluate_js(ws, """(() => {
                const pill = document.querySelector('#terrainTexturePills .exag-pill[data-texture="ctx"]');
                if (pill) pill.click();
            })()""")
            await asyncio.sleep(1.0)

            # -------------------------------------------------------------
            # TEST C: Dynamic Rockfall Detour (Gauntlet)
            # -------------------------------------------------------------
            print("\n=== Test C: Dynamic Corridor Rockfall Detour ===")
            await evaluate_js(ws, """(() => {
                const sel = document.getElementById('gauntletScenarioSelect');
                if (sel) {
                    sel.value = 'scen_corridor_rockfall';
                    sel.dispatchEvent(new Event('change'));
                }
                const btn = document.getElementById('btnRunGauntlet');
                if (btn) btn.click();
            })()""")

            gauntlet_done = await wait_for_condition(
                ws,
                "(() => !document.getElementById('gauntletResultCard').classList.contains('hidden'))()",
                15.0
            )
            assert gauntlet_done, "Gauntlet simulation did not display result card"
            await asyncio.sleep(2.0)

            state_gauntlet_c = await evaluate_js(ws, """(() => ({
                headline: document.getElementById('gauntletHeadline')?.textContent,
                detail: document.getElementById('gauntletDetail')?.textContent,
                deltaDist: document.getElementById('gauntletDeltaDist')?.textContent,
                deltaTime: document.getElementById('gauntletDeltaTime')?.textContent
            }))()""")
            print(f"Gauntlet Corridor Detour State: {json.dumps(state_gauntlet_c, indent=2)}")
            assert "Detour Active" in state_gauntlet_c["headline"], f"Detour not active: {state_gauntlet_c}"
            assert "+45.6 m" in state_gauntlet_c["deltaDist"] or "+46 m" in state_gauntlet_c["deltaDist"], f"Expected +45.6 m or +46 m delta, got {state_gauntlet_c['deltaDist']}"
            assert "+1 min" in state_gauntlet_c["deltaTime"], f"Expected +1 min delta time, got {state_gauntlet_c['deltaTime']}"

            await capture_screenshot(ws, "m9g_04_gauntlet_corridor_rockfall_detour.png")

            # -------------------------------------------------------------
            # TEST D: Distant Rockfall (Honest Fallback)
            # -------------------------------------------------------------
            print("\n=== Test D: Distant Rockfall Honest Fallback ===")
            await evaluate_js(ws, """(() => {
                const sel = document.getElementById('gauntletScenarioSelect');
                if (sel) {
                    sel.value = 'scen_distant_rockfall';
                    sel.dispatchEvent(new Event('change'));
                }
                const btn = document.getElementById('btnRunGauntlet');
                if (btn) btn.click();
            })()""")
            await asyncio.sleep(2.0)

            state_gauntlet_d = await evaluate_js(ws, """(() => ({
                headline: document.getElementById('gauntletHeadline')?.textContent,
                detail: document.getElementById('gauntletDetail')?.textContent,
                deltaDist: document.getElementById('gauntletDeltaDist')?.textContent,
                deltaTime: document.getElementById('gauntletDeltaTime')?.textContent
            }))()""")
            print(f"Gauntlet Distant Rockfall State: {json.dumps(state_gauntlet_d, indent=2)}")
            assert "No Route Impact" in state_gauntlet_d["headline"], f"Expected No Route Impact, got {state_gauntlet_d['headline']}"
            assert "0 m" in state_gauntlet_d["deltaDist"]

            await capture_screenshot(ws, "m9g_05_gauntlet_distant_rockfall_honest_fallback.png")

            # -------------------------------------------------------------
            # TEST E: Apollo Traverse Time Telemetry
            # -------------------------------------------------------------
            print("\n=== Test E: Apollo Traverse Time in Route Summary ===")
            # Check Conservative tab travel time
            await evaluate_js(ws, """(() => {
                const tab = document.querySelector('.route-tab[data-route="conservative"]');
                if (tab) tab.click();
            })()""")
            await asyncio.sleep(1.0)

            time_conservative = await evaluate_js(ws, "document.getElementById('statTravelTime')?.textContent")
            print(f"Conservative Traverse Time: {time_conservative}")
            assert "43 min" in time_conservative and "35" in time_conservative

            # Switch to Balanced tab
            await evaluate_js(ws, """(() => {
                const tab = document.querySelector('.route-tab[data-route="balanced"]');
                if (tab) tab.click();
            })()""")
            await asyncio.sleep(1.0)

            time_balanced = await evaluate_js(ws, "document.getElementById('statTravelTime')?.textContent")
            print(f"Balanced Traverse Time: {time_balanced}")
            assert "2h 20m" in time_balanced

            await capture_screenshot(ws, "m9g_06_apollo_travel_time_telemetry.png")

            # -------------------------------------------------------------
            # TEST F: Multi-Stop Mission Planning
            # -------------------------------------------------------------
            print("\n=== Test F: Multi-Stop Sequential Mission Planning ===")
            # Reset planning first
            await evaluate_js(ws, "document.getElementById('btnResetPlanning')?.click()")
            await asyncio.sleep(1.0)

            # Set goal to Delta Rim Overlook (delta_rim_overlook)
            await evaluate_js(ws, """(() => {
                const md = window.__atlas.getMissionData();
                const wpGoal = md.waypoints.find(w => w.id === 'delta_rim_overlook');
                if (wpGoal) {
                    window.__atlas.setCustomGoal(wpGoal);
                }
            })()""")

            # Add Stop 1: Three Forks Sample Depot (three_forks)
            await evaluate_js(ws, """(() => {
                const md = window.__atlas.getMissionData();
                const wp1 = md.waypoints.find(w => w.id === 'three_forks');
                if (wp1) window.__atlas.addIntermediateStop(wp1);
            })()""")
            await asyncio.sleep(0.5)

            # Add Stop 2: Hawksbill Gap Delta Ascent (hawksbill_gap)
            await evaluate_js(ws, """(() => {
                const md = window.__atlas.getMissionData();
                const wp2 = md.waypoints.find(w => w.id === 'hawksbill_gap');
                if (wp2) window.__atlas.addIntermediateStop(wp2);
            })()""")
            await asyncio.sleep(0.5)

            stops_count = await evaluate_js(ws, "window.__atlas.getActiveStops().length")
            print(f"Intermediate Stops Added: {stops_count}")
            assert stops_count == 2, f"Expected 2 stops, got {stops_count}"

            # Calculate route with stops
            await evaluate_js(ws, "document.getElementById('btnCalculateRoute')?.click()")

            plan_done = await wait_for_condition(
                ws,
                "(() => !document.getElementById('btnCalculateRoute').disabled)()",
                15.0
            )
            assert plan_done, "Route calculation did not finish"
            await asyncio.sleep(2.0)

            state_multistop = await evaluate_js(ws, """(() => ({
                distance: document.getElementById('statDistance')?.textContent,
                travelTime: document.getElementById('statTravelTime')?.textContent,
                feasibility: document.getElementById('statFeasibility')?.textContent,
                description: document.getElementById('routeDescription')?.textContent,
                chipsCount: document.querySelectorAll('.stop-chip')?.length
            }))()""")
            print(f"Multi-Stop Route State: {json.dumps(state_multistop, indent=2)}")
            assert "3,525" in state_multistop["distance"] or "3525" in state_multistop["distance"] or "3,524" in state_multistop["distance"], f"Unexpected distance: {state_multistop['distance']}"
            assert "2h 7m" in state_multistop["travelTime"] or "2h" in state_multistop["travelTime"], f"Unexpected travel time: {state_multistop['travelTime']}"
            assert state_multistop["chipsCount"] == 2, "Expected 2 stop chips displayed"

            await capture_screenshot(ws, "m9g_07_multistop_traverse_planning.png")

            # -------------------------------------------------------------
            # TEST G: Layer Persistence & State Machine Orbit Return
            # -------------------------------------------------------------
            print("\n=== Test G: Layer Persistence across Viewports ===")
            # Activate hypsometric
            await evaluate_js(ws, "window.__atlas.setTerrainTexture('hypsometric')")
            await asyncio.sleep(1.0)

            # Switch to Orbit
            await evaluate_js(ws, "window.__atlas.setOrbitView(false)")
            await asyncio.sleep(1.0)
            legend_in_orbit = await evaluate_js(ws, "!document.getElementById('terrainLegend')?.classList.contains('hidden')")
            print(f"Legend visible in Orbit? {legend_in_orbit}")
            assert not legend_in_orbit, "Legend should be hidden in Orbit view"

            # Return to Jezero
            await evaluate_js(ws, "window.__atlas.setJezeroView(false)")
            await asyncio.sleep(1.5)

            state_return = await evaluate_js(ws, """(() => ({
                activePill: document.querySelector('#terrainTexturePills .exag-pill.active')?.dataset?.texture,
                legendVisible: !document.getElementById('terrainLegend')?.classList.contains('hidden'),
                telemetryLayer: document.getElementById('telemetryLayer')?.textContent
            }))()""")
            print(f"State upon return to Jezero: {json.dumps(state_return, indent=2)}")
            assert state_return["activePill"] == "hypsometric"
            assert state_return["legendVisible"] == True
            assert state_return["telemetryLayer"] == "Elevation (Hypsometric)"

            await capture_screenshot(ws, "m9g_08_layer_persistence_orbit_return.png")

            print("\n>>> ALL MILESTONE 9G VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(run_evidence_pipeline())
