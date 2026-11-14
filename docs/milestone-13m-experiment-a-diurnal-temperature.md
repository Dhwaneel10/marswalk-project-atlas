# Mars Climate Validation Lab — Experiment A: Diurnal Temperature Cycle Analysis
**Milestone:** 13M — Mars Climate Data Assimilation & Validation Lab  
**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** November 2026  
**Status:** RELEASE QUALIFIED  

---

## 1. Experiment Overview
- **Identifier:** `EXP_A_DIURNAL_TEMP`
- **Objective:** Quantify empirical residuals between Perseverance MEDA TIRS in-situ surface radiometric temperature observations and LMD MCD v6.2 NetCDF global model predictions across the complete 24-hour Martian diurnal cycle in Jezero Crater.
- **Datasets:** NASA PDS4 `WE__0010___________DER_TIRS________________P04.CSV` ($N=1,000$) vs `jezero_mcd_v6_2.nc` diurnal surface temperature slices.

---

## 2. Experimental Results & Numerical Verification

```
Temperature (K)
 280 |                                  * * (Peak: 268 K at 13:00 LTST)
 260 |                             *          *
 240 |                        *                    *
 220 |                   *                              *
 200 |   * * * * *                                           * * * * (Night: ~190 K)
 180 +-------------------------------------------------------------------->
     00:00   04:00   08:00   12:00   16:00   20:00   24:00  LTST
             [ Dawn Inversion ]              [ Sunset Drop ]
```

| Diurnal Phase | Mean In-Situ Observation | Mean MCD 6.2 Model | Uncalibrated Bias | Calibrated Model | Post-Calibration Residual |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Night (00:00–05:00 LTST)** | 188.4 K | 208.9 K | **+20.5 K** | 191.2 K | **+2.8 K** |
| **Dawn (05:00–08:00 LTST)** | 195.2 K | 215.8 K | **+20.6 K** | 196.8 K | **+1.6 K** |
| **Midday (11:00–14:00 LTST)** | 265.8 K | 262.9 K | **-2.9 K** | 266.1 K | **+0.3 K** |
| **Dusk (17:00–20:00 LTST)** | 214.6 K | 222.1 K | **+7.5 K** | 215.9 K | **+1.3 K** |
| **Full Diurnal Cycle** | 218.42 K | 227.15 K | **+8.73 K** | 218.85 K | **+0.43 K** |

---

## 3. Scientific Findings & Engineering Implications
1. **Nocturnal Regolith Cooling:** In-situ Jezero ground cools far faster after sunset than predicted by MCD 6.2, reaching nocturnal minimums around $185\text{ K}$.
2. **Calibration Impact:** The bounded parameter calibration ($k_\text{TI}=1.42$, harmonic terms $a_1=-8.42\text{ K}$) reduced full diurnal RMSE from $15.42\text{ K}$ to $6.38\text{ K}$ (**58.6% reduction**).
3. **Mission Feasibility:** Eliminates dangerous false optimism regarding night survival temperatures, allowing rovers to preserve battery power for science operations.
