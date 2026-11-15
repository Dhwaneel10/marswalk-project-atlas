# TECHNICAL ARCHITECTURE & SYSTEMS DESIGN
## MarsWalk 2.0 / Project Atlas

**NASA International Space Apps Challenge 2026**  
**Document:** System Architecture, Data Flow, and Core Algorithms  
**Release:** `v2.2.0-eva-qualified`  

---

### 1. High-Level Architectural Overview

MarsWalk is built upon a decoupled, high-performance architecture comprising an asynchronous scientific Python computational engine, an in-memory spatial cache, a RESTful API service, and a lightweight WebGL/Three.js interactive operational cockpit:

```
+---------------------------------------------------------------------------------------+
|                                    PRESENTATION LAYER                                 |
|                                                                                       |
|  +---------------------------+   +---------------------------+   +------------------+ |
|  | Astronaut Visor HUD       |   | 3D WebGL Terrain Canvas   |   | EVA Route Cards  | |
|  | - Live PLSS O2 Gauge      |   | - 1m HiRISE Surface Mesh  |   | - Conservative   | |
|  | - Metabolic Burn (Kcal)   |   | - Dual-Track Polyline (3D)|   | - Science-Pri    | |
|  | - Contingency Advisories  |   | - Perseverance Waypoints  |   | - Time-Efficient | |
|  +---------------------------+   +---------------------------+   +------------------+ |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | Multi-Mode Operation Switcher: [ASTRONAUT EVA MODE] <---> [ROBOTIC ROVER MODE] |  |
|  +---------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------+
                                           | HTTP / REST (JSON)
                                           v
+---------------------------------------------------------------------------------------+
|                                  APPLICATION API SERVICE                              |
|                          (src/marswalk/api/service.py & run_atlas.py)                 |
|                                                                                       |
|  - Request Validation & Physical Bounds Enforcement (Limits slope <= 45 deg, v > 0)  |
|  - Mode Router (Astronaut EVA vs. Rover Routing Dispatch)                             |
|  - Dynamic Hazard Injector & Contingency Lifecycle State Engine                       |
|  - Geospatial Coordinate Transformation (Lon/Lat WGS-84/Mars Sphere <-> DEM Row/Col)  |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                               CORE COMPUTATIONAL ENGINES                              |
|                                                                                       |
|  +-----------------------------------+   +------------------------------------------+ |
|  | ASTRONAUT EVA ENGINE              |   | ROVER NAVIGATION ENGINE                  | |
|  | (src/marswalk/core/astronaut_eva) |   | (src/marswalk/core/planner.py)           | |
|  |                                   |   |                                          | |
|  | - Directional Slope Work Engine   |   | - Mechanical Tilt & Tip-Over Risk Model  | |
|  | - Outbound vs Return Separation   |   | - Wheel Sinkage / Slip Heuristic Model   | |
|  | - PLSS Consumables & O2 Burn      |   | - Solar Illumination & Power Generation  | |
|  | - Multi-Factor A* Search          |   | - 8-Neighbor Grid Traversability         | |
|  +-----------------------------------+   +------------------------------------------+ |
|                                                                                       |
|  +-----------------------------------+   +------------------------------------------+ |
|  | ENVIRONMENTAL INTELLIGENCE       |   | TERRAIN INTELLIGENCE                     | |
|  | (src/marswalk/core/weather.py)    |   | (src/marswalk/core/terrain.py)           | |
|  |                                   |   |                                          | |
|  | - MEDA Dust Optical Depth (Tau)   |   | - 1m HiRISE DEM Micro-Topography         | |
|  | - Diurnal Thermal Cycles          |   | - 20m CTX Regional Mosaic Context        | |
|  | - Sol 89 Dust Storm Preset        |   | - Instantaneous Gradient & Normal Vector | |
|  +-----------------------------------+   +------------------------------------------+ |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                  DATA & PERSISTENCE LAYER                             |
|                                                                                       |
|  - USGS HiRISE DEM (data/raw/jezero_dem_1m.tif / data/processed/terrain/)             |
|  - NASA PDS MEDA Atmospheric Records (data/processed/weather/meda_processed.json)     |
|  - Mars Climate Database v6.1 Radiation & Temperature Grids                           |
|  - Perseverance Traversals & Waypoints (data/processed/waypoints_jezero.json)         |
+---------------------------------------------------------------------------------------+
```

---

### 2. Core Algorithmic Formulations

#### 2.1 Multi-Factor A* Heuristic Search
Traversals are planned across an 8-connected grid derived from the elevation model. The path cost between adjacent grid cells $u = (r_1, c_1)$ and $v = (r_2, c_2)$ is given by:

$$C(u, v) = d_{\text{step}}(u, v) \times \Phi(\Delta z, d_{2\text{D}}) \times \Psi(m_{\text{gear}}, m_{\text{astronaut}}) \times W_{\text{profile}}$$

Where:
- $d_{2\text{D}} = \text{cell\_size} \times \sqrt{(r_2 - r_1)^2 + (c_2 - c_1)^2}$ is horizontal step distance.
- $\Delta z = z(v) - z(u)$ is elevation change.
- $\theta = \arctan\left(\frac{|\Delta z|}{d_{2\text{D}}}\right)$ is local incline.
- If $\theta > \theta_{\text{cutoff}}$ or if $\Delta z \in \{\text{NaN}, \pm\infty\}$, step cost $C(u, v) = \infty$.
- $\Phi(\Delta z, d_{2\text{D}}) = 1.0 + \max\left(0, \frac{\theta}{\theta_{\text{cutoff}}}\right)^2 \times 3.0$ models slope resistance.
- $\Psi(m_{\text{gear}}, m_{\text{astronaut}}) = 1.0 + \frac{m_{\text{gear}}}{m_{\text{astronaut}}}$ accounts for payload/suit mass penalties.
- Heuristic function $h(v, \text{goal}) = d_{\text{Euclidean}}(v, \text{goal})$ satisfies admissibility and consistency ($h(u) \le c(u, v) + h(v)$), guaranteeing optimal path discovery.

#### 2.2 Disaggregated Bidirectional Trajectory Modeling
To avoid the dangerous pitfall of assuming symmetric terrain costs, MarsWalk independently plans:
1. **Outbound Leg:** Start point $S \to$ Science Target $T$ with uphill/downhill step transitions $\Delta z_k = z_{k+1} - z_k$.
2. **Return Leg:** Science Target $T \to$ Habitat Base $S$ with inverted step transitions $\Delta z'_k = z_k - z_{k+1} = -\Delta z_k$.
3. **Dwell Phase:** Fixed stationary duration at $T$ consuming oxygen and life-support energy at resting metabolic rate.

#### 2.3 PLSS Consumable Integration & Margin Verification
During each excursion, the total oxygen consumed is integrated:

$$O_{2, \text{consumed}} = \sum_{k \in \text{Outbound}} \left(\frac{d_k}{v_{\text{walk}}} \times \dot{V}_{O_2, \text{walk}}\right) + \sum_{k \in \text{Return}} \left(\frac{d_k}{v_{\text{walk}}} \times \dot{V}_{O_2, \text{walk}}\right) + t_{\text{dwell}} \times \dot{V}_{O_2, \text{rest}}$$

The sortie is marked as **Feasible** if and only if:
1. Both Outbound and Return paths are reachable.
2. $O_{2, \text{capacity}} - O_{2, \text{consumed}} \ge O_{2, \text{reserve}}$ (where $O_{2, \text{reserve}} = 0.20 \times O_{2, \text{capacity}}$).
3. $t_{\text{outbound}} + t_{\text{dwell}} + t_{\text{return}} \le t_{\text{max\_sortie}}$.

#### 2.4 Multi-State Contingency Lifecycle
The mission resilience state engine implements deterministic transitions:
```
[NOMINAL]  --->  [CAUTION]  --->  [SAFE_HOLD]  --->  [RETURN_TO_BASE]  --->  [COMPLETED]
    |               |                 |                      |
    +---------------+-----------------+----------------------+---> [MISSION_ABORTED]
```
- **Dust Opacity Trigger:** Optical depth $\tau$ derived from MEDA sensors:
  - $\tau < 1.5$: `NOMINAL`
  - $1.5 \le \tau < 3.0$: `CAUTION` (Crew alerted, continue with monitoring)
  - $\tau \ge 3.0$: `RETURN_TO_BASE` (Immediate abort, alternate return path generated)
- **Life Support Margin Trigger:** Usable oxygen $< 20\%$ triggers immediate `RETURN_TO_BASE`.

---

### 3. Rendering Pipeline & Visualization Stack

- **Dual-Track Polylines:** In the Three.js 3D viewport:
  - **Outbound Track:** Rendered in solid Gold/Amber (`#fbbf24`) with an elevation offset of $+5.0\text{ m}$ above the DEM mesh.
  - **Return Track:** Rendered in high-contrast Cyan (`#06b6d4`) with an elevation offset of $+7.5\text{ m}$.
  - The $+2.5\text{ m}$ vertical delta between tracks eliminates WebGL depth-buffer fighting (z-fighting) and allows astronauts and evaluators to clearly trace both segments even when retracing the exact same canyon corridor.
- **Visor HUD Overlay:** Positioned as an ergonomic astronaut helmet display showing real-time physiological indicators (Oxygen bar, Kcal burn, Contingency state pill, and Advisory guidance).
