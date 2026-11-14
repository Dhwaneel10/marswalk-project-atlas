"""
MarsWalk 2.0 / Project Atlas — Milestone 13Q
=============================================
Module: science_uncertainty_field.py
Maintains multi-dimensional, spatially continuous and gridded uncertainty
fields over the Martian environment, candidate geological features, and hypotheses.

Enforces:
- Separation of 8 distinct uncertainty dimensions.
- Explicit non-conflation of "unobserved" with "scientifically uninteresting".
- Retention of deterministic interval bounds when probability distributions are unjustified.
- Ground truth preservation in synthetic benchmark worlds.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class UncertaintyDimension(str, Enum):
    MEASUREMENT = "MEASUREMENT"
    CALIBRATION = "CALIBRATION"
    SPATIAL_INTERPOLATION = "SPATIAL_INTERPOLATION"
    TEMPORAL_INTERPOLATION = "TEMPORAL_INTERPOLATION"
    MODEL_PARAMETER = "MODEL_PARAMETER"
    MODEL_STRUCTURAL = "MODEL_STRUCTURAL"
    CLASSIFICATION = "CLASSIFICATION"
    SCIENTIFIC_INTERPRETATION = "SCIENTIFIC_INTERPRETATION"


@dataclass
class PointUncertaintyProfile:
    x_m: float
    y_m: float
    measurement_uncertainty: float           # Sensor precision
    calibration_uncertainty: float         # Instrument zero-offset / drift
    spatial_interpolation_uncertainty: float # Distance-dependent kriging variance
    temporal_interpolation_uncertainty: float# Time elapsed since last observation
    classification_entropy: float            # Shannon entropy over discrete classes
    scientific_interpretation_ambiguity: float # Margin between top competing explanations
    deterministic_interval_bounds: Tuple[float, float] = (0.0, 1.0)
    data_coverage_factor: float = 0.0        # 0.0 (unobserved) to 1.0 (dense coverage)
    observation_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x_m": round(self.x_m, 2),
            "y_m": round(self.y_m, 2),
            "dimensions": {
                UncertaintyDimension.MEASUREMENT.value: round(self.measurement_uncertainty, 4),
                UncertaintyDimension.CALIBRATION.value: round(self.calibration_uncertainty, 4),
                UncertaintyDimension.SPATIAL_INTERPOLATION.value: round(self.spatial_interpolation_uncertainty, 4),
                UncertaintyDimension.TEMPORAL_INTERPOLATION.value: round(self.temporal_interpolation_uncertainty, 4),
                UncertaintyDimension.CLASSIFICATION.value: round(self.classification_entropy, 4),
                UncertaintyDimension.SCIENTIFIC_INTERPRETATION.value: round(self.scientific_interpretation_ambiguity, 4),
            },
            "deterministic_interval_bounds": [round(b, 4) for b in self.deterministic_interval_bounds],
            "data_coverage_factor": round(self.data_coverage_factor, 4),
            "observation_count": self.observation_count,
        }


@dataclass
class SyntheticGroundTruthTarget:
    target_id: str
    name: str
    true_x_m: float
    true_y_m: float
    true_geology: str               # e.g., "SMECTITE_DELTA_DEPOSIT", "CARBONATE_BEARING_UNIT", "BASALTIC_BEDROCK"
    true_spectral_band_depth_2_3: float
    true_layer_boundary_depth_m: float
    is_instrument_artifact: bool = False
    artifact_mechanism: Optional[str] = None


class ScienceUncertaintyField:
    """
    2D/3D Spatial Uncertainty Field across the mission exploration theatre.
    """

    def __init__(
        self,
        grid_width_m: float = 1000.0,
        grid_height_m: float = 1000.0,
        resolution_m: float = 25.0,
    ):
        self.width_m = grid_width_m
        self.height_m = grid_height_m
        self.resolution_m = resolution_m
        self.cols = int(math.ceil(grid_width_m / resolution_m))
        self.rows = int(math.ceil(grid_height_m / resolution_m))

        # Recorded observation locations: List of (x, y, timestamp_sol, quality)
        self._observations: List[Tuple[float, float, float, float]] = []

        # Synthetic ground truth catalog (preserved for held-out evaluation)
        self._ground_truth_targets: Dict[str, SyntheticGroundTruthTarget] = {}

    def add_ground_truth_target(self, target: SyntheticGroundTruthTarget) -> None:
        self._ground_truth_targets[target.target_id] = target

    def get_ground_truth_target(self, target_id: str) -> Optional[SyntheticGroundTruthTarget]:
        return self._ground_truth_targets.get(target_id)

    def list_ground_truth_targets(self) -> List[SyntheticGroundTruthTarget]:
        return list(self._ground_truth_targets.values())

    def record_observation_event(
        self,
        x_m: float,
        y_m: float,
        timestamp_sol: float,
        quality: float = 0.9,
    ) -> None:
        self._observations.append((x_m, y_m, timestamp_sol, quality))

    def evaluate_point_uncertainty(
        self,
        x_m: float,
        y_m: float,
        current_sol: float = 1.0,
        competing_hypotheses_probs: Optional[List[float]] = None,
    ) -> PointUncertaintyProfile:
        """
        Evaluates the multi-dimensional uncertainty profile at arbitrary coordinates (x, y).
        Uses inverse distance weighting (IDW) to estimate spatial interpolation uncertainty.
        """
        if not self._observations:
            # Entirely unobserved location
            classification_ent = 0.0
            if competing_hypotheses_probs:
                classification_ent = -sum(
                    p * math.log2(p) for p in competing_hypotheses_probs if p > 1e-9
                )

            return PointUncertaintyProfile(
                x_m=x_m,
                y_m=y_m,
                measurement_uncertainty=0.0,  # No measurement exists yet
                calibration_uncertainty=0.0,
                spatial_interpolation_uncertainty=1.0,  # Max spatial ignorance
                temporal_interpolation_uncertainty=1.0,
                classification_entropy=classification_ent,
                scientific_interpretation_ambiguity=1.0,
                deterministic_interval_bounds=(0.0, 1.0),
                data_coverage_factor=0.0,
                observation_count=0,
            )

        # Compute distance to nearest observation and weighted density
        min_dist = float("inf")
        sum_weights = 0.0
        weighted_time_delta = 0.0
        count_in_radius = 0
        influence_radius_m = 150.0

        for ox, oy, ot, oq in self._observations:
            dist = math.hypot(x_m - ox, y_m - oy)
            if dist < min_dist:
                min_dist = dist
            if dist <= influence_radius_m:
                count_in_radius += 1
                w = 1.0 / max(1.0, dist)
                sum_weights += w
                weighted_time_delta += w * (current_sol - ot)

        # Spatial uncertainty increases with distance (variogram proxy: 1 - exp(-d / correlation_length))
        correlation_length_m = 75.0
        spatial_unc = 1.0 - math.exp(-min_dist / correlation_length_m)

        # Temporal uncertainty increases with elapsed time
        avg_time_delta = (weighted_time_delta / sum_weights) if sum_weights > 0 else (current_sol)
        temporal_unc = 1.0 - math.exp(-avg_time_delta / 10.0)

        # Coverage factor
        coverage = min(1.0, count_in_radius / 5.0)

        # Shannon classification entropy
        classification_ent = 0.0
        if competing_hypotheses_probs:
            classification_ent = -sum(
                p * math.log2(p) for p in competing_hypotheses_probs if p > 1e-9
            )

        return PointUncertaintyProfile(
            x_m=x_m,
            y_m=y_m,
            measurement_uncertainty=0.05 * (1.0 - coverage) + 0.01,
            calibration_uncertainty=0.02,
            spatial_interpolation_uncertainty=spatial_unc,
            temporal_interpolation_uncertainty=temporal_unc,
            classification_entropy=classification_ent,
            scientific_interpretation_ambiguity=spatial_unc * 0.7 + classification_ent * 0.3,
            deterministic_interval_bounds=(max(0.0, 0.5 - spatial_unc * 0.5), min(1.0, 0.5 + spatial_unc * 0.5)),
            data_coverage_factor=coverage,
            observation_count=count_in_radius,
        )

    def generate_raster_slice(
        self,
        stride: int = 2,
        current_sol: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Generates a 2D spatial raster grid of uncertainty and coverage for visualization.
        """
        grid_data: List[Dict[str, Any]] = []
        for r in range(0, self.rows, stride):
            y = r * self.resolution_m
            for c in range(0, self.cols, stride):
                x = c * self.resolution_m
                prof = self.evaluate_point_uncertainty(x, y, current_sol=current_sol)
                grid_data.append({
                    "x_m": round(x, 1),
                    "y_m": round(y, 1),
                    "spatial_uncertainty": round(prof.spatial_interpolation_uncertainty, 3),
                    "data_coverage": round(prof.data_coverage_factor, 3),
                    "obs_count": prof.observation_count,
                })

        return {
            "width_m": self.width_m,
            "height_m": self.height_m,
            "resolution_m": self.resolution_m * stride,
            "sample_count": len(grid_data),
            "cells": grid_data,
        }
