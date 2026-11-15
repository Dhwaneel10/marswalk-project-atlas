# MarsWalk 2.0 — Project Atlas

[![Tests](https://img.shields.io/badge/tests-1271%20passed-brightgreen.svg)](#automated-testing)
[![NASA Data](https://img.shields.io/badge/NASA%20Data-PDS%20%7C%20USGS-blue.svg)](docs/NASA_DATA_INVENTORY.md)
[![Five Pillars](https://img.shields.io/badge/Five%20Pillars-INTEGRATED-brightgreen.svg)](docs/FIVE_PILLAR_PRODUCT_ARCHITECTURE.md)
[![Flagship](https://img.shields.io/badge/flagship-WHEN%20MARS%20GOES%20DARK-blueviolet.svg)](docs/EVALUATOR_QUICK_START.md)
[![Verification](https://img.shields.io/badge/merkle--root-0380a7cf-success.svg)](docs/MISSION_4_TEST_REPORT.md)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![NASA Space Apps](https://img.shields.io/badge/NASA%20Space%20Apps-Challenge%202026-orange.svg)](https://www.spaceappschallenge.org/)

> **Authentic Planetary Mission Operations & Resilience Platform**  
> Powered by real NASA Planetary Data System (PDS), USGS Astrogeology CTX/HiRISE terrain models, and JPL in-situ telemetry.

---

## 🏆 Official Competition Release Package (NASA Space Apps 2026)

**Release:** `v2.6.1-competition-ready` (`mission-17-competition-readiness`)  
**Mission 17 & 17B Validation Status:** **11 / 11 Checkpoints Passed (100% Verified)**  
**Public Repository:** [https://github.com/Dhwaneel10/marswalk-project-atlas](https://github.com/Dhwaneel10/marswalk-project-atlas)  
**Published Git Commit:** `f924d54` (Branch: `mission-17-competition-readiness`)  
**Reproducible Server Command:** `python3 scripts/run_atlas.py --port 3000 --host 0.0.0.0 --no-browser` (Listening on `0.0.0.0:3000`)  
**Automated Verification Suite:** `.venv/bin/python3 scripts/verify_mission17_workflow.py`  

### 📑 Mission 18, 17B & 17 Release Documents
- **[Mission 18 Publication and Live Deployment Report](docs/MISSION_18_PUBLICATION_AND_DEPLOYMENT_REPORT.md):** Official public GitHub release audit, zero-leak verification, and cloud hosting architecture.
- **[Mission 17B Homepage Repair Report](docs/MISSION_17B_HOMEPAGE_REPAIR_REPORT.md):** Architectural root-cause repair, 7-section continuous document flow, and layout rebalancing.
- **[Mission 17B Multi-Resolution Responsive QA](docs/MISSION_17B_RESPONSIVE_QA.md):** Automated CDP audit across 7 viewports (1920x1080 to 360x800) with 0px horizontal overflow verification.
- **[Mission 17 Final Handover Report](docs/MISSION_17_FINAL_HANDOVER.md):** Complete release sign-off, phase-by-phase completion matrix, and screenshot index.
- **[Product Scope & Release Boundaries](docs/MISSION_17_PRODUCT_SCOPE.md):** Definitive boundaries of the Jezero Crater surface release vs deferred subsystems.
- **[Subsystem Feature Audit & Deferral Ledger](docs/MISSION_17_FEATURE_AUDIT.md):** Forensic audit of RelayNet Comms, Joint Co-Design Studio, and extended engineering labs.
- **[Homepage Architecture & Redesign Report](docs/MISSION_17_HOMEPAGE_REDESIGN.md):** Unobstructed viewport hierarchy, two-tier CTA architecture, and Sol 89 dust storm specs grid.
- **[Workstation Verification & Test Report](docs/MISSION_17_WORKSTATION_TESTS.md):** Detailed audit of the 5 core views (Astronaut EVA, Rover, Terrain, Science, Environment) and persistent 3D map legend.
- **[Public Release Readiness & Deployment Feasibility](docs/MISSION_17_PUBLIC_RELEASE_READINESS.md):** Repository hygiene, zero-cloud reproducibility, Docker roadmap, and network socket architecture.

### 📑 Comprehensive Technical & Scientific Archives
- **[Project Overview](docs/PROJECT_OVERVIEW.md):** Executive summary, core innovation, and Space Apps challenge alignment.
- **[Technical Architecture](docs/TECHNICAL_ARCHITECTURE.md):** Full end-to-end architecture, data flows, and subsystem specifications.
- **[Evaluator Demo Script](docs/DEMO_SCRIPT.md):** 3-minute video pitch and 5-minute technical demo script with exact spoken cues.
- **[Technical Limitations & Scientific Disclosures](docs/TECHNICAL_LIMITATIONS.md):** Transparent epistemic boundaries, assumptions, and physical approximations.
- **[Project Evidence & Evaluation Index](docs/PROJECT_EVIDENCE_INDEX.md):** Master verification matrix and Space Apps challenge rubric mapping.
- **[Scientific Claims Audit](docs/MISSION_7_CLAIM_AUDIT.md):** Rigorous peer-review level audit of all 8 scientific claims with literature citations.
- **[Official Release Manifest](docs/RELEASE_MANIFEST.md):** Machine-verified build manifest, SHA-256 dataset digests, and test results.
- **[Reproducible Setup Runbook](docs/REPRODUCIBLE_SETUP.md):** Linux bootstrap, dependencies, and one-command reproduction guide.
- **[Evaluator Experience & Interface Specification](docs/MISSION_7_EVALUATOR_EXPERIENCE.md):** The 15-second opening screen and 7-step Golden Path HUD design.

---

## 🏛️ The Five Product Pillars (Mission 4 Upgrade)

MarsWalk 2.0 / Atlas is organized around **Five Core Capabilities** grounded in verified NASA planetary science archives:

1. **[Pillar 1 — Real Mars Terrain Intelligence](docs/FIVE_PILLAR_PRODUCT_ARCHITECTURE.md#2-pillar-1-real-mars-terrain-intelligence):**
   - USGS Jezero CTX 20m DEM (250×250 corridor, DOI [10.5066/P9T31O12](https://doi.org/10.5066/P9T31O12)).
   - USGS TRN HiRISE 1m DTM window (600×600 px Hawksbill Gap ascent channel, DOI [10.5066/P13CPYYU](https://doi.org/10.5066/P13CPYYU)).
   - Horn 8-neighbor gradient kernel with operational slope barrier threshold $\theta \le 16.0^\circ$.
2. **[Pillar 2 — Real Rover Operations & Ground Truth](docs/FIVE_PILLAR_PRODUCT_ARCHITECTURE.md#3-pillar-2-real-rover-operations--ground-truth):**
   - 577 archived tactical sites from NASA PDS Rover PLACES (`best_tactical.csv`, Sols 13–1896).
   - 10 hermetically sealed titanium sample tubes deposited in Jezero Crater (NASA PDS Three Forks Sample Depot Cache).
   - 708 MMGIS traverse waypoints tracking Perseverance's historical exploration path.
3. **[Pillar 3 — Mars Environment & Weather Replay](docs/FIVE_PILLAR_PRODUCT_ARCHITECTURE.md#4-pillar-3-mars-environment--weather-replay):**
   - In-situ atmospheric dynamics from NASA Mars 2020 MEDA (PDS Atmospheres Node).
   - Diurnal pressure cycle ($690$–$775\,\text{Pa}$), air temperature ($-88.4^\circ\text{C}$ to $-11.2^\circ\text{C}$), and wind speeds.
   - Atmospheric optical depth dust storm scaling ($\tau: 0.82 \to 3.25 \to 4.10$).
4. **[Pillar 4 — Science-Driven Rover Planning](docs/FIVE_PILLAR_PRODUCT_ARCHITECTURE.md#5-pillar-4-science-driven-rover-planning):**
   - Geolocated astrobiology targets collocated onto the Jezero raster grid: Wildcat Ridge (organic carbon rings in sulfate mudstone), Skinner Ridge, Enchanted Lake, Kodiak Butte, and Belva Crater Rim.
   - Multi-objective A* traversal optimizing distance, energy, slopes, and scientific priority scores.
5. **[Pillar 5 — Autonomous Resilience & Mission Assurance](docs/FIVE_PILLAR_PRODUCT_ARCHITECTURE.md#6-pillar-5-communications--autonomous-resilience):**
   - Topographic Line-of-Sight (LOS) 3D ray-casting across the 20m CTX DTM.
   - Autonomous safe hold & adaptive lateral ridge detour around steep slope barriers and rockfall corridors.
   - Bit-exact cryptographic Merkle state proof (`0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8`).
   - *(Note: Deferred subsystem capabilities, including RelayNet RFC 9171 multi-hop mesh routing, are documented in the formal audit ledger at [docs/MISSION_17_FEATURE_AUDIT.md](docs/MISSION_17_FEATURE_AUDIT.md) to keep this competition release focused on verified surface operations.)*

---

## 📦 Evaluator Quick-Start & Flagship Demonstrator

Project MarsWalk 2.0 / Atlas is fully verified, regression-tested, and submission-ready on Ubuntu 22.04 LTS.

### 🚀 One-Command Flagship Showcase ("WHEN MARS GOES DARK")
```bash
# Run the complete end-to-end 7-stage flagship resilience demonstrator:
./scripts/run_showcase.sh 3000

# Web Interface: Open browser to http://127.0.0.1:3000/
# Click '1. Mission Control' to view the Five-Pillar Operations Deck & Flagship Cockpit.
```

### 📋 Evaluator & Mission 6 Qualification Documentation Suite
- **[Evaluator Golden Path Walkthrough](docs/EVALUATOR_GOLDEN_PATH.md):** 7-step guided evaluator tour through the Five-Pillar architecture with live interactive HUD (`★ EVALUATOR TOUR`), expected values, and scientific explanations.
- **[Mission 6 Final Handover Report](docs/MISSION_6_FINAL_HANDOVER.md):** Complete mission sign-off, red-team defect register, comprehensive verification scorecard, and evaluator rubric alignment.
- **[Mission 6 Red-Team Qualification Audit](docs/MISSION_6_RED_TEAM_AUDIT.md):** Independent adversarial audit verifying Git state, process daemons, and 8/8 disk SHA-256 hashes.
- **[Mission 6 Scientific & Mathematical Validation](docs/MISSION_6_SCIENTIFIC_VALIDATION.md):** Mathematical resolution of Route A vs B planning, 30m science interception tolerance, and Three Forks sample depot ground truth.
- **[Mission 6 Linux Browser QA Report](docs/MISSION_6_BROWSER_QA.md):** Automated Chrome DevTools Protocol (CDP) headless test suite on Ubuntu 22.04 with 0 unhandled exceptions and full visual screenshot evidence.
- **[Evaluator Demo Guide](docs/EVALUATOR_DEMO_GUIDE.md):** Step-by-step evaluator manual for hackathon judges with terminal verification, 5-minute browser tour, and scenario walkthrough.
- **[Five-Pillar Interaction Report](docs/FIVE_PILLAR_INTERACTION_REPORT.md):** Architecture of the five NASA pillars, interactive endpoints, dynamic calibration, and live UI action trays.
- **[Multi-Scale Terrain Explorer Report](docs/TERRAIN_EXPLORER_REPORT.md):** USGS CTX 20m vs HiRISE 1m DTM geodesy, 5 control points, Horn slope math, and resolution-aware point inspection.
- **[Science-Driven Mission Report](docs/SCIENCE_DRIVEN_MISSION_REPORT.md):** Complete narrative arc connecting Three Forks Depot $\to$ Wildcat Ridge organic sampling $\to$ MEDA dust storm $\to$ Ridge detour $\to$ Bit-exact Merkle proof.
- **[NASA Planetary Data Inventory](docs/NASA_DATA_INVENTORY.md):** Complete catalog of all ingested USGS, PDS, and JPL datasets with SHA-256 digests.
- **[NASA Data Provenance & Geodesy Standards](docs/NASA_DATA_PROVENANCE.md):** IAU 2000 Mars Spheroid parameters, Equirectangular projection math, and primary citations.
- **[Technical Claims Register](docs/TECHNICAL_CLAIMS_REGISTER.md):** 12 verified claims with source citations, code links, test files, and measured results.

### Quick Start & Automated Verification (Linux / Ubuntu 22.04 LTS)
```bash
# 1. Automated environment setup & dependency bootstrap
./scripts/setup_atlas.sh

# 2. Run data integrity audit (8/8 authentic NASA/USGS datasets verified)
.venv/bin/python scripts/audit_nasa_data.py

# 3. Run planetary science validation gates (25/25 checks passed)
.venv/bin/python scripts/validate_nasa_data.py

# 4. Run Five-Pillar integration test suite (8/8 passed)
./scripts/run_tests.sh tests/test_nasa_data_integration.py

# 5. Run "When Mars Goes Dark" flagship test suite (9/9 passed)
./scripts/run_tests.sh tests/test_when_mars_goes_dark_integration.py

# 6. Run headless browser Golden Path audit via Chrome DevTools Protocol (7/7 steps verified)
.venv/bin/python scripts/audit_golden_path_browser.py

# 7. Launch interactive mission control workstation on port 3000
./scripts/start_atlas.sh --port 3000 --no-browser
```

### Quick Start (PowerShell / Windows)
```powershell
# 1. Automated environment setup
.\scripts\setup_atlas.ps1

# 2. Verify installation & dataset integrity
python scripts/verify_installation.py

# 3. Reproduce the 60-Sol Flagship Mission (Bit-Exact Root Hash: f9d124...bd14)
python scripts/run_flagship_mission.py

# 4. Launch interactive mission control workstation on port 3000
.\scripts\start_atlas.ps1 -Port 3000
```

### Research Architecture & Reviewer Index
- **[Architecture Overview](docs/research/architecture-overview.md):** 10-layer modular simulation stack.
- **[Module Ownership Manifesto](docs/research/module-ownership.md):** Authoritative state boundaries.
- **[Data Flow & Pipelines](docs/research/data-flow.md):** Telemetry loops and closed feedback cycles.
- **[Discrete Event Model & Clock](docs/research/event-model.md):** Causal priority dispatching.
- **[Multi-Tier Mission State Model](docs/research/mission-state-model.md):** 4-tier state twin & SHA-256 Merkle chain.
- **[HTTP REST API Reference](docs/research/api-reference.md):** Endpoints on port 3000.
- **[Scientific Evidence Model](docs/research/scientific-evidence-model.md):** Bayesian inference & Shannon information gain.
- **[Resource Accounting Ledgers](docs/research/resource-accounting.md):** Mass/energy conservation (dM <= 1e-4 kg).
- **[Known Limitations & Disclosures](docs/research/known-limitations.md):** Academic scope; non-flight-certified.
- **[Technical Research Paper Draft](docs/publication/project-atlas-research-paper.md):** Full academic draft for JOSS/IEEE.
- **[External Reviewer Guide & Challenge Kit](docs/13v-external-reviewer-guide.md):** Hands-on evaluation handbook.

---

## 🚀 Overview

**MarsWalk 2.0 (Project Atlas)** is an end-to-end planetary mission planning and rehearsal workstation designed for the NASA Space Apps Challenge. Combining deterministic route optimization with rigorous remote-sensing datasets, MarsWalk enables mission designers to explore Mars globally, investigate regional geology, plan multi-stop surface traverses across measured topography, stress-test trajectories against compound hazards, design interactive mission contingencies, and generate auditable mission briefings.

Unlike generic routing tools, MarsWalk strictly respects planetary data boundaries:
- **No Synthetic Topography:** Surface planning is confined to surveyed areas with genuine digital elevation models (Jezero Crater 20 m/pixel CTX DTM).
- **Physical Velocity & Effort Models:** Differentiates between Apollo lunar walking analogues (Crew EVA) and Mars 2020 robotic mobility dynamics (Perseverance rover).
- **Deterministic Disruption Rehearsal:** Simulates rockfall corridor closures, dune slip impedance, and drive motor derating with automated 3-way recovery proposals.
- **Interactive Contingency Designer:** Enables mission planners to place custom spatial closures, compound hazards, and operational holds with instant 8-measurement comparison tables.
- **Decision-Grade Mission Evidence:** Exports single-file Decision Pack ZIPs containing canonical bundles, briefings, RFC 4180 CSVs, and cryptographic hash manifests.
- **Traceable Scientific Provenance:** Distinguishes measured observations, derived quantities, and hypothetical simulations across every report and export.
- **Zero-Friction Competition Demo Mode:** Built-in 5-minute showcase and 12-point preflight diagnostic suite that never corrupts or overwrites user session data.

---

## 🌟 Key Capabilities

### 1. Competition Demo Mode & Preflight Diagnostics
- **One-Click Guided Showcase:** 5-minute walkthrough highlighting key features directly on live controls without requiring prior training.
- **Authentic Jezero Demonstration Traversal:** Verified 4-leg, 1,750-meter sortie from Octavia Landing through Hawksbill Gap, Skinner Ridge, and Enchanted Lake to Delta Rim Overlook.
- **12-Point Automated Preflight Diagnostics:** Instant verification of HTTP server, raster basemaps, 2,061-item gazetteer, DTM grids, A* planner, Gauntlet disruption engine, and workspace storage via CLI (`scripts/preflight_check.py`) or UI modal.
- **Safe Session Isolation:** In-memory session snapshotting (`demoSessionBackup`) guarantees active mission planning and persistent disk records are never mutated or lost.

### 2. Planetary Cartography & Surface Demonstration Focus
- **IAU 2000 Planetocentric Reference Sphere:** 3D globe rendered with USGS Viking MDIM 2.1 color basemap (232 m/pixel) and MOLA global topography.
- **Searchable Gazetteer:** Over 2,000 verified planetary landmarks, robotic landing sites, and geological features with instant orbital camera navigation.
- **Operational Surface Focus — Jezero Crater:**
  - **Jezero Crater (Primary Demonstration Workstation):** High-resolution surface routing, DTM pathfinding, and interactive EVA sortie planning are **focused exclusively on Jezero Crater** (Perseverance landing site, Hawksbill Gap, Skinner Ridge, Enchanted Lake, Delta Rim) backed by authentic USGS CTX 20m digital elevation data and NASA PDS telemetry.
  *(Note: Other planetary landmarks such as Olympus Mons, Valles Marineris, and Gale Crater are indexed in the orbital reference gazetteer for planetary orientation; 3D terrain elevation mesh routing is exclusively implemented and verified for Jezero Crater.)*

### 3. Jezero Crater 3D Surface Workstation
- **Authentic 20 m/px DTM:** Constructed from USGS Astrogeology Science Center MRO CTX stereo pairs.
- **Draped 6 m/px Orthomosaic:** Seamless optical imagery aligned with physical elevation coordinates.
- **Interactive Shader Overlays:** Real-time slope hazard heatmaps (>15° slope ceiling) and hypsometric elevation tinting.
- **12 Verified Candidate Science Waypoints:** Octavia E. Butler Landing, Hawksbill Gap, Skinner Ridge, Enchanted Lake, Belva Crater Overlook, and more.

### 4. Surface Traverse Planning (Python A* Planner)
- **Multi-Stop Sortie Planning:** Sequential routing through departure, intermediate research stops, and final destination.
- **Travelling Salesperson Optimization:** Exact permutation TSP (≤7 stops) and deterministic 2-Opt local search (>7 stops) for minimal distance and effort.
- **Vehicle Operational Modes:**
  - **Crew EVA:** 2.0 km/h nominal walking speed (Apollo analogue) with 8.0-hour life-support budget ceiling.
  - **Robotic Rover:** 0.035 m/s (~0.126 km/h) engineering drive velocity with 4.0-hour single-sol drive window.
- **Operational Budgets:** Real-time checking of life-support duration, stationary science dwell time, contingency delays, and physical distance limits.

### 5. Mission Design Lab & Autonomous Science-Tour Optimizer (Milestone 9V)
- **Autonomous Multi-Stop Tour Optimization:** Answers the core planetary planning question: *"Given a departure site, destination, life-support budget, and candidate science targets, which mission should we fly, and what alternatives should we consider?"*
- **Bounded Beam Search:** Employs pairwise directed $A^*$ leg caching over candidate science targets to evaluate hundreds of permutations in $< 500\text{ ms}$ on real CTX topography.
- **Multi-Objective Champion Synthesis:**
  - **Science Priority Champion:** Maximizes cumulative priority score within operational limits.
  - **Time Efficiency Champion:** Maximizes scientific yield rate per elapsed mission hour.
  - **Balanced Expedition Champion:** Optimizes composite utility balancing science return, climb effort, and life-support margin.
  - **Direct Nominal Baseline:** 0-stop point-to-point reference trajectory.
- **Non-Dominated Pareto Frontier:** Automatically extracts Pareto-optimal alternatives, eliminating dominated routes and illuminating true scientific trade-offs.
- **Authoritative Re-Evaluation Guarantee:** Champions and Pareto alternatives are passed through the sequential Python $A^*$ engine, ensuring exact physical geometry and timeline parity.
- **Interactive Mission Design Lab UI:** Candidate target chips, preset filters, multi-stop constraints, 3D route previewing, and one-click workspace activation.

### 6. Gauntlet Stress-Testing & Interactive Contingency Designer
- **Predefined Disruption Scenarios:** Corridor rockfall closures, crater floor dune migration, steep slope restrictions, actuator derating, and regional dust storms.
- **Interactive Contingency Designer:**
  - **6 Custom Event Types:** Closed corridor (`closed_corridor`), Difficult terrain (`difficult_terrain`), Reduced mobility (`reduced_mobility`), Reduced time budget (`reduced_time_budget`), Operational hold (`operational_hold`), and Target unavailable (`target_unavailable`).
  - **3D Coordinate Raycasting:** Interactive viewport picking on the Jezero DTM mesh to stage obstacle epicenters with adjustable radius in meters.
  - **Compound Hazard Synthesis:** Staging and solving up to 3 simultaneous compound disruptions.
  - **8-Measurement What-If Matrix:** Side-by-side comparison of baseline vs scenario metrics (distance, driving time, dwell time, total mission duration, life-support/sol margin, maximum slope, energy effort, and feasibility).
  - **Instant Baseline Restoration:** Reset custom contingencies with immediate restoration of baseline routes, markers, and footprints.

### 7. Persistent Workspaces & Auditable Export
- **Local Workspace Persistence:** Stores mission configurations and immutable experiment logs with deterministic input fingerprints.
- **Experiment Library Integration:** Custom contingency what-if analyses can be saved directly to the persistent Experiment Library conforming to Draft 2020-12 JSON schema (`saved-experiment.schema.json`).
- **Reproducible Replay:** Historical experiments can be re-executed against current algorithms while preserving historical records on disk.
- **Auditable Briefing Export:** Produces comprehensive Markdown dossiers and Draft 2020-12 valid JSON schemas detailing science targets, schedule breakdowns, classification ledgers, and disclaimers.

### 8. Decision Pack ZIP & Independent Replay Engine (Milestone 9T)
- **Canonical Mission Run Bundle:** Fully self-contained JSON schema (`mission-run-bundle.schema.json`) uniting mission inputs, terrain hash, baseline routes, and scenario comparison metrics.
- **One-Click Decision Pack (.zip):** Downloadable auditable package containing 5 artifacts (`mission_bundle.json`, `mission_brief.md`, `comparison.csv`, `route.json`, `README.txt`).
- **Cryptographic Provenance:** Bound to authentic USGS MRO CTX 20m Jezero GeoTIFF SHA-256 hash (`875e7e...`).
- **3-Stage Independent Replay:** Headless validation auditing schema validity, verifying terrain compatibility, and deterministically reproducing path geometry within strict tolerance ($\le 0.1\text{ m}$, $\le 0.1\text{ s}$).
- **Zero Historical Mutation:** Replay execution preserves all archived missions and historical experiments, persisting verified reproductions under distinct new records.

### 9. Adaptive Mission Replanning & Science Recovery (Milestone 9W)
- **Operational Replanning Decision Framework:** Answers the critical mission-operations question: *"When a disruption occurs, should the current mission continue, change its route, remove a target, or be replaced with a different science tour?"*
- **3-Stage Disruption-Aware Mission Comparison:**
  - **Original Plan:** Selected baseline mission before disruption.
  - **Disrupted Plan:** Original itinerary evaluated under active disruption conditions (obstacles, deratings, budget cuts).
  - **Adaptive Plan:** Re-optimized itinerary synthesized using disruption-aware pairwise $A^*$ search on real CTX topography to maximize preserved and recovered science.
- **Quantitative Science Recovery Ledger:**
  - **Priority Tracking:** $P_{\text{orig}}, P_{\text{disr}}, P_{\text{adapt}}$, with Priority Lost ($\Delta P_{\text{lost}}$), Priority Recovered ($\Delta P_{\text{rec}}$), and Net Delta ($\Delta P_{\text{net}}$).
  - **Recovery Efficiency:** $\eta = \frac{\Delta P_{\text{rec}}}{\Delta P_{\text{lost}}} \times 100\%$, tracking true scientific return per disruption.
  - **Target Disposition Breakdown:** Explicit accounting of retained, dropped, and newly added science waypoints.
  - **Operational Deltas:** Detailed variances in traverse distance ($\Delta D$), total elapsed time ($\Delta T$), and life-support margin ($\Delta M$).
- **Deterministic 5-Class Recommendation Engine:**
  - `continue_with_detour`: Disrupted plan remains feasible within budget; minor detour suffices.
  - `drop_target_and_proceed`: Partial corridor failure; dropping unreachable stops restores mission feasibility.
  - `replace_with_adaptive_tour`: Disrupted plan fails or loses primary objectives, but an alternative tour recovers substantial science within budget.
  - `abort_to_direct_baseline`: Sortie envelope exceeded; direct emergency egress to final destination recommended.
  - `unresolvable_critical_hazard`: Destination or immediate surrounding corridor is physically severed; mandatory safety hold.
- **Full API & Interactive Atlas Integration:**
  - Endpoint `POST /api/mission/replan` with strict bounds checking and input validation.
  - Modern HUD Glassmorphism Adaptive Replanning Card with 3-stage side-by-side comparison grid, color-coded status badges, 3D route previews, and one-click workspace activation.

### 10. Mission Robustness Lab, Sensitivity Analysis & Decision Stability (Milestone 9X)
- **Deterministic Sensitivity Engine:** Answers the operational questions: *"Does a selected mission remain feasible when operational assumptions change? How sensitive are duration, distance, and science return? At what tested budget or mobility level does the recommendation shift?"*
- **5 Sensitivity Dimensions Evaluated on Physical Terrain:**
  - **Operational Budget:** Time limits scaled to 50%, 75%, 100%, 125% of nominal, enforcing path geometry invariance ($\Delta D = 0$).
  - **Vehicle Mobility:** Speed deratings (0.5x, 0.75x, 1.0x, 1.25x) scaling travel time by $1/m$ without altering spatial route geometry.
  - **Corridor Closures:** Circular rockfall footprints testing physical intersection; computes $A^*$ detours or detects severed paths without false detour claims.
  - **Target Loss:** Evaluates individual science target access failures, measuring exact priority reduction and sequence re-optimization.
  - **Compound Disruption:** Simultaneous mobility deratings combined with operational hold delays.
- **Robustness & Stability Metrics:** Feasibility ratio ($N_{\text{feas}}/N$), reachability ratio ($N_{\text{reach}}/N$), minimum operational margin ($M_{\min}$), duration/distance spans, and decision stability percentage.
- **Discrete Breakpoint Detection:** Identifies parameter boundary transitions (e.g. minimum feasible budget, speed threshold) with explicit reporting of tested step resolution.
- **Multi-Candidate Stability Comparison:** Evaluates alternative sorties (Science Champion, Time Efficiency Champion, Balanced Expedition, Direct Baseline) against the identical scenario matrix to expose true resilience vs science trade-offs.
- **Full API & Interactive Atlas Integration:**
  - Endpoint `POST /api/mission/robustness` with Draft 2020-12 schema validation (`mission-robustness-response.schema.json`).
  - Web Atlas Mission Robustness Lab Card with preset selector, summary grid, breakpoint list, interactive scenario matrix, and 3D detour route preview.

### 11. Explainable Terrain Intelligence, Route Cost Attribution & Decision Support (Milestone 9Y)
- **Primary Operational Questions Answered:**
  - *Why did the planner choose this route?*
  - *Which terrain segments contribute most to its modeled travel cost and traversal effort?*
  - *What changes when the planning profile or vehicle mode changes?*
  - *Which alternative routes offer a different distance-versus-cost trade-off?*
  - *How did a disruption change the route's geometry, cost, and explanation?*
  - *Can a teammate or competition judge inspect the evidence behind a recommendation?*
- **Mathematical Cost Decomposition:** Step-by-step additive attribution decomposing directed edge traversal effort into five disjoint physical terms: flat-ground base distance, quadratic slope penalty, decameter surface roughness, directional climbing grade, and contingency hazard multiplier ($C_{\text{total}} = \sum C_{\text{comp}}$).
- **Auditable Reconciliation Ledger:** Strictly proves that segment metrics aggregate exactly to route totals with $\Delta \le 10^{-5}$ m error tolerance ($\sum D_j = D_{\text{total}}, \sum C_j = C_{\text{total}}$), explicitly flagging non-additive bounds (maximum slope, elevation extrema, impedance density ratio).
- **Highest-Cost Bottleneck Ranking:** Ranks top-K effort-accumulating segments with operational impacts and targeted mitigations (e.g. contour diversions, profile adjustments).
- **Deterministic Decision Rationale:** Generates verifiable explanations detailing A* optimization objectives, cliff cutoffs avoided ($\theta \ge \theta_{\max}$), and lateral detour trade-offs accepted.
- **Comparative Route Trade-Off Analysis:** Quantifies spatial divergence/convergence steps, distance/effort deltas, and efficiency metrics between nominal routes and contingency detours.
- **Live API & 3D Web Atlas Integration:**
  - Endpoint `POST /api/route/explain` validated against JSON Schema Draft 2020-12 (`route-explanation-response.schema.json`).
  - Interactive Route Decision Intelligence Card inside Tab 2 with component bars, bottleneck cards, click-to-highlight 3D terrain segments, and dynamic staleness tracking.

### 12. Mission Timeline Playback, Synchronized 3D Route Animation & Event Reconstruction (Milestone 9Z)
- **Time-Parameterized Path Trajectory Reconstruction:** Bridges discrete spatial grid routing with continuous mission timing via directed slope-cost weighted step timing: steeper segments naturally demand more modeled traversal time ($\Delta t_k \propto c_k$), preserving exact leg and mission durations.
- **Stationary Dwell & Scenario Hold Coordinates:** Coordinates remain strictly pinned during `science_dwell` (target sampling) and `scenario_delay` (operational holds) while elapsed mission time advances and instantaneous velocity drops to zero.
- **3D Vehicle Marker in Three.js:** Authentic 3D rover marker (metallic bronze chassis, solar deck, mast, directional heading indicator, and pulsing cyan navigation beacon light) translating smoothly above terrain mesh without z-fighting.
- **Full Interactive Transport HUD:** Complete control deck (Play/Pause, Reset, Scrubber slider with real-time seeking, and 1x, 5x, 10x, 25x, 50x, 100x speed multipliers) paired with live telemetry readouts (active phase, distance traversed, elevation, slope, instantaneous speed, and active science target).
- **Multi-Variant Mission Isolation:** Independent playback state for Nominal Baseline, Disrupted Detour, and Adaptive Replacement tours without state pollution.
- **Live API & Contract Conformance:**
  - Endpoint `POST /api/mission/playback` validated against JSON Schema Draft 2020-12 (`mission-playback-response.schema.json`).
  - Instantaneous state interpolation for arbitrary query timestamps $t \in [0, T_{\text{total}}]$.

### 13. Mission Camera Director, Rover Follow Modes & Synchronized Telemetry Cues (Milestone 10A)
- **Four Specialized Camera Modes:**
  - **Orbit Mode:** Free orbital manipulation with standard `OrbitControls` rotation, pan, and zoom without camera fighting.
  - **Rover Follow Mode (3rd-Person Chase):** Smooth third-person chase camera aligned with the vehicle marker's heading ($68.0\,\text{m}$ offset behind, $34.0\,\text{m}$ elevated) avoiding terrain clipping and sudden step turns.
  - **Rover Cockpit Mode (1st-Person Perspective):** Forward-facing perspective mounted atop the rover sensor mast ($8.5\,\text{m}$ elevation, $4.0\,\text{m}$ forward nudge) with a dedicated HUD reticle, crosshair, pitch ladder markings, real-time telemetry pill, and prominent disclaimer banner: *"Illustrative Visualization • Not a Certified Astronaut Flight Envelope"*.
  - **Overhead Mode (Nadir Perspective):** Stabilized top-down nadir view ($460.0\,\text{m}$ altitude) centered on the vehicle progression across the Martian terrain.
- **Route-Aware Heading & Stationary Latching:**
  - Forward tangent derived from look-ahead trajectory sampling ($1.2\,\text{s}$ forward).
  - Normalizes angular differences into $[-\pi, \pi]$ to eliminate 360-degree camera spin across branch cuts.
  - Applies low-pass exponential smoothing with $\alpha = 0.18$.
  - **Stationary Latching:** Strictly freezes heading and pitch during science dwell and delay periods, completely eliminating camera and marker jitter.
- **In-Memory Web Audio Synthesizer & Telemetry Cues:**
  - Pure synthetic sine and triangle oscillators generated via browser `AudioContext`. Zero external audio files or network requests.
  - Strictly **MUTED by default**; enabled only via explicit user interaction with real-time UI indicator (`Audio Cues: ACTIVE` / `Audio Cues: MUTED`).
  - Distinct harmonic cue profiles for mission start ($C_5 \to E_5$), science target dwell ($D_5 \to F\sharp_5 \to A_5$), contingency hold ($F_4$ double-pulse), mission completion ($C_5+E_5+G_5$ triad), and speed changes ($B_5$ tick).
  - **Scrubbing Suppression:** Suppresses audio cues during manual scrubber slider dragging.
  - **Visual Telemetry Cues:** Amber pulsing badge (`[🔔 CUE]`) and live remaining distance-to-next-stop readout (e.g. `412 m (Three Forks)`).

### 14. Mid-Sortie Emergency Injection, State Handoff & Live Replanning (Milestone 10B)
- **Mid-Mission Emergency Response:** Allows a flight controller to pause mission playback at any intermediate timestamp $t_{\text{pause}}$, inject a simulated contingency (rockfall corridor closure, mobility speed derating, operational hold, or dropped target), and re-plan the remainder of the sortie from current coordinates.
- **Accurate Instantaneous State Handoff:** Extracts rover grid cell $[r, c]$, subcell coordinates, elevation, slope, and completed target list. The remaining operational budget is strictly calculated as $T_{\text{rem}} = \max(0, T_{\text{budget}} - t)$ without double-counting past traverse or dwell times.
- **3-Way Real-Time Trade-Off Evaluation:**
  - **Nominal Remaining:** Projected completion along the original plan from rover's current coordinates.
  - **Disrupted Remaining:** Evaluates blocked-cell encounters, speed reductions, or schedule impacts on the remainder path.
  - **Adaptive Detour Continuation:** Re-optimizes unvisited targets around the hazard footprint within $T_{\text{rem}}$, classifying decisions into `continue_with_detour`, `drop_target_and_proceed`, `abort_to_direct_baseline`, or `unresolvable_critical_hazard`.
- **3D Hazard & Detour Visualization:** Displays a semi-transparent coral cylinder (`#FF5722`) at the disruption site, slate historical track (`#546E7A`), and bright green adaptive continuation polyline (`#00E676`).
- **Seamless Playback Handoff:** Applying continuation resets the playback scrubber and timeline to the continuation model ($t=0$ at interruption point), seamlessly continuing the 3D rover traverse without snapping back to mission origin or replaying prior audio cues.
- **Contract & API Conformance:** `POST /api/mission/continue` validated against JSON Schema Draft 2020-12 (`mission-continue-response.schema.json`).

### 15. Sortie Black Box & Incident Replay (Milestone 10C)
- **Append-Only Flight Event Ledger:** Immutable, schema-validated JSON ledger (`data/workspaces/events/<source_mission_id>_events.json`) recording all operational actions, departure milestones, target arrivals, simulated contingencies, route recalculations, and continuation handoffs.
- **Atomic Persistence & Idempotency:** File writes are atomically committed via isolated temporary files and `os.replace` to safeguard against corruption. Duplicate event submissions are idempotently deduplicated by `event_id`.
- **Two-Column Interactive Audit Modal:** Dedicated Sortie Black Box modal (`#blackBoxModal`) accessible directly from the 3D HUD playback toolbar.
  - **Left Column:** Chronological timeline stream with quick-filter pills (`ALL`, `NAVIGATION`, `SCIENCE`, `CONTINGENCY`, `DECISIONS`). Selecting an event highlights it in blue and loads its full payload.
  - **Right Column Top:** Incident Replay & Decision Fidelity card comparing recorded decisions vs recomputed estimates with real-time variance readouts ($\Delta D$, $\Delta T$, `MATCH` vs `DEVIATION`).
  - **Right Column Bottom:** Real-time JSON payload inspector displaying exact telemetry, planetocentric coordinates, elevation datum, and algorithm provenance.
- **Authentic Decision Fidelity Replay:**
  - Re-evaluates adaptive continuation recommendations against authentic USGS 20 m Jezero CTX elevation model.
  - Verifies exact decision and path geometry match between recorded history and recomputed estimates.
- **Truthful Provenance Distinction:** Every card and ledger view clearly distinguishes recorded historical facts from recomputed algorithmic estimates with color-coded badges (`RECORDED FACT` in green vs `RECOMPUTED ESTIMATE` in cyan).
- **Live HTTP APIs & Draft 2020-12 Contracts:**
  - `POST /api/mission/events`: Records single or batch events validated against `mission-event.schema.json`.
  - `GET /api/mission/events`: Retrieves sorted event streams with optional category and time filters.
  - `POST /api/mission/incident/replay`: Recomputes decisions and returns fidelity comparison conforming to `incident-replay-response.schema.json`.

### 16. Mars Environmental Intelligence (Milestone 10D)
- **NASA PDS In-Situ Archival Ingestion:** Atmospheric data ingestion from the NASA Planetary Data System (PDS) Atmospheres Node, featuring authentic Perseverance MEDA ground observations at Jezero Crater (Sol 1619: 589.7 Pa surface pressure, -61.7°C air temperature, -60.0°C ground temperature, 5.6% RH, $\tau = 0.35$).
- **In-Situ Environmental Focus:** Strictly anchors in-situ environmental calculations to Perseverance MEDA ground truth at Jezero Crater. Prevents unphysical atmospheric projection across planetary distances.
- **Physical Range Guard & Clean Missing Data:** Rejects unphysical Martian atmospheric metrics ($P \notin [10, 2000]\text{ Pa}$, $T \notin [130, 310]\text{ K}$) and maps PDS missing sentinels (`999999999`) to `null` rather than falsifying zero-wind speeds.
- **Climatological Model Distinction:** Explicitly distinguishes empirical surface measurements (`IN_SITU_OBSERVATION`) from numerical circulation model predictions.
- **Interactive Environmental Dashboard (`#weatherModal`):**
  - Atmospheric telemetry tiles: Barometric pressure (Pa & hPa), Air Temperature (°C & K), Ground Temperature (°C & K), Relative Humidity, Wind Vector, and Dust Optical Opacity ($\tau$).
  - Station banner with Martian Sol, UTC timestamp, local mean solar time (LMST), solar longitude ($L_s$ season), and cache age.
  - Bounded 15-minute automatic refresh preference and manual query trigger.
  - Provenance links directly to official NASA PDS archival bundles.
- **Non-Intrusive Advisory Integration:** Weather metrics provide environmental situational awareness without silently tampering with deterministic A* terrain pathfinding heuristics.
- **Draft 2020-12 Contract & Endpoints:**
  - `GET /api/weather/current?site=jezero_crater`: Returns verified environmental snapshot conforming to `weather-report.schema.json`.
  - `GET /api/weather/sites`: Returns catalogue of supported planetary stations.
  - `POST /api/weather/refresh`: Forces upstream PDS check or re-evaluates local cache.

### 17. Mission Science Report & Export Dashboard (Milestone 10E)
- **Unified Scientific Mission Report Assembler:** Integrates canonical A* routing metrics, science sampling waypoint sequences, black-box sortie event ledgers, and source-attributed Martian atmospheric telemetry into a cohesive engineering report.
- **Reproducibility Manifest & Audit Trail:** Binds every generated report with explicit USGS CTX DTM 20 m dataset IDs, SHA-256 integrity digests, planner assumptions, and deterministic input fingerprints.
- **Sandboxed High-Fidelity UI Preview (`#missionReportModal`):** Complete WYSIWYG report preview hosted inside an isolated `<iframe>` (`srcdoc`), preventing host workstation CSS cross-contamination while rendering dark-themed and print-ready layouts.
- **Offline Self-Contained HTML Export:** Single-file publication document incorporating responsive flexbox/grid styling, print-friendly `@media print` black-and-white page rules, and full HTML escaping against XSS vulnerabilities.
- **Machine-Readable JSON Companion:** Complete analytical data bundle validated against `schemas/api/v1/mission-science-report.schema.json`.
- **Live HTTP APIs & Server Endpoints:**
  - `POST /api/mission/report`: Assembles report payload and returns validated JSON with embedded HTML preview.
  - `POST /api/mission/report/html`: Direct download endpoint returning UTF-8 HTML attachment bytes.

### 18. Mission Readiness & Decision Gate (Milestone 10F)
- **Unified Decision-Support Planning Assurance:** Consolidates all four mission dimensions—Feasibility, Environmental Telemetry Readiness, Robustness & Contingency Coverage, and Provenance Reproducibility—into an authoritative planning evaluation.
- **Strict 4-State Status Engine:** Classifies every evaluated mission into `READY_FOR_REVIEW`, `CONDITIONAL`, `INCOMPLETE`, or `BLOCKED` with deterministic 0–100 scoring and penalty caps.
- **Traceable Structured Findings:** Provides unique finding codes, severity classifications (`blocker`, `warning`, `info`, `untested`), evidence telemetry citations, and actionable recommended mitigation steps.
- **Interactive Workstation Modal (`#missionReadinessModal`):** Direct navigation from top header (`#btnHeaderReadiness`), executive decision gate banner, category score tiles, interactive category/severity filter pills, expandable finding cards, and one-click JSON export.
- **Draft 2020-12 Contract & Endpoints:**
  - `POST /api/mission/readiness`: Computes comprehensive readiness assessment and validates against `mission-readiness-assessment.schema.json`.
  - `GET /api/mission/readiness/list`: Lists persisted assessments across workspace missions.
  - `GET /api/mission/readiness/<id>`: Retrieves individual assessment record.

### 19. Mission Campaign Orchestrator — Multi-Sol Planning (Milestone 11A)
- **Multi-Sol Campaign Planning Engine:** Evolved MarsWalk from individual-sortie routing to comprehensive multi-sol planetary campaign scheduling across authentic USGS CTX 20m Jezero topography.
- **Topological Prerequisite DAGs:** Enforces scientific sequencing dependencies with cycle detection, self-reference checks, and missing prerequisite rejection.
- **Resource-Bounded Partitioning:** Sequentially partitions candidate targets across multiple sols respecting daily life-support duration limits, Crew EVA locomotion physics, and zero double-counting.
- **Planning Profiles:** Supports `science_priority` (greedy science maximization), `time_constrained` (duration minimization), and `conservative` (automated 20% temporal safety buffer).
- **Dynamic Disruption & Adaptive Replanning:** Adapts downstream sols under corridor closures, target unavailability, mobility deratings, and holds while immutably preserving completed historical sols and tracking delta comparison manifests.
- **Three.js Multi-Sol Visualization:** Renders distinct color-coded 3D routes per sol directly on the Jezero surface mesh (Sol 1 Cyan, Sol 2 Amber, Sol 3 Emerald, Sol 4 Purple).
- **Versioned API & Atomic Persistence:** Validated against `schemas/api/v1/mission-campaign.schema.json` with immutable version archiving in `data/workspaces/campaigns/`.
- **Standalone Dossier Export:** One-click generation of self-contained, publication-ready HTML dossiers and JSON data bundles.

### 20. Campaign Progress & Science Observation Registry (Milestone 11B)
- **Interactive Closed-Loop Execution Tracking:** Tracks campaign progression in real-time across target and sortie state machines (`PLANNED`, `READY`, `IN_PROGRESS`, `COMPLETED`, `BLOCKED`, `DEFERRED`, `CANCELLED`).
- **Validated Science Observation Registry:** Captures first-class observational telemetry adhering to `schemas/api/v1/science-observation.schema.json` with mandatory physical SI units (`Pa`, `K`, `degC`, `m/s`, `m`, `%`, `ppm`, `count`) and strict source provenance tagging (`SIMULATED`, `IMPORTED_PDS_MEDA`, `IMPORTED_PDS_REMS`, `MEASURED_IN_SITU`).
- **Non-Rescheduling Invariant & DAG Unblocking:** Marking a target `COMPLETED` permanently prevents it from being rescheduled in remaining sols, automatically unblocks downstream dependent targets in the topological DAG, freezes past executed sols, increments the campaign version (`v1 -> v2`), and generates a revision delta comparison.
- **Target Blockage Lifecycle:** Supports marking targets `BLOCKED` with causal explanations, dynamically adapting downstream plans without corrupting prior sols.
- **Idempotency & Workspace Persistence:** Dedicated workspace directories (`data/workspaces/observations/` and `data/workspaces/campaign_progress/`) with atomic writes and idempotency deduplication.
- **Two-View Campaign Dashboard:** Interactive modal switcher between *Sortie Schedules & Target DAG* and *Execution Progress & Science Registry*, complete with progress bar, target progression ledger, observations table, and in-situ logging modal (`#campaignObservationModal`).
- **Versioned REST API Endpoints:**
  - `POST /api/campaign/progress`: Advances campaign execution, logs progress events, and dynamically recomputes remaining sols.
  - `GET /api/campaign/progress`: Retrieves active sol index, completion percentage, and recorded events.
  - `POST /api/campaign/observations`: Saves validated in-situ science observations.
  - `GET /api/campaign/observations`: Queries recorded observations with campaign and target filters.
  - `GET /api/campaign/next_eligible_targets`: Queries unblocked targets in DAG ready for execution.

### 21. Observation-Driven Campaign Intelligence & Adaptive Science Prioritization (Milestone 11C)
- **Closed-Loop Scientific Prioritization:** Elevates campaign planning from static sequencing into dynamic, observation-driven intelligence.
- **Explicit Objective & Evidence Classification:** Links candidate targets to core planetary science disciplines (`ASTROBIOLOGY_BIOSIGNATURE`, `PALEOLAKE_HYDROLOGY`, `FLUVIAL_DELTA_SEDIMENTOLOGY`, `REGOLITH_GEOCHEMISTRY`) with four-way evidence assessment (`SUPPORTS_OBJECTIVE`, `DOES_NOT_SUPPORT_OBJECTIVE`, `INCONCLUSIVE`, `NOT_ASSESSED`).
- **Adaptive Prioritization Heuristics:**
  - Positive observational evidence grants a **+25% priority boost** to downstream prerequisite targets along the same branch.
  - Negative observational evidence applies a **-35% priority reduction** to downstream dependent branches, diverting resources to higher-yielding objectives.
  - User objective weights ($[0.0, 3.0]$) dynamically scale target priorities to match evolving flight director directives.
  - Inconclusive observations remain strictly neutral (multiplier 1.0).
  - Explicit repeat observation requests schedule dedicated follow-up verification passes (`{tid}_repeat`).
- **Scientific Anti-Fabrication Guarantees:** Visiting a target does not automatically infer discovery; missing values remain strictly null; authentic source provenance (`SIMULATED`, `IMPORTED_PDS_MEDA`, `MEASURED_IN_SITU`) is immutably preserved.
- **Multi-Strategy Trade-Off Matrix:** Evaluates Baseline, Proposed Adaptive Plan, Science Priority, Time Constrained, and Conservative profiles under identical life-support envelopes.
- **Explainable Target Movement Rationales:** Generates clear justification cards with explicit status changes (`EXPEDITED`, `POSTPONED`, `UNBLOCKED`, `UNCHANGED`, `DEFERRED`, `REPEAT_ADDED`, `COMPLETED_PRESERVED`).
- **Three-Way Mode Tabs Switcher:** Instant UI navigation between Sortie Schedules & Target DAG, Execution Progress & Science Registry, and Observation-Driven Intelligence & Prioritization.
- **Versioned REST API Endpoints:**
  - `POST /api/campaign/reprioritize`: Computes adaptive plan, evaluates multi-strategy matrix, and atomically applies revisions.
  - `GET /api/campaign/recommendations`: Queries historical saved intelligence recommendations.

### 22. Campaign What-If Simulation Lab & Scenario Comparison (Milestone 11D)
- **Deterministic Multi-Scenario Simulation Engine**: Parallel stress-testing of multi-sol planetary exploration campaigns against hypothetical disruptions, mobility deratings, corridor closures, operational delays, and scientific priority shifts before promoting revisions to production.
- **6 Supported Scenario Types**:
  - `mobility_change`: Rover velocity derating factor ($[0.1, 1.5]$) and traverse slope ceiling ($[5.0, 35.0]^\circ$).
  - `operational_delay`: Injected ground hold or instrument setup delay ($[0, 14400]\text{ s}$) applied to specific sorties.
  - `target_loss`: Inaccessibility or sampling failure at a target, with automatic cascading pruning of dependent downstream DAG branches.
  - `corridor_closure`: Geographic hazard envelope (lat/lon, radius $[10.0, 500.0]\text{ m}$) triggering terrain obstacle masking and A* avoidance detours.
  - `time_constraint`: Tightened daily sortie duration limits ($[1800, 28800]\text{ s}$) or shortened campaign sol budget ($[1, 20]$).
  - `objective_priority_change`: Dynamic target priority overrides ($[0.0, 100.0]$) causing optimal target reallocation across available sol budgets.
- **Topological Order of Evaluation**: Enforces physical precedence for combined multi-perturbation scenarios:
  $\text{corridor\_closure} \to \text{target\_loss} \to \text{mobility\_change} \to \text{operational\_delay} \to \text{time\_constraint} \to \text{objective\_priority\_change}$.
- **Multi-Scenario Comparison Matrix**: Side-by-side evaluation computing explicit delta metrics relative to baseline: $\Delta\text{Sols}$, $\Delta\text{Traverse Distance (m)}$, $\Delta\text{Cumulative Duration (s)}$, $\Delta\text{Science Score}$, target accounting (`lost_target_ids`, `deferred_target_ids`, `added_target_ids`), feasibility status transition (`FEASIBLE`, `MARGINAL`, `INFEASIBLE`), and operational reversibility classification (`REVERSIBLE`, `IRREVERSIBLE`, `CONDITIONAL`).
- **Controlled Version Promotion & Zero Data Loss**: Planners can promote any evaluated what-if scenario to a new campaign version (e.g. `v1` $\to$ `v2`). The preceding baseline is permanently archived on disk (`{cid}_v1.json`) with full promotion audit metadata (`promoted_from_scenario_id`, `promotion_timestamp_utc`, `promotion_rationale`).
- **Four-Way Campaign Mode Tabs**: Instant UI navigation between Sortie Schedules & Target DAG, Execution Progress & Science Registry, Observation-Driven Intelligence, and What-If Simulation Lab.
- **Interactive UI & Standard Presets**: Dynamic scenario builder, one-click standard presets ("Dust Storm Mobility Derate", "Rockfall Corridor Closure", "Sampling Drill Anomaly Delay", "Target Lost: Rover Stuck"), live comparison table, scenario detail inspector, and structured briefing JSON export.
- **Anti-Fabrication & Research Disclaimers**: Unsupported scenario types cleanly tagged `UNSUPPORTED` with zero invented data; prominent warnings affirming simulations are deterministic heuristic tools and not certified flight decisions.
- **Versioned REST API Endpoints**:
  - `POST /api/campaign/scenarios/evaluate`: Evaluates up to 10 what-if scenarios in batch with optional persistence.
  - `GET /api/campaign/scenarios`: Queries persisted what-if scenarios with optional campaign filter.
  - `GET /api/campaign/scenarios/<scenario_id>`: Fetches individual scenario record.
  - `POST /api/campaign/scenarios/apply`: Promotes evaluated scenario to the next campaign version.

### 23. Multi-Agent Campaign Coordination & Resource Handoffs (Milestone 11E)
- **Multi-Unit Planetary Campaign Coordination**: Coordinates multiple simulated exploration units across a single campaign, allocating candidate targets and multi-sol sorties according to unit-specific mobility and energy profiles.
- **Configured Exploration Fleet Models**:
  - Explicit exploration units with deterministic mobility constraints:
    - `unit_perseverance` (Robotic Rover): nominal velocity $0.035\text{ m/s}$ ($0.13\text{ km/h}$), slope ceiling $15.0^\circ$, max sortie duration $14,400\text{ s}$ ($4.0\text{ h}$), energy rate $18.5\text{ Wh/km}$.
    - `unit_crew_eva_1` (Crew EVA Team Alpha): nominal velocity $0.556\text{ m/s}$ ($2.0\text{ km/h}$), slope ceiling $25.0^\circ$, max sortie duration $28,800\text{ s}$ ($8.0\text{ h}$), energy rate $92.0\text{ Wh/km}$.
- **Three Multi-Asset Coordination Strategies**:
  - `priority_first`: Greedy science priority allocation assigning highest-value targets to highest-capability units.
  - `balanced_workload`: Equalizes sortie counts and operational sols across units to prevent platform fatigue.
  - `capability_first`: Matches local topography slope demands and traverse distances to specific unit mobility profiles.
- **Task Responsibility Handoff Protocol**:
  - Validates and executes task responsibility transfers between units without double-counting dwell times or violating prerequisite DAG dependencies.
  - Enforces slope feasibility, unit availability windows, non-completion invariants, and remaining sol envelopes with structured rejection attribution (`INCOMPATIBLE_MOBILITY`, `UNAVAILABLE_WINDOW`, `PREREQUISITE_UNMET`, `BUDGET_EXCEEDED`, `COMPLETED_TARGET`, `SAME_UNIT`).
- **Coordination Contingencies & What-If**: Simulates unit loss (e.g. rover mechanical failure) with automatic reallocation of reachable targets to surviving crew EVA and graceful deferral of out-of-reach objectives.
- **Controlled Version Promotion & Zero Data Loss**: Promotes coordinated fleet plans to official campaign versions (`v1` $\to$ `v2`) with immutable predecessor snapshot archiving.
- **Five-Way Campaign Navigation & Interactive UI**:
  - Dedicated 5th tab (`#campaignCoordinationView`) in Campaign Orchestrator.
  - Real-time fleet unit status cards, task handoff execution form, side-by-side strategy trade-off table, chronological sortie schedule with color-coded rover vs crew indicators, and structured JSON briefing export.
- **Anti-Fabrication & Physical Transfer Disclaimers**: Physical sample transfer, direct power tethering, and inter-vehicle towing are explicitly marked `UNSUPPORTED`; simulation disclaimers are prominently displayed throughout.
- **Versioned REST API Endpoints**:
  - `POST /api/campaign/coordinate`: Generates coordinated multi-unit target allocation across specified strategy.
  - `GET /api/campaign/coordination`: Lists persisted coordination plans filtered by optional campaign ID.
  - `POST /api/campaign/handoff`: Validates and executes task responsibility handoffs.
  - `GET /api/campaign/handoffs`: Lists recorded task handoff records.
  - `POST /api/campaign/coordination/apply`: Promotes coordinated plan to next official campaign version.

### 24. Campaign Digital Twin, Multi-Unit Timeline & Temporal Execution Simulation (Milestone 11F)
- **Continuous Temporal Campaign Digital Twin**: Deterministic, event-driven temporal simulation modeling multi-unit Martian surface exploration campaigns unfolding continuously over simulated time.
- **Simulated Campaign Clock & Documented Origin**: Standardized monotonic time advancement in seconds (`simulated_time_s`) coupled with authentic Martian Sol indexing ($T_{\text{sol}} = 88,775.244\text{ s}$) and explicit format (`T+00d 00h 00m 00s`).
- **Multi-Lane Task Intervals**: Decomposes multi-unit campaign sorties into discrete, non-overlapping intervals (`TRANSIT`, `DWELL`, `HOLD`, `HANDOFF`, `REST`, `DEPOT`) with position derivations explicitly tagged `is_simulated_position=True`.
- **Deterministic Event Ordering & Tie-Breaking**: Four-tier comparator (`simulated_time_s`, `event_priority`, `unit_id`, `event_id`) guarantees bit-exact event ordering reproducibility across platforms.
- **Temporal Conflict Detection Engine**:
  - `CONFLICT_UNIT_DOUBLE_BOOKED` (Blocker): Single unit with overlapping active tasks.
  - `CONFLICT_TARGET_CONCURRENT_ACCESS` (Blocker): Two units dwelling at same target concurrently without permission.
  - `CONFLICT_PREREQUISITE_VIOLATION` (Blocker): Task starts before prerequisite completes.
  - `CONFLICT_OUTSIDE_AVAILABILITY` (Blocker): Unit assigned to task outside its operational availability window.
  - `CONFLICT_DURATION_BUDGET_EXCEEDED` (Warning): Active duration exceeds unit consumables envelope.
  - `CONFLICT_ORPHANED_TASKS` (Warning): Scheduled tasks remain assigned to an offline unit.
- **Interactive Simulation Controls**: Deterministic `advance(target_time_s)`, `step(event_count)`, `seek(target_time_s)`, `pause()`, and `reset()`. The `seek()` operation reconstructs past state from event history without mutating recorded future events.
- **Contingency Injection & Prefix Freezing**: Injects disruptions at timestamp $t_{\text{int}}$, freezes historical prefix up to $t_{\text{int}}$, reallocates remaining uncompleted work to surviving units, and creates a revised simulation continuation identity (`sim_xxx_rev1`) with full parent lineage.
- **Six-Way Campaign Navigation & Interactive UI**:
  - Dedicated 6th tab (`#campaignSimulationView`) in Campaign Orchestrator.
  - Multi-unit horizontal Gantt timeline lanes with color-coded transit, dwell, hold, and rest blocks plus a neon-cyan progress cursor.
  - Real-time simulation clock, Sol badge, playback buttons (Play, Pause, Step, +30m, +2h, Reset, Inject Contingency), interactive scrubber slider, chronological event stream, conflicts inspector, and JSON briefing export.
- **Anti-Fabrication & Reality Disclaimers**: Physical sample and power transfers between units are explicitly marked `UNSUPPORTED`; prominent simulation disclaimers are featured throughout.
- **Versioned REST API Endpoints**:
  - `POST /api/campaign/simulation/start`: Initializes digital twin simulation.
  - `POST /api/campaign/simulation/advance`: Advances simulation clock.
  - `POST /api/campaign/simulation/step`: Steps forward by event count.
  - `POST /api/campaign/simulation/seek`: Reconstructs state at target time.
  - `GET /api/campaign/simulation/<simulation_id>`: Retrieves simulation state.
  - `GET /api/campaign/simulation/<simulation_id>/events`: Retrieves discrete event stream.
  - `GET /api/campaign/simulation/<simulation_id>/conflicts`: Retrieves temporal conflicts.
  - `POST /api/campaign/simulation/interrupt`: Freezes history, injects contingency, and replans continuation.
  - `GET /api/campaign/simulations`: Lists saved simulations.

### 25. Campaign Performance Analytics, Deviation Analysis & Lessons Learned (Milestone 11G)
- **Exact Planned vs Simulated Metric Comparisons**: Rigorous comparison of planned multi-sol sorties against simulated execution timelines, auditing duration deltas, start slips, end slips, target completion rates, and operational hold durations without double-counting.
- **Workload & Energy Decomposition Across Fleet Assets**: Decomposes activity intervals into active traverse and dwell vs idle/standby durations per unit. Calculates fleet utilization and models energy consumption in kWh ($18.5\text{ Wh/km}$ for robotic rovers, $92.0\text{ Wh/km}$ for crew EVA life support).
- **Strict Causal Attribution Engine**: Distinguishes direct causality from correlation:
  - `confirmed_cause`: Unbroken event chain directly links an operational hold or contingency to a sortie blowout or target abandonment, citing triggering event IDs.
  - `contributing_factor`: Concurrent operational events present during execution without solitary proof.
  - `undetermined`: Variance observed without discrete disruption events logged.
- **Standardized Machine-Readable Deviation Codes**: Employs stable codes (`DEV_SORTIE_DURATION_BLOWOUT`, `DEV_SORTIE_START_SLIP`, `DEV_TARGET_ABANDONED`, `DEV_TARGET_BLOCKED`, `DEV_FLEET_IDLE_IMBALANCE`, `DEV_CRITICAL_HOLD_PROLONGED`, `DEV_TEMPORAL_CONFLICT`) with explicit physical units, severity, and actionable remediation guidance.
- **Grounded Lessons Learned Recommendations**: Generates concrete, evidence-backed advisory recommendations across five categories (`time_budget`, `coordination_strategy`, `task_sequencing`, `scenario_coverage`, `unit_assignment`) with grounded rationales, expected impacts, explicit assumptions, structured JSON proposed changes, and review status tracking (`active`, `reviewed`, `dismissed`).
- **Seven-Way Campaign Navigation & Interactive UI**:
  - Dedicated 7th tab (`#campaignAnalyticsView`) in Campaign Orchestrator.
  - Executive summary KPI cards (duration delta, target completion %, fleet utilization %, operational holds, temporal conflicts).
  - Sortie timing slips table with planned vs simulated departure and duration deltas.
  - Unit workload breakdown bars showing active vs idle distribution and modeled energy consumption.
  - Root cause diagnostic inspector citing triggering event chains.
  - Lessons learned action center with "Accept" and "Dismiss" controls, collapsible JSON proposed change viewer, and JSON report export.
- **Versioned REST API Endpoints**:
  - `POST /api/campaign/analyze`: Executes performance analytics on a campaign plan and simulation run.
  - `GET /api/campaign/analyses`: Lists saved campaign performance analyses.
  - `GET /api/campaign/analyses/<analysis_id>`: Retrieves a specific performance analysis record.
  - `POST /api/campaign/recommendations/review`: Updates recommendation status (`active`, `reviewed`, `dismissed`).

### 26. Campaign Design Space Explorer & Pareto Optimization (Milestone 11H)
- **Bounded Multi-Objective Exploration**: Evaluates a finite, deterministic grid of candidate campaign configurations across planning profiles (`science_priority`, `time_constrained`, `conservative`), per-sortie duration limits ($21,600\text{ s}$ to $36,000\text{ s}$), and maximum sol bounds (2 to 5 Sols).
- **Candidate Deduplication & Search Completeness**: Employs canonical SHA-256 input fingerprinting to prevent redundant evaluations. Records exact considered, deduplicated, evaluated, and rejected counts, explicitly reporting whether a search was exhaustive or bounded.
- **Authentic Planner Evaluations**: Evaluates every candidate through the real A* kinematic terrain planner on authentic USGS CTX 20m topography, generating genuine feasibility, duration, and objective metrics.
- **Rigorous Mathematical Pareto Frontier Classification**: Evaluates multi-dimensional objective vectors ($\text{Coverage}$, $\text{Duration}$, $\text{Distance}$, $\text{Unallocated Priority}$, $\text{Conflicts}$), partitioning candidates into non-dominated Pareto frontier, dominated alternatives (annotated with dominating references), and infeasible configurations.
- **Grounded Trade-off Explanations**: Generates comparative trade-off rationales grounded in calculated numbers for Maximal Science, Expedited Duration, and Minimal Mobility Distance without fabricated probabilities or confidence scores.
- **Safe Candidate Promotion & Campaign Immutability**: Allows one-click promotion of any feasible candidate to a distinct, traceable campaign plan version ($v_{n+1}$) without in-place mutation of baseline campaigns.
- **Eight-Way Campaign Navigation & Interactive UI**:
  - Dedicated 8th tab (`#campaignDesignSpaceView`) in Campaign Orchestrator.
  - Search bounds configuration toolbar (candidate count slider, profile checkboxes, duration limit and sol selectors).
  - Search completeness KPI banners with limit status indicators.
  - Interactive 2D HTML5 Canvas Pareto scatter plot (Duration vs Science Coverage) displaying dominated points, infeasible points, and the connected Pareto frontier step-curve.
  - Sortable candidate comparison table with Pareto status badges and inspection triggers.
  - Selected candidate detail inspector with configuration delta preview and promotion control.
  - Standalone JSON report export.
- **Versioned REST API Endpoints**:
  - `POST /api/campaign/design-space/evaluate`: Launches bounded multi-objective design space exploration.
  - `GET /api/campaign/design-spaces`: Lists saved campaign design space explorations.
  - `GET /api/campaign/design-space/<design_space_id>`: Retrieves a specific design space evaluation record.
  - `POST /api/campaign/design-space/promote`: Promotes a feasible candidate to a distinct new campaign version ($v_{n+1}$).

### 27. Campaign Benchmark Harness, System Integration & V2 Release Acceptance Gate (Milestone 11I)
- **Deterministic 8-Scenario Benchmark Harness**: Standardized benchmark suite (`scripts/run_campaign_benchmark.py` and `src/marswalk/core/campaign_benchmark.py`) evaluating 8 representative campaign scenarios:
  1. `BM-NORM-01`: Nominal Multi-Target Feasible Campaign across 3 Sols.
  2. `BM-DURC-02`: Duration-Constrained Campaign enforcing tight 18,000s duration ceilings with target deferral.
  3. `BM-SCIP-03`: Science-Priority Prerequisite Chain evaluating topological DAG dependency ordering ($A \to B \to C$).
  4. `BM-CONS-04`: Conservative High-Margin Campaign verifying steep slope cost derating and safety buffers.
  5. `BM-INFEAS-05`: Infeasible Candidate Partitioning & Hard Dominance Rejection (infeasible candidates cannot dominate feasible candidates or be promoted).
  6. `BM-PARETO-06`: Genuine Multi-Objective Pareto Trade-Offs preserving multi-dimensional objective vectors without composite scoring.
  7. `BM-MULTI-07`: Multi-Unit Coordination & Temporal Execution verifying multi-agent allocation and temporal timeline collision checks.
  8. `BM-INCOMP-08`: Incomplete & Inconclusive Evidence Integrity verifying neutral deltas, undetermined causal attributions, and limitations disclaimers.
- **Reproducibility Audit**: Bitwise repeat-pass verification proving zero metric drift or candidate divergence across repeat executions.
- **Full Planning-to-Analysis Lifecycle Integration**: Connects campaign formulation $\to$ design space exploration $\to$ A* terrain routing $\to$ Pareto dominance $\to$ atomic persistence $\to$ version promotion ($v_1 \to v_2$) with baseline immutability $\to$ fleet coordination $\to$ digital twin temporal simulation $\to$ in-situ observations $\to$ retrospective performance analytics.
- **JSON Schema Draft 2020-12 Contract**: Standardized contract [`schemas/api/v1/campaign-benchmark.schema.json`](schemas/api/v1/campaign-benchmark.schema.json) with validation exported via `validate_campaign_benchmark_record`.
- **Command-Line Benchmark Runner**:
  ```bash
  python scripts/run_campaign_benchmark.py [--scenarios BM-NORM-01,BM-PARETO-06] [--output outputs/benchmarks/campaign_benchmark_results.json]
  ```

---

## 🛠️ Architecture & Technology Stack

```
                        ┌────────────────────────────────────────────────┐
                        │              Browser Client (Atlas)            │
                        │  Three.js 3D Engine • Modern HUD Telemetry UI  │
                        └───────────────────────┬────────────────────────┘
                                                │ REST API / JSON
                                                ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                           MarsWalk Python Core Engine                          │
│                                                                                │
│  ┌───────────────────────┐ ┌───────────────────────┐ ┌──────────────────────┐  │
│  │    Terrain Engine     │ │    Path Planner       │ │   Gauntlet Engine    │  │
│  │ USGS 20m CTX DTM Grid │ │ A* Cost Function      │ │ Disruption Models    │  │
│  │ Slope & Effort Models │ │ Exact TSP / 2-Opt     │ │ 3-Way Recovery Plan  │  │
│  └───────────────────────┘ └───────────────────────┘ └──────────────────────┘  │
│                                                                                │
│  ┌───────────────────────┐ ┌───────────────────────┐ ┌──────────────────────┐  │
│  │  Workspace Library    │ │   Contract Validator  │ │ Tile Cache Manager   │  │
│  │ JSON Persistence      │ │ Draft 2020-12 Schemas │ │ Mars Trek Regional   │  │
│  └───────────────────────┘ └───────────────────────┘ └──────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────┘
```

- **Frontend:** Three.js (r128), OrbitControls, Vanilla JavaScript (zero bundler overhead), Modern CSS3 Glassmorphism HUD.
- **Backend Service:** Python 3.12, HTTP Server API, Rasterio, NumPy, Shapely, PyProj.
- **Cartographic Standards:** IAU Mars 2000 Planetocentric Sphere, GeoTIFF, Web Mercator Tile Matrix.

---

## 📥 Quick Start Guide

### Prerequisites
- Python 3.10+ (Python 3.10 or 3.12 recommended)
- Modern web browser with WebGL 2.0 support (Google Chrome, Mozilla Firefox, Microsoft Edge, Brave)

### Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/Dhwaneel10/marswalk-project-atlas.git
   cd marswalk-project-atlas
   ```
2. **Set up virtual environment:**
   ```bash
   # On Linux / macOS / WSL
   python3 -m venv .venv
   source .venv/bin/activate

   # On Windows PowerShell
   # python -m venv .venv
   # .\.venv\Scripts\Activate.ps1
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

### 🗺️ Planetary Terrain Datasets: Bundled vs Optional Extended

- **Bundled Out-of-the-Box (Immediate Zero-Download Deployment):**  
  The core digital elevation model `data/processed/jezero_ready_20m.tif` (247 KB, 250×250 raster grid, USGS CTX Jezero Crater 20 m/pixel) is **bundled directly in this Git repository**. You do not need to download any external files to start the server, plan EVA or rover routes, run contingency simulations, or inspect authentic topography.
- **Extended Full-Quadrant Datasets (Optional & Downloaded Separately):**  
  Full-quadrant regional CTX GeoTIFFs (DOI [10.5066/P9T31O12](https://doi.org/10.5066/P9T31O12), 100+ MB) and TRN HiRISE 1m DTM windows (DOI [10.5066/P13CPYYU](https://doi.org/10.5066/P13CPYYU)) are not bundled in Git to respect lightweight repository hygiene. They can be fetched on demand via `python scripts/download_hi_res_tiles.py` or `python data/fetch_raw_data.py`.

### Launching the Application

#### Option A: Linux / WSL / macOS (Recommended)
```bash
python3 scripts/run_atlas.py --port 3000 --host 0.0.0.0 --no-browser
```
Open your browser and navigate to `http://127.0.0.1:3000` (or `http://localhost:3000`).

#### Option B: Windows PowerShell Launcher
```powershell
.\scripts\start_atlas.ps1 -Port 3000
```

---

## 🚀 Repeatable End-to-End Demonstration Runner

To execute the complete 10-stage end-to-end mission planning, emergency replanning, reporting, and decision-gate demonstration in $<2$ seconds:

```powershell
python scripts/run_demonstration.py
```

This automated runner exercises:
1. Atlas server launch & authentic USGS CTX 20m DTM elevation model verification.
2. Saved mission selection (`m_jezero_delta_scarp_surve_090607`) & optimal multi-stop A* traverse.
3. Waypoint sequence inspection and mobility metrics ($3,149$m ground distance, $113$ min walking).
4. Kinematic playback model & mid-sortie state capture at $t=600$s without budget double-counting.
5. Injected rockfall corridor closure & 3-stage continuation trade-off evaluation (`ABORT_TO_DIRECT_BASELINE`).
6. Sortie Black Box chronological event ledger recording and retrieval.
7. Environmental telemetry verification (Perseverance MEDA Sol 1619 in-situ vs MCD v6.1 climatological model).
8. Mission Science Report generation with HTML and JSON exports.
9. Mission Readiness Decision Gate assessment ($95.0\%$ score, `CONDITIONAL` status, actionable findings).
10. Decision Pack cryptographic SHA-256 fingerprinting, RFC 4180 comparison CSV, and Markdown briefing.

Detailed operator instructions, expected visible outcomes, and recovery procedures are documented in [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md).

---

## ⚙️ Preflight Readiness Diagnostics

Before presenting or running simulations, verify full system integrity across all 12 checkpoints:

```bash
python scripts/preflight_check.py
```

The diagnostic suite evaluates:
1. Atlas HTTP daemon connectivity & API response time.
2. Web frontend assets (`index.html`, `app.js`, `styles.css`).
3. Planetary gazetteer integrity (2,061 IAU landmarks).
4. Regional imagery registry (all 4 destinations).
5. Global Viking/MOLA basemap raster assets.
6. Jezero Crater CTX optical orthomosaic.
7. Jezero Crater 20 m/pixel DTM GeoTIFF grid.
8. Deterministic Python A* path planner smoke test.
9. Gauntlet disruption & 3-way recovery engine.
10. Local workspace storage read/write permissions.
11. Mission briefing generator & Draft 2020-12 schema validation.
12. Streamlit tactical telemetry dashboard syntax.

*(You can also run preflight diagnostics directly inside the web interface by clicking the `⚙ PREFLIGHT` button on the landing page or top navigation bar.)*

---

## 🎬 5-Minute Competition Presentation Script

For judges, aerospace reviewers, and teammates, follow this recommended 5-minute showcase:

| Step | Duration | Target Screen / Controls | Key Demonstration Points |
| :--- | :--- | :--- | :--- |
| **1. Global Mars Context** | 0:00 – 1:00 | Landing Page $\rightarrow$ `EXPLORE ATLAS` | - Introduce IAU 2000 planetocentric reference sphere.<br>- Demonstrate search gazetteer (2,061 planetary landmarks).<br>- Highlight operational focus on Jezero Crater exploration corridor. |
| **2. Jezero 3D Workstation** | 1:00 – 2:00 | Click `Jezero Crater` card | - Show authentic USGS 20m CTX DTM & draped optical imagery.<br>- Toggle slope hazard heatmap (>15° slope limit) & elevation tints.<br>- View 12 scientifically verified sample candidate waypoints. |
| **3. Surface Traverse Planning** | 2:00 – 3:15 | Click `★ DEMO MODE` or load Demo Mission | - Explain 4-leg sortie: Octavia Landing $\rightarrow$ Hawksbill $\rightarrow$ Skinner $\rightarrow$ Enchanted Lake $\rightarrow$ Delta Rim.<br>- Review live A* metrics: 1,750m distance, 52 min walking, 45 min dwell, +6h 23m margin.<br>- Contrast Crew EVA walking (2.0 km/h) vs Robotic Rover (0.035 m/s). |
| **4. Gauntlet Stress-Testing** | 3:15 – 4:15 | Stress Test $\rightarrow$ `Hawksbill Rockfall` | - Simulate physical corridor rockfall forcing 3D red obstruction cylinder and amber detour (+180m).<br>- Demonstrate mobility derating: traverse time doubles while path geometry stays invariant. |
| **5. Recovery & Briefing Export** | 4:15 – 5:00 | `Apply Recovery` $\rightarrow$ `Export Briefing` | - Review 3-Way Trade-off Matrix (*Baseline vs Disrupted vs Recovered*).<br>- Export auditable Markdown dossier and Draft 2020-12 schema-valid JSON.<br>- Exit Demo Mode to demonstrate zero user workspace data corruption. |

---

## 🧪 Automated Testing

MarsWalk maintains an exhaustive suite of unit, integration, schema validation, and independent replay tests:

```bash
# Run the core competition test suite (Astronaut EVA, adversarial boundaries, REST API):
./scripts/run_tests.sh tests/test_astronaut_eva.py tests/test_astronaut_eva_adversarial.py tests/test_api_routing.py

# Run surface workstation workflow verification:
.venv/bin/python3 scripts/verify_mission17_workflow.py

# Run multi-viewport responsive layout audit (7 resolutions, 0px overflow):
.venv/bin/python3 scripts/verify_mission17b_responsive.py
```

**Verification Results:**
- **Core Competition Suite:** **33 / 33 passed (100% green)** in 24.88s.
- **Workflow Verification:** **11 / 11 surface workstation checkpoints passed**.
- **Multi-Viewport Responsive QA:** **35 / 35 checks passed** across 7 device resolutions with 0px horizontal overflow.
- **Full Repository Regression Suite:** **1,305 passed** tests across all simulation, kinematic, planetary data, and API modules.
- Validates autonomous science-tour optimization, multi-objective champion synthesis, non-dominated Pareto frontier extraction, multi-stop geometry invariants, vehicle locomotion modes, budget feasibility, disruption detours, custom interactive contingencies, compound multi-event simulation, workspace immutability, canonical run bundle schemas with cryptographic execution digests, Decision Pack ZIP extraction, independent deterministic replay reproduction, mid-sortie emergency handoffs, Sortie Black Box event ledgers, authentic NASA PDS environmental intelligence, reproducible mission science reporting, and Mission Readiness Decision Gate assurance evaluations. *(Note: Deferred subsystem prototypes are archived in the audit ledger at `docs/MISSION_17_FEATURE_AUDIT.md`.)*

### 🔬 Independent Replay & Verification for Judges
To independently verify the integrity and deterministic reproduction of any exported Decision Pack bundle without browser overhead:
```bash
# 1. Integrity and compatibility audit
python -c "import json; from marswalk.api.decision_pack import verify_bundle_integrity; b=json.load(open('mission_bundle.json')); print(verify_bundle_integrity(b))"

# 2. Authoritative engine replay reproduction
python -c "import json, rasterio; from marswalk.core.terrain import load_and_process_terrain; from marswalk.api.decision_pack import replay_decision_pack_bundle; t=load_and_process_terrain('data/processed/jezero_ready_20m.tif'); b=json.load(open('mission_bundle.json')); print(replay_decision_pack_bundle(b, t, rasterio.open('data/processed/jezero_ready_20m.tif').transform, []))"
```

---

## 📚 Scientific Provenance & Attribution

| Dataset / Model | Author / Source | Primary Citation |
| :--- | :--- | :--- |
| **Jezero 20m DTM** | USGS Astrogeology Science Center | NASA MRO Context Camera (CTX) Stereo Pairs |
| **Jezero 6m Ortho** | NASA / JPL / MSSS | MRO CTX Optical Observations (Calche & Hughes, 2020) |
| **Global Basemap** | USGS / NASA | Viking Orbiter MDIM 2.1 Mars Mosaic (232 m/pixel) |
| **Global Topography** | NASA / GSFC | MGS Mars Orbiter Laser Altimeter (MOLA) Gridded Data |
| **Crew EVA Speed** | NASA Apollo Program | Apollo Lunar Surface EVA Traverses (Walsh et al., 2022) |
| **Rover Dynamics** | NASA / JPL-Caltech | Mars 2020 Perseverance Mobility Performance (Farley et al., 2022) |
| **Terrain Cost** | Adapted Metabolic Model | Minetti et al. (2002) slope-energy expenditure relation |

---

## 🔧 Release Documentation & Verification Artifacts

- **Milestone 13K Goal-Driven Mission Design Compiler:** [`docs/milestone-13k-final-report.md`](docs/milestone-13k-final-report.md) — Natural-language mission intent parsing, remote sensing validation, Directed Acyclic Task Graph (DAG) decomposition, hard vs soft constraint engine, 7-level hierarchical fleet synthesis of 8 operational postures, non-dominated Pareto frontier extraction, forensic causal compilation debugger with 1-click relaxation, 6-scenario benchmark lab (Campaigns A–F), Atlas Mission Design Studio 2.0 interface, and 18-screenshot conference showcase gallery.
- **Milestone 13J Atlas Fleet Intelligence [DEFERRED]:** [`docs/milestone-13j-final-report.md`](docs/milestone-13j-final-report.md) — Multi-rover cooperative exploration, distributed science task allocation with authoritative instrument matching, multi-agent terrain-aware route coordination, 4D spatiotemporal deconfliction, and counterfactual disturbance recovery lab (F1–F7). *(Deferred to research archive per [docs/MISSION_17_FEATURE_AUDIT.md](docs/MISSION_17_FEATURE_AUDIT.md)).*
- **Milestone 13I Mission Assurance & Counterfactual Operations Lab:** [`docs/milestone-13i-final-report.md`](docs/milestone-13i-final-report.md) — Immutable campaign branching, deterministic replay, 20-rule invariant verification, 12 standardized planetary disturbance models, 3-way comparative workspace, optimistic concurrency promotion, Merkle cryptographic dossier, and conference showcase gallery.
- **Milestone 13H Campaign Operations Director (MOCC):** [`docs/milestone-13h-final-report.md`](docs/milestone-13h-final-report.md) — Multi-Sol mission orchestration, closed-loop execution, SHA-256 event deduplication, adaptive campaign replanning, flight-operations MOCC cockpit, 3D Mission Theater Story Mode, and conference showcase gallery.
- **Milestone 13G-R Science Return & Data Logistics Co-Design:** [`docs/milestone-13g-final-report.md`](docs/milestone-13g-final-report.md) — Multi-instrument observation scheduling, robotic arm turret singularity, exact First Law byte conservation ($S_{\text{used}} = S_{\text{gen}} - S_{\text{rel}}$), communications-aware simulated transfer, 8D Pareto optimization, Science Return Recovery Lab disturbance simulation, and conference showcase gallery.
- **Milestone 13F Energy & Resource Intelligence:** [`docs/milestone-13f-report.md`](docs/milestone-13f-report.md) — Resource-constrained traverse planning, terramechanical power budgeting ($W_r, W_g, E_m$), descent non-regenerative physics, 7-state feasibility classification, and conference showcase gallery.
- **Milestone 13E Joint Mission Co-Design [DEFERRED]:** [`docs/milestone-13e-report.md`](docs/milestone-13e-report.md) — Coupled traverse planning × orbital line-of-sight optimization with multi-dimensional Pareto frontier. *(Deferred to research archive per [docs/MISSION_17_FEATURE_AUDIT.md](docs/MISSION_17_FEATURE_AUDIT.md)).*
- **V2 Demonstration Runbook:** [`docs/v2-demonstration-runbook.md`](docs/v2-demonstration-runbook.md) — 5-minute interactive evaluator walkthrough covering the complete V2 multi-sol campaign orchestration lifecycle.
- **Scientific Evidence Traceability Matrix:** [`docs/scientific-evidence-traceability.md`](docs/scientific-evidence-traceability.md) — Rigorous audit mapping terrain, geodesy, atmospheric intelligence, kinematics, energy, Pareto optimization, and digital twin replay to primary citations and test suites.
- **Milestone 12A Hardening Report:** [`docs/milestone-12a-report.md`](docs/milestone-12a-report.md) — System hardening, resilience audit, performance measurements, and acceptance gate report.
- **V1 Demonstration Runbook:** [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md) — 60-second quickstart, 10-stage operator guide, visible outcomes, and troubleshooting.
- **V1 Release Checklist & Sign-Off:** [`docs/V1_RELEASE_CHECKLIST.md`](docs/V1_RELEASE_CHECKLIST.md) — Comprehensive 11-category acceptance audit.
- **Milestone 10H Packaging Report:** [`docs/milestone-10h-report.md`](docs/milestone-10h-report.md) — Final acceptance sign-off, test matrix, and commands.
- **Milestone 10H Design Specification:** [`docs/milestone-10h-design.md`](docs/milestone-10h-design.md) — Architectural packaging and reproducibility specification.
- **Engineering Handoff:** [`docs/CLAUDE_ENGINEERING_HANDOFF.md`](docs/CLAUDE_ENGINEERING_HANDOFF.md) — Architecture, design principles, API reference, and persistence governance.

---

## ⚠️ Scientific Research Prototype Disclaimer

> **IMPORTANT SCIENTIFIC DISCLOSURE:**  
> MarsWalk 2.0 is an interactive scientific research and mission rehearsal prototype developed for educational and mission analysis purposes during the NASA Space Apps Challenge. Modeled traverses, energy effort calculations, and disruption contingencies are mathematical approximations derived from remote-sensing products. **They are NOT certified as operationally safe for human astronaut EVA operations.** Real planetary extravehicular activities require high-resolution in-situ hazard surveys, real-time life-support consumables monitoring, and multi-redundant telemetry from certified ground mission control systems.
