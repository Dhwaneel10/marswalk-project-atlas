#!/usr/bin/env python3
"""
scripts/capture_mission16c_evidence.py
Captures fresh visual evidence for Mission 16C verification across desktop & mobile.
"""

import asyncio
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import websockets

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "mission_16c"))
os.makedirs(OUTPUT_DIR, exist_ok=True)
CHROME_BIN = "/usr/bin/google-chrome"
TARGET_URL = "http://127.0.0.1:3000"


DEBUG_PORT = 9550

async def capture_screenshots():
    # 1. Desktop Session (1920x1080)
    print("Launching Desktop Chrome Session (1920x1080)...")
    tmp_d = tempfile.mkdtemp(prefix="m16c_desk_")
    proc_d = subprocess.Popen([
        CHROME_BIN,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={tmp_d}",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1920,1080",
        "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
                    r = json.loads(await ws.recv())
                    if r.get("id") == msg_id:
                        return r

            async def eval_js(expr):
                r = await send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
                return r.get("result", {}).get("result", {}).get("value")

            async def snap(name):
                r = await send("Page.captureScreenshot", {"format": "png"})
                data = r.get("result", {}).get("data")
                path = os.path.join(OUTPUT_DIR, name)
                with open(path, "wb") as f:
                    f.write(base64.b64decode(data))
                size_kb = round(os.path.getsize(path) / 1024, 1)
                print(f"Captured {name} ({size_kb} KB)")
                return path

            await send("Page.enable")
            await send("Runtime.enable")

            # 1. Homepage Top
            print("1. Loading Homepage...")
            await send("Page.navigate", {"url": TARGET_URL})
            await asyncio.sleep(4.0)
            await snap("01_homepage_top.png")

            # 2. Homepage Specs Section
            print("2. Capturing Specifications Grid...")
            await eval_js("document.querySelector('.landing-specs-grid')?.scrollIntoView({behavior:'instant'});")
            await asyncio.sleep(1.0)
            await snap("02_homepage_specs.png")

            # 3. Homepage How It Works Section
            print("3. Capturing How It Works Section...")
            await eval_js("document.querySelector('.landing-how-it-works')?.scrollIntoView({behavior:'instant'});")
            await asyncio.sleep(1.0)
            await snap("03_homepage_how_it_works.png")

            # 4. Homepage Footer Section
            print("4. Capturing Provenance Footer...")
            await eval_js("document.querySelector('.landing-footer')?.scrollIntoView({behavior:'instant'});")
            await asyncio.sleep(1.0)
            await snap("04_homepage_footer.png")

            # 5. Launch EVA & Jezero Environment
            print("5. Launching Astronaut EVA Mode...")
            await eval_js("window.scrollTo(0,0); document.getElementById('btnLandingEnterEVA')?.click();")
            await asyncio.sleep(2.5)
            await snap("05_jezero_environment.png")

            # 6. Select targets & Plan routes
            print("6. Selecting targets and planning 3 routes...")
            await eval_js("""
            (() => {
                const chks = document.querySelectorAll('.eva-target-chk');
                chks.forEach((c, idx) => {
                    c.checked = (idx < 4);
                    c.dispatchEvent(new Event('change', {bubbles: true}));
                });
                document.getElementById('btnPlanEVARoutes')?.click();
            })()
            """)
            await asyncio.sleep(4.5)
            await snap("06_eva_planning.png")

            # 7. Route Comparison
            print("7. Comparing route strategies...")
            await eval_js("document.querySelector('.eva-route-card[data-route-key=\"science_first\"]')?.click();")
            await asyncio.sleep(1.5)
            await snap("07_route_comparison.png")

            # 8. Resource Dashboard (Visor HUD)
            print("8. Opening Visor HUD resource dashboard...")
            await eval_js("document.getElementById('btnToggleEvaVisor')?.click();")
            await asyncio.sleep(1.5)
            await snap("08_resource_dashboard.png")

            # 9. Contingency Workflow (Dust Event)
            print("9. Triggering dust event contingency...")
            await eval_js("document.querySelector('.btn-eva-contingency-trigger[data-contingency=\"dust_event\"]')?.click();")
            await asyncio.sleep(2.5)
            await snap("09_contingency_workflow.png")

    finally:
        proc_d.terminate()
        try:
            proc_d.wait(timeout=3)
        except Exception:
            proc_d.kill()
        shutil.rmtree(tmp_d, ignore_errors=True)

    # 2. Mobile Session (390x844)
    print("\nLaunching Mobile Chrome Session (390x844)...")
    tmp_m = tempfile.mkdtemp(prefix="m16c_mob_")
    proc_m = subprocess.Popen([
        CHROME_BIN,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={tmp_m}",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=390,844",
        "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(2.0)

    try:
        req_m = urllib.request.Request(f"http://127.0.0.1:{DEBUG_PORT}/json")
        with urllib.request.urlopen(req_m, timeout=5) as resp_m:
            targets_m = json.loads(resp_m.read().decode("utf-8"))
        ws_url_m = targets_m[0]["webSocketDebuggerUrl"]
        async with websockets.connect(ws_url_m, max_size=50 * 1024 * 1024) as ws:
            msg_id = 0

            async def send_m(method, params=None):
                nonlocal msg_id
                msg_id += 1
                payload = {"id": msg_id, "method": method}
                if params:
                    payload["params"] = params
                await ws.send(json.dumps(payload))
                while True:
                    r = json.loads(await ws.recv())
                    if r.get("id") == msg_id:
                        return r

            async def eval_m(expr):
                r = await send_m("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
                return r.get("result", {}).get("result", {}).get("value")

            async def snap_m(name):
                r = await send_m("Page.captureScreenshot", {"format": "png"})
                data = r.get("result", {}).get("data")
                path = os.path.join(OUTPUT_DIR, name)
                with open(path, "wb") as f:
                    f.write(base64.b64decode(data))
                size_kb = round(os.path.getsize(path) / 1024, 1)
                print(f"Captured {name} ({size_kb} KB)")
                return path

            await send_m("Page.enable")
            await send_m("Runtime.enable")

            # 10. Mobile Homepage
            print("10. Capturing Mobile Homepage...")
            await send_m("Page.navigate", {"url": TARGET_URL})
            await asyncio.sleep(4.0)
            await snap_m("10_mobile_homepage.png")

            # 11. Mobile EVA Interface
            print("11. Capturing Mobile EVA Interface...")
            await eval_m("document.getElementById('btnLandingEnterEVA')?.click();")
            await asyncio.sleep(2.5)
            await snap_m("11_mobile_eva_interface.png")

    finally:
        proc_m.terminate()
        try:
            proc_m.wait(timeout=3)
        except Exception:
            proc_m.kill()
        shutil.rmtree(tmp_m, ignore_errors=True)

    print("\nAll Mission 16C evidence captured successfully in outputs/mission_16c/.")


if __name__ == "__main__":
    asyncio.run(capture_screenshots())
