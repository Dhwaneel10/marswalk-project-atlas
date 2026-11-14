# Project MarsWalk — Subsystem Dependency & Data Flow Map

**Document ID:** `MARSWALK-DEP-001`  
**Date:** 2026-11-14  
**Author:** Principal Software Architect & Systems Engineer  
**Workspace:** `/home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission`  
**Target Environment:** Ubuntu 22.04 LTS

---

## 1. High-Level Subsystem Communication Graph

The MarsWalk 2.0 / Project Atlas software system is structured as an interactive client-server architecture backed by an authoritative discrete-event simulation kernel:

```mermaid
graph TD
    subgraph BrowserClient["Browser Client Tier (web/)"]
        IndexHTML["web/index.html (Single Page App)"]
        AppJS["web/app.js (State Machine & Controller)"]
        ThreeJS["web/libs/three.min.js (Three.js r128 Engine)"]
        OrbitControls["web/libs/OrbitControls.js (Camera Rig)"]
        StylesCSS["web/styles.css (Aerospace Dark UI)"]
        
        IndexHTML --> AppJS
        IndexHTML --> StylesCSS
        AppJS --> ThreeJS
        AppJS --> OrbitControls
    end

    subgraph ServerTier["Server & API Tier (scripts/run_atlas.py & marswalk.api)"]
        ServerRunner["scripts/run_atlas.py (Port 3000 ThreadingHTTPServer)"]
        StaticServer["SimpleHTTPRequestHandler (Static File Server)"]
        APIService["marswalk.api.service (REST API Dispatcher)"]
        Contracts["marswalk.api.contracts (Draft 2020-12 Validator)"]
        Workspace["marswalk.api.workspace (Persistent JSON Store)"]
        DecisionPack["marswalk.api.decision_pack (Single-File ZIP Packager)"]

        ServerRunner --> StaticServer
        ServerRunner --> APIService
        APIService --> Contracts
        APIService --> Workspace
        APIService --> DecisionPack
    end

    subgraph CoreSimTier["Core Simulation & Scientific Tier (marswalk.core)"]
        TerrainEngine["marswalk.core.terrain (DTM, Slopes, Roughness)"]
        RoutePlanner["marswalk.core.planner (A* & Multi-Stop TSP)"]
        RelayEngine["marswalk.core.relay_graph & relay_planner"]
        DTNEngine["marswalk.core.atlas_dtn_engine (BPv7 Custody & Buffers)"]
        Resilience["marswalk.core.mars_fault_injection & coordinator"]
        ExecutionCore["marswalk.core.atlas_mission_execution_core"]
        StateTwin["marswalk.core.atlas_mission_state (Merkle Chain)"]
        
        APIService --> TerrainEngine
        APIService --> RoutePlanner
        APIService --> RelayEngine
        APIService --> DTNEngine
        APIService --> Resilience
        APIService --> ExecutionCore
        ExecutionCore --> StateTwin
        RoutePlanner --> TerrainEngine
        RelayEngine --> TerrainEngine
    end

    subgraph DataStorage["Data & Asset Tier (data/)"]
        RawDTM[("data/raw/JEZ_ctx_...20m.tif (9.3 MB)")]
        ReadyDTM[("data/processed/jezero_ready_20m.tif (247 KB)")]
        PlacesJSON[("web/data/mars_places.json (2,061 items)")]
        WeatherJSON[("data/weather/*.json (PDS Baselines)")]
        Workspaces[("data/workspaces/ (Persistent JSON Records)")]
        
        TerrainEngine --> ReadyDTM
        StaticServer --> PlacesJSON
        APIService --> WeatherJSON
        Workspace --> Workspaces
    end

    AppJS -- "HTTP REST Requests (/api/...)" --> ServerRunner
    AppJS -- "Static Assets Fetch (GET /web/...)" --> StaticServer
```

---

## 2. Detailed Internal Module Dependency Matrix

### 2.1 Python Core Module Dependency Chains

```mermaid
graph LR
    subgraph DataIngestion["1. Data Ingestion"]
        DI_Ingest["data.ingest"]
        DI_Registry["data.imagery_registry"]
        DI_Cache["data.tile_cache"]
    end

    subgraph TerrainPhysics["2. Terrain & Physics"]
        TP_Terrain["core.terrain"]
        TP_Visibility["core.terrain_visibility"]
        TP_Intel["core.terrain_intelligence"]
    end

    subgraph RoutePlanning["3. Route Planning"]
        RP_Planner["core.planner"]
        RP_Optimizer["core.mission_optimizer"]
        RP_Replanner["core.adaptive_replanner"]
        RP_Explainer["core.route_explainer"]
    end

    subgraph CommsRelay["4. Comms & RelayNet"]
        CR_RelayGraph["core.relay_graph"]
        CR_RelayPlanner["core.relay_planner"]
        CR_DTN["core.atlas_dtn_engine"]
        CR_Scheduler["core.atlas_contact_scheduler"]
    end

    subgraph FaultResilience["5. Fault & Resilience"]
        FR_Fault["core.mars_fault_injection_engine"]
        FR_Prop["core.mars_failure_propagation"]
        FR_Coord["core.atlas_mission_resilience_coordinator"]
        FR_Stress["core.stress_test"]
        FR_Contingency["core.contingency"]
    end

    subgraph ExecutionReproducibility["6. Mission Execution & Hash Chain"]
        ER_Exec["core.atlas_mission_execution_core"]
        ER_State["core.atlas_mission_state"]
        ER_Replay["core.atlas_mission_replay"]
    end

    DI_Ingest --> TP_Terrain
    TP_Terrain --> RP_Planner
    TP_Terrain --> TP_Visibility
    TP_Visibility --> CR_RelayPlanner
    CR_RelayGraph --> CR_RelayPlanner
    RP_Planner --> RP_Optimizer
    RP_Planner --> RP_Replanner
    FR_Fault --> FR_Prop
    FR_Prop --> FR_Coord
    FR_Coord --> RP_Replanner
    ER_Exec --> ER_State
    ER_Exec --> FR_Coord
    ER_Exec --> CR_DTN
    ER_State --> ER_Replay
```

---

## 3. The Eager Import Bottleneck (Architectural Defect)

A critical architectural coupling defect was discovered during the reconnaissance:

```mermaid
graph TD
    CallerModule["Any Caller (e.g. preflight_check.py, campaign_analytics.py)"]
    ApiInit["src/marswalk/api/__init__.py"]
    ApiService["src/marswalk/api/service.py"]
    Contracts["src/marswalk/api/contracts.py"]
    RasterioPkg["External Package: rasterio"]
    JsonschemaPkg["External Package: jsonschema"]

    CallerModule -- "from marswalk.api.contracts import ..." --> ApiInit
    ApiInit -- "eager import: from marswalk.api.service import ..." --> ApiService
    ApiService -- "top-level import (line 15)" --> RasterioPkg
    Contracts -- "top-level import (line 12)" --> JsonschemaPkg
    Contracts -- "top-level import (line 13)" --> RasterioPkg

    style RasterioPkg fill:#ff9999,stroke:#ff0000,stroke-width:2px;
    style JsonschemaPkg fill:#ff9999,stroke:#ff0000,stroke-width:2px;
```

### Defect Explanation
In `src/marswalk/api/__init__.py`:
```python
# Line 5: Eagerly imports service.py
from marswalk.api.service import plan_route_api, gauntlet_api, parse_endpoint_rc
```
Because `service.py` has `import rasterio` on line 15, importing *anything* from `marswalk.api` (such as `contracts.py` or `workspace.py`) triggers an immediate top-level `ModuleNotFoundError` if `rasterio` is not installed, even if the calling script does not perform any raster operations!

**Resolution Strategy (For Milestone 2):**  
Decouple `__init__.py` so that imports from `marswalk.api` do not eagerly import `service.py` unless explicitly requested, or guard `import rasterio` inside functions that actually read GeoTIFFs.

---

## 4. External Software and Library Dependencies

### 4.1 Python Package Dependencies

| Package | Declared in `requirements.txt` | Current Ubuntu System Status | Impact if Missing |
|:---|:---:|:---:|:---|
| `numpy` | `>=2.0.0` | Installed (v1.21.5) | Numerical calculations execute, but version mismatch exists. |
| `scipy` | `>=1.14.0` | Installed (v1.8.0) | Spatial trees work; version difference. |
| `rasterio` | `>=1.4.0` | **NOT INSTALLED** | **CRITICAL BLOCKER:** Prevents server boot and DTM loading. |
| `affine` | `>=2.4.0` | **NOT INSTALLED** | **CRITICAL BLOCKER:** Needed for GeoTIFF spatial coordinates. |
| `jsonschema` | `>=4.20.0` | **NOT INSTALLED** | **BLOCKER:** Needed for API request contract enforcement. |
| `requests` | `>=2.31.0` | Installed (v2.25.1) | Functional for HTTP API tests. |
| `websockets` | `>=12.0` | Installed (v9.1) | Usable for CDP streams. |
| `pytest` | `>=8.0.0` | Installed (v6.2.5) | **DEFECT:** Does not support `pythonpath` config in `pyproject.toml`. |
| `plotly` | Optional | **NOT INSTALLED** | Only impacts Streamlit `app.py`. |
| `streamlit` | Optional | **NOT INSTALLED** | Only impacts Streamlit `app.py`. |

### 4.2 Native Linux System Libraries (Ubuntu 22.04 LTS)
`rasterio` requires native C/C++ geospatial libraries. When building or installing into a virtual environment, the system requires:
- `libgdal-dev` (GDAL geospatial data abstraction library)
- `libproj-dev` (Cartographic projections library)
- `libgeos-dev` (Geometry engine)
- Standard wheels (`pip install rasterio`) typically bundle precompiled GDAL binaries, avoiding manual compile times if wheel compatibility is met.

### 4.3 Node.js & Web Runtime
- **Node.js:** System has `v22.23.5` installed.
- **npm dependencies:** None. All web dependencies (`three.min.js`, `OrbitControls.js`) are vendored in `web/libs/`.

---

## 5. File & Dataset Dependency Map

```mermaid
graph TD
    subgraph PrimaryDatasets["Authentic Primary Datasets"]
        RAW_DTM["data/raw/JEZ_ctx_...20m.tif<br/>(9.3 MB, USGS Astrogeology)"]
        READY_DTM["data/processed/jezero_ready_20m.tif<br/>(247 KB, Calibrated 250x250)"]
        PLACES["web/data/mars_places.json<br/>(2,061 USGS Nomenclature Items)"]
        WAYPOINTS["data/waypoints_jezero.json<br/>(6 Verified Science Targets)"]
    end

    subgraph SimulationConsumers["Consuming Subsystems"]
        TERRAIN_MOD["marswalk.core.terrain"]
        INGEST_MOD["marswalk.data.ingest"]
        PLANNER_MOD["marswalk.core.planner"]
        RELAY_MOD["marswalk.core.relay_planner"]
        THREE_CANVAS["Three.js 3D Viewport"]
    end

    RAW_DTM --> INGEST_MOD
    INGEST_MOD --> READY_DTM
    READY_DTM --> TERRAIN_MOD
    TERRAIN_MOD --> PLANNER_MOD
    TERRAIN_MOD --> RELAY_MOD
    PLACES --> THREE_CANVAS
    WAYPOINTS --> PLANNER_MOD
    WAYPOINTS --> THREE_CANVAS
```
