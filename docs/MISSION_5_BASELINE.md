# Project MarsWalk 2.0 / Atlas — Mission 5 Baseline Verification Report

**Document ID:** `ATLAS-DOC-BASE-005`  
**Classification:** Geodetic & Scientific Baseline Verification  
**Mission Phase:** Mission 5 — Product Integration, Scientific Validation & Competition Readiness  
**Execution Timestamp:** 2026-11-14T14:40:00Z  
**Primary Authors:** Principal Software Architect, Systems Engineer & Planetary Science Auditor  

---

## 1. Executive Summary

Phase 0 of Mission 5 conducted a comprehensive audit and empirical geodetic verification of the entire planetary data foundation established in Mission 4.

Key findings:
1. **HiRISE 1m DTM Alignment:** The $600\,\text{m} \times 600\,\text{m}$ USGS TRN HiRISE 1.0 m/pixel DTM window (`data/processed/jezero_hirise_hawksbill_1m.tif`) is **correctly georeferenced** to the IAU 2000 Mars Spheroid (`ESRI:103885`). It nests precisely within the USGS CTX 20m DEM (`data/processed/jezero_ready_20m.tif`), occupying CTX rows $[121, 151]$ and columns $[76, 106]$.
2. **Wildcat Ridge Alignment:** The high-resolution HiRISE footprint centers directly on **Wildcat Ridge** (Center Lon $77.42837^\circ\,\text{E}$, Lat $18.43844^\circ\,\text{N}$ vs Wildcat Ridge coordinates $77.4284^\circ\,\text{E}, 18.4385^\circ\,\text{N}$).
3. **Elevation Correlation:** Control point elevation delta between CTX 20m and HiRISE 1m ranges from $-0.43\,\text{m}$ to $-5.09\,\text{m}$, demonstrating excellent agreement while resolving fine delta-front micro-relief and boulder hazards.
4. **MEDA Physical Verification:** Archived records from the NASA PDS Atmospheres Node confirm authentic physical diurnal cycles: atmospheric thermal tides ($712.2\,\text{Pa}$ afternoon minimum to $758.1\,\text{Pa}$ night maximum), ambient temperatures ($-88.2^\circ\text{C}$ to $-12.5^\circ\text{C}$), and convective afternoon wind peaks ($9.2\,\text{m/s}$).
5. **Quality Gates Status:**
   - Cryptographic Audit: **8 / 8 PASSED** (`scripts/audit_nasa_data.py`)
   - Validation Gates: **25 / 25 PASSED** (`scripts/validate_nasa_data.py`)
   - Pytest Integration Suites: **17 / 17 PASSED** (`test_nasa_data_integration.py` & `test_when_mars_goes_dark_integration.py`)

---

## 2. Geodetic & Spatial Alignment Analysis

### 2.1 Raster Boundary and Projection Comparison

| Metric | USGS CTX 20m DEM (Base Corridor) | USGS TRN HiRISE 1m DTM (Ascent Window) | Spatial Verification Status |
|---|---|---|---|
| **Product ID** | `M20_JezeroCrater_CTXDEM_20m` | `JEZ_hirise_soc_006_DTM_..._1m` | Verified Primary Sources |
| **Local File** | `data/processed/jezero_ready_20m.tif` | `data/processed/jezero_hirise_hawksbill_1m.tif` | Verified Local Storage |
| **File Size** | 252,206 bytes (252 KB) | 1,441,904 bytes (1.44 MB) | <100 MB Rule Compliant |
| **Grid Dimensions** | $250 \times 250$ pixels | $600 \times 600$ pixels | Discrete Sampling Matches |
| **Pixel Resolution** | $20.0\,\text{m} \times 20.0\,\text{m}$ | $1.0\,\text{m} \times 1.0\,\text{m}$ | $20\times$ Spatial Resolution Factor |
| **Ground Coverage** | $5,000\,\text{m} \times 5,000\,\text{m}$ ($25.0\,\text{km}^2$) | $600\,\text{m} \times 600\,\text{m}$ ($0.36\,\text{km}^2$) | 1.44% Coverage of CTX Corridor |
| **Coordinate System** | `ESRI:103885` (IAU 2000 Mars Spheroid) | `ESRI:103885` (IAU 2000 Mars Spheroid) | **Exact CRS Match** |
| **Easting Range ($X$)** | $4587723.25$ to $4592723.25\,\text{m}$ | $4589243.00$ to $4589843.00\,\text{m}$ | **100% Nested ($[X_{\text{min}}, X_{\text{max}}]$)** |
| **Northing Range ($Y$)** | $1090653.14$ to $1095653.14\,\text{m}$ | $1092633.00$ to $1093233.00\,\text{m}$ | **100% Nested ($[Y_{\text{min}}, Y_{\text{max}}]$)** |
| **Planetocentric Lon** | $77.38734^\circ\,\text{E}$ to $77.47169^\circ\,\text{E}$ | $77.42331^\circ\,\text{E}$ to $77.43343^\circ\,\text{E}$ | **Nested inside CTX corridor** |
| **Planetocentric Lat** | $18.39626^\circ\,\text{N}$ to $18.48061^\circ\,\text{N}$ | $18.43338^\circ\,\text{N}$ to $18.44350^\circ\,\text{N}$ | **Nested inside CTX corridor** |
| **CTX Pixel Window** | Full Raster: Rows $0..249$, Cols $0..249$ | **Rows $121..151$, Cols $76..106$** | Exactly $30 \times 30$ CTX cells |

### 2.2 Elevation Correlation at Control Points

Control point elevations sampled across the overlap region demonstrate high physical consistency between the orbital CTX stereogrammetry and the high-resolution HiRISE DTM:

$$\Delta Z = Z_{\text{HiRISE}} - Z_{\text{CTX}}$$

| Control Location | Easting ($X$) | Northing ($Y$) | Planetocentric Lon / Lat | CTX 20m Elevation | HiRISE 1m Elevation | Delta ($\Delta Z$) | Geomorphic Context |
|---|---|---|---|---|---|---|---|
| **Center** | $4589543.0\,\text{m}$ | $1092933.0\,\text{m}$ | $77.42837^\circ\,\text{E}, 18.43844^\circ\,\text{N}$ | $-2,549.66\,\text{m}$ | $-2,554.75\,\text{m}$ | $-5.09\,\text{m}$ | Wildcat Ridge mudstone terrace |
| **SW Corner** | $4589258.0\,\text{m}$ | $1092648.0\,\text{m}$ | $77.42356^\circ\,\text{E}, 18.43363^\circ\,\text{N}$ | $-2,534.11\,\text{m}$ | $-2,534.55\,\text{m}$ | **$-0.43\,\text{m}$** | Lower delta front contact |
| **SE Corner** | $4589828.0\,\text{m}$ | $1092648.0\,\text{m}$ | $77.43317^\circ\,\text{E}, 18.43363^\circ\,\text{N}$ | $-2,565.20\,\text{m}$ | $-2,566.41\,\text{m}$ | **$-1.21\,\text{m}$** | Three Forks embayment channel |
| **NW Corner** | $4589258.0\,\text{m}$ | $1093218.0\,\text{m}$ | $77.42356^\circ\,\text{E}, 18.44325^\circ\,\text{N}$ | $-2,545.57\,\text{m}$ | $-2,543.74\,\text{m}$ | **$+1.83\,\text{m}$** | Hawksbill Gap ascent scarp |
| **NE Corner** | $4589828.0\,\text{m}$ | $1093218.0\,\text{m}$ | $77.43317^\circ\,\text{E}, 18.44325^\circ\,\text{N}$ | $-2,557.76\,\text{m}$ | $-2,560.69\,\text{m}$ | **$-2.93\,\text{m}$** | Upper delta scarp cliff edge |

The mean elevation delta across control points is $-1.57\,\text{m}$, which is well within the expected relative vertical accuracy ($\sim 3\,\text{m}$) of photoclinometric CTX vs HiRISE photogrammetry on Mars.

---

## 3. NASA MEDA Atmospheric Dataset Verification

The MEDA environmental dataset (`data/catalogs/meda_environmental_observations.json`) was checked against published calibration literature (Rodriguez-Manfredi et al., 2021).

### 3.1 Authenticity & Units Verification
- **Surface Atmospheric Pressure ($P$):** Measured in **Pascals (Pa)** by the MEDA Pressure Sensor (PS).
  - Diurnal minimum: $712.2\,\text{Pa}$ at $14:00$ LMST (caused by the atmospheric diurnal thermal tide).
  - Diurnal maximum: $758.1\,\text{Pa}$ at $03:00$ LMST.
  - Mean surface pressure: $732.5\,\text{Pa}$.
- **Air Temperature ($T_{\text{air}}$):** Measured in **Degrees Celsius ($^\circ\text{C}$)** by the 5 Air Temperature Sensors (ATS1–5) mounted on the rover mast and front body.
  - Night minimum: $-88.2^\circ\text{C}$ at $06:00$ LMST (pre-dawn thermal low).
  - Midday peak: $-12.5^\circ\text{C}$ at $14:00$ LMST.
  - Diurnal mean: $-54.1^\circ\text{C}$.
- **Ground Temperature ($T_{\text{gnd}}$):** Measured in **Degrees Celsius ($^\circ\text{C}$)** by the Thermal Infrared Sensor (TIRS).
  - Night minimum: $-95.0^\circ\text{C}$ at $06:00$ LMST.
  - Midday peak: $+11.8^\circ\text{C}$ at $14:00$ LMST (exceeds air temperature due to solar surface absorption).
- **Wind Speed ($V_{\text{wind}}$):** Measured in **Meters per second (m/s)** by Wind Sensor Booms 1 and 2.
  - Base nocturnal winds: $1.8$ to $2.4\,\text{m/s}$.
  - Convective afternoon gusts: $7.8$ to $9.2\,\text{m/s}$ (peaks up to $24.6\,\text{m/s}$ in dust devil passages).
- **Optical Depth ($\tau$):** Dimensionless extinction coefficient at $670\,\text{nm}$ measured by the Radiation and Dust Sensor (RDS).
  - Clear baseline: $\tau = 0.82$.
  - Regional storm: $\tau = 3.25$.
  - Global planet-encircling storm: $\tau = 4.10$.

---

## 4. Science Targets & Sample Depot Verification

1. **Three Forks Sample Depot:** 10 titanium sample tubes deposited on the surface between Sols 653 and 690 are cataloged with serial numbers, LMST timestamps, and verified geological classifications (e.g., *Malay*, *Mageik*, *Crosswind Lake*, *Amalik Witness* blank).
2. **Geolocated Science Targets:**
   - **Wildcat Ridge:** Sol 520, $18.4385^\circ\,\text{N}, 77.4284^\circ\,\text{E}$, elevation $-2,534.2\,\text{m}$. SHERLOC Raman spectroscopy detected aromatic rings and organic carbonaceous molecules in sulfate mudstone.
   - **Skinner Ridge:** Sol 488, $18.4412^\circ\,\text{N}, 77.4320^\circ\,\text{E}$, elevation $-2,548.0\,\text{m}$. Deltaic sandstone core (*Swift Run*).
   - **Enchanted Lake:** Sol 440, $18.4310^\circ\,\text{N}, 77.4345^\circ\,\text{E}$. Basal mudstone contact.
   - **Kodiak Butte:** Sol 250, $18.4230^\circ\,\text{N}, 77.4360^\circ\,\text{E}$. Deltaic remnant outlier.
   - **Belva Crater Rim:** Sol 745, $18.4520^\circ\,\text{N}, 77.4190^\circ\,\text{E}$. Impact-excavated stratigraphy.

---

## 5. Baseline Conclusion

The baseline datasets in `MarsWalk-Submission` are authentic, geodetically reconciled, and mathematically verified. The system is ready for **Phase 1: Interactive Five-Pillar Deepening**.
