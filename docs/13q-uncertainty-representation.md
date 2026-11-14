# PROJECT ATLAS — MILESTONE 13Q
# SCIENTIFIC UNCERTAINTY REPRESENTATION & SPATIAL FIELDS
## Eight-Dimensional Uncertainty Decomposition & Continuous Planetary Spatial Modeling

**Milestone:** 13Q — Atlas Autonomous Science Discovery Engine  
**Module:** `src/marswalk/core/science_uncertainty_field.py`  
**Status:** `QUALIFIED`

---

## 1. Architectural Philosophy: The Unknown is Not Empty

In robotic path planning, unobserved regions are often treated either as uniform free space or as arbitrary obstacles. In planetary science, **the unknown is not empty, safe, or scientifically uninteresting**. Unsurveyed regions possess high epistemic uncertainty and therefore offer high potential scientific information gain.

Milestone 13Q decomposes uncertainty into eight orthogonal dimensions rather than collapsing complex physics into a single scalar confidence score.

---

## 2. The Eight Uncertainty Dimensions

1. **Measurement Uncertainty:** High-frequency Gaussian or Poisson sensor noise ($\sigma_{\text{meas}}$).
2. **Calibration Uncertainty:** Systematic zero-point drift, dark current variation, or flat-fielding error ($\delta_{\text{cal}}$).
3. **Spatial Interpolation Uncertainty:** Kriging / variogram estimation variance increasing exponentially with Euclidean distance from prior observation coordinates:
   $$\sigma_{\text{spatial}}(d) = 1.0 - \exp\left(-\frac{d}{L_{\text{corr}}}\right)$$
   where $L_{\text{corr}} = 75.0\text{ m}$ is the spatial correlation length.
4. **Temporal Interpolation Uncertainty:** Uncertainty due to environmental diurnal or seasonal changes since the last observation sol.
5. **Model Parameter Uncertainty:** Variance in assumed physical constants (e.g., thermal inertia, grain density, dielectric constant).
6. **Model Structural Uncertainty:** Physics omissions in forward models (e.g., neglecting aerosol scattering in optical radiative transfer).
7. **Classification Entropy:** Shannon entropy across discrete candidate mineral or lithological categories.
8. **Scientific Interpretation Ambiguity:** Margin of likelihood separation between the top competing geological hypotheses.

---

## 3. Continuous 2D Spatial Raster Representation

The uncertainty field maintains a 2D spatial grid over Jezero Crater ($1,000\text{ m} \times 1,000\text{ m}$ at $25.0\text{ m}$ native resolution):
- Data Coverage Layer ($0.0 \le C \le 1.0$)
- Spatial Uncertainty Layer ($0.0 \le U_{\text{spatial}} \le 1.0$)
- Observation Density Map (accumulated in-situ and aerial contact footprints)
- Synthetic Ground Truth Targets (preserved for held-out algorithmic benchmarking)
