# ATLAS 13AE: MARTIAN DUST SPECTRAL PROVENANCE & ÅNGSTRÖM EXPONENT AUDIT

**Document Identifier:** `ATLAS-DOC-13AE-STAGE-01`  
**Milestone:** 13AE — Propagation Evidence Closure  
**Parent Milestone:** 13AD — Mars Physics Reference Validation  
**Date:** November 2026  
**Status:** Audit Completed — Remediation Enforced  

---

## 1. Executive Summary & Audit Mandate

In Milestone 13AD, the wavelength-dependent optical depth extrapolation between the reference MER Mastcam filter ($880\text{ nm}$) and Deep Space Optical Communications (DSOC) laser wavelength ($1550\text{ nm}$) was modeled as:

$$\tau(\lambda) = \tau(\lambda_{\text{ref}}) \left(\frac{\lambda}{\lambda_{\text{ref}}}\right)^{-\alpha_{\text{ang}}}$$

with an assumed default Ångström exponent:
$$\alpha_{\text{ang}} = +0.35 \implies \tau(1550\text{ nm}) = 0.8203 \cdot \tau(880\text{ nm})$$

This assumed a $\sim 18\%$ reduction in optical extinction at $1550\text{ nm}$.

**Audit Finding:** This $+0.35$ default is **scientifically ungrounded for Mars**. It conflated terrestrial coarse aerosol behavior with in-situ Martian dust properties. Primary Martian exploration records (Lemmon et al. 2014, 2019; Wolff et al. 2009; Fernández-Rodríguez et al. 2024) establish that Martian dust is dominated by larger particles ($r_{\text{eff}} \approx 1.5\text{ to } 2.5\,\mu\text{m}$). Consequently, the Ångström exponent across the visible-to-telecom NIR spectrum is **slightly negative or near zero** ($\alpha \in [-0.16, 0.0]$), meaning that $1550\text{ nm}$ optical depth is **equal to or slightly higher than visible opacity ($\tau_{1.55} \approx 1.02 - 1.10 \cdot \tau_{\text{ref}}$)**, never 18% lower.

---

## 2. Examination of Primary Sources

### 2.1 Lemmon et al. (2014) — MER 5-Year Optical Depth Record
- **Source:** *Dust aerosol, clouds, and the atmospheric optical depth record over 5 Mars years of the Mars Exploration Rover mission*, Icarus 251, 96–111.
- **Filters Analyzed:** Direct solar imaging via Pancam L8 ($440\text{ nm}$) and R8 ($880\text{ nm}$).
- **Findings:** The ratio of extinction $\tau(440\text{ nm}) / \tau(880\text{ nm})$ hovers near $1.0 \pm 0.1$ during normal conditions, indicating weak spectral dependence. The derived effective radius is $r_{\text{eff}} \approx 1.4 - 1.6\,\mu\text{m}$.
- **Implication:** Because $2\pi r_{\text{eff}} / \lambda \gg 1$ throughout the visible and near-IR, extinction is in the anomalous diffraction/Mie plateau regime where $Q_{\text{ext}} \approx 2$, precluding steep positive Ångström exponents.

### 2.2 Lemmon et al. (2019) — 2018 Global Dust Event
- **Source:** *Large dust aerosol sizes seen during the 2018 Martian global dust event by the Curiosity rover*, Geophys. Res. Lett. 46, 9448–9456.
- **Findings:** During the massive MY 34 planet-encircling dust event, Curiosity Mastcam measured dust effective radius increasing from $r_{\text{eff}} \approx 1.5\,\mu\text{m}$ to $> 2.5\,\mu\text{m}$.
- **Empirical Ångström Values:** Multi-wavelength fits yielded slightly negative Ångström exponents ranging from $\alpha = -0.036$ (early storm / baseline) to $\alpha = -0.160$ (peak storm with elevated coarse aerosols).

### 2.3 Wolff et al. (2009) — CRISM Single-Scattering Albedo vs Extinction
- **Source:** *Wavelength dependence of dust aerosol single scattering albedo as observed by CRISM*, J. Geophys. Res. 114, E00D04.
- **Findings:** Wolff et al. analyze the *single-scattering albedo* $\omega_0(\lambda)$, which increases from $\sim 0.6$ at $440\text{ nm}$ to $> 0.9$ at $880\text{ nm}$ and $1550\text{ nm}$ (dust is strongly absorbing in blue/UV, but predominantly scattering in the near-IR).
- **Distinction:** Single-scattering albedo $\omega_0 = Q_{\text{sca}} / Q_{\text{ext}}$ is **not** the Ångström exponent of total extinction. Conflating $\omega_0$ with total optical depth scaling was an error in 13AD literature referencing.

### 2.4 Fernández-Rodríguez et al. (2024) — Mars Optical Satellite Communications
- **Source:** *On the feasibility of laser satellite communications from the Martian surface*, arXiv:2404.16955 / 2504.16955.
- **Methodology:** The authors specifically evaluate the visibility and slant link budget of $1550\text{ nm}$ laser communications on Mars.
- **Conversion Formulation:** They scale optical depth from Mars Climate Database (MCD) reference wavelengths to $1.55\,\mu\text{m}$ using:
  $$\frac{\tau_{1.55}}{\tau_{0.67}} = \left(\frac{0.67}{1.55}\right)^\alpha$$
  with empirical exponent $\alpha = -0.082$, yielding:
  $$\tau(1550\text{ nm}) \approx 1.071 \times \tau(670\text{ nm}) \approx 1.048 \times \tau(880\text{ nm})$$
- **Result:** $1550\text{ nm}$ experiences $\sim 5 - 7\%$ *higher* optical depth than visible wavelengths, refuting the 13AD claim of an 18% path loss reduction.

---

## 3. Systematic Sensitivity Table

The table below evaluates optical depth scaling, transmission, and attenuation from reference opacity ($\tau_{\text{ref}} = 0.5$ nominal, $\tau_{\text{ref}} = 3.0$ severe dust storm) across documented Martian exponents:

| Scenario / Citation | $\alpha$ | $\lambda_0$ | $\frac{\tau(1550)}{\tau_0}$ | $\tau_{1550}$ ($\tau_0=0.5$) | Zenith Loss ($0.5$) | $10^\circ$ Loss ($0.5$) | $\tau_{1550}$ ($\tau_0=3.0$) | Zenith Loss ($3.0$) | $10^\circ$ Loss ($3.0$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Historical 13AD (Terrestrial)** | $+0.350$ | $880\text{ nm}$ | $0.8203$ | $0.4101$ | $1.78\text{ dB}$ | $9.22\text{ dB}$ | $2.4608$ | $10.69\text{ dB}$ | $55.34\text{ dB}$ |
| **Lemmon 2019 Low-Dust Fit** | $-0.036$ | $880\text{ nm}$ | $1.0206$ | $0.5103$ | $2.22\text{ dB}$ | $11.48\text{ dB}$ | $3.0618$ | $13.30\text{ dB}$ | $68.86\text{ dB}$ |
| **Lemmon 2019 Intermediate Fit** | $-0.047$ | $880\text{ nm}$ | $1.0270$ | $0.5135$ | $2.23\text{ dB}$ | $11.55\text{ dB}$ | $3.0809$ | $13.38\text{ dB}$ | $69.29\text{ dB}$ |
| **Fernández-Rodríguez 2024 (MCD)** | $-0.082$ | $880\text{ nm}$ | $1.0475$ | $0.5238$ | $2.27\text{ dB}$ | $11.78\text{ dB}$ | $3.1425$ | $13.65\text{ dB}$ | $70.67\text{ dB}$ |
| **Fernández-Rodríguez 2024 (0.67µm)** | $-0.082$ | $670\text{ nm}$ | $1.0712$ | $0.5356$ | $2.33\text{ dB}$ | $12.05\text{ dB}$ | $3.2136$ | $13.96\text{ dB}$ | $72.27\text{ dB}$ |
| **Lemmon 2019 Severe Storm Bound** | $-0.160$ | $880\text{ nm}$ | $1.0948$ | $0.5474$ | $2.38\text{ dB}$ | $12.31\text{ dB}$ | $3.2844$ | $14.26\text{ dB}$ | $73.86\text{ dB}$ |

*(Note: $10^\circ$ elevation airmass evaluated via exact Chapman numerical integration: $X(10^\circ) = 5.1783$)*

---

## 4. Software Implementation Remediation

1. **Retire $+0.35$ as Default:** The default `dust_angstrom_exponent` in `MarsAtmosphericProfile` must be updated from $+0.35$ to **$-0.082$** (traceable to Fernández-Rodríguez et al. 2024 / Lemmon et al. 2019).
2. **Expose Explicit Parameterization:** `dust_angstrom_exponent` must remain a fully configurable parameter with documented uncertainty envelope $[-0.16, 0.0]$.
3. **Disclosure:** Disclose that optical laser telecommunication at $1550\text{ nm}$ does not benefit from significant aerosol thinning on Mars; atmospheric dust attenuation at $1550\text{ nm}$ is comparable to or slightly greater than visible opacity.
