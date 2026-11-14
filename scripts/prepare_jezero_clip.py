"""
Prepare the calibrated Jezero Western Delta 250x250 pixel crop (5 km x 5 km)
from the raw USGS CTX DTM GeoTIFF.
"""
import os
import sys
import json

# Ensure src is on python path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from marswalk.data.ingest import (
    crop_study_region,
    inspect_geotiff,
    query_elevation_at_lonlat,
    planetocentric_to_proj_xy,
)

RAW_PATH = os.path.join(
    REPO_ROOT, "data", "raw", "JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif"
)
PROCESSED_PATH = os.path.join(REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")
WAYPOINTS_PATH = os.path.join(REPO_ROOT, "data", "waypoints_jezero.json")

def main():
    print("=== MarsWalk Step 1: Data Ingestion & Calibration ===")
    if not os.path.exists(RAW_PATH):
        print(f"Error: Raw GeoTIFF not found at {RAW_PATH}")
        sys.exit(1)

    print(f"1. Inspecting raw USGS CTX GeoTIFF: {RAW_PATH}")
    raw_meta = inspect_geotiff(RAW_PATH)
    print(f"   Dimensions: {raw_meta['width']} samples x {raw_meta['height']} lines")
    print(f"   Resolution: {raw_meta['resolution'][0]} x {raw_meta['resolution'][1]} m/px")
    print(f"   Elevation range: {raw_meta['elevation_min_m']:.2f} m to {raw_meta['elevation_max_m']:.2f} m")
    print(f"   Elevation mean: {raw_meta['elevation_mean_m']:.2f} m (std: {raw_meta['elevation_std_m']:.2f} m)")
    print(f"   NoData value: {raw_meta['nodata']}")

    print("\n2. Cropping 250x250 study region centered on Western Delta Front (77.440°E, 18.442°N)...")
    crop_meta = crop_study_region(
        raw_geotiff_path=RAW_PATH,
        output_geotiff_path=PROCESSED_PATH,
        center_lon_deg=77.440,
        center_lat_deg=18.442,
        crop_width_px=250,
        crop_height_px=250,
    )
    print(f"   Cropped raster saved: {PROCESSED_PATH}")
    print(f"   Cropped Dimensions: {crop_meta['width']} x {crop_meta['height']} px (5.0 km x 5.0 km)")
    print(f"   Cropped Elevation: {crop_meta['elevation_min_m']:.2f} m to {crop_meta['elevation_max_m']:.2f} m")

    print("\n3. Validating waypoints inside cropped raster...")
    with open(WAYPOINTS_PATH, "r", encoding="utf-8") as f:
        wp_data = json.load(f)

    for wp in wp_data["waypoints"]:
        elev, r, c = query_elevation_at_lonlat(PROCESSED_PATH, wp["lon_deg"], wp["lat_deg"])
        print(f"   - {wp['name']}: Lon {wp['lon_deg']}°E, Lat {wp['lat_deg']}°N -> Pixel (row {r}, col {c}), Elev {elev:.1f} m")

    print("\nData preparation complete and verified!")

if __name__ == "__main__":
    main()
