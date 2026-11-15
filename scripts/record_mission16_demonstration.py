#!/usr/bin/env python3
"""
scripts/record_mission16_demonstration.py
Complete live demonstration recorder for Mission 16:
- Runs live Chrome instance under virtual X11 display (Xvfb)
- Captures real-time MP4 video with ffmpeg: outputs/mission_16/marswalk_guided_demonstration.mp4
- Automates Demostrations A through F with realistic presentation pacing
"""

import asyncio
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
import websockets

TARGET_PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3000
BASE_URL = f"http://127.0.0.1:{TARGET_PORT}"
DISPLAY_NUM = ":99"
DEBUG_PORT = 9530
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "mission_16"))
VIDEO_PATH = os.path.join(OUTPUT_DIR, "marswalk_guided_demonstration.mp4")
CHROME_BIN = "/usr/bin/google-chrome"


async def record_demonstration():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if os.path.exists(VIDEO_PATH):
        try:
            os.remove(VIDEO_PATH)
        except Exception:
            pass

    print(f"Starting Xvfb on display {DISPLAY_NUM} (1920x1080x24)...")
    xvfb_proc = subprocess.Popen(
        ["Xvfb", DISPLAY_NUM, "-screen", "0", "1920x1080x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)

    print(f"Starting ffmpeg screen recorder -> {VIDEO_PATH}...")
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f", "x11grab",
        "-video_size", "1920x1080",
        "-i", f"{DISPLAY_NUM}.0",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-r", "24",
        VIDEO_PATH,
    ]
    ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)

    tmp_profile = tempfile.mkdtemp(prefix="chrome_m16_rec_")
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY_NUM

    chrome_cmd = [
        CHROME_BIN,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={tmp_profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-position=0,0",
        "--window-size=1920,1080",
        "--start-maximized",
        "about:blank",
    ]

    print("Launching Google Chrome on virtual display...")
    chrome_proc = subprocess.Popen(chrome_cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(2.5)

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

            await send("Page.enable")
            await send("Runtime.enable")
            await send("DOM.enable")

            # DEMO A: Homepage & Product Overview
            print("[DEMO A] Navigating to MarsWalk Landing Stage...")
            await send("Page.navigate", {"url": f"{BASE_URL}/"})
            await asyncio.sleep(4.0)

            # Showcase Curated Destination Hover / Selection
            print("[DEMO A] Exploring Curated Destinations...")
            await eval_js("document.querySelectorAll('.dest-item')[1]?.click();")
            await asyncio.sleep(1.5)
            await eval_js("document.querySelectorAll('.dest-item')[0]?.click();")
            await asyncio.sleep(1.5)

            # Scroll down to How It Works & Footer
            print("[DEMO A] Expanding Architecture & Provenance...")
            await eval_js("document.getElementById('btnLandingHowItWorks')?.click();")
            await asyncio.sleep(2.0)
            await eval_js("document.getElementById('landingFooter')?.scrollIntoView({behavior: 'smooth'});")
            await asyncio.sleep(3.0)

            # Scroll back to top
            print("[DEMO A] Scrolling back to Top...")
            await eval_js("document.getElementById('marsLandingPage')?.scrollTo({top: 0, behavior: 'smooth'});")
            await asyncio.sleep(2.5)

            # DEMO B: Enter Astronaut EVA Mode & Interface Tour
            print("[DEMO B] Entering Astronaut EVA Mode...")
            await eval_js("document.getElementById('btnLandingEnterEVA')?.click();")
            await asyncio.sleep(3.0)

            # DEMO C: Terrain Intelligence & Science Target Selection
            print("[DEMO C] Selecting Multi-Stop Science Outcrop Targets...")
            await eval_js("""
            (() => {
                const chks = document.querySelectorAll('.eva-target-chk');
                chks.forEach((c, idx) => { c.checked = (idx < 4); });
            })()
            """)
            await asyncio.sleep(2.0)

            # Plan EVA Routes
            print("[DEMO B/D] Computing 3 Human EVA Routes across Jezero Topography...")
            await eval_js("document.getElementById('btnPlanEVARoutes')?.click();")
            await asyncio.sleep(4.0)

            # Compare Route Strategies (Conservative, Science-First, Time-Efficient)
            print("[DEMO B] Demonstrating Pareto Route Comparison...")
            await eval_js("document.querySelector('.eva-route-card[data-route-key=\"science_first\"]')?.click();")
            await asyncio.sleep(2.5)
            await eval_js("document.querySelector('.eva-route-card[data-route-key=\"time_efficient\"]')?.click();")
            await asyncio.sleep(2.5)
            await eval_js("document.querySelector('.eva-route-card[data-route-key=\"conservative\"]')?.click();")
            await asyncio.sleep(2.0)

            # DEMO D: Resource and Mission Constraints (Visor HUD & PLSS Telemetry)
            print("[DEMO D] Opening Dedicated Astronaut Visor HUD with 20% PLSS Reserve Redline...")
            await eval_js("document.getElementById('btnToggleEvaVisor')?.click();")
            await asyncio.sleep(3.5)

            # DEMO E: Contingency and Mission Resilience
            print("[DEMO E] Triggering Simulated Atmospheric Dust Event Contingency...")
            await eval_js("document.querySelector('.btn-eva-contingency-trigger[data-contingency=\"dust_event\"]')?.click();")
            await asyncio.sleep(3.5)

            print("[DEMO E] Resetting Contingency to Nominal Traverse State...")
            await eval_js("document.getElementById('btnEvaContingencyReset')?.click();")
            await asyncio.sleep(2.0)

            # DEMO F: Robotic Rover Mode & Handover
            print("[DEMO F] Switching to Robotic Rover Mode...")
            await eval_js("document.getElementById('btnModeRoboticRover')?.click();")
            await asyncio.sleep(3.0)

            # Evaluator Golden Path Tour
            print("[DEMO F] Launching 7-Step Evaluator Golden Path Tour...")
            await eval_js("document.getElementById('btnGoldenPathTour')?.click();")
            await asyncio.sleep(3.0)
            await eval_js("document.getElementById('btnGpNext')?.click();")
            await asyncio.sleep(2.5)
            await eval_js("document.getElementById('btnGpNext')?.click();")
            await asyncio.sleep(2.5)

            # Return to Overview
            print("[DEMO A] Returning to Overview Stage...")
            await eval_js("document.getElementById('btnNavOverview')?.click();")
            await asyncio.sleep(3.0)

            print("Demonstration sequence completed successfully.")

    finally:
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=3)
        except Exception:
            chrome_proc.kill()
        shutil.rmtree(tmp_profile, ignore_errors=True)

        print("Stopping ffmpeg screen recorder cleanly...")
        ffmpeg_proc.send_signal(signal.SIGINT)
        try:
            ffmpeg_proc.wait(timeout=5)
        except Exception:
            ffmpeg_proc.terminate()

        print("Stopping Xvfb display...")
        xvfb_proc.terminate()
        try:
            xvfb_proc.wait(timeout=3)
        except Exception:
            xvfb_proc.kill()

    if os.path.exists(VIDEO_PATH):
        v_size_mb = round(os.path.getsize(VIDEO_PATH) / (1024 * 1024), 2)
        print(f"\n=======================================================")
        print(f"MARSWALK GUIDED DEMONSTRATION VIDEO CREATED")
        print(f"Path: {VIDEO_PATH}")
        print(f"Size: {v_size_mb} MB")
        print(f"=======================================================\n")
    else:
        print(f"\nWARNING: Demonstration video was not created at {VIDEO_PATH}\n")


if __name__ == "__main__":
    asyncio.run(record_demonstration())
