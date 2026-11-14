"""
MarsWalk 2.0 / Project Atlas — Milestone 13L: Spatiotemporal Environmental Field Model.

Provides 2D/3D raster representations of continuous and discrete environmental variables
across Jezero Crater, with coordinate bounds checking, sub-pixel bilinear sampling,
and strict preservation of NoData boundaries.
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


class FieldState(str, enum.Enum):
    """Integrity state of an environmental field sample."""
    VALID = "VALID"
    ESTIMATED = "ESTIMATED"
    INTERPOLATED = "INTERPOLATED"
    EXTRAPOLATED = "EXTRAPOLATED"
    NO_DATA = "NO_DATA"
    INVALID = "INVALID"
    OUTSIDE_SOURCE_COVERAGE = "OUTSIDE_SOURCE_COVERAGE"


class FieldSamplingMethod(str, enum.Enum):
    """Sampling interpolation methodology."""
    NEAREST = "NEAREST"
    BILINEAR = "BILINEAR"


@dataclass
class EnvironmentalField2D:
    """
    Continuous 2D spatial raster layer representing an environmental parameter
    over the Jezero Crater regional grid.
    """
    parameter_name: str
    units: str
    data: np.ndarray  # Shape: [H, W], float32 or float64
    valid_mask: np.ndarray  # Shape: [H, W], boolean (True = valid, False = NoData)
    product_id: str
    sol: int = 1
    ltst_hours: float = 12.0
    dx_ground_m: float = 18.972887
    dy_ground_m: float = 20.000000
    ref_lat_deg: float = 18.442

    def __post_init__(self) -> None:
        if self.data.shape != self.valid_mask.shape:
            raise ValueError(
                f"Data shape {self.data.shape} does not match valid_mask shape {self.valid_mask.shape}"
            )

    @property
    def height(self) -> int:
        return self.data.shape[0]

    @property
    def width(self) -> int:
        return self.data.shape[1]

    def sample(
        self,
        row: float,
        col: float,
        method: FieldSamplingMethod = FieldSamplingMethod.BILINEAR,
    ) -> Tuple[Optional[float], FieldState]:
        """
        Sample the environmental parameter at sub-pixel floating-point coordinates.
        Preserves NoData masks: if any required corner is invalid, rejects sample as NO_DATA.
        """
        # 1. Bounds check
        if row < 0.0 or row > (self.height - 1) or col < 0.0 or col > (self.width - 1):
            return None, FieldState.OUTSIDE_SOURCE_COVERAGE

        # 2. Nearest neighbor sampling
        if method == FieldSamplingMethod.NEAREST:
            r_idx = int(round(row))
            c_idx = int(round(col))
            r_idx = min(max(r_idx, 0), self.height - 1)
            c_idx = min(max(c_idx, 0), self.width - 1)

            if not self.valid_mask[r_idx, c_idx]:
                return None, FieldState.NO_DATA
            val = float(self.data[r_idx, c_idx])
            if math.isnan(val) or math.isinf(val):
                return None, FieldState.INVALID
            return val, FieldState.VALID

        # 3. Sub-pixel Bilinear sampling
        r0 = int(math.floor(row))
        c0 = int(math.floor(col))
        r1 = min(r0 + 1, self.height - 1)
        c1 = min(c0 + 1, self.width - 1)

        # Exact pixel center or corner hit
        if r0 == r1 and c0 == c1:
            if not self.valid_mask[r0, c0]:
                return None, FieldState.NO_DATA
            val = float(self.data[r0, c0])
            return val, FieldState.VALID

        # Verify all bounding corners are valid (prevent interpolation across NoData edges)
        corners = [(r0, c0), (r0, c1), (r1, c0), (r1, c1)]
        for r_c, c_c in corners:
            if not self.valid_mask[r_c, c_c]:
                return None, FieldState.NO_DATA

        dr = row - r0
        dc = col - c0

        v00 = float(self.data[r0, c0])
        v01 = float(self.data[r0, c1])
        v10 = float(self.data[r1, c0])
        v11 = float(self.data[r1, c1])

        # Bilinear interpolation equation
        top = v00 * (1.0 - dc) + v01 * dc
        bot = v10 * (1.0 - dc) + v11 * dc
        val = top * (1.0 - dr) + bot * dr

        if math.isnan(val) or math.isinf(val):
            return None, FieldState.INVALID

        return float(round(val, 4)), FieldState.INTERPOLATED

    def summary(self) -> Dict[str, Any]:
        """Compute statistical summary over valid cells."""
        valid_data = self.data[self.valid_mask]
        valid_count = int(np.count_nonzero(self.valid_mask))
        total_cells = self.height * self.width
        nodata_count = total_cells - valid_count

        if valid_count == 0:
            return {
                "parameter_name": self.parameter_name,
                "units": self.units,
                "product_id": self.product_id,
                "total_cells": total_cells,
                "valid_cells": 0,
                "nodata_cells": nodata_count,
                "min": None,
                "max": None,
                "mean": None,
                "coverage_pct": 0.0,
            }

        return {
            "parameter_name": self.parameter_name,
            "units": self.units,
            "product_id": self.product_id,
            "total_cells": total_cells,
            "valid_cells": valid_count,
            "nodata_cells": nodata_count,
            "min": float(round(np.min(valid_data), 3)),
            "max": float(round(np.max(valid_data), 3)),
            "mean": float(round(np.mean(valid_data), 3)),
            "coverage_pct": float(round((valid_count / total_cells) * 100.0, 2)),
        }
