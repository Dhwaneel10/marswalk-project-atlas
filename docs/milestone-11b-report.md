# MarsWalk 2.0 — Milestone 11B Engineering & Verification Report
## Campaign Progress & Science Observation Registry

**Milestone:** 11B (MarsWalk 2.0 V2)  
**Status:** COMPLETE & VERIFIED  
**Date:** 2026-10-29  
**Target Environment:** Mars (IAU 2000 Sphere / USGS CTX DTM 20m Jezero Crater Topography)  
**Verification Baseline:** Full Repository Pytest Suite Passing (100% Green), Atlas Preflight 12/12  

---

## 1. Executive Summary

Milestone 11B elevates the **Mission Campaign Orchestrator** from a static multi-sol scheduler into an interactive, closed-loop **Campaign Progress & Science Observation Registry**. 

During simulated campaign execution across Jezero Crater:
1. Field sorties and science targets advance through strict lifecycle state machines (`PLANNED`, `READY`, `IN_PROGRESS`, `COMPLETED`, `BLOCKED`, `DEFERRED`, `CANCELLED`).
2. Science observations are captured as first-class, schema-validated artifacts (`schemas/api/v1/science-observation.schema.json`) with mandatory physical SI units (`Pa`, `K`, `degC`, `m/s`, `m`, `%`, `ppm`, `count`) and strict source provenance tags (`SIMULATED`, `IMPORTED_PDS_MEDA`, `IMPORTED_PDS_REMS`, `MEASURED_IN_SITU`).
3. Completing a target permanently prevents it from being rescheduled in future sols (**Non-Rescheduling Invariant**), unlocks newly eligible downstream targets in the prerequisite DAG, freezes past executed sols, increments the campaign version (`v1 -> v2`), and records a revision comparison delta.
4. Blocking a target (`TARGET_BLOCKED`) flags it as inaccessible, tracks the causal rationale, and cleanly adapts remaining planned sorties.
5. All observations and progress events are atomically persisted to `data/workspaces/observations/` and `data/workspaces/campaign_progress/` without mutating or deleting existing missions, event ledgers, weather records, or Decision Packs.

---

## 2. Core Implementation Summary

### 2.1 Schema Architecture & Contracts
- **`schemas/api/v1/science-observation.schema.json`**:
  - Validates observation records, requiring `observation_id`, `campaign_id`, `target_id`, `observation_type`, `provenance`, and `is_simulated`.
  - Enforces physical units on quantitative measurements and prevents fabrication: missing fields remain explicitly `null`.
- **`schemas/api/v1/campaign-progress-event.schema.json`**:
  - Validates discrete progress events, requiring `event_id`, `campaign_id`, `sol_index`, `event_type`, `timestamp_utc`, and `idempotency_key`.
  - Connects simulated progress events with Sortie Black Box ledgers.
- **`schemas/api/v1/mission-campaign.schema.json`**:
  - Backward-compatibly augmented with `progress` and `observations_summary` blocks.
  - Expanded `summary.overall_status` enum to support progress states (`IN_PROGRESS`, `COMPLETED`, `FEASIBLE`, `PARTIALLY_FEASIBLE`, `INFEASIBLE`).
  - Registered in `src/marswalk/api/contracts.py` under `SCHEMA_FILE_MAP`.

### 2.2 Progression Controller (`src/marswalk/core/campaign_progress.py`)
- **`ObservationType` & `ObservationProvenance`**: Categorizes geological assays, spectral surveys, atmospheric measurements, sample coring, and hazard inspections with authentic provenance tracking.
- **`RECOGNIZED_PHYSICAL_UNITS`**: Validates SI and planetary units (`Pa`, `hPa`, `kPa`, `bar`, `mbar`, `K`, `degC`, `m/s`, `km/h`, `m`, `km`, `cm`, `mm`, `s`, `min`, `h`, `sol`, `deg`, `rad`, `J`, `W`, `kg`, `g`, `%`, `ppm`, `count`, `dimensionless`). Arbitrary non-SI units (`mph`, `psi`, `feet`) raise `ValueError`.
- **`advance_campaign_progress`**:
  - Enforces idempotency: duplicate events with identical `idempotency_key` are rejected.
  - Updates target states: `TARGET_VISITED` or `TARGET_OBSERVED` marks target `COMPLETED`.
  - Preserves Non-Rescheduling Invariant: completed targets are removed from candidate pool for all future sols.
  - Prerequisite DAG Unblocking: filters satisfied prerequisites and evaluates newly eligible downstream targets.
  - Sol Freezing: past sorties (`sol < sol_index`) remain immutable; remaining sorties are recalculated with shifted sol indices.
  - Version Increment: increments campaign version (`v1 -> v2`) and records `revision_comparison` deltas.

### 2.3 Workspace Persistence (`src/marswalk/api/workspace.py`)
- Added `DEFAULT_OBSERVATIONS_DIR = data/workspaces/observations/`.
- Added `DEFAULT_CAMPAIGN_PROGRESS_DIR = data/workspaces/campaign_progress/`.
- Implemented `save_observation`, `get_observation`, `list_observations(campaign_id, target_id)`.
- Implemented `save_progress_event`, `list_progress_events(campaign_id)`.
- Guaranteed atomic write safety via sibling temp file and `os.replace`.

### 2.4 Versioned REST API Routes (`src/marswalk/api/service.py` & `scripts/run_atlas.py`)
- `POST /api/campaign/progress`: Records progress event, updates target/sortie state machines, and dynamically recalculates remaining sols.
- `GET /api/campaign/progress?campaign_id=<id>`: Retrieves active sol, completion percentage, completed/blocked targets, events, and observations.
- `POST /api/campaign/observations`: Validates and saves standalone science observation records.
- `GET /api/campaign/observations?campaign_id=<id>&target_id=<id>`: Lists filtered observations.
- `GET /api/campaign/observations/<obs_id>`: Retrieves observation by ID.
- `GET /api/campaign/next_eligible_targets?campaign_id=<id>`: Identifies candidate targets in DAG whose prerequisites have been satisfied.

### 2.5 Atlas Web Application (`web/index.html` & `web/app.js`)
- Added **Campaign Mode Tabs Switcher**:
  - View 1: `Sortie Schedules & Target DAG` (Milestone 11A multi-sol itinerary).
  - View 2: `Execution Progress & Science Registry` (Milestone 11B real-time progress and telemetry).
- **Execution Progress & Science Registry Dashboard**:
  - Progress bar showing `% Objectives Completed`, Active Sol, and observation count.
  - Target Progression Ledger with status badges (`[COMPLETED]`, `[ELIGIBLE]`, `[SCHEDULED]`, `[BLOCKED]`) and quick actions (`[Observe]`, `[Block]`).
  - Science Observations Registry table with physical SI units, timestamp, and `[SIMULATED]` vs `[AUTHENTIC PDS]` badges.
- **Science Observation Logging Modal (`#campaignObservationModal`)**:
  - Target selector pre-populated with campaign targets.
  - Sol index input.
  - Observation type selector and instrument name input.
  - Quantitative measurement form with mandatory physical SI unit validation.
  - Qualitative field notes textarea.
- Exposed progress methods in `window.MarsWalkAtlas`.

---

## 3. Verification & Acceptance Testing

The dedicated test suite `tests/test_milestone_11b_campaign_progress.py` includes 13 test cases covering all requirements:

| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_observation_valid_si_units` | Validates observation record with recognized SI units (`%`, `K`, `Pa`, `m`) against schema | **PASSED** |
| `test_observation_invalid_units_raise_error` | Verifies non-SI units (`mph`) raise `ValueError` | **PASSED** |
| `test_observation_provenance_and_simulated_consistency` | Enforces `SIMULATED` vs `is_simulated=True` and authentic PDS vs `is_simulated=False` | **PASSED** |
| `test_observation_dataclass_roundtrip` | Verifies dataclass `to_dict()` and `from_dict()` serialization fidelity | **PASSED** |
| `test_progress_event_validation` | Validates progress event contract against schema | **PASSED** |
| `test_progress_event_idempotency_rejection` | Verifies duplicate event with identical idempotency key is rejected | **PASSED** |
| `test_target_completion_and_non_rescheduling_invariant` | Verifies target transitions to `COMPLETED` and is NEVER rescheduled in remaining planned sols | **PASSED** |
| `test_prerequisite_dag_unblocking` | Verifies downstream child target transitions to eligible once parent is completed | **PASSED** |
| `test_target_blockage_lifecycle` | Verifies target transitions to `BLOCKED` with causal reason recorded | **PASSED** |
| `test_workspace_save_and_list_observations` | Verifies saving, retrieving, and filtering observations in workspace | **PASSED** |
| `test_workspace_save_and_list_progress_events` | Verifies saving and retrieving progress events in workspace | **PASSED** |
| `test_api_service_progress_and_observations` | Exercises service layer API functions directly | **PASSED** |
| `test_live_server_campaign_progress_endpoints` | Exercises live HTTP endpoints on port 3000 across full lifecycle | **PASSED** |

---

## 4. Scientific Rigor & Provenance Accountability

1. **Anti-Fabrication Constraints**: No simulated observation is ever presented as authentic Martian data. All simulated measurements carry `provenance="SIMULATED"` and `is_simulated=true`.
2. **Authentic Data Preservation**: NASA PDS MEDA and REMS records retain their primary source citations, instrument serials, and coordinate frames.
3. **Missing Data Rules**: When observational data is unmeasured or unavailable, the value remains explicitly `null`.
4. **Research Disclaimer**: Prominently presented on all UI panels, HTML exports, and JSON payloads:
   > *RESEARCH PROTOTYPE • NOT OPERATIONAL SAFETY PATHFINDING • USGS CTX / NASA MARS 2020 DATA*
