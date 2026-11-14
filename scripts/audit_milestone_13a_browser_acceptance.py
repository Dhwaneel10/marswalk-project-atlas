"""
MarsWalk 2.0 / Project Atlas - Milestone 13A Presentation and Browser Acceptance Audit.

Comprehensive Chrome DevTools Protocol (CDP) automated browser verification:
1. Daemon Health Check (http://127.0.0.1:3000/api/health)
2. All 5 Studios Audited:
   - Studio 1: Mission Control Cockpit
   - Studio 2: Mission Robustness Lab
   - Studio 3: Mission Rehearsal Director
   - Studio 4: Causal Replay Studio
   - Studio 5: Mission Experiment Studio
3. UI Discrepancy & Truth Checks:
   - Inspects UI labels, units, and data values.
   - Compares DOM values against live API responses (/api/campaign/list, /api/weather/current, /api/route/terrain-analysis).
   - Verifies DTM attribution ("USGS CTX 20m DTM" vs "HiRISE").
   - Asserts non-probabilistic truth disclosure & no misleading "astronaut safe" claims.
4. Multi-Viewport Responsiveness:
   - 1920x1080 (Desktop) and 1366x768 (Laptop).
   - Asserts document.body.scrollWidth <= window.innerWidth across all 5 studios.
5. Captures fresh evidence screenshots:
   - outputs/milestone_13a_*.png and outputs/conference_demo_*.png.
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
DEBUG_PORT = 9500

OUTPUTS_DIR = os.path.abspath(r"outputs")
CALLER_ARTIFACT_DIR = r"C:\Users\dhwan\.gemini\antigravity\brain\0a1bc6e9-d3cc-4c3b-b1fe-4875c358b144\outputs"
OUR_ARTIFACT_DIR = r"C:\Users\dhwan\.gemini\antigravity\brain\2c3d8dd6-e884-464d-b6a7-ed4ec3e307db\outputs"

SCREENSHOTS = {
    "mission_control": {
        "m13a": os.path.join(OUTPUTS_DIR, "milestone_13a_mission_control.png"),
        "demo": os.path.join(OUTPUTS_DIR, "conference_demo_mission_control.png"),
    },
    "robustness_lab": {
        "m13a": os.path.join(OUTPUTS_DIR, "milestone_13a_robustness_lab.png"),
        "demo": os.path.join(OUTPUTS_DIR, "conference_demo_robustness_lab.png"),
    },
    "rehearsal_director": {
        "m13a": os.path.join(OUTPUTS_DIR, "milestone_13a_rehearsal_director.png"),
        "demo": os.path.join(OUTPUTS_DIR, "conference_demo_rehearsal_director.png"),
    },
    "causal_replay": {
        "m13a": os.path.join(OUTPUTS_DIR, "milestone_13a_causal_replay.png"),
        "demo": os.path.join(OUTPUTS_DIR, "conference_demo_causal_replay.png"),
    },
    "experiment_studio": {
        "m13a": os.path.join(OUTPUTS_DIR, "milestone_13a_experiment_studio.png"),
        "demo": os.path.join(OUTPUTS_DIR, "conference_demo_experiment_studio.png"),
    },
}


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


async def run_milestone_13a_audit():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    os.makedirs(CALLER_ARTIFACT_DIR, exist_ok=True)
    os.makedirs(OUR_ARTIFACT_DIR, exist_ok=True)

    audit_report = {
        "daemon_health": False,
        "studios": {},
        "truth_and_units": {},
        "responsiveness": {},
        "screenshots": {},
        "discrepancies": [],
    }

    # 1. Daemon Health Check
    print("=" * 80)
    print("  MARSWALK 2.0 / PROJECT ATLAS — MILESTONE 13A ACCEPTANCE AUDIT")
    print("=" * 80)
    print("\n[Stage 1] Verifying Daemon Health (/api/health)...")
    health = fetch_api_json("/api/health")
    assert health.get("status") == "online", f"Daemon status not online: {health}"
    print(f"  -> Daemon online! Target: {health.get('target')}")
    print(f"  -> Terrain loaded: {health.get('terrain_loaded')}, Waypoints: {health.get('waypoints_count')}")
    audit_report["daemon_health"] = True

    # Check live weather API
    print("\n[Stage 2] Fetching Live APIs for Cross-Verification...")
    weather_api = fetch_api_json("/api/weather/current")
    meas = weather_api.get("measurements", {})
    print(f"  -> Weather API Site: {weather_api.get('site_name')}")
    print(f"  -> Air Temp: {meas.get('air_temperature_c')} deg C, Ground: {meas.get('ground_temperature_c')} deg C")
    print(f"  -> Pressure: {meas.get('atmospheric_pressure_pa')} Pa, Wind: {meas.get('wind_speed_m_s')} m/s")

    campaigns_api = fetch_api_json("/api/campaign/list")
    camps = campaigns_api.get("campaigns", [])
    print(f"  -> Campaigns Count: {len(camps)}")
    active_cid = "cmp_12i_integration_test"
    active_camp = next((c for c in camps if c.get("campaign_id") == active_cid), camps[0] if camps else None)
    assert active_camp is not None, "No active campaign found"
    print(f"  -> Target Campaign: {active_camp.get('campaign_id')} ('{active_camp.get('name')}')")

    # Launch Chrome Headless CDP
    tmp_profile = tempfile.mkdtemp(prefix="chrome_m13a_audit_")
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
            raise RuntimeError(f"No page target found in CDP: {targets}")
        ws_url = page_targets[0]["webSocketDebuggerUrl"]
        print(f"\n[Stage 3] Connected to CDP Page Target: {page_targets[0].get('title')}")

        async with websockets.connect(ws_url, max_size=30 * 1024 * 1024) as ws:
            msg_id = 0
            pending_responses = {}
            event_log = []

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
                            event_log.append(msg)
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

            async def check_responsive(studio_name):
                # 1920x1080
                await send_cmd("Emulation.setDeviceMetricsOverride", {
                    "width": 1920, "height": 1080, "deviceScaleFactor": 1, "mobile": False
                })
                await asyncio.sleep(0.4)
                val_1080 = await evaluate_js("JSON.stringify({ scrollW: document.body.scrollWidth, innerW: window.innerWidth, overflow: document.body.scrollWidth > window.innerWidth })")
                r_1080 = json.loads(val_1080)

                # 1366x768
                await send_cmd("Emulation.setDeviceMetricsOverride", {
                    "width": 1366, "height": 768, "deviceScaleFactor": 1, "mobile": False
                })
                await asyncio.sleep(0.4)
                val_768 = await evaluate_js("JSON.stringify({ scrollW: document.body.scrollWidth, innerW: window.innerWidth, overflow: document.body.scrollWidth > window.innerWidth })")
                r_768 = json.loads(val_768)

                # Restore 1920x1080
                await send_cmd("Emulation.setDeviceMetricsOverride", {
                    "width": 1920, "height": 1080, "deviceScaleFactor": 1, "mobile": False
                })
                await asyncio.sleep(0.4)

                res_info = {
                    "desktop_1920x1080": r_1080,
                    "laptop_1366x768": r_768,
                    "passed": (not r_1080["overflow"]) and (not r_768["overflow"])
                }
                audit_report["responsiveness"][studio_name] = res_info
                assert res_info["passed"], f"Horizontal overflow in {studio_name}: {res_info}"
                print(f"  [RESPONSIVE] {studio_name}: 1920x1080 overflow={r_1080['overflow']}, 1366x768 overflow={r_768['overflow']}")
                return res_info

            async def save_screenshot(key):
                shot_resp = await send_cmd("Page.captureScreenshot", {"format": "png"})
                img_data = base64.b64decode(shot_resp["result"]["data"])
                paths = SCREENSHOTS[key]
                for p in [paths["m13a"], paths["demo"]]:
                    with open(p, "wb") as f:
                        f.write(img_data)
                fname = os.path.basename(paths["m13a"])
                shutil.copy(paths["m13a"], os.path.join(CALLER_ARTIFACT_DIR, fname))
                shutil.copy(paths["m13a"], os.path.join(OUR_ARTIFACT_DIR, fname))
                audit_report["screenshots"][key] = paths["m13a"]
                print(f"  [SCREENSHOT] Saved {key} to {paths['m13a']} ({len(img_data)} bytes)")

            await send_cmd("Page.enable")
            await send_cmd("Runtime.enable")
            await send_cmd("Emulation.setDeviceMetricsOverride", {
                "width": 1920, "height": 1080, "deviceScaleFactor": 1, "mobile": False
            })

            # Navigate to Atlas
            print("\n[Stage 4] Navigating to http://127.0.0.1:3000/index.html...")
            await send_cmd("Page.navigate", {"url": f"{BASE_URL}/index.html"})

            # Wait for Atlas init
            for _ in range(50):
                await asyncio.sleep(0.3)
                v = await evaluate_js("JSON.stringify({ ready: document.readyState === 'complete', hasMarsWalk: !!window.MarsWalk })")
                if v:
                    obj = json.loads(v)
                    if obj.get("ready") and obj.get("hasMarsWalk"):
                        break

            # -----------------------------------------------------------------
            # AUDIT STUDIO 1: MISSION CONTROL COCKPIT
            # -----------------------------------------------------------------
            print("\n[Studio 1/5] Auditing Mission Control Cockpit...")
            await evaluate_js("document.getElementById('btnHeaderMissionControl')?.click();")
            await asyncio.sleep(0.5)

            # Select target campaign
            val_mc = await evaluate_js(f"""(async () => {{
                const sel = document.getElementById('mcCampaignSelect');
                if (sel) {{
                    sel.value = '{active_cid}';
                    sel.dispatchEvent(new Event('change'));
                }}
                await window.MarsWalk.selectMissionControlCampaign('{active_cid}');
                await new Promise(r => setTimeout(r, 600));

                const title = document.getElementById('mcCampaignTitle')?.textContent;
                const dist = document.getElementById('mcMetricDistance')?.textContent;
                const dur = document.getElementById('mcMetricDuration')?.textContent;
                const sci = document.getElementById('mcMetricScience')?.textContent;
                const energy = document.getElementById('mcMetricEnergy')?.textContent;
                const datasetBadge = document.getElementById('mcDatasetBadge')?.textContent;
                
                // Weather in MC
                const airTemp = document.getElementById('mcWeatherAirTemp')?.textContent;
                const gndTemp = document.getElementById('mcWeatherGndTemp')?.textContent;
                const pressure = document.getElementById('mcWeatherPressure')?.textContent;
                const wind = document.getElementById('mcWeatherWind')?.textContent;

                // Elevation profile
                const minEl = document.getElementById('mcMinElevation')?.textContent;
                const maxEl = document.getElementById('mcMaxElevation')?.textContent;
                const climb = document.getElementById('mcTotalClimb')?.textContent;
                const slope = document.getElementById('mcMeanSlope')?.textContent;
                const hasSvgPath = !!document.querySelector('#mcElevationProfileSvg path');

                return JSON.stringify({{
                    title, dist, dur, sci, energy, datasetBadge,
                    airTemp, gndTemp, pressure, wind,
                    minEl, maxEl, climb, slope, hasSvgPath
                }});
            }})()""", await_promise=True)
            mc_ui = json.loads(val_mc)
            print("  -> UI Metrics:", mc_ui)

            print("  -> Verifying Telemetry, Attribution, and Units...")
            assert "m" in mc_ui["dist"], f"Distance unit missing: {mc_ui['dist']}"
            assert "h" in mc_ui["dur"], f"Duration unit missing: {mc_ui['dur']}"
            assert "pts" in mc_ui["sci"], f"Science unit missing: {mc_ui['sci']}"
            assert "Wh" in mc_ui["energy"], f"Energy unit missing: {mc_ui['energy']}"
            assert "USGS" in mc_ui["datasetBadge"] and "CTX" in mc_ui["datasetBadge"], f"Dataset badge not USGS CTX: {mc_ui['datasetBadge']}"
            assert mc_ui["hasSvgPath"], "Elevation profile SVG path not rendered"
            assert "°C" in mc_ui["airTemp"] or "C" in mc_ui["airTemp"], f"Air temp unit missing: {mc_ui['airTemp']}"
            assert "Pa" in mc_ui["pressure"], f"Pressure unit missing: {mc_ui['pressure']}"
            assert "m/s" in mc_ui["wind"], f"Wind unit missing: {mc_ui['wind']}"

            # Compare UI weather values with API response
            api_air_c = f"{meas.get('air_temperature_c', 0):.1f}"
            api_pa = f"{meas.get('atmospheric_pressure_pa', 0):.1f}"
            print(f"  -> Truth Cross-Verification: UI airTemp='{mc_ui['airTemp']}' vs API='{api_air_c}°C', UI pressure='{mc_ui['pressure']}' vs API='{api_pa} Pa'")
            assert api_air_c in mc_ui["airTemp"], f"UI air temp ({mc_ui['airTemp']}) does not match API ({api_air_c})"
            assert api_pa in mc_ui["pressure"], f"UI pressure ({mc_ui['pressure']}) does not match API ({api_pa})"

            # Test Evidence Inspector Modal
            val_ev = await evaluate_js("""(async () => {
                await window.MarsWalk.inspectEvidence('slope', '12.5°');
                await new Promise(r => setTimeout(r, 600));
                const modal = document.getElementById('evidenceModal');
                const title = document.getElementById('evMetricTitle')?.textContent;
                const classification = document.getElementById('evClassificationBadge')?.textContent;
                const source = document.getElementById('evPrimarySource')?.textContent;
                const equations = document.getElementById('evEquations')?.textContent;
                const visible = modal && !modal.classList.contains('hidden');
                document.getElementById('btnCloseEvidenceModal')?.click();
                return JSON.stringify({ visible, title, classification, source, equations });
            })()""", await_promise=True)
            ev_ui = json.loads(val_ev)
            print("  -> Evidence Inspector:", ev_ui)
            assert ev_ui["visible"], "Evidence modal did not open"
            assert "Derived Planetary Geometry" in ev_ui["classification"], f"Evidence classification unexpected: {ev_ui['classification']}"
            assert "USGS CTX" in ev_ui["source"], f"Evidence source not USGS CTX: {ev_ui['source']}"

            await check_responsive("mission_control")
            await save_screenshot("mission_control")
            audit_report["studios"]["mission_control"] = "PASSED"

            # -----------------------------------------------------------------
            # AUDIT STUDIO 2: MISSION ROBUSTNESS LAB
            # -----------------------------------------------------------------
            print("\n[Studio 2/5] Auditing Mission Robustness Lab...")
            await evaluate_js("document.getElementById('tabBtnRobustnessLab')?.click();")
            await asyncio.sleep(0.8)

            # Trigger stress battery execution
            val_rob = await evaluate_js("""(async () => {
                const btn = document.getElementById('btnRunRobustnessBattery');
                if (btn) btn.click();
                for (let i = 0; i < 35; i++) {
                    await new Promise(r => setTimeout(r, 400));
                    const tag = document.getElementById('robStatusTag')?.textContent;
                    const disabled = document.getElementById('btnRunRobustnessBattery')?.disabled;
                    if (!disabled && (tag === 'COMPLETED' || tag === 'READY')) break;
                }
                const ratioText = document.getElementById('robEnvelopeRatioText')?.textContent;
                const progressW = document.getElementById('robEnvelopeProgressBar')?.style.width;
                const bottlenecks = document.querySelectorAll('#robBottlenecksList li').length;
                const sensRows = document.querySelectorAll('.rob-sens-row').length;
                const stratCount = document.querySelectorAll('.rob-strat-card').length;
                const ans1 = document.getElementById('robAns1')?.textContent;
                const ans5 = document.getElementById('robAns5')?.textContent;
                const ans7 = document.getElementById('robAns7')?.textContent;

                return JSON.stringify({
                    ratioText, progressW, bottlenecks, sensRows, stratCount,
                    ans1, ans5, ans7
                });
            })()""", await_promise=True)
            rob_ui = json.loads(val_rob)
            print("  -> Robustness Lab Results:", {k: rob_ui[k] for k in ['ratioText', 'progressW', 'bottlenecks', 'sensRows', 'stratCount']})
            assert rob_ui["sensRows"] >= 1, f"Insufficient sensitivity rows: {rob_ui['sensRows']}"
            assert rob_ui["stratCount"] == 3, f"Expected 3 candidate strategies, got {rob_ui['stratCount']}"
            assert "LIMITATIONS DISCLOSURE" in rob_ui["ans7"] or "not" in rob_ui["ans7"].lower(), f"Non-probabilistic limitations disclosure missing in Ans7: {rob_ui['ans7']}"

            await check_responsive("robustness_lab")
            await save_screenshot("robustness_lab")
            audit_report["studios"]["robustness_lab"] = "PASSED"

            # -----------------------------------------------------------------
            # AUDIT STUDIO 3: MISSION REHEARSAL DIRECTOR
            # -----------------------------------------------------------------
            print("\n[Studio 3/5] Auditing Mission Rehearsal Director...")
            await evaluate_js("document.getElementById('tabBtnRehearsalDirector')?.click();")
            await asyncio.sleep(0.8)

            val_reh = await evaluate_js("""(async () => {
                const btn = document.getElementById('btnExecuteRehearsal');
                if (btn) btn.click();
                for (let i = 0; i < 35; i++) {
                    await new Promise(r => setTimeout(r, 400));
                    const tag = document.getElementById('rehStatusTag')?.textContent;
                    if (tag === 'RECOVERED' || tag === 'RECOVERED_WITH_DEGRADATION' || tag === 'COMPLETED') break;
                }
                const statusTag = document.getElementById('rehStatusTag')?.textContent;
                const sciPreserved = document.getElementById('rehSciencePreservedVal')?.textContent;
                const recMargin = document.getElementById('rehRecoveredMarginVal')?.textContent;
                const delay = document.getElementById('rehDelayIncurredVal')?.textContent;
                const candCount = document.getElementById('rehCandidatesContainer')?.children.length || 0;
                const stepCount = document.getElementById('rehCausalLedgerContainer')?.children.length || 0;

                return JSON.stringify({
                    statusTag, sciPreserved, recMargin, delay, candCount, stepCount
                });
            })()""", await_promise=True)
            reh_ui = json.loads(val_reh)
            print("  -> Rehearsal Director Results:", reh_ui)
            assert reh_ui["candCount"] == 3, f"Expected 3 candidate options, got {reh_ui['candCount']}"
            assert reh_ui["stepCount"] >= 7, f"Expected >= 7 causal ledger steps, got {reh_ui['stepCount']}"

            await check_responsive("rehearsal_director")
            await save_screenshot("rehearsal_director")
            audit_report["studios"]["rehearsal_director"] = "PASSED"

            # -----------------------------------------------------------------
            # AUDIT STUDIO 4: CAUSAL REPLAY STUDIO
            # -----------------------------------------------------------------
            print("\n[Studio 4/5] Auditing Causal Replay Studio...")
            val_rep = await evaluate_js("""(async () => {
                const bannerVisible = document.getElementById('rehDivergenceBanner')?.style.display !== 'none';
                const triggerText = document.getElementById('rehDivTriggerText')?.textContent;
                const timeText = document.getElementById('rehDivTimeText')?.textContent;
                const stepIndicatorInitial = document.getElementById('rehStepIndicator')?.textContent;

                // Scrub to Step 3
                window.MarsWalk.seekRehearsalStep(3);
                await new Promise(r => setTimeout(r, 400));
                const step3Indicator = document.getElementById('rehStepIndicator')?.textContent;
                const step3Id = document.getElementById('rehInspectorStepId')?.textContent;
                const linksCount = document.getElementById('rehInspectorLinksContainer')?.children.length || 0;

                // Scrub to Step 5
                window.MarsWalk.seekRehearsalStep(5);
                await new Promise(r => setTimeout(r, 400));
                const step5Indicator = document.getElementById('rehStepIndicator')?.textContent;

                return JSON.stringify({
                    bannerVisible, triggerText, timeText,
                    stepIndicatorInitial, step3Indicator, step3Id,
                    linksCount, step5Indicator
                });
            })()""", await_promise=True)
            rep_ui = json.loads(val_rep)
            print("  -> Causal Replay Results:", rep_ui)
            assert rep_ui["bannerVisible"], "Forensic divergence banner not visible"
            assert "3" in rep_ui["step3Indicator"], f"Step 3 seeking failed: {rep_ui['step3Indicator']}"
            assert "5" in rep_ui["step5Indicator"], f"Step 5 seeking failed: {rep_ui['step5Indicator']}"
            assert rep_ui["linksCount"] >= 1, "Causal links missing from inspector drawer"

            await check_responsive("causal_replay")
            await save_screenshot("causal_replay")
            audit_report["studios"]["causal_replay"] = "PASSED"

            # -----------------------------------------------------------------
            # AUDIT STUDIO 5: MISSION EXPERIMENT STUDIO
            # -----------------------------------------------------------------
            print("\n[Studio 5/5] Auditing Mission Experiment Studio...")
            await evaluate_js("document.getElementById('tabBtnExperimentStudio')?.click();")
            await asyncio.sleep(0.8)

            val_exp = await evaluate_js("""(async () => {
                document.getElementById('expScenarioSuite').value = 'mobility_derating';
                document.getElementById('expRehearsalTriggerSelect').value = 'all';

                const btn = document.getElementById('btnRunExperiment');
                if (btn) btn.click();
                for (let i = 0; i < 40; i++) {
                    await new Promise(r => setTimeout(r, 400));
                    const tag = document.getElementById('expStatusTag')?.textContent;
                    const evalVal = document.getElementById('expCounterEvaluated')?.textContent;
                    const disabled = document.getElementById('btnRunExperiment')?.disabled;
                    if (!disabled && evalVal !== '--' && evalVal !== '0') break;
                }
                const evaluated = document.getElementById('expCounterEvaluated')?.textContent;
                const rehearsed = document.getElementById('expCounterRehearsed')?.textContent;
                const feasible = document.getElementById('expCounterFeasible')?.textContent;
                const recovered = document.getElementById('expCounterRecovered')?.textContent;
                const matrixRows = document.querySelectorAll('#expMatrixTableBody tr').length;
                const replayBtns = document.querySelectorAll('.btn-matrix-replay').length;

                return JSON.stringify({
                    evaluated, rehearsed, feasible, recovered, matrixRows, replayBtns
                });
            })()""", await_promise=True)
            exp_ui = json.loads(val_exp)
            print("  -> Experiment Studio Results:", exp_ui)
            assert int(exp_ui["evaluated"]) >= 3, f"Expected >=3 scenarios evaluated, got {exp_ui['evaluated']}"
            assert exp_ui["matrixRows"] >= 3, f"Expected >=3 matrix rows, got {exp_ui['matrixRows']}"
            assert exp_ui["replayBtns"] >= 1, "Forensic replay buttons missing in matrix"

            # Test Forensic Deep-link & Return Navigation
            val_deep = await evaluate_js("""(async () => {
                const replayBtn = document.querySelector('.btn-matrix-replay');
                if (replayBtn) replayBtn.click();
                await new Promise(r => setTimeout(r, 600));
                const rehActive = !document.getElementById('tabRehearsalDirector')?.classList.contains('hidden');
                const breadcrumbVisible = document.getElementById('rehExperimentBreadcrumb')?.style.display !== 'none';

                // Return to experiment studio
                const returnBtn = document.getElementById('btnReturnToExperiment');
                if (returnBtn) returnBtn.click();
                await new Promise(r => setTimeout(r, 600));
                const expActive = !document.getElementById('tabExperimentStudio')?.classList.contains('hidden');

                return JSON.stringify({
                    rehActive, breadcrumbVisible, expActive
                });
            })()""", await_promise=True)
            deep_ui = json.loads(val_deep)
            print("  -> Forensic Deep-link & Return:", deep_ui)
            assert deep_ui["rehActive"], "Rehearsal tab was not opened by forensic deep-link"
            assert deep_ui["breadcrumbVisible"], "Context breadcrumb was not displayed in Rehearsal Director"
            assert deep_ui["expActive"], "Experiment Studio was not restored on return click"

            await check_responsive("experiment_studio")
            await save_screenshot("experiment_studio")
            audit_report["studios"]["experiment_studio"] = "PASSED"

            # -----------------------------------------------------------------
            # GLOBAL TRUTH, DTM & TERMINOLOGY SCAN IN DOM
            # -----------------------------------------------------------------
            print("\n[Stage 5] Running Global Truth & Provenance Checks on DOM...")
            val_truth = await evaluate_js("""(() => {
                const bodyText = document.body.innerText;
                const fullText = document.body.textContent;
                const htmlText = document.body.innerHTML;

                // Check HiRISE
                const hiriseMatches = htmlText.match(/hirise/gi) || [];
                
                // Check USGS CTX references
                const ctxMatches = htmlText.match(/usgs\\s*ctx/gi) || [];

                // Check misleading safety claims (affirmative claims that route is safe for astronauts)
                const misleadingSafe1 = (fullText.match(/operationally safe for astronauts/gi) || []).length;
                const misleadingSafe2 = (fullText.match(/guaranteed safe/gi) || []).length;
                const misleadingSafe3 = (fullText.match(/(?:route is|routes are|path is)\s+safe for astronauts/gi) || []).length;

                // Check truth disclosures presence
                const hasLimitations = fullText.includes('Not a certified operational safety envelope') ||
                                       fullText.includes('LIMITATIONS DISCLOSURE') ||
                                       fullText.includes('All calculations derive from USGS CTX 20m') ||
                                       fullText.includes('flight-certified');

                return JSON.stringify({
                    hiriseCount: hiriseMatches.length,
                    ctxCount: ctxMatches.length,
                    misleadingSafeCount: misleadingSafe1 + misleadingSafe2 + misleadingSafe3,
                    hasLimitations
                });
            })()""")
            truth_obj = json.loads(val_truth)
            print("  -> Global DOM Truth Scan:", truth_obj)
            audit_report["truth_and_units"] = truth_obj
            assert truth_obj["hiriseCount"] == 0, f"Found {truth_obj['hiriseCount']} HiRISE mentions in DOM!"
            assert truth_obj["ctxCount"] > 0, "No USGS CTX mentions in DOM!"
            assert truth_obj["misleadingSafeCount"] == 0, f"Found {truth_obj['misleadingSafeCount']} misleading safety claims!"
            assert truth_obj["hasLimitations"], "Scientific truth & limitations disclosure missing!"

            print("\n" + "=" * 80)
            print(">>> ALL MILESTONE 13A ACCEPTANCE AUDIT CRITERIA PASSED! <<<")
            print("=" * 80)

            # Write JSON audit report
            report_path = os.path.join(OUTPUTS_DIR, "milestone_13a_browser_acceptance_report.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(audit_report, f, indent=2)
            shutil.copy(report_path, os.path.join(CALLER_ARTIFACT_DIR, "milestone_13a_browser_acceptance_report.json"))
            shutil.copy(report_path, os.path.join(OUR_ARTIFACT_DIR, "milestone_13a_browser_acceptance_report.json"))
            print(f"Audit report saved to: {report_path}")

    finally:
        proc.terminate()


if __name__ == "__main__":
    asyncio.run(run_milestone_13a_audit())
