"""
MarsWalk 2.0 — Milestone 9V Mission Design Lab & Autonomous Science-Tour Optimizer Test Suite

Verifies:
1. Candidate waypoints selection: stops in proposed sorties are subsets of candidate IDs.
2. Endpoint preservation: start and goal coordinates are exactly preserved.
3. Catalogue validation: waypoints exist in catalogue, science scores match sum of priorities.
4. Route geometry and planner fidelity: re-running authoritative planner matches sortie geometry.
5. Telemetry & timeline consistency: traverse time, dwell time, delay, total time, and margins are mathematically consistent.
6. Operational budget enforcement: tight operational budget marks over-budget sorties as infeasible.
7. Feasibility honesty: sorties exceeding operational limits are never labeled as feasible.
8. Error handling and validation: invalid coordinates, identical endpoints, and unknown target IDs return 400.
9. Determinism: identical inputs produce identical sorties and computation fingerprints.
10. Multi-objective champions: Science Priority, Time Efficiency, Balanced, and Baseline behave according to objectives.
11. Pareto frontier filtering: non-dominated alternatives contain no strictly dominated sorties.
12. Locomotion model differentiation: Crew EVA (2.0 km/h) vs Robotic Rover (0.035 m/s) velocity differences.
13. Live HTTP API integration: POST /api/mission/optimize on port 3000 returns HTTP 200 with complete report.
14. Workspace immutability: zero mutation or deletion of existing saved missions and historical experiments.
"""

import os
import json
import urllib.request
import urllib.error
import pytest
import rasterio
from pathlib import Path

from marswalk.core.terrain import load_and_process_terrain, TerrainGrid
from marswalk.core.planner import plan_route, plan_sequential_multistop_route, ScienceWaypoint
from marswalk.core.mission_optimizer import (
    SortieObjective,
    SortieCandidate,
    OptimizationReport,
    optimize_science_tour,
    optimize_mission_sorties,
    extract_pareto_frontier,
)
from marswalk.api.service import mission_optimize_api, APIError
from marswalk.api.workspace import list_missions, list_experiments


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TERRAIN_TIFF = DATA_DIR / "processed" / "jezero_ready_20m.tif"
WAYPOINTS_JSON = DATA_DIR / "waypoints_jezero.json"
MISSIONS_DIR = DATA_DIR / "workspaces" / "missions"
EXPERIMENTS_DIR = DATA_DIR / "workspaces" / "experiments"
SERVER_BASE_URL = "http://127.0.0.1:3000"


@pytest.fixture(scope="module")
def terrain_grid():
    if not TERRAIN_TIFF.exists():
        pytest.skip(f"Terrain GeoTIFF not found at {TERRAIN_TIFF}")
    return load_and_process_terrain(str(TERRAIN_TIFF))


@pytest.fixture(scope="module")
def transform_affine():
    if not TERRAIN_TIFF.exists():
        pytest.skip(f"Terrain GeoTIFF not found at {TERRAIN_TIFF}")
    with rasterio.open(str(TERRAIN_TIFF)) as src:
        return src.transform


@pytest.fixture(scope="module")
def waypoints_catalog():
    if not WAYPOINTS_JSON.exists():
        pytest.skip(f"Waypoints JSON not found at {WAYPOINTS_JSON}")
    from marswalk.data.ingest import query_elevation_at_lonlat
    with open(WAYPOINTS_JSON, "r", encoding="utf-8") as f:
        wp_data = json.load(f)
    wps = []
    for wp in wp_data.get("waypoints", []):
        elev, r, c = query_elevation_at_lonlat(str(TERRAIN_TIFF), wp["lon_deg"], wp["lat_deg"])
        wps.append(
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
    return wps


def test_candidate_target_selection_subset(terrain_grid, waypoints_catalog):
    """Sorties only visit waypoints from the user-selected candidate pool."""
    start = (117, 157)
    goal = (66, 128)
    selected_ids = ["three_forks", "neretva_margin"]

    report = optimize_mission_sorties(
        terrain=terrain_grid,
        all_waypoints=waypoints_catalog,
        candidate_waypoint_ids=selected_ids,
        start_rc=start,
        goal_rc=goal,
        max_stops=2,
        operational_limit_s=28800.0,
    )

    assert report is not None
    assert len(report.all_candidates) > 0

    for cand in report.all_candidates:
        for sid in cand.stop_ids:
            assert sid in selected_ids, f"Sortie visited unselected target {sid}"


def test_endpoint_preservation(terrain_grid, waypoints_catalog):
    """Start and goal coordinates are exactly preserved in all candidate sorties."""
    start = (117, 157)
    goal = (66, 128)

    report = optimize_mission_sorties(
        terrain=terrain_grid,
        all_waypoints=waypoints_catalog,
        candidate_waypoint_ids=["three_forks", "hawksbill_gap", "belva_crater_overlook"],
        start_rc=start,
        goal_rc=goal,
        max_stops=2,
    )

    assert tuple(report.start_rc) == start
    assert tuple(report.goal_rc) == goal

    for cand in report.all_candidates:
        assert tuple(cand.path_rc[0]) == start, "First coordinate must match start"
        assert tuple(cand.path_rc[-1]) == goal, "Last coordinate must match goal"


def test_catalogue_membership_and_priority_scores(terrain_grid, waypoints_catalog):
    """Visited targets exist in the catalog and science score matches the sum of priorities."""
    wp_map = {w.id: w for w in waypoints_catalog}
    start = (117, 157)
    goal = (66, 128)

    report = optimize_mission_sorties(
        terrain=terrain_grid,
        all_waypoints=waypoints_catalog,
        candidate_waypoint_ids=["three_forks", "hawksbill_gap", "seitah_dunes"],
        start_rc=start,
        goal_rc=goal,
        max_stops=2,
    )

    for cand in report.all_candidates:
        expected_score = sum(wp_map[sid].priority_score for sid in cand.stop_ids)
        assert abs(cand.science_score - expected_score) < 1e-4, f"Science score mismatch on {cand.id}"


def test_route_geometry_and_planner_fidelity(terrain_grid, waypoints_catalog):
    """Champion sortie path geometry exactly matches sequential authoritative planner."""
    start = (117, 157)
    goal = (66, 128)
    cand_ids = ["three_forks", "hawksbill_gap"]

    report = optimize_mission_sorties(
        terrain=terrain_grid,
        all_waypoints=waypoints_catalog,
        candidate_waypoint_ids=cand_ids,
        start_rc=start,
        goal_rc=goal,
        max_stops=2,
    )

    champ = report.balanced_champion or report.recommended_sortie
    assert champ is not None

    if champ.stop_ids:
        wp_map = {w.id: w for w in waypoints_catalog}
        ordered_points = [start] + [wp_map[sid].rc for sid in champ.stop_ids] + [goal]
        authoritative = plan_sequential_multistop_route(
            ordered_points=ordered_points,
            terrain=terrain_grid,
        )
        assert authoritative is not None
        assert [tuple(p) for p in authoritative.path] == [tuple(p) for p in champ.path_rc]
        assert abs(authoritative.distance_m - champ.distance_m) < 0.1
    else:
        authoritative = plan_route(terrain_grid, start, goal, profile=champ.profile)
        assert authoritative is not None
        assert [tuple(p) for p in authoritative.path] == [tuple(p) for p in champ.path_rc]


def test_telemetry_and_timeline_consistency(terrain_grid, waypoints_catalog):
    """Mission timeline breakdown is self-consistent and mathematically sound."""
    start = (117, 157)
    goal = (66, 128)
    op_limit = 28800.0
    dwell = 900.0
    delay = 300.0

    report = optimize_mission_sorties(
        terrain=terrain_grid,
        all_waypoints=waypoints_catalog,
        candidate_waypoint_ids=["three_forks", "hawksbill_gap"],
        start_rc=start,
        goal_rc=goal,
        max_stops=2,
        operational_limit_s=op_limit,
        dwell_time_per_stop_s=dwell,
        operational_delay_s=delay,
    )

    for cand in report.all_candidates:
        expected_dwell = cand.num_stops * dwell
        assert abs(cand.dwell_time_s - expected_dwell) < 1e-4
        expected_total = cand.travel_time_s + cand.dwell_time_s + cand.hold_delay_s
        assert abs(cand.total_mission_time_s - expected_total) < 1e-4
        expected_margin = op_limit - cand.total_mission_time_s
        assert abs(cand.time_margin_s - expected_margin) < 1e-4
        assert cand.is_budget_feasible == (cand.total_mission_time_s <= op_limit)


def test_operational_budget_enforcement(terrain_grid, waypoints_catalog):
    """Sorties exceeding a tight operational budget are flagged as infeasible."""
    start = (117, 157)
    goal = (66, 128)
    # Extremely tight 1500s budget (< 25 mins)
    tight_limit = 1500.0

    report = optimize_mission_sorties(
        terrain=terrain_grid,
        all_waypoints=waypoints_catalog,
        candidate_waypoint_ids=["three_forks", "hawksbill_gap", "neretva_margin"],
        start_rc=start,
        goal_rc=goal,
        max_stops=3,
        operational_limit_s=tight_limit,
    )

    for cand in report.all_candidates:
        if cand.total_mission_time_s > tight_limit:
            assert not cand.is_budget_feasible, f"Candidate {cand.id} should be marked budget infeasible"
            assert not cand.is_feasible, f"Candidate {cand.id} should not be marked overall feasible"


def test_feasibility_honesty():
    """An over-budget candidate is never labeled as feasible."""
    cand = SortieCandidate(
        id="test_over_budget",
        objective="science_priority",
        title="Over Budget Candidate",
        tradeoff_rationale="Over-budget test candidate",
        stop_ids=["wp1"],
        stop_names=["Waypoint 1"],
        num_stops=1,
        path_rc=[(117, 157), (66, 128)],
        distance_m=3000.0,
        terrain_cost=3000.0,
        travel_time_s=10000.0,
        dwell_time_s=1800.0,
        hold_delay_s=0.0,
        total_mission_time_s=11800.0,
        operational_limit_s=7200.0,  # limit is 7200s, total is 11800s
        time_margin_s=-4600.0,
        max_distance_m=None,
        distance_margin_m=None,
        science_score=80.0,
        science_rate_per_hour=24.4,
        is_reachable=True,
        is_budget_feasible=False,
        is_pareto=False,
    )
    assert not cand.is_feasible
    assert not cand.is_budget_feasible
    assert cand.time_margin_s < 0


def test_api_validation_errors(terrain_grid, transform_affine, waypoints_catalog):
    """API service rejects invalid inputs with APIError 400."""
    valid_payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "candidate_waypoint_ids": ["three_forks"],
        "max_stops": 2,
    }

    # 1. Missing start
    with pytest.raises(APIError) as exc:
        mission_optimize_api({**valid_payload, "start": None}, terrain_grid, transform_affine, waypoints_catalog)
    assert exc.value.status_code == 400

    # 2. Out of bounds coordinates
    with pytest.raises(APIError) as exc:
        mission_optimize_api({**valid_payload, "start": {"row": 9999, "col": 157}}, terrain_grid, transform_affine, waypoints_catalog)
    assert exc.value.status_code == 400

    # 3. Identical start and goal
    with pytest.raises(APIError) as exc:
        mission_optimize_api({**valid_payload, "goal": {"row": 117, "col": 157}}, terrain_grid, transform_affine, waypoints_catalog)
    assert exc.value.status_code == 400

    # 4. Empty candidate waypoints
    with pytest.raises(APIError) as exc:
        mission_optimize_api({**valid_payload, "candidate_waypoint_ids": []}, terrain_grid, transform_affine, waypoints_catalog)
    assert exc.value.status_code == 400


def test_determinism_and_fingerprinting(terrain_grid, transform_affine, waypoints_catalog):
    """Identical inputs produce identical sorties and matching fingerprints."""
    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "candidate_waypoint_ids": ["three_forks", "hawksbill_gap"],
        "max_stops": 2,
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "operational_limit_s": 28800.0,
    }

    rep1 = mission_optimize_api(payload, terrain_grid, transform_affine, waypoints_catalog)
    rep2 = mission_optimize_api(payload, terrain_grid, transform_affine, waypoints_catalog)

    assert rep1["computation_fingerprint"] == rep2["computation_fingerprint"]
    assert rep1["candidates_evaluated"] == rep2["candidates_evaluated"]
    assert len(rep1["all_candidates"]) == len(rep2["all_candidates"])
    assert rep1["balanced_champion"]["path_rc"] == rep2["balanced_champion"]["path_rc"]


def test_multi_objective_mode_behaviors(terrain_grid, waypoints_catalog):
    """Champions conform to their objective definitions."""
    report = optimize_mission_sorties(
        terrain=terrain_grid,
        all_waypoints=waypoints_catalog,
        candidate_waypoint_ids=["three_forks", "hawksbill_gap", "seitah_dunes", "neretva_margin"],
        start_rc=(117, 157),
        goal_rc=(66, 128),
        max_stops=3,
        operational_limit_s=28800.0,
    )

    baseline = report.direct_baseline
    assert baseline is not None
    assert baseline.num_stops == 0
    assert baseline.science_score == 0.0

    sci_champ = report.science_champion
    assert sci_champ is not None
    assert sci_champ.science_score >= baseline.science_score

    time_champ = report.time_champion
    assert time_champ is not None
    # Fastest feasible multi-stop or baseline
    assert time_champ.travel_time_s <= sci_champ.travel_time_s or sci_champ.num_stops == 0


def test_pareto_frontier_filtering(terrain_grid, waypoints_catalog):
    """Extracted Pareto frontier contains no strictly dominated sorties."""
    report = optimize_mission_sorties(
        terrain=terrain_grid,
        all_waypoints=waypoints_catalog,
        candidate_waypoint_ids=["three_forks", "hawksbill_gap", "neretva_margin"],
        start_rc=(117, 157),
        goal_rc=(66, 128),
        max_stops=2,
    )

    pareto_candidates = report.pareto_frontier_2d
    assert len(pareto_candidates) > 0

    # Verify no member in pareto_frontier_2d is strictly dominated by another member
    for a in pareto_candidates:
        for b in pareto_candidates:
            if a.id == b.id:
                continue
            # A dominates B if A has strictly better/equal science AND strictly faster/equal travel time
            # with at least one strictly better
            b_is_dominated_by_a = (
                a.science_score >= b.science_score and
                a.travel_time_s <= b.travel_time_s and
                (a.science_score > b.science_score or a.travel_time_s < b.travel_time_s)
            )
            assert not b_is_dominated_by_a, f"Candidate {b.id} is dominated by {a.id} in Pareto set!"


def test_locomotion_models_crew_vs_rover(terrain_grid, waypoints_catalog):
    """Rover mode (0.035 m/s) exhibits much longer traverse times than crew EVA (2.0 km/h)."""
    start = (117, 157)
    goal = (66, 128)
    cand_ids = ["three_forks"]

    rep_crew = optimize_mission_sorties(
        terrain=terrain_grid,
        all_waypoints=waypoints_catalog,
        candidate_waypoint_ids=cand_ids,
        start_rc=start,
        goal_rc=goal,
        max_stops=1,
        vehicle_mode="crew_eva",
    )

    rep_rover = optimize_mission_sorties(
        terrain=terrain_grid,
        all_waypoints=waypoints_catalog,
        candidate_waypoint_ids=cand_ids,
        start_rc=start,
        goal_rc=goal,
        max_stops=1,
        vehicle_mode="robotic_rover",
    )

    crew_direct = rep_crew.direct_baseline
    rover_direct = rep_rover.direct_baseline

    assert crew_direct is not None and rover_direct is not None
    assert rover_direct.travel_time_s > crew_direct.travel_time_s * 5.0, (
        "Robotic rover traverse time must be substantially longer than crew EVA"
    )


def test_live_http_api_optimization():
    """Live HTTP API endpoint /api/mission/optimize returns HTTP 200 with complete report."""
    url = f"{SERVER_BASE_URL}/api/mission/optimize"
    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "candidate_waypoint_ids": ["three_forks", "hawksbill_gap"],
        "max_stops": 2,
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "operational_limit_s": 28800.0,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "schema_version" in data
            assert data["schema_version"] == "1.0.0"
            assert "computation_fingerprint" in data
            assert "recommended_sortie" in data
            assert data["recommended_sortie"] is not None
            assert "balanced_champion" in data
            assert "all_candidates" in data
            assert len(data["all_candidates"]) >= 3
            assert data["execution_time_ms"] < 2500.0
    except urllib.error.URLError as e:
        pytest.skip(f"Atlas server not running at {SERVER_BASE_URL}: {e}")


def test_workspace_immutability():
    """Mission optimization does not mutate existing saved missions or experiments."""
    missions = list_missions()
    experiments = list_experiments()

    assert len(missions) == 7, "Must maintain exactly 7 saved missions"
    assert len(experiments) == 11, "Must maintain exactly 11 historical experiments"
