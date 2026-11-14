# Mars Climate Data Assimilation & Validation Lab: Planetary Data Quality & Sensor Degradation Architecture
**Milestone:** 13M — Mars Climate Data Assimilation & Validation Lab  
**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** November 2026  
**Status:** RELEASE QUALIFIED  

---

## 1. Quality Flag Hierarchy & Screening Architecture

Planetary surface measurements on Mars are subject to environmental degradation, dust deposition, high-energy particle radiation, and mechanical damage. Project Atlas enforces a strict 4-level quality grading schema implemented in `planetary_data_quality.py`:

| Quality Code | Flag Name | Semantic Definition | Action in Model Collocation | Action in Model Calibration |
| :---: | :--- | :--- | :--- | :--- |
| **0** | `NOMINAL` | Fully calibrated, within physical tolerances, unobstructed FOV | Accepted with standard sensor weight ($\sigma_0$) | Included in training and holdout validation sets |
| **1** | `UNCERTAIN` | High ambient noise, partial shadow fringe, or low SNR | Accepted with inflated uncertainty ($\sqrt{2} \sigma_0$) | Included in training with reduced weighting |
| **2** | `DEGRADED` | Known sensor degradation (e.g. wind boom sand grit damage) | Flagged; excluded from automated loss functions | Excluded from bounded parameter optimization |
| **3** | `INVALID` | Missing packet, corrupted telemetry, out-of-physical-range | Rejected immediately; recorded as `null` / `NaN` | Excluded completely |

---

## 2. Sensor-Specific Physical Failure Modes & Screening Rules

### 2.1 Perseverance MEDA Wind Sensor (WS) Grit Damage
During Perseverance's landing on Sol 0 and severe dust events around Sol 270, high-velocity sand and pebble saltation impacted Wind Sensor Boom 1 and Boom 2, damaging sensitive heated film anemometer elements.
- **Screening Rule:** Sols where wind flags indicate sensor saturation, circuit imbalance, or constant zero drift are permanently flagged as `QUALITY_DEGRADED` (code 2). Atlas does not attempt to synthesize wind fields for degraded sols.

### 2.2 MEDA Thermal Infrared Sensor (TIRS) Shadow & Chassis Obscuration
The TIRS sensor points downward at the ground to measure Martian surface radiometric temperature $T_\text{ground}$. However, at specific solar azimuths and low solar elevations, the rover chassis or Mastcam-Z mast casts a shadow directly across the TIRS footprint ($A \approx 2\text{–}3\text{ m}^2$).
- **Shadow Detection Formula:**
  $$\Delta \theta_\text{az} = |\phi_\text{solar} - \phi_\text{rover\_heading}|$$
  If $h_\text{sun} < 35^\circ$ and $\Delta \theta_\text{az} \in [140^\circ, 220^\circ]$, the surface footprint enters rover self-shadowing, depressing observed temperatures by up to $15\text{ K}$.
- **Screening Rule:** Records detected within rover self-shadowing are flagged as `QUALITY_UNCERTAIN` or `QUALITY_DEGRADED`.

### 2.3 MEDA Air Temperature Sensors (ATS) Rover Thermal Wake
Perseverance is powered by a Multi-Mission Radioisotope Thermoelectric Generator (MMRTG) mounted on the aft deck, generating $\approx 2000\text{ W}$ of thermal waste heat.
- **Wake Screening Formula:**
  When wind blows from the rear across the MMRTG deck toward the front mast ($\text{Wind Direction} \in [150^\circ, 210^\circ]$ relative to rover bow), thermal convection contaminates ATS mast readings by $+1.5\text{ to }+4.0\text{ K}$.
- **Screening Rule:** Contaminated records are flagged with `MASK_THERMAL_WAKE` and downweighted during model evaluation.

---

## 3. Strict Planetary Null Preservation Policy

In compliance with the MarsWalk Scientific Integrity Rules:
1. **Never Fill with Synthetic Data:** When a sensor reading is missing or corrupted, Atlas stores an explicit `null` / `NaN`.
2. **No Data Imputation for Real Records:** Interpolation or spline smoothing is strictly prohibited across missing observation intervals in raw or processed observational data files.
3. **No-Data Masks:** Every processed series stores an associated boolean mask (`valid_mask: [true, false, ...]`). Downstream numerical routines (RMSE, Bias, Pearson $r$) operate strictly on the intersection of valid pairs.

---

## 4. Quantitative Instrument Uncertainty Specifications

| Instrument / Sensor | Parameter | In-Situ Measurement Range | Absolute Sensor Uncertainty ($\pm 1\sigma$) | Model Benchmark Threshold |
| :--- | :--- | :--- | :--- | :--- |
| **MEDA PS** | Atmospheric Pressure | 600 to 1100 Pa | $\pm 2.0\text{ Pa}$ ($\approx 0.25\%$) | GCM acceptable if $|Bias| \le 15\text{ Pa}$ |
| **MEDA TIRS** | Ground Temperature | 130 to 300 K | $\pm 1.5\text{ K}$ | GCM acceptable if $|Bias| \le 12\text{ K}$ |
| **MEDA ATS** | 1.45m Air Temperature | 150 to 280 K | $\pm 0.75\text{ K}$ | GCM acceptable if $|Bias| \le 8\text{ K}$ |
| **MEDA RHS** | Relative Humidity | 0 to 100% | $\pm 3.0\%$ | GCM acceptable if $|Bias| \le 10\%$ |
| **MRO MCS** | Atmospheric Sounding $T(z)$ | 120 to 260 K | $\pm 2.5\text{ K}$ | GCM acceptable if $|Bias| \le 10\text{ K}$ |
| **MRO MCS** | Dust Extinction | $10^{-5}$ to $10^{-2}\text{ km}^{-1}$ | $\pm 20\%$ | GCM acceptable if $|Bias| \le 35\%$ |
