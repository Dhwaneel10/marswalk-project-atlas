"""
MarsWalk 2.0 / Project Atlas — Milestone 13P: Planetary Rotor Aerodynamics Engine
================================================================================
Mathematical models for thin-atmosphere rotorcraft aerodynamics on Mars:
- Equation of state for CO2 atmosphere (density, speed of sound, dynamic viscosity).
- Low-Reynolds-number, high-Mach-number aerodynamic regime analysis.
- Momentum Theory and Blade Element Momentum (BEM) formulation.
- Induced, profile, and parasite power calculations for hover and forward flight.
- Rotor disk loading, thrust margins, and blade tip velocity metrics.

Scientific Provenance & Citations:
- NASA/JPL Ingenuity Mars Helicopter publications (Balaram et al., 2018, 2021).
- NASA Technical Reports: Young et al., "Vertical Lift Planetary Aerial Vehicles".
- Leishman, J. Gordon, "Principles of Helicopter Aerodynamics", Cambridge Univ. Press.
- Mars Atmosphere Model: CO2 molar mass M = 44.01 g/mol, gamma = 1.29, Sutherland viscosity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Universal Physical Constants
UNIVERSAL_GAS_CONSTANT_RU = 8314.4626  # J / (kmol * K)
SPEED_OF_LIGHT = 299792458.0  # m / s
MARS_GRAVITY = 3.721  # m / s^2

# Martian Atmospheric Constants (CO2 Dominated ~95.3%)
MOLAR_MASS_CO2 = 44.01  # kg / kmol (g / mol)
SPECIFIC_GAS_CONSTANT_CO2 = UNIVERSAL_GAS_CONSTANT_RU / MOLAR_MASS_CO2  # 188.922 J / (kg * K)
RATIO_SPECIFIC_HEATS_GAMMA = 1.29  # Dimensionless for CO2 at Martian temperatures
SUTHERLAND_T0 = 273.15  # Reference temperature for Sutherland's law (K)
SUTHERLAND_MU0 = 1.37e-5  # Dynamic viscosity of CO2 at T0 (Pa * s)
SUTHERLAND_S = 222.0  # Sutherland constant for CO2 (K)

# Default Jezero Surface Baseline Reference
DEFAULT_JEZERO_PRESSURE_PA = 610.0  # Pa (~6.1 mbar)
DEFAULT_JEZERO_TEMPERATURE_K = 215.0  # K (~-58.15 C)


@dataclass(frozen=True)
class AtmosphericProperties:
    """Atmospheric state properties derived from local temperature and pressure."""
    pressure_pa: float
    temperature_k: float
    density_kg_m3: float
    speed_of_sound_m_s: float
    dynamic_viscosity_pa_s: float
    kinematic_viscosity_m2_s: float
    is_valid: bool
    provenance: str = "Mars CO2 Equation of State (NASA JPL Standard)"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pressure_pa": round(self.pressure_pa, 2),
            "temperature_k": round(self.temperature_k, 2),
            "density_kg_m3": round(self.density_kg_m3, 5),
            "speed_of_sound_m_s": round(self.speed_of_sound_m_s, 2),
            "dynamic_viscosity_pa_s": f"{self.dynamic_viscosity_pa_s:.3e}",
            "kinematic_viscosity_m2_s": f"{self.kinematic_viscosity_m2_s:.3e}",
            "is_valid": self.is_valid,
            "provenance": self.provenance,
        }


def compute_atmospheric_properties(
    pressure_pa: float = DEFAULT_JEZERO_PRESSURE_PA,
    temperature_k: float = DEFAULT_JEZERO_TEMPERATURE_K,
) -> AtmosphericProperties:
    """
    Computes Martian atmospheric properties from local pressure and temperature.
    Equation of State: rho = (p * M) / (R_u * T) = p / (R_s * T)
    Speed of Sound: a = sqrt(gamma * R_s * T)
    Dynamic Viscosity (Sutherland's Law for CO2):
      mu = mu_0 * ((T_0 + S) / (T + S)) * (T / T_0)^(3/2)
    """
    if pressure_pa <= 0.0 or temperature_k <= 0.0:
        return AtmosphericProperties(
            pressure_pa=pressure_pa,
            temperature_k=temperature_k,
            density_kg_m3=0.0,
            speed_of_sound_m_s=0.0,
            dynamic_viscosity_pa_s=0.0,
            kinematic_viscosity_m2_s=0.0,
            is_valid=False,
            provenance="INVALID_STATE",
        )

    # Ideal Gas Law for CO2
    density = pressure_pa / (SPECIFIC_GAS_CONSTANT_CO2 * temperature_k)

    # Speed of Sound in CO2
    speed_of_sound = math.sqrt(RATIO_SPECIFIC_HEATS_GAMMA * SPECIFIC_GAS_CONSTANT_CO2 * temperature_k)

    # Sutherland's Law for Dynamic Viscosity of CO2
    temp_ratio = temperature_k / SUTHERLAND_T0
    viscosity = SUTHERLAND_MU0 * ((SUTHERLAND_T0 + SUTHERLAND_S) / (temperature_k + SUTHERLAND_S)) * (temp_ratio ** 1.5)

    # Kinematic Viscosity
    kinematic_viscosity = viscosity / density if density > 0.0 else 0.0

    return AtmosphericProperties(
        pressure_pa=pressure_pa,
        temperature_k=temperature_k,
        density_kg_m3=density,
        speed_of_sound_m_s=speed_of_sound,
        dynamic_viscosity_pa_s=viscosity,
        kinematic_viscosity_m2_s=kinematic_viscosity,
        is_valid=True,
    )


@dataclass
class RotorGeometry:
    """Geometric and aerodynamic configuration of a planetary rotor system."""
    rotor_type: str = "COAXIAL_COUNTER_ROTATING"  # COAXIAL_COUNTER_ROTATING, MULTI_ROTOR, SINGLE_ROTOR
    radius_m: float = 0.605  # Ingenuity class radius (diameter 1.21 m)
    num_rotors: int = 2  # 2 for coaxial counter-rotating
    blades_per_rotor: int = 2  # 2 blades per rotor (4 total blades)
    mean_chord_m: float = 0.080  # Mean blade chord (m)
    profile_drag_cd0: float = 0.035  # Mean profile drag coeff in low-Re regime
    induced_power_factor_kappa: float = 1.20  # Inflow & coaxial interference factor
    equivalent_flat_plate_area_f_m2: float = 0.022  # Fuselage & mast parasite area (m^2)
    motor_electrical_efficiency: float = 0.82  # Brushless DC motor + ESC efficiency

    @property
    def disk_area_m2(self) -> float:
        """Single rotor disk area A = pi * R^2."""
        return math.pi * (self.radius_m ** 2)

    @property
    def total_disk_area_m2(self) -> float:
        """Effective disk area depending on rotor configuration."""
        if self.rotor_type == "COAXIAL_COUNTER_ROTATING":
            # Coaxial rotors share swept area with ~10-15% overlap loss
            return self.disk_area_m2
        return self.disk_area_m2 * self.num_rotors

    @property
    def total_blade_count(self) -> int:
        return self.num_rotors * self.blades_per_rotor

    @property
    def rotor_solidity_sigma(self) -> float:
        """Rotor solidity: ratio of total blade planform area to disk area."""
        return (self.total_blade_count * self.mean_chord_m) / (math.pi * self.radius_m)


@dataclass
class AerodynamicOperatingPoint:
    """Evaluated aerodynamic parameters at a specific flight condition."""
    rotor_rpm: float
    forward_speed_m_s: float
    climb_rate_m_s: float
    tip_velocity_m_s: float
    tip_mach: float
    reynolds_number: float
    thrust_n: float
    disk_loading_n_m2: float
    ideal_induced_velocity_m_s: float
    induced_power_w: float
    profile_power_w: float
    parasite_power_w: float
    climb_power_w: float
    total_aerodynamic_power_w: float
    total_electrical_power_w: float
    is_compressibility_penalized: bool
    is_stall_risk: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rotor_rpm": round(self.rotor_rpm, 1),
            "forward_speed_m_s": round(self.forward_speed_m_s, 2),
            "climb_rate_m_s": round(self.climb_rate_m_s, 2),
            "tip_velocity_m_s": round(self.tip_velocity_m_s, 2),
            "tip_mach": round(self.tip_mach, 3),
            "reynolds_number": int(round(self.reynolds_number)),
            "thrust_n": round(self.thrust_n, 2),
            "disk_loading_n_m2": round(self.disk_loading_n_m2, 2),
            "ideal_induced_velocity_m_s": round(self.ideal_induced_velocity_m_s, 2),
            "induced_power_w": round(self.induced_power_w, 1),
            "profile_power_w": round(self.profile_power_w, 1),
            "parasite_power_w": round(self.parasite_power_w, 1),
            "climb_power_w": round(self.climb_power_w, 1),
            "total_aerodynamic_power_w": round(self.total_aerodynamic_power_w, 1),
            "total_electrical_power_w": round(self.total_electrical_power_w, 1),
            "is_compressibility_penalized": self.is_compressibility_penalized,
            "is_stall_risk": self.is_stall_risk,
        }


class MarsRotorAerodynamics:
    """
    Rotor aerodynamics solver for Martian rotorcraft.
    Implements Classical Momentum Theory with Blade Element Momentum corrections,
    compressibility drag rise at high tip Mach numbers, and low-Reynolds drag adjustments.
    """

    def __init__(self, geometry: Optional[RotorGeometry] = None):
        self.geom = geometry or RotorGeometry()

    def evaluate_flight_condition(
        self,
        total_mass_kg: float,
        rotor_rpm: float,
        forward_speed_m_s: float = 0.0,
        climb_rate_m_s: float = 0.0,
        atmosphere: Optional[AtmosphericProperties] = None,
        avionics_power_w: float = 15.0,
    ) -> AerodynamicOperatingPoint:
        """
        Evaluates the aerodynamic operating point, power required, Mach number,
        and Reynolds number for a given vehicle mass and flight condition.
        """
        atmos = atmosphere or compute_atmospheric_properties()
        rho = max(atmos.density_kg_m3, 1e-6)
        a_sound = max(atmos.speed_of_sound_m_s, 1.0)
        mu = max(atmos.dynamic_viscosity_pa_s, 1e-7)

        # 1. Kinematics of Rotor Tip and Advancing Blade
        omega = (rotor_rpm * 2.0 * math.pi) / 60.0  # rad/s
        v_tip = omega * self.geom.radius_m  # m/s
        tip_mach = v_tip / a_sound
        # Advancing blade tip speed in forward flight: V_adv = V_tip + V_forward
        v_adv_tip = v_tip + forward_speed_m_s
        adv_tip_mach = v_adv_tip / a_sound

        # 2. Reynolds Number at 75% Blade Radius (Representative Aerodynamic Station)
        v_75 = 0.75 * v_tip
        reynolds = (rho * v_75 * self.geom.mean_chord_m) / mu

        # 3. Thrust Requirement
        # In steady hover/climb: T = m * (g + a_climb)
        thrust_req = total_mass_kg * MARS_GRAVITY
        if climb_rate_m_s > 0.0:
            thrust_req += total_mass_kg * (climb_rate_m_s * 0.05)

        disk_loading = thrust_req / self.geom.total_disk_area_m2

        # 4. Momentum Theory: Ideal Induced Velocity (Hover / Forward Flight)
        v_hover_ideal = math.sqrt(thrust_req / (2.0 * rho * self.geom.total_disk_area_m2))

        # Forward flight translational lift correction (Glauert's formula):
        v_i = v_hover_ideal
        if forward_speed_m_s > 0.1:
            for _ in range(5):
                denom = math.sqrt((forward_speed_m_s ** 2) + (v_i ** 2))
                v_i = (v_hover_ideal ** 2) / max(denom, 1e-4)

        # 5. Induced Power (with non-uniform inflow & coaxial interference kappa)
        p_induced = self.geom.induced_power_factor_kappa * thrust_req * v_i

        # 6. Profile Power with Low-Re, Advancing Blade Mach, and Advance Ratio Corrections
        cd0_effective = self.geom.profile_drag_cd0

        # Low Reynolds number penalty: when Re < 20,000, laminar separation bubbles increase drag
        if reynolds < 20000.0:
            re_penalty = 1.0 + 0.5 * ((20000.0 - reynolds) / 20000.0)
            cd0_effective *= re_penalty

        # Compressibility drag rise on advancing blade:
        # On Mars, advancing blade reaches transonic speeds at modest forward velocities
        is_compressibility_penalized = False
        if adv_tip_mach > 0.72:
            is_compressibility_penalized = True
            mach_excess = adv_tip_mach - 0.72
            cd0_effective += 0.5 * mach_excess + 5.0 * (mach_excess ** 2)

        # Total profile power for all rotors
        advance_ratio_mu = forward_speed_m_s / max(v_tip, 1.0)
        p_profile_hover = (1.0 / 8.0) * rho * self.geom.rotor_solidity_sigma * cd0_effective * self.geom.total_disk_area_m2 * (v_tip ** 3)
        p_profile = p_profile_hover * (1.0 + 4.65 * (advance_ratio_mu ** 2))

        # 7. Parasite & Rotor Edgewise Drag Power
        rotor_drag_area = 0.12 * self.geom.total_disk_area_m2 * self.geom.rotor_solidity_sigma
        total_drag_area = self.geom.equivalent_flat_plate_area_f_m2 + rotor_drag_area
        p_parasite = 0.5 * rho * (forward_speed_m_s ** 3) * total_drag_area

        # 8. Climb Power (Work done against gravity)
        p_climb = max(0.0, thrust_req * climb_rate_m_s)

        # 9. Total Aerodynamic and Electrical Power
        p_aero_total = p_induced + p_profile + p_parasite + p_climb
        p_electrical = (p_aero_total / max(self.geom.motor_electrical_efficiency, 0.1)) + avionics_power_w

        # Stall risk check: excessive blade collective pitch required when density is critically low
        is_stall_risk = (disk_loading / max(rho, 1e-5)) > 1500.0 or tip_mach > 0.85

        return AerodynamicOperatingPoint(
            rotor_rpm=rotor_rpm,
            forward_speed_m_s=forward_speed_m_s,
            climb_rate_m_s=climb_rate_m_s,
            tip_velocity_m_s=v_tip,
            tip_mach=tip_mach,
            reynolds_number=reynolds,
            thrust_n=thrust_req,
            disk_loading_n_m2=disk_loading,
            ideal_induced_velocity_m_s=v_i,
            induced_power_w=p_induced,
            profile_power_w=p_profile,
            parasite_power_w=p_parasite,
            climb_power_w=p_climb,
            total_aerodynamic_power_w=p_aero_total,
            total_electrical_power_w=p_electrical,
            is_compressibility_penalized=is_compressibility_penalized,
            is_stall_risk=is_stall_risk,
        )

    def find_minimum_power_speed(
        self,
        total_mass_kg: float,
        rotor_rpm: float,
        atmosphere: Optional[AtmosphericProperties] = None,
        max_speed_m_s: float = 20.0,
    ) -> Tuple[float, float]:
        """
        Calculates the best-endurance forward flight speed (V_be) where total power is minimized.
        Due to translational lift, forward flight requires less power than pure hover until parasite drag dominates.
        Returns: (best_endurance_speed_m_s, minimum_power_w)
        """
        best_speed = 0.0
        min_power = float("inf")

        for s_int in range(0, int(max_speed_m_s * 10) + 1, 5):
            spd = s_int / 10.0
            pt = self.evaluate_flight_condition(
                total_mass_kg=total_mass_kg,
                rotor_rpm=rotor_rpm,
                forward_speed_m_s=spd,
                atmosphere=atmosphere,
            )
            if pt.total_electrical_power_w < min_power:
                min_power = pt.total_electrical_power_w
                best_speed = spd

        return best_speed, min_power
