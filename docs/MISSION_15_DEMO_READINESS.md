# MISSION 15: THREE-MINUTE DEMONSTRATION READINESS GUIDE
## MarsWalk 2.0 / Project Atlas | Evaluator Showcase Playbook

**Project:** MarsWalk 2.0 / Project Atlas  
**Branch:** `mission-15-visual-polish`  
**Target Duration:** Exactly 3 Minutes (180 Seconds)  
**Demonstration Script:** `scripts/audit_mission15_demonstration_browser.py`  
**Execution Timestamp:** 2026-11-15T18:12:00+05:30  
**Status:** **DEMONSTRATION QUALIFIED (11 / 11 Stages Verified, Zero Flashing, Smooth Transitions)**

---

### 1. Demonstration Concept & Narrative Arc

MarsWalk tells a unified, defensible scientific story:
$$\text{REAL MARS OBSERVATIONS} \longrightarrow \text{TERRAIN INTELLIGENCE} \longrightarrow \text{ASTRONAUT EVA PLANNING} \longrightarrow \text{LIFE-SUPPORT BUDGETING} \longrightarrow \text{CONTINGENCY RESILIENCE} \longrightarrow \text{ROBOTIC COOPERATION}$$

The 3-minute presentation is structured to capture immediate attention with the Ascend-inspired dark-space aesthetics, prove uncompromising scientific provenance, demonstrate human surface excursion trade-offs, execute an emergency abort recovery, and show rover-astronaut joint operations.

---

### 2. Minute-by-Minute Presentation Timeline

```
[00:00 - 00:30]  STAGE 1: CINEMATIC HERO & EPISTEMIC TAXONOMY
                 • Hero headline & ambient starfield canvas
                 • 3-tier data provenance (Measured Archives, Derived Products, Simulation Models)
                 • Click: [ENTER ASTRONAUT EVA MODE]

[00:30 - 01:00]  STAGE 2: TERRAIN INTELLIGENCE & SCIENCE TARGET SELECTION
                 • Transition to 3D Jezero Crater workstation (ESRI:103885 coordinates)
                 • USGS CTX 20m DTM + 1m HiRISE slope variance
                 • Check science outcrops (Delta Scarp, Kodiak Mesa)

[01:00 - 01:45]  STAGE 3: CANDIDATE HUMAN EVA ROUTES & DUAL-TRACK TRAVERSAL
                 • Click: [PLAN 3 ASTRONAUT EVA ROUTES]
                 • Compare Conservative (Lowest Slope), Science-Priority, Time-Efficient
                 • Highlight dual-track polylines: Amber outbound, Cyan return (+2.5m Z-delta)

[01:45 - 02:15]  STAGE 4: VISOR HUD TELEMETRY & PLSS OXYGEN PROGRESS GAUGE
                 • Inspect Astronaut Visor HUD in top-right
                 • Point out 77% O2 progress bar & 20% Emergency Reserve Barrier (120 L gate)
                 • Review biophysical expenditure: 882 kcal, return ETA, usable margin (342 L)
                 • Non-safety disclosure prominence: Research Decision-Support Model

[02:15 - 02:45]  STAGE 5: CONTINGENCY INJECTION & AUTONOMOUS EMERGENCY ABORT
                 • Trigger: Dust Storm Encroachment (MEDA tau >= 3.0)
                 • Immediate mission state transition: NOMINAL -> RETURN_TO_BASE
                 • Emergency return route drawn; advisory banner displayed
                 • Click: [x RESET] to clear contingency and demonstrate state recovery

[02:45 - 03:00]  STAGE 6: ROBOTIC ROVER MODE & FIVE-PILLAR PRESERVATION
                 • Click: [Rover] quick nav pill -> status badge: ROVER MISSION ACTIVE
                 • Visor HUD automatically isolates and hides
                 • Highlight Perseverance Sols 0-1000+ ground truth & 5-pillar architecture
```

---

### 3. Stage-by-Stage Operator Directives

#### 3.1 Stage 1: Planetary Landing & Truth Taxonomy (0:00 – 0:30)
- **Visual Focus:** [m15_01_hero_cinematic_polished.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_15/browser_qa/m15_01_hero_cinematic_polished.png)
- **Spoken Narrative:**
  > *"Welcome to MarsWalk 2.0. Rather than treating Mars as a decorative game environment, MarsWalk is an aerospace decision-support workstation combining authentic NASA and USGS observations with human-first mission operations. Notice our epistemic taxonomy: we strictly separate real measured PDS archives from derived slope matrices and simulation models."*
- **Action:** Click the primary glowing amber button: `ENTER ASTRONAUT EVA MODE`.

#### 3.2 Stage 2: 3D Terrain & Science Selection (0:30 – 1:00)
- **Visual Focus:** [m15_02_eva_mode_planning.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_15/browser_qa/m15_02_eva_mode_planning.png)
- **Spoken Narrative:**
  > *"We land directly in Jezero Crater, mapped on the IAU 2000 Mars Spheroid using authentic USGS CTX 20m elevation data. In the EVA Planning Studio, our astronaut base is anchored at Octavia E. Butler Landing. We select candidate astrobiology targets along the ancient river delta."*
- **Action:** Verify science targets are selected (`Delta Scarp` and `Kodiak Mesa`), then click `PLAN 3 ASTRONAUT EVA ROUTES`.

#### 3.3 Stage 3: Three Route Alternatives & Dual Tracks (1:00 – 1:45)
- **Visual Focus:** [m15_03_eva_3routes_comparison.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_15/browser_qa/m15_03_eva_3routes_comparison.png)
- **Spoken Narrative:**
  > *"The system evaluates human biomechanical cost functions and generates three distinct route profiles: Conservative (lowest slope, strictly under 15 degrees), Science-Priority, and Time-Efficient. Notice the 3D canvas: we render dual tracks—an amber outbound traverse and a high-contrast cyan return path, offset by 2.5 meters in elevation to prevent z-fighting."*
- **Action:** Click on `Science-Priority` card; observe instant route update.

#### 3.4 Stage 4: Visor HUD & Life Support Budgeting (1:45 – 2:15)
- **Visual Focus:** [m15_04_visor_hud_plss_gauge_nominal.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_15/browser_qa/m15_04_visor_hud_plss_gauge_nominal.png)
- **Spoken Narrative:**
  > *"In the upper right, our Astronaut Visor HUD displays live Portable Life Support System (PLSS) telemetry. The animated gauge indicates 79.8% oxygen remaining, with an explicit redline marker at 20% representing NASA's mandatory abort gate. Notice our strict non-safety disclosure: all outputs are planning models, never certified flight operations."*
- **Action:** Point out the 8 micro-cells: Elapsed Time, Remaining Time, O2 Supply, Metabolic Burn, Distance to Base, Return ETA, Atmospheric Tau, and Radiation.

#### 3.5 Stage 5: Contingency Ingestion & Emergency Abort (2:15 – 2:45)
- **Visual Focus:** [m15_05_eva_contingency_emergency_return.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_15/browser_qa/m15_05_eva_contingency_emergency_return.png) and [m15_06_contingency_reset_nominal.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_15/browser_qa/m15_06_contingency_reset_nominal.png)
- **Spoken Narrative:**
  > *"Now we inject a simulated environmental disruption: a sudden dust storm encroachment with optical depth tau >= 3.0 from MEDA weather models. The platform immediately transitions the mission state to RETURN_TO_BASE, calculates the fastest walkback corridor, and displays an emergency advisory. With one click on RESET, the platform cleanly restores nominal state."*
- **Action:** Click `Dust Storm Encroachment`, show advisory, then click `× RESET`.

#### 3.6 Stage 6: Robotic Rover Mode & 5 Pillars (2:45 – 3:00)
- **Visual Focus:** [m15_07_rover_mode_preserved.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_15/browser_qa/m15_07_rover_mode_preserved.png)
- **Spoken Narrative:**
  > *"Finally, we seamlessly switch to Robotic Rover Mode. The Visor HUD automatically isolates to prevent human telemetry confusion, and Perseverance's complete 33.2 km ground-truth traverse across Sols 0 to 1000+ is restored. MarsWalk proves that human exploration and robotic autonomy are complementary pillars of the Martian frontier."*
- **Action:** Click `Rover` quick-nav pill; show `ROVER MISSION ACTIVE` badge.

---

### 4. Automated Reproduction Command

Evaluators or judges can execute the exact demonstration sequence unattended at any time:

```bash
# Start local server
./scripts/start_atlas.sh --port 3000 --no-browser

# Execute full automated demonstration & capture 10 screenshots
.venv/bin/python scripts/audit_mission15_demonstration_browser.py 3000
```
