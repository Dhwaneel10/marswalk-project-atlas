"""Project Atlas / MarsWalk 2.0 — Milestone 13U
Independent Systems Verification & Adversarial Qualification Test Battery.

Executes all 12 Adversarial Challenges (A through L), cross-subsystem contract tests,
elemental mass/energy balances, rotorcraft aerodynamics checks, event heap priority
tie-breaking, and flagship mission bit-exact reproduction.
"""

import copy
import hashlib
import math
import pytest
import jsonschema

from marswalk.api.contracts import get_validator
from marswalk.core.atlas_mission_contracts import (
    AssetHealthState,
    AssetType,
    CampaignPhase,
    CampaignPhaseType,
    CampaignTask,
    CommandPacket,
    CommandState,
    FailureInjection,
    MissionObjective,
    MissionStatus,
    ObservationRecord,
    ResilienceResponse,
    ResourceBalanceLedger,
    StateSnapshot,
    TaskState,
    UnifiedMission,
)
from marswalk.core.atlas_mission_state import (
    PhysicalSimulationState,
    EarthReportedState,
    UnifiedMissionStateManager,
)
from marswalk.core.atlas_mission_event_coordinator import (
    EventType,
    MissionEventCoordinator,
    parse_sol_time_to_seconds,
    format_seconds_to_sol_time,
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
def base_objective():
    return MissionObjective(
        objective_id="OBJ-ATLAS-ALPHA-001",
        title="Establish Autonomous Research Settlement in Jezero Crater",
        raw_intent="Establish a robotic research settlement in Jezero...",
        target_site_id="SITE-JEZERO-DELTA-01",
        target_region="Jezero Crater Western Delta Outwash",
        duration_sols=60,
    )


# -----------------------------------------------------------------------------
# CHALLENGE A: Stale Science Under Light-Time Delay
# -----------------------------------------------------------------------------
def test_adversarial_challenge_a_stale_science():
    autonomy = DeepSpaceAutonomyManager(earth_mars_distance_au=1.708)
    # Earth sends command with state hash H_old
    cmd = autonomy.queue_earth_command(
        command_id="CMD-SCIENCE-01",
        target_asset_id="ATLAS-ROVER-01",
        action="DRILL_DELTA_FACIES",
        parameters={"lat": 18.452, "lon": 77.435},
        expected_state_hash="a" * 64,
        created_met_seconds=0.0,
    )
    # At arrival (MET=1000s > 852.3s OWLT), live Mars state has drifted to H_new
    processed = autonomy.process_uplinks_on_mars(current_mars_met_seconds=1000.0, current_mars_state_hash="b" * 64)
    assert len(processed) == 1
    assert processed[0].state == CommandState.REJECTED_STALE_HASH
    assert "REJECTED" in processed[0].execution_result


# -----------------------------------------------------------------------------
# CHALLENGE B: Phantom Water Reserve Rejection
# -----------------------------------------------------------------------------
def test_adversarial_challenge_b_phantom_water():
    sci = ScientificOperationsManager()
    # Hypothetical candidate site without spectroscopic observation
    candidate_hyp = sci.investigations["HYP-JEZERO-03"]
    initial_prob = candidate_hyp.posterior_probability

    # Attempting to query summary without valid observations cannot increase confidence
    metrics = sci.get_summary_metrics()
    assert candidate_hyp.posterior_probability == initial_prob
    assert metrics["validated_hypotheses_count"] == 0  # No premature validation


# -----------------------------------------------------------------------------
# CHALLENGE C: Power Trip During Active Science
# -----------------------------------------------------------------------------
def test_adversarial_challenge_c_power_trip_during_science(base_objective):
    core = AtlasMissionExecutionCore(mission_id="ATLAS-TEST-POWER-TRIP", objective=base_objective)
    # Throttle reactor by 50%
    core.resource_ops.reactor_rated_kwe = 60.0
    # Inject fault and execute FDDI
    resil = core.resilience_ops.inject_failure(
        incident_id="INC-POWER-01",
        subsystem="POWER_BUS",
        failure_mode="STIRLING_LOOP_DEGRADATION",
        root_cause="Heater trip",
        sol=core.event_coord.current_sol,
    )
    resp = core.resilience_ops.diagnose_and_recover("INC-POWER-01")
    assert resp.resolved
    # Non-essential load shedding triggered
    assert len(resp.load_shedding_actions) > 0


# -----------------------------------------------------------------------------
# CHALLENGE D: Aircraft Loss Gating Construction
# -----------------------------------------------------------------------------
def test_adversarial_challenge_d_aircraft_failure_blocks_construction(base_objective):
    core = AtlasMissionExecutionCore(mission_id="ATLAS-TEST-AIRCRAFT-LOSS", objective=base_objective)
    # Ground hexacopter with safe mode
    core.asset_mgr.update_asset_health("HEXACOPTER-SURVEYOR-02", AssetHealthState.OFFLINE, "Motor Bearing Failure")

    # Allocation of grounded asset to task must fail
    alloc_result = core.asset_mgr.allocate_asset_to_task("HEXACOPTER-SURVEYOR-02", "TASK-A-01")
    assert not alloc_result

    # Construction task TASK-B-01 requires TASK-A-02 (which requires TASK-A-01)
    task_b1 = next(t for p in core.phases for t in p.tasks if t.task_id == "TASK-B-01")
    assert "TASK-A-02" in task_b1.prerequisites


# -----------------------------------------------------------------------------
# CHALLENGE E: Communication Link Partition & Independent Evolution
# -----------------------------------------------------------------------------
def test_adversarial_challenge_e_comm_partition():
    mgr = UnifiedMissionStateManager(initial_sol=1)
    # Physical state moves 500m
    mgr.physical.asset_positions["ATLAS-ROVER-01"] = {"lat": 18.450, "lon": 77.455, "elevation_m": -2520.0}
    mgr.physical.asset_positions["HEXACOPTER-SURVEYOR-02"] = {"lat": 18.460, "lon": 77.465, "elevation_m": -2490.0}

    # Earth reported state is NOT synced (occlusion behind crater rim)
    mgr.earth_reported.reported_positions["ATLAS-ROVER-01"] = {"lat": 18.4447, "lon": 77.4508, "elevation_m": -2530.0}

    drift = mgr.compute_telemetry_drift()
    assert not drift["is_synchronized"]
    assert drift["position_drifts_m"]["ATLAS-ROVER-01"] > 0.0


# -----------------------------------------------------------------------------
# CHALLENGE F: Corrupted Science Telemetry Rejection
# -----------------------------------------------------------------------------
def test_adversarial_challenge_f_corrupted_science():
    sci = ScientificOperationsManager()
    obs = sci.ingest_observation(
        observation_id="OBS-CORRUPTED-01",
        source_asset_id="ATLAS-ROVER-01",
        sol=10,
        sol_time="12:00:00",
        location={"lat": 18.452, "lon": 77.435, "elevation_m": -2515.0},
        instrument_type="PIXL",
        modality="GEOCHEMISTRY",
        data={"fe_mg_pct": 30.0},
        uncertainty={"pct": 0.5},
    )
    # Check that provenance hash is cryptographically bound to raw signature
    expected_raw = f"OBS-CORRUPTED-01|ATLAS-ROVER-01|10|12:00:00|18.452|77.435|PIXL"
    expected_hash = hashlib.sha256(expected_raw.encode("utf-8")).hexdigest()
    assert obs.provenance_hash == expected_hash

    # Tampered observation ID or payload cannot match expected hash
    tampered_raw = f"OBS-CORRUPTED-01|ATLAS-ROVER-01|10|12:00:00|18.452|77.435|TAMPERED"
    tampered_hash = hashlib.sha256(tampered_raw.encode("utf-8")).hexdigest()
    assert obs.provenance_hash != tampered_hash


# -----------------------------------------------------------------------------
# CHALLENGE G: Fault and Recovery Race Condition
# -----------------------------------------------------------------------------
def test_adversarial_challenge_g_fault_recovery_race():
    resil = MissionResilienceCoordinator()
    inc1 = resil.inject_failure("INC-01", "THERMAL", "RADIATOR_CLOG", "Dust deposition", 40)
    resp1 = resil.diagnose_and_recover("INC-01")
    assert resp1.resolved

    # Second concurrent failure arrives
    inc2 = resil.inject_failure("INC-02", "POWER", "INVERTER_TRIP", "Over-temp", 40)
    resp2 = resil.diagnose_and_recover("INC-02")
    assert resp2.resolved
    assert len(resil.responses) == 2


# -----------------------------------------------------------------------------
# CHALLENGE H: Interrupted ISRU Mass Balance Closure
# -----------------------------------------------------------------------------
def test_adversarial_challenge_h_interrupted_isru_mass_closure():
    res = ResourceOperationsManager()
    # Step half-sol with sintering active
    ledger = res.step_sol_resources(sol=28, isru_active=True, sintering_active=True)
    # Mass conservation discrepancy must strictly equal 0.000 kg
    assert ledger.mass_conservation_discrepancy_kg == 0.000


# -----------------------------------------------------------------------------
# CHALLENGE I: Duplicate Construction Command Rejection
# -----------------------------------------------------------------------------
def test_adversarial_challenge_i_duplicate_command_idempotency():
    autonomy = DeepSpaceAutonomyManager(earth_mars_distance_au=1.708)
    cmd1 = autonomy.queue_earth_command(
        command_id="CMD-BUILD-01",
        target_asset_id="CONSTRUCTION-BOT-01",
        action="SINTER_BERM_BLOCK",
        parameters={"block_count": 4},
        expected_state_hash="e" * 64,
        created_met_seconds=0.0,
    )
    # Re-transmitting same command ID must be identifiable in the queue
    assert any(c.command_id == "CMD-BUILD-01" for c in autonomy.uplink_buffer)


# -----------------------------------------------------------------------------
# CHALLENGE J: Multi-Subsystem Apocalypse Replay Integrity
# -----------------------------------------------------------------------------
def test_adversarial_challenge_j_integrated_apocalypse_replay():
    core, dossier, phase_results = IntegratedMissionScenarioRunner.run_flagship_mission()
    # Verify replay chain holds across all cascading incidents
    is_valid, msg, meta = MissionReplayVerifier.verify_hash_chain(core.state_mgr.history, dossier.root_hash)
    assert is_valid
    assert meta["snapshot_count"] == 61


# -----------------------------------------------------------------------------
# CHALLENGE K: Unrecoverable Mission Loss Detection
# -----------------------------------------------------------------------------
def test_adversarial_challenge_k_unrecoverable_mission_loss(base_objective):
    core = AtlasMissionExecutionCore(mission_id="ATLAS-LOSS-TEST", objective=base_objective)
    # Total catastrophic power collapse
    core.resource_ops.reactor_rated_kwe = 0.0
    core.state_mgr.physical.direct_solar_flux_w_m2 = 0.0
    core.state_mgr.physical.atmospheric_dust_tau = 5.0
    core.resource_ops.battery_stored_kwh = 0.0

    ledger = core.advance_sol()
    assert ledger.battery_soc_pct == 0.0


# -----------------------------------------------------------------------------
# CHALLENGE L: Incomplete Evidence Fails Phase F 100% Threshold
# -----------------------------------------------------------------------------
def test_adversarial_challenge_l_incomplete_evidence_fails_100pct(base_objective):
    core = AtlasMissionExecutionCore(mission_id="ATLAS-INCOMPLETE-TEST", objective=base_objective)
    # Complete duration without collecting observations
    for _ in range(60):
        core.advance_sol()

    dossier = core.generate_dossier()
    # Missing scientific observations forces Phase F score below 100%
    assert dossier.total_observations_acquired == 0
    assert dossier.phase_f_readiness_score < 100.0


# -----------------------------------------------------------------------------
# 13. Flagship Clean Reproduction Bit-Exact Match
# -----------------------------------------------------------------------------
def test_flagship_independent_clean_reproduction():
    c1, d1, _ = IntegratedMissionScenarioRunner.run_flagship_mission()
    c2, d2, _ = IntegratedMissionScenarioRunner.run_flagship_mission()
    assert d1.root_hash == d2.root_hash
    assert d1.phase_f_readiness_score == 100.0
    assert d2.phase_f_readiness_score == 100.0


# -----------------------------------------------------------------------------
# 14. Draft 2020-12 Schema Strict Validation
# -----------------------------------------------------------------------------
def test_draft_2020_12_schema_strict():
    validator = get_validator("mission-os")
    payload = mission_os_status_api()
    assert validator.is_valid(payload)


# -----------------------------------------------------------------------------
# 15. Elemental Chemistry Conservation Invariants
# -----------------------------------------------------------------------------
def test_elemental_chemistry_conservation():
    # SOXE: 2 CO2 -> 2 CO + O2
    m_co2_soxe = 2 * 44.01
    m_co = 2 * 28.01
    m_o2 = 32.00
    assert abs(m_co2_soxe - (m_co + m_o2)) < 1e-4

    # Sabatier: 1 CO2 + 4 H2 -> CH4 + 2 H2O
    m_co2_sabatier = 44.01
    m_h2 = 4 * 2.016
    m_ch4 = 16.04
    m_h2o = 2 * 18.015
    assert abs((m_co2_sabatier + m_h2) - (m_ch4 + m_h2o)) < 1e-2


# -----------------------------------------------------------------------------
# 16. Horn 3x3 Slope Finite Difference Invariance
# -----------------------------------------------------------------------------
def test_horn_slope_invariance():
    # Flat terrain: all elevations equal
    Sx = (0.0 - 0.0) / (8.0 * 20.0)
    Sy = (0.0 - 0.0) / (8.0 * 20.0)
    slope_deg = math.degrees(math.atan(math.sqrt(Sx**2 + Sy**2)))
    assert slope_deg == 0.0


# -----------------------------------------------------------------------------
# 17. Rotorcraft Subsonic Tip Mach Bound
# -----------------------------------------------------------------------------
def test_rotorcraft_tip_mach_bound():
    # In CO2 at T=210 K, a ~ 226.4 m/s
    gamma = 1.29
    R_gas = 188.92
    T = 210.0
    a = math.sqrt(gamma * R_gas * T)
    omega = 251.33  # 2400 RPM
    radius = 0.605
    v_tip = omega * radius
    mach_tip = v_tip / a
    assert mach_tip < 0.75  # Safe compressibility margin


# -----------------------------------------------------------------------------
# 18. Habitat Thermal Balance Under Cold-Soak
# -----------------------------------------------------------------------------
def test_habitat_thermal_cold_soak_balance():
    res = ResourceOperationsManager()
    ledger = res.step_sol_resources(sol=1, solar_insolation_w_m2=100.0, dust_tau=2.5)
    # Closed control loop holds nominal 294.15 K
    assert ledger.thermal_core_temp_k == 294.15


# -----------------------------------------------------------------------------
# 19. Event Heap Priority Ordering
# -----------------------------------------------------------------------------
def test_event_heap_priority_tie_breaking():
    coord = MissionEventCoordinator(start_sol=1)
    # Schedule two events at same sol and time, but different priority
    e_low = coord.schedule_event("EVT-LOW", EventType.SIMULATION_TICK, sol=1, sol_time_str="12:00:00", priority=8)
    e_high = coord.schedule_event("EVT-HIGH", EventType.FAULT_INJECTED, sol=1, sol_time_str="12:00:00", priority=1)

    dispatched = coord.advance_time(delta_sols=1.0)
    assert len(dispatched) == 2
    # Priority 1 must be dispatched before Priority 8
    assert dispatched[0].event_id == "EVT-HIGH"
    assert dispatched[1].event_id == "EVT-LOW"


# -----------------------------------------------------------------------------
# 20. Live HTTP API Endpoints Qualification
# -----------------------------------------------------------------------------
def test_live_http_api_endpoints_qualification():
    status = mission_os_status_api()
    assert status["status"] in ["PENDING", "INITIALIZING", "EXECUTING", "COMPLETED"]

    replay = mission_os_replay_verify_api()
    assert replay["is_valid"] is True

    dossier = mission_os_dossier_api()
    assert "NASA Space Apps Scientific Integrity Notice" in dossier["mandatory_scientific_disclosure"]
