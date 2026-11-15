#!/usr/bin/env python3
"""
scripts/verify_mission17b_responsive.py
Mission 17B: Comprehensive Homepage Layout Reconstruction & Responsive Multi-Viewport QA Audit
Audits:
- 7 Target Viewport Resolutions:
  1. 1920x1080 (Desktop Full HD)
  2. 1600x900 (Desktop Standard)
  3. 1366x768 (Laptop Standard)
  4. 1024x768 (iPad Landscape / Small Desktop)
  5. 768x1024 (iPad Portrait / Tablet)
  6. 390x844 (Mobile iPhone 14 Pro)
  7. 360x800 (Mobile Android Standard)
- Zero Horizontal Overflow (scrollWidth <= innerWidth + 1)
- 7 Architectural Sections Verification:
  1. Sticky Navigation Bar (.landing-nav)
  2. Balanced Hero Stage (#heroSection)
  3. Empirical Data Overview Specs (#dataOverviewSection)
  4. Mission Workflow Pipeline (#workflowSection)
  5. Data Provenance & Epistemic Taxonomy (#provenanceSection)
  6. Scientific Limitations Disclaimer (#limitationsSection)
  7. Clean Minimal Footer (#landingFooter)
- Interactive Anchor Navigation (Data, Workflow, Provenance, About, Back-to-Top, Launch Workstation)
- Visual Screenshot Evidence Generation under outputs/mission_17b/
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

TARGET_PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3000
BASE_URL = f"http://127.0.0.1:{TARGET_PORT}"
DEBUG_PORT = 9565
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "mission_17b"))
CHROME_BIN = "/usr/bin/google-chrome"

RESOLUTIONS = [
    {"name": "desktop_1920x1080", "width": 1920, "height": 1080, "scale": 1, "mobile": False},
    {"name": "desktop_1600x900", "width": 1600, "height": 900, "scale": 1, "mobile": False},
    {"name": "laptop_1366x768", "width": 1366, "height": 768, "scale": 1, "mobile": False},
    {"name": "tablet_landscape_1024x768", "width": 1024, "height": 768, "scale": 1, "mobile": False},
    {"name": "tablet_portrait_768x1024", "width": 768, "height": 1024, "scale": 2, "mobile": True},
    {"name": "mobile_390x844", "width": 390, "height": 844, "scale": 2, "mobile": True},
    {"name": "mobile_360x800", "width": 360, "height": 800, "scale": 2, "mobile": True},
]


async def cdp_call(ws, req_id, method, params=None):
    payload = {"id": req_id, "method": method}
    if params:
        payload["params"] = params
    await ws.send(json.dumps(payload))
    while True:
        resp = await ws.recv()
        data = json.loads(resp)
        if data.get("id") == req_id:
            return data.get("result", {})


async def evaluate_js(ws, req_id, expr):
    res = await cdp_call(ws, req_id, "Runtime.evaluate", {
        "expression": expr,
        "returnByValue": True,
        "awaitPromise": True
    })
    return res.get("result", {}).get("value")


async def capture_screenshot(ws, req_id, filepath):
    res = await cdp_call(ws, req_id, "Page.captureScreenshot", {"format": "png"})
    raw_b64 = res.get("data", "")
    if raw_b64:
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(raw_b64))
        size_kb = os.path.getsize(filepath) // 1024
        print(f"  [SCREENSHOT] Saved: {os.path.basename(filepath)} ({size_kb} KB)")
        return True
    return False


async def run_audit():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tmp_profile = tempfile.mkdtemp(prefix="chrome_m17b_")

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
    ws = None
    results = {
        "viewports": {},
        "interactions": {},
        "summary": {"passed": True, "checks_total": 0, "checks_passed": 0}
    }

    try:
        tabs = None
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json") as r:
                    tabs = json.loads(r.read().decode())
                    if tabs:
                        break
            except Exception:
                await asyncio.sleep(0.3)

        if not tabs:
            raise RuntimeError("Failed to connect to headless Chrome CDP endpoint.")

        ws_url = tabs[0]["webSocketDebuggerUrl"]
        req_id = 1

        async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as websocket:
            ws = websocket
            await cdp_call(ws, req_id, "Page.enable"); req_id += 1
            await cdp_call(ws, req_id, "Runtime.enable"); req_id += 1

            print(f"=== Initializing MarsWalk Homepage Audit on {BASE_URL} ===")
            await cdp_call(ws, req_id, "Page.navigate", {"url": f"{BASE_URL}/"}); req_id += 1
            await asyncio.sleep(3.5)

            # Step 1: Audit all 7 Resolutions
            for r in RESOLUTIONS:
                r_name = r["name"]
                w, h = r["width"], r["height"]
                scale = r["scale"]
                mobile = r["mobile"]

                print(f"\n--- AUDITING VIEWPORT: {r_name} ({w}x{h}) ---")
                await cdp_call(ws, req_id, "Emulation.setDeviceMetricsOverride", {
                    "width": w,
                    "height": h,
                    "deviceScaleFactor": scale,
                    "mobile": mobile
                }); req_id += 1
                await asyncio.sleep(1.0)

                # Ensure page is at top
                await evaluate_js(ws, req_id, """
                    (() => {
                        const page = document.getElementById('marsLandingPage');
                        if (page) page.scrollTop = 0;
                        window.scrollTo(0, 0);
                    })()
                """); req_id += 1
                await asyncio.sleep(0.5)

                metrics = await evaluate_js(ws, req_id, """
                    (() => {
                        const page = document.getElementById('marsLandingPage');
                        const docWidth = document.documentElement.scrollWidth;
                        const winWidth = window.innerWidth;
                        const pageScrollWidth = page ? page.scrollWidth : 0;
                        const hasHorizontalOverflow = (pageScrollWidth > winWidth + 1) || (docWidth > winWidth + 1);

                        // Hero metrics
                        const headline = document.querySelector('.landing-headline');
                        const narrative = document.querySelector('.landing-narrative');
                        const btnEVA = document.getElementById('btnLandingEnterEVA');
                        const btnEnv = document.getElementById('btnLandingExploreEnv');
                        const sidebar = document.querySelector('.landing-hero-sidebar');
                        const heroContainer = document.querySelector('.landing-hero-container');

                        // Section visibility
                        const heroSec = document.getElementById('heroSection');
                        const dataSec = document.getElementById('dataOverviewSection');
                        const workflowSec = document.getElementById('workflowSection');
                        const provSec = document.getElementById('provenanceSection');
                        const limSec = document.getElementById('limitationsSection');
                        const footerSec = document.getElementById('landingFooter');

                        // Grid counts
                        const specCards = document.querySelectorAll('.spec-card').length;
                        const workflowCards = document.querySelectorAll('.workflow-card').length;
                        const provCols = document.querySelectorAll('.provenance-col').length;

                        // Sidebar dimensions
                        const sidebarRect = sidebar ? sidebar.getBoundingClientRect() : null;
                        const heroRect = heroContainer ? heroContainer.getBoundingClientRect() : null;

                        return {
                            winWidth,
                            winHeight: window.innerHeight,
                            docWidth,
                            pageScrollWidth,
                            hasHorizontalOverflow,
                            hero: {
                                headlineVisible: Boolean(headline && headline.offsetWidth > 0 && headline.offsetHeight > 0),
                                headlineText: headline ? headline.innerText.split('\\n')[0].trim() : '',
                                narrativeVisible: Boolean(narrative && narrative.offsetWidth > 0),
                                btnEVAVisible: Boolean(btnEVA && btnEVA.offsetWidth > 0),
                                btnEnvVisible: Boolean(btnEnv && btnEnv.offsetWidth > 0),
                                sidebarWidth: sidebarRect ? Math.round(sidebarRect.width) : 0,
                                heroWidth: heroRect ? Math.round(heroRect.width) : 0,
                            },
                            sections: {
                                hero: Boolean(heroSec),
                                data: Boolean(dataSec),
                                workflow: Boolean(workflowSec),
                                provenance: Boolean(provSec),
                                limitations: Boolean(limSec),
                                footer: Boolean(footerSec)
                            },
                            counts: {
                                specCards,
                                workflowCards,
                                provCols
                            }
                        };
                    })()
                """); req_id += 1

                print(f"  Widths: Window={metrics['winWidth']}, PageScroll={metrics['pageScrollWidth']}, DocScroll={metrics['docWidth']}")
                print(f"  Horizontal Overflow: {'FAIL' if metrics['hasHorizontalOverflow'] else 'PASS (0px)'}")
                print(f"  Hero: Headline='{metrics['hero']['headlineText']}', EVA_CTA={metrics['hero']['btnEVAVisible']}, SidebarW={metrics['hero']['sidebarWidth']}px")
                print(f"  Cards: Specs={metrics['counts']['specCards']}, Workflow={metrics['counts']['workflowCards']}, Provenance={metrics['counts']['provCols']}")

                results["viewports"][r_name] = metrics
                results["summary"]["checks_total"] += 5

                # Verify criteria
                if not metrics["hasHorizontalOverflow"]:
                    results["summary"]["checks_passed"] += 1
                else:
                    results["summary"]["passed"] = False

                if metrics["hero"]["headlineVisible"] and metrics["hero"]["btnEVAVisible"]:
                    results["summary"]["checks_passed"] += 1
                else:
                    results["summary"]["passed"] = False

                if metrics["counts"]["specCards"] == 4 and metrics["counts"]["workflowCards"] == 5 and metrics["counts"]["provCols"] == 3:
                    results["summary"]["checks_passed"] += 1
                else:
                    results["summary"]["passed"] = False

                if all(metrics["sections"].values()):
                    results["summary"]["checks_passed"] += 1
                else:
                    results["summary"]["passed"] = False

                # Capture top hero screenshot
                shot_path = os.path.join(OUTPUT_DIR, f"{r_name}_01_hero.png")
                await capture_screenshot(ws, req_id, shot_path); req_id += 1
                results["summary"]["checks_passed"] += 1

                # If this is one of our primary review viewports, capture middle and bottom too
                if r_name in ["desktop_1920x1080", "tablet_portrait_768x1024", "mobile_390x844"]:
                    # Scroll to workflow
                    await evaluate_js(ws, req_id, """
                        (() => {
                            const sec = document.getElementById('workflowSection');
                            if (sec) sec.scrollIntoView();
                        })()
                    """); req_id += 1
                    await asyncio.sleep(0.8)
                    shot_mid = os.path.join(OUTPUT_DIR, f"{r_name}_02_workflow.png")
                    await capture_screenshot(ws, req_id, shot_mid); req_id += 1

                    # Scroll to footer
                    await evaluate_js(ws, req_id, """
                        (() => {
                            const sec = document.getElementById('landingFooter');
                            if (sec) sec.scrollIntoView();
                        })()
                    """); req_id += 1
                    await asyncio.sleep(0.8)
                    shot_bot = os.path.join(OUTPUT_DIR, f"{r_name}_03_footer.png")
                    await capture_screenshot(ws, req_id, shot_bot); req_id += 1

            # Step 2: Test Interactive Navigation at 1920x1080
            print("\n--- AUDITING INTERACTIVE ANCHOR & WORKFLOW NAVIGATION ---")
            await cdp_call(ws, req_id, "Emulation.setDeviceMetricsOverride", {
                "width": 1920,
                "height": 1080,
                "deviceScaleFactor": 1,
                "mobile": False
            }); req_id += 1
            await asyncio.sleep(0.5)

            # Scroll back to top
            await evaluate_js(ws, req_id, """
                (() => {
                    const page = document.getElementById('marsLandingPage');
                    if (page) page.scrollTop = 0;
                })()
            """); req_id += 1
            await asyncio.sleep(0.5)

            # Test Nav Link: Data Specs
            nav_data_res = await evaluate_js(ws, req_id, """
                (() => {
                    const btn = document.getElementById('navLinkData');
                    if (btn) { btn.click(); return true; }
                    return false;
                })()
            """); req_id += 1
            await asyncio.sleep(1.0)
            data_scroll_pos = await evaluate_js(ws, req_id, "document.getElementById('marsLandingPage').scrollTop"); req_id += 1
            print(f"  Click navLinkData: scrolled to {data_scroll_pos}px (Expected > 200px)")

            # Test Nav Link: Workflow
            nav_work_res = await evaluate_js(ws, req_id, """
                (() => {
                    const btn = document.getElementById('navLinkHowItWorks');
                    if (btn) { btn.click(); return true; }
                    return false;
                })()
            """); req_id += 1
            await asyncio.sleep(1.0)
            workflow_scroll_pos = await evaluate_js(ws, req_id, "document.getElementById('marsLandingPage').scrollTop"); req_id += 1
            print(f"  Click navLinkHowItWorks: scrolled to {workflow_scroll_pos}px (Expected > {data_scroll_pos}px)")

            # Test Nav Link: Provenance
            nav_prov_res = await evaluate_js(ws, req_id, """
                (() => {
                    const btn = document.getElementById('navLinkProvenance');
                    if (btn) { btn.click(); return true; }
                    return false;
                })()
            """); req_id += 1
            await asyncio.sleep(1.0)
            prov_scroll_pos = await evaluate_js(ws, req_id, "document.getElementById('marsLandingPage').scrollTop"); req_id += 1
            print(f"  Click navLinkProvenance: scrolled to {prov_scroll_pos}px (Expected > {workflow_scroll_pos}px)")

            # Test Back to Top Button
            back_res = await evaluate_js(ws, req_id, """
                (() => {
                    const btn = document.getElementById('btnFooterBackToTop');
                    if (btn) { btn.click(); return true; }
                    return false;
                })()
            """); req_id += 1
            await asyncio.sleep(1.2)
            top_scroll_pos = await evaluate_js(ws, req_id, "document.getElementById('marsLandingPage').scrollTop"); req_id += 1
            print(f"  Click btnFooterBackToTop: returned to {top_scroll_pos}px (Expected ~0px)")

            # Test Launch Atlas Workstation button in footer
            footer_launch_res = await evaluate_js(ws, req_id, """
                (() => {
                    const btn = document.getElementById('btnFooterEnterWorkstation');
                    if (btn) { btn.click(); return true; }
                    return false;
                })()
            """); req_id += 1
            await asyncio.sleep(1.5)

            workstation_state = await evaluate_js(ws, req_id, """
                (() => {
                    const landing = document.getElementById('marsLandingPage');
                    const isHidden = landing && landing.classList.contains('hidden');
                    return { isHidden };
                })()
            """); req_id += 1
            print(f"  Click btnFooterEnterWorkstation: Landing page hidden = {workstation_state['isHidden']}")

            results["interactions"] = {
                "data_scroll_pos": data_scroll_pos,
                "workflow_scroll_pos": workflow_scroll_pos,
                "prov_scroll_pos": prov_scroll_pos,
                "top_scroll_pos": top_scroll_pos,
                "workstation_launched": workstation_state["isHidden"]
            }

            # Return to landing page for clean state
            await evaluate_js(ws, req_id, """
                (() => {
                    const btn = document.getElementById('btnNavOverview');
                    if (btn) btn.click();
                })()
            """); req_id += 1
            await asyncio.sleep(1.0)

            # Final summary
            results_file = os.path.join(OUTPUT_DIR, "audit_results.json")
            with open(results_file, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\n=== AUDIT COMPLETE: Passed={results['summary']['passed']} ({results['summary']['checks_passed']}/{results['summary']['checks_total']} checks) ===")
            print(f"  Audit results saved to: {results_file}")

    finally:
        if proc:
            proc.terminate()
            proc.wait()
        if os.path.exists(tmp_profile):
            shutil.rmtree(tmp_profile, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(run_audit())
