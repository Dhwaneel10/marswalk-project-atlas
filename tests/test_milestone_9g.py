"""
Milestone 9G Functional Verification Suite:
- Apollo EVA travel time calculation & uncertainty bounds
- Multi-stop sequential traverse planning
- Dynamic Gauntlet corridor rockfall with verified lateral detour
- Honest non-intersecting Gauntlet scenario reporting ("No Route Impact")
- 12 verified NASA Mars 2020 science targets inside Jezero DTM
- Terrain layer data contracts & geodetic coordinate validation
"""

import json
import math
import os
import pytest
import rasterio

from marswalk.core.terrain import load_and_process_terrain
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    plan_route,
    plan_sequential_multistop_route,
    calculate_traverse_time,
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
MISSION_DATA_JSON = os.path.join(REPO_ROOT, "web", "data", "jezero_mission_data.json")


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


def test_apollo_traverse_time_calculation():
    """Verify Apollo EVA-calibrated speed model (2.0 km/h baseline, 1.5-2.5 km/h range)."""
    # Test flat 1439.9 m cost
    cost = 1439.9
    t_nom, t_min, t_max, formatted = calculate_traverse_time(cost)

    # 1439.9 / (2000/3600) = 2591.8 s ~ 43.2 min
    assert 2580 < t_nom < 2605
    assert 2060 < t_min < 2085  # at 2.5 km/h -> faster -> minimum time
    assert 3440 < t_max < 3470  # at 1.5 km/h -> slower -> maximum time

    assert t_min < t_nom < t_max
    assert "43 min" in formatted
    assert "35–58 min" in formatted or "35-58 min" in formatted or "range: 35" in formatted

    # Zero cost
    t0, tm0, tx0, fmt0 = calculate_traverse_time(0.0)
    assert fmt0 == "—"

    # Infinite cost
    ti, tmi, txi, fmti = calculate_traverse_time(float("inf"))
    assert fmti == "—"


def test_12_verified_jezero_waypoints_data(terrain_env):
    """Verify exactly 12 authentic science waypoints with PDS citations and valid elevations."""
    wps = terrain_env["waypoints"]
    terrain = terrain_env["terrain"]
    assert len(wps) == 12

    expected_ids = {
        "octavia_butler_landing",
        "three_forks",
        "hawksbill_gap",
        "kodiak_butte",
        "delta_rim_overlook",
        "neretva_margin",
        "seitah_dunes",
        "artuby_ridge",
        "skinner_ridge",
        "enchanted_lake",
        "belva_crater_overlook",
        "dourbes_floor",
    }
    actual_ids = {w.id for w in wps}
    assert expected_ids == actual_ids

    for w in wps:
        r, c = w.rc
        assert 0 <= r < terrain.height
        assert 0 <= c < terrain.width
        assert not terrain.invalid_mask[r, c], f"Waypoint {w.id} falls on invalid NoData mask"
        elev = float(terrain.elevation[r, c])
        assert -2650.0 < elev < -2400.0, f"Waypoint {w.id} has unexpected elevation {elev}"
        assert len(w.pds_citation) > 10, f"Waypoint {w.id} missing PDS citation"
        assert len(w.crism_signature) > 10, f"Waypoint {w.id} missing CRISM signature"


def test_sequential_multistop_traverse(terrain_env):
    """Verify sequential multi-stop continuous traverse connecting user-ordered stops."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    waypoints = terrain_env["waypoints"]

    # Plan 3 intermediate stops: Butler Landing -> Three Forks -> Hawksbill Gap -> Delta Rim
    payload = {
        "start": {"row": 117, "col": 157},
        "stops": [
            {"row": 153, "col": 123, "id": "three_forks", "priority_score": 75.0},
            {"row": 136, "col": 91, "id": "hawksbill_gap", "priority_score": 95.0},
        ],
        "goal": {"row": 66, "col": 128},
        "profile": "conservative",
    }

    result = plan_route_api(payload, terrain, transform, waypoints)

    assert result["is_reachable"] is True
    assert result["is_budget_feasible"] is True
    assert len(result["path_rc"]) > 100
    assert result["path_rc"][0] == [117, 157]
    assert result["path_rc"][-1] == [66, 128]
    assert result["distance_m"] > 2500.0
    assert ("min" in result["formatted_travel_time"]) or ("h" in result["formatted_travel_time"])
    assert "range:" in result["formatted_travel_time"]
    assert "three_forks" in result["visited_waypoint_ids"]
    assert "hawksbill_gap" in result["visited_waypoint_ids"]
    assert result["science_score"] == 170.0


def test_dynamic_gauntlet_corridor_rockfall_intersection(terrain_env):
    """Verify that scen_corridor_rockfall intersects the baseline route and forces an authentic detour."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    waypoints = terrain_env["waypoints"]

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "conservative",
        "scenario_id": "scen_corridor_rockfall",
    }

    res = gauntlet_api(payload, terrain, transform, waypoints)

    assert res["scenario"]["id"] == "scen_corridor_rockfall"
    assert res["scenario"]["intersects_baseline"] is True
    assert res["delta_distance_m"] > 0.0, f"Expected positive detour distance, got {res['delta_distance_m']}"
    assert res["delta_cost"] > 0.0
    assert res["delta_travel_time_s"] > 0.0
    assert len(res["scenario"]["coordinates_3d"]) > 0
    assert res["scenario"]["center_rc"] is not None

    # Both baseline and scenario routes must be distinct valid paths
    b_path = res["baseline_route"]["path_rc"]
    s_path = res["scenario_route"]["path_rc"]
    assert len(b_path) > 10
    assert len(s_path) > 10
    assert b_path != s_path
    assert "Detour Active" in res["headline"] or "Replanning Successful" in res["headline"]


def test_distant_gauntlet_rockfall_honest_no_impact(terrain_env):
    """Verify that a distant scenario reports honest 'No Route Impact' when not intersecting."""
    terrain = terrain_env["terrain"]
    transform = terrain_env["transform"]
    waypoints = terrain_env["waypoints"]

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "conservative",
        "scenario_id": "scen_distant_rockfall",
    }

    res = gauntlet_api(payload, terrain, transform, waypoints)

    assert res["scenario"]["id"] == "scen_distant_rockfall"
    assert res["scenario"]["intersects_baseline"] is False
    assert res["delta_distance_m"] == 0.0
    assert res["delta_cost"] == 0.0
    assert res["delta_travel_time_s"] == 0.0
    assert "No Route Impact" in res["headline"]
    assert "does not intersect the active traverse corridor" in res["detail"]


def test_mission_data_geographic_bounds_contract():
    """Verify that jezero_mission_data.json has bounds.geographic preventing NaN coordinates."""
    with open(MISSION_DATA_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "bounds" in data
    assert "geographic" in data["bounds"]
    geo = data["bounds"]["geographic"]
    assert "min_lon_deg" in geo
    assert "max_lon_deg" in geo
    assert "min_lat_deg" in geo
    assert "max_lat_deg" in geo
    assert not math.isnan(geo["min_lon_deg"])
    assert not math.isnan(geo["max_lon_deg"])
    assert 77.3 < geo["min_lon_deg"] < 77.45
    assert 77.45 < geo["max_lon_deg"] < 77.5
    assert 18.3 < geo["min_lat_deg"] < 18.45
    assert 18.45 < geo["max_lat_deg"] < 18.5
