"""
MarsWalk 2.0 / Project Atlas — Milestone 13L: Environmental Uncertainty Engine.

Manages measurement, spatial interpolation, and scenario uncertainties across
Martian environmental parameters using physically calibrated confidence intervals
and sensor specification tolerances, without manufacturing unscientific Gaussian distributions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Any


@dataclass(frozen=True)
class UncertaintyInterval:
    """Bounded confidence interval for an environmental parameter."""
    nominal: float
    lower_bound: float
    upper_bound: float
    confidence_basis: str  # e.g., "INSTRUMENT_CALIBRATION_SPEC", "SENSOR_RESOLUTION_LIMIT"
    parameter_name: str
    units: str

    def __post_init__(self) -> None:
        if self.lower_bound > self.upper_bound:
            raise ValueError(
                f"lower_bound ({self.lower_bound}) cannot exceed upper_bound ({self.upper_bound})"
            )

    @property
    def span(self) -> float:
        """Total interval range (upper - lower)."""
        return round(self.upper_bound - self.lower_bound, 4)

    def contains(self, value: float) -> bool:
        """Check if a measured or evaluated value falls within bounds."""
        return self.lower_bound <= value <= self.upper_bound

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nominal": round(self.nominal, 3),
            "lower_bound": round(self.lower_bound, 3),
            "upper_bound": round(self.upper_bound, 3),
            "span": self.span,
            "confidence_basis": self.confidence_basis,
            "parameter_name": self.parameter_name,
            "units": self.units,
        }


class EnvironmentalUncertaintyEngine:
    """
    Evaluates physical instrument and model uncertainty intervals for Jezero Crater observations.
    Derived from published Mars 2020 Perseverance instrument papers (MEDA, Mastcam-Z)
    and USGS MRO CTX stereogrammetry calibration reports.
    """

    # Physical tolerances from instrument specs
    CTX_ELEVATION_TOLERANCE_M = 1.0        # CTX stereogrammetric vertical accuracy
    HORN_SLOPE_TOLERANCE_DEG = 0.8         # 3x3 finite-difference discretization uncertainty
    MEDA_AIR_TEMP_TOLERANCE_K = 2.5        # MEDA ATS sensor calibration accuracy (Rodriguez-Manfredi et al., 2021)
    MEDA_GROUND_TEMP_TOLERANCE_K = 3.0     # MEDA TRS infrared thermopile sensor accuracy
    MEDA_PRESSURE_TOLERANCE_PA = 5.0       # MEDA PS pressure sensor resolution and hysteresis
    DUST_OPACITY_TOLERANCE_TAU = 0.15      # Mastcam-Z / MEDA RDS direct-sun solar extinction fit tolerance
    SOLAR_FLUX_TOLERANCE_W_M2 = 12.0       # Direct solar irradiance atmospheric attenuation variance

    @classmethod
    def evaluate_elevation_interval(cls, nominal_elev_m: float) -> UncertaintyInterval:
        """Compute elevation bounds based on CTX vertical stereogrammetry precision."""
        return UncertaintyInterval(
            nominal=nominal_elev_m,
            lower_bound=nominal_elev_m - cls.CTX_ELEVATION_TOLERANCE_M,
            upper_bound=nominal_elev_m + cls.CTX_ELEVATION_TOLERANCE_M,
            confidence_basis="USGS_CTX_STEREOGRAMMETRIC_SPEC",
            parameter_name="surface_elevation",
            units="m",
        )

    @classmethod
    def evaluate_slope_interval(cls, nominal_slope_deg: float) -> UncertaintyInterval:
        """Compute slope bounds considering 3x3 kernel quantization."""
        lower = max(0.0, nominal_slope_deg - cls.HORN_SLOPE_TOLERANCE_DEG)
        upper = min(90.0, nominal_slope_deg + cls.HORN_SLOPE_TOLERANCE_DEG)
        return UncertaintyInterval(
            nominal=nominal_slope_deg,
            lower_bound=lower,
            upper_bound=upper,
            confidence_basis="HORN_KERNEL_DISCRETIZATION_TOLERANCE",
            parameter_name="surface_slope",
            units="deg",
        )

    @classmethod
    def evaluate_air_temperature_interval(cls, nominal_temp_c: float) -> UncertaintyInterval:
        """Compute ambient atmospheric temperature bounds based on MEDA ATS calibration."""
        return UncertaintyInterval(
            nominal=nominal_temp_c,
            lower_bound=nominal_temp_c - cls.MEDA_AIR_TEMP_TOLERANCE_K,
            upper_bound=nominal_temp_c + cls.MEDA_AIR_TEMP_TOLERANCE_K,
            confidence_basis="MEDA_ATS_CALIBRATION_TOLERANCE",
            parameter_name="air_temperature",
            units="deg_C",
        )

    @classmethod
    def evaluate_ground_temperature_interval(cls, nominal_temp_c: float) -> UncertaintyInterval:
        """Compute surface ground temperature bounds based on MEDA TRS infrared calibration."""
        return UncertaintyInterval(
            nominal=nominal_temp_c,
            lower_bound=nominal_temp_c - cls.MEDA_GROUND_TEMP_TOLERANCE_K,
            upper_bound=nominal_temp_c + cls.MEDA_GROUND_TEMP_TOLERANCE_K,
            confidence_basis="MEDA_TRS_CALIBRATION_TOLERANCE",
            parameter_name="ground_temperature",
            units="deg_C",
        )

    @classmethod
    def evaluate_dust_opacity_interval(cls, nominal_tau: float) -> UncertaintyInterval:
        """Compute atmospheric optical depth bounds based on solar extinction measurement uncertainty."""
        lower = max(0.05, nominal_tau - cls.DUST_OPACITY_TOLERANCE_TAU)
        upper = min(10.0, nominal_tau + cls.DUST_OPACITY_TOLERANCE_TAU)
        return UncertaintyInterval(
            nominal=nominal_tau,
            lower_bound=lower,
            upper_bound=upper,
            confidence_basis="MASTCAM_MEDA_RDS_EXTINCTION_TOLERANCE",
            parameter_name="dust_opacity_tau",
            units="dimensionless_tau",
        )

    @classmethod
    def evaluate_pressure_interval(cls, nominal_pressure_pa: float) -> UncertaintyInterval:
        """Compute atmospheric pressure bounds based on MEDA PS transducer precision."""
        return UncertaintyInterval(
            nominal=nominal_pressure_pa,
            lower_bound=nominal_pressure_pa - cls.MEDA_PRESSURE_TOLERANCE_PA,
            upper_bound=nominal_pressure_pa + cls.MEDA_PRESSURE_TOLERANCE_PA,
            confidence_basis="MEDA_PS_TRANSDUCER_SPEC",
            parameter_name="atmospheric_pressure",
            units="Pa",
        )
