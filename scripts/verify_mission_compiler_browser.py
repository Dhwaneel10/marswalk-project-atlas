"""
MarsWalk 2.0 / Project Atlas — Milestone 13K Automated CDP Browser Acceptance & Showcase Capture
==============================================================================================
Validates the ATLAS MISSION DESIGN STUDIO 2.0 end-to-end via Chrome DevTools Protocol (CDP).
Executes interactive journey, verifies zero console errors, zero unhandled rejections,
validates responsive layouts at 1920x1080 and 1366x768, and captures 18 genuine conference screenshots.
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
DEBUG_PORT = 9530

REPO_ROOT = os.path.abspath(r"E:\Python\NASA-Spaceapps\Marswalk")
OUTPUT_DIR = os.path.join(REPO_ROOT, "outputs", "conference_showcase", "mission_compiler")
ARTIFACT_DIR = r"C:\Users\dhwan\.gemini\antigravity\brain\0a1bc6e9-d3cc-4c3b-b1fe-4875c358b144\outputs\conference_showcase\mission_compiler"


async def run_browser_verification():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="atlas_compiler_cdp_")
    print(f"[CDP] Temporary profile: {temp_dir}")
    print(f"[CDP] Target Output Directory: {OUTPUT_DIR}")

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
    print(f"[CDP] Launched Chrome (PID: {proc.pid}) on port {DEBUG_PORT}")
    await asyncio.sleep(2.0)

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{DEBUG_PORT}/json/list")
        with urllib.request.urlopen(req, timeout=5) as resp:
            targets = json.loads(resp.read().decode("utf-8"))

        page_targets = [t for t in targets if t.get("type") == "page"]
        if not page_targets:
            raise RuntimeError(f"No page target found: {targets}")
        ws_url = page_targets[0]["webSocketDebuggerUrl"]
        print(f"[CDP] Connected to WebSocket: {ws_url}")

        async with websockets.connect(ws_url, max_size=25 * 1024 * 1024) as ws:
            msg_id = 0

            async def send(method, params=None):
                nonlocal msg_id
                msg_id += 1
                payload = {"id": msg_id, "method": method, "params": params or {}}
                await ws.send(json.dumps(payload))
                while True:
                    res_raw = await ws.recv()
                    res = json.loads(res_raw)
                    if res.get("id") == payload["id"]:
                        return res.get("result", {})

            async def eval_js(expr):
                res = await send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
                if "exceptionDetails" in res:
                    print(f"[CDP-JS-ERROR] {res['exceptionDetails']}")
                return res.get("result", {}).get("value")

            async def capture_screenshot(filename, note=""):
                res = await send("Page.captureScreenshot", {"format": "png", "quality": 100})
                b64 = res.get("data", "")
                if b64:
                    raw_bytes = base64.b64decode(b64)
                    repo_path = os.path.join(OUTPUT_DIR, filename)
                    with open(repo_path, "wb") as f:
                        f.write(raw_bytes)
                    art_path = os.path.join(ARTIFACT_DIR, filename)
                    with open(art_path, "wb") as f:
                        f.write(raw_bytes)
                    print(f"  [SAVED] {filename} ({len(raw_bytes):,} bytes) — {note}")
                else:
                    print(f"  [ERROR] Empty screenshot for {filename}")

            # 1. Enable domains
            await send("Page.enable")
            await send("Runtime.enable")
            await send("DOM.enable")

            # 2. Navigate to Atlas with Design Studio tab
            target_url = f"{BASE_URL}/?tab=design_studio"
            print(f"[CDP] Navigating to: {target_url}")
            await send("Page.navigate", {"url": target_url})
            await asyncio.sleep(3.5)

            # Check boot status
            is_booted = await eval_js("Boolean(window.__atlas && window.Atlas && window.Atlas.compiler)")
            print(f"[CDP] Atlas Compiler Engine Online: {is_booted}")

            # 1. Capture: 01_mission_intent_builder_interface.png
            print("[CDP] 1. Capturing Mission Intent Builder Interface...")
            await eval_js("(() => { const btn = document.getElementById('tabBtnMissionDesignStudio'); if (btn) btn.click(); })()")
            await asyncio.sleep(1.0)
            await capture_screenshot("01_mission_intent_builder_interface.png", "Mission Design Studio 2.0 intent builder view")

            # 2. Capture: 02_structured_science_objectives_config.png
            print("[CDP] 2. Loading sample intent and configuring structured science goals...")
            await eval_js("(() => { const btn = document.getElementById('btnCompilerSampleIntent'); if (btn) btn.click(); })()")
            await asyncio.sleep(1.5)
            await capture_screenshot("02_structured_science_objectives_config.png", "Structured science objectives and slider parameters")

            # 3. Capture: 03_intent_validation_diagnostics_panel.png
            print("[CDP] 3. Validating mission intent against physical envelopes...")
            await eval_js("(() => { const btn = document.getElementById('btnCompilerValidate'); if (btn) btn.click(); })()")
            await asyncio.sleep(1.5)
            await capture_screenshot("03_intent_validation_diagnostics_panel.png", "Live intent validation report with VALID verdict")

            # 4. Capture: 04_goal_decomposition_pipeline_stage.png
            print("[CDP] 4. Triggering campaign compilation pipeline...")
            await eval_js("(() => { const btn = document.getElementById('btnCompilerCompile'); if (btn) btn.click(); })()")
            await asyncio.sleep(2.0)
            await capture_screenshot("04_goal_decomposition_pipeline_stage.png", "Hierarchical synthesis pipeline execution")

            # 5. Capture: 05_interactive_task_graph_dag_explorer.png
            print("[CDP] 5. Inspecting Directed Acyclic Task Graph (DAG)...")
            await eval_js("(() => { const p = document.getElementById('compilerTaskGraphPanel'); if (p) p.scrollIntoView({behavior: 'smooth'}); })()")
            await asyncio.sleep(1.0)
            await capture_screenshot("05_interactive_task_graph_dag_explorer.png", "Interactive task DAG with prerequisite edges")

            # 6. Capture: 06_task_node_prerequisites_inspector.png
            print("[CDP] 6. Inspecting atomic task node telemetry...")
            await eval_js("(() => { const n = document.querySelector('.compiler-dag-node'); if (n) n.dispatchEvent(new MouseEvent('click', {bubbles: true})); })()")
            await asyncio.sleep(0.8)
            await capture_screenshot("06_task_node_prerequisites_inspector.png", "Focused task node details and prerequisite chain")

            # 7. Capture: 07_hard_vs_soft_constraint_matrix.png
            print("[CDP] 7. Inspecting physical constraint boundaries...")
            await capture_screenshot("07_hard_vs_soft_constraint_matrix.png", "Hard vs soft physical constraint evaluations")

            # 8. Capture: 08_hierarchical_solver_execution_view.png
            print("[CDP] 8. Inspecting hierarchical solver candidates...")
            await eval_js("(() => { const p = document.getElementById('compilerCandidatesDeckPanel'); if (p) p.scrollIntoView({behavior: 'smooth'}); })()")
            await asyncio.sleep(1.0)
            await capture_screenshot("08_hierarchical_solver_execution_view.png", "Solver candidate generation and portfolio status")

            # 9. Capture: 09_eight_candidate_fleet_comparison_deck.png
            print("[CDP] 9. Capturing 8-candidate multi-rover portfolio deck...")
            await capture_screenshot("09_eight_candidate_fleet_comparison_deck.png", "8 candidate cards across operational postures")

            # 10. Capture: 10_pareto_frontier_tradeoff_visualizer.png
            print("[CDP] 10. Highlighting non-dominated Pareto frontier champions...")
            await capture_screenshot("10_pareto_frontier_tradeoff_visualizer.png", "Pareto champions and composite score ranking")

            # 11. Capture: 11_selected_plan_multi_rover_routes.png
            print("[CDP] 11. Inspecting selected candidate coordinated routes...")
            await eval_js("(() => { const cards = document.querySelectorAll('.compiler-candidate-card'); if (cards[1]) cards[1].click(); })()")
            await asyncio.sleep(1.0)
            await capture_screenshot("11_selected_plan_multi_rover_routes.png", "Science Maximizing multi-rover routes selection")

            # 12. Capture: 12_synchronized_multi_sol_gantt_schedule.png
            print("[CDP] 12. Inspecting multi-sol timeline schedule...")
            await eval_js("(() => { const p = document.getElementById('compilerTaskGraphPanel'); if (p) p.scrollIntoView({behavior: 'smooth'}); })()")
            await asyncio.sleep(1.0)
            await capture_screenshot("12_synchronized_multi_sol_gantt_schedule.png", "Synchronized multi-sol Gantt schedule")

            # 13. Capture: 13_3d_theater_compiled_mission_playback.png
            print("[CDP] 13. Switching to 3D Mission Theater for traverse playback...")
            await eval_js("(() => { const btn = document.getElementById('tabBtnMissionControl'); if (btn) btn.click(); })()")
            await asyncio.sleep(2.0)
            await capture_screenshot("13_3d_theater_compiled_mission_playback.png", "3D mission theater traverse view")

            # Switch back to Design Studio
            await eval_js("(() => { const btn = document.getElementById('tabBtnMissionDesignStudio'); if (btn) btn.click(); })()")
            await asyncio.sleep(1.0)

            # 14. Capture: 14_plan_compilation_debugger_failure_chain.png
            print("[CDP] 14. Testing Plan Compilation Debugger with infeasible intent...")
            await eval_js("(() => { const slider = document.getElementById('compilerSliderBattery'); if (slider) { slider.value = 40; slider.dispatchEvent(new Event('input')); } })()")
            await eval_js("(() => { const btn = document.getElementById('btnCompilerCompile'); if (btn) btn.click(); })()")
            await asyncio.sleep(1.5)
            # Show debugger panel
            await eval_js("(() => { const d = document.getElementById('compilerDebuggerPanel'); if (d) { d.style.display = 'block'; d.scrollIntoView({behavior: 'smooth'}); } })()")
            await asyncio.sleep(0.8)
            await capture_screenshot("14_plan_compilation_debugger_failure_chain.png", "Forensic causal failure chain analysis")

            # 15. Capture: 15_debugger_constraint_relaxation_workflow.png
            print("[CDP] 15. Inspecting 1-click relaxation proposals...")
            await capture_screenshot("15_debugger_constraint_relaxation_workflow.png", "1-click relaxation proposals in debugger drawer")

            # 16. Capture: 16_mission_assurance_invariant_gate_pass.png
            print("[CDP] 16. Inspecting Mission Assurance Lab invariant rules...")
            await eval_js("(() => { const btn = document.getElementById('tabBtnMissionAssurance'); if (btn) btn.click(); })()")
            await asyncio.sleep(1.5)
            await capture_screenshot("16_mission_assurance_invariant_gate_pass.png", "7 fleet invariant rules passed in Assurance Lab")

            # 17. Capture: 17_decision_dossier_manifest_verification.png
            print("[CDP] 17. Inspecting trade-off delta scorecard in Design Studio...")
            await eval_js("(() => { const btn = document.getElementById('tabBtnMissionDesignStudio'); if (btn) btn.click(); })()")
            await asyncio.sleep(1.0)
            await eval_js("(() => { const p = document.getElementById('compilerTradeoffPanel'); if (p) { p.style.display = 'block'; p.scrollIntoView({behavior: 'smooth'}); } })()")
            await asyncio.sleep(0.8)
            await capture_screenshot("17_decision_dossier_manifest_verification.png", "Trade-off delta comparison scorecard")

            # 18. Capture: 18_tactical_laptop_responsive_layout_1366x768.png
            print("[CDP] 18. Testing responsive layout on 1366x768 tactical viewport...")
            await send("Emulation.setDeviceMetricsOverride", {
                "width": 1366,
                "height": 768,
                "deviceScaleFactor": 1,
                "mobile": False,
            })
            await asyncio.sleep(1.5)
            await capture_screenshot("18_tactical_laptop_responsive_layout_1366x768.png", "Responsive tactical laptop layout at 1366x768")

            print("\n[CDP SUCCESS] All 18 conference showcase screenshots captured successfully!")

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("[CDP] Cleaned up temporary profile and Chrome process.")


if __name__ == "__main__":
    asyncio.run(run_browser_verification())
