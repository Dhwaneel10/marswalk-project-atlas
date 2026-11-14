"""
MarsWalk 2.0 - Milestone 9F Verification Tests
Validates navigation reliability, data integrity, optical/elevation separation,
restrained minimalist UI contracts, and elimination of mode traps.
"""

import os
import json
import pytest
from pathlib import Path
from marswalk.data.imagery_registry import load_imagery_registry

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_registry_resolution_separation_and_provenance():
    """Verify registry strictly differentiates optical source, texture sampling, and DTM resolution."""
    reg = load_imagery_registry()
    jez = reg.get_by_id("jezero_ctx_local_mesh")
    assert jez is not None, "jezero_ctx_local_mesh must exist in registry"
    
    # Elevation resolution is 20m/cell
    assert jez.elevation_resolution_m == 20.0
    assert jez.has_elevation_data is True
    assert jez.planning_supported is True
    
    # Optical resolution metadata
    assert jez.optical_source_resolution_m == 6.0
    assert jez.texture_sampling_resolution_m == 4.88
    assert "20 m/cell" in jez.description or "20 m ground spacing" in jez.description


def test_frontend_html_and_css_milestone_9f_clean_ui():
    """Verify index.html and styles.css implement clean, restrained UI contracts."""
    html_path = PROJECT_ROOT / "web" / "index.html"
    css_path = PROJECT_ROOT / "web" / "styles.css"
    
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    # Inspector panel and waypoint search must start hidden in orbit view
    assert 'id="inspectorPanel" class="hud-inspector hidden"' in html
    assert 'id="waypointSelect" class="hud-select hidden"' in html
    
    # Theatrical / goofy jargon replaced with professional scientific wording
    assert "Loading planetary atlas..." in html
    assert "INITIALIZING IAU MARS 2000 GEODESIC ENGINE..." not in html
    assert "Mission Stress Testing" in html
    assert "Simulate Route Disruption" in html
    assert "THE GAUNTLET" not in html
    assert "RUN GAUNTLET STRESS TEST" not in html
    assert "Terrain Slope" in html
    assert "Slope Hazards" not in html
    
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()
    
    assert ".location-card.hidden" in css
    assert "display: none !important" in css
    assert "max-width: calc(100vw - 40px)" in css


def test_app_js_telemetry_and_mode_trap_contracts():
    """Verify app.js contracts for telemetry accuracy, hemisphere notation, and mode trap elimination."""
    app_js_path = PROJECT_ROOT / "web" / "app.js"
    with open(app_js_path, "r", encoding="utf-8") as f:
        js = f.read()
    
    # Mode trap prevention in selectAndFocusPlace
    assert "if (currentViewMode === 'jezero')" in js
    assert "marsGlobeGroup.visible = true" in js
    assert "jezeroSurfaceGroup.visible = false" in js
    
    # Telemetry logic: Viking MDIM resolution contract
    assert "Viking MDIM (${prod.nominal_resolution_m} m)" not in js
    assert "Viking MDIM (232 m/px)" in js
    assert "MRO CTX Regional" in js
    assert "20 m CTX DTM (Active)" in js
    
    # Directional hemisphere formatting in updateLiveTelemetry
    assert "const lonDir = lon >= 0 ? 'E' : 'W'" in js
    assert "const latDir = lat >= 0 ? 'N' : 'S'" in js


def test_evidence_screenshots_exist_and_non_empty():
    """Verify that all Milestone 9F automated visual evidence screenshots were captured and valid."""
    expected_shots = [
        "m9f_01_global_orbit_restrained.png",
        "m9f_02_olympus_mons_navigation.png",
        "m9f_03_gale_crater_navigation.png",
        "m9f_04_jezero_workstation_planning.png",
        "m9f_05_jezero_stress_test_simulation.png",
        "m9f_06_elysium_honest_fallback.png",
    ]
    for shot in expected_shots:
        shot_path = PROJECT_ROOT / "outputs" / shot
        assert shot_path.is_file(), f"Expected evidence shot missing: {shot}"
        size_kb = shot_path.stat().st_size / 1024
        assert size_kb > 50, f"Screenshot {shot} suspiciously small: {size_kb:.1f} KB"
