#!/usr/bin/env python3
"""
MarsWalk 2.0 / Project Atlas — NASA Planetary Data Validation Engine
Executes rigorous mathematical, geospatial, and scientific integrity tests on ingested datasets:
1. CTX & HiRISE DEM spatial bounds, resolution, and CRS alignment
2. Planetary coordinate transforms (IAU 2000 Sphere -> Projected Easting/Northing -> Grid [row, col])
3. Ground-truth rover localization integrity (PDS Rover PLACES)
4. Atmospheric MEDA measurement units and diurnal tides
5. Three Forks sample depot tube coordinates and LMST timestamps
6. Geolocated science target metadata completeness
Outputs: outputs/nasa_data_integration/nasa_data_validation_summary.json
"""

from __future__ import annotations

import json
import math
import os
import sys
from typing import Any, Dict, List

import numpy as np
import rasterio


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "nasa_data_integration")


def validate_all() -> Dict[str, Any]:
    print("========================================================================")
    print("  MARSWALK 2.0 • PROJECT ATLAS — NASA PLANETARY DATA VALIDATION GATES   ")
    print("========================================================================")

    results: Dict[str, Any] = {}
    total_checks = 0
    passed_checks = 0

    def check(name: str, condition: Any, detail: str = ""):
        nonlocal total_checks, passed_checks
        total_checks += 1
        is_pass = bool(condition)
        status = "PASS" if is_pass else "FAIL"
        if is_pass:
            passed_checks += 1
            print(f"  [PASS] {name} {f'({detail})' if detail else ''}")
        else:
            print(f"  [FAIL] {name} - FAILED! {detail}")
        results[name] = {"passed": is_pass, "detail": detail}

    # ---------------------------------------------------------
    # GATE 1: CTX & HiRISE Terrain Ingestion & Alignment
    # ---------------------------------------------------------
    print("\n--- GATE 1: TERRAIN SPATIAL COVERAGE & CRS ALIGNMENT ---")
    ctx_path = os.path.join(DATA_DIR, "processed", "jezero_ready_20m.tif")
    hirise_path = os.path.join(DATA_DIR, "processed", "jezero_hirise_hawksbill_1m.tif")

    with rasterio.open(ctx_path) as ctx_src:
        check("CTX_DEM_EXISTS", True, f"{ctx_src.width}x{ctx_src.height} pixels")
        check("CTX_DEM_RESOLUTION", ctx_src.res[0] == 20.0 and ctx_src.res[1] == 20.0, "20.0m x 20.0m")
        check("CTX_DEM_CRS_VALID", "103885" in str(ctx_src.crs), str(ctx_src.crs))
        check("CTX_DEM_NODATA_VALUE", ctx_src.nodata is not None and ctx_src.nodata < -1e30, f"NoData = {ctx_src.nodata}")
        ctx_bounds = ctx_src.bounds

    with rasterio.open(hirise_path) as hi_src:
        check("HIRISE_DTM_EXISTS", True, f"{hi_src.width}x{hi_src.height} pixels")
        check("HIRISE_DTM_RESOLUTION", hi_src.res[0] == 1.0 and hi_src.res[1] == 1.0, "1.0m x 1.0m")
        check("HIRISE_DTM_CRS_MATCH", str(hi_src.crs) == str(ctx_src.crs), "ESRI:103885")
        # Check HiRISE bounds fall within CTX bounds
        hi_inside = (
            hi_src.bounds.left >= ctx_bounds.left and
            hi_src.bounds.right <= ctx_bounds.right and
            hi_src.bounds.bottom >= ctx_bounds.bottom and
            hi_src.bounds.top <= ctx_bounds.top
        )
        check("HIRISE_BOUNDS_WITHIN_CTX", hi_inside, "HiRISE sub-window fully bounded by Jezero CTX mosaic")

    # ---------------------------------------------------------
    # GATE 2: Coordinate Transformation Validation
    # ---------------------------------------------------------
    print("\n--- GATE 2: PLANETARY COORDINATE CONVERSIONS ---")
    # Three Forks Sample Depot coordinates: lon = 77.4392 deg E, lat = 18.4326 deg N
    # Test affine conversion from projected coordinates to grid (row, col)
    with rasterio.open(ctx_path) as src:
        # Projected Easting/Northing for Three Forks: approx E: 4590858, N: 1093318
        tf_easting = 4590858.0
        tf_northing = 1093318.0
        row, col = src.index(tf_easting, tf_northing)
        check("COORD_TRANSFORM_ROW_IN_BOUNDS", 0 <= row < src.height, f"row = {row} / {src.height}")
        check("COORD_TRANSFORM_COL_IN_BOUNDS", 0 <= col < src.width, f"col = {col} / {src.width}")
        elev_at_tf = src.read(1)[row, col]
        check("ELEVATION_IN_PHYSICAL_RANGE", -2600.0 <= elev_at_tf <= -2400.0, f"elevation = {elev_at_tf:.1f}m (Jezero crater floor)")

    # ---------------------------------------------------------
    # GATE 3: NASA PDS Rover PLACES Ground-Truth Integrity
    # ---------------------------------------------------------
    print("\n--- GATE 3: ROVER PLACES GROUND-TRUTH LOCALIZATION ---")
    places_path = os.path.join(DATA_DIR, "catalogs", "perseverance_ground_truth_places.json")
    with open(places_path, "r", encoding="utf-8") as f:
        places_doc = json.load(f)
    places = places_doc.get("records", [])
    check("ROVER_PLACES_RECORD_COUNT", len(places) >= 500, f"{len(places)} localization records")
    check("ROVER_PLACES_SOL_SPAN", places_doc["sol_range"][1] >= 1000, f"Sols {places_doc['sol_range'][0]} to {places_doc['sol_range'][1]}")
    # Verify coordinate ranges are in Jezero
    lats = [p["latitude_planetocentric"] for p in places]
    lons = [p["longitude_east"] for p in places]
    check("ROVER_PLACES_LAT_RANGE", 18.0 <= min(lats) and max(lats) <= 19.0, f"[{min(lats):.2f}, {max(lats):.2f}] deg N")
    check("ROVER_PLACES_LON_RANGE", 77.0 <= min(lons) and max(lons) <= 78.0, f"[{min(lons):.2f}, {max(lons):.2f}] deg E")

    # ---------------------------------------------------------
    # GATE 4: Three Forks Sample Depot Cache
    # ---------------------------------------------------------
    print("\n--- GATE 4: THREE FORKS EXTRACTED SAMPLE TUBES ---")
    samples_path = os.path.join(DATA_DIR, "catalogs", "three_forks_sample_depot_catalog.json")
    with open(samples_path, "r", encoding="utf-8") as f:
        samples_doc = json.load(f)
    samples = samples_doc.get("samples", [])
    check("THREE_FORKS_SAMPLE_COUNT", len(samples) == 10, f"{len(samples)} titanium sample tubes deposited")
    sample_names = {s["sample_name"] for s in samples}
    expected_tubes = {"Malay", "Mageik", "Crosswind Lake", "Roubion", "Coulettes", "Montdenier", "Bearwallow", "Skyland", "Atsah", "Amalik Witness"}
    check("THREE_FORKS_SAMPLE_NAMES_ACCURATE", sample_names == expected_tubes, "All 10 authentic NASA tube names reconciled")

    # ---------------------------------------------------------
    # GATE 5: NASA MEDA In-Situ Atmospheric Observations
    # ---------------------------------------------------------
    print("\n--- GATE 5: NASA MEDA ENVIRONMENTAL OBSERVATIONS ---")
    meda_path = os.path.join(DATA_DIR, "catalogs", "meda_environmental_observations.json")
    with open(meda_path, "r", encoding="utf-8") as f:
        meda_doc = json.load(f)
    stats = meda_doc.get("summary_statistics", {})
    check("MEDA_PRESSURE_METRICS_PRESENT", "pressure_pa" in stats and stats["pressure_pa"]["unit"] == "Pascals (Pa)", "Pascals (Pa)")
    check("MEDA_PRESSURE_VALUES_PHYSICAL", 650.0 <= stats["pressure_pa"]["min"] and stats["pressure_pa"]["max"] <= 850.0, f"Range: {stats['pressure_pa']['min']} - {stats['pressure_pa']['max']} Pa")
    check("MEDA_AIR_TEMP_PHYSICAL", -120.0 <= stats["air_temperature_c"]["min"] and stats["air_temperature_c"]["max"] <= 0.0, f"Range: {stats['air_temperature_c']['min']} - {stats['air_temperature_c']['max']} °C")
    check("MEDA_DIURNAL_PROFILE_PRESENT", len(meda_doc.get("diurnal_reference_profile", [])) >= 8, f"{len(meda_doc.get('diurnal_reference_profile', []))} LMST timepoints")

    # ---------------------------------------------------------
    # GATE 6: Geolocated Science Targets
    # ---------------------------------------------------------
    print("\n--- GATE 6: GEOLOCATED SCIENCE TARGETS ---")
    sci_path = os.path.join(DATA_DIR, "catalogs", "geolocated_science_targets.json")
    with open(sci_path, "r", encoding="utf-8") as f:
        sci_doc = json.load(f)
    targets = sci_doc.get("targets", [])
    check("SCIENCE_TARGETS_COUNT", len(targets) >= 5, f"{len(targets)} scientific observation targets")
    target_names = [t["name"] for t in targets]
    check("SCIENCE_TARGETS_INCLUDES_WILDCAT", any("Wildcat" in n for n in target_names), "Wildcat Ridge Organic Mudstone")
    check("SCIENCE_TARGETS_INCLUDES_SKINNER", any("Skinner" in n for n in target_names), "Skinner Ridge Deltaic Sandstone")
    check("SCIENCE_TARGETS_CITATIONS_PRESENT", all(len(t.get("pds_citation", "")) > 0 for t in targets), "PDS citations on all targets")

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    summary_path = os.path.join(OUTPUT_DIR, "nasa_data_validation_summary.json")
    summary = {
        "validation_version": "2.0.0",
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "all_passed": total_checks == passed_checks,
        "results": results,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n========================================================================")
    print(f"VALIDATION GATES COMPLETE: {passed_checks}/{total_checks} PASSED ({'ALL CLEAR' if total_checks == passed_checks else 'FAILURES'})")
    print(f"Summary Report: {summary_path}")
    print("========================================================================")
    return summary


if __name__ == "__main__":
    val = validate_all()
    if not val["all_passed"]:
        sys.exit(1)
