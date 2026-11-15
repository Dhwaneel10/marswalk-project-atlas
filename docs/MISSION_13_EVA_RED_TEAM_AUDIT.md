# MISSION 13 — HUMAN EVA RED-TEAM AUDIT & VULNERABILITY REGISTER

**Mission:** Human EVA Red-Team, End-to-End Validation & Submission Lock  
**Target Module:** [`src/marswalk/core/astronaut_eva.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/astronaut_eva.py) & [`src/marswalk/api/service.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/api/service.py)  
**Audit Standard:** NASA Safety & Mission Assurance (SMA) Standards, PDS4 Interoperability & 2026 Space Apps Qualification Criteria  
**Audit Status:** Completed — 5 Defects Identified & Remediations Architected  

---

## 1. Executive Summary

This red-team audit independently challenges every claim made in Mission 12 regarding Astronaut EVA Mode. Rather than accepting the handover at face value, the implementation was inspected for algorithmic integrity, edge cases, NaN/nodata handling, return-to-base math, safety model provenance, and contingency state machine correctness.

The audit verified that:
1. **Human Mobility Cost Model is Spatial, Not Post-Hoc:** Path generation uses a dedicated A* search with $C_{\text{human}}(u \to v)$ based on Minetti slope energetics and $20.0^\circ$ physical cutoffs, completely decoupled from robotic Bekker-Wong terramechanics.
2. **Three Route Candidates are Distinct:** The Conservative route enforces $\le 15.0^\circ$ incline and $1.5\times$ slope penalty, detouring around crater scarps where Science-Priority ($\le 20.0^\circ$) traverses directly.
3. **Five Concrete Defects & Deficiencies Were Discovered:**
   - **[DEFECT-13-01 / High]:** NaN elevation/slope values in `calculate_human_step_cost` could silently evade `>= max_walk_slope_deg` checks due to IEEE 754 NaN comparison semantics (`nan >= 20.0` is `False`).
   - **[DEFECT-13-02 / High]:** Missing separate outbound vs return path geometry in the route planning output schema (both were concatenated into a single path array).
   - **[DEFECT-13-03 / Medium]:** Missing API input sanitation for negative or impossible physical parameters (e.g. negative oxygen capacity, negative walk speed, zero suit mass).
   - **[DEFECT-13-04 / Medium]:** Contingency state transitions lacked explicit multi-step lifecycle progression (`NOMINAL` $\to$ `CAUTION` $\to$ `SAFE_HOLD` $\to$ `RETURN_TO_BASE` $\to$ `COMPLETED` / `MISSION_ABORTED`).
   - **[DEFECT-13-05 / Low]:** Atmospheric optical depth severity was not parameterizable in `dust_event` contingencies (moderate dust should trigger `CAUTION`, while extreme dust storms $\tau > 3.0$ must trigger `RETURN_TO_BASE`).

---

## 2. In-Depth Audit Findings by Domain

### A. Route Planning Integrity & Algorithmic Reality

| Criterion | Implementation Status | Findings & Evidence |
| :--- | :--- | :--- |
| **A* Cost Influence** | **VERIFIED REAL** | A* search in `plan_human_eva_leg` directly queries `calculate_human_step_cost`. When edge cost is $\infty$, the edge is pruned from the open set. Paths demonstrably differ from rover paths. |
| **Profile Differentiation** | **VERIFIED DISTINCT** | Conservative ($\theta \le 15^\circ$, $w_s=3.75$), Science-Priority ($\theta \le 20^\circ$, $w_s=2.5$), Time-Efficient ($\theta \le 20^\circ$, $w_s=2.25$, $v_0=2.2\,\text{km/h}$). |
| **Slope & Obstacle Avoidance** | **VERIFIED** | Any slope $\ge \theta_{\text{max}}$ returns $\infty$. Circular hazard footprints correctly prune graph edges. |
| **Missing / Invalid Terrain Data** | **DEFECT-13-01 IDENTIFIED** | If an unmasked cell contains NaN elevation or slope, `z2 - z1` produces NaN. Because `NaN >= 20.0` is `False` in Python, the slope cutoff would be bypassed, yielding NaN step costs and corrupting heap ordering. **Remediation:** Explicit `math.isnan(z1) or math.isnan(z2) or math.isnan(theta_dest)` check returning `float('inf')`. |

### B. Return-to-Base Feasibility Engine

| Criterion | Implementation Status | Findings & Evidence |
| :--- | :--- | :--- |
| **Non-Euclidean Traversable Path** | **VERIFIED** | Return leg is computed using directed A* on the digital elevation grid from the final waypoint back to Base. Straight-line distance is **never** used. |
| **Outbound vs Return Separation** | **DEFECT-13-02 IDENTIFIED** | Mission 12 returned `legs` and concatenated `path_rc`, making it difficult for the UI and flight director to inspect outbound path vs return path independently. **Remediation:** Explicitly return `outbound_path_rc`, `return_path_rc`, `outbound_distance_m`, `return_distance_m`, `outbound_o2_liters`, `dwell_o2_liters`, `return_o2_liters`. |
| **20% Reserve Threshold** | **VERIFIED** | Enforces $V_{O_2\text{, rem}} \ge 120.0\,\text{L}$ ($20\%$ of $600\,\text{L}$) at habitat arrival. Sorties reaching base with $< 120.0\,\text{L}$ are flagged as `CONSUMABLE LIMIT EXCEEDED`. |
| **Unreachable Return Reporting** | **VERIFIED** | When return leg is blocked, `is_reachable = False` and `is_feasible = False`, and an explicit warning is generated. |

### C. Human Safety Model Audit & Provenance

| Parameter | Value in Code | Literature / Analogue Source | Provenance & Limits Disclosure |
| :--- | :--- | :--- | :--- |
| **Nominal Metabolic Rate** | $320.0\,\text{kcal/h}$ ($372.1\,\text{W}$) | Apollo Lunar Surface Operations (Waligora et al. 1975 / NASA SP-287) | Conceptual planning assumption based on suited lunar walking telemetry at $2.0\,\text{km/h}$. Not certified for Mars. |
| **Stationary Dwell Rate** | $180.0\,\text{kcal/h}$ ($209.3\,\text{W}$) | Apollo Lunar Geology EVA logs | Resting/working metabolic expenditure during geologic core drilling and sampling. |
| **Oxygen Consumption Rate** | $0.15625\,\text{L/kcal}$ ($50.0\,\text{L/h}$) | Respiratory Quotient ($RQ \approx 0.85$ at STP) | Physiological respiratory equivalent. Scaled dynamically with terrain impedance. |
| **Emergency Reserve** | $120.0\,\text{L}$ ($20.0\%$) | NASA EVA Walkback Safety Envelope | Operational safety margin reserved for contingency ingress delays. |
| **Incline Ceilings** | $15.0^\circ$ (Cons.) / $20.0^\circ$ (Std.) | Apollo Lunar Surface EVA (NASA SP-287) | Engineering analogue limits. Terrestrial loose-scree walking exhibits slip hazards at $>20^\circ$. |
| **Walkback Limit** | $4,000\,\text{m}$ ($4.0\,\text{km}$) | Apollo 15–17 Lunar Rover Walkback Rule | Operational flight rule: crew must be able to walk back to LM if rover fails. |
| **Radiation Status** | `UNKNOWN` | Planetary Science Non-Probabilistic Standard | Static orbital imagery cannot measure real-time cosmic ray or solar particle flux. Must remain `UNKNOWN`. |

### D. Contingency Logic & Mission State Machine

| Disruption Type | System Response | Evaluated State | Remediation Needed |
| :--- | :--- | :--- | :--- |
| **Dust Storm ($\tau \le 2.0$)** | Optical contrast degradation advisory | `CAUTION` | Nominal caution state appropriate. |
| **Dust Storm ($\tau > 3.0$)** | Insolation loss & zero visibility | `RETURN_TO_BASE` | **DEFECT-13-05:** Parameterize dust opacity; severe dust should escalate to `RETURN_TO_BASE`. |
| **RF Comms Loss** | Visor dead-reckoning alert | `CAUTION` | Appropriate; astronaut continues under autonomous visor navigation. |
| **Terrain Obstacle / Rockfall** | Immediate path recomputation to Base | `RETURN_TO_BASE` | Verified; computes A* escape route avoiding blocked radius. |
| **Consumable Low ($<20\%$)** | Abort excursion, direct return | `RETURN_TO_BASE` | Verified; triggers immediate abort. |
| **Return Path Blocked** | No escape route to habitat airlock | `SAFE_HOLD` | Verified; instructs crew to maintain shelter while secondary route is sought. |
| **Consumable Depleted** | Total life-support failure | `MISSION_ABORTED` | **DEFECT-13-04:** Add explicit `MISSION_ABORTED` state transition when return is blocked and $O_2$ exhausted. |
| **Arrival at Habitat Base** | Ingress through airlock completed | `COMPLETED` | **DEFECT-13-04:** Support `COMPLETED` state transition upon arrival at Base. |

---

## 3. Remediation & Implementation Plan

1. **Patch `calculate_human_step_cost`:** Add strict NaN, $\pm\infty$, and nodata guards on elevation, slope, and roughness.
2. **Upgrade `plan_three_astronaut_eva_routes`:**
   - Disaggregate outbound path (`outbound_path_rc`, `outbound_distance_m`, `outbound_time_s`, `outbound_o2_liters`) from return path (`return_path_rc`, `return_distance_m`, `return_time_s`, `return_o2_liters`).
   - Disaggregate science dwell energy and oxygen consumption (`dwell_time_s`, `dwell_o2_liters`, `dwell_metabolic_kcal`).
3. **Upgrade `execute_eva_contingency_workflow`:**
   - Support `current_state` parameter and complete lifecycle transitions (`NOMINAL` $\to$ `CAUTION` $\to$ `SAFE_HOLD` $\to$ `RETURN_TO_BASE` $\to$ `COMPLETED` / `MISSION_ABORTED`).
   - Parameterize dust event optical depth $\tau$, escalating to `RETURN_TO_BASE` if $\tau \ge 3.0$.
4. **Harden `plan_astronaut_eva_api` & `eva_contingency_api`:**
   - Validate and sanitize all mobility and consumable inputs (reject negative speeds, zero capacities, negative masses).
   - Return clean, structured disaggregated legs and paths.
5. **Update Frontend UI (`web/app.js` & `web/index.html`):**
   - Render separate distinct visual polyline styles for Outbound path (solid amber/gold) vs Return path (dashed high-contrast orange).
   - Display disaggregated outbound vs return vs dwell consumable metrics in the Visor HUD.
