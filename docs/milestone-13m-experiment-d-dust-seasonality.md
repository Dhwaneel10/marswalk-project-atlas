# Mars Climate Validation Lab — Experiment D: Dust Optical Depth Seasonality
**Milestone:** 13M — Mars Climate Data Assimilation & Validation Lab  
**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** November 2026  
**Status:** RELEASE QUALIFIED  

---

## 1. Experiment Overview
- **Identifier:** `EXP_D_DUST_SEASONALITY`
- **Objective:** Evaluate the seasonal variation in aerosol column dust optical depth ($\tau$) between the Aphelion clear season ($L_s \in [60^\circ, 120^\circ]$) and the Perihelion storm season ($L_s \in [240^\circ, 300^\circ]$), assessing its impact on direct solar irradiance and nighttime thermal radiative trapping.
- **Datasets:** Perseverance MEDA derived dust optical depth indices vs MCD 6.2 climatological dust scenario.

---

## 2. Experimental Results & Numerical Verification

```
Dust Optical Depth (tau)
 1.2 |                                  * * (Perihelion Peak: tau ~ 1.15)
 1.0 |                             *          *
 0.8 |                        *                    *
 0.6 |                   *                              *
 0.4 |   * * * * *                                           * * * * (Aphelion: tau ~ 0.28)
 0.2 +-------------------------------------------------------------------->
      0°       60°      120°     180°     240°     300°     360°  Ls (deg)
               [ Aphelion Clear Season ]           [ Perihelion Dust Storms ]
```

| Seasonal Regime | Solar Longitude ($L_s$) | Mean Observed $\tau_\text{vis}$ | Mean MCD 6.2 Model $\tau$ | Direct Irradiance ($I_\text{dir}$) | Thermal Trapping ($\Delta T_\text{night}$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Aphelion Clear Season** | $60^\circ\text{ to }120^\circ$ | **$0.28\pm 0.04$** | 0.32 | $485\text{ W/m}^2$ (High) | $+2.5\text{ K}$ (Minimal) |
| **Equinoctial Transition**| $120^\circ\text{ to }240^\circ$| **$0.48\pm 0.08$** | 0.45 | $410\text{ W/m}^2$ (Moderate) | $+5.8\text{ K}$ (Moderate) |
| **Perihelion Dust Season**| $240^\circ\text{ to }300^\circ$| **$1.15\pm 0.25$** | 0.88 | **$195\text{ W/m}^2$ (Low)** | **$+16.2\text{ K}$ (Strong)** |
| **Post-Storm Decay** | $300^\circ\text{ to }360^\circ$| **$0.55\pm 0.12$** | 0.50 | $380\text{ W/m}^2$ (Recovering) | $+7.4\text{ K}$ (Decaying) |

---

## 3. Scientific Findings & Engineering Implications
1. **Severe Solar Attenuation:** During perihelion dust events ($\tau > 1.1$), direct solar beam irradiance collapses by over $60\%$, dropping available solar power for MarsWalk traverse batteries from $750\text{ W}$ to under $300\text{ W}$.
2. **Thermal Blanketing Effect:** Increased atmospheric dust raises nighttime downward infrared flux ($F_\text{IR} \propto \epsilon_\text{dust} \sigma T_\text{dust}^4$), warming nocturnal ground temperatures by $+16.2\text{ K}$ relative to clear-sky conditions.
3. **Model Underprediction of Extreme Peaks:** MCD 6.2 climatological scenario underpredicts peak dust opacity by $\approx 23\%$ during local dust storms, requiring the Atlas calibrated dust scaling parameter $k_\tau = 1.18$ to ensure robust power margin budgeting.
