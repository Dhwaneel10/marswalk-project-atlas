# MarsWalk 2.0 — Milestone 11E Architectural & Technical Design
## Multi-Agent Campaign Coordination & Resource Handoffs

**Milestone:** 11E (MarsWalk 2.0 V2)  
**Status:** IMPLEMENTATION PHASE  
**Date:** 2026-10-29  
**Target Environment:** Mars (IAU 2000 Sphere / USGS CTX DTM 20m Jezero Crater Topography)  
**Safety & Scientific Disclaimer:** Mathematical planning simulation for multi-asset exploration analysis. Does NOT represent actual autonomous rover control, flight-certified operational decision software, or physical sample/power transfer between vehicles.

---

## 1. System Overview & Problem Statement

Milestones 11A–11D established single-asset multi-sol planetary campaign scheduling, observation registries, closed-loop science prioritization, and what-if simulation on authentic 20m USGS CTX Jezero Crater topography.

In realistic planetary missions, surface campaigns may deploy heterogeneous robotic and crewed assets (e.g. robotic rovers like Perseverance paired with crewed EVA sorties or scout micro-rovers). These assets exhibit substantially different locomotion physics, daily life-support budgets, slope climbing envelopes, and operational windows:
- **Crew EVA**: Locomotion speed 2.0 km/h (0.556 m/s), maximum sortie duration 28,800 s (8 hours), slope ceiling 25.0°, high dexterity.
- **Robotic Rover**: Drive velocity 0.035 m/s (~0.126 km/h), maximum drive duration 14,400 s (4 hours), slope ceiling 15.0°, persistent instrument payloads.
- **Scout Rover**: Drive velocity 0.070 m/s (~0.252 km/h), maximum drive duration 10,800 s (3 hours), slope ceiling 20.0°, reconnaissance imaging.

### Core Objectives for Milestone 11E
1. **Versioned Exploration-Unit Model**: Explicit asset definitions (`ExplorationUnit`) with verified locomotion physics, availability windows, starting locations, and explicit capabilities.
2. **Multi-Unit Task Allocation Engine**: Deterministic assignment of candidate targets and daily sorties across available units, respecting DAG prerequisite dependencies, terrain slope ceilings, and daily duration limits.
3. **Coordination Strategy Trade-off Engine**: Side-by-side evaluation of genuinely different allocation philosophies:
   - `priority_first`: Greedy science maximization.
   - `balanced_workload`: Equalized duration and distance distribution across units.
   - `capability_first`: Matching targets to asset slope and speed capabilities.
4. **Explicit Task Responsibility Handoffs**: Formal event model (`TaskHandoff`) transferring responsibility for a target between units with rigorous precondition checking, validation, and rejection diagnostics.
5. **Multi-Asset What-If Simulation**: Scenario modeling for unit incapacitation/loss, mobility deratings, and corridor closures with re-allocation analysis.
6. **Controlled Version Promotion & Zero Data Loss**: Promotion of a coordinated plan to the next campaign version (`v1` $\rightarrow$ `v2`) with complete audit trails and baseline preservation.

---

## 2. Exploration-Unit Model

```python
class UnitType(str, enum.Enum):
    ROBOTIC_ROVER = "robotic_rover"
    CREW_EVA = "crew_eva"
    SCOUT_ROVER = "scout_rover"

class UnitStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    UNAVAILABLE = "UNAVAILABLE"
    MAINTENANCE = "MAINTENANCE"
    RETIRED = "RETIRED"
```

### Supported vs. Non-Modeled Capabilities
| Capability | Status | Planning Model |
| :--- | :--- | :--- |
| **Surface Traversal** | Supported | Authentic A* pathfinding on USGS CTX 20m DTM |
| **Slope Thresholding** | Supported | Unit-specific slope ceiling cutoffs (15° vs 25°) |
| **Duration Budgeting** | Supported | Per-sortie limits (e.g. 14,400s vs 28,800s) |
| **Dwell Time Sampling** | Supported | Stationary sampling duration deduction |
| **Availability Windows** | Supported | Active sol bounds (`start_sol` to `end_sol`) |
| **Physical Sample Transfer** | *Not Modeled* | Explicitly tagged `UNSUPPORTED` (task responsibility transfer only) |
| **Direct Power Tethering** | *Not Modeled* | Explicitly tagged `UNSUPPORTED` |
| **Inter-Vehicle Towing** | *Not Modeled* | Explicitly tagged `UNSUPPORTED` |

---

## 3. Allocation Engine & Topological Dependency Enforcement

For a multi-unit campaign, targets form a directed acyclic graph (DAG) of prerequisite constraints:
$$T_j \text{ requires } T_i \implies \text{Sol}(T_i) \le \text{Sol}(T_j) \text{ and } \text{Order}(T_i) < \text{Order}(T_j) \text{ if } \text{Sol}(T_i) = \text{Sol}(T_j)$$

### Allocation Rules:
1. **DAG Prerequisite Validation**: A target cannot be allocated to any unit on Sol $s$ unless all its prerequisite targets are either:
   - Already marked `COMPLETED` in campaign history, or
   - Scheduled on an earlier sol ($< s$), or
   - Scheduled on the same sol ($s$) by the same unit prior to that target.
2. **Mutual Exclusion**: No two units can be assigned the same target on the same sol unless repeat observation is explicitly requested.
3. **Terrain Slope Feasibility**: If the slope along the access path or at the target exceeds $\theta_{\max,\text{unit}}$, the target is marked `UNREACHABLE` for that unit.
4. **Duration Feasibility**: If adding a target exceeds `max_duration_per_sortie_s`, it is deferred to subsequent sols or units.
5. **Availability Window**: Unit $u$ cannot accept sorties on Sol $s$ if $s \notin [u.\text{start\_sol}, u.\text{end\_sol}]$.

---

## 4. Coordination Strategy Profiles

1. **Priority-First**:
   - Sorts unallocated candidate targets by descending priority score.
   - Assigns each target to the first feasible unit with available sol capacity.
   - Maximizes immediate science yield.
2. **Balanced-Workload**:
   - Calculates target load dynamically and allocates targets to the unit with the least cumulative duration so far.
   - Equalizes physical wear, driving time, and operational burden.
3. **Capability-First**:
   - Assigns steep-slope targets ($> 15^\circ$) and distant targets preferentially to high-mobility assets (Crew EVA).
   - Assigns high-dwell, low-slope sedimentary sampling targets to Robotic Rovers.

---

## 5. Task Responsibility Handoff Model

```
Source Unit (e.g. unit_perseverance)
       │
       ▼ [PROPOSED HANDOFF] (Target T-03)
       │
Preconditions Check:
 - Recipient unit available on Sol s?
 - Recipient unit max slope >= target slope?
 - Recipient unit duration margin sufficient?
 - Prerequisite DAG valid under handoff?
       │
       ├─► [PASSED] ──► [ACCEPTED] ──► Task transferred to Recipient Unit
       │
       └─► [FAILED] ──► [REJECTED] ──► Task retained by Source Unit
                                      (Diagnostic explanation recorded)
```

---

## 6. REST API Endpoints

- `POST /api/campaign/coordinate`: Generates multi-unit coordination proposals and strategy comparisons.
- `GET /api/campaign/coordination`: Lists persisted coordination plans with optional `campaign_id` filter.
- `POST /api/campaign/handoff`: Proposes or executes a task responsibility handoff between units.
- `GET /api/campaign/handoffs`: Lists historical handoff records.
- `POST /api/campaign/coordination/apply`: Promotes a coordinated multi-unit plan to the next campaign version.
