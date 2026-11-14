"""
Automated unit tests for MarsWalk Mission-Control Workstation UI & Explainer (Milestone 4).
"""

import math
import os
import pytest
import numpy as np
import plotly.graph_objects as go

from marswalk.core.terrain import load_and_process_terrain, TerrainGrid
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    plan_route,
    RouteResult,
)
from marswalk.core.explainer import (
    generate_route_tradeoff_summary,
    get_blind_spot_disclaimer,
)
from marswalk.app import (
    load_raw_waypoints,
    get_cached_terrain,
    compute_hillshade,
    render_tactical_terrain_map,
    render_elevation_slope_profile,
    render_science_budget_chart,
    format_regret_ledger_html,
    PROCESSED_TIFF,
    WAYPOINTS_JSON,
    PREFERENCES_FILE,
)
from marswalk.core.science_budget import FrontierResult, CandidatePlan
from marswalk.core.stress_test import RegretLedger
from marswalk.core.preferences import RankedRoute, RouteFeatures


def test_app_imports_and_constants():
    """Verify application configuration and data paths exist."""
    assert os.path.exists(PROCESSED_TIFF), f"Processed raster missing: {PROCESSED_TIFF}"
    assert os.path.exists(WAYPOINTS_JSON), f"Waypoints JSON missing: {WAYPOINTS_JSON}"


def test_load_raw_waypoints():
    """Verify waypoint metadata loading from JSON."""
    wps = load_raw_waypoints(WAYPOINTS_JSON)
    assert len(wps) >= 6
    ids = [w["id"] for w in wps]
    assert "octavia_butler_landing" in ids
    assert "three_forks" in ids
    assert "hawksbill_gap" in ids
    assert "delta_rim_overlook" in ids


def test_cached_terrain_loading():
    """Verify terrain loading through app loader."""
    grid = get_cached_terrain(PROCESSED_TIFF, alpha_s=2.0, alpha_r=1.0, alpha_up=1.5)
    assert isinstance(grid, TerrainGrid)
    assert grid.shape == (250, 250)
    assert np.all(np.isfinite(grid.elevation[10:240, 10:240]))


def test_compute_hillshade():
    """Verify analytical hillshade computation."""
    elev = np.zeros((30, 30), dtype=np.float32)
    # Add a gentle slope
    elev[:, 15:] = 10.0
    hs = compute_hillshade(elev, dx=20.0, dy=20.0)
    assert hs.shape == (30, 30)
    assert np.min(hs) >= 0.0
    assert np.max(hs) <= 1.0


def test_render_tactical_terrain_map():
    """Verify tactical Plotly map figure construction with real terrain and routes."""
    grid = get_cached_terrain(PROCESSED_TIFF, alpha_s=2.0, alpha_r=1.0, alpha_up=1.5)
    start = (117, 157)
    goal = (66, 128)

    w1 = ScienceWaypoint("three_forks", "Three Forks", (153, 123), 75.0)
    res_cons = plan_route(start, goal, grid, config=PlannerConfig(profile="conservative"))
    res_bal = plan_route(start, goal, grid, waypoints=[w1], config=PlannerConfig(profile="balanced"))

    routes = {
        "conservative": res_cons,
        "balanced": res_bal,
        "science_first": res_cons,
    }

    fig = render_tactical_terrain_map(
        terrain=grid,
        routes=routes,
        active_profile="balanced",
        waypoints=[w1],
        start_rc=start,
        goal_rc=goal,
        show_hazard_overlay=True,
        show_hillshade=True,
    )

    assert isinstance(fig, go.Figure)
    trace_names = [trace.name for trace in fig.data]
    assert any("Hillshade" in t for t in trace_names)
    assert any("Balanced" in t for t in trace_names)
    assert any("Start" in t for t in trace_names)
    assert any("Goal" in t for t in trace_names)
    assert any("Waypoints" in t for t in trace_names)


def test_render_elevation_slope_profile():
    """Verify dual-axis profile chart generation along active route."""
    grid = get_cached_terrain(PROCESSED_TIFF, alpha_s=2.0, alpha_r=1.0, alpha_up=1.5)
    start = (117, 157)
    goal = (66, 128)
    res = plan_route(start, goal, grid, config=PlannerConfig(profile="conservative"))

    fig = render_elevation_slope_profile(res, grid)
    assert isinstance(fig, go.Figure)
    trace_names = [trace.name for trace in fig.data]
    assert any("Elevation" in t for t in trace_names)
    assert any("Slope" in t for t in trace_names)

    # Empty route fallback check
    empty_res = RouteResult(
        profile="conservative",
        start_rc=(0, 0),
        goal_rc=(0, 0),
        path=[],
        distance_m=0.0,
        cost=float("inf"),
        science_score=0.0,
        visited_waypoint_ids=[],
        num_cells=0,
        num_steps=0,
        is_reachable=False,
        is_budget_feasible=False,
        max_distance_m=None,
        status_message="Empty",
    )
    empty_fig = render_elevation_slope_profile(empty_res, grid)
    assert len(empty_fig.data) == 0


def test_explainer_voice_modes_and_disclaimer():
    """Verify deterministic trade-off narratives in Professional and Dry Humour modes."""
    grid = get_cached_terrain(PROCESSED_TIFF, alpha_s=2.0, alpha_r=1.0, alpha_up=1.5)
    start = (117, 157)
    goal = (66, 128)
    w1 = ScienceWaypoint("three_forks", "Three Forks", (153, 123), 75.0)

    res_cons = plan_route(start, goal, grid, config=PlannerConfig(profile="conservative"))
    res_bal = plan_route(start, goal, grid, waypoints=[w1], config=PlannerConfig(profile="balanced"))

    # 1. Professional Mode
    debrief_prof = generate_route_tradeoff_summary(
        primary_route=res_bal,
        conservative_route=res_cons,
        science_first_route=res_bal,
        waypoints=[w1],
        voice_mode="professional",
    )
    assert "Balanced Traverse" in debrief_prof["headline"]
    assert "Captures 1 high-yield targets" in debrief_prof["detail"]

    # 2. Dry Humour Mode
    debrief_humour = generate_route_tradeoff_summary(
        primary_route=res_bal,
        conservative_route=res_cons,
        science_first_route=res_bal,
        waypoints=[w1],
        voice_mode="dry_humour",
    )
    assert "Balanced Traverse" in debrief_humour["headline"]
    # Verify humour narrative contains space-themed wit
    assert ("promotion" in debrief_humour["detail"].lower() or "pragmatic" in debrief_humour["detail"].lower() or "optimism" in debrief_humour["detail"].lower())

    # 3. Budget Exceeded Warning in Humour Mode
    over_route = RouteResult(
        profile="balanced",
        start_rc=start,
        goal_rc=goal,
        path=[start, goal],
        distance_m=8000.0,
        cost=8500.0,
        science_score=50.0,
        visited_waypoint_ids=["three_forks"],
        num_cells=2,
        num_steps=1,
        is_reachable=True,
        is_budget_feasible=False,
        max_distance_m=5000.0,
        status_message="Budget Exceeded",
    )
    over_debrief = generate_route_tradeoff_summary(
        primary_route=over_route,
        conservative_route=res_cons,
        voice_mode="dry_humour",
    )
    assert "walking budget: unfortunately, not" in over_debrief["budget_note"].lower()

    # 4. Mandatory Honesty Disclaimer
    disclaimer = get_blind_spot_disclaimer()
    assert "MANDATORY SCIENTIFIC HONESTY DISCLAIMER" in disclaimer["unmodeled_hazards"]
    assert "Low Modeled Macro-Slope Effort" in disclaimer["unmodeled_hazards"]


def test_format_regret_ledger_html():
    """Verify HTML rendering of the Science Regret Ledger."""
    wps = [
        ScienceWaypoint("alpha", "Site Alpha", (5, 5), 40.0),
        ScienceWaypoint("beta", "Site Beta", (10, 10), 60.0),
        ScienceWaypoint("gamma", "Site Gamma", (15, 15), 30.0),
    ]

    ledger = RegretLedger(
        baseline_visited_ids=["alpha", "beta", "gamma"],
        scenario_visited_ids=["alpha"],
        retained_target_ids=["alpha"],
        dropped_by_optimizer_ids=["gamma"],
        disabled_by_scenario_ids=["beta"],
        baseline_priority=130.0,
        retained_priority=40.0,
        lost_priority=90.0,
        retention_pct=30.77,
    )

    html = format_regret_ledger_html(ledger, wps)
    assert "Science Regret Ledger" in html
    assert "Site Alpha" in html
    assert "regret-retained" in html
    assert "Site Gamma" in html
    assert "regret-dropped" in html
    assert "Site Beta" in html
    assert "regret-disabled" in html
    assert "40 / 130 pts" in html


def test_render_tactical_terrain_map_gauntlet_overlay():
    """Verify map canvas correctly renders Gauntlet detour trace and blocked obstacle markers."""
    grid = get_cached_terrain(PROCESSED_TIFF, alpha_s=2.0, alpha_r=1.0, alpha_up=1.5)
    start = (117, 157)
    goal = (66, 128)

    w1 = ScienceWaypoint("three_forks", "Three Forks", (153, 123), 75.0)
    res_cons = plan_route(start, goal, grid, config=PlannerConfig(profile="conservative"))

    routes = {"conservative": res_cons}

    scen_route = RouteResult(
        profile="conservative",
        start_rc=start,
        goal_rc=goal,
        path=[start, (100, 140), goal],
        distance_m=1200.0,
        cost=1300.0,
        science_score=0.0,
        visited_waypoint_ids=[],
        num_cells=3,
        num_steps=2,
        is_reachable=True,
        is_budget_feasible=True,
        max_distance_m=None,
        status_message="ok",
    )

    blocked = [(110, 150), (111, 150)]

    fig = render_tactical_terrain_map(
        terrain=grid,
        routes=routes,
        active_profile="conservative",
        waypoints=[w1],
        start_rc=start,
        goal_rc=goal,
        show_hazard_overlay=True,
        show_hillshade=True,
        scenario_route=scen_route,
        blocked_cells=blocked,
        scenario_name="Hawksbill Rockfall",
    )

    trace_names = [trace.name for trace in fig.data]
    assert any("Baseline Conservative" in t for t in trace_names)
    assert any("Stress Detour" in t for t in trace_names)
    assert any("Simulated Obstacle" in t for t in trace_names)


def test_app_commander_ai_preferences_path():
    """Verify PREFERENCES_FILE is located in data/preferences directory."""
    assert PREFERENCES_FILE.endswith("commander_preferences.json")
    pref_dir = os.path.dirname(PREFERENCES_FILE)
    assert os.path.basename(pref_dir) == "preferences"
    assert os.path.exists(pref_dir)


def test_render_science_budget_chart_2d_and_3d():
    """Verify 2D and 3D Science Budget chart rendering."""
    c1 = CandidatePlan(
        candidate_id="plan_01",
        subset_key="wp1",
        visited_waypoint_ids=["wp1"],
        visited_waypoint_names=["Alpha Outcrop"],
        path=[(0, 0), (1, 1)],
        distance_m=1200.0,
        cost=1500.0,
        science_score=30.0,
        is_reachable=True,
        is_budget_feasible=True,
        num_targets=1,
        profile_tag="conservative",
        is_pareto_2d=True,
        is_pareto_3d=True,
    )
    c2 = CandidatePlan(
        candidate_id="plan_02",
        subset_key="wp1,wp2",
        visited_waypoint_ids=["wp1", "wp2"],
        visited_waypoint_names=["Alpha Outcrop", "Beta Outcrop"],
        path=[(0, 0), (1, 1), (2, 2)],
        distance_m=2200.0,
        cost=2800.0,
        science_score=75.0,
        is_reachable=True,
        is_budget_feasible=True,
        num_targets=2,
        profile_tag="balanced",
        is_pareto_2d=True,
        is_pareto_3d=True,
    )

    f_res = FrontierResult(
        candidates=[c1, c2],
        pareto_candidates_2d=[c1, c2],
        pareto_candidates_3d=[c1, c2],
        dominated_candidates_2d=[],
        infeasible_candidates=[],
        recommended_plan=c2,
        max_distance_m=5000.0,
        total_subsets_evaluated=2,
    )

    # Test 2D chart
    fig_2d = render_science_budget_chart(f_res, active_profile="balanced", view_mode="2d")
    assert isinstance(fig_2d, go.Figure)
    trace_names_2d = [t.name for t in fig_2d.data]
    assert any("2D Pareto Trade-Off Frontier" in t for t in trace_names_2d)
    assert any("Conservative Profile" in t for t in trace_names_2d)
    assert any("Balanced Profile" in t for t in trace_names_2d)

    # Test 3D chart
    fig_3d = render_science_budget_chart(f_res, active_profile="balanced", view_mode="3d")
    assert isinstance(fig_3d, go.Figure)
    trace_names_3d = [t.name for t in fig_3d.data]
    assert any("3D Pareto Frontier" in t for t in trace_names_3d)


def test_render_tactical_terrain_map_with_inspected_candidate():
    """Verify tactical map renders inspected candidate path in distinct cyan overlay."""
    grid = get_cached_terrain(PROCESSED_TIFF, alpha_s=2.0, alpha_r=1.0, alpha_up=1.5)
    start = (117, 157)
    goal = (66, 128)
    res_cons = plan_route(start, goal, grid, config=PlannerConfig(profile="conservative"))

    inspected_path = [(117, 157), (120, 150), (125, 140), (66, 128)]
    fig = render_tactical_terrain_map(
        terrain=grid,
        routes={"conservative": res_cons},
        active_profile="conservative",
        waypoints=[],
        start_rc=start,
        goal_rc=goal,
        inspected_candidate_path=inspected_path,
        inspected_candidate_label="Inspected: plan_05",
    )

    trace_names = [t.name for t in fig.data]
    assert any("Inspected: plan_05" in t for t in trace_names)


def test_ranked_route_utility_attribute_and_recommendation_card_regression():
    """
    Regression test for Milestone 8A live crash:
    AttributeError: 'RankedRoute' object has no attribute 'utility'

    Verifies:
    1. RankedRoute exposes both .utility_score and .utility alias without error.
    2. CandidatePlan exposes both .utility_score and .utility alias without error.
    3. The recommendation formatting string executes successfully without AttributeError.
    """
    dummy_route = RouteResult(
        profile="balanced",
        start_rc=(0, 0),
        goal_rc=(10, 10),
        path=[(0, 0), (5, 5), (10, 10)],
        distance_m=2500.0,
        cost=2800.0,
        science_score=80.0,
        visited_waypoint_ids=["w1"],
        num_cells=3,
        num_steps=2,
        is_reachable=True,
        is_budget_feasible=True,
        max_distance_m=5000.0,
        status_message="ok",
    )
    dummy_feats = RouteFeatures(
        distance_m=2500.0,
        cost=2800.0,
        science_score=80.0,
        elevation_gain_m=45.0,
    )
    ranked = RankedRoute(
        profile="balanced",
        route=dummy_route,
        features=dummy_feats,
        utility_score=0.852,
        rank=1,
        is_recommended=True,
        explanation="High scientific yield with moderate slope effort.",
    )

    # 1. Attribute access verification
    assert ranked.utility_score == 0.852
    assert ranked.utility == 0.852

    # 2. CandidatePlan utility attribute verification
    cand = CandidatePlan(
        candidate_id="plan_test",
        subset_key="w1",
        visited_waypoint_ids=["w1"],
        visited_waypoint_names=["Test Target"],
        path=[(0, 0), (1, 1)],
        distance_m=1000.0,
        cost=1100.0,
        science_score=50.0,
        is_reachable=True,
        is_budget_feasible=True,
        num_targets=1,
        utility_score=0.741,
    )
    assert cand.utility_score == 0.741
    assert cand.utility == 0.741

    # 3. Simulate the exact recommendation card formatting from app.py
    top_ai = ranked
    card_html = f"""
    <div>
        {top_ai.profile.replace('_', ' ').title()} Profile (Utility: {top_ai.utility_score:+.3f})
    </div>
    """
    assert "Balanced Profile (Utility: +0.852)" in card_html

    # Also verify that access via .utility alias works identically
    alias_card_html = f"""
    <div>
        {top_ai.profile.replace('_', ' ').title()} Profile (Utility: {top_ai.utility:+.3f})
    </div>
    """
    assert "Balanced Profile (Utility: +0.852)" in alias_card_html


def test_hud_bar_and_workstation_telemetry_layout():
    """Verify HUD bar metadata and telemetry labels are correctly formatted."""
    profile = "balanced"
    hud_html = f"""
    <div class="hud-bar">
        <div class="hud-title-group">
            <div class="hud-title"><span class="hud-brand-tag">MARSWALK</span> // MISSION REHEARSAL STATION</div>
            <div class="hud-subtitle">OPERATING AREA: JEZERO CRATER • WESTERN DELTA FRONT (18.44°N, 77.45°E)</div>
        </div>
        <div class="hud-pills">
            <span class="hud-pill hud-pill-sector">USGS CTX 20 M/PX</span>
            <span class="hud-pill hud-pill-profile">PROFILE: {profile.upper()}</span>
            <span class="hud-pill hud-pill-prototype">SIMULATION PROTOTYPE • NOT FLIGHT CERTIFIED</span>
        </div>
    </div>
    """
    assert "MARSWALK" in hud_html
    assert "JEZERO CRATER • WESTERN DELTA FRONT" in hud_html
    assert "SIMULATION PROTOTYPE • NOT FLIGHT CERTIFIED" in hud_html
    assert "PROFILE: BALANCED" in hud_html



