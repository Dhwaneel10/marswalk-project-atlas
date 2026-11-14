"""
MarsWalk 2.0 — Milestone 9U End-to-End Scenario Proof, Decision Pack Integrity & Rehearsal Suite

Verifies:
1. Automatic simulation of custom_events during Decision Pack export when scenario_result is omitted.
2. Cryptographic output tamper detection via execution_digest in verify_bundle_integrity.
3. Tamper detection on modified path_rc, distance_m, feasibility flags, and delta metrics.
4. Deterministic compound contingency replay reproducing exact geometry and metrics within 0.1m/0.1s.
5. Explicit export_type='baseline' guarantees pure nominal sortie without contingency leakage.
6. Explicit export_type='contingency' strictly validates presence of contingency events.
7. Workspace immutability guarantee: zero mutation of existing missions and historical experiments.
8. Live HTTP API integration round-trip on port 3000 for export, audit verification, and replay.
"""

import os
import io
import json
import zipfile
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
    compute_bundle_execution_digest,
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
    WorkspaceError,
    DEFAULT_MISSIONS_DIR,
    DEFAULT_EXPERIMENTS_DIR,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GEOTIFF_PATH = str(PROJECT_ROOT / "data" / "processed" / "jezero_ready_20m.tif")
ATLAS_BASE_URL = "http://127.0.0.1:3000"


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


# =============================================================================
# 1. AUTO-SIMULATION OF CUSTOM CONTINGENCIES DURING DECISION PACK EXPORT
# =============================================================================

def test_decision_pack_export_auto_simulates_custom_events(terrain_context):
    terrain, transform, waypoints = terrain_context

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "stops": [{"id": "hawksbill_gap", "row": 95, "col": 140, "priority_score": 85.0}],
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "custom_events": [
            {
                "id": "ev_closure_9u",
                "type": "closure",
                "center_rc": [95, 140],
                "radius_m": 80.0,
                "severity": "total_closure",
                "enabled": True,
            }
        ],
    }

    zip_bytes, filename, bundle = export_decision_pack_api(payload, terrain, transform, waypoints)

    assert filename.startswith("marswalk_decision_pack_run_bundle_contingency_")
    assert filename.endswith(".zip")
    assert bundle["scenario_result"] is not None
    assert bundle["contingency_input"] is not None
    assert bundle["contingency_input"]["events"][0]["id"] == "ev_closure_9u"
    assert "execution_digest" in bundle
    assert len(bundle["execution_digest"]) == 64

    # Verify the ZIP contains valid canonical mission_bundle.json
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        bundle_raw = json.loads(zf.read("mission_bundle.json").decode("utf-8"))
        assert bundle_raw["bundle_id"] == bundle["bundle_id"]
        assert bundle_raw["execution_digest"] == bundle["execution_digest"]
        is_valid, errs = validate_contract(bundle_raw, "mission-run-bundle")
        assert is_valid, f"Contract validation failed: {errs}"


# =============================================================================
# 2. CRYPTOGRAPHIC TAMPER DETECTION VIA EXECUTION DIGEST
# =============================================================================

def test_tamper_detection_catches_falsified_route_distance(terrain_context):
    terrain, transform, waypoints = terrain_context

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "export_type": "baseline",
    }
    _, _, bundle = export_decision_pack_api(payload, terrain, transform, waypoints)

    # Clean audit must pass
    audit_clean = verify_bundle_integrity(bundle, terrain=terrain)
    assert audit_clean["is_integrity_valid"] is True
    assert audit_clean["execution_digest_matches"] is True
    assert len(audit_clean["integrity_errors"]) == 0

    # Tamper with baseline route distance
    tampered_bundle = json.loads(json.dumps(bundle))
    tampered_bundle["baseline_route"]["distance_m"] = tampered_bundle["baseline_route"]["distance_m"] + 100.0

    audit_tampered = verify_bundle_integrity(tampered_bundle, terrain=terrain)
    assert audit_tampered["is_integrity_valid"] is False
    assert audit_tampered["execution_digest_matches"] is False
    assert any("Execution digest mismatch" in err for err in audit_tampered["integrity_errors"])

    # Attempting to replay tampered bundle must fail
    with pytest.raises(WorkspaceError) as exc_info:
        replay_decision_pack_bundle(tampered_bundle, terrain, transform, waypoints, allow_persist=False)
    assert exc_info.value.error_code == "ERR_BUNDLE_CORRUPTED"


def test_tamper_detection_catches_altered_path_geometry_and_feasibility(terrain_context):
    terrain, transform, waypoints = terrain_context

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "custom_events": [
            {
                "id": "ev_mobility",
                "type": "mobility",
                "mobility_multiplier": 0.5,
                "enabled": True,
            }
        ],
    }
    _, _, bundle = export_decision_pack_api(payload, terrain, transform, waypoints)

    # 1. Tamper with path geometry coordinate
    tampered_geom = json.loads(json.dumps(bundle))
    orig_path = tampered_geom["baseline_route"]["path_rc"]
    tampered_geom["baseline_route"]["path_rc"] = [[0, 0]] + orig_path[1:]

    audit_geom = verify_bundle_integrity(tampered_geom, terrain=terrain)
    assert audit_geom["is_integrity_valid"] is False
    assert audit_geom["execution_digest_matches"] is False

    # 2. Tamper with comparison metrics
    tampered_comp = json.loads(json.dumps(bundle))
    tampered_comp["comparison_metrics"]["delta_travel_time_s"] = 0.0

    audit_comp = verify_bundle_integrity(tampered_comp, terrain=terrain)
    assert audit_comp["is_integrity_valid"] is False
    assert audit_comp["execution_digest_matches"] is False

    # 3. Tamper with reachability overall_status
    tampered_status = json.loads(json.dumps(bundle))
    tampered_status["reachability_and_feasibility"]["overall_status"] = "falsified_nominal"

    audit_status = verify_bundle_integrity(tampered_status, terrain=terrain)
    assert audit_status["is_integrity_valid"] is False
    assert audit_status["execution_digest_matches"] is False


# =============================================================================
# 3. COMPOUND CONTINGENCY DETERMINISTIC REPLAY & REPRODUCTION
# =============================================================================

def test_compound_contingency_replay_exact_reproduction(terrain_context):
    terrain, transform, waypoints = terrain_context

    compound_events = [
        {
            "id": "c1_rockfall",
            "type": "closure",
            "center_rc": [90, 138],
            "radius_m": 60.0,
            "severity": "total_closure",
            "enabled": True,
        },
        {
            "id": "c2_mobility_derating",
            "type": "mobility",
            "mobility_multiplier": 0.75,
            "enabled": True,
        },
        {
            "id": "c3_ops_hold",
            "type": "operational_hold",
            "operational_delay_s": 600.0,
            "enabled": True,
        },
    ]

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "stops": [
            {"id": "hawksbill_gap", "row": 95, "col": 140, "priority_score": 85.0},
            {"id": "skinner_ridge", "row": 82, "col": 133, "priority_score": 90.0},
        ],
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "custom_events": compound_events,
    }

    zip_bytes, filename, bundle = export_decision_pack_api(payload, terrain, transform, waypoints)

    assert bundle["contingency_input"]["is_compound"] is True
    assert bundle["contingency_input"]["num_events"] == 3

    # Replay in an isolated temporary directory to guarantee zero contamination
    with tempfile.TemporaryDirectory() as tmp_dir:
        replay_res = replay_decision_pack_bundle(
            bundle,
            terrain,
            transform,
            waypoints,
            experiments_dir=tmp_dir,
            allow_persist=True,
        )

        assert replay_res["is_integrity_valid"] is True
        assert replay_res["is_replay_compatible"] is True
        assert replay_res["is_reproduced"] is True
        assert replay_res["verification_status"] == "reproduced"

        comparisons = replay_res["comparisons"]
        assert comparisons["path_geometry_identical"] is True
        assert comparisons["visited_targets_identical"] is True
        assert comparisons["distance_delta_m"] <= 0.1
        assert comparisons["travel_time_delta_s"] <= 0.1
        assert comparisons["scenario_geometry_identical"] is True
        assert comparisons["scenario_distance_delta_m"] <= 0.1
        assert comparisons["scenario_travel_time_delta_s"] <= 0.1


# =============================================================================
# 4. EXPLICIT EXPORT TYPE HANDLING
# =============================================================================

def test_export_type_baseline_guarantees_pure_sortie(terrain_context):
    terrain, transform, waypoints = terrain_context

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
        "export_type": "baseline",
        # Pass custom events that should be ignored because export_type is 'baseline'
        "custom_events": [
            {
                "id": "ignored_closure",
                "type": "closure",
                "center_rc": [90, 138],
                "radius_m": 100.0,
                "severity": "total_closure",
                "enabled": True,
            }
        ],
    }

    _, filename, bundle = export_decision_pack_api(payload, terrain, transform, waypoints)

    assert bundle["bundle_id"].startswith("run_bundle_baseline_")
    assert bundle["scenario_result"] is None
    assert bundle["contingency_input"] is None
    assert bundle["comparison_metrics"] is None

    audit = verify_bundle_integrity(bundle, terrain=terrain)
    assert audit["is_integrity_valid"] is True
    assert audit["execution_digest_matches"] is True


def test_export_type_contingency_rejects_missing_scenario(terrain_context):
    terrain, transform, waypoints = terrain_context

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
        "export_type": "contingency",
        # No scenario_result and no custom_events
    }

    with pytest.raises(APIError) as exc_info:
        export_decision_pack_api(payload, terrain, transform, waypoints)

    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "ERR_NO_CONTINGENCY"


# =============================================================================
# 5. IMMUTABILITY GUARANTEE
# =============================================================================

def test_immutability_preserves_historical_missions_and_experiments(terrain_context):
    terrain, transform, waypoints = terrain_context

    initial_missions = list_missions(missions_dir=DEFAULT_MISSIONS_DIR)
    initial_experiments = list_experiments(experiments_dir=DEFAULT_EXPERIMENTS_DIR)

    assert len(initial_missions) == 7, "Expected exactly 7 saved missions"
    assert len(initial_experiments) == 11, "Expected exactly 11 saved experiments"

    initial_m_ids = {m["mission_id"] for m in initial_missions}
    initial_e_ids = {e["experiment_id"] for e in initial_experiments}

    # Run complete export, verify, and replay with allow_persist=False
    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "science_first",
        "vehicle_mode": "robotic_rover",
    }
    _, _, bundle = export_decision_pack_api(payload, terrain, transform, waypoints)
    verify_bundle_integrity(bundle, terrain=terrain)
    replay_decision_pack_bundle(bundle, terrain, transform, waypoints, allow_persist=False)

    post_missions = list_missions(missions_dir=DEFAULT_MISSIONS_DIR)
    post_experiments = list_experiments(experiments_dir=DEFAULT_EXPERIMENTS_DIR)

    assert len(post_missions) == 7
    assert len(post_experiments) == 11
    assert {m["mission_id"] for m in post_missions} == initial_m_ids
    assert {e["experiment_id"] for e in post_experiments} == initial_e_ids


# =============================================================================
# 6. LIVE HTTP API ENDPOINT INTEGRATION
# =============================================================================

def test_live_http_decision_pack_export_and_verification_cycle():
    # 1. Export Decision Pack over HTTP
    req_data = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "export_type": "baseline",
    }
    req = urllib.request.Request(
        f"{ATLAS_BASE_URL}/api/export_decision_pack",
        data=json.dumps(req_data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "application/zip"
        zip_bytes = resp.read()

    # 2. Extract mission_bundle.json from received ZIP
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        bundle = json.loads(zf.read("mission_bundle.json").decode("utf-8"))

    assert "execution_digest" in bundle
    assert "computation_fingerprint" in bundle

    # 3. Verify bundle via POST /api/bundle/verify
    v_req = urllib.request.Request(
        f"{ATLAS_BASE_URL}/api/bundle/verify",
        data=json.dumps({"bundle": bundle}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(v_req, timeout=10) as resp:
        assert resp.status == 200
        audit = json.loads(resp.read().decode("utf-8"))
        assert audit["is_integrity_valid"] is True
        assert audit["execution_digest_matches"] is True
        assert audit["fingerprint_matches"] is True

    # 4. Tamper with bundle and verify rejection via POST /api/bundle/verify
    tampered_bundle = dict(bundle)
    tampered_bundle["execution_digest"] = "0000000000000000000000000000000000000000000000000000000000000000"

    t_req = urllib.request.Request(
        f"{ATLAS_BASE_URL}/api/bundle/verify",
        data=json.dumps({"bundle": tampered_bundle}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(t_req, timeout=10) as resp:
        assert resp.status == 200
        tamper_audit = json.loads(resp.read().decode("utf-8"))
        assert tamper_audit["is_integrity_valid"] is False
        assert tamper_audit["execution_digest_matches"] is False
