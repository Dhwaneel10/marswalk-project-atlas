# MarsWalk 2.0 — Milestone 9R Design Document
## Interactive Contingency Designer, Compound Mission Events, and Real-Time What-If Analysis

**Author:** Principal Aerospace Software Engineer, Planetary Robotics Mission Planner, Simulation Engineer, Three.js Interaction Developer, and Verification Lead  
**Status:** Implemented & Verified  
**Milestone:** 9R  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`

---

## 1. Architectural Overview

Milestone 9R establishes the **Interactive Mission Contingency Designer** within MarsWalk's mission control workspace (`web/index.html`, `web/app.js`, `src/marswalk/core/contingency.py`, `src/marswalk/api/service.py`). 

Prior to Milestone 9R, MarsWalk supported curated, predefined disruption scenarios (e.g. Scenario A rockfall, Scenario D actuator derating). While scientifically robust, mission planners could not stage hypothetical hazards at arbitrary user-selected coordinates, tune severity sliders, or combine cascading failures (e.g. a blocked canyon combined with degraded mobility and an emergency communications hold).

The Milestone 9R architecture introduces an authoritative, validated multi-event engine that adheres strictly to planetary physics, terrain constraints, and NASA mission-planning semantics.

```
       ┌────────────────────────────────────────────────────────┐
       │                MarsWalk 3D Frontend                   │
       │  (Three.js Mesh + HUD Inspector: Scenarios Workspace)  │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                   Staged Events & Spatial Overlays
                                  │
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │             FastAPI / Atlas HTTP Server                │
       │          POST /api/contingency/simulate                │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                        Validated Event Schema
                                  │
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │              Custom Contingency Engine                 │
       │            (marswalk.core.contingency)                 │
       │  - Circular Footprint Metric Projection                │
       │  - Multi-Event Compatibility & Conflict Matrix         │
       │  - Single / Compound Scenario Definition Compiler      │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                     Authoritative ScenarioDefinition
                                  │
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │               Gauntlet Stress-Test Core                │
       │             (marswalk.core.stress_test)                │
       │  - Non-Geometric Detour Invariance Preserver           │
       │  - Multi-Stop Sequential Detour Re-Planner             │
       │  - Regret Ledger & Priority Loss Tracking              │
       │  - 3-Way Recovery Recommendation Engine                │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                   ScenarioComparison & RouteResult
                                  │
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │         Synthesis & Evidence-Based Reporting           │
       │  - 8-Row Comparison Table (Baseline vs Scenario vs Δ)  │
       │  - Truth-Telling Narrative Synthesizer                 │
       │  - 3D Geographic Coordinate Overlays                   │
       │  - Immutable Experiment Record Persistence             │
       └────────────────────────────────────────────────────────┘
```

---

## 2. Event Taxonomy & Mathematical Specifications

Milestone 9R formalizes six canonical event types (`CustomEventType`):

| Event Type | Key | Spatial? | Invariant Geometry? | Governing Parameters | Planner Behavior |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **Event A: Closed Corridor** | `closed_corridor` | Yes | No | Center $(r, c)$, Radius $R$ (m) | Enclosed grid cells marked impassable (`blocked_cells`). A* finds optimal physical detour; fails with `is_feasible = False` if goal/start is severed. |
| **Event B: Difficult Terrain** | `difficult_terrain` | Yes | Depends | Center $(r, c)$, Radius $R$ (m), Cost Multiplier $k \in (1.0, 10.0]$ | Cell cost multiplied by $k$. Planner evaluates whether to detour around or traverse with elevated effort/energy. |
| **Event C: Reduced Mobility** | `reduced_mobility` | No | Yes | Speed Multiplier $s \in [0.05, 1.0]$, Slope Penalty Multiplier $p \in [1.0, 3.0]$ | Physical path geometry is 100% identical (0.0 m net detour). Travel time expanded by factor $1/s$ with additional slope drag. |
| **Event D: Reduced Time Budget**| `reduced_time_budget`| No | Depends | Budget Cut Pct $b \in [1.0, 95.0]\%$ or Ceiling $T_{max}$ (s) | Expedition time ceiling lowered. If existing timeline exceeds new budget, optimizer drops distal science targets or flags mission infeasible. |
| **Event E: Operational Hold** | `operational_hold` | No | Yes | Delay $t_{hold}$ (min or s) | Zero geometric detour. Adds explicit stationary delay segment to timeline and decrements remaining margin. |
| **Event F: Science Target Inaccessible** | `target_unavailable` | No | No | Target ID $T_{dropped}$ | Dropped waypoint bypassed. Planner recalculates leg sequence without $T_{dropped}$; regret ledger records forfeited priority. |

---

## 3. Spatial Footprint Calculation on Mars Geodesic Grids

Spatial events (Closed Corridor and Difficult Terrain) require converting metric radius $R$ into discrete grid coordinates $(r, c)$ without distorting physical distances on Mars.

Given reference grid cell spacing $\Delta x_{ground}$, $\Delta y_{ground}$ (nominally 20.0 m for Jezero CTX DTM):
$$\Delta r = (r - r_0) \cdot \Delta y_{ground}$$
$$\Delta c = (c - c_0) \cdot \Delta x_{ground}$$
$$D^2(r, c) = \Delta r^2 + \Delta c^2 \le R^2$$

The algorithm calculates the integer bounding box:
$$\text{span}_r = \lceil R / \Delta y_{ground} \rceil + 1, \quad \text{span}_c = \lceil R / \Delta x_{ground} \rceil + 1$$
and evaluates circular distance strictly in Euclidean ground meters. If `dx_ground_m` or `dy_ground_m` are `None` (uniform isotropic grid), the algorithm safely defaults to `cell_size_m` (20.0 m), preventing runtime `TypeError`.

---

## 4. Compound Scenario Synthesis & Compatibility Rules

Planners can stage **up to 3 concurrent events**. The compiler (`compile_custom_contingency`) enforces the following synthesis rules:

1. **Spatial Overlay Union:**
   - Multiple `closed_corridor` events merge their `blocked_cells` sets.
   - Overlapping `difficult_terrain` events take the maximum cost multiplier: $k_{eff} = \max(k_1, k_2)$.
   - If a cell is both `closed_corridor` and `difficult_terrain`, impassability takes precedence (`blocked_cells` wins).
2. **Speed & Mobility Composition:**
   - Multiple mobility events compose multiplicatively: $s_{eff} = s_1 \cdot s_2$ (clamped to $[0.05, 1.0]$).
3. **Operational Delay Accumulation:**
   - Multiple operational holds sum additively: $t_{delay, total} = \sum t_{hold, i}$.
4. **Budget Reduction:**
   - Budget cuts compose to the most restrictive ceiling: $T_{limit, eff} = \min(T_{limit, 1}, T_{limit, 2})$.
5. **Conflict Resolution:**
   - Duplicate target drops for the identical target ID are rejected during validation.
   - Compounding more than 3 events raises `ValueError("Maximum 3 concurrent events supported")`.

---

## 5. Eight-Measurement Comparison Table Specification

The comparison engine generates a strictly deterministic 8-row table comparing the nominal baseline traverse against the simulated contingency scenario:

| # | Metric Name | Unit | Difference Calculation | Favorable Direction |
| :---: | :--- | :--- | :--- | :---: |
| 1 | **Route distance** | meters | $\Delta d = d_{scenario} - d_{baseline}$ | Negative ($\Delta d < 0$) |
| 2 | **Terrain-adjusted effort** | flat-m | $\Delta c = c_{scenario} - c_{baseline}$ | Negative ($\Delta c < 0$) |
| 3 | **Estimated active traverse time** | time | $\Delta t_{trav} = t_{trav, scen} - t_{trav, base}$ | Negative ($\Delta t_{trav} < 0$) |
| 4 | **Total mission duration** | time | $\Delta T = T_{total, scen} - T_{total, base}$ | Negative ($\Delta T < 0$) |
| 5 | **Available mission time** | time | $\Delta T_{limit} = T_{limit, scen} - T_{limit, base}$ | Neutral |
| 6 | **Remaining time margin** | time | $\Delta M = M_{scen} - M_{base}$ | Positive ($\Delta M > 0$) |
| 7 | **Science objectives retained** | count | $\Delta N = N_{scen} - N_{base}$ | Positive ($\Delta N \ge 0$) |
| 8 | **Mission feasibility** | status | Feasibility status comparison | Compliant vs Infeasible |

Percentage changes are computed via `_safe_pct_delta(current, baseline)`, which guarantees zero division and non-finite numbers never yield `NaN`, `Infinity`, or fake `0.0%` artifacts.

---

## 6. Truth-Telling Narrative Synthesizer

The narrative generator produces grounded, factual text directly derived from the calculated numerical fields:
- **Detour Bypasses Obstacle:** If $\Delta d > 0$, states exact detour meters and minutes added.
- **Local Obstacle Bypassed with Zero Net Detour:** If an obstacle was placed on the nominal path but an alternative parallel grid track has identical distance, explicitly clarifies: `"Local Obstacle Bypassed (0 m net detour: local path skirted obstacle footprint without extending gross distance)"`.
- **Non-Intersecting Event:** If the event footprint does not intersect the route, explicitly clarifies: `"No Route Impact (does not intersect nominal traverse corridor)"`.
- **Pure Operational Event:** For mobility derating or hold, highlights that physical geometry remained 100% invariant (0.0 m detour).
- **Dropped Waypoints:** Explicitly names each dropped waypoint and quotes retained priority percentage from the regret ledger.
- **Infeasibility:** If the destination is walled off or the time budget is exceeded, provides an unambiguous warning and recovery advice.
- **Non-Safety Disclosure:** Appends the standard scientific disclosure: `"Modeled for what-if mission rehearsal, not certified operational safety."`

---

## 7. Persistence & Immutable Experiment Library

Custom contingency runs can be saved to the Experiment Library via `/api/experiments`:
- Saved records strictly conform to `schemas/api/v1/saved-experiment.schema.json`.
- The compound scenario is serialized under `scenarios_evaluated` with `is_custom_contingency = True` and the full list of `custom_events`.
- Once written to disk (`data/experiments/exp_*.json`), the records are immutable and can be reloaded or replayed across user sessions.
