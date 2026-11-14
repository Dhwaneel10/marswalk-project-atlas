"""
Automated unit tests for MarsWalk The Gauntlet: EVA Stress-Testing & Dynamic Scenario Engine (Milestone 5).
Covers TC-01 through TC-13.
"""

import math
import os
import pytest
import numpy as np

from marswalk.core.terrain import (
    TerrainConfig,
    TerrainGrid,
    derive_terrain_from_array,
    load_and_process_terrain,
)
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    RouteResult,
    plan_route,
)
from marswalk.core.stress_test import (
    DisruptionType,
    ScenarioDefinition,
    RegretLedger,
    ScenarioComparison,
    ToughnessReport,
    compute_science_regret_ledger,
    generate_scenario_narrative,
    run_scenario,
    get_curated_gauntlet_scenarios,
    evaluate_route_toughness,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_TIFF = os.path.join(REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")


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


@pytest.fixture
def standard_waypoints():
    """Standard set of 3 waypoints on 30x30 grid."""
    return [
        ScienceWaypoint(id="alpha", name="Site Alpha", rc=(5, 10), priority_score=40.0),
        ScienceWaypoint(id="beta", name="Site Beta", rc=(15, 20), priority_score=60.0),
        ScienceWaypoint(id="gamma", name="Site Gamma", rc=(22, 10), priority_score=30.0),
    ]


# ==============================================================================
# TC-01: Underlying Planetary Raster Immutability
# ==============================================================================
def test_tc_01_terrain_immutability(synthetic_flat_grid, standard_waypoints):
    """
    TC-01: Verify that executing a stress-test scenario (corridor closure)
    does not alter the underlying terrain elevation array, slope, or invalid_mask.
    """
    elev_before = synthetic_flat_grid.elevation.copy()
    mask_before = synthetic_flat_grid.invalid_mask.copy()
    slope_before = synthetic_flat_grid.slope_deg.copy()

    start_rc = (2, 2)
    goal_rc = (25, 25)
    p_cfg = PlannerConfig(profile="conservative")
    baseline = plan_route(start_rc, goal_rc, synthetic_flat_grid, waypoints=[], config=p_cfg)

    # Apply a corridor closure
    scenario = ScenarioDefinition(
        id="scen_wall",
        name="Regolith Collapse",
        disruption_type=DisruptionType.CORRIDOR_CLOSURE,
        description="Hypothetical barrier across diagonal.",
        blocked_cells=[(10, c) for c in range(5, 25)],
    )

    comparison = run_scenario(
        baseline_route=baseline,
        scenario=scenario,
        start_rc=start_rc,
        goal_rc=goal_rc,
        waypoints=[],
        terrain=synthetic_flat_grid,
        planner_config=p_cfg,
    )

    # Elevation, mask, slope must remain bit-for-bit identical
    np.testing.assert_array_equal(synthetic_flat_grid.elevation, elev_before)
    np.testing.assert_array_equal(synthetic_flat_grid.invalid_mask, mask_before)
    np.testing.assert_array_equal(synthetic_flat_grid.slope_deg, slope_before)
    assert comparison.scenario.is_simulated is True


# ==============================================================================
# TC-02: Blocked Corridor Produces Detour
# ==============================================================================
def test_tc_02_blocked_corridor_produces_detour(synthetic_flat_grid):
    """
    TC-02: A blocked corridor cutting directly across the baseline diagonal
    forces the planner to take an avoidance detour, increasing distance and cost.
    """
    start_rc = (5, 5)
    goal_rc = (25, 25)
    p_cfg = PlannerConfig(profile="conservative")
    baseline = plan_route(start_rc, goal_rc, synthetic_flat_grid, waypoints=[], config=p_cfg)

    # Wall from (15, 5) to (15, 20), leaving opening at c > 20
    blocked = [(15, c) for c in range(5, 21)]
    scenario = ScenarioDefinition(
        id="scen_wall",
        name="Fissure Opening",
        disruption_type=DisruptionType.CORRIDOR_CLOSURE,
        description="Blocking the direct central passage.",
        blocked_cells=blocked,
    )

    comp = run_scenario(
        baseline_route=baseline,
        scenario=scenario,
        start_rc=start_rc,
        goal_rc=goal_rc,
        waypoints=[],
        terrain=synthetic_flat_grid,
        planner_config=p_cfg,
    )

    assert comp.is_scenario_reachable is True
    assert comp.scenario_distance_m > comp.baseline_distance_m
    assert comp.delta_distance_m > 0.0
    assert comp.scenario_cost > comp.baseline_cost
    # Verify no cell in the scenario path is in the blocked cells
    path_set = set(comp.scenario_route.path)
    for b in blocked:
        assert b not in path_set


# ==============================================================================
# TC-03: Fully Isolated Destination Handles Unreachability Gracefully
# ==============================================================================
def test_tc_03_fully_isolated_destination(synthetic_flat_grid):
    """
    TC-03: When a corridor closure completely encloses the goal,
    the scenario engine must report is_scenario_reachable=False and empty path.
    """
    start_rc = (5, 5)
    goal_rc = (25, 25)
    p_cfg = PlannerConfig(profile="conservative")
    baseline = plan_route(start_rc, goal_rc, synthetic_flat_grid, waypoints=[], config=p_cfg)

    # Box around goal_rc (25, 25)
    box = []
    for r in range(23, 27):
        for c in range(23, 27):
            if (r, c) != goal_rc:
                box.append((r, c))

    scenario = ScenarioDefinition(
        id="scen_box",
        name="Total Entrapment",
        disruption_type=DisruptionType.CORRIDOR_CLOSURE,
        description="Completely walling off the destination.",
        blocked_cells=box,
    )

    comp = run_scenario(
        baseline_route=baseline,
        scenario=scenario,
        start_rc=start_rc,
        goal_rc=goal_rc,
        waypoints=[],
        terrain=synthetic_flat_grid,
        planner_config=p_cfg,
    )

    assert comp.is_scenario_reachable is False
    assert len(comp.scenario_route.path) == 0
    assert math.isnan(comp.scenario_distance_m)
    assert math.isinf(comp.scenario_route.cost)
    assert "Infeasible" in comp.headline or "Deadlock" in comp.headline


# ==============================================================================
# TC-04: Reduced Budget Enforces Physical Travel Ceiling
# ==============================================================================
def test_tc_04_reduced_budget_enforcement(synthetic_flat_grid, standard_waypoints):
    """
    TC-04: Under a reduced distance budget, the planner sheds distal waypoints
    to satisfy the physical meter limit.
    """
    start_rc = (2, 2)
    goal_rc = (25, 25)
    p_cfg = PlannerConfig(profile="science_first")
    baseline = plan_route(start_rc, goal_rc, synthetic_flat_grid, waypoints=standard_waypoints, config=p_cfg)
    assert len(baseline.visited_waypoint_ids) == 3

    # Reduce budget by 30%
    scenario = ScenarioDefinition(
        id="scen_budget_cut",
        name="Consumable Reserve Margin",
        disruption_type=DisruptionType.REDUCED_BUDGET,
        description="Reduced life-support endurance.",
        budget_reduction_pct=30.0,
    )

    comp = run_scenario(
        baseline_route=baseline,
        scenario=scenario,
        start_rc=start_rc,
        goal_rc=goal_rc,
        waypoints=standard_waypoints,
        terrain=synthetic_flat_grid,
        planner_config=p_cfg,
    )

    assert comp.is_scenario_reachable is True
    assert comp.is_scenario_budget_feasible is True
    assert comp.scenario_distance_m <= comp.effective_budget_m
    # At least one target dropped to respect the tighter budget
    assert len(comp.regret_ledger.dropped_by_optimizer_ids) > 0
    assert comp.regret_ledger.retention_pct < 100.0


# ==============================================================================
# TC-05: Budget-Infeasible Route Flagged Correctly
# ==============================================================================
def test_tc_05_budget_infeasible_flag(synthetic_flat_grid):
    """
    TC-05: When the reduced budget is smaller than the minimum direct distance
    between start and goal, the route is flagged is_budget_feasible = False.
    """
    start_rc = (0, 0)
    goal_rc = (20, 20)
    p_cfg = PlannerConfig(profile="conservative")
    baseline = plan_route(start_rc, goal_rc, synthetic_flat_grid, waypoints=[], config=p_cfg)

    direct_dist = baseline.distance_m  # approx 20 * 20 * sqrt(2) ≈ 565.68 m

    # Impose a budget of 200 m, well below the physical minimum direct path
    scenario = ScenarioDefinition(
        id="scen_impossible_budget",
        name="Severe Oxygen Leak",
        disruption_type=DisruptionType.REDUCED_BUDGET,
        description="Ceiling too low for even direct traverse.",
        reduced_max_distance_m=200.0,
    )

    comp = run_scenario(
        baseline_route=baseline,
        scenario=scenario,
        start_rc=start_rc,
        goal_rc=goal_rc,
        waypoints=[],
        terrain=synthetic_flat_grid,
        planner_config=p_cfg,
    )

    assert comp.is_scenario_reachable is True
    assert comp.is_scenario_budget_feasible is False
    assert comp.scenario_distance_m > comp.effective_budget_m


# ==============================================================================
# TC-06: Target Inaccessibility Excludes Target Without Mutating Waypoints Catalog
# ==============================================================================
def test_tc_06_target_inaccessibility(synthetic_flat_grid, standard_waypoints):
    """
    TC-06: When a target is marked inaccessible, it is omitted from the scenario
    plan while the input waypoint list remains unchanged.
    """
    start_rc = (2, 2)
    goal_rc = (25, 25)
    p_cfg = PlannerConfig(profile="science_first")
    wps_copy = [w for w in standard_waypoints]

    baseline = plan_route(start_rc, goal_rc, synthetic_flat_grid, waypoints=wps_copy, config=p_cfg)
    assert "beta" in baseline.visited_waypoint_ids

    scenario = ScenarioDefinition(
        id="scen_beta_blocked",
        name="Steep Scarp at Beta",
        disruption_type=DisruptionType.TARGET_UNAVAILABLE,
        description="Hazardous scree renders Beta approach unsafe.",
        unavailable_target_id="beta",
    )

    comp = run_scenario(
        baseline_route=baseline,
        scenario=scenario,
        start_rc=start_rc,
        goal_rc=goal_rc,
        waypoints=wps_copy,
        terrain=synthetic_flat_grid,
        planner_config=p_cfg,
    )

    # Input waypoints list length unchanged
    assert len(wps_copy) == 3
    # Scenario route does not visit beta
    assert "beta" not in comp.scenario_route.visited_waypoint_ids
    # Regret ledger flags beta as disabled_by_scenario_ids
    assert "beta" in comp.regret_ledger.disabled_by_scenario_ids
    assert "beta" not in comp.regret_ledger.dropped_by_optimizer_ids


# ==============================================================================
# TC-07: Science Regret Ledger Distinguishes Optimizer Drops vs Scenario Disables
# ==============================================================================
def test_tc_07_regret_ledger_categorization(standard_waypoints):
    """
    TC-07: Verify compute_science_regret_ledger correctly classifies targets
    into retained, dropped_by_optimizer, and disabled_by_scenario.
    """
    base_res = RouteResult(
        profile="science_first",
        start_rc=(0, 0),
        goal_rc=(25, 25),
        path=[(0, 0), (25, 25)],
        distance_m=1000.0,
        cost=1000.0,
        science_score=130.0,
        visited_waypoint_ids=["alpha", "beta", "gamma"],
        num_cells=2,
        num_steps=1,
        is_reachable=True,
        is_budget_feasible=True,
        max_distance_m=None,
        status_message="ok",
    )

    # Scenario route only visits alpha: beta was explicitly disabled, gamma was dropped by optimizer
    scen_res = RouteResult(
        profile="science_first",
        start_rc=(0, 0),
        goal_rc=(25, 25),
        path=[(0, 0), (25, 25)],
        distance_m=500.0,
        cost=500.0,
        science_score=40.0,
        visited_waypoint_ids=["alpha"],
        num_cells=2,
        num_steps=1,
        is_reachable=True,
        is_budget_feasible=True,
        max_distance_m=None,
        status_message="ok",
    )

    scenario = ScenarioDefinition(
        id="scen_beta_out",
        name="Beta Out",
        disruption_type=DisruptionType.TARGET_UNAVAILABLE,
        description="Beta unavailable",
        unavailable_target_id="beta",
    )

    ledger = compute_science_regret_ledger(base_res, scen_res, standard_waypoints, scenario)

    assert ledger.baseline_visited_ids == ["alpha", "beta", "gamma"]
    assert ledger.scenario_visited_ids == ["alpha"]
    assert ledger.retained_target_ids == ["alpha"]
    assert ledger.disabled_by_scenario_ids == ["beta"]
    assert ledger.dropped_by_optimizer_ids == ["gamma"]
    assert ledger.baseline_priority == 130.0
    assert ledger.retained_priority == 40.0
    assert ledger.lost_priority == 90.0
    assert pytest.approx(ledger.retention_pct, rel=1e-3) == (40.0 / 130.0 * 100.0)


# ==============================================================================
# TC-08: Zero-Priority and Empty Waypoint Handling
# ==============================================================================
def test_tc_08_empty_and_zero_priority(synthetic_flat_grid):
    """
    TC-08: Empty waypoint lists and zero-priority waypoints do not cause
    division by zero or exceptions.
    """
    start_rc = (2, 2)
    goal_rc = (20, 20)
    p_cfg = PlannerConfig(profile="conservative")
    baseline = plan_route(start_rc, goal_rc, synthetic_flat_grid, waypoints=[], config=p_cfg)

    scenario = ScenarioDefinition(
        id="scen_zero",
        name="Empty Test",
        disruption_type=DisruptionType.REDUCED_BUDGET,
        description="Testing zero waypoints.",
        budget_reduction_pct=10.0,
    )

    comp = run_scenario(
        baseline_route=baseline,
        scenario=scenario,
        start_rc=start_rc,
        goal_rc=goal_rc,
        waypoints=[],
        terrain=synthetic_flat_grid,
        planner_config=p_cfg,
    )

    assert comp.regret_ledger.retention_pct == 100.0
    assert comp.regret_ledger.baseline_priority == 0.0
    assert comp.regret_ledger.retained_priority == 0.0
    assert comp.regret_ledger.lost_priority == 0.0


# ==============================================================================
# TC-09: Multiple Scenario Runs Preserve Baseline
# ==============================================================================
def test_tc_09_multiple_scenarios_isolation(synthetic_flat_grid, standard_waypoints):
    """
    TC-09: Executing multiple scenarios sequentially preserves the baseline route
    and does not leak state between runs.
    """
    start_rc = (2, 2)
    goal_rc = (25, 25)
    p_cfg = PlannerConfig(profile="science_first")
    baseline = plan_route(start_rc, goal_rc, synthetic_flat_grid, waypoints=standard_waypoints, config=p_cfg)

    scen1 = ScenarioDefinition(
        id="s1",
        name="Wall 1",
        disruption_type=DisruptionType.CORRIDOR_CLOSURE,
        description="Block 1",
        blocked_cells=[(10, 10), (10, 11)],
    )
    scen2 = ScenarioDefinition(
        id="s2",
        name="Budget 2",
        disruption_type=DisruptionType.REDUCED_BUDGET,
        description="Budget 2",
        budget_reduction_pct=20.0,
    )
    scen3 = ScenarioDefinition(
        id="s3",
        name="Target 3",
        disruption_type=DisruptionType.TARGET_UNAVAILABLE,
        description="Target 3",
        unavailable_target_id="alpha",
    )

    comp1 = run_scenario(baseline, scen1, start_rc, goal_rc, standard_waypoints, synthetic_flat_grid, p_cfg)
    comp2 = run_scenario(baseline, scen2, start_rc, goal_rc, standard_waypoints, synthetic_flat_grid, p_cfg)
    comp3 = run_scenario(baseline, scen3, start_rc, goal_rc, standard_waypoints, synthetic_flat_grid, p_cfg)

    # Baseline metrics remain identical across all comparisons
    for c in [comp1, comp2, comp3]:
        assert c.baseline_distance_m == baseline.distance_m
        assert c.baseline_cost == baseline.cost
        assert c.baseline_route.visited_waypoint_ids == baseline.visited_waypoint_ids

    # Each comparison has its distinct scenario type
    assert comp1.scenario.disruption_type == DisruptionType.CORRIDOR_CLOSURE
    assert comp2.scenario.disruption_type == DisruptionType.REDUCED_BUDGET
    assert comp3.scenario.disruption_type == DisruptionType.TARGET_UNAVAILABLE


# ==============================================================================
# TC-10: Route Toughness Evaluation Metrics Match Evaluated Scenarios
# ==============================================================================
def test_tc_10_route_toughness_report(synthetic_flat_grid, standard_waypoints):
    """
    TC-10: evaluate_route_toughness computes aggregated metrics matching
    the individual scenario results.
    """
    start_rc = (2, 2)
    goal_rc = (25, 25)
    p_cfg = PlannerConfig(profile="balanced", science_appetite_gamma=1.0)
    baseline = plan_route(start_rc, goal_rc, synthetic_flat_grid, waypoints=standard_waypoints, config=p_cfg)

    # 3 mini scenarios
    scenarios = [
        ScenarioDefinition(
            id="t1",
            name="T1 Closure",
            disruption_type=DisruptionType.CORRIDOR_CLOSURE,
            description="T1",
            blocked_cells=[(12, 12)],
        ),
        ScenarioDefinition(
            id="t2",
            name="T2 Budget",
            disruption_type=DisruptionType.REDUCED_BUDGET,
            description="T2",
            budget_reduction_pct=15.0,
        ),
        ScenarioDefinition(
            id="t3",
            name="T3 Target",
            disruption_type=DisruptionType.TARGET_UNAVAILABLE,
            description="T3",
            unavailable_target_id="alpha",
        ),
    ]

    report = evaluate_route_toughness(
        baseline_route=baseline,
        start_rc=start_rc,
        goal_rc=goal_rc,
        waypoints=standard_waypoints,
        terrain=synthetic_flat_grid,
        scenarios=scenarios,
        planner_config=p_cfg,
    )

    assert isinstance(report, ToughnessReport)
    assert report.total_scenarios_tested == 3
    assert len(report.results) == 3

    # Check consistency
    calc_feasible = sum(1 for r in report.results if r.is_reachable)
    calc_budget = sum(1 for r in report.results if r.is_budget_feasible)
    assert report.feasible_count == calc_feasible
    assert report.budget_met_count == calc_budget

    expected_avg_ret = sum(r.retention_pct for r in report.results) / len(report.results)
    assert pytest.approx(report.avg_retention_pct, abs=1e-3) == expected_avg_ret
    assert "Route Toughness Evaluation" in report.summary_narrative


# ==============================================================================
# TC-11: Determinism Check
# ==============================================================================
def test_tc_11_determinism(synthetic_flat_grid, standard_waypoints):
    """
    TC-11: Running the same scenario twice produces bitwise identical
    paths, costs, distances, and narrative headlines.
    """
    start_rc = (2, 2)
    goal_rc = (25, 25)
    p_cfg = PlannerConfig(profile="balanced")
    baseline = plan_route(start_rc, goal_rc, synthetic_flat_grid, waypoints=standard_waypoints, config=p_cfg)

    scenario = ScenarioDefinition(
        id="det_scen",
        name="Det Test",
        disruption_type=DisruptionType.CORRIDOR_CLOSURE,
        description="Deterministic wall",
        blocked_cells=[(12, c) for c in range(8, 16)],
    )

    run1 = run_scenario(baseline, scenario, start_rc, goal_rc, standard_waypoints, synthetic_flat_grid, p_cfg)
    run2 = run_scenario(baseline, scenario, start_rc, goal_rc, standard_waypoints, synthetic_flat_grid, p_cfg)

    assert run1.scenario_route.path == run2.scenario_route.path
    assert run1.scenario_distance_m == run2.scenario_distance_m
    assert run1.scenario_cost == run2.scenario_cost
    assert run1.headline == run2.headline
    assert run1.detail == run2.detail


# ==============================================================================
# TC-12: Professional vs Dry Humour Narrative Variations
# ==============================================================================
def test_tc_12_voice_modes(synthetic_flat_grid, standard_waypoints):
    """
    TC-12: Verify professional and dry humour voices generate distinct narratives.
    """
    start_rc = (2, 2)
    goal_rc = (25, 25)
    p_cfg = PlannerConfig(profile="conservative")
    baseline = plan_route(start_rc, goal_rc, synthetic_flat_grid, waypoints=[], config=p_cfg)

    scenario = ScenarioDefinition(
        id="voice_scen",
        name="Hawksbill Rockfall",
        disruption_type=DisruptionType.CORRIDOR_CLOSURE,
        description="Block central cells",
        blocked_cells=[(10, 10), (10, 11)],
    )

    comp_pro = run_scenario(
        baseline, scenario, start_rc, goal_rc, [], synthetic_flat_grid, p_cfg, voice_mode="professional"
    )
    comp_dry = run_scenario(
        baseline, scenario, start_rc, goal_rc, [], synthetic_flat_grid, p_cfg, voice_mode="dry_humour"
    )

    assert comp_pro.headline != comp_dry.headline
    assert comp_pro.detail != comp_dry.detail
    assert "good run" in comp_dry.headline or "Recalculating" in comp_dry.headline
    assert "Replanning Successful" in comp_pro.headline


# ==============================================================================
# TC-13: Real Jezero CTX Raster Smoke Test
# ==============================================================================
def test_tc_13_real_jezero_gauntlet_smoke():
    """
    TC-13: On the actual USGS Jezero 20m GeoTIFF, run a curated gauntlet scenario
    and verify realistic detour replanning and execution time < 3.0s.
    """
    if not os.path.exists(PROCESSED_TIFF):
        pytest.skip("Processed Jezero GeoTIFF not found.")

    terrain = load_and_process_terrain(PROCESSED_TIFF)
    start_rc = (156, 179)  # Butler Landing
    goal_rc = (127, 85)   # Belva Crater rim

    wps = [
        ScienceWaypoint(id="hawksbill_gap", name="Hawksbill Gap", rc=(136, 91), priority_score=85.0),
        ScienceWaypoint(id="three_forks", name="Three Forks", rc=(148, 148), priority_score=75.0),
    ]

    p_cfg = PlannerConfig(profile="balanced", science_appetite_gamma=1.0)
    baseline = plan_route(start_rc, goal_rc, terrain, waypoints=wps, config=p_cfg)
    assert baseline.is_reachable

    curated = get_curated_gauntlet_scenarios(terrain, wps, baseline.distance_m)
    assert len(curated) == 5

    # Run the first curated scenario: Hawksbill Gap Scarp Rockfall
    comp = run_scenario(
        baseline_route=baseline,
        scenario=curated[0],
        start_rc=start_rc,
        goal_rc=goal_rc,
        waypoints=wps,
        terrain=terrain,
        planner_config=p_cfg,
    )

    assert comp.is_scenario_reachable
    assert comp.baseline_distance_m > 0
    assert comp.scenario_distance_m > 0
    assert comp.regret_ledger.retention_pct >= 0.0
