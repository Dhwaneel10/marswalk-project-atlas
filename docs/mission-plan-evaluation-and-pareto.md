# MarsWalk 2.0 / Project Atlas — Plan Quality Evaluation & Pareto Analysis

## 1. Six Normalized Physical Performance Dimensions

Each candidate mission plan $\mathbf{x}$ is evaluated across six normalized dimensions:

| Dimension | Metric | Normalization Formula |
| :--- | :--- | :--- |
| **Science Utility** | Total returned science utility points | $S_{\text{sci}} = \frac{U(\mathbf{x})}{\max_{\mathbf{x}'} U(\mathbf{x}')}$ |
| **Mobility Efficiency** | Science utility points returned per kilometer traveled | $S_{\text{mob}} = \frac{U(\mathbf{x}) / D_{\text{km}}(\mathbf{x})}{\max_{\mathbf{x}'} (U(\mathbf{x}') / D_{\text{km}}(\mathbf{x}'))}$ |
| **Battery Reserve Margin** | Minimum rover battery state of charge across the mission | $S_{\text{batt}} = \frac{\text{SoC}_{\min}(\mathbf{x})}{100.0}$ |
| **Comms Continuity** | Geometric line-of-sight reachability to base or relay mesh | $S_{\text{comms}} = \frac{\text{Reachability}_{\%}(\mathbf{x})}{100.0}$ |
| **Storage Margin** | Headroom below flash storage utilization ceiling | $S_{\text{store}} = 1.0 - \frac{\text{Storage}_{\text{peak}}(\mathbf{x})}{100.0}$ |
| **Duration Compression** | Compression of campaign duration relative to maximum sols | $S_{\text{dur}} = 1.0 - \frac{T_{\text{hours}}(\mathbf{x})}{\max_{\mathbf{x}'} T_{\text{hours}}(\mathbf{x}') \cdot 1.2}$ |

---

## 2. Multi-Objective Weighted Composite Scoring

The final composite score $\mathcal{S}(\mathbf{x})$ is computed using designer preference weights:

$$\mathcal{S}(\mathbf{x}) = w_{\text{sci}} S_{\text{sci}} + w_{\text{mob}} S_{\text{mob}} + w_{\text{batt}} S_{\text{batt}} + w_{\text{comms}} S_{\text{comms}} + 0.05 S_{\text{store}} + w_{\text{dur}} S_{\text{dur}}$$

where $\sum w_i = 1.0$.

---

## 3. Pairwise Trade-Off Delta Scorecard

When evaluating alternative postures (e.g. Science Maximizing vs Energy Efficient), the engine computes exact physical deltas:
$$\Delta U = U(\mathbf{x}_{\text{target}}) - U(\mathbf{x}_{\text{base}})$$
$$\Delta E = E(\mathbf{x}_{\text{target}}) - E(\mathbf{x}_{\text{base}})$$
$$\Delta \text{SoC} = \text{SoC}_{\min}(\mathbf{x}_{\text{target}}) - \text{SoC}_{\min}(\mathbf{x}_{\text{base}})$$

This provides the flight director with an unvarnished, quantitative explanation of exactly what is gained and what is surrendered when selecting an aggressive vs conservative plan.
