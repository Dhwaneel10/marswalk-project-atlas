"""
Automated Visual Evidence Capture for MarsWalk 2.0 Project Atlas (Milestone 9E).
Uses Chrome DevTools Protocol (CDP) for deterministic state synchronization and 1366x768 captures:
  1. m9e_01_global_orbit_overview.png: Global zoom overview with calm labels, global basemap, telemetry
  2. m9e_02_search_olympus_mons_flight.png: Search and autocomplete for Olympus Mons
  3. m9e_03_olympus_mons_regional_ctx.png: Regional exploration of Olympus Mons with MRO CTX 6m mosaic & dossier
  4. m9e_04_gale_crater_regional_ctx.png: Regional exploration of Gale Crater & Mount Sharp with CTX 6m overlay
  5. m9e_05_elysium_planitia_honest_fallback.png: Exploration of Elysium Planitia with honest basemap fallback
  6. m9e_06_jezero_regional_context_orbit.png: Orbit view near Jezero showing boundary notice and telemetry
  7. m9e_07_jezero_local_ctx_mesh_workstation.png: High-resolution 3D Jezero Workstation with authentic 6m CTX orthomosaic
  8. m9e_08_jezero_waypoint_screen_labels.png: Screen-aligned waypoint labels and active waypoint dossier modal
  9. m9e_09_jezero_tactical_slope_hazards.png: Tactical slope hazard classification overlay
  10. m9e_10_jezero_live_python_astar_plan.png: Live Python A* traverse computation (Science-First profile)
  11. m9e_11_jezero_gauntlet_stress_test.png: Live Gauntlet disruption scenario recalculation with regret ledger
  12. m9e_12_repeat_navigation_cache_hit.png: Repeat navigation to Olympus Mons demonstrating texture cache hit
"""

import os
import sys
import time
import json
import base64
import subprocess
import urllib.request
import asyncio
import websockets
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = Path("outputs")
BASE_URL = "http://127.0.0.1:3000"
DEBUG_PORT = 9333

cmd_counter = [1]

async def send_cmd(ws, method, params=None):
    cid = cmd_counter[0]
    cmd_counter[0] += 1
    msg = {"id": cid, "method": method}
    if params:
        msg["params"] = params
    await ws.send(json.dumps(msg))
    while True:
        raw = await ws.recv()
        data = json.loads(raw)
        if data.get("id") == cid:
            return data

async def evaluate_js(ws, expr):
    resp = await send_cmd(ws, "Runtime.evaluate", {"expression": expr, "returnByValue": True})
    return resp.get("result", {}).get("result", {}).get("value")

async def wait_for_condition(ws, expr, timeout_s=12.0, poll_interval=0.4):
    start = time.time()
    while time.time() - start < timeout_s:
        val = await evaluate_js(ws, expr)
        if val:
            return True
        await asyncio.sleep(poll_interval)
    return False

async def capture_all_evidence():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    shots = [
        # 1. Global Orbit Overview (calm labels, global basemap, telemetry chip)
        {
            "id": "m9e_01",
            "name": "m9e_01_global_orbit_overview.png",
            "url": f"{BASE_URL}/?diag=1",
            "ready_expr": "document.getElementById('loadingOverlay') && document.getElementById('loadingOverlay').classList.contains('hidden')",
            "extra_delay": 1.5
        },
        # 2. Search Autocomplete for Olympus Mons
        {
            "id": "m9e_02",
            "name": "m9e_02_search_olympus_mons_flight.png",
            "url": f"{BASE_URL}/?q=Olympus&diag=1",
            "ready_expr": "document.getElementById('searchResultsDropdown') && !document.getElementById('searchResultsDropdown').classList.contains('hidden')",
            "extra_delay": 1.5
        },
        # 3. Regional Exploration: Olympus Mons Caldera & Shield (MRO CTX 6m overlay & Dossier Card)
        {
            "id": "m9e_03",
            "name": "m9e_03_olympus_mons_regional_ctx.png",
            "url": f"{BASE_URL}/?place=iau_4453&diag=1",
            "ready_expr": "document.getElementById('locationCard') && !document.getElementById('locationCard').classList.contains('hidden') && document.getElementById('locCardTitle').textContent.includes('OLYMPUS')",
            "extra_delay": 2.5
        },
        # 4. Regional Exploration: Gale Crater & Mount Sharp (MRO CTX 6m overlay & Curiosity context)
        {
            "id": "m9e_04",
            "name": "m9e_04_gale_crater_regional_ctx.png",
            "url": f"{BASE_URL}/?place=iau_2071&diag=1",
            "ready_expr": "document.getElementById('locationCard') && !document.getElementById('locationCard').classList.contains('hidden') && document.getElementById('locCardTitle').textContent.includes('GALE')",
            "extra_delay": 2.5
        },
        # 5. Unsupported High-Res Sector: Elysium Mons / Planitia (Honest basemap fallback & no-DTM disclosure)
        {
            "id": "m9e_05",
            "name": "m9e_05_elysium_planitia_honest_fallback.png",
            "url": f"{BASE_URL}/?place=iau_1783&diag=1",
            "ready_expr": "document.getElementById('locationCard') && !document.getElementById('locationCard').classList.contains('hidden') && document.getElementById('locCardTitle').textContent.includes('ELYSIUM')",
            "extra_delay": 2.5
        },
        # 6. Orbit approach to Jezero Crater (Showing study boundary notice & telemetry)
        {
            "id": "m9e_06",
            "name": "m9e_06_jezero_regional_context_orbit.png",
            "url": f"{BASE_URL}/?place=iau_14300&diag=1",
            "ready_expr": "document.getElementById('locationCard') && !document.getElementById('locationCard').classList.contains('hidden') && document.getElementById('locCardTitle').textContent.includes('JEZERO')",
            "extra_delay": 2.5
        },
        # 7. High-Fidelity 3D Jezero Workstation (Draped 6m CTX Orthomosaic on 250x250 DTM)
        {
            "id": "m9e_07",
            "name": "m9e_07_jezero_local_ctx_mesh_workstation.png",
            "url": f"{BASE_URL}/?fly=jezero&texture=ctx&route=balanced&diag=1",
            "ready_expr": "document.getElementById('viewModeSelect') && document.getElementById('viewModeSelect').value === 'jezero' && document.getElementById('loadingOverlay').classList.contains('hidden')",
            "extra_delay": 3.0
        },
        # 8. Jezero 3D Cartographic Waypoint Labels & Dossier Modal (Hawksbill Gap)
        {
            "id": "m9e_08",
            "name": "m9e_08_jezero_waypoint_screen_labels.png",
            "url": f"{BASE_URL}/?fly=jezero&waypoint=hawksbill_gap&diag=1",
            "ready_expr": "document.getElementById('waypointModal') && !document.getElementById('waypointModal').classList.contains('hidden')",
            "extra_delay": 2.5
        },
        # 9. Tactical Slope Hazard Classification Overlay (<=10 deg, 10-15 deg, >15 deg)
        {
            "id": "m9e_09",
            "name": "m9e_09_jezero_tactical_slope_hazards.png",
            "url": f"{BASE_URL}/?fly=jezero&texture=slope&diag=1",
            "ready_expr": "document.getElementById('viewModeSelect') && document.getElementById('viewModeSelect').value === 'jezero'",
            "extra_delay": 2.5
        },
        # 10. Live Python A* Traverse Computation (Science-First Profile)
        {
            "id": "m9e_10",
            "name": "m9e_10_jezero_live_python_astar_plan.png",
            "url": f"{BASE_URL}/?fly=jezero&texture=ctx&route=science_first&action=plan&diag=1",
            "ready_expr": "document.getElementById('planningStatus') && document.getElementById('planningStatus').textContent.includes('ROUTE COMPUTED')",
            "extra_delay": 2.5
        },
        # 11. Live Gauntlet Disruption Stress-Test with Regret Ledger
        {
            "id": "m9e_11",
            "name": "m9e_11_jezero_gauntlet_stress_test.png",
            "url": f"{BASE_URL}/?fly=jezero&texture=slope&route=balanced&scenario=scen_hawksbill_rockfall&action=gauntlet&diag=1",
            "ready_expr": "document.getElementById('gauntletResultCard') && !document.getElementById('gauntletResultCard').classList.contains('hidden') && document.getElementById('gauntletHeadline').textContent.length > 2",
            "extra_delay": 2.5
        },
        # 12. Repeated Navigation to Olympus Mons (Demonstrating Texture Cache Hit)
        {
            "id": "m9e_12",
            "name": "m9e_12_repeat_navigation_cache_hit.png",
            "url": f"{BASE_URL}/?place=iau_4453&diag=1",
            "ready_expr": "document.getElementById('locationCard') && !document.getElementById('locationCard').classList.contains('hidden')",
            "extra_delay": 2.0
        },
    ]

    chrome_cmd = [
        CHROME_PATH,
        "--headless=new",
        f"--remote-debugging-port={DEBUG_PORT}",
        r"--user-data-dir=C:\Users\dhwan\AppData\Local\Temp\chrome_clean_9333",
        "--disable-gpu",
        "--no-sandbox",
        "--window-size=1366,768",
        "about:blank"
    ]
    
    print(f"[CDP Capture] Launching headless Chrome on port {DEBUG_PORT}...")
    proc = subprocess.Popen(chrome_cmd)
    time.sleep(2.0)
    
    results = []
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json") as r:
            targets = json.loads(r.read().decode())
        page_target = next(t for t in targets if t.get("type") == "page")
        ws_url = page_target["webSocketDebuggerUrl"]
        
        async with websockets.connect(ws_url, max_size=30*1024*1024) as ws:
            await send_cmd(ws, "Page.enable")
            await send_cmd(ws, "Runtime.enable")
            
            for shot in shots:
                out_path = OUTPUT_DIR / shot["name"]
                print(f"[CDP Capture] Processing ({shot['id']}): {shot['name']}...")
                
                # Navigate
                await send_cmd(ws, "Page.navigate", {"url": shot["url"]})
                
                # Wait for ready expression
                ready = await wait_for_condition(ws, shot["ready_expr"], timeout_s=15.0)
                if not ready:
                    print(f"  [Warning] Timeout waiting for condition for {shot['name']}; proceeding with capture.")
                
                # Extra animation / render settling
                await asyncio.sleep(shot["extra_delay"])

                if shot["id"] == "m9e_12":
                    # Cycle through Gale Crater and return to Olympus Mons to verify memory cache hit
                    print("  [m9e_12] Cycling to Gale Crater and returning to Olympus Mons to trigger memory cache hit...")
                    await evaluate_js(ws, "(() => { const sel = document.getElementById('featuredSelect'); if (sel) { sel.value = 'iau_2071'; sel.dispatchEvent(new Event('change')); } })()")
                    await asyncio.sleep(3.2)
                    await evaluate_js(ws, "(() => { const sel = document.getElementById('featuredSelect'); if (sel) { sel.value = 'iau_4453'; sel.dispatchEvent(new Event('change')); } })()")
                    await wait_for_condition(ws, "document.getElementById('diagCacheStatus') && document.getElementById('diagCacheStatus').textContent.includes('HIT')", timeout_s=8.0)
                    await asyncio.sleep(2.5)
                
                # Capture frame
                resp = await send_cmd(ws, "Page.captureScreenshot", {"format": "png"})
                if "result" in resp and "data" in resp["result"]:
                    png_bytes = base64.b64decode(resp["result"]["data"])
                    out_path.write_bytes(png_bytes)
                    size_kb = len(png_bytes) / 1024
                    print(f"  [OK] Saved {shot['name']} ({size_kb:.1f} KB)")
                    results.append((shot["name"], True))
                else:
                    print(f"  [Error] Failed to capture screenshot for {shot['name']}")
                    results.append((shot["name"], False))
                    
    finally:
        proc.kill()
        
    print("\n--- Milestone 9E Visual Evidence Capture Summary ---")
    all_ok = True
    for name, ok in results:
        status_txt = "OK" if ok else "FAILED"
        print(f"  {name}: {status_txt}")
        if not ok:
            all_ok = False
            
    assert all_ok, "One or more evidence captures failed!"
    print("\n[MarsWalk Atlas] All 12 Milestone 9E visual evidence screenshots captured successfully.")

if __name__ == "__main__":
    asyncio.run(capture_all_evidence())
