"""
Unit and regression tests for MarsWalk 2.0 Mission Assets Exporter.
Verifies authentic terrain export, geodetic coordinates, waypoint ingestion,
and A* route calculations for the 3D Planetary Atlas.
"""

import os
import sys
import json
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.export_mission_assets import export_mission_assets


def test_export_mission_assets_structure_and_provenance(tmp_path):
    output_dir = str(tmp_path / "web_data")
    output_file = export_mission_assets(
        geotiff_path="data/processed/jezero_ready_20m.tif",
        waypoints_path="data/waypoints_jezero.json",
        output_dirs=(output_dir,),
    )

    assert os.path.exists(output_file), f"Export file missing at {output_file}"

    with open(output_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Metadata & Geodetic Provenance
    assert data["target"] == "Mars"
    assert "ESRI:103885" in data["crs"]
    assert "MOLA DeltaGeoid" in data["datum"]
    assert "USGS Astrogeology" in data["source_attribution"]["elevation"]
    assert "Perseverance" in data["source_attribution"]["waypoints"]
    assert "research simulation prototype" in data["source_attribution"]["disclaimer"].lower()

    # 2. Bounding Box & Grid Calibration
    bounds_geo = data["bounds"]["geographic"]
    assert 77.39 < bounds_geo["min_lon_deg"] < 77.41
    assert 77.47 < bounds_geo["max_lon_deg"] < 77.49
    assert 18.39 < bounds_geo["min_lat_deg"] < 18.41
    assert 18.47 < bounds_geo["max_lat_deg"] < 18.49

    grid = data["grid"]
    assert grid["rows"] == 250
    assert grid["cols"] == 250
    assert abs(grid["ground_dx_m"] - 18.973) < 0.05
    assert abs(grid["ground_dy_m"] - 20.000) < 0.01

    # 3. Waypoints Validation
    wps = data["waypoints"]
    assert len(wps) == 12
    wp_ids = {w["id"] for w in wps}
    assert "octavia_butler_landing" in wp_ids
    assert "delta_rim_overlook" in wp_ids
    assert "hawksbill_gap" in wp_ids
    assert "seitah_dunes" in wp_ids
    assert "skinner_ridge" in wp_ids

    for w in wps:
        assert 0 <= w["row"] < 250
        assert 0 <= w["col"] < 250
        assert -2700.0 < w["elevation_m"] < -2400.0
        assert len(w["pds_citation"]) > 0

    # 4. Authentic Python A* Routes
    routes = data["routes"]
    assert set(routes.keys()) == {"conservative", "balanced", "science_first"}

    cons = routes["conservative"]
    assert cons["is_reachable"] is True
    assert 1000.0 < cons["distance_m"] < 1500.0
    assert len(cons["coordinates_3d"]) == cons["num_cells"]
    assert cons["cumulative_climb_m"] >= 0.0
    assert "travel_time_s" in cons
    assert "formatted_travel_time" in cons

    sci = routes["science_first"]
    assert sci["is_reachable"] is True
    assert sci["distance_m"] > cons["distance_m"]
    assert sci["science_score"] > cons["science_score"]

    # 5. Elevation and Slope Samples
    elev_samples = data["elevation_samples"]
    assert len(elev_samples) == 250
    assert len(elev_samples[0]) == 250

    slope_samples = data["slope_samples"]
    assert len(slope_samples) == 250
    assert len(slope_samples[0]) == 250
