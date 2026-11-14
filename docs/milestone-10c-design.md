# MarsWalk 2.0 — Milestone 10C Design Document
## Sortie Black Box & Incident Replay

### 1. Executive Summary

Milestone 10C establishes an auditable, append-only **Sortie Black Box and Incident Replay** system for MarsWalk 2.0. Every operational phase transition, departure milestone, intermediate target arrival, simulated contingency injection, route recalculation, and adaptive continuation handoff is deterministically recorded into an immutable, schema-validated JSON ledger.

A flight director, operations researcher, or visualization specialist can open the interactive Sortie Black Box interface at any time to:
1. Review the chronological stream of mission events filtered by operational category (`Navigation`, `Science`, `Contingency`, `Decisions`).
2. Inspect individual event telemetry, planetocentric coordinates, USGS CTX digital elevation samples, and payload provenance.
3. Trigger an authentic **Incident Replay**, which reconstructs the mid-sortie contingency from the ledger, re-evaluates the optimal continuation using current pathfinding algorithms across authentic 20 m CTX terrain, and calculates decision fidelity metrics comparing historical decisions against recomputed solutions.

Crucially, MarsWalk 2.0 strictly preserves scientific truthfulness:
- Recorded facts from the sortie ledger are explicitly distinguished from recomputed algorithmic estimates.
- All simulated emergencies are branded with the mandatory `[SIMULATED CONTINGENCY]` badge.
- Historical saved missions (7) and historical experiment runs (11) remain immutable and protected from alteration.

---

### 2. Architecture & Data Model

#### 2.1 The `MissionEvent` Specification

Every entry in the Sortie Black Box is represented by an immutable `MissionEvent` dataclass conforming to the Draft 2020-12 JSON Schema (`schemas/api/v1/mission-event.schema.json`):

| Field | Type | Description |
|---|---|---|
| `schema_version` | `str` | Fixed contract version (`"1.0.0"`). |
| `event_id` | `str` | Unique, random event identifier (`evt_[a-zA-Z0-9_-]{1,64}`). |
| `source_mission_id` | `str` | Root mission identifier to which the sortie ledger belongs. |
| `continuation_id` | `Optional[str]` | Optional identifier if event occurred on an adaptive continuation branch. |
| `event_type` | `str` | Standardized lifecycle event enum (e.g., `sortie_started`, `contingency_injected`, `route_recalculated`, `continuation_selected`). |
| `mission_time_s` | `float` | Continuous sortie mission elapsed time in seconds ($\ge 0$). |
| `playback_elapsed_s` | `float` | Active playback scrubber elapsed time in seconds ($\ge 0$). |
| `recorded_at_utc` | `str` | ISO 8601 UTC timestamp of event creation. |
| `route_variant` | `str` | Active route variant (`"nominal"`, `"disrupted"`, `"adaptive"`, `"continuation"`). |
| `rover_rc` | `Optional[Tuple[int, int]]` | Grid row and column $[r, c]$ on the 250×250 Jezero CTX DTM. |
| `rover_float_rc` | `Optional[Tuple[float, float]]` | Subcell floating-point coordinates. |
| `elevation_m` | `Optional[float]` | Authentic USGS CTX terrain elevation in meters datum. |
| `slope_deg` | `Optional[float]` | Local terrain slope angle in degrees. |
| `speed_m_s` | `Optional[float]` | Instantaneous rover velocity in meters per second. |
| `payload` | `Dict[str, Any]` | Detailed event payload (parameters, category, descriptions). |
| `provenance` | `Dict[str, Any]` | Provenance metadata (`source`, `is_recomputed`, `algorithm_version`). |

#### 2.2 Append-Only Atomic Ledger Storage

Ledgers are persisted to `data/workspaces/events/<source_mission_id>_events.json`:
- **Atomic Persistence**: File updates are written to an isolated temporary file in the same directory and renamed atomically (`os.replace`) to prevent corrupt states during abrupt server shutdowns.
- **Idempotent Deduplication**: If an event with an identical `event_id` is re-submitted (e.g., via network retry), it is deduplicated without duplicating records.
- **Deterministic Chronology**: All events are deterministically sorted by `(mission_time_s, recorded_at_utc, event_id)` upon retrieval.
- **Security Boundaries**: Path traversal patterns (such as `../` or `..\`) in mission IDs are strictly validated against regex `^[a-zA-Z0-9_-]{3,64}$` and rejected with HTTP 400.

---

### 3. Incident Replay & Decision Fidelity Engine

When a contingency occurs mid-sortie, operations controllers need to verify whether the system's recommended response was optimal, reproducible, and compliant with terrain constraints.

#### 3.1 Timeline Reconstruction

The `reconstruct_incident_timeline` module parses the event ledger into distinct mission phases:
- Departure Phase ($t = 0$)
- Traverse Legs & Intermediate Stops
- Incident Ingestion Point ($t = t_{\text{int}}$)
- Evaluated Continuation Options & Selected Action

#### 3.2 Algorithmic Recomputation & Variance Metrics

The `replay_incident` engine retrieves the recorded contingency parameters from `contingency_injected` and the vehicle state snapshot ($[r, c], z, \theta_{\text{slope}}, T_{\text{rem}}$), and executes a fresh A* pathfinding evaluation over the authentic 20 m Jezero CTX DTM:

$$\Delta D = |D_{\text{recomputed}} - D_{\text{recorded}}|$$
$$\Delta T = |T_{\text{recomputed}} - T_{\text{recorded}}|$$
$$\text{Geometry Match} = (\text{Path}_{\text{recomputed}} == \text{Path}_{\text{recorded}})$$

If $\Delta D < 1.0\text{ m}$ and geometry matches, the replay confirms 100% mathematical fidelity. If terrain conditions or planning weights differ, variance metrics clearly communicate discrepancies to the operator.

---

### 4. API Endpoints

1. **`POST /api/mission/events`**:
   - Accepts single event (`{"event": {...}}`) or batch (`{"events": [...]}`).
   - Validates each event against `schemas/api/v1/mission-event.schema.json`.
   - Returns `{ "status": "success", "recorded_count": N, "events": [...] }`.

2. **`GET /api/mission/events`**:
   - Query parameters: `source_mission_id` (or `mission_id`), `event_type`, `category`, `since_time_s`.
   - Returns sorted list of events and total count.

3. **`POST /api/mission/incident/replay`**:
   - Request body: `{ "mission_id": "...", "recompute": true }`.
   - Validates response against `schemas/api/v1/incident-replay-response.schema.json`.
   - Returns `{ "status": "success", "timeline_summary": {...}, "reconstructed_sortie": {...}, "fidelity": {...}, "disclosures": {...} }`.

---

### 5. Frontend Sortie Black Box Modal

- **Access Point**: Direct CTA button in the 3D HUD playback toolbar (`#btnOpenBlackBoxModal`).
- **Two-Column Audit Workstation**:
  - **Left Column**: Interactive chronological timeline with quick-filter pills (`ALL`, `NAVIGATION`, `SCIENCE`, `CONTINGENCY`, `DECISIONS`). Clicking an event selects it and highlights its border.
  - **Right Column Top**: Replay Summary Card displaying:
    - Sortie status (`NOMINAL SORTIE` vs `INCIDENT VERIFIED`).
    - Side-by-side comparison of `Recorded Decision` vs `Recomputed Decision`.
    - Real-time variance readouts ($\Delta D$, $\Delta T$, `MATCH` vs `DEVIATION`).
  - **Right Column Bottom**: Live JSON payload and provenance inspector (`#bbDetailJson`), displaying exact timestamps, planetary coordinates, and algorithm parameters.
