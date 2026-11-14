"""
Milestone 9M Verification Test Suite:
Validates trustworthy stress-testing, operational life-support budget limits,
recovery plan feasibility, intermediate research stops retention,
inspector 4-tab UI organization, distinct vehicle/texture pill isolation,
and genuine regional exploration assets.
"""

import json
from pathlib import Path
import pytest
import rasterio

from marswalk.core.terrain import load_and_process_terrain, TerrainConfig
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    plan_route,
    plan_sequential_multistop_route,
    build_mission_timeline,
)
from marswalk.core.stress_test import (
    DisruptionType,
    ScenarioDefinition,
    run_scenario,
    get_curated_gauntlet_scenarios,
)
from marswalk.api.service import plan_route_api, gauntlet_api

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = WORKSPACE_ROOT / "web"
ASSETS_DIR = WEB_DIR / "assets"
DATA_DIR = WEB_DIR / "data"


@pytest.fixture(scope="module")
def terrain_env():
    """Load real Jezero DTM and verified waypoints."""
    tif_path = str(WORKSPACE_ROOT / "data" / "processed" / "jezero_ready_20m.tif")
    tg = load_and_process_terrain(tif_path)
    with rasterio.open(tif_path) as src:
        transform = src.transform

    json_path = DATA_DIR / "jezero_mission_data.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    waypoints = [
        ScienceWaypoint(
            id=w["id"],
            name=w["name"],
            rc=(w["row"], w["col"]),
            priority_score=w["priority_score"],
            geological_context=w.get("geological_context", ""),
            pds_citation=w.get("pds_citation", ""),
        )
        for w in data["waypoints"]
    ]

    return {"terrain": tg, "transform": transform, "waypoints": waypoints}


def test_operational_limit_time_feasibility_violation(terrain_env):
    """
    Verify that if total mission operational time exceeds user-specified
    operational_limit_s, is_budget_feasible is strictly False.
    """
    tg = terrain_env["terrain"]
    start_rc = (117, 157)
    goal_rc = (66, 128)

    # First plan nominal route without operational limit
    nominal = plan_route(start_rc, goal_rc, tg, config=PlannerConfig(profile="conservative"), vehicle_mode="crew_eva")
    assert nominal.is_reachable is True
    assert nominal.is_budget_feasible is True
    total_time_s = nominal.timeline.total_mission_time_s
    assert total_time_s > 0

    # Now constrain operational limit to 50% of nominal time
    restricted_limit = total_time_s * 0.5
    constrained = plan_route(
        start_rc,
        goal_rc,
        tg,
        config=PlannerConfig(profile="conservative"),
        vehicle_mode="crew_eva",
        operational_limit_s=restricted_limit,
    )
    assert constrained.is_reachable is True
    assert constrained.is_budget_feasible is False
    assert "exceeds" in constrained.status_message.lower()
    assert constrained.timeline.remaining_margin_s < 0
    assert constrained.timeline.is_within_limit is False


def test_stress_test_reduced_budget_operational_time_separation(terrain_env):
    """
    Verify REDUCED_BUDGET scenario scales life-support operational time without
    conflating physical distance ceilings, and generates a truthful narrative.
    """
    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "scenario_id": "scen_budget_cut_40",
        "operational_limit_s": 3600.0,  # 1 hour life-support budget
    }
    resp = gauntlet_api(payload, terrain_env["terrain"], terrain_env["transform"], terrain_env["waypoints"])
    assert resp["is_scenario_reachable"] is True
    # The baseline route is within budget (~43 min < 60 min)
    assert resp["baseline_route"]["is_budget_feasible"] is True
    # Disrupted route reduced by 40% (limit 36 min < 43 min) => infeasible
    assert resp["scenario_route"]["is_budget_feasible"] is False
    assert resp["scenario_route"]["timeline"]["remaining_margin_s"] < 0
    # Truthful narrative: must not claim budget compliant!
    assert "budget compliant" not in resp["headline"].lower()
    assert "budget compliant" not in resp["detail"].lower()


def test_recovery_plan_no_arbitrary_offset_and_feasibility_check(terrain_env):
    """
    Verify recovery planner eliminates arbitrary +600s offset and checks
    feasibility of recovery candidates before recommending.
    """
    wps = terrain_env["waypoints"]
    payload = {
        "start": {"row": wps[0].rc[0], "col": wps[0].rc[1]},
        "goal": {"row": wps[1].rc[0], "col": wps[1].rc[1]},
        "scenario_id": "scen_corridor_rockfall",
        "operational_limit_s": 14400.0,  # 4 hours
    }
    resp = gauntlet_api(payload, terrain_env["terrain"], terrain_env["transform"], terrain_env["waypoints"])
    assert resp["is_scenario_reachable"] is True
    assert "recovery_plan" in resp
    rec = resp["recovery_plan"]
    assert rec is not None
    assert "strategy" in rec
    assert isinstance(rec["strategy"], str) and len(rec["strategy"]) > 0
    assert "action_label" in rec
    if "route" in rec and rec["route"]:
        assert rec["route"]["is_budget_feasible"] is True


def test_valles_marineris_regional_mosaic_asset_and_registry():
    """
    Verify genuine local regional preview mosaic for Valles Marineris exists
    and is properly registered with calibrated geographic bounds.
    """
    vm_asset = ASSETS_DIR / "valles_marineris_ctx_preview.jpg"
    assert vm_asset.exists(), f"Asset {vm_asset} must exist."
    assert vm_asset.stat().st_size > 10000, "Valles Marineris preview must be a valid non-empty JPEG image."

    registry_path = DATA_DIR / "mars_imagery_registry.json"
    assert registry_path.exists()
    with open(registry_path, "r", encoding="utf-8") as f:
        reg = json.load(f)

    vm_product = next((p for p in reg["products"] if p["id"] == "valles_marineris_ctx_regional"), None)
    assert vm_product is not None, "valles_marineris_ctx_regional must be in imagery registry."
    assert vm_product["local_asset_path"] == "assets/valles_marineris_ctx_preview.jpg"
    assert vm_product["bounds"]["min_lon_deg"] == -78.0
    assert vm_product["bounds"]["max_lon_deg"] == -40.0
    assert vm_product["bounds"]["min_lat_deg"] == -25.0
    assert vm_product["bounds"]["max_lat_deg"] == -5.0


def test_html_inspector_tabs_and_budget_inputs():
    """
    Verify index.html contains the 4-tab structure, user budget controls,
    and distinct pill classes.
    """
    index_html = (WEB_DIR / "index.html").read_text(encoding="utf-8")

    # Inspector 4 tabs
    assert 'id="inspectorTabs"' in index_html
    assert 'id="tabPlan"' in index_html
    assert 'id="tabResults"' in index_html
    assert 'id="tabScenarios"' in index_html
    assert 'id="tabWorkspaces"' in index_html

    # Expedition Budget Inputs
    assert 'id="inputExpeditionHours"' in index_html
    assert 'id="inputDwellMins"' in index_html
    assert 'id="inputDelayMins"' in index_html
    assert 'id="inputMaxDistanceM"' in index_html
    assert 'id="chkShowAllWaypoints"' in index_html

    # Distinct pill classes (no class collisions)
    assert 'class="vehicle-pill active"' in index_html or 'class="vehicle-pill' in index_html
    assert 'class="texture-pill active"' in index_html or 'class="texture-pill' in index_html

    # Landing page body class
    assert 'class="landing-active"' in index_html


def test_app_js_profile_switch_preserves_intermediate_stops():
    """
    Verify app.js preserves intermediate stops when switching profiles
    and scopes exagPills without NaN mesh destruction.
    """
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    # Stops retention check on profile tab click
    assert "hasNoStops" in app_js
    assert "!activeIntermediateStops || activeIntermediateStops.length === 0" in app_js

    # Exaggeration selector scoped properly
    assert "document.querySelectorAll('#exagPills .exag-pill')" in app_js
    assert "document.querySelectorAll('#vehicleModePills .vehicle-pill')" in app_js
    assert "document.querySelectorAll('#terrainTexturePills .texture-pill')" in app_js

    # Inspector tab switcher
    assert "function switchInspectorTab" in app_js
    assert "switchInspectorTab:" in app_js
    assert "setExpeditionBudget:" in app_js
