"""
Automated unit and calibration tests for MarsWalk data ingestion (Milestone 1).
Tests TC-08 (coordinate round-trip accuracy) and TC-09 (Jezero elevation benchmark).
"""
import os
import json
import math
import pytest
import numpy as np

from marswalk.data.ingest import (
    planetocentric_to_proj_xy,
    proj_xy_to_planetocentric,
    inspect_geotiff,
    query_elevation_at_lonlat,
    MARS_RADIUS_M,
    METERS_PER_DEGREE_LAT,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_TIFF = os.path.join(REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")
WAYPOINTS_JSON = os.path.join(REPO_ROOT, "data", "waypoints_jezero.json")


def test_processed_raster_exists_and_dimensions():
    """Verify that the calibrated Jezero crop exists with exact 250x250 dimensions."""
    assert os.path.exists(PROCESSED_TIFF), f"Processed raster missing: {PROCESSED_TIFF}"
    meta = inspect_geotiff(PROCESSED_TIFF)
    assert meta["width"] == 250, f"Expected width 250, got {meta['width']}"
    assert meta["height"] == 250, f"Expected height 250, got {meta['height']}"
    assert meta["count"] == 1, f"Expected 1 band, got {meta['count']}"
    assert meta["dtype"] == "float32", f"Expected float32, got {meta['dtype']}"
    assert meta["resolution"] == (20.0, 20.0), f"Expected 20.0 m resolution, got {meta['resolution']}"


def test_elevation_statistics():
    """Verify that elevation values are within expected Jezero Crater delta ranges."""
    meta = inspect_geotiff(PROCESSED_TIFF)
    min_elev = meta["elevation_min_m"]
    max_elev = meta["elevation_max_m"]
    assert min_elev is not None and max_elev is not None
    assert -2700.0 < min_elev < -2500.0, f"Unexpected min elevation: {min_elev}"
    assert -2500.0 < max_elev < -2300.0, f"Unexpected max elevation: {max_elev}"
    assert max_elev > min_elev + 100.0, "Expected at least 100 m of delta relief"


def test_tc_08_coordinate_transform_roundtrip():
    """
    TC-08: Convert Perseverance Landing Site (18.4447° N, 77.4508° E) to (X, Y) and back.
    Asserts round-trip latitude/longitude error is < 0.0002° (< 12 m, within half a 20m pixel).
    """
    orig_lon = 77.4508
    orig_lat = 18.4447

    x, y = planetocentric_to_proj_xy(orig_lon, orig_lat)
    calc_lon, calc_lat = proj_xy_to_planetocentric(x, y)

    lon_error_deg = abs(calc_lon - orig_lon)
    lat_error_deg = abs(calc_lat - orig_lat)

    assert lon_error_deg < 0.0002, f"TC-08 failed: Lon error {lon_error_deg}° >= 0.0002°"
    assert lat_error_deg < 0.0002, f"TC-08 failed: Lat error {lat_error_deg}° >= 0.0002°"

    # Metric distance error on Mars surface
    error_meters = math.sqrt(
        (lat_error_deg * METERS_PER_DEGREE_LAT) ** 2
        + (lon_error_deg * METERS_PER_DEGREE_LAT * math.cos(orig_lat * math.pi / 180.0)) ** 2
    )
    assert error_meters < 1.0, f"TC-08 metric ground error {error_meters:.4f} m >= 1.0 m"


def test_tc_09_jezero_elevation_sanity_check():
    """
    TC-09: Query DEM elevation at Octavia E. Butler Landing (18.4447° N, 77.4508° E).
    Returns elevation within published MOLA/CTX benchmark range of -2570 +/- 25 meters.
    """
    elev, row, col = query_elevation_at_lonlat(PROCESSED_TIFF, 77.4508, 18.4447)
    benchmark_elev = -2570.0
    tolerance_m = 25.0

    assert 0 <= row < 250
    assert 0 <= col < 250
    assert abs(elev - benchmark_elev) <= tolerance_m, (
        f"TC-09 failed: Measured elevation {elev:.2f} m outside benchmark range "
        f"[{benchmark_elev - tolerance_m}, {benchmark_elev + tolerance_m}]"
    )


def test_all_waypoints_contained_and_valid():
    """Verify all 6 curated waypoints fall within the 250x250 grid with valid elevations."""
    assert os.path.exists(WAYPOINTS_JSON), f"Waypoints file missing: {WAYPOINTS_JSON}"
    with open(WAYPOINTS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    waypoints = data["waypoints"]
    assert len(waypoints) >= 6, "Expected at least 6 waypoints"

    for wp in waypoints:
        elev, r, c = query_elevation_at_lonlat(PROCESSED_TIFF, wp["lon_deg"], wp["lat_deg"])
        # Ensure interior pixel with at least 5 px margin from raster borders
        assert 5 <= r < 245, f"Waypoint {wp['id']} row {r} too close to edge"
        assert 5 <= c < 245, f"Waypoint {wp['id']} col {c} too close to edge"
        assert -2700.0 <= elev <= -2400.0, f"Waypoint {wp['id']} elevation {elev} out of bounds"
        assert wp["priority_score"] > 0, f"Waypoint {wp['id']} missing priority score"
