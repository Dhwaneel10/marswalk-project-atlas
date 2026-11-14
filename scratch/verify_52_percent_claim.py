import json
import math
import os
import sys
import numpy as np

REPO_ROOT = os.path.abspath(r"E:\Python\NASA-Spaceapps\Marswalk")
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from marswalk.core.planetary_archive_ingestion import PlanetaryArchiveIngestor
from marswalk.core.mars_environment_collocation import EnvironmentCollocationEngine
from marswalk.core.environment_model_calibration import EnvironmentModelCalibrator

ingestor = PlanetaryArchiveIngestor()
norm_obs = ingestor.ingest_meda_daily_series()
ingestor.ingest_mcd_netcdf()

engine = EnvironmentCollocationEngine()
pairs = engine.collocate_dataset(norm_obs, ingestor)

calibrator = EnvironmentModelCalibrator(train_ratio=0.60)
res_orig = calibrator.calibrate_thermal_diurnal_model(pairs, target_param="ground_temperature")

print("=== ORIGINAL 13M CALIBRATION RUN ===")
print(f"Target Parameter: {res_orig.target_parameter}")
print(f"Train Sample Count: {res_orig.train_sample_count}")
print(f"Held-Out Sample Count: {res_orig.held_out_sample_count}")
print(f"Train Before RMSE: {res_orig.train_before.rmse:.3f} K")
print(f"Train After RMSE:  {res_orig.train_after.rmse:.3f} K (Reduction: {res_orig.train_rmse_reduction_pct:.2f}%)")
print(f"Held-Out Before RMSE: {res_orig.held_out_before.rmse:.3f} K")
print(f"Held-Out After RMSE:  {res_orig.held_out_after.rmse:.3f} K (Reduction: {res_orig.held_out_rmse_reduction_pct:.2f}%)")
print(f"Overfitting Status: {res_orig.overfitting_status}")
print(f"Qualification Verdict: {res_orig.qualification_verdict}")
print(f"Calibrated Parameters: {res_orig.parameters.calibrated_values}")

# Now test Chronological split (Sols <= 916 vs Sols > 916)
valid_pairs = [p for p in pairs if p.parameter_name == "ground_temperature" and p.gate_status == "COLLOCATION_QUALIFIED"]
train_chrono = [p for p in valid_pairs if p.sol <= 916]
test_chrono = [p for p in valid_pairs if p.sol > 916]

print("\n=== CHRONOLOGICAL SPLIT TEST (Sol <= 916 vs Sol > 916) ===")
print(f"Train Chrono Count: {len(train_chrono)}, Test Chrono Count: {len(test_chrono)}")

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

from scipy.optimize import minimize

train_obs = np.array([p.observed_value for p in train_chrono])
train_hrs = np.array([p.delta_ltst_hours for p in train_chrono])
train_base_preds = np.array([predict_temp(h, 218.0, 38.0, 0.0) for h in train_hrs])
base_train_rmse = float(np.sqrt(np.mean((train_base_preds - train_obs)**2)))

def loss_chrono(x):
    tm, ta, ps = x
    preds = np.array([predict_temp(h, tm, ta, ps) for h in train_hrs])
    return float(np.mean((preds - train_obs)**2))

res_ch = minimize(loss_chrono, [218.0, 38.0, 0.0], method="L-BFGS-B", bounds=[(200.0, 235.0), (20.0, 45.0), (-1.5, 1.5)])
opt_tm_ch, opt_ta_ch, opt_ps_ch = res_ch.x

calib_train_preds = np.array([predict_temp(h, opt_tm_ch, opt_ta_ch, opt_ps_ch) for h in train_hrs])
calib_train_rmse = float(np.sqrt(np.mean((calib_train_preds - train_obs)**2)))

test_obs = np.array([p.observed_value for p in test_chrono])
test_hrs = np.array([p.delta_ltst_hours for p in test_chrono])
test_base_preds = np.array([predict_temp(h, 218.0, 38.0, 0.0) for h in test_hrs])
base_test_rmse = float(np.sqrt(np.mean((test_base_preds - test_obs)**2)))

calib_test_preds = np.array([predict_temp(h, opt_tm_ch, opt_ta_ch, opt_ps_ch) for h in test_hrs])
calib_test_rmse = float(np.sqrt(np.mean((calib_test_preds - test_obs)**2)))

train_red_ch = (base_train_rmse - calib_train_rmse) / base_train_rmse * 100.0
test_red_ch = (base_test_rmse - calib_test_rmse) / base_test_rmse * 100.0

print(f"Chrono Train Base RMSE: {base_train_rmse:.3f} K -> Calib: {calib_train_rmse:.3f} K ({train_red_ch:.2f}%)")
print(f"Chrono Test Base RMSE:  {base_test_rmse:.3f} K -> Calib: {calib_test_rmse:.3f} K ({test_red_ch:.2f}%)")
print(f"Chrono Calibrated Params: t_mean={opt_tm_ch:.2f}, t_amp={opt_ta_ch:.2f}, phase_shift={opt_ps_ch:.2f}")

# Bootstrap 95% Confidence Interval for held-out RMSE reduction on original split
held_out_pairs = [p for p in valid_pairs if (p.sol % 10) >= 6]
opt_tm, opt_ta, opt_ps = res_orig.parameters.calibrated_values["t_mean"], res_orig.parameters.calibrated_values["t_amp"], res_orig.parameters.calibrated_values["phase_shift"]

n_boot = 1000
boot_reds = []
np.random.seed(42)
for _ in range(n_boot):
    idx = np.random.choice(len(held_out_pairs), size=len(held_out_pairs), replace=True)
    sample = [held_out_pairs[i] for i in idx]
    s_obs = np.array([p.observed_value for p in sample])
    s_hrs = np.array([p.delta_ltst_hours for p in sample])
    b_preds = np.array([predict_temp(h, 218.0, 38.0, 0.0) for h in s_hrs])
    c_preds = np.array([predict_temp(h, opt_tm, opt_ta, opt_ps) for h in s_hrs])
    b_rmse = np.sqrt(np.mean((b_preds - s_obs)**2))
    c_rmse = np.sqrt(np.mean((c_preds - s_obs)**2))
    if b_rmse > 0:
        boot_reds.append((b_rmse - c_rmse) / b_rmse * 100.0)

ci_lower = np.percentile(boot_reds, 2.5)
ci_upper = np.percentile(boot_reds, 97.5)
print(f"\nBootstrap 95% CI for Held-Out RMSE Reduction: [{ci_lower:.2f}%, {ci_upper:.2f}%], Median: {np.median(boot_reds):.2f}%")
