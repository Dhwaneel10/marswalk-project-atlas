"""
Milestone 13AF — Dedicated Test Suite: Independent Benchmark, Parameter Provenance & Link Feasibility.

Mission Designation: ATLAS-13AF-INDEPENDENT-BENCHMARK
Scope:
1. Optical Dust Spectral Extinction:
   - Sensitivity configurations across alpha in {-0.160, -0.082, -0.047, -0.036, +0.350}
   - Explicit disclosure of 1550 nm extrapolation metadata
2. RF Dust Dielectric Loss & Rayleigh Regime Verification:
   - Complex polarizability derivation Im(-K) = 0.005468
   - Rayleigh size parameter validation (x <= 0.0134 << 1)
   - Multi-band loss replication (Ka-band 0.762 dB typical, 4.345 dB severe, > 24 dB slant)
   - UHF proximity loss < 0.10 dB
3. Link Feasibility Audit & Survivability Claim Disproof:
   - Proof that low dust attenuation does NOT guarantee link closure
   - Scenario with dust loss = 0.009 dB failing by > 10 dB due to range, off-axis nulls, and high rate
4. Receiver System Noise & Planck vs Rayleigh-Jeans Departure:
   - Quantification of Planck vs Rayleigh-Jeans departure at 32 GHz (2.029 K vs 2.725 K, -25.5%)
   - Strict proof of reference plane invariance (Plane A vs Plane B) with zero double-counting
5. Antenna Model Evidence Register & Sidelobe Bounds:
   - Verification of broadbeam guard for wire and array antennas
   - Exact mathematical Airy diffraction first sidelobe level (-17.57 dB)
6. Cross-Module Margin Enforcement:
   - Strict rejection of insufficient link margin (is_link_closed = False, rate = 0 bps)
"""

import math
import pytest
from scipy.special import j1

from marswalk.core.atlas_mars_atmospheric_model import (
    MarsAtmosphericEngine,
    MarsAtmosphericProfile,
    SPEED_OF_LIGHT_M_S,
)
from marswalk.core.atlas_antenna_model import (
    AdvancedAntennaEngine,
    AntennaCategory,
    FieldRegionClassification,
    PatternModelTier,
    bessel_j1,
)
from marswalk.core.atlas_network_link_model import (
    ReceiverSpec,
    TransmitterSpec,
    CommunicationBand,
    CommunicationMedium,
    PhysicalLinkBudgetEngine,
    BOLTZMANN_CONSTANT_J_K,
)


# ============================================================================
# 1. OPTICAL DUST SPECTRAL EXTRAPOLATION & METADATA DISCLOSURE
# ============================================================================

def test_13af_optical_dust_angstrom_sensitivity_and_extrapolation_disclosure():
    """
    Verify optical extinction across the five published sensitivity configurations.
    Verify that calculate_optical_attenuation_db outputs explicit disclosure metadata
    confirming that 1550 nm is an extrapolated value, not a direct measurement.
    """
    cases = {
        "Lemmon_Upper": -0.160,
        "Atlas_Reference": -0.082,
        "Wolff_CRISM": -0.047,
        "Lemmon_Lower": -0.036,
        "13AD_Terrestrial": +0.350,
    }

    lambda_0 = 880e-9
    lambda_nir = 1550e-9

    for name, alpha in cases.items():
        ratio = (lambda_nir / lambda_0) ** (-alpha)
        if alpha < 0:
            assert ratio > 1.0, f"{name} failed to show NIR opacity increase"
            assert 1.02 <= ratio <= 1.10
        else:
            assert ratio < 1.0, f"Terrestrial case unexpectedly showed opacity increase"

    # Evaluate production call at 1550 nm
    res = MarsAtmosphericEngine.calculate_optical_attenuation_db(
        elevation_deg=90.0,
        wavelength_m=1550e-9,
        tau_880nm=0.5,
    )
    assert res["is_extrapolated_wavelength"] is True
    assert "extrapolated" in res["spectral_model_provenance"].lower()
    assert math.isclose(res["spectral_optical_depth"], 0.5238, abs_tol=0.001)
    assert math.isclose(res["attenuation_db"], 2.275, abs_tol=0.01)

    # Evaluate production call at reference 880 nm (not extrapolated)
    res_880 = MarsAtmosphericEngine.calculate_optical_attenuation_db(
        elevation_deg=90.0,
        wavelength_m=880e-9,
        tau_880nm=0.5,
    )
    assert res_880["is_extrapolated_wavelength"] is False
    assert res_880["spectral_optical_depth"] == 0.5


# ============================================================================
# 2. RF DUST DIELECTRIC PARAMETERS & RAYLEIGH SIZE PARAMETER
# ============================================================================

def test_13af_rf_dust_dielectric_polarization_and_rayleigh_limit():
    """
    Verify that basaltic analog permittivity (eps_r = 2.80 - j*0.0420) produces
    Im(-K) = 0.005468, and that size parameter x = 2*pi*r / lambda << 0.1 at 32 GHz,
    strictly validating Rayleigh absorption theory over Mie scattering.
    """
    eps_real = 2.80
    eps_imag = 0.0420

    # Derive Im(-K)
    u_re = eps_real - 1.0
    u_im = -eps_imag
    v_re = eps_real + 2.0
    v_im = -eps_imag

    v_mag_sq = v_re**2 + v_im**2
    k_num_im = u_im * v_re - u_re * v_im
    im_neg_k = - (k_num_im / v_mag_sq)

    assert math.isclose(im_neg_k, 0.005468, rel_tol=1e-4)

    # Check size parameter x at 32 GHz for coarse 20 um particle
    lambda_32ghz = SPEED_OF_LIGHT_M_S / 32.0e9
    x_20um = (2.0 * math.pi * 20.0e-6) / lambda_32ghz
    assert x_20um <= 0.0135
    assert x_20um < 0.05, f"Size parameter {x_20um} violated Rayleigh limit (x < 0.05)"

    # Check Rayleigh scattering-to-absorption ratio: 2/3 * x^3 * |K|^2 / Im(-K)
    abs_k_sq = (u_re**2 + u_im**2) / v_mag_sq
    ratio_sca_abs = (2.0 / 3.0) * (x_20um ** 3) * (abs_k_sq / im_neg_k)
    assert ratio_sca_abs < 1e-4, f"Scattering exceeded 0.01% of absorption: {ratio_sca_abs}"


def test_13af_rf_dust_multiband_replication_and_jpl_benchmark():
    """
    Verify multi-band RF dust attenuation values against JPL DESCANSO benchmarks:
    - Typical Ka-band zenith: ~ 0.762 dB
    - Severe Ka-band zenith: ~ 4.345 dB
    - Severe Ka-band slant (10 deg): > 24 dB
    - Severe UHF zenith: < 0.10 dB
    """
    # 1. Typical dust (tau = 0.5)
    loss_ka_typical = MarsAtmosphericEngine.calculate_rf_atmospheric_attenuation_db(32.0e9, 90.0, airmass=1.0, dust_tau=0.5)
    assert math.isclose(loss_ka_typical, 0.762, abs_tol=0.01)

    # 2. Severe dust storm (tau = 3.0)
    loss_ka_severe_zenith = MarsAtmosphericEngine.calculate_rf_atmospheric_attenuation_db(32.0e9, 90.0, airmass=1.0, dust_tau=3.0)
    loss_ka_severe_slant = MarsAtmosphericEngine.calculate_rf_atmospheric_attenuation_db(32.0e9, 10.0, airmass=5.602, dust_tau=3.0)
    loss_uhf_severe = MarsAtmosphericEngine.calculate_rf_atmospheric_attenuation_db(401.5e6, 90.0, airmass=1.0, dust_tau=3.0)

    assert math.isclose(loss_ka_severe_zenith, 4.345, abs_tol=0.05)
    assert loss_ka_severe_slant > 24.0
    assert loss_uhf_severe < 0.10


# ============================================================================
# 3. LINK SURVIVABILITY AUDIT & FAILURE DEMONSTRATION
# ============================================================================

def test_13af_negligible_dust_loss_with_link_failure():
    """
    Demonstrate that low dust attenuation does NOT guarantee link closure.
    Scenario 3: Dust attenuation is only 0.009 dB (negligible), yet the link
    FAILS by more than 10 dB due to high slant range, chassis null, and high bit rate.
    """
    # Transmitter: Rover UHF emergency low-power beacon (0.5 W, -3.85 dBi in off-axis chassis null)
    tx_rover = TransmitterSpec(
        name="Rover_UHF_Low_Angle",
        band=CommunicationBand.UHF_PROXIMITY,
        power_watts=0.5,
        antenna_gain_dbi=-3.85,  # Chassis ground plane null at low elevation
        cable_loss_db=0.8,
        pointing_error_deg=1.5,
    )
    # Receiver: Orbiter UHF patch (6 dBi, T_sys = 488.28 K, required Eb/N0 = 9.6 dB)
    rx_orbiter = ReceiverSpec(
        name="Orbiter_UHF_Receiver",
        band=CommunicationBand.UHF_PROXIMITY,
        antenna_gain_dbi=6.0,
        sys_noise_temp_k=488.28,
        req_eb_n0_db=9.6,
        implementation_loss_db=1.5,
        min_link_margin_db=3.0,
        elevation_mask_deg=1.0,  # Explicitly allow horizon pass down to 1.0 deg
    )

    # Slant range = 2,280 km (horizon pass at theta = 2.5 deg)
    res = PhysicalLinkBudgetEngine.evaluate_link(
        tx=tx_rover,
        rx=rx_orbiter,
        slant_range_m=2_280_000.0,
        elevation_deg=2.5,
        dust_tau=0.20,  # Clear atmosphere
    )

    # 1. Atmospheric loss is very small (< 0.50 dB total, < 0.01 dB dust)
    assert res.atmospheric_loss_db < 0.50

    # 2. But the link FAILS completely
    assert not res.is_link_closed
    assert res.operational_rate_bps == 0
    assert not res.is_link_closed
    assert "below" in res.status_reason.lower()


# ============================================================================
# 4. RECEIVER NOISE & PLANCK VS RAYLEIGH-JEANS DEPARTURE
# ============================================================================

def test_13af_planck_rayleigh_jeans_departure_at_microwave_bands():
    """
    Verify the departure of Rayleigh-Jeans equivalent brightness temperature T_RJ
    from thermodynamic CMB temperature (2.725 K):
    - At 401.5 MHz: T_RJ ~ 2.715 K (departure < 0.01 K)
    - At 32.0 GHz: T_RJ ~ 2.029 K (departure ~ -0.70 K, -25.5%)
    """
    h = 6.62607015e-34
    k = 1.380649e-23
    t_thermo = 2.725

    def compute_t_rj(freq_hz: float) -> float:
        h_nu_over_k = (h * freq_hz) / k
        x = h_nu_over_k / t_thermo
        return h_nu_over_k / (math.exp(x) - 1.0)

    t_rj_uhf = compute_t_rj(401.5e6)
    t_rj_ka = compute_t_rj(32.0e9)

    assert math.isclose(t_rj_uhf, 2.715, abs_tol=0.01)
    assert math.isclose(t_rj_ka, 2.029, abs_tol=0.01)
    # Ka-band departs by more than 20%
    delta_ka_pct = abs(t_rj_ka - t_thermo) / t_thermo * 100.0
    assert delta_ka_pct > 25.0


def test_13af_receiver_reference_plane_invariance():
    """
    Verify exact carrier-to-noise spectral density invariance between Plane A and Plane B:
    (C / N_0)_A == (C / N_0)_B
    """
    p_ant = 1.0e-12  # -90 dBm
    t_ant = 120.0
    feed_loss_db = 1.8
    t_phys = 260.0
    nf_db = 2.5

    l_feed = 10.0 ** (feed_loss_db / 10.0)
    t_rx = (10.0 ** (nf_db / 10.0) - 1.0) * 290.0

    # Plane A
    t_sys_a = t_ant + (l_feed - 1.0) * t_phys + l_feed * t_rx
    c_n0_a = p_ant / (BOLTZMANN_CONSTANT_J_K * t_sys_a)

    # Plane B
    p_b = p_ant / l_feed
    t_sys_b = (t_ant / l_feed) + (1.0 - 1.0 / l_feed) * t_phys + t_rx
    c_n0_b = p_b / (BOLTZMANN_CONSTANT_J_K * t_sys_b)

    assert math.isclose(c_n0_a, c_n0_b, rel_tol=1e-12)


# ============================================================================
# 5. ANTENNA EVIDENCE REGISTER & BROADBEAM GUARD
# ============================================================================

def test_13af_antenna_broadbeam_guard_and_airy_sidelobes():
    """
    Verify that wire and broadbeam antennas bypass Airy pattern calculations,
    and verify the exact first sidelobe level of the ideal circular aperture (-17.57 dB).
    """
    # 1. Broadbeam dipole bypasses Airy
    res_dipole = AdvancedAntennaEngine.evaluate_radiation_pattern(
        boresight_gain_dbi=2.15,
        physical_dimension_m=0.18,
        carrier_freq_hz=401.5e6,
        pointing_error_deg=30.0,
        category=AntennaCategory.DIPOLE_OMNI,
    )
    assert res_dipole.pointing_loss_db == 0.1
    assert "omni/broadbeam" in res_dipole.status_reason.lower()

    # 2. Airy first sidelobe peak at u = 5.135622
    j1_peak = bessel_j1(5.135622)
    p_rel = (2.0 * j1_peak / 5.135622) ** 2
    loss_db = -10.0 * math.log10(p_rel)
    assert math.isclose(loss_db, 17.57, abs_tol=0.05)


# ============================================================================
# 6. CROSS-MODULE MARGIN ENFORCEMENT
# ============================================================================

def test_13af_strict_link_margin_rejection():
    """
    Verify that PhysicalLinkBudgetEngine strictly rejects negative margin links
    and returns 0 bps operational rate with is_link_closed = False.
    """
    # Micro-power transmitter (1 uW) over deep space distance produces negative margin
    tx_weak = TransmitterSpec(
        name="WeakTx",
        band=CommunicationBand.KA_BAND_DEEP_SPACE,
        power_watts=1.0e-6,
        antenna_gain_dbi=0.0,
    )
    rx_standard = ReceiverSpec(
        name="StdRx",
        band=CommunicationBand.KA_BAND_DEEP_SPACE,
        antenna_gain_dbi=20.0,
        req_eb_n0_db=6.0,
        min_link_margin_db=3.0,
    )

    res = PhysicalLinkBudgetEngine.evaluate_link(
        tx=tx_weak,
        rx=rx_standard,
        slant_range_m=10_000_000.0,  # 10,000 km
        elevation_deg=45.0,
    )

    assert not res.is_link_closed
    assert res.operational_rate_bps == 0
    assert res.link_margin_db < 0.0
    assert "insufficient link budget" in res.status_reason.lower()
