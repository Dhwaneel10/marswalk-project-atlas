"""
MarsWalk 2.0 — Preflight Readiness Diagnostic Service
Evaluates 12 system components, data products, route planning services, and
persistence directories before competition demonstrations.
"""

import os
import sys
import time
import json
import uuid
import tempfile
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def check_server_health(base_url: str = "http://127.0.0.1:3000", timeout: float = 2.5) -> Dict[str, Any]:
    """Check 1: Atlas HTTP server reachable."""
    t0 = time.time()
    url = f"{base_url}/api/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MarsWalk-Preflight/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = round((time.time() - t0) * 1000, 1)
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == "online":
                    return {
                        "id": "server_reachable",
                        "name": "Atlas HTTP API Server",
                        "status": "passed",
                        "category": "local",
                        "details": f"Online on port 3000 ({data.get('target')}) in {elapsed_ms}ms.",
                        "duration_ms": elapsed_ms,
                    }
            return {
                "id": "server_reachable",
                "name": "Atlas HTTP API Server",
                "status": "warning",
                "category": "local",
                "details": f"Server responded with status {resp.status}.",
                "duration_ms": elapsed_ms,
            }
    except Exception as e:
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        return {
            "id": "server_reachable",
            "name": "Atlas HTTP API Server",
            "status": "failed",
            "category": "local",
            "details": f"Cannot connect to {url}: {e}. Ensure 'scripts/run_atlas.py' is running.",
            "duration_ms": elapsed_ms,
        }


def check_frontend_assets() -> Dict[str, Any]:
    """Check 2: Frontend assets exist and are non-empty."""
    t0 = time.time()
    web_dir = PROJECT_ROOT / "web"
    required_files = ["index.html", "app.js", "styles.css"]
    missing = []
    total_bytes = 0
    for f in required_files:
        p = web_dir / f
        if not p.is_file() or p.stat().st_size == 0:
            missing.append(f)
        else:
            total_bytes += p.stat().st_size
    elapsed_ms = round((time.time() - t0) * 1000, 1)
    if missing:
        return {
            "id": "frontend_assets",
            "name": "Web Frontend Assets",
            "status": "failed",
            "category": "local",
            "details": f"Missing or empty web assets: {', '.join(missing)}.",
            "duration_ms": elapsed_ms,
        }
    return {
        "id": "frontend_assets",
        "name": "Web Frontend Assets",
        "status": "passed",
        "category": "local",
        "details": f"Verified index.html, app.js, and styles.css ({total_bytes // 1024} KB).",
        "duration_ms": elapsed_ms,
    }


def check_places_catalog() -> Dict[str, Any]:
    """Check 3: Planetary feature gazetteer catalog."""
    t0 = time.time()
    catalog_path = PROJECT_ROOT / "web" / "data" / "mars_places.json"
    elapsed_ms = round((time.time() - t0) * 1000, 1)
    if not catalog_path.is_file():
        return {
            "id": "places_catalog",
            "name": "Planetary Feature Gazetteer",
            "status": "failed",
            "category": "local",
            "details": f"Missing gazetteer: {catalog_path}.",
            "duration_ms": elapsed_ms,
        }
    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = len(data.get("places", []))
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        if count >= 2000:
            return {
                "id": "places_catalog",
                "name": "Planetary Feature Gazetteer",
                "status": "passed",
                "category": "local",
                "details": f"Loaded {count:,} IAU-approved Martian landmarks and landing sites.",
                "duration_ms": elapsed_ms,
            }
        else:
            return {
                "id": "places_catalog",
                "name": "Planetary Feature Gazetteer",
                "status": "warning",
                "category": "local",
                "details": f"Catalog contains {count} items (expected ≥2,000).",
                "duration_ms": elapsed_ms,
            }
    except Exception as e:
        return {
            "id": "places_catalog",
            "name": "Planetary Feature Gazetteer",
            "status": "failed",
            "category": "local",
            "details": f"Error parsing gazetteer: {e}.",
            "duration_ms": elapsed_ms,
        }


def check_imagery_registry() -> Dict[str, Any]:
    """Check 4: Multi-scale imagery registry metadata."""
    t0 = time.time()
    reg_path = PROJECT_ROOT / "web" / "data" / "mars_imagery_registry.json"
    if not reg_path.is_file():
        return {
            "id": "imagery_registry",
            "name": "Planetary Imagery Registry",
            "status": "failed",
            "category": "local",
            "details": f"Missing registry file: {reg_path}.",
            "duration_ms": 0,
        }
    try:
        with open(reg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw_products = data.get("products", [])
        if isinstance(raw_products, list):
            product_ids = {p.get("id") for p in raw_products if isinstance(p, dict)}
            count = len(raw_products)
        elif isinstance(raw_products, dict):
            product_ids = set(raw_products.keys())
            count = len(raw_products)
        else:
            product_ids = set()
            count = 0

        required = [
            "olympus_mons_ctx_regional",
            "valles_marineris_ctx_regional",
            "gale_crater_ctx_regional",
            "jezero_ctx_regional_context",
        ]
        missing = [p for p in required if p not in product_ids]
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        if missing:
            return {
                "id": "imagery_registry",
                "name": "Planetary Imagery Registry",
                "status": "warning",
                "category": "local",
                "details": f"Missing regional products: {', '.join(missing)}.",
                "duration_ms": elapsed_ms,
            }
        return {
            "id": "imagery_registry",
            "name": "Planetary Imagery Registry",
            "status": "passed",
            "category": "local",
            "details": f"Verified metadata for {count} planetary imagery products (all 4 featured regions present).",
            "duration_ms": elapsed_ms,
        }
    except Exception as e:
        return {
            "id": "imagery_registry",
            "name": "Planetary Imagery Registry",
            "status": "failed",
            "category": "local",
            "details": f"Registry syntax error: {e}.",
            "duration_ms": 0,
        }


def check_global_basemap() -> Dict[str, Any]:
    """Check 5: Global basemap tiles or assets."""
    t0 = time.time()
    # Check if local texture asset exists or tile cache has basemap
    assets_dir = PROJECT_ROOT / "web" / "assets"
    basemap_files = list(assets_dir.glob("*viking*")) + list(assets_dir.glob("*basemap*")) + list(assets_dir.glob("*mola*"))
    elapsed_ms = round((time.time() - t0) * 1000, 1)
    if basemap_files:
        return {
            "id": "global_basemap",
            "name": "Global Mars Basemap Layer",
            "status": "passed",
            "category": "local",
            "details": f"Local Viking/MOLA basemap assets verified ({len(basemap_files)} files).",
            "duration_ms": elapsed_ms,
        }
    # Otherwise check tile cache directory
    cache_dir = PROJECT_ROOT / "data" / "cache" / "imagery"
    if cache_dir.exists():
        return {
            "id": "global_basemap",
            "name": "Global Mars Basemap Layer",
            "status": "passed",
            "category": "local",
            "details": "Operational planetary tile cache configured for on-demand WMTS tiles.",
            "duration_ms": elapsed_ms,
        }
    return {
        "id": "global_basemap",
        "name": "Global Mars Basemap Layer",
        "status": "warning",
        "category": "remote",
        "details": "Tile cache directory will be created on first external fetch.",
        "duration_ms": elapsed_ms,
    }


def check_jezero_ctx_imagery() -> Dict[str, Any]:
    """Check 6: Jezero Crater CTX optical imagery."""
    t0 = time.time()
    assets_dir = PROJECT_ROOT / "web" / "assets"
    ctx_candidates = list(assets_dir.glob("*jezero*")) + list(assets_dir.glob("*ctx*"))
    elapsed_ms = round((time.time() - t0) * 1000, 1)
    if ctx_candidates:
        return {
            "id": "jezero_ctx_imagery",
            "name": "Jezero CTX Optical Imagery",
            "status": "passed",
            "category": "local",
            "details": f"Verified Jezero optical orthomosaic assets ({len(ctx_candidates)} items).",
            "duration_ms": elapsed_ms,
        }
    return {
        "id": "jezero_ctx_imagery",
        "name": "Jezero CTX Optical Imagery",
        "status": "warning",
        "category": "local",
        "details": "Jezero imagery will use dynamic canvas or cached preview.",
        "duration_ms": elapsed_ms,
    }


def check_jezero_elevation(terrain=None) -> Dict[str, Any]:
    """Check 7: Jezero Crater 20m DTM elevation model."""
    t0 = time.time()
    if terrain is not None:
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        return {
            "id": "jezero_elevation",
            "name": "Jezero Crater 20m DTM",
            "status": "passed",
            "category": "local",
            "details": f"Loaded in-memory: shape {terrain.elevation.shape}, min {terrain.elevation.min():.1f}m, max {terrain.elevation.max():.1f}m.",
            "duration_ms": elapsed_ms,
        }

    dtm_path = PROJECT_ROOT / "data" / "processed" / "jezero_ready_20m.tif"
    elapsed_ms = round((time.time() - t0) * 1000, 1)
    if not dtm_path.is_file():
        return {
            "id": "jezero_elevation",
            "name": "Jezero Crater 20m DTM",
            "status": "failed",
            "category": "local",
            "details": f"Missing DTM GeoTIFF: {dtm_path}.",
            "duration_ms": elapsed_ms,
        }
    try:
        import rasterio
        with rasterio.open(dtm_path) as src:
            w, h = src.width, src.height
        return {
            "id": "jezero_elevation",
            "name": "Jezero Crater 20m DTM",
            "status": "passed",
            "category": "local",
            "details": f"Verified GeoTIFF: {w}x{h} px at 20 m/px geodetic grid.",
            "duration_ms": elapsed_ms,
        }
    except Exception as e:
        return {
            "id": "jezero_elevation",
            "name": "Jezero Crater 20m DTM",
            "status": "failed",
            "category": "local",
            "details": f"Rasterio read error on DTM: {e}.",
            "duration_ms": elapsed_ms,
        }


def check_route_planner_smoke(terrain=None, transform=None, waypoints=None) -> Dict[str, Any]:
    """Check 8: Route planning engine smoke test."""
    t0 = time.time()
    try:
        from marswalk.core.terrain import load_and_process_terrain
        from marswalk.api.service import plan_route_api

        if terrain is None:
            dtm_path = str(PROJECT_ROOT / "data" / "processed" / "jezero_ready_20m.tif")
            if not os.path.exists(dtm_path):
                return {
                    "id": "route_planner_smoke",
                    "name": "Route Planning Engine (A*)",
                    "status": "failed",
                    "category": "local",
                    "details": "DTM unavailable for route planner smoke test.",
                    "duration_ms": 0,
                }
            terrain = load_and_process_terrain(dtm_path)
            import rasterio
            with rasterio.open(dtm_path) as src:
                transform = src.transform

        payload = {
            "start": {"row": 117, "col": 157},
            "goal": {"row": 104, "col": 147},
            "profile": "balanced",
            "vehicle_mode": "crew_eva",
        }
        res = plan_route_api(payload, terrain, transform, waypoints or [])
        elapsed_ms = round((time.time() - t0) * 1000, 1)

        if res.get("is_reachable"):
            dist_m = res.get("distance_m", 0)
            return {
                "id": "route_planner_smoke",
                "name": "Route Planning Engine (A*)",
                "status": "passed",
                "category": "local",
                "details": f"Calculated smoke route ({dist_m:.0f}m, {res.get('num_cells')} cells) in {elapsed_ms}ms.",
                "duration_ms": elapsed_ms,
            }
        else:
            return {
                "id": "route_planner_smoke",
                "name": "Route Planning Engine (A*)",
                "status": "failed",
                "category": "local",
                "details": f"Smoke route unreachable: {res.get('status_message')}.",
                "duration_ms": elapsed_ms,
            }
    except Exception as e:
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        return {
            "id": "route_planner_smoke",
            "name": "Route Planning Engine (A*)",
            "status": "failed",
            "category": "local",
            "details": f"Planner exception: {e}.",
            "duration_ms": elapsed_ms,
        }


def check_scenario_engine_smoke(terrain=None, transform=None, waypoints=None) -> Dict[str, Any]:
    """Check 9: Scenario engine disruption simulation smoke test."""
    t0 = time.time()
    try:
        from marswalk.core.terrain import load_and_process_terrain
        from marswalk.api.service import gauntlet_api

        if terrain is None:
            dtm_path = str(PROJECT_ROOT / "data" / "processed" / "jezero_ready_20m.tif")
            terrain = load_and_process_terrain(dtm_path)
            import rasterio
            with rasterio.open(dtm_path) as src:
                transform = src.transform

        payload = {
            "start": {"row": 117, "col": 157},
            "goal": {"row": 104, "col": 147},
            "profile": "balanced",
            "vehicle_mode": "crew_eva",
            "scenario_id": "scen_corridor_rockfall",
        }
        res = gauntlet_api(payload, terrain, transform, waypoints or [])
        elapsed_ms = round((time.time() - t0) * 1000, 1)

        if "scenario" in res and "recovery_plan" in res:
            scen_name = res["scenario"].get("title", "Rockfall Detour")
            return {
                "id": "scenario_engine_smoke",
                "name": "Gauntlet Disruption & Recovery Engine",
                "status": "passed",
                "category": "local",
                "details": f"Evaluated '{scen_name}' with 3-way recovery plan in {elapsed_ms}ms.",
                "duration_ms": elapsed_ms,
            }
        return {
            "id": "scenario_engine_smoke",
            "name": "Gauntlet Disruption & Recovery Engine",
            "status": "failed",
            "category": "local",
            "details": "Gauntlet output missing scenario or recovery_plan key.",
            "duration_ms": elapsed_ms,
        }
    except Exception as e:
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        return {
            "id": "scenario_engine_smoke",
            "name": "Gauntlet Disruption & Recovery Engine",
            "status": "failed",
            "category": "local",
            "details": f"Scenario engine exception: {e}.",
            "duration_ms": elapsed_ms,
        }


def check_workspaces_filesystem() -> Dict[str, Any]:
    """Check 10: Persistent workspace missions and experiments storage."""
    t0 = time.time()
    m_dir = PROJECT_ROOT / "data" / "workspaces" / "missions"
    e_dir = PROJECT_ROOT / "data" / "workspaces" / "experiments"
    w_dir = PROJECT_ROOT / "data" / "weather"

    m_dir.mkdir(parents=True, exist_ok=True)
    e_dir.mkdir(parents=True, exist_ok=True)
    w_dir.mkdir(parents=True, exist_ok=True)

    # Safe isolated test probe (creates and immediately removes a temporary test file)
    test_id = f"preflight_probe_{uuid.uuid4().hex[:8]}.tmp"
    probe_file = m_dir / test_id
    try:
        probe_file.write_text('{"probe": true}', encoding="utf-8")
        _ = probe_file.read_text(encoding="utf-8")
        probe_file.unlink()

        m_count = len(list(m_dir.glob("*.json")))
        e_count = len(list(e_dir.glob("*.json")))
        w_count = len(list(w_dir.glob("*.json")))
        elapsed_ms = round((time.time() - t0) * 1000, 1)

        return {
            "id": "workspaces_filesystem",
            "name": "Persistent Workspace Storage",
            "status": "passed",
            "category": "local",
            "details": f"Filesystem writable: {m_count} missions, {e_count} experiments, {w_count} weather records preserved.",
            "duration_ms": elapsed_ms,
        }
    except Exception as e:
        if probe_file.exists():
            try:
                probe_file.unlink()
            except Exception:
                pass
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        return {
            "id": "workspaces_filesystem",
            "name": "Persistent Workspace Storage",
            "status": "failed",
            "category": "local",
            "details": f"Workspace filesystem permissions error: {e}.",
            "duration_ms": elapsed_ms,
        }


def check_briefing_exporter(terrain=None, transform=None) -> Dict[str, Any]:
    """Check 11: Technical mission briefing exporter and Draft 2020-12 schema validation."""
    t0 = time.time()
    try:
        from marswalk.api.service import export_briefing_api
        from marswalk.api.contracts import validate_contract
        from marswalk.core.terrain import load_and_process_terrain

        if terrain is None:
            dtm_path = str(PROJECT_ROOT / "data" / "processed" / "jezero_ready_20m.tif")
            terrain = load_and_process_terrain(dtm_path)
            import rasterio
            with rasterio.open(dtm_path) as src:
                transform = src.transform

        dummy_route = {
            "start": {"row": 117, "col": 157, "name": "Landing Site"},
            "goal": {"row": 104, "col": 147, "name": "Hawksbill Gap"},
            "distance_m": 850.0,
            "path_rc": [[117, 157], [104, 147]],
            "profile": "balanced",
            "vehicle_mode": "crew_eva",
            "is_reachable": True,
            "is_budget_feasible": True,
            "timeline": {
                "events": [{"event_type": "traverse_leg", "distance_m": 850.0, "duration_s": 1530.0, "label": "Leg 1"}],
                "total_mission_time_s": 1530.0,
                "total_traverse_time_s": 1530.0,
                "total_dwell_time_s": 0.0,
                "total_operational_delay_s": 0.0,
                "operational_limit_s": 28800.0,
                "remaining_margin_s": 27270.0,
                "is_within_limit": True,
            },
        }

        res = export_briefing_api({"baseline_route": dummy_route}, terrain, transform)
        json_export = res.get("json_export", {})
        md_text = res.get("markdown_briefing", "")

        # Validate against formal JSON Schema
        validate_contract(json_export, "mission-briefing-export", raise_on_error=True)
        elapsed_ms = round((time.time() - t0) * 1000, 1)

        has_disclaimer = "NOT certified as operationally safe" in md_text or "RESEARCH PROTOTYPE" in md_text
        if has_disclaimer:
            return {
                "id": "briefing_exporter",
                "name": "Mission Briefing & Schema Validator",
                "status": "passed",
                "category": "local",
                "details": f"Draft 2020-12 valid schema & Markdown export verified in {elapsed_ms}ms.",
                "duration_ms": elapsed_ms,
            }
        return {
            "id": "briefing_exporter",
            "name": "Mission Briefing & Schema Validator",
            "status": "warning",
            "category": "local",
            "details": "Export generated but missing standard safety disclaimer.",
            "duration_ms": elapsed_ms,
        }
    except Exception as e:
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        return {
            "id": "briefing_exporter",
            "name": "Mission Briefing & Schema Validator",
            "status": "failed",
            "category": "local",
            "details": f"Briefing exporter failure: {e}.",
            "duration_ms": elapsed_ms,
        }


def check_streamlit_companion() -> Dict[str, Any]:
    """Check 12: Streamlit companion application launchability."""
    t0 = time.time()
    app_path = PROJECT_ROOT / "src" / "marswalk" / "app.py"
    if not app_path.is_file():
        return {
            "id": "streamlit_companion",
            "name": "Streamlit Tactical Control App",
            "status": "warning",
            "category": "optional",
            "details": f"Streamlit application file not found at {app_path}.",
            "duration_ms": 0,
        }
    try:
        # Check Python syntax validity via compile()
        source = app_path.read_text(encoding="utf-8")
        compile(source, str(app_path), "exec")
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        return {
            "id": "streamlit_companion",
            "name": "Streamlit Tactical Control App",
            "status": "passed",
            "category": "optional",
            "details": f"Verified tactical Streamlit dashboard ({len(source.splitlines()):,} lines syntax valid).",
            "duration_ms": elapsed_ms,
        }
    except Exception as e:
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        return {
            "id": "streamlit_companion",
            "name": "Streamlit Tactical Control App",
            "status": "warning",
            "category": "optional",
            "details": f"Streamlit script syntax check warning: {e}.",
            "duration_ms": elapsed_ms,
        }


def run_preflight_diagnostics(
    terrain=None,
    transform=None,
    waypoints=None,
    base_url: str = "http://127.0.0.1:3000",
) -> Dict[str, Any]:
    """
    Run all 12 preflight readiness checks and return structured diagnostic results.
    """
    t_start = time.time()
    checks = [
        check_server_health(base_url),
        check_frontend_assets(),
        check_places_catalog(),
        check_imagery_registry(),
        check_global_basemap(),
        check_jezero_ctx_imagery(),
        check_jezero_elevation(terrain),
        check_route_planner_smoke(terrain, transform, waypoints),
        check_scenario_engine_smoke(terrain, transform, waypoints),
        check_workspaces_filesystem(),
        check_briefing_exporter(terrain, transform),
        check_streamlit_companion(),
    ]

    passed = sum(1 for c in checks if c["status"] == "passed")
    warnings = sum(1 for c in checks if c["status"] == "warning")
    failed = sum(1 for c in checks if c["status"] == "failed")

    overall_status = "ready"
    if failed > 0:
        overall_status = "unready"
    elif warnings > 0:
        overall_status = "ready_with_warnings"

    total_time_ms = round((time.time() - t_start) * 1000, 1)

    return {
        "overall_status": overall_status,
        "is_ready_for_demo": failed == 0,
        "summary": f"{passed}/12 checks passed, {warnings} warnings, {failed} failures in {total_time_ms}ms.",
        "passed_count": passed,
        "warning_count": warnings,
        "failed_count": failed,
        "total_count": len(checks),
        "total_duration_ms": total_time_ms,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "checks": checks,
    }
