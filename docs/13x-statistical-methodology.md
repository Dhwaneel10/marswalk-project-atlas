# Project Atlas — Milestone 13X: Statistical Methodology & Robustness Analysis

**Project:** MarsWalk 2.0 / Project Atlas  
**Milestone:** 13X — Atlas Mission Grand Prix  
**Document:** `docs/13x-statistical-methodology.md`  
**Status:** **VERIFIED & OPERATIONAL**  

---

## 1. Distribution-Aware Metrics

Averages alone can be deeply misleading in planetary mission design where lower-tail catastrophic outcomes dictate mission survival. The Grand Prix engine implements full distributional statistics:

- **Central Tendency:** Mean and Median ($\tilde{x}$).
- **Dispersion:** Standard Deviation ($\sigma$) and Interquartile Range ($IQR = Q_{75} - Q_{25}$).
- **Tail Risk Quantiles:** 5th percentile ($P_{05}$), 10th percentile ($P_{10}$), and Worst-Case ($\min x$).
- **Conditional Value at Risk ($\text{CVaR}_\alpha$):**
  $$\text{CVaR}_\alpha(X) = \mathbb{E}\left[ X \mid X \le \text{VaR}_\alpha(X) \right]$$
  Quantifies the expected performance in the worst $\alpha = 5\%$ of mission scenarios.

---

## 2. Inferential & Non-Parametric Comparisons

### 2.1 Percentile Bootstrap Confidence Intervals
Empirical bootstrap resampling ($B = 1,000$ iterations) calculates non-parametric 95% confidence intervals without assuming Gaussian normality:
$$\text{CI}_{95\%} = \left[ \hat{\theta}^*_{(2.5\%)}, \, \hat{\theta}^*_{(97.5\%)} \right]$$

### 2.2 Paired-Seed Differences & Effect Sizes
Because competing strategies are evaluated on paired seeds, direct differences $\Delta_i = X_{A, i} - X_{B, i}$ isolate algorithmic efficacy from scenario variance:
- **Cohen's $d$:**
  $$d = \frac{\bar{\Delta}}{s_\Delta}$$
- **Cliff's Delta ($\delta$):** Non-parametric dominance metric:
  $$\delta = \frac{\#(\Delta > 0) - \#(\Delta < 0)}{N}$$
  Interpreted as: Negligible ($|\delta| < 0.147$), Small ($0.147 \le |\delta| < 0.33$), Moderate ($0.33 \le |\delta| < 0.47$), and Substantial ($|\delta| \ge 0.47$).

---

## 3. Epistemic Notice on Synthetic Scenarios

> [!CAUTION]
> **Planetary Statistics Disclosure:**
> High statistical confidence on synthetic or sampled Martian scenarios indicates robustness within the benchmark configuration space. It does not constitute a real-world Mars mission flight success probability.
