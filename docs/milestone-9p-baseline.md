# MARSWALK 2.0 — MILESTONE 9P BASELINE AUDIT
## Real System Baseline, Stored Records Inventory, and Verification of Failure Points

**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** 2026-10-18  
**Author:** Principal Software Engineer, Planetary Mission Systems Engineer, GIS Verification Engineer  
**Status:** Audit Complete — Baseline Established  

---

## 1. Environment & Server Process Verification

- **Active Process:** Python Atlas Daemon (`scripts/run_atlas.py --port 3000 --no-browser`) running as background process.
- **Port & Host:** `http://localhost:3000` (and `http://127.0.0.1:3000`).
- **Health Check Response:**
  ```json
  {
    "status": "online",
    "engine": "MarsWalk 2.0 Routing Intelligence",
    "target": "Mars (IAU 2000 Sphere / USGS CTX DTM 20m)",
    "terrain_loaded": true,
    "waypoints_count": 12,
    "endpoints": [
      "/api/plan_route",
      "/api/gauntlet",
      "/api/scenario_comparison",
      "/api/scenario_sensitivity",
      "/api/export_briefing",
      "/api/missions",
      "/api/experiments",
      "/api/experiments/compare",
      "/api/imagery/status",
      "/api/imagery/tile",
      "/api/health"
    ]
  }
  ```
- **Git Working Tree:** Clean on `main`, zero deleted or modified untracked user assets (`AGENTS.md`, `data/`, `docs/`, `outputs/`, `pyproject.toml`, `schemas/`, `scripts/`, `src/`, `tests/`, `web/`).

---

## 2. Test Suite Baseline

- **Execution Command:** `pytest`
- **Result:** **216 passed in 79.72 seconds (0 failures, 0 errors, 0 skipped)**
- **Test Modules Passing:**
  - `tests/test_api_routing.py`: 14 passed
  - `tests/test_app.py`: 14 passed
  - `tests/test_export_mission_assets.py`: 1 passed
  - `tests/test_ingest.py`: 5 passed
  - `tests/test_milestone_8a_smoke.py`: 5 passed
  - `tests/test_milestone_9d.py`: 5 passed
  - `tests/test_milestone_9e.py`: 7 passed
  - `tests/test_milestone_9f.py`: 4 passed
  - `tests/test_milestone_9g.py`: 6 passed
  - `tests/test_milestone_9h.py`: 11 passed
  - `tests/test_milestone_9i.py`: 7 passed
  - `tests/test_milestone_9j_contracts.py`: 20 passed
  - `tests/test_milestone_9k_workspace.py`: 20 passed
  - `tests/test_milestone_9l_design.py`: 4 passed
  - `tests/test_milestone_9m_verification.py`: 6 passed
  - `tests/test_milestone_9n_verification.py`: 8 passed
  - `tests/test_milestone_9o_verification.py`: 7 passed
  - `tests/test_place_catalog.py`: 5 passed
  - `tests/test_planner.py`: 14 passed
  - `tests/test_preferences.py`: 15 passed
  - `tests/test_science_budget.py`: 15 passed
  - `tests/test_stress_test.py`: 13 passed
  - `tests/test_terrain.py`: 10 passed

---

## 3. Persistent Workspace Inventory (Zero Deletion Policy)

Preserved intact with zero deletions or overwrites:
1. **Saved Missions (`data/workspaces/missions/`): 7 Records**
   - `m_jezero_delta_scarp_surve_090607.json` (1,334 bytes)
   - `m_jezero_delta_scarp_surve_110130.json` (1,334 bytes)
   - `m_jezero_delta_scarp_surve_281379.json` (1,334 bytes)
   - `m_jezero_delta_scarp_surve_ab03e3.json` (1,076 bytes)
   - `m_jezero_delta_scarp_surve_b25501.json` (1,334 bytes)
   - `m_jezero_delta_scarp_surve_bb4117.json` (1,334 bytes)
   - `m_milestone_9m_jezero_rehe_08f02f.json` (1,346 bytes)

2. **Saved Stress-Test Experiments (`data/workspaces/experiments/`): 10 Records**
   - `exp_m9m_stress_test_experime_d7b97e.json` (68,749 bytes)
   - `exp_rockfall_baseline_run_0eb813.json` (59,038 bytes)
   - `exp_rockfall_baseline_run_7df530.json` (59,038 bytes)
   - `exp_rockfall_baseline_run_a66cc9.json` (59,038 bytes)
   - `exp_rockfall_baseline_run_fe315c.json` (59,038 bytes)
   - `exp_rockfall_rover_fast_run_4b99f7.json` (59,134 bytes)
   - `exp_rockfall_rover_fast_run_600b2d.json` (59,135 bytes)
   - `exp_rockfall_rover_fast_run_822404.json` (59,135 bytes)
   - `exp_rockfall_rover_fast_run_ed0d57.json` (59,135 bytes)
   - `exp_study_untitled_mission_1_9e1842.json` (61,407 bytes)

---

## 4. Identified Defects & Integration Failure Modes

Through detailed inspection of `web/app.js`, `src/marswalk/core/planner.py`, `src/marswalk/core/stress_test.py`, and `src/marswalk/api/service.py`, seven critical integration defects were diagnosed:

1. **Missing `isBooted: () => true` on `window.__atlas`:**
   Automated browser runners and test tools poll for `window.__atlas && window.__atlas.isBooted && window.__atlas.isBooted()`. Its absence forced automation suites to hit timeout fallbacks.
2. **Missing Invalidation on 3D Surface Picking:**
   When clicking to pick `start` or `goal` directly on the 3D terrain mesh (`planningMode === 'start'` or `'goal'`), the code updated `customStart`/`customGoal` coordinates but failed to call `updateCalculateButtonState()`, `buildWaypointBeacons()`, `updateJezeroLabels()`, `setSimulationStale(true)`, or `setUnsavedChanges(true)`, leaving the previous route and scenario outputs unflagged as stale.
3. **No Input/Change Listeners on Expedition Budget Controls:**
   `#inputExpeditionHours`, `#inputDwellMins`, `#inputDelayMins`, and `#inputMaxDistanceM` lacked event listeners. Typing or modifying a budget constraint did not trigger `setSimulationStale(true)` or `setUnsavedChanges(true)` until an explicit calculation completed.
4. **Silent Failure & Missing Client-Side Validation on Non-Positive Budgets:**
   Entering `0` or negative numbers in `#inputExpeditionHours` or negative distances triggered raw HTTP 400 errors from the backend (`'operational_limit_s' must be a positive number`) rather than clean, informative inline UI validation messages.
5. **Stale Scenario & Recovery Cards Persisting Across Baseline Route Changes:**
   When recalculating a new baseline route with different endpoints, stops, or profiles, `recoveryPlanCard`, `comparisonLabCard`, and `sensitivityResultCard` were not closed, leaving obsolete historical scenario metrics visible side-by-side with the new baseline.
6. **Vertical Exaggeration Scene Desynchronization:**
   Changing the vertical exaggeration factor rebuilt the 3D elevation mesh and redrew the primary route polyline, but failed to recalculate elevation positions for active detour lines (`detourRouteLineMesh`) or disruption hazard warning markers (`disruptionHazardMesh`), causing them to float or sink relative to the terrain.
7. **Briefing Export Reachability Conflation:**
   In fallback briefing generation (`web/app.js:2977`), `is_reachable` was derived via `statFeasibility.textContent === 'FEASIBLE'`. For a route that was reachable but over budget (`OVER BUDGET`), this evaluated `is_reachable` to `false`, conflating physical reachability with budget compliance.
