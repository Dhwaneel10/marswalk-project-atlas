# Milestone 13G — Unified Science Return & Data Logistics Architecture Audit
## Coupled Science Prioritization, Observation Scheduling, Onboard Storage Management & Resource-Constrained Multi-Objective Optimization

**System:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Milestone:** 13G — Atlas Science Return & Data Logistics Co-Design  
**Date:** 2026-11-01  
**Execution Environment:** Windows 11 (64-bit), Python 3.12.4 (`.venv`), Vanilla JS / Three.js Frontend, Atlas API Daemon on port 3000  
**Contributors:** Agent A (Science Scheduling), Agent B (Data & Storage), Agent C (Optimization Engine), Agent D (Validation & UI)  
**Status:** COMPLETE ARCHITECTURAL SYNTHESIS  

---

## 1. Executive Summary & Problem Formulation

MarsWalk 2.0 has progressively built a multi-layered mission simulation and planning platform:
- **Milestones 11–12:** Calibrated terramechanics, slope cost modeling, and kinematic traverse generation across the USGS 20m Jezero Crater CTX DTM.
- **Milestone 13D:** Terrain-aware line-of-sight raycasting and Mars RelayNet topological optimization.
- **Milestone 13E:** Joint traverse-relay co-design and bi-objective Pareto trade-off analysis.
- **Milestone 13F:** First-principles rover/relay electrical and mechanical energy budgeting.

Despite these advancements, an essential dimension of planetary exploration remained disconnected: **Science Return and Data Logistics**.

In authentic planetary exploration (e.g. NASA Mars 2020 *Perseverance*, MSL *Curiosity*), rovers do not traverse extreme terrain merely to accumulate kilometers or maintain continuous radio contact. Missions exist to conduct scientific investigations, characterize mineralogy, capture high-resolution imagery, and collect core samples. However, scientific return is bound by strict physical and logistical realities:
1. **Instrument Electrical Demands:** Active instruments (spectrometers, corers, lasers) consume substantial battery energy ($15\text{ W}$ to $145\text{ W}$) and require significant dwell time ($180\text{ s}$ to $5,400\text{ s}$).
2. **Onboard Storage Saturation:** Flash storage partitions ($4\text{ GB}$ to $64\text{ GB}$) fill rapidly. Generating data faster than it can be transferred leads to storage exhaustion and lost observations.
3. **Verified Storage Release Invariant:** A fundamental spaceflight rule dictates that onboard memory can **never** be released until an end-to-end receipt has been acknowledged and cryptographically verified.
4. **Episodic Communications Logistics:** Ground-to-base and ground-to-relay data offload is strictly intermittent, governed by line-of-sight visibility, relay availability, and configured channel bitrates.

Milestone 13G establishes the **Science Return & Data Logistics Co-Design Engine**, synthesizing target prioritization, multi-instrument scheduling, byte-level storage accounting, and 8-dimensional Pareto optimization into a unified, reproducible system.

---

## 2. Agent A Synthesis: Science Prioritization & Activity Scheduling

### 2.1 Scientific Priority Classification
To uphold the NASA Space Apps scientific integrity requirement (*"Never invent measurements or present synthetic data as real Martian observations"*), priorities are rigorously partitioned into three explicit categories:
1. **`USER_ASSIGNED_PRIORITY`:** Configured via operator preference (UI slider or optimization profile). Represents subjective mission preference, not intrinsic scientific ground truth.
2. **`SOURCE_DERIVED_PRIORITY`:** Populated from peer-reviewed literature or NASA PDS/CRISM spectral products (e.g., Farley et al. 2022, Scheller et al. 2022). Documented as derived from cited sources with full provenance.
3. **`UNASSESSED_PRIORITY`:** Applied to gazetteer targets lacking campaign evaluation ($0.0$ default). The scheduler prohibits unassessed waypoints from preempting evaluated targets without explicit user override.

### 2.2 Science Objectives & 7-Instrument Taxonomy
The engine defines 6 standardized mission objectives (`GEOLOGICAL_CHARACTERIZATION`, `MINERALOGICAL_INVESTIGATION`, `ATMOSPHERIC_OBSERVATION`, `SURFACE_MORPHOLOGY`, `ENVIRONMENTAL_MONITORING`, `ASTROBIOLOGY_BIOSIGNATURE_SURVEY`) and a comprehensive 7-instrument taxonomy based on Mars 2020 flight systems:
- **Mastcam-Z (Mast):** `PANO_360_COLOR` (1200s, 17.4W, 112.5MB), `MULTISPECTRAL_STEREO` (600s, 19.8W, 60MB), `SUN_PHOTOMETRY` (180s, 12W, 3MB).
- **SuperCam (Mast):** `LIBS_BURST` (900s, 38W, 18MB), `RAMAN_SPECTRA` (1500s, 42W, 37.5MB), `RMI_RASTER` (400s, 25W, 17.1MB).
- **PIXL (Turret):** `CONTACT_SCAN_ALIGN` (600s, 15W, 5MB), `XRF_ELEMENTAL_GRID` (3600s, 25W, 34MB), `XRF_HIGH_DEF` (14400s, 22W, 100MB).
- **SHERLOC + WATSON (Turret):** `WATSON_MICRO_IMAGE` (300s, 12W, 13.3MB), `DUV_RAMAN_SCAN` (2400s, 48W, 55MB).
- **RIMFAX (Radar):** `DRIVE_SOUNDING` (continuous 8.5W, 3.3MB/km during traverse), `DEEP_SOUNDING_STATIONARY` (600s, 11W, 16.7MB).
- **MEDA (Meteorology):** `METEOROLOGY_CONTINUOUS` (continuous 17W, 6MB/sol), `HIGH_RATE_TURBULENCE` (1800s, 21W, 17.5MB).
- **Coring Tool (Turret):** `ABRASION_PATCH` (1800s, 115W, 4MB), `SAMPLE_CORE_EXTRACTION` (5400s, 145W, 10MB).

*Interlocks:* Enforces robotic arm turret singularity (PIXL, SHERLOC, and Coring Tool cannot operate simultaneously) and chassis stability constraints (drive motors locked during spectroscopy).

### 2.3 5-Phase Chronological Observation Schedule
Each observation stop decomposes into five deterministic operational phases:
1. **Phase 1: Rover Arrival & Settle** (180s, 130W) — Wheel brake lock, IMU stabilization.
2. **Phase 2: Instrument Preparation & Warmup** (300–600s, 165W) — Arm un-stow, de-icing heaters, calibration.
3. **Phase 3: Observation Execution** (180–5400s, 130–255W) — Active sensor integration.
4. **Phase 4: Data Post-Processing & Cache** (120s, 135W) — Wavelet compression, SHA-256 fingerprinting.
5. **Phase 5: Instrument Stow & Secure** (240s, 150W) — Turret arm park, mast azimuth lock.

---

## 3. Agent B Synthesis: Onboard Data & Storage Ledger

### 3.1 Data Product Lifecycle & Immutability
Every generated data product is modeled as an immutable `MissionDataProduct` featuring:
- Unique ID (`dp_<uuid>`), parent observation ID, target ID, and instrument attribution.
- Data category (`ENVIRONMENTAL_TELEMETRY`, `MULTISPECTRAL_IMAGERY`, `HIGH_RES_PANORAMA`, `SPECTRAL_CUBE`, `SUBSURFACE_RADAR`, `ENGINEERING_LOG`).
- Exact byte size and 64-character SHA-256 fingerprint:
  $$\text{checksum\_sha256} = \text{SHA-256}(\text{product\_id} \parallel \text{instrument\_id} \parallel \text{size\_bytes} \parallel t_{\text{created}})$$
- Mandatory synthetic disclosures (`is_synthetic: True`, `is_simulated: True`).

### 3.2 Exact Byte Conservation Law
Onboard flash storage is governed by a strict First-Law conservation identity:
$$S_{\text{used}, t} = S_{\text{used}, t-1} + S_{\text{generated}, t} - S_{\text{released}, t}$$
- **Release Precondition Invariant:** $S_{\text{released}, t} \equiv 0$ unless the data product's transfer to the surface base has been verified and recorded.
- **Backlog Conservation:**
  $$D_{\text{backlog}, t} = D_{\text{collected}, t} - D_{\text{transferred}, t} - D_{\text{released}, t}$$
- **Zero-Drift Assertion:** The ledger verifies $\epsilon_{\text{conservation}} \equiv 0$ at every step.

### 3.3 Storage Policies & Pressure Alert State Machine
- **Retention Tiers:** `PROTECTED_PERMANENT` (inviolable sample records), `TRANSFER_THEN_RELEASE` (standard science), `VOLATILE_SCRATCH` (discardable telemetry).
- **Pressure States:**
  - `STORAGE_AVAILABLE`: $\rho_S = S_{\text{used}} / S_{\text{capacity}} < 0.60$
  - `STORAGE_PRESSURE`: $0.60 \le \rho_S < 0.80$
  - `STORAGE_NEAR_CAPACITY`: $0.80 \le \rho_S < 0.95$
  - `STORAGE_CAPACITY_REACHED`: $\rho_S \ge 0.95$
  - `TRANSFER_QUEUE_BACKLOG`: Pending queue backlog $> 100\text{ MB}$
  - `HIGH_PRIORITY_DATA_PENDING`: Critical science pending un-offloaded $> 3600\text{ s}$

### 3.4 Communications-Aware Simulated Data Transfer Model
- **Deterministic Offload Model:**
  $$D_{\text{transferred}}(\Delta t) = R_{\text{configured}} \cdot (1 - \eta_{\text{overhead}}) \cdot \delta_{\text{comm}} \cdot \Delta t$$
- **Coupling to RelayNet:** Transfer occurs only during `CONNECTED_DIRECT` or `CONNECTED_RELAYED` states. During `SIMULATED_GEOMETRIC_CONNECTIVITY_GAP`, transfer rate is strictly $0\text{ bps}$.
- **Truth Disclosures:** Surface base destination only; no Mars-to-Earth DSN downlink claims.

---

## 4. Agent C Synthesis: Optimization Engine & 8D Pareto Analysis

### 4.1 Co-Design State Vector & Two-Stage Gating
The co-design plan is formulated as an 8-tuple state:
$$\mathcal{C} = \Big\langle \mathcal{T}, \mathcal{S}, \Pi_{\text{obs}}, \mathcal{R}, \mathbf{E}(t), \mathbf{D}(t), \mathbf{S}(t), \mathbf{B}(t) \Big\rangle$$
Candidates undergo strict two-stage hard constraint gating:
1. **Hard Feasibility Gates (Rejection):**
   - Minimum vehicle energy: $\min_t E_{\text{rover}}(t) \ge E_{\text{reserve}}$ (typically 20%).
   - Relay battery reserves: $\min_t E_{\text{relay}, j}(t) \ge E_{\text{relay, min}}$ for all $j \in \mathcal{R}$.
   - Mission duration: $T_{\text{mission}} \le T_{\text{limit}}$ (88,775 s / 1 Sol).
   - Storage capacity: $\max_t S_{\text{used}}(t) \le S_{\text{capacity}}$.
   - Terrain slope: $\max \theta \le 25^\circ$.
   *High science return CANNOT override hard feasibility failures.*
2. **Multi-Objective Optimization Vector:**
   - Maximize Science Utility $U_{\text{science}} = \sum w_i S_i$
   - Minimize Energy Consumed $E_{\text{total}}$
   - Minimize Mission Duration $T_{\text{mission}}$
   - Minimize Relay Count $|\mathcal{R}|$
   - Maximize Communications Coverage $C_{\text{geom}}$
   - Maximize Data Transferred $D_{\text{transferred}}$
   - Minimize Storage Peak $\max S_{\text{used}}$
   - Minimize Final Backlog $D_{\text{backlog}}(T)$

### 4.2 Marginal Rate of Substitution (MRS)
To provide actionable trade-off explanations, the engine computes:
$$\text{MRS}_{E, S} = \frac{\Delta E}{\Delta U_{\text{science}}} \quad \left[\frac{\text{Wh}}{\text{point}}\right], \quad \text{MRS}_{D, S} = \frac{\Delta D_{\text{transferred}}}{\Delta U_{\text{science}}} \quad \left[\frac{\text{MB}}{\text{point}}\right]$$

---

## 5. Agent D Synthesis: Validation Engineering Matrix & UI Architecture

### 5.1 9-Step Guided Joint Mission Studio
Expands the existing stepper navigation into a 9-step workflow:
1. **Step 1: Targets** — Curated Jezero target selection, priority tiers, objective weight normalization.
2. **Step 2: Mobility** — Rover mass, battery capacity, rolling resistance, drive speed.
3. **Step 3: Comms** — Promontory selection, relay mast heights, LOS raycasting parameters.
4. **Step 4: Energy** — Electrical base loads, reserve margin threshold, thermal heater loads.
5. **Step 5: Payload** — Instrument selection cards, operating modes, observation duration overrides.
6. **Step 6: Storage** — Flash storage capacity, transfer rates, retention and overflow policies.
7. **Step 7: Optimize** — Autonomous co-design solver execution.
8. **Step 8: Pareto** — 5 Pareto visualization modes, 13-column feasibility scorecard table, MRS trade-off cards.
9. **Step 9: Export** — Plan promotion, JSON manifest download, Markdown mission dossier export.

### 5.2 3D Mission Theater Data Logistics Digital Twin
- **Telemetry HUD Drawer:** Flash storage fill gauge bar ($S_{\text{used}} / S_{\text{capacity}}$), live transfer rate ($2.0\text{ Mbps}$ in LOS / $0$ in blackout), transfer queue backlog ($MB$), and accumulated science points.
- **3D Science Target Beacons:** Interactive pulsing cylinders (Cyan = Pending, Pulsing Gold = In-Observation, Emerald = Completed, Gray = Descheduled).
- **Synchronized Timeline Scrubber:** Dynamic scrubbing updates battery drain, observation data generation, and contact-window queue flushing simultaneously.
- **Spatial Raycast Inspector:** Raycasting on beacons and data product markers reveals detailed telemetry.

### 5.3 Automated Browser CDP Acceptance & Quality Gates
Automation script `scripts/verify_science_mission_browser.py` enforces:
- Zero console errors and zero horizontal body overflow (`scrollWidth <= innerWidth`).
- Responsive verification across $1920\times 1080$ and $1366\times 768$ viewports.
- 8 conference showcase screenshots captured to `outputs/conference_showcase/science_logistics/`.

---

## 6. Mathematical Invariants & Scientific Integrity Summary

| Invariant / Law | Formal Definition | Enforcement Location |
| :--- | :--- | :--- |
| **First-Law Energy Balance** | $\|E_{\text{start}} - (E_{\text{rem}} + \sum E_{\text{consumed}})\| \le 10^{-4}\text{ J}$ | `mission_resource_model.py` |
| **First-Law Byte Conservation** | $S_{\text{used}, t} = S_{\text{used}, t-1} + S_{\text{gen}, t} - S_{\text{rel}, t}$ | `mission_data_ledger.py` |
| **Storage Release Precondition** | $S_{\text{rel}, t} > 0 \implies \text{status}(p) == \text{TRANSFERRED}$ | `mission_data_ledger.py` |
| **Backlog Conservation** | $D_{\text{backlog}} = D_{\text{gen}} - D_{\text{transferred}} - D_{\text{released}}$ | `mission_data_ledger.py` |
| **Hard Constraint Dominance** | Violations $\implies \text{Candidate Feasibility} = \text{False}$ | `joint_mission_planner.py` |
| **Conservative Descent Baseline** | `allow_regenerative_braking: False` by default | `mission_resource_model.py` |
| **Synthetic Data Disclosures** | Explicit `SIMULATED_DATA_TRANSFER` and synthetic tags | Schemas, API, UI, Docs |

---

## 7. Next Steps: Implementation Sequence

1. **Implement Core Engine:** `src/marswalk/core/mission_data_ledger.py`.
2. **Implement Core Engine:** `src/marswalk/core/science_mission_planner.py`.
3. **Extend Co-Design Engine:** `src/marswalk/core/joint_mission_planner.py`.
4. **Author Schemas & API Endpoints:** `schemas/api/v1/` and `src/marswalk/api/service.py`.
5. **Implement Test Suite:** `tests/test_milestone_13g_science_mission.py` and run quality gates.
6. **Extend Frontend:** `web/index.html`, `web/styles.css`, and `web/app.js`.
7. **Run Browser CDP Acceptance:** `scripts/verify_science_mission_browser.py`.
8. **Finalize Documentation & Showcase Packaging.**
