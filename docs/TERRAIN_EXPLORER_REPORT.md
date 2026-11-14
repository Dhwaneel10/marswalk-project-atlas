# MULTI-SCALE TERRAIN EXPLORER &amp; GEOSPATIAL AUDIT
## Project MarsWalk / Atlas — Mission 5 Terrain System

**Document Version:** 1.0.0  
**Status:** QUALIFIED &amp; VERIFIED  
**Date:** 2026-11-14  
**Workspace:** `/home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission`  
**Primary Coordinate Reference System:** Equirectangular Mars Sphere (IAU 2000, $R = 3,396,190\,\text{m}$, ESRI:103885)  

---

## 1. MULTI-SCALE TERRAIN ARCHITECTURE

MarsWalk 2.0 implements a dual-resolution hierarchical elevation model over Jezero Crater:

1. **Regional Context DEM (USGS CTX 20m):**
   * **Product ID:** `USGS_CTX_DEM_PROCESSED_20M`
   * **Source:** Fergusson et al. (2020), USGS Astrogeology Science Center, DOI: [10.5066/P9T31O12](https://doi.org/10.5066/P9T31O12).
   * **Dimensions:** $250 \times 250$ grid cells ($5,000\,\text{m} \times 5,000\,\text{m}$ ground footprint).
   * **Spatial Resolution:** $20.0\,\text{m/pixel}$.
   * **Projected Extent:** Easting $[4,587,723.25, 4,592,723.25]\,\text{m}$, Northing $[1,090,653.14, 1,095,653.14]\,\text{m}$.
   * **Planetocentric Extent:** Longitude $[77.39767^\circ\,\text{E}, 77.48202^\circ\,\text{E}]$, Latitude $[18.39998^\circ\,\text{N}, 18.48433^\circ\,\text{N}]$.
   * **Elevation Range:** $-2,608.0\,\text{m}$ to $-2,382.4\,\text{m}$ relative to the MOLA areoid.
   * **SHA-256 Hash:** `024c0d027f311c1d3c0e3a67732a30bbdfb88ef68da8cf7f45ec63feea32bbff`.

2. **Micro-Hazard DTM (USGS TRN HiRISE 1m):**
   * **Product ID:** `USGS_TRN_HIRISE_1M`
   * **Source:** Bland et al. (2024), USGS Terrain Relative Navigation (TRN) Project, DOI: [10.5066/P13CPYYU](https://doi.org/10.5066/P13CPYYU).
   * **Dimensions:** $600 \times 600$ grid cells ($600\,\text{m} \times 600\,\text{m}$ ground footprint).
   * **Spatial Resolution:** $1.0\,\text{m/pixel}$.
   * **Target Corridor:** Hawksbill Gap Delta Scarp &amp; Wildcat Ridge Organic Core Site.
   * **Projected Extent:** Easting $[4,589,243.0, 4,589,843.0]\,\text{m}$, Northing $[1,092,633.0, 1,093,233.0]\,\text{m}$.
   * **Planetocentric Extent:** Longitude $[77.42331^\circ\,\text{E}, 77.43343^\circ\,\text{E}]$, Latitude $[18.43338^\circ\,\text{N}, 18.44350^\circ\,\text{N}]$.
   * **Elevation Range:** $-2,581.4\,\text{m}$ to $-2,514.8\,\text{m}$ relative to the MOLA areoid.
   * **SHA-256 Hash:** `b084920210e7b8f95c479493544aa3fcfa46d655f05df399c752ba17ae7a8120`.

```
===================================================================================
USGS CTX 20m Exploration Corridor (5000m x 5000m, 250 x 250 px)
-----------------------------------------------------------------------------------
[Row 0, Col 0]                                             [Row 0, Col 249]
  +-------------------------------------------------------------+
  |                                                             |
  |             Hawksbill Gap HiRISE 1m Window                  |
  |             Rows [121, 151], Cols [76, 106]                 |
  |             (600m x 600m, 600 x 600 px)                     |
  |                 +---------------+                           |
  |                 | Wildcat Ridge |                           |
  |                 | (136, 91)     |                           |
  |                 +---------------+                           |
  |                                                             |
  |   Three Forks Depot                                         |
  |   (Row 116, Col 156)                                        |
  |                                                             |
  +-------------------------------------------------------------+
[Row 249, Col 0]                                           [Row 249, Col 249]
===================================================================================
```

---

## 2. GEODETIC ALIGNMENT &amp; CONTROL POINT AUDIT

The HiRISE $600\,\text{m} \times 600\,\text{m}$ raster nests exactly within the CTX 20m coordinate envelope. The alignment was verified across 5 geodetic control points (4 corners and the center Wildcat Ridge core site):

| Control Point | Projected Coords $(X, Y)\,\text{m}$ | Planetocentric Coords | CTX $(R, C)$ | HiRISE Elev | CTX Elev | $\Delta z$ | Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Northwest Corner** | $(4589243, 1093233)$ | $77.42331^\circ\,\text{E}, 18.44350^\circ\,\text{N}$ | $(121, 76)$ | $-2573.57\,\text{m}$ | $-2571.49\,\text{m}$ | $-2.08\,\text{m}$ | **VERIFIED** |
| **Northeast Corner** | $(4589843, 1093233)$ | $77.43343^\circ\,\text{E}, 18.44350^\circ\,\text{N}$ | $(121, 106)$ | $-2524.31\,\text{m}$ | $-2520.17\,\text{m}$ | $-4.14\,\text{m}$ | **VERIFIED** |
| **Southeast Corner** | $(4589843, 1092633)$ | $77.43343^\circ\,\text{E}, 18.43338^\circ\,\text{N}$ | $(151, 106)$ | $-2535.80\,\text{m}$ | $-2530.71\,\text{m}$ | $-5.09\,\text{m}$ | **VERIFIED** |
| **Southwest Corner** | $(4589243, 1092633)$ | $77.42331^\circ\,\text{E}, 18.43338^\circ\,\text{N}$ | $(151, 76)$ | $-2572.88\,\text{m}$ | $-2572.45\,\text{m}$ | $-0.43\,\text{m}$ | **VERIFIED** |
| **Wildcat Ridge Center** | $(4589543, 1092933)$ | $77.42837^\circ\,\text{E}, 18.43844^\circ\,\text{N}$ | $(136, 91)$ | $-2554.69\,\text{m}$ | $-2550.82\,\text{m}$ | $-3.87\,\text{m}$ | **VERIFIED** |

### Mathematical Significance of $\Delta z$:
The elevation deltas range strictly between $-0.43\,\text{m}$ and $-5.09\,\text{m}$ ($\text{mean} = -3.12\,\text{m}$). This is consistent with known photogrammetric stereo bundle adjustment offsets between independent CTX regional stereo models and TRN HiRISE sub-pixel tied triangulations. No artificial translation or datum shift is applied, preserving the original USGS archive fidelity.

---

## 3. HORN GRADIENT SLOPE ALGORITHM &amp; HAZARD TIERS

Surface steepness is calculated using Horn’s $3 \times 3$ finite-difference convolution operator, which weights orthogonal and diagonal adjacent elevation values:

$$\frac{\partial z}{\partial x} = \frac{(z_{i-1, j+1} + 2z_{i, j+1} + z_{i+1, j+1}) - (z_{i-1, j-1} + 2z_{i, j-1} + z_{i+1, j-1})}{8 \cdot \Delta x}$$

$$\frac{\partial z}{\partial y} = \frac{(z_{i-1, j-1} + 2z_{i-1, j} + z_{i-1, j+1}) - (z_{i+1, j-1} + 2z_{i+1, j} + z_{i+1, j+1})}{8 \cdot \Delta y}$$

$$\theta_{\text{slope}} = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right) \cdot \frac{180^\circ}{\pi}$$

### Hazard Classification Thresholds:
* **Nominal ($\theta < 8^\circ$):** Traversable by all wheeled rovers and simulated human EVA units.
* **Caution ($8^\circ \le \theta < 15^\circ$):** Requires terramechanical slip compensation; rover speed reduced by 40%.
* **Critical Hazard ($\theta \ge 15^\circ$):** Impassable barrier; high risk of rollover or wheel trenching. The Multi-Objective A\* planner applies severe path penalties or hard exclusions.

---

## 4. RESOLUTION-AWARE POINT INSPECTOR API

The backend exposes `POST /api/pillars/terrain/inspect`. The engine performs spatial indexing to determine whether the queried coordinate falls within the HiRISE 1m micro-hazard boundary or the regional CTX base:

### Query Example (Hawksbill Gap):
```bash
curl -X POST http://127.0.0.1:3000/api/pillars/terrain/inspect \
  -H "Content-Type: application/json" \
  -d '{"row": 136, "col": 91}'
```
### Response:
```json
{
  "easting_m": 4589543.25,
  "northing_m": 1092933.14,
  "lon_deg": 77.428371,
  "lat_deg": 18.438443,
  "active_dataset": "USGS_TRN_HIRISE_1M",
  "resolution_m": 1.0,
  "is_high_resolution": true,
  "elevation_m": -2554.69,
  "slope_deg": 9.39,
  "hazard_tier": "CAUTION",
  "base_ctx_elevation_m": -2550.82,
  "elevation_delta_m": -3.87,
  "provenance_citation": "Bland et al. (2024), USGS TRN HiRISE DTM, DOI: 10.5066/P13CPYYU",
  "coverage_context": "Within 600m Hawksbill Gap Ascent Channel"
}
```

---

## 5. 3D VISUALIZATION &amp; SPATIAL RAYCASTING

In the 3D surface workstation:
1. **HiRISE Footprint Mesh (`hiriseBoundaryMesh`):** A cyan boundary box delineates the exact $600\,\text{m} \times 600\,\text{m}$ Hawksbill Gap window.
2. **Interactive Toggles:** Checkboxes in Tab 2 allow operators to toggle HiRISE bounds, historical traverse tracks, sample depot tubes, and astrobiology targets.
3. **Spatial Raycasting:** Clicking anywhere on the 3D surface fires a raycast query through the Three.js mesh, extracting grid row/col, planetocentric coordinates, elevation, Horn slope, and the active dataset attribution.

---

## 6. SCIENTIFIC INTEGRITY &amp; OPERATIONAL BOUNDARIES

> [!CAUTION]
> **Operational Safety Disclaimer:**  
> All slope, traversal, and terrain hazard classifications are mathematical models derived from orbital photogrammetry (USGS CTX and HiRISE). While calibrated against real Martian datasets, **these routes must never be designated as operationally safe for human astronauts or flight rovers**. Sub-pixel obstacles (boulders $<1\,\text{m}$, loose sand ripples, and regolith bearing-capacity variations) require in-situ tactical hazard camera confirmation.
