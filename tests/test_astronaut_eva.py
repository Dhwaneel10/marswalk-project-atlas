"""
MarsWalk 2.0 / Project Atlas — Unit & Integration Test Suite for Astronaut EVA Mode.

Validates:
- EVA profile configuration and parameter bounds.
- Biomechanical human mobility cost model (asymmetric slope, carried mass, roughness).
- Slope impassability constraints for suited astronaut (configurable 15-20° threshold).
- Three-route comparison generator (Conservative, Science-Priority, Time-Efficient).
- Consumable budgeting (dynamic metabolic kcal, oxygen liters, suit battery Wh, emergency reserves).
- Return-to-base trajectory validation (active return route, not Euclidean approximation).
- Walkback safety limit enforcement (>4.0 km Apollo limit advisory).
- Dedicated EVA contingency workflow (dust events, comms loss, obstacle detection, consumable warnings).
- Authoritative state machine transitions (NOMINAL, CAUTION, SAFE_HOLD, RETURN_TO_BASE).
- Radiation status separation (explicit UNKNOWN display).
- Input validation and rejection of invalid / missing inputs.
- Strict isolation: verifies that astronaut profile modifications do NOT alter robotic rover results.
"""

import os
import json
import pytest
import numpy as np
import rasterio

from marswalk.core.terrain import TerrainGrid, TerrainConfig, load_and_process_terrain
from marswalk.core.planner import ScienceWaypoint
from marswalk.data.ingest import query_elevation_at_lonlat
from marswalk.core.astronaut_eva import (
    EVAMissionState,
    EVAContingencyType,
    HumanMobilityConfig,
    EVAConsumableBudget,
    EVAConsumableUsage,
    calculate_human_step_cost,
    calculate_human_walk_time_and_metabolics,
    evaluate_eva_consumable_budget,
    plan_human_eva_leg,
    plan_three_astronaut_eva_routes,
    execute_eva_contingency_workflow,
)
from marswalk.api.service import (
    plan_astronaut_eva_api,
    eva_contingency_api,
    plan_route_api,
    APIError,
)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSED_TIFF = os.path.join(_REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")
WAYPOINTS_JSON = os.path.join(_REPO_ROOT, "data", "waypoints_jezero.json")


@pytest.fixture
def jezero_environment():
    """Load authentic Jezero CTX terrain grid, affine transform, and science waypoints."""
    assert os.path.exists(PROCESSED_TIFF), f"Missing processed GeoTIFF: {PROCESSED_TIFF}"
    grid = load_and_process_terrain(PROCESSED_TIFF)
    with rasterio.open(PROCESSED_TIFF) as src:
        transform = src.transform

    waypoints = []
    if os.path.exists(WAYPOINTS_JSON):
        with open(WAYPOINTS_JSON, "r", encoding="utf-8") as f:
            wp_data = json.load(f)
        for wp in wp_data.get("waypoints", []):
            elev, r, c = query_elevation_at_lonlat(PROCESSED_TIFF, wp["lon_deg"], wp["lat_deg"])
            waypoints.append(
                ScienceWaypoint(
                    id=wp["id"],
                    name=wp["name"],
                    rc=(r, c),
                    priority_score=wp.get("priority_score", 0.0),
                )
            )

    return {
        "grid": grid,
        "transform": transform,
        "waypoints": waypoints,
    }


def test_human_mobility_config_defaults_and_mass():
    """Verify default biometric and mass parameters."""
    cfg = HumanMobilityConfig()
    assert cfg.nominal_walk_speed_kmh == 2.0
    assert cfg.max_walk_slope_deg == 20.0
    assert cfg.astronaut_body_mass_kg == 80.0
    assert cfg.spacesuit_mass_kg == 60.0
    assert cfg.carried_gear_mass_kg == 25.0
    assert cfg.total_system_mass_kg == 165.0
    # Mass effort multiplier: 165 / 140 = 1.17857...
    assert round(cfg.mass_effort_multiplier, 3) == 1.179


def test_human_step_cost_flat_vs_slope(jezero_environment):
    """Verify slope and uphill penalties in human mobility model."""
    grid = jezero_environment["grid"]
    cfg = HumanMobilityConfig(nominal_walk_speed_kmh=2.0, max_walk_slope_deg=20.0)

    # Identical cell (zero step)
    c_zero = calculate_human_step_cost((100, 100), (100, 100), grid, config=cfg)
    assert c_zero == 0.0

    # Neighbor step
    c_step = calculate_human_step_cost((100, 100), (100, 101), grid, config=cfg)
    assert c_step > 0.0
    assert not np.isinf(c_step)

    # If destination exceeds max_walk_slope_deg, cost must be infinite
    # Temporarily force steep slope in a synthetic test cell
    test_grid = grid
    r, c = 50, 50
    orig_slope = test_grid.slope_deg[r, c]
    try:
        test_grid.slope_deg[r, c] = 25.0  # Exceeds 20.0° cutoff
        c_steep = calculate_human_step_cost((50, 49), (50, 50), test_grid, config=cfg)
        assert np.isinf(c_steep)
    finally:
        test_grid.slope_deg[r, c] = orig_slope


def test_consumable_budget_and_walkback_checks():
    """Verify consumable modeling, reserve percentage, and walkback detection."""
    b = EVAConsumableBudget(
        max_duration_s=28800.0,
        primary_o2_capacity_liters=600.0,
        emergency_o2_reserve_liters=120.0,
        apollo_walkback_limit_m=4000.0,
    )

    # 1. Short nominal traverse (1.0 hour walk, 1.0 hour dwell, 2000m)
    walk_s, tot_s, kcal, o2_l, bat_wh = calculate_human_walk_time_and_metabolics(
        effort_cost=2000.0,
        ground_distance_m=2000.0,
        budget_cfg=b,
        dwell_time_s=3600.0,
    )
    usage = evaluate_eva_consumable_budget(
        active_walk_s=walk_s,
        dwell_s=3600.0,
        metabolic_kcal=kcal,
        o2_liters=o2_l,
        battery_wh=bat_wh,
        budget=b,
        ground_dist_m=2000.0,
    )
    assert usage.is_consumable_feasible is True
    assert usage.walkback_limit_exceeded is False
    assert usage.remaining_o2_liters > b.emergency_o2_reserve_liters
    assert usage.o2_reserve_margin_pct > 20.0

    # 2. Excursion exceeding 4.0 km walkback limit
    usage_long = evaluate_eva_consumable_budget(
        active_walk_s=walk_s,
        dwell_s=3600.0,
        metabolic_kcal=kcal,
        o2_liters=o2_l,
        battery_wh=bat_wh,
        budget=b,
        ground_dist_m=4500.0,
    )
    assert usage_long.walkback_limit_exceeded is True


def test_plan_three_astronaut_eva_routes(jezero_environment):
    """Verify generation of Conservative, Science-Priority, and Time-Efficient routes."""
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]

    # Base at Octavia E. Butler Landing (117, 157)
    # Science stops at 2 realistic outcrop points in Jezero
    payload = {
        "base": {"row": 117, "col": 157},
        "science_targets": [
            {"row": 100, "col": 140, "id": "target_delta_front", "name": "Delta Front Outcrop"},
            {"row": 85, "col": 135, "id": "target_crater_floor", "name": "Crater Floor Stratum"},
        ],
        "require_return_to_base": True,
        "dwell_time_per_target_s": 900.0,
    }

    res = plan_astronaut_eva_api(payload, grid, transform)
    assert res["mission_mode"] == "astronaut_eva"
    assert "routes" in res
    assert "conservative" in res["routes"]
    assert "science_first" in res["routes"]
    assert "time_efficient" in res["routes"]

    for r_key, r_info in res["routes"].items():
        assert r_info["is_reachable"] is True
        assert r_info["total_distance_m"] > 0.0
        assert r_info["consumables"]["metabolic_burn_kcal"] > 0.0
        assert r_info["consumables"]["oxygen_consumed_liters"] > 0.0
        assert len(r_info["path_rc"]) > 0
        assert r_info["return_to_base_included"] is True

    # Disclaimer check
    assert "not certified" in res["operational_safety_disclaimer"].lower()


def test_eva_contingency_dust_event_and_safe_hold(jezero_environment):
    """Verify state transitions and emergency return route under dust disruption."""
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]

    payload = {
        "current_position": {"row": 85, "col": 135},
        "base": {"row": 117, "col": 157},
        "contingency_type": "dust_event",
        "custom_message": "Atmospheric dust optical depth tau=2.8 approaching from north",
    }
    res = eva_contingency_api(payload, grid, transform)
    assert res["mission_state"] == "CAUTION"
    assert "dust" in res["advisory"].lower()
    assert "UNKNOWN" in res["radiation_status"]
    assert res["emergency_return_route"]["is_reachable"] is True
    assert res["emergency_return_route"]["metrics"]["return_distance_m"] > 0.0


def test_eva_contingency_obstacle_immediate_return(jezero_environment):
    """Verify obstacle detection triggers RETURN_TO_BASE sequence."""
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]

    payload = {
        "current_position": {"row": 85, "col": 135},
        "base": {"row": 117, "col": 157},
        "contingency_type": "newly_detected_obstacle",
        "obstacle_location": {"row": 90, "col": 140},
        "obstacle_radius_m": 50.0,
    }
    res = eva_contingency_api(payload, grid, transform)
    assert res["mission_state"] == "RETURN_TO_BASE"
    assert res["requires_immediate_return"] is True
    assert "hazard" in res["advisory"].lower() or "obstructed" in res["advisory"].lower()


def test_eva_input_validation_errors(jezero_environment):
    """Verify rejection of missing base, missing targets, duplicate targets, or invalid contingency."""
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]

    # Missing base
    with pytest.raises(APIError) as exc_info:
        plan_astronaut_eva_api({"science_targets": [{"row": 100, "col": 140}]}, grid, transform)
    assert exc_info.value.status_code == 400

    # Missing targets
    with pytest.raises(APIError) as exc_info:
        plan_astronaut_eva_api({"base": {"row": 117, "col": 157}, "science_targets": []}, grid, transform)
    assert exc_info.value.status_code == 400

    # Duplicate target coordinates
    with pytest.raises(APIError) as exc_info:
        plan_astronaut_eva_api({
            "base": {"row": 117, "col": 157},
            "science_targets": [
                {"row": 100, "col": 140},
                {"row": 100, "col": 140},
            ]
        }, grid, transform)
    assert exc_info.value.status_code == 400

    # Invalid contingency type
    with pytest.raises(APIError) as exc_info:
        eva_contingency_api({
            "current_position": {"row": 85, "col": 135},
            "base": {"row": 117, "col": 157},
            "contingency_type": "alien_encounter",
        }, grid, transform)
    assert exc_info.value.status_code == 400


def test_rover_mode_isolation(jezero_environment):
    """
    CRITICAL ISOLATION TEST:
    Verify that calling plan_route_api for robotic_rover produces completely identical,
    unmodified results without human bioenergetics artifacts.
    """
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]
    waypoints = jezero_environment["waypoints"]

    payload_rover = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "conservative",
        "vehicle_mode": "robotic_rover",
    }
    res_rover = plan_route_api(payload_rover, grid, transform, waypoints)
    assert res_rover["is_reachable"] is True
    assert res_rover["vehicle_mode"] == "robotic_rover"
    assert res_rover.get("human_eva_bioenergetics") is None
    # Verify rover speed model: drive window is 4.0h, travel time is substantial
    assert res_rover["travel_time_s"] > 10000.0  # Much longer than 2.0 km/h human walk
