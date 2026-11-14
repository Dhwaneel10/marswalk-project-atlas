# MarsWalk 2.0 — Milestone 9O Planetary Imagery & Regional Exploration Audit
## Comprehensive Spatial Resolution, Provenance, and Geographic Registration Analysis

**Document Version:** 1.0.0  
**Date:** 2026-10-18  
**Author:** Principal Planetary GIS Engineer & Scientific Visualization Architect  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  

---

## 1. Executive Summary

Milestone 9O audits the existing planetary imagery pipeline of MarsWalk 2.0, establishing a rigorous, scientifically traceable distinction between:
1. **Original Source Sensor Resolution:** The native optical resolving power of the instrument (e.g., MRO Context Camera ~6.0 m/px, Viking Orbiter VIS ~232 m/px, MGS MOLA ~463 m/px).
2. **Global Basemap Resolution:** The macro-scale base sphere texture draped over the global Mars globe (Viking MDIM 2.1 at 232 m/px).
3. **Tile-Matrix Zoom Level:** The spatial sampling of the Equirectangular WMTS tile matrix (Level 6 = ~651.2 m/px, Level 7 = ~325.6 m/px, Level 12 = ~10.17 m/px).
4. **Local Preview Asset Dimensions:** The exact pixel dimensions and spatial footprints of pre-rendered preview textures stored under `web/assets/`.
5. **Elevation Grid Spacing:** The digital elevation model cell size (20 m/cell in Jezero Crater vs 463 m macro-datum globally).

> [!IMPORTANT]
> **Core Scientific Principle:** An image crop's pixel width (e.g., 512×512) must never be conflated with its scientific resolving power. Nor may visual contrast enhancement or colorization of monochrome CTX data be presented as natural Martian surface reflectance.

---

## 2. Multi-Scale Regional Coverage Matrix

The four featured destinations exhibit distinctly different data availability, sensor provenance, and mission support:

| Attribute | 1. Jezero Crater | 2. Olympus Mons | 3. Valles Marineris | 4. Gale Crater |
| :--- | :--- | :--- | :--- | :--- |
| **Feature Category** | Impact Crater / Paleolake Delta | Shield Volcano & Caldera | Canyon System (Coprates/Capri) | Impact Crater / Central Mound |
| **Catalog Place ID** | `iau_14300` / `landing_perseverance` | `iau_4453` | `iau_6288` | `iau_2071` / `landing_curiosity` |
| **Target Coordinates** | 18.4422° N, 77.4398° E | 18.6500° N, 226.2000° E (-133.8000° W) | -14.0100° S, -58.5900° W (canyon center) | -5.3500° S, 137.8000° E |
| **Optical Source Product** | USGS SIM 3467 CTX Orthomosaic | NASA Mars Trek `olympus_mons.eq` | NASA Mars Trek `SE_Marineris_CTX_BlockAdj_dd` | NASA Mars Trek `Gale_CTX_BlockAdj_dd` |
| **Sensor / Mission** | MRO Context Camera (CTX) | MRO Context Camera (CTX) | MRO Context Camera (CTX) | MRO Context Camera (CTX) |
| **Source Sensor Resolution**| 6.0 m/px (optical baseline) | ~6.0 m/px (nadir) | ~6.0 m/px (nadir) | ~6.0 m/px (nadir) |
| **Display Texture Sampling**| 4.88 m/px (draped on 5×5 km mesh) | Level 6 (~651 m/px) / Level 7 (~326 m/px) | Level 6 (~651 m/px) / Level 7 (~326 m/px) | Level 6 (~651 m/px) / Level 7 (~326 m/px) |
| **Stitched Asset Path** | `web/assets/jezero_ctx_orthomosaic.jpg` | `web/assets/olympus_mons_ctx_preview.jpg` | `web/assets/valles_marineris_ctx_preview.jpg` | `web/assets/gale_crater_ctx_preview.jpg` |
| **Asset Pixel Dimensions**| 1024 × 1024 pixels (RGB, 152 KB) | 512 × 512 pixels (RGB, 32.3 KB) | 512 × 512 pixels (RGB, 36.0 KB) | 512 × 512 pixels (RGB, 51.1 KB) |
| **Asset Tile Selection** | Pre-projected Equirectangular GeoTIFF | Z=6, rows=[25, 26], cols=[16, 17] | Z=6, rows=[38, 39], cols=[45, 46] | Z=6, rows=[33, 34], cols=[112, 113] |
| **Exact Texture Footprint** | Lon: [77.3977°, 77.4820°]<br>Lat: [18.4000°, 18.4843°] | Lon: [-135.0000°, -129.3750°]<br>Lat: [14.0625°, 19.6875°] | Lon: [-53.4375°, -47.8125°]<br>Lat: [-22.5000°, -16.8750°] | Lon: [135.0000°, 140.6250°]<br>Lat: [-8.4375°, -2.8125°] |
| **Overall Region Bounds** | Lon: [77.1605°, 77.6992°]<br>Lat: [18.2110°, 18.7212°] | Lon: [-136.0000°, -124.0000°]<br>Lat: [12.0000°, 24.0000°] | Lon: [-78.0000°, -40.0000°]<br>Lat: [-25.0000°, -5.0000°] | Lon: [135.1843°, 139.2413°]<br>Lat: [-6.5733°, -2.8078°] |
| **Digital Elevation Model** | **USGS CTX 20 m DTM** (`jezero_ready_20m.tif`)| **None (MGS MOLA 463 m Macro-Datum)** | **None (MGS MOLA 463 m Macro-Datum)** | **None (MGS MOLA 463 m Macro-Datum)** |
| **Elevation Resolution** | 20.0 m/cell ground spacing | 463.0 m/cell (global basemap only) | 463.0 m/cell (global basemap only) | 463.0 m/cell (global basemap only) |
| **Elevation Range (Datum)**| -2,623.8 m to -2,445.0 m | +14,000 m to +21,287 m | -7,000 m to +2,000 m | -4,500 m to +5,500 m |
| **Traverse Planning?** | **YES (Python A*, Slope Hazards)** | **NO (Visual & Cartographic Exploration)** | **NO (Visual & Cartographic Exploration)** | **NO (Visual & Cartographic Exploration)** |
| **Scientific Limitations** | Restricted strictly to 5×5 km study box | Summit caldera optical draped on sphere | Southeast sector (Coprates/Capri wall strata) | Optical mosaic of crater floor & Aeolis Mons |

---

## 3. Mathematical Foundations of Martian Equirectangular Tiling

NASA Mars Trek tiles are delivered in **Equirectangular Projection (EPSG:104905 / IAU Mars 2000 Sphere)**:
- Mars Reference Radius: $R_{\text{Mars}} = 3,396,190.0\text{ m}$.
- Planetary Circumference: $C = 2 \pi R_{\text{Mars}} \approx 21,338,885.26\text{ m}$.
- Tiling Scheme: At zoom level $Z$, the globe is divided into $W = 2^{Z+1}$ columns and $H = 2^Z$ rows.
- Each tile consists of $256 \times 256$ pixels.
- Angular span per tile:
  $$\Delta \theta = \frac{360^\circ}{W} = \frac{180^\circ}{2^Z}$$
- Ground resolution at the equator:
  $$\text{GSD}_0 = \frac{C}{W \times 256} = \frac{21,338,885.26}{2^{Z+1} \times 256}\text{ meters/pixel}$$

### Tiling Resolution Ladder
- **Zoom Level 0:** 1 tile high, 2 tiles wide. $\Delta \theta = 180^\circ$. $\text{GSD} \approx 41.68\text{ km/pixel}$.
- **Zoom Level 6:** 64 tiles high, 128 tiles wide. $\Delta \theta = 2.8125^\circ$. $\text{GSD} \approx 651.2\text{ m/pixel}$.
- **Zoom Level 7:** 128 tiles high, 256 tiles wide. $\Delta \theta = 1.40625^\circ$. $\text{GSD} \approx 325.6\text{ m/pixel}$.
- **Zoom Level 8:** 256 tiles high, 512 tiles wide. $\Delta \theta = 0.703125^\circ$. $\text{GSD} \approx 162.8\text{ m/pixel}$.
- **Zoom Level 12 (Native CTX):** 4,096 tiles high, 8,192 tiles wide. $\Delta \theta \approx 0.0439^\circ$. $\text{GSD} \approx 10.17\text{ m/pixel}$.

### Tile Coordinate Conversion Functions
For a planetary coordinate $(\lambda, \phi)$ where $\lambda \in [-180^\circ, 180^\circ]$ (east longitude) and $\phi \in [-90^\circ, 90^\circ]$ (planetocentric latitude):
$$\text{col} = \left\lfloor \frac{\lambda + 180^\circ}{\Delta \theta} \right\rfloor = \left\lfloor \frac{\lambda + 180^\circ}{180^\circ} \times 2^Z \right\rfloor$$
$$\text{row} = \left\lfloor \frac{90^\circ - \phi}{\Delta \theta} \right\rfloor = \left\lfloor \frac{90^\circ - \phi}{180^\circ} \times 2^Z \right\rfloor$$

Tile spatial bounding box $[\lambda_{\min}, \lambda_{\max}, \phi_{\min}, \phi_{\max}]$:
$$\lambda_{\min} = -180^\circ + \text{col} \times \Delta \theta, \quad \lambda_{\max} = \lambda_{\min} + \Delta \theta$$
$$\phi_{\max} = 90^\circ - \text{row} \times \Delta \theta, \quad \phi_{\min} = \phi_{\max} - \Delta \theta$$

---

## 4. Analysis of Existing Registration and Rendering Pipelines

### 4.1 Root Cause of Regional Patch Distortion
In Milestone 9M/9N, `createRegionalCurvedPatch(product, texture)` in `web/app.js` derived its spherical geometry strictly from `product.bounds`:
```javascript
const minLon = product.bounds.min_lon_deg;
const maxLon = product.bounds.max_lon_deg;
const minLat = product.bounds.min_lat_deg;
const maxLat = product.bounds.max_lat_deg;
```
For Valles Marineris, `product.bounds` was configured as:
`min_lon: -78.0°, max_lon: -40.0°, min_lat: -25.0°, max_lat: -5.0°` (a $38^\circ \times 20^\circ$ geographic area).
However, `valles_marineris_ctx_preview.jpg` was generated from a $2 \times 2$ tile stitch at Level 6:
`rows=[38, 39], cols=[45, 46]`, covering strictly `lon: [-53.4375°, -47.8125°], lat: [-22.5000°, -16.8750°]` (a $5.625^\circ \times 5.625^\circ$ area).

**Distortion Effect:**
A $5.625^\circ \times 5.625^\circ$ image patch was stretched over a $38^\circ \times 20^\circ$ spherical mesh, magnifying the image by ~7× horizontally and ~3.5× vertically!

**Solution in Milestone 9O:**
Introduce `texture_bounds` in the registry and `createRegionalCurvedPatch`:
```javascript
const bounds = product.texture_bounds || product.bounds;
```
This guarantees that each pre-stitched or cached texture is draped with sub-pixel geographic registration precisely matching its true Martian footprint.

### 4.2 Contrast Enhancement and False Color Transparency
Monochrome CTX images (single optical channel, 500–800 nm broad passband) were colorized using a warm tri-color gradient:
`black="#22120C", mid="#9A5430", white="#EFB287"`.
While this aids cartographic integration with the underlying Viking color basemap, **it must be disclosed explicitly** to users:
- The colorization is a synthetic perceptual enhancement.
- The true CTX observation is a single-band grayscale reflectance measurement.

---

## 5. Architectural Requirements for Milestone 9O

1. **Consistent Imagery Registry:**
   Update `web/data/mars_imagery_registry.json` and `src/marswalk/data/imagery_registry.py` with explicit `texture_bounds`, `native_sensor_resolution_m`, `display_sampling_m`, `color_interpretation`, and `elevation_capabilities`.
2. **Safe Python Tile Cache Server:**
   Implement `src/marswalk/data/tile_cache.py` with allowlist enforcement, atomic file replacement, and transparent cache hit/miss headers (`X-MarsWalk-Cache: HIT|MISS`).
3. **Progressive Regional Detail:**
   In `web/app.js`, support progressive refinement: instant local preview -> seamless transition to higher-detail tiles when available.
4. **Transparent Location Dossier Telemetry:**
   Update `#locationCard` to clearly report native sensor resolution vs tile zoom level, and distinguish optical imagery from elevation constraints.
