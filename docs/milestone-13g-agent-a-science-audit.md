# Milestone 13G — Science Scheduling Architecture Audit (Agent A)
## First-Principles Science Target Prioritization, Instrument-Observation Compatibility, and Chronological Activity Scheduling for MarsWalk 2.0 / Project Atlas

**Milestone:** 13G — Science Target Prioritization × Observation Scheduling × Onboard Data Management × Resource-Constrained Mission Optimization  
**Agent Role:** Agent A — Science Scheduling Architect  
**Target Output File:** `docs/milestone-13g-agent-a-science-audit.md`  
**System:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Execution Environment:** Windows 11 (64-bit), Python 3.12.4 (`.venv`), Vanilla JS / Three.js Frontend, Atlas API Daemon on port 3000  
**Date:** 2026-11-01  
**Status:** COMPLETE & SCIENTIFICALLY AUDITED  

---

## 1. Executive Summary & Purpose

In planetary surface exploration missions such as NASA's Mars 2020 *Perseverance* rover and Mars Science Laboratory (MSL) *Curiosity*, **science return is the fundamental mission objective**. However, scientific activities cannot be conducted in an unconstrained vacuum. In reality, science return is tightly coupled with:
1. **Vehicle Mobility & Terramechanics:** Navigating rugged regolith and steep slopes consumes valuable electrical energy and operational daylight time.
2. **Multi-Instrument Subsystem Physical Demands:** Scientific instruments (e.g., spectrometers, microscopes, ground-penetrating radars, coring drills) exhibit distinct thermal preparation times, duty cycles, peak electrical power draws, and multi-megabyte data generation volumes.
3. **Finite Onboard Resources:** Rovers operate under strict battery state-of-charge (SOC) reserve floors, single-sol life-support/daylight windows, and onboard solid-state memory storage limits.
4. **Episodic Communications Logistics:** Observational data products must be queued, managed under storage pressure, and transmitted across intermittent Direct-To-Earth (DTE) or UHF orbital relay links.

### The Milestone 13G Architectural Evolution
Prior to Milestone 13G, MarsWalk modeled science targets as static spatial waypoints with a scalar priority score (0–100) and an arbitrary, monolithic dwell time (e.g., 900 s / 15 min at 120 W). While suitable for initial mobility heuristics, this abstraction does not model true planetary science operations.

**Agent A establishes the Science Scheduling Subsystem (`src/marswalk/core/science_mission_planner.py`)**, which:
- **Audits Existing Models:** Dissects `ScienceWaypoint`, `CampaignTarget`, `CandidatePlan`, `ScienceObservation`, `waypoints_jezero.json`, and `mars_places.json`.
- **Formulates Scientific Priority Classifications:** Establishes a rigorous tri-state priority model distinguishing `USER_ASSIGNED_PRIORITY`, `SOURCE_DERIVED_PRIORITY`, and `UNASSESSED_PRIORITY`, enforcing NASA Space Apps scientific integrity rules by explicitly separating configured user utility from objective ground truth.
- **Defines an Instrument-to-Observation Compatibility Layer:** Establishes a complete taxonomy of 7 exploration instruments (Mastcam-Z, SuperCam, PIXL, SHERLOC/WATSON, RIMFAX, MEDA, Coring Tool) with explicit operating modes, durations, electrical power draws, data generation rates, and mutual exclusivity constraints.
- **Specifies a Chronological Multi-Phase Observation Scheduling Engine:** Breaks each scientific stop into five deterministic operational phases (*Rover Arrival & Settle*, *Instrument Preparation & Warmup*, *Observation Execution*, *Data Post-Processing & Cache*, and *Instrument Stow & Secure*), seamlessly integrating with the Milestone 13F Terramechanical & Electrical Resource Model.
- **Establishes 5 Adaptive Science Scheduling Triggers:** Provides deterministic replanning logic for *Unreachable Targets*, *Resource Violations*, *Instrument Unavailability*, *Storage Pressure*, and *Reduced Transfer Availability*.

```
+---------------------------------------------------------------------------------------------------------+
|                         MILESTONE 13G AGENT A: SCIENCE SCHEDULING ARCHITECTURE                          |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|   +------------------------------------+          +-------------------------------------------------+   |
|   |    CANDIDATE SCIENCE TARGETS       |          |        SCIENTIFIC PRIORITY CLASSIFICATION       |   |
|   | - 12 Curated Jezero Delta Targets  | =======> | - USER_ASSIGNED_PRIORITY (Operator utility)     |   |
|   | - 2,061 Global USGS/IAU Features   |          | - SOURCE_DERIVED_PRIORITY (CRISM/PDS citation)  |   |
|   | - Target Dependency DAGs (Prereqs) |          | - UNASSESSED_PRIORITY (Pending evaluation)      |   |
|   +------------------------------------+          +-------------------------------------------------+   |
|                     |                                                      |                            |
|                     v                                                      v                            |
|   +-------------------------------------------------------------------------------------------------+   |
|   |                   INSTRUMENT-TO-OBSERVATION COMPATIBILITY LAYER                                 |   |
|   |  Instruments: Mastcam-Z, SuperCam, PIXL, SHERLOC/WATSON, RIMFAX, MEDA, Coring Tool              |   |
|   |  Modes: Panoramic, Multispectral, LIBS, Raman, Micro-XRF, Radar Sounding, Coring                |   |
|   |  Validation: Arm Turret Exclusivity, Stationary Constraints, Observation Domain Mapping        |   |
|   +-------------------------------------------------------------------------------------------------+   |
|                                                     |                                                   |
|                                                     v                                                   |
|   +-------------------------------------------------------------------------------------------------+   |
|   |                   CHRONOLOGICAL OBSERVATION SCHEDULING ENGINE                                   |   |
|   |  Phase 1: Rover Arrival & Settle (Brakes, IMU stabilization)                                    |   |
|   |  Phase 2: Instrument Preparation & Warmup (Heaters, arm un-stow, radiometric cal)               |   |
|   |  Phase 3: Observation Execution (Active sensor integration, mode power P_inst)                  |   |
|   |  Phase 4: Data Post-Processing & Cache (Wavelet compression, SHA-256 checksum)                 |   |
|   |  Phase 5: Instrument Stow & Secure (Turret latch, mast drive azimuth)                           |   |
|   +-------------------------------------------------------------------------------------------------+   |
|                            /                                                \                           |
|                           v                                                  v                          |
|   +-----------------------------------------------+  +----------------------------------------------+   |
|   |       13F RESOURCE MODEL INTEGRATION          |  |       DATA LOGISTICS HANDOFF (AGENT B)       |   |
|   | - Dynamic Electrical Draw: P_base + P_inst    |  | - Data Product Generation D_gen(t)           |   |
|   | - First-Law Energy Conservation Check         |  | - Storage Occupancy Accounting S_used(t)     |   |
|   | - Battery SOC % and Reserve Floor Tracking    |  | - Transfer Queue Notification                |   |
|   +-----------------------------------------------+  +----------------------------------------------+   |
|                           \                                                  /                          |
|                            v                                                v                           |
|   +-------------------------------------------------------------------------------------------------+   |
|   |                   ADAPTIVE SCIENCE SCHEDULING TRIGGERS                                          |   |
|   |  [T1] Unreachable Target        ===> DAG Pruning & Pareto Rerouting                             |   |
|   |  [T2] Resource Violation        ===> 4-Stage Progressive Observation Load Shedding             |   |
|   |  [T3] Instrument Unavailability ===> Compatibility Layer Alternative Mode Substitution          |   |
|   |  [T4] Storage Pressure          ===> Adaptive Wavelet Compression & Culling                     |   |
|   |  [T5] Reduced Comm Availability ===> Autonomous Survey Caching & Ground Deferral               |   |
|   +-------------------------------------------------------------------------------------------------+   |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Audit of Existing Science Targets, Waypoints, and Observation Models

An exhaustive audit of the existing MarsWalk codebase reveals several foundational data structures across planning, campaign management, and API contracts.

### 2.1 Existing Core Codebase Data Structures

#### 1. `ScienceWaypoint` (`src/marswalk/core/planner.py`, lines 26–39)
```python
@dataclass
class ScienceWaypoint:
    id: str
    name: str
    rc: Tuple[int, int]
    priority_score: float = 0.0
    geological_context: str = ""
    crism_signature: str = ""
    pds_citation: str = ""
```
- **Strengths:** Lightweight, carries authentic geological context and CRISM/PDS provenance metadata.
- **Shortcomings:** Purely spatial; priority is an unclassified float scalar (`0.0` default); lacks instrument requirements, observation duration, power demands, or data volume estimates.

#### 2. `CampaignTarget` (`src/marswalk/core/mission_campaign.py`, lines 77–161)
```python
@dataclass
class CampaignTarget:
    id: str
    name: str
    row: int
    col: int
    lat_deg: Optional[float] = None
    lon_deg: Optional[float] = None
    elevation_m: Optional[float] = None
    priority_score: float = 50.0
    priority_label: str = "default"  # "user_defined" or "default"
    dwell_time_s: float = 900.0
    prerequisites: List[str] = field(default_factory=list)
    geological_context: Optional[str] = ""
    crism_signature: Optional[str] = ""
    provenance: Optional[str] = ""
    status: str = TargetStatus.UNSCHEDULED.value
    assigned_sortie_id: Optional[str] = None
    assigned_sol_index: Optional[int] = None
    unscheduled_reason: Optional[str] = None
    science_objective: Optional[str] = None
    objective_classification: Optional[str] = "NOT_ASSESSED"
    linked_observation_ids: List[str] = field(default_factory=list)
    repeat_observation_requested: bool = False
    assigned_unit_id: Optional[str] = None
```
- **Strengths:** Supports directed acyclic graph (DAG) topological prerequisite tracking (`validate_target_dependencies`), campaign lifecycle tracking (`TargetStatus`), and linkage to completed observation IDs.
- **Shortcomings:** Priority label is a binary string (`user_defined` vs `default`) rather than an explicit provenance classification; dwell time defaults to a static `900.0 s`; instruments are not explicitly modeled or scheduled.

#### 3. `CandidatePlan` & `FrontierResult` (`src/marswalk/core/science_budget.py`, lines 27–108)
```python
@dataclass
class CandidatePlan:
    candidate_id: str
    subset_key: str
    visited_waypoint_ids: List[str]
    visited_waypoint_names: List[str]
    path: List[Tuple[int, int]]
    distance_m: float
    cost: float
    science_score: float
    is_reachable: bool
    is_budget_feasible: bool
    num_targets: int
    ...
```
- **Strengths:** Implements exact powerset evaluation ($2^K$ combinations up to 6 waypoints) and extracts 2D/3D non-dominated Pareto frontiers comparing distance, terrain cost, and science score.
- **Shortcomings:** Treats science score as a linear sum ($\sum w_i$); ignores the energy and time costs of performing the actual observations; assumes dwell time does not impact battery SOC or feasibility.

#### 4. `ScienceObservation` (`src/marswalk/core/campaign_progress.py`, lines 126–194)
```python
@dataclass
class ScienceObservation:
    observation_id: str
    campaign_id: str
    target_id: str
    timestamp_utc: str
    observation_type: str
    provenance: str
    is_simulated: bool
    schema_version: str = "1.0.0"
    sortie_id: Optional[str] = None
    mission_id: Optional[str] = None
    target_name: Optional[str] = ""
    sol_index: Optional[int] = None
    instrument_name: Optional[str] = ""
    quantitative_measurements: List[QuantitativeMeasurement] = field(default_factory=list)
    qualitative_notes: Optional[str] = ""
    evidence_references: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 1.0
```
- **Strengths:** Strictly validated against `schemas/api/v1/science-observation.schema.json`; enforces strict SI unit validation (`RECOGNIZED_PHYSICAL_UNITS`); distinguishes authentic PDS data from simulated records.
- **Shortcomings:** Exists purely as an historical *record* produced post-facto during campaign execution, rather than an schedulable activity that demands power, time, and data storage during the planning phase.

### 2.2 Planetary Datasets & Catalogs

#### 1. Jezero Western Delta Target Catalog (`data/waypoints_jezero.json`)
Contains 12 scientifically curated targets across the Jezero Western Delta Front:
- `octavia_butler_landing` (Touchdown site, basaltic Máaz unit)
- `three_forks` (Sample cache depot, olivine-carbonate contact)
- `hawksbill_gap` (Delta ascent scarp, clay/smectite biosignature target, priority 95)
- `kodiak_butte` (Delta stratigraphy outlier mesa, priority 60)
- `delta_rim_overlook` (Strategic rim overlook, Tenby scarp, priority 70)
- `neretva_margin` (Inflow breach boulder conglomerate, priority 85)
- `seitah_dunes` (Olivine-rich sand dune field, mobility hazard, priority 55)
- `artuby_ridge` (Séítah/Máaz boundary ridge scarp, priority 65)
- `skinner_ridge` (Abraded outcrop 'Swift Run', sulfate minerals, priority 90)
- `enchanted_lake` (Delta scarp base, laminated mudstones, priority 80)
- `belva_crater_overlook` (1-km impact crater exposing delta topset beds, priority 75)
- `dourbes_floor` (Crater floor cored sample 'Montdenier', priority 70)

All 12 entries possess authentic CRISM spectral signatures and primary literature PDS citations (e.g., Farley et al. 2022, Scheller et al. 2022, Mangold et al. 2021).

#### 2. Global Mars Gazetteer (`web/data/mars_places.json`)
Contains 2,061 planetary nomenclature records from the USGS Astrogeology Science Center and IAU WGPSN:
- 10 Robotic Mission Landing Sites (Perseverance, Curiosity, InSight, Opportunity, Spirit, Zhurong, Phoenix, Pathfinder, Viking 1, Viking 2).
- 1,239 Impact Craters, 273 Canyons, 121 Volcanoes, 97 Ridges, 46 Plains, 30 Chaos terrains.
- Importance tiers 1 (190), 2 (602), 3 (1,269).

### 2.3 Synthesis of Codebase Gaps

| Dimension | Current State in Codebase | Milestone 13G Required Architecture |
|---|---|---|
| **Priority Model** | Single scalar `priority_score` (0–100) with binary `priority_label` (`user_defined` vs `default`). | Tri-State Classification: `USER_ASSIGNED_PRIORITY`, `SOURCE_DERIVED_PRIORITY`, `UNASSESSED_PRIORITY` with explicit provenance tracking. |
| **Observation Timing** | Monolithic global constant: `900.0 s` (15 min) in `planner.py` and `mission_resource_model.py`. | Multi-phase operational schedule: Settle, Warmup, Active Observation, Compression, and Stow. |
| **Instrument Taxonomy** | Free-form string `instrument_name` in observation records; no operational specs. | Formal 7-instrument taxonomy with validated modes, duration, active power ($W$), and data volume ($MB$). |
| **Power Integration** | Static dwell equation: $P_{\text{base}} + P_{\text{inst}} \cdot \text{duty} + P_{\text{comm}}$. | Dynamic integration with 13F: multi-phase electrical power integrated into `MissionResourceLedger`. |
| **Data Generation** | Non-existent; data production is not tracked or budgeted. | Exact byte-level data generation accounting feeding Agent B's `MissionDataLedger`. |
| **Adaptive Replanning** | DAG pruning for blocked targets in `campaign_intelligence.py`; no resource-aware triggers. | 5 Deterministic Triggers: Unreachable Target, Resource Violation, Instrument Fault, Storage Pressure, and Comm Loss. |

---

## 3. Scientific Priority Classifications & Integrity Guardrails

### 3.1 The NASA Space Apps Scientific Integrity Mandate
A foundational rule of the MarsWalk project (`.agents/skills/marswalk-scientific-integrity/SKILL.md`) states:
> *"Never invent measurements or present synthetic data as real Martian observations. Distinguish measured data, derived quantities and model estimates."*

In planning systems, when an automated optimizer or user interface assigns a "score" of 95 to a rock outcrop, there is a severe risk of misleading users into believing this represents an objective, certified physical measurement of Martian scientific value. In truth, scientific value is always:
- Configured by mission investigation teams based on campaign goals;
- Derived from specific remote sensing papers and mission reports; or
- Completely unassessed for raw gazetteer landmarks.

### 3.2 The Tri-State Priority Classification Model

Milestone 13G formally establishes the `ScientificPriorityClassification` enum:

```
                                +-----------------------------------+
                                | SCIENTIFIC PRIORITY CLASSIFICATION |
                                +-----------------------------------+
                                                  |
         +----------------------------------------+---------------------------------------+
         |                                        |                                       |
         v                                        v                                       v
+------------------------+              +------------------------+              +------------------------+
| USER_ASSIGNED_PRIORITY |              | SOURCE_DERIVED_PRIORITY|              |  UNASSESSED_PRIORITY   |
+------------------------+              +------------------------+              +------------------------+
| - Configured by user   |              | - Derived from PDS or  |              | - Gazetteer feature    |
|   or mission planner   |              |   peer-reviewed source |              |   without evaluation   |
| - Reflects tactical    |              | - Requires explicit    |              | - Neutral base score   |
|   campaign priorities  |              |   citation & method    |              | - Cannot outrank       |
| - Adjustable via UI    |              | - Immutable baseline   |              |   assessed targets     |
+------------------------+              +------------------------+              +------------------------+
```

#### 1. `USER_ASSIGNED_PRIORITY`
- **Definition:** Priority scores explicitly configured, overridden, or weighted by the human mission commander, science investigator, or user.
- **Semantics:** Represents subjective campaign utility. Reflects specific mission objectives (e.g., "focus on lacustrine mudstones during Sol 12").
- **Required Metadata:**
  - `assigned_by`: Identifier of the operator/investigator (e.g., `"user_ui"`, `"science_team_lead"`).
  - `assignment_timestamp_utc`: ISO 8601 timestamp.
  - `justification_notes`: Human-readable rationale for the assigned priority.
- **Score Range:** $0.0 \le S \le 100.0$.

#### 2. `SOURCE_DERIVED_PRIORITY`
- **Definition:** Priority scores derived directly from published peer-reviewed planetary science literature, official NASA PDS mission archives, or CRISM multispectral index rankings.
- **Semantics:** Represents an evidence-grounded scientific ranking published by mission science teams (e.g., the 12 Jezero delta targets).
- **Mandatory Provenance Attributes:**
  - `source_citation`: Bibliographic citation (e.g., `"Scheller, E.L. et al. (2022), Science 378, 1105-1110"`).
  - `source_dataset`: Primary dataset ID (e.g., `"NASA_PDS_CRISM_FRT000047A3"`, `"USGS_CTX_DTM_JEZERO_20M"`).
  - `derivation_method`: Algorithmic or heuristic derivation protocol (e.g., `"crism_spectral_absorption_depth"`, `"landing_site_selection_tier"`).
- **Integrity Rule:** Must NEVER be claimed as an objective ground-truth physical law. The UI and reports must explicitly display: *"Source-derived value based on cited primary literature."*

#### 3. `UNASSESSED_PRIORITY`
- **Definition:** Features or locations imported from global gazetteers (such as the 2,061 places in `mars_places.json`) that have geographic nomenclature and coordinates, but have not been evaluated for scientific return within this campaign.
- **Semantics:** Prevents algorithmic hallucination. A crater named "Belva" or "Jezero" does not automatically possess a high scientific score simply because it has an entry in a gazetteer.
- **Default Baseline:** Assigned a score of $0.0$ (or a tagged baseline of $20.0$ with `is_evaluated=False`).
- **Gating Rule:** The scheduling engine will never prioritize an `UNASSESSED_PRIORITY` target over an assessed target unless an explicit user override is supplied.

### 3.3 Target Science Utility Formulation

To compute the aggregate scientific return for candidate mission plans while preserving scientific integrity, the utility $U_{\text{science}}$ of a plan visiting subset $\mathcal{S}$ is defined as:

$$U_{\text{science}} = \sum_{i \in \mathcal{S}} \Big( w_{\text{obj}}(i) \cdot S_i \cdot \prod_{j \in \text{prereq}(i)} \kappa(j) \Big)$$

Where:
- $S_i \in [0, 100]$ is the base priority score of target $i$.
- $w_{\text{obj}}(i) \ge 0$ is the user-configured weight corresponding to the scientific objective of target $i$ (e.g., mineralogy vs atmospheric monitoring).
- $\kappa(j)$ is the evidence modifier from prerequisite target $j$, derived from `src/marswalk/core/campaign_intelligence.py`:
  - $\kappa(j) = 1.25$ if prerequisite observation `SUPPORTS_OBJECTIVE` (+25% boost).
  - $\kappa(j) = 0.65$ if prerequisite observation `DOES_NOT_SUPPORT_OBJECTIVE` (-35% penalty).
  - $\kappa(j) = 1.00$ if prerequisite observation is `INCONCLUSIVE` or `NOT_ASSESSED`.

> **Scientific Disclosure:** $U_{\text{science}}$ represents a *modeled preference utility score under configured mission weights*, not an empirical measurement of planetary truth.

---

## 4. Science Objectives & Instrument-to-Observation Compatibility Layer

### 4.1 Mission Science Objectives Taxonomy

Milestone 13G standardizes six core planetary science objectives:
1. `GEOLOGICAL_CHARACTERIZATION`: Stratigraphic mapping, bed dip/strike measurement, outcrop facies analysis, and bedrock texture imaging.
2. `MINERALOGICAL_INVESTIGATION`: Identification of phyllosilicates (smectite clays), carbonates, sulfates, and olivine-pyroxene basaltic minerals.
3. `ATMOSPHERIC_OBSERVATION`: Diurnal atmospheric pressure cycles, dust optical depth ($\tau$), boundary layer turbulence, and ambient wind velocity.
4. `SURFACE_MORPHOLOGY`: High-resolution stereoscopic terrain mapping, boulder size-frequency distribution, and wheel sinkage/hazard evaluation.
5. `ENVIRONMENTAL_MONITORING`: Thermal inertia, ambient air/ground temperature variations, and UV solar irradiance tracking.
6. `ASTROBIOLOGY_BIOSIGNATURE_SURVEY`: Micro-scale spatial co-location of organic molecules with carbonate/silica minerals in ancient lacustrine sediments.

### 4.2 Mars Exploration Instrument Taxonomy

Based on the Mars 2020 *Perseverance* science payload and authentic planetary instruments, we define seven exploration instruments with validated operational profiles:

```
+---------------------------------------------------------------------------------------------------------+
|                                    MARSWALK 2.0 INSTRUMENT TAXONOMY                                    |
+---------------------------------------------------------------------------------------------------------+
| [ REMOTE SENSING MAST ]                                                                                 |
| 1. Mastcam-Z : Multispectral Stereoscopic Panoramic Imager (Terrain, Color Mosaics, Tau Photometry)    |
| 2. SuperCam  : Laser-Induced Breakdown Spectroscopy (LIBS) & Remote Raman/VIS-IR Spectrometer          |
|                                                                                                         |
| [ CONTACT SCIENCE TURRET (ROBOTIC ARM) ]                                                                |
| 3. PIXL      : Planetary Instrument for X-ray Lithochemistry (Micro-XRF elemental mapping)              |
| 4. SHERLOC   : Scanning Habitable Environments with Raman & Luminescence for Organics & Chemicals       |
|    + WATSON  : Wide Angle Topographic Sensor for Operations and eNgineering (Hand-lens imager)          |
| 5. CORING_TOOL: Rotary Percussive Coring Drill & Abrasion Tool (Rock core caching)                     |
|                                                                                                         |
| [ SUBSURFACE SOUNDING & ENVIRONMENT ]                                                                   |
| 6. RIMFAX    : Radar Imager for Mars' Subsurface Experiment (Ground-Penetrating Radar)                  |
| 7. MEDA      : Mars Environmental Dynamics Analyzer (Meteorology & Dust Sensors)                        |
+---------------------------------------------------------------------------------------------------------+
```

### 4.3 Detailed Instrument Operational Profiles

All power, duration, and data rate parameters are derived from NASA/JPL Mars 2020 technical instrument papers:

| Instrument ID | Operating Mode | Duration ($\text{s}$) | Operating Power ($\text{W}$) | Raw Data Volume ($\text{MB}$) | Compression Ratio | Compressed Data ($\text{MB}$) | Compatible Observation Domain |
|---|---|---|---|---|---|---|---|
| **`MASTCAM_Z`** | `PANO_360_COLOR` | 1,200 | 17.4 | 450.0 | 4.0:1 | 112.5 | `TERRAIN_IMAGING`, `SURFACE_MORPHOLOGY` |
| | `MULTISPECTRAL_STEREO`| 600 | 19.8 | 180.0 | 3.0:1 | 60.0 | `SPECTRAL_SURVEY`, `MINERALOGY` |
| | `SUN_PHOTOMETRY_TAU` | 180 | 12.0 | 15.0 | 5.0:1 | 3.0 | `ATMOSPHERIC_MEASUREMENT`, `PHOTOMETRIC`|
| **`SUPERCAM`** | `LIBS_BURST_30` | 900 | 38.0 | 45.0 | 2.5:1 | 18.0 | `GEOLOGICAL_ASSAY`, `SPECTRAL_SURVEY` |
| | `RAMAN_SPECTRA` | 1,500 | 42.0 | 75.0 | 2.0:1 | 37.5 | `MINERALOGICAL_INVESTIGATION` |
| | `RMI_HIGH_RES_RASTER` | 400 | 25.0 | 60.0 | 3.5:1 | 17.1 | `TERRAIN_IMAGING`, `GEOLOGICAL_ASSAY` |
| **`PIXL`** | `CONTACT_SCAN_ALIGN` | 600 | 15.0 | 10.0 | 2.0:1 | 5.0 | `GEOLOGICAL_ASSAY` |
| | `XRF_ELEMENTAL_GRID` | 3,600 | 25.0 | 85.0 | 2.5:1 | 34.0 | `GEOLOGICAL_ASSAY`, `MINERALOGY` |
| | `XRF_HIGH_DEF_DWELL` | 14,400 | 22.0 | 250.0 | 2.5:1 | 100.0 | `GEOLOGICAL_ASSAY`, `ASTROBIOLOGY` |
| **`SHERLOC`** | `WATSON_MICRO_IMAGE` | 300 | 12.0 | 40.0 | 3.0:1 | 13.3 | `GEOLOGICAL_ASSAY`, `TERRAIN_IMAGING` |
| | `DUV_RAMAN_SCAN` | 2,400 | 48.0 | 110.0 | 2.0:1 | 55.0 | `ASTROBIOLOGY_BIOSIGNATURE_SURVEY` |
| **`RIMFAX`** | `DRIVE_SOUNDING` | Matches drive | 8.5 | 5.0 / km | 1.5:1 | 3.3 / km | `GEOLOGICAL_ASSAY`, `HAZARD_INSPECTION`|
| | `DEEP_SOUNDING_STATIONARY`| 600 | 11.0 | 25.0 | 1.5:1 | 16.7 | `GEOLOGICAL_ASSAY`, `STRATIGRAPHY` |
| **`MEDA`** | `METEOROLOGY_CONTINUOUS`| Continuous | 17.0 | 12.0 / sol| 2.0:1 | 6.0 / sol | `ATMOSPHERIC_MEASUREMENT`, `ENVIRONMENT`|
| | `HIGH_RATE_TURBULENCE`| 1,800 | 21.0 | 35.0 | 2.0:1 | 17.5 | `ATMOSPHERIC_MEASUREMENT`, `BOUNDARY` |
| **`CORING_TOOL`**| `ABRASION_PATCH` | 1,800 | 115.0 | 8.0 | 2.0:1 | 4.0 | `SAMPLE_CORE_EXTRACTION`, `GEOLOGY` |
| | `SAMPLE_CORE_EXTRACTION`| 5,400 | 145.0 | 20.0 | 2.0:1 | 10.0 | `SAMPLE_CORE_EXTRACTION`, `CACHING` |

### 4.4 Compatibility Matrix & Operational Constraints

The compatibility layer evaluates observation requests against physical vehicle constraints:

```
+-----------------------------------------------------------------------------------------------------------+
|                                  OBSERVATION COMPATIBILITY MATRIX                                         |
+-----------------------------------------------------------------------------------------------------------+
| Observation Classification     | Allowed Instruments           | Vehicle Motion | Arm Turret State       |
+--------------------------------+-------------------------------+----------------+------------------------+
| GEOLOGICAL_ASSAY               | PIXL, SHERLOC, SuperCam, RIMFAX| Stationary     | Deployed (PIXL/SHERLOC)|
| SPECTRAL_SURVEY                | Mastcam-Z, SuperCam, SHERLOC  | Stationary     | Stowed or Contact      |
| ATMOSPHERIC_MEASUREMENT        | MEDA, Mastcam-Z               | Any (Drive/Stop| Stowed                 |
| SAMPLE_CORE_EXTRACTION         | CORING_TOOL, WATSON, Mastcam-Z| Stationary     | Deployed (Turret Drill)|
| HAZARD_INSPECTION              | Mastcam-Z, RIMFAX             | Any            | Stowed                 |
| TERRAIN_IMAGING                | Mastcam-Z, SuperCam (RMI)     | Stationary     | Stowed                 |
| PHOTOMETRIC_ANALYSIS           | Mastcam-Z, MEDA               | Stationary     | Stowed                 |
+-----------------------------------------------------------------------------------------------------------+
```

#### Physical Mutual Exclusivity Rules:
1. **Robotic Arm Turret Singularity Rule:** The arm turret holds PIXL, SHERLOC/WATSON, and the CORING_TOOL. Only **one** turret device can engage a target patch at any instant. Simultaneous abrasion and X-ray emission is mechanically prohibited.
2. **Vehicle Stability Rule:** High-precision spectroscopic instruments (SuperCam LIBS lasers, PIXL sub-millimeter collimators, WATSON focus stacks) require zero chassis vibration. Vehicle drive motors must be locked with holding torque enabled.
3. **Continuous Subsurface Sounding Exception:** RIMFAX is specifically designed to operate during traverse movement, emitting radar pulses every 10 cm of ground progress without imposing a dwell penalty.

---

## 5. Observation Scheduling Engine Requirements

### 5.1 Five-Phase Chronological Activity Model

Rather than inserting an arbitrary pause into the timeline, each scheduled science stop is resolved into **five discrete operational phases**:

```
[ VEHICLE TRAVERSE ]
        |
        v
+-------------------------------------------------------------------+
| PHASE 1: ROVER ARRIVAL AND SETTLE                                 |
| Duration: 180 s | Power: P_base + P_comm_standby (130 W)           |
| Action: Wheels halt, mechanical brake engage, IMU settle.        |
+-------------------------------------------------------------------+
        |
        v
+-------------------------------------------------------------------+
| PHASE 2: INSTRUMENT PREPARATION & WARMUP                          |
| Duration: 300 - 600 s | Power: P_base + P_heaters + P_arm (165 W)  |
| Action: Sensor un-stow, thermal de-ice, radiometric calibration.  |
+-------------------------------------------------------------------+
        |
        v
+-------------------------------------------------------------------+
| PHASE 3: ACTIVE OBSERVATION EXECUTION                             |
| Duration: Mode-specific (180 s - 5,400 s)                          |
| Power: P_base + P_inst_active + P_comm_telemetry (130 W - 255 W)   |
| Action: Laser firing, XRF excitation, spectral integration.       |
+-------------------------------------------------------------------+
        |
        v
+-------------------------------------------------------------------+
| PHASE 4: DATA POST-PROCESSING & CACHING                           |
| Duration: 120 s | Power: P_base + P_coprocessor (135 W)           |
| Action: Wavelet ICER compression, SHA-256 hash, non-volatile SSD. |
+-------------------------------------------------------------------+
        |
        v
+-------------------------------------------------------------------+
| PHASE 5: INSTRUMENT STOW & SECURE                                 |
| Duration: 240 s | Power: P_base + P_actuators (150 W)              |
| Action: Turret parked on contact bracket, mast azimuth locked.    |
+-------------------------------------------------------------------+
        |
        v
[ RESUME TRAVERSE ]
```

### 5.2 Integration with Milestone 13F Terramechanical & Electrical Engine

The observation scheduling engine directly couples with `src/marswalk/core/mission_resource_model.py`.

#### 1. Dynamic Energy Accounting
During an observation stop of duration $T_{\text{stop}} = \sum_{p=1}^5 \Delta t_p$, the electrical energy consumed $E_{\text{stop}}$ is calculated as:

$$E_{\text{stop}} = \sum_{p=1}^5 \int_0^{\Delta t_p} \Big( P_{\text{base}} + P_{\text{inst}, p}(t) + P_{\text{comm}, p}(t) \Big) dt \quad [\text{Joules}]$$

#### 2. First-Law Energy Conservation Invariant
At every transition between activity phases, the scheduler enforces:

$$|E_{\text{usable}} - (E_{\text{rem}}(t) + E_{\text{consumed}}(t))| \le 10^{-4}\text{ J}$$

Across all evaluated mission plans, this invariant guarantees that no energy is created or lost during science observation sequences.

#### 3. Peak Instantaneous Power Tracking
Drilling and active thermal warmup draw substantial instantaneous currents. The peak power across the mission is monitored:

$$P_{\text{peak}} = \max \Big( \max_{t} P_{\text{traverse}}(t), \max_{t} P_{\text{observation}}(t) \Big)$$

If $P_{\text{peak}} > P_{\text{bus,max}}$ (e.g., $320\text{ W}$ bus limit), the scheduler flags a power constraint violation.

### 5.3 Data Generation Accounting & Agent B Handoff Contract

Every completed observation produces a validated data payload. For each instrument mode $m$:
- Raw Data Bytes: $D_{\text{raw}} = V_{\text{raw}, m} \cdot 1024^2\text{ bytes}$.
- Compressed Data Bytes: $D_{\text{comp}} = \lfloor D_{\text{raw}} / \text{CR}_m \rfloor$.

At Phase 4 (*Data Post-Processing & Cache*), the scheduler generates a validated `MissionDataProductRecord` adhering to `schemas/api/v1/mission-data-product.schema.json` and hands it off to Agent B's `MissionDataLedger`:
```python
{
    "product_id": f"dp_{uuid.uuid4().hex[:12]}",
    "observation_id": obs_id,
    "target_id": target.id,
    "instrument_id": instrument.id,
    "mode_id": mode.id,
    "data_category": "SPECTRAL_CUBE",
    "raw_bytes": D_raw,
    "compressed_bytes": D_comp,
    "compression_ratio": CR,
    "created_at_s": current_time_s,
    "retention_priority": target.priority_score,
    "checksum_sha256": product_sha256,
    "is_simulated": True
}
```

---

## 6. Adaptive Science Scheduling Triggers

Planetary exploration is filled with operational uncertainties. Milestone 13G specifies five deterministic triggers that adaptively reschedule science activities without corrupting completed observations or historical logs.

```
+---------------------------------------------------------------------------------------------------------+
|                               ADAPTIVE SCIENCE SCHEDULING TRIGGERS                                      |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|   [ TRIGGER 1: UNREACHABLE TARGET ]                                                                     |
|   Condition: Terrain obstacle, slope > 25 deg, or sand slip > 40%                                       |
|   Action   : Mark target UNREACHABLE; prune downstream DAG; reroute to next Pareto candidate.           |
|                                                                                                         |
|   [ TRIGGER 2: RESOURCE VIOLATION (ENERGY / TIME) ]                                                     |
|   Condition: Battery SOC < reserve_margin_pct (20%) OR elapsed time > sol_duration_ceiling              |
|   Action   : Progressive 4-Stage Load Shedding (Drop core -> Switch to remote -> Rapid Tau -> Abort)    |
|                                                                                                         |
|   [ TRIGGER 3: INSTRUMENT UNAVAILABILITY ]                                                              |
|   Condition: Sensor telemetry anomaly, turret mechanical jam, or thermal heater failure                 |
|   Action   : Query Compatibility Layer for substitute instrument (e.g., PIXL -> SuperCam LIBS)          |
|                                                                                                         |
|   [ TRIGGER 4: STORAGE PRESSURE (ONBOARD SSD SATURATION) ]                                              |
|   Condition: S_used(t) / S_capacity > 85% with no imminent downlink pass                               |
|   Action   : Adaptive wavelet compression ratio increase (4:1 -> 10:1); thumbnail burst deferral        |
|                                                                                                         |
|   [ TRIGGER 5: REDUCED TRANSFER AVAILABILITY (UHF / DSN LINK DROP) ]                                    |
|   Condition: Orbiter line-of-sight masked by crater rim cliff or DSN ground outage                      |
|   Action   : Defer ground-in-the-loop operations (e.g., coring); switch to local survey caching         |
|                                                                                                         |
+---------------------------------------------------------------------------------------------------------+
```

### 6.1 Trigger 1: `UNREACHABLE_TARGET_TRIGGER`
- **Detection:** Pathfinding identifies an impassable terrain barrier (e.g., steep crater rim scarp $> 25^\circ$), an untraversable sand ripple field, or a prerequisite target that was previously blocked.
- **Scheduler Action:**
  1. The target is flagged as `TargetStatus.UNREACHABLE` with an explicit reason string.
  2. **DAG Pruning:** The scheduler traverses the dependency graph. Any candidate target requiring this target as a prerequisite is flagged as `REJECTED_PREREQUISITE_FAILED` and removed from the active candidate pool.
  3. **Alternative Pareto Selection:** The TSP permutation solver evaluates the remaining unvisited candidates, selecting the next highest utility target that fits within remaining mobility energy and time bounds.

### 6.2 Trigger 2: `RESOURCE_VIOLATION_TRIGGER`
- **Detection:** During traverse or science dwell, unexpected terrain drag (high $C_{rr}$ in loose regolith) or extended heater draw reduces predicted battery SOC below the safety reserve floor ($20\%$), or total elapsed sortie time approaches the single-sol limit ($14,400\text{ s}$ for rover).
- **Progressive 4-Stage Load Shedding:**
  - **Stage 1 (High-Power Shedding):** Cancel mechanical coring or abrasion operations ($145\text{ W}$, $5,400\text{ s}$).
  - **Stage 2 (Mode Substitution):** Downscale contact science (PIXL/SHERLOC) to remote sensing (SuperCam LIBS or Mastcam-Z multispectral, saving $100\text{ W}$ and $2,000\text{ s}$).
  - **Stage 3 (Rapid Inspection):** Downscale observation to a rapid $180\text{ s}$ atmospheric/photometric check.
  - **Stage 4 (Emergency Abort):** Cancel the observation stop entirely; command immediate return along the retrograde path to base or nearest safe haven.

### 6.3 Trigger 3: `INSTRUMENT_UNAVAILABILITY_TRIGGER`
- **Detection:** An instrument health monitor flags an anomaly (e.g., PIXL high-voltage power supply fault, robotic arm joint limit jam, or Mastcam-Z filter wheel stall).
- **Scheduler Action:**
  1. The target's required observation domain is queried against the Compatibility Matrix.
  2. If an alternative instrument exists on the vehicle capable of addressing the domain (e.g., SuperCam LIBS substituting for PIXL elemental chemistry), the observation plan is dynamically rewritten with the substitute instrument's power, duration, and data profile.
  3. If no alternative exists, the observation is deferred, and the dwell time allocation is converted to mobility margin.

### 6.4 Trigger 4: `STORAGE_PRESSURE_TRIGGER`
- **Detection:** Agent B's `MissionDataLedger` reports onboard flash storage occupancy exceeding the high-water threshold ($S_{\text{used}} / S_{\text{capacity}} \ge 0.85$) while no orbiter communication pass is active.
- **Scheduler Action:**
  1. **Dynamic Compression Scaling:** The scheduler instructs image processors to switch from near-lossless 3:1 wavelet compression to high-ratio 10:1 lossy compression.
  2. **Selective ROI Windowing:** Mastcam-Z panos are constrained to specific regions of interest (ROI) rather than full $360^\circ$ mosaics.
  3. **Data Culling Policy:** High-priority spectral vectors and telemetry logs are preserved; raw engineering calibration frames are purged from volatile buffers.

### 6.5 Trigger 5: `REDUCED_TRANSFER_AVAILABILITY_TRIGGER`
- **Detection:** Geometric line-of-sight raycasting to an overhead Mars relay orbiter (e.g., MRO or MAVEN) indicates that the orbiter's ground track passes behind the western delta scarp cliff, eliminating UHF connectivity.
- **Scheduler Action:**
  1. High-value sample extraction activities requiring ground Earth-in-the-loop confirmation before tube sealing are postponed.
  2. The rover switches to autonomous survey mode, executing observations and caching compressed products into solid-state memory until the next morning orbital pass.

---

## 7. Architectural Implementation Blueprint (`science_mission_planner.py`)

### 7.1 Proposed Data Structures

```python
"""
Core Architecture Blueprint for src/marswalk/core/science_mission_planner.py
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any

class ScientificPriorityClassification(str, Enum):
    USER_ASSIGNED_PRIORITY = "USER_ASSIGNED_PRIORITY"
    SOURCE_DERIVED_PRIORITY = "SOURCE_DERIVED_PRIORITY"
    UNASSESSED_PRIORITY = "UNASSESSED_PRIORITY"

class ScienceObjectiveCategory(str, Enum):
    GEOLOGICAL_CHARACTERIZATION = "GEOLOGICAL_CHARACTERIZATION"
    MINERALOGICAL_INVESTIGATION = "MINERALOGICAL_INVESTIGATION"
    ATMOSPHERIC_OBSERVATION = "ATMOSPHERIC_OBSERVATION"
    SURFACE_MORPHOLOGY = "SURFACE_MORPHOLOGY"
    ENVIRONMENTAL_MONITORING = "ENVIRONMENTAL_MONITORING"
    ASTROBIOLOGY_BIOSIGNATURE_SURVEY = "ASTROBIOLOGY_BIOSIGNATURE_SURVEY"

class InstrumentIdentifier(str, Enum):
    MASTCAM_Z = "MASTCAM_Z"
    SUPERCAM = "SUPERCAM"
    PIXL = "PIXL"
    SHERLOC = "SHERLOC"
    RIMFAX = "RIMFAX"
    MEDA = "MEDA"
    CORING_TOOL = "CORING_TOOL"

@dataclass
class InstrumentModeProfile:
    mode_id: str
    instrument_id: InstrumentIdentifier
    name: str
    duration_s: float
    operating_power_w: float
    raw_data_mb: float
    compression_ratio: float
    compatible_observations: List[str]
    is_turret_mounted: bool = False
    requires_stationary_vehicle: bool = True

@dataclass
class ObservationScheduleItem:
    item_id: str
    target_id: str
    target_name: str
    phase_name: str  # "SETTLE", "PREP", "EXECUTION", "COMPRESSION", "STOW"
    instrument_id: Optional[InstrumentIdentifier]
    mode_id: Optional[str]
    start_time_s: float
    end_time_s: float
    duration_s: float
    average_power_w: float
    energy_consumed_j: float
    data_generated_mb: float
    is_simulated: bool = True

@dataclass
class ScienceMissionSchedule:
    schedule_id: str
    campaign_id: str
    sol_index: int
    target_ids: List[str]
    schedule_items: List[ObservationScheduleItem]
    total_observation_duration_s: float
    total_observation_energy_j: float
    total_data_generated_mb: float
    peak_observation_power_w: float
    is_feasible: bool
    rejection_reasons: List[str] = field(default_factory=list)
```

### 7.2 Core Class Interfaces

```python
class ScienceMissionPlanner:
    """
    Orchestrates science target prioritization, instrument compatibility validation,
    multi-phase observation scheduling, and resource integration.
    """
    def __init__(self, instrument_registry: Optional[Dict[str, InstrumentModeProfile]] = None):
        self.instruments = instrument_registry or self._build_default_instrument_registry()

    def validate_target_priority(self, target: CampaignTarget) -> Tuple[ScientificPriorityClassification, float]:
        """Classifies target priority and enforces non-probabilistic truth disclosure."""
        ...

    def check_instrument_compatibility(
        self,
        observation_type: str,
        requested_instrument: InstrumentIdentifier,
        requested_mode: str
    ) -> bool:
        """Verifies instrument capability and mutual exclusivity."""
        ...

    def schedule_target_observation(
        self,
        target: CampaignTarget,
        arrival_time_s: float,
        rover_config: RoverResourceConfig,
        instrument_id: InstrumentIdentifier,
        mode_id: str
    ) -> List[ObservationScheduleItem]:
        """Generates 5-phase chronological observation activity events."""
        ...

    def evaluate_adaptive_triggers(
        self,
        active_schedule: ScienceMissionSchedule,
        current_battery_soc: float,
        current_storage_used_pct: float,
        comm_available: bool,
        anomalous_instruments: Set[InstrumentIdentifier]
    ) -> Optional[str]:
        """Detects operational trigger events and determines rescheduling action."""
        ...
```

---

## 8. Compliance, Verification Matrix & Scientific Disclaimers

### 8.1 Verification Against Scientific Guardrails

| Requirement | Guardrail Policy | Agent A Verification Mechanism |
|---|---|---|
| **No Artificial Measurements** | Never fabricate sensor telemetry as authentic Mars observations. | All observation records created by the scheduler are strictly flagged with `is_simulated=True` and `provenance="SIMULATED"`. |
| **Priority Provenance** | Distinguish user preference from empirical observation. | All targets are classified as `USER_ASSIGNED_PRIORITY`, `SOURCE_DERIVED_PRIORITY`, or `UNASSESSED_PRIORITY`. Reports include full citations. |
| **Conservation of Energy** | Energy must strictly balance across all observation activities. | Evaluated via 13F invariant: $\|E_{\text{usable}} - (E_{\text{rem}} + E_{\text{consumed}})\| \le 10^{-4}\text{ J}$. |
| **No Astronaut Safety Claims** | Modeled plans must not be labeled flight-certified. | Disclaimers explicitly state that all schedules and rates are *Simulated Planning Heuristics*. |
| **Physical SI Units** | Quantities must use recognized physical units. | Durations in seconds ($\text{s}$), energy in Joules ($\text{J}$) / Watt-hours ($\text{Wh}$), power in Watts ($\text{W}$), data in Megabytes ($\text{MB}$). |

### 8.2 Primary Scientific Literature Citations

All instrument specifications and environmental parameters are grounded in primary planetary science literature:
1. **Perseverance Science Overview:** Farley, K.A. et al. (2020), *"Mars 2020 Mission Overview"*, *Space Science Reviews*, 216, 142.
2. **Mastcam-Z Imaging Suite:** Bell, J.F. et al. (2021), *"The Mars 2020 Perseverance Rover Mast Camera Zoom (Mastcam-Z) Multispectral, Stereoscopic Imaging Investigation"*, *Space Science Reviews*, 217, 24.
3. **SuperCam Remote Sensing:** Wiens, R.C. et al. (2021), *"The SuperCam Instrument Suite on the NASA Mars 2020 Rover: Body Unit and Combined System Tests"*, *Space Science Reviews*, 217, 4.
4. **PIXL Micro-XRF:** Allwood, A.C. et al. (2020), *"The PIXL Instrument on the Mars 2020 Perseverance Rover"*, *Space Science Reviews*, 216, 134.
5. **SHERLOC Deep UV Raman:** Beegle, L.W. et al. (2021), *"The SHERLOC Investigation on the Mars 2020 Perseverance Rover"*, *Space Science Reviews*, 217, 83.
6. **RIMFAX Subsurface Radar:** Hamran, S.E. et al. (2020), *"Radar Imager for Mars' Subsurface Experiment—RIMFAX"*, *Space Science Reviews*, 216, 126.
7. **MEDA Environmental Analyzer:** Rodriguez-Manfredi, J.A. et al. (2021), *"The Mars Environmental Dynamics Analyzer (MEDA) Investigation on the Mars 2020 Perseverance Rover"*, *Space Science Reviews*, 217, 48.
8. **Jezero Western Delta Science:** Scheller, E.L. et al. (2022), *"Aqueous alteration processes in Jezero crater, Mars—implications for biosignature preservation"*, *Science*, 378, 1105–1110.

---

## 9. Next Steps & Integration Roadmap

1. **Implement `src/marswalk/core/science_mission_planner.py`:**
   - Implement the `ScientificPriorityClassification` enum and priority validator.
   - Implement the `InstrumentModeProfile` registry and compatibility layer.
   - Implement the 5-phase `ScienceMissionPlanner` scheduler.
2. **Integrate with Agent B (`mission_data_ledger.py`):**
   - Stream `MissionDataProductRecord` instances into the onboard storage ledger upon Phase 4 completion.
3. **Integrate with Agent C (`joint_mission_planner.py`):**
   - Provide multi-phase observation durations, active energy draw, and science utility vectors to the joint Pareto optimizer.
4. **Deliver Unit and Regression Tests (`tests/test_milestone_13g_science_mission.py`):**
   - Test priority provenance validation.
   - Test instrument compatibility and mutual exclusivity enforcement.
   - Verify First-Law energy conservation during observation sequences.
   - Test the 5 adaptive triggers under simulated disruptions.
