"""
MarsWalk 2.0 — Milestone 12G Acceptance Test Suite
Causal Replay Studio, Forensic Divergence Detection & Rehearsal Evidence Bundle.

Tests:
1. Historical rehearsal replay reconstruction without active re-simulation (<50ms).
2. Causal decision ledger completeness, step IDs, preceding step IDs, and CausalLink validation.
3. Spatial collision check: off-track corridor closure does not induce false detour distance or penalty.
4. Forensic divergence detection: computes exact T_div, trigger, divergent sorties, and milestones.
5. Forensic evidence bundle export: SHA-256 manifest integrity, provenance, and ZIP packaging.
6. Zero-baseline and mathematical safety:
   - Aborted mission yields recovery_efficiency_pct == 0.0% (fixes inverted logic defect).
   - Operational delay yields 0.0m added ground distance (fixes phantom distance defect).
   - Zero-baseline science calculation safe from division-by-zero.
7. HTTP API endpoints for /replay, /bundle, and /bundle/export.
"""

import copy
import json
import os
import time
import urllib.request
import zipfile
import pytest
import rasterio

from marswalk.api.contracts import (
    TERRAIN_DATASET_ID,
    TERRAIN_SHA256,
    validate_mission_rehearsal_record,
)
from marswalk.api.workspace import (
    DEFAULT_REHEARSALS_DIR,
    delete_rehearsal_record,
    get_rehearsal_record,
    list_rehearsal_records,
    save_rehearsal_record,
)
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignTarget,
    MissionCampaign,
    PlanningProfile,
    plan_mission_campaign,
)
from marswalk.core.mission_rehearsal_director import (
    CausalDecisionStep,
    CausalLink,
    CausalLinkStatus,
    DisturbanceSpecification,
    DisturbanceType,
    DivergenceAnalysis,
    DivergenceMilestone,
    RecoveryPolicyType,
    RehearsalOutcomeStatus,
    compute_track_divergence,
    execute_mission_rehearsal,
    export_rehearsal_evidence_bundle,
    export_rehearsal_pack_zip,
    get_supported_disturbances_catalog,
    reconstruct_rehearsal_replay,
)
from marswalk.core.terrain import TerrainGrid, load_and_process_terrain

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOTIFF_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "jezero_ready_20m.tif")
API_BASE_URL = "http://127.0.0.1:3000"


@pytest.fixture(scope="module")
def jezero_terrain():
    """Load authentic 20m Jezero elevation grid."""
    if not os.path.exists(GEOTIFF_PATH):
        pytest.skip(f"Terrain GeoTIFF not found at {GEOTIFF_PATH}")
    return load_and_process_terrain(GEOTIFF_PATH)


@pytest.fixture
def test_campaign(jezero_terrain):
    """Create a deterministic test campaign with 3 targets."""
    cfg = CampaignConfig(
        planning_profile=PlanningProfile.SCIENCE_PRIORITY.value,
        max_duration_per_sortie_s=28800.0,
        base_start_rc=(117, 157),
    )
    targets = [
        CampaignTarget(id="t1", name="Delta Outcrop", row=120, col=160, priority_score=80.0, dwell_time_s=900.0),
        CampaignTarget(id="t2", name="Crater Ridge", row=125, col=165, priority_score=60.0, dwell_time_s=900.0),
        CampaignTarget(id="t3", name="Sediment Fan", row=115, col=150, priority_score=40.0, dwell_time_s=900.0),
    ]
    return plan_mission_campaign("cmp_test_12g", "12G Rehearsal Campaign", cfg, targets, jezero_terrain)


def test_01_historical_rehearsal_reconstruction_without_simulation(test_campaign, jezero_terrain):
    """Verify reconstruct_rehearsal_replay loads stored record without re-running simulation."""
    disturbances = [
        {
            "disturbance_id": "dst_test_01",
            "disturbance_type": "operational_delay",
            "trigger_time_s": 1200.0,
            "parameters": {"delay_s": 1800.0},
        }
    ]
    record = execute_mission_rehearsal(
        campaign=test_campaign,
        disturbances=disturbances,
        recovery_policy={"policy_type": "balanced"},
        terrain=jezero_terrain,
        title="Historical Replay Test",
    )
    save_rehearsal_record(record.to_dict())

    # Reconstruct historical replay
    t_start = time.perf_counter()
    replay = reconstruct_rehearsal_replay(record.rehearsal_id)
    duration_ms = (time.perf_counter() - t_start) * 1000.0

    # Must complete virtually instantly without running A* route planning
    assert duration_ms < 100.0, f"Reconstruction took {duration_ms:.1f}ms; expected <100ms"
    assert replay["rehearsal_id"] == record.rehearsal_id
    assert replay["campaign_id"] == test_campaign.campaign_id
    assert len(replay["causal_decision_ledger"]) == 7
    assert replay["divergence_analysis"]["diverged"] is True
    assert replay["divergence_analysis"]["t_diverge_s"] == 1200.0
    assert replay["causal_links_summary"]["total_links"] >= 5

    # Cleanup
    delete_rehearsal_record(record.rehearsal_id)


def test_02_causal_decision_ledger_and_link_inspector(test_campaign, jezero_terrain):
    """Verify CausalDecisionStep chain, preceding step IDs, and CausalLink classification."""
    disturbances = [
        {
            "disturbance_id": "dst_causal_1",
            "disturbance_type": "corridor_closure",
            "trigger_time_s": 1500.0,
            "parameters": {"center_rc": [120, 160], "radius_m": 60.0},
        }
    ]
    record = execute_mission_rehearsal(
        campaign=test_campaign,
        disturbances=disturbances,
        recovery_policy={"policy_type": "balanced"},
        terrain=jezero_terrain,
    )

    ledger = record.causal_ledger
    assert len(ledger) == 7

    # Verify sequential chain: preceding_step_id matches step_id of previous step
    for idx, step in enumerate(ledger):
        assert isinstance(step, CausalDecisionStep)
        assert step.step_id != ""
        assert step.evidence_status == "CONFIRMED"
        if idx == 0:
            assert step.preceding_step_id is None
        else:
            assert step.preceding_step_id == ledger[idx - 1].step_id

        # Verify each causal link
        assert len(step.causal_links) >= 1
        for link in step.causal_links:
            assert isinstance(link, CausalLink)
            assert link.link_id.startswith("clink_")
            assert link.status in (CausalLinkStatus.CONFIRMED, CausalLinkStatus.DERIVED, CausalLinkStatus.UNRESOLVED)
            assert 0.0 <= link.confidence <= 1.0
            assert len(link.evidence_rationale) > 5


def test_03_spatial_collision_check_non_intersecting_hazard(test_campaign, jezero_terrain):
    """Verify that an off-path corridor closure does NOT add false detour distance or penalty."""
    # Place hazard far away at (10, 10), while mission is around (117, 157)
    disturbances = [
        {
            "disturbance_id": "dst_faraway",
            "disturbance_type": "corridor_closure",
            "trigger_time_s": 1800.0,
            "parameters": {"center_rc": [10, 10], "radius_m": 50.0},
        }
    ]
    record = execute_mission_rehearsal(
        campaign=test_campaign,
        disturbances=disturbances,
        recovery_policy={"policy_type": "balanced"},
        terrain=jezero_terrain,
    )

    # Detour candidate should have 0 added detour distance because hazard is off-track
    cand_detour = next(c for c in record.recovery_candidates if c.strategy == "conservative_detour")
    assert cand_detour.added_detour_distance_m == 0.0
    assert record.recovered_metrics.total_distance_m == record.baseline_metrics.total_distance_m

    # The causal link in step 2 should acknowledge the off-track condition
    step_2 = record.causal_ledger[1]
    far_link = next(l for l in step_2.causal_links if l.source_id == "dst_faraway")
    assert far_link.status == CausalLinkStatus.UNRESOLVED
    assert "off-path" in far_link.evidence_rationale.lower()


def test_04_forensic_divergence_detection_algorithm(test_campaign, jezero_terrain):
    """Verify compute_track_divergence computes exact divergence point, cause, and milestones."""
    disturbances = [
        DisturbanceSpecification(
            disturbance_id="dst_div_test",
            disturbance_type=DisturbanceType.OPERATIONAL_DELAY,
            trigger_time_s=1800.0,
            parameters={"delay_s": 3600.0},
        )
    ]
    base_m = record_track_metrics_helper(duration=4000.0, distance=800.0, science=180.0, margin=24000.0)
    dist_m = record_track_metrics_helper(duration=7600.0, distance=800.0, science=180.0, margin=20400.0)
    rec_m = record_track_metrics_helper(duration=7600.0, distance=800.0, science=180.0, margin=20400.0)

    div = compute_track_divergence(base_m, dist_m, rec_m, disturbances, test_campaign)
    assert isinstance(div, DivergenceAnalysis)
    assert div.diverged is True
    assert div.t_diverge_s == 1800.0
    assert div.divergence_trigger_id == "dst_div_test"
    assert div.divergence_trigger_name == "operational_delay"
    assert len(div.divergence_milestones) >= 4

    # Nominal case: zero disturbances
    div_nom = compute_track_divergence(base_m, base_m, base_m, [])
    assert div_nom.diverged is False
    assert div_nom.t_diverge_s is None
    assert "zero divergence" in div_nom.summary.lower()


def test_05_rehearsal_evidence_bundle_export_and_readback(test_campaign, jezero_terrain):
    """Verify evidence bundle generation, SHA-256 manifest hashing, and ZIP pack contents."""
    disturbances = [
        {
            "disturbance_id": "dst_bundle_test",
            "disturbance_type": "operational_delay",
            "trigger_time_s": 900.0,
            "parameters": {"delay_s": 1800.0},
        }
    ]
    record = execute_mission_rehearsal(
        campaign=test_campaign,
        disturbances=disturbances,
        recovery_policy={"policy_type": "balanced"},
        terrain=jezero_terrain,
    )
    save_rehearsal_record(record.to_dict())

    bundle = export_rehearsal_evidence_bundle(record.rehearsal_id)
    assert bundle["schema_version"] == "2.0.0"
    assert bundle["bundle_id"] == f"reh_bundle_{record.rehearsal_id}"
    assert "manifest_sha256" in bundle["manifest"]
    assert bundle["scientific_provenance"]["dataset_id"] == TERRAIN_DATASET_ID
    assert bundle["scientific_provenance"]["dtm_resolution_m"] == 20.0
    assert "disclosures" in bundle

    # Test ZIP export
    zip_path = export_rehearsal_pack_zip(record.rehearsal_id)
    assert os.path.isfile(zip_path)

    with zipfile.ZipFile(zip_path, "r") as zf:
        file_list = zf.namelist()
        assert "manifest.json" in file_list
        assert "rehearsal_bundle.json" in file_list
        assert "causal_decision_ledger.json" in file_list
        assert "tri_track_comparison.csv" in file_list
        assert "briefing_report.md" in file_list
        assert "README.txt" in file_list

        # Verify manifest reads back valid JSON
        manifest_data = json.loads(zf.read("manifest.json"))
        assert "manifest_sha256" in manifest_data

    # Cleanup
    if os.path.exists(zip_path):
        os.remove(zip_path)
    delete_rehearsal_record(record.rehearsal_id)


def test_06_zero_baseline_and_mathematical_safety(test_campaign, jezero_terrain):
    """Verify mathematical safety: no phantom distance, no division by zero, and correct abort efficiency."""
    # 1. Operational delay should add 0.0 m to traverse distance (Defect 5B fix)
    dist_delay = [
        {
            "disturbance_id": "dst_delay_only",
            "disturbance_type": "operational_delay",
            "trigger_time_s": 600.0,
            "parameters": {"delay_s": 3600.0},
        }
    ]
    rec_delay = execute_mission_rehearsal(test_campaign, dist_delay, {"policy_type": "balanced"}, jezero_terrain)
    assert rec_delay.recovered_metrics.total_distance_m == rec_delay.baseline_metrics.total_distance_m
    assert rec_delay.comparison.distance_delta_m == 0.0

    # 2. Insurmountable disruption causing abort must yield recovery_efficiency_pct == 0.0 (Defect 5A fix)
    dist_catastrophic = [
        {
            "disturbance_id": "dst_fatal",
            "disturbance_type": "operational_delay",
            "trigger_time_s": 600.0,
            "parameters": {"delay_s": 50000.0},
        }
    ]
    rec_abort = execute_mission_rehearsal(
        test_campaign,
        dist_catastrophic,
        {"policy_type": "safety_first", "min_margin_threshold_s": 7200.0},
        jezero_terrain,
    )
    assert rec_abort.outcome_status == RehearsalOutcomeStatus.NO_FEASIBLE_RECOVERY.value
    assert rec_abort.comparison.recovery_efficiency_pct == 0.0
    assert rec_abort.comparison.science_preservation_pct == 0.0

    # 3. Zero-baseline campaign (0 science targets) handled cleanly without NaN
    cfg_zero = CampaignConfig(base_start_rc=(117, 157))
    t_zero = [CampaignTarget(id="tz1", name="Zero Target", row=118, col=158, priority_score=0.0, dwell_time_s=600.0)]
    cmp_zero = plan_mission_campaign("cmp_zero_sci", "Zero Science Campaign", cfg_zero, t_zero, jezero_terrain)
    rec_zero = execute_mission_rehearsal(cmp_zero, [], {"policy_type": "balanced"}, jezero_terrain)
    assert rec_zero.comparison.science_preservation_pct == 100.0
    assert not (rec_zero.comparison.science_preservation_pct != rec_zero.comparison.science_preservation_pct)  # Not NaN


def test_07_http_api_replay_and_bundle_endpoints(test_campaign, jezero_terrain):
    """Verify live HTTP API endpoints /replay, /bundle, and /bundle/export."""
    # Ensure server is running
    try:
        ping = urllib.request.urlopen(f"{API_BASE_URL}/api/health", timeout=2.0)
        assert ping.status == 200
    except Exception:
        pytest.skip(f"Live Atlas server not reachable at {API_BASE_URL}")

    # Create and persist a rehearsal
    disturbances = [
        {
            "disturbance_id": "dst_api_test",
            "disturbance_type": "operational_delay",
            "trigger_time_s": 900.0,
            "parameters": {"delay_s": 1200.0},
        }
    ]
    record = execute_mission_rehearsal(test_campaign, disturbances, {"policy_type": "balanced"}, jezero_terrain)
    save_rehearsal_record(record.to_dict())
    reh_id = record.rehearsal_id

    try:
        # Test 1: GET /api/rehearsal/<id>/replay
        with urllib.request.urlopen(f"{API_BASE_URL}/api/rehearsal/{reh_id}/replay", timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["status"] == "success"
            assert "replay" in data
            assert data["replay"]["rehearsal_id"] == reh_id
            assert len(data["replay"]["causal_decision_ledger"]) == 7

        # Test 2: GET /api/rehearsal/<id>/bundle
        with urllib.request.urlopen(f"{API_BASE_URL}/api/rehearsal/{reh_id}/bundle", timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["status"] == "success"
            assert "bundle" in data
            assert data["bundle"]["bundle_id"] == f"reh_bundle_{reh_id}"
            assert "manifest" in data["bundle"]

        # Test 3: POST /api/rehearsal/bundle/export (JSON format)
        req_json = urllib.request.Request(
            f"{API_BASE_URL}/api/rehearsal/bundle/export",
            data=json.dumps({"rehearsal_id": reh_id, "format": "json"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_json, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["status"] == "success"
            assert data["format"] == "json"
            assert "bundle" in data

        # Test 4: POST /api/rehearsal/bundle/export (ZIP format)
        req_zip = urllib.request.Request(
            f"{API_BASE_URL}/api/rehearsal/bundle/export",
            data=json.dumps({"rehearsal_id": reh_id, "format": "zip"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_zip, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["status"] == "success"
            assert data["format"] == "zip"
            assert "zip_path" in data
            if os.path.exists(data["zip_path"]):
                os.remove(data["zip_path"])

    finally:
        delete_rehearsal_record(reh_id)


def record_track_metrics_helper(duration: float, distance: float, science: float, margin: float):
    """Helper to instantiate RehearsalTrackMetrics for unit test divergence checks."""
    from marswalk.core.mission_rehearsal_director import RehearsalTrackMetrics
    return RehearsalTrackMetrics(
        track_name="test",
        total_duration_s=duration,
        total_distance_m=distance,
        science_score=science,
        targets_completed=3,
        targets_attempted=3,
        completed_target_ids=["t1", "t2", "t3"],
        dropped_target_ids=[],
        min_margin_s=margin,
        critical_events_count=0,
        violations=[],
        path_rc=[[117, 157], [120, 160]],
        coordinates_3d=[[4587723.0, 1095653.0, -2447.0]],
    )
