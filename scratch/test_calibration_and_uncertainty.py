import sys
sys.path.insert(0, 'src')
from marswalk.core.planetary_archive_ingestion import PlanetaryArchiveIngestor
from marswalk.core.mars_environment_collocation import EnvironmentCollocationEngine
from marswalk.core.environment_model_validation import ModelEvaluationLab
from marswalk.core.environment_model_calibration import EnvironmentModelCalibrator
from marswalk.core.environment_model_uncertainty import EnvironmentModelUncertaintyEngine

ingestor = PlanetaryArchiveIngestor()
meda_records = ingestor.ingest_meda_daily_series()
engine = EnvironmentCollocationEngine()
calibrator = EnvironmentModelCalibrator(train_ratio=0.60)
unc_engine = EnvironmentModelUncertaintyEngine()

# Collocate 13L baseline pairs for calibration
pairs_13l = engine.collocate_dataset(meda_records[:300], ingestor, model_target="ATLAS_13L_BASELINE")

# 1. Calibrate ground temperature
res_thermal = calibrator.calibrate_thermal_diurnal_model(pairs_13l, target_param="ground_temperature")
print("=== THERMAL CALIBRATION RESULT ===")
print("Method:", res_thermal.calibration_method)
print("Baseline params:", res_thermal.parameters.baseline_values)
print("Calibrated params:", res_thermal.parameters.calibrated_values)
print(f"Train RMSE: {res_thermal.train_before.rmse:.2f} -> {res_thermal.train_after.rmse:.2f} ({res_thermal.train_rmse_reduction_pct:.1f}% reduction)")
print(f"Held-out RMSE: {res_thermal.held_out_before.rmse:.2f} -> {res_thermal.held_out_after.rmse:.2f} ({res_thermal.held_out_rmse_reduction_pct:.1f}% reduction)")
print("Overfitting status:", res_thermal.overfitting_status)
print("Qualification verdict:", res_thermal.qualification_verdict)

# 2. Calibrate pressure
res_pressure = calibrator.calibrate_pressure_barometric_model(pairs_13l)
print("\n=== PRESSURE CALIBRATION RESULT ===")
print("Baseline params:", res_pressure.parameters.baseline_values)
print("Calibrated params:", res_pressure.parameters.calibrated_values)
print(f"Train RMSE: {res_pressure.train_before.rmse:.2f} -> {res_pressure.train_after.rmse:.2f} ({res_pressure.train_rmse_reduction_pct:.1f}% reduction)")
print(f"Held-out RMSE: {res_pressure.held_out_before.rmse:.2f} -> {res_pressure.held_out_after.rmse:.2f} ({res_pressure.held_out_rmse_reduction_pct:.1f}% reduction)")
print("Overfitting status:", res_pressure.overfitting_status)

# 3. Test operational risk evaluation on SHERLOC (-35C limit) at dawn (-50C predicted)
risk = unc_engine.evaluate_instrument_thermal_risk("SHERLOC", predicted_temp_c=-45.0, residual_stats=res_thermal.held_out_after)
print("\n=== SHERLOC THERMAL RISK ASSESSMENT ===")
print(f"Predicted: {risk.predicted_value} C | Margin to min: {risk.safety_margin_to_min} C | Violation prob: {risk.violation_probability_pct}% | Level: {risk.risk_level}")
print("Recommendation:", risk.recommendation)
