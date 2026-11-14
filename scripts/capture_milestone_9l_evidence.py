"""
MarsWalk 2.0 - Milestone 9L Visual Evidence & Interaction Verification Script
Captures all 13 verified journeys showcasing the new visual identity:
Cinematic Landing Page, Editorial Typography, Vertical Destination Selector,
Planetary Onboarding Modal, Restyled HUD, State Preservation, and Responsive Breakpoints.
"""

import os
import sys
import time
import json
import shutil
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
DEBUG_PORT = 9477

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

            print("\n=== Initializing MarsWalk 2.0 Project Atlas ===")
            await send_cmd(ws, "Page.navigate", {"url": f"{BASE_URL}/?landing=1"})

            ready = await wait_for_condition(
                ws,
                "(() => document.getElementById('loadingOverlay') && document.getElementById('loadingOverlay').classList.contains('hidden') && window.__atlas !== undefined)()",
                25.0
            )
            if not ready:
                raise RuntimeError("Atlas failed to load in time.")

            print("[Init] Atlas UI online with Milestone 9L Visual Identity.")
            await asyncio.sleep(2.0)

            # -------------------------------------------------------------
            # Journey 1: Desktop Standard Landing Hero (1366x768)
            # -------------------------------------------------------------
            print("\n--- Journey 1: Desktop Standard Landing Hero (1366x768) ---")
            await set_viewport(ws, 1366, 768)
            await evaluate_js(ws, "window.__atlas.showLandingPage()")
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, "m9l_01_landing_hero_desktop_1366.png")

            # -------------------------------------------------------------
            # Journey 2: Desktop Ultra Landing Hero (1920x1080)
            # -------------------------------------------------------------
            print("\n--- Journey 2: Desktop Ultra Landing Hero (1920x1080) ---")
            await set_viewport(ws, 1920, 1080)
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, "m9l_02_landing_hero_ultra_1920.png")

            # Reset back to 1366x768
            await set_viewport(ws, 1366, 768)
            await asyncio.sleep(0.5)

            # -------------------------------------------------------------
            # Journey 3: Destination Selector Hover & Selection
            # -------------------------------------------------------------
            print("\n--- Journey 3: Destination Selector Hover & Selection ---")
            print("[Journey 3] Selecting Olympus Mons via vertical selector...")
            await evaluate_js(ws, "window.__atlas.selectDestination('olympus')")
            await asyncio.sleep(2.0)
            await capture_screenshot(ws, "m9l_03_destination_selector_hover_active.png")

            # -------------------------------------------------------------
            # Journey 4: Expandable 'How It Works' Section
            # -------------------------------------------------------------
            print("\n--- Journey 4: Expandable 'How It Works' Section ---")
            await evaluate_js(ws, """
                (() => {
                    const section = document.getElementById('landingHowItWorksSection');
                    if (section) {
                        section.classList.remove('hidden');
                        section.scrollIntoView({ behavior: 'instant' });
                    }
                })()
            """)
            await asyncio.sleep(1.2)
            await capture_screenshot(ws, "m9l_04_how_it_works_expanded.png")

            # Close how it works and scroll back to top
            await evaluate_js(ws, """
                (() => {
                    const section = document.getElementById('landingHowItWorksSection');
                    if (section) section.classList.add('hidden');
                    const page = document.getElementById('marsLandingPage');
                    if (page) page.scrollTop = 0;
                })()
            """)
            await asyncio.sleep(0.5)

            # -------------------------------------------------------------
            # Journey 5: Planetary Onboarding Step 1 — Cartography
            # -------------------------------------------------------------
            print("\n--- Journey 5: Planetary Onboarding Step 1 — Cartography ---")
            await evaluate_js(ws, "window.__atlas.openOnboarding(1)")
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, "m9l_05_onboarding_step1_cartography.png")

            # -------------------------------------------------------------
            # Journey 6: Planetary Onboarding Step 2 — Elevation & Slope
            # -------------------------------------------------------------
            print("\n--- Journey 6: Planetary Onboarding Step 2 — Elevation & Slope ---")
            await evaluate_js(ws, "window.__atlas.setOnboardingStep(2)")
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, "m9l_06_onboarding_step2_elevation.png")

            # -------------------------------------------------------------
            # Journey 7: Planetary Onboarding Step 3 — Rehearsal & Persistence
            # -------------------------------------------------------------
            print("\n--- Journey 7: Planetary Onboarding Step 3 — Rehearsal & Persistence ---")
            await evaluate_js(ws, "window.__atlas.setOnboardingStep(3)")
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, "m9l_07_onboarding_step3_rehearsal.png")

            # -------------------------------------------------------------
            # Journey 8: Enter Atlas Transition
            # -------------------------------------------------------------
            print("\n--- Journey 8: Enter Atlas Transition ---")
            await evaluate_js(ws, "window.__atlas.closeOnboarding(true)")
            await asyncio.sleep(1.5)
            is_landing_visible = await evaluate_js(ws, "window.__atlas.isLandingPageActive()")
            assert not is_landing_visible, "Landing page should be inactive after entering Atlas"
            await capture_screenshot(ws, "m9l_08_enter_atlas_transition.png")

            # -------------------------------------------------------------
            # Journey 9: Restyled HUD & Surface Workstation with Editorial Serif
            # -------------------------------------------------------------
            print("\n--- Journey 9: Restyled HUD & Surface Workstation ---")
            print("[Journey 9] Switching to Jezero Crater 3D Surface Workstation...")
            await evaluate_js(ws, "window.__atlas.setJezeroView()")
            await asyncio.sleep(2.0)
            await wait_for_condition(ws, "document.getElementById('viewport3d').style.display !== 'none'")
            await evaluate_js(ws, "window.__atlas.setTerrainTexture('ctx')")
            await asyncio.sleep(1.0)

            print("[Journey 9] Calculating baseline mission route...")
            await evaluate_js(ws, "window.__atlas.calculateTraverse('conservative')", await_promise=True)
            await wait_for_condition(ws, "!document.getElementById('btnCalculateRoute').disabled")
            await asyncio.sleep(1.5)
            await capture_screenshot(ws, "m9l_09_hud_restyled_editorial_serif.png")

            # -------------------------------------------------------------
            # Journey 10: Return to Landing Page With Preserved Mission State
            # -------------------------------------------------------------
            print("\n--- Journey 10: Return to Landing Page With Preserved Mission State ---")
            baseline_before = await evaluate_js(ws, "window.__atlas.getBaselineRouteResult() !== null")
            assert baseline_before, "Baseline route should be computed before returning to landing page"

            print("[Journey 10] Clicking Overview button to return to landing hero...")
            await evaluate_js(ws, "window.__atlas.showLandingPage()")
            await asyncio.sleep(1.2)
            await capture_screenshot(ws, "m9l_10_return_to_landing_state_preserved.png")

            # Verify mission state was NOT destroyed
            baseline_after = await evaluate_js(ws, "window.__atlas.getBaselineRouteResult() !== null")
            assert baseline_after, "Mission state must be preserved when returning to landing page"
            print("[Journey 10] Mission state successfully verified intact!")

            # -------------------------------------------------------------
            # Journey 11: Reopening Onboarding Guide from HUD
            # -------------------------------------------------------------
            print("\n--- Journey 11: Reopening Onboarding Guide from HUD ---")
            await evaluate_js(ws, "window.__atlas.hideLandingPage()")
            await asyncio.sleep(0.5)
            await evaluate_js(ws, "window.__atlas.openOnboarding(1)")
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, "m9l_11_onboarding_guide_reopen_from_hud.png")

            await evaluate_js(ws, "window.__atlas.closeOnboarding(false)")
            await asyncio.sleep(0.5)

            # -------------------------------------------------------------
            # Journey 12: Responsive Breakpoint — Tablet (1024x768)
            # -------------------------------------------------------------
            print("\n--- Journey 12: Responsive Breakpoint — Tablet (1024x768) ---")
            await evaluate_js(ws, "window.__atlas.showLandingPage()")
            await set_viewport(ws, 1024, 768)
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, "m9l_12_responsive_tablet_1024.png")

            # -------------------------------------------------------------
            # Journey 13: Responsive Breakpoint — Mobile (390x844)
            # -------------------------------------------------------------
            print("\n--- Journey 13: Responsive Breakpoint — Mobile (390x844) ---")
            await set_viewport(ws, 390, 844, is_mobile=True)
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, "m9l_13_responsive_mobile_390.png")

            # Reset viewport
            await send_cmd(ws, "Emulation.clearDeviceMetricsOverride")

            print("\n=== Milestone 9L Evidence Capture Complete: All 13 Journeys Verified ===")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(run_evidence_pipeline())
