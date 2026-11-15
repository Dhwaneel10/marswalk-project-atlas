# Mission 17: Feature Audit & Subsystem Deferral Ledger

**Project:** MarsWalk 2.0 / Project Atlas  
**Audit Date:** November 2026  
**Auditor:** Independent Technical Verification Engineer  
**Workspace:** `/home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission`  

---

## 1. Executive Summary

As MarsWalk evolved from an initial route-planning prototype into a comprehensive planetary mission operations platform, several sophisticated engineering subsystems were introduced across Milestones 13 and 14. Among these were the **Atlas Mars RelayNet Mesh & Connectivity Twin** (Milestone 13D/13Y) and the **Joint Mission Co-Design Studio** (Milestone 13E).

While both subsystems showcase advanced mathematical modeling, an audit revealed that:
1. They introduced oversized DOM control panels (`#jointMissionStudioPanel` and `#relayNetPanel`) with high z-indices (`z-index: 105`) that persisted outside the mission theater HUD and rendered directly across the landing page, obstructing the hero section, the specs grid, and the primary call-to-action buttons.
2. They mixed authentic remote sensing data with mathematical simulation heuristics without clear epistemic boundaries, risking confusion among competition evaluators.
3. They diluted the primary human-first exploration narrative ("Astronaut EVA Mode").

In Mission 17, these subsystems were audited, decoupled from default viewport loading, and relocated into designated secondary and experimental navigation tiers.

---

## 2. Forensic Audit: Atlas Mars RelayNet Twin

### 2.1 Subsystem Overview
- **DOM Container:** `#relayNetPanel` (`.relaynet-control-panel`)
- **Inspector Tab:** `tabPlanetaryNetwork` ("3. Comms & DTN")
- **Theater Toggle:** `#btnToggleRelayNet` (`.theater-relaynet-btn`)
- **Core Algorithms:**
  - 3D topographic Line-of-Sight (LoS) ray casting across the USGS CTX 20m elevation matrix.
  - Orbital relay pass calculation (MRO, 2001 Mars Odyssey, ExoMars TGO, MAVEN).
  - RFC 9171 Delay-Tolerant Networking (DTN) bundle custody transfer simulation with store-and-forward queuing.

### 2.2 Data Provenance: Real vs. Heuristic Breakdown

| Subsystem Component | Analytical Basis | Scientific Status | Epistemic Classification |
|---|---|---|---|
| **Base Station Position** | Octavia E. Butler Base $[117, 157]$ ($-2548.2\text{ m}$) | Ground Truth (Perseverance Landing Site) | **Measured Ground Truth** |
| **Topographic LoS Occlusion** | Digital Elevation Model ray-intersection | Computed from USGS 20m CTX DTM | **Derived Product** |
| **Orbital Ephemerides** | Keplerian two-line element approximations | Calculated Keplerian orbital periods | **Orbital Simulation** |
| **RF Path Loss & Fade Margin** | Free-space path loss equation $L_{\text{fs}} = 20\log_{10}(d) + 20\log_{10}(f) + 92.45$ | Deterministic link budget heuristic | **Simulation Model** |
| **DTN Bundle Custody** | RFC 9171 custodial transfer state machine | Protocol simulator (0 KB data loss under buffer) | **Simulation Model** |

### 2.3 Rationale for Deferral
- **Obstructive Rendering:** The panel had no `hidden` class in `web/index.html` and occupied an $800\text{px}$-wide fixed drawer.
- **Misleading Telemetry Risk:** Evaluators could misinterpret "RELAYNET ONLINE" or "0 KB LOST" as active Martian radio signals rather than a local simulation.
- **Action Taken:**
  - Added `.hidden` class to `#relayNetPanel` in `web/index.html`.
  - Removed `.active` class from `#btnToggleRelayNet`.
  - Initialized `relayNetVisible = false;` in `web/app.js`.
  - Demarcated RelayNet under `<optgroup label="Experimental / Deferred Labs">` in `extendedLabsSelect`.

---

## 3. Forensic Audit: Joint Mission Co-Design Studio

### 3.1 Subsystem Overview
- **DOM Container:** `#jointMissionStudioPanel` (`.jointstudio-control-panel`)
- **Inspector Tab:** `tabJointMissionStudio`
- **Theater Toggle:** `#btnToggleJointStudio` (`.theater-jointstudio-btn`)
- **Core Algorithms:**
  - Multi-agent asset rendezvous (Astronaut + Robotic Rover + Aerial Scout).
  - Pareto multi-objective optimization (Energy vs. Distance vs. Science Score).
  - 2D Canvas Pareto scatter plot and candidate ranking engine.

### 3.2 Data Provenance: Real vs. Heuristic Breakdown

| Subsystem Component | Analytical Basis | Scientific Status | Epistemic Classification |
|---|---|---|---|
| **Terrain Costs** | USGS CTX 20m Slope Matrix | Computed via Horn 3x3 kernel | **Derived Product** |
| **Rover Energy Consumption** | Empirical rolling resistance + incline power | JPL rover power model heuristic | **Simulation Model** |
| **Astronaut Metabolic Energy** | Minetti-Margaria biomechanics | Literature-derived metabolic equation | **Simulation Model** |
| **Task Allocation & Rendezvous** | Dynamic programming candidate ranking | Combinatorial heuristic optimization | **Algorithm Benchmark** |
| **Pareto Frontier Selection** | Non-dominated sorting ($O(N \log N)$) | Mathematical Pareto frontier derivation | **Algorithm Benchmark** |

### 3.3 Rationale for Deferral
- **Visual Blockage:** Declared at root level in `web/index.html` with `z-index: 105`, covering the landing page hero and preventing access to "ENTER ASTRONAUT EVA MODE".
- **Complexity vs. Evaluation Time:** The multi-agent co-design wizard requires 4 separate configuration steps, which exceeds the typical 3-to-5 minute evaluation window of hackathon judges.
- **Action Taken:**
  - Added `.hidden` class to `#jointMissionStudioPanel` in `web/index.html`.
  - Reduced `z-index` from `105` to `28` in `web/styles.css`.
  - Initialized `jointMissionDrawerVisible = false;` in `web/app.js`.
  - Moved Joint Co-Design to `<optgroup label="Experimental / Deferred Labs">` in `extendedLabsSelect`.

---

## 4. Complete Extended Labs Reorganization Ledger

In Mission 17, all 17 extended engineering labs were audited and organized into two clear categories within `extendedLabsSelect`:

### 4.1 Group 1: Specialized Science & Simulation (Operational)
These labs provide deep-dive analysis directly supporting the Jezero surface mission:
1. `tabExperimentStudio`: In-situ experiment configuration and protocol execution.
2. `tabRobustnessLab`: Monte Carlo disturbance testing and slope perturbation.
3. `tabRehearsalDirector`: Multi-sol campaign rehearsal and timeline director.
4. `tabCampaignOperations`: Multi-mission operations command center.
5. `tabMissionAssurance`: Quality assurance gates and validation audits.
6. `tabFleetControl`: Autonomous multi-rover coordination and telemetry.
7. `tabMissionDesignStudio`: Sortie parameterization and payload configuration.
8. `tabEnvironmentStudio`: Mars environmental twin and MEDA climate analysis.
9. `tabScienceDiscovery`: Active learning, hypothesis board, and Shannon entropy.
10. `tabEnvironmentValidation`: Climate model assimilation and sensor cross-check.
11. `tabSettlement`: Base camp infrastructure and life-support habitat metrics.
12. `tabMissionOS`: Unified planetary mission operating system cockpit.
13. `tabPlanetaryFoundry`: Resource utilization and in-situ manufacturing heuristics.
14. `tabResults`: Post-sortie analytics, metrics charts, and performance telemetry.
15. `tabScenarios`: Curated exploration challenges and historical analogies.
16. `tabWorkspaces`: Persistent mission dossiers, experiment files, and JSON packages.

### 4.2 Group 2: Experimental / Deferred Labs (Deferred)
These labs are strictly classified as experimental prototypes:
1. `tabPlanetaryNetwork`: Multi-settlement communications & DTN (RelayNet).
2. `tabJointMissionStudio`: Multi-agent co-design optimization.
3. `tabDeepSpaceAutonomy`: Long-range autonomous navigation heuristics.
4. `tabAerialCorps`: Rotorcraft aerodynamics simulation (Ingenuity flight models).
