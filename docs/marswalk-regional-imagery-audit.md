# MarsWalk 2.0 — Planetary Regional Imagery & Products Audit
## Technical Verification and Spatial Provenance of Featured Destinations

**Project:** MarsWalk 2.0 — Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** October 18, 2026  
**Auditor:** Planetary GIS Engineer & Mission Systems Verification Engineer  

---

## 1. Executive Summary

This audit assesses the spatial resolution, geographic bounds, raster dimensions, storage mode, and elevation model capabilities for the four featured exploration destinations in MarsWalk 2.0:
1. **Jezero Crater** (Perseverance Touchdown & Delta Corridor)
2. **Olympus Mons** (Tharsis Volcanic Shield & Summit Caldera)
3. **Valles Marineris** (Equatorial Canyon System / Coprates Chasma)
4. **Gale Crater** (Curiosity Roving Area & Mount Sharp Base)

> [!IMPORTANT]
> **Scientific Integrity Disclosure:** MarsWalk strictly distinguishes between true digital elevation models (DEM/DTM) that support surface slope modeling and route calculation versus optical 2D orthomosaics. Only Jezero Crater possesses high-resolution $20\text{ m}$ digital elevation data in the current release. The other three regions provide authentic NASA Context Camera (CTX) regional optical previews with macro-scale MOLA elevation context, with route planning appropriately disabled to prevent fictitious navigational claims.

---

## 2. Comprehensive Destination Products Audit

### Product 1: Jezero Crater Study Boundary

| Property | Value / Verification |
| :--- | :--- |
| **Product ID** | `jezero_ctx_local_mesh` |
| **Registry Layer Type** | `local_mesh_ortho` |
| **Primary Source** | USGS Astrogeology Science Center / NASA Mars 2020 Perseverance Science Team / MRO CTX Team (Fergason et al., 2020) |
| **Attribution** | USGS Astrogeology / NASA JPL-Caltech / MSSS |
| **Primary Citation** | Fergason, R.L. et al. (2020), *USGS Scientific Investigations Map 3467*; DOI: [10.5066/P906QQT8](https://doi.org/10.5066/P906QQT8) |
| **Nominal Spatial Resolution** | **Elevation DTM:** $20.0\text{ m/cell}$ ground spacing ($250 \times 250$ grid).<br>**Optical Orthomosaic:** $6.0\text{ m/pixel}$ (Texture sampling ground spacing $\sim 4.88\text{ m/px}$). |
| **Geographic Bounds** | **Min Lon:** $77.397666^\circ\text{ E}$ &bull; **Max Lon:** $77.482019^\circ\text{ E}$<br>**Min Lat:** $18.399978^\circ\text{ N}$ &bull; **Max Lat:** $18.484331^\circ\text{ N}$<br>**Center:** $77.439843^\circ\text{ E}, 18.442155^\circ\text{ N}$ |
| **Projected Dimensions** | $5,000.0\text{ m}$ Width $\times 5,000.0\text{ m}$ Height ($25\text{ km}^2$ study quadrangle) |
| **Actual Image Dimensions** | $1024 \times 1024$ pixels, 8-bit RGB JPEG (`web/assets/jezero_ctx_orthomosaic.jpg`, 148.4 KB) |
| **Storage & Delivery Mode** | Local bundled asset in repository, pre-packaged for zero-latency offline loading. |
| **Elevation Data Availability** | **ACTIVE & VERIFIED.** Genuine $250 \times 250$ elevation grid derived from USGS CTX DTM GeoTIFF (`elevation_min`: $-2,623.84\text{ m}$, `elevation_max`: $-2,445.02\text{ m}$). Live Python A* route planning supported. |
| **Preprocessing Performed** | Extracted from Fergason et al. (2020) GeoTIFF, re-projected to IAU Mars 2000 Equirectangular coordinates, normalized for Three.js heightmap vertices, draped with matched $6\text{ m/px}$ CTX orthomosaic. |
| **Limitations** | Route planning is strictly confined to this $5 \times 5\text{ km}$ surveyed boundary. Traverses outside this quadrangle are disallowed by the API. |

---

### Product 2: Olympus Mons Summit Caldera & Volcanic Shield

| Property | Value / Verification |
| :--- | :--- |
| **Product ID** | `olympus_mons_ctx_regional` |
| **Registry Layer Type** | `regional_mosaic` |
| **Primary Source** | NASA Mars Trek WMTS / MRO CTX Science Team (`olympus_mons.eq`) |
| **Attribution** | NASA / JPL-Caltech / MSSS / USGS Astrogeology |
| **Primary Citation** | Malin, M.C. et al. (2007), *Context Camera Investigation on board the Mars Reconnaissance Orbiter*, J. Geophys. Res. 112, E05S04; DOI: 10.1029/2006JE002808 |
| **Nominal Spatial Resolution** | **Optical Source:** $6.0\text{ m/pixel}$ controlled CTX mosaic.<br>**Preview Rendering:** Zoom Level 6 ($512 \times 512$ stitched preview). |
| **Geographic Bounds** | **Min Lon:** $-136.0^\circ\text{ W}$ ($224.0^\circ\text{ E}$) &bull; **Max Lon:** $-124.0^\circ\text{ W}$ ($236.0^\circ\text{ E}$)<br>**Min Lat:** $12.0^\circ\text{ N}$ &bull; **Max Lat:** $24.0^\circ\text{ N}$<br>**Caldera Center:** $18.65^\circ\text{ N}, -133.8^\circ\text{ W}$ |
| **Actual Image Dimensions** | $512 \times 512$ pixels, 8-bit RGB JPEG (`web/assets/olympus_mons_ctx_preview.jpg`, 31.6 KB) |
| **Storage & Delivery Mode** | Local bundled preview in `web/assets/`, with live RESTful WMTS fallback to NASA Mars Trek tile service (`https://trek.nasa.gov/tiles/Mars/EQ/olympus_mons.eq/`). |
| **Elevation Data Availability** | **GLOBAL DATUM ONLY.** No localized high-resolution CTX DTM is integrated. Global MOLA altimetry ($463\text{ m/cell}$) provides macro-scale vertical context. Route planning is disabled. |
| **Preprocessing Performed** | Stitched 4 tiles ($2 \times 2$ matrix: Z=6, rows [25, 26], cols [16, 17]) from NASA Mars Trek WMTS via `scripts/prepare_regional_imagery.py`, contrast-enhanced, and colorized with Mars orbital mineral palette. |
| **Limitations** | Covers the summit caldera collapse structures, volcanic lava terraces, and flank cliffs. No operational surface routing. |

---

### Product 3: Valles Marineris (Coprates & Capri Chasma)

| Property | Value / Verification |
| :--- | :--- |
| **Product ID** | `valles_marineris_ctx_regional` |
| **Registry Layer Type** | `regional_mosaic` |
| **Primary Source** | NASA Mars Trek WMTS / MRO CTX Science Team (`SE_Marineris_CTX_BlockAdj_dd`) |
| **Attribution** | NASA / JPL-Caltech / MSSS / USGS Astrogeology |
| **Primary Citation** | Malin, M.C. et al. (2007), *Context Camera Investigation on board the Mars Reconnaissance Orbiter*, J. Geophys. Res. 112. |
| **Nominal Spatial Resolution** | **Optical Source:** $6.0\text{ m/pixel}$ controlled CTX mosaic.<br>**Preview Rendering:** Zoom Level 6 ($512 \times 512$ stitched preview). |
| **Geographic Bounds** | **Tile Extent:** $-53.4375^\circ\text{ W}$ to $-47.8125^\circ\text{ W}$ Lon, $-22.5^\circ\text{ S}$ to $-16.875^\circ\text{ S}$ Lat<br>**Regional Coverage:** $-78.0^\circ\text{ W}$ to $-40.0^\circ\text{ W}$ Lon, $-25.0^\circ\text{ S}$ to $-5.0^\circ\text{ S}$ Lat |
| **Actual Image Dimensions** | $512 \times 512$ pixels, 8-bit RGB JPEG (`web/assets/valles_marineris_ctx_preview.jpg`, 36.0 KB) |
| **Storage & Delivery Mode** | Local bundled preview in `web/assets/` freshly updated from authentic CTX tiles via `scripts/prepare_regional_imagery.py`, with WMTS tile template fallback to NASA Mars Trek. |
| **Elevation Data Availability** | **GLOBAL DATUM ONLY.** Global MGS MOLA elevation datum only. Canyon depths exceed $8,000\text{ m}$, but micro-slope rover navigation is not available. |
| **Preprocessing Performed** | Upgraded from previous Milestone 9M Viking global basemap crop: fetched 4 authentic CTX tiles from NASA Mars Trek (`SE_Marineris_CTX_BlockAdj_dd`, Z=6, rows [38, 39], cols [45, 46]), stitched, contrast-calibrated, and colorized. |
| **Limitations** | Resolves mega-landslides, wall spur stratification, and canyon floor deposits along Coprates Chasma. Route planning is disabled. |

---

### Product 4: Gale Crater (Curiosity Landing & Mount Sharp Corridor)

| Property | Value / Verification |
| :--- | :--- |
| **Product ID** | `gale_crater_ctx_regional` |
| **Registry Layer Type** | `regional_mosaic` |
| **Primary Source** | NASA Mars Trek WMTS / MRO CTX Science Team (`Gale_CTX_BlockAdj_dd`) |
| **Attribution** | NASA / JPL-Caltech / MSSS / USGS Astrogeology |
| **Primary Citation** | Malin, M.C. et al. (2007), *Context Camera Investigation on board the Mars Reconnaissance Orbiter*, J. Geophys. Res. 112, E05S04. |
| **Nominal Spatial Resolution** | **Optical Source:** $6.0\text{ m/pixel}$ controlled CTX mosaic.<br>**Preview Rendering:** Zoom Level 6 ($512 \times 512$ stitched preview). |
| **Geographic Bounds** | **Min Lon:** $135.184259^\circ\text{ E}$ &bull; **Max Lon:** $139.241301^\circ\text{ E}$<br>**Min Lat:** $-6.573299^\circ\text{ S}$ &bull; **Max Lat:** $-2.807781^\circ\text{ S}$<br>**Bradbury Landing:** $137.4417^\circ\text{ E}, -4.5895^\circ\text{ S}$ |
| **Actual Image Dimensions** | $512 \times 512$ pixels, 8-bit RGB JPEG (`web/assets/gale_crater_ctx_preview.jpg`, 49.9 KB) |
| **Storage & Delivery Mode** | Local bundled preview in `web/assets/`, with WMTS tile template fallback to NASA Mars Trek (`Gale_CTX_BlockAdj_dd`). |
| **Elevation Data Availability** | **GLOBAL DATUM ONLY.** Global MGS MOLA datum only. Route planning is disabled. |
| **Preprocessing Performed** | Stitched 4 tiles ($2 \times 2$ matrix: Z=6, rows [33, 34], cols [112, 113]) from NASA Mars Trek WMTS via `scripts/prepare_regional_imagery.py`, contrast-enhanced, and colorized. |
| **Limitations** | Visualizes Bradbury Landing, Peace Vallis fan, Bagnold Dunes, and the lower clay/sulfate-bearing layered strata of Mount Sharp (Aeolis Mons). Surface routing is disabled. |

---

## 3. Comparative Summary Matrix

| Destination | Optical Product | Ground Res | Image Size | Local DTM? | Route Planning? | Storage Mode |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Jezero Crater** | USGS CTX Orthomosaic | $6.0\text{ m/px}$ | $1024 \times 1024$ | **Yes** ($20\text{ m}$) | **Supported** | Local repository asset |
| **Olympus Mons** | MRO CTX `olympus_mons.eq` | $6.0\text{ m/px}$ | $512 \times 512$ | No (MOLA only) | Disabled | Local preview + WMTS |
| **Valles Marineris** | MRO CTX `SE_Marineris` | $6.0\text{ m/px}$ | $512 \times 512$ | No (MOLA only) | Disabled | Local preview + WMTS |
| **Gale Crater** | MRO CTX `Gale_CTX_dd` | $6.0\text{ m/px}$ | $512 \times 512$ | No (MOLA only) | Disabled | Local preview + WMTS |

This audit confirms that all four destinations are now backed by genuine NASA MRO CTX optical imagery products, and that their capabilities and coverage limitations are truthfully documented.
