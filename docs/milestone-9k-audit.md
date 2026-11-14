# MarsWalk 2.0 — Milestone 9K Pre-Implementation Audit Report
## Persistent Mission Workspace, Experiment Library, and Reproducible Analysis

**Date:** October 18, 2026  
**Auditor:** Principal Software Architect, Planetary Mission Planning Engineer, & Simulation Engineer  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Current Test Suite Status:** 171 Passed (100% pass rate in 43.68s)  
**Specification Baseline:** Milestone 9J Contracts (JSON Schema Draft 2020-12)

---

## 1. Executive Summary

Milestone 9J successfully introduced versioned JSON Schema Draft 2020-12 data contracts, deterministic SHA-256 mission fingerprinting, multi-stop 2-Opt TSP optimization, and browser briefing exports. However, **all mission configurations and experiment results currently reside strictly in ephemeral client memory or one-off file downloads**. 

When a user closes or refreshes the browser, or when the server restarts:
- In-progress mission designs and intermediate stop selections are lost.
- Multi-scenario comparisons and parameter sensitivity sweeps vanish.
- Recovery plans and trade-off deliberations cannot be audited or retrieved.
- Re-running an analysis requires reconstructing the mission from scratch.

Milestone 9K introduces a **robust, atomic, filesystem-based persistence architecture** for both Mission Configurations and Simulation Experiments without requiring an external database or cloud service.

---

## 2. Inventory of Existing Persistence & State

| Component | Current State | Deficiencies & Gaps for Multi-Session Work |
| :--- | :--- | :--- |
| **Mission Storage** | Ephemeral browser memory (`customStart`, `customGoal`, `activeIntermediateStops`). | No server-side mission library. Missions cannot be named, saved, reopened, duplicated, or deleted. |
| **Preferences Storage** | `data/preferences/commander_preferences.json` (atomic rename with `os.replace`). | Only stores machine learning preference weights for routing profiles; does not store mission definitions. |
| **Simulation Experiments** | Stored in ephemeral frontend state (`lastComparisonResult`, `lastSensitivityResult`, `lastRecoveryPlan`). | No persistent experiment records. Historical outcomes cannot be compared across sessions. |
| **Export Mechanism** | Ephemeral blob downloads (`marswalk_mission_briefing_<timestamp>.json` and `.md`). | Downloaded files are not cataloged on the server; client cannot list or reopen previously exported studies. |
| **Server State** | `scripts/run_atlas.py` preloads terrain raster and waypoint catalog into memory. | Server handles transient POSTs for `/api/plan_route`, `/api/gauntlet`, etc., but has no REST endpoints for missions or experiments. |
| **HTTP Routing** | Handled via `SimpleHTTPRequestHandler` in `MarsWalkHTTPRequestHandler`. | Only supports GET and POST on fixed endpoints. Does not support PUT, DELETE, or dynamic URL segments. |

---

## 3. Mission Fingerprinting & Reproducibility Assessment

In `src/marswalk/api/contracts.py`:
- `compute_input_fingerprint()` computes a canonical SHA-256 hash incorporating:
  - Terrain dataset identity (`dataset_id`: `USGS_CTX_DTM_JEZERO_20M`)
  - Departure grid coordinate `[row, col]`
  - Destination grid coordinate `[row, col]`
  - Intermediate stops `[(row, col, id, priority_score, dwell_time_s), ...]`
  - Route profile (`conservative`, `balanced`, `science_first`)
  - Vehicle mode (`crew_eva`, `robotic_rover`)
  - Speed multiplier and optional distance/duration budget constraints.
- **Evaluation:** The fingerprinting algorithm is deterministic, insensitive to dictionary key ordering, and excludes ephemeral UI properties. It provides the exact mathematical foundation needed to verify whether a stored historical experiment matches the current mission workspace.

---

## 4. Test Suite Baseline Execution

The full test suite was executed prior to any modifications:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.4, pytest-9.1.1, pluggy-1.7.0
rootdir: E:\Python\NASA-Spaceapps\Marswalk
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.15.1
collected 171 items

tests\test_api_routing.py ..............                                 [  8%]
tests\test_app.py ..............                                         [ 16%]
tests\test_export_mission_assets.py .                                    [ 16%]
tests\test_ingest.py .....                                               [ 19%]
tests\test_milestone_8a_smoke.py .....                                   [ 22%]
tests\test_milestone_9d.py .....                                         [ 25%]
tests\test_milestone_9e.py .......                                       [ 29%]
tests\test_milestone_9f.py ....                                          [ 32%]
tests\test_milestone_9g.py ......                                        [ 35%]
tests\test_milestone_9h.py ...........                                   [ 42%]
tests\test_milestone_9i.py .......                                       [ 46%]
tests\test_milestone_9j_contracts.py ....................                [ 57%]
tests\test_place_catalog.py .....                                        [ 60%]
tests\test_planner.py ..............                                     [ 69%]
tests\test_preferences.py ...............                                [ 77%]
tests\test_science_budget.py ...............                             [ 86%]
tests\test_stress_test.py .............                                  [ 94%]
tests\test_terrain.py ..........                                         [100%]

============================ 171 passed in 43.68s =============================
```
**Baseline Result:** 171 passed, 0 failed, 0 skipped.

---

## 5. Architectural Requirements for Milestone 9K

1. **Dedicated Workspace Directories:**
   - Missions: `data/workspaces/missions/`
   - Experiments: `data/workspaces/experiments/`
2. **Atomic Durability:**
   - Write via temporary files (`.tmp`) and atomic `os.replace` to prevent corrupted records on power loss or aborts.
3. **Draft 2020-12 Storage Schemas:**
   - `saved-mission.schema.json`
   - `saved-experiment.schema.json`
   - `experiment-comparison.schema.json`
4. **RESTful Workspace API:**
   - Support `GET`, `POST`, `PUT`, `DELETE` with path segment parsing (`/api/missions/{id}`, `/api/experiments/{id}`).
   - Path traversal protection (strict slug/UUID validation, prohibiting `..`, `/`, `\`).
5. **Historical vs Current Integrity:**
   - Clear lifecycle classification: `historical_result`, `reproducible`, `recalculation_required`, `stale_incompatible`, `failed`.
   - Never mutate historical records during replay or comparison; assign new run IDs.
6. **Isolated Test Fixtures:**
   - Use `tmp_path` fixtures in tests so test executions never pollute or wipe user workspace files.
