# MISSION 11 — HUMAN MARSWALK USER EXPERIENCE & COCKPIT AUDIT

**Project:** MarsWalk 2.0 / Project Atlas  
**Audit Standard:** NASA Human Integration Design Handbook (NASA/SP-2010-3407) & Flight Display Standards  
**Companion Documents:**
- [`MISSION_11_END_TO_END_EXECUTION_REPORT.md`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/docs/MISSION_11_END_TO_END_EXECUTION_REPORT.md)
- [`MISSION_11_HUMAN_EXPLORATION_GAP_ANALYSIS.md`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/docs/MISSION_11_HUMAN_EXPLORATION_GAP_ANALYSIS.md)

---

## 1. Executive Summary & Ergonomic Objective

An effective Mars mission operations workstation must provide **cognitive clarity under high-stress conditions**:
- Flight directors on Earth face communication latency (8 to 24 minutes one-way light-time).
- Astronauts on Mars face physical spacesuit encumbrance, helmet visor reflections, and lethal life-support limits.

This audit evaluates MarsWalk 2.0 strictly from the perspective of the **operator and field crew**: does the interface present critical hazards immediately, explain autonomous routing decisions clearly, and avoid cognitive overload?

---

## 2. Cockpit HUD Telemetry & Situational Awareness

The top HUD bar in MarsWalk provides high-contrast, real-time mission telemetry:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ SPEED: 2.00 km/h │ BATTERY: 84.2% │ DISTANCE: 5,420 m │ DTN CUSTODY: 14 BUNDLES  │
├──────────────────────────────────────────────────────────────────────────────────┤
│ STATUS: CONTINGENCY RECOVERY │ ACTIVE PROFILE: BALANCED │ VEHICLE: CREW EVA (0.38g)│
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Hazard Visibility & Color Coding
- **Slope Risk Zones:** Slopes are rendered on the terrain grid using an intuitive color ramp:
  - Green ($0^\circ$–$8^\circ$): Safe walking terrain; minimal metabolic strain.
  - Yellow ($8^\circ$–$15^\circ$): Moderate incline; elevated oxygen consumption and motor torque.
  - Orange ($15^\circ$–$25^\circ$): Severe incline; crew EVA threshold, impassable for wheeled rovers.
  - Red / Hatch ($> 25^\circ$): Lethal escarpment / cliff; hard barrier excluded from path search.
- **Dynamic Rockfall Footprint:** The Hawksbill Gap rockfall hazard is rendered as a distinct red translucent polygon with hazard radius indicators, ensuring operators immediately see *why* the standard corridor was closed.

---

## 3. Astrobiology Science Priorities & Sample Context

When an operator hovers over or selects a scientific waypoint, MarsWalk displays a structured **Science Context Card**:
- **Target Name & Sol:** e.g., *Wildcat Ridge Organic Mudstone* (Sol 520).
- **Astrobiology Significance:** Highlights specific chemical and geological detections (aromatics, sulfate minerals, carbonaceous molecules).
- **Instruments Represented:** Displays instrument pills (SHERLOC, PIXL, SuperCam, Mastcam-Z).
- **Associated Sample Tube:** Identifies the corresponding titanium core sample tube (e.g., tube *Hazelton*) and its deposition status at the Three Forks depot.
- **Science Score vs. Energy Trade-off:** Quantifies whether detouring to this target provides positive marginal science utility per watt-hour expended.

---

## 4. Multi-Persona Route Explainability Engine

One of MarsWalk's standout operational features is its **Route Explainer** (`src/marswalk/core/route_explainer.py`). Instead of presenting an opaque numeric cost, the system generates natural language rationales tailored to distinct mission roles:

1. **Professional Mode (Default Flight Director):**
   > *"Balanced route selected. Traverses 5,420m along the delta floor, avoiding the 18° scarp rim. Increases path distance by 8.4% to reduce peak wheel slip risk by 34.2%."*
2. **Concise Mode (Cockpit Audio / Astronaut Visor):**
   > *"Route: 5.4 km. Max slope 11.2°. Hawksbill corridor bypassed. ETA: 2h 42m."*
3. **Field Geologist Mode (Science Operations):**
   > *"Optimized for mudstone contact at Wildcat Ridge. Bypasses basalt floor to maximize dwell time on sulfate-rich lacustrine laminations."*
4. **Skeptical Flight Director Mode (Safety & Risk Review):**
   > *"Notice: Delta channel route exposes traverse to intermittent UHF relay shadow. DTN bundle custody buffer required for 1.8km."*

---

## 5. Non-Probabilistic Truth Disclosures in the UI

To prevent false confidence during human exploration planning, MarsWalk implements explicit UI indicators:
- **Data Source Pills:** Displayed alongside every metric (e.g., `USGS CTX 20m DTM`, `NASA PDS MEDA`, `MCD v6.2 GCM`).
- **Heuristic Indicators:** Whenever a simulation proxy is active (e.g., the Sol 89 dust storm $\tau$ spike), the badge displays `SIMULATED SCENARIO PROXY`.
- **Mandatory Safety Disclaimer:** Displayed persistently at the bottom of the navigation drawer:
  > *"MarsWalk is a research and decision-support simulation prototype. Modeled traverses are NOT certified operational flight paths for astronauts or flight hardware."*
