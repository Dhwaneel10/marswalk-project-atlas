"""
MarsWalk 2.0 / Project Atlas — Milestone 13P: Planetary Aerial Corps Dedicated Verification Suite
================================================================================================
Exhaustive automated test suite validating:
- Martian CO2 atmospheric equation of state, speed of sound, and Sutherland viscosity.
- Thin-atmosphere rotor aerodynamics, tip Mach numbers, and low-Reynolds drag scaling.
- Momentum Theory hover power, translational lift, and best-endurance speed.
- Three reference aircraft specifications (Light Scout, Science Scout, Science Mapper).
- Performance envelopes, thrust margins (TM >= 1.15), and physics invariants.
- 3D terrain-aware navigation, landing site suitability, and GNC flight dynamics under wind.
- Aerial science payloads (Visible GSD, NIR spectrometry, synthetic GPR radar disclosures).
- Rover-aircraft cooperation, obstacle identification, and route uncertainty reduction.
- Multi-aircraft 4D corridor deconfliction and task allocation.
- Flagship Scenario 01 "The Crater Reveal" (all 6 stages) and Draft 2020-12 schema contracts.
"""

import math
import pytest
from typing import Dict, Any

from marswalk.core.mars_rotor_aerodynamics import (
    compute_atmospheric_properties,
    AtmosphericProperties,
    MarsRotorAerodynamics,
    RotorGeometry,
    MARS_GRAVITY,
)
from marswalk.core.mars_aircraft_fleet import (
    AircraftProfile,
    AircraftSpecification,
    AircraftState,
    FlightMode,
    AircraftHealthState,
    MarsAircraftFleetManager,
    AIRCRAFT_SPEC_CATALOG,
    SPEC_LIGHT_SCOUT,
    SPEC_SCIENCE_SCOUT,
    SPEC_SCIENCE_MAPPER,
)
from marswalk.core.mars_aircraft_performance import (
    MarsAircraftPerformanceEngine,
    ModelingFidelityLevel,
    PerformanceEnvelope,
)
from marswalk.core.mars_flight_dynamics import (
    MarsFlightDynamicsSimulator,
    PIDController,
)
from marswalk.core.mars_aerial_navigation import (
    MarsAerialNavigationEngine,
    LandingSiteEvaluation,
    AerialFlightPlan,
)
from marswalk.core.mars_aerial_science import (
    MarsAerialScienceEngine,
    SensorModality,
)
from marswalk.core.mars_aerial_rover_coordinator import (
    MarsAerialRoverCoordinator,
)
from marswalk.core.mars_aerial_fleet_intelligence import (
    MarsAerialFleetIntelligence,
)
from marswalk.core.mars_aerial_scenario_engine import (
    MarsAerialScenarioEngine,
)
from marswalk.api.contracts import validate_contract


class TestMilestone13PAerialCorps:

    def test_01_atmospheric_properties_co2_eos(self):
        """Validates CO2 Equation of State, speed of sound, and Sutherland's viscosity on Mars."""
        atmos = compute_atmospheric_properties(pressure_pa=610.0, temperature_k=215.0)
        assert atmos.is_valid is True
        # Ideal Gas Law: rho = 610 / (188.922 * 215) = ~0.01502 kg/m3
        assert 0.0145 <= atmos.density_kg_m3 <= 0.0155
        # Speed of Sound in CO2: a = sqrt(1.29 * 188.922 * 215) = ~228.9 m/s
        assert 225.0 <= atmos.speed_of_sound_m_s <= 235.0
        # Sutherland viscosity: ~1.1e-5 Pa*s
        assert 1.0e-5 <= atmos.dynamic_viscosity_pa_s <= 1.3e-5
        assert atmos.kinematic_viscosity_m2_s > 0.0

    def test_02_rotor_kinematics_and_tip_mach(self):
        """Verifies blade tip velocity, Mach number, and low-Reynolds number at 75% radius."""
        geom = RotorGeometry(radius_m=0.605, mean_chord_m=0.08)
        solver = MarsRotorAerodynamics(geom)
        atmos = compute_atmospheric_properties()

        # Ingenuity at 2537 RPM: omega = 265.67 rad/s, V_tip = 265.67 * 0.605 = 160.73 m/s
        pt = solver.evaluate_flight_condition(
            total_mass_kg=1.8,
            rotor_rpm=2537.0,
            atmosphere=atmos,
        )
        assert 158.0 <= pt.tip_velocity_m_s <= 163.0
        # Tip Mach: ~160.7 / 228.9 = ~0.702
        assert 0.68 <= pt.tip_mach <= 0.73
        # Reynolds number at 75% radius (V = ~120 m/s): Re = rho * V * c / mu = ~13,000 - 17,000
        assert 10000 <= pt.reynolds_number <= 25000

    def test_03_momentum_theory_hover_thrust_and_induced_power(self):
        """Validates momentum theory hover induced velocity and induced power."""
        geom = RotorGeometry(radius_m=0.605)
        solver = MarsRotorAerodynamics(geom)
        atmos = compute_atmospheric_properties()
        m = 1.8
        t_req = m * MARS_GRAVITY  # 6.698 N

        pt = solver.evaluate_flight_condition(total_mass_kg=m, rotor_rpm=2537.0, atmosphere=atmos)
        assert abs(pt.thrust_n - t_req) < 1e-3
        # Disk loading: T / A = 6.698 / (pi * 0.605^2) = ~5.82 N/m2
        assert 5.0 <= pt.disk_loading_n_m2 <= 6.5
        # Ideal induced velocity: v_i = sqrt(T / (2 * rho * A)) = ~13.9 m/s
        assert 12.0 <= pt.ideal_induced_velocity_m_s <= 16.0
        assert pt.induced_power_w > 0.0
        assert pt.profile_power_w > 0.0
        assert pt.total_aerodynamic_power_w > pt.induced_power_w

    def test_04_low_reynolds_and_compressibility_corrections(self):
        """Verifies that high tip Mach (> 0.72) and low Reynolds (< 20,000) apply drag penalties."""
        geom = RotorGeometry(radius_m=0.605)
        solver = MarsRotorAerodynamics(geom)
        atmos = compute_atmospheric_properties()

        # At 2800 RPM, tip speed is ~177 m/s => Tip Mach ~0.77 (> 0.72 critical Mach)
        pt_high = solver.evaluate_flight_condition(total_mass_kg=1.8, rotor_rpm=2800.0, atmosphere=atmos)
        assert pt_high.is_compressibility_penalized is True
        assert pt_high.tip_mach > 0.75

    def test_05_forward_flight_translational_lift(self):
        """Verifies translational lift: forward speed decreases induced power and finds min power speed."""
        geom = RotorGeometry(radius_m=0.605)
        solver = MarsRotorAerodynamics(geom)
        atmos = compute_atmospheric_properties()

        hover_pt = solver.evaluate_flight_condition(total_mass_kg=1.8, rotor_rpm=2537.0, forward_speed_m_s=0.0, atmosphere=atmos)
        cruise_pt = solver.evaluate_flight_condition(total_mass_kg=1.8, rotor_rpm=2537.0, forward_speed_m_s=6.0, atmosphere=atmos)

        # Due to translational lift, induced power in forward flight is significantly lower than hover
        assert cruise_pt.induced_power_w < hover_pt.induced_power_w
        # Parasite drag increases with forward speed
        assert cruise_pt.parasite_power_w > hover_pt.parasite_power_w

        best_spd, min_pwr = solver.find_minimum_power_speed(total_mass_kg=1.8, rotor_rpm=2537.0, atmosphere=atmos)
        assert 3.0 <= best_spd <= 10.0
        assert min_pwr <= hover_pt.total_electrical_power_w

    def test_06_aircraft_specification_catalog(self):
        """Verifies that all 3 reference aircraft profiles are configured with valid engineering data."""
        assert len(AIRCRAFT_SPEC_CATALOG) == 3
        light = AIRCRAFT_SPEC_CATALOG[AircraftProfile.LIGHT_SCOUT]
        scout = AIRCRAFT_SPEC_CATALOG[AircraftProfile.SCIENCE_SCOUT]
        mapper = AIRCRAFT_SPEC_CATALOG[AircraftProfile.SCIENCE_MAPPER]

        assert light.dry_mass_kg == 1.8
        assert scout.dry_mass_kg == 3.8 and scout.nominal_payload_kg == 0.70
        assert mapper.dry_mass_kg == 15.0 and mapper.max_payload_kg == 5.0
        assert light.battery_capacity_wh == 35.0
        assert scout.battery_capacity_wh == 85.0
        assert mapper.battery_capacity_wh == 360.0

    def test_07_aircraft_fleet_lifecycle_and_telemetry(self):
        """Verifies fleet manager registration, telemetry updates, and airborne distance accumulation."""
        mgr = MarsAircraftFleetManager()
        ac = mgr.get_aircraft("AERO-INGENUITY-01")
        assert ac is not None
        assert ac.is_airborne is False

        mgr.update_aircraft_telemetry(
            aircraft_id="AERO-INGENUITY-01",
            flight_mode=FlightMode.FORWARD_FLIGHT,
            position_xyz_m=[10.0, 20.0, 15.0],
            velocity_xyz_m_s=[5.0, 0.0, 0.0],
            battery_soc_pct=92.5,
            dt_seconds=2.0,
        )
        assert ac.is_airborne is True
        assert ac.total_flight_time_s == 2.0
        assert ac.total_distance_flown_m == 10.0  # 5.0 m/s * 2.0 s

    def test_08_performance_envelope_evaluation(self):
        """Verifies performance envelope calculations, thrust margins, and endurance."""
        perf = MarsAircraftPerformanceEngine()
        spec = SPEC_LIGHT_SCOUT
        env = perf.evaluate_envelope(specification=spec)

        assert env.is_flight_feasible is True
        assert env.hover_thrust_margin >= 1.15
        assert env.estimated_hover_endurance_s > 60.0
        assert env.usable_energy_wh == spec.battery_capacity_wh * 0.80

    def test_09_physics_invariant_payload_scaling(self):
        """Physics Invariant: Adding payload must increase required thrust, never decrease it."""
        perf = MarsAircraftPerformanceEngine()
        spec = SPEC_SCIENCE_SCOUT
        env_light = perf.evaluate_envelope(specification=spec, payload_mass_kg=0.0)
        env_heavy = perf.evaluate_envelope(specification=spec, payload_mass_kg=0.8)

        assert env_heavy.hover_thrust_required_n > env_light.hover_thrust_required_n
        assert env_heavy.hover_thrust_margin < env_light.hover_thrust_margin
        assert env_heavy.estimated_hover_endurance_s < env_light.estimated_hover_endurance_s

    def test_10_physics_invariant_density_scaling(self):
        """Physics Invariant: Lower atmospheric density reduces thrust margin and cannot improve hover."""
        perf = MarsAircraftPerformanceEngine()
        spec = SPEC_LIGHT_SCOUT
        atmos_nominal = compute_atmospheric_properties(pressure_pa=610.0, temperature_k=215.0)
        atmos_thin = compute_atmospheric_properties(pressure_pa=450.0, temperature_k=240.0)

        assert atmos_thin.density_kg_m3 < atmos_nominal.density_kg_m3
        env_nom = perf.evaluate_envelope(specification=spec, atmosphere=atmos_nominal)
        env_thin = perf.evaluate_envelope(specification=spec, atmosphere=atmos_thin)

        assert env_thin.hover_thrust_margin < env_nom.hover_thrust_margin
        assert env_thin.hover_power_w > env_nom.hover_power_w

    def test_11_physics_invariant_energy_non_negativity(self):
        """Physics Invariant: Power and energy consumption are strictly positive."""
        perf = MarsAircraftPerformanceEngine()
        spec = SPEC_LIGHT_SCOUT
        env = perf.evaluate_envelope(specification=spec)
        assert env.hover_power_w > 0.0
        assert env.cruise_power_w > 0.0
        assert env.usable_energy_wh > 0.0
        assert env.invariants_validated["INV-ENERGY-NON-NEGATIVE-02"] is True

    def test_12_landing_site_suitability_assessment(self):
        """Verifies transparent landing site assessment and rejection of steep/rough terrain."""
        nav = MarsAerialNavigationEngine()
        # Safe flat site
        safe_eval = nav.evaluate_landing_site([10.0, 10.0], ground_slope_deg=3.5, terrain_roughness_m=0.03, nearest_boulder_distance_m=12.0)
        assert safe_eval.is_suitable is True
        assert len(safe_eval.rejection_reasons) == 0

        # Unsafe steep site
        steep_eval = nav.evaluate_landing_site([20.0, 20.0], ground_slope_deg=14.2, terrain_roughness_m=0.05)
        assert steep_eval.is_suitable is False
        assert any("SLOPE" in r for r in steep_eval.rejection_reasons)

        # Unsafe boulder strike site
        boulder_eval = nav.evaluate_landing_site([30.0, 30.0], nearest_boulder_distance_m=2.5)
        assert boulder_eval.is_suitable is False
        assert any("BOULDER" in r for r in boulder_eval.rejection_reasons)

    def test_13_flight_corridor_generation(self):
        """Verifies 3D flight corridor generation with altitude clearance and energy checks."""
        nav = MarsAerialNavigationEngine(min_terrain_clearance_m=8.0)
        plan = nav.plan_reconnaissance_corridor(
            plan_id="PLAN-TEST-01",
            aircraft_id="AERO-INGENUITY-01",
            origin_xy_m=[0.0, 0.0],
            target_xy_m=[50.0, 50.0],
            cruise_altitude_agl_m=12.0,
            cruise_speed_m_s=6.0,
        )
        assert plan.is_terrain_cleared is True
        assert plan.is_plan_feasible is True
        assert plan.cruise_altitude_agl_m == 12.0
        assert plan.total_3d_flight_distance_m > plan.total_ground_distance_m

    def test_14_pid_flight_dynamics_and_wind_compensation(self):
        """Verifies closed-loop PID control and trajectory simulation under crosswind."""
        spec = SPEC_LIGHT_SCOUT
        sim = MarsFlightDynamicsSimulator(spec)
        initial_state = AircraftState(aircraft_id="AERO-TEST", specification=spec)

        traj = sim.simulate_waypoint_flight(
            initial_state=initial_state,
            target_waypoints_xyz_m=[[20.0, 0.0, 10.0], [40.0, 0.0, 10.0]],
            wind_vector_m_s=[0.0, 8.0, 0.0],  # 8 m/s crosswind
            dt_seconds=0.2,
            max_duration_s=60.0,
        )
        assert len(traj) > 5
        # Verify touchdown occurred
        assert initial_state.flight_mode == FlightMode.TOUCHDOWN_SHUTDOWN
        assert initial_state.position_xyz_m[2] == 0.0
        assert initial_state.battery_soc_pct < 100.0

    def test_15_aerial_science_optical_and_nir(self):
        """Verifies visible camera footprint / GSD scaling with altitude and NIR spectrometry."""
        sci = MarsAerialScienceEngine()
        obs_vis_low = sci.acquire_visible_imagery("AERO-01", [0.0, 0.0, 10.0], 1342.0)
        obs_vis_high = sci.acquire_visible_imagery("AERO-01", [0.0, 0.0, 20.0], 1342.0)

        # Higher altitude => larger GSD (coarser pixel) and larger footprint
        assert obs_vis_high.ground_sampling_distance_cm_px > obs_vis_low.ground_sampling_distance_cm_px
        assert obs_vis_high.sensor_footprint_radius_m > obs_vis_low.sensor_footprint_radius_m

        obs_nir = sci.acquire_nir_multispectral("AERO-02", [10.0, 10.0, 15.0], 1342.0)
        assert obs_nir.sensor_modality == SensorModality.NIR_MULTISPECTRAL
        assert obs_nir.primary_metric_name == "PHYLLOSILICATE_BAND_DEPTH_2.3UM"

    def test_16_synthetic_gpr_radar_sounding_truth_disclosure(self):
        """Verifies synthetic Ground-Penetrating Radar acquisition and mandatory truth disclosure."""
        sci = MarsAerialScienceEngine()
        obs_gpr = sci.acquire_synthetic_gpr_radar("AERO-03", [50.0, 50.0, 25.0], 1342.0, simulated_layer_depth_m=3.5)

        assert obs_gpr.is_synthetic_scenario_model is True
        assert obs_gpr.sensor_modality == SensorModality.SYNTHETIC_GPR_RADAR
        assert "DISCLOSURE" in obs_gpr.geological_context["water_ice_provenance_warning"]
        assert "SYNTHETIC SCENARIO MODEL" in obs_gpr.scientific_provenance

    def test_17_rover_aircraft_cooperative_planning(self):
        """Verifies cooperative reconnaissance: obstacle discovery, path shortening, and uncertainty reduction."""
        coord = MarsAerialRoverCoordinator()
        plan = coord.plan_joint_reconnaissance(
            rover_id="ROVER-01",
            aircraft_id="AERO-01",
            target_region_name="Jezero Gateway",
            rover_current_xy_m=[0.0, 0.0],
            science_target_xy_m=[100.0, 100.0],
            orbital_obstacle_present_in_corridor=True,
        )
        assert plan.cooperation_recommended is True
        assert plan.obstacles_discovered_count == 1
        assert plan.net_rover_distance_delta_m > 0.0
        assert plan.refined_rover_uncertainty_pct < plan.baseline_rover_uncertainty_pct
        assert plan.net_mission_energy_delta_wh > 0.0

    def test_18_multi_aircraft_4d_corridor_deconfliction(self):
        """Verifies multi-aircraft 4D corridor reservation and conflict detection."""
        fleet_intel = MarsAerialFleetIntelligence()
        ok1, msg1, c1 = fleet_intel.request_flight_corridor("AERO-01", [[0,0,15], [50,50,15]], 0.0, 60.0)
        assert ok1 is True

        # Second aircraft requests overlapping corridor in space and time
        ok2, msg2, c2 = fleet_intel.request_flight_corridor("AERO-02", [[0,0,15], [50,50,15]], 10.0, 50.0)
        assert ok2 is False
        assert "CONFLICT" in msg2

    def test_19_scenario_01_crater_reveal_six_stages(self):
        """Verifies complete execution of Flagship Scenario 01 across all 6 stages."""
        engine = MarsAerialScenarioEngine()
        result = engine.run_scenario("SCENARIO_01")
        assert result.success is True
        assert result.total_stages == 6
        assert len(result.stages) == 6
        assert result.stages[0].stage_name == "Rover Standstill at Crater Rim"
        assert result.stages[2].stage_name == "Aerial Scout Mapping & Boulder Discovery"
        assert result.stages[5].stage_name == "Rover Arrival & Synchronized Telemetry"
        assert result.metrics["boulders_discovered"] == 14
        assert result.metrics["rover_distance_saved_m"] > 30.0

    def test_20_api_contract_schema_validation(self):
        """Verifies that the /api/aerial/status response passes Draft 2020-12 schema validation."""
        from marswalk.api.service import aerial_status_api
        status = aerial_status_api()
        # validate_contract raises exception if invalid
        validate_contract(status, "aerial-corps")
        assert status["mission_id"] == "ATLAS-AERIAL-JEZERO-CORPS"
        assert len(status["aircraft_fleet"]) == 3
        assert "system_disclaimer" in status
