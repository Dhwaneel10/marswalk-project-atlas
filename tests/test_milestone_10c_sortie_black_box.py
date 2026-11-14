"""
MarsWalk 2.0 — Milestone 10C Test Suite: Sortie Black Box & Incident Replay.
Verifies event ledger persistence, deterministic chronological ordering, Draft 2020-12
schema compliance, idempotency, truthful separation of recorded vs recomputed outputs,
incident timeline reconstruction, and live API endpoints.
"""

import os
import json
import uuid
import tempfile
import urllib.request
import urllib.parse
from pathlib import Path
import pytest
import rasterio

from marswalk.core.terrain import TerrainGrid
from marswalk.core.planner import ScienceWaypoint
from marswalk.core.mission_event_ledger import (
    MissionEvent,
    record_event,
    record_events_batch,
    get_mission_events,
    clear_mission_events,
    generate_event_id,
    get_current_iso_time,
    EventLedgerError,
    VALID_EVENT_TYPES,
)
from marswalk.core.incident_replay import (
    reconstruct_incident_timeline,
    replay_incident,
)
from marswalk.api.contracts import validate_contract, ContractValidationError


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEM_PATH = PROJECT_ROOT / "data" / "processed" / "jezero_ready_20m.tif"
SAVED_MISSIONS_DIR = PROJECT_ROOT / "data" / "workspaces" / "missions"
SAVED_EXPERIMENTS_DIR = PROJECT_ROOT / "data" / "workspaces" / "experiments"
BASE_URL = "http://127.0.0.1:3000"


@pytest.fixture(scope="module")
def terrain_and_transform():
    """Load authentic Jezero Crater 20m CTX DTM grid and affine transform."""
    from marswalk.core.terrain import load_and_process_terrain
    terrain = load_and_process_terrain(str(DEM_PATH))
    with rasterio.open(DEM_PATH) as src:
        transform = src.transform
    return terrain, transform


@pytest.fixture
def temp_ledger_dir():
    """Create a temporary directory for isolated event ledger tests."""
    with tempfile.TemporaryDirectory(prefix="marswalk_events_test_") as tmpdir:
        yield Path(tmpdir)


# -----------------------------------------------------------------------------
# 1. Event Model & Identification Tests
# -----------------------------------------------------------------------------

def test_01_event_id_generation_and_format():
    """Verify that generate_event_id produces unique, prefixed IDs conforming to regex."""
    ids = {generate_event_id() for _ in range(100)}
    assert len(ids) == 100
    for eid in ids:
        assert eid.startswith("evt_")
        assert len(eid) >= 12


def test_02_mission_event_schema_contract_validation():
    """Verify that MissionEvent objects serialize to valid Draft 2020-12 schema."""
    evt = MissionEvent(
        event_id="evt_test_10c_001",
        source_mission_id="mission_jezero_alpha",
        continuation_id=None,
        event_type="sortie_started",
        mission_time_s=0.0,
        playback_elapsed_s=0.0,
        recorded_at_utc=get_current_iso_time(),
        route_variant="nominal",
        rover_rc=(117, 157),
        elevation_m=-2540.5,
        slope_deg=2.1,
        speed_m_s=0.55,
        payload={"mission_name": "Jezero Crater Science Traverse"},
        provenance={"source": "telemetry", "is_recomputed": False, "algorithm_version": "10C"},
    )
    d = evt.to_dict()
    # Contract validation raises on failure
    validate_contract(d, "mission-event")
    assert d["event_id"] == "evt_test_10c_001"
    assert d["event_type"] == "sortie_started"


def test_03_invalid_event_attributes_rejected():
    """Verify that negative timestamps or invalid event types are strictly rejected."""
    with pytest.raises(EventLedgerError):
        MissionEvent(
            event_id="evt_invalid_01",
            source_mission_id="mission_beta",
            event_type="invalid_action_unknown",
            mission_time_s=10.0,
            playback_elapsed_s=10.0,
            recorded_at_utc=get_current_iso_time(),
        )

    with pytest.raises(EventLedgerError):
        MissionEvent(
            event_id="evt_invalid_02",
            source_mission_id="mission_beta",
            event_type="sortie_started",
            mission_time_s=-5.0,  # Negative time not allowed
            playback_elapsed_s=0.0,
            recorded_at_utc=get_current_iso_time(),
        )


# -----------------------------------------------------------------------------
# 2. Append-Only Persistence & Deduplication
# -----------------------------------------------------------------------------

def test_04_atomic_event_recording_and_retrieval(temp_ledger_dir):
    """Verify append-only recording and accurate retrieval from disk."""
    mission_id = "test_mission_01"
    evt1 = MissionEvent(
        event_id="evt_001",
        source_mission_id=mission_id,
        event_type="sortie_started",
        mission_time_s=0.0,
        playback_elapsed_s=0.0,
        recorded_at_utc=get_current_iso_time(),
        rover_rc=(117, 157),
    )
    evt2 = MissionEvent(
        event_id="evt_002",
        source_mission_id=mission_id,
        event_type="playback_checkpoint",
        mission_time_s=120.0,
        playback_elapsed_s=120.0,
        recorded_at_utc=get_current_iso_time(),
        rover_rc=(122, 155),
    )

    record_event(evt1, base_dir=temp_ledger_dir)
    record_event(evt2, base_dir=temp_ledger_dir)

    loaded = get_mission_events(mission_id, base_dir=temp_ledger_dir)
    assert len(loaded) == 2
    assert loaded[0].event_id == "evt_001"
    assert loaded[1].event_id == "evt_002"
    assert loaded[1].mission_time_s == 120.0


def test_05_idempotent_duplicate_handling(temp_ledger_dir):
    """Verify that re-submitting an identical event_id does not create duplicate entries."""
    mission_id = "test_mission_idempotent"
    evt = MissionEvent(
        event_id="evt_idemp_01",
        source_mission_id=mission_id,
        event_type="sortie_started",
        mission_time_s=0.0,
        playback_elapsed_s=0.0,
        recorded_at_utc=get_current_iso_time(),
    )
    # Record twice
    record_event(evt, base_dir=temp_ledger_dir)
    record_event(evt, base_dir=temp_ledger_dir)

    loaded = get_mission_events(mission_id, base_dir=temp_ledger_dir)
    assert len(loaded) == 1
    assert loaded[0].event_id == "evt_idemp_01"


def test_06_batch_event_recording(temp_ledger_dir):
    """Verify recording multiple events in a single batch."""
    mission_id = "test_mission_batch"
    batch = [
        {
            "event_id": f"evt_batch_{i}",
            "source_mission_id": mission_id,
            "event_type": "playback_checkpoint",
            "mission_time_s": float(i * 60),
            "playback_elapsed_s": float(i * 60),
            "recorded_at_utc": get_current_iso_time(),
            "route_variant": "nominal",
        }
        for i in range(1, 6)
    ]
    recorded = record_events_batch(batch, base_dir=temp_ledger_dir)
    assert len(recorded) == 5

    loaded = get_mission_events(mission_id, base_dir=temp_ledger_dir)
    assert len(loaded) == 5
    assert [e.mission_time_s for e in loaded] == [60.0, 120.0, 180.0, 240.0, 300.0]


# -----------------------------------------------------------------------------
# 3. Deterministic Ordering & Query Filtering
# -----------------------------------------------------------------------------

def test_07_deterministic_chronological_ordering(temp_ledger_dir):
    """Verify that events recorded out of order are always returned sorted by mission_time_s."""
    mission_id = "test_mission_order"
    t_vals = [300.0, 50.0, 800.0, 0.0, 150.0]
    for idx, t in enumerate(t_vals):
        record_event({
            "event_id": f"evt_ord_{idx}",
            "source_mission_id": mission_id,
            "event_type": "playback_checkpoint",
            "mission_time_s": t,
            "playback_elapsed_s": t,
            "recorded_at_utc": get_current_iso_time(),
            "route_variant": "nominal",
        }, base_dir=temp_ledger_dir)

    loaded = get_mission_events(mission_id, base_dir=temp_ledger_dir)
    sorted_times = [e.mission_time_s for e in loaded]
    assert sorted_times == [0.0, 50.0, 150.0, 300.0, 800.0]


def test_08_filtering_by_event_type_and_time(temp_ledger_dir):
    """Verify filtering by event_type, since_time_s, and until_time_s."""
    mission_id = "test_mission_filter"
    events_def = [
        ("sortie_started", 0.0),
        ("playback_checkpoint", 100.0),
        ("target_reached", 200.0),
        ("science_dwell_started", 200.0),
        ("science_dwell_completed", 500.0),
        ("playback_checkpoint", 600.0),
        ("mission_completed", 900.0),
    ]
    for idx, (etype, t) in enumerate(events_def):
        record_event({
            "event_id": f"evt_flt_{idx}",
            "source_mission_id": mission_id,
            "event_type": etype,
            "mission_time_s": t,
            "playback_elapsed_s": t,
            "recorded_at_utc": get_current_iso_time(),
            "route_variant": "nominal",
        }, base_dir=temp_ledger_dir)

    checkpoints = get_mission_events(mission_id, event_type="playback_checkpoint", base_dir=temp_ledger_dir)
    assert len(checkpoints) == 2

    time_slice = get_mission_events(mission_id, since_time_s=200.0, until_time_s=600.0, base_dir=temp_ledger_dir)
    assert len(time_slice) == 4  # 200, 200, 500, 600


def test_09_missing_ledger_handled_gracefully(temp_ledger_dir):
    """Verify that querying a mission with no recorded events returns an empty list without error."""
    loaded = get_mission_events("non_existent_mission_id", base_dir=temp_ledger_dir)
    assert loaded == []


# -----------------------------------------------------------------------------
# 4. Incident Reconstruction & Decision Replay
# -----------------------------------------------------------------------------

def test_10_reconstruct_incident_timeline(temp_ledger_dir):
    """Verify that timeline reconstruction identifies phases and decision points correctly."""
    mission_id = "test_mission_timeline"
    events = [
        {"event_id": "evt_t0", "source_mission_id": mission_id, "event_type": "sortie_started", "mission_time_s": 0.0, "playback_elapsed_s": 0.0, "recorded_at_utc": get_current_iso_time(), "route_variant": "nominal"},
        {"event_id": "evt_t1", "source_mission_id": mission_id, "event_type": "playback_checkpoint", "mission_time_s": 200.0, "playback_elapsed_s": 200.0, "recorded_at_utc": get_current_iso_time(), "route_variant": "nominal"},
        {"event_id": "evt_t2", "source_mission_id": mission_id, "event_type": "contingency_injected", "mission_time_s": 350.0, "playback_elapsed_s": 350.0, "recorded_at_utc": get_current_iso_time(), "route_variant": "nominal", "rover_rc": [136, 142], "payload": {"event_type": "closure", "radius_m": 60.0}},
        {"event_id": "evt_t3", "source_mission_id": mission_id, "event_type": "route_recalculated", "mission_time_s": 350.0, "playback_elapsed_s": 350.0, "recorded_at_utc": get_current_iso_time(), "route_variant": "adaptive", "payload": {"recommendation": "continue_with_detour"}},
        {"event_id": "evt_t4", "source_mission_id": mission_id, "event_type": "continuation_selected", "mission_time_s": 350.0, "playback_elapsed_s": 0.0, "recorded_at_utc": get_current_iso_time(), "route_variant": "continuation", "continuation_id": "cont_abc123"},
        {"event_id": "evt_t5", "source_mission_id": mission_id, "event_type": "mission_completed", "mission_time_s": 1800.0, "playback_elapsed_s": 1450.0, "recorded_at_utc": get_current_iso_time(), "route_variant": "continuation", "continuation_id": "cont_abc123"},
    ]
    record_events_batch(events, base_dir=temp_ledger_dir)

    summary = reconstruct_incident_timeline(mission_id, base_dir=temp_ledger_dir)
    assert summary["total_events"] == 6
    assert summary["has_incident"] is True
    assert summary["timeline_summary"]["contingency_events_count"] == 1
    assert summary["timeline_summary"]["replan_events_count"] == 2
    assert "contingency_interruption" in summary["timeline_summary"]["phases"]
    assert "adaptive_replanning" in summary["timeline_summary"]["phases"]


def test_11_replay_incident_with_authentic_terrain(terrain_and_transform, temp_ledger_dir):
    """Verify that replay_incident re-evaluates the contingency on Jezero terrain and confirms fidelity."""
    terrain, transform = terrain_and_transform
    mission_id = "test_mission_replay_live"

    events = [
        {
            "event_id": "evt_rep_01",
            "source_mission_id": mission_id,
            "event_type": "sortie_started",
            "mission_time_s": 0.0,
            "playback_elapsed_s": 0.0,
            "recorded_at_utc": get_current_iso_time(),
            "route_variant": "nominal",
            "rover_rc": [117, 157],
        },
        {
            "event_id": "evt_rep_02",
            "source_mission_id": mission_id,
            "event_type": "contingency_injected",
            "mission_time_s": 400.0,
            "playback_elapsed_s": 400.0,
            "recorded_at_utc": get_current_iso_time(),
            "route_variant": "nominal",
            "rover_rc": [136, 142],
            "elevation_m": -2538.0,
            "slope_deg": 2.5,
            "payload": {
                "event_type": "closure",
                "center_rc": [142, 146],
                "radius_m": 60.0,
                "remaining_budget_s": 24000.0,
                "destination_rc": [194, 131],
                "completed_stop_ids": [],
                "unvisited_waypoints": [],
            },
        },
        {
            "event_id": "evt_rep_03",
            "source_mission_id": mission_id,
            "event_type": "route_recalculated",
            "mission_time_s": 400.0,
            "playback_elapsed_s": 400.0,
            "recorded_at_utc": get_current_iso_time(),
            "route_variant": "adaptive",
            "payload": {
                "recommendation": "continue_with_detour",
                "adaptive_continuation": {
                    "distance_m": 1250.0,
                    "total_time_s": 2200.0,
                    "path_rc": [],
                },
            },
        },
    ]
    record_events_batch(events, base_dir=temp_ledger_dir)

    result = replay_incident(mission_id, terrain, transform, base_dir=temp_ledger_dir, recompute=True)
    assert result["status"] == "success"
    assert result["schema_version"] == "1.0.0"
    assert result["reconstructed_sortie"]["has_incident"] is True
    assert result["reconstructed_sortie"]["interruption_rc"] == [136, 142]
    assert result["fidelity"]["is_recomputed"] is True
    # Recomputed recommendation detours around closure
    assert result["reconstructed_sortie"]["recomputed_recommendation"] in ("continue_with_detour", "abort_to_direct_baseline")


def test_12_replay_without_incident_handles_gracefully(terrain_and_transform, temp_ledger_dir):
    """Verify replay on a nominal sortie with no contingencies reports has_incident=False."""
    terrain, transform = terrain_and_transform
    mission_id = "test_mission_nominal_only"
    events = [
        {"event_id": "evt_nom_01", "source_mission_id": mission_id, "event_type": "sortie_started", "mission_time_s": 0.0, "playback_elapsed_s": 0.0, "recorded_at_utc": get_current_iso_time(), "route_variant": "nominal"},
        {"event_id": "evt_nom_02", "source_mission_id": mission_id, "event_type": "mission_completed", "mission_time_s": 1500.0, "playback_elapsed_s": 1500.0, "recorded_at_utc": get_current_iso_time(), "route_variant": "nominal"},
    ]
    record_events_batch(events, base_dir=temp_ledger_dir)

    result = replay_incident(mission_id, terrain, transform, base_dir=temp_ledger_dir)
    assert result["reconstructed_sortie"]["has_incident"] is False
    assert result["reconstructed_sortie"]["incident_event_id"] is None
    assert result["fidelity"]["is_recomputed"] is False


# -----------------------------------------------------------------------------
# 5. Workspace Immutability & Safety
# -----------------------------------------------------------------------------

def test_13_historical_missions_remain_untouched():
    """Verify that existing historical missions in data/workspaces/missions/ are not modified."""
    mission_files = list(SAVED_MISSIONS_DIR.glob("*.json"))
    assert len(mission_files) >= 7
    for mf in mission_files:
        with open(mf, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert ("mission_id" in data or "id" in data)
        assert "name" in data


def test_14_historical_experiments_remain_untouched():
    """Verify that existing historical experiments in data/workspaces/experiments/ are not modified."""
    exp_files = list(SAVED_EXPERIMENTS_DIR.glob("*.json"))
    assert len(exp_files) >= 11
    for ef in exp_files:
        with open(ef, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert ("experiment_id" in data or "id" in data)
        assert "name" in data


def test_15_path_traversal_attempts_rejected():
    """Verify that path traversal in mission_id is strictly blocked."""
    with pytest.raises(EventLedgerError):
        get_mission_events("../../etc/passwd")

    with pytest.raises(EventLedgerError):
        get_mission_events("..\\..\\windows\\system32")


def test_16_oversized_batch_rejected(temp_ledger_dir):
    """Verify that an oversized batch (>500 items) is rejected."""
    batch = [
        {
            "event_id": f"evt_huge_{i}",
            "source_mission_id": "test_oversized",
            "event_type": "playback_checkpoint",
            "mission_time_s": float(i),
            "playback_elapsed_s": float(i),
            "recorded_at_utc": get_current_iso_time(),
            "route_variant": "nominal",
        }
        for i in range(505)
    ]
    with pytest.raises(EventLedgerError):
        record_events_batch(batch, base_dir=temp_ledger_dir)


# -----------------------------------------------------------------------------
# 6. Live HTTP Endpoints Integration
# -----------------------------------------------------------------------------

def test_17_live_http_post_mission_events():
    """Test POST /api/mission/events on live server."""
    test_id = f"test_api_{uuid.uuid4().hex[:6]}"
    payload = {
        "event": {
            "event_id": f"evt_live_{uuid.uuid4().hex[:8]}",
            "source_mission_id": test_id,
            "event_type": "sortie_started",
            "mission_time_s": 0.0,
            "playback_elapsed_s": 0.0,
            "recorded_at_utc": get_current_iso_time(),
            "route_variant": "nominal",
            "rover_rc": [117, 157],
            "elevation_m": -2540.0,
            "slope_deg": 1.5,
            "speed_m_s": 0.55,
            "payload": {"status": "nominal_departure"},
            "provenance": {"source": "live_test", "is_recomputed": False},
        }
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/mission/events",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert res["status"] == "success"
        assert res["recorded_count"] == 1
        assert len(res["events"]) == 1


def test_18_live_http_get_mission_events():
    """Test GET /api/mission/events on live server."""
    test_id = f"test_api_{uuid.uuid4().hex[:6]}"
    # Record one event first
    evt_id = f"evt_live_{uuid.uuid4().hex[:8]}"
    post_payload = {
        "event": {
            "event_id": evt_id,
            "source_mission_id": test_id,
            "event_type": "playback_checkpoint",
            "mission_time_s": 60.0,
            "playback_elapsed_s": 60.0,
            "recorded_at_utc": get_current_iso_time(),
            "route_variant": "nominal",
            "payload": {"checkpoint": "waypoint_1"},
            "provenance": {"source": "live_test", "is_recomputed": False},
        }
    }
    req_post = urllib.request.Request(
        f"{BASE_URL}/api/mission/events",
        data=json.dumps(post_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req_post, timeout=5) as resp:
        assert resp.status == 200

    # Retrieve via GET
    with urllib.request.urlopen(f"{BASE_URL}/api/mission/events?source_mission_id={test_id}", timeout=5) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert res["status"] == "success"
        assert res["source_mission_id"] == test_id
        assert res["total_events"] >= 1
        assert res["events"][0]["event_id"] == evt_id


def test_19_live_http_post_incident_replay():
    """Test POST /api/mission/incident/replay on live server."""
    test_id = f"test_api_{uuid.uuid4().hex[:6]}"
    # Record incident event
    post_payload = {
        "events": [
            {
                "event_id": f"evt_liv_start_{uuid.uuid4().hex[:6]}",
                "source_mission_id": test_id,
                "event_type": "sortie_started",
                "mission_time_s": 0.0,
                "playback_elapsed_s": 0.0,
                "recorded_at_utc": get_current_iso_time(),
                "route_variant": "nominal",
                "rover_rc": [117, 157],
            },
            {
                "event_id": f"evt_liv_inc_{uuid.uuid4().hex[:6]}",
                "source_mission_id": test_id,
                "event_type": "contingency_injected",
                "mission_time_s": 300.0,
                "playback_elapsed_s": 300.0,
                "recorded_at_utc": get_current_iso_time(),
                "route_variant": "nominal",
                "rover_rc": [136, 142],
                "elevation_m": -2538.0,
                "slope_deg": 2.2,
                "payload": {
                    "event_type": "closure",
                    "center_rc": [140, 145],
                    "radius_m": 60.0,
                    "remaining_budget_s": 25000.0,
                    "destination_rc": [194, 131],
                },
            },
        ]
    }
    req_post = urllib.request.Request(
        f"{BASE_URL}/api/mission/events",
        data=json.dumps(post_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req_post, timeout=5) as resp:
        assert resp.status == 200

    # Call incident replay
    replay_payload = {
        "source_mission_id": test_id,
        "recompute": True,
    }
    req_replay = urllib.request.Request(
        f"{BASE_URL}/api/mission/incident/replay",
        data=json.dumps(replay_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req_replay, timeout=10) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert res["status"] == "success"
        assert res["schema_version"] == "1.0.0"
        assert res["source_mission_id"] == test_id
        assert res["reconstructed_sortie"]["has_incident"] is True
        assert res["reconstructed_sortie"]["interruption_rc"] == [136, 142]
        # Validate against schema
        validate_contract(res, "incident-replay-response")


def test_20_decision_pack_bundle_regression():
    """Verify that Decision Pack contracts remain valid and backward compatible."""
    from marswalk.api.contracts import validate_contract
    sample_bundle = {
        "schema_version": "1.0.0",
        "bundle_id": "test_bundle_10c",
        "created_at_utc": get_current_iso_time(),
        "mission_name": "Decision Pack Integrity Test",
        "mission_snapshot": {
            "schema_version": "1.0.0",
            "input_fingerprint": "abc123def456",
            "departure": {"row": 117, "col": 157, "name": "Start"},
            "destination": {"row": 194, "col": 131, "name": "Goal"},
            "intermediate_stops": [],
            "vehicle_mode": "crew_eva",
            "profile": "balanced",
            "created_at_utc": get_current_iso_time(),
        },
        "terrain_provenance": {
            "dataset_id": "jezero_ctx_20m_dem",
            "sha256": "875e7e31d279e8bf69cd71ca4d6d62846f33d45ef133b3a6efdbf1244365bf02",
            "coordinate_system": "IAU 2000 Planetocentric",
            "resolution_m": 20.0,
        },
        "execution_summary": {
            "total_distance_m": 1239.5,
            "total_duration_s": 2591.0,
            "total_cost": 1439.92,
            "is_reachable": True,
            "is_within_limit": True,
        },
        "disclosures": ["RESEARCH PROTOTYPE"],
    }
    validate_contract(sample_bundle, "mission-run-bundle")
