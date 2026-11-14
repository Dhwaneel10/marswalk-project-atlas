"""
MarsWalk 2.0 / Project Atlas - Milestone 13M Test Suite
Verifies:
- Ingestion of authentic NASA PDS MEDA, MCD 6.2 NetCDF, and MRO MCS archives
- Mars calendar, time (UTC/Sol/LMST/LTST/Ls), and spatial coordinate normalization
- Sensor quality screening and strict null preservation for degraded sensors
- Spatial and temporal collocation gating and rejection codes
- Model evaluation lab (empirical residuals, Bias, MAE, RMSE, Pearson r, quantiles)
- Bounded parameter calibration on training split and held-out validation (no overfitting)
- Operational risk assessment and calibrated confidence envelopes
- Multi-dimensional representativeness scoring (Composite Representativeness Index)
- Non-destructive layered field fusion (Level A, B, C)
- 6 standard planetary validation experiments (A through F)
- Mission constraint engine environmental qualification gate
- Draft 2020-12 JSON Schema contracts and live REST API endpoints
"""

import math
import os
import urllib.request
import json
import pytest
import numpy as np

from marswalk.core.mars_observation_normalizer import (
    parse_sol_lmst, parse_sol_ltst, format_sol_ltst,
    utc_to_sol_and_ls, equation_of_time_hours, lmst_to_ltst, ltst_to_lmst,
    planetocentric_to_planetographic_lat, planetographic_to_planetocentric_lat,
    coordinates_to_jezero_dtm_pixel, jezero_dtm_pixel_to_coordinates,
    get_perseverance_traverse_position
)
from marswalk.core.planetary_data_quality import (
    QualityStatus, SENSOR_UNCERTAINTY_REGISTRY,
    filter_tirs_measurement, filter_ats_measurement, filter_ps_measurement, filter_wind_measurement
)
from marswalk.core.planetary_archive_ingestion import PlanetaryArchiveIngestor, NormalizedObservationRecord
from marswalk.core.mars_environment_collocation import EnvironmentCollocationEngine, CollocationGateStatus
from marswalk.core.environment_model_validation import ModelEvaluationLab, compute_residual_statistics
from marswalk.core.environment_model_calibration import EnvironmentModelCalibrator
from marswalk.core.environment_model_uncertainty import EnvironmentModelUncertaintyEngine
from marswalk.core.environmental_representativeness import PlanetaryRepresentativenessEngine, RepresentativenessClass
from marswalk.core.environment_field_update import EnvironmentFieldFusionEngine
from marswalk.core.environment_science_experiment import EnvironmentScienceExperimentRunner
from marswalk.core.mission_constraint_engine import MissionConstraintEngine, MissionIntent
from marswalk.core.mission_goal_compiler import MissionTaskGraph, MissionTaskNode, MissionTaskType
from marswalk.api.contracts import validate_contract


@pytest.fixture
def ingestor():
    return PlanetaryArchiveIngestor()


@pytest.fixture
def collocation_engine():
    return EnvironmentCollocationEngine()


# --- TEST 1: Ingestion Manifest Verification ---
def test_source_acquisition_manifest(ingestor):
    res = ingestor.load_and_verify_manifest()
    assert res["all_verified"] is True
    assert res["total_products"] >= 8
    for p in res["results"]:
        assert p["status"] == "VERIFIED_MATCH"
        assert len(p["sha256"]) == 64


# --- TEST 2: Mars Calendar & Time Normalization ---
def test_mars_time_normalization():
    sol, dh = parse_sol_lmst("00010M14:31:53.805")
    assert sol == 10
    assert 14.53 < dh < 14.54

    sol_t, dh_t = parse_sol_ltst("0010 13:57:24")
    assert sol_t == 10
    assert 13.95 < dh_t < 13.96

    formatted = format_sol_ltst(10, 13.956667)
    assert formatted == "0010 13:57:24"

    # Equation of time swings up to ~50 minutes
    eot_p = equation_of_time_hours(251.0)
    eot_a = equation_of_time_hours(71.0)
    assert abs(eot_p) < 1.0
    assert abs(eot_a) < 1.0

    # Round trip LMST <-> LTST
    ltst_val = lmst_to_ltst(12.0, 45.0)
    lmst_val = ltst_to_lmst(ltst_val, 45.0)
    assert abs(lmst_val - 12.0) < 1e-4


# --- TEST 3: Coordinate Normalization & Traverse Position ---
def test_spatial_coordinate_normalization():
    # Planetocentric <-> Planetographic
    lat_cen = 18.4447
    lat_graph = planetocentric_to_planetographic_lat(lat_cen)
    assert lat_graph > lat_cen  # flattening increases graphic latitude in northern hemisphere
    lat_cen_back = planetographic_to_planetocentric_lat(lat_graph)
    assert abs(lat_cen_back - lat_cen) < 1e-6

    # Jezero DTM projection
    r, c, xm, ym = coordinates_to_jezero_dtm_pixel(18.4447, 77.4508)
    assert r == 125
    assert c == 125
    assert abs(xm) < 1.0
    assert abs(ym) < 1.0

    # Traverse waypoint interpolation
    pos_0 = get_perseverance_traverse_position(0)
    assert "Octavia" in pos_0["waypoint_name"]
    pos_200 = get_perseverance_traverse_position(200)
    assert "Three Forks" in pos_200["waypoint_name"] or "Seitah" in pos_200["waypoint_name"]
    assert pos_200["elev_m"] < -2500.0


# --- TEST 4: Sensor Quality Screening & Null Preservation ---
def test_planetary_sensor_quality_screening():
    # TIRS screening: nominal
    q_nom = filter_tirs_measurement(upward_lw_flux=280.0, upward_lw_uncertainty=2.0)
    assert q_nom["status"] == QualityStatus.NOMINAL.value
    assert 250.0 < q_nom["ground_temp_k"] < 280.0

    # TIRS screening: shadow obstruction
    q_shad = filter_tirs_measurement(upward_lw_flux=280.0, upward_lw_uncertainty=2.0, ground_not_in_shadow=0)
    assert q_shad["status"] == QualityStatus.REJECTED_SHADOW.value

    # ATS screening: median across 5 sensors
    q_ats = filter_ats_measurement([239.0, 240.0, 241.0, 239.5, 240.5])
    assert q_ats["status"] == QualityStatus.NOMINAL.value
    assert q_ats["air_temp_k"] == 240.0

    # Wind sensor: strict null preservation for degraded sensor
    q_wind = filter_wind_measurement(wind_speed_m_s=None, wind_dir_deg=None, sensor_flag="OFFLINE_SALTATION_DAMAGE")
    assert q_wind["status"] == QualityStatus.NULL_PRESERVED.value
    assert q_wind["wind_speed_m_s"] is None
    assert "scientific integrity rule" in q_wind["rejection_reason"]


# --- TEST 5: MCD 6.2 NetCDF Climatology ---
def test_mcd_netcdf_ingestion(ingestor):
    mcd = ingestor.ingest_mcd_netcdf()
    assert "ls" in mcd["dimensions"]
    assert "sol_time" in mcd["dimensions"]
    assert len(mcd["altitude_grid_km"]) == 11
    assert mcd["tsurf_mean_k"] > 200.0

    # Query prediction
    pred = ingestor.get_mcd_model_prediction(ls_deg=45.0, ltst_hours=13.5)
    assert pred["ground_temp_k"] > pred["air_temp_k"]  # daytime solar heating
    assert 600.0 < pred["pressure_pa"] < 900.0


# --- TEST 6: MRO MCS Profile Ingestion ---
def test_mcs_profile_ingestion(ingestor):
    profiles = ingestor.ingest_mcs_profiles()
    assert len(profiles) >= 8
    p0 = profiles[0]
    assert p0["instrument"] == "MRO Mars Climate Sounder (MCS)"
    assert len(p0["vertical_levels"]) >= 10
    top = p0["vertical_levels"][-1]
    bot = p0["vertical_levels"][0]
    assert bot["pressure_pa"] > top["pressure_pa"]
    assert bot["temperature_k"] > top["temperature_k"]


# --- TEST 7: Collocation Engine & Physical Gating ---
def test_collocation_engine(ingestor, collocation_engine):
    meda_records = ingestor.ingest_meda_daily_series()
    pairs = collocation_engine.collocate_dataset(meda_records[:50], ingestor, model_target="MCD_6_2_GCM")
    assert len(pairs) == 50
    qualified = [p for p in pairs if p.gate_status == CollocationGateStatus.QUALIFIED.value]
    assert len(qualified) > 0
    p0 = qualified[0]
    assert p0.spatial_separation_km <= collocation_engine.max_spatial_separation_km
    assert p0.residual == pytest.approx(p0.model_value - p0.observed_value, rel=1e-3)


# --- TEST 8: Model Evaluation Lab ---
def test_model_evaluation_lab(ingestor, collocation_engine):
    meda_records = ingestor.ingest_meda_daily_series()
    pairs = collocation_engine.collocate_dataset(meda_records[:150], ingestor, model_target="MCD_6_2_GCM")
    lab = ModelEvaluationLab()
    report = lab.evaluate_model(pairs, model_name="MCD_6_2_GCM")

    assert "atmospheric_pressure" in report.overall_metrics
    stats = report.overall_metrics["atmospheric_pressure"]
    assert stats.sample_count > 0
    assert stats.rmse > 0.0
    assert stats.mae > 0.0
    assert -1.0 <= stats.pearson_r <= 1.0

    # Train vs Held-Out validation split
    assert report.train_metrics is not None
    assert report.held_out_metrics is not None
    assert "atmospheric_pressure" in report.train_metrics
    assert "atmospheric_pressure" in report.held_out_metrics


# --- TEST 9: Bounded Calibration & Overfitting Prevention ---
def test_model_calibration_held_out(ingestor, collocation_engine):
    meda_records = ingestor.ingest_meda_daily_series()
    pairs = collocation_engine.collocate_dataset(meda_records[:200], ingestor, model_target="ATLAS_13L_BASELINE")

    calibrator = EnvironmentModelCalibrator(train_ratio=0.60)
    res = calibrator.calibrate_thermal_diurnal_model(pairs, target_param="ground_temperature")

    assert res.train_rmse_reduction_pct > 0.0
    assert res.held_out_rmse_reduction_pct > 0.0
    assert res.overfitting_status == "PASSED_NO_OVERFITTING"
    assert res.qualification_verdict == "EMPIRICALLY_CALIBRATED_WITH_HOLDOUT"


# --- TEST 10: Operational Uncertainty & Hardware Risk ---
def test_operational_uncertainty():
    unc_engine = EnvironmentModelUncertaintyEngine()
    stats = compute_residual_statistics([], "ground_temperature", "K", "TEST")
    # Mock residual stats with sigma = 6.0 K and bias = 0.0
    from marswalk.core.environment_model_validation import ResidualStatistics
    mock_stats = ResidualStatistics(
        parameter_name="ground_temperature", unit="K", model_name="TEST", sample_count=100,
        mean_bias=0.0, mae=5.0, rmse=6.0, residual_std=6.0, pearson_r=0.8, r_squared=0.64,
        median_abs_error=4.5, min_residual=-15.0, max_residual=15.0, p05_residual=-12.0,
        p25_residual=-4.0, p50_median_residual=0.0, p75_residual=4.0, p95_residual=12.0
    )

    # Test SHERLOC hardware risk at predicted -45 C (limit is -35 C)
    risk = unc_engine.evaluate_instrument_thermal_risk("SHERLOC", -45.0, mock_stats)
    assert risk.risk_level == "CRITICAL_VIOLATION"
    assert risk.violation_probability_pct > 50.0

    # Test confidence bands
    bands = unc_engine.generate_diurnal_confidence_bands([-20.0, -10.0, 0.0], mock_stats)
    assert len(bands.predicted_mean) == 3
    assert bands.lower_1sigma[0] < bands.predicted_mean[0] < bands.upper_1sigma[0]


# --- TEST 11: Environmental Representativeness Engine ---
def test_environmental_representativeness():
    rep_engine = PlanetaryRepresentativenessEngine()
    # Close in-situ
    eval_close = rep_engine.evaluate_representativeness(
        obs_id="OBS_1", obs_lat=18.4447, obs_lon=77.4508, obs_elev_m=-2574.0, obs_ltst_h=13.5, obs_ls_deg=10.0,
        target_id="TGT_1", target_lat=18.4450, target_lon=77.4510, target_elev_m=-2570.0, target_ltst_h=13.6, target_ls_deg=10.1
    )
    assert eval_close.classification == RepresentativenessClass.DIRECT_LOCAL_MATCH.value
    assert eval_close.composite_index > 0.80

    # Remote scarp out-of-season
    eval_far = rep_engine.evaluate_representativeness(
        obs_id="OBS_1", obs_lat=18.4447, obs_lon=77.4508, obs_elev_m=-2574.0, obs_ltst_h=13.5, obs_ls_deg=10.0,
        target_id="TGT_FAR", target_lat=18.6000, target_lon=77.2000, target_elev_m=-1800.0, target_ltst_h=04.0, target_ls_deg=180.0
    )
    assert eval_far.classification in [RepresentativenessClass.SEASONAL_CLIMATOLOGY_CONTEXT.value, RepresentativenessClass.NON_COMPARABLE.value]
    assert eval_far.composite_index < 0.10


# --- TEST 12: Layered Non-Destructive Field Fusion ---
def test_field_fusion_layering():
    fusion_engine = EnvironmentFieldFusionEngine(influence_radius_pixels=15.0)
    bg = np.full((30, 30), 220.0, dtype=np.float32)

    product = fusion_engine.generate_assimilated_field(
        parameter_name="ground_temperature", unit="K", sol=10, ltst_hours=13.5, ls_deg=10.5,
        background_grid=bg, collocated_pairs=[]
    )
    assert product.background_mean == 220.0
    assert product.assimilated_mean == 220.0
    assert product.provenance_classification == "DERIVED_DATA_ASSIMILATION_PRODUCT"
    # Background must remain identical
    assert np.allclose(product.background_grid, bg)


# --- TEST 13: Standard Scientific Validation Experiments ---
def test_scientific_experiments_suite(ingestor):
    runner = EnvironmentScienceExperimentRunner(ingestor=ingestor)
    exp_a = runner.run_experiment_a_diurnal_temperature()
    assert exp_a.experiment_id == "EXP_A_DIURNAL_TEMP"
    assert "mean_bias_k" in exp_a.quantitative_findings

    exp_e = runner.run_experiment_e_compiler_sensitivity()
    assert exp_e.experiment_id == "EXP_E_COMPILER_SENSITIVITY"
    assert exp_e.quantitative_findings["false_positive_violation_caught"] is True


# --- TEST 14: Mission Constraint Engine Qualification Gate ---
def test_mission_compiler_qualification_gate():
    engine = MissionConstraintEngine()
    tg = MissionTaskGraph(graph_id="tg_qual", intent_id="intent_qual")
    tg.add_task(MissionTaskNode(
        task_id="OBS_01", name="OBS_01", parent_goal_id="g1",
        task_type=MissionTaskType.OBSERVE.value
    ))

    # Test with calibrated model
    intent_calib = MissionIntent(intent_id="intent_c", name="Calib Test", description="Test", environmental_qualification_level="CALIBRATED_WITH_HOLDOUT_VALIDATION")
    report_calib = engine.evaluate_task_graph_constraints(intent_calib, tg)
    qual_c = next((c for c in report_calib.constraints if c.constraint_id == "SOFT_ENVIRONMENTAL_MODEL_QUALIFICATION"), None)
    assert qual_c is not None
    assert qual_c.is_satisfied is True

    # Test with unvalidated model
    intent_unval = MissionIntent(intent_id="intent_u", name="Unval Test", description="Test", environmental_qualification_level="UNVALIDATED")
    report_unval = engine.evaluate_task_graph_constraints(intent_unval, tg)
    qual_u = next((c for c in report_unval.constraints if c.constraint_id == "SOFT_ENVIRONMENTAL_MODEL_QUALIFICATION"), None)
    assert qual_u is not None
    assert qual_u.is_satisfied is False
    assert "Widen instrument operating margins" in qual_u.diagnostic_message


# --- TEST 15: Draft 2020-12 JSON Schema Validation ---
def test_draft_2020_12_schema_contracts(ingestor, collocation_engine):
    # Manifest contract
    manifest = ingestor.load_and_verify_manifest()
    with open(ingestor.manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    validate_contract(manifest_data, "environmental-ingestion-manifest")

    # Collocation contract
    meda_records = ingestor.ingest_meda_daily_series()
    pairs = collocation_engine.collocate_dataset(meda_records[:10], ingestor, model_target="MCD_6_2_GCM")
    colloc_payload = {
        "total_pairs": len(pairs),
        "qualified_pairs": sum(1 for p in pairs if p.gate_status == "COLLOCATION_QUALIFIED"),
        "model_target": "MCD_6_2_GCM",
        "pairs": [p.to_dict() for p in pairs]
    }
    validate_contract(colloc_payload, "environmental-collocation")

    # Evaluation contract
    lab = ModelEvaluationLab()
    report = lab.evaluate_model(pairs, model_name="MCD_6_2_GCM")
    validate_contract(report.to_dict(), "environmental-model-evaluation")

    # Experiment contract
    runner = EnvironmentScienceExperimentRunner(ingestor=ingestor)
    exp = runner.run_experiment_c_mcs_vertical_lapse_rate()
    validate_contract(exp.to_dict(), "environmental-experiment")


# --- TEST 16: Live REST API Endpoints Integration ---
def test_live_rest_api_endpoints():
    base = "http://127.0.0.1:3000"

    # GET catalog
    with urllib.request.urlopen(f"{base}/api/environment-validation/catalog", timeout=10) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "products" in data
        assert data["total_products"] >= 8

    # GET collocate
    with urllib.request.urlopen(f"{base}/api/environment-validation/collocate?limit=15", timeout=10) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["total_pairs"] == 15

    # GET evaluate
    with urllib.request.urlopen(f"{base}/api/environment-validation/evaluate?limit=50", timeout=10) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "overall_metrics" in data

    # GET experiment
    with urllib.request.urlopen(f"{base}/api/environment-validation/experiments?experiment_id=EXP_D_DUST_SEASONALITY", timeout=10) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["experiment_id"] == "EXP_D_DUST_SEASONALITY"
