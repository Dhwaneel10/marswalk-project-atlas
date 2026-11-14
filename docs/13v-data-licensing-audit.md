# Milestone 13V: Open-Source Software & Data Licensing Forensic Audit

**Document ID:** `ATLAS-DOC-LIC-AUDIT`  
**Classification:** Legal & Licensing Due Diligence  
**Repository:** [`E:/Python/NASA-Spaceapps/Marswalk`](file:///e:/Python/NASA-Spaceapps/Marswalk)

---

## 1. Executive Licensing Summary

A comprehensive forensic audit of all runtime dependencies, development tools, web assets, and remote-sensing datasets within Project Atlas was conducted.

**Findings:**
1. **Zero Copyleft Encroachment:** No components under GPL, AGPL, or SSPL are present in the dependency tree.
2. **Permissive Ecosystem:** All Python dependencies are licensed under MIT, BSD 3-Clause, or Apache 2.0.
3. **Public Domain Datasets:** All elevation models, optical mosaics, and atmospheric records originate from NASA, USGS, or IAU public domain releases.
4. **Recommended Project License:** The **Apache License 2.0** or **MIT License** is recommended for Project Atlas, guaranteeing complete compatibility with all upstream sources while protecting the authors with express liability disclaimers.

---

## 2. Dependency Audit Matrix

| Package / Asset | Upstream Provider | License | Compatibility Status | Commercial / Research Use |
|:---|:---|:---|:---:|:---:|
| **numpy** | NumPy Developers | BSD 3-Clause | **COMPATIBLE** | Unrestricted |
| **scipy** | SciPy Developers | BSD 3-Clause | **COMPATIBLE** | Unrestricted |
| **rasterio** | Mapbox | BSD 3-Clause | **COMPATIBLE** | Unrestricted |
| **affine** | Sean Gillies | BSD 3-Clause | **COMPATIBLE** | Unrestricted |
| **jsonschema** | Julian Berman | MIT | **COMPATIBLE** | Unrestricted |
| **requests** | Kenneth Reitz | Apache 2.0 | **COMPATIBLE** | Unrestricted |
| **websockets** | Aymeric Augustin | BSD 3-Clause | **COMPATIBLE** | Unrestricted |
| **pytest** | Holger Krekel | MIT | **COMPATIBLE** | Unrestricted |
| **Three.js** | Ricardo Cabello (mrdoob) | MIT | **COMPATIBLE** | Unrestricted |
| **USGS 20m DTM** | USGS Astrogeology | Public Domain (US Gov) | **COMPATIBLE** | Unrestricted |
| **MEDA Weather** | NASA PDS / CSIC-INTA | Public Domain (NASA) | **COMPATIBLE** | Unrestricted |

---

## 3. Disclaimers & Attribution Enforcement

In strict compliance with 17 U.S.C. § 105 and NASA Open Data policies:
- Project Atlas does not claim ownership or copyright over NASA or USGS raw imagery or elevation data.
- Proper attribution is preserved in all exports, Decision Packs, and user-facing dashboards.
- A prominent disclaimer is included in all exports: *"This computational research simulation is independently developed and is not endorsed or certified by NASA, JPL, or the USGS."*
