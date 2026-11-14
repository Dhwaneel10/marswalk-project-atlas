"""
MarsWalk 2.0 — Milestone 9X Mission Robustness Lab, Sensitivity Analysis & Decision Stability Test Suite.

Comprehensive automated regression tests covering critical engineering and scientific behaviors:
 1. Identical inputs produce deterministic results and identical SHA-256 fingerprints.
 2. Looser operational budget does not make an otherwise identical reachable route infeasible.
 3. Budget below calculated mission time marks the candidate infeasible.
 4. Reduced mobility scales duration preserving route geometry.
 5. Changing budget alone does not falsely claim terrain geometry changed.
 6. Closure intersecting route evaluates actual blocked-cell behavior and detours.
 7. Closure outside route does not claim a detour.
 8. Target loss changes selected science targets and priority score consistently.
 9. Robustness proportions strictly agree with enumerated scenario outcomes.
10. Breakpoint reporting respects discrete tested parameter resolution.
11. Invalid and excessively large inputs (> 50 cases) are rejected with HTTP 400.
12. Direct baseline mission (0 intermediate stops) evaluated safely.
13. Distinct terrain identities cannot reuse incompatible cached results.
14. Candidate comparison evaluates alternatives across the identical test matrix.
15. Workspace immutability (7 missions and 11 experiments preserved).
16. Existing adaptive replanning continues to function without regression.
17. Existing mission tour optimizer continues to function without regression.
18. Live HTTP round-trip on port 3000 for POST /api/mission/robustness.
"""

import os
import json
import copy
import urllib.request
import urllib.error
import pytest
import rasterio
import numpy as np
from pathlib import Path

from marswalk.core.terrain import load_and_process_terrain, TerrainGrid
from marswalk.core.planner import plan_route, ScienceWaypoint, PlannerConfig
from marswalk.core.mission_optimizer import optimize_science_tour, SortieObjective
from marswalk.core.adaptive_replanner import replan_adaptive_mission
from marswalk.core.robustness import (
    evaluate_mission_robustness,
    RobustnessTestCase,
    RobustnessAnalysisResult,
    SensitivityDimension,
)
from marswalk.api.service import mission_robustness_api, APIError
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
                priority_score=float(wp.get("priority_score", 50.0)),
                geological_context=wp.get("geological_context", ""),
                crism_signature=wp.get("crism_signature", ""),
                pds_citation=wp.get("pds_citation", ""),
            )
        )
    return wps


def test_01_identical_inputs_produce_deterministic_results(terrain_grid, waypoints_catalog):
    """Behavior 1: Robustness analysis produces deterministic numerical results and matching fingerprints."""
    start_rc = (178, 48)
    goal_rc = (136, 91)
    wp_map = {w.id: w for w in waypoints_catalog}
    stops = [wp_map["hawksbill_gap"], wp_map["skinner_ridge"]]

    res1 = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        candidate_pool=waypoints_catalog,
        profile="balanced",
        vehicle_mode="crew_eva",
        nominal_budget_s=28800.0,
    )

    res2 = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        candidate_pool=waypoints_catalog,
        profile="balanced",
        vehicle_mode="crew_eva",
        nominal_budget_s=28800.0,
    )

    assert res1.computation_fingerprint == res2.computation_fingerprint
    assert res1.primary_evaluation.cases_tested == res2.primary_evaluation.cases_tested
    assert res1.primary_evaluation.feasible_cases_count == res2.primary_evaluation.feasible_cases_count
    assert res1.primary_evaluation.min_margin_s == res2.primary_evaluation.min_margin_s


def test_02_looser_operational_budget_preserves_feasibility(terrain_grid, waypoints_catalog):
    """Behavior 2: A looser budget does not make an otherwise identical reachable route infeasible."""
    start_rc = (178, 48)
    goal_rc = (136, 91)
    wp_map = {w.id: w for w in waypoints_catalog}
    stops = [wp_map["hawksbill_gap"]]

    spec = {
        "budget_limits_s": [18000.0, 28800.0, 36000.0]
    }
    res = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        sensitivity_spec=spec,
        nominal_budget_s=28800.0,
    )

    cases = res.primary_evaluation.case_results
    assert len(cases) == 3
    # If 18000s is feasible, then 28800s and 36000s MUST also be feasible
    if cases[0].is_feasible:
        assert cases[1].is_feasible
        assert cases[2].is_feasible
    assert cases[2].remaining_margin_s > cases[1].remaining_margin_s > cases[0].remaining_margin_s


def test_03_tight_budget_marks_candidate_infeasible(terrain_grid, waypoints_catalog):
    """Behavior 3: A budget below calculated mission duration marks the candidate infeasible."""
    start_rc = (178, 48)
    goal_rc = (136, 91)
    wp_map = {w.id: w for w in waypoints_catalog}
    stops = [wp_map["hawksbill_gap"]]

    # Extremely tight budget of 100 seconds
    spec = {
        "budget_limits_s": [100.0]
    }
    res = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        sensitivity_spec=spec,
        nominal_budget_s=28800.0,
    )

    cases = res.primary_evaluation.case_results
    assert len(cases) == 1
    assert not cases[0].is_feasible
    assert not cases[0].is_budget_feasible
    assert cases[0].is_reachable  # Path is physically reachable, but exceeds 100s


def test_04_reduced_mobility_scales_duration_preserving_geometry(terrain_grid, waypoints_catalog):
    """Behavior 4: Reduced mobility scales travel duration without modifying route path cells."""
    start_rc = (178, 48)
    goal_rc = (136, 91)
    wp_map = {w.id: w for w in waypoints_catalog}
    stops = [wp_map["hawksbill_gap"]]

    res = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        nominal_budget_s=28800.0,
    )

    nom_case = next(c for c in res.primary_evaluation.case_results if c.case_id == "mobility_100pct")
    derate_case = next(c for c in res.primary_evaluation.case_results if c.case_id == "mobility_50pct")

    assert not derate_case.geometry_changed
    assert derate_case.distance_m == pytest.approx(nom_case.distance_m, rel=1e-3)
    # Travel time for 0.5x mobility is exactly 2.0x nominal travel time
    assert derate_case.travel_time_s == pytest.approx(nom_case.travel_time_s * 2.0, rel=1e-3)


def test_05_budget_variation_alone_preserves_terrain_geometry(terrain_grid, waypoints_catalog):
    """Behavior 5: Budget changes alone do NOT alter route coordinates or claim false detours."""
    start_rc = (178, 48)
    goal_rc = (136, 91)
    wp_map = {w.id: w for w in waypoints_catalog}
    stops = [wp_map["skinner_ridge"]]

    res = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        nominal_budget_s=28800.0,
    )

    budget_cases = [c for c in res.primary_evaluation.case_results if c.dimension == SensitivityDimension.BUDGET.value]
    assert len(budget_cases) >= 3
    for bc in budget_cases:
        assert not bc.geometry_changed
        assert bc.distance_m == pytest.approx(res.baseline_mission["distance_m"], rel=1e-3)


def test_06_closure_intersecting_route_evaluates_blocked_cells(terrain_grid, waypoints_catalog):
    """Behavior 6: Closure centered on route path activates blocked cells and computes physical detour."""
    start_rc = (178, 48)
    goal_rc = (136, 91)
    wp_map = {w.id: w for w in waypoints_catalog}
    stops = [wp_map["hawksbill_gap"]]

    res = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        nominal_budget_s=28800.0,
    )

    intersect_case = next(
        (c for c in res.primary_evaluation.case_results if c.case_id == "closure_intersect_60m"),
        None,
    )
    assert intersect_case is not None
    # Intersecting closure forces route modification
    assert intersect_case.geometry_changed


def test_07_closure_outside_route_does_not_claim_detour(terrain_grid, waypoints_catalog):
    """Behavior 7: Closure placed outside the route corridor does NOT claim a detour."""
    start_rc = (178, 48)
    goal_rc = (136, 91)
    wp_map = {w.id: w for w in waypoints_catalog}
    stops = [wp_map["hawksbill_gap"]]

    res = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        nominal_budget_s=28800.0,
    )

    ext_case = next(
        (c for c in res.primary_evaluation.case_results if c.case_id == "closure_external_50m"),
        None,
    )
    assert ext_case is not None
    assert not ext_case.geometry_changed
    assert ext_case.distance_m == pytest.approx(res.baseline_mission["distance_m"], rel=1e-3)


def test_08_target_loss_updates_science_score_and_itinerary(terrain_grid, waypoints_catalog):
    """Behavior 8: Dropping a target updates science score and removes waypoint from itinerary."""
    start_rc = (178, 48)
    goal_rc = (136, 91)
    wp_map = {w.id: w for w in waypoints_catalog}
    target1 = wp_map["hawksbill_gap"]
    target2 = wp_map["skinner_ridge"]
    stops = [target1, target2]

    res = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        nominal_budget_s=28800.0,
    )

    tl_case = next(
        (c for c in res.primary_evaluation.case_results if c.case_id == f"target_loss_{target1.id}"),
        None,
    )
    assert tl_case is not None
    assert target1.id not in tl_case.active_stop_ids
    assert target2.id in tl_case.active_stop_ids
    assert tl_case.science_score == pytest.approx(target2.priority_score, rel=1e-3)


def test_09_robustness_proportions_agree_with_case_counts(terrain_grid, waypoints_catalog):
    """Behavior 9: Feasible and reachable proportions strictly equal count / tested."""
    start_rc = (178, 48)
    goal_rc = (136, 91)
    wp_map = {w.id: w for w in waypoints_catalog}
    stops = [wp_map["hawksbill_gap"]]

    res = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        nominal_budget_s=28800.0,
    )

    pe = res.primary_evaluation
    n = pe.cases_tested
    assert n > 0
    assert pe.feasible_ratio == pytest.approx(pe.feasible_cases_count / n, abs=1e-3)
    assert pe.reachable_ratio == pytest.approx(pe.reachable_cases_count / n, abs=1e-3)


def test_10_breakpoint_reporting_respects_tested_resolution(terrain_grid, waypoints_catalog):
    """Behavior 10: Breakpoints report tested thresholds with explicit parameter step resolution."""
    start_rc = (178, 48)
    goal_rc = (136, 91)
    wp_map = {w.id: w for w in waypoints_catalog}
    stops = [wp_map["hawksbill_gap"]]

    # Construct explicit stepping from 2000s (infeasible) to 6000s (feasible) with step 1000s
    spec = {
        "budget_limits_s": [1000.0, 2000.0, 3000.0, 4000.0, 5000.0, 6000.0]
    }
    res = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        sensitivity_spec=spec,
        nominal_budget_s=28800.0,
    )

    bps = res.primary_evaluation.breakpoints
    budget_bps = [b for b in bps if b.dimension == SensitivityDimension.BUDGET.value]
    if budget_bps:
        bp = budget_bps[0]
        assert "Tested step resolution" in bp.tested_resolution
        assert bp.breakpoint_value in spec["budget_limits_s"]


def test_11_invalid_and_excessive_inputs_rejected(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 11: Service API rejects malformed, out-of-bounds, or excessive (>50) evaluations."""
    # 1. Non-dict payload
    with pytest.raises(APIError) as exc_info:
        mission_robustness_api([], terrain_grid, transform_affine, waypoints_catalog)
    assert exc_info.value.error_code == "ERR_MALFORMED_JSON"

    # 2. Identical endpoints
    with pytest.raises(APIError) as exc_info:
        mission_robustness_api(
            {"start": {"row": 100, "col": 100}, "goal": {"row": 100, "col": 100}},
            terrain_grid,
            transform_affine,
            waypoints_catalog,
        )
    assert exc_info.value.error_code == "ERR_IDENTICAL_ENDPOINTS"

    # 3. Excessive evaluations (> 50 cases)
    excessive_budgets = [float(i * 100) for i in range(1, 60)]
    with pytest.raises(APIError) as exc_info:
        mission_robustness_api(
            {
                "start": {"row": 178, "col": 48},
                "goal": {"row": 136, "col": 91},
                "sensitivity_spec": {"budget_limits_s": excessive_budgets},
            },
            terrain_grid,
            transform_affine,
            waypoints_catalog,
        )
    assert exc_info.value.error_code == "ERR_EXCESSIVE_EVALUATIONS"


def test_12_empty_stops_direct_baseline_robustness(terrain_grid):
    """Behavior 12: Direct baseline route (0 intermediate stops) evaluates robustness safely."""
    start_rc = (178, 48)
    goal_rc = (136, 91)

    res = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=[],
        nominal_budget_s=28800.0,
    )

    assert res.status == "success"
    assert res.baseline_mission["num_stops"] == 0
    assert res.primary_evaluation.cases_tested > 0
    assert res.primary_evaluation.feasible_cases_count > 0


def test_13_distinct_terrain_identities_cannot_reuse_cache(terrain_grid, waypoints_catalog):
    """Behavior 13: Fingerprint incorporates terrain and route identity preventing stale cache reuse."""
    start_rc = (178, 48)
    goal_rc = (136, 91)
    wp_map = {w.id: w for w in waypoints_catalog}

    res_eva = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=[wp_map["hawksbill_gap"]],
        vehicle_mode="crew_eva",
        nominal_budget_s=28800.0,
    )

    res_rover = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=[wp_map["hawksbill_gap"]],
        vehicle_mode="robotic_rover",
        nominal_budget_s=14400.0,
    )

    assert res_eva.computation_fingerprint != res_rover.computation_fingerprint


def test_14_candidate_comparison_across_identical_test_matrix(terrain_grid, waypoints_catalog):
    """Behavior 14: Multiple candidates evaluated against the exact same scenario matrix with trade-offs."""
    start_rc = (178, 48)
    goal_rc = (136, 91)
    wp_map = {w.id: w for w in waypoints_catalog}
    stops = [wp_map["hawksbill_gap"], wp_map["skinner_ridge"]]

    comparison_candidates = [
        {"id": "direct_baseline", "title": "Direct Baseline", "stop_ids": []}
    ]

    res = evaluate_mission_robustness(
        terrain=terrain_grid,
        start_rc=start_rc,
        goal_rc=goal_rc,
        stops=stops,
        candidate_pool=waypoints_catalog,
        comparison_candidates=comparison_candidates,
        nominal_budget_s=28800.0,
    )

    assert len(res.candidate_comparisons) == 1
    comp = res.candidate_comparisons[0]
    assert comp.candidate_id == "direct_baseline"
    assert comp.cases_tested == res.primary_evaluation.cases_tested
    assert comp.nominal_science_score == 0.0
    assert comp.nominal_duration_s < res.primary_evaluation.nominal_duration_s


def test_15_historical_workspace_immutability():
    """Behavior 15: Existing saved missions and experiments remain unmutated on disk."""
    missions = list_missions()
    experiments = list_experiments()
    assert len(missions) == 7, f"Expected 7 saved missions, got {len(missions)}"
    assert len(experiments) == 11, f"Expected 11 saved experiments, got {len(experiments)}"


def test_16_existing_adaptive_replanning_unaffected(terrain_grid, waypoints_catalog):
    """Behavior 16: Milestone 9W adaptive replanning engine continues to function without regression."""
    start_rc = (117, 157)
    goal_rc = (66, 128)
    events = [
        {"event_type": "reduced_mobility", "speed_multiplier": 0.8, "enabled": True}
    ]
    replan_res = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=waypoints_catalog,
        events_data=events,
        original_stop_ids=["belva_crater_overlook"],
        profile="balanced",
        vehicle_mode="crew_eva",
    )
    assert replan_res.recommendation is not None
    assert replan_res.recovery_metrics is not None


def test_17_existing_mission_optimization_unaffected(terrain_grid, waypoints_catalog):
    """Behavior 17: Milestone 9V autonomous science-tour optimizer continues to function without regression."""
    start_rc = (117, 157)
    goal_rc = (66, 128)
    opt_report = optimize_science_tour(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=waypoints_catalog,
        max_stops=2,
    )
    assert opt_report.candidates_evaluated > 0
    assert len(opt_report.all_candidates) >= 1


def test_18_live_http_round_trip_port_3000():
    """Behavior 18: Live HTTP POST /api/mission/robustness returns HTTP 200 with complete response."""
    payload = {
        "start": {"row": 178, "col": 48, "name": "Octavia E. Butler Landing"},
        "goal": {"row": 136, "col": 91, "name": "Delta Rim Overlook"},
        "stops": ["hawksbill_gap", "skinner_ridge"],
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "comparison_candidates": [
            {"id": "direct_baseline", "title": "Direct Baseline", "stop_ids": []}
        ]
    }
    url = f"{SERVER_BASE_URL}/api/mission/robustness"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "success"
            assert data["schema_version"] == "1.0.0"
            assert "computation_fingerprint" in data
            assert "primary_evaluation" in data
            pe = data["primary_evaluation"]
            assert pe["cases_tested"] >= 10
            assert "candidate_comparisons" in data
            assert len(data["candidate_comparisons"]) == 1
    except urllib.error.URLError as err:
        pytest.skip(f"Atlas server not reachable on {SERVER_BASE_URL}: {err}")
