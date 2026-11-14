"""
Milestone 9D Automated Validation and Regression Tests
Validates Orbit Experience Redesign & High-Fidelity Jezero Surface Exploration:
1. Georeferenced NASA CTX orthomosaic texture integrity and dimensions.
2. Idle Orbit iconic landmark catalog presence.
3. Navigation state machine contracts in app.js, index.html, and styles.css.
4. Screen-aligned Jezero waypoint labels and texture switching support.
"""

from pathlib import Path
import json
import pytest
from PIL import Image

def test_jezero_ctx_orthomosaic_texture_integrity():
    asset_paths = [
        Path("web/assets/jezero_ctx_orthomosaic.jpg"),
        Path("web/public/assets/jezero_ctx_orthomosaic.jpg"),
    ]

    for p in asset_paths:
        assert p.exists(), f"Missing authentic CTX orthomosaic texture at {p}"
        size_bytes = p.stat().st_size
        assert 50_000 <= size_bytes <= 10_000_000, f"Texture file size {size_bytes} out of expected range"

        with Image.open(p) as img:
            assert img.size == (1024, 1024), f"Texture dimensions {img.size} != (1024, 1024)"
            assert img.mode in ("RGB", "L"), f"Unexpected texture mode {img.mode}"


def test_idle_iconic_landmarks_in_catalog():
    catalog_path = Path("web/data/mars_places.json")
    assert catalog_path.exists(), "Missing mars_places.json"

    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    places_by_id = {p["id"]: p for p in data["places"]}

    iconic_ids = [
        "iau_4453",            # Olympus Mons
        "iau_6288",            # Valles Marineris
        "iau_2432",            # Hellas Planitia
        "iau_2071",            # Gale Crater (Curiosity)
        "iau_14300",           # Jezero Crater
        "landing_perseverance", # Perseverance Landing Site
        "iau_1783",            # Elysium Mons
        "iau_371",             # Argyre Planitia
    ]

    for iid in iconic_ids:
        assert iid in places_by_id, f"Iconic landmark {iid} missing from place catalog"
        p = places_by_id[iid]
        assert len(p["name"]) > 0
        assert -90.0 <= p["lat_deg"] <= 90.0
        assert -180.0 <= p["lon_deg"] <= 180.0


def test_index_html_has_milestone_9d_elements():
    html_path = Path("web/index.html")
    assert html_path.exists(), "Missing web/index.html"
    content = html_path.read_text(encoding="utf-8")

    assert "btnToggleRotation" in content, "Missing #btnToggleRotation button in index.html"
    assert "rotationBtnText" in content, "Missing #rotationBtnText span in index.html"
    assert "jezeroLabelsOverlay" in content, "Missing #jezeroLabelsOverlay container in index.html"
    assert "terrainTexturePills" in content, "Missing #terrainTexturePills in index.html"
    assert 'data-texture="ctx"' in content, "Missing NASA CTX option in index.html"
    assert 'data-texture="slope"' in content, "Missing slope hazard option in index.html"


def test_styles_css_has_milestone_9d_rules():
    css_path = Path("web/styles.css")
    assert css_path.exists(), "Missing web/styles.css"
    content = css_path.read_text(encoding="utf-8")

    assert ".rotation-dot" in content, "Missing .rotation-dot CSS in styles.css"
    assert "#btnToggleRotation" in content, "Missing #btnToggleRotation CSS in styles.css"
    assert ".jezero-waypoint-label" in content, "Missing .jezero-waypoint-label CSS in styles.css"
    assert ".wp-label-pin" in content, "Missing .wp-label-pin CSS in styles.css"


def test_app_js_has_navigation_state_machine():
    js_path = Path("web/app.js")
    assert js_path.exists(), "Missing web/app.js"
    content = js_path.read_text(encoding="utf-8")

    assert "navigationState" in content, "Missing navigationState variable in app.js"
    assert "autoRotationEnabled" in content, "Missing autoRotationEnabled variable in app.js"
    assert "IDLE_ICONIC_LANDMARKS" in content, "Missing IDLE_ICONIC_LANDMARKS set in app.js"
    assert "setNavigationState" in content, "Missing setNavigationState function in app.js"
    assert "initJezeroLabels" in content, "Missing initJezeroLabels function in app.js"
    assert "updateJezeroLabels" in content, "Missing updateJezeroLabels function in app.js"
    assert "assets/jezero_ctx_orthomosaic.jpg" in content, "Missing orthomosaic texture reference in app.js"
