# FINAL SYSTEM ARCHITECTURE SPECIFICATION
## Project MarsWalk 2.0 / Atlas — "WHEN MARS GOES DARK"
**Document ID:** `SPEC-SYS-ARCH-2026-FINAL`  
**System Version:** MarsWalk 2.0 / Atlas v2.4-Hardened  
**Primary Target Body:** Mars (IAU 2000 Planetary Spheroid, $R = 3{,}396.19\,\text{km}$)  
**Reference Terrain:** USGS CTX Jezero Crater Delta ($20\,\text{m/pixel}$ DTM, $18.38^\circ\,\text{N}, 77.58^\circ\,\text{E}$)  
**Status:** QUALIFIED & TEST-VERIFIED

---

## 1. ARCHITECTURAL OVERVIEW

Project MarsWalk 2.0 (Project Atlas) is an integrated, planetary-scale mission operations and autonomous surface traverse platform. It is engineered specifically to demonstrate robotic resilience under extreme Martian environmental disruptions, catastrophic communications blackouts, and unforeseen topographic corridor failures.

The core architecture unites seven operational domains into a deterministic, verifiable workflow:
1. **Planetary Terrain & Coordinate Engine:** High-resolution GeoTIFF ingestion, IAU 2000 spheroid projections, slope angle determination, roughness estimation, and NoData hazard dilation.
2. **Multi-Objective A\* Traverse Planner:** Pareto-optimal pathfinding balancing traverse distance, slope penalty, mechanical energy dissipation, and scientific waypoint value.
3. **Terrain-Aware RF Line-of-Sight Engine:** Numerical chord line-of-sight ray casting across 2.5D elevation models, accounting for antenna mast heights and geometric crater rim shadows.
4. **RFC 9171 Delay-Tolerant Networking (DTN) Engine:** Store-and-forward bundle custody buffer asserting local storage retention during communications occlusions with strict CCSDS priority flushing.
5. **Fault Injection & Contingency Monitor:** Real-time corridor occlusion detection, traction motor overtemperature protection, and autonomous safe hold actuation.
6. **Adaptive Replanning & Causal Explanation Core:** Dynamic re-routing around blocked corridors, selecting lateral detours that maximize elevation gain for RF recovery.
7. **Cryptographic Merkle State Chainer:** Immutable SHA-256 state tracking linking every snapshot to its predecessor, producing a verifiable, tamper-proof audit trail.

---

## 2. SUBSYSTEM INTERACTION & PIPELINE ARCHITECTURE

The following flowchart illustrates the complete data and control flow of the MarsWalk 2.0 system:

```mermaid
flowchart TD
    subgraph S1["1. Planetary Terrain & Environment"]
        DTM["USGS CTX Jezero 20m DTM"] --> TGrid["TerrainGrid Engine (Elevation, Slope, Roughness)"]
        Atmosphere["Atmospheric Tau & Insolation Model (G0 = 590 W/m2)"] --> Power["Differential Power Balance Model"]
    end

    subgraph S2["2. Autonomous Planning & RF Geometry"]
        TGrid --> AStar["Multi-Objective A* Planner"]
        TGrid --> LOS["Line-of-Sight Ray Caster (Rover Mast 2.5m vs Base 15m)"]
        Waypoints["Science Waypoints (Three Forks, Hawksbill, Ridge)"] --> AStar
    end

    subgraph S3["3. Communication & Data Logistics"]
        LOS --> Carrier["RF Carrier State Detector (128 kbps vs 0 kbps)"]
        Instruments["Scientific Payload (SHERLOC Raman, PIXL, Mastcam-Z)"] --> Bundles["RFC 9171 Data Bundles"]
        Carrier --> DTN["Planetary DTN Engine (32MB Local Flash Buffer)"]
        Bundles --> DTN
    end

    subgraph S4["4. Fault Handling & Adaptive Recovery"]
        Hazards["Forward Hazard Detection (Rockfall Obstacle)"] --> FaultDetector["Fault Monitor & Motor Load Guard"]
        FaultDetector --> SafeHold["Autonomous Safe Hold (0W Drive Cutoff)"]
        SafeHold --> Replanner["Adaptive Replanner Engine"]
        TGrid --> Replanner
        Replanner --> DetourRoute["Ridge Terrace Detour (+42.6m Elevation Delta)"]
    end

    subgraph S5["5. State Attestation & Replay"]
        AStar --> StateTracker["Mission Stage State Engine (7 Snapshots)"]
        DTN --> StateTracker
        SafeHold --> StateTracker
        DetourRoute --> StateTracker
        StateTracker --> MerkleChain["Merkle State Chainer (SHA-256 Hash Chain)"]
        MerkleChain --> RootMerkle["Deterministic Root Hash: 0380a7cf..."]
    end

    subgraph S6["6. Operator Interface & Web Services"]
        StateTracker --> API["Atlas REST API Service (Port 3000)"]
        RootMerkle --> API
        API --> WebHUD["Cockpit Web Workstation (Three.js WebGL & HUD)"]
        WebHUD --> Scrubber["Interactive Timeline Scrubber"]
        WebHUD --> CompModal["Strategy Comparison Modal"]
    end
```

---

## 3. CORE SUBSYSTEM RESPONSIBILITIES

### 3.1 Planetary Terrain Engine (`src/marswalk/core/terrain.py`)
- Ingests single-band float32 GeoTIFFs (`jezero_ready_20m.tif`).
- Computes cell slope gradients via central differences:
  $$\nabla z = \left( \frac{\partial z}{\partial x}, \frac{\partial z}{\partial y} \right), \quad \theta = \arctan(\|\nabla z\|)$$
- Enforces strict traversability slope cutoffs ($15.0^\circ$ maximum rover grade).
- Dilates NoData mask pixels to ensure rover safety margins.

### 3.2 RF Line-of-Sight Ray Caster (`src/marswalk/core/terrain_visibility.py`)
- Evaluates line-of-sight clearance between arbitrary surface points $(r_1, c_1)$ and $(r_2, c_2)$ using Bresenham 2.5D profile interpolation.
- Models antenna elevations: Rover mast $h_r = 2.5\,\text{m}$, Base station mast $h_b = 15.0\,\text{m}$.
- Identifies exact terrain occlusion points where intervening crater ridges intercept the radio chord.

### 3.3 Delay-Tolerant Networking Engine (`src/marswalk/core/atlas_dtn_engine.py`)
- Implements RFC 9171 Bundle Protocol Version 7 (BPv7).
- Nodes: `PERSEVERANCE_ROVER` ($32\,\text{MB}$ flash allocation), `BASE_STATION` ($1\,\text{GB}$ base storage).
- Supports 5 standardized priority tiers:
  1. `CLASS_1_EMERGENCY` (Emergency telemetry)
  2. `CLASS_2_COMMAND_UPLINK` (Recovery confirmations, flight commands)
  3. `CLASS_3_HIGH_PRIORITY_SCIENCE` (Spectroscopic discoveries, e.g. SHERLOC Raman)
  4. `CLASS_4_ROUTINE_ENGINEERING` (Motor thermals, housekeeping)
  5. `CLASS_5_BULK_SCIENCE` (Multispectral panoramas)
- Enforces strict priority drain upon line-of-sight restoration.

### 3.4 Adaptive Replanner (`src/marswalk/core/adaptive_replanner.py`)
- Detects dynamic obstacle events (`CLOSED_CORRIDOR`, boulder fields).
- Eliminates blocked nodes from traversability space.
- Re-executes heuristic A\* search to compute lateral bypass corridors.
- Logs explainable mission decisions: evaluates trade-offs between slope gradient, distance penalty, and elevation gain for communications clearance.

### 3.5 Flagship Scenario Engine (`src/marswalk/core/when_mars_goes_dark.py`)
- Orchestrates the signature 7-stage Jezero Crater resilience mission.
- Computes deterministic state snapshots capturing sol, position, elevation, comms status, solar flux, battery charge, optical depth, alarms, and buffer status.
- Generates side-by-side Strategy Comparison metrics between nominal failure and adaptive success.
- Calculates immutable SHA-256 Merkle root hash.

### 3.6 WebGL Mission Control Workstation (`web/app.js`, `web/index.html`)
- Unified Mission Control Cockpit with Three.js 3D terrain canvas.
- Real-time animated playback across all 7 operational stages.
- Interactive timeline scrubber allowing direct stage inspection.
- Side-by-side Strategy Comparison card.
- One-click cryptographic proof verification.

---

## 4. DETERMINISTIC REPRODUCIBILITY CONTRACT

The system enforces bit-exact reproducibility across restarts:
- **Seed:** Fixed deterministic seed ($42$).
- **State Hashes:** Each snapshot hash incorporates its predecessor's SHA-256 hash, stage identifier, sol timestamp, rover grid position, comms status, battery reserve, and delivered bundle count.
- **Root Merkle Hash:** 
  $$\text{Root} = \text{SHA-256}\left(\sum_{i=1}^{7} \text{SnapshotHash}_i\right) = \mathbf{0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8}$$
- This root hash is identical on Ubuntu Linux, macOS, and Windows platforms.
