# MarsWalk 2.0 — Milestone 9R Baseline & Architecture Audit
## Autonomous 90-Minute Engineering Sprint: Interactive Contingency Designer, Compound Mission Events, and Real-Time What-If Analysis

**Date:** October 18, 2026  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Engineer:** Principal Aerospace Software Engineer, Planetary Robotics Mission Planner, Simulation Engineer, Three.js Interaction Developer, and Verification Lead.  
**Sprint Horizon:** 90 Minutes (Target completion: 22:55 local time)

---

## 1. Verified Baseline Status

Before authoring code or modifying existing interfaces, the active repository status was independently verified:

### 1.1 Git Status
- Working tree clean of uncommitted changes to tracked files.
- Untracked files present in documentation, tests, web assets, and runtime caches.

### 1.2 Automated Test Baseline
- **Execution:** `pytest -q`
- **Result:** **232 passed in 64.51s** (25 test suites, 0 failures, 0 skips).
- **Core verification suites confirmed:**
  - `tests/test_milestone_9q_demo.py` (8 tests passed)
  - `tests/test_milestone_9p_integration.py` (8 tests passed)
  - `tests/test_milestone_9k_workspace.py` (20 tests passed)
  - `tests/test_milestone_9j_contracts.py` (20 tests passed)
  - `tests/test_stress_test.py` (13 tests passed)
  - `tests/test_planner.py` (14 tests passed)

### 1.3 Active Server & Daemon
- Process: Python Atlas server running on `http://127.0.0.1:3000` (PID active under task `task-8042`).
- Preflight health check: `GET /api/preflight` returns `12/12` passing checks in 445.5ms.

---

## 2. Architecture & Extension Points Audit

### 2.1 Existing Scenario Simulation Engine (`src/marswalk/core/stress_test.py`)
- **`DisruptionType` enum:** Defines `CORRIDOR_CLOSURE`, `UNSTABLE_SAND`, `RESTRICTED_SLOPE`, `MOBILITY_DEGRADATION`, `DUST_STORM_VISIBILITY`, `TARGET_UNAVAILABLE`, `REDUCED_BUDGET`, `COMPOUND_DISRUPTION`.
- **`ScenarioDefinition` dataclass:** Represents a disruption with `blocked_cells`, `cost_multiplier_cells`, `cost_multiplier`, `max_slope_deg_override`, `speed_multiplier`, `operational_delay_s`, `budget_reduction_pct`, `reduced_max_distance_m`, `unavailable_target_id`, `compound_scenarios`, etc.
- **`run_scenario()` function:**
  - Accepts baseline `RouteResult`, `ScenarioDefinition`, start/goal coords, waypoints, `TerrainGrid`, and vehicle/planning configs.
  - Translates `blocked_cells` into a boolean mask (`scen_blocked_mask`).
  - Translates `cost_multiplier_cells` into a float mask (`scen_cost_multiplier_mask`).
  - Calls `plan_route()` or `plan_sequential_multistop_route()` with masks applied.
  - For non-geometric scenarios (e.g. speed derating, dust holds), keeps physical path identical and recomputes edge costs/timeline without inventing detours.
  - Computes `RegretLedger`, `ScenarioComparison`, and an automated 3-way recovery plan.
- **Current Limitation:** Predefined scenario IDs (`scen_corridor_rockfall`, etc.) are curated; custom closure only supports a single ad-hoc list of `blocked_cells` without a structured multi-event configuration schema or UI designer.

### 2.2 API Layer (`src/marswalk/api/service.py`)
- **`POST /api/gauntlet`:** Currently supports `scenario_id` selection or a basic `custom_closure` with `blocked_cells`.
- **`POST /api/scenario_comparison`:** Compares a list of predefined scenario IDs against a baseline.
- **Extension Required:**
  - Support a structured `custom_contingency` payload in `/api/gauntlet` and/or a dedicated `/api/contingency/simulate` endpoint.
  - Support compound events (up to 3 combined events: e.g., closed corridor + difficult terrain + reduced mobility + budget reduction + target unavailable).
  - Geographic radius-to-cell expansion helper with boundary and NoData safety checks.
  - Clean validation rejecting invalid, infinite, or out-of-bounds parameters.

### 2.3 Frontend & 3D Interaction Layer (`web/app.js` & `web/index.html`)
- **Terrain Surface Picking:**
  - Existing `onJezeroClick(event)` raycasts onto `jezeroTerrainMesh` and computes `(row, col)` via UV/world coordinates for `customStart` and `customGoal`.
  - Extension point: Introduce `mapInteractionMode`: `'normal'` | `'set_start'` | `'set_goal'` | `'place_contingency'`.
  - When in `'place_contingency'`, clicking the terrain sets event center `(row, col)`, calculates radius in meters, displays a 3D translucent hazard marker/ring, and populates the Contingency Designer UI without mutating start/goal!
- **Scenarios Tab UI:**
  - Tab 3 (`#tabScenarios`) currently houses predefined stress testing, comparison lab, and parameter sweep.
  - Add a dedicated **Interactive Contingency Designer** section:
    - Event Type selector (Corridor Closure, Difficult Terrain, Reduced Mobility, Reduced Time Budget, Operational Hold, Target Unavailable).
    - Map placement button (`📍 Place on Terrain`) + coordinate fallback inputs `(Row, Col, Radius)`.
    - Event parameters (Severity, cost multiplier, speed multiplier, budget reduction %, delay).
    - Event list / staging shelf (supports up to 3 combined events with toggles and remove buttons).
    - Simulation trigger (`⚡ Simulate Custom Contingency`).
    - Stale result detection (warns if baseline or contingency parameters change).
    - Detailed Results Matrix (Baseline vs Custom Scenario vs Difference) and plain-English evidence-based explanation.
    - Save to Experiment Library action.

---

## 3. Implementation Plan & Phases

| Phase | Description | Target Time |
| :--- | :--- | :--- |
| **Phase 1: Audit & Baseline** | Verify baseline tests and write audit | Min 0–10 |
| **Phase 2: Custom Contingency Engine** | Core Python event models, cell footprint conversion, compound event resolver | Min 10–35 |
| **Phase 3: API Endpoints & Contracts** | API endpoint `/api/contingency/simulate`, schema validation, unit tests | Min 35–48 |
| **Phase 4: Map Placement & 3D Visualizer** | Three.js raycasting mode, hazard footprints, clear separation from start/goal | Min 48–60 |
| **Phase 5: Designer UI & Comparison Table** | Staging list, compound simulation, delta table, narrative generation | Min 60–72 |
| **Phase 6: Persistence & Experiment Library** | Saving custom contingency runs to disk, replay compatibility | Min 72–78 |
| **Phase 7: Testing & Evidence Capture** | 17+ automated test cases in `test_milestone_9r_contingency.py`, browser journeys | Min 78–88 |
| **Phase 8: Documentation & Handoff** | Update README, write reports, create user artifact | Min 88–90 |
