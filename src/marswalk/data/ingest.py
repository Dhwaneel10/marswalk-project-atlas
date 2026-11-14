"""
MarsWalk Data Ingestion & Spatial Calibration Module.
Handles metadata inspection, coordinate transformations on the IAU Mars 2000 Sphere,
and precise affine-transform cropping of the USGS Jezero CTX DTM.
"""

import os
import json
import math
from typing import Dict, Any, Tuple, Optional
import numpy as np

# Physical constants for IAU Mars 2000 Sphere
MARS_RADIUS_M = 3396190.0
DEG_TO_RAD = math.pi / 180.0
RAD_TO_DEG = 180.0 / math.pi
METERS_PER_DEGREE_LAT = (math.pi * MARS_RADIUS_M) / 180.0  # ~59274.6975 m/deg


def planetocentric_to_proj_xy(lon_deg: float, lat_deg: float) -> Tuple[float, float]:
    """
    Convert planetocentric degrees to Equirectangular projected meters
    with CenterLatitude = 0.0, CenterLongitude = 0.0 on IAU Mars 2000 Sphere.
    Matches USGS PDS Equirectangular projection definition:
        X = R * (lon_rad)
        Y = R * (lat_rad)
    """
    x = MARS_RADIUS_M * (lon_deg * DEG_TO_RAD)
    y = MARS_RADIUS_M * (lat_deg * DEG_TO_RAD)
    return x, y


def proj_xy_to_planetocentric(x: float, y: float) -> Tuple[float, float]:
    """
    Convert Equirectangular projected meters back to planetocentric degrees.
    """
    lon_deg = (x / MARS_RADIUS_M) * RAD_TO_DEG
    lat_deg = (y / MARS_RADIUS_M) * RAD_TO_DEG
    return lon_deg, lat_deg


def inspect_geotiff(filepath: str) -> Dict[str, Any]:
    """
    Inspect GeoTIFF metadata, dimensions, affine transform, NoData, and elevation statistics.
    """
    import rasterio

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"GeoTIFF file not found: {filepath}")

    with rasterio.open(filepath) as src:
        bounds = src.bounds
        res_x, res_y = src.res
        nodata = src.nodata
        meta = {
            "driver": src.driver,
            "width": src.width,
            "height": src.height,
            "count": src.count,
            "dtype": str(src.dtypes[0]),
            "crs": str(src.crs),
            "transform": [src.transform[i] for i in range(9)],
            "resolution": (res_x, res_y),
            "bounds": {
                "left": bounds.left,
                "bottom": bounds.bottom,
                "right": bounds.right,
                "top": bounds.top,
            },
            "nodata": nodata,
        }
        # Read band 1 to compute statistics on valid elevation pixels
        z = src.read(1)
        valid_mask = ~np.isnan(z)
        if nodata is not None:
            valid_mask &= (z != nodata)
        valid_mask &= (z > -10000.0)

        if np.any(valid_mask):
            meta["elevation_min_m"] = float(np.min(z[valid_mask]))
            meta["elevation_max_m"] = float(np.max(z[valid_mask]))
            meta["elevation_mean_m"] = float(np.mean(z[valid_mask]))
            meta["elevation_std_m"] = float(np.std(z[valid_mask]))
        else:
            meta["elevation_min_m"] = None
            meta["elevation_max_m"] = None
            meta["elevation_mean_m"] = None
            meta["elevation_std_m"] = None

    return meta


def crop_study_region(
    raw_geotiff_path: str,
    output_geotiff_path: str,
    center_lon_deg: float = 77.442,
    center_lat_deg: float = 18.442,
    crop_width_px: int = 250,
    crop_height_px: int = 250,
) -> Dict[str, Any]:
    """
    Derive a 250x250 pixel crop centered on the Western Delta Front from the raw raster transform.
    Saves the calibrated float32 GeoTIFF to output_geotiff_path.
    """
    import rasterio
    from rasterio.windows import Window
    from rasterio.transform import Affine

    os.makedirs(os.path.dirname(output_geotiff_path), exist_ok=True)

    with rasterio.open(raw_geotiff_path) as src:
        # Compute projected coordinates of the center point
        center_x, center_y = planetocentric_to_proj_xy(center_lon_deg, center_lat_deg)

        # Invert affine transform to get float row and col in raw raster
        inv_transform = ~src.transform
        center_col_f, center_row_f = inv_transform @ (center_x, center_y)

        col_start = int(round(center_col_f - (crop_width_px / 2.0)))
        row_start = int(round(center_row_f - (crop_height_px / 2.0)))

        # Boundary checks
        if col_start < 0:
            col_start = 0
        if row_start < 0:
            row_start = 0
        if col_start + crop_width_px > src.width:
            col_start = src.width - crop_width_px
        if row_start + crop_height_px > src.height:
            row_start = src.height - crop_height_px

        window = Window(col_start, row_start, crop_width_px, crop_height_px)
        cropped_data = src.read(1, window=window).astype(np.float32)

        # Compute new affine transform for the window
        new_transform = src.window_transform(window)
        profile = src.profile.copy()
        profile.update(
            {
                "driver": "GTiff",
                "height": crop_height_px,
                "width": crop_width_px,
                "transform": new_transform,
                "dtype": "float32",
                "nodata": src.nodata if src.nodata is not None else -32768.0,
            }
        )

        with rasterio.open(output_geotiff_path, "w", **profile) as dst:
            dst.write(cropped_data, 1)

    return inspect_geotiff(output_geotiff_path)


def query_elevation_at_lonlat(
    geotiff_path: str, lon_deg: float, lat_deg: float
) -> Tuple[float, int, int]:
    """
    Query elevation in meters at a given planetocentric (lon, lat) degree position.
    Returns (elevation_m, row, col).
    """
    import rasterio

    x, y = planetocentric_to_proj_xy(lon_deg, lat_deg)
    with rasterio.open(geotiff_path) as src:
        inv_transform = ~src.transform
        col_f, row_f = inv_transform @ (x, y)
        row = int(round(row_f))
        col = int(round(col_f))

        if 0 <= row < src.height and 0 <= col < src.width:
            data = src.read(1)
            elevation = float(data[row, col])
            return elevation, row, col
        else:
            raise ValueError(
                f"Coordinates ({lon_deg}°E, {lat_deg}°N) map to pixel ({row}, {col}), "
                f"outside raster dimensions ({src.height}, {src.width})!"
            )
