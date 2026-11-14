import sys
import time
sys.path.insert(0, 'src')
from marswalk.core.terrain import load_and_process_terrain
from marswalk.core.joint_mission_planner import optimize_joint_mission

def test_run():
    print("Loading Jezero terrain...")
    t0 = time.time()
    terrain = load_and_process_terrain("data/processed/jezero_ready_20m.tif")
    print(f"Loaded in {time.time() - t0:.2f}s. Grid shape: {terrain.elevation.shape}")

    start_rc = (117, 157) # Octavia Butler Base
    goal_rc = (138, 114)  # Three Forks
    base_station = {
        "node_id": "BASE",
        "row": 117,
        "col": 157,
        "antenna_height_m": 10.0,
        "label": "Octavia E. Butler Base"
    }

    print("\nRunning optimize_joint_mission...")
    t1 = time.time()
    result = optimize_joint_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain,
        base_station=base_station,
        relay_budget=2,
        objective_profile="balanced",
        max_route_candidates=4
    )
    t_opt = time.time() - t1
    print(f"Optimization completed in {t_opt:.2f}s ({result.search_bounds['execution_runtime_ms']:.1f}ms reported)!")

    print(f"\nResult ID: {result.result_id}")
    print(f"Candidate Traverses: {len(result.candidate_traverses)}")
    for trv in result.candidate_traverses:
        print(f"  - {trv.traverse_id} ({trv.label}): dist={trv.distance_m:.1f}m, slope={trv.mean_slope_deg:.1f} deg")

    print(f"\nEvaluated Configurations: {len(result.all_configurations)}")
    print(f"Pareto Frontier Count: {len(result.pareto_frontier)}")
    for p in result.pareto_frontier:
        m = p.metrics
        print(f"  * Pareto Config: {p.configuration_id} (Trv: {p.traverse.traverse_id}, Relays: {m.relay_count}) -> Dist: {m.distance_m:.0f}m, Avail: {m.availability_pct:.1f}%, Score: {m.scalar_utility_score:.4f}")

    rec = result.recommended_configuration
    print(f"\nRecommended Configuration: {rec.configuration_id}")
    print(f"  Traverse: {rec.traverse.label}")
    print(f"  Distance: {rec.metrics.distance_m:.1f}m, Availability: {rec.metrics.availability_pct:.1f}%")
    print(f"  Relays deployed: {rec.metrics.relay_count} ({[r['node_id'] for r in rec.relays.relays_deployed]})")
    print(f"  Score: {rec.metrics.scalar_utility_score:.4f}")

    print("\nDecision Explanation:")
    print("Summary:", result.decision_explanation.summary)
    print("Rationale:", result.decision_explanation.selection_rationale)
    print("Connectivity Resolution:", result.decision_explanation.connectivity_resolution)

if __name__ == "__main__":
    test_run()
