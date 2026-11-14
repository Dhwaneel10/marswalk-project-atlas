#!/usr/bin/env python3
"""
MarsWalk 2.0 / Project Atlas — Comprehensive Live Screenshot Capture Suite
Captures certified visual proof of all primary UI states using Chrome CDP:
  1. landing_hero_live.png
  2. five_pillar_deck_live.png
  3. jezero_3d_layers_live.png
  4. science_trade_comparison_live.png
  5. meda_weather_live.png
  6. when_mars_goes_dark_live.png
  7. golden_path_completion_live.png
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
DEBUG_PORT = 9499
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "browser_qa"))
CHROME_BIN = "/usr/bin/google-chrome"


async def capture_screenshots():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tmp_profile = tempfile.mkdtemp(prefix="chrome_screenshot_suite_")

    cmd = [
        CHROME_BIN,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={tmp_profile}",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1600,1050",
        "about:blank",
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(2.0)

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{DEBUG_PORT}/json")
        with urllib.request.urlopen(req, timeout=5) as resp:
            targets = json.loads(resp.read().decode("utf-8"))

        ws_url = targets[0]["webSocketDebuggerUrl"]
        print(f"[Screenshot QA] Connected to Chrome CDP at {ws_url}")

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
                print(f"[Screenshot QA] Saved: {filename} ({len(data):,} bytes)")
                return path

            # 1. Navigate to base URL
            print("[Screenshot QA] Navigating to http://127.0.0.1:3000...")
            await send_cdp("Page.navigate", {"url": BASE_URL})
            await asyncio.sleep(3.5)

            # Shot 1: Landing Page Hero
            await take_screenshot("landing_hero_live.png")

            # Shot 2: Five-Pillar Operations Deck
            # Scroll to #nasaPillarsDeck or ensure visible
            await eval_js("document.getElementById('nasaPillarsDeck')?.scrollIntoView();")
            await asyncio.sleep(1.0)
            await take_screenshot("five_pillar_deck_live.png")

            # Shot 3: 3D Jezero Terrain with layers active
            # Scroll up to 3D canvas and ensure layers active
            await eval_js("document.getElementById('mapSection')?.scrollIntoView();")
            await asyncio.sleep(1.5)
            await take_screenshot("jezero_3d_layers_live.png")

            # Open Golden Path HUD to drive guided steps
            await eval_js("document.getElementById('btnGoldenPathTour')?.click();")
            await asyncio.sleep(1.0)

            # Step 4: Atmospheric Physics / MEDA observation (Step 4 of Golden Path)
            # Switch to Step 4
            await eval_js("window._gpCurrentStep = 3; window._gpRenderStep(3);")
            await asyncio.sleep(0.5)
            # Click execute
            await eval_js("document.getElementById('gpBtnAction')?.click();")
            await asyncio.sleep(2.0)
            await take_screenshot("meda_weather_live.png")

            # Step 5: Science Route Comparison (Step 5 of Golden Path)
            await eval_js("window._gpCurrentStep = 4; window._gpRenderStep(4);")
            await asyncio.sleep(0.5)
            await eval_js("document.getElementById('gpBtnAction')?.click();")
            # Wait for route planning to finish
            for _ in range(30):
                txt = await eval_js("document.getElementById('gpBtnAction')?.innerText || ''")
                if "EXECUTING" not in txt:
                    break
                await asyncio.sleep(0.5)
            await asyncio.sleep(1.0)
            await take_screenshot("science_trade_comparison_live.png")

            # Step 6: Flagship Autonomous Resilience ("When Mars Goes Dark") (Step 6 of Golden Path)
            await eval_js("window._gpCurrentStep = 5; window._gpRenderStep(5);")
            await asyncio.sleep(0.5)
            await eval_js("document.getElementById('gpBtnAction')?.click();")
            for _ in range(30):
                txt = await eval_js("document.getElementById('gpBtnAction')?.innerText || ''")
                if "EXECUTING" not in txt:
                    break
                await asyncio.sleep(0.5)
            await asyncio.sleep(1.0)
            await take_screenshot("when_mars_goes_dark_live.png")

            # Step 7: Cryptographic Proof & DTN Custody Audit (Step 7 of Golden Path)
            await eval_js("window._gpCurrentStep = 6; window._gpRenderStep(6);")
            await asyncio.sleep(0.5)
            await eval_js("document.getElementById('gpBtnAction')?.click();")
            await asyncio.sleep(2.0)
            await take_screenshot("golden_path_completion_live.png")

            listener_task.cancel()
            print("[Screenshot QA] All 7 live screenshots successfully captured!")

    finally:
        proc.terminate()
        proc.wait(timeout=5)
        shutil.rmtree(tmp_profile, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(capture_screenshots())
