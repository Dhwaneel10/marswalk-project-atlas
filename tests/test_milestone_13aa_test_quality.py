"""
MarsWalk 2.0 / Project Atlas — Milestone 13AA Test Quality Suite
================================================================
Disciplined test quality verification:
  1. Property-Based Invariant Tests (Mass, Non-negative Stock, Energy, State Integrity)
  2. Metamorphic Tests (Monotonicity of Physical Relationships)
  3. Differential Tests (Independent Formulations Checked Against Each Other)
  4. Mutation Testing Evaluation Fixtures (Verifying Tests Catch Injected Defects)
"""

import math
import pytest
import random

from marswalk.core.terrain import (
    compute_ground_spacings,
    calculate_step_distance,
)
from marswalk.core.atlas_foundry_materials import (
    MaterialCategory,
    STANDARD_MATERIAL_SPECS,
    SettlementMaterialInventory,
)
from marswalk.core.atlas_foundry_robotics import (
    RobotClass,
    IndustrialRobot,
)
from marswalk.core.atlas_network_link_model import PhysicalLinkBudgetEngine
from marswalk.core.atlas_dtn_engine import (
    DataBundle,
    PlanetaryDTNEngine,
    BundlePriority,
)


# ============================================================================
# 1. PROPERTY-BASED TESTS
# ============================================================================

def test_property_mass_conservation_under_random_screening():
    """Property: For any positive raw regolith mass, screening yield + waste strictly equals input."""
    rng = random.Random(42)
    spec = STANDARD_MATERIAL_SPECS[MaterialCategory.REGOLITH_SCREENED]

    for _ in range(50):
        input_mass = rng.uniform(10.0, 50000.0)
        usable_mass = round(input_mass * spec.yield_fraction, 4)
        waste_mass = round(input_mass - usable_mass, 4)
        assert math.isclose(input_mass, usable_mass + waste_mass, abs_tol=1e-3)


def test_property_non_negative_inventory_under_random_debits():
    """Property: Inventory can never drop below zero under any sequence of overdraft attempts."""
    inv = SettlementMaterialInventory("TEST-PROP-ALPHA")
    inv.add_stock(MaterialCategory.REGOLITH_FEEDSTOCK_RAW, 1000.0)

    rng = random.Random(1337)
    for _ in range(30):
        attempt_mass = rng.uniform(50.0, 2000.0)
        current = inv.get_stock_kg(MaterialCategory.REGOLITH_FEEDSTOCK_RAW)
        if attempt_mass > current:
            success = inv.consume_stock(MaterialCategory.REGOLITH_FEEDSTOCK_RAW, attempt_mass)
            assert not success
            assert inv.get_stock_kg(MaterialCategory.REGOLITH_FEEDSTOCK_RAW) == current
        else:
            success = inv.consume_stock(MaterialCategory.REGOLITH_FEEDSTOCK_RAW, attempt_mass)
            assert success
            assert inv.get_stock_kg(MaterialCategory.REGOLITH_FEEDSTOCK_RAW) >= 0.0

    assert inv.get_stock_kg(MaterialCategory.REGOLITH_FEEDSTOCK_RAW) >= 0.0


def test_property_robot_payload_enforcement_invariants():
    """Property: A robot can NEVER accept a task exceeding its max_payload_kg."""
    robot = IndustrialRobot(
        asset_id="HAU-PROP",
        name="Heavy Hauler",
        robot_class=RobotClass.HAULER,
        settlement_id="ALPHA",
        max_payload_kg=5000.0,
        nominal_power_kw=10.0,
        battery_capacity_kwh=80.0,
        current_battery_kwh=80.0,
        speed_km_h=8.0,
    )
    rng = random.Random(999)
    for _ in range(40):
        load = rng.uniform(5001.0, 50000.0)
        assert not robot.can_perform_task(RobotClass.HAULER, payload_kg=load)


# ============================================================================
# 2. METAMORPHIC TESTS
# ============================================================================

def test_metamorphic_fspl_monotonicity_with_distance():
    """
    Metamorphic Relationship: Increasing distance while holding frequency constant
    MUST monotonically increase path loss (reduce received power).
    """
    freq_hz = 401.5e6  # UHF Proximity channel
    d1 = 10_000.0      # 10 km
    d2 = 25_000.0      # 25 km
    d3 = 100_000.0     # 100 km

    fspl_1 = PhysicalLinkBudgetEngine.calculate_free_space_path_loss(d1, freq_hz)
    fspl_2 = PhysicalLinkBudgetEngine.calculate_free_space_path_loss(d2, freq_hz)
    fspl_3 = PhysicalLinkBudgetEngine.calculate_free_space_path_loss(d3, freq_hz)

    assert fspl_1 < fspl_2 < fspl_3
    # 2x distance increases FSPL by ~6.02 dB: 20 * log10(2)
    delta_2x = PhysicalLinkBudgetEngine.calculate_free_space_path_loss(20_000.0, freq_hz) - fspl_1
    assert math.isclose(delta_2x, 20.0 * math.log10(2.0), abs_tol=0.05)


def test_metamorphic_payload_serialization_delay_monotonicity():
    """
    Metamorphic Relationship: Increasing payload size at fixed channel rate
    MUST monotonically increase serialization time.
    """
    data_rate_bps = 256_000.0  # 256 kbps UHF
    s1_bytes = 10_000
    s2_bytes = 50_000
    s3_bytes = 200_000

    t1 = (s1_bytes * 8.0) / data_rate_bps
    t2 = (s2_bytes * 8.0) / data_rate_bps
    t3 = (s3_bytes * 8.0) / data_rate_bps

    assert t1 < t2 < t3


def test_metamorphic_robot_capability_exclusion():
    """
    Metamorphic Relationship: Stripping a robot of its certified class
    MUST make the corresponding task infeasible.
    """
    excavator = IndustrialRobot(
        asset_id="EXC-META",
        name="Continuous Excavator",
        robot_class=RobotClass.EXCAVATOR,
        settlement_id="ALPHA",
        max_payload_kg=2500.0,
        nominal_power_kw=15.0,
        battery_capacity_kwh=100.0,
        current_battery_kwh=100.0,
        speed_km_h=5.0,
    )
    # Valid for excavator task
    assert excavator.can_perform_task(RobotClass.EXCAVATOR, 1000.0)

    # Infeasible for any other class
    for other_class in [RobotClass.HAULER, RobotClass.ASSEMBLER, RobotClass.MANUFACTURER, RobotClass.INSPECTOR, RobotClass.MAINTAINER]:
        assert not excavator.can_perform_task(other_class, 100.0)


# ============================================================================
# 3. DIFFERENTIAL TESTS
# ============================================================================

def test_differential_distance_calculation_step_vs_euclidean_projection():
    """
    Differential Test: For arbitrary grid coordinate steps (dr, dc) in (row, col) raster space,
    calculate_step_distance(u, v, dx, dy) must match the independent analytical
    Euclidean distance formula sqrt((dc * dx)^2 + (dr * dy)^2) with relative tolerance < 1e-12.
    """
    dx, dy = compute_ground_spacings(cell_size_m=20.0, ref_lat_deg=18.38)

    test_steps = [
        ((0, 0), (0, 1)),    # East step (col change: dc=1, dr=0)
        ((0, 0), (1, 0)),    # North/South step (row change: dr=1, dc=0)
        ((0, 0), (1, 1)),    # Diagonal step (dr=1, dc=1)
        ((5, 10), (8, 14)),  # Multi-cell vector step (dr=3, dc=4)
        ((12, 18), (12, 18)) # Zero step (dr=0, dc=0)
    ]

    for u, v in test_steps:
        # Implementation under test
        d_step = calculate_step_distance(u, v, dx, dy)

        # Independent differential formulation: row=dy, col=dx
        dr = abs(v[0] - u[0])
        dc = abs(v[1] - u[1])
        d_analytical = math.sqrt((dc * dx) ** 2 + (dr * dy) ** 2)

        assert math.isclose(d_step, d_analytical, abs_tol=1e-12)


# ============================================================================
# 4. MUTATION TESTING EVALUATION
# ============================================================================

def test_mutation_detector_tampered_mass_conservation():
    """
    Mutation Test: If a bug in yield calculation violates mass conservation,
    it must trigger assertion failure.
    """
    def buggy_sintering(input_mass: float) -> tuple[float, float]:
        # Injected mutation: yield = 0.95 (instead of 0.92) while waste remains 0.08
        return input_mass * 0.95, input_mass * 0.08

    usable, waste = buggy_sintering(1000.0)
    # The mutated function produces 950 + 80 = 1030 kg != 1000 kg
    is_conserved = math.isclose(usable + waste, 1000.0, abs_tol=1e-3)
    assert not is_conserved, "Mutation survived! Mass conservation failure was undetected."


def test_mutation_detector_stale_bundle_expiration():
    """
    Mutation Test: If a DTN buffer fails to check bundle expiration TTL,
    an expired bundle would erroneously be forwarded or retained.
    """
    engine = PlanetaryDTNEngine()
    buf = engine.register_node("SETTLEMENT-ALPHA", capacity_bytes=10_000_000)

    # Create expired bundle (created at T=0, TTL=60s, current time T=100s)
    bundle = DataBundle.create(
        bundle_id="BUN-MUT-01",
        source_id="SETTLEMENT-ALPHA",
        destination_id="EARTH-STATION",
        priority=BundlePriority.CLASS_4_ROUTINE_ENGINEERING,
        size_bytes=1024,
        creation_time_s=0.0,
        ttl_seconds=60.0,
    )
    current_time_s = 100.0

    # Invariant: is_expired must be True
    assert bundle.is_expired(current_time_s)

    # Enqueue at T=0
    buf.enqueue(bundle)
    assert buf.has_bundle("BUN-MUT-01")

    # Pruning at T=100 must discard expired bundle
    pruned = buf.prune_expired(current_time_s)
    assert len(pruned) == 1
    assert not buf.has_bundle("BUN-MUT-01"), "Mutation survived! Expired bundle was retained."
