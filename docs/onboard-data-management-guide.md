# Onboard Data Management Guide
## Flash Storage Sizing, Buffer Satiation Protocols & Retention Policy Workflows

**Milestone:** 13G-R Release Qualification  
**Project:** MarsWalk 2.0 / Project Atlas  
**Audience:** Mission Planners, Flight Controllers & Software Evaluators  

---

## 1. Storage Capacity Sizing & Profiles

In planetary exploration planning, onboard solid-state mass memory (SSMM) is a critical resource constraint alongside battery energy and traverse time.

### Synthetic Demonstration Profiles
MarsWalk configures standard demonstration flash capacities:

| Preset Name | Capacity (Bytes) | Capacity (GB) | Recommended Mission Scenario |
| :--- | :---: | :---: | :--- |
| `4_GB` | 4,294,967,296 | 4.0 GB | Minimal Sortie / Small Scout Rover |
| `8_GB` | 8,589,934,592 | 8.0 GB | Constrained In-Situ Exploration |
| `16_GB` | 17,179,869,184 | 16.0 GB | **Nominal Baseline** (Perseverance Class) |
| `32_GB` | 34,359,738,368 | 32.0 GB | Multi-Instrument Campaign |
| `64_GB` | 68,719,476,736 | 64.0 GB | High-Bandwidth Regional Survey |

---

## 2. Retention Policies & Buffer Management

Every `MissionDataProduct` is assigned an explicit `RetentionPolicy`:

1. **`TRANSFER_THEN_RELEASE` (Default)**:
   Designed for maximum storage efficiency during long traverses. Flash memory occupied by the data product is marked for release immediately following confirmed receipt at the local Surface Base Station.
2. **`PROTECTED_PERMANENT`**:
   Designed for critical discovery samples (e.g. astrobiology biosignature scans, rock abrasion cores). Under NO circumstances is this data purged or overwritten. If storage is full, the mission halts further collection rather than discarding protected products.
3. **`TRANSFER_THEN_RETAIN`**:
   Designed for flight telemetry and engineering health records. The data is transferred during contact windows but retained locally in non-volatile flash until the rover returns to base or receives explicit operator override.
4. **`VOLATILE_SCRATCH`**:
   Temporary processing buffer (e.g., intermediate stereo disparity maps, raw spectrometer calibration dark frames). Automatically released when higher-level data products are generated.

---

## 3. Storage Pressure Action Protocols

When storage pressure escalates along a traverse:

```
[Available (<80%)]  --> Accept all observations unconditionally
         |
[Pressure (80-95%)] --> Prioritize transfer queue by priority_score
         |
[Near-Cap (95-100%)]-> Defer non-critical continuous surveys
         |
[Full (100%)]       --> Halt science acquisition; route rover to high-bandwidth relay window
```

In the 3D Mission Theater and Joint Studio Cockpit, flight controllers monitor the real-time storage gauge track:
- **Cyan fill**: Nominal ($<80\%$)
- **Amber fill**: Warning ($80\% - 95\%$)
- **Red fill**: Critical ($>95\%$)
