# Milestone 13T: Mission Campaign Compiler & Workstream DAG

**Milestone:** 13T — Atlas Planetary Mission OS  
**System Module:** `atlas_campaign_compiler.py`

---

## 1. High-Level Intent Decomposition

The Campaign Compiler converts unstructured natural-language objectives into a multi-phase campaign task dependency graph:

```
INPUT INTENT:
"Establish a robotic research settlement in Jezero, investigate scientifically valuable
geological regions, deploy supporting infrastructure and prepare a hypothetical long-duration expedition."
                                      |
                                      v
+----------------------------------------------------------------------------------------------------+
| PHASE A: Site Reconnaissance & Geotechnical Survey (Sols 01-08)                                   |
|   - TASK-A-01: Aerial DTM Slope & Hazard Mapping [Ingenuity, Hexacopter]                         |
|   - TASK-A-02: Ground Rover Geotechnical Bearing Verification (185 kPa) [Atlas Rover]             |
|   - TASK-A-03: Baseline Dust optical depth tau & Solar Flux Calibration [Atlas Rover, Comm Mast]   |
+----------------------------------------------------------------------------------------------------+
                                      |
+----------------------------------------------------------------------------------------------------+
| PHASE B: Infrastructure Staging & Power Grid Deployment (Sols 09-16)                               |
|   - TASK-B-01: Landing Zone Clearing & Grading (1,200 m2) [Construction Bot]                       |
|   - TASK-B-02: Kilopower 120 kWe Fission Reactor Emplacement & Cabling [Construction Bot, Rover]   |
+----------------------------------------------------------------------------------------------------+
                                      |
+----------------------------------------------------------------------------------------------------+
| PHASE C: Primary Habitat Pressurization & Thermal Stabilization (Sols 17-25)                       |
|   - TASK-C-01: Habitat Core Inflatable Deployment & Ground Anchoring [Construction Bot]           |
|   - TASK-C-02: Environmental Loop Pressurization (101.3 kPa, 294 K) [Habitat Core]                 |
+----------------------------------------------------------------------------------------------------+
                                      |
+----------------------------------------------------------------------------------------------------+
| PHASE D: Pilot In-Situ Resource Utilization (ISRU) Operations (Sols 26-36)                         |
|   - TASK-D-01: Atmospheric SOXE Oxygen Generation Startup (2.45 kg/sol) [ISRU Plant]               |
|   - TASK-D-02: Microwave Sintering of Blast Berm Protection Blocks (240 blocks) [Construction Bot] |
+----------------------------------------------------------------------------------------------------+
                                      |
+----------------------------------------------------------------------------------------------------+
| PHASE E: Distributed Planetary Science & Sample Caching (Sols 37-46)                               |
|   - TASK-E-01: Delta Scarp Traverse & Mineralogical Core Ingestion [Atlas Rover]                   |
|   - TASK-E-02: Aerial Multispectral Transect of Séítah Olivine Dunes [Hexacopter]                  |
+----------------------------------------------------------------------------------------------------+
                                      |
+----------------------------------------------------------------------------------------------------+
| PHASE F: Deep-Space Autonomy & Resilient Contingency Response (Sols 47-54)                         |
|   - TASK-F-01: 14.2 min Light-Time Delay Autonomous Command Execution [Atlas Rover, Ingenuity]     |
|   - TASK-F-02: Regional Dust Storm Resilient Load-Shedding & Recovery [Habitat Core, ISRU Plant]   |
+----------------------------------------------------------------------------------------------------+
                                      |
+----------------------------------------------------------------------------------------------------+
| PHASE G: Long-Duration Expedition Readiness & Final Qualification Review (Sols 55-60)              |
|   - TASK-G-01: Closed Mass & Energy Balance End-of-Campaign Audit [Habitat Core, ISRU Plant]       |
|   - TASK-G-02: Mission Performance Dossier & Phase F Qualification Review [Atlas Rover, Comm Mast] |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Prerequisite Enforcement & Task Lifecycle

Each task transitions strictly through:
$$\text{QUEUED} \longrightarrow \text{IN\_PROGRESS} \longrightarrow \text{COMPLETED} \quad (\text{or } \text{BLOCKED} / \text{FAILED})$$

A task cannot transition to `IN_PROGRESS` unless:
$$\forall p \in \text{task.prerequisites}, \quad \text{state}(p) = \text{COMPLETED}$$
This mathematical guarantee ensures no construction, pressurization, or drilling occurs before foundation surveys and power grids are verified.
