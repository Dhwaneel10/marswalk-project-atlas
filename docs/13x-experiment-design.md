# Project Atlas — Milestone 13X: Experiment Design & Tournament Architecture

**Project:** MarsWalk 2.0 / Project Atlas  
**Milestone:** 13X — Atlas Mission Grand Prix  
**Document:** `docs/13x-experiment-design.md`  
**Status:** **VERIFIED & OPERATIONAL**  

---

## 1. Experimental Methodology

The **Atlas Mission Grand Prix** is structured as an evidence-based, reproducible computational competition between autonomous planetary mission planning strategies.

### 1.1 Core Principles
- **Common Operational Scenarios:** Competing strategies are evaluated on identical `ScenarioPlanningContext` instances, sharing the same terrain rasters, solar insolation envelopes, communication delay windows, fleet asset configurations, and initial consumable inventories.
- **Strict Information Gating:** Strategies are forbidden from accessing future hidden fault events or future Earth telemetry during upfront schedule compilation.
- **Paired-Seed Evaluation:** Scenario generation uses deterministic integer seeds, allowing exact pairwise difference metrics and variance reduction across competitors.

---

## 2. Dataset Partitions

Scenarios are strictly partitioned into three independent suites to prevent tuning contamination:
1. **Development Set (Seeds 1000–1199, N=200):** Used for unit tests, functional debugging, and algorithm verification.
2. **Tuning Set (Seeds 2000–2299, N=300):** Used for hyperparameter tuning and multi-objective compromise calibration.
3. **Held-Out Challenge Set (Seeds 5000+, N=5,000+):** Frozen benchmark competition suite. Strategies are evaluated once without retuning.

---

## 3. The 8-Round Grand Prix Tournament Structure

| Round | Round Name | Partition | Scenarios | Primary Operational Stressor |
|:---:|:---|:---:|:---:|:---|
| **R1** | **Nominal Martian Operations** | `DEVELOPMENT` | 20 | Nominal Jezero exploration, clear skies, nominal comms. |
| **R2** | **Resource Pressure** | `DEVELOPMENT` | 20 | Tight energy budgets (<50 kWh), high dust attenuation, 15-sol horizon. |
| **R3** | **Scientific Uncertainty** | `DEVELOPMENT` | 20 | High-entropy competing geological hypotheses (Lacustrine vs. Volcanic). |
| **R4** | **Deep Space Communications** | `TUNING` | 20 | 18–20 min OWLT, solar conjunction blackout, intermittent relay passes. |
| **R5** | **Multi-Robot Cooperation** | `TUNING` | 20 | Concurrent aerial rotorcraft reconnaissance and heavy ground rover traversal. |
| **R6** | **Failure Arena** | `TUNING` | 20 | Cascading component faults: drive motor drag, spectrometer calibration drift. |
| **R7** | **Long-Duration Settlement** | `TUNING` | 20 | 60-Sol extended campaign balancing Kilopower reactors and regolith sintering. |
| **R8** | **Held-Out Apocalypse** | `HELD_OUT` | 30 | Unseen extreme terrain scarps (>25°), severe regional dust storms ($\tau > 2.0$). |
| **TOTAL** | **8 Championship Rounds** | **ALL** | **170** | **1,020 Total Strategy Simulations** |

---

## 4. Multi-Category Champions

To avoid reducing complex trade-offs to a single misleading scalar, four distinct tournament champions are crowned:
- **Science Champion:** Highest raw scientific yield ($STRAT-03-SCIENCE$, 11.82 mean science points).
- **Efficiency Champion:** Lowest total energy consumption footprint ($STRAT-04-RESSAFE$, 13.80 kWh mean).
- **Robustness Champion:** Highest worst-case reliability, zero hard constraint violations, and highest lower-tail CVaR ($STRAT-06-ATLAS$, 100% feasibility, CVaR 63.57).
- **Overall Grand Prix Champion:** Highest multi-dimensional composite index balancing science, energy, time, and resilience ($STRAT-06-ATLAS$, 75.95 index).
