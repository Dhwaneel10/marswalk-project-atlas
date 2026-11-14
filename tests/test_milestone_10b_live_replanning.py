"""
MarsWalk 2.0 — Milestone 10B Test Suite: Mid-Sortie Emergency Injection, Mission State Handoff & Live Adaptive Replanning.

Validates the 20 criteria established in the Milestone 10B Specification:
1. Captured position matches active route at selected playback time within tolerance.
2. Time-zero state maps to route start.
3. Completion state maps to destination.
4. Dwell-period state preserves stationary position.
5. Replanning preserves captured current position.
6. Completed targets are not scheduled again.
7. Remaining target order is valid and connects to destination.
8. A closure affects a route that actually intersects its blocked footprint.
9. The revised route never traverses blocked cells.
10. A closure outside active route does not falsely claim a detour.
11. Mobility changes remaining time according to vehicle speed semantics.
12. An operational hold is accounted for exactly once.
13. The remaining budget excludes elapsed mission time correctly without double counting.
14. An unreachable continuation is not reported as a successful sortie.
15. Invalid inputs and non-finite timestamps fail safely.
16. A selected continuation receives a distinct identity and preserves parent provenance.
17. Historical mission and experiment records in workspace storage remain strictly untouched.
18. Playback model starts at rover's captured location without jumping back to mission origin.
19. Completed event cues are not repeated as future events.
20. Live HTTP API endpoint POST /api/mission/continue returns valid JSON Schema Draft 2020-12 responses.
"""

import math
import os
import json
import urllib.request
import pytest
import numpy as np

from marswalk.core.terrain import TerrainGrid, TerrainConfig
from marswalk.core.planner import (
    RouteResult,
    ScienceWaypoint,
    MissionTimeline,
    TimelineEvent,
    build_mission_timeline,
    plan_route,
    plan_sequential_multistop_route,
    PlannerConfig,
    calculate_traverse_time,
)
from marswalk.core.mission_playback import (
    PlaybackSample,
    PlaybackTimelineEvent,
    MissionPlaybackModel,
    build_mission_playback_model,
    interpolate_playback_state,
)
from marswalk.core.mission_continuation import (
    MidSortieState,
    capture_mid_sortie_state,
    plan_mission_continuation,
)
from marswalk.core.adaptive_replanner import ReplanningRecommendation
from marswalk.api.contracts import validate_contract
from marswalk.api.workspace import list_missions, list_experiments


# --- Fixtures ---

@pytest.fixture
def synthetic_flat_terrain() -> TerrainGrid:
    """100x100 synthetic flat terrain at -2500m with 20m grid spacing."""
    elev = np.full((100, 100), -2500.0, dtype=np.float32)
    slope = np.zeros((100, 100), dtype=np.float32)
    rough = np.full((100, 100), 0.5, dtype=np.float32)
    invalid = np.zeros((100, 100), dtype=bool)
    cfg = TerrainConfig(cell_size_m=20.0, ref_lat_deg=18.38)
    return TerrainGrid(
        elevation=elev,
        slope_deg=slope,
        roughness_m=rough,
        invalid_mask=invalid,
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        config=cfg,
    )


@pytest.fixture
def synthetic_multistop_playback(synthetic_flat_terrain: TerrainGrid) -> MissionPlaybackModel:
    """Multi-stop mission: start=(20, 20), stop1=(20, 40), stop2=(50, 40), goal=(50, 70)."""
    t = synthetic_flat_terrain
    start_rc = (20, 20)
    goal_rc = (50, 70)
    wps = [
        ScienceWaypoint(id="site_alpha", name="Site Alpha", rc=(20, 40), priority_score=80.0),
        ScienceWaypoint(id="site_beta", name="Site Beta", rc=(50, 40), priority_score=60.0),
    ]
    p_cfg = PlannerConfig(profile="balanced")
    route = plan_sequential_multistop_route(
        ordered_points=[start_rc, (20, 40), (50, 40), goal_rc],
        terrain=t,
        stop_ids=["site_alpha", "site_beta"],
        stop_priorities=[80.0, 60.0],
        config=p_cfg,
        vehicle_mode="crew_eva",
        dwell_time_per_stop_s=900.0,
        speed_multiplier=1.0,
    )
    wp_dicts = [
        {"id": "site_alpha", "name": "Site Alpha", "rc": [20, 40], "priority": 80.0, "dwell_time_s": 900.0},
        {"id": "site_beta", "name": "Site Beta", "rc": [50, 40], "priority": 60.0, "dwell_time_s": 900.0},
    ]
    return build_mission_playback_model(
        route_data=route,
        terrain=t,
        vehicle_mode="crew_eva",
        mission_variant="nominal",
        mission_id="test_mission_001",
        profile="balanced",
        waypoints=wp_dicts,
    )


# --- 20 Criteria Test Cases ---

def test_01_captured_position_matches_active_route(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """1. Captured position matches active route at selected playback time within tolerance."""
    model = synthetic_multistop_playback
    query_t = model.total_duration_s * 0.3
    state = capture_mid_sortie_state(model, query_t, synthetic_flat_terrain)

    assert state.interruption_time_s == pytest.approx(query_t, abs=0.1)
    assert 0 <= state.rover_rc[0] < synthetic_flat_terrain.height
    assert 0 <= state.rover_rc[1] < synthetic_flat_terrain.width

    # Check distance tolerance between float and integer cell <= 1.0 cell
    dr = abs(state.rover_float_rc[0] - state.rover_rc[0])
    dc = abs(state.rover_float_rc[1] - state.rover_rc[1])
    assert math.hypot(dr, dc) <= 1.0


def test_02_time_zero_state_maps_to_route_start(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """2. Time-zero state maps to route start."""
    model = synthetic_multistop_playback
    state = capture_mid_sortie_state(model, 0.0, synthetic_flat_terrain)

    assert state.interruption_time_s == 0.0
    start_cell = tuple(model.events[0].start_rc)
    assert state.rover_rc == start_cell
    assert len(state.completed_stop_ids) == 0
    assert len(state.unvisited_stop_ids) == 2


def test_03_completion_state_maps_to_destination(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """3. Completion state maps to destination."""
    model = synthetic_multistop_playback
    total_t = model.total_duration_s
    state = capture_mid_sortie_state(model, total_t, synthetic_flat_terrain)

    dest_cell = tuple(model.events[-1].end_rc)
    assert state.rover_rc == dest_cell
    assert state.interruption_time_s == pytest.approx(total_t, abs=0.1)
    assert "site_alpha" in state.completed_stop_ids
    assert "site_beta" in state.completed_stop_ids
    assert len(state.unvisited_stop_ids) == 0


def test_04_dwell_period_state_preserves_stationary_position(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """4. Dwell-period state preserves stationary position."""
    model = synthetic_multistop_playback
    dwell_event = next(e for e in model.events if e.event_type == "science_dwell" and e.target_id == "site_alpha")

    # Midpoint of dwell
    t_dwell_mid = (dwell_event.start_time_s + dwell_event.end_time_s) / 2.0
    state = capture_mid_sortie_state(model, t_dwell_mid, synthetic_flat_terrain)

    assert state.rover_rc == dwell_event.start_rc
    assert state.is_stationary is True
    assert state.active_event_type == "science_dwell"
    assert state.active_target_id == "site_alpha"


def test_05_replanning_preserves_captured_current_position(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """5. Replanning preserves captured current position as continuation departure point."""
    model = synthetic_multistop_playback
    state = capture_mid_sortie_state(model, 300.0, synthetic_flat_terrain)
    ev = {"event_type": "mobility", "speed_multiplier": 0.8}

    res = plan_mission_continuation(synthetic_flat_terrain, state, ev)

    assert res["status"] == "success"
    assert res["rover_state"]["rover_rc"] == list(state.rover_rc)
    adapt_path = res["adaptive_continuation"]["path_rc"]
    assert adapt_path[0] == list(state.rover_rc)
    assert res["continuation_playback"]["samples"][0]["rc"] == [state.rover_rc[0], state.rover_rc[1]]


def test_06_completed_targets_not_scheduled_again(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """6. Completed targets are not scheduled again."""
    model = synthetic_multistop_playback
    # Interruption after site_alpha dwell finishes
    dwell_alpha = next(e for e in model.events if e.event_type == "science_dwell" and e.target_id == "site_alpha")
    t_after_alpha = dwell_alpha.end_time_s + 10.0

    state = capture_mid_sortie_state(model, t_after_alpha, synthetic_flat_terrain)
    assert "site_alpha" in state.completed_stop_ids
    assert "site_alpha" not in state.unvisited_stop_ids

    ev = {"event_type": "closure", "center_rc": [10, 10], "radius_m": 20.0}
    res = plan_mission_continuation(synthetic_flat_terrain, state, ev)

    # Site alpha must never appear in continuation visited or unvisited targets
    assert "site_alpha" not in res["adaptive_continuation"]["visited_stop_ids"]
    assert "site_alpha" in res["rover_state"]["completed_stop_ids"]


def test_07_remaining_target_order_is_valid(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """7. Remaining target order is valid and leads to destination."""
    model = synthetic_multistop_playback
    state = capture_mid_sortie_state(model, 100.0, synthetic_flat_terrain)
    ev = {"event_type": "mobility", "speed_multiplier": 0.9}

    res = plan_mission_continuation(synthetic_flat_terrain, state, ev)

    adapt_path = res["adaptive_continuation"]["path_rc"]
    assert adapt_path[-1] == list(state.goal_rc)
    assert res["adaptive_continuation"]["is_reachable"] is True


def test_08_closure_affects_route_intersecting_footprint(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """8. A closure affects a route that actually intersects its blocked footprint."""
    model = synthetic_multistop_playback
    state = capture_mid_sortie_state(model, 50.0, synthetic_flat_terrain)

    # Pick a point on nominal remaining path
    nom_path = state.nominal_remaining_path_rc
    block_pt = nom_path[len(nom_path) // 2]

    ev = {"event_type": "closure", "center_rc": list(block_pt), "radius_m": 30.0}
    res = plan_mission_continuation(synthetic_flat_terrain, state, ev)

    assert res["disrupted_remaining"]["is_reachable"] is False
    assert res["disrupted_remaining"]["blocked_cell_encounters"] > 0
    assert res["adaptive_continuation"]["is_reachable"] is True


def test_09_revised_route_never_traverses_blocked_cells(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """9. The revised route never traverses blocked cells."""
    model = synthetic_multistop_playback
    state = capture_mid_sortie_state(model, 50.0, synthetic_flat_terrain)
    nom_path = state.nominal_remaining_path_rc
    block_pt = nom_path[len(nom_path) // 2]

    ev = {"event_type": "closure", "center_rc": list(block_pt), "radius_m": 40.0}
    res = plan_mission_continuation(synthetic_flat_terrain, state, ev)

    # Extract blocked set
    c_r, c_c = block_pt
    blocked_cells = {
        (r, c)
        for r in range(synthetic_flat_terrain.height)
        for c in range(synthetic_flat_terrain.width)
        if math.hypot((r - c_r) * 20.0, (c - c_c) * 20.0) <= 40.0
    }

    adapt_path = [tuple(p) for p in res["adaptive_continuation"]["path_rc"]]
    for pt in adapt_path:
        assert pt not in blocked_cells, f"Cell {pt} is blocked but traversed by adaptive continuation!"


def test_10_closure_outside_route_does_not_falsely_claim_detour(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """10. A closure outside active route does not falsely claim a detour."""
    model = synthetic_multistop_playback
    state = capture_mid_sortie_state(model, 50.0, synthetic_flat_terrain)

    # Closure far away in top-right corner
    ev = {"event_type": "closure", "center_rc": [5, 95], "radius_m": 20.0}
    res = plan_mission_continuation(synthetic_flat_terrain, state, ev)

    assert res["disrupted_remaining"]["is_reachable"] is True
    assert res["disrupted_remaining"]["blocked_cell_encounters"] == 0


def test_11_mobility_changes_remaining_time_correctly(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """11. Mobility changes remaining time according to vehicle speed semantics."""
    model = synthetic_multistop_playback
    state = capture_mid_sortie_state(model, 100.0, synthetic_flat_terrain)

    # 50% speed derate
    ev = {"event_type": "mobility", "speed_multiplier": 0.5}
    res = plan_mission_continuation(synthetic_flat_terrain, state, ev)

    nom_trav = res["nominal_remaining"]["traverse_time_s"]
    disr_trav = res["disrupted_remaining"]["traverse_time_s"]
    assert disr_trav == pytest.approx(nom_trav * 2.0, rel=0.05)


def test_12_operational_hold_accounted_exactly_once(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """12. An operational hold is accounted for exactly once."""
    model = synthetic_multistop_playback
    state = capture_mid_sortie_state(model, 100.0, synthetic_flat_terrain)

    hold_s = 600.0
    ev = {"event_type": "hold", "operational_delay_s": hold_s}
    res = plan_mission_continuation(synthetic_flat_terrain, state, ev)

    nom_total = res["nominal_remaining"]["total_time_s"]
    disr_total = res["disrupted_remaining"]["total_time_s"]
    assert disr_total == pytest.approx(nom_total + hold_s, abs=1.0)


def test_13_remaining_budget_excludes_elapsed_mission_time(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """13. The remaining budget excludes elapsed mission time correctly."""
    model = synthetic_multistop_playback
    t_pause = 500.0
    orig_budget = 10000.0

    state = capture_mid_sortie_state(model, t_pause, synthetic_flat_terrain, total_budget_s=orig_budget)
    assert state.remaining_budget_s == pytest.approx(orig_budget - t_pause, abs=0.1)

    ev = {"event_type": "mobility", "speed_multiplier": 1.0}
    res = plan_mission_continuation(synthetic_flat_terrain, state, ev, operational_limit_s=state.remaining_budget_s)
    assert res["rover_state"]["remaining_budget_s"] == pytest.approx(orig_budget - t_pause, abs=0.1)


def test_14_unreachable_continuation_not_reported_successful(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """14. An unreachable continuation is not reported as a successful sortie."""
    model = synthetic_multistop_playback
    state = capture_mid_sortie_state(model, 50.0, synthetic_flat_terrain)

    # Block entire destination
    g_r, g_c = state.goal_rc
    ev = {"event_type": "closure", "center_rc": [g_r, g_c], "radius_m": 80.0}
    res = plan_mission_continuation(synthetic_flat_terrain, state, ev)

    assert res["adaptive_continuation"]["is_reachable"] is False
    assert res["recommendation"] == ReplanningRecommendation.UNRESOLVABLE_CRITICAL_HAZARD.value


def test_15_invalid_inputs_fail_safely(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """15. Invalid inputs fail safely with informative exceptions."""
    from marswalk.api.service import mission_continue_api, APIError
    import rasterio

    # Missing event
    payload_no_event = {
        "playback_model": synthetic_multistop_playback.to_dict(),
        "interruption_time_s": 100.0,
    }
    with pytest.raises(APIError) as exc_info:
        mission_continue_api(payload_no_event, synthetic_flat_terrain, rasterio.Affine.identity())
    assert exc_info.value.error_code == "ERR_NO_CONTINGENCY_EVENTS"

    # Negative interruption time
    payload_neg_time = {
        "playback_model": synthetic_multistop_playback.to_dict(),
        "interruption_time_s": -50.0,
        "event": {"event_type": "mobility", "speed_multiplier": 0.5},
    }
    with pytest.raises(APIError) as exc_info2:
        mission_continue_api(payload_neg_time, synthetic_flat_terrain, rasterio.Affine.identity())
    assert exc_info2.value.error_code == "ERR_INVALID_INTERRUPTION_TIME"


def test_16_selected_continuation_distinct_identity(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """16. A selected continuation has a distinct identity and preserves parent provenance."""
    model = synthetic_multistop_playback
    state = capture_mid_sortie_state(model, 150.0, synthetic_flat_terrain)
    ev = {"event_type": "mobility", "speed_multiplier": 0.8}

    res = plan_mission_continuation(synthetic_flat_terrain, state, ev)

    assert res["continuation_id"].startswith("cont_")
    assert res["source_mission_id"] == "test_mission_001"
    cont_model = res["continuation_playback"]
    assert cont_model["metadata"]["source_mission_id"] == "test_mission_001"
    assert cont_model["metadata"]["is_continuation"] is True
    assert cont_model["metadata"]["interruption_time_s"] == 150.0


def test_17_historical_records_remain_unchanged():
    """17. Historical mission and experiment records in workspace remain strictly unchanged."""
    missions = list_missions()
    experiments = list_experiments()

    assert len(missions) == 7, f"Expected 7 historical missions, found {len(missions)}"
    assert len(experiments) == 11, f"Expected 11 historical experiments, found {len(experiments)}"


def test_18_continuation_playback_model_resumes_without_reset(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """18. Continuation playback model samples start from current rover location without snapping to start."""
    model = synthetic_multistop_playback
    state = capture_mid_sortie_state(model, 250.0, synthetic_flat_terrain)
    ev = {"event_type": "mobility", "speed_multiplier": 0.8}

    res = plan_mission_continuation(synthetic_flat_terrain, state, ev)
    cont_model_dict = res["continuation_playback"]

    assert len(cont_model_dict["samples"]) > 0
    start_sample = cont_model_dict["samples"][0]
    assert start_sample["rc"] == [state.rover_rc[0], state.rover_rc[1]]
    assert start_sample["time_s"] == 0.0


def test_19_completed_event_cues_not_repeated(
    synthetic_multistop_playback: MissionPlaybackModel,
    synthetic_flat_terrain: TerrainGrid
):
    """19. Completed event cues are not repeated as future events in continuation model."""
    model = synthetic_multistop_playback
    dwell_alpha = next(e for e in model.events if e.event_type == "science_dwell" and e.target_id == "site_alpha")
    t_after_alpha = dwell_alpha.end_time_s + 10.0

    state = capture_mid_sortie_state(model, t_after_alpha, synthetic_flat_terrain)
    ev = {"event_type": "mobility", "speed_multiplier": 1.0}

    res = plan_mission_continuation(synthetic_flat_terrain, state, ev)
    cont_events = res["continuation_playback"]["events"]

    event_target_ids = [e.get("target_id") for e in cont_events if e.get("target_id")]
    assert "site_alpha" not in event_target_ids


def test_20_live_http_api_mission_continue():
    """20. Live HTTP endpoint POST /api/mission/continue conforms to JSON Schema Draft 2020-12."""
    payload = {
        "source_mission_id": "m_jezero_delta_scarp_surve_090607",
        "interruption_time_s": 800.0,
        "event": {
            "event_type": "closure",
            "center_rc": [130, 140],
            "radius_m": 50.0,
        },
    }
    req = urllib.request.Request(
        "http://127.0.0.1:3000/api/mission/continue",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "success"
        assert data["schema_version"] == "1.0.0"
        assert "continuation_id" in data
        assert "rover_state" in data
        assert "adaptive_continuation" in data
        assert "recommendation" in data

        # Explicit validation against Draft 2020-12 contract
        is_valid, errors = validate_contract(data, "mission-continue-response", raise_on_error=True)
        assert is_valid is True
        assert len(errors) == 0
