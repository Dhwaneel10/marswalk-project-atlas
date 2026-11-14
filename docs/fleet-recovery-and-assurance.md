# Fleet Recovery, Mission Assurance & Counterfactual Operations
## Fault Injection Models (F1–F7), Autonomous Recovery & 3-Way Comparative Delta Matrix

**Component:** `src/marswalk/core/fleet_optimization_engine.py`  
**JSON Contract:** `schemas/api/v1/fleet-scenario.schema.json`, `fleet-assurance.schema.json`  
**Invariant Rules Library:** 7 Fleet-Scale Mission Invariant Rules

---

## 1. Problem Formulation & Autonomous Recovery

In extreme planetary environments, disturbances are inevitable: rover mobility failures, instrument detector degradation, surface relay power outages, severe dust storms, or sudden scientific discoveries requiring target reprioritization.

Single-rover systems must halt operations and enter safe mode during severe anomalies. In Project Atlas, the fleet **dynamically self-heals**:
- Healthy exploration units absorb orphaned science targets based on instrument compatibility and remaining battery margins.
- Traverses are dynamically rerouted to bypass blocked corridors or chokepoints.
- Mobile relays reposition to maintain RF mesh reachability.

---

## 2. Standardized Disturbance Scenarios (F1–F7)

Atlas implements seven formalized multi-rover disturbance benchmarks:

| Scenario Code | Name | Disturbance Mechanism | Autonomous Recovery Strategy |
| :--- | :--- | :--- | :--- |
| **F1** | **Rover Inoperability** | Rover A mobility system failure on Sol 2 | Orphaned targets (`TGT_HAWKSBILL_GAP`, `TGT_BELVA_CRATER`) reallocated to Rover C and Rover B; Rover D establishes communications bridge. |
| **F2** | **Shared Surface Relay Outage** | Relay Beta hardware outage ($3600\text{ s}$) | Rover Delta assumes Active Mobile Relay on Solitary Butte, restoring 100% geometric reachability. |
| **F3** | **Fleet Resource Imbalance** | Rover C thermal battery throttling ($-30\%$ SOC) | Deep coring task deferred; Rover C switches to low-power panoramic imaging; Coring re-assigned to Rover A. |
| **F4** | **Science Target Dynamic Preemption** | Discovery of high-priority organic target ($+500\text{ pts}$) | Dynamic schedule insertion; low-priority meteorological tasks preempted; routes recalculated. |
| **F5** | **Spatiotemporal Route Contention** | Rover A & Rover B simultaneous arrival at delta chokepoint | Automatic temporal hold ($15\text{ min}$) injected for Rover B; Rover A maintains priority right-of-way. |
| **F6** | **Flash Memory Backlog Concentration** | Downlink pass truncated by orbiter trajectory shift | High-priority spectral data prioritized; Rover Delta buffers data for next pass; compression filters engaged. |
| **F7** | **Combined Multi-Rover Disturbance** | Simultaneous Rover A wheel stall + regional dust storm ($\tau = 2.1$) | Fleet-wide power throttling; mobile relay deployment; multi-target redistribution across Rovers B, C, D. |

---

## 3. The 3-Way Comparative Scorecard

To evaluate the mathematical effectiveness of an autonomous recovery plan, Atlas calculates a **3-Way Comparative Delta Matrix**:

$$\text{Delta Matrix} = \left[ \mathbf{M}_{\text{Baseline Nominal}} \;\middle|\; \mathbf{M}_{\text{Disturbed Unmitigated}} \;\middle|\; \mathbf{M}_{\text{Autonomous Recovery}} \right]$$

### Evaluated Dimensions:
1. **Active Operational Units:** Count of operational rovers.
2. **Fleet Traverse Distance:** Total ground distance covered ($\text{km}$).
3. **Min Battery Margin (SOC):** Worst-case rover energy margin ($\%$).
4. **RelayNet Comms Reachability:** Percentage of fleet with active RF path to Base Station ($\%$).
5. **Flash Memory Backlog:** Total un-downlinked data volume ($\text{MB}$).
6. **Total Science Utility Yield:** Aggregate points achieved ($\text{pts}$).
7. **Overall Feasibility:** Binary master verdict (`FEASIBLE` vs `VIOLATION`).

In benchmark F1 (Rover A failure), unmitigated operations lose $39.4\%$ of scientific utility. The autonomous recovery plan recovers **$94.2\%$ of baseline science return** while preserving $>34\%$ energy margins across all surviving vehicles.

---

## 4. Seven Fleet-Scale Invariant Rules

Mission assurance is governed by 7 hard invariant rules:

| Rule ID | Rule Name | Category | Severity | Invariant Condition |
| :--- | :--- | :--- | :--- | :--- |
| `UNIT-001` | **Exploration Units Registered** | Unit | CRITICAL | All 4 rovers registered with valid configs & non-empty battery buffers. |
| `ALLOC-001` | **100% Instrument Compatibility** | Allocation | CRITICAL | Every assigned target must match a compatible instrument carried on the vehicle. |
| `ALLOC-002` | **Zero Duplicate Assignments** | Allocation | CRITICAL | Every target assigned at most once across all rovers ($\sum_i x_{ij} \le 1$). |
| `DECONF-001` | **Zero Spatiotemporal Overlaps** | Spatiotemporal | CRITICAL | No two rovers occupy $<40\text{ m}$ separation during overlapping time intervals. |
| `RES-001` | **Zero Cross-Rover Energy Pooling** | Resource | CRITICAL | Strictly independent battery registers ($\partial SOC_i / \partial E_j = 0$). |
| `NET-001` | **Fleet Base Reachability $\ge 90\%$** | Network | WARNING | Minimum $90\%$ of active rovers maintain valid RF paths to Base Station. |
| `REC-001` | **Version Monotonicity Guard** | Recovery | CRITICAL | Fleet recovery plan version strictly monotonic ($v_{\text{new}} = v_{\text{old}} + 1$). |

---

## 5. Cryptographic Promotion Sign-Off

When an evaluator or flight director authorizes a recovered fleet plan:
1. A unique SHA-256 fingerprint is computed across the entire fleet state.
2. The approver's callsign and technical rationale are recorded in an immutable audit ledger.
3. The fleet version increments ($v1 \rightarrow v2$), and the new plan is promoted as the operational baseline.
