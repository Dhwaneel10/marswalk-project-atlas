"""
MarsWalk 2.0 / Project Atlas - Model Evaluation Lab
Computes rigorous empirical residual statistics, Pearson correlation, R^2,
quantile residual distributions, and stratified multi-dimensional breakdowns
(by parameter, season Ls, diurnal LTST, and mission Sol phase).
"""

from __future__ import annotations
import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from marswalk.core.mars_environment_collocation import CollocatedObservationModelPair


@dataclass
class ResidualStatistics:
    parameter_name: str
    unit: str
    model_name: str
    sample_count: int
    mean_bias: float
    mae: float
    rmse: float
    residual_std: float
    pearson_r: float
    r_squared: float
    median_abs_error: float
    min_residual: float
    max_residual: float
    p05_residual: float
    p25_residual: float
    p50_median_residual: float
    p75_residual: float
    p95_residual: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StratifiedEvaluationReport:
    model_name: str
    dataset_name: str
    evaluation_timestamp: str
    overall_metrics: Dict[str, ResidualStatistics]
    by_parameter: Dict[str, ResidualStatistics]
    by_season_ls: Dict[str, Dict[str, ResidualStatistics]]
    by_diurnal_phase: Dict[str, Dict[str, ResidualStatistics]]
    train_metrics: Optional[Dict[str, ResidualStatistics]] = None
    held_out_metrics: Optional[Dict[str, ResidualStatistics]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "dataset_name": self.dataset_name,
            "evaluation_timestamp": self.evaluation_timestamp,
            "overall_metrics": {k: v.to_dict() for k, v in self.overall_metrics.items()},
            "by_parameter": {k: v.to_dict() for k, v in self.by_parameter.items()},
            "by_season_ls": {s: {p: m.to_dict() for p, m in pm.items()} for s, pm in self.by_season_ls.items()},
            "by_diurnal_phase": {d: {p: m.to_dict() for p, m in pm.items()} for d, pm in self.by_diurnal_phase.items()},
            "train_metrics": {k: v.to_dict() for k, v in self.train_metrics.items()} if self.train_metrics else None,
            "held_out_metrics": {k: v.to_dict() for k, v in self.held_out_metrics.items()} if self.held_out_metrics else None
        }


def compute_residual_statistics(
    pairs: List[CollocatedObservationModelPair],
    parameter_name: str,
    unit: str,
    model_name: str
) -> Optional[ResidualStatistics]:
    """Compute empirical residual metrics for a given subset of collocated pairs."""
    # Filter qualified pairs for the parameter
    valid = [p for p in pairs if p.parameter_name == parameter_name and p.gate_status == "COLLOCATION_QUALIFIED"]
    if not valid:
        return None

    obs_vals = np.array([p.observed_value for p in valid], dtype=np.float64)
    mod_vals = np.array([p.model_value for p in valid], dtype=np.float64)
    residuals = mod_vals - obs_vals  # Model - Observed

    n = len(valid)
    mean_bias = float(np.mean(residuals))
    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(residuals**2)))
    res_std = float(np.std(residuals))

    # Pearson r
    obs_std = np.std(obs_vals)
    mod_std = np.std(mod_vals)
    if obs_std > 1e-6 and mod_std > 1e-6:
        r = float(np.corrcoef(obs_vals, mod_vals)[0, 1])
    else:
        r = 0.0

    # R^2
    ss_tot = np.sum((obs_vals - np.mean(obs_vals))**2)
    ss_res = np.sum(residuals**2)
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 1e-6 else 0.0

    # Quantiles
    p05, p25, p50, p75, p95 = np.percentile(residuals, [5, 25, 50, 75, 95])

    return ResidualStatistics(
        parameter_name=parameter_name,
        unit=unit,
        model_name=model_name,
        sample_count=n,
        mean_bias=round(mean_bias, 3),
        mae=round(mae, 3),
        rmse=round(rmse, 3),
        residual_std=round(res_std, 3),
        pearson_r=round(r, 4),
        r_squared=round(r2, 4),
        median_abs_error=round(float(np.median(np.abs(residuals))), 3),
        min_residual=round(float(np.min(residuals)), 3),
        max_residual=round(float(np.max(residuals)), 3),
        p05_residual=round(float(p05), 3),
        p25_residual=round(float(p25), 3),
        p50_median_residual=round(float(p50), 3),
        p75_residual=round(float(p75), 3),
        p95_residual=round(float(p95), 3)
    )


class ModelEvaluationLab:
    """Evaluates collocated model-observation sets with stratified breakdowns and held-out validation."""

    def __init__(self):
        pass

    def evaluate_model(
        self,
        collocated_pairs: List[CollocatedObservationModelPair],
        model_name: str,
        dataset_name: str = "PERSEVERANCE_MEDA_PDS4",
        train_test_split_ratio: float = 0.60
    ) -> StratifiedEvaluationReport:
        from datetime import datetime, timezone

        qualified = [p for p in collocated_pairs if p.gate_status == "COLLOCATION_QUALIFIED"]
        parameters = sorted(list(set(p.parameter_name for p in qualified)))

        # 1. Overall by parameter
        by_parameter: Dict[str, ResidualStatistics] = {}
        for param in parameters:
            unit = next((p.unit for p in qualified if p.parameter_name == param), "")
            stat = compute_residual_statistics(qualified, param, unit, model_name)
            if stat:
                by_parameter[param] = stat

        # 2. Stratified by season (Ls quadrants)
        season_bins = {
            "Spring_Ls0_90": lambda p: 0.0 <= p.delta_ls_deg % 360.0 < 90.0,
            "Summer_Ls90_180": lambda p: 90.0 <= p.delta_ls_deg % 360.0 < 180.0,
            "Autumn_Ls180_270": lambda p: 180.0 <= p.delta_ls_deg % 360.0 < 270.0,
            "Winter_Ls270_360": lambda p: 270.0 <= p.delta_ls_deg % 360.0 < 360.0
        }
        by_season: Dict[str, Dict[str, ResidualStatistics]] = {}
        for sname, sfilter in season_bins.items():
            spairs = [p for p in qualified if sfilter(p)]
            if spairs:
                by_season[sname] = {}
                for param in parameters:
                    unit = next((p.unit for p in spairs if p.parameter_name == param), "")
                    st = compute_residual_statistics(spairs, param, unit, model_name)
                    if st:
                        by_season[sname][param] = st

        # 3. Stratified by diurnal phase
        diurnal_bins = {
            "Dawn_04_08h": lambda p: 4.0 <= (p.delta_ltst_hours % 24.0) < 8.0,
            "Midday_11_15h": lambda p: 11.0 <= (p.delta_ltst_hours % 24.0) < 15.0,
            "Evening_17_21h": lambda p: 17.0 <= (p.delta_ltst_hours % 24.0) < 21.0,
            "Night_21_04h": lambda p: (p.delta_ltst_hours % 24.0) >= 21.0 or (p.delta_ltst_hours % 24.0) < 4.0
        }
        by_diurnal: Dict[str, Dict[str, ResidualStatistics]] = {}
        for dname, dfilter in diurnal_bins.items():
            dpairs = [p for p in qualified if dfilter(p)]
            if dpairs:
                by_diurnal[dname] = {}
                for param in parameters:
                    unit = next((p.unit for p in dpairs if p.parameter_name == param), "")
                    st = compute_residual_statistics(dpairs, param, unit, model_name)
                    if st:
                        by_diurnal[dname][param] = st

        # 4. Train vs Held-Out Validation Split (e.g. 60% / 40% split by Sol number)
        # Sols are split deterministically: sol % 10 < 6 is training, sol % 10 >= 6 is held-out
        train_pairs = [p for p in qualified if (p.sol % 10) < int(train_test_split_ratio * 10)]
        held_out_pairs = [p for p in qualified if (p.sol % 10) >= int(train_test_split_ratio * 10)]

        train_metrics: Dict[str, ResidualStatistics] = {}
        held_out_metrics: Dict[str, ResidualStatistics] = {}

        for param in parameters:
            unit = next((p.unit for p in qualified if p.parameter_name == param), "")
            st_tr = compute_residual_statistics(train_pairs, param, unit, model_name)
            if st_tr:
                train_metrics[param] = st_tr
            st_ho = compute_residual_statistics(held_out_pairs, param, unit, model_name)
            if st_ho:
                held_out_metrics[param] = st_ho

        return StratifiedEvaluationReport(
            model_name=model_name,
            dataset_name=dataset_name,
            evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
            overall_metrics=by_parameter,
            by_parameter=by_parameter,
            by_season_ls=by_season,
            by_diurnal_phase=by_diurnal,
            train_metrics=train_metrics,
            held_out_metrics=held_out_metrics
        )
