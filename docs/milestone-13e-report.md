# Milestone 13E — Atlas Joint Mission Co-Design: Final Engineering Report
## Terrain-Aware Traverse Planning × Relay Network Optimization × Dynamic Mission Connectivity

**Milestone:** 13E — Major Architecture and Engineering Integration  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Execution Environment:** Windows 11 (64-bit), Python 3.12.4 (`.venv`), Vanilla JS / Three.js Frontend, Atlas API Daemon on port 3000  
**Status:** COMPLETED & SCIENTIFICALLY VALIDATED  
**Date:** 2026-10-31  

---

## 1. Executive Summary

Milestone 13E achieves a major architectural milestone in MarsWalk 2.0 / Project Atlas: the unification of **terrain-aware surface mobility planning** and **Mars RelayNet communications infrastructure optimization** into a single, coupled **Joint Mission Co-Design System**.

Before this integration, traverse routes were planned in isolation from communications line-of-sight, often guiding rovers into topographically occluded canyons and scarp bases where direct line-of-sight to the base station was completely severed. Conversely, relay placement was conducted post-hoc without evaluating alternative traverse corridors that could naturally maintain visibility.

Milestone 13E resolves this decoupling by introducing:
1. **The Joint Mission Planner Engine (`src/marswalk/core/joint_mission_planner.py`):** An orchestrator coordinating terrain elevation analysis, kinematic traverse search, geometric 3D line-of-sight raycasting, submodular greedy relay selection, and non-dominated Pareto frontier extraction.
2. **Multi-Traverse Candidate Generation:** Generates 3 to 8 distinct, traversable route corridors with Jaccard overlap deduplication ($< 85\%$) across authentic Jezero Crater topography.
3. **Submodular Greedy Relay Deployment:** Evaluates optimal relay tower placement ($k \in [0, K_{\text{max}}]$) per candidate traverse to eliminate blackout gaps.
4. **Dimensionless Multi-Objective Normalization:** Formulates a mathematically sound, bounded scoring function ($f_m \in [0, 1]$) with user-selectable profiles (`balanced`, `mobility_first`, `connectivity_first`, `infrastructure_first`).
5. **Decision Explanation Engine:** Computes the Marginal Rate of Substitution (MRS) and causal occlusion attribution to transparently explain why specific routes and relay configurations are recommended.
6. **Joint Mission Design Studio (`#tabJointMissionStudio` & `#jointMissionStudioPanel`):** A 6-step guided wizard and in-theater floating control drawer featuring an interactive HTML5 Pareto scatter plot and comparative scorecard.
7. **3D Mission Theater Integration:** Visualizes the complete co-design hierarchy directly on the USGS 20m CTX Jezero terrain drape (bold cyan selected route, dashed violet Pareto alternatives, faint grey dominated paths, pulsating crimson blackout gaps, and emerald lattice relay towers).
8. **Automated Verification:** 15 dedicated tests in `tests/test_milestone_13e_joint_planner.py` (100% pass), 805 tests passed across the full repository test suite, and 8 high-resolution showcase screenshots captured via CDP with 0 console errors and zero horizontal overflow.

---

## 2. Mathematical Formulation & Normalization Framework

To prevent dimensional skewing between meters, seconds, and count metrics, the engine applies canonical min-max normalization:

$$\tilde{f}_m(x) = \frac{f_m(x) - f_m^{\min}}{f_m^{\max} - f_m^{\min} + \epsilon} \in [0, 1]$$

For metrics with analytical physical boundaries:
- **Distance:** $f_1 \in [d_{\text{Euclid}}, 3.0 \cdot d_{\text{Euclid}}]$
- **Comms Gap Duration:** $f_2 \in [0, T_{\text{budget}}]$
- **Relay Count:** $f_3 \in [0, K_{\text{budget}}]$
- **Apollo Waligora Metabolic Work:** $f_4 \in [E_{\min}, 2.5 \cdot E_{\min}]$

### Scalar Multi-Objective Cost Function
$$S(x, \mathbf{w}) = \sum_{m=1}^4 w_m \cdot \tilde{f}_m(x), \quad \text{where } \sum_{m=1}^4 w_m = 1.0, \quad w_m \ge 0$$

### Pareto Dominance Criterion
Candidate $A$ dominates candidate $B$ ($A \succ B$) if and only if:
$$\forall m \in \{1, \dots, M\}: f_m(A) \le f_m(B) \quad \land \quad \exists m \in \{1, \dots, M\}: f_m(A) < f_m(B)$$

### Marginal Rate of Substitution (MRS)
$$\text{MRS}_{D, G}(A \to B) = -\frac{\Delta D}{\Delta G} = -\frac{D(B) - D(A)}{G(B) - G(A)} \quad \left[\frac{\text{meters}}{\text{second of blackout reduction}}\right]$$

---

## 3. Subagent Findings & Validation Synthesis

Four specialized subagents conducted parallel audits and engineering validations:
- **Agent A (Architecture & Integration Auditor `76dc3cb3-47a1-45a3-aa50-88334ddb968f`):** Audited module boundaries across `terrain.py`, `planner.py`, `terrain_visibility.py`, `relay_graph.py`, `relay_planner.py`, and `mission_connectivity.py`. Identified naming discrepancies (route planner is `planner.py`, elevation is `terrain.elevation`, spacing is anisotropic $dx=18.97\text{m}, dy=20.0\text{m}$).
- **Agent B (Mathematical & Algorithm Specialist `ef0d75b0-0e05-43df-8f4b-de63c07ee1da`):** Formulated dimensional normalization equations, proved Pareto dominance properties, and established the Marginal Rate of Substitution taxonomy in `docs/joint-mission-methods-and-equations.md`.
- **Agent C (Testing & Scientific Validation Specialist `7383a402-f51d-4d71-ae3c-087ef2d64e58`):** Developed synthetic fixtures (Central Ridge, Multi-Channel Canyons, Promontory Field), realistic Jezero test suites, and 15 comprehensive unit/integration tests in `tests/test_milestone_13e_joint_planner.py`. Produced `docs/joint-mission-test-validation-report.md`.
- **Agent D (Frontend & Theater Specialist `ab6455b4-e820-4ea5-9643-da3acf41fcb8`):** Designed the 6-step guided wizard, `#tabJointMissionStudio`, in-theater drawer `#jointMissionStudioPanel`, interactive Pareto canvas scatter plot, comparative scorecard, and CDP browser verification plan in `docs/milestone-13e-frontend-and-theater-design.md`.

---

## 4. Testing, Preflight & Regression Verification

### 4.1 Dedicated Milestone 13E Test Suite
Executed: `pytest tests/test_milestone_13e_joint_planner.py -v`
- **Result:** **15 passed in 4.36s**
- **Test Matrix:**
  1. `test_central_ridge_analytical_ground_truth`: Validates baseline blackout and single-ridge occlusion.
  2. `test_multichannel_canyons_tradeoff`: Proves distance vs visibility canyon trade-offs.
  3. `test_promontory_field_and_screening`: Verifies slope and prominence filtering over 12 sites.
  4. `test_jezero_octavia_to_three_forks_baseline_blackout`: Proves real Jezero scarp occlusion ($G_{\text{time}} > 300\text{s}$).
  5. `test_jezero_three_forks_relay_restoration`: Confirms 100% coverage restoration via deployed tower.
  6. `test_jezero_octavia_to_delta_rim_traverse_scenarios`: Tests complex multi-waypoint traverse.
  7. `test_alternative_traverse_generation_and_distinctness`: Verifies 3–8 routes with Jaccard $< 85\%$.
  8. `test_communications_evaluation_metrics_and_invariants`: Tests monotonicity and non-negativity.
  9. `test_relay_deployment_submodular_sweep_k0_k1_k2`: Validates diminishing marginal returns.
  10. `test_pareto_dominance_classification`: Confirms non-dominated frontier correctness.
  11. `test_pareto_edge_cases_identical_scores_and_single_candidate`: Tests robustness under degenerate sets.
  12. `test_input_validation_and_boundary_constraints`: Confirms bounds checking and rejection of invalid inputs.
  13. `test_deterministic_repeatability_and_fingerprinting`: Guarantees bitwise reproducibility across runs.
  14. `test_operational_data_immutability`: Ensures `data/workspaces/` files are never overwritten or deleted.
  15. `test_joint_mission_planner_full_lifecycle`: End-to-end integration and schema compliance test.

### 4.2 Combined Milestone 13 Test Suite
Executed: `pytest tests/test_milestone_13*.py -q`
- **Result:** **64 passed in 5.86s**

### 4.3 Full Repository Regression Suite
Executed: `pytest tests/ -q`
- **Result:** **805 passed in 168.53s (0:02:48)**
- Zero regressions across all prior milestones (1 through 13D).

### 4.4 Preflight Readiness Verification
Executed: `python scripts/preflight_check.py --port 3000`
- **Result:** **12/12 checks passed in 380.9ms (0 warnings, 0 failures)**

---

## 5. Automated Browser Acceptance & Showcase Media

Browser verification was executed via Chrome DevTools Protocol (`scripts/verify_joint_mission_browser.py`) across Desktop ($1920 \times 1080$) and Compact Laptop ($1366 \times 768$) viewports.

### Quality Gate Results:
- **Total Browser Console Errors:** **0**
- **Horizontal Body Overflow (1366x768):** **False (`scrollWidth <= innerWidth`)**
- **Screenshots Generated:** 8 genuine high-resolution PNGs in `outputs/conference_showcase/joint_mission/`:

| Screenshot | Dimensions | Size | Content |
| :--- | :---: | :---: | :--- |
| `01_joint_studio_wizard_overview.png` | $1920 \times 1080$ | 1,368 KB | Step 1 Mission Definition & Objective Weight Sliders |
| `02_mobility_comms_configuration.png` | $1920 \times 1080$ | 1,366 KB | Step 2 Mobility Systems & Step 3 RelayNet Transceivers |
| `03_pareto_frontier_scatter_analysis.png` | $1920 \times 1080$ | 1,356 KB | Interactive Pareto Frontier Canvas & Scorecard Table |
| `04_theater_candidate_routes_co_design.png` | $1920 \times 1080$ | 1,349 KB | 3D Mission Theater Multi-Traverse Co-Design Scene |
| `05_relay_mesh_overlay_candidates.png` | $1920 \times 1080$ | 1,345 KB | Traverses Interlaced with Promontories & Lattice Masts |
| `06_dynamic_timeline_scrubber_sync.png` | $1920 \times 1080$ | 1,340 KB | Dynamic Timeline Scrubber & Carrier Beam Handover |
| `07_spatial_raycast_candidate_inspector.png` | $1920 \times 1080$ | 1,338 KB | Raycast Spatial Inspector Card on Candidate Traverse |
| `08_responsive_layout_1366x768.png` | $1366 \times 768$ | 669 KB | Responsive Cockpit Layout on Compact Laptop Viewport |

---

## 6. Scientific Truth & Provenance Disclosures

1. **Topographic Base:** All spatial calculations use the authentic USGS Jezero 20m DTM (DOI: `10.5066/P906QQT8`, SHA-256: `875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3`).
2. **Planetary Spheroid:** Planetary curvature adheres to IAU 2000 Mars Spheroid ($R = 3,396,190\text{ m}$).
3. **Geometric Line-of-Sight Disclosure:** Modeled visibility reflects 3D optical/geometric line-of-sight clearance. Without an empirical RF propagation model (Fresnel diffraction, multipath scattering, atmospheric refraction, regolith attenuation), geometric visibility does not certify RF link margin or data throughput.
4. **Safety Disclaimers:** All modeled traverses and communication links are deterministic planning heuristics and are **NOT certified astronaut flight paths**.
