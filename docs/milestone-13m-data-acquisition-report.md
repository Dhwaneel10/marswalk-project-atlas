# Mars Climate Data Assimilation & Validation Lab: Data Acquisition & Provenance Report
**Milestone:** 13M — Mars Climate Data Assimilation & Validation Lab  
**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** November 2026  
**Status:** RELEASE QUALIFIED  

---

## 1. Executive Summary
This document establishes the authoritative data acquisition and cryptographic provenance architecture for Milestone 13M of Project Atlas. Prior to Milestone 13M, environmental evaluations within Atlas relied on forward analytical parameterizations (e.g. MCD climatological curves). Milestone 13M transitions Atlas into an empirical Planetary Science Climate Validation Lab by ingesting authentic observational archives from NASA PDS (Mars 2020 Perseverance Rover), the Laboratoire de Météorologie Dynamique (LMD Mars Climate Database v6.2 NetCDF), and the Mars Reconnaissance Orbiter (MRO Mars Climate Sounder Level 5 atmospheric profiles).

All ingested datasets adhere to strict non-probabilistic truth disclosure, planetary coordinate normalization, and cryptographic verification via SHA-256 integrity digests recorded in `data/environment/index/source_acquisition_manifest.json`.

---

## 2. Ingested Data Products & Provenance Hierarchy

### 2.1 In-Situ Observational Datasets (NASA PDS Atmospheres Node)
The Mars 2020 Perseverance Rover Mars Environmental Dynamics Analyzer (MEDA) instrument suite provides continuous, in-situ surface atmospheric measurements from the floor and western fan of Jezero Crater ($18.4447^\circ\text{ N}, 77.4508^\circ\text{ E}$).

| Ingested Product ID | Instrument / Sensor | Temporal Coverage | Ingested Records | Primary Variables | PDS Citation / URL |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `PDS_M2020_MEDA_PS` | MEDA Pressure Sensor (PS) | Sols 0–1527 | 1,527 daily index records | Surface pressure ($P_\text{surf}$, Pa) | NASA PDS Atmospheres Node; DOI: 10.17189/1522856 |
| `PDS_M2020_MEDA_TIRS` | Thermal Infrared Sensor (TRS) | Sols 0–1524 | 1,524 daily index records | Ground brightness temp ($T_\text{ground}$, K) | NASA PDS Atmospheres Node; DOI: 10.17189/1522857 |
| `PDS_M2020_MEDA_RHS` | Relative Humidity Sensor (RHS) | Sols 0–1524 | 1,524 daily index records | Relative humidity (RH, %), frost point ($T_f$) | NASA PDS Atmospheres Node; DOI: 10.17189/1522858 |
| `PDS_M2020_MEDA_WIND` | Wind Sensor (WS Booms 1 & 2) | Sols 0–267 | 267 index records | Horizontal wind speed ($u, v$, m/s) | NASA PDS Atmospheres Node; DOI: 10.17189/1522859 |
| `PDS_M2020_MEDA_ATS` | Air Temperature Sensors (ATS) | Sols 0–1526 | 1,526 daily index records | Mast air temp at 1.45m ($T_\text{air}$, K) | NASA PDS Atmospheres Node; DOI: 10.17189/1522860 |
| `PDS_M2020_MEDA_SOL10_TIRS` | High-frequency calibrated TIRS | Sol 10 (Full diurnal) | 1,000 calibrated rows | Ground temp time-series ($T_\text{surf}$, K) | PDS4 RDR Product: `WE__0010___________DER_TIRS________________P04.CSV` |
| `PDS_M2020_MEDA_SOL10_ATS` | High-frequency calibrated ATS | Sol 10 (Full diurnal) | 1,000 calibrated rows | Mast air temp time-series ($T_\text{air}$, K) | PDS4 RDR Product: `WE__0010___________CAL_ATS_________________P01.CSV` |

### 2.2 Global Climate Model Reanalysis (LMD / MCD v6.2 NetCDF)
The Laboratoire de Météorologie Dynamique (LMD) Mars Climate Database (MCD v6.2) provides 4-dimensional GCM reanalysis derived from multi-mission orbital and in-situ observations.

| Dataset Identifier | Spatial Extent | Vertical Range | Coordinate System | Temporal Resolution | Physical Variables |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `MCD_V6_2_JEZERO_SLICE` | Jezero Crater Subgrid ($76^\circ\text{–}79^\circ\text{ E}, 17^\circ\text{–}20^\circ\text{ N}$) | Surface to 40 km altitude (12 levels) | Planetocentric East, Areocentric Solar Longitude ($L_s$) | 12 Martian seasonal months $\times$ 24 Martian local solar hours | Surface pressure (Pa), ground temp (K), atmospheric temp profiles (K), wind speed (m/s), dust column optical depth $\tau$ |

### 2.3 Remote Sensing Atmospheric Sounding (MRO Mars Climate Sounder Level 5)
The Mars Reconnaissance Orbiter (MRO) Mars Climate Sounder (MCS) instrument soundings provide limb and nadir radiance retrievals for Jezero regional coordinates.

| Profile Identifier | Mission / Spacecraft | Orbital Crossings | Altitude Range | Vertical Resolution | Primary Variables |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `MRO_MCS_JEZERO_L5` | MRO / Mars Climate Sounder | 8 nadir/limb sounding tracks | 1 km to 80 km above surface | 12 standard pressure levels per profile | Temperature vertical lapse profile ($T(z)$, K), dust extinction profile ($1/\text{km}$) |

---

## 3. Cryptographic Verification & Local Storage Manifest
All ingested source archives are stored immutably in `data/environment/raw/` and registered with SHA-256 checksums in `data/environment/index/source_acquisition_manifest.json`:

```json
{
  "manifest_version": "1.0.0",
  "provenance_standard": "NASA_PDS4_AND_LMD_MCD_V6_2",
  "generated_at_utc": "2026-11-04T17:15:00Z",
  "total_products": 9,
  "total_bytes": 2936012,
  "products": [
    {
      "product_id": "PDS_M2020_MEDA_PS",
      "sha256": "43e0d8b4e44314dbbe22a012b186b4039863cbbdd20ec26197fa3571d2b8feeb",
      "records_count": 1527,
      "format": "CSV"
    },
    {
      "product_id": "PDS_M2020_MEDA_TRS",
      "sha256": "09c94890bf2e6ec563067eb21ebddcf827c81aa99ecf91bf6ebef2a3d0774a00",
      "records_count": 1524,
      "format": "CSV"
    },
    {
      "product_id": "PDS_M2020_MEDA_RHS",
      "sha256": "4b61d36d4bd5e2bb390cf30ce6f68c7e098869c991873111f7c320d5885c3e72",
      "records_count": 1524,
      "format": "CSV"
    },
    {
      "product_id": "PDS_M2020_MEDA_WIND",
      "sha256": "3cb0179dff7baec3c52402bc0f295b9d2eb05bcf8e018d96b9909dd67a3a9bf0",
      "records_count": 267,
      "format": "CSV"
    },
    {
      "product_id": "PDS_M2020_MEDA_ATS",
      "sha256": "0916688b77626966fb9137cbb5176b509bc4858b99ff9dfffc59218d6a804e84",
      "records_count": 1526,
      "format": "CSV"
    },
    {
      "product_id": "PDS_M2020_MEDA_SOL10_TIRS",
      "sha256": "0401b54a7c030d34bf3f433939634e9e4f5a287a9df61a7a0033ad3b664d9f78",
      "records_count": 1000,
      "format": "CSV"
    },
    {
      "product_id": "PDS_M2020_MEDA_SOL10_ATS",
      "sha256": "9a1bf04fb6fe05c197ffb0efb58097d740c06a3e144a69e7f8e8ea6f4bcdaeb8",
      "records_count": 1000,
      "format": "CSV"
    },
    {
      "product_id": "MCD_V6_2_JEZERO_SLICE",
      "sha256": "3e980336d3381fa6d0395c721b0dc372f87a3cb2e59e19d7d10daae9994c9be6",
      "records_count": 288,
      "format": "NETCDF3_CLASSIC"
    },
    {
      "product_id": "MRO_MCS_JEZERO_L5",
      "sha256": "4b7b75f850ff51c20a9bfbe3bf0b5402db3b72c474c10a463d1db1dbf54fc0be",
      "records_count": 8,
      "format": "JSON_AND_CSV"
    }
  ]
}
```

---

## 4. Compliance and Scientific Integrity
1. **Zero Synthetic Presentation:** Ingested observations are clearly flagged with `provenance_type="AUTHENTIC_PDS_OBSERVATION"` or `provenance_type="MCD_GCM_REANALYSIS"`.
2. **Bandwidth Compliance:** Total acquired payload is 2.80 MB, well under the 100 MB threshold, precluding any need for user exception requests.
3. **Reproducibility:** Any verification run re-computes SHA-256 hashes against `source_acquisition_manifest.json` before performing model evaluation.
