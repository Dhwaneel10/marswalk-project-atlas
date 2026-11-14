# MarsWalk 2.0 — Milestone 11B Design Specification
## Campaign Progress & Science Observation Registry

**Milestone:** 11B (MarsWalk 2.0 V2)  
**Status:** IMPLEMENTATION DESIGN SPECIFICATION  
**Author:** MarsWalk Core Architecture Team  
**Date:** 2026-10-29  
**Target Environment:** Mars (IAU 2000 Sphere / USGS CTX DTM 20m Jezero Crater)

---

### 1. Architectural Motivation & Problem Statement

Milestone 11A introduced the **Mission Campaign Orchestrator**, which models multi-sol planetary campaign schedules and resolves target prerequisite DAGs. However, real and simulated planetary exploration is an interactive, closed-loop process:
1. Sorties are executed sequentially. As each target is reached, scientific instruments capture observations (spectral reflectance, atmospheric pressure, bedrock coring assays).
2. The outcomes of these observations dictate what happens next: a completed objective unblocks downstream prerequisites; a severed corridor or blocked sample site forces dynamic rescheduling of remaining sols.
3. Historical plans and recorded observations must be **immutable**: an updated schedule must never erase or rewrite what already occurred on previous sols.
4. Simulated observations must be strictly labeled with provenance (`SIMULATED`, `IMPORTED_PDS_MEDA`, `MEASURED_IN_SITU`, `UNKNOWN`) and physical SI units to prevent scientific fabrication.

---

### 2. Core Concepts & State Machine

#### 2.1 Sortie Lifecycle States
A campaign sortie traverses through the following state machine:
```
           ┌───────────┐
           │  PLANNED  │
           └─────┬─────┘
                 │
                 ▼
           ┌───────────┐
      ┌───►│   READY   │ (All prerequisite targets satisfied)
      │    └─────┬─────┘
      │          │ Sortie commences
      │          ▼
      │    ┌───────────┐
      │    │IN_PROGRESS│
      │    └─────┬─────┘
      │          │
      ├──────────┴─────────────────────────┬────────────────────────┐
      │ Targets completed & base returned  │ Hazard blocks traverse │ Sols cut
      ▼                                    ▼                        ▼
┌───────────┐                        ┌───────────┐            ┌───────────┐
│ COMPLETED │                        │  BLOCKED  │            │ CANCELLED │
└───────────┘                        └───────────┘            └───────────┘
```

#### 2.2 Target Lifecycle States
```
UNSCHEDULED ──> SCHEDULED ──> VISITING ──> COMPLETED
                     │             │
                     │             └──> BLOCKED (Site hazardous or inaccessible)
                     └──> DEFERRED (Budget or sol limit exceeded)
```
- **Rule of Non-Rescheduling:** Once a target reaches `COMPLETED`, it can **never** be scheduled in future sols of the campaign unless explicitly configured as a repeated multi-epoch monitoring objective.
- **Dependency Resolution:** Upon marking a target `COMPLETED`, all downstream targets in the prerequisite DAG are immediately re-evaluated. If all prerequisites for a downstream target are now satisfied, its status transitions to `ELIGIBLE` for scheduling in the next available sol.

---

### 3. Science Observation Registry

Each science observation is a first-class, schema-validated entity:
```json
{
  "observation_id": "obs_jezero_spectral_001",
  "campaign_id": "cmp_jezero_delta_front",
  "sortie_id": "sortie_sol_01",
  "target_id": "enchanted_lake",
  "timestamp_utc": "2026-10-29T00:30:00Z",
  "sol_index": 1,
  "observation_type": "SPECTRAL_SURVEY",
  "provenance": "SIMULATED",
  "instrument_name": "Mastcam-Z / SuperCam Emulation",
  "quantitative_measurements": [
    {
      "parameter": "clay_mineral_absorption_depth",
      "value": 0.42,
      "unit": "dimensionless",
      "uncertainty": 0.03
    },
    {
      "parameter": "surface_temperature",
      "value": 218.4,
      "unit": "K",
      "uncertainty": 1.5
    }
  ],
  "qualitative_notes": "Laminated mudstone outcrop displays pronounced 2.2 um absorption band indicative of smectite/phyllosilicate clays.",
  "evidence_references": {
    "crism_product_id": "FRT0000B9DF_07",
    "spatial_coordinates_rc": [140, 108],
    "ground_elevation_m": -2566.77
  },
  "confidence_score": 0.95,
  "is_simulated": true
}
```

#### Physical Quantity & Units Standard
All quantitative measurements strictly enforce standard SI units or internationally recognized planetary science conventions:
- Atmospheric Pressure: `Pa` or `hPa`
- Temperature: `K` or `degC`
- Wind Speed: `m/s`
- Distance: `m` or `km`
- Time / Duration: `s`, `min`, or `h`
- Slope / Angle: `deg`
- Optical Depth: `dimensionless`

---

### 4. Dynamic Campaign Replanning on Progress

When a progress event (`TARGET_COMPLETED` or `TARGET_BLOCKED`) is recorded:
1. **Preserve Completed History:** All past sols and completed sorties remain immutable with their original telemetry and observations intact.
2. **Recompute Remaining Sols:** The planning engine (`plan_mission_campaign`) is invoked starting from `active_sol_index`:
   - Completed targets are excluded from the candidate pool.
   - Newly eligible targets are included.
   - Blocked targets are recorded with their causal rationale.
3. **Version Increment & Delta Manifest:**
   - The campaign version increments ($v_n \to v_{n+1}$).
   - `revision_comparison` captures:
     - Delta traverse distance ($\Delta D$)
     - Delta duration ($\Delta T$)
     - Delta science yield ($\Delta S$)
     - List of newly eligible targets
     - List of deferred or omitted targets
4. **Storage:** Saved to `data/workspaces/campaigns/cmp_<id>_v<version>.json` and updated in active campaign `cmp_<id>.json`.

---

### 5. Scientific Research Simulation Disclaimer

All observation records and progress workflows bear the mandatory notice:
> **SCIENTIFIC RESEARCH SIMULATION DISCLAIMER:** All simulated observations, instrument readings, and sortie progression events are generated for academic research and educational modeling. Simulated findings do not represent physical Martian measurements. Imported in-situ data (e.g. NASA PDS MEDA) retain their original archival citations and are never altered or labeled as simulated.
