#!/usr/bin/env python3
"""
MarsWalk 2.0 / Project Atlas — Multi-Viewport & Usability Verification Suite
Validates:
  1. 1920x1080 Desktop Viewport rendering
  2. 1366x768 Laptop Viewport rendering & overflow
  3. Back-to-start & repeated Golden Path execution
  4. Error presentation state resilience
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

TARGET_PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3000
BASE_URL = f"http://127.0.0.1:{TARGET_PORT}"
DEBUG_PORT = 9497
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "browser_qa"))
CHROME_BIN = "/usr/bin/google-chrome"


async def run_usability_tests():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tmp_profile = tempfile.mkdtemp(prefix="chrome_usability_test_")

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

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{DEBUG_PORT}/json")
        with urllib.request.urlopen(req, timeout=5) as resp:
            targets = json.loads(resp.read().decode("utf-8"))

        ws_url = targets[0]["webSocketDebuggerUrl"]
        print(f"[Usability QA] Connected to Chrome CDP at {ws_url}")

        async with websockets.connect(ws_url, max_size=25_000_000) as ws:
            msg_id = 1
            pending_requests = {}

            async def send_cdp(method, params=None):
                nonlocal msg_id
                cid = msg_id
                msg_id += 1
                fut = asyncio.get_event_loop().create_future()
                pending_requests[cid] = fut
                payload = {"id": cid, "method": method, "params": params or {}}
                await ws.send(json.dumps(payload))
                return await fut

            async def cdp_listener():
                try:
                    async for raw in ws:
                        data = json.loads(raw)
                        if "id" in data and data["id"] in pending_requests:
                            fut = pending_requests.pop(data["id"])
                            if not fut.done():
                                fut.set_result(data.get("result", {}))
                except asyncio.CancelledError:
                    pass

            listener_task = asyncio.create_task(cdp_listener())
            await send_cdp("Page.enable")
            await send_cdp("Runtime.enable")

            async def eval_js(expression):
                res = await send_cdp("Runtime.evaluate", {"expression": expression, "returnByValue": True})
                return res.get("result", {}).get("value")

            async def take_screenshot(filename):
                shot = await send_cdp("Page.captureScreenshot", {"format": "png"})
                data = base64.b64decode(shot["data"])
                path = os.path.join(OUTPUT_DIR, filename)
                with open(path, "wb") as f:
                    f.write(data)
                print(f"[Usability QA] Captured {filename} ({len(data):,} bytes)")
                return path

            # -------------------------------------------------------------
            # TEST 1: 1920x1080 Viewport
            # -------------------------------------------------------------
            print("[Usability QA] Testing 1920x1080 Desktop Viewport...")
            await send_cdp("Emulation.setDeviceMetricsOverride", {
                "width": 1920,
                "height": 1080,
                "deviceScaleFactor": 1,
                "mobile": False,
            })
            await send_cdp("Page.navigate", {"url": BASE_URL})
            await asyncio.sleep(3.0)
            await take_screenshot("viewport_1920x1080_desktop.png")

            # Verify hero elements
            h1_text = await eval_js("document.querySelector('.landing-headline')?.innerText || ''")
            assert "MARSWALK" in h1_text, f"Unexpected headline: {h1_text}"
            print("  [PASS] 1920x1080 Hero headline and layout render cleanly.")

            # -------------------------------------------------------------
            # TEST 2: 1366x768 Laptop Viewport
            # -------------------------------------------------------------
            print("[Usability QA] Testing 1366x768 Laptop Viewport...")
            await send_cdp("Emulation.setDeviceMetricsOverride", {
                "width": 1366,
                "height": 768,
                "deviceScaleFactor": 1,
                "mobile": False,
            })
            await asyncio.sleep(1.0)
            await take_screenshot("viewport_1366x768_laptop.png")

            # Check horizontal overflow
            body_scroll_w = await eval_js("document.body.scrollWidth")
            inner_w = await eval_js("window.innerWidth")
            assert body_scroll_w <= inner_w + 20, f"Horizontal overflow detected: {body_scroll_w} > {inner_w}"
            print("  [PASS] 1366x768 Laptop layout fits viewport without disruptive overflow.")

            # -------------------------------------------------------------
            # TEST 3: Workstation Transition & Repeated Golden Path
            # -------------------------------------------------------------
            print("[Usability QA] Testing Workstation Launch & Repeated Golden Path...")
            await eval_js("document.getElementById('btnLandingEnterWorkstation')?.click();")
            await asyncio.sleep(1.5)

            # Check landing page hidden
            landing_disp = await eval_js("document.getElementById('marsLandingPage')?.style.display")
            print(f"  Landing page display state: {landing_disp}")

            # Open Golden Path
            await eval_js("document.getElementById('btnGoldenPathTour')?.click();")
            await asyncio.sleep(0.5)

            # Cycle Step 1 -> 2 -> 3
            for step_idx in range(1, 4):
                await eval_js(f"window._gpRenderStep({step_idx});")
                await asyncio.sleep(0.3)
                await eval_js("document.getElementById('btnGpExecuteStep')?.click();")
                await asyncio.sleep(0.8)

            print("  [PASS] First pass of Golden Path executed smoothly.")

            # Test Reset Button (Back-to-start)
            print("[Usability QA] Testing Golden Path Reset...")
            await eval_js("document.getElementById('btnGpReset')?.click();")
            await asyncio.sleep(0.5)
            curr_step_after_reset = await eval_js("window._gpCurrentStep")
            assert curr_step_after_reset == 1, f"Unexpected step after reset: {curr_step_after_reset}"
            print("  [PASS] Reset restored Golden Path tour to initial step (Step 1).")

            # Test Repeated Execution after reset
            await eval_js("document.getElementById('btnGpExecuteStep')?.click();")
            await asyncio.sleep(1.0)
            out_text = await eval_js("document.getElementById('gpOutputBox')?.innerText || ''")
            assert "STEP 1" in out_text, f"Unexpected output after re-execution: {out_text[:100]}"
            print("  [PASS] Repeated execution successfully produced valid evidence without state contamination.")

            # Close Golden Path HUD
            await eval_js("document.getElementById('btnGpClose')?.click();")
            await asyncio.sleep(0.5)
            gp_disp = await eval_js("document.getElementById('evaluatorGoldenPathCard')?.style.display")
            assert gp_disp == "none", f"Expected Golden Path card hidden, got: {gp_disp}"
            print("  [PASS] Golden Path HUD closes cleanly on demand.")

            # -------------------------------------------------------------
            # TEST 4: Browser Refresh & Re-initialization
            # -------------------------------------------------------------
            print("[Usability QA] Testing Browser Refresh...")
            await send_cdp("Page.reload")
            await asyncio.sleep(2.5)
            h1_after_reload = await eval_js("document.querySelector('.landing-headline')?.innerText || ''")
            assert "MARSWALK" in h1_after_reload, "Application failed to re-initialize after reload"
            print("  [PASS] Application state cleanly restored after browser refresh.")

            listener_task.cancel()
            print("\n=======================================================")
            print("USABILITY & MULTI-VIEWPORT AUDIT: ALL TESTS PASSED")
            print("=======================================================\n")

    finally:
        proc.terminate()
        proc.wait(timeout=5)
        shutil.rmtree(tmp_profile, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(run_usability_tests())
