# MarsWalk 2.0 — Milestone 10B Baseline & Architectural Audit

**Milestone:** 10B — Mid-Sortie Emergency Injection, Mission State Handoff & Live Adaptive Replanning  
**Status:** Baseline Audited & Verified  
**Date:** 2026-10-19  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  

---

## 1. Baseline Verification

Before initiating Milestone 10B development, repository integrity, test suite performance, and operational health were verified independently:

1. **Test Suite Execution (`pytest -q`):**
   - **Result:** **384 passed** across 34 test files in 174.65 seconds.
   - **Failures / Warnings:** 0 failures, 0 warnings.
   - **Coverage:** Core terrain cost modeling, Apollo walking equations, A* search, contingency gauntlet detours, compound stress scenarios, multi-stop optimization, adaptive replanning, sensitivity analysis, explainability attribution, Milestone 9Z mission playback, and Milestone 10A camera director & telemetry cues.

2. **Preflight Readiness Verification (`scripts/preflight_check.py`):**
   - **Result:** **12/12 checks passed** in 403.0 ms on `http://127.0.0.1:3000`.
   - **Subsystems Verified:**
     - 01 Atlas HTTP API Server (`/api/health`) — Online on port 3000 (Mars IAU 2000)
     - 02 Web Frontend Assets (`index.html`, `app.js`, `styles.css`)
     - 03 Planetary Feature Gazetteer (2,061 Martian features loaded)
     - 04 Planetary Imagery Registry (9 imagery products verified)
     - 05 Global Mars Basemap Layer (Viking MDIM2.1 / MGS MOLA)
     - 06 Jezero CTX Optical Imagery
     - 07 Jezero Crater 20m DTM (250x250 GeoTIFF, cell size 20.0m)
     - 08 Route Planning Engine (A*)
     - 09 Gauntlet Disruption & Recovery Engine
     - 10 Persistent Workspace Storage (**7 historical missions, 11 saved experiments preserved**)
     - 11 Mission Briefing & Schema Validator (Draft 2020-12 valid)
     - 12 Streamlit Tactical Control App

---

## 2. Mid-Sortie Emergency Injection Architecture Audit

### 2.1 State Capture at Interruption Timestamp $t_{\text{current}}$
MarsWalk 2.0 tracks mission playback via `playbackState.elapsedSeconds` ($t$) against a deterministic `MissionPlaybackModel`.
- **Rover Position:** `interpolate_playback_state(model, t)` calculates interpolated floating-point grid coordinates $[r, c]$, instantaneous elevation, slope, and heading. For replanning, the rover's discrete anchor cell is obtained as $P_{\text{current}} = (\operatorname{round}(r), \operatorname{round}(c))$.
- **NoData & Grid Validation:** Cell $(r, c)$ must be within Jezero DTM bounds $[0, 250) \times [0, 250)$ with elevation $> -9000.0\text{ m}$.
- **Target Partitioning:**
  - In `model.events` and `model.waypoints`, each waypoint/dwell stop has an associated `start_time_s` and `end_time_s`.
  - Any target whose dwell period has completed (`end_time_s <= t`) is marked as **completed/visited**.
  - Any target whose dwell period is in the future (`start_time_s > t`) is marked as **unvisited/pending**.
  - If the interruption occurs *during* an active dwell (`start_time_s <= t < end_time_s`), the remaining dwell duration is $(end\_time\_s - t)$ or the dwell is treated as interrupted.
- **Budget Accounting:**
  - Given mission total budget $T_{\text{budget}}$, the remaining operational budget is:
    $$T_{\text{rem}} = \max(0.0, T_{\text{budget}} - t_{\text{current}})$$
  - This guarantees that prior drive time and dwell periods are never double-counted when evaluating feasibility of remaining stops.

### 2.2 Supported Injected Event Types
Milestone 10B introduces 4 genuine operational contingencies:
1. **Rockfall Corridor Closure (`closure`):**
   - Specified by epicenter $[r, c]$ or target coordinate and radius $R$ (meters or cells).
   - Injects blocked non-traversable cells into the active `TerrainGrid`.
   - Forces A* to compute an authentic detour from $P_{\text{current}}$ to remaining targets.
2. **Mobility Derate (`mobility`):**
   - Rover speed derating factor (e.g., $0.5\times$ or $0.3\times$) or metabolic exertion modifier.
   - Increases traversal time across all subsequent legs, testing whether the remaining itinerary exceeds $T_{\text{rem}}$.
3. **Operational Safety Hold (`hold`):**
   - Immediate operational delay (e.g., 600 seconds) for sensor diagnostics or dust clearing.
   - Directly reduces available mobility budget for remaining targets: $T_{\text{rem, eff}} = T_{\text{rem}} - \Delta t_{\text{hold}}$.
4. **Instrument Abort / Drop Target (`drop_target`):**
   - A target instrument failure renders a specific pending target non-viable.
   - Target is excised from candidate stops, re-routing directly to subsequent objectives or landing site.

### 2.3 3-Stage Mid-Sortie Trade-off Evaluation
When an emergency is injected, the engine evaluates three concurrent continuation trajectories from $P_{\text{current}}$:
1. **Nominal Remaining (`nominal_remaining`):** What would happen if the rover simply continued its original planned route to remaining stops without alterations.
2. **Disrupted Remaining (`disrupted_remaining`):** Original path evaluated under the injected event (e.g. encountering blocked cells or running out of time due to derated speed).
3. **Adaptive Continuation (`adaptive_continuation`):** Fully optimized A* replan from $P_{\text{current}}$ to original goal $P_{\text{goal}}$, visiting the optimal feasible subset of unvisited targets within $T_{\text{rem}}$.

### 2.4 Playback Handoff Mechanics
When the user applies the adaptive continuation:
- The historical route traversed up to $t_{\text{current}}$ is preserved as an immutable historical track (rendered in dim cyan/slate).
- The continuation route is loaded as the active trajectory from $P_{\text{current}}$ onward.
- Rover marker remains anchored at $P_{\text{current}}$, avoiding visual snapping to the original origin.
- The playback engine updates total sortie duration ($t_{\text{total}} = t_{\text{current}} + t_{\text{continuation}}$) and advances seamlessly.
- Audio and visual telemetry triggers for completed stops are suppressed, preventing duplicate cue firing.

---

## 3. Plan & Acceptance Criteria

1. **Core Module (`src/marswalk/core/mission_continuation.py`):**
   - Implement `capture_mid_sortie_state` and `plan_mission_continuation`.
   - Implement event disruption modeling on remaining routes.
2. **Schema & API Service:**
   - Define `schemas/api/v1/mission-continue-response.schema.json`.
   - Implement `mission_continue_api` in `src/marswalk/api/service.py`.
   - Route `POST /api/mission/continue` in `scripts/run_atlas.py`.
3. **Automated Testing Suite (`tests/test_milestone_10b_live_replanning.py`):**
   - Verify state capture accuracy, unvisited target filtering, budget deduction, closure detour calculation, and HTTP endpoint contract compliance. Target 400+ passing tests.
4. **Frontend Integration (`web/index.html`, `web/styles.css`, `web/app.js`):**
   - Add "⚡ INJECT EVENT / REPLAN" button in playback panel.
   - Emergency Injection modal/drawer with parameterized event types.
   - Three-stage trade-off card with clear feasibility metrics.
   - "Apply Continuation" action seamlessly swapping playback model and maintaining rover position.
5. **Real CDP Browser Automation (`scripts/capture_milestone_10b_evidence.py`):**
   - Capture 5 high-resolution evidence screenshots depicting pause, event injection, continuation trade-off, route preview, and resumed traversal.
