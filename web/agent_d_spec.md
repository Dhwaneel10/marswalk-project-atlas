The following is a <SYSTEM_MESSAGE> not actually sent by the user. It is provided by the system as important information to pay attention to.

<SYSTEM_MESSAGE>
[Message] timestamp=2026-11-04T13:17:50Z sender=07f8e322-2b92-49f0-96a2-81a82a5d5010 priority=MESSAGE_PRIORITY_HIGH content=# ARCHITECTURAL DESIGN SPECIFICATION: ATLAS MISSION OPERATIONS CONTROL CENTER (MOCC) & 3D MISSION THEATER STORY MODE
**Milestone 13H • MarsWalk 2.0 / Project Atlas**
**Author:** Agent D (Frontend & Mission Theater Specialist)
**Target Files:** `web/index.html`, `web/styles.css`, `web/app.js`

---

## Executive Summary & System Overview

Milestone 13H delivers the **Atlas Mission Operations Control Center (MOCC)** and the **3D Mission Theater Story Mode**, unifying multi-sol campaign planning, real-time spatial digital twin simulation, and autonomous mission execution into an integrated, flight-operations-grade control interface.

The system bridges the analytical capabilities developed in Milestones 10–13 (Multi-Sol Orchestrator, Apollo Waligora Metabolic Model, Bekker-Wong Terramechanics, Mars RelayNet Line-of-Sight Mesh, and Joint Co-Design Pareto Optimization) into an intuitive, interactive cockpit and cinematic 3D theater that operates smoothly on both standard workstation monitors (1920×1080) and deployable tactical field laptops (1366×768) with strictly **0 horizontal overflow**.

---

## 1. Atlas Mission Operations Control Center (MOCC) Architecture & Layout

The MOCC interface is integrated as a top-level workspace mode accessible via `#btnHeaderMissionControl` (or keyboard shortcut `M`), dynamically binding to `#tabMissionControl` and expanding into a full-height dual-pane operations deck.

```
+----------------------------------------------------------------------------------------------------+
| TOP GLOBAL HEADER: Branding • Sol/MET Clock • Mode Switcher • Exaggeration • Theater/Demo CTAs   |
+--------------------------------------------------+-------------------------------------------------+
| MOCC LEFT PANE: CAMPAIGN OPERATIONS (420px)      | MOCC RIGHT PANE: 3D THEATER & SPATIAL TWIN (1fr)|
| +----------------------------------------------+ | +---------------------------------------------+ |
| | CAMPAIGN OVERVIEW KPIS & READINESS GATE      | | | TOP THEATER BAR (Sol, MET, Phase, Units)    | |
| | Dist, Sols, Duration, Science, SOC, LoS %    | | +---------------------------------------------+ |
| +----------------------------------------------+ | | CAMERA DIRECTOR | SURFACE & TRAJECTORIES     | |
| | MULTI-SOL TIMELINE & GANTT BLOCKS            | | +---------------------------------------------+ |
| | [Sol 1]--[Sol 2]--[Sol 3]--[Sol 4]           | | |                                             | |
| | > Traverse -> Sample -> Deploy Relay -> Base | | | THREE.JS 3D JEZERO SURFACE DIGITAL TWIN     | |
| +----------------------------------------------+ | | - Color-Coded Multi-Sol Polylines           | |
| | LIVE SIMULATED STATE HUD (Real-Time Gauges)  | | | - Science Target Diamond Beacons            | |
| | Battery SOC % • Storage Buffer • Slip • Link | | | - 3D Relay Masts & Microwave Fresnel Cones  | |
| +----------------------------------------------+ | | - Animated Exploration Unit Model           | |
| | CAMPAIGN DECISION & REPLANNING REVIEW PANEL  | | | - Spatial Object Inspector Card             | |
| | Contingency Ingestion • Delta Audit • Promote| | |                                             | |
| +----------------------------------------------+ | +---------------------------------------------+ |
| | OPERATIONAL COMMANDS TOOLBAR (Phase E Safe)  | | | UNIFIED BOTTOM SIMULATION TRANSPORT BAR     | |
| +----------------------------------------------+ | | Reset | Step-5s | PLAY | Step+5s | Scrubber | |
+--------------------------------------------------+-------------------------------------------------+
```

### 1.1 Campaign Overview KPIs & Decision Gate
Positioned at the top of the left operations deck, this card renders high-level campaign viability metrics calculated from verified USGS Jezero CTX 20m DTM and NASA rover engineering parameters:

- **Total Sols Planned:** Sol count badge with nominal vs buffer breakdown (e.g., `4 Sols Planned (1 Reserve Sol)`).
- **Aggregate Traverse Distance:** Total surface geodesy distance (e.g., `14,820 m` across all sorties).
- **Cumulative Mission Duration:** Planned drive time + scientific sampling dwell time + relay deployment overhead (e.g., `28.4 h`).
- **Total Science Yield Score:** Aggregate scientific return calculated across visited Jezero stratigraphic targets (e.g., `485.0 pts` using SuperCam, PIXL, and SHERLOC payload valuations).
- **Battery Consumable SOC Margin:** Minimum predicted battery State-of-Charge across all drive segments (e.g., `Min SOC: 38.2% (Reserve Margin: +18.2%)`).
- **RelayNet Comms Continuity:** Percentage of campaign traverse with direct or multi-hop Line-of-Sight to Octavia E. Butler Base (e.g., `98.4% LOS Coverage`).
- **Readiness Gate Badge:** Non-probabilistic verification tag (`MISSION FEASIBLE • NOT CERTIFIED FOR FLIGHT CREW`).

### 1.2 Multi-Sol Timeline with Interactive Sol Blocks
A vertical or horizontally scrollable Gantt-style operational schedule rendering each Sol as an autonomous block:
- **Sol Block Structure (`.mocc-sol-block`):**
  - **Header:** Sol Number (e.g., `SOL 1620`), Target Count (`3 Targets`), Sortie Distance (`3,850 m`), Est. Time (`6.2 h`).
  - **Color-Coded Status Pill:** `NOMINAL` (emerald), `CONTINGENCY_REPLAN` (amber), `ACTIVE_SIM` (cyan glow), `EXECUTED` (slate).
  - **Segmented Activity Track:** Micro-segments representing:
    - `DRIVE` (cyan): Mobility leg over terrain mesh.
    - `SCIENCE` (amber): Instrument deployment and core drill dwell.
    - `RELAY_DEPLOY` (emerald): Field mast installation and alignment.
    - `REST / BIVOUAC` (purple): Overnight thermal hold and battery trickle charge.
  - **Click-to-Focus:** Clicking a Sol block isolates that Sol's trajectory in the 3D viewer, zooms camera to the starting depot, and snaps the scrubber to MET 00:00:00 of that Sol.

### 1.3 Live Simulated State HUD (Digital Twin Telemetry)
Dynamically binds to the active time scrubber tick to provide real-time vehicle and environmental feedback:
- **Rover Kinematics:** Instantaneous heading ($0^\circ–360^\circ$), local slope gradient ($Horn\ 3\times3$, degrees), simulated ground speed ($0.38\ \text{m/s}$ nominal), and wheel slip estimate.
- **Real-Time Battery SOC Gauge:** Visual gradient bar with active percentage, current drain ($W$), and reserve limit line ($20\%$).
- **Storage Buffer Fill Gauge:** Real-time solid-state storage utilization ($GB / 16\ GB$), active instrument transfer rate ($Mbps$), and memory warning flags.
- **RF Comms Link Indicator:** Dynamic indicator displaying active link type (`DIRECT BASE`, `RELAY MRN-01 (1 HOP)`, or `COMM BLINDSPOT`), LOS terrain clearance in meters, and RF attenuation ($dB$).
- **Environmental Context:** Live Jezero MEDA in-situ atmospheric readouts (Ground Temp, Pressure, Wind Speed, Optical Depth $\tau$).

### 1.4 Campaign Decision & Replanning Review Panel
An in-line review drawer triggered when disturbances (dust storm, rockfall blockage, or instrument fault) are injected or detected:
- **Disruption Ingestion Event Log:** Displays event type, injection sol/MET, and failure classification.
- **Side-by-Side Delta Comparison Table:**
  | Metric | Baseline Plan (v1) | Contingency Plan (v2) | Operational Impact ($\Delta$) |
  | :--- | :--- | :--- | :--- |
  | **Traverse Distance** | $14,820\ \text{m}$ | $15,640\ \text{m}$ | $+820\ \text{m}\ (+5.5\%)$ |
  | **Elapsed Time** | $28.4\ \text{h}$ | $30.1\ \text{h}$ | $+1.7\ \text{h}$ |
  | **Science Yield** | $485.0\ \text{pts}$ | $460.0\ \text{pts}$ | $-25.0\ \text{pts}\ (1\ \text{target dropped})$ |
  | **Min Battery SOC** | $38.2\%$ | $24.8\%$ | $-13.4\%\ (\text{Low Reserve Alert})$ |
  | **Relays Deployed** | $2\ \text{towers}$ | $3\ \text{towers}$ | $+1\ \text{tower}\ (\text{MRN-03 added})$ |
- **Executive Actions:**
  - `[APPROVE & PROMOTE TO ACTIVE]`: Atomic commit promoting v2 to active flight plan across all views.
  - `[EXPORT REPLANNING DOSSIER]`: Generates structured Markdown / JSON audit pack.
  - `[REVERT TO BASELINE]`: Aborts contingency plan and restores v1 baseline.

---

## 2. 3D Mission Theater Story Mode Integration

The 3D Mission Theater Story Mode converts the static Jezero Crater DTM surface mesh into a living four-dimensional narrative of the campaign.

```
       [Sun Directional Light]
                  \
                   v
+--------------------------------------------------------+
| 3D Jezero Crater Mesh (USGS CTX 20m DTM)               |
|                                                        |
|   (Octavia Butler Base)                                |
|        [O]===================                          |
|         \\   Sol 1 Path     \\ Sol 2 Path               |
|          \\  (#00e5ff)       \\ (#10b981)              |
|           v                   v                        |
|       (Target A)          (Target B)                   |
|       [Diamond]           [Diamond]                    |
|           \                   /                        |
|            \    [Relay Mast] / (Microwave Link Beam)   |
|             \       /\      /                          |
|              ======[/\ ]====                           |
|               Sol 3 Path (#a855f7)                     |
|                                                        |
|   [Rover 3D Unit Mesh] ---> Moving with Timeline       |
|    - Animated Mast Camera                              |
|    - Dynamic Headlights & Dust Wake                    |
+--------------------------------------------------------+
```

### 2.1 Multi-Sol Traverses with Color-Coded Sol Paths
Each Sol's path is rendered as a distinct 3D polyline draped over the bilinear interpolated terrain elevation with customizable vertical exaggeration ($1.0\times$ to $3.0\times$):
- **Chromatic Sol Palette:**
  - **Sol 1:** Cyan (`#00e5ff`) – Initial delta traverse from Octavia E. Butler Base to Three Forks Depot.
  - **Sol 2:** Emerald (`#10b981`) – Delta scarp ascent and sample caching.
  - **Sol 3:** Purple (`#a855f7`) – Hawksbill Gap exploration and promontory relay placement.
  - **Sol 4:** Amber (`#f59e0b`) – Western fan rim survey.
  - **Sol 5+:** Rose / Magenta (`#f43f5e`) – Extended mission egress / sample cache recovery.
- **Polyline Styling & Depth Buffer:**
  - Plotted using `THREE.Line` / custom ribbon geometry elevated $+1.8\ \text{m}$ above local DTM surface to prevent z-fighting with terrain polygons.
  - **Executed / Historical Legs:** Solid, slightly dimmed polyline ($0.6$ opacity).
  - **Active Sol Leg:** Vibrant, glowing polyline with animated shader dash offset (`dashSize: 10`, `gapSize: 4`).
  - **Future / Planned Legs:** Semi-transparent dashed polyline ($0.4$ opacity).

### 2.2 Spatial Science Target Markers & Depots
Interactive 3D markers positioned at certified Jezero target coordinates:
- **Geometry:** Floating octahedron (diamond) suspended above a semi-transparent vertical cylinder beacon grounded on the terrain.
- **Color Coding:**
  - High Priority Sample Target ($\ge 85$ pts): Glowing gold/amber (`#f59e0b`).
  - Medium Priority Survey Site: Cyan (`#00e5ff`).
  - Sample Tube Depot / Drop Point: White/Emerald striped beacon (`#10b981`).
- **Interactive Hover & Click States:**
  - Hovering creates a pulsating elevation ring and reveals target name badge.
  - Clicking invokes `#theaterInspectorCard` with target geology, scientific rationale, instrument suites (SuperCam, PIXL, SHERLOC), core tube ID, and expected data volume.

### 2.3 Deployed Relay Towers & Microwave Fresnel Beams
Renders autonomous Mars RelayNet infrastructure:
- **Relay Tower 3D Mesh:** Procedural aluminum lattice mast ($8.0\ \text{m}$ height) with omnidirectional high-gain dish pointing toward Base Station.
- **Line-of-Sight RF Beams:**
  - `Active Multi-Hop Link`: Continuous glowing cyan beam connecting Rover $\rightarrow$ Relay Tower $\rightarrow$ Base Station.
  - `Clear LOS Mesh`: Thin green vectors indicating available backhaul lines.
  - `Obstructed LOS Rays`: Red dashed lines terminating at terrain collision points with impact hazard rings.

### 2.4 Dynamic Timeline Scrubber & Story Playback Synchronization
The bottom transport bar controls campaign time progression:
- **Time Representation:** Dual-clock display showing **Sol Day** + **Mission Elapsed Time (MET)** (`Sol 1620 • 04:12:35`).
- **Kinematic Interpolation:** Scrubber ticks dynamically calculate Rover position $(x, y, z)$ by parameterizing the active Sol's polyline by distance and speed ($0.38\ \text{m/s}$), computing tangent heading, terrain normal pitch, and roll.
- **Camera Director Modes:**
  - `ORBIT`: Free user camera navigation around target coordinate.
  - `TOPOGRAPHIC`: High-angle oblique perspective showcasing scarp relief.
  - `FOLLOW UNIT`: Smooth third-person chase camera locked to rover heading ($15\ \text{m}$ offset, $+6\ \text{m}$ elevation).
  - `OVERVIEW`: Jezero Crater bounding overview ($5.0 \times 5.0\ \text{km}$) framing all multi-sol loops.
  - `EVENT FOCUS`: Camera automatically dollies to highlight active disruptions or relay deployment operations.

### 2.5 5-Tier Spatial Click Inspectors
Integrated raycaster hierarchy handling user clicks on 3D elements:
1. **Tier 1 (Rover Unit):** Inspects rover state, battery margin, motor currents, payload bay status.
2. **Tier 2 (Science Target):** Inspects target priority, scientific objectives, sample tube allocation.
3. **Tier 3 (Relay Tower / Base):** Inspects antenna height, elevation, active hops, backhaul link status.
4. **Tier 4 (Sol Route Segment):** Inspects segment distance, slope, Apollo Waligora metabolic cost, Bekker-Wong rolling resistance, energy Wh.
5. **Tier 5 (Terrain Mesh):** Inspects USGS DTM elevation, Horn $3\times3$ slope gradient, planetocentric lat/lon.

---

## 3. DOM Structure, Responsive Styling & `window.Atlas` API

### 3.1 DOM Structure (`web/index.html`)

```html
<!-- MOCC Workstation Tab Content Panel -->
<div id="tabMissionControl" class="inspector-tab-panel mocc-container">
  
  <!-- MOCC Header & Campaign Selector Toolbar -->
  <div class="mocc-header-deck">
    <div class="mocc-title-block">
      <span class="mocc-title-badge">&#128640; ATLAS MOCC</span>
      <h2 class="mocc-headline">MISSION OPERATIONS CONTROL CENTER</h2>
      <span id="moccActiveSolPill" class="mocc-sol-pill">SOL 1620</span>
    </div>
    <div class="mocc-toolbar-actions">
      <select id="moccCampaignSelect" class="hud-select mocc-campaign-select" title="Select Active Multi-Sol Campaign">
        <option value="cmp_jezero_delta_5sol">Campaign 1: Jezero Delta Multi-Sol Traverse (5 Sols)</option>
        <option value="cmp_crater_rim_scout">Campaign 2: Jezero Crater Rim Long-Range Scout (3 Sols)</option>
        <option value="cmp_sample_depot_egress">Campaign 3: Three Forks Sample Depot Egress (2 Sols)</option>
      </select>
      <button id="btnMoccReplan" class="btn-secondary mocc-btn-replan" title="Trigger Contingency Replanning">&#9889; Contingency Replan</button>
      <button id="btnMoccLaunchTheater" class="btn-primary mocc-btn-theater" title="Expand Fullscreen 3D Mission Theater">&#127917; 3D Theater</button>
    </div>
  </div>

  <!-- Campaign Overview KPIs Deck -->
  <div class="mocc-kpi-deck">
    <div class="mocc-kpi-card">
      <span class="mocc-kpi-label">TOTAL DISTANCE</span>
      <strong id="moccKpiDist" class="mocc-kpi-val text-cyan">14.82 km</strong>
      <span class="mocc-kpi-sub">5 Multi-Sol Sorties</span>
    </div>
    <div class="mocc-kpi-card">
      <span class="mocc-kpi-label">CAMPAIGN TIME</span>
      <strong id="moccKpiTime" class="mocc-kpi-val text-white">28.4 h</strong>
      <span class="mocc-kpi-sub">Drive + Dwell + Deploy</span>
    </div>
    <div class="mocc-kpi-card">
      <span class="mocc-kpi-label">SCIENCE YIELD</span>
      <strong id="moccKpiScience" class="mocc-kpi-val text-emerald">485.0 pts</strong>
      <span class="mocc-kpi-sub">12 Geological Targets</span>
    </div>
    <div class="mocc-kpi-card">
      <span class="mocc-kpi-label">MIN BATTERY SOC</span>
      <strong id="moccKpiSoc" class="mocc-kpi-val text-emerald">38.2%</strong>
      <span class="mocc-kpi-sub">+18.2% Reserve Margin</span>
    </div>
    <div class="mocc-kpi-card">
      <span class="mocc-kpi-label">LOS COMMS COVERAGE</span>
      <strong id="moccKpiComms" class="mocc-kpi-val text-cyan">98.4%</strong>
      <span class="mocc-kpi-sub">2 Relays Deployed</span>
    </div>
    <div class="mocc-kpi-card">
      <span class="mocc-kpi-label">DECISION GATE</span>
      <strong id="moccKpiGate" class="mocc-kpi-val text-emerald">FEASIBLE</strong>
      <span class="mocc-kpi-sub">All Invariants Pass</span>
    </div>
  </div>

  <!-- Multi-Sol Timeline & Interactive Sol Blocks Deck -->
  <div class="mocc-timeline-deck">
    <div class="mocc-section-header">
      <span class="mocc-section-title">&#128506; MULTI-SOL CAMPAIGN TIMELINE</span>
      <div class="mocc-sol-legend">
        <span class="sol-legend-item"><span class="sol-dot sol-1"></span>Sol 1</span>
        <span class="sol-legend-item"><span class="sol-dot sol-2"></span>Sol 2</span>
        <span class="sol-legend-item"><span class="sol-dot sol-3"></span>Sol 3</span>
        <span class="sol-legend-item"><span class="sol-dot sol-4"></span>Sol 4</span>
        <span class="sol-legend-item"><span class="sol-dot sol-5"></span>Sol 5</span>
      </div>
    </div>
    <div id="moccSolBlocksContainer" class="mocc-sol-blocks-grid">
      <!-- Dynamic Sol Block Cards rendered by app.js -->
    </div>
  </div>

  <!-- Live Simulated State HUD (Digital Twin Cockpit) -->
  <div class="mocc-telemetry-deck">
    <div class="mocc-section-header">
      <span class="mocc-section-title">&#128225; LIVE SIMULATED STATE HUD</span>
      <span id="moccLiveMetClock" class="font-mono text-cyan">MET 01:24:15 • SOL 1620</span>
    </div>
    <div class="mocc-hud-grid">
      <!-- Kinematic & Heading -->
      <div class="mocc-hud-card">
        <div class="mocc-hud-row"><span>HDG:</span> <strong id="moccLiveHeading">142.5&deg;</strong></div>
        <div class="mocc-hud-row"><span>SLOPE:</span> <strong id="moccLiveSlope" class="text-emerald">4.2&deg; (Horn 3x3)</strong></div>
        <div class="mocc-hud-row"><span>SPEED:</span> <strong id="moccLiveSpeed">0.38 m/s</strong></div>
      </div>
      <!-- Battery SOC Gauge -->
      <div class="mocc-hud-card">
        <div class="mocc-hud-label-row">
          <span>BATTERY SOC:</span>
          <strong id="moccLiveSocText" class="text-emerald">84.2% (4,041 Wh)</strong>
        </div>
        <div class="mocc-gauge-track">
          <div id="moccLiveSocFill" class="mocc-gauge-fill" style="width: 84.2%; background: #10b981;"></div>
          <div class="mocc-gauge-reserve-line" style="left: 20%;" title="20% Reserve Margin"></div>
        </div>
        <div class="mocc-hud-subtext">Drain: 184.2 W • Margin: +64.2%</div>
      </div>
      <!-- Storage Capacity Gauge -->
      <div class="mocc-hud-card">
        <div class="mocc-hud-label-row">
          <span>SCIENCE BUFFER:</span>
          <strong id="moccLiveBufferText" class="text-cyan">3.2 / 16 GB (20%)</strong>
        </div>
        <div class="mocc-gauge-track">
          <div id="moccLiveBufferFill" class="mocc-gauge-fill" style="width: 20%; background: #00e5ff;"></div>
        </div>
        <div class="mocc-hud-subtext">Transfer: 2.0 Mbps • Queue: 1 Target</div>
      </div>
      <!-- RF Link & LOS -->
      <div class="mocc-hud-card">
        <div class="mocc-hud-row"><span>RF LINK:</span> <strong id="moccLiveRfStatus" class="text-emerald">DIRECT (BASE)</strong></div>
        <div class="mocc-hud-row"><span>LOS CLEAR:</span> <strong id="moccLiveLosClearance">+18.4 m</strong></div>
        <div class="mocc-hud-row"><span>HOPS:</span> <strong id="moccLiveHops">0 (Direct)</strong></div>
      </div>
    </div>
  </div>

  <!-- Campaign Replanning & Decision Review Drawer (Hidden by default, shown on replan) -->
  <div id="moccReplanningDrawer" class="mocc-replanning-drawer hidden">
    <div class="mocc-drawer-header">
      <div style="display:flex; align-items:center; gap:8px;">
        <span class="text-amber font-bold">&#9889; CAMPAIGN CONTINGENCY REPLANNING &amp; DELTA REVIEW</span>
        <span id="moccReplanBadge" class="mocc-badge amber">HAZARD INGESTION</span>
      </div>
      <button id="btnCloseMoccReplan" class="btn-close">&times;</button>
    </div>
    <div class="mocc-drawer-body">
      <div id="moccReplanNarrative" class="mocc-replan-narrative">
        Rockfall disruption injected on Sol 2 (MET 02:15:00) severed nominal delta ascent corridor. Multi-sol replanner synthesized detour and relocated Relay MRN-02 to maintain uninterrupted LOS.
      </div>
      <table class="mocc-delta-table">
        <thead>
          <tr>
            <th>METRIC</th>
            <th>BASELINE PLAN</th>
            <th>CONTINGENCY PLAN</th>
            <th>OPERATIONAL DELTA</th>
          </tr>
        </thead>
        <tbody id="moccDeltaTableBody">
          <!-- Filled dynamically -->
        </tbody>
      </table>
      <div class="mocc-drawer-actions">
        <button id="btnMoccRevertReplan" class="btn-secondary">Revert to Baseline</button>
        <button id="btnMoccExportReplan" class="btn-secondary">&#128196; Export Decision Dossier</button>
        <button id="btnMoccPromotePlan" class="btn-primary mocc-btn-promote">&#128640; Approve &amp; Promote Plan</button>
      </div>
    </div>
  </div>

</div>
```

---

### 3.2 Responsive Styling Specification (`web/styles.css`)

Strict layout constraints ensure **zero horizontal body overflow** (`overflow-x: hidden`), seamless flex/grid wrapping, and full responsiveness across:
- **Primary Workstation Resolution:** `1920 × 1080` (Standard Dual-Pane Layout).
- **Tactical Field Laptop Resolution:** `1366 × 768` (Condensed Compact Layout).

```css
/* =============================================================================
   Milestone 13H: Atlas Mission Operations Control Center (MOCC) Styles
   ============================================================================= */

/* Universal Layout & Overflow Guard */
html, body {
  margin: 0;
  padding: 0;
  width: 100%;
  max-width: 100vw;
  overflow-x: hidden !important;
  box-sizing: border-box;
}

*, *::before, *::after {
  box-sizing: inherit;
}

/* MOCC Main Tab Container */
.mocc-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  max-width: 100%;
  padding: 12px 16px;
  box-sizing: border-box;
  overflow-x: hidden;
  overflow-y: auto;
  max-height: calc(100vh - 120px);
}

/* Header Deck */
.mocc-header-deck {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.mocc-title-block {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mocc-title-badge {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.8px;
  color: var(--telemetry-cyan);
  background: rgba(0, 229, 255, 0.12);
  border: 1px solid rgba(0, 229, 255, 0.3);
  padding: 3px 6px;
  border-radius: 3px;
}

.mocc-headline {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: #ffffff;
}

.mocc-sol-pill {
  font-size: 9px;
  font-family: var(--font-mono);
  font-weight: 700;
  color: #10b981;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.35);
  padding: 2px 6px;
  border-radius: 10px;
}

.mocc-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mocc-campaign-select {
  font-size: 10px;
  font-weight: 600;
  padding: 4px 8px;
  min-width: 240px;
  max-width: 380px;
}

/* Campaign Overview KPIs Deck */
.mocc-kpi-deck {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
  width: 100%;
}

.mocc-kpi-card {
  display: flex;
  flex-direction: column;
  padding: 8px 10px;
  background: rgba(15, 23, 42, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 5px;
}

.mocc-kpi-label {
  font-size: 8px;
  font-weight: 700;
  color: var(--text-tertiary);
  letter-spacing: 0.5px;
}

.mocc-kpi-val {
  font-size: 14px;
  font-family: var(--font-mono);
  font-weight: 800;
  margin: 2px 0;
}

.mocc-kpi-sub {
  font-size: 8px;
  color: #94a3b8;
}

/* Multi-Sol Timeline Deck */
.mocc-timeline-deck {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 10px 12px;
}

.mocc-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.6px;
  color: #cbd5e1;
}

.mocc-sol-legend {
  display: flex;
  gap: 8px;
  font-size: 8px;
}

.sol-legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.sol-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.sol-dot.sol-1 { background: #00e5ff; box-shadow: 0 0 5px #00e5ff; }
.sol-dot.sol-2 { background: #10b981; box-shadow: 0 0 5px #10b981; }
.sol-dot.sol-3 { background: #a855f7; box-shadow: 0 0 5px #a855f7; }
.sol-dot.sol-4 { background: #f59e0b; box-shadow: 0 0 5px #f59e0b; }
.sol-dot.sol-5 { background: #f43f5e; box-shadow: 0 0 5px #f43f5e; }

.mocc-sol-blocks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
  width: 100%;
}

.mocc-sol-card {
  display: flex;
  flex-direction: column;
  padding: 8px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mocc-sol-card:hover {
  background: rgba(30, 41, 59, 0.9);
  border-color: var(--telemetry-cyan);
  transform: translateY(-1px);
}

.mocc-sol-card.active {
  background: rgba(0, 229, 255, 0.12);
  border-color: #00e5ff;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.25);
}

.mocc-sol-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.mocc-sol-title {
  font-size: 10px;
  font-weight: 800;
  color: #ffffff;
}

.mocc-sol-tag {
  font-size: 7.5px;
  padding: 1px 4px;
  border-radius: 2px;
  font-weight: 600;
}

.mocc-activity-bar {
  display: flex;
  height: 6px;
  width: 100%;
  border-radius: 3px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.4);
  margin-bottom: 6px;
}

.act-seg.drive { background: #00e5ff; }
.act-seg.science { background: #f59e0b; }
.act-seg.relay { background: #10b981; }
.act-seg.bivouac { background: #a855f7; }

.mocc-sol-stats {
  display: flex;
  justify-content: space-between;
  font-size: 8px;
  font-family: var(--font-mono);
  color: #cbd5e1;
}

/* Live Simulated State HUD Deck */
.mocc-telemetry-deck {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 10px 12px;
}

.mocc-hud-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  width: 100%;
}

.mocc-hud-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  font-size: 8.5px;
}

.mocc-hud-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mocc-hud-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 700;
}

.mocc-gauge-track {
  position: relative;
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.mocc-gauge-fill {
  height: 100%;
  transition: width 0.2s ease, background 0.3s ease;
}

.mocc-gauge-reserve-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #f59e0b;
}

.mocc-hud-subtext {
  font-size: 7.5px;
  color: #94a3b8;
}

/* Replanning Drawer */
.mocc-replanning-drawer {
  background: rgba(24, 18, 10, 0.95);
  border: 1px solid rgba(245, 158, 11, 0.4);
  border-radius: 6px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mocc-replanning-drawer.hidden {
  display: none !important;
}

.mocc-drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mocc-replan-narrative {
  font-size: 9px;
  line-height: 1.4;
  color: #fde68a;
}

.mocc-delta-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 8.5px;
  font-family: var(--font-mono);
}

.mocc-delta-table th, .mocc-delta-table td {
  padding: 4px 8px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.mocc-delta-table th {
  color: #94a3b8;
  font-weight: 600;
}

.mocc-drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 6px;
}

.mocc-btn-promote {
  background: linear-gradient(135deg, #059669 0%, #10b981 100%);
  border-color: #10b981;
  color: #ffffff;
}

/* =============================================================================
   Responsive Breakpoints: 1920x1080 and 1366x768 Protection
   ============================================================================= */

/* 1366px Laptop Displays */
@media (max-width: 1440px) {
  .mocc-container {
    padding: 8px 10px;
    gap: 8px;
  }
  .mocc-kpi-deck {
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
  }
  .mocc-kpi-val {
    font-size: 12px;
  }
  .mocc-hud-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 6px;
  }
  .mocc-campaign-select {
    min-width: 180px;
  }
}

/* 1024px and Smaller Mobile/Tablets */
@media (max-width: 1024px) {
  .mocc-kpi-deck {
    grid-template-columns: repeat(2, 1fr);
  }
  .mocc-hud-grid {
    grid-template-columns: 1fr;
  }
}
```

---

### 3.3 Three.js 3D Mission Theater Story Engine (`web/app.js`)

Below is the procedural implementation pattern for multi-sol path rendering, dynamic target markers, and dynamic scrubber synchronization:

```javascript
// =============================================================================
// Milestone 13H: 3D Mission Theater Story Mode Engine
// =============================================================================

let moccActiveCampaign = null;
let moccActiveSolIndex = 0;
let moccStoryPlaybackActive = false;
let moccPlaybackSpeed = 1.0;
let moccStoryMetSeconds = 0;
let moccTotalCampaignMetSeconds = 100000;

// Three.js Scene Groups
let theaterStoryGroup = null;
let theaterMultiSolPathsGroup = null;
let theaterScienceMarkersGroup = null;
let theaterRelayTowersGroup = null;
let theaterRfBeamsGroup = null;

const SOL_COLORS = [
  0x00e5ff, // Sol 1: Cyan
  0x10b981, // Sol 2: Emerald
  0xa855f7, // Sol 3: Purple
  0xf59e0b, // Sol 4: Amber
  0xf43f5e  // Sol 5: Rose
];

function initTheaterStoryEngine() {
  if (!jezeroSurfaceGroup) return;
  if (!theaterStoryGroup) {
    theaterStoryGroup = new THREE.Group();
    theaterStoryGroup.name = 'theaterStoryGroup';

    theaterMultiSolPathsGroup = new THREE.Group();
    theaterMultiSolPathsGroup.name = 'theaterMultiSolPathsGroup';

    theaterScienceMarkersGroup = new THREE.Group();
    theaterScienceMarkersGroup.name = 'theaterScienceMarkersGroup';

    theaterRelayTowersGroup = new THREE.Group();
    theaterRelayTowersGroup.name = 'theaterRelayTowersGroup';

    theaterRfBeamsGroup = new THREE.Group();
    theaterRfBeamsGroup.name = 'theaterRfBeamsGroup';

    theaterStoryGroup.add(theaterMultiSolPathsGroup);
    theaterStoryGroup.add(theaterScienceMarkersGroup);
    theaterStoryGroup.add(theaterRelayTowersGroup);
    theaterStoryGroup.add(theaterRfBeamsGroup);

    jezeroSurfaceGroup.add(theaterStoryGroup);
  }
  console.log('[MissionTheater] Story Mode Engine initialized on Jezero Surface Group.');
}

/**
 * Render Multi-Sol Traverses with Color-Coded Polylines
 */
function renderMultiSolTraverses(solsData) {
  if (!theaterMultiSolPathsGroup) return;
  
  // Clear previous paths
  while (theaterMultiSolPathsGroup.children.length > 0) {
    const child = theaterMultiSolPathsGroup.children[0];
    theaterMultiSolPathsGroup.remove(child);
    if (child.geometry) child.geometry.dispose();
    if (child.material) child.material.dispose();
  }

  solsData.forEach((sol, idx) => {
    const solColor = SOL_COLORS[idx % SOL_COLORS.length];
    const points = [];

    sol.traverse_points.forEach(pt => {
      // Bilinear interpolation for true terrain z
      const x = (pt.col - 128) * 20.0;
      const y = (128 - pt.row) * 20.0;
      const elev = getInterpolatedElevation(pt.row, pt.col);
      const z = (elev * currentExaggeration) + 1.8; // +1.8m clearance above DTM
      points.push(new THREE.Vector3(x, y, z));
    });

    if (points.length >= 2) {
      const geom = new THREE.BufferGeometry().setFromPoints(points);
      const mat = new THREE.LineBasicMaterial({
        color: solColor,
        linewidth: 3,
        transparent: true,
        opacity: (idx === moccActiveSolIndex) ? 0.95 : 0.45
      });
      const lineMesh = new THREE.Line(geom, mat);
      lineMesh.userData = {
        type: 'mocc_sol_path',
        solIndex: idx,
        solNumber: sol.sol_number || (idx + 1),
        stats: sol
      };
      theaterMultiSolPathsGroup.add(lineMesh);
    }
  });
}

/**
 * Render 3D Science Target Diamond Beacons
 */
function renderStoryScienceTargets(targets) {
  if (!theaterScienceMarkersGroup) return;

  while (theaterScienceMarkersGroup.children.length > 0) {
    const child = theaterScienceMarkersGroup.children[0];
    theaterScienceMarkersGroup.remove(child);
  }

  targets.forEach(tgt => {
    const x = (tgt.col - 128) * 20.0;
    const y = (128 - tgt.row) * 20.0;
    const elev = getInterpolatedElevation(tgt.row, tgt.col);
    const zBase = elev * currentExaggeration;

    const group = new THREE.Group();
    group.position.set(x, y, zBase);

    // 1. Vertical Guide Cylinder
    const cylGeom = new THREE.CylinderGeometry(0.5, 0.5, 20, 8);
    cylGeom.rotateX(Math.PI / 2);
    const cylMat = new THREE.MeshBasicMaterial({
      color: 0x00e5ff,
      transparent: true,
      opacity: 0.35
    });
    const cyl = new THREE.Mesh(cylGeom, cylMat);
    cyl.position.z = 10;
    group.add(cyl);

    // 2. Suspended Diamond Beacon (Octahedron)
    const diamGeom = new THREE.OctahedronGeometry(4.0, 0);
    const diamMat = new THREE.MeshStandardMaterial({
      color: tgt.priority >= 80 ? 0xf59e0b : 0x00e5ff,
      emissive: tgt.priority >= 80 ? 0xf59e0b : 0x00e5ff,
      emissiveIntensity: 0.5,
      metalness: 0.2,
      roughness: 0.3
    });
    const diamond = new THREE.Mesh(diamGeom, diamMat);
    diamond.position.z = 22;
    group.add(diamond);

    group.userData = {
      type: 'mocc_science_target',
      targetData: tgt
    };

    theaterScienceMarkersGroup.add(group);
  });
}

/**
 * Dynamic Scrubber Time Update & Telemetry Sync
 */
function updateStoryPlayback(metSeconds) {
  moccStoryMetSeconds = metSeconds;

  // 1. Find active Sol and interpolation point
  const currentSol = getSolFromMet(metSeconds);
  if (currentSol && currentSol.solIndex !== moccActiveSolIndex) {
    moccActiveSolIndex = currentSol.solIndex;
    updateMoccActiveSolUI(moccActiveSolIndex);
  }

  // 2. Kinematic rover position
  const pose = computeRoverPoseAtMet(metSeconds);
  if (pose && playbackVehicleMesh) {
    playbackVehicleMesh.position.set(pose.x, pose.y, pose.z);
    playbackVehicleMesh.rotation.z = pose.headingRad;
    playbackVehicleMesh.visible = true;
  }

  // 3. Update Camera Director if in Follow Mode
  if (currentCameraDirectorMode === 'follow' && pose) {
    const camOffset = new THREE.Vector3(
      -Math.sin(pose.headingRad) * 20.0,
      -Math.cos(pose.headingRad) * 20.0,
      10.0
    );
    camera.position.copy(playbackVehicleMesh.position).add(camOffset);
    camera.lookAt(playbackVehicleMesh.position);
  }

  // 4. Update HUD Telemetry
  updateMoccLiveHud(pose, metSeconds);
}
```

---

### 3.4 Integration with `window.Atlas` Public Interface

The public `window.Atlas` (and `window.MarsWalk`) namespace is extended to provide comprehensive operational and automated testing hooks:

```javascript
// Expose Milestone 13H API on window.Atlas
window.Atlas.mocc = {
  // Campaign Management
  loadCampaign: (campaignId) => loadMoccCampaignAction(campaignId),
  getCampaignData: () => moccActiveCampaign,
  selectSol: (solIndex) => setMoccActiveSol(solIndex),
  
  // 3D Mission Theater Story Mode
  enterStoryMode: () => enterMissionTheaterStoryMode(),
  scrubTimeline: (metSeconds) => updateStoryPlayback(metSeconds),
  setPlaybackRate: (rateMultiplier) => setStoryPlaybackSpeed(rateMultiplier),
  togglePlayPause: () => toggleStoryPlayPause(),
  
  // Contingency & Replanning
  injectContingency: (disruptionPayload) => triggerMoccContingencyReplan(disruptionPayload),
  promoteActivePlan: () => promoteMoccActivePlan(),
  getReplanningAudit: () => moccReplanningState,
  
  // Camera Director
  setStoryCameraDirector: (mode) => setCameraDirectorMode(mode) // 'orbit' | 'topographic' | 'follow' | 'overview' | 'focus'
};
```

---

## 4. Verification & Acceptance Criteria Matrix

| Verification Dimension | Acceptance Standard | Method of Validation |
| :--- | :--- | :--- |
| **0 Horizontal Overflow** | Body and `.mocc-container` width strictly $\le 100\text{vw}$ at $1920\times1080$ and $1366\times768$. Zero horizontal scrollbar appearance. | Chrome DevTools viewport resize check; document width assertion. |
| **Multi-Sol Gantt Layout** | Sol cards render dynamically with color-coded chromatic dots, segmented activity bars, distance, duration, and target counts. | DOM inspection of `#moccSolBlocksContainer` against active campaign payload. |
| **3D Trajectory Elevation** | Polylines elevated $+1.8\ \text{m}$ above local USGS Jezero DTM surface with proper vertical exaggeration scaling. | 3D raycasting and depth buffer check; no z-fighting against terrain mesh. |
| **Scrubber Synchronization** | Moving `#theaterTimelineScrubber` or `#mcTimelineScrubber` updates Rover 3D position, heading, Sol card highlight, and Live State HUD simultaneously. | Automated scrub tick evaluation from MET $00:00:00$ to $28:24:00$. |
| **Contingency Replanning** | Ingesting a hazard populates `#moccReplanningDrawer` with Delta table ($+820\ \text{m}$, $-25\ \text{pts}$, etc.) and enables atomic promotion. | Simulated test call to `window.Atlas.mocc.injectContingency()`. |
| **Scientific Attribution** | Every telemetry item references primary source: USGS Jezero 20m DTM, Apollo Waligora (1972), Bekker-Wong, or NASA PDS4 MEDA. | Spatial click inspector validation with provenance citation check. |

---
*Report submitted by Agent D (Frontend & Mission Theater Specialist) for Milestone 13H Integration.*
</SYSTEM_MESSAGE>