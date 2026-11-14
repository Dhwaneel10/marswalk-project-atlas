"""
MarsWalk 2.0 / Project Atlas - Environmental Field Update & Data Fusion Engine
Generates layered, non-destructive environmental field products:
Level A: Unmodified Background Field (MCD 6.2 GCM / 13L Physical Model)
Level B: Empirical Residual Field (Observation - Model at traverse points)
Level C: Assimilated / Fused Field Product (Background + Confidence-Weighted Local Residual)
Strict scientific rule: Background is NEVER overwritten. Provenance and uncertainty are fully preserved.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from marswalk.core.mars_observation_normalizer import JEZERO_DTM_ROWS, JEZERO_DTM_COLS, coordinates_to_jezero_dtm_pixel
from marswalk.core.mars_environment_collocation import CollocatedObservationModelPair


@dataclass
class AssimilatedFieldProduct:
    product_id: str
    parameter_name: str
    unit: str
    grid_rows: int
    grid_cols: int
    cell_size_m: float
    sol: int
    ltst_hours: float
    solar_longitude_ls_deg: float
    background_model: str
    observation_count_assimilated: int
    background_mean: float
    background_min: float
    background_max: float
    assimilated_mean: float
    assimilated_min: float
    assimilated_max: float
    max_assimilation_adjustment: float
    confidence_weight_mean: float
    background_grid: List[List[float]]
    residual_grid: List[List[float]]
    assimilated_grid: List[List[float]]
    confidence_grid: List[List[float]]
    provenance_classification: str
    scientific_disclaimer: str

    def to_dict(self, include_grids: bool = True) -> Dict[str, Any]:
        d = asdict(self)
        if not include_grids:
            d["background_grid"] = f"<{self.grid_rows}x{self.grid_cols} array omitted>"
            d["residual_grid"] = f"<{self.grid_rows}x{self.grid_cols} array omitted>"
            d["assimilated_grid"] = f"<{self.grid_rows}x{self.grid_cols} array omitted>"
            d["confidence_grid"] = f"<{self.grid_rows}x{self.grid_cols} array omitted>"
        return d


class EnvironmentFieldFusionEngine:
    """Fuses model backgrounds with in-situ observations using localized confidence weighting."""

    def __init__(self, influence_radius_pixels: float = 35.0):
        # 35 pixels at 20m/pixel = 700 meters local thermal footprint
        self.influence_radius_pixels = influence_radius_pixels

    def generate_assimilated_field(
        self,
        parameter_name: str,
        unit: str,
        sol: int,
        ltst_hours: float,
        ls_deg: float,
        background_grid: np.ndarray,
        collocated_pairs: List[CollocatedObservationModelPair],
        background_model_name: str = "ATLAS_13L_BASELINE"
    ) -> AssimilatedFieldProduct:
        h, w = background_grid.shape
        # Filter qualified observation pairs for this parameter
        valid_pairs = [p for p in collocated_pairs if p.parameter_name == parameter_name and p.gate_status == "COLLOCATION_QUALIFIED"]

        residual_grid = np.zeros((h, w), dtype=np.float32)
        confidence_grid = np.zeros((h, w), dtype=np.float32)

        if valid_pairs:
            # Extract observation pixel coordinates and residuals (Observed - Model)
            # Note: Collocated pair has residual = Model - Observed.
            # Here we want correction: delta = Observed - Model = -residual
            obs_rows = []
            obs_cols = []
            obs_deltas = []

            for p in valid_pairs:
                r, c, _, _ = coordinates_to_jezero_dtm_pixel(18.4447, 77.4508)
                # Correction to add to background
                delta = -p.residual
                obs_rows.append(r)
                obs_cols.append(c)
                obs_deltas.append(delta)

            # Build distance-weighted residual and confidence fields
            yy, xx = np.mgrid[0:h, 0:w]
            num_accum = np.zeros((h, w), dtype=np.float32)
            den_accum = np.zeros((h, w), dtype=np.float32)
            max_conf = np.zeros((h, w), dtype=np.float32)

            for r_obs, c_obs, delta in zip(obs_rows, obs_cols, obs_deltas):
                dist_sq = (yy - r_obs)**2 + (xx - c_obs)**2
                # Gaussian kernel
                w_k = np.exp(-dist_sq / (2.0 * (self.influence_radius_pixels**2)))
                num_accum += w_k * delta
                den_accum += w_k
                max_conf = np.maximum(max_conf, w_k)

            mask = den_accum > 1e-4
            residual_grid[mask] = num_accum[mask] / den_accum[mask]
            confidence_grid = max_conf

        # Level C: Fused Field
        assimilated_grid = background_grid + confidence_grid * residual_grid

        bg_mean = float(np.mean(background_grid))
        bg_min = float(np.min(background_grid))
        bg_max = float(np.max(background_grid))

        as_mean = float(np.mean(assimilated_grid))
        as_min = float(np.min(assimilated_grid))
        as_max = float(np.max(assimilated_grid))

        max_adj = float(np.max(np.abs(assimilated_grid - background_grid)))
        conf_mean = float(np.mean(confidence_grid))

        return AssimilatedFieldProduct(
            product_id=f"ASSIM_{parameter_name.upper()}_SOL_{sol:04d}",
            parameter_name=parameter_name,
            unit=unit,
            grid_rows=h,
            grid_cols=w,
            cell_size_m=20.0,
            sol=sol,
            ltst_hours=round(ltst_hours, 2),
            solar_longitude_ls_deg=round(ls_deg, 2),
            background_model=background_model_name,
            observation_count_assimilated=len(valid_pairs),
            background_mean=round(bg_mean, 2),
            background_min=round(bg_min, 2),
            background_max=round(bg_max, 2),
            assimilated_mean=round(as_mean, 2),
            assimilated_min=round(as_min, 2),
            assimilated_max=round(as_max, 2),
            max_assimilation_adjustment=round(max_adj, 2),
            confidence_weight_mean=round(conf_mean, 4),
            background_grid=background_grid.round(2).tolist(),
            residual_grid=residual_grid.round(2).tolist(),
            assimilated_grid=assimilated_grid.round(2).tolist(),
            confidence_grid=confidence_grid.round(4).tolist(),
            provenance_classification="DERIVED_DATA_ASSIMILATION_PRODUCT",
            scientific_disclaimer="Assimilated field blends empirical in-situ observations with numerical model background. It represents a modeled spatial interpolation and must not be cited as direct in-situ measurement across unobserved terrain cells."
        )
