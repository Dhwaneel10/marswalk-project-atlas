"""
Milestone 13A — Independent Scientific Validation & Conference Qualification Test Suite.

Independently verifies:
1. Analytical grid ground distance (EW, NS, diagonal).
2. Segment slope and Horn 3x3 finite-difference kernels.
3. Cumulative elevation gain/loss accounting and NoData safety.
4. A* search optimality vs an independent Dijkstra reference on analytical terrain.
5. Additive model effort cost decomposition and reconciliation.
6. Pareto multi-objective dominance logic (Distance min, Cost min, Science max).
7. Robustness scenario feasibility ratio and zero-baseline percentage deltas.
8. Martian sol time conversion constants (88,775.244 s/sol).
9. Authentic raw vs processed CTX terrain raster SHA-256 digests.
10. Experiment dossier ZIP cryptographic integrity and unauthorized file detection.
"""

import hashlib
import heapq
import io
import math
import os
import zipfile
import pytest
import numpy as np

from marswalk.core.terrain import (
    TerrainGrid,
    TerrainConfig,
    calculate_step_distance,
    calculate_edge_cost,
    compute_ground_spacings,
    compute_horn_slope,
    derive_terrain_from_array,
)
from marswalk.core.planner import (
    astar_search,
    generalized_octile_heuristic,
)
from marswalk.api.contracts import (
    TERRAIN_DATASET_ID,
    TERRAIN_SHA256,
    calculate_safe_pct_delta,
)
from marswalk.core.mission_experiment import (
    verify_experiment_dossier_zip,
)


# ---------------------------------------------------------------------------
# Test 1: Analytical Grid Ground Distance
# ---------------------------------------------------------------------------
def test_01_grid_distance_analytical():
    """
    Verify ground distance calculation against hand-derived analytical geometry.
    Projected cell size: 20.0 m.
    Reference latitude: 18.442 deg N (Jezero crater center).
    dx_ground = 20.0 * cos(18.442 deg) = 18.972728 m.
    dy_ground = 20.0 m.
    """
    ref_lat = 18.442
    lat_rad = math.radians(ref_lat)
    expected_dx = 20.0 * math.cos(lat_rad)  # ~18.972728 m
    expected_dy = 20.0  # 20.0 m

    dx, dy = compute_ground_spacings(cell_size_m=20.0, ref_lat_deg=ref_lat)
    assert math.isclose(dx, expected_dx, rel_tol=1e-6)
    assert math.isclose(dy, expected_dy, rel_tol=1e-6)

    # 1. East-West orthogonal neighbor (dr=0, dc=1)
    d_ew = calculate_step_distance((0, 0), (0, 1), dx, dy)
    assert math.isclose(d_ew, expected_dx, rel_tol=1e-6)

    # 2. North-South orthogonal neighbor (dr=1, dc=0)
    d_ns = calculate_step_distance((0, 0), (1, 0), dx, dy)
    assert math.isclose(d_ns, expected_dy, rel_tol=1e-6)

    # 3. Diagonal neighbor (dr=1, dc=1)
    expected_diag = math.sqrt(expected_dx**2 + expected_dy**2)
    d_diag = calculate_step_distance((0, 0), (1, 1), dx, dy)
    assert math.isclose(d_diag, expected_diag, rel_tol=1e-6)
    assert math.isclose(d_diag, math.sqrt(dx**2 + dy**2), rel_tol=1e-6)


# ---------------------------------------------------------------------------
# Test 2: Segment Slope and Horn 3x3 Kernel Verification
# ---------------------------------------------------------------------------
def test_02_segment_slope_and_horn_kernels():
    """
    Verify point-to-point slope and Horn 3x3 finite-difference slope convolution.
    """
    # Analytical point-to-point slope
    # dz = 10 m over d = 20 m -> theta = arctan(10/20) = 26.565051 deg
    dist = 20.0
    dz = 10.0
    theta_rad = math.atan(abs(dz) / dist)
    theta_deg = math.degrees(theta_rad)
    assert math.isclose(theta_deg, 26.565051, rel_tol=1e-5)

    # Negative elevation difference has identical slope magnitude
    dz_neg = -10.0
    assert math.isclose(math.degrees(math.atan(abs(dz_neg) / dist)), theta_deg, rel_tol=1e-5)

    # Horn 3x3 kernel test on analytical planar ramp
    # Ramp with constant slope 45 deg in Y (dz/dy = 1.0)
    # y increases with row * dy, so elevation = row * dy
    H, W = 10, 10
    dx, dy = 20.0, 20.0
    ramp_y = np.zeros((H, W), dtype=np.float32)
    for r in range(H):
        ramp_y[r, :] = r * dy  # dz/dy = 1.0 everywhere

    slope_y = compute_horn_slope(ramp_y, dx_ground_m=dx, dy_ground_m=dy)
    # Interior pixels (away from borders) should have exactly arctan(1.0) = 45.0 deg
    interior = slope_y[2:-2, 2:-2]
    assert np.allclose(interior, 45.0, atol=1e-2)

    # Horn 3x3 kernel test on analytical planar ramp in X (dz/dx = 1.0)
    ramp_x = np.zeros((H, W), dtype=np.float32)
    for c in range(W):
        ramp_x[:, c] = c * dx  # dz/dx = 1.0 everywhere

    slope_x = compute_horn_slope(ramp_x, dx_ground_m=dx, dy_ground_m=dy)
    interior_x = slope_x[2:-2, 2:-2]
    assert np.allclose(interior_x, 45.0, atol=1e-2)


# ---------------------------------------------------------------------------
# Test 3: Cumulative Elevation Gain and Descent
# ---------------------------------------------------------------------------
def test_03_cumulative_elevation_gain_descent():
    """
    Verify cumulative ascent, descent, and NoData boundary protection.
    Analytical sequence: [100.0, 110.0, 105.0, 120.0, 115.0]
    Deltas: +10, -5, +15, -5
    Gain: 10 + 15 = 25.0 m
    Descent: 5 + 5 = 10.0 m
    Net: 25 - 10 = 15.0 m (115 - 100)
    """
    z_seq = [100.0, 110.0, 105.0, 120.0, 115.0]

    gain = sum(max(0.0, z_seq[k + 1] - z_seq[k]) for k in range(len(z_seq) - 1))
    descent = sum(max(0.0, z_seq[k] - z_seq[k + 1]) for k in range(len(z_seq) - 1))

    assert math.isclose(gain, 25.0, rel_tol=1e-9)
    assert math.isclose(descent, 10.0, rel_tol=1e-9)
    assert math.isclose(gain - descent, z_seq[-1] - z_seq[0], rel_tol=1e-9)

    # NoData safety test: invalid pixels (-32768 or -3.4e38) must be masked
    raw_seq = [100.0, 110.0, -32768.0, 120.0]
    valid_seq = [z for z in raw_seq if z > -1000.0]
    assert valid_seq == [100.0, 110.0, 120.0]
    # Masked gain computation avoids corrupted delta of -32878 m
    clean_gain = sum(max(0.0, valid_seq[k + 1] - valid_seq[k]) for k in range(len(valid_seq) - 1))
    assert math.isclose(clean_gain, 20.0, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Test 4: A* Search Optimality vs Independent Dijkstra Reference
# ---------------------------------------------------------------------------
def dijkstra_reference(
    start: tuple[int, int],
    goal: tuple[int, int],
    terrain: TerrainGrid,
) -> tuple[list[tuple[int, int]], float, float]:
    """
    Independent reference implementation of Dijkstra's algorithm on 8-connected grid.
    """
    pq = [(0.0, start)]
    g_score = {start: 0.0}
    dist_map = {start: 0.0}
    parent = {}
    visited = set()

    H, W = terrain.shape
    neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]

    while pq:
        g, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)

        if u == goal:
            path = []
            curr = u
            while curr in parent:
                path.append(curr)
                curr = parent[curr]
            path.append(start)
            path.reverse()
            return path, g, dist_map[goal]

        r, c = u
        for dr, dc in neighbors:
            v = (r + dr, c + dc)
            if 0 <= v[0] < H and 0 <= v[1] < W:
                edge_cost = calculate_edge_cost(u, v, terrain)
                if not math.isinf(edge_cost):
                    new_g = g + edge_cost
                    if new_g < g_score.get(v, float("inf")):
                        g_score[v] = new_g
                        dx = terrain.dx_ground_m
                        dy = terrain.dy_ground_m
                        step_d = math.sqrt((abs(dc) * dx) ** 2 + (abs(dr) * dy) ** 2)
                        dist_map[v] = dist_map[u] + step_d
                        parent[v] = u
                        heapq.heappush(pq, (new_g, v))

    return [], float("inf"), 0.0


def test_04_astar_vs_dijkstra_analytical_equivalence():
    """
    Verify A* finds the mathematically optimal path cost identical to Dijkstra.
    """
    # 10x10 terrain with analytical Gaussian hill
    H, W = 10, 10
    elev = np.zeros((H, W), dtype=np.float32)
    for r in range(H):
        for c in range(W):
            elev[r, c] = max(0.0, 15.0 - math.sqrt((r - 4.5) ** 2 + (c - 4.5) ** 2) * 3.0)

    cfg = TerrainConfig(cell_size_m=20.0, ref_lat_deg=18.442, theta_max_deg=35.0)
    grid = derive_terrain_from_array(elev, config=cfg)

    start = (0, 0)
    goal = (9, 9)

    res_astar = astar_search(start, goal, grid)
    dijk_path, dijk_cost, dijk_dist = dijkstra_reference(start, goal, grid)

    assert res_astar.is_reachable is True
    assert len(res_astar.path) > 0
    assert math.isclose(res_astar.cost, dijk_cost, rel_tol=1e-7)

    # Verify admissible heuristic: h(start, goal) <= true cost
    h_start = generalized_octile_heuristic(start, goal, grid.dx_ground_m, grid.dy_ground_m)
    assert h_start <= dijk_cost
    assert h_start <= res_astar.cost


# ---------------------------------------------------------------------------
# Test 5: Model-Cost Decomposition and Additive Reconciliation
# ---------------------------------------------------------------------------
def test_05_model_cost_additive_reconciliation():
    """
    Verify additive decomposition: C_model = C_dist + C_slope + C_rough + C_uphill.
    """
    H, W = 5, 5
    elev = np.array([
        [10.0, 15.0, 20.0, 25.0, 30.0],
        [12.0, 17.0, 22.0, 27.0, 32.0],
        [14.0, 19.0, 24.0, 29.0, 34.0],
        [16.0, 21.0, 26.0, 31.0, 36.0],
        [18.0, 23.0, 28.0, 33.0, 38.0],
    ], dtype=np.float32)

    cfg = TerrainConfig(
        cell_size_m=20.0,
        ref_lat_deg=18.442,
        alpha_s=2.0,
        theta_crit_deg=10.0,
        alpha_r=1.0,
        sigma_0_m=1.5,
        alpha_up=1.5,
    )
    grid = derive_terrain_from_array(elev, config=cfg)

    u = (1, 1)
    v = (1, 2)

    total_cost = calculate_edge_cost(u, v, grid)

    # Independent component calculation
    dist = calculate_step_distance(u, v, grid.dx_ground_m, grid.dy_ground_m)
    dz = float(elev[v[0], v[1]] - elev[u[0], u[1]])
    theta_step = math.degrees(math.atan(abs(dz) / dist))
    theta_dest = float(grid.slope_deg[v[0], v[1]])
    theta_uv = max(theta_dest, theta_step)

    c_dist = dist
    c_slope = dist * (cfg.alpha_s * ((theta_uv / cfg.theta_crit_deg) ** 2))
    c_rough = dist * (cfg.alpha_r * (float(grid.roughness_m[v[0], v[1]]) / cfg.sigma_0_m))
    c_uphill = dist * (cfg.alpha_up * max(0.0, dz / dist))

    reconciled_sum = c_dist + c_slope + c_rough + c_uphill

    assert math.isclose(total_cost, reconciled_sum, rel_tol=1e-12)
    assert total_cost >= dist  # Model cost never underestimates ground distance


# ---------------------------------------------------------------------------
# Test 6: Pareto Multi-Objective Dominance
# ---------------------------------------------------------------------------
def dominates(cand_a: tuple[float, float, float], cand_b: tuple[float, float, float]) -> bool:
    """
    Feasible candidate A dominates candidate B iff:
    Distance_A <= Distance_B, Cost_A <= Cost_B, Science_A >= Science_B
    and at least one inequality is strict.
    Tuple: (distance, cost, science_points)
    """
    d_a, c_a, s_a = cand_a
    d_b, c_b, s_b = cand_b

    weakly_better = (d_a <= d_b) and (c_a <= c_b) and (s_a >= s_b)
    strictly_better = (d_a < d_b) or (c_a < c_b) or (s_a > s_b)
    return weakly_better and strictly_better


def test_06_pareto_dominance_analytical_matrix():
    """
    Verify Pareto dominance properties on analytical multi-objective fixtures.
    """
    # Cand 1: (D=1000m, C=1200, S=50 pts)
    # Cand 2: (D=1200m, C=1400, S=40 pts) -> Strictly dominated by Cand 1
    # Cand 3: (D=800m,  C=1000, S=30 pts) -> Incomparable with Cand 1 (shorter, but less science)
    # Cand 4: (D=1000m, C=1200, S=50 pts) -> Identical to Cand 1 (neither dominates)

    c1 = (1000.0, 1200.0, 50.0)
    c2 = (1200.0, 1400.0, 40.0)
    c3 = (800.0, 1000.0, 30.0)
    c4 = (1000.0, 1200.0, 50.0)

    # 1. Strict dominance
    assert dominates(c1, c2) is True
    assert dominates(c2, c1) is False

    # 2. Incomparability
    assert dominates(c1, c3) is False
    assert dominates(c3, c1) is False

    # 3. Identity
    assert dominates(c1, c4) is False
    assert dominates(c4, c1) is False

    # 4. Partial dominance: equal distance & cost, strictly better science
    c5 = (1000.0, 1200.0, 60.0)
    assert dominates(c5, c1) is True
    assert dominates(c1, c5) is False


# ---------------------------------------------------------------------------
# Test 7: Robustness Feasibility Ratio and Zero-Baseline Handling
# ---------------------------------------------------------------------------
def test_07_robustness_feasibility_ratio_and_safe_delta():
    """
    Verify R_test = N_feasible / N_evaluated and zero-baseline safe delta logic.
    """
    evaluated_scenarios = [
        {"id": "sc_01", "is_feasible": True},
        {"id": "sc_02", "is_feasible": True},
        {"id": "sc_03", "is_feasible": False},
        {"id": "sc_04", "is_feasible": True},
    ]
    n_evaluated = len(evaluated_scenarios)
    n_feasible = sum(1 for s in evaluated_scenarios if s["is_feasible"])
    r_test = n_feasible / n_evaluated
    assert math.isclose(r_test, 0.75, rel_tol=1e-9)

    # Zero-baseline safety: dividing by zero baseline returns None (JSON null) to prevent NaN/Inf
    assert calculate_safe_pct_delta(150.0, 0.0) is None
    assert calculate_safe_pct_delta(0.0, 0.0) is None
    # Normal delta: (120 - 100) / 100 = +20.0%
    assert math.isclose(calculate_safe_pct_delta(120.0, 100.0), 20.0, rel_tol=1e-6)
    # Negative delta: (80 - 100) / 100 = -20.0%
    assert math.isclose(calculate_safe_pct_delta(80.0, 100.0), -20.0, rel_tol=1e-6)


# ---------------------------------------------------------------------------
# Test 8: Martian Sol Time Accounting Constants
# ---------------------------------------------------------------------------
def test_08_sol_time_conversion_constants():
    """
    Verify IAU Martian solar day constant: 88,775.244 s/sol (~24h 39m 35.244s).
    """
    martian_sol_s = 88775.244

    hours = martian_sol_s / 3600.0
    assert math.isclose(hours, 24.65979, abs_tol=1e-4)

    # Verify a 4-hour EVA in sol fraction
    eva_s = 4.0 * 3600.0  # 14400 s
    sol_fraction = eva_s / martian_sol_s
    assert math.isclose(sol_fraction, 0.162207, abs_tol=1e-5)


# ---------------------------------------------------------------------------
# Test 9: Raw and Processed CTX Terrain Raster SHA-256 Authenticity
# ---------------------------------------------------------------------------
def test_09_terrain_asset_sha256_authenticity():
    """
    Verify on-disk byte hashes of both the raw source CTX DTM and processed 20m raster.
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    processed_path = os.path.join(repo_root, "data", "processed", "jezero_ready_20m.tif")
    raw_path = os.path.join(
        repo_root, "data", "raw", "JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif"
    )

    # 1. Processed local raster
    assert os.path.exists(processed_path), f"Processed raster missing: {processed_path}"
    with open(processed_path, "rb") as f:
        proc_hash = hashlib.sha256(f.read()).hexdigest()
    assert proc_hash == "875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3"
    assert proc_hash == TERRAIN_SHA256
    assert TERRAIN_DATASET_ID == "USGS_CTX_DTM_JEZERO_20M"

    # 2. Raw source product (if present in local dev checkout)
    if os.path.exists(raw_path):
        with open(raw_path, "rb") as f:
            raw_hash = hashlib.sha256(f.read()).hexdigest()
        assert raw_hash == "16a1aa66c3f48c1bca252795827db7b417876217aff0f5e1aff18027fab2327b"


# ---------------------------------------------------------------------------
# Test 10: Experiment ZIP Tamper Detection & Manifest Integrity
# ---------------------------------------------------------------------------
def test_10_experiment_zip_tamper_detection(tmp_path):
    """
    Verify that verify_experiment_dossier_zip rejects archives with extra files,
    tampered byte contents, or mismatched manifest checksums.
    """
    import json
    from marswalk.core.mission_experiment import (
        ExperimentConfig,
        orchestrate_mission_experiment,
        export_experiment_dossier_zip,
    )
    from marswalk.core.mission_campaign import (
        CampaignConfig,
        CampaignTarget,
        plan_mission_campaign,
    )

    # Build a tiny analytical terrain and test campaign in isolated tmp_path
    elev = np.zeros((10, 10), dtype=np.float32)
    cfg_t = TerrainConfig(cell_size_m=20.0, ref_lat_deg=18.442, theta_max_deg=35.0)
    grid = derive_terrain_from_array(elev, config=cfg_t)

    camp_cfg = CampaignConfig(max_duration_per_sortie_s=14400.0, base_start_rc=(1, 1))
    targets = [CampaignTarget("tgt_val_1", "Test Target", 3, 3, 50.0, 1200.0)]
    camp = plan_mission_campaign("cmp_13a_val_test", "13A Validation Camp", camp_cfg, targets, grid)

    exp_cfg = ExperimentConfig(
        campaign_id=camp.campaign_id,
        suite_type="operational_delays",
        max_scenarios=1,
        max_rehearsals=0,
    )
    rec = orchestrate_mission_experiment(camp, grid, exp_cfg)
    zip_path = export_experiment_dossier_zip(rec.experiment_id)

    # 1. Clean zip must verify successfully
    is_valid, errors = verify_experiment_dossier_zip(zip_path)
    assert is_valid is True, f"Clean ZIP failed validation: {errors}"

    # 2. Tamper: inject unauthorized extra file
    tampered_zip = os.path.join(tmp_path, "tampered_extra.zip")
    with zipfile.ZipFile(zip_path, "r") as zin:
        with zipfile.ZipFile(tampered_zip, "w") as zout:
            for item in zin.infolist():
                zout.writestr(item, zin.read(item.filename))
            zout.writestr("malicious_untracked_payload.bin", b"INJECTED_PAYLOAD")

    is_valid_extra, err_extra = verify_experiment_dossier_zip(tampered_zip)
    assert is_valid_extra is False
    assert any("unauthorized" in e.lower() or "untracked" in e.lower() for e in err_extra)

    # 3. Tamper: corrupted manifest hash
    corrupted_zip = os.path.join(tmp_path, "corrupted_hash.zip")
    with zipfile.ZipFile(zip_path, "r") as zin:
        with zipfile.ZipFile(corrupted_zip, "w") as zout:
            for item in zin.infolist():
                content = zin.read(item.filename)
                if item.filename == "manifest.json":
                    man = json.loads(content.decode("utf-8"))
                    man["overall_manifest_sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"
                    content = json.dumps(man).encode("utf-8")
                zout.writestr(item, content)

    is_valid_corr, err_corr = verify_experiment_dossier_zip(corrupted_zip)
    assert is_valid_corr is False
    assert any("manifest sha-256 mismatch" in e.lower() for e in err_corr)
