"""
MarsWalk 2.0 - Milestone 9E Verification Tests
Tests for multi-scale planetary exploration, imagery coverage registry,
honest elevation/imagery separation, coordinate contracts, and route API preservation.
"""

import os
import json
import pytest
from PIL import Image

from marswalk.data.imagery_registry import (
    load_imagery_registry,
    ImageryRegistry,
    ImageryProduct,
    GeographicBounds,
)
from marswalk.core.terrain import load_and_process_terrain
from marswalk.core.planner import plan_route, ScienceWaypoint, PlannerConfig
from marswalk.api.service import plan_route_api, APIError
import rasterio


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_imagery_registry_file_and_schema():
    """Verify registry JSON file exists, conforms to schema, and has required metadata."""
    reg_path = os.path.join(PROJECT_ROOT, "web", "data", "mars_imagery_registry.json")
    assert os.path.isfile(reg_path), f"Registry file missing: {reg_path}"

    with open(reg_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("schema_version") == "1.0.0"
    assert data.get("target") == "Mars"
    assert "ESRI:103885" in data.get("crs", "")

    meta = data.get("metadata", {})
    assert meta.get("total_products", 0) >= 7
    assert meta.get("global_basemaps_count", 0) >= 2
    assert meta.get("regional_mosaics_count", 0) >= 4
    assert meta.get("local_elevation_meshes_count", 0) == 1

    products = data.get("products", [])
    assert len(products) >= 7


def test_imagery_registry_integrity_and_bounds():
    """Verify registry logic, bounds ranges, and non-empty attributions."""
    reg = load_imagery_registry()
    assert isinstance(reg, ImageryRegistry)
    assert len(reg.products) >= 7

    errors = reg.validate_integrity()
    assert len(errors) == 0, f"Registry integrity validation failed: {errors}"

    for p in reg.products:
        assert p.id, "Product must have an id"
        assert p.title, f"Product {p.id} missing title"
        assert p.source, f"Product {p.id} missing source"
        assert p.attribution, f"Product {p.id} missing attribution"
        assert p.nominal_resolution_m > 0, f"Product {p.id} invalid resolution"
        assert -90.0 <= p.bounds.min_lat_deg <= p.bounds.max_lat_deg <= 90.0


def test_elevation_vs_imagery_separation():
    """
    Verify strict separation between optical imagery and genuine elevation data.
    Regional CTX mosaics must NOT claim elevation data or route planning capability.
    """
    reg = load_imagery_registry()

    # Jezero local study area has authentic elevation
    jez = reg.get_by_id("jezero_ctx_local_mesh")
    assert jez is not None
    assert jez.has_elevation_data is True
    assert jez.planning_supported is True
    assert jez.elevation_resolution_m == 20.0
    assert reg.has_highres_elevation(77.44, 18.44) is True

    # Regional CTX mosaics are optical imagery ONLY
    regional_ids = [
        "olympus_mons_ctx_regional",
        "gale_crater_ctx_regional",
        "valles_marineris_ctx_regional",
        "gusev_crater_ctx_regional",
        "hellas_planitia_ctx_regional",
    ]
    for rid in regional_ids:
        prod = reg.get_by_id(rid)
        if prod:
            assert prod.has_elevation_data is False, f"{rid} must not claim elevation data"
            assert prod.planning_supported is False, f"{rid} must not claim planning capability"
            assert prod.elevation_source is None

    # Regional locations must report NO high-res elevation
    assert reg.has_highres_elevation(-133.8, 18.65) is False  # Olympus Mons
    assert reg.has_highres_elevation(137.4, -4.6) is False     # Gale Crater
    assert reg.has_highres_elevation(150.0, 13.0) is False     # Elysium Planitia


def test_geographic_coverage_matching():
    """Test best imagery lookup across planetary scales."""
    reg = load_imagery_registry()

    # 1. Jezero crater center -> jezero_ctx_local_mesh
    best_jez = reg.find_best_imagery(77.4398, 18.4421)
    assert best_jez.id == "jezero_ctx_local_mesh"
    assert best_jez.nominal_resolution_m < 10.0

    # 2. Olympus Mons caldera -> olympus_mons_ctx_regional
    best_oly = reg.find_best_imagery(-133.8, 18.65)
    assert best_oly.id == "olympus_mons_ctx_regional"
    assert best_oly.nominal_resolution_m == 6.0

    # 3. Gale Crater -> gale_crater_ctx_regional
    best_gale = reg.find_best_imagery(137.4, -4.6)
    assert best_gale.id == "gale_crater_ctx_regional"
    assert best_gale.nominal_resolution_m == 6.0

    # 4. Elysium Planitia -> honest fallback to global basemap
    best_elys = reg.find_best_imagery(150.0, 13.0)
    assert best_elys.id == "mars_viking_mdim21_global"
    assert best_elys.nominal_resolution_m == 232.0


def test_local_cached_previews_exist_and_sizes():
    """Verify packaged regional CTX previews are valid, non-empty, and lightweight."""
    previews = [
        "web/assets/olympus_mons_ctx_preview.jpg",
        "web/assets/gale_crater_ctx_preview.jpg",
        "web/assets/jezero_ctx_orthomosaic.jpg",
    ]
    for p in previews:
        full_p = os.path.join(PROJECT_ROOT, p)
        assert os.path.isfile(full_p), f"Asset missing: {p}"
        size_kb = os.path.getsize(full_p) / 1024
        assert 10.0 < size_kb < 500.0, f"Asset size outside reasonable bounds: {p} ({size_kb:.1f} KB)"
        with Image.open(full_p) as img:
            assert img.width >= 512
            assert img.height >= 512
            assert img.mode in ("RGB", "L")


def test_preservation_of_live_routing_api_and_boundary_safety():
    """Verify Python A* planning API functions within Jezero DTM and rejects outside queries."""
    geotiff = os.path.join(PROJECT_ROOT, "data", "processed", "jezero_ready_20m.tif")
    wps_json = os.path.join(PROJECT_ROOT, "data", "waypoints_jezero.json")

    terrain = load_and_process_terrain(geotiff)
    with rasterio.open(geotiff) as src:
        transform = src.transform

    with open(wps_json, "r", encoding="utf-8") as f:
        wp_data = json.load(f)
    waypoints = [
        ScienceWaypoint(
            id=w["id"],
            name=w["name"],
            rc=(117, 157) if w["type"] == "landing_site" else (66, 128),
            priority_score=float(w.get("priority_score", 0)),
        )
        for w in wp_data.get("waypoints", [])
    ]

    # Valid route within Jezero study boundary
    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "conservative",
    }
    result = plan_route_api(payload, terrain, transform, waypoints)
    assert result["is_reachable"] is True
    assert result["distance_m"] > 0
    assert len(result["path_rc"]) > 0

    # Outside bounds query (e.g., Olympus Mons coordinates) must raise APIError
    bad_payload = {
        "start": {"lon_deg": -133.8, "lat_deg": 18.65},
        "goal": {"lon_deg": -133.5, "lat_deg": 18.70},
        "profile": "conservative",
    }
    with pytest.raises(APIError) as exc_info:
        plan_route_api(bad_payload, terrain, transform, waypoints)
    assert exc_info.value.status_code in (400, 422)


def test_frontend_html_and_css_milestone_9e_elements():
    """Verify index.html and styles.css include Milestone 9E elements."""
    html_path = os.path.join(PROJECT_ROOT, "web", "index.html")
    css_path = os.path.join(PROJECT_ROOT, "web", "styles.css")

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert "locCardImagery" in html
    assert "locCardElevation" in html
    assert "telemetryLayer" in html
    assert "telemetryElevStatus" in html
    assert "diagActiveLayer" in html
    assert "diagNominalRes" in html
    assert "diagCacheStatus" in html

    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    assert ".location-imagery-badge-row" in css
    assert ".imagery-tag" in css
    assert ".elevation-tag" in css
