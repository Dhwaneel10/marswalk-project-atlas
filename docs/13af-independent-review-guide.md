# PROJECT ATLAS — MILESTONE 13AF
# Independent Scientific Reviewer Guide & Replication Instructions

**Mission Designation:** `ATLAS-13AF-INDEPENDENT-BENCHMARK`  
**System:** Project Atlas / MarsWalk 2.0  
**Target Audience:** External Scientific Reviewers, Planetary Telecommunications Engineers, Peer Evaluators  
**Scope:** Martian Radiative Transfer, RF Microwave Dust Storm Attenuation, Antenna Modeling, Receiver Noise Decomposition, Cross-Module Link Feasibility  
**Date:** 2026-11-07  
**Disposition Gate:** `QUALIFIED_FOR_INTERNAL_RESEARCH_PREVIEW`  

---

## 1. Introduction for External Reviewers

Welcome to the independent scientific evaluation package for Project Atlas. This guide provides peer reviewers with everything necessary to independently verify, challenge, replicate, and audit the communications and planetary physics simulation models within Project Atlas.

Atlas is an integrated autonomous mission planning platform developed for Mars surface and orbital operations. In Milestones 13AC–13AF, the team transitioned Atlas from empirical engineering approximations to rigorous physical models grounded in primary literature.

Every equation in this benchmark can be run independently of the Atlas core system using standard Python (`math`, `json`, `dataclasses`) with zero external package dependencies.

---

## 2. Replication Instructions

### 2.1 One-Line Reproduction

```bash
python research/13af_propagation_benchmarks/run_all_benchmarks.py
```

### 2.2 Independent Test Execution

| Benchmark | Script | Replicated Phenomenon | Analytical Standard | Tolerance |
|:---|:---|:---|:---|:---:|
| **BM-1** | `benchmark_optical_dust.py` | Spherical optical airmass, Ångström spectral scaling ($\alpha = -0.082$) | Lambert-Beer $T = e^{-\tau m}$, $\tau_{1550} = 0.5236$ | $\pm 0.01\text{ dB}$ |
| **BM-2** | `benchmark_rf_dust.py` | Multiband RF dust loss (401.5 MHz–32 GHz), Rayleigh limit ($x \le 0.0134$) | Goldhirsh (2000), Ho & Golshan (2000), JPL handbooks | $\pm 0.005\text{ dB}$ |
| **BM-3** | `benchmark_receiver_noise.py` | Noise temperature decomposition, Plane A/B invariance, Planck vs RJ | Nyquist-Johnson $k T B$, Fixsen (2009) CMB | $\pm 10^{-12}\text{ dB}$ |
| **BM-4** | `benchmark_antenna_patterns.py` | Fraunhofer distance, Airy pattern, broadbeam pointing loss guard | Silver (1949), ITU-R S.580, Balanis (2016) | $\pm 0.01\text{ dB}$ |

---

## 3. Core Scientific Discrepancy Reconciliations

Reviewers should review how the following seven critical scientific questions were reconciled:

### 3.1 1550 nm Optical Attenuation Extrapolation
- **Finding:** No direct in-situ laser transmission measurement at 1550 nm has been conducted on the surface of Mars.
- **Reconciliation:** Atlas explicitly discloses in both API outputs (`is_extrapolated_wavelength: True`) and telemetry that 1550 nm is derived from MER Pancam 440–880 nm observations using an Ångström exponent $\alpha = -0.082$ (Fernández-Rodríguez et al. 2024 / 2025 preprint arXiv:2504.16955).
- **Physical Consequence:** At $\alpha = -0.082$, optical depth increases slightly in the near-infrared ($\tau_{1550} / \tau_{880} \approx 1.047$). For $\tau_{880} = 0.5$, $\tau_{1550} = 0.5236$, producing $2.27\text{ dB}$ attenuation at zenith.

### 3.2 RF Dust Storm Attenuation & Literature Variance
- **Finding:** Goldhirsh (2000) reports $\sim 1.3\text{ dB}$ worst-case zenith attenuation at 32 GHz for coarse $20\,\mu\text{m}$ particles, whereas Ho & Golshan (2000) report $\sim 1.0\text{ dB}$ typical and $\ge 3.0\text{ dB}$ in severe global dust storms.
- **Reconciliation:** Both models are mathematically identical under Rayleigh absorption. The variance arises purely from differing assumptions regarding total suspended column mass ($M = 0.078\text{ g/m}^2$ typical vs $M = 2.44\text{ g/m}^2$ severe dust storms) and scale height. Atlas implements both models and demonstrates exact numerical agreement when normalized to column mass.

### 3.3 Dielectric Permittivity Source Provenance
- **Finding:** The complex relative permittivity $\epsilon_r = 2.80 - j 0.0420$ ($\tan\delta \approx 0.015$) is frequently cited as "Martian dust permittivity".
- **Reconciliation:** Historical review confirms this value is derived from laboratory measurements on terrestrial basalt powders and Apollo lunar soil samples under zero moisture conditions (Campbell & Ulrichs 1969; Olhoeft & Strangway 1975; Goldhirsh 2000). Atlas explicitly labels this parameter as an analog proxy.

### 3.4 Cosmic Microwave Background vs Rayleigh-Jeans Departure
- **Finding:** Enforcing a flat $2.725\text{ K}$ lower bound on receiver antenna temperature in Rayleigh-Jeans formulas over-estimates cold-sky noise at high frequencies.
- **Reconciliation:** At 32 GHz (Ka-band), the Planck equivalent Rayleigh-Jeans brightness temperature is $T_{\text{RJ}} = 2.029\text{ K}$, departing by $-0.70\text{ K}$ ($-25.5\%$) from the thermodynamic $2.725\text{ K}$ value. Atlas retains the $2.7\text{ K}$ floor as a conservative engineering lower bound and explicitly notes this analytical departure.

### 3.5 Opportunity 19.2 km Scale-Height Provenance
- **Finding:** Opportunity Pancam observations reported an apparent dust scale height of $19.2\text{ km}$ (Lemmon et al. 2014, Section 4.3).
- **Reconciliation:** This value was an artifact of fitting a single-exponential profile to an atmosphere containing a high-altitude detached dust layer (identified by MRO Mars Climate Sounder). Atlas categorizes $19.2\text{ km}$ strictly as an aloft dust layer stress case, retaining $10.0\text{ km}$ as the validated well-mixed tropospheric baseline.

### 3.6 Antenna Patterns: Airy Disc vs Real Blocked Apertures
- **Finding:** Analytical Bessel $J_1(u)/u$ models predict deep nulls ($-\infty\text{ dB}$) and first sidelobes at $-17.57\text{ dB}$, which do not reflect real Cassegrain or Gregorian antennas.
- **Reconciliation:** Atlas bounds pointing loss to $-30\text{ dB}$, applies a broadbeam pointing guard ($0.1\text{ dB}$) for low-gain antennas, and references ITU-R S.580 / NASA DSN empirical envelope standards for operational communications modeling.

### 3.7 Link Survivability vs Propagation Demarcation
- **Finding:** Previous reports claimed that low UHF dust loss "guarantees rover proximity survivability".
- **Reconciliation:** Atlas formally demarcates six operational tiers (Dust Propagation Loss $\rightarrow$ Total Propagation Loss $\rightarrow$ Link Margin $\rightarrow$ Link Availability $\rightarrow$ Hardware Reliability $\rightarrow$ Mission Survivability). Negligible dust loss ($\le 0.01\text{ dB}$) does not guarantee communication; in Scenario 3, a 0.5 W rover beacon at 2.5° elevation fails completely ($0\text{ bps}$, achievable rate $3.6\text{ kbps} < 8.0\text{ kbps}$) due to free-space loss and chassis pattern roll-off.

---

## 4. Peer Reviewer Verification Checklist

Reviewers can verify compliance by executing the test assertions:

- [ ] Execute `python research/13af_propagation_benchmarks/run_all_benchmarks.py` $\rightarrow$ 4/4 PASS.
- [ ] Verify optical wavelength scaling: $\tau_{1550} > \tau_{880}$ for $\alpha = -0.082$.
- [ ] Verify RF Rayleigh limit: $x \le 0.0134 \ll 1$ at 32 GHz for $r = 20\,\mu\text{m}$.
- [ ] Verify reference plane invariance: $(C/N_0)_A = (C/N_0)_B$ within $10^{-12}\text{ dB}$.
- [ ] Verify negative margin link rejection: `is_link_closed == False` and `operational_rate_bps == 0`.
- [ ] Verify mutation resilience: 8/8 targeted mutations caught by automated test suites.

---

## 5. Reviewer Sign-Off Block

```text
================================================================================
PROJECT ATLAS INDEPENDENT BENCHMARK REVIEW SIGN-OFF
================================================================================
Reviewer Organization: _________________________________________________________
Lead Reviewer:         _________________________________________________________
Date of Evaluation:    _________________________________________________________
Disposition Recommendation:
  [ ] QUALIFIED FOR RESEARCH REPRODUCTION
  [ ] QUALIFIED WITH RESERVATIONS (Specify in comments)
  [ ] REJECTED (Specify unphysical models or numerical defects)

Comments:
________________________________________________________________________________
________________________________________________________________________________
================================================================================
```
