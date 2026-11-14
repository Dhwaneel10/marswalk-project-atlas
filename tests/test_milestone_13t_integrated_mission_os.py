"""Project Atlas / MarsWalk 2.0 — Milestone 13T
Comprehensive Verification Test Battery for Atlas Planetary Mission OS.

Tests end-to-end mission orchestration, multi-tiered state management, causal event
coordination, asset fleet allocation, Bayesian scientific discovery, closed-loop
resource conservation, deep-space autonomy under delay, resilience against cascades,
flagship 12-phase execution, cryptographic replay, and Draft 2020-12 schema conformance.
"""

import pytest
import jsonschema

from marswalk.api.contracts import get_validator
from marswalk.core.atlas_mission_contracts import (
    AssetHealthState,
    AssetType,
    CampaignPhaseType,
    CommandState,
    MissionObjective,
    MissionStatus,
    TaskState,
)
from marswalk.core.atlas_mission_state import UnifiedMissionStateManager
from marswalk.core.atlas_mission_event_coordinator import (
    MissionEventCoordinator,
    parse_sol_time_to_seconds,
    format_seconds_to_sol_time,
    EventType,
)
from marswalk.core.atlas_campaign_compiler import CampaignCompiler
from marswalk.core.atlas_unified_asset_manager import UnifiedAssetManager
from marswalk.core.atlas_scientific_operations import (
    ScientificOperationsManager,
    USGS_CTX_JEZERO_HASH,
    compute_shannon_entropy,
)
from marswalk.core.atlas_resource_operations import ResourceOperationsManager
from marswalk.core.atlas_autonomous_operations import (
    DeepSpaceAutonomyManager,
    calculate_owlt_seconds,
)
from marswalk.core.atlas_mission_resilience_coordinator import MissionResilienceCoordinator
from marswalk.core.atlas_mission_execution_core import AtlasMissionExecutionCore
from marswalk.core.atlas_integrated_mission_scenario import IntegratedMissionScenarioRunner
from marswalk.core.atlas_mission_replay import MissionReplayVerifier
from marswalk.api.service import (
    mission_os_status_api,
    mission_os_create_api,
    mission_os_advance_api,
    mission_os_dispatch_command_api,
    mission_os_inject_event_api,
    mission_os_flagship_run_api,
    mission_os_replay_verify_api,
    mission_os_dossier_api,
)


@pytest.fixture
def sample_objective():
    return MissionObjective(
        objective_id="OBJ-TEST-ALPHA",
        title="Jezero Settlement & Science Ingestion",
        raw_intent="Establish research settlement, survey delta, and prepare for human arrival.",
        target_site_id="SITE-JEZERO-DELTA-01",
        target_region="Jezero Crater Western Delta Outwash",
        duration_sols=60,
    )


# -----------------------------------------------------------------------------
# 1. Campaign Compiler & Objective Decomposition
# -----------------------------------------------------------------------------
def test_campaign_compiler_decomposition(sample_objective):
    phases = CampaignCompiler.compile_campaign(sample_objective)
    assert len(phases) == 7
    assert phases[0].phase_type == CampaignPhaseType.PHASE_A_RECONNAISSANCE
    assert phases[-1].phase_type == CampaignPhaseType.PHASE_G_EXPEDITION_READINESS

    # Check tasks and prerequisite connectivity
    all_tasks = [t for p in phases for t in p.tasks]
    assert len(all_tasks) >= 14
    task_ids = {t.task_id for t in all_tasks}
    for t in all_tasks:
        for prereq in t.prerequisites:
            assert prereq in task_ids, f"Prerequisite {prereq} missing in compiled tasks"


# -----------------------------------------------------------------------------
# 2. Multi-Tiered Mission State & SHA-256 Hashing
# -----------------------------------------------------------------------------
def test_multi_tiered_state_manager():
    mgr = UnifiedMissionStateManager(initial_sol=1)
    assert mgr.physical.sol == 1
    assert mgr.physical.habitat_core_pressure_kpa == 101.3

    initial_hash = mgr.compute_state_hash()
    assert len(initial_hash) == 64

    snap1 = mgr.capture_snapshot(active_assets_count=8, health_status="NOMINAL")
    assert snap1.step_index == 0
    assert snap1.prev_state_hash == "0" * 64
    assert snap1.state_hash == initial_hash

    # Alter physical state
    mgr.physical.water_storage_kg -= 50.0
    drift = mgr.compute_telemetry_drift()
    assert drift["water_drift_kg"] == 50.0
    assert not drift["is_synchronized"]

    # Synchronize Earth reported telemetry
    mgr.sync_earth_reported(owlt_seconds=852.0)
    drift2 = mgr.compute_telemetry_drift()
    assert drift2["water_drift_kg"] == 0.0
    assert drift2["is_synchronized"]


# -----------------------------------------------------------------------------
# 3. Discrete Event Timeline & Clock Synchronization
# -----------------------------------------------------------------------------
def test_event_coordinator_temporal_mechanics():
    coord = MissionEventCoordinator(start_sol=1, start_sol_time="06:00:00", initial_ls=56.4)
    assert coord.current_sol == 1
    assert coord.current_sol_time == "06:00:00"

    # Schedule event at Sol 2 12:00:00
    coord.schedule_event(
        event_id="EVT-001",
        event_type=EventType.SIMULATION_TICK,
        sol=2,
        sol_time_str="12:00:00",
        priority=3,
        payload={"note": "Scheduled drill sample"},
    )

    # Advance 0.5 sols (clock reaches Sol 1 18:00:00, event should not fire yet)
    dispatched = coord.advance_time(delta_sols=0.5)
    assert len(dispatched) == 0
    assert coord.current_sol == 1

    # Advance another 1.0 sol (reaches Sol 2 18:00:00, event must fire)
    dispatched2 = coord.advance_time(delta_sols=1.0)
    assert len(dispatched2) == 1
    assert dispatched2[0].event_id == "EVT-001"
    assert dispatched2[0].executed


# -----------------------------------------------------------------------------
# 4. Asset Fleet Registry & Conflict-Free Allocation
# -----------------------------------------------------------------------------
def test_asset_fleet_allocation():
    fleet = UnifiedAssetManager()
    rover = fleet.get_asset("ATLAS-ROVER-01")
    assert rover is not None
    assert rover.asset_type == AssetType.GROUND_ROVER
    assert rover.battery_charge_pct == 98.5

    # Allocate to task
    allocated = fleet.allocate_asset_to_task("ATLAS-ROVER-01", "TASK-TEST-01")
    assert allocated
    assert rover.current_task_id == "TASK-TEST-01"

    # Double-booking attempt must fail
    second_alloc = fleet.allocate_asset_to_task("ATLAS-ROVER-01", "TASK-CONFLICT-02")
    assert not second_alloc

    # Release asset
    fleet.release_asset("ATLAS-ROVER-01")
    assert rover.current_task_id is None

    # Battery discharge and recharge
    fleet.consume_battery("ATLAS-ROVER-01", 15.0)
    assert rover.battery_charge_pct == 83.5
    fleet.recharge_battery("ATLAS-ROVER-01", 20.0)
    assert rover.battery_charge_pct == 100.0


# -----------------------------------------------------------------------------
# 5. Scientific Operations, Bayesian Learning & Provenance Guardrails
# -----------------------------------------------------------------------------
def test_scientific_operations_bayesian_discovery():
    sci = ScientificOperationsManager()
    assert len(sci.investigations) == 4
    hyp = sci.investigations["HYP-JEZERO-01"]
    assert hyp.prior_probability == 0.65

    # Ingest authentic observation
    obs = sci.ingest_observation(
        observation_id="OBS-TEST-01",
        source_asset_id="ATLAS-ROVER-01",
        sol=5,
        sol_time="10:00:00",
        location={"lat": 18.4447, "lon": 77.4508, "elevation_m": -2530.0},
        instrument_type="PIXL",
        modality="GEOCHEMISTRY",
        data={"smectite_clay_pct": 32.5},
        uncertainty={"pct": 0.5},
    )
    assert len(obs.provenance_hash) == 64

    # Update hypothesis with strong evidence
    new_prob, info_gain = sci.update_hypothesis_evidence("HYP-JEZERO-01", "OBS-TEST-01", likelihood_ratio=10.0)
    assert new_prob > 0.65
    assert info_gain > 0.0
    assert obs.shannon_information_gain_bits > 0.0

    metrics = sci.get_summary_metrics()
    assert metrics["reference_dtm_provenance"] == USGS_CTX_JEZERO_HASH
    assert metrics["total_observations"] == 1


# -----------------------------------------------------------------------------
# 6. Closed-Loop Mass Balance & Thermodynamic Power Operations
# -----------------------------------------------------------------------------
def test_resource_operations_closed_conservation():
    res = ResourceOperationsManager(reactor_rated_kwe=120.0, battery_capacity_kwh=250.0)
    ledger = res.step_sol_resources(sol=1, solar_insolation_w_m2=480.0, dust_tau=0.45, base_demand_kwe=65.0)

    assert ledger.power_generated_kwe >= 120.0
    assert ledger.power_balance_kwe > 0.0
    assert ledger.mass_conservation_discrepancy_kg == 0.000
    assert ledger.battery_soc_pct >= 90.0
    assert ledger.thermal_core_temp_k == 294.15


# -----------------------------------------------------------------------------
# 7. Deep-Space Autonomy, OWLT Delay & Stale State Hash Rejection
# -----------------------------------------------------------------------------
def test_deep_space_autonomy_and_stale_hash_rejection():
    autonomy = DeepSpaceAutonomyManager(earth_mars_distance_au=1.708)
    assert 852.0 <= autonomy.owlt_seconds <= 853.0  # 14.2 minutes (852.3 s)

    valid_hash = "f" * 64
    stale_hash = "0" * 64

    # Earth dispatches command targeting state hash 'f'*64
    cmd = autonomy.queue_earth_command(
        command_id="CMD-TEST-001",
        target_asset_id="ATLAS-ROVER-01",
        action="DRILL_CORE",
        parameters={},
        expected_state_hash=valid_hash,
        created_met_seconds=0.0,
    )
    assert cmd.state == CommandState.UPLINK_QUEUED

    # Mars receives at MET 1000s (> 852s arrival time)
    # Case A: Live Mars state is drifted to '0'*64 -> MUST REJECT
    processed = autonomy.process_uplinks_on_mars(current_mars_met_seconds=1000.0, current_mars_state_hash=stale_hash)
    assert len(processed) == 1
    assert processed[0].state == CommandState.REJECTED_STALE_HASH
    assert "REJECTED" in processed[0].execution_result

    # Case B: Dispatched with matching hash -> MUST EXECUTE
    cmd2 = autonomy.queue_earth_command(
        command_id="CMD-TEST-002",
        target_asset_id="ATLAS-ROVER-01",
        action="DRILL_CORE",
        parameters={},
        expected_state_hash=valid_hash,
        created_met_seconds=1000.0,
    )
    processed2 = autonomy.process_uplinks_on_mars(current_mars_met_seconds=2000.0, current_mars_state_hash=valid_hash)
    assert len(processed2) == 1
    assert processed2[0].state == CommandState.EXECUTED


# -----------------------------------------------------------------------------
# 8. Resilience Coordinator & FDDI Contingency Mitigation
# -----------------------------------------------------------------------------
def test_resilience_fault_injection_and_recovery():
    resil = MissionResilienceCoordinator()
    incident = resil.inject_failure(
        incident_id="INC-DUST-01",
        subsystem="ENVIRONMENT",
        failure_mode="DUST_STORM_SOLAR_DROP",
        root_cause="Saltation event",
        sol=48,
    )
    resp = resil.diagnose_and_recover("INC-DUST-01")
    assert resp.resolved
    assert "AUTONOMOUS_LOAD_SHED_TO_BASELOAD_REACTOR" in resp.recovery_strategy
    assert "MICROWAVE_REGOLITH_SINTERING" in resp.load_shedding_actions

    metrics = resil.get_resilience_metrics()
    assert metrics["total_incidents_injected"] == 1
    assert metrics["diagnosed_and_recovered_count"] == 1
    assert metrics["resilience_assurance_index"] == 1.0


# -----------------------------------------------------------------------------
# 9. Execution Core Integration & Single-Sol Advancement
# -----------------------------------------------------------------------------
def test_execution_core_sol_advancement(sample_objective):
    core = AtlasMissionExecutionCore(mission_id="ATLAS-TEST-001", objective=sample_objective)
    assert core.status == MissionStatus.EXECUTING
    assert core.event_coord.current_sol == 1

    ledger = core.advance_sol()
    assert core.event_coord.current_sol == 2
    assert ledger.sol == 1
    assert core.state_mgr.physical.sol == 2
    assert len(core.state_mgr.history) == 2  # initial + 1 advanced


# -----------------------------------------------------------------------------
# 10. Flagship 12-Phase Mission Execution & Phase F Qualification
# -----------------------------------------------------------------------------
def test_flagship_12_phase_demonstration():
    core, dossier, phase_results = IntegratedMissionScenarioRunner.run_flagship_mission()

    assert core.mission_id == "ATLAS-MARS-BASE-ALPHA-001"
    assert core.event_coord.current_sol >= 60
    assert core.status == MissionStatus.COMPLETED

    # Verify all 12 phases executed
    assert len(phase_results) == 12
    assert phase_results["phase_07_autonomy_loop"]["stale_rejection_verified"] is True
    assert phase_results["phase_09_resilience"]["resolved"] is True
    assert phase_results["phase_10_construction"]["blast_berm_ready"] is True
    assert phase_results["phase_11_reconciliation"]["mass_conservation_discrepancy_kg"] == 0.000

    # Verify dossier & Phase F qualification
    assert dossier.phase_f_readiness_score == 100.0
    assert dossier.cryptographic_replay_valid is True
    assert len(dossier.root_hash) == 64
    assert "NASA Space Apps Scientific Integrity Notice" in dossier.mandatory_scientific_disclosure


# -----------------------------------------------------------------------------
# 11. Cryptographic Replay & Bit-Exact Hash Chain Verification
# -----------------------------------------------------------------------------
def test_cryptographic_replay_verification():
    core, dossier, _ = IntegratedMissionScenarioRunner.run_flagship_mission()
    is_valid, msg, meta = MissionReplayVerifier.verify_hash_chain(
        snapshots=core.state_mgr.history,
        expected_root_hash=dossier.root_hash,
    )
    assert is_valid, f"Hash chain verification failed: {msg}"
    assert meta["snapshot_count"] == len(core.state_mgr.history)

    # Scrub to step 10
    scrubbed = MissionReplayVerifier.scrub_to_step(core.state_mgr.history, 10)
    assert scrubbed is not None
    assert scrubbed["step_index"] == 10


# -----------------------------------------------------------------------------
# 12. JSON Schema Draft 2020-12 Contract Conformance
# -----------------------------------------------------------------------------
def test_json_schema_draft_2020_12_contract_conformance():
    validator = get_validator("mission-os")
    payload = mission_os_status_api()

    # Draft 2020-12 validation must pass with zero errors
    errors = list(validator.iter_errors(payload))
    assert len(errors) == 0, f"Schema validation failed: {[e.message for e in errors]}"


# -----------------------------------------------------------------------------
# 13. High-Level API Endpoints Verification
# -----------------------------------------------------------------------------
def test_api_endpoints_suite():
    # 1. Status
    status = mission_os_status_api()
    assert "mission_id" in status
    assert status["status"] in ["PENDING", "INITIALIZING", "EXECUTING", "COMPLETED"]

    # 2. Advance
    advanced = mission_os_advance_api({"sols_to_advance": 2})
    assert advanced["current_sol"] >= 2

    # 3. Dispatch command
    cmd = mission_os_dispatch_command_api({
        "target_asset_id": "ATLAS-ROVER-01",
        "action": "SURVEY_OUTWASH_FAN",
        "parameters": {"depth_cm": 25.0},
    })
    assert "command_id" in cmd
    assert cmd["state"] == "UPLINK_QUEUED"

    # 4. Inject resilience event
    inj = mission_os_inject_event_api({
        "subsystem": "POWER_GRID",
        "mode": "SOLAR_INVERTER_TRIP",
        "root_cause": "Thermal expansion on connector",
    })
    assert inj["response"]["resolved"] is True

    # 5. Replay verification
    replay = mission_os_replay_verify_api()
    assert replay["is_valid"] is True

    # 6. Dossier
    dossier = mission_os_dossier_api()
    assert "phase_f_readiness_score" in dossier
    assert "mandatory_scientific_disclosure" in dossier


# -----------------------------------------------------------------------------
# 14. Causal Parent-Child Event Graph Linkage
# -----------------------------------------------------------------------------
def test_causal_event_graph_lineage():
    coord = MissionEventCoordinator(start_sol=1)
    parent_evt = coord.schedule_event(
        event_id="EVT-PARENT-01",
        event_type=EventType.TASK_STARTED,
        sol=1,
        sol_time_str="08:00:00",
        priority=2,
    )
    child_evt = coord.schedule_event(
        event_id="EVT-CHILD-01",
        event_type=EventType.TASK_COMPLETED,
        sol=1,
        sol_time_str="10:00:00",
        priority=3,
        parent_event_id=parent_evt.event_id,
    )
    dispatched = coord.advance_time(delta_sols=1.0)
    assert len(dispatched) == 2
    assert dispatched[1].parent_event_id == parent_evt.event_id


# -----------------------------------------------------------------------------
# 15. Shannon Entropy Monotonic Reduction
# -----------------------------------------------------------------------------
def test_shannon_entropy_calculation():
    # Maximum entropy at p=0.5
    h_max = compute_shannon_entropy(0.50)
    assert round(h_max, 4) == 1.0000

    # Low entropy at near-certainty p=0.99
    h_low = compute_shannon_entropy(0.99)
    assert h_low < 0.10


# -----------------------------------------------------------------------------
# 16. Multi-Asset Simultaneous Allocation & Location Odometry
# -----------------------------------------------------------------------------
def test_multi_asset_simultaneous_movement():
    fleet = UnifiedAssetManager()
    fleet.update_asset_location("ATLAS-ROVER-01", 18.4500, 77.4550, -2520.0, distance_delta_m=420.0)
    fleet.update_asset_location("HEXACOPTER-SURVEYOR-02", 18.4600, 77.4650, -2490.0, distance_delta_m=1250.0)

    rover = fleet.get_asset("ATLAS-ROVER-01")
    heli = fleet.get_asset("HEXACOPTER-SURVEYOR-02")
    assert rover.cumulative_distance_m == 420.0
    assert heli.cumulative_distance_m == 1250.0


# -----------------------------------------------------------------------------
# 17. Replay Scrubber Boundary Conditions
# -----------------------------------------------------------------------------
def test_replay_scrubber_boundaries():
    core, _, _ = IntegratedMissionScenarioRunner.run_flagship_mission()
    # Out-of-bounds queries must return None safely
    assert MissionReplayVerifier.scrub_to_step(core.state_mgr.history, -1) is None
    assert MissionReplayVerifier.scrub_to_step(core.state_mgr.history, 9999) is None
    # In-bounds query returns dictionary
    valid = MissionReplayVerifier.scrub_to_step(core.state_mgr.history, 0)
    assert valid["step_index"] == 0


# -----------------------------------------------------------------------------
# 18. Unified Mission Serialization Round-Trip
# -----------------------------------------------------------------------------
def test_unified_mission_serialization_round_trip(sample_objective):
    core = AtlasMissionExecutionCore(mission_id="ATLAS-ROUNDTRIP-001", objective=sample_objective)
    entity = core.get_mission_entity()
    d = entity.to_dict()
    assert d["mission_id"] == "ATLAS-ROUNDTRIP-001"
    assert "phases" in d
    assert "assets" in d

    from marswalk.core.atlas_mission_contracts import UnifiedMission
    reconstituted = UnifiedMission.from_dict(d)
    assert reconstituted.mission_id == entity.mission_id
    assert reconstituted.status == entity.status
    assert len(reconstituted.phases) == len(entity.phases)


# -----------------------------------------------------------------------------
# 19. Cold-Soak Night Environmental Thermal Balance
# -----------------------------------------------------------------------------
def test_habitat_thermal_stability():
    res = ResourceOperationsManager()
    # Step across 10 sols
    for s in range(1, 11):
        ledger = res.step_sol_resources(sol=s, solar_insolation_w_m2=350.0, dust_tau=0.55)
        # Habitat core must maintain 294.15 K (+21 C) despite night cold-soak
        assert ledger.thermal_core_temp_k == 294.15


# -----------------------------------------------------------------------------
# 20. Stale State Hash Guard In Transit
# -----------------------------------------------------------------------------
def test_stale_command_in_transit_status():
    autonomy = DeepSpaceAutonomyManager(earth_mars_distance_au=1.708)
    cmd = autonomy.queue_earth_command(
        command_id="CMD-TRANSIT-01",
        target_asset_id="ATLAS-ROVER-01",
        action="DRILL",
        parameters={},
        expected_state_hash="a" * 64,
        created_met_seconds=100.0,
    )
    # Check at MET 200s (only 100s elapsed, less than 852.3s OWLT)
    in_transit = autonomy.process_uplinks_on_mars(current_mars_met_seconds=200.0, current_mars_state_hash="a" * 64)
    assert len(in_transit) == 0
    assert cmd.state == CommandState.IN_TRANSIT


# -----------------------------------------------------------------------------
# 21. Multi-Hypothesis Joint Information Evaluation
# -----------------------------------------------------------------------------
def test_multi_hypothesis_joint_evaluation():
    sci = ScientificOperationsManager()
    hyps = sci.list_investigations()
    assert len(hyps) == 4
    init_entropy = sum(h.information_entropy_bits for h in hyps)
    assert init_entropy > 3.0


# -----------------------------------------------------------------------------
# 22. Inactive Phase Immutability & Completion Tracking
# -----------------------------------------------------------------------------
def test_phase_state_transitions(sample_objective):
    core = AtlasMissionExecutionCore(mission_id="ATLAS-PHASE-TEST", objective=sample_objective)
    # At sol 1, Phase A is active, Phase B is inactive
    assert core.phases[0].is_active is True
    assert core.phases[1].is_active is False
    assert core.phases[0].is_completed is False


# -----------------------------------------------------------------------------
# 23. CommLink Elevation and SNR Calculations
# -----------------------------------------------------------------------------
def test_comm_link_query():
    autonomy = DeepSpaceAutonomyManager(earth_mars_distance_au=1.708)
    link = autonomy.get_comm_link_status("EARTH_MCC", "SURFACE-COMM-MAST-01")
    assert link.is_line_of_sight is True
    assert link.signal_to_noise_ratio_db >= 15.0
    assert link.bandwidth_kbps > 1000.0


# -----------------------------------------------------------------------------
# 24. Dossier Cryptographic Root Hash Non-Empty
# -----------------------------------------------------------------------------
def test_dossier_root_hash_integrity(sample_objective):
    core = AtlasMissionExecutionCore(mission_id="ATLAS-DOSSIER-TEST", objective=sample_objective)
    for _ in range(5):
        core.advance_sol()
    dossier = core.generate_dossier()
    assert len(dossier.root_hash) == 64
    assert dossier.total_duration_sols == 6


# -----------------------------------------------------------------------------
# 25. Mission OS Create Custom API
# -----------------------------------------------------------------------------
def test_mission_os_create_custom_api():
    custom = mission_os_create_api({
        "mission_id": "ATLAS-CUSTOM-SITE-02",
        "title": "Neretva Vallis Exploration",
        "intent": "Explore channel deposits and establish secondary station.",
        "target_site_id": "SITE-NERETVA-01",
        "target_region": "Neretva Vallis",
        "duration_sols": 45,
    })
    assert custom["mission_id"] == "ATLAS-CUSTOM-SITE-02"
    assert custom["status"] == "EXECUTING"
    assert len(custom["phases"]) == 7


# -----------------------------------------------------------------------------
# 26. Mandatory Scientific Disclosures on Export Records
# -----------------------------------------------------------------------------
def test_mandatory_scientific_disclosures_present():
    core = AtlasMissionExecutionCore(
        mission_id="ATLAS-DISC-TEST",
        objective=MissionObjective(
            objective_id="OBJ-DISC",
            title="Integrity Test",
            raw_intent="Check disclosure",
            target_site_id="SITE-01",
            target_region="Jezero",
        ),
    )
    dossier = core.generate_dossier()
    assert "NASA Space Apps Scientific Integrity Notice" in dossier.mandatory_scientific_disclosure
    assert "not certify physical operational safety" in dossier.mandatory_scientific_disclosure

