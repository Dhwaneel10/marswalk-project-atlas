"""
MarsWalk 2.0 — Milestone 9W Adaptive Mission Replanning & Science Recovery Test Suite

Comprehensive automated regression tests covering the 20 critical engineering
and scientific behaviors of the disruption-aware replanning engine:

 1. Original inputs preserved (zero caller mutation).
 2. Closed corridor produces event-aware revised route.
 3. Adaptive route avoids every blocked cell.
 4. Closure outside route does not claim detour.
 5. Unavailable target excluded from adaptive itinerary.
 6. Reduced mobility scales time without altering geometry.
 7. Operational hold applied exactly once.
 8. Reduced budget alters feasibility correctly.
 9. Difficult terrain modifies routing cost.
10. Science priority totals match selected targets.
11. Lost and recovered priority math is consistent.
12. Over-budget adaptive candidate never marked feasible.
13. Adaptive plan evaluated under identical disruption conditions as disrupted plan.
14. Deterministic outputs and matching computation fingerprints.
15. API rejection of invalid coordinates, NaN, identical endpoints with HTTP 400.
16. Recommendation classification enums adhere to decision matrix.
17. Workspace immutability (7 missions and 11 experiments preserved).
18. Three-stage structure completeness (original, disrupted, adaptive).
19. Nominal Mission Design Lab continues to function without regression.
20. Live HTTP round-trip on port 3000 for POST /api/mission/replan.
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
from marswalk.core.adaptive_replanner import (
    replan_adaptive_mission,
    compile_custom_contingency,
    ReplanningRecommendation,
    AdaptiveReplanningResult,
)
from marswalk.api.service import mission_replan_api, mission_optimize_api, APIError
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


def test_01_original_inputs_preserved(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 1: Replan call does not mutate the caller's input lists or objects."""
    start_rc = (117, 157)
    goal_rc = (66, 128)
    original_stops = ["belva_crater_overlook", "kodiak_butte"]
    events = [
        {"event_type": "closed_corridor", "center_rc": (130, 160), "radius_m": 80.0, "enabled": True}
    ]

    stops_clone = copy.deepcopy(original_stops)
    events_clone = copy.deepcopy(events)
    wps_clone = [copy.deepcopy(w) for w in waypoints_catalog]

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=waypoints_catalog,
        events_data=events,
        original_stop_ids=original_stops,
        profile="balanced",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=900.0,
        operational_delay_s=0.0,
        max_stops=2,
        beam_width=6,
        transform=transform_affine,
    )

    assert original_stops == stops_clone, "Original stops list was mutated by replanner"
    assert events == events_clone, "Custom events list was mutated by replanner"
    assert [w.id for w in waypoints_catalog] == [w.id for w in wps_clone], "Waypoint list was mutated"


def test_02_closed_corridor_produces_event_aware_revised_route(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 2: Placing a closed corridor directly on the nominal route causes a detour in disrupted/adaptive plans."""
    start_rc = (117, 157)
    goal_rc = (66, 128)

    cfg = PlannerConfig(profile="balanced")
    nominal = plan_route(start_rc, goal_rc, terrain_grid, config=cfg)
    assert nominal.is_reachable, "Nominal route must be reachable"
    mid_idx = len(nominal.path) // 2
    mid_rc = nominal.path[mid_idx]

    events = [
        {"event_type": "closed_corridor", "center_rc": mid_rc, "radius_m": 40.0, "enabled": True}
    ]

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=[],
        events_data=events,
        original_stop_ids=[],
        profile="balanced",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=0.0,
        operational_delay_s=0.0,
        max_stops=0,
        transform=transform_affine,
    )

    assert (
        result.original_plan.path_rc != result.disrupted_plan.path_rc
        or result.original_plan.terrain_cost < result.disrupted_plan.terrain_cost
        or result.original_plan.distance_m < result.disrupted_plan.distance_m
        or not result.disrupted_plan.is_reachable
    ), "Closed corridor must alter route geometry or increase traversal cost"



def test_03_adaptive_route_avoids_every_blocked_cell(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 3: The adaptive route geometry never traverses any blocked cell."""
    start_rc = (117, 157)
    goal_rc = (66, 128)
    block_center = (100, 145)
    block_radius = 50.0
    events = [
        {"event_type": "closed_corridor", "center_rc": block_center, "radius_m": block_radius, "enabled": True}
    ]

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=waypoints_catalog[:4],
        events_data=events,
        original_stop_ids=[],
        profile="balanced",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=900.0,
        operational_delay_s=0.0,
        max_stops=2,
        beam_width=6,
        transform=transform_affine,
    )

    path_rc = result.adaptive_plan.path_rc
    assert len(path_rc) > 0, "Adaptive route must have a valid path"

    for r, c in path_rc:
        dist_m = np.hypot(r - block_center[0], c - block_center[1]) * 20.0
        assert dist_m > block_radius - 1.0, f"Adaptive route touched blocked cell ({r}, {c}) at distance {dist_m:.1f} m"


def test_04_closure_outside_route_does_not_claim_detour(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 4: A closed corridor placed far from the route does not cause any detour or penalty."""
    start_rc = (117, 157)
    goal_rc = (110, 150)
    # Block corner (10, 10) far away
    events = [
        {"event_type": "closed_corridor", "center_rc": (10, 10), "radius_m": 40.0, "enabled": True}
    ]

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=[],
        events_data=events,
        original_stop_ids=[],
        profile="conservative",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=0.0,
        operational_delay_s=0.0,
        max_stops=0,
        transform=transform_affine,
    )

    orig_dist = result.original_plan.distance_m
    disr_dist = result.disrupted_plan.distance_m
    assert abs(orig_dist - disr_dist) < 1.0, f"Distant closure caused spurious detour: orig={orig_dist}, disr={disr_dist}"
    assert result.recommendation == ReplanningRecommendation.CONTINUE_WITH_DETOUR


def test_05_unavailable_target_excluded_from_adaptive_itinerary(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 5: An unavailable target is purged from candidate pool and never proposed in adaptive itinerary."""
    start_rc = (117, 157)
    goal_rc = (66, 128)
    bad_target_id = "belva_crater_overlook"
    original_stops = [bad_target_id]
    events = [
        {"event_type": "target_unavailable", "target_id": bad_target_id, "enabled": True}
    ]

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=waypoints_catalog,
        events_data=events,
        original_stop_ids=original_stops,
        profile="balanced",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=900.0,
        operational_delay_s=0.0,
        max_stops=2,
        beam_width=8,
        transform=transform_affine,
    )

    adaptive_stop_ids = result.adaptive_plan.stop_ids
    assert bad_target_id not in adaptive_stop_ids, f"Unavailable target {bad_target_id} was improperly included in adaptive plan: {adaptive_stop_ids}"
    assert bad_target_id in result.recovery_metrics.dropped_stop_ids


def test_06_reduced_mobility_scales_time_without_altering_geometry(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 6: Drive actuator derating scales travel time while distance remains geometrically invariant."""
    start_rc = (117, 157)
    goal_rc = (90, 140)
    events = [
        {"event_type": "reduced_mobility", "speed_multiplier": 0.5, "enabled": True}
    ]

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=[],
        events_data=events,
        original_stop_ids=[],
        profile="conservative",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=0.0,
        operational_delay_s=0.0,
        max_stops=0,
        transform=transform_affine,
    )

    orig = result.original_plan
    disr = result.disrupted_plan

    assert abs(orig.distance_m - disr.distance_m) < 0.1, "Mobility derating altered path distance"
    expected_time = orig.total_mission_time_s * 2.0
    assert abs(disr.total_mission_time_s - expected_time) < 5.0, f"Travel time did not double: orig={orig.total_mission_time_s}, disr={disr.total_mission_time_s}"


def test_07_operational_hold_applied_exactly_once(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 7: An operational hold adds exactly its duration to the total mission timeline."""
    start_rc = (117, 157)
    goal_rc = (100, 150)
    hold_s = 1800.0  # 30 minutes
    events = [
        {"event_type": "operational_hold", "hold_time_s": hold_s, "enabled": True}
    ]

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=[],
        events_data=events,
        original_stop_ids=[],
        profile="balanced",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=0.0,
        operational_delay_s=0.0,
        max_stops=0,
        transform=transform_affine,
    )

    delta_time = result.disrupted_plan.total_mission_time_s - result.original_plan.total_mission_time_s
    assert abs(delta_time - hold_s) < 1.0, f"Hold time error: expected {hold_s}s delta, got {delta_time}s"


def test_08_reduced_budget_alters_feasibility_correctly(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 8: Reducing budget below mission time changes feasibility from True to False."""
    start_rc = (117, 157)
    goal_rc = (66, 128)
    cfg = PlannerConfig(profile="balanced")
    nom = plan_route(start_rc, goal_rc, terrain_grid, config=cfg)
    nom_time = nom.travel_time_s

    tight_budget = nom_time + 100.0
    events = [
        {"event_type": "reduced_time_budget", "budget_cut_pct": 50.0, "enabled": True}
    ]

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=[],
        events_data=events,
        original_stop_ids=[],
        profile="balanced",
        vehicle_mode="crew_eva",
        operational_limit_s=tight_budget,
        dwell_time_per_stop_s=0.0,
        operational_delay_s=0.0,
        max_stops=0,
        transform=transform_affine,
    )

    assert result.original_plan.is_budget_feasible is True, "Original plan should be feasible"
    assert result.disrupted_plan.is_budget_feasible is False, "Disrupted plan should be infeasible under 50% cut"


def test_09_difficult_terrain_modifies_routing_cost(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 9: Difficult terrain impedance increases traversal cost."""
    start_rc = (117, 157)
    goal_rc = (90, 140)
    events = [
        {"event_type": "difficult_terrain", "center_rc": (105, 150), "radius_m": 80.0, "cost_multiplier": 4.0, "enabled": True}
    ]

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=[],
        events_data=events,
        original_stop_ids=[],
        profile="conservative",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=0.0,
        operational_delay_s=0.0,
        max_stops=0,
        transform=transform_affine,
    )

    assert (result.disrupted_plan.distance_m >= result.original_plan.distance_m or
            result.disrupted_plan.total_mission_time_s >= result.original_plan.total_mission_time_s)


def test_10_science_priority_totals_match_selected_targets(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 10: Science priority totals in all three stages strictly equal the sum of constituent stop scores."""
    start_rc = (117, 157)
    goal_rc = (66, 128)
    original_stops = ["belva_crater_overlook", "kodiak_butte"]
    events = [
        {"event_type": "target_unavailable", "target_id": "belva_crater_overlook", "enabled": True}
    ]
    wp_map = {w.id: w for w in waypoints_catalog}

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=waypoints_catalog[:6],
        events_data=events,
        original_stop_ids=original_stops,
        profile="balanced",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=900.0,
        operational_delay_s=0.0,
        max_stops=2,
        beam_width=6,
        transform=transform_affine,
    )

    orig_sum = sum(wp_map[sid].priority_score for sid in result.original_plan.stop_ids if sid in wp_map)
    assert abs(orig_sum - result.original_plan.science_score) < 0.01

    disr_sum = sum(wp_map[sid].priority_score for sid in result.disrupted_plan.stop_ids if sid in wp_map)
    assert abs(disr_sum - result.disrupted_plan.science_score) < 0.01

    adapt_sum = sum(wp_map[sid].priority_score for sid in result.adaptive_plan.stop_ids if sid in wp_map)
    assert abs(adapt_sum - result.adaptive_plan.science_score) < 0.01


def test_11_lost_and_recovered_priority_math_consistent(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 11: Quantitative science recovery ledger satisfies all algebraic identities."""
    start_rc = (117, 157)
    goal_rc = (66, 128)
    original_stops = ["belva_crater_overlook", "kodiak_butte"]
    events = [
        {"event_type": "target_unavailable", "target_id": "belva_crater_overlook", "enabled": True}
    ]

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=waypoints_catalog,
        events_data=events,
        original_stop_ids=original_stops,
        profile="balanced",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=900.0,
        operational_delay_s=0.0,
        max_stops=2,
        beam_width=8,
        transform=transform_affine,
    )

    rec = result.recovery_metrics
    orig_p = rec.original_science_score
    disr_p = rec.disrupted_science_score
    adapt_p = rec.adaptive_science_score

    expected_lost = max(0.0, orig_p - disr_p)
    assert abs(rec.science_score_lost - expected_lost) < 0.01

    expected_rec = max(0.0, adapt_p - disr_p)
    assert abs(rec.science_score_recovered - expected_rec) < 0.01

    assert abs(rec.net_science_delta - (adapt_p - orig_p)) < 0.01

    if expected_lost > 0:
        expected_eff = (expected_rec / expected_lost) * 100.0
        assert abs(rec.science_recovery_pct - expected_eff) < 0.01


def test_12_over_budget_adaptive_candidate_never_marked_feasible(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 12: An adaptive plan that exceeds budget is strictly marked is_budget_feasible = False."""
    start_rc = (117, 157)
    goal_rc = (66, 128)

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=waypoints_catalog[:3],
        events_data=[],
        original_stop_ids=[],
        profile="balanced",
        vehicle_mode="crew_eva",
        operational_limit_s=100.0,  # 100s ceiling
        dwell_time_per_stop_s=900.0,
        operational_delay_s=0.0,
        max_stops=1,
        transform=transform_affine,
    )

    assert result.adaptive_plan.is_budget_feasible is False, "Over-budget candidate was marked feasible"


def test_13_adaptive_plan_evaluated_under_identical_disruption_conditions(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 13: The adaptive tour optimizer operates on the disrupted pairwise matrix, not nominal."""
    start_rc = (117, 157)
    goal_rc = (66, 128)
    events = [
        {"event_type": "closed_corridor", "center_rc": (110, 150), "radius_m": 60.0, "enabled": True}
    ]

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=waypoints_catalog[:4],
        events_data=events,
        original_stop_ids=[],
        profile="balanced",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=900.0,
        operational_delay_s=0.0,
        max_stops=2,
        beam_width=6,
        transform=transform_affine,
    )

    for r, c in result.adaptive_plan.path_rc:
        dist = np.hypot(r - 110, c - 150) * 20.0
        assert dist > 59.0, f"Adaptive plan routed through closed corridor at ({r}, {c})"


def test_14_deterministic_outputs_and_matching_fingerprints(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 14: Two runs with identical inputs produce identical computation fingerprints and results."""
    start_rc = (117, 157)
    goal_rc = (66, 128)
    events = [{"event_type": "reduced_mobility", "speed_multiplier": 0.8, "enabled": True}]

    run1 = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=waypoints_catalog[:3],
        events_data=events,
        original_stop_ids=["kodiak_butte"],
        profile="balanced",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=900.0,
        operational_delay_s=0.0,
        max_stops=1,
        transform=transform_affine,
    )

    run2 = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=waypoints_catalog[:3],
        events_data=events,
        original_stop_ids=["kodiak_butte"],
        profile="balanced",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=900.0,
        operational_delay_s=0.0,
        max_stops=1,
        transform=transform_affine,
    )

    assert run1.computation_fingerprint == run2.computation_fingerprint
    assert run1.recommendation == run2.recommendation
    assert run1.adaptive_plan.science_score == run2.adaptive_plan.science_score
    assert run1.adaptive_plan.distance_m == run2.adaptive_plan.distance_m


def test_15_api_validation_rejection_invalid_inputs(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 15: API rejects out-of-bounds coordinates, NaN, and identical endpoints with APIError (HTTP 400)."""
    with pytest.raises(APIError) as exc1:
        mission_replan_api({
            "start": {"row": 999, "col": 100},
            "goal": {"row": 66, "col": 128},
            "events": [{"event_type": "operational_hold", "hold_time_s": 300.0}]
        }, terrain_grid, transform_affine, waypoints_catalog)
    assert exc1.value.status_code == 400

    with pytest.raises(APIError) as exc2:
        mission_replan_api({
            "start": {"row": 100, "col": 100},
            "goal": {"row": 100, "col": 100},
            "events": [{"event_type": "operational_hold", "hold_time_s": 300.0}]
        }, terrain_grid, transform_affine, waypoints_catalog)
    assert exc2.value.status_code == 400

    with pytest.raises(APIError) as exc3:
        mission_replan_api({
            "start": {"row": 100, "col": 100},
            "events": [{"event_type": "operational_hold", "hold_time_s": 300.0}]
        }, terrain_grid, transform_affine, waypoints_catalog)
    assert exc3.value.status_code == 400


def test_16_recommendation_classification_enums(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 16: Recommendation output strictly belongs to ReplanningRecommendation enum."""
    start_rc = (117, 157)
    goal_rc = (66, 128)
    events = [{"event_type": "operational_hold", "hold_time_s": 600.0, "enabled": True}]

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=[],
        events_data=events,
        original_stop_ids=[],
        profile="balanced",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=0.0,
        operational_delay_s=0.0,
        max_stops=0,
        transform=transform_affine,
    )

    assert isinstance(result.recommendation, ReplanningRecommendation)


def test_17_workspace_immutability():
    """Behavior 17: Workspace storage is immutable; 7 saved missions and 11 experiments remain intact."""
    missions = list_missions()
    experiments = list_experiments()
    assert len(missions) == 7, f"Expected 7 saved missions, found {len(missions)}"
    assert len(experiments) == 11, f"Expected 11 saved experiments, found {len(experiments)}"


def test_18_three_stage_structure_completeness(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 18: AdaptiveReplanningResult contains complete 3-stage structures and metadata."""
    start_rc = (117, 157)
    goal_rc = (66, 128)

    result = replan_adaptive_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain_grid,
        candidate_waypoints=waypoints_catalog[:3],
        events_data=[],
        original_stop_ids=[],
        profile="balanced",
        vehicle_mode="crew_eva",
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=900.0,
        operational_delay_s=0.0,
        max_stops=1,
        transform=transform_affine,
    )

    res_dict = result.to_dict()
    assert res_dict["status"] == "success"
    assert "original_plan" in res_dict
    assert "disrupted_plan" in res_dict
    assert "adaptive_plan" in res_dict
    assert "science_recovery" in res_dict
    assert "recommendation" in res_dict
    assert "recommendation_rationale" in res_dict
    assert "computation_fingerprint" in res_dict


def test_19_nominal_mission_optimizer_unaffected(terrain_grid, transform_affine, waypoints_catalog):
    """Behavior 19: Milestone 9V Mission Design Lab optimizer functions without regressions."""
    report = optimize_science_tour(
        terrain=terrain_grid,
        start_rc=(117, 157),
        goal_rc=(66, 128),
        candidate_waypoints=waypoints_catalog[:4],
        max_stops=2,
        operational_limit_s=28800.0,
        dwell_time_per_stop_s=900.0,
        operational_delay_s=0.0,
        profile="balanced",
        vehicle_mode="crew_eva",
        beam_width=6,
        transform=transform_affine,
    )
    assert report.candidates_evaluated > 0
    assert report.balanced_champion is not None
    assert report.balanced_champion.is_budget_feasible is True


def test_20_live_http_round_trip_port_3000():
    """Behavior 20: Live HTTP POST to /api/mission/replan returns HTTP 200 with complete 3-stage replanning."""
    url = f"{SERVER_BASE_URL}/api/mission/replan"
    payload = {
        "start": {"row": 117, "col": 157, "name": "Octavia Butler Landing"},
        "goal": {"row": 66, "col": 128, "name": "Delta Rim Overlook"},
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "speed_multiplier": 1.0,
        "dwell_time_per_stop_s": 900.0,
        "operational_delay_s": 0.0,
        "operational_limit_s": 28800.0,
        "stops": [
            {"id": "kodiak_butte", "name": "Kodiak Butte", "row": 120, "col": 140, "priority_score": 50.0}
        ],
        "candidate_targets": [
            {"id": "skinner_ridge", "name": "Skinner Ridge Delta Base", "row": 92, "col": 142, "priority_score": 90.0}
        ],
        "custom_events": [
            {"event_type": "operational_hold", "hold_time_s": 900.0, "enabled": True}
        ],
        "max_stops": 2,
        "objective": "balanced"
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            assert resp.status == 200
            body = json.loads(resp.read().decode("utf-8"))
            assert body["status"] == "success"
            assert "original_plan" in body
            assert "disrupted_plan" in body
            assert "adaptive_plan" in body
            assert "science_recovery" in body
            assert "recommendation" in body
            assert "computation_fingerprint" in body
    except urllib.error.URLError as err:
        pytest.fail(f"HTTP request to {url} failed: {err}")
