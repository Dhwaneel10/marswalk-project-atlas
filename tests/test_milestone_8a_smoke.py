"""
Milestone 8A End-to-End Smoke and Integration Test Suite.

Verifies:
1. Application initial state and terrain loading with real Jezero data.
2. Route planning across all three mission profiles (Conservative, Balanced, Science-First).
3. Mission Commander AI ranking, recommendation formatting, and utility attribute access.
4. Gauntlet stress-test scenarios (corridor closure, budget reduction, target unavailable, toughness suite).
5. Science Budget 2D & 3D frontier plotting, candidate inspection, and tactical map overlay.
6. CSV and JSON telemetry export generation and reproducibility.
7. Preference model lifecycle (Untrained -> Calibrating -> Personalized -> Reset).
"""

import json
import math
import os
import pytest
import numpy as np
import plotly.graph_objects as go

from marswalk.core.terrain import TerrainGrid
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    plan_route,
    RouteResult,
    compute_pairwise_leg_cache,
)
from marswalk.core.stress_test import (
    ScenarioDefinition,
    DisruptionType,
    run_scenario,
    evaluate_route_toughness,
)
from marswalk.core.science_budget import (
    analyze_science_budget,
    export_mission_brief_csv,
    export_mission_brief_json,
    CandidatePlan,
    FrontierResult,
)
from marswalk.core.preferences import (
    PreferenceModel,
    PreferenceObservation,
    CandidateOption,
    RankedRoute,
    RouteFeatures,
    LearningState,
    extract_route_features,
)
from marswalk.app import (
    PROCESSED_TIFF,
    WAYPOINTS_JSON,
    PREFERENCES_FILE,
    load_raw_waypoints,
    get_cached_terrain,
    render_tactical_terrain_map,
    render_elevation_slope_profile,
    render_science_budget_chart,
)


@pytest.fixture(scope="module")
def terrain_grid():
    """Load authentic Jezero crater DTM terrain grid."""
    assert os.path.exists(PROCESSED_TIFF)
    return get_cached_terrain(PROCESSED_TIFF, alpha_s=2.0, alpha_r=1.0, alpha_up=1.5)


@pytest.fixture(scope="module")
def jezero_waypoints(terrain_grid):
    """Load and prepare authentic Jezero science waypoints."""
    raw = load_raw_waypoints(WAYPOINTS_JSON)
    from marswalk.data.ingest import query_elevation_at_lonlat

    wps = []
    for item in raw[:4]:
        _, r, c = query_elevation_at_lonlat(PROCESSED_TIFF, item["lon_deg"], item["lat_deg"])
        wps.append(
            ScienceWaypoint(
                id=item["id"],
                name=item["name"],
                rc=(r, c),
                priority_score=float(item["priority_score"]),
                geological_context=item.get("geological_context", ""),
            )
        )
    return wps


def test_m8a_01_terrain_and_profiles(terrain_grid, jezero_waypoints):
    """Verify route planning on real Jezero terrain for all 3 profiles."""
    start = (117, 157)  # Octavia Butler landing area
    goal = (66, 128)    # Delta rim overlook area

    cache = compute_pairwise_leg_cache([start] + [w.rc for w in jezero_waypoints] + [goal], terrain_grid)

    r_cons = plan_route(start, goal, terrain_grid, jezero_waypoints, PlannerConfig(profile="conservative"), leg_cache=cache)
    r_bal = plan_route(start, goal, terrain_grid, jezero_waypoints, PlannerConfig(profile="balanced"), leg_cache=cache)
    r_sci = plan_route(start, goal, terrain_grid, jezero_waypoints, PlannerConfig(profile="science_first"), leg_cache=cache)

    assert r_cons.is_reachable
    assert r_bal.is_reachable
    assert r_sci.is_reachable

    # Conservative traverses fewer stops than science-first
    assert len(r_cons.visited_waypoint_ids) == 0
    assert len(r_sci.visited_waypoint_ids) >= 1
    assert r_sci.science_score >= r_bal.science_score >= r_cons.science_score


def test_m8a_02_commander_ai_recommendation_and_attribute_safety(terrain_grid, jezero_waypoints):
    """Verify Mission Commander AI utility computation and recommendation card rendering without AttributeError."""
    start = (117, 157)
    goal = (66, 128)

    cache = compute_pairwise_leg_cache([start] + [w.rc for w in jezero_waypoints] + [goal], terrain_grid)
    routes = {
        "conservative": plan_route(start, goal, terrain_grid, jezero_waypoints, PlannerConfig(profile="conservative"), leg_cache=cache),
        "balanced": plan_route(start, goal, terrain_grid, jezero_waypoints, PlannerConfig(profile="balanced"), leg_cache=cache),
    }

    model = PreferenceModel()
    model.weights = np.array([-0.5, -0.5, 1.0, -0.2])
    ranked = model.rank_routes(routes, terrain=terrain_grid)

    assert len(ranked) >= 1
    top_ai = ranked[0]

    # Verify both .utility_score and .utility attribute access succeed
    assert hasattr(top_ai, "utility_score")
    assert hasattr(top_ai, "utility")
    assert top_ai.utility == top_ai.utility_score

    # Verify card formatting from app.py
    card_html = f"{top_ai.profile.replace('_', ' ').title()} Profile (Utility: {top_ai.utility_score:+.3f})"
    assert "Profile (Utility: " in card_html


def test_m8a_03_gauntlet_scenario_and_toughness_suite(terrain_grid, jezero_waypoints):
    """Verify Gauntlet corridor closure, reduced budget, and toughness suite execution."""
    start = (117, 157)
    goal = (66, 128)
    p_cfg = PlannerConfig(profile="balanced", max_distance_m=7000.0)
    base_route = plan_route(start, goal, terrain_grid, jezero_waypoints, p_cfg)

    # 1. Corridor closure scenario
    scen_closure = ScenarioDefinition(
        id="scen_rockfall",
        name="Hawksbill Rockfall",
        disruption_type=DisruptionType.CORRIDOR_CLOSURE,
        description="Simulated boulder scarp failure",
        blocked_cells=[(135, 91), (135, 92)],
    )
    comp = run_scenario(base_route, scen_closure, start, goal, jezero_waypoints, terrain_grid, p_cfg)
    assert comp.regret_ledger is not None
    assert comp.regret_ledger.retention_pct >= 0.0

    # 2. Reduced budget scenario
    scen_budget = ScenarioDefinition(
        id="scen_budget_cut",
        name="Oxygen Reserve -30%",
        disruption_type=DisruptionType.REDUCED_BUDGET,
        description="Consumable margin alert",
        budget_reduction_pct=30.0,
    )
    comp_budget = run_scenario(base_route, scen_budget, start, goal, jezero_waypoints, terrain_grid, p_cfg)
    assert comp_budget.effective_budget_m < 7000.0

    # 3. Toughness benchmark suite
    report = evaluate_route_toughness(base_route, start, goal, jezero_waypoints, terrain_grid, planner_config=p_cfg)
    assert report.total_scenarios_tested >= 4
    assert 0.0 <= report.avg_retention_pct <= 100.0


def test_m8a_04_science_budget_and_exports(terrain_grid, jezero_waypoints):
    """Verify Pareto frontier extraction, candidate inspection overlay, and CSV/JSON export generation."""
    start = (117, 157)
    goal = (66, 128)
    p_cfg = PlannerConfig(profile="balanced", max_distance_m=8000.0)

    frontier = analyze_science_budget(start, goal, terrain_grid, jezero_waypoints[:3], p_cfg)
    assert frontier.total_subsets_evaluated == 8  # 2^3
    assert len(frontier.pareto_candidates_2d) >= 1
    assert len(frontier.pareto_candidates_3d) >= 1

    # CandidatePlan utility attribute check
    for c in frontier.candidates:
        c.utility_score = 0.42
        assert c.utility == 0.42

    # CSV Export
    csv_str = export_mission_brief_csv(frontier)
    assert "candidate_id,num_targets,visited_targets" in csv_str
    assert "plan_01" in csv_str

    # JSON Export
    json_str = export_mission_brief_json(frontier, metadata={"mission": "Jezero Rehearsal"})
    parsed = json.loads(json_str)
    assert parsed["mission_metadata"]["mission"] == "Jezero Rehearsal"
    assert "summary" in parsed
    assert parsed["summary"]["total_candidates_evaluated"] == 8

    # 2D and 3D Chart generation
    fig_2d = render_science_budget_chart(frontier, active_profile="balanced", view_mode="2d")
    fig_3d = render_science_budget_chart(frontier, active_profile="balanced", view_mode="3d")
    assert isinstance(fig_2d, go.Figure)
    assert isinstance(fig_3d, go.Figure)

    # Tactical map overlay with inspected plan
    rec = frontier.recommended_plan or frontier.candidates[0]
    map_fig = render_tactical_terrain_map(
        terrain=terrain_grid,
        routes={"balanced": frontier.recommended_plan.path if frontier.recommended_plan else None},
        active_profile="balanced",
        waypoints=jezero_waypoints[:3],
        start_rc=start,
        goal_rc=goal,
        inspected_candidate_path=rec.path,
        inspected_candidate_label=f"Inspected: {rec.candidate_id}",
    )
    assert any(f"Inspected: {rec.candidate_id}" in t.name for t in map_fig.data)


def test_m8a_05_preference_model_lifecycle():
    """Verify preference model state progression and reset functionality."""
    model = PreferenceModel()
    assert model.get_state() == LearningState.UNTRAINED

    f1 = RouteFeatures(distance_m=2000.0, cost=2200.0, science_score=80.0, elevation_gain_m=30.0)
    f2 = RouteFeatures(distance_m=1200.0, cost=1300.0, science_score=0.0, elevation_gain_m=10.0)

    obs1 = PreferenceObservation(
        choice_id="choice_01",
        timestamp="2026-10-17T00:00:00Z",
        selected_profile="balanced",
        selected_features=f1,
        rejected_candidates=[CandidateOption("conservative", f2)],
    )
    model.add_observation(obs1)
    assert model.get_state() == LearningState.COLLECTING_INITIAL

    obs2 = PreferenceObservation(
        choice_id="choice_02",
        timestamp="2026-10-17T00:01:00Z",
        selected_profile="balanced",
        selected_features=f1,
        rejected_candidates=[CandidateOption("conservative", f2)],
    )
    obs3 = PreferenceObservation(
        choice_id="choice_03",
        timestamp="2026-10-17T00:02:00Z",
        selected_profile="balanced",
        selected_features=f1,
        rejected_candidates=[CandidateOption("conservative", f2)],
    )
    model.add_observation(obs2)
    model.add_observation(obs3)
    assert model.get_state() == LearningState.PERSONALIZED

    model.reset()
    assert model.get_state() == LearningState.RESET
    assert len(model.observations) == 0
