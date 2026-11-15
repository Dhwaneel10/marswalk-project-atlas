# MISSION 16B: COMPLETE HOMEPAGE WALKTHROUGH & VISUAL GUIDE

**Project:** MarsWalk 2.0 / Project Atlas  
**Interface:** Landing Page & Planetary Mission Control Gateway (`http://127.0.0.1:3000/`)  
**Target Release:** `v2.5.0-jezero-verified`  
**Client Files:** [web/index.html](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/web/index.html), [web/styles.css](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/web/styles.css), [web/app.js](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/web/app.js)  

---

## 1. Overview for First-Time Evaluators

When an evaluator or judge opens **MarsWalk 2.0** (`http://127.0.0.1:3000/`), they are greeted by an immersive, dark-space planetary control interface inspired by modern aerospace glassmorphism and cinematic space operations software. 

The homepage immediately establishes the two primary pillars of the system:
1. **Real Planetary Data Truth:** Every calculation is grounded in genuine NASA and USGS planetary datasets (USGS 20m CTX Stereo DTM, NASA PDS Mars 2020 ground truth, and MEDA in-situ atmospheric records).
2. **Human-First Planetary Exploration:** While honoring the 33.2 km rover traverse of Perseverance, MarsWalk prioritizes **Astronaut EVA Mode**—evaluating metabolic expenditure, terrain slope impedance, life support consumable envelopes, and safe-haven return corridors.

---

## 2. Detailed Top-to-Bottom Component Breakdown

### 2.1 Navigation Header & Brand Bar
- **Brand Identifier:** `MARSWALK 2.0 // PROJECT ATLAS` in crisp monospaced typography with an active glowing telemetry dot indicating local service connectivity.
- **Navigation Controls:**
  - `ASTRONAUT EVA`: Immediate shortcut to open the 3D surface workstation configured for human sortie planning.
  - `ROVER MISSION`: Enters robotic operations mode, showing the actual 33.2 km path driven by Perseverance across Sols 0–1000+.
  - `TERRAIN`: Triggers inspection of the 20m CTX Digital Terrain Model and slope analysis overlays.
  - `SCIENCE TARGETS`: Highlights the 12 curated Jezero river delta outcrop waypoints.
  - `⚙ PREFLIGHT`: Opens the 12-point automated diagnostics modal.

---

### 2.2 Hero Section & Epistemic Truth Metadata
Located in the primary viewport, the hero section provides immediate situational awareness without overwhelming the user.

- **Kicker Row & Epistemic Badges:**
  - `NASA SPACE APPS CHALLENGE 2026` (Gold-bordered competition badge).
  - `IAU 2000 MARS SPHERE`: Discloses coordinate reference datum ($R = 3,396,190\text{ m}$).
  - `USGS 20M CTX STEREO DTM`: Confirms elevation matrix resolution.
  - `PDS MEDA SOL 89 DUST STORM`: Declares authentic meteorological boundary data.
- **Headline:**
  > **EXPLORE MARS.**  
  > **PLAN THE HUMAN EXPEDITION.**
- **Sub-headline & Description:**
  Concise explanation of the platform's purpose: dual-mode surface operations enabling planetary scientists and astronauts to model traverses across Jezero Crater with rigorous biophysical modeling and autonomous contingency re-planning.

---

### 2.3 Streamlined Call-to-Action (CTA) Cluster
The hero CTA cluster has been reduced from legacy clutter into a disciplined 6-button operations group:

1. **`⚡ ENTER ASTRONAUT EVA MODE` (Primary Action):**
   - *Visual Style:* High-contrast radiant amber gradient (`linear-gradient(135deg, #f59e0b 0%, #d97706 100%)`).
   - *Behavior:* Dismisses landing overlay, opens the 3D Jezero workstation, selects the `tabPlan` inspector, and sets Astronaut EVA as the active planning regime.
2. **`★ EVALUATOR TOUR`:**
   - *Behavior:* Initiates a guided 7-step walkthrough highlighting data provenance, terrain elevation profiles, and route optimization.
3. **`★ 5-Min Showcase`:**
   - *Behavior:* Runs an automated presentation showcasing the flagship "When Mars Goes Dark" dust storm contingency and autonomous recovery.
4. **`Workstation Canvas →`:**
   - *Behavior:* Direct access into the 3D Three.js terrain canvas for freeform navigation.
5. **`⚙ Preflight Check`:**
   - *Behavior:* Runs real-time diagnostics verifying API endpoints, DEM grid caches, and memory allocations.
6. **`How It Works`:**
   - *Behavior:* Smoothly scrolls down to the algorithmic architecture and methodology section.

---

### 2.4 Jezero Crater Operational Digital Twin Hub (Sidebar)
Positioned on the right column of the hero container, this card serves as the focal point for regional mission control:

- **Hub Header:**
  - `OPERATIONAL MISSION HUB` tag.
  - `ACTIVE 3D TWIN` badge in vivid emerald green, confirming Jezero Crater is loaded in active GPU memory.
- **Jezero Regional Dossier Item:**
  - Coordinates: `18.44°N, 77.45°E` &bull; Landing site of Perseverance Rover and ancient Jezero river delta.
  - `EXPLORE →` Button: Immediate launch into the Jezero 3D scene.
- **Verified Jezero Workstation Data Card:**
  Displays the four pillars of data integrity packaged inside this release:
  - *Topography:* USGS CTX 20m Stereo DTM &bull; 1m HiRISE Inflow Sub-grid.
  - *Ground Truth:* NASA PDS Mars 2020 Sols 0–1000+ actual traverse (33.2 km).
  - *Meteorology:* NASA PDS MEDA In-Situ atmospheric measurements (Sol 89 Storm).
  - *Science Targets:* 12 Delta Outcrops &bull; Perseverance Sample Depot.
- **Scientific Integrity Disclosure:**
  Prominently states that Jezero Crater is the sole verified operational workstation in this release and reiterates that traverses are computational models, not flight-certified astronaut paths.

---

### 2.5 Specifications & Capabilities Grid
Below the hero fold, four glassmorphic cards outline the technical specifications of the engine:

1. **Terrain Intelligence:** 250×250 elevation grid, 20.0 m nominal cell spacing, georeferenced to IAU 2000 Mars planetocentric sphere.
2. **Human Biomechanics:** Minetti metabolic energy equations ($W_{\text{eff}} = \dots$), asymmetric uphill/downhill slope friction, and carried mass penalties (25 kg gear).
3. **Environmental Telemetry:** In-situ atmospheric pressure ($600\text{ Pa}$), diurnal temperature swings ($-85^\circ\text{C}$ to $-15^\circ\text{C}$), and optical dust opacity ($\tau$).
4. **Autonomous Mission Resilience:** Live A* re-planning under simulated dust storms, actuator deratings, or rockfall corridor closures.

---

### 2.6 "How It Works" Architectural Pipeline
A 4-step sequential flow diagram illustrating how raw NASA/USGS PDS products transform into actionable astronaut mission plans:

$$\text{USGS/PDS Data} \longrightarrow \text{Biomechanical Cost Surface} \longrightarrow \text{Multi-Criteria A* Solver} \longrightarrow \text{Autonomous Contingency Response}$$

1. **Ingest & Calibration:** USGS 20m CTX GeoTIFFs and NASA PDS traverse waypoints are ingested and projected onto the IAU 2000 Mars sphere.
2. **Biomechanical Cost Modeling:** Slopes are derived via spatial gradients, with metabolic cost factors applied for human sorties.
3. **Multi-Strategy Optimization:** Asymmetric A* computes three Pareto-optimal paths: Conservative, Science-First, and Time-Efficient.
4. **Resilience & Safe Return:** If an anomaly occurs (dust storm or oxygen margin loss), the engine replans the shortest safe-haven return corridor.

---

### 2.7 Complete Provenance & Non-Safety Operational Footer
The page concludes with a glassmorphic footer divided into four thematic columns:
1. **Core Systems:** Quick links to Astronaut EVA Studio, Robotic Rover Mode, 3D Workstation, and Preflight Suite.
2. **Planetary Datasets:** Direct attribution to USGS Astrogeology CTX Stereo DTM, NASA PDS Mars 2020 Rover Archive, and NASA PDS Atmospheres Node MEDA.
3. **Verification & Quality Gates:** Overview of the test infrastructure (125 automated unit and regression tests, 7-viewport zero-overflow guarantee).
4. **Operational Disclosures:** Re-statement of non-probabilistic truth standards and research prototype boundaries.

**Mandatory Aerospace Disclaimer Banner:**
> [!IMPORTANT]
> **SCIENTIFIC RESEARCH PROTOTYPE • NOT OPERATIONAL SAFETY FLIGHT CERTIFIED**  
> MarsWalk 2.0 (Project Atlas) is an independent planetary mission rehearsal and decision-support demonstrator. Traverses, biophysical effort models, metabolic rates, and consumable envelopes are computational heuristics derived from NASA/USGS observations. Under no circumstances should modeled traverses be interpreted as certified operationally safe for human astronauts.
