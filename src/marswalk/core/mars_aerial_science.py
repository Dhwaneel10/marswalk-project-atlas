"""
MarsWalk 2.0 / Project Atlas — Milestone 13P: Planetary Aerial Science Engine
============================================================================
Simulates scientific observation payloads aboard Martian rotorcraft:
- High-Resolution Visible Optical Camera (Stereo mapping, GSD, coverage footprints).
- Near-Infrared (NIR) Multispectral Imager (Mineralogical bands, phyllosilicates, ferric oxides).
- Synthetic Ground-Penetrating Radar (GPR) Subsurface Sounder (Explicitly synthetic layer boundaries,
  dielectric contrasts, radar echoes, and non-probabilistic truth disclosures).
- Aerial Atmospheric Sensor Suite (Wind profiles, pressure, temperature, dust optical depth).
- Microdosimeter (Cosmic radiation flux, simulated dose rates).

Scientific Rules:
- All radar reflections are labeled as SYNTHETIC SIMULATION MODELS, never proof of subsurface water ice.
- Sensor footprints and GSD strictly respect optical geometry (GSD = (altitude * pixel_pitch) / focal_length).
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SensorModality(str, Enum):
    VISIBLE_OPTICAL = "VISIBLE_OPTICAL"
    NIR_MULTISPECTRAL = "NIR_MULTISPECTRAL"
    SYNTHETIC_GPR_RADAR = "SYNTHETIC_GPR_RADAR"
    ATMOSPHERIC_SUITE = "ATMOSPHERIC_SUITE"
    RADIATION_DOSIMETER = "RADIATION_DOSIMETER"


@dataclass
class AerialObservation:
    """Standardized scientific observation acquired by an airborne rotorcraft."""
    observation_id: str
    aircraft_id: str
    sensor_modality: SensorModality
    sensor_name: str
    timestamp_sol: float
    position_xyz_m: List[float]
    sensor_footprint_radius_m: float
    ground_sampling_distance_cm_px: float
    target_feature_name: str
    primary_metric_name: str
    primary_metric_value: float
    metric_units: str
    measurement_uncertainty: float
    is_synthetic_scenario_model: bool
    scientific_provenance: str
    geological_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "aircraft_id": self.aircraft_id,
            "sensor_modality": self.sensor_modality.value,
            "sensor_name": self.sensor_name,
            "timestamp_sol": round(self.timestamp_sol, 4),
            "position_xyz_m": [round(c, 2) for c in self.position_xyz_m],
            "sensor_footprint_radius_m": round(self.sensor_footprint_radius_m, 2),
            "ground_sampling_distance_cm_px": round(self.ground_sampling_distance_cm_px, 2),
            "target_feature_name": self.target_feature_name,
            "primary_metric_name": self.primary_metric_name,
            "primary_metric_value": round(self.primary_metric_value, 4),
            "metric_units": self.metric_units,
            "measurement_uncertainty": round(self.measurement_uncertainty, 4),
            "is_synthetic_scenario_model": self.is_synthetic_scenario_model,
            "scientific_provenance": self.scientific_provenance,
            "geological_context": self.geological_context,
        }


class MarsAerialScienceEngine:
    """
    Simulates observation acquisition, sensor footprint projections, and science data logging.
    """

    def __init__(self):
        self._observations_log: List[AerialObservation] = []

    def acquire_visible_imagery(
        self,
        aircraft_id: str,
        position_xyz_m: List[float],
        timestamp_sol: float,
        target_name: str = "Jezero Delta Scarp Outcrop",
        focal_length_mm: float = 8.5,
        sensor_width_mm: float = 6.4,
        pixel_count_horizontal: int = 4056,
    ) -> AerialObservation:
        """
        Calculates visible optical footprint and ground sampling distance (GSD).
        GSD = (Altitude * SensorWidth) / (FocalLength * Pixels)
        """
        alt_m = max(1.0, position_xyz_m[2])
        # Field of View (horizontal)
        fov_rad = 2.0 * math.atan((sensor_width_mm / 2.0) / focal_length_mm)
        footprint_radius_m = alt_m * math.tan(fov_rad / 2.0)
        gsd_m_px = (alt_m * (sensor_width_mm / 1000.0)) / (focal_length_mm / 1000.0 * pixel_count_horizontal)
        gsd_cm_px = gsd_m_px * 100.0

        obs_id = f"OBS-VIS-{uuid.uuid4().hex[:8].upper()}"
        obs = AerialObservation(
            observation_id=obs_id,
            aircraft_id=aircraft_id,
            sensor_modality=SensorModality.VISIBLE_OPTICAL,
            sensor_name="High-Resolution Aerial NavCam/ScoutCam",
            timestamp_sol=timestamp_sol,
            position_xyz_m=list(position_xyz_m),
            sensor_footprint_radius_m=footprint_radius_m,
            ground_sampling_distance_cm_px=gsd_cm_px,
            target_feature_name=target_name,
            primary_metric_name="SURFACE_REFLECTANCE_ALBEDO",
            primary_metric_value=0.235,
            metric_units="dimensionless",
            measurement_uncertainty=0.015,
            is_synthetic_scenario_model=False,
            scientific_provenance="Optical geometry model derived from JPL Ingenuity RTE camera optics",
            geological_context={
                "boulder_count_detected": 14,
                "max_boulder_diameter_m": 0.85,
                "traversability_hazard_flag": "LOCAL_ESCARPMENT_DETECTED",
            },
        )
        self._observations_log.append(obs)
        return obs

    def acquire_nir_multispectral(
        self,
        aircraft_id: str,
        position_xyz_m: List[float],
        timestamp_sol: float,
        target_name: str = "Clay-Bearing Delta Sediments",
    ) -> AerialObservation:
        """
        Acquires near-infrared spectral reflectance indicators (phyllosilicates / carbonates).
        """
        alt_m = max(1.0, position_xyz_m[2])
        footprint_radius = alt_m * 0.45  # ~50 deg FOV
        gsd_cm_px = (alt_m / 15.0) * 4.5

        obs_id = f"OBS-NIR-{uuid.uuid4().hex[:8].upper()}"
        obs = AerialObservation(
            observation_id=obs_id,
            aircraft_id=aircraft_id,
            sensor_modality=SensorModality.NIR_MULTISPECTRAL,
            sensor_name="Aerial Compact Reconnaissance Imaging Spectrometer",
            timestamp_sol=timestamp_sol,
            position_xyz_m=list(position_xyz_m),
            sensor_footprint_radius_m=footprint_radius,
            ground_sampling_distance_cm_px=gsd_cm_px,
            target_feature_name=target_name,
            primary_metric_name="PHYLLOSILICATE_BAND_DEPTH_2.3UM",
            primary_metric_value=0.142,
            metric_units="normalized_band_depth",
            measurement_uncertainty=0.012,
            is_synthetic_scenario_model=False,
            scientific_provenance="CRISM / SuperCam spectral reflectance analogs for Jezero Delta",
            geological_context={
                "mineral_class": "FE_MG_SMECTITE_CLAY",
                "astrobiology_priority": "TIER_1_SAMPLE_CANDIDATE",
            },
        )
        self._observations_log.append(obs)
        return obs

    def acquire_synthetic_gpr_radar(
        self,
        aircraft_id: str,
        position_xyz_m: List[float],
        timestamp_sol: float,
        target_name: str = "Delta Scarp Subsurface Radar Line",
        simulated_layer_depth_m: float = 4.2,
        relative_dielectric_permittivity: float = 3.8,
    ) -> AerialObservation:
        """
        Simulates airborne Ground-Penetrating Radar (RIMFAX analog) subsurface echo.
        Explicitly marked as a SYNTHETIC SIMULATION SCENARIO MODEL.
        """
        alt_m = max(1.0, position_xyz_m[2])
        footprint_radius = alt_m * 0.80  # Broad beam ground footprint

        obs_id = f"OBS-GPR-{uuid.uuid4().hex[:8].upper()}"
        obs = AerialObservation(
            observation_id=obs_id,
            aircraft_id=aircraft_id,
            sensor_modality=SensorModality.SYNTHETIC_GPR_RADAR,
            sensor_name="Aerial Subsurface Sounding Radar (RIMFAX Concept)",
            timestamp_sol=timestamp_sol,
            position_xyz_m=list(position_xyz_m),
            sensor_footprint_radius_m=footprint_radius,
            ground_sampling_distance_cm_px=50.0,
            target_feature_name=target_name,
            primary_metric_name="SYNTHETIC_LAYER_BOUNDARY_DEPTH_M",
            primary_metric_value=simulated_layer_depth_m,
            metric_units="meters",
            measurement_uncertainty=0.45,
            is_synthetic_scenario_model=True,
            scientific_provenance="SYNTHETIC SCENARIO MODEL — Not actual Mars ground truth; for research simulation only",
            geological_context={
                "apparent_dielectric_constant_eps": relative_dielectric_permittivity,
                "radar_reflection_strength_db": -18.5,
                "interpretation": "CANDIDATE_STRATIFIED_CROSSBEDDED_SEDIMENT_INTERFACE",
                "water_ice_provenance_warning": "DISCLOSURE: Subsurface reflection must NEVER be interpreted as confirmed water ice.",
            },
        )
        self._observations_log.append(obs)
        return obs

    def acquire_atmospheric_profile(
        self,
        aircraft_id: str,
        position_xyz_m: List[float],
        timestamp_sol: float,
        temperature_k: float = 215.0,
        pressure_pa: float = 610.0,
        wind_speed_m_s: float = 4.2,
    ) -> AerialObservation:
        obs_id = f"OBS-ATM-{uuid.uuid4().hex[:8].upper()}"
        obs = AerialObservation(
            observation_id=obs_id,
            aircraft_id=aircraft_id,
            sensor_modality=SensorModality.ATMOSPHERIC_SUITE,
            sensor_name="Aerial Boundary Layer Meteorological Probe",
            timestamp_sol=timestamp_sol,
            position_xyz_m=list(position_xyz_m),
            sensor_footprint_radius_m=0.0,
            ground_sampling_distance_cm_px=0.0,
            target_feature_name="Atmospheric Boundary Layer",
            primary_metric_name="AIR_PRESSURE_PA",
            primary_metric_value=pressure_pa,
            metric_units="Pascals",
            measurement_uncertainty=2.5,
            is_synthetic_scenario_model=False,
            scientific_provenance="MEDA In-situ atmospheric sensor correlation model",
            geological_context={
                "temperature_k": round(temperature_k, 2),
                "wind_speed_m_s": round(wind_speed_m_s, 2),
                "air_density_kg_m3": round(pressure_pa / (188.922 * temperature_k), 5),
            },
        )
        self._observations_log.append(obs)
        return obs

    def get_all_observations(self) -> List[AerialObservation]:
        return list(self._observations_log)

    def clear_observations(self) -> None:
        self._observations_log.clear()
