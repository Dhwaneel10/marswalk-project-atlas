# ATLAS 13R — API SPECIFICATION
## REST Endpoints, Schema Contracts, and Request/Response Payload Specifications

**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Milestone:** 13R — Atlas Apocalypse Engine  
**Schema:** `schemas/api/v1/mission-resilience.schema.json` (Draft 2020-12)  

---

### 1. Endpoint Summary

| Method | Path | Description | Schema / Response |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/resilience/status` | Current system health index, active faults, and confirmed diagnoses. | `mission-resilience.schema.json` |
| `GET` | `/api/resilience/taxonomy` | Returns full 7-class catalog of standard planetary failure modes. | Array of `FailureRecord` |
| `POST` | `/api/resilience/faults/inject` | Injects time-parameterized failure into counterfactual branch. | Injected instance & cascade trigger |
| `POST` | `/api/resilience/diagnose` | Evaluates observable symptoms and outputs FDDI report. | `DiagnosticReport` |
| `POST` | `/api/resilience/propagation` | Propagates active faults through causal DAG and toggles barriers. | Full DAG state & failed nodes |
| `POST` | `/api/resilience/recovery/evaluate` | Synthesizes and counterfactually benchmarks candidate recovery plans. | Array of `CandidateRecoveryPlan` |
| `GET` | `/api/resilience/fmea` | Formal FMEA table and top-level Boolean Fault Tree. | FMEA records & FaultTreeNode |
| `GET` | `/api/resilience/scenarios` | Returns catalog of 12 Apocalypse Scenarios. | Catalog of 12 scenario specs |
| `POST` | `/api/resilience/scenarios/run` | Executes complete end-to-end scenario injection & recovery. | `ScenarioExecutionResult` |
| `GET` | `/api/resilience/benchmarks` | Comparative evaluation across 6 strategies on Dev and Held-Out suites. | Benchmark results & summary |
| `POST` | `/api/resilience/reset` | Clears all injected faults and restores pristine nominal baseline. | Reset status |

---

### 2. Sample Payloads

#### `POST /api/resilience/scenarios/run`
**Request Body:**
```json
{
  "scenario_id": "SCENARIO-12",
  "sol": 1,
  "time_s": 3600.0
}
```

**Response (HTTP 200 OK):**
```json
{
  "scenario_id": "SCENARIO-12",
  "name": "Project Apocalypse — Five Simultaneous Multi-Domain Failures",
  "injected_faults_count": 5,
  "detected_symptoms_count": 9,
  "confirmed_diagnoses_count": 3,
  "propagated_cascade_nodes": [
    "ROV_POWER_BUS_SURGE",
    "ROV_SPEED_DEGRADATION",
    "ROV_SCHEDULE_SLIP",
    "ROV_BUFFER_OVERFLOW",
    "AERO_LIFT_DEFICIT",
    "AERO_MOTOR_OVERHEAT",
    "AERO_EMERGENCY_DESCENT",
    "AERO_SOLAR_DEPLETION",
    "SCI_FALSE_DISCOVERY"
  ],
  "selected_recovery_plan": {
    "plan_id": "PLAN-ATLAS-AUTONOMOUS",
    "name": "Atlas Integrated Multi-Asset Autonomous Recovery",
    "strategy_class": "FULL_ATLAS_RECOVERY",
    "overall_resilience_rank": 1,
    "metrics": {
      "science_objectives_completed": 5,
      "science_objectives_preserved_deferred": 1,
      "science_objectives_abandoned": 0,
      "energy_remaining_wh": 710.0,
      "data_retained_mb": 420.0,
      "data_lost_mb": 0.0,
      "mission_duration_extension_s": 9000.0,
      "time_to_recover_s": 272.0,
      "unresolved_failures_count": 0,
      "remaining_operational_constraints": [
        "ROVER_5_WHEEL_DRIVE_ACTIVE",
        "AIRCRAFT_LOW_CEILING_LIMIT_5M",
        "DTE_COMPRESSED_DATA_MODE"
      ],
      "resource_violations_count": 0,
      "final_mission_state_validity": true,
      "state_validity_explanation": "Full mission validity preserved: all critical science preserved, zero buffer drops, no thermal or electrical bus limits breached."
    }
  },
  "execution_duration_ms": 42.5,
  "state_hash": "BA87A9EA97A25717"
}
```
