"""
Automated unit tests for MarsWalk Route Intelligence Engine (Milestone 3).
Covers TC-01 through TC-14.
"""

import math
import os
import time
import pytest
import numpy as np

from marswalk.core.terrain import (
    TerrainConfig,
    TerrainGrid,
    derive_terrain_from_array,
    load_and_process_terrain,
    calculate_edge_cost,
    calculate_step_distance,
)
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    LegResult,
    RouteResult,
    generalized_octile_heuristic,
    astar_search,
    compute_pairwise_leg_cache,
    stitch_path_legs,
    evaluate_balanced_utility,
    plan_route,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_TIFF = os.path.join(REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")


# ==============================================================================
# TC-01: Flat-Grid Geodesic Shortest Path Identity
# ==============================================================================
def test_tc_01_flat_grid_identity():
    """
    TC-01: On a synthetic flat grid with equal 20m x 20m spacing and zero penalties,
    verify the shortest path from (0,0) to (10,10) takes exactly 10 diagonal steps
    with ground distance = 10 * 20 * sqrt(2) ≈ 282.84 m.
    """
    elev = np.zeros((30, 30), dtype=np.float32)
    cfg = TerrainConfig(
        cell_size_m=20.0,
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        alpha_s=0.0,
        alpha_r=0.0,
        alpha_up=0.0,
    )
    grid = derive_terrain_from_array(elev, config=cfg)

    leg = astar_search((0, 0), (10, 10), grid)
    assert leg.is_reachable
    assert len(leg.path) == 11  # 11 vertices for 10 steps
    expected_dist = 10.0 * 20.0 * math.sqrt(2)
    assert pytest.approx(leg.distance_m, abs=0.01) == expected_dist
    assert pytest.approx(leg.cost, abs=0.01) == expected_dist

    # Verify each step is strictly diagonal
    for i in range(len(leg.path) - 1):
        r1, c1 = leg.path[i]
        r2, c2 = leg.path[i + 1]
        assert abs(r2 - r1) == 1 and abs(c2 - c1) == 1


# ==============================================================================
# TC-02: Calibrated Rectangular Ground Spacing
# ==============================================================================
def test_tc_02_calibrated_rectangular_ground_spacing():
    """
    TC-02: On a grid with unequal ground step lengths (dx = 18.97 m, dy = 20.0 m),
    verify cardinal and diagonal path distances.
    """
    elev = np.zeros((20, 20), dtype=np.float32)
    dx = 18.97
    dy = 20.0
    cfg = TerrainConfig(cell_size_m=20.0, dx_ground_m=dx, dy_ground_m=dy, alpha_s=0.0, alpha_r=0.0, alpha_up=0.0)
    grid = derive_terrain_from_array(elev, config=cfg)

    # East-West step (0,0) -> (0,5): 5 horizontal steps
    leg_ew = astar_search((0, 0), (0, 5), grid)
    assert leg_ew.is_reachable
    assert pytest.approx(leg_ew.distance_m, abs=0.01) == 5 * dx

    # North-South step (0,0) -> (5,0): 5 vertical steps
    leg_ns = astar_search((0, 0), (5, 0), grid)
    assert leg_ns.is_reachable
    assert pytest.approx(leg_ns.distance_m, abs=0.01) == 5 * dy

    # Diagonal step (0,0) -> (5,5): 5 diagonal steps
    leg_diag = astar_search((0, 0), (5, 5), grid)
    assert leg_diag.is_reachable
    expected_diag = 5 * math.sqrt(dx**2 + dy**2)
    assert pytest.approx(leg_diag.distance_m, abs=0.01) == expected_diag


# ==============================================================================
# TC-03: Known Obstacle Detour
# ==============================================================================
def test_tc_03_known_obstacle_detour():
    """
    TC-03: Block a corridor with a vertical impassable barrier bisecting start and goal,
    with a 1-pixel gap at row 15. Verify path routes cleanly through the gap.
    """
    H, W = 25, 25
    elev = np.zeros((H, W), dtype=np.float32)
    # A barrier wall blocking col 12, EXCEPT at rows 14..16 where there is a pass
    elev[:14, 12] = 20.0
    elev[17:, 12] = 20.0

    cfg = TerrainConfig(cell_size_m=20.0, dx_ground_m=20.0, dy_ground_m=20.0, theta_max_deg=25.0)
    grid = derive_terrain_from_array(elev, config=cfg)

    start = (5, 5)
    goal = (5, 20)
    leg = astar_search(start, goal, grid)

    assert leg.is_reachable
    # Verify the path traverses through the gap at (14..16, 12)
    assert (15, 12) in leg.path or (14, 12) in leg.path or (16, 12) in leg.path


# ==============================================================================
# TC-04: NoData and Invalid Terrain Isolation
# ==============================================================================
def test_tc_04_nodata_and_invalid_terrain():
    """
    TC-04: Place a NoData block on the direct path.
    Verify that no successful route contains invalid or dilated NoData cells.
    """
    H, W = 25, 25
    elev = np.zeros((H, W), dtype=np.float32)
    nodata_val = -32768.0
    # NoData block across rows 8 to 14, cols 10 to 14
    elev[8:15, 10:15] = nodata_val

    cfg = TerrainConfig(cell_size_m=20.0, dx_ground_m=20.0, dy_ground_m=20.0, nodata_sentinel=nodata_val)
    grid = derive_terrain_from_array(elev, config=cfg)

    start = (11, 2)
    goal = (11, 22)
    leg = astar_search(start, goal, grid)

    assert leg.is_reachable
    for pt in leg.path:
        assert not grid.invalid_mask[pt[0], pt[1]], f"Path touches invalid cell: {pt}"


# ==============================================================================
# TC-05: Unreachable Destination
# ==============================================================================
def test_tc_05_unreachable_destination():
    """
    TC-05: Encircle the goal with an impassable cliff ring (>= 25°).
    Verify that the planner returns is_reachable = False and empty path.
    """
    H, W = 30, 30
    elev = np.zeros((H, W), dtype=np.float32)
    # Ring of 40m cliff surrounding (15, 15) at distance 2
    for r in range(12, 19):
        for c in range(12, 19):
            if r in (12, 18) or c in (12, 18):
                elev[r, c] = 40.0

    cfg = TerrainConfig(cell_size_m=20.0, dx_ground_m=20.0, dy_ground_m=20.0, theta_max_deg=25.0)
    grid = derive_terrain_from_array(elev, config=cfg)

    start = (2, 2)
    goal = (15, 15)
    leg = astar_search(start, goal, grid)

    assert not leg.is_reachable
    assert leg.path == []
    assert math.isinf(leg.cost)


# ==============================================================================
# TC-06: Directional Uphill/Downhill Traverse Cost
# ==============================================================================
def test_tc_06_directional_cost():
    """
    TC-06: Verify that reverse legs on inclined terrain reflect directional uphill penalties.
    """
    H, W = 20, 20
    # Continuous linear ramp climbing from West to East: dz = 2m per 20m column
    cols = np.tile(np.arange(W), (H, 1))
    elev = (cols * 2.0).astype(np.float32)

    cfg = TerrainConfig(
        cell_size_m=20.0,
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        alpha_s=1.0,
        alpha_r=0.0,
        alpha_up=2.0,
    )
    grid = derive_terrain_from_array(elev, config=cfg)

    start = (10, 2)
    goal = (10, 12)

    # Forward: climbing uphill (elev goes from 4m to 24m)
    leg_fwd = astar_search(start, goal, grid)
    # Reverse: descending downhill (elev goes from 24m to 4m)
    leg_rev = astar_search(goal, start, grid)

    assert leg_fwd.is_reachable and leg_rev.is_reachable
    # Same physical distance
    assert pytest.approx(leg_fwd.distance_m) == leg_rev.distance_m
    # Uphill cost must be strictly greater than downhill cost
    assert leg_fwd.cost > leg_rev.cost


# ==============================================================================
# TC-07: Endpoint Validation
# ==============================================================================
def test_tc_07_endpoint_validation():
    """
    TC-07: Reject out-of-bounds, invalid or malformed endpoints cleanly.
    """
    elev = np.zeros((15, 15), dtype=np.float32)
    elev[5, 5] = -32768.0  # Invalid
    cfg = TerrainConfig(nodata_sentinel=-32768.0)
    grid = derive_terrain_from_array(elev, config=cfg)

    # Out of bounds
    res1 = astar_search((-1, 5), (10, 10), grid)
    assert not res1.is_reachable and res1.path == []

    res2 = astar_search((5, 5), (20, 20), grid)
    assert not res2.is_reachable and res2.path == []

    # Inside invalid mask
    res3 = astar_search((5, 5), (10, 10), grid)
    assert not res3.is_reachable and res3.path == []


# ==============================================================================
# TC-08: Science-First Objective & Cost Tie-Breaking
# ==============================================================================
def test_tc_08_science_first_objective():
    """
    TC-08: Verify Science-First traverse prioritizes maximum science score,
    using modeled cost as an explicit tie-breaker between equal-science candidates.
    """
    elev = np.zeros((30, 30), dtype=np.float32)
    cfg = TerrainConfig(cell_size_m=20.0, dx_ground_m=20.0, dy_ground_m=20.0, alpha_s=0.0, alpha_r=0.0, alpha_up=0.0)
    grid = derive_terrain_from_array(elev, config=cfg)

    start = (5, 5)
    goal = (25, 25)

    # Waypoint 1: priority 50, near start
    w1 = ScienceWaypoint(id="w1", name="Target 1", rc=(6, 6), priority_score=50.0)
    # Waypoint 2: priority 90, slightly off-path
    w2 = ScienceWaypoint(id="w2", name="Target 2", rc=(10, 20), priority_score=90.0)
    # Waypoint 3: priority 90, far detour
    w3 = ScienceWaypoint(id="w3", name="Target 3", rc=(2, 28), priority_score=90.0)

    # Test A: w1 vs w2 (w2 has higher science)
    res_a = plan_route(start, goal, grid, waypoints=[w1, w2], config=PlannerConfig(profile="science_first"))
    assert res_a.is_reachable
    # When all waypoints can be visited, science_first visits both
    assert "w1" in res_a.visited_waypoint_ids and "w2" in res_a.visited_waypoint_ids
    assert res_a.science_score == 140.0

    # Test B: Tie-breaker between two equal-priority targets when forced to choose one
    # Provide a distance budget that allows visiting only w2 (682.8m), but not w3 (969.7m)
    budget = 750.0  # Direct is ~565m. w2 fits under 750m, w3 exceeds
    res_b = plan_route(
        start, goal, grid, waypoints=[w2, w3],
        config=PlannerConfig(profile="science_first", max_distance_m=budget)
    )
    assert res_b.is_reachable
    # Both have 90 points, but w2 fits within the budget
    assert "w2" in res_b.visited_waypoint_ids
    assert "w3" not in res_b.visited_waypoint_ids


# ==============================================================================
# TC-09: Balanced Objective Parameter Sensitivity
# ==============================================================================
def test_tc_09_balanced_objective_tradeoff():
    """
    TC-09: Verify Balanced profile trade-off. Increasing gamma shifts preference
    away from expensive detours toward the conservative baseline.
    """
    elev = np.zeros((35, 35), dtype=np.float32)
    cfg = TerrainConfig(cell_size_m=20.0, dx_ground_m=20.0, dy_ground_m=20.0, alpha_s=0.0, alpha_r=0.0, alpha_up=0.0)
    grid = derive_terrain_from_array(elev, config=cfg)

    start = (5, 5)
    goal = (25, 25)

    # w1: moderate science near baseline path (small detour)
    w1 = ScienceWaypoint(id="w1", name="Near Target", rc=(10, 10), priority_score=20.0)
    # w2: extra science at a far corner (large detour)
    w2 = ScienceWaypoint(id="w2", name="Far Detour", rc=(5, 25), priority_score=25.0)

    # Low gamma (e.g. 0.2): high science appetite, gladly accepts both detours
    res_greedy = plan_route(
        start, goal, grid, waypoints=[w1, w2],
        config=PlannerConfig(profile="balanced", science_appetite_gamma=0.2)
    )
    assert res_greedy.is_reachable
    assert "w1" in res_greedy.visited_waypoint_ids and "w2" in res_greedy.visited_waypoint_ids

    # High gamma (e.g. 2.5): high terrain-cost sensitivity, drops the expensive detour w2
    res_cautious = plan_route(
        start, goal, grid, waypoints=[w1, w2],
        config=PlannerConfig(profile="balanced", science_appetite_gamma=2.5)
    )
    assert res_cautious.is_reachable
    # High gamma should retain w1 but drop w2
    assert "w1" in res_cautious.visited_waypoint_ids
    assert "w2" not in res_cautious.visited_waypoint_ids


# ==============================================================================
# TC-10: Pairwise Cache Correctness & Directed Integrity
# ==============================================================================
def test_tc_10_pairwise_cache_correctness():
    """
    TC-10: Check that precomputed leg cache matches direct point-to-point A* results,
    including directed asymmetry.
    """
    elev = np.zeros((20, 20), dtype=np.float32)
    elev[:, 10:] = 10.0  # Slope jump
    cfg = TerrainConfig(alpha_up=2.0)
    grid = derive_terrain_from_array(elev, config=cfg)

    nodes = [(2, 2), (5, 15), (18, 18)]
    cache = compute_pairwise_leg_cache(nodes, grid)

    # Check that cache contains all 3x3 pairs
    assert len(cache) == 9

    # Check (2,2) -> (5,15) matches fresh A*
    direct = astar_search((2, 2), (5, 15), grid)
    cached = cache[((2, 2), (5, 15))]
    assert pytest.approx(cached.cost) == direct.cost
    assert pytest.approx(cached.distance_m) == direct.distance_m
    assert cached.path == direct.path

    # Check reverse is directed and cost differs
    cached_rev = cache[((5, 15), (2, 2))]
    assert cached.cost != cached_rev.cost


# ==============================================================================
# TC-11: Continuous Route Reconstruction Without Duplicate Vertices
# ==============================================================================
def test_tc_11_route_reconstruction():
    """
    TC-11: Verify stitched route segments are 8-connected, continuous,
    and adjoining endpoints are not duplicated.
    """
    elev = np.zeros((30, 30), dtype=np.float32)
    grid = derive_terrain_from_array(elev)

    nodes = [(2, 2), (10, 10), (10, 20), (25, 25)]
    cache = compute_pairwise_leg_cache(nodes, grid)

    stitched, dist, cost, ok = stitch_path_legs(nodes, cache)
    assert ok
    assert len(stitched) > 0
    assert stitched[0] == nodes[0]
    assert stitched[-1] == nodes[-1]

    # Check 8-connected continuity and no adjacent duplicate vertices
    for i in range(len(stitched) - 1):
        u = stitched[i]
        v = stitched[i + 1]
        dr = abs(v[0] - u[0])
        dc = abs(v[1] - u[1])
        assert max(dr, dc) == 1, f"Discontinuity between {u} and {v}"
        assert not (dr == 0 and dc == 0), f"Duplicate adjoining vertex at {u}"


# ==============================================================================
# TC-12: Real Jezero CTX Data Smoke Test
# ==============================================================================
def test_tc_12_real_jezero_data_smoke_test():
    """
    TC-12: Run all three profiles across the real Jezero CTX raster from
    Octavia E. Butler Landing (117, 157) to Delta Rim (66, 128) via Three Forks (153, 123).
    Verify finite, consistent metrics.
    """
    assert os.path.exists(PROCESSED_TIFF), f"Processed raster missing: {PROCESSED_TIFF}"
    grid = load_and_process_terrain(PROCESSED_TIFF)

    start = (117, 157)  # Octavia E. Butler Landing
    goal = (66, 128)    # Delta Rim Overlook
    tf = ScienceWaypoint(id="three_forks", name="Three Forks Depot", rc=(153, 123), priority_score=75.0)

    # 1. Conservative
    res_cons = plan_route(start, goal, grid, waypoints=[tf], config=PlannerConfig(profile="conservative"))
    assert res_cons.is_reachable
    assert res_cons.science_score == 0.0
    assert len(res_cons.path) > 50
    assert res_cons.cost >= res_cons.distance_m

    # 2. Science-First
    res_sci = plan_route(start, goal, grid, waypoints=[tf], config=PlannerConfig(profile="science_first"))
    assert res_sci.is_reachable
    assert res_sci.science_score == 75.0
    assert "three_forks" in res_sci.visited_waypoint_ids
    # Visiting Three Forks adds detour distance
    assert res_sci.distance_m > res_cons.distance_m
    assert res_sci.cost > res_cons.cost

    # 3. Balanced
    res_bal = plan_route(start, goal, grid, waypoints=[tf], config=PlannerConfig(profile="balanced", science_appetite_gamma=1.0))
    assert res_bal.is_reachable
    assert res_bal.cost >= res_cons.cost


# ==============================================================================
# TC-13: Scenario-Mask Compatibility
# ==============================================================================
def test_tc_13_scenario_mask_compatibility():
    """
    TC-13: Verify that an external scenario mask blocks routes without altering
    the underlying terrain raster.
    """
    elev = np.zeros((20, 20), dtype=np.float32)
    grid = derive_terrain_from_array(elev)

    start = (10, 2)
    goal = (10, 15)

    # Baseline: straight line along row 10
    leg_baseline = astar_search(start, goal, grid)
    assert leg_baseline.is_reachable
    assert (10, 8) in leg_baseline.path

    # Apply blocked mask on row 10, cols 7 to 9
    blocked_mask = np.zeros((20, 20), dtype=bool)
    blocked_mask[10, 7:10] = True

    leg_diverted = astar_search(start, goal, grid, blocked_mask=blocked_mask)
    assert leg_diverted.is_reachable
    # Diverted route avoids the blocked mask
    for pt in leg_diverted.path:
        assert not blocked_mask[pt[0], pt[1]]
    # Diverted path must be slightly longer than baseline straight path
    assert leg_diverted.distance_m > leg_baseline.distance_m

    # Complete wall blocking all passage
    wall_mask = np.zeros((20, 20), dtype=bool)
    wall_mask[:, 8] = True
    leg_blocked = astar_search(start, goal, grid, blocked_mask=wall_mask)
    assert not leg_blocked.is_reachable
    assert leg_blocked.path == []


# ==============================================================================
# TC-14: Physical Distance Budget Enforcement
# ==============================================================================
def test_tc_14_physical_distance_budget():
    """
    TC-14: Verify that a route meeting terrain constraints but exceeding
    max_distance_m is correctly flagged as is_budget_feasible = False.
    """
    elev = np.zeros((30, 30), dtype=np.float32)
    grid = derive_terrain_from_array(elev)

    start = (5, 5)
    goal = (25, 25)
    # Direct distance is 20 * 20 * sqrt(2) ≈ 565.68 m

    # Conservative route with tight budget of 400 m
    res = plan_route(start, goal, grid, config=PlannerConfig(profile="conservative", max_distance_m=400.0))
    assert res.is_reachable
    assert not res.is_budget_feasible
    assert "exceeds distance budget" in res.status_message.lower()

    # Conservative route with ample budget of 800 m
    res_ok = plan_route(start, goal, grid, config=PlannerConfig(profile="conservative", max_distance_m=800.0))
    assert res_ok.is_reachable
    assert res_ok.is_budget_feasible
