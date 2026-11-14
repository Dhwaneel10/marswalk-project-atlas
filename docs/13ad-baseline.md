# Milestone 13AD — Stage 0 Baseline Report
## Pre-Investigation Environment, 13AC State Preservation & Baseline Verification

**Mission Designation:** `ATLAS-13AD-MARS-PHYSICS-VALIDATION`  
**Parent Milestone:** `ATLAS-13AC-PHYSICS-BOUNDARY`  
**Timestamp:** 2026-11-07T04:37:00Z  
**Operating Environment:** Windows 11 Home Single Language (Build 10.0.26300, 64-bit), Python 3.12.4 (`.venv`), pytest 9.1.1, numpy 2.5.4  
**Atlas Daemon:** Running on `http://127.0.0.1:3000` (task-31274, HTTP 200, 24 endpoints active)  
**Status:** BASELINE VERIFIED & PRESERVED  

---

## 1. Baseline System State

### 1.1 Git Status & Repository Cleanliness
- Working Directory: `E:\Python\NASA-Spaceapps\Marswalk`
- Branch: `main` (active repository, untracked/staged files preserved)
- Working Tree: All user files, prior artifacts, test scripts, and benchmark outputs intact.

### 1.2 Verification Metrics from 13AC
- **Total Test Suite:** 1,224 tests passing across unit, integration, metamorphic, adversarial, and boundary suites (0 failures, 2 benign pending deprecation warnings).
- **13AC Dedicated Boundary Suite:** 17 tests passed in 0.41s (`tests/test_milestone_13ac_physics_boundaries.py`).
- **Mutation Kill Rate:** 100% (4/4 mutations killed in `scratch/run_mutation_campaign.py`).
- **Preflight Verification:** 12/12 checkpoints passed in 429.9 ms.
- **Physical Model Register:** 10 registered models in `docs/13ac-model-validity-register.md`.

---

## 2. 13AC Model Configurations Under Investigation

### 2.1 Atmospheric Propagation Model
- **Current Model:**
  - Elevation $\theta \ge 5.0^\circ$: Flat-slab airmass $X(\theta) = 1 / \sin\theta$.
  - Elevation $0.0^\circ < \theta < 5.0^\circ$: Rozenberg empirical approximation:
    $$X(\theta) = \frac{1}{\sin\theta + 0.025 \exp(-11.0 \sin\theta)}$$
  - Elevation $\theta \le 0.0^\circ$: Raises `ValueError` in direct calculation, evaluated as `OCCULTED_BELOW_HORIZON` in `evaluate_link`.
- **Target of 13AD Investigation:**
  - Rozenberg formula was derived for Earth's twilight atmosphere, not Mars.
  - Does not account for Martian dust scale height ($H \approx 11\text{--}19\text{ km}$ from MER Spirit/Opportunity observations by Lemmon et al. 2014) or true spherical path integration along arbitrary observer-target geometries.
  - Optical dust extinction and RF attenuation are currently handled through coarse constants without spectral distinction or path-integral derivation.

### 2.2 Antenna Field-Region & Far-Field Validity
- **Current Model:**
  - Aperture diameter estimated via $D = (\lambda / \pi) \sqrt{10^{G/10} / \eta}$.
  - Fraunhofer distance $R_{\text{ff}} = \max(2 D^2 / \lambda, 2\lambda)$.
  - $R < R_{\text{ff}}$ tagged as `NEAR_FIELD_OUT_OF_DOMAIN`.
- **Target of 13AD Investigation:**
  - Classical Fraunhofer distance $2 D^2 / \lambda$ assumes large directive apertures ($D \gg \lambda$) and small phase deviations ($\pi/8$ rad).
  - Additional distance conditions ($R \gg D$ and $R \gg \lambda$) are required by IEEE 145 and ISED GL-01.
  - Need explicit multi-criteria field-region breakdown: Reactive Near-Field ($R < 0.62\sqrt{D^3/\lambda}$), Radiating Near-Field / Fresnel ($0.62\sqrt{D^3/\lambda} \le R < 2D^2/\lambda$), and Fraunhofer Far-Field ($R \ge 2D^2/\lambda$).

### 2.3 Antenna Radiation Pattern & Off-Axis Pointing Loss
- **Current Model:**
  - $L_{\text{point}} = 12 (\theta_{\text{err}} / \text{HPBW})^2\text{ dB}$, capped at 40 dB tracking loss for $\theta_{\text{err}} \ge 2.5\times \text{HPBW}$.
- **Target of 13AD Investigation:**
  - A quadratic cap is not an antenna radiation pattern. Real directive antennas exhibit Bessel/Airy patterns ($J_1(u)/u$), sidelobes, nulls, and backlobes.
  - Establish a 3-tier hierarchy: Level 1 (measured/reference pattern), Level 2 (Airy/Bessel circular aperture approximation), Level 3 (out-of-domain with exposed computational guard metadata).

### 2.4 Communication Medium Semantics
- **Current Model:** $R = 0$ returns `COLLOCATED_LOCAL_INTERFACE` with $0\text{ dB}$ loss and 1 Gbps rate.
- **Target of 13AD Investigation:** Ensure local bus communication is cleanly typed as a non-RF medium and cannot be registered as an RF link or orbital contact.

### 2.5 System Noise Temperature & Physical Constants
- **Current Model:** $T_{\text{sys}} \le 0\text{ K}$ raises `ValueError`.
- **Target of 13AD Investigation:** Clarify operating-domain justification (receiver thermal noise model) and verify antenna background temperature, receiver equivalent noise temperature, and exact SI $k_B = 1.380649\times 10^{-23}\text{ J/K}$.

---

## 3. Reproduction of 13AC Baseline Tests

Execution of `pytest tests/test_milestone_13ac_physics_boundaries.py` yielded:
```text
17 passed in 0.41s (100% pass rate)
```
Execution of `scripts/preflight_check.py` yielded:
```text
12/12 checks passed, 0 warnings, 0 failures in 429.9ms.
```

The system is in a stable, verified baseline condition. We are ready to proceed with Stage 1.
