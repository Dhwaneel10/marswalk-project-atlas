"""
MarsWalk 2.0 / Project Atlas - Milestone 13B Browser & Visual Quality Audit.

Deep automated visual, layout, and responsiveness inspection via Chrome DevTools Protocol (CDP):
1. Verify daemon health on http://127.0.0.1:3000/api/health
2. Multi-viewport audit across 1920x1080 (Desktop) and 1366x768 (Compact Laptop)
3. Audit all 5 Studios:
   - Studio 1: Mission Control Cockpit
   - Studio 2: Mission Robustness Lab
   - Studio 3: Mission Rehearsal Director
   - Studio 4: Causal Replay Studio
   - Studio 5: Mission Experiment Studio
4. Inspect:
   - Console errors and unhandled exceptions
   - Horizontal body overflows (document.body.scrollWidth > window.innerWidth)
   - Layout bounding box overflows (elements spilling past window boundaries)
   - Text clipping and unscrollable hidden overflow
   - Text bounding collisions / overlapping text
   - Telemetry card formatting, units, typography, and contrast
5. Verify screenshot assets in outputs/ and save high-resolution evidence to outputs/conference_showcase/
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:3000"
DEBUG_PORT = 9505

REPO_ROOT = os.path.abspath(r"E:\Python\NASA-Spaceapps\Marswalk")
OUTPUTS_DIR = os.path.join(REPO_ROOT, "outputs")
SHOWCASE_DIR = os.path.join(OUTPUTS_DIR, "conference_showcase")
DOCS_DIR = os.path.join(REPO_ROOT, "docs")

VIEWPORTS = [
    {"name": "desktop_1920x1080", "width": 1920, "height": 1080},
    {"name": "laptop_1366x768", "width": 1366, "height": 768},
]


def fetch_api_json(endpoint, post_data=None):
    url = f"{BASE_URL}{endpoint}"
    if post_data is not None:
        req = urllib.request.Request(
            url,
            data=json.dumps(post_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
    else:
        req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def run_visual_audit():
    os.makedirs(SHOWCASE_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    audit_data = {
        "timestamp": "2026-10-31T01:40:00Z",
        "milestone": "13B",
        "daemon_health": {},
        "console_events": [],
        "console_errors": [],
        "studios": {},
        "responsiveness": {},
        "clipping_and_overflow": {},
        "screenshots_captured": [],
        "existing_outputs_inventory": {},
    }

    print("=" * 80)
    print("  MARSWALK 2.0 / PROJECT ATLAS — MILESTONE 13B BROWSER & VISUAL QUALITY AUDIT")
    print("=" * 80)

    # 1. Daemon Health Check
    print("\n[Step 1] Verifying Daemon Health (GET /api/health)...")
    health = fetch_api_json("/api/health")
    assert health.get("status") == "online", f"Daemon offline: {health}"
    print(f"  -> Status: {health.get('status')}")
    print(f"  -> Engine: {health.get('engine')}")
    print(f"  -> Target: {health.get('target')}")
    print(f"  -> Terrain Loaded: {health.get('terrain_loaded')}, Waypoints: {health.get('waypoints_count')}")
    print(f"  -> Endpoints available: {len(health.get('endpoints', []))}")
    audit_data["daemon_health"] = health

    # Inventory existing screenshots
    print("\n[Step 2] Inventorying existing screenshot assets in outputs/...")
    existing_files = os.listdir(OUTPUTS_DIR)
    png_files = [f for f in existing_files if f.endswith(".png")]
    print(f"  -> Total PNG files in outputs/: {len(png_files)}")
    audit_data["existing_outputs_inventory"] = {
        "total_pngs": len(png_files),
        "recent_showcase_pngs": [f for f in png_files if "conference" in f or "milestone_13" in f or "milestone_12" in f],
    }
    for f in audit_data["existing_outputs_inventory"]["recent_showcase_pngs"]:
        sz = os.path.getsize(os.path.join(OUTPUTS_DIR, f))
        print(f"     - {f} ({sz:,} bytes)")

    # Launch Chrome Headless with Remote Debugging
    print(f"\n[Step 3] Launching Chrome Headless on CDP port {DEBUG_PORT}...")
    tmp_profile = tempfile.mkdtemp(prefix="chrome_m13b_visual_")
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
    await asyncio.sleep(2.0)

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{DEBUG_PORT}/json/list")
        with urllib.request.urlopen(req, timeout=3) as resp:
            targets = json.loads(resp.read().decode("utf-8"))

        page_targets = [t for t in targets if t.get("type") == "page"]
        if not page_targets:
            raise RuntimeError(f"No page target found: {targets}")
        ws_url = page_targets[0]["webSocketDebuggerUrl"]
        print(f"  -> Connected to CDP Page Target: {page_targets[0].get('title')}")

        async with websockets.connect(ws_url, max_size=35 * 1024 * 1024) as ws:
            msg_id = 0
            pending_responses = {}
            console_errors = []
            console_warnings = []
            js_exceptions = []

            async def send_cmd(method, params=None, timeout_s=15.0):
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
                        else:
                            method_name = msg.get("method", "")
                            if method_name == "Runtime.consoleAPICalled":
                                p = msg.get("params", {})
                                mtype = p.get("type")
                                text = " ".join([str(arg.get("value", arg.get("description", ""))) for arg in p.get("args", [])])
                                if mtype == "error":
                                    console_errors.append(text)
                                    print(f"  [CONSOLE ERROR] {text}")
                                elif mtype == "warning":
                                    console_warnings.append(text)
                            elif method_name == "Runtime.exceptionThrown":
                                p = msg.get("params", {})
                                ex_text = p.get("exceptionDetails", {}).get("text", "")
                                js_exceptions.append(ex_text)
                                print(f"  [JS EXCEPTION] {ex_text}")
                    except asyncio.TimeoutError:
                        pass
                raise TimeoutError(f"Command {method} (id={curr_id}) timed out after {timeout_s}s")

            async def evaluate_js(expression, await_promise=False):
                res = await send_cmd("Runtime.evaluate", {
                    "expression": expression,
                    "awaitPromise": await_promise,
                    "returnByValue": True,
                })
                result = res.get("result", {})
                if "exceptionDetails" in result:
                    raise RuntimeError(f"JS Exception: {json.dumps(result['exceptionDetails'])}")
                return result.get("result", {}).get("value")

            async def set_viewport(width, height):
                await send_cmd("Emulation.setDeviceMetricsOverride", {
                    "width": width,
                    "height": height,
                    "deviceScaleFactor": 1,
                    "mobile": False,
                })
                await asyncio.sleep(0.4)

            async def capture_png(filepath):
                res = await send_cmd("Page.captureScreenshot", {"format": "png"})
                img_data = base64.b64decode(res["result"]["data"])
                with open(filepath, "wb") as f:
                    f.write(img_data)
                sz = len(img_data)
                print(f"  [SCREENSHOT] Captured {os.path.basename(filepath)} ({sz:,} bytes)")
                audit_data["screenshots_captured"].append({
                    "path": filepath,
                    "filename": os.path.basename(filepath),
                    "size_bytes": sz,
                })
                return sz

            async def check_layout_quality(studio_key, viewport_name):
                code = """(() => {
                    const winW = window.innerWidth;
                    const winH = window.innerHeight;
                    const bodyW = document.body.scrollWidth;
                    const bodyH = document.body.scrollHeight;
                    const hasHorizontalOverflow = bodyW > winW;

                    // Elements overflowing window width
                    const overflowingElements = [];
                    const allEls = document.querySelectorAll('*');
                    allEls.forEach(el => {
                        if (el.offsetParent === null) return;
                        const rect = el.getBoundingClientRect();
                        if (rect.right > winW + 2) {
                            overflowingElements.push({
                                tag: el.tagName,
                                id: el.id || '',
                                class: (el.className || '').toString().slice(0, 50),
                                right: Math.round(rect.right),
                                width: Math.round(rect.width),
                                winW: winW
                            });
                        }
                    });

                    // Check for severe unscrollable text clipping
                    const clippedElements = [];
                    allEls.forEach(el => {
                        if (el.offsetParent === null) return;
                        if (['CANVAS', 'SVG', 'PATH', 'BODY', 'HTML'].includes(el.tagName)) return;
                        const style = window.getComputedStyle(el);
                        if (style.overflow === 'hidden' || style.overflowX === 'hidden' || style.overflowY === 'hidden') {
                            const diffW = el.scrollWidth - el.clientWidth;
                            const diffH = el.scrollHeight - el.clientHeight;
                            if (diffW > 8 || diffH > 8) {
                                // Ignore long narrative paragraphs designed for scrolling/truncation
                                if (!el.classList.contains('scrollable') && !el.classList.contains('narrative-text')) {
                                    clippedElements.push({
                                        tag: el.tagName,
                                        id: el.id || '',
                                        class: (el.className || '').toString().slice(0, 40),
                                        diffW, diffH,
                                        scrollW: el.scrollWidth,
                                        clientW: el.clientWidth,
                                        scrollH: el.scrollHeight,
                                        clientH: el.clientHeight,
                                        text: (el.textContent || '').trim().slice(0, 40)
                                    });
                                }
                            }
                        }
                    });

                    // Check overlapping text candidates in key headers/cards
                    const cardHeaders = Array.from(document.querySelectorAll('.control-label, .card-title, .metric-label, .metric-value, .studio-tab, .cockpit-tag'));
                    const overlaps = [];
                    for (let i = 0; i < cardHeaders.length; i++) {
                        for (let j = i + 1; j < cardHeaders.length; j++) {
                            const a = cardHeaders[i];
                            const b = cardHeaders[j];
                            if (a.offsetParent === null || b.offsetParent === null) continue;
                            if (a.contains(b) || b.contains(a)) continue;
                            const ra = a.getBoundingClientRect();
                            const rb = b.getBoundingClientRect();
                            if (ra.width === 0 || ra.height === 0 || rb.width === 0 || rb.height === 0) continue;
                            const xOverlap = Math.max(0, Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left));
                            const yOverlap = Math.max(0, Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top));
                            if (xOverlap > 5 && yOverlap > 5) {
                                overlaps.push({
                                    a: (a.textContent || '').trim().slice(0, 25),
                                    b: (b.textContent || '').trim().slice(0, 25),
                                    xOverlap, yOverlap
                                });
                            }
                        }
                    }

                    return JSON.stringify({
                        winW, winH, bodyW, bodyH,
                        hasHorizontalOverflow,
                        overflowCount: overflowingElements.length,
                        overflowSample: overflowingElements.slice(0, 5),
                        clippedCount: clippedElements.length,
                        clippedSample: clippedElements.slice(0, 5),
                        overlappingTextCount: overlaps.length,
                        overlappingTextSample: overlaps.slice(0, 5)
                    });
                })()"""
                raw = await evaluate_js(code)
                return json.loads(raw)

            # Enable CDP agents
            await send_cmd("Page.enable")
            await send_cmd("Runtime.enable")
            await send_cmd("DOM.enable")

            # Navigate to Atlas
            print(f"\n[Step 4] Navigating to {BASE_URL}/index.html at 1920x1080...")
            await set_viewport(1920, 1080)
            await send_cmd("Page.navigate", {"url": f"{BASE_URL}/index.html"})

            # Wait for Atlas init
            for _ in range(60):
                await asyncio.sleep(0.3)
                v = await evaluate_js("JSON.stringify({ ready: document.readyState === 'complete', hasMarsWalk: !!window.MarsWalk })")
                if v:
                    obj = json.loads(v)
                    if obj.get("ready") and obj.get("hasMarsWalk"):
                        break
            print("  -> Atlas initialized and window.MarsWalk available.")

            # Load active campaign
            active_cid = "cmp_12i_integration_test"
            print(f"  -> Selecting campaign: {active_cid}...")
            await evaluate_js(f"""(async () => {{
                if (window.MarsWalk.selectMissionControlCampaign) {{
                    await window.MarsWalk.selectMissionControlCampaign('{active_cid}');
                }}
            }})()""", await_promise=True)
            await asyncio.sleep(0.8)

            # -------------------------------------------------------------
            # AUDIT STUDIO 1: MISSION CONTROL COCKPIT
            # -------------------------------------------------------------
            print("\n" + "-" * 70)
            print("[Studio 1/5] Mission Control Cockpit Inspection")
            print("-" * 70)
            await evaluate_js("document.getElementById('btnHeaderMissionControl')?.click();")
            await asyncio.sleep(0.8)

            mc_metrics_raw = await evaluate_js("""JSON.stringify({
                campaignTitle: document.getElementById('mcCampaignTitle')?.textContent,
                dist: document.getElementById('mcMetricDistance')?.textContent,
                dur: document.getElementById('mcMetricDuration')?.textContent,
                sci: document.getElementById('mcMetricScience')?.textContent,
                energy: document.getElementById('mcMetricEnergy')?.textContent,
                datasetBadge: document.getElementById('mcDatasetBadge')?.textContent,
                airTemp: document.getElementById('mcWeatherAirTemp')?.textContent,
                gndTemp: document.getElementById('mcWeatherGndTemp')?.textContent,
                pressure: document.getElementById('mcWeatherPressure')?.textContent,
                wind: document.getElementById('mcWeatherWind')?.textContent,
                minEl: document.getElementById('mcMinElevation')?.textContent,
                maxEl: document.getElementById('mcMaxElevation')?.textContent,
                climb: document.getElementById('mcTotalClimb')?.textContent,
                slope: document.getElementById('mcMeanSlope')?.textContent,
                hasSvgProfile: !!document.querySelector('#mcElevationProfileSvg path')
            })""")
            mc_metrics = json.loads(mc_metrics_raw)
            print("  -> Mission Control Metrics:", mc_metrics)
            audit_data["studios"]["mission_control"] = mc_metrics

            # Check 1920x1080
            await set_viewport(1920, 1080)
            q_1920 = await check_layout_quality("mission_control", "1920x1080")
            print(f"  -> 1920x1080: overflow={q_1920['hasHorizontalOverflow']}, bodyW={q_1920['bodyW']}, clippedCount={q_1920['clippedCount']}, overlaps={q_1920['overlappingTextCount']}")
            await capture_png(os.path.join(SHOWCASE_DIR, "showcase_1920_studio1_mission_control.png"))

            # Check 1366x768
            await set_viewport(1366, 768)
            q_1366 = await check_layout_quality("mission_control", "1366x768")
            print(f"  -> 1366x768: overflow={q_1366['hasHorizontalOverflow']}, bodyW={q_1366['bodyW']}, clippedCount={q_1366['clippedCount']}, overlaps={q_1366['overlappingTextCount']}")
            await capture_png(os.path.join(SHOWCASE_DIR, "showcase_1366_studio1_mission_control.png"))
            audit_data["responsiveness"]["mission_control"] = {"1920x1080": q_1920, "1366x768": q_1366}

            # Inspect Evidence Modal at 1920x1080
            await set_viewport(1920, 1080)
            await evaluate_js("window.MarsWalk.inspectEvidence('slope', '12.5°');")
            await asyncio.sleep(0.5)
            await capture_png(os.path.join(SHOWCASE_DIR, "showcase_1920_modal_evidence_inspector.png"))
            await set_viewport(1366, 768)
            await capture_png(os.path.join(SHOWCASE_DIR, "showcase_1366_modal_evidence_inspector.png"))
            await evaluate_js("document.getElementById('btnCloseEvidenceModal')?.click();")
            await asyncio.sleep(0.4)

            # -------------------------------------------------------------
            # AUDIT STUDIO 2: MISSION ROBUSTNESS LAB
            # -------------------------------------------------------------
            print("\n" + "-" * 70)
            print("[Studio 2/5] Mission Robustness Lab Inspection")
            print("-" * 70)
            await set_viewport(1920, 1080)
            await evaluate_js("document.getElementById('tabBtnRobustnessLab')?.click();")
            await asyncio.sleep(0.6)

            # Trigger robustness battery
            print("  -> Triggering stress battery...")
            await evaluate_js("""(async () => {
                const btn = document.getElementById('btnRunRobustnessBattery');
                if (btn) btn.click();
            })()""")
            for _ in range(40):
                await asyncio.sleep(0.3)
                tag = await evaluate_js("document.getElementById('robStatusTag')?.textContent")
                disabled = await evaluate_js("document.getElementById('btnRunRobustnessBattery')?.disabled")
                if not disabled and tag in ["COMPLETED", "READY"]:
                    break

            rob_metrics_raw = await evaluate_js("""JSON.stringify({
                statusTag: document.getElementById('robStatusTag')?.textContent,
                envelopeRatio: document.getElementById('robEnvelopeRatioText')?.textContent,
                progressBarWidth: document.getElementById('robEnvelopeProgressBar')?.style.width,
                bottlenecksCount: document.querySelectorAll('#robBottlenecksList li').length,
                sensRowsCount: document.querySelectorAll('.rob-sens-row').length,
                strategyCardsCount: document.querySelectorAll('.rob-strat-card').length,
                ans1: document.getElementById('robAns1')?.textContent,
                ans7: document.getElementById('robAns7')?.textContent
            })""")
            rob_metrics = json.loads(rob_metrics_raw)
            print("  -> Robustness Lab Metrics:", rob_metrics)
            audit_data["studios"]["robustness_lab"] = rob_metrics

            # Check 1920x1080
            await set_viewport(1920, 1080)
            q_1920_rob = await check_layout_quality("robustness_lab", "1920x1080")
            print(f"  -> 1920x1080: overflow={q_1920_rob['hasHorizontalOverflow']}, bodyW={q_1920_rob['bodyW']}, clippedCount={q_1920_rob['clippedCount']}, overlaps={q_1920_rob['overlappingTextCount']}")
            await capture_png(os.path.join(SHOWCASE_DIR, "showcase_1920_studio2_robustness_lab.png"))

            # Check 1366x768
            await set_viewport(1366, 768)
            q_1366_rob = await check_layout_quality("robustness_lab", "1366x768")
            print(f"  -> 1366x768: overflow={q_1366_rob['hasHorizontalOverflow']}, bodyW={q_1366_rob['bodyW']}, clippedCount={q_1366_rob['clippedCount']}, overlaps={q_1366_rob['overlappingTextCount']}")
            await capture_png(os.path.join(SHOWCASE_DIR, "showcase_1366_studio2_robustness_lab.png"))
            audit_data["responsiveness"]["robustness_lab"] = {"1920x1080": q_1920_rob, "1366x768": q_1366_rob}

            # -------------------------------------------------------------
            # AUDIT STUDIO 3: MISSION REHEARSAL DIRECTOR
            # -------------------------------------------------------------
            print("\n" + "-" * 70)
            print("[Studio 3/5] Mission Rehearsal Director Inspection")
            print("-" * 70)
            await set_viewport(1920, 1080)
            await evaluate_js("document.getElementById('tabBtnRehearsalDirector')?.click();")
            await asyncio.sleep(0.6)

            # Execute rehearsal
            print("  -> Executing closed-loop rehearsal...")
            await evaluate_js("""(async () => {
                const btn = document.getElementById('btnExecuteRehearsal');
                if (btn) btn.click();
            })()""")
            for _ in range(40):
                await asyncio.sleep(0.3)
                tag = await evaluate_js("document.getElementById('rehStatusTag')?.textContent")
                if tag in ["RECOVERED", "RECOVERED_WITH_DEGRADATION", "COMPLETED"]:
                    break

            reh_metrics_raw = await evaluate_js("""JSON.stringify({
                statusTag: document.getElementById('rehStatusTag')?.textContent,
                sciencePreserved: document.getElementById('rehSciencePreservedVal')?.textContent,
                recoveredMargin: document.getElementById('rehRecoveredMarginVal')?.textContent,
                delayIncurred: document.getElementById('rehDelayIncurredVal')?.textContent,
                candidatesCount: document.getElementById('rehCandidatesContainer')?.children.length || 0,
                causalLedgerCount: document.getElementById('rehCausalLedgerContainer')?.children.length || 0
            })""")
            reh_metrics = json.loads(reh_metrics_raw)
            print("  -> Rehearsal Director Metrics:", reh_metrics)
            audit_data["studios"]["rehearsal_director"] = reh_metrics

            # Check 1920x1080
            await set_viewport(1920, 1080)
            q_1920_reh = await check_layout_quality("rehearsal_director", "1920x1080")
            print(f"  -> 1920x1080: overflow={q_1920_reh['hasHorizontalOverflow']}, bodyW={q_1920_reh['bodyW']}, clippedCount={q_1920_reh['clippedCount']}, overlaps={q_1920_reh['overlappingTextCount']}")
            await capture_png(os.path.join(SHOWCASE_DIR, "showcase_1920_studio3_rehearsal_director.png"))

            # Check 1366x768
            await set_viewport(1366, 768)
            q_1366_reh = await check_layout_quality("rehearsal_director", "1366x768")
            print(f"  -> 1366x768: overflow={q_1366_reh['hasHorizontalOverflow']}, bodyW={q_1366_reh['bodyW']}, clippedCount={q_1366_reh['clippedCount']}, overlaps={q_1366_reh['overlappingTextCount']}")
            await capture_png(os.path.join(SHOWCASE_DIR, "showcase_1366_studio3_rehearsal_director.png"))
            audit_data["responsiveness"]["rehearsal_director"] = {"1920x1080": q_1920_reh, "1366x768": q_1366_reh}

            # -------------------------------------------------------------
            # AUDIT STUDIO 4: CAUSAL REPLAY STUDIO
            # -------------------------------------------------------------
            print("\n" + "-" * 70)
            print("[Studio 4/5] Causal Replay Studio Inspection")
            print("-" * 70)
            await set_viewport(1920, 1080)
            # Seek step 3 to activate forensic state
            await evaluate_js("""(async () => {
                if (window.MarsWalk.seekRehearsalStep) {
                    window.MarsWalk.seekRehearsalStep(3);
                }
            })()""", await_promise=True)
            await asyncio.sleep(0.5)

            rep_metrics_raw = await evaluate_js("""JSON.stringify({
                divergenceBannerVisible: document.getElementById('rehDivergenceBanner')?.style.display !== 'none',
                divTriggerText: document.getElementById('rehDivTriggerText')?.textContent,
                divTimeText: document.getElementById('rehDivTimeText')?.textContent,
                stepIndicator: document.getElementById('rehStepIndicator')?.textContent,
                inspectorStepId: document.getElementById('rehInspectorStepId')?.textContent,
                linksCount: document.getElementById('rehInspectorLinksContainer')?.children.length || 0
            })""")
            rep_metrics = json.loads(rep_metrics_raw)
            print("  -> Causal Replay Metrics:", rep_metrics)
            audit_data["studios"]["causal_replay"] = rep_metrics

            # Check 1920x1080
            await set_viewport(1920, 1080)
            q_1920_rep = await check_layout_quality("causal_replay", "1920x1080")
            print(f"  -> 1920x1080: overflow={q_1920_rep['hasHorizontalOverflow']}, bodyW={q_1920_rep['bodyW']}, clippedCount={q_1920_rep['clippedCount']}, overlaps={q_1920_rep['overlappingTextCount']}")
            await capture_png(os.path.join(SHOWCASE_DIR, "showcase_1920_studio4_causal_replay.png"))

            # Check 1366x768
            await set_viewport(1366, 768)
            q_1366_rep = await check_layout_quality("causal_replay", "1366x768")
            print(f"  -> 1366x768: overflow={q_1366_rep['hasHorizontalOverflow']}, bodyW={q_1366_rep['bodyW']}, clippedCount={q_1366_rep['clippedCount']}, overlaps={q_1366_rep['overlappingTextCount']}")
            await capture_png(os.path.join(SHOWCASE_DIR, "showcase_1366_studio4_causal_replay.png"))
            audit_data["responsiveness"]["causal_replay"] = {"1920x1080": q_1920_rep, "1366x768": q_1366_rep}

            # -------------------------------------------------------------
            # AUDIT STUDIO 5: MISSION EXPERIMENT STUDIO
            # -------------------------------------------------------------
            print("\n" + "-" * 70)
            print("[Studio 5/5] Mission Experiment Studio Inspection")
            print("-" * 70)
            await set_viewport(1920, 1080)
            await evaluate_js("document.getElementById('tabBtnExperimentStudio')?.click();")
            await asyncio.sleep(0.6)

            print("  -> Running experiment batch...")
            await evaluate_js("""(async () => {
                document.getElementById('expScenarioSuite').value = 'mobility_derating';
                document.getElementById('expRehearsalTriggerSelect').value = 'all';
                const btn = document.getElementById('btnRunExperiment');
                if (btn) btn.click();
            })()""")
            for _ in range(40):
                await asyncio.sleep(0.3)
                evalVal = await evaluate_js("document.getElementById('expCounterEvaluated')?.textContent")
                disabled = await evaluate_js("document.getElementById('btnRunExperiment')?.disabled")
                if not disabled and evalVal not in ["--", "0", ""]:
                    break

            exp_metrics_raw = await evaluate_js("""JSON.stringify({
                evaluated: document.getElementById('expCounterEvaluated')?.textContent,
                rehearsed: document.getElementById('expCounterRehearsed')?.textContent,
                feasible: document.getElementById('expCounterFeasible')?.textContent,
                recovered: document.getElementById('expCounterRecovered')?.textContent,
                matrixRows: document.querySelectorAll('#expMatrixTableBody tr').length,
                replayBtnsCount: document.querySelectorAll('.btn-matrix-replay').length
            })""")
            exp_metrics = json.loads(exp_metrics_raw)
            print("  -> Experiment Studio Metrics:", exp_metrics)
            audit_data["studios"]["experiment_studio"] = exp_metrics

            # Check 1920x1080
            await set_viewport(1920, 1080)
            q_1920_exp = await check_layout_quality("experiment_studio", "1920x1080")
            print(f"  -> 1920x1080: overflow={q_1920_exp['hasHorizontalOverflow']}, bodyW={q_1920_exp['bodyW']}, clippedCount={q_1920_exp['clippedCount']}, overlaps={q_1920_exp['overlappingTextCount']}")
            await capture_png(os.path.join(SHOWCASE_DIR, "showcase_1920_studio5_experiment_studio.png"))

            # Check 1366x768
            await set_viewport(1366, 768)
            q_1366_exp = await check_layout_quality("experiment_studio", "1366x768")
            print(f"  -> 1366x768: overflow={q_1366_exp['hasHorizontalOverflow']}, bodyW={q_1366_exp['bodyW']}, clippedCount={q_1366_exp['clippedCount']}, overlaps={q_1366_exp['overlappingTextCount']}")
            await capture_png(os.path.join(SHOWCASE_DIR, "showcase_1366_studio5_experiment_studio.png"))
            audit_data["responsiveness"]["experiment_studio"] = {"1920x1080": q_1920_exp, "1366x768": q_1366_exp}

            # Deep-link back to Rehearsal with breadcrumb
            print("  -> Testing deep-link replay and breadcrumb...")
            await set_viewport(1920, 1080)
            await evaluate_js("""(async () => {
                const btn = document.querySelector('.btn-matrix-replay');
                if (btn) btn.click();
            })()""")
            await asyncio.sleep(0.6)
            await capture_png(os.path.join(SHOWCASE_DIR, "showcase_1920_forensic_breadcrumb.png"))

            # Return to experiment studio
            await evaluate_js("document.getElementById('btnReturnToExperiment')?.click();")
            await asyncio.sleep(0.4)

            # Check for console errors & warnings
            audit_data["console_errors"] = console_errors
            audit_data["console_warnings"] = console_warnings
            audit_data["js_exceptions"] = js_exceptions

            print("\n" + "=" * 80)
            print("AUDIT SUMMARY & QUALITY VERIFICATION")
            print("=" * 80)
            print(f"  Console Errors: {len(console_errors)}")
            print(f"  Console Warnings: {len(console_warnings)}")
            print(f"  JS Exceptions: {len(js_exceptions)}")
            print(f"  Screenshots Captured: {len(audit_data['screenshots_captured'])}")

            # Assert zero unhandled console errors or exceptions
            assert len(console_errors) == 0, f"Uncaught console errors detected: {console_errors}"
            assert len(js_exceptions) == 0, f"Uncaught JS exceptions detected: {js_exceptions}"

            # Save JSON report
            report_json_path = os.path.join(SHOWCASE_DIR, "visual_audit_report.json")
            with open(report_json_path, "w", encoding="utf-8") as f:
                json.dump(audit_data, f, indent=2)
            print(f"\nSaved detailed audit JSON to: {report_json_path}")

    finally:
        proc.terminate()
        print("Chrome headless process terminated cleanly.")


if __name__ == "__main__":
    asyncio.run(run_visual_audit())
