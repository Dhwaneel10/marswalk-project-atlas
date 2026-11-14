# Project Atlas — Milestone 13X: Scenario Generation Methodology

**Project:** MarsWalk 2.0 / Project Atlas  
**Milestone:** 13X — Atlas Mission Grand Prix  
**Module:** [`src/marswalk/core/atlas_grand_prix_scenario_generator.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/atlas_grand_prix_scenario_generator.py)  
**Status:** **IMPLEMENTED & VERIFIED**  

---

## 1. Principles of Scenario Generation

The **Martian Scenario Generator** serves as the experimental bedrock of the Atlas Mission Grand Prix. Rather than evaluating strategies on a handful of arbitrary handcrafted test runs, the generator deterministically synthesizes thousands of controlled planetary mission scenarios across 7 orthogonal dimensions.

### Epistemic Grounding & Labeling
- **Real Planetary Data:** Terrain is extracted directly from the surveyed **USGS Jezero Crater 20m CTX DTM** (SHA-256: `875e7e80c170b84e...`) with true **Horn 8-neighbor gradient convolutions**.
- **Synthetic Distinctions:** If synthetic procedural scarps are generated, the scenario is explicitly flagged with `is_synthetic_terrain = True` to preserve scientific provenance.
- **Atmospheric Physics:** Diurnal temperature extremes (180 K to 275 K), dust optical depth ($\tau = 0.35$ to $2.5$), and atmospheric density ($\rho \approx 0.015\text{ kg/m}^3$) are calibrated against **MEDA archives** from Mars 2020.

---

## 2. Orthogonal Scenario Dimensions

1. **Topographic Geometry:** Subgrid windows ($60 \times 60$ cells at 20 m/pixel = $1.44\text{ km}^2$) sampling delta scarps, outwash plains, and crater floors.
2. **Atmospheric Degradation:** Nominal insolation ($590\text{ W/m}^2$) attenuated exponentially by atmospheric dust opacity ($I = I_0 e^{-\tau / \cos\theta}$).
3. **Deep Space Telemetry:** One-Way Light Time (OWLT) ranging from $3.8\text{ min}$ (perihelic conjunction) to $20.5\text{ min}$ (aphelic opposition), combined with relay pass windows ($1.5\text{ to }4.0\text{ hours}$).
4. **Fleet Diversity:** Ground heavy rover (`ATLAS-ROVER-01`), high-speed aerial scout (`HEXACOPTER-SURVEYOR-02`, 60% probability), and construction bot (`CONSTRUCTION-BOT-01`, 40% probability).
5. **Bayesian Science Targets:** 4 to 9 distributed geological waypoints with competing hypothesis discrimination (Lacustrine Clay vs. Pyroclastic Volcanic vs. Impact Hydrothermal).
6. **Resource Initial Inventory:** Battery capacities (60 to 100 kWh), initial state-of-charge, and Kilopower generation ratings.
7. **Injected Runtime Faults:** Discrete component failures (power loss, drive motor drag, comms blackout, sensor calibration drift) with variable onset sol and severity.

---

## 3. Dataset Partitions & Data Segregation

To prevent tuning contamination and algorithm overfitting, scenarios are organized into three frozen partitions:

| Partition | Seed Range | Allocation Size | Intended Experimental Purpose |
|:---|:---:|:---:|:---|
| **DEVELOPMENT SET** | `1000` – `1199` | 200 Scenarios | Functional validation, edge-case testing, and unit tests. |
| **TUNING SET** | `2000` – `2299` | 300 Scenarios | Hyperparameter calibration and multi-objective weight tuning. |
| **HELD-OUT CHALLENGE SET** | `5000` – `9999` | 5,000+ Scenarios | Frozen benchmark competition; strategies are evaluated once without retuning. |

---

## 4. Verification

Unit tests in `tests/test_milestone_13x_grand_prix.py` verify that:
- Any scenario regenerated with identical seed and partition yields bit-exact identical terrain, science targets, and fault sequences.
- Terrain gradients match Horn kernel values computed on the underlying GeoTIFF.
- Injected faults are kept hidden from the strategy's upfront `ScenarioPlanningContext`.
