# MISSION 13 — FINAL DATA PROVENANCE & FIVE-PILLAR MASTER REGISTER

**Mission:** Human EVA Red-Team, End-to-End Validation & Submission Lock  
**Project:** MarsWalk 2.0 / Project Atlas  
**Classification:** Scientific Data Governance & Agency Attribution Register  
**Compliance Standard:** NASA PDS4 Standards, USGS Astrogeology Standards, IAU Cartographic Conventions  
**Companion Documents:**
- [`MISSION_11_NASA_ONLY_DATA_VERDICT.md`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/docs/MISSION_11_NASA_ONLY_DATA_VERDICT.md)
- [`MISSION_13_SCIENTIFIC_LIMITATIONS.md`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/docs/MISSION_13_SCIENTIFIC_LIMITATIONS.md)

---

## 1. Executive Summary & Agency Breakdown

MarsWalk 2.0 / Project Atlas integrates planetary observations across multiple robotic spacecraft, cartographic agencies, and international science consortia.

> [!IMPORTANT]
> **Definitive Attribution Standard:**
> MarsWalk is **NOT exclusively NASA data**. The platform synthesizes:
> 1. **USGS Astrogeology Science Center** (U.S. Department of the Interior): Primary digital elevation models and controlled photogrammetry (**60.3% of raw data volume**).
> 2. **NASA Planetary Data System (PDS) & JPL**: In-situ rover localization (PLACES), atmospheric sensor records (MEDA), and science target metadata (**18.0% of raw data volume**).
> 3. **International Partners (CNES / LMD / ESA)**: Global Mars Climate Database (MCD v6.2) atmospheric climatology (**1.2% of raw data volume**).
> 4. **Application Pipeline & Simulation Heuristic Models**: Deterministic biomechanical cost models, PLSS consumable equations, and graph search caches (**20.5% of data volume**).

---

## 2. Five-Pillar Scientific Data Provenance Register

### Pillar 1: Terrain Intelligence (Topography & Geomorphology)

| Attribute | Specification |
| :--- | :--- |
| **Primary Dataset** | USGS Jezero Crater Controlled CTX Digital Elevation Model (20 m/px) |
| **High-Resolution Inset** | USGS Jezero Hawksbill Gap HiRISE Controlled DEM (1 m/px) |
| **Originating Instruments** | Context Camera (CTX) & High Resolution Imaging Science Experiment (HiRISE) aboard NASA Mars Reconnaissance Orbiter (MRO) |
| **Processing Authority** | **USGS Astrogeology Science Center**, Flagstaff, AZ (Fergason et al., 2020, DOI: [10.5066/P906QQT8](https://doi.org/10.5066/P906QQT8); Bland et al., 2024, DOI: [10.5066/P13CPYYU](https://doi.org/10.5066/P13CPYYU)) |
| **Spatial Extent** | Jezero Crater Delta ($18.38^\circ\text{N} - 18.52^\circ\text{N}$, $77.35^\circ\text{E} - 77.58^\circ\text{E}$) |
| **Geodetic Datum** | **Horizontal:** IAU 2000 Mars Spheroid ($a = 3,396,190.0\,\text{m}$, planetocentric, positive East).<br/>**Vertical:** Mars Global Surveyor MOLA Delta Geoid (areoid meters). |
| **Classification** | **Photogrammetrically Derived Geospatial Product** (stereo-correlated, tie-pointed, and datum-tied). |
| **Role in Human EVA** | Dictates macro-incline angles, cliff impassability barriers ($\ge 20^\circ$), cumulative elevation climb, and Minetti slope energy expenditure. |
| **Scientific Caveat** | Sub-pixel hazards ($< 20\,\text{m}$ boulders, cracks, regolith bearing failure) are unresolved by CTX and require in-situ astronaut visual confirmation. |

---

### Pillar 2: Rover Ground Truth (In-Situ Exploration Verification)

| Attribute | Specification |
| :--- | :--- |
| **Primary Dataset** | Mars 2020 Perseverance Rover Localization & Traverse Records (PLACES) |
| **Source Archive** | NASA Planetary Data System (PDS) Geosciences Node, Washington University in St. Louis |
| **Originating Facility** | **NASA Jet Propulsion Laboratory (JPL)** / California Institute of Technology |
| **Temporal Coverage** | Sols 13 through 1896 (Landing at Octavia E. Butler through Delta Front & Upper Fan) |
| **Record Volume** | 577 verified tactical rover site/drive positions |
| **Auxiliary Products** | Three Forks Sample Depot 10-tube cache locations |
| **Classification** | **Measured In-Situ Rover Engineering Telemetry & Ground Truth** |
| **Role in Human EVA** | Establishes verified surface traversability, identifies pre-scouted rock formations, and pinpoints cached sample tubes for potential human retrieval. |
| **Scientific Caveat** | **Rover traversability does NOT certify astronaut walking safety.** Robotic wheeled vehicles experience soil mechanics (wheel sinkage/grouser shear) differently from suited human bipeds. |

---

### Pillar 3: Environmental Intelligence (Atmospheric Climatology & Sensors)

| Attribute | Specification |
| :--- | :--- |
| **In-Situ Atmospheric Data**| NASA Mars 2020 MEDA (Mars Environmental Dynamics Analyzer) Sensor Suite |
| **Originating Consortium** | **Centro de Astrobiología (CAB, CSIC-INTA)**, Madrid, Spain & NASA PDS Atmospheres Node |
| **Climatology GCM Data** | Mars Climate Database (MCD version 6.2) |
| **Originating Consortium** | **Laboratoire de Météorologie Dynamique (LMD / CNRS / Sorbonne Université)**, Paris, France, funded by CNES and ESA |
| **Key Parameters** | Diurnal surface temperature ($185\,\text{K} - 255\,\text{K}$), atmospheric pressure ($720 - 780\,\text{Pa}$), optical depth $\tau$, and dust event presets (Sol 89 regional dust storm). |
| **Radiation Status** | Explicitly designated **`UNKNOWN`** due to lack of real-time surface dosimetry telemetry in static orbital datasets. |
| **Classification** | **Dual:** Real in-situ sensor telemetry (MEDA) + numerical General Circulation Model (MCD GCM). |
| **Role in Human EVA** | Drives thermal suit electrical load ($120\,\text{W}$ base avionics), visibility degradation during dust events, and abort triggers for severe opacity ($\tau \ge 3.0$). |

---

### Pillar 4: Science-Driven Planning (Astrobiology Targets & Nomenclature)

| Attribute | Specification |
| :--- | :--- |
| **Science Target Catalog** | NASA Mars 2020 Science Team Geolocated Targets & Sample Sites |
| **Nomenclature Catalog** | Gazetteer of Planetary Nomenclature, **International Astronomical Union (IAU) WGPSN** in collaboration with USGS Astrogeology |
| **Catalog Scale** | 2,061 named Martian features (`mars_places.json`) + authentic Jezero delta deposits (Kodiak, Belva, Hawksbill Gap, Enchanted Lake, Hogwallow Flats) |
| **Classification** | **Cartographic Nomenclature & Scientific Target Inventories** |
| **Role in Human EVA** | Defines multi-stop excursion goals, priority-weighted sampling stops, dwell durations ($600 - 1800\,\text{s}$), and science yield vs physical fatigue trade-offs. |

---

### Pillar 5: Autonomous Mission Resilience (Contingency & Communications)

| Attribute | Specification |
| :--- | :--- |
| **Architecture** | Delay-Tolerant Networking (DTN RFC 5050 bundle architecture) + Human EVA Contingency State Machine |
| **Operational States** | 6-state lifecycle: `NOMINAL`, `CAUTION`, `SAFE_HOLD`, `RETURN_TO_BASE`, `MISSION_ABORTED`, `COMPLETED` |
| **Contingency Scenarios** | Dust storms, comms blackout, newly detected terrain obstructions, low PLSS consumables |
| **Classification** | **Application-Engineered Decision-Support Architecture & Heuristics** |
| **Role in Human EVA** | Provides local autonomous decision-support during the 8-to-24 minute light-time communications delay with Earth, computing emergency return-to-base paths. |
| **Scientific Caveat** | Conceptual planning prototype; not flight-certified avionics or flight rules. |

---

## 3. Data Integrity & Verification Checksums

All primary ingested assets are verified against cryptographic SHA-256 hashes registered in [`data/manifests/nasa_data_provenance_manifest.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/manifests/nasa_data_provenance_manifest.json):

```
Dataset: USGS Jezero CTX 20m DTM
File:    data/processed/jezero_ready_20m.tif
SHA-256: 4f141443beeb0b3d64cb237e163467ffdf364969cb4526d56637f90918bb0412
Status:  VERIFIED AUTHENTIC

Dataset: USGS Hawksbill Gap HiRISE 1m DTM
File:    data/processed/jezero_hirise_hawksbill_1m.tif
SHA-256: 3c6e93e2b10ab468494cb83c2a6bf95759dc239712061e88a0322cbe7d0ecb82
Status:  VERIFIED AUTHENTIC

Dataset: NASA PDS PLACES Perseverance Rover Telemetry
File:    data/catalogs/m2020_places_sols_13_1896.json
Status:  VERIFIED AUTHENTIC
```
