# Milestone 13E — Atlas Joint Mission Co-Design: Evaluator Decision Guide

**Product:** MarsWalk 2.0 / Project Atlas  
**Feature:** Joint Mission Design Studio (`#tabJointMissionStudio` & `#jointMissionStudioPanel`)  
**Audience:** Mission Planners, Science Evaluators, Conference Attendees  
**Document Version:** 1.0.0  
**Date:** 2026-10-31  

---

## 1. Introduction: Why Joint Co-Design Matters on Mars

Planning a surface traverse on Mars is fundamentally a coupled optimization problem. A rover traveling across Jezero Crater cannot rely on satellite communications at all times; direct line-of-sight to a base station or intermediate surface relays is essential for high-bandwidth science telemetry, real-time command uplinks, and astronaut safety monitoring.

When mission planning optimizes **only for mobility**, rovers naturally descend into canyons and depression floors where slope angles are low, but hills and scarp crests completely sever communication with the base.

When planning optimizes **only for communications**, rovers are forced along narrow ridge crests and promontories, incurring steep slope hazards, excessive Waligora metabolic energy expenditure, and mechanical drive wear.

The **Atlas Joint Mission Design Studio** solves this dilemma by presenting an interactive, terrain-aware multi-objective trade-off space where planners can explore:
- *"How many extra meters must we drive to avoid dropping an expensive relay tower?"*
- *"If we deploy one relay on the Delta Scarp promontory, how much blackout time do we eliminate?"*
- *"Which route configurations are mathematically non-dominated on the Pareto frontier?"*

---

## 2. 6-Step Guided Co-Design Workflow

Evaluators can access the studio by clicking the **⚙ Co-Design** tab in the Mission Cockpit or the **⚙ CO-DESIGN** button in the 3D Mission Theater HUD.

```
+--------------------------------------------------------------------------+
|  [1. Mission] -> [2. Mobility] -> [3. Comms] -> [4. Solve] -> [5. Pareto] -> [6. Promote]  |
+--------------------------------------------------------------------------+
```

### Step 1: Define Mission Requirements & Trade-Off Weights
1. **Origin:** Defaulted to `[117, 157]` (Octavia E. Butler Landing Base, elevation $-2548.2\text{ m}$).
2. **Target Destination:** Choose among curated Jezero science destinations:
   - `Delta Remnant / Three Forks [138, 114]` (Classic delta scarp traverse)
   - `Kodiak Butte Promontory [175, 122]` (High-relief isolated remnant)
   - `Séítah Carbonates Region [150, 140]` (Rough fractured terrain)
   - `Belva Crater Rim Lookout [95, 185]` (Impact crater boundary)
3. **Planning Horizon:** Select 1 Sol (24.6h / 88,775s) or Sortie EVA (4.0h / 14,400s).
4. **Objective Weight Sliders:**
   - Configure weights for Distance ($w_d$), Gap Duration ($w_g$), Relays ($w_r$), and Metabolic Energy ($w_e$).
   - Click one of the 4 quick preset pills:
     - `Balanced`: $w = (0.30, 0.35, 0.20, 0.15)$
     - `Mobility-First`: $w = (0.50, 0.15, 0.10, 0.25)$
     - `Comms-First`: $w = (0.15, 0.55, 0.20, 0.10)$
     - `Min-Relays`: $w = (0.25, 0.20, 0.45, 0.10)$
   - Click **`Σ = 1.0`** to automatically re-normalize weights.

### Step 2: Configure Mobility & Locomotion Systems
1. **Platform Selector:**
   - `Perseverance Rover Class`: $1025\text{ kg}$, $0.55\text{ m/s}$ nominal velocity.
   - `Crew EVA Suit`: $140\text{ kg}$, $1.0\text{ m/s}$, derated by Apollo Waligora metabolic cost.
2. **Slope Traversability Limits:**
   - Nominal Slope: $15.0^\circ$
   - Caution Ceiling: $20.0^\circ$
   - Critical Limit: $25.0^\circ$ (Impassable bedrock cliffs)

### Step 3: Configure Mars RelayNet Communications
1. **Transceiver Masts:**
   - Central Base Mast: $10.0\text{ m}$ ($Z = -2538.2\text{ m}$).
   - Rover Mobile Antenna: $2.5\text{ m}$.
   - Field Relay Tower Mast: $8.0\text{ m}$.
2. **Relay Budget ($K_{\text{max}}$):**
   - Choose between $0$ (Direct base only), $1$, $2$, $3$, or $4$ deployable towers.
3. **Candidate Promontories:**
   - Pre-screened pool of 12 topographic promontories on Jezero ridges.

### Step 4: Autonomous Co-Design Optimization Engine
1. Click **`[⚡ EXECUTE JOINT CO-DESIGN OPTIMIZATION]`**.
2. The solver generates candidate traverse variants, runs 3D geometric line-of-sight raycasting, optimizes relay placements via submodular greedy selection, and isolates the Pareto frontier.
3. Runtime is typically $< 850\text{ ms}$.

### Step 5: Interactive Pareto Frontier Studio
1. **Interactive 2D Scatter Plot:**
   - **X-Axis:** Total Traverse Distance ($m$) [shorter is better].
   - **Y-Axis:** Blackout Comms Gap Duration ($s$) [zero is better].
   - **Green Points & Dashed Frontier:** Non-dominated Pareto Rank 1 candidates.
   - **Grey Points:** Dominated alternatives.
   - **Cyan Reticle:** Currently selected configuration.
   - **Hover:** Reveals tooltip with Candidate ID, Strategy Name, Distance, Coverage %, Relays, and Blackout Gap.
   - **Click:** Selects candidate, synchronizes table, and updates 3D Mission Theater.
2. **Comparative Scorecard Table:**
   - Lists all candidate configurations side-by-side.
   - Columns: Candidate ID, Strategy Name, Pareto Rank, Distance, Coverage %, Relays, Max Blackout Gap, and Waligora Metabolic Work.
   - Click any row to preview in 3D.
3. **Decision Rationale Box:**
   - Displays physical trade-off attribution, Marginal Rate of Substitution (MRS), and terrain occlusion factors:
     * *Example:* `"Candidate JMC-01 (Scarp Crest Highway + 1 Relay): achieves 100.0% line-of-sight connectivity with 1 deployed surface relay. Marginal trade-off: +182m distance for 420s blackout reduction."*

### Step 6: Plan Selection, Promotion & Artifact Export
1. Review the selected configuration summary.
2. Click **`[🚀 PROMOTE TO ACTIVE CAMPAIGN PLAN]`** to deploy the route and relays to the Mission Control Cockpit.
3. Click **`Export Plan (JSON)`** to download Draft 2020-12 compliant JSON.
4. Click **`Download Dossier (MD)`** to generate a technical decision report.

---

## 3. 3D Mission Theater Visual Hierarchy

In the 3D Mission Theater, candidates are rendered directly onto the 20m USGS CTX Jezero Crater terrain drape:

| Visual Element | Color | Appearance | Meaning |
| :--- | :--- | :--- | :--- |
| **Selected Candidate** | Cyan (`#00e5ff`) | Solid 3D Tube with glow | The currently inspected co-design plan. |
| **Pareto Alternatives** | Violet (`#a855f7`) | Dashed ribbon | Non-dominated routes with different trade-off balances. |
| **Dominated Routes** | Slate Grey (`#64748b`) | Faint thin line | Sub-optimal traverses strictly worse in all objectives. |
| **Comms Blackout Gaps** | Crimson (`#ef4444`) | Pulsating thick tube | Trajectory segments where terrain severs all LOS. |
| **Deployed Relays** | Emerald (`#10b981`) | Lattice tower mast | Surface relay masts deployed on promontories. |
| **Carrier Beams** | Green / Cyan | Dynamic line | Real-time line-of-sight ray connecting unit to base/relay. |

---

## 4. Scientific Grounding & Disclaimers
- All elevations are sampled from USGS CTX 20m DTM (DOI: `10.5066/P906QQT8`).
- Planetary curvature uses the IAU 2000 Mars Spheroid ($R = 3,396,190\text{ m}$).
- Line-of-sight calculations evaluate 3D geometric optical clearance and do NOT certify RF link margins without an empirical propagation model.
- Traverses and communications networks are planning heuristics and are **NOT certified astronaut flight paths**.
