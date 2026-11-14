# MarsWalk 2.0 — Milestone 9T Architectural Design
## Canonical Mission Run Bundle, Decision Pack Packaging & Independent Replay Engine

**Document Version:** 1.0.0  
**Milestone:** 9T (Decision-Grade Mission Briefing, Reproducibility & Competition Evidence)  
**Status:** Approved & Implemented  
**Author:** Principal Aerospace Software Engineer, Scientific Computing Auditor & Verification Lead  
**Target Environment:** NASA Space Apps Challenge 2026 / IAU Mars 2000 Planetocentric Reference System  

---

## 1. Executive Summary & Design Directive

Milestone 9T transforms MarsWalk 2.0 from an interactive exploration tool into a **decision-grade, auditable, and independently reproducible mission demonstration platform**.

In competition presentations, aerospace reviews, and scientific evaluations, reviewers must not be required to accept simulation outputs on faith. Milestone 9T implements:
1. **Canonical Mission Run Bundle Specification** (`schemas/api/v1/mission-run-bundle.schema.json`): A complete, self-contained, schema-validated snapshot of all planning inputs, authoritative baseline route geometry, contingency disruptions, comparison deltas, terrain raster hash, and scientific disclosures.
2. **Deterministic Computation Fingerprint**: A stable SHA-256 hash incorporating all physical and operational inputs (start, goal, stops, priority, dwell, vehicle mode, velocity multiplier, corridor closures, deratings, terrain identity, and terrain SHA-256) while rigorously rejecting non-finite values (`NaN`, `inf`).
3. **In-Memory Decision Pack ZIP Generator** (`marswalk_decision_pack_<bundle_id>.zip`): Standard-library-based packaging creating an auditable archive containing 5 artifacts with safe relative filenames and zero directory traversal vulnerability.
4. **Three-Stage Independent Replay & Verification Service**:
   - *Stage 1: Integrity Audit* — Validates Draft 2020-12 schema, value bounds, finite coordinates.
   - *Stage 2: Replay Compatibility* — Checks terrain dataset ID and 256-bit raster hash against local topography.
   - *Stage 3: Deterministic Reproduction* — Re-executes authoritative A* and Gauntlet engines, asserting exact equality for path coordinates and targets, and floating tolerances within $\le 0.1\text{ m}$ distance and $\le 0.1\text{ s}$ duration.
5. **Zero-Mutation Guarantee**: Persistence of historical missions and saved experiments is strictly immutable; bundle replays persist only as distinct, new records tagged with reproduction lifecycle state.

---

## 2. Architecture & Data Flow

```
+----------------------------------------------------------------------------------------------------+
|                                      BROWSER CLIENT (Atlas 3D UI)                                  |
|                                                                                                    |
|   +-----------------------+     +--------------------------+     +-------------------------------+ |
|   | Baseline A* Planner   |     | Interactive Contingency  |     | One-Click Decision Pack (.zip)| |
|   | Start/Goal/Stops HUD  | --> | Designer (Rockfall/Hold) | --> | Download Trigger              | |
|   +-----------------------+     +--------------------------+     +-------------------------------+ |
+-----------------------------------------------|----------------------------------------------------+
                                                | HTTP POST /api/export_decision_pack
                                                v
+----------------------------------------------------------------------------------------------------+
|                                    ATLAS HTTP & API SERVICE                                        |
|                                                                                                    |
|   1. Canonical Bundle Builder:                                                                     |
|      - Extracts inputs, baseline route, scenario result, comparison deltas                         |
|      - Embeds terrain provenance: USGS_CTX_DTM_JEZERO_20M (SHA-256: 875e7e...)                     |
|      - Computes deterministic input fingerprint: SHA-256(canonical JSON)                          |
|      - Validates contract: schemas/api/v1/mission-run-bundle.schema.json                           |
|                                                                                                    |
|   2. Decision Pack Artifacts Generation:                                                           |
|      - mission_brief.md      : Executive narrative, trade-offs, disclosures                        |
|      - comparison.csv        : RFC 4180 audit metrics (Distance, Duration, Schedule, Feasibility)  |
|      - route.json            : 3D cartographic coordinates, elevation profile, climb, steps        |
|      - mission_bundle.json   : Complete canonical run record                                       |
|      - README.txt            : Package manifest, verification instructions, citation ledger        |
|                                                                                                    |
|   3. Safe In-Memory ZIP Packager (zipfile + io.BytesIO):                                           |
|      - Streams binary archive (Content-Type: application/zip) with attachment header               |
+----------------------------------------------------------------------------------------------------+
                                                |
                 +------------------------------+-------------------------------+
                 |                                                              |
                 v HTTP POST /api/bundle/verify                                 v HTTP POST /api/bundle/replay
+----------------------------------------------------+   +----------------------------------------------------+
|            STAGE 1 & 2: INTEGRITY AUDIT            |   |           STAGE 3: REPLAY ENGINE                   |
|                                                    |   |                                                    |
| - Draft 2020-12 Schema Validation                  |   | - Re-runs A* with Minetti cost model               |
| - Value sanity (rejects NaN, Inf, out-of-bounds)   |   | - Re-evaluates custom contingency disruptions      |
| - Recomputes input SHA-256 fingerprint             |   | - Asserts exact coordinate equality                |
| - Matches recorded vs computed fingerprint         |   | - Asserts tolerance: distance <= 0.1m, time <= 0.1s|
| - Verifies local USGS 20m DTM raster SHA-256       |   | - Persists new experiment replay record in library |
+----------------------------------------------------+   +----------------------------------------------------+
```

---

## 3. Canonical Mission Run Bundle Specification

### 3.1 Schema Conformance
The bundle contract is defined in `schemas/api/v1/mission-run-bundle.schema.json` under JSON Schema Draft 2020-12.

### 3.2 Required Top-Level Schema Properties
1. `schema_version`: Must strictly equal `"1.0.0"`.
2. `bundle_id`: Slug identifier conforming to `^[a-zA-Z0-9_-]{3,64}$`.
3. `created_at`: ISO 8601 UTC timestamp.
4. `computation_fingerprint`: 64-character lowercase hexadecimal string (SHA-256).
5. `baseline_fingerprint`: 64-character lowercase hexadecimal string of nominal inputs.
6. `mission_input`: Complete mission specifications (`start`, `goal`, `stops`, `profile`, `vehicle_mode`, `speed_multiplier`, `max_distance_m`, `operational_limit_s`).
7. `terrain_provenance`: Topographic dataset identity, dimensions, resolution, and raster SHA-256 hash.
8. `baseline_route`: Authoritative path geometry, cost, distance, timeline, and visited targets.
9. `reachability_and_feasibility`: Reachability status for baseline and scenario.
10. `engine_metadata`: Model version, assumptions version, algorithm name, and assumption ledger.
11. `disclosures`: Mandatory scientific and operational disclaimers.

---

## 4. Deterministic Computation Fingerprint Algorithm

### 4.1 Input Invariance Principles
To ensure exact replay reproducibility, the fingerprint computation ignores non-deterministic client state (timestamps, session IDs, UI flags) and captures only physical and algorithmic variables:

$$\text{Fingerprint} = \text{SHA-256}\Big(\text{JSON}_{\text{canonical}}\big(\mathcal{T}, \mathcal{P}, \mathcal{V}, \mathcal{S}, \mathcal{G}, \mathcal{W}, \mathcal{C}, \mathcal{E}\big)\Big)$$

Where:
- $\mathcal{T}$: Terrain identity (`USGS_CTX_DTM_JEZERO_20M`) and 256-bit raster hash (`875e7e...`).
- $\mathcal{P}$: Traversal strategy profile (`conservative`, `balanced`, `science_first`).
- $\mathcal{V}$: Vehicle mobility mode (`crew_eva`, `robotic_rover`).
- $\mathcal{S}, \mathcal{G}$: Integer grid coordinates for start and goal.
- $\mathcal{W}$: Intermediate science targets sorted canonically (or preserving order if fixed sequence).
- $\mathcal{C}$: Numerical operational constraints (maximum distance cap, operational duration limit, dwell time).
- $\mathcal{E}$: Normalized contingency events sorted by `(event_type, id, center_rc)`.

### 4.2 Numerical Sanitization & Finiteness Enforcement
Every floating-point parameter is inspected:
- NaN and $\pm\infty$ values immediately trigger `ValueError` or `ContractValidationError`.
- Floating-point parameters are rounded to canonical precision (distances: 2 decimals, durations: 1 decimal, multipliers: 4 decimals) to prevent machine-epsilon divergence across CPU architectures.

---

## 5. In-Memory Decision Pack ZIP Architecture

### 5.1 File Manifest
The ZIP package contains 5 self-contained, auditable files:
1. `mission_bundle.json`: The authoritative canonical run bundle conforming to schema.
2. `mission_brief.md`: Executive decision briefing with comparison table, trade-off analysis, and citations.
3. `comparison.csv`: Machine-readable tabular comparison adhering to RFC 4180.
4. `route.json`: 3D cartographic route breakdown (coordinates in local metres, step count, elevation, climb).
5. `README.txt`: Manifest, reproduction guide, command-line verification scripts, and scientific provenance.

### 5.2 Security & Path Safety
- Built completely in memory via `io.BytesIO` and Python standard library `zipfile`.
- Zero temporary disk files created during export.
- Filenames inside the archive are strictly relative and flat (no `/`, `\`, or `..` path traversals).
- Archive size is optimized (~11.5 KB uncompressed, ~2.5 KB compressed).

---

## 6. Independent Replay & Verification Engine

### 6.1 Verification Workflow (3 Stages)
```
[Uploaded / Exported Bundle]
         |
         v
+-----------------------------+
| Stage 1: Integrity Check    | ---> [Schema Valid? Coordinates Finite & In-Bounds? Fingerprint Matches?]
+-----------------------------+
         | PASS
         v
+-----------------------------+
| Stage 2: Compatibility Check| ---> [Terrain Dataset ID Matches? Terrain SHA-256 Raster Matches?]
+-----------------------------+
         | PASS
         v
+-----------------------------+
| Stage 3: Replay Recomputation| ---> [Re-run A* & Gauntlet Engine]
+-----------------------------+
         |
         +--> Exact Path Equality Check: rec_path == new_path
         +--> Exact Target Equality Check: rec_wps == new_wps
         +--> Metric Delta Check: |new_dist - rec_dist| <= 0.1 m
         +--> Duration Delta Check: |new_time - rec_time| <= 0.1 s
         |
         v
+-----------------------------+
| Persist Verified Replay     | ---> Saves distinct experiment record replay_<bundle_id>_<uuid>.json
+-----------------------------+
```

### 6.2 Immutability Contract
Under no circumstances does replay modify or overwrite existing historical experiments or saved missions. The engine writes a newly created experiment with `lifecycle_state: "reproducible"` or `"diverged"`, establishing an unbroken chain of custody.

---

## 7. Compliance with Project Directives

- **Primary Source Data:** Bound to USGS Context Camera 20m Jezero Crater DTM.
- **Traceable Attribution:** Explicitly cites Minetti et al. (2002) for metabolic cost, Apollo telemetry for Crew EVA speed, and MSL/M2020 telemetry for Robotic Rover speed.
- **Scientific Honesty:** Clear research prototype disclaimer in all exports; explicitly states modeled routes are not flight-certified.
- **Zero Hallucination:** Blocked scenarios truthfully report `is_scenario_reachable: false` and `CORRIDOR_SEVERED`, never inventing bypass paths.
