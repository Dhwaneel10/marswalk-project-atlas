# MISSION 6 — BROWSER QA & OPERATOR INTERFACE AUDIT
## Full-Stack UI Verification and Reproducible Defect Register

**Audit Phase:** Mission 6 — Phase 3 Browser QA  
**Auditor:** Principal Systems Engineer &amp; Browser QA Lead  
**Date:** 2026-11-14T20:55:00+05:30  
**Testing Engine:** Autonomous Headless Chrome CDP (`scripts/audit_browser_linux.py`)  
**Resolution Tested:** $1600 \times 1000$ (High DPI Operator Workstation)  
**Host Browser Binary:** `/usr/bin/google-chrome` (Chrome 130+ Linux)  

---

## 1. END-TO-END UI &amp; INTERACTIVE WORKSTATION AUDIT

The operator interface at `http://127.0.0.1:3000` was subjected to an automated stress-test across all five operational pillars and 3D visual workstations.

```
===================================================================================================================
COMPONENT / PILLAR           INTERACTIVE ACTION TESTED              UI RESPONSE TIME   CONSOLE LOGS  AUDIT STATUS
===================================================================================================================
Pillar 1: USGS Terrain       Switch tab &amp; click Point Inspect (1m)        120 ms          Clean      PASS / NOMINAL
Pillar 2: PDS Ground Truth   Switch tab &amp; query 10 Depot Tubes            140 ms          Clean      PASS / NOMINAL
Pillar 3: MEDA Weather       Inject Regional Dust Storm (tau=2.45)        160 ms          Clean      PASS / NOMINAL
Pillar 4: Science Planner    Compute Multi-Objective Science Trade        210 ms          Clean      PASS / NOMINAL
Pillar 5: DTN &amp; Resilience   Inspect Merkle State Proof (7/7 Root)        110 ms          Clean      PASS / NOMINAL
3D Orbit to Surface Flight   Slerp flight transition to Jezero (3.8 km)  1,400 ms         Clean      PASS / NOMINAL
Planetary GIS Layers         Toggle HiRISE, PDS, Depot, Targets mesh       40 ms          Clean      PASS / NOMINAL
Spatial Raycasting           Raycast query on Wildcat Ridge beacon         50 ms          Clean      PASS / NOMINAL
===================================================================================================================
Unhandled Window Errors: 0
Visual Proof Captured:
  - outputs/browser_qa/five_pillars_deck_live.png  (1,043,025 bytes)
  - outputs/browser_qa/jezero_3d_surface_live.png   (1,040,029 bytes)
===================================================================================================================
```

---

## 2. REPRODUCIBLE DEFECT REGISTER

During the red-team qualification and browser stress-testing, 5 defects were identified, investigated, and closed with rigorous engineering fixes:

### DEFECT-01: Non-Numeric Coordinate Inputs Returned HTTP 500
* **Severity:** HIGH (API Robustness)
* **Subsystem:** `src/marswalk/api/service.py` (`pillars_terrain_inspect_api`)
* **Trigger:** Sending `{"row": "foo", "col": "bar"}` to `POST /api/pillars/terrain/inspect`.
* **Root Cause:** Direct `int()` cast raised unhandled `ValueError`, caught by outer top-level handler and returned as `500 ERR_INTERNAL_ROUTING`.
* **Fix:** Wrapped parameter extraction in `try...except (ValueError, TypeError)` and raised `APIError(..., 400)` with `ERR_VALIDATION_FAILED`.
* **Verification:** `curl -X POST ... -d '{"row":"foo"}'` now returns HTTP 400 with a clean diagnostic message.

### DEFECT-02: Science Planner Route A vs Route B Identical Distance
* **Severity:** HIGH (Scientific Defensibility)
* **Subsystem:** `src/marswalk/api/service.py` (`pillars_science_targets_plan_api`) &amp; `web/app.js`
* **Trigger:** Calling `POST /api/pillars/science-targets/plan` to compare Direct vs Science-Optimized traverses.
* **Root Cause:**
  1. Destination was hardcoded to `(135, 91)`, which is identical to Wildcat Ridge. Thus Route A was already terminating at Wildcat Ridge, making the detour collinear with the direct route.
  2. Frontend passed `science_target_ids: ["ST-01", "ST-02"]`, but service looked for `target_ids`, causing fallback to only Wildcat Ridge and ignoring Kodiak Butte.
* **Fix:**
  1. Default destination updated to Delta Scarp Rim Crest `(50, 90)` so the rover executes a true cross-delta transit.
  2. Implemented parameter aliasing (`target_ids` and `science_target_ids`, `ST-01` -> `sci_wildcat_ridge`, `ST-02` -> `sci_kodiak_butte`).
  3. Enforced an operational interception radius $R_{\text{intercept}} = 30.0\,\text{m}$. Route A passes $297.3\,\text{m}$ away (0 science pts), while Route B intercepts both targets ($+160\,\text{pts}$ yield, $+3,096.5\,\text{m}$ delta distance).
* **Verification:** Controlled comparison script confirms distinct geometries and verified target interception.

### DEFECT-03: Stale Checksums in Documentation
* **Severity:** MEDIUM (Documentation Traceability)
* **Subsystem:** `docs/TERRAIN_EXPLORER_REPORT.md`
* **Trigger:** SHA-256 hash inspection of processed rasters.
* **Root Cause:** Intermediate scratch hashes (`024c...` and `b084...`) were copied into documentation instead of the actual on-disk hashes.
* **Fix:** Corrected documentation to reflect true on-disk SHA-256 digests (`875e7e80...` for CTX 20m processed and `0258c9e1...` for HiRISE 1m DTM).
* **Verification:** `sha256sum data/processed/*` matches master manifest and documentation.

### DEFECT-04: Hazelton Sample Tube Designation Mismatch
* **Severity:** MEDIUM (Planetary Science Integrity)
* **Subsystem:** `docs/SCIENCE_DRIVEN_MISSION_REPORT.md` &amp; UI Metadata
* **Trigger:** Sample catalog cross-referencing.
* **Root Cause:** Text stated that *Hazelton* was in tube #241 deposited at Three Forks. In reality, *Hazelton* (tube #268) is retained onboard Perseverance, while its paired core *Bearwallow* (tube #239) was deposited at Three Forks. Tube #241 contains *Malay*.
* **Fix:** Corrected all documentation and UI captions to accurately distinguish onboard retained cores from surface-deposited backup cache tubes.
* **Verification:** Cross-referenced against NASA PDS Mars 2020 Sample Depot Catalog (`three_forks_sample_depot_catalog.json`).

### DEFECT-05: System ROS 2 Humble Pytest Plugin Collision
* **Severity:** MEDIUM (Linux Host Reproducibility)
* **Subsystem:** Test Execution Infrastructure (`scripts/run_tests.sh`)
* **Trigger:** Running `pytest` in an environment where `/opt/ros/humble` is in `PYTHONPATH`.
* **Root Cause:** Pytest auto-loaded ROS `launch_testing` entrypoints from system Python, causing missing `yaml` errors.
* **Fix:** Authored `scripts/run_tests.sh` with isolated `PYTHONPATH` and explicit plugin disable flags (`-p no:launch_testing -p no:launch_testing_ros`).
* **Verification:** `./scripts/run_tests.sh` executes 100% of tests with zero host pollution.

---
*QA report and defect register certified by MarsWalk Lead QA Engineer.*
