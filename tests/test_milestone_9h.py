"""
Milestone 9H Mission Rehearsal Suite:
- Operational Timelines & Vehicle Modes (Crew EVA vs Robotic Rover)
- Multi-Stop Science Mission Order Optimizer (Exact Permutation TSP)
- Extended Scenario Library (Rockfall, Unstable Sand, Slope Restriction, Mobility Derating, Dust Storm, Compound)
- Science Regret Ledger & Recovery Plan recommendations
- API endpoint contracts and serialization
"""

import json
import math
import os
import pytest
import rasterio

from marswalk.core.terrain import load_and_process_terrain, TerrainConfig
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    VehicleMode,
    OPERATIONAL_LIMITS_S,
    calculate_traverse_time,
    format_duration,
    build_mission_timeline,
    optimize_stop_order,
    plan_route,
    plan_sequential_multistop_route,
)
from marswalk.core.stress_test import (
    DisruptionType,
    ScenarioDefinition,
    get_curated_gauntlet_scenarios,
    run_scenario,
)
from marswalk.api.service import (
    plan_route_api,
    gauntlet_api,
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

    with open(WAYPOINTS_JSON, "r", encoding="utf-8") as f:
        wp_data = json.load(f)

    waypoints = []
    for wp in wp_data.get("waypoints", []):
        from marswalk.data.ingest import query_elevation_at_lonlat
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

    return {
        "terrain": terrain,
        "transform": transform,
        "waypoints": waypoints,
    }


def test_vehicle_modes_and_operational_limits():
    """Verify Crew EVA (2.0 km/h, 8h limit) and Robotic Rover (0.035 m/s, 4h limit)."""
    assert OPERATIONAL_LIMITS_S[VehicleMode.CREW_EVA] == 28800.0  # 8 hours
    assert OPERATIONAL_LIMITS_S[VehicleMode.ROBOTIC_ROVER] == 14400.0  # 4 hours

    cost = 1000.0  # 1 km flat cost

    # Crew EVA: 1000m / (2000m / 3600s) = 1800 s (30 min)
    t_crew, t_min_c, t_max_c, fmt_crew = calculate_traverse_time(cost, vehicle_mode=VehicleMode.CREW_EVA)
    assert pytest.approx(t_crew, 0.1) == 1800.0
    assert "30 min" in fmt_crew

    # Robotic Rover: 1000m / 0.035 m/s = 28571.4 s (~7h 56m)
    t_rover, t_min_r, t_max_r, fmt_rover = calculate_traverse_time(cost, vehicle_mode=VehicleMode.ROBOTIC_ROVER)
    assert pytest.approx(t_rover, 0.5) == 28571.4
    assert "7h" in fmt_rover or "8h" in fmt_rover

    # Rover is ~15.87x slower than Crew EVA
    assert t_rover / t_crew == pytest.approx((2000.0 / 3600.0) / 0.035, 0.01)


def test_operational_timeline_building(terrain_env):
    """Verify build_mission_timeline tracks legs, dwell times, delays, and margin remaining."""
    terrain = terrain_env["terrain"]
    waypoints = terrain_env["waypoints"]

    # Plan a baseline 2-stop route
    start_rc = waypoints[0].rc
    stop1_rc = waypoints[1].rc
    goal_rc = waypoints[2].rc

    route = plan_sequential_multistop_route(
        ordered_points=[start_rc, stop1_rc, goal_rc],
        terrain=terrain,
        stop_ids=[waypoints[1].id],
        stop_priorities=[waypoints[1].priority_score],
        vehicle_mode="crew_eva",
        dwell_time_per_stop_s=900.0,
        operational_delay_s=600.0,
    )

    timeline = route.timeline
    assert timeline is not None
    assert timeline.total_traverse_time_s > 0.0
    assert timeline.total_dwell_time_s == 900.0  # 1 intermediate stop * 900s
    assert timeline.total_operational_delay_s == 600.0
    assert timeline.total_mission_time_s == pytest.approx(
        timeline.total_traverse_time_s + 900.0 + 600.0, 0.1
    )
    assert timeline.operational_limit_s == 28800.0
    assert timeline.remaining_margin_s == pytest.approx(
        28800.0 - timeline.total_mission_time_s, 0.1
    )
    assert timeline.is_within_limit is True


def test_optimize_stop_order_tsp(terrain_env):
    """Verify exact permutation TSP optimizes visiting order for intermediate science stops."""
    terrain = terrain_env["terrain"]
    waypoints = terrain_env["waypoints"]

    # Start = landing site, Goal = Kodiak Butte
    start_rc = waypoints[0].rc
    goal_rc = waypoints[3].rc

    # Two intermediate stops intentionally placed in zigzag order
    stops = [
        {"id": waypoints[2].id, "rc": waypoints[2].rc, "priority_score": waypoints[2].priority_score},
        {"id": waypoints[1].id, "rc": waypoints[1].rc, "priority_score": waypoints[1].priority_score},
    ]

    opt_result = optimize_stop_order(
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        terrain=terrain,
    )

    assert "optimized_stops" in opt_result
    assert len(opt_result["optimized_stops"]) == len(stops)
    # Optimized distance should be less than or equal to original distance
    assert opt_result["optimized_distance_m"] <= opt_result["original_distance_m"] + 1e-3
    assert opt_result["time_saved_s"] >= -1e-3


def test_scenario_library_extended_definitions(terrain_env):
    """Verify curated scenarios contain all 6 distinct types, compound scenarios, and control."""
    terrain = terrain_env["terrain"]
    waypoints = terrain_env["waypoints"]

    scenarios = get_curated_gauntlet_scenarios(
        terrain=terrain,
        waypoints=waypoints,
        baseline_distance_m=1000.0,
        baseline_path=[(100, 100), (105, 105), (110, 110), (115, 115), (120, 120)],
        include_extended=True,
    )
    assert len(scenarios) == 13

    types_present = {s.disruption_type for s in scenarios}
    assert DisruptionType.CORRIDOR_CLOSURE in types_present
    assert DisruptionType.UNSTABLE_SAND in types_present
    assert DisruptionType.RESTRICTED_SLOPE in types_present
    assert DisruptionType.MOBILITY_DEGRADATION in types_present
    assert DisruptionType.DUST_STORM_VISIBILITY in types_present
    assert DisruptionType.COMPOUND_DISRUPTION in types_present

    # Check Compound Scenarios
    compound_scenarios = [s for s in scenarios if s.disruption_type == DisruptionType.COMPOUND_DISRUPTION]
    assert len(compound_scenarios) >= 2


def test_scenario_unstable_sand_traversal(terrain_env):
    """Verify Unstable Sand applies 3.0x cost multiplier and creates a footprint without hard closure."""
    terrain = terrain_env["terrain"]
    waypoints = terrain_env["waypoints"]

    start_wp = waypoints[0]
    goal_wp = waypoints[1]

    baseline = plan_route(start_wp.rc, goal_wp.rc, terrain)
    assert baseline.is_reachable is True

    # Midpoint of baseline route
    mid_idx = len(baseline.path) // 2
    mid_r, mid_c = baseline.path[mid_idx]

    sand_cells = []
    for r in range(mid_r - 2, mid_r + 3):
        for c in range(mid_c - 2, mid_c + 3):
            if 0 <= r < terrain.height and 0 <= c < terrain.width:
                sand_cells.append((r, c))

    sand_scenario = ScenarioDefinition(
        id="test_sand",
        name="Test Sand Corridor",
        disruption_type=DisruptionType.UNSTABLE_SAND,
        description="Hypothetical soft sand footprint.",
        cost_multiplier_cells=sand_cells,
        cost_multiplier=3.5,
    )

    comparison = run_scenario(
        baseline_route=baseline,
        scenario=sand_scenario,
        start_rc=start_wp.rc,
        goal_rc=goal_wp.rc,
        waypoints=[],
        terrain=terrain,
    )
    assert comparison.scenario_route.is_reachable is True
    # The route must either detour around or traverse with increased cost/effort
    assert comparison.scenario_route.cost >= baseline.cost


def test_scenario_restricted_slope_ceiling(terrain_env):
    """Verify Restricted Slope overrides max slope ceiling and forces detour or handles steep cells."""
    terrain = terrain_env["terrain"]
    waypoints = terrain_env["waypoints"]

    start_wp = waypoints[0]
    goal_wp = waypoints[1]
    baseline = plan_route(start_wp.rc, goal_wp.rc, terrain)

    slope_scenario = ScenarioDefinition(
        id="test_slope",
        name="Test 10deg Slope Cap",
        disruption_type=DisruptionType.RESTRICTED_SLOPE,
        description="Restricted slope test corridor.",
        max_slope_deg_override=10.0,
    )

    comparison = run_scenario(
        baseline_route=baseline,
        scenario=slope_scenario,
        start_rc=start_wp.rc,
        goal_rc=goal_wp.rc,
        waypoints=[],
        terrain=terrain,
    )
    assert comparison.scenario_route.is_reachable is True


def test_scenario_mobility_derating_preserves_path(terrain_env):
    """Verify Mobility Degradation preserves geometric path (0 m detour) but increases traverse time."""
    terrain = terrain_env["terrain"]
    waypoints = terrain_env["waypoints"]

    start_wp = waypoints[0]
    goal_wp = waypoints[1]
    baseline = plan_route(start_wp.rc, goal_wp.rc, terrain)

    mobility_scenario = ScenarioDefinition(
        id="test_mobility",
        name="Test Motor Derating",
        disruption_type=DisruptionType.MOBILITY_DEGRADATION,
        description="Drive motor thermal degradation test.",
        speed_multiplier=0.5,
        slope_penalty_multiplier=1.5,
    )

    comparison = run_scenario(
        baseline_route=baseline,
        scenario=mobility_scenario,
        start_rc=start_wp.rc,
        goal_rc=goal_wp.rc,
        waypoints=[],
        terrain=terrain,
    )
    assert comparison.scenario_route.is_reachable is True
    # Geometric path is identical
    assert pytest.approx(comparison.delta_distance_m, abs=0.1) == 0.0
    # Travel time is doubled (0.5x speed)
    assert comparison.scenario_route.travel_time_s >= baseline.travel_time_s * 1.95


def test_compound_scenario_execution(terrain_env):
    """Verify Compound Scenario combines physical closure and operational speed degradation."""
    terrain = terrain_env["terrain"]
    waypoints = terrain_env["waypoints"]

    start_wp = waypoints[0]
    goal_wp = waypoints[1]
    baseline = plan_route(start_wp.rc, goal_wp.rc, terrain)

    scenarios = get_curated_gauntlet_scenarios(
        terrain=terrain,
        waypoints=waypoints,
        baseline_distance_m=baseline.distance_m,
        baseline_path=baseline.path,
        include_extended=True,
    )
    compound = next(s for s in scenarios if s.id == "scen_compound_rockfall_mobility")

    comparison = run_scenario(
        baseline_route=baseline,
        scenario=compound,
        start_rc=start_wp.rc,
        goal_rc=goal_wp.rc,
        waypoints=[],
        terrain=terrain,
    )
    assert comparison.scenario_route.is_reachable is True
    assert comparison.scenario.disruption_type == DisruptionType.COMPOUND_DISRUPTION
    # Detour must exist because rockfall is on the corridor
    assert comparison.delta_distance_m > 0.0
    assert comparison.delta_travel_time_s > 0.0


def test_api_vehicle_mode_and_timeline_serialization(terrain_env):
    """Verify /api/plan_route returns vehicle_mode and timeline events."""
    waypoints = terrain_env["waypoints"]
    payload = {
        "start": {"row": waypoints[0].rc[0], "col": waypoints[0].rc[1]},
        "goal": {"row": waypoints[2].rc[0], "col": waypoints[2].rc[1]},
        "stops": [
            {"row": waypoints[1].rc[0], "col": waypoints[1].rc[1], "id": waypoints[1].id, "priority_score": waypoints[1].priority_score}
        ],
        "vehicle_mode": "robotic_rover",
        "dwell_time_s": 900,
    }

    resp = plan_route_api(payload, terrain_env["terrain"], terrain_env["transform"], terrain_env["waypoints"])
    assert resp["is_reachable"] is True
    assert resp["vehicle_mode"] == "robotic_rover"
    assert "timeline" in resp
    timeline = resp["timeline"]
    assert len(timeline["events"]) >= 3
    assert timeline["operational_limit_s"] == 14400.0


def test_api_stop_order_optimization(terrain_env):
    """Verify /api/plan_route with optimize_stops=True returns optimization metadata."""
    waypoints = terrain_env["waypoints"]
    payload = {
        "start": {"row": waypoints[0].rc[0], "col": waypoints[0].rc[1]},
        "goal": {"row": waypoints[3].rc[0], "col": waypoints[3].rc[1]},
        "stops": [
            {"row": waypoints[2].rc[0], "col": waypoints[2].rc[1], "id": waypoints[2].id, "priority_score": waypoints[2].priority_score},
            {"row": waypoints[1].rc[0], "col": waypoints[1].rc[1], "id": waypoints[1].id, "priority_score": waypoints[1].priority_score},
        ],
        "optimize_stops": True,
    }

    resp = plan_route_api(payload, terrain_env["terrain"], terrain_env["transform"], terrain_env["waypoints"])
    assert resp["is_reachable"] is True
    assert "optimization" in resp
    opt = resp["optimization"]
    assert opt["is_optimized"] is True
    assert "formatted_time_saved" in opt


def test_api_gauntlet_with_recovery_plan(terrain_env):
    """Verify /api/gauntlet returns recovery plan and hazard footprint coordinates."""
    waypoints = terrain_env["waypoints"]
    payload = {
        "start": {"row": waypoints[0].rc[0], "col": waypoints[0].rc[1]},
        "goal": {"row": waypoints[1].rc[0], "col": waypoints[1].rc[1]},
        "scenario_id": "scen_corridor_rockfall",
    }

    resp = gauntlet_api(payload, terrain_env["terrain"], terrain_env["transform"], terrain_env["waypoints"])
    assert resp["is_scenario_reachable"] is True
    assert "recovery_plan" in resp
    rec = resp["recovery_plan"]
    assert rec is not None
    assert "strategy" in rec
    assert "action_label" in rec
    assert "coordinates_3d" in resp["scenario"]
