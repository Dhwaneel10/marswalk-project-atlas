# PROJECT ATLAS — MILESTONE 13Q
# OBSERVATION UTILITY & MULTI-OBJECTIVE COST MODEL
## Resource-Aware Scientific Ranking, Trade-Off Economics & Selection Strategies

**Milestone:** 13Q — Atlas Autonomous Science Discovery Engine  
**Module:** `src/marswalk/core/science_observation_value.py`  
**Status:** `QUALIFIED`

---

## 1. Multi-Component Cost Decomposition

A candidate observation cannot be evaluated solely on its potential scientific return. Planetary robotic exploration is strictly constrained by battery state-of-charge, operational daylight windows, non-volatile data storage pressure, and terrain hazards.

Every candidate action $a$ computes an explicit `ObservationCostProfile`:

1. **Total Energy ($E_{\text{obs}}$ in Wh):**
   $$E_{\text{obs}} = \frac{P_{\text{transit}} \cdot t_{\text{transit}} + P_{\text{inst}} \cdot t_{\text{obs}}}{3600}$$
2. **Transit & Observation Duration ($T_{\text{total}}$ in seconds):**
   $$T_{\text{total}} = \frac{d_{\text{Euclidean}}}{v_{\text{platform}}} + t_{\text{warmup}} + t_{\text{integration}}$$
3. **Data Volume ($V_{\text{data}}$ in Mbits):**
   $$V_{\text{data}} = \frac{R_{\text{data}} \cdot t_{\text{integration}}}{1024}$$
4. **Comm Window Demand ($t_{\text{comm}}$ in seconds):** Proximity UHF or direct-to-Earth X-band duration required to downlink the data product.
5. **Terrain / Atmospheric Risk Factor ($0.0 \le R \le 1.0$):** Slope hazard and atmospheric dust attenuation penalty.

Composite cost index:

$$C(a) = w_E \cdot \left(\frac{E}{50\text{ Wh}}\right) + w_T \cdot \left(\frac{T}{600\text{ s}}\right) + w_D \cdot \left(\frac{V}{20\text{ MB}}\right) + w_R \cdot R$$

---

## 2. Multi-Objective Cost-Aware Utility

The **Cost-Aware Discovery** strategy optimizes the information density of each exploration Joule:

$$U(a) = \frac{EIG(a) \cdot (1.0 + \text{DiscriminatingPower}(a))}{\max(0.05, C(a))}$$

This mathematical formulation naturally penalizes:
- Long traverses to low-information targets.
- High-power instruments when lower-power remote alternatives suffice.
- Observations in hazardous terrain during dust storm events.

---

## 3. Comparison of Selection Strategies

The engine natively implements and evaluates six distinct selection strategies:
1. `RANDOM_SELECTION`: Uniform random target selection baseline.
2. `FIXED_PREDETERMINED_SURVEY`: Rigid pre-planned linear raster line.
3. `GREEDY_ANOMALY`: Greedily chases highest raw spectral band depth or thermal anomaly (vulnerable to bright artifacts!).
4. `GREEDY_UNCERTAINTY`: Greedily navigates to highest spatial ignorance point.
5. `EXPECTED_INFO_GAIN`: Maximizes raw theoretical bits gained.
6. `COST_AWARE_DISCOVERY`: Maximizes bits gained per normalized unit cost.
