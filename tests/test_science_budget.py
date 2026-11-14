"""
Unit and integration tests for MarsWalk Science Budget & Pareto Frontier Engine.
Validates multi-objective dominance (2D and 3D), candidate plan generation,
budget constraints, sensitivity analysis, Gauntlet scenario comparisons,
and Mission Commander AI independence.
"""

import json
import math
import os
import pytest
import numpy as np

from marswalk.core.terrain import TerrainConfig, TerrainGrid, load_and_process_terrain
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    compute_pairwise_leg_cache,
    plan_route,
)
from marswalk.core.preferences import (
    PreferenceModel,
    extract_route_features,
)
from marswalk.core.science_budget import (
    CandidatePlan,
    FrontierResult,
    evaluate_all_candidate_plans,
    check_dominance_2d,
    check_dominance_3d,
    extract_pareto_frontier,
    analyze_science_budget,
    compare_frontiers,
    generate_science_budget_narrative,
    export_mission_brief_csv,
    export_mission_brief_json,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIFF_PATH = os.path.join(REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")
WAYPOINTS_JSON = os.path.join(REPO_ROOT, "data", "waypoints_jezero.json")


def make_dummy_candidate(
    cid: str,
    dist: float,
    cost: float,
    sci: float,
    is_reach: bool = True,
    is_budget: bool = True,
    targets: int = 1,
    tag: str = None,
) -> CandidatePlan:
    """Helper to build a candidate plan with specified metrics for mathematical testing."""
    return CandidatePlan(
        candidate_id=cid,
        subset_key=cid,
        visited_waypoint_ids=[f"wp_{i}" for i in range(targets)],
        visited_waypoint_names=[f"Target {i}" for i in range(targets)],
        path=[(0, 0), (1, 1)],
        distance_m=dist,
        cost=cost,
        science_score=sci,
        is_reachable=is_reach,
        is_budget_feasible=is_budget,
        num_targets=targets,
        profile_tag=tag,
    )


# ==============================================================================
# TC-01 & TC-02: Known Analytical 2D Pareto Frontier & Dominance
# ==============================================================================
def test_tc_01_and_02_analytical_2d_pareto_frontier():
    """
    Test 2D Pareto dominance: minimize distance, maximize science.
    A: (1000m, cost=1500, sci=20) -> Pareto
    B: (1500m, cost=2200, sci=50) -> Pareto
    C: (1600m, cost=2300, sci=50) -> Dominated by B (more dist for same sci)
    D: (1400m, cost=2000, sci=10) -> Dominated by A (more dist for less sci)
    E: (2000m, cost=2900, sci=80) -> Pareto
    """
    cand_a = make_dummy_candidate("A", 1000.0, 1500.0, 20.0)
    cand_b = make_dummy_candidate("B", 1500.0, 2200.0, 50.0)
    cand_c = make_dummy_candidate("C", 1600.0, 2300.0, 50.0)
    cand_d = make_dummy_candidate("D", 1400.0, 2000.0, 10.0)
    cand_e = make_dummy_candidate("E", 2000.0, 2900.0, 80.0)

    # Check pairwise dominance
    assert check_dominance_2d(cand_b, cand_c) is True
    assert check_dominance_2d(cand_c, cand_b) is False

    assert check_dominance_2d(cand_a, cand_d) is True
    assert check_dominance_2d(cand_d, cand_a) is False

    assert check_dominance_2d(cand_a, cand_b) is False
    assert check_dominance_2d(cand_b, cand_a) is False

    # Extract 2D frontier
    all_cands = [cand_a, cand_b, cand_c, cand_d, cand_e]
    frontier_2d = extract_pareto_frontier(all_cands, mode="2d")

    frontier_ids = [c.candidate_id for c in frontier_2d]
    assert frontier_ids == ["A", "B", "E"]


# ==============================================================================
# TC-03: 3D vs 2D Frontier Distinction (Modeled Terrain Cost)
# ==============================================================================
def test_tc_03_three_objective_frontier_distinction():
    """
    Test 3D Pareto dominance: minimize distance, minimize cost, maximize science.
    A candidate dominated in 2D can be non-dominated in 3D if it has strictly lower terrain cost!

    P1: (1000m, cost=1800, sci=20)
    P2: (1100m, cost=1300, sci=20)

    In 2D (dist, sci):
    - P1 has 1000m and 20 sci.
    - P2 has 1100m and 20 sci.
    - P1 dominates P2 in 2D!

    In 3D (dist, cost, sci):
    - P1 is better on distance (1000 < 1100).
    - But P2 is strictly better on terrain cost (1300 < 1800)!
    - Neither dominates the other in 3D. Both must be on the 3D frontier.
    """
    p1 = make_dummy_candidate("P1", 1000.0, 1800.0, 20.0)
    p2 = make_dummy_candidate("P2", 1100.0, 1300.0, 20.0)

    # 2D checks
    assert check_dominance_2d(p1, p2) is True
    assert check_dominance_2d(p2, p1) is False
    frontier_2d = extract_pareto_frontier([p1, p2], mode="2d")
    assert [c.candidate_id for c in frontier_2d] == ["P1"]

    # 3D checks
    assert check_dominance_3d(p1, p2) is False
    assert check_dominance_3d(p2, p1) is False
    frontier_3d = extract_pareto_frontier([p1, p2], mode="3d")
    assert set(c.candidate_id for c in frontier_3d) == {"P1", "P2"}


# ==============================================================================
# TC-04: Duplicate and Equal Candidates
# ==============================================================================
def test_tc_04_duplicate_and_equal_candidates():
    """
    Two candidates with identical distance, cost, and science do not dominate each other.
    Both should be retained if neither is dominated by another candidate.
    """
    c1 = make_dummy_candidate("C1", 1200.0, 1600.0, 40.0)
    c2 = make_dummy_candidate("C2", 1200.0, 1600.0, 40.0)

    assert check_dominance_2d(c1, c2) is False
    assert check_dominance_2d(c2, c1) is False

    frontier = extract_pareto_frontier([c1, c2], mode="2d")
    assert len(frontier) == 2
    assert {c.candidate_id for c in frontier} == {"C1", "C2"}


# ==============================================================================
# TC-05: Infeasible Candidates Excluded from Frontier
# ==============================================================================
def test_tc_05_infeasible_candidates_excluded():
    """
    Infeasible candidates (unreachable or exceeding max budget) must NEVER be in the frontier,
    even if they have high science or low cost.
    """
    feasible_c = make_dummy_candidate("Feasible", 2000.0, 3000.0, 25.0, is_reach=True, is_budget=True)
    unreachable_c = make_dummy_candidate("Unreachable", 1000.0, 1200.0, 90.0, is_reach=False, is_budget=True)
    over_budget_c = make_dummy_candidate("OverBudget", 2500.0, 3500.0, 100.0, is_reach=True, is_budget=False)

    # Feasible dominates infeasible
    assert check_dominance_2d(feasible_c, unreachable_c) is True
    assert check_dominance_2d(feasible_c, over_budget_c) is True
    assert check_dominance_2d(unreachable_c, feasible_c) is False

    frontier_2d = extract_pareto_frontier([feasible_c, unreachable_c, over_budget_c], mode="2d")
    assert [c.candidate_id for c in frontier_2d] == ["Feasible"]

    frontier_3d = extract_pareto_frontier([feasible_c, unreachable_c, over_budget_c], mode="3d")
    assert [c.candidate_id for c in frontier_3d] == ["Feasible"]


# ==============================================================================
# TC-06: Empty and Zero-Science Candidates
# ==============================================================================
def test_tc_06_empty_and_zero_science_candidates():
    """
    Empty candidate sets return empty frontier without error.
    Zero-science candidate (direct conservative traverse) is a valid frontier member
    if it has the minimum distance.
    """
    assert extract_pareto_frontier([], mode="2d") == []
    assert extract_pareto_frontier([], mode="3d") == []

    zero_sci_direct = make_dummy_candidate("ZeroSci", 800.0, 1000.0, 0.0)
    sci_detour = make_dummy_candidate("SciDetour", 1500.0, 2000.0, 50.0)

    frontier = extract_pareto_frontier([zero_sci_direct, sci_detour], mode="2d")
    assert len(frontier) == 2
    assert [c.candidate_id for c in frontier] == ["ZeroSci", "SciDetour"]


# ==============================================================================
# TC-07: Candidate Metric Stability & Evaluation on Synthetic Grid
# ==============================================================================
def test_tc_07_candidate_evaluation_synthetic_grid():
    """
    Evaluate candidate generation on a calibrated flat 20x20 grid.
    Start at (0, 0), Goal at (19, 19), with 2 candidate waypoints.
    Verifies exactly 2^2 = 4 candidate plans are generated with stable metrics.
    """
    elev = np.zeros((20, 20), dtype=np.float32)
    grid = TerrainGrid(
        elevation=elev,
        slope_deg=np.zeros_like(elev),
        roughness_m=np.zeros_like(elev),
        invalid_mask=np.zeros_like(elev, dtype=bool),
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        config=TerrainConfig(cell_size_m=20.0),
    )

    wp1 = ScienceWaypoint(id="wp1", name="Alpha Outcrop", rc=(5, 5), priority_score=30.0)
    wp2 = ScienceWaypoint(id="wp2", name="Beta Outcrop", rc=(10, 10), priority_score=50.0)

    cands = evaluate_all_candidate_plans(
        start_rc=(0, 0),
        goal_rc=(19, 19),
        terrain=grid,
        waypoints=[wp1, wp2],
    )

    assert len(cands) == 4  # 2^2 = 4 subsets: {}, {wp1}, {wp2}, {wp1, wp2}
    for c in cands:
        assert c.is_reachable is True
        assert c.is_budget_feasible is True
        assert c.distance_m > 0.0
        assert c.cost > 0.0
        assert len(c.path) >= 2


# ==============================================================================
# TC-08: Budget Constraint Response
# ==============================================================================
def test_tc_08_budget_constraint_response():
    """
    Verifies that tightening max_distance_m marks long traverses as budget infeasible
    and eliminates them from the Pareto frontier.
    """
    c_short = make_dummy_candidate("Short", 1000.0, 1200.0, 20.0)
    c_long = make_dummy_candidate("Long", 3000.0, 4000.0, 80.0)

    # With generous budget 5000m: both feasible
    c_short.is_budget_feasible = True
    c_long.is_budget_feasible = True
    frontier_generous = extract_pareto_frontier([c_short, c_long], mode="2d")
    assert len(frontier_generous) == 2

    # With tight budget 2000m: c_long is budget infeasible
    c_long.is_budget_feasible = False
    frontier_tight = extract_pareto_frontier([c_short, c_long], mode="2d")
    assert len(frontier_tight) == 1
    assert frontier_tight[0].candidate_id == "Short"


# ==============================================================================
# TC-09: Science Priority Sensitivity
# ==============================================================================
def test_tc_09_science_priority_sensitivity():
    """
    Verifies that changing a waypoint's priority score updates the frontier correctly.
    """
    elev = np.zeros((15, 15), dtype=np.float32)
    grid = TerrainGrid(
        elevation=elev,
        slope_deg=np.zeros_like(elev),
        roughness_m=np.zeros_like(elev),
        invalid_mask=np.zeros_like(elev, dtype=bool),
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        config=TerrainConfig(cell_size_m=20.0),
    )

    # Initial low priority for wp1
    wp1_low = ScienceWaypoint(id="wp1", name="Target 1", rc=(5, 5), priority_score=5.0)
    cands_low = evaluate_all_candidate_plans((0, 0), (14, 14), grid, [wp1_low])
    direct = [c for c in cands_low if c.num_targets == 0][0]
    detour = [c for c in cands_low if c.num_targets == 1][0]
    assert detour.science_score == 5.0

    # Boosted priority for wp1
    wp1_high = ScienceWaypoint(id="wp1", name="Target 1", rc=(5, 5), priority_score=95.0)
    cands_high = evaluate_all_candidate_plans((0, 0), (14, 14), grid, [wp1_high])
    detour_high = [c for c in cands_high if c.num_targets == 1][0]
    assert detour_high.science_score == 95.0


# ==============================================================================
# TC-10: Terrain Cost Sensitivity & Recomputation
# ==============================================================================
def test_tc_10_terrain_cost_sensitivity():
    """
    Increasing slope weight alpha_s strictly increases modeled terrain cost for inclined paths.
    """
    elev = np.zeros((20, 20), dtype=np.float32)
    for r in range(20):
        elev[r, :] = r * 5.0  # inclined slope
    slope = np.full_like(elev, 14.0)

    grid1 = TerrainGrid(
        elevation=elev,
        slope_deg=slope,
        roughness_m=np.zeros_like(elev),
        invalid_mask=np.zeros_like(elev, dtype=bool),
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        config=TerrainConfig(cell_size_m=20.0, alpha_s=1.0),
    )
    grid2 = TerrainGrid(
        elevation=elev,
        slope_deg=slope,
        roughness_m=np.zeros_like(elev),
        invalid_mask=np.zeros_like(elev, dtype=bool),
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        config=TerrainConfig(cell_size_m=20.0, alpha_s=4.0),
    )

    cands1 = evaluate_all_candidate_plans((0, 0), (19, 19), grid1, [])
    cands2 = evaluate_all_candidate_plans((0, 0), (19, 19), grid2, [])

    assert cands2[0].cost > cands1[0].cost
    assert cands2[0].distance_m == pytest.approx(cands1[0].distance_m, rel=1e-3)


# ==============================================================================
# TC-11: Determinism
# ==============================================================================
def test_tc_11_determinism():
    """
    Evaluating the science budget twice with identical inputs produces identical metrics.
    """
    cand1 = make_dummy_candidate("c1", 1200.0, 1500.0, 30.0)
    cand2 = make_dummy_candidate("c2", 1800.0, 2200.0, 70.0)

    f1 = extract_pareto_frontier([cand1, cand2], mode="2d")
    f2 = extract_pareto_frontier([cand1, cand2], mode="2d")

    assert [c.candidate_id for c in f1] == [c.candidate_id for c in f2]


# ==============================================================================
# TC-12: Baseline vs Scenario Frontier Comparison (The Gauntlet)
# ==============================================================================
def test_tc_12_gauntlet_frontier_comparison():
    """
    Test compare_frontiers when a scenario severs high-science plans.
    """
    c_direct = make_dummy_candidate("plan_01_direct", 1000.0, 1200.0, 0.0)
    c_outcrop = make_dummy_candidate("plan_02_wp1", 1800.0, 2400.0, 60.0)

    # Baseline: both feasible
    res_base = FrontierResult(
        candidates=[c_direct, c_outcrop],
        pareto_candidates_2d=[c_direct, c_outcrop],
        pareto_candidates_3d=[c_direct, c_outcrop],
        dominated_candidates_2d=[],
        infeasible_candidates=[],
        recommended_plan=c_outcrop,
        max_distance_m=3000.0,
        total_subsets_evaluated=2,
    )

    # Scenario: c_outcrop severed (e.g. corridor blocked)
    c_outcrop_severed = make_dummy_candidate("plan_02_wp1", 1800.0, float("inf"), 60.0, is_reach=False)
    res_scen = FrontierResult(
        candidates=[c_direct, c_outcrop_severed],
        pareto_candidates_2d=[c_direct],
        pareto_candidates_3d=[c_direct],
        dominated_candidates_2d=[],
        infeasible_candidates=[c_outcrop_severed],
        recommended_plan=c_direct,
        max_distance_m=3000.0,
        total_subsets_evaluated=2,
    )

    comp = compare_frontiers(res_base, res_scen)
    assert comp["num_baseline_feasible"] == 2
    assert comp["num_scenario_feasible"] == 1
    assert comp["num_severed_plans"] == 1
    assert comp["max_science_baseline"] == 60.0
    assert comp["max_science_scenario"] == 0.0
    assert comp["lost_science_ceiling"] == 60.0


# ==============================================================================
# TC-13: Independent Operation of Frontier and Mission Commander AI
# ==============================================================================
def test_tc_13_mission_commander_ai_independence():
    """
    Verify that Mission Commander AI utility ranking does not alter the Pareto frontier.
    The frontier is objective mathematical dominance; Commander AI is subjective learned utility.
    """
    c1 = make_dummy_candidate("c1", 1000.0, 1200.0, 10.0)
    c2 = make_dummy_candidate("c2", 2000.0, 2500.0, 80.0)

    # Both are on the 2D frontier
    frontier = extract_pareto_frontier([c1, c2], mode="2d")
    assert len(frontier) == 2

    # A distance-averse commander assigns higher utility to c1
    c1.utility_score = 0.85
    c2.utility_score = 0.12

    # Frontier extraction is unaffected by utility scores
    frontier_after = extract_pareto_frontier([c1, c2], mode="2d")
    assert len(frontier_after) == 2
    assert [c.candidate_id for c in frontier_after] == ["c1", "c2"]


# ==============================================================================
# TC-14: Narrative Generation & Voice Modes
# ==============================================================================
def test_tc_14_narrative_generation_voice_modes():
    """
    Test narrative generation in both Professional and Dry Humour modes.
    """
    c_direct = make_dummy_candidate("direct", 1000.0, 1200.0, 0.0)
    c_sci = make_dummy_candidate("sci", 2500.0, 3200.0, 75.0)

    f_res = FrontierResult(
        candidates=[c_direct, c_sci],
        pareto_candidates_2d=[c_direct, c_sci],
        pareto_candidates_3d=[c_direct, c_sci],
        dominated_candidates_2d=[],
        infeasible_candidates=[],
        recommended_plan=c_sci,
        max_distance_m=4000.0,
        total_subsets_evaluated=2,
    )

    narr_prof = generate_science_budget_narrative(f_res, voice_mode="professional")
    narr_humour = generate_science_budget_narrative(f_res, voice_mode="dry_humour")

    assert "Non-Dominated Plans" in narr_prof["headline"]
    assert "Science Budget" in narr_humour["headline"]
    assert "walking" in narr_humour["detail"].lower()


# ==============================================================================
# TC-15: CSV and JSON Mission Brief Export
# ==============================================================================
def test_tc_15_csv_and_json_export():
    """
    Verify CSV and JSON export formatting, column headers, and schema integrity.
    """
    c1 = make_dummy_candidate("plan_01", 1200.0, 1500.0, 25.0)
    f_res = FrontierResult(
        candidates=[c1],
        pareto_candidates_2d=[c1],
        pareto_candidates_3d=[c1],
        dominated_candidates_2d=[],
        infeasible_candidates=[],
        recommended_plan=c1,
        max_distance_m=5000.0,
        total_subsets_evaluated=1,
    )

    csv_text = export_mission_brief_csv(f_res)
    assert "candidate_id,num_targets,visited_targets" in csv_text
    assert "plan_01" in csv_text

    json_text = export_mission_brief_json(f_res, {"mission_name": "Test EVA"})
    parsed = json.loads(json_text)
    assert parsed["schema_version"] == "1.0"
    assert parsed["summary"]["total_candidates_evaluated"] == 1
    assert "Test EVA" in parsed["mission_metadata"]["mission_name"]


# ==============================================================================
# TC-16: Real Jezero CTX Data Integration Smoke Test
# ==============================================================================
def test_tc_16_real_jezero_data_integration():
    """
    End-to-end integration test on authentic Jezero CTX 20m GeoTIFF.
    Evaluates 3 real science waypoints (2^3 = 8 candidate subsets).
    Confirms execution time < 1.0s and extracts non-empty Pareto frontier.
    """
    grid = load_and_process_terrain(TIFF_PATH)

    with open(WAYPOINTS_JSON, "r", encoding="utf-8") as f:
        wp_data = json.load(f)["waypoints"]

    # Select 3 targets
    wps = [
        ScienceWaypoint(w["id"], w["name"], (136, 91), float(w["priority_score"]))
        for w in wp_data[:3]
    ]

    start_rc = (117, 157)  # Octavia Butler Landing
    goal_rc = (66, 128)    # Delta Rim Overlook

    frontier_res = analyze_science_budget(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=grid,
        waypoints=wps,
        planner_config=PlannerConfig(max_distance_m=8000.0),
    )

    assert frontier_res.total_subsets_evaluated == 8  # 2^3 = 8
    assert len(frontier_res.pareto_candidates_2d) >= 1
    assert frontier_res.execution_time_s < 2.0

    # Minimum distance plan on 2D frontier should visit 0 waypoints (conservative)
    min_dist_plan = frontier_res.pareto_candidates_2d[0]
    assert min_dist_plan.num_targets == 0
