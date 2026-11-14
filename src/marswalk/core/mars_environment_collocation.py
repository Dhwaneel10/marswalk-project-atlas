"""
MarsWalk 2.0 / Project Atlas - Observation Collocation Engine
Collocates in-situ planetary observations (Perseverance MEDA) and orbital soundings (MRO MCS)
with numerical models (MCD 6.2 GCM) and Atlas 13L Environmental Field Models under strict physical tolerances.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

from marswalk.core.mars_observation_normalizer import (
    coordinates_to_jezero_dtm_pixel, MARS_RADIUS_EQUATORIAL_M
)
from marswalk.core.planetary_archive_ingestion import NormalizedObservationRecord, PlanetaryArchiveIngestor


class CollocationGateStatus(str, Enum):
    QUALIFIED = "COLLOCATION_QUALIFIED"
    EXCEEDS_SPATIAL_TOLERANCE = "EXCEEDS_SPATIAL_TOLERANCE"
    EXCEEDS_TEMPORAL_TOLERANCE = "EXCEEDS_TEMPORAL_TOLERANCE"
    EXCEEDS_SEASONAL_TOLERANCE = "EXCEEDS_SEASONAL_TOLERANCE"
    ALTITUDE_MISMATCH = "ALTITUDE_MISMATCH"
    SENSOR_FLAGGED_OR_NULL = "SENSOR_FLAGGED_OR_NULL"


@dataclass
class CollocatedObservationModelPair:
    pair_id: str
    parameter_name: str
    unit: str
    sol: int
    observation_id: str
    observed_value: float
    observed_uncertainty_1sigma: Optional[float]
    model_name: str
    model_value: float
    residual: float  # Model - Observed
    relative_error_pct: Optional[float]
    spatial_separation_km: float
    delta_ltst_hours: float
    delta_ls_deg: float
    gate_status: str
    rejection_reason: Optional[str]
    representativeness_class: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EnvironmentCollocationEngine:
    """Rigorous collocation between observations and environmental models."""

    def __init__(
        self,
        max_spatial_separation_km: float = 50.0,
        max_temporal_delta_hours: float = 0.5,
        max_seasonal_delta_ls_deg: float = 5.0
    ):
        self.max_spatial_separation_km = max_spatial_separation_km
        self.max_temporal_delta_hours = max_temporal_delta_hours
        self.max_seasonal_delta_ls_deg = max_seasonal_delta_ls_deg

    def compute_great_circle_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine distance on IAU Mars Spheroid."""
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return (MARS_RADIUS_EQUATORIAL_M * c) / 1000.0

    def collocate_observation_with_mcd(
        self,
        obs: NormalizedObservationRecord,
        ingestor: PlanetaryArchiveIngestor
    ) -> CollocatedObservationModelPair:
        """
        Collocate a single NormalizedObservationRecord with the MCD 6.2 NetCDF climatology.
        Evaluates spatial distance to Jezero model cell, diurnal LTST alignment, and seasonal Ls alignment.
        """
        # 1. Check if observation is valid
        if obs.observed_value is None or obs.quality_status not in ["NOMINAL", "CALIBRATED"]:
            return CollocatedObservationModelPair(
                pair_id=f"COLLOC_MCD_{obs.observation_id}",
                parameter_name=obs.parameter_name,
                unit=obs.unit,
                sol=obs.sol,
                observation_id=obs.observation_id,
                observed_value=0.0,
                observed_uncertainty_1sigma=obs.uncertainty_1sigma,
                model_name="MCD_6_2_GCM",
                model_value=0.0,
                residual=0.0,
                relative_error_pct=None,
                spatial_separation_km=0.0,
                delta_ltst_hours=0.0,
                delta_ls_deg=0.0,
                gate_status=CollocationGateStatus.SENSOR_FLAGGED_OR_NULL.value,
                rejection_reason=f"Observation status is {obs.quality_status}: {obs.rejection_reason}",
                representativeness_class="NON_COMPARABLE"
            )

        # 2. Query MCD model prediction at exact Ls and LTST
        pred = ingestor.get_mcd_model_prediction(
            ls_deg=obs.solar_longitude_ls_deg,
            ltst_hours=obs.ltst_hours,
            lat_deg=obs.lat_deg,
            lon_deg=obs.lon_deg
        )

        model_val: Optional[float] = None
        if obs.parameter_name == "ground_temperature":
            model_val = pred["ground_temp_k"]
        elif obs.parameter_name == "air_temperature":
            model_val = pred["air_temp_k"]
        elif obs.parameter_name == "atmospheric_pressure":
            model_val = pred["pressure_pa"]
        elif obs.parameter_name == "optical_depth_tau":
            model_val = pred["optical_depth_tau"]

        if model_val is None:
            return CollocatedObservationModelPair(
                pair_id=f"COLLOC_MCD_{obs.observation_id}",
                parameter_name=obs.parameter_name,
                unit=obs.unit,
                sol=obs.sol,
                observation_id=obs.observation_id,
                observed_value=obs.observed_value,
                observed_uncertainty_1sigma=obs.uncertainty_1sigma,
                model_name="MCD_6_2_GCM",
                model_value=0.0,
                residual=0.0,
                relative_error_pct=None,
                spatial_separation_km=0.0,
                delta_ltst_hours=0.0,
                delta_ls_deg=0.0,
                gate_status=CollocationGateStatus.ALTITUDE_MISMATCH.value,
                rejection_reason=f"Parameter {obs.parameter_name} not available in MCD prediction",
                representativeness_class="NON_COMPARABLE"
            )

        # 3. Spatial separation to central model cell (18.44N, 77.45E)
        sep_km = self.compute_great_circle_distance_km(obs.lat_deg, obs.lon_deg, 18.4447, 77.4508)
        # In bilinear interpolation, delta_ltst and delta_ls are matched exactly
        delta_ltst = 0.0
        delta_ls = 0.0

        # Physical gate screening
        gate_status = CollocationGateStatus.QUALIFIED.value
        rejection_reason = None

        if sep_km > self.max_spatial_separation_km:
            gate_status = CollocationGateStatus.EXCEEDS_SPATIAL_TOLERANCE.value
            rejection_reason = f"Distance {sep_km:.1f} km exceeds {self.max_spatial_separation_km} km threshold"

        residual = float(round(model_val - obs.observed_value, 3))
        rel_err = float(round(abs(residual) / abs(obs.observed_value) * 100.0, 2)) if obs.observed_value != 0 else None

        # Classify representativeness
        rep_class = "DIRECT_LOCAL_MATCH" if sep_km < 5.0 else "REGIONAL_MODEL_CONTEXT"

        return CollocatedObservationModelPair(
            pair_id=f"COLLOC_MCD_{obs.observation_id}",
            parameter_name=obs.parameter_name,
            unit=obs.unit,
            sol=obs.sol,
            observation_id=obs.observation_id,
            observed_value=float(round(obs.observed_value, 2)),
            observed_uncertainty_1sigma=obs.uncertainty_1sigma,
            model_name="MCD_6_2_GCM",
            model_value=float(round(model_val, 2)),
            residual=residual,
            relative_error_pct=rel_err,
            spatial_separation_km=float(round(sep_km, 2)),
            delta_ltst_hours=delta_ltst,
            delta_ls_deg=delta_ls,
            gate_status=gate_status,
            rejection_reason=rejection_reason,
            representativeness_class=rep_class
        )

    def collocate_observation_with_atlas_13l(
        self,
        obs: NormalizedObservationRecord,
        atlas_baseline_t_mean: float = 218.0,
        atlas_baseline_t_amp: float = 38.0,
        atlas_elevation_lapse: float = -4.5,
        atlas_baseline_p0: float = 610.0,
        atlas_scale_height: float = 11100.0
    ) -> CollocatedObservationModelPair:
        """
        Collocate a single NormalizedObservationRecord with the 13L Environmental Baseline Model.
        Uses the 13L asymmetric cosine diurnal temperature spline and hydrostatic pressure curve.
        """
        if obs.observed_value is None or obs.quality_status not in ["NOMINAL", "CALIBRATED"]:
            return CollocatedObservationModelPair(
                pair_id=f"COLLOC_13L_{obs.observation_id}",
                parameter_name=obs.parameter_name,
                unit=obs.unit,
                sol=obs.sol,
                observation_id=obs.observation_id,
                observed_value=0.0,
                observed_uncertainty_1sigma=obs.uncertainty_1sigma,
                model_name="ATLAS_13L_BASELINE",
                model_value=0.0,
                residual=0.0,
                relative_error_pct=None,
                spatial_separation_km=0.0,
                delta_ltst_hours=0.0,
                delta_ls_deg=0.0,
                gate_status=CollocationGateStatus.SENSOR_FLAGGED_OR_NULL.value,
                rejection_reason=f"Observation status is {obs.quality_status}: {obs.rejection_reason}",
                representativeness_class="NON_COMPARABLE"
            )

        hr = obs.ltst_hours % 24.0
        elev_km = (obs.elevation_m - (-2500.0)) / 1000.0  # Elevation relative to Jezero floor datum

        model_val: Optional[float] = None

        if obs.parameter_name in ["ground_temperature", "air_temperature"]:
            # 13L Asymmetric diurnal spline
            if hr < 5.5:
                phase = (hr + 10.5) / 16.0
                swing = -atlas_baseline_t_amp + 8.0 * math.cos(math.pi * phase)
            elif hr <= 13.0:
                phase = (hr - 5.5) / 7.5
                swing = -atlas_baseline_t_amp + (2.0 * atlas_baseline_t_amp) * math.sin(math.pi * phase * 0.5)
            else:
                phase = (hr - 13.0) / 16.5
                swing = atlas_baseline_t_amp * math.cos(math.pi * phase * 0.7)

            t_gnd_k = atlas_baseline_t_mean + swing + atlas_elevation_lapse * elev_km
            if obs.parameter_name == "ground_temperature":
                model_val = t_gnd_k
            else:
                # Mast air temperature offset
                model_val = t_gnd_k - 4.5 if 8.0 <= hr <= 17.0 else t_gnd_k + 2.5

        elif obs.parameter_name == "atmospheric_pressure":
            # 13L Barometric formula with scale height
            # P(z) = P0 * exp(-z / H)
            model_val = atlas_baseline_p0 * math.exp(-obs.elevation_m / atlas_scale_height)
            # Add diurnal semi-diurnal tide approximation
            model_val -= 15.0 * math.cos(2.0 * math.pi * (hr - 9.0) / 24.0)

        elif obs.parameter_name == "optical_depth_tau":
            # 13L fixed baseline tau
            model_val = 0.45

        if model_val is None:
            return CollocatedObservationModelPair(
                pair_id=f"COLLOC_13L_{obs.observation_id}",
                parameter_name=obs.parameter_name,
                unit=obs.unit,
                sol=obs.sol,
                observation_id=obs.observation_id,
                observed_value=obs.observed_value,
                observed_uncertainty_1sigma=obs.uncertainty_1sigma,
                model_name="ATLAS_13L_BASELINE",
                model_value=0.0,
                residual=0.0,
                relative_error_pct=None,
                spatial_separation_km=0.0,
                delta_ltst_hours=0.0,
                delta_ls_deg=0.0,
                gate_status=CollocationGateStatus.ALTITUDE_MISMATCH.value,
                rejection_reason=f"Parameter {obs.parameter_name} not modeled in 13L baseline",
                representativeness_class="NON_COMPARABLE"
            )

        sep_km = self.compute_great_circle_distance_km(obs.lat_deg, obs.lon_deg, 18.4447, 77.4508)
        residual = float(round(model_val - obs.observed_value, 3))
        rel_err = float(round(abs(residual) / abs(obs.observed_value) * 100.0, 2)) if obs.observed_value != 0 else None

        return CollocatedObservationModelPair(
            pair_id=f"COLLOC_13L_{obs.observation_id}",
            parameter_name=obs.parameter_name,
            unit=obs.unit,
            sol=obs.sol,
            observation_id=obs.observation_id,
            observed_value=float(round(obs.observed_value, 2)),
            observed_uncertainty_1sigma=obs.uncertainty_1sigma,
            model_name="ATLAS_13L_BASELINE",
            model_value=float(round(model_val, 2)),
            residual=residual,
            relative_error_pct=rel_err,
            spatial_separation_km=float(round(sep_km, 2)),
            delta_ltst_hours=0.0,
            delta_ls_deg=0.0,
            gate_status=CollocationGateStatus.QUALIFIED.value,
            rejection_reason=None,
            representativeness_class="DIRECT_LOCAL_MATCH"
        )

    def collocate_dataset(
        self,
        observations: List[NormalizedObservationRecord],
        ingestor: PlanetaryArchiveIngestor,
        model_target: str = "MCD_6_2_GCM"
    ) -> List[CollocatedObservationModelPair]:
        """Collocate a collection of observation records against a target model."""
        pairs: List[CollocatedObservationModelPair] = []
        for obs in observations:
            if model_target == "MCD_6_2_GCM":
                p = self.collocate_observation_with_mcd(obs, ingestor)
            elif model_target == "ATLAS_13L_BASELINE":
                p = self.collocate_observation_with_atlas_13l(obs)
            else:
                continue
            pairs.append(p)
        return pairs
