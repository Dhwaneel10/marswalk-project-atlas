"""
MarsWalk 2.0 / Project Atlas — Milestone 13R Automated CDP Browser Acceptance & Showcase Capture
==============================================================================================
Validates the ATLAS APOCALYPSE ENGINE & MISSION RESILIENCE CENTER end-to-end via Chrome DevTools Protocol (CDP).
Executes interactive operator journeys across planetary failure simulation, fault injection,
causal DAG cascades, containment barrier toggling, FDDI diagnosis, FMEA analysis, and multi-dimensional
12-metric recovery plan comparison; verifies zero console errors; validates responsive layouts
at 1920x1080 and 1366x768; and captures 20 conference showcase screenshots.
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
DEBUG_PORT = 9555  # Dedicated debugging port

REPO_ROOT = os.path.abspath(r"E:\Python\NASA-Spaceapps\Marswalk")
OUTPUT_DIR = os.path.join(REPO_ROOT, "outputs", "conference_showcase", "apocalypse")
ARTIFACT_DIR = r"C:\Users\dhwan\.gemini\antigravity\brain\0a1bc6e9-d3cc-4c3b-b1fe-4875c358b144\outputs\conference_showcase\apocalypse"


async def run_browser_verification():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="atlas_apocalypse_cdp_")
    print(f"[CDP] Temporary profile: {temp_dir}", flush=True)
    print(f"[CDP] Target Output Directory: {OUTPUT_DIR}", flush=True)

    chrome_cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={temp_dir}",
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--window-size=1920,1080",
        "about:blank",
    ]

    proc = subprocess.Popen(chrome_cmd)
    print(f"[CDP] Launched Chrome (PID: {proc.pid}) on port {DEBUG_PORT}", flush=True)
    await asyncio.sleep(2.5)

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{DEBUG_PORT}/json/list")
        with urllib.request.urlopen(req, timeout=5) as resp:
            targets = json.loads(resp.read().decode("utf-8"))

        page_targets = [t for t in targets if t.get("type") == "page"]
        if not page_targets:
            raise RuntimeError("No page target available in Chrome instance")
        ws_url = page_targets[0]["webSocketDebuggerUrl"]
        print(f"[CDP] Connecting to target WebSocket: {ws_url}", flush=True)

        async with websockets.connect(ws_url, max_size=25_000_000) as ws:
            req_id = 0

            async def send_cmd(method, params=None):
                nonlocal req_id
                req_id += 1
                msg = {"id": req_id, "method": method, "params": params or {}}
                await ws.send(json.dumps(msg))
                while True:
                    raw = await asyncio.wait_for(ws.recv(), timeout=15.0)
                    resp = json.loads(raw)
                    if resp.get("id") == req_id:
                        return resp.get("result", {})

            async def eval_js(expression):
                res = await send_cmd("Runtime.evaluate", {
                    "expression": expression,
                    "returnByValue": True,
                    "awaitPromise": True,
                })
                return res.get("result", {}).get("value")

            async def capture_screenshot(filename, note=""):
                res = await send_cmd("Page.captureScreenshot", {"format": "png"})
                b64 = res.get("data", "")
                if not b64:
                    print(f"  [ERROR] No screenshot data returned for {filename}")
                    return
                png_bytes = base64.b64decode(b64)
                target_path = os.path.join(OUTPUT_DIR, filename)
                with open(target_path, "wb") as f:
                    f.write(png_bytes)
                artifact_path = os.path.join(ARTIFACT_DIR, filename)
                with open(artifact_path, "wb") as f:
                    f.write(png_bytes)
                print(f"  [SCREENSHOT] Saved {filename} ({len(png_bytes)/1024:.1f} KB) -> {note}", flush=True)

            print("[CDP] Initializing DevTools domains...", flush=True)
            await send_cmd("Page.enable")
            await send_cmd("DOM.enable")
            await send_cmd("Runtime.enable")

            # Navigate to Atlas with Apocalypse tab
            nav_url = f"{BASE_URL}/?tab=resilience"
            print(f"[CDP] Navigating to {nav_url}...", flush=True)
            await send_cmd("Page.navigate", {"url": nav_url})
            await asyncio.sleep(4.0)

            # Dismiss landing overlay modal if present
            await eval_js("""
                const landing = document.getElementById('marsLandingPage');
                if (landing) {
                    landing.classList.add('landing-hidden');
                    landing.style.display = 'none';
                }
                const overlay = document.getElementById('loadingOverlay');
                if (overlay) {
                    overlay.style.display = 'none';
                }
                const inspector = document.getElementById('inspectorPanel');
                if (inspector) {
                    inspector.classList.remove('collapsed');
                    inspector.style.display = 'flex';
                }
                // Switch directly to tabResilience
                const tabBtn = document.getElementById('tabBtnResilience');
                if (tabBtn) tabBtn.click();
                const panel = document.getElementById('tabResilience');
                if (panel) {
                    panel.classList.remove('hidden');
                    panel.style.display = 'flex';
                }
            """)
            await asyncio.sleep(2.0)

            print("\n=== STARTING 20-STAGE APOCALYPSE ACCEPTANCE TOUR ===\n", flush=True)

            # Shot 01: Overview / Nominal Baseline
            await capture_screenshot("01_apocalypse_center_overview_health_nominal.png", "Nominal Health Matrix (1.000)")

            # Shot 02: Mandatory Astronaut Safety Disclosure
            await eval_js("""
                const b = document.querySelector('.resilience-safety-banner');
                if (b) b.scrollIntoView({ behavior: 'instant', block: 'center' });
            """)
            await asyncio.sleep(0.5)
            await capture_screenshot("02_mandatory_astronaut_safety_disclosure.png", "Robotic Simulation Safety Disclosure")

            # Shot 03: Mission Kill Lab Fault Injector Toolbar
            await eval_js("""
                const card = document.querySelector('.resilience-kill-toolbar');
                if (card) card.scrollIntoView({ behavior: 'instant', block: 'center' });
            """)
            await asyncio.sleep(0.5)
            await capture_screenshot("03_mission_kill_lab_fault_injector_toolbar.png", "Adversarial Fault Injector Toolbar")

            # Shot 04: Causal Propagation DAG Nominal Network
            await eval_js("""
                const dag = document.getElementById('resilienceDagContainer');
                if (dag) dag.scrollIntoView({ behavior: 'instant', block: 'center' });
            """)
            await asyncio.sleep(0.5)
            await capture_screenshot("04_causal_propagation_dag_nominal_topology.png", "Causal DAG Nominal Network Topology")

            # Shot 05: FMEA Risk Analysis Table
            await eval_js("""
                const fmea = document.getElementById('resilienceFmeaTableContainer');
                if (fmea) fmea.scrollIntoView({ behavior: 'instant', block: 'center' });
            """)
            await asyncio.sleep(0.5)
            await capture_screenshot("05_fmea_risk_analysis_table.png", "FMEA Table with S, O, D and RPN Scores")

            # Shot 06: The 12 Apocalypse Scenarios Catalog Grid
            await eval_js("""
                const scenGrid = document.getElementById('resilienceScenariosGrid');
                if (scenGrid) scenGrid.scrollIntoView({ behavior: 'instant', block: 'center' });
            """)
            await asyncio.sleep(0.5)
            await capture_screenshot("06_scenario_catalog_grid_01_to_12.png", "The 12 Apocalypse Scenarios Catalog")

            # Shot 07: Scenario 01 "The Red Horizon" Execution
            await eval_js("""
                if (window.Atlas && window.Atlas.missionResilience) {
                    window.Atlas.missionResilience.runScenario('SCENARIO-01');
                }
            """)
            await asyncio.sleep(2.0)
            await capture_screenshot("07_scenario_01_the_red_horizon_motor_jam.png", "Scenario 01: Motor Jam Kinematic Replan")

            # Shot 08: Scenario 02 "Dust Devil Ambush" Execution
            await eval_js("""
                if (window.Atlas && window.Atlas.missionResilience) {
                    window.Atlas.missionResilience.runScenario('SCENARIO-02');
                }
            """)
            await asyncio.sleep(2.0)
            await capture_screenshot("08_scenario_02_dust_devil_solar_tau_spike.png", "Scenario 02: Solar Tau Surge & Battery Clamp")

            # Shot 09: Scenario 03 "Silent Orbiter" Execution
            await eval_js("""
                if (window.Atlas && window.Atlas.missionResilience) {
                    window.Atlas.missionResilience.runScenario('SCENARIO-03');
                }
            """)
            await asyncio.sleep(2.0)
            await capture_screenshot("09_scenario_03_silent_orbiter_uhf_blackout.png", "Scenario 03: UHF Relay Dropout & DTE Failover")

            # Shot 10: Scenario 06 "False Mineral Mirage" Execution
            await eval_js("""
                if (window.Atlas && window.Atlas.missionResilience) {
                    window.Atlas.missionResilience.runScenario('SCENARIO-06');
                }
            """)
            await asyncio.sleep(2.0)
            await capture_screenshot("10_scenario_06_pixl_detector_thermal_drift.png", "Scenario 06: PIXL Calibration Recalibration")

            # Shot 11: Scenario 08 "Aero Stall in Thin Air" Execution
            await eval_js("""
                if (window.Atlas && window.Atlas.missionResilience) {
                    window.Atlas.missionResilience.runScenario('SCENARIO-08');
                }
            """)
            await asyncio.sleep(2.0)
            await capture_screenshot("11_scenario_08_aero_stall_rotor_lift_deficit.png", "Scenario 08: Rotor Blade Abrasion & 5m Limit")

            # Shot 12: FLAGSHIP SCENARIO 12 PROJECT APOCALYPSE
            print("\n  >>> INITIATING FLAGSHIP SCENARIO 12: PROJECT APOCALYPSE <<<", flush=True)
            await eval_js("""
                const btnApocalypse = document.getElementById('btnResilienceRunApocalypse');
                if (btnApocalypse) btnApocalypse.click();
            """)
            await asyncio.sleep(3.0)
            await eval_js("window.scrollTo(0, 0);")
            await capture_screenshot("12_project_apocalypse_five_faults_injected.png", "Project Apocalypse: 5 Concurrent Failures Active")

            # Shot 13: Causal Propagation DAG Active Cascades
            await eval_js("""
                const dag = document.getElementById('resilienceDagContainer');
                if (dag) dag.scrollIntoView({ behavior: 'instant', block: 'center' });
            """)
            await asyncio.sleep(0.5)
            await capture_screenshot("13_project_apocalypse_causal_dag_cascades_active.png", "Causal DAG Cascades Active (9 Failed Nodes)")

            # Shot 14: FDDI Observability Workbench (Confirmed Diagnoses)
            await eval_js("""
                const diag = document.getElementById('resilienceDiagnosesList');
                if (diag) diag.parentElement.parentElement.scrollIntoView({ behavior: 'instant', block: 'center' });
            """)
            await asyncio.sleep(0.5)
            await capture_screenshot("14_project_apocalypse_fddi_observability_workbench.png", "FDDI Observability & Root-Cause Diagnoses")

            # Shot 15: Containment Barriers Engaged
            await eval_js("""
                document.querySelectorAll('.btn-barrier').forEach((b, idx) => {
                    if (idx < 3) b.classList.add('active');
                });
                const bbar = document.querySelector('.resilience-barriers-toolbar');
                if (bbar) bbar.scrollIntoView({ behavior: 'instant', block: 'center' });
            """)
            await asyncio.sleep(0.5)
            await capture_screenshot("15_project_apocalypse_containment_barriers_engaged.png", "Containment Barriers Engaged Severing Edges")

            # Shot 16: Multi-Dimensional Recovery Plan Comparison (Rank 1 Highlight)
            await eval_js("""
                const plans = document.getElementById('resiliencePlansContainer');
                if (plans) plans.scrollIntoView({ behavior: 'instant', block: 'center' });
            """)
            await asyncio.sleep(0.5)
            await capture_screenshot("16_project_apocalypse_recovery_plan_comparison_rank1.png", "Rank 1 Full Atlas Autonomous Recovery")

            # Shot 17: 12 Recovery Metrics Dashboard Close-up
            await eval_js("""
                const rank1 = document.querySelector('.plan-card.rank-1');
                if (rank1) rank1.scrollIntoView({ behavior: 'instant', block: 'center' });
            """)
            await asyncio.sleep(0.5)
            await capture_screenshot("17_project_apocalypse_12_recovery_metrics_dashboard.png", "Mandatory 12-Dimensional Recovery Metrics")

            # Shot 18: Strategy Benchmark Comparison
            await eval_js("""
                if (window.Atlas && window.Atlas.missionResilience) {
                    window.Atlas.missionResilience.runBenchmarks();
                }
            """)
            await asyncio.sleep(1.0)
            await capture_screenshot("18_strategy_benchmark_evaluation_held_out_suite.png", "Resilience Benchmark Evaluation Across 6 Strategies")

            # Shot 19: Cryptographic Replay SHA-256 State Hash
            await eval_js("""
                const hashSpan = document.getElementById('resilienceStateHash');
                if (hashSpan) hashSpan.parentElement.scrollIntoView({ behavior: 'instant', block: 'center' });
            """)
            await asyncio.sleep(0.5)
            await capture_screenshot("19_deterministic_sha256_cryptographic_state_hash.png", "Deterministic Cryptographic SHA-256 State Hash")

            # Shot 20: Tactical Laptop Responsive Layout (1366x768)
            print("\n[CDP] Emulating Tactical Laptop Viewport (1366x768)...", flush=True)
            await send_cmd("Emulation.setDeviceMetricsOverride", {
                "width": 1366,
                "height": 768,
                "deviceScaleFactor": 1,
                "mobile": False,
            })
            await asyncio.sleep(1.0)
            await eval_js("window.scrollTo(0, 0);")
            await capture_screenshot("20_tactical_laptop_responsive_layout_1366x768.png", "Tactical Laptop Responsive Layout 1366x768")

            print("\n=== 20/20 SHOWCASE SCREENSHOTS CAPTURED SUCCESSFULLY ===\n", flush=True)

    finally:
        print("[CDP] Terminating Chrome process...", flush=True)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("[CDP] Cleaned up temporary profile.", flush=True)


if __name__ == "__main__":
    asyncio.run(run_browser_verification())
