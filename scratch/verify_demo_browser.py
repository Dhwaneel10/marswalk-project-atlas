import asyncio
import json
import os
import subprocess
import time
import urllib.request
import base64
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9231
TMP_PROFILE = r"C:\Users\dhwan\AppData\Local\Temp\chrome_demo_audit_v3"
TARGET_URL = "http://127.0.0.1:3000/?mode=demo"
OUTPUT_DIR = r"E:\Python\NASA-Spaceapps\Marswalk\outputs\conference_showcase"

async def run_audit():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TMP_PROFILE, exist_ok=True)

    cmd = [
        CHROME_PATH,
        "--headless=new",
        f"--remote-debugging-port={PORT}",
        f"--user-data-dir={TMP_PROFILE}",
        "--disable-extensions",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1920,1080",
        "about:blank"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)

    ws_url = None
    for _ in range(10):
        try:
            req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=2)
            tabs = json.loads(req.read().decode())
            page_target = next((t for t in tabs if t.get("type") == "page"), None)
            if page_target:
                ws_url = page_target["webSocketDebuggerUrl"]
                break
        except Exception:
            time.sleep(0.5)

    if not ws_url:
        proc.kill()
        raise RuntimeError("Failed to connect to headless Chrome page target")

    print(f"Connected to CDP Page Target at {ws_url}")
    msg_id = 1
    console_errors = []

    async with websockets.connect(ws_url, max_size=30*1024*1024) as ws:
        async def send(method, params=None):
            nonlocal msg_id
            curr_id = msg_id
            msg_id += 1
            payload = {"id": curr_id, "method": method, "params": params or {}}
            await ws.send(json.dumps(payload))
            while True:
                raw = await ws.recv()
                resp = json.loads(raw)
                if "method" in resp:
                    m = resp["method"]
                    if m == "Runtime.consoleAPICalled":
                        c_type = resp["params"].get("type")
                        args = [str(a.get("value", a.get("description", ""))) for a in resp["params"].get("args", [])]
                        log_line = " ".join(args)
                        if c_type == "error":
                            console_errors.append(log_line)
                            print(f"  [BROWSER ERROR] {log_line}")
                        else:
                            print(f"  [BROWSER CONSOLE] {log_line}")
                    elif m == "Runtime.exceptionThrown":
                        ex_text = json.dumps(resp["params"])
                        console_errors.append(ex_text)
                        print(f"  [BROWSER EXCEPTION] {ex_text}")
                if resp.get("id") == curr_id:
                    return resp.get("result", {})

        async def evaluate(expr):
            res = await send("Runtime.evaluate", {
                "expression": expr,
                "returnByValue": True,
                "awaitPromise": True
            })
            if "exceptionDetails" in res:
                print(f"  [EVAL EXCEPTION]: {json.dumps(res['exceptionDetails'])}")
            val = res.get("result", {}).get("value")
            return val

        async def capture_screenshot(filename):
            res = await send("Page.captureScreenshot", {"format": "png"})
            data = base64.b64decode(res["data"])
            path = os.path.join(OUTPUT_DIR, filename)
            with open(path, "wb") as f:
                f.write(data)
            print(f"  [SCREENSHOT] Saved: {filename} ({len(data):,} bytes)")
            return path

        await send("Page.enable")
        await send("Runtime.enable")
        await send("Emulation.setDeviceMetricsOverride", {
            "width": 1920,
            "height": 1080,
            "deviceScaleFactor": 1,
            "mobile": False
        })

        print(f"Navigating to {TARGET_URL}...")
        await send("Page.navigate", {"url": TARGET_URL})

        # Wait for page readiness
        print("Waiting for page load and Atlas boot...")
        for i in range(20):
            await asyncio.sleep(0.5)
            booted = await evaluate("Boolean(window.__atlas && window.__atlas.isBooted && window.__atlas.isBooted())")
            if booted:
                print(f"Atlas fully booted after {(i+1)*0.5}s!")
                break

        await asyncio.sleep(1.0)

        # 1. Verify Demo Mode auto-launched on ?mode=demo
        hud_state = await evaluate("""(() => {
            const banner = document.getElementById('demoModeBanner');
            const hud = document.getElementById('demoShowcaseHUD');
            const ind = document.getElementById('showcaseStepIndicator');
            const title = document.getElementById('showcaseStepTitle');
            const truth = document.getElementById('showcaseTruthNote');
            const prog = document.getElementById('showcaseProgressBar');
            return {
                bannerVisible: banner && !banner.classList.contains('hidden'),
                hudVisible: hud && !hud.classList.contains('hidden'),
                stepText: ind ? ind.textContent : null,
                titleText: title ? title.textContent : null,
                truthText: truth ? truth.textContent : null,
                progressWidth: prog ? prog.style.width : null
            };
        })()""")
        print(f"\nStep 1 HUD State: {json.dumps(hud_state, indent=2)}")

        assert hud_state["bannerVisible"], "Banner should be visible"
        assert hud_state["hudVisible"], "HUD card should be visible"
        assert "01 / 09" in hud_state["stepText"], f"Expected 01 / 09, got {hud_state['stepText']}"
        assert hud_state["progressWidth"] in ("11%", "12%"), f"Unexpected progress: {hud_state['progressWidth']}"

        await capture_screenshot("showcase_demo_step1_hud.png")

        # 2. Test Technical Explainability Drawer
        print("\nOpening Technical Explainability Drawer...")
        drawer_opened = await evaluate("""(() => {
            const btn = document.getElementById('btnToggleDemoExplain');
            if (btn) btn.click();
            const drawer = document.getElementById('demoExplainabilityDrawer');
            return drawer && !drawer.classList.contains('hidden');
        })()""")
        await asyncio.sleep(0.5)
        print(f"Explainability Drawer Open: {drawer_opened}")
        assert drawer_opened, "Drawer should be visible"

        topic_count = await evaluate("""(() => {
            const drawer = document.getElementById('demoExplainabilityDrawer');
            const items = drawer.querySelectorAll('.explain-accordion-item');
            return items.length;
        })()""")
        print(f"Explainability Topics Count: {topic_count}")
        assert topic_count == 6, f"Expected 6 topics, got {topic_count}"

        await capture_screenshot("showcase_demo_formulary_drawer.png")

        # Close drawer
        await evaluate("""(() => {
            const btn = document.getElementById('btnCloseDemoExplainability');
            if (btn) btn.click();
        })()""")
        await asyncio.sleep(0.5)

        # 3. Step Through Demo Walkthrough (Step 2 to Step 9)
        for target_step in range(2, 10):
            print(f"\nAdvancing to Step {target_step}...")
            step_info = await evaluate(f"""(() => {{
                window.__atlas.setDemoStep({target_step});
                const ind = document.getElementById('showcaseStepIndicator');
                const title = document.getElementById('showcaseStepTitle');
                const prog = document.getElementById('showcaseProgressBar');
                return {{
                    stepText: ind ? ind.textContent : null,
                    titleText: title ? title.textContent : null,
                    progressWidth: prog ? prog.style.width : null
                }};
            }})()""")
            await asyncio.sleep(1.2)
            print(f"  Step Info: {step_info}")
            assert f"0{target_step} / 09" in step_info["stepText"]

            if target_step == 4:
                await capture_screenshot("showcase_demo_step4_workbench.png")
            elif target_step == 5:
                await capture_screenshot("showcase_demo_step5_cockpit.png")
            elif target_step == 8:
                await capture_screenshot("showcase_demo_step8_causal_replay.png")
            elif target_step == 9:
                await capture_screenshot("showcase_demo_step9_experiment_studio.png")

        # 4. Check Responsiveness & Overflow
        overflow_check = await evaluate("""(() => {
            return {
                scrollWidth: document.body.scrollWidth,
                innerWidth: window.innerWidth,
                noHorizontalOverflow: document.body.scrollWidth <= window.innerWidth
            };
        })()""")
        print(f"\nLayout Overflow Check: {json.dumps(overflow_check)}")
        assert overflow_check["noHorizontalOverflow"], "Horizontal overflow detected!"

        # 5. Check Console Errors
        print(f"\nConsole Errors Count: {len(console_errors)}")
        assert len(console_errors) == 0, f"Detected console errors: {console_errors}"

        # 6. Test Exit Demo Mode
        print("\nTesting Exit Demo Mode...")
        exit_state = await evaluate("""(() => {
            window.__atlas.exitDemoMode(false);
            const banner = document.getElementById('demoModeBanner');
            const hud = document.getElementById('demoShowcaseHUD');
            return {
                bannerHidden: banner && banner.classList.contains('hidden'),
                hudHidden: hud && hud.classList.contains('hidden')
            };
        })()""")
        print(f"Exit State: {json.dumps(exit_state)}")
        assert exit_state["bannerHidden"] and exit_state["hudHidden"], "Demo UI should be hidden after exit"

        print("\n=======================================================")
        print("  ALL 9-STEP DEMO ACCEPTANCE QUALITY GATES PASSED!    ")
        print("=======================================================")

    proc.kill()

if __name__ == "__main__":
    asyncio.run(run_audit())
