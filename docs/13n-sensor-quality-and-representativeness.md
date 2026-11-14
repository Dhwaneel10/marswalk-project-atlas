# Milestone 13N: Sensor Quality Screening & Representativeness Framework Audit
**Document ID:** `DOC-13N-SENS-004`  
**Milestone:** 13N — The Scientific Reproducibility Tribunal  
**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** November 2026  
**Auditor:** Scientific Reproducibility Tribunal (Reviewer A & Lead Integration Owner)  
**Status:** AUDITED & VERIFIED  

---

## 1. Executive Summary

This investigation audits the sensor data-quality screening and environmental representativeness formulations implemented in Milestone 13M. The Tribunal specifically challenged:
1. Whether published hardware degradation events (MEDA Wind Sensor grit damage) are correctly isolated without synthetic imputation.
2. Whether geometric obscuration rules (TIRS rover self-shadowing, ATS aft-deck thermal wake) reflect authentic spacecraft engineering constraints.
3. Whether the Composite Representativeness Index (CRI) uses defensible mathematical physics or masks dimensional discrepancies behind an arbitrary average.

---

## 2. In-Situ Sensor Quality Screening Audit

### 2.1 Perseverance MEDA Wind Sensor (WS) Grit Damage
- **Documented Flight Event:** During descent stage landing thruster impingement (Sol 0) and high-velocity saltation events around Sol 270, wind sensor booms 1 and 2 suffered severe dust and pebble impacts, damaging micro-machined hot-film anemometers (Newman et al., 2022, JGR Planets).
- **Audit of Implementation:** In `planetary_data_quality.py`, degraded wind sensors are assigned status `DEGRADED` (code 2) and excluded from parameter optimization.
- **Strict Null Preservation:** In `planetary_archive_ingestion.py`, invalid or uncalibrated wind records are stored with `observed_value: None`. No spline smoothing, synthetic wind generation, or fake data filling is performed.

### 2.2 MEDA Thermal Infrared Sensor (TIRS) Shadow & Obscuration
- **Physical Context:** TIRS measures downward radiometric flux from an upward-looking sensor and ground radiometric flux from a downward-looking sensor mounted on the Remote Sensing Mast (RSM).
- **Geometric Screening Flags:** The PDS RDR Sol 10 records contain 8 boolean hardware flags:
  - `RSM_HEAD_OUTSIDE_TIRS_UPWARD_LOOKING_FOV` (must be 1)
  - `TIRS_GROUND_FOOTPRINT_NOT_IN_SHADOW` (must be 1)
  - `ROVER_STILL` (must be 1)
  - `ROVER_LOW_TILT` (must be 1)
- **Tribunal Code Audit:** In `filter_tirs_measurement()`, if `ground_not_in_shadow == 0`, status is immediately set to `REJECTED_SHADOW` and 1-sigma uncertainty is inflated by $1.8\times$.

### 2.3 MEDA Air Temperature Sensors (ATS) Mast Thermal Wake
- **Physical Context:** ATS1 through ATS5 consist of platinum RTDs mounted at $1.45\text{ m}$ on the mast and on the front chassis. When winds blow from the rear across the Multi-Mission Radioisotope Thermoelectric Generator (MMRTG), thermal convection elevates measured air temperatures by $+1.5\text{ to }+4.0\text{ K}$.
- **Screening Rule:** Validated mast air temperature is computed by taking the robust median of the unflagged RTD sensors, successfully isolating isolated hardware drift.

---

## 3. Mathematical Representativeness (CRI) Audit

The Tribunal audited `PlanetaryRepresentativenessEngine` in `src/marswalk/core/environmental_representativeness.py`:

### 3.1 Multiplicative Formulation vs Additive Average
Milestone 13M implements CRI as a joint multiplicative probability kernel:
$$\text{CRI} = s_\text{spatial} \times s_\text{temporal} \times s_\text{seasonal} \times s_\text{vertical}$$
where each sub-score $s_i = \exp(-\Delta_i / L_i) \in (0, 1]$.

**Tribunal Finding:** A simple weighted arithmetic mean ($w_1 s_1 + w_2 s_2 + \dots$) can produce a falsely reassuring score (e.g. $0.75$) even if one dimension is completely invalid (e.g. $s_\text{seasonal} = 0.0$ across opposite seasons). The **multiplicative formulation** ensures that if any single physical dimension collapses, the Composite Representativeness Index asymptotically drops to zero.

### 3.2 Non-Comparable Priority Gate
Lines 101–104 enforce an unconditional override:
$$\text{If } |\Delta L_s| > 60.0^\circ \quad \text{or} \quad |\Delta z| > 600.0\text{ m} \implies \text{Context} = \mathbf{NON\_COMPARABLE}$$
This prevents crater-floor observations from being erroneously extrapolated up steep $800\text{ m}$ crater rim escarpments regardless of 2D horizontal proximity.

**Tribunal Verdict:** `REPRESENTATIVENESS FORMULATION IS PHYSICALLY SOUND & DEFENDED`
