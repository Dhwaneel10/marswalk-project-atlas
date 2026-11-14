"""
Benchmark MarsWalk Route Intelligence Engine on real Jezero CTX raster.
"""
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from marswalk.core.terrain import load_and_process_terrain
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    compute_pairwise_leg_cache,
    plan_route,
)
from marswalk.data.ingest import query_elevation_at_lonlat

TIFF_PATH = os.path.join(REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")
WP_PATH = os.path.join(REPO_ROOT, "data", "waypoints_jezero.json")

def main():
    print("=== MarsWalk Route Intelligence Benchmark ===")
    t_start = time.perf_counter()
    grid = load_and_process_terrain(TIFF_PATH)
    t_terrain = time.perf_counter() - t_start
    print(f"1. Terrain loaded and derived in {t_terrain:.3f} s (shape: {grid.shape})")

    with open(WP_PATH, "r", encoding="utf-8") as f:
        wp_raw = json.load(f)["waypoints"]

    # Select 5 candidate waypoints
    wps = []
    for w in wp_raw[:5]:
        elev, r, c = query_elevation_at_lonlat(TIFF_PATH, w["lon_deg"], w["lat_deg"])
        wps.append(ScienceWaypoint(w["id"], w["name"], (r, c), w["priority_score"]))

    start_rc = (117, 157)  # Octavia E. Butler Landing
    goal_rc = (66, 128)    # Delta Rim Overlook

    nodes = [start_rc] + [w.rc for w in wps] + [goal_rc]
    unique_nodes = list(dict.fromkeys(nodes))
    print(f"2. Computing pairwise directed cache for {len(unique_nodes)} nodes ({len(unique_nodes)**2} pairs)...")

    t_cache_0 = time.perf_counter()
    cache = compute_pairwise_leg_cache(unique_nodes, grid)
    t_cache = time.perf_counter() - t_cache_0
    print(f"   Pairwise cache computed in {t_cache:.3f} s ({len(cache)} directed legs)")

    print("\n3. Solving 3 mission traverse profiles...")
    t_solve_0 = time.perf_counter()
    res_cons = plan_route(start_rc, goal_rc, grid, wps, PlannerConfig(profile="conservative"), leg_cache=cache)
    res_sci = plan_route(start_rc, goal_rc, grid, wps, PlannerConfig(profile="science_first"), leg_cache=cache)
    res_bal = plan_route(start_rc, goal_rc, grid, wps, PlannerConfig(profile="balanced", science_appetite_gamma=1.0), leg_cache=cache)
    t_solve = time.perf_counter() - t_solve_0

    print(f"   All 3 profiles solved in {t_solve:.4f} s!")
    print(f"   Total routing time (cache + solve): {t_cache + t_solve:.3f} s")

    print("\n4. Route Comparison Metrics:")
    print(f"   [Conservative]  Dist: {res_cons.distance_m:7.1f} m | Cost: {res_cons.cost:7.1f} | Science: {res_cons.science_score:5.1f} pts | Visited: {res_cons.visited_waypoint_ids}")
    print(f"   [Balanced]      Dist: {res_bal.distance_m:7.1f} m | Cost: {res_bal.cost:7.1f} | Science: {res_bal.science_score:5.1f} pts | Visited: {res_bal.visited_waypoint_ids}")
    print(f"   [Science-First] Dist: {res_sci.distance_m:7.1f} m | Cost: {res_sci.cost:7.1f} | Science: {res_sci.science_score:5.1f} pts | Visited: {res_sci.visited_waypoint_ids}")

if __name__ == "__main__":
    main()
