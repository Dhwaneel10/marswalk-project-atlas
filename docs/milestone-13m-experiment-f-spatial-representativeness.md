# Mars Climate Validation Lab — Experiment F: Spatial Representativeness & Topographic Microclimates
**Milestone:** 13M — Mars Climate Data Assimilation & Validation Lab  
**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** November 2026  
**Status:** RELEASE QUALIFIED  

---

## 1. Experiment Overview
- **Identifier:** `EXP_F_SPATIAL_REPRESENTATIVENESS`
- **Objective:** Quantify the breakdown of spatial representativeness as a rover traverses from the flat Jezero crater floor onto steep topographic structures (e.g. the Western Delta Scarp and Crater Rim), evaluating the Composite Representativeness Index (CRI) and micro-shading aspect angles.
- **Components:** `src/marswalk/core/environmental_representativeness.py` coupled with the 20m USGS CTX DTM.

---

## 2. Experimental Traverse Profile Across Jezero Topography

We evaluated a 25 km transect beginning at the Perseverance landing site (-2570 m), ascending the Western Delta Scarp (-2480 m), traversing the delta top (-2420 m), and scaling the outer crater rim (-1890 m):

```
Elevation (m)
 -1800 |                                                         * * * (Crater Rim: -1890 m)
 -2000 |                                                    *
 -2200 |                                              *
 -2400 |                     * * * * (Delta Top: -2420 m)
 -2500 |               * * * (Delta Scarp: -2480 m)
 -2600 +---* * * * * (Crater Floor: -2570 m)------------------------------------>
         0         5        10        15        20        25 km from Landing
```

| Waypoint Along Transect | Distance (km) | Elevation (m) | Slope ($\theta$) | CRI Score | Context Tier | Microclimate Discrepancy ($\Delta T_\text{surf}$) |
| :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| **Octavia E. Butler Base** | 0.0 km | -2570 m | $0.2^\circ$ | **0.98** | `IN_SITU_PROXIMATE` | $0.0\text{ K}$ (Exact Match) |
| **Séítah North Border** | 2.5 km | -2565 m | $1.1^\circ$ | **0.91** | `IN_SITU_PROXIMATE` | $+0.8\text{ K}$ |
| **Delta Scarp Foot (Kodiak)**| 4.8 km | -2535 m | $6.5^\circ$ | **0.78** | `TOPOGRAPHIC_MICROCLIMATE` | $-3.2\text{ K}$ (Slope shading) |
| **Delta Face (North Scarp)** | 5.5 km | -2480 m | $18.2^\circ$| **0.67** | `TOPOGRAPHIC_MICROCLIMATE` | **$-14.5\text{ K}$ (Severe shadow cold)**|
| **Delta Top (Hawksbill)** | 8.0 km | -2420 m | $1.8^\circ$ | **0.62** | `REGIONAL_MODEL_CONTEXT` | $-1.5\text{ K}$ |
| **Margin Carbonate Unit** | 14.5 km| -2380 m | $3.4^\circ$ | **0.51** | `REGIONAL_MODEL_CONTEXT` | $+2.1\text{ K}$ (Higher albedo) |
| **Outer Crater Rim Ascent**| 24.2 km| -1890 m | $22.4^\circ$| **0.14** | `NON_COMPARABLE` | **$-18.2\text{ K}$ (High-altitude cold)**|

---

## 3. Scientific Findings & Engineering Implications
1. **The Steep Scarp Shadow Trap:** On north-facing scarp slopes ($\theta > 15^\circ$) during northern winter ($L_s \approx 270^\circ$), low sun angles ($h_\text{sun} < 25^\circ$) cause total self-shadowing throughout midday. Surface temperatures drop by $-14.5\text{ K}$ relative to adjacent flat ground, creating an intense microclimatic cold trap that coarse GCMs cannot resolve.
2. **Representativeness Cutoff:** When ascending the crater rim, the elevation delta exceeds $600\text{ m}$, triggering the `NON_COMPARABLE` priority gate. The system correctly warns operators that crater-floor MEDA observations cannot be extrapolated to the rim.
3. **Layered Fusion Resilience:** Level C field blending ensures that high-CRI points receive accurate empirical corrections while low-CRI scarp regions rely on ray-cast geometric thermal corrections rather than invalid planar extrapolations.
