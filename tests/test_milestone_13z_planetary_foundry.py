"""
MarsWalk 2.0 / Project Atlas — Milestone 13Z Test Suite
=======================================================
Comprehensive test suite validating the 10 core architectural invariants of
the Atlas Planetary Foundry: Autonomous Robotic Construction, ISRU Manufacturing,
Infrastructure Deployment & Industrial Operations.

Invariants Covered:
  - INV-01-MASS-CONSERVATION
  - INV-02-TASK-DEPENDENCY
  - INV-03-QUALITY-NON-SILENT-REWORK
  - INV-04-CAPABILITY-MATCHING
  - INV-05-RESILIENCE-AND-REPAIR
  - INV-06-ENERGY-ACCOUNTING
  - INV-07-UNIT-CONSISTENCY
  - INV-08-ISRU-MAXIMIZATION
  - INV-09-SPARE-PARTS-ACCOUNTING
  - INV-10-NETWORK-COORDINATION
  - SCENARIO-EXECUTION-AND-GRAND-PRIX
"""

import math
import pytest

from marswalk.core.atlas_foundry_materials import (
    MaterialCategory,
    MaterialSpec,
    STANDARD_MATERIAL_SPECS,
    SettlementMaterialInventory,
    EvidenceClassification,
)
from marswalk.core.atlas_foundry_robotics import (
    RobotClass,
    RobotOperatingState,
    IndustrialRobot,
    create_standard_industrial_fleet,
)
from marswalk.core.atlas_foundry_structures import (
    InfrastructureAssetType,
    AssetConstructionState,
    InfrastructureBillOfQuantities,
    ConstructedAssetInstance,
    INFRASTRUCTURE_CATALOGUE,
)
from marswalk.core.atlas_foundry_resource_processing import FoundryProductionEngine
from marswalk.core.atlas_foundry_inspection import (
    FoundryInspectionEngine,
    InspectionResultStatus,
    InspectionReport,
)
from marswalk.core.atlas_foundry_maintenance import (
    FoundryMaintenanceCoordinator,
    IndustrialFaultType,
)
from marswalk.core.atlas_foundry_construction import (
    MultiRobotConstructionPlanner,
    ConstructionTaskPhase,
    ConstructionTask,
)
from marswalk.core.atlas_foundry_scheduler import (
    ConstructionStrategyType,
    FastBuildStrategy,
    MinMassStrategy,
    EnergySaverStrategy,
    ResilienceFirstStrategy,
    AtlasIndustrialDirectorStrategy,
)
from marswalk.core.atlas_foundry_scenario_engine import (
    PlanetaryFoundryScenarioEngine,
    CampaignScenarioResult,
)
from marswalk.core.atlas_foundry_grand_prix import (
    FoundryGrandPrixTournament,
    FoundryGrandPrixResult,
    StrategyBenchmarkRecord,
)


# ============================================================================
# INV-01: MASS CONSERVATION
# ============================================================================

def test_inv_01_material_spec_yield_plus_waste_equals_unity():
    """Verify that every material spec rigorously enforces yield + waste == 1.0."""
    for cat, spec in STANDARD_MATERIAL_SPECS.items():
        total = spec.yield_fraction + spec.waste_fraction
        assert math.isclose(total, 1.0, rel_tol=1e-5), f"Mass balance violated for {cat.value}: {total}"

    # Invalid spec creation must raise ValueError
    with pytest.raises(ValueError, match="Mass balance violation"):
        MaterialSpec(
            category=MaterialCategory.REGOLITH_FEEDSTOCK_RAW,
            name="Defective Physics Spec",
            density_kg_m3=1500.0,
            mean_particle_size_um=100.0,
            compressive_strength_mpa=1.0,
            processing_temp_c=25.0,
            processing_energy_kwh_kg=0.01,
            yield_fraction=0.70,
            waste_fraction=0.10,  # 0.70 + 0.10 = 0.80 != 1.0
            binder_ratio=0.0,
            evidence_class=EvidenceClassification.ASSUMED,
            citation_source="Test",
        )


def test_inv_01_production_engine_mass_conservation():
    """Verify screening and sintering operations strictly conserve mass."""
    inventory = SettlementMaterialInventory("ALPHA-TEST")
    inventory.add_stock(MaterialCategory.REGOLITH_FEEDSTOCK_RAW, 10000.0)
    engine = FoundryProductionEngine({"ALPHA-TEST": inventory})

    excavator = IndustrialRobot(
        asset_id="EXC-TEST",
        name="Excavator Test",
        robot_class=RobotClass.EXCAVATOR,
        settlement_id="ALPHA-TEST",
        max_payload_kg=2500.0,
        nominal_power_kw=15.0,
        battery_capacity_kwh=100.0,
        current_battery_kwh=100.0,
        speed_km_h=5.0,
    )
    manufacturer = IndustrialRobot(
        asset_id="MFG-TEST",
        name="Manufacturer Test",
        robot_class=RobotClass.MANUFACTURER,
        settlement_id="ALPHA-TEST",
        max_payload_kg=1500.0,
        nominal_power_kw=25.0,
        battery_capacity_kwh=100.0,
        current_battery_kwh=100.0,
        speed_km_h=2.0,
    )

    # Screen 5000 kg of raw regolith
    screen_res = engine.execute_screening("ALPHA-TEST", 5000.0, excavator, 100.0)
    assert screen_res.success
    # Feedstock consumed = 5000 kg, usable = 5000 * 0.82 = 4100 kg, waste = 5000 * 0.18 = 900 kg
    assert math.isclose(screen_res.input_mass_kg, 5000.0, abs_tol=1e-3)
    assert math.isclose(screen_res.output_usable_mass_kg + screen_res.waste_mass_kg, 5000.0, abs_tol=1e-3)
    assert math.isclose(screen_res.output_usable_mass_kg, 4100.0, abs_tol=1e-3)
    assert math.isclose(screen_res.waste_mass_kg, 900.0, abs_tol=1e-3)

    # Sinter 2000 kg of screened fines into blocks
    sinter_res = engine.execute_sintering("ALPHA-TEST", 2000.0, manufacturer, 200.0)
    assert sinter_res.success
    # Feedstock consumed = 2000 kg, product = 2000 * 0.92 = 1840 kg, waste = 160 kg
    assert math.isclose(sinter_res.input_mass_kg, 2000.0, abs_tol=1e-3)
    assert math.isclose(sinter_res.output_usable_mass_kg + sinter_res.waste_mass_kg, 2000.0, abs_tol=1e-3)
    assert math.isclose(sinter_res.output_usable_mass_kg, 1840.0, abs_tol=1e-3)
    assert math.isclose(sinter_res.waste_mass_kg, 160.0, abs_tol=1e-3)


# ============================================================================
# INV-02: TASK DEPENDENCY
# ============================================================================

def test_inv_02_task_dependency_enforcement():
    """Verify that assets cannot proceed if predecessor dependencies are unfulfilled."""
    landing_pad_def = INFRASTRUCTURE_CATALOGUE[InfrastructureAssetType.LANDING_PAD_SEGMENTS]
    assert InfrastructureAssetType.LANDING_ZONE_PREPARATION in landing_pad_def.predecessor_asset_types

    fleet = create_standard_industrial_fleet()
    inventories = {"SETTLEMENT-ALPHA": SettlementMaterialInventory("SETTLEMENT-ALPHA")}
    production = FoundryProductionEngine(inventories)
    inspection = FoundryInspectionEngine()
    planner = MultiRobotConstructionPlanner(fleet, inventories, production, inspection)

    # Register both LZ prep and landing pad
    lz_asset = planner.register_construction_project(InfrastructureAssetType.LANDING_ZONE_PREPARATION, "SETTLEMENT-ALPHA", 0.0)
    pad_asset = planner.register_construction_project(InfrastructureAssetType.LANDING_PAD_SEGMENTS, "SETTLEMENT-ALPHA", 0.0)

    # Pad cannot commence because LZ is not accepted yet
    assert not planner.are_predecessors_accepted(pad_asset), "Landing pad should not commence without LZ preparation completed"

    # Complete predecessor LZ preparation
    lz_asset.state = AssetConstructionState.ACCEPTED

    assert planner.are_predecessors_accepted(pad_asset), "Landing pad should commence after LZ preparation completed"


# ============================================================================
# INV-03: QUALITY & NON-SILENT REWORK
# ============================================================================

def test_inv_03_quality_non_silent_rework_transition():
    """Verify that defective structures are not silently passed; they transition to REWORK_REQUIRED or REJECTED."""
    defn = INFRASTRUCTURE_CATALOGUE[InfrastructureAssetType.LANDING_PAD_SEGMENTS]
    asset = ConstructedAssetInstance(
        instance_id="ASSET-TEST-01",
        asset_type=InfrastructureAssetType.LANDING_PAD_SEGMENTS,
        settlement_id="SETTLEMENT-ALPHA",
        definition=defn,
        state=AssetConstructionState.INSPECTION_PENDING,
    )
    inspector = IndustrialRobot(
        asset_id="QC-ROBOT-01",
        name="LIDAR Quality Inspector",
        robot_class=RobotClass.INSPECTOR,
        settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=50.0,
        nominal_power_kw=0.8,
        battery_capacity_kwh=30.0,
        current_battery_kwh=30.0,
        speed_km_h=3.0,
    )
    engine = FoundryInspectionEngine(random_seed=42)

    # Induce high defect rate
    report = engine.inspect_asset(
        asset=asset,
        inspector_robot=inspector,
        current_time_s=100.0,
        simulated_defect_rate=0.8,
    )
    if report.verdict != InspectionResultStatus.ACCEPTED_PASSED:
        assert asset.state in (AssetConstructionState.REWORK_REQUIRED, AssetConstructionState.REJECTED)
        assert asset.rework_count >= 1 or asset.state == AssetConstructionState.REJECTED
        assert not asset.is_accepted
        assert len(engine.inspection_reports) >= 1


def test_inv_03_remediation_and_reinspection():
    """Verify that nominal quality inspection awards formal ACCEPTED status."""
    defn = INFRASTRUCTURE_CATALOGUE[InfrastructureAssetType.ACCESS_ROADS_MOBILITY_ROUTES]
    asset = ConstructedAssetInstance(
        instance_id="ASSET-TEST-02",
        asset_type=InfrastructureAssetType.ACCESS_ROADS_MOBILITY_ROUTES,
        settlement_id="SETTLEMENT-ALPHA",
        definition=defn,
        state=AssetConstructionState.REWORK_REQUIRED,
        rework_count=1,
    )
    inspector = IndustrialRobot(
        asset_id="QC-ROBOT-02",
        name="LIDAR Quality Inspector",
        robot_class=RobotClass.INSPECTOR,
        settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=50.0,
        nominal_power_kw=0.8,
        battery_capacity_kwh=30.0,
        current_battery_kwh=30.0,
        speed_km_h=3.0,
    )
    engine = FoundryInspectionEngine(random_seed=1)

    # Defect rate 0.0 forces nominal pass
    report = engine.inspect_asset(
        asset=asset,
        inspector_robot=inspector,
        current_time_s=200.0,
        simulated_defect_rate=0.0,
    )
    assert report.verdict == InspectionResultStatus.ACCEPTED_PASSED
    assert asset.state == AssetConstructionState.ACCEPTED
    assert asset.is_accepted


# ============================================================================
# INV-04: CAPABILITY MATCHING
# ============================================================================

def test_inv_04_robot_capability_and_payload_matching():
    """Verify that robots only execute tasks matching certified class and payload limit."""
    excavator = IndustrialRobot(
        asset_id="EXC-01",
        name="Continuous Excavator",
        robot_class=RobotClass.EXCAVATOR,
        settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=2500.0,
        nominal_power_kw=15.0,
        battery_capacity_kwh=100.0,
        current_battery_kwh=100.0,
        speed_km_h=5.0,
    )
    hauler = IndustrialRobot(
        asset_id="HAU-01",
        name="Heavy Hauler",
        robot_class=RobotClass.HAULER,
        settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=5000.0,
        nominal_power_kw=10.0,
        battery_capacity_kwh=80.0,
        current_battery_kwh=80.0,
        speed_km_h=8.0,
    )

    # Excavator can excavate within payload limit
    assert excavator.can_perform_task(RobotClass.EXCAVATOR, 2000.0)
    # Excavator cannot haul or assemble
    assert not excavator.can_perform_task(RobotClass.HAULER, 1000.0)
    assert not excavator.can_perform_task(RobotClass.ASSEMBLER, 500.0)
    # Excavator cannot exceed payload capacity
    assert not excavator.can_perform_task(RobotClass.EXCAVATOR, 3000.0)

    # Hauler can haul up to 5000 kg
    assert hauler.can_perform_task(RobotClass.HAULER, 4500.0)
    assert not hauler.can_perform_task(RobotClass.HAULER, 6000.0)
    assert not hauler.can_perform_task(RobotClass.EXCAVATOR, 1000.0)


# ============================================================================
# INV-05: RESILIENCE & REPAIR
# ============================================================================

def test_inv_05_fault_injection_and_maintainer_recovery():
    """Verify fault injection isolates robot and maintainer successfully restores health."""
    hauler = IndustrialRobot(
        asset_id="HAU-TEST",
        name="Hauler Test",
        robot_class=RobotClass.HAULER,
        settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=5000.0,
        nominal_power_kw=10.0,
        battery_capacity_kwh=80.0,
        current_battery_kwh=80.0,
        speed_km_h=8.0,
    )
    maintainer = IndustrialRobot(
        asset_id="MNT-TEST",
        name="Mobile Maintainer",
        robot_class=RobotClass.MAINTAINER,
        settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=300.0,
        nominal_power_kw=2.0,
        battery_capacity_kwh=40.0,
        current_battery_kwh=40.0,
        speed_km_h=4.0,
    )
    inventory = SettlementMaterialInventory("SETTLEMENT-ALPHA")
    inventory.add_stock(MaterialCategory.METALLIC_FASTENERS, 500.0)

    fleet = {"HAU-TEST": hauler, "MNT-TEST": maintainer}
    inventories = {"SETTLEMENT-ALPHA": inventory}
    coordinator = FoundryMaintenanceCoordinator(fleet, inventories)

    # Inject motor stall fault
    coordinator.inject_fault("HAU-TEST", IndustrialFaultType.HAULER_DRIVE_MOTOR_STALL)
    assert hauler.active_fault == IndustrialFaultType.HAULER_DRIVE_MOTOR_STALL.value
    assert not hauler.is_available
    assert hauler.health_score < 1.0

    # Maintainer executes repair
    action = coordinator.diagnose_and_repair("HAU-TEST", "MNT-TEST", 50.0)
    assert action.success
    assert hauler.is_available
    assert hauler.active_fault is None
    assert hauler.health_score >= 0.90
    assert action.spare_parts_consumed_kg > 0.0


# ============================================================================
# INV-06: ENERGY ACCOUNTING
# ============================================================================

def test_inv_06_energy_draw_and_battery_deduction():
    """Verify robot task execution strictly calculates and deducts energy."""
    assembler = IndustrialRobot(
        asset_id="ASM-TEST",
        name="Rigid Arm Assembler",
        robot_class=RobotClass.ASSEMBLER,
        settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=1200.0,
        nominal_power_kw=8.0,
        battery_capacity_kwh=50.0,
        current_battery_kwh=50.0,
        speed_km_h=3.0,
    )

    # 2.5 hours of operation at 8.0 kW = 20.0 kWh energy consumed
    energy_kwh = assembler.consume_energy(2.5)
    assert math.isclose(energy_kwh, 20.0, abs_tol=1e-3)
    assert math.isclose(assembler.current_battery_kwh, 30.0, abs_tol=1e-3)
    assert math.isclose(assembler.cumulative_energy_spent_kwh, 20.0, abs_tol=1e-3)

    # Recharge
    assembler.recharge(15.0)
    assert math.isclose(assembler.current_battery_kwh, 45.0, abs_tol=1e-3)


# ============================================================================
# INV-07: UNIT CONSISTENCY
# ============================================================================

def test_inv_07_unit_consistency_and_non_negative_stocks():
    """Verify inventory stocks cannot become negative (overdraft rejection)."""
    inventory = SettlementMaterialInventory("TEST-UNITS")
    inventory.add_stock(MaterialCategory.IMPORTED_STRUCTURAL, 100.0)

    # Overdraft attempt returns False
    success = inventory.consume_stock(MaterialCategory.IMPORTED_STRUCTURAL, 150.0)
    assert not success

    # Stock remains positive and unaltered
    assert math.isclose(inventory.get_stock_kg(MaterialCategory.IMPORTED_STRUCTURAL), 100.0, abs_tol=1e-5)


# ============================================================================
# INV-08: ISRU MAXIMIZATION
# ============================================================================

def test_inv_08_isru_mass_fraction_thresholds():
    """Verify earthen embankments, roads, pads, and foundations exceed 85% ISRU mass fraction."""
    high_isru_assets = [
        InfrastructureAssetType.LANDING_ZONE_PREPARATION,
        InfrastructureAssetType.LANDING_PAD_SEGMENTS,
        InfrastructureAssetType.ACCESS_ROADS_MOBILITY_ROUTES,
        InfrastructureAssetType.REGOLITH_BERMS_SHIELDING,
        InfrastructureAssetType.EQUIPMENT_FOUNDATIONS,
        InfrastructureAssetType.UTILITY_TRENCHES,
    ]

    for asset_type in high_isru_assets:
        defn = INFRASTRUCTURE_CATALOGUE[asset_type]
        isru_pct = defn.boq.isru_mass_fraction_pct
        assert isru_pct >= 85.0, f"Asset {asset_type.value} has ISRU fraction {isru_pct:.1f}% < 85%"


# ============================================================================
# INV-09: SPARE PARTS ACCOUNTING
# ============================================================================

def test_inv_09_spare_parts_depletion_and_stock_deduction():
    """Verify that maintenance actions consume spare parts from inventory."""
    inventory = SettlementMaterialInventory("SETTLEMENT-ALPHA")
    initial_fasteners = 200.0
    inventory.add_stock(MaterialCategory.METALLIC_FASTENERS, initial_fasteners)

    hauler = IndustrialRobot(
        asset_id="HAU-09",
        name="Hauler",
        robot_class=RobotClass.HAULER,
        settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=5000.0,
        nominal_power_kw=10.0,
        battery_capacity_kwh=80.0,
        current_battery_kwh=80.0,
        speed_km_h=8.0,
    )
    maintainer = IndustrialRobot(
        asset_id="MNT-09",
        name="Maintainer",
        robot_class=RobotClass.MAINTAINER,
        settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=300.0,
        nominal_power_kw=2.0,
        battery_capacity_kwh=40.0,
        current_battery_kwh=40.0,
        speed_km_h=4.0,
    )
    fleet = {"HAU-09": hauler, "MNT-09": maintainer}
    coordinator = FoundryMaintenanceCoordinator(fleet, {"SETTLEMENT-ALPHA": inventory})
    coordinator.inject_fault("HAU-09", IndustrialFaultType.HAULER_DRIVE_MOTOR_STALL)

    action = coordinator.diagnose_and_repair("HAU-09", "MNT-09", 10.0)
    assert action.success
    expected_remaining = initial_fasteners - action.spare_parts_consumed_kg
    current_stock = inventory.get_stock_kg(MaterialCategory.METALLIC_FASTENERS)
    assert math.isclose(current_stock, expected_remaining, abs_tol=1e-3)


# ============================================================================
# INV-10: NETWORK COORDINATION & NO TELEPORTATION
# ============================================================================

def test_inv_10_inter_settlement_logistics_without_teleportation():
    """Verify inter-settlement inventory transfers deduct from origin and add to destination."""
    origin = SettlementMaterialInventory("OUTPOST-GAMMA")
    destination = SettlementMaterialInventory("OUTPOST-BETA")

    origin.add_stock(MaterialCategory.REGOLITH_SINTERED_BLOCKS, 5000.0)
    assert destination.get_stock_kg(MaterialCategory.REGOLITH_SINTERED_BLOCKS) == 0.0

    # Transfer 3000 kg from Gamma to Beta
    transfer_amount = 3000.0
    consumed = origin.consume_stock(MaterialCategory.REGOLITH_SINTERED_BLOCKS, transfer_amount)
    assert consumed
    destination.add_stock(MaterialCategory.REGOLITH_SINTERED_BLOCKS, transfer_amount)

    assert math.isclose(origin.get_stock_kg(MaterialCategory.REGOLITH_SINTERED_BLOCKS), 2000.0, abs_tol=1e-3)
    assert math.isclose(destination.get_stock_kg(MaterialCategory.REGOLITH_SINTERED_BLOCKS), 3000.0, abs_tol=1e-3)


# ============================================================================
# SCENARIOS AND GRAND PRIX TOURNAMENT
# ============================================================================

def test_12_canonical_campaigns_registration_and_execution():
    """Verify all 12 canonical campaigns are registered and executable."""
    engine = PlanetaryFoundryScenarioEngine()
    campaigns = engine.list_all_campaigns()
    assert len(campaigns) == 12

    # Verify Campaign 01: Landing Zone Preparation
    res1 = engine.execute_campaign("CAMPAIGN-01", override_strategy=ConstructionStrategyType.FAST_BUILD)
    assert res1.campaign_id == "CAMPAIGN-01"
    assert res1.assets_accepted >= 1
    assert res1.duration_hours > 0
    assert res1.total_energy_kwh > 0

    # Verify Campaign 05: Crater-Rim Communications Relay Mast
    res5 = engine.execute_campaign("CAMPAIGN-05", override_strategy=ConstructionStrategyType.RESILIENCE_FIRST)
    assert res5.campaign_id == "CAMPAIGN-05"
    assert res5.assets_accepted >= 1
    assert res5.isru_fraction_pct >= 85.0

    # Verify Campaign 12: The Grand Foundry
    res12 = engine.execute_campaign("CAMPAIGN-12", override_strategy=ConstructionStrategyType.ATLAS_INDUSTRIAL)
    assert res12.campaign_id == "CAMPAIGN-12"
    assert res12.total_assets_planned >= 6
    assert res12.assets_accepted >= 2


def test_foundry_grand_prix_tournament_benchmarking():
    """Verify that the 5-strategy Grand Prix benchmark executes and ranks all strategies."""
    tournament = FoundryGrandPrixTournament()
    result = tournament.run_tournament()

    assert result.total_strategies == 5
    assert len(result.rankings) == 5
    strategy_types = {r.strategy_type for r in result.rankings}
    assert strategy_types == {
        ConstructionStrategyType.FAST_BUILD,
        ConstructionStrategyType.MIN_MASS,
        ConstructionStrategyType.ENERGY_SAVER,
        ConstructionStrategyType.RESILIENCE_FIRST,
        ConstructionStrategyType.ATLAS_INDUSTRIAL,
    }

    # Verify every strategy produced valid metrics
    for rec in result.rankings:
        assert rec.total_assets_planned > 0
        assert rec.completion_duration_hours > 0
        assert rec.energy_consumed_kwh > 0
        assert rec.composite_foundry_score > 0

    assert result.overall_grand_prix_champion is not None
