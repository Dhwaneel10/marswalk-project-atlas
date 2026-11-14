"""
MarsWalk 2.0 / Project Atlas - Environment Model Uncertainty Engine
Quantifies empirical residual uncertainty, propagates parameter errors into operational
risk margins for rover subsystems and scientific instruments, and builds calibrated confidence bands.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from scipy import stats

from marswalk.core.environment_model_validation import ResidualStatistics


@dataclass
class OperationalRiskAssessment:
    subsystem_id: str
    target_parameter: str
    predicted_value: float
    unit: str
    operational_limit_min: float
    operational_limit_max: float
    empirical_residual_std: float
    safety_margin_to_min: float
    safety_margin_to_max: float
    violation_probability_pct: float
    risk_level: str  # "SAFE", "CAUTION", "CRITICAL_VIOLATION"
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CalibratedConfidenceBands:
    parameter_name: str
    unit: str
    time_hours: List[float]
    predicted_mean: List[float]
    lower_1sigma: List[float]
    upper_1sigma: List[float]
    lower_2sigma: List[float]
    upper_2sigma: List[float]
    empirical_p05: List[float]
    empirical_p95: List[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EnvironmentModelUncertaintyEngine:
    """Propagates empirical model residuals into operations, instrument margins, and confidence envelopes."""

    def __init__(self):
        # Instrument operational hardware temperature limits (Space Science Reviews, 2020-2021)
        self.instrument_limits: Dict[str, Tuple[float, float]] = {
            "MASTCAM_Z": (-55.0, 40.0),   # Celsius
            "SHERLOC": (-35.0, 30.0),     # Celsius
            "PIXL": (-40.0, 35.0),        # Celsius
            "SUPERCAM": (-50.0, 30.0),    # Celsius
            "MEDA_SYS": (-80.0, 45.0),    # Celsius
            "ROVER_BATTERY": (-20.0, 30.0) # Internal battery heaters keep >= -20 C
        }

    def evaluate_instrument_thermal_risk(
        self,
        subsystem_id: str,
        predicted_temp_c: float,
        residual_stats: ResidualStatistics
    ) -> OperationalRiskAssessment:
        """
        Evaluate probability that actual temperature violates instrument hardware operating limits,
        given model empirical residual distribution (mean bias and standard deviation).
        """
        limits = self.instrument_limits.get(subsystem_id, (-50.0, 35.0))
        t_min, t_max = limits

        sigma = residual_stats.residual_std if residual_stats.residual_std > 0 else 5.0
        bias = residual_stats.mean_bias

        # Expected actual temperature distribution: T_actual ~ Normal(predicted_temp - bias, sigma^2)
        expected_actual = predicted_temp_c - bias

        # Probability of falling below minimum operating temperature
        prob_under = stats.norm.cdf(t_min, loc=expected_actual, scale=sigma)
        # Probability of exceeding maximum operating temperature
        prob_over = 1.0 - stats.norm.cdf(t_max, loc=expected_actual, scale=sigma)

        total_violation_prob = float(prob_under + prob_over) * 100.0

        margin_min = float(expected_actual - t_min)
        margin_max = float(t_max - expected_actual)

        if total_violation_prob > 15.0 or margin_min < 0.0 or margin_max < 0.0:
            risk = "CRITICAL_VIOLATION"
            rec = f"Pre-heat or reschedule activity: actual temperature has {total_violation_prob:.1f}% risk of violating {subsystem_id} limits [{t_min}, {t_max}] C."
        elif total_violation_prob > 5.0 or min(margin_min, margin_max) < 5.0:
            risk = "CAUTION"
            rec = f"Narrow thermal safety margin ({min(margin_min, margin_max):.1f} C). Enable rover auxiliary warming circuits before science operation."
        else:
            risk = "SAFE"
            rec = f"Operating comfortably within qualified thermal window. Margin: +{min(margin_min, margin_max):.1f} C."

        return OperationalRiskAssessment(
            subsystem_id=subsystem_id,
            target_parameter="temperature_celsius",
            predicted_value=round(predicted_temp_c, 2),
            unit="C",
            operational_limit_min=t_min,
            operational_limit_max=t_max,
            empirical_residual_std=round(sigma, 2),
            safety_margin_to_min=round(margin_min, 2),
            safety_margin_to_max=round(margin_max, 2),
            violation_probability_pct=round(total_violation_prob, 2),
            risk_level=risk,
            recommendation=rec
        )

    def generate_diurnal_confidence_bands(
        self,
        predicted_curve_c: List[float],
        residual_stats: ResidualStatistics,
        time_steps: Optional[List[float]] = None
    ) -> CalibratedConfidenceBands:
        """
        Generate calibrated confidence bands (1-sigma, 2-sigma, p05/p95) around a diurnal curve
        using empirical residual quantiles and standard deviation.
        """
        n = len(predicted_curve_c)
        hours = time_steps if time_steps is not None else list(np.linspace(0.0, 24.0, n))

        sigma = residual_stats.residual_std if residual_stats.residual_std > 0 else 4.0
        p05_offset = residual_stats.p05_residual
        p95_offset = residual_stats.p95_residual
        bias = residual_stats.mean_bias

        means = []
        l1 = []
        u1 = []
        l2 = []
        u2 = []
        ep05 = []
        ep95 = []

        for val in predicted_curve_c:
            calib_val = val - bias
            means.append(round(calib_val, 2))
            l1.append(round(calib_val - sigma, 2))
            u1.append(round(calib_val + sigma, 2))
            l2.append(round(calib_val - 2.0 * sigma, 2))
            u2.append(round(calib_val + 2.0 * sigma, 2))
            ep05.append(round(calib_val + p05_offset, 2))
            ep95.append(round(calib_val + p95_offset, 2))

        return CalibratedConfidenceBands(
            parameter_name=residual_stats.parameter_name,
            unit=residual_stats.unit,
            time_hours=[round(h, 2) for h in hours],
            predicted_mean=means,
            lower_1sigma=l1,
            upper_1sigma=u1,
            lower_2sigma=l2,
            upper_2sigma=u2,
            empirical_p05=ep05,
            empirical_p95=ep95
        )
