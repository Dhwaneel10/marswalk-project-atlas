#!/usr/bin/env python3
"""
MarsWalk 2.0 / Project Atlas — Evaluator Golden Path Browser QA Verification
Automates end-to-end browser execution of the 7-step Evaluator Golden Path Tour
using Chrome DevTools Protocol (CDP) on Ubuntu 22.04 LTS.
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

BASE_URL = "http://127.0.0.1:3000"
DEBUG_PORT = 9498
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "browser_qa"))
CHROME_BIN = "/usr/bin/google-chrome"


async def run_golden_path_browser_audit():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tmp_profile = tempfile.mkdtemp(prefix="chrome_gp_audit_")

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
        print(f"[Golden Path QA] Connected to Chrome CDP at {ws_url}")

        async with websockets.connect(ws_url, max_size=25_000_000) as ws:
            msg_id = 1

            pending_requests = {}

            async def send_cdp(method, params=None):
                nonlocal msg_id
                cid = msg_id
                msg_id += 1
                fut = asyncio.get_event_loop().create_future()
                pending_requests[cid] = fut
                payload = {"id": cid, "method": method}
                if params:
                    payload["params"] = params
                await ws.send(json.dumps(payload))
                return await fut

            async def eval_js(expr):
                resp = await send_cdp("Runtime.evaluate", {
                    "expression": expr,
                    "returnByValue": True,
                    "awaitPromise": True
                })
                return resp.get("result", {}).get("value")

            async def cdp_dispatcher():
                try:
                    while True:
                        raw = await ws.recv()
                        ev = json.loads(raw)
                        if "id" in ev and ev["id"] in pending_requests:
                            fut = pending_requests.pop(ev["id"])
                            if "error" in ev:
                                fut.set_exception(Exception(ev["error"]))
                            else:
                                fut.set_result(ev.get("result", {}))
                        elif ev.get("method") == "Runtime.exceptionThrown":
                            details = ev.get("params", {}).get("exceptionDetails", {})
                            print(f"  [JS EXCEPTION] {details.get('text')}: {details.get('exception', {}).get('description')}")
                        elif ev.get("method") == "Console.messageAdded":
                            msg = ev.get("params", {}).get("message", {})
                            if msg.get("level") in ("error", "warning"):
                                print(f"  [CONSOLE {msg.get('level').upper()}] {msg.get('text')}")
                except Exception:
                    pass

            asyncio.create_task(cdp_dispatcher())

            await send_cdp("Page.enable")
            await send_cdp("Runtime.enable")
            await send_cdp("Console.enable")

            print(f"[Golden Path QA] Navigating to {BASE_URL}...")
            await send_cdp("Page.navigate", {"url": BASE_URL})
            await asyncio.sleep(5.0)

            # Check if initEvaluatorGoldenPathTour exists
            t = await eval_js("typeof initEvaluatorGoldenPathTour")
            print(f"  typeof initEvaluatorGoldenPathTour: {t}")
            t_deck = await eval_js("typeof initNasaPillarsDeck")
            print(f"  typeof initNasaPillarsDeck: {t_deck}")

            # Step 0: Open Golden Path Tour HUD
            print("[Golden Path QA] Clicking #btnGoldenPathTour...")
            is_visible_init = await eval_js("document.getElementById('evaluatorGoldenPathCard').style.display")
            print(f"  Initial display: {is_visible_init}")
            await eval_js("document.getElementById('btnGoldenPathTour').click()")
            await asyncio.sleep(0.5)
            is_visible_after = await eval_js("document.getElementById('evaluatorGoldenPathCard').style.display")
            print(f"  After click display: {is_visible_after}")
            assert is_visible_after == "block", "evaluatorGoldenPathCard failed to open"

            results = []

            for step_num in range(1, 8):
                print(f"\n--- [Golden Path QA] Testing Step {step_num} of 7 ---")
                # Activate step via pill click
                await eval_js(f"document.querySelector('.gp-step-btn[data-step=\"{step_num}\"]').click()")
                await asyncio.sleep(0.3)

                header = await eval_js("document.getElementById('gpStepHeader').innerText")
                print(f"  Header: {header}")

                # Execute Step Action
                print("  Executing step action...")
                await eval_js("document.getElementById('btnGpExecuteStep').click()")
                await asyncio.sleep(1.8)

                out_text = await eval_js("document.getElementById('gpOutputBox').innerText")
                print(f"  Output preview: {out_text[:120].strip()}...")

                # Step-specific assertions
                if step_num == 1:
                    assert "USGS Jezero CTX 20m DEM" in out_text
                    assert "8/8 INTEGRITY VERIFIED" in out_text
                elif step_num == 2:
                    assert "Hawksbill Gap" in out_text
                    assert "9.4°" in out_text or "9.4" in out_text
                    assert "Crater Floor" in out_text
                elif step_num == 3:
                    assert "THREE FORKS SAMPLE DEPOT" in out_text
                    assert "33.2 km" in out_text
                    assert "Sealed Titanium Tubes" in out_text
                elif step_num == 4:
                    assert "MEDA ATMOSPHERIC COUPLING" in out_text
                    assert "Solar Subsystem Output" in out_text
                    assert "RF Dust Attenuation" in out_text
                elif step_num == 5:
                    assert "MULTI-OBJECTIVE SCIENCE TRADE-OFF" in out_text
                    assert "Route A (Direct)" in out_text
                    assert "Route B (Science-Priority)" in out_text
                elif step_num == 6:
                    assert "FLAGSHIP AUTONOMOUS RESILIENCE" in out_text
                    assert "When Mars Goes Dark" in out_text or "Safe Hold" in out_text
                elif step_num == 7:
                    assert "CRYPTOGRAPHIC AUDIT CERTIFICATE" in out_text
                    assert "0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8" in out_text
                    assert "ALL 7 TEST CRITERIA PASSED" in out_text

                results.append({"step": step_num, "header": header, "status": "VERIFIED_PASS"})

            # Capture live visual proof screenshot
            print("\n[Golden Path QA] Capturing high-resolution visual proof screenshot...")
            shot_res = await send_cdp("Page.captureScreenshot", {"format": "png", "quality": 95})
            img_data = base64.b64decode(shot_res.get("data", ""))
            shot_path = os.path.join(OUTPUT_DIR, "evaluator_golden_path_live.png")
            with open(shot_path, "wb") as f:
                f.write(img_data)
            print(f"[Golden Path QA] Screenshot saved to: {shot_path} ({len(img_data)} bytes)")

            print("\n=======================================================")
            print("GOLDEN PATH AUDIT SUCCESS: 7/7 STEPS VERIFIED IN BROWSER")
            print("=======================================================")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        shutil.rmtree(tmp_profile, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(run_golden_path_browser_audit())
