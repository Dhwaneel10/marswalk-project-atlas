# MISSION 12 — EVA CONSUMABLE & LIFE-SUPPORT BUDGET SPECIFICATION
## Oxygen Consumption, Metabolic Expenditure, Electrical Power & Reserve Governance

**Document Version:** 1.0.0  
**Engine:** [`src/marswalk/core/astronaut_eva.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/astronaut_eva.py)  
**Classification:** Conceptual Life-Support Modeling Specification  

---

### 1. Conceptual Baseline Assumptions & Sourcing

In Mission 11, static estimates of $320.0\,\text{kcal/h}$ metabolic energy and $50.0\,\text{L/h}$ oxygen consumption were introduced as post-hoc route metadata. Mission 12 audits and elevates these values into a **dynamic, terrain-dependent life-support consumable engine**:

| Parameter | Conceptual Baseline | Physical Units | Primary Literature / Analogue Source | Governance Classification |
| :--- | :--- | :--- | :--- | :--- |
| **Max Sortie Duration** | $8.0$ | $\text{hours}$ ($28,800\,\text{s}$) | NASA EVA Standard Baseline / ISS PLSS Sizing Envelope | Configurable Planning Constraint |
| **Nominal Metabolic Rate** | $320.0$ | $\text{kcal/h}$ ($372.1\,\text{W}$) | Apollo Lunar Surface Operations (Waligora et al. 1975 / NASA SP-287) | Engineering Analogue Assumption |
| **Nominal } O_2 \text{ Rate** | $50.0$ | $\text{L/h}$ (STP) | Human Respiratory Quotient ($RQ \approx 0.85$, $0.156\,\text{L } O_2/\text{kcal}$) | Physiological Sizing Estimate |
| **Primary } O_2 \text{ Capacity** | $600.0$ | $\text{liters}$ | Advanced Planetary Space Suit Concept (4.0 kg @ 25 MPa) | Conceptual System Capacity |
| **Emergency } O_2 \text{ Reserve**| $120.0$ | $\text{liters}$ ($20\%$) | Mandatory 30-minute to 1-hour walkback contingency margin | Mandatory Safety Constraint |
| **Suit Battery Storage** | $1,800.0$ | $\text{Watt-hours}$ | Li-Ion PLSS Avionics & Sublimator Pump Package | Conceptual System Capacity |
| **Base Suit Electrical Load**| $120.0$ | $\text{Watts}$ | Visor HUD, telemetry radios, fans, and sensor packages | Continuous Baseline Draw |

> [!CAUTION]
> **Prominent Non-Safety Disclosure:**
> All life-support parameters, oxygen rates, and metabolic values are **conceptual decision-support modeling assumptions**. They are **NOT** certified spacesuit specifications, NASA flight rules, or operational safety guarantees for real Martian extravehicular activity.

---

### 2. Dynamic Terrain-Dependent Metabolic Rate Formulation

Astronaut metabolic burn is not constant. Traversing loose regolith or ascending steep crater slopes dramatically increases cardiopulmonary workload:

$$\dot{E}_{\text{metabolic}}(u \to v) = \dot{E}_{\text{baseline}} \cdot \left[ 1.0 + 0.4 \cdot (\text{Impedance} - 1.0) \right] \cdot M_{\text{payload}}$$

Where:
- $\dot{E}_{\text{baseline}} = 320.0\,\text{kcal/h}$ for active locomotion.
- $\text{Impedance} = \max\left(1.0, \frac{C_{\text{human}}}{d(u, v)}\right)$ is the ratio of flat-terrain effort to metric distance.
- $M_{\text{payload}} = \frac{165.0\,\text{kg}}{140.0\,\text{kg}} \approx 1.179$ is the carried equipment mass penalty.
- For stationary science dwell / core sampling, metabolic burn drops to a nominal resting/working rate of $\dot{E}_{\text{dwell}} = 180.0\,\text{kcal/h}$.

---

### 3. Dynamic Oxygen Consumption Formulation

Oxygen volume consumption is physiologically linked to metabolic caloric burn through the respiratory caloric equivalent of oxygen ($k_{O_2} \approx 0.15625\,\text{L } O_2 / \text{kcal}$ at STP):

$$V_{O_2} = E_{\text{metabolic}} \cdot \left(\frac{50.0\,\text{L/h}}{320.0\,\text{kcal/h}}\right) = E_{\text{metabolic}} \cdot 0.15625\,\text{L/kcal}$$

#### Timeline Partitioning
The total consumable expenditure is partitioned across all sortie phases:
$$V_{O_2\text{, total}} = V_{O_2\text{, outbound}} + V_{O_2\text{, dwell}} + V_{O_2\text{, return}}$$
$$E_{\text{kcal, total}} = E_{\text{kcal, outbound}} + E_{\text{kcal, dwell}} + E_{\text{kcal, return}}$$
$$t_{\text{total}} = t_{\text{outbound}} + t_{\text{dwell}} + t_{\text{return}}$$

---

### 4. Remaining Reserve & Safety Margin Governance

At any moment $t$ during the sortie:
1. **Remaining Oxygen Volume:**
   $$V_{O_2\text{, rem}} = \max\left(0.0, V_{O_2\text{, cap}} - V_{O_2\text{, consumed}}\right)$$
2. **Remaining Reserve Percentage:**
   $$\%_{\text{reserve}} = \left(\frac{V_{O_2\text{, rem}}}{V_{O_2\text{, cap}}}\right) \cdot 100\%$$
3. **Emergency Threshold Trigger:**
   If $\%_{\text{reserve}} < 20.0\%$ (or $V_{O_2\text{, rem}} < 120.0\,\text{L}$), the system automatically triggers a **`CONSUMABLE_RESERVE_WARNING`**, initiates a mission state transition to **`RETURN_TO_BASE`**, and computes the fastest safe walkback trajectory to the habitat airlock.
