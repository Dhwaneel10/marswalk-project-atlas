# MarsWalk 2.0 — Milestone 9X Technical Architecture & Design Document
## Mission Robustness Lab, Sensitivity Analysis & Decision Stability

**Milestone:** 9X  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** October 19, 2026  
**Auditor & Lead:** Principal Aerospace Software Engineer, Mission-Reliability Analyst & Scientific Computing Architect  

---

## 1. Operational Problem Statement & Motivation

Prior milestones gave MarsWalk the capability to:
- Find optimal nominal science tours (Milestone 9V: Mission Design Lab).
- Stage compound disruptions and evaluate what-if contingency detours (Milestone 9R / 9W).
- Adaptively replan missions under active hazards to recover scientific return (Milestone 9W).

However, in planetary mission operations, selecting a plan based on a single deterministic forecast leaves mission planners vulnerable to operational fragility:
1. *Is the selected mission robust against subtle parameter variations (e.g., life-support consumable degradation, drive motor wear, unexpected corridor blockages)?*
2. *At what specific tested threshold does the mission become infeasible or lose its preferred status?*
3. *Does an alternative candidate sortie (e.g. fewer stops or a less ambitious route) offer superior decision stability across tested operational uncertainties?*

The **Mission Robustness Lab** answers these questions through systematic, discrete sensitivity analysis and breakpoint identification.

---

## 2. Core Scientific Axiom: Deterministic Sensitivity vs Probabilistic Uncertainty

> [!IMPORTANT]
> **Deterministic Sensitivity vs Probabilistic Forecasting:**
> Sensitivity analysis in MarsWalk evaluates discrete, explicit parameter perturbations against an authoritative physical terrain model.
> **It is NOT a probability distribution or Monte Carlo stochastic forecast.**
> Ratios such as $N_{\text{feasible}} / N_{\text{tested}}$ represent proportions of **explicitly tested cases**, and must never be represented as empirical real-world probabilities, statistical confidence intervals, or flight-certified astronaut safety envelopes.

---

## 3. Mathematical & Algorithmic Formulation

### 3.1 Sensitivity Dimensions

Let $\mathcal{M} = (S, G, \mathcal{W}, \mathbf{T}, \theta_{\text{nom}})$ represent an evaluated mission, where:
- $S \in \mathbb{R}^2$: Departure coordinates.
- $G \in \mathbb{R}^2$: Destination coordinates.
- $\mathcal{W} = [w_1, w_2, \dots, w_k]$: Ordered intermediate science waypoints.
- $\mathbf{T}$: Authoritative USGS 20m CTX Jezero Crater Digital Terrain Model.
- $\theta_{\text{nom}} = (T_{\text{budget}}, v_{\text{speed}}, \tau_{\text{dwell}}, \tau_{\text{delay}})$: Nominal operational configuration.

The Robustness Engine evaluates a discrete set of deterministic test cases $\mathcal{C} = \{c_1, c_2, \dots, c_N\}$.

#### 1. Operational Budget Sensitivity:
$$\theta_i = (T_{\text{budget}, i}, v_{\text{nom}}, \tau_{\text{dwell}}, \tau_{\text{delay}}), \quad T_{\text{budget}, i} \in \{0.5, 0.75, 1.0, 1.25\} \times T_{\text{budget, nom}}$$
- **Path Invariance:** Because budget does not alter physical topography or speed, route path geometry and distance are strictly invariant ($\Delta D = 0$, `geometry_changed = False`).
- **Margin & Feasibility:**
  $$M_i = T_{\text{budget}, i} - T_{\text{mission, nom}}$$
  $$\text{Feasible}_i = (M_i \ge 0)$$

#### 2. Mobility (Speed Multiplier) Sensitivity:
$$\theta_i = (T_{\text{budget, nom}}, m_i \cdot v_{\text{nom}}, \tau_{\text{dwell}}, \tau_{\text{delay}}), \quad m_i \in \{0.5, 0.75, 1.0, 1.25\}$$
- **Travel Time Scaling:**
  $$T_{\text{travel}, i} = \frac{T_{\text{travel, nom}}}{m_i}$$
  $$T_{\text{mission}, i} = T_{\text{travel}, i} + T_{\text{dwell, nom}} + T_{\text{delay, nom}}$$
- **Path Invariance:** Because uniform speed derating scales time linearly across all terrain cells without shifting gradient penalties, path geometry is invariant (`geometry_changed = False`).

#### 3. Spatial Corridor Closures:
$$c_i = (\mathbf{x}_{\text{closure}}, R_i)$$
- Enclosed cells $\mathcal{B} = \text{compute\_circular\_footprint}(\mathbf{x}_{\text{closure}}, R_i, \mathbf{T})$.
- **Corridor Intersection Check:**
  $$\mathcal{I} = \mathcal{B} \cap \text{Path}_{\text{nom}}$$
  - If $\mathcal{I} = \emptyset$: Route does not intersect closure $\implies$ `geometry_changed = False`, distance identical, explanation notes route unaffected.
  - If $\mathcal{I} \ne \emptyset$: Run sequential $A^*$ with $\mathbf{M}_{\text{blocked}}[\mathcal{B}] = \text{True}$. Path detours around obstacle (`geometry_changed = True`), or is declared unreachable if severed.

#### 4. Target Loss Sensitivity:
$$c_i = \text{drop}(w_k), \quad \mathcal{W}_i = \mathcal{W} \setminus \{w_k\}$$
- Science priority drops: $P_i = P_{\text{nom}} - P(w_k)$.
- Route recalculated through remaining sequence $[S, \dots, w_{k-1}, w_{k+1}, \dots, G]$.
- Incurs genuine geometry change, typically reducing traverse distance and mission time while sacrificing scientific return.

---

### 3.2 Aggregate Robustness Metrics

For $N$ evaluated test cases:
1. **Feasibility Ratio:**
   $$R_{\text{feas}} = \frac{N_{\text{feasible}}}{N}$$
2. **Reachability Ratio:**
   $$R_{\text{reach}} = \frac{N_{\text{reachable}}}{N}$$
3. **Minimum Operational Margin:**
   $$M_{\min} = \min_{i \in \text{reachable}} (M_i)$$
4. **Metric Spans:**
   $$D_{\text{range}} = [\min_i D_i, \max_i D_i], \quad T_{\text{range}} = [\min_i T_i, \max_i T_i], \quad P_{\text{range}} = [\min_i P_i, \max_i P_i]$$
5. **Decision Stability:**
   $$S_{\text{dec}} = \frac{\sum_{i=1}^N \mathbb{I}(\text{Feasible}_i == \text{Feasible}_{\text{nom}})}{N}$$

---

### 3.3 Breakpoint Detection & Search Resolution

A breakpoint is a discrete parameter boundary at which a qualitative outcome flips (e.g. feasible $\to$ infeasible, reachable $\to$ unreachable):

$$\text{Resolution: } \Delta \theta = |\theta_{k+1} - \theta_k|$$

The engine explicitly reports the tested resolution (e.g. *"Tested step resolution of 1.00 h (3600 s)"*) to guarantee scientific transparency and prevent false claims of continuous certainty.

---

### 3.4 Multi-Candidate Stability Comparison

When comparison candidates $\mathcal{M}_A, \mathcal{M}_B, \dots$ are supplied (e.g. from the Mission Design Lab), each candidate is subjected to the **exact same scenario matrix $\mathcal{C}$**.

Trade-offs are exposed side-by-side:
- **Candidate A:** High Science (28.0 pts), 69.2% Feasibility, Min Margin -42.1 min.
- **Candidate B (Direct Baseline):** Low Science (0.0 pts), 100.0% Feasibility, Min Margin +186.7 min.

Planners can immediately identify whether a conservative alternative offers superior operational insurance against uncertainty.
