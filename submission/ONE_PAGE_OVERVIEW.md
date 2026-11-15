# ONE-PAGE EXECUTIVE OVERVIEW
## MarsWalk 2.0 / Project Atlas

**NASA International Space Apps Challenge 2026**  
**Dual-Mode Planetary Surface Mission Operations Platform**  
**Release:** `v2.2.0-eva-qualified` | **Repository:** `MarsWalk-Submission`  

---

### Project Snapshot

| Attribute | Details |
| :--- | :--- |
| **Mission Objective** | Enable human astronauts and robotic rovers to safely plan, evaluate, and navigate surface excursions across real Martian terrain using authentic NASA planetary datasets. |
| **Operational Modes** | **Astronaut EVA Mode** (Primary human life-support workflow) & **Robotic Rover Mode** (Perseverance ground truth). |
| **Authoritative Data** | USGS 1m HiRISE DEM, CTX 20m Mosaic, NASA PDS MEDA Weather (Sol 0-1000+), Mars Climate Database v6.1. |
| **Key Innovations** | Asymmetric bidirectional slope modeling, PLSS oxygen/metabolic budgeting, MEDA $\tau$ contingency triggers, dual-track 3D polyline rendering. |
| **Verification Gate** | 100% test pass rate across 357 test cases, 10/10 adversarial qualification suites passed, automated CDP browser acceptance verified. |

---

### Core Architecture & Operational Workflow

```
+---------------------------------------------------------------------------------------------------------+
|                                    ASTRONAUT SURFACE EXCURSION WORKFLOW                                 |
+---------------------------------------------------------------------------------------------------------+
|  [ 1. REAL TOPOGRAPHY ]    ->  [ 2. BIOPHYSICAL A* ]      ->  [ 3. PLSS CONSUMABLES ] ->  [ 4. DECISION ] |
|  USGS 1m HiRISE DEM            Disaggregated Outbound /       Continuous O2 Integration    Visor HUD     |
|  Jezero Fan Delta & Séítah     Return Directional Gradients   20% Emergency Reserve Gate   3 Route Choice|
+---------------------------------------------------------------------------------------------------------+
                                                     |
                                     [ CONTINGENCY RESILIENCE ]
                           MEDA Dust Optical Depth (Tau >= 3.0) Trigger
                           Automated State Transition: NOMINAL -> CAUTION -> RETURN_TO_BASE
                           Instantaneous Alternate Emergency Escape Corridor
```

---

### Key Capabilities at a Glance

1. **Dual-Mode Exploration:** Toggle seamlessly between human surface excursions and robotic rover drives without reloading or cross-contaminating mission state.
2. **Directional Slope Physics:** Independently calculates the outbound journey and return-to-base journey, preventing dangerous uphill fatigue on the return leg.
3. **Astronaut Visor HUD:** Ergononically displays live Portable Life Support System (PLSS) indicators: usable oxygen volume ($600\text{ L}$ capacity), metabolic calorie expenditure, and reserve margins.
4. **Autonomous Emergency Resilience:** Reacts dynamically to rising atmospheric dust opacity ($\tau \ge 3.0$), aborting non-essential operations and routing the astronaut along safe escape corridors.
5. **Scientific Rigor & Ethics:** Distinguishes measured planetary observations from model heuristics; prominently warns that models are decision-support tools and not operational flight certifications.

---

### 30-Second Quick Start

```bash
git clone https://github.com/NASA-SpaceApps-2026/MarsWalk-Submission.git
cd MarsWalk-Submission
./scripts/setup_atlas.sh && ./scripts/start_atlas.sh --port 3000
# Open http://127.0.0.1:3000 in Chrome/Firefox/Safari
```
