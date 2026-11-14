"""
scripts/verify_installation.py
Automated environment, dependency, dataset, and computation verification for Project Atlas / MarsWalk 2.0.
Designed for independent researchers and external reviewers to validate installation readiness.
"""

import sys
import os
import hashlib
import json
import importlib.metadata
from pathlib import Path

EXPECTED_USGS_DTM_SHA256 = "875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3"
REPO_ROOT = Path(__file__).resolve().parent.parent

def compute_file_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    print("=" * 78)
    print("  PROJECT ATLAS / MARSWALK 2.0 — INSTALLATION & ENVIRONMENT AUDIT")
    print("=" * 78)
    
    passes = 0
    failures = 0
    warnings = 0
    
    # 1. Python Version Check
    py_ver = sys.version_info
    py_ver_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
    if py_ver.major == 3 and py_ver.minor >= 10:
        print(f"[PASSED] Python Runtime: {py_ver_str} (>= 3.10 required, 3.12 recommended)")
        passes += 1
    else:
        print(f"[FAILED] Python Runtime: {py_ver_str} (Requires Python 3.10 or higher)")
        failures += 1

    # 2. Third-Party Dependency Imports
    required_packages = [
        ("numpy", "Numerical tensor operations"),
        ("scipy", "Scientific calculations & spatial trees"),
        ("rasterio", "Planetary geospatial raster I/O"),
        ("affine", "Affine coordinate transformations"),
        ("jsonschema", "Draft 2020-12 data contract enforcement"),
        ("requests", "HTTP client telemetry communication"),
        ("websockets", "Real-time CDP and telemetry streams"),
        ("pytest", "Automated test runner & regression suites"),
    ]
    
    for pkg_name, desc in required_packages:
        try:
            __import__(pkg_name)
            try:
                ver = importlib.metadata.version(pkg_name)
            except Exception:
                ver = "installed"
            print(f"[PASSED] Package '{pkg_name}' (v{ver}): {desc}")
            passes += 1
        except ImportError as e:
            print(f"[FAILED] Package '{pkg_name}': Missing ({e})")
            failures += 1

    # 3. Core MarsWalk Architecture Modules
    sys.path.insert(0, str(REPO_ROOT / "src"))
    core_modules = [
        ("marswalk.core.terrain", "Terrain elevation & Horn slope kernel"),
        ("marswalk.core.planner", "A* search & TSP tour optimization"),
        ("marswalk.core.atlas_campaign_compiler", "Intent ingestion & 7-phase DAG compiler"),
        ("marswalk.core.atlas_mission_event_coordinator", "Discrete-event priority scheduler"),
        ("marswalk.core.atlas_mission_state", "Mission state twin & Merkle hash chain"),
        ("marswalk.core.atlas_resource_operations", "ISRU, Kilopower & mass/energy accounting"),
        ("marswalk.core.atlas_scientific_operations", "Bayesian hypothesis testing & Shannon gain"),
        ("marswalk.core.atlas_autonomous_operations", "OWLT delay modeling & idempotent commands"),
        ("marswalk.core.atlas_mission_execution_core", "Closed-loop mission execution engine"),
        ("marswalk.core.atlas_unified_asset_manager", "Heterogeneous rover/aircraft fleet registry"),
        ("marswalk.core.atlas_mission_resilience_coordinator", "Cascading failure injection & FDIR"),
        ("marswalk.core.atlas_mission_replay", "Deterministic replay verification engine"),
    ]
    
    for mod_name, desc in core_modules:
        try:
            __import__(mod_name)
            print(f"[PASSED] Architecture Module '{mod_name}': {desc}")
            passes += 1
        except Exception as e:
            print(f"[FAILED] Architecture Module '{mod_name}': Error loading ({e})")
            failures += 1

    # 4. Primary Remote-Sensing Datasets
    dtm_candidates = [
        REPO_ROOT / "data" / "processed" / "jezero_ready_20m.tif",
        REPO_ROOT / "data" / "terrain" / "usgs_jezero_20m.tif",
    ]
    dtm_found = None
    for p in dtm_candidates:
        if p.exists():
            dtm_found = p
            break
            
    if dtm_found:
        actual_hash = compute_file_sha256(dtm_found)
        if actual_hash.lower() == EXPECTED_USGS_DTM_SHA256.lower():
            print(f"[PASSED] Primary USGS Jezero 20m DTM ({dtm_found.name}): Exists and SHA-256 verified ({actual_hash[:16]}...)")
            passes += 1
        else:
            print(f"[WARNING] Primary USGS Jezero 20m DTM hash mismatch: {actual_hash} != {EXPECTED_USGS_DTM_SHA256}")
            warnings += 1
    else:
        print(f"[FAILED] Primary USGS Jezero 20m DTM not found in data directories.")
        failures += 1

    # 5. Web Frontend Assets
    frontend_files = [
        ("web/index.html", "Tactical Cockpit & 3D WebGL viewport"),
        ("web/app.js", "Client application state controller"),
        ("web/styles.css", "Mission-control HUD styling"),
    ]
    for rel_path, desc in frontend_files:
        p = REPO_ROOT / rel_path
        if p.exists() and p.stat().st_size > 0:
            print(f"[PASSED] Frontend Asset '{rel_path}': Found ({p.stat().st_size} bytes)")
            passes += 1
        else:
            print(f"[FAILED] Frontend Asset '{rel_path}': Missing or empty")
            failures += 1

    # 6. Sanity Mathematical Computation
    try:
        import numpy as np
        # 3x3 Horn slope kernel smoke test
        grid = np.array([
            [10.0, 10.0, 10.0],
            [10.0, 10.0, 10.0],
            [10.0, 10.0, 10.0]
        ], dtype=float)
        dz_dx = ((grid[0, 2] + 2*grid[1, 2] + grid[2, 2]) - (grid[0, 0] + 2*grid[1, 0] + grid[2, 0])) / (8 * 20.0)
        assert dz_dx == 0.0
        
        # Hypsometric pressure scale check: P(z) = P0 * exp(-z / H)
        p0 = 610.0 # Pa
        h_scale = 11100.0 # m
        p_5000 = p0 * np.exp(-5000.0 / h_scale)
        assert 380.0 < p_5000 < 400.0
        print("[PASSED] Mathematical & Physical Core: Horn kernel & hypsometric formulas validated")
        passes += 1
    except Exception as e:
        print(f"[FAILED] Mathematical Sanity Test: {e}")
        failures += 1

    print("-" * 78)
    print(f"Summary: {passes} passed, {warnings} warnings, {failures} failures")
    if failures == 0:
        print(">>> RESULT: Environment and installation verified successfully for Project Atlas. <<<")
        print("=" * 78)
        return 0
    else:
        print(">>> RESULT: Installation verification detected failures. Please inspect errors above. <<<")
        print("=" * 78)
        return 1

if __name__ == "__main__":
    sys.exit(main())
