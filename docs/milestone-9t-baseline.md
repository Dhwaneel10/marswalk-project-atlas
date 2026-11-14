# MarsWalk 2.0 — Milestone 9T Reconnaissance & Baseline Audit

**Audit Date:** 2026-10-18  
**Auditor Roles:** Principal Aerospace Software Engineer, Mission Operations Analyst, Scientific Data Provenance Auditor, and NASA Space Apps Challenge Demo Lead  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  

---

## 1. Verified Baseline State

- **Automated Test Suite:** **263 tests passing** across 27 test modules in **99.95s** (0 failed, 0 skipped, 0 warnings).
- **Preflight Diagnostics:** **12/12 checkpoints green** in **541.8ms** against live HTTP server on port 3000 (`scripts/preflight_check.py`).
- **Active Server Daemon:** `http://127.0.0.1:3000` (PID / daemon active, responding with HTTP 200).
- **User Library Records:** Strictly intact and preserved:
  - `data/workspaces/missions/`: 7 saved mission records.
  - `data/workspaces/experiments/`: 11 saved experiment records.
- **Git Working Tree:** Changes uncommitted from 9S verification, no unrelated files touched.

---

## 2. Capabilities & Codebase Inventory

### 2.1 Existing Data Contracts & Schemas (`schemas/api/v1/`)
- `route-result.schema.json`: Canonical representation of computed traverse path, terrain metrics, operational timeline, legs, and feasibility.
- `mission-snapshot.schema.json`: Canonical snapshot of mission parameters, ordered points, stop IDs, terrain dataset reference, and input fingerprint.
- `saved-experiment.schema.json`: Encapsulates baseline route, sensitivity sweep, scenarios evaluated, and trade-off results.
- `mission-briefing-export.schema.json`: Technical briefing containing metadata, mission snapshot, baseline route, scenario comparisons, recovery plans, and provenance.
- `experiment-comparison-response.schema.json`: Side-by-side trade-off deltas.

### 2.2 Existing Export Endpoints
- `POST /api/export_briefing` (`src/marswalk/api/service.py`):
  - Returns `{ "json_export": dict, "markdown_briefing": str, "timestamp": str }`.
  - Frontend downloads individual `.json` or `.md` files via browser `Blob` and `a.download`.
  - **Limitation for Milestone 9T:** Currently exports either loose JSON or Markdown, but not a unified, downloadable "Mission Decision Pack" (ZIP archive containing canonical `mission_bundle.json`, `mission_brief.md`, `comparison.csv`, `README.txt`, and cartographic geometry `route.json`).

### 2.3 Existing Replay & Fingerprinting
- `compute_input_fingerprint` in `src/marswalk/api/contracts.py`:
  - Computes SHA-256 hash of canonical mission input: dataset ID, start/goal, stops (sorted if `optimize_stops` is True), profile, vehicle mode, speed multiplier, max distance/duration limits.
  - **Limitation for Milestone 9T:** Does not yet incorporate custom contingency event definitions (types, coordinates, multipliers, durations) into a unified run bundle computation fingerprint.
- `replay_saved_experiment` in `src/marswalk/api/workspace.py`:
  - Re-executes historical experiment baseline and scenarios through the authoritative Python A* planner and persists a new run with `replayed_from_experiment_id`.
  - **Requirement for Milestone 9T:** Extend to support independent replay and 3-stage outcome verification of exported mission bundles:
    1. **Integrity valid** (schema check, valid coordinates, valid float bounds).
    2. **Replay compatible** (terrain dataset ID match, raster bounds match).
    3. **Replay reproduced** (re-executed via authoritative engine, comparing route geometry, target retention, and metrics).

---

## 3. Milestone 9T Architecture Plan

1. **Canonical Mission Run Bundle (`src/marswalk/api/contracts.py` & `schemas/api/v1/mission-run-bundle.schema.json`):**
   - Define canonical `MissionRunBundle` schema Draft 2020-12.
   - Include SHA-256 hash of terrain artifact (`data/processed/jezero_ready_20m.tif`).
   - Define stable canonical computation fingerprint combining mission parameters, terrain SHA-256, and contingency events.
2. **Downloadable Mission Decision Pack (`POST /api/export_decision_pack`):**
   - Returns a single ZIP archive containing:
     - `mission_bundle.json`: Full canonical bundle.
     - `mission_brief.md`: Technical briefing.
     - `comparison.csv`: CSV table of baseline vs scenario metrics.
     - `README.txt`: Inspection instructions, input fingerprint, provenance, disclosures.
     - `route.json`: Cartographic coordinates and elevation profile.
3. **Independent Replay & Integrity Verification Service (`POST /api/verify_bundle` & `POST /api/replay_bundle`):**
   - Dissect outcomes: `is_integrity_valid`, `is_replay_compatible`, `is_reproduced`.
   - Never mutate archived historical data; generate distinct replay records.
4. **Frontend Integration (`web/app.js` & `web/index.html`):**
   - Add "Download Decision Pack (.zip)" button with clear run identification and stale invalidation.
5. **Testing & Handoff:**
   - Dedicated suite: `tests/test_milestone_9t_run_bundle.py`.
   - Re-verify full test suite and preflight diagnostics.
