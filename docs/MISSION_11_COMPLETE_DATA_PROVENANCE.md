# MISSION 11 — COMPLETE DATA PROVENANCE AUDIT

**Project:** MarsWalk 2.0 / Project Atlas  
**Audit Standard:** NASA Planetary Data System (PDS4), USGS Astrogeology Standards, IAU WGPSN Cartographic Conventions  
**Audit Tool:** `scripts/audit_mission11_data_provenance.py`  
**Master Manifests:**
- [`mission11_complete_data_inventory.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/manifests/mission11_complete_data_inventory.json)
- [`mission11_source_hashes.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/manifests/mission11_source_hashes.json)

---

## 1. Executive Summary & Inventory Scope

This audit provides an exhaustive, source-by-source accounting of every planetary dataset, raster, tabular record, and simulation catalog bundled within **MarsWalk 2.0 / Project Atlas**.

A total of **55 static data and asset files** totaling **29.70 MB** were analyzed for origin authority, acquisition methodology, processing lineage, coordinate reference frames, units of measure, and licensing.

### Provenance Rollup Breakdown

| Provenance Class Group | Primary Origin Authorities | File Count | Count Share (%) | Data Volume (MB) | Volume Share (%) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **USGS Astrogeology & IAU** | USGS Astrogeology Science Center, IAU WGPSN | 15 | 27.3% | 17.92 MB | **60.3%** |
| **NASA PDS & JPL Ground Truth** | NASA PDS Geosciences, PDS Atmospheres, JPL ACA | 20 | 36.4% | 5.36 MB | **18.0%** |
| **Application & Simulation Models** | MarsWalk Pipeline, Parametric Resilience Proxies | 17 | 30.9% | 6.07 MB | **20.4%** |
| **International Research Partners** | CNES / LMD (Sorbonne/CNRS) / ESA | 3 | 5.5% | 0.35 MB | **1.2%** |
| **TOTAL** | **Multi-Agency Planetary Consortium** | **55** | **100.0%** | **29.70 MB** | **100.0%** |

```
DATA VOLUME DISTRIBUTION (29.70 MB Total):
████████████████████████████████ USGS Astrogeology & IAU (60.3%)
███████████ Application & Simulation Models (20.4%)
██████████ NASA PDS & JPL (18.0%)
█ International Partners / MCD (1.2%)
```

---

## 2. Primary Dataset Provenance Profiles

### 2.1 USGS Jezero Crater CTX 20m Digital Terrain Model (DTM)
- **Local Files:**
  - Raw Mosaic: [`JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/raw/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif) (9.66 MB)
  - Processed Raster (250x250): [`jezero_ready_20m.tif`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/processed/jezero_ready_20m.tif) (252 KB)
- **Primary Publisher:** USGS Astrogeology Science Center (Flagstaff, AZ).
- **Spacecraft & Instrument:** NASA Mars Reconnaissance Orbiter (MRO) Context Camera (CTX).
- **Cartographic Citation:** Fergason, R. L. et al. (2020), *Mars 2020 Terrain Relative Navigation Flight Products: CTX DTM Mosaic*, USGS ScienceBase, [DOI: 10.5066/P906QQT8](https://doi.org/10.5066/P906QQT8).
- **Processing Methodology:**
  1. Multiple MRO CTX stereo image pairs acquired over Jezero Crater ($18.4^\circ\text{N}, 77.4^\circ\text{E}$).
  2. Photogrammetrically controlled and bundle-adjusted using USGS Integrated Software for Imagers and Spectrometers (ISIS3) and SOC stereo pipeline.
  3. Tied vertically to Mars Global Surveyor (MGS) Mars Orbiter Laser Altimeter (MOLA) Delta Geoid datum.
  4. Reprojected to Equirectangular projection at $20.0\,\text{m/pixel}$ resolution.
- **Coordinate Reference System (CRS):** `ESRI:103885` (IAU 2000 Mars Spheroid, $R = 3,396,190\,\text{m}$, standard parallel $0^\circ$, center lon $0^\circ$).
- **NoData Value:** $-3.4028227 \times 10^{38}$ (`float32`).
- **License / Terms:** Public Domain (U.S. Government Work).

---

### 2.2 USGS Hawksbill Gap HiRISE 1m Digital Terrain Model (DTM)
- **Local File:** [`jezero_hirise_hawksbill_1m.tif`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/processed/jezero_hirise_hawksbill_1m.tif) (1.44 MB)
- **Primary Publisher:** USGS Astrogeology Science Center / NASA JPL.
- **Spacecraft & Instrument:** NASA Mars Reconnaissance Orbiter (MRO) High Resolution Imaging Science Experiment (HiRISE).
- **Cartographic Citation:** Bland, M. T. et al. (2024), *Mars Sample Return HiRISE Digital Terrain Models for Landing and Surface Operations*, USGS ScienceBase, [DOI: 10.5066/P13CPYYU](https://doi.org/10.5066/P13CPYYU).
- **Parent Product ID:** `JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40.tif`.
- **Processing Methodology:**
  1. MRO HiRISE sub-meter stereo observation pairs of the western Jezero Delta scarp and Hawksbill Gap corridor.
  2. Extreme high-precision photogrammetric reconstruction at $1.0\,\text{m/pixel}$ resolution.
  3. Coregistered and co-aligned with regional CTX basemap and MOLA geoid elevation datum.
  4. Extracted $600 \times 600$ pixel sub-window covering the critical rover scarp ascent and sample cache depot zone.
- **Coordinate Reference System (CRS):** `ESRI:103885` (matches CTX DEM).
- **License / Terms:** Public Domain (U.S. Government Work).

---

### 2.3 NASA PDS Rover PLACES Ground-Truth Localization
- **Local Files:**
  - Raw Telemetry: [`pds_places_best_tactical.csv`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/raw/pds_places_best_tactical.csv) (171 KB)
  - Curated Catalog: [`perseverance_ground_truth_places.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/catalogs/perseverance_ground_truth_places.json) (256 KB)
- **Primary Publisher:** NASA Planetary Data System (PDS) Geosciences Node (Washington University in St. Louis).
- **Spacecraft & Instrument:** NASA Mars 2020 Perseverance Rover (Engineering Localization).
- **PDS4 Bundle URN:** `urn:nasa:pds:mars2020_rover_places:data_localizations:best_tactical.csv`.
- **Telemetry Span:** Sols 13 through 1896 (577 distinct high-fidelity tactical localization stations).
- **Processing Methodology:**
  1. Rover visual odometry, wheel odometry, and Rover Inertial Measurement Unit (RIMU) telemetry downlinked daily via Deep Space Network (DSN).
  2. Multi-sensor Kalman filtering and orbital image tie-point resection executed by JPL Rover Planners (best tactical solution).
  3. Ingestion into MarsWalk verifies planetocentric coordinates ($18.42^\circ\text{N}$ to $18.50^\circ\text{N}$, $77.22^\circ\text{E}$ to $77.46^\circ\text{E}$) and transforms positions to projected terrain coordinates for ground-truth comparison against planned routes.
- **License / Terms:** NASA Open Data Policy (Public Domain).

---

### 2.4 NASA JPL Three Forks Sample Depot Catalog
- **Local Files:**
  - Raw Log: [`pds_three_forks_sample_drops.csv`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/raw/pds_three_forks_sample_drops.csv) (539 bytes)
  - Curated Catalog: [`three_forks_sample_depot_catalog.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/catalogs/three_forks_sample_depot_catalog.json) (5.14 KB)
- **Primary Publisher:** NASA Jet Propulsion Laboratory (JPL) / Mars Sample Return Project.
- **Spacecraft & Instrument:** NASA Mars 2020 Perseverance Adaptive Caching Assembly (ACA).
- **PDS Citation:** PDS Geosciences Node, *Mars 2020 Sample Depot at Three Forks Drop Records*, Sols 653–676.
- **Contents:** Exact ground drop positions, Local Mean Solar Time (LMST), surface imagery identifiers, and geological core descriptions for all 10 deposited titanium sample tubes:
  1. *Malay* (Sol 653) — Basal mudstone
  2. *Mageik* (Sol 656) — Volcanic/olivine basalt
  3. *Crosswind Lake* (Sol 659) — Coarse sandstone
  4. *Roubion* (Sol 662) — Regolith/atmospheric witness
  5. *Coulettes* (Sol 665) — Delta mudstone
  6. *Montdenier* (Sol 668) — Olivine cumulate
  7. *Bearwallow* (Sol 671) — Sandstone
  8. *Skyland* (Sol 674) — Delta sandstone
  9. *Atsah* (Sol 675) — Igneous floor
  10. *Amalik Witness* (Sol 676) — Organic/particulate witness tube
- **License / Terms:** NASA Open Data Policy (Public Domain).

---

### 2.5 NASA PDS MEDA Atmospheric Observations
- **Local Files:**
  - Calibrated Air Temperature: [`mars2020_meda_calibrated_ATS.csv`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/environment/raw/meda/mars2020_meda_calibrated_ATS.csv) (558 KB)
  - Surface Pressure: [`mars2020_meda_derived_PS.csv`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/environment/raw/meda/mars2020_meda_derived_PS.csv) (482 KB)
  - Ground Temperature: [`mars2020_meda_derived_TRS.csv`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/environment/raw/meda/mars2020_meda_derived_TRS.csv) (496 KB)
  - Relative Humidity: [`mars2020_meda_derived_RHS.csv`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/environment/raw/meda/mars2020_meda_derived_RHS.csv) (497 KB)
  - Wind Vectors: [`mars2020_meda_derived_wind.csv`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/environment/raw/meda/mars2020_meda_derived_wind.csv) (82 KB)
  - Normalized Series: [`meda_normalized_series.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/environment/processed/meda_normalized_series.json) (3.00 MB)
  - Observations Catalog: [`meda_environmental_observations.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/catalogs/meda_environmental_observations.json) (2.67 KB)
- **Primary Publisher:** NASA PDS Atmospheres Node (New Mexico State University) / Centro de Astrobiología (CAB, CSIC-INTA, Spain).
- **Spacecraft & Instrument:** NASA Mars 2020 Perseverance Rover / Mars Environmental Dynamics Analyzer (MEDA).
- **Primary Scientific Citation:** Rodriguez-Manfredi, J. A. et al. (2021), *The Mars Environmental Dynamics Analyzer (MEDA) Instrument on the Mars 2020 Perseverance Rover*, Space Science Reviews, 217(3), 48.
- **Physical Verification:**
  - Pressure: $690.0\,\text{Pa}$ to $775.0\,\text{Pa}$ (capturing semi-diurnal thermal atmospheric tide).
  - Air Temperature ($1.45\,\text{m}$ above ground): $-88.4^\circ\text{C}$ to $-11.2^\circ\text{C}$.
  - Ground Radiometric Temperature: $-89.1^\circ\text{C}$ to $+8.2^\circ\text{C}$.
- **License / Terms:** NASA Open Data Policy (Public Domain).

---

### 2.6 NASA Mars 2020 In-Situ Science Targets
- **Local File:** [`geolocated_science_targets.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/catalogs/geolocated_science_targets.json) (3.92 KB)
- **Primary Publisher:** NASA Mars 2020 Science Team / Peer-Reviewed Primary Literature.
- **Validated Targets:**
  1. *Wildcat Ridge*: Fine-grained organic-bearing mudstone (Sol 520; Scheller et al., 2022, *Science*).
  2. *Skinner Ridge*: Deltaic sandstone outcrop (Sol 508; Farley et al., 2022).
  3. *Enchanted Lake*: Basal layered delta deposit (Sol 482; Simon et al., 2023).
  4. *Kodiak Butte*: Remnant Gilbert-type delta fan cliff (Sol 142; Mangold et al., 2021).
  5. *Belva Rim*: Impact crater layered ejecta and conglomerate (Sol 800; Wiens et al., 2023).
- **License / Terms:** Academic Open Access / NASA Open Data.

---

### 2.7 European Space Agency / CNES Mars Climate Database (MCD v6.2)
- **Local Files:**
  - NetCDF Archive: [`jezero_mcd_v6_2.nc`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/environment/raw/mcd/jezero_mcd_v6_2.nc) (365 KB)
  - Climatology Summary: [`mcd_climatology_summary.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/environment/processed/mcd_climatology_summary.json) (1.08 KB)
- **Primary Publisher:** Laboratoire de Météorologie Dynamique (LMD, CNRS / Sorbonne Université) / CNES / European Space Agency (ESA).
- **Scientific Citation:** Forget, F. et al., *Improved Mars Climate Database (MCD v6.2) for Atmospheric Entry and Operations*, Europlanet Science Congress.
- **Lineage:** Synthesized general circulation model (GCM) predicting seasonal variations in atmospheric density, dust column loading, and thermal structure across Mars solar longitudes ($L_s$).
- **License / Terms:** LMD / ESA Research & Educational License (Non-Commercial).

---

### 2.8 USGS / IAU Planetary Nomenclature Database
- **Local Files:**
  - Nomenclature Raw: [`MARS_nomenclature_center_pts.kml`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/raw/MARS_nomenclature_center_pts.kml) (5.42 MB)
  - Curated Catalog: [`mars_places.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/web/data/mars_places.json) (520 KB)
- **Primary Publisher:** International Astronomical Union (IAU) Working Group for Planetary System Nomenclature (WGPSN) in cooperation with USGS Astrogeology.
- **Records Count:** 2,061 formally approved named Martian geographical features (craters, planitia, valles, fossae, ridges, and historic landing sites).
- **License / Terms:** Public Domain / International Open Science.

---

### 2.9 Illustrative Simulation Models & Heuristic Proxies (Explicit Disclosures)
To maintain scientific transparency and prevent misleading claims, the following features are classified and labeled in the codebase as **heuristic proxies**, not empirical observations:
1. **Sol 89 Dust Storm Optical Depth ($\tau$):** While Mars experienced an authentic regional dust storm around Sol 89 (observed by MEDA sensors), the rapid step-function $\tau$-spike scenario in `mission_when_mars_goes_dark.json` is a **simulation scenario** designed to test autonomous rover/crew reaction logic.
2. **RF Dust Extinction Model:** Signal attenuation of the UHF Mars relay band ($401.58\,\text{MHz}$) during dust events is modeled using an analytical proxy ($\alpha_{\text{RF}} = k \cdot \tau$), not calibrated RF measurements.
3. **Solar Array Degradation Proxy:** Power loss during dust deposition is calculated using a modified Beer-Lambert irradiance decay ($I = I_0 e^{-\tau / \cos\theta}$), disclosed as an engineering simulation.
4. **Human EVA Mobility Model:** Astronaut walking speed and metabolic power expenditure use an empirical gravity-adjusted slope heuristic ($v(\theta) = v_{\text{nominal}} \cdot e^{-3.5|\sin\theta|}$), representing research decision-support models rather than medical certification.

---

## 3. Cryptographic Verification & Hash Audit Summary

All 55 audited files match their master cryptographic hashes in [`mission11_source_hashes.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/manifests/mission11_source_hashes.json). Zero altered, truncated, or unverified files were detected.

| Top Asset by Volume | Size (Bytes) | SHA-256 Checksum | Origin Group |
| :--- | :---: | :--- | :--- |
| `JEZ_ctx_B_soc_008_DTM_..._20m_Eqc_latTs0_lon0.tif` | 9,662,387 | `16a1aa66c3f48c1bca252795827db7b417876217aff0f5e1aff18027fab2327b` | USGS Astrogeology |
| `MARS_nomenclature_center_pts.kml` | 5,422,931 | `a61b835e3be538562d4993a749ef6022e6b54784a0c86ebf4b008d5b8823531b` | USGS / IAU |
| `meda_normalized_series.json` | 3,007,516 | `1707fc9691884399e5ca2d36fc3a17e01e6a5fe16bc6838d722db0b79313ea59` | NASA PDS Atmospheres |
| `jezero_hirise_hawksbill_1m.tif` | 1,441,904 | `0258c9e15d4bcca9c003eacba2a536ade61ac8b109730490faef97d5cd17f608` | USGS / NASA JPL |
| `MARS_nomenclature_center_pts.kmz` | 1,217,357 | `994aa1cae8e9ffc57dc16d418e2be35d56858e38f615fbaee0e9fbfa97405108` | USGS / IAU |
| `nasa_m20_waypoints.json` | 603,126 | `bd143ee69241229926abd373e6305b8bbb326d6b5a7b4a8d6935262696f93dc4` | NASA MMGIS / JPL |
| `mars2020_meda_calibrated_ATS.csv` | 558,743 | `c30e3544e4fdbbb0cd3548eb8ff42a474add321e6fb34f0d2ebb14de65d4634a` | NASA PDS Atmospheres |
| `mars_places.json` | 520,381 | `898ea65d86f7881c3c9c99df602a6548170b741aa2a98eef62a98f121dff0311` | USGS / IAU |
| `mars2020_meda_derived_RHS.csv` | 497,677 | `e0468932a7aad64e29eef66458d631015d8dde1b63ae49681595547fe18647d8` | NASA PDS Atmospheres |
| `mars2020_meda_derived_TRS.csv` | 496,706 | `a0ad2156c249350241c82c9bd9e85d1228439187dcdf70372540384ce92aaaf4` | NASA PDS Atmospheres |
| `mars2020_meda_derived_PS.csv` | 482,411 | `435817bf8bac2f0ed68718ec7d35d2df1fe2544b4bd9cd66f1200931485c248e` | NASA PDS Atmospheres |
| `jezero_mcd_v6_2.nc` | 365,184 | `085799986bb66d6d84a1e90dc815c345ecfae7b16382103328eb43fc83307221` | CNES / LMD / ESA |
| `perseverance_ground_truth_places.json` | 256,378 | `365691f13b63261a877ff484c2a71bfab49c12feab387cf38f97e748ea307406` | NASA PDS Geosciences |
| `jezero_ready_20m.tif` | 252,206 | `875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3` | USGS Astrogeology |
| `perseverance_curated_waypoints.json` | 240,519 | `ee95a32b6eeb79f41b212ddbc9aa8f9e67d2685a218f293ffb25d0bb47b592f6` | NASA MMGIS / JPL |
