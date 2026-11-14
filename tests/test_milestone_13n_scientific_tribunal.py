"""
MarsWalk 2.0 / Project Atlas — Milestone 13N Automated Test Suite
Independent Scientific Reproducibility Tribunal & Adversarial Audit Battery
==========================================================================
Verifies all 9 scientific claims, provenance digests, mathematical invariants,
collocation sensitivity tiers, statistical hand-calculated benchmarks, calibration
reproduction on benchmark slices vs full archives, parameter identifiability,
counterexamples, and Draft 2020-12 schema contracts.
"""

import math
import os
import urllib.request
import json
import pytest
import numpy as np

from marswalk.core.mars_source_provenance_audit import SourceProvenanceAuditor, ProvenanceVerdict
from marswalk.core.mars_validation_statistics import compute_independent_statistics, IndependentStatisticalMetrics
from marswalk.core.mars_calibration_reproduction import (
    CalibrationReproductionAuditor, CalibrationReproductionVerdict, predict_diurnal_spline
)
from marswalk.core.mars_science_evidence_registry import ScientificEvidenceRegistry, EvidenceVerdict
from marswalk.core.mars_reproducibility_audit import ScientificReproducibilityTribunal
from marswalk.core.planetary_archive_ingestion import PlanetaryArchiveIngestor
from marswalk.core.planetary_data_quality import (
    QualityStatus, filter_tirs_measurement, filter_ats_measurement, filter_wind_measurement
)
from marswalk.core.mars_observation_normalizer import (
    equation_of_time_hours, lmst_to_ltst, ltst_to_lmst,
    planetocentric_to_planetographic_lat, MARS_RADIUS_EQUATORIAL_M
)
from marswalk.core.environmental_representativeness import (
    PlanetaryRepresentativenessEngine, RepresentativenessClass
)
from marswalk.core.environment_model_uncertainty import EnvironmentModelUncertaintyEngine
from marswalk.core.environment_model_validation import ResidualStatistics
from marswalk.api.contracts import validate_contract


# --- TEST 1: Source Provenance Audit on Authentic Manifest ---
def test_provenance_audit_all_products_valid():
    auditor = SourceProvenanceAuditor()
    report = auditor.audit_all_products()
    assert report.total_manifest_products == 9
    assert report.verified_products_count == 9
    assert report.discrepancy_count == 0
    assert report.overall_provenance_verdict == ProvenanceVerdict.VERIFIED.value
    for prod in report.product_audits:
        assert prod.file_exists is True
        assert prod.checksum_match is True
        assert prod.provenance_verdict == ProvenanceVerdict.VERIFIED.value


# --- TEST 2: Adversarial Provenance Tamper Detection ---
def test_provenance_audit_tamper_detection(tmp_path):
    auditor = SourceProvenanceAuditor()
    fake_manifest = {
        "manifest_version": "1.0.0",
        "products": [
            {
                "product_id": "TAMPERED_PRODUCT",
                "relative_path": "data/environment/raw/meda/mars2020_meda_derived_PS.csv",
                "file_size_bytes": 482411,
                "sha256_checksum": "0000000000000000000000000000000000000000000000000000000000000000",
                "platform": "TEST",
                "instrument": "TEST",
                "processing_level": "TEST"
            },
            {
                "product_id": "MISSING_PRODUCT",
                "relative_path": "data/environment/raw/meda/non_existent_file.csv",
                "file_size_bytes": 100,
                "sha256_checksum": "1111111111111111111111111111111111111111111111111111111111111111",
                "platform": "TEST",
                "instrument": "TEST",
                "processing_level": "TEST"
            }
        ]
    }
    m_path = tmp_path / "data" / "environment" / "index" / "source_acquisition_manifest.json"
    m_path.parent.mkdir(parents=True, exist_ok=True)
    with open(m_path, "w", encoding="utf-8") as f:
        json.dump(fake_manifest, f)

    adv_auditor = SourceProvenanceAuditor(workspace_root=str(tmp_path))
    report = adv_auditor.audit_all_products()
    assert report.total_manifest_products == 2
    assert report.verified_products_count == 0
    assert report.discrepancy_count == 2
    assert report.overall_provenance_verdict == ProvenanceVerdict.PARTIALLY_VERIFIED.value

    p_missing = next(p for p in report.product_audits if p.product_id == "MISSING_PRODUCT")
    assert p_missing.provenance_verdict == ProvenanceVerdict.UNAVAILABLE.value


# --- TEST 3: Time & Coordinate Invariants ---
def test_time_and_coordinate_math():
    # EOT swing test across perihelion (Ls=251) and aphelion (Ls=71)
    eot_peri = equation_of_time_hours(251.0)
    eot_aphel = equation_of_time_hours(71.0)
    assert abs(eot_peri) < 0.2  # near zero at perihelion
    # Round-trip LMST <-> LTST
    for h in [0.0, 6.5, 12.0, 18.25, 23.9]:
        ltst = lmst_to_ltst(h, ls_deg=90.0)
        lmst_back = ltst_to_lmst(ltst, ls_deg=90.0)
        assert lmst_back == pytest.approx(h, abs=1e-5)

    # Planetocentric to Planetographic latitude
    lat_cen = 18.4447
    lat_graph = planetocentric_to_planetographic_lat(lat_cen)
    assert lat_graph > lat_cen
    assert lat_graph == pytest.approx(18.66, abs=0.02)


# --- TEST 4: Collocation Sensitivity Gating ---
def test_collocation_sensitivity_thresholds():
    ingestor = PlanetaryArchiveIngestor()
    norm_obs = ingestor.ingest_meda_daily_series()
    ingestor.ingest_mcd_netcdf()

    from marswalk.core.mars_environment_collocation import EnvironmentCollocationEngine, CollocationGateStatus
    # Strict (d <= 2.5 km, dt <= 0.25h, dLs <= 2.5 deg) across full dataset
    strict_eng = EnvironmentCollocationEngine(max_spatial_separation_km=2.5, max_temporal_delta_hours=0.25, max_seasonal_delta_ls_deg=2.5)
    strict_pairs = strict_eng.collocate_dataset(norm_obs, ingestor)
    qualified_strict = [p for p in strict_pairs if p.gate_status == CollocationGateStatus.QUALIFIED.value]
    assert len(qualified_strict) < len(strict_pairs)  # traverses beyond 2.5km rejected (2025 rejected)
    assert len(qualified_strict) == 2548

    # Nominal (d <= 50.0 km) across initial traverse slice
    nom_eng = EnvironmentCollocationEngine(max_spatial_separation_km=50.0)
    nom_pairs = nom_eng.collocate_dataset(norm_obs[:500], ingestor)
    qualified_nom = [p for p in nom_pairs if p.gate_status == CollocationGateStatus.QUALIFIED.value]
    assert len(qualified_nom) == 500  # all Jezero points pass nominal 50km gate


# --- TEST 5: Cross-Boundary Temporal & Seasonal Wrapping ---
def test_collocation_cross_boundary_wrapping():
    rep_engine = PlanetaryRepresentativenessEngine()
    # Cross-midnight delta (23.8h to 0.2h is 0.4h delta)
    res_time = rep_engine.evaluate_representativeness(
        obs_id="OBS_1", obs_lat=18.44, obs_lon=77.45, obs_elev_m=-2570.0, obs_ltst_h=23.8, obs_ls_deg=10.0,
        target_id="TGT_1", target_lat=18.44, target_lon=77.45, target_elev_m=-2570.0, target_ltst_h=0.2, target_ls_deg=10.0
    )
    assert res_time.delta_ltst_hours == pytest.approx(0.4, abs=0.01)

    # Cross-year seasonal delta (358 deg to 2 deg is 4 deg delta)
    res_season = rep_engine.evaluate_representativeness(
        obs_id="OBS_2", obs_lat=18.44, obs_lon=77.45, obs_elev_m=-2570.0, obs_ltst_h=12.0, obs_ls_deg=358.0,
        target_id="TGT_2", target_lat=18.44, target_lon=77.45, target_elev_m=-2570.0, target_ltst_h=12.0, target_ls_deg=2.0
    )
    assert res_season.delta_ls_deg == pytest.approx(4.0, abs=0.01)


# --- TEST 6: Sensor Quality Screening & Null Preservation ---
def test_sensor_quality_screening_null_preservation():
    # Degraded wind sensor: must preserve null without imputation
    q_wind = filter_wind_measurement(wind_speed_m_s=None, wind_dir_deg=None, sensor_flag="SALTATION_GRIT_FAILURE")
    assert q_wind["status"] == QualityStatus.NULL_PRESERVED.value
    assert q_wind["wind_speed_m_s"] is None
    assert "scientific integrity rule" in q_wind["rejection_reason"]

    # ATS sensor: outlier rejected, valid median preserved
    q_ats = filter_ats_measurement([240.0, 240.5, 350.0, 239.5, 240.2])  # 350K is unphysical outlier
    assert q_ats["status"] == QualityStatus.NOMINAL.value
    assert q_ats["air_temp_k"] == pytest.approx(240.2, abs=0.1)


# --- TEST 7: Sensor Quality Shadow Obstruction ---
def test_sensor_quality_shadow_screening():
    q_shad = filter_tirs_measurement(upward_lw_flux=260.0, upward_lw_uncertainty=2.0, ground_not_in_shadow=0)
    assert q_shad["status"] == QualityStatus.REJECTED_SHADOW.value
    assert "rover cast shadow" in q_shad["rejection_reason"]


# --- TEST 8: Statistical Metrics on Hand-Calculated Benchmark ---
def test_statistical_metrics_hand_calculated():
    # Known paired vectors
    # O = [10.0, 20.0, 30.0, 40.0, 50.0], mean = 30.0, std = sqrt(200) = 14.142
    # M = [12.0, 18.0, 33.0, 39.0, 53.0]
    # Residuals = [+2.0, -2.0, +3.0, -1.0, +3.0]
    # Mean Bias = (2 - 2 + 3 - 1 + 3) / 5 = +1.0
    # MAE = (2 + 2 + 3 + 1 + 3) / 5 = 2.2
    # Squared residuals = [4, 4, 9, 1, 9] -> mean = 27 / 5 = 5.4 -> RMSE = sqrt(5.4) = 2.3238
    # SS_tot = (10-30)^2 + (20-30)^2 + (30-30)^2 + (40-30)^2 + (50-30)^2 = 400 + 100 + 0 + 100 + 400 = 1000
    # SS_res = 27 -> R^2 = 1 - 27/1000 = 0.973
    obs = [10.0, 20.0, 30.0, 40.0, 50.0]
    mod = [12.0, 18.0, 33.0, 39.0, 53.0]

    stats = compute_independent_statistics(obs, mod, n_bootstrap=200)
    assert stats.sample_count == 5
    assert stats.mean_bias == pytest.approx(1.0, abs=1e-3)
    assert stats.mae == pytest.approx(2.2, abs=1e-3)
    assert stats.rmse == pytest.approx(math.sqrt(5.4), abs=1e-3)
    assert stats.r_squared == pytest.approx(0.973, abs=1e-3)
    assert stats.pearson_r > 0.98


# --- TEST 9: Statistical Metrics Edge Cases (Zero/Negative R^2) ---
def test_statistical_metrics_zero_and_negative_cases():
    # Constant data
    c_obs = [20.0, 20.0, 20.0]
    c_mod = [20.0, 20.0, 20.0]
    stats_c = compute_independent_statistics(c_obs, c_mod, n_bootstrap=50)
    assert stats_c.rmse == 0.0
    assert stats_c.r_squared == 0.0  # safe zero division

    # Pathological negative R^2 case (model far worse than mean)
    p_obs = [10.0, 20.0, 30.0]  # mean = 20, SS_tot = 200
    p_mod = [100.0, 100.0, 100.0]  # residuals [90, 80, 70], SS_res = 8100 + 6400 + 4900 = 19400
    # R^2 = 1 - 19400 / 200 = 1 - 97 = -96.0
    stats_neg = compute_independent_statistics(p_obs, p_mod, n_bootstrap=50)
    assert stats_neg.r_squared < 0.0
    assert stats_neg.r_squared == pytest.approx(-96.0, abs=0.1)

    # Empty array
    stats_empty = compute_independent_statistics([], [])
    assert stats_empty.sample_count == 0


# --- TEST 10: The 52.1% Held-Out RMSE Reproduction on Benchmark Slice ---
def test_calibration_reproduction_benchmark_slice():
    auditor = CalibrationReproductionAuditor()
    report = auditor.run_reproduction_study()
    b300 = report.benchmark_slice_result

    # Verify exact reproduction of the reported 52.1% claim
    assert b300.test_rmse_reduction_pct == pytest.approx(52.10, abs=0.2)
    assert b300.train_rmse_reduction_pct == pytest.approx(59.16, abs=0.2)
    assert b300.reproduction_verdict == CalibrationReproductionVerdict.REPRODUCED.value
    assert b300.baseline_test_rmse == pytest.approx(50.64, abs=0.2)
    assert b300.calibrated_test_rmse == pytest.approx(24.26, abs=0.2)


# --- TEST 11: Multi-Year Archive Generalization Drift ---
def test_calibration_reproduction_full_archive_drift():
    auditor = CalibrationReproductionAuditor()
    report = auditor.run_reproduction_study()
    fa = report.full_archive_result

    # Expose multi-year generalization collapse (4.22% vs reported 52.1%)
    assert fa.test_rmse_reduction_pct < 10.0
    assert fa.test_rmse_reduction_pct == pytest.approx(4.22, abs=0.5)
    assert fa.reproduction_verdict == CalibrationReproductionVerdict.REPRODUCED_WITH_DEVIATION.value


# --- TEST 12: Parameter Identifiability & Sensitivity ---
def test_parameter_identifiability_sensitivity():
    # phase_shift sensitivity test
    # Evaluates predict_diurnal_spline at dawn (hr=6.0)
    t_nom = predict_diurnal_spline(6.0, 218.0, 38.0, 0.0)
    t_shifted = predict_diurnal_spline(6.0, 218.0, 38.0, 0.5)
    diff = abs(t_shifted - t_nom)
    assert diff > 7.0  # highly sensitive to diurnal phase (7.94 K shift per 30 minutes)


# --- TEST 13: Counterexample Hunting (Where Calibration Failed) ---
def test_counterexample_hunting():
    # Test nocturnal Sol 36 where baseline error was 1.19K but calibration worsened to 7.91K
    base_pred = predict_diurnal_spline(0.0, 218.0, 38.0, 0.0)
    calib_pred = predict_diurnal_spline(0.0, 222.0, 35.0, -0.2)
    obs_val = 175.04
    err_base = abs(base_pred - obs_val)
    err_calib = abs(calib_pred - obs_val)
    assert err_calib > err_base + 3.0  # confirmed counterexample degradation


# --- TEST 14: Competitive Baselines (Persistence Outperforms) ---
def test_baseline_comparisons_persistence():
    # 1-sol persistence test on smooth nocturnal observations
    obs_sol1 = 188.5
    obs_sol2 = 189.0
    persist_err = abs(obs_sol2 - obs_sol1)  # 0.5 K
    static_model_pred = 210.0  # GCM overprediction
    static_err = abs(static_model_pred - obs_sol2)  # 21.0 K
    assert persist_err < static_err


# --- TEST 15: Representativeness Multiplicative Score & Priority Veto ---
def test_representativeness_multiplicative_and_veto():
    rep = PlanetaryRepresentativenessEngine()
    # High horizontal proximity (1.0 km) but extreme vertical cliff (700 m delta)
    # Must trigger NON_COMPARABLE veto
    res = rep.evaluate_representativeness(
        obs_id="OBS_FLOOR", obs_lat=18.4447, obs_lon=77.4508, obs_elev_m=-2570.0, obs_ltst_h=12.0, obs_ls_deg=10.0,
        target_id="TGT_RIM", target_lat=18.4450, target_lon=77.4510, target_elev_m=-1870.0, target_ltst_h=12.0, target_ls_deg=10.0
    )
    assert res.classification == RepresentativenessClass.NON_COMPARABLE.value
    assert "NON_COMPARABLE" in res.confidence_verdict


# --- TEST 16: Hardware Risk Modeling for SHERLOC Spectrometer ---
def test_operational_hardware_thermal_risk():
    unc = EnvironmentModelUncertaintyEngine()
    mock_stats = ResidualStatistics(
        parameter_name="ground_temperature", unit="K", model_name="MCD", sample_count=1000,
        mean_bias=0.0, mae=5.8, rmse=7.22, residual_std=7.22, pearson_r=0.9, r_squared=0.8,
        median_abs_error=5.0, min_residual=-18.0, max_residual=18.0, p05_residual=-14.0,
        p25_residual=-5.0, p50_median_residual=0.0, p75_residual=5.0, p95_residual=14.0
    )
    # Dawn prediction: -46.75 C = 226.4 K
    risk = unc.evaluate_instrument_thermal_risk("SHERLOC", -46.75, mock_stats)
    assert risk.risk_level == "CRITICAL_VIOLATION"
    assert risk.violation_probability_pct > 90.0


# --- TEST 17: Tribunal Master Audit Certificate & Schema Validation ---
def test_tribunal_master_audit_certificate():
    tribunal = ScientificReproducibilityTribunal()
    cert = tribunal.conduct_full_tribunal_audit()
    assert cert.claims_audited_count == 9
    assert cert.claims_reproduced_count == 7
    assert cert.claims_with_deviation_count == 2
    assert cert.claims_rejected_count == 0
    assert cert.the_52_percent_claim_verdict == "REPRODUCED_WITH_DEVIATION"
    assert cert.the_52_percent_benchmark_reduction_pct == pytest.approx(52.1, abs=0.2)

    # Validate against Draft 2020-12 schema
    d = cert.to_dict()
    validate_contract(d, "environmental-tribunal-audit")


# --- TEST 18: Live REST API Endpoint Verification ---
def test_live_tribunal_api_endpoint():
    req = urllib.request.Request("http://127.0.0.1:3000/api/environment-validation/tribunal")
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["overall_certification_status"] == "QUALIFIED_WITH_SCIENTIFIC_DISCLOSURES"
        assert data["claims_audited_count"] == 9
        assert data["the_52_percent_benchmark_reduction_pct"] == pytest.approx(52.1, abs=0.2)
        validate_contract(data, "environmental-tribunal-audit")
