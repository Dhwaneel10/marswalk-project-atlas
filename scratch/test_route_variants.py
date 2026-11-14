import sys
sys.path.insert(0, 'src')
from marswalk.core.terrain import load_and_process_terrain, TerrainConfig
from marswalk.core.planner import astar_search, plan_route, PlannerConfig, ScienceWaypoint

def test_routes():
    print("Loading terrain...")
    terrain = load_and_process_terrain("data/processed/jezero_ready_20m.tif")
    start = (117, 157) # Octavia Butler Base
    goal = (138, 114)  # Three Forks

    # Variant 1: Direct shortest / low slope penalty
    cfg1 = TerrainConfig(alpha_s=1.0, theta_crit_deg=18.0)
    res1 = astar_search(start, goal, terrain, terrain_config=cfg1)
    print(f"Variant 1 (Direct Shortest): dist={res1.distance_m:.1f}m, cost={res1.cost:.1f}, path_len={len(res1.path)}")

    # Variant 2: Conservative / high slope penalty (avoiding slopes)
    cfg2 = TerrainConfig(alpha_s=8.0, theta_crit_deg=8.0)
    res2 = astar_search(start, goal, terrain, terrain_config=cfg2)
    print(f"Variant 2 (Conservative Flat): dist={res2.distance_m:.1f}m, cost={res2.cost:.1f}, path_len={len(res2.path)}")

    # Variant 3: Waypoint via Promontory Pass (126, 138)
    wp = ScienceWaypoint(id="WP_PROMONTORY", name="Promontory Pass", rc=(126, 138), priority_score=85.0)
    res3 = plan_route(start, goal, terrain, waypoints=[wp], config=PlannerConfig(profile="balanced"))
    print(f"Variant 3 (Waypoint Constrained): dist={res3.distance_m:.1f}m, cost={res3.cost:.1f}, path_len={len(res3.path)}")

    # Variant 4: Balanced profile via standard plan_route
    res4 = plan_route(start, goal, terrain, config=PlannerConfig(profile="balanced"))
    print(f"Variant 4 (Balanced Profile): dist={res4.distance_m:.1f}m, cost={res4.cost:.1f}, path_len={len(res4.path)}")

    # Variant 5: North-Detour via (100, 135)
    wp_north = ScienceWaypoint(id="WP_NORTH", name="Northern Plain", rc=(100, 135), priority_score=50.0)
    res5 = plan_route(start, goal, terrain, waypoints=[wp_north], config=PlannerConfig(profile="conservative"))
    print(f"Variant 5 (Northern Plain Detour): dist={res5.distance_m:.1f}m, cost={res5.cost:.1f}, path_len={len(res5.path)}")

    path1_set = set(res1.path)
    path2_set = set(res2.path)
    path3_set = set(res3.path)
    path5_set = set(res5.path)

    print(f"Overlap V1 & V2: {len(path1_set.intersection(path2_set))} / {len(path1_set)} cells")
    print(f"Overlap V1 & V3: {len(path1_set.intersection(path3_set))} / {len(path1_set)} cells")
    print(f"Overlap V1 & V5: {len(path1_set.intersection(path5_set))} / {len(path1_set)} cells")

if __name__ == "__main__":
    test_routes()
