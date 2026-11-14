# ATLAS 13AD: MODEL VALIDITY REGISTER & OPERATIONAL BOUNDARIES

**Document Identifier:** `ATLAS-DOC-13AD-STAGE-10`  
**Milestone:** 13AD — Mars Physics Reference Validation  
**Parent:** `ATLAS-13AC-PHYSICS-BOUNDARY`  
**Status:** Approved & Enforced  
**Date:** November 2026  

---

## 1. Executive Summary

In accordance with Milestone 13AD principles, "A mathematically finite result is not necessarily physically meaningful. A numerically stable calculation is not necessarily a valid physical approximation."

This Model Validity Register provides an exhaustive, defensible inventory of all mathematical and physical models governing communications, radiative transfer, and antenna electromagnetics in Project Atlas. It defines their governing equations, valid operational domains, failure boundaries, defensive software handling, and empirical reference baselines.

---

## 2. Model Validity Inventory

### 2.1 Spherical Atmospheric Radiative Transfer & Airmass
- **Governing Equations:**
  $$h(s) = \sqrt{r_0^2 + 2 r_0 s \sin\theta + s^2} - R_M$$
  $$\tau_{\text{slant}} = \int_0^{s_{\text{TOA}}} \alpha_0 \exp\left(-\frac{h(s)}{H}\right) ds, \quad X(\theta) = \frac{\tau_{\text{slant}}}{\tau_{\text{zenith}}}$$
  $$X(0^\circ)_{\text{asymptote}} \approx \sqrt{\frac{\pi R_M}{2 H}}$$
- **Physical Validity Domain:**
  - Elevation angle: $0.001^\circ \le \theta \le 90.0^\circ$.
  - Observer altitude: $0 \le h_{\text{obs}} < h_{\text{TOA}}$ ($100\text{ km}$).
  - Scale height: $H \in [5.0, 30.0]\text{ km}$ ($H_{\text{ref}} = 11.0\text{ km}$).
- **Failure Boundaries & Breakdown Regimes:**
  - $\theta \le 0.0^\circ$: Geometric occultation behind Martian solid planetary sphere. Line-of-sight ray intersects terrain or core.
  - $\theta < 5.0^\circ$: Plane-parallel slab approximation $X_{\text{slab}}(\theta) = 1/\sin\theta$ fails, diverging by $> 28\%$ at $5^\circ$, $> 226\%$ at $1^\circ$, and $\infty$ at $0^\circ$.
- **Software Implementation & Defensive Boundaries:**
  - Implemented in `MarsAtmosphericEngine.calculate_spherical_airmass`.
  - Elevation $\le 0.0^\circ$ strictly tagged as `OCCULTED_BELOW_HORIZON` with infinite slant depth.
  - Integration performed via 21-point Gauss-Kronrod adaptive quadrature (`scipy.integrate.quad`) with pure-Python trapezoidal fallback.
- **Reference Citations:**
  - Chapman, S. (1931), *The Absorption and Dissociative or Ionizing Effect of Monochromatic Radiation in an Earth's Atmosphere*, Proc. Phys. Soc. 43, 26.
  - Lemmon, M. T. et al. (2014), *Dust aerosol, clouds, and the atmospheric optical depth record over 5 Mars years of the Mars Exploration Rover mission*, Icarus 251, 96–111.

---

### 2.2 Spectral Optical Extinction (Ångström Power Law)
- **Governing Equations:**
  $$\tau(\lambda) = \tau_{\text{ref}} \left(\frac{\lambda}{\lambda_{\text{ref}}}\right)^{-\alpha_{\text{ang}}}$$
  $$A_{\text{dB}}(\lambda) = 10 \log_{10}(e) \cdot \tau(\lambda) \cdot X(\theta) \approx 4.3429448 \cdot \tau_{\text{slant}}$$
- **Physical Validity Domain:**
  - Optical & Near-Infrared wavelengths: $400\text{ nm} \le \lambda \le 2000\text{ nm}$.
  - Reference wavelength: $\lambda_{\text{ref}} = 880\text{ nm}$ (MER Mastcam reference filter).
  - Dust Ångström exponent: $\alpha_{\text{ang}} \approx -0.082$ (in-situ Martian coarse dust, $r_{\text{eff}} \sim 1.5 - 2.5\,\mu\text{m}$, Fernández-Rodríguez et al. 2024 / Lemmon 2019).
  - *Remediation Note (13AE):* The previous 13AD value of $+0.35$ was an unsupported terrestrial fine-aerosol assumption that falsely predicted a ~18% decrease in optical depth at 1550 nm. On Mars, coarse dust produces a flat or slightly negative Ångström exponent ($\alpha \in [-0.16, 0.0]$), resulting in ~5% greater extinction at 1550 nm ($\tau_{1550} \approx 1.05 \tau_{880}$).
- **Failure Boundaries & Breakdown Regimes:**
  - Wavelengths $\lambda > 10\,\mu\text{m}$ (Thermal Infrared to Microwave): Dust grain parameter $x = 2\pi r / \lambda \ll 1$. Optical Beer-Lambert extinction breaks down completely; Rayleigh microwave scattering applies.
  - Negative optical depth $\tau < 0$: Violates thermodynamics and energy conservation.
- **Software Implementation & Defensive Boundaries:**
  - Implemented in `MarsAtmosphericEngine.calculate_optical_attenuation_db`.
  - Negative $\tau$ or non-positive $\lambda$ raises `ValueError`.
  - Default profile configured with `dust_angstrom_exponent = -0.082`.
  - Attenuation capped at $100.0\text{ dB}$ ($T < 10^{-10}$) to prevent floating-point underflow.
- **Reference Citations:**
  - Fernández-Rodríguez, A. et al. (2024), *Atmospheric optical attenuation and turbulence on Mars for optical communications*, arXiv:2404.16955 / 2504.16955.
  - Wolff, M. J. et al. (2009), *Wavelength dependence of dust aerosol properties from Mars Exploration Rover Pancam observations*, J. Geophys. Res. 114, E00D04.
  - Lemmon, M. T. et al. (2014, 2019), *Dust aerosol, clouds, and the atmospheric optical depth record over 5 Mars years of the Mars Exploration Rover mission*, Icarus 251, 96–111.

---

### 2.3 RF Atmospheric Attenuation (Microwave Decoupling & Dielectric Dust Absorption)
- **Governing Equations:**
  $$A_{\text{RF, dB}} = \left[\alpha_{\text{gas}}(f) + \alpha_{\text{dust, RF}}(f, \tau_{\text{dust}})\right] \cdot X(\theta)$$
  $$\alpha_{\text{dust, dB/km}} = 8.186 \times 10^4 \cdot \frac{M}{\lambda_{\text{cm}}} \cdot \text{Im}\left(-\frac{\epsilon_r - 1}{\epsilon_r + 2}\right)$$
  $$\text{where } M \approx 2.0 \times 10^{-4} \cdot \tau_{\text{dust}}\text{ g/m}^3, \quad \text{Im}(-K) \approx 0.005468 \quad (\epsilon_r = 2.8 - j 0.042)$$
- **Physical Validity Domain:**
  - Frequencies: $100\text{ MHz} \le f \le 40\text{ GHz}$ (UHF, S, X, Ka bands).
  - Atmospheric pressure: $P_{\text{surface}} \approx 6.1\text{ mbar}$ pure CO2.
  - Dust loading: $\tau_{\text{dust}} \in [0.1, 5.0]$.
  - *Remediation Note (13AE):* Reconciles 13AD's assertion that Martian dust attenuation is negligible (< 0.5 dB) with NASA/JPL DESCANSO Pub 02-05 and Goldhirsh (2000). While true for UHF (< 0.02 dB) and X-band (< 0.25 dB) in typical dust, Ka-band (32 GHz) experiences 0.76 dB zenith loss under typical dust and up to 8.68 dB zenith (> 40 dB low slant) during severe dust storms.
- **Failure Boundaries & Breakdown Regimes:**
  - Frequencies $f > 60\text{ GHz}$: Sub-millimeter continuum transitions to rotational line absorption.
  - Direct equivalence with optical dust: Applying optical $\tau$ directly to microwave frequencies violates dielectric Rayleigh physics and produces errors > 100 dB.
- **Software Implementation & Defensive Boundaries:**
  - Implemented in `MarsAtmosphericEngine.calculate_rf_atmospheric_attenuation_db`.
  - Gaseous CO2 absorption and Rayleigh dielectric aerosol attenuation evaluated independently and summed.
- **Reference Citations:**
  - Goldhirsh, J. (2000), *Handbook of Radio Wave Propagation for Communication On and Around Mars*, NASA/JPL DESCANSO Publication 02-05.
  - Smith, E. K. & Flock, W. L. (1986), *Propagation Effects on Microwave Satellite Communication on and around Mars*, IEEE Trans. Antennas Propag.

---

### 2.4 Free-Space Path Loss (Friis Far-Field Transmission)
- **Governing Equations:**
  $$\text{FSPL} = 20 \log_{10}\left(\frac{4 \pi R}{\lambda}\right) = 20 \log_{10}\left(\frac{4 \pi R f}{c}\right)$$
- **Physical Validity Domain:**
  - Distance: $R \ge R_{\text{FF}} = \max\left(\frac{2 D^2}{\lambda}, 5 D, 2\lambda\right)$ (Fraunhofer far-field).
  - Frequency: $f > 0\text{ Hz}$.
- **Failure Boundaries & Breakdown Regimes:**
  - $R = 0\text{ m}$: Logarithmic singularity ($\log_{10}(0) = -\infty$).
  - $R < \frac{\lambda}{4\pi}$: Friis formula yields $\text{FSPL} < 0\text{ dB}$, implying passive unamplified power gain and violating conservation of energy.
  - $R < R_{\text{FF}}$: Wavefront curvature introduces significant phase error across aperture, making Fraunhofer far-field gain unphysical.
- **Software Implementation & Defensive Boundaries:**
  - Implemented in `PhysicalLinkBudgetEngine.calculate_free_space_path_loss`.
  - $R = 0$ routed to `CommunicationMedium.LOCAL_BUS` (`FSPL = 0 dB`, rate governed by digital bus).
  - $R < \frac{\lambda}{4\pi}$ strictly raises `ValueError`.
  - $R < R_{\text{FF}}$ returns structured `NEAR_FIELD_OUT_OF_DOMAIN` result.
- **Reference Citations:**
  - Friis, H. T. (1946), *A Note on a Simple Transmission Formula*, Proc. IRE 34, 254–256.
  - IEEE Std 145-2013, *IEEE Standard for Definitions of Terms for Antennas*.

---

### 2.5 Antenna Field Regions & Boundary Criteria
- **Governing Equations:**
  $$R_1 = 0.62 \sqrt{\frac{D^3}{\lambda}} \quad (\text{Reactive Near-Field Boundary})$$
  $$R_{\text{Fresnel}} = \frac{2 D^2}{\lambda} \quad (\text{Radiating Near-Field Boundary})$$
  $$R_{\text{FF}} = \max\left(\frac{2 D^2}{\lambda}, 5 D, 2\lambda\right) \quad (\text{Fraunhofer Boundary})$$
- **Physical Validity Domain:**
  - Directive apertures ($D > \lambda / 2$): Classical ISED GL-01 triple criteria.
  - Electrically small antennas ($D \le \lambda / 2$): Reactive boundary extends to $\lambda / 2\pi$; far field begins at $R \ge 2\lambda$.
- **Failure Boundaries & Breakdown Regimes:**
  - Applying $2 D^2 / \lambda$ to electrically small antennas ($D \le \lambda/2$) yields a boundary inside the reactive induction zone, violating electromagnetic boundary physics.
- **Software Implementation & Defensive Boundaries:**
  - Implemented in `AdvancedAntennaEngine.calculate_field_regions`.
  - Evaluates aperture diameter against wavelength; dynamically selects appropriate standard.
- **Reference Citations:**
  - ISED Canada (2016), *GL-01: Guidelines for the Measurement of Radio Frequency Fields*, Section 2.3.
  - Balanis, C. A. (2016), *Antenna Theory: Analysis and Design*, 4th Edition, John Wiley & Sons, Section 2.2.4.

---

### 2.6 Antenna Radiation Patterns & Pointing Degradation
- **Governing Equations:**
  $$u = \frac{\pi D}{\lambda} \sin\theta_{\text{err}}$$
  $$F(u) = \left|\frac{2 J_1(u)}{u}\right|^2 \quad (\text{Circular Aperture Airy Diffraction Disc})$$
  $$u_1 \approx 3.831706 \quad (\text{First Null}), \quad u_{\text{peak}} \approx 5.136 \quad (\text{First Sidelobe at } -17.58\text{ dB})$$
- **Physical Validity Domain:**
  - Main beam and first/second sidelobes ($u \le 7.0156$).
  - Circular reflector or circular telescope aperture.
- **Failure Boundaries & Breakdown Regimes:**
  - Quadratic approximation $12 (\theta / \text{HPBW})^2$ diverges to $\infty$ at large off-axis angles, ignoring sidelobes.
  - Sidelobe envelope becomes diffuse at large angles due to back-lobe diffraction and feed spillover.
- **Software Implementation & Defensive Boundaries:**
  - Implemented in `AdvancedAntennaEngine.evaluate_radiation_pattern`.
  - Tier 1: Measured/Reference envelopes (e.g. ITU-R S.580).
  - Tier 2: Analytical Airy diffraction pattern with Bessel $J_1(u)$ polynomial evaluation.
  - Tier 3: Out-of-Domain Guard ($40.0\text{ dB}$) with explicit disclosure `computational_guard_applied = True`.
- **Reference Citations:**
  - Airy, G. B. (1835), *On the Diffraction of an Object-glass with Circular Aperture*, Trans. Camb. Phil. Soc. 5, 283–291.
  - ITU-R Recommendation S.580-6, *Radiation diagrams for use as design objectives for antennas of earth stations*.

---

### 2.7 Receiver System Noise Temperature & Johnson-Nyquist Floor
- **Governing Equations:**
  $$T_{\text{sys}} = T_{\text{ant}} + T_{\text{feed}} + T_{\text{rx}} \cdot L_{\text{feed}}$$
  $$T_{\text{feed}} = (L_{\text{feed}} - 1) T_{\text{phys}}, \quad T_{\text{rx}} = (10^{\frac{\text{NF}}{10}} - 1) \cdot 290.0\text{ K}$$
  $$N_0 = k_B \cdot T_{\text{sys}}, \quad k_B = 1.380649 \times 10^{-23}\text{ J/K}$$
- **Physical Validity Domain:**
  - Thermal temperatures: $T_{\text{ant}} \ge 2.725\text{ K}$ (Cosmic Microwave Background).
  - Physical temperature: $T_{\text{phys}} > 0\text{ K}$.
  - System noise temperature: $T_{\text{sys}} > 0\text{ K}$.
- **Failure Boundaries & Breakdown Regimes:**
  - $T_{\text{ant}} < 2.7\text{ K}$: Physically impossible in unobstructed space.
  - Negative noise figure $\text{NF} < 0$: Violates thermodynamics.
- **Software Implementation & Defensive Boundaries:**
  - Implemented in `ReceiverSpec.calculate_system_noise_temp`.
  - Strictly raises `ValueError` on sub-CMB or negative inputs.
- **Reference Citations:**
  - Johnson, J. B. (1928), *Thermal Agitation of Electricity in Conductors*, Phys. Rev. 32, 97.
  - Nyquist, H. (1928), *Thermal Agitation of Electric Charge in Conductors*, Phys. Rev. 32, 110.
  - Fixsen, D. J. (2009), *The Temperature of the Cosmic Microwave Background*, Astrophys. J. 707, 916–920.

---

## 3. Truth Disclosures & Non-Flight Certification Notice

In strict adherence to MarsWalk Project Rules:
1. **Research Simulation Status:** All models in Project Atlas represent computational simulations designed for mission architecture research and software verification.
2. **Non-Astronaut-Rated Notice:** Atlas is a research platform. **Under no circumstances should any route, schedule, or link budget generated by Atlas be considered certified or operationally safe for human spaceflight or real-time astronaut extravehicular activity (EVA).**
3. **Traceability of Empirical Inputs:** Martian atmospheric dust opacities and scale heights are derived from peer-reviewed mission publications (MER Spirit, Opportunity, MRO MCS, Curiosity REMS). Synthetic or assumed parameters are explicitly marked as model estimates.

---

## 4. Milestone 13AE Closure & Reconciliation Status

In Milestone 13AE (`ATLAS-13AE-PROPAGATION-EVIDENCE-CLOSURE`), seven discrepancies in 13AD were formally investigated and reconciled:

1. **Dust Ångström Exponent Direction:** Inverted from +0.35 to traceable in-situ reference -0.082 (Fernández-Rodríguez et al. 2024 / Lemmon 2019). Verified across multi-study literature table.
2. **RF Dust-Storm Attenuation:** Reconciled with NASA/JPL DESCANSO Publication 02-05 (Goldhirsh 2000). Dielectric absorption formula implemented, proving Ka-band loss reaches 8.68 dB zenith (and > 40 dB low slant) during severe dust storms, while UHF remains < 0.15 dB.
3. **MER Dust Scale-Height Interpretation:** Opportunity 19.2 km fit confirmed as an aloft detached dust layer artifact (Lemmon et al. 2014) and retained strictly as an aloft-layer stress case, preserving 11.0 km as the standard global baseline.
4. **Receiver Noise Invariance:** Proved mathematical invariance of $C/N_0$ between Plane A (Antenna Terminals) and Plane B (LNA Input). Zero double-counting verified.
5. **Antenna Screening Criteria:** Fraunhofer distance $\max(2D^2/\lambda, 5D, 2\lambda)$ clarified as an informative screening convention per IEEE Std 145-2013 and ISED GL-01.
6. **Airy Diffraction Model Applicability:** Bounded strictly to ideal, unobstructed, uniformly illuminated circular apertures; realistic reflector degradation bounds (-24 to -30 dB taper, -14 to -16 dB blockage) disclosed.
7. **Regression Evidence Integrity:** Full uninterrupted test suite execution verified: 1,246 passed across 93 test files in 193.82s, 0 failures, 12/12 preflight checks passed, and 9/9 mutations killed (100% score).

