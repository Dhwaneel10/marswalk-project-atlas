"""
MarsWalk Core Terrain Visibility Engine (Milestone 13D - Atlas Mars RelayNet).

Calculates geometric Line-of-Sight (LOS) visibility between arbitrary Martian surface endpoints
over authentic digital elevation models (DTMs) such as the USGS CTX 20m Jezero Crater mosaic.

Evaluates:
- Horizontal geodesic ground distance D and 3D Euclidean slant range.
- Ray parameterization P(t) = P0 + t*(P1 - P0) and ray altitude h_LOS(t) = Z0 + t*(Z1 - Z0).
- Sub-pixel bilinear elevation sampling with strict NoData sentinel rejection (z <= -9000 m).
- Terrain clearance c(t) = h_LOS(t) - z(t) and first obstruction detection where c(t) <= clearance_margin.
- Separation of geometric visibility from configured maximum RF range limits.
- Scientific disclosures: Geometric LOS does not model RF path loss, Fresnel zones, or atmospheric refraction.
"""

from dataclasses import dataclass, field
import math
from typing import Optional, Tuple, Dict, Any, List
import numpy as np

# Physical constants for IAU Mars 2000 Sphere
MARS_RADIUS_M = 3396190.0
DEFAULT_DX_M = 18.972887  # 20.0 * cos(18.442 deg) at Jezero Crater
DEFAULT_DY_M = 20.000000  # 20.0 m North-South raster spacing
NODATA_THRESHOLD_M = -9000.0  # Sentinel threshold for missing Martian elevation


@dataclass(frozen=True)
class ObstructionPoint:
    """
    Detailed spatial record of first or worst terrain obstruction.
    """
    t: float
    row: float
    col: float
    ground_dist_from_a_m: float
    terrain_elevation_m: float
    los_ray_height_m: float
    clearance_m: float


@dataclass(frozen=True)
class LineOfSightResult:
    """
    Full scientific evaluation of a pairwise geometric Line-of-Sight ray.
    """
    endpoint_a_id: str
    endpoint_b_id: str
    row_a: float
    col_a: float
    row_b: float
    col_b: float
    antenna_h_a_m: float
    antenna_h_b_m: float
    ground_elevation_a_m: Optional[float]
    ground_elevation_b_m: Optional[float]
    total_altitude_a_m: Optional[float]
    total_altitude_b_m: Optional[float]
    ground_distance_m: float
    slant_distance_m: Optional[float]
    min_clearance_m: Optional[float]
    sample_count: int
    sample_interval_m: float
    status: str  # "VISIBLE", "BLOCKED", "OUT_OF_RANGE", "BLOCKED_AND_OUT_OF_RANGE", "UNKNOWN", "INVALID_INPUT"
    is_visible: bool
    is_terrain_blocked: bool
    is_out_of_range: bool
    data_completeness: float
    first_obstruction: Optional[ObstructionPoint]
    max_range_m: Optional[float]
    clearance_margin_m: float
    reason: Optional[str] = None
    source_attribution: str = "USGS MRO CTX 20m Jezero DTM (DOI 10.5066/P906QQT8)"
    scientific_disclaimer: str = (
        "Simplified geometric line-of-sight based on terrain surface intersection. "
        "Does NOT establish actual radio frequency communication, Fresnel zone clearance, "
        "RF path loss, transmitter power, data rate, or operational astronaut safety."
    )

    @property
    def distance_m(self) -> float:
        """Ergonomic alias for ground_distance_m."""
        return self.ground_distance_m

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to JSON-serializable dictionary."""
        obs_dict = None
        if self.first_obstruction is not None:
            obs_dict = {
                "t": round(self.first_obstruction.t, 4),
                "row": round(self.first_obstruction.row, 2),
                "col": round(self.first_obstruction.col, 2),
                "ground_dist_from_a_m": round(self.first_obstruction.ground_dist_from_a_m, 2),
                "terrain_elevation_m": round(self.first_obstruction.terrain_elevation_m, 2),
                "los_ray_height_m": round(self.first_obstruction.los_ray_height_m, 2),
                "clearance_m": round(self.first_obstruction.clearance_m, 2),
            }
        return {
            "endpoint_a_id": self.endpoint_a_id,
            "endpoint_b_id": self.endpoint_b_id,
            "row_a": round(self.row_a, 2),
            "col_a": round(self.col_a, 2),
            "row_b": round(self.row_b, 2),
            "col_b": round(self.col_b, 2),
            "antenna_h_a_m": self.antenna_h_a_m,
            "antenna_h_b_m": self.antenna_h_b_m,
            "ground_elevation_a_m": round(self.ground_elevation_a_m, 2) if self.ground_elevation_a_m is not None else None,
            "ground_elevation_b_m": round(self.ground_elevation_b_m, 2) if self.ground_elevation_b_m is not None else None,
            "total_altitude_a_m": round(self.total_altitude_a_m, 2) if self.total_altitude_a_m is not None else None,
            "total_altitude_b_m": round(self.total_altitude_b_m, 2) if self.total_altitude_b_m is not None else None,
            "ground_distance_m": round(self.ground_distance_m, 2),
            "slant_distance_m": round(self.slant_distance_m, 2) if self.slant_distance_m is not None else None,
            "min_clearance_m": round(self.min_clearance_m, 2) if self.min_clearance_m is not None else None,
            "sample_count": self.sample_count,
            "sample_interval_m": round(self.sample_interval_m, 3),
            "status": self.status,
            "is_visible": self.is_visible,
            "is_terrain_blocked": self.is_terrain_blocked,
            "is_out_of_range": self.is_out_of_range,
            "data_completeness": round(self.data_completeness, 3),
            "first_obstruction": obs_dict,
            "max_range_m": self.max_range_m,
            "clearance_margin_m": self.clearance_margin_m,
            "reason": self.reason,
            "source_attribution": self.source_attribution,
            "scientific_disclaimer": self.scientific_disclaimer,
        }


def sample_bilinear_elevation(
    grid: np.ndarray,
    r: float,
    c: float,
    invalid_mask: Optional[np.ndarray] = None,
    nodata_threshold_m: float = NODATA_THRESHOLD_M,
) -> Tuple[Optional[float], bool]:
    """
    Sub-pixel bilinear interpolation of terrain elevation on a 2D raster.

    Parameters
    ----------
    grid : np.ndarray
        2D elevation matrix [H, W] in meters.
    r : float
        Row coordinate (fractional).
    c : float
        Column coordinate (fractional).
    invalid_mask : Optional[np.ndarray]
        Boolean mask where True denotes invalid or dilated NoData cells.
    nodata_threshold_m : float
        Elevation sentinel threshold below which cell is rejected as NoData.

    Returns
    -------
    Tuple[Optional[float], bool]
        Interpolated elevation in meters and boolean valid flag.
    """
    rows, cols = grid.shape
    if r < 0.0 or r > float(rows - 1) or c < 0.0 or c > float(cols - 1):
        return None, False

    r0 = int(math.floor(r))
    c0 = int(math.floor(c))
    r1 = min(r0 + 1, rows - 1)
    c1 = min(c0 + 1, cols - 1)

    dr = r - r0
    dc = c - c0

    corners = [(r0, c0), (r0, c1), (r1, c0), (r1, c1)]
    for cr, cc in corners:
        val = grid[cr, cc]
        if np.isnan(val) or np.isinf(val) or float(val) <= nodata_threshold_m:
            return None, False
        if invalid_mask is not None and invalid_mask[cr, cc]:
            return None, False

    z00 = float(grid[r0, c0])
    z01 = float(grid[r0, c1])
    z10 = float(grid[r1, c0])
    z11 = float(grid[r1, c1])

    # Bilinear interpolation
    z = (1.0 - dr) * (1.0 - dc) * z00 + (1.0 - dr) * dc * z01 + dr * (1.0 - dc) * z10 + dr * dc * z11
    return float(z), True


def calculate_line_of_sight(
    elevation_grid: np.ndarray,
    point_a: Tuple[float, float],
    point_b: Tuple[float, float],
    antenna_h_a: float = 2.5,
    antenna_h_b: float = 10.0,
    dx_m: float = DEFAULT_DX_M,
    dy_m: float = DEFAULT_DY_M,
    max_range_m: Optional[float] = None,
    clearance_margin_m: float = 0.0,
    sample_step_m: Optional[float] = None,
    invalid_mask: Optional[np.ndarray] = None,
    nodata_threshold_m: float = NODATA_THRESHOLD_M,
    endpoint_a_id: str = "node_a",
    endpoint_b_id: str = "node_b",
    include_planetary_curvature: bool = False,
) -> LineOfSightResult:
    """
    Calculate geometric Line-of-Sight between two Martian surface endpoints.

    Parameters
    ----------
    elevation_grid : np.ndarray
        2D elevation matrix [H, W] in meters (e.g. USGS 20m Jezero CTX).
    point_a : Tuple[float, float]
        (row, col) coordinates of Endpoint A.
    point_b : Tuple[float, float]
        (row, col) coordinates of Endpoint B.
    antenna_h_a : float
        Antenna mast height in meters above ground level at Endpoint A (default 2.5m).
    antenna_h_b : float
        Antenna mast height in meters above ground level at Endpoint B (default 10.0m).
    dx_m : float
        True East-West ground pixel dimension in meters (default 18.972887m).
    dy_m : float
        True North-South ground pixel dimension in meters (default 20.0m).
    max_range_m : Optional[float]
        Maximum allowed geometric communication range in meters.
    clearance_margin_m : float
        Safety clearance buffer above terrain in meters (default 0.0m).
    sample_step_m : Optional[float]
        Distance between ray sampling steps. Defaults to min(dx_m, dy_m)/2 (~9.486m).
    invalid_mask : Optional[np.ndarray]
        Boolean invalid/NoData mask.
    nodata_threshold_m : float
        Sentinel threshold for NoData rejection (default -9000.0m).
    endpoint_a_id : str
        Human-readable or telemetry identifier for Endpoint A.
    endpoint_b_id : str
        Human-readable or telemetry identifier for Endpoint B.
    include_planetary_curvature : bool
        If True, applies spherical sagitta drop delta_h = (D^2 / (2 * R_Mars)) * t * (1 - t).

    Returns
    -------
    LineOfSightResult
        Complete evaluation with clearance metrics, obstruction details, and provenance.
    """
    r_a, c_a = float(point_a[0]), float(point_a[1])
    r_b, c_b = float(point_b[0]), float(point_b[1])

    # Check for non-finite or invalid coordinate values
    if any(math.isnan(v) or math.isinf(v) for v in [r_a, c_a, r_b, c_b]):
        return LineOfSightResult(
            endpoint_a_id=endpoint_a_id,
            endpoint_b_id=endpoint_b_id,
            row_a=r_a,
            col_a=c_a,
            row_b=r_b,
            col_b=c_b,
            antenna_h_a_m=antenna_h_a,
            antenna_h_b_m=antenna_h_b,
            ground_elevation_a_m=None,
            ground_elevation_b_m=None,
            total_altitude_a_m=None,
            total_altitude_b_m=None,
            ground_distance_m=0.0,
            slant_distance_m=None,
            min_clearance_m=None,
            sample_count=0,
            sample_interval_m=0.0,
            status="INVALID_INPUT",
            is_visible=False,
            is_terrain_blocked=False,
            is_out_of_range=False,
            data_completeness=0.0,
            first_obstruction=None,
            max_range_m=max_range_m,
            clearance_margin_m=clearance_margin_m,
            reason="Coordinates contain NaN or Inf",
        )

    # Compute ground metric distance
    delta_x = (c_b - c_a) * dx_m
    delta_y = (r_b - r_a) * dy_m
    ground_dist_m = math.sqrt(delta_x**2 + delta_y**2)

    # Sample endpoint elevations
    z_a, valid_a = sample_bilinear_elevation(elevation_grid, r_a, c_a, invalid_mask, nodata_threshold_m)
    z_b, valid_b = sample_bilinear_elevation(elevation_grid, r_b, c_b, invalid_mask, nodata_threshold_m)

    if not valid_a or not valid_b:
        return LineOfSightResult(
            endpoint_a_id=endpoint_a_id,
            endpoint_b_id=endpoint_b_id,
            row_a=r_a,
            col_a=c_a,
            row_b=r_b,
            col_b=c_b,
            antenna_h_a_m=antenna_h_a,
            antenna_h_b_m=antenna_h_b,
            ground_elevation_a_m=z_a,
            ground_elevation_b_m=z_b,
            total_altitude_a_m=None,
            total_altitude_b_m=None,
            ground_distance_m=ground_dist_m,
            slant_distance_m=None,
            min_clearance_m=None,
            sample_count=0,
            sample_interval_m=0.0,
            status="UNKNOWN",
            is_visible=False,
            is_terrain_blocked=False,
            is_out_of_range=False,
            data_completeness=0.0,
            first_obstruction=None,
            max_range_m=max_range_m,
            clearance_margin_m=clearance_margin_m,
            reason="Endpoint situated in NoData or outside grid extent",
        )

    alt_a = z_a + antenna_h_a
    alt_b = z_b + antenna_h_b
    slant_dist_m = math.sqrt(ground_dist_m**2 + (alt_b - alt_a)**2)

    is_out_of_range = (max_range_m is not None and ground_dist_m > max_range_m)

    # Handle degenerate case: endpoints are identical
    if ground_dist_m < 1e-5:
        min_clear = min(antenna_h_a, antenna_h_b)
        status = "OUT_OF_RANGE" if is_out_of_range else "VISIBLE"
        return LineOfSightResult(
            endpoint_a_id=endpoint_a_id,
            endpoint_b_id=endpoint_b_id,
            row_a=r_a,
            col_a=c_a,
            row_b=r_b,
            col_b=c_b,
            antenna_h_a_m=antenna_h_a,
            antenna_h_b_m=antenna_h_b,
            ground_elevation_a_m=z_a,
            ground_elevation_b_m=z_b,
            total_altitude_a_m=alt_a,
            total_altitude_b_m=alt_b,
            ground_distance_m=0.0,
            slant_distance_m=abs(alt_b - alt_a),
            min_clearance_m=min_clear,
            sample_count=1,
            sample_interval_m=0.0,
            status=status,
            is_visible=(status == "VISIBLE"),
            is_terrain_blocked=False,
            is_out_of_range=is_out_of_range,
            data_completeness=1.0,
            first_obstruction=None,
            max_range_m=max_range_m,
            clearance_margin_m=clearance_margin_m,
        )

    # Nyquist sampling step along chord
    if sample_step_m is None or sample_step_m <= 0:
        sample_step_m = min(dx_m, dy_m) / 2.0  # ~9.486m

    num_intervals = max(2, int(math.ceil(ground_dist_m / sample_step_m)))
    actual_step_m = ground_dist_m / float(num_intervals)
    t_samples = np.linspace(0.0, 1.0, num_intervals + 1)

    min_clearance = float("inf")
    first_obs: Optional[ObstructionPoint] = None
    is_blocked = False
    valid_samples = 0
    total_samples = len(t_samples)

    for t in t_samples:
        curr_r = r_a + t * (r_b - r_a)
        curr_c = c_a + t * (c_b - c_a)
        curr_los_h = alt_a + t * (alt_b - alt_a)

        # Optional planetary curvature drop: Delta h = (D^2 / (2 * R)) * t * (1 - t)
        if include_planetary_curvature:
            sagitta_drop = ((ground_dist_m**2) / (2.0 * MARS_RADIUS_M)) * t * (1.0 - t)
            curr_los_h -= sagitta_drop

        curr_z, sample_valid = sample_bilinear_elevation(
            elevation_grid, curr_r, curr_c, invalid_mask, nodata_threshold_m
        )

        if not sample_valid:
            # Traversed into NoData: Honest scientific disclosure
            completeness = float(valid_samples) / float(total_samples)
            return LineOfSightResult(
                endpoint_a_id=endpoint_a_id,
                endpoint_b_id=endpoint_b_id,
                row_a=r_a,
                col_a=c_a,
                row_b=r_b,
                col_b=c_b,
                antenna_h_a_m=antenna_h_a,
                antenna_h_b_m=antenna_h_b,
                ground_elevation_a_m=z_a,
                ground_elevation_b_m=z_b,
                total_altitude_a_m=alt_a,
                total_altitude_b_m=alt_b,
                ground_distance_m=ground_dist_m,
                slant_distance_m=slant_dist_m,
                min_clearance_m=None,
                sample_count=total_samples,
                sample_interval_m=actual_step_m,
                status="UNKNOWN",
                is_visible=False,
                is_terrain_blocked=False,
                is_out_of_range=is_out_of_range,
                data_completeness=completeness,
                first_obstruction=None,
                max_range_m=max_range_m,
                clearance_margin_m=clearance_margin_m,
                reason=f"Ray traversed unmeasured/NoData terrain at t={t:.3f}",
            )

        valid_samples += 1
        clearance = curr_los_h - curr_z
        if clearance < min_clearance:
            min_clearance = clearance

        # Obstruction detection: ray height - terrain <= clearance_margin
        if clearance <= clearance_margin_m and not is_blocked:
            is_blocked = True
            first_obs = ObstructionPoint(
                t=float(t),
                row=float(curr_r),
                col=float(curr_c),
                ground_dist_from_a_m=float(t * ground_dist_m),
                terrain_elevation_m=float(curr_z),
                los_ray_height_m=float(curr_los_h),
                clearance_m=float(clearance),
            )

    # Determine final status
    if is_blocked and is_out_of_range:
        status = "BLOCKED_AND_OUT_OF_RANGE"
    elif is_blocked:
        status = "BLOCKED"
    elif is_out_of_range:
        status = "OUT_OF_RANGE"
    else:
        status = "VISIBLE"

    return LineOfSightResult(
        endpoint_a_id=endpoint_a_id,
        endpoint_b_id=endpoint_b_id,
        row_a=r_a,
        col_a=c_a,
        row_b=r_b,
        col_b=c_b,
        antenna_h_a_m=antenna_h_a,
        antenna_h_b_m=antenna_h_b,
        ground_elevation_a_m=z_a,
        ground_elevation_b_m=z_b,
        total_altitude_a_m=alt_a,
        total_altitude_b_m=alt_b,
        ground_distance_m=ground_dist_m,
        slant_distance_m=slant_dist_m,
        min_clearance_m=min_clearance,
        sample_count=total_samples,
        sample_interval_m=actual_step_m,
        status=status,
        is_visible=(status == "VISIBLE"),
        is_terrain_blocked=is_blocked,
        is_out_of_range=is_out_of_range,
        data_completeness=1.0,
        first_obstruction=first_obs,
        max_range_m=max_range_m,
        clearance_margin_m=clearance_margin_m,
    )
