# MISSION 11 — FINAL ENGINEERING HANDOVER & 25 QUESTIONS ANSWERED

**Project:** MarsWalk 2.0 / Project Atlas  
**Workspace:** `/home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission`  
**Reference Source (Immutable):** `/home/mech_ka_launda/projects/NASA-SpaceApps-2026/Atlas-Source/MarsWalk`  
**Release Branch:** `mission-11-final-challenge-validation`  
**Certified Release Archive:** [`outputs/releases/marswalk-v2.0.0-rc3.tar.gz`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/releases/marswalk-v2.0.0-rc3.tar.gz)  
**Archive SHA-256:** `49c4fd1dc49283e6c2cb723296a0f0cddea66c5d73293c1a5a78e15f9788799a`  
**Total Tests:** **1,289 Passed / 1,289 Total (100.0% Pass Rate)**  

---

## 1. Quick-Start Guide for Evaluators

### 1.1 Automated Clean-Room Launch
```bash
cd /home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission

# 1. Run full test suite (1,289 unit and integration tests)
./scripts/run_tests.sh

# 2. Launch the local Atlas HTTP server daemon on port 3000
./scripts/start_atlas.sh --port 3000 --no-browser

# 3. Open workstation interface in your web browser
# Standard URL:   http://127.0.0.1:3000/
# Evaluator Demo: http://127.0.0.1:3000/?mode=demo
```

### 1.2 Interactive Evaluator Tour (7-Step Golden Path)
1. Navigate to `http://127.0.0.1:3000/?mode=demo`.
2. Click **"EVALUATOR TOUR"** in the top navigation header.
3. Click through Steps 1 to 7 to experience the complete mission story:
   - **Step 1:** Octavia E. Butler Base initialization on the Jezero crater floor.
   - **Step 2:** Layered USGS CTX terrain slopes and MEDA atmospheric baseline.
   - **Step 3:** Multi-profile route generation (Conservative vs Balanced vs Science-First).
   - **Step 4:** Injected Sol 89 dust storm and topographic radio communication blackout.
   - **Step 5:** Autonomous RFC 5050 DTN custody bundle transfer.
   - **Step 6:** Dynamic rockfall detection at Hawksbill Gap and automatic detour replanning.
   - **Step 7:** Communications restoration at Ridge Terrace and Merkle root verification.

---

## 2. Answers to the 25 Key Questions (In Plain Language)

### Q1: Does the entire application actually work?
**YES.** Every layer of MarsWalk 2.0 works end-to-end. The Python HTTP server daemon, A\* routing engine, Three.js/Cesium 3D planetary rendering, cockpit HUD, multi-stop tour optimizer, and resilience simulator all run live and were validated via automated Chrome CDP browser testing.

### Q2: Can every important feature be run from beginning to end?
**YES.** You can launch the server, select custom start and goal coordinates, choose locomotion modes (`crew_eva` or `robotic_rover`), select routing profiles, inject rockfall closures, execute the 5-Sol "When Mars Goes Dark" dust storm contingency, scrub the timeline slider, and inspect preflight diagnostic checks.

### Q3: Is the scientific data genuinely from NASA, or is it from other sources?
**It is from a multi-agency planetary science consortium.** The rover tactical localization (PLACES) and atmospheric weather (MEDA) are genuine NASA PDS datasets. However, the elevation maps (DTMs) were processed and published by the **USGS Astrogeology Science Center**, the nomenclature is from the **IAU**, and the climatology models are from **European research institutions (CNES/LMD/ESA)**.

### Q4: What percentage of the data is NASA vs USGS vs European vs simulated?
By byte volume across 55 project data assets ($29.70\,\text{MB}$ total):
- **USGS Astrogeology & IAU:** **60.3%** ($17.92\,\text{MB}$) — CTX and HiRISE digital elevation models, Viking basemap, and planetary gazetteer.
- **NASA PDS & JPL:** **18.0%** ($5.36\,\text{MB}$) — Mars 2020 PLACES rover telemetry, Three Forks sample drops, and MEDA weather logs.
- **Application Pipeline & Simulation Heuristics:** **20.4%** ($6.07\,\text{MB}$) — Clipped operational rasters, resilience scenarios, and preference configs.
- **European Space Agency / CNES / LMD:** **1.2%** ($0.35\,\text{MB}$) — Mars Climate Database (MCD v6.2) atmospheric GCM NetCDF files.

### Q5: Does the application use machine learning, or does it use classical AI algorithms?
**It uses classical AI algorithms for pathfinding and physics, combined with statistical machine learning for operator preference adaptation.**
- Point-to-point and multi-stop traverses use **directed 8-connected A\* search** and **bounded beam search**.
- Multi-criteria trade-offs use **Pareto frontier optimization** (non-dominated sorting).
- Surface slopes use **Horn's 8-neighbor gradient filter**.
- Flight director preference learning uses a **regularized Bradley-Terry pairwise logistic regression model** solved via SciPy's L-BFGS-B convex optimizer.

### Q6: Are there any trained model weights in the repository?
**NO.** There are zero pre-trained deep learning weight files (`.pt`, `.pth`, `.onnx`, `.h5`, `.bin`, `.joblib`) in the repository. No neural network inference graphs are bundled. The statistical preference model learns dynamically online from operator feedback.

### Q7: How does the preference learning model work mathematically?
When a flight director chooses route $\mathbf{x}_{\text{sel}}$ over alternatives $\mathbf{x}_{\text{rej}}$, MarsWalk computes feature difference vectors $\mathbf{z} = \mathbf{x}_{\text{sel}} - \mathbf{x}_{\text{rej}}$ across 4 normalized metrics: distance, slope risk, surface roughness, and science score. It minimizes an $L_2$-regularized cross-entropy loss:
$$\mathcal{L}(\mathbf{w}) = \sum \ln(1 + e^{-\mathbf{w}^T \mathbf{z}}) + \frac{\lambda}{2} \|\mathbf{w}\|_2^2$$
using SciPy's L-BFGS-B optimizer, yielding a linear utility function $U(\mathbf{x}) = \mathbf{w} \cdot \mathbf{x}$ to rank future candidate routes without ever violating hard safety constraints.

### Q8: Does the application make live network requests during runtime?
**NO.** MarsWalk makes zero outbound network requests to external servers during runtime. All 220 frontend `fetch()` calls in `web/app.js` point to the local loopback interface (`http://127.0.0.1:3000/api/...`) or local asset files.

### Q9: Can the application run completely offline in an air-gapped environment?
**YES.** You can unplug the ethernet cable or disable Wi-Fi entirely; the application, server daemon, and all 1,289 tests run with 100% functionality because all elevation grids, weather baselines, and 3D libraries (Three.js, OrbitControls) are stored locally in the repository.

### Q10: What coordinate reference system is used, and why was it chosen?
MarsWalk uses **`ESRI:103885` (IAU 2000 Mars Spheroid / Equirectangular Projection)**, with semi-major axis $a = 3,396,190\,\text{m}$, planetocentric latitude, and positive East longitude. It was chosen because it is the official cartographic standard adopted by USGS Astrogeology and NASA JPL for Mars 2020 Terrain Relative Navigation (TRN) products.

### Q11: What is the vertical datum, and what do negative elevations mean?
The vertical datum is the **MOLA Delta Geoid** (areoid), where $0\,\text{m}$ elevation is defined by the mean gravitational equipotential surface where Mars atmospheric pressure equals $610.5\,\text{Pa}$ (the triple point of water). All elevations in Jezero Crater are negative ($-2,565\,\text{m}$ at the crater floor to $-2,250\,\text{m}$ at the delta rim) because the impact basin lies deep below the Martian planetary reference datum.

### Q12: How does the 20m CTX terrain relate to the 1m HiRISE terrain?
The $20\,\text{m/pixel}$ Context Camera (CTX) mosaic provides regional elevation coverage across the full $5.0 \times 5.0\,\text{km}$ mission area. The $1\,\text{m/pixel}$ High Resolution Imaging Science Experiment (HiRISE) DTM covers a nested $600 \times 600\,\text{m}$ sub-window at Hawksbill Gap, providing micro-topographic detail for navigating the steep delta scarp ascent. Both rasters share the exact same CRS and geoid datum.

### Q13: How accurate is the rover ground truth data, and what is its source?
The ground truth rover data originates from the **NASA Planetary Data System (PDS) Geosciences Node** Mars 2020 Rover PLACES archive (`best_tactical.csv`). It represents 577 tactical localization stations calculated by JPL rover planners using wheel odometry, visual odometry, and orbital image resection, accurate to sub-meter tactical precision.

### Q14: How were the 10 Three Forks sample tubes deposited and cataloged?
Between Sols 653 and 676, Perseverance dropped 10 hermetically sealed titanium sample tubes on the crater floor at Three Forks to serve as a backup cache for Mars Sample Return. MarsWalk ingests authentic JPL drop records (`pds_three_forks_sample_drops.csv`) recording tube names (Malay, Mageik, Crosswind Lake, etc.), surface imagery, and geological rock type.

### Q15: What real measurements did the MEDA sensor make on the surface of Mars?
The Mars Environmental Dynamics Analyzer (MEDA) measured surface atmospheric pressure ($690$ to $775\,\text{Pa}$ showing semi-diurnal thermal atmospheric tides), air temperature at $1.45\,\text{m}$ ($-88.4^\circ\text{C}$ to $-11.2^\circ\text{C}$), radiometric ground surface temperature, relative humidity, wind velocity vectors, and dust optical depth ($\tau$).

### Q16: How is the Sol 89 dust storm modeled, and is it real or simulated?
The presence of a regional dust event around Sol 89 is **historically real** (observed by MEDA sensors). However, the sudden step-function spike to $\tau = 4.2$ used in the "When Mars Goes Dark" scenario is an **illustrative engineering simulation** designed to test autonomous rover/crew reaction logic, and is explicitly labeled as such in the user interface.

### Q17: How does the RF communication blackout and DTN custody protocol work?
When the rover descends into the delta channel, line-of-sight to the orbital relay antenna is blocked by the crater scarp. Rather than dropping scientific telemetry, the rover activates **RFC 5050 Delay-Tolerant Networking (DTN)** custody transfer, securely queuing bundles in non-volatile flash memory until line-of-sight is restored at Ridge Terrace.

### Q18: How does the dynamic detour replanning work when a corridor is blocked?
When a simulated rockfall hazard closes Hawksbill Gap, the A\* graph search updates the cost matrix by setting closed grid cells to infinity ($\infty$). The replanner initiates an incremental A\* search from the vehicle's current position to the destination, automatically discovering the alternate northern switchback corridor.

### Q19: How does MarsWalk align with the 2026 NASA Space Apps Marswalk challenge?
It directly meets every criterion of the challenge: creating an interactive route-planning tool for human Mars exploration that layers multiple authentic planetary datasets (elevation, imagery, weather, geology, nomenclature), models obstacles and astronaut safety hazards, evaluates multi-criteria trade-offs, and functions reliably.

### Q20: What is the difference between rover locomotion and human crew EVA?
Robotic rovers move slowly ($\sim 0.12\,\text{km/h}$) under low slope limits ($15^\circ$) with multi-Sol planning windows. Human astronauts on foot (`crew_eva`) move 16 times faster ($\sim 2.0\,\text{km/h}$) and can negotiate steeper inclines ($25^\circ$), but face strict $8.0\text{-hour}$ life-support consumable caps and lethal environmental exposure limits.

### Q21: What are the bio-energetic limits and walkback safety envelope for astronauts?
In Martian gravity ($0.38g$), suited walking burns approximately $320\,\text{kcal/hr}$ and consumes $\sim 50\,\text{liters}$ of oxygen per hour. Under the Apollo walkback rule, astronauts must remain within a **$4.0\,\text{km}$ radius of base** so that in the event of an exploration vehicle failure, the crew pair can walk back on primary PLSS suit reserves alone.

### Q22: Why must a modeled route never be called operationally safe for astronauts?
Because computer simulations on $20\,\text{m}$ orbital rasters cannot detect sub-pixel hazards such as sharp ventifact rocks, loose scree slips, crevasse fractures, or spacesuit joint pinch fatigue. Calling an unvalidated model "operationally safe" would create false confidence and violate NASA safety protocol. All routes are research decision-support models.

### Q23: What official NASA resources were used and integrated into the project?
1. NASA Mars Trek (WMTS basemap imagery registry).
2. USGS Astrogeology Jezero Geologic Mapping (MRO CTX and HiRISE DTMs).
3. NASA Mars 2020 MMGIS ("Where is Perseverance?" waypoints and traverse).
4. NASA PDS Geosciences Node (Rover PLACES tactical telemetry).
5. NASA PDS Atmospheres Node (MEDA atmospheric weather sensors).
6. NASA JPL Mars Sample Return (Three Forks sample depot records).

### Q24: How many total tests exist in the test suite, and what is the pass rate?
There are **1,289 tests** collected across 48 test modules in `tests/`. The pass rate is **100.0% (1,289 passed / 1,289 total)** with 0 failures, 0 skips, and 0 errors, running in $376.99\,\text{seconds}$.

### Q25: What is the final release package, its size, and its cryptographic hash?
- **Package Archive:** `outputs/releases/marswalk-v2.0.0-rc3.tar.gz`
- **Archive File Size:** $16,968,582\,\text{bytes}$ ($16.18\,\text{MB}$)
- **Files Contained:** $1,090\,\text{files}$
- **Cryptographic SHA-256:**
  ```text
  49c4fd1dc49283e6c2cb723296a0f0cddea66c5d73293c1a5a78e15f9788799a
  ```
