# Mars Climate Data Assimilation & Validation Lab: Bounded Least-Squares Calibration Study
**Milestone:** 13M — Mars Climate Data Assimilation & Validation Lab  
**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** November 2026  
**Status:** RELEASE QUALIFIED  

---

## 1. Mathematical Calibration Formulation

Global climate model reanalyses cannot be deployed for micro-traverse rover operations without calibration against local terrain and regolith properties. Milestone 13M implements a physically bounded least-squares optimization engine in `environment_model_calibration.py`.

### 1.1 Objective Loss Function
For training sample observations $O_i$ and parameterized model outputs $M_i(\mathbf{\theta})$:
$$\mathcal{L}(\mathbf{\theta}) = \frac{1}{N_\text{train}} \sum_{i \in \text{Train}} w_i \left( M_i(\mathbf{\theta}) - O_i \right)^2 + \lambda \sum_{j} \left( \frac{\theta_j - \theta_{0,j}}{\sigma_{\theta,j}} \right)^2$$
where $\mathbf{\theta}$ is the vector of physical parameters, $w_i = 1/\sigma_{\text{sensor}, i}^2$ represents inverse measurement variance, and the regularization term penalizes unphysical drift away from baseline nominal values $\mathbf{\theta}_0$.

### 1.2 Physically Bounded Parameter Space
Optimization is performed using the Limited-memory BFGS with Bounds (L-BFGS-B) algorithm, strictly constraining parameter drift within planetary physics boundaries:

| Parameter Symbol | Physical Meaning | Baseline $\theta_0$ | Lower Bound $\theta_\text{min}$ | Upper Bound $\theta_\text{max}$ | Calibrated Value $\theta^*$ | Physical Interpretation |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **$k_\text{TI}$** | Thermal Inertia Multiplier | 1.00 | 0.50 | 2.50 | **1.42** | Crater floor regolith holds more heat than regional GCM average |
| **$\Delta \alpha$** | Surface Albedo Adjustment | 0.00 | -0.08 | +0.08 | **-0.035** | Jezero basaltic floor has lower albedo (darker) than dusty surroundings |
| **$k_\tau$** | Dust Opacity Multiplier | 1.00 | 0.50 | 3.00 | **1.18** | Local convective boundary layer lofts localized dust |
| **$k_H$** | Scale Height Multiplier | 1.00 | 0.80 | 1.20 | **0.96** | Slightly colder lower column compresses effective scale height |
| **$a_1$** | Diurnal Diurnal Harmonic (Cos) | 0.00 | -15.0 K | +15.0 K | **-8.42 K** | Dampens unmodeled nocturnal thermal overprediction |
| **$b_1$** | Diurnal Harmonic (Sin) | 0.00 | -15.0 K | +15.0 K | **+3.15 K** | Shifts diurnal thermal peak by +35 min toward afternoon |
| **$a_2, b_2$** | Semi-diurnal Harmonic Terms | 0.00 | -5.0 K | +5.0 K | **-1.20, +0.85 K** | Captures morning thermal wake transition |

---

## 2. Experimental Optimization Protocol

To strictly guard against overfitting:
1. **Training Partition (60%):** Sols 0 to 916 ($N=600$ Sol-10 high-resolution time steps). Parameter optimization is performed solely on this partition.
2. **Held-Out Validation Partition (40%):** Sols 917 to 1527 ($N=400$ samples). Completely isolated from the optimizer; evaluated only after convergence.

```
       [ Baseline Model ]
                |
                v
    [ 60% Training Partition ] ----> ( L-BFGS-B Optimizer ) ----> [ Calibrated Parameters ]
                                                                             |
    [ 40% Held-Out Test Set ] -----------------------------------------------+
                |                                                            |
                v                                                            v
    Baseline Holdout RMSE: 15.08 K                             Calibrated Holdout RMSE: 7.22 K
                                                               (52.1% Error Reduction!)
```

---

## 3. Quantitative Calibration Performance Results

| Evaluation Metric | Baseline Model (Training) | Calibrated Model (Training) | Baseline Model (Held-Out Test) | Calibrated Model (Held-Out Test) |
| :--- | :---: | :---: | :---: | :---: |
| **Mean Bias** | +8.95 K | **+0.12 K** | +8.40 K | **+0.85 K** |
| **MAE** | 12.45 K | **5.10 K** | 11.80 K | **5.65 K** |
| **RMSE** | 15.65 K | **6.38 K** | 15.08 K | **7.22 K** |
| **Pearson $r$** | 0.565 | **0.912** | 0.582 | **0.887** |
| **$R^2$ Variance Explained** | 0.319 | **0.832** | 0.339 | **0.787** |
| **Percent Error Reduction** | — | **-59.2%** | — | **-52.1%** |

### 3.1 Overfitting Audit & Qualification Gate
- **Training Error Reduction:** 59.2%
- **Held-Out Test Error Reduction:** 52.1%
- **Generalization Gap ($\Delta \text{RMSE}$):** $7.22\text{ K} - 6.38\text{ K} = 0.84\text{ K}$ (Well below the $2.5\text{ K}$ tolerance)
- **Overfitting Qualification Decision:** `PASSED_NO_OVERFITTING`
- **Model Qualification Level:** `CALIBRATED_WITH_HOLDOUT_VALIDATION`
