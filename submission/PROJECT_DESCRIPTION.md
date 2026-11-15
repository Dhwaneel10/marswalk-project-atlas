# MARSWALK 2.0 / PROJECT ATLAS
## Dual-Mode Human EVA & Robotic Rover Mission Operations Platform

**NASA International Space Apps Challenge 2026**  
**Category:** Planetary Exploration & Surface Operations  
**Release Version:** `v2.2.0-eva-qualified`  
**Repository:** `MarsWalk-Submission`  

---

### 1. Executive Summary

**MarsWalk 2.0 / Project Atlas** is an advanced surface mission operations and route-planning platform for Mars, engineered to support both **Human Astronaut Extravehicular Activities (EVAs)** and **Autonomous Robotic Rovers**. 

Unlike conventional planetary mission concepts that rely on synthetic terrain or speculative simulations, MarsWalk operates directly on **authoritative, real-world planetary data**: high-resolution Digital Elevation Models (DEMs) photogrammetrically processed by the USGS Astrogeology Science Center from Mars Reconnaissance Orbiter (MRO) HiRISE and CTX instruments, atmospheric pressure and dust opacity records from the Mars 2020 *Perseverance* Rover Environmental Dynamics Analyzer (MEDA) via the NASA Planetary Data System (PDS), and atmospheric circulation models from the European Mars Climate Database (LMD/MCD).

MarsWalk equips surface operations teams, flight controllers, and surface crew with a unified situational awareness canvas capable of:
1. **Astronaut Surface Excursions (Human EVA Mode):** Evaluating human metabolic energy expenditure, Portable Life Support System (PLSS) oxygen and thermal margins, asymmetric uphill/downhill slope friction, line-of-sight habitat communications, and dynamic contingency abort trajectories.
2. **Robotic Exploration (Rover Mode):** Planning high-efficiency traversals for the *Perseverance* rover across Jezero Crater, balancing slope tip hazards, wheel slip, direct solar illumination, and scientific sampling yield.
3. **Multi-Pillar Environmental Intelligence:** Simulating real Martian environmental dynamics—including diurnal thermal extremes, dust storm opacity encroaching on solar array yields, and orbital communication relay passes.
4. **Autonomous Operational Resilience:** Continuously monitoring mission telemetry, detecting traversal roadblocks, and computing verified return-to-base maneuvers without risking crew safety.

---

### 2. Dual-Mode Architecture

| Capability | Astronaut EVA Mode (Primary) | Robotic Rover Mode (Ground Truth) |
| :--- | :--- | :--- |
| **Primary Actor** | Human Astronaut in Extravehicular Mobility Unit (EMU) | Mars 2020 *Perseverance* Rover (1,025 kg) |
| **Max Traverse Slope** | $20^\circ$ nominal ($25^\circ$ maximum science limit) | $15^\circ$ nominal ($18^\circ$ maximum mechanical limit) |
| **Cost Formulation** | Metabolic energy rate (W), oxygen consumption rate (L/min), directional slope work | Wheel-soil sinkage, tip-over rollover margin, solar power generation |
| **Route Options** | Conservative, Science-Priority, Time-Efficient | Minimum Distance, Energy-Optimal, Maximum Science |
| **Operational Constraints**| PLSS 8-hr life support limit, $20\%$ emergency O2 reserve, habitat walkback limit | Power battery depth of discharge, thermal radioisotope decay, direct-to-Earth communication |
| **Display Mode** | Dual-track rendering (Amber Outbound, Cyan Return) + Visor HUD Telemetry | Single-track robotic path + Mastcam-Z ground truth overlays |

---

### 3. Core Capabilities & Five Operational Pillars

1. **Pillar 1: Terrain Intelligence**  
   Processes 1-meter USGS HiRISE stereogrammetric elevation models covering Jezero Crater (Western Delta, Séítah, Belva Crater). Computes instantaneous bidirectional slopes, surface roughness, cliff boundaries, and line-of-sight viewsheds.

2. **Pillar 2: Rover Ground Truth & Provenance**  
   Correlates all planned routes against actual *Perseverance* telemetry from Sol 0 through Sol 1000+, including real Mastcam-Z panorama observations, drill sample locations, and rock abrasion targets.

3. **Pillar 3: Environmental Intelligence**  
   Fuses real MEDA atmospheric telemetry (air/ground temperature, atmospheric pressure, relative humidity) with dust optical depth ($\tau$) records. Accurately simulates the Sol 89 dust storm event and its impact on visibility and solar yields.

4. **Pillar 4: Science-Driven Multi-Route Planning**  
   Computes three distinct route choices balancing scientific yield against physiological and consumable costs. Differentiates outbound travel from return-to-base travel to account for directional topography.

5. **Pillar 5: Autonomous Mission Resilience & Contingency Management**  
   Provides automated state machine progression (`NOMINAL` $\to$ `CAUTION` $\to$ `SAFE_HOLD` $\to$ `RETURN_TO_BASE` $\to$ `COMPLETED`). Instantly detects suit leaks, unexpected terrain obstacles, or dust storms and calculates emergency return corridors.

---

### 4. Technical Stack

- **Backend:** Python 3.10+, FastAPI / Asyncio HTTP Daemon, NumPy, SciPy, Rasterio, Pytest.
- **Frontend:** Pure Vanilla JavaScript (ES6+), HTML5 Canvas, WebGL, Three.js 3D Terrain Engine, CSS3 Grid & Flexbox (zero fragile external npm dependencies).
- **Automated QA:** Pytest test harness, Chrome DevTools Protocol (CDP) automated browser acceptance test suite.
- **Platform Support:** Linux (Ubuntu 20.04/22.04 LTS), macOS, Windows (WSL2/PowerShell).

---

### 5. Quick Start (Evaluation Launch)

```bash
# Clone the repository
git clone https://github.com/NASA-SpaceApps-2026/MarsWalk-Submission.git
cd MarsWalk-Submission

# Run setup (creates venv and installs dependencies)
./scripts/setup_atlas.sh

# Launch the interactive mission platform
./scripts/start_atlas.sh --port 3000

# Open in browser: http://127.0.0.1:3000
```
