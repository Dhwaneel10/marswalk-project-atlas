# Milestone 13G — Agent D: Validation & UI Engineering Audit
## Science Return, Onboard Storage Logistics, Multi-Objective Co-Design & Digital Twin Verification

**Milestone:** 13G — Science Mission Planning, Payload Logistics & Pareto Co-Design  
**Subsystem Role:** Agent D — Validation, UI Engineering & Scientific Integrity  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Target Specifications:** Vanilla JS / Three.js Frontend, FastAPI/Uvicorn Daemon (Port 3000), Pytest Suite, Chrome DevTools Protocol (CDP) Headless Automation  
**Date:** 2026-11-01  
**Status:** COMPLETE ARCHITECTURAL SPECIFICATION & INTEGRATION AUDIT  

---

## 1. Executive Summary

Milestone 13G elevates MarsWalk 2.0 / Project Atlas from a resource-aware traverse and communications planner into a comprehensive **Planetary Science Mission & Data Logistics Co-Design System**.

In authentic planetary exploration, rovers do not traverse extreme terrain merely to reach geometric coordinates or maintain radio contact. Traverses are undertaken to collect high-value scientific observations, drill geologic cores, characterize mineralogical spectra, and log subsurface stratigraphy. However, scientific return is bound by severe physical constraints:
1. **Instrument Electrical Budgets:** Active instruments (e.g. Raman spectrometers, rock abrasion tools, standoff lasers) draw substantial peak power during dwell periods.
2. **Onboard Solid-State Storage Capacity:** Rover flash storage is finite. If observations generate data faster than the communications infrastructure can transfer it to orbiters or base stations, onboard storage overflows, forcing either the rejection of new observations or hazardous FIFO data overwrites.
3. **Discontinuous Simulated Transfer Opportunities:** High-rate data transfers are only possible during line-of-sight contact windows with surface relay nodes or orbital passes.

As **Agent D (Validation and UI)**, this audit delivers the end-to-end integration and verification architecture for Milestone 13G across five core engineering pillars:
1. **Joint Mission Design Studio UI Extension:** Transforms the existing 7-step wizard into a coherent 9-step guided science and data logistics co-design workflow with science target prioritization, instrument operating profiles, onboard storage budgeting, a multi-dimensional Pareto explorer, and an expanded comparative feasibility scorecard.
2. **3D Mission Theater Data Logistics Digital Twin:** Enhances the 3D cockpit HUD with real-time storage fill gauge telemetry, simulated data transfer rates, queue backlog counters, pulsing 3D science target status beacons, dynamic timeline scrubber synchronization, and interactive spatial raycasting for science data products.
3. **Comprehensive Test Engineering Matrix:** Establishes the 36-test specification for `tests/test_milestone_13g_science_mission.py` covering priority utility scoring, instrument-observation compatibility, exact byte conservation, storage overflow rejection, simulated multi-hop transfers, and multi-objective Pareto optimality.
4. **Automated Browser CDP Acceptance Suite:** Formulates the automation script `scripts/verify_science_mission_browser.py` capturing 8 conference showcase screenshots across $1920\times 1080$ and $1366\times 768$ viewports with zero console errors and zero horizontal body overflow.
5. **Scientific Integrity Correction for Milestone 13F:** Formulates the required documentation updates reclassifying non-regenerative descent from an asserted Mars 2020 flight fact into a conservative configurable modeling assumption (`allow_regenerative_braking: False`), maintaining strict NASA Space Apps scientific standards.

---

## 2. Joint Mission Design Studio UI Extension

The current 7-step Joint Mission Studio (`web/index.html` lines 1645–2120) seamlessly couples terrain traverse planning, RelayNet communications, and Milestone 13F electrical power budgeting. Milestone 13G expands this workflow into a **9-Step Coherent Science & Data Logistics Studio**.

### 2.1 Stepper Navigation Re-Architecture
To maintain clean typography and prevent horizontal wrapping on compact displays ($1366\times 768$), the stepper navigation (`#jointWizardStepper`) expands from 7 to 9 steps with optimized grid layout:

```html
<!-- 9-Step Guided Wizard Stepper (Milestone 13G) -->
<div class="joint-stepper-container" style="margin-bottom:10px;">
  <div class="joint-stepper-nav" id="jointWizardStepper" style="grid-template-columns: repeat(9, 1fr);">
    <button class="joint-step-btn active" data-step="1" title="Step 1: Mission Endpoints & Science Target Selection">
      <span class="step-num">1</span><span class="step-name">Targets</span>
    </button>
    <button class="joint-step-btn" data-step="2" title="Step 2: Configure Mobility Platforms">
      <span class="step-num">2</span><span class="step-name">Mobility</span>
    </button>
    <button class="joint-step-btn" data-step="3" title="Step 3: Mars RelayNet Communications">
      <span class="step-num">3</span><span class="step-name">Comms</span>
    </button>
    <button class="joint-step-btn" data-step="4" title="Step 4: Energy Budgets & Subsystems">
      <span class="step-num">4</span><span class="step-name">Energy</span>
    </button>
    <button class="joint-step-btn" data-step="5" title="Step 5: Science Payload & Instrument Operating Profiles">
      <span class="step-num">5</span><span class="step-name">Payload</span>
    </button>
    <button class="joint-step-btn" data-step="6" title="Step 6: Onboard Storage & Simulated Transfer Logistics">
      <span class="step-num">6</span><span class="step-name">Storage</span>
    </button>
    <button class="joint-step-btn" data-step="7" title="Step 7: Autonomous Co-Design Optimization">
      <span class="step-num">7</span><span class="step-name">Solve</span>
    </button>
    <button class="joint-step-btn" data-step="8" title="Step 8: Multi-Objective Pareto Frontier & Feasibility Scorecard">
      <span class="step-num">8</span><span class="step-name">Pareto</span>
    </button>
    <button class="joint-step-btn" data-step="9" title="Step 9: Mission Promotion & Scientific Dossier Export">
      <span class="step-num">9</span><span class="step-name">Promote</span>
    </button>
  </div>
</div>
```

### 2.2 Detailed Step-by-Step UI Specifications

#### Step 1: Mission Endpoints & Science Target Prioritization (`#jointStepPanel1`)
Extends Step 1 beyond start/goal coordinate definition to include interactive science target prioritization:
- **Origin & Destination:** Preserves baseline selection (Octavia Butler Base `[117, 157]` $\rightarrow$ Delta Remnant `[138, 114]`).
- **Science Target Registry Checklist:** An interactive multi-select list displaying authentic Jezero Crater locations:
  1. *Delta Remnant / Three Forks* (`[138, 114]`, Priority: Critical, Category: Fluvial-Deltaic Sediments)
  2. *Kodiak Butte Promontory* (`[175, 122]`, Priority: High, Category: Stratigraphic Butte Architecture)
  3. *Séítah Carbonates Region* (`[150, 140]`, Priority: High, Category: Olivine-Carbonate Igneous Base)
  4. *Belva Crater Rim Lookout* (`[95, 185]`, Priority: Medium, Category: Impact Ejecta & Megabreccia)
  5. *Neretva Vallis Inflow Channel* (`[110, 85]`, Priority: Medium, Category: Hydrodynamic Valley Network)
- **Target Priority Configuration:** Users can assign priority tiers (`CRITICAL = 100`, `HIGH = 75`, `MEDIUM = 50`, `LOW = 25`) or define custom numeric utilities ($U_i \in [1, 100]$).
- **Objective Weight Normalization Bar:** Sliders for:
  - Traverse Distance ($w_{\text{dist}}$, default 0.25)
  - Comms Line-of-Sight ($w_{\text{los}}$, default 0.25)
  - Battery Energy ($w_{\text{energy}}$, default 0.25)
  - Science Return Utility ($w_{\text{sci}}$, default 0.25)
  - One-click normalization button ($\sum w_i = 1.0$) and pre-configured presets (*Balanced*, *Science-Maximizing*, *Comms-First*, *Energy-Conserving*).
- **Scientific Disclosure Badge:** "Utility scores represent user-configured planning preferences, not objective absolute scientific value."

#### Step 5: Science Payload & Instrument Operating Profiles (`#jointStepPanel5`)
A dedicated instrument configuration panel allowing users to inspect and toggle scientific payload instruments:
- **Synthetic Instrument Catalog Cards:**
  1. **Mastcam-Z (Multispectral Stereoscopic Imager):**
     - Base Load: $18.5\text{ W}$, Dwell: $180\text{ s}$, Data Yield: $45.0\text{ MB/obs}$
     - Target Compatibility: Surface Morphology, Geology, Visual Context
  2. **SuperCam (Standoff Laser-Induced Breakdown Spectroscopy - LIBS):**
     - Base Load: $65.0\text{ W}$, Dwell: $600\text{ s}$, Data Yield: $28.0\text{ MB/obs}$
     - Target Compatibility: Mineralogy, Elemental Chemistry, Acoustic
  3. **PIXL (Planetary Instrument for X-ray Lithochemistry):**
     - Base Load: $42.0\text{ W}$, Dwell: $1200\text{ s}$, Data Yield: $16.0\text{ MB/obs}$
     - Target Compatibility: Micro-Scale Elemental Geochemistry
  4. **SHERLOC (Deep UV Raman & Luminescence for Organics):**
     - Base Load: $58.0\text{ W}$, Dwell: $1500\text{ s}$, Data Yield: $35.0\text{ MB/obs}$
     - Target Compatibility: Organic Biosignatures, Astrobiology
  5. **RIMFAX (Radar Imager for Mars' Subsurface Experiment):**
     - Base Load: $12.0\text{ W}$, Dwell: Continuous along traverse, Data Yield: $2.5\text{ MB/km}$
     - Target Compatibility: Subsurface Dielectric Stratigraphy
  6. **MEDA (Mars Environmental Dynamics Analyzer):**
     - Base Load: $15.0\text{ W}$, Dwell: Continuous background, Data Yield: $0.8\text{ MB/hr}$
     - Target Compatibility: Atmospheric Pressure, Dust, Wind, Radiation
- **Instrument Preset Configurations:**
  - *Comprehensive Analytical Suite:* Mastcam-Z + SuperCam + PIXL + SHERLOC + RIMFAX ($195.5\text{ W}$ peak, $126.5\text{ MB/site}$)
  - *Rapid Reconnaissance:* Mastcam-Z + SuperCam + RIMFAX ($95.5\text{ W}$, $75.5\text{ MB/site}$)
  - *Astrobiology Core Survey:* Mastcam-Z + PIXL + SHERLOC ($118.5\text{ W}$, $96.0\text{ MB/site}$)
  - *Ultralight Survey:* Mastcam-Z + MEDA ($33.5\text{ W}$, $45.8\text{ MB/site}$)
- **Incompatible Combination Interlocks:** UI dynamically prevents invalid instrument-target assignments (e.g. attempting contact Raman spectroscopy on an inaccessible distant promontory) and shows explanatory tooltips.

#### Step 6: Onboard Storage & Simulated Transfer Logistics (`#jointStepPanel6`)
Configures the rover's onboard solid-state mass memory and simulated communications transfer pipeline:
- **Onboard Flash Memory Capacity Slider:**
  - Range: $4\text{ GB}$ to $64\text{ GB}$ (Default: $16\text{ GB} = 16,384\text{ MB}$)
  - Reserve Buffer Margin Slider: $10\%$ to $35\%$ (Default: $20\% = 3,276.8\text{ MB}$)
- **Storage Management Retention Policies (Dropdown):**
  - `RETAIN_UNTIL_VERIFIED_TRANSFER` (Default / Recommended): Data products remain locked in storage until end-to-end simulated transfer receipt is confirmed.
  - `PRIORITY_FIFO_EVICTION`: Lower-priority environmental data products may be pruned if storage enters `STORAGE_PRESSURE` state.
  - `STRICT_OVERFLOW_REJECT`: Solver immediately rejects candidate schedules that exceed usable storage capacity ($S_{\text{used}} > S_{\text{max}} \cdot (1 - \text{margin})$).
- **Simulated RelayNet Transfer Parameters:**
  - Configured Transfer Rate ($R_{\text{config}}$): Dropdown with options:
    - $256\text{ kbps}$ (Direct-to-Base Low Power UHF)
    - $2.0\text{ Mbps}$ (High-Gain Line-of-Sight RelayNet Mast)
    - $5.0\text{ Mbps}$ (High-Elevation Relay Promontory Optical/Ka-Band)
  - Protocol Transfer Overhead ($\eta_{\text{proto}}$): Configurable $5\%$ to $20\%$ packet framing and retransmission penalty.
  - Transfer Initiation Window: Option to require minimum continuous contact duration (e.g., $\ge 60\text{ s}$) before initiating high-rate transfer sessions.
- **Scientific Disclosure Badge:** "Transfer rates model simulated bandwidth between surface assets; no actual interplanetary RF transmissions are executed."

#### Step 8: Multi-Objective Pareto Frontier & Feasibility Scorecard (`#jointStepPanel8`)
The central decision studio combining multi-criteria visualization and deep feasibility auditing:
- **Multi-Metric Pareto Dimension Switcher (5 Operational Modes):**
  1. $\text{Mode 1: } \text{Science Return (Points) vs Energy Consumed (Wh)}$ [Primary Science Optimization]
  2. $\text{Mode 2: } \text{Science Return (Points) vs Data Transferred (MB)}$ [Data Return Throughput]
  3. $\text{Mode 3: } \text{Science Return (Points) vs Peak Storage Occupancy (MB)}$ [Buffer Pressure]
  4. $\text{Mode 4: } \text{Energy Consumed (Wh) vs Traverse Distance (m)}$ [Terramechanical Efficiency]
  5. $\text{Mode 5: } \text{Traverse Distance (m) vs Max Comms Gap (s)}$ [Line-of-Sight Safety]
- **Interactive 2D Canvas Plotter (`#paretoScatterCanvas`):**
  - Dynamically updates axis labels, min/max scaling, and efficiency frontier curve based on active mode.
  - Non-dominated (Rank 1) candidates highlighted in vibrant emerald (`#10b981`), dominated alternatives in muted slate (`#64748b`), active selection with glowing cyan ring (`#00e5ff`).
  - Rich hover tooltip displaying: Candidate ID, Strategy Name, Science Score, Total Energy, Data Collected, Data Transferred, and Max Storage Fill %.
- **Comprehensive Comparative Scorecard Table (`#paretoScorecardTable`):**
  Expanded table schema featuring 13 critical decision columns:
  | ID | Strategy | Rank | Distance (m) | Duration (min) | Comms (%) | Relays | Science (Pts) | Data Gen (MB) | Transferred (MB) | Storage Peak (MB) | Energy (Wh) | Feasibility Badge |
  - Feasibility badge styling:
    - `FEASIBLE (OK)`: Solid Green badge (`#10b981`)
    - `FEASIBLE (LOW RESERVE)`: Amber badge (`#f59e0b`)
    - `STORAGE PRESSURE`: Orange badge (`#fb923c`)
    - `STORAGE OVERFLOW`: Crimson badge (`#ef4444`)
    - `ENERGY VIOLATION`: Crimson badge (`#ef4444`)
- **Decision Rationale & Physical Trade-off Attribution Card:**
  Computes and displays exact Marginal Rates of Substitution (MRS):
  $$\text{MRS}_{E, S} = \frac{\Delta E}{\Delta \text{Science Points}} \quad [\text{Wh / Point}]$$
  $$\text{MRS}_{D, S} = \frac{\Delta \text{Data Transferred}}{\Delta \text{Science Points}} \quad [\text{MB / Point}]$$

---

## 3. 3D Mission Theater Data Logistics Layer

The 3D Mission Theater (`web/app.js`) provides an immersive, interactive digital twin of the Martian surface in Jezero Crater. Milestone 13G introduces the **Data Logistics Subsystem Telemetry** directly into the theater cockpit HUD, dynamic timeline scrubber, and 3D spatial raycast inspector.

### 3.1 In-Cockpit HUD Telemetry Drawer Additions
Located inside the Mission Theater Drawer (`#jointMissionDrawerContent`), adjacent to the Milestone 13F Battery SOC Gauge:

```html
<!-- Data Logistics Subsystem Telemetry (Milestone 13G) -->
<div class="theater-logistics-section" style="margin-top:6px; padding:6px 8px; border-radius:4px; background:rgba(0,0,0,0.35); border:1px solid rgba(255,255,255,0.08);">
  <div class="jointstudio-section-title" style="font-size:8px; font-weight:700; color:var(--telemetry-cyan); margin-bottom:4px; letter-spacing:0.5px;">
    DATA LOGISTICS &amp; STORAGE STATUS
  </div>
  
  <!-- Onboard Flash Storage Gauge -->
  <div style="margin-bottom:6px;">
    <div style="display:flex; justify-content:space-between; font-size:8px; margin-bottom:2px;">
      <span style="color:#94a3b8; font-weight:600;">FLASH STORAGE:</span>
      <span id="jointTheaterStorageVal" class="font-mono text-cyan" style="font-weight:700;">3,420 / 16,384 MB (20.9%)</span>
    </div>
    <div class="theater-storage-gauge-track" style="position:relative; width:100%; height:6px; background:rgba(255,255,255,0.1); border-radius:3px; overflow:hidden;">
      <div id="jointTheaterStorageBar" class="theater-storage-gauge-fill" style="width:20.9%; height:100%; background:#10b981; transition:width 0.2s ease, background 0.3s ease;"></div>
      <div class="theater-storage-threshold-marker" style="position:absolute; top:0; bottom:0; left:80%; width:2px; background:#f59e0b;" title="80% Storage Pressure Floor"></div>
    </div>
  </div>

  <!-- Real-time Data Metrics Rows -->
  <div class="jointstudio-telemetry-row">
    <span class="jointstudio-telemetry-key">SCIENCE RETURN:</span>
    <span id="jointTheaterSciencePoints" class="jointstudio-telemetry-val text-emerald" style="font-weight:700;">345 / 420 pts (82.1%)</span>
  </div>
  <div class="jointstudio-telemetry-row">
    <span class="jointstudio-telemetry-key">DATA GENERATED:</span>
    <span id="jointTheaterDataGen" class="jointstudio-telemetry-val">4,280 MB (38 products)</span>
  </div>
  <div class="jointstudio-telemetry-row">
    <span class="jointstudio-telemetry-key">DATA TRANSFERRED:</span>
    <span id="jointTheaterDataTransferred" class="jointstudio-telemetry-val text-cyan">3,120 MB (72.9%)</span>
  </div>
  <div class="jointstudio-telemetry-row">
    <span class="jointstudio-telemetry-key">TRANSFER QUEUE:</span>
    <span id="jointTheaterTransferQueue" class="jointstudio-telemetry-val text-amber">1,160 MB pending (8 items)</span>
  </div>
  <div class="jointstudio-telemetry-row">
    <span class="jointstudio-telemetry-key">LINK TRANSFER RATE:</span>
    <span id="jointTheaterTransferRate" class="jointstudio-telemetry-val font-mono" style="color:#38bdf8;">2.0 Mbps (Active LOS)</span>
  </div>
</div>
```

### 3.2 3D Science Target Status Beacons
To visually distinguish observation waypoints from standard navigation waypoints, the 3D scene creates dedicated `ScienceBeacon` meshes:
- **Geometry:** A composite Three.js object consisting of:
  - A vertical cylindrical light beacon ($r = 6\text{ m}, h = 120\text{ m}$) anchored on USGS CTX elevation.
  - A concentric pulsating ground ring ($r = 25\text{ m}$) that animates via vertex shader or delta-time scaling.
  - An overhead holographic billboard displaying target acronym (e.g., `DELTA-REM`, `SEITAH-CARB`) and priority badge.
- **Dynamic Color States:**
  - *Pending / Unvisited:* Translucent Cyan (`rgba(0, 229, 255, 0.45)`)
  - *In-Progress / Active Dwell:* Pulsing Goldenrod (`#f59e0b`) with outward concentric wave rings
  - *Observation Complete / Core Acquired:* Solid Emerald Green (`#10b981`) with permanent vertical beam
  - *Descheduled / Resource Pruned:* Muted Charcoal Gray (`#64748b`, $0.2$ opacity)

### 3.3 Dynamic Timeline Scrubber Synchronization
When the mission playback scrubber moves across time $t \in [0, T_{\text{mission}}]$:
- The system queries the `MissionDataLedger` timeline index for the active interval.
- **Dynamic State Transitions:**
  1. *Traverse Segments:* Rover battery drains according to terramechanical work ($W_r + \max(0, W_g)$) and base electrical load; storage remains constant; transfer rate shows $0\text{ kbps}$ if occluded or $R_{\text{config}}$ if in LOS to RelayNet.
  2. *Science Observation Segments:* Rover halts at target; instrument active load draws high power ($P_{\text{base}} + P_{\text{inst}}$); observation data products accumulate incrementally into flash storage; `#jointTheaterStorageBar` animates upwards; `#jointTheaterTransferQueue` backlog grows.
  3. *Simulated Transfer Segments:* When in LOS of a RelayNet node or Base Station with active transfer window, data transmits at $R_{\text{config}} \cdot (1 - \eta_{\text{proto}})$; `#jointTheaterDataTransferred` increments; `#jointTheaterTransferQueue` diminishes; flash storage releases transferred buffers if policy allows.
- **Dynamic Gauge Thresholds:**
  If storage exceeds $80\%$, the storage gauge smoothly shifts from `#10b981` (green) to `#f59e0b` (amber). If storage exceeds $95\%$, it pulses `#ef4444` (crimson).

### 3.4 Spatial Raycast Inspector Extension
Extends `showTheaterSpatialInspector(type, data, pt)` in `web/app.js` with two new interactive raycast targets:
1. `type === 'science_target_beacon'`:
   - Target Name, Priority Class, and Planetocentric Coordinates
   - Target Geological Theme & Mineralogical Target
   - Configured Instruments Assigned & Dwell Durations
   - Expected Science Return Points & Cumulative Target Weight
   - Estimated Raw Data Yield (MB) and Power Draw (W)
2. `type === 'data_product_node'`:
   - Product ID (UUIDv4) and Observation Identifier
   - Origin Instrument & Data Modality (e.g., Multispectral Cube, Raman Spectrum)
   - Product Payload Size ($S_i$ in MB) & Cryptographic Checksum (SHA-256)
   - Retention Status (`PENDING_IN_FLASH`, `TRANSMITTING`, `CONFIRMED_AT_BASE`)
   - Cumulative Transfer Latency from Observation Generation to Base Receipt

---

## 4. Test Engineering Matrix (`tests/test_milestone_13g_science_mission.py`)

A comprehensive 36-test engineering matrix is established to rigorously validate the science mission planner, data ledger, storage constraint engine, and simulated transfer accounting.

### 4.1 Structure and Module Hierarchy
The test suite is partitioned into 7 dedicated test classes:

```
tests/test_milestone_13g_science_mission.py
├── TestScienceTargetRegistryAndPrioritization (5 tests)
├── TestInstrumentTaxonomyAndCompatibility (5 tests)
├── TestChronologicalObservationScheduling (5 tests)
├── TestMissionDataLedgerAndByteConservation (6 tests)
├── TestSimulatedDataTransferLogistics (6 tests)
├── TestMultiObjectiveParetoCoDesign (5 tests)
└── TestScientificIntegrityAndRegressionGuard (4 tests)
Total: 36 Automated Quality Gate Tests
```

### 4.2 Comprehensive Test Specifications

#### Class 1: `TestScienceTargetRegistryAndPrioritization`
1. `test_target_registry_ingestion_and_schema`:
   - Validates ingestion of target fixtures across authentic Jezero coordinates. Asserts coordinates resolve to valid DTM cells within $[0, 250]$ row/col boundaries.
2. `test_priority_type_classification`:
   - Enforces valid classification of all targets into `USER_ASSIGNED_PRIORITY`, `SOURCE_DERIVED_PRIORITY`, or `UNASSESSED_PRIORITY`.
3. `test_utility_score_normalization`:
   - Verifies that target priority tiers map deterministically to normalized utility scores $U_i \in [0.0, 1.0]$.
4. `test_objective_weight_normalization_and_sum`:
   - Asserts $\sum w_i = 1.0 \pm 10^{-6}$ across distance, comms, energy, and science weights.
5. `test_multi_target_preference_ordering`:
   - Verifies that a target with priority `CRITICAL` ($U = 100$) strictly dominates a target with priority `LOW` ($U = 25$) when energy and distance are identical.

#### Class 2: `TestInstrumentTaxonomyAndCompatibility`
6. `test_instrument_taxonomic_specifications`:
   - Validates baseline specifications for all 6 instruments (Mastcam-Z, SuperCam, PIXL, SHERLOC, RIMFAX, MEDA). Asserts positive power draw ($P > 0$) and positive data yield ($D > 0$).
7. `test_compatible_observation_pairing`:
   - Asserts valid pairing of mineralogy targets with SuperCam/PIXL and organic targets with SHERLOC.
8. `test_incompatible_pairing_rejection`:
   - Asserts explicit rejection (raising `IncompatibleObservationError`) when attempting subsurface radar sounding on an atmospheric observation target.
9. `test_operating_power_and_warmup_energy`:
   - Verifies electrical energy integration: $E_{\text{obs}} = (P_{\text{base}} + P_{\text{inst}}) \cdot t_{\text{obs}} + E_{\text{warmup}}$.
10. `test_instrument_concurrency_and_exclusion`:
    - Asserts that high-power contact instruments (PIXL and SHERLOC) cannot operate simultaneously on the robotic arm if peak power exceeds rover power bus limit ($P_{\text{bus}} = 300\text{ W}$).

#### Class 3: `TestChronologicalObservationScheduling`
11. `test_chronological_event_ordering`:
    - Asserts strict monotonic ordering of mission events: $t_{\text{arrive}} \le t_{\text{prep}} \le t_{\text{obs\_start}} < t_{\text{obs\_end}} \le t_{\text{depart}}$.
12. `test_coupled_energy_drawdown_during_observation`:
    - Couples observation dwell with Milestone 13F resource ledger. Asserts battery SOC decreases strictly in accordance with instrument load over duration $t_{\text{obs}}$.
13. `test_total_mission_duration_conservation`:
    - Asserts $T_{\text{mission}} = T_{\text{traverse}} + \sum t_{\text{science\_dwell}} + \sum t_{\text{relay\_deploy}}$.
14. `test_adaptive_target_pruning_on_time_budget`:
    - Given a restrictive planning horizon ($T_{\text{max}} = 14,400\text{ s}$), asserts the planner selectively drops lower-priority targets while retaining highest-utility targets.
15. `test_zero_dwell_flyby_observation_mode`:
    - Validates continuous survey mode (e.g. RIMFAX radar sounding along traverse) with zero stationary dwell time.

#### Class 4: `TestMissionDataLedgerAndByteConservation`
16. `test_data_product_identity_and_cryptographic_checksum`:
    - Asserts every data product contains a valid UUIDv4, timestamp, instrument ID, integer byte size, and 64-character SHA-256 hex digest.
17. `test_strict_byte_conservation_law`:
    - Enforces exact First-Law Data Conservation across all time steps:
      $$S_{\text{used}, t} = S_{\text{used}, t-1} + S_{\text{generated}, t} - S_{\text{released}, t}$$
      Asserts zero floating-point loss ($|\Delta S - (S_{\text{gen}} - S_{\text{rel}})| = 0$ bytes).
18. `test_storage_capacity_limit_enforcement`:
    - Configures a small flash buffer ($1,000\text{ MB}$). Generates $1,200\text{ MB}$ of observation data without transfer. Asserts solver classifies mission as `STORAGE_OVERFLOW_REJECTED`.
19. `test_storage_pressure_state_transitions`:
    - Verifies monotonic state transitions: `STORAGE_AVAILABLE` ($<70\%$) $\rightarrow$ `STORAGE_PRESSURE` ($70-85\%$) $\rightarrow$ `STORAGE_NEAR_CAPACITY` ($85-100\%$) $\rightarrow$ `STORAGE_CAPACITY_REACHED` ($100\%$).
20. `test_release_after_verified_transfer_policy`:
    - Asserts flash storage is NEVER freed when a transfer is in-flight; buffer is released ONLY upon receiving simulated transfer confirmation.
21. `test_data_product_immutability_and_retention`:
    - Asserts completed data products marked `PROTECTED_CORE_RECORD` cannot be evicted even under storage pressure.

#### Class 5: `TestSimulatedDataTransferLogistics`
22. `test_los_dependent_transfer_initiation`:
    - Asserts simulated data transfer rate is strictly $0\text{ bps}$ during communications blackout intervals, and equals $R_{\text{config}}$ only when geometric LOS to RelayNet exists.
23. `test_data_transfer_volume_integration`:
    - Verifies transferred volume: $D_{\text{transferred}} = R_{\text{config}} \cdot (1 - \eta_{\text{proto}}) \cdot \Delta t_{\text{contact}}$.
24. `test_transfer_queue_fifo_and_priority_ordering`:
    - Asserts high-priority observation data products are transmitted before lower-priority ambient telemetry in the transfer queue.
25. `test_partial_transfer_across_split_windows`:
    - Models a large $100\text{ MB}$ hyperspectral cube split across two $30\text{ MB}$ contact windows and one $40\text{ MB}$ contact window. Verifies byte conservation across segments.
26. `test_multi_hop_relay_bandwidth_bottleneck`:
    - Validates end-to-end data throughput across Rover $\rightarrow$ Relay Tower $\rightarrow$ Base Station. Asserts effective rate is limited by the minimum capacity link in the path:
      $$R_{\text{end-to-end}} = \min(R_{\text{access}}, R_{\text{backhaul}})$$
27. `test_end_to_end_backlog_accounting`:
    - Enforces: $D_{\text{backlog}} = D_{\text{collected}} - D_{\text{transferred}} - D_{\text{evicted}}$.

#### Class 6: `TestMultiObjectiveParetoCoDesign`
28. `test_5d_pareto_dominance_evaluation`:
    - Evaluates candidate routes across Distance, Comms Gap, Rover Energy, Science Points, and Peak Storage. Verifies non-dominated classification.
29. `test_science_vs_energy_tradeoff_ranking`:
    - Verifies that adding a high-science detour ($+150\text{ pts}$, $+450\text{ Wh}$) creates a legitimate Pareto alternative rather than being dominated by the direct traverse.
30. `test_hard_constraint_filtering_precedence`:
    - Asserts candidates violating battery reserve ($SOC < 20\%$) or storage capacity ($S > S_{\text{max}}$) are strictly excluded from the promoted candidate set.
31. `test_marginal_rate_of_substitution_calculation`:
    - Verifies calculation of $\text{MRS}_{E, S}$ and asserts values are strictly non-negative along the efficient frontier.
32. `test_authentic_jezero_full_science_mission_solve`:
    - Executes full co-design solve on authentic USGS CTX 20m Jezero terrain from Octavia Butler Base to Delta Remnant visiting Three Forks and Séítah. Asserts valid solution with positive science score and intact battery reserve.

#### Class 7: `TestScientificIntegrityAndRegressionGuard`
33. `test_synthetic_data_provenance_labels`:
    - Asserts all generated data products and transfer logs bear explicit `SYNTHETIC_DEMONSTRATION_DATA` and `SIMULATED_DATA_TRANSFER` tags.
34. `test_non_regenerative_descent_modeling_classification`:
    - Asserts the resource model classifies non-regenerative descent as a conservative configurable assumption (`allow_regenerative_braking: False` by default), with no claims of proprietary Mars 2020 flight facts.
35. `test_operational_data_immutability`:
    - Verifies that running science mission optimization does not mutate underlying elevation grids, relay tower registries, or waypoint databases.
36. `test_no_astronaut_safety_claims_in_science_dossier`:
    - Scans generated JSON and Markdown dossiers for prohibited terms ("operationally safe for astronauts", "certified safe route"). Asserts zero occurrences.

---

## 5. Browser Acceptance & CDP Automation Architecture (`scripts/verify_science_mission_browser.py`)

To ensure flawless conference demonstration readiness, an automated browser verification script is designed using the Chrome DevTools Protocol (CDP).

### 5.1 Quality Gates & Acceptance Thresholds
- **Zero Console Errors:** Captures and fails on any browser console `error` or uncaught JavaScript exception (excluding harmless favicon/404).
- **Zero Horizontal Body Overflow:** Strictly validates `document.documentElement.scrollWidth <= window.innerWidth` across all viewport sizes.
- **Showcase Image Integrity:** Every screenshot must be $\ge 50.0\text{ KB}$ and contain rich, rendered visual content.
- **Dual-Storage Artifact Delivery:** Screenshots are written to `outputs/conference_showcase/science_logistics/` and mirrored to the subagent artifact directory.

### 5.2 8-Screenshot Conference Showcase Capture Matrix

| # | Filename | Viewport | Active View / Configuration | Key Assertions |
|---|---|---|---|---|
| **01** | `01_science_target_selection_studio.png` | $1920\times 1080$ | Joint Studio Step 1: Science Target Prioritization | Target checklist rendered, priority badges visible, $w_{\text{sci}}$ weight slider present |
| **02** | `02_science_payload_instrument_config.png` | $1920\times 1080$ | Joint Studio Step 5: Science Payload Profiles | 6 instrument cards rendered, power draw and dwell time inputs visible |
| **03** | `03_onboard_storage_and_transfer_logistics.png` | $1920\times 1080$ | Joint Studio Step 6: Onboard Storage & Transfers | Flash capacity slider ($16\text{ GB}$), reserve buffer ($20\%$), transfer rate ($2\text{ Mbps}$) |
| **04** | `04_science_pareto_frontier_explorer.png` | $1920\times 1080$ | Joint Studio Step 8: Pareto Studio (Science vs Energy) | Canvas scatter plot rendered, efficiency curve visible, tooltip active |
| **05** | `05_comparative_scorecard_science_logistics.png` | $1920\times 1080$ | Joint Studio Step 8: Expanded Scorecard Table | All 13 columns present, Science Points, Data Gen/Transferred, Feasibility badges |
| **06** | `06_3d_theater_data_logistics_hud.png` | $1920\times 1080$ | 3D Mission Theater Cockpit View | Real-time Flash Storage gauge bar, transfer queue backlog, 3D science beacons |
| **07** | `07_dynamic_timeline_scrubber_data_transfer.png` | $1920\times 1080$ | 3D Theater Timeline Scrubber Active | Playback active during science dwell, storage bar filling, transfer rate pulsing |
| **08** | `08_responsive_layout_1366x768.png` | $1366\times 768$ | Laptop Viewport Responsive Verification | Zero horizontal overflow, 9-step stepper cleanly laid out, telemetry cards readable |

### 5.3 CDP Script Implementation Architecture
The script follows the proven asynchronous WebSocket pattern from `verify_resource_intelligence_browser.py`:
- Initializes temporary Chrome user profile with headless mode (`--headless=new`).
- Enables `Page`, `Runtime`, `DOM`, and `Emulation` domains.
- Attaches event listeners for `Runtime.consoleAPICalled` and `Runtime.exceptionThrown`.
- Dynamically drives UI via `Runtime.evaluate` calling `window.Atlas.switchJointWizardStep()`, `window.Atlas.setParetoMode()`, and `window.Atlas.updatePlaybackTime()`.
- Validates overflow via:
  ```javascript
  (() => {
    const sw = document.documentElement.scrollWidth;
    const iw = window.innerWidth;
    return { scrollWidth: sw, innerWidth: iw, overflow: sw > iw };
  })()
  ```

---

## 6. Scientific Integrity Review: 13F Non-Regenerative Descent Correction

### 6.1 Scientific Integrity Analysis
In Milestone 13F, the mechanical energy equation governing slope descent:
$$W_{\text{mech}} = W_r + \max(0, W_g)$$
was accompanied by explanatory text in `docs/milestone-13f-physics-audit.md` and `docs/milestone-13f-report.md` stating as historical flight facts that:
> *"Planetary exploration rovers (Sojourner, MER Spirit/Opportunity, MSL Curiosity, Mars 2020 Perseverance) employ multi-stage epicyclic or harmonic drive gearheads... The drivetrain is intentionally designed to be non-backdrivable under normal gravitational loads... There is no bidirectional active buck-boost DC-DC converter capable of conditioning fluctuating, noisy regenerative motor current into the high-precision lithium-ion battery management system."*

While these engineering descriptions reflect common design trade-offs in planetary robotics, presenting them as **established, flight-telemetry-certified Mars 2020 hardware specifications** without primary NASA/JPL telecommand citations violates the MarsWalk project rule:
> *"Never invent measurements or present synthetic data as real Martian observations. Distinguish measured data, derived quantities and model estimates."*

Electromechanical drives with brushless DC motors can physically produce back-EMF during downhill motion, and while rovers typically dissipate this power through dynamic braking shunts or motor coil resistance to maintain strict AutoNav velocity limits, the prohibition of regenerative recharge in MarsWalk is fundamentally a **conservative engineering modeling choice** rather than a certified NASA flight constraint.

### 6.2 Required Reclassification
MarsWalk 2.0 / Project Atlas must explicitly reclassify non-regenerative descent as a:
> **"Conservative Configurable Modeling Assumption (`allow_regenerative_braking: False` by default)"**

#### Rationale for the Modeling Assumption:
1. **Conservative Mission Feasibility:** In autonomous traverse planning, relying on unverified slope-descent energy recovery across unpredictable regolith to maintain battery margins is operationally hazardous. If an algorithm plans a route assuming battery recharge, but terrain wheel slip, motor thermals, or battery management protection prevent energy capture, the rover faces catastrophic battery exhaustion.
2. **Architectural Configurability:** The model provides an explicit toggle (`allow_regenerative_braking: True/False`), allowing researchers to evaluate advanced future rover architectures (e.g., pressurized crew rovers) that may incorporate bidirectional regenerative drivetrains.
3. **Scientific Provenance:** The code and documentation must clearly state that zero descent regeneration is an analytical planning heuristic designed to prevent optimistic bias, rather than a claim about proprietary JPL internal circuit schematics.

### 6.3 Actionable Documentation Updates

#### 1. Update to `docs/milestone-13f-report.md` (Section 2.3):
*Current Text:*
> "Because planetary rovers employ non-backdrivable harmonic drive planetary gearboxes, cold-temperature battery protection constraints, and actively control descent speed via motor hold-back torque: $W_{\text{mech}} = W_r + \max(0, W_g)$. Gravitational descent work ($W_g < 0$) is dissipated as mechanical/motor heat and does not recharge the battery..."

*Required Replacement Text:*
> "MarsWalk adopts a **conservative configurable modeling assumption** (`allow_regenerative_braking: False` by default) for slope descents:
> $$W_{\text{mech}} = W_r + \max(0, W_g)$$
> In autonomous planetary traverse planning, relying on downhill gravitational potential energy to recharge cold-temperature flight batteries or offset wheel rolling resistance is a hazardous operational assumption. Unless verified by certified in-situ telemetry and active bidirectional power management models, downhill gravitational work ($W_g < 0$) is conservatively treated as dissipated heat. This assumption is configurable in both the API and UI for comparative studies."

#### 2. Update to `docs/milestone-13f-physics-audit.md` (Section 2.1):
*Current Text:*
> "A critical finding of this physics audit is that assuming negative gravitational work offsets rolling resistance or recharges the battery is physically false and operationally dangerous for Martian surface exploration... There is no bidirectional active buck-boost DC-DC converter..."

*Required Replacement Text:*
> "MarsWalk explicitly models downhill descent under a **conservative engineering assumption** rather than asserting proprietary flight hardware specifications.
> While commercial electric vehicles utilize bidirectional inverters for regenerative energy capture, planetary rover traverse planning requires strict conservatism:
> 1. Soil-wheel slip, steep scree slopes, and low crawl speeds ($0.04 - 0.12\text{ m/s}$) produce high rolling resistance that often dominates downhill motion.
> 2. Rover velocity control systems actively command hold-back torque, frequently dissipating excess kinetic energy into brake resistors or motor stator windings.
> 3. Assuming energy recapture without primary flight verification risks producing dangerously optimistic battery reserve estimates.
> Therefore, MarsWalk disables downhill regeneration by default, ensuring planners do not depend on unmodeled recharge to establish mission feasibility."

#### 3. Update to `src/marswalk/core/mission_resource_model.py`:
Ensure docstrings for `allow_regenerative_braking` explicitly state:
```python
"""
allow_regenerative_braking: bool = False
    Conservative configurable modeling assumption. When False (default), downhill 
    gravitational work (W_g < 0) does not reduce rolling resistance or recharge 
    the battery (W_mech = W_r + max(0, W_g)). Set to True only for experimental 
    modeling of advanced bidirectional energy recovery drivetrains.
"""
```

---

## 7. Execution Roadmap & Subagent Synchronization

To execute Milestone 13G cleanly, the integration roadmap is coordinated across all specialized subagents:

```
[Agent A: Science Planner] ───> [Agent B: Data & Storage] ───> [Agent C: Optimization]
                                                                        │
                                                                        ▼
                                                             [Agent D: Validation & UI]
                                                             ├── 9-Step Studio Stepper
                                                             ├── Data Logistics HUD
                                                             ├── 36-Test Pytest Suite
                                                             └── 8-Shot CDP Automation
```

1. **Phase 1: Core Engine Implementation (Agents A, B, C):**
   - Agent A delivers `science_mission_planner.py` (target priority scoring, instrument compatibility, observation schedules).
   - Agent B delivers `mission_data_ledger.py` (exact byte accounting, storage capacity management, simulated transfer queues).
   - Agent C delivers `joint_mission_planner.py` extensions (5D Pareto evaluation, hard constraint filtering, MRS attribution).
2. **Phase 2: UI & Theater Integration (Agent D):**
   - Update `web/index.html` with Steps 5 and 6 and extended Step 8 scorecard.
   - Update `web/styles.css` with responsive 9-step grid, storage gauge styles, and data badges.
   - Update `web/app.js` with data logistics telemetry drawer, timeline scrubber sync, 3D science beacons, and spatial raycast handlers.
3. **Phase 3: Verification & Quality Gates (Agent D):**
   - Execute `tests/test_milestone_13g_science_mission.py` (36 tests, 100% pass).
   - Run complete repository regression suite (Milestones 13A through 13F).
   - Execute preflight readiness audit (`python scripts/preflight_check.py --port 3000`).
   - Run headless browser acceptance (`python scripts/verify_science_mission_browser.py`) capturing all 8 showcase images with zero console errors and zero overflow.
4. **Phase 4: Scientific Integrity Documentation (Agent D):**
   - Apply the formulated 13F non-regenerative descent correction across all milestone documentation.
   - Generate `docs/milestone-13g-report.md` and conversation artifacts for user sign-off.

---

## 8. Conclusion

This audit establishes a complete, rigorous, and actionable plan for Milestone 13G. By extending the Joint Mission Design Studio into a 9-step science and data logistics workflow, embedding real-time storage and transfer digital twin telemetry in the 3D theater, enforcing a 36-test analytical test matrix, and automating browser acceptance, MarsWalk 2.0 / Project Atlas achieves unprecedented depth in planetary mission planning while rigorously preserving scientific truth and data provenance.
