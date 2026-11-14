"""
MarsWalk 2.0 / Project Atlas — Milestone 13P: Planetary Aircraft Fleet Architecture
==================================================================================
Defines the configurable multi-aircraft fleet data models and profiles:
- LIGHT_SCOUT: Ingenuity-inspired flight tech demonstrator (1.8 kg, short-range scouting).
- SCIENCE_SCOUT: Configurable scientific payload rotorcraft (4.5 kg, visible/NIR/atmosphere).
- SCIENCE_MAPPER: Conceptual heavy reconnaissance platform (18.5 kg, GPR radar/multispectral).

Enforces:
- Strict unit specifications, source provenance, and configuration validity.
- Ground truth spatial states (x, y, z, roll, pitch, yaw) and flight modes.
- Battery State-of-Charge (SoC), thermal envelopes, and payload power accounting.
"""

from __future__ import annotations

import copy
import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from marswalk.core.mars_rotor_aerodynamics import (
    AtmosphericProperties,
    MarsRotorAerodynamics,
    RotorGeometry,
    compute_atmospheric_properties,
)


class AircraftProfile(str, Enum):
    LIGHT_SCOUT = "LIGHT_SCOUT"
    SCIENCE_SCOUT = "SCIENCE_SCOUT"
    SCIENCE_MAPPER = "SCIENCE_MAPPER"


class FlightMode(str, Enum):
    GROUND_STANDBY = "GROUND_STANDBY"
    ROTOR_SPINUP = "ROTOR_SPINUP"
    VERTICAL_TAKEOFF = "VERTICAL_TAKEOFF"
    HOVER = "HOVER"
    FORWARD_FLIGHT = "FORWARD_FLIGHT"
    TERRAIN_MAPPING = "TERRAIN_MAPPING"
    VERTICAL_DESCENT = "VERTICAL_DESCENT"
    TOUCHDOWN_SHUTDOWN = "TOUCHDOWN_SHUTDOWN"
    EMERGENCY_LANDING = "EMERGENCY_LANDING"
    SAFE_HOLD = "SAFE_HOLD"


class AircraftHealthState(str, Enum):
    NOMINAL = "NOMINAL"
    DEGRADED = "DEGRADED"
    CRITICAL_BATTERY = "CRITICAL_BATTERY"
    THERMAL_ALERT = "THERMAL_ALERT"
    COMM_LOSS = "COMM_LOSS"
    GROUNDED = "GROUNDED"


@dataclass
class AircraftSpecification:
    """Rigorous engineering specification of an aerial vehicle platform."""
    profile: AircraftProfile
    name: str
    description: str
    provenance: str
    dry_mass_kg: float
    max_payload_kg: float
    nominal_payload_kg: float
    rotor_geometry: RotorGeometry
    nominal_rpm: float
    max_rpm: float
    battery_capacity_wh: float
    nominal_voltage_v: float
    min_touchdown_reserve_pct: float = 20.0  # Hard floor for safe descent
    max_flight_speed_m_s: float = 10.0
    max_climb_rate_m_s: float = 3.0
    max_descent_rate_m_s: float = 2.0
    max_operational_altitude_agl_m: float = 25.0
    min_terrain_clearance_m: float = 8.0
    avionics_power_w: float = 15.0
    heater_power_w: float = 12.0
    operational_temp_range_c: Tuple[float, float] = (-40.0, 35.0)

    @property
    def max_takeoff_mass_kg(self) -> float:
        return self.dry_mass_kg + self.max_payload_kg

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile.value,
            "name": self.name,
            "description": self.description,
            "provenance": self.provenance,
            "dry_mass_kg": self.dry_mass_kg,
            "max_payload_kg": self.max_payload_kg,
            "nominal_payload_kg": self.nominal_payload_kg,
            "max_takeoff_mass_kg": self.max_takeoff_mass_kg,
            "rotor_type": self.rotor_geometry.rotor_type,
            "rotor_diameter_m": round(self.rotor_geometry.radius_m * 2.0, 3),
            "num_rotors": self.rotor_geometry.num_rotors,
            "total_blades": self.rotor_geometry.total_blade_count,
            "nominal_rpm": self.nominal_rpm,
            "max_rpm": self.max_rpm,
            "battery_capacity_wh": self.battery_capacity_wh,
            "min_touchdown_reserve_pct": self.min_touchdown_reserve_pct,
            "max_flight_speed_m_s": self.max_flight_speed_m_s,
            "max_operational_altitude_agl_m": self.max_operational_altitude_agl_m,
            "avionics_power_w": self.avionics_power_w,
        }


# =====================================================================
# THREE CONFIGURABLE REFERENCE AIRCRAFT SPECIFICATIONS
# =====================================================================

SPEC_LIGHT_SCOUT = AircraftSpecification(
    profile=AircraftProfile.LIGHT_SCOUT,
    name="Atlas Light Scout (Ingenuity Class)",
    description="Technology demonstrator profile inspired by NASA's Ingenuity Mars Helicopter. Optimized for short-range local scouting.",
    provenance="NASA/JPL Ingenuity Published Flight Parameters (Balaram et al., 2018)",
    dry_mass_kg=1.80,
    max_payload_kg=0.00,  # Tech demo carries no science payload
    nominal_payload_kg=0.00,
    rotor_geometry=RotorGeometry(
        rotor_type="COAXIAL_COUNTER_ROTATING",
        radius_m=0.605,  # 1.21 m diameter
        num_rotors=2,
        blades_per_rotor=2,
        mean_chord_m=0.080,
        profile_drag_cd0=0.035,
        induced_power_factor_kappa=1.20,
        equivalent_flat_plate_area_f_m2=0.022,
        motor_electrical_efficiency=0.82,
    ),
    nominal_rpm=2537.0,
    max_rpm=2800.0,
    battery_capacity_wh=35.0,  # 6x Sony VTC4 cells
    nominal_voltage_v=14.8,
    min_touchdown_reserve_pct=20.0,
    max_flight_speed_m_s=10.0,
    max_climb_rate_m_s=3.0,
    max_descent_rate_m_s=1.5,
    max_operational_altitude_agl_m=20.0,
    avionics_power_w=15.0,
)

SPEC_SCIENCE_SCOUT = AircraftSpecification(
    profile=AircraftProfile.SCIENCE_SCOUT,
    name="Atlas Science Scout (Research Class)",
    description="Mid-sized planetary research rotorcraft configured with dedicated visible and near-infrared multi-spectral imaging payloads.",
    provenance="NASA Mars Science Helicopter Concept Study (Grip et al., 2020)",
    dry_mass_kg=3.80,
    max_payload_kg=1.00,
    nominal_payload_kg=0.70,  # High-res camera + NIR + atmospheric sensors
    rotor_geometry=RotorGeometry(
        rotor_type="COAXIAL_COUNTER_ROTATING",
        radius_m=0.725,  # 1.45 m diameter
        num_rotors=2,
        blades_per_rotor=2,
        mean_chord_m=0.095,
        profile_drag_cd0=0.032,
        induced_power_factor_kappa=1.18,
        equivalent_flat_plate_area_f_m2=0.038,
        motor_electrical_efficiency=0.84,
    ),
    nominal_rpm=2350.0,
    max_rpm=2650.0,
    battery_capacity_wh=85.0,
    nominal_voltage_v=22.2,
    min_touchdown_reserve_pct=22.0,
    max_flight_speed_m_s=12.0,
    max_climb_rate_m_s=3.5,
    max_descent_rate_m_s=2.0,
    max_operational_altitude_agl_m=35.0,
    avionics_power_w=28.0,
)

SPEC_SCIENCE_MAPPER = AircraftSpecification(
    profile=AircraftProfile.SCIENCE_MAPPER,
    name="Atlas Science Mapper (SkyFall / Heavy Class)",
    description="Large conceptual planetary exploration rotorcraft designed for regional mapping and carrying synthetic Ground-Penetrating Radar.",
    provenance="Atlas Conceptual Planetary Aerial Vehicle (SkyFall analog research model)",
    dry_mass_kg=15.00,
    max_payload_kg=5.00,
    nominal_payload_kg=3.50,  # GPR transceiver + mapping gimbal + laser altimeter
    rotor_geometry=RotorGeometry(
        rotor_type="MULTI_ROTOR",  # Heavy hexarotor configuration
        radius_m=0.625,  # 6 rotors of 1.25 m diameter each
        num_rotors=6,
        blades_per_rotor=2,
        mean_chord_m=0.090,
        profile_drag_cd0=0.030,
        induced_power_factor_kappa=1.15,
        equivalent_flat_plate_area_f_m2=0.095,
        motor_electrical_efficiency=0.86,
    ),
    nominal_rpm=1950.0,
    max_rpm=2300.0,
    battery_capacity_wh=360.0,
    nominal_voltage_v=44.4,
    min_touchdown_reserve_pct=25.0,
    max_flight_speed_m_s=15.0,
    max_climb_rate_m_s=4.0,
    max_descent_rate_m_s=2.5,
    max_operational_altitude_agl_m=50.0,
    avionics_power_w=65.0,
)

AIRCRAFT_SPEC_CATALOG: Dict[AircraftProfile, AircraftSpecification] = {
    AircraftProfile.LIGHT_SCOUT: SPEC_LIGHT_SCOUT,
    AircraftProfile.SCIENCE_SCOUT: SPEC_SCIENCE_SCOUT,
    AircraftProfile.SCIENCE_MAPPER: SPEC_SCIENCE_MAPPER,
}


@dataclass
class AircraftState:
    """Dynamic operational state of a planetary aircraft."""
    aircraft_id: str
    specification: AircraftSpecification
    payload_mass_kg: float = 0.0
    position_xyz_m: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])  # x (East), y (North), z (Altitude AGL)
    velocity_xyz_m_s: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    attitude_rpy_deg: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])  # Roll, Pitch, Yaw
    flight_mode: FlightMode = FlightMode.GROUND_STANDBY
    health_state: AircraftHealthState = AircraftHealthState.NOMINAL
    battery_soc_pct: float = 100.0  # 0.0 to 100.0%
    battery_temp_c: float = 15.0
    current_rpm: float = 0.0
    power_draw_w: float = 0.0
    total_flight_time_s: float = 0.0
    total_distance_flown_m: float = 0.0
    assigned_mission_id: Optional[str] = None
    paired_rover_id: Optional[str] = None
    observation_count: int = 0

    @property
    def total_mass_kg(self) -> float:
        return self.specification.dry_mass_kg + self.payload_mass_kg

    @property
    def altitude_agl_m(self) -> float:
        return self.position_xyz_m[2]

    @property
    def is_airborne(self) -> bool:
        return self.flight_mode in [
            FlightMode.VERTICAL_TAKEOFF,
            FlightMode.HOVER,
            FlightMode.FORWARD_FLIGHT,
            FlightMode.TERRAIN_MAPPING,
            FlightMode.VERTICAL_DESCENT,
            FlightMode.EMERGENCY_LANDING,
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "aircraft_id": self.aircraft_id,
            "profile": self.specification.profile.value,
            "name": self.specification.name,
            "total_mass_kg": round(self.total_mass_kg, 2),
            "payload_mass_kg": round(self.payload_mass_kg, 2),
            "position_xyz_m": [round(c, 2) for c in self.position_xyz_m],
            "velocity_xyz_m_s": [round(v, 2) for v in self.velocity_xyz_m_s],
            "altitude_agl_m": round(self.altitude_agl_m, 2),
            "attitude_rpy_deg": [round(a, 1) for a in self.attitude_rpy_deg],
            "flight_mode": self.flight_mode.value,
            "health_state": self.health_state.value,
            "battery_soc_pct": round(self.battery_soc_pct, 1),
            "battery_temp_c": round(self.battery_temp_c, 1),
            "current_rpm": round(self.current_rpm, 1),
            "power_draw_w": round(self.power_draw_w, 1),
            "total_flight_time_s": round(self.total_flight_time_s, 1),
            "total_distance_flown_m": round(self.total_distance_flown_m, 1),
            "assigned_mission_id": self.assigned_mission_id,
            "paired_rover_id": self.paired_rover_id,
            "observation_count": self.observation_count,
        }


class MarsAircraftFleetManager:
    """Manages the lifecycle, registration, and state updates of all aircraft in the Atlas fleet."""

    def __init__(self):
        self._fleet: Dict[str, AircraftState] = {}
        self._aero_solver = MarsRotorAerodynamics()
        self._initialize_default_fleet()

    def _initialize_default_fleet(self) -> None:
        """Initializes default 3 reference aircraft co-located at Jezero base camp."""
        # 1. Ingenuity-class Light Scout
        self.create_aircraft(
            profile=AircraftProfile.LIGHT_SCOUT,
            aircraft_id="AERO-INGENUITY-01",
            initial_position_m=[0.0, 0.0, 0.0],
            paired_rover_id="PERSEVERANCE_01",
        )
        # 2. Science Scout
        self.create_aircraft(
            profile=AircraftProfile.SCIENCE_SCOUT,
            aircraft_id="AERO-SCOUT-02",
            initial_position_m=[25.0, 10.0, 0.0],
            paired_rover_id="PERSEVERANCE_01",
        )
        # 3. Heavy Science Mapper
        self.create_aircraft(
            profile=AircraftProfile.SCIENCE_MAPPER,
            aircraft_id="AERO-MAPPER-03",
            initial_position_m=[-30.0, 40.0, 0.0],
            paired_rover_id="CURIOSITY_02",
        )

    def create_aircraft(
        self,
        profile: AircraftProfile,
        aircraft_id: Optional[str] = None,
        initial_position_m: Optional[List[float]] = None,
        payload_mass_kg: Optional[float] = None,
        paired_rover_id: Optional[str] = None,
    ) -> AircraftState:
        spec = AIRCRAFT_SPEC_CATALOG.get(profile, SPEC_LIGHT_SCOUT)
        ac_id = aircraft_id or f"AERO-{profile.value}-{uuid.uuid4().hex[:6].upper()}"
        pos = initial_position_m or [0.0, 0.0, 0.0]
        actual_payload = payload_mass_kg if payload_mass_kg is not None else spec.nominal_payload_kg
        actual_payload = min(max(0.0, actual_payload), spec.max_payload_kg)

        state = AircraftState(
            aircraft_id=ac_id,
            specification=spec,
            payload_mass_kg=actual_payload,
            position_xyz_m=copy.deepcopy(pos),
            paired_rover_id=paired_rover_id,
        )
        self._fleet[ac_id] = state
        return state

    def get_aircraft(self, aircraft_id: str) -> Optional[AircraftState]:
        return self._fleet.get(aircraft_id)

    def list_fleet(self) -> List[AircraftState]:
        return list(self._fleet.values())

    def update_aircraft_telemetry(
        self,
        aircraft_id: str,
        flight_mode: Optional[FlightMode] = None,
        position_xyz_m: Optional[List[float]] = None,
        velocity_xyz_m_s: Optional[List[float]] = None,
        attitude_rpy_deg: Optional[List[float]] = None,
        battery_soc_pct: Optional[float] = None,
        power_draw_w: Optional[float] = None,
        dt_seconds: float = 0.0,
    ) -> Optional[AircraftState]:
        ac = self._fleet.get(aircraft_id)
        if not ac:
            return None

        if flight_mode is not None:
            ac.flight_mode = flight_mode
        if position_xyz_m is not None:
            ac.position_xyz_m = list(position_xyz_m)
        if velocity_xyz_m_s is not None:
            ac.velocity_xyz_m_s = list(velocity_xyz_m_s)
        if attitude_rpy_deg is not None:
            ac.attitude_rpy_deg = list(attitude_rpy_deg)
        if battery_soc_pct is not None:
            ac.battery_soc_pct = max(0.0, min(100.0, battery_soc_pct))
            if ac.battery_soc_pct <= ac.specification.min_touchdown_reserve_pct:
                ac.health_state = AircraftHealthState.CRITICAL_BATTERY
        if power_draw_w is not None:
            ac.power_draw_w = power_draw_w

        if dt_seconds > 0.0 and ac.is_airborne:
            ac.total_flight_time_s += dt_seconds
            speed = math.sqrt(sum(v ** 2 for v in ac.velocity_xyz_m_s))
            ac.total_distance_flown_m += speed * dt_seconds

        return ac

    def reset_fleet(self) -> None:
        self._fleet.clear()
        self._initialize_default_fleet()
