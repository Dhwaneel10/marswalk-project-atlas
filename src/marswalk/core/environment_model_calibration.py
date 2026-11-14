"""
MarsWalk 2.0 / Project Atlas - Environment Model Calibration Engine
Performs bounded least-squares optimization to calibrate physical parameters
(diurnal thermal amplitude, mean temperature, lapse rates, scale height, pressure datum)
on an isolated training split and validates on a held-out test split to strictly detect and prevent overfitting.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from scipy.optimize import minimize

from marswalk.core.mars_environment_collocation import CollocatedObservationModelPair, EnvironmentCollocationEngine
from marswalk.core.environment_model_validation import compute_residual_statistics, ResidualStatistics


@dataclass
class CalibratedParameterSet:
    parameter_category: str
    baseline_values: Dict[str, float]
    calibrated_values: Dict[str, float]
    parameter_bounds: Dict[str, Tuple[float, float]]
    physical_units: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_category": self.parameter_category,
            "baseline_values": self.baseline_values,
            "calibrated_values": self.calibrated_values,
            "parameter_bounds": {k: list(v) for k, v in self.parameter_bounds.items()},
            "physical_units": self.physical_units
        }


@dataclass
class CalibrationResult:
    calibration_id: str
    target_parameter: str
    calibration_method: str
    parameters: CalibratedParameterSet
    train_sample_count: int
    held_out_sample_count: int
    train_before: ResidualStatistics
    train_after: ResidualStatistics
    held_out_before: ResidualStatistics
    held_out_after: ResidualStatistics
    train_rmse_reduction_pct: float
    held_out_rmse_reduction_pct: float
    overfitting_status: str  # "PASSED_NO_OVERFITTING" or "FLAGGED_OVERFIT"
    qualification_verdict: str  # "EMPIRICALLY_CALIBRATED_WITH_HOLDOUT" or "REJECTED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "calibration_id": self.calibration_id,
            "target_parameter": self.target_parameter,
            "calibration_method": self.calibration_method,
            "parameters": self.parameters.to_dict(),
            "train_sample_count": self.train_sample_count,
            "held_out_sample_count": self.held_out_sample_count,
            "train_before": self.train_before.to_dict(),
            "train_after": self.train_after.to_dict(),
            "held_out_before": self.held_out_before.to_dict(),
            "held_out_after": self.held_out_after.to_dict(),
            "train_rmse_reduction_pct": self.train_rmse_reduction_pct,
            "held_out_rmse_reduction_pct": self.held_out_rmse_reduction_pct,
            "overfitting_status": self.overfitting_status,
            "qualification_verdict": self.qualification_verdict
        }


class EnvironmentModelCalibrator:
    """Bounded empirical parameter calibrator with held-out validation."""

    def __init__(self, train_ratio: float = 0.60):
        self.train_ratio = train_ratio

    def _split_train_test(
        self,
        pairs: List[CollocatedObservationModelPair]
    ) -> Tuple[List[CollocatedObservationModelPair], List[CollocatedObservationModelPair]]:
        """Split collocated pairs deterministically by sol number."""
        train = [p for p in pairs if (p.sol % 10) < int(self.train_ratio * 10)]
        held_out = [p for p in pairs if (p.sol % 10) >= int(self.train_ratio * 10)]
        return train, held_out

    def calibrate_thermal_diurnal_model(
        self,
        collocated_pairs: List[CollocatedObservationModelPair],
        target_param: str = "ground_temperature"
    ) -> CalibrationResult:
        """
        Calibrate 13L diurnal thermal model parameters:
        x = [t_mean, t_amp, phase_shift]
        Bounds:
          t_mean in [200.0, 235.0] K
          t_amp in [20.0, 45.0] K
          phase_shift in [-1.5, 1.5] hours
        """
        valid_pairs = [p for p in collocated_pairs if p.parameter_name == target_param and p.gate_status == "COLLOCATION_QUALIFIED"]
        if len(valid_pairs) < 20:
            raise ValueError(f"Insufficient observation pairs ({len(valid_pairs)}) for calibration")

        train_pairs, held_out_pairs = self._split_train_test(valid_pairs)

        train_before = compute_residual_statistics(train_pairs, target_param, "K", "ATLAS_13L_BASELINE")
        held_out_before = compute_residual_statistics(held_out_pairs, target_param, "K", "ATLAS_13L_BASELINE")

        # Baseline values
        baseline_t_mean = 218.0
        baseline_t_amp = 38.0
        baseline_phase = 0.0

        def predict_temp(hr: float, t_mean: float, t_amp: float, phase_shift: float) -> float:
            shifted_hr = (hr - phase_shift) % 24.0
            if shifted_hr < 5.5:
                phase = (shifted_hr + 10.5) / 16.0
                swing = -t_amp + 8.0 * math.cos(math.pi * phase)
            elif shifted_hr <= 13.0:
                phase = (shifted_hr - 5.5) / 7.5
                swing = -t_amp + (2.0 * t_amp) * math.sin(math.pi * phase * 0.5)
            else:
                phase = (shifted_hr - 13.0) / 16.5
                swing = t_amp * math.cos(math.pi * phase * 0.7)
            return t_mean + swing

        # Loss function on training split: Mean Squared Error
        train_obs = np.array([p.observed_value for p in train_pairs])
        train_hrs = np.array([p.delta_ltst_hours for p in train_pairs])

        def loss(x: np.ndarray) -> float:
            tm, ta, ps = x
            preds = np.array([predict_temp(h, tm, ta, ps) for h in train_hrs])
            return float(np.mean((preds - train_obs)**2))

        init_x = [baseline_t_mean, baseline_t_amp, baseline_phase]
        bounds = [(200.0, 235.0), (20.0, 45.0), (-1.5, 1.5)]

        res = minimize(loss, init_x, method="L-BFGS-B", bounds=bounds)
        opt_tm, opt_ta, opt_ps = res.x

        # Create calibrated copies of pairs for evaluation
        calib_train_pairs = []
        for p in train_pairs:
            new_val = predict_temp(p.delta_ltst_hours, opt_tm, opt_ta, opt_ps)
            cp = CollocatedObservationModelPair(
                pair_id=f"CALIB_{p.pair_id}",
                parameter_name=p.parameter_name,
                unit=p.unit,
                sol=p.sol,
                observation_id=p.observation_id,
                observed_value=p.observed_value,
                observed_uncertainty_1sigma=p.observed_uncertainty_1sigma,
                model_name="ATLAS_13M_CALIBRATED",
                model_value=round(new_val, 2),
                residual=round(new_val - p.observed_value, 3),
                relative_error_pct=round(abs(new_val - p.observed_value)/p.observed_value * 100.0, 2) if p.observed_value != 0 else None,
                spatial_separation_km=p.spatial_separation_km,
                delta_ltst_hours=p.delta_ltst_hours,
                delta_ls_deg=p.delta_ls_deg,
                gate_status=p.gate_status,
                rejection_reason=None,
                representativeness_class="DIRECT_LOCAL_MATCH"
            )
            calib_train_pairs.append(cp)

        calib_held_out_pairs = []
        for p in held_out_pairs:
            new_val = predict_temp(p.delta_ltst_hours, opt_tm, opt_ta, opt_ps)
            cp = CollocatedObservationModelPair(
                pair_id=f"CALIB_{p.pair_id}",
                parameter_name=p.parameter_name,
                unit=p.unit,
                sol=p.sol,
                observation_id=p.observation_id,
                observed_value=p.observed_value,
                observed_uncertainty_1sigma=p.observed_uncertainty_1sigma,
                model_name="ATLAS_13M_CALIBRATED",
                model_value=round(new_val, 2),
                residual=round(new_val - p.observed_value, 3),
                relative_error_pct=round(abs(new_val - p.observed_value)/p.observed_value * 100.0, 2) if p.observed_value != 0 else None,
                spatial_separation_km=p.spatial_separation_km,
                delta_ltst_hours=p.delta_ltst_hours,
                delta_ls_deg=p.delta_ls_deg,
                gate_status=p.gate_status,
                rejection_reason=None,
                representativeness_class="DIRECT_LOCAL_MATCH"
            )
            calib_held_out_pairs.append(cp)

        train_after = compute_residual_statistics(calib_train_pairs, target_param, "K", "ATLAS_13M_CALIBRATED")
        held_out_after = compute_residual_statistics(calib_held_out_pairs, target_param, "K", "ATLAS_13M_CALIBRATED")

        # Reduction calculations
        train_rmse_red = ((train_before.rmse - train_after.rmse) / train_before.rmse) * 100.0 if train_before.rmse > 0 else 0.0
        held_out_rmse_red = ((held_out_before.rmse - held_out_after.rmse) / held_out_before.rmse) * 100.0 if held_out_before.rmse > 0 else 0.0

        is_overfit = held_out_after.rmse > held_out_before.rmse
        overfit_status = "FLAGGED_OVERFIT" if is_overfit else "PASSED_NO_OVERFITTING"
        verdict = "EMPIRICALLY_CALIBRATED_WITH_HOLDOUT" if not is_overfit and held_out_rmse_red > 0 else "REJECTED_OVERFIT_OR_NO_IMPROVEMENT"

        param_set = CalibratedParameterSet(
            parameter_category="DIURNAL_THERMAL_SPLINE",
            baseline_values={"t_mean": baseline_t_mean, "t_amp": baseline_t_amp, "phase_shift": baseline_phase},
            calibrated_values={"t_mean": round(float(opt_tm), 2), "t_amp": round(float(opt_ta), 2), "phase_shift": round(float(opt_ps), 2)},
            parameter_bounds={"t_mean": (200.0, 235.0), "t_amp": (20.0, 45.0), "phase_shift": (-1.5, 1.5)},
            physical_units={"t_mean": "K", "t_amp": "K", "phase_shift": "hours"}
        )

        return CalibrationResult(
            calibration_id=f"CALIB_THERMAL_{target_param.upper()}",
            target_parameter=target_param,
            calibration_method="L-BFGS-B Bounded Least-Squares on Training Split",
            parameters=param_set,
            train_sample_count=len(train_pairs),
            held_out_sample_count=len(held_out_pairs),
            train_before=train_before,
            train_after=train_after,
            held_out_before=held_out_before,
            held_out_after=held_out_after,
            train_rmse_reduction_pct=round(train_rmse_red, 2),
            held_out_rmse_reduction_pct=round(held_out_rmse_red, 2),
            overfitting_status=overfit_status,
            qualification_verdict=verdict
        )

    def calibrate_pressure_barometric_model(
        self,
        collocated_pairs: List[CollocatedObservationModelPair]
    ) -> CalibrationResult:
        """
        Calibrate 13L barometric model parameters against real MEDA PS observations:
        x = [p0_datum, scale_height]
        Bounds:
          p0_datum in [590.0, 680.0] Pa
          scale_height in [9500.0, 12500.0] m
        """
        valid_pairs = [p for p in collocated_pairs if p.parameter_name == "atmospheric_pressure" and p.gate_status == "COLLOCATION_QUALIFIED"]
        if len(valid_pairs) < 20:
            raise ValueError(f"Insufficient observation pairs ({len(valid_pairs)}) for pressure calibration")

        train_pairs, held_out_pairs = self._split_train_test(valid_pairs)

        train_before = compute_residual_statistics(train_pairs, "atmospheric_pressure", "Pa", "ATLAS_13L_BASELINE")
        held_out_before = compute_residual_statistics(held_out_pairs, "atmospheric_pressure", "Pa", "ATLAS_13L_BASELINE")

        baseline_p0 = 610.0
        baseline_hp = 11100.0

        def predict_p(elev_m: float, p0: float, hp: float) -> float:
            return p0 * math.exp(-elev_m / hp)

        train_obs = np.array([p.observed_value for p in train_pairs])
        # Elevations reconstructed from DTM pixels or rover waypoint (-2550m)
        train_elevs = np.array([-2550.0 for _ in train_pairs])

        def loss(x: np.ndarray) -> float:
            p0, hp = x
            preds = np.array([predict_p(z, p0, hp) for z in train_elevs])
            return float(np.mean((preds - train_obs)**2))

        init_x = [baseline_p0, baseline_hp]
        bounds = [(590.0, 680.0), (9500.0, 12500.0)]

        res = minimize(loss, init_x, method="L-BFGS-B", bounds=bounds)
        opt_p0, opt_hp = res.x

        calib_train_pairs = []
        for p in train_pairs:
            new_val = predict_p(-2550.0, opt_p0, opt_hp)
            calib_train_pairs.append(CollocatedObservationModelPair(
                pair_id=f"CALIB_{p.pair_id}",
                parameter_name=p.parameter_name, unit=p.unit, sol=p.sol, observation_id=p.observation_id,
                observed_value=p.observed_value, observed_uncertainty_1sigma=p.observed_uncertainty_1sigma,
                model_name="ATLAS_13M_CALIBRATED", model_value=round(new_val, 2),
                residual=round(new_val - p.observed_value, 3), relative_error_pct=round(abs(new_val - p.observed_value)/p.observed_value * 100.0, 2),
                spatial_separation_km=p.spatial_separation_km, delta_ltst_hours=p.delta_ltst_hours, delta_ls_deg=p.delta_ls_deg,
                gate_status=p.gate_status, rejection_reason=None, representativeness_class="DIRECT_LOCAL_MATCH"
            ))

        calib_held_out_pairs = []
        for p in held_out_pairs:
            new_val = predict_p(-2550.0, opt_p0, opt_hp)
            calib_held_out_pairs.append(CollocatedObservationModelPair(
                pair_id=f"CALIB_{p.pair_id}",
                parameter_name=p.parameter_name, unit=p.unit, sol=p.sol, observation_id=p.observation_id,
                observed_value=p.observed_value, observed_uncertainty_1sigma=p.observed_uncertainty_1sigma,
                model_name="ATLAS_13M_CALIBRATED", model_value=round(new_val, 2),
                residual=round(new_val - p.observed_value, 3), relative_error_pct=round(abs(new_val - p.observed_value)/p.observed_value * 100.0, 2),
                spatial_separation_km=p.spatial_separation_km, delta_ltst_hours=p.delta_ltst_hours, delta_ls_deg=p.delta_ls_deg,
                gate_status=p.gate_status, rejection_reason=None, representativeness_class="DIRECT_LOCAL_MATCH"
            ))

        train_after = compute_residual_statistics(calib_train_pairs, "atmospheric_pressure", "Pa", "ATLAS_13M_CALIBRATED")
        held_out_after = compute_residual_statistics(calib_held_out_pairs, "atmospheric_pressure", "Pa", "ATLAS_13M_CALIBRATED")

        train_rmse_red = ((train_before.rmse - train_after.rmse) / train_before.rmse) * 100.0 if train_before.rmse > 0 else 0.0
        held_out_rmse_red = ((held_out_before.rmse - held_out_after.rmse) / held_out_before.rmse) * 100.0 if held_out_before.rmse > 0 else 0.0

        is_overfit = held_out_after.rmse > held_out_before.rmse
        overfit_status = "FLAGGED_OVERFIT" if is_overfit else "PASSED_NO_OVERFITTING"
        verdict = "EMPIRICALLY_CALIBRATED_WITH_HOLDOUT" if not is_overfit and held_out_rmse_red > 0 else "REJECTED_OVERFIT_OR_NO_IMPROVEMENT"

        param_set = CalibratedParameterSet(
            parameter_category="BAROMETRIC_HYDROSTATIC_PROFILE",
            baseline_values={"p0_datum": baseline_p0, "scale_height": baseline_hp},
            calibrated_values={"p0_datum": round(float(opt_p0), 2), "scale_height": round(float(opt_hp), 2)},
            parameter_bounds={"p0_datum": (590.0, 680.0), "scale_height": (9500.0, 12500.0)},
            physical_units={"p0_datum": "Pa", "scale_height": "m"}
        )

        return CalibrationResult(
            calibration_id="CALIB_PRESSURE_BAROMETRIC",
            target_parameter="atmospheric_pressure",
            calibration_method="L-BFGS-B Bounded Least-Squares on Training Split",
            parameters=param_set,
            train_sample_count=len(train_pairs),
            held_out_sample_count=len(held_out_pairs),
            train_before=train_before,
            train_after=train_after,
            held_out_before=held_out_before,
            held_out_after=held_out_after,
            train_rmse_reduction_pct=round(train_rmse_red, 2),
            held_out_rmse_reduction_pct=round(held_out_rmse_red, 2),
            overfitting_status=overfit_status,
            qualification_verdict=verdict
        )
