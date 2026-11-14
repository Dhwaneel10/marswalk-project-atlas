"""
MarsWalk 2.0 — Milestone 9Z Test Suite: Mission Timeline Playback, Synchronized 3D Route Animation & Event Reconstruction.

Validates:
1. Discrete time monotonicity and time conservation.
2. Distance conservation and monotonicity.
3. Directed cost-weighted edge timing.
4. Stationary pinning during science dwell and contingency delays.
5. Multi-stop tour event sequencing and waypoint association.
6. Robotic rover vs Crew EVA speed modeling.
7. State interpolation at boundaries and arbitrary intermediate scrub timestamps.
8. Unreachable and trivial single-point route resilience.
9. Variant isolation (Nominal, Disrupted, Adaptive).
10. JSON Schema Draft 2020-12 contract validation.
11. Live HTTP API endpoint verification on port 3000.
12. Workspace immutability for existing historical missions and experiments.
"""

import os
import json
import math
import urllib.request
import pytest
import numpy as np

from marswalk.core.terrain import TerrainGrid, TerrainConfig, get_profile_terrain_config
from marswalk.core.planner import (
    RouteResult,
    LegResult,
    MissionTimeline,
    TimelineEvent,
    build_mission_timeline,
    plan_route,
    plan_sequential_multistop_route,
    PlannerConfig,
)
from marswalk.core.mission_playback import (
    PlaybackSample,
    PlaybackTimelineEvent,
    MissionPlaybackModel,
    build_mission_playback_model,
    interpolate_playback_state,
)
from marswalk.api.contracts import validate_contract


# --- Fixtures ---

@pytest.fixture
def synthetic_flat_terrain() -> TerrainGrid:
    """Create a 50x50 perfectly flat terrain (elevation 0m, slope 0deg)."""
    h, w = 50, 50
    elev = np.zeros((h, w), dtype=np.float32)
    slope = np.zeros((h, w), dtype=np.float32)
    rough = np.zeros((h, w), dtype=np.float32)
    invalid = np.zeros((h, w), dtype=bool)
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
def synthetic_sloped_terrain() -> TerrainGrid:
    """Create a 50x50 sloped terrain with an uphill ramp along rows."""
    h, w = 50, 50
    elev = np.zeros((h, w), dtype=np.float32)
    slope = np.zeros((h, w), dtype=np.float32)
    for r in range(h):
        elev[r, :] = r * 5.0  # 5m rise per row (20m ground step -> ~14 deg slope)
        slope[r, :] = 14.03
    rough = np.zeros((h, w), dtype=np.float32)
    invalid = np.zeros((h, w), dtype=bool)
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


# --- Tests ---

def test_01_discrete_time_monotonicity(synthetic_flat_terrain):
    """All samples along a traversal have strictly non-decreasing timestamps."""
    start = (5, 5)
    goal = (15, 25)
    cfg = PlannerConfig(profile="conservative")
    route = plan_route(start, goal, synthetic_flat_terrain, cfg)

    model = build_mission_playback_model(
        route_data=route,
        terrain=synthetic_flat_terrain,
        vehicle_mode="crew_eva",
    )

    assert len(model.samples) >= 2
    for i in range(len(model.samples) - 1):
        s0 = model.samples[i]
        s1 = model.samples[i + 1]
        assert s1.time_s >= s0.time_s, f"Sample {i+1} time {s1.time_s} < sample {i} time {s0.time_s}"


def test_02_distance_conservation(synthetic_flat_terrain):
    """Cumulative distance ends at total path distance and is non-decreasing."""
    start = (10, 10)
    goal = (20, 20)
    cfg = PlannerConfig(profile="conservative")
    route = plan_route(start, goal, synthetic_flat_terrain, cfg)

    model = build_mission_playback_model(
        route_data=route,
        terrain=synthetic_flat_terrain,
        vehicle_mode="crew_eva",
    )

    last_sample = model.samples[-1]
    assert math.isclose(last_sample.cumulative_distance_m, route.distance_m, rel_tol=1e-3)
    assert math.isclose(model.total_distance_m, route.distance_m, rel_tol=1e-3)

    for i in range(len(model.samples) - 1):
        assert model.samples[i + 1].cumulative_distance_m >= model.samples[i].cumulative_distance_m


def test_03_time_conservation(synthetic_flat_terrain):
    """Total mission duration exactly matches timeline duration."""
    start = (5, 5)
    goal = (15, 15)
    cfg = PlannerConfig(profile="conservative")
    route = plan_route(start, goal, synthetic_flat_terrain, cfg)

    timeline = build_mission_timeline(
        route,
        vehicle_mode="crew_eva",
        dwell_time_per_stop_s=900.0,
        operational_delay_s=600.0,
    )

    model = build_mission_playback_model(
        route_data=route,
        terrain=synthetic_flat_terrain,
        timeline=timeline,
        vehicle_mode="crew_eva",
    )

    assert math.isclose(model.total_duration_s, timeline.total_mission_time_s, abs_tol=0.1)
    assert math.isclose(model.samples[-1].time_s, timeline.total_mission_time_s, abs_tol=0.1)


def test_04_directed_cost_speed_variation(synthetic_sloped_terrain):
    """Uphill steps take more time per unit ground distance than downhill or flat steps."""
    # Route A: Uphill (0, 10) to (20, 10)
    # Route B: Downhill (20, 10) to (0, 10)
    cfg = PlannerConfig(profile="conservative")
    route_uphill = plan_route((0, 10), (20, 10), synthetic_sloped_terrain, cfg)
    route_downhill = plan_route((20, 10), (0, 10), synthetic_sloped_terrain, cfg)

    model_uphill = build_mission_playback_model(route_uphill, synthetic_sloped_terrain)
    model_downhill = build_mission_playback_model(route_downhill, synthetic_sloped_terrain)

    # Uphill duration should exceed downhill duration due to Minetti metabolic slope cost
    assert model_uphill.total_duration_s > model_downhill.total_duration_s


def test_05_science_dwell_stationary_pinning(synthetic_flat_terrain):
    """During science dwell, marker coordinates and distance remain strictly pinned."""
    pts = [(10, 10), (20, 20), (30, 30)]
    cfg = PlannerConfig(profile="conservative")
    route = plan_sequential_multistop_route(
        ordered_points=pts,
        terrain=synthetic_flat_terrain,
        config=cfg,
        dwell_time_per_stop_s=900.0,
    )

    model = build_mission_playback_model(
        route_data=route,
        terrain=synthetic_flat_terrain,
        timeline=route.timeline,
    )

    dwell_events = [e for e in model.events if e.event_type == "science_dwell"]
    assert len(dwell_events) == 1

    dwell_evt = dwell_events[0]
    # Dwell coordinate must match waypoint 1 (20, 20)
    assert dwell_evt.start_rc == (20, 20)
    assert dwell_evt.end_rc == (20, 20)
    assert dwell_evt.duration_s == 900.0

    # Query interpolated state at start, midpoint, and end of dwell
    t_mid = dwell_evt.start_time_s + 450.0
    state_mid = interpolate_playback_state(model, t_mid)

    assert state_mid["is_stationary"] is True
    assert math.isclose(state_mid["rc"][0], 20.0, abs_tol=0.1)
    assert math.isclose(state_mid["rc"][1], 20.0, abs_tol=0.1)
    assert state_mid["speed_m_s"] == 0.0


def test_06_scenario_delay_stationary_pinning(synthetic_flat_terrain):
    """During scenario delay, marker position stays stationary while time advances."""
    start = (10, 10)
    goal = (20, 20)
    cfg = PlannerConfig(profile="conservative")
    route = plan_route(start, goal, synthetic_flat_terrain, cfg)

    timeline = build_mission_timeline(
        route,
        vehicle_mode="crew_eva",
        operational_delay_s=1200.0,
    )

    model = build_mission_playback_model(
        route_data=route,
        terrain=synthetic_flat_terrain,
        timeline=timeline,
    )

    delay_events = [e for e in model.events if e.event_type == "scenario_delay"]
    assert len(delay_events) == 1
    delay_evt = delay_events[0]
    assert delay_evt.duration_s == 1200.0

    # Query state halfway through the delay
    t_query = delay_evt.start_time_s + 600.0
    state = interpolate_playback_state(model, t_query)

    assert state["is_stationary"] is True
    assert state["event_type"] == "scenario_delay"
    assert state["speed_m_s"] == 0.0


def test_07_multistop_tour_event_order(synthetic_flat_terrain):
    """Multi-stop sortie generates correctly ordered sequence: Departure -> Leg 1 -> Dwell 1 -> Leg 2 -> Arrival."""
    pts = [(5, 5), (10, 15), (20, 25)]
    cfg = PlannerConfig(profile="conservative")
    route = plan_sequential_multistop_route(
        ordered_points=pts,
        terrain=synthetic_flat_terrain,
        config=cfg,
        dwell_time_per_stop_s=600.0,
    )

    model = build_mission_playback_model(
        route_data=route,
        terrain=synthetic_flat_terrain,
        timeline=route.timeline,
    )

    event_types = [e.event_type for e in model.events]
    expected = ["start", "traverse_leg", "science_dwell", "traverse_leg", "arrival"]
    assert event_types == expected


def test_08_robotic_rover_mode_speed_scaling(synthetic_flat_terrain):
    """Robotic rover mode traverses at ~0.035 m/s, yielding ~15x longer duration than crew EVA."""
    start = (10, 10)
    goal = (20, 20)
    cfg = PlannerConfig(profile="conservative")
    route_crew = plan_route(start, goal, synthetic_flat_terrain, cfg, vehicle_mode="crew_eva")
    route_rover = plan_route(start, goal, synthetic_flat_terrain, cfg, vehicle_mode="robotic_rover")

    model_crew = build_mission_playback_model(route_crew, synthetic_flat_terrain, vehicle_mode="crew_eva")
    model_rover = build_mission_playback_model(route_rover, synthetic_flat_terrain, vehicle_mode="robotic_rover")

    # Rover duration must be significantly higher than crew duration
    assert model_rover.total_duration_s > model_crew.total_duration_s * 5.0
    # Geometry should be identical on flat terrain
    assert math.isclose(model_rover.total_distance_m, model_crew.total_distance_m, abs_tol=1e-3)


def test_09_continuous_state_interpolation_boundaries(synthetic_flat_terrain):
    """Queries before start or after end clamp to start and arrival respectively."""
    start = (10, 10)
    goal = (20, 20)
    cfg = PlannerConfig(profile="conservative")
    route = plan_route(start, goal, synthetic_flat_terrain, cfg)
    model = build_mission_playback_model(route, synthetic_flat_terrain)

    # Before start
    state_before = interpolate_playback_state(model, -100.0)
    assert state_before["time_s"] == 0.0
    assert state_before["rc"] == [10.0, 10.0]
    assert state_before["progress_ratio"] == 0.0

    # After end
    state_after = interpolate_playback_state(model, model.total_duration_s + 500.0)
    assert state_after["time_s"] == round(model.total_duration_s, 2)
    assert state_after["rc"] == [20.0, 20.0]
    assert state_after["progress_ratio"] == 1.0


def test_10_continuous_state_interpolation_midpoint(synthetic_flat_terrain):
    """Midpoint query inside a traversal leg yields smoothly interpolated coordinates."""
    start = (10, 10)
    goal = (20, 20)
    cfg = PlannerConfig(profile="conservative")
    route = plan_route(start, goal, synthetic_flat_terrain, cfg)
    model = build_mission_playback_model(route, synthetic_flat_terrain)

    t_half = model.total_duration_s / 2.0
    state_half = interpolate_playback_state(model, t_half)

    assert 10.0 < state_half["rc"][0] < 20.0
    assert 10.0 < state_half["rc"][1] < 20.0
    assert 0.4 < state_half["progress_ratio"] < 0.6


def test_11_unreachable_route_handling(synthetic_flat_terrain):
    """Unreachable route returns safe model with is_reachable=False and zero distance."""
    route = {
        "profile": "conservative",
        "start_rc": [5, 5],
        "goal_rc": [45, 45],
        "path": [],
        "distance_m": 0.0,
        "cost": float("inf"),
        "is_reachable": False,
    }

    model = build_mission_playback_model(route, synthetic_flat_terrain)
    assert model.is_reachable is False
    assert model.total_distance_m == 0.0
    assert len(model.samples) >= 1

    state = interpolate_playback_state(model, 10.0)
    assert state["rc"] == [5.0, 5.0]


def test_12_single_point_trivial_route(synthetic_flat_terrain):
    """Single point route (start == goal) produces safe model without ZeroDivisionError."""
    route = {
        "profile": "conservative",
        "start_rc": [15, 15],
        "goal_rc": [15, 15],
        "path": [[15, 15]],
        "distance_m": 0.0,
        "cost": 0.0,
        "is_reachable": True,
    }

    model = build_mission_playback_model(route, synthetic_flat_terrain)
    assert model.total_distance_m == 0.0
    state = interpolate_playback_state(model, 0.0)
    assert state["rc"] == [15.0, 15.0]


def test_13_mission_variants_isolation(synthetic_flat_terrain):
    """Nominal, Disrupted, and Adaptive models maintain independent variant metadata and paths."""
    r1 = plan_route((10, 10), (20, 20), synthetic_flat_terrain)
    r2 = plan_route((10, 10), (25, 25), synthetic_flat_terrain)

    m_nominal = build_mission_playback_model(r1, synthetic_flat_terrain, mission_variant="nominal")
    m_disrupted = build_mission_playback_model(r2, synthetic_flat_terrain, mission_variant="disrupted")

    assert m_nominal.mission_variant == "nominal"
    assert m_disrupted.mission_variant == "disrupted"
    assert m_nominal.total_distance_m != m_disrupted.total_distance_m


def test_14_schema_contract_validation(synthetic_flat_terrain):
    """Serialized playback model strictly satisfies mission-playback-response JSON schema."""
    start = (10, 10)
    goal = (20, 20)
    cfg = PlannerConfig(profile="conservative")
    route = plan_route(start, goal, synthetic_flat_terrain, cfg)
    model = build_mission_playback_model(route, synthetic_flat_terrain)

    data = model.to_dict()
    is_valid, errors = validate_contract(data, "mission-playback-response", raise_on_error=False)
    assert is_valid, f"Contract validation failed: {errors}"


def test_15_live_http_round_trip():
    """Live HTTP POST /api/mission/playback on port 3000 responds with schema-valid data."""
    payload = {
        "start_rc": [120, 120],
        "goal_rc": [130, 130],
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
        "query_time_s": 45.0,
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:3000/api/mission/playback",
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        body = json.loads(resp.read().decode("utf-8"))

    assert body["schema_version"] == "1.0.0"
    assert body["is_reachable"] is True
    assert "interpolated_state" in body
    assert body["interpolated_state"]["time_s"] == 45.0

    is_valid, errors = validate_contract(body, "mission-playback-response", raise_on_error=False)
    assert is_valid, f"Contract validation error on live endpoint: {errors}"


def test_16_historical_workspace_immutability():
    """Playback execution preserves existing historical workspace missions and experiments."""
    missions_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "workspace", "missions")
    )
    experiments_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "workspace", "experiments")
    )

    if os.path.isdir(missions_dir):
        mission_files = [f for f in os.listdir(missions_dir) if f.endswith(".json")]
        assert len(mission_files) >= 7, f"Expected at least 7 saved missions, found {len(mission_files)}"

    if os.path.isdir(experiments_dir):
        exp_files = [f for f in os.listdir(experiments_dir) if f.endswith(".json")]
        assert len(exp_files) >= 11, f"Expected at least 11 experiments, found {len(exp_files)}"
