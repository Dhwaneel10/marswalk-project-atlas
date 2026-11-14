# MarsWalk 2.0 — Milestone 9W Architecture & Engineering Design
## Adaptive Mission Replanning, Science Recovery & Disruption-Aware Optimization

**Document:** `docs/milestone-9w-design.md`  
**Milestone:** 9W  
**Author:** Principal Aerospace Software Engineer & Scientific Computing Lead  
**Target:** NASA Space Apps Challenge 2026 — Planetary Surface Traverses  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  

---

## 1. Architectural Motivation & Problem Statement

Prior to Milestone 9W, MarsWalk provided two separate mission capabilities:
1. **Interactive Mission Design Lab (Milestone 9V):** Autonomously proposed and evaluated nominal multi-stop science sorties across candidate Jezero waypoints.
2. **Interactive Contingency Designer (Milestone 9R) & Gauntlet (Milestone 9E):** Evaluated how a fixed, pre-existing itinerary was impacted when encountering physical rockfalls, difficult terrain slip, mobility speed derating, or consumable ceiling cuts.

However, in actual Martian surface operations, when an unexpected hazard blocks an EVA or rover traverse corridor:
> *"Should the crew simply detour around the obstacle, drop a target and proceed, or replace the entire remaining traverse with a newly optimized adaptive tour that recovers lost science within the surviving life-support envelope?"*

Milestone 9W integrates these two engines into an autonomous **Adaptive Mission Replanning** system. It evaluates three distinct mission states under identical real-world conditions, computes a quantitative Science Recovery Ledger, and classifies the optimal operational recommendation using a deterministic decision matrix.

```
                          [ Nominal Mission Plan ]
                                     |
                                     v
                        [ Disruption Event Injected ]
                        (Corridor Closure / Derating)
                                     |
             +-----------------------+-----------------------+
             |                                               |
             v                                               v
    [ Disrupted Plan ]                             [ Adaptive Tour Replanner ]
  - Evaluates original stops                     - Disrupted Pairwise Leg Cache
  - Applies blocked & cost masks                 - Prunes unavailable targets
  - Yields: Distorted path, lost                 - Bounded beam search on surviving graph
    science points, or infeasibility             - Synthesizes recovered champions
             |                                               |
             +-----------------------+-----------------------+
                                     |
                                     v
                       [ 3-Stage Comparison Matrix ]
                   +-----------------------------------+
                   | Stage 1: Nominal Baseline         |
                   | Stage 2: Disrupted Evaluation     |
                   | Stage 3: Adaptive Recovered Tour  |
                   +-----------------------------------+
                                     |
                                     v
                       [ Science Recovery Ledger ]
                   - Priority Lost / Priority Recovered
                   - Recovery Efficiency (η %)
                   - Retained / Dropped / Added Targets
                   - Operational Recommendation Enum
```

---

## 2. Core Mathematical Formulation & Science Recovery Ledger

### 2.1 Three Mission States Under Comparison
Let $\mathcal{W}$ denote the complete catalogue of candidate science targets in the surveyed Jezero study area ($N=12$), with each target $w_i \in \mathcal{W}$ having known grid coordinate $\mathbf{x}_i = (r_i, c_i)$ and scientific priority score $P(w_i) \in [10, 200]$.

Let $\mathbf{s} = (r_s, c_s)$ be departure base and $\mathbf{g} = (r_g, c_g)$ be destination terminus.

1. **Stage 1 — Original Plan ($\mathcal{S}_{orig}$):**
   The nominal multi-stop itinerary selected before the contingency event:
   $$\mathcal{S}_{orig} = (\mathbf{s}, w_{o,1}, w_{o,2}, \dots, w_{o,k}, \mathbf{g})$$
   $$\text{Total Priority: } P_{orig} = \sum_{j=1}^k P(w_{o,j})$$
   $$\text{Ground Distance: } D_{orig}, \quad \text{Mission Time: } T_{orig} \le T_{max}$$

2. **Stage 2 — Disrupted Plan ($\mathcal{S}_{disr}$):**
   The exact original itinerary $\mathcal{S}_{orig}$ evaluated in the presence of the active disruption:
   - If a target $w_{o,j}$ is declared inaccessible ($\text{target\_unavailable}$), it is dropped from the itinerary.
   - If an obstacle $\mathcal{B} \subset \mathbb{Z}^2$ blocks corridor cells, legs are re-routed using $A^*$ constrained to $\mathbb{Z}^2 \setminus \mathcal{B}$.
   - If mobility derating factor $\alpha \in (0, 1]$ or hold delay $\Delta t_{hold}$ are active, leg durations scale: $t'_{leg} = t_{leg}/\alpha$, $T_{disr} = \sum t'_{leg} + \Delta t_{hold} + T_{dwell}$.
   $$\text{Surviving Priority: } P_{disr} \le P_{orig}$$

3. **Stage 3 — Adaptive Plan ($\mathcal{S}_{adapt}$):**
   A newly optimized itinerary generated under the *exact same disruption conditions*:
   $$\mathcal{S}_{adapt} = (\mathbf{s}, w_{a,1}, \dots, w_{a,m}, \mathbf{g}), \quad w_{a,j} \in \mathcal{W} \setminus (\mathcal{B} \cup \mathcal{U})$$
   where $\mathcal{U}$ is the set of unavailable targets.
   $$\text{Recovered Priority: } P_{adapt} = \sum_{j=1}^m P(w_{a,j})$$

### 2.2 Quantitative Science Recovery Ledger Identities
The engine computes and verifies the following exact algebraic metrics:
- **Priority Lost:**
  $$\Delta P_{lost} = \max\left(0, P_{orig} - P_{disr}\right)$$
- **Priority Recovered:**
  $$\Delta P_{rec} = \max\left(0, P_{adapt} - P_{disr}\right)$$
- **Net Science Delta:**
  $$\Delta P_{net} = P_{adapt} - P_{orig}$$
- **Recovery Efficiency Percentage ($\eta$):**
  $$\eta = \begin{cases} \left(\frac{\Delta P_{rec}}{\Delta P_{lost}}\right) \times 100\%, & \text{if } \Delta P_{lost} > 0 \\ 100\%, & \text{if } \Delta P_{lost} = 0 \text{ and } P_{adapt} \ge P_{orig} \\ 0\%, & \text{otherwise} \end{cases}$$
- **Target Tracking Sets:**
  $$\mathcal{W}_{retained} = \mathcal{W}_{orig} \cap \mathcal{W}_{adapt}$$
  $$\mathcal{W}_{dropped} = \mathcal{W}_{orig} \setminus \mathcal{W}_{adapt}$$
  $$\mathcal{W}_{added} = \mathcal{W}_{adapt} \setminus \mathcal{W}_{orig}$$
- **Operational Deltas:**
  $$\Delta D = D_{adapt} - D_{orig}, \quad \Delta T = T_{adapt} - T_{orig}, \quad \Delta M = M_{adapt} - M_{orig}$$

---

## 3. Disruption-Aware Optimization Pipeline

### 3.1 Disrupted Pairwise Leg Caching
Crucially, nominal precomputed pairwise legs *cannot* be used during disruption-aware replanning. A nominal leg could pass straight through a newly closed rockfall corridor.
The replanner generates a **Disrupted Pairwise Graph**:
```python
t_cfg = get_profile_terrain_config(profile)
leg_cache = compute_pairwise_leg_cache(
    unique_nodes=candidate_nodes,
    terrain=terrain,
    terrain_config=t_cfg,
    blocked_mask=scen_blocked_mask,
    cost_multiplier_mask=scen_cost_mask,
)
```
Every leg in `leg_cache` is strictly pre-routed around blocked cells using Python $A^*$. If a candidate waypoint is fully enveloped by a closed corridor, all connected directed edges have `is_reachable = False` and `cost = inf`, mathematically pruning the inaccessible waypoint from graph exploration.

### 3.2 Bounded Beam Search Under Disruption
Candidate itineraries are explored up to depth $K \le 5$ intermediate stops using bounded beam search ($B \in [6, 20]$).
At expansion depth $d$:
1. State vector: $(\text{visited\_indices}, \mathbf{x}_{last}, D_{cum}, C_{cum}, T_{cum}, P_{cum})$
2. Heuristic evaluation function:
   $$H(s) = P_{cum} - \lambda D_{cum}$$
   where $\lambda = 0.015$ (Balanced/Conservative) or $0.005$ (Science-First).
3. Budget filtering: At every step, the leg from $\mathbf{x}_{last} \to \mathbf{g}$ is checked. If $T_{total} > T_{limit}$, the candidate is rejected from beam expansion.
4. Top $B$ non-dominated states survive to depth $d+1$.

### 3.3 Authoritative Re-Evaluation
The best adaptive candidate is passed to `plan_sequential_multistop_route()` on the live Jezero 20m CTX raster with the active disruption masks. Exact path geometry, cumulative climb (meters), maximum slope (degrees), and multi-leg timeline events are authoritatively measured.

---

## 4. Operational Recommendation Decision Matrix

The system classifies the operational trade-off into one of five mutually exclusive `ReplanningRecommendation` enums:

| Recommendation Enum | Condition | Operational Meaning |
| :--- | :--- | :--- |
| `unresolvable_critical_hazard` | Neither adaptive nor disrupted route is reachable | Spatial obstruction completely isolates base or goal; immediate field abort required. |
| `abort_to_direct_baseline` | Adaptive and disrupted multi-stop tours are infeasible | Consumables / mobility derating prevents intermediate stops; return directly to base. |
| `replace_with_adaptive_tour` | Adaptive plan adds alternative targets ($\mathcal{W}_{added} \neq \emptyset$) and recovers lost priority ($\Delta P_{rec} > 0$) within budget | Recommended! Replaces degraded original tour with an optimized alternative recovering scientific return. |
| `drop_target_and_proceed` | Disrupted plan dropped unavailable target but remains feasible without needing itinerary restructuring | Proceeding with surviving stops is safe; no reroute necessary. |
| `continue_with_detour` | Disrupted plan remains fully feasible with acceptable detour delta ($\Delta D < 15\%$) preserving all targets | Proceed with original stops via $A^*$ detour around obstacle. |

---

## 5. System Integration & Immutability

### 5.1 Service Layer API (`POST /api/mission/replan`)
- **Input:** JSON payload with `start`, `goal`, `profile`, `vehicle_mode`, `operational_limit_s`, `stops`, `candidate_targets`, `custom_events`, `max_stops`, `objective`.
- **Validation:** Bounds checking against surveyed Jezero boundary, endpoint distinctness, event validation, target catalog resolution.
- **Output:** JSON containing `status: "success"`, `computation_fingerprint`, `recommendation`, `recommendation_rationale`, `science_recovery`, `original_plan`, `disrupted_plan`, `adaptive_plan`, `adaptive_alternatives`.
- **Determinism:** Cryptographically sealed with SHA-256 fingerprint binding input parameters, disruption event IDs, and itinerary sequence.

### 5.2 Workspace Data Immutability
In accordance with non-negotiable project rules:
- Replanning is strictly non-destructive.
- Zero existing saved missions or historical experiments are modified on disk.
- All 7 saved missions and 11 historical experiments remain intact and unmutated.

---

## 6. Verification Summary

- **Unit & Regression Suite:** `tests/test_milestone_9w_adaptive_replanning.py`
  - 20 test cases covering all 20 required behaviors.
  - **Result:** 20/20 PASSED in 33.82s.
- **Full Test Suite:** 319/319 PASSED across 30 test files in 131.80s.
- **Preflight Diagnostics:** 12/12 checkpoints PASSED in 462.8ms.
