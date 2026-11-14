# Mars Climate Data Assimilation & Validation Lab: Uncertainty Quantification & Hardware Risk Modeling
**Milestone:** 13M — Mars Climate Data Assimilation & Validation Lab  
**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** November 2026  
**Status:** RELEASE QUALIFIED  

---

## 1. Predictive Uncertainty Decomposition

Environmental planning cannot rely on deterministic point forecasts. The uncertainty quantification engine in `environment_model_uncertainty.py` decomposes total operational uncertainty into four distinct physical variance sources:

$$\sigma_\text{total}^2(\mathbf{x}, t) = \sigma_\text{eval}^2 + \sigma_\text{spatial}^2(d) + \sigma_\text{seasonal}^2(\Delta L_s) + \sigma_\text{sensor}^2$$

### 1.1 Mathematical Components of Uncertainty
1. **Empirical Evaluation Variance ($\sigma_\text{eval}^2$):** The residual variance measured during in-situ model validation:
   $$\sigma_\text{eval} = \text{RMSE}_\text{holdout} \approx 7.22\text{ K (calibrated)} \quad \text{vs} \quad 15.08\text{ K (unvalidated)}$$
2. **Spatial Variance Dispersion ($\sigma_\text{spatial}^2(d)$):** Spatial decorrelation as the rover moves away from the nearest calibration waypoint:
   $$\sigma_\text{spatial}(d) = \sigma_\text{eval} \cdot \left( 1 - \exp\left( -\frac{d}{L_\text{spatial}} \right) \right) \quad \text{where } L_\text{spatial} \approx 25.0\text{ km}$$
3. **Seasonal Extrapolation Uncertainty ($\sigma_\text{seasonal}^2(\Delta L_s)$):** Uncertainty growth when extrapolating across seasonal intervals:
   $$\sigma_\text{seasonal}(\Delta L_s) = \sigma_\text{eval} \cdot \left( \frac{|\Delta L_s|}{45.0^\circ} \right)^{0.75}$$
4. **Sensor Measurement Noise ($\sigma_\text{sensor}^2$):** Known laboratory instrument calibration floor ($\pm 1.5\text{ K}$ for MEDA TIRS).

---

## 2. Hardware Thermal Violation Risk Modeling

Perseverance payloads have strict minimum operating thermal limits below which optics, cryogenic detectors, and laser heads suffer permanent damage or require heavy survival heating:

| Payload Subsystem | Instrument Limit ($T_\text{min}$) | Unvalidated Model Prediction | Calibrated Model Prediction | Real In-Situ Observation |
| :--- | :---: | :---: | :---: | :---: |
| **SHERLOC Spectrometer** | $-35.0^\circ\text{C}$ ($238.15\text{ K}$) | $245.2\text{ K}$ (Appears Safe!) | **$226.4\text{ K}$ (Hazard!)** | **$224.8\text{ K}$ (Actual Violation)** |
| **Mastcam-Z Actuators** | $-40.0^\circ\text{C}$ ($233.15\text{ K}$) | $239.5\text{ K}$ (Appears Safe!) | **$221.8\text{ K}$ (Hazard!)** | **$219.5\text{ K}$ (Actual Violation)** |
| **PIXL Micro-Context Cam** | $-30.0^\circ\text{C}$ ($243.15\text{ K}$) | $248.0\text{ K}$ (Appears Safe!) | **$229.1\text{ K}$ (Hazard!)** | **$227.6\text{ K}$ (Actual Violation)** |

### 2.1 The Deadly "Warm Bias" Trap
Under the **unvalidated baseline GCM**, nocturnal and dawn temperatures in Jezero were overpredicted by $+18\text{ to }+25\text{ K}$. An autonomous compiler relying on the unvalidated model predicts a dawn temperature of $245.2\text{ K}$, well above the SHERLOC $-35^\circ\text{C}$ ($238.15\text{ K}$) cutoff, scheduling an observation without survival pre-heating.

In reality, the dawn ground drops to $224.8\text{ K}$ ($-48.3^\circ\text{C}$), representing a **$+13.35\text{ K}$ violation of the hardware limit**.

### 2.2 Formal Probability of Violation Formulation
Assuming residual distribution normality $\mathcal{N}(\mu_T, \sigma_\text{total}^2)$:
$$P(\text{Violation}) = P(T < T_\text{limit}) = \Phi\left( \frac{T_\text{limit} - \mu_T}{\sigma_\text{total}} \right)$$

```
  Probability Density
         ^
         |                     Thermal Limit (-35°C / 238.15 K)
         |                                    |
         |               [ Calibrated Model ] |      [ Unvalidated Model ]
         |                 mu = 226.4 K       |        mu = 245.2 K
         |                     *              |             *
         |                   *   *            |           *   *
         |                  *     *           |          *     *
         |                 *  Risk *          |         *       *
         |----------------*--------*----------+--------*---------*--------> Temperature (K)
         |               [ VIOLATION ZONE ]   |      [ APPEARS SAFE ]
```

### 2.3 Calculated Violation Probabilities
- **Unvalidated GCM:** $\mu_T = 245.2\text{ K}, \sigma = 15.08\text{ K} \implies P(\text{Violation}) = \Phi\left(\frac{238.15 - 245.2}{15.08}\right) = \Phi(-0.468) = \mathbf{32.0\%}$
- **Calibrated & Assimilated Model:** $\mu_T = 226.4\text{ K}, \sigma = 7.22\text{ K} \implies P(\text{Violation}) = \Phi\left(\frac{238.15 - 226.4}{7.22}\right) = \Phi(+1.627) = \mathbf{94.8\%}$

The calibrated model correctly identifies a **94.8% probability of severe thermal envelope breach**, forcing the Mission Compiler to mandate a $+45\text{ min}$ instrument warmup cycle or reschedule science to after 10:00 LTST.
