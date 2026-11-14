# MarsWalk 2.0 — Milestone 9M Defect & Root Cause Audit
## Mission Workspace Recovery, Trustworthy Stress Testing, High-Resolution Regional Exploration, and Final UI Refinement

**Date:** October 18, 2026  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Author:** Principal Software Engineer, Planetary GIS Engineer, Simulation Engineer, and Senior Product Designer  

---

## 1. Executive Summary

This audit investigates the specific functional and visual defects identified in real browser use following Milestone 9L. The root causes span JavaScript event handling, route optimization caching, unit/semantic conflation between physical distance and life-support time, label management state machines, and regional imagery lifecycle hooks.

---

## 2. Root Cause Analysis of Identified Defects

### 2.1 P0: Map Loss and Scene Destruction When Switching Vehicle Mode
- **Symptom:** Selecting Crew EVA or Robotic Rover in Jezero Crater causes the 3D surface mesh to disappear completely or leaves the WebGL canvas in a corrupted state.
- **Root Cause:** In [`web/index.html`](file:///E:/Python/NASA-Spaceapps/Marswalk/web/index.html), three distinct control groups shared the generic CSS class `.exag-pill`:
  1. `#exagPills` (Vertical Exaggeration: 1.0x, 1.5x, 2.0x, 3.0x)
  2. `#terrainTexturePills` (NASA CTX, Terrain Slope, Elevation)
  3. `#vehicleModePills` (Crew EVA, Robotic Rover)
  In [`web/app.js`](file:///E:/Python/NASA-Spaceapps/Marswalk/web/app.js) line 133, `const exagPills = document.querySelectorAll('.exag-pill')` selected all three sets of buttons. In line 4235, the click listener on `exagPills` read `pill.dataset.exag`. On vehicle mode buttons, `dataset.exag` is `undefined`, so `parseFloat(undefined)` evaluated to `NaN`. The handler then set `currentExaggeration = NaN` and called `buildTerrainMesh(NaN, currentTerrainTexture)`, multiplying all vertex heights by `NaN`. This resulted in corrupted WebGL bounding boxes and wiped the terrain mesh from the scene.
- **Correction:** Scope vertical exaggeration selectors strictly to `#exagPills .exag-pill`, guard `parseFloat` against `NaN`, and isolate vehicle mode pills to their dedicated click listener without triggering terrain geometry reconstruction.

---

### 2.2 Intermediate Research Stops Omitted in Balanced & Science-First Profiles
- **Symptom:** Adding research targets works in Conservative mode, but switching to Balanced or Science-First wipes the added stops or displays precomputed direct routes.
- **Root Cause:** In [`web/app.js`](file:///E:/Python/NASA-Spaceapps/Marswalk/web/app.js) lines 4196–4208, the profile tab click listener checked:
  ```javascript
  const isDefaultEndpoints = customStart && customStart.row === 117 && customStart.col === 157 &&
                            customGoal && customGoal.row === 66 && customGoal.col === 128;
  if (isDefaultEndpoints && missionData && missionData.routes[currentProfile]) {
    activeRoutePath = missionData.routes[currentProfile].path_rc;
    drawLiveRoute(activeRoutePath, currentProfile);
  } else {
    calculateTraverse();
  }
  ```
  `isDefaultEndpoints` only checked departure/destination row and column, completely ignoring `activeIntermediateStops.length > 0`. Consequently, whenever the user was at the default endpoints and added research stops, switching profiles loaded the static 2-point precomputed path from `missionData.routes`, discarding the user's custom research stops from the route.
- **Correction:** Only load static precomputed assets if `activeIntermediateStops.length === 0`. If any intermediate stop exists, always invoke `calculateTraverse()` with the user's active stops. Furthermore, ensure `service.py` applies profile-specific terrain weights (`theta_max_deg`, `alpha_s`, `alpha_up`) so that Conservative, Balanced, and Science-First genuinely produce distinct routes based on their documented planning objectives.

---

### 2.3 Stress-Test Engine Semantic Errors: Distance vs. Life-Support Time
- **Symptom:** The `25% Emergency Life Support Budget Reduction` scenario reported a traverse distance of 4577 m, displayed a 3433 m ceiling, and claimed the mission was budget-compliant (`is_budget_feasible: True`). Baseline and disrupted plans showed identical +0 m, +0 effort, 0 min changes, followed by implausible recovery values.
- **Root Causes:**
  1. **Unit Conflation:** In [`src/marswalk/core/stress_test.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/stress_test.py) lines 549–556, `DisruptionType.REDUCED_BUDGET` converted a life-support reduction into a physical distance ceiling:
     `scen_max_distance_m = base_ceiling * (1.0 - pct / 100.0)`.
     Life support is consumable time (oxygen, battery, cooling, hydration), not physical ground distance. Reducing life support must reduce the *operational time limit* (`operational_limit_s`), not invent an arbitrary metre threshold.
  2. **Hardcoded Feasibility Copying:** In line 649 of `stress_test.py`, `scenario_route.is_budget_feasible` was hardcoded to `baseline_route.is_budget_feasible`. It was never re-evaluated against the reduced ceiling! Even when 4577 m exceeded 3433 m, it copied `True` from the baseline.
  3. **Recovery Calculation Artifacts:** In lines 794–798, `rec_margin_s` added a hardcoded `+ 600.0` seconds and accepted pruned routes without verifying whether they satisfied the reduced budget.
- **Correction:**
  - Separate physical distance limits from available mission duration.
  - For life-support budget reductions, reduce `operational_limit_s` by 25% (e.g. from 8.0h to 6.0h for crew EVA, or from 4.0h to 3.0h for rovers).
  - Explicitly calculate `is_budget_feasible = (is_dist_within_limit and is_time_within_limit)`.
  - Recalculate remaining time margin honestly: `remaining_margin_s = operational_limit_s - total_mission_time_s`. If `total_mission_time_s > operational_limit_s`, the mission is strictly `OVER BUDGET` / `INFEASIBLE`.

---

### 2.4 Label Clutter During Mission Planning
- **Symptom:** Dozens of unselected waypoint beacons and text popups crowd the map during active mission planning, obscuring traverse corridors and terrain slopes.
- **Root Cause:** In [`web/app.js`](file:///E:/Python/NASA-Spaceapps/Marswalk/web/app.js), `buildWaypointBeacons()` and `updateJezeroLabels()` rendered 3D billboard markers and DOM labels for all 12+ Jezero waypoints indiscriminately, regardless of whether a mission was actively being planned.
- **Correction:** Implement intelligent waypoint filtering:
  - During active route planning or display, show ONLY the departure marker, intermediate research stops, destination, and visited objectives.
  - Suppress unselected catalog waypoints by default.
  - Provide an optional `Show all locations` toggle in the workspace.
  - Restore standard exploratory labels when the mission is reset or cleared.

---

### 2.5 Landing Page Label & HUD Leakage
- **Symptom:** In Milestone 9L, planetary feature labels (`Olympus Mons 610 km`, `Valles Marineris 3761 km`) and the top Atlas HUD header leaked through the landing page hero composition.
- **Root Cause:** `#marsLandingPage` was toggled via `.hidden` class, but the underlying HUD header (`.hud-header`), category filter bar (`#categoryFilterBar`), telemetry bar (`.hud-telemetry-bar`), and globe labels (`#labelsOverlay`) remained visible with higher or equal z-indexes and opacity.
- **Correction:** Link landing page visibility state to HUD display state: when `isLandingActive` is true, explicitly hide `.hud-header`, `#categoryFilterBar`, `#labelsOverlay`, and `#jezeroLabelsOverlay`. When entering Atlas, restore them cleanly.

---

### 2.6 Regional Destinations Lacking Interactive Imagery
- **Symptom:** Selecting Olympus Mons, Valles Marineris, or Gale Crater on the landing page reoriented the globe but did not load regional CTX mosaics, leaving the user with only global Viking basemaps.
- **Root Cause:** In [`web/app.js`](file:///E:/Python/NASA-Spaceapps/Marswalk/web/app.js), `loadRegionalOverlay()` was defined (lines 744–798) but never invoked by destination selection handlers or search actions.
- **Correction:** Hook `loadRegionalOverlay()` into `handleDestinationSelect()` and featured destination navigation. Provide genuine 6 m CTX regional curved patches on the globe for Olympus Mons, Gale Crater, and Valles Marineris, with clear indicators of imagery resolution and elevation data availability.

---

### 2.7 Cramped Workspace Layout & Missing Expedition Budget
- **Symptom:** The planning panel is narrow (320px), heavily scrolled, and lacks an overall mission time budget configuration for the whole outing.
- **Correction:** Expand workspace panel to 460–500px on desktop. Organize into 4 distinct functional tabs (`Plan`, `Results`, `Scenarios`, `Saved Work`). Add an expedition budget section allowing the user to configure total available expedition time (hours/minutes), per-stop observation dwell time, and operational delays.
