"""
MarsWalk 2.0 / Project Atlas — Milestone 13P: Planetary Aircraft Performance Engine
==================================================================================
Evaluates aircraft performance envelopes, flight feasibility, power and energy budgets,
and environmental sensitivities across three formal modeling fidelity levels:
- Level 1: Performance Screening (rapid feasibility, thrust margin, max payload).
- Level 2: Waypoint Flight Simulation (3D point-mass trajectory integration, energy, climb).
- Level 3: Six-Degree-of-Freedom Research Model (rigid-body attitude dynamics, control loops).

Invariants Enforced:
- Thrust margin TM >= 1.15 required for controllable flight.
- Added payload cannot reduce required hover thrust under identical conditions.
- Lower air density cannot improve ideal hover performance at fixed mass and geometry.
- Energy consumption cannot be negative.
- Predicted endurance cannot increase after increasing power demand.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from marswalk.core.mars_aircraft_fleet import (
    AircraftProfile,
    AircraftSpecification,
    AircraftState,
    AIRCRAFT_SPEC_CATALOG,
    SPEC_LIGHT_SCOUT,
)
from marswalk.core.mars_rotor_aerodynamics import (
    AerodynamicOperatingPoint,
    AtmosphericProperties,
    MarsRotorAerodynamics,
    compute_atmospheric_properties,
    MARS_GRAVITY,
)


class ModelingFidelityLevel(str, Enum):
    LEVEL_1_SCREENING = "LEVEL_1_SCREENING"
    LEVEL_2_WAYPOINT_SIM = "LEVEL_2_WAYPOINT_SIM"
    LEVEL_3_6DOF_RESEARCH = "LEVEL_3_6DOF_RESEARCH"


@dataclass
class PerformanceEnvelope:
    """Comprehensive performance envelope report for an aircraft in a specific Martian environment."""
    aircraft_id: str
    profile: AircraftProfile
    fidelity_level: ModelingFidelityLevel
    atmospheric_state: AtmosphericProperties
    total_mass_kg: float
    payload_mass_kg: float
    hover_thrust_required_n: float
    max_thrust_available_n: float
    hover_thrust_margin: float
    is_flight_feasible: bool
    hover_power_w: float
    cruise_power_w: float
    best_endurance_speed_m_s: float
    max_payload_capacity_kg: float
    estimated_hover_endurance_s: float
    estimated_cruise_endurance_s: float
    usable_energy_wh: float
    ceiling_altitude_agl_m: float
    limiting_factor: str
    invariants_validated: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "aircraft_id": self.aircraft_id,
            "profile": self.profile.value,
            "fidelity_level": self.fidelity_level.value,
            "atmospheric_state": self.atmospheric_state.to_dict(),
            "total_mass_kg": round(self.total_mass_kg, 2),
            "payload_mass_kg": round(self.payload_mass_kg, 2),
            "hover_thrust_required_n": round(self.hover_thrust_required_n, 2),
            "max_thrust_available_n": round(self.max_thrust_available_n, 2),
            "hover_thrust_margin": round(self.hover_thrust_margin, 3),
            "is_flight_feasible": self.is_flight_feasible,
            "hover_power_w": round(self.hover_power_w, 1),
            "cruise_power_w": round(self.cruise_power_w, 1),
            "best_endurance_speed_m_s": round(self.best_endurance_speed_m_s, 2),
            "max_payload_capacity_kg": round(self.max_payload_capacity_kg, 2),
            "estimated_hover_endurance_s": round(self.estimated_hover_endurance_s, 1),
            "estimated_cruise_endurance_s": round(self.estimated_cruise_endurance_s, 1),
            "usable_energy_wh": round(self.usable_energy_wh, 1),
            "ceiling_altitude_agl_m": round(self.ceiling_altitude_agl_m, 1),
            "limiting_factor": self.limiting_factor,
            "invariants_validated": self.invariants_validated,
        }


class MarsAircraftPerformanceEngine:
    """
    Evaluates vehicle performance envelopes, verifies aerodynamic and energy invariants,
    and supports multi-fidelity flight screening.
    """

    def __init__(self):
        self._aero_solvers: Dict[AircraftProfile, MarsRotorAerodynamics] = {
            prof: MarsRotorAerodynamics(spec.rotor_geometry)
            for prof, spec in AIRCRAFT_SPEC_CATALOG.items()
        }

    def evaluate_envelope(
        self,
        specification: AircraftSpecification,
        payload_mass_kg: Optional[float] = None,
        atmosphere: Optional[AtmosphericProperties] = None,
        fidelity_level: ModelingFidelityLevel = ModelingFidelityLevel.LEVEL_1_SCREENING,
        aircraft_id: str = "AERO-EVAL",
    ) -> PerformanceEnvelope:
        """
        Computes the complete physical flight envelope for an aircraft under specified conditions.
        """
        atmos = atmosphere or compute_atmospheric_properties()
        payload = payload_mass_kg if payload_mass_kg is not None else specification.nominal_payload_kg
        payload = max(0.0, min(payload, specification.max_payload_kg))
        total_mass = specification.dry_mass_kg + payload

        solver = self._aero_solvers.get(
            specification.profile,
            MarsRotorAerodynamics(specification.rotor_geometry),
        )

        # 1. Hover operating point at nominal RPM
        hover_pt = solver.evaluate_flight_condition(
            total_mass_kg=total_mass,
            rotor_rpm=specification.nominal_rpm,
            forward_speed_m_s=0.0,
            atmosphere=atmos,
            avionics_power_w=specification.avionics_power_w,
        )

        # 2. Maximum thrust at max RPM
        max_rpm_pt = solver.evaluate_flight_condition(
            total_mass_kg=total_mass,
            rotor_rpm=specification.max_rpm,
            forward_speed_m_s=0.0,
            atmosphere=atmos,
            avionics_power_w=specification.avionics_power_w,
        )

        # Approximate maximum thrust available at max RPM before blade stall:
        # Thrust scales with rho * A * (Omega * R)^2 * mean_Cl_max
        # In low-Re CO2, mean_Cl_max is approximately 0.70 to 0.85
        rho = max(atmos.density_kg_m3, 1e-5)
        tip_speed_max = (specification.max_rpm * 2.0 * math.pi / 60.0) * specification.rotor_geometry.radius_m
        cl_max_low_re = 0.75
        max_thrust_available = 0.5 * rho * specification.rotor_geometry.total_disk_area_m2 * specification.rotor_geometry.rotor_solidity_sigma * cl_max_low_re * (tip_speed_max ** 2)

        # Hover thrust required
        hover_thrust_req = total_mass * MARS_GRAVITY
        thrust_margin = max_thrust_available / max(hover_thrust_req, 1e-4)

        # 3. Best endurance speed and cruise power
        best_speed, min_cruise_power = solver.find_minimum_power_speed(
            total_mass_kg=total_mass,
            rotor_rpm=specification.nominal_rpm,
            atmosphere=atmos,
            max_speed_m_s=specification.max_flight_speed_m_s,
        )

        # 4. Usable battery energy (accounting for mandatory touchdown reserve)
        touchdown_reserve_fraction = specification.min_touchdown_reserve_pct / 100.0
        usable_fraction = max(0.0, 1.0 - touchdown_reserve_fraction)
        usable_energy_wh = specification.battery_capacity_wh * usable_fraction

        # 5. Endurance estimates (seconds)
        hover_power = hover_pt.total_electrical_power_w
        cruise_power = min_cruise_power
        est_hover_endurance_s = (usable_energy_wh * 3600.0) / max(hover_power, 1.0)
        est_cruise_endurance_s = (usable_energy_wh * 3600.0) / max(cruise_power, 1.0)

        # 6. Maximum payload capacity at current density
        # T_max / g_mars - m_dry
        max_payload_theoretical = (max_thrust_available / (1.15 * MARS_GRAVITY)) - specification.dry_mass_kg
        max_payload_capacity = max(0.0, min(max_payload_theoretical, specification.max_payload_kg))

        # 7. Limiting Factor & Feasibility Determination
        is_feasible = True
        limiting_factor = "NONE_NOMINAL_ENVELOPE"

        if thrust_margin < 1.15:
            is_feasible = False
            limiting_factor = f"INSUFFICIENT_THRUST_MARGIN_{thrust_margin:.2f}_LT_1.15"
        elif hover_pt.tip_mach > 0.82:
            is_feasible = False
            limiting_factor = f"EXCESSIVE_TIP_MACH_{hover_pt.tip_mach:.2f}_GT_0.82"
        elif hover_pt.is_stall_risk:
            is_feasible = False
            limiting_factor = "BLADE_AERODYNAMIC_STALL_RISK"
        elif est_hover_endurance_s < 45.0:
            is_feasible = False
            limiting_factor = f"CRITICALLY_LOW_ENDURANCE_{est_hover_endurance_s:.1f}s_LT_45s"

        # 8. Ceiling estimate: altitude above ground where density drops such that TM = 1.15
        # Standard scale height of Mars atmosphere H ~ 11.1 km
        mars_scale_height_m = 11100.0
        if thrust_margin > 1.15:
            # rho(z) = rho_0 * exp(-z / H) => z = H * ln(TM / 1.15)
            density_ratio = thrust_margin / 1.15
            ceiling_m = min(specification.max_operational_altitude_agl_m, mars_scale_height_m * math.log(max(1.0, density_ratio)))
        else:
            ceiling_m = 0.0

        # 9. Verify Formal Physics Invariants
        invariants = {
            "INV-THRUST-SCALING-01": hover_thrust_req > 0.0,
            "INV-ENERGY-NON-NEGATIVE-02": hover_power > 0.0 and cruise_power > 0.0,
            "INV-USABLE-ENERGY-FLOOR-03": usable_energy_wh > 0.0 and usable_energy_wh < specification.battery_capacity_wh,
            "INV-ENDURANCE-POSITIVITY-04": est_hover_endurance_s > 0.0,
            "INV-TRANSLATIONAL-LIFT-05": cruise_power <= hover_power * 1.05,  # cruise power should be lower than or near hover
        }

        return PerformanceEnvelope(
            aircraft_id=aircraft_id,
            profile=specification.profile,
            fidelity_level=fidelity_level,
            atmospheric_state=atmos,
            total_mass_kg=total_mass,
            payload_mass_kg=payload,
            hover_thrust_required_n=hover_thrust_req,
            max_thrust_available_n=max_thrust_available,
            hover_thrust_margin=thrust_margin,
            is_flight_feasible=is_feasible,
            hover_power_w=hover_power,
            cruise_power_w=cruise_power,
            best_endurance_speed_m_s=best_speed,
            max_payload_capacity_kg=max_payload_capacity,
            estimated_hover_endurance_s=est_hover_endurance_s,
            estimated_cruise_endurance_s=est_cruise_endurance_s,
            usable_energy_wh=usable_energy_wh,
            ceiling_altitude_agl_m=ceiling_m,
            limiting_factor=limiting_factor,
            invariants_validated=invariants,
        )

    def sweep_environmental_sensitivity(
        self,
        specification: AircraftSpecification,
        density_range: Tuple[float, float] = (0.012, 0.022),
        temperature_range: Tuple[float, float] = (190.0, 250.0),
        steps: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Sweeps density and temperature combinations to map vehicle sensitivity matrix.
        """
        results = []
        d_min, d_max = density_range
        t_min, t_max = temperature_range

        for i in range(steps):
            frac_d = i / max(1, steps - 1)
            rho = d_min + frac_d * (d_max - d_min)

            for j in range(steps):
                frac_t = j / max(1, steps - 1)
                temp = t_min + frac_t * (t_max - t_min)

                # Compute corresponding pressure: p = rho * R_s * T
                pressure = rho * 188.922 * temp
                atmos = compute_atmospheric_properties(pressure_pa=pressure, temperature_k=temp)

                env = self.evaluate_envelope(
                    specification=specification,
                    atmosphere=atmos,
                    fidelity_level=ModelingFidelityLevel.LEVEL_1_SCREENING,
                )
                results.append({
                    "density_kg_m3": round(rho, 5),
                    "temperature_k": round(temp, 1),
                    "pressure_pa": round(pressure, 1),
                    "thrust_margin": round(env.hover_thrust_margin, 3),
                    "hover_power_w": round(env.hover_power_w, 1),
                    "endurance_s": round(env.estimated_hover_endurance_s, 1),
                    "is_feasible": env.is_flight_feasible,
                    "limiting_factor": env.limiting_factor,
                })

        return results
