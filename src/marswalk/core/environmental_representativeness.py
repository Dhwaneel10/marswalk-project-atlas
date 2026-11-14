"""
MarsWalk 2.0 / Project Atlas - Environmental Representativeness Engine
Evaluates spatial, temporal, seasonal, and vertical representativeness of planetary observations
relative to rover planning targets, computing the Composite Representativeness Index (CRI).
"""

from __future__ import annotations
import math
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

from marswalk.core.mars_observation_normalizer import MARS_RADIUS_EQUATORIAL_M


class RepresentativenessClass(str, Enum):
    DIRECT_LOCAL_MATCH = "DIRECT_LOCAL_MATCH"
    NEARBY_CONTEXTUAL_MATCH = "NEARBY_CONTEXTUAL_MATCH"
    REGIONAL_MODEL_CONTEXT = "REGIONAL_MODEL_CONTEXT"
    SEASONAL_CLIMATOLOGY_CONTEXT = "SEASONAL_CLIMATOLOGY_CONTEXT"
    NON_COMPARABLE = "NON_COMPARABLE"


@dataclass
class RepresentativenessAssessment:
    observation_id: str
    target_id: str
    classification: str
    composite_index: float  # [0.0, 1.0]
    spatial_score: float
    temporal_score: float
    seasonal_score: float
    vertical_score: float
    distance_km: float
    delta_ltst_hours: float
    delta_ls_deg: float
    delta_elevation_m: float
    confidence_verdict: str
    disclaimer: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PlanetaryRepresentativenessEngine:
    """Evaluates the multi-dimensional representativeness of observational data."""

    def __init__(
        self,
        spatial_scale_km: float = 15.0,
        temporal_scale_hours: float = 1.5,
        seasonal_scale_ls_deg: float = 15.0,
        vertical_scale_m: float = 300.0
    ):
        self.spatial_scale_km = spatial_scale_km
        self.temporal_scale_hours = temporal_scale_hours
        self.seasonal_scale_ls_deg = seasonal_scale_ls_deg
        self.vertical_scale_m = vertical_scale_m

    def compute_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi, dlam = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return (MARS_RADIUS_EQUATORIAL_M * c) / 1000.0

    def evaluate_representativeness(
        self,
        obs_id: str,
        obs_lat: float,
        obs_lon: float,
        obs_elev_m: float,
        obs_ltst_h: float,
        obs_ls_deg: float,
        target_id: str,
        target_lat: float,
        target_lon: float,
        target_elev_m: float,
        target_ltst_h: float,
        target_ls_deg: float
    ) -> RepresentativenessAssessment:
        # 1. Distances and deltas
        d_km = self.compute_distance_km(obs_lat, obs_lon, target_lat, target_lon)
        d_ltst = abs((target_ltst_h % 24.0) - (obs_ltst_h % 24.0))
        if d_ltst > 12.0:
            d_ltst = 24.0 - d_ltst
        d_ls = abs((target_ls_deg % 360.0) - (obs_ls_deg % 360.0))
        if d_ls > 180.0:
            d_ls = 360.0 - d_ls
        d_elev = abs(target_elev_m - obs_elev_m)

        # 2. Sub-scores [0.0, 1.0]
        s_spatial = float(math.exp(-d_km / self.spatial_scale_km))
        s_temporal = float(math.exp(-d_ltst / self.temporal_scale_hours))
        s_seasonal = float(math.exp(-d_ls / self.seasonal_scale_ls_deg))
        s_vertical = float(math.exp(-d_elev / self.vertical_scale_m))

        cri = float(s_spatial * s_temporal * s_seasonal * s_vertical)

        # 3. Classification
        if d_ls > 60.0 or d_elev > 600.0:
            cls = RepresentativenessClass.NON_COMPARABLE.value
            verdict = "NON_COMPARABLE_INCOMPATIBLE"
            disc = "Observation and target are physically incompatible (different season, elevation or region)."
        elif d_km <= 5.0 and d_ltst <= 0.5 and d_ls <= 5.0 and d_elev <= 100.0:
            cls = RepresentativenessClass.DIRECT_LOCAL_MATCH.value
            verdict = "HIGH_CONFIDENCE_IN_SITU"
            disc = "Observation matches rover target coordinates within in-situ operational tolerances."
        elif d_km <= 25.0 and d_ltst <= 1.5 and d_ls <= 15.0 and d_elev <= 400.0:
            cls = RepresentativenessClass.NEARBY_CONTEXTUAL_MATCH.value
            verdict = "MODERATE_CONTEXTUAL_MATCH"
            disc = "Observation is within Jezero crater basin; local topographic or slope microclimate variance may apply."
        elif d_km <= 150.0:
            cls = RepresentativenessClass.REGIONAL_MODEL_CONTEXT.value
            verdict = "REGIONAL_SCALE_APPROXIMATION"
            disc = "Observation or model provides regional climatology, not microclimate terrain conditions."
        elif d_ls <= 30.0:
            cls = RepresentativenessClass.SEASONAL_CLIMATOLOGY_CONTEXT.value
            verdict = "SEASONAL_ANALOGUE"
            disc = "Temporal or spatial discrepancy exists; represents seasonal climatological expectation."
        else:
            cls = RepresentativenessClass.NON_COMPARABLE.value
            verdict = "NON_COMPARABLE_INCOMPATIBLE"
            disc = "Observation and target are physically incompatible (different season, elevation or region)."

        return RepresentativenessAssessment(
            observation_id=obs_id,
            target_id=target_id,
            classification=cls,
            composite_index=round(cri, 4),
            spatial_score=round(s_spatial, 4),
            temporal_score=round(s_temporal, 4),
            seasonal_score=round(s_seasonal, 4),
            vertical_score=round(s_vertical, 4),
            distance_km=round(d_km, 2),
            delta_ltst_hours=round(d_ltst, 2),
            delta_ls_deg=round(d_ls, 2),
            delta_elevation_m=round(d_elev, 1),
            confidence_verdict=verdict,
            disclaimer=disc
        )
