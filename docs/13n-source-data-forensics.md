# Milestone 13N: Planetary Source Data Forensics & Provenance Audit
**Document ID:** `DOC-13N-DATA-002`  
**Milestone:** 13N — The Scientific Reproducibility Tribunal  
**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** November 2026  
**Auditor:** Scientific Reproducibility Tribunal (Reviewer A & Lead Integration Owner)  
**Status:** AUDITED & VERIFIED  

---

## 1. Executive Summary

This forensic investigation audits every planetary dataset acquired, ingested, and processed in Milestone 13M. In accordance with Section 3 of the Milestone 13N directive, every product has been inspected for:
1. Physical origin and PDS archive provenance.
2. Data processing level (unprocessed telemetry vs calibrated vs derived vs GCM model reanalysis).
3. Header contents, units, coordinate systems, and quality flags.
4. Independent re-calculation of cryptographic SHA-256 digests.
5. Clear separation between in-situ surface weather, orbital limb soundings, and numerical climate simulations.

---

## 2. Product-by-Product Forensic Evidence Table

| Product ID | File Path | Format & Size | Processing Level | Source Archive / Authority | Computed SHA-256 | Forensic Verdict |
| :--- | :--- | :---: | :--- | :--- | :---: | :---: |
| `PDS4_M2020_MEDA_DERIVED_PS_INDEX` | `data/environment/raw/meda/mars2020_meda_derived_PS.csv` | CSV (482,411 B) | PDS4 Index Log (Daily Sols 1–1527) | NASA PDS Atmospheres Node (`PERSEVERANCE/logs`) | `435817bf8bac...` | **VERIFIED** |
| `PDS4_M2020_MEDA_DERIVED_TRS_INDEX` | `data/environment/raw/meda/mars2020_meda_derived_TRS.csv` | CSV (496,706 B) | PDS4 Index Log (Daily Sols 1–1524) | NASA PDS Atmospheres Node (`PERSEVERANCE/logs`) | `a0ad2156c249...` | **VERIFIED** |
| `PDS4_M2020_MEDA_DERIVED_RHS_INDEX` | `data/environment/raw/meda/mars2020_meda_derived_RHS.csv` | CSV (497,677 B) | PDS4 Index Log (Daily Sols 1–1524) | NASA PDS Atmospheres Node (`PERSEVERANCE/logs`) | `e0468932a7aa...` | **VERIFIED** |
| `PDS4_M2020_MEDA_DERIVED_WIND_INDEX` | `data/environment/raw/meda/mars2020_meda_derived_wind.csv` | CSV (82,758 B) | PDS4 Index Log (Daily Sols 36–267) | NASA PDS Atmospheres Node (`PERSEVERANCE/logs`) | `611d7d0ef918...` | **VERIFIED** |
| `PDS4_M2020_MEDA_CALIBRATED_ATS_INDEX`| `data/environment/raw/meda/mars2020_meda_calibrated_ATS.csv` | CSV (558,743 B) | PDS4 Index Log (Daily Sols 1–1526) | NASA PDS Atmospheres Node (`PERSEVERANCE/logs`) | `c30e3544e4fd...` | **VERIFIED** |
| `PDS4_M2020_MEDA_SOL0010_TIRS` | `data/environment/raw/meda/WE__0010___________DER_TIRS________________P04.CSV` | CSV (202,967 B) | Level 4 Derived Radiometric Ground Temp | NASA PDS4 RDR (`data_derived_env/sol_0010`) | `2141e0430b7f...` | **VERIFIED** |
| `PDS4_M2020_MEDA_SOL0010_ATS` | `data/environment/raw/meda/WE__0010___________CAL_ATS_________________P01.CSV` | CSV (214,895 B) | Level 3 Calibrated Mast Air Temp (1.45m) | NASA PDS4 RDR (`data_calibrated_env/sol_0010`) | `2b334af75ad4...` | **VERIFIED** |
| `LMD_CNES_MCD_V6_2_JEZERO` | `data/environment/raw/mcd/jezero_mcd_v6_2.nc` | NetCDF3 (365,184 B) | Numerical GCM Climatological Reanalysis | Laboratoire de Météorologie Dynamique (LMD/CNES) | `3c3bd5a870d5...` | **VERIFIED** |
| `MRO_MCS_LEVEL5_JEZERO_PROFILES` | `data/environment/raw/mcs/mro_mcs_jezero_profiles.json` | JSON (31,460 B) | Level 5 DDR Vertical Sounding Profiles | NASA PDS Geosciences / MRO Mars Climate Sounder | `6632001b4ca0...` | **VERIFIED** |

---

## 3. Forensic Evaluation of Ingested Datasets

### 3.1 Mars 2020 Perseverance MEDA Archives
- **Distinction between Logs and Observational Telemetry:** The five daily CSV files (`derived_PS.csv`, `derived_TRS.csv`, `derived_RHS.csv`, `derived_wind.csv`, `calibrated_ATS.csv`) are genuine PDS log/catalog index files maintained by the PDS Atmospheres Node. They record exact URNs, start/stop UTC times, mission elapsed sols, LMST, LTST, $L_s$, and file volumes across 1,527 sols.
- **High-Frequency Observational Verification:** The Sol 10 files (`WE__0010___________DER_TIRS________________P04.CSV` and `WE__0010___________CAL_ATS_________________P01.CSV`) contain genuine, un-interpolated PDS4 RDR records:
  - TIRS records contain calibrated downward and upward longwave irradiances ($\text{W/m}^2$) and 8 physical screening flags (`RSM_HEAD_OUTSIDE_TIRS_UPWARD_LOOKING_FOV`, `TIRS_GROUND_FOOTPRINT_NOT_IN_SHADOW`, `ROVER_STILL`, etc.).
  - ATS records contain 5 separate Resistance Temperature Detector (RTD) sensors located at $1.45\text{ m}$ height on the rover Remote Sensing Mast (RSM).
- **Physical Accuracy Verdict:** All variables preserve authentic SI units ($\text{Pa}$, $\text{K}$, $\text{W/m}^2$, $\text{m/s}$) and comply with PDS4 standards.

### 3.2 MRO Mars Climate Sounder (MCS) Vertical Profiles
- **Remote Sensing vs In-Situ Ground Truth:** MCS is an orbital limb-sounding infrared radiometer operating from a Sun-synchronous orbit at $\approx 250\text{–}320\text{ km}$ altitude. Limb retrievals capture atmospheric temperature $T(p, z)$ and aerosol extinction from $1\text{ km}$ above the surface up to $80\text{ km}$.
- **Methodological Guardrail:** The Tribunal confirms that Milestone 13M correctly avoids treating MCS as a surface weather station. MCS soundings are utilized exclusively in Experiment C for evaluating free-tropospheric vertical lapse rates ($\Gamma = -\frac{dT}{dz}$), which is physically valid.

### 3.3 LMD Mars Climate Database (MCD v6.2) NetCDF Climatology
- **Model vs Observation Separation:** MCD v6.2 is a numerical General Circulation Model (GCM) reanalysis driven by Mars Global Surveyor (TES) and Mars Reconnaissance Orbiter (MCS) orbital dust scenarios. It is **NOT** a collection of independent in-situ surface weather measurements.
- **Circularity Prevention:** Milestone 13M properly formulates MCD v6.2 as the **target model under evaluation** and uses Perseverance MEDA as the **independent observational truth**. There is zero circular evaluation in the pipeline.
- **Spatiotemporal Granularity:** MCD represents a monthly diurnal climatology ($12\text{ months } \times 24\text{ hours}$). It cannot and does not resolve individual sub-diurnal convective gusts or micro-topographic shadow transitions.

---

## 4. Final Data Forensics Verdict

All 9 products reported in Milestone 13M exist on disk, match their cryptographic SHA-256 digests exactly, and adhere to planetary data standards.

**Tribunal Forensic Verdict:** `ALL 9 PRODUCTS VERIFIED`
