# MISSION 11 — HUMAN MARSWALK EXPLORATION GAP & BIO-ENERGETIC AUDIT

**Project:** MarsWalk 2.0 / Project Atlas  
**Audit Standard:** NASA Human Research Program (HRP) Standards & EVA Standard Baseline  
**Core Constraint:** Rule `AGENTS.md`: *"Never call a modeled route operationally safe for astronauts."*  
**Companion Documents:**
- [`MISSION_11_CHALLENGE_REQUIREMENT_MATRIX.md`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/docs/MISSION_11_CHALLENGE_REQUIREMENT_MATRIX.md)
- [`MISSION_11_HUMAN_MARSWALK_UX_AUDIT.md`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/docs/MISSION_11_HUMAN_MARSWALK_UX_AUDIT.md)

---

## 1. Executive Summary: Rover vs. Human Crew Dynamics

While MarsWalk 2.0 originated with rover operational telemetry (Mars 2020 Perseverance), human surface exploration introduces radically different physical, physiological, and life-support constraints:

```
┌────────────────────────────────────────────────────────────────────────┐
│               ROBOTIC ROVER vs. CREWED EVA MOBILITY COMPARISON         │
├──────────────────────────┬────────────────────┬────────────────────────┤
│ Parameter                │ Robotic Rover      │ Crewed EVA Astronaut   │
├──────────────────────────┼────────────────────┼────────────────────────┤
│ Nominal Locomotion Rate  │ ~0.12 km/h         │ ~2.00 km/h (16x faster)│
│ Operational Window       │ Multi-Sol planning │ Strict 8-hour PLSS cap │
│ Failure Mode             │ Wheel stall/sleep  │ Lethal asphyxiation    │
│ Critical Constraint      │ Battery & memory   │ Walkback life-support  │
│ Energy Dissipation       │ Motor Joule heat   │ Metabolic cooling loop │
└──────────────────────────┴────────────────────┴────────────────────────┘
```

---

## 2. Current Implementation in MarsWalk 2.0

In [`planner.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/planner.py) and [`service.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/api/service.py), MarsWalk natively supports `vehicle_mode = "crew_eva"`:
1. **Nominal Speed:** $2.0\,\text{km/h}$ ($0.556\,\text{m/s}$), configurable in range $1.5$–$2.5\,\text{km/h}$.
2. **Operational Sortie Limit:** $28,800\,\text{s}$ (8.0 hours), based on ISS/Artemis Portable Life Support System (PLSS) envelope.
3. **Slope Limit:** Default allowable incline up to $25.0^\circ$ (compared to $15.0^\circ$ for wheeled rovers).
4. **Explicit Scientific Disclosure:** Formally documented in `ENGINEERING_ASSUMPTIONS`:
   > *"Engineering analogue based on Apollo lunar surface traverses (NASA SP-287 / Waligora et al. 1975); NOT validated Mars astronaut performance in Martian gravity (0.38g) or pressurized exploration suits."*

---

## 3. Human Surface Exploration Gaps & Scientific Analysis

### 3.1 Gap 1: Metabolic Bio-Energetics & Oxygen Expenditure Modeling
- **Current Model:** Travel time is calculated as distance divided by slope-adjusted speed: $t = \frac{d}{v(\theta)}$. Energy consumption is treated as general watt-hours.
- **Physical Reality on Mars:** Astronauts walking in partial Martian gravity ($g = 3.721\,\text{m/s}^2$) with a pressurized suit ($120$–$150\,\text{kg}$ total mass) experience complex metabolic workloads:
  - Basal metabolic rate: $\approx 100\,\text{W}$
  - Moderate level walking: $\approx 250$–$350\,\text{W}$
  - Steep incline ascent ($> 15^\circ$): $\approx 450$–$600\,\text{W}$
  - Oxygen consumption rate: $\dot{V}_{O_2} \approx 0.003 \cdot \dot{Q}_{\text{metabolic}}\,\text{L/min}$ (approx $1.0$–$1.8\,\text{L/min}$).
- **Required Disclosure:** MarsWalk must explicitly label metabolic costs as **preliminary bio-energetic estimates**, noting that pressurized suit joint resistance and cooling water sublimation are not modeled in micro-detail.

---

### 3.2 Gap 2: The "Walkback Limit" (Apollo Safety Rule)
- **Operational Rule:** Under Apollo and Artemis surface operations guidelines, an EVA crew operating with a rover or exploring away from the habitat must **never exceed the walkback distance limit**:
  $$\text{Distance to Base} \le v_{\text{contingency}} \cdot t_{\text{emergency PLSS reserve}}$$
  If a rover or primary mobility system suffers catastrophic failure at the furthest waypoint, the astronaut pair must be capable of walking back to the airlock on remaining suit oxygen and cooling reserves alone.
- **MarsWalk Gap:** While MarsWalk calculates total route length against budget distance ($8,000\,\text{m}$), it does not continuously compute a real-time "Walkback Safety Radius" polygon indicating whether the crew can abort directly back to base at any point along the traverse.

---

### 3.3 Gap 3: Biomechanical Slope Penalty (Ascent vs. Scree Descent)
- **Current Model:** Direction-dependent cost penalizes steep ascents based on Horn slope.
- **Biomechanical Reality on Mars:** While uphill climbing incurs cardiovascular and muscular fatigue, **steep downhill descents ($> 18^\circ$) on Martian scree or loose talus** present severe slipping and fall hazards:
  - In a pressurized exploration suit, center-of-mass is shifted backward by the heavy backpack PLSS.
  - A fall on jagged basalt can puncture the suit pressure bladder (catastrophic depressurization).
  - Walking downhill on loose slopes requires active muscular braking, inducing knee/quadriceps fatigue.
- **Recommendation:** Implement a non-linear downhill penalty on loose slope terrain in the path cost matrix.

---

## 4. Priority Remediation Plan (P0 / P1 Gaps)

| Gap ID | Priority | Description | Target Code Remediation | Status |
| :--- | :---: | :--- | :--- | :--- |
| **GAP-H1** | **P0** | **Operational Safety Warning:** Ensure UI and API explicitly display non-safety disclaimer when `crew_eva` mode is selected. | Update `contracts.py` and UI route header with mandatory disclaimer: *"Conceptual research route; NOT certified safe for astronaut operations."* | **Enforced via Rule AGENTS.md** |
| **GAP-H2** | **P1** | **Consumable Margin Metric:** Add estimated EVA Oxygen consumption ($\text{L}$) and Water Cooling ($\text{kg}$) based on metabolic power model to the route result summary. | Add `estimated_o2_liters` and `metabolic_burn_kcal` calculation to `extract_route_features()` in `preferences.py`. | **Planned in Part 10** |
| **GAP-H3** | **P1** | **Walkback Safety Limit Flag:** Check if max distance from base exceeds Apollo walkback envelope ($4.0\,\text{km}$ on foot). | Add boolean `walkback_limit_exceeded` to `RouteResult` validation metadata. | **Planned in Part 10** |
