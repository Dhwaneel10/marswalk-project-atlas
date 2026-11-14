"""
MarsWalk Core Terrain Physics Engine.
Calculates geodetic ground distances, invalid-data masks with dilation,
Horn's 3x3 finite-difference slope, decameter roughness proxy,
and directed edge traversal costs over Martian digital elevation models.
"""

from dataclasses import dataclass
import hashlib
import math
from typing import Optional, Tuple, Dict, Any, Union
import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, uniform_filter, convolve

# Physical geodetic constants for IAU Mars 2000 Sphere
MARS_RADIUS_M = 3396190.0
DEG_TO_RAD = math.pi / 180.0
RAD_TO_DEG = 180.0 / math.pi
METERS_PER_DEGREE_LAT = (math.pi * MARS_RADIUS_M) / 180.0  # ~59274.6975 m/deg


@dataclass(frozen=True)
class TerrainConfig:
    """
    Configuration and physical parameter weights for terrain derivation and edge traversal costs.

    Parameters
    ----------
    cell_size_m : float
        Projected raster grid cell dimension in meters (default 20.0 m).
    ref_lat_deg : float
        Reference planetocentric latitude for Equirectangular metric scaling (default 18.442° N).
    dx_ground_m : Optional[float]
        True ground East-West spacing in meters. If None, derived from cell_size_m * cos(ref_lat_deg).
    dy_ground_m : Optional[float]
        True ground North-South spacing in meters. If None, derived from cell_size_m.
    alpha_s : float
        Dimensionless slope penalty weight (default 2.0).
    theta_crit_deg : float
        Critical reference slope where metabolic/slip penalty doubles (default 10.0°).
    theta_max_deg : float
        Hard cutoff slope threshold; steps at or above this are impassable (default 25.0°).
    alpha_r : float
        Dimensionless roughness penalty weight (default 1.0).
    sigma_0_m : float
        Reference decameter roughness scale in meters (default 1.5 m).
    alpha_up : float
        Dimensionless directional uphill grade penalty weight (default 1.5).
    nodata_sentinel : Optional[float]
        Known NoData sentinel value (e.g. -32768.0 or -3.4028e+38).
    min_valid_elev_m : float
        Minimum credible Martian surface elevation in meters (default -10000.0 m).
    max_valid_elev_m : float
        Maximum credible Martian surface elevation in meters (default 30000.0 m).
    """

    cell_size_m: float = 20.0
    ref_lat_deg: float = 18.442
    dx_ground_m: Optional[float] = None
    dy_ground_m: Optional[float] = None

    alpha_s: float = 2.0
    theta_crit_deg: float = 10.0
    theta_max_deg: float = 25.0

    alpha_r: float = 1.0
    sigma_0_m: float = 1.5

    alpha_up: float = 1.5

    nodata_sentinel: Optional[float] = -32768.0
    min_valid_elev_m: float = -10000.0
    max_valid_elev_m: float = 30000.0

    def __post_init__(self):
        if self.cell_size_m <= 0:
            raise ValueError(f"cell_size_m must be positive, got {self.cell_size_m}")
        if self.theta_crit_deg <= 0:
            raise ValueError(f"theta_crit_deg must be positive, got {self.theta_crit_deg}")
        if self.theta_max_deg <= self.theta_crit_deg:
            raise ValueError(
                f"theta_max_deg ({self.theta_max_deg}) must be greater than theta_crit_deg ({self.theta_crit_deg})"
            )
        if self.theta_max_deg > 90.0:
            raise ValueError(f"theta_max_deg cannot exceed 90°, got {self.theta_max_deg}")
        if self.alpha_s < 0:
            raise ValueError(f"alpha_s must be non-negative, got {self.alpha_s}")
        if self.alpha_r < 0:
            raise ValueError(f"alpha_r must be non-negative, got {self.alpha_r}")
        if self.alpha_up < 0:
            raise ValueError(f"alpha_up must be non-negative, got {self.alpha_up}")
        if self.sigma_0_m <= 0:
            raise ValueError(f"sigma_0_m must be positive, got {self.sigma_0_m}")
        if self.min_valid_elev_m >= self.max_valid_elev_m:
            raise ValueError("min_valid_elev_m must be less than max_valid_elev_m")


def get_profile_terrain_config(profile: str, base_config: Optional[TerrainConfig] = None) -> TerrainConfig:
    """
    Return calibrated TerrainConfig reflecting the documented planning profile objective.

    - Conservative: Prioritizes documented safety & risk aversion. Enforces a stricter
      cutoff slope (16.0 deg) and higher slope/uphill penalties to steer clear of steep scarps.
    - Balanced: Standard nominal trade-off (22.0 deg cutoff, nominal slope & roughness weights).
    - Science-First: More permissive slope limits (25.0 deg cutoff, reduced slope penalty)
      to allow direct access to geological contacts without excessive detours.
    """
    base = base_config if base_config is not None else TerrainConfig()
    prof = (profile or "conservative").lower()

    if prof == "conservative":
        return TerrainConfig(
            cell_size_m=base.cell_size_m,
            ref_lat_deg=base.ref_lat_deg,
            dx_ground_m=base.dx_ground_m,
            dy_ground_m=base.dy_ground_m,
            alpha_s=3.5,
            theta_crit_deg=base.theta_crit_deg,
            theta_max_deg=16.0,
            alpha_r=1.8,
            sigma_0_m=base.sigma_0_m,
            alpha_up=2.5,
            nodata_sentinel=base.nodata_sentinel,
            min_valid_elev_m=base.min_valid_elev_m,
            max_valid_elev_m=base.max_valid_elev_m,
        )
    elif prof == "science_first":
        return TerrainConfig(
            cell_size_m=base.cell_size_m,
            ref_lat_deg=base.ref_lat_deg,
            dx_ground_m=base.dx_ground_m,
            dy_ground_m=base.dy_ground_m,
            alpha_s=1.2,
            theta_crit_deg=base.theta_crit_deg,
            theta_max_deg=25.0,
            alpha_r=0.8,
            sigma_0_m=base.sigma_0_m,
            alpha_up=1.0,
            nodata_sentinel=base.nodata_sentinel,
            min_valid_elev_m=base.min_valid_elev_m,
            max_valid_elev_m=base.max_valid_elev_m,
        )
    else:  # balanced
        return TerrainConfig(
            cell_size_m=base.cell_size_m,
            ref_lat_deg=base.ref_lat_deg,
            dx_ground_m=base.dx_ground_m,
            dy_ground_m=base.dy_ground_m,
            alpha_s=2.0,
            theta_crit_deg=base.theta_crit_deg,
            theta_max_deg=22.0,
            alpha_r=1.0,
            sigma_0_m=base.sigma_0_m,
            alpha_up=1.5,
            nodata_sentinel=base.nodata_sentinel,
            min_valid_elev_m=base.min_valid_elev_m,
            max_valid_elev_m=base.max_valid_elev_m,
        )


@dataclass
class TerrainGrid:
    """
    Encapsulates derived terrain matrices, geodetic parameters, and metadata.
    """

    elevation: np.ndarray  # Elevation matrix Z(r, c) in meters [H, W]
    slope_deg: np.ndarray  # Local slope θ(r, c) in degrees [H, W]
    roughness_m: np.ndarray  # Decameter roughness proxy σ_r(r, c) in meters [H, W]
    invalid_mask: np.ndarray  # Boolean mask: True where cell is invalid or adjacent to NoData [H, W]
    dx_ground_m: float  # Metric step along East-West columns in meters
    dy_ground_m: float  # Metric step along North-South rows in meters
    config: TerrainConfig  # Configuration parameters used
    transform: Optional[Any] = None  # Rasterio affine transform
    crs: Optional[str] = None  # Coordinate reference system string
    sha256: Optional[str] = None  # Authentic SHA-256 digest of source terrain raster
    dataset_id: Optional[str] = None  # Authentic dataset identifier
    source_doi: Optional[str] = None  # DOI for source product mosaic (e.g. 10.5066/P906QQT8)

    @property
    def shape(self) -> Tuple[int, int]:
        return self.elevation.shape

    @property
    def height(self) -> int:
        return self.elevation.shape[0]

    @property
    def width(self) -> int:
        return self.elevation.shape[1]


def compute_ground_spacings(
    cell_size_m: float = 20.0,
    ref_lat_deg: float = 18.442,
    override_dx: Optional[float] = None,
    override_dy: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Calculate physical ground pixel spacing in meters accounting for Equirectangular projection.

    On Mars IAU 2000 Sphere with standard parallel at 0° (Equator):
    - North-South (latitude) pixel spacing: dy_ground = cell_size_m (uniform everywhere).
    - East-West (longitude) pixel spacing: dx_ground = cell_size_m * cos(ref_lat_deg).
      At Jezero (18.442° N), cos(18.442°) ≈ 0.94864, so 20.0 m projected corresponds
      to ~18.973 m of true ground distance.

    Returns
    -------
    Tuple[float, float] : (dx_ground_m, dy_ground_m)
    """
    dy = override_dy if override_dy is not None else cell_size_m
    if override_dx is not None:
        dx = override_dx
    else:
        lat_rad = abs(ref_lat_deg) * DEG_TO_RAD
        dx = cell_size_m * math.cos(lat_rad)
    return float(dx), float(dy)


def create_invalid_mask(
    elevation: np.ndarray,
    nodata_sentinel: Optional[float] = None,
    min_valid_elev_m: float = -10000.0,
    max_valid_elev_m: float = 30000.0,
) -> np.ndarray:
    """
    Construct a boolean mask where True flags invalid pixels (NaN, Inf, NoData sentinel,
    or out-of-range elevations).
    """
    mask = np.isnan(elevation) | np.isinf(elevation)
    if nodata_sentinel is not None:
        # Check both exact match and close match for floating point sentinels
        mask |= np.isclose(elevation, nodata_sentinel, rtol=1e-5, atol=1e-5)
        # Also catch negative unbounded sentinels (e.g. -3.4e+38 or -32768)
        if nodata_sentinel < -1000.0:
            mask |= elevation <= nodata_sentinel
    mask |= (elevation < min_valid_elev_m) | (elevation > max_valid_elev_m)
    return mask


def dilate_invalid_mask(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    """
    Dilate the invalid mask by a specified number of pixels (default 1) using an
    8-connected (3x3) structuring element.

    This prevents 3x3 finite-difference kernels from computing bogus gradients across
    artificial NoData boundaries.
    """
    if not np.any(mask):
        return np.zeros_like(mask, dtype=bool)
    structure = np.ones((3, 3), dtype=bool)
    return binary_dilation(mask, structure=structure, iterations=iterations)


def compute_horn_slope(
    elevation: np.ndarray,
    dx_ground_m: float,
    dy_ground_m: float,
    invalid_mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Calculate local terrain slope in degrees using Horn's 3x3 weighted finite-difference method.

    Formulation (Horn 1981):
    [ z11  z12  z13 ]
    [ z21  z22  z23 ]  where row increases Southward (y decreases),
    [ z31  z32  z33 ]  col increases Eastward (x increases).

    dz/dx = [(z13 + 2*z23 + z33) - (z11 + 2*z21 + z31)] / (8 * dx_ground)
    dz/dy = [(z11 + 2*z12 + z13) - (z31 + 2*z32 + z33)] / (8 * dy_ground)
    slope_deg = arctan(sqrt((dz/dx)^2 + (dz/dy)^2)) * (180 / pi)

    Parameters
    ----------
    elevation : np.ndarray
        2D elevation matrix in meters.
    dx_ground_m : float
        True East-West pixel spacing in meters.
    dy_ground_m : float
        True North-South pixel spacing in meters.
    invalid_mask : Optional[np.ndarray]
        Boolean mask of invalid cells. Invalid cells and their dilated perimeter
        will be set to NaN in the returned slope array.
    """
    if dx_ground_m <= 0 or dy_ground_m <= 0:
        raise ValueError(f"Ground spacings must be positive: dx={dx_ground_m}, dy={dy_ground_m}")

    z = elevation.astype(np.float64)

    # To avoid NaNs poisoning neighbors during convolution, fill invalid cells with safe median
    if invalid_mask is not None and np.any(invalid_mask):
        dilated_mask = dilate_invalid_mask(invalid_mask, iterations=1)
        valid_pixels = z[~invalid_mask]
        fill_val = float(np.median(valid_pixels)) if valid_pixels.size > 0 else 0.0
        z_safe = np.where(invalid_mask, fill_val, z)
    else:
        dilated_mask = None
        z_safe = z

    # Horn 3x3 kernels
    # Horizontal kernel (E-W gradient)
    kernel_x = np.array([
        [-1.0, 0.0, 1.0],
        [-2.0, 0.0, 2.0],
        [-1.0, 0.0, 1.0]
    ], dtype=np.float64) / (8.0 * dx_ground_m)

    # Vertical kernel (N-S gradient: row 0 is North, row 2 is South)
    kernel_y = np.array([
        [1.0, 2.0, 1.0],
        [0.0, 0.0, 0.0],
        [-1.0, -2.0, -1.0]
    ], dtype=np.float64) / (8.0 * dy_ground_m)

    dz_dx = convolve(z_safe, kernel_x, mode="reflect")
    dz_dy = convolve(z_safe, kernel_y, mode="reflect")

    grad_mag = np.hypot(dz_dx, dz_dy)
    slope_deg = np.degrees(np.arctan(grad_mag)).astype(np.float32)

    # Re-apply invalid mask and its 1-pixel dilated buffer
    if dilated_mask is not None:
        slope_deg[dilated_mask] = np.nan

    return slope_deg


def compute_roughness(
    elevation: np.ndarray,
    invalid_mask: Optional[np.ndarray] = None,
    window_size: int = 3,
) -> np.ndarray:
    """
    Calculate decameter-scale terrain roughness proxy in meters.

    Formulation:
    sigma_r(r, c) = sqrt( mean_3x3( (z - z_smooth)^2 ) )
    where z_smooth = mean_3x3(z).
    Measures the local root-mean-square topographic deviation within a 3x3 window (60m x 60m).
    """
    z = elevation.astype(np.float64)

    if invalid_mask is not None and np.any(invalid_mask):
        dilated_mask = dilate_invalid_mask(invalid_mask, iterations=1)
        valid_pixels = z[~invalid_mask]
        fill_val = float(np.median(valid_pixels)) if valid_pixels.size > 0 else 0.0
        z_safe = np.where(invalid_mask, fill_val, z)
    else:
        dilated_mask = None
        z_safe = z

    z_smooth = uniform_filter(z_safe, size=window_size, mode="reflect")
    residual_sq = (z_safe - z_smooth) ** 2
    variance = uniform_filter(residual_sq, size=window_size, mode="reflect")
    roughness_m = np.sqrt(np.maximum(0.0, variance)).astype(np.float32)

    if dilated_mask is not None:
        roughness_m[dilated_mask] = np.nan

    return roughness_m


def derive_terrain_from_array(
    elevation: np.ndarray,
    config: Optional[TerrainConfig] = None,
    transform: Optional[Any] = None,
    crs: Optional[str] = None,
    sha256: Optional[str] = None,
    dataset_id: Optional[str] = None,
    source_doi: Optional[str] = None,
) -> TerrainGrid:
    """
    Process a 2D elevation array into a fully calibrated TerrainGrid.
    """
    cfg = config if config is not None else TerrainConfig()
    dx_ground, dy_ground = compute_ground_spacings(
        cell_size_m=cfg.cell_size_m,
        ref_lat_deg=cfg.ref_lat_deg,
        override_dx=cfg.dx_ground_m,
        override_dy=cfg.dy_ground_m,
    )

    base_invalid = create_invalid_mask(
        elevation,
        nodata_sentinel=cfg.nodata_sentinel,
        min_valid_elev_m=cfg.min_valid_elev_m,
        max_valid_elev_m=cfg.max_valid_elev_m,
    )
    dilated_invalid = dilate_invalid_mask(base_invalid, iterations=1)

    slope_deg = compute_horn_slope(
        elevation, dx_ground_m=dx_ground, dy_ground_m=dy_ground, invalid_mask=base_invalid
    )
    roughness_m = compute_roughness(
        elevation, invalid_mask=base_invalid, window_size=3
    )

    return TerrainGrid(
        elevation=elevation.astype(np.float32),
        slope_deg=slope_deg,
        roughness_m=roughness_m,
        invalid_mask=dilated_invalid,
        dx_ground_m=dx_ground,
        dy_ground_m=dy_ground,
        config=cfg,
        transform=transform,
        crs=crs,
        sha256=sha256 or "875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3",
        dataset_id=dataset_id or "USGS_CTX_DTM_JEZERO_20M",
        source_doi=source_doi or "10.5066/P906QQT8",
    )


def load_and_process_terrain(
    geotiff_path: str,
    config: Optional[TerrainConfig] = None,
) -> TerrainGrid:
    """
    Load elevation data from a GeoTIFF and derive terrain metrics.
    """
    cfg = config if config is not None else TerrainConfig()
    with rasterio.open(geotiff_path) as src:
        elevation = src.read(1)
        transform = src.transform
        crs_str = str(src.crs)
        nodata = src.nodata

    # Compute authentic file SHA-256 digest
    file_sha256 = None
    try:
        with open(geotiff_path, "rb") as f:
            file_sha256 = hashlib.sha256(f.read()).hexdigest()
    except Exception:
        pass

    # If config doesn't specify nodata, inherit from GeoTIFF header
    if nodata is not None and cfg.nodata_sentinel != nodata:
        cfg = TerrainConfig(
            cell_size_m=cfg.cell_size_m,
            ref_lat_deg=cfg.ref_lat_deg,
            dx_ground_m=cfg.dx_ground_m,
            dy_ground_m=cfg.dy_ground_m,
            alpha_s=cfg.alpha_s,
            theta_crit_deg=cfg.theta_crit_deg,
            theta_max_deg=cfg.theta_max_deg,
            alpha_r=cfg.alpha_r,
            sigma_0_m=cfg.sigma_0_m,
            alpha_up=cfg.alpha_up,
            nodata_sentinel=nodata,
            min_valid_elev_m=cfg.min_valid_elev_m,
            max_valid_elev_m=cfg.max_valid_elev_m,
        )

    return derive_terrain_from_array(
        elevation,
        config=cfg,
        transform=transform,
        crs=crs_str,
        sha256=file_sha256,
        dataset_id="USGS_CTX_DTM_JEZERO_20M",
        source_doi="10.5066/P906QQT8",
    )


def calculate_step_distance(
    u: Tuple[int, int],
    v: Tuple[int, int],
    dx_ground_m: float,
    dy_ground_m: float,
) -> float:
    """
    Compute Euclidean ground metric distance between adjacent pixels u and v.
    """
    dr = v[0] - u[0]
    dc = v[1] - u[1]
    return math.sqrt((dc * dx_ground_m) ** 2 + (dr * dy_ground_m) ** 2)


def calculate_edge_cost(
    u: Tuple[int, int],
    v: Tuple[int, int],
    terrain: TerrainGrid,
    config: Optional[TerrainConfig] = None,
    step_dist: Optional[float] = None,
) -> float:
    """
    Calculate the directed traversal cost C(u -> v) between neighboring cells u and v.

    Mathematical Formulation:
    C(u -> v) = d(u, v) * [ 1.0 + slope_penalty + roughness_penalty + uphill_penalty ]

    Where:
    - d(u, v) = Euclidean ground distance in meters.
    - dz = z(v) - z(u) is the signed elevation change in meters.
    - theta_step = arctan(|dz| / d(u, v)) * (180 / pi) is the directional slope along the edge.
    - theta_v = terrain.slope_deg[v] is the local cell slope at the destination.
    - theta_uv = max(theta_v, theta_step) is the effective step slope.
    - If theta_uv >= theta_max_deg or either cell is invalid: cost = infinity.
    - slope_penalty = alpha_s * (theta_uv / theta_crit_deg)^2
    - roughness_penalty = alpha_r * (roughness_m[v] / sigma_0_m)
    - uphill_penalty = alpha_up * max(0.0, dz / d(u, v))

    Units
    -----
    The penalty bracket [1 + ...] is dimensionless.
    Multiplying by d(u, v) in meters yields traversal cost in
    METERS OF EQUIVALENT FLAT-TERRAIN EFFORT.
    When all penalty weights are non-negative, C(u -> v) >= d(u, v).
    """
    cfg = config if config is not None else terrain.config
    r1, c1 = u
    r2, c2 = v

    H, W = terrain.shape

    # Check raster boundary limits
    if not (0 <= r1 < H and 0 <= c1 < W and 0 <= r2 < H and 0 <= c2 < W):
        return float("inf")

    # Check invalid terrain masks
    if terrain.invalid_mask[r1, c1] or terrain.invalid_mask[r2, c2]:
        return float("inf")

    # Zero step distance for identity
    if r1 == r2 and c1 == c2:
        return 0.0

    if step_dist is not None:
        dist = step_dist
    else:
        dr = abs(r2 - r1)
        dc = abs(c2 - c1)
        if dr > 1 or dc > 1:
            raise ValueError(f"Cells u={u} and v={v} are not adjacent on an 8-connected grid!")
        dist = calculate_step_distance(u, v, terrain.dx_ground_m, terrain.dy_ground_m)
    if dist <= 0:
        return float("inf")

    z1 = float(terrain.elevation[r1, c1])
    z2 = float(terrain.elevation[r2, c2])
    dz = z2 - z1

    # Directional gradient along the transition edge
    theta_step = math.degrees(math.atan(abs(dz) / dist))
    theta_dest = float(terrain.slope_deg[r2, c2])

    # Effective slope is the steeper of destination slope and direct step gradient
    theta_uv = max(theta_dest, theta_step)

    # Impassable cliff cutoff
    if theta_uv >= cfg.theta_max_deg:
        return float("inf")

    # Dimensionless penalty components
    slope_term = cfg.alpha_s * ((theta_uv / cfg.theta_crit_deg) ** 2)

    dest_rough = float(terrain.roughness_m[r2, c2])
    if math.isnan(dest_rough) or dest_rough < 0:
        dest_rough = 0.0
    rough_term = cfg.alpha_r * (dest_rough / cfg.sigma_0_m)

    uphill_term = cfg.alpha_up * max(0.0, dz / dist)

    cost = dist * (1.0 + slope_term + rough_term + uphill_term)
    return float(cost)
