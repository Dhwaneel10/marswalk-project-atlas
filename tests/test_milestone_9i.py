"""
Milestone 9I Mission Analysis Laboratory Test Suite:
- Scalable Multi-Stop Optimization (Exact permutation for k <= 7, 2-Opt heuristic for k > 7)
- Transparent Algorithm Disclosure & Profile-Specific Objectives
- Engineering Assumptions & Operational Constraints Classification
- Side-by-Side Scenario Comparison Engine with Safe Delta Calculations
- Scenario Sensitivity Parameter Sweep Analysis
- Mission Briefing JSON and Markdown Export Serialization
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
    ENGINEERING_ASSUMPTIONS,
    calculate_traverse_time,
    format_duration,
    optimize_stop_order,
    plan_route,
    plan_sequential_multistop_route,
)
from marswalk.core.stress_test import (
    DisruptionType,
    ScenarioDefinition,
    get_curated_gauntlet_scenarios,
    run_scenario,
    run_scenario_sensitivity_sweep,
)
from marswalk.api.service import (
    plan_route_api,
    gauntlet_api,
    scenario_comparison_api,
    scenario_sensitivity_api,
    export_briefing_api,
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
                    )
                )
            except Exception:
                pass
    return {"terrain": terrain, "transform": transform, "waypoints": waypoints}


def test_multistop_exact_tsp_for_k_le_7(terrain_env):
    """Verify exact permutation search is utilized for k <= 7 stops and reports global optimality."""
    terrain = terrain_env["terrain"]
    waypoints = terrain_env["waypoints"]

    start_rc = waypoints[0].rc
    goal_rc = waypoints[5].rc

    # 4 intermediate stops
    stops = [
        {"id": waypoints[i].id, "rc": waypoints[i].rc, "priority_score": waypoints[i].priority_score}
        for i in [4, 1, 3, 2]
    ]

    opt_res = optimize_stop_order(
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        terrain=terrain,
        profile="conservative",
    )

    assert opt_res["optimization_method"] == "exact_permutation"
    assert opt_res["is_globally_optimal"] is True
    assert "Globally optimal" in opt_res["algorithm_disclosure"]
    assert opt_res["objective_profile"] == "conservative"
    assert len(opt_res["optimized_stops"]) == 4
    assert opt_res["optimized_distance_m"] <= opt_res["original_distance_m"] + 1e-2


def test_multistop_2opt_heuristic_for_k_gt_7(terrain_env):
    """Verify deterministic 2-Opt local search is utilized for k > 7 stops and explicitly discloses approximation."""
    terrain = terrain_env["terrain"]
    waypoints = terrain_env["waypoints"]

    start_rc = waypoints[0].rc
    goal_rc = waypoints[11].rc

    # 9 intermediate stops (from waypoints 1 through 9)
    stops = [
        {"id": waypoints[i].id, "rc": waypoints[i].rc, "priority_score": waypoints[i].priority_score}
        for i in range(1, 10)
    ]
    assert len(stops) == 9

    opt_res = optimize_stop_order(
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        terrain=terrain,
        profile="balanced",
    )

    assert opt_res["optimization_method"] == "heuristic_2opt"
    assert opt_res["is_globally_optimal"] is False
    assert "2-Opt local search heuristic" in opt_res["algorithm_disclosure"]
    assert "Global optimality is not guaranteed" in opt_res["algorithm_disclosure"]
    assert opt_res["objective_profile"] == "balanced"
    # All 9 stops must be preserved in optimized_stops
    assert len(opt_res["optimized_stops"]) == 9
    assert opt_res["optimized_distance_m"] <= opt_res["original_distance_m"] + 1e-2


def test_engineering_assumptions_classification():
    """Verify transparent classification of Apollo analogue and operational constraints."""
    assert "crew_eva_speed" in ENGINEERING_ASSUMPTIONS
    crew_speed = ENGINEERING_ASSUMPTIONS["crew_eva_speed"]
    assert crew_speed["classification"] == "Engineering Analogue"
    assert "Apollo" in crew_speed["citation"]
    assert crew_speed["is_physical_limit"] is False
    assert "NOT validated Mars astronaut performance" in crew_speed["disclosure"]

    assert "robotic_rover_speed" in ENGINEERING_ASSUMPTIONS
    rover_speed = ENGINEERING_ASSUMPTIONS["robotic_rover_speed"]
    assert rover_speed["classification"] == "Sourced Technical Value"
    assert "Perseverance" in rover_speed["citation"]

    assert "crew_eva_duration_limit" in ENGINEERING_ASSUMPTIONS
    crew_limit = ENGINEERING_ASSUMPTIONS["crew_eva_duration_limit"]
    assert crew_limit["classification"] == "Configurable Mission Constraint"


def test_scenario_sensitivity_sweep(terrain_env):
    """Verify parameter sensitivity sweep experiment executes real evaluations across varying severities."""
    terrain = terrain_env["terrain"]
    waypoints = terrain_env["waypoints"]

    start_rc = waypoints[0].rc
    goal_rc = waypoints[3].rc

    base_route = plan_route(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain,
        config=PlannerConfig(profile="conservative"),
    )

    scenarios = get_curated_gauntlet_scenarios(
        terrain=terrain,
        waypoints=waypoints,
        baseline_distance_m=base_route.distance_m,
        baseline_path=base_route.path,
        include_extended=True,
    )
    scen_rockfall = next(s for s in scenarios if s.id == "scen_corridor_rockfall")

    radii = [20.0, 40.0, 70.0, 100.0]
    sweep_res = run_scenario_sensitivity_sweep(
        baseline_route=base_route,
        scenario=scen_rockfall,
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain,
        parameter_name="radius_m",
        parameter_values=radii,
    )

    assert sweep_res["parameter_name"] == "radius_m"
    assert sweep_res["num_evaluations"] == 4
    assert len(sweep_res["records"]) == 4
    for r in sweep_res["records"]:
        assert r["distance_m"] >= base_route.distance_m - 1e-2
        assert "delta_distance_m" in r
        assert "travel_time_s" in r
        assert "pct_distance_change" in r
        assert r["is_reachable"] is True


def test_scenario_comparison_api(terrain_env):
    """Verify POST /api/scenario_comparison returns structured side-by-side metrics from identical baseline."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    waypoints = terrain_env["waypoints"]

    payload = {
        "start": {"row": waypoints[0].rc[0], "col": waypoints[0].rc[1]},
        "goal": {"row": waypoints[3].rc[0], "col": waypoints[3].rc[1]},
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
        "scenario_ids": [
            "scen_corridor_rockfall",
            "scen_unstable_sand",
            "scen_mobility_degradation",
        ],
    }

    res = scenario_comparison_api(payload, terrain, transform, waypoints)

    assert "baseline_route" in res
    assert "scenarios" in res
    assert len(res["scenarios"]) == 3

    for sc in res["scenarios"]:
        assert "scenario" in sc
        assert "scenario_route" in sc
        assert "delta_distance_m" in sc
        assert "delta_travel_time_s" in sc
        assert "pct_distance_change" in sc
        assert "regret_ledger" in sc
        # Non-negative retention
        assert sc["regret_ledger"]["retention_pct"] >= 0.0


def test_scenario_sensitivity_api(terrain_env):
    """Verify POST /api/scenario_sensitivity endpoint executes correctly."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    waypoints = terrain_env["waypoints"]

    payload = {
        "start": {"row": waypoints[0].rc[0], "col": waypoints[0].rc[1]},
        "goal": {"row": waypoints[3].rc[0], "col": waypoints[3].rc[1]},
        "scenario_id": "scen_corridor_rockfall",
        "parameter_name": "radius_m",
        "parameter_values": [30.0, 60.0, 90.0],
    }

    res = scenario_sensitivity_api(payload, terrain, transform, waypoints)
    assert res["scenario_id"] == "scen_corridor_rockfall"
    assert res["parameter_name"] == "radius_m"
    assert res["num_evaluations"] == 3
    assert len(res["records"]) == 3


def test_export_briefing_api(terrain_env):
    """Verify POST /api/export_briefing generates JSON archive and Markdown technical report."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]

    payload = {
        "mission_plan": {
            "profile": "conservative",
            "vehicle_mode": "crew_eva",
            "distance_m": 2450.5,
            "formatted_travel_time": "1h 14m",
            "visited_waypoint_ids": ["octavia_butler", "kodiak_butte"],
            "is_reachable": True,
            "timeline": {
                "formatted_mission_time": "1h 44m",
            },
        },
        "comparison_data": {
            "scenarios": [
                {
                    "scenario": {"name": "Traverse Corridor Rockfall"},
                    "scenario_route": {"distance_m": 2680.0},
                    "delta_distance_m": 229.5,
                    "formatted_delta_travel_time": "+7 min",
                    "formatted_total_mission_time": "1h 51m",
                    "regret_ledger": {"retention_pct": 100.0},
                    "is_scenario_reachable": True,
                }
            ]
        },
        "recovery_data": {
            "strategy": "Lateral avoidance of rockfall cone",
            "formatted_margin_recovered": "+15 min",
        },
    }

    briefing = export_briefing_api(payload, terrain, transform)
    assert "json_export" in briefing
    assert "markdown_briefing" in briefing
    assert "timestamp" in briefing

    md = briefing["markdown_briefing"]
    assert "# MARSWALK 2.0 — MISSION REHEARSAL & ANALYSIS LABORATORY BRIEFING" in md
    assert "Executive Mission Summary" in md
    assert "Engineering Assumptions & Classification Ledger" in md
    assert "Disruption Scenarios Comparison Matrix" in md
    assert "Contingency & Recovery Assessment" in md
    assert "USGS Astrogeology Science Center" in md
    assert "RESEARCH PROTOTYPE DISCLAIMER" in md
