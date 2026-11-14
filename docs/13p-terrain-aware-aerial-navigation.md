# PROJECT ATLAS — MILESTONE 13P
# TERRAIN-AWARE AERIAL NAVIGATION & LANDING SITE EVALUATION
## 3D Flight Corridors, DTM Elevation Tracking, Transparent Landing Suitability, and Survey Rasters

**Milestone:** 13P — Atlas Aerial Corps: Multi-Rotorcraft Intelligence, Aerial Science, Flight Dynamics & Rover–Aircraft Cooperation  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Core Implementation:** `src/marswalk/core/mars_aerial_navigation.py`

---

## 1. Topographic Integration with Jezero Crater Cartography

Aerial navigation on Mars requires three-dimensional terrain intelligence. Project Atlas couples the rotorcraft navigation engine directly to the high-resolution USGS MRO CTX Digital Terrain Model ($20\text{ m/px}$, $250\times 250$ grid, covering a $5\times 5\text{ km}$ region of the Jezero Western Delta) and the registered NASA CTX surface optical orthomosaic ($6\text{ m/px}$).

### 1.1. 3D Flight Corridor Generation
Unlike ground rovers which are bound to the surface manifold, rotorcraft navigate through 3D airspace while maintaining a certified clearance margin above terrain:

$$z_{\text{commanded}}(x, y) = z_{\text{terrain}}(x, y) + h_{\text{clearance}} \quad (h_{\text{clearance}} \ge 8.0\text{ m})$$

For nominal scouting missions, cruise altitude is set between $12.0\text{ and }20.0\text{ m}$ Above Ground Level (AGL):
1. **Vertical Climb Stage:** Ascent from surface to cruise altitude ($w = 1.5\text{ m/s}$).
2. **Intermediate Waypoints:** 3D coordinates tracking terrain contours while clipping sharp ridgelines.
3. **Descent & Touchdown:** Vertical descent onto certified landing zones ($w = -1.2\text{ m/s}$).

---

## 2. Transparent Takeoff & Landing Site Evaluation

Landing a planetary rotorcraft on unpaved Martian regolith requires assessing multiple physical criteria. In Atlas, rather than using an ungrounded black-box "suitability percentage", candidate touchdown zones are evaluated against three transparent engineering dimensions:

```
+----------------------------------------------------------------------------------------------------+
|                               LANDING SITE ASSESSMENT MULTI-DIMENSIONAL CRITERIA                    |
+----------------------------------------------------------------------------------------------------+
|  DIMENSION              | ACCEPTABLE ENVELOPE     | REJECTION THRESHOLD   | SCORING FORMULATION    |
+-------------------------+-------------------------+-----------------------+------------------------+
|  Ground Slope (theta)   | theta <= 8.0 deg        | theta > 8.0 deg       | max(0, 1 - theta/12.0) |
|  Surface Roughness (r)  | r <= 0.08 m (8 cm)      | r > 0.12 m (12 cm)    | max(0, 1 - r/0.20)     |
|  Nearest Boulder (d)    | d >= 10.0 m             | d < 5.0 m (Rotor tip) | clamp((d - 3)/12, 0, 1)|
+-------------------------+-------------------------+-----------------------+------------------------+
```

### 2.1. Mathematical Scoring Formulation
1. **Slope Suitability Score ($S_{\text{slope}}$):**
   $$S_{\text{slope}} = \max\left(0.0, \, \min\left(1.0, \, 1.0 - \frac{\theta_{\text{slope}}}{12.0^\circ}\right)\right)$$
2. **Roughness Suitability Score ($S_{\text{rough}}$):**
   $$S_{\text{rough}} = \max\left(0.0, \, \min\left(1.0, \, 1.0 - \frac{r_{\text{roughness}}}{0.20\text{ m}}\right)\right)$$
3. **Obstacle Clearance Score ($S_{\text{obs}}$):**
   $$S_{\text{obs}} = \max\left(0.0, \, \min\left(1.0, \, \frac{d_{\text{boulder}} - 3.0\text{ m}}{12.0\text{ m}}\right)\right)$$
4. **Composite Overall Suitability:**
   $$S_{\text{overall}} = 0.40 \cdot S_{\text{slope}} + 0.30 \cdot S_{\text{rough}} + 0.30 \cdot S_{\text{obs}}$$

A landing site is certified as `SUITABLE` if and only if **no individual threshold is breached** and $S_{\text{overall}} \ge 0.65$. If any criteria fails, a structured rejection reason is recorded (e.g. `GROUND_SLOPE_TOO_STEEP_14.5deg_GT_8deg`), triggering an autonomous divert.

---

## 3. Systematic Terrain Coverage & Raster Mapping

For geological surveying and high-resolution orthomosaic generation, the navigation engine computes a lawnmower raster path covering target bounding boxes:

$$\Delta y_{\text{strip}} = 2 \cdot h_{\text{flight}} \cdot \tan\left(\frac{\text{FOV}_{\text{cross}}}{2}\right) \cdot (1 - \text{Overlap})$$

For nominal $h_{\text{flight}} = 15.0\text{ m}$, camera field of view $\text{FOV} = 50^\circ$, and lateral overlap of $40\%$:
$$\Delta y_{\text{strip}} = 2 \times 15.0 \times \tan(25^\circ) \times (1 - 0.40) = 30.0 \times 0.4663 \times 0.60 = 8.39\text{ m}$$

The generated raster waypoints ensure continuous, gap-free imagery across the entire region of interest without dead spots.

> [!WARNING]
> **MANDATORY ASTRONAUT SAFETY DISCLOSURE:**
> All 3D flight corridors, terrain clearance margins, and landing suitability algorithms documented here are designed for unmanned robotic vehicles. They must NEVER be used or construed as certified safe for human astronaut landing systems or piloted EVAs.
