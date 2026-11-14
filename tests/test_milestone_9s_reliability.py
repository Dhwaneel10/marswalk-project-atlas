"""
MarsWalk 2.0 — Milestone 9S Autonomous Reliability Audit & Release Verification Suite

Verifies:
1. Closed corridor blocked-cell avoidance (no route points intersect blocked mask).
2. Closed corridor start-blocked controlled failure (is_reachable=False, clear narrative, no crash).
3. Closed corridor goal-blocked controlled failure (is_reachable=False, clear narrative, no crash).
4. Difficult terrain soft cost: small penalty absorbs cost (0m detour), large penalty forces detour.
5. Reduced mobility exact 2.0x velocity scaling (no slope penalty distortion when unspecified).
6. Reduced time budget in seconds (reduced_time_budget_s properly enforces feasibility boundary).
7. Operational hold delay accounting (single addition in timeline, scenario_delay event).
8. Compound scenario with target_unavailable in multi-stop route (omits target, updates regret ledger).
9. Compound scenario order invariance (event order does not alter physical simulation outcome).
10. Duplicate event ID rejection (enforces identifier uniqueness).
11. Adversarial input validation (NaN, inf, negative values, out-of-bounds coordinates).
12. Out-of-bounds error message accuracy (reports actual terrain grid dimensions).
13. Experiment persistence immutability in isolated temp directory.
14. Experiment replay exact match and trade-off compatibility verification.
"""

import os
import math
import tempfile
import pytest
import numpy as np
import rasterio
from pathlib import Path

from marswalk.core.terrain import load_and_process_terrain, TerrainGrid, TerrainConfig
from marswalk.core.planner import (
    ScienceWaypoint,
    plan_route,
    plan_sequential_multistop_route,
    PlannerConfig,
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
from marswalk.core.stress_test import (
    ScenarioDefinition,
    DisruptionType,
    run_scenario,
)
from marswalk.api.service import (
    plan_route_api,
    contingency_simulate_api,
    APIError,
)
from marswalk.api.workspace import (
    save_experiment,
    get_experiment,
    list_experiments,
    replay_saved_experiment,
    compare_two_experiments,
    WorkspaceError,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GEOTIFF_PATH = str(PROJECT_ROOT / "data" / "processed" / "jezero_ready_20m.tif")
WAYPOINTS_PATH = str(PROJECT_ROOT / "data" / "waypoints_jezero.json")


@pytest.fixture(scope="module")
def terrain_context():
    """Load default surveyed Jezero terrain once for the suite."""
    terrain = load_and_process_terrain(GEOTIFF_PATH)
    with rasterio.open(GEOTIFF_PATH) as src:
        transform = src.transform

    waypoints = [
        ScienceWaypoint(id="octavia_landing", name="Octavia E. Butler Landing", rc=(117, 157), priority_score=100.0),
        ScienceWaypoint(id="hawksbill_gap", name="Hawksbill Gap", rc=(95, 140), priority_score=85.0),
        ScienceWaypoint(id="skinner_ridge", name="Skinner Ridge", rc=(82, 133), priority_score=90.0),
        ScienceWaypoint(id="enchanted_lake", name="Enchanted Lake", rc=(75, 130), priority_score=75.0),
        ScienceWaypoint(id="delta_rim_overlook", name="Delta Rim Overlook", rc=(66, 128), priority_score=95.0),
    ]
    return terrain, transform, waypoints


@pytest.fixture
def baseline_payload():
    return {
        "start": {"row": 120, "col": 100},
        "goal": {"row": 120, "col": 130},
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "operational_limit_s": 28800.0,
        "dwell_time_per_stop_s": 900.0,
    }


# =============================================================================
# 1. Closed Corridor Avoidance & Boundary Tests
# =============================================================================

def test_closed_corridor_avoids_blocked_cells(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context
    base = plan_route_api(baseline_payload, terrain, transform, waypoints)
    mid_idx = len(base["path_rc"]) // 2
    r_mid, c_mid = base["path_rc"][mid_idx]

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "closed_corridor",
            "center_row": r_mid,
            "center_col": c_mid,
            "radius_m": 60.0,
            "name": "Midpoint Corridor Rockfall",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)
    assert res["is_feasible"] is True
    assert res["scenario_summary"]["distance_delta_m"] > 0.0

    blocked_set = set(tuple(cell) for cell in res["blocked_cells"])
    revised_path = [tuple(cell) for cell in res["revised_route"]["path_rc"]]
    for pt in revised_path:
        assert pt not in blocked_set, f"Revised path intersected blocked cell {pt}"


def test_closed_corridor_start_blocked_controlled_failure(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context
    start_r = baseline_payload["start"]["row"]
    start_c = baseline_payload["start"]["col"]

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "closed_corridor",
            "blocked_cells": [[start_r, start_c]],
            "name": "Landing Zone Blocked",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)
    assert res["is_feasible"] is False
    assert res["is_scenario_reachable"] is False
    assert "infeasible" in res["narrative"]["headline"].lower()
    assert "severed" in res["narrative"]["headline"].lower()


def test_closed_corridor_goal_blocked_controlled_failure(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context
    goal_r = baseline_payload["goal"]["row"]
    goal_c = baseline_payload["goal"]["col"]

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "closed_corridor",
            "blocked_cells": [[goal_r, goal_c]],
            "name": "Destination Ridge Blocked",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)
    assert res["is_feasible"] is False
    assert res["is_scenario_reachable"] is False
    assert "infeasible" in res["narrative"]["headline"].lower()


# =============================================================================
# 2. Difficult Terrain Soft Cost Tests
# =============================================================================

def test_difficult_terrain_small_vs_large_penalty(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context
    base = plan_route_api(baseline_payload, terrain, transform, waypoints)
    mid_idx = len(base["path_rc"]) // 2
    r_mid, c_mid = base["path_rc"][mid_idx]

    # Small penalty (1.2x): should absorb cost on path without detour
    payload_small = dict(baseline_payload)
    payload_small["custom_events"] = [
        {
            "event_type": "difficult_terrain",
            "center_row": r_mid,
            "center_col": c_mid,
            "radius_m": 40.0,
            "cost_multiplier": 1.2,
            "name": "Mild Regolith Slip",
        }
    ]
    res_small = contingency_simulate_api(payload_small, terrain, transform, waypoints)
    assert res_small["is_feasible"] is True
    assert res_small["scenario_summary"]["distance_delta_m"] == 0.0
    assert res_small["revised_route"]["cost"] > base["cost"]

    # Large penalty (8.0x): should force planner into lateral detour
    payload_large = dict(baseline_payload)
    payload_large["custom_events"] = [
        {
            "event_type": "difficult_terrain",
            "center_row": r_mid,
            "center_col": c_mid,
            "radius_m": 60.0,
            "cost_multiplier": 8.0,
            "name": "Severe Sand Mega-Ripple",
        }
    ]
    res_large = contingency_simulate_api(payload_large, terrain, transform, waypoints)
    assert res_large["is_feasible"] is True
    assert res_large["scenario_summary"]["distance_delta_m"] > 10.0


# =============================================================================
# 3. Reduced Mobility & Exact Velocity Scaling
# =============================================================================

def test_mobility_derating_pure_speed_multiplier_exact_ratio(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context
    base = plan_route_api(baseline_payload, terrain, transform, waypoints)

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "reduced_mobility",
            "speed_multiplier": 0.5,
            "name": "Actuator Thermal Derating",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)
    assert res["is_feasible"] is True
    assert res["scenario_summary"]["distance_delta_m"] == 0.0

    # Physical travel time must double exactly (within 0.1% rounding)
    base_t = base["travel_time_s"]
    revised_t = res["revised_route"]["travel_time_s"]
    assert pytest.approx(revised_t, rel=0.001) == base_t * 2.0


# =============================================================================
# 4. Reduced Time Budget in Seconds
# =============================================================================

def test_reduced_time_budget_seconds_feasibility_boundary(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context
    base = plan_route_api(baseline_payload, terrain, transform, waypoints)
    base_time_s = base["travel_time_s"]

    # Budget above baseline time -> FEASIBLE
    payload_ok = dict(baseline_payload)
    payload_ok["custom_events"] = [
        {
            "event_type": "reduced_time_budget",
            "reduced_time_budget_s": base_time_s + 600.0,
            "name": "Generous Budget Limit",
        }
    ]
    res_ok = contingency_simulate_api(payload_ok, terrain, transform, waypoints)
    assert res_ok["is_feasible"] is True

    # Budget below any possible traverse time -> INFEASIBLE
    payload_tight = dict(baseline_payload)
    payload_tight["custom_events"] = [
        {
            "event_type": "reduced_time_budget",
            "reduced_time_budget_s": 300.0,
            "name": "Strict Budget Limit",
        }
    ]
    res_tight = contingency_simulate_api(payload_tight, terrain, transform, waypoints)
    assert res_tight["is_feasible"] is False
    assert "budget violated" in res_tight["narrative"]["headline"].lower()


# =============================================================================
# 5. Operational Hold Accounting
# =============================================================================

def test_operational_hold_single_addition_in_timeline(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context
    base = plan_route_api(baseline_payload, terrain, transform, waypoints)

    payload = dict(baseline_payload)
    payload["custom_events"] = [
        {
            "event_type": "operational_hold",
            "delay_minutes": 25.0,
            "name": "Comms Diagnostic Hold",
        }
    ]

    res = contingency_simulate_api(payload, terrain, transform, waypoints)
    assert res["is_feasible"] is True
    assert res["scenario_summary"]["distance_delta_m"] == 0.0

    timeline = res["revised_timeline"]
    assert timeline["total_operational_delay_s"] == 1500.0
    assert pytest.approx(timeline["total_mission_time_s"], rel=0.001) == base["timeline"]["total_mission_time_s"] + 1500.0

    # Ensure dedicated scenario_delay event is present in timeline
    event_types = [e["event_type"] for e in timeline["events"]]
    assert event_types.count("scenario_delay") == 1


# =============================================================================
# 6. Compound Scenarios: Target Unavailable in Multi-Stop
# =============================================================================

def test_compound_scenario_target_unavailable_prunes_in_multistop(terrain_context):
    terrain, transform, waypoints = terrain_context
    ordered = [(120, 100), (120, 110), (125, 120), (120, 130)]
    w1 = ScienceWaypoint(id="target_alpha", name="Alpha Crater", rc=(120, 110), priority_score=80.0)
    w2 = ScienceWaypoint(id="target_beta", name="Beta Outcrop", rc=(125, 120), priority_score=90.0)

    base = plan_sequential_multistop_route(
        ordered_points=ordered,
        terrain=terrain,
        stop_ids=["target_alpha", "target_beta"],
        stop_priorities=[80.0, 90.0],
    )
    assert "target_alpha" in base.visited_waypoint_ids
    assert "target_beta" in base.visited_waypoint_ids

    events = [
        {"id": "drop_alpha", "event_type": "target_unavailable", "target_id": "target_alpha"},
        {"id": "speed_derate", "event_type": "reduced_mobility", "speed_multiplier": 0.8},
    ]

    scen_def, _ = compile_custom_contingency(events, terrain, baseline_route=base)
    comp = run_scenario(
        baseline_route=base,
        scenario=scen_def,
        start_rc=(120, 100),
        goal_rc=(120, 130),
        waypoints=[w1, w2],
        terrain=terrain,
        ordered_points=ordered,
        stop_ids=["target_alpha", "target_beta"],
        stop_priorities=[80.0, 90.0],
    )

    # target_alpha must be pruned; target_beta must be retained
    assert "target_alpha" not in comp.scenario_route.visited_waypoint_ids
    assert "target_beta" in comp.scenario_route.visited_waypoint_ids
    assert "target_alpha" in comp.regret_ledger.disabled_by_scenario_ids


def test_compound_scenario_order_invariance(terrain_context):
    terrain, _, _ = terrain_context
    ev1 = {"id": "ev_closure", "event_type": "closed_corridor", "center_rc": [120, 115], "radius_m": 50.0}
    ev2 = {"id": "ev_mobility", "event_type": "reduced_mobility", "speed_multiplier": 0.75}
    ev3 = {"id": "ev_hold", "event_type": "operational_hold", "delay_minutes": 20.0}

    scen_a, _ = compile_custom_contingency([ev1, ev2, ev3], terrain)
    scen_b, _ = compile_custom_contingency([ev3, ev1, ev2], terrain)
    scen_c, _ = compile_custom_contingency([ev2, ev3, ev1], terrain)

    assert set(scen_a.blocked_cells) == set(scen_b.blocked_cells) == set(scen_c.blocked_cells)
    assert scen_a.speed_multiplier == scen_b.speed_multiplier == scen_c.speed_multiplier
    assert scen_a.operational_delay_s == scen_b.operational_delay_s == scen_c.operational_delay_s


# =============================================================================
# 7. Identifier Validation & Adversarial Inputs
# =============================================================================

def test_duplicate_event_id_rejection(terrain_context):
    terrain, _, _ = terrain_context
    dup_events = [
        {"id": "duplicate_id", "event_type": "operational_hold", "delay_minutes": 10},
        {"id": "duplicate_id", "event_type": "reduced_mobility", "speed_multiplier": 0.8},
    ]
    with pytest.raises(ValueError, match="Duplicate event ID"):
        compile_custom_contingency(dup_events, terrain)


def test_adversarial_nan_inf_negative_inputs(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context

    # NaN radius
    p1 = dict(baseline_payload)
    p1["custom_events"] = [{"event_type": "closed_corridor", "center_rc": [120, 115], "radius_m": float("nan")}]
    with pytest.raises(APIError):
        contingency_simulate_api(p1, terrain, transform, waypoints)

    # Negative radius
    p2 = dict(baseline_payload)
    p2["custom_events"] = [{"event_type": "closed_corridor", "center_rc": [120, 115], "radius_m": -30.0}]
    with pytest.raises(APIError):
        contingency_simulate_api(p2, terrain, transform, waypoints)

    # Inf speed
    p3 = dict(baseline_payload)
    p3["custom_events"] = [{"event_type": "reduced_mobility", "speed_multiplier": float("inf")}]
    with pytest.raises(APIError):
        contingency_simulate_api(p3, terrain, transform, waypoints)

    # Excessive speed (> 1.0)
    p4 = dict(baseline_payload)
    p4["custom_events"] = [{"event_type": "reduced_mobility", "speed_multiplier": 2.5}]
    with pytest.raises(APIError):
        contingency_simulate_api(p4, terrain, transform, waypoints)


def test_adversarial_out_of_bounds_grid_message(terrain_context):
    terrain, _, _ = terrain_context
    with pytest.raises(ValueError, match="outside the 0-249 grid bounds"):
        validate_custom_event_dict({
            "event_type": "closed_corridor",
            "center_row": 9999,
            "center_col": -10,
        }, terrain)


# =============================================================================
# 8. Persistence Integrity, Isolation & Replay Tests
# =============================================================================

def test_experiment_persistence_isolation_and_immutability(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context
    base = plan_route_api(baseline_payload, terrain, transform, waypoints)

    with tempfile.TemporaryDirectory() as tmp_dir:
        exp_payload = {
            "experiment_id": "test_m9s_persist_01",
            "name": "Milestone 9S Temp Experiment",
            "description": "Persistence isolation smoke test",
            "mission_snapshot": {"canonical_mission": baseline_payload, "input_fingerprint": base["input_fingerprint"]},
            "baseline_route": base,
            "scenarios_evaluated": [{"scenario_id": "scen_test", "name": "Test Disruption"}],
        }

        saved = save_experiment(exp_payload, experiments_dir=tmp_dir, allow_overwrite=False)
        assert saved["experiment_id"] == "test_m9s_persist_01"

        # Read back
        loaded = get_experiment("test_m9s_persist_01", experiments_dir=tmp_dir)
        assert loaded["name"] == "Milestone 9S Temp Experiment"

        # Attempt overwrite must raise WorkspaceError (immutability)
        with pytest.raises(WorkspaceError, match="already exists"):
            save_experiment(exp_payload, experiments_dir=tmp_dir, allow_overwrite=False)

        # Listing in tmp dir
        listed = list_experiments(experiments_dir=tmp_dir)
        assert len(listed) == 1
        assert listed[0]["experiment_id"] == "test_m9s_persist_01"


def test_experiment_replay_and_stale_detection(terrain_context, baseline_payload):
    terrain, transform, waypoints = terrain_context
    base = plan_route_api(baseline_payload, terrain, transform, waypoints)

    with tempfile.TemporaryDirectory() as tmp_dir:
        exp_payload = {
            "experiment_id": "test_m9s_replay_base",
            "name": "Base Replay Experiment",
            "mission_snapshot": {"canonical_mission": baseline_payload, "input_fingerprint": base["input_fingerprint"]},
            "baseline_route": base,
            "scenarios_evaluated": [],
        }
        save_experiment(exp_payload, experiments_dir=tmp_dir)

        # Replay should match exactly
        replay_res = replay_saved_experiment(
            "test_m9s_replay_base",
            terrain=terrain,
            transform=transform,
            waypoints=waypoints,
            experiments_dir=tmp_dir,
        )
        assert replay_res["is_exact_match"] is True
        assert replay_res["lifecycle_state"] == "reproducible"

        # Test cross-experiment comparison
        comp_res = compare_two_experiments(
            "test_m9s_replay_base",
            replay_res["experiment_id"],
            experiments_dir=tmp_dir,
        )
        assert comp_res["is_compatible"] is True
        assert comp_res["deltas"]["distance_delta_m"] == 0.0
