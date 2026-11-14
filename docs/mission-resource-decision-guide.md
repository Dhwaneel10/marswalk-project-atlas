# Atlas Mission Resource Intelligence: Operator & Evaluator Decision Guide

## 1. Overview & Operational Philosophy

The **Atlas Mission Resource Intelligence Subsystem** provides mission planners, science leads, and flight evaluators with computational clarity regarding the feasibility of Martian surface traverses.

A plan that is geometrically optimal or maintains line-of-sight visibility may still fail if the cumulative energy demand exceeds the rover's usable battery capacity or breaches the mandatory safety reserve.

The Joint Mission Co-Design Studio integrates traverse geometry, line-of-sight relay deployment, terramechanical energy, and operational timelines into a unified 7-step planning pipeline.

---

## 2. The 7-Step Co-Design Wizard Workflow

```
+----------------------------------------------------------------------------------------------------+
|                                 JOINT MISSION STUDIO STEPPER                                       |
|                                                                                                    |
|  [1. MISSION]   -->  [2. MOBILITY]  -->  [3. COMMS]   -->  [4. ENERGY]                             |
|  Targets & Goals     Platform & Mast      Range & Relays    Capacity & Subsystems                  |
|                                                                   |                                |
|                                                                   v                                |
|  [7. PROMOTE]   <--  [6. PARETO]    <--  [5. SOLVE]   <-----------+                                |
|  Export Dossier      Trade-offs & HUD     Optimizer Engine                                         |
+----------------------------------------------------------------------------------------------------+
```

### Step 1: Mission Definition & Objectives
- Select starting base location (e.g. *Octavia E. Butler Landing Base* at `[117, 157]`).
- Select destination target (e.g. *Delta Scarp Lookout* at `[138, 114]`).
- Define multi-objective optimization weights:
  - Traverse Distance weight ($w_{\text{dist}}$)
  - Communications Blackout Gap weight ($w_{\text{gap}}$)
  - Relay Deployment Cost weight ($w_{\text{relays}}$)
  - Terramechanical Energy weight ($w_{\text{energy}}$)

### Step 2: Rover Mobility & Platform Architecture
- Configure vehicle mobility platform (e.g. *Perseverance Heavy Rover* $1025\text{ kg}$).
- Set rover antenna mast height ($2.5\text{ m}$ nominal).
- Configure slope threshold limits ($\le 12^\circ$ nominal traversable, $\ge 18^\circ$ severe hazard).

### Step 3: Communications Network & Tower Budgets
- Configure base station mast height ($10.0\text{ m}$ nominal).
- Set portable field relay mast height ($8.0\text{ m}$ nominal).
- Set allowable relay deployment budget ($0$ to $3$ towers).
- Specify maximum RF range limits ($2500\text{ m}$ direct, $5000\text{ m}$ relay).

### Step 4: Energy & Resource Subsystems Configuration
- Choose from pre-configured engineering presets or fine-tune custom parameters:
  - **Perseverance Nominal:** $1025\text{ kg}$, $4800\text{ Wh}$ battery, $20\%$ reserve, $0.08\text{ }C_{rr}$, $0.72$ drivetrain efficiency, $110\text{ W}$ base avionics, $120\text{ W}$ science payload.
  - **High-Power Drill & Sampling:** $1050\text{ kg}$, $4800\text{ Wh}$ battery, $25\%$ reserve, $220\text{ W}$ high-load percussion drill, $1800\text{ s}$ dwell.
  - **Ultralight Scout Rover:** $185\text{ kg}$, $850\text{ Wh}$ battery, $15\%$ reserve, $0.55\text{ m/s}$ speed, $45\text{ W}$ lightweight avionics.
  - **Crew EVA Sortie (Exploration Life-Support):** $150\text{ kg}$ suit + life support, $1200\text{ Wh}$ backpack battery, $35\%$ safety reserve floor.
- Toggle non-regenerative descent physics (disabled by default in accordance with authentic planetary rover operations).

### Step 5: Coupled Co-Design Solver
- Initiates coupled exploration across alternative traverses and candidate promontory relay sites.
- Computes Pareto non-dominated configurations across distance, blackout gap, relay towers, and energy.

### Step 6: Interactive Pareto Frontier & Feasibility Scorecard
- Inspect the Pareto Frontier scatter plot across selectable trade-off dimensions:
  - **Energy vs Distance:** Highlights how detouring around steep ridges saves battery climbing work despite longer path distance.
  - **Energy vs Gap Duration:** Shows the resource cost of maintaining communications via detour versus deploying a field relay.
  - **Distance vs Gap Duration:** Classic geometric mobility versus connectivity trade-off.
- Scorecard Table columns:
  - Candidate ID & Pareto Rank (Rank 1 vs Dominated)
  - Traverse Distance (m)
  - Mission Duration (HH:MM:SS)
  - Comms Coverage (%)
  - Relay Towers Deployed
  - Energy Consumed (Wh)
  - Energy Remaining (Wh)
  - Usable Reserve Margin (%)
  - Feasibility Classification Badge

### Step 7: Promotion & Mission Dossier Export
- Promotes selected candidate as active mission plan across Atlas (Campaign Planner, Mission Theater, Robustness Lab).
- Exports complete Markdown Decision Dossier with cryptographic SHA-256 fingerprint and USGS CTX DTM provenance citations.

---

## 3. Interpreting Feasibility Classifications & Triage

| Feasibility State | Badge Styling | Meaning | Recommended Operator Triage |
|---|---|---|---|
| `FEASIBLE_WITHIN_CONFIGURED_BUDGET` | Green (`.feasible`) | Battery SOC at mission end strictly exceeds configured safety reserve floor. All deadlines met. | Nominal configuration. Candidate is ready for mission promotion. |
| `FEASIBLE_WITH_LOW_RESERVE` | Amber (`.low-reserve`) | Battery remains positive, but final SOC penetrates into the reserve margin. | Increase battery allocation, decrease science dwell duration, or choose a flatter contour route. |
| `CRITICAL_ENERGY_VIOLATION` | Crimson (`.energy-violation`) | Usable energy reaches 0% before traverse completes. Rover becomes stranded. | Add promontory relay to avoid long detours, reduce payload mass, or select an alternative staging base. |
| `SCHEDULE_TIME_EXHAUSTION` | Crimson (`.time-violation`) | Total mission duration exceeds diurnal daylight or operational shift window. | Increase nominal drive speed ($v_{\text{drive}}$) or reduce waypoint dwell duration. |
| `MULTI_CONSTRAINT_VIOLATION` | Crimson (`.multi-violation`) | Multiple boundaries breached (e.g. both battery depletion and schedule timeout). | Major mission replan required. Re-evaluate relay deployment budget and route waypoints. |

---

## 4. In-Theater Digital Twin Telemetry & 3D Tools

When entering the **Atlas 3D Mission Theater** (`T` hotkey or Header button):
1. **Real-Time Battery SOC Gauge:**
   Located in the lower-right `#jointMissionStudioPanel` drawer, displaying real-time battery percentage, remaining Watt-hours, and color-coded status bar (Green $\ge 35\%$, Amber $20-35\%$, Red $< 20\%$).
2. **Timeline Playback Scrubber:**
   Scrubbing the timeline slider dynamically simulates battery drawdown as the rover traverses across Jezero Crater.
3. **Interactive Raycast Spatial Inspector:**
   Clicking directly on any traverse ribbon opens the Spatial Inspector Card displaying:
   - Segment length and slope inclination
   - Rolling resistance work ($W_r$) in Joules
   - Gravitational climb work ($W_g$) in Joules
   - Segment electrical energy ($E_m$) in Watt-hours
   - Battery SOC margin at segment completion
