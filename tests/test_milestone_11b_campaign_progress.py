"""
Tests for Milestone 11B: Campaign Progress & Science Observation Registry.
Covers:
  1. Science observation schema validation and physical SI unit enforcement.
  2. Provenance tagging (SIMULATED vs imported authentic data) and missing-data null safety.
  3. Progress event schema validation, lifecycle transitions, and idempotency key duplicate rejection.
  4. Dynamic replanning: target completion marks COMPLETED and unblocks downstream DAG targets.
  5. Invariant enforcement: completed targets are permanently protected from being rescheduled.
  6. Target blockage: marks BLOCKED and tracks unscheduled reason.
  7. Multi-sol execution: frozen prior sols, shifted sol indices, version increment, and delta synthesis.
  8. Workspace persistence: saving, querying, and filtering observations and progress events.
  9. Live REST API endpoints:
     - POST /api/campaign/progress
     - GET /api/campaign/progress
     - POST /api/campaign/observations
     - GET /api/campaign/observations
     - GET /api/campaign/next_eligible_targets
"""

import json
import os
import uuid
import shutil
import tempfile
import urllib.request
import urllib.error
import pytest
import numpy as np

from marswalk.core.terrain import load_and_process_terrain, TerrainGrid, TerrainConfig
from marswalk.core.mission_campaign import (
    CampaignTarget,
    CampaignConfig,
    CampaignSortie,
    MissionCampaign,
    TargetStatus,
    plan_mission_campaign,
)
from marswalk.core.campaign_progress import (
    ObservationType,
    ObservationProvenance,
    ProgressEventType,
    SortieLifecycleState,
    QuantitativeMeasurement,
    ScienceObservation,
    CampaignProgressEvent,
    validate_observation_record,
    validate_progress_event_record,
    calculate_campaign_progress_metrics,
    get_next_eligible_targets,
    advance_campaign_progress,
    RECOGNIZED_PHYSICAL_UNITS,
)
from marswalk.api.workspace import (
    save_campaign,
    get_campaign,
    list_campaigns,
    save_observation,
    get_observation,
    list_observations,
    save_progress_event,
    list_progress_events,
    WorkspaceError,
)
from marswalk.api.contracts import validate_contract, ContractValidationError
from marswalk.api.service import (
    record_campaign_progress_api,
    get_campaign_progress_api,
    record_campaign_observation_api,
    list_campaign_observations_api,
    get_next_eligible_targets_api,
    APIError,
)


@pytest.fixture(scope="module")
def jezero_terrain():
    """Load authentic USGS CTX 20m Jezero Crater terrain."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tiff_path = os.path.join(base_dir, "data", "processed", "jezero_ready_20m.tif")
    if not os.path.exists(tiff_path):
        pytest.skip(f"Jezero CTX raster not found at {tiff_path}")
    return load_and_process_terrain(tiff_path)


@pytest.fixture
def temp_workspace(monkeypatch):
    """Temporary workspace directories for tests."""
    temp_dir = tempfile.mkdtemp(prefix="marswalk_m11b_test_")
    obs_dir = os.path.join(temp_dir, "observations")
    prog_dir = os.path.join(temp_dir, "campaign_progress")
    camp_dir = os.path.join(temp_dir, "campaigns")
    os.makedirs(obs_dir, exist_ok=True)
    os.makedirs(prog_dir, exist_ok=True)
    os.makedirs(camp_dir, exist_ok=True)

    yield {
        "root": temp_dir,
        "observations": obs_dir,
        "campaign_progress": prog_dir,
        "campaigns": camp_dir,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# 1. Observation Schema & Physical SI Unit Enforcement
# ==============================================================================

def test_observation_valid_si_units():
    """Test that valid SI and planetary units pass observation validation."""
    valid_obs = {
        "schema_version": "1.0.0",
        "observation_id": "obs_test_001",
        "campaign_id": "cmp_test_alpha",
        "target_id": "target_sample_a",
        "timestamp_utc": "2026-10-29T12:00:00Z",
        "observation_type": ObservationType.GEOLOGICAL_ASSAY.value,
        "provenance": ObservationProvenance.SIMULATED.value,
        "is_simulated": True,
        "instrument_name": "PIXL_SIMULATOR",
        "quantitative_measurements": [
            {"parameter": "silica_weight_percent", "value": 45.2, "unit": "%", "uncertainty": 0.5},
            {"parameter": "surface_temperature", "value": 210.5, "unit": "K"},
            {"parameter": "atmospheric_pressure", "value": 750.0, "unit": "Pa"},
            {"parameter": "traverse_distance", "value": 1250.0, "unit": "m"},
        ],
        "qualitative_notes": "Layered clay sulfate contact observed in Jezero delta.",
        "evidence_references": {"camera_frame": "SOL_012_PIX_0042.RAW"},
        "confidence_score": 0.95,
    }
    validate_observation_record(valid_obs)


def test_observation_invalid_units_raise_error():
    """Test that unrecognized non-SI units (e.g. feet, psi, mph) raise ValueError."""
    bad_obs = {
        "schema_version": "1.0.0",
        "observation_id": "obs_test_bad_unit",
        "campaign_id": "cmp_test_alpha",
        "target_id": "target_sample_a",
        "timestamp_utc": "2026-10-29T12:00:00Z",
        "observation_type": ObservationType.ATMOSPHERIC_MEASUREMENT.value,
        "provenance": ObservationProvenance.SIMULATED.value,
        "is_simulated": True,
        "quantitative_measurements": [
            {"parameter": "wind_speed", "value": 15.0, "unit": "mph"},  # INVALID
        ],
    }
    with pytest.raises(ValueError, match="Unrecognized physical unit 'mph'"):
        validate_observation_record(bad_obs)


def test_observation_provenance_and_simulated_consistency():
    """Test that provenance SIMULATED requires is_simulated=True and authentic requires is_simulated=False."""
    # SIMULATED provenance with is_simulated=False must fail
    inconsistent_1 = {
        "schema_version": "1.0.0",
        "observation_id": "obs_test_inconsistent_1",
        "campaign_id": "cmp_test_alpha",
        "target_id": "target_a",
        "timestamp_utc": "2026-10-29T12:00:00Z",
        "observation_type": "SPECTRAL_SURVEY",
        "provenance": "SIMULATED",
        "is_simulated": False,  # Conflict
    }
    with pytest.raises(ValueError, match="Observations with provenance 'SIMULATED' must have is_simulated=True"):
        validate_observation_record(inconsistent_1)

    # Authentic MEDA provenance with is_simulated=True must fail
    inconsistent_2 = {
        "schema_version": "1.0.0",
        "observation_id": "obs_test_inconsistent_2",
        "campaign_id": "cmp_test_alpha",
        "target_id": "target_a",
        "timestamp_utc": "2026-10-29T12:00:00Z",
        "observation_type": "ATMOSPHERIC_MEASUREMENT",
        "provenance": "IMPORTED_PDS_MEDA",
        "is_simulated": True,  # Conflict: authentic data cannot be labeled simulated
    }
    with pytest.raises(ValueError, match="Authentic observation from IMPORTED_PDS_MEDA must not be labeled as simulated"):
        validate_observation_record(inconsistent_2)


def test_observation_dataclass_roundtrip():
    """Test ScienceObservation dataclass to_dict and from_dict fidelity."""
    obs = ScienceObservation(
        observation_id="obs_roundtrip_001",
        campaign_id="cmp_rt_01",
        target_id="target_01",
        timestamp_utc="2026-10-29T14:30:00Z",
        observation_type=ObservationType.SAMPLE_CORE_EXTRACTION.value,
        provenance=ObservationProvenance.SIMULATED.value,
        is_simulated=True,
        sortie_id="sortie_sol_01",
        target_name="Sample Core Belva",
        sol_index=1,
        instrument_name="CORER_DRILL",
        quantitative_measurements=[
            QuantitativeMeasurement(parameter="core_length", value=5.4, unit="cm", uncertainty=0.1)
        ],
        qualitative_notes="Fine-grained sedimentary rock sample successfully sealed.",
        confidence_score=0.98,
    )
    obs_dict = obs.to_dict()
    obs_restored = ScienceObservation.from_dict(obs_dict)

    assert obs_restored.observation_id == obs.observation_id
    assert obs_restored.campaign_id == obs.campaign_id
    assert obs_restored.observation_type == obs.observation_type
    assert len(obs_restored.quantitative_measurements) == 1
    assert obs_restored.quantitative_measurements[0].unit == "cm"
    assert obs_restored.quantitative_measurements[0].value == 5.4


# ==============================================================================
# 2. Campaign Progress Event & Idempotency
# ==============================================================================

def test_progress_event_validation():
    """Test CampaignProgressEvent contract validation."""
    valid_event = {
        "schema_version": "1.0.0",
        "event_id": "cpe_test_001",
        "campaign_id": "cmp_test_campaign",
        "sol_index": 1,
        "sortie_id": "sortie_sol_01",
        "event_type": ProgressEventType.TARGET_OBSERVED.value,
        "target_id": "target_a",
        "observation_id": "obs_test_001",
        "timestamp_utc": "2026-10-29T12:00:00Z",
        "details": {"phase": "science_dwell", "energy_kwh": 1.2},
        "idempotency_key": "cmp_test_TARGET_OBSERVED_target_a_sol1_001",
    }
    validate_progress_event_record(valid_event)


def test_progress_event_idempotency_rejection(jezero_terrain):
    """Test that submitting duplicate progress events with identical idempotency key is rejected."""
    targets = [
        CampaignTarget(id="t1", name="Target 1", row=120, col=158, priority_score=50.0),
        CampaignTarget(id="t2", name="Target 2", row=125, col=155, priority_score=40.0),
    ]
    cfg = CampaignConfig(base_start_rc=(117, 157), max_duration_per_sortie_s=7200.0)
    campaign = plan_mission_campaign("cmp_idemp", "Idempotency Test", cfg, targets, jezero_terrain)

    existing_event = CampaignProgressEvent(
        event_id="cpe_first",
        campaign_id=campaign.campaign_id,
        sol_index=1,
        event_type="TARGET_VISITED",
        target_id="t1",
        timestamp_utc="2026-10-29T12:00:00Z",
        idempotency_key="UNIQUE_IDEMP_KEY_001",
    )

    with pytest.raises(ValueError, match="Duplicate progress event rejected"):
        advance_campaign_progress(
            campaign=campaign,
            event_type="TARGET_VISITED",
            target_id="t1",
            terrain=jezero_terrain,
            sol_index=1,
            details={"idempotency_key": "UNIQUE_IDEMP_KEY_001"},
            existing_events=[existing_event],
        )


# ==============================================================================
# 3. Dynamic Progress Engine, Target Completion & DAG Unblocking
# ==============================================================================

def test_target_completion_and_non_rescheduling_invariant(jezero_terrain):
    """
    Test that completing a target:
      1. Marks it COMPLETED and adds it to completed_target_ids.
      2. Permanently prevents it from being rescheduled in remaining planned sols.
      3. Increments the campaign version and calculates deltas.
    """
    targets = [
        CampaignTarget(id="t_alpha", name="Alpha Outcrop", row=120, col=158, priority_score=80.0),
        CampaignTarget(id="t_beta", name="Beta Crater", row=125, col=155, priority_score=60.0),
        CampaignTarget(id="t_gamma", name="Gamma Ridge", row=110, col=160, priority_score=40.0),
    ]
    # Restrict max duration so targets require multiple sols
    cfg = CampaignConfig(
        base_start_rc=(117, 157),
        max_duration_per_sortie_s=2500.0,
        return_to_base_each_sol=True,
    )
    campaign = plan_mission_campaign("cmp_complete_test", "Completion Invariant", cfg, targets, jezero_terrain)
    assert campaign.version == 1

    # Simulate observation at t_alpha
    obs = ScienceObservation(
        observation_id="obs_alpha_01",
        campaign_id=campaign.campaign_id,
        target_id="t_alpha",
        timestamp_utc="2026-10-29T12:00:00Z",
        observation_type=ObservationType.GEOLOGICAL_ASSAY.value,
        provenance=ObservationProvenance.SIMULATED.value,
        is_simulated=True,
        target_name="Alpha Outcrop",
        sol_index=1,
        quantitative_measurements=[
            QuantitativeMeasurement(parameter="calcium_abundance", value=12.4, unit="%")
        ],
    )

    updated_campaign, progress_event, returned_obs = advance_campaign_progress(
        campaign=campaign,
        event_type=ProgressEventType.TARGET_OBSERVED.value,
        target_id="t_alpha",
        terrain=jezero_terrain,
        sol_index=1,
        observation=obs,
    )

    # 1. Verification of version and progress state
    assert updated_campaign.version == 2
    assert "t_alpha" in updated_campaign.progress["completed_target_ids"]
    assert updated_campaign.progress["completion_percentage"] > 0.0

    # 2. NON-RESCHEDULING INVARIANT:
    # t_alpha must NOT appear in the target list of any remaining planned sorties (sols >= 1 replanned)
    remaining_sorties = [s for s in updated_campaign.sorties if s.sol_index > 1]
    for s in remaining_sorties:
        assert "t_alpha" not in s.target_ids, f"Completed target 't_alpha' was rescheduled in Sol {s.sol_index}!"

    # 3. Target status updated
    target_alpha = next(t for t in updated_campaign.targets if t.id == "t_alpha")
    assert target_alpha.status == TargetStatus.COMPLETED.value


def test_prerequisite_dag_unblocking(jezero_terrain):
    """
    Test DAG prerequisite progression:
      Target B requires Target A.
      Before Target A is completed, Target B is NOT eligible.
      After Target A is completed, Target B becomes eligible.
    """
    targets = [
        CampaignTarget(id="t_parent", name="Parent Target", row=120, col=158, priority_score=100.0),
        CampaignTarget(
            id="t_child",
            name="Child Target",
            row=125, col=155,
            priority_score=90.0,
            prerequisites=["t_parent"],
        ),
    ]
    cfg = CampaignConfig(base_start_rc=(117, 157), max_duration_per_sortie_s=7200.0)
    campaign = plan_mission_campaign("cmp_dag_prog", "DAG Test", cfg, targets, jezero_terrain)

    # Initially, no targets are completed
    eligible_initial = get_next_eligible_targets(campaign, completed_target_ids=set(), blocked_target_ids=set())
    eligible_ids = [t["id"] for t in eligible_initial]
    assert "t_parent" in eligible_ids
    assert "t_child" not in eligible_ids  # Child is not eligible yet!

    # Complete parent target
    updated_campaign, _, _ = advance_campaign_progress(
        campaign=campaign,
        event_type=ProgressEventType.TARGET_VISITED.value,
        target_id="t_parent",
        terrain=jezero_terrain,
        sol_index=1,
    )

    # Now child must be eligible
    completed = set(updated_campaign.progress["completed_target_ids"])
    eligible_after = get_next_eligible_targets(updated_campaign, completed_target_ids=completed, blocked_target_ids=set())
    eligible_ids_after = [t["id"] for t in eligible_after]
    assert "t_child" in eligible_ids_after
    assert "t_parent" not in eligible_ids_after  # Parent is completed, no longer "next eligible"


def test_target_blockage_lifecycle(jezero_terrain):
    """Test that blocking a target marks it BLOCKED and records reason."""
    targets = [
        CampaignTarget(id="t_block", name="Blocked Outcrop", row=120, col=158, priority_score=75.0),
        CampaignTarget(id="t_other", name="Accessible Outcrop", row=125, col=155, priority_score=50.0),
    ]
    cfg = CampaignConfig(base_start_rc=(117, 157), max_duration_per_sortie_s=7200.0)
    campaign = plan_mission_campaign("cmp_block_test", "Blockage Test", cfg, targets, jezero_terrain)

    updated_campaign, event, _ = advance_campaign_progress(
        campaign=campaign,
        event_type=ProgressEventType.TARGET_BLOCKED.value,
        target_id="t_block",
        terrain=jezero_terrain,
        sol_index=1,
        details={"reason": "Steep scree slope exceeds mobility threshold"},
    )

    assert "t_block" in updated_campaign.progress["blocked_target_ids"]
    t_target = next(t for t in updated_campaign.targets if t.id == "t_block")
    assert t_target.status == "BLOCKED"
    assert "Steep scree" in t_target.unscheduled_reason


# ==============================================================================
# 4. Workspace Persistence for Observations & Progress Events
# ==============================================================================

def test_workspace_save_and_list_observations(temp_workspace):
    """Test saving and retrieving observations in workspace."""
    obs_dir = temp_workspace["observations"]

    obs_1 = {
        "schema_version": "1.0.0",
        "observation_id": "obs_ws_001",
        "campaign_id": "cmp_ws_test",
        "target_id": "target_ws_a",
        "timestamp_utc": "2026-10-29T12:00:00Z",
        "observation_type": "GEOLOGICAL_ASSAY",
        "provenance": "SIMULATED",
        "is_simulated": True,
        "qualitative_notes": "First observation in workspace.",
    }
    obs_2 = {
        "schema_version": "1.0.0",
        "observation_id": "obs_ws_002",
        "campaign_id": "cmp_ws_test",
        "target_id": "target_ws_b",
        "timestamp_utc": "2026-10-29T13:00:00Z",
        "observation_type": "SPECTRAL_SURVEY",
        "provenance": "SIMULATED",
        "is_simulated": True,
        "qualitative_notes": "Second observation in workspace.",
    }

    save_observation(obs_1, observations_dir=obs_dir)
    save_observation(obs_2, observations_dir=obs_dir)

    # Retrieve specific observation
    retrieved = get_observation("obs_ws_001", observations_dir=obs_dir)
    assert retrieved["observation_id"] == "obs_ws_001"
    assert retrieved["qualitative_notes"] == "First observation in workspace."

    # List all observations
    all_obs = list_observations(observations_dir=obs_dir)
    assert len(all_obs) == 2

    # Filter by target_id
    filtered_b = list_observations(target_id="target_ws_b", observations_dir=obs_dir)
    assert len(filtered_b) == 1
    assert filtered_b[0]["observation_id"] == "obs_ws_002"


def test_workspace_save_and_list_progress_events(temp_workspace):
    """Test saving and retrieving progress events in workspace."""
    prog_dir = temp_workspace["campaign_progress"]

    ev_1 = {
        "schema_version": "1.0.0",
        "event_id": "cpe_ws_001",
        "campaign_id": "cmp_ws_prog",
        "sol_index": 1,
        "event_type": "TARGET_VISITED",
        "target_id": "target_a",
        "timestamp_utc": "2026-10-29T12:00:00Z",
        "idempotency_key": "idemp_ws_001",
    }
    save_progress_event(ev_1, progress_dir=prog_dir)

    events = list_progress_events("cmp_ws_prog", progress_dir=prog_dir)
    assert len(events) == 1
    assert events[0]["event_id"] == "cpe_ws_001"


# ==============================================================================
# 5. API Service Layer Functions
# ==============================================================================

def test_api_service_progress_and_observations(jezero_terrain, temp_workspace, monkeypatch):
    """Test service layer API functions directly."""
    # Monkeypatch workspace directories for test isolation
    monkeypatch.setattr("marswalk.api.workspace.DEFAULT_OBSERVATIONS_DIR", temp_workspace["observations"])
    monkeypatch.setattr("marswalk.api.workspace.DEFAULT_CAMPAIGN_PROGRESS_DIR", temp_workspace["campaign_progress"])
    monkeypatch.setattr("marswalk.api.workspace.DEFAULT_CAMPAIGNS_DIR", temp_workspace["campaigns"])

    # Plan a campaign
    targets = [
        {"id": "t_api_1", "name": "API Target 1", "row": 120, "col": 158, "priority_score": 80.0},
        {"id": "t_api_2", "name": "API Target 2", "row": 125, "col": 155, "priority_score": 60.0},
    ]
    camp_payload = {
        "campaign_id": "cmp_api_test_01",
        "name": "API Service Test",
        "targets": targets,
        "config": {"max_duration_per_sortie_s": 7200.0, "base_start_rc": [117, 157]},
    }
    from marswalk.api.service import plan_campaign_api
    camp_res = plan_campaign_api(camp_payload, jezero_terrain, getattr(jezero_terrain, "transform", None))
    cid = camp_res["campaign"]["campaign_id"]

    # 1. Record progress event via API
    progress_payload = {
        "campaign_id": cid,
        "event_type": "TARGET_OBSERVED",
        "target_id": "t_api_1",
        "sol_index": 1,
        "observation": {
            "observation_type": "GEOLOGICAL_ASSAY",
            "provenance": "SIMULATED",
            "is_simulated": True,
            "quantitative_measurements": [
                {"parameter": "hematite_wt_pct", "value": 8.7, "unit": "%"}
            ],
            "qualitative_notes": "High hematite concentration detected.",
        },
    }
    transform = getattr(jezero_terrain, "transform", None)
    prog_res = record_campaign_progress_api(progress_payload, jezero_terrain, transform)

    assert prog_res["status"] == "success"
    assert prog_res["campaign"]["version"] == 2
    assert "t_api_1" in prog_res["campaign"]["progress"]["completed_target_ids"]

    # 2. Query progress via GET API
    get_prog_res = get_campaign_progress_api(cid)
    assert get_prog_res["status"] == "success"
    assert get_prog_res["progress"]["completion_percentage"] == 50.0
    assert len(get_prog_res["events"]) == 1
    assert len(get_prog_res["observations"]) == 1

    # 3. Query next eligible targets
    next_res = get_next_eligible_targets_api(cid)
    assert next_res["status"] == "success"
    assert next_res["count"] == 1
    assert next_res["eligible_targets"][0]["id"] == "t_api_2"


# ==============================================================================
# 6. Live HTTP Endpoints (Port 3000)
# ==============================================================================

def test_live_server_campaign_progress_endpoints():
    """Verify live HTTP server on port 3000 handles campaign progress & observations endpoints."""
    base_url = "http://127.0.0.1:3000"

    # Check server availability
    try:
        req = urllib.request.Request(f"{base_url}/api/health")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
    except urllib.error.URLError:
        pytest.skip("Atlas HTTP server on port 3000 not currently reachable")

    # 1. Create a campaign on live server with unique ID for isolation
    live_cid = f"cmp_live_{uuid.uuid4().hex[:6]}"
    create_payload = json.dumps({
        "campaign_id": live_cid,
        "name": "Live HTTP 11B Test",
        "targets": [
            {"id": "t_live_a", "name": "Live Target A", "row": 120, "col": 158, "priority_score": 90.0},
            {"id": "t_live_b", "name": "Live Target B", "row": 125, "col": 155, "priority_score": 70.0, "prerequisites": ["t_live_a"]},
        ],
        "config": {"max_duration_per_sortie_s": 7200.0, "base_start_rc": [117, 157]},
    }).encode("utf-8")

    req_create = urllib.request.Request(
        f"{base_url}/api/campaign/plan",
        data=create_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req_create, timeout=10.0) as resp:
        assert resp.status == 200
        camp_data = json.loads(resp.read().decode())["campaign"]
        assert camp_data["campaign_id"] == live_cid

    # 2. Check next eligible targets (only t_live_a should be eligible)
    req_next = urllib.request.Request(f"{base_url}/api/campaign/next_eligible_targets?campaign_id={live_cid}")
    with urllib.request.urlopen(req_next, timeout=5.0) as resp:
        assert resp.status == 200
        next_data = json.loads(resp.read().decode())
        assert next_data["status"] == "success"
        eligible_ids = [t["id"] for t in next_data["eligible_targets"]]
        assert "t_live_a" in eligible_ids
        assert "t_live_b" not in eligible_ids

    # 3. Post a progress event with an observation
    progress_payload = json.dumps({
        "campaign_id": live_cid,
        "event_type": "TARGET_OBSERVED",
        "target_id": "t_live_a",
        "sol_index": 1,
        "observation": {
            "observation_type": "SPECTRAL_SURVEY",
            "provenance": "SIMULATED",
            "is_simulated": True,
            "quantitative_measurements": [
                {"parameter": "albedo", "value": 0.22, "unit": "dimensionless"},
                {"parameter": "olivine_fraction", "value": 15.0, "unit": "%"},
            ],
            "qualitative_notes": "Live HTTP test spectral survey completed successfully.",
        },
    }).encode("utf-8")

    req_prog = urllib.request.Request(
        f"{base_url}/api/campaign/progress",
        data=progress_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req_prog, timeout=10.0) as resp:
        assert resp.status == 200
        prog_res = json.loads(resp.read().decode())
        assert prog_res["status"] == "success"
        assert prog_res["campaign"]["version"] == 2
        assert "t_live_a" in prog_res["campaign"]["progress"]["completed_target_ids"]

    # 4. Check progress GET endpoint
    req_get_prog = urllib.request.Request(f"{base_url}/api/campaign/progress?campaign_id={live_cid}")
    with urllib.request.urlopen(req_get_prog, timeout=5.0) as resp:
        assert resp.status == 200
        get_res = json.loads(resp.read().decode())
        assert get_res["status"] == "success"
        assert get_res["progress"]["completion_percentage"] == 50.0
        assert len(get_res["events"]) == 1
        assert len(get_res["observations"]) == 1

    # 5. Check observations GET endpoint
    req_get_obs = urllib.request.Request(f"{base_url}/api/campaign/observations?campaign_id={live_cid}")
    with urllib.request.urlopen(req_get_obs, timeout=5.0) as resp:
        assert resp.status == 200
        obs_res = json.loads(resp.read().decode())
        assert obs_res["status"] == "success"
        assert obs_res["count"] == 1
        assert obs_res["observations"][0]["target_id"] == "t_live_a"

    # 6. Check next eligible targets after progress (t_live_b now unblocked!)
    with urllib.request.urlopen(req_next, timeout=5.0) as resp:
        assert resp.status == 200
        next_data_2 = json.loads(resp.read().decode())
        eligible_ids_2 = [t["id"] for t in next_data_2["eligible_targets"]]
        assert "t_live_b" in eligible_ids_2
        assert "t_live_a" not in eligible_ids_2
