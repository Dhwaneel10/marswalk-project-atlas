# MISSION 16B: 18-STEP JEZERO WORKFLOW DEMONSTRATION SCRIPT

**Project:** MarsWalk 2.0 / Project Atlas  
**Target Release:** `v2.5.0-jezero-verified`  
**Purpose:** Evaluator, Judge, and Mission Director Guided Live Walkthrough  
**Test Automation Script:** [scripts/test_jezero_workflow.py](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/scripts/test_jezero_workflow.py)  
**Report Artifact:** [outputs/mission_16/workflow/jezero_workflow_report.json](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_16/workflow/jezero_workflow_report.json)  
**Verification Status:** 18/18 STEPS VERIFIED & PASSED (100%)  

---

## Instructions for Demonstrator

Follow this chronological presentation script during evaluator evaluations, live reviews, or video demonstrations. Each step includes the exact user interface click action, spoken explanation, expected telemetry output, and reference screenshot evidence.

> [!IMPORTANT]
> **MANDATORY SCIENTIFIC INTEGRITY RULE**  
> Always distinguish measured remote sensing data (USGS 20m CTX Stereo DTM, NASA PDS Mars 2020) from derived quantities and heuristic models (Minetti metabolic equations). Under no circumstances claim that a modeled route is operationally safe for astronauts.

---

## The 18-Step Guided Workflow

### Step 1: Open Homepage
- **UI Action:** Open browser to `http://127.0.0.1:3000/`.
- **What to Say:**  
  *"Welcome to MarsWalk 2.0, developed for the NASA Space Apps Challenge. MarsWalk transforms planetary exploration planning by providing genuine data-grounded situational awareness for human astronaut EVAs and robotic rovers."*
- **Visual Evidence:** [outputs/mission_16/workflow/wf_01_homepage.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_16/workflow/wf_01_homepage.png)

---

### Step 2: Understand Product from Hero Section
- **UI Action:** Hover over the epistemic truth pills and the hero headline.
- **What to Say:**  
  *"Notice our primary epistemic truth pills: IAU 2000 Mars Volumetric Mean Sphere, USGS 20-meter CTX elevation data, and authentic PDS MEDA meteorological records from Sol 89. We never invent synthetic terrain observations. On the right, our Operational Mission Hub confirms Jezero Crater as our active 3D workstation."*
- **Expected Metrics:** Headline reads *"EXPLORE MARS. PLAN THE HUMAN EXPEDITION."*

---

### Step 3: Enter Astronaut EVA Mode
- **UI Action:** Click the radiant amber button: `⚡ ENTER ASTRONAUT EVA MODE` (`#btnLandingEnterEVA`).
- **What to Say:**  
  *"Let's transition directly into mission operations. MarsWalk loads the authentic 3D terrain canvas and immediately configures the Astronaut EVA Planning Studio in our mission inspector."*
- **Visual Evidence:** [outputs/mission_16/workflow/wf_02_enter_astronaut_eva.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_16/workflow/wf_02_enter_astronaut_eva.png)

---

### Step 4: Confirm Jezero Crater Active Workstation
- **UI Action:** Inspect the top telemetry bar and the Location Dossier.
- **What to Say:**  
  *"We confirm that our active workstation is Jezero Crater (18.44°N, 77.45°E). This release intentionally focuses on Jezero Crater, where we have authentic ground truth from the Mars 2020 Perseverance mission."*
- **Expected Metrics:** Workstation title confirms `JEZERO CRATER`.

---

### Step 5: Wait for Actual Terrain Data to Load
- **UI Action:** Observe the 3D surface rendering and telemetry resolution indicator.
- **What to Say:**  
  *"The 250×250 elevation grid has finished streaming. Each cell corresponds to a nominal 20-meter ground spacing, accurately reflecting the steep scarp walls of the ancient Jezero river delta."*
- **Expected Metrics:** Elevation range spans approximately $-2,650\text{ m}$ to $-2,400\text{ m}$.

---

### Step 6: Inspect Terrain Environment
- **UI Action:** Orbit the camera across the Jezero delta front (`wf_03_terrain_environment.png`).
- **What to Say:**  
  *"Notice the terrain contrast between the flat crater floor where Octavia E. Butler Base Camp is situated and the jagged, erosion-carved delta scarps. These slopes represent critical biomechanical challenges for space-suited astronauts."*
- **Visual Evidence:** [outputs/mission_16/workflow/wf_03_terrain_environment.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_16/workflow/wf_03_terrain_environment.png)

---

### Step 7: Select Supported Science Targets
- **UI Action:** Under "Science Outcrops to Sample", select the top 4 delta outcrop targets:
  1. *Delta Front Outcrop* (Clay-Bearing Sediments, +85 pts)
  2. *Crater Floor Stratum* (Basaltic Igneous Pavement, +70 pts)
  3. *Séítah Carbonate Layer* (Astrobiology Target, +90 pts)
  4. *Kodiak Butte Stratigraphy* (Delta Remnant, +80 pts)
- **What to Say:**  
  *"We select four authentic science targets identified during the Perseverance campaign. Notice that each target carries genuine geological classifications and science priority ratings."*
- **Expected Metrics:** Target badge displays `4 SELECTED`.
- **Visual Evidence:** [outputs/mission_16/workflow/wf_04_science_targets_selected.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_16/workflow/wf_04_science_targets_selected.png)

---

### Step 8: Plan Multi-Criteria EVA Routes
- **UI Action:** Click `⚡ PLAN 3 ASTRONAUT EVA ROUTES` (`#btnPlanEVARoutes`).
- **What to Say:**  
  *"MarsWalk now invokes our asymmetric A* heuristic solver. In less than half a second, it computes three distinct route options: Conservative, Science-First, and Time-Efficient, balancing slope impedance against metabolic burn."*
- **Expected Metrics:** 3 route cards rendered under `.eva-route-card`.
- **Visual Evidence:** [outputs/mission_16/workflow/wf_05_eva_routes_planned.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_16/workflow/wf_05_eva_routes_planned.png)

---

### Step 9: Compare Available Route Strategies
- **UI Action:** Click through the 3 route cards:
  1. Click `Conservative` (Green badge: `LOWEST SLOPE • <=15° BIOMECHANICS`).
  2. Click `Science-First` (`wf_06_route_science_first.png`).
  3. Click `Time-Efficient` (`wf_07_route_time_efficient.png`).
- **What to Say:**  
  *"Let's compare the tradeoffs. The Conservative route adheres strictly to slopes under 15 degrees to preserve astronaut postural stability. The Science-First route maximizes delta outcrop dwell time. The Time-Efficient route optimizes for the most direct traversal."*
- **Visual Evidence:** 
  - [outputs/mission_16/workflow/wf_06_route_science_first.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_16/workflow/wf_06_route_science_first.png)
  - [outputs/mission_16/workflow/wf_07_route_time_efficient.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_16/workflow/wf_07_route_time_efficient.png)

---

### Step 10: Inspect Outbound and Return Paths
- **UI Action:** Select the Conservative route card and inspect the 3D scene path.
- **What to Say:**  
  *"Notice our dual-path rendering: the solid cyan line indicates the outbound science leg, while the dashed amber line indicates the return corridor back to safe haven. The return path accounts for astronaut fatigue and down-slope deceleration."*
- **Expected Metrics:** Outbound walk: $\sim 1,200\text{ m}$; Return walk: $\sim 1,200\text{ m}$; Total traverse: $\sim 2.4\text{ km}$.

---

### Step 11: Inspect Estimated Resource Consumption (Visor HUD)
- **UI Action:** Inspect the Astronaut EVA Visor HUD overlay (`wf_08_visor_hud_resources.png`).
- **What to Say:**  
  *"Our Visor HUD models the Portable Life Support System (PLSS) consumable envelope. For an 8-hour nominal capacity of 600 liters of oxygen, the Conservative sortie consumes approximately 323 liters, leaving 276.6 liters remaining (46.1%)."*
- **Expected Metrics:**  
  - $O_2$ Supply: `276.6 L (46.1%)`  
  - Usable Margin: `157 L USABLE (ABOVE 20% RESERVE)`  
  - Metabolic Burn: `~1,480 kcal`  
  - Base Distance: `~1,200 m`
- **Visual Evidence:** [outputs/mission_16/workflow/wf_08_visor_hud_resources.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_16/workflow/wf_08_visor_hud_resources.png)

---

### Step 12: Review Reserve Barrier & Operational Limitations
- **UI Action:** Highlight the mandatory reserve gate on the HUD and the bottom disclaimer.
- **What to Say:**  
  *"Notice our mandatory 20% oxygen reserve barrier (120 liters). The planner refuses to allocate any portion of the emergency reserve to planned science stops. And as always, our HUD reminds operators: 'RESEARCH DECISION-SUPPORT MODEL • NOT OPERATIONAL SAFETY FLIGHT CERTIFIED'."*

---

### Step 13: Trigger Supported Contingency Scenario (Dust Storm)
- **UI Action:** In the Contingency Simulation panel, click `Simulated Dust Event` (`.btn-eva-contingency-trigger[data-contingency="dust_event"]`).
- **What to Say:**  
  *"Now we test autonomous mission resilience. We simulate a sudden regional dust storm event modeled directly on MEDA Sol 89 data, with atmospheric optical depth rising to $\tau = 1.5$."*
- **Expected Metrics:**  
  - Mission State transitions from `NOMINAL` to `CAUTION` (amber badge).  
  - Advisory text: `[CAUTION] Moderate dust opacity event detected (optical depth tau = 1.5). Atmospheric contrast degraded. Visor contrast enhancement active.`
- **Visual Evidence:** [outputs/mission_16/workflow/wf_09_contingency_triggered.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_16/workflow/wf_09_contingency_triggered.png)

---

### Step 14: Inspect Resulting State & Return Logic
- **UI Action:** Inspect the red emergency abort path drawn on the 3D surface.
- **What to Say:**  
  *"The system immediately computes the fastest emergency egress corridor directly back to Octavia E. Butler Base Camp, bypassing remaining science outcrops to minimize environmental exposure."*

---

### Step 15: Reset Contingency to Nominal
- **UI Action:** Click `RESET` (`#btnEvaContingencyReset`).
- **What to Say:**  
  *"We clear the contingency. The mission state returns to NOMINAL, restoring the planned three-route baseline."*
- **Expected Metrics:** Mission state badge resets to green `NOMINAL`.
- **Visual Evidence:** [outputs/mission_16/workflow/wf_10_contingency_reset.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_16/workflow/wf_10_contingency_reset.png)

---

### Step 16: Return to Homepage Overview
- **UI Action:** Click the top-left brand logo or execute `showLandingPage()`.
- **What to Say:**  
  *"We return to the homepage to demonstrate dual-mode flexibility."*
- **Visual Evidence:** [outputs/mission_16/workflow/wf_11_returned_homepage.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_16/workflow/wf_11_returned_homepage.png)

---

### Step 17: Enter Robotic Rover Mode
- **UI Action:** Click the `ROVER MISSION MODE` toggle (`#btnModeRoboticRover`).
- **What to Say:**  
  *"Now we switch into Robotic Rover Mode. Notice how the telemetry calculations adjust immediately. Instead of human walking speeds of 2 to 4 km/h, the system switches to the 0.035 m/s terramechanical drive model of Perseverance, displaying the real 33.2 km ground truth traverse recorded across Sols 0 to 1000+."*
- **Expected Metrics:** Rover Mode pill becomes `active`, telemetry updates to `Perseverance 0.035 m/s Model`.
- **Visual Evidence:** [outputs/mission_16/workflow/wf_12_rover_mode.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_16/workflow/wf_12_rover_mode.png)

---

### Step 18: Return to Main Interface Ready State
- **UI Action:** Switch inspector tab to `tabPlan` (`#inspectorTabPlan`).
- **What to Say:**  
  *"MarsWalk 2.0 stands fully validated, responsive across all viewports, reproducible in any clean-room environment, and scientifically grounded in genuine Martian observations. Thank you."*
- **Visual Evidence:** [outputs/mission_16/workflow/wf_13_main_interface_ready.png](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/mission_16/workflow/wf_13_main_interface_ready.png)
