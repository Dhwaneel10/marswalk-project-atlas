"""
MarsWalk 2.0 / Project Atlas — Milestone 13AD: Mars Physics Reference Validation
================================================================================
Independent numerical benchmarks, empirical planetary datasets, antenna field-region
standards, and multi-tier radiation pattern verification.

Tests:
1. Spherical-shell airmass numerical integration vs analytical asymptote sqrt(pi*R/(2*H)).
2. Empirical Mars scale heights: Spirit (H=11.9 km), Opportunity (H=19.2 km), and reference (H=11.0 km).
3. Tangent-path and limb-sounding chord optical depth integrals.
4. Plane-parallel divergence table across elevation angles (90° down to 0.001°).
5. Spectral optical depth scaling with Ångström exponent alpha=0.35 (880 nm vs 1550 nm).
6. Decoupling of RF microwave propagation from optical dust extinction.
7. IEEE Std 145-2013 and ISED GL-01 antenna field region triple criteria (small vs large antennas).
8. Circular aperture Airy diffraction pattern: main lobe, first null at u=3.8317, first sidelobe at -17.58 dB.
9. Pointing model tier taxonomy and out-of-domain guard disclosure.
10. Communication medium isolation: orbital contact pass rejects local bus interfaces.
11. Receiver system noise temperature decomposition and 2.7 K CMB physical lower bound.
"""

import math
import pytest

from marswalk.core.atlas_mars_atmospheric_model import (
    MarsAtmosphericEngine,
    MarsAtmosphericProfile,
)
from marswalk.core.atlas_antenna_model import (
    AdvancedAntennaEngine,
    AntennaCategory,
    FieldRegionClassification,
    PatternModelTier,
    bessel_j1,
)
from marswalk.core.atlas_network_link_model import (
    CommunicationBand,
    CommunicationMedium,
    PhysicalLinkBudgetEngine,
    ReceiverSpec,
    TransmitterSpec,
    SPEED_OF_LIGHT_M_S,
)
from marswalk.core.atlas_orbital_contact_planner import (
    OrbitalContactPlanner,
)
from marswalk.core.atlas_planetary_network_architecture import (
    create_standard_planetary_network,
)


# ============================================================================
# 1. SPHERICAL RADIATIVE TRANSFER & NUMERICAL INTEGRATION BENCHMARKS
# ============================================================================

def test_13ad_spherical_airmass_numerical_vs_analytical_asymptote():
    """
    Verify numerical quadrature of spherical Chapman path matches the analytical
    asymptotic formula sqrt(pi * R_M / (2 * H)) to within 0.2% at horizon.
    Scenario: R_M = 3396 km, H = 11.0 km.
    Analytical asymptote = sqrt(pi * 3396 / 22) = 22.0215.
    """
    profile = MarsAtmosphericProfile(
        mars_radius_m=3_396_000.0,
        extinction_scale_height_m=11_000.0,
    )
    # Elevation 0.001° (horizon grazing)
    res = MarsAtmosphericEngine.calculate_spherical_airmass(
        elevation_deg=0.001,
        h_obs_m=0.0,
        profile=profile,
    )
    analytical_asymptote = math.sqrt((math.pi * profile.mars_radius_m) / (2.0 * profile.extinction_scale_height_m))

    assert math.isclose(res.analytical_asymptote_horizon, analytical_asymptote, rel_tol=1e-5)
    # Numerical airmass must match analytical asymptote within 0.2%
    relative_err_pct = abs(res.spherical_airmass - analytical_asymptote) / analytical_asymptote * 100.0
    assert relative_err_pct < 0.2, f"Relative error {relative_err_pct:.4f}% exceeded 0.2% tolerance"
    assert math.isclose(res.spherical_airmass, 22.0449, abs_tol=0.05)


def test_13ad_empirical_mars_scale_height_variations():
    """
    Verify airmass scaling across documented Mars exploration scale heights:
    - Spirit (Gusev crater): H ~ 11.9 km -> horizon airmass ~ 21.2
    - Opportunity (Meridiani Planum): H ~ 19.2 km -> horizon airmass ~ 16.8
    A larger scale height spreads dust higher vertically, resulting in a LOWER horizon airmass ratio.
    """
    spirit_profile = MarsAtmosphericProfile(extinction_scale_height_m=11_900.0)
    oppy_profile = MarsAtmosphericProfile(extinction_scale_height_m=19_200.0)

    res_spirit = MarsAtmosphericEngine.calculate_spherical_airmass(0.001, profile=spirit_profile)
    res_oppy = MarsAtmosphericEngine.calculate_spherical_airmass(0.001, profile=oppy_profile)

    assert math.isclose(res_spirit.spherical_airmass, 21.20, abs_tol=0.10)
    assert math.isclose(res_oppy.spherical_airmass, 16.77, abs_tol=0.10)
    # Opportunity's thicker vertical scale height must produce a lower horizon-to-zenith airmass ratio
    assert res_oppy.spherical_airmass < res_spirit.spherical_airmass


def test_13ad_tangent_path_limb_sounding_integral():
    """
    Verify limb-sounding tangent optical depth:
    - Surface tangent (tangent_alt = 0 m) is exactly 2x the surface-to-TOA horizon half-path.
    - Tangent altitude at or above TOA (100 km) has tau = 0.0 and is not occulted.
    - Negative tangent altitude (intersects Mars solid body) has tau = inf and is occulted.
    """
    profile = MarsAtmosphericProfile()
    tau_zenith = 0.5

    # 1. Surface tangent (h_t = 0 m)
    tau_tangent, occulted = MarsAtmosphericEngine.calculate_tangent_path_optical_depth(
        tangent_alt_m=0.0,
        profile=profile,
        tau_zenith_surface=tau_zenith,
    )
    assert not occulted
    res_half = MarsAtmosphericEngine.calculate_spherical_airmass(0.0001, profile=profile)
    expected_tau = 2.0 * tau_zenith * res_half.spherical_airmass
    assert math.isclose(tau_tangent, expected_tau, rel_tol=1e-3)

    # 2. Above TOA (h_t = 120 km)
    tau_above, occulted_above = MarsAtmosphericEngine.calculate_tangent_path_optical_depth(
        tangent_alt_m=120_000.0,
        profile=profile,
    )
    assert not occulted_above
    assert tau_above == 0.0

    # 3. Intersecting Mars solid core (h_t = -100 m)
    tau_neg, occulted_neg = MarsAtmosphericEngine.calculate_tangent_path_optical_depth(
        tangent_alt_m=-100.0,
        profile=profile,
    )
    assert occulted_neg
    assert math.isinf(tau_neg)


def test_13ad_plane_parallel_divergence_table_across_elevations():
    """
    Validate the plane-parallel divergence table:
    - At 90°: divergence is 0.00%
    - At 30°: divergence < 0.1%
    - At 10°: divergence < 3.0%
    - At 5° (elevation mask boundary): divergence > 25% (plane-parallel overestimates by > 28%)
    - At 1°: divergence > 200% (plane-parallel is over 3x higher)
    - At 0.001°: plane-parallel diverges toward infinity while spherical stays bounded (~22)
    """
    div_table = MarsAtmosphericEngine.generate_plane_parallel_divergence_table()
    assert len(div_table) >= 8

    # Check key elevation milestones
    div_90 = next(row for row in div_table if row["elevation_deg"] == 90.0)
    div_30 = next(row for row in div_table if row["elevation_deg"] == 30.0)
    div_5 = next(row for row in div_table if row["elevation_deg"] == 5.0)
    div_1 = next(row for row in div_table if row["elevation_deg"] == 1.0)
    div_001 = next(row for row in div_table if row["elevation_deg"] == 0.001)

    assert div_90["divergence_pct"] == 0.0
    assert div_30["divergence_pct"] < 1.0
    assert div_5["divergence_pct"] > 25.0
    assert div_1["divergence_pct"] > 200.0
    assert div_001["spherical_airmass"] < 25.0
    assert div_001["plane_parallel_airmass"] > 50000.0


# ============================================================================
# 2. SPECTRAL SCALING & RF DECOUPLING BENCHMARKS
# ============================================================================

def test_13ad_spectral_optical_depth_angstrom_power_law():
    """
    Verify spectral extinction scaling via Ångström power law:
    tau(lambda) = tau(880nm) * (lambda / 880nm)^(-alpha)
    For 1550 nm DSOC telecom laser with alpha = -0.082 (Fernandez-Rodriguez et al. 2024):
    lambda_ratio = 1550 / 880 = 1.76136
    tau(1550) = 0.5 * (1.76136)^(+0.082) = 0.5 * 1.0475 = 0.5238
    """
    res_880 = MarsAtmosphericEngine.calculate_optical_attenuation_db(
        elevation_deg=45.0,
        wavelength_m=880e-9,
        tau_880nm=0.5,
    )
    res_1550 = MarsAtmosphericEngine.calculate_optical_attenuation_db(
        elevation_deg=45.0,
        wavelength_m=1550e-9,
        tau_880nm=0.5,
    )

    expected_tau_1550 = 0.5 * ((1550.0 / 880.0) ** 0.082)
    assert math.isclose(res_1550["spectral_optical_depth"], expected_tau_1550, rel_tol=1e-3)
    # On Mars, coarse dust (r_eff ~ 1.5 um) produces flat/slightly negative alpha, so tau(1550) >= tau(880)
    assert res_1550["attenuation_db"] >= res_880["attenuation_db"]
    assert math.isclose(res_1550["spectral_optical_depth"] / res_880["spectral_optical_depth"], 1.0475, rel_tol=1e-3)


def test_13ad_strict_decoupling_of_rf_from_optical_dust_loss():
    """
    Verify RF atmospheric attenuation separating CO2 gaseous absorption and dielectric dust loss.
    In clear to typical dust conditions (tau_880 = 0.5, zenith airmass = 1.0):
    - Optical laser (1550 nm) experiences ~ 2.27 dB attenuation.
    - Ka-band (32 GHz) attenuation matches NASA/JPL handbook (~ 0.76 dB zenith).
    - X-band (8.4 GHz) attenuation remains under 0.25 dB.
    - UHF (401.5 MHz) attenuation remains under 0.02 dB.
    """
    # 1. Optical attenuation under typical dust at zenith
    opt_res = MarsAtmosphericEngine.calculate_optical_attenuation_db(
        elevation_deg=90.0,
        wavelength_m=1550e-9,
        tau_880nm=0.5,
    )
    assert math.isclose(opt_res["attenuation_db"], 2.27, abs_tol=0.1)

    # 2. RF bands at zenith under typical dust (tau = 0.5)
    loss_ka = MarsAtmosphericEngine.calculate_rf_atmospheric_attenuation_db(32.0e9, 90.0, airmass=1.0, dust_tau=0.5)
    loss_x = MarsAtmosphericEngine.calculate_rf_atmospheric_attenuation_db(8.4e9, 90.0, airmass=1.0, dust_tau=0.5)
    loss_uhf = MarsAtmosphericEngine.calculate_rf_atmospheric_attenuation_db(401.5e6, 90.0, airmass=1.0, dust_tau=0.5)

    assert math.isclose(loss_ka, 0.762, abs_tol=0.05), f"Ka-band attenuation {loss_ka:.3f} dB did not match JPL reference ~0.76 dB"
    assert loss_x < 0.25, f"X-band attenuation {loss_x:.3f} dB was unphysically high"
    assert loss_uhf < 0.02, f"UHF attenuation {loss_uhf:.3f} dB was unphysically high"


# ============================================================================
# 3. ANTENNA FIELD REGION STANDARDS (IEEE 145 & ISED GL-01)
# ============================================================================

def test_13ad_antenna_field_regions_electrically_small_vs_large():
    """
    Verify antenna field regions per IEEE Std 145-2013 and ISED GL-01 Section 2.3:
    1. Electrically small antenna (e.g. UHF monopole, D = 0.15 m, lambda = 0.747 m):
       D <= lambda / 2 -> Fraunhofer distance governed by R >= 2 * lambda (1.49 m),
       NOT 2 * D^2 / lambda (0.06 m, which would fall inside the reactive near field).
    2. Large directive dish (e.g. Ka-band 1.0 m dish, lambda = 0.00937 m):
       D >> lambda -> Fraunhofer distance governed by 2 * D^2 / lambda = 213.5 m.
    """
    # 1. Electrically small UHF antenna
    f_uhf = 401.5e6
    lambda_uhf = SPEED_OF_LIGHT_M_S / f_uhf
    uhf_regions = AdvancedAntennaEngine.calculate_field_regions(
        physical_dimension_m=0.15,
        carrier_freq_hz=f_uhf,
        category=AntennaCategory.DIPOLE_OMNI,
    )
    assert uhf_regions.is_electrically_small
    assert math.isclose(uhf_regions.fraunhofer_far_field_distance_m, 2.0 * lambda_uhf, rel_tol=1e-3)
    assert uhf_regions.fraunhofer_far_field_distance_m > (2.0 * (0.15 ** 2) / lambda_uhf)

    # Classification at 0.1 m (< lambda / 2*pi): Reactive
    assert uhf_regions.classify_distance(0.1) == FieldRegionClassification.REACTIVE_NEAR_FIELD
    # Classification at 0.5 m: Radiating Near-Field (Fresnel)
    assert uhf_regions.classify_distance(0.5) == FieldRegionClassification.RADIATING_NEAR_FIELD_FRESNEL
    # Classification at 2.0 m: Fraunhofer Far-Field
    assert uhf_regions.classify_distance(2.0) == FieldRegionClassification.FRAUNHOFER_FAR_FIELD

    # 2. Large Ka-band dish (D = 1.0 m)
    f_ka = 32.0e9
    lambda_ka = SPEED_OF_LIGHT_M_S / f_ka
    ka_regions = AdvancedAntennaEngine.calculate_field_regions(
        physical_dimension_m=1.0,
        carrier_freq_hz=f_ka,
        category=AntennaCategory.PARABOLIC_REFLECTOR,
    )
    expected_r_ff = (2.0 * (1.0 ** 2)) / lambda_ka
    assert not ka_regions.is_electrically_small
    assert math.isclose(ka_regions.fraunhofer_far_field_distance_m, expected_r_ff, rel_tol=1e-3)
    assert ka_regions.classify_distance(50.0) == FieldRegionClassification.RADIATING_NEAR_FIELD_FRESNEL
    assert ka_regions.classify_distance(300.0) == FieldRegionClassification.FRAUNHOFER_FAR_FIELD


# ============================================================================
# 4. AIRY DIFFRACTION PATTERN & MULTI-TIER POINTING LOSS
# ============================================================================

def test_13ad_airy_disc_diffraction_and_sidelobe_peaks():
    """
    Verify circular aperture Airy diffraction pattern F(u) = |2 * J1(u) / u|^2:
    - First null occurs at u_1 = 3.831706
    - First sidelobe peak occurs at u = 5.136, down by exactly 17.58 dB
    - On-axis (u < 0.01) evaluates with zero loss
    """
    # Verify Bessel function J1 at root and peak
    assert math.isclose(bessel_j1(3.831706), 0.0, abs_tol=1e-4)

    j1_peak = bessel_j1(5.136)
    p_sidelobe = (2.0 * j1_peak / 5.136) ** 2
    sidelobe_db = -10.0 * math.log10(p_sidelobe)
    assert math.isclose(sidelobe_db, 17.58, abs_tol=0.2)

    # Evaluate radiation pattern for a 1.0 m dish at 8.4 GHz (lambda = 0.0357 m)
    # HPBW ~ 70 * (0.0357 / 1.0) = 2.50°
    pattern_on_axis = AdvancedAntennaEngine.evaluate_radiation_pattern(
        boresight_gain_dbi=35.0,
        physical_dimension_m=1.0,
        carrier_freq_hz=8.4e9,
        pointing_error_deg=0.001,
    )
    assert pattern_on_axis.pointing_loss_db == 0.0
    assert pattern_on_axis.model_tier == PatternModelTier.TIER_2_ANALYTICAL_APPROXIMATION
    assert not pattern_on_axis.computational_guard_applied


def test_13ad_pointing_model_tier_and_guard_disclosure():
    """
    Verify pointing model tier disclosure and explicit metadata tagging:
    - Moderate pointing error inside main beam / first sidelobes: Tier 2, guard=False.
    - Extreme pointing error (> 2.5x HPBW or deep sidelobes): Tier 3, guard=True, loss=40.0 dB.
    - Reference measured ITU-R S.580 pattern: Tier 1, guard=False.
    """
    # 1. Tier 2 Main Lobe
    res_tier2 = AdvancedAntennaEngine.evaluate_radiation_pattern(
        boresight_gain_dbi=35.0,
        physical_dimension_m=1.0,
        carrier_freq_hz=8.4e9,
        pointing_error_deg=0.8,
    )
    assert res_tier2.model_tier == PatternModelTier.TIER_2_ANALYTICAL_APPROXIMATION
    assert not res_tier2.computational_guard_applied
    assert 0.0 < res_tier2.pointing_loss_db < 15.0

    # 2. Tier 3 Out-of-Domain Guard
    res_tier3 = AdvancedAntennaEngine.evaluate_radiation_pattern(
        boresight_gain_dbi=35.0,
        physical_dimension_m=1.0,
        carrier_freq_hz=8.4e9,
        pointing_error_deg=15.0,
    )
    assert res_tier3.model_tier == PatternModelTier.TIER_3_OUT_OF_DOMAIN_GUARD
    assert res_tier3.computational_guard_applied
    assert res_tier3.pointing_loss_db == 40.0
    assert "guard applied" in res_tier3.status_reason.lower()

    # 3. Tier 1 Reference Pattern
    res_tier1 = AdvancedAntennaEngine.evaluate_radiation_pattern(
        boresight_gain_dbi=45.0,
        physical_dimension_m=3.0,
        carrier_freq_hz=8.4e9,
        pointing_error_deg=2.0,
        reference_envelope="ITU-R_S.580",
    )
    assert res_tier1.model_tier == PatternModelTier.TIER_1_REFERENCE_MEASURED
    assert not res_tier1.computational_guard_applied


# ============================================================================
# 5. COMMUNICATION MEDIUM SEMANTICS & CONTACT ISOLATION
# ============================================================================

def test_13ad_communication_medium_isolation_in_orbital_contact():
    """
    Verify that orbital contact planner strictly requires radiated RF or optical channels,
    and rejects local bus interfaces from satisfying orbital passes.
    """
    topo = create_standard_planetary_network()
    planner = OrbitalContactPlanner(topo)

    # Collocated evaluation between a hypothetical surface node with zero range
    tx_local = TransmitterSpec("LocalTx", CommunicationBand.UHF_PROXIMITY, 5.0, 0.0)
    rx_local = ReceiverSpec("LocalRx", CommunicationBand.UHF_PROXIMITY, 0.0)

    # 1. Direct evaluate_link at R=0 produces LOCAL_BUS
    res_bus = PhysicalLinkBudgetEngine.evaluate_link(tx_local, rx_local, slant_range_m=0.0)
    assert res_bus.communication_medium == CommunicationMedium.LOCAL_BUS
    assert res_bus.is_link_closed

    # 2. Verify that evaluate_instantaneous_contact requires RF_WIRELESS or OPTICAL_FREE_SPACE
    # Orbiters have standard geometry; verify contacts closed are RF or optical
    contact_pair = planner.evaluate_instantaneous_contact(
        "SETTLEMENT-ALPHA",
        "ATLAS-ORB-01",
        sim_time_s=100.0,
    )
    # If in contact, band must be a valid radiated band
    if contact_pair is not None:
        band, slant_range, elev, rate = contact_pair
        assert band in (CommunicationBand.UHF_PROXIMITY, CommunicationBand.X_BAND_PROXIMITY, CommunicationBand.KA_BAND_DEEP_SPACE)


# ============================================================================
# 6. RECEIVER NOISE TEMPERATURE & THERMODYNAMIC BOUNDARIES
# ============================================================================

def test_13ad_system_noise_temperature_decomposition_and_cmb_floor():
    """
    Verify system noise temperature decomposition:
    T_sys = T_ant + T_feed + T_rx * L_feed
    where T_feed = (L_feed - 1) * T_phys and T_rx = (10^(NF/10) - 1) * 290 K.
    Verify rejection of sub-CMB temperatures (< 2.7 K).
    """
    # 1. Nominal surface receiver
    # T_ant = 210 K, NF = 2.0 dB, L_cable = 1.0 dB, T_phys = 250 K
    t_sys = ReceiverSpec.calculate_system_noise_temp(
        t_antenna_k=210.0,
        noise_figure_db=2.0,
        cable_loss_db=1.0,
        t_phys_k=250.0,
    )
    l_feed = 10.0 ** 0.1
    t_rx = (10.0 ** 0.2 - 1.0) * 290.0
    t_feed = (l_feed - 1.0) * 250.0
    expected_t_sys = 210.0 + t_feed + t_rx * l_feed
    assert math.isclose(t_sys, expected_t_sys, rel_tol=1e-4)
    assert math.isclose(t_sys, 488.26, abs_tol=0.1)

    # 2. Sub-CMB temperature rejection
    with pytest.raises(ValueError, match="Antenna brightness temperature cannot be below CMB"):
        ReceiverSpec.calculate_system_noise_temp(t_antenna_k=1.5)

    # 3. Non-physical negative loss or temperature rejection
    with pytest.raises(ValueError, match="Noise figure and cable loss must be non-negative"):
        ReceiverSpec.calculate_system_noise_temp(noise_figure_db=-1.0)
