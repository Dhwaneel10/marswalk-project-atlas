"""
MarsWalk 2.0 / Project Atlas - Planetary Data Quality & Sensor Uncertainty Engine
Formal verification of instrument sensor quality flags, operational constraints,
uncertainty characterization, and strict preservation of missing/corrupted values.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List


class QualityStatus(str, Enum):
    NOMINAL = "NOMINAL"
    CALIBRATED = "CALIBRATED"
    DEGRADED = "DEGRADED"
    FLAGGED_OUTLIER = "FLAGGED_OUTLIER"
    NULL_PRESERVED = "NULL_PRESERVED"
    REJECTED_SHADOW = "REJECTED_SHADOW"
    REJECTED_TILT = "REJECTED_TILT"
    REJECTED_OBSTRUCTION = "REJECTED_OBSTRUCTION"


@dataclass(frozen=True)
class SensorUncertaintySpec:
    sensor_id: str
    instrument: str
    parameter_name: str
    unit: str
    accuracy_1sigma: float
    precision_1sigma: float
    valid_range_min: float
    valid_range_max: float
    literature_reference: str


# Sensor specifications from published instrument calibration papers
SENSOR_UNCERTAINTY_REGISTRY: Dict[str, SensorUncertaintySpec] = {
    "MEDA_PS": SensorUncertaintySpec(
        sensor_id="MEDA_PS",
        instrument="Perseverance MEDA Pressure Sensor",
        parameter_name="atmospheric_pressure",
        unit="Pa",
        accuracy_1sigma=0.12,
        precision_1sigma=0.04,
        valid_range_min=450.0,
        valid_range_max=1150.0,
        literature_reference="Rodriguez-Manfredi et al. (2021), Space Science Reviews"
    ),
    "MEDA_ATS": SensorUncertaintySpec(
        sensor_id="MEDA_ATS",
        instrument="Perseverance MEDA Air Temperature Sensors (ATS1-ATS5)",
        parameter_name="air_temperature",
        unit="K",
        accuracy_1sigma=1.0,
        precision_1sigma=0.1,
        valid_range_min=140.0,  # -133 C
        valid_range_max=310.0,  # +37 C
        literature_reference="Savijarvi et al. (2022), JGR Planets"
    ),
    "MEDA_TIRS": SensorUncertaintySpec(
        sensor_id="MEDA_TIRS",
        instrument="Perseverance MEDA Thermal Infrared Sensor (TIRS)",
        parameter_name="ground_temperature",
        unit="K",
        accuracy_1sigma=1.5,
        precision_1sigma=0.2,
        valid_range_min=130.0,  # -143 C
        valid_range_max=325.0,  # +52 C
        literature_reference="Perez-Izquierdo et al. (2018), JGR Planets"
    ),
    "MEDA_RDS": SensorUncertaintySpec(
        sensor_id="MEDA_RDS",
        instrument="Perseverance MEDA Radiation and Dust Sensor (RDS)",
        parameter_name="optical_depth_tau",
        unit="1",
        accuracy_1sigma=0.05,
        precision_1sigma=0.02,
        valid_range_min=0.1,
        valid_range_max=6.0,
        literature_reference="Apestigue et al. (2022), Space Science Reviews"
    ),
    "MEDA_WS": SensorUncertaintySpec(
        sensor_id="MEDA_WS",
        instrument="Perseverance MEDA Wind Sensor Booms (WS1/WS2)",
        parameter_name="wind_speed",
        unit="m/s",
        accuracy_1sigma=1.2,
        precision_1sigma=0.3,
        valid_range_min=0.0,
        valid_range_max=50.0,
        literature_reference="Newman et al. (2022), JGR Planets"
    ),
    "MRO_MCS_TEMP": SensorUncertaintySpec(
        sensor_id="MRO_MCS_TEMP",
        instrument="MRO Mars Climate Sounder (MCS)",
        parameter_name="atmospheric_temperature_profile",
        unit="K",
        accuracy_1sigma=1.5,
        precision_1sigma=0.5,
        valid_range_min=120.0,
        valid_range_max=300.0,
        literature_reference="Kleinboehl et al. (2009), JGR Planets"
    ),
    "MRO_MCS_DUST": SensorUncertaintySpec(
        sensor_id="MRO_MCS_DUST",
        instrument="MRO Mars Climate Sounder (MCS)",
        parameter_name="dust_extinction_profile",
        unit="1/km",
        accuracy_1sigma=0.0003,
        precision_1sigma=0.0001,
        valid_range_min=0.0,
        valid_range_max=0.05,
        literature_reference="McCleese et al. (2010), JGR Planets"
    ),
    "MCD_6_2_GCM": SensorUncertaintySpec(
        sensor_id="MCD_6_2_GCM",
        instrument="Mars Climate Database v6.2 (GCM Numerical Model)",
        parameter_name="climatological_prediction",
        unit="K",
        accuracy_1sigma=4.5,
        precision_1sigma=1.0,
        valid_range_min=130.0,
        valid_range_max=320.0,
        literature_reference="Forget et al. (1999), Millour et al. (2018)"
    )
}


def filter_tirs_measurement(
    upward_lw_flux: float,
    upward_lw_uncertainty: float,
    rsm_outside_fov: Optional[int] = None,
    wheel_outside_fov: Optional[int] = None,
    sun_outside_fov: Optional[int] = None,
    rover_low_tilt: Optional[int] = None,
    ground_not_in_shadow: Optional[int] = None,
    rover_still: Optional[int] = None
) -> Dict[str, Any]:
    """
    Apply Perseverance MEDA TIRS quality screening rules.
    Derives ground temperature from upward longwave radiative flux:
    T_ground = (F / (eps * sigma))^(1/4) with emissivity eps ~ 0.98.
    """
    sigma = 5.670374419e-8  # Stefan-Boltzmann constant W/(m^2 K^4)
    emissivity = 0.98

    # Check physical flux validity
    if upward_lw_flux <= 0.0 or upward_lw_flux > 600.0:
        return {
            "status": QualityStatus.FLAGGED_OUTLIER.value,
            "ground_temp_k": None,
            "ground_temp_c": None,
            "uncertainty_k": None,
            "rejection_reason": f"Upward flux {upward_lw_flux} W/m2 out of physical bounds [0, 600]"
        }

    # Compute ground surface temperature
    t_k = (upward_lw_flux / (emissivity * sigma)) ** 0.25
    # Propagate uncertainty: dT = (1/4) * (T / F) * dF
    t_err_k = 0.25 * (t_k / upward_lw_flux) * upward_lw_uncertainty if upward_lw_flux > 0 else 1.5

    spec = SENSOR_UNCERTAINTY_REGISTRY["MEDA_TIRS"]
    if t_k < spec.valid_range_min or t_k > spec.valid_range_max:
        return {
            "status": QualityStatus.FLAGGED_OUTLIER.value,
            "ground_temp_k": round(t_k, 2),
            "ground_temp_c": round(t_k - 273.15, 2),
            "uncertainty_k": round(t_err_k, 2),
            "rejection_reason": f"Derived temperature {t_k:.1f} K exceeds valid range [{spec.valid_range_min}, {spec.valid_range_max}]"
        }

    # Hardware quality flags
    if ground_not_in_shadow == 0:
        return {
            "status": QualityStatus.REJECTED_SHADOW.value,
            "ground_temp_k": round(t_k, 2),
            "ground_temp_c": round(t_k - 273.15, 2),
            "uncertainty_k": round(t_err_k * 1.8, 2),
            "rejection_reason": "Ground footprint in rover cast shadow (thermal perturbation)"
        }

    if rover_low_tilt == 0:
        return {
            "status": QualityStatus.REJECTED_TILT.value,
            "ground_temp_k": round(t_k, 2),
            "ground_temp_c": round(t_k - 273.15, 2),
            "uncertainty_k": round(t_err_k * 1.5, 2),
            "rejection_reason": "Rover tilt exceeds safe threshold (>15 deg)"
        }

    if sun_outside_fov == 0 or rsm_outside_fov == 0:
        return {
            "status": QualityStatus.REJECTED_OBSTRUCTION.value,
            "ground_temp_k": round(t_k, 2),
            "ground_temp_c": round(t_k - 273.15, 2),
            "uncertainty_k": round(t_err_k * 2.0, 2),
            "rejection_reason": "Sun or RSM mast structure directly in TIRS field of view"
        }

    return {
        "status": QualityStatus.NOMINAL.value,
        "ground_temp_k": round(t_k, 2),
        "ground_temp_c": round(t_k - 273.15, 2),
        "uncertainty_k": round(t_err_k, 2),
        "rejection_reason": None
    }


def filter_ats_measurement(temperatures_k: List[float]) -> Dict[str, Any]:
    """
    Screen calibrated mast temperatures from ATS1-ATS5 sensors.
    ATS1 and ATS2 are mounted on the Remote Sensing Mast at 1.45m height.
    Filters out corrupted or disconnected sensors and returns the representative air temperature.
    """
    spec = SENSOR_UNCERTAINTY_REGISTRY["MEDA_ATS"]
    valid_temps = [t for t in temperatures_k if spec.valid_range_min <= t <= spec.valid_range_max]

    if not valid_temps:
        return {
            "status": QualityStatus.FLAGGED_OUTLIER.value,
            "air_temp_k": None,
            "air_temp_c": None,
            "uncertainty_k": None,
            "valid_sensor_count": 0,
            "rejection_reason": "All ATS temperature channels outside valid physical limits"
        }

    # If multiple valid sensors, take median to reject thermal plume contamination from rover deck
    sorted_temps = sorted(valid_temps)
    median_t = sorted_temps[len(sorted_temps) // 2]
    # Check sensor dispersion
    spread = max(valid_temps) - min(valid_temps)
    status = QualityStatus.NOMINAL.value if spread < 8.0 else QualityStatus.DEGRADED.value
    err_k = spec.accuracy_1sigma if status == QualityStatus.NOMINAL.value else spec.accuracy_1sigma * 2.0

    return {
        "status": status,
        "air_temp_k": round(median_t, 2),
        "air_temp_c": round(median_t - 273.15, 2),
        "uncertainty_k": round(err_k, 2),
        "valid_sensor_count": len(valid_temps),
        "sensor_spread_k": round(spread, 2),
        "rejection_reason": None if status == QualityStatus.NOMINAL.value else f"High inter-sensor dispersion ({spread:.1f} K)"
    }


def filter_ps_measurement(pressure_pa: float) -> Dict[str, Any]:
    """Verify atmospheric pressure transducer range."""
    spec = SENSOR_UNCERTAINTY_REGISTRY["MEDA_PS"]
    if spec.valid_range_min <= pressure_pa <= spec.valid_range_max:
        return {
            "status": QualityStatus.NOMINAL.value,
            "pressure_pa": round(pressure_pa, 2),
            "uncertainty_pa": spec.accuracy_1sigma,
            "rejection_reason": None
        }
    return {
        "status": QualityStatus.FLAGGED_OUTLIER.value,
        "pressure_pa": round(pressure_pa, 2),
        "uncertainty_pa": None,
        "rejection_reason": f"Pressure {pressure_pa:.1f} Pa outside valid Martian range [{spec.valid_range_min}, {spec.valid_range_max}]"
    }


def filter_wind_measurement(wind_speed_m_s: Optional[float], wind_dir_deg: Optional[float], sensor_flag: Optional[str] = None) -> Dict[str, Any]:
    """
    Screen MEDA Wind Sensor (WS).
    Strictly preserves null values when sensor suffered saltation grit degradation.
    Never invents synthetic wind values.
    """
    if wind_speed_m_s is None or (sensor_flag and "OFFLINE" in sensor_flag.upper()):
        return {
            "status": QualityStatus.NULL_PRESERVED.value,
            "wind_speed_m_s": None,
            "wind_dir_deg": None,
            "uncertainty_m_s": None,
            "rejection_reason": "MEDA WS boom suffered grit degradation; measurement preserved as NULL per scientific integrity rule"
        }

    spec = SENSOR_UNCERTAINTY_REGISTRY["MEDA_WS"]
    if spec.valid_range_min <= wind_speed_m_s <= spec.valid_range_max:
        return {
            "status": QualityStatus.NOMINAL.value,
            "wind_speed_m_s": round(wind_speed_m_s, 2),
            "wind_dir_deg": round(wind_dir_deg % 360.0, 1) if wind_dir_deg is not None else None,
            "uncertainty_m_s": spec.accuracy_1sigma,
            "rejection_reason": None
        }

    return {
        "status": QualityStatus.FLAGGED_OUTLIER.value,
        "wind_speed_m_s": round(wind_speed_m_s, 2),
        "wind_dir_deg": wind_dir_deg,
        "uncertainty_m_s": None,
        "rejection_reason": f"Wind speed {wind_speed_m_s} m/s exceeds physical limits [{spec.valid_range_min}, {spec.valid_range_max}]"
    }
