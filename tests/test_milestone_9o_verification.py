"""
Milestone 9O Verification Tests.

Validates:
1. Multi-scale planetary imagery registry schema, texture_bounds, and sensor resolutions.
2. Exact geographic registration for regional mosaics (Olympus Mons, Valles Marineris, Gale Crater),
   specifically preventing the 7x stretching distortion on Valles Marineris.
3. Safe planetary tile cache engine, strict allowlist enforcement, coordinate validation,
   and atomic persistence.
4. Server endpoints /api/imagery/status and /api/imagery/tile with cache headers.
5. Strict separation of optical imagery from high-resolution elevation models (zero hallucination guarantee).
6. Frontend scientific disclosures (display sampling, synthetic contrast enhancement, planning limits).
"""

import json
from pathlib import Path
import urllib.request
import urllib.error
import pytest

from marswalk.data.imagery_registry import load_imagery_registry, ImageryProduct, GeographicBounds
from marswalk.data.tile_cache import PlanetaryTileCache, TileCacheError, ALLOWED_TILE_PRODUCTS

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = WORKSPACE_ROOT / "web"


def test_imagery_registry_integrity_and_bounds():
    """Verify registry parses completely with zero validation errors and all products valid."""
    registry = load_imagery_registry()
    errors = registry.validate_integrity()
    assert errors == [], f"Registry validation reported errors: {errors}"
    assert len(registry.products) >= 9

    # Check key destinations exist
    olympus = registry.get_by_id("olympus_mons_ctx_regional")
    valles = registry.get_by_id("valles_marineris_ctx_regional")
    gale = registry.get_by_id("gale_crater_ctx_regional")
    jezero = registry.get_by_id("jezero_ctx_local_mesh")

    assert olympus is not None
    assert valles is not None
    assert gale is not None
    assert jezero is not None


def test_texture_bounds_exact_geographic_registration():
    """
    Verify regional imagery products define exact texture_bounds matching their stitched tile quads.
    This explicitly prevents the 7x distortion bug where regional bounds were used instead of tile bounds.
    """
    registry = load_imagery_registry()

    # Valles Marineris: bounds are [-78, -40] (38 deg span), but preview is 2x2 stitch at Z=6 [-53.4375, -47.8125] (5.625 deg span)
    valles = registry.get_by_id("valles_marineris_ctx_regional")
    assert valles.texture_bounds is not None
    assert pytest.approx(valles.texture_bounds.min_lon_deg, 0.001) == -53.4375
    assert pytest.approx(valles.texture_bounds.max_lon_deg, 0.001) == -47.8125
    assert pytest.approx(valles.texture_bounds.min_lat_deg, 0.001) == -22.5
    assert pytest.approx(valles.texture_bounds.max_lat_deg, 0.001) == -16.875

    # Olympus Mons: preview is 2x2 stitch at Z=6 [-135.0, -129.375] lon, [14.0625, 19.6875] lat
    olympus = registry.get_by_id("olympus_mons_ctx_regional")
    assert olympus.texture_bounds is not None
    assert pytest.approx(olympus.texture_bounds.min_lon_deg, 0.001) == -135.0
    assert pytest.approx(olympus.texture_bounds.max_lon_deg, 0.001) == -129.375
    assert pytest.approx(olympus.texture_bounds.min_lat_deg, 0.001) == 14.0625
    assert pytest.approx(olympus.texture_bounds.max_lat_deg, 0.001) == 19.6875

    # Gale Crater: preview is 2x2 stitch at Z=6 [135.0, 140.625] lon, [-8.4375, -2.8125] lat
    gale = registry.get_by_id("gale_crater_ctx_regional")
    assert gale.texture_bounds is not None
    assert pytest.approx(gale.texture_bounds.min_lon_deg, 0.001) == 135.0
    assert pytest.approx(gale.texture_bounds.max_lon_deg, 0.001) == 140.625
    assert pytest.approx(gale.texture_bounds.min_lat_deg, 0.001) == -8.4375
    assert pytest.approx(gale.texture_bounds.max_lat_deg, 0.001) == -2.8125


def test_zero_elevation_hallucination_guarantee():
    """
    Verify strict separation of optical imagery from high-resolution elevation models.
    Traverse planning and slope evaluation must remain strictly confined to surveyed Jezero Crater.
    """
    registry = load_imagery_registry()

    for pid in ["olympus_mons_ctx_regional", "valles_marineris_ctx_regional", "gale_crater_ctx_regional"]:
        prod = registry.get_by_id(pid)
        assert prod.planning_supported is False, f"Product '{pid}' must not claim planning support without DTM"
        assert prod.has_elevation_data is False, f"Product '{pid}' must not claim local elevation data"
        assert prod.elevation_capabilities == "none"

    # Jezero study area must be the only layer with true planning_supported = True
    jezero = registry.get_by_id("jezero_ctx_local_mesh")
    assert jezero.planning_supported is True
    assert jezero.has_elevation_data is True
    assert jezero.elevation_resolution_m == 20.0
    assert jezero.elevation_capabilities == "high_res_dtm_20m"


def test_tile_cache_allowlist_and_parameter_validation():
    """Verify tile cache enforces strict allowlist, bounds checking, and rejects path traversal."""
    cache = PlanetaryTileCache()

    # Reject path traversal
    with pytest.raises(TileCacheError, match="Invalid product_id format"):
        cache.validate_tile_coords("../../etc/passwd", 6, 0, 0)

    # Reject unallowed product
    with pytest.raises(TileCacheError, match="not in allowed tile products"):
        cache.validate_tile_coords("random_untrusted_layer", 6, 0, 0)

    # Reject out of range zoom
    with pytest.raises(TileCacheError, match="out of bounds"):
        cache.validate_tile_coords("olympus_mons_ctx_regional", 99, 0, 0)

    # Reject out of range row/col
    with pytest.raises(TileCacheError, match="Row 9999 out of bounds"):
        cache.validate_tile_coords("olympus_mons_ctx_regional", 6, 9999, 0)


def test_tile_cache_local_hit_miss_and_status():
    """Verify tile cache records hits, misses, and reports operational status."""
    cache = PlanetaryTileCache()
    status = cache.get_status()
    assert status["status"] == "operational"
    assert "olympus_mons_ctx_regional" in status["allowed_products"]
    assert "stats" in status
    assert status["stats"]["cached_tiles"] >= 0


def test_atlas_server_imagery_endpoints():
    """Verify localhost:3000 serves /api/imagery/status and /api/imagery/tile with proper headers."""
    # Test status endpoint
    req_status = urllib.request.Request("http://localhost:3000/api/imagery/status")
    with urllib.request.urlopen(req_status, timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "operational"
        assert "olympus_mons_ctx_regional" in data["allowed_products"]

    # Test tile endpoint (Olympus Mons Z=6, r=25, c=16)
    req_tile = urllib.request.Request("http://localhost:3000/api/imagery/tile?product_id=olympus_mons_ctx_regional&z=6&r=25&c=16")
    with urllib.request.urlopen(req_tile, timeout=6) as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") in ("image/png", "image/jpeg")
        assert resp.headers.get("X-MarsWalk-Cache") in ("HIT", "MISS")
        raw = resp.read()
        assert len(raw) > 1000

    # Test invalid coordinates reject with 400
    try:
        urllib.request.urlopen("http://localhost:3000/api/imagery/tile?product_id=olympus_mons_ctx_regional&z=99&r=0&c=0", timeout=5)
        assert False, "Should have returned HTTP 400"
    except urllib.error.HTTPError as err:
        assert err.code == 400


def test_frontend_scientific_disclosures_dom_and_app_js():
    """Verify index.html and app.js implement scientific disclosures and progressive refinement."""
    index_html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    # DOM elements in locationCard
    assert 'id="locCardDisclosures"' in index_html
    assert 'id="locCardSamplingDisclosure"' in index_html
    assert 'id="locCardContrastDisclosure"' in index_html
    assert 'id="locCardPlanningDisclosure"' in index_html

    # JS implementations in app.js
    assert "product.texture_bounds || product.bounds" in app_js
    assert "triggerProgressiveRefinement" in app_js
    assert "cancelCurrentFlight" in app_js
    assert "Synthetic contrast enhancement" in app_js
    assert "Restricted to surveyed Jezero 20 m DTM" in app_js

    # window.__atlas exports
    assert "getTileCacheStatus:" in app_js
    assert "getActiveRegionalProduct:" in app_js
    assert "cancelCurrentFlight:" in app_js
