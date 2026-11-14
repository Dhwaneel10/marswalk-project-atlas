# Mars Climate Data Assimilation & Validation Lab: Coordinate & Time Normalization Architecture
**Milestone:** 13M — Mars Climate Data Assimilation & Validation Lab  
**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** November 2026  
**Status:** RELEASE QUALIFIED  

---

## 1. Mathematical Time Standards for Mars Exploration

Planetary atmospheric observations from spacecraft and rovers are referenced across discordant temporal systems: Coordinated Universal Time (UTC), Ephemeris Time (ET), Mission Elapsed Sol, Local Mean Solar Time (LMST), Local True Solar Time (LTST), and Areocentric Solar Longitude ($L_s$). Project Atlas unifies all temporal variables through the rigorous formulation implemented in `mars_observation_normalizer.py`.

### 1.1 Mars Sol Date (MSD) and Sol Arithmetic
Following the Allison & McEwen (2000) standard:
$$\text{MSD} = \frac{\text{JD}_\text{UTC} - 2405522.0028779}{1.027491252} + 44796.0 - 0.00096$$

For Mars 2020 Perseverance at Jezero Crater, mission landing occurred on **February 18, 2021, 20:55 UTC** (MSD 52303.871, defined as Sol 0):
$$\text{Sol}_\text{M2020} = \lfloor \text{MSD} - \text{MSD}_\text{landing} \rfloor$$

### 1.2 Local Mean Solar Time (LMST) vs Local True Solar Time (LTST)
LMST advances at a constant rate corresponding to the Martian Mean Solar Day ($88,775.244\text{ s} = 24\text{h }39\text{m }35.244\text{s}$):
$$\text{LMST} = \left( 24 \times (\text{MSD} \pmod 1) + \frac{\lambda_\text{east}}{15^\circ} \right) \pmod{24}$$

Due to the eccentricity of the Martian orbit ($e \approx 0.0934$), the true sun drifts relative to the mean sun. The Equation of Time (EOT) is evaluated using the True Anomaly $\nu$ and Mean Anomaly $M$:
$$\text{EOT}(L_s) = \left( \frac{\alpha - M}{15^\circ} \right) \text{ hours}$$
$$\text{LTST} = (\text{LMST} + \text{EOT}(L_s)) \pmod{24}$$

### 1.3 Areocentric Solar Longitude ($L_s$)
Martian seasonality is strictly parameterized by $L_s \in [0^\circ, 360^\circ)$:
- $L_s = 0^\circ$: Northern Spring Equinox
- $L_s = 90^\circ$: Northern Summer Solstice (Aphelion $\approx 71^\circ$, cold/dust-clear)
- $L_s = 180^\circ$: Northern Autumnal Equinox
- $L_s = 270^\circ$: Northern Winter Solstice (Perihelion $\approx 251^\circ$, dust storm season)

```
   Ls = 90° (Northern Summer / Aphelion)
              [ Mars Orbit ]
                   |
     Ls = 0° ----- Sun ----- Ls = 180°
                   |
   Ls = 270° (Northern Winter / Perihelion)
```

---

## 2. Planetary Spatial Coordinate Standardization

### 2.1 Planetocentric East Coordinates (IAU 2000 Mars Spheroid)
All spatial coordinates ingested into Project Atlas are transformed into the standard Planetocentric East frame:
- Semi-major equatorial radius: $a = 3,396,190.0\text{ m}$
- Semi-minor polar radius: $b = 3,376,200.0\text{ m}$
- Flattening: $f = \frac{a - b}{a} \approx 0.005886$

Planetographic latitude $\phi_\text{pg}$ relates to Planetocentric latitude $\phi_\text{pc}$ via:
$$\tan(\phi_\text{pc}) = (1 - f)^2 \tan(\phi_\text{pg})$$

Atlas validates that all longitudes $\lambda \in [0^\circ, 360^\circ\text{ E}]$ and latitudes $\phi \in [-90^\circ, +90^\circ\text{ N}]$.

### 2.2 Jezero Crater Topocentric Projection
For tactical traverse modeling and collocation, spherical coordinates $(\phi, \lambda)$ are projected into a local topocentric East-North-Up (ENU) tangent plane centered at the Octavia E. Butler landing site:
$$\text{East} = R_\text{mars} \cdot (\lambda - \lambda_0) \cos\left(\frac{\phi + \phi_0}{2}\right)$$
$$\text{North} = R_\text{mars} \cdot (\phi - \phi_0)$$
$$\text{Altitude } z = h_\text{DTM}(\text{East}, \text{North}) \quad \text{[m relative to MOLA datum]}$$

Where $h_\text{DTM}$ is sampled from the authoritative 20m USGS CTX Digital Terrain Model (`jezero_ctx_dtm_20m.tif`).

---

## 3. Perseverance Traverse Waypoint Tracking
The normalizer indexes key Perseverance mission campaign milestones to associate in-situ observations with specific geological and topographic contexts:

| Traverse Milestone | Sol Range | Distance from Landing (km) | Elevation (MOLA m) | Terrain Classification |
| :--- | :--- | :--- | :--- | :--- |
| Octavia E. Butler Landing | Sols 0–60 | 0.00 km | -2570 m | Flat crater floor regolith |
| Séítah Ridge Entry | Sols 120–280 | 1.85 km | -2585 m | Sand dunes & fractured bedrock |
| Delta Scarp Base (Kodiak) | Sols 380–450 | 4.60 km | -2530 m | Rocky delta slope base |
| Delta Top (Hawksbill Gap) | Sols 450–700 | 7.20 km | -2490 m | Stratified sedimentary delta top |
| Margin Carbonate Unit | Sols 800–1100 | 14.50 km | -2380 m | High-albedo carbonate terrain |
| Crater Rim Ascent | Sols 1200–1527 | 22.80 km | -2150 m | Steep impact breccia scarp |

---

## 4. SI Unit Normalization Pipeline
All observation streams are ingested through strict unit transformations:
- **Pressure:** Ingested $\text{hPa} \to \text{Pa}$ ($\times 100.0$)
- **Temperature:** Ingested $^\circ\text{C} \to \text{Kelvin}$ ($+ 273.15$)
- **Wind Speed:** Validated in $\text{m/s}$
- **Dust Opacity:** Column extinction optical depth $\tau_{9.3\mu\text{m}}$ scaled to visible $\tau_\text{vis} = 2.0 \times \tau_\text{IR}$
- **Elevation:** Normalized to MOLA Datum (0 km elevation = 610.5 Pa triple point of water)
