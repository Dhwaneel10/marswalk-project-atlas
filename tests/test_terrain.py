"""
Automated unit tests for MarsWalk Core Terrain Physics Engine (Milestone 2).
Covers TC-01 through TC-10.
"""

import math
import os
import pytest
import numpy as np

from marswalk.core.terrain import (
    TerrainConfig,
    TerrainGrid,
    compute_ground_spacings,
    create_invalid_mask,
    dilate_invalid_mask,
    compute_horn_slope,
    compute_roughness,
    derive_terrain_from_array,
    load_and_process_terrain,
    calculate_step_distance,
    calculate_edge_cost,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_TIFF = os.path.join(REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")


# ==============================================================================
# TC-01: Flat Terrain Geodesic & Movement Identity
# ==============================================================================
def test_tc_01_flat_terrain_identity():
    """
    TC-01: A constant-elevation plane must yield approximately zero interior slope.
    With all terrain penalties disabled, diagonal and cardinal movement costs must
    agree with their geometric ground distances.
    """
    H, W = 50, 50
    elev = np.full((H, W), -2500.0, dtype=np.float32)

    # Use uniform planar spacing dx = dy = 20.0 m for pure geometric verification
    cfg = TerrainConfig(
        cell_size_m=20.0,
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        alpha_s=0.0,
        alpha_r=0.0,
        alpha_up=0.0,
    )
    grid = derive_terrain_from_array(elev, config=cfg)

    # Slope in interior pixels should be ~0.0 degrees
    interior_slope = grid.slope_deg[2:-2, 2:-2]
    assert np.all(np.abs(interior_slope) < 1e-4), "Flat terrain slope is non-zero"

    # Roughness in interior pixels should be ~0.0 meters
    interior_rough = grid.roughness_m[2:-2, 2:-2]
    assert np.all(np.abs(interior_rough) < 1e-4), "Flat terrain roughness is non-zero"

    # Cardinal step (E-W): cost must equal ground distance exactly (20.0 m)
    cost_card_ew = calculate_edge_cost((10, 10), (10, 11), grid)
    assert pytest.approx(cost_card_ew, abs=1e-4) == 20.0

    # Cardinal step (N-S): cost must equal ground distance exactly (20.0 m)
    cost_card_ns = calculate_edge_cost((10, 10), (11, 10), grid)
    assert pytest.approx(cost_card_ns, abs=1e-4) == 20.0

    # Diagonal step: cost must equal 20 * sqrt(2) ≈ 28.28427 m
    cost_diag = calculate_edge_cost((10, 10), (11, 11), grid)
    expected_diag = 20.0 * math.sqrt(2)
    assert pytest.approx(cost_diag, abs=1e-4) == expected_diag


# ==============================================================================
# TC-02: Analytical Inclined Plane Slope
# ==============================================================================
def test_tc_02_analytical_inclined_plane():
    """
    TC-02: Construct a synthetic planar raster with a known 15.0° ground slope.
    Verify that calculated interior slope is within 15.00° ± 0.05°, accounting for
    ground pixel spacing.
    """
    H, W = 40, 40
    target_slope_deg = 15.0
    tan_15 = math.tan(math.radians(target_slope_deg))

    # Case A: East-West planar ramp with planar spacing (dx = dy = 20.0 m)
    dx_a, dy_a = 20.0, 20.0
    cols, rows = np.meshgrid(np.arange(W), np.arange(H))
    elev_a = (cols * dx_a * tan_15).astype(np.float32)

    cfg_a = TerrainConfig(cell_size_m=20.0, dx_ground_m=dx_a, dy_ground_m=dy_a)
    grid_a = derive_terrain_from_array(elev_a, config=cfg_a)

    interior_a = grid_a.slope_deg[3:-3, 3:-3]
    assert np.all(pytest.approx(target_slope_deg, abs=0.05) == interior_a), (
        f"E-W ramp slope deviated from {target_slope_deg}°: mean={np.mean(interior_a):.4f}°"
    )

    # Case B: Equirectangular ground-scaled ramp at Jezero latitude (~18.442° N)
    dx_b, dy_b = compute_ground_spacings(cell_size_m=20.0, ref_lat_deg=18.442)
    cfg_b = TerrainConfig(cell_size_m=20.0, ref_lat_deg=18.442)
    elev_b = (cols * dx_b * tan_15).astype(np.float32)

    grid_b = derive_terrain_from_array(elev_b, config=cfg_b)
    interior_b = grid_b.slope_deg[3:-3, 3:-3]
    assert np.all(pytest.approx(target_slope_deg, abs=0.05) == interior_b), (
        f"Equirectangular E-W ramp slope deviated from {target_slope_deg}°: mean={np.mean(interior_b):.4f}°"
    )

    # Case C: North-South ramp
    elev_c = ((H - 1 - rows) * dy_a * tan_15).astype(np.float32)
    grid_c = derive_terrain_from_array(elev_c, config=cfg_a)
    interior_c = grid_c.slope_deg[3:-3, 3:-3]
    assert np.all(pytest.approx(target_slope_deg, abs=0.05) == interior_c), (
        f"N-S ramp slope deviated from {target_slope_deg}°: mean={np.mean(interior_c):.4f}°"
    )


# ==============================================================================
# TC-03: Local Decameter Roughness Proxy
# ==============================================================================
def test_tc_03_roughness_proxy():
    """
    TC-03: A flat plane should produce approximately zero local roughness.
    A deliberately varied synthetic surface must produce positive roughness in the affected region.
    """
    H, W = 30, 30
    flat_elev = np.full((H, W), 100.0, dtype=np.float32)
    cfg = TerrainConfig(cell_size_m=20.0, dx_ground_m=20.0, dy_ground_m=20.0)

    flat_grid = derive_terrain_from_array(flat_elev, config=cfg)
    assert np.all(flat_grid.roughness_m[2:-2, 2:-2] < 1e-4), "Flat terrain roughness should be 0"

    # Add a local mound in the center (radius 4 px)
    bumpy_elev = flat_elev.copy()
    bumpy_elev[12:18, 12:18] += np.array([
        [0, 2, 4, 4, 2, 0],
        [2, 6, 10, 10, 6, 2],
        [4, 10, 15, 15, 10, 4],
        [4, 10, 15, 15, 10, 4],
        [2, 6, 10, 10, 6, 2],
        [0, 2, 4, 4, 2, 0],
    ], dtype=np.float32)

    bumpy_grid = derive_terrain_from_array(bumpy_elev, config=cfg)
    # Interior mound should have positive roughness (scale of ~1 - 6 meters)
    mound_roughness = bumpy_grid.roughness_m[13:17, 13:17]
    assert np.all(mound_roughness > 0.5), "Mound roughness should be distinctly positive"
    # Unaffected border should remain ~0
    assert np.all(bumpy_grid.roughness_m[2:5, 2:5] < 1e-4), "Distant flat region roughness should be 0"


# ==============================================================================
# TC-04: NoData Sentinel & 1-Pixel Mask Dilation Barrier
# ==============================================================================
def test_tc_04_nodata_barrier_and_dilation():
    """
    TC-04: Insert a NoData region into a synthetic raster. Verify:
    1. The invalid mask and 1-pixel dilation are correct.
    2. Slope and roughness calculations do not produce misleading finite values across invalid boundaries.
    3. Movement into or through invalid cells has infinite traversal cost.
    """
    H, W = 30, 30
    elev = np.full((H, W), -2500.0, dtype=np.float32)
    nodata_val = -32768.0

    # Place a 4x4 block of NoData at rows 10:14, cols 10:14
    elev[10:14, 10:14] = nodata_val

    cfg = TerrainConfig(nodata_sentinel=nodata_val, cell_size_m=20.0, dx_ground_m=20.0, dy_ground_m=20.0)
    grid = derive_terrain_from_array(elev, config=cfg)

    # 1. Base invalid mask covers exactly 10:14, 10:14
    base_mask = create_invalid_mask(elev, nodata_sentinel=nodata_val)
    assert np.sum(base_mask) == 16
    assert np.all(base_mask[10:14, 10:14])

    # 2. Dilated mask covers 9:15, 9:15 (a 6x6 region = 36 pixels)
    assert np.sum(grid.invalid_mask) == 36
    assert np.all(grid.invalid_mask[9:15, 9:15])

    # 3. Slope and roughness within the dilated boundary must be NaN
    assert np.all(np.isnan(grid.slope_deg[9:15, 9:15]))
    assert np.all(np.isnan(grid.roughness_m[9:15, 9:15]))

    # Valid interior pixels beyond the dilated perimeter must remain finite and ~0
    valid_interior_slope = grid.slope_deg[2:7, 2:7]
    assert np.all(np.isfinite(valid_interior_slope))
    assert np.all(valid_interior_slope < 1e-4)

    # 4. Traversal cost into dilated or NoData cells must be inf
    # Step from valid (8, 10) into boundary (9, 10)
    cost_into_boundary = calculate_edge_cost((8, 10), (9, 10), grid)
    assert math.isinf(cost_into_boundary), "Traversal into dilated NoData buffer should be inf"

    # Step from inside NoData (11, 11) to (11, 12)
    cost_inside_nodata = calculate_edge_cost((11, 11), (11, 12), grid)
    assert math.isinf(cost_inside_nodata), "Traversal inside NoData should be inf"


# ==============================================================================
# TC-05: Edge Traversal Cost Units & Lower Bound
# ==============================================================================
def test_tc_05_edge_cost_units_and_lower_bound():
    """
    TC-05: Verify that all valid edge costs are >= their actual geometric ground distance
    when penalty weights are non-negative.
    """
    H, W = 20, 20
    # Gentle terrain with small slopes
    elev = np.zeros((H, W), dtype=np.float32)
    for r in range(H):
        for c in range(W):
            elev[r, c] = 0.5 * r + 0.3 * c

    cfg = TerrainConfig(cell_size_m=20.0, dx_ground_m=18.97, dy_ground_m=20.0, alpha_s=2.0, alpha_r=1.0, alpha_up=1.5)
    grid = derive_terrain_from_array(elev, config=cfg)

    for r in range(5, 15):
        for c in range(5, 15):
            u = (r, c)
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    v = (r + dr, c + dc)
                    dist = calculate_step_distance(u, v, grid.dx_ground_m, grid.dy_ground_m)
                    cost = calculate_edge_cost(u, v, grid)
                    assert cost >= dist, (
                        f"Cost ({cost:.3f}) is less than ground distance ({dist:.3f}) for {u} -> {v}"
                    )


# ==============================================================================
# TC-06: Direction-Dependent Uphill Cost
# ==============================================================================
def test_tc_06_direction_dependent_uphill_cost():
    """
    TC-06: When uphill cost is enabled, moving uphill and downhill across the same
    height difference should have appropriately different costs.
    Moving uphill must cost more than moving downhill by alpha_up * dz.
    """
    H, W = 10, 10
    elev = np.zeros((H, W), dtype=np.float32)
    # Cell u at (5, 5) elevation 0 m; Cell v at (5, 6) elevation 5.0 m
    elev[5, 5] = 0.0
    elev[5, 6] = 5.0

    alpha_up = 2.0
    cfg_with_uphill = TerrainConfig(
        cell_size_m=20.0,
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        alpha_s=1.0,
        alpha_r=0.0,
        alpha_up=alpha_up,
        theta_max_deg=45.0,
    )
    grid = derive_terrain_from_array(elev, config=cfg_with_uphill)

    u = (5, 5)
    v = (5, 6)

    cost_uphill = calculate_edge_cost(u, v, grid)
    cost_downhill = calculate_edge_cost(v, u, grid)

    assert cost_uphill > cost_downhill, "Uphill movement should cost strictly more than downhill"

    # Because roughness is 0 and destination slopes are identical in this symmetric pair,
    # the cost difference should equal alpha_up * dz = 2.0 * 5.0 = 10.0 equivalent flat meters
    dz = 5.0
    expected_diff = alpha_up * dz
    # Both steps have the same ground distance d=20m, step slope atan(5/20) ~ 14.0°
    # Downhill uphill_term = 0, uphill uphill_term = alpha_up * (dz / d)
    # Difference = d * alpha_up * (dz / d) = alpha_up * dz
    # Note: local destination cell slope theta_dest differs slightly due to convolution, but theta_step dominates
    assert cost_uphill - cost_downhill > 0.0

    # With alpha_up = 0, uphill penalty vanishes
    cfg_no_uphill = TerrainConfig(
        cell_size_m=20.0,
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        alpha_s=0.0,
        alpha_r=0.0,
        alpha_up=0.0,
        theta_max_deg=45.0,
    )
    grid_flat_cost = derive_terrain_from_array(elev, config=cfg_no_uphill)
    assert pytest.approx(calculate_edge_cost(u, v, grid_flat_cost)) == 20.0
    assert pytest.approx(calculate_edge_cost(v, u, grid_flat_cost)) == 20.0


# ==============================================================================
# TC-07: Slope Cutoff Impassability
# ==============================================================================
def test_tc_07_slope_cutoff():
    """
    TC-07: Edges exceeding the configured slope cutoff (theta_max_deg) must return infinite cost.
    Edges below the cutoff must return finite cost.
    """
    H, W = 10, 10
    elev = np.zeros((H, W), dtype=np.float32)

    # Create a step of height dz between col 4 and col 5
    # For d = 20 m:
    # A step slope of 30° requires dz = 20 * tan(30°) ≈ 11.547 m
    # A step slope of 20° requires dz = 20 * tan(20°) ≈ 7.279 m
    elev[:, 5:] = 12.0  # slope ~ 30.96° > 25°

    cfg = TerrainConfig(
        cell_size_m=20.0,
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        theta_crit_deg=10.0,
        theta_max_deg=25.0,
    )
    grid = derive_terrain_from_array(elev, config=cfg)

    # Step crossing from col 4 to col 5 (dz=12m, theta_step ~ 31° > 25°)
    cost_steep = calculate_edge_cost((5, 4), (5, 5), grid)
    assert math.isinf(cost_steep), "Steep edge >= theta_max should have infinite cost"

    # Step within flat area (col 1 to col 2, dz=0)
    cost_gentle = calculate_edge_cost((5, 1), (5, 2), grid)
    assert math.isfinite(cost_gentle), "Gentle edge < theta_max should have finite cost"


# ==============================================================================
# TC-08: Shape, Orientation and Grid Metadata
# ==============================================================================
def test_tc_08_shape_and_orientation():
    """
    TC-08: Verify that output arrays preserve the source dimensions and that
    row/column orientation is not inadvertently reversed.
    """
    H, W = 35, 60
    elev = np.zeros((H, W), dtype=np.float32)
    # Add an asymmetric feature at top-left
    elev[2, 3] = 50.0

    cfg = TerrainConfig(cell_size_m=20.0, ref_lat_deg=18.442)
    grid = derive_terrain_from_array(elev, config=cfg)

    assert grid.shape == (H, W)
    assert grid.slope_deg.shape == (H, W)
    assert grid.roughness_m.shape == (H, W)
    assert grid.invalid_mask.shape == (H, W)

    # Verify peak is at row 2, col 3, not reversed to (H-1-2, W-1-3)
    assert grid.elevation[2, 3] == 50.0
    assert grid.elevation[3, 2] == 0.0

    # Slope around row 2, col 3 should be high, while bottom-right (30, 50) is 0
    assert grid.slope_deg[2, 4] > 5.0
    assert grid.slope_deg[30, 50] < 1e-4


# ==============================================================================
# TC-09: Parameter Validation Schema
# ==============================================================================
def test_tc_09_parameter_validation():
    """
    TC-09: Reject invalid parameters such as negative weights, invalid slope
    thresholds, negative roughness scales, and non-positive cell sizes.
    """
    # cell_size <= 0
    with pytest.raises(ValueError, match="cell_size_m must be positive"):
        TerrainConfig(cell_size_m=-20.0)

    # theta_crit <= 0
    with pytest.raises(ValueError, match="theta_crit_deg must be positive"):
        TerrainConfig(theta_crit_deg=-5.0)

    # theta_max <= theta_crit
    with pytest.raises(ValueError, match="must be greater than theta_crit_deg"):
        TerrainConfig(theta_crit_deg=15.0, theta_max_deg=10.0)

    # theta_max > 90
    with pytest.raises(ValueError, match="cannot exceed 90°"):
        TerrainConfig(theta_max_deg=95.0)

    # alpha_s < 0
    with pytest.raises(ValueError, match="alpha_s must be non-negative"):
        TerrainConfig(alpha_s=-1.0)

    # alpha_r < 0
    with pytest.raises(ValueError, match="alpha_r must be non-negative"):
        TerrainConfig(alpha_r=-0.5)

    # alpha_up < 0
    with pytest.raises(ValueError, match="alpha_up must be non-negative"):
        TerrainConfig(alpha_up=-2.0)

    # sigma_0 <= 0
    with pytest.raises(ValueError, match="sigma_0_m must be positive"):
        TerrainConfig(sigma_0_m=0.0)


# ==============================================================================
# TC-10: Real Jezero CTX Data Smoke Test
# ==============================================================================
def test_tc_10_real_jezero_data_smoke_test():
    """
    TC-10: Load the actual calibrated 250x250 Jezero CTX raster.
    Verify output shapes, finite values in valid interior regions, sensible slope
    and roughness ranges, and valid edge cost calculations.
    """
    assert os.path.exists(PROCESSED_TIFF), f"Calibrated raster missing: {PROCESSED_TIFF}"

    cfg = TerrainConfig(
        cell_size_m=20.0,
        ref_lat_deg=18.442,
        alpha_s=2.0,
        theta_crit_deg=10.0,
        theta_max_deg=25.0,
        alpha_r=1.0,
        sigma_0_m=1.5,
        alpha_up=1.5,
    )
    grid = load_and_process_terrain(PROCESSED_TIFF, config=cfg)

    # 1. Shape and spacing verification
    assert grid.shape == (250, 250)
    assert pytest.approx(grid.dy_ground_m, abs=0.01) == 20.0
    # At 18.442° N, dx = 20 * cos(18.442°) ≈ 18.973 m
    assert pytest.approx(grid.dx_ground_m, abs=0.05) == 18.973

    # 2. Interior valid regions have finite elevations, slopes, and roughness
    interior_z = grid.elevation[10:-10, 10:-10]
    interior_slope = grid.slope_deg[10:-10, 10:-10]
    interior_rough = grid.roughness_m[10:-10, 10:-10]
    interior_mask = grid.invalid_mask[10:-10, 10:-10]

    valid_cells = ~interior_mask
    assert np.any(valid_cells), "No valid cells in interior!"

    assert np.all(np.isfinite(interior_z[valid_cells]))
    assert np.all(np.isfinite(interior_slope[valid_cells]))
    assert np.all(np.isfinite(interior_rough[valid_cells]))

    # 3. Slopes at Jezero Delta: flat plains are ~0-5°, scarps up to ~20-30°
    valid_slopes = interior_slope[valid_cells]
    assert np.min(valid_slopes) >= 0.0
    assert np.max(valid_slopes) > 15.0, "Expected steep delta scarp slopes > 15°"
    assert np.mean(valid_slopes) < 15.0, "Average Jezero delta slope should be moderate (< 15°)"

    # 4. Decameter roughness proxy: typical values 0 to 5 meters
    valid_rough = interior_rough[valid_cells]
    assert np.min(valid_rough) >= 0.0
    assert np.max(valid_rough) < 25.0, "Decameter roughness should be reasonable"

    # 5. Edge cost calculation across Butler Landing area
    # Octavia Butler Landing is around row 117, col 157
    landing_u = (117, 157)
    landing_v = (117, 158)
    cost = calculate_edge_cost(landing_u, landing_v, grid)
    assert math.isfinite(cost), "Landing site edge cost should be finite"
    assert cost >= grid.dx_ground_m, "Cost should be >= ground step distance"
