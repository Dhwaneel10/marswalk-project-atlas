# Milestone 13N: Calibration Reproducibility Report — The 52.1% RMSE Claim
**Document ID:** `DOC-13N-REPRO-005`  
**Milestone:** 13N — The Scientific Reproducibility Tribunal  
**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** November 2026  
**Auditor:** Scientific Reproducibility Tribunal (Reviewer B & Lead Integration Owner)  
**Status:** AUDITED, QUALIFIED & CHALLENGED  

---

## 1. Executive Summary & The Central Question

**Central Question:** *Can an independent engineer reproduce the reported 52.1% reduction in held-out RMSE from the preserved data, code, configuration, and methods?*

### The Tribunal Verdict: `REPRODUCED_WITH_CRITICAL_DEVIATIONS`
1. **Reproduced on Benchmark Slice ($N=300$):** When executed on the initial $N=300$ observation slice (`recs[:300]`), the Tribunal **reproduced the exact figures**:
   - Baseline Training RMSE: $51.00\text{ K} \implies$ Calibrated: $20.83\text{ K}$ (**59.16% reduction** vs reported 59.2%).
   - Baseline Held-Out RMSE: $50.64\text{ K} \implies$ Calibrated: $24.26\text{ K}$ (**52.10% reduction** vs reported 52.1%).
   - Bootstrap 95% Confidence Interval for held-out improvement: $[46.8\%, 56.4\%]$ with median $52.2\%$.
2. **Critical Discovery — Split Implementation Divergence:**
   - The 13M documentation claimed a chronological split at Sol 916 (Sols 0–916 train, Sols 917–1527 test).
   - In code (`environment_model_calibration.py:84`), the split was actually implemented as an interleaved modulo-10 partition: `(sol % 10) < 6`.
   - This creates subtle temporal dependence across the boundary (training on sols $0\dots5$ and evaluating on sols $6\dots9$ of the exact same month/season).
3. **Critical Discovery — Multi-Year Generalization Collapse:**
   - When the same static 3-parameter diurnal spline is evaluated across the complete 1,527-sol multi-year mission ($N=4,573$), the held-out improvement collapses to **4.23%** (and exhibits overfitting in transitional seasons).
   - Root Cause: A static diurnal spline ($T_\text{mean}, T_\text{amp}, \text{phase\_shift}$) cannot account for the $\pm 25\text{ K}$ annual seasonal swing driven by Mars's orbital eccentricity ($e=0.0934$) without explicit $L_s$ modulation.

---

## 2. Reconstructed Calibration Pipeline & Computational Graph

```
[ Authentic In-Situ MEDA Archives ]
               |
               v
  ( PlanetaryArchiveIngestor )  --> ( 4,573 Normalized Observations )
               |
               v
 ( EnvironmentCollocationEngine ) --> ( Collocated Pairs with ATLAS_13L_BASELINE )
               |
               +-----------------------------------+
               |                                   |
               v                                   v
   [ Benchmark Slice N=300 ]           [ Full Mission Archive N=4,573 ]
               |                                   |
   Modulo-10 Train (Sols % 10 < 6)      Modulo-10 Train / Chrono Split
               |                                   |
   L-BFGS-B Parameter Fitting          L-BFGS-B Parameter Fitting
   (tm=218.0, ta=38.0, ps=0.0)         (Requires Seasonal Ls Terms)
               |                                   |
               v                                   v
   Held-Out RMSE: 50.64 -> 24.26 K     Held-Out RMSE: 31.45 -> 30.12 K
   (REDUCTION: 52.10% [PASSED])        (REDUCTION: 4.23% [DEGRADED])
```

---

## 3. Quantitative Reproduction Ledger

| Evaluation Scope | Sample Size ($N$) | Split Methodology | Baseline Holdout RMSE | Calibrated Holdout RMSE | Relative RMSE Reduction | Generalization Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **13M Reported Claim** | "Archive" | "Chronological" | 50.64 K | 24.26 K | **52.1%** | Reported as "PASSED_NO_OVERFITTING" |
| **Tribunal Audit 1 (Exact)**| $N=300$ | Modulo-10 (`sol % 10 < 6`) | 50.64 K | 24.26 K | **52.10%** | **CONFIRMED REPRODUCIBLE** |
| **Tribunal Audit 2 (Chrono)**| $N=300$ | Chrono (`sol <= 180`) | 48.90 K | 26.15 K | **46.52%** | **REPRODUCIBLE (Modest drop)** |
| **Tribunal Audit 3 (Full)** | $N=4,573$ | Modulo-10 (`sol % 10 < 6`) | 31.45 K | 30.12 K | **4.23%** | **DOWNGRADED (Seasonal drift)** |
| **Tribunal Audit 4 (Full Chrono)**| $N=4,573$| Chrono (`sol <= 916`) | 30.61 K | 30.61 K | **0.00%** | **FAILED (Static model cannot fit)** |

---

## 4. Challenge to "Zero Overfitting"

The Tribunal explicitly revokes the phrase *"Zero Overfitting"* from Project Atlas release materials:
1. Within the narrow $N=300$ slice (Northern Spring), the model generalizes across interleaved days because atmospheric turbidity and solar declination remain relatively stable.
2. Across the full 1,527-sol mission, a non-seasonal model suffers distribution shift.
3. **Approved Terminology:** *"Statistically significant error reduction (52.1%) demonstrated within Northern Spring/Summer regimes; multi-year orbital generalization requires spatiotemporal Ls coupling."*
