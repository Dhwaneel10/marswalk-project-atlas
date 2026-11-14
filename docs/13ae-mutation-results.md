# PROJECT ATLAS — MILESTONE 13AE
# Targeted Mutation Testing Campaign Report

**Mission Designation:** `ATLAS-13AE-PROPAGATION-EVIDENCE-CLOSURE`  
**Date:** 2026-11-07  
**Objective:** Demonstrate that the 13AE dedicated and regression test suites actively detect unphysical implementations, reversed scaling laws, un-grounded assertions, and boundary violations.

---

## 1. Mutation Campaign Summary

| ID | Mutation Description | Target File | Status | Detection Evidence |
|:---|:---|:---|:---:|:---|
| **M1** | Restore Erroneous Positive Ångström Exponent (+0.35) | `src/marswalk/core/atlas_mars_atmospheric_model.py` | **KILLED** | `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad` |
| **M2** | Disable RF Dust-Storm Attenuation (Dust Loss Zeroed) | `src/marswalk/core/atlas_mars_atmospheric_model.py` | **KILLED** | `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad` |
| **M3** | Reverse Wavelength Scaling in Optical Extinction | `src/marswalk/core/atlas_mars_atmospheric_model.py` | **KILLED** | `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad` |
| **M4** | Omit Feed-Line Thermal Noise Generation (T_feed = 0) | `src/marswalk/core/atlas_network_link_model.py` | **KILLED** | `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad` |
| **M5** | Double-Count Cable Loss in System Noise Temperature | `src/marswalk/core/atlas_network_link_model.py` | **KILLED** | `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad` |
| **M6** | Remove CMB Lower-Bound Check on Antenna Temperature | `src/marswalk/core/atlas_network_link_model.py` | **KILLED** | `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad` |
| **M7** | Bypass Antenna Omni/Broadbeam Pattern Guard for High-Gain Airy Application | `src/marswalk/core/atlas_antenna_model.py` | **KILLED** | `FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test` |
| **M8** | Remove Small-Antenna Screening from Fraunhofer Calculation | `src/marswalk/core/atlas_antenna_model.py` | **KILLED** | `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad` |
| **M9** | Disable Out-of-Domain Pointing Error Computational Guard (Tier 3) | `src/marswalk/core/atlas_antenna_model.py` | **KILLED** | `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad` |

**Mutation Score:** 9 / 9 (100% Mutation Kill Rate)

---

## 2. Detailed Mutation Tracebacks & Analysis

### M1: Restore Erroneous Positive Ångström Exponent (+0.35)
- **Target File:** `src/marswalk/core/atlas_mars_atmospheric_model.py`
- **Outcome:** `KILLED`
- **Failing Assertion:** `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_strict_decoupling_of_rf_from_optical_dust_loss`

```text
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
E        +  where False = <built-in function isclose>(1.781, 2.27, abs_tol=0.1)
E        +    where <built-in function isclose> = math.isclose

tests\test_milestone_13ad_mars_physics_validation.py:211: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_angstrom_spectral_inversion_and_multi_study_table
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_production_optical_attenuation_with_corrected_angstrom
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_rf_vs_optical_dust_insensitivity_ratio
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_spectral_optical_depth_angstrom_power_law
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_strict_decoupling_of_rf_from_optical_dust_loss
5 failed, 17 passed in 0.65s
```

---

### M2: Disable RF Dust-Storm Attenuation (Dust Loss Zeroed)
- **Target File:** `src/marswalk/core/atlas_mars_atmospheric_model.py`
- **Outcome:** `KILLED`
- **Failing Assertion:** `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_strict_decoupling_of_rf_from_optical_dust_loss`

```text
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
    
>       assert math.isclose(loss_ka, 0.762, abs_tol=0.05), f"Ka-band attenuation {loss_ka:.3f} dB did not match JPL reference ~0.76 dB"
E       AssertionError: Ka-band attenuation 0.045 dB did not match JPL reference ~0.76 dB
E       assert False
E        +  where False = <built-in function isclose>(0.045, 0.762, abs_tol=0.05)
E        +    where <built-in function isclose> = math.isclose

tests\test_milestone_13ad_mars_physics_validation.py:218: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_rf_dust_attenuation_multi_band_and_scenarios
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_strict_decoupling_of_rf_from_optical_dust_loss
2 failed, 20 passed in 0.64s
```

---

### M3: Reverse Wavelength Scaling in Optical Extinction
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
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_production_optical_attenuation_with_corrected_angstrom
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_spectral_optical_depth_angstrom_power_law
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_strict_decoupling_of_rf_from_optical_dust_loss
3 failed, 19 passed in 0.64s
```

---

### M4: Omit Feed-Line Thermal Noise Generation (T_feed = 0)
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
E        +  where False = <built-in function isclose>(423.5377019206667, 488.2690548692085, rel_tol=0.0001)
E        +    where <built-in function isclose> = math.isclose

tests\test_milestone_13ad_mars_physics_validation.py:401: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_receiver_system_noise_invariance_across_reference_planes
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_system_noise_temperature_decomposition_and_cmb_floor
2 failed, 20 passed in 0.63s
```

---

### M5: Double-Count Cable Loss in System Noise Temperature
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
2 failed, 20 passed in 0.55s
```

---

### M6: Remove CMB Lower-Bound Check on Antenna Temperature
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
2 failed, 20 passed in 0.60s
```

---

### M7: Bypass Antenna Omni/Broadbeam Pattern Guard for High-Gain Airy Application
- **Target File:** `src/marswalk/core/atlas_antenna_model.py`
- **Outcome:** `KILLED`
- **Failing Assertion:** `FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_airy_applicability_guard_and_taper_disclosure`

```text
        assert not res_tier2.computational_guard_applied
        assert res_tier2.pointing_loss_db > 0.0
    
        # 2. Tier 3 Out of domain guard
        res_tier3 = AdvancedAntennaEngine.evaluate_radiation_pattern(
            boresight_gain_dbi=38.0,
            physical_dimension_m=1.2,
            carrier_freq_hz=32.0e9,
            pointing_error_deg=25.0,
        )
        assert res_tier3.model_tier == PatternModelTier.TIER_3_OUT_OF_DOMAIN_GUARD
        assert res_tier3.computational_guard_applied
        assert res_tier3.pointing_loss_db == 40.0
    
        # 3. Omni / Broadbeam antenna must bypass Airy diffraction and report flat wide-angle beam
        res_omni = AdvancedAntennaEngine.evaluate_radiation_pattern(
            boresight_gain_dbi=2.15,
            physical_dimension_m=0.15,
            carrier_freq_hz=401.5e6,
            pointing_error_deg=35.0,
            category=AntennaCategory.DIPOLE_OMNI,
        )
>       assert res_omni.pointing_loss_db == 0.1
E       AssertionError: assert 0.14266234578804288 == 0.1
E        +  where 0.14266234578804288 = AntennaRadiationPatternResult(boresight_gain_dbi=2.15, pointing_error_deg=35.0, hpbw_deg=70.0, effective_gain_dbi=2.00...APPROXIMATION'>, computational_guard_applied=False, status_reason='Main lobe Airy pattern (theta < first null 90.00°)').pointing_loss_db

tests\test_milestone_13ae_propagation_evidence_closure.py:538: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_airy_applicability_guard_and_taper_disclosure
1 failed, 21 passed in 0.59s
```

---

### M8: Remove Small-Antenna Screening from Fraunhofer Calculation
- **Target File:** `src/marswalk/core/atlas_antenna_model.py`
- **Outcome:** `KILLED`
- **Failing Assertion:** `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_antenna_field_regions_electrically_small_vs_large`

```text
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
>       assert uhf_regions.classify_distance(0.1) == FieldRegionClassification.REACTIVE_NEAR_FIELD
E       AssertionError: assert <FieldRegionC...IELD_FRESNEL'> == <FieldRegionC...E_NEAR_FIELD'>
E         
E         - REACTIVE_NEAR_FIELD
E         + RADIATING_NEAR_FIELD_FRESNEL

tests\test_milestone_13ad_mars_physics_validation.py:249: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_antenna_field_regions_electrically_small_vs_large
1 failed, 21 passed in 0.61s
```

---

### M9: Disable Out-of-Domain Pointing Error Computational Guard (Tier 3)
- **Target File:** `src/marswalk/core/atlas_antenna_model.py`
- **Outcome:** `KILLED`
- **Failing Assertion:** `FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_pointing_model_tier_and_guard_disclosure`

```text
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
>       assert res_tier3.model_tier == PatternModelTier.TIER_3_OUT_OF_DOMAIN_GUARD
E       AssertionError: assert <PatternModel...PPROXIMATION'> == <PatternModel...DOMAIN_GUARD'>
E         
E         - TIER_3_OUT_OF_DOMAIN_GUARD
E         + TIER_2_ANALYTICAL_APPROXIMATION

tests\test_milestone_13ad_mars_physics_validation.py:327: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_milestone_13ae_propagation_evidence_closure.py::test_13ae_airy_applicability_guard_and_taper_disclosure
FAILED tests/test_milestone_13ad_mars_physics_validation.py::test_13ad_pointing_model_tier_and_guard_disclosure
2 failed, 20 passed in 0.58s
```

---
