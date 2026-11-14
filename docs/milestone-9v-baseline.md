# MarsWalk 2.0 — Milestone 9V Baseline & Reconnaissance Report
## Autonomous Science-Tour Optimizer & Intelligent Mission Alternatives

**Milestone:** 9V  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Timestamp:** October 18, 2026 (22:10 UTC)  
**Role:** Principal Aerospace Software Engineer & Mission-Planning Algorithm Designer  

---

## 1. Verified Baseline State

Prior to designing and implementing the autonomous science-tour optimizer and Mission Design Lab, an independent reconnaissance of the active workspace was performed:

| Diagnostic / Metric | Recorded Baseline Value | Status |
| :--- | :--- | :--- |
| **Full Automated Test Suite** | **285 passed** in 75.70s (28 suites) | **100% GREEN** |
| **Preflight System Diagnostics** | **12 / 12 passed** in 675.9ms | **100% READY** |
| **Atlas HTTP Server** | Port 3000 (`http://127.0.0.1:3000`) | **ONLINE** |
| **Terrain Elevation Grid** | USGS MRO CTX Jezero Crater 20m GeoTIFF | **VERIFIED** ($250 \times 250\text{ px}$, SHA-256 intact) |
| **Planetary Gazetteer** | 2,061 IAU Martian landmarks | **VERIFIED** |
| **Jezero Science Waypoints** | 12 curated science targets (`waypoints_jezero.json`) | **VERIFIED** |
| **Workspace Mission Records** | 7 saved missions (`data/workspaces/missions`) | **IMMUTABLE** |
| **Workspace Experiment Records** | 11 historical experiments (`data/workspaces/experiments`)| **IMMUTABLE** |
| **Git Working Tree** | Clean working state | **PRESERVED** |

---

## 2. Codebase Reconnaissance & Gap Analysis

### 2.1 Existing Multi-Stop Routing & Science Budget Logic
- **`src/marswalk/core/planner.py`:**
  - Implements `plan_sequential_multistop_route` which takes a predetermined list of `ordered_points: List[Tuple[int, int]]`, calls A* for each leg, stitches the path, and builds a `MissionTimeline`.
  - Implements `optimize_stop_order`: Given a fixed set of stops, it optimizes the permutation order via TSP (exact permutation for $K \le 7$, 2-Opt for $K > 7$).
  - **Limitation:** Requires the user to have already manually picked the exact set of stops. It does not select *which* stops to visit out of a larger candidate catalogue.
- **`src/marswalk/core/science_budget.py`:**
  - Contains `evaluate_all_candidate_plans` which evaluates all $2^K$ combinations for up to $K = 6$ waypoints.
  - **Limitation:** Fails to scale beyond 6 waypoints (combinatorial explosion: $2^{12} = 4,096$ subsets, with TSP permutations exceeding millions of calculations). Does not model operational time budgets (crew EVA vs rover velocities, Minetti metabolic slope effort, dwell times, operational holds). Only compares physical distance vs raw science score.
- **Frontend (`web/index.html`, `web/app.js`):**
  - Users currently have to manually click each waypoint or select from a dropdown one by one.
  - No interactive Mission Design Lab exists to evaluate alternative sorties, inspect Pareto trade-offs, or choose from intelligently ranked candidate missions.

---

## 3. Milestone 9V Architectural Blueprint

### 3.1 New Core Module: `src/marswalk/core/mission_optimizer.py`
A dedicated, bounded-search science tour optimizer:
1. **Inputs:** Departure and destination coordinates, candidate science waypoints, maximum stops limit, operational time budget (`operational_limit_s`), distance budget (`max_distance_m`), dwell time per stop (`dwell_time_per_stop_s`), vehicle mode (`crew_eva` vs `robotic_rover`), speed multiplier, and planning profile (`conservative`, `balanced`, `science_first`).
2. **Pairwise Directed Leg Caching:** Precomputes A* legs between all unique nodes on the active terrain, avoiding repeated search.
3. **Bounded Beam Search:** Iteratively expands partial tours level by level with a configurable beam width ($B = 12$), evaluating path continuity, ground distance, terrain effort, science sum, travel time, and operational feasibility.
4. **Multi-Objective Champion Synthesis:**
   - **Science Priority Champion:** Maximizes total science priority points within budget.
   - **Time Efficiency Champion:** Maximizes science return per unit mission time (`science_score / total_mission_time_s`).
   - **Balanced Trade-off Champion:** Compromises between science score, route distance, and operational time margin.
   - **Direct Nominal Sortie (Baseline):** 0-stop direct baseline reference.
5. **Pareto Frontier Extraction:** Identifies 2D (time vs science) and 3D (time, terrain cost, science) non-dominated candidates.
6. **Authoritative Route Verification:** Passes the champion candidates through `plan_sequential_multistop_route` to guarantee exact coordinate geometry, slope limits, cumulative climb, and leg-by-leg timeline fidelity.

### 3.2 API Integration
- Add `POST /api/mission/optimize` to `src/marswalk/api/service.py` and `scripts/run_atlas.py`.
- Schema validation, input sanitization, error codes, and computation fingerprinting.

### 3.3 UI Integration: Mission Design Lab
- Integrate a Mission Design Lab card into `web/index.html` (within Tab 1: Plan).
- Multi-select candidate waypoints, configure operational limits, trigger sortie generation, inspect alternatives in a comparison table, preview 3D route on the Jezero DTM, and apply the chosen sortie to the active mission.
