# Project MarsWalk 2.0 / Atlas — Executive Project Overview
**Submission Title:** MarsWalk 2.0 (Project Atlas) — Planetary Mission Operations & Resilience Platform  
**Target Challenge:** NASA Space Apps Challenge 2026  
**Document ID:** `DOC-MW-M7-PROJECT-OVERVIEW`  
**Platform:** Ubuntu 22.04 LTS (x86_64) | Python 3.10 | WebGL 3D Workstation  

---

## 1. Challenge & Problem Statement

Planetary surface exploration on Mars operates under extreme operational constraints that prevent real-time Earth-in-the-loop intervention:
1. **Light-Time Communication Latency:** One-Way Light Time (OWLT) between Earth and Mars ranges from **4.3 to 22.3 minutes** (Round-Trip Light Time 8.6 to 44.6 minutes). Tactical teleoperation is impossible; rovers must navigate autonomously.
2. **Terrain Hazards & Slope Ceilings:** The Martian surface features steep crater scarps, unconsolidated sand ripples, and rugged boulder fields. Slopes exceeding $15^\circ\text{--}16^\circ$ risk vehicle tip-over and catastrophic mission failure.
3. **The Astrobiology Dilemma:** Rovers must balance mobility risk and battery energy against science yield. Bypassing high-priority astrobiological targets (such as deltaic mudstones preserving organic molecules) wastes multi-billion-dollar mission investments, yet traversing blindly into steep terrain jeopardizes survival.
4. **Environmental Disruptions & Blackouts:** Seasonal regional dust storms drastically reduce solar array power (up to $-94\%$ attenuation), spike thermal survival heating loads, and sever direct orbital communications for hours to days when vehicles are caught in topographic radio shadows.

---

## 2. The MarsWalk 2.0 Solution

**MarsWalk 2.0 (Project Atlas)** is an end-to-end, scientifically grounded mission operations workstation and autonomous routing intelligence platform. Grounded strictly in authentic NASA Planetary Data System (PDS) and USGS Astrogeology archives, MarsWalk unites multi-scale terrain analysis, in-situ weather telemetry, astrobiological site prioritization, and delay-tolerant communication protocols into a unified mission execution platform.

```
+---------------------------------------------------------------------------------------------------------+
|                                    FIVE-PILLAR MISSION ARCHITECTURE                                     |
+-------------------+-------------------+-------------------+--------------------+------------------------+
| 1. TERRAIN        | 2. ROVER GROUND   | 3. IN-SITU        | 4. SCIENCE-DRIVEN  | 5. DTN AUTONOMY &      |
|    GEODESY        |    TRUTH (PDS)    |    WEATHER (MEDA) |    ROVER PLANNING  |    RESILIENCE          |
| USGS CTX 20m +    | 33.2 km Traverse  | PDS Observations  | Multi-Objective A* | RFC 9171 DTN Buffer    |
| HiRISE 1m DTM     | 10 Cached Tubes   | Solar Extinction  | Three Forks ->     | Safe Hold Detour       |
| Horn 8-Neighbor   | Three Forks Depot | Thermal Loads     | Delta (+160 pts)   | Merkle Root 0380a7cf...|
+-------------------+-------------------+-------------------+--------------------+------------------------+
```

---

## 3. The Five Core Pillars

### Pillar 1: Real Mars Terrain Intelligence
- **Primary Datasets:** USGS Astrogeology Jezero CTX 20m Stereo DEM ($5,000\,\text{m} \times 5,000\,\text{m}$ corridor, DOI [10.5066/P9T31O12](https://doi.org/10.5066/P9T31O12)) and USGS TRN HiRISE 1m DTM ($600\,\text{m} \times 600\,\text{m}$ Hawksbill Gap window, DOI [10.5066/P13CPYYU](https://doi.org/10.5066/P13CPYYU)).
- **Planetary Geodesy:** Planetocentric IAU 2000 Mars Spheroid ($R = 3,396,190\,\text{m}$, ESRI:103885), Equirectangular projection.
- **Slope Physics:** Horn 8-neighbor gradient kernel with operational slope ceiling threshold $\theta_{\text{max}} = 15.0^\circ$. Demonstrates resolution-aware hazard detection: while 20m CTX floor is gentle ($3.0^\circ$), 1m HiRISE reveals caution-grade slopes ($9.4^\circ$ with localized scarps $>18^\circ$) in the ascent channel.

### Pillar 2: Real Rover Operations & Ground Truth
- **Primary Datasets:** NASA PDS Rover PLACES archive (`best_tactical.csv`, Sols 13 to 1896) and NASA JPL Three Forks Sample Depot drop catalog (Sols 653 to 680).
- **Ground Truth Capabilities:** Tracks 33.2 km of historical Perseverance traverse odometry across 577 tactical localization sites. Indexes the 10 sealed titanium sample tubes cached on the Martian surface (including Tube #241 *Malay* and Tube #239 *Bearwallow*).

### Pillar 3: Mars Environment & Weather Replay
- **Primary Datasets:** In-situ atmospheric telemetry from NASA Mars 2020 MEDA (Rodriguez-Manfredi et al., Space Science Reviews 2021).
- **Physical Couplings:** Diurnal pressure cycle ($690\text{--}775\,\text{Pa}$), air temperatures ($-88.4^\circ\text{C}$ to $-11.2^\circ\text{C}$), wind speeds ($4.8\text{--}24.6\,\text{m/s}$), and optical depth scaling ($\tau = 0.82 \to 2.45 \to 4.10$). Computes plane-parallel Beer-Lambert solar array attenuation and battery survival heating loads.

### Pillar 4: Science-Driven Rover Planning
- **Primary Datasets:** Peer-reviewed geolocated astrobiology targets from Perseverance SHERLOC, PIXL, SuperCam, and Mastcam-Z investigations.
- **Multi-Objective A* Planner:** Optimizes across distance, slope risk, and astrobiological yield. Implements strict $R_{\text{intercept}} = 30.0\,\text{m}$ sampling thresholds. Demonstrates clear trade-offs: Route A (direct corridor, $2,309.7\,\text{m}$, 0 pts) vs Route B (science detour, $5,406.2\,\text{m}$, $+160\,\text{pts}$ yield for $+134.1\%$ distance and $+907.2\,\text{Wh}$ mobility energy).

### Pillar 5: Communications & Autonomous Resilience
- **Flagship Demonstrator:** "When Mars Goes Dark" scenario (Sols 88–92 severe regional dust storm and Hawksbill Gap rockfall).
- **Autonomous Recovery:** Rover executes autonomous safe hold at $T+01:45$, commands an adaptive lateral ridge detour, and climbs out of radio shadow to restore Line-of-Sight to the Mars Reconnaissance Orbiter (MRO).
- **Delay-Tolerant Networking (RFC 9171):** Telemetry bundles stored in non-volatile custodian buffer during blackout, achieving **100% data yield (0 bytes lost)**.
- **Cryptographic Audit:** Reconciles 7 lifecycle state snapshots into a bit-exact Merkle tree (`0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8`).

---

## 4. Key Innovations

1. **Multi-Resolution Dual-Raster Ingestion:** Dynamically switches between 20m regional CTX and 1m micro-hazard HiRISE DTMs to evaluate traversability across spatial scales.
2. **Epistemological Integrity Framework:** Enforces strict boundary markers distinguishing *Measured Archival Data*, *Derived Geospatial Models*, *Physical Heuristics*, and *Illustrative Simulations*.
3. **Cryptographically Auditable Mission Lifecycle:** Uses SHA-256 Merkle trees to produce tamper-evident proof chains verifying autonomous onboard decisions.
4. **Zero-Friction Evaluator Experience:** Embedded 7-step interactive Evaluator Golden Path HUD (`★ EVALUATOR TOUR`) runnable in under 10 minutes, backed by headless Chrome DevTools Protocol automation.

---

## 5. What is Real vs. What is Simulated

| Element | Real / Measured (NASA / USGS) | Simulated / Algorithmic Model |
| :--- | :--- | :--- |
| **Topography & Elevation** | USGS Jezero CTX 20m & HiRISE 1m DTMs | Interpolated raster rendering |
| **Rover Traverse Ground Truth** | 33.2 km historical path (Sols 13–1896) | Modeled future traverse options |
| **Sample Depot Inventory** | 10 sealed tubes deposited at Three Forks | Proximity pickup planning |
| **Atmospheric Conditions** | NASA MEDA pressure, temp, wind profiles | Simulated Sol 88–92 dust storm timing |
| **Rover Power Subsystem** | MMRTG hardware on Perseverance (~110W) | Analogue solar array model ($900\text{W} \to 258\text{W} \to 50\text{W}$) |
| **RF Dust Attenuation** | Near-transparent UHF proximity link (~0.008 dB/km) | Empirical heuristic proxy ($\alpha = 0.008 + 0.098\tau^{1.15}$) |
| **Autonomous Detour & DTN** | Topographic MRO Line-of-Sight geometry | RFC 9171 custodian buffer simulation |

---

## 6. Limitations & Future Work

- **Non-Flight Certification Notice:** All routes and hazard margins are algorithmic models, **never certified for human astronaut safety**.
- **Spatial Boundaries:** Planning is confined to the surveyed $5\text{km} \times 5\text{km}$ Jezero CTX sub-grid and $600\text{m} \times 600\text{m}$ Hawksbill Gap HiRISE window.
- **Future Work:** Integrate multi-spectral CRISM mineralogy overlays, dynamic slip-sinkage terramechanics, and multi-rover collaborative coordination.
