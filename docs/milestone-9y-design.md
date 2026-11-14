# MarsWalk 2.0 — Milestone 9Y Architectural Design Specification
## Explainable Terrain Intelligence, Route Cost Attribution & Mission Decision Support

**Milestone:** 9Y  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** October 19, 2026  
**Architect:** Principal Aerospace Software Engineer, Terrain-Analysis Specialist, Explainable Optimization Researcher & Three.js Integration Engineer  

---

## 1. Executive Summary

Milestone 9Y equips MarsWalk 2.0 with an authoritative **Explainable Route Decision Engine**. While earlier milestones delivered optimal pathfinding, multi-stop tour optimization, adaptive replanning, and robustness sensitivity sweeps, the algorithmic reasons behind route selections remained opaque.

Milestone 9Y answers six foundational mission-planning questions directly from physical equations and DTM raster data:
1. **Why did the planner choose this route?** Grounded in 8-connected A* cost minimization, profile slope limits ($\theta_{\max}$), and hazard avoidance.
2. **Which terrain segments contribute most to its modeled travel cost and traversal effort?** Decomposing continuous routes into auditable segments with cost density ($C/d$) and dominant factor classification.
3. **What changes when planning profiles or vehicle modes change?** Directly attributing variations in slope penalties, roughness impedance, and speed multipliers.
4. **Which alternative routes offer different distance-versus-cost trade-offs?** Explicitly contrasting lateral distance deltas against climbing slope relief.
5. **How did a disruption change the route's geometry, cost, and explanation?** Tracking spatial divergence/convergence steps and quantifying detour efficiency.
6. **Can a teammate or competition judge inspect the evidence behind a recommendation?** Proving route totals match segment sums down to numerical tolerances ($10^{-5}$) in a mathematical reconciliation ledger.

---

## 2. Mathematical Formulation & Additive Cost Decomposition

### 2.1 Primary Directed Edge Cost Equation
For adjacent cells $u = (r_1, c_1)$ and $v = (r_2, c_2)$ on an 8-connected grid with ground pixel spacing $dx_{\text{ground}}, dy_{\text{ground}}$:
$$d(u, v) = \sqrt{((c_2 - c_1) \cdot dx_{\text{ground}})^2 + ((r_2 - r_1) \cdot dy_{\text{ground}})^2}$$

Elevation change: $\Delta z = z(v) - z(u)$.  
Direct step slope angle: $\theta_{\text{step}} = \arctan(|\Delta z| / d(u, v)) \cdot \frac{180}{\pi}$.  
Destination cell Horn slope: $\theta_v = \text{slope\_deg}[v]$.  
Effective step slope: $\theta_{uv} = \max(\theta_v, \theta_{\text{step}})$.

Cutoff slope threshold: If $\theta_{uv} \ge \theta_{\max}$, $C(u \to v) = \infty$ (impassable cliff).

Dimensionless terrain penalty components:
- Slope penalty: $P_{\text{slope}} = \alpha_s \cdot \left(\frac{\theta_{uv}}{\theta_{\text{crit}}}\right)^2$
- Roughness penalty: $P_{\text{rough}} = \alpha_r \cdot \left(\frac{\sigma_v}{\sigma_0}\right)$
- Uphill grade penalty: $P_{\text{up}} = \alpha_{\text{up}} \cdot \max\left(0, \frac{\Delta z}{d(u, v)}\right)$

Base bracket:
$$B(u, v) = 1.0 + P_{\text{slope}} + P_{\text{rough}} + P_{\text{up}}$$
Base traversal cost:
$$C_{\text{base}}(u \to v) = d(u, v) \cdot B(u, v)$$

Contingency hazard multiplier:
$$M_{\text{contingency}}(v) = \max(1.0, \text{cost\_multiplier\_mask}[v])$$
Effective directed step cost:
$$C(u \to v) = C_{\text{base}}(u \to v) \cdot M_{\text{contingency}}(v)$$

### 2.2 Exact Additive Component Breakdown
To explain traversal cost without hand-waving, every step's cost is broken down additively into five disjoint terms:
$$C(u \to v) = C_{\text{dist}} + C_{\text{slope}} + C_{\text{rough}} + C_{\text{uphill}} + C_{\text{contingency}}$$
Where:
- $C_{\text{dist}} = d(u, v) \cdot 1.0$ (flat ground base distance)
- $C_{\text{slope}} = d(u, v) \cdot P_{\text{slope}}$ (effort to traverse slope)
- $C_{\text{rough}} = d(u, v) \cdot P_{\text{rough}}$ (effort to overcome surface roughness)
- $C_{\text{uphill}} = d(u, v) \cdot P_{\text{up}}$ (effort to climb directional grade)
- $C_{\text{contingency}} = C_{\text{base}}(u \to v) \cdot (M_{\text{contingency}}(v) - 1.0)$ (excess effort induced by contingency hazard)

**Theorem:**
$$\sum_{\text{components}} C_k = C(u \to v)$$
Holds identically at every step, every aggregated segment, and the entire route.

---

## 3. Segment Partitioning & Aggregation Engine

### 3.1 Partitioning Modes
1. **Multi-Stop Leg Alignment:** When a route includes intermediate science targets, segment boundaries naturally align to leg endpoints: Departure $\to W_1 \to W_2 \to \dots \to$ Destination.
2. **Uniform-Chunk Decomposition:** For single-leg traverses, the route's $N$ discrete steps are partitioned into $K$ contiguous slices (default $K=10$), guaranteeing:
   $$\bigcup_{j=1}^K S_j = \text{Path Steps}, \quad S_j \cap S_k = \emptyset \quad (j \ne k)$$

### 3.2 Segment Attributes
For each segment $j$:
- Step range: $[s_{\text{start}}, s_{\text{end}}]$
- Coordinates: start $(r_{\text{start}}, c_{\text{start}})$, end $(r_{\text{end}}, c_{\text{end}})$
- Ground distance: $D_j = \sum_{i \in S_j} d_i$
- Traversal effort: $C_j = \sum_{i \in S_j} C_i$
- Effort fraction: $F_j = \frac{C_j}{C_{\text{total}}} \cdot 100\%$
- Cost density ratio: $\rho_j = \frac{C_j}{D_j}$ (dimensionless multiplier of flat-ground effort)
- Topographic bounds: $\min(z), \max(z), \Delta z = z_{\text{end}} - z_{\text{start}}$, cumulative climb, cumulative descent
- Extreme slope: $\theta_{\max, j} = \max_{i \in S_j} \theta_i$
- Mean slope: $\bar{\theta}_j = \frac{\sum_{i \in S_j} \theta_i \cdot d_i}{D_j}$ (distance-weighted)
- Dominant factor: Selected among `slope`, `roughness`, `uphill`, `contingency_multiplier` if any non-base term contributes $\ge 12\%$ of segment effort, else `base_distance`.
- Difficulty classification:
  - `nominal`: $\rho_j < 1.30$
  - `moderate`: $1.30 \le \rho_j < 2.00$
  - `challenging`: $2.00 \le \rho_j < 3.50$
  - `severe`: $\rho_j \ge 3.50$

---

## 4. Mathematical Reconciliation Ledger

The reconciliation ledger (`RouteCostLedger`) provides irrefutable proof that segment statistics aggregate precisely to overall route telemetry:

$$\Delta_{\text{dist}} = \left| \sum_{j=1}^K D_j - D_{\text{total}} \right| \le \epsilon$$
$$\Delta_{\text{cost}} = \left| \sum_{j=1}^K C_j - C_{\text{total}} \right| \le \epsilon$$
$$\Delta_{\text{comp}} = \left| \sum_{k} C_{\text{comp}, k} - C_{\text{total}} \right| \le \epsilon$$
Where $\epsilon = 0.05$ m tolerance (typically $< 10^{-12}$ m floating point residue).

### Explicit Non-Additive Disclosures
The ledger explicitly flags non-additive quantities to prevent fallacious averaging:
- Maximum slope ($\theta_{\max}$) is a supremum, not an additive sum.
- Elevation bounds ($z_{\min}, z_{\max}$) are topological extrema.
- Cost density ($\rho = C / D$) is an impedance ratio.

---

## 5. Decision Rationale & Comparative Trade-Offs

### 5.1 Rationale Generation
The engine deterministically explains route geometry by auditing:
- Optimization objective: A* global cost minimization under profile constraints.
- Avoided hazards: Cliffs steeper than $\theta_{\max}$ (e.g., 16° for conservative, 25° for science-first), invalid DTM pixels, active contingency corridors.
- Accepted trade-offs: Lateral detour distance added ($+X$m, $+Y\%$) to remain on gentle contours below the cliff cutoff.

### 5.2 Comparative Route Analysis
When contrasting a reference route against an alternative or detour:
- Divergence index: First step $i_{\text{div}}$ where paths separate.
- Convergence index: Final step $i_{\text{conv}}$ where paths reunite.
- Quantitative deltas: $\Delta D, \Delta C, \Delta T, \Delta \theta_{\max}$.
- Trade-off verdict: Deterministically explaining whether the alternative saves effort, incurs a detour penalty, or trades distance for slope relief.

---

## 6. Software Architecture & API Endpoints

```
[Web UI (Three.js Atlas)]
     |
     v  POST /api/route/explain
[Atlas HTTP Dispatcher (run_atlas.py)]
     |
     v
[API Service Handler (service.py: route_explain_api)]
     |
     +--> parse_endpoint_rc / unpack route payload
     +--> optional compile_custom_contingency
     +--> marswalk.core.route_explainer.explain_route()
     |       |
     |       +--> compute_step_attributions()
     |       +--> decompose_route_segments()
     |       +--> reconcile_route_cost_ledger()
     |       +--> rank_highest_cost_segments()
     |       +--> generate_decision_rationale()
     |       +--> compare_routes_explained()
     |
     +--> JSON Schema Draft 2020-12 validation (route-explanation-response.schema.json)
     +--> sanitize_for_json RFC 8259
     |
     v  200 OK JSON
[Web UI: Render Reconciliation Ledger, Bottleneck Cards, 3D Segment Highlight Mesh]
```

---

## 7. Scientific Non-Negotiables & Disclaimers

1. **Deterministic Attribution:** Traversal effort is calculated directly from USGS CTX 20m DTM elevation matrices and calibrated slope formulas. No synthetic post-hoc narratives.
2. **Units:** Traversal costs are strictly expressed in **meters of equivalent flat-terrain effort**.
3. **No Operational Safety Claims:** Modeled terrain impedance is an algorithmic metric, **never a certified operational safety envelope for human astronauts**.
