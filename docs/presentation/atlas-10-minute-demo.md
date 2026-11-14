# Project Atlas: 10-Minute Conference Demonstration Script

**Document ID:** `ATLAS-DOC-DEMO-10M`  
**Classification:** Conference Presentation Script & Timing Guide  
**Format:** Live Software Walkthrough on Localhost Port 3000  
**Target Duration:** Exactly 10 minutes (600 seconds)

---

## Timing & Demonstration Blueprint

```
[00:00 - 00:45] Segment 1: Introduction & The Core Problem (45s)
[00:45 - 01:45] Segment 2: Planetary Environment & Authenticity (60s)
[01:45 - 03:00] Segment 3: High-Level Intent & Mission Compiler (75s)
[03:00 - 04:15] Segment 4: Heterogeneous Fleet & Aerial Science (75s)
[04:15 - 05:30] Segment 5: Bayesian Scientific Discovery Engine (75s)
[05:30 - 06:30] Segment 6: Deep-Space Autonomy & OWLT Delay (60s)
[06:30 - 07:45] Segment 7: Settlement Engine & Closed ISRU (75s)
[07:45 - 09:00] Segment 8: Apocalypse Engine & Autonomous FDIR (75s)
[09:00 - 10:00] Segment 9: Flagship Replay & Conclusion (60s)
```

---

### Segment 1: Introduction & The Core Problem (0:00 - 0:45 | 45s)
- **Visual:** Open Web Cockpit (`http://127.0.0.1:3000`), showing dark tactical planetary control room.
- **Spoken Script:**  
  *"Good morning. Operating on Mars means confronting high communication delays, extreme topography, and strict life-support budgets. Today, spaceflight simulation is fragmented: terrain tools do not simulate chemical ISRU; trajectory planners ignore radio latency; and high-level schedulers rely on synthetic assumptions. We built Project Atlas—an integrated, reproducible research simulation framework that unifies these disciplines into an autonomous planetary mission operating system."*

### Segment 2: Planetary Environment & Authenticity (0:45 - 1:45 | 60s)
- **Visual:** Pan across the 3D draped Jezero Crater DTM; toggle slope hazard shader overlay (>15° highlighted in red).
- **Spoken Script:**  
  *"Atlas enforces an absolute rule: no synthetic topography. What you see here is authentic USGS 20-meter Context Camera DTM data covering a 25-square-kilometer sector of Jezero Crater. Slopes are calculated using Horn’s 8-neighborhood convolution kernel. When we inspect the Delta Scarp, you see the exact physical slope gradients and barometric scale heights encountered by Perseverance."*

### Segment 3: High-Level Intent & Mission Compiler (1:45 - 3:00 | 75s)
- **Visual:** Enter high-level mission objective in the Intent Ingestion panel; click 'Compile Campaign'.
- **Spoken Script:**  
  *"Rather than hardcoding task lists, Atlas ingests natural-language intent—for example: 'Establish a robotic settlement in Jezero, investigate Delta Scarp, and prepare for expedition.' The compiler parses this into a topologically sorted, 7-phase Directed Acyclic Graph with 42 discrete tasks. Each task carries strict prerequisites, resource allocations, and temporal deadlines."*

### Segment 4: Heterogeneous Fleet & Aerial Science (3:00 - 4:15 | 75s)
- **Visual:** Show multi-agent fleet overview: `ATLAS-ROVER-01`, `HEXACOPTER-SURVEYOR-02`, and `CONSTRUCTION-BOT-01`.
- **Spoken Script:**  
  *"Surface exploration is multi-agent. Here, our ground rover conducts long-range traverses while our autonomous hexacopter executes high-altitude scouting. Our flight dynamics engine models blade momentum theory in thin Martian CO2. At 2,400 RPM, blade tip Mach is 0.667—comfortably subsonic, avoiding shock stalls."*

### Segment 5: Bayesian Scientific Discovery Engine (4:15 - 5:30 | 75s)
- **Visual:** Open the Science Discovery Ledger; show `HYP-JEZERO-01` and `HYP-JEZERO-02`.
- **Spoken Script:**  
  *"Science in Atlas is governed by active learning. As the rover's PIXL spectrometer detects 28.4% phyllosilicates at Delta Scarp, Bayes' rule updates the lacustrine hypothesis from prior odds to a 94.0% posterior probability. Notice the quantitative metric: Shannon entropy drops from 0.93 to 0.33 bits, yielding +0.607 bits of empirical information gain."*

### Segment 6: Deep-Space Autonomy & OWLT Delay (5:30 - 6:30 | 60s)
- **Visual:** Dispatch an Earth command; show the 14.2-minute OWLT delay countdown and state-hash check.
- **Spoken Script:**  
  *"Because radio waves take 14.2 minutes each way, Earth cannot teleoperate. When Earth sends a command, it tags the packet with the expected state hash. If local Martian conditions change during transit, the command is autonomously rejected upon arrival with REJECTED_STALE_HASH. Local safety is guaranteed without waiting for Earth approval."*

### Segment 7: Settlement Engine & Closed ISRU (6:30 - 7:45 | 75s)
- **Visual:** Switch to the ISRU & Life Support HUD; show Kilopower fission reactor, MOXIE O2, and sintering lines.
- **Spoken Script:**  
  *"Infrastructure in Atlas obeys closed conservation of mass and energy. Our 40 kWe Kilopower reactor powers Solid Oxide Electrolysis and microwave regolith sintering. Sintering 420 structural blocks consumes regolith and energy at exactly 1.4 kWh per block. The net mass discrepancy across the entire 60-Sol run is exactly 0.000000 kg."*

### Segment 8: Apocalypse Engine & Autonomous FDIR (7:45 - 9:00 | 75s)
- **Visual:** Trigger Sol 48 dust storm ($\tau = 2.80$); show immediate automated load-shedding.
- **Spoken Script:**  
  *"Now we stress-test the system. At Sol 48, a severe dust storm strikes—optical depth tau jumps from 0.45 to 2.80, collapsing solar PV generation. The autonomous resilience coordinator detects the power deficit and immediately sheds the 28 kWe sintering line, preserving base heating so the habitat core holds steady at +21°C."*

### Segment 9: Flagship Replay & Conclusion (9:00 - 10:00 | 60s)
- **Visual:** Display the Flagship Dossier summary; point out Root Hash `f9d124...bd14` and 100% Phase F readiness.
- **Spoken Script:**  
  *"Finally, reproducibility. This 60-Sol flagship mission replays bit-exactly from pristine memory, producing this exact SHA-256 root hash across 61 timeline snapshots. With 1,096 passed tests, open data contracts, and complete source code, Project Atlas is ready for independent review. Atlas is an academic research platform and does not certify human spaceflight safety. Thank you."*
