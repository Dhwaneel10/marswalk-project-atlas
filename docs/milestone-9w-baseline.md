# MarsWalk 2.0 — Milestone 9W Baseline Reconnaissance & Audit Report
## Adaptive Mission Replanning, Science Recovery & Disruption-Aware Optimization

**Milestone:** 9W (Phase 1 Baseline Audit)  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** October 18, 2026 (Local: October 19, 2026)  
**Lead Auditor:** Principal Aerospace Software Engineer & Scientific Computing Auditor  

---

## 1. System Health & Baseline Verification

Prior to development on Milestone 9W, an independent audit of the repository, test suites, preflight checkpoints, and algorithmic interfaces was executed:

| Inspection Area | Baseline Metric / State | Status |
| :--- | :--- | :--- |
| **Full Automated Test Suite** | 299 tests passed across 29 test suites in 90.60s | **100% GREEN** |
| **Preflight System Diagnostics** | 12 / 12 checkpoints verified in 437.8 ms | **100% READY** |
| **HTTP API Server** | Port 3000 running in background (Mars IAU 2000 Sphere) | **ACTIVE** |
| **Jezero DTM Topography** | Authentic USGS MRO CTX 20m GeoTIFF (250x250 px, SHA-256 `875e7e...`) | **VERIFIED** |
| **Gazetteer & Planetary Catalog** | 2,061 IAU approved Martian landmarks + 9 imagery products | **VERIFIED** |
| **Persistent Workspace Records** | 7 saved missions, 11 historical experiments preserved | **UNMUTATED** |

---

## 2. Technical Audit of Existing Engines

### 2.1 Mission Optimizer Audit (`src/marswalk/core/mission_optimizer.py`)
- **Current Capability:** Autonomously discovers and ranks nominal multi-stop scientific sorties using bounded beam search ($B=12..30$) over pairwise directed $A^*$ leg caches. Synthesizes 4 champions (Direct Baseline, Science Priority, Time Efficiency, Balanced) plus non-dominated Pareto alternatives in $< 500\text{ ms}$.
- **Architectural Limitation:** `optimize_science_tour()` evaluates candidate routes strictly in an **unperturbed, nominal environment**. It accepts `start_rc`, `goal_rc`, `terrain`, `candidate_waypoints`, `profile`, `vehicle_mode`, and budgets, but **does NOT accept** disruption masks (`blocked_mask`, `cost_multiplier_mask`), modified terrain configurations (`terrain_config`), unavailable targets, or custom contingency definitions.
- **Verdict:** The existing optimizer is strictly a nominal planner; it is not disruption-aware.

### 2.2 Contingency & Stress-Testing Audit (`src/marswalk/core/contingency.py` & `src/marswalk/core/stress_test.py`)
- **Current Capability:** Validates and compiles 1 to 3 custom contingency events:
  1. `closed_corridor`: Spatial impassable obstacle circle with `blocked_cells`.
  2. `difficult_terrain`: Spatial impedance circle with `cost_multiplier_cells`.
  3. `reduced_mobility`: Locomotion speed scaling ($0.05 \le \text{mult} \le 1.0$) and slope penalty scaling ($1.0 \le \text{mult} \le 3.0$).
  4. `reduced_time_budget`: Percentage cut ($1\%..95\%$) or absolute duration ceiling.
  5. `operational_hold`: Unplanned communications / diagnostic hold delay ($> 0\text{ s}$).
  6. `target_unavailable`: Exclusion of a specific science waypoint due to localized dust or instrument failure.
- `run_scenario()` evaluates the disruption against a **single pre-existing route** to calculate detour distance, duration deltas, and feasibility.
- **Architectural Limitation:** It evaluates the disruption on the *current* itinerary, and can propose single-leg local detours or target drops, but **cannot explore the global space of alternative multi-stop science tours** under the disruption to recover lost science objectives.

### 2.3 Core Planner Capabilities (`src/marswalk/core/planner.py`)
- **Foundational Functions:**
  - `compute_pairwise_leg_cache()`: Already accepts `blocked_mask`, `cost_multiplier_mask`, and `terrain_config`.
  - `astar_search()`: Naturally routes around cells marked in `blocked_mask` and penalizes cells in `cost_multiplier_mask`.
  - `plan_sequential_multistop_route()`: Already supports `blocked_mask`, `cost_multiplier_mask`, `terrain_config`, `vehicle_mode`, `speed_multiplier`, `operational_delay_s`, and `operational_limit_s`.

---

## 3. The Milestone 9W Objective & Essential Distinction

A system that first optimizes a nominal mission and only afterward displays how a disruption affects it is **not** a disruption-aware optimizer.

To answer the operational question:
> **"When a disruption occurs, should the current mission continue, change its route, remove a target, or be replaced with a different science tour?"**

Milestone 9W will build an **Adaptive Mission Replanner** (`src/marswalk/core/adaptive_replanner.py`) executing a three-stage comparison:
1. **Stage 1 — Original Plan:** The nominal mission selected before the disruption.
2. **Stage 2 — Disrupted Plan:** The original itinerary evaluated under the actual disruption conditions.
3. **Stage 3 — Adaptive Plan:** A newly optimized itinerary generated under the **exact same disrupted conditions**, exploring alternative science targets to recover lost priority within the remaining budget.

### Quantitative Science Recovery Metrics
- Original Selected Priority: $P_{orig} = \sum_{w \in \pi_{orig}} \text{score}(w)$
- Disrupted Retained Priority: $P_{disr} = \sum_{w \in \pi_{disr}} \text{score}(w)$
- Adaptive Plan Priority: $P_{adapt} = \sum_{w \in \pi_{adapt}} \text{score}(w)$
- Priority Lost: $\Delta P_{lost} = \max(0, P_{orig} - P_{disr})$
- Priority Recovered: $\Delta P_{rec} = \max(0, P_{adapt} - P_{disr})$
- Science Recovery Efficiency: $\eta_{rec} = \frac{\Delta P_{rec}}{\Delta P_{lost}}$ (when $\Delta P_{lost} > 0$)

---

## 4. Phase 2 Implementation Roadmap
1. Develop `src/marswalk/core/adaptive_replanner.py` with `AdaptiveReplanningResult`, `ScienceRecoverySummary`, and `replan_adaptive_mission()`.
2. Integrate disruption parameters into beam search candidate evaluation and leg caching.
3. Expose REST API endpoint `POST /api/mission/replan` in `src/marswalk/api/service.py` and `scripts/run_atlas.py`.
4. Implement Adaptive Mission Operations UI in `web/index.html`, `web/styles.css`, and `web/app.js`.
5. Author comprehensive test suite `tests/test_milestone_9w_adaptive_replanning.py` covering all 20 required behaviors.
6. Verify full regression suite, preflight check, and document results.
