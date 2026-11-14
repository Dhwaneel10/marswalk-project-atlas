# MarsWalk 2.0 — API Data Contract Specification (v1.0.0)
## Contract-First Planetary Mission Simulation, Route Intelligence, & Telemetry

**Specification Version:** 1.0.0  
**JSON Schema Standard:** Draft 2020-12  
**Base Schema Location:** `schemas/api/v1/`  
**Target Environment:** NASA Mars 2020 Mission (Jezero Crater 20 m CTX Digital Elevation Grid)  

---

## 1. Architectural Principles

MarsWalk 2.0 enforces a **Contract-First Architecture** across all components:
1. **Single Source of Truth:** Route geometry, effort calculations, operational timelines, and risk assessments are computed authoritatively by the Python backend. The browser UI and export systems consume and visualize this state without recalculating or scraping formatted strings.
2. **Deterministic Reproducibility:** Every calculated mission is tagged with an immutable `input_fingerprint` computed deterministically from all result-affecting input parameters. Alternate scenario simulations and technical briefings must reference this exact fingerprint.
3. **Transparent Scientific Disclosures:** Mathematical approximations (such as 2-Opt TSP heuristic for $k > 7$ stops) and operational models (such as Apollo lunar walking speed as an analogue) are embedded directly within response contracts.
4. **RFC 8259 JSON Compliance:** No non-standard numerical values (`NaN`, `Infinity`, `-Infinity`) may be serialized. Unreachable or undefined values are explicitly represented as `null` and documented.
5. **Fail-Closed Validation:** Invalid coordinates, unsupported profiles, duplicate stop identifiers, or out-of-bounds requests are rejected with structured machine-readable error envelopes before invoking routing algorithms.

---

## 2. Canonical Contracts Inventory

| Schema Identifier | File Path | Method & Endpoint | Description |
| :--- | :--- | :--- | :--- |
| `mission-request` | `schemas/api/v1/mission-request.schema.json` | `POST /api/plan_route` | Canonical input payload for point-to-point and multi-stop traverse planning. |
| `mission-snapshot` | `schemas/api/v1/mission-snapshot.schema.json` | Internal / Export | Immutable record of result-affecting inputs and SHA-256 fingerprint. |
| `route-result` | `schemas/api/v1/route-result.schema.json` | `POST /api/plan_route` Response | Canonical output containing connected geometry, metrics, timeline, and feasibility. |
| `scenario-comparison-request` | `schemas/api/v1/scenario-comparison-request.schema.json` | `POST /api/scenario_comparison` | Batch request for multi-scenario disruption simulation. |
| `scenario-comparison-response` | `schemas/api/v1/scenario-comparison-response.schema.json` | `POST /api/scenario_comparison` Response | Side-by-side comparison matrix with safe zero-baseline deltas and recovery options. |
| `scenario-sensitivity-request` | `schemas/api/v1/scenario-sensitivity-request.schema.json` | `POST /api/scenario_sensitivity` | Parameter sweep request ($\le 8$ discrete severity steps). |
| `scenario-sensitivity-response` | `schemas/api/v1/scenario-sensitivity-response.schema.json` | `POST /api/scenario_sensitivity` Response | Parameter sweep progression records with what-if disclaimers. |
| `mission-briefing-export` | `schemas/api/v1/mission-briefing-export.schema.json` | `POST /api/export_briefing` | Machine-readable archival bundle and publication-ready Markdown briefing. |
| `api-error` | `schemas/api/v1/api-error.schema.json` | HTTP 4xx / 5xx | Structured machine-readable error payload with retry guidance. |

---

## 3. Detailed Data Model Specifications

### 3.1 Canonical Mission Request (`mission-request.schema.json`)
The canonical mission request normalizes all departure, stop, destination, profile, and constraint definitions.

```json
{
  "schema_version": "1.0.0",
  "mission_id": "mission_jezero_alpha",
  "start": { "row": 117, "col": 157, "name": "Octavia E. Butler Landing" },
  "goal": { "row": 194, "col": 131, "name": "Kodiak Butte Outlier" },
  "stops": [
    { "id": "three_forks", "name": "Three Forks Sample Depot", "row": 153, "col": 123, "priority_score": 75.0 }
  ],
  "profile": "conservative",
  "vehicle_mode": "crew_eva",
  "mission_constraints": {
    "max_distance_m": 5000.0,
    "dwell_time_per_stop_s": 900.0,
    "speed_multiplier": 1.0
  },
  "route_options": {
    "optimize_stops": false,
    "science_appetite_gamma": 1.0
  }
}
```

#### Field Invariants:
- `start` and `goal`: Coordinates must be integers within grid dimensions: $0 \le \text{row} < 250$, $0 \le \text{col} < 250$. Neither point may fall on invalid NoData or cliff barriers (`invalid_mask == True`).
- `start` and `goal` coordinates cannot be identical ($\text{Start} \neq \text{Goal}$).
- `stops`: Maximum 12 intermediate targets. Each stop must have a unique `id` within the request. No stop may duplicate `start` or `goal`.
- `profile`: Strict enum: `"conservative"`, `"balanced"`, `"science_first"`.
- `vehicle_mode`: Strict enum: `"crew_eva"` ($2.0\text{ km/h}$, $8\text{h}$ limit), `"robotic_rover"` ($0.035\text{ m/s}$, $4\text{h}$ window).

---

### 3.2 Deterministic Mission Fingerprint & Snapshot (`mission-snapshot.schema.json`)
The input fingerprint provides cryptographic provenance and detects stale simulation results:

$$\text{CanonicalString} = \text{JSON}(\{ \text{start}, \text{goal}, \text{stops}, \text{profile}, \text{vehicle\_mode}, \text{constraints}, \text{dataset\_id} \}, \text{sort\_keys}=\text{True})$$

$$\text{input\_fingerprint} = \text{SHA256}(\text{CanonicalString})[:16]$$

#### Fingerprint Rules:
- Timestamps, client formatting, and request UUIDs are **strictly excluded** from the fingerprint calculation.
- Any change in coordinates, stop order, profile, vehicle mode, speed multiplier, or terrain dataset version produces a distinct fingerprint.
- Comparison results, sensitivity sweeps, and exported briefings must carry the `baseline_fingerprint` matching the active baseline. If the active mission inputs change, the previous results are invalidated as stale.

---

### 3.3 Canonical Route Result Contract (`route-result.schema.json`)
Defines the authoritative geometry, metrics, timeline, and scientific feasibility of a planned traverse.

#### Route Metrics Definitions:
- `ground_distance_m` (Unit: metres): Physical distance along the grid. Diagonal steps are computed at $20.0 \times \sqrt{2} \approx 28.284\text{ m}$; cardinal steps at $20.0\text{ m}$.
- `terrain_cost_flat_m` (Unit: $\text{flat-m}$): Terrain-adjusted cost equivalent to walking across flat ground with zero slope penalty and nominal regolith friction:
  $$\text{Cost} = \sum_{\text{steps}} \text{step\_dist} \times \left(1.0 + \left(\frac{\tan\theta}{\tan 15^\circ}\right)^2\right) \times \mu_{\text{friction}}$$
- `active_traverse_time_s` (Unit: seconds): Total in-motion transit duration computed cell-by-cell using the operational velocity model and slope impedance.
- `total_mission_time_s` (Unit: seconds): Active traverse time + dwell time ($\sum \text{Dwell}$) + operational scenario holds.
- `travel_time_range_s`: Operational uncertainty envelope ($\pm 15\%$ to $\pm 25\%$) reflecting terrain surface roughness and astronaut suit fatigue.
- `path_rc`: Ordered array of integer pairs $[[\text{row}, \text{col}], ...]$. Every transition between adjacent cells must be cardinal or diagonal ($\Delta r, \Delta c \in \{-1, 0, 1\}$, $|dr| + |dc| > 0$).

---

### 3.4 Scenario Comparison Contract (`scenario-comparison-response.schema.json`)
Evaluates alternate futures against an identical baseline mission.

#### Safe Delta Formulation:
- Absolute distance delta:
  $$\Delta d = d_{\text{scenario}} - d_{\text{baseline}}$$
- Percentage distance change:
  $$\Delta d\% = \begin{cases} 
  100 \times \frac{d_{\text{scenario}} - d_{\text{baseline}}}{d_{\text{baseline}}}, & d_{\text{baseline}} > 0 \text{ and reachable} \\
  \text{null}, & d_{\text{baseline}} = 0 \text{ or unreachable}
  \end{cases}$$
- When a scenario is unreachable (`is_scenario_reachable == False`), `delta_distance_m` and `delta_cost` are serialized as `null` (UI displays `—`), rather than non-standard `NaN` or misleading `0.0`.

---

### 3.5 Scenario Sensitivity Sweep Contract (`scenario-sensitivity-response.schema.json`)
Evaluates up to 8 discrete severity values of a single parameter.
- Each evaluation record explicitly identifies the `parameter_value` that produced it.
- Failed or blocked evaluations preserve `is_reachable = False` and `distance_m = null`.
- Every response carries `disclaimer: "WHAT-IF SENSITIVITY EXPERIMENT. Not an operational risk forecast."`.

---

### 3.6 Mission Briefing Export Contract (`mission-briefing-export.schema.json`)
The exported briefing bundles:
- `mission_snapshot`: Complete input snapshot and `input_fingerprint`.
- `baseline_route`: Canonical baseline route result.
- `scenario_comparison`: Comparison matrix (matching `baseline_fingerprint`).
- `sensitivity_analysis`: Parameter sweep records (matching `baseline_fingerprint`).
- `recovery_plan`: Applied recovery strategy.
- `engineering_assumptions`: Full classification ledger.
- `data_provenance`: USGS CTX DTM 20 m metadata.

---

### 3.7 Structured API Error Contract (`api-error.schema.json`)
All API errors return standard HTTP status codes (400, 404, 422, 500, 503) and a unified JSON error envelope:

```json
{
  "schema_version": "1.0.0",
  "error_code": "ERR_NO_DATA_BARRIER",
  "message": "Start pixel (10, 10) falls on invalid NoData or cliff hazard barrier",
  "status_code": 422,
  "details": [
    {
      "field": "start",
      "issue": "pixel falls on NoData barrier",
      "value": { "row": 10, "col": 10 }
    }
  ],
  "is_retryable": false,
  "timestamp": "2026-10-18T12:00:00Z"
}
```

#### Standard Error Codes:
- `ERR_MALFORMED_JSON`: Request body is not valid JSON.
- `ERR_VALIDATION_FAILED`: Request payload violates schema structure.
- `ERR_MISSING_REQUIRED_FIELD`: Missing `start`, `goal`, or parameter name.
- `ERR_ENDPOINT_OUT_OF_BOUNDS`: Coordinates fall outside terrain grid boundaries.
- `ERR_NO_DATA_BARRIER`: Coordinate maps to an unnavigable NoData or cliff barrier.
- `ERR_DUPLICATE_STOPS`: Intermediate stop IDs or coordinates are duplicated.
- `ERR_UNSUPPORTED_PROFILE`: Profile not in `{"conservative", "balanced", "science_first"}`.
- `ERR_UNSUPPORTED_VEHICLE_MODE`: Mode not in `{"crew_eva", "robotic_rover"}`.
- `ERR_UNREACHABLE_TRAVERSE`: Destination is physically unreachable across terrain.
- `ERR_STALE_SIMULATION`: Simulation results mismatch current mission fingerprint.
- `ERR_TERRAIN_UNAVAILABLE`: Jezero CTX elevation grid not loaded on server.
- `ERR_NOT_FOUND`: HTTP endpoint not found.
- `ERR_INTERNAL_ROUTING`: Unhandled internal exception during A* execution.

---

## 4. Contract Invariants & Verification Checklist

1. [x] **Geometry Connectivity:** All path cells are 8-connected neighbors.
2. [x] **Grid Confinement:** All coordinates satisfy $0 \le r < 250, 0 \le c < 250$.
3. [x] **Obstacle Exclusion:** In a scenario with `blocked_cells`, no blocked cell appears in the computed route path.
4. [x] **Sequence Fidelity:** Multi-stop paths visit intermediate targets in declared sequence.
5. [x] **RFC 8259 Compliance:** Zero `NaN` or `Infinity` values serialized in any JSON response.
6. [x] **Safe Deltas:** Undefined percentage changes serialize as `null` with UI rendering `—`.
7. [x] **Fingerprint Consistency:** Scenario comparisons and briefings cross-validate against baseline fingerprint.
