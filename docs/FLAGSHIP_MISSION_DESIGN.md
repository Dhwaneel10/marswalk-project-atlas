# Project MarsWalk — Flagship Mission Design Specification: "WHEN MARS GOES DARK"

**Mission Document:** `MARSWALK-FLAGSHIP-SPEC-001`  
**Scenario Name:** `WHEN MARS GOES DARK — Jezero Crater Resilience Traverse`  
**Mission ID:** `MISSION-MARS-DARK-001`  
**Target Body:** Mars (IAU 2000 Reference Sphere / USGS CTX Jezero Crater 20m DTM)  
**Landing Datum:** Octavia E. Butler Landing / Three Forks Base Camp `(117, 157)`  
**Terminal Goal:** Delta Scarp Overlook `(66, 128)`  
**Operational Horizon:** 60 Martian Sols (Focus Window: Sols 14.00 – 15.00)  
**Status:** **QUALIFIED & INTEGRATED**

---

## 1. Executive Summary & Narrative Purpose

In human and autonomous planetary exploration, missions rarely fail under benign nominal conditions. True mission viability is determined when Martian conditions deteriorate.

**"WHEN MARS GOES DARK"** is the signature operational demonstration for Project MarsWalk / Project Atlas. It proves why integrated mission planning, topological line-of-sight analysis, delay-tolerant communications custody (RFC 9171), and adaptive replanning are vital for planetary surface survival.

### The Central Story
A robotic exploration rover departs the Jezero crater floor on a multi-stop scientific traverse toward the western fan delta. During the traverse:
1. **Severe Atmospheric Dust Storm:** Atmospheric optical depth ($\tau$) spikes from 0.82 to 3.25, dropping solar power by 55% and derating autonomous visual odometry speed to 0.60×.
2. **Topographic RF Shadow & Comms Blackout:** The rover enters a depression behind the Hawksbill Gap scarp shoulder. Ray-traced Line-of-Sight (LoS) to the Three Forks Base Station is physically occluded by the crater shoulder, and the Mars Reconnaissance Orbiter (MRO) UHF pass window terminates, dropping the RF link to 0 kbps.
3. **Data Preservation Under Blackout:** High-priority scientific discoveries (including deep-UV Raman organic signatures from the SHERLOC instrument) cannot be transmitted. The Delay-Tolerant Networking (DTN) protocol asserts custody, queuing data in non-volatile flash storage ranked by 6-tier priority. Zero bytes are discarded.
4. **Scarp Rockfall & Autonomous Safe Hold:** A localized scarp regolith collapse blocks the primary Hawksbill ascent corridor with impassable boulders. Forward hazard cameras detect the obstruction, traction motor thermal warnings trigger, and the rover enters an autonomous safe hold.
5. **Adaptive Replanning with Causal Explanation:** Rather than aborting or remaining trapped, the autonomous replanning engine re-evaluates the terrain and computes a Pareto-optimal lateral detour around the scarp, ascending a stable ridge terrace.
6. **Ridge Relay Restoration & Custody Flush:** Upon cresting the Ridge Terrace at elevation -2,492m, clear Line-of-Sight is restored to the base station and ExoMars Trace Gas Orbiter (TGO). The DTN buffer flushes in strict priority order. All data packets are confirmed delivered with bit-exact SHA-256 cryptographic verification.

---

## 2. Planetary Coordinate & Target Configuration

All spatial coordinates are tied to the calibrated USGS CTX Jezero Crater 20m Digital Terrain Model (`data/processed/jezero_ready_20m.tif`), where each grid cell represents $20.0\,\text{m} \times 20.0\,\text{m}$:

| Waypoint Identifier | Grid (Row, Col) | Ground Elevation (MOLA Datum) | Geological & Operational Context |
|:---|:---:|:---:|:---|
| **Departure (`START_RC`)** | `(117, 157)` | $-2,534.6\,\text{m}$ | **Octavia E. Butler Landing / Three Forks Base Camp**. Base station with $15.0\,\text{m}$ mast antenna. |
| **Intermediate Target 1** | `(136, 91)` | $-2,518.2\,\text{m}$ | **Hawksbill Gap Ascent Channel**. Primary delta ascent corridor; site of simulated regolith collapse. |
| **Ridge Relay Point** | `(102, 110)` | $-2,492.0\,\text{m}$ | **Ridge Terrace Relay Point**. High-elevation promontory clearing crater scarp Line-of-Sight. |
| **Terminal Goal (`GOAL_RC`)** | `(66, 128)` | $-2,481.5\,\text{m}$ | **Delta Scarp Overlook**. Scientific target overlooking ancient Jezero river delta deposits. |

---

## 3. Physical Models & Constraint Parameters

### 3.1 Kinematic & Energy Model
- **Rover Vehicle Class:** Mars 2020 Perseverance Rover Digital Twin.
- **Nominal Velocity ($v_{\text{nom}}$):** $0.035\,\text{m/s}$ ($\sim 126\,\text{m/h}$).
- **Dust Storm Derated Velocity ($v_{\text{storm}}$):** $0.021\,\text{m/s}$ ($0.60 \times v_{\text{nom}}$) to preserve wheel traction.
- **Maximum Traversable Slope:** $15.0^{\circ}$ (Flight safety threshold). Slopes $>15.0^{\circ}$ are marked infinite cost (`inf`).
- **Battery Capacity:** $15,000\,\text{Wh}$ onboard Li-ion reserve.
- **Solar Array Output:** $950\,\text{W}$ nominal $\rightarrow$ derated to $427\,\text{W}$ ($-55\%$) during dust storm ($\tau = 3.25$).

### 3.2 Communications & Line-of-Sight Model
- **UHF Surface Frequency:** $401.58\,\text{MHz}$ (Electra Proximity-1 standard).
- **Nominal Link Rate:** $128\,\text{kbps}$.
- **Base Antenna Height:** $15.0\,\text{m}$ above ground level.
- **Rover Antenna Height:** $2.5\,\text{m}$ above ground level.
- **Line-of-Sight Ray Tracing:** Bilinear interpolation along top surface $Z(r, c)$. Obstructed if terrain profile penetrates line-of-sight ray vector with 0m clearance margin.

### 3.3 RFC 9171 Delay-Tolerant Networking (DTN) Architecture
The rover implements a 6-tier strict priority Bundle Protocol engine with 32 MB persistent flash memory:
1. **Class 1 (Emergency / Life-Support):** Highest priority; non-preemptible.
2. **Class 2 (Command Sequences & Recovery Confirmations):** Critical vehicle state telecommands.
3. **Class 3 (High-Priority Science):** Transient discoveries, SHERLOC deep-UV Raman organic spectra, PIXL elemental maps.
4. **Class 4 (Routine Engineering):** Housekeeping, thermal telemetry, battery state-of-charge.
5. **Class 5 (Bulk Science):** Mastcam-Z multispectral panoramas, raw imaging cubes.
6. **Class 6 (Background Archive):** Historical log archives, telemetry dumps.

---

## 4. Deterministic Reproducibility

The scenario execution is completely deterministic:
- **Random Seed:** 42.
- **Root Merkle Hash:** `0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8`.
- Running the scenario repeatedly yields bit-exact state hashes across all 7 operational snapshots.
