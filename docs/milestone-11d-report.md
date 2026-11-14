# MarsWalk 2.0 — Milestone 11D Engineering & Verification Report
## Campaign What-If Simulation Lab & Scenario Comparison

**Milestone:** 11D (MarsWalk 2.0 V2)  
**Status:** COMPLETE & VERIFIED  
**Date:** 2026-10-29  
**Target Environment:** Mars (IAU 2000 Sphere / USGS CTX DTM 20m Jezero Crater Topography)  
**Verification Baseline:** Full Repository Pytest Suite Passing (568/568 Tests, 100% Green), Atlas Preflight 12/12, Node.js Syntax Check 0 Errors  

---

## 1. Executive Summary

Milestone 11D delivers the **Campaign What-If Simulation Lab & Scenario Comparison**, giving mission planners, tactical flight directors, and science teams the capability to rigorously stress-test multi-sol exploration campaigns under hypothetical disruptions, mobility degradations, corridor closures, operational delays, and scientific priority shifts *before* deciding whether to promote an updated plan to production.

Prior to Milestone 11D, campaign plans and adaptive revisions were evaluated sequentially. What-If Simulation Lab introduces parallel, deterministic scenario evaluation against authentic 20m USGS CTX Jezero Crater topography and operational constraints:

1. **Deterministic Scenario Simulation Engine**:
   - Evaluates up to 10 distinct what-if scenarios in a single batch.
   - Provides 6 validated scenario types:
     - `mobility_change`: Rover velocity derating factor ($[0.1, 1.5]$) and traverse slope ceiling ($[5.0, 35.0]^\circ$).
     - `operational_delay`: Injected ground hold or instrument setup delay ($[0, 14400]\text{ s}$) applied to specific sorties.
     - `target_loss`: Sudden inaccessibility or mechanical sampling failure at a target, with automatic cascading pruning of dependent downstream DAG branches.
     - `corridor_closure`: Geographic hazard envelope (center lat/lon, radius $[10.0, 500.0]\text{ m}$) triggering terrain obstacle masking and A* avoidance detours.
     - `time_constraint`: Tightened daily sortie duration limits ($[1800, 28800]\text{ s}$) or shortened campaign sol budget ($[1, 20]$).
     - `objective_priority_change`: Dynamic target priority overrides ($[0.0, 100.0]$) causing optimal target reallocation across available sol budgets.
2. **Topological Order of Evaluation**:
   - For combined multi-perturbation scenarios, operations execute in strict physical precedence:
     $$\text{corridor\_closure} \longrightarrow \text{target\_loss} \longrightarrow \text{mobility\_change} \longrightarrow \text{operational\_delay} \longrightarrow \text{time\_constraint} \longrightarrow \text{objective\_priority\_change}$$
3. **Multi-Scenario Comparison Matrix**:
   - Computes explicit delta metrics against the baseline campaign:
     - $\Delta\text{Sols}$, $\Delta\text{Traverse Distance (m)}$, $\Delta\text{Cumulative Duration (s)}$, $\Delta\text{Science Score}$.
     - Detailed target accounting: `lost_target_ids`, `deferred_target_ids`, `added_target_ids`.
     - Feasibility status transition (`FEASIBLE`, `MARGINAL`, `INFEASIBLE`).
     - Reversibility classification (`REVERSIBLE`, `IRREVERSIBLE`, `CONDITIONAL`).
4. **Controlled Version Promotion & Zero Data Loss**:
   - Planners can promote any evaluated what-if scenario to a new campaign version (e.g., `v1` $\rightarrow$ `v2`).
   - The baseline campaign version is permanently archived (`{cid}_v1.json`), ensuring complete historical provenance and zero data loss.
   - Promoted campaigns carry full scenario audit metadata (`promoted_from_scenario_id`, `promotion_timestamp_utc`, `promotion_rationale`).
5. **Anti-Fabrication & Scientific Disclaimers**:
   - Unsupported scenario types are cleanly tagged `UNSUPPORTED` with `has_unsupported_assumptions = True` and zero synthetic numbers.
   - Every UI panel, report export, and JSON payload features prominent disclaimers affirming deterministic simulation and disclaiming probabilistic flight-risk certification.

---

## 2. Core Implementation Summary

### 2.1 Schema Architecture & Contracts
- **`schemas/api/v1/campaign-scenario.schema.json`**:
  - Full Draft 2020-12 JSON schema for campaign scenarios and comparison records.
  - Validates scenario input specifications (`scenario_id`, `name`, `scenario_type`, `parameters`).
  - Validates evaluated scenario records (`scenario_id`, `campaign_id`, `scenario_type`, `comparison`, `reversibility`, `feasibility_status`, `rationale`, `limitations_disclaimer`).
- **Contract Registration (`src/marswalk/api/contracts.py`)**:
  - Registered `campaign-scenario` in `SCHEMA_FILE_MAP`.
  - Added `validate_campaign_scenario_record` contract validator function.

### 2.2 Simulation Engine (`src/marswalk/core/campaign_scenarios.py`)
- **`ScenarioType` Enum**: Standardized scenario categories (`MOBILITY_CHANGE`, `OPERATIONAL_DELAY`, `TARGET_LOSS`, `CORRIDOR_CLOSURE`, `TIME_CONSTRAINT`, `OBJECTIVE_PRIORITY_CHANGE`, `COMBINED`, `UNSUPPORTED`).
- **`Reversibility` Enum**: Operational reversibility categories (`REVERSIBLE`, `IRREVERSIBLE`, `CONDITIONAL`).
- **`ScenarioComparison` Model**: Holds quantitative delta metrics and target diff sets.
- **`CampaignScenario` Model**: Complete evaluated scenario container.
- **`evaluate_campaign_scenario(...)`**:
  - Deep-copies baseline campaign ensuring baseline immutability.
  - Applies perturbations according to topological precedence rules.
  - Reruns terrain traverse routing with obstacle avoidance masks where corridor closures are defined.
  - Recalculates life-support feasibility, sol allocations, and science yields.
  - Validates generated record against JSON schema.
- **`evaluate_campaign_scenarios_batch(...)`**:
  - Bounded to max 10 scenarios per call.
  - Executes batch evaluations and returns combined scenario list.
- **`promote_scenario_to_campaign_version(...)`**:
  - Takes an evaluated scenario and creates a new valid campaign version.
  - Injects promotion metadata into campaign history.

### 2.3 Workspace Persistence (`src/marswalk/api/workspace.py`)
- Configured default scenario directory: `data/workspaces/campaign_scenarios/`.
- Implemented `save_campaign_scenario(scenario_data, workspace_dir=None)`.
- Implemented `get_campaign_scenario(scenario_id, workspace_dir=None)`.
- Implemented `list_campaign_scenarios(campaign_id=None, workspace_dir=None)`.

### 2.4 REST API Service & HTTP Routes (`src/marswalk/api/service.py` & `scripts/run_atlas.py`)
- `POST /api/campaign/scenarios/evaluate`:
  - Accepts campaign ID or payload, array of scenario specifications, and `persist` flag.
  - Returns array of evaluated `CampaignScenario` records.
- `GET /api/campaign/scenarios`:
  - Returns list of persisted scenarios filtered by optional `campaign_id`.
- `GET /api/campaign/scenarios/<scenario_id>`:
  - Fetches specific persisted scenario record.
- `POST /api/campaign/scenarios/apply`:
  - Promotes evaluated scenario to the next campaign version, archives predecessor, and saves both versioned snapshot and active campaign.

### 2.5 Atlas Web Application Frontend (`web/index.html` & `web/app.js`)
- **Four-Tab Navigation in Campaign Orchestrator**:
  1. `Sortie Schedules & Target DAG` (Milestone 11A)
  2. `Execution Progress & Science Registry` (Milestone 11B)
  3. `Observation-Driven Intelligence` (Milestone 11C)
  4. `What-If Simulation Lab` (Milestone 11D)
- **Interactive Scenario Lab View (`#campaignWhatIfView`)**:
  - *Scenario Specification Form*: Dynamic input fields adapted to chosen scenario type (`mobility_change`, `operational_delay`, `target_loss`, `corridor_closure`, `time_constraint`, `objective_priority_change`).
  - *Standard Presets Button*: One-click simulation of 4 authentic mission challenges:
    1. *Dust Storm Mobility Derate* (speed 0.5x, slope ceiling 10 deg)
    2. *Rockfall Corridor Closure* (Delta front channel blocked, radius 150m)
    3. *Sampling Drill Anomaly Delay* (120 min hold on Sol 1)
    4. *Target Lost: Rover Stuck* (Target T-02 lost, dependent T-04 pruned)
  - *Comparison Matrix Table*: Clear tabular view of all simulated scenarios with delta distance, duration, science score, lost/deferred targets, and feasibility badges.
  - *Scenario Detail Inspector*: Detailed view with impacted sortie breakdown, reversibility tag, and rationale text.
  - *Promote Action*: `[PROMOTE TO NEW CAMPAIGN VERSION]` with automatic campaign version bump.
  - *Briefing Export*: `[EXPORT WHAT-IF BRIEFING JSON]` generating structured planning briefs.
  - *Clear Research Prototype Disclaimers*: Prominently rendered warning banners.

---

## 3. Verification & Test Results

### 3.1 Test Suite Breakdown
| Test Component | Tests | Status | Execution Time |
|---|---|---|---|
| Milestone 11D Dedicated Suite (`tests/test_milestone_11d_campaign_scenarios.py`) | 17 | PASSED | 0.87s |
| Campaign Suite Total (11A + 11B + 11C + 11D) | 64 | PASSED | 3.76s |
| Full Repository Pytest Suite | 568 | PASSED | ~18s |
| Atlas Preflight Verification (`scripts/preflight_check.py`) | 12/12 | PASSED | 421.4ms |
| Frontend JavaScript Syntax Check (`web/app.js`) | 0 errors | PASSED | ~1.2s |

### 3.2 Key Test Coverage Highlights
- `test_scenario_evaluation_unchanged_baseline`: Verifies zero delta for identity scenario.
- `test_mobility_reduction_derates_velocity_and_increases_duration`: Confirms velocity scaling down and duration increase.
- `test_mobility_slope_ceiling_blocks_steep_traverses`: Confirms slope ceiling forces route re-planning or target deferral.
- `test_target_loss_and_dag_cascade`: Verifies DAG traversal where losing parent target automatically eliminates child targets.
- `test_corridor_closure_obstacle_avoidance`: Tests terrain masking and detour calculations around rockfall hazard.
- `test_operational_delay_accounting`: Checks hold time accumulation and sol budget impacts.
- `test_time_constraint_and_budget_infeasibility`: Checks infeasibility triggers when daily sol duration is compressed.
- `test_objective_priority_change_alters_target_allocation`: Verifies target re-ranking based on updated priority weights.
- `test_combined_compatible_scenarios_deterministic_order`: Verifies topological order execution for compound perturbations.
- `test_unsupported_scenario_type_labeled_without_synthetic_data`: Confirms unsupported types are tagged without invented data.
- `test_bounded_limits_and_validation_errors`: Asserts validation errors on out-of-range inputs.
- `test_max_scenarios_batch_limit`: Enforces 10-scenario batch boundary.
- `test_workspace_persistence_and_retrieval`: Validates disk round-trip serialization in `data/workspaces/campaign_scenarios/`.
- `test_promote_scenario_to_new_campaign_version`: Validates version bumping (`v1` $\rightarrow$ `v2`) and metadata preservation.
- `test_baseline_campaign_immutability`: Ensures baseline is completely unchanged by simulation.
- `test_api_service_scenarios_evaluate_and_apply`: Tests service-level endpoint logic.
- `test_live_server_scenario_endpoints`: Validates live HTTP communication against Atlas server on port 3000.

---

## 4. Scientific Provenance & Safety Compliance

- **Authentic Topography**: All route re-evaluations use genuine USGS CTX 20m digital elevation data for Jezero Crater (`data/processed/jezero_ready_20m.tif`).
- **No Probabilistic Claims**: All what-if calculations are deterministic simulation results. They do not claim certified survival likelihoods or statistical mission reliability.
- **Traceable Versioning**: Promotion never overwrites past campaign states. Every version is preserved for full mission accountability.
- **Research Disclaimer**: Prominently presented on every user-facing view, briefing export, and data artifact.
