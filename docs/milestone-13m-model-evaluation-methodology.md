# Mars Climate Data Assimilation & Validation Lab: Model Evaluation Methodology
**Milestone:** 13M — Mars Climate Data Assimilation & Validation Lab  
**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** November 2026  
**Status:** RELEASE QUALIFIED  

---

## 1. Statistical Metric Foundations

Model evaluation within Milestone 13M applies rigorous empirical residuals between collocated observation pairs $(O_i, M_i)$ where $R_i = M_i - O_i$:

### 1.1 First- and Second-Order Residual Metrics
- **Mean Error (Bias):**
  $$\text{Bias} = \frac{1}{N} \sum_{i=1}^N (M_i - O_i)$$
- **Mean Absolute Error (MAE):**
  $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N |M_i - O_i|$$
- **Root Mean Square Error (RMSE):**
  $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (M_i - O_i)^2}$$

### 1.2 Correlation and Variance Explained
- **Pearson Product-Moment Correlation ($r$):**
  $$r = \frac{\sum (M_i - \bar{M})(O_i - \bar{O})}{\sqrt{\sum (M_i - \bar{M})^2 \sum (O_i - \bar{O})^2}}$$
- **Coefficient of Determination ($R^2$):**
  $$R^2 = 1 - \frac{\sum_{i=1}^N (O_i - M_i)^2}{\sum_{i=1}^N (O_i - \bar{O})^2}$$

### 1.3 Robust & Non-Parametric Quantile Metrics
Martian environmental data frequently exhibit non-Gaussian tails (e.g. abrupt dust devil pressure drops or sudden thermal inversions). Project Atlas computes:
- **Median Absolute Deviation (MAD):**
  $$\text{MAD} = \text{median}\left(|R_i - \text{median}(R)|\right)$$
- **Percentile Quantiles:** $p_{05}, p_{25}, p_{50}\text{ (Median Bias)}, p_{75}, p_{95}$
- **Interquartile Range (IQR):** $\text{IQR} = p_{75} - p_{25}$

---

## 2. Multi-Dimensional Stratified Evaluation

Global bulk metrics often obscure critical operational regimes (e.g. an acceptable mean daily temperature bias may hide a lethal $-25\text{ K}$ nocturnal cold bias). Atlas stratifies residuals into operational bins:

### 2.1 Diurnal Bins (Local True Solar Time)
1. **Dawn (04:00–07:00 LTST):** Maximum diurnal thermal inversion; minimum surface temperatures; extreme critical hardware risks (SHERLOC spectrometer heating).
2. **Midday (11:00–14:00 LTST):** Peak solar irradiance; maximum convective boundary layer growth; dust devil activity; maximum rover drive energy.
3. **Dusk (17:00–20:00 LTST):** Rapid thermal collapse; solar array shutdown; rover transition to night sleep mode.
4. **Night (22:00–03:00 LTST):** Stable nocturnal boundary layer; barometric thermal tide minimum.

### 2.2 Seasonal Bins (Areocentric Solar Longitude)
1. **Aphelion Cold/Clear Season ($L_s \in [60^\circ, 120^\circ]$):** Mars farthest from the Sun; low atmospheric dust opacity ($\tau < 0.3$); high nocturnal thermal radiative loss.
2. **Perihelion Dust Season ($L_s \in [240^\circ, 300^\circ]$):** Mars closest to the Sun; maximum solar insolation; global dust storm development; elevated nocturnal warming from dust thermal blanketing.

---

## 3. Train / Test Held-Out Split Methodology

To prevent overfitting during model parameter calibration, Atlas strictly enforces a **chronological split**:
- **Training Partition (60%):** Sols 0 to 916 ($N=600$ Sol-10 high-frequency samples, 915 daily indices).
- **Held-Out Test Partition (40%):** Sols 917 to 1527 ($N=400$ Sol-10 samples, 611 daily indices).

```
[ Sols 0 -------------------------- Sol 916 ] [ Sol 917 -------------------- Sol 1527 ]
<---------- Training Split (60%) -----------> <-------- Held-Out Test Split (40%) ------->
Used for L-BFGS-B Parameter Fitting           NEVER SEEN DURING CALIBRATION
                                              Used for Model Generalization Validation
```

### 3.1 Overfitting Detection Criteria
A calibration is declared invalid if:
$$\text{RMSE}_\text{holdout} > 1.15 \times \text{RMSE}_\text{baseline, holdout}$$
or if the training RMSE improves by $> 30\%$ while the holdout RMSE degrades or improves by $< 5\%$.
