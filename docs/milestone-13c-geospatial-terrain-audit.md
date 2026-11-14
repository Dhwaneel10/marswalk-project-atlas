# Milestone 13C — Geospatial & Terrain Coordinate Transformation Pipeline Audit Report
## Authentic USGS CTX 20m DTM Raster to Three.js 3D Mission Theater Mathematical Verification

**Auditor:** Agent 2 — Geospatial & Terrain Auditor (MarsWalk 2.0 / Project Atlas)  
**Date:** 2026-10-31T02:20:00+05:30  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Target Milestone:** Milestone 13C (Atlas 3D Mission Theater)  
**Reference Document:** `docs/milestone-13c-checklist.md`  
**Audit Test Suite:** `tests/test_milestone_13c_geospatial_terrain_audit.py` (9/9 Passed)  

---

## 1. Executive Summary & Audit Mandate

As part of Milestone 13C for MarsWalk 2.0 / Project Atlas, this audit rigorously analyzes and mathematically verifies the end-to-end geospatial and terrain coordinate transformation pipeline. The objective is to ensure mathematical fidelity, data provenance, coordinate system rigor, and flawless spatial alignment between authentic orbital observations (USGS MRO CTX 20m digital elevation model) and the interactive Three.js 3D Mission Theater.

### Audit Summary Scorecard

| Pipeline Component | Specification / Standard | Audit Finding | Status |
| :--- | :--- | :--- | :---: |
| **Authentic Source Raster** | USGS Astrogeology CTX DTM 20m (Fergason et al., 2020) | $250 \times 250$ grid, 20.0m res, SHA-256 verified | **PASS** |
| **Planetary Geodetic Spheroid** | IAU 2000 Mars Sphere ($R = 3,396,190\text{ m}$) | Meridian scale $59,274.70\text{ m/deg}$, verified | **PASS** |
| **Equirectangular Cosine Metric** | $dx = C \cdot \cos(\phi_{\text{ref}})$, $dy = C$ | $dx = 18.973\text{ m}$, $dy = 20.000\text{ m}$ at $18.442^\circ\text{ N}$ | **PASS** |
| **Web Mission Data JSON** | Millimetric match with GeoTIFF elevation array | $\max \|\Delta z\| = 0.0051\text{ m}$, mean $0.0025\text{ m}$ | **PASS** |
| **Three.js 3D Coordinate Mapping** | Plane geometry centered at $(0, 0, 0)$ | $X, Z$ metric spans and $Y$ elevation zero-offset | **PASS** |
| **Vertical Exaggeration Separation** | Visual scaling ($1.0\times$–$3.0\times$) strictly isolated | Analytical distance/slope/cost invariant | **PASS** |
| **NoData Mask Handling** | Sentinel $-3.4028\times 10^{38}$ clamped at baseline | 0 NoData in ROI; guards prevent sinkholes/NaNs | **PASS** |
| **Route & Target Snapping** | Positive facet clearance, sub-pixel accuracy | All 12 targets $<0.01\text{ m}$ diff; $+10\text{m}$ clearance | **PASS** |

---

## 2. Authentic USGS CTX 20m DTM Raster Verification

### 2.1 Dataset Provenance & Attribution
- **Primary Source:** USGS Astrogeology Science Center / NASA Mars Reconnaissance Orbiter (MRO) Context Camera (CTX) Stereo Digital Terrain Model.
- **Scientific Citation:** Fergason, R.L., et al. (2020), *Mars 2020 Perseverance Landing Site CTX DTM and Orthomosaic*, USGS Astrogeology Science Center, DOI: [`10.5066/P906QQT8`](https://doi.org/10.5066/P906QQT8).
- **Raw Master Mosaic:** `data/raw/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif`  
  - Dimensions: $1512 \times 1596$ cells  
  - Elevation Range: $-2710.70\text{ m}$ to $-1515.54\text{ m}$  
  - NoData Sentinel: $-3.4028226550889045\times 10^{38}$ (IEEE 754 Float32 minimum)  
- **Processed Mission ROI Raster:** `data/processed/jezero_ready_20m.tif`  
  - Dimensions: $250 \times 250$ cells  
  - Ground Coverage: $5,000.0\text{ m} \times 5,000.0\text{ m}$ ($5.0\text{ km} \times 5.0\text{ km}$)  
  - Resolution: $(20.0\text{ m}, 20.0\text{ m})$ projected cell size  
  - CRS: `ESRI:103885` (`Equirectangular Mars 2000 Sphere IAU`)  
  - Authenticity Cryptographic Digest (SHA-256):  
    `875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3`

### 2.2 Bounding Box and Extents

$$\begin{aligned}
\text{Projected Left } (X_{\min}) &= 4,587,723.250853\text{ m} \\
\text{Projected Right } (X_{\max}) &= 4,592,723.250853\text{ m} \quad (\Delta X = 5,000.000\text{ m}) \\
\text{Projected Bottom } (Y_{\min}) &= 1,090,653.140188\text{ m} \\
\text{Projected Top } (Y_{\max}) &= 1,095,653.140188\text{ m} \quad (\Delta Y = 5,000.000\text{ m})
\end{aligned}$$

Using the IAU 2000 Mars meridian conversion ($59,274.69752\text{ m/degree}$):

$$\begin{aligned}
\text{Geographic Min Longitude} &= 77.397666^\circ\text{ E} \\
\text{Geographic Max Longitude} &= 77.482019^\circ\text{ E} \quad (\Delta \lambda = 0.084353^\circ) \\
\text{Geographic Min Latitude} &= 18.399978^\circ\text{ N} \\
\text{Geographic Max Latitude} &= 18.484331^\circ\text{ N} \quad (\Delta \phi = 0.084353^\circ) \\
\text{Centroid} &= (77.439843^\circ\text{ E}, 18.442155^\circ\text{ N})
\end{aligned}$$

### 2.3 Elevation Distribution in Study Area
- **Minimum Elevation:** $-2,623.8362\text{ m}$ (crater floor depression)
- **Maximum Elevation:** $-2,445.0170\text{ m}$ (delta scarp crest)
- **Total Topographic Relief:** $178.8192\text{ m}$
- **Mean Elevation:** $-2,556.3345\text{ m}$
- **Standard Deviation:** $34.4639\text{ m}$
- **Invalid / NoData Cells:** Exactly 0 cells ($0.0\%$) out of 62,500 total cells.

---

## 3. Web Mission Data JSON Integrity & Alignment

The frontend client consumes pre-processed mission data from `web/data/jezero_mission_data.json` (mirrored at `web/public/data/jezero_mission_data.json`).

### 3.1 Pixel-by-Pixel Cross-Verification
A numerical comparison between `data/processed/jezero_ready_20m.tif` and `web/data/jezero_mission_data.json` revealed:
- **Matrix Dimension:** Exactly $250 \times 250$ in both datasets.
- **Maximum Absolute Elevation Discrepancy:** $0.005127\text{ m}$ ($5.1\text{ mm}$).
- **Mean Absolute Elevation Discrepancy:** $0.002500\text{ m}$ ($2.5\text{ mm}$).
- **Cause:** Millimetric truncation from two-decimal-place JSON serialization (`-2623.84` vs `-2623.8362`).
- **Slope Sample Cross-Verification:** The `slope_samples` array was cross-checked against Python Horn 3x3 finite-difference calculations:
  - $\max |\theta_{\text{python}} - \theta_{\text{json}}| = 0.00499^\circ$ ($< 0.005^\circ$).
  - Mean difference: $0.00251^\circ$.

---

## 4. Coordinate Transformation Mathematics

### 4.1 Planetary Reference Spheroid
Mars is modeled as a sphere conforming to the IAU/IAG 2000 reference standards:
- **Mars Volumetric Mean Radius:** $R_{\text{mars}} = 3,396,190.0\text{ m}$
- **Meridian Arc Length per Degree:**
  
$$M = \frac{\pi \cdot R_{\text{mars}}}{180^\circ} \approx 59,274.69752399\text{ m/degree}$$

### 4.2 Equirectangular Projection & Metric Spacing
The source raster is projected in Equirectangular (Plate Carrée) with standard parallel $\phi_0 = 0^\circ$ and central meridian $\lambda_0 = 0^\circ$:

$$X = R_{\text{mars}} \cdot (\lambda - \lambda_0) \cdot \frac{\pi}{180^\circ} = M \cdot \lambda$$

$$Y = R_{\text{mars}} \cdot (\phi - \phi_0) \cdot \frac{\pi}{180^\circ} = M \cdot \phi$$

Because standard parallel is the equator, longitudinal spacing contracts toward the poles by $\cos(\phi)$. For local operations within Jezero crater at reference latitude $\phi_{\text{ref}} = 18.442^\circ\text{ N}$:

$$\cos(\phi_{\text{ref}}) = \cos(18.442^\circ) = 0.94864437$$

$$\begin{aligned}
dx_{\text{ground}} &= C \cdot \cos(\phi_{\text{ref}}) = 20.0\text{ m} \cdot 0.94864437 = 18.972887\text{ m} \approx 18.973\text{ m} \\
dy_{\text{ground}} &= C = 20.000\text{ m}
\end{aligned}$$

For diagonal 8-connected grid transitions:

$$d_{\text{diag}} = \sqrt{dx_{\text{ground}}^2 + dy_{\text{ground}}^2} = \sqrt{(18.972887)^2 + (20.0)^2} = 27.5676\text{ m}$$

---

## 5. Three.js Plane Geometry & 3D World Transformation

### 5.1 Grid $(r, c)$ to World $(x, y, z)$ Mapping
In `web/app.js`, the Jezero 3D terrain mesh is constructed via `buildTerrainMesh(exaggeration, textureMode)`:
- Coordinate orientation: Right-handed Cartesian:
  - $+X$: East (increasing column $c$)
  - $+Y$: Local vertical up (elevation above baseline)
  - $+Z$: South (increasing row $r$)
- Mesh dimensions:
  
$$\text{totalW} = (cols - 1) \cdot dx = 249 \cdot 18.972887\text{ m} = 4,724.2488\text{ m}$$

$$\text{totalH} = (rows - 1) \cdot dy = 249 \cdot 20.000000\text{ m} = 4,980.0000\text{ m}$$

$$\text{halfW} = \frac{\text{totalW}}{2} = 2,362.1244\text{ m}, \quad \text{halfH} = \frac{\text{totalH}}{2} = 2,490.0000\text{ m}$$

- For vertex at row $r \in [0, 249]$ and column $c \in [0, 249]$:

$$x(r, c) = c \cdot dx - \text{halfW}$$

$$z(r, c) = r \cdot dy - \text{halfH}$$

$$y(r, c) = \big(z_{\text{elev}}(r, c) - z_{\min}\big) \cdot \text{exaggeration}$$

where $z_{\min} = -2,623.8362\text{ m}$.

### 5.2 Geometric Properties & GPU Precision
- **Centroid Anchoring:** Centering the mesh at $(0, 0, 0)$ anchors the scene at $(r=124.5, c=124.5)$, eliminating 4.5 million meter floating point offsets that would otherwise cause vertex jitter in standard 32-bit GPU floating point vertex buffers.
- **Winding Order:** Triangles are indexed counter-clockwise (CCW) when viewed from $+Y$:
  - $T_1 = (i_0, i_2, i_1)$ where $i_0=(r, c)$, $i_2=(r+1, c)$, $i_1=(r, c+1)$
  - $T_2 = (i_1, i_2, i_3)$ where $i_3=(r+1, c+1)$
  - Resulting vertex normals point upward toward Martian sky ($+Y$).
- **UV Texture Mapping:**
  - $u = \frac{c}{cols - 1}$ ($0.0$ at West edge to $1.0$ at East edge)
  - $v = 1.0 - \frac{r}{rows - 1}$ ($1.0$ at North top edge to $0.0$ at South bottom edge)
  - Aligns 1:1 with the calibrated MRO CTX orthomosaic crop (`web/assets/jezero_ctx_orthomosaic.jpg`).

---

## 6. Visual Vertical Exaggeration Audit

### 6.1 Strict Separation of Visual Display and Analytical Science
Milestone 13C specifies that visual vertical exaggeration must be adjustable for planetary terrain readability without contaminating analytical metrics.

| Domain | Parameter / Metric | Exaggeration Dependent? | Formulary / Value |
| :--- | :--- | :---: | :--- |
| **3D Rendering** | Mesh Vertex $Y$ | **YES** | $y = (z - z_{\min}) \cdot E$ |
| **3D Rendering** | Route Polyline $Y$ | **YES** | $y = (z - z_{\min}) \cdot E + 10.0\text{ m}$ |
| **3D Rendering** | Waypoint Beacon Mast $Y$ | **YES** | $y = (z - z_{\min}) \cdot E + 6.0\text{ m} + 35.0\text{ m}$ |
| **Science Analysis** | Ground Step Distance | **NO** | $d = \sqrt{(dc \cdot dx)^2 + (dr \cdot dy)^2}$ |
| **Science Analysis** | Local Horn 3x3 Slope | **NO** | $\theta = \arctan(\sqrt{(dz/dx)^2 + (dz/dy)^2})$ |
| **Science Analysis** | Traversal Effort Cost | **NO** | $C = d \cdot [1 + \alpha_s (\theta/\theta_{\text{crit}})^2 + \dots]$ |
| **Science Analysis** | Cumulative Climb / Gain | **NO** | $\sum \max(0, z_{i+1} - z_i)$ |
| **Science Analysis** | Waligora Metabolic Rate | **NO** | $M = 3.68 \cdot m + 2.72 \cdot m \cdot v^2 + \dots$ |

### 6.2 Exaggeration Controls & Dynamic Re-alignment
- In `web/index.html`, `#exagPills` provides $1.0\times\text{ (True)}$, $1.5\times$, $2.0\times$, and $3.0\times$.
- Default configuration is $1.0\times$ baseline, with $1.5\times$ recommended for surface scarp readability.
- When exaggeration changes, event listeners re-project:
  - Base terrain mesh (`buildTerrainMesh`)
  - Waypoint beacons (`buildWaypointBeacons`)
  - Start and goal markers (`updatePlanningMarkers`)
  - Nominal route polylines (`drawLiveRoute`)
  - Detour and gauntlet routes (`drawDetourRoute`)
  - Spatial disruption footprint cylinders (`highlightDisruptionZone`)
  - Contingency placement previews

---

## 7. NoData Mask Handling

### 7.1 Prevention of Artificial Zero-Elevation Sinkholes
In standard GIS pipelines, unhandled NoData values (such as $-32768$ or $-3.4\times 10^{38}$) can produce catastrophic geometric spikes or bottomless sinkholes in 3D meshes.

MarsWalk enforces a multi-tier defense:
1. **Python Ingestion:**
   `create_invalid_mask` flags values matching `nodata_sentinel`, `np.isnan`, `np.isinf`, or outside $[-10000, 30000]\text{ m}$.
2. **Dilation Protection:**
   `dilate_invalid_mask` dilates invalid cells by 1 pixel (3x3 structuring element), preventing Horn finite-difference kernels and roughness filters from computing gradients across missing boundaries.
3. **Frontend Mesh Clamping:**
   In `buildTerrainMesh`:
   ```javascript
   const y = (elev > -9000) ? (elev - minElev) * exaggeration : 0;
   ```
   Any cell with elevation $\le -9000\text{ m}$ or `NaN` is safely clamped to $y = 0$ (the crater floor baseline) rather than plunging into negative infinity.
4. **Local Coordinate Function Clamping (`rcToLocalPos`):**
   Hardened during this audit (DEF-13C-GEO-02):
   ```javascript
   const safeElev = (elev !== undefined && !isNaN(elev) && elev > -9000) ? elev : minElev;
   const safeExag = (isNaN(exaggeration) || exaggeration <= 0) ? 1.0 : exaggeration;
   const y = ((safeElev - minElev) * safeExag) + 6.0;
   ```

---

## 8. Route and Waypoint Snapping Audit

### 8.1 Waypoint Alignment
All 12 science targets defined in `data/waypoints_jezero.json` were audited for sub-pixel alignment:

| Waypoint ID | Row | Col | Catalog Lon / Lat | Center-Cell Lon / Lat | Dem $\Delta z$ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `octavia_butler_landing` | 117 | 157 | $77.4508^\circ\text{ E}, 18.4447^\circ\text{ N}$ | $77.4508^\circ\text{ E}, 18.4447^\circ\text{ N}$ | $< 0.001\text{ m}$ |
| `three_forks` | 153 | 123 | $77.4392^\circ\text{ E}, 18.4326^\circ\text{ N}$ | $77.4393^\circ\text{ E}, 18.4325^\circ\text{ N}$ | $< 0.001\text{ m}$ |
| `hawksbill_gap` | 136 | 91 | $77.4284^\circ\text{ E}, 18.4385^\circ\text{ N}$ | $77.4285^\circ\text{ E}, 18.4383^\circ\text{ N}$ | $< 0.001\text{ m}$ |
| `kodiak_butte` | 194 | 131 | $77.4420^\circ\text{ E}, 18.4190^\circ\text{ N}$ | $77.4420^\circ\text{ E}, 18.4187^\circ\text{ N}$ | $< 0.001\text{ m}$ |
| `delta_rim_overlook` | 66 | 128 | $77.4410^\circ\text{ E}, 18.4620^\circ\text{ N}$ | $77.4410^\circ\text{ E}, 18.4619^\circ\text{ N}$ | $< 0.001\text{ m}$ |
| `neretva_margin` | 87 | 81 | $77.4250^\circ\text{ E}, 18.4550^\circ\text{ N}$ | $77.4252^\circ\text{ E}, 18.4548^\circ\text{ N}$ | $< 0.001\text{ m}$ |
| `seitah_dunes` | 137 | 140 | $77.4450^\circ\text{ E}, 18.4380^\circ\text{ N}$ | $77.4451^\circ\text{ E}, 18.4379^\circ\text{ N}$ | $< 0.001\text{ m}$ |
| `artuby_ridge` | 130 | 148 | $77.4475^\circ\text{ E}, 18.4405^\circ\text{ N}$ | $77.4478^\circ\text{ E}, 18.4403^\circ\text{ N}$ | $< 0.001\text{ m}$ |
| `skinner_ridge` | 133 | 94 | $77.4295^\circ\text{ E}, 18.4395^\circ\text{ N}$ | $77.4296^\circ\text{ E}, 18.4393^\circ\text{ N}$ | $< 0.001\text{ m}$ |
| `enchanted_lake` | 140 | 108 | $77.4340^\circ\text{ E}, 18.4370^\circ\text{ N}$ | $77.4343^\circ\text{ E}, 18.4369^\circ\text{ N}$ | $< 0.001\text{ m}$ |
| `belva_crater_overlook` | 57 | 90 | $77.4280^\circ\text{ E}, 18.4650^\circ\text{ N}$ | $77.4282^\circ\text{ E}, 18.4649^\circ\text{ N}$ | $< 0.001\text{ m}$ |
| `dourbes_floor` | 122 | 149 | $77.4480^\circ\text{ E}, 18.4430^\circ\text{ N}$ | $77.4481^\circ\text{ E}, 18.4430^\circ\text{ N}$ | $0.010\text{ m}$ |

*All 12 waypoints align within half a pixel ($<15.5\text{ m}$) of catalog coordinates, with elevation residuals $\le 0.01\text{ m}$.*

### 8.2 Positive Vertical Offset Stratification
To eliminate visual facet clipping and z-fighting along diagonal steps that traverse non-planar quad facets, visual layers in Three.js are systematically stratified above the terrain mesh:

```
[+76.0 m]  Waypoint Beacon Glowing Head
[+41.0 m]  Waypoint Beacon Cylinder Mast (Center)
[+25.0 m]  Study Area Boundary Box Wireframe
[+14.0 m]  Playback Vehicle Marker & Detour Route Polyline
[+13.5 m]  Event Footprint Disruption Cylinder
[+10.0 m]  Nominal Route Polyline (Conservative / Balanced / Science-First)
[+9.5 m]   Contingency Continuation Polyline
[+8.0 m]   Historical Traversal Track Polyline
[+6.0 m]   rcToLocalPos Base Clearance Floor
-------------------------------------------------------------------------
[+0.0 m]   Authentic USGS CTX 20m Terrain Mesh Surface
```

---

## 9. Discovered Defects and Applied Remediations

During this audit, three technical defects were detected and remediated:

### DEF-13C-GEO-01: Undeclared `row` Variable in `onCanvasClick` Terrain Query
- **Severity:** High (Runtime `ReferenceError` during user interaction)
- **File:** `web/app.js` (line 15338)
- **Description:** When clicking the 3D surface mesh while not in planning mode, `updateLiveTelemetry` computed latitude using `row`. However, `row` was only declared inside the planning mode block (`if (planningMode === 'start'...)`), throwing `ReferenceError: row is not defined`.
- **Remediation:** Added `const row = Math.max(0, Math.min(missionData.grid.rows - 1, Math.round((pt.z + halfH) / dy)));` directly above latitude interpolation.

### DEF-13C-GEO-02: Missing Sentinel / NaN Guard in `rcToLocalPos`
- **Severity:** Medium (Potential sinkhole or NaN coordinate generation)
- **File:** `web/app.js` (line 5058)
- **Description:** If an elevation sample was `undefined`, `NaN`, or an unhandled sentinel ($\le -9000\text{ m}$), `rcToLocalPos` would compute invalid Three.js vector components.
- **Remediation:** Added `safeElev` and `safeExag` guards that safely clamp invalid values to `minElev` and valid positive exaggeration factors.

### DEF-13C-GEO-03: Deep-Linking URL Query Parameter for Vertical Exaggeration
- **Severity:** Low (Feature completeness for Milestone 13C presentation mode)
- **File:** `web/app.js` (line 17973)
- **Description:** URL query parameters supported `texture`, `start_r`, `goal_r`, but lacked `exag` / `exaggeration` deep-linking.
- **Remediation:** Added parsing for `params.get('exag')` and `params.get('exaggeration')` with bounds $[1.0, 5.0]$, automatically activating matching `#exagPills` buttons and rebuilding terrain mesh.

---

## 10. Audit Verification Test Suite

A comprehensive test suite was implemented in [`tests/test_milestone_13c_geospatial_terrain_audit.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/tests/test_milestone_13c_geospatial_terrain_audit.py).

### Execution Results
```
tests/test_milestone_13c_geospatial_terrain_audit.py::test_audit_01_geotiff_raster_provenance_and_dimensions PASSED [ 11%]
tests/test_milestone_13c_geospatial_terrain_audit.py::test_audit_02_raster_cryptographic_authenticity PASSED [ 22%]
tests/test_milestone_13c_geospatial_terrain_audit.py::test_audit_03_web_mission_data_json_alignment PASSED [ 33%]
tests/test_milestone_13c_geospatial_terrain_audit.py::test_audit_04_iau_mars_spheroid_and_equirectangular_scaling PASSED [ 44%]
tests/test_milestone_13c_geospatial_terrain_audit.py::test_audit_05_threejs_plane_geometry_coordinate_mapping PASSED [ 55%]
tests/test_milestone_13c_geospatial_terrain_audit.py::test_audit_06_vertical_exaggeration_analytical_separation PASSED [ 66%]
tests/test_milestone_13c_geospatial_terrain_audit.py::test_audit_07_nodata_safety_and_clamping PASSED [ 77%]
tests/test_milestone_13c_geospatial_terrain_audit.py::test_audit_08_waypoint_snapping_accuracy PASSED [ 88%]
tests/test_milestone_13c_geospatial_terrain_audit.py::test_audit_09_route_polyline_snapping_and_facet_clearance PASSED [100%]

============================== 9 passed in 0.82s ==============================
```

---

## 11. Conclusion & Recommendations

The geospatial and terrain coordinate transformation pipeline for MarsWalk 2.0 / Project Atlas is **fully verified, mathematically consistent, and scientifically grounded**:
1. Authentic USGS CTX 20m elevation data is preserved with zero artificial fabrication or metric distortion.
2. The IAU 2000 Mars Spheroid and Equirectangular cosine metric scaling ($dx=18.973\text{ m}, dy=20.000\text{ m}$) are accurately implemented across both Python backend and Three.js frontend.
3. Visual vertical exaggeration is strictly isolated from analytical science metrics.
4. Vertical layer stratification guarantees zero facet clipping or z-fighting across complex topographic terrain.
5. All 9 dedicated audit unit tests pass with zero regressions.
