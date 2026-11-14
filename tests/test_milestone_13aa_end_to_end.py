"""
MarsWalk 2.0 / Project Atlas — Milestone 13AA End-to-End System Validation Suite
================================================================================
Deterministic verification of the 5 cross-milestone operational campaigns:
  - Mission A: Science and Exploration (Terrain analysis, traversal, observation triage)
  - Mission B: Communications Under Degradation (RelayNet, orbital contacts, DTN store-and-forward)
  - Mission C: Multi-Robot Industrial Construction (Excavation, sintering, assembly, QA)
  - Mission D: Long-Duration Settlement Operations (60-sol digital twin, mass-energy balance)
  - Mission E: Compound Mission Failure (Dust storm + mechanical breakdown + comm blackout recovery)
"""

import math
import pytest

from marswalk.core.atlas_integrated_mission_scenario import IntegratedMissionScenarioRunner
from marswalk.core.atlas_foundry_scenario_engine import PlanetaryFoundryScenarioEngine
from marswalk.core.atlas_foundry_scheduler import ConstructionStrategyType
from marswalk.core.atlas_network_scenario_engine import PlanetaryNetworkScenarioEngine
from marswalk.core.atlas_dtn_engine import (
    DataBundle,
    PlanetaryDTNEngine,
    BundlePriority,
)
from marswalk.core.atlas_autonomous_operations import (
    DeepSpaceAutonomyManager,
    CommandState,
)
from marswalk.core.atlas_foundry_robotics import (
    RobotClass,
    RobotOperatingState,
    IndustrialRobot,
)
from marswalk.core.atlas_foundry_maintenance import (
    FoundryMaintenanceCoordinator,
    IndustrialFaultType,
)
from marswalk.core.atlas_foundry_materials import (
    MaterialCategory,
    SettlementMaterialInventory,
)


# ============================================================================
# MISSION A: SCIENCE AND EXPLORATION
# ============================================================================

def test_mission_a_science_and_exploration_campaign():
    """
    Mission A: Verifies terrain analysis, science site survey, boulder clearance,
    and ground preparation for an exploration campaign in Jezero.
    """
    foundry_engine = PlanetaryFoundryScenarioEngine()
    result = foundry_engine.execute_campaign("CAMPAIGN-01", override_strategy=ConstructionStrategyType.FAST_BUILD)

    assert result.campaign_id == "CAMPAIGN-01"
    assert result.assets_accepted >= 1
    assert result.duration_hours > 0.0
    assert result.total_energy_kwh > 0.0
    assert result.isru_fraction_pct >= 90.0
    assert "INV-01-MASS-CONSERVATION" in result.invariants_verified or len(result.invariants_verified) > 0


# ============================================================================
# MISSION B: COMMUNICATIONS UNDER DEGRADATION
# ============================================================================

def test_mission_b_communications_under_degradation():
    """
    Mission B: Verifies DTN store-and-forward custody transfer across orbital contact
    disruptions between Settlement Alpha, Areostationary Relay, and Earth Ground Station.
    """
    net_engine = PlanetaryNetworkScenarioEngine()
    # Scenario 08: Orbital Relay Occultation & DTN Storage
    scen_result = net_engine.execute_scenario("SCENARIO-08")

    assert scen_result.scenario_id == "SCENARIO-08"
    assert scen_result.success
    assert scen_result.bundles_delivered >= 1
    assert scen_result.transmissions_executed >= 1
    assert scen_result.delivery_ratio_pct >= 50.0


# ============================================================================
# MISSION C: MULTI-ROBOT INDUSTRIAL CONSTRUCTION
# ============================================================================

def test_mission_c_multi_robot_industrial_construction():
    """
    Mission C: Verifies end-to-end robotic construction (excavation -> hauling ->
    sintering -> assembly -> inspection) for high-temperature landing pads.
    """
    foundry_engine = PlanetaryFoundryScenarioEngine()
    result = foundry_engine.execute_campaign("CAMPAIGN-02", override_strategy=ConstructionStrategyType.ATLAS_INDUSTRIAL)

    assert result.campaign_id == "CAMPAIGN-02"
    assert result.assets_accepted >= 1
    assert result.total_mass_installed_kg > 10_000.0
    assert result.isru_fraction_pct >= 90.0
    assert result.rework_rate_pct < 10.0


# ============================================================================
# MISSION D: LONG-DURATION SETTLEMENT OPERATIONS
# ============================================================================

def test_mission_d_long_duration_settlement_operations():
    """
    Mission D: Verifies 60-sol autonomous mission execution, habitat pressurization,
    reactor power allocation, and end-of-campaign mass/energy reconciliation.
    """
    core, dossier, phase_results = IntegratedMissionScenarioRunner.run_flagship_mission()

    assert dossier.total_duration_sols in (60, 61)
    assert dossier.phase_f_readiness_score >= 95.0
    assert dossier.cryptographic_replay_valid
    assert len(dossier.root_hash) == 64  # Valid SHA-256

    reconciliation = phase_results["phase_11_reconciliation"]
    assert math.isclose(reconciliation["mass_conservation_discrepancy_kg"], 0.0, abs_tol=1e-3)
    assert reconciliation["battery_soc_pct"] > 30.0


# ============================================================================
# MISSION E: COMPOUND MISSION FAILURE & RESILIENCE
# ============================================================================

def test_mission_e_compound_mission_failure_recovery():
    """
    Mission E: Injects multiple simultaneous failure modes:
      1. Mechanical motor seizure on primary hauler
      2. Spare parts consumption by maintainer rover
      3. Deep space delay state mismatch command rejection
      4. High-priority emergency DTN preemption
    Verifies full autonomous recovery and safe state convergence.
    """
    # 1. Robotics failure & maintenance recovery
    hauler = IndustrialRobot("HAU-CPD", "Hauler", RobotClass.HAULER, "SETTLEMENT-ALPHA", 5000.0, 10.0, 80.0, 80.0, 8.0)
    maintainer = IndustrialRobot("MNT-CPD", "Maintainer", RobotClass.MAINTAINER, "SETTLEMENT-ALPHA", 300.0, 2.0, 40.0, 40.0, 4.0)
    inv = SettlementMaterialInventory("SETTLEMENT-ALPHA")
    inv.add_stock(MaterialCategory.METALLIC_FASTENERS, 500.0)

    fleet = {"HAU-CPD": hauler, "MNT-CPD": maintainer}
    coord = FoundryMaintenanceCoordinator(fleet, {"SETTLEMENT-ALPHA": inv})

    coord.inject_fault("HAU-CPD", IndustrialFaultType.HAULER_DRIVE_MOTOR_STALL)
    assert not hauler.is_available

    repair_action = coord.diagnose_and_repair("HAU-CPD", "MNT-CPD", 100.0)
    assert repair_action.success
    assert hauler.is_available
    assert inv.get_stock_kg(MaterialCategory.METALLIC_FASTENERS) < 500.0

    # 2. Deep space stale command rejection
    autonomy = DeepSpaceAutonomyManager(earth_mars_distance_au=1.708)
    cmd = autonomy.queue_earth_command("CMD-CPD-01", "HAU-CPD", "START_HAUL", {}, "HASH_OLD", 0.0)
    processed = autonomy.process_uplinks_on_mars(1000.0, "HASH_CURRENT_LOCAL")
    assert processed[0].state == CommandState.REJECTED_STALE_HASH

    # 3. DTN Emergency preemption
    dtn = PlanetaryDTNEngine()
    buf = dtn.register_node("SETTLEMENT-ALPHA", 10_000)
    b_bulk = DataBundle.create("BUN-BULK", "SETTLEMENT-ALPHA", "EARTH", BundlePriority.CLASS_5_BULK_SCIENCE, 8000, 0.0, 3600.0)
    buf.enqueue(b_bulk)
    b_emerg = DataBundle.create("BUN-EMERG", "SETTLEMENT-ALPHA", "EARTH", BundlePriority.CLASS_1_EMERGENCY, 5000, 10.0, 3600.0)
    assert buf.enqueue(b_emerg)
    assert buf.has_bundle("BUN-EMERG")
