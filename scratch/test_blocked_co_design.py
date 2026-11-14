import sys
import time
sys.path.insert(0, 'src')
from marswalk.core.terrain import load_and_process_terrain
from marswalk.core.joint_mission_planner import optimize_joint_mission

def test_blocked():
    print("Loading Jezero terrain...")
    terrain = load_and_process_terrain("data/processed/jezero_ready_20m.tif")

    start_rc = (117, 157) # Octavia Butler Base
    goal_rc = (145, 95)   # Hawksbill Ascent (behind Séítah & Delta rim)
    base_station = {
        "node_id": "BASE",
        "row": 117,
        "col": 157,
        "antenna_height_m": 10.0,
        "label": "Octavia E. Butler Base"
    }

    print("\nRunning optimize_joint_mission to Hawksbill Ascent (145, 95)...")
    t0 = time.time()
    result = optimize_joint_mission(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain,
        base_station=base_station,
        relay_budget=2,
        objective_profile="balanced",
        max_route_candidates=4
    )
    print(f"Completed in {time.time() - t0:.2f}s!")

    print(f"\nEvaluated Configurations: {len(result.all_configurations)}")
    for cfg in result.all_configurations:
        m = cfg.metrics
        print(f"  Config: {cfg.configuration_id} -> Dist: {m.distance_m:.0f}m, Relays: {m.relay_count}, Avail: {m.availability_pct:.1f}%, GapDist: {m.gap_distance_m:.0f}m, Score: {m.scalar_utility_score:.4f}, Pareto: {cfg.is_pareto_optimal}")

    rec = result.recommended_configuration
    print(f"\nRECOMMENDED: {rec.configuration_id}")
    print(f"  Relays: {rec.metrics.relay_count} ({[r['node_id'] for r in rec.relays.relays_deployed]})")
    print(f"  Availability: {rec.metrics.availability_pct:.1f}%")
    print(f"  Explanation: {result.decision_explanation.summary}")
    print(f"  Connectivity Resolution: {result.decision_explanation.connectivity_resolution}")

if __name__ == "__main__":
    test_blocked()
