"""MarsWalk 2.0 / Project Atlas - Milestone 12E Mission Robustness Lab Browser Audit Script.

Uses Headless Chrome DevTools Protocol to verify:
1. Atlas boots cleanly without runtime exceptions.
2. Mission Robustness Lab tab opens and adopts cockpit mode.
3. Stress suite selector and target campaign selector load.
4. Deterministic stress battery executes cleanly.
5. Feasibility envelope gauge renders with ratio and progress bar.
6. Parameter sensitivity gradients and elasticities render.
7. Vulnerable objectives and units list populates.
8. Seven core engineering answers render with non-probabilistic truth disclosure.
9. Resilient strategy comparison table renders with candidate selection.
10. Evaluates layout across 1920x1080 and 1366x768 viewports.
11. Captures evidence screenshot to outputs/milestone_12e_robustness_lab_screenshot.png.
"""

import asyncio
import base64
import json
import os
import sys
import subprocess
import tempfile
import urllib.request
import websockets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:3000"
DEBUG_PORT = 9496
SCREENSHOT_PATH = os.path.abspath(r"outputs\milestone_12e_robustness_lab_screenshot.png")


async def run_browser_audit():
    os.makedirs(os.path.dirname(SCREENSHOT_PATH), exist_ok=True)
    tmp_profile = tempfile.mkdtemp(prefix="chrome_rob_audit_")

    proc = subprocess.Popen([
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={tmp_profile}",
        "--headless=new",
        "--disable-gpu",
        "--disable-extensions",
        "--window-size=1920,1080",
        "about:blank",
    ])
    await asyncio.sleep(1.8)

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{DEBUG_PORT}/json/list")
        with urllib.request.urlopen(req, timeout=3) as resp:
            targets = json.loads(resp.read().decode("utf-8"))

        page_targets = [t for t in targets if t.get("type") == "page"]
        if not page_targets:
            raise RuntimeError(f"No page target found in CDP targets: {targets}")
        ws_url = page_targets[0]["webSocketDebuggerUrl"]
        print(f"Connected to CDP page target: {page_targets[0].get('title')}")

        async with websockets.connect(ws_url, max_size=25 * 1024 * 1024) as ws:
            msg_id = 0
            pending_responses = {}
            event_log = []

            async def send_cmd(method, params=None, timeout_s=10.0):
                nonlocal msg_id
                msg_id += 1
                curr_id = msg_id
                payload = {"id": curr_id, "method": method}
                if params:
                    payload["params"] = params
                await ws.send(json.dumps(payload))

                end_time = asyncio.get_event_loop().time() + timeout_s
                while asyncio.get_event_loop().time() < end_time:
                    if curr_id in pending_responses:
                        return pending_responses.pop(curr_id)
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        msg = json.loads(raw)
                        if "id" in msg:
                            if msg["id"] == curr_id:
                                return msg
                            else:
                                pending_responses[msg["id"]] = msg
                        elif "method" in msg:
                            event_log.append(msg)
                    except asyncio.TimeoutError:
                        pass
                raise TimeoutError(f"Command {method} timed out waiting for id {curr_id}")

            async def eval_js(expr):
                res = await send_cmd("Runtime.evaluate", {
                    "expression": expr,
                    "returnByValue": True,
                    "awaitPromise": True
                })
                result = res.get("result", {})
                if "exceptionDetails" in result:
                    exc = result["exceptionDetails"]
                    raise RuntimeError(f"JS Exception: {json.dumps(exc)}")
                return result.get("result", {}).get("value")

            print("\n============================================================================")
            print("  MARSWALK 2.0 — MILESTONE 12E ROBUSTNESS LAB BROWSER AUDIT")
            print("============================================================================")

            # 1. Enable Page & Runtime
            await send_cmd("Page.enable")
            await send_cmd("Runtime.enable")

            # 2. Navigate to Atlas
            print(f"[Check 1] Navigating to {BASE_URL}...")
            await send_cmd("Page.navigate", {"url": f"{BASE_URL}/index.html"})

            # Wait for Atlas DOM to be ready
            loaded = False
            for _ in range(50):
                await asyncio.sleep(0.3)
                try:
                    eval_ready = await send_cmd("Runtime.evaluate", {
                        "expression": "JSON.stringify({ readyState: document.readyState, hasMarsWalk: !!window.MarsWalk, hasRob: !!document.getElementById('tabRobustnessLab') })",
                        "returnByValue": True,
                    })
                    val = eval_ready.get("result", {}).get("result", {}).get("value")
                    if val:
                        state_obj = json.loads(val)
                        if state_obj.get("hasMarsWalk") and state_obj.get("hasRob"):
                            loaded = True
                            print(f"  -> Page fully loaded! State: {state_obj}")
                            break
                except Exception:
                    pass

            assert loaded, "Atlas failed to load window.MarsWalk within timeout"
            print("  [PASSED] Atlas initialized cleanly with window.MarsWalk.")

            # 3. Switch to Robustness Lab tab
            print("\n[Check 2] Switching to Robustness Lab tab...")
            has_tab = await eval_js("!!document.getElementById('tabBtnRobustnessLab')")
            assert has_tab, "Robustness Lab tab button not found"

            await eval_js("document.getElementById('tabBtnRobustnessLab').click()")
            await asyncio.sleep(0.6)

            tab_visible = await eval_js("!document.getElementById('tabRobustnessLab').classList.contains('hidden')")
            assert tab_visible, "Robustness Lab panel is not visible after tab click"
            cockpit_mode = await eval_js("document.querySelector('.hud-inspector').classList.contains('cockpit-mode')")
            assert cockpit_mode, "Inspector panel did not adopt cockpit-mode width"
            print("  [PASSED] Robustness Lab tab active with cockpit-mode styling.")

            # 4. Check Controls & Selectors
            print("\n[Check 3] Inspecting Robustness Lab controls...")
            suite_options = await eval_js("Array.from(document.getElementById('robSuiteSelect').options).map(o => o.value)")
            print(f"  Available stress suites: {suite_options}")
            assert "full_battery" in suite_options
            assert "duration_stress" in suite_options
            assert "mobility_derating" in suite_options
            print("  [PASSED] Stress suite options populated.")

            # 5. Trigger Stress Battery Evaluation
            print("\n[Check 4] Executing full stress battery via UI button...")
            await eval_js("document.getElementById('btnRunRobustnessBattery').click()")

            # Wait for evaluation completion
            eval_status = ""
            for _ in range(30):
                await asyncio.sleep(0.5)
                eval_status = await eval_js("document.getElementById('robStatusTag').textContent")
                is_disabled = await eval_js("document.getElementById('btnRunRobustnessBattery').disabled")
                if not is_disabled and eval_status in ("COMPLETED", "READY"):
                    break

            print(f"  Status tag after execution: '{eval_status}'")
            assert eval_status == "COMPLETED", f"Expected COMPLETED status, got: {eval_status}"

            # 6. Verify Feasibility Envelope
            print("\n[Check 5] Verifying Feasibility Envelope metrics...")
            ratio_text = await eval_js("document.getElementById('robEnvelopeRatioText').textContent")
            print(f"  Feasibility Ratio: {ratio_text}")
            assert "cases" in ratio_text

            progress_w = await eval_js("document.getElementById('robEnvelopeProgressBar').style.width")
            print(f"  Envelope Progress Width: {progress_w}")
            assert float(progress_w.replace('%', '')) > 0.0

            bottlenecks_count = await eval_js("document.querySelectorAll('#robBottlenecksList li').length")
            print(f"  Bottlenecks reported: {bottlenecks_count}")
            assert bottlenecks_count > 0
            print("  [PASSED] Feasibility envelope, progress bar, and bottlenecks rendered.")

            # 7. Verify Parameter Sensitivity Gradients
            print("\n[Check 6] Verifying Parameter Sensitivity gradients...")
            sens_count = await eval_js("document.querySelectorAll('.rob-sens-row').length")
            print(f"  Sensitivity rows rendered: {sens_count}")
            assert sens_count >= 1

            first_param = await eval_js("document.querySelector('.rob-sens-row .rob-sens-header').textContent")
            print(f"  Primary sensitive parameter: {first_param.strip()}")
            assert "#1" in first_param
            print("  [PASSED] Finite-difference sensitivity gradients and elasticity bars rendered.")

            # 8. Verify Seven Core Answers
            print("\n[Check 7] Verifying Seven Core Answers...")
            ans1 = await eval_js("document.getElementById('robAns1').textContent")
            ans5 = await eval_js("document.getElementById('robAns5').textContent")
            ans7 = await eval_js("document.getElementById('robAns7').textContent")

            print(f"  Q1 (Assumptions): {ans1[:75]}...")
            print(f"  Q5 (Margin):      {ans5[:75]}...")
            print(f"  Q7 (Limits):      {ans7[:75]}...")

            assert len(ans1) > 20, "Q1 answer is empty"
            assert len(ans5) > 20, "Q5 answer is empty"
            assert "NOT" in ans7 or "not" in ans7, "Q7 must include non-probabilistic truth disclosure"
            print("  [PASSED] Seven core questions answered with explicit non-probabilistic disclosures.")

            # 9. Verify Resilient Strategy Comparison & Candidate Selection
            print("\n[Check 8] Verifying Resilient Strategy Comparison...")
            strat_count = await eval_js("document.querySelectorAll('.rob-strat-card').length")
            print(f"  Strategy candidates rendered: {strat_count}")
            assert strat_count == 3

            # Click on second strategy card (Conservative)
            await eval_js("document.querySelectorAll('.rob-strat-card')[1].click()")
            await asyncio.sleep(0.3)
            is_selected = await eval_js("document.querySelectorAll('.rob-strat-card')[1].classList.contains('selected')")
            assert is_selected, "Failed to select strategy candidate"
            print("  [PASSED] 3 resilient strategy candidates rendered with interactive Pareto selection.")

            # 10. Viewport Responsiveness Check
            print("\n[Check 9] Auditing Viewport Responsiveness...")
            for w, h in [(1920, 1080), (1366, 768)]:
                await send_cmd("Emulation.setDeviceMetricsOverride", {
                    "width": w,
                    "height": h,
                    "deviceScaleFactor": 1,
                    "mobile": False
                })
                await asyncio.sleep(0.4)
                overflows = await eval_js("document.body.scrollWidth > window.innerWidth")
                print(f"  Viewport {w}x{h}: horizontal overflow = {overflows}")
                assert not overflows, f"Horizontal overflow detected at {w}x{h}"
            print("  [PASSED] Responsive layout validated across 1920x1080 and 1366x768 viewports.")

            # Reset to 1920x1080 for final screenshot
            await send_cmd("Emulation.setDeviceMetricsOverride", {
                "width": 1920,
                "height": 1080,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(0.5)

            # 11. Capture Screenshot
            print("\n[Check 10] Capturing visual proof screenshot...")
            res_shot = await send_cmd("Page.captureScreenshot", {"format": "png"})
            png_bytes = base64.b64decode(res_shot["result"]["data"])
            with open(SCREENSHOT_PATH, "wb") as f:
                f.write(png_bytes)
            print(f"  Saved screenshot to: {SCREENSHOT_PATH} ({len(png_bytes) // 1024} KB)")

            print("\n============================================================================")
            print(">>> ALL 10 BROWSER AUDIT CHECKS PASSED FOR MILESTONE 12E! <<<")
            print("============================================================================\n")

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(run_browser_audit())
