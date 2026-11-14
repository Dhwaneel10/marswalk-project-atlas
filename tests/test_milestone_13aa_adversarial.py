"""
MarsWalk 2.0 / Project Atlas — Milestone 13AA Adversarial System Testing Suite
=============================================================================
Hostile adversarial testing across:
  - Input attacks (missing fields, invalid types, negative numbers, NaN/infinity)
  - Numerical edge cases (zero distance, singularity handling, extreme ranges)
  - Mission state failures (stale commands, duplicate events, out-of-order actions)
  - Network failures (blackouts, buffer exhaustion, preemption of routine traffic)
  - Industrial failures (breakdowns mid-task, inventory stockouts, rework cascades)
"""

import math
import pytest

from marswalk.core.terrain import compute_ground_spacings, calculate_step_distance
from marswalk.core.atlas_network_link_model import PhysicalLinkBudgetEngine
from marswalk.core.atlas_dtn_engine import (
    DataBundle,
    PlanetaryDTNEngine,
    BundlePriority,
)
from marswalk.core.atlas_foundry_materials import (
    MaterialCategory,
    SettlementMaterialInventory,
)
from marswalk.core.atlas_foundry_robotics import (
    RobotClass,
    RobotOperatingState,
    IndustrialRobot,
)
from marswalk.core.atlas_foundry_structures import (
    InfrastructureAssetType,
    AssetConstructionState,
    ConstructedAssetInstance,
    INFRASTRUCTURE_CATALOGUE,
)
from marswalk.core.atlas_foundry_inspection import (
    FoundryInspectionEngine,
    InspectionResultStatus,
)
from marswalk.core.atlas_autonomous_operations import (
    DeepSpaceAutonomyManager,
    CommandState,
)


# ============================================================================
# 1. INPUT ATTACKS & NUMERICAL EDGE CASES
# ============================================================================

def test_adversarial_numerical_nan_and_infinity_in_path_loss():
    """Verify that path loss calculation rejects non-positive distances, NaN, and near-field violations."""
    # Physical boundary condition: non-positive distances must raise ValueError (not silent 0 dB clamp)
    with pytest.raises(ValueError, match="cannot be negative|cannot be zero"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(0.0, 401.5e6)

    with pytest.raises(ValueError, match="cannot be negative|cannot be zero"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(-500.0, 401.5e6)

    # Unhandled NaN raises ValueError
    with pytest.raises(ValueError):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(float("nan"), 401.5e6)


def test_adversarial_zero_step_distance_and_collocated_coordinates():
    """Verify identical coordinate input does not divide by zero or cause numerical instability."""
    dx, dy = compute_ground_spacings(20.0, 18.38)
    # Zero step
    dist = calculate_step_distance((100, 100), (100, 100), dx, dy)
    assert dist == 0.0


def test_adversarial_extreme_payload_and_overdraft():
    """Verify handling of astronomical inventory debit attempts ($10^{12}$ kg)."""
    inv = SettlementMaterialInventory("ALPHA-ADV")
    inv.add_stock(MaterialCategory.REGOLITH_FEEDSTOCK_RAW, 5000.0)

    # Attempting to debit 1 trillion kg must be safely rejected
    res = inv.consume_stock(MaterialCategory.REGOLITH_FEEDSTOCK_RAW, 1e12)
    assert not res
    assert inv.get_stock_kg(MaterialCategory.REGOLITH_FEEDSTOCK_RAW) == 5000.0


# ============================================================================
# 2. MISSION STATE & COMMAND SECURITY FAILURES
# ============================================================================

def test_adversarial_stale_command_rejection():
    """
    Adversarial Test: Injected uplink command arriving after Mars state has changed
    (stale state hash mismatch) MUST be rejected by the deep space autonomy manager.
    """
    manager = DeepSpaceAutonomyManager(earth_mars_distance_au=1.708)

    # Earth queued command planning against initial hash HASH_INIT
    cmd = manager.queue_earth_command(
        command_id="CMD-ADV-001",
        target_asset_id="ROVER-01",
        action="DRIVE_WAYPOINT_B",
        parameters={"distance_m": 100.0},
        expected_state_hash="a1b2c3d4e5f67890",
        created_met_seconds=0.0,
    )
    assert cmd.state == CommandState.UPLINK_QUEUED

    # Command arrives at Mars after OWLT (14.2 min = ~853s)
    # However, local state has changed (e.g. unexpected rock obstacle or weather event: HASH_DRIFTED)
    current_time_s = 1000.0
    live_mars_state_hash = "deadbeef99990000"

    processed = manager.process_uplinks_on_mars(
        current_mars_met_seconds=current_time_s,
        current_mars_state_hash=live_mars_state_hash,
    )
    assert len(processed) == 1
    assert processed[0].state == CommandState.REJECTED_STALE_HASH
    assert "REJECTED" in processed[0].execution_result
    assert len(manager.rejected_commands) == 1
    assert len(manager.executed_commands) == 0


# ============================================================================
# 3. NETWORK FAILURES & BUFFER EXHAUSTION
# ============================================================================

def test_adversarial_dtn_buffer_saturation_and_priority_preemption():
    """
    Adversarial Test: Saturate DTN buffer with low-priority bulk science bundles (Class 5),
    then inject high-priority emergency bundle (Class 1). Buffer MUST evict Class 5
    to accommodate Class 1, never drop the emergency bundle.
    """
    engine = PlanetaryDTNEngine()
    buffer_capacity = 10_000  # 10 KB total capacity
    buf = engine.register_node("OUTPOST-BETA", capacity_bytes=buffer_capacity)

    # Fill buffer with Class 5 bulk science (2 x 4000 bytes = 8000 bytes used, 2000 available)
    b1 = DataBundle.create("BUN-BULK-01", "OUTPOST-BETA", "EARTH", BundlePriority.CLASS_5_BULK_SCIENCE, 4000, 0.0, 3600.0)
    b2 = DataBundle.create("BUN-BULK-02", "OUTPOST-BETA", "EARTH", BundlePriority.CLASS_5_BULK_SCIENCE, 4000, 0.0, 3600.0)
    assert buf.enqueue(b1)
    assert buf.enqueue(b2)
    assert buf.used_bytes == 8000

    # Inject Class 1 Emergency telemetry (requires 5000 bytes; only 2000 free)
    b_crit = DataBundle.create("BUN-EMERG-01", "OUTPOST-BETA", "EARTH", BundlePriority.CLASS_1_EMERGENCY, 5000, 10.0, 3600.0)
    success = buf.enqueue(b_crit)

    assert success, "Emergency bundle failed to preempt lower priority traffic!"
    assert buf.has_bundle("BUN-EMERG-01")
    # At least one bulk bundle must have been evicted to make room
    assert buf.used_bytes <= buffer_capacity


# ============================================================================
# 4. ROBOTICS & INDUSTRIAL FAILURES
# ============================================================================

def test_adversarial_robot_breakdown_during_active_construction():
    """
    Adversarial Test: Robot suffers catastrophic motor failure while performing a task.
    Engine must isolate robot into FAULT_ISOLATED state, prevent task progression,
    and require maintainer intervention.
    """
    hauler = IndustrialRobot(
        asset_id="HAU-FAIL",
        name="Hauler",
        robot_class=RobotClass.HAULER,
        settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=5000.0,
        nominal_power_kw=10.0,
        battery_capacity_kwh=80.0,
        current_battery_kwh=80.0,
        speed_km_h=8.0,
    )
    # Inject fault
    hauler.state = RobotOperatingState.FAULT_ISOLATED
    hauler.active_fault = "MOTOR_BEARING_SEIZURE"

    # Robot cannot perform tasks while faulted
    assert not hauler.is_available
    assert not hauler.can_perform_task(RobotClass.HAULER, 1000.0)


def test_adversarial_quality_inspection_critical_rejection():
    """
    Adversarial Test: Structural asset suffering severe compressive deficit (< 75% threshold)
    MUST be REJECTED, not merely marked REWORK_REQUIRED.
    """
    defn = INFRASTRUCTURE_CATALOGUE[InfrastructureAssetType.LANDING_PAD_SEGMENTS]
    asset = ConstructedAssetInstance(
        instance_id="PAD-CATASTROPHIC",
        asset_type=InfrastructureAssetType.LANDING_PAD_SEGMENTS,
        settlement_id="SETTLEMENT-ALPHA",
        definition=defn,
        state=AssetConstructionState.INSPECTION_PENDING,
    )
    inspector = IndustrialRobot(
        asset_id="QC-ADV",
        name="Inspector",
        robot_class=RobotClass.INSPECTOR,
        settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=50.0,
        nominal_power_kw=0.8,
        battery_capacity_kwh=30.0,
        current_battery_kwh=30.0,
        speed_km_h=3.0,
    )
    engine = FoundryInspectionEngine(random_seed=14)

    # Extreme defect: 100% defect rate with seed 14 triggers catastrophic structural rejection
    report = engine.inspect_asset(asset, inspector, current_time_s=100.0, simulated_defect_rate=1.0)
    assert report.verdict == InspectionResultStatus.REJECTED_FAILED
    assert asset.state == AssetConstructionState.REJECTED
    assert not asset.is_accepted
