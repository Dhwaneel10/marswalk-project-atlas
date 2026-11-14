# MarsWalk 2.0 — Milestone 11G Technical Design Document
## Campaign Performance Analytics, Deviation Analysis & Lessons Learned

**Milestone:** 11G (MarsWalk 2.0 V2)  
**Status:** In Progress / Implementation Phase  
**Author:** Antigravity / MarsWalk Planetary Engineering Team  
**Date:** 2026-10-29  
**Target Environment:** Mars (IAU 2000 Planetocentric Sphere / USGS CTX DTM 20m Jezero Crater Topography)  

---

## 1. Overview & Problem Statement

Across Milestones 11A–11F, MarsWalk has evolved from individual-sortie planning into a comprehensive multi-sol planetary campaign system featuring:
- Resource-bounded multi-sol scheduling and topological DAG prerequisite enforcement (11A).
- In-situ science observation logging and execution progress tracking (11B).
- Dynamic observation-driven intelligence and adaptive science reprioritization (11C).
- Deterministic campaign what-if simulation scenario sweeps (11D).
- Multi-agent fleet coordination and task responsibility handoffs (11E).
- Event-driven campaign digital twin simulation with temporal conflict detection (11F).

However, during execution and rehearsal, **simulated reality often diverges from the planned baseline**:
- Traversing through steep terrain can take longer than budgeted.
- Equipment anomalies or dust accumulation trigger unexpected operational holds.
- Tasks are blocked because upstream observations were postponed or inconclusive.
- Fleet units experience uneven workload distribution or mobility limitations.

**Milestone 11G delivers the Campaign Performance Analytics, Deviation Analysis & Lessons Learned Engine**:
A deterministic, evidence-backed diagnostic suite that reconciles scheduled campaign baselines against simulated execution runs, pinpoints root causes of schedule slippage, identifies bottlenecks, and generates actionable, grounded recommendations for subsequent mission campaigns.

> **Crucial Reality Boundary**: This analytics engine operates on deterministic simulation models and recorded event histories. It does NOT represent live telemetry from active spacecraft or actual physical science discoveries.

---

## 2. Core Metrics & Accounting Principles

### 2.1 Traceable Performance Metrics
Every calculated metric has an explicit definition, physical SI units, data source provenance, and missing-data behavior:

| Metric Category | Specific Metrics | Formula / Definition | Units |
|---|---|---|---|
| **Temporal Duration** | Planned Duration ($T_{\text{plan}}$), Simulated Duration ($T_{\text{sim}}$), Schedule Delta ($\Delta T$) | $\Delta T = T_{\text{sim}} - T_{\text{plan}}$ | Seconds ($\text{s}$), Sols |
| **Sortie Timings** | Sortie Start Slip ($\Delta t_{\text{start}}$), Sortie End Slip ($\Delta t_{\text{end}}$) | $t_{\text{sim, start}} - t_{\text{plan, start}}$ | Seconds ($\text{s}$) |
| **Target Outcomes** | Completed, Deferred, Blocked, Unallocated, Repeat Counts | Set cardinality across target state machines | Count, % |
| **Priority Coverage** | High/Medium/Low Priority Target Completion Rates | $\frac{N_{\text{completed}}(P)}{N_{\text{total}}(P)} \times 100\%$ | % |
| **Operational Holds** | Total Hold Count, Total Hold Duration | $\sum t_{\text{hold}}$ across logged hold events | Count, Seconds |
| **Fleet Utilization** | Active Traverse Time, Dwell Time, Idle/Depot Time per Unit | Active time / Total campaign duration | Seconds, % |
| **Traverse & Energy** | Total Traverse Distance, Cumulative Elevation Climb, Energy | Summed along route legs | Meters ($\text{m}$), $\text{kWh}$ |
| **Handoff Metrics** | Proposed, Validated, Executed, Rejected Counts | Rejection rate = $\frac{N_{\text{rejected}}}{N_{\text{total}}}$ | Count, % |
| **Temporal Conflicts** | Blocker, Warning, Info Counts | Count of detected conflicts from 11F engine | Count |

### 2.2 Accounting Invariants
1. **Zero Double-Counting**: Traverse legs, target dwell intervals, and operational holds are mutually exclusive and counted exactly once.
2. **Comparable Baselines**: Plans with mismatched target sets, unit fleet compositions, or locomotion models cannot be directly diffed without explicit mismatch attribution.
3. **No Fabricated Data**: If an environmental sensor or power variable was not modeled, it remains strictly `null` and is not synthetic.

---

## 3. Deviation & Root Cause Analysis

The deviation engine identifies variance between the scheduled plan and simulated execution:

### 3.1 Deviation Codes
- **`DEV_SORTIE_DELAYED`**: Sortie departed or completed later than planned ($\Delta t > 60\text{ s}$).
- **`DEV_PREREQUISITE_BLOCKED`**: Task could not proceed because an upstream prerequisite target was incomplete or postponed.
- **`DEV_TARGET_INACCESSIBLE`**: Target was blocked by a terrain obstacle, slope limit, or corridor closure.
- **`DEV_UNIT_UNAVAILABLE`**: Exploration unit went offline or was busy with higher-priority tasks.
- **`DEV_CORRIDOR_DETOUR`**: Route leg distance or traverse time expanded due to detour pathfinding.
- **`DEV_REPLAN_ORDER_CHANGE`**: Dynamic replanning reordered the sequence of targets.
- **`DEV_HANDOFF_REJECTED`**: Task responsibility handoff failed validation.
- **`DEV_UNRESOLVED_HORIZON`**: Target remained unscheduled or incomplete when simulation horizon was reached.

### 3.2 Cause Attribution Classification
Each deviation is categorized into one of three strict causal levels:
- **`CONFIRMED_CAUSE`**: Explicitly demonstrated by an unbroken chain of recorded simulation events (e.g. an operational hold event directly pushed the departure time back by the hold duration).
- **`CONTRIBUTING_FACTOR`**: Influenced the outcome but was accompanied by other compounding factors (e.g. terrain slope reduced speed while a brief hold also occurred).
- **`UNDETERMINED`**: The variance exists, but the event history contains insufficient evidence to attribute a single definitive root cause.

---

## 4. Evidence-Grounded Lessons Learned

Recommendations are synthesized directly from verified deviations and objective dependencies:

| Recommendation Category | Trigger Condition | Generated Recommendation | Expected Impact |
|---|---|---|---|
| **`TIME_BUDGET`** | $\Delta T > 0$ with active sortie overruns | Increase sortie time envelope by $\Delta T + 10\%$ buffer or reduce target count | Eliminates sortie deadline violations |
| **`COORDINATION_STRATEGY`** | Rover assigned steep targets ($>15^\circ$) or uneven workload | Switch fleet coordination strategy to `capability_first` or `balanced_workload` | Matches platform slopes and balances wear |
| **`TASK_SEQUENCING`** | Downstream targets delayed waiting for prerequisites | Reorder eligible DAG targets to execute independent science while prerequisite completes | Reduces idle waiting by up to 30% |
| **`SCENARIO_COVERAGE`** | Mission unverified against specific hazard class | Evaluate what-if scenarios (e.g. `mobility_change` or `corridor_closure`) in What-If Lab | Improves operational robustness |
| **`UNIT_ASSIGNMENT`** | Unit experienced high rejection rate on handoffs | Reassign target responsibility to capable platform or revise handoff window | Ensures target completion |

Recommendations are purely advisory and include a structured `proposed_change` payload. Applying a recommendation creates a new campaign plan version (`v{n+1}`), preserving all previous plans and records.

---

## 5. Atlas Web Application Integration

A 7th tab (`#campaignAnalyticsView`) is added to the Campaign Orchestrator:
- **Header Toolbar**: Campaign & Simulation Selectors, `ANALYZE CAMPAIGN` button.
- **Executive Summary KPI Tiles**: Duration Delta, Target Completion Rate, Total Traverse, Fleet Utilization, Operational Holds.
- **Sortie Timeline Deviation Table**: Planned vs Simulated start, end, and duration with color-coded variance indicators.
- **Deviation & Cause Inspector**: Expandable cards displaying deviation code, severity, planned vs simulated values, cause classification (`CONFIRMED`, `CONTRIBUTING`, `UNDETERMINED`), and triggering event citations.
- **Unit Workload & Efficiency Breakdown**: Visual comparative bars for each platform showing active traverse, dwell, and idle durations.
- **Lessons Learned Action Center**: Grounded recommendation cards with category badges, supporting evidence citations, expected impacts, and review status toggles (`ACTIVE` / `REVIEWED`).
- **Export Action**: One-click JSON export of the complete analysis report.

---

## 6. Verification Plan & Test Strategy

- **Module**: `tests/test_milestone_11g_campaign_analytics.py`
- Target: 16+ comprehensive unit and integration tests covering:
  1. Identical baseline and simulation producing zero unexplained deviations.
  2. Accurate duration delta and schedule slip calculations with explicit SI units.
  3. Target outcome counts (completed, deferred, blocked, unallocated) and priority coverage.
  4. Unit workload and utilization calculations without double-counting.
  5. Cause attribution classification (`confirmed_cause`, `contributing_factor`, `undetermined`).
  6. Grounded lessons learned recommendations with evidence references.
  7. Recommendation review status updates (`active`, `reviewed`, `dismissed`).
  8. Incompatible baseline/simulation detection and graceful error handling.
  9. Draft 2020-12 schema validation against `schemas/api/v1/campaign-analytics.schema.json`.
  10. Workspace persistence, reload, and API service roundtrip.
  11. Full regression across all existing milestones (11A–11F, 600 tests).
