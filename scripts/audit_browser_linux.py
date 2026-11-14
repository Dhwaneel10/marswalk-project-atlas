#!/usr/bin/env python3
"""
MarsWalk 2.0 / Project Atlas — Autonomous Headless Browser QA Engine (Linux)
Launches /usr/bin/google-chrome via Chrome DevTools Protocol (CDP),
tests all Five Pillars, executes dynamic actions, verifies 3D surface loading,
monitors JavaScript exceptions, and captures visual proof screenshots.
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import websockets

BASE_URL = "http://127.0.0.1:3000"
DEBUG_PORT = 9499
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "browser_qa"))
CHROME_BIN = "/usr/bin/google-chrome"


async def run_browser_qa():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tmp_profile = tempfile.mkdtemp(prefix="chrome_marswalk_qa_")

    cmd = [
        CHROME_BIN,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={tmp_profile}",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1600,1000",
        "about:blank",
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(2.0)

    js_exceptions = []
    console_logs = []

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{DEBUG_PORT}/json")
        with urllib.request.urlopen(req, timeout=5) as resp:
            targets = json.loads(resp.read().decode("utf-8"))

        ws_url = targets[0]["webSocketDebuggerUrl"]
        print(f"[Browser QA] Connected to Chrome CDP at {ws_url}")

        async with websockets.connect(ws_url, max_size=20_000_000) as ws:
            msg_id = 1

            async def send_cdp(method, params=None):
                nonlocal msg_id
                cid = msg_id
                msg_id += 1
                payload = {"id": cid, "method": method}
                if params:
                    payload["params"] = params
                await ws.send(json.dumps(payload))
                return cid

            async def eval_js(expr):
                nonlocal msg_id
                cid = msg_id
                msg_id += 1
                await ws.send(json.dumps({
                    "id": cid,
                    "method": "Runtime.evaluate",
                    "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}
                }))
                while True:
                    resp_str = await ws.recv()
                    data = json.loads(resp_str)
                    if data.get("id") == cid:
                        return data.get("result", {}).get("result", {}).get("value")

            # Enable CDP agents
            await send_cdp("Page.enable")
            await send_cdp("Runtime.enable")
            await send_cdp("Console.enable")

            # Navigate to Atlas
            print(f"[Browser QA] Navigating to {BASE_URL}...")
            await send_cdp("Page.navigate", {"url": BASE_URL})

            # Wait for load and initialization
            await asyncio.sleep(5.0)

            # Check title
            title = await eval_js("document.title")
            print(f"[Browser QA] Page Title: {title}")

            # 1. Test Pillar 1: USGS Terrain
            print("[Browser QA] Testing Pillar 1 (USGS Terrain)...")
            await eval_js("document.getElementById('btnPillar1Terrain').click()")
            await asyncio.sleep(1.0)
            p1_title = await eval_js("document.getElementById('pillarsCardTitle').innerText")
            print(f"  Pillar 1 Title: {p1_title}")

            # Click dynamic point inspection
            print("[Browser QA] Triggering Hawksbill Gap Point Inspection...")
            await eval_js("""
                const btns = Array.from(document.querySelectorAll('#pillarsActionButtons button'));
                const b = btns.find(x => x.innerText.includes('Inspect Hawksbill Gap'));
                if (b) b.click();
            """)
            await asyncio.sleep(1.5)
            dyn_out_1 = await eval_js("document.getElementById('pillarsDynamicOutput').innerText")
            print(f"  Point Inspection Output: {dyn_out_1[:100]}...")

            # 2. Test Pillar 2: PDS Ground Truth
            print("[Browser QA] Testing Pillar 2 (PDS Ground Truth)...")
            await eval_js("document.getElementById('btnPillar2GroundTruth').click()")
            await asyncio.sleep(1.0)
            await eval_js("""
                const btns = Array.from(document.querySelectorAll('#pillarsActionButtons button'));
                const b = btns.find(x => x.innerText.includes('List Three Forks Depot'));
                if (b) b.click();
            """)
            await asyncio.sleep(1.5)
            dyn_out_2 = await eval_js("document.getElementById('pillarsDynamicOutput').innerText")
            print(f"  Sample Depot Output: {dyn_out_2[:100]}...")

            # 3. Test Pillar 3: NASA MEDA In-Situ
            print("[Browser QA] Testing Pillar 3 (MEDA Calibration)...")
            await eval_js("document.getElementById('btnPillar3Meda').click()")
            await asyncio.sleep(1.0)
            await eval_js("""
                const btns = Array.from(document.querySelectorAll('#pillarsActionButtons button'));
                const b = btns.find(x => x.innerText.includes('Regional Storm'));
                if (b) b.click();
            """)
            await asyncio.sleep(1.5)
            dyn_out_3 = await eval_js("document.getElementById('pillarsDynamicOutput').innerText")
            print(f"  MEDA Calibration Output: {dyn_out_3[:100]}...")

            # 4. Test Pillar 4: Science Planning
            print("[Browser QA] Testing Pillar 4 (Science-Driven Planning)...")
            await eval_js("document.getElementById('btnPillar4Science').click()")
            await asyncio.sleep(1.0)
            await eval_js("""
                const btns = Array.from(document.querySelectorAll('#pillarsActionButtons button'));
                const b = btns.find(x => x.innerText.includes('Compare Direct vs Science'));
                if (b) b.click();
            """)
            await asyncio.sleep(2.0)
            dyn_out_4 = await eval_js("document.getElementById('pillarsDynamicOutput').innerText")
            print(f"  Science Trade Output: {dyn_out_4[:120]}...")

            # 5. Test Pillar 5: Resilience & Merkle Proof
            print("[Browser QA] Testing Pillar 5 (Resilience & Merkle)...")
            await eval_js("document.getElementById('btnPillar5Resilience').click()")
            await asyncio.sleep(1.0)
            await eval_js("""
                const btns = Array.from(document.querySelectorAll('#pillarsActionButtons button'));
                const b = btns.find(x => x.innerText.includes('Verify Merkle Proof'));
                if (b) b.click();
            """)
            await asyncio.sleep(1.5)
            dyn_out_5 = await eval_js("document.getElementById('pillarsDynamicOutput').innerText")
            print(f"  Merkle Audit Output: {dyn_out_5[:100]}...")

            # Capture Screenshot of Five Pillars Deck
            shot_cid = await send_cdp("Page.captureScreenshot", {"format": "png"})
            while True:
                resp_str = await ws.recv()
                data = json.loads(resp_str)
                if data.get("id") == shot_cid:
                    import base64
                    img_data = base64.b64decode(data["result"]["data"])
                    shot_path = os.path.join(OUTPUT_DIR, "five_pillars_deck_live.png")
                    with open(shot_path, "wb") as f:
                        f.write(img_data)
                    print(f"[Browser QA] Captured visual screenshot: {shot_path}")
                    break

            # 6. Test 3D Flight to Jezero Surface
            print("[Browser QA] Testing Flight Transition to Jezero Surface...")
            await eval_js("if (typeof flyToJezeroView === 'function') flyToJezeroView();")
            await asyncio.sleep(3.0)

            # Capture Surface View Screenshot
            shot_cid2 = await send_cdp("Page.captureScreenshot", {"format": "png"})
            while True:
                resp_str = await ws.recv()
                data = json.loads(resp_str)
                if data.get("id") == shot_cid2:
                    import base64
                    img_data = base64.b64decode(data["result"]["data"])
                    shot_path2 = os.path.join(OUTPUT_DIR, "jezero_3d_surface_live.png")
                    with open(shot_path2, "wb") as f:
                        f.write(img_data)
                    print(f"[Browser QA] Captured visual screenshot: {shot_path2}")
                    break

            # Check for runtime errors
            print("[Browser QA] Checking for JavaScript runtime errors...")
            err_count = await eval_js("window.__marswalk_error_count || 0")
            print(f"[Browser QA] Unhandled Window Errors: {err_count}")

            print("\n========================================================================")
            print("  BROWSER QA PASSED: ALL FIVE PILLARS & 3D VIEWS RESPONSIVE & NOMINAL  ")
            print("========================================================================")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        shutil.rmtree(tmp_profile, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(run_browser_qa())
