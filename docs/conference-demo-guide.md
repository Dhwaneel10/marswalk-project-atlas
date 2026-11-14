# MarsWalk 2.0 / Project Atlas
# Conference Demonstration Guide & Evaluator Runbook

**Edition:** Conference Demonstration Edition (Milestone 13B)  
**Target Architecture:** Mars IAU 2000 Planetocentric Sphere & USGS CTX 20m Jezero Crater DTM  
**Demonstration Runtime:** ~5 to 7 minutes (Guided Walkthrough) or Self-Paced Exploration  
**Platform Support:** Windows 10/11, PowerShell 5.1/7+, Python 3.10–3.12, Modern Chromium/Edge/Firefox  

---

## 1. Quick-Start Launch Protocol (Under 10 Seconds)

MarsWalk 2.0 includes a Windows-first, single-command launcher that automatically verifies the local Python environment, tests server port health, avoids duplicate process collisions, and opens the guided demonstration directly in your default browser.

### Option A: One-Click PowerShell Launcher (Recommended)
Open Windows PowerShell and run:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_marswalk_demo.ps1
```
*Tip:* To start the background server without opening a browser window automatically, append `-NoBrowser`. To run in background daemon mode, append `-Background`.

### Option B: Deep-Link URL
If the MarsWalk server is already running:
```
http://127.0.0.1:3000/?mode=demo
```
Opening this URL directly suppresses the landing page overlay, initializes the transient conference demonstration fixture (`cmp_conference_demo_jezero`), expands the operations cockpit, and positions the camera at the planetary overview with the Guided Walkthrough HUD ready.

---

## 2. Walkthrough HUD Controls & Interactive Freedom

The Guided Walkthrough HUD floats unobtrusively on the left side of the screen (`width: 380px`), providing clear narrative context, scientific truth disclosures, and progressive technical explainability without restricting your ability to explore:

- **Action Button (`[Execute Action & Advance →]`):** Automatically triggers the recommended action for the active step (e.g., flying the camera, computing an A* route, loading a campaign, or opening an analytical lab) and advances to the next step.
- **Formulary Drawer (`🧠 Formulary` or `Technical & Scientific Specifications`):** Expands the 6-topic Technical Explainability panel detailing the exact mathematical derivations (Horn slope filter, octile heuristic admissibility proof, Pareto vector dominance).
- **Navigation Controls (`← Prev`, `Skip`, `Next →`):** Allows moving back and forth through the 9 steps at your own pace.
- **Exit Demo Mode (`✕ Exit Demo`):** Restores standard Atlas operations immediately without reloading the page, preserving any custom waypoints or exploratory state.
- **Interactive Freedom:** You can rotate the 3D Mars globe, hover over SVG crosshairs, or inspect telemetry at any point during any step.

---

## 3. The 9-Step Guided Mission Lifecycle

```
[01. Geodesy] → [02. Topography] → [03. A* Planning] → [04. Workbench] → [05. Cockpit]
      ↓
[06. Traceability] → [07. Robustness Lab] → [08. Rehearsal & Causal Replay] → [09. Experiment Studio]
```

### Step 1: Global Cartography & Geodesy
- **Context:** Mars referenced to the IAU 2000 planetocentric datum ($R = 3,396,190\text{ m}$) with USGS Viking MDIM 2.1 color imagery and 2,061 verified IAU landmarks.
- **Evaluator Action:** Click `Fly to Jezero Crater Workstation →` to descend from global orbit into the Western Delta.
- **Scientific Disclosure:** High-resolution surface routing is strictly confined to surveyed basins where calibrated elevation models exist.

### Step 2: Authentic Topographic Grounding
- **Context:** Displays the authentic USGS CTX 20m Digital Terrain Model ($250 \times 250$ cells, $5.0 \times 5.0\text{ km}$, elevation $-2,624\text{ m}$ to $-2,445\text{ m}$). Facet slopes are calculated using Horn's 3x3 convolution kernel; slopes $>15^\circ$ are highlighted as critical hazards.
- **Evaluator Action:** Click `Load Demo Sortie Configuration →` to preload 5 science targets (Octavia Landing, Hawksbill Gap, Skinner Ridge, Enchanted Lake, Delta Rim Overlook).

### Step 3: Multi-Stop Sortie Planning & Least-Cost Routing
- **Context:** Live Python A* graph search over the 20m anisotropic cost grid. Computes distance ($3,149\text{ m}$), duration ($113\text{ min}$ at $0.85\text{ m/s}$), and Apollo Waligora metabolic energy proxy ($1,620\text{ kcal}$).
- **Evaluator Action:** Click `Calculate Traverse (Python A*) →` to compute and visualize the 3D route polyline.

### Step 4: Route Decision Workbench & Elevation Profile
- **Context:** Interactive SVG elevation profile visualizes authentic terrain undulation. Moving the crosshair dynamically tracks distance, elevation, slope, and synchronizes a 3D locator beacon across the Martian surface.
- **Evaluator Action:** Click `Enter Mission Operations Cockpit →` to transition to wide analytical cockpit mode.
- **Reconciliation Principle:** $\text{Total Effort} = \text{Distance} \times (1 + P_{\text{slope}} + P_{\text{rough}} + P_{\text{climb}})$, additively reconciling to machine epsilon ($1.42 \times 10^{-14}\text{ m}$).

### Step 5: Mission Operations Cockpit & Telemetry
- **Context:** Real-time operations dashboard displaying the 3-Sol Jezero campaign (`cmp_conference_demo_jezero`), battery margin, 12-checkpoint preflight flight-readiness assessment, and environmental telemetry from PDS4 MEDA archives (Sol 1619, $589.7\text{ Pa}$).
- **Evaluator Action:** Click `Audit Scientific Traceability & Evidence →` to inspect data provenance.

### Step 6: Scientific Traceability & Evidence Inspector
- **Context:** Every metric displayed on screen is independently auditable. The modal exposes governing equations, primary remote sensing sources (USGS CTX 20m DTM, DOI `10.5066/P906QQT8`), sensor classifications, and the mandatory aerospace non-certification statement.
- **Evaluator Action:** Click `Close Inspector & Enter Robustness Lab →` to transition to stress testing.

### Step 7: Mission Robustness Lab & Stress Gauntlet
- **Context:** Stress-tests mission viability across a deterministic 10-case gauntlet (traction derating, duration contraction, operational holds, corridor chokepoints). Computes finite-difference sensitivity elasticities and answers core resilience questions.
- **Evaluator Action:** Click `Adopt Resilient Strategy & Launch Rehearsal →` to advance to closed-loop recovery.

### Step 8: Autonomous Rehearsal Director & Causal Replay Studio
- **Context:** Closed-loop tri-track simulation comparing **Nominal Baseline** vs **Disturbed Unmitigated** (60m rockfall barrier) vs **Autonomous Recovered** (adaptive detour preserving 100% science). Evaluators scrub the 7-step Causal Decision Timeline to inspect traceable causal links.
- **Evaluator Action:** Click `Orchestrate Experiment Battery in Studio →` to view multi-scenario campaign outcomes.

### Step 9: Mission Experiment Studio & Tamper-Evident Dossier
- **Context:** Multi-scenario experiment engine evaluates 10 stress scenarios in batch. Cross-scenario comparative matrix highlights degraded vs recovered sorties with one-click deep-dive clapperboards (🎬). Generates a complete, cryptographically verified Evidence Dossier ZIP containing RFC 8259 JSON and SHA-256 manifests.
- **Evaluator Action:** Click `★ Complete Tour & Explore MarsWalk Freely` to unlock full unguided operational control.

---

## 4. Technical Explainability Formulary (Defense Quick Reference)

The Technical Explainability drawer provides instant mathematical defense across 6 core planetary science and algorithmic pillars:

1. **Equirectangular Cosine Metric Scaling:**  
   Mars meridians converge: $dx = C \cdot \cos(\phi_{\text{ref}}) = 20.0 \cdot \cos(18.442^\circ) = 18.973\text{ m}$. Eliminates a $2.53\%$ distance distortion.
2. **Horn (1981) 3x3 Gradient & Dual-Slope Maximum:**  
   $\theta_{uv} = \max(\theta_{\text{Horn}}(v), \theta_{\text{step}}(u, v))$. Prevents contour paths on steep scarps from being falsely classified as flat.
3. **Generalized Octile Heuristic Admissibility ($h \le h^*$):**  
   Anisotropic octile distance strictly underestimates edge cost ($\sum C \ge \sum d \ge h$). Provably Dijkstra-equivalent ($0.000\text{ m}$ cost discrepancy) while pruning over $97\%$ of node expansions.
4. **Multi-Objective Pareto Dominance:**  
   Evaluates true vector trade-offs across distance, time, climb, and science diversity. Infeasible plans are quarantined into an explicit violation partition.
5. **4-Tier Closed-Loop Disruption Triage Hierarchy:**  
   Level 1 In-Situ Resume $\to$ Level 2 Local A* Detour $\to$ Level 3 Greedy Science Pruning $\to$ Level 4 Direct Habitat Abort.
6. **Non-Probabilistic Truth Disclosures:**  
   All metrics derive from published NASA/USGS datasets. Modeled traverses are planning decision-support aids and MUST NEVER be certified as operationally safe for astronauts without in-situ verification.

---

## 6. Atlas 3D Mission Theater (Spatial Digital Twin & Forensic Playback)

Introduced in Milestone 13C, the **Atlas 3D Mission Theater** provides an evaluator-first, high-immersion spatial experience:

### Launching Theater Mode
- **URL Parameter:** `http://127.0.0.1:3000/?mode=demo&theater=1` or `http://127.0.0.1:3000/?theater=1`.
- **Top Navigation Bar:** Click `🎭 3D THEATER`.
- **Demo Banner:** Click `🎭 3D Theater` in the floating conference demo banner.
- **Keyboard Shortcut:** Press `T` to toggle Theater Mode on/off. Press `Escape` to exit.

### Theater Capabilities
1. **5-Mode Camera Director:**
   - `[ORBIT]`: Free user orbit, zoom, and panning.
   - `[TOPOGRAPHIC]`: Oblique scarp perspective ($h \approx 360\text{ m}$, pitch $22^\circ$) highlighting delta relief.
   - `[FOLLOW UNIT]`: Third-person chase camera tracking active vehicle with heading yaw smoothing and stationary freeze latching.
   - `[MISSION OVERVIEW]`: Regional high view auto-framing the campaign bounding box.
   - `[EVENT FOCUS]`: Automatically centers injected disturbance zones (e.g. 60m rockfall obstacle) or selected science targets.
   - *Smooth Interruptibility:* Any user mouse drag or wheel scroll immediately cancels tweening and returns camera control to `ORBIT`.
2. **Raycast Spatial Object Inspector:**
   - Click anywhere on the 3D canvas (terrain, routes, unit markers, science beacons, or disturbance barriers) to view the floating acrylic Inspector Card (`#theaterInspectorCard`) with coordinates, MOLA elevations, Horn slopes, Apollo Waligora costs, and permanent USGS CTX DOI links (`10.5066/P906QQT8`).
3. **Tri-Track Trajectory Comparison:**
   - Simultaneously toggle Nominal Baseline (Cyan), Disturbed Unmitigated (Red), and Autonomous Recovered (Amber) paths.
4. **Unified Rehearsal Transport Bar:**
   - Play/Pause, Step $\pm 5\text{s}$, Seek Scrubber, and Speed Multipliers ($1\times, 2\times, 5\times, 10\times$).


## 7. Atlas Mars RelayNet (Terrain-Aware Communications Visibility & Relay Optimization)

Introduced in Milestone 13D, **Atlas Mars RelayNet** extends surface traverse planning into terrain-aware mission communications visibility and multi-hop relay planning:

### Launching RelayNet
- **URL Parameter:** \http://127.0.0.1:3000/?mode=demo&theater=1&relaynet=1\ or \http://127.0.0.1:3000/?relaynet=1\.
- **Theater HUD Control:** Click \📡 RELAYNET\ in the top-right controls drawer to toggle the RelayNet control panel and 3D visual layer.

### Live Demonstration Workflow
1. **Observe Geometric Terrain Occlusion Baseline:**
   - Notice the central Base Station transceiver mast at Octavia E. Butler landing site ($[117, 157]$).
   - In nominal baseline mode with the rover traversing toward Three Forks ($[138, 114]$), observe the direct communications link turning **crimson dashed** and terminating at a 3D red diamond obstruction marker.
   - Point out the Cockpit HUD telemetry badge: \STATUS: BLOCKED (GAP)\ with clearance $-4.44\\text{ m}$ occluded by the intermediate ridge crest.
2. **Explore Candidate Promontories:**
   - In the \#relayNetPanel\ drawer, check \Candidate Pins\. Observe 12 amber holographic markers on topographic peaks along the Jezero crater rim and delta front, screened for low slope ($\\le 12^\\circ$) and spatial diversity ($\\ge 450\\text{ m}$).
3. **Execute Greedy Submodular Relay Optimization:**
   - Click \⚡ Auto-Plan Optimal Relays (Greedy Submodular)\.
   - The engine selects the 2 highest-impact relay locations (\MRN_CAND_03\ and \MRN_CAND_07\), deploying 3D emerald relay towers with swiveling parabolic dishes.
   - The status transitions to \RELAY MESH ACTIVE (100% REACHABLE)\.
4. **Dynamic Mission Scrubbing & Carrier Beam Tracking:**
   - Scrub the mission playback timeline. Observe the bright cyan/emerald carrier beam tracking the vehicle through the relay backhaul to Base Station.
   - HUD telemetry confirms \COMM: CONNECTED (1 HOP via MRN_CAND_03)\ with zero packet blackout gaps across the traverse.
5. **Inspect 3D Object Telemetry:**
   - Click any Base Station mast, Relay Tower, or Occlusion Diamond to open the \#theaterInspectorCard\ displaying elevation, antenna heights, clearance depth, and USGS CTX DTM citations.



## 8. Atlas Joint Mission Co-Design (Traverse Planning × Relay Network Optimization)

Introduced in Milestone 13E, the **Joint Mission Design Studio** unifies surface mobility planning and Mars RelayNet infrastructure planning into a coupled co-design system.

### Launching Joint Mission Co-Design
- **URL Parameter:** `http://127.0.0.1:3000/?mode=demo&jointstudio=1` or `http://127.0.0.1:3000/?jointstudio=1`
- **Cockpit Tab:** Click the **⚙ Co-Design** tab in `#inspectorTabs`.
- **Theater HUD Control:** Click **⚙ CO-DESIGN** in the top bar to toggle `#jointMissionStudioPanel`.

### Live Demonstration Workflow
1. **Define Mission & Objectives (Step 1):**
   - Origin: Octavia E. Butler Landing Base `[117, 157]`.
   - Destination: Delta Remnant / Three Forks `[138, 114]`.
   - Select weight preset: `Balanced (0.3/0.35/0.2/0.15)` or `Comms-First`.
2. **Configure Mobility & Comms Platforms (Steps 2 & 3):**
   - Confirm Perseverance platform, slope limits (15° / 20° / 25°), Base mast (10m), rover antenna (2.5m), and relay budget ($K_{\text{max}} = 2$).
3. **Run Autonomous Co-Design Optimization (Step 4):**
   - Click `[⚡ EXECUTE JOINT CO-DESIGN OPTIMIZATION]`.
   - Observe solver generating candidate traverses, evaluating 3D geometric line-of-sight against USGS Jezero 20m DTM, and computing Pareto dominance in $< 850\text{ ms}$.
4. **Explore Pareto Frontier Trade-Offs (Step 5):**
   - Inspect the interactive 2D scatter plot (Traverse Distance vs Blackout Gap Duration vs Relays).
   - Point out green non-dominated frontier candidates versus grey dominated alternatives.
   - Click candidate rows in the comparative scorecard table to switch active preview.
   - Read the dynamic trade-off explanation box with Marginal Rate of Substitution (MRS) and scarp occlusion attribution.
5. **Inspect 3D Mission Theater Multi-Traverse Hierarchy:**
   - Switch to Mission Theater.
   - Observe bold cyan selected candidate ribbon, dashed violet Pareto alternatives, faint grey dominated paths, and pulsating crimson blackout gaps.
   - Notice deployed emerald relay towers on promontories and dynamic carrier beam handovers.
6. **Promote Plan & Export Artifacts (Step 6):**
   - Click `[🚀 PROMOTE CO-DESIGN TO ACTIVE MISSION PLAN]` to deploy candidate to active operations.
   - Click `Export Plan (JSON)` or `Download Dossier (MD)` to inspect Draft 2020-12 valid schema evidence.


## 9. Atlas Energy & Resource Intelligence (Resource-Constrained Feasibility Digital Twin)

Introduced in Milestone 13F, the **Energy & Resource Intelligence Subsystem** upgrades Atlas into a multi-subsystem, resource-constrained mission feasibility Digital Twin. Evaluators can directly explore the physical energy costs of mobility, terramechanical compaction, elevation climbing, and subsystem operations along authentic Martian topography.

### Key Capabilities Demonstrated
1. **Physical Terramechanical Mobility Modeling:**
   - Rolling resistance on compressible regolith: $W_r = m \cdot g_{\text{Mars}} \cdot C_{rr} \cdot \cos(\theta) \cdot d$.
   - Authentic gravitational potential work: $W_g = m \cdot g_{\text{Mars}} \cdot \Delta z$.
   - Non-regenerative descent dissipation physics: $W_{\text{mech}} = W_r + \max(0, W_g)$.
   - Electromechanical motor conversion: $E_{\text{mobility}} = W_{\text{mech}} / \eta_{\text{drive}}$.
2. **Platform & Operational Presets (Step 4 of Wizard):**
   - *Perseverance Nominal:* 1025 kg rover, 4800 Wh battery, 20% safety reserve, 110W base avionics, 120W science payload.
   - *High-Power Drill:* 1050 kg, 220W percussion drill, 1800s science dwell.
   - *Ultralight Scout:* 185 kg, 850 Wh battery, 15% reserve, 45W avionics.
   - *Crew EVA Sortie:* 150 kg suit + life-support, 1200 Wh battery, 35% safety floor.
3. **Multi-Dimensional Pareto Trade-Off Analysis (Step 6):**
   - Seamlessly toggle Pareto visualization axes between **Energy vs Distance**, **Energy vs Gap Duration**, and **Distance vs Gap Duration**.
   - Review the detailed scorecard tracking Duration, Energy Consumed (Wh), Energy Remaining (Wh), Reserve Margin (%), and Feasibility Status.
4. **7-State Feasibility State Machine:**
   - Clearly distinguishes between fully feasible operations, low-reserve alerts, critical energy violations, and schedule timeouts.
5. **3D Mission Theater Resource Telemetry:**
   - **In-Cockpit Battery Gauge:** Real-time State of Charge (SOC) percentage and remaining Watt-hours bar in the `#jointMissionStudioPanel` drawer.
   - **Dynamic Timeline Scrubber:** Simulates continuous battery drawdown ($t_0 \to t_{\text{end}}$) as the rover navigates across Jezero Crater.
   - **Interactive Raycast Segment Inspector:** Click directly on traverse ribbons to view terramechanical work breakdown ($W_r, W_g, E_m$, SOC).


## 10. Atlas Science Return & Data Logistics System (Milestone 13G-R)

Introduced in Milestone 13G-R, the **Atlas Science Return System** couples science target prioritization, multi-instrument observation scheduling, and byte-level onboard data accounting with communications-aware simulated data transfer.

### Key Capabilities Demonstrated
1. **Science Target Prioritization (Step 1):**
   - Review candidate science sites (Three Forks, Hawksbill Gap, Kodiak Butte).
   - Inspect tri-state priority tags (`USER`, `SOURCE`, `UNASSESSED`).
   - Set multi-objective science weighting (`w_science`).
2. **Multi-Instrument Payload & Turret Protection (Step 5):**
   - Configure remote sensors (Mastcam-Z, SuperCam, RIMFAX, MEDA) and contact tools (PIXL, SHERLOC, Coring Tool).
   - Experience automatic robotic arm turret singularity protection (only one contact tool active concurrently).
3. **Onboard Storage & Simulated Transfer Logistics (Step 6):**
   - Configure solid-state mass memory (SSMM) capacity (4 GB to 64 GB).
   - Select simulated local surface transfer rate presets (256 kbps UHF to 5 Mbps High-Rate Base).
   - Select data retention policies (`TRANSFER_THEN_RELEASE` vs `PROTECTED_PERMANENT`).
4. **8D Pareto Co-Design Frontier (Step 8):**
   - Toggle Pareto axes: **Science Return vs Total Energy Consumed**, **Science Return vs Data Transferred**, **Peak Storage vs Distance**.
   - Inspect comparative scorecard showing Science Points, Data Generated (MB), Simulated Data Transferred (MB), Peak Storage (MB), and Energy Margin.
5. **Atlas Science Return Recovery Lab:**
   - Evaluate 4 operational disturbance scenarios: Relay outage, Instrument offline, Storage saturation, and Energy restriction via `POST /api/science-mission/recovery-lab`.
6. **3D Mission Theater Data Logistics HUD:**
   - Real-time Onboard Storage Fill gauge track with 80% warning and 95% critical capacity markers.
   - Dynamic timeline scrubber synchronizing rover movement, battery drain, storage fill, and transfer backlog in real time.


## 11. Atlas Campaign Operations Director & MOCC (Milestone 13H)

Introduced in Milestone 13H, the **Atlas Campaign Operations Director** provides flight-operations-grade multi-sol mission orchestration, closed-loop execution, SHA-256 event deduplication, and adaptive replanning under contingency.

### Key Capabilities Demonstrated
1. **Mission Operations Control Center (MOCC):**
   - Direct access via **"&#128506; MOCC OPS"** header button or URL `http://127.0.0.1:3000/?tab=mocc`.
   - **6-Card KPI Deck:** Traverse Distance (km), Campaign Time (h), Science Yield (pts), Min Battery SOC (%), Comms Coverage (%), and Decision Gate Status.
2. **Multi-Sol Timeline & Interactive Sol Cards:**
   - 5 color-coded Sol cards (Cyan, Emerald, Purple, Amber, Rose) decomposing each day's schedule into Drive, Science, Relay Deployment, and Bivouac rest segments.
   - Click-to-focus interactivity that isolates specific sorties in the 3D viewport.
3. **Live Simulated State HUD:**
   - Real-time kinematic telemetry (HDG, slope gradient, ground speed), visual Battery SOC gauge bar with 20% reserve line, Science buffer utilization bar, and RF comms link status.
4. **Closed-Loop Contingency Replanning:**
   - One-click disruption ingestion via **"&#9889; Contingency Replan"** button.
   - Side-by-side delta comparison table showing $\Delta\text{Dist}, \Delta\text{Time}, \Delta\text{Sci}, \Delta\text{SOC}, \Delta\text{Relays}$.
   - Atomic promotion of contingency plans with full plan version history and lineage preservation.
5. **3D Mission Theater Story Mode:**
   - Color-coded multi-sol traverse ribbons elevated $+1.8\text{ m}$ above the USGS Jezero DTM surface.
   - 3D floating diamond science target beacons and deployed relay towers with microwave Fresnel clearance beams.
   - Dynamic timeline scrubber synchronizing 3D rover position, heading, Sol card highlight, and Live State HUD.


## 12. Atlas Mission Assurance & Counterfactual Operations Lab (Milestone 13I)

Introduced in Milestone 13I, the **Atlas Mission Assurance & Counterfactual Operations Lab** provides mathematically rigorous, tamper-evident mission verification, immutable campaign branching, deterministic replay, and multi-objective recovery optimization.

### Key Capabilities Demonstrated
1. **Mission Assurance Workbench & Status Deck:**
   - Direct access via **"&#128737; ASSURANCE LAB"** tab button or URL `http://127.0.0.1:3000/?tab=assurance`.
   - **5-Card HUD Grid:** Master Assurance Verdict (`PASS`), Active Branch Lineage (`main v1`), Robustness Stress Score (`94.8%`), Violations Count (`0`), and SHA-256 Merkle Root Digest snippet.
2. **Area A: Campaign Branch Tree & Experimental Sandboxing:**
   - Deep-copy child branch creation with dedicated workspaces (`data/workspaces/branches/{id}/`).
   - Absolute parent campaign immutability (`ISO-001`) preventing accidental data mutation or test contamination.
3. **Area B: Counterfactual Scenario Lab (12 Disturbance Models):**
   - Standardized planetary disturbances: Relay Loss (R1), Comms Degradation (R2), Battery Cell Failure (E1), Dust Storm Solar Loss (E2), High-Utility Discovery (S1), Drilling Time Overrun (S2), Flash Storage Lockout (D1), Downlink Bottleneck (D2), Drive Slip / Actuator Anomaly (M1), Ripple Detour (M2), Precautionary Sol Abort (O1), and Spectrometer Calibration Thermal Drift (O2).
   - Automated recovery synthesis restoring mission feasibility.
4. **Area C: 3-Way Comparative Workspace:**
   - Quantitative performance comparison matrix evaluating Baseline (`main`), Disturbed (unmitigated failure cascade), and Recovery Candidate branches.
   - 3D spatial overlay layers in Mission Theater: Solid Cyan Baseline, Dashed Amber Disturbed, Glowing Emerald Recovery, and Rose Divergence Marker.
5. **Area D: 20-Rule Invariant Audit Scorecard:**
   - Exhaustive mathematical verification across Energy, Storage, Communications, Mobility, Science, Timing, and Replay rules.
   - Formal evidence grading (`CONFIRMED`, `DERIVED`, `UNRESOLVED`, `CONFLICTING`, `MISSING`).
6. **Area E: Recovery Approval & Promotion Drawer:**
   - Optimistic concurrency version locking (`CONC-001`) preventing stale promotion overwrites with `StaleVersionConflictError` ($HTTP\ 409$).
   - Immutable promotion audit recording Approver call-sign, rationale, and incrementing parent campaign version to $v_2$.
7. **Area F: Cryptographic Tamper-Evident Dossier:**
   - SHA-256 content hashes for all campaign artifacts and unified Merkle root digest.
   - One-click export of complete audit verification JSON package for external evaluators.


---

## 8. Milestone 13J: Atlas Fleet Intelligence & Multi-Rover Cooperative Exploration

Introduced in Milestone 13J, **Atlas Fleet Intelligence** transitions Project Atlas from single-rover operations to cooperative multi-rover planetary surface exploration.

### Key Capabilities Demonstrated
1. **Fleet Operations Control Center:**
   - Direct access via **"🚀 FLEET CONTROL"** tab button or URL `http://127.0.0.1:3000/?tab=fleet`.
   - **5-Card Telemetry HUD:** Active Rovers (`4/4 Units`), Fleet Traverse (`18.4 km`), Min SOC Margin (`36.8%`), Comms Reachability (`100.0%`), and Science Utility (`2,840 pts`).
2. **Area 1: Four-Rover Status Cards Grid:**
   - Real-time telemetry for Rover Alpha (Science Lead, Cyan), Rover Beta (Geophysical Surveyor, Emerald), Rover Gamma (Coring Specialist, Purple), and Rover Delta (Mobile Relay & Sentinel, Amber).
   - Strict enforcement of the **zero-energy-pooling invariant** ($\partial SOC_i / \partial E_j = 0$).
3. **Area 2: Distributed Science Task Assignment Board:**
   - Bounded Pareto optimization allocating 12 Jezero targets based on authoritative instrument matching (`INSTRUMENT_CATALOG`).
   - One-click eligibility explanation modal detailing quantitative selection and exclusion rationale.
4. **Area 3: Multi-Lane Synchronized Fleet Timeline (Gantt):**
   - Parallel activity lanes across Sols 1–5 with color-coded activity blocks (traverse, observation, downlink, spatial holds, diurnal rest).
5. **Area 4: 6D Pareto Optimization Champions Matrix:**
   - Comparison and 1-click selection of 5 specialized champion configurations (`BALANCED_CHAMPION`, `SCIENCE_MAXIMIZING`, `ENERGY_EFFICIENT`, `COMMUNICATIONS_FOCUSED`, `MINIMUM_DURATION`).
6. **Area 5: Counterfactual Disturbance & Recovery Lab:**
   - Fault injection benchmarking across 7 standardized scenarios (F1–F7).
   - 3-Way Comparative Scorecard (Baseline vs Disturbed vs Recovery) demonstrating recovery of $94.2\%$ science yield.
   - Formal promotion drawer with cryptographic SHA-256 state fingerprint logging.
7. **Three.js 3D Mission Theater Integration:**
   - Simultaneous rendering of 4 color-coded trajectory ribbons, rover markers, laser beacons, and microwave RelayNet mesh links.


---

## 🎯 DEMO STAGE 13K: ATLAS GOAL-DRIVEN MISSION DESIGN COMPILER (Milestone 13K)

### Elevator Pitch
> *"Traditional mission planning requires manual subsystem configuration across mobility, communications, payload, and power teams. Atlas Milestone 13K introduces the Goal-Driven Mission Design Compiler: operators express high-level scientific and operational intent in plain language, and the compiler autonomously synthesizes an 8-candidate Pareto exploration portfolio in under 15 milliseconds."*

### Key Capabilities Demonstrated
1. **Mission Design Studio 2.0:**
   - Direct access via **"🎯 DESIGN STUDIO"** tab button or URL `http://127.0.0.1:3000/?tab=design_studio`.
   - Natural-language mission intent input with calibrated presets for Western Jezero delta reconnaissance.
2. **Pre-Flight Remote Sensing & Physical Validation:**
   - 1-click intent validation against USGS CTX 20m DTM elevation boundaries, slope ceilings, and authoritative instrument catalogs.
   - Emits structured verdicts (`VALID`, `VALID_WITH_WARNINGS`, `INVALID`) and sanitizing auto-normalization.
3. **Directed Acyclic Task Graph (DAG) Explorer:**
   - Visual SVG task graph displaying atomic operational tasks (traverses, arrivals, instrument preparations, observations, downlinks, diurnal checkpoints).
   - Critical path highlighted with active pulsing flow; click-to-inspect task telemetry (duration, energy Wh, data MB, prerequisites).
4. **8-Candidate Multi-Rover Portfolio Synthesis:**
   - 7-level hierarchical fleet synthesis producing 8 distinct operational postures (`BALANCED`, `SCIENCE_MAXIMIZING`, `ENERGY_EFFICIENT`, `COMMUNICATIONS_FOCUSED`, `MINIMUM_DURATION`, `ROBUSTNESS_FOCUSED`, `MINIMUM_INFRASTRUCTURE`, `DATA_RETURN_FOCUSED`).
   - Non-dominated Pareto frontier extraction and multi-objective composite scoring.
5. **Plan Compilation Debugger (Forensic Causal Tracing):**
   - Step-by-step causal failure chain analysis for infeasible mission intents.
   - 1-click executable relaxation proposals restoring feasibility without violating hard physical laws.
6. **6-Scenario Benchmark Lab:**
   - Automated stress testing across synthetic campaigns A through F with $+258.9\%$ mean science utility gain over the greedy baseline.
7. **Single-Click Promotion & 3D Theater Playback:**
   - Promotion to active operational fleet director with cryptographic SHA-256 fingerprint logging and synchronized multi-rover 3D trajectory playback.
