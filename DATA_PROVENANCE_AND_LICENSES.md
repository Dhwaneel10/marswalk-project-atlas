# Planetary Data Provenance, Licensing & Redistribution Rights

**Project:** Project Atlas / MarsWalk 2.0  
**Repository:** [`E:/Python/NASA-Spaceapps/Marswalk`](file:///e:/Python/NASA-Spaceapps/Marswalk)  
**Standard:** Open Data & NASA Scientific Attribution Policy

---

## 1. Remote-Sensing Datasets

### 1. USGS Jezero Crater Digital Terrain Model (20m DTM)
- **Local Path:** `data/processed/jezero_ready_20m.tif` (also archived in `data/raw/`)
- **Cryptographic Hash (SHA-256):** `875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3`
- **Data Provider:** United States Geological Survey (USGS) Astrogeology Science Center / NASA Mars Reconnaissance Orbiter (MRO) Context Camera (CTX).
- **Persistent Identifier:** USGS Astrogeology Jezero DTM (DeltaGeoid 20m Equirectangular projection).
- **Licensing Status:** Public Domain (United States Government Work under 17 U.S.C. § 105).
- **Attribution Requirement:** "USGS Astrogeology Science Center / NASA / JPL-Caltech / MSSS".
- **Redistribution Rights:** Unrestricted public redistribution and derivative generation permitted worldwide.
- **Usage Restrictions:** None.

---

### 2. NASA PDS4 MEDA Atmospheric Archives
- **Local Source:** `data/science/meda/`
- **Data Provider:** NASA Planetary Data System (PDS) Geosciences & Atmospheres Nodes / Centro de Astrobiología (CSIC-INTA).
- **Persistent Identifier:** `urn:nasa:pds:mars2020_meda`
- **Licensing Status:** Public Domain (NASA Open Data Policy).
- **Attribution Requirement:** "NASA / JPL-Caltech / Centro de Astrobiología (CSIC-INTA)".
- **Redistribution Rights:** Unrestricted public redistribution.
- **Usage Restrictions:** None.

---

### 3. USGS Viking MDIM 2.1 & MOLA Global Elevation Map
- **Local Path:** `data/imagery/`
- **Data Provider:** USGS Astrogeology Science Center / NASA Mars Global Surveyor (MGS) MOLA Team.
- **Licensing Status:** Public Domain (U.S. Government Work).
- **Attribution Requirement:** "NASA / USGS Astrogeology / GSFC".
- **Redistribution Rights:** Unrestricted public redistribution.

---

### 4. IAU Gazetteer of Planetary Nomenclature
- **Local Path:** `data/gazetteer/iau_features.json`
- **Data Provider:** International Astronomical Union (IAU) Working Group for Planetary System Nomenclature (WGPSN) in cooperation with USGS Astrogeology.
- **Licensing Status:** Open Public Scientific Data.
- **Attribution Requirement:** "IAU WGPSN / USGS Gazetteer of Planetary Nomenclature".

---

## 2. Data Governance & Storage Policy

1. **No Synthetic Topography:** All elevation profiles must be derived from verified public domain rasters.
2. **Local Cache Policy:** Ingested rasters are stored locally within `data/` to allow bit-exact offline reproducibility.
3. **Immutability:** Primary raw GeoTIFF files are treated as read-only canonical baselines.
