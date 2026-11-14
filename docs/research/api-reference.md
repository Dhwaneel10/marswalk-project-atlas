# Project Atlas: HTTP REST API Reference

**Document ID:** `ATLAS-DOC-API-001`  
**Classification:** Interface Specification  
**Default Base URL:** `http://127.0.0.1:3000`  
**Protocol:** HTTP/1.1 JSON (Draft 2020-12 Schema Validated)

---

## 1. System Health & Diagnostics

### `GET /api/health`
Returns the operational readiness status of the Atlas HTTP backend daemon.
- **Request:** None
- **Response `200 OK`:**
  ```json
  {
    "status": "healthy",
    "version": "2.0.0",
    "milestone": "13V",
    "planet": "Mars (IAU 2000)",
    "terrain_loaded": true,
    "dtm_resolution_m": 20.0
  }
  ```

---

## 2. Terrain Routing & Mission Optimization

### `POST /api/plan-route`
Calculates an optimal surface traversal path using terrain-constrained $A^*$ search on real CTX topography.
- **Request Body:**
  ```json
  {
    "start_coords": [18.4448, 77.4510],
    "goal_coords": [18.4520, 77.4350],
    "mode": "ROVER",
    "max_slope_deg": 15.0,
    "intermediate_stops": []
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "status": "SUCCESS",
    "total_distance_m": 1748.2,
    "travel_time_hours": 13.8,
    "max_slope_deg": 8.4,
    "climb_effort_joules": 184200.0,
    "waypoints_count": 84,
    "path_coordinates": [[18.4448, 77.4510, -2530.0], ...]
  }
  ```

---

## 3. Mission OS Orchestration Endpoints

### `GET /api/mission-os/status`
Retrieves live multi-tier state twin telemetry, active phase, and fleet health.
- **Response `200 OK`:**
  ```json
  {
    "mission_id": "ATLAS-MARS-BASE-ALPHA-001",
    "current_sol": 42,
    "sol_time": "14:22:10",
    "active_phase_id": "PHASE-05-SCIENCE",
    "is_synchronized": true,
    "state_hash": "a4f891b...",
    "power_reserve_kwh": 312.4,
    "water_storage_kg": 3440.5
  }
  ```

### `GET /api/mission-os/flagship/run`
Triggers an automated clean execution of the 60-Sol flagship demonstration mission.
- **Response `200 OK`:**
  ```json
  {
    "status": "COMPLETED",
    "dossier": {
      "mission_id": "ATLAS-MARS-BASE-ALPHA-001",
      "total_duration_sols": 61,
      "phase_f_readiness_score": 100.0,
      "root_hash": "f9d124cfac3738ddb403be883ba273c2c9bc4af96b75f71a6ca66a96cb65bd14",
      "cryptographic_replay_valid": true
    }
  }
  ```

### `POST /api/mission-os/command`
Queues an interplanetary command subject to simulated $OWLT$ light-time delay and state hash verification.
- **Request Body:**
  ```json
  {
    "target_asset_id": "ATLAS-ROVER-01",
    "action": "EXECUTE_TRAVERSE",
    "parameters": {"target_lat": 18.4520, "target_lon": 77.4350},
    "expected_state_hash": "f9d124..."
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "command_id": "CMD-2026-0042",
    "state": "QUEUED_LIGHT_DELAY",
    "owlt_delay_seconds": 852.0,
    "scheduled_execution_sol": 42
  }
  ```
