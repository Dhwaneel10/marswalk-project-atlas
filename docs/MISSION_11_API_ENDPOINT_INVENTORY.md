# MISSION 11 — API ENDPOINT INVENTORY & SCHEMA CONTRACT AUDIT

**Project:** MarsWalk 2.0 / Project Atlas  
**Audited File:** [`run_atlas.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/scripts/run_atlas.py)  
**Total Route Handlers:** Over 400 endpoints across Core, Versioned (`/api/v1/*`), and Domain Workspaces.  
**Schema Standard:** JSON Schema Draft 2020-12 / Python Dataclasses  

---

## 1. Core Mission Operations & Pillar Endpoints

### 1.1 Planetary Health & Telemetry
- **`GET /api/health`**
  - *Description:* Server heartbeat and uptime verification.
  - *Response:* `{"status": "online", "version": "2.0.0", "timestamp": "...", "subsystems": {...}}`
- **`GET /api/status`**
  - *Description:* Global mission operations status, active campaign, and loaded DEM rasters.
- **`GET /api/v1/pillars/manifest`**
  - *Description:* Master cryptographic and scientific manifest of all 5 operational pillars.

---

### 1.2 Pillar 1: Terrain Intelligence Endpoints
- **`GET /api/v1/pillars/terrain`**
  - *Description:* Retrieves regional CTX (20m) and localized HiRISE (1m) raster bounds, spatial resolution, and CRS (`ESRI:103885`).
- **`POST /api/v1/pillars/terrain/inspect`**
  - *Payload:* `{"row": int, "col": int, "resolution": "20m" | "1m"}`
  - *Response:* Elevation in meters (MOLA geoid datum), local slope in degrees, roughness index.
- **`POST /api/profile`**
  - *Payload:* `{"start": {"row": int, "col": int}, "goal": {"row": int, "col": int}}`
  - *Response:* 1D elevation profile, slope distribution, cumulative ascent/descent along linear path.
- **`POST /api/gauntlet`**
  - *Payload:* `{"scenario_id": "hawksbill_rockfall" | "delta_channel_block" | ...}`
  - *Response:* Applies dynamic hazard masks (rockfall corridor closures) onto terrain cost grid.

---

### 1.3 Pillar 2: Rover Ground Truth Endpoints
- **`GET /api/v1/pillars/rover-ground-truth`**
  - *Description:* Retrieves NASA PDS Perseverance rover tactical localization telemetry (Sols 13–1896).
  - *Response:* Array of 577 ground-truth tactical stations with planetocentric Easting/Northing and LMST timestamps.
- **`POST /api/v1/pillars/rover-ground-truth/query`**
  - *Payload:* `{"sol_min": int, "sol_max": int, "site_id": str}`
  - *Response:* Filtered traverse path and associated Three Forks sample depot drop records.

---

### 1.4 Pillar 3: Environmental Intelligence Endpoints
- **`GET /api/weather/current`**
  - *Description:* Latest authentic in-situ atmospheric snapshot from Perseverance MEDA sensors.
  - *Response:* Surface pressure ($589.69\,\text{Pa}$), air temp ($-61.7^\circ\text{C}$), ground temp ($-59.95^\circ\text{C}$), diurnal tide phase.
- **`POST /api/weather/refresh`**
  - *Payload:* `{"site_id": "jezero_crater", "force_refresh": bool}`
  - *Response:* Updates weather snapshot from local cache or verified baseline.
- **`GET /api/v1/pillars/environment-meda`**
  - *Description:* Environmental summary statistics, diurnal reference profiles, and instrument citations.
- **`POST /api/environment/solar`**
  - *Payload:* `{"sol": int, "tau": float, "solar_elevation_deg": float}`
  - *Response:* Direct and diffuse solar irradiance ($W/m^2$) under dust loading $\tau$.

---

### 1.5 Pillar 4: Science-Driven Planning Endpoints
- **`POST /api/plan_route`**
  - *Payload:*
    ```json
    {
      "start": {"row": 117, "col": 157},
      "goal": {"row": 66, "col": 128},
      "profile": "balanced",
      "vehicle_mode": "robotic_rover",
      "stops": [{"row": 136, "col": 91, "priority_score": 85.0}],
      "budget_distance_m": 8000.0,
      "max_slope_deg": 15.0
    }
    ```
  - *Response:* Full 2D/3D traverse coordinates, path length ($m$), energy cost ($Wh$), max slope, ETA ($s$), Pareto efficiency.
- **`POST /api/routes`**
  - *Description:* Computes multi-profile route comparison (Conservative, Balanced, Direct, Science-First) simultaneously.
- **`POST /api/v1/pillars/science-targets/plan`**
  - *Description:* Bounded beam-search optimization of authentic astrobiology targets (Wildcat Ridge, Skinner Ridge, etc.).
- **`POST /api/preferences/feedback`**
  - *Description:* Ingests operator choice $\mathbf{x}_{\text{sel}} \succ \mathbf{x}_{\text{rej}}$ and updates Bradley-Terry linear utility model.

---

### 1.6 Pillar 5: Autonomous Resilience Endpoints ("When Mars Goes Dark")
- **`POST /api/flagship/when-mars-goes-dark/run`**
  - *Description:* Executes the canonical 5-Sol resilience demonstration.
  - *Response:* Full multi-Sol event log: dust storm detection, comms blackout, DTN custody queue, rockfall detour replan, and restoration.
- **`GET /api/flagship/when-mars-goes-dark/status`**
  - *Description:* Current execution phase, rover position, battery state-of-charge ($SoC$), and DTN bundle custody count.
- **`GET /api/flagship/when-mars-goes-dark/comparison`**
  - *Description:* Quantitative comparison matrix between Baseline (Static) vs Autonomous Resilient mission strategies.
- **`POST /api/flagship/when-mars-goes-dark/replay`**
  - *Description:* Replays mission execution deterministically with SHA-256 Merkle root verification.

---

## 2. Error Gating & Contract Compliance

All endpoints adhere to standardized HTTP status code contracts:
- `200 OK`: Request succeeded; valid payload returned.
- `400 Bad Request`: Payload validation failed (e.g. coordinates out of bounds, unknown profile, non-numeric values).
- `404 Not Found`: Target entity (campaign ID, mission replay, or route ID) does not exist.
- `409 Conflict`: Concurrency conflict or conflicting branch mutation.
- `500 Internal Error`: Unhandled server exception (safely caught and serialized with stack trace logging).
