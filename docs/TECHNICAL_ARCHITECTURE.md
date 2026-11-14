# Project MarsWalk 2.0 / Atlas — Technical Systems Architecture
**Document ID:** `DOC-MW-M7-TECH-ARCHITECTURE`  
**System Version:** 2.0.0-RELEASE  
**Runtime:** Python 3.10.12 Backend Daemon | HTML5/WebGL/Three.js Frontend  
**Service Port:** `3000` (HTTP REST & Static Serving)  

---

## 1. System Overview & Architectural Topology

MarsWalk 2.0 is structured as a decoupled, deterministic planetary operations workstation. A Python REST service powers the geospatial, physical, and algorithmic planning engines, serving an interactive 3D WebGL client:

```
+-------------------------------------------------------------------------------------------------------+
|                                  MARSWALK 2.0 SYSTEM ARCHITECTURE                                     |
+-------------------------------------------------------------------------------------------------------+
                                        WEB BROWSER CLIENT
                               (WebGL 3D Engine, Three.js, Canvas)
  +---------------------------------------------------------------------------------------------------+
  |  Hero Stage / 15-Sec Landing  |  Five-Pillar Operations Deck  |  Evaluator Golden Path HUD (7-St) |
  |  Jezero Crater 3D Surface     |  Cockpit HUD Telemetry        |  Mission Theater & Rehearsal      |
  +---------------------------------------------------------------------------------------------------+
                                                |
                                      HTTP JSON REST / Port 3000
                                                v
  +---------------------------------------------------------------------------------------------------+
  |                                   PYTHON REST API SERVICE                                         |
  |                                  (src/marswalk/api/service.py)                                    |
  +---------------------------------------------------------------------------------------------------+
        |                     |                     |                     |                     |
        v                     v                     v                     v                     v
  +-------------+       +-------------+       +-------------+       +-------------+       +-------------+
  |  Pillar 1:  |       |  Pillar 2:  |       |  Pillar 3:  |       |  Pillar 4:  |       |  Pillar 5:  |
  |   Terrain   |       |    Rover    |       |    MEDA     |       |   Science   |       |   DTN &     |
  |   Engine    |       |   History   |       |   Weather   |       |   Planner   |       | Resilience  |
  | (Rasterio,  |       | (PDS PLACES,|       |  (In-Situ   |       |  (Multi-Obj |       |  (RFC 9171, |
  |  Horn DTM)  |       | Three Forks)|       | Atmospheres)|       |  A* Search) |       | Merkle Root)|
  +-------------+       +-------------+       +-------------+       +-------------+       +-------------+
        |                     |                     |                     |                     |
        +---------------------+---------------------+---------------------+---------------------+
                                                |
                                                v
  +---------------------------------------------------------------------------------------------------+
  |                               PLANETARY DATA PROVENANCE LAYER                                     |
  |                           (data/raw/, data/processed/, data/catalogs/)                            |
  | USGS Jezero CTX 20m | USGS HiRISE 1m | PDS PLACES | MEDA CSV/JSON | Master Provenance Manifest     |
  +---------------------------------------------------------------------------------------------------+
```

---

## 2. Data Ingestion & Provenance Pipeline

1. **Master Manifest Ledger (`data/manifests/nasa_data_provenance_manifest.json`):**
   - Indexes all 8 primary datasets with product IDs, spatial coverage, local paths, and SHA-256 digests.
   - Enforces cryptographic verification on startup via `scripts/audit_nasa_data.py`.
2. **Terrain Ingestion (`src/marswalk/core/terrain.py`):**
   - Ingests USGS Jezero CTX 20m DTM GeoTIFF ($250 \times 250$ raster cells).
   - Ingests USGS TRN HiRISE 1m micro-hazard DTM ($600 \times 600$ raster cells).
   - Validates CRS compliance against planetocentric IAU 2000 Mars Spheroid ($R = 3,396,190\,\text{m}$, ESRI:103885).
   - Replaces floating-point NoData masks (`-3.402823e+38`) with local elevation interpolation.
3. **Slope Gradient Kernel:**
   - Computes surface slope using the Horn (1981) 8-neighbor finite difference kernel:
     $$\frac{\partial z}{\partial x} = \frac{(z_{i+1, j-1} + 2z_{i+1, j} + z_{i+1, j+1}) - (z_{i-1, j-1} + 2z_{i-1, j} + z_{i-1, j+1})}{8 \cdot \Delta x}$$
     $$\frac{\partial z}{\partial y} = \frac{(z_{i-1, j+1} + 2z_{i, j+1} + z_{i+1, j+1}) - (z_{i-1, j-1} + 2z_{i, j-1} + z_{i+1, j-1})}{8 \cdot \Delta y}$$
     $$\theta = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right)$$
   - Enforces operational slope threshold $\theta_{\text{max}} = 15.0^\circ$ for rover traversability.

---

## 3. Rover Ground Truth & Sample Depot Architecture

1. **Tactical Rover Positioning (`data/raw/m2020_places/best_tactical.csv`):**
   - Ingests 577 archived tactical sites from NASA PDS Rover PLACES across Sols 13 to 1896.
   - Converts planetocentric latitude/longitude coordinates to local raster row/column indices using affine transformation matrices.
2. **Three Forks Sample Depot (`data/catalogs/three_forks_sample_depot.json`):**
   - Indexes the 10 sealed titanium tubes dropped in Jezero crater between Sols 653 and 680.
   - Reconciles historical sample pairings: Tube #241 (*Malay*) and Tube #239 (*Bearwallow*) are located at Three Forks; sister core *Hazelton* (Tube #268) is retained onboard Perseverance.

---

## 4. Atmospheric Coupling Engine (NASA MEDA)

1. **In-Situ Atmospheric Observations:**
   - Ingests calibrated diurnal reference profiles from NASA Mars 2020 MEDA (`data/catalogs/meda_environmental_observations.json`).
   - Tracks surface pressure ($690\text{--}775\,\text{Pa}$), ambient air temperature ($-88.4^\circ\text{C}$ to $-11.2^\circ\text{C}$), and wind speeds ($4.8\text{--}24.6\,\text{m/s}$).
2. **Subsystem Derivations:**
   - **Solar Transmission:** Plane-parallel Beer-Lambert model:
     $$T = \exp\left(-\frac{\tau}{0.85}\right)$$
     Clean array capacity $P_0 = 900.0\,\text{W}$. Attenuation drops power to $258.6\,\text{W}$ at $\tau = 1.06$ ($-71.3\%$), and to $50.4\,\text{W}$ at $\tau = 2.45$ ($-94.4\%$).
   - **Battery Survival Heating:** Dynamic thermal load model:
     $$P_{\text{heater}} = \max\left(0.0, (-20.0 - T_{\text{air}}) \times 1.8\right)\,\text{W}$$
   - **RF Path Extinction:** Documented as an empirical heuristic proxy:
     $$\alpha_{\text{RF}} = 0.008 + 0.098 \cdot \tau^{1.15}\,\text{dB/km}$$

---

## 5. Multi-Objective Science Route Planning Engine

1. **Search Algorithm:** Multi-Objective A* search over the 20m CTX cost grid.
2. **Cost Function Formulation:**
   $$f(n) = g(n) + h(n) + C_{\text{slope}}(n)$$
   where $g(n)$ is Euclidean travel distance, $h(n)$ is Euclidean distance to goal, and $C_{\text{slope}}$ applies a steep exponential barrier penalty for slopes approaching $15.0^\circ$:
   $$C_{\text{slope}} = \begin{cases} 
   0 & \theta < 10.0^\circ \\ 
   10 \cdot (\theta - 10.0)^2 & 10.0^\circ \le \theta < 15.0^\circ \\ 
   \infty & \theta \ge 15.0^\circ 
   \end{cases}$$
3. **Science Target Interception Threshold:**
   - $R_{\text{intercept}} = 30.0\,\text{m}$ ($1.5 \times$ cell pitch).
   - Evaluates direct transit (Route A) against science-prioritized detour (Route B) visiting Wildcat Ridge ($+95\,\text{pts}$) and Kodiak Butte ($+65\,\text{pts}$).

---

## 6. Delay-Tolerant Networking & Autonomous Resilience Engine

1. **RFC 9171 Bundle Protocol Simulator:**
   - Simulates custodian storage of 6 telemetry bundles ($4.4\,\text{MB}$) during a 4-hour orbital comms blackout.
   - Restores transmission when Line-of-Sight is regained, achieving 100% data yield (0 bytes lost).
2. **Cryptographic Merkle Proof:**
   - Reconciles 7 sequential lifecycle snapshots into a binary SHA-256 Merkle tree:
     ```
                     Root: 0380a7cf112a7bd3...
                            /          \
                   Hash(0..3)          Hash(4..6)
                    /      \            /      \
                 H(0,1)   H(2,3)     H(4,5)    H(6,6)
     ```
   - Confirms bit-exact reconciliation with zero tamper vectors.

---

## 7. Major REST API Contracts

| Endpoint | HTTP Method | Request Payload | Response Attributes |
| :--- | :--- | :--- | :--- |
| `/api/health` | `GET` | None | `status`, `terrain_loaded`, `waypoints_count` |
| `/api/pillars/terrain` | `GET` | None | CTX and HiRISE grid dimensions, resolution, CRS, SHA-256 |
| `/api/pillars/terrain/inspect` | `POST` | `{"row": int, "col": int}` | `elevation_m`, `slope_deg`, `resolution_m`, `hazard_tier` |
| `/api/pillars/rover-ground-truth` | `GET` | None | Total tactical sites, sol range, Three Forks depot summary |
| `/api/pillars/rover-ground-truth/query` | `GET` | `?depot_only=true` | Inventory of 10 sealed titanium tubes |
| `/api/pillars/environment-meda/calibrate` | `POST` | `{"optical_depth_tau": float, ...}` | In-situ weather, solar output W, heater load W, RF loss |
| `/api/pillars/science-targets/plan` | `POST` | `{"start_rc": [r,c], "goal_rc": [r,c], "target_ids": [...]}` | Route A vs Route B distance, energy, time, science score |
| `/api/flagship/when-mars-goes-dark/replay` | `GET` | None | 7 lifecycle snapshots, DTN yield, Merkle root hash |
