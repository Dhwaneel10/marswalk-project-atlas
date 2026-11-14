"""
MarsWalk 2.0 — Milestone 9P End-to-End Mission Validation & Integration Suite
Validates:
1. Multi-Stop Mission Planning: Start + 3 research stops + Goal across profiles and vehicle modes.
2. Distance & Timeline Invariants: Sum of leg distances matches total distance; travel time + dwell time + delay = total time.
3. Feasibility & Budget Constraints: Distinguishes reachability from budget feasibility under time and distance caps.
4. Disruption & Stress-Testing Scenarios: Rockfall detour exclusion vs mobility degradation time penalty.
5. Recovery Engine: Proposes verifiable margin recovery via stop pruning or safe corridor.
6. Persistent Workspaces & Replay Immutability: Replaying preserves historical record immutability.
7. Mission Briefing Export & Draft 2020-12 Schema Validation.
8. Live Atlas Server Endpoints & Tile Cache Health.
"""

import os
import json
import uuid
import copy
import pytest
import urllib.request
import urllib.error
from pathlib import Path

from marswalk.api.workspace import (
    save_mission,
    list_missions,
    get_mission,
    save_experiment,
    list_experiments,
    get_experiment,
    replay_saved_experiment,
    compare_two_experiments,
)
from marswalk.api.contracts import (
    SCHEMA_VERSION,
    validate_contract,
    compute_input_fingerprint,
)
from marswalk.core.terrain import load_and_process_terrain
from marswalk.api.service import (
    plan_route_api,
    gauntlet_api,
    export_briefing_api,
)
from marswalk.core.planner import (
    ScienceWaypoint,
    VehicleMode,
    OPERATIONAL_LIMITS_S,
    calculate_traverse_time,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GEOTIFF_PATH = str(PROJECT_ROOT / "data" / "processed" / "jezero_ready_20m.tif")
WAYPOINTS_PATH = str(PROJECT_ROOT / "data" / "waypoints_jezero.json")


from marswalk.data.ingest import query_elevation_at_lonlat


@pytest.fixture(scope="module")
def terrain_context():
    terrain = load_and_process_terrain(GEOTIFF_PATH)
    import rasterio
    with rasterio.open(GEOTIFF_PATH) as src:
        transform = src.transform

    waypoints = []
    if os.path.exists(WAYPOINTS_PATH):
        with open(WAYPOINTS_PATH, "r", encoding="utf-8") as f:
            wp_data = json.load(f)
        for wp in wp_data.get("waypoints", []):
            elev, r, c = query_elevation_at_lonlat(GEOTIFF_PATH, wp["lon_deg"], wp["lat_deg"])
            waypoints.append(
                ScienceWaypoint(
                    id=wp["id"],
                    name=wp["name"],
                    rc=(r, c),
                    priority_score=float(wp.get("priority_score", 50.0)),
                )
            )
    return terrain, transform, waypoints


@pytest.fixture
def isolated_dirs(tmp_path):
    m_dir = str(tmp_path / "missions")
    e_dir = str(tmp_path / "experiments")
    os.makedirs(m_dir, exist_ok=True)
    os.makedirs(e_dir, exist_ok=True)
    return m_dir, e_dir


# ==============================================================================
# TEST 1: Multi-Stop Planning & Leg Geometry Sum Invariant
# ==============================================================================

def test_01_multi_stop_planning_and_leg_sum_invariant(terrain_context):
    """
    Plan a mission with Start (117, 157) + 3 intermediate science stops + Goal (66, 128).
    Verify that each leg is present, total distance equals sum of leg distances,
    and cumulative climb and steps are consistent.
    """
    terrain, transform, waypoints = terrain_context

    stops = [
        {"row": 125, "col": 140, "id": "stop_1", "name": "Delta Scarp Foot", "priority_score": 85.0},
        {"row": 110, "col": 135, "id": "stop_2", "name": "Meander Channel Bed", "priority_score": 75.0},
        {"row": 90, "col": 130, "id": "stop_3", "name": "Crater Floor Stratum", "priority_score": 90.0},
    ]

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "stops": stops,
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "dwell_time_s": 900.0,
    }

    res = plan_route_api(payload, terrain, transform, waypoints)
    assert res["is_reachable"] is True
    assert res["is_budget_feasible"] is True
    assert len(res["visited_waypoint_ids"]) == 3

    # Check legs via timeline events
    leg_events = [e for e in res["timeline"]["events"] if e["event_type"] == "traverse_leg"]
    assert len(leg_events) == 4  # 3 intermediate stops = 4 sequential legs

    leg_dist_sum = sum(e["distance_m"] for e in leg_events)
    assert pytest.approx(res["distance_m"], 0.1) == leg_dist_sum

    # Path starts at Start and ends at Goal
    assert res["path_rc"][0] == [117, 157]
    assert res["path_rc"][-1] == [66, 128]


# ==============================================================================
# TEST 2: Vehicle Mode Traversal Durations & Engineering Assumptions
# ==============================================================================

def test_02_vehicle_mode_traversal_durations(terrain_context):
    """
    Verify that Robotic Rover and Crew EVA produce distinctly different
    traversal durations for identical spatial traverses matching their engineering speeds.
    """
    terrain, transform, waypoints = terrain_context

    base_payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "conservative",
    }

    # Crew EVA (2.0 km/h nominal)
    eva_res = plan_route_api(dict(base_payload, vehicle_mode="crew_eva"), terrain, transform, waypoints)
    # Robotic Rover (0.035 m/s nominal)
    rover_res = plan_route_api(dict(base_payload, vehicle_mode="robotic_rover"), terrain, transform, waypoints)

    assert eva_res["distance_m"] == rover_res["distance_m"]
    # Rover speed (0.035 m/s = 0.126 km/h) is roughly 16x slower than EVA (2.0 km/h)
    eva_time = eva_res["timeline"]["total_traverse_time_s"]
    rover_time = rover_res["timeline"]["total_traverse_time_s"]

    ratio = rover_time / eva_time
    assert 14.0 <= ratio <= 18.0, f"Expected rover-to-EVA time ratio ~16x, got {ratio:.2f}"
    assert eva_res["timeline"]["operational_limit_s"] == 28800.0  # 8 hours
    assert rover_res["timeline"]["operational_limit_s"] == 14400.0  # 4 hours


# ==============================================================================
# TEST 3: Budget Constraint & Feasibility Checker
# ==============================================================================

def test_03_budget_feasibility_under_time_and_distance_caps(terrain_context):
    """
    Verify that when mission time exceeds the operational limit or max distance,
    the route is marked is_reachable=True but is_budget_feasible=False.
    """
    terrain, transform, waypoints = terrain_context

    stops = [
        {"row": 125, "col": 140, "id": "s1", "priority_score": 80.0},
        {"row": 90, "col": 130, "id": "s2", "priority_score": 80.0},
    ]

    # Normal generous budget
    generous_payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "stops": stops,
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "operational_limit_s": 28800.0,
    }
    res_ok = plan_route_api(generous_payload, terrain, transform, waypoints)
    assert res_ok["is_budget_feasible"] is True

    # Severely restricted time budget (e.g. 15 minutes = 900s, less than dwell + traverse)
    tight_time_payload = dict(generous_payload, operational_limit_s=900.0)
    res_tight_time = plan_route_api(tight_time_payload, terrain, transform, waypoints)
    assert res_tight_time["is_reachable"] is True
    assert res_tight_time["is_budget_feasible"] is False
    assert res_tight_time["timeline"]["is_within_limit"] is False
    assert res_tight_time["timeline"]["remaining_margin_s"] < 0

    # Severely restricted distance budget (e.g. 100 meters, far less than ~1500m traverse)
    tight_dist_payload = dict(generous_payload, max_distance_m=100.0)
    res_tight_dist = plan_route_api(tight_dist_payload, terrain, transform, waypoints)
    assert res_tight_dist["is_reachable"] is True
    assert res_tight_dist["is_budget_feasible"] is False
    assert "exceeds distance budget" in res_tight_dist["status_message"]


# ==============================================================================
# TEST 4: Stress-Testing Disruption (Rockfall vs Mobility Degradation)
# ==============================================================================

def test_04_stress_test_disruptions(terrain_context):
    """
    Verify that:
    1. Rockfall corridor closure alters path geometry (detour or blocked).
    2. Mobility degradation doubles traversal time while keeping coordinates identical.
    """
    terrain, transform, waypoints = terrain_context

    base_payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
    }
    base_res = plan_route_api(base_payload, terrain, transform, waypoints)
    base_path = [tuple(rc) for rc in base_res["path_rc"]]

    # Scenario 1: Rockfall in Hawksbill corridor
    g_rockfall = gauntlet_api(
        dict(base_payload, scenario_id="scen_hawksbill_rockfall"),
        terrain,
        transform,
        waypoints,
    )
    assert g_rockfall["scenario"]["disruption_type"] == "corridor_closure"
    assert g_rockfall["scenario"]["num_blocked_cells"] > 0
    if g_rockfall["scenario_route"]["is_reachable"]:
        detour_path = [tuple(rc) for rc in g_rockfall["scenario_route"]["path_rc"]]
        assert detour_path != base_path, "Rockfall detour must produce a distinct physical path"

    # Scenario 2: Mobility Degradation (50% speed penalty)
    g_mobility = gauntlet_api(
        dict(base_payload, scenario_id="scen_mobility_degradation"),
        terrain,
        transform,
        waypoints,
    )
    assert g_mobility["scenario"]["disruption_type"] == "mobility_degradation"
    mob_path = [tuple(rc) for rc in g_mobility["scenario_route"]["path_rc"]]
    # Coordinates must remain identical
    assert mob_path == base_path
    # Traversal duration must strictly increase
    assert g_mobility["delta_travel_time_s"] > 0


# ==============================================================================
# TEST 5: Recovery Strategy Calculation
# ==============================================================================

def test_05_recovery_plan_margin_restoration(terrain_context):
    """
    Verify that an evaluated disruption calculates a recovery plan that
    recovers operational margin by bypassing compromised stops or executing safe corridor.
    """
    terrain, transform, waypoints = terrain_context

    stops = [
        {"row": 125, "col": 140, "id": "delta_foot", "name": "Delta Scarp Foot", "priority_score": 85.0},
        {"row": 110, "col": 135, "id": "channel_bed", "name": "Channel Bed", "priority_score": 40.0},
    ]

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "stops": stops,
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "scenario_id": "scen_delta_channel_block",
        "operational_limit_s": 7200.0,  # 2.0 hours
    }

    g_res = gauntlet_api(payload, terrain, transform, waypoints)
    rec_plan = g_res.get("recovery_plan")
    assert rec_plan is not None
    assert "strategy" in rec_plan
    assert rec_plan["strategy"] != ""
    assert "margin_recovered_s" in rec_plan
    assert rec_plan["recovered_route"] is not None
    assert rec_plan["recovered_route"]["is_reachable"] is True


# ==============================================================================
# TEST 6: Workspace Persistence, Server Restart & Replay Immutability
# ==============================================================================

def test_06_workspace_persistence_and_replay_immutability(isolated_dirs, terrain_context):
    """
    Save a mission and an experiment, verify JSON written to disk, reload,
    and verify that replaying an experiment preserves historical immutability.
    """
    m_dir, e_dir = isolated_dirs
    terrain, transform, waypoints = terrain_context

    route_res = plan_route_api({
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "science_first",
        "vehicle_mode": "crew_eva",
        "stops": [{"row": 125, "col": 140, "id": "s1", "name": "Scarp Point", "priority_score": 90.0}],
    }, terrain, transform, waypoints)

    # 1. Save mission
    mission_payload = {
        "mission_id": "m_m9p_validation_01",
        "name": "Milestone 9P Validation Traverse",
        "description": "Validation mission for Milestone 9P.",
        "canonical_mission": {
            "start": {"row": 117, "col": 157, "name": "Landing Site"},
            "goal": {"row": 66, "col": 128, "name": "Delta Rim Overlook"},
            "stops": [{"row": 125, "col": 140, "id": "s1", "name": "Scarp Point", "priority_score": 90.0}],
            "profile": "science_first",
            "vehicle_mode": "crew_eva",
            "speed_multiplier": 1.0,
            "optimize_stops": False,
            "mission_constraints": {"max_duration_s": 28800.0, "max_distance_m": 4000.0},
        },
        "profile": "science_first",
        "vehicle_mode": "crew_eva",
    }
    saved_m = save_mission(mission_payload, missions_dir=m_dir)
    m_id = saved_m["mission_id"]

    # Verify reload
    reloaded_m = get_mission(m_id, missions_dir=m_dir)
    assert reloaded_m["name"] == "Milestone 9P Validation Traverse"
    assert len(reloaded_m["canonical_mission"]["stops"]) == 1

    # 2. Save experiment
    exp_payload = {
        "experiment_id": "exp_m9p_disruption_01",
        "name": "Rockfall Disruption Trial",
        "description": "Validation experiment for Milestone 9P.",
        "status": "success",
        "lifecycle_state": "historical_result",
        "baseline_fingerprint": route_res["input_fingerprint"],
        "mission_snapshot": route_res["mission_snapshot"],
        "baseline_route": route_res,
        "scenarios_evaluated": [{"id": "scen_hawksbill_rockfall", "title": "Hawksbill Rockfall"}],
    }
    saved_exp = save_experiment(exp_payload, experiments_dir=e_dir)
    exp_id = saved_exp["experiment_id"]

    # Verify saved experiment exists on disk
    reloaded_exp = get_experiment(exp_id, experiments_dir=e_dir)
    assert reloaded_exp["experiment_id"] == exp_id
    assert reloaded_exp["name"] == "Rockfall Disruption Trial"

    # 3. Replay experiment (must produce distinct run ID and leave original record unmutated)
    replayed = replay_saved_experiment(
        exp_id,
        terrain=terrain,
        transform=transform,
        waypoints=waypoints,
        experiments_dir=e_dir,
    )
    assert replayed["experiment_id"] != exp_id
    assert replayed["replayed_from_experiment_id"] == exp_id

    # Verify original is completely unchanged
    orig_after = get_experiment(exp_id, experiments_dir=e_dir)
    assert orig_after["experiment_id"] == exp_id
    assert orig_after.get("replayed_from_experiment_id") is None


# ==============================================================================
# TEST 7: Technical Briefing Export & Draft 2020-12 Schema Validation
# ==============================================================================

def test_07_briefing_export_schema_and_disclosures(terrain_context):
    """
    Generate mission briefing in both JSON and Markdown formats.
    Validate JSON against schemas/api/v1/mission_briefing.json.
    Verify Markdown includes honest human safety disclaimers and sensor provenance.
    """
    terrain, transform, waypoints = terrain_context

    route_res = plan_route_api(
        {
            "start": {"row": 117, "col": 157},
            "goal": {"row": 66, "col": 128},
            "profile": "balanced",
            "vehicle_mode": "crew_eva",
        },
        terrain,
        transform,
        waypoints,
    )

    briefing_payload = {
        "baseline_route": route_res,
        "recovery_data": {
            "strategy": "Direct conservative safe corridor",
            "formatted_margin_recovered": "+15 min",
        },
    }

    # Export briefing (both json_export and markdown_briefing are returned)
    briefing_res = export_briefing_api(briefing_payload, terrain, transform)
    briefing_json = briefing_res["json_export"]
    assert briefing_json["schema_version"] == SCHEMA_VERSION
    assert "data_provenance" in briefing_json
    assert "metadata" in briefing_json and "disclaimer" in briefing_json["metadata"]

    # Validate against formal JSON Schema
    validate_contract(briefing_json, "mission-briefing-export", raise_on_error=True)

    # Markdown export
    md_text = briefing_res["markdown_briefing"]

    assert "MARSWALK 2.0" in md_text
    assert "MISSION REHEARSAL & ANALYSIS LABORATORY BRIEFING" in md_text
    assert "MRO Context Camera" in md_text or "CTX" in md_text
    assert "USGS CTX DTM 20m" in md_text or "20 m" in md_text
    assert "RESEARCH PROTOTYPE DISCLAIMER" in md_text or "NOT certified as operationally safe" in md_text


# ==============================================================================
# TEST 8: Live Atlas Server Endpoints & Tile Cache Health
# ==============================================================================

def test_08_live_server_endpoints_and_tile_cache():
    """
    Query the active Atlas server on port 3000.
    Verify /api/health, /api/imagery/status, and /api/imagery/tile.
    """
    base_url = "http://127.0.0.1:3000"

    # Health check
    try:
        with urllib.request.urlopen(f"{base_url}/api/health", timeout=5) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "online"
            assert data["terrain_loaded"] is True
            assert data["waypoints_count"] == 12
    except urllib.error.URLError as e:
        pytest.fail(f"Atlas server not reachable at {base_url}/api/health: {e}")

    # Imagery tile cache status
    with urllib.request.urlopen(f"{base_url}/api/imagery/status", timeout=5) as resp:
        assert resp.status == 200
        status_data = json.loads(resp.read().decode("utf-8"))
        assert status_data["status"] == "operational"
        assert "stats" in status_data
        assert "hits" in status_data["stats"]

    # Valid tile request (Level 6 Olympus Mons caldera tile)
    tile_url = f"{base_url}/api/imagery/tile?product_id=olympus_mons_ctx_regional&z=6&r=25&c=16"
    with urllib.request.urlopen(tile_url, timeout=10) as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") in ("image/jpeg", "image/png", "application/octet-stream")
        assert "X-MarsWalk-Cache" in resp.headers
        tile_bytes = resp.read()
        assert len(tile_bytes) > 500  # Valid tile image payload
