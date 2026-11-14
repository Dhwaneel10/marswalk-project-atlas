# Milestone 9Z Baseline Audit — Mission Timeline Playback & Route Animation

**Project:** MarsWalk 2.0 (NASA Space Apps Challenge)  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** October 19, 2026  
**Status:** Baseline Audited & Verified

---

## 1. Verified Baseline State (Milestone 9Y Handoff)

Before implementing Milestone 9Z, the repository state was independently inspected and verified:
- **Test Suite Status:** 353 / 353 passing tests across 32 test suites.
- **Preflight Diagnostics:** 12 / 12 checkpoints green (server operational on `http://127.0.0.1:3000`).
- **Core Planner & Models:** `src/marswalk/core/planner.py`, `src/marswalk/core/terrain.py`, `src/marswalk/core/route_explainer.py`.
- **API Contracts:** 8 registered schemas in `src/marswalk/api/contracts.py` (including `route-explanation-response.schema.json`).
- **Existing User Data:** 7 saved missions in `data/workspace/missions/`, 11 experiments in `data/workspace/experiments/`, completely untouched.

---

## 2. Architectural Analysis: Timeline & Playback Mechanics

### A. Existing Mission Timeline (`planner.py`)
In `src/marswalk/core/planner.py`:
- `MissionTimeline` tracks:
  - `events`: Ordered list of `TimelineEvent`.
  - `total_traverse_time_s`: Cumulative travel duration.
  - `total_dwell_time_s`: Cumulative target science dwell.
  - `total_operational_delay_s`: Cumulative scenario holds (e.g., communication blackout, dust storm hold).
  - `total_mission_time_s`: Total mission duration $T_{\text{mission}} = T_{\text{traverse}} + T_{\text{dwell}} + T_{\text{delay}}$.
  - `remaining_margin_s`: Budget margin $T_{\text{budget}} - T_{\text{mission}}$.
- `TimelineEvent`:
  - `event_type`: `'start'`, `'traverse_leg'`, `'science_dwell'`, `'scenario_delay'`, `'arrival'`.
  - `label`: Human-readable description.
  - `target_id`: Optional science target identifier.
  - `leg_index`: Optional index of the associated route leg.
  - `start_time_s` and `end_time_s`: Modeled wall-clock timestamps within the mission.
  - `duration_s`: Event duration in seconds.
  - `distance_m`: Traverse distance (0.0 for dwell/delay).

### B. Missing Playback Primitives (The Milestone 9Z Gaps)
1. **Discrete Step vs. Leg-Level Resolution:**
   - Existing `TimelineEvent` provides timestamps at the leg level (e.g. Leg 0 start to end).
   - In physical path traversal, a leg contains dozens to hundreds of discrete grid steps $(r_k, c_k) \to (r_{k+1}, c_{k+1})$.
   - To render smooth 3D route animation, we require discrete time attribution $\tau_k$ for every grid step along the path, weighted by directed traversal cost $c_k = C(v_k \to v_{k+1})$.
2. **Stationary Dwell & Scenario Delay Interpolation:**
   - During `science_dwell` and `scenario_delay`, marker spatial coordinates $(r, c)$ must stay strictly stationary at the active waypoint, while mission elapsed time continues advancing and active event state reflects the dwell/delay phase.
3. **Vehicle / Crew 3D Marker in Three.js:**
   - The Three.js scene (`web/app.js`) currently displays static polyline tubes for routes (`activeRouteLineMesh`, `baselineRouteLineMesh`, `contingencyRouteLineMesh`).
   - It lacks an active 3D vehicle marker (rover mesh / beacon) that translates along the polyline surface at proper height above the DEM with vertical exaggeration.
4. **Playback Loop Integration:**
   - The renderer in `web/app.js` has a single `animate()` loop (`requestAnimationFrame(animate)`).
   - Playback must hook cleanly into `animate(time)` with delta-time integration and user speed scaling (1x, 5x, 10x, 25x, 50x, 100x), without spawning duplicate `requestAnimationFrame` loops.
5. **Interactive Scrubbing & Variant Switching:**
   - The user must be able to scrub a slider to any arbitrary mission timestamp $t \in [0, T_{\text{total}}]$, instantly repositioning the marker and synchronizing telemetry (elapsed time, distance traversed, current event, elevation, slope).
   - The playback system must support switching seamlessly between Nominal Baseline, Disrupted Detour, and Adaptive Replacement missions without mixing route geometry or timing arrays.

---

## 3. Scientific & Operational Integrity Rules
- Modeled timelines represent calculated traversal times based on slope penalty functions and walking/driving speeds; they are not real-time telemetry from an active Mars mission.
- Traversal effort is reported in equivalent flat meters or calculated seconds, never as certified astronaut life-support envelopes.
- No synthetic data will be presented as primary observations.
