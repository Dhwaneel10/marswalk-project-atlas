# Project MarsWalk — Operator Interface & Mission Control Guide

**Document ID:** `MARSWALK-UI-SPEC-001`  
**Application Title:** MarsWalk 2.0 / Project Atlas Planetary Mission Operations Workstation  
**Primary Interface:** Mars Mission Control Cockpit (`#tabMissionControl`)  
**Target Viewport:** Desktop ($1920 \times 1080$, min $1280 \times 720$)  
**Status:** **INTEGRATED & VERIFIED**

---

## 1. Interface Philosophy & Aesthetic Direction

The Project Atlas interface implements a mission-grade planetary command aesthetic:
- **Palette:** High-contrast dark field (`#081018`, `#0f172a`) with telemetry-coded signal colors:
  - Cyan (`#38bdf8`): Active routes, line-of-sight rays, nominal telemetry.
  - Green (`#10b981`): Qualified health, restored communication paths, delivered science data.
  - Amber (`#f59e0b`): Atmospheric tau spikes, DTN buffer occupancy, lateral adaptive detours.
  - Crimson (`#ef4444`): Topographic RF shadows, scarp rockfalls, vehicle safe hold triggers.
  - Purple (`#c084fc`): Cryptographic Merkle tree hashes, forensic decision lineage.
- **Cognitive Clarity:** The top navigation bar organizes the system into the **5 primary mission work areas**, while all 17 secondary engineering labs remain instantly accessible through the integrated **Extended Labs** dropdown.

---

## 2. Organization Around 5 Primary Work Areas

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  MARSWALK 2.0 &bull; PROJECT ATLAS — MARS MISSION CONTROL                             │
│  [1. Cockpit]  [2. Terrain & Traverse]  [3. Comms & DTN]  [4. Faults]  [5. Analysis]   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. Mission Overview (Cockpit Telemetry HUD)
- **Active Coordinates:** Real-time rover position $(r, c)$ mapped to geodetic longitude/latitude.
- **Topographic Elevation:** Ground elevation (meters MOLA datum) with local slope angles.
- **Consumables & Power:** $15\,\text{kWh}$ Li-ion battery budget, solar array flux ($\text{W/m}^2$), power derating factor.
- **Atmospheric Conditions:** Real-time atmospheric optical depth ($\tau$) calibrated against Jezero MEDA data.
- **Carrier Status:** RF connectivity state (`ONLINE_128KBPS`, `BLOCKED_TERRAIN_OCCLUSION`, `RESTORED_128KBPS`).

### 2. Terrain & Traverse (3D Planetary Workstation)
- **High-Resolution 3D Surface:** Three.js terrain mesh constructed from USGS CTX Jezero Crater 20m DTM.
- **Nominal Trajectory:** Cyan path tracing the planned A* traverse from Three Forks (`(117, 157)`) to Hawksbill Gap (`(136, 91)`).
- **Hazard Visualization:** Red wireframe hazard sphere marking the localized scarp collapse ($60\,\text{m}$ radius).
- **Adaptive Lateral Detour:** Amber/Green traverse climbing the low-gradient Ridge Terrace (`(102, 110)`) to Delta Scarp Overlook (`(66, 128)`).
- **Elevation Profile Crosshair:** Interactive SVG elevation profile with distance, ascent, and slope attribution.

### 3. Communications & Delay-Tolerant Networking (DTN)
- **Line-of-Sight Evaluation:** Real-time ray-tracing between surface rover antenna ($2.5\,\text{m}$ AGL) and base station ($15.0\,\text{m}$ AGL).
- **RFC 9171 Flash Custody Buffer:** 32 MB local buffer utilization meter displaying packet custody throughout the 2.5-hour blackout.
- **6-Tier Priority Ledger:** Class 1 (Emergency), Class 2 (Command), Class 3 (High Science), Class 4 (Engineering), Class 5 (Bulk Science), Class 6 (Archive).
- **Custody Flush Status:** Real-time verification of custody transfers and SHA-256 payload digests.

### 4. Faults & Autonomous Recovery
- **Active Alarm Box:** Displays triggered flight rule alerts (`FAULT_CORRIDOR_OCCLUSION`, `WARN_ATMOSPHERIC_TAU_HIGH`).
- **Autonomous Safe Hold:** Visual confirmation when the vehicle halts to preserve battery and structure.
- **Adaptive Replanner Recommendation:** Explains why the nominal route was aborted and the detour selected.
- **Causal Lineage:** Transparent rationale explaining slope, energy, and elevation trade-offs.

### 5. Mission Strategy Analysis
- **Side-by-Side Comparison:** Strategy A (Static/Nominal) vs Strategy B (Adaptive/Resilient).
- **Head-to-Head Metrics:** Data preservation rate ($33.3\%$ vs $100.0\%$), data lost ($2,944\,\text{KB}$ vs $0\,\text{KB}$), battery margin remaining, completion status (`FAILED_TRAPPED` vs `COMPLETED_SUCCESS`).
- **Cryptographic Merkle Proof:** Displays root hash `0380a7...` with verified 7-stage state continuity.

---

## 3. Operator Walkthrough Workflow

1. **Launch Mission Control:** Click **1. Mission Control** in the header or access `http://127.0.0.1:3000`.
2. **Inspect Baseline Sortie:** Note the nominal departure from Three Forks Base Camp on the Jezero Crater floor.
3. **Click `[▶ RUN MISSION]`:** Launches the 7-stage automated sequence with live scrubber synchronization.
4. **Observe Dust Storm Onset (Stage 2):** Atmospheric $\tau$ spikes to 3.25; solar flux drops by 55%; speed derates.
5. **Observe Communications Loss (Stage 3):** Rover enters terrain depression; Line-of-Sight drops; RF link goes dead ($0\,\text{kbps}$).
6. **Observe DTN Custody (Stage 4):** SHERLOC Raman organic discovery captured; DTN protocol asserts custody in flash storage; 0 bytes lost.
7. **Observe Rockfall Obstruction & Safe Hold (Stage 5):** Scarp collapse detected; forward progress halts safely.
8. **Observe Adaptive Replanning (Stage 6):** Autonomous replanner identifies Ridge Terrace detour avoiding steep slopes.
9. **Observe Ridge Relay Clearance (Stage 7):** Rover reaches high ground; RF carrier restored; DTN custody queue flushes all 6 bundles in priority sequence.
10. **Click `[⚖ COMPARE]` & `[🔒 VERIFY PROOF]`:** Inspect head-to-head performance table and cryptographic Merkle proof.
