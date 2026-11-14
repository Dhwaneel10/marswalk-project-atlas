"""
MarsWalk 2.0 / Project Atlas — Milestone 13L Automated Test Suite.
Verifies the Atlas Planetary Environment Intelligence Digital Twin:
- Environmental Data Catalog & Provenance Integrity
- Spatiotemporal Environmental Field Model (2D/3D Rasters, NoData Handling)
- Environmental Uncertainty Engine (Non-Gaussian Sensor Tolerances)
- Mars Solar Geometry & 3D Ray-Cast Terrain Horizon Shadows
- Thermal Environment Intelligence & Diurnal Cycles
- Atmospheric Dust Opacity, Extinction & Optical Suitability
- Atmospheric Barometric Pressure & Diurnal Wind Vectors
- Environmental Hazard Model & Operational Rules
- Calibrated Deterministic Scenarios (ENV-A to ENV-E)
- Environmental Mission Windows Optimizer
- Draft 2020-12 JSON Schema Validation
"""

import math
import numpy as np
import pytest

from marswalk.core.environmental_data_catalog import (
    EnvironmentalDataCatalog,
    EnvironmentalProductMetadata,
    ProvenanceClass,
)
from marswalk.core.environment_field_model import (
    EnvironmentalField2D,
    FieldState,
    FieldSamplingMethod,
)
from marswalk.core.environmental_uncertainty import (
    EnvironmentalUncertaintyEngine,
    UncertaintyInterval,
)
from marswalk.core.mars_solar_environment import (
    MarsSolarGeometryEngine,
    SolarEphemeris,
    TerrainIlluminationResult,
)
from marswalk.core.mars_thermal_environment import (
    MarsThermalEnvironmentEngine,
    ThermalEvaluationResult,
    INSTRUMENT_THERMAL_LIMITS_C,
)
from marswalk.core.mars_dust_environment import (
    MarsDustEnvironmentEngine,
    DustEvaluationResult,
    INSTRUMENT_MAX_TAU_LIMITS,
)
from marswalk.core.mars_atmospheric_environment import (
    MarsAtmosphericEnvironmentEngine,
    AtmosphericStateResult,
)
from marswalk.core.environmental_hazard_model import (
    EnvironmentalHazardEngine,
    EnvironmentalAssessmentReport,
    HazardSeverity,
    HazardType,
)
from marswalk.core.environment_scenario_engine import (
    EnvironmentalScenarioEngine,
    EnvironmentalScenarioDefinition,
    ScenarioCode,
)
from marswalk.core.environmental_mission_window import (
    EnvironmentalMissionWindowOptimizer,
    EnvironmentalOpportunityWindow,
)
from marswalk.api.contracts import validate_contract


class TestEnvironmentalDataCatalog:
    """Verifies data catalog registration, provenance taxonomy, and attribution auditing."""

    def test_core_catalog_initialization(self):
        catalog = EnvironmentalDataCatalog()
        products = catalog.list_products()
        assert len(products) >= 6

        # Check USGS CTX DTM metadata
        ctx = catalog.get_product("USGS_CTX_DTM_JEZERO_20M")
        assert ctx is not None
        assert ctx.provenance_class == ProvenanceClass.REMOTE_SENSING_PRODUCT
        assert ctx.checksum_sha256 == "875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3"
        assert ctx.native_resolution_m == 20.0
        assert "USGS" in ctx.source_institution

    def test_provenance_validation_audit(self):
        catalog = EnvironmentalDataCatalog()
        # Verify valid product audit
        val_ctx = catalog.validate_product_provenance("USGS_CTX_DTM_JEZERO_20M")
        assert val_ctx["is_registered"] is True
        assert val_ctx["verification_status"] == "VERIFIED_AUTHENTIC"

        # Verify unregistered product handling
        val_unknown = catalog.validate_product_provenance("NON_EXISTENT_PRODUCT")
        assert val_unknown["is_registered"] is False
        assert val_unknown["verification_status"] == "UNREGISTERED_PRODUCT"

    def test_catalog_filtering(self):
        catalog = EnvironmentalDataCatalog()
        direct_obs = catalog.list_products(provenance_filter=ProvenanceClass.DIRECT_OBSERVATION)
        assert len(direct_obs) >= 1
        assert direct_obs[0].product_id == "NASA_M2020_MEDA_JEZERO_HISTORICAL"


class TestEnvironmentalFieldModel:
    """Verifies continuous raster field sampling, interpolation, and NoData preservation."""

    def test_field_sampling_nearest_and_bilinear(self):
        data = np.array([
            [10.0, 20.0],
            [30.0, 40.0],
        ], dtype=np.float32)
        valid_mask = np.ones((2, 2), dtype=bool)

        field = EnvironmentalField2D(
            parameter_name="test_field",
            units="m",
            data=data,
            valid_mask=valid_mask,
            product_id="test_prod",
        )

        # Nearest neighbor
        val_near, state_near = field.sample(0.2, 0.2, method=FieldSamplingMethod.NEAREST)
        assert state_near == FieldState.VALID
        assert val_near == 10.0

        # Sub-pixel bilinear at exact center (0.5, 0.5) -> (10 + 20 + 30 + 40) / 4 = 25.0
        val_bi, state_bi = field.sample(0.5, 0.5, method=FieldSamplingMethod.BILINEAR)
        assert state_bi == FieldState.INTERPOLATED
        assert val_bi == 25.0

    def test_field_nodata_boundary_preservation(self):
        data = np.array([
            [10.0, 20.0],
            [30.0, -9999.0],
        ], dtype=np.float32)
        valid_mask = np.array([
            [True, True],
            [True, False],  # Bottom right is NoData
        ])

        field = EnvironmentalField2D(
            parameter_name="elevation",
            units="m",
            data=data,
            valid_mask=valid_mask,
            product_id="test_elev",
        )

        # Bilinear sample in quadrant touching NoData corner must be rejected as NO_DATA
        val, state = field.sample(0.5, 0.5, method=FieldSamplingMethod.BILINEAR)
        assert val is None
        assert state == FieldState.NO_DATA

        # Out-of-bounds coordinate
        val_oob, state_oob = field.sample(5.0, 5.0)
        assert val_oob is None
        assert state_oob == FieldState.OUTSIDE_SOURCE_COVERAGE


class TestEnvironmentalUncertainty:
    """Verifies physical confidence bounds derived from sensor specifications."""

    def test_elevation_uncertainty(self):
        interval = EnvironmentalUncertaintyEngine.evaluate_elevation_interval(-2500.0)
        assert interval.nominal == -2500.0
        assert interval.lower_bound == -2501.0
        assert interval.upper_bound == -2499.0
        assert interval.span == 2.0
        assert interval.contains(-2500.5)
        assert not interval.contains(-2502.0)

    def test_temperature_intervals(self):
        t_air = EnvironmentalUncertaintyEngine.evaluate_air_temperature_interval(-40.0)
        assert t_air.lower_bound == -42.5
        assert t_air.upper_bound == -37.5
        assert t_air.span == 5.0

        t_gnd = EnvironmentalUncertaintyEngine.evaluate_ground_temperature_interval(-20.0)
        assert t_gnd.lower_bound == -23.0
        assert t_gnd.upper_bound == -17.0


class TestMarsSolarGeometryAndShadows:
    """Verifies celestial solar ephemeris and 3D ray-cast terrain shadows."""

    def test_solar_ephemeris_vernal_equinox_noon(self):
        engine = MarsSolarGeometryEngine(ref_latitude_deg=18.442)
        # Sol 1 at vernal equinox Ls=0°, local solar noon LTST=12.0
        ephem = engine.compute_solar_ephemeris(sol=1, ltst_hours=12.0, base_ls_deg=0.0)

        assert ephem.sol == 1
        assert ephem.ltst_hours == 12.0
        assert ephem.solar_longitude_ls_deg == 0.0
        assert abs(ephem.solar_declination_deg) < 0.1  # Equator declination ≈ 0°
        assert abs(ephem.hour_angle_deg) < 0.1         # Noon hour angle ≈ 0°
        # At latitude 18.442° N and declination 0°, solar elevation ≈ 90° - 18.442° ≈ 71.558°
        assert abs(ephem.solar_elevation_deg - 71.56) < 0.2
        assert ephem.is_sun_above_horizon is True
        assert ephem.toa_irradiance_w_m2 > 400.0

    def test_solar_nighttime_detection(self):
        engine = MarsSolarGeometryEngine(ref_latitude_deg=18.442)
        # Midnight LTST = 0.0
        ephem = engine.compute_solar_ephemeris(sol=1, ltst_hours=0.0)
        assert ephem.is_sun_above_horizon is False
        assert ephem.solar_elevation_deg < -50.0

    def test_raycast_terrain_shadow_behind_cliff(self):
        engine = MarsSolarGeometryEngine(ref_latitude_deg=18.442)
        # Create synthetic synthetic 100x100 terrain with a 500m cliff wall
        elevation = np.zeros((100, 100), dtype=np.float32)
        elevation[:, 40:45] = 500.0  # High ridge running North-South
        slope = np.zeros((100, 100), dtype=np.float32)

        # Sun low in the West (late afternoon LTST = 17.0, azimuth towards West ~260-270°)
        ephem = engine.compute_solar_ephemeris(sol=1, ltst_hours=17.0)

        # Point situated directly East of the cliff (row 50, col 50)
        # Since the Sun is in the West, the cliff at col 40-45 blocks the solar ray
        result = engine.evaluate_point_illumination(
            row=50.0,
            col=50.0,
            elevation_grid=elevation,
            slope_grid=slope,
            ephemeris=ephem,
            dx_ground_m=20.0,
            dy_ground_m=20.0,
        )

        assert result.is_daylight is True
        assert result.is_terrain_shadowed is True
        assert result.is_illuminated is False
        assert result.obstruction_distance_m is not None
        assert result.direct_flux_w_m2 == 0.0


class TestMarsThermalEnvironment:
    """Verifies diurnal temperature curves and instrument envelope gates."""

    def test_diurnal_curve_extrema(self):
        engine = MarsThermalEnvironmentEngine(base_elevation_m=-2500.0)
        # Peak ground temp occurs around 13:00 LTST
        t_air_noon, t_gnd_noon = engine.compute_diurnal_temperatures(13.0, elevation_m=-2500.0)
        # Coldest occurs near dawn (~05:30 LTST)
        t_air_dawn, t_gnd_dawn = engine.compute_diurnal_temperatures(5.5, elevation_m=-2500.0)

        assert t_gnd_noon > -25.0
        assert t_gnd_dawn < -80.0
        assert t_gnd_noon > t_gnd_dawn

    def test_instrument_thermal_limits(self):
        engine = MarsThermalEnvironmentEngine()
        # SHERLOC requires min -35°C
        # At dawn (05:30 LTST), air temperature is ~ -80°C, so it should violate limit
        dawn_eval = engine.evaluate_instrument_thermal_state(1, 5.5, "SHERLOC")
        assert dawn_eval.is_instrument_within_limits is False
        assert "below minimum operational limit" in dawn_eval.thermal_violation_reason

        # At mid-afternoon (14:00 LTST), air temperature is ~ -22°C, which is within [-35°C, +30°C]
        noon_eval = engine.evaluate_instrument_thermal_state(1, 14.0, "SHERLOC")
        assert noon_eval.is_instrument_within_limits is True
        assert noon_eval.thermal_violation_reason is None


class TestMarsDustAndAtmosphere:
    """Verifies atmospheric dust extinction and barometric wind models."""

    def test_dust_opacity_suitability(self):
        engine = MarsDustEnvironmentEngine()
        # SuperCam limit is tau=1.5
        # Under clear skies tau=0.45: suitable
        clear_eval = engine.evaluate_instrument_dust_suitability(1, 12.0, "SUPERCAM", current_tau=0.45)
        assert clear_eval.is_instrument_suitable is True
        assert clear_eval.visibility_status == "NOMINAL_CLEAR"

        # Under regional dust storm tau=2.2: unsuitable
        storm_eval = engine.evaluate_instrument_dust_suitability(1, 12.0, "SUPERCAM", current_tau=2.2)
        assert storm_eval.is_instrument_suitable is False
        assert storm_eval.visibility_status == "DUST_STORM"
        assert "exceeds instrument limit" in storm_eval.dust_violation_reason

    def test_atmospheric_pressure_and_wind(self):
        engine = MarsAtmosphericEnvironmentEngine()
        # Scale height pressure at -2500m (Jezero Crater) vs +5000m (Crater rim/plateau)
        p_crater = engine.compute_barometric_pressure(-2500.0)
        p_rim = engine.compute_barometric_pressure(5000.0)
        assert p_crater > p_rim  # Crater floor is denser/higher pressure than rim
        assert 700.0 < p_crater < 850.0

        # Afternoon convective gusts
        _, _, gust = engine.compute_surface_wind(15.0, wind_anomaly_m_s=15.0)
        assert gust > 20.0


class TestEnvironmentalHazardEngine:
    """Verifies operational hazard rules and severity scoring."""

    def test_critical_nighttime_optical_hazard(self):
        report = EnvironmentalHazardEngine.evaluate_observation_safety(
            sol=1,
            ltst_hours=2.0,
            target_id="tgt_sample",
            instrument_name="MASTCAM_Z",
            is_illuminated=False,
            is_terrain_shadowed=False,
            is_daylight=False,
            air_temperature_c=-75.0,
            optical_depth_tau=0.45,
            wind_gust_m_s=5.0,
        )
        assert report.is_operation_permissible is False
        assert report.to_dict()["critical_count"] >= 1
        haz_types = [h.hazard_type for h in report.hazards]
        assert HazardType.ILLUMINATION_UNAVAILABLE in haz_types


class TestEnvironmentalScenarios:
    """Verifies deterministic calibrated scenarios ENV-A through ENV-E."""

    def test_all_scenarios_registered(self):
        engine = EnvironmentalScenarioEngine()
        scenarios = engine.list_scenarios()
        assert len(scenarios) == 6  # Baseline + 5 stress scenarios

        codes = {s.scenario_code for s in scenarios}
        assert ScenarioCode.BASELINE_NOMINAL in codes
        assert ScenarioCode.ENV_A_REDUCED_ILLUMINATION in codes
        assert ScenarioCode.ENV_B_ELEVATED_THERMAL_STRESS in codes
        assert ScenarioCode.ENV_C_DUST_STORM_OPACITY in codes
        assert ScenarioCode.ENV_D_ATMOSPHERIC_WIND_PERTURBATION in codes
        assert ScenarioCode.ENV_E_COMPOUND_DISTURBANCE in codes

    def test_scenario_perturbation_properties(self):
        engine = EnvironmentalScenarioEngine()
        env_c = engine.get_scenario(ScenarioCode.ENV_C_DUST_STORM_OPACITY)
        assert env_c.dust_tau_override == 2.40
        assert env_c.solar_flux_factor == 0.30
        assert "MASTCAM_Z" in env_c.affected_subsystems


class TestEnvironmentalMissionWindowsOptimizer:
    """Verifies synthesis of hazard-free observation windows."""

    def test_optimal_window_synthesis(self):
        optimizer = EnvironmentalMissionWindowOptimizer()
        window = optimizer.find_optimal_observation_window(
            target_id="tgt_delta_crest",
            target_row=125.0,
            target_col=125.0,
            instrument_name="MASTCAM_Z",
            sol=1,
            required_duration_hours=1.0,
        )

        assert window.is_valid is True
        assert window.duration_hours == 1.0
        assert 10.0 <= window.start_ltst <= 15.0  # Midday peak sunlight
        assert window.quality_score > 0.6
        assert window.mean_direct_flux_w_m2 > 100.0


class TestDraft202012SchemaContracts:
    """Verifies strict Draft 2020-12 JSON Schema compliance for all 13L payloads."""

    def test_catalog_contract_validation(self):
        from marswalk.api.service import environmental_catalog_api
        res = environmental_catalog_api()
        validate_contract(res, "environmental-catalog", raise_on_error=True)

    def test_solar_contract_validation(self):
        from marswalk.api.service import environmental_solar_api
        res = environmental_solar_api({"sol": 2, "ltst_hours": 13.5})
        validate_contract(res, "environmental-solar", raise_on_error=True)

    def test_point_eval_contract_validation(self):
        from marswalk.api.service import environmental_point_eval_api
        res = environmental_point_eval_api({
            "sol": 1,
            "ltst_hours": 12.0,
            "row": 120.0,
            "col": 130.0,
            "instrument_name": "SUPERCAM",
        })
        validate_contract(res, "environmental-point-eval", raise_on_error=True)

    def test_scenarios_contract_validation(self):
        from marswalk.api.service import environmental_scenarios_api
        res = environmental_scenarios_api()
        validate_contract(res, "environmental-scenario", raise_on_error=True)

    def test_window_contract_validation(self):
        from marswalk.api.service import environmental_window_api
        res = environmental_window_api({
            "target_id": "test_tgt",
            "row": 100.0,
            "col": 100.0,
            "sol": 1,
            "instrument_name": "MASTCAM_Z",
            "duration_hours": 1.0,
        })
        validate_contract(res, "environmental-window", raise_on_error=True)
