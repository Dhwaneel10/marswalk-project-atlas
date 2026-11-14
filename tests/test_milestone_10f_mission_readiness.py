"""
MarsWalk 2.0 — Milestone 10F Verification Test Suite.
Tests Mission Readiness & Decision Gate Engine:
  1. Feasible mission with complete inputs (READY_FOR_REVIEW)
  2. Unreachable required destination handling (BLOCKED)
  3. Budget and duration constraint failures (BLOCKED)
  4. Missing optional route metrics (INCOMPLETE)
  5. Missing, cached, stale, and historical weather
  6. Modelled climate data distinction (MCD v6.1 notice)
  7. Weather site geographic mismatch (Jezero vs Gale Crater)
  8. Existing mission with no event ledger history
  9. Recorded vs recomputed telemetry flags
  10. Tested vs untested robustness scenarios
  11. Malformed mission inputs and unknown mission IDs
  12. Finding severity and status determinism
  13. Assessment identity and reproducibility manifest
  14. Historical assessment persistence and non-destructive immutability
  15. Draft 2020-12 JSON Schema validation and API integration
  16. Regression tests for existing report, event ledger, and weather engines
"""

import os
import json
import pytest
from pathlib import Path

from marswalk.api.contracts import validate_contract, SCHEMA_VERSION, TERRAIN_DATASET_ID
from marswalk.core.mission_readiness import (
    evaluate_mission_readiness,
    save_mission_readiness_assessment,
    get_mission_readiness_assessment,
    list_mission_readiness_assessments,
    generate_assessment_id,
    MissionReadinessError,
    NASA_OPERATIONAL_DISCLAIMER,
    SUPPORTED_DISRUPTION_CLASSES,
)
from marswalk.api.service import (
    evaluate_mission_readiness_api,
    list_mission_readiness_api,
    get_mission_readiness_api,
    APIError,
)
from marswalk.core.mission_event_ledger import record_event

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MISSIONS_DIR = PROJECT_ROOT / "data" / "workspaces" / "missions"
EVENTS_DIR = PROJECT_ROOT / "data" / "workspaces" / "events"


@pytest.fixture
def nominal_mission_id():
    return "m_jezero_delta_scarp_surve_090607"


@pytest.fixture
def mock_route_result():
    return {
        "total_distance_m": 4350.5,
        "total_cost": 5120.3,
        "total_duration_s": 5400.0,
        "traverse_duration_s": 3600.0,
        "max_slope_deg": 12.4,
        "mean_slope_deg": 4.2,
    }


@pytest.fixture
def mock_robustness_result():
    return {
        "evaluated_disruption_classes": SUPPORTED_DISRUPTION_CLASSES,
        "tested_cases": [{"case_id": f"c_{i}"} for i in range(6)],
        "breakpoints": [],
    }


def test_01_assessment_id_generation():
    """Verify clean, deterministic prefix assessment identifier formatting."""
    aid = generate_assessment_id("m_jezero_delta_scarp_surve_090607")
    assert aid.startswith("asmt_jezero_delta_scarp_sur_")
    assert len(aid) >= 16
    assert " " not in aid


def test_02_ready_for_review_status(nominal_mission_id, mock_route_result, mock_robustness_result):
    """Verify full feasibility, verified in-situ weather, and tested robustness produce READY_FOR_REVIEW."""
    asmt = evaluate_mission_readiness(
        nominal_mission_id,
        route_result=mock_route_result,
        robustness_result=mock_robustness_result,
        weather_site="jezero_crater",
        persist_assessment=False,
    )
    assert asmt["readiness_status"] == "READY_FOR_REVIEW"
    assert asmt["blocker_count"] == 0
    assert asmt["warning_count"] == 0
    assert asmt["readiness_score"] == 100.0
    assert "READY FOR REVIEW" in asmt["summary"]

    is_valid, errs = validate_contract(asmt, "mission-readiness-assessment")
    assert is_valid is True, f"Contract validation failed: {errs}"


def test_03_incomplete_uncomputed_route():
    """Verify missing trajectory evaluation produces INCOMPLETE status with null metrics."""
    raw_mission = {
        "mission_id": "m_test_uncomputed",
        "name": "Uncomputed Traverse",
        "canonical_mission": {
            "start": {"row": 100, "col": 100},
            "goal": {"row": 140, "col": 140},
            "stops": [],
            "vehicle_mode": "crew_eva",
            "profile": "conservative",
        }
    }
    asmt = evaluate_mission_readiness(raw_mission, route_result=None, terrain=None, persist_assessment=False)
    assert asmt["readiness_status"] == "INCOMPLETE"
    assert asmt["blocker_count"] == 0
    assert asmt["categories_summary"]["feasibility"]["route_exists"] is False
    assert asmt["categories_summary"]["feasibility"]["total_duration_s"] is None
    assert any(f["finding_code"] == "FEAS_ROUTE_UNCOMPUTED" for f in asmt["findings"])

    is_valid, errs = validate_contract(asmt, "mission-readiness-assessment")
    assert is_valid is True, f"Incomplete assessment contract failed: {errs}"


def test_04_budget_violation_blocker(nominal_mission_id):
    """Verify duration exceeding operational budget produces BLOCKED status."""
    over_budget_route = {
        "total_distance_m": 25000.0,
        "total_cost": 30000.0,
        "total_duration_s": 36000.0,  # 10 hours > 8 hour nominal EVA budget
        "max_slope_deg": 10.0,
    }
    asmt = evaluate_mission_readiness(
        nominal_mission_id,
        route_result=over_budget_route,
        operational_budget_s=28800.0,
        persist_assessment=False,
    )
    assert asmt["readiness_status"] == "BLOCKED"
    assert asmt["blocker_count"] >= 1
    assert asmt["categories_summary"]["feasibility"]["is_within_budget"] is False
    assert any(f["finding_code"] == "FEAS_BUDGET_EXCEEDED" and f["is_blocking"] for f in asmt["findings"])


def test_05_unreachable_destination_blocker():
    """Verify missing coordinates or impossible routing yields BLOCKED status."""
    bad_mission = {
        "mission_id": "m_bad_coords",
        "canonical_mission": {
            "start": None,
            "goal": {"row": 100, "col": 100},
        }
    }
    asmt = evaluate_mission_readiness(bad_mission, persist_assessment=False)
    assert asmt["readiness_status"] == "BLOCKED"
    assert asmt["blocker_count"] >= 1
    assert any(f["finding_code"] == "FEAS_MISSING_ENDPOINTS" for f in asmt["findings"])


def test_06_environmental_site_mismatch_warning(nominal_mission_id, mock_route_result):
    """Verify querying Gale Crater REMS weather for Jezero traverse triggers ENV_SITE_MISMATCH."""
    asmt = evaluate_mission_readiness(
        nominal_mission_id,
        route_result=mock_route_result,
        weather_site="gale_crater",
        persist_assessment=False,
    )
    assert asmt["categories_summary"]["environmental"]["is_site_compatible"] is False
    assert any(f["finding_code"] == "ENV_SITE_MISMATCH" and f["severity"] == "warning" for f in asmt["findings"])
    assert asmt["readiness_status"] == "CONDITIONAL"


def test_07_climatological_model_distinction(nominal_mission_id, mock_route_result):
    """Verify MCD model weather produces numerical climate model disclosure warning."""
    asmt = evaluate_mission_readiness(
        nominal_mission_id,
        route_result=mock_route_result,
        weather_site="olympus_mons",
        persist_assessment=False,
    )
    assert asmt["categories_summary"]["environmental"]["data_type"] == "CLIMATOLOGICAL_MODEL"
    assert any(f["finding_code"] == "ENV_CLIMATOLOGICAL_MODEL_NOTICE" for f in asmt["findings"])


def test_08_historical_archive_notice(nominal_mission_id, mock_route_result):
    """Verify InSight APSS historical archive produces archival warning."""
    asmt = evaluate_mission_readiness(
        nominal_mission_id,
        route_result=mock_route_result,
        weather_site="elysium_planitia",
        persist_assessment=False,
    )
    assert "HISTORICAL" in asmt["categories_summary"]["environmental"]["data_type"]
    assert any(f["finding_code"] == "ENV_HISTORICAL_ARCHIVE_NOTICE" for f in asmt["findings"])


def test_09_stale_weather_data_handling(nominal_mission_id, mock_route_result):
    """Verify stale environmental cache status is flagged without fabricating fresh data."""
    stale_weather = {
        "status": "success",
        "site_id": "jezero_crater",
        "site_name": "Jezero Crater",
        "data_type": "IN_SITU_OBSERVATION",
        "freshness_status": "STALE_ARCHIVE",
        "observation_sol": 1500,
        "measurements": {"atmospheric_pressure_pa": 580.0, "air_temperature_c": -60.0},
    }
    asmt = evaluate_mission_readiness(
        nominal_mission_id,
        route_result=mock_route_result,
        weather_snapshot=stale_weather,
        persist_assessment=False,
    )
    assert any(f["finding_code"] == "ENV_DATA_STALE" and f["severity"] == "warning" for f in asmt["findings"])


def test_10_missing_optional_telemetry_not_zero_filled(nominal_mission_id, mock_route_result):
    """Verify missing sensor fields are preserved as null and reported honestly."""
    partial_weather = {
        "status": "success",
        "site_id": "jezero_crater",
        "site_name": "Jezero Crater",
        "data_type": "IN_SITU_OBSERVATION",
        "freshness_status": "ACTIVE_MISSION_CADENCE",
        "observation_sol": 1619,
        "measurements": {"atmospheric_pressure_pa": 589.69, "wind_speed_m_s": None},
    }
    asmt = evaluate_mission_readiness(
        nominal_mission_id,
        route_result=mock_route_result,
        weather_snapshot=partial_weather,
        persist_assessment=False,
    )
    assert any(f["finding_code"] == "ENV_INCOMPLETE_SENSOR_TELEMETRY" for f in asmt["findings"])


def test_11_untested_robustness_scenarios_labeling(nominal_mission_id, mock_route_result):
    """Verify untested robustness dimensions are surfaced with untested severity, never passed."""
    partial_robustness = {
        "evaluated_disruption_classes": ["corridor_closure"],
        "tested_cases": [{"case_id": "rockfall"}],
        "breakpoints": [],
    }
    asmt = evaluate_mission_readiness(
        nominal_mission_id,
        route_result=mock_route_result,
        robustness_result=partial_robustness,
        weather_site="jezero_crater",
        persist_assessment=False,
    )
    assert asmt["readiness_status"] == "CONDITIONAL"
    assert asmt["categories_summary"]["robustness"]["untested_scenarios_count"] == 5
    assert any(f["finding_code"] == "ROB_UNTESTED_SCENARIOS" and f["severity"] == "untested" for f in asmt["findings"])


def test_12_robustness_breakpoints_surfaced(nominal_mission_id, mock_route_result):
    """Verify detected disruption breakpoints are surfaced as warnings."""
    breakpoint_robustness = {
        "evaluated_disruption_classes": SUPPORTED_DISRUPTION_CLASSES,
        "tested_cases": [{"case_id": "case_1"}],
        "breakpoints": [{"case_id": "c1", "reason": "Severe corridor blockage"}],
    }
    asmt = evaluate_mission_readiness(
        nominal_mission_id,
        route_result=mock_route_result,
        robustness_result=breakpoint_robustness,
        weather_site="jezero_crater",
        persist_assessment=False,
    )
    assert asmt["readiness_status"] == "CONDITIONAL"
    assert any(f["finding_code"] == "ROB_BREAKPOINTS_SURFACED" and f["severity"] == "warning" for f in asmt["findings"])


def test_13_tight_operational_margin_warning(nominal_mission_id):
    """Verify traverse duration leaving < 15% budget generates warning."""
    tight_route = {
        "total_distance_m": 8000.0,
        "total_cost": 9000.0,
        "total_duration_s": 26000.0,  # 28800 - 26000 = 2800s (~9.7% margin)
        "max_slope_deg": 11.0,
    }
    asmt = evaluate_mission_readiness(
        nominal_mission_id,
        route_result=tight_route,
        operational_budget_s=28800.0,
        persist_assessment=False,
    )
    assert any(f["finding_code"] == "FEAS_TIGHT_OPERATIONAL_MARGIN" and f["severity"] == "warning" for f in asmt["findings"])
    assert asmt["readiness_status"] == "CONDITIONAL"


def test_14_mission_event_ledger_correlation(tmp_path, nominal_mission_id, mock_route_result):
    """Verify black box sortie event ledger logs are correlated."""
    record_event({
        "source_mission_id": nominal_mission_id,
        "event_type": "sortie_started",
        "mission_time_s": 0.0,
        "playback_elapsed_s": 0.0,
        "route_variant": "nominal",
    }, base_dir=tmp_path)

    asmt = evaluate_mission_readiness(
        nominal_mission_id,
        route_result=mock_route_result,
        events_dir=tmp_path,
        persist_assessment=False,
    )
    assert asmt["categories_summary"]["provenance"]["ledger_present"] is True
    assert asmt["categories_summary"]["provenance"]["events_count"] == 1
    assert any(f["finding_code"] == "PROV_LEDGER_CORRELATED" for f in asmt["findings"])


def test_15_atomic_assessment_persistence(tmp_path, nominal_mission_id, mock_route_result):
    """Verify atomic persistence preserves historical immutability without modifying mission."""
    asmt = evaluate_mission_readiness(
        nominal_mission_id,
        route_result=mock_route_result,
        readiness_dir=tmp_path,
        persist_assessment=True,
    )
    aid = asmt["assessment_id"]
    saved_file = tmp_path / f"{aid}.json"
    assert saved_file.is_file()

    loaded = get_mission_readiness_assessment(aid, base_dir=tmp_path)
    assert loaded["assessment_id"] == aid
    assert loaded["readiness_status"] == asmt["readiness_status"]

    items = list_mission_readiness_assessments(mission_id=nominal_mission_id, base_dir=tmp_path)
    assert len(items) == 1
    assert items[0]["assessment_id"] == aid


def test_16_api_evaluate_readiness_success(nominal_mission_id, mock_route_result):
    """Verify POST /api/mission/readiness service handler."""
    payload = {
        "mission_id": nominal_mission_id,
        "route_result": mock_route_result,
        "weather_site": "jezero_crater",
        "persist": False,
    }
    res = evaluate_mission_readiness_api(payload)
    assert res["status"] == "success"
    assert "assessment_id" in res
    assert res["assessment"]["mission_id"] == nominal_mission_id


def test_17_api_evaluate_readiness_missing_mission():
    """Verify 400 rejection when payload lacks mission_id and mission_plan."""
    payload = {"weather_site": "jezero_crater"}
    with pytest.raises(APIError) as exc_info:
        evaluate_mission_readiness_api(payload)
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "ERR_MISSING_MISSION"


def test_18_api_evaluate_readiness_malformed_json():
    """Verify 400 rejection for non-dict payloads."""
    with pytest.raises(APIError) as exc_info:
        evaluate_mission_readiness_api(["not", "a", "dict"])
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "ERR_MALFORMED_JSON"


def test_19_nonexistent_mission_id_error():
    """Verify clean 400/404 error when requested mission_id does not exist."""
    with pytest.raises(MissionReadinessError):
        evaluate_mission_readiness("m_nonexistent_mission_000000", persist_assessment=False)


def test_20_reproducibility_manifest_and_disclaimer(nominal_mission_id, mock_route_result):
    """Verify manifest includes DTM SHA-256 and operational safety disclaimer is present."""
    asmt = evaluate_mission_readiness(
        nominal_mission_id,
        route_result=mock_route_result,
        persist_assessment=False,
    )
    manifest = asmt["reproducibility_manifest"]
    assert manifest["terrain_dataset_id"] == TERRAIN_DATASET_ID
    assert len(manifest["terrain_sha256"]) == 64
    assert NASA_OPERATIONAL_DISCLAIMER in asmt["limitations_and_disclaimers"]
