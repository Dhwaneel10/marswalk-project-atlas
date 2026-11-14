# PROJECT ATLAS — MILESTONE 13AF
# Targeted Mutation Testing Campaign Report

**Mission Designation:** `ATLAS-13AF-INDEPENDENT-BENCHMARK`  
**Date:** 2026-11-07  
**Objective:** Verify that the 13AF independent benchmark and cross-module test suites actively detect ungrounded defaults, reversed spectral laws, disabled dust losses, double-counted receiver noise, and optimistic link-closure defaults.

---

## 1. Mutation Campaign Summary

| ID | Mutation Description | Target Source File | Status | Detection Evidence |
|:---|:---|:---|:---:|:---|
| **MUT-13AF-01** | Reverse Optical Spectral Dependence (Invert Exponent Sign) | `src/marswalk/core/atlas_mars_atmospheric_model.py` | **KILLED** | `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad` |
| **MUT-13AF-02** | Restore Unsupported Terrestrial Optical Default (+0.35) | `src/marswalk/core/atlas_mars_atmospheric_model.py` | **KILLED** | `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad` |
| **MUT-13AF-03** | Disable RF Dust Attenuation (Zero Dust Loss) | `src/marswalk/core/atlas_mars_atmospheric_model.py` | **KILLED** | `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad` |
| **MUT-13AF-04** | Change Dielectric Loss Parameters (Im(-K) reduced to 0.001) | `src/marswalk/core/atlas_mars_atmospheric_model.py` | **KILLED** | `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad` |
| **MUT-13AF-05** | Remove CMB Lower-Bound Check on Antenna Temperature | `src/marswalk/core/atlas_network_link_model.py` | **KILLED** | `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad` |
| **MUT-13AF-06** | Double-Count Feed Cable Noise in System Temperature | `src/marswalk/core/atlas_network_link_model.py` | **KILLED** | `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad` |
| **MUT-13AF-07** | Remove Far-Field Distance Screening Check in Link Budget | `src/marswalk/core/atlas_network_link_model.py` | **KILLED** | `FAILED tests/test_milestone_13ac_physics_boundaries.py::test_13ac_near` |
| **MUT-13AF-08** | Return Success (is_link_closed=True) for Insufficient Link Margin | `src/marswalk/core/atlas_network_link_model.py` | **KILLED** | `FAILED tests/test_milestone_13ac_physics_boundaries.py::test_13ac_nega` |

**Mutation Score:** 8 / 8 (100% Mutation Kill Rate)

---

## 2. Detailed Mutation Tracebacks & Analysis

### MUT-13AF-01: Reverse Optical Spectral Dependence (Invert Exponent Sign)
- **Target File:** `src/marswalk/core/atlas_mars_atmospheric_model.py`
- **Outcome:** `KILLED`
- **Failing Assertion:** `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_strict_decoupling_of_rf_from_optical_dust_loss`

```text
tests\test_milestone_13ad_mars_physics_validation.py:190: AssertionError
__________ test_13ad_strict_decoupling_of_rf_from_optical_dust_loss ___________

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
>       assert math.isclose(opt_res["attenuation_db"], 2.27, abs_tol=0.1)
E       assert False
E        +  where False = <built-in function isclose>(2.073, 2.27, abs_tol=0.1)
E        +    where <built-in function isclose> = math.isclose

tests\test_milestone_13ad_mars_physics_validation.py:211: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_milestone_13af_independent_benchmark.py::test_13af_optical_dust_angstrom_sensitivity_and_extrapolation_disclosure
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_production_optical_attenuation_with_corrected_angstrom
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_spectral_optical_depth_angstrom_power_law
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_strict_decoupling_of_rf_from_optical_dust_loss
4 failed, 43 passed in 0.80s
```

---

### MUT-13AF-02: Restore Unsupported Terrestrial Optical Default (+0.35)
- **Target File:** `src/marswalk/core/atlas_mars_atmospheric_model.py`
- **Outcome:** `KILLED`
- **Failing Assertion:** `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_strict_decoupling_of_rf_from_optical_dust_loss`

```text

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
>       assert math.isclose(opt_res["attenuation_db"], 2.27, abs_tol=0.1)
E       assert False
E        +  where False = <built-in function isclose>(1.781, 2.27, abs_tol=0.1)
E        +    where <built-in function isclose> = math.isclose

tests\test_milestone_13ad_mars_physics_validation.py:211: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_milestone_13af_independent_benchmark.py::test_13af_optical_dust_angstrom_sensitivity_and_extrapolation_disclosure
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_angstrom_spectral_inversion_and_multi_study_table
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_production_optical_attenuation_with_corrected_angstrom
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_rf_vs_optical_dust_insensitivity_ratio
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_spectral_optical_depth_angstrom_power_law
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_strict_decoupling_of_rf_from_optical_dust_loss
6 failed, 41 passed in 0.86s
```

---

### MUT-13AF-03: Disable RF Dust Attenuation (Zero Dust Loss)
- **Target File:** `src/marswalk/core/atlas_mars_atmospheric_model.py`
- **Outcome:** `KILLED`
- **Failing Assertion:** `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_strict_decoupling_of_rf_from_optical_dust_loss`

```text
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
    
>       assert math.isclose(loss_ka, 0.762, abs_tol=0.05), f"Ka-band attenuation {loss_ka:.3f} dB did not match JPL reference ~0.76 dB"
E       AssertionError: Ka-band attenuation 0.045 dB did not match JPL reference ~0.76 dB
E       assert False
E        +  where False = <built-in function isclose>(0.045, 0.762, abs_tol=0.05)
E        +    where <built-in function isclose> = math.isclose

tests\test_milestone_13ad_mars_physics_validation.py:218: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_milestone_13af_independent_benchmark.py::test_13af_rf_dust_multiband_replication_and_jpl_benchmark
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_rf_dust_attenuation_multi_band_and_scenarios
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_strict_decoupling_of_rf_from_optical_dust_loss
3 failed, 44 passed in 0.87s
```

---

### MUT-13AF-04: Change Dielectric Loss Parameters (Im(-K) reduced to 0.001)
- **Target File:** `src/marswalk/core/atlas_mars_atmospheric_model.py`
- **Outcome:** `KILLED`
- **Failing Assertion:** `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_strict_decoupling_of_rf_from_optical_dust_loss`

```text
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
    
>       assert math.isclose(loss_ka, 0.762, abs_tol=0.05), f"Ka-band attenuation {loss_ka:.3f} dB did not match JPL reference ~0.76 dB"
E       AssertionError: Ka-band attenuation 0.176 dB did not match JPL reference ~0.76 dB
E       assert False
E        +  where False = <built-in function isclose>(0.17606667279801952, 0.762, abs_tol=0.05)
E        +    where <built-in function isclose> = math.isclose

tests\test_milestone_13ad_mars_physics_validation.py:218: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_milestone_13af_independent_benchmark.py::test_13af_rf_dust_multiband_replication_and_jpl_benchmark
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_rf_dust_attenuation_multi_band_and_scenarios
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_strict_decoupling_of_rf_from_optical_dust_loss
3 failed, 44 passed in 0.81s
```

---

### MUT-13AF-05: Remove CMB Lower-Bound Check on Antenna Temperature
- **Target File:** `src/marswalk/core/atlas_network_link_model.py`
- **Outcome:** `KILLED`
- **Failing Assertion:** `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_system_noise_temperature_decomposition_and_cmb_floor`

```text
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
>       with pytest.raises(ValueError, match="Antenna brightness temperature cannot be below CMB"):
E       Failed: DID NOT RAISE ValueError

tests\test_milestone_13ad_mars_physics_validation.py:405: Failed
=========================== short test summary info ===========================
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_antenna_temperature_cmb_floor_enforcement
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_system_noise_temperature_decomposition_and_cmb_floor
2 failed, 45 passed in 0.90s
```

---

### MUT-13AF-06: Double-Count Feed Cable Noise in System Temperature
- **Target File:** `src/marswalk/core/atlas_network_link_model.py`
- **Outcome:** `KILLED`
- **Failing Assertion:** `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_system_noise_temperature_decomposition_and_cmb_floor`

```text

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
>       assert math.isclose(t_sys, expected_t_sys, rel_tol=1e-4)
E       assert False
E        +  where False = <built-in function isclose>(614.6943209675671, 488.2690548692085, rel_tol=0.0001)
E        +    where <built-in function isclose> = math.isclose

tests\test_milestone_13ad_mars_physics_validation.py:401: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_receiver_system_noise_invariance_across_reference_planes
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_system_noise_temperature_decomposition_and_cmb_floor
2 failed, 45 passed in 0.82s
```

---

### MUT-13AF-07: Remove Far-Field Distance Screening Check in Link Budget
- **Target File:** `src/marswalk/core/atlas_network_link_model.py`
- **Outcome:** `KILLED`
- **Failing Assertion:** `FAILED tests/test_milestone_13ac_physics_boundaries.py::test_13ac_near_field_out_of_domain_link_tagging`

```text
................................F..............                          [100%]
================================== FAILURES ===================================
_______________ test_13ac_near_field_out_of_domain_link_tagging _______________

    def test_13ac_near_field_out_of_domain_link_tagging():
        """Verify evaluate_link returns structured OUT_OF_DOMAIN result when inside near-field."""
        # Ka-band high-gain link (Fraunhofer distance ~ 24 meters)
        tx = TransmitterSpec("KaTx", CommunicationBand.KA_BAND_DEEP_SPACE, 20.0, 35.0)
        rx = ReceiverSpec("KaRx", CommunicationBand.KA_BAND_DEEP_SPACE, 35.0)
    
        # Slant range of 2.0 meters is well inside the 24 m near-field
        res = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, slant_range_m=2.0, elevation_deg=45.0)
    
>       assert not res.is_link_closed
E       AssertionError: assert not True
E        +  where True = LinkBudgetResult(slant_range_m=2.0, elevation_deg=45.0, carrier_freq_hz=32000000000.0, wavelength_m=0.0093685143125, f...NEL', pointing_model_tier='TIER_2_ANALYTICAL_APPROXIMATION', pointing_guard_applied=False, spectral_optical_depth=None).is_link_closed

tests\test_milestone_13ac_physics_boundaries.py:104: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_milestone_13ac_physics_boundaries.py::test_13ac_near_field_out_of_domain_link_tagging
1 failed, 46 passed in 0.75s
```

---

### MUT-13AF-08: Return Success (is_link_closed=True) for Insufficient Link Margin
- **Target File:** `src/marswalk/core/atlas_network_link_model.py`
- **Outcome:** `KILLED`
- **Failing Assertion:** `FAILED tests/test_milestone_13ac_physics_boundaries.py::test_13ac_negative_margin_strictly_prevents_link_closure`

```text
        res = PhysicalLinkBudgetEngine.evaluate_link(
            tx=tx_weak,
            rx=rx_standard,
            slant_range_m=10_000_000.0,  # 10,000 km
            elevation_deg=45.0,
        )
    
>       assert not res.is_link_closed
E       AssertionError: assert not True
E        +  where True = LinkBudgetResult(slant_range_m=10000000.0, elevation_deg=45.0, carrier_freq_hz=32000000000.0, wavelength_m=0.009368514...ELD', pointing_model_tier='TIER_2_ANALYTICAL_APPROXIMATION', pointing_guard_applied=False, spectral_optical_depth=None).is_link_closed

tests\test_milestone_13af_independent_benchmark.py:326: AssertionError
__________ test_13ac_negative_margin_strictly_prevents_link_closure ___________

    def test_13ac_negative_margin_strictly_prevents_link_closure():
        """Verify that insufficient link budget strictly sets is_link_closed=False and rate=0."""
        # Weak 0.001 W transmitter over 100,000 km
        tx = TransmitterSpec("WeakTx", CommunicationBand.UHF_PROXIMITY, 0.001, 0.0)
        rx = ReceiverSpec("WeakRx", CommunicationBand.UHF_PROXIMITY, 0.0)
    
        res = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, slant_range_m=100_000_000.0)
>       assert not res.is_link_closed
E       AssertionError: assert not True
E        +  where True = LinkBudgetResult(slant_range_m=100000000.0, elevation_deg=45.0, carrier_freq_hz=401500000.0, wavelength_m=0.7466810909...ELD', pointing_model_tier='TIER_2_ANALYTICAL_APPROXIMATION', pointing_guard_applied=False, spectral_optical_depth=None).is_link_closed

tests\test_milestone_13ac_physics_boundaries.py:210: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_milestone_13af_independent_benchmark.py::test_13af_strict_link_margin_rejection
FAILED tests/test_milestone_13ac_physics_boundaries.py::test_13ac_negative_margin_strictly_prevents_link_closure
2 failed, 45 passed in 0.78s
```

---
