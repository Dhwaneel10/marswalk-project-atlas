"""
Milestone 9J — Automated API Contract & Invariant Verification Test Suite.
Validates end-to-end contract compliance across JSON Schema Draft 2020-12,
deterministic input fingerprinting, geometry invariants, safe zero-baseline deltas,
and structured error reporting across all MarsWalk 2.0 endpoints.
"""

import os
import json
import math
import pytest
import rasterio

from marswalk.core.terrain import load_and_process_terrain, TerrainGrid
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    plan_route,
)
from marswalk.api.service import (
    plan_route_api,
    gauntlet_api,
    scenario_comparison_api,
    scenario_sensitivity_api,
    export_briefing_api,
    APIError,
)
from marswalk.api.contracts import (
    SCHEMA_VERSION,
    TERRAIN_DATASET_ID,
    validate_contract,
    compute_input_fingerprint,
    calculate_safe_pct_delta,
    create_api_error_response,
    sanitize_for_json,
    build_mission_snapshot,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_TIFF = os.path.join(REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")
WAYPOINTS_JSON = os.path.join(REPO_ROOT, "data", "waypoints_jezero.json")


@pytest.fixture(scope="module")
def terrain_env():
    assert os.path.exists(PROCESSED_TIFF), f"Missing GeoTIFF: {PROCESSED_TIFF}"
    terrain = load_and_process_terrain(PROCESSED_TIFF)
    with rasterio.open(PROCESSED_TIFF) as src:
        transform = src.transform

    waypoints = []
    if os.path.exists(WAYPOINTS_JSON):
        from marswalk.data.ingest import query_elevation_at_lonlat
        with open(WAYPOINTS_JSON, "r", encoding="utf-8") as f:
            wp_data = json.load(f)
        for wp in wp_data.get("waypoints", []):
            try:
                elev, r, c = query_elevation_at_lonlat(PROCESSED_TIFF, wp["lon_deg"], wp["lat_deg"])
                waypoints.append(
                    ScienceWaypoint(
                        id=wp["id"],
                        name=wp["name"],
                        rc=(r, c),
                        priority_score=float(wp.get("priority_score", 0.0)),
                        geological_context=wp.get("geological_context", ""),
                        crism_signature=wp.get("crism_signature", ""),
                        pds_citation=wp.get("pds_citation", ""),
                    )
                )
            except Exception as e:
                print(f"[Warning] Failed loading waypoint {wp.get('id')}: {e}")

    return {
        "terrain": terrain,
        "transform": transform,
        "waypoints": waypoints,
    }


# ==============================================================================
# TEST 1: Valid Mission Request Schema Validation
# ==============================================================================
def test_01_valid_mission_request_schema():
    """Verify single-leg and multi-stop mission requests conform to mission-request.schema.json."""
    single_leg_payload = {
        "start": {"row": 178, "col": 48, "name": "Octavia Butler"},
        "goal": {"row": 136, "col": 91, "name": "Hawksbill Gap"},
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
        "speed_multiplier": 1.0,
    }
    is_valid, errs = validate_contract(single_leg_payload, "mission-request")
    assert is_valid, f"Single-leg payload failed schema validation: {errs}"

    multi_stop_payload = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "stops": [
            {"row": 153, "col": 123, "id": "three_forks", "priority_score": 75.0, "dwell_time_s": 900.0},
            {"row": 142, "col": 110, "id": "kodiak_butte", "priority_score": 80.0, "dwell_time_s": 1200.0},
        ],
        "profile": "balanced",
        "vehicle_mode": "robotic_rover",
        "mission_constraints": {"max_distance_m": 5000.0, "max_duration_s": 28800.0},
    }
    is_valid_multi, errs_multi = validate_contract(multi_stop_payload, "mission-request")
    assert is_valid_multi, f"Multi-stop payload failed schema validation: {errs_multi}"


# ==============================================================================
# TEST 2: Rejection of Unsupported Profiles
# ==============================================================================
def test_02_rejection_unsupported_profile(terrain_env):
    """Reject unknown profiles with HTTP 400 and ERR_UNSUPPORTED_PROFILE."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    payload = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "profile": "hyper_speed",
    }
    with pytest.raises(APIError) as exc_info:
        plan_route_api(payload, terrain, transform)
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "ERR_UNSUPPORTED_PROFILE"


# ==============================================================================
# TEST 3: Rejection of Unsupported Vehicle Modes
# ==============================================================================
def test_03_rejection_unsupported_vehicle_mode(terrain_env):
    """Reject unknown vehicle modes with HTTP 400 and ERR_UNSUPPORTED_VEHICLE_MODE."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    payload = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "vehicle_mode": "flying_drone",
    }
    with pytest.raises(APIError) as exc_info:
        plan_route_api(payload, terrain, transform)
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "ERR_UNSUPPORTED_VEHICLE_MODE"


# ==============================================================================
# TEST 4: Rejection of Out-of-Bounds Coordinates
# ==============================================================================
def test_04_rejection_endpoint_out_of_bounds(terrain_env):
    """Reject coordinates outside the 250x250 DTM grid with ERR_ENDPOINT_OUT_OF_BOUNDS."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    payload = {
        "start": {"row": -5, "col": 48},
        "goal": {"row": 136, "col": 91},
    }
    with pytest.raises(APIError) as exc_info:
        plan_route_api(payload, terrain, transform)
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "ERR_ENDPOINT_OUT_OF_BOUNDS"


# ==============================================================================
# TEST 5: Rejection of Impassable NoData Barrier Cells
# ==============================================================================
def test_05_rejection_nodata_barrier_cell(terrain_env):
    """Reject endpoints located on NoData or cliff hazard cells with HTTP 422 and ERR_NO_DATA_BARRIER."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]

    # Locate an invalid masked cell
    invalid_indices = terrain.invalid_mask.nonzero()
    if len(invalid_indices[0]) > 0:
        inv_r = int(invalid_indices[0][0])
        inv_c = int(invalid_indices[1][0])
        payload = {
            "start": {"row": inv_r, "col": inv_c},
            "goal": {"row": 136, "col": 91},
        }
        with pytest.raises(APIError) as exc_info:
            plan_route_api(payload, terrain, transform)
        assert exc_info.value.status_code == 422
        assert exc_info.value.error_code == "ERR_NO_DATA_BARRIER"


# ==============================================================================
# TEST 6: Rejection of Duplicate Stops and Identical Endpoints
# ==============================================================================
def test_06_rejection_duplicate_stops_and_identical_start_goal(terrain_env):
    """Reject start == goal and duplicate intermediate stop coordinates with ERR_DUPLICATE_STOPS."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]

    # Start == Goal
    payload_identical = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 178, "col": 48},
    }
    with pytest.raises(APIError) as exc_info:
        plan_route_api(payload_identical, terrain, transform)
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "ERR_DUPLICATE_STOPS"

    # Duplicate intermediate stops
    payload_dup_stops = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "stops": [
            {"row": 153, "col": 123, "id": "stop1"},
            {"row": 153, "col": 123, "id": "stop2"},
        ],
    }
    with pytest.raises(APIError) as exc_info_dup:
        plan_route_api(payload_dup_stops, terrain, transform)
    assert exc_info_dup.value.status_code == 400
    assert exc_info_dup.value.error_code == "ERR_DUPLICATE_STOPS"


# ==============================================================================
# TEST 7: Rejection of Exceeding Maximum 12 Stops
# ==============================================================================
def test_07_rejection_exceeding_max_12_stops(terrain_env):
    """Reject requests with more than 12 intermediate science stops."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    payload = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "stops": [{"row": 100 + i, "col": 100 + i, "id": f"s{i}"} for i in range(13)],
    }
    with pytest.raises(APIError) as exc_info:
        plan_route_api(payload, terrain, transform)
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "ERR_VALIDATION_FAILED"


# ==============================================================================
# TEST 8: Fingerprint Determinism
# ==============================================================================
def test_08_fingerprint_determinism():
    """Identical mission parameters must yield the exact same SHA-256 fingerprint."""
    mission_a = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "stops": [
            {"row": 153, "col": 123, "id": "three_forks", "priority_score": 75.0, "dwell_time_s": 900.0},
        ],
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
        "speed_multiplier": 1.0,
    }
    fp1 = compute_input_fingerprint(mission_a)
    fp2 = compute_input_fingerprint(mission_a)
    assert fp1 == fp2
    assert len(fp1) == 64


# ==============================================================================
# TEST 9: Fingerprint Sensitivity to Parameter Changes
# ==============================================================================
def test_09_fingerprint_sensitivity_to_inputs():
    """Altering any result-affecting input parameter must alter the fingerprint."""
    base_mission = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
        "speed_multiplier": 1.0,
    }
    base_fp = compute_input_fingerprint(base_mission)

    # Change profile
    m_profile = dict(base_mission, profile="balanced")
    assert compute_input_fingerprint(m_profile) != base_fp

    # Change vehicle mode
    m_mode = dict(base_mission, vehicle_mode="robotic_rover")
    assert compute_input_fingerprint(m_mode) != base_fp

    # Change start coordinate
    m_start = dict(base_mission, start={"row": 179, "col": 48})
    assert compute_input_fingerprint(m_start) != base_fp

    # Change speed multiplier
    m_speed = dict(base_mission, speed_multiplier=0.5)
    assert compute_input_fingerprint(m_speed) != base_fp


# ==============================================================================
# TEST 10: Fingerprint Excludes Ephemeral Fields
# ==============================================================================
def test_10_fingerprint_excludes_ephemeral_fields():
    """Adding client request IDs, render options, or timestamps does not change the fingerprint."""
    base_mission = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
    }
    base_fp = compute_input_fingerprint(base_mission)

    with_ephemeral = dict(
        base_mission,
        timestamp=1729238400,
        client_request_id="req_987654321",
        render_options={"color": "red", "show_markers": True},
    )
    ephemeral_fp = compute_input_fingerprint(with_ephemeral)
    assert base_fp == ephemeral_fp


# ==============================================================================
# TEST 11: Route Geometry Connectivity Invariant
# ==============================================================================
def test_11_route_geometry_connectivity_invariant(terrain_env):
    """Every pair of consecutive path cells must be 8-connected neighbors."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    payload = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "profile": "conservative",
    }
    res = plan_route_api(payload, terrain, transform)
    path = res["path_rc"]
    assert len(path) >= 2

    for i in range(len(path) - 1):
        r1, c1 = path[i]
        r2, c2 = path[i + 1]
        step_dr = abs(r1 - r2)
        step_dc = abs(c1 - c2)
        assert max(step_dr, step_dc) == 1, f"Disconnected step at index {i}: ({r1},{c1}) -> ({r2},{c2})"
        assert step_dr + step_dc > 0, f"Zero-step loop at index {i}: ({r1},{c1})"


# ==============================================================================
# TEST 12: Route Start and Goal Matching Invariant
# ==============================================================================
def test_12_route_start_and_goal_matching_invariant(terrain_env):
    """The first cell of path_rc must match start and the last cell must match goal."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    start = (178, 48)
    goal = (136, 91)
    payload = {
        "start": {"row": start[0], "col": start[1]},
        "goal": {"row": goal[0], "col": goal[1]},
        "profile": "conservative",
    }
    res = plan_route_api(payload, terrain, transform)
    path = res["path_rc"]
    assert tuple(path[0]) == start
    assert tuple(path[-1]) == goal


# ==============================================================================
# TEST 13: Route Never Traverses Hazard Barriers
# ==============================================================================
def test_13_route_never_traverses_hazard_barriers(terrain_env):
    """Path must never step on terrain cells marked invalid in invalid_mask."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    payload = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "profile": "conservative",
    }
    res = plan_route_api(payload, terrain, transform)
    for r, c in res["path_rc"]:
        assert not terrain.invalid_mask[r, c], f"Path traversed invalid hazard cell ({r}, {c})"


# ==============================================================================
# TEST 14: Metric Integrity Invariants
# ==============================================================================
def test_14_metric_integrity_invariants(terrain_env):
    """Computed metrics must obey physical bounds (positive distance, slope in [0, 90], positive time)."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    payload = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "profile": "conservative",
    }
    res = plan_route_api(payload, terrain, transform)
    metrics = res["route_metrics"]
    assert metrics["ground_distance_m"] > 0.0
    assert metrics["terrain_cost_flat_m"] >= metrics["ground_distance_m"]
    assert metrics["active_traverse_time_s"] > 0.0
    assert metrics["cumulative_climb_m"] >= 0.0
    assert 0.0 <= metrics["max_slope_deg"] <= 90.0
    assert metrics["science_score"] >= 0.0


# ==============================================================================
# TEST 15: Safe Zero-Baseline Percentage Deltas
# ==============================================================================
def test_15_safe_zero_baseline_percentage_deltas():
    """Zero-baseline or unreachable missions must return None (null), never 0.0% or NaN."""
    # Zero baseline distance
    assert calculate_safe_pct_delta(100.0, 0.0) is None
    # Negative baseline
    assert calculate_safe_pct_delta(100.0, -50.0) is None
    # Unreachable (None input)
    assert calculate_safe_pct_delta(None, 100.0) is None
    assert calculate_safe_pct_delta(100.0, None) is None
    # NaN inputs
    assert calculate_safe_pct_delta(float("nan"), 100.0) is None
    assert calculate_safe_pct_delta(100.0, float("nan")) is None
    # Valid delta calculation
    assert calculate_safe_pct_delta(125.0, 100.0) == 25.0
    assert calculate_safe_pct_delta(75.0, 100.0) == -25.0


# ==============================================================================
# TEST 16: Live /api/plan_route Schema Validation
# ==============================================================================
def test_16_plan_route_live_response_schema_validation(terrain_env):
    """POST /api/plan_route response must strictly validate against route-result.schema.json."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    waypoints = terrain_env["waypoints"]
    payload = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "stops": [
            {"row": waypoints[0].rc[0], "col": waypoints[0].rc[1], "id": waypoints[0].id, "priority_score": 75.0},
        ],
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
    }
    res = plan_route_api(payload, terrain, transform, waypoints)
    is_valid, errors = validate_contract(res, "route-result")
    assert is_valid, f"Route result failed schema validation: {errors}"
    assert res["schema_version"] == "1.0.0"
    assert len(res["input_fingerprint"]) == 64


# ==============================================================================
# TEST 17: Live /api/scenario_comparison Schema Validation
# ==============================================================================
def test_17_scenario_comparison_live_response_schema_validation(terrain_env):
    """POST /api/scenario_comparison response must strictly validate against scenario-comparison-response.schema.json."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    waypoints = terrain_env["waypoints"]
    payload = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
        "scenario_ids": ["scen_corridor_rockfall", "scen_unstable_sand"],
    }
    res = scenario_comparison_api(payload, terrain, transform, waypoints)
    is_valid, errors = validate_contract(res, "scenario-comparison-response")
    assert is_valid, f"Scenario comparison failed schema validation: {errors}"
    assert res["overall_status"] in ["all_feasible", "partially_blocked", "all_blocked", "calculation_failed"]
    assert len(res["scenario_results"]) == 2


# ==============================================================================
# TEST 18: Live /api/scenario_sensitivity Schema Validation
# ==============================================================================
def test_18_scenario_sensitivity_live_response_schema_validation(terrain_env):
    """POST /api/scenario_sensitivity response must strictly validate against scenario-sensitivity-response.schema.json."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    waypoints = terrain_env["waypoints"]
    payload = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "scenario_id": "scen_corridor_rockfall",
        "parameter_name": "radius_m",
        "parameter_values": [30.0, 60.0, 90.0],
    }
    res = scenario_sensitivity_api(payload, terrain, transform, waypoints)
    is_valid, errors = validate_contract(res, "scenario-sensitivity-response")
    assert is_valid, f"Scenario sensitivity failed schema validation: {errors}"
    assert res["num_evaluations"] == 3
    assert res["overall_status"] in ["all_feasible", "transition_to_blocked", "all_blocked", "calculation_failed"]


# ==============================================================================
# TEST 19: Live /api/export_briefing Schema Validation
# ==============================================================================
def test_19_export_briefing_live_response_schema_validation(terrain_env):
    """POST /api/export_briefing json_export bundle must strictly validate against mission-briefing-export.schema.json."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    payload = {
        "start": {"row": 178, "col": 48},
        "goal": {"row": 136, "col": 91},
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
    }
    route_res = plan_route_api(payload, terrain, transform)
    export_payload = {
        "baseline_route": route_res,
        "mission_snapshot": route_res["mission_snapshot"],
    }
    res = export_briefing_api(export_payload, terrain, transform)
    json_export = res["json_export"]
    is_valid, errors = validate_contract(json_export, "mission-briefing-export")
    assert is_valid, f"Briefing export failed schema validation: {errors}"
    assert res["markdown_briefing"].startswith("# MARSWALK 2.0")


# ==============================================================================
# TEST 20: Standardized API Error Response Schema Validation
# ==============================================================================
def test_20_structured_api_error_responses_schema_validation():
    """All structured error responses (400, 404, 422, 503) must validate against api-error.schema.json."""
    error_cases = [
        ("ERR_MALFORMED_JSON", "Malformed request syntax", 400),
        ("ERR_NOT_FOUND", "Endpoint not found: /api/unknown", 404),
        ("ERR_NO_DATA_BARRIER", "Pixel falls on NoData sentinel", 422),
        ("ERR_TERRAIN_UNAVAILABLE", "Terrain engine not initialized", 503),
    ]

    for code, msg, status in error_cases:
        err_obj = create_api_error_response(
            error_code=code,
            message=msg,
            status_code=status,
            details=[{"field": "input", "issue": "Contract check"}],
            is_retryable=(status == 503),
        )
        is_valid, errors = validate_contract(err_obj, "api-error")
        assert is_valid, f"Error object for {code} failed schema validation: {errors}"
        # Verify backward compatibility
        assert err_obj["error"] == msg
        assert err_obj["status"] == status
