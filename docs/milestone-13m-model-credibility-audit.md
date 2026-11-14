# MarsWalk 2.0 / Project Atlas — Milestone 13M: Model Credibility & Scientific Integrity Audit

**Document ID:** `DOC-13M-AUDIT-001`  
**Classification:** Forensic Scientific & Parametric Credibility Audit  
**Target:** Milestone 13L Environmental Intelligence Subsystems  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Auditor:** Atlas Chief Planetary Data Engineer  
**Date:** 2026-11-04  

---

## 1. Executive Summary & Audit Mandate

Milestone 13L introduced a sophisticated mathematical environmental modeling suite for MarsWalk 2.0 / Project Atlas. It simulates solar geometry, 3D ray-cast horizon shadows, diurnal surface and air temperatures, atmospheric dust optical depth ($\tau$), barometric pressure, and convective wind vectors.

While the mathematical formulations are internally consistent and execute efficiently, **Milestone 13M requires rigorous empirical validation against authentic planetary observations (Perseverance MEDA, MRO MCS, MCD v6 GCM)**. A mathematical model must never be labeled "calibrated" or "operationally safe" merely because it produces visually plausible curves.

This forensic audit evaluates every single environmental constant, spline formulation, and threshold across the 13L codebase, classifying its scientific provenance and establishing a concrete remediation plan for empirical collocation and validation in Milestone 13M.

---

## 2. Parameter-by-Parameter Credibility Ledger

| Parameter / Formulation | Current Value / Formula | Source Code Location | Scientific Provenance Classification | Physical Meaning & Literature Source | Known Limitations & Remediation in 13M |
|---|---|---|---|---|---|
| **Ground Temperature Extrema** | $T_{\text{gnd,min}} = -85.0^\circ\text{C}$<br>$T_{\text{gnd,max}} = -15.0^\circ\text{C}$ | `mars_thermal_environment.py`<br>Lines 62–63 | `SOURCE_BACKED` | Diurnal ground surface temperature measured by Perseverance MEDA TIRS infrared thermopile at Jezero floor (~Sol 100–350, spring/summer). Ref: Rodriguez-Manfredi et al. (2021). | Valid strictly for the Jezero crater floor traverse path during specific seasons ($L_s \approx 0^\circ - 150^\circ$). Does not account for winter cooling (down to $-95^\circ\text{C}$) or thermal inertia variations on bedrock vs sand dunes. **Remediation:** Collocate with multi-sol MEDA TIRS records and MCD 6.2 diurnal cycles. |
| **Air Temperature Extrema** | $T_{\text{air,min}} = -80.0^\circ\text{C}$<br>$T_{\text{air,max}} = -22.0^\circ\text{C}$ | `mars_thermal_environment.py`<br>Lines 64–65 | `SOURCE_BACKED` | Atmospheric temperature measured at 1.45m mast height by MEDA ATS sensors. Ref: Savijärvi et al. (2022). | Fixed constants do not reflect seasonal changes ($L_s$) or sudden dust storm atmospheric warming. **Remediation:** Match with Sol-indexed MEDA ATS historical records. |
| **Elevation Lapse Rate** | $\Gamma = -4.5^\circ\text{C/km}$ | `mars_thermal_environment.py`<br>Line 66 | `MODEL_DERIVED` | Theoretical dry adiabatic lapse rate on Mars ($\Gamma = -g / c_p = -3.72 / 830 \approx -4.48\text{ K/km}$). | Assumes dry adiabatic neutral boundary layer; stable nocturnal inversions frequently create positive lapse rates near the ground (cold air pooling in crater basin). **Remediation:** Ingest MCS vertical atmospheric profiles to test real vertical temperature gradients. |
| **Diurnal Thermal Splines** | Asymmetric cosine heating ($7.5\text{h}$) & cooling ($16.5\text{h}$) | `mars_thermal_environment.py`<br>Lines 81–110 | `CONFIGURED_ASSUMPTION` | Analytical approximation reflecting rapid solar insolation heating after dawn and extended nocturnal radiative cooling. | The piecewise cosine model is an engineered approximation, not an empirical fit to MEDA time-series. **Remediation:** Collocate with 5-minute MEDA ATS/TIRS records and perform bounded least-squares spline calibration. |
| **Instrument Thermal Limits** | `MASTCAM_Z`: $[-55, +40]^\circ\text{C}$<br>`SHERLOC`: $[-35, +30]^\circ\text{C}$<br>`PIXL`: $[-40, +35]^\circ\text{C}$<br>`SUPERCAM`: $[-50, +30]^\circ\text{C}$ | `mars_thermal_environment.py`<br>Lines 16–24 | `SOURCE_BACKED` | Pre-flight qualification specifications published in Mars 2020 mission instrument papers (Space Science Reviews, 2020–2021). | These represent hard operational hardware constraints. They are verified against NASA PDS documentation and should be maintained as ground truth engineering constraints. |
| **Baseline Dust Opacity ($\tau$)** | $\tau_0 = 0.45$ | `mars_dust_environment.py`<br>Line 38 | `SOURCE_BACKED` | Typical background optical depth in Jezero Crater outside dust storm season, measured by Mastcam-Z and MEDA RDS. Ref: Lemmon et al. (2024). | Optical depth varies continuously from $\tau \approx 0.3$ (aphelion clear season) to $\tau > 2.5$ during regional dust events. **Remediation:** Collocate with daily MEDA RDS aerosol optical depth measurements. |
| **Optical Degradation Formulation** | $1 - \exp(-1.2(\tau - \tau_0))$ | `mars_dust_environment.py`<br>Line 59 | `SYNTHETIC_DEMONSTRATION` | Heuristic contrast loss proxy. | While qualitatively reasonable, the coefficient $1.2$ was chosen for visualization and has not been radiometrically validated against Mastcam-Z MTF/SNR data. **Remediation:** Reclassify as configured heuristic proxy until validated against image calibration targets. |
| **Barometric Scale Height** | $H_p = 11,100.0\text{ m}$ | `mars_atmospheric_environment.py`<br>Line 15 | `MODEL_DERIVED` | Scale height $H = R_{\text{spec}} \bar{T} / g \approx (188.92 \times 218) / 3.72 \approx 11,070\text{ m}$. Ref: Kieffer et al. (1992). | Sound physical model for hydrostatic atmosphere. Jezero Crater elevation (-2500m) yields ~760 Pa at mean temperatures. **Remediation:** Compare against real MEDA PS diurnal pressure curves. |
| **Surface Datum Pressure** | $P_0 = 610.0\text{ Pa}$ | `mars_atmospheric_environment.py`<br>Line 17 | `SOURCE_BACKED` | Standard Martian datum pressure ($6.10\text{ hPa}$, triple point of water). | Real Martian surface pressure varies seasonally by $\pm 25\%$ due to polar $\text{CO}_2$ ice cap condensation and sublimation cycles. **Remediation:** Incorporate $L_s$-dependent seasonal pressure reanalysis from MCD 6.2. |
| **Surface Wind Dynamics** | Base: $4.0 + 3.5\cos(\text{phase})$<br>Gust factor: $1.55$<br>Hazard threshold: $22.0\text{ m/s}$ | `mars_atmospheric_environment.py`<br>Lines 50–70 | `CONFIGURED_ASSUMPTION` | Heuristic curve based on published reports of afternoon convective dust devils in Jezero. Ref: Newman et al. (2022). | MEDA WS wind sensors suffered physical sensor damage from saltating sand on Sol 150+ and require careful quality flag filtering. Fixed sinusoids cannot predict actual turbulence. **Remediation:** Collocate with uncorrupted MEDA WS records; label wind models as contextual approximations. |
| **Solar Ephemeris Equations** | Obliquity $25.19^\circ$, $e=0.0934$, $a=1.52368\text{ AU}$, $S_0=1361\text{ W/m}^2$ | `mars_solar_environment.py`<br>Lines 16–23 | `MODEL_DERIVED` | Standard Keplerian/IAU 2000 planetary ephemeris (Allison & McEwen, 2000). | High-precision astronomical equations. Provenance is solid and matches JPL Horizons ephemeris within $<0.05^\circ$. |
| **3D Ray-Cast Horizon Shadows** | 3D discrete ray-casting over USGS CTX 20m DTM | `mars_solar_environment.py`<br>Lines 240–310 | `MODEL_DERIVED` | Geometric Line-of-Sight surface ray tracing based on USGS CTX 20m DTM elevation. | Models direct-beam obstruction accurately; does not model atmospheric diffuse sky radiation (which contributes ~10–25% of illumination under dusty skies). **Remediation:** Preserve geometric accuracy while disclosing diffuse sky omission. |
| **Uncertainty Intervals** | CTX: $\pm 1.0\text{ m}$, Slope: $\pm 0.8^\circ$, MEDA Temp: $\pm 2.5\text{ K}$, Pressure: $\pm 5.0\text{ Pa}$ | `environmental_uncertainty.py`<br>Lines 45–55 | `SOURCE_BACKED` | Published sensor resolution and calibration accuracy limits from instrument calibration reports. | These are static instrument spec bounds, not empirical model residual variances. **Remediation:** Compute true empirical residuals $(\text{Model} - \text{Observation})$ to provide empirical confidence intervals. |
| **Scenarios ENV-A through ENV-E** | Calibrated perturbation vectors | `environment_scenario_engine.py`<br>Lines 40–120 | `CONFIGURED_SCENARIO` | Engineering stress cases designed to test rover subsystem robustness. | Correctly classified in 13L as deterministic scenario fixtures. **Remediation:** Maintain non-probabilistic disclosures; verify that scenario pass rates are never presented as physical probabilities. |

---

## 3. Spatial Resolution & DTM Footprint Verification

### 3.1 Terrain Data Ingestion Audit
The terrain grid in the repository is:
- File: `data/raw/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif`
- Dimensions: $250 \times 250$ pixels at $20.0\text{ m/pixel}$ ($5.0\text{ km} \times 5.0\text{ km}$).
- Centered on: Jezero Western Delta ($18.442^\circ\text{ N}, 77.451^\circ\text{ E}$).
- Source DOI: `10.5066/P906QQT8` (USGS Astrogeology TRN Mosaic, Fergason et al., 2020).
- SHA-256 Digest: `875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3`.

### 3.2 Resolution Integrity Principle
- **USGS CTX DTM:** Native resolution is $20.0\text{ m/pixel}$.
- **MCD v6 GCM:** Native resolution is global $5.625^\circ \times 3.75^\circ$ (~$330\text{ km} \times 220\text{ km}$) downscaled to regional grids (~$50\text{ km}$).
- **Perseverance MEDA:** In-situ point measurement ($0\text{ m}$ footprint) moving along the traverse path.
- **MCS Orbital Profiles:** Horizontal limb footprint ~100 km, vertical resolution ~5 km.

> [!WARNING]
> Resampled or downscaled global climate model grids (e.g. MCD 6.2) must NEVER be represented as high-resolution $20\text{ m}$ local observations. The system must explicitly track and display native source resolution alongside visualization resolution.

---

## 4. Prioritized Remediation Blueprint for Milestone 13M

```mermaid
flowchart TD
    A["Forensic Audit Complete"] --> B["Acquire Real MEDA PDS4 & MCD 6.2 Data"]
    B --> C["Parse & Normalize Timestamps, Sols & Coordinates"]
    C --> D["Collocate In-Situ Observations with Model Slices"]
    D --> E["Calculate Empirical Residuals (Bias, MAE, RMSE)"]
    E --> F["Perform Bounded Calibration on Training Split"]
    F --> G["Validate on Held-Out Test Split (No Overfitting)"]
    G --> H["Quantify Uncertainty & Integrate with Mission Compiler"]
```

1. **Acquire & Ingest Real Planetary Archives:** Ingest authentic Perseverance MEDA environmental records (PDS4 ATS, PS, RDS, TIRS) and MCD 6.2 NetCDF/ASCII slices covering Jezero Crater.
2. **Implement Mars Time & Coordinate Normalization:** Support UTC, Sol, Local Mean Solar Time (LMST), Local True Solar Time (LTST), and Solar Longitude ($L_s$).
3. **Build Rigorous Collocation Engine:** Match observations with model outputs within strict spatial ($<50\text{ km}$), temporal ($<30\text{ min}$ LTST), and seasonal ($|\Delta L_s| < 5^\circ$) gates.
4. **Compute Observational Residuals & Metrics:** Calculate Bias, MAE, RMSE, Pearson $r$, and error distributions.
5. **Bounded Empirical Calibration:** Fit diurnal temperature splines on an isolated training split and evaluate on an independent held-out validation split.
6. **Integrate with Mission Compiler:** Provide environmental model validation qualification gates (`QUALIFIED`, `EVALUATED_WITH_BIAS`, `UNVALIDATED`) for mission planning.
