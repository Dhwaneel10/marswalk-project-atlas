# MISSION 12 — BASELINE AUDIT & GAP ANALYSIS
## Astronaut EVA Mode: Human-First MarsWalk Implementation

**Sprint:** Mission 12  
**Starting Commit:** [`a5c6697`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission)  
**Release Baseline:** `v2.0.0-rc3`  
**Branch:** `mission-12-astronaut-eva`  
**Audit Date:** 2026-11-15  
**Auditor:** Antigravity Autonomous Agent  

---

### 1. Executive Summary

Mission 12 elevates the human astronaut from an auxiliary vehicle mode selector (`crew_eva`) into the primary operational demonstration actor in MarsWalk 2.0 / Project Atlas. 

This audit inspects the exact state of `crew_eva` logic, bioenergetics calculations, walkback safety bounds, routing cost functions, user interfaces, HUD overlays, and disruption engines inherited from Mission 11 to establish the technical baseline before implementing the dedicated **Astronaut EVA Planning Mode**.

---

### 2. Comprehensive Codebase Audit of Existing Human / EVA Features

#### 2.1 `crew_eva` References Across Modules
A repository-wide grep for `crew_eva` identified 45+ reference sites across core, API, and web tiers:
1. **Core Data Enums & Defaults:**
   - [`src/marswalk/core/planner.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/planner.py#L93-L147): Defines `VehicleMode.CREW_EVA = "crew_eva"` alongside `ROBOTIC_ROVER = "robotic_rover"`. Sets `OPERATIONAL_LIMITS_S[CREW_EVA] = 28,800.0` s ($8.0\text{ h}$) and Apollo lunar analogue walk speed $2.0\,\text{km/h}$ ($0.556\,\text{m/s}$).
   - [`src/marswalk/core/mission_campaign.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/mission_campaign.py#L171): Default sortie duration envelope $28,800\text{ s}$ ($8.0\text{ h}$).
   - [`src/marswalk/core/campaign_coordination.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/campaign_coordination.py#L350-L375): Defines unit `unit_crew_eva_1` (Crew EVA Team Alpha) with $2.0\,\text{km/h}$, $25.0^\circ$ slope ceiling, and specific energy $92.0\,\text{Wh/km}$.
2. **API Contracts & Request Handling:**
   - [`src/marswalk/api/contracts.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/api/contracts.py#L282): Normalizes `vehicle_mode` string to lowercase, validating against `{"crew_eva", "robotic_rover"}`.
   - [`src/marswalk/api/service.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/api/service.py#L260-L280): Formats route responses with human bioenergetics metadata (GAP-H1, GAP-H2, GAP-H3).
3. **Frontend Controls & Display:**
   - [`web/index.html`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/web/index.html#L6106-L6113): `#vehicleModePills` provides two toggle buttons: `Crew EVA (2.0 km/h)` and `Robotic Rover (0.035 m/s)`.
   - [`web/app.js`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/web/app.js#L6005-L6025): `setVehicleMode(mode)` switches `currentVehicleMode`, adjusts expedition hours input ($8.0\text{ h}$ for EVA vs $4.0\text{ h}$ for rover), and triggers route recalculation.

#### 2.2 Critical Finding: Influence of `crew_eva` on Route Planning
> [!IMPORTANT]
> **Audit Finding on Route Influence:**
> In Mission 11, the `crew_eva` mode calculations **DID NOT influence the spatial path search**; they **only generated post-hoc API metadata and a uniform speed divisor**.
> - **A\* Edge Cost Calculation:** [`src/marswalk/core/terrain.py::calculate_edge_cost`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/terrain.py#L481-L560) uses a single static `TerrainConfig` formula based on generic Horn slope, surface roughness, and uphill gradients. It does not ingest `vehicle_mode`.
> - **Path Geometry:** An A\* route generated with `vehicle_mode="crew_eva"` follows the exact same pixel path as `vehicle_mode="robotic_rover"` under identical profile weights.
> - **Traverse Time:** `planner.py::calculate_traverse_time` merely divides the total flat-effort cost by $2.0\,\text{km/h}$ (for EVA) instead of $0.126\,\text{km/h}$ (for rover).
> - **Bioenergetics:** `service.py::format_route_result` calculates `metabolic_burn_kcal = hrs * 320.0` and `estimated_o2_liters = hrs * 50.0` as an arithmetic scalar after the route is already computed.

#### 2.3 Existing 4 km Walkback Radius Implementation
In Mission 11 ([`service.py#L269-L279`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/api/service.py#L269-L279)):
- The check tests if `ground_dist_val > 4000.0`.
- If exceeded, it sets `"walkback_limit_exceeded": True` and appends an advisory warning:
  `"Advisory: Traverse length (...) exceeds the 4.0 km Apollo-analogue walking return envelope from base station."`
- **Limitation:** The current walkback check evaluates the *total forward traverse length*, not the actual *return distance from the farthest sortie point back to the base/habitat*, and does not compute a dedicated safe return trajectory.

#### 2.4 Existing Cockpit / HUD and Five-Pillar UI
- **HUD Reticle (`#cockpitHudOverlay`):** Implemented in `web/index.html` lines 329–349 with pitch ladder, heading, slope, and speed displays. Currently oriented towards rover forward drive telemetry.
- **Mission Control Dashboard (`#tabMissionControl`):** Features metric boxes for Traverse Dist, Planned Time, Sim Time, Science Yield, Energy Cost, Peak Slope. Displays disclaimer and trade-off summaries.
- **3D Mission Theater HUD (`#missionTheaterHUD`):** Cinematic 3D playback with timeline scrubbing, camera poses (Orbit, Follow, Cockpit, Overhead Nadir).
- **Limitation:** The interface terminology frequently uses robotic rover terminology (e.g., "drive rate", "motor derating", "wheel slip", "Wh battery capacity") even when `crew_eva` is selected.

#### 2.5 Existing Disruption and Recovery Logic
- [`src/marswalk/core/contingency.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/contingency.py): Supports rockfall closures, difficult terrain zones, motor derating, time budget cuts, and target dropouts.
- [`src/marswalk/core/mission_continuation.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/mission_continuation.py): Handles mid-sortie emergency injection, state handoff, and 3-way continuation trade-off evaluation.
- **Limitation:** The disruption engine lacks human-specific EVA failure modes (such as suit life-support pressure decay, oxygen leak/excessive consumption, astronaut physical fatigue, terrain slip/fall hazard, or communications blackout requiring immediate return-to-base abort).

---

### 3. Reuse Plan vs. New Architecture Required

| Capability | Existing Implementation (Mission 11) | Reusability Plan | Mission 12 Requirement |
| :--- | :--- | :--- | :--- |
| **Locomotion Mode** | String `"crew_eva"` or `"robotic_rover"` | Keep backward compatibility in all APIs | First-class primary UI mode selector with distinct visual theme |
| **Mobility Model** | Static Horn slope / rover terramechanics | Preserve for Rover Mode | Dedicated Human Biomechanics Mobility Model (slope cost curve, roughness, carried payload, work/rest cycles, fatigue) |
| **Path Search** | A\* on 8-connected grid with generic cost | Reuse high-performance A\* search core | Parameterize A\* edge cost with human mobility function when in EVA Mode |
| **Consumables** | Fixed $320\,\text{kcal/h}$ & $50\,\text{L/h } O_2$ metadata | Enhance with dynamic terrain-dependent rate | Comprehensive EVA Consumable Engine ($O_2$, metabolic burn, reserves, return margins) |
| **Return Planning** | Simple distance threshold ($>4000\,\text{m}$) | Replace with active trajectory calculation | Dedicated Return-to-Base feasibility engine computing actual return A\* routes |
| **Contingency Workflow**| Rover rockfall / motor derating | Keep for Rover Mode | Human EVA Emergency Workflow (Dust event, comms loss, obstacle, $O_2$ warning, return-to-base abort) |
| **HUD / Cockpit** | Rover 1st-person reticle | Keep for Rover Mode | Astronaut Visor HUD with elapsed time, $O_2$ remaining, metabolic kcal, return ETA, and mission state |
| **Rover Intelligence** | Rover historical paths & sample drops | Integrate into EVA mode | Render rover ground truth as supporting reconnaissance layer for astronaut excursions |

---

### 4. Technical Specifications for Mission 12 Implementation

1. **Human Mobility Physics:**
   - Walking speed: $v_0 = 2.0\,\text{km/h}$ ($0.556\,\text{m/s}$) nominal flat terrain; configurable $1.5 - 4.0\,\text{km/h}$.
   - Slope effort: Minetti-analogue metabolic cost curve where uphill gradients $>5^\circ$ increase metabolic expenditure non-linearly, and steep slopes $>15^\circ$ severely derate speed. Slopes $\ge 20^\circ$ (configurable) represent an impassable barrier for suited EVA.
   - Carried mass penalty: Equipment payload $M_{gear}$ ($15 - 40\,\text{kg}$) increases energy cost by factor $\frac{M_{body} + M_{suit} + M_{gear}}{M_{body} + M_{suit}}$.
   - Work/Rest cycle: Configurable duty cycle (e.g. 50 min active walk, 10 min rest/sample collection).
2. **Consumable Budget & Return Validation:**
   - Nominal $O_2$ consumption rate scaled by metabolic burn:
     $$\dot{V}_{O_2} = \text{Base Rate} \times \left(1.0 + \frac{\text{Metabolic Effort} - \text{Base Effort}}{\text{Base Effort}}\right)$$
   - Outbound, dwell, and return legs must each be modeled explicitly.
   - Return-to-base trajectory is computed from each planned intermediate stop and destination using the human mobility model to verify remaining $O_2$ and energy reserves exceed the configured safety margin (minimum 20%).
3. **Mission State Machine:**
   - States: `NOMINAL` $\rightarrow$ `CAUTION` $\rightarrow$ `SAFE HOLD` $\rightarrow$ `RETURN TO BASE` $\rightarrow$ `MISSION ABORTED` $\rightarrow$ `COMPLETED`.
   - Clear deterministic transition thresholds based on consumable margins, environmental events, and route obstructions.

---

### 5. Verification Baseline
- Prior test suite: **1,289 passed / 1,289 total (100.0%)**.
- All existing tests in [`tests/test_api_routing.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/tests/test_api_routing.py) must continue to pass without modification.
- Rover Mode must remain 100% regression-free and bitwise reproducible.
