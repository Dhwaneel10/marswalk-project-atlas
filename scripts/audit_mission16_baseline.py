#!/usr/bin/env python3
"""
scripts/audit_mission16_baseline.py
Comprehensive Baseline Audit for Mission 16:
- Captures console logs, network errors, asset failures
- Measures viewport responsiveness across 5 viewports (1920x1080, 1366x768, 1024x768, 768x1024, 390x844)
- Checks horizontal overflow (scrollWidth vs innerWidth)
- Inspects hero sections, CTAs, destination cards, and disclaimers
- Saves baseline screenshots to outputs/mission_16/baseline/
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

TARGET_PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3000
BASE_URL = f"http://127.0.0.1:{TARGET_PORT}"
DEBUG_PORT = 9510
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "mission_16", "baseline"))
CHROME_BIN = "/usr/bin/google-chrome"

VIEWPORTS = [
    {"name": "desktop_1080p", "width": 1920, "height": 1080},
    {"name": "laptop_1366", "width": 1366, "height": 768},
    {"name": "laptop_compact_1024", "width": 1024, "height": 768},
    {"name": "tablet_portrait_768", "width": 768, "height": 1024},
    {"name": "mobile_390", "width": 390, "height": 844},
]


async def run_baseline_audit():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tmp_profile = tempfile.mkdtemp(prefix="chrome_m16_base_")

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

    audit_results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_url": BASE_URL,
        "console_errors": [],
        "console_warnings": [],
        "failed_network_requests": [],
        "viewports": {},
        "elements_audit": {},
    }

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
                    # Track events
                    if data.get("method") == "Runtime.consoleAPICalled":
                        log_type = data.get("params", {}).get("type")
                        args = data.get("params", {}).get("args", [])
                        msg_text = " ".join([str(a.get("value", a.get("description", ""))) for a in args])
                        if log_type == "error":
                            audit_results["console_errors"].append(msg_text)
                        elif log_type == "warning":
                            audit_results["console_warnings"].append(msg_text)
                    elif data.get("method") == "Network.loadingFailed":
                        params = data.get("params", {})
                        audit_results["failed_network_requests"].append({
                            "requestId": params.get("requestId"),
                            "errorText": params.get("errorText"),
                            "type": params.get("type"),
                        })
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
            await send("Network.enable")

            print(f"Navigating to {BASE_URL}...")
            await send("Page.navigate", {"url": f"{BASE_URL}/"})
            await asyncio.sleep(4.0)

            # Audit elements on standard 1080p desktop first
            elements_check_js = """
            (() => {
                const checks = {};
                const ids = [
                    'marsLandingPage',
                    'brandLandingLogo',
                    'btnLandingEnterEVA',
                    'btnLandingExploreEnv',
                    'btnLandingEvaluatorTour',
                    'btnLandingDemoMode',
                    'btnLandingExplore',
                    'btnLandingHowItWorks',
                    'btnLandingPreflight',
                    'btnLandingBrowseMissions',
                    'landingHowItWorksSection',
                    'cesiumContainer',
                    'evaVisorHudOverlay',
                    'cockpitHudOverlay',
                    'inspectorPanel'
                ];
                ids.forEach(id => {
                    const el = document.getElementById(id);
                    if (!el) {
                        checks[id] = { exists: false };
                    } else {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        checks[id] = {
                            exists: true,
                            visible: style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0',
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            top: Math.round(rect.top),
                            left: Math.round(rect.left),
                            hasText: el.innerText ? el.innerText.trim().length > 0 : false
                        };
                    }
                });

                // Check epistemic pills
                const pills = Array.from(document.querySelectorAll('.epistemic-pill')).map(p => p.innerText.trim());
                checks['epistemic_pills'] = pills;

                // Check destination items
                const destItems = Array.from(document.querySelectorAll('.dest-item')).map(d => ({
                    dest: d.getAttribute('data-dest'),
                    name: d.querySelector('.dest-name')?.innerText.trim(),
                    meta: d.querySelector('.dest-meta')?.innerText.trim(),
                    capability: d.querySelector('.dest-capability-tag')?.innerText.trim()
                }));
                checks['destinations'] = destItems;

                // Check landing specs
                const specs = Array.from(document.querySelectorAll('.landing-spec-item')).map(s => ({
                    val: s.querySelector('.spec-value')?.innerText.trim(),
                    label: s.querySelector('.spec-label')?.innerText.trim()
                }));
                checks['specs'] = specs;

                return checks;
            })()
            """
            audit_results["elements_audit"] = await eval_js(elements_check_js)

            # Audit across all 5 viewports
            for vp in VIEWPORTS:
                name = vp["name"]
                w = vp["width"]
                h = vp["height"]
                print(f"Testing Viewport: {name} ({w}x{h})...")
                await send("Emulation.setDeviceMetricsOverride", {
                    "width": w,
                    "height": h,
                    "deviceScaleFactor": 1,
                    "mobile": (w <= 768),
                })
                await asyncio.sleep(1.0)

                overflow_js = """
                (() => {
                    const scrollW = document.documentElement.scrollWidth;
                    const innerW = window.innerWidth;
                    const landingEl = document.getElementById('marsLandingPage');
                    const landingScrollW = landingEl ? landingEl.scrollWidth : 0;
                    return {
                        docScrollWidth: scrollW,
                        innerWidth: innerW,
                        hasDocHOverflow: scrollW > innerW + 1,
                        landingScrollWidth: landingScrollW,
                        hasLandingHOverflow: landingScrollW > innerW + 1,
                        bodyHeight: document.body.scrollHeight
                    };
                })()
                """
                vp_metrics = await eval_js(overflow_js)
                audit_results["viewports"][name] = {
                    "width": w,
                    "height": h,
                    "metrics": vp_metrics,
                }
                filename = f"m16_baseline_{name}.png"
                await snap(filename)

            # Save json report
            report_path = os.path.join(OUTPUT_DIR, "m16_baseline_report.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(audit_results, f, indent=2)
            print(f"Saved baseline audit report to {report_path}")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        shutil.rmtree(tmp_profile, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(run_baseline_audit())
