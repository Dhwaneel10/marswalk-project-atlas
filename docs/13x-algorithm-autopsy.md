# Project Atlas — Milestone 13X: Algorithmic Autopsies & Decision Lineage

**Project:** MarsWalk 2.0 / Project Atlas  
**Milestone:** 13X — Atlas Mission Grand Prix  
**Document:** `docs/13x-algorithm-autopsy.md`  
**Status:** **VERIFIED & OPERATIONAL**  

---

## 1. Forensic Decision Lineage

The Grand Prix explainability engine ([`atlas_strategy_explainability.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/atlas_strategy_explainability.py)) traces the exact causal rationale behind every planned action.

### 1.1 Representative Scenario Autopsy: Seed 1010
**Mission:** High-Density Jezero Exploration & Hypothesis Testing

| Step | Action by `STRAT-06-ATLAS` | Action by `STRAT-03-SCIENCE` | Causal Divergence Reason |
|:---:|:---|:---|:---|
| **1** | Forward Aerial Reconnaissance on Belva Crater Ejecta (Sol 1.0) | Direct Ground Rover dispatch to Alagnak Carbonate Splay (Sol 1.0) | Atlas uses aerial scout to survey slope hazards; Science-First directly commits ground asset. |
| **2** | Verified ground traverse to Cape Nukshak Promontory (Sol 2.6) | High-speed traverse to Séítah Layered Olivine Unit (Sol 3.1) | Atlas follows cleared corridor; Science-First pursues maximum entropy target despite 11° slope. |
| **3** | Ground investigation: Neretva Vallis Outwash (Sol 4.2) | Intensive spectrometer dwell on Neretva Vallis (Sol 5.2) | Aligned target selection; Science-First dwells 2.0 sols vs Atlas 1.5 sols. |
| **4** | Carbonate sampling at Alagnak Splay (Sol 5.9) | Traversal to distant Cape Nukshak Promontory (Sol 7.4) | Atlas executes clustered routing; Science-First incurs long cross-cutting drive. |
| **5** | Delta Scarp stratigraphy (Sol 7.6) | Long return leg to Belva Crater Ejecta (Sol 9.6) | Atlas preserves return margin; Science-First experiences battery drop to 22% reserve. |

**Verdict:**
- **Science Winner:** `STRAT-03-SCIENCE` ($12.15$ vs $10.17$ points).
- **Efficiency Winner:** `STRAT-06-ATLAS` ($45.87\text{ kWh}$ vs $83.01\text{ kWh}$).
- **Composite Winner:** `STRAT-06-ATLAS` ($76.71$ vs $71.72$ index).

---

## 2. Infeasibility Autopsies: Why Did Competitors Fail?

### Case A: `STRAT-03-SCIENCE` on Round 8 (Held-Out Apocalypse, Seed 5104)
- **Failure Mode:** `INFEASIBLE_SLOPE`
- **Root Cause:** In pursuing a high-gain top-of-scarp outcrop, the planner generated a direct waypoint connection traversing a $22.4^\circ$ slope, violating the $15.0^\circ$ rover chassis rollover ceiling.
- **Remediation:** In corporate slope penalty into A* cost function.

### Case B: `STRAT-05-PARETO` on Round 2 (Resource Pressure, Seed 1128)
- **Failure Mode:** `INFEASIBLE_ENERGY`
- **Root Cause:** Tight battery budget ($38\text{ kWh}$) combined with high dust opacity ($\tau = 2.1$) caused net battery reserve to deplete to $0.0\%$ at Sol 13.2.
- **Remediation:** Enforce active load-shedding and throttle non-essential instrument heating.
