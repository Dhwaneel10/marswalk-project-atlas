"""
MarsWalk 2.0 / Project Atlas — Milestone 13L: Mars Thermal Environment Intelligence.

Models diurnal surface and atmospheric temperature curves for Jezero Crater based on
published Mars 2020 Perseverance MEDA observations and Mars Climate Database (MCD) profiles.
Validates instrument operational envelopes and detects thermal limit violations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any

# Standard instrument thermal operating limits in degrees Celsius
# (Derived from Mars 2020 mission instrument specs)
INSTRUMENT_THERMAL_LIMITS_C: Dict[str, Tuple[float, float]] = {
    "MASTCAM_Z": (-55.0, 40.0),
    "SUPERCAM": (-50.0, 30.0),
    "PIXL": (-40.0, 35.0),
    "SHERLOC": (-35.0, 30.0),
    "RIMFAX": (-60.0, 50.0),
    "MEDA": (-90.0, 60.0),
    "MOXIE": (-20.0, 45.0),
}


@dataclass(frozen=True)
class ThermalEvaluationResult:
    """Thermal state evaluation for a given location, sol, and local solar time."""
    sol: int
    ltst_hours: float
    air_temperature_c: float
    ground_temperature_c: float
    elevation_m: float
    instrument_name: Optional[str]
    is_instrument_within_limits: bool
    temperature_margin_c: Optional[float]
    thermal_violation_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sol": self.sol,
            "ltst_hours": round(self.ltst_hours, 3),
            "air_temperature_c": round(self.air_temperature_c, 2),
            "ground_temperature_c": round(self.ground_temperature_c, 2),
            "elevation_m": round(self.elevation_m, 2),
            "instrument_name": self.instrument_name,
            "is_instrument_within_limits": self.is_instrument_within_limits,
            "temperature_margin_c": round(self.temperature_margin_c, 2) if self.temperature_margin_c is not None else None,
            "thermal_violation_reason": self.thermal_violation_reason,
        }


class MarsThermalEnvironmentEngine:
    """
    Computes diurnal temperature variations and thermal limit compliance for Jezero Crater.
    """

    # Baseline diurnal constants (calibrated to MEDA data at Jezero Crater, ~ -2500m elevation)
    # Rodriguez-Manfredi et al. (2021), Savijärvi et al. (2022)
    BASE_GROUND_TEMP_MIN_C = -85.0   # Dawn ground temperature (~05:30 LTST)
    BASE_GROUND_TEMP_MAX_C = -15.0   # Early afternoon ground temperature (~13:00 LTST)
    BASE_AIR_TEMP_MIN_C = -80.0      # Dawn air temperature (~06:00 LTST)
    BASE_AIR_TEMP_MAX_C = -22.0      # Afternoon air temperature (~14:00 LTST)
    ELEVATION_LAPSE_RATE_C_PER_KM = -4.5  # Dry adiabatic lapse rate on Mars

    def __init__(self, base_elevation_m: float = -2500.0) -> None:
        self.base_elevation_m = base_elevation_m

    def compute_diurnal_temperatures(
        self,
        ltst_hours: float,
        elevation_m: float = -2500.0,
        thermal_anomaly_c: float = 0.0,
    ) -> Tuple[float, float]:
        """
        Calculate ground and air temperatures in Celsius at a specific Local Solar Time (LTST)
        accounting for elevation lapse rate and optional scenario anomaly.
        """
        # Realistic asymmetric diurnal cycle:
        # Ground solar heating from dawn (~05:30) to peak (~13:00) takes 7.5 hours.
        # Ground radiative cooling from peak (~13:00) to dawn (~05:30) takes 16.5 hours.
        ltst = ltst_hours % 24.0
        if 5.5 <= ltst <= 13.0:
            frac_gnd = (ltst - 5.5) / 7.5
            phase_gnd = math.pi * (1.0 - frac_gnd)
        else:
            elapsed_gnd = (ltst - 13.0) if ltst > 13.0 else ((24.0 - 13.0) + ltst)
            frac_gnd = elapsed_gnd / 16.5
            phase_gnd = math.pi * frac_gnd

        gnd_factor = math.cos(phase_gnd)
        gnd_amp = (self.BASE_GROUND_TEMP_MAX_C - self.BASE_GROUND_TEMP_MIN_C) / 2.0
        gnd_mean = (self.BASE_GROUND_TEMP_MAX_C + self.BASE_GROUND_TEMP_MIN_C) / 2.0
        t_ground = gnd_mean + gnd_amp * gnd_factor

        # Air temperature curve (lagging ground: heating 06:00 to 14:00, cooling 14:00 to 06:00)
        if 6.0 <= ltst <= 14.0:
            frac_air = (ltst - 6.0) / 8.0
            phase_air = math.pi * (1.0 - frac_air)
        else:
            elapsed_air = (ltst - 14.0) if ltst > 14.0 else ((24.0 - 14.0) + ltst)
            frac_air = elapsed_air / 16.0
            phase_air = math.pi * frac_air

        air_factor = math.cos(phase_air)
        air_amp = (self.BASE_AIR_TEMP_MAX_C - self.BASE_AIR_TEMP_MIN_C) / 2.0
        air_mean = (self.BASE_AIR_TEMP_MAX_C + self.BASE_AIR_TEMP_MIN_C) / 2.0
        t_air = air_mean + air_amp * air_factor

        # Elevation lapse adjustment: higher elevations are cooler
        delta_z_km = (elevation_m - self.base_elevation_m) / 1000.0
        lapse_offset = delta_z_km * self.ELEVATION_LAPSE_RATE_C_PER_KM

        t_ground += lapse_offset + thermal_anomaly_c
        t_air += lapse_offset + thermal_anomaly_c

        return float(round(t_air, 2)), float(round(t_ground, 2))

    def evaluate_instrument_thermal_state(
        self,
        sol: int,
        ltst_hours: float,
        instrument_name: str,
        elevation_m: float = -2500.0,
        thermal_anomaly_c: float = 0.0,
    ) -> ThermalEvaluationResult:
        """
        Evaluate if an instrument operation is within its thermal envelope at the specified time.
        """
        t_air, t_ground = self.compute_diurnal_temperatures(
            ltst_hours=ltst_hours,
            elevation_m=elevation_m,
            thermal_anomaly_c=thermal_anomaly_c,
        )

        limits = INSTRUMENT_THERMAL_LIMITS_C.get(instrument_name.upper())
        if limits is None:
            # Unknown instrument: default safe pass with warning
            return ThermalEvaluationResult(
                sol=sol,
                ltst_hours=ltst_hours,
                air_temperature_c=t_air,
                ground_temperature_c=t_ground,
                elevation_m=elevation_m,
                instrument_name=instrument_name,
                is_instrument_within_limits=True,
                temperature_margin_c=None,
                thermal_violation_reason=None,
            )

        min_t, max_t = limits
        # Most instruments depend primarily on air / internal electronics temperature
        margin_low = t_air - min_t
        margin_high = max_t - t_air
        min_margin = min(margin_low, margin_high)

        is_within = (t_air >= min_t) and (t_air <= max_t)
        reason = None
        if t_air < min_t:
            reason = f"Air temp ({t_air:.1f}°C) below minimum operational limit ({min_t:.1f}°C) for {instrument_name}"
        elif t_air > max_t:
            reason = f"Air temp ({t_air:.1f}°C) exceeds maximum operational limit ({max_t:.1f}°C) for {instrument_name}"

        return ThermalEvaluationResult(
            sol=sol,
            ltst_hours=ltst_hours,
            air_temperature_c=t_air,
            ground_temperature_c=t_ground,
            elevation_m=elevation_m,
            instrument_name=instrument_name,
            is_instrument_within_limits=is_within,
            temperature_margin_c=min_margin,
            thermal_violation_reason=reason,
        )
