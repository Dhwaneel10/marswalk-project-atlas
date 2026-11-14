# MarsWalk 2.0 / Project Atlas — Mission Compiler Conference Demo Script

**Session Length:** 5 Minutes  
**Audience:** Planetary Scientists, Aerospace Mission Planners, Autonomy Researchers  
**Live URL:** `http://127.0.0.1:3000/?tab=design_studio`

---

## 1. Introduction: The Mission Design Paradigm Shift (0:00 – 1:00)

> "In traditional planetary operations, planning a multi-rover campaign across complex terrain like the Jezero delta takes weeks of human engineering effort across separate teams: mobility engineers calculate energy, communications engineers map line-of-sight relays, and science payload teams fight for observation time.
>
> In Atlas Milestone 13K, we introduce the **Atlas Goal-Driven Mission Design Compiler**. Watch how an operator can state natural-language intent and compile an entire 5-sol multi-rover campaign in under 15 milliseconds."

---

## 2. Intent Specification & Validation (1:00 – 2:00)

1. Click **📄 LOAD SAMPLE INTENT**.
2. Point out the brief:
   > *"Explore the western Jezero delta using two rovers over five sols. Prioritize geological characterization and mineralogical investigation. Preserve at least 20% of each rover's configured energy reserve. Deploy no more than two relays."*
3. Click **🔍 VALIDATE INTENT**.
4. Surface the **VALID** badge:
   > "Notice that the compiler immediately verifies the intent against our authoritative USGS CTX 20m DTM and instrument catalog. Zero physical violations detected."

---

## 3. Autonomous Portfolio Compilation & Pareto Champions (2:00 – 3:30)

1. Click **⚡ COMPILE CAMPAIGN**.
2. Reveal the 8 synthesized candidate cards:
   > "In less than 10 milliseconds, the compiler solved 7 hierarchical planning levels: goal decomposition, task allocation, terrain-aware mobility, RelayNet mesh visibility, independent battery ledgers, multi-sol scheduling, and invariant gates.
   >
   > Look at the 8 distinct operational postures: Balanced, Science Maximizing, Energy Efficient, Communications Focused, Minimum Duration, Robustness Focused, Minimum Infrastructure, and Data Return Focused. Six are Pareto Champions on the non-dominated frontier."
3. Click on **Science Maximizing**:
   > "Selecting Science Maximizing brings up its Directed Acyclic Task Graph (DAG) below."

---

## 4. Interactive Task Graph (DAG) & Causal Debugger (3:30 – 4:30)

1. Scroll to the **Directed Acyclic Task Graph (DAG)**:
   > "Here is the exact task graph: traverses in cyan, arrivals in blue, instrument preps in yellow, observations in green, and diurnal checkpoints in amber. The critical path is highlighted with an active glowing dash line."
2. Click on a task node to show its duration, energy consumption, and prerequisite links.
3. Demonstrate the **Plan Compilation Debugger**:
   - Set the Battery Reserve slider to an impossible $40\%$.
   - Re-compile to trigger the Debugger Drawer:
   > "When constraints conflict, Atlas doesn't crash or guess. It isolates the conflict core and offers 1-click relaxation proposals to safely restore feasibility."

---

## 5. Conclusion & Operational Promotion (4:30 – 5:00)

1. Click **🚀 PROMOTE PLAN TO FLEET**:
   > "With a single click, this compiled mission plan is signed, fingerprinted, and handed off to active fleet operations. This is how future robotic fleets will explore the Moon and Mars."
