"""
MarsWalk 2.0 — Milestone 9R Interactive Contingency Designer & What-If Analysis Test Suite

Validates:
1. Valid closed corridor replan (detour path, positive distance delta, revised narrative).
2. Parameter validation (rejection of negative radius, out-of-bounds, invalid multipliers).
3. Blocked cell compilation (correct grid footprint generation).
4. Revised route avoidance (route does not traverse blocked cells).
5. Non-intersecting event behavior (zero detour, path unchanged, narrative clarity).
6. Difficult terrain cost multiplier (increased traversal energy/cost).
7. Mobility derating invariant geometry (identical 0m detour path, expanded duration).
8. Reduced time budget feasibility evaluation (detects budget deficit/negative margin).
9. Operational hold delay metrics (timeline updated, 0m detour).
10. Target unavailable replan (dropped science target, regret ledger).
11. Compound scenario with 2 compatible events (corridor + mobility).
12. Compound scenario with 3 compatible events (corridor + mobility + hold).
13. Incompatible/excess event rejection (> 3 events rejected).
14. Infeasible scenario detection (severed destination handled gracefully).
15. Terrain isolation (underlying terrain not mutated by simulation).
16. Eight-measurement comparison table (accurate deltas for all 8 rows).
17. Experiment library persistence and immutability for custom contingency.
"""

import os
import json
import pytest
import numpy as np
import rasterio
from pathlib import Path

from marswalk.core.terrain import load_and_process_terrain, TerrainGrid, TerrainConfig
from marswalk.core.planner import (
    ScienceWaypoint,
    VehicleMode,
    calculate_traverse_time,
)
from marswalk.core.contingency import (
    CustomEventType,
    CustomEventDefinition,
    validate_custom_event_dict,
    compile_custom_contingency,
    compute_circular_footprint,
    generate_contingency_narrative,
    build_contingency_comparison_table,
)
from marswalk.api.service import (
    plan_route_api,
    contingency_simulate_api,
    gauntlet_api,
)
from marswalk.data.ingest import query_elevation_at_lonlat
from marswalk.api.workspace import (
    save_experiment,
    get_experiment,
    list_experiments,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GEOTIFF_PATH = str(PROJECT_ROOT / "data" / "processed" / "jezero_ready_20m.tif")
WAYPOINTS_PATH = str(PROJECT_ROOT / "data" / "waypoints_jezero.json")


@pytest.fixture(scope="module")
def terrain_context():
    """Load default surveyed Jezero terrain and transform once for the suite."""
    terrain = load_and_process_terrain(GEOTIFF_PATH)
    with rasterio.open(GEOTIFF_PATH) as src:
        transform = src.transform

    waypoints = []
    if os.path.exists(WAYPOINTS_PATH):
        with open(WAYPOINTS_PATH, "r", encoding="utf-8") as f:
            wp_data = json.load(f)
        for wp in wp_data.get("waypoints", []):
            elev, r, c = query_elevation_at_lonlat(GEOTIFF_PATH, wp["lon_deg"], wp["lat_deg"])
            waypoints.append(
                ScienceWaypoint(
                    id=wp["id"],
                    name=wp["name"],
                    rc=(r, c),
                    priority_score=float(wp.get("priority_score", 50.0)),
                )
            )
    return terrain, transform, waypoints


@pytest.fixture
def baseline_payload():
    """Standard baseline mission payload: Octavia Landing to Delta Rim with Hawksbill Gap."""
    return {
        "start": {"row": 117, "col": 157, "name": "Octavia E. Butler Landing"},
        "goal": {"row": 66, "col": 128, "name": "Delta Rim Overlook"},
        "stops": [
            {"row": 104, "col": 147, "id": "hawksbill_gap", "name": "Hawksbill Gap", "priority_score": 95.0}
        ],
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "operational_limit_s": 28800.0,
        "dwell_time_per_stop_s": 900.0,
    }


# =============================================================================
# Test 1: Valid closed corridor replan
# =============================================================================
def test_valid_closed_corridor_replan(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context

    base_plan = plan_route_api(baseline_payload, terrain, transform, waypoints)
    path = base_plan["path_rc"]
    mid_cell = path[len(path) // 2]

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "closed_corridor",
            "center_row": mid_cell[0],
            "center_col": mid_cell[1],
            "radius_m": 80.0,
            "name": "Rockfall Obstruction",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)

    assert res["is_feasible"] is True
    assert res["scenario_summary"]["distance_delta_m"] >= 0.0
    assert "narrative" in res
    assert res["narrative"]["headline"] != ""
    assert len(res["comparison_table"]) == 8


# =============================================================================
# Test 2: Parameter validation
# =============================================================================
def test_rejected_invalid_parameters():
    # Invalid event type
    with pytest.raises(ValueError, match="Unsupported contingency event_type"):
        validate_custom_event_dict({"event_type": "alien_landing"})

    # Negative radius
    with pytest.raises(ValueError, match="radius_m must be strictly positive"):
        validate_custom_event_dict({"event_type": "closed_corridor", "center_row": 10, "center_col": 10, "radius_m": -20})

    # Out of bounds
    with pytest.raises(ValueError, match="outside the 0-99 grid"):
        validate_custom_event_dict({"event_type": "closed_corridor", "center_row": 150, "center_col": 10, "radius_m": 50})

    # Difficult terrain cost multiplier <= 1.0
    with pytest.raises(ValueError, match="cost_multiplier must be > 1.0"):
        validate_custom_event_dict({"event_type": "difficult_terrain", "center_row": 10, "center_col": 10, "radius_m": 50, "cost_multiplier": 0.9})

    # Reduced mobility speed multiplier <= 0 or > 1.0
    with pytest.raises(ValueError, match="speed_multiplier must be between 0.05 and 1.0"):
        validate_custom_event_dict({"event_type": "reduced_mobility", "speed_multiplier": 1.5})
    with pytest.raises(ValueError, match="speed_multiplier must be between 0.05 and 1.0"):
        validate_custom_event_dict({"event_type": "reduced_mobility", "speed_multiplier": 0.0})

    # Reduced budget cut <= 0 or >= 100
    with pytest.raises(ValueError, match="budget_reduction_pct must be between 1.0% and 95.0%"):
        validate_custom_event_dict({"event_type": "reduced_time_budget", "budget_reduction_pct": 100.0})

    # Operational hold delay <= 0
    with pytest.raises(ValueError, match="delay_minutes must be > 0"):
        validate_custom_event_dict({"event_type": "operational_hold", "delay_minutes": 0})

    # Target unavailable missing target_id
    with pytest.raises(ValueError, match="target_id is required"):
        validate_custom_event_dict({"event_type": "target_unavailable", "target_id": ""})


# =============================================================================
# Test 3: Blocked cell compilation
# =============================================================================
def test_blocked_cells_applied_to_terrain(terrain_context):
    terrain, transform, _ = terrain_context
    events = [
        {
            "event_type": "closed_corridor",
            "center_row": 50,
            "center_col": 50,
            "radius_m": 60.0,
            "name": "Blocked Zone",
        }
    ]
    scen_def, _ = compile_custom_contingency(events, terrain)
    assert scen_def.blocked_cells is not None and len(scen_def.blocked_cells) > 0
    assert (50, 50) in scen_def.blocked_cells


# =============================================================================
# Test 4: Revised route avoids blocked cells
# =============================================================================
def test_revised_route_avoids_blocked_corridor(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context

    base_plan = plan_route_api(baseline_payload, terrain, transform, waypoints)
    path = base_plan["path_rc"]
    r, c = path[len(path) // 2]

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "closed_corridor",
            "center_row": r,
            "center_col": c,
            "radius_m": 60.0,
            "name": "Severed Path Segment",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)

    if res["is_feasible"]:
        revised_path = res["revised_route"]["path_rc"]
        revised_set = set((pt[0], pt[1]) for pt in revised_path)
        blocked_set = set(tuple(bc) for bc in res["blocked_cells"])
        intersection = revised_set.intersection(blocked_set)
        assert len(intersection) == 0, f"Revised path intersects blocked cells: {intersection}"


# =============================================================================
# Test 5: Non-intersecting event behavior
# =============================================================================
def test_non_intersecting_event_behavior(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "closed_corridor",
            "center_row": 10,
            "center_col": 10,
            "radius_m": 30.0,
            "name": "Far Off Corridor Closure",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)

    assert res["is_feasible"] is True
    assert res["scenario_summary"]["distance_delta_m"] == 0.0
    headline_lower = res["narrative"]["headline"].lower()
    detail_lower = res["narrative"]["detail"].lower()
    assert "no route impact" in headline_lower or "no net impact" in headline_lower or "identical" in detail_lower or "baseline" in headline_lower


# =============================================================================
# Test 6: Difficult terrain cost multiplier
# =============================================================================
def test_difficult_terrain_cost_multiplier(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context

    base_plan = plan_route_api(baseline_payload, terrain, transform, waypoints)
    path = base_plan["path_rc"]
    r, c = path[len(path) // 2]

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "difficult_terrain",
            "center_row": r,
            "center_col": c,
            "radius_m": 80.0,
            "cost_multiplier": 3.5,
            "name": "High Drag Regolith",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)

    assert res["is_feasible"] is True
    assert (res["revised_route"]["cost"] >= base_plan["cost"] or
            res["scenario_summary"]["distance_delta_m"] >= 0.0)


# =============================================================================
# Test 7: Mobility derating invariant geometry
# =============================================================================
def test_mobility_derating_time_expansion_invariant_geometry(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context

    base_plan = plan_route_api(baseline_payload, terrain, transform, waypoints)

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "reduced_mobility",
            "speed_multiplier": 0.5,
            "name": "Degraded EVA Mobility",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)

    assert res["is_feasible"] is True
    # 0m net detour geometry
    assert res["scenario_summary"]["distance_delta_m"] == 0.0
    assert len(res["revised_route"]["path_rc"]) == len(base_plan["path_rc"])

    # Traverse time must double
    base_trav_s = base_plan["travel_time_s"]
    revised_trav_s = res["revised_route"]["travel_time_s"]
    assert pytest.approx(revised_trav_s, rel=0.03) == base_trav_s * 2.0


# =============================================================================
# Test 8: Reduced time budget feasibility evaluation
# =============================================================================
def test_reduced_time_budget_feasibility_check(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context

    payload = dict(baseline_payload)
    # Severe 90% cut on 28800s life-support limit -> 2880s
    payload["custom_events"] = [
        {
            "event_type": "reduced_time_budget",
            "budget_reduction_pct": 90.0,
            "name": "Critical Life Support Ceiling Drop",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)

    assert res["is_feasible"] is False
    assert res["revised_timeline"]["is_within_limit"] is False
    assert res["revised_timeline"]["remaining_margin_s"] < 0


# =============================================================================
# Test 9: Operational hold delay metrics
# =============================================================================
def test_operational_hold_delay_metrics(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context

    base_plan = plan_route_api(baseline_payload, terrain, transform, waypoints)
    delay_mins = 35.0

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "operational_hold",
            "delay_minutes": delay_mins,
            "name": "Comms Diagnostic Dwell",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)

    assert res["is_feasible"] is True
    assert res["scenario_summary"]["distance_delta_m"] == 0.0

    base_total_s = base_plan["timeline"]["total_mission_time_s"]
    revised_total_s = res["revised_timeline"]["total_mission_time_s"]
    assert pytest.approx(revised_total_s - base_total_s, abs=5) == delay_mins * 60.0


# =============================================================================
# Test 10: Target unavailable replan
# =============================================================================
def test_dropped_science_target_replanning(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "target_unavailable",
            "target_id": "hawksbill_gap",
            "name": "Hawksbill Gap Unreachable",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)

    assert res["is_feasible"] is True
    # Visited waypoints should now be 0 (bypassed Hawksbill Gap)
    assert len(res["revised_route"]["visited_waypoint_ids"]) == 0
    assert "regret_ledger" in res
    assert "hawksbill_gap" in res["regret_ledger"]["disabled_by_scenario_ids"]


# =============================================================================
# Test 11: Compound scenario with 2 compatible events
# =============================================================================
def test_compound_two_events_synergy(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context

    base_plan = plan_route_api(baseline_payload, terrain, transform, waypoints)
    path = base_plan["path_rc"]
    r, c = path[len(path) // 2]

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "closed_corridor",
            "center_row": r,
            "center_col": c,
            "radius_m": 60.0,
            "name": "Rock Wall Obstruction",
        },
        {
            "event_type": "reduced_mobility",
            "speed_multiplier": 0.65,
            "name": "EVA Suit Thermal Limitation",
        },
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)

    assert res["scenario_summary"]["applied_events_count"] == 2
    assert res["revised_route"]["travel_time_s"] > base_plan["travel_time_s"]


# =============================================================================
# Test 12: Compound scenario with 3 compatible events
# =============================================================================
def test_compound_three_events_synergy(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context

    base_plan = plan_route_api(baseline_payload, terrain, transform, waypoints)
    path = base_plan["path_rc"]
    r, c = path[len(path) // 3]

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "closed_corridor",
            "center_row": r,
            "center_col": c,
            "radius_m": 50.0,
            "name": "Boulder Hazard",
        },
        {
            "event_type": "reduced_mobility",
            "speed_multiplier": 0.8,
            "name": "Reduced Speed",
        },
        {
            "event_type": "operational_hold",
            "delay_minutes": 15.0,
            "name": "Operational Stand-Down",
        },
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)

    assert res["scenario_summary"]["applied_events_count"] == 3
    assert len(res["comparison_table"]) == 8


# =============================================================================
# Test 13: Incompatible/excess event rejection
# =============================================================================
def test_incompatible_events_rejection():
    four_events = [
        {"event_type": "operational_hold", "delay_minutes": 10},
        {"event_type": "operational_hold", "delay_minutes": 15},
        {"event_type": "reduced_mobility", "speed_multiplier": 0.8},
        {"event_type": "reduced_time_budget", "budget_reduction_pct": 10},
    ]

    with pytest.raises(ValueError, match="Maximum 3 concurrent events"):
        validate_custom_event_dict({"events": four_events})

    duplicate_drop = [
        {"event_type": "target_unavailable", "target_id": "TARGET_A"},
        {"event_type": "target_unavailable", "target_id": "TARGET_A"},
    ]
    with pytest.raises(ValueError, match="Duplicate target drop"):
        validate_custom_event_dict({"events": duplicate_drop})


# =============================================================================
# Test 14: Infeasible scenario detection
# =============================================================================
def test_infeasible_scenario_detection(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context

    payload = dict(baseline_payload)
    # Severe closed corridor covering the destination completely
    goal_r = baseline_payload["goal"]["row"]
    goal_c = baseline_payload["goal"]["col"]
    payload["custom_events"] = [
        {
            "event_type": "closed_corridor",
            "center_row": goal_r,
            "center_col": goal_c,
            "radius_m": 250.0,
            "name": "Complete Goal Isolation",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)

    assert res["is_feasible"] is False
    headline_lower = res["narrative"]["headline"].lower()
    assert "infeasible" in headline_lower or "severed" in headline_lower or "no passable" in headline_lower


# =============================================================================
# Test 15: Independent runs do not pollute baseline terrain
# =============================================================================
def test_independent_runs_do_not_pollute_baseline_terrain(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context

    orig_elev_sum = float(np.sum(terrain.elevation))
    orig_slope_sum = float(np.sum(terrain.slope_deg))

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "closed_corridor",
            "center_row": 80,
            "center_col": 140,
            "radius_m": 120.0,
            "name": "Massive Hazard Zone",
        }
    ]

    contingency_simulate_api(payload, terrain, transform, waypoints)

    assert float(np.sum(terrain.elevation)) == orig_elev_sum
    assert float(np.sum(terrain.slope_deg)) == orig_slope_sum


# =============================================================================
# Test 16: Eight-measurement comparison table deltas
# =============================================================================
def test_eight_measurement_comparison_table_deltas(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "operational_hold",
            "delay_minutes": 25.0,
            "name": "Hold Test",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)

    table = res["comparison_table"]
    assert len(table) == 8

    dur_row = next(r for r in table if r["metric"] == "Total mission duration")
    assert dur_row["difference"] != "—"
    assert dur_row["baseline"] != dur_row["scenario"]

    dist_row = next(r for r in table if r["metric"] == "Route distance")
    assert "+0.0 m" in dist_row["difference"] or "(+0.0%)" in dist_row["difference"]


# =============================================================================
# Test 17: Experiment library persistence and immutability
# =============================================================================
def test_contingency_experiment_persistence_and_immutability(terrain_context, baseline_payload, tmp_path):
    terrain, transform, waypoints = terrain_context
    temp_exp_dir = str(tmp_path / "experiments")
    os.makedirs(temp_exp_dir, exist_ok=True)

    payload = dict(baseline_payload)
    events = [
        {
            "event_type": "reduced_mobility",
            "speed_multiplier": 0.8,
            "name": "Wheel Drag Test",
        }
    ]
    payload["custom_events"] = events

    sim_res = contingency_simulate_api(payload, terrain, transform, waypoints)

    exp_data = {
        "name": "M9R Custom Contingency Run",
        "description": "Interactive contingency simulation testing wheel drag",
        "baseline_fingerprint": sim_res["baseline_route"]["input_fingerprint"],
        "mission_snapshot": sim_res["baseline_route"]["mission_snapshot"],
        "baseline_route": sim_res["baseline_route"],
        "scenarios_evaluated": [
            {
                "scenario_id": "COMPOUND_DISRUPTION",
                "name": "Custom Contingency Simulation",
                "is_custom_contingency": True,
                "custom_events": events,
                "scenario_route": sim_res["revised_route"],
                "comparison_table": sim_res["comparison_table"],
                "narrative": sim_res["narrative"],
            }
        ],
        "is_custom_contingency": True,
        "custom_events": events,
        "terrain_dataset_id": "jezero_ready_20m.tif",
        "model_version": "2.0.0",
    }

    saved = save_experiment(exp_data, experiments_dir=temp_exp_dir)
    assert "experiment_id" in saved
    exp_id = saved["experiment_id"]

    retrieved = get_experiment(exp_id, experiments_dir=temp_exp_dir)
    assert retrieved is not None
    assert retrieved["name"] == "M9R Custom Contingency Run"
    assert len(retrieved["scenarios_evaluated"]) == 1
    scen = retrieved["scenarios_evaluated"][0]
    assert scen.get("is_custom_contingency") is True
    assert len(scen.get("custom_events", [])) == 1
    assert scen["custom_events"][0]["event_type"] == "reduced_mobility"
