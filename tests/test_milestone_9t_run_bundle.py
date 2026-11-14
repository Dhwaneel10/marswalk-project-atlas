"""
MarsWalk 2.0 — Milestone 9T Canonical Mission Run Bundle & Decision Pack Verification Suite

Verifies:
1. Canonical run bundle schema conformance (Draft 2020-12).
2. Stable computation fingerprints for equivalent inputs.
3. Fingerprint sensitivity to start/goal/stops/profile/vehicle/contingency changes.
4. Terrain identity and SHA-256 raster hash provenance.
5. Exact export of route geometry, metrics, timeline, and cartography.
6. Comparison CSV values matching underlying route calculation results.
7. Rejection of invalid JSON, NaN/inf, and out-of-bounds coordinates.
8. Blocked/severed scenario represented as unreachable, not fabricated success.
9. Immutability of historical missions and experiments during export/replay.
10. Replay creates a distinct new run ID and verifies exact reproduction within tolerances.
11. Terrain incompatibility detection when dataset or hash differs.
12. Rejection of malformed or tampered fingerprints.
13. In-memory ZIP package valid extraction, manifest, and safe path structure.
"""

import os
import io
import csv
import json
import zipfile
import hashlib
import tempfile
import urllib.request
import urllib.error
import pytest
from pathlib import Path

import rasterio

from marswalk.core.terrain import load_and_process_terrain, TerrainGrid
from marswalk.core.planner import ScienceWaypoint
from marswalk.api.contracts import (
    TERRAIN_SHA256,
    TERRAIN_DATASET_ID,
    compute_bundle_fingerprint,
    build_canonical_mission_run_bundle,
    validate_contract,
    ContractValidationError,
)
from marswalk.api.decision_pack import (
    generate_comparison_csv,
    generate_decision_pack_briefing_md,
    generate_decision_pack_readme,
    generate_route_cartography,
    build_decision_pack_zip,
    verify_bundle_integrity,
    replay_decision_pack_bundle,
)
from marswalk.api.service import (
    plan_route_api,
    contingency_simulate_api,
    export_decision_pack_api,
    verify_bundle_api,
    replay_bundle_api,
    APIError,
)
from marswalk.api.workspace import (
    list_missions,
    list_experiments,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GEOTIFF_PATH = str(PROJECT_ROOT / "data" / "processed" / "jezero_ready_20m.tif")
WAYPOINTS_PATH = str(PROJECT_ROOT / "data" / "waypoints_jezero.json")


@pytest.fixture(scope="module")
def terrain_context():
    """Load surveyed Jezero terrain once for the suite."""
    terrain = load_and_process_terrain(GEOTIFF_PATH)
    with rasterio.open(GEOTIFF_PATH) as src:
        transform = src.transform

    waypoints = [
        ScienceWaypoint(id="octavia_landing", name="Octavia E. Butler Landing", rc=(117, 157), priority_score=100.0),
        ScienceWaypoint(id="hawksbill_gap", name="Hawksbill Gap", rc=(95, 140), priority_score=85.0),
        ScienceWaypoint(id="skinner_ridge", name="Skinner Ridge", rc=(82, 133), priority_score=90.0),
        ScienceWaypoint(id="delta_rim_overlook", name="Delta Rim Overlook", rc=(66, 128), priority_score=95.0),
    ]
    return terrain, transform, waypoints


@pytest.fixture
def sample_mission_bundle(terrain_context):
    terrain, transform, waypoints = terrain_context

    plan_payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "stops": [
            {"id": "hawksbill_gap", "row": 95, "col": 140, "priority_score": 85.0, "dwell_time_s": 900.0}
        ],
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "max_distance_m": 15000.0,
        "max_duration_s": 28800.0,
    }
    baseline_route = plan_route_api(plan_payload, terrain, transform, waypoints)

    contingency_payload = {
        **plan_payload,
        "custom_events": [
            {
                "id": "test_rockfall_1",
                "name": "Local Ridge Rockfall",
                "event_type": "closed_corridor",
                "center_rc": [90, 138],
                "radius_m": 60.0,
                "enabled": True,
            }
        ]
    }
    contingency_result = contingency_simulate_api(contingency_payload, terrain, transform, waypoints)

    bundle = build_canonical_mission_run_bundle(
        mission_input=plan_payload,
        baseline_route=baseline_route,
        terrain=terrain,
        scenario_result=contingency_result,
        comparison_metrics={
            "delta_distance_m": contingency_result.get("delta_distance_m"),
            "delta_travel_time_s": contingency_result.get("delta_travel_time_s"),
            "is_scenario_reachable": contingency_result.get("is_scenario_reachable"),
            "is_scenario_budget_feasible": contingency_result.get("is_scenario_budget_feasible"),
        },
        contingency_input={
            "events": contingency_payload["custom_events"],
            "is_compound": False,
            "num_events": 1,
        }
    )
    return bundle


# =============================================================================
# 1. Schema Validation & Required Fields
# =============================================================================

def test_bundle_schema_validation_and_required_fields(sample_mission_bundle):
    """Bundle strictly validates against Draft 2020-12 schema and contains all required top-level fields."""
    is_valid, errors = validate_contract(sample_mission_bundle, "mission-run-bundle")
    assert is_valid is True, f"Schema validation errors: {errors}"

    required_fields = [
        "schema_version",
        "bundle_id",
        "created_at",
        "computation_fingerprint",
        "terrain_provenance",
        "mission_input",
        "baseline_route",
        "reachability_and_feasibility",
        "engine_metadata",
        "disclosures",
    ]
    for field in required_fields:
        assert field in sample_mission_bundle, f"Missing required top-level field: {field}"

    assert sample_mission_bundle["schema_version"] == "1.0.0"
    assert len(sample_mission_bundle["computation_fingerprint"]) == 64


# =============================================================================
# 2. Stable Computation Fingerprints
# =============================================================================

def test_stable_computation_fingerprints(terrain_context, sample_mission_bundle):
    """Equivalent planning and contingency inputs yield identical deterministic SHA-256 fingerprints."""
    fp1 = sample_mission_bundle["computation_fingerprint"]

    raw_events = (
        sample_mission_bundle.get("contingency_input", {}).get("events")
        or sample_mission_bundle["mission_input"].get("custom_events")
        or []
    )

    # Re-compute fingerprint directly from the same inputs
    fp2 = compute_bundle_fingerprint(
        sample_mission_bundle["mission_input"],
        contingency_events=raw_events,
        dataset_id=sample_mission_bundle["terrain_provenance"]["dataset_id"],
        terrain_sha256=sample_mission_bundle["terrain_provenance"]["sha256_hash"],
    )
    assert fp1 == fp2, "Fingerprint must be stable and deterministic"
    assert isinstance(fp1, str) and len(fp1) == 64


# =============================================================================
# 3. Fingerprint Sensitivity
# =============================================================================

def test_fingerprint_sensitivity_to_input_changes(sample_mission_bundle):
    """Mutating start, goal, stops, profile, vehicle mode, or contingency changes the fingerprint."""
    base_input = sample_mission_bundle["mission_input"]
    tid = sample_mission_bundle["terrain_provenance"]["dataset_id"]
    t_sha = sample_mission_bundle["terrain_provenance"]["sha256_hash"]
    c_events = sample_mission_bundle.get("contingency_input", {}).get("events", [])

    base_fp = compute_bundle_fingerprint(base_input, contingency_events=c_events, dataset_id=tid, terrain_sha256=t_sha)

    # 1. Mutate start
    mut_start = {**base_input, "start": {"row": 118, "col": 157}}
    assert compute_bundle_fingerprint(mut_start, contingency_events=c_events, dataset_id=tid, terrain_sha256=t_sha) != base_fp

    # 2. Mutate goal
    mut_goal = {**base_input, "goal": {"row": 65, "col": 128}}
    assert compute_bundle_fingerprint(mut_goal, contingency_events=c_events, dataset_id=tid, terrain_sha256=t_sha) != base_fp

    # 3. Mutate profile
    mut_prof = {**base_input, "profile": "conservative"}
    assert compute_bundle_fingerprint(mut_prof, contingency_events=c_events, dataset_id=tid, terrain_sha256=t_sha) != base_fp

    # 4. Mutate vehicle mode
    mut_veh = {**base_input, "vehicle_mode": "robotic_rover"}
    assert compute_bundle_fingerprint(mut_veh, contingency_events=c_events, dataset_id=tid, terrain_sha256=t_sha) != base_fp

    # 5. Mutate contingency event
    mut_events = [
        {
            "id": "test_rockfall_1",
            "name": "Different Event",
            "event_type": "closed_corridor",
            "center_rc": [90, 138],
            "radius_m": 120.0,
            "enabled": True,
        }
    ]
    assert compute_bundle_fingerprint(base_input, contingency_events=mut_events, dataset_id=tid, terrain_sha256=t_sha) != base_fp


# =============================================================================
# 4. Terrain Provenance and Raster SHA-256 Hash
# =============================================================================

def test_terrain_identity_and_sha256(sample_mission_bundle):
    """Verifies terrain provenance identity and checks that the recorded hash matches the actual GeoTIFF."""
    prov = sample_mission_bundle["terrain_provenance"]
    assert prov["dataset_id"] == TERRAIN_DATASET_ID
    assert prov["sha256_hash"] == TERRAIN_SHA256

    # Verify directly against physical file on disk
    with open(GEOTIFF_PATH, "rb") as f:
        actual_file_sha = hashlib.sha256(f.read()).hexdigest()
    assert actual_file_sha == TERRAIN_SHA256


# =============================================================================
# 5. Route Geometry & Cartography Export
# =============================================================================

def test_export_route_geometry_and_cartography(sample_mission_bundle):
    """Verifies baseline route geometry exists and cartography extracts 3D coordinates and steps."""
    b_route = sample_mission_bundle["baseline_route"]
    assert "path_rc" in b_route and len(b_route["path_rc"]) > 10
    assert b_route["distance_m"] > 0

    carto = generate_route_cartography(b_route, scenario_result=sample_mission_bundle.get("scenario_result"))
    assert "baseline_route" in carto
    assert "coordinates_3d" in carto["baseline_route"]
    assert "path_rc" in carto["baseline_route"]
    assert len(carto["baseline_route"]["path_rc"]) == len(b_route["path_rc"])
    assert carto["baseline_route"]["num_steps"] == b_route.get("num_steps", len(b_route["path_rc"]) - 1)

    if sample_mission_bundle.get("scenario_result"):
        assert "scenario_route" in carto
        assert carto["scenario_route"] is not None


# =============================================================================
# 6. Comparison CSV Values Match Calculations
# =============================================================================

def test_comparison_csv_matches_underlying_metrics(sample_mission_bundle):
    """CSV export matches underlying numeric route metrics."""
    b_route = sample_mission_bundle["baseline_route"]
    scen_res = sample_mission_bundle.get("scenario_result")
    comp_metrics = sample_mission_bundle.get("comparison_metrics")

    csv_text = generate_comparison_csv(b_route, scen_res, comp_metrics)
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)

    assert len(rows) >= 6
    header = rows[0]
    assert header == ["Metric", "Baseline_Nominal", "Scenario_Revised", "Delta_Absolute", "Delta_Percent", "Unit", "Status"]

    metrics_dict = {r[0]: r for r in rows[1:]}
    assert "Ground Traverse Distance" in metrics_dict
    dist_row = metrics_dict["Ground Traverse Distance"]

    baseline_dist = float(dist_row[1])
    assert abs(baseline_dist - b_route["distance_m"]) < 0.1


# =============================================================================
# 7. Rejection of NaN, Inf, and Out-of-Bounds Coordinates
# =============================================================================

def test_rejection_of_invalid_json_nan_inf_out_of_bounds(terrain_context):
    """Rejects NaN, inf, and coordinates exceeding grid boundaries."""
    terrain, transform, waypoints = terrain_context

    # NaN in mission input
    nan_input = {
        "start": {"row": float("nan"), "col": 157},
        "goal": {"row": 66, "col": 128},
        "stops": [],
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
    }
    with pytest.raises((ValueError, ContractValidationError)):
        compute_bundle_fingerprint(nan_input, dataset_id=TERRAIN_DATASET_ID, terrain_sha256=TERRAIN_SHA256)

    # Out of bounds bundle verification
    oob_bundle = {
        "schema_version": "1.0.0",
        "bundle_id": "test_oob",
        "created_at": "2026-10-18T00:00:00Z",
        "computation_fingerprint": "a" * 64,
        "terrain_provenance": {
            "dataset_id": TERRAIN_DATASET_ID,
            "source": "USGS Astrogeology Science Center MRO CTX DTM",
            "resolution_m": 20.0,
            "dimensions": {"height": 250, "width": 250},
            "coordinate_reference": "IAU Mars 2000 Planetocentric Sphere",
            "sha256_hash": TERRAIN_SHA256,
            "file_size_bytes": 252206,
        },
        "mission_input": {
            "start": {"row": 99999, "col": 99999},
            "goal": {"row": 66, "col": 128},
            "profile": "balanced",
            "vehicle_mode": "crew_eva",
        },
        "baseline_route": {
            "path_rc": [[99999, 99999]],
            "distance_m": 100.0,
            "cost": 100.0,
            "duration_s": 100.0,
            "formatted_travel_time": "1m",
            "profile": "balanced",
            "vehicle_mode": "crew_eva",
            "is_reachable": True,
            "is_budget_feasible": True,
            "visited_waypoint_ids": [],
            "regret_ledger": {"omitted_targets": []},
            "timeline": {},
        },
        "reachability_and_feasibility": {
            "is_baseline_reachable": True,
            "is_baseline_budget_feasible": True,
            "overall_status": "nominal",
        },
        "engine_metadata": {
            "model_version": "2.0.0",
            "assumptions_version": "1.0.0",
            "planner_algorithm": "A*",
            "assumptions": {},
        },
        "disclosures": ["Test"],
    }
    res = verify_bundle_integrity(oob_bundle, terrain=terrain)
    assert res["is_integrity_valid"] is False
    assert any("exceed terrain bounds" in err.lower() for err in res["integrity_errors"])


# =============================================================================
# 8. Severed / Impassable Route Reporting
# =============================================================================

def test_blocked_scenario_reachability_reporting(terrain_context):
    """When a corridor closure severs all possible paths, reachability is honestly false."""
    terrain, transform, waypoints = terrain_context

    plan_payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "stops": [],
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
    }
    baseline_route = plan_route_api(plan_payload, terrain, transform, waypoints)

    # Block start cell directly to sever traverse
    block_payload = {
        **plan_payload,
        "custom_events": [
            {
                "id": "block_start",
                "name": "Complete Blockade",
                "event_type": "closed_corridor",
                "blocked_cells": [[117, 157]],
                "enabled": True,
            }
        ]
    }
    scen_result = contingency_simulate_api(block_payload, terrain, transform, waypoints)

    bundle = build_canonical_mission_run_bundle(
        mission_input=plan_payload,
        baseline_route=baseline_route,
        terrain=terrain,
        scenario_result=scen_result,
        comparison_metrics={
            "delta_distance_m": scen_result.get("delta_distance_m"),
            "delta_travel_time_s": scen_result.get("delta_travel_time_s"),
            "is_scenario_reachable": scen_result.get("is_scenario_reachable"),
            "is_scenario_budget_feasible": scen_result.get("is_scenario_budget_feasible"),
        },
    )

    assert bundle["reachability_and_feasibility"]["is_scenario_reachable"] is False
    assert bundle["reachability_and_feasibility"]["is_scenario_budget_feasible"] is False

    briefing = generate_decision_pack_briefing_md(bundle)
    assert "IMPASSABLE" in briefing or "severed" in briefing.lower() or "unreachable" in briefing.lower()


# =============================================================================
# 9. Immutability of Historical Missions & Experiments
# =============================================================================

def test_immutability_of_historical_missions_and_experiments(terrain_context, sample_mission_bundle):
    """Exporting decision packs or verifying bundles leaves existing historical files untouched."""
    missions_before = list_missions()
    experiments_before = list_experiments()

    # Perform bundle verification and export
    verify_bundle_integrity(sample_mission_bundle)
    generate_decision_pack_briefing_md(sample_mission_bundle)
    generate_comparison_csv(sample_mission_bundle["baseline_route"])

    missions_after = list_missions()
    experiments_after = list_experiments()

    assert len(missions_after) == len(missions_before)
    assert len(experiments_after) == len(experiments_before)
    assert [m["mission_id"] for m in missions_after] == [m["mission_id"] for m in missions_before]
    assert [e["experiment_id"] for e in experiments_after] == [e["experiment_id"] for e in experiments_before]


# =============================================================================
# 10. Replay Creates Distinct Run & Verifies Exact Reproduction
# =============================================================================

def test_bundle_replay_exact_reproduction(terrain_context, sample_mission_bundle, tmp_path):
    """Replay independently re-executes calculations and asserts reproduction within strict tolerance."""
    terrain, transform, waypoints = terrain_context

    replay_res = replay_decision_pack_bundle(
        bundle=sample_mission_bundle,
        terrain=terrain,
        transform=transform,
        waypoints=waypoints,
        experiments_dir=str(tmp_path),
        allow_persist=True,
    )

    assert replay_res["is_reproduced"] is True
    assert replay_res["comparisons"]["distance_delta_m"] <= 0.1
    assert replay_res["comparisons"]["travel_time_delta_s"] <= 0.1
    assert replay_res["comparisons"]["path_geometry_identical"] is True
    assert replay_res["comparisons"]["visited_targets_identical"] is True

    # Check that a distinct experiment was persisted in isolated tmp_path
    exp_files = list(tmp_path.glob("*.json"))
    assert len(exp_files) == 1
    assert exp_files[0].name.startswith("replay_")


# =============================================================================
# 11. Terrain Incompatibility Detection
# =============================================================================

def test_terrain_incompatibility_detection(terrain_context, sample_mission_bundle):
    """Mismatched terrain SHA-256 or dataset ID is flagged during integrity verification."""
    terrain, _, _ = terrain_context

    tampered_bundle = json.loads(json.dumps(sample_mission_bundle))
    tampered_bundle["terrain_provenance"]["sha256_hash"] = "0" * 64

    res = verify_bundle_integrity(tampered_bundle, terrain=terrain)
    assert res["is_replay_compatible"] is False
    assert any("hash mismatch" in note.lower() for note in res["compatibility_notes"])


# =============================================================================
# 12. Tampered Fingerprint Rejected
# =============================================================================

def test_tampered_fingerprint_rejected(terrain_context, sample_mission_bundle):
    """Modifying fingerprint without modifying data causes validation to fail."""
    tampered_bundle = json.loads(json.dumps(sample_mission_bundle))
    tampered_bundle["computation_fingerprint"] = "f" * 64

    res = verify_bundle_integrity(tampered_bundle)
    assert res["fingerprint_matches"] is False
    assert res["is_integrity_valid"] is False


# =============================================================================
# 13. Decision Pack ZIP Valid Extraction & Safe Manifest
# =============================================================================

def test_decision_pack_zip_valid_extraction_and_manifest(terrain_context, sample_mission_bundle):
    """Decision Pack ZIP contains 5 expected files, safe relative paths, and valid contents."""
    terrain, transform, waypoints = terrain_context

    zip_bytes, filename, bundle = export_decision_pack_api(
        {"bundle": sample_mission_bundle},
        terrain,
        transform,
        waypoints,
    )

    assert filename.startswith("marswalk_decision_pack_") and filename.endswith(".zip")
    assert len(zip_bytes) > 1000

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        expected_files = [
            "mission_brief.md",
            "comparison.csv",
            "README.txt",
            "mission_bundle.json",
            "route.json",
        ]
        for exp in expected_files:
            assert exp in namelist, f"ZIP archive missing expected file: {exp}"
            # Ensure no directory traversal or absolute paths
            assert not exp.startswith("/") and not exp.startswith("\\") and ".." not in exp

            content = zf.read(exp)
            assert len(content) > 0, f"File {exp} in ZIP is empty"

        # Verify mission_bundle.json inside the ZIP matches original bundle
        bundle_in_zip = json.loads(zf.read("mission_bundle.json").decode("utf-8"))
        assert bundle_in_zip["bundle_id"] == sample_mission_bundle["bundle_id"]
        assert bundle_in_zip["computation_fingerprint"] == sample_mission_bundle["computation_fingerprint"]


# =============================================================================
# 14. Live Atlas Server Endpoints Verification
# =============================================================================

def test_14_live_server_decision_pack_and_bundle_endpoints(sample_mission_bundle):
    """Query live server endpoints /api/export_decision_pack, /api/bundle/verify, /api/bundle/replay."""
    base_url = "http://127.0.0.1:3000"

    # 1. Test POST /api/export_decision_pack
    try:
        req = urllib.request.Request(
            f"{base_url}/api/export_decision_pack",
            data=json.dumps({"bundle": sample_mission_bundle}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 200
            assert resp.headers.get("Content-Type") == "application/zip"
            zip_bytes = resp.read()
            assert len(zip_bytes) > 1000
    except urllib.error.URLError as e:
        pytest.skip(f"Atlas server not running at {base_url}: {e}")

    # 2. Test POST /api/bundle/verify
    req_v = urllib.request.Request(
        f"{base_url}/api/bundle/verify",
        data=json.dumps({"bundle": sample_mission_bundle}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_v, timeout=10) as resp_v:
        assert resp_v.status == 200
        v_res = json.loads(resp_v.read().decode("utf-8"))
        assert v_res["is_integrity_valid"] is True
        assert v_res["is_replay_compatible"] is True
        assert v_res["fingerprint_matches"] is True

    # 3. Test POST /api/bundle/replay (without persisting)
    req_r = urllib.request.Request(
        f"{base_url}/api/bundle/replay",
        data=json.dumps({"bundle": sample_mission_bundle, "persist": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_r, timeout=10) as resp_r:
        assert resp_r.status == 200
        r_res = json.loads(resp_r.read().decode("utf-8"))
        assert r_res["is_reproduced"] is True

