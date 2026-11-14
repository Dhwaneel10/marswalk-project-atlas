"""
MarsWalk 2.0 / Project Atlas - Standalone Statistical Validation Engine (Milestone 13N)
Pure, independent implementation of mathematical evaluation metrics, bootstrap confidence intervals,
and robust non-parametric statistics without reliance on internal library caches.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple
import numpy as np


@dataclass
class IndependentStatisticalMetrics:
    sample_count: int
    mean_observed: float
    mean_modeled: float
    mean_bias: float
    mae: float
    rmse: float
    pearson_r: float
    r_squared: float
    median_absolute_error: float
    min_residual: float
    max_residual: float
    p05_residual: float
    p25_residual: float
    p50_median_residual: float
    p75_residual: float
    p95_residual: float
    rmse_ci_95: Tuple[float, float]
    mae_ci_95: Tuple[float, float]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["rmse_ci_95"] = list(self.rmse_ci_95)
        d["mae_ci_95"] = list(self.mae_ci_95)
        return d


def compute_independent_statistics(
    observed_values: List[float],
    modeled_values: List[float],
    n_bootstrap: int = 500,
    random_seed: int = 42
) -> IndependentStatisticalMetrics:
    """
    Independently compute evaluation metrics from raw observation and model arrays.
    Guarantees strict zero-division guards and honest negative R^2 reporting.
    """
    n = len(observed_values)
    if n == 0 or len(modeled_values) != n:
        return IndependentStatisticalMetrics(
            sample_count=0,
            mean_observed=0.0,
            mean_modeled=0.0,
            mean_bias=0.0,
            mae=0.0,
            rmse=0.0,
            pearson_r=0.0,
            r_squared=0.0,
            median_absolute_error=0.0,
            min_residual=0.0,
            max_residual=0.0,
            p05_residual=0.0,
            p25_residual=0.0,
            p50_median_residual=0.0,
            p75_residual=0.0,
            p95_residual=0.0,
            rmse_ci_95=(0.0, 0.0),
            mae_ci_95=(0.0, 0.0)
        )

    obs = np.array(observed_values, dtype=np.float64)
    mod = np.array(modeled_values, dtype=np.float64)
    residuals = mod - obs

    mean_obs = float(np.mean(obs))
    mean_mod = float(np.mean(mod))
    bias = float(np.mean(residuals))
    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(residuals**2)))

    # Pearson r
    std_obs = float(np.std(obs))
    std_mod = float(np.std(mod))
    if std_obs > 1e-9 and std_mod > 1e-9:
        cov = float(np.mean((obs - mean_obs) * (mod - mean_mod)))
        r = float(np.clip(cov / (std_obs * std_mod), -1.0, 1.0))
    else:
        r = 0.0

    # R-squared (Coefficient of Determination)
    # R^2 = 1 - SS_res / SS_tot
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((obs - mean_obs)**2))
    if ss_tot > 1e-9:
        r2 = float(1.0 - (ss_res / ss_tot))
    else:
        r2 = 0.0

    # Non-parametric quantiles
    sorted_res = np.sort(residuals)
    abs_res = np.abs(residuals)
    mad = float(np.median(abs_res))
    min_res = float(sorted_res[0])
    max_res = float(sorted_res[-1])
    p05 = float(np.percentile(sorted_res, 5))
    p25 = float(np.percentile(sorted_res, 25))
    p50 = float(np.percentile(sorted_res, 50))
    p75 = float(np.percentile(sorted_res, 75))
    p95 = float(np.percentile(sorted_res, 95))

    # Bootstrap 95% Confidence Intervals
    boot_rmse = []
    boot_mae = []
    rng = np.random.default_rng(random_seed)
    for _ in range(n_bootstrap):
        sample_indices = rng.integers(0, n, size=n)
        s_res = residuals[sample_indices]
        boot_rmse.append(float(np.sqrt(np.mean(s_res**2))))
        boot_mae.append(float(np.mean(np.abs(s_res))))

    rmse_ci = (float(np.percentile(boot_rmse, 2.5)), float(np.percentile(boot_rmse, 97.5)))
    mae_ci = (float(np.percentile(boot_mae, 2.5)), float(np.percentile(boot_mae, 97.5)))

    return IndependentStatisticalMetrics(
        sample_count=n,
        mean_observed=round(mean_obs, 3),
        mean_modeled=round(mean_mod, 3),
        mean_bias=round(bias, 3),
        mae=round(mae, 3),
        rmse=round(rmse, 3),
        pearson_r=round(r, 4),
        r_squared=round(r2, 4),
        median_absolute_error=round(mad, 3),
        min_residual=round(min_res, 3),
        max_residual=round(max_res, 3),
        p05_residual=round(p05, 3),
        p25_residual=round(p25, 3),
        p50_median_residual=round(p50, 3),
        p75_residual=round(p75, 3),
        p95_residual=round(p95, 3),
        rmse_ci_95=(round(rmse_ci[0], 3), round(rmse_ci[1], 3)),
        mae_ci_95=(round(mae_ci[0], 3), round(mae_ci[1], 3))
    )
