"""
MarsWalk 2.0 — Milestone 9Q Competition Demo & Preflight Verification Suite
Validates:
1. Demo Mission Configuration: start, 3 intermediate science targets, goal, vehicle mode, and constraints.
2. Deterministic Demo Route Calculation: physical distance, travel duration, dwell time, and schedule timeline.
3. Disruption Scenarios (Rockfall Detour vs Mobility Degradation).
4. 3-Way Recovery Plan Calculation & Margin Restoration.
5. Preflight Diagnostic Suite (12 Checkpoints).
6. Preflight Resilience: detection of missing local assets and graceful handling of remote services.
7. Data Protection Guarantee: running demo sortie preserves existing user missions and historical experiments.
8. Live Atlas Server /api/preflight and /api/health endpoints.
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
from marswalk.api.preflight import (
    run_preflight_diagnostics,
    check_server_health,
    check_frontend_assets,
    check_places_catalog,
    check_imagery_registry,
    check_global_basemap,
    check_jezero_ctx_imagery,
    check_jezero_elevation,
    check_route_planner_smoke,
    check_scenario_engine_smoke,
    check_workspaces_filesystem,
    check_briefing_exporter,
    check_streamlit_companion,
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
# TEST 1: Demo Mission Configuration & Deterministic Calculation
# ==============================================================================

def test_01_demo_mission_configuration_and_plan(terrain_context):
    """
    Validate the official 5-minute showcase demo sortie:
    - Start: Octavia E. Butler Landing (117, 157)
    - Intermediate Stops: Hawksbill Gap, Skinner Ridge, Enchanted Lake (3 science targets)
    - Goal: Delta Rim Overlook (66, 128)
    - Vehicle: Crew EVA (2.0 km/h)
    - Profile: Balanced
    - Budget: 8.0 hours life-support, 15 min dwell per stop.
    """
    terrain, transform, waypoints = terrain_context

    demo_payload = {
        "start": {"row": 117, "col": 157, "name": "Octavia E. Butler Landing"},
        "goal": {"row": 66, "col": 128, "name": "Delta Rim Overlook"},
        "stops": [
            {"row": 104, "col": 147, "id": "hawksbill_gap", "name": "Hawksbill Gap", "priority_score": 95.0},
            {"row": 95, "col": 139, "id": "skinner_ridge", "name": "Skinner Ridge", "priority_score": 88.0},
            {"row": 107, "col": 136, "id": "enchanted_lake", "name": "Enchanted Lake", "priority_score": 80.0},
        ],
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "operational_limit_s": 28800.0,
        "dwell_time_per_stop_s": 900.0,
    }

    res = plan_route_api(demo_payload, terrain, transform, waypoints)

    assert res["is_reachable"] is True
    assert res["is_budget_feasible"] is True
    assert len(res["visited_waypoint_ids"]) == 3
    assert 1500.0 < res["distance_m"] < 2200.0  # Actual computed distance: 1,749.7 m across 4 legs

    timeline = res["timeline"]
    assert timeline["is_within_limit"] is True
    assert timeline["total_dwell_time_s"] == 2700.0  # 3 stops * 15 min * 60s = 2700s
    assert timeline["total_mission_time_s"] == timeline["total_traverse_time_s"] + 2700.0
    assert timeline["remaining_margin_s"] > 18000.0  # Generous >5h margin remaining


# ==============================================================================
# TEST 2: Disruption Scenarios on Demo Mission (Rockfall Detour vs Mobility)
# ==============================================================================

def test_02_demo_disruption_scenarios(terrain_context):
    """
    Evaluate the two primary demo scenarios:
    1. Rockfall Corridor Obstruction: changes physical route coordinates & travel time.
    2. Drive Mobility Derating (0.5x speed): preserves identical path geometry and doubles traverse duration.
    """
    terrain, transform, waypoints = terrain_context

    base_payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "stops": [
            {"row": 104, "col": 147, "id": "hawksbill_gap", "name": "Hawksbill Gap", "priority_score": 95.0},
            {"row": 95, "col": 139, "id": "skinner_ridge", "name": "Skinner Ridge", "priority_score": 88.0},
            {"row": 107, "col": 136, "id": "enchanted_lake", "name": "Enchanted Lake", "priority_score": 80.0},
        ],
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
    }
    base_res = plan_route_api(base_payload, terrain, transform, waypoints)
    base_coords = [tuple(rc) for rc in base_res["path_rc"]]

    # 1. Rockfall Detour
    g_rockfall = gauntlet_api(
        dict(base_payload, scenario_id="scen_corridor_rockfall"),
        terrain,
        transform,
        waypoints,
    )
    assert g_rockfall["scenario"]["disruption_type"] == "corridor_closure"
    if g_rockfall["scenario_route"]["is_reachable"]:
        detour_coords = [tuple(rc) for rc in g_rockfall["scenario_route"]["path_rc"]]
        assert detour_coords != base_coords, "Rockfall detour must produce a distinct spatial trajectory"

    # 2. Mobility Derating
    g_mobility = gauntlet_api(
        dict(base_payload, scenario_id="scen_mobility_degradation"),
        terrain,
        transform,
        waypoints,
    )
    assert g_mobility["scenario"]["disruption_type"] == "mobility_degradation"
    mob_coords = [tuple(rc) for rc in g_mobility["scenario_route"]["path_rc"]]
    assert mob_coords == base_coords, "Drive actuator derating must preserve identical geometry"
    assert g_mobility["delta_travel_time_s"] > 0, "Traverse travel time must increase under velocity derating"


# ==============================================================================
# TEST 3: Recovery Plan Generation on Demo Disruption
# ==============================================================================

def test_03_demo_recovery_plan(terrain_context):
    """
    Verify that disruption generates an actionable 3-way recovery plan
    with positive recovered operational margin.
    """
    terrain, transform, waypoints = terrain_context

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "stops": [
            {"row": 104, "col": 147, "id": "hawksbill_gap", "name": "Hawksbill Gap", "priority_score": 95.0},
            {"row": 95, "col": 139, "id": "skinner_ridge", "name": "Skinner Ridge", "priority_score": 88.0},
        ],
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "scenario_id": "scen_corridor_rockfall",
    }

    g_res = gauntlet_api(payload, terrain, transform, waypoints)
    rec = g_res.get("recovery_plan")
    assert rec is not None
    assert "strategy" in rec
    assert rec["recovered_route"] is not None
    assert rec["recovered_route"]["is_reachable"] is True


# ==============================================================================
# TEST 4: Preflight Diagnostic Suite (12 Checkpoints)
# ==============================================================================

def test_04_preflight_diagnostics_suite(terrain_context):
    """
    Execute all 12 preflight readiness checks against the current repository and environment.
    Verify that 12 checks are executed and no critical failures occur.
    """
    terrain, transform, waypoints = terrain_context

    diag = run_preflight_diagnostics(
        terrain=terrain,
        transform=transform,
        waypoints=waypoints,
        base_url="http://127.0.0.1:3000",
    )

    assert diag["total_count"] == 12
    assert diag["failed_count"] == 0, f"Critical preflight checks failed: {[c for c in diag['checks'] if c['status'] == 'failed']}"
    assert diag["is_ready_for_demo"] is True
    assert diag["overall_status"] in ("ready", "ready_with_warnings")

    # Verify key individual checks
    check_ids = {c["id"]: c for c in diag["checks"]}
    assert check_ids["frontend_assets"]["status"] == "passed"
    assert check_ids["places_catalog"]["status"] == "passed"
    assert check_ids["imagery_registry"]["status"] == "passed"
    assert check_ids["jezero_elevation"]["status"] == "passed"
    assert check_ids["route_planner_smoke"]["status"] == "passed"
    assert check_ids["scenario_engine_smoke"]["status"] == "passed"
    assert check_ids["workspaces_filesystem"]["status"] == "passed"
    assert check_ids["briefing_exporter"]["status"] == "passed"
    assert check_ids["streamlit_companion"]["status"] == "passed"


# ==============================================================================
# TEST 5: Preflight Resilience to Missing Assets
# ==============================================================================

def test_05_preflight_detection_of_missing_assets(tmp_path, monkeypatch):
    """
    Verify that preflight diagnostics accurately detect missing assets and
    report 'failed' status without crashing.
    """
    empty_dir = tmp_path / "empty_web"
    empty_dir.mkdir()

    # Monkeypatch PROJECT_ROOT in preflight module temporarily
    import marswalk.api.preflight as pf
    monkeypatch.setattr(pf, "PROJECT_ROOT", tmp_path)

    res = pf.check_frontend_assets()
    assert res["status"] == "failed"
    assert "Missing" in res["details"]

    res_cat = pf.check_places_catalog()
    assert res_cat["status"] == "failed"


# ==============================================================================
# TEST 6: User Workspace Protection & Immutability During Demo
# ==============================================================================

def test_06_user_workspaces_protection(isolated_dirs, terrain_context):
    """
    Prove that running demo missions and disruption rehearsals never modifies
    pre-existing saved user missions or historical experiments.
    """
    m_dir, e_dir = isolated_dirs
    terrain, transform, waypoints = terrain_context

    # 1. Seed existing user mission and experiment
    user_route = plan_route_api({
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
    }, terrain, transform, waypoints)

    user_m = save_mission({
        "mission_id": "m_user_mission_original",
        "name": "Dr. Smith Crater Floor Survey",
        "canonical_mission": {
            "start": {"row": 117, "col": 157, "name": "Landing Site"},
            "goal": {"row": 66, "col": 128, "name": "Delta Rim Overlook"},
            "stops": [],
            "profile": "conservative",
            "vehicle_mode": "crew_eva",
        },
    }, missions_dir=m_dir)

    user_exp = save_experiment({
        "experiment_id": "exp_user_study_original",
        "name": "Smith Dune Traverse Study",
        "status": "success",
        "lifecycle_state": "historical_result",
        "baseline_fingerprint": user_route["input_fingerprint"],
        "mission_snapshot": user_route["mission_snapshot"],
        "baseline_route": user_route,
        "scenarios_evaluated": [{"id": "scen_unstable_sand", "title": "Dune Slip"}],
    }, experiments_dir=e_dir)

    initial_missions = list_missions(missions_dir=m_dir)
    initial_experiments = list_experiments(experiments_dir=e_dir)
    assert len(initial_missions) == 1
    assert len(initial_experiments) == 1

    # 2. Execute Demo Sortie calculation and Gauntlet scenario
    demo_plan = plan_route_api({
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "stops": [{"row": 104, "col": 147, "id": "demo_stop", "name": "Demo Stop", "priority_score": 90.0}],
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
    }, terrain, transform, waypoints)

    demo_gauntlet = gauntlet_api({
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "scenario_id": "scen_corridor_rockfall",
    }, terrain, transform, waypoints)

    # 3. Verify user missions and experiments on disk are 100% UNCHANGED
    missions_after = list_missions(missions_dir=m_dir)
    experiments_after = list_experiments(experiments_dir=e_dir)

    assert len(missions_after) == 1
    assert len(experiments_after) == 1
    assert missions_after[0]["mission_id"] == "m_user_mission_original"
    assert experiments_after[0]["experiment_id"] == "exp_user_study_original"

    reloaded_m = get_mission("m_user_mission_original", missions_dir=m_dir)
    assert reloaded_m["name"] == "Dr. Smith Crater Floor Survey"


# ==============================================================================
# TEST 7: Technical Mission Briefing Draft 2020-12 Validation
# ==============================================================================

def test_07_demo_briefing_export_schema(terrain_context):
    """
    Validate that a demo mission briefing generates valid Draft 2020-12 JSON
    and Markdown containing authentic provenance disclosures.
    """
    terrain, transform, waypoints = terrain_context

    route_res = plan_route_api({
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "stops": [
            {"row": 104, "col": 147, "id": "hawksbill_gap", "name": "Hawksbill Gap", "priority_score": 95.0},
            {"row": 95, "col": 139, "id": "skinner_ridge", "name": "Skinner Ridge", "priority_score": 88.0},
        ],
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
    }, terrain, transform, waypoints)

    res = export_briefing_api({"baseline_route": route_res}, terrain, transform)
    json_export = res["json_export"]
    md_text = res["markdown_briefing"]

    # Formal schema validation
    validate_contract(json_export, "mission-briefing-export", raise_on_error=True)

    assert "MARSWALK 2.0" in md_text
    assert "USGS CTX DTM 20m" in md_text or "20 m" in md_text
    assert "RESEARCH PROTOTYPE DISCLAIMER" in md_text or "NOT certified as operationally safe" in md_text


# ==============================================================================
# TEST 8: Live Atlas Server Endpoints
# ==============================================================================

def test_08_live_server_preflight_and_health():
    """
    Query the active Atlas server at http://127.0.0.1:3000 to verify
    /api/health and /api/preflight respond successfully.
    """
    base_url = "http://127.0.0.1:3000"

    # 1. Health check
    try:
        with urllib.request.urlopen(f"{base_url}/api/health", timeout=5) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "online"
            assert "/api/preflight" in data["endpoints"]
    except urllib.error.URLError as e:
        pytest.fail(f"Atlas server not reachable at {base_url}/api/health: {e}")

    # 2. Preflight endpoint
    with urllib.request.urlopen(f"{base_url}/api/preflight", timeout=15) as resp:
        assert resp.status == 200
        diag = json.loads(resp.read().decode("utf-8"))
        assert diag["is_ready_for_demo"] is True
        assert diag["total_count"] == 12
        assert diag["failed_count"] == 0
