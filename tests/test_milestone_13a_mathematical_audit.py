"""
MarsWalk 2.0 / Project Atlas - Milestone 13A
Mathematical and Algorithm Auditor Test Suite

Verifies:
1. Grid Distance Geodetics: Equirectangular ground projection, dx/dy ground spacing,
   orthogonal and diagonal step distances, and metric properties (symmetry, identity, triangle inequality).
2. Segment Slope & Horn Convolution: Analytical ramps, step slope vs Horn 3x3 facet slope,
   cross-slope contour side-hill protection, and 1-pixel dilation boundary masking.
3. Cumulative Elevation & NoData Safety: Elevation gain and descent conservation (G - D == delta_z),
   and zero false 0m elevation injection over missing or invalid terrain.
4. A* Optimality vs Independent Dijkstra: Strict cost identity between A* and Dijkstra reference,
   heuristic consistency (monotonicity) and admissibility (h <= h*), and expansion reduction.
5. Model-Cost Additive Reconciliation: Linear decomposition of traversal effort
   into distance, slope, roughness, and uphill terms with zero double-counting.
6. Pareto Dominance & Infeasibility Partitioning: Multi-objective dominance rules,
   non-dominated frontier classification, duplicate candidate handling, and infeasible isolation.
"""

import heapq
import math
import os
from typing import Any, Dict, List, Optional, Set, Tuple
import pytest
import numpy as np

from marswalk.core.terrain import (
    TerrainConfig,
    TerrainGrid,
    compute_ground_spacings,
    create_invalid_mask,
    dilate_invalid_mask,
    derive_terrain_from_array,
    load_and_process_terrain,
    calculate_step_distance,
    calculate_edge_cost,
)
from marswalk.core.planner import (
    generalized_octile_heuristic,
    astar_search,
    LegResult,
)
from marswalk.core.terrain_intelligence import extract_route_elevation_profile
from marswalk.core.route_explainer import (
    compute_step_attributions,
    decompose_route_segments,
    reconcile_route_cost_ledger,
)
from marswalk.core.campaign_design_space import (
    CandidateEvaluation,
    CandidateObjectives,
    CandidateStatus,
    DominanceStatus,
    check_dominance,
    classify_pareto_frontier,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_TIFF = os.path.join(REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")


# ==============================================================================
# 1. GRID DISTANCE AUDIT
# ==============================================================================
def test_audit_01_grid_distance_formulation():
    cell_size = 20.0
    ref_lat = 18.442

    lat_rad = ref_lat * (math.pi / 180.0)
    cos_lat = math.cos(lat_rad)
    expected_dx = cell_size * cos_lat
    expected_dy = cell_size
    expected_diag = math.sqrt(expected_dx**2 + expected_dy**2)

    calc_dx, calc_dy = compute_ground_spacings(cell_size_m=cell_size, ref_lat_deg=ref_lat)

    assert abs(calc_dx - expected_dx) < 1e-12
    assert abs(calc_dy - expected_dy) < 1e-12

    # 8-connected steps
    u = (10, 10)
    directions = [
        ((0, 1), expected_dx),
        ((0, -1), expected_dx),
        ((-1, 0), expected_dy),
        ((1, 0), expected_dy),
        ((-1, 1), expected_diag),
        ((-1, -1), expected_diag),
        ((1, 1), expected_diag),
        ((1, -1), expected_diag),
    ]

    for (dr, dc), expected_d in directions:
        v = (u[0] + dr, u[1] + dc)
        dist = calculate_step_distance(u, v, calc_dx, calc_dy)
        assert abs(dist - expected_d) < 1e-12
        # Symmetry
        assert calculate_step_distance(u, v, calc_dx, calc_dy) == calculate_step_distance(v, u, calc_dx, calc_dy)

    # Identity
    assert calculate_step_distance(u, u, calc_dx, calc_dy) == 0.0

    # Triangle inequality
    w = (11, 12)
    assert calculate_step_distance(u, w, calc_dx, calc_dy) <= (
        calculate_step_distance(u, (10, 11), calc_dx, calc_dy) +
        calculate_step_distance((10, 11), w, calc_dx, calc_dy) + 1e-12
    )


# ==============================================================================
# 2. SEGMENT SLOPE & HORN CONVOLUTION AUDIT
# ==============================================================================
def test_audit_02_segment_slope_and_horn_convolution():
    cell_size = 20.0
    ref_lat = 18.442
    dx, dy = compute_ground_spacings(cell_size_m=cell_size, ref_lat_deg=ref_lat)

    # 1. Planar ramps across multiple slope angles
    test_angles = [0.0, 5.0, 10.0, 15.0, 20.0, 24.5]
    H, W = 40, 40
    cols, rows = np.meshgrid(np.arange(W), np.arange(H))

    for angle in test_angles:
        tan_theta = math.tan(math.radians(angle))
        elev_ew = (cols * dx * tan_theta).astype(np.float64)
        cfg = TerrainConfig(cell_size_m=cell_size, ref_lat_deg=ref_lat, dx_ground_m=dx, dy_ground_m=dy)
        grid_ew = derive_terrain_from_array(elev_ew, config=cfg)
        interior_ew = grid_ew.slope_deg[3:-3, 3:-3]
        assert np.max(np.abs(interior_ew - angle)) < 1e-3

        elev_ns = ((H - 1 - rows) * dy * tan_theta).astype(np.float64)
        grid_ns = derive_terrain_from_array(elev_ns, config=cfg)
        interior_ns = grid_ns.slope_deg[3:-3, 3:-3]
        assert np.max(np.abs(interior_ns - angle)) < 1e-3

    # 2. Side-hill contour traverse test: theta_step == 0 vs theta_horn == 20
    tan_20 = math.tan(math.radians(20.0))
    elev_side = ((H - 1 - rows) * dy * tan_20).astype(np.float64)
    grid_side = derive_terrain_from_array(elev_side, config=cfg)

    u_c = (20, 15)
    v_c = (20, 16)
    dz_c = float(grid_side.elevation[v_c] - grid_side.elevation[u_c])
    dist_c = calculate_step_distance(u_c, v_c, dx, dy)
    theta_step_c = math.degrees(math.atan(abs(dz_c) / dist_c))
    theta_horn_c = float(grid_side.slope_deg[v_c])

    assert theta_step_c == 0.0
    assert abs(theta_horn_c - 20.0) < 1e-3
    cost_c = calculate_edge_cost(u_c, v_c, grid_side)
    # Effective slope in calculate_edge_cost is max(theta_horn, theta_step) = 20 deg
    # Cost must exceed flat ground distance
    assert cost_c > dist_c

    # 3. NoData dilation and boundary padding
    elev_nodata = np.full((30, 30), -2500.0, dtype=np.float32)
    elev_nodata[12:16, 12:16] = -32768.0
    cfg_nd = TerrainConfig(nodata_sentinel=-32768.0, cell_size_m=cell_size, dx_ground_m=dx, dy_ground_m=dy)
    grid_nd = derive_terrain_from_array(elev_nodata, config=cfg_nd)

    base_mask = create_invalid_mask(elev_nodata, nodata_sentinel=-32768.0)
    dilated_mask = dilate_invalid_mask(base_mask, iterations=1)
    assert np.sum(base_mask) == 16
    assert np.sum(dilated_mask) == 36
    assert np.all(np.isnan(grid_nd.slope_deg[11:17, 11:17]))
    assert np.all(np.isfinite(grid_nd.slope_deg[2:8, 2:8]))
    assert math.isinf(calculate_edge_cost((10, 14), (11, 14), grid_nd))


# ==============================================================================
# 3. CUMULATIVE ELEVATION & NODATA SAFETY AUDIT
# ==============================================================================
def test_audit_03_cumulative_elevation_and_nodata_safety():
    # Invariant test: Gain - Loss == Net Change
    z_profile = np.array([-2500.0, -2480.0, -2450.0, -2470.0, -2460.0, -2490.0, -2440.0, -2440.0, -2465.0])
    deltas = np.diff(z_profile)
    gains = np.maximum(0.0, deltas)
    descents = np.maximum(0.0, -deltas)

    total_gain = float(np.sum(gains))
    total_descent = float(np.sum(descents))
    net_elevation_change = float(z_profile[-1] - z_profile[0])

    assert abs((total_gain - total_descent) - net_elevation_change) < 1e-12

    # Zero false elevation injection over NoData
    elev_grid = np.full((10, 10), -2500.0, dtype=np.float32)
    elev_grid[5, 5] = -32768.0
    cfg = TerrainConfig(nodata_sentinel=-32768.0, cell_size_m=20.0, dx_ground_m=20.0, dy_ground_m=20.0)
    grid = derive_terrain_from_array(elev_grid, config=cfg)

    test_path = [(5, 3), (5, 4), (5, 5), (5, 6), (5, 7)]
    profile = extract_route_elevation_profile(test_path, grid)

    assert profile.samples[2].is_nodata is True
    assert profile.samples[2].elevation_m is None
    assert profile.total_elevation_gain_m == 0.0
    assert profile.total_elevation_loss_m == 0.0


# ==============================================================================
# 4. A* SEARCH VS INDEPENDENT DIJKSTRA REFERENCE AUDIT
# ==============================================================================
def _dijkstra_reference(
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    terrain: TerrainGrid,
    terrain_config: Optional[TerrainConfig] = None,
) -> Tuple[LegResult, int]:
    H, W = terrain.shape
    if terrain.invalid_mask[start_rc] or terrain.invalid_mask[goal_rc]:
        return LegResult(start_rc, goal_rc, [], 0.0, float("inf"), False), 0
    if start_rc == goal_rc:
        return LegResult(start_rc, goal_rc, [start_rc], 0.0, 0.0, True), 0

    dx, dy = terrain.dx_ground_m, terrain.dy_ground_m
    neighbors_delta = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]

    pq = [(0.0, start_rc)]
    g_score = {start_rc: 0.0}
    dist_so_far = {start_rc: 0.0}
    parent = {}
    expansions = 0

    while pq:
        g, u = heapq.heappop(pq)
        expansions += 1
        if u == goal_rc:
            path = []
            curr = u
            while curr in parent:
                path.append(curr)
                curr = parent[curr]
            path.append(start_rc)
            path.reverse()
            return LegResult(start_rc, goal_rc, path, dist_so_far[goal_rc], g_score[goal_rc], True), expansions

        if g > g_score.get(u, float("inf")):
            continue

        ur, uc = u
        for dr, dc in neighbors_delta:
            nr, nc = ur + dr, uc + dc
            if not (0 <= nr < H and 0 <= nc < W) or terrain.invalid_mask[nr, nc]:
                continue
            v = (nr, nc)
            edge_c = calculate_edge_cost(u, v, terrain, config=terrain_config)
            if math.isinf(edge_c):
                continue
            step_d = calculate_step_distance(u, v, dx, dy)
            tentative_g = g + edge_c
            if tentative_g < g_score.get(v, float("inf")):
                g_score[v] = tentative_g
                dist_so_far[v] = dist_so_far[u] + step_d
                parent[v] = u
                heapq.heappush(pq, (tentative_g, v))

    return LegResult(start_rc, goal_rc, [], 0.0, float("inf"), False), expansions


def _count_astar(
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    terrain: TerrainGrid,
    terrain_config: Optional[TerrainConfig] = None,
) -> Tuple[LegResult, int]:
    H, W = terrain.shape
    if terrain.invalid_mask[start_rc] or terrain.invalid_mask[goal_rc]:
        return LegResult(start_rc, goal_rc, [], 0.0, float("inf"), False), 0
    if start_rc == goal_rc:
        return LegResult(start_rc, goal_rc, [start_rc], 0.0, 0.0, True), 0

    dx, dy = terrain.dx_ground_m, terrain.dy_ground_m
    neighbors_delta = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]

    h_start = generalized_octile_heuristic(start_rc, goal_rc, dx, dy)
    pq = [(h_start, 0.0, start_rc)]
    g_score = {start_rc: 0.0}
    dist_so_far = {start_rc: 0.0}
    parent = {}
    expansions = 0

    while pq:
        f, g, u = heapq.heappop(pq)
        expansions += 1
        if u == goal_rc:
            path = []
            curr = u
            while curr in parent:
                path.append(curr)
                curr = parent[curr]
            path.append(start_rc)
            path.reverse()
            return LegResult(start_rc, goal_rc, path, dist_so_far[goal_rc], g_score[goal_rc], True), expansions

        if g > g_score.get(u, float("inf")):
            continue

        ur, uc = u
        for dr, dc in neighbors_delta:
            nr, nc = ur + dr, uc + dc
            if not (0 <= nr < H and 0 <= nc < W) or terrain.invalid_mask[nr, nc]:
                continue
            v = (nr, nc)
            edge_c = calculate_edge_cost(u, v, terrain, config=terrain_config)
            if math.isinf(edge_c):
                continue
            step_d = calculate_step_distance(u, v, dx, dy)
            tentative_g = g + edge_c
            if tentative_g < g_score.get(v, float("inf")):
                g_score[v] = tentative_g
                dist_so_far[v] = dist_so_far[u] + step_d
                parent[v] = u
                h_v = generalized_octile_heuristic(v, goal_rc, dx, dy)
                heapq.heappush(pq, (tentative_g + h_v, tentative_g, v))

    return LegResult(start_rc, goal_rc, [], 0.0, float("inf"), False), expansions


def test_audit_04_astar_vs_independent_dijkstra_reference():
    cell_size = 20.0
    ref_lat = 18.442
    dx, dy = compute_ground_spacings(cell_size_m=cell_size, ref_lat_deg=ref_lat)

    # 1. Flat grid
    elev_flat = np.full((30, 30), -2500.0, dtype=np.float32)
    cfg1 = TerrainConfig(cell_size_m=cell_size, ref_lat_deg=ref_lat, dx_ground_m=dx, dy_ground_m=dy)
    grid_flat = derive_terrain_from_array(elev_flat, config=cfg1)

    res_d, exp_d = _dijkstra_reference((5, 5), (25, 25), grid_flat)
    res_a, exp_a = _count_astar((5, 5), (25, 25), grid_flat)
    assert abs(res_d.cost - res_a.cost) < 1e-6
    assert exp_a <= exp_d

    # 2. Asymmetric ramp
    cols, rows = np.meshgrid(np.arange(30), np.arange(30))
    elev_ramp = (-2500.0 + rows * 2.0 + cols * 1.5).astype(np.float32)
    cfg2 = TerrainConfig(cell_size_m=cell_size, ref_lat_deg=ref_lat, dx_ground_m=dx, dy_ground_m=dy, alpha_up=2.0)
    grid_ramp = derive_terrain_from_array(elev_ramp, config=cfg2)

    res_d2, exp_d2 = _dijkstra_reference((5, 5), (25, 25), grid_ramp)
    res_a2, exp_a2 = _count_astar((5, 5), (25, 25), grid_ramp)
    assert abs(res_d2.cost - res_a2.cost) < 1e-6
    assert exp_a2 <= exp_d2

    # 3. Real Jezero CTX crop if available
    if os.path.exists(PROCESSED_TIFF):
        real_grid = load_and_process_terrain(PROCESSED_TIFF)
        res_dr, exp_dr = _dijkstra_reference((117, 157), (125, 165), real_grid)
        res_ar, exp_ar = _count_astar((117, 157), (125, 165), real_grid)
        assert abs(res_dr.cost - res_ar.cost) < 1e-6
        assert exp_ar <= exp_dr

    # 4. Consistency check
    goal_test = (25, 25)
    for r in range(12, 22):
        for c in range(12, 22):
            u = (r, c)
            h_u = generalized_octile_heuristic(u, goal_test, dx, dy)
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    v = (r + dr, c + dc)
                    edge_cost = calculate_edge_cost(u, v, grid_ramp)
                    if math.isinf(edge_cost):
                        continue
                    h_v = generalized_octile_heuristic(v, goal_test, dx, dy)
                    assert h_u <= edge_cost + h_v + 1e-10


# ==============================================================================
# 5. MODEL-COST RECONCILIATION AUDIT
# ==============================================================================
def test_audit_05_model_cost_additive_reconciliation():
    cell_size = 20.0
    ref_lat = 18.442
    dx, dy = compute_ground_spacings(cell_size_m=cell_size, ref_lat_deg=ref_lat)

    H, W = 35, 35
    cols, rows = np.meshgrid(np.arange(W), np.arange(H))
    elev = (-2500.0 + np.sin(cols / 3.0) * 8.0 + rows * 1.2).astype(np.float32)

    cfg = TerrainConfig(
        cell_size_m=cell_size,
        ref_lat_deg=ref_lat,
        dx_ground_m=dx,
        dy_ground_m=dy,
        alpha_s=2.0,
        theta_crit_deg=10.0,
        theta_max_deg=22.0,
        alpha_r=1.0,
        sigma_0_m=1.5,
        alpha_up=1.5,
    )
    grid = derive_terrain_from_array(elev, config=cfg)

    leg = astar_search((5, 5), (28, 28), grid)
    assert leg.is_reachable
    path = leg.path

    attributions = compute_step_attributions(path, grid, cfg)
    assert len(attributions) == len(path) - 1

    # Step level decomposition exactness
    for attr in attributions:
        comp_sum = (
            attr.base_distance_cost_m +
            attr.slope_cost_m +
            attr.roughness_cost_m +
            attr.uphill_cost_m +
            attr.contingency_cost_m
        )
        assert abs(comp_sum - attr.cost_m) < 1e-12

    # Ledger level reconciliation
    segments = decompose_route_segments(path, attributions, grid, num_aggregated_segments=6)
    ledger = reconcile_route_cost_ledger(
        total_distance_m=leg.distance_m,
        total_cost_m=leg.cost,
        segments=segments,
        max_slope_deg=max(a.slope_deg for a in attributions),
        mean_slope_deg=float(np.mean([a.slope_deg for a in attributions])),
        min_elevation_m=float(min(elev[r, c] for r, c in path)),
        max_elevation_m=float(max(elev[r, c] for r, c in path)),
        tolerance_m=0.05,
    )

    assert ledger.is_reconciled is True
    assert ledger.cost_delta_m < 1e-8
    assert ledger.distance_delta_m < 1e-8
    assert ledger.component_delta_m < 1e-8


# ==============================================================================
# 6. PARETO DOMINANCE AUDIT
# ==============================================================================
def test_audit_06_pareto_dominance_and_infeasibility_partitioning():
    # 1. Classic 3-objective Pareto test: Distance(min), Cost(min), Science(max)
    def check_3obj(a, b):
        if not a["feasible"]:
            return False
        if not b["feasible"]:
            return True
        as_good = (a["d"] <= b["d"]) and (a["c"] <= b["c"]) and (a["s"] >= b["s"])
        strictly_better = (a["d"] < b["d"]) or (a["c"] < b["c"]) or (a["s"] > b["s"])
        return as_good and strictly_better

    cand_a = {"d": 1000.0, "c": 1100.0, "s": 80.0, "feasible": True}
    cand_b = {"d": 1200.0, "c": 1300.0, "s": 70.0, "feasible": True}  # Dominated
    cand_c = {"d": 1100.0, "c": 1050.0, "s": 90.0, "feasible": True}  # Trade-off
    cand_d = {"d": 1000.0, "c": 1100.0, "s": 80.0, "feasible": True}  # Duplicate of a
    cand_e = {"d": 800.0, "c": 900.0, "s": 95.0, "feasible": False}   # Infeasible

    assert check_3obj(cand_a, cand_b) is True
    assert check_3obj(cand_b, cand_a) is False
    assert check_3obj(cand_a, cand_c) is False
    assert check_3obj(cand_c, cand_a) is False
    assert check_3obj(cand_a, cand_d) is False
    assert check_3obj(cand_d, cand_a) is False
    assert check_3obj(cand_a, cand_e) is True
    assert check_3obj(cand_e, cand_a) is False

    # 2. Campaign Design Space Explorer CandidateEvaluation audit
    eval1 = CandidateEvaluation(
        candidate_id="c1",
        fingerprint="fp1",
        configuration={"profile": "science_first"},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(90.0, 18000.0, 4500.0, 10.0, 0, 2),
        dominance_status="",
    )
    eval2 = CandidateEvaluation(
        candidate_id="c2",
        fingerprint="fp2",
        configuration={"profile": "conservative"},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(80.0, 22000.0, 5500.0, 25.0, 1, 2),
        dominance_status="",
    )
    eval3 = CandidateEvaluation(
        candidate_id="c3",
        fingerprint="fp3",
        configuration={"profile": "balanced"},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(95.0, 24000.0, 5000.0, 5.0, 0, 2),
        dominance_status="",
    )
    eval_dup = CandidateEvaluation(
        candidate_id="c_dup",
        fingerprint="fp_dup",
        configuration={"profile": "science_first_clone"},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(90.0, 18000.0, 4500.0, 10.0, 0, 2),
        dominance_status="",
    )
    eval_inf = CandidateEvaluation(
        candidate_id="c_inf",
        fingerprint="fp_inf",
        configuration={"profile": "extreme"},
        status=CandidateStatus.INFEASIBLE.value,
        objectives=CandidateObjectives(100.0, 10000.0, 3000.0, 0.0, 0, 1),
        dominance_status="",
        infeasibility_reasons=["Exceeds EVA consumable margin"],
    )

    assert check_dominance(eval1, eval2) is True
    assert check_dominance(eval2, eval1) is False
    assert check_dominance(eval1, eval3) is False
    assert check_dominance(eval3, eval1) is False
    assert check_dominance(eval1, eval_dup) is False
    assert check_dominance(eval_dup, eval1) is False
    assert check_dominance(eval1, eval_inf) is True
    assert check_dominance(eval_inf, eval1) is False

    pareto, dominated, infeasible = classify_pareto_frontier([eval1, eval2, eval3, eval_dup, eval_inf])
    assert set(c.candidate_id for c in pareto) == {"c1", "c3", "c_dup"}
    assert set(c.candidate_id for c in dominated) == {"c2"}
    assert set(eval2.dominated_by) == {"c1", "c_dup"}
    assert set(c.candidate_id for c in infeasible) == {"c_inf"}
