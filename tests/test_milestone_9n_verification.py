"""
Milestone 9N Verification Tests.

Validates:
1. Waypoint visibility controls (All locations vs Mission locations only) and dynamic counting.
2. Endpoint clearing controls (Clear Start, Clear Destination), endpoint swap, and mission reset.
3. Reset mission confirmation modal with data-protection reassurance.
4. Upgraded regional imagery (authentic NASA Mars Trek CTX mosaic for Valles Marineris).
5. Four featured regional destinations and [GLOBAL MARS] return to orbit navigation.
"""

import json
from pathlib import Path
import pytest


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = WORKSPACE_ROOT / "web"
DOCS_DIR = WORKSPACE_ROOT / "docs"


def test_waypoint_visibility_dom_and_styling():
    """Verify index.html and styles.css provide explicit waypoint visibility controls."""
    index_html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    styles_css = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    # Visibility pills container
    assert 'id="waypointVisibilityPills"' in index_html
    assert 'id="btnVisAll"' in index_html
    assert 'id="btnVisMission"' in index_html
    assert 'id="countAllWaypoints"' in index_html

    # Backward compatibility with 9M checkbox
    assert 'id="chkShowAllWaypoints"' in index_html

    # Distinct CSS classes for waypoints
    assert ".is-start" in styles_css
    assert ".is-goal" in styles_css
    assert ".is-stop" in styles_css
    assert ".visibility-pills" in styles_css
    assert ".visibility-pill" in styles_css


def test_endpoint_manipulation_dom_controls():
    """Verify Clear Start, Clear Destination, Swap, and Reset Mission controls exist."""
    index_html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    styles_css = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    # Clear Start and Clear Goal buttons
    assert 'id="btnClearStart"' in index_html
    assert 'id="btnClearGoal"' in index_html
    assert 'id="btnSwapEndpoints"' in index_html

    # Reset Mission button and confirmation modal
    assert 'id="btnResetMission"' in index_html
    assert 'id="resetMissionModal"' in index_html
    assert 'id="btnCancelResetMission"' in index_html
    assert 'id="btnDismissResetMission"' in index_html
    assert 'id="btnConfirmResetMission"' in index_html

    # Data protection guarantee notice in reset modal
    assert "Data Protection Guarantee" in index_html or "data protection" in index_html.lower()

    # CSS styles
    assert ".btn-clear-endpoint" in styles_css
    assert ".btn-swap-endpoints" in styles_css
    assert ".btn-reset-action" in styles_css


def test_app_js_methods_and_visibility_architecture():
    """Verify app.js implements the required Milestone 9N API functions and state machine."""
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    # Waypoint visibility mode methods
    assert "setWaypointVisibilityMode" in app_js
    assert "waypointVisibilityMode" in app_js

    # Endpoint clearing methods
    assert "clearStart" in app_js
    assert "clearGoal" in app_js
    assert "swapEndpoints" in app_js
    assert "resetMission" in app_js
    assert "executeResetMission" in app_js
    assert "clearRouteTelemetry" in app_js
    assert "updateCalculateButtonState" in app_js

    # window.__atlas exports
    assert "clearStart:" in app_js
    assert "clearGoal:" in app_js
    assert "swapEndpoints:" in app_js
    assert "resetMission:" in app_js
    assert "setWaypointVisibilityMode:" in app_js
    assert "getWaypointVisibilityMode:" in app_js
    assert "getCustomStart:" in app_js
    assert "getCustomGoal:" in app_js


def test_valles_marineris_ctx_mosaic_asset():
    """Verify authentic NASA Mars Trek CTX mosaic asset exists and is valid JPEG."""
    preview_file = WEB_DIR / "assets" / "valles_marineris_ctx_preview.jpg"
    assert preview_file.exists(), "valles_marineris_ctx_preview.jpg must exist"
    size = preview_file.stat().st_size
    assert size > 15_000, f"Preview image size too small ({size} bytes); must be genuine CTX mosaic"

    # Verify JPEG magic bytes
    with open(preview_file, "rb") as f:
        magic = f.read(3)
        assert magic == b"\xff\xd8\xff", "File must have valid JPEG header"


def test_mars_imagery_registry_valles_marineris_ctx():
    """Verify registry properly configures genuine CTX product for Valles Marineris."""
    registry_file = WEB_DIR / "data" / "mars_imagery_registry.json"
    registry = json.loads(registry_file.read_text(encoding="utf-8"))

    products = {p["id"]: p for p in registry["products"]}
    assert "valles_marineris_ctx_regional" in products

    vm_prod = products["valles_marineris_ctx_regional"]
    assert vm_prod["layer_type"] == "regional_mosaic"
    assert vm_prod["nominal_resolution_m"] == 6.0
    assert "SE_Marineris_CTX_BlockAdj_dd" in vm_prod["source"] or "SE_Marineris_CTX_BlockAdj_dd" in vm_prod["wmts_capabilities_url"]
    assert vm_prod["local_asset_path"] == "assets/valles_marineris_ctx_preview.jpg"
    assert vm_prod["bounds"]["min_lon_deg"] == -78.0
    assert vm_prod["bounds"]["max_lon_deg"] == -40.0
    assert vm_prod["planning_supported"] is False


def test_four_featured_destinations_integrity():
    """Verify the four featured destinations have entries in catalog and appropriate imagery."""
    catalog_file = WEB_DIR / "data" / "mars_places.json"
    catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
    places = {p["id"]: p for p in catalog["places"]}

    # 4 Featured Destinations:
    # 1. Jezero Crater
    assert "iau_14300" in places or "landing_perseverance" in places
    # 2. Olympus Mons
    assert "iau_4453" in places
    # 3. Valles Marineris
    assert "iau_6288" in places
    # 4. Gale Crater
    assert "iau_2071" in places

    registry_file = WEB_DIR / "data" / "mars_imagery_registry.json"
    registry = json.loads(registry_file.read_text(encoding="utf-8"))
    reg_ids = {p["id"] for p in registry["products"]}

    assert "jezero_ctx_local_mesh" in reg_ids
    assert "olympus_mons_ctx_regional" in reg_ids
    assert "valles_marineris_ctx_regional" in reg_ids
    assert "gale_crater_ctx_regional" in reg_ids


def test_location_card_orbit_return_action():
    """Verify location card contains GLOBAL MARS orbit return button."""
    index_html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="btnLocOrbit"' in index_html
    assert "GLOBAL MARS" in index_html
    assert "btnLocOrbit" in app_js


def test_regional_imagery_audit_report_exists():
    """Verify comprehensive technical audit report for regional imagery exists."""
    audit_file = DOCS_DIR / "marswalk-regional-imagery-audit.md"
    assert audit_file.exists()
    content = audit_file.read_text(encoding="utf-8")
    assert "Jezero Crater" in content
    assert "Olympus Mons" in content
    assert "Valles Marineris" in content
    assert "Gale Crater" in content
    assert "SE_Marineris_CTX_BlockAdj_dd" in content
