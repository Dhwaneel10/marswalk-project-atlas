# MarsWalk 2.0 / Project Atlas — Evaluator & Judge Q&A Compendium

**Document Identifier:** `MW-M9-JUDGE-QA`  
**Total Questions:** 22 Rigorous Inquiries Across Science, Engineering, and Mission Operations  
**Audience:** Technical Judges, Science Reviewers, and Systems Auditors  
**Standard of Conduct:** Truth-first, evidence-backed disclosures; explicit acknowledgment of modeling assumptions and unknowns.

---

## Section I: Planetary Science & Ground Truth

### Q1: What specific elevation models are used, and how was coordinate alignment verified?
**Answer:** We ingest the USGS Astrogeology CTX DEM for Jezero Crater (`DOI: 10.5066/P9T31O12`, 20 m/pixel) and the USGS TRN HiRISE DTM for Hawksbill Gap (`DOI: 10.5066/P13CPYYU`, 1.0 m/pixel). Both rasters use the IAU 2000 Mars Spheroid ($R = 3,396,190\,\text{m}$) and Equirectangular projection (ESRI:103885). Coordinate alignment was verified via automated affine transformation checks proving that the 600m HiRISE window is geometrically nested within the regional CTX grid with zero coordinate drift.  
**Evidence:** [`scripts/validate_nasa_data.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/scripts/validate_nasa_data.py#L55-L95), [`data/manifests/nasa_data_provenance_manifest.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/manifests/nasa_data_provenance_manifest.json#L15-L80).

### Q2: Are the Perseverance rover positions real NASA telemetry or simulated?
**Answer:** The 577 waypoint sites in our ground-truth database are directly parsed from the NASA Planetary Data System (PDS) Mars 2020 Rover PLACES Best Tactical bundle, spanning Sol 13 through Sol 1896 (33.2 km odometry).  
**Evidence:** [`data/raw/pds_places_best_tactical.csv`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/raw/pds_places_best_tactical.csv), [`data/catalogs/perseverance_ground_truth_places.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/catalogs/perseverance_ground_truth_places.json).

### Q3: How are the Three Forks sample drop locations verified?
**Answer:** All 10 deposited titanium sample tubes are cataloged using authentic NASA Mars 2020 mission records, including tube serial numbers, sample core lengths (e.g., *Mageik* 7.36 cm, *Malay* 6.0 cm), deposit sols (Sols 653–688), and ground-truth coordinates at Three Forks.  
**Evidence:** [`data/catalogs/three_forks_sample_depot_catalog.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/catalogs/three_forks_sample_depot_catalog.json).

### Q4: How is the atmospheric dust storm modeled, and what is the scientific source?
**Answer:** We model atmospheric extinction using the Beer-Lambert-Bougher solar transmission equation: $I = I_0 \cdot \exp(-\tau / \cos(z))$. During our signature scenario, optical depth spikes to $\tau = 2.15$, calibrated directly from NASA MEDA sensor observations recorded during the Sol 89 regional dust event in Jezero, resulting in a calculated $71.3\%$ solar irradiance loss.  
**Evidence:** [`src/marswalk/api/service.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/api/service.py#L10970-L11025), [`data/catalogs/meda_environmental_observations.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/catalogs/meda_environmental_observations.json).

### Q5: What units are reported by the weather endpoints?
**Answer:** Strictly SI units: Pressure in Pascals ($\text{Pa}$), ambient temperature in Celsius ($^\circ\text{C}$), wind speed in meters per second ($\text{m/s}$), and optical depth $\tau$ (dimensionless).  
**Evidence:** [`tests/test_nasa_data_integration.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/tests/test_nasa_data_integration.py#L125-L165).

### Q6: Can this system be used to guarantee astronaut safety on Mars?
**Answer:** **No.** While our terrain models reflect accurate USGS elevation and Horn slope kernels, human EVA traversal requires biomechanical oxygen consumption models, suit pressurization constraints, and micro-crevasse detection beyond 1m resolution. We explicitly disclose across all UI surfaces: *"NOT CERTIFIED AS AN OPERATIONALLY SAFE ROUTE FOR ASTRONAUTS."*  
**Evidence:** Disclosures in [`web/index.html`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/web/index.html#L199-L202) and [`AGENTS.md`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/AGENTS.md).

---

## Section II: Navigation, Optimization & Autonomy

### Q7: How does your pathfinding algorithm account for terrain slopes?
**Answer:** Slopes are computed dynamically across the 2D elevation grid using an 8-neighbor Horn kernel. Cells with slopes exceeding $15^\circ$ are marked as impassable barriers (infinite traversal cost) to prevent vehicle tip-over. For slopes $< 15^\circ$, an exponential terramechanics slip penalty is added to the A* movement heuristic.  
**Evidence:** [`src/marswalk/core/terrain.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/terrain.py).

### Q8: What is the Multi-Objective Science Trade-off?
**Answer:** The planner optimizes a multi-objective cost function:
$$J(\pi) = w_d \cdot D(\pi) + w_e \cdot E(\pi) + w_r \cdot R(\pi) - w_s \cdot S(\pi)$$
balancing total distance $D$, electrical energy expenditure $E$, slope hazard risk $R$, and astrobiology sample yield $S$. Users can toggle between *Direct Transit* (minimizing distance/time) and *High-Science* (diverting to high-yield mudstone targets for an additional $+160$ reward points).  
**Evidence:** [`src/marswalk/api/service.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/api/service.py#L11080-L11150).

### Q9: How is an unexpected rockfall handled during autonomous execution?
**Answer:** During the "When Mars Goes Dark" scenario, an injected scarp rockfall blocks the primary corridor. The vehicle's on-board mission coordinator detects the path obstruction, updates local cost grids, and executes a real-time re-plan through Hawksbill Gap without querying Earth or requiring human teleoperation.  
**Evidence:** [`src/marswalk/core/when_mars_goes_dark.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/when_mars_goes_dark.py#L180-L240).

---

## Section III: Telemetry, Networking & Cryptographic Proof

### Q10: How does the system handle communications blackouts?
**Answer:** We implement an Delay-Tolerant Networking (DTN) architecture conforming to RFC 9171 / RFC 5050 bundle protocol principles. When the vehicle enters radio shadow behind delta scarps, telemetry frames and instrument spectra are stored in flash custody buffers. Custody transfer acknowledges retention until the vehicle ascends Ridge Terrace and establishes line-of-sight RF communications.  
**Evidence:** [`src/marswalk/core/when_mars_goes_dark.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/when_mars_goes_dark.py#L250-L310).

### Q11: What is the Merkle root hash and why is it important?
**Answer:** Every state change in the 7-stage crisis recovery scenario generates a cryptographic SHA-256 hash incorporating the rover's position, battery state, science inventory, and DTN custody status. These hashes form a Merkle tree whose root hash is:
$$\mathtt{0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8}$$
Any alteration of mission parameters or re-execution on any computer produces this exact hash, providing mathematical proof of deterministic execution.  
**Evidence:** [`tests/test_when_mars_goes_dark_integration.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/tests/test_when_mars_goes_dark_integration.py#L60-L100).

---

## Section IV: Software Architecture & Reproducibility

### Q12: What third-party libraries and frameworks are required to run MarsWalk?
**Answer:** Minimal production stack: `numpy` (matrix math), `scipy` (k-d trees), `rasterio` (geotiff I/O), `affine` (coordinate transforms), `jsonschema` (contract validation), `requests`, `websockets`, and `pytest`. We use Python's built-in `http.server` instead of heavy web frameworks to ensure zero external services are needed. Frontend uses standard Three.js for 3D WebGL rendering.  
**Evidence:** [`requirements.txt`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/requirements.txt), [`pyproject.toml`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/pyproject.toml).

### Q13: Did the application undergo clean-room testing outside the developer environment?
**Answer:** **Yes.** We extracted the release tarball into an isolated `/tmp/marswalk-clean-room/` directory, created a clean virtual environment, installed dependencies via `scripts/setup_atlas.sh`, and executed all 9 quality gates on an alternate port (`3005`). All tests passed with 0 reliance on workspace files.  
**Evidence:** [`docs/MISSION_9_CLEAN_ROOM_REPORT.md`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/docs/MISSION_9_CLEAN_ROOM_REPORT.md).

### Q14: How does the API handle invalid, unphysical, or malicious inputs?
**Answer:** All endpoints enforce strict physical bounds: negative optical depth ($\tau < 0$), temperatures below absolute zero ($-273.15^\circ\text{C}$), negative pressure, and out-of-bounds raster coordinates immediately return structured HTTP 400 errors with diagnostic error messages. Unhandled HTTP 500 exceptions are eliminated.  
**Evidence:** [`tests/test_mission8_api_failure_resilience.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/tests/test_mission8_api_failure_resilience.py).

### Q15: What is the steady-state memory footprint and response latency?
**Answer:** Steady-state memory footprint is $155.7\,\text{MB}$ RSS. Querying health/manifest metadata takes $1.2$–$2.8\,\text{ms}$, terrain elevation queries take $54.9\,\text{ms}$, and computing a 250x250 multi-objective A* route takes $699.7\,\text{ms}$. Memory drift across 40 continuous stress runs was $+4.5\%$ due to normal Python allocator pooling with zero leaks.  
**Evidence:** [`docs/MISSION_8_PERFORMANCE_REPORT.md`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/docs/MISSION_8_PERFORMANCE_REPORT.md).

---

## Section V: Competition Alignment & Future Scope

### Q16: How does an external evaluator experience the platform in under 3 minutes?
**Answer:** Launch the application (`./scripts/start_atlas.sh`), open `http://localhost:3000`, and click the prominent golden **`★ EVALUATOR TOUR`** button. The 7-step guided HUD steps through data provenance, terrain slopes, sample depot, MEDA weather, science trade-off, rockfall detour, and Merkle verification with one click per step.  
**Evidence:** [`scripts/audit_golden_path_browser.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/scripts/audit_golden_path_browser.py).

### Q17: Can this system be extended to other regions on Mars like Gale Crater or Valles Marineris?
**Answer:** Yes. The cartographic gazetteer and raster ingest engine support arbitrary GeoTIFF DTMs. The UI includes regional preview cards for Gale Crater, Olympus Mons, and Valles Marineris. High-resolution routing is currently calibrated for Jezero Crater because of the combined availability of 20m CTX and 1m HiRISE TRN models.  
**Evidence:** [`web/index.html`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/web/index.html#L157-L198).

### Q18: What is your slip model and how is it calibrated?
**Answer:** Terramechanics slip follows a simplified Bekker pressure-sinkage formulation where slip ratio $s$ scales quadratically with local slope angle: $s = \min(0.8, 0.05 + 0.002 \cdot \theta^2)$. While representative of sandy delta deposits, it does not currently simulate localized duricrust break-through or wheel grousers.  
**Evidence:** [`src/marswalk/core/terrain.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/terrain.py).

### Q19: How are the science target priority scores assigned?
**Answer:** Scores are assigned based on astrobiological preservation potential documented by the Mars 2020 Science Team: Fine-grained deltaic mudstones (*Wildcat Ridge*) receive 95 points; delta sandstones (*Skinner Ridge*) receive 85 points; igneous crater floor basalt (*Máaz*) receives 60 points.  
**Evidence:** [`data/catalogs/geolocated_science_targets.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/catalogs/geolocated_science_targets.json).

### Q20: What are the main known limitations of the current demonstrator?
**Answer:**
1. Global 3D globe uses static Viking MDIM 2.1 textures; real-time 1m HiRISE terrain is localized to Jezero Crater.
2. Atmospheric dust scattering uses a 1D column model rather than a full 3D Mars Regional Atmospheric Modeling System (MRAMS).
3. The rover battery model assumes constant thermal degradation rather than dynamic radioisotope thermoelectric generator (MMRTG) waste-heat scavenging.

### Q21: What happens if an evaluator's machine does not have Google Chrome installed?
**Answer:** The Atlas HTTP server and REST APIs run 100% independently of Chrome. All scientific validation gates, integration tests, and gauntlet benchmarks run via terminal (`./scripts/run_tests.sh`). Headless Chrome is only required for automated browser visual screenshot capture (Gate 8).

### Q22: Is the codebase reproducible on non-Ubuntu Linux systems?
**Answer:** Yes. Any modern POSIX-compliant x86_64 or aarch64 Linux environment (Debian, Fedora, Arch) with Python 3.10+ and GDAL/PROJ library support will execute the full platform.
