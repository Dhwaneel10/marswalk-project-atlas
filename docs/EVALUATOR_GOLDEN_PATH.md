# Project MarsWalk 2.0 / Atlas — Evaluator Golden Path Walkthrough
**Document ID:** `DOC-MW-M6-EVALUATOR-GOLDEN-PATH`  
**Target Audience:** NASA Space Apps Evaluators, Planetary Geodesists, Mission Operations Reviewers  
**Platform Execution:** Ubuntu 22.04 LTS | Python 3.10 (`.venv`) | Modern Web Browser (Chrome/Firefox)  
**Interactive UI Feature:** Click **`★ EVALUATOR TOUR`** in the top-right header of the Five-Pillar Operations Deck.

---

## 1. Executive Summary & Evaluator Golden Path Overview

Project MarsWalk 2.0 / Atlas is an operational Mars rover routing, astrobiology exploration, and delay-tolerant mission assurance platform grounded strictly in authentic NASA, USGS, and PDS planetary archives.

To allow evaluators to verify the complete five-pillar architecture in under **10 minutes**, MarsWalk features a scripted, interactive **Evaluator Golden Path HUD**. This walkthrough details each step, the exact UI interaction, the underlying REST API call, the mathematically computed ground truth, and the scientific justification.

```
+-------------------------------------------------------------------------------------------------------+
|                                    EVALUATOR GOLDEN PATH ROADMAP                                      |
+-------------------+-------------------+-------------------+-------------------+-------------------+
|  1. REAL MARS     |  2. MULTI-RES     |  3. ROVER GROUND  |  4. MEDA IN-SITU  |  5. A* SCIENCE    |
|     GEODESY       |     TERRAIN       |     TRUTH (PDS)   |     ENVIRONMENT   |     TRADE STUDY   |
| USGS CTX + HiRISE | 1m Slope Hazard   | 33.2 km Traverse  | Dust Storm tau    | Direct vs Science |
| 8/8 Valid Datasets| vs 20m Floor      | 10 Sample Tubes   | Solar / RF loss   | +160 pts / +134%  |
+-------------------+-------------------+-------------------+-------------------+-------------------+
                                            |
                                            v
                    +-----------------------------------+-----------------------------------+
                    |  6. AUTONOMOUS RESILIENCE         |  7. CRYPTOGRAPHIC MERKLE PROOF   |
                    |     "When Mars Goes Dark" Replay  |     Bit-Exact State Tree Audit    |
                    |     Safe Hold & Lateral Detour    |     Root Hash: 0380a7cf...        |
                    |     MRO Line-of-Sight Restored    |     100% DTN Bundle Custody       |
                    +-----------------------------------+-----------------------------------+
```

---

## 2. Step-by-Step Evaluator Script

### Step 1: Real Mars Data Provenance & Geodesy
- **Evaluator Goal:** Confirm that MarsWalk operates entirely on authentic planetary science archives rather than synthetic procedural terrain.
- **UI Interaction:** Click **`★ EVALUATOR TOUR`** header button, ensure Step **`1. DATA`** is active, and click **`▶ EXECUTE STEP ACTION`** (or click Pillar 1 `TERRAIN (USGS)`).
- **API Endpoint:**
  - `GET /api/pillars/terrain`
  - `GET /api/pillars/manifest`
- **Expected Values & Verifiable Evidence:**
  - **USGS Jezero CTX 20m DEM:** Product `USGS_CTX_DEM_PROCESSED_20M` (250×250 cells, 20.0 m/px resolution, 5,000 m × 5,000 m corridor). SHA-256: `875e7e80f9cb...` | DOI: [10.5066/P9T31O12](https://doi.org/10.5066/P9T31O12)
  - **USGS TRN HiRISE 1m DTM:** Product `USGS_TRN_HIRISE_1M` (600×600 cells, 1.0 m/px resolution, Hawksbill Gap ascent). SHA-256: `0258c9e135cf...` | DOI: [10.5066/P13CPYYU](https://doi.org/10.5066/P13CPYYU)
  - **Planetary Coordinate Reference System:** Planetocentric IAU 2000 Mars Spheroid ($R = 3,396,190\,\text{m}$, authority `ESRI:103885`), Equirectangular projection.
  - **Provenance Audit:** `8/8 INTEGRITY VERIFIED` against disk manifest.
- **Scientific Takeaway:** MarsWalk enforces planetary geodesy and strict data integrity. No elevation values are randomly generated.

---

### Step 2: Multi-Resolution Slope & Micro-Hazard Inspection
- **Evaluator Goal:** Observe how resolution-tier switching dynamically catches micro-hazards that coarser regional models smooth over.
- **UI Interaction:** Click Step **`2. TERRAIN`** and click **`▶ EXECUTE STEP ACTION`**.
- **API Endpoint:**
  - `POST /api/pillars/terrain/inspect` with `{"row": 136, "col": 91}` (Hawksbill Gap)
  - `POST /api/pillars/terrain/inspect` with `{"row": 50, "col": 50}` (Crater Floor)
- **Expected Values & Verifiable Evidence:**
  - **Hawksbill Gap (`row: 136, col: 91`):** Resolution: **1.0 m** (HiRISE DTM) | Elevation: **-2,554.7 m** | Horn 8-Neighbor Slope: **9.4°** | Assessment: **CAUTION (ASCENT)** (with localized steep scarps reaching >18°).
  - **Crater Floor (`row: 50, col: 50`):** Resolution: **20.0 m** (CTX DEM) | Elevation: **-2,480.5 m** | Horn 8-Neighbor Slope: **3.0°** | Assessment: **NOMINAL FLAT**.
  - **3D Visualization:** Camera automatically aligns and focuses directly on the Hawksbill Gap ascent corridor in the 3D viewport.
- **Scientific Takeaway:** Planetary rovers face vehicle tip-over hazards on slopes $>15^\circ$. MarsWalk integrates 1m HiRISE micro-hazard data specifically within the delta ascent window to ensure terrain traversal safety.

---

### Step 3: Ground Truth Rover History & Three Forks Depot
- **Evaluator Goal:** Cross-examine simulated path solutions against the actual historical traverse of NASA’s Perseverance rover and inspect the surface sample cache.
- **UI Interaction:** Click Step **`3. ROVER`** and click **`▶ EXECUTE STEP ACTION`** (or click Pillar 2 `ROVER OPS (PDS)`).
- **API Endpoint:**
  - `GET /api/pillars/rover-ground-truth/query?depot_only=true`
- **Expected Values & Verifiable Evidence:**
  - **Tactical Traverse:** **33.2 km** total odometry across **1,896 Sols** (Landing at Octavia E. Butler to present).
  - **Three Forks Sample Depot Inventory:** Exactly **10 sealed titanium tubes** deposited on the surface (Sols 653–680):
    - *Tube #241:* Sample **Malay** (Amalik outcrop, fine-grained sandstone, deposited Sol 653).
    - *Tube #239:* Sample **Bearwallow** (Wildcat Ridge paired core, deposited Sol 674; sister core *Hazelton* #268 retained onboard).
    - *Tube #254:* Sample **Mageik** (Séítah formation igneous olivine).
    - *Tube #258:* Sample **Montdenier** (Crater floor basaltic igneous).
    - *Atmospheric Witness Tube #217:* Dropped Sol 663.
  - **3D Context:** Camera focuses on the Three Forks depot cache coordinates (`row: 146, col: 77`).
- **Scientific Takeaway:** The sample depot inventory accurately tracks PDS mission logs, correctly distinguishing samples deposited in the backup cache vs. retained onboard the rover.

---

### Step 4: Authentic Atmospheric Physics & Sensor Calibration
- **Evaluator Goal:** Verify that environmental constraints are dynamically coupled to real NASA Mars 2020 MEDA (Mars Environmental Dynamics Analyzer) measurements.
- **UI Interaction:** Click Step **`4. MEDA`** and click **`▶ EXECUTE STEP ACTION`** (or select `Regional Storm` preset in Pillar 3).
- **API Endpoint:**
  - `POST /api/pillars/environment-meda/calibrate` with `{"optical_depth_tau": 2.45, "air_temp_c": -35.0, "pressure_pa": 725.0, "wind_speed_ms": 18.4}`
- **Expected Values & Verifiable Evidence:**
  - **Atmospheric State:** Column optical depth $\tau = 2.45$ (Sol 89 Regional Dust Storm), $T_{\text{air}} = -35.0^\circ\text{C}$, $P = 725.0\,\text{Pa}$, Wind $18.4\,\text{m/s}$.
  - **Solar Array Degradation:** Output drops from $900.0\,\text{W}$ nominal to **$258.1\,\text{W}$** (an attenuation of **$-71.3\%$** via Beer-Lambert absorption).
  - **Battery Survival Heating:** Thermal load increases to **$72.5\,\text{W}$** to prevent battery electrolyte freezing.
  - **RF Dust Attenuation:** X-Band attenuation rises to **$0.158\,\text{dB/km}$** based on empirical Mie scattering:
    $$\alpha_{\text{RF}} = 0.008 + 0.098 \cdot \tau^{1.15}\,\text{dB/km}$$
  - **Operational Assessment:** `DEGRADED_OPERATIONS_DUST_STORM`.
- **Scientific Takeaway:** Rover traverse speeds and daily drive sol budgets must degrade realistically under dust storm conditions.

---

### Step 5: Multi-Objective A* Comparative Science Trade Study
- **Evaluator Goal:** Evaluate the core planning engine's ability to trade off mobility costs against astrobiological science yield.
- **UI Interaction:** Click Step **`5. SCIENCE`** and click **`▶ EXECUTE STEP ACTION`** (or click `Compare Direct vs Science-Optimized Traverse` in Pillar 4).
- **API Endpoint:**
  - `POST /api/pillars/science-targets/plan` with:
    ```json
    {
      "start_rc": [153, 123],
      "goal_rc": [50, 90],
      "target_ids": ["sci_wildcat_ridge", "sci_kodiak_butte"]
    }
    ```
- **Expected Values & Verifiable Evidence:**
  | Evaluation Metric | Route A (Direct Corridor) | Route B (Science-Priority Detour) | Trade-Off Delta |
  | :--- | :--- | :--- | :--- |
  | **Traverse Distance** | $2,309.7\,\text{m}$ | $5,406.2\,\text{m}$ | **$+3,096.5\,\text{m}$ ($+134.1\%$)** |
  | **Estimated Mobility Energy**| $659.9\,\text{Wh}$ | $1,567.1\,\text{Wh}$ | **$+907.2\,\text{Wh}$ ($+137.5\%$)** |
  | **Travel Time** | $1.28\,\text{hours}$ | $3.00\,\text{hours}$ | $+1.72\,\text{hours}$ |
  | **Science Yield Score** | **$0\,\text{pts}$** (Bypasses targets $>30\,\text{m}$) | **$+160\,\text{pts}$** (Wildcat Ridge + Kodiak) | **$+160\,\text{pts}$ Gain** |
- **Scientific Takeaway:** Route A cuts straight from Three Forks to the Delta Scarp Rim, passing $297.3\,\text{m}$ away from Wildcat Ridge and $835.5\,\text{m}$ away from Kodiak Butte—yielding zero scientific return. Route B justifies a $+134\%$ distance detour to sample organic carbon signatures detected by SHERLOC at Wildcat Ridge and deltaic stratigraphy at Kodiak Butte.

---

### Step 6: Autonomous Resilience & Detour ("When Mars Goes Dark")
- **Evaluator Goal:** Witness autonomous onboard fault recovery when orbital communication is cut off during a regional dust storm.
- **UI Interaction:** Click Step **`6. DETOUR`** and click **`▶ EXECUTE STEP ACTION`** (or click `Launch "When Mars Goes Dark" Replay` in Pillar 5).
- **API Endpoint:**
  - `POST /api/flagship/when-mars-goes-dark/run`
  - `GET /api/flagship/when-mars-goes-dark/replay`
- **Expected Values & Verifiable Evidence:**
  - **Trigger Event:** High-consequence rockfall hazard detected at Hawksbill Gap entrance during a 4-hour orbital comms blackout (Sols 88–92).
  - **Triage Phase:** Safe Hold commanded at $T+01\text{h}:45\text{m}$. Primary corridor deemed impassable.
  - **Autonomous Detour:** Autonomous planner computes an alternate lateral ridge ascent traverse.
  - **Orbital Restoration:** The lateral ridge path climbs out of terrain radio shadow, restoring Line-of-Sight (LoS) communication to the Mars Reconnaissance Orbiter (MRO) while the primary corridor remains occluded.
- **Scientific Takeaway:** The rover makes mission-critical safety and routing decisions locally without requiring Earth ground control intervention.

---

### Step 7: Cryptographic Proof & DTN Custody Audit
- **Evaluator Goal:** Audit tamper-proof mission logs and verify zero telemetry loss across the communications blackout.
- **UI Interaction:** Click Step **`7. MERKLE`** and click **`▶ EXECUTE STEP ACTION`**.
- **API Endpoint:**
  - `GET /api/flagship/when-mars-goes-dark/replay`
- **Expected Values & Verifiable Evidence:**
  - **Merkle State Root Hash:**
    `0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8`
  - **State Tree Reconciliation:** **7 out of 7** mission snapshots cryptographically verified (0 tamper vectors).
  - **RFC 9171 Delay-Tolerant Networking (DTN) Custody:** **100% Data Yield (6 of 6 telemetry bundles delivered)**. Exactly **$0\,\text{KB}$ data lost** despite the complete 4-hour communication blackout.
- **Scientific Takeaway:** Proves mathematical verifiability and deep-space network compliance using RFC 9171 Bundle Protocol standards.

---

## 3. Evaluator Command-Line Reproduction Battery

Evaluators wishing to audit the entire system headlessly from the terminal on Linux can run the following automated test suites:

```bash
# 1. Authenticate All 8 Planetary Datasets on Disk (SHA-256 Checksums)
.venv/bin/python scripts/audit_nasa_data.py

# 2. Run Comprehensive Scientific Validation Battery (25/25 Tests)
.venv/bin/python scripts/validate_nasa_data.py

# 3. Execute Pytest Five-Pillar Integration Suite (8/8 Tests)
./scripts/run_tests.sh tests/test_nasa_data_integration.py

# 4. Execute "When Mars Goes Dark" Mission Rehearsal Suite (9/9 Tests)
./scripts/run_tests.sh tests/test_when_mars_goes_dark_integration.py

# 5. Run Automated Headless Browser Golden Path Audit (CDP Automation)
.venv/bin/python scripts/audit_golden_path_browser.py
```

All 5 commands return exit code `0` on clean execution.

---

## 4. Evaluator FAQ & Common Pitfalls

### Q1: Is the route planner claiming these paths are operationally safe for astronauts?
**A:** **NO.** Per rule `AGENTS.md` and planetary flight safety rules, all routes generated by MarsWalk are **modeled algorithmic estimates** based on USGS digital elevation data and mobility heuristics ($15^\circ$ vehicle slope limits). They are **never designated as operationally certified or human-crew safe**.

### Q2: Why did Route A and Route B previously report identical distances?
**A:** In earlier sprints, the planner defaulted to terminating at Wildcat Ridge (`row: 135, col: 91`). When Route B added Wildcat Ridge as a midpoint target, the waypoint set was identical. In Mission 6, the destination was corrected to Delta Scarp Rim Crest (`row: 50, col: 90`), and strict 30m interception radii were enforced. Route A now bypasses the sites ($2,309.7\,\text{m}$, 0 pts), while Route B detours to both ($5,406.2\,\text{m}$, $+160\,\text{pts}$).

### Q3: Why is Tube #268 (Hazelton) not in the Three Forks depot list?
**A:** Tube #268 (*Hazelton*, cored from Wildcat Ridge) is **retained onboard the Perseverance rover** for primary Mars Sample Return. Its paired duplicate core, *Bearwallow* (Tube #239), was deposited at Three Forks. Tube #241 deposited at Three Forks is *Malay*. MarsWalk accurately reflects this historical reality.

### Q4: How does MarsWalk handle headless browser execution without an X11 display?
**A:** MarsWalk includes native Chrome DevTools Protocol (CDP) runners (`scripts/audit_browser_linux.py` and `scripts/audit_golden_path_browser.py`) that launch Google Chrome via `--headless=new --no-sandbox`, connect over WebSockets, interact with DOM elements, and capture 1080p visual proof PNGs into `outputs/browser_qa/`.
