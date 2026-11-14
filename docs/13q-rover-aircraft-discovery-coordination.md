# PROJECT ATLAS — MILESTONE 13Q
# ROVER–AIRCRAFT DISCOVERY COORDINATION & MULTI-AGENT SCIENCE
## Synergistic Reconnaissance, Cross-Platform Task Allocation & Delayed Communications

**Milestone:** 13Q — Atlas Autonomous Science Discovery Engine  
**Module:** `src/marswalk/core/active_science_planner.py`  
**Status:** `QUALIFIED`

---

## 1. Ground–Air Exploration Synergy

The coupling of ground rovers and aerial rotorcraft represents a transformative multiplier for planetary exploration:

```
+-----------------------------------------------------------------------------------+
|                        GROUND–AIR COOPERATIVE SCIENCE CYCLE                       |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [ AERIAL SCOUT ]                                                                 |
|  - Rapid regional transit (7.0 m/s)                                               |
|  - High-altitude multi-spectral screening                                         |
|  - Broad spatial anomaly detection                                                |
|  - Landing site evaluation                                                        |
|         |                                                                         |
|         v (UHF 401.5 MHz Downlink across scheduled contact window)                |
|  [ GROUND ROVER ]                                                                 |
|  - In-situ precision approach (4.0 cm/s)                                          |
|  - Robotic arm deployment (< 3 cm standoff)                                       |
|  - High-energy micro-scale lithochemistry (PIXL XRF, SHERLOC Raman)               |
|  - Ground truth validation & definitive mineral confirmation                      |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Six Cooperative Discovery Strategies

1. **Aerial Reconnaissance Followed by Targeted Ground In-Situ Verification:**
   The rotorcraft identifies a candidate $2.3\ \mu\text{m}$ absorption feature. The rover evaluates transit energy and navigates to the outcrop to perform sub-millimeter PIXL elemental mapping.
2. **Multi-Altitude Spatial Resolution Scaling:**
   Rotorcraft flies at $15\text{ m}$ ($0.78\text{ cm/px}$) and $50\text{ m}$ ($2.6\text{ cm/px}$) to evaluate scale-dependent geological facies.
3. **Multi-Instrument Cross-Validation:**
   SuperCam remote SWIR detects absorption; PIXL performs elemental stoichiometry to confirm cation ratios; SHERLOC performs deep UV Raman to verify crystal lattice.
4. **Spatial Scouting with Information-Gated Rover Dispatch:**
   The rover does not traverse high-risk slopes unless aerial reconnaissance reduces path uncertainty below $15\%$.
5. **Distributed Multi-Asset Parallel Investigation:**
   Two aircraft (`AERO-INGENUITY`, `AERO-MAPPER`) survey separate delta lobes while two rovers perform independent in-situ analyses.
6. **Adaptive Replanning on Instrument Dropout:**
   If an airborne spectrometer fails, the active planner reschedules ground SuperCam VISIR without falsifying or losing missing telemetry.

---

## 3. Communication Latency and Transfer Invariants

In strict adherence to Milestone 13O deep space autonomy:
- Aerial observations are **not instantaneously known to the rover**.
- Observations must be buffered in non-volatile flash storage and downlinked across scheduled UHF proximity contact passes.
- Ground rovers operate under bounded autonomy while waiting for aerial map downlinks.
