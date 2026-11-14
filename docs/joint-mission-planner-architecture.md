# Milestone 13E — Atlas Joint Mission Co-Design: Architecture Specification

**System:** MarsWalk 2.0 / Project Atlas  
**Component:** Joint Mission Co-Design Engine & Architecture (`src/marswalk/core/joint_mission_planner.py`)  
**Specification Version:** 1.0.0  
**Status:** Validated Release Candidate  
**Date:** 2026-10-31  

---

## 1. System Overview & Problem Statement

Prior to Milestone 13E, Project Atlas operated two independent optimization pipelines:
1. **Kinematic Traverse Planning (`src/marswalk/core/planner.py`):** Minimized physical path distance, local slope penalties (Horn 3x3 filter), and Apollo Waligora metabolic cost across authentic USGS CTX 20m Jezero topography.
2. **Communications Network Planning (`src/marswalk/core/relay_planner.py`):** Selected topographic promontories for surface relay towers to maximize static or route-adjacent geometric line-of-sight coverage.

In operational reality, these domains are deeply coupled:
- The optimal route from a terrain cost perspective often follows canyon beds or scarp floors, causing severe terrain occlusion and communications blackout.
- The route with best line-of-sight often follows exposed ridge crests with high slope penalties and unacceptable metabolic strain.
- Deploying field relays costs logistics mass and time, creating a multi-objective trade-off between traverse distance, blackout duration, and deployed infrastructure.

Milestone 13E resolves this architectural decoupling by introducing the **Atlas Joint Mission Co-Design System**, where candidate traverses and surface relay deployments are synthesized and evaluated simultaneously over a non-dominated Pareto frontier.

```
                           +-------------------------------------+
                           |         JointMissionInput           |
                           | (Endpoints, Slopes, Comms, Weights) |
                           +------------------+------------------+
                                              |
                                              v
                           +-------------------------------------+
                           |    Candidate Traverse Generator     |
                           |  (Multi-Heuristic A* + Jaccard Dedup)|
                           +------------------+------------------+
                                              |
                                              v
                           +-------------------------------------+
                           |   Submodular Relay Deployment Sweep |
                           |  (LOS Raycasting + Greedy Selection)|
                           +------------------+------------------+
                                              |
                                              v
                           +-------------------------------------+
                           |   Dimensional Metric Normalization  |
                           |   (Range-Independent Normalization) |
                           +------------------+------------------+
                                              |
                                              v
                           +-------------------------------------+
                           |  Pareto Non-Dominated Extraction    |
                           |  (Kung's Frontier Filter + MRS)     |
                           +------------------+------------------+
                                              |
                     +------------------------+------------------------+
                     |                                                 |
                     v                                                 v
+---------------------------------------+   +---------------------------------------+
|        REST API Service Layer         |   |         3D Mission Theater            |
|  (/api/joint-mission/evaluate, ...)   |   |   (Selected Ribbon, Gaps, Beams)      |
+---------------------------------------+   +---------------------------------------+
```

---

## 2. Core Modules & Inter-Module Coordination

The Joint Mission Planner orchestrates six foundational MarsWalk subsystems:

| Subsystem | Source Module | Role in Joint Co-Design |
| :--- | :--- | :--- |
| **Topographic DTM Engine** | `src/marswalk/core/terrain.py` | Supplies authentic 20m anisotropic elevation grid ($dx = 18.9729\text{ m}, dy = 20.0\text{ m}$) from USGS CTX DTM Jezero Crater (DOI `10.5066/P906QQT8`). |
| **Kinematic Route Planner** | `src/marswalk/core/planner.py` | Generates candidate traverse corridors using multi-objective A* with varied slope weights, waypoint sequences, and Apollo Waligora metabolic cost derating. |
| **Geometric LOS Raycasting** | `src/marswalk/core/terrain_visibility.py` | Evaluates true 3D line-of-sight ray clearance against local topography sampled along candidate trajectories. |
| **Relay Topology Graph** | `src/marswalk/core/relay_graph.py` | Builds visibility graphs, computes Tarjan bridges and articulation points, and evaluates multi-hop connectivity paths. |
| **Submodular Relay Optimizer** | `src/marswalk/core/relay_planner.py` | Solves the NP-hard maximum visibility coverage problem using a $(1 - 1/e)$-approximate submodular greedy algorithm over candidate promontories. |
| **Dynamic Timeline Twin** | `src/marswalk/core/mission_connectivity.py` | Evaluates time-indexed carrier beam handovers, instantaneous LOS clearance margins, and duration of blackout segments. |

---

## 3. Data Contracts & Schemas

The joint planner exchanges structured data validated against Draft 2020-12 JSON schemas:
- `schemas/api/v1/joint-mission-optimization.schema.json`
- `schemas/api/v1/joint-mission-evaluation.schema.json`

### 3.1 Input Contract (`JointMissionInput`)
```python
@dataclass
class JointMissionInput:
    start_rc: tuple[int, int]
    goal_rc: tuple[int, int]
    intermediate_waypoints: list[dict] = field(default_factory=list)
    max_relays_budget: int = 2
    weights: dict[str, float] = field(default_factory=lambda: {
        "distance": 0.30,
        "gap_duration": 0.35,
        "relay_cost": 0.20,
        "metabolic_energy": 0.15
    })
    antenna_mast_rover_m: float = 2.5
    antenna_mast_base_m: float = 10.0
    antenna_mast_relay_m: float = 8.0
    max_gap_duration_s: float = 900.0
    vehicle_platform: str = "perseverance_rover"
```

### 3.2 Output Contract (`JointMissionOptimizationResult`)
- `optimization_id`: Unique deterministic UUID.
- `recommended_candidate`: Top-ranked candidate based on scalar multi-objective score.
- `pareto_candidates`: Non-dominated efficiency frontier candidates ($k \in [1, 5]$).
- `all_candidates`: Full set of evaluated co-design configurations (3 to 8 candidates).
- `computation_time_ms`: Execution latency ($< 850\text{ ms}$).
- `dataset_provenance`: Formal USGS citation, DOI, and SHA-256 integrity hash.

---

## 4. API Endpoints Reference

The Atlas REST API exposes five dedicated endpoints:

1. `POST /api/joint-mission/optimize`
   - Executes the complete co-design pipeline.
   - Generates candidate traverses, evaluates line-of-sight, optimizes relay placement, extracts the Pareto frontier, and computes decision rationale.
2. `POST /api/joint-mission/evaluate`
   - Evaluates a specific pre-defined traverse and relay deployment configuration without running candidate generation.
3. `GET /api/joint-mission/configurations`
   - Lists stored co-design configurations from `data/workspaces/joint_missions/`.
4. `POST /api/joint-mission/compare`
   - Performs a side-by-side marginal trade-off comparison between two candidate IDs.
5. `POST /api/joint-mission/promote`
   - Promotes a selected co-design candidate to the active mission plan, updating Cockpit and Mission Theater state machines.

---

## 5. Scientific Truth & Provenance Disclosures

1. **Topographic Base:** All elevation queries use the authentic USGS Jezero 20m DTM (DOI: `10.5066/P906QQT8`, SHA-256: `875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3`).
2. **Planetary Spheroid:** Planetary curvature uses the IAU 2000 Mars Spheroid ($R = 3,396,190\text{ m}$).
3. **Geometric Line-of-Sight vs RF Propagation:** Modeled visibility reflects optical/geometric line-of-sight clearance. Without an empirical RF propagation model (Fresnel diffraction, multipath scattering, regolith attenuation), geometric visibility does not certify RF link margin or throughput.
4. **Safety Disclaimers:** All modeled traverses and relay meshes are deterministic decision-support heuristics and are **NOT certified astronaut flight paths**.
