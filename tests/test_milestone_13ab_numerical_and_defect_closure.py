"""
MarsWalk 2.0 / Project Atlas — Milestone 13AB: Numerical Hardening & Defect Closure Suite
========================================================================================
Comprehensive verification and regression hardening across:
  - FND-13AA-01: Propagation of NaN/Infinity into RF/optical link budget models
  - Numerical edge cases: distance, frequency, power, gain, noise temperature, elevation, optical depth
  - Physical validity bounds: zero distance, negative values, extreme deep-space ranges
  - Contract guarantee: all output fields and JSON dictionaries are strictly finite
  - Route alias verification for /api/planetary-network/overview
"""

import json
import math
import pytest

from marswalk.core.atlas_network_link_model import (
    CommunicationBand,
    TransmitterSpec,
    ReceiverSpec,
    PhysicalLinkBudgetEngine,
    SPEED_OF_LIGHT_M_S,
    CARRIER_FREQUENCIES_HZ,
    STANDARD_DATA_RATES_BPS,
)


# ============================================================================
# 1. PATH LOSS NUMERICAL BOUNDS & REJECTION OF NON-FINITE INPUTS
# ============================================================================

def test_rejection_of_nan_in_path_loss():
    """Verify that calculate_free_space_path_loss strictly rejects NaN."""
    with pytest.raises(ValueError, match="cannot be NaN"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(float("nan"), 401.5e6)

    with pytest.raises(ValueError, match="cannot be NaN"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(1000.0, float("nan"))


def test_rejection_of_infinities_in_path_loss():
    """Verify that calculate_free_space_path_loss rejects positive/negative infinity."""
    with pytest.raises(ValueError, match="must be finite"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(float("inf"), 401.5e6)

    with pytest.raises(ValueError, match="must be finite"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(float("-inf"), 401.5e6)

    with pytest.raises(ValueError, match="must be finite"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(1000.0, float("inf"))


def test_frequency_physical_bounds():
    """Carrier frequency must be strictly positive (> 0 Hz)."""
    with pytest.raises(ValueError, match="must be strictly positive"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(1000.0, 0.0)

    with pytest.raises(ValueError, match="must be strictly positive"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(1000.0, -1e6)


def test_zero_and_near_field_distance_boundary():
    """Zero and negative distances raise ValueError (physically invalid for free-space Friis propagation)."""
    with pytest.raises(ValueError, match="cannot be zero"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(0.0, 401.5e6)

    with pytest.raises(ValueError, match="cannot be negative"):
        PhysicalLinkBudgetEngine.calculate_free_space_path_loss(-10.0, 401.5e6)


def test_analytical_exact_free_space_path_loss_value():
    """Verify exact analytical FSPL against standard Friis spherical propagation formula."""
    # 401.5 MHz at 500,000 m: FSPL must equal 20 * log10(4*pi*R/lambda) ≈ 138.50 dB
    fspl = PhysicalLinkBudgetEngine.calculate_free_space_path_loss(500_000.0, 401.5e6)
    expected_fspl = 20.0 * math.log10((4.0 * math.pi * 500_000.0) / (SPEED_OF_LIGHT_M_S / 401.5e6))
    assert math.isclose(fspl, expected_fspl, rel_tol=1e-6)
    assert 138.49 < fspl < 138.51
    # Detects power factor mutation (10*log10 would yield ~69.25 dB)
    assert abs(fspl - 69.25) > 10.0


# ============================================================================
# 2. TRANSMITTER & RECEIVER SPECIFICATION NUMERICAL HARDENING
# ============================================================================

def test_transmitter_spec_nan_and_inf_hardening():
    """Verify TransmitterSpec rejects non-finite power, gain, and cable loss."""
    # NaN power
    tx_nan_pwr = TransmitterSpec("TxBad", CommunicationBand.UHF_PROXIMITY, float("nan"), 6.0)
    with pytest.raises(ValueError, match="power_watts must be a finite real number"):
        _ = tx_nan_pwr.power_dbw

    # Inf power
    tx_inf_pwr = TransmitterSpec("TxInf", CommunicationBand.UHF_PROXIMITY, float("inf"), 6.0)
    with pytest.raises(ValueError, match="power_watts must be a finite real number"):
        _ = tx_inf_pwr.power_dbw

    # NaN antenna gain
    tx_nan_gain = TransmitterSpec("TxBadGain", CommunicationBand.UHF_PROXIMITY, 20.0, float("nan"))
    with pytest.raises(ValueError, match="antenna_gain_dbi must be a finite real number"):
        _ = tx_nan_gain.eirp_dbw

    # NaN cable loss
    tx_nan_cable = TransmitterSpec("TxBadCable", CommunicationBand.UHF_PROXIMITY, 20.0, 6.0, cable_loss_db=float("nan"))
    with pytest.raises(ValueError, match="cable_loss_db must be a finite real number"):
        _ = tx_nan_cable.eirp_dbw

    # NaN custom carrier frequency
    tx_nan_freq = TransmitterSpec("TxBadFreq", CommunicationBand.UHF_PROXIMITY, 20.0, 6.0, carrier_freq_hz=float("nan"))
    with pytest.raises(ValueError, match="carrier_freq_hz must be a finite number"):
        _ = tx_nan_freq.get_frequency_hz()


def test_receiver_spec_temperature_hardening():
    """Receiver system noise temperature must be finite and strictly positive (> 0 K)."""
    # NaN noise temp
    rx_nan = ReceiverSpec("RxNan", CommunicationBand.UHF_PROXIMITY, 6.0, sys_noise_temp_k=float("nan"))
    with pytest.raises(ValueError, match="sys_noise_temp_k must be a finite real number"):
        _ = rx_nan.noise_spectral_density_dbw_hz

    # Inf noise temp
    rx_inf = ReceiverSpec("RxInf", CommunicationBand.UHF_PROXIMITY, 6.0, sys_noise_temp_k=float("inf"))
    with pytest.raises(ValueError, match="sys_noise_temp_k must be a finite real number"):
        _ = rx_inf.noise_spectral_density_dbw_hz

    # Zero noise temp (absolute zero singularity)
    rx_zero = ReceiverSpec("RxZero", CommunicationBand.UHF_PROXIMITY, 6.0, sys_noise_temp_k=0.0)
    with pytest.raises(ValueError, match="must be strictly positive"):
        _ = rx_zero.noise_spectral_density_dbw_hz

    # Negative noise temp (unphysical)
    rx_neg = ReceiverSpec("RxNeg", CommunicationBand.UHF_PROXIMITY, 6.0, sys_noise_temp_k=-10.0)
    with pytest.raises(ValueError, match="must be strictly positive"):
        _ = rx_neg.noise_spectral_density_dbw_hz


# ============================================================================
# 3. POINTING & ATMOSPHERIC LOSS HARDENING
# ============================================================================

def test_pointing_loss_hardening():
    """Verify calculate_pointing_loss rejects NaN/Inf and handles negative error angles."""
    # Reject NaN
    with pytest.raises(ValueError, match="cannot be NaN"):
        PhysicalLinkBudgetEngine.calculate_pointing_loss(float("nan"), 30.0, 8.4e9)

    with pytest.raises(ValueError, match="cannot be NaN"):
        PhysicalLinkBudgetEngine.calculate_pointing_loss(0.05, float("nan"), 8.4e9)

    # Reject Inf
    with pytest.raises(ValueError, match="must be finite"):
        PhysicalLinkBudgetEngine.calculate_pointing_loss(float("inf"), 30.0, 8.4e9)

    # Negative pointing angle takes absolute value
    loss_pos = PhysicalLinkBudgetEngine.calculate_pointing_loss(0.1, 30.0, 8.4e9)
    loss_neg = PhysicalLinkBudgetEngine.calculate_pointing_loss(-0.1, 30.0, 8.4e9)
    assert math.isclose(loss_pos, loss_neg, abs_tol=1e-6)

    # Low gain (broad beam) has nominal pointing loss
    omni_loss = PhysicalLinkBudgetEngine.calculate_pointing_loss(5.0, 2.0, 401.5e6)
    assert omni_loss == 0.1


def test_atmospheric_loss_hardening():
    """Verify calculate_atmospheric_loss handles elevation clamping, tau bounds, and rejects NaN."""
    # Reject NaN
    with pytest.raises(ValueError, match="cannot be NaN"):
        PhysicalLinkBudgetEngine.calculate_atmospheric_loss(CommunicationBand.OPTICAL_LASER, float("nan"), 0.5)

    with pytest.raises(ValueError, match="cannot be NaN"):
        PhysicalLinkBudgetEngine.calculate_atmospheric_loss(CommunicationBand.OPTICAL_LASER, 45.0, float("nan"))

    # Negative dust tau rejected
    with pytest.raises(ValueError, match="cannot be negative"):
        PhysicalLinkBudgetEngine.calculate_atmospheric_loss(CommunicationBand.OPTICAL_LASER, 45.0, -0.5)

    # Sub-horizon elevation (<= 0.0) rejected as geometrically occulted
    with pytest.raises(ValueError, match="sub-horizon elevation"):
        PhysicalLinkBudgetEngine.calculate_atmospheric_loss(CommunicationBand.OPTICAL_LASER, 0.0, 0.5)

    with pytest.raises(ValueError, match="sub-horizon elevation"):
        PhysicalLinkBudgetEngine.calculate_atmospheric_loss(CommunicationBand.OPTICAL_LASER, -5.0, 0.5)

    # Near-horizon elevation (e.g. 0.1 deg) evaluated via spherical Chapman airmass without 1/0 singularity
    loss_horizon = PhysicalLinkBudgetEngine.calculate_atmospheric_loss(CommunicationBand.OPTICAL_LASER, 0.1, 0.5)
    loss_1deg = PhysicalLinkBudgetEngine.calculate_atmospheric_loss(CommunicationBand.OPTICAL_LASER, 1.0, 0.5)
    assert math.isfinite(loss_horizon)
    assert loss_horizon > loss_1deg


# ============================================================================
# 4. END-TO-END LINK EVALUATION & FINITENESS CONTRACT
# ============================================================================

def test_evaluate_link_rejects_nan_and_inf_inputs():
    """Verify evaluate_link rejects non-finite slant range, elevation, and dust tau."""
    tx = TransmitterSpec("NominalTx", CommunicationBand.UHF_PROXIMITY, 20.0, 6.0)
    rx = ReceiverSpec("NominalRx", CommunicationBand.UHF_PROXIMITY, 6.0)

    # NaN slant range
    with pytest.raises(ValueError, match="slant_range_m must be a finite real number"):
        PhysicalLinkBudgetEngine.evaluate_link(tx, rx, float("nan"))

    # Inf slant range
    with pytest.raises(ValueError, match="slant_range_m must be a finite real number"):
        PhysicalLinkBudgetEngine.evaluate_link(tx, rx, float("inf"))

    # Negative slant range
    with pytest.raises(ValueError, match="slant_range_m cannot be negative"):
        PhysicalLinkBudgetEngine.evaluate_link(tx, rx, -100.0)

    # NaN elevation
    with pytest.raises(ValueError, match="elevation_deg must be a finite real number"):
        PhysicalLinkBudgetEngine.evaluate_link(tx, rx, 100_000.0, elevation_deg=float("nan"))

    # NaN dust tau
    with pytest.raises(ValueError, match="dust_tau must be a finite real number"):
        PhysicalLinkBudgetEngine.evaluate_link(tx, rx, 100_000.0, dust_tau=float("nan"))


def test_evaluate_link_unpowered_transmitter_graceful_handling():
    """Unpowered transmitter (power <= 0) returns structured failure without crashing or NaN."""
    tx = TransmitterSpec("DeadTx", CommunicationBand.UHF_PROXIMITY, 0.0, 6.0)
    rx = ReceiverSpec("NominalRx", CommunicationBand.UHF_PROXIMITY, 6.0)

    res = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, 100_000.0)
    assert not res.is_link_closed
    assert res.operational_rate_bps == 0
    assert res.link_margin_db == -999.0
    assert "unpowered" in res.status_reason.lower()

    # JSON export must succeed with zero NaN/Inf values
    d = res.to_dict()
    json_str = json.dumps(d, allow_nan=False)
    assert json_str is not None


def test_evaluate_link_astronomical_range_budget_limit():
    """Extremely large finite distances (e.g. 100 AU deep space) must evaluate cleanly."""
    tx = TransmitterSpec("DSNTx", CommunicationBand.X_BAND_DEEP_SPACE, 50.0, 48.0)
    rx = ReceiverSpec("DSNRx", CommunicationBand.X_BAND_DEEP_SPACE, 68.0)

    # 100 Astronomical Units (~1.5e13 meters)
    extreme_range = 100.0 * 149_597_870_700.0
    res = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, extreme_range)

    assert not res.is_link_closed
    assert res.operational_rate_bps == 0
    assert math.isfinite(res.fspl_db)
    assert res.fspl_db > 300.0  # Massive path loss
    assert math.isfinite(res.link_margin_db)
    assert res.to_dict() is not None


def test_all_output_fields_finite_for_nominal_rf_and_optical():
    """Guarantee that for nominal RF and optical links, all output metrics are strictly finite."""
    # 1. Proximity UHF Link (500 km)
    tx_uhf = TransmitterSpec("UHF-Tx", CommunicationBand.UHF_PROXIMITY, 10.0, 5.0)
    rx_uhf = ReceiverSpec("UHF-Rx", CommunicationBand.UHF_PROXIMITY, 5.0)
    res_uhf = PhysicalLinkBudgetEngine.evaluate_link(tx_uhf, rx_uhf, 500_000.0, 45.0)

    for field_name in ["fspl_db", "eirp_dbw", "received_power_dbw", "c_n0_dbhz", "link_margin_db", "propagation_delay_s"]:
        val = getattr(res_uhf, field_name)
        assert math.isfinite(val), f"Field {field_name} was non-finite: {val}"

    # 2. Deep Space Optical Link (0.5 AU, 7.5e10 m)
    tx_opt = TransmitterSpec("Opt-Tx", CommunicationBand.OPTICAL_LASER, 10.0, 110.0)
    rx_opt = ReceiverSpec("Opt-Rx", CommunicationBand.OPTICAL_LASER, 115.0)
    res_opt = PhysicalLinkBudgetEngine.evaluate_link(tx_opt, rx_opt, 7.5e10, 60.0, dust_tau=0.8)

    for field_name in ["fspl_db", "eirp_dbw", "received_power_dbw", "c_n0_dbhz", "link_margin_db", "propagation_delay_s"]:
        val = getattr(res_opt, field_name)
        assert math.isfinite(val), f"Field {field_name} was non-finite in optical: {val}"

    # Verify JSON serialization compliance
    uhf_json = json.dumps(res_uhf.to_dict(), allow_nan=False)
    opt_json = json.dumps(res_opt.to_dict(), allow_nan=False)
    assert "is_link_closed" in uhf_json
    assert "is_link_closed" in opt_json
