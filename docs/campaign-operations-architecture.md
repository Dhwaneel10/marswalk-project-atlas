# Atlas Campaign Operations Director: Architecture & System Design
**MarsWalk 2.0 / Project Atlas • Milestone 13H**
**Standard Reference:** AIAA / IEEE Aerospace Multi-Sol Mission Planning Specification
**Topographic Datum:** USGS CTX 20m Jezero Crater DTM (DOI `10.5066/P906QQT8`), IAU 2000 Mars Spheroid ($R = 3,396,190\text{ m}$)

---

## 1. Executive Summary

Milestone 13H introduces the **Atlas Campaign Operations Director**, an operational architecture that orchestrates multi-sol Mars exploration campaigns. While previous milestones (13D Line-of-Sight & RelayNet, 13E Joint Traverse Co-Design, 13F Terramechanical Energy & Battery SOC, 13G Science Instrument Pairing & Byte Conservation) formulated individual sub-problem solvers, Milestone 13H provides closed-loop orchestration across multiple Martian sols ($N \ge 3$).

```
+----------------------------------------------------------------------------------------------------+
|                                    MISSION OPERATIONS CENTER (MOCC)                               |
+----------------------------------------------------------------------------------------------------+
|                                                  |                                                 |
|  1. MULTI-SOL SCHEDULING (Milestone 11A / 13H)   |  2. GEOMETRIC LINE-OF-SIGHT (Milestone 13D)      |
|     - Sol activity timeline decomposition        |     - Horn 3x3 DEM slope & LOS raycasting        |
|     - Sortie, science dwell, relay, bivouac      |     - Relay tower placement & backhaul link     |
|                                                  |                                                 |
|  3. JOINT TRAVERSE CO-DESIGN (Milestone 13E)     |  4. PHYSICAL RESOURCE MODELS (Milestone 13F)     |
|     - Pareto candidate frontier ranking          |     - Bekker-Wong terramechanics (g = 3.71)      |
|     - Multi-objective utility scalarization      |     - Usable battery capacity & non-regen SOC    |
|                                                  |                                                 |
|  5. SCIENCE RETURN & LEDGER (Milestone 13G)      |  6. ADAPTIVE EVENT REPLANNER (Milestone 13H)    |
|     - First-law byte conservation                |     - Idempotent SHA-256 event log deduplication|
|     - Turret arm singularity protection          |     - Delta comparison table & atomic promotion  |
+--------------------------------------------------+-------------------------------------------------+
```

---

## 2. Invariants & Planetary Science Guardrails

1. **Non-Regenerative Terramechanics Invariant:**
   Per Martian rover mechanical drive guidelines (Perseverance / Curiosity), descent gravitational potential energy is dissipated as frictional heat in the harmonic gearhead dampers. Regenerative energy absorption into the battery is strictly zero ($\eta_{\text{regen}} = 0.0$).
2. **First-Law Byte Conservation Invariant:**
   Solid-state storage utilization satisfies $S_{\text{used}}(t) = S_{\text{gen}}(t) - S_{\text{rel}}(t)$. No data volume is deleted or evicted until positive transfer acknowledgement (`TRANSFER_COMPLETED`) is confirmed.
3. **Cross-Sol Battery Recharge Invariant:**
   At day boundary Sol $N \to N+1$, battery capacity charges via overnight RTG/solar trickle:
   $$E_{\text{start}}(N+1) = \min(E_{\text{cap}}, E_{\text{end}}(N) + E_{\text{recharge}})$$
   Recharge cannot exceed physical cell capacity ($E_{\text{cap}} = 4,800\text{ Wh}$ nominal).
4. **Relay Persistence Invariant:**
   Relay masts deployed on earlier sols remain spatial obstacles and active RF transceivers in the terrain visibility graph for all subsequent sols unless a specific outage event is injected.
5. **Human Non-Probabilistic Operator Truth:**
   Modeled traverse durations and science priorities reflect human operator mission design heuristics, NOT certified flight telemetry or autonomous life-critical execution paths.

---

## 3. Subsystem Breakdown

### 3.1 `CampaignOperationsDirector` (`src/marswalk/core/campaign_operations_director.py`)
- **Lifecycle Management:** Orchestrates states: `PLANNED`, `READY_FOR_REVIEW`, `APPROVED_FOR_SIMULATION`, `EXECUTING_SIMULATION`, `PAUSED`, `REQUIRES_REPLANNING`, `COMPLETED`, `FAILED_CONSTRAINTS`.
- **Event Engine:** Evaluates 19 distinct `CampaignEventType` events with cryptographic SHA-256 idempotency.
- **Cross-Sol Carryover:** Propagates state vectors (SOC, storage queue, target completion list, infrastructure graph) across discrete sols.
- **Adaptive Replanner:** Generates bounded alternative routes within $< 2.0\text{ s}$ latency budget.

### 3.2 Draft 2020-12 Contract Schemas
- `schemas/api/v1/campaign-operations.schema.json`
- `schemas/api/v1/campaign-operations-event.schema.json`

### 3.3 HTTP Service Routes (`src/marswalk/api/service.py`)
- `POST /api/campaign-operations/create`
- `GET /api/campaign-operations/list`
- `GET /api/campaign-operations/{id}`
- `POST /api/campaign-operations/{id}/plan`
- `POST /api/campaign-operations/{id}/execute-event`
- `POST /api/campaign-operations/{id}/advance-sol`
- `POST /api/campaign-operations/{id}/replan`
- `POST /api/campaign-operations/{id}/scenario`
- `GET /api/campaign-operations/{id}/timeline`
- `GET /api/campaign-operations/{id}/analytics`

### 3.4 Mission Operations Control Center (MOCC) UI (`web/`)
- Dual-deck cockpit featuring 6-card KPI summary, multi-sol color-coded Gantt timeline, real-time simulated state HUD, and contingency replanning drawer.
- Three.js 3D Mission Theater Story Mode with $+1.8\text{ m}$ elevated multi-sol ribbons, floating diamond target beacons, and microwave RF clearance rays.
