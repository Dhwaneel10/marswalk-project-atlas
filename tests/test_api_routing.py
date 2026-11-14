"""
Automated unit and integration tests for MarsWalk 2.0 Live Routing & Gauntlet API Engine.
Tests endpoint validation, A* route generation, budget constraints, hypothetical disruptions,
and HTTP response contracts.
"""

import json
import math
import os
import urllib.request
import urllib.error
import pytest
import numpy as np
import rasterio

from marswalk.core.terrain import (
    TerrainConfig,
    TerrainGrid,
    derive_terrain_from_array,
    load_and_process_terrain,
)
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    plan_route,
)
from marswalk.core.stress_test import (
    DisruptionType,
    ScenarioDefinition,
    get_curated_gauntlet_scenarios,
)
from marswalk.data.ingest import (
    proj_xy_to_planetocentric,
    planetocentric_to_proj_xy,
    query_elevation_at_lonlat,
    inspect_geotiff,
)
from marswalk.api.service import (
    APIError,
    parse_endpoint_rc,
    rc_to_lonlat,
    format_route_result,
    plan_route_api,
    gauntlet_api,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_TIFF = os.path.join(REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")
WAYPOINTS_JSON = os.path.join(REPO_ROOT, "data", "waypoints_jezero.json")


@pytest.fixture(scope="module")
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


@pytest.fixture
def synthetic_flat_grid():
    """30x30 flat terrain grid with standard 20m x 20m spacing."""
    elev = np.zeros((30, 30), dtype=np.float32)
    cfg = TerrainConfig(
        cell_size_m=20.0,
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        alpha_s=0.0,
        alpha_r=0.0,
        alpha_up=0.0,
    )
    return derive_terrain_from_array(elev, config=cfg)


# ==============================================================================
# Endpoint Parsing and Validation Tests
# ==============================================================================

def test_parse_endpoint_rc_valid_integers(jezero_environment):
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]

    r, c = parse_endpoint_rc({"row": 117, "col": 157}, grid, transform, "Start")
    assert r == 117
    assert c == 157

    # String integer coercion
    r, c = parse_endpoint_rc({"row": "66", "col": "128"}, grid, transform, "Goal")
    assert r == 66
    assert c == 128


def test_parse_endpoint_rc_valid_lonlat(jezero_environment):
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]

    # Octavia landing lon/lat: ~77.4509, ~18.4447
    lon, lat = rc_to_lonlat(117, 157, transform)
    r, c = parse_endpoint_rc({"lon_deg": lon, "lat_deg": lat}, grid, transform, "Landing")
    assert abs(r - 117) <= 1
    assert abs(c - 157) <= 1


def test_parse_endpoint_rc_out_of_bounds(jezero_environment):
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]

    with pytest.raises(APIError) as exc_info:
        parse_endpoint_rc({"row": -1, "col": 50}, grid, transform, "Start")
    assert exc_info.value.status_code == 400
    assert "outside raster dimensions" in exc_info.value.message

    with pytest.raises(APIError) as exc_info:
        parse_endpoint_rc({"row": 300, "col": 50}, grid, transform, "Start")
    assert exc_info.value.status_code == 400


def test_parse_endpoint_rc_nodata_mask(synthetic_flat_grid):
    # Set (5, 5) to invalid NoData mask
    synthetic_flat_grid.invalid_mask[5, 5] = True
    dummy_transform = rasterio.Affine.identity()

    with pytest.raises(APIError) as exc_info:
        parse_endpoint_rc({"row": 5, "col": 5}, synthetic_flat_grid, dummy_transform, "Hazard")
    assert exc_info.value.status_code == 422
    assert "falls on invalid NoData" in exc_info.value.message


def test_parse_endpoint_rc_invalid_types(synthetic_flat_grid):
    dummy_transform = rasterio.Affine.identity()

    with pytest.raises(APIError) as exc_info:
        parse_endpoint_rc("not_a_dict", synthetic_flat_grid, dummy_transform, "BadInput")
    assert exc_info.value.status_code == 400

    with pytest.raises(APIError) as exc_info:
        parse_endpoint_rc({"invalid_key": 10}, synthetic_flat_grid, dummy_transform, "BadKeys")
    assert exc_info.value.status_code == 400


# ==============================================================================
# Live Route Planning API Tests
# ==============================================================================

def test_plan_route_api_conservative_success(jezero_environment):
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]
    waypoints = jezero_environment["waypoints"]

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "conservative",
    }

    result = plan_route_api(payload, grid, transform, waypoints)

    assert result["is_reachable"] is True
    assert result["is_budget_feasible"] is True
    assert result["profile"] == "conservative"
    assert result["distance_m"] > 1000.0
    assert result["cost"] is not None
    assert result["cumulative_climb_m"] >= 0.0
    assert result["max_slope_deg"] >= 0.0
    assert len(result["path_rc"]) > 10
    assert result["path_rc"][0] == [117, 157]
    assert result["path_rc"][-1] == [66, 128]
    assert len(result["coordinates_3d"]) == len(result["path_rc"])


def test_plan_route_api_profiles(jezero_environment):
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]
    waypoints = jezero_environment["waypoints"]

    for prof in ["balanced", "science_first"]:
        payload = {
            "start": {"row": 117, "col": 157},
            "goal": {"row": 66, "col": 128},
            "profile": prof,
        }
        res = plan_route_api(payload, grid, transform, waypoints)
        assert res["is_reachable"] is True
        assert res["profile"] == prof


def test_plan_route_api_invalid_profile(jezero_environment):
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "hyper_warp_drive",
    }
    with pytest.raises(APIError) as exc:
        plan_route_api(payload, grid, transform)
    assert exc.value.status_code == 400
    assert "Unsupported profile" in exc.value.message


def test_plan_route_api_budget_constraint(jezero_environment):
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]
    waypoints = jezero_environment["waypoints"]

    # Set unrealistically small physical distance budget (500m when baseline ~1240m)
    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "conservative",
        "max_distance_m": 500.0,
    }
    res = plan_route_api(payload, grid, transform, waypoints)
    assert res["is_reachable"] is True
    assert res["is_budget_feasible"] is False
    assert "exceeds" in res["status_message"].lower() or "budget" in res["status_message"].lower()


# ==============================================================================
# The Gauntlet Stress-Testing API Tests
# ==============================================================================

def test_gauntlet_api_hawksbill_rockfall(jezero_environment):
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]
    waypoints = jezero_environment["waypoints"]

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "conservative",
        "scenario_id": "scen_hawksbill_rockfall",
    }

    res = gauntlet_api(payload, grid, transform, waypoints)

    assert "HYPOTHETICAL STRESS-TEST SCENARIO" in res["disclaimer"]
    assert res["scenario"]["id"] == "scen_hawksbill_rockfall"
    assert res["scenario"]["disruption_type"] == "corridor_closure"
    assert res["baseline_route"]["is_reachable"] is True
    assert res["scenario_route"]["is_reachable"] is True
    assert "regret_ledger" in res
    assert res["headline"] is not None
    assert res["detail"] is not None


def test_gauntlet_api_delta_channel_block(jezero_environment):
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]
    waypoints = jezero_environment["waypoints"]

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "conservative",
        "scenario_id": "scen_delta_channel_block",
    }

    res = gauntlet_api(payload, grid, transform, waypoints)
    assert res["scenario"]["id"] == "scen_delta_channel_block"
    assert res["scenario_route"]["is_reachable"] is True


def test_gauntlet_api_custom_closure(jezero_environment):
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]
    waypoints = jezero_environment["waypoints"]

    # Block specific cells
    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "scenario_id": "custom_closure",
        "blocked_cells": [[110, 150], [111, 150], [112, 150]],
    }

    res = gauntlet_api(payload, grid, transform, waypoints)
    assert res["scenario"]["id"] == "custom_closure"
    assert res["scenario"]["num_blocked_cells"] == 3


def test_gauntlet_api_unknown_scenario(jezero_environment):
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "scenario_id": "alien_mothership_invasion",
    }

    with pytest.raises(APIError) as exc:
        gauntlet_api(payload, grid, transform)
    assert exc.value.status_code == 400
    assert "Unknown scenario_id" in exc.value.message


# ==============================================================================
# Live HTTP Server Integration Tests (Port 3000)
# ==============================================================================

def test_live_server_endpoints():
    """Verify live HTTP server on port 3000 handles endpoints properly."""
    base_url = "http://127.0.0.1:3000"

    # 1. Health check
    try:
        req = urllib.request.Request(f"{base_url}/api/health")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["status"] == "online"
            assert data["terrain_loaded"] is True
    except urllib.error.URLError:
        pytest.skip("Atlas HTTP server on port 3000 not currently reachable")

    # 2. Plan Route POST
    plan_body = json.dumps({
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "conservative"
    }).encode("utf-8")

    req_plan = urllib.request.Request(
        f"{base_url}/api/plan_route",
        data=plan_body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req_plan, timeout=5.0) as resp:
        assert resp.status == 200
        p_data = json.loads(resp.read().decode())
        assert p_data["is_reachable"] is True
        assert len(p_data["path_rc"]) > 10

    # 3. Gauntlet POST
    gauntlet_body = json.dumps({
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "conservative",
        "scenario_id": "scen_hawksbill_rockfall"
    }).encode("utf-8")

    req_gauntlet = urllib.request.Request(
        f"{base_url}/api/gauntlet",
        data=gauntlet_body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req_gauntlet, timeout=5.0) as resp:
        assert resp.status == 200
        g_data = json.loads(resp.read().decode())
        assert "HYPOTHETICAL" in g_data["disclaimer"]
        assert g_data["scenario"]["id"] == "scen_hawksbill_rockfall"
