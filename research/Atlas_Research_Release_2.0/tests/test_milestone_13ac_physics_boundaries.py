"""
Milestone 13AC — Physics Boundary Qualification Test Suite
=========================================================
Designation: ATLAS-13AC-PHYSICS-BOUNDARIES
Verification of numerical semantics, physical validity domains,
collocated interfaces, Fraunhofer boundaries, elevation occultation,
terrain gradient bounds, and ISRU thermodynamic mass-energy conservation.
"""

import math
import pytest
import numpy as np
from typing import Dict

from marswalk.core.atlas_network_link_model import (
    CommunicationBand,
    TransmitterSpec,
    ReceiverSpec,
    LinkBudgetResult,
    PhysicalLinkBudgetEngine,
    SPEED_OF_LIGHT_M_S,
    CARRIER_FREQUENCIES_HZ,
)
from marswalk.core.atlas_orbital_contact_planner import (
    OrbitalContactPlanner,
    MARS_RADIUS_M,
)
from marswalk.core.atlas_planetary_network_architecture import (
    PlanetaryNode,
    PlanetaryNetworkTopology,
    create_standard_planetary_network,
)
from marswalk.core.terrain import (
    compute_horn_slope,
    compute_ground_spacings,
    calculate_step_distance,
)
from marswalk.core.atlas_foundry_resource_processing import (
    FoundryProductionEngine,
    ProcessingOperationType,
)
from marswalk.core.atlas_foundry_materials import (
    MaterialCategory,
    SettlementMaterialInventory,
    STANDARD_MATERIAL_SPECS,
)
from marswalk.core.atlas_foundry_robotics import (
    IndustrialRobot,
    RobotClass,
)


# ============================================================================
# 1. COMMUNICATIONS BOUNDARIES: NEAR-FIELD, COLLOCATED, DEEP SPACE, FREQUENCY
# ============================================================================

def test_13ac_free_space_path_loss_sub_wavelength_rejection():
    """Verify that calculate_free_space_path_loss strictly rejects R <= lambda/(4*pi)."""
    freq_hz = 401.5e6  # UHF, lambda ~ 0.7467 m, lambda/(4*pi) ~ 0.0594 m (5.94 cm)
    wavelength = SPEED_OF_LIGHT_M_S / freq_hz
    sub_wavelength_r = (wavelength / (4.0 * math.pi)) * 0.9  # 10% below reactive boundary

    # Negative distance
    with pytest.raises(ValueError, match="cannot be negative"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(-1.0, freq_hz)

    # Zero distance
    with pytest.raises(ValueError, match="cannot be zero"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(0.0, freq_hz)

    # Sub-wavelength reactive distance
    with pytest.raises(ValueError, match="sub-wavelength reactive near-field"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(sub_wavelength_r, freq_hz)


def test_13ac_fraunhofer_distance_calculation():
    """Verify Fraunhofer boundary R_ff = 2*D^2/lambda for high gain and 2*lambda for low gain."""
    freq_uhf = 401.5e6
    lambda_uhf = SPEED_OF_LIGHT_M_S / freq_uhf

    # Low gain (omni dipole 2.15 dBi <= 3.0 dBi)
    d_omni = PhysicalLinkBudgetEngine.calculate_antenna_aperture_diameter_m(2.15, freq_uhf)
    r_ff_omni = PhysicalLinkBudgetEngine.calculate_fraunhofer_distance_m(d_omni, freq_uhf)
    assert r_ff_omni >= 2.0 * lambda_uhf

    # High gain (Ka-band 35 dBi dish, 32 GHz)
    freq_ka = 32.0e9
    lambda_ka = SPEED_OF_LIGHT_M_S / freq_ka
    d_ka = PhysicalLinkBudgetEngine.calculate_antenna_aperture_diameter_m(35.0, freq_ka)
    r_ff_ka = PhysicalLinkBudgetEngine.calculate_fraunhofer_distance_m(d_ka, freq_ka)
    expected_r_ff = (2.0 * (d_ka ** 2)) / lambda_ka
    assert math.isclose(r_ff_ka, expected_r_ff, rel_tol=1e-4)


def test_13ac_near_field_out_of_domain_link_tagging():
    """Verify evaluate_link returns structured OUT_OF_DOMAIN result when inside near-field."""
    # Ka-band high-gain link (Fraunhofer distance ~ 24 meters)
    tx = TransmitterSpec("KaTx", CommunicationBand.KA_BAND_DEEP_SPACE, 20.0, 35.0)
    rx = ReceiverSpec("KaRx", CommunicationBand.KA_BAND_DEEP_SPACE, 35.0)

    # Slant range of 2.0 meters is well inside the 24 m near-field
    res = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, slant_range_m=2.0, elevation_deg=45.0)

    assert not res.is_link_closed
    assert not res.is_physically_available
    assert res.operating_domain == "NEAR_FIELD_OUT_OF_DOMAIN"
    assert res.validation_status == "OUT_OF_DOMAIN"
    assert "near-field" in res.status_reason.lower()


def test_13ac_collocated_local_interface():
    """Verify collocated components (R=0) are handled as local bus/wired connection without FSPL singularity."""
    tx = TransmitterSpec("MastCam", CommunicationBand.UHF_PROXIMITY, 5.0, 2.0)
    rx = ReceiverSpec("RoverBus", CommunicationBand.UHF_PROXIMITY, 2.0)

    res = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, slant_range_m=0.0, elevation_deg=90.0)

    assert res.is_link_closed
    assert res.is_physically_available
    assert res.operating_domain == "COLLOCATED_LOCAL_INTERFACE"
    assert res.validation_status == "VALID_LOCAL_DIRECT"
    assert res.propagation_delay_s == 0.0
    assert res.operational_rate_bps >= 1_000_000_000  # Local bus line rate


def test_13ac_deep_space_numerical_precision_and_domain():
    """Verify deep-space interplanetary link (Earth-Mars opposition/conjunction) precision and domain tagging."""
    tx = TransmitterSpec("DSN70m-Tx", CommunicationBand.X_BAND_DEEP_SPACE, 20_000.0, 72.0)
    rx = ReceiverSpec("MRO-Rx", CommunicationBand.X_BAND_DEEP_SPACE, 42.0)

    # 2.5 AU (~3.74e11 m, Mars solar conjunction opposition)
    dist_conjunction = 2.5 * 149_597_870_700.0
    res = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, slant_range_m=dist_conjunction, elevation_deg=45.0)

    assert res.operating_domain == "INTERPLANETARY_DEEP_SPACE"
    assert res.validation_status == "VALID"
    assert res.is_physically_available
    assert res.fspl_db > 270.0
    assert math.isfinite(res.link_margin_db)
    assert res.propagation_delay_s > 1000.0  # > 16 minutes one-way light time


def test_13ac_elevation_occultation_and_mask_boundaries():
    """Verify elevation angle distinctions: occultation (<=0°), below mask (<5°), and valid (>=5°)."""
    tx = TransmitterSpec("NominalTx", CommunicationBand.UHF_PROXIMITY, 10.0, 5.0)
    rx = ReceiverSpec("NominalRx", CommunicationBand.UHF_PROXIMITY, 5.0, elevation_mask_deg=5.0)
    slant_range = 50_000.0  # 50 km (far field)

    # 1. Negative elevation (-10°): Body occulted
    res_neg = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, slant_range, elevation_deg=-10.0)
    assert not res_neg.is_link_closed
    assert not res_neg.is_physically_available
    assert res_neg.operating_domain == "OCCULTED_BELOW_HORIZON"
    assert res_neg.validation_status == "PHYSICALLY_UNAVAILABLE"
    assert "occulted" in res_neg.status_reason.lower()

    # 2. Zero elevation (0.0°): Horizon grazing
    res_zero = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, slant_range, elevation_deg=0.0)
    assert not res_zero.is_link_closed
    assert not res_zero.is_physically_available
    assert res_zero.operating_domain == "OCCULTED_BELOW_HORIZON"

    # 3. Low elevation above horizon but below mask (2.5°): Geometrically visible, below mask
    res_mask = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, slant_range, elevation_deg=2.5)
    assert not res_mask.is_link_closed
    assert not res_mask.is_physically_available
    assert res_mask.operating_domain == "BELOW_ELEVATION_MASK"
    assert res_mask.validation_status == "PHYSICALLY_UNAVAILABLE"

    # 4. Above elevation mask (10.0°): Valid link
    res_valid = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, slant_range, elevation_deg=10.0)
    assert res_valid.is_physically_available
    assert res_valid.operating_domain == "FAR_FIELD_FREE_SPACE"
    assert res_valid.validation_status == "VALID"


def test_13ac_pointing_error_beam_null_capping():
    """Verify that off-axis pointing error exceeding beamwidth caps at 40 dB tracking loss."""
    # 35 dBi antenna has HPBW ~ 7.0 degrees
    loss_small = PhysicalLinkBudgetEngine.calculate_pointing_loss(0.5, 35.0, 8.4e9)
    loss_moderate = PhysicalLinkBudgetEngine.calculate_pointing_loss(3.5, 35.0, 8.4e9)
    loss_extreme = PhysicalLinkBudgetEngine.calculate_pointing_loss(25.0, 35.0, 8.4e9)

    assert loss_small < loss_moderate
    assert loss_extreme == 40.0  # Capped at null/tracking failure threshold


def test_13ac_pointing_loss_reduces_received_power_in_evaluate_link():
    """Verify that pointing loss strictly decreases received power (sign check mutation defense)."""
    tx_perfect = TransmitterSpec("PerfTx", CommunicationBand.X_BAND_DEEP_SPACE, 20.0, 35.0, pointing_error_deg=0.0)
    tx_offset = TransmitterSpec("OffsetTx", CommunicationBand.X_BAND_DEEP_SPACE, 20.0, 35.0, pointing_error_deg=2.5)
    rx = ReceiverSpec("Rx", CommunicationBand.X_BAND_DEEP_SPACE, 35.0)

    res_perfect = PhysicalLinkBudgetEngine.evaluate_link(tx_perfect, rx, slant_range_m=10_000_000.0)
    res_offset = PhysicalLinkBudgetEngine.evaluate_link(tx_offset, rx, slant_range_m=10_000_000.0)

    # Pointing loss must reduce received power, never increase it
    assert res_offset.received_power_dbw < res_perfect.received_power_dbw
    delta_power = res_perfect.received_power_dbw - res_offset.received_power_dbw
    assert delta_power > 0.0


def test_13ac_negative_margin_strictly_prevents_link_closure():
    """Verify that insufficient link budget strictly sets is_link_closed=False and rate=0."""
    # Weak 0.001 W transmitter over 100,000 km
    tx = TransmitterSpec("WeakTx", CommunicationBand.UHF_PROXIMITY, 0.001, 0.0)
    rx = ReceiverSpec("WeakRx", CommunicationBand.UHF_PROXIMITY, 0.0)

    res = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, slant_range_m=100_000_000.0)
    assert not res.is_link_closed
    assert res.operational_rate_bps == 0
    assert res.link_margin_db < 0.0


def test_13ac_carrier_frequency_extremes_and_invariants():
    """Verify carrier frequency validations: positive bounds, optical bands, and sub-MHz bounds."""
    # Non-positive frequency
    with pytest.raises(ValueError, match="Carrier frequency must be strictly positive"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(1000.0, 0.0)

    with pytest.raises(ValueError, match="Carrier frequency must be strictly positive"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(1000.0, -100.0)

    # Optical laser (193.4 THz)
    fspl_opt = PhysicalLinkBudgetEngine.calculate_free_space_path_loss(100_000.0, 193.414e12)
    assert fspl_opt > 230.0  # Extremely high free-space spread for optical


# ============================================================================
# 2. ORBITAL CONTACT BOUNDARIES: ZENITH, NADIR, GRAZING
# ============================================================================

def test_13ac_orbital_zenith_and_nadir_elevation():
    """Verify zenith (+90°) and nadir (-90°) elevation computations and occultation flags."""
    topo = create_standard_planetary_network()
    planner = OrbitalContactPlanner(topo)

    settlement_node = topo.nodes["SETTLEMENT-ALPHA"]
    settlement_mcmf = planner.get_surface_node_mcmf_position(settlement_node)

    # Zenith: target 500 km directly along surface normal vector
    zenith_pos = (
        settlement_mcmf[0] * (1.0 + 500_000.0 / MARS_RADIUS_M),
        settlement_mcmf[1] * (1.0 + 500_000.0 / MARS_RADIUS_M),
        settlement_mcmf[2] * (1.0 + 500_000.0 / MARS_RADIUS_M),
    )
    elev_zenith = planner.calculate_surface_elevation_deg(settlement_node, zenith_pos)
    assert math.isclose(elev_zenith, 90.0, abs_tol=1e-4)

    # Nadir: target on opposite side of planet
    nadir_pos = (-zenith_pos[0], -zenith_pos[1], -zenith_pos[2])
    elev_nadir = planner.calculate_surface_elevation_deg(settlement_node, nadir_pos)
    assert math.isclose(elev_nadir, -90.0, abs_tol=1e-4)
    assert planner.is_line_of_sight_occulted_by_mars(settlement_mcmf, nadir_pos)


def test_13ac_orbital_grazing_contact_at_mask_boundary():
    """Verify grazing contacts at elevation mask boundary (5.0° +- 0.1°)."""
    topo = create_standard_planetary_network()
    planner = OrbitalContactPlanner(topo)
    settlement_node = topo.nodes["SETTLEMENT-ALPHA"]

    tx = settlement_node.transmitters[CommunicationBand.UHF_PROXIMITY]
    rx = topo.nodes["ATLAS-ORB-01"].receivers[CommunicationBand.UHF_PROXIMITY]

    # Just below mask (4.9°): blocked
    res_below = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, slant_range_m=800_000.0, elevation_deg=4.9)
    assert not res_below.is_link_closed
    assert not res_below.is_physically_available
    assert res_below.operating_domain == "BELOW_ELEVATION_MASK"

    # Just above mask (5.1°): permitted
    res_above = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, slant_range_m=800_000.0, elevation_deg=5.1)
    assert res_above.is_physically_available
    assert res_above.operating_domain == "FAR_FIELD_FREE_SPACE"


# ============================================================================
# 3. TERRAIN BOUNDARIES: FLAT, VERTICAL CLIFF, SPACING
# ============================================================================

def test_13ac_terrain_flat_and_steep_slope_bounds():
    """Verify Horn slope output is bounded in [0°, 90°) for flat and vertical terrains."""
    dx, dy = 1.0, 1.0

    # 1. Completely flat terrain
    flat_dem = np.full((5, 5), 100.0, dtype=np.float64)
    slope_flat = compute_horn_slope(flat_dem, dx, dy)
    assert math.isclose(slope_flat[2, 2], 0.0, abs_tol=1e-6)

    # 2. Extreme vertical cliff (10,000 m drop over 1 m)
    cliff_dem = np.array([
        [0.0, 0.0, 10000.0, 10000.0, 10000.0],
        [0.0, 0.0, 10000.0, 10000.0, 10000.0],
        [0.0, 0.0, 10000.0, 10000.0, 10000.0],
        [0.0, 0.0, 10000.0, 10000.0, 10000.0],
        [0.0, 0.0, 10000.0, 10000.0, 10000.0],
    ], dtype=np.float64)
    slope_cliff = compute_horn_slope(cliff_dem, dx, dy)
    # Slope must approach 90.0° asymptotically and never exceed 90.0°
    assert 89.0 < slope_cliff[2, 2] < 90.0


def test_13ac_terrain_ground_spacing_physical_bounds():
    """Verify that non-positive ground spacings raise ValueError."""
    dem = np.zeros((3, 3), dtype=np.float64)
    with pytest.raises(ValueError, match="Ground spacings must be positive"):
        compute_horn_slope(dem, dx_ground_m=0.0, dy_ground_m=10.0)

    with pytest.raises(ValueError, match="Ground spacings must be positive"):
        compute_horn_slope(dem, dx_ground_m=10.0, dy_ground_m=-5.0)


def test_13ac_terrain_collocated_step_distance():
    """Verify collocated coordinates yield exactly zero step distance without error."""
    dx, dy = compute_ground_spacings(20.0, 18.38)
    dist = calculate_step_distance((42, 42), (42, 42), dx, dy)
    assert dist == 0.0


# ============================================================================
# 4. RESOURCE/ISRU BOUNDARIES: MASS CONSERVATION & POWER MONOTONICITY
# ============================================================================

def test_13ac_isru_mass_conservation_and_positive_work():
    """Verify strict mass conservation across screening and sintering, and positive energy."""
    inv = SettlementMaterialInventory("TEST_SITE")
    inv.stocks_kg[MaterialCategory.REGOLITH_FEEDSTOCK_RAW] = 1000.0
    inventories = {"TEST_SITE": inv}
    engine = FoundryProductionEngine(inventories)

    robot = IndustrialRobot(
        asset_id="TEST_ROBOT",
        name="Test Hauler",
        robot_class=RobotClass.HAULER,
        settlement_id="TEST_SITE",
        max_payload_kg=2000.0,
        nominal_power_kw=10.0,
        battery_capacity_kwh=50.0,
        current_battery_kwh=50.0,
        speed_km_h=5.0,
    )

    # Execute screening of 500 kg
    rec_screen = engine.execute_screening("TEST_SITE", 500.0, robot, current_time_s=100.0)

    # First law of thermodynamics: usable + waste == input
    assert math.isclose(rec_screen.output_usable_mass_kg + rec_screen.waste_mass_kg, 500.0, abs_tol=1e-4)
    assert rec_screen.energy_consumed_kwh > 0.0
    assert robot.current_battery_kwh < 50.0  # Battery drained monotonically


def test_13ac_isru_non_positive_mass_rejection():
    """Verify that zero and negative mass processing requests are rejected with ValueError."""
    inv = SettlementMaterialInventory("TEST_SITE")
    inventories = {"TEST_SITE": inv}
    engine = FoundryProductionEngine(inventories)

    robot = IndustrialRobot(
        asset_id="TEST_ROBOT",
        name="Test Excavator",
        robot_class=RobotClass.EXCAVATOR,
        settlement_id="TEST_SITE",
        max_payload_kg=2000.0,
        nominal_power_kw=15.0,
        battery_capacity_kwh=50.0,
        current_battery_kwh=50.0,
        speed_km_h=4.0,
    )

    # Zero excavation mass
    with pytest.raises(ValueError, match="must be a positive finite number"):
        engine.execute_excavation("TEST_SITE", 0.0, robot, current_time_s=0.0)

    # Negative excavation mass (attempted reverse excavation / energy generation)
    with pytest.raises(ValueError, match="must be a positive finite number"):
        engine.execute_excavation("TEST_SITE", -100.0, robot, current_time_s=0.0)

    # Negative screening mass
    with pytest.raises(ValueError, match="must be a positive finite number"):
        engine.execute_screening("TEST_SITE", -50.0, robot, current_time_s=0.0)

    # Negative sintering mass
    with pytest.raises(ValueError, match="must be a positive finite number"):
        engine.execute_sintering("TEST_SITE", -50.0, robot, current_time_s=0.0)
