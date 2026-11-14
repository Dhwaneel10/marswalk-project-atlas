# MarsWalk 2.0 — Milestone 9W Engineering Handoff Report
## Adaptive Mission Replanning, Science Recovery & Disruption-Aware Optimization

**Milestone:** 9W (Adaptive Mission Replanning, Science Recovery & Disruption-Aware Optimization)  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** October 19, 2026  
**Auditor & Lead:** Principal Aerospace Software Engineer, Scientific Computing Auditor & Planetary Mission Integration Lead  
**Challenge Target:** NASA Space Apps Challenge 2026 / Planetary Surface Route Planning Track  

---

## 1. Executive Summary & Verification Ledger

Milestone 9W delivers a mission-critical operational capability to MarsWalk 2.0: **Adaptive Mission Replanning & Science Recovery**.

When an unforeseen operational disruption occurs on the Martian surface (corridor rockfall closure, sand dune migration slip, drive actuator speed derating, life-support consumable reduction, or science target accessibility loss), MarsWalk answers the operations question:

> **"When a disruption occurs, should the current mission continue, change its route, remove a target, or be replaced with a different science tour?"**

The system models, authoritatively routes, and compares three distinct mission states on the authentic USGS Jezero Crater 20 m CTX elevation model:
1. **Original Plan:** The nominal multi-stop mission selected before the disruption.
2. **Disrupted Plan:** The original itinerary evaluated under the actual disruption events (obstacle masks, speed multipliers, delays, and target unavailability).
3. **Adaptive Plan:** A newly optimized multi-stop tour calculated on the *disrupted pairwise graph* under identical constraints to recover lost science within the surviving life-support envelope.

### Verification Ledger

| Diagnostic / Verification Checkpoint | Baseline (9V) | Milestone 9W Active Build | Status |
| :--- | :--- | :--- | :--- |
| **Automated Test Suite (pytest)** | 299 passed | **319 passed** (20 new 9W regression tests) | **100% GREEN** |
| **Preflight System Diagnostics** | 12 / 12 passed | **12 / 12 passed** (462.8 ms) | **100% READY** |
| **Live API Endpoint** | 11 endpoints | **`POST /api/mission/replan`** wired & validated | **VERIFIED** |
| **3-Stage Comparison Matrix** | N/A | **Stage 1 (Orig) vs Stage 2 (Disr) vs Stage 3 (Adapt)** | **VERIFIED** |
| **Quantitative Science Recovery Ledger** | N/A | **$\Delta P_{lost}, \Delta P_{rec}, \Delta P_{net}, \eta \%$, target deltas** | **VERIFIED** |
| **Recommendation Engine** | N/A | **5-Class Decision State Machine Enum** | **VERIFIED** |
| **Disrupted Pairwise Leg Caching** | Nominal only | **True Disruption Awareness** ($A^*$ detours in leg cache) | **VERIFIED** |
| **Interactive UI Integration** | Contingency only | **Adaptive Replan card, 3-stage grid, 3D preview, Apply** | **VERIFIED** |
| **Workspace Data Immutability** | 7 missions, 11 exp | **Zero Mutation** (7 missions, 11 experiments preserved) | **PRESERVED** |

---

## 2. Technical Deliverables & Architecture

### 2.1 Core Replanning Engine
- **File:** `src/marswalk/core/adaptive_replanner.py`
- **Core Functions & Types:**
  - `ReplanningRecommendation` (Enum): `continue_with_detour`, `drop_target_and_proceed`, `replace_with_adaptive_tour`, `abort_to_direct_baseline`, `unresolvable_critical_hazard`.
  - `ScienceRecoverySummary` (Dataclass): Exact accounting of original priority, disrupted priority, adaptive priority, points lost, points recovered, net priority delta, recovery efficiency percentage, retained stop IDs, dropped stop IDs, and newly added stop IDs.
  - `AdaptiveReplanningResult` (Dataclass): Structured 3-stage comparison capturing `original_plan`, `disrupted_plan`, `adaptive_plan`, `recovery_metrics`, `adaptive_alternatives`, `recommendation`, `recommendation_title`, `operational_rationale`, `computation_fingerprint`, and scientific disclosures.
  - `replan_adaptive_mission()`:
    1. Evaluates Stage 1 nominal baseline.
    2. Compiles 1–3 custom contingency events into `ScenarioDefinition` with spatial obstacle and impedance masks.
    3. Evaluates Stage 2 disrupted baseline under active events, recalculating $A^*$ routes around blocked zones.
    4. Constructs a **disrupted pairwise leg cache** using Python $A^*$ and filters out unavailable targets.
    5. Executes bounded beam search ($B \in [6, 20]$) up to $K \le 5$ stops on the disrupted graph to synthesize candidate tours.
    6. Authoritatively re-evaluates chosen itineraries on the 20 m CTX elevation raster via `plan_sequential_multistop_route()`.
    7. Computes exact recovery ledger and classifies operational recommendation.
    8. Generates deterministic SHA-256 computation fingerprint.

### 2.2 REST API Service
- **Files:** `src/marswalk/api/service.py` & `scripts/run_atlas.py`
- **Endpoint:** `POST /api/mission/replan`
- **Payload Schema:**
  - `start`, `goal`: Coordinate objects (`row`, `col`, `name`).
  - `stops`: Active intermediate science stops.
  - `candidate_targets` / `candidate_waypoints`: Candidate target pool.
  - `custom_events`: 1–3 staged contingency events.
  - `profile`, `vehicle_mode`, `operational_limit_s`, `max_distance_m`, `dwell_time_per_stop_s`, `operational_delay_s`, `max_stops`, `objective`.
- **Validation:** Enforces bounds checking on Jezero CTX DTM (250x250 px), distinct endpoints, valid event definitions, and catalog IDs with HTTP 400 rejection on invalid data.

### 2.3 Web Atlas Frontend Integration
- **Files:** `web/index.html`, `web/styles.css`, `web/app.js`
- **UI Elements:**
  - **Trigger Button:** `btnAdaptiveReplan` ("⚡ ADAPTIVE REPLAN & SCIENCE RECOVERY") styled with mission-ops gradient in Tab 3 (Interactive Contingency Designer).
  - **Three-Stage Comparison Matrix (`.three-stage-grid`):**
    - **Stage 1 (Original Plan):** Science score, stops count, ground distance, total mission time, feasibility badge, and itinerary sequence.
    - **Stage 2 (Disrupted Plan):** Surviving science, priority lost (-pts), detour distance, disrupted duration, and feasibility badge.
    - **Stage 3 (Adaptive Plan):** Recovered science, priority recovered (+pts), distance, duration, remaining margin, and feasibility badge.
  - **Science Recovery Ledger:** Retained objectives, dropped objectives, newly added objectives, and recovery efficiency badge.
  - **Interactive Action Buttons:**
    - `btnApplyAdaptivePlan` ("✓ Apply Adaptive Plan to Mission"): Instantly injects the recovered tour into active intermediate stops and recalculates the workspace traverse.
    - `btnPreviewAdaptive3D` ("⬡ Preview 3D"): Draws the adaptive recovered route on the 3D Three.js terrain mesh.
  - **Staleness Tracking:** Displays amber staleness warning whenever baseline mission parameters or contingency events are modified.

---

## 3. Dedicated Verification Suite (20 Behaviors)

**Test Suite:** `tests/test_milestone_9w_adaptive_replanning.py`  
**Execution Result:** 20 passed in 33.82 seconds.

```
tests/test_milestone_9w_adaptive_replanning.py::test_01_original_inputs_preserved PASSED [  5%]
tests/test_milestone_9w_adaptive_replanning.py::test_02_closed_corridor_produces_event_aware_revised_route PASSED [ 10%]
tests/test_milestone_9w_adaptive_replanning.py::test_03_adaptive_route_avoids_every_blocked_cell PASSED [ 15%]
tests/test_milestone_9w_adaptive_replanning.py::test_04_closure_outside_route_does_not_claim_detour PASSED [ 20%]
tests/test_milestone_9w_adaptive_replanning.py::test_05_unavailable_target_excluded_from_adaptive_itinerary PASSED [ 25%]
tests/test_milestone_9w_adaptive_replanning.py::test_06_reduced_mobility_scales_time_without_altering_geometry PASSED [ 30%]
tests/test_milestone_9w_adaptive_replanning.py::test_07_operational_hold_applied_exactly_once PASSED [ 35%]
tests/test_milestone_9w_adaptive_replanning.py::test_08_reduced_budget_alters_feasibility_correctly PASSED [ 40%]
tests/test_milestone_9w_adaptive_replanning.py::test_09_difficult_terrain_modifies_routing_cost PASSED [ 45%]
tests/test_milestone_9w_adaptive_replanning.py::test_10_science_priority_totals_match_selected_targets PASSED [ 50%]
tests/test_milestone_9w_adaptive_replanning.py::test_11_lost_and_recovered_priority_math_consistent PASSED [ 55%]
tests/test_milestone_9w_adaptive_replanning.py::test_12_over_budget_adaptive_candidate_never_marked_feasible PASSED [ 60%]
tests/test_milestone_9w_adaptive_replanning.py::test_13_adaptive_plan_evaluated_under_identical_disruption_conditions PASSED [ 65%]
tests/test_milestone_9w_adaptive_replanning.py::test_14_deterministic_outputs_and_matching_fingerprints PASSED [ 70%]
tests/test_milestone_9w_adaptive_replanning.py::test_15_api_validation_rejection_invalid_inputs PASSED [ 75%]
tests/test_milestone_9w_adaptive_replanning.py::test_16_recommendation_classification_enums PASSED [ 80%]
tests/test_milestone_9w_adaptive_replanning.py::test_17_workspace_immutability PASSED [ 85%]
tests/test_milestone_9w_adaptive_replanning.py::test_18_three_stage_structure_completeness PASSED [ 90%]
tests/test_milestone_9w_adaptive_replanning.py::test_19_nominal_mission_optimizer_unaffected PASSED [ 95%]
tests/test_milestone_9w_adaptive_replanning.py::test_20_live_http_round_trip_port_3000 PASSED [100%]
```

### Full Regression Suite
- **Command:** `pytest -q`
- **Result:** **319 passed in 131.80s (2 minutes 11 seconds)** across 30 test files.
- **Regressions:** Zero.

---

## 4. Scientific Disclosures & Operational Honesty

In adherence to project rules:
1. **Topographic Data Provenance:** Terrain elevation is derived from USGS Astrogeology Science Center MRO CTX Digital Terrain Model of Jezero Crater Western Delta at 20 m/pixel resolution (projected planar CRS `ESRI:103885`, Mars 2000 Sphere).
2. **Model Transparency:** Science waypoint priority scores are user/curator model inputs, not official NASA scientific rankings.
3. **Operational Boundary:** Modeled routes and adaptive recommendations are research decision-support prototypes and are **never certified as operationally safe for astronaut flight EVA operations**.
4. **Data Integrity:** Historical experiments (11 records) and saved missions (7 records) in `data/workspaces/` remain completely unmutated.
