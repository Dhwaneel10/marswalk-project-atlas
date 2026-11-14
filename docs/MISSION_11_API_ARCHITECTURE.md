# MISSION 11 — API ARCHITECTURE & INTEGRATION SPECIFICATION

**Project:** MarsWalk 2.0 / Project Atlas  
**Architecture Style:** Layered Microkernel / Local JSON REST Gateway  
**Server Daemon:** [`run_atlas.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/scripts/run_atlas.py)  
**Gateway Service:** [`service.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/api/service.py)  
**Contract Validation:** [`contracts.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/api/contracts.py)  
**Dependency Graph:** [`api_dependency_graph.mmd`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_11/api_dependency_graph.mmd)

---

## 1. Architectural Philosophy

MarsWalk 2.0 employs an **offline-first, zero-external-dependency microkernel architecture** designed to simulate an autonomous planetary flight operations console.

```
┌────────────────────────────────────────────────────────┐
│             BROWSER WEB CLIENT (Three.js HUD)          │
└────────────────────────────────────────────────────────┘
                           │ (Local HTTP / JSON REST)
                           ▼
┌────────────────────────────────────────────────────────┐
│           LOCAL HTTP DAEMON (scripts/run_atlas.py)     │
│        Single-threaded Non-blocking BaseHTTPHandler    │
└────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│          UNIFIED API GATEWAY (src/marswalk/api)        │
│    Contract Validation • Error Gating • Merkle Tree    │
└────────────────────────────────────────────────────────┘
       │           │             │            │
       ▼           ▼             ▼            ▼
┌───────────┐ ┌─────────┐   ┌───────────┐ ┌──────────┐
│  Terrain  │ │  Rover  │   │Environment│ │ Planning │
│  Pillar 1 │ │Pillar 2 │   │ Pillar 3  │ │ Pillar 4 │
└───────────┘ └─────────┘   └───────────┘ └──────────┘
```

### Core Design Principles:
1. **100% Local Self-Containment:** The application server binds exclusively to `127.0.0.1` (or local interface). No cloud servers, telemetry trackers, or external APIs are required.
2. **Schema-Strict JSON Contracts:** Every inbound request and outbound payload conforms to Draft 2020-12 compatible dataclass schemas defined in `contracts.py`. Unknown fields, invalid coordinate types, or missing bounds are rejected with HTTP 400 Bad Request.
3. **Decoupled Planetary Services:** Computational engines (A\* search, Horn slope filters, DTN bundle simulation) are decoupled from the HTTP transport layer. They can be invoked directly as Python library calls or executed via HTTP REST.
4. **Deterministic Merkle Provenance:** All campaign operations, replans, and event logs write state transitions to structured JSON files with SHA-256 Merkle root verification.

---

## 2. API Request Lifecycle

1. **Client Dispatch:** The single-page web application (`web/app.js`) dispatches an asynchronous `fetch('/api/v1/...')` request with JSON payload.
2. **Path & Verb Routing:** `run_atlas.py` matches the request method (`GET` / `POST` / `OPTIONS`) and endpoint against its route registry.
3. **Input Sanitization & Contract Validation:** Inbound parameters (e.g. start/goal rows and columns, profile constraints, max slope) are parsed and type-checked against `src/marswalk/api/contracts.py`.
4. **Core Service Invocation:** The dispatcher invokes the relevant core engine in `src/marswalk/core/` (e.g. `planner.py` for routing, `weather.py` for atmospheric state).
5. **JSON Response Serialization:** The resulting dataclass is serialized to UTF-8 JSON with standard status codes (`200 OK`, `400 Bad Request`, `404 Not Found`, `500 Server Error`).
6. **Socket Error Resilience:** Outbound writes are wrapped in `BrokenPipeError` and `ConnectionResetError` exception guards to prevent server process death if client browsers disconnect prematurely.

---

## 3. Pillar Mapping & Endpoint Groups

| Architectural Pillar | Core Modules Involved | Primary Endpoints |
| :--- | :--- | :--- |
| **Pillar 1: Terrain Intelligence** | `terrain.py`, `terrain_intelligence.py` | `/api/v1/pillars/terrain`, `/api/profile`, `/api/gauntlet` |
| **Pillar 2: Rover Ground Truth** | `planetary_archive_ingestion.py` | `/api/v1/pillars/rover-ground-truth`, `/api/catalogs/places` |
| **Pillar 3: Environmental Intelligence** | `weather.py`, `atlas_mars_atmospheric_model.py` | `/api/v1/pillars/environment-meda`, `/api/weather/current`, `/api/environment/raster` |
| **Pillar 4: Science-Driven Planning** | `planner.py`, `science_budget.py`, `preferences.py` | `/api/plan_route`, `/api/routes`, `/api/v1/pillars/science-targets/plan` |
| **Pillar 5: Autonomous Resilience** | `when_mars_goes_dark.py`, `atlas_dtn_engine.py` | `/api/flagship/when-mars-goes-dark/*`, `/api/v1/planetary-network/*` |
