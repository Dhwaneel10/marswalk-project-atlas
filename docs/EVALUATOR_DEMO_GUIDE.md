# MARSWALK 2.0 / PROJECT ATLAS — EVALUATOR DEMO GUIDE
## Comprehensive Evaluation Manual for Hackathon Judges &amp; Planetary Engineers

**Document Version:** 1.0.0  
**Target Platform:** Ubuntu 22.04 LTS (x86_64)  
**Demonstration Port:** `3000` (configurable via `--port`)  
**URL:** [http://127.0.0.1:3000](http://127.0.0.1:3000)  

---

## 1. QUICK-START: ONE-COMMAND AUTOMATED VERIFICATION

Judges and evaluators can verify the entire platform, all 8 planetary datasets, all 25 science validation gates, all integration and resilience test suites, and the live headless Chrome Golden Path audit with a single command:

```bash
# Enter the submission repository and run the 9-gate release preflight battery:
cd /home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission
./scripts/release_preflight.sh 3000
```
*Expected Result: ALL 9 QUALITY GATES PASSED (100% QUALIFIED).*

Alternatively, each individual audit component can be executed independently:

```bash
# 1. Run the automated data integrity audit (8/8 Checks)
.venv/bin/python scripts/audit_nasa_data.py

# 3. Run the comprehensive planetary science validation gates (25/25 Checks)
.venv/bin/python scripts/validate_nasa_data.py

# 4. Run the Five-Pillar integration test suite (8/8 Tests)
./scripts/run_tests.sh tests/test_nasa_data_integration.py

# 5. Run the flagship "When Mars Goes Dark" resilience test suite (9/9 Tests)
./scripts/run_tests.sh tests/test_when_mars_goes_dark_integration.py

# 6. Execute the end-to-end showcase script against the live server
./scripts/run_showcase.sh 3000

# 7. Execute automated headless browser Golden Path audit via Chrome DevTools Protocol (7/7 Steps)
.venv/bin/python scripts/audit_golden_path_browser.py
```
*Expected Result: 100% of audits and tests pass with zero errors.*

---

## 2. 5-MINUTE GUIDED BROWSER WALKTHROUGH

Open [http://127.0.0.1:3000](http://127.0.0.1:3000) in Chrome, Firefox, or any modern WebGL-capable browser.

> **QUICK TIP — INTERACTIVE EVALUATOR TOUR:**  
> Click the yellow **`★ EVALUATOR TOUR`** button in the header of the Five-Pillar Operations Deck. It opens an interactive 7-step guided HUD that walks through all 7 steps with one-click automated actions and real-time live data inspection! For full step documentation, see [docs/EVALUATOR_GOLDEN_PATH.md](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/docs/EVALUATOR_GOLDEN_PATH.md).

```
========================================================================================
STEP 1: THE FIVE-PILLAR PLANETARY INTELLIGENCE DECK
========================================================================================
Location: Center-top control deck (Tab 0: "PILLARS") or click "★ EVALUATOR TOUR"

1. Click "PILLAR 1: USGS TERRAIN":
   - Observe: Displays USGS CTX 20m DEM (5km x 5km) and USGS TRN HiRISE 1m DTM (600m).
   - Action: Click "[🔍 Inspect Hawksbill Gap (1m)]" button in the action tray.
   - Result: Shows point inspection at Wildcat Ridge: 1.0 m/px resolution, 9.4° slope,
     elevation -2,554.7m, and primary USGS DOI citation.
   - Action: Click "[🔍 Inspect Crater Floor Base (20m CTX)]".
   - Result: Shows resolution shifts to 20.0 m/px, slope 3.0°, elevation -2,480.5m.

2. Click "PILLAR 2: PDS GROUND TRUTH":
   - Observe: 577 archived tactical drives across Sols 13–1896 and 10 Three Forks tubes.
   - Action: Click "[🧪 List Three Forks Depot (10 Tubes)]".
   - Result: Renders an interactive table displaying all 10 surface-cached sample tubes
     (Malay, Mageik, Crosswind Lake, Roubion, Coulettes, Montdenier, Bearwallow, Skyland,
     Atsah, and Amalik Witness) with sol cored and lithology.

3. Click "PILLAR 3: MEDA WEATHER":
   - Observe: Diurnal pressure minimum (712.2 Pa) and maximum (758.1 Pa), air temp range
     (-88.2°C to -12.5°C), and peak gusts up to 24.6 m/s.
   - Action: Click "[🌪️ Regional Storm (τ=2.45)]".
   - Result: Digital twin dynamically recalculates solar array output (drops to 154 W),
     battery heating demand rises, atmospheric density updates, and RF dust attenuation
     increases to 0.245 dB/km.

4. Click "PILLAR 4: SCIENCE PLANNING":
   - Action: Click "[⚡ Compare Direct vs Science-Optimized Traverse]".
   - Result: Renders a multi-objective trade-off table comparing Route A (Direct Sortie)
     against Route B (Science-Optimized Multi-Stop via Wildcat Ridge).
   - Takeaway: Route B earns +95 astrobiology points for a minor +11.3 Wh battery draw.

5. Click "PILLAR 5: RESILIENCE & DTN":
   - Action: Click "[🔒 Verify Merkle Proof & DTN Yield]".
   - Result: Confirms bit-exact root 0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8,
     reconciling all 7 mission snapshots with 100% data yield across the 4-hour blackout.
```

```
========================================================================================
STEP 2: 3D TERRAIN WORKSTATION & PLANETARY GIS OVERLAYS
========================================================================================
Location: Top navigation bar -> Click "FLY TO JEZERO" (or click Jezero target marker)

1. Visualizing the Surface:
   - The 3D viewport renders authentic USGS CTX 20m photogrammetric terrain.
   - Notice the Cyan Rectangular Box: Delineates the 600m x 600m Hawksbill Gap ascent
     window (1.0 m/px HiRISE micro-hazard coverage).
   - Notice the Amber Polyline: Renders Perseverance's actual 577 historical tactical drives.
   - Notice the White Cylinders: Renders all 10 Three Forks Sample Depot titanium tubes.
   - Notice the Violet Diamonds: Renders the geolocated astrobiology targets (Wildcat Ridge).

2. Interactive Spatial Raycasting:
   - Click directly on the Cyan HiRISE boundary box or Wildcat Ridge:
     The "THEATER SPATIAL INSPECTOR" card slides in, identifying the high-resolution
     1m DTM footprint, exact Horn slope, and elevation.
   - Click on any of the White Sample Tubes at Three Forks:
     The inspector reveals the Tube Serial Number, rock core lithology, and sol cored.
   - Click on the Violet Diamond at Wildcat Ridge:
     The inspector reveals the active instruments (SHERLOC Raman, PIXL XRF) and discovery notes.

3. GIS Layer Toggles:
   - Open Tab 2 ("PLAN"): Locate the "PLANETARY GIS OVERLAYS" control card.
   - Toggle the checkboxes for HiRISE 1m DTM, PDS Traverse, Three Forks Depot, and
     Science Targets to independently show or hide each spatial intelligence layer.
```

```
========================================================================================
STEP 3: RUNNING THE AUTONOMOUS FLAGSHIP SCENARIO
========================================================================================
Location: Tab 1 ("WHEN MARS GOES DARK")

1. Click the large cyan button: "[🚀 EXECUTE FLAGSHIP REHEARSAL]".
2. The simulation automatically initiates the 7-stage causal replay:
   - Stage 0: Rover departs Three Forks Depot and reaches Wildcat Ridge under clear skies.
   - Stage 1: MEDA sensors detect rising atmospheric opacity (τ rises from 0.82 to 2.45).
   - Stage 2: Direct line-of-sight is lost; RFC 9171 DTN custody buffer engages.
   - Stage 3: A 60m rockfall hazard occludes the primary Hawksbill Gap ascent chute.
   - Stage 4: Vehicle safe-holds, evaluates terramechanics, and generates an adaptive
     lateral ridge detour (+420m climb).
   - Stage 5: Rover crests the delta rim, restoring geometric LOS to MRO; all 6 custodian
     bundles are transferred with 0 KB data loss.
   - Stage 6: The cryptographic Merkle tree audit confirms bit-exact state reconciliation.
```

---

## 3. CORE ARCHITECTURAL COMMITMENTS

| Evaluation Criterion | Implementation Details |
|:---|:---|
| **Real NASA Data** | USGS Jezero CTX 20m DEM, USGS TRN HiRISE 1m DTM, NASA PDS Perseverance tactical coordinates (Sols 13–1896), Three Forks sample depot tubes, NASA MEDA diurnal weather records. |
| **No Synthetic Observation Claims** | Clear demarcation between measured historical archives, derived physical quantities (Horn slope, terramechanical work), and simulated mission decisions. |
| **Scientific Defensibility** | Primary DOIs provided for all datasets; elevation deltas at 5 geodetic control points verified between $-0.43\,\text{m}$ and $-5.09\,\text{m}$. |
| **Deterministic Reproducibility** | Bit-exact Merkle root `0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8` guarantees zero simulated state tampering. |
| **Platform Compatibility** | 100% native Linux on Ubuntu 22.04 LTS (Python 3.10 virtual environment, Three.js WebGL client). |
| **Safety Transparency** | Non-probabilistic truth disclosure: No modeled route is presented as certified safe for human astronauts. |

---
*Evaluator guide prepared by Project MarsWalk Systems Engineering Team.*
