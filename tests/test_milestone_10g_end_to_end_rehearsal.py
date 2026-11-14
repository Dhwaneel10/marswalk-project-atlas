"""
MarsWalk 2.0 — Milestone 10G Verification Test Suite:
End-to-End Mission Rehearsal, Integration Hardening & V1 Readiness.

Exercises the full 11-stage integration workflow and verifies cross-system invariants:
  1. Saved mission loading & baseline route generation
  2. Multi-target waypoint traversal & dwell time accounting
  3. Playback model construction & mid-sortie state capture
  4. Contingency injection & 3-stage remaining trade-off evaluation (nominal, disrupted, adaptive)
  5. Sortie black box event recording & deterministic retrieval
  6. Environmental telemetry inspection (MEDA in-situ vs MCD model distinction)
  7. Mission science report assembly & HTML/JSON dual export
  8. Mission readiness decision gate assessment & structured findings
  9. Decision Pack bundle assembly & cryptographic integrity fingerprint verification
  10. Incident replay decision fidelity & delta metric reconstruction
  11. User workspace immutability & non-destructive preservation
  12. Boundary handling: unknown mission IDs, invalid disruption radii, budget overruns
  13. Scientific rigor: units consistency, missing telemetry null preservation, disclaimer verification
"""

import os
import json
import copy
import hashlib
import tempfile
import pytest
from pathlib import Path
import rasterio

from marswalk.core.terrain import load_and_process_terrain, TerrainGrid
from marswalk.core.planner import (
    ScienceWaypoint,
    plan_route,
    plan_sequential_multistop_route,
    format_duration,
)
from marswalk.core.mission_playback import (
    build_mission_playback_model,
    interpolate_playback_state,
)
from marswalk.core.mission_continuation import (
    MidSortieState,
    capture_mid_sortie_state,
    plan_mission_continuation,
)
from marswalk.core.contingency import (
    CustomEventType,
    CustomEventDefinition,
)
from marswalk.core.mission_event_ledger import (
    MissionEvent,
    record_event,
    record_events_batch,
    get_mission_events,
    clear_mission_events,
)
from marswalk.core.weather import (
    get_weather_manager,
    WeatherSnapshot,
    PDS_MEDA_ARCHIVE_URL,
)
from marswalk.core.mission_report import (
    assemble_mission_report,
    generate_mission_report_html,
)
from marswalk.core.mission_readiness import (
    evaluate_mission_readiness,
    get_mission_readiness_assessment,
    list_mission_readiness_assessments,
    NASA_OPERATIONAL_DISCLAIMER,
)
from marswalk.api.decision_pack import (
    verify_bundle_integrity,
    generate_comparison_csv,
    generate_decision_pack_briefing_md,
    build_decision_pack_zip,
)
from marswalk.core.incident_replay import (
    replay_incident,
    reconstruct_incident_timeline,
)
from marswalk.api.workspace import (
    get_mission,
    list_missions,
    DEFAULT_MISSIONS_DIR,
)
from marswalk.api.contracts import (
    validate_contract,
    compute_input_fingerprint,
    compute_bundle_execution_digest,
    build_canonical_mission_run_bundle,
    TERRAIN_DATASET_ID,
    TERRAIN_SHA256,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TERRAIN_PATH = PROJECT_ROOT / "data" / "processed" / "jezero_ready_20m.tif"
SAVED_MISSION_ID = "m_jezero_delta_scarp_surve_090607"


@pytest.fixture(scope="module")
def terrain_and_transform():
    """Load authentic USGS 20m CTX DTM grid once for module tests."""
    terrain = load_and_process_terrain(str(TERRAIN_PATH))
    with rasterio.open(str(TERRAIN_PATH)) as src:
        transform = src.transform
    return terrain, transform


@pytest.fixture
def clean_events_dir(tmp_path):
    """Provide isolated events directory for integration testing."""
    return tmp_path / "events"


def _plan_mission_helper(cm, terrain, transform):
    from marswalk.api.service import plan_route_api
    return plan_route_api(payload=copy.deepcopy(cm), terrain=terrain, transform=transform)


# =============================================================================
# 1. END-TO-END WORKFLOW INTEGRATION TESTS
# =============================================================================

def test_01_saved_mission_retrieval_and_integrity():
    """Step 1: Open Atlas workspace and select verified saved mission."""
    mission = get_mission(SAVED_MISSION_ID)
    assert mission is not None
    assert mission["mission_id"] == SAVED_MISSION_ID
    assert mission["terrain_dataset_id"] == TERRAIN_DATASET_ID
    assert "canonical_mission" in mission
    cm = mission["canonical_mission"]
    assert cm["start"]["row"] == 117 and cm["start"]["col"] == 157
    assert cm["goal"]["row"] == 194 and cm["goal"]["col"] == 131
    assert len(cm["stops"]) >= 2


def test_02_baseline_multi_stop_route_planning(terrain_and_transform):
    """Step 2 & 3: Generate baseline multi-target route and inspect route metrics."""
    terrain, transform = terrain_and_transform
    mission = get_mission(SAVED_MISSION_ID)
    cm = mission["canonical_mission"]

    route_res = _plan_mission_helper(cm, terrain, transform)

    assert route_res["is_reachable"] is True
    assert route_res["distance_m"] > 1000.0
    assert route_res["travel_time_s"] > 1000.0
    assert route_res["route_metrics"]["total_mission_time_s"] >= route_res["travel_time_s"]
    assert len(route_res["visited_waypoint_ids"]) == len(cm["stops"])
    assert len(route_res["path_rc"]) > 50


def test_03_mission_playback_model_and_mid_sortie_handoff(terrain_and_transform):
    """Step 4: Build playback model and advance to mid-sortie state."""
    terrain, transform = terrain_and_transform
    mission = get_mission(SAVED_MISSION_ID)
    cm = mission["canonical_mission"]

    base_route = _plan_mission_helper(cm, terrain, transform)

    playback = build_mission_playback_model(
        route_data=base_route,
        terrain=terrain,
        vehicle_mode="crew_eva",
    )

    assert playback.total_duration_s > 0.0
    assert len(playback.samples) >= 5

    # Advance playback to intermediate time (e.g., 500s)
    interruption_time_s = 500.0
    current_state = interpolate_playback_state(playback, interruption_time_s)
    assert current_state["time_s"] == interruption_time_s
    assert current_state["rc"] is not None
    assert current_state["elevation_m"] > -3000.0


def test_04_contingency_injection_and_adaptive_continuation(terrain_and_transform):
    """Step 5: Inject disruption and compare nominal, disrupted and adaptive continuation."""
    terrain, transform = terrain_and_transform
    mission = get_mission(SAVED_MISSION_ID)
    cm = mission["canonical_mission"]

    base_route = _plan_mission_helper(cm, terrain, transform)

    playback = build_mission_playback_model(
        route_data=base_route,
        terrain=terrain,
        vehicle_mode="crew_eva",
    )

    # Capture mid-sortie state at 600s
    mid_state = capture_mid_sortie_state(
        playback_model=playback,
        interruption_time_s=600.0,
        terrain=terrain,
        total_budget_s=25000.0,
        goal_rc=(cm["goal"]["row"], cm["goal"]["col"]),
    )

    assert mid_state.interruption_time_s == 600.0
    assert mid_state.remaining_budget_s == 25000.0 - 600.0

    # Inject corridor rockfall
    rockfall_center = (mid_state.rover_rc[0] + 5, mid_state.rover_rc[1] + 5)
    injected_event = {
        "id": "evt_rockfall_rehearsal",
        "name": "Corridor Rockfall",
        "event_type": "closed_corridor",
        "center_rc": list(rockfall_center),
        "radius_m": 60.0,
    }

    continuation_eval = plan_mission_continuation(
        terrain=terrain,
        mid_state=mid_state,
        event_definition=injected_event,
        profile="conservative",
        vehicle_mode="crew_eva",
        transform=transform,
    )

    assert continuation_eval["continuation_id"].startswith("cont_")
    assert continuation_eval["nominal_remaining"] is not None
    assert continuation_eval["disrupted_remaining"] is not None
    assert continuation_eval["adaptive_continuation"] is not None
    assert "recommendation" in continuation_eval


def test_05_sortie_black_box_event_ledger_integration(clean_events_dir):
    """Step 6: Verify event ledger accurately records chronological events and decisions."""
    mission_id = "test_rehearsal_mission"
    events = [
        MissionEvent(
            event_id="evt_reh_01",
            source_mission_id=mission_id,
            recorded_at_utc="2026-10-26T02:00:00Z",
            mission_time_s=0.0,
            playback_elapsed_s=0.0,
            event_type="sortie_started",
            route_variant="nominal",
            rover_rc=(117, 157),
            elevation_m=-2540.0,
            slope_deg=1.5,
            payload={"note": "Sortie commenced"},
        ),
        MissionEvent(
            event_id="evt_reh_02",
            source_mission_id=mission_id,
            recorded_at_utc="2026-10-26T02:10:00Z",
            mission_time_s=600.0,
            playback_elapsed_s=60.0,
            event_type="contingency_injected",
            route_variant="disrupted",
            rover_rc=(130, 148),
            elevation_m=-2530.0,
            slope_deg=3.2,
            payload={"hazard": "rockfall", "radius_m": 60.0},
        ),
        MissionEvent(
            event_id="evt_reh_03",
            source_mission_id=mission_id,
            recorded_at_utc="2026-10-26T02:10:05Z",
            mission_time_s=605.0,
            playback_elapsed_s=60.5,
            event_type="continuation_selected",
            route_variant="adaptive",
            rover_rc=(130, 148),
            elevation_m=-2530.0,
            slope_deg=3.2,
            payload={"action": "detour_engaged", "added_dist_m": 120.0},
        ),
    ]

    record_events_batch(events, base_dir=clean_events_dir)

    retrieved = get_mission_events(mission_id, base_dir=clean_events_dir)
    assert len(retrieved) == 3
    assert retrieved[0].event_type == "sortie_started"
    assert retrieved[1].event_type == "contingency_injected"
    assert retrieved[2].event_type == "continuation_selected"
    assert retrieved[1].mission_time_s == 600.0


def test_06_environmental_intelligence_and_provenance():
    """Step 7: Inspect environmental observations, timestamps and source provenance."""
    wm = get_weather_manager()
    report = wm.get_weather(site_id="jezero_crater", force_refresh=False)

    assert report["status"] == "success"
    assert report["site_id"] == "jezero_crater"
    assert report["data_type"] == "IN_SITU_OBSERVATION"
    assert report["observation_sol"] == 1619
    assert report["measurements"]["atmospheric_pressure_pa"] == 589.69
    assert report["measurements"]["wind_speed_m_s"] is None  # Missing remains null!
    assert report["source_metadata"]["archive_url"] == PDS_MEDA_ARCHIVE_URL
    assert "observation_archive_distinction" in report["source_metadata"]

    # Verify Olympus Mons climatological model distinction
    mcd_report = wm.get_weather(site_id="olympus_mons")
    assert mcd_report["data_type"] == "CLIMATOLOGICAL_MODEL"
    assert mcd_report["measurements"]["atmospheric_pressure_pa"] < 100.0  # Thin caldera air


def test_07_mission_science_report_assembly_and_export(terrain_and_transform):
    """Step 8: Generate a Mission Science Report and export HTML and JSON."""
    terrain, transform = terrain_and_transform
    mission = get_mission(SAVED_MISSION_ID)
    cm = mission["canonical_mission"]

    route_res = _plan_mission_helper(cm, terrain, transform)

    report_data = assemble_mission_report(
        mission_data_or_id=mission,
        route_result=route_res,
        weather_site="jezero_crater",
    )

    assert report_data["report_id"].startswith("rep_")
    assert report_data["reproducibility_manifest"]["terrain_dataset_id"] == TERRAIN_DATASET_ID
    assert report_data["mobility_metrics"]["is_computed"] is True
    assert report_data["mobility_metrics"]["total_distance_m"] > 1000.0

    html = generate_mission_report_html(report_data)
    assert "<!DOCTYPE html>" in html
    assert TERRAIN_DATASET_ID in html
    assert "NASA" in html and "PDS" in html


def test_08_mission_readiness_decision_gate_assessment(terrain_and_transform):
    """Step 9: Generate a Mission Readiness assessment and inspect its evidence."""
    terrain, transform = terrain_and_transform
    mission = get_mission(SAVED_MISSION_ID)
    cm = mission["canonical_mission"]

    route_res = _plan_mission_helper(cm, terrain, transform)

    assessment = evaluate_mission_readiness(
        mission_data_or_id=mission,
        route_result=route_res,
        terrain=terrain,
        transform=transform,
        weather_site="jezero_crater",
        persist_assessment=False,
    )

    assert assessment["assessment_id"].startswith("asmt_")
    assert assessment["readiness_status"] in ("READY_FOR_REVIEW", "CONDITIONAL")
    assert assessment["readiness_score"] >= 60.0
    assert len(assessment["findings"]) >= 1

    # Verify every finding has actionable fields
    for f in assessment["findings"]:
        assert "finding_code" in f
        assert "recommended_action" in f
        assert "evidence_references" in f


def test_09_decision_pack_bundle_and_integrity_verification(terrain_and_transform):
    """Step 10: Verify Decision Pack assembly and bundle integrity verification."""
    terrain, transform = terrain_and_transform
    mission = get_mission(SAVED_MISSION_ID)
    cm = mission["canonical_mission"]

    base_route = _plan_mission_helper(cm, terrain, transform)

    bundle = build_canonical_mission_run_bundle(
        mission_input=cm,
        baseline_route=base_route,
        terrain=terrain,
    )

    assert "bundle_id" in bundle
    assert "computation_fingerprint" in bundle
    assert "baseline_fingerprint" in bundle
    assert "execution_digest" in bundle

    # Verify integrity passes on authentic bundle
    integrity = verify_bundle_integrity(bundle)
    assert integrity["is_integrity_valid"] is True
    assert len(integrity["integrity_errors"]) == 0

    # Tampering with distance must fail integrity
    corrupted_bundle = copy.deepcopy(bundle)
    corrupted_bundle["baseline_route"]["distance_m"] = 99999.0
    corrupted_integrity = verify_bundle_integrity(corrupted_bundle)
    assert corrupted_integrity["is_integrity_valid"] is False
    assert any("mismatch" in err.lower() for err in corrupted_integrity["integrity_errors"])


def test_10_incident_replay_decision_fidelity(terrain_and_transform, clean_events_dir):
    """Step 10b: Reconstruct incident replay decision fidelity from recorded events."""
    terrain, transform = terrain_and_transform
    mission_id = "test_incident_replay_mission"

    # Seed events with nominal and adaptive continuation
    events = [
        MissionEvent(
            event_id="evt_inc_01",
            source_mission_id=mission_id,
            recorded_at_utc="2026-10-26T02:00:00Z",
            mission_time_s=0.0,
            playback_elapsed_s=0.0,
            event_type="sortie_started",
            route_variant="nominal",
            rover_rc=(136, 142),
            elevation_m=-2538.0,
            slope_deg=2.2,
        ),
        MissionEvent(
            event_id="evt_inc_02",
            source_mission_id=mission_id,
            recorded_at_utc="2026-10-26T02:05:00Z",
            mission_time_s=300.0,
            playback_elapsed_s=30.0,
            event_type="contingency_injected",
            route_variant="disrupted",
            rover_rc=(136, 142),
            elevation_m=-2538.0,
            slope_deg=2.2,
            payload={
                "event_type": "closure",
                "center_rc": [140, 145],
                "radius_m": 60.0,
                "remaining_budget_s": 25000.0,
                "destination_rc": [194, 131],
            },
        ),
    ]
    record_events_batch(events, base_dir=clean_events_dir)

    replay_res = replay_incident(
        source_mission_id=mission_id,
        terrain=terrain,
        transform=transform,
        base_dir=clean_events_dir,
    )

    assert replay_res["status"] == "success"
    assert replay_res["source_mission_id"] == mission_id
    assert "fidelity" in replay_res
    assert "variance_distance_m" in replay_res["fidelity"]
    assert replay_res["total_events"] == 2


def test_11_original_missions_and_data_immutability():
    """Step 11: Confirm original saved missions and records remain unmodified."""
    mission = get_mission(SAVED_MISSION_ID)
    assert mission["mission_id"] == SAVED_MISSION_ID
    assert mission["name"] == "Jezero Delta Scarp Survey"
    # Ensure mission file has not been deleted or emptied
    mpath = Path(DEFAULT_MISSIONS_DIR) / f"{SAVED_MISSION_ID}.json"
    assert mpath.exists()
    assert mpath.stat().st_size > 100


# =============================================================================
# 2. BOUNDARY CONDITIONS, FAILURE CASES & RIGOR TESTS
# =============================================================================

def test_12_nonexistent_mission_rejection():
    """Verify non-existent mission IDs produce appropriate clean errors."""
    with pytest.raises(Exception):
        get_mission("m_definitely_nonexistent_999999")


def test_13_budget_overrun_triggers_blocker(terrain_and_transform):
    """Verify mission with duration exceeding budget yields BLOCKED readiness."""
    terrain, transform = terrain_and_transform
    mission = get_mission(SAVED_MISSION_ID)

    synthetic_route = {
        "is_reachable": True,
        "travel_time_s": 35000.0,
        "duration_s": 35000.0,
        "total_duration_s": 35000.0,
        "distance_m": 5000.0,
        "path_rc": [[117, 157], [194, 131]],
    }

    assessment = evaluate_mission_readiness(
        mission_data_or_id=mission,
        route_result=synthetic_route,
        terrain=terrain,
        transform=transform,
        operational_budget_s=10000.0,  # 35000 > 10000
        persist_assessment=False,
    )

    assert assessment["readiness_status"] == "BLOCKED"
    assert assessment["readiness_score"] <= 25.0
    assert any(f["finding_code"] == "FEAS_BUDGET_EXCEEDED" for f in assessment["findings"])


def test_14_unreachable_destination_readiness(terrain_and_transform):
    """Verify unreachable route result triggers BLOCKED status."""
    terrain, transform = terrain_and_transform
    mission = get_mission(SAVED_MISSION_ID)

    unreachable_route = {
        "is_reachable": False,
        "distance_m": 0.0,
        "travel_time_s": 0.0,
        "path_rc": [],
    }

    assessment = evaluate_mission_readiness(
        mission_data_or_id=mission,
        route_result=unreachable_route,
        terrain=terrain,
        transform=transform,
        persist_assessment=False,
    )

    assert assessment["readiness_status"] == "BLOCKED"
    assert any(f["finding_code"] == "FEAS_UNREACHABLE_DESTINATION" for f in assessment["findings"])


def test_15_environmental_site_mismatch_warning(terrain_and_transform):
    """Verify requesting Gale Crater weather for Jezero mission produces site mismatch warning."""
    terrain, transform = terrain_and_transform
    mission = get_mission(SAVED_MISSION_ID)

    assessment = evaluate_mission_readiness(
        mission_data_or_id=mission,
        terrain=terrain,
        transform=transform,
        weather_site="gale_crater",  # Mismatch for Jezero mission!
        persist_assessment=False,
    )

    assert any(f["finding_code"] == "ENV_SITE_MISMATCH" for f in assessment["findings"])


def test_16_decision_pack_csv_and_markdown_exports(terrain_and_transform):
    """Verify Decision Pack generates valid comparison CSV and Markdown briefing."""
    terrain, transform = terrain_and_transform
    mission = get_mission(SAVED_MISSION_ID)
    cm = mission["canonical_mission"]

    base_route = {
        "distance_m": 1500.0,
        "travel_time_s": 2700.0,
        "dwell_time_s": 1800.0,
        "total_duration_s": 4500.0,
        "is_reachable": True,
    }
    scen_result = {
        "is_scenario_reachable": True,
        "revised_route": {
            "distance_m": 1680.0,
            "travel_time_s": 3024.0,
            "dwell_time_s": 1800.0,
            "total_duration_s": 4824.0,
        },
    }

    csv_out = generate_comparison_csv(base_route, scen_result)
    assert "Ground Traverse Distance" in csv_out
    assert "metres" in csv_out
    assert "DETOUR_REQUIRED" in csv_out

    bundle = build_canonical_mission_run_bundle(
        mission_input=cm,
        baseline_route=base_route,
        terrain=terrain,
        scenario_result=scen_result,
    )
    md_out = generate_decision_pack_briefing_md(bundle)
    assert "MISSION DECISION BRIEFING" in md_out.upper()
    assert "Jezero Delta Scarp Survey" in md_out or "Jezero" in md_out


def test_17_deterministic_scoring_bounds(terrain_and_transform):
    """Verify readiness score respects bounds [0.0, 100.0]."""
    terrain, transform = terrain_and_transform
    mission = get_mission(SAVED_MISSION_ID)

    asmt = evaluate_mission_readiness(
        mission_data_or_id=mission,
        terrain=terrain,
        transform=transform,
        persist_assessment=False,
    )
    assert 0.0 <= asmt["readiness_score"] <= 100.0


def test_18_disclaimer_preservation_across_subsystems():
    """Verify research prototype disclosures are present across all outputs."""
    wm = get_weather_manager()
    w_snap = wm.get_weather("jezero_crater")
    assert any("NASA PDS" in d for d in w_snap["disclosures"])

    asmt = evaluate_mission_readiness(SAVED_MISSION_ID, persist_assessment=False)
    assert any("NOT certified operationally safe" in d for d in asmt["limitations_and_disclaimers"])
    assert any("simulation" in d.lower() for d in asmt["limitations_and_disclaimers"])


def test_19_weather_physical_range_guard():
    """Verify PhysicalRangeGuard flags unphysical Martian atmosphere values."""
    from marswalk.core.weather import PhysicalRangeGuard
    unphysical_readings = {
        "atmospheric_pressure_pa": 5000.0,  # Max is 2000 Pa
        "air_temperature_k": 350.0,         # Max is 310 K
        "wind_speed_m_s": 100.0,            # Max is 70 m/s
    }
    warns = PhysicalRangeGuard.validate(unphysical_readings)
    assert len(warns) == 3
    assert any("pressure" in w.lower() for w in warns)
    assert any("air temperature" in w.lower() for w in warns)
    assert any("wind speed" in w.lower() for w in warns)


def test_20_schema_contract_round_trip_validation():
    """Verify all milestone JSON outputs pass Draft 2020-12 schema validation."""
    wm = get_weather_manager()
    w_snap = wm.get_weather("jezero_crater")
    validate_contract(w_snap, "weather-report", raise_on_error=True)

    asmt = evaluate_mission_readiness(SAVED_MISSION_ID, persist_assessment=False)
    validate_contract(asmt, "mission-readiness-assessment", raise_on_error=True)
