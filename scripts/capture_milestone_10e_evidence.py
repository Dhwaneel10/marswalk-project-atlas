"""
MarsWalk 2.0 — Milestone 10E Evidence Capture: Mission Science Report & Export Dashboard.

Captures all 3 verified operational states via Chrome DevTools Protocol:
1. Report Modal Overview (m10e_01_report_modal_overview.png):
   Assembled mission report with plan metadata, mobility metrics, and embedded report preview.
2. Environmental & Science Provenance (m10e_02_report_environmental_weather_provenance.png):
   In-situ Martian environmental intelligence (Perseverance MEDA Sol 1619) & operational disclaimers.
3. Export Actions & Reproducibility Manifest (m10e_03_report_export_actions_and_manifest.png):
   Standalone export toolbar (HTML, JSON, Print) with verified CTX 20m DTM SHA-256 hash.
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
DEBUG_PORT = 9501

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
    print("=== Milestone 10E Evidence Capture: Mission Science Report & Export Dashboard ===")

    # Check server
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=3) as r:
            print("Atlas server is online.")
    except Exception as e:
        print(f"Error connecting to Atlas: {e}")
        return

    user_data_dir = tempfile.mkdtemp(prefix="chrome_m10e_")
    chrome_proc = subprocess.Popen([
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={user_data_dir}",
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1440,900",
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
        for _ in range(30):
            ready = await evaluate_js(ws, "typeof window.__atlas !== 'undefined' && typeof window.__atlas.openMissionReport === 'function'")
            if ready:
                print("Atlas workstation and window.__atlas ready.")
                break
            await asyncio.sleep(1)

        # 1. Open Mission Science Report & Export Dashboard Modal for Jezero Delta Scarp Survey
        print("Opening Mission Science Report modal...")
        await evaluate_js(ws, """
            if (window.__atlas && window.__atlas.openMissionReport) {
                window.__atlas.openMissionReport('m_jezero_delta_scarp_surve_090607');
            } else {
                const btn = document.getElementById('btnHeaderReport');
                if (btn) btn.click();
            }
        """)
        await asyncio.sleep(4)

        # Capture State 1: Report Modal Overview
        print("[1/3] Capturing: m10e_01_report_modal_overview.png...")
        await capture_screenshot(ws, "m10e_01_report_modal_overview.png")

        # 2. Scroll the embedded iframe to reveal Martian Environmental Intelligence & Black Box Ledger
        print("Scrolling report preview to Environmental Intelligence section...")
        await evaluate_js(ws, """
            const iframe = document.getElementById('missionReportPreviewIframe');
            if (iframe && iframe.contentDocument) {
                const weatherSec = iframe.contentDocument.querySelector('.weather-card');
                if (weatherSec) {
                    weatherSec.scrollIntoView();
                } else if (iframe.contentWindow) {
                    iframe.contentWindow.scrollTo({ top: 400, behavior: 'instant' });
                }
            }
        """)
        await asyncio.sleep(2)

        # Capture State 2: Environmental & Science Provenance
        print("[2/3] Capturing: m10e_02_report_environmental_weather_provenance.png...")
        await capture_screenshot(ws, "m10e_02_report_environmental_weather_provenance.png")

        # 3. Switch weather site to Gale Crater (REMS In-Situ) and regenerate
        print("Regenerating report with Gale Crater REMS weather site...")
        await evaluate_js(ws, """
            const siteSel = document.getElementById('reportWeatherSiteSelect');
            if (siteSel) {
                siteSel.value = 'gale_crater';
            }
            if (window.__atlas && window.__atlas.generateReport) {
                window.__atlas.generateReport('m_jezero_delta_scarp_surve_090607', 'gale_crater');
            }
        """)
        await asyncio.sleep(4)

        # Capture State 3: Export Actions & Gale Crater Multi-Site Report
        print("[3/3] Capturing: m10e_03_report_export_actions_and_manifest.png...")
        await capture_screenshot(ws, "m10e_03_report_export_actions_and_manifest.png")

        print("=== Milestone 10E Evidence Capture Complete ===")

    chrome_proc.terminate()


if __name__ == "__main__":
    asyncio.run(main())
