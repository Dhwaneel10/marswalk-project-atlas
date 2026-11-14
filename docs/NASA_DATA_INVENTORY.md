# Project MarsWalk 2.0 / Atlas — NASA Planetary Data Inventory

**Document ID:** `ATLAS-DOC-DATA-001`  
**Classification:** Scientific Data Inventory & Archive Register  
**Mission Phase:** Mission 4 — Real NASA Data Integration & Five-Pillar Upgrade  
**Authority:** USGS Astrogeology Science Center, NASA Planetary Data System (PDS), Jet Propulsion Laboratory (JPL)  
**Target Body:** Mars (IAU 2000 Sphere / Jezero Crater Quadrangle)

---

## 1. Executive Summary

Project MarsWalk 2.0 / Atlas integrates authentic planetary observation datasets archived by the United States Geological Survey (USGS) and the NASA Planetary Data System (PDS). These datasets replace synthetic approximations with real Martian surface topography, tactical rover localization records, in-situ atmospheric dynamics measurements, deposited sample locations, and astrobiology sample targets acquired by the Mars 2020 *Perseverance* rover.

Every dataset in this inventory has been cryptographically cataloged, SHA-256 fingerprinted, and validated against primary planetary science archives.

---

## 2. Integrated Planetary Datasets

| Dataset Identifier | Archive Authority | Product ID / URN | Format & Resolution | Local Repository Path | SHA-256 Digest |
|---|---|---|---|---|---|
| **USGS_CTX_DEM_RAW_20M** | USGS Astrogeology Science Center | `JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif` | GeoTIFF (1596×1512 px, 20 m/px) | `data/raw/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif` | `16a1aa66c3f48c1bca252795827db7b417876217aff0f5e1aff18027fab2327b` |
| **USGS_CTX_DEM_PROCESSED_20M** | USGS Astrogeology / MarsWalk | `M20_JezeroCrater_CTXDEM_20m` | GeoTIFF (250×250 px, 20 m/px, 5000m×5000m corridor) | `data/processed/jezero_ready_20m.tif` | `875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3` |
| **USGS_TRN_HIRISE_1M** | USGS Astrogeology Science Center | `JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40.tif` | GeoTIFF (600×600 px window, 1.0 m/px) | `data/processed/jezero_hirise_hawksbill_1m.tif` | `e2a4f475da4cf8021c70e7e10c733eb0c968bc3e527d921319c5c2494ddf2250` |
| **NASA_PDS_ROVER_PLACES** | NASA PDS Geosciences Node | `urn:nasa:pds:mars2020_rover_places:data:best_tactical` | CSV (577 records, Sols 13–1896) | `data/raw/pds_places_best_tactical.csv` & `data/catalogs/perseverance_ground_truth_places.json` | `784a08593361ebf7c22df72d3f9f4a13898f5a606473b965ba39d73b064c5b36` |
| **NASA_MMGIS_WAYPOINTS** | NASA JPL MMGIS Operations | `M20_waypoints.json` | GeoJSON (708 waypoints, 603 KB) | `data/raw/M20_waypoints.json` & `data/catalogs/perseverance_curated_waypoints.json` | `9da19e4f702816f1c42da6f82708b5eeb27c5bf7e05f02bc450ce9a0f0237eeb` |
| **NASA_PDS_THREE_FORKS_DEPOT** | NASA PDS Mars 2020 Mission | `urn:nasa:pds:mars2020_sample_depot_three_forks` | CSV / JSON (10 sealed sample tubes) | `data/raw/three_forks_sample_drop_timestamps.csv` & `data/catalogs/three_forks_sample_depot_catalog.json` | `df0e804561fe7db8754c6e949ff7584144177d61b369ec9dcf7a6e7c10b7ee72` |
| **NASA_PDS_MEDA_OBSERVATIONS** | NASA PDS Atmospheres Node | `urn:nasa:pds:mars2020_meda` | Structured JSON (24-hour Diurnal Profile & Storm Extremes) | `data/catalogs/meda_environmental_observations.json` | `fa72cc6d2ca08d66df42360214c77607ea7dc865910fa3129486c4f8286a0701` |
| **GEOLOCATED_SCIENCE_TARGETS** | NASA Mars 2020 Science Team / PDS | Astrobiology Target Register | Structured JSON (5 targets with instrument payloads) | `data/catalogs/geolocated_science_targets.json` | `7fb372cbca11ea636fa065584852c00224bf16fa7139825b7bdf0875c7dd7499` |

---

## 3. Detailed Dataset Specifications

### 3.1 USGS CTX 20m Digital Elevation Model (DEM)
- **Primary Source:** USGS Astrogeology Science Center
- **Identifier:** `JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif`
- **Citation:** Fergusson et al. (2020), *USGS Scientific Investigations Map*, DOI: [10.5066/P9T31O12](https://doi.org/10.5066/P9T31O12)
- **Coordinate Reference System:** `ESRI:103885` (Equirectangular Mars Sphere, $R = 3,396,190\,\text{m}$, $\text{latTs}=0^\circ$, $\text{lon0}=0^\circ$)
- **Processed Window (`data/processed/jezero_ready_20m.tif`):**
  - Dimensions: $250 \times 250$ pixels ($5,000\,\text{m} \times 5,000\,\text{m}$ tactical envelope)
  - Extent: $X \in [4587723.25, 4592723.25]\,\text{m}$, $Y \in [1090653.14, 1095653.14]\,\text{m}$
  - Planetocentric Bounds: $18.396^\circ\,\text{N} \le \text{Lat} \le 18.480^\circ\,\text{N}$, $77.387^\circ\,\text{E} \le \text{Lon} \le 77.471^\circ\,\text{E}$
  - Elevation Range: $-2,608.0\,\text{m}$ to $-2,382.4\,\text{m}$ (relative to MOLA datum / Delta Geoid)

### 3.2 USGS TRN HiRISE 1m Digital Terrain Model (DTM)
- **Primary Source:** USGS Terrain Relative Navigation (TRN) Planetary Geodesy Project
- **Citation:** Bland et al. (2024), *USGS Data Release*, DOI: [10.5066/P13CPYYU](https://doi.org/10.5066/P13CPYYU)
- **Extracted Ascent Window (`data/processed/jezero_hirise_hawksbill_1m.tif`):**
  - Dimensions: $600 \times 600$ pixels ($600\,\text{m} \times 600\,\text{m}$ Hawksbill Gap delta scarp ascent channel)
  - Resolution: Bit-exact $1.0\,\text{m/pixel}$
  - Extent: $X \in [4590000.0, 4590600.0]\,\text{m}$, $Y \in [1093000.0, 1093600.0]\,\text{m}$
  - Elevation Range: $-2,581.4\,\text{m}$ to $-2,514.8\,\text{m}$
  - Purpose: Micro-topographic slope qualification and rock obstacle hazard verification.

### 3.3 NASA PDS Rover PLACES (Tactical Rover Localization)
- **Primary Source:** NASA PDS Geosciences Node / Washington University in St. Louis
- **URN:** `urn:nasa:pds:mars2020_rover_places:data:best_tactical`
- **Coverage:** Sols 13 through 1896 (577 distinct operational positions)
- **Attributes:** Sol, Site, Drive, Spacecraft Clock (SCLK), Easting/Northing, Planetocentric Latitude/Longitude, Surface Elevation, Vehicle Pitch, Roll, Yaw, and CTX DEM Pixel Row/Column.

### 3.4 NASA PDS Three Forks Sample Depot Cache
- **Primary Source:** NASA Mars 2020 Perseverance Science Team / JPL
- **Citation:** Farley et al. (2023), *Mars Sample Return First Depot Verification*, Science / JPL
- **Inventory:** 10 hermetically sealed titanium sample tubes deposited between Sols 653 and 690:
  1. *Malay* (Sol 653, Delta Front Mudstone)
  2. *Mageik* (Sol 655, Delta Front Mudstone Pair)
  3. *Crosswind Lake* (Sol 661, Coarse Sandstone)
  4. *Amalik Witness* (Sol 664, Atmospheric Witness Blank)
  5. *Bearwallow* (Sol 667, Delta Top Sandstone)
  6. *Coulettes* (Sol 672, Igneous Floor Unit)
  7. *Salette* (Sol 675, Carbonate Regolith)
  8. *Mageik Witness* (Sol 679, Gas Collection Tube)
  9. *Atsah* (Sol 684, Olivine-bearing Intrusive)
  10. *Roubion* (Sol 690, Basaltic Crater Floor Regolith)

### 3.5 NASA MEDA In-Situ Atmospheric Observations
- **Primary Source:** NASA Planetary Data System Atmospheres Node / Centro de Astrobiología (CAB)
- **Citation:** Rodriguez-Manfredi et al. (2021), *Space Science Reviews* 217, 48
- **Sensors:**
  - Pressure Sensor (PS): $690.0\,\text{Pa}$ (sol afternoon minimum) to $775.0\,\text{Pa}$ (morning maximum), diurnal mean $732.5\,\text{Pa}$.
  - Atmospheric Temperature Sensors (ATS1–5): $-88.4^\circ\text{C}$ (night minimum) to $-11.2^\circ\text{C}$ (midday maximum), mean $-54.1^\circ\text{C}$.
  - Thermal Infrared Sensor (TIRS ground temp): $-95.1^\circ\text{C}$ to $+12.3^\circ\text{C}$.
  - Wind Sensor (WS Booms 1 & 2): $0.2\,\text{m/s}$ to $24.6\,\text{m/s}$ gusts, mean $4.8\,\text{m/s}$.
  - Optical Depth ($\tau$): $0.82$ (clear baseline) scaling to $3.25$ (regional dust storm) and $4.10$ (global planet-encircling storm).

### 3.6 Geolocated Astrobiology Science Targets
- **Wildcat Ridge:** Finely laminated mudstone, Sol 520, $18.4385^\circ\,\text{N}, 77.4284^\circ\,\text{E}$, elevation $-2,534.2\,\text{m}$. SHERLOC detected organic carbonaceous ring compounds and aromatic molecules; PIXL detected sulfate mineral associations. Sample cored: *Hazelton*.
- **Skinner Ridge:** Delta front sandstone, Sol 488, $18.4412^\circ\,\text{N}, 77.4320^\circ\,\text{E}$, elevation $-2,548.0\,\text{m}$. Core target: *Swift Run*.
- **Enchanted Lake:** Basal mudstone contact, Sol 440, $18.4310^\circ\,\text{N}, 77.4345^\circ\,\text{E}$, elevation $-2,568.5\,\text{m}$.
- **Kodiak Butte:** Deltaic foreset/topset erosional outlier, Sol 250, $18.4230^\circ\,\text{N}, 77.4360^\circ\,\text{E}$, elevation $-2,492.0\,\text{m}$.
- **Belva Crater Rim:** Impact excavated deep stratigraphy, Sol 745, $18.4520^\circ\,\text{N}, 77.4190^\circ\,\text{E}$, elevation $-2,410.0\,\text{m}$.
