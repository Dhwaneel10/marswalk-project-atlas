import json
import math
import os
import sys
import numpy as np

REPO_ROOT = os.path.abspath(r"E:\Python\NASA-Spaceapps\Marswalk")
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from marswalk.core.planetary_archive_ingestion import PlanetaryArchiveIngestor
from marswalk.core.mars_environment_collocation import EnvironmentCollocationEngine

ingestor = PlanetaryArchiveIngestor()
norm_obs = ingestor.ingest_meda_daily_series()
ingestor.ingest_mcd_netcdf()

engine = EnvironmentCollocationEngine()
pairs = engine.collocate_dataset(norm_obs[:300], ingestor, model_target="ATLAS_13L_BASELINE")
valid_pairs = [p for p in pairs if p.parameter_name == "ground_temperature" and p.gate_status == "COLLOCATION_QUALIFIED"]

# Evaluated split (modulo-10)
train_pairs = [p for p in valid_pairs if (p.sol % 10) < 6]
test_pairs = [p for p in valid_pairs if (p.sol % 10) >= 6]

train_obs = np.array([p.observed_value for p in train_pairs])
train_hrs = np.array([p.delta_ltst_hours for p in train_pairs])
test_obs = np.array([p.observed_value for p in test_pairs])
test_hrs = np.array([p.delta_ltst_hours for p in test_pairs])

def predict_temp(hr, tm, ta, ps):
    shifted_hr = (hr - ps) % 24.0
    if shifted_hr < 5.5:
        phase = (shifted_hr + 10.5) / 16.0
        swing = -ta + 8.0 * math.cos(math.pi * phase)
    elif shifted_hr <= 13.0:
        phase = (shifted_hr - 5.5) / 7.5
        swing = -ta + (2.0 * ta) * math.sin(math.pi * phase * 0.5)
    else:
        phase = (shifted_hr - 13.0) / 16.5
        swing = ta * math.cos(math.pi * phase * 0.7)
    return tm + swing

# 1. BASELINE COMPARISONS
# A. Uncalibrated 13L baseline
base_test_preds = np.array([predict_temp(h, 218.0, 38.0, 0.0) for h in test_hrs])
base_test_rmse = float(np.sqrt(np.mean((base_test_preds - test_obs)**2)))
base_test_mae = float(np.mean(np.abs(base_test_preds - test_obs)))

# B. Calibrated model (from N=300 optimal: tm=218.0, ta=38.0, ps=0.0 on delta_ltst=0)
# But let's check with real observation LTST
obs_train_ltst = np.array([p.sol % 24 for p in train_pairs])  # proxy hour
# C. Climatological Mean Baseline: constant mean of training observations
clim_mean = float(np.mean(train_obs))
clim_test_preds = np.full_like(test_obs, clim_mean)
clim_test_rmse = float(np.sqrt(np.mean((clim_test_preds - test_obs)**2)))
clim_test_mae = float(np.mean(np.abs(clim_test_preds - test_obs)))

# D. Persistence Baseline: predict previous sol's observation
obs_by_sol = {p.sol: p.observed_value for p in valid_pairs}
persist_preds = []
persist_actuals = []
for p in test_pairs:
    prev_val = obs_by_sol.get(p.sol - 1)
    if prev_val is not None:
        persist_preds.append(prev_val)
        persist_actuals.append(p.observed_value)

persist_test_rmse = float(np.sqrt(np.mean((np.array(persist_preds) - np.array(persist_actuals))**2))) if persist_preds else 0.0
persist_test_mae = float(np.mean(np.abs(np.array(persist_preds) - np.array(persist_actuals)))) if persist_preds else 0.0

print("=== BASELINE COMPARISONS (Held-Out Test Set) ===")
print(f"1. Uncalibrated 13L Baseline:       RMSE = {base_test_rmse:.2f} K, MAE = {base_test_mae:.2f} K")
print(f"2. Climatological Mean Baseline:    RMSE = {clim_test_rmse:.2f} K, MAE = {clim_test_mae:.2f} K")
print(f"3. Persistence Baseline (Sol-1):    RMSE = {persist_test_rmse:.2f} K, MAE = {persist_test_mae:.2f} K (N={len(persist_preds)})")

# 2. ABLATION STUDY
# Full Calibrated: tm=222.0, ta=35.0, ps=-0.2
full_test_preds = np.array([predict_temp(h, 222.0, 35.0, -0.2) for h in test_hrs])
full_rmse = float(np.sqrt(np.mean((full_test_preds - test_obs)**2)))

# Ablation 1: No phase shift (ps=0.0)
abl1_preds = np.array([predict_temp(h, 222.0, 35.0, 0.0) for h in test_hrs])
abl1_rmse = float(np.sqrt(np.mean((abl1_preds - test_obs)**2)))

# Ablation 2: No amplitude calibration (ta=38.0)
abl2_preds = np.array([predict_temp(h, 222.0, 38.0, -0.2) for h in test_hrs])
abl2_rmse = float(np.sqrt(np.mean((abl2_preds - test_obs)**2)))

# Ablation 3: No mean adjustment (tm=218.0)
abl3_preds = np.array([predict_temp(h, 218.0, 35.0, -0.2) for h in test_hrs])
abl3_rmse = float(np.sqrt(np.mean((abl3_preds - test_obs)**2)))

print("\n=== ABLATION STUDY (Held-Out Test Set) ===")
print(f"Full Model (tm=222, ta=35, ps=-0.2):  RMSE = {full_rmse:.2f} K")
print(f"Ablation 1 (No Phase Shift, ps=0):     RMSE = {abl1_rmse:.2f} K (Delta: {abl1_rmse - full_rmse:+.2f} K)")
print(f"Ablation 2 (No Amp Calib, ta=38):      RMSE = {abl2_rmse:.2f} K (Delta: {abl2_rmse - full_rmse:+.2f} K)")
print(f"Ablation 3 (No Mean Adj, tm=218):      RMSE = {abl3_rmse:.2f} K (Delta: {abl3_rmse - full_rmse:+.2f} K)")

# 3. COUNTEREXAMPLE HUNTING (Where calibration degrades performance)
counterexamples = []
for p in test_pairs:
    base_pred = predict_temp(p.delta_ltst_hours, 218.0, 38.0, 0.0)
    calib_pred = predict_temp(p.delta_ltst_hours, 222.0, 35.0, -0.2)
    err_base = abs(base_pred - p.observed_value)
    err_calib = abs(calib_pred - p.observed_value)
    
    # If calibration made error worse by > 3 K
    if err_calib > err_base + 3.0:
        counterexamples.append({
            "sol": p.sol,
            "observation_id": p.observation_id,
            "observed_k": p.observed_value,
            "baseline_pred_k": round(base_pred, 2),
            "calibrated_pred_k": round(calib_pred, 2),
            "baseline_error_k": round(err_base, 2),
            "calibrated_error_k": round(err_calib, 2),
            "degradation_k": round(err_calib - err_base, 2)
        })

print(f"\n=== COUNTEREXAMPLES FOUND: {len(counterexamples)} ===")
for ce in counterexamples[:5]:
    print(f"  Sol {ce['sol']} ({ce['observation_id']}): Observed={ce['observed_k']} K | BaseErr={ce['baseline_error_k']} K -> CalibErr={ce['calibrated_error_k']} K (Worse by +{ce['degradation_k']} K)")

output_data = {
    "baseline_comparisons": {
        "uncalibrated_baseline_rmse": base_test_rmse,
        "climatological_mean_rmse": clim_test_rmse,
        "persistence_rmse": persist_test_rmse
    },
    "ablations": {
        "full_calibrated_rmse": full_rmse,
        "no_phase_shift_rmse": abl1_rmse,
        "no_amplitude_calib_rmse": abl2_rmse,
        "no_mean_adjustment_rmse": abl3_rmse
    },
    "counterexamples_count": len(counterexamples),
    "counterexamples": counterexamples
}

with open(os.path.join(REPO_ROOT, "data", "environment", "validation", "ablations_and_counterexamples.json"), "w", encoding="utf-8") as f:
    json.dump(output_data, f, indent=2)
print("\nSaved ablations and counterexamples to data/environment/validation/ablations_and_counterexamples.json")
