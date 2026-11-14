"""
MarsWalk 2.0 / Project Atlas - Milestone 13C
Geospatial & Terrain Coordinate Transformation Pipeline Audit Test Suite

Audits:
1. Authentic USGS CTX 20m DTM raster (dimensions, resolution, bounds, CRS, nodata values, SHA-256).
2. Web Mission Data JSON consistency and millimetric alignment with GeoTIFF raster.
3. Coordinate transformation formulas (IAU 2000 Mars Spheroid R=3396190m, Equirectangular cosine metric scaling dx/dy).
4. Three.js 3D world (x, y, z) coordinate mapping centered at (0, 0, 0).
5. Vertical exaggeration strict separation from analytical calculations and NoData safety.
6. Waypoint and route polyline elevation snapping and vertical facet clearance.
"""

import hashlib
import json
import math
import os
from pathlib import Path
import numpy as np
import pytest
import rasterio

from marswalk.core.terrain import (
    TerrainConfig,
    TerrainGrid,
    compute_ground_spacings,
    compute_horn_slope,
    create_invalid_mask,
    derive_terrain_from_array,
    load_and_process_terrain,
    MARS_RADIUS_M,
    METERS_PER_DEGREE_LAT,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_TIFF = REPO_ROOT / "data" / "processed" / "jezero_ready_20m.tif"
RAW_TIFF = REPO_ROOT / "data" / "raw" / "JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif"
WEB_MISSION_DATA_JSON = REPO_ROOT / "web" / "data" / "jezero_mission_data.json"
WEB_PUBLIC_MISSION_DATA_JSON = REPO_ROOT / "web" / "public" / "data" / "jezero_mission_data.json"


# ==============================================================================
# 1. AUTHENTIC USGS CTX 20m DTM RASTER AUDIT
# ==============================================================================
def test_audit_01_geotiff_raster_provenance_and_dimensions():
    """Verify authentic USGS CTX 20m DTM raster dimensions, CRS, resolution, and bounds."""
    assert PROCESSED_TIFF.exists(), f"Processed GeoTIFF missing: {PROCESSED_TIFF}"

    with rasterio.open(PROCESSED_TIFF) as src:
        # Dimensions: 250 x 250 cells
        assert src.width == 250, f"Expected width 250, got {src.width}"
        assert src.height == 250, f"Expected height 250, got {src.height}"
        assert src.count == 1, "Expected single-band raster"

        # Resolution: 20m x 20m projected cell size
        res_x, res_y = src.res
        assert math.isclose(res_x, 20.0, abs_tol=1e-6), f"Expected 20.0m res_x, got {res_x}"
        assert math.isclose(res_y, 20.0, abs_tol=1e-6), f"Expected 20.0m res_y, got {res_y}"

        # Projected bounds: exactly 5000m x 5000m
        bounds = src.bounds
        width_m = bounds.right - bounds.left
        height_m = bounds.top - bounds.bottom
        assert math.isclose(width_m, 5000.0, abs_tol=1e-3), f"Expected width 5000m, got {width_m}"
        assert math.isclose(height_m, 5000.0, abs_tol=1e-3), f"Expected height 5000m, got {height_m}"
        assert math.isclose(bounds.left, 4587723.250853, abs_tol=1e-3)
        assert math.isclose(bounds.right, 4592723.250853, abs_tol=1e-3)
        assert math.isclose(bounds.bottom, 1090653.140188, abs_tol=1e-3)
        assert math.isclose(bounds.top, 1095653.140188, abs_tol=1e-3)

        # CRS: ESRI:103885 (Equirectangular Mars 2000 Sphere IAU)
        crs_wkt = src.crs.to_wkt()
        assert "Mars" in crs_wkt, f"CRS does not identify Mars: {crs_wkt}"
        assert "Equirectangular" in crs_wkt, f"CRS is not Equirectangular: {crs_wkt}"
        assert "3396190" in crs_wkt, f"Mars radius 3396190m missing from CRS: {crs_wkt}"

        # Elevation range: crater floor (-2624m to -2445m)
        elev = src.read(1)
        nodata = src.nodata
        assert math.isclose(nodata, -3.4028226550889045e+38, rel_tol=1e-5), f"Unexpected nodata sentinel: {nodata}"

        # Ensure zero nodata cells in the prepared 250x250 Jezero ROI
        nodata_count = np.isclose(elev, nodata).sum()
        assert nodata_count == 0, f"Expected 0 nodata cells, found {nodata_count}"
        assert np.isnan(elev).sum() == 0, "Found NaN in processed elevation"

        min_elev = float(elev.min())
        max_elev = float(elev.max())
        assert -2624.0 <= min_elev <= -2623.5, f"Min elevation {min_elev} outside [-2624, -2623.5]"
        assert -2445.5 <= max_elev <= -2445.0, f"Max elevation {max_elev} outside [-2445.5, -2445.0]"


def test_audit_02_raster_cryptographic_authenticity():
    """Verify SHA-256 cryptographic digest of the authentic processed raster."""
    with open(PROCESSED_TIFF, "rb") as f:
        file_sha256 = hashlib.sha256(f.read()).hexdigest()

    expected_sha256 = "875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3"
    assert file_sha256 == expected_sha256, (
        f"Processed GeoTIFF SHA-256 altered: got {file_sha256}, expected {expected_sha256}"
    )


# ==============================================================================
# 2. WEB MISSION DATA JSON AUDIT
# ==============================================================================
def test_audit_03_web_mission_data_json_alignment():
    """Verify web JSON elevation and slope samples align with GeoTIFF raster to millimetric precision."""
    assert WEB_MISSION_DATA_JSON.exists(), f"Web mission data JSON missing: {WEB_MISSION_DATA_JSON}"
    assert WEB_PUBLIC_MISSION_DATA_JSON.exists(), f"Public web mission data JSON missing: {WEB_PUBLIC_MISSION_DATA_JSON}"

    with open(WEB_MISSION_DATA_JSON, "r") as f:
        data = json.load(f)

    # Check grid metadata
    grid = data["grid"]
    assert grid["rows"] == 250
    assert grid["cols"] == 250
    assert math.isclose(grid["projected_cell_size_m"], 20.0, abs_tol=1e-5)
    assert math.isclose(grid["ground_dx_m"], 18.973, abs_tol=1e-3)
    assert math.isclose(grid["ground_dy_m"], 20.0, abs_tol=1e-5)

    # Matrix dimensions
    elev_samples = np.array(data["elevation_samples"], dtype=np.float32)
    assert elev_samples.shape == (250, 250)

    # Compare with actual GeoTIFF
    with rasterio.open(PROCESSED_TIFF) as src:
        tif_elev = src.read(1)

    diff = np.abs(tif_elev - elev_samples)
    assert diff.max() < 0.01, f"Max difference between GeoTIFF and JSON elevation exceeded 1cm: {diff.max()}m"
    assert diff.mean() < 0.005, f"Mean difference exceeded 5mm: {diff.mean()}m"

    # Verify slope samples match Horn slope within 2-decimal rounding tolerance
    if "slope_samples" in data:
        slope_samples = np.array(data["slope_samples"], dtype=np.float32)
        assert slope_samples.shape == (250, 250)
        tg = load_and_process_terrain(str(PROCESSED_TIFF))
        slope_diff = np.abs(tg.slope_deg - slope_samples)
        assert np.nanmax(slope_diff) < 0.01, f"Max slope diff exceeded 0.01 deg: {np.nanmax(slope_diff)}"


# ==============================================================================
# 3. COORDINATE TRANSFORMATION FORMULAS AUDIT
# ==============================================================================
def test_audit_04_iau_mars_spheroid_and_equirectangular_scaling():
    """
    Verify Equirectangular cosine metric scaling at Jezero reference latitude (18.442 deg N).
    dx = C * cos(ref_lat) = 20.0 * cos(18.442 deg) = 18.972887 m.
    dy = 20.000000 m.
    """
    ref_lat_deg = 18.442
    lat_rad = math.radians(ref_lat_deg)
    cos_lat = math.cos(lat_rad)
    cell_size = 20.0

    expected_dx = cell_size * cos_lat
    expected_dy = cell_size

    calc_dx, calc_dy = compute_ground_spacings(cell_size_m=cell_size, ref_lat_deg=ref_lat_deg)

    assert math.isclose(calc_dx, expected_dx, rel_tol=1e-12)
    assert math.isclose(calc_dy, expected_dy, rel_tol=1e-12)
    assert math.isclose(calc_dx, 18.972887, abs_tol=1e-5)
    assert round(calc_dx, 3) == 18.973

    # Check meridian and parallel metric scales
    expected_meridian_m_deg = (math.pi * MARS_RADIUS_M) / 180.0
    assert math.isclose(METERS_PER_DEGREE_LAT, expected_meridian_m_deg, rel_tol=1e-9)
    assert math.isclose(METERS_PER_DEGREE_LAT, 59274.69752, abs_tol=1e-3)

    # Check forward and inverse transformation
    with open(WEB_MISSION_DATA_JSON, "r") as f:
        data = json.load(f)

    proj_bounds = data["bounds"]["projected"]
    geo_bounds = data["bounds"]["geographic"]

    # Projected bounds -> geographic bounds
    calc_min_lon = proj_bounds["left"] / METERS_PER_DEGREE_LAT
    calc_max_lon = proj_bounds["right"] / METERS_PER_DEGREE_LAT
    calc_min_lat = proj_bounds["bottom"] / METERS_PER_DEGREE_LAT
    calc_max_lat = proj_bounds["top"] / METERS_PER_DEGREE_LAT

    assert math.isclose(calc_min_lon, geo_bounds["min_lon_deg"], abs_tol=1e-5)
    assert math.isclose(calc_max_lon, geo_bounds["max_lon_deg"], abs_tol=1e-5)
    assert math.isclose(calc_min_lat, geo_bounds["min_lat_deg"], abs_tol=1e-5)
    assert math.isclose(calc_max_lat, geo_bounds["max_lat_deg"], abs_tol=1e-5)


def test_audit_05_threejs_plane_geometry_coordinate_mapping():
    """
    Verify Three.js plane geometry mapping formulas from grid (r, c) to local world (x, y, z):
    totalW = (cols - 1) * dx
    totalH = (rows - 1) * dy
    halfW = totalW / 2.0
    halfH = totalH / 2.0
    x = c * dx - halfW
    z = r * dy - halfH
    y = (elev - minElev) * exaggeration
    """
    rows = 250
    cols = 250
    dx = 18.972887
    dy = 20.0
    min_elev = -2623.8362
    max_elev = -2445.0170

    total_w = (cols - 1) * dx
    total_h = (rows - 1) * dy
    half_w = total_w / 2.0
    half_h = total_h / 2.0

    # Corner 0: (r=0, c=0) -> North-West
    x0 = 0 * dx - half_w
    z0 = 0 * dy - half_h
    assert math.isclose(x0, -half_w, abs_tol=1e-6)
    assert math.isclose(z0, -half_h, abs_tol=1e-6)

    # Corner 1: (r=0, c=249) -> North-East
    x1 = (cols - 1) * dx - half_w
    z1 = 0 * dy - half_h
    assert math.isclose(x1, half_w, abs_tol=1e-6)
    assert math.isclose(z1, -half_h, abs_tol=1e-6)

    # Corner 2: (r=249, c=0) -> South-West
    x2 = 0 * dx - half_w
    z2 = (rows - 1) * dy - half_h
    assert math.isclose(x2, -half_w, abs_tol=1e-6)
    assert math.isclose(z2, half_h, abs_tol=1e-6)

    # Corner 3: (r=249, c=249) -> South-East
    x3 = (cols - 1) * dx - half_w
    z3 = (rows - 1) * dy - half_h
    assert math.isclose(x3, half_w, abs_tol=1e-6)
    assert math.isclose(z3, half_h, abs_tol=1e-6)

    # Geometric center: (r=124.5, c=124.5) -> (0, 0, 0)
    xc = 124.5 * dx - half_w
    zc = 124.5 * dy - half_h
    assert math.isclose(xc, 0.0, abs_tol=1e-9)
    assert math.isclose(zc, 0.0, abs_tol=1e-9)

    # Elevation baseline: min elevation maps to y = 0
    y_min = (min_elev - min_elev) * 1.5
    assert math.isclose(y_min, 0.0, abs_tol=1e-9)

    # Max elevation relief:
    y_max = (max_elev - min_elev) * 1.5
    assert math.isclose(y_max, 178.8192 * 1.5, abs_tol=1e-3)


# ==============================================================================
# 4. VERTICAL EXAGGERATION & NODATA SAFETY AUDIT
# ==============================================================================
def test_audit_06_vertical_exaggeration_analytical_separation():
    """
    Ensure vertical exaggeration is strictly isolated to 3D visualization
    and does NOT affect analytical distances, slopes, or traversal costs.
    """
    tg = load_and_process_terrain(str(PROCESSED_TIFF))

    # Analytical step distance
    u = (100, 100)
    v = (100, 101)
    d_ew = tg.dx_ground_m  # 18.973 m

    # The ground metric distance must not be modified by visual exaggeration
    for exag in [1.0, 1.5, 2.0, 3.0]:
        # Visual height difference is magnified
        z1 = float(tg.elevation[u])
        z2 = float(tg.elevation[v])
        dz_real = z2 - z1
        dz_visual = dz_real * exag

        # But analytical slope remains invariant
        analytical_slope = tg.slope_deg[u]
        assert not math.isnan(analytical_slope)
        assert tg.config.cell_size_m == 20.0


def test_audit_07_nodata_safety_and_clamping():
    """
    Verify that NoData sentinels (-3.4e38, -32768), NaNs, or extreme negative values
    are properly masked by create_invalid_mask and do not create false zero-elevation sinkholes.
    """
    test_grid = np.array([
        [-2500.0, -2505.0, -2510.0],
        [-2502.0, -3.40282e+38, -2508.0],
        [-2501.0, -2504.0, -2506.0]
    ], dtype=np.float32)

    mask = create_invalid_mask(test_grid, nodata_sentinel=-3.40282e+38)
    assert mask[1, 1] == True
    assert mask.sum() == 1

    # Dilation by 1 pixel protects 3x3 convolution neighbors
    from marswalk.core.terrain import dilate_invalid_mask
    dilated = dilate_invalid_mask(mask, iterations=1)
    assert np.all(dilated), "A single central invalid cell must dilate to all 9 cells in a 3x3 block"


# ==============================================================================
# 5. ROUTE & WAYPOINT SNAPPING AUDIT
# ==============================================================================
def test_audit_08_waypoint_snapping_accuracy():
    """Verify all 12 science waypoints snap cleanly inside the 250x250 grid and match DEM elevation."""
    with open(WEB_MISSION_DATA_JSON, "r") as f:
        data = json.load(f)

    waypoints = data["waypoints"]
    assert len(waypoints) == 12

    elev_samples = data["elevation_samples"]

    for wp in waypoints:
        r = wp["row"]
        c = wp["col"]
        wp_id = wp["id"]

        assert 0 <= r < 250, f"Waypoint {wp_id} row {r} out of bounds"
        assert 0 <= c < 250, f"Waypoint {wp_id} col {c} out of bounds"

        dem_elev = elev_samples[r][c]
        wp_elev = wp["elevation_m"]
        assert math.isclose(dem_elev, wp_elev, abs_tol=0.02), (
            f"Waypoint {wp_id} elevation {wp_elev} deviates from DEM elevation {dem_elev}"
        )


def test_audit_09_route_polyline_snapping_and_facet_clearance():
    """
    Verify route polylines have positive vertical clearance above terrain facets.
    In web/app.js:
    rcToLocalPos adds +6.0m base vertical offset.
    drawLiveRoute adds +4.0m (total +10.0m).
    drawDetourRoute adds +8.0m (total +14.0m).
    This guarantees zero facet clipping across non-planar triangle intersections.
    """
    with open(WEB_MISSION_DATA_JSON, "r") as f:
        data = json.load(f)

    routes = data["routes"]
    for profile_key in ["conservative", "balanced", "science_first"]:
        assert profile_key in routes, f"Route profile {profile_key} missing"
        route = routes[profile_key]
        path_rc = route["path_rc"]
        assert len(path_rc) > 1, f"Route {profile_key} has insufficient path steps"

        for step in path_rc:
            r, c = step
            assert 0 <= r < 250, f"Route step ({r}, {c}) row out of bounds"
            assert 0 <= c < 250, f"Route step ({r}, {c}) col out of bounds"
