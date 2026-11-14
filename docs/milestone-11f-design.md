# MarsWalk 2.0 — Milestone 11F Technical Design Document
## Campaign Digital Twin, Multi-Unit Timeline & Temporal Execution Simulation

**Milestone:** 11F (MarsWalk 2.0 V2)  
**Status:** In Progress / Implementation Phase  
**Author:** Antigravity / MarsWalk Planetary Engineering Team  
**Date:** 2026-10-29  
**Target Environment:** Mars (IAU 2000 Planetocentric Sphere / USGS CTX DTM 20m Jezero Crater Topography)  

---

## 1. Overview & Problem Statement

Mars surface exploration campaigns schedule multiple sorties across multiple Martian sols (days). In Milestone 11E, MarsWalk gained the capability to coordinate multiple simulated exploration units (e.g. robotic rovers and crew EVA teams) across candidate targets. 

However, static schedules do not capture the **temporal dynamics** of execution:
- How does a campaign unfold as a function of continuous simulated time $t$?
- Where is each vehicle or crew member located at any given moment along their planned route?
- Are tasks overlapping in time on the same unit (double-booking)?
- Does a unit attempt to sample a science target before its prerequisite observations have finished?
- What happens when an operational delay, hardware fault, or corridor rockfall interrupts execution at simulation time $t_{\text{int}}$?

Milestone 11F builds the **Campaign Digital Twin**: a deterministic, event-driven temporal simulation engine that executes a multi-unit campaign over simulated time, detects temporal scheduling conflicts, supports interactive simulation controls (advance, step, seek, pause, reset), handles interruptions with historical prefix freezing, and provides a multi-lane Gantt timeline visualization in Project Atlas.

> **Crucial Reality Boundary**: The Campaign Digital Twin is a deterministic simulation model for mission planning and rehearsal. It is NOT a live telemetry feed, real-time autonomous vehicle control system, or flight-certified operations software.

---

## 2. Temporal Reference & Time Representation

### 2.1 Campaign Epoch & Time Units
- **`simulated_time_s`**: `float`, monotonic elapsed seconds from campaign departure ($t = 0.0\text{ s}$).
- **Campaign Epoch**: Sol 1 departure time, by default relative to campaign initialization (or explicit ISO-8601 UTC string `2026-10-29T00:00:00Z`).
- **Martian Sol Duration**: $T_{\text{sol}} = 88,775.244\text{ seconds}$ (standard Martian solar day).
- **Current Sol Computation**:
  $$\text{current\_sol} = 1 + \left\lfloor \frac{\text{simulated\_time\_s}}{88,775} \right\rfloor$$
- **Daily Sortie Start Offset**: Sorties on Sol $s$ begin at:
  $$t_{\text{sol\_start}}(s) = (s - 1) \times 88,775\text{ s} + t_{\text{ops\_offset}}$$
  where $t_{\text{ops\_offset}}$ defaults to $0.0\text{ s}$ (or configured EVA operational start offset).

### 2.2 Event Ordering & Deterministic Tie-Breaking
When multiple discrete events share the identical timestamp `simulated_time_s`, ties are resolved deterministically using a four-tier comparator:
1. `simulated_time_s` (ascending numerical order).
2. `event_priority` (ascending numerical priority: status change = 10, completion = 20, start = 30, departure = 40, conflict = 50).
3. `unit_id` (alphabetical string sort).
4. `event_id` (alphabetical string sort).

This guarantees 100% bit-exact event ordering across simulations with identical inputs.

---

## 3. Multi-Unit Task Interval Architecture

For each configured unit, its schedule is compiled into discrete, non-overlapping **Task Intervals** (`TimelineInterval`):

| Activity Type | Description | Start/End Model | Position Behavior |
|---|---|---|---|
| **`TRANSIT`** | Surface traverse along a calculated route leg | $t_{\text{start}}$, $t_{\text{end}} = t_{\text{start}} + \frac{d}{v}$ | Interpolated along route polyline cells; labeled `is_simulated_position=True` |
| **`DWELL`** | In-situ science observation & sampling | $t_{\text{start}}$, $t_{\text{end}} = t_{\text{start}} + t_{\text{dwell}}$ | Stationary at target waypoint coordinates |
| **`HOLD`** | Operational pause, ground wait, or weather stand-down | $t_{\text{start}}$, $t_{\text{end}} = t_{\text{start}} + t_{\text{hold}}$ | Stationary at current coordinates |
| **`HANDOFF`** | Task responsibility transfer window | $t_{\text{start}}$, $t_{\text{end}} = t_{\text{start}} + t_{\text{handoff}}$ | Units at current locations |
| **`REST` / `DEPOT`** | Overnight habitat dwell or turnaround between sols | End of sol sortie $\to$ start of next sol | Stationary at base / overnight habitat |

### Task States
- `PLANNED`: In schedule, not yet reached.
- `IN_PROGRESS`: Currently being executed at `current_time_s`.
- `COMPLETED`: Finished and verified.
- `BLOCKED`: Infeasible or prerequisite failed.
- `DEFERRED`: Postponed to a future sol or unassigned.
- `INTERRUPTED`: Aborted or halted due to an injected contingency.

---

## 4. Temporal Conflict Detection Engine

The simulation engine analyzes intervals and target DAG dependencies to flag scheduling conflicts before and during execution:

| Conflict Code | Severity | Trigger Condition | Corrective Recommendation |
|---|---|---|---|
| **`CONFLICT_UNIT_DOUBLE_BOOKED`** | **BLOCKER** | Single unit has overlapping active intervals ($[t_1, t_2] \cap [t_3, t_4] \neq \emptyset$) | Serialize tasks or reassign secondary task to another unit. |
| **`CONFLICT_TARGET_CONCURRENT_ACCESS`** | **BLOCKER** | Two units scheduled to dwell at the same target simultaneously without concurrency permission | Offset arrival times or designate secondary unit as scout. |
| **`CONFLICT_PREREQUISITE_VIOLATION`** | **BLOCKER** | Dependent target $B$ starts before prerequisite target $A$ completes ($t_{\text{start}, B} < t_{\text{end}, A}$) | Delay target $B$'s sortie or reorder sequence within sol. |
| **`CONFLICT_OUTSIDE_AVAILABILITY`** | **BLOCKER** | Unit task scheduled outside unit's active `AvailabilityWindow` (e.g. unit in maintenance or retired) | Reassign task to an available unit or expand availability window. |
| **`CONFLICT_DURATION_BUDGET_EXCEEDED`** | **WARNING** | Sortie active duration exceeds unit's `max_duration_per_sortie_s` or life-support consumables | Truncate sortie, reduce dwell time, or split targets across multiple sols. |
| **`CONFLICT_HANDOFF_UNAVAILABLE`** | **BLOCKER** | Handoff scheduled while source or receiving unit is offline or incapable of traversing to target | Cancel handoff or assign to alternative capable platform. |
| **`CONFLICT_ORPHANED_TASKS`** | **WARNING** | Unit goes offline leaving pending tasks unassigned | Trigger automated replanning to reallocate tasks to surviving fleet. |
| **`CONFLICT_MISSING_TEMPORAL_DATA`** | **WARNING** | Route leg distance or dwell duration missing or zero without explicit configuration | Recompute route metrics with valid terrain DTM. |

---

## 5. Simulation Control & Replay Service

The simulation service exposes deterministic state control:
- **`start(campaign_id, coordination_id, config)`**: Compiles campaign plan and coordination allocations into a discrete event queue, initialized at $t = 0.0$.
- **`advance(target_time_s)`**: Advances the simulation clock to `target_time_s`, processing all intervening events, updating vehicle coordinates, and logging completions.
- **`step(event_count=1)`**: Advances simulation clock to the timestamp of the next $N$ events.
- **`pause()`**: Halts automatic clock progression while preserving state.
- **`seek(target_time_s)`**: Reconstructs the exact simulation state at any historical timestamp without mutating recorded past.
- **`reset()`**: Reinitializes simulation run to $t = 0.0$, generating a clean audit record.

### Bounds & Protective Limits
- Maximum simulation time: 14 sols ($1,242,850\text{ s}$).
- Maximum event count: 5,000 events.
- Maximum step size: 1,000 events per call.

---

## 6. Contingency Injection & Dynamic Replanning Protocol

When a contingency occurs at simulation time $t_{\text{int}}$:
1. **Historical Prefix Freezing**:
   - All completed intervals and logged events prior to $t_{\text{int}}$ are permanently frozen and immutable.
   - Completed targets are preserved in the execution ledger.
2. **Dynamic Remaining Work Replanning**:
   - The engine isolates uncompleted candidate targets.
   - Re-runs the coordination and campaign planning algorithms starting from the units' current coordinates at $t_{\text{int}}$.
   - Surviving units are assigned reachable targets. Targets exceeding slope limits or duration budgets are classified as deferred or unassigned.
3. **Continuation Identity & Audit Traceability**:
   - Generates a new simulation revision (`sim_xxx_rev1`) linked to the original simulation ID.
   - Preserves complete operational provenance and delta comparison metrics.

---

## 7. Atlas Campaign Digital Twin UI

A 6th tab (`#campaignSimulationView`) is integrated into the Campaign Orchestrator:
- **Simulation HUD Toolbar**: Play/Pause, Step, Seek Scrubber, Reset, and Inject Interruption buttons.
- **Synchronized Simulation Clock**: Sol indicator and formatted elapsed time (`T+01d 03h 14m 20s`).
- **Multi-Lane Gantt Timeline**: Horizontal time lanes per unit with color-coded intervals:
  - Transit: Blue (`#38bdf8`)
  - Dwell: Emerald (`#10b981`)
  - Hold: Amber (`#f59e0b`)
  - Rest/Depot: Dark Slate (`#334155`)
  - Active Cursor: Neon Cyan scrubber line tracking current time.
- **Chronological Event Stream**: Real-time event ledger detailing departures, waypoint arrivals, dwell completions, handoffs, and conflicts.
- **Temporal Conflicts Inspector**: Interactive conflict cards with severity badges, affected units/targets, and recommendation text.
- **Map Synchronization**: The active unit's current position is displayed on the existing 3D Three.js terrain mesh using a distinct vehicle marker.

---

## 8. Verification Plan & Test Strategy

- **Module**: `tests/test_milestone_11f_campaign_simulator.py`
- Target: 16+ comprehensive tests verifying:
  1. Deterministic simulation reproducibility with identical inputs.
  2. Stable tie-breaking for simultaneous events.
  3. Time advancement, stepping, and pause/resume.
  4. Non-mutating state reconstruction during seek operations.
  5. Derived route position labeling (`is_simulated_position=True`).
  6. Accurate task duration and dwell time accounting without double-counting.
  7. Prerequisite DAG dependency enforcement.
  8. Temporal conflict detection (double-booking, concurrent access, prerequisite violation, availability window).
  9. Handoff execution and ownership history tracking.
  10. Contingency injection with historical prefix freezing.
  11. Dynamic replanning of remaining work following unit loss.
  12. Persistence and reload from workspace storage.
  13. Draft 2020-12 schema validation.
  14. REST API routes for simulation lifecycle and control.
  15. Atlas UI integration and clean JavaScript syntax.
  16. Full regression across existing milestones (11A–11E).
