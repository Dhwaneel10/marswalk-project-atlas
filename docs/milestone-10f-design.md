# MarsWalk 2.0 — Milestone 10F: Mission Readiness & Decision Gate
## Technical Architecture & Engineering Design Specification

### 1. Overview & Objective
Milestone 10F establishes a comprehensive **Mission Readiness & Decision Gate** engine and decision-support dashboard for MarsWalk 2.0 / Project Atlas. Rather than serving as an autonomous flight authority or flight-certified clearance system, this engine provides a unified planning-assurance interface that consolidates:
1. **Mission Feasibility:** Endpoint coordinates within terrain boundaries, destination reachability, traverse duration compliance against life-support/mission duration budgets, and slope limit checks.
2. **Environmental Data Readiness:** Telemetry freshness, distinction between in-situ station observations (Perseverance MEDA, Curiosity REMS) and climatological model simulations (MCD v6.1), landing site spatial compatibility, and explicit handling of missing telemetry without zero-filling.
3. **Robustness & Contingency Coverage:** Verification of simulated disruptions across standard classes (dust storms, rockfalls, degraded mobility, communications blackout), explicit flagging of untested failure modes, identification of operational margin breakpoints, and tight margin alerts.
4. **Data Provenance & Reproducibility:** Input parameter fingerprinting, USGS CTX 20m DTM dataset SHA-256 verification, validation against mission event ledgers, and distinction between cached and actively recomputed trajectory plans.

---

### 2. Architecture & Data Flow

```
+---------------------------------------------------------------------------------------------------+
|                                  MARSWALK 2.0 DATA PLATFORM                                       |
|                                                                                                   |
|  [Mission Plans]           [Weather Engine]         [Sortie Black Box]    [Robustness Evaluator]  |
|  - Start / Goal / Stops    - Current Station/Model  - Chronological Logs  - Disruption Gauntlet   |
|  - Vehicle Envelope        - Sol / Timestamp        - Event Injections    - Margin Breakpoints    |
|  - Budget Constraints      - Telemetry Integrity    - Continuations       - Failure Classes       |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
|                      MISSION READINESS ENGINE (mission_readiness.py)                              |
|                                                                                                   |
|  1. Stable Assessment ID Generation (mra_<slug>_<uid>)                                            |
|  2. Feasibility Gate: Coordinate validation, path reachability, duration budget analysis         |
|  3. Environmental Gate: In-situ vs Climatology, Site mismatch, Telemetry freshness & completeness |
|  4. Robustness Gate: Tested vs Untested scenario matrix, Breakpoint & Margin evaluation           |
|  5. Provenance Gate: Terrain SHA-256 hash, Input fingerprint, Ledger correlation                  |
|  6. Deterministic Readiness Scoring (0-100) with Blocker & Incomplete Caps                        |
|  7. Contract Validation: schemas/api/v1/mission-readiness-assessment.schema.json                  |
+---------------------------------------------------------------------------------------------------+
                                                  │
                        ┌─────────────────────────┴─────────────────────────┐
                        ▼                                                   ▼
+-----------------------------------------------+   +-----------------------------------------------+
|      ATLAS WORKSTATION READINESS DASHBOARD    |   |           ATLAS HTTP API ENDPOINTS            |
|  - Header Access Button (#btnHeaderReadiness) |   |  - POST /api/mission/readiness (Evaluate)     |
|  - Executive Decision Gate Banner & Score     |   |  - GET  /api/mission/readiness/list (History) |
|  - 4 Category Summary Status Tiles            |   |  - GET  /api/mission/readiness/<id> (Detail)  |
|  - Category & Severity Filter Pills           |   |  - Machine-Readable JSON Export               |
|  - Findings Accordion with Evidence Refs      |   |  - Research Prototype Safety Disclaimers      |
+-----------------------------------------------+   +-----------------------------------------------+
```

---

### 3. Readiness Status Model & Deterministic Scoring

The decision gate classifies mission readiness into four mutually exclusive operational statuses:

| Status | Definition | Transition Criteria |
| :--- | :--- | :--- |
| `BLOCKED` | Mission cannot proceed; fundamental violations detected. | Any `blocker` finding present (e.g. unreachable destination, coordinate out-of-bounds, duration budget exceeded). |
| `INCOMPLETE` | Route trajectory or core mission parameters have not been computed. | Route uncomputed (`is_computed: false`) or start/goal coordinates missing. |
| `CONDITIONAL` | Feasible and reachable, but operating with cautionary risks or unverified dimensions. | No blockers, but contains `warning` or `untested` findings (e.g. weather site mismatch, climatological model fallback, untested disruption gauntlet, tight margins). |
| `READY_FOR_REVIEW` | All feasibility checks verified, in-situ weather confirmed, robustness thoroughly tested. | Zero blockers, zero warnings, zero untested categories, full disruption coverage. |

#### Deterministic Scoring Algorithm:
- **Baseline:** Starts at 100 points.
- **Deductions:**
  - Each `blocker` severity finding: -40 points.
  - Each `warning` severity finding: -15 points.
  - Each `untested` scenario/dimension: -5 points.
  - Each `info` finding: 0 points.
- **Score Floors & Caps:**
  - Minimum score: 0; Maximum score: 100.
  - If status is `INCOMPLETE`: Score is capped at `min(score, 40)`.
  - If status is `BLOCKED`: Score is capped at `min(score, 25)`.

---

### 4. Structured Finding Contract

Every finding generated by the readiness engine adheres to the following specification:
- `finding_code`: Unique uppercase snake_case identifier (e.g. `ROUTE_NOT_COMPUTED`, `BUDGET_EXCEEDED`, `WEATHER_SITE_MISMATCH`, `ROBUSTNESS_UNTESTED`, `ROBUSTNESS_BREAKPOINT_FOUND`, `MARGIN_TIGHT`).
- `category`: One of `"feasibility"`, `"environmental"`, `"robustness"`, `"provenance"`.
- `severity`: One of `"blocker"`, `"warning"`, `"info"`, `"untested"`.
- `title`: Concise human-readable finding summary.
- `description`: Detailed scientific/engineering explanation.
- `is_blocking`: Boolean flag indicating whether this finding forces `BLOCKED` status.
- `evidence_references`: Array of strings citing concrete telemetry, file hashes, waypoint IDs, or metrics.
- `recommended_action`: Actionable guidance for mission planners to mitigate the finding.

---

### 5. Schema Specification (`schemas/api/v1/mission-readiness-assessment.schema.json`)

The assessment output is strictly validated against JSON Schema Draft 2020-12, containing:
- `assessment_id`: Pattern `^mra_[a-zA-Z0-9_-]{3,64}$`.
- `evaluated_at_utc`: RFC 3339 timestamp.
- `mission_id` & `mission_name`: Mission identifiers.
- `readiness_status`: `"READY_FOR_REVIEW"`, `"CONDITIONAL"`, `"INCOMPLETE"`, `"BLOCKED"`.
- `overall_score`: Integer between 0 and 100.
- `summary`: High-level executive synthesis.
- `categories`: Summary breakdown of the 4 categories (`status`, `findings_count`, `blockers_count`, `warnings_count`).
- `findings`: Array of validated finding objects.
- `reproducibility_manifest`: Dataset ID, terrain SHA-256, model version, software version, input fingerprint.
- `operational_disclaimer`: Prominent disclaimer distinguishing simulation research from certified flight-readiness.
