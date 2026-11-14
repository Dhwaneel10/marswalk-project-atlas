"""Project Atlas / MarsWalk 2.0 — Milestone 13X
Atlas Mission Grand Prix: Rigorous Statistical Analysis & Robustness Engine.

Provides distribution-aware statistical summaries, non-parametric comparisons,
bootstrap confidence intervals, Conditional Value at Risk (CVaR), and paired
difference testing across competing planetary mission strategies.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from marswalk.core.atlas_grand_prix_metrics import ScenarioEvaluationResult


class GrandPrixStatistics:
    """Statistical evaluation suite for planetary mission strategy benchmarks."""

    @staticmethod
    def compute_distribution_metrics(values: List[float]) -> Dict[str, float]:
        """Compute complete distributional profile: mean, median, IQR, quantiles, and worst-case."""
        if not values:
            return {
                "count": 0,
                "mean": 0.0,
                "std": 0.0,
                "median": 0.0,
                "iqr": 0.0,
                "p05": 0.0,
                "p25": 0.0,
                "p75": 0.0,
                "p95": 0.0,
                "worst_case": 0.0,
                "cvar_05": 0.0,
                "cvar_10": 0.0,
            }

        arr = np.array(values, dtype=np.float64)
        n = len(arr)
        mean_val = float(np.mean(arr))
        std_val = float(np.std(arr, ddof=1)) if n > 1 else 0.0
        median_val = float(np.median(arr))

        p05 = float(np.percentile(arr, 5))
        p10 = float(np.percentile(arr, 10))
        p25 = float(np.percentile(arr, 25))
        p75 = float(np.percentile(arr, 75))
        p95 = float(np.percentile(arr, 95))
        iqr_val = p75 - p25
        worst_case = float(np.min(arr))

        # CVaR (Conditional Value at Risk, lower tail expected shortfall)
        lower_05 = arr[arr <= p05]
        cvar_05 = float(np.mean(lower_05)) if len(lower_05) > 0 else worst_case

        lower_10 = arr[arr <= p10]
        cvar_10 = float(np.mean(lower_10)) if len(lower_10) > 0 else worst_case

        return {
            "count": n,
            "mean": round(mean_val, 3),
            "std": round(std_val, 3),
            "median": round(median_val, 3),
            "iqr": round(iqr_val, 3),
            "p05": round(p05, 3),
            "p25": round(p25, 3),
            "p75": round(p75, 3),
            "p95": round(p95, 3),
            "worst_case": round(worst_case, 3),
            "cvar_05": round(cvar_05, 3),
            "cvar_10": round(cvar_10, 3),
        }

    @staticmethod
    def compute_bootstrap_ci(
        values: List[float],
        num_resamples: int = 1000,
        ci_level: float = 0.95,
        seed: int = 42,
    ) -> Tuple[float, float]:
        """Compute empirical percentile bootstrap confidence interval for the mean."""
        if not values or len(values) < 2:
            val = values[0] if values else 0.0
            return (val, val)

        arr = np.array(values, dtype=np.float64)
        n = len(arr)
        rng = np.random.RandomState(seed)

        boot_means = np.empty(num_resamples, dtype=np.float64)
        for i in range(num_resamples):
            sample = rng.choice(arr, size=n, replace=True)
            boot_means[i] = np.mean(sample)

        lower_pct = ((1.0 - ci_level) / 2.0) * 100.0
        upper_pct = (ci_level + (1.0 - ci_level) / 2.0) * 100.0
        ci_low = float(np.percentile(boot_means, lower_pct))
        ci_high = float(np.percentile(boot_means, upper_pct))
        return (round(ci_low, 3), round(ci_high, 3))

    @staticmethod
    def compare_paired_strategies(
        results_a: List[ScenarioEvaluationResult],
        results_b: List[ScenarioEvaluationResult],
        metric_name: str = "science_score",
    ) -> Dict[str, Any]:
        """Paired-seed difference analysis between two competing strategies."""
        # Align by identical scenario seed
        dict_a = {r.seed: r for r in results_a}
        dict_b = {r.seed: r for r in results_b}
        common_seeds = sorted(set(dict_a.keys()).intersection(set(dict_b.keys())))

        if not common_seeds:
            return {"error": "No common scenario seeds between strategies"}

        paired_diffs = []
        wins_a = 0
        wins_b = 0
        ties = 0

        for s in common_seeds:
            val_a = getattr(dict_a[s], metric_name)
            val_b = getattr(dict_b[s], metric_name)
            diff = val_a - val_b
            paired_diffs.append(diff)
            if diff > 1e-5:
                wins_a += 1
            elif diff < -1e-5:
                wins_b += 1
            else:
                ties += 1

        arr_diffs = np.array(paired_diffs, dtype=np.float64)
        mean_diff = float(np.mean(arr_diffs))
        std_diff = float(np.std(arr_diffs, ddof=1)) if len(arr_diffs) > 1 else 0.0

        # Cohen's d paired effect size: mean_diff / std_diff
        cohens_d = (mean_diff / std_diff) if std_diff > 1e-9 else 0.0

        # Cliff's delta non-parametric effect size
        n_pairs = len(paired_diffs)
        cliffs_delta = (wins_a - wins_b) / n_pairs if n_pairs > 0 else 0.0

        ci_low, ci_high = GrandPrixStatistics.compute_bootstrap_ci(paired_diffs)

        return {
            "metric_evaluated": metric_name,
            "paired_sample_size": n_pairs,
            "wins_strategy_a": wins_a,
            "wins_strategy_b": wins_b,
            "ties": ties,
            "mean_paired_difference": round(mean_diff, 3),
            "std_paired_difference": round(std_diff, 3),
            "ci_95_paired_diff": [ci_low, ci_high],
            "cohens_d": round(cohens_d, 3),
            "cliffs_delta": round(cliffs_delta, 3),
            "effect_interpretation": "Substantial" if abs(cliffs_delta) > 0.47 else ("Moderate" if abs(cliffs_delta) > 0.33 else ("Small" if abs(cliffs_delta) > 0.147 else "Negligible")),
        }

    @staticmethod
    def aggregate_strategy_benchmark(
        results: List[ScenarioEvaluationResult],
    ) -> Dict[str, Any]:
        """Compute multi-dimensional statistical profile for a single strategy across a test suite."""
        if not results:
            return {}

        strategy_id = results[0].strategy_id
        n = len(results)
        feasible_runs = [r for r in results if r.is_feasible]
        infeasible_runs = [r for r in results if not r.is_feasible]
        feasibility_rate = len(feasible_runs) / n

        science_scores = [r.science_score for r in results]
        energy_consumptions = [r.energy_consumed_kwh for r in results]
        distances = [r.traverse_distance_km for r in results]
        durations = [r.total_duration_sols for r in results]
        latencies = [r.planning_latency_ms for r in results]
        composite_scores = [r.balanced_composite_score for r in results]
        containments = [r.containment_success_rate for r in results]

        sci_dist = GrandPrixStatistics.compute_distribution_metrics(science_scores)
        sci_ci = GrandPrixStatistics.compute_bootstrap_ci(science_scores)

        energy_dist = GrandPrixStatistics.compute_distribution_metrics(energy_consumptions)
        dist_dist = GrandPrixStatistics.compute_distribution_metrics(distances)
        lat_dist = GrandPrixStatistics.compute_distribution_metrics(latencies)
        comp_dist = GrandPrixStatistics.compute_distribution_metrics(composite_scores)

        return {
            "strategy_id": strategy_id,
            "total_runs": n,
            "feasible_runs_count": len(feasible_runs),
            "infeasible_runs_count": len(infeasible_runs),
            "feasibility_rate_pct": round(feasibility_rate * 100.0, 1),
            "science": {
                "mean": sci_dist["mean"],
                "median": sci_dist["median"],
                "ci_95": list(sci_ci),
                "iqr": sci_dist["iqr"],
                "worst_case": sci_dist["worst_case"],
                "cvar_05": sci_dist["cvar_05"],
            },
            "energy_kwh": {
                "mean": energy_dist["mean"],
                "median": energy_dist["median"],
                "p95": energy_dist["p95"],
            },
            "distance_km": {
                "mean": dist_dist["mean"],
                "median": dist_dist["median"],
            },
            "containment_rate_mean": round(float(np.mean(containments)), 3),
            "planning_latency_ms": {
                "mean": lat_dist["mean"],
                "median": lat_dist["median"],
                "p95": lat_dist["p95"],
            },
            "composite_score": {
                "mean": comp_dist["mean"],
                "median": comp_dist["median"],
                "cvar_05": comp_dist["cvar_05"],
            },
        }
