# Project MarsWalk 2.0 / Atlas — NASA Planetary Data Provenance & Geodetic Standards

**Document ID:** `ATLAS-DOC-PROV-001`  
**Classification:** Scientific Methodology & Geodesy Standards  
**Mission Phase:** Mission 4 — Real NASA Data Integration & Five-Pillar Upgrade  
**Authority:** IAU Working Group on Cartographic Coordinates, USGS Astrogeology, NASA PDS  

---

## 1. Geodetic Datum & Planetary Reference Frame

All geospatial operations in Project MarsWalk 2.0 / Atlas are strictly referenced to the **IAU 2000 Mars Spheroid** as standardized by the International Astronomical Union (IAU) / International Association of Geodesy (IAG) Working Group on Cartographic Coordinates and Rotational Elements.

### 1.1 Spheroid Constants
- **Equatorial Radius ($a$ / Semi-major axis):** $3,396,190.0\,\text{m}$ ($3,396.190\,\text{km}$)
- **Polar Radius ($c$ / Semi-minor axis):** $3,376,200.0\,\text{m}$ ($3,376.200\,\text{km}$)
- **Flattening ($f$):**
  $$f = \frac{a - c}{a} = \frac{3396190.0 - 3376200.0}{3396190.0} \approx 0.00588607$$
- **Authority Identifier:** `ESRI:103885` (Mars 2000 Sphere Equirectangular)
- **Vertical Datum:** Mars Orbiter Laser Altimeter (MOLA) areoid / Delta Geoid (areocentric equipotential surface where average atmospheric pressure is $610.5\,\text{Pa}$).

### 1.2 Coordinate Conventions
- **Latitude:** Planetocentric latitude $\phi$ in decimal degrees $[-90.0^\circ, +90.0^\circ]$, where positive denotes the Northern Hemisphere.
- **Longitude:** Positive East longitude $\lambda$ in decimal degrees $[0.0^\circ, 360.0^\circ]$ measured eastward from the Martian prime meridian (Airy-0 crater).
- **Elevation ($Z$):** Orthometric height in meters relative to the MOLA areoid.

---

## 2. Projection Mathematics: Equirectangular Mapping

The mapping between planetocentric spherical coordinates $(\lambda, \phi)$ and planar projected coordinates $(X, Y)$ uses the standard Equirectangular (Plate Carrée) projection with standard parallel $\phi_{\text{ts}} = 0^\circ$ and central meridian $\lambda_0 = 0^\circ$:

### 2.1 Forward Projection (Spherical $\to$ Planar Meters)
$$X = R_{\text{Mars}} \cdot (\lambda - \lambda_0) \cdot \frac{\pi}{180^\circ}$$
$$Y = R_{\text{Mars}} \cdot \phi \cdot \frac{\pi}{180^\circ}$$
where $R_{\text{Mars}} = 3,396,190.0\,\text{m}$.

### 2.2 Inverse Projection (Planar Meters $\to$ Spherical)
$$\lambda = \left(\frac{X}{R_{\text{Mars}}}\right) \cdot \frac{180^\circ}{\pi}$$
$$\phi = \left(\frac{Y}{R_{\text{Mars}}}\right) \cdot \frac{180^\circ}{\pi}$$

### 2.3 Raster Collocation Transform
The mapping between planar metric coordinates $(X, Y)$ and raster pixel coordinates $(\text{col}, \text{row})$ is governed by the 6-parameter Affine transform $\mathbf{T}$:
$$\begin{bmatrix} X \\ Y \\ 1 \end{bmatrix} = \begin{bmatrix} a & b & c \\ d & e & f \\ 0 & 0 & 1 \end{bmatrix} \begin{bmatrix} \text{col} \\ \text{row} \\ 1 \end{bmatrix}$$
For north-up, non-rotated grids: $b = 0$, $d = 0$, $a = \Delta X = +20.0\,\text{m}$, $e = -\Delta Y = -20.0\,\text{m}$.  
The exact pixel indices are given by:
$$\text{col} = \left\lfloor \frac{X - c}{a} \right\rfloor = \left\lfloor \frac{X - X_{\text{min}}}{\Delta X} \right\rfloor$$
$$\text{row} = \left\lfloor \frac{Y - f}{e} \right\rfloor = \left\lfloor \frac{Y_{\text{max}} - Y}{\Delta Y} \right\rfloor$$

---

## 3. Topographic Slope & Hazard Formulation

Local surface gradients are computed using the **Horn 8-neighbor gradient kernel**, which weights orthogonal neighbors by 2 and diagonal neighbors by 1 to minimize grid orientation bias.

### 3.1 Horn Finite-Difference Stencils
For a $3 \times 3$ elevation window:
$$\begin{matrix}
Z_{1} & Z_{2} & Z_{3} \\
Z_{4} & Z_{0} & Z_{5} \\
Z_{6} & Z_{7} & Z_{8}
\end{matrix}$$

The partial derivatives are:
$$\frac{\partial Z}{\partial x} = \frac{(Z_3 + 2 Z_5 + Z_8) - (Z_1 + 2 Z_4 + Z_6)}{8 \cdot \Delta x}$$
$$\frac{\partial Z}{\partial y} = \frac{(Z_1 + 2 Z_2 + Z_3) - (Z_6 + 2 Z_7 + Z_8)}{8 \cdot \Delta y}$$

### 3.2 Slope Angle Calculation
$$\theta = \arctan\left(\sqrt{\left(\frac{\partial Z}{\partial x}\right)^2 + \left(\frac{\partial Z}{\partial y}\right)^2}\right) \cdot \frac{180^\circ}{\pi}$$

### 3.3 Strict Operational Barrier
- Slopes $\theta > 16.0^\circ$ represent steep scarp barriers that are non-traversable by Martian exploration rovers (rocker-bogie chassis limit).
- Any grid cell exceeding $16.0^\circ$ is assigned an infinite traversal cost ($+\infty$) or marked `invalid_mask = True`.

---

## 4. Scientific Provenance & Primary Source Citations

| Domain | Primary Authority | Source Publication & DOI | PDS Bundle / URN |
|---|---|---|---|
| **Orbital Topography (20m)** | USGS Astrogeology Science Center | Fergusson et al. (2020), *USGS Jezero CTX DTM*, [DOI: 10.5066/P9T31O12](https://doi.org/10.5066/P9T31O12) | N/A (USGS Astrogeology GIS Repository) |
| **High-Res Topography (1m)** | USGS TRN Geodesy Project | Bland et al. (2024), *USGS TRN HiRISE DTM*, [DOI: 10.5066/P13CPYYU](https://doi.org/10.5066/P13CPYYU) | N/A (USGS Astrogeology S3 Archive) |
| **Tactical Localization** | NASA PDS Geosciences Node / WUSTL | Mars 2020 Rover Operations Team, JPL / Caltech | `urn:nasa:pds:mars2020_rover_places:data:best_tactical` |
| **Sample Depot Cache** | NASA Mars 2020 Science Team / JPL | Farley et al. (2023), *Science* 380, 1345-1350 | `urn:nasa:pds:mars2020_sample_depot_three_forks` |
| **Atmospheric In-Situ** | NASA PDS Atmospheres Node / CAB | Rodriguez-Manfredi et al. (2021), *Space Sci Rev* 217, 48 | `urn:nasa:pds:mars2020_meda` |
| **Astrobiology Science** | NASA Mars 2020 SHERLOC / PIXL | Scheller et al. (2022), *Science* 378, 1105-1110 | `urn:nasa:pds:mars2020_sherloc` |

---

## 5. Non-Probabilistic Truth Disclosures

To prevent scientific misrepresentation and ensure honest planetary mission reporting, Project MarsWalk 2.0 / Atlas enforces three categorical boundaries:

1. **Measured Historical Observations vs Simulation Telemetry:**
   Archived PDS Rover PLACES coordinates, Three Forks tube depositions, and MEDA atmospheric statistics are historical facts observed by NASA instruments. They are used as calibration anchors; they are never presented as real-time live telemetry from an active spacecraft.

2. **Model Estimations vs Physical Ground Truth:**
   Traversal times, battery discharge rates, metabolic consumption, and terrain line-of-sight are deterministic simulation model outputs. They reflect engineering assumptions and published empirical constants, not physical hardware telemetry.

3. **Astronaut Safety Boundary:**
   > [!CAUTION]
   > Modeled routes, EVA traverses, and autonomous detours generated by Project MarsWalk 2.0 are research demonstrator outputs. Under no circumstances should any modeled route be characterized as operationally safe for human astronauts. Real human extraterrestrial operations require certified life-support margins, micro-relief hazard verification (<10 cm), geotechnical soil bearing capacity analysis, and direct mission flight control authorization.
