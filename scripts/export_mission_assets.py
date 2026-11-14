"""
MarsWalk 2.0 Mission Assets Exporter
Extracts real Jezero Crater terrain elevation grid, slope, waypoints,
and authentic Python A* planned routes into a unified JSON bridge for the 3D Atlas.

Preserves exact IAU Mars 2000 Sphere coordinates, datum, resolution, and data provenance.
"""

import os
import json
import math
from typing import Dict, Any, List, Tuple
import numpy as np
import rasterio

from marswalk.core.terrain import (
    load_and_process_terrain,
    MARS_RADIUS_M,
    DEG_TO_RAD,
    RAD_TO_DEG,
)
from marswalk.core.planner import (
    plan_route,
    PlannerConfig,
    ScienceWaypoint,
    compute_pairwise_leg_cache,
)
from marswalk.data.ingest import (
    planetocentric_to_proj_xy,
    proj_xy_to_planetocentric,
    query_elevation_at_lonlat,
    inspect_geotiff,
)


def rc_to_lonlat(
    r: int, c: int, transform: rasterio.Affine
) -> Tuple[float, float]:
    """Convert raster (row, col) to planetocentric (lon_deg, lat_deg)."""
    # rasterio.transform.xy maps (row, col) to projected (x, y)
    x, y = rasterio.transform.xy(transform, r, c, offset="center")
    lon_deg, lat_deg = proj_xy_to_planetocentric(x, y)
    return lon_deg, lat_deg


def export_mission_assets(
    geotiff_path: str = "data/processed/jezero_ready_20m.tif",
    waypoints_path: str = "data/waypoints_jezero.json",
    output_dirs: Tuple[str, ...] = ("web/public/data", "web/data"),
) -> str:
    """
    Export terrain elevation grid, waypoints, and pre-computed authentic A* routes
    to JSON for the 3D planetary atlas.
    """
    print(f"Loading terrain from {geotiff_path}...")
    terrain = load_and_process_terrain(geotiff_path)
    meta = inspect_geotiff(geotiff_path)

    with rasterio.open(geotiff_path) as src:
        transform = src.transform
        bounds = src.bounds
        left_lon, bottom_lat = proj_xy_to_planetocentric(bounds.left, bounds.bottom)
        right_lon, top_lat = proj_xy_to_planetocentric(bounds.right, bounds.top)

    # 1. Waypoints
    print(f"Loading waypoints from {waypoints_path}...")
    with open(waypoints_path, "r", encoding="utf-8") as f:
        wp_data = json.load(f)

    exported_waypoints = []
    science_waypoints = []

    for wp in wp_data.get("waypoints", []):
        elev, r, c = query_elevation_at_lonlat(geotiff_path, wp["lon_deg"], wp["lat_deg"])
        wp_entry = {
            "id": wp["id"],
            "name": wp["name"],
            "type": wp.get("type", "waypoint"),
            "priority_score": wp.get("priority_score", 0.0),
            "lon_deg": wp["lon_deg"],
            "lat_deg": wp["lat_deg"],
            "elevation_m": round(float(elev), 2),
            "row": r,
            "col": c,
            "geological_context": wp.get("geological_context", ""),
            "crism_signature": wp.get("crism_signature", ""),
            "pds_citation": wp.get("pds_citation", ""),
        }
        exported_waypoints.append(wp_entry)
        science_waypoints.append(
            ScienceWaypoint(
                id=wp["id"],
                name=wp["name"],
                rc=(r, c),
                priority_score=float(wp.get("priority_score", 0.0)),
                geological_context=wp.get("geological_context", ""),
                crism_signature=wp.get("crism_signature", ""),
                pds_citation=wp.get("pds_citation", ""),
            )
        )

    # 2. Plan Authentic Routes
    print("Computing authentic A* traverse profiles...")
    start_wp = next(w for w in exported_waypoints if w["id"] == "octavia_butler_landing")
    goal_wp = next(w for w in exported_waypoints if w["id"] == "delta_rim_overlook")
    start_rc = (start_wp["row"], start_wp["col"])
    goal_rc = (goal_wp["row"], goal_wp["col"])

    # Science targets (excluding start/goal), select top 5 by priority for precomputed profiles
    candidate_science = sorted(
        [w for w in science_waypoints if w.id not in ("octavia_butler_landing", "delta_rim_overlook")],
        key=lambda w: w.priority_score,
        reverse=True
    )[:5]

    # Leg cache
    all_nodes = [start_rc] + [w.rc for w in candidate_science] + [goal_rc]
    leg_cache = compute_pairwise_leg_cache(all_nodes, terrain)

    routes = {}

    profiles = [
        ("conservative", PlannerConfig(profile="conservative"), []),
        ("balanced", PlannerConfig(profile="balanced", science_appetite_gamma=1.0), candidate_science),
        ("science_first", PlannerConfig(profile="science_first"), candidate_science),
    ]

    for name, cfg, wps in profiles:
        print(f"  - Planning {name} profile...")
        result = plan_route(
            start_rc,
            goal_rc,
            terrain,
            config=cfg,
            waypoints=wps,
            leg_cache=leg_cache,
        )

        # Build detailed 3D path coordinates: [lon, lat, elevation]
        coords_3d = []
        cumulative_climb = 0.0
        max_slope = 0.0

        for i, (r, c) in enumerate(result.path):
            lon, lat = rc_to_lonlat(r, c, transform)
            elev = float(terrain.elevation[r, c])
            coords_3d.append([round(lon, 6), round(lat, 6), round(elev, 2)])

            slope = float(terrain.slope_deg[r, c])
            if slope > max_slope:
                max_slope = slope

            if i > 0:
                prev_elev = float(terrain.elevation[result.path[i - 1][0], result.path[i - 1][1]])
                delta_elev = elev - prev_elev
                if delta_elev > 0:
                    cumulative_climb += delta_elev

        routes[name] = {
            "profile": name,
            "distance_m": round(result.distance_m, 1),
            "cost": round(result.cost, 2),
            "science_score": round(result.science_score, 1),
            "visited_waypoint_ids": result.visited_waypoint_ids,
            "num_steps": result.num_steps,
            "num_cells": result.num_cells,
            "is_reachable": result.is_reachable,
            "cumulative_climb_m": round(cumulative_climb, 1),
            "max_slope_deg": round(max_slope, 1),
            "path_rc": [list(rc) for rc in result.path],
            "coordinates_3d": coords_3d,
            "travel_time_s": round(result.travel_time_s, 1),
            "travel_time_min_s": round(result.travel_time_min_s, 1),
            "travel_time_max_s": round(result.travel_time_max_s, 1),
            "formatted_travel_time": result.formatted_travel_time,
        }

    # 3. Elevation Grid
    print("Formatting elevation grid and metadata...")
    valid_mask = ~terrain.invalid_mask
    elev_grid = np.where(valid_mask, np.round(terrain.elevation, 2), -9999.0).tolist()
    slope_grid = np.where(valid_mask, np.round(terrain.slope_deg, 2), 0.0).tolist()

    mission_data = {
        "schema_version": "2.0.0",
        "target": "Mars",
        "crs": "ESRI:103885 (IAU Mars 2000 Sphere)",
        "datum": "MOLA DeltaGeoid",
        "source_attribution": {
            "elevation": "USGS Astrogeology Science Center / MRO CTX DTM (Fergason et al., 2020; DOI: 10.5066/P906QQT8)",
            "waypoints": "NASA Mars 2020 Perseverance Mission Science Team",
            "global_tiles": "NASA Mars Trek WMTS (Viking MDIM 2.1 & MOLA Shaded Relief)",
            "disclaimer": "MarsWalk is an independent research simulation prototype developed for the 2026 NASA Space Apps Challenge. Traverses reflect modeled macro-slope trade-offs and are NOT certified operational paths for crew or rovers.",
        },
        "bounds": {
            "projected": {
                "left": bounds.left,
                "right": bounds.right,
                "bottom": bounds.bottom,
                "top": bounds.top,
                "width_m": bounds.right - bounds.left,
                "height_m": bounds.top - bounds.bottom,
            },
            "geographic": {
                "min_lon_deg": round(left_lon, 6),
                "max_lon_deg": round(right_lon, 6),
                "min_lat_deg": round(bottom_lat, 6),
                "max_lat_deg": round(top_lat, 6),
                "center_lon_deg": round((left_lon + right_lon) / 2.0, 6),
                "center_lat_deg": round((bottom_lat + top_lat) / 2.0, 6),
            },
        },
        "grid": {
            "rows": terrain.height,
            "cols": terrain.width,
            "projected_cell_size_m": terrain.config.cell_size_m,
            "ground_dx_m": round(terrain.dx_ground_m, 3),
            "ground_dy_m": round(terrain.dy_ground_m, 3),
            "elevation_min_m": round(meta["elevation_min_m"], 2),
            "elevation_max_m": round(meta["elevation_max_m"], 2),
            "elevation_mean_m": round(meta["elevation_mean_m"], 2),
        },
        "waypoints": exported_waypoints,
        "routes": routes,
        "elevation_samples": elev_grid,
        "slope_samples": slope_grid,
    }

    # Save to all target directories
    output_path = ""
    for out_dir in output_dirs:
        os.makedirs(out_dir, exist_ok=True)
        target_file = os.path.join(out_dir, "jezero_mission_data.json")
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(mission_data, f, indent=2)
        print(f"Exported mission data to {target_file} ({os.path.getsize(target_file) / 1024 / 1024:.2f} MB)")
        if not output_path:
            output_path = target_file

    return output_path


if __name__ == "__main__":
    export_mission_assets()
