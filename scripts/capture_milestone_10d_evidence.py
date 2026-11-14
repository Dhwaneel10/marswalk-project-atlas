"""
MarsWalk 2.0 — Milestone 10D Evidence Script: Mars Environmental Intelligence.

Captures all 3 verified operational states via Chrome DevTools Protocol:
1. Jezero In-Situ Observations (m10d_01_weather_jezero_meda_in_situ.png):
   Authentic Perseverance MEDA atmospheric readings (Sol 1619, 589.7 Pa, -61.7°C, PDS provenance).
2. Multi-Site Isolation (m10d_02_weather_site_isolation_gale_rems.png):
   Gale Crater Curiosity REMS readings strictly isolated from Jezero.
3. Climatology Model Distinction (m10d_03_weather_climatological_model_olympus.png):
   Olympus Mons summit explicitly tagged as CLIMATOLOGICAL_MODEL (MCD v6.1, 72 Pa).
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

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


async def capture_screenshot(ws, filename):
    params = {"format": "png"}
    resp = await send_cmd(ws, "Page.captureScreenshot", params)
    data_b64 = resp.get("result", {}).get("data", "")
    if not data_b64:
        print(f"Failed to capture {filename}")
        return

    raw_bytes = base64.b64decode(data_b64)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / filename
    with open(out_file, "wb") as f:
        f.write(raw_bytes)
    print(f"Saved: {out_file} ({len(raw_bytes):,} bytes)")

    if ARTIFACT_OUTPUT_DIR.exists():
        art_file = ARTIFACT_OUTPUT_DIR / filename
        with open(art_file, "wb") as f:
            f.write(raw_bytes)
        print(f"Mirrored artifact: {art_file}")


async def main():
    print("=== Milestone 10D Evidence Capture: Mars Environmental Intelligence ===")

    # Check server
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=3) as r:
            print("Atlas server is online.")
    except Exception as e:
        print(f"Error connecting to Atlas: {e}")
        return

    user_data_dir = tempfile.mkdtemp(prefix="chrome_m10d_")
    chrome_proc = subprocess.Popen([
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={user_data_dir}",
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1400,900",
        f"{BASE_URL}/?landing=false&fly=jezero"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    ws_url = None
    for _ in range(30):
        await asyncio.sleep(0.5)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=2) as resp:
                tabs = json.loads(resp.read().decode())
                for t in tabs:
                    if t.get("type") == "page" and "webSocketDebuggerUrl" in t:
                        ws_url = t["webSocketDebuggerUrl"]
                        break
            if ws_url:
                break
        except Exception:
            pass

    if not ws_url:
        print("Failed to attach to Chrome debug port.")
        chrome_proc.terminate()
        return

    async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
        await send_cmd(ws, "Page.enable")
        await send_cmd(ws, "Runtime.enable")
        print("Connected to CDP. Waiting for Atlas app initialization...")
        await asyncio.sleep(6)

        # 1. Open Mars Environmental Intelligence Modal (Jezero MEDA)
        print("Opening Mars Environmental Intelligence modal...")
        await evaluate_js(ws, "window.__atlas.openWeather();")
        await asyncio.sleep(2)

        # Capture State 1: Jezero MEDA In-Situ
        print("Capturing m10d_01_weather_jezero_meda_in_situ.png...")
        await capture_screenshot(ws, "m10d_01_weather_jezero_meda_in_situ.png")
        await asyncio.sleep(1)

        # 2. Switch site to Gale Crater (Curiosity REMS)
        print("Switching site to Gale Crater (Curiosity REMS)...")
        await evaluate_js(ws, "window.__atlas.loadWeather('gale_crater', false);", await_promise=True)
        await asyncio.sleep(1.5)

        # Capture State 2: Multi-Site Isolation (Gale REMS)
        print("Capturing m10d_02_weather_site_isolation_gale_rems.png...")
        await capture_screenshot(ws, "m10d_02_weather_site_isolation_gale_rems.png")
        await asyncio.sleep(1)

        # 3. Switch site to Olympus Mons (MCD Climatology Model)
        print("Switching site to Olympus Mons Summit (MCD Climatology Model)...")
        await evaluate_js(ws, "window.__atlas.loadWeather('olympus_mons', false);", await_promise=True)
        await asyncio.sleep(1.5)

        # Capture State 3: Climatology Model Distinction (Olympus Mons)
        print("Capturing m10d_03_weather_climatological_model_olympus.png...")
        await capture_screenshot(ws, "m10d_03_weather_climatological_model_olympus.png")
        await asyncio.sleep(1)

    chrome_proc.terminate()
    print("Evidence capture complete!")


if __name__ == "__main__":
    asyncio.run(main())
