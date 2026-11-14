"""
MarsWalk 2.0 / Project Atlas — Milestone 13O Dedicated Automated Test Suite
===========================================================================
Deep Space Autonomy Lab: Earth–Mars Communication, Distributed Intelligence & Bounded Autonomous Operations.
Tests all 20 core requirements:
- Command lifecycle state machine, CCSDS headers, SHA-256 integrity, idempotency.
- Independent uplink/downlink propagation delay (3–22 min), contact windows, solar conjunction.
- Epistemic state distinction: CURRENT_ON_MARS vs LAST_REPORTED_BY_MARS.
- Onboard rover autonomy modes, stale command detection, and explainable decision records.
- Distributed multi-rover coordination, network partition, and reconnection reconciliation.
- Discrete-event simulation, causality tracking, and deterministic replay.
- All 10 scenarios including the flagship 8-stage Scenario 01 "The Rover That Lost Earth".
- Live API endpoints and Draft 2020-12 schema validation.
"""

import copy
import json
import pytest
import urllib.request
import urllib.error

from marswalk.core.mars_command_transmission import (
    MarsRoverCommand,
    CommandTransmissionEngine,
    CommandLifecycleState,
    CommandPreconditions,
    CommandRiskClassification,
    CommandApprovalLevel,
    ContingencyPolicy,
    compute_payload_sha256,
)
from marswalk.core.mars_communication_environment import (
    DeepSpaceCommunicationEnvironment,
    CommunicationPacket,
    ContactWindowStatus,
    LinkMediumType,
    EpistemicInformationState,
)
from marswalk.core.mars_onboard_autonomy import (
    OnboardRoverAutonomyEngine,
    RoverPhysicalState,
    AutonomyOperatingMode,
    DecisionActionType,
)
from marswalk.core.mars_distributed_fleet_intelligence import (
    DistributedFleetIntelligenceManager,
    PartitionStatus,
)
from marswalk.core.deep_space_operations_simulator import (
    DeepSpaceOperationsSimulator,
    SimulatorEventType,
)
from marswalk.core.deep_space_scenario_engine import (
    DeepSpaceScenarioCatalog,
    ScenarioExecutionResult,
)
from marswalk.api.contracts import validate_contract


# --- TEST 1: Command Lifecycle State Machine Transitions ---
def test_command_lifecycle_state_machine():
    engine = CommandTransmissionEngine()
    precond = CommandPreconditions(expected_state_version=1)
    cmd = engine.create_command(
        mission_id="MSN_TEST",
        rover_id="ROVER_ALPHA",
        sequence_number=1,
        action_type="TRANSIT",
        payload={"waypoints": [{"x": 10.0, "y": 20.0}]},
        preconditions=precond,
    )
    assert cmd.current_state == CommandLifecycleState.DRAFT.value

    # Valid transition to VALIDATED
    ok, msg = engine.validate_on_earth(cmd.command_id, 0.0)
    assert ok is True
    assert cmd.current_state == CommandLifecycleState.VALIDATED.value

    # Cannot jump directly to EXECUTING
    assert cmd.can_transition_to(CommandLifecycleState.EXECUTING) is False

    # Valid approval
    ok, msg = engine.approve_command(cmd.command_id, "FLIGHT_DIRECTOR", 10.0)
    assert ok is True
    assert cmd.current_state == CommandLifecycleState.APPROVED.value

    # Queue
    ok, msg = engine.queue_for_transmission(cmd.command_id, 20.0)
    assert ok is True
    assert cmd.current_state == CommandLifecycleState.QUEUED.value


# --- TEST 2: Command Payload Integrity and Tampering Detection ---
def test_command_payload_integrity_tampering():
    engine = CommandTransmissionEngine()
    cmd = engine.create_command(
        mission_id="MSN_TEST",
        rover_id="ROVER_ALPHA",
        sequence_number=2,
        action_type="SAMPLE_DRILL",
        payload={"sample_depth_cm": 5.0},
        preconditions=CommandPreconditions(expected_state_version=1),
    )
    original_hash = cmd.payload_sha256
    assert len(original_hash) == 64

    # Tamper with payload
    cmd.payload["sample_depth_cm"] = 50.0  # Unauthorized depth change
    ok, msg = engine.validate_on_earth(cmd.command_id, 0.0)
    assert ok is False
    assert "integrity" in msg.lower() or "corruption" in msg.lower()
    assert cmd.current_state == CommandLifecycleState.REJECTED.value


# --- TEST 3: Idempotency and Duplicate Execution Prevention ---
def test_command_idempotency_duplicate_suppression():
    engine = CommandTransmissionEngine()
    cmd = engine.create_command(
        mission_id="MSN_TEST",
        rover_id="ROVER_ALPHA",
        sequence_number=3,
        action_type="SAMPLE_DRILL",
        payload={"sample_id": "CORE_01"},
        preconditions=CommandPreconditions(expected_state_version=1),
    )
    idem_key = cmd.idempotency_key
    assert idem_key is not None
    assert engine.check_duplicate_execution(idem_key) is False

    # Mark executed
    engine.mark_executed(idem_key)
    assert engine.check_duplicate_execution(idem_key) is True


# --- TEST 4: Communication Latency (Independent Uplink & Downlink) ---
def test_communication_latency_profile():
    comm = DeepSpaceCommunicationEnvironment(default_owlt_s=852.0)  # 14.2 min
    assert comm.round_trip_light_time_s == 852.0 * 2.0
    assert comm.rtl_time_minutes == pytest.approx(28.4, abs=0.1)

    # Independent profiles
    comm.set_latency_profile(uplink_min=4.5, downlink_min=18.0)
    assert comm.uplink_owlt_s == 4.5 * 60.0
    assert comm.downlink_owlt_s == 18.0 * 60.0
    assert comm.rtl_time_minutes == pytest.approx(22.5, abs=0.1)


# --- TEST 5: DSN Contact Windows and Scheduled Passes ---
def test_dsn_contact_windows_and_outages():
    comm = DeepSpaceCommunicationEnvironment()
    win = comm.schedule_contact_window(
        station_name="DSN_MADRID_DSS63",
        rover_id="ROVER_ALPHA",
        start_time_s=100.0,
        duration_s=3600.0,
    )
    assert win.duration_s == 3600.0

    # Before window
    is_open, reason = comm.is_link_operational_at(50.0, "ROVER_ALPHA")
    assert is_open is False

    # During window
    is_open, reason = comm.is_link_operational_at(500.0, "ROVER_ALPHA")
    assert is_open is True
    assert "DSN_MADRID" in reason

    # Outage injection
    comm.inject_link_outage(start_sim_time_s=400.0, duration_s=200.0, reason="High Winds at Madrid Antenna")
    is_open, reason = comm.is_link_operational_at(500.0, "ROVER_ALPHA")
    assert is_open is False
    assert "OUTAGE" in reason


# --- TEST 6: Solar Conjunction Blackout ---
def test_solar_conjunction_blackout():
    comm = DeepSpaceCommunicationEnvironment()
    comm.inject_solar_conjunction_blackout(start_sim_time_s=1000.0, duration_s=86400.0 * 14.0)
    assert comm.solar_conjunction.is_active is True

    # Check during conjunction
    is_open, reason = comm.is_link_operational_at(2000.0)
    assert is_open is False
    assert "SOLAR CONJUNCTION" in reason


# --- TEST 7: Epistemic State Distinction (Mars Truth vs Earth Knowledge) ---
def test_epistemic_information_tagging():
    comm = DeepSpaceCommunicationEnvironment(default_owlt_s=600.0)
    # Earth initial view is UNKNOWN
    ev0 = comm.get_epistemic_view_for_earth("ROVER_ALPHA")
    assert ev0["epistemic_state"] == EpistemicInformationState.UNKNOWN.value

    # Mars transmits telemetry at T=100s
    comm.transmit_telemetry_from_mars(
        rover_id="ROVER_ALPHA",
        telemetry_payload={"battery_wh": 850.0},
        sim_time_s=100.0,
    )
    # At T=500s, downlink is still in-flight
    comm.advance_simulation_time(500.0)
    ev1 = comm.get_epistemic_view_for_earth("ROVER_ALPHA")
    assert ev1["epistemic_state"] == EpistemicInformationState.UNKNOWN.value

    # At T=750s (100 + 600 = 700s arrival elapsed), telemetry delivered to Earth
    comm.advance_simulation_time(750.0)
    ev2 = comm.get_epistemic_view_for_earth("ROVER_ALPHA")
    assert ev2["epistemic_state"] == EpistemicInformationState.LAST_REPORTED_BY_MARS.value
    assert ev2["telemetry"]["battery_wh"] == 850.0


# --- TEST 8: Onboard Rover Autonomy Operating Modes ---
def test_onboard_rover_autonomy_modes():
    rover = OnboardRoverAutonomyEngine(rover_id="ROVER_ALPHA", initial_mode=AutonomyOperatingMode.EARTH_SUPERVISED.value)
    assert rover.state.operating_mode == AutonomyOperatingMode.EARTH_SUPERVISED.value

    rover.set_operating_mode(AutonomyOperatingMode.BOUNDED_AUTONOMY, "Entering crater traverse phase", 100.0)
    assert rover.state.operating_mode == AutonomyOperatingMode.BOUNDED_AUTONOMY.value
    assert rover.state.state_version == 2
    assert len(rover.decisions_log) == 1


# --- TEST 9: Stale Command State Version Mismatch Interception ---
def test_stale_command_state_version_mismatch():
    rover = OnboardRoverAutonomyEngine(rover_id="ROVER_ALPHA")
    rover.state.state_version = 5  # Mars state has advanced to v5

    cmd = MarsRoverCommand(
        command_id="CMD_STALE_VER",
        mission_id="MSN_1",
        rover_id="ROVER_ALPHA",
        command_sequence_number=10,
        action_type="TRANSIT",
        payload={"destination": "CRATER_DELTA"},
        preconditions=CommandPreconditions(expected_state_version=2),  # Earth assumed v2
        creation_sim_time_s=0.0,
    )
    is_acc, dec = rover.evaluate_incoming_command(cmd, 100.0)
    assert is_acc is False
    assert cmd.current_state == CommandLifecycleState.REJECTED.value
    assert "STATE_VERSION_MISMATCH" in dec.relevant_constraints[0]


# --- TEST 10: Stale Command Terrain Hazard Interception ---
def test_stale_command_terrain_hazard_interception():
    rover = OnboardRoverAutonomyEngine(rover_id="ROVER_ALPHA")
    # Newly detected rockfall at (35, 50)
    rover.inject_environmental_hazard("HZ_01", "ROCKFALL", (35.0, 50.0), "SEVERE", "Scarp collapse")

    # Command whose planned route passes through (35, 50)
    cmd = MarsRoverCommand(
        command_id="CMD_HAZARD",
        mission_id="MSN_1",
        rover_id="ROVER_ALPHA",
        command_sequence_number=11,
        action_type="TRANSIT",
        payload={"waypoints": [{"x": 10.0, "y": 20.0}, {"x": 35.0, "y": 50.0}]},
        preconditions=CommandPreconditions(expected_state_version=rover.state.state_version),
        contingency_policy=ContingencyPolicy.RECALCULATE_ROUTE.value,
    )
    is_acc, dec = rover.evaluate_incoming_command(cmd, 200.0)
    assert is_acc is False
    assert dec.selected_action == DecisionActionType.EXECUTE_CONTINGENCY_DETOUR.value
    assert dec.contingency_executed == "RECOMPUTE_LOCAL_WAYPOINT_DETOUR"


# --- TEST 11: Stale Command Energy Margin Interception ---
def test_stale_command_energy_margin_interception():
    rover = OnboardRoverAutonomyEngine(rover_id="ROVER_ALPHA")
    rover.state.battery_charge_wh = 220.0
    rover.state.min_reserve_limit_wh = 200.0

    # Command requires 100 Wh (would drop to 120 Wh < 200 Wh minimum)
    cmd = MarsRoverCommand(
        command_id="CMD_ENERGY",
        mission_id="MSN_1",
        rover_id="ROVER_ALPHA",
        command_sequence_number=12,
        action_type="SCIENCE_DWELL",
        payload={"dwell_target": "MINERAL_VEIN"},
        preconditions=CommandPreconditions(expected_state_version=rover.state.state_version, max_energy_cost_wh=100.0),
        contingency_policy=ContingencyPolicy.DEFER_SCIENCE.value,
    )
    is_acc, dec = rover.evaluate_incoming_command(cmd, 300.0)
    assert is_acc is False
    assert dec.selected_action == DecisionActionType.DEFER_SCIENCE_ACTIVITY.value
    assert dec.contingency_executed == "DEFER_SCIENCE_AND_PRESERVE_CHARGE"


# --- TEST 12: Stale Command Instrument Fault Interception ---
def test_stale_command_instrument_fault_interception():
    rover = OnboardRoverAutonomyEngine(rover_id="ROVER_ALPHA")
    rover.state.operational_instruments["CORING_DRILL"] = False  # Drill faulted

    cmd = MarsRoverCommand(
        command_id="CMD_DRILL",
        mission_id="MSN_1",
        rover_id="ROVER_ALPHA",
        command_sequence_number=13,
        action_type="SAMPLE_DRILL",
        payload={"sample_depth_cm": 4.0},
        preconditions=CommandPreconditions(
            expected_state_version=rover.state.state_version,
            required_instruments_operational=["CORING_DRILL"],
        ),
    )
    is_acc, dec = rover.evaluate_incoming_command(cmd, 400.0)
    assert is_acc is False
    assert any("CORING_DRILL" in c for c in dec.relevant_constraints)


# --- TEST 13: Explainable Autonomy Decision Record Transparency ---
def test_explainable_autonomy_decision_record():
    rover = OnboardRoverAutonomyEngine(rover_id="ROVER_ALPHA")
    rover.state.battery_charge_wh = 180.0  # Already below reserve limit
    cmd = MarsRoverCommand(
        command_id="CMD_EXP_TEST",
        mission_id="MSN_1",
        rover_id="ROVER_ALPHA",
        command_sequence_number=14,
        action_type="TRANSIT",
        payload={},
        preconditions=CommandPreconditions(expected_state_version=rover.state.state_version, max_energy_cost_wh=50.0),
    )
    is_acc, dec = rover.evaluate_incoming_command(cmd, 500.0)
    dec_dict = dec.to_dict()

    # Verify all explainability fields exist without confidence scores
    assert "situation_detected" in dec_dict
    assert "available_evidence" in dec_dict
    assert "relevant_constraints" in dec_dict
    assert "applicable_rule" in dec_dict
    assert "alternatives_considered" in dec_dict
    assert "selected_action" in dec_dict
    assert "engineering_explanation" in dec_dict
    assert "confidence_score" not in dec_dict  # Non-negotiable: no arbitrary AI confidence scores


# --- TEST 14: Bounded Local Detour Contingency ---
def test_bounded_contingency_detour():
    rover = OnboardRoverAutonomyEngine(rover_id="ROVER_ALPHA")
    rover.inject_environmental_hazard("HZ_02", "STEEP_SCARP", (20.0, 20.0), "CRITICAL", "Slope > 25 deg")
    cmd = MarsRoverCommand(
        command_id="CMD_DETOUR",
        mission_id="MSN_1",
        rover_id="ROVER_ALPHA",
        command_sequence_number=15,
        action_type="TRANSIT",
        payload={"waypoints": [{"x": 20.0, "y": 20.0}]},
        preconditions=CommandPreconditions(expected_state_version=rover.state.state_version),
        contingency_policy=ContingencyPolicy.RECALCULATE_ROUTE.value,
    )
    is_acc, dec = rover.evaluate_incoming_command(cmd, 600.0)
    assert is_acc is False
    assert dec.contingency_executed == "RECOMPUTE_LOCAL_WAYPOINT_DETOUR"


# --- TEST 15: Multi-Rover Fleet & Shared Peer Hazards ---
def test_multi_rover_fleet_and_shared_hazards():
    fleet = DistributedFleetIntelligenceManager(fleet_rover_ids=["ROVER_ALPHA", "ROVER_BRAVO"])
    assert len(fleet.rovers) == 2

    msg = fleet.broadcast_hazard_from_rover(
        sender_id="ROVER_ALPHA",
        hazard_type="DUNES_LOOSE_SAND",
        location_xy=(50.0, 75.0),
        severity="MEDIUM",
        description="Active barchan dune field",
        sim_time_s=100.0,
    )
    assert msg.is_delivered is True
    # Rover Bravo must now have the shared hazard in its catalog
    assert len(fleet.rovers["ROVER_BRAVO"].state.known_hazards) == 1
    assert fleet.rovers["ROVER_BRAVO"].state.known_hazards[0]["hazard_type"] == "DUNES_LOOSE_SAND"


# --- TEST 16: Network Partition and Reconnection State Reconciliation ---
def test_network_partition_and_reconnection_reconciliation():
    fleet = DistributedFleetIntelligenceManager(fleet_rover_ids=["ROVER_ALPHA", "ROVER_BRAVO"])
    # Disconnect rovers into independent partitions
    fleet.set_network_partition([["ROVER_ALPHA"], ["ROVER_BRAVO"]])
    assert fleet.partition_status == PartitionStatus.SEVERELY_ISOLATED.value
    assert fleet.are_rovers_connected("ROVER_ALPHA", "ROVER_BRAVO") is False

    # Rover Alpha detects hazard while disconnected
    fleet.broadcast_hazard_from_rover("ROVER_ALPHA", "LOCAL_PIT", (10.0, 10.0), "HIGH", "Collapse pit", 150.0)
    # Rover Bravo does NOT know yet!
    assert len(fleet.rovers["ROVER_BRAVO"].state.known_hazards) == 0

    # Reconnect network and reconcile state
    conflicts = fleet.reconcile_partition_reconnection(200.0)
    assert fleet.partition_status == PartitionStatus.FULLY_CONNECTED.value
    # Rover Bravo now possesses reconciled hazard
    assert len(fleet.rovers["ROVER_BRAVO"].state.known_hazards) == 1


# --- TEST 17: Discrete-Event Simulator Deterministic Replay ---
def test_discrete_event_deterministic_replay():
    # Run 1
    sim1 = DeepSpaceOperationsSimulator(seed=123)
    sim1.record_event(SimulatorEventType.COMMAND_CREATED, "EARTH", {"id": 1}, 10.0)
    sim1.record_event(SimulatorEventType.UPLINK_INITIATED, "EARTH", {"id": 1}, 15.0)

    # Run 2
    sim2 = DeepSpaceOperationsSimulator(seed=123)
    sim2.record_event(SimulatorEventType.COMMAND_CREATED, "EARTH", {"id": 1}, 10.0)
    sim2.record_event(SimulatorEventType.UPLINK_INITIATED, "EARTH", {"id": 1}, 15.0)

    assert len(sim1.event_ledger) == len(sim2.event_ledger)
    assert sim1.event_ledger[0].event_id == sim2.event_ledger[0].event_id
    assert sim1.event_ledger[1].event_id == sim2.event_ledger[1].event_id


# --- TEST 18: Flagship Scenario 01 "The Rover That Lost Earth" All 8 Stages ---
def test_flagship_scenario_01_all_8_stages():
    res = DeepSpaceScenarioCatalog.run_scenario("SCENARIO_01", seed=42)
    assert res.is_success is True
    assert res.stages_completed == 8
    assert res.total_stages == 8
    assert res.stale_commands_intercepted == 1
    assert res.contingencies_executed == 1
    assert res.final_mission_status == "MISSION_OPERATIONAL_NOMINAL"


# --- TEST 19: All 10 Scenarios Execution ---
def test_all_10_scenarios_execution():
    sc_list = DeepSpaceScenarioCatalog.list_scenarios()
    assert len(sc_list) == 10
    for sc in sc_list:
        res = DeepSpaceScenarioCatalog.run_scenario(sc["scenario_id"])
        assert res.is_success is True
        assert res.stages_completed == res.total_stages


# --- TEST 20: Live Deep Space API Endpoints on Daemon ---
def test_live_deep_space_api_endpoints():
    # Test GET /api/deep-space/status
    req = urllib.request.Request("http://127.0.0.1:3000/api/deep-space/status")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "mission_id" in data
        assert "comm_status" in data
        assert "fleet_status" in data
        validate_contract(data, "deep-space-autonomy")

    # Test GET /api/deep-space/scenarios
    req_sc = urllib.request.Request("http://127.0.0.1:3000/api/deep-space/scenarios")
    with urllib.request.urlopen(req_sc, timeout=5) as resp:
        assert resp.status == 200
        scs = json.loads(resp.read().decode("utf-8"))
        assert len(scs) == 10

    # Test POST /api/deep-space/scenarios/run
    payload = json.dumps({"scenario_id": "SCENARIO_01"}).encode("utf-8")
    req_run = urllib.request.Request(
        "http://127.0.0.1:3000/api/deep-space/scenarios/run",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_run, timeout=5) as resp:
        assert resp.status == 200
        run_res = json.loads(resp.read().decode("utf-8"))
        assert run_res["is_success"] is True
        assert run_res["stages_completed"] == 8
