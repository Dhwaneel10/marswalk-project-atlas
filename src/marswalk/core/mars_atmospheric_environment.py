"""
MarsWalk 2.0 / Project Atlas — Milestone 13L: Mars Atmospheric Pressure & Wind Model.

Calculates elevation-dependent barometric pressure and diurnal surface wind speed vectors
calibrated to Mars 2020 Perseverance MEDA observations at Jezero Crater.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any

# Scale height of Martian atmosphere in meters
MARS_SCALE_HEIGHT_M = 11100.0
# Reference surface pressure at Martian datum (z = 0 m) in Pascals
MARS_DATUM_PRESSURE_PA = 610.0


@dataclass(frozen=True)
class AtmosphericStateResult:
    """Atmospheric pressure, density, and surface wind vector at a given point and time."""
    sol: int
    ltst_hours: float
    elevation_m: float
    pressure_pa: float
    air_density_kg_m3: float
    wind_speed_m_s: float
    wind_direction_deg: float
    wind_gust_m_s: float
    is_wind_hazard: bool
    wind_hazard_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sol": self.sol,
            "ltst_hours": round(self.ltst_hours, 3),
            "elevation_m": round(self.elevation_m, 2),
            "pressure_pa": round(self.pressure_pa, 1),
            "air_density_kg_m3": round(self.air_density_kg_m3, 5),
            "wind_speed_m_s": round(self.wind_speed_m_s, 2),
            "wind_direction_deg": round(self.wind_direction_deg, 1),
            "wind_gust_m_s": round(self.wind_gust_m_s, 2),
            "is_wind_hazard": self.is_wind_hazard,
            "wind_hazard_reason": self.wind_hazard_reason,
        }


class MarsAtmosphericEnvironmentEngine:
    """
    Evaluates barometric pressure and surface wind conditions over Jezero Crater.
    """

    MAX_OPERATIONAL_WIND_SPEED_M_S = 22.0  # Safe mobility and mast deployment limit

    def compute_barometric_pressure(
        self,
        elevation_m: float,
        seasonal_anomaly_pa: float = 0.0,
    ) -> float:
        """
        Compute hydrostatic surface pressure P(z) = P0 * exp(-z / H).
        At Jezero Crater (-2500 m elevation), standard pressure is ~760 Pa.
        """
        p = MARS_DATUM_PRESSURE_PA * math.exp(-elevation_m / MARS_SCALE_HEIGHT_M)
        p += seasonal_anomaly_pa
        return max(50.0, float(p))

    def compute_air_density(self, pressure_pa: float, temperature_c: float) -> float:
        """
        Compute atmospheric density rho = P / (R_spec * T).
        For Mars CO2-dominated atmosphere: R_spec ≈ 188.92 J/(kg·K).
        """
        temp_k = temperature_c + 273.15
        r_spec = 188.92
        rho = pressure_pa / (r_spec * temp_k)
        return float(rho)

    def compute_surface_wind(
        self,
        ltst_hours: float,
        slope_deg: float = 0.0,
        wind_anomaly_m_s: float = 0.0,
    ) -> Tuple[float, float, float]:
        """
        Compute diurnal wind speed (m/s), direction (deg clockwise from North), and peak gust.
        MEDA Jezero records show calm mornings (<3 m/s) and gusty convective afternoons (8-15 m/s).
        Returns: (wind_speed_m_s, wind_direction_deg, wind_gust_m_s)
        """
        # Diurnal wind speed curve peaking around 15:00 LTST
        phase = ((ltst_hours - 15.0) % 24.0) / 24.0 * 2.0 * math.pi
        base_speed = 4.0 + 3.5 * math.cos(phase) + (slope_deg * 0.15)
        speed = max(0.5, base_speed + wind_anomaly_m_s)

        # Prevailing wind direction in Jezero: Easterly to South-Easterly morning (100°),
        # shifting to North-Westerly afternoon (310°)
        if 6.0 <= ltst_hours <= 12.0:
            direction = 100.0 + (ltst_hours - 6.0) * 15.0
        else:
            direction = 280.0 + math.sin(phase) * 30.0

        gust = speed * 1.55  # Peak instantaneous gust factor

        return float(round(speed, 2)), float(round(direction % 360.0, 1)), float(round(gust, 2))

    def evaluate_atmospheric_state(
        self,
        sol: int,
        ltst_hours: float,
        elevation_m: float = -2500.0,
        temperature_c: float = -40.0,
        slope_deg: float = 0.0,
        pressure_anomaly_pa: float = 0.0,
        wind_anomaly_m_s: float = 0.0,
    ) -> AtmosphericStateResult:
        """
        Evaluate full atmospheric parameters and check for operational wind hazards.
        """
        pressure = self.compute_barometric_pressure(elevation_m, pressure_anomaly_pa)
        density = self.compute_air_density(pressure, temperature_c)
        speed, direction, gust = self.compute_surface_wind(ltst_hours, slope_deg, wind_anomaly_m_s)

        is_hazard = gust >= self.MAX_OPERATIONAL_WIND_SPEED_M_S
        reason = None
        if is_hazard:
            reason = (
                f"Peak wind gust ({gust:.1f} m/s) exceeds maximum operational limit "
                f"({self.MAX_OPERATIONAL_WIND_SPEED_M_S:.1f} m/s)"
            )

        return AtmosphericStateResult(
            sol=sol,
            ltst_hours=ltst_hours,
            elevation_m=elevation_m,
            pressure_pa=pressure,
            air_density_kg_m3=density,
            wind_speed_m_s=speed,
            wind_direction_deg=direction,
            wind_gust_m_s=gust,
            is_wind_hazard=is_hazard,
            wind_hazard_reason=reason,
        )
