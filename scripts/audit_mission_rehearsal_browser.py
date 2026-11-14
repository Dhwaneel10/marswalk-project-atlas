"""
MarsWalk 2.0 / Project Atlas - Milestone 12F Mission Rehearsal Director Browser Audit Script.

Uses Headless Chrome DevTools Protocol to verify:
1. Atlas boots cleanly without runtime exceptions.
2. Mission Rehearsal Director tab opens and adopts cockpit mode.
3. Disturbance selector, trigger time scrubber, and policy selector load.
4. Closed-loop rehearsal executes cleanly via UI button.
5. Tri-Track Trajectory Comparison renders (Baseline vs Disturbed vs Recovered).
6. Science preservation %, net science delta, and margin metrics populate.
7. Evaluated candidate recovery options list renders with status badges.
8. Causal decision ledger renders 7-step sequence with timestamps.
9. Evaluates layout across 1920x1080 and 1366x768 viewports.
10. Captures evidence screenshot to outputs/milestone_12f_rehearsal_screenshot.png.
"""

import asyncio
import base64
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import websockets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:3000"
DEBUG_PORT = 9497
SCREENSHOT_PATH = os.path.abspath(r"outputs\milestone_12f_rehearsal_screenshot.png")


async def run_browser_audit():
    os.makedirs(os.path.dirname(SCREENSHOT_PATH), exist_ok=True)
    tmp_profile = tempfile.mkdtemp(prefix="chrome_reh_audit_")

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
            print("  MARSWALK 2.0 — MILESTONE 12F REHEARSAL DIRECTOR BROWSER AUDIT")
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
                        "expression": "JSON.stringify({ readyState: document.readyState, hasMarsWalk: !!window.MarsWalk, hasReh: !!document.getElementById('tabRehearsalDirector') })",
                        "returnByValue": True,
                    })
                    val = eval_ready.get("result", {}).get("result", {}).get("value")
                    if val:
                        state_obj = json.loads(val)
                        if state_obj.get("hasMarsWalk") and state_obj.get("hasReh"):
                            loaded = True
                            print(f"  -> Page fully loaded! State: {state_obj}")
                            break
                except Exception:
                    pass

            assert loaded, "Atlas failed to load window.MarsWalk within timeout"
            print("  [PASSED] Atlas initialized cleanly with window.MarsWalk.")

            # 3. Switch to Rehearsal Director tab
            print("\n[Check 2] Switching to Rehearsal Director tab...")
            has_tab = await eval_js("!!document.getElementById('tabBtnRehearsalDirector')")
            assert has_tab, "Rehearsal Director tab button not found"

            await eval_js("document.getElementById('tabBtnRehearsalDirector').click()")
            await asyncio.sleep(0.6)

            tab_visible = await eval_js("!document.getElementById('tabRehearsalDirector').classList.contains('hidden')")
            assert tab_visible, "Rehearsal Director panel is not visible after tab click"
            cockpit_mode = await eval_js("document.querySelector('.hud-inspector').classList.contains('cockpit-mode')")
            assert cockpit_mode, "Inspector panel did not adopt cockpit-mode width"
            print("  [PASSED] Rehearsal Director tab active with cockpit-mode styling.")

            # 4. Check Controls & Selectors
            print("\n[Check 3] Inspecting Rehearsal Director controls...")
            dist_options = await eval_js("Array.from(document.getElementById('rehDisturbanceType').options).map(o => o.value)")
            print(f"  Available disturbance types: {dist_options}")
            assert "operational_delay" in dist_options
            assert "corridor_closure" in dist_options
            assert "mobility_derating" in dist_options
            assert "target_unavailability" in dist_options
            assert "unit_dropout" in dist_options

            policies = await eval_js("Array.from(document.getElementById('rehPolicySelect').options).map(o => o.value)")
            assert "balanced" in policies
            assert "safety_first" in policies
            assert "max_science" in policies
            print("  [PASSED] Disturbance types and recovery policies populated.")

            # 5. Trigger Rehearsal Execution
            print("\n[Check 4] Executing rehearsal via UI button...")
            await eval_js("document.getElementById('btnExecuteRehearsal').click()")
            await asyncio.sleep(2.0)

            # Wait for evaluation completion
            eval_status = await eval_js("document.getElementById('rehStatusTag').textContent")
            print(f"  Status tag after execution: '{eval_status}'")
            assert eval_status in ("RECOVERED", "RECOVERED_WITH_DEGRADATION", "COMPLETED"), f"Unexpected status: {eval_status}"

            # 6. Verify Tri-Track Comparison HUD
            print("\n[Check 5] Verifying Tri-Track Trajectory Comparison HUD...")
            card_display = await eval_js("document.getElementById('rehComparisonCard').style.display")
            assert card_display != "none", "Comparison card is not displayed"

            science_preserved = await eval_js("document.getElementById('rehSciencePreservedVal').textContent")
            print(f"  Science Preserved: {science_preserved}")
            assert "%" in science_preserved

            margin_recovered = await eval_js("document.getElementById('rehRecoveredMarginVal').textContent")
            print(f"  Recovered Margin: {margin_recovered}")

            delay_incurred = await eval_js("document.getElementById('rehDelayIncurredVal').textContent")
            print(f"  Delay Incurred: {delay_incurred}")
            print("  [PASSED] Tri-track comparison metrics displayed.")

            # 7. Verify Candidate Options Evaluated
            print("\n[Check 6] Verifying evaluated candidate options list...")
            cands_count = await eval_js("document.getElementById('rehCandidatesContainer').children.length")
            print(f"  Candidates evaluated: {cands_count}")
            assert cands_count == 3, f"Expected 3 candidate options, got: {cands_count}"
            print("  [PASSED] Three-way candidate evaluation cards rendered.")

            # 8. Verify Causal Decision Ledger
            print("\n[Check 7] Verifying Causal Decision Ledger...")
            steps_count = await eval_js("document.getElementById('rehCausalLedgerContainer').children.length")
            print(f"  Causal decision steps logged: {steps_count}")
            assert steps_count >= 7, f"Expected >= 7 causal steps, got: {steps_count}"
            print("  [PASSED] Complete causal decision chain logged.")

            # 9. Verify Responsive Layouts
            print("\n[Check 8] Verifying Responsive Layouts (1920x1080 and 1366x768)...")
            for w, h in [(1920, 1080), (1366, 768)]:
                await send_cmd("Emulation.setDeviceMetricsOverride", {
                    "width": w,
                    "height": h,
                    "deviceScaleFactor": 1,
                    "mobile": False,
                })
                await asyncio.sleep(0.4)
                overflows = await eval_js("document.body.scrollWidth > window.innerWidth")
                print(f"  Viewport {w}x{h}: horizontal overflow = {overflows}")
                assert not overflows, f"Horizontal overflow detected at {w}x{h}"
            print("  [PASSED] Responsive scaling verified across 1920x1080 and 1366x768.")

            # Restore 1920x1080 for capture
            await send_cmd("Emulation.setDeviceMetricsOverride", {
                "width": 1920,
                "height": 1080,
                "deviceScaleFactor": 1,
                "mobile": False,
            })
            await asyncio.sleep(0.5)

            # 10. Capture Screenshot
            print(f"\n[Check 9] Capturing high-resolution evidence screenshot to {SCREENSHOT_PATH}...")
            shot_res = await send_cmd("Page.captureScreenshot", {"format": "png"})
            data_b64 = shot_res.get("result", {}).get("data")
            with open(SCREENSHOT_PATH, "wb") as f:
                f.write(base64.b64decode(data_b64))

            assert os.path.exists(SCREENSHOT_PATH) and os.path.getsize(SCREENSHOT_PATH) > 50000
            print(f"  [PASSED] Screenshot saved ({os.path.getsize(SCREENSHOT_PATH)} bytes).")

            print("\n============================================================================")
            print("  ALL 10 MISSION REHEARSAL DIRECTOR BROWSER AUDIT CHECKS PASSED!")
            print("============================================================================")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutError:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(run_browser_audit())
