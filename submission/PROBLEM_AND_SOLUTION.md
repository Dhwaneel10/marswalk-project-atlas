# PROBLEM & SOLUTION STATEMENT
## Mars Surface Excursion Planning & Human-Machine Autonomy

**NASA International Space Apps Challenge 2026**  
**Project:** MarsWalk 2.0 / Project Atlas  

---

### 1. The Planetary Surface Problem

Planning human surface excursions (EVAs) and robotic rover operations on Mars presents a formidable combination of physical, environmental, and operational challenges:

1. **Extreme and Treacherous Topography:**  
   Martian impact craters, river deltas, and sand dune fields feature steep scarps, boulder fields, and unconsolidated regolith. A route that looks flat on low-resolution global satellite imagery can easily contain lethal 30-degree slopes or treacherous sand traps (such as the Séítah region in Jezero Crater) that can trap a rover or cause an astronaut in a pressurized suit to slide and rupture life-support umbilical connectors.

2. **Life-Support & Consumable Limits:**  
   Unlike robotic rovers that can remain stationary for sols waiting for ground instruction, an astronaut EVA is strictly limited by the Portable Life Support System (PLSS) consumable capacity: typically 6 to 8 hours of usable oxygen ($O_2$), limited battery power for heating, and strict $CO_2$ scrubber absorption limits. Every meter traversed, every degree of incline climbed, and every minute spent collecting core samples expends unrecoverable physiological energy and consumable volume.

3. **Directional Slope Energy Asymmetry:**  
   Traversing a slope uphill requires immense mechanical and cardiovascular exertion against Martian gravity ($g = 3.721\text{ m/s}^2$). Traversing that same slope downhill requires eccentric muscular braking. Merely computing a symmetric "round-trip distance" dramatically underestimates return metabolic strain and walk times when traversing undulating terrain.

4. **Communications Latency & Deep-Space Isolation:**  
   One-way light-time communication latency between Mars and Earth ranges from 3 to 22 minutes. In an emergency—such as an approaching regional dust storm, sudden suit depressurization, or a blocked return path—astronauts and surface rovers cannot wait 40 minutes for Mission Control on Earth to calculate a safe escape route. Immediate, on-site, edge-computed tactical decisions are vital.

5. **The Synthetic Simulation Pitfall:**  
   Most student and conceptual planning tools fabricate fictitious terrain or present synthetic, idealized game maps. When applied to real planetary operations, such systems fail because they ignore actual sensor noise, DEM resolution artifacts, coordinate reference distortions, and true atmospheric variability.

---

### 2. The MarsWalk Solution

**MarsWalk 2.0 / Project Atlas** solves these challenges by combining **authentic NASA and USGS planetary datasets** with **rigorous biophysical modeling**, **directional graph search**, and **autonomous contingency resilience**:

```
+-----------------------------------------------------------------------------------+
|                           MARSWALK 2.0 SOLUTION ENGINE                            |
+-----------------------------------------------------------------------------------+
| 1. REAL PLANETARY DATA                                                            |
|    - USGS HiRISE 1m Elevation (Jezero Crater Delta, Séítah, Belva)                |
|    - NASA PDS MEDA Atmospheric Opacity (Tau), Pressure, Temperature               |
|    - Mars Climate Database v6.1 Solar Irradiance Profiles                         |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 2. BIOPHYSICAL & KINEMATIC PATH COST ENGINE                                       |
|    - Directional Human Locomotion Formulation (Santee et al. / Minetti equations) |
|    - Mechanical Gear & Suit Mass Loading (80 kg astronaut + 40 kg PLSS/tools)     |
|    - Strict Human Slope Cutoffs (20 deg nominal / 25 deg science)                 |
|    - Disaggregated Outbound vs. Return Path Cost Calculations                     |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 3. PLSS CONSUMABLE & METABOLIC BUDGET EVALUATOR                                   |
|    - Continuous Oxygen Consumption Rate Integration (Walking vs. Dwell Sampling)  |
|    - 20% Mandatory Emergency Reserve Enforcement                                  |
|    - Real-Time Visor HUD Telemetry Display (O2 %, Kcal, Remaining Margin)          |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 4. AUTONOMOUS CONTINGENCY RESILIENCE & ESCAPE CORRIDORS                           |
|    - Multi-State Contingency Progression (NOMINAL -> CAUTION -> RETURN_TO_BASE)  |
|    - MEDA Dust Storm Optical Depth Thresholding (Tau >= 3.0 Abort)                |
|    - Instantaneous Alternate Return Corridor Generation                           |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 5. SCIENTIFIC TRANSPARENCY & NON-SAFETY DISCLOSURE                                |
|    - Non-probabilistic truth: Explicitly distinguishes real data vs. models      |
|    - Prominent operational notice: Research decision-support model (not certified)|
+-----------------------------------------------------------------------------------+
```

---

### 3. Concrete Value Delivered

1. **For Planetary Surface Astronauts:**  
   Provides real-time situational awareness on the EVA Visor HUD, comparing outbound effort with return margin, alerting crew before the point-of-no-return consumable threshold is breached.

2. **For Mission Control & Flight Directors:**  
   Enables multi-criteria trade studies (Conservative, Science-Priority, Time-Efficient routes) evaluating scientific return against crew fatigue and consumable expenditure.

3. **For Robotic Science Operations:**  
   Delivers cross-validated rover traversal plans aligned with actual *Perseverance* ground truth, identifying high-priority sampling sites while avoiding wheel-slip terrain.
