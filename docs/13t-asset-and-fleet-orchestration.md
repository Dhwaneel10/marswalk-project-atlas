# Milestone 13T: Asset & Fleet Orchestration

**Milestone:** 13T — Atlas Planetary Mission OS  
**System Module:** `atlas_unified_asset_manager.py`

---

## 1. Heterogeneous Fleet Specification

The Expedition Fleet in Jezero Crater comprises 8 synchronized mobile and stationary assets:

| Asset ID | Class | Health State | Power Spec | Primary Operational Role |
|:---|:---|:---:|:---|:---|
| `ATLAS-ROVER-01` | Ground Rover | `NOMINAL` | 4.5 kW / 98.5% SoC | Heavy science traverse, rock coring, geotechnical bearing tests. |
| `INGENUITY-ROTOR-01` | Scout Rotorcraft | `NOMINAL` | 0.5 kW / 100% SoC | Forward scouting, steep terrain visual inspection. |
| `HEXACOPTER-SURVEYOR-02`| Regional Surveyor| `NOMINAL` | 2.2 kW / 95% SoC | High-altitude multispectral mapping of Séítah dunes. |
| `CONSTRUCTION-BOT-01` | Excavator/Sinterer | `NOMINAL` | 12.0 kW / 92% SoC | Pad grading, foundation anchoring, microwave regolith sintering. |
| `SURFACE-COMM-MAST-01`| High-Gain Mast | `NOMINAL` | 1.5 kW / 100% SoC | Line-of-sight UHF relay & direct X-band Earth uplink. |
| `KILOPOWER-REACTOR-01`| Fission Station | `NOMINAL` | 120.0 kWe Baseload | Continuous Stirling cycle power independent of dust storms. |
| `ISRU-PLANT-01` | Chemical Plant | `NOMINAL` | 35.0 kW Draw | SOXE atmospheric oxygen extraction & Sabatier methane trial. |
| `HABITAT-CORE-01` | Inflatable Core | `NOMINAL` | 40.0 kW Capacity | Pressurized 101.3 kPa habitat module holding 294.15 K thermal loop.|

---

## 2. Conflict-Free Resource Reservation

Asset allocation implements mutually exclusive single-task assignment:
```python
def allocate_asset_to_task(asset_id: str, task_id: str) -> bool:
    asset = get_asset(asset_id)
    if asset.health in (OFFLINE, SAFE_MODE):
        return False
    if asset.current_task_id is not None and asset.current_task_id != task_id:
        return False # Double-booking prevented
    asset.current_task_id = task_id
    return True
```

This prevents race conditions between competing campaign workstreams (e.g., hauling vs pad grading).
