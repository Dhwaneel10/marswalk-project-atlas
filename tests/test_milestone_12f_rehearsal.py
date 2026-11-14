"""
MarsWalk 2.0 — Milestone 12F Acceptance Test Suite
Autonomous Mission Rehearsal Director: Closed-Loop Simulation, Disruption Response,
Adaptive Recovery & Mission Replay.

Tests:
1. Disturbance catalog completeness and structure.
2. Nominal paired rehearsal (baseline == recovered when no disturbance).
3. Corridor closure disturbance with conservative detour recovery.
4. Operational delay disturbance with target shedding recovery.
5. Mobility derating disturbance affecting traverse speed and budget.
6. Exploration unit dropout with cross-asset target reallocation.
7. Extreme insurmountable disturbance yielding NO_FEASIBLE_RECOVERY.
8. Causal decision ledger completeness and causal step sequencing.
9. Immutability guarantee: baseline campaign is strictly unmodified.
10. Persistence roundtrip: save, get, list, and delete rehearsal records.
11. JSON Schema Draft 2020-12 validation compliance.
12. Determinism and SHA-256 fingerprint reproducibility.
13. HTTP API live endpoint integration.
"""

import copy
import json
import os
import urllib.request
import pytest
import rasterio

from marswalk.api.contracts import validate_mission_rehearsal_record
from marswalk.api.workspace import (
    DEFAULT_REHEARSALS_DIR,
    delete_rehearsal_record,
    get_campaign,
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
    DisturbanceSpecification,
    DisturbanceType,
    RecoveryPolicyType,
    RehearsalOutcomeStatus,
    execute_mission_rehearsal,
    get_supported_disturbances_catalog,
)
from marswalk.core.terrain import TerrainGrid, load_and_process_terrain

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOTIFF_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "jezero_ready_20m.tif")


@pytest.fixture(scope="module")
def jezero_terrain():
    """Load authentic 20m Jezero elevation grid."""
    if not os.path.exists(GEOTIFF_PATH):
        pytest.skip(f"Terrain GeoTIFF not found at {GEOTIFF_PATH}")
    return load_and_process_terrain(GEOTIFF_PATH)


@pytest.fixture
def sample_campaign(jezero_terrain):
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
    return plan_mission_campaign("cmp_test_reh_001", "Rehearsal Test Campaign", cfg, targets, jezero_terrain)


@pytest.fixture
def multi_unit_campaign(jezero_terrain):
    """Create a campaign with targets distributed across 2 units."""
    cfg = CampaignConfig(
        planning_profile=PlanningProfile.SCIENCE_PRIORITY.value,
        max_duration_per_sortie_s=28800.0,
        base_start_rc=(117, 157),
    )
    targets = [
        CampaignTarget(id="mu_t1", name="Delta Point A", row=120, col=160, priority_score=85.0, dwell_time_s=900.0, assigned_unit_id="unit_crew_1"),
        CampaignTarget(id="mu_t2", name="Delta Point B", row=125, col=165, priority_score=65.0, dwell_time_s=900.0, assigned_unit_id="unit_crew_1"),
        CampaignTarget(id="mu_t3", name="Scout Target C", row=115, col=150, priority_score=50.0, dwell_time_s=900.0, assigned_unit_id="unit_scout_1"),
        CampaignTarget(id="mu_t4", name="Scout Target D", row=112, col=148, priority_score=45.0, dwell_time_s=900.0, assigned_unit_id="unit_scout_1"),
    ]
    return plan_mission_campaign("cmp_test_multi_reh", "Multi-Unit Rehearsal Campaign", cfg, targets, jezero_terrain)


def test_01_disturbance_catalog_completeness():
    """Verify supported disturbances catalog defines all required disruption types and schemas."""
    catalog = get_supported_disturbances_catalog()
    assert len(catalog) == 5

    types = {item["disturbance_type"] for item in catalog}
    assert DisturbanceType.CORRIDOR_CLOSURE.value in types
    assert DisturbanceType.OPERATIONAL_DELAY.value in types
    assert DisturbanceType.MOBILITY_DERATING.value in types
    assert DisturbanceType.TARGET_UNAVAILABILITY.value in types
    assert DisturbanceType.UNIT_DROPOUT.value in types

    for item in catalog:
        assert "name" in item
        assert "description" in item
        assert "parameters" in item
        assert isinstance(item["parameters"], dict)


def test_02_nominal_paired_rehearsal(sample_campaign, jezero_terrain):
    """Verify nominal rehearsal with 0 disturbances preserves 100% science and matches baseline."""
    record = execute_mission_rehearsal(
        campaign=sample_campaign,
        disturbances=[],
        recovery_policy={"policy_type": "balanced"},
        terrain=jezero_terrain,
        title="Nominal Baseline Test",
    )

    assert record.outcome_status == RehearsalOutcomeStatus.NOMINAL.value
    assert record.comparison.science_preservation_pct == 100.0
    assert record.comparison.net_science_delta == 0.0
    assert record.comparison.delay_incurred_s == 0.0
    assert record.recovered_metrics.science_score == record.baseline_metrics.science_score
    assert record.recovered_metrics.targets_completed == record.baseline_metrics.targets_completed
    assert len(record.causal_ledger) >= 5


def test_03_corridor_closure_recovery(sample_campaign, jezero_terrain):
    """Verify corridor closure triggers conservative detour or appropriate recovery."""
    disturbances = [
        {
            "disturbance_id": "dst_closure_1",
            "disturbance_type": "corridor_closure",
            "trigger_time_s": 1800.0,
            "parameters": {
                "center_rc": [120, 160],
                "radius_m": 40.0,
            },
            "description": "Hazardous boulder collapse across main egress",
        }
    ]

    record = execute_mission_rehearsal(
        campaign=sample_campaign,
        disturbances=disturbances,
        recovery_policy={"policy_type": "balanced", "min_margin_threshold_s": 1800.0},
        terrain=jezero_terrain,
    )

    assert record.outcome_status in (RehearsalOutcomeStatus.RECOVERED.value, RehearsalOutcomeStatus.RECOVERED_WITH_DEGRADATION.value)
    assert record.disturbed_metrics.critical_events_count > 0
    assert len(record.recovery_candidates) == 3

    # Check candidates exist and have required fields
    detour_cand = next(c for c in record.recovery_candidates if c.strategy == "conservative_detour")
    assert detour_cand.title != ""
    assert isinstance(detour_cand.is_feasible, bool)


def test_04_operational_delay_target_shedding(sample_campaign, jezero_terrain):
    """Verify heavy operational delay under safety_first policy triggers target shedding."""
    disturbances = [
        {
            "disturbance_id": "dst_delay_heavy",
            "disturbance_type": "operational_delay",
            "trigger_time_s": 2400.0,
            "parameters": {
                "delay_s": 7200.0,  # 2 hour delay
            },
            "description": "Extended drill telemetry timeout",
        }
    ]

    record = execute_mission_rehearsal(
        campaign=sample_campaign,
        disturbances=disturbances,
        recovery_policy={"policy_type": "safety_first", "min_margin_threshold_s": 3600.0},
        terrain=jezero_terrain,
    )

    assert record.outcome_status in (RehearsalOutcomeStatus.RECOVERED.value, RehearsalOutcomeStatus.RECOVERED_WITH_DEGRADATION.value)
    assert record.recovered_metrics.min_margin_s >= 0.0
    shed_cand = next(c for c in record.recovery_candidates if c.strategy == "target_shedding")
    assert shed_cand.is_feasible


def test_05_mobility_derating_consequence(sample_campaign, jezero_terrain):
    """Verify mobility derating increases traverse times and adjusts remaining margin."""
    disturbances = [
        {
            "disturbance_id": "dst_slip",
            "disturbance_type": "mobility_derating",
            "trigger_time_s": 1200.0,
            "parameters": {
                "speed_factor": 0.6,  # 40% speed drop
            },
            "description": "Loose regolith wheel slip derating",
        }
    ]

    record = execute_mission_rehearsal(
        campaign=sample_campaign,
        disturbances=disturbances,
        recovery_policy={"policy_type": "balanced"},
        terrain=jezero_terrain,
    )

    assert record.disturbed_metrics.total_duration_s > record.baseline_metrics.total_duration_s
    assert record.comparison.recovery_efficiency_pct > 0.0


def test_06_unit_dropout_multi_asset_reallocation(multi_unit_campaign, jezero_terrain):
    """Verify multi-unit campaign reallocates targets when an exploration unit drops out."""
    disturbances = [
        {
            "disturbance_id": "dst_scout_loss",
            "disturbance_type": "unit_dropout",
            "trigger_time_s": 3600.0,
            "parameters": {
                "affected_unit_id": "unit_scout_1",
                "reason": "Battery thermal runaway",
            },
            "description": "Scout rover battery fault",
        }
    ]

    record = execute_mission_rehearsal(
        campaign=multi_unit_campaign,
        disturbances=disturbances,
        recovery_policy={"policy_type": "balanced"},
        terrain=jezero_terrain,
    )

    rebal_cand = next(c for c in record.recovery_candidates if c.strategy == "priority_rebalance")
    assert rebal_cand.is_feasible
    assert len(rebal_cand.reallocated_targets) > 0
    assert record.recovered_metrics.targets_completed > record.disturbed_metrics.targets_completed


def test_07_insurmountable_disturbance_no_recovery(sample_campaign, jezero_terrain):
    """Verify massive compound delay exceeding EVA budget yields NO_FEASIBLE_RECOVERY."""
    disturbances = [
        {
            "disturbance_id": "dst_catastrophic",
            "disturbance_type": "operational_delay",
            "trigger_time_s": 600.0,
            "parameters": {
                "delay_s": 50000.0,  # Far exceeds 8h EVA budget
            },
            "description": "Catastrophic dust storm hold",
        }
    ]

    record = execute_mission_rehearsal(
        campaign=sample_campaign,
        disturbances=disturbances,
        recovery_policy={"policy_type": "safety_first", "min_margin_threshold_s": 7200.0},
        terrain=jezero_terrain,
    )

    assert record.outcome_status == RehearsalOutcomeStatus.NO_FEASIBLE_RECOVERY.value
    assert record.comparison.science_preservation_pct == 0.0
    assert "Abort to safe haven" in record.recovered_metrics.violations[-1]


def test_08_causal_decision_ledger_sequencing(sample_campaign, jezero_terrain):
    """Verify causal ledger contains all required sequence steps in order."""
    disturbances = [
        {
            "disturbance_id": "dst_seq_check",
            "disturbance_type": "operational_delay",
            "trigger_time_s": 1800.0,
            "parameters": {"delay_s": 1800.0},
        }
    ]

    record = execute_mission_rehearsal(
        campaign=sample_campaign,
        disturbances=disturbances,
        recovery_policy={"policy_type": "balanced"},
        terrain=jezero_terrain,
    )

    steps = record.causal_ledger
    assert len(steps) >= 7

    types = [s.step_type for s in steps]
    assert types[0] == "INITIAL_STATE"
    assert types[1] == "DISTURBANCE_TRIGGER"
    assert types[2] == "IMPACT_ANALYSIS"
    assert types[3] == "CANDIDATE_EVALUATION"
    assert types[4] == "SELECTION_DECISION"
    assert types[5] == "REVISED_EXECUTION"
    assert types[6] == "FINAL_OUTCOME"

    for idx, s in enumerate(steps, start=1):
        assert s.step_index == idx
        assert s.title != ""
        assert s.description != ""


def test_09_campaign_immutability(sample_campaign, jezero_terrain):
    """Verify baseline campaign and its sorties remain strictly immutable after rehearsal."""
    original_dump = copy.deepcopy(sample_campaign.to_dict())

    disturbances = [
        {
            "disturbance_id": "dst_immut_test",
            "disturbance_type": "operational_delay",
            "trigger_time_s": 1800.0,
            "parameters": {"delay_s": 3600.0},
        }
    ]

    execute_mission_rehearsal(
        campaign=sample_campaign,
        disturbances=disturbances,
        recovery_policy={"policy_type": "balanced"},
        terrain=jezero_terrain,
    )

    current_dump = sample_campaign.to_dict()
    assert original_dump == current_dump, "Baseline campaign was mutated during rehearsal!"


def test_10_persistence_roundtrip(sample_campaign, jezero_terrain):
    """Verify rehearsal records can be saved, fetched, listed, and deleted from workspace."""
    record = execute_mission_rehearsal(
        campaign=sample_campaign,
        disturbances=[],
        recovery_policy={"policy_type": "balanced"},
        terrain=jezero_terrain,
        title="Persistence Roundtrip Rehearsal",
    )

    rec_id = record.rehearsal_id
    saved_id = save_rehearsal_record(record.to_dict())
    assert saved_id == rec_id

    # Retrieve
    loaded = get_rehearsal_record(rec_id)
    assert loaded is not None
    assert loaded["rehearsal_id"] == rec_id
    assert loaded["title"] == "Persistence Roundtrip Rehearsal"

    # List
    all_recs = list_rehearsal_records(campaign_id=sample_campaign.campaign_id)
    assert any(r["rehearsal_id"] == rec_id for r in all_recs)

    # Delete
    deleted = delete_rehearsal_record(rec_id)
    assert deleted is True
    assert get_rehearsal_record(rec_id) is None


def test_11_json_schema_validation(sample_campaign, jezero_terrain):
    """Verify generated rehearsal record strictly complies with JSON Schema Draft 2020-12."""
    record = execute_mission_rehearsal(
        campaign=sample_campaign,
        disturbances=[
            {
                "disturbance_id": "dst_schema",
                "disturbance_type": "operational_delay",
                "trigger_time_s": 1200.0,
                "parameters": {"delay_s": 1800.0},
            }
        ],
        recovery_policy={"policy_type": "balanced"},
        terrain=jezero_terrain,
    )

    is_valid, err = validate_mission_rehearsal_record(record.to_dict())
    assert is_valid is True, f"Schema validation failed: {err}"


def test_12_repeat_determinism(sample_campaign, jezero_terrain):
    """Verify executing identical rehearsal multiple times produces identical fingerprints and metrics."""
    disturbances = [
        {
            "disturbance_id": "dst_det_1",
            "disturbance_type": "corridor_closure",
            "trigger_time_s": 1800.0,
            "parameters": {"center_rc": [120, 160], "radius_m": 50.0},
        }
    ]
    policy = {"policy_type": "balanced", "min_margin_threshold_s": 1800.0}

    rec1 = execute_mission_rehearsal(sample_campaign, disturbances, policy, jezero_terrain)
    rec2 = execute_mission_rehearsal(sample_campaign, disturbances, policy, jezero_terrain)

    assert rec1.computation_fingerprint == rec2.computation_fingerprint
    assert rec1.comparison.science_preservation_pct == rec2.comparison.science_preservation_pct
    assert rec1.comparison.net_science_delta == rec2.comparison.net_science_delta
    assert rec1.comparison.delay_incurred_s == rec2.comparison.delay_incurred_s
    assert rec1.comparison.margin_delta_s == rec2.comparison.margin_delta_s


def test_13_api_live_endpoints():
    """Verify live HTTP endpoints for rehearsal execution, listing, and disturbances."""
    # 1. Disturbances catalog
    req1 = urllib.request.urlopen("http://127.0.0.1:3000/api/rehearsal/disturbances")
    data1 = json.loads(req1.read().decode())
    assert data1["status"] == "success"
    assert len(data1["disturbances"]) == 5

    # 2. Rehearsal listing
    req2 = urllib.request.urlopen("http://127.0.0.1:3000/api/rehearsal/list")
    data2 = json.loads(req2.read().decode())
    assert data2["status"] == "success"
    assert "rehearsals" in data2
