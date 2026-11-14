# MarsWalk 2.0 — Milestone 9Y Baseline Audit & Architectural Assessment
## Explainable Terrain Intelligence, Route Cost Attribution & Mission Decision Support

**Milestone:** 9Y  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** October 19, 2026  
**Auditor & Lead:** Principal Aerospace Software Engineer, Terrain-Analysis Specialist, Explainable Optimization Researcher & Three.js Integration Engineer  

---

## 1. Initial State Verification

Before designing and implementing Milestone 9Y, the repository state was independently audited and verified:

- **Full Pytest Suite:**
  - **337 / 337 tests PASSED** in 132.35s across 31 test suites.
  - Zero test failures, zero regressions, zero skipped required tests.
- **Preflight Diagnostics (`scripts/preflight_check.py`):**
  - **12 / 12 checkpoints PASSED** in 401.7 ms.
  - Server online on port 3000.
  - Jezero 20m CTX DTM verified (250x250 px, GeoTIFF elevation grid).
  - Workspace storage verified: 7 saved missions, 11 historical experiments preserved without mutation.
- **Milestone 9X Mission Robustness Lab Verified:**
  - `POST /api/mission/robustness` functioning with deterministic sweep grids (budgets, speed derating, closure radius, target drops).
  - Robustness score ($N_{\text{feasible}} / N_{\text{tested}}$) with clear disclaimer that sensitivity analysis is not empirical probability or certified safety.

---

## 2. Terrain Cost Model Inspection

We audited `src/marswalk/core/terrain.py` and `src/marswalk/core/planner.py` to identify the authoritative physical and mathematical relationships governing route planning:

### 2.1 Directed Edge Cost Formulation
In `calculate_edge_cost(u, v, terrain, config)`:
$$C(u \to v) = d(u, v) \cdot \left[ 1.0 + \alpha_s \left(\frac{\theta}{\theta_{\text{crit}}}\right)^2 + \alpha_r \left(\frac{\sigma}{\sigma_0}\right) + \alpha_{\text{up}} \max\left(0, \frac{\Delta z}{d}\right) \right] \cdot M_{\text{contingency}}(v)$$

Where:
- $d(u, v)$ is the Euclidean ground step distance in meters: $\sqrt{dx^2 + dy^2}$ (horizontal grid step with cell dimensions $dx=20\text{m}, dy=20\text{m}$).
- $\theta = \arctan(|\Delta z| / d)$ is the slope angle in radians.
- If $\theta \ge \theta_{\text{max}}$, the step is impassable ($C = \infty$).
- $\sigma$ is surface roughness from CTX DTM standard deviation / slope variance.
- $\Delta z / d$ is the directional grade. Uphill steps ($\Delta z > 0$) incur an additional climbing effort penalty $\alpha_{\text{up}}$.
- $M_{\text{contingency}}(v)$ is the spatial cost multiplier mask applied by disruptions (e.g. rough ejecta field, sand dune traverse).
- If cell $v$ is inside a blocked corridor, $C = \infty$.

### 2.2 Traverse Time Formulation
Traverse time is not a naive linear function of ground distance; it is directly coupled to modeled terrain traversal cost:
$$T_{\text{traverse}} = \frac{C_{\text{route}}}{v_{\text{effective}}} = \frac{\sum_{i=1}^{N-1} C(u_i \to u_{i+1})}{v_{\text{nominal}} \cdot \mu_{\text{speed}}}$$
Where:
- $v_{\text{nominal}}$ depends on the mobility mode (e.g., EVA Astronaut Walking = 0.8 m/s, Pressurized Rover = 4.2 m/s).
- $\mu_{\text{speed}}$ is the contingency speed multiplier (e.g. 0.65 for wheel motor degradation).

### 2.3 Mathematical Additivity vs Non-Additivity
- **Strictly Additive Metrics along a Discrete Route:**
  - Route Ground Distance: $D_{\text{total}} = \sum_{k=1}^K D_k$
  - Route Modeled Cost: $C_{\text{total}} = \sum_{k=1}^K C_k$
  - Elevation Gain: $\Delta Z_{\text{gain, total}} = \sum_{k=1}^K \Delta Z_{\text{gain}, k}$
  - Elevation Loss: $\Delta Z_{\text{loss, total}} = \sum_{k=1}^K \Delta Z_{\text{loss}, k}$
- **Non-Additive (Path-Dependent & Extrema) Metrics:**
  - Maximum Slope: $\theta_{\max} = \max_k (\theta_{\max, k})$ (cannot be averaged or summed).
  - Mean Slope: Distance-weighted average $\bar{\theta} = \frac{\sum_k \bar{\theta}_k \cdot D_k}{D_{\text{total}}}$.
  - Cost Density / Impedance Ratio: $\frac{C_{\text{total}}}{D_{\text{total}}}$, representing the equivalent flat-ground effort multiplier.

---

## 3. The Explainability Gap

While MarsWalk plans optimal routes via A* and evaluates scenarios, until now the interface has only shown the final path geometry and aggregate metrics (total distance, total time, max slope). 

Users, flight controllers, and competition judges have been unable to inspect:
1. **Cost Attribution:** Exactly which segments of the route accumulated the bulk of the traversal cost and time?
2. **Terrain Factors:** Was a segment costly due to steep slopes, surface roughness, climbing elevation, or a disruption multiplier?
3. **Alternative & Detour Rationale:** When a detour was selected around a crater or closed corridor, why did the planner choose that specific path instead of an alternative ridge or valley?
4. **Profile & Vehicle Sensitivity:** How does changing from Astronaut EVA to Pressurized Rover alter the segment cost profile?
5. **Reconciliation Ledger:** A verifiable mathematical proof demonstrating that segment-level metrics reconcile cleanly to total route metrics.

---

## 4. Milestone 9Y Architecture & Deliverables

1. **Core Explainability Engine (`src/marswalk/core/route_explainer.py`):**
   - Detailed segment decomposition (10 uniform route segments, plus multi-stop leg decomposition).
   - Component cost breakdown (base ground distance, slope penalty, roughness penalty, uphill penalty, contingency multiplier).
   - Dominant cost factor classification (`slope`, `roughness`, `uphill`, `base_distance`, `contingency_multiplier`).
   - Terrain difficulty classification (`nominal`, `moderate`, `challenging`, `severe`).
   - Route reconciliation ledger proving $\sum D_k = D_{\text{total}}$ and $\sum C_k = C_{\text{total}}$.
   - Top-K highest-cost bottleneck identification with actionable operational explanations.
   - Comparative explanation engine comparing reference routes vs detours / vehicle modes / Pareto alternatives.
2. **API & Contract Registration:**
   - JSON Schema: `schemas/api/v1/route-explanation-response.schema.json`.
   - Contract registry update: `src/marswalk/api/contracts.py`.
   - API Handler: `route_explain_api` in `src/marswalk/api/service.py`.
   - Atlas server route: `POST /api/route/explain` in `scripts/run_atlas.py`.
3. **UI Integration:**
   - Route Cost Profile & Segment Inspector Card in `web/index.html`.
   - Visual styling in `web/styles.css` (cost density bar chart, dominant factor badges, interactive segment cards).
   - Frontend logic in `web/app.js`: Interactive click to highlight segments in 3D Three.js terrain mesh, baseline vs detour comparison toggle, full window export.
4. **Comprehensive Test Suite (`tests/test_milestone_9y_route_explainer.py`):**
   - 15+ rigorous regression and verification tests.
   - Verification of mathematical reconciliation, non-negativity, ranking correctness, leg alignment, contingency sensitivity, and API contract compliance.
