# PROJECT ATLAS — MILESTONE 13AF
# Martian Optical Dust Spectral Model Qualification & Sensitivity Benchmark

**Document Identifier:** `ATLAS-DOC-13AF-OPTICAL-BENCHMARK`  
**Milestone:** 13AF — Atlas Independent Benchmark & Research Freeze  
**Parent Milestone:** 13AE — Propagation Evidence Closure  
**Date:** 2026-11-07  
**Status:** QUALIFIED INDEPENDENT BENCHMARK

---

## 1. Executive Summary & Epistemological Disclosure

Milestone 13AE corrected the mathematical direction of the Martian dust Ångström exponent from the unphysical terrestrial value ($\alpha = +0.35$) to the in-situ coarse dust reference ($\alpha = -0.082$). 

Milestone 13AF undertakes a rigorous epistemological audit of this parameter:
1. **Extrapolation vs Direct Measurement:** The adopted parameter $\alpha = -0.082$ originates from the 2024/2025 deep-space optical communication study (*On the feasibility of laser satellite communications from the Martian surface*, Fernández-Rodríguez et al., arXiv:2404.16955 / 2504.16955). This work utilizes visible-band Mastcam observations ($440 - 880\text{ nm}$) from specific Martian sols and extrapolates optical depth to the near-infrared telecom wavelength ($\lambda = 1550\text{ nm}$). **There are no long-term, direct, in-situ spectrophotometric laser transmission measurements at $1550\text{ nm}$ across the Martian surface.**
2. **Non-Universality of a Single Exponent:** The effective Ångström exponent is a direct function of the atmospheric dust particle size distribution ($r_{\text{eff}}, v_{\text{eff}}$), refractive index, and lifting dynamics. Coarse dust lifted during global dust events exhibits a more negative exponent than ambient background dust. A single constant $\alpha$ cannot be treated as a universal physical truth for all mission seasons.

---

## 2. Governing Equations & Exponent Conventions

In planetary optics, the spectral extinction of mineral dust aerosols follows the power law:

$$\tau(\lambda) = \tau(\lambda_0) \left(\frac{\lambda}{\lambda_0}\right)^{-\alpha}$$

where:
- $\lambda_0 = 880\text{ nm}$ is the primary reference filter of the Mars Exploration Rover (MER) Pancam and Mars Science Laboratory (MSL) Mastcam solar direct-imaging filters.
- $\lambda = 1550\text{ nm}$ is the standard Deep Space Optical Communications (DSOC) downlink laser wavelength.
- $\alpha$ is the Ångström turbidity exponent, defined as:
  $$\alpha = -\frac{d \ln \tau(\lambda)}{d \ln \lambda}$$

The resulting Beer-Lambert optical transmission along a slant path of spherical airmass $X(\theta)$ is:

$$T(\theta, \lambda) = \exp\left(-\tau(\lambda) \cdot X(\theta)\right)$$

and the total one-way atmospheric attenuation in decibels is:

$$A_{\text{opt, dB}}(\theta, \lambda) = -10 \log_{10} T(\theta, \lambda) = 10 \log_{10}(e) \cdot \tau(\lambda) \cdot X(\theta) \approx 4.3429448 \cdot \tau(\lambda) \cdot X(\theta)$$

---

## 3. Comprehensive Sensitivity Evaluation Across Published Literature

We evaluate five distinct configurations representing published literature benchmarks, observational uncertainty limits, and the discredited 13AD baseline.

| Configuration ID | Source & Citation | $\alpha$ | $\frac{\tau(1550)}{\tau(880)}$ | Description & Observational Context |
|:---|:---|:---:|:---:|:---|
| **CONF-OPT-01** | Lemmon et al. (2014) Upper Bound | **$-0.160$** | **$1.0954$** | Severe dust-loading season; active saltation and coarse particle lifting ($r_{\text{eff}} \ge 2.5\,\mu\text{m}$). |
| **CONF-OPT-02** | Fernández-Rodríguez et al. (2024/2025) | **$-0.082$** | **$1.0475$** | Flagship Atlas reference configuration; extrapolated DSOC link baseline. |
| **CONF-OPT-03** | Wolff et al. (2009) CRISM Retrieval | **$-0.047$** | **$1.0270$** | Multi-instrument Pancam/CRISM dust phase function fit for typical ambient haze. |
| **CONF-OPT-04** | Lemmon et al. (2014) Lower Bound | **$-0.036$** | **$1.0206$** | Clear season background dust ($r_{\text{eff}} \approx 1.4\,\mu\text{m}$); minimum NIR opacity ratio. |
| **CONF-OPT-05** | Terrestrial Fine Aerosol (13AD Discredited) | **$+0.350$** | **$0.8202$** | Invalid sub-micron urban aerosol assumption; falsely predicts NIR atmospheric thinning. |

---

## 4. Multi-Scenario Quantitative Comparison

For each configuration, we compute optical depth $\tau_{1550}$, zenith transmission ($X = 1.0$), low-elevation transmission at $10^\circ$ ($X \approx 5.602$), and atmospheric attenuation in decibels across three standard dust scenarios:
1. **Typical Background Dust ($\tau_{880} = 0.5$)**
2. **Regional Dust Storm ($\tau_{880} = 1.5$)**
3. **Severe Planet-Encircling Storm ($\tau_{880} = 3.0$)**

### 4.1 Scenario A: Typical Background Dust ($\tau_{880} = 0.5$)

| Configuration | $\alpha$ | $\tau_{1550}$ | $T_{\text{zenith}}$ ($X=1.0$) | $A_{\text{zenith}}$ (dB) | $T_{10^\circ}$ ($X=5.60$) | $A_{10^\circ}$ (dB) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **CONF-OPT-01** (Lemmon Upper) | $-0.160$ | 0.5477 | 0.5783 | 2.379 dB | 0.0465 | 13.33 dB |
| **CONF-OPT-02** (Atlas Flagship) | $-0.082$ | 0.5238 | 0.5923 | 2.275 dB | 0.0532 | 12.74 dB |
| **CONF-OPT-03** (Wolff CRISM) | $-0.047$ | 0.5135 | 0.5984 | 2.230 dB | 0.0563 | 12.49 dB |
| **CONF-OPT-04** (Lemmon Lower) | $-0.036$ | 0.5103 | 0.6003 | 2.216 dB | 0.0573 | 12.42 dB |
| **CONF-OPT-05** (13AD Terrestrial) | $+0.350$ | 0.4101 | 0.6636 | **1.781 dB** | 0.1005 | **9.98 dB** |

*Analysis:* Under typical background dust, the legitimate Martian literature values span a narrow range of zenith attenuation ($2.22\text{ dB}$ to $2.38\text{ dB}$, a spread of only $0.16\text{ dB}$). The discredited 13AD baseline under-reported optical loss by $\approx 0.50\text{ dB}$ at zenith and nearly $2.8\text{ dB}$ at $10^\circ$ elevation.

---

### 4.2 Scenario B: Regional Dust Storm ($\tau_{880} = 1.5$)

| Configuration | $\alpha$ | $\tau_{1550}$ | $T_{\text{zenith}}$ ($X=1.0$) | $A_{\text{zenith}}$ (dB) | $T_{10^\circ}$ ($X=5.60$) | $A_{10^\circ}$ (dB) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **CONF-OPT-01** (Lemmon Upper) | $-0.160$ | 1.6431 | 0.1934 | 7.136 dB | $1.01 \times 10^{-4}$ | 39.98 dB |
| **CONF-OPT-02** (Atlas Flagship) | $-0.082$ | 1.5713 | 0.2078 | 6.824 dB | $1.50 \times 10^{-4}$ | 38.23 dB |
| **CONF-OPT-03** (Wolff CRISM) | $-0.047$ | 1.5405 | 0.2143 | 6.690 dB | $1.78 \times 10^{-4}$ | 37.48 dB |
| **CONF-OPT-04** (Lemmon Lower) | $-0.036$ | 1.5309 | 0.2163 | 6.649 dB | $1.89 \times 10^{-4}$ | 37.25 dB |
| **CONF-OPT-05** (13AD Terrestrial) | $+0.350$ | 1.2303 | 0.2922 | **5.343 dB** | $1.02 \times 10^{-3}$ | **29.93 dB** |

*Analysis:* During a regional dust storm, the spread between clear-sky and severe coarse-dust exponents widens to $0.49\text{ dB}$ at zenith and $2.73\text{ dB}$ at $10^\circ$. At $10^\circ$, slant attenuation reaches $\approx 38 - 40\text{ dB}$, which exceeds the link margin of any realistic surface-to-orbit laser receiver, causing total optical communication blackout.

---

### 4.3 Scenario C: Severe Dust Storm ($\tau_{880} = 3.0$)

| Configuration | $\alpha$ | $\tau_{1550}$ | $T_{\text{zenith}}$ ($X=1.0$) | $A_{\text{zenith}}$ (dB) | $T_{10^\circ}$ ($X=5.60$) | $A_{10^\circ}$ (dB) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **CONF-OPT-01** (Lemmon Upper) | $-0.160$ | 3.2862 | 0.0374 | 14.272 dB | $1.01 \times 10^{-8}$ | 79.95 dB |
| **CONF-OPT-02** (Atlas Flagship) | $-0.082$ | 3.1426 | 0.0432 | 13.648 dB | $2.26 \times 10^{-8}$ | 76.46 dB |
| **CONF-OPT-03** (Wolff CRISM) | $-0.047$ | 3.0810 | 0.0459 | 13.381 dB | $3.18 \times 10^{-8}$ | 74.96 dB |
| **CONF-OPT-04** (Lemmon Lower) | $-0.036$ | 3.0618 | 0.0468 | 13.297 dB | $3.56 \times 10^{-8}$ | 74.50 dB |
| **CONF-OPT-05** (13AD Terrestrial) | $+0.350$ | 2.4606 | 0.0854 | **10.686 dB** | $1.03 \times 10^{-6}$ | **59.87 dB** |

---

## 5. Particle-Size Distribution Mechanics & Microphysical Context

The physical explanation for why the Martian Ångström exponent is near zero or slightly negative lies in the aerosol particle size parameter:

$$x = \frac{2 \pi r_{\text{eff}}}{\lambda}$$

1. **Terrestrial Urban Aerosols ($\alpha \approx +1.0\text{ to }+1.8$):**
   Dominated by fine sub-micron particles ($r_{\text{eff}} \approx 0.1 - 0.3\,\mu\text{m}$). At visible/NIR wavelengths, $x \ll 1$ (Rayleigh to early Mie transition), where scattering efficiency $Q_{\text{ext}} \propto \lambda^{-4}$ or $\lambda^{-2}$, causing strong wavelength decline.
2. **Martian Mineral Dust ($\alpha \approx -0.04\text{ to }-0.16$):**
   In-situ measurements by Viking, Pathfinder, MER Pancam, and MSL Mastcam establish a modified gamma or log-normal size distribution:
   $$\frac{dn}{dr} = C r^{\frac{1-3v_{\text{eff}}}{v_{\text{eff}}}} \exp\left(-\frac{r}{r_{\text{eff}} v_{\text{eff}}}\right)$$
   with effective radius $r_{\text{eff}} \approx 1.5\text{ to }2.5\,\mu\text{m}$ and effective variance $v_{\text{eff}} \approx 0.2\text{ to }0.5$.
   At $\lambda = 880\text{ nm}$, $x \approx 10.7$. At $\lambda = 1550\text{ nm}$, $x \approx 6.1$.
   Both values sit in the flat, oscillatory "anomalous diffraction" regime of the Mie extinction curve where $Q_{\text{ext}} \approx 2.0 - 2.2$. Because the imaginary refractive index of Martian basaltic dust has slight absorption features in the NIR (ferric oxides / silicates), $Q_{\text{ext}}$ at $1550\text{ nm}$ is slightly higher than at $880\text{ nm}$, yielding $\tau(1550) > \tau(880)$ ($\alpha < 0$).

---

## 6. Standalone Reference Verification & Production Alignment

A dedicated standalone benchmark module was constructed completely independent of the Atlas codebase:

- Location: `research/13af_propagation_benchmarks/benchmark_optical_dust.py`
- Executed independently with pure Python standard library and standard math quadrature.
- Confirmed that Atlas production engine (`MarsAtmosphericEngine.calculate_optical_attenuation_db`) matches the independent benchmark across all five configurations to within $< 0.001\text{ dB}$.
- Production telemetry confirmed to output explicit metadata disclosing that $1550\text{ nm}$ is an extrapolated modeling value.
