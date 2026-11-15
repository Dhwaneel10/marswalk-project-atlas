#!/usr/bin/env python3
"""
scripts/capture_mission15_baseline.py
Capture initial baseline screenshots for Mission 15 Phase 0.
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
DEBUG_PORT = 9501
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "mission_15", "baseline"))
CHROME_BIN = "/usr/bin/google-chrome"


async def capture_baseline():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tmp_profile = tempfile.mkdtemp(prefix="chrome_m15_base_")

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

        async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
            msg_id = 0

            async def send(method, params=None):
                nonlocal msg_id
                msg_id += 1
                payload = {"id": msg_id, "method": method}
                if params:
                    payload["params"] = params
                await ws.send(json.dumps(payload))
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    if data.get("id") == msg_id:
                        return data

            async def eval_js(expression):
                res = await send("Runtime.evaluate", {
                    "expression": expression,
                    "returnByValue": True,
                    "awaitPromise": True,
                })
                return res.get("result", {}).get("result", {}).get("value")

            async def snap(filename):
                res = await send("Page.captureScreenshot", {"format": "png"})
                b64 = res.get("result", {}).get("data")
                if b64:
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(b64))
                    size_kb = round(os.path.getsize(filepath) / 1024, 1)
                    print(f"Captured {filename} ({size_kb} KB)")
                    return filepath

            await send("Page.enable")
            await send("Runtime.enable")
            await send("DOM.enable")

            # 1. Capture landing page
            print("Navigating to landing page...")
            await send("Page.navigate", {"url": f"{BASE_URL}/"})
            await asyncio.sleep(4.0)
            await snap("m15_00_baseline_landing.png")

            # 2. Enter EVA mode and plan routes
            print("Entering Astronaut EVA mode...")
            await eval_js("document.getElementById('btnLandingEnterEVA')?.click();")
            await asyncio.sleep(2.5)
            await eval_js("document.getElementById('btnPlanEVARoutes')?.click();")
            await asyncio.sleep(3.5)
            await snap("m15_00_baseline_mission.png")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(tmp_profile, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(capture_baseline())
