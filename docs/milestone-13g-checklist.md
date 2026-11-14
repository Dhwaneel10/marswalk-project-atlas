# Milestone 13G — Atlas Science Return & Data Logistics Co-Design Task Checklist

**Milestone:** 13G — Science Target Prioritization × Observation Scheduling × Onboard Data Management × Resource-Constrained Mission Optimization  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Execution Environment:** Windows 11 (64-bit), Python 3.12.4 (`.venv`), Vanilla JS / Three.js Frontend, Atlas API Daemon on port 3000  
**Started:** 2026-11-01T01:24:00+05:30  
**Status:** IN PROGRESS  

---

## 1. Governance, Skills & Architecture Audit
- [x] MarsWalk skills activated (`marswalk-regression-guardian`, `marswalk-scientific-integrity`, `marswalk-browser-acceptance`)
- [x] Working tree verified clean and Atlas server verified online on port 3000
- [x] Task checklist initialized (`docs/milestone-13g-checklist.md`)
- [x] 4 Specialist Subagents launched (A: Science, B: Data/Storage, C: Optimization, D: Validation/UI)
- [x] Subagent findings reviewed and synthesized
- [x] Architecture Audit completed: `docs/milestone-13g-architecture-audit.md`
- [x] Required 13F Scientific Correction applied: Classify non-regenerative descent as a conservative configurable modelling assumption rather than an established Mars 2020 flight fact across all 13F docs and code

---

## 2. Core Engine: Science Mission Planner (`src/marswalk/core/science_mission_planner.py`)
- [x] Science target registry integration:
  - Reuse existing target models and observation registry
  - Configurable priority types: `USER_ASSIGNED_PRIORITY`, `SOURCE_DERIVED_PRIORITY`, `UNASSESSED_PRIORITY`
  - Explicit disclosure that utility scores represent configured mission preferences, not objective scientific value
- [x] Configurable mission objectives:
  - Geological characterization, mineralogical investigation, atmospheric observation, surface morphology, environmental monitoring
- [x] Instrument-to-Observation compatibility layer:
  - Instrument taxonomy with explicit synthetic demonstration profiles (e.g., Mastcam-Z, SuperCam, PIXL, SHERLOC, RIMFAX, MEDA)
  - Operating power draw, duration, compatible observation types, and rejection of invalid combinations
- [x] Observation & instrument scheduling:
  - Chronological schedule: arrival, instrument prep, observation start/completion, energy expenditure (using 13F resource model), and data generation
- [x] Adaptive science scheduling:
  - Responds to unreachable targets, resource violations, instrument unavailability, storage pressure, or reduced transfer availability

---

## 3. Data Generation & Onboard Storage Engine (`src/marswalk/core/mission_data_ledger.py`)
- [x] Data product identity & tracking:
  - Unique data product ID, observation ID, target, instrument, data category, size in bytes, creation time, status, checksum (SHA-256), provenance, retention state
- [x] Synthetic data volume profiles:
  - Environmental measurements, imaging sequences, high-res image collections, spectral cubes, radar scans (all explicitly marked as synthetic)
- [x] Exact onboard storage byte accounting:
  - $S_{\text{used}, t} = S_{\text{used}, t-1} + S_{\text{generated}, t} - S_{\text{released}, t}$
  - Storage is only released AFTER a transfer has been verified and recorded
  - Strict storage capacity overflow rejection unless explicitly permitted by policy
- [x] Storage management policies:
  - Priority-based retention, transfer-first allocation, protected observation records, queue ordering
  - Model-generated planning indicators: `STORAGE_AVAILABLE`, `STORAGE_PRESSURE`, `STORAGE_NEAR_CAPACITY`, `STORAGE_CAPACITY_REACHED`, `TRANSFER_QUEUE_BACKLOG`, `HIGH_PRIORITY_DATA_PENDING`
- [x] Communications-aware simulated data transfer model:
  - Explicit link assumptions: transfer rate $R_{\text{configured}}$, duty cycle, max duration, protocol overhead
  - Strict formula: $D_{\text{transferred}} = R_{\text{configured}} \cdot \Delta t$
  - Geometric connectivity dependency: evaluates paths through RelayNet graph
  - Transfer queue with partial, completed, deferred, and failed transfer tracking
  - Strict label: `SIMULATED_DATA_TRANSFER` (no claim of actual Mars radio transmission or Earth downlink)
  - Exact data conservation: $D_{\text{backlog}} = D_{\text{collection}} - D_{\text{simulated\_transfer}} - D_{\text{explicitly\_released}}$

---

## 4. Science Return & Logistics Optimization Integration
- [x] Extend Joint Mission Planner (`src/marswalk/core/joint_mission_planner.py`):
  - Co-evaluate traverse, targets, observation schedule, relays, rover/relay energy, mission time, data volume, storage, and simulated transfer
  - Science utility: $U_{\text{science}} = \sum w_i x_i$ based on user-configured priorities and objective weights
  - Hard constraint enforcement: energy budget, reserve floor, duration limit, storage capacity, instrument availability
- [x] Multi-dimensional Pareto Analysis:
  - Non-dominated ranking across science utility, energy, duration, relays, connectivity, data collected, data transferred, and storage occupancy
  - Documented normalization and Marginal Rate of Substitution (MRS) for science vs energy and science vs data return

---

## 5. API & Data Architecture
- [x] Add versioned Draft 2020-12 JSON schemas in `schemas/api/v1/`:
  - `science-mission-evaluation.schema.json`
  - `science-mission-schedule.schema.json`
  - `mission-data-product.schema.json`
  - `mission-storage-ledger.schema.json`
  - `simulated-data-transfer.schema.json`
- [x] Implement and route API endpoints in `src/marswalk/api/service.py` & `scripts/run_atlas.py`:
  - `POST /api/science-mission/evaluate`
  - `POST /api/science-mission/optimize`
  - `GET /api/science-mission/configurations`
  - `GET /api/science-mission/compatibility`
  - `POST /api/science-mission/transfers/evaluate`
  - `POST /api/science-mission/recovery-lab`

---

## 6. Frontend & 3D Mission Theater Integration
- [x] Update `web/index.html` & `web/styles.css`:
  - Extend Joint Studio wizard to include Science Target Prioritization and Data Logistics steps
  - Add Onboard Storage fill level bar, transfer queue backlog, and science return metrics
  - Add Pareto modes: Science Return vs Energy, Science Return vs Data Transferred, Storage vs Distance
- [x] Update Three.js frontend (`web/app.js`):
  - In-theater Data Logistics HUD telemetry (storage bar, transfer rate, queue backlog)
  - Synchronize timeline scrubber with observation events, data generation, and simulated transfers
  - Interactive spatial inspector for science targets, data products, and transfer events
  - Verify syntax with `node --check web/app.js`

---

## 7. Verification & Quality Gates
- [x] Unit & integration test suite: `tests/test_milestone_13g_science_mission.py`
  - 17/17 tests passing (0.51s)
- [x] Regression testing:
  - Milestone 13 suite: 114/114 passing (7.06s)
  - Complete repository test suite: 855/855 passing (174.51s)
  - Preflight readiness check: 12/12 passing (396.9ms)
- [x] Automated Browser CDP Acceptance (`scripts/verify_science_mission_browser.py`):
  - 8/8 high-resolution showcase screenshots in `outputs/conference_showcase/science_logistics/`
  - 0 console errors and 0 horizontal overflow on $1920\times 1080$ and $1366\times 768$

---

## 8. Documentation & Deliverables
- [x] `docs/milestone-13g-recovery-audit.md`
- [x] `docs/milestone-13g-scientific-compatibility.md`
- [x] `docs/science-mission-planner-architecture.md`
- [x] `docs/science-data-logistics-methods.md`
- [x] `docs/onboard-data-management-guide.md`
- [x] `docs/science-mission-recovery-lab.md`
- [x] `docs/milestone-13g-validation-report.md`
- [x] `docs/milestone-13g-final-report.md`
- [x] `outputs/conference_showcase/science_logistics/README.md`
- [x] Update `README.md`, `docs/conference-demo-guide.md`, `docs/v2-demonstration-runbook.md`
- [x] Conversation artifact `milestone_13g_report.md` and user handoff
