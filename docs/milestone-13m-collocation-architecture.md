# Mars Climate Data Assimilation & Validation Lab: Observational Collocation Architecture
**Milestone:** 13M — Mars Climate Data Assimilation & Validation Lab  
**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** November 2026  
**Status:** RELEASE QUALIFIED  

---

## 1. The 4-Dimensional Collocation Problem on Mars

Evaluating a global or regional Mars atmospheric model against in-situ rover observations requires matching points across four physical dimensions:
1. **Horizontal Space ($\Delta d_\text{horiz}$):** The distance between the rover's position $(\phi_\text{obs}, \lambda_\text{obs})$ and the model grid cell center $(\phi_\text{mod}, \lambda_\text{mod})$.
2. **Topographic Altitude ($\Delta z$):** The difference between the in-situ ground elevation $z_\text{DTM}$ and the model grid cell orography $z_\text{GCM}$.
3. **Diurnal Phase ($\Delta \text{LTST}$):** The difference between local true solar times. On Mars, surface temperature shifts by up to $15\text{ K/hour}$ near sunrise and sunset; strict diurnal matching is required.
4. **Orbital Season ($\Delta L_s$):** The difference in solar longitude, controlling orbital distance, solar insolation, and the annual $\text{CO}_2$ condensation cycle.

```
+-----------------------------------------------------------------------------------+
|                        4D PHYSICAL COLLOCATION GATES                              |
|                                                                                   |
|  [ In-Situ Observation ]                      [ Model Grid / Climatology ]        |
|  (lat, lon, z, LTST, Ls)                      (lat_g, lon_g, z_g, LTST_g, Ls_g)   |
|            |                                              |                       |
|            +----------------------v-----------------------+                       |
|                                   |                                               |
|                    Check: Δd <= 50 km ?                                           |
|                    Check: |ΔLTST| <= 0.50 h ?                                     |
|                    Check: |ΔLs| <= 5.0 deg ?                                      |
|                    Check: |Δz| <= 300 m ?                                         |
|                    Check: Quality Code <= 1 ?                                     |
|                                   |                                               |
|               +-------------------+-------------------+                           |
|               | (All Gates Met)                       | (Any Gate Failed)         |
|               v                                       v                           |
|        [ COLLOCATED PAIR ]                     [ REJECTION LOGGED ]               |
|        (Obs Value, Mod Value)                  (Reason Code Recorded)             |
+-----------------------------------------------------------------------------------+
```

---

## 2. Quantitative Collocation Physical Gating Thresholds

The collocation engine in `mars_environment_collocation.py` enforces the following physical gates:

| Dimension | Physical Variable | Maximum Permitted Delta | Mathematical Rejection Condition | Failure Rejection Code |
| :--- | :--- | :--- | :--- | :--- |
| **Horizontal Space** | Great-circle distance | $\Delta d \le 50.0\text{ km}$ | $R_\text{mars} \cdot \arccos(\dots) > 50.0\text{ km}$ | `REJECT_DISTANCE` |
| **Diurnal Phase** | Local True Solar Time | $|\Delta \text{LTST}| \le 0.50\text{ h}$ (30 min) | $\min(|\Delta|, 24 - |\Delta|) > 0.50\text{ h}$ | `REJECT_DIURNAL_PHASE` |
| **Seasonal Phase** | Solar Longitude | $|\Delta L_s| \le 5.0^\circ$ | $\min(|\Delta|, 360^\circ - |\Delta|) > 5.0^\circ$ | `REJECT_SEASONAL_MISMATCH` |
| **Vertical Altitude** | Topographic elevation | $|\Delta z| \le 300.0\text{ m}$ | $|z_\text{DTM} - z_\text{GCM}| > 300.0\text{ m}$ | `REJECT_ELEVATION_DELTA` |
| **Data Quality** | Sensor Quality Flag | Code $\le 1$ (`NOMINAL`/`UNCERTAIN`) | $\text{Quality Code} \ge 2$ | `REJECT_QUALITY_DEGRADED` |

---

## 3. Topographic and Hypsometric Adjustments

When vertical elevation deltas exist within the $300\text{ m}$ tolerance, thermodynamic variables must be adjusted for elevation difference before residual computation:

### 3.1 Barometric Pressure Hypsometric Adjustment
Using the isothermal barometric formula with scale height $H \approx \frac{R_\text{gas} T}{g_\text{mars}} \approx 11.1\text{ km}$:
$$P_\text{mod, adj} = P_\text{mod} \cdot \exp\left( -\frac{z_\text{DTM} - z_\text{GCM}}{H} \right)$$
Without this adjustment, a modest $100\text{ m}$ elevation discrepancy between the coarse GCM grid cell and the crater floor would induce an artificial $\approx 7\text{ Pa}$ bias.

### 3.2 Atmospheric Temperature Lapse Rate Adjustment
For atmospheric mast temperature:
$$T_\text{mod, adj} = T_\text{mod} - \Gamma_\text{mars} \cdot (z_\text{DTM} - z_\text{GCM})$$
where $\Gamma_\text{mars} \approx 4.5\text{ K/km}$ is the standard Martian lower-troposphere lapse rate. Ground temperature is NOT lapsed via adiabatic formulas; rather, it is matched through surface energy balance and thermal inertia modeling.

---

## 4. Rejection Statistics & Audit Trail
Every collocation run outputs an explicit rejection summary. In our evaluation of the 4,573 normalized MEDA observations against MCD 6.2:
- **Total Ingested Candidates:** 4,573
- **Passed Physical Gating:** 4,120 pairs (90.1%)
- **Rejected due to Seasonal Misalignment:** 142 records
- **Rejected due to Sensor Grit/Degradation:** 267 records (MEDA WS)
- **Rejected due to Diurnal Phase Gap:** 44 records
- **Zero Ambiguous Matches:** Every accepted observation maps to exactly one spatially and temporally closest model prediction.
