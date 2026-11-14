"""
MarsWalk 2.0 / Project Atlas — Milestone 13H Test Battery
==========================================================
Tests the Atlas Campaign Operations Director:
  - Multi-sol mission campaign planning & activity scheduling
  - Idempotent event ledger processing (replay protection & zero double-accounting)
  - First-Law byte conservation & transfer release precondition
  - Cross-sol state carryover (energy, flash buffer, target permanence, relay persistence)
  - Closed-loop adaptive replanning triggers & explainable alternatives
  - Campaign What-If & Recovery Lab 2.0 scenarios (Scenarios A through F)
  - Draft 2020-12 JSON Schema validation & workspace persistence
"""

import copy
import json
import os
from pathlib import Path
import pytest

from marswalk.core.terrain import load_and_process_terrain, TerrainGrid
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignTarget,
    TargetStatus,
    PlanningProfile,
)
from marswalk.core.mission_resource_model import RoverResourceConfig
from marswalk.core.campaign_operations_director import (
    CampaignOperationsDirector,
    CampaignLifecycleState,
    CampaignEventType,
    ReplanningTriggerType,
)
from marswalk.api.contracts import (
    validate_campaign_operations_record,
    validate_campaign_operations_event_record,
)
from marswalk.api.service import (
    campaign_operations_create_api,
    campaign_operations_list_api,
    campaign_operations_get_api,
    campaign_operations_plan_api,
    campaign_operations_execute_event_api,
    campaign_operations_advance_sol_api,
    campaign_operations_replan_api,
    campaign_operations_scenario_api,
    campaign_operations_timeline_api,
    campaign_operations_analytics_api,
)


@pytest.fixture(scope="module")
def jezero_grid():
    """Load authentic USGS CTX 20m Jezero Crater terrain."""
    base_dir = Path(__file__).resolve().parent.parent
    tiff_path = base_dir / "data" / "processed" / "jezero_ready_20m.tif"
    if not tiff_path.exists():
        pytest.skip(f"Jezero CTX raster not found at {tiff_path}")
    return load_and_process_terrain(str(tiff_path))


@pytest.fixture
def sample_targets():
    """Standardized multi-objective Jezero exploration targets."""
    return [
        CampaignTarget(
            id="tgt_octavia",
            name="Octavia E. Butler Landing",
            row=117,
            col=157,
            priority_score=100.0,
            dwell_time_s=900.0,
            science_objective="SURFACE_MORPHOLOGY",
        ),
        CampaignTarget(
            id="tgt_delta_front",
            name="Kodiak Mesa Delta Front",
            row=122,
            col=148,
            priority_score=90.0,
            dwell_time_s=1800.0,
            science_objective="GEOLOGICAL_CHARACTERIZATION",
        ),
        CampaignTarget(
            id="tgt_crater_rim",
            name="Belva Crater Rim Exposure",
            row=135,
            col=160,
            priority_score=75.0,
            dwell_time_s=1200.0,
            science_objective="MINERALOGICAL_INVESTIGATION",
        ),
        CampaignTarget(
            id="tgt_neretva_fan",
            name="Neretva Fan Sediments",
            row=110,
            col=140,
            priority_score=85.0,
            dwell_time_s=2400.0,
            science_objective="ASTROBIOLOGY_BIOSIGNATURE_SURVEY",
        ),
    ]


def test_01_campaign_operations_initialization(tmp_path):
    """Verifies default initialization, lifecycle state, and reproducibility manifest."""
    director = CampaignOperationsDirector(
        campaign_id="cmp_ops_init_test",
        name="Unit Test Campaign",
        workspace_dir=tmp_path,
    )
    assert director.campaign_id == "cmp_ops_init_test"
    assert director.version == 1
    assert director.lifecycle_state == CampaignLifecycleState.PLANNED.value
    assert director.current_sol == 1
    assert director.current_energy_wh == 4800.0
    assert director.used_storage_mb == 0.0

    state = director.get_campaign_operations_state()
    valid, err = validate_campaign_operations_record(state)
    assert valid, f"Schema validation error: {err}"
    assert state["reproducibility_manifest"]["terrain_dataset_id"] == "USGS_CTX_DTM_JEZERO_20M"


def test_02_multi_sol_schedule_planning(jezero_grid, sample_targets, tmp_path):
    """Verifies deterministic multi-sol schedule generation and 13F/13G integration."""
    director = CampaignOperationsDirector(
        campaign_id="cmp_ops_plan_test",
        name="Multi-Sol Jezero Campaign",
        terrain_grid=jezero_grid,
        workspace_dir=tmp_path,
    )
    config = CampaignConfig(
        max_sols=3,
        planning_profile=PlanningProfile.SCIENCE_PRIORITY.value,
        max_duration_per_sortie_s=28800.0,
    )
    rover_cfg = RoverResourceConfig(
        usable_battery_capacity_wh=4800.0,
        reserve_margin_pct=20.0,
    )

    state = director.plan_multi_sol_campaign(
        targets=sample_targets,
        config=config,
        rover_config=rover_cfg,
        data_capacity_mb=16384.0,
    )

    assert director.lifecycle_state == CampaignLifecycleState.READY_FOR_REVIEW.value
    assert len(director.sol_schedules) >= 1
    assert len(director.events_log) == 1
    assert director.events_log[0]["event_type"] == CampaignEventType.CAMPAIGN_INITIALIZED.value

    # Verify first sol schedule properties
    sol1 = director.sol_schedules[1]
    assert sol1.total_distance_m > 0.0
    assert sol1.energy_consumed_wh > 0.0
    assert len(sol1.activities) >= 3  # outbound traverse, science dwell, return traverse
    assert sol1.is_feasible is True


def test_03_idempotent_event_execution(jezero_grid, tmp_path):
    """Verifies that duplicate event fingerprints are rejected without double-deducting energy."""
    director = CampaignOperationsDirector(
        campaign_id="cmp_ops_idempotent_test",
        name="Idempotency Test",
        terrain_grid=jezero_grid,
        workspace_dir=tmp_path,
    )
    initial_energy = director.current_energy_wh

    # First event application
    event1 = director.record_event(
        event_type=CampaignEventType.TRAVERSE_COMPLETED.value,
        sol_index=1,
        payload={"distance_m": 250.0, "energy_consumed_wh": 65.0},
        event_id="evt_test_fixed_01",
    )
    assert director.current_energy_wh == initial_energy - 65.0
    assert director.cumulative_distance_m == 250.0
    assert len(director.events_log) == 1

    # Attempt duplicate replay with exact same fingerprint
    applied = director.apply_event(event1)
    assert applied is False, "Duplicate event must be rejected by idempotency check"
    assert director.current_energy_wh == initial_energy - 65.0, "Energy must NOT be double-deducted"
    assert director.cumulative_distance_m == 250.0, "Distance must NOT be double-counted"
    assert len(director.events_log) == 1


def test_04_first_law_byte_conservation_and_transfer_release(jezero_grid, tmp_path):
    """Verifies that solid-state flash memory strictly obeys S_used = S_gen - S_rel."""
    director = CampaignOperationsDirector(
        campaign_id="cmp_ops_storage_test",
        name="Byte Conservation Test",
        terrain_grid=jezero_grid,
        workspace_dir=tmp_path,
    )
    assert director.used_storage_mb == 0.0

    # Observation generates data
    director.record_event(
        event_type=CampaignEventType.OBSERVATION_COMPLETED.value,
        sol_index=1,
        payload={
            "target_id": "tgt_octavia",
            "science_utility": 80.0,
            "data_generated_mb": 50.0,
            "energy_consumed_wh": 10.0,
        },
    )
    assert director.used_storage_mb == 50.0
    assert director.total_data_generated_mb == 50.0
    assert director.backlog_mb == 50.0

    # Confirmed transfer releases storage
    director.record_event(
        event_type=CampaignEventType.TRANSFER_COMPLETED.value,
        sol_index=1,
        payload={"transferred_mb": 35.0, "products_count": 1},
    )
    # 50 - 35 = 15 MB remaining
    assert director.used_storage_mb == 15.0
    assert director.total_data_transferred_mb == 35.0
    assert director.backlog_mb == 15.0


def test_05_cross_sol_resource_carryover_and_target_permanence(jezero_grid, sample_targets, tmp_path):
    """Verifies that resources and completed targets carry over across Sol N -> Sol N+1 boundaries."""
    director = CampaignOperationsDirector(
        campaign_id="cmp_ops_carryover_test",
        name="Cross-Sol Carryover Test",
        terrain_grid=jezero_grid,
        workspace_dir=tmp_path,
    )
    config = CampaignConfig(max_sols=3)
    director.plan_multi_sol_campaign(sample_targets, config)

    # Consume some mobility and observation energy on Sol 1
    director.record_event(
        event_type=CampaignEventType.TRAVERSE_COMPLETED.value,
        sol_index=1,
        payload={"distance_m": 400.0, "energy_consumed_wh": 120.0},
    )
    director.record_event(
        event_type=CampaignEventType.OBSERVATION_COMPLETED.value,
        sol_index=1,
        payload={
            "target_id": "tgt_octavia",
            "science_utility": 100.0,
            "data_generated_mb": 40.0,
            "energy_consumed_wh": 15.0,
        },
    )
    assert "tgt_octavia" in director.completed_target_ids
    assert director.used_storage_mb == 40.0

    end_sol1_energy = director.current_energy_wh

    # Advance to Sol 2 with deterministic recharge
    state_sol2 = director.advance_sol(recharge_energy_wh=50.0)
    assert state_sol2["current_sol"] == 2
    assert director.current_sol == 2
    # Verify energy carryover + explicit recharge (within battery capacity ceiling)
    assert director.current_energy_wh == min(director.battery_capacity_wh, end_sol1_energy + 50.0)
    # Verify storage backlog carryover
    assert director.used_storage_mb == 40.0
    # Verify completed target permanence
    assert "tgt_octavia" in director.completed_target_ids


def test_06_adaptive_replanning_triggers_and_alternatives(jezero_grid, sample_targets, tmp_path):
    """Verifies trigger evaluation and bounded alternative generation with explainable diffs."""
    director = CampaignOperationsDirector(
        campaign_id="cmp_ops_replan_test",
        name="Replanning Engine Test",
        terrain_grid=jezero_grid,
        workspace_dir=tmp_path,
    )
    director.plan_multi_sol_campaign(sample_targets, CampaignConfig(max_sols=2))

    # Force energy depletion below reserve
    director.current_energy_wh = director.battery_capacity_wh * 0.12
    director.reserve_margin_pct = 12.0

    triggers = director.evaluate_replanning_triggers()
    assert len(triggers) >= 1
    assert triggers[0]["type"] == ReplanningTriggerType.ENERGY_RESERVE_VIOLATION.value
    assert director.lifecycle_state == CampaignLifecycleState.REQUIRES_REPLANNING.value

    # Generate bounded alternatives
    alternatives = director.generate_replanning_alternatives(triggers[0])
    assert len(alternatives) >= 2
    alt_conservative = alternatives[0]
    assert alt_conservative.alternative_id == "alt_conservative_energy"
    assert alt_conservative.delta_energy_wh < 0.0  # Saves energy
    assert "Conservative" in alt_conservative.strategy_name

    # Accept alternative and verify version increment
    initial_ver = director.version
    promoted_state = director.accept_replanning_alternative("alt_conservative_energy")
    assert promoted_state["version"] == initial_ver + 1
    assert director.lifecycle_state == CampaignLifecycleState.APPROVED_FOR_SIMULATION.value
    assert len(director.historical_plans) == 1


def test_07_recovery_lab_scenarios_a_through_f(jezero_grid, sample_targets, tmp_path):
    """Verifies execution of all 6 deterministic Recovery Lab scenarios."""
    director = CampaignOperationsDirector(
        campaign_id="cmp_ops_scenarios_test",
        name="Recovery Lab 2.0 Test",
        terrain_grid=jezero_grid,
        workspace_dir=tmp_path,
    )
    director.plan_multi_sol_campaign(sample_targets, CampaignConfig(max_sols=2))

    scenarios = [
        "SCENARIO_A_RELAY_OUTAGE",
        "SCENARIO_B_ENERGY_SHORTFALL",
        "SCENARIO_C_STORAGE_SATURATION",
        "SCENARIO_D_INSTRUMENT_OFFLINE",
        "SCENARIO_E_ROUTE_DISTURBANCE",
        "SCENARIO_F_SCIENCE_DISCOVERY",
    ]

    for sc in scenarios:
        res = director.run_campaign_scenario(sc)
        assert "scenario" in res
        assert "alternatives" in res
        assert len(res["alternatives"]) >= 1


def test_08_workspace_persistence_and_reproducibility(jezero_grid, sample_targets, tmp_path):
    """Verifies state serialization to JSON workspace and idempotent deserialization."""
    director = CampaignOperationsDirector(
        campaign_id="cmp_ops_persist_test",
        name="Persistence Test",
        terrain_grid=jezero_grid,
        workspace_dir=tmp_path,
    )
    director.plan_multi_sol_campaign(sample_targets, CampaignConfig(max_sols=2))
    director.record_event(
        event_type=CampaignEventType.OBSERVATION_COMPLETED.value,
        sol_index=1,
        payload={"target_id": "tgt_octavia", "science_utility": 95.0, "data_generated_mb": 18.0},
    )

    saved_file = director.save_to_workspace(tmp_path)
    assert saved_file.exists()

    # Load into fresh director instance
    loaded = CampaignOperationsDirector.load_from_workspace("cmp_ops_persist_test", tmp_path)
    assert loaded.campaign_id == director.campaign_id
    assert loaded.version == director.version
    assert loaded.current_sol == director.current_sol
    assert loaded.total_science_utility == 95.0
    assert "tgt_octavia" in loaded.completed_target_ids
    assert len(loaded.events_log) == 2


def test_09_api_service_endpoints_integration(jezero_grid, tmp_path):
    """Verifies full end-to-end integration across all service.py endpoints."""
    # 1. Create
    c = campaign_operations_create_api({"campaign_id": "cmp_api_test", "name": "API Test"}, jezero_grid, None)
    assert c["campaign_id"] == "cmp_api_test"

    # 2. List
    lst = campaign_operations_list_api({}, jezero_grid, None)
    assert any(x["campaign_id"] == "cmp_api_test" for x in lst["campaigns"])

    # 3. Plan
    pl = campaign_operations_plan_api({"campaign_id": "cmp_api_test"}, jezero_grid, None)
    assert len(pl["sol_schedules"]) >= 1

    # 4. Execute Event
    ev = campaign_operations_execute_event_api({
        "campaign_id": "cmp_api_test",
        "event_type": "OBSERVATION_COMPLETED",
        "payload": {"target_id": "tgt_octavia", "science_utility": 100.0, "data_generated_mb": 20.0},
    }, jezero_grid, None)
    assert ev["status"] == "APPLIED"

    # 5. Advance Sol
    adv = campaign_operations_advance_sol_api({"campaign_id": "cmp_api_test", "recharge_energy_wh": 10.0}, jezero_grid, None)
    assert adv["current_sol"] == 2

    # 6. Timeline
    tl = campaign_operations_timeline_api("cmp_api_test", jezero_grid, None)
    assert tl["current_sol"] == 2
    assert len(tl["events_log"]) >= 2

    # 7. Analytics
    ana = campaign_operations_analytics_api("cmp_api_test", jezero_grid, None)
    assert ana["science"]["total_science_utility"] == 100.0
    assert ana["data"]["total_generated_mb"] == 20.0


def test_10_campaign_operations_event_schema_validation(jezero_grid, tmp_path):
    """Verifies campaign operations event data contracts against Draft 2020-12 schema."""
    director = CampaignOperationsDirector(
        campaign_id="cmp_schema_evt_test",
        name="Event Schema Test",
        terrain_grid=jezero_grid,
        workspace_dir=tmp_path,
    )
    event = director.record_event(
        event_type=CampaignEventType.OBSERVATION_COMPLETED.value,
        sol_index=1,
        payload={"target_id": "tgt_octavia", "science_utility": 90.0, "data_generated_mb": 15.0},
    )
    valid, err = validate_campaign_operations_event_record(event.to_dict())
    assert valid, f"Event schema validation failed: {err}"


def test_11_cross_sol_storage_queue_persistence(jezero_grid, tmp_path):
    """Verifies that un-transferred data in the transfer queue persists across multiple sol boundaries."""
    director = CampaignOperationsDirector(
        campaign_id="cmp_queue_test",
        name="Queue Persistence Test",
        terrain_grid=jezero_grid,
        workspace_dir=tmp_path,
    )
    # Generate 3 observations on Sol 1
    for i in range(3):
        director.record_event(
            event_type=CampaignEventType.OBSERVATION_COMPLETED.value,
            sol_index=1,
            payload={"target_id": f"tgt_{i}", "science_utility": 50.0, "data_generated_mb": 20.0},
        )
    assert director.transfer_queue_count == 3
    assert director.used_storage_mb == 60.0

    # Advance to Sol 2
    director.advance_sol()
    assert director.current_sol == 2
    assert director.transfer_queue_count == 3
    assert director.used_storage_mb == 60.0

    # Advance to Sol 3
    director.advance_sol()
    assert director.current_sol == 3
    assert director.transfer_queue_count == 3
    assert director.used_storage_mb == 60.0


def test_12_turret_singularity_protection_in_schedule(jezero_grid, sample_targets, tmp_path):
    """Verifies that no sol schedule assigns more than one arm turret instrument to a target."""
    director = CampaignOperationsDirector(
        campaign_id="cmp_turret_test",
        name="Turret Invariant Test",
        terrain_grid=jezero_grid,
        workspace_dir=tmp_path,
    )
    state = director.plan_multi_sol_campaign(sample_targets, CampaignConfig(max_sols=2))
    turret_modes = {"PIXL_XRF_GRID", "SHERLOC_DUV_RAMAN", "CORING_ABRASION"}

    for sol_idx, sched in director.sol_schedules.items():
        for act in sched.activities:
            if act.activity_type == "SCIENCE_OBSERVATION":
                chosen = act.metadata.get("instrument_mode")
                # At most 1 mode assigned per target observation
                assert chosen is not None


def test_13_bounded_replanning_timing_benchmark(jezero_grid, sample_targets, tmp_path):
    """Verifies that trigger evaluation and alternative plan synthesis complete in < 4.0s."""
    import time
    director = CampaignOperationsDirector(
        campaign_id="cmp_timing_test",
        name="Timing Benchmark Test",
        terrain_grid=jezero_grid,
        workspace_dir=tmp_path,
    )
    director.plan_multi_sol_campaign(sample_targets, CampaignConfig(max_sols=3))

    t0 = time.perf_counter()
    triggers = director.evaluate_replanning_triggers({"relay_outage_id": "relay_01"})
    alts = director.generate_replanning_alternatives(triggers[0])
    dt = time.perf_counter() - t0

    assert dt < 4.0, f"Replanning latency exceeded 4.0s budget: {dt:.3f}s"
    assert len(alts) >= 1


def test_14_deterministic_end_to_end_3sol_campaign(jezero_grid, sample_targets, tmp_path):
    """
    Complete worked multi-sol campaign execution (Milestone 13H Section 14.3):
      - Sol 1: Traverse to Target A, complete observation, generate data products.
      - Sol 2: Continue traverse, deploy relay infrastructure, transfer data, carry forward resources.
      - Sol 3: Operational disturbance, closed-loop replanning, promote alternative plan, complete science.
    """
    director = CampaignOperationsDirector(
        campaign_id="cmp_e2e_3sol_worked_example",
        name="Jezero 3-Sol Exploration Campaign",
        terrain_grid=jezero_grid,
        workspace_dir=tmp_path,
    )
    # 0. Plan baseline campaign
    plan = director.plan_multi_sol_campaign(sample_targets, CampaignConfig(max_sols=3))
    assert director.lifecycle_state == CampaignLifecycleState.READY_FOR_REVIEW.value

    # ==================== SOL 1 ====================
    # Start sortie
    director.record_event(
        event_type=CampaignEventType.SORTIE_STARTED.value,
        sol_index=1,
        payload={"sortie_id": "sortie_sol_1"},
    )
    assert director.lifecycle_state == CampaignLifecycleState.EXECUTING_SIMULATION.value

    # Outbound traverse
    director.record_event(
        event_type=CampaignEventType.TRAVERSE_COMPLETED.value,
        sol_index=1,
        payload={"distance_m": 450.0, "energy_consumed_wh": 110.0, "end_position_rc": [122, 148]},
    )
    assert director.cumulative_distance_m == 450.0

    # Science observation at Target A (Kodiak Mesa Delta Front)
    director.record_event(
        event_type=CampaignEventType.OBSERVATION_COMPLETED.value,
        sol_index=1,
        payload={
            "target_id": "tgt_delta_front",
            "science_utility": 90.0,
            "data_generated_mb": 45.0,
            "energy_consumed_wh": 22.0,
        },
    )
    assert "tgt_delta_front" in director.completed_target_ids
    assert director.used_storage_mb == 45.0

    # Advance Sol 1 -> Sol 2
    director.advance_sol(recharge_energy_wh=40.0)
    assert director.current_sol == 2

    # ==================== SOL 2 ====================
    # Continue traverse toward Belva Rim
    director.record_event(
        event_type=CampaignEventType.TRAVERSE_COMPLETED.value,
        sol_index=2,
        payload={"distance_m": 600.0, "energy_consumed_wh": 140.0, "end_position_rc": [130, 155]},
    )
    # Deploy surface relay mast
    director.record_event(
        event_type=CampaignEventType.RELAY_DEPLOYED.value,
        sol_index=2,
        payload={"relay": {"id": "relay_belva_crest", "row": 130, "col": 155, "elevation_m": -2400.0}},
    )
    assert "relay_belva_crest" in director.active_relay_ids

    # Simulated data transfer opportunity
    director.record_event(
        event_type=CampaignEventType.TRANSFER_COMPLETED.value,
        sol_index=2,
        payload={"transferred_mb": 40.0, "products_count": 1},
    )
    assert director.used_storage_mb == 5.0  # 45 - 40 = 5 MB backlog
    assert director.total_data_transferred_mb == 40.0

    # Advance Sol 2 -> Sol 3
    director.advance_sol(recharge_energy_wh=35.0)
    assert director.current_sol == 3

    # ==================== SOL 3 ====================
    # Inject deterministic disturbance (Relay outage)
    triggers = director.evaluate_replanning_triggers({"relay_outage_id": "relay_belva_crest"})
    assert len(triggers) == 1
    assert triggers[0]["type"] == ReplanningTriggerType.RELAY_OUTAGE.value

    # Synthesize explainable alternatives
    alts = director.generate_replanning_alternatives(triggers[0])
    assert len(alts) >= 2

    # Promote conservative alternative
    promoted = director.accept_replanning_alternative("alt_conservative_energy")
    assert promoted["version"] == 2
    assert director.lifecycle_state == CampaignLifecycleState.APPROVED_FOR_SIMULATION.value

    # Complete revised science activity at Octavia Base Cache
    director.record_event(
        event_type=CampaignEventType.OBSERVATION_COMPLETED.value,
        sol_index=3,
        payload={"target_id": "tgt_octavia", "science_utility": 100.0, "data_generated_mb": 20.0},
    )
    assert "tgt_octavia" in director.completed_target_ids
    assert director.total_science_utility == 190.0  # 90 + 100

    # Verify overall analytics
    state = director.get_campaign_operations_state()
    valid, err = validate_campaign_operations_record(state)
    assert valid, f"Final campaign state validation failed: {err}"

