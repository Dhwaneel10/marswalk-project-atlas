# Mission 17: Product Scope & Release Boundaries

**Project:** MarsWalk 2.0 / Project Atlas  
**Release Tag:** `v2.6.0-competition-release`  
**Git Branch:** `mission-17-competition-readiness`  
**Target Environment:** NASA International Space Apps Challenge 2026  
**Primary Workstation Location:** Jezero Crater Study Boundary ($5.0 \times 5.0\text{ km}$)  

---

## 1. Executive Product Definition

MarsWalk 2.0 is an authentic planetary mission operations and human-first extravehicular activity (EVA) planning platform developed for the NASA Space Apps Challenge. Grounded in genuine NASA Planetary Data System (PDS) and USGS Astrogeology remote sensing records, MarsWalk enables mission controllers, planetary scientists, and astronaut crew to plan, evaluate, and stress-test surface traverses across Martian terrain.

In Mission 17, the application has been simplified and focused for competition release:
1. **Primary Actor:** Human Astronaut crew on surface EVA sorties.
2. **Secondary Actor:** Perseverance robotic rover exploring historical and autonomous science corridors.
3. **Sole Supported Surface Workstation:** Jezero Crater ($18.44^\circ\text{N}, 77.45^\circ\text{E}$), backed by authentic 20m USGS CTX Digital Elevation Models and 1m HiRISE micro-hazard digital terrain maps.
4. **Clean Information Architecture:** Elimination of obstructing experimental drawers from the landing interface and clear demarcation between production workstation capabilities and deferred experimental engineering labs.

---

## 2. Core Operational Capabilities (Production Scope)

### 2.1 Capability 1: Human-First Astronaut EVA Sorties
- **Operational Model:** Extravehicular activity excursion planning for a suited astronaut ($M_{\text{total}} = 140\text{ kg}$: 80 kg crew + 60 kg suit/PLSS) on the Martian surface ($g_{\text{Mars}} = 3.72076\text{ m/s}^2$).
- **Metabolic Cost Function:** Minetti-Margaria asymmetric biomechanical metabolic energy expenditure:
  $$E_{\text{metabolic}} = d \cdot \left(2.8 + 0.12 \cdot \theta + 0.008 \cdot \theta^2\right)\quad [\text{J/kg}]$$
- **Walking Speed Curve:** Slope-dependent speed model peaking at nominal flat ground speed of $1.10\text{ m/s}$ ($3.96\text{ km/h}$) and decelerating sharply on steep inclines to $0.25\text{ m/s}$ ($0.90\text{ km/h}$).
- **PLSS Life-Support Consumables:**
  - Standard 8.0-hour EVA sortie duration ($28,800\text{ s}$).
  - Usable oxygen budget of $600\text{ L}$ ($2.08\text{ g/s}$ consumption baseline at moderate metabolic effort).
  - Strict $20\%$ ($120\text{ L}$ / $96\text{ min}$) mandatory reserve safety barrier. Sortie planning rejects or warns when oxygen reserve margins dip below $20\%$.
- **Route Visualization:** Dual-polyline rendering:
  - Outbound traverse: High-contrast amber (`#f59e0b`) or profile-specific hue.
  - Return-to-base traverse: High-contrast cyan (`#38bdf8`) offset vertically by $+2.5\text{ m}$ to eliminate z-fighting on retraced paths.

### 2.2 Capability 2: Perseverance Robotic Rover Exploration
- **Operational Model:** Perseverance rover ground truth ($M_{\text{rover}} = 1025\text{ kg}$, 6-wheel rocker-bogie mobility chassis).
- **Drive Speed Model:** Deterministic $0.035\text{ m/s}$ ($126\text{ m/h}$) drive window speed model derived from NASA JPL tactical driving logs.
- **PDS Historical Traverse:** 577 archived tactical drive sites spanning Sols 13 through 1896, totaling $33.2\text{ km}$ of authentic Martian surface exploration.
- **Sample Depot:** 10 hermetically sealed titanium sample tubes cached at Three Forks depot.

### 2.3 Capability 3: Multi-Scale Terrain Intelligence
- **Regional Foundation:** USGS Jezero CTX 20m Digital Terrain Model ($250 \times 250$ raster grid, $5.0 \times 5.0\text{ km}$, elevation $-2623.8\text{ m}$ to $-2445.0\text{ m}$).
- **Local Micro-Hazards:** 1m/pixel HiRISE elevation model covering the Hawksbill Gap delta scarp ascent corridor ($600 \times 600\text{ m}$).
- **Slope Derivation:** Horn $3 \times 3$ finite-difference gradient operator with continuous slope classification (Gentle $<5^\circ$, Moderate $5^\circ$–$15^\circ$, Steep $>15^\circ$, Impassable $>16^\circ$).

### 2.4 Capability 4: Astrobiology Science Targets
- **Catalog:** 12 georeferenced Jezero delta and crater floor outcrops (Belva Crater Rim, Kodiak Mesa, Three Forks, Séítah, Skinner Ridge, Enchanted Lake, Berea, Wildcat Ridge, etc.).
- **Science Evaluation:** Multi-stop Traveling Salesperson Problem (TSP) with exact and 2-Opt solvers, Shannon entropy reduction, and Expected Information Gain (EIG).

### 2.5 Capability 5: In-Situ Martian Environmental Digital Twin
- **Atmospheric Provenance:** NASA Mars 2020 MEDA sensor measurements archived in PDS Atmospheres Node.
- **Telemetry Replay:** Diurnal pressure swing ($690$–$775\text{ Pa}$), diurnal temperature cycle ($-88.4^\circ\text{C}$ to $-11.2^\circ\text{C}$), and atmospheric optical depth dust storm contingency ($\tau = 1.5$ up to $\tau = 4.10$).

---

## 3. Product Boundaries & Non-Supported Content

To guarantee 100% reliability, reproducibility, and clarity for competition judges, the following boundaries are formally enforced:

| Dimension | Supported in Competition Release | Explicitly Deferred / Non-Operational |
|---|---|---|
| **Planetary Target** | Mars (IAU 2000 Sphere, $R=3,396,190\text{ m}$) | Earth, Moon, Europa, Titan |
| **Surface Workstation** | **Jezero Crater Only** ($5.0 \times 5.0\text{ km}$) | Gale Crater, Gusev Crater, Valles Marineris (Global gazetteer search only) |
| **Terrain Elevation** | Authentic USGS CTX 20m & HiRISE 1m DTMs | Synthetic or procedural terrain generators |
| **Primary Workstations** | 5 Verified Views: Astronaut EVA, Rover, Terrain, Science, Environment | Unverified secondary modules |
| **Drawer Interfaces** | Clean on-demand modals | Autoloading persistent desktop drawers |
| **Network & DTN Twin** | Heuristic simulation in Extended Labs | Live RF telemetry claims |
| **Human Safety Claims** | **NEVER** called operationally safe for astronauts | Certified flight clearance claims |

---

## 4. Scientific Disclosures & Guardrails

> [!CAUTION]
> **MANDATORY RESEARCH SAFETY DISCLOSURE:**
> MarsWalk 2.0 / Project Atlas is an academic and engineering decision-support simulation prototype developed for the NASA Space Apps Challenge.
>
> All calculated traverses, metabolic rates, oxygen consumption figures, walking speeds, and return safety margins represent mathematical heuristics derived from published planetary science literature and remote sensing datasets.
>
> **Under no circumstances should any route, speed, consumable estimate, or contingency plan generated by MarsWalk be characterized as "flight-certified" or "operationally safe for astronauts."** Real astronaut planetary excursions require exhaustive physiological monitoring, ground-in-the-loop flight medicine oversight, spacesuit sensor telemetry, and flight qualification protocols.
