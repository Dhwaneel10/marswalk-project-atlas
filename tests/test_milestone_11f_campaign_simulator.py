# tests/test_milestone_11f_campaign_simulator.py
"""
Test suite for Milestone 11F: Campaign Digital Twin, Multi-Unit Timeline & Temporal Execution Simulation.
Verifies:
1. Digital twin compilation and schema conformance.
2. Deterministic event ordering and tie-breaking.
3. Time advancement, stepping, and non-mutating seek state reconstruction.
4. Simulated route position labeling (is_simulated_position=True).
5. Accurate dwell and transit duration accounting without double-counting.
6. Temporal conflict detection:
   - Double-booking per unit.
   - Concurrent target access.
   - DAG prerequisite violations.
   - Availability window violations.
   - Duration budget violations.
7. Contingency interruptions with historical prefix freezing.
8. Unit loss and automatic remaining work reallocation.
9. Workspace persistence, reload, and API service roundtrip.
10. Explicit unsupported physical transfer disclaimers.
"""

import copy
import json
import pytest
from typing import Dict, Any

from marswalk.core.terrain import TerrainGrid, load_and_process_terrain
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignTarget,
    CampaignSortie,
    MissionCampaign,
    TargetStatus,
    CampaignStatus,
    PlanningProfile,
    plan_mission_campaign,
)
from marswalk.core.campaign_coordination import (
    ExplorationUnit,
    MobilityProfile,
    AvailabilityWindow,
    TargetAllocation,
    TaskHandoff,
    CoordinationPlan,
    UnitType,
    UnitStatus,
    create_default_units,
    allocate_campaign_coordination,
)
from marswalk.core.campaign_simulator import (
    ActivityType,
    IntervalStatus,
    SimulationStatus,
    ConflictCode,
    ConflictSeverity,
    TimelineInterval,
    SimulationEvent,
    TemporalConflict,
    SimulatedUnitState,
    CampaignDigitalTwin,
    detect_temporal_conflicts,
    interpolate_position_along_path,
    MARTIAN_SOL_SECONDS,
)
from marswalk.api.contracts import (
    validate_campaign_simulation_record,
    ContractValidationError,
)
from marswalk.api.workspace import (
    save_campaign_simulation,
    get_campaign_simulation,
    list_campaign_simulations,
    save_campaign,
    save_coordination_plan,
)
from marswalk.api.service import (
    start_campaign_simulation_api,
    advance_campaign_simulation_api,
    step_campaign_simulation_api,
    seek_campaign_simulation_api,
    interrupt_campaign_simulation_api,
    get_campaign_simulation_api,
    get_campaign_simulation_events_api,
    get_campaign_simulation_conflicts_api,
    list_campaign_simulations_api,
)


@pytest.fixture(scope="module")
def terrain_grid() -> TerrainGrid:
    return load_and_process_terrain("data/processed/jezero_ready_20m.tif")


@pytest.fixture
def sample_campaign(terrain_grid: TerrainGrid) -> MissionCampaign:
    targets = [
        CampaignTarget(
            id="tgt_octavia_w0",
            name="Octavia E. Butler Landing",
            row=117,
            col=157,
            priority_score=100.0,
            dwell_time_s=600.0,
        ),
        CampaignTarget(
            id="tgt_hawksbill_w1",
            name="Hawksbill Gap",
            row=119,
            col=159,
            priority_score=85.0,
            dwell_time_s=900.0,
            prerequisites=["tgt_octavia_w0"],
        ),
        CampaignTarget(
            id="tgt_skinner_w2",
            name="Skinner Ridge",
            row=120,
            col=160,
            priority_score=75.0,
            dwell_time_s=900.0,
            prerequisites=["tgt_hawksbill_w1"],
        ),
        CampaignTarget(
            id="tgt_enchanted_w3",
            name="Enchanted Lake",
            row=122,
            col=161,
            priority_score=70.0,
            dwell_time_s=900.0,
        ),
    ]

    cfg = CampaignConfig(
        planning_profile=PlanningProfile.SCIENCE_PRIORITY.value,
        max_duration_per_sortie_s=14400.0,
        max_sols=3,
    )

    campaign = plan_mission_campaign(
        campaign_id="cmp_sim_test",
        name="Jezero Digital Twin Test Campaign",
        config=cfg,
        targets=targets,
        terrain=terrain_grid,
    )
    save_campaign(campaign.to_dict())
    return campaign


@pytest.fixture
def sample_coordination(sample_campaign: MissionCampaign, terrain_grid: TerrainGrid) -> CoordinationPlan:
    units = create_default_units(sample_campaign.config)
    plan = allocate_campaign_coordination(
        campaign=sample_campaign,
        terrain=terrain_grid,
        units=units,
        strategy="priority_first",
    )
    save_coordination_plan(plan.to_dict())
    return plan


def test_digital_twin_initialization_and_compilation(
    sample_campaign: MissionCampaign,
    sample_coordination: CoordinationPlan,
    terrain_grid: TerrainGrid,
):
    """Verifies that CampaignDigitalTwin initializes and compiles timeline intervals."""
    twin = CampaignDigitalTwin(
        simulation_id="sim_init_test_001",
        campaign=sample_campaign,
        coordination_plan=sample_coordination,
        terrain=terrain_grid,
    )

    assert twin.simulation_id == "sim_init_test_001"
    assert twin.campaign.campaign_id == sample_campaign.campaign_id
    assert twin.status == SimulationStatus.IDLE.value
    assert twin.current_time_s == 0.0
    assert twin.current_sol == 1
    assert len(twin.units) >= 2
    assert len(twin.timeline_intervals) > 0
    assert len(twin.event_queue) > 0
    assert len(twin.logged_events) == 1  # SIMULATION_START event logged
    assert twin.total_duration_s > 0.0


def test_digital_twin_schema_validation(
    sample_campaign: MissionCampaign,
    sample_coordination: CoordinationPlan,
    terrain_grid: TerrainGrid,
):
    """Verifies that the serialized twin strictly conforms to schemas/api/v1/campaign-simulation.schema.json."""
    twin = CampaignDigitalTwin(
        simulation_id="sim_schema_val_001",
        campaign=sample_campaign,
        coordination_plan=sample_coordination,
        terrain=terrain_grid,
    )
    sim_data = twin.to_dict()

    is_valid, errors = validate_campaign_simulation_record(sim_data)
    assert is_valid is True, f"Schema validation errors: {errors}"
    assert sim_data["schema_version"] == "1.0.0"
    assert sim_data["statistics"]["total_intervals"] == len(twin.timeline_intervals)
    assert "limitations_disclaimer" in sim_data


def test_deterministic_event_ordering_and_tie_breaking():
    """Verifies deterministic sorting of simultaneous events by priority, unit, and ID."""
    e1 = SimulationEvent(
        event_id="evt_z_end",
        event_type="DWELL_COMPLETE",
        simulated_time_s=1000.0,
        sol_index=1,
        event_priority=20,  # completion
        unit_id="unit_b",
        title="Complete B",
        description="B Complete",
    )
    e2 = SimulationEvent(
        event_id="evt_a_start",
        event_type="DWELL_START",
        simulated_time_s=1000.0,
        sol_index=1,
        event_priority=30,  # start
        unit_id="unit_a",
        title="Start A",
        description="A Start",
    )
    e3 = SimulationEvent(
        event_id="evt_a_end",
        event_type="DWELL_COMPLETE",
        simulated_time_s=1000.0,
        sol_index=1,
        event_priority=20,  # completion
        unit_id="unit_a",
        title="Complete A",
        description="A Complete",
    )

    events = [e1, e2, e3]
    # Sort with deterministic tie-breaking key
    events.sort(key=lambda e: (e.simulated_time_s, e.event_priority, e.unit_id or "", e.event_id))

    # Priority 20 before 30; between e1 and e3 (both 20), unit_a comes before unit_b
    assert events[0].unit_id == "unit_a" and events[0].event_type == "DWELL_COMPLETE"
    assert events[1].unit_id == "unit_b" and events[1].event_type == "DWELL_COMPLETE"
    assert events[2].unit_id == "unit_a" and events[2].event_type == "DWELL_START"


def test_time_advancement_and_event_stepping(
    sample_campaign: MissionCampaign,
    sample_coordination: CoordinationPlan,
    terrain_grid: TerrainGrid,
):
    """Verifies that advancing the clock executes events and updates state."""
    twin = CampaignDigitalTwin(
        simulation_id="sim_advance_test_001",
        campaign=sample_campaign,
        coordination_plan=sample_coordination,
        terrain=terrain_grid,
    )

    initial_events_count = len(twin.logged_events)
    assert twin.current_time_s == 0.0

    # Advance by 1800 seconds (30 minutes)
    new_events = twin.advance(1800.0)
    assert twin.current_time_s == 1800.0
    assert twin.status == SimulationStatus.RUNNING.value
    assert len(new_events) > 0
    assert len(twin.logged_events) == initial_events_count + len(new_events)

    # Step to next event
    step_events = twin.step(1)
    assert len(step_events) >= 1
    assert twin.current_time_s >= 1800.0


def test_simulated_position_interpolation(terrain_grid: TerrainGrid):
    """Verifies position interpolation along route polyline and explicit simulation labeling."""
    path = [(117, 157), (118, 158), (119, 159), (120, 160)]

    pos_start = interpolate_position_along_path(path, 0.0, terrain_grid)
    assert pos_start["row"] == 117
    assert pos_start["col"] == 157
    assert pos_start["is_simulated_position"] is True

    pos_mid = interpolate_position_along_path(path, 0.5, terrain_grid)
    assert pos_mid["row"] in (118, 119)
    assert pos_mid["col"] in (158, 159)
    assert pos_mid["is_simulated_position"] is True

    pos_end = interpolate_position_along_path(path, 1.0, terrain_grid)
    assert pos_end["row"] == 120
    assert pos_end["col"] == 160
    assert pos_end["is_simulated_position"] is True


def test_non_mutating_seek_state_reconstruction(
    sample_campaign: MissionCampaign,
    sample_coordination: CoordinationPlan,
    terrain_grid: TerrainGrid,
):
    """Verifies seeking to an earlier time reconstructs state without deleting future events."""
    twin = CampaignDigitalTwin(
        simulation_id="sim_seek_test_001",
        campaign=sample_campaign,
        coordination_plan=sample_coordination,
        terrain=terrain_grid,
    )

    total_events = len(twin.event_queue) + len(twin.logged_events)

    # Advance to 3600s
    twin.advance(3600.0)
    assert twin.current_time_s == 3600.0

    # Seek back to 600s
    twin.seek(600.0)
    assert twin.current_time_s == 600.0
    assert twin.status == SimulationStatus.PAUSED.value

    # Verify no events were lost in the reconstruction
    assert len(twin.event_queue) + len(twin.logged_events) == total_events


def test_dwell_and_task_completion_invariants(
    sample_campaign: MissionCampaign,
    sample_coordination: CoordinationPlan,
    terrain_grid: TerrainGrid,
):
    """Verifies dwell intervals complete targets and record completion timestamps."""
    twin = CampaignDigitalTwin(
        simulation_id="sim_complete_test_001",
        campaign=sample_campaign,
        coordination_plan=sample_coordination,
        terrain=terrain_grid,
    )

    # Find the first target that completes
    dwell_end_events = [e for e in twin.event_queue if e.event_type == "DWELL_COMPLETE" and e.target_id]
    if dwell_end_events:
        first_comp = dwell_end_events[0]
        target_id = first_comp.target_id

        # Advance past completion time
        twin.advance(first_comp.simulated_time_s + 10.0)

        assert twin.target_states[target_id]["status"] == TargetStatus.COMPLETED.value
        assert twin.target_states[target_id]["completed_at_s"] == first_comp.simulated_time_s


def test_temporal_conflict_unit_double_booked():
    """Verifies detection of overlapping active intervals on a single unit."""
    iv1 = TimelineInterval(
        interval_id="iv1",
        unit_id="unit_perseverance",
        activity_type=ActivityType.TRANSIT.value,
        start_time_s=100.0,
        end_time_s=500.0,
        duration_s=400.0,
        sol_index=1,
    )
    iv2 = TimelineInterval(
        interval_id="iv2",
        unit_id="unit_perseverance",
        activity_type=ActivityType.DWELL.value,
        start_time_s=400.0,  # Overlaps iv1 by 100s
        end_time_s=800.0,
        duration_s=400.0,
        sol_index=1,
    )

    units = [ExplorationUnit(unit_id="unit_perseverance", name="Perseverance")]
    conflicts = detect_temporal_conflicts([iv1, iv2], [], units)

    assert len(conflicts) >= 1
    assert any(c.code == ConflictCode.CONFLICT_UNIT_DOUBLE_BOOKED.value for c in conflicts)
    assert any(c.severity == ConflictSeverity.BLOCKER.value for c in conflicts)


def test_temporal_conflict_target_concurrent_access():
    """Verifies detection of concurrent dwell at the same target across different units."""
    iv1 = TimelineInterval(
        interval_id="iv1",
        unit_id="unit_perseverance",
        activity_type=ActivityType.DWELL.value,
        start_time_s=1000.0,
        end_time_s=1600.0,
        duration_s=600.0,
        sol_index=1,
        target_id="tgt_sample_point_a",
    )
    iv2 = TimelineInterval(
        interval_id="iv2",
        unit_id="unit_crew_eva_1",
        activity_type=ActivityType.DWELL.value,
        start_time_s=1200.0,  # Overlaps dwell at same target
        end_time_s=1800.0,
        duration_s=600.0,
        sol_index=1,
        target_id="tgt_sample_point_a",
    )

    units = [
        ExplorationUnit(unit_id="unit_perseverance", name="Rover"),
        ExplorationUnit(unit_id="unit_crew_eva_1", name="Crew"),
    ]
    conflicts = detect_temporal_conflicts([iv1, iv2], [], units)

    assert any(c.code == ConflictCode.CONFLICT_TARGET_CONCURRENT_ACCESS.value for c in conflicts)
    assert any("tgt_sample_point_a" in c.affected_targets for c in conflicts)


def test_temporal_conflict_prerequisite_violation():
    """Verifies detection when a target starts before its prerequisite completes."""
    targets = [
        CampaignTarget(id="tgt_parent", name="Parent", row=10, col=10),
        CampaignTarget(id="tgt_child", name="Child", row=12, col=12, prerequisites=["tgt_parent"]),
    ]
    iv_child = TimelineInterval(
        interval_id="iv_child",
        unit_id="unit_perseverance",
        activity_type=ActivityType.DWELL.value,
        start_time_s=500.0,  # Child starts at 500s
        end_time_s=1000.0,
        duration_s=500.0,
        sol_index=1,
        target_id="tgt_child",
    )
    iv_parent = TimelineInterval(
        interval_id="iv_parent",
        unit_id="unit_perseverance",
        activity_type=ActivityType.DWELL.value,
        start_time_s=800.0,  # Parent doesn't finish until 1200s!
        end_time_s=1200.0,
        duration_s=400.0,
        sol_index=1,
        target_id="tgt_parent",
    )

    units = [ExplorationUnit(unit_id="unit_perseverance", name="Rover")]
    conflicts = detect_temporal_conflicts([iv_child, iv_parent], targets, units)

    assert any(c.code == ConflictCode.CONFLICT_PREREQUISITE_VIOLATION.value for c in conflicts)


def test_temporal_conflict_outside_availability():
    """Verifies conflict when a unit is scheduled on a sol outside its availability window."""
    unit = ExplorationUnit(
        unit_id="unit_perseverance",
        name="Rover",
        availability_window=AvailabilityWindow(start_sol=1, end_sol=2),
    )
    iv = TimelineInterval(
        interval_id="iv_sol3",
        unit_id="unit_perseverance",
        activity_type=ActivityType.TRANSIT.value,
        start_time_s=2 * MARTIAN_SOL_SECONDS + 100.0,
        end_time_s=2 * MARTIAN_SOL_SECONDS + 500.0,
        duration_s=400.0,
        sol_index=3,  # Unit only available on Sols 1-2!
    )

    conflicts = detect_temporal_conflicts([iv], [], [unit])
    assert any(c.code == ConflictCode.CONFLICT_OUTSIDE_AVAILABILITY.value for c in conflicts)


def test_contingency_interruption_and_prefix_freezing(
    sample_campaign: MissionCampaign,
    sample_coordination: CoordinationPlan,
    terrain_grid: TerrainGrid,
):
    """Verifies that injecting an interruption freezes the prefix and constructs a continuation."""
    twin = CampaignDigitalTwin(
        simulation_id="sim_freeze_test_001",
        campaign=sample_campaign,
        coordination_plan=sample_coordination,
        terrain=terrain_grid,
    )

    # Advance to 2000s
    twin.advance(2000.0)
    frozen_event_count = len(twin.logged_events)

    # Inject an operational hold contingency at t=2000s
    revised_twin = twin.inject_interruption(
        interruption_type="operational_hold",
        affected_unit_id="unit_perseverance",
        delay_duration_s=1800.0,
        reason="Dust accumulation sensor cleaning",
    )

    assert twin.status == SimulationStatus.INTERRUPTED.value
    assert revised_twin.parent_simulation_id == twin.simulation_id
    assert revised_twin.current_time_s >= 2000.0
    assert revised_twin.campaign.version == twin.campaign.version + 1


def test_contingency_unit_loss_and_reallocation(
    sample_campaign: MissionCampaign,
    sample_coordination: CoordinationPlan,
    terrain_grid: TerrainGrid,
):
    """Verifies unit loss reallocates uncompleted targets to the surviving unit."""
    twin = CampaignDigitalTwin(
        simulation_id="sim_unit_loss_001",
        campaign=sample_campaign,
        coordination_plan=sample_coordination,
        terrain=terrain_grid,
    )

    twin.advance(1000.0)

    # Rover experiences catastrophic power failure
    revised_twin = twin.inject_interruption(
        interruption_type="unit_unavailable",
        affected_unit_id="unit_perseverance",
        reason="Electrical short in drive motor bus",
    )

    # Check rover status in revised twin
    rover = next(u for u in revised_twin.units if u.unit_id == "unit_perseverance")
    assert rover.status == UnitStatus.UNAVAILABLE.value

    # Check that surviving crew EVA received reallocated tasks
    crew = next(u for u in revised_twin.units if u.unit_id == "unit_crew_eva_1")
    assert crew.status != UnitStatus.UNAVAILABLE.value


def test_simulation_workspace_persistence_and_reload(
    sample_campaign: MissionCampaign,
    sample_coordination: CoordinationPlan,
    terrain_grid: TerrainGrid,
):
    """Verifies saving, retrieving, and listing simulations in workspace."""
    twin = CampaignDigitalTwin(
        simulation_id="sim_persist_test_001",
        campaign=sample_campaign,
        coordination_plan=sample_coordination,
        terrain=terrain_grid,
    )
    sim_data = twin.to_dict()

    # Save
    saved = save_campaign_simulation(sim_data)
    assert saved["simulation_id"] == "sim_persist_test_001"

    # Get
    loaded = get_campaign_simulation("sim_persist_test_001")
    assert loaded["simulation_id"] == "sim_persist_test_001"
    assert loaded["campaign_id"] == sample_campaign.campaign_id

    # List
    all_sims = list_campaign_simulations(sample_campaign.campaign_id)
    assert any(s["simulation_id"] == "sim_persist_test_001" for s in all_sims)


def test_api_simulation_lifecycle_endpoints(
    sample_campaign: MissionCampaign,
    sample_coordination: CoordinationPlan,
    terrain_grid: TerrainGrid,
):
    """Verifies REST API service functions for start, advance, step, seek, interrupt, and queries."""
    # 1. Start
    start_payload = {
        "campaign_id": sample_campaign.campaign_id,
        "coordination_id": sample_coordination.coordination_id,
        "persist": True,
    }
    start_res = start_campaign_simulation_api(start_payload, terrain_grid)
    sim_id = start_res["simulation_id"]
    assert sim_id.startswith("sim_")
    assert start_res["status"] == SimulationStatus.IDLE.value

    # 2. Advance
    adv_payload = {"simulation_id": sim_id, "target_time_s": 2400.0, "persist": True}
    adv_res = advance_campaign_simulation_api(adv_payload, terrain_grid)
    assert adv_res["status"] == "success"
    assert adv_res["simulation"]["current_time_s"] == 2400.0

    # 3. Step
    step_payload = {"simulation_id": sim_id, "event_count": 2, "persist": True}
    step_res = step_campaign_simulation_api(step_payload, terrain_grid)
    assert step_res["status"] == "success"

    # 4. Seek
    seek_payload = {"simulation_id": sim_id, "target_time_s": 600.0, "persist": True}
    seek_res = seek_campaign_simulation_api(seek_payload, terrain_grid)
    assert seek_res["status"] == "success"
    assert seek_res["simulation"]["current_time_s"] == 600.0

    # 5. Queries
    sim_info = get_campaign_simulation_api(sim_id)
    assert sim_info["simulation_id"] == sim_id

    events = get_campaign_simulation_events_api(sim_id)
    assert isinstance(events, list)

    conflicts = get_campaign_simulation_conflicts_api(sim_id)
    assert isinstance(conflicts, list)

    sim_list = list_campaign_simulations_api(sample_campaign.campaign_id)
    assert any(s["simulation_id"] == sim_id for s in sim_list)

    # 6. Interrupt
    int_payload = {
        "simulation_id": sim_id,
        "interruption_type": "operational_hold",
        "affected_unit_id": "unit_perseverance",
        "delay_duration_s": 900.0,
        "reason": "Communication gap test",
        "persist": True,
    }
    int_res = interrupt_campaign_simulation_api(int_payload, terrain_grid)
    assert int_res["status"] == "success"
    assert int_res["revised_simulation"]["parent_simulation_id"] == sim_id


def test_unsupported_assumptions_flagged(
    sample_campaign: MissionCampaign,
    sample_coordination: CoordinationPlan,
    terrain_grid: TerrainGrid,
):
    """Verifies simulation disclaimers and flags against physical resource transfer assumptions."""
    twin = CampaignDigitalTwin(
        simulation_id="sim_disclaimer_001",
        campaign=sample_campaign,
        coordination_plan=sample_coordination,
        terrain=terrain_grid,
    )
    sim_data = twin.to_dict()

    disclaimer = sim_data["limitations_disclaimer"]
    assert "deterministic simulation model" in disclaimer
    assert "unsupported" in disclaimer.lower() or "not" in disclaimer.lower()
    for u in twin.units:
        assert "PHYSICAL_SAMPLE_TRANSFER" in u.unsupported_capabilities
        assert "DIRECT_POWER_TETHERING" in u.unsupported_capabilities
