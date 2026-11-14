# PROJECT ATLAS RESEARCH BASELINE 2.0
## Standalone Evaluation Package & Scientific Reproduction Guide for External Researchers

**Package Designation:** `ATLAS-RESEARCH-BASELINE-2.0`  
**Parent Milestone:** `ATLAS-13AF-INDEPENDENT-BENCHMARK`  
**Repository:** `https://github.com/nasa-spaceapps/marswalk` (Project Atlas)  
**Publication Reference:** MarsWalk 2.0 / Project Atlas Scientific Evaluation Package  
**Status:** `QUALIFIED_FOR_INTERNAL_RESEARCH_PREVIEW`  
**Release Date:** 2026-11-07  

---

## 1. Executive Summary & Purpose

This package provides external researchers, telecommunications engineers, and planetary scientists with a self-contained, reproducible test suite and independent reference calculations for the Martian propagation, radiative transfer, receiver noise, and antenna models implemented in **Project Atlas**.

Project Atlas is an integrated autonomous planetary mission simulation platform developed for the NASA International Space Apps Challenge. Milestone 13AF establishes an independent benchmark baseline where every physical equation, numerical assumption, parameter provenance, and boundary condition is explicitly cataloged and verified against primary literature (MER Pancam/Opportunity, Viking, Mars Pathfinder, Curiosity REMS, NASA JPL Deep Space Communications Handbooks, Goldhirsh 2000, and Ho & Golshan 2000).

---

## 2. Scientific Principles & Non-Probabilistic Disclosures

In accordance with MarsWalk Scientific Integrity Rules:

1. **Explicit Extrapolation Disclosure:** The 1550 nm optical laser communication attenuation model uses an Ångström power-law extrapolation ($\alpha = -0.082$) derived from MER Pancam 440–880 nm observations. It is **not** an in-situ optical laser transmission measurement.
2. **Dielectric Analog Disclosure:** RF dust storm attenuation calculations use an effective relative permittivity $\epsilon_r = 2.80 - j 0.0420$ ($\tan\delta \approx 0.015, \text{Im}(-K) \approx 0.005468$) derived from dry terrestrial basalt powder and Apollo lunar regolith analogs at microwave frequencies. Direct in-situ dielectric measurements of suspended Martian dust storms do not currently exist.
3. **Rayleigh Absorption Regime:** At microwave frequencies up to Ka-band (32 GHz), the electromagnetic size parameter $x = 2 \pi r / \lambda \le 0.0134 \ll 1$ for coarse 20 µm particles. Rayleigh absorption dominates over scattering by $> 10^7$ ($\sigma_{\text{sca}} / \sigma_{\text{abs}} < 4.2 \times 10^{-5}$); Mie scattering corrections are negligible ($< 0.01\%$).
4. **CMB Equivalent Brightness Departure:** At microwave frequencies, the Rayleigh-Jeans equivalent brightness temperature departs from the thermodynamic CMB temperature (2.725 K). At Ka-band (32 GHz), $T_{\text{RJ}} = 2.029\text{ K}$ (a departure of $-0.70\text{ K}$ or $-25.5\%$). The 2.7 K floor in Atlas is an operational engineering convenience that slightly overestimates cold-sky receiver noise.
5. **No Flight Certification:** All simulation models, link budget assessments, and contact schedules are exploratory research models. **None are flight-certified or operationally safe for astronauts without physical validation.**

---

## 3. Directory Layout

```text
research/
├── Atlas_Research_Baseline_2.0/
│   ├── README.md                                  # This independent evaluation guide
│   ├── parameter_provenance_registry.json         # Complete parameters and provenance metadata
│   ├── optical_angstrom_sensitivity_table.csv     # Multi-study Ångström spectral table
│   └── rf_dust_attenuation_table.csv              # Multi-frequency RF dust attenuation table
└── 13af_propagation_benchmarks/
    ├── benchmark_optical_dust.py                  # Standalone optical dust benchmark
    ├── benchmark_rf_dust.py                       # Standalone RF dust attenuation benchmark
    ├── benchmark_receiver_noise.py                # Standalone receiver noise benchmark
    ├── benchmark_antenna_patterns.py              # Standalone antenna radiation pattern benchmark
    ├── run_all_benchmarks.py                      # Flagship test runner (zero external dependencies)
    └── benchmark_results_summary.json             # Benchmark execution metrics
```

---

## 4. Environment Setup & Standalone Reproduction

The independent benchmark harness has **zero dependencies on the Atlas core codebase** and requires only standard Python 3.10+ with standard library modules (`math`, `json`, `dataclasses`).

### Quick Start (Zero Dependencies)

```bash
# Navigate to the benchmark suite
cd research/13af_propagation_benchmarks

# Run all 4 independent benchmarks simultaneously
python run_all_benchmarks.py
```

### Expected Output Summary

```text
================================================================================
ATLAS MILESTONE 13AF: INDEPENDENT PROPAGATION BENCHMARK SUITE
================================================================================
Running: Benchmark 1 - Optical Dust Spectral Propagation...
  [PASS] Benchmark 1: Optical Dust Attenuation replicated within 0.01 dB tolerance.

Running: Benchmark 2 - RF Dust-Storm Microwave Attenuation...
  [PASS] Benchmark 2: RF Dust Attenuation replicated within 0.005 dB tolerance.

Running: Benchmark 3 - Receiver System Noise Temperature & Reference Plane...
  [PASS] Benchmark 3: Receiver Noise replicated within 1e-12 dB tolerance.

Running: Benchmark 4 - Antenna Radiation Patterns & Far-Field Limits...
  [PASS] Benchmark 4: Antenna Radiation Patterns replicated within 0.01 dB tolerance.

================================================================================
ALL 4 INDEPENDENT PROPAGATION BENCHMARKS PASSED SUCCESSFULLY.
Summary metrics saved to: benchmark_results_summary.json
================================================================================
```

---

## 5. Parameter Provenance Registry

| Parameter | Value | Source / Primary Citation | Scientific Status |
|:---|:---:|:---|:---|
| **Martian Radius ($R_M$)** | $3,389.5\text{ km}$ | NASA Mars Fact Sheet (IAU/IAG 2015) | Standard Planetary Geodesy |
| **Surface Atmospheric Density ($\rho_0$)** | $0.020\text{ kg/m}^3$ | Viking Lander / Mars-GRAM Reference | Validated In-Situ Inversion |
| **Atmospheric Scale Height ($H_{\text{atm}}$)** | $11.1\text{ km}$ | Viking / Mars Pathfinder / REMS | Validated In-Situ Inversion |
| **Typical Dust Scale Height ($H_{\text{dust}}$)** | $10.0\text{ km}$ | MER Pancam (Lemmon et al. 2004, 2014) | Validated In-Situ Inversion |
| **Aloft Dust Layer Stress Height** | $19.2\text{ km}$ | MER Opportunity (Lemmon et al. 2014) | Detached Layer Stress Case |
| **Dust Ångström Exponent ($\alpha$)** | $-0.082$ | Fernández-Rodríguez et al. (2024 / arXiv:2504.16955) | Extrapolated Model from 880 nm |
| **RF Dust Permittivity ($\epsilon_r$)** | $2.80 - j 0.0420$ | Basalt / Lunar Regolith (Campbell & Ulrichs 1969; Goldhirsh 2000) | Dry Terrestrial / Lunar Analog |
| **RF Dust Polarizability Factor ($\text{Im}(-K)$)** | $0.005468$ | Analytical Maxwell Garnett / Rayleigh derived | Analytical Calculation |
| **Dust Grain Density ($\rho_{\text{grain}}$)** | $2.5\times 10^3\text{ kg/m}^3$ | Basalt / Silicate analog (Goldhirsh 2000) | Analog Baseline |
| **Cosmic Microwave Background ($T_{\text{CMB}}$)** | $2.725\text{ K}$ | Fixsen (2009) COBE/FIRAS | Fundamental Astrophysics |
| **Antenna Aperture Efficiency ($\eta$)** | $0.55$ | NASA JPL DSN / DESCANSO Handbook | Industry Standard Antenna Engineering |

---

## 6. Reviewer Verification Checklist & Challenge Questions

External reviewers are encouraged to verify the following physical test cases:

1. **Spectral Reversal Test:** Does setting $\alpha > 0$ invert optical attenuation so 1550 nm experiences less loss than 880 nm?  
   *Atlas assertion:* At $\alpha = -0.082$, optical depth at 1550 nm is $\tau_{1550} = \tau_{880} \cdot (1550/880)^{0.082} = 1.047 \cdot \tau_{880}$. Longer wavelengths suffer slightly higher dust extinction due to the negative slope of the extinction efficiency curve $Q_{\text{ext}}(\lambda)$ in the near-infrared for $r_{\text{eff}} \approx 1.5\,\mu\text{m}$.
2. **Rayleigh Size Parameter Limit:** Is the Rayleigh approximation valid at 32 GHz for $20\,\mu\text{m}$ particles?  
   *Atlas calculation:* $x = 2 \pi (20\times 10^{-6}) / (9.375\times 10^{-3}) = 0.0134 \ll 1$. $\sigma_{\text{sca}} / \sigma_{\text{abs}} = 4.19\times 10^{-5}$. Rayleigh absorption is verified.
3. **Reference Plane Invariance:** Does carrier-to-noise spectral density $(C/N_0)$ depend on whether the link budget is referenced at the antenna terminals or the LNA input?  
   *Atlas proof:* $(C/N_0)_A = (C/N_0)_B$ with absolute difference $< 10^{-12}\text{ dB}$. Reference plane selection does not alter achievable data rate or link margin.
4. **Link Survivability Truth Disclosure:** Does negligible RF dust attenuation guarantee communication link closure?  
   *Atlas proof:* In Scenario 3 (0.5 W rover beacon at 2.5° elevation, range 2,280 km), dust loss is only $0.009\text{ dB}$, but the link completely fails ($C/N_0 = 48.16\text{ dB-Hz} < 48.81\text{ dB-Hz}$ threshold, achievable rate $3.6\text{ kbps} < 8.0\text{ kbps}$, operational rate $0\text{ bps}$) due to free-space path loss and chassis pattern roll-off.
