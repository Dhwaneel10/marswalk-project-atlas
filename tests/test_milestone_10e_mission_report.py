"""
MarsWalk 2.0 — Milestone 10E Verification Test Suite.
Tests Mission Science Report & Export Dashboard:
  1. Complete mission report assembly and schema compliance
  2. Incomplete / uncomputed mission handling (explicit nulls, is_computed=False)
  3. Sortie Black-Box event ledger integration and continuation provenance
  4. Environmental intelligence integration (in-situ vs climatology vs archive)
  5. HTML report generation and XSS escaping security
  6. Machine-readable JSON contract roundtrip
  7. API service endpoints (POST /api/mission/report and POST /api/mission/report/html)
  8. Error handling, physical validation, and regression safety
"""

import os
import json
import pytest
from pathlib import Path

from marswalk.api.contracts import validate_contract, SCHEMA_VERSION, TERRAIN_DATASET_ID
from marswalk.core.mission_report import (
    assemble_mission_report,
    generate_mission_report_html,
    generate_report_id,
    MissionReportError,
    NASA_OPERATIONAL_DISCLAIMER,
)
from marswalk.api.service import (
    generate_mission_report_api,
    export_mission_report_html_api,
    APIError,
)
from marswalk.core.mission_event_ledger import record_event, MissionEvent

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
        "min_elevation_m": -2530.0,
        "max_elevation_m": -2410.0,
        "elevation_gain_m": 120.0,
        "max_slope_deg": 14.2,
        "mean_slope_deg": 4.8,
    }


def test_01_report_id_generation():
    """Verify clean, reproducible report ID formatting."""
    rid = generate_report_id("m_jezero_delta_scarp_surve_090607")
    assert rid.startswith("rep_jezero_delta_scarp_sur_")
    assert len(rid) >= 15
    assert " " not in rid


def test_02_assemble_complete_mission_report(nominal_mission_id, mock_route_result):
    """Verify complete report assembly matches schema contract."""
    report = assemble_mission_report(
        nominal_mission_id,
        route_result=mock_route_result,
        weather_site="jezero_crater",
    )
    assert report["schema_version"] == SCHEMA_VERSION
    assert report["mission_id"] == nominal_mission_id
    assert report["mission_name"] == "Jezero Delta Scarp Survey"
    assert report["reproducibility_manifest"]["terrain_dataset_id"] == TERRAIN_DATASET_ID
    assert report["reproducibility_manifest"]["software_version"] == "2.0.0"

    # Plan summary
    assert report["plan_summary"]["start"]["row"] == 117
    assert report["plan_summary"]["start"]["col"] == 157
    assert report["plan_summary"]["goal"]["row"] == 194
    assert report["plan_summary"]["goal"]["col"] == 131
    assert report["plan_summary"]["waypoints_count"] == 2

    # Mobility
    assert report["mobility_metrics"]["total_distance_m"] == 4350.5
    assert report["mobility_metrics"]["total_cost"] == 5120.3
    assert report["mobility_metrics"]["total_duration_s"] == 5400.0
    assert report["mobility_metrics"]["traverse_duration_s"] == 3600.0
    assert report["mobility_metrics"]["is_computed"] is True

    # Stops
    assert len(report["stop_metrics"]) == 2
    assert report["stop_metrics"][0]["stop_id"] == "three_forks"
    assert report["stop_metrics"][1]["stop_id"] == "artuby_ridge"

    # Contract validation
    is_valid, errs = validate_contract(report, "mission-science-report")
    assert is_valid is True, f"Schema validation errors: {errs}"


def test_03_incomplete_uncomputed_mission_report():
    """Verify safe handling of incomplete missions without zero-filling."""
    raw_mission = {
        "mission_id": "m_uncomputed_test",
        "name": "Uncomputed Traverse",
        "canonical_mission": {
            "start": {"row": 50, "col": 50, "name": "Camp Alpha"},
            "goal": {"row": 80, "col": 80, "name": "Ridge Beta"},
            "stops": [],
            "vehicle_mode": "crew_eva",
            "profile": "conservative",
        }
    }
    report = assemble_mission_report(raw_mission, route_result=None, terrain=None)
    assert report["mobility_metrics"]["total_distance_m"] is None
    assert report["mobility_metrics"]["total_cost"] is None
    assert report["mobility_metrics"]["total_duration_s"] is None
    assert report["mobility_metrics"]["is_computed"] is False
    assert report["mission_status"] in ("nominal", "incomplete")

    is_valid, errs = validate_contract(report, "mission-science-report")
    assert is_valid is True, f"Incomplete mission schema errors: {errs}"


def test_04_sortie_ledger_and_continuation_provenance(tmp_path):
    """Verify black-box ledger event integration and continuation status transition."""
    test_mid = "m_test_ledger_prov_10e"
    
    # Record events in isolated temporary ledger directory
    record_event({
        "source_mission_id": test_mid,
        "event_type": "sortie_started",
        "mission_time_s": 0.0,
        "playback_elapsed_s": 0.0,
        "route_variant": "nominal",
    }, base_dir=tmp_path)

    record_event({
        "source_mission_id": test_mid,
        "event_type": "contingency_injected",
        "mission_time_s": 420.0,
        "playback_elapsed_s": 25.0,
        "route_variant": "disrupted",
        "payload": {"reason": "Dust devil encountered"},
    }, base_dir=tmp_path)

    record_event({
        "source_mission_id": test_mid,
        "event_type": "continuation_selected",
        "mission_time_s": 450.0,
        "playback_elapsed_s": 27.0,
        "route_variant": "continuation",
        "continuation_id": "cont_420s_detour",
        "payload": {"strategy": "reroute_ridge"},
    }, base_dir=tmp_path)

    raw_mission = {
        "mission_id": test_mid,
        "name": "Disrupted Sortie",
        "canonical_mission": {
            "start": {"row": 100, "col": 100},
            "goal": {"row": 120, "col": 120},
            "stops": [{"id": "s1", "name": "Stop 1", "row": 110, "col": 110, "dwell_time_s": 600}],
            "vehicle_mode": "crew_eva",
            "profile": "conservative",
        }
    }

    report = assemble_mission_report(
        raw_mission,
        events_dir=tmp_path,
    )

    ledger_summary = report["sortie_ledger_summary"]
    assert ledger_summary["ledger_present"] is True
    assert ledger_summary["total_events_recorded"] == 3
    assert ledger_summary["has_contingencies"] is True
    assert ledger_summary["continuation_count"] == 1
    assert report["mission_status"] == "continued"

    is_valid, errs = validate_contract(report, "mission-science-report")
    assert is_valid is True, f"Ledger report validation error: {errs}"


def test_05_environmental_intelligence_isolation_jezero(nominal_mission_id):
    """Verify authentic in-situ weather telemetry attachment for Jezero Crater."""
    report = assemble_mission_report(nominal_mission_id, weather_site="jezero_crater")
    env = report["environmental_context"]
    assert env is not None
    assert env["site_id"] == "jezero_crater"
    assert env["data_type"] == "IN_SITU_OBSERVATION"
    assert env["observation_sol"] is not None
    assert env["atmospheric_pressure_pa"] > 500.0  # Jezero floor ~589 Pa
    assert env["provenance_institution"] == "NASA / PDS Atmospheres Node"


def test_06_environmental_intelligence_isolation_olympus(nominal_mission_id):
    """Verify Mars Climate Database (MCD) climatology label for Olympus Mons."""
    report = assemble_mission_report(nominal_mission_id, weather_site="olympus_mons")
    env = report["environmental_context"]
    assert env is not None
    assert env["site_id"] == "olympus_mons"
    assert "CLIMATOLOGICAL_MODEL" in env["data_type"]
    assert env["atmospheric_pressure_pa"] < 150.0  # Summit thin atmosphere ~72.4 Pa


def test_07_html_generation_and_xss_escaping():
    """Verify that user-supplied text with potential script injection is safely HTML-escaped."""
    malicious_mission = {
        "mission_id": "m_xss_test",
        "name": "Exploration <script>alert('XSS')</script>",
        "description": "Bold <b>danger</b> & harmful \"quotes\"",
        "canonical_mission": {
            "start": {"row": 10, "col": 10, "name": "Start <img src=x onerror=alert(1)>"},
            "goal": {"row": 20, "col": 20, "name": "Goal <svg/onload=alert(2)>"},
            "stops": [
                {"id": "stop_1", "name": "Stop <script>fetch('leak')</script>", "row": 15, "col": 15, "dwell_time_s": 300}
            ],
            "vehicle_mode": "crew_eva",
            "profile": "conservative",
        }
    }
    report = assemble_mission_report(malicious_mission)
    html_output = generate_mission_report_html(report)

    # Must NOT contain raw unescaped script tags
    assert "<script>alert('XSS')</script>" not in html_output
    assert "<img src=x onerror=alert(1)>" not in html_output
    assert "<svg/onload=alert(2)>" not in html_output
    assert "<script>fetch('leak')</script>" not in html_output

    # Must contain properly escaped entities
    assert "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;" in html_output or "&lt;script&gt;alert('XSS')&lt;/script&gt;" in html_output
    assert "&lt;img src=x onerror=alert(1)&gt;" in html_output


def test_08_html_report_print_and_structure_fidelity(nominal_mission_id, mock_route_result):
    """Verify essential sections and print-media styles exist in HTML report."""
    report = assemble_mission_report(nominal_mission_id, route_result=mock_route_result)
    html_doc = generate_mission_report_html(report)

    assert "<!DOCTYPE html>" in html_doc
    assert "@media print" in html_doc
    assert "MarsWalk 2.0 &mdash; Mission Science Report" in html_doc
    assert "Trajectory Metadata & Reproducibility" in html_doc
    assert "Mobility & Energy Metrics" in html_doc
    assert "Science Waypoints & Sampling Dwell Sequence" in html_doc
    assert "Martian Environmental Intelligence" in html_doc
    assert "Sortie Black-Box Mission Event Ledger" in html_doc
    assert "Scientific Provenance, Verification & Disclaimers" in html_doc
    assert NASA_OPERATIONAL_DISCLAIMER in html_doc


def test_09_api_generate_mission_report_success(nominal_mission_id, mock_route_result):
    """Verify POST /api/mission/report handler."""
    payload = {
        "mission_id": nominal_mission_id,
        "route_result": mock_route_result,
        "weather_site": "jezero_crater",
        "include_html": True,
    }
    res = generate_mission_report_api(payload)
    assert res["status"] == "success"
    assert "report_id" in res
    assert res["report"]["mission_id"] == nominal_mission_id
    assert res["html"].startswith("<!DOCTYPE html>")


def test_10_api_export_mission_report_html(nominal_mission_id):
    """Verify POST /api/mission/report/html handler returns UTF-8 HTML bytes."""
    payload = {
        "mission_id": nominal_mission_id,
        "weather_site": "jezero_crater",
    }
    html_bytes, filename = export_mission_report_html_api(payload)
    assert isinstance(html_bytes, bytes)
    assert html_bytes.startswith(b"<!DOCTYPE html>")
    assert filename.startswith("marswalk_science_report_rep_")
    assert filename.endswith(".html")


def test_11_api_error_on_missing_mission():
    """Verify 400 error when payload lacks both mission_id and mission_plan."""
    payload = {"weather_site": "jezero_crater"}
    with pytest.raises(APIError) as exc_info:
        generate_mission_report_api(payload)
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "ERR_MISSING_MISSION"


def test_12_api_error_on_non_dict_payload():
    """Verify 400 error when payload is not a dictionary."""
    with pytest.raises(APIError) as exc_info:
        generate_mission_report_api(["not", "a", "dict"])
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "ERR_MALFORMED_JSON"


def test_13_mission_not_found_handling():
    """Verify clean 400/404 error when requested mission_id does not exist."""
    with pytest.raises(MissionReportError):
        assemble_mission_report("m_nonexistent_mission_999999")


def test_14_stop_status_progression():
    """Verify stop status reflects ledger progress."""
    raw_mission = {
        "mission_id": "m_progress_test",
        "name": "Progress Test",
        "canonical_mission": {
            "start": {"row": 10, "col": 10},
            "goal": {"row": 50, "col": 50},
            "stops": [
                {"id": "s_alpha", "name": "Stop Alpha", "row": 20, "col": 20, "dwell_time_s": 300},
                {"id": "s_beta", "name": "Stop Beta", "row": 30, "col": 30, "dwell_time_s": 300},
            ],
            "vehicle_mode": "crew_eva",
            "profile": "conservative",
        }
    }
    # When no events recorded, stops are "planned"
    rep = assemble_mission_report(raw_mission)
    assert rep["stop_metrics"][0]["status"] == "planned"
    assert rep["stop_metrics"][1]["status"] == "planned"


def test_15_json_export_roundtrip(nominal_mission_id, mock_route_result):
    """Verify report can be serialized to JSON and loaded back identically."""
    report = assemble_mission_report(nominal_mission_id, route_result=mock_route_result)
    json_text = json.dumps(report, indent=2)
    loaded = json.loads(json_text)

    assert loaded["report_id"] == report["report_id"]
    assert loaded["mobility_metrics"]["total_distance_m"] == report["mobility_metrics"]["total_distance_m"]
    is_valid, _ = validate_contract(loaded, "mission-science-report")
    assert is_valid is True


def test_16_stop_dwell_time_summation(nominal_mission_id, mock_route_result):
    """Verify stop dwell times are correctly aggregated into total_dwell_s."""
    report = assemble_mission_report(nominal_mission_id, route_result=mock_route_result)
    expected_dwell = sum(s["dwell_time_s"] for s in report["stop_metrics"])
    assert report["mobility_metrics"]["total_dwell_s"] == expected_dwell
    assert report["mobility_metrics"]["total_dwell_s"] == 1800.0  # 900s + 900s


def test_17_gale_crater_rems_in_situ_weather(nominal_mission_id):
    """Verify Gale Crater Curiosity REMS in-situ weather telemetry."""
    report = assemble_mission_report(nominal_mission_id, weather_site="gale_crater")
    env = report["environmental_context"]
    assert env is not None
    assert env["site_id"] == "gale_crater"
    assert env["data_type"] == "IN_SITU_OBSERVATION"
    assert env["observation_sol"] == 3720
    assert env["atmospheric_pressure_pa"] == 842.10


def test_18_historical_elysium_insight_weather(nominal_mission_id):
    """Verify Elysium Planitia InSight historical mission archive telemetry."""
    report = assemble_mission_report(nominal_mission_id, weather_site="elysium_planitia")
    env = report["environmental_context"]
    assert env is not None
    assert env["site_id"] == "elysium_planitia"
    assert env["data_type"] == "HISTORICAL_MISSION_ARCHIVE"
    assert env["observation_sol"] == 1440


def test_19_provenance_audit_recomputed_flag(nominal_mission_id, mock_route_result):
    """Verify provenance audit accurately flags when route metrics are precomputed vs recomputed."""
    # With precomputed route
    rep1 = assemble_mission_report(nominal_mission_id, route_result=mock_route_result)
    assert rep1["provenance_audit"]["recomputed_metrics"] is False

    # Without precomputed route
    rep2 = assemble_mission_report(nominal_mission_id, route_result=None)
    assert rep2["provenance_audit"]["recomputed_metrics"] is True


def test_20_html_report_contains_all_stops(nominal_mission_id, mock_route_result):
    """Verify HTML rendered document includes all science stops in tabular format."""
    report = assemble_mission_report(nominal_mission_id, route_result=mock_route_result)
    html_doc = generate_mission_report_html(report)
    assert "three_forks" in html_doc
    assert "artuby_ridge" in html_doc
    assert "Three Forks Sample Depot" in html_doc
    assert "Artuby Ridge Scarp" in html_doc

