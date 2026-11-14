# Mission 10 — Defect Register & Remediation Log

**Project:** MarsWalk 2.0 / Project Atlas  
**Audit Sprint:** Mission 10 — Independent Technical Validation & Release Acceptance  
**Workspace:** `/home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission`  
**Date:** November 14, 2026  
**Auditor:** Independent Technical Verification Engineer (Mission 10)  

---

## 1. Defect Classification Severity Matrix

| Severity | Definition | Action Required |
|---|---|---|
| **CRITICAL** | Total system failure, corrupted scientific calculation, false data claim, or crash. | Immediate blocker; release rejected until fixed. |
| **HIGH** | Test suite breakage, environment incompatibility, unhandled 500 error, or broken pipeline. | Mandatory fix prior to release candidate sign-off. |
| **MEDIUM** | Performance constraint breach, unexpected latency, or flaky test assertions. | Remediated and verified in regression suite. |
| **LOW** | Deprecation notices, UI element mismatches, code styling, or package bloat. | Remediated for release hygiene and packaging polish. |

---

## 2. Complete Defect Register

### Defect MW-M10-DEF-01: UI Landing Page Slogan & CTA Button Regression
- **Severity:** LOW (UI Presentation Regression)
- **Component:** `web/index.html`, `tests/test_milestone_9l_design.py`
- **Symptom:** `test_milestone_9l_design.py::test_index_html_landing_page_structure` failed with `AssertionError: assert 'A NEW WORLD.' in html` and `assert 'id="btnLandingHowItWorks"' in html`.
- **Root Cause:** Modernization of the hero banner in Mission 7 had consolidated button elements, accidentally omitting the secondary architectural CTA button and the original milestone subtitle.
- **Remediation:**
  1. Restored `<span style="...">A NEW WORLD. WITHIN REACH.</span>` inside the landing hero headline block.
  2. Restored `<button id="btnLandingHowItWorks" class="btn-hero-secondary"><span>How It Works</span></button>` in `.landing-cta-row`. The click handler in `web/app.js` already existed to toggle and smooth-scroll to `#landingHowItWorksSection`.
- **Verification:** `tests/test_milestone_9l_design.py` passed 4/4 in 0.07s.

---

### Defect MW-M10-DEF-02: Route Optimizer Latency Threshold Exceeded
- **Severity:** MEDIUM (Performance & Test Assertion)
- **Component:** `src/marswalk/core/planner.py`, `src/marswalk/core/terrain.py`, `tests/test_milestone_9v_mission_optimizer.py`
- **Symptom:** `test_milestone_9v_mission_optimizer.py::test_live_http_api_optimization` failed with `AssertionError: assert 2707.6 < 2500.0`.
- **Root Cause:** Pairwise leg caching computes 12 directed A* searches on the $250 \times 250$ Jezero grid. Inside `astar_search`, `math.hypot` was being recomputed twice per neighbor, and `generalized_octile_heuristic` was calculating `math.sqrt(dx**2 + dy**2)` on every open set heap push.
- **Remediation:**
  1. Precomputed neighbor ground distances (`dx`, `dy`, `d_diag`) in `astar_search`.
  2. Enhanced `calculate_edge_cost()` with an optional `step_dist` parameter to avoid recomputing Euclidean distances and boundary limits.
  3. Precomputed $d_{\text{diag}}$ passed into `generalized_octile_heuristic()` to eliminate redundant square roots.
- **Result:** Route optimization latency dropped from **2,707.6 ms to 1,925.3 ms (28.9% reduction)**, comfortably below the 2,500.0 ms threshold.
- **Verification:** `tests/test_milestone_9v_mission_optimizer.py` passed 14/14 in 35.73s.

---

### Defect MW-M10-DEF-03: Matrix Multiplication Deprecation Warnings in Affine/Rasterio
- **Severity:** LOW (Code Quality & Deprecation)
- **Component:** `src/marswalk/api/service.py`, `src/marswalk/core/campaign_simulator.py`
- **Symptom:** 10 occurrences of `PendingDeprecationWarning: Use @ matmul instead of * mul operator for matrix multiplication` emitted during pytest runs.
- **Root Cause:** In modern `affine` (v3.0+) and `rasterio`, coordinate transforms use the Python matrix multiplication operator `@` rather than `*`.
- **Remediation:** Updated `inv_ctx * (x, y)` -> `inv_ctx @ (x, y)` at lines 10809, 10824, 11135 in `service.py` and line 361 in `campaign_simulator.py`.
- **Verification:** Zero deprecation warnings in full regression Run 2 (1,288 passed, 0 warnings).

---

### Defect MW-M10-DEF-04: ROS Humble Plugin Entrypoint Collision on Ubuntu 22.04 LTS
- **Severity:** HIGH (Host Environment Compatibility)
- **Component:** `pyproject.toml`, `scripts/run_tests.sh`
- **Symptom:** Running pytest directly failed with `pluggy._manager.PluginValidationError: unknown hook 'pytest_launch_collect_makemodule' in plugin 'launch_ros'` and `ModuleNotFoundError: No module named 'catkin_pkg'`.
- **Root Cause:** On Ubuntu systems with ROS 2 Humble installed, `/opt/ros/humble/` injects pytest entrypoints and exports a `scripts` package that shadows the project's `./scripts` folder.
- **Remediation:**
  1. Added `-p no:launch_testing -p no:launch_ros` to `addopts` in `pyproject.toml`.
  2. Updated `scripts/run_tests.sh` to isolate `PYTHONPATH="$PROJECT_ROOT/src:$PROJECT_ROOT"` and disable `launch_ros`.
- **Verification:** All 1,288 tests collect cleanly and execute deterministically on Ubuntu 22.04 LTS.

---

### Defect MW-M10-DEF-05: Backup File Bloat in Release Candidate Archive
- **Severity:** LOW (Packaging Hygiene)
- **Component:** `scripts/package_release.py`, `outputs/releases/marswalk-v2.0.0-rc1.tar.gz`
- **Symptom:** Release archive `v2.0.0-rc1` included `web/app.js.bak13d_orig` (841 KB decompressed).
- **Root Cause:** `EXCLUDE_EXTENSIONS` only filtered `.bak`, while `web/app.js.bak13d_orig` had a compound extension `.bak13d_orig`.
- **Remediation:** Updated `should_exclude()` in `scripts/package_release.py` to filter any path containing `.bak` or starting with `.bak`.
- **Verification:** Repackaged `marswalk-v2.0.0-rc2.tar.gz` successfully excluded the backup file, reducing archive size from 16.23 MB to 16.11 MB.

---

### Defect MW-M10-DEF-06: Socket BrokenPipeError on Client Disconnect During Long Computations
- **Severity:** LOW (Server Telemetry Robustness)
- **Component:** `scripts/run_atlas.py`
- **Symptom:** Server log logged `BrokenPipeError: [Errno 32] Broken pipe` when a client closed its socket before a multi-second route calculation finished.
- **Root Cause:** `send_json_response()` attempted `self.wfile.write(body)` without handling standard socket disconnect exceptions.
- **Remediation:** Wrapped response writing in `try...except (BrokenPipeError, ConnectionResetError): pass`.
- **Verification:** Zero unhandled socket exceptions during 20-thread concurrency stress tests.

---

## 3. Summary & Remediation Statistics

| Defect ID | Severity | Component | Status | Verification Gate |
|---|---|---|---|---|
| **MW-M10-DEF-01** | LOW | UI Landing Elements | **RESOLVED** | `test_milestone_9l_design.py` (PASS) |
| **MW-M10-DEF-02** | MEDIUM | A* Optimization Latency | **RESOLVED** | `test_milestone_9v_mission_optimizer.py` (PASS, 1925ms) |
| **MW-M10-DEF-03** | LOW | Matrix Multiplication Deprecation | **RESOLVED** | Pytest Warning Counter = 0 |
| **MW-M10-DEF-04** | HIGH | ROS Humble Test Collision | **RESOLVED** | Full Suite Collection (1,288/1,288 PASS) |
| **MW-M10-DEF-05** | LOW | Release Archive Bloat | **RESOLVED** | `v2.0.0-rc2` Archive Inspection (-124 KB) |
| **MW-M10-DEF-06** | LOW | Socket Disconnect Robustness | **RESOLVED** | Concurrency Stress Test (20/20 PASS) |

**Total Defects Identified:** 6  
**Total Defects Resolved:** 6 (100% Remediation Rate)  
**Open Critical/High Defects:** 0 (Zero)
