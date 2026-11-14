import sys

patch_code = '''

# =====================================================================
# MILESTONE 13P: ATLAS AERIAL CORPS SERVICE APIS
# =====================================================================

_GLOBAL_AERIAL_ENGINE = None

def get_aerial_engine():
    global _GLOBAL_AERIAL_ENGINE
    if _GLOBAL_AERIAL_ENGINE is None:
        from marswalk.core.mars_aerial_scenario_engine import MarsAerialScenarioEngine
        _GLOBAL_AERIAL_ENGINE = MarsAerialScenarioEngine()
    return _GLOBAL_AERIAL_ENGINE


def aerial_status_api() -> Dict[str, Any]:
    """
    GET /api/aerial/status
    Returns current multi-aircraft fleet telemetry, atmospheric state,
    active flight plans, science observations, and cooperative plans.
    """
    eng = get_aerial_engine()
    from marswalk.core.mars_rotor_aerodynamics import compute_atmospheric_properties
    atmos = compute_atmospheric_properties()

    fleet_dicts = [ac.to_dict() for ac in eng.fleet_mgr.list_fleet()]
    obs_dicts = [obs.to_dict() for obs in eng.science_engine.get_all_observations()]

    res = {
        "mission_id": "ATLAS-AERIAL-JEZERO-CORPS",
        "timestamp_sol": 1342.42,
        "aircraft_fleet": fleet_dicts,
        "atmospheric_state": atmos.to_dict(),
        "active_flight_plans": [],
        "science_observations": obs_dicts,
        "cooperative_plans": [],
        "system_disclaimer": "All planetary flight models, rotor aerodynamics, aerial navigation corridors, and multi-rotorcraft fleet coordination are simulated for robotic mission research and are not flight-certified for human astronaut operations.",
    }
    validate_contract(res, "aerial-corps")
    return res


def aerial_fleet_list_api() -> List[Dict[str, Any]]:
    """
    GET /api/aerial/fleet
    Returns the list of all registered aircraft in the fleet.
    """
    eng = get_aerial_engine()
    return [ac.to_dict() for ac in eng.fleet_mgr.list_fleet()]


def aerial_aircraft_create_api(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST /api/aerial/fleet/create
    Registers a new aircraft platform in the fleet.
    """
    eng = get_aerial_engine()
    from marswalk.core.mars_aircraft_fleet import AircraftProfile
    profile_str = body.get("profile", "SCIENCE_SCOUT")
    profile = AircraftProfile(profile_str) if profile_str in [p.value for p in AircraftProfile] else AircraftProfile.SCIENCE_SCOUT
    aircraft_id = body.get("aircraft_id")
    pos = body.get("initial_position_m", [0.0, 0.0, 0.0])
    payload = body.get("payload_mass_kg")
    paired_rover = body.get("paired_rover_id")

    ac = eng.fleet_mgr.create_aircraft(
        profile=profile,
        aircraft_id=aircraft_id,
        initial_position_m=pos,
        payload_mass_kg=payload,
        paired_rover_id=paired_rover,
    )
    return ac.to_dict()


def aerial_performance_evaluate_api(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST /api/aerial/performance/evaluate
    Evaluates the physical flight performance envelope for an aircraft profile.
    """
    eng = get_aerial_engine()
    from marswalk.core.mars_aircraft_fleet import AircraftProfile, AIRCRAFT_SPEC_CATALOG
    from marswalk.core.mars_rotor_aerodynamics import compute_atmospheric_properties
    from marswalk.core.mars_aircraft_performance import ModelingFidelityLevel

    profile_str = body.get("profile", "LIGHT_SCOUT")
    profile = AircraftProfile(profile_str) if profile_str in [p.value for p in AircraftProfile] else AircraftProfile.LIGHT_SCOUT
    spec = AIRCRAFT_SPEC_CATALOG[profile]

    pressure_pa = float(body.get("pressure_pa", 610.0))
    temperature_k = float(body.get("temperature_k", 215.0))
    atmos = compute_atmospheric_properties(pressure_pa=pressure_pa, temperature_k=temperature_k)

    payload_kg = float(body.get("payload_mass_kg", spec.nominal_payload_kg))
    env = eng.perf_engine.evaluate_envelope(
        specification=spec,
        payload_mass_kg=payload_kg,
        atmosphere=atmos,
        fidelity_level=ModelingFidelityLevel.LEVEL_1_SCREENING,
    )
    return env.to_dict()


def aerial_mission_plan_api(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST /api/aerial/mission/plan
    Plans a 3D terrain-cleared flight corridor between origin and destination.
    """
    eng = get_aerial_engine()
    plan_id = body.get("plan_id", "PLAN-AERO-001")
    aircraft_id = body.get("aircraft_id", "AERO-INGENUITY-01")
    origin = body.get("origin_xy_m", [0.0, 0.0])
    target = body.get("target_xy_m", [80.0, 95.0])
    alt = float(body.get("cruise_altitude_agl_m", 15.0))
    speed = float(body.get("cruise_speed_m_s", 7.0))

    ac = eng.fleet_mgr.get_aircraft(aircraft_id)
    batt_wh = ac.specification.battery_capacity_wh if ac else 35.0
    soc = ac.battery_soc_pct if ac else 100.0

    plan = eng.nav_engine.plan_reconnaissance_corridor(
        plan_id=plan_id,
        aircraft_id=aircraft_id,
        origin_xy_m=origin,
        target_xy_m=target,
        cruise_altitude_agl_m=alt,
        cruise_speed_m_s=speed,
        battery_capacity_wh=batt_wh,
        initial_soc_pct=soc,
    )
    return plan.to_dict()


def aerial_rover_cooperation_plan_api(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST /api/aerial/rover-cooperation/plan
    Synthesizes and quantifies a joint rover-aircraft reconnaissance mission.
    """
    eng = get_aerial_engine()
    rover_id = body.get("rover_id", "PERSEVERANCE_01")
    aircraft_id = body.get("aircraft_id", "AERO-INGENUITY-01")
    target_region = body.get("target_region_name", "Jezero Delta Front")
    rover_xy = body.get("rover_current_xy_m", [0.0, 0.0])
    target_xy = body.get("science_target_xy_m", [80.0, 95.0])
    has_obstacle = bool(body.get("orbital_obstacle_present_in_corridor", True))

    plan = eng.coordinator.plan_joint_reconnaissance(
        rover_id=rover_id,
        aircraft_id=aircraft_id,
        target_region_name=target_region,
        rover_current_xy_m=rover_xy,
        science_target_xy_m=target_xy,
        orbital_obstacle_present_in_corridor=has_obstacle,
    )
    return plan.to_dict()


def aerial_scenarios_list_api() -> List[Dict[str, Any]]:
    """
    GET /api/aerial/scenarios
    Lists the 10 reproducible planetary aerial exploration scenarios.
    """
    eng = get_aerial_engine()
    return eng.list_scenarios()


def aerial_scenario_run_api(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST /api/aerial/scenarios/run
    Executes a planetary aerial exploration scenario deterministically.
    """
    eng = get_aerial_engine()
    scenario_id = body.get("scenario_id", "SCENARIO_01")
    res = eng.run_scenario(scenario_id)
    return res.to_dict()


def aerial_observations_list_api() -> List[Dict[str, Any]]:
    """
    GET /api/aerial/observations
    Returns the log of scientific observations collected by aircraft.
    """
    eng = get_aerial_engine()
    return [obs.to_dict() for obs in eng.science_engine.get_all_observations()]


def aerial_reset_api() -> Dict[str, Any]:
    """
    POST /api/aerial/reset
    Resets the aerial corps fleet, scenarios, and science engine.
    """
    global _GLOBAL_AERIAL_ENGINE
    from marswalk.core.mars_aerial_scenario_engine import MarsAerialScenarioEngine
    _GLOBAL_AERIAL_ENGINE = MarsAerialScenarioEngine()
    return aerial_status_api()
'''

with open("src/marswalk/api/service.py", "a", encoding="utf-8") as f:
    f.write(patch_code)
print("Successfully patched service.py with Aerial Corps APIs!")
