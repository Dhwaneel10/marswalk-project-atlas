"""
MarsWalk 2.0 / Project Atlas — Adversarial & Qualification Test Suite for Astronaut EVA Mode.

PHASE 4 INDEPENDENT QUALIFICATION TESTS:
1. Zero oxygen availability & capacity exhaustion.
2. Negative, zero, or impossible API configuration parameters.
3. Destination and base coordinates outside terrain raster coverage.
4. No feasible return route (barrier blocking return-to-base corridor).
5. Consumable reserve exceeded during return transit.
6. Severe terrain slope (>= 20°) impassability.
7. Corrupted terrain data (NaN elevations, infinite slopes).
8. Environmental contingencies: dust storm opacity escalation and comms blackout.
9. Full multi-event contingency lifecycle (NOMINAL -> CAUTION -> SAFE_HOLD -> RETURN_TO_BASE -> COMPLETED / MISSION_ABORTED).
10. Rover Mode isolation during concurrent or successive EVA operations.
"""

import os
import json
import pytest
import numpy as np
import rasterio

from marswalk.core.terrain import TerrainGrid, TerrainConfig, load_and_process_terrain
from marswalk.core.planner import ScienceWaypoint
from marswalk.data.ingest import query_elevation_at_lonlat
from marswalk.core.astronaut_eva import (
    EVAMissionState,
    EVAContingencyType,
    HumanMobilityConfig,
    EVAConsumableBudget,
    EVAConsumableUsage,
    calculate_human_step_cost,
    calculate_human_walk_time_and_metabolics,
    evaluate_eva_consumable_budget,
    plan_human_eva_leg,
    plan_three_astronaut_eva_routes,
    execute_eva_contingency_workflow,
)
from marswalk.api.service import (
    plan_astronaut_eva_api,
    eva_contingency_api,
    plan_route_api,
    APIError,
)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSED_TIFF = os.path.join(_REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")
WAYPOINTS_JSON = os.path.join(_REPO_ROOT, "data", "waypoints_jezero.json")


@pytest.fixture
def jezero_environment():
    """Load authentic Jezero CTX terrain grid, affine transform, and science waypoints."""
    assert os.path.exists(PROCESSED_TIFF), f"Missing processed GeoTIFF: {PROCESSED_TIFF}"
    grid = load_and_process_terrain(PROCESSED_TIFF)
    with rasterio.open(PROCESSED_TIFF) as src:
        transform = src.transform

    waypoints = []
    if os.path.exists(WAYPOINTS_JSON):
        with open(WAYPOINTS_JSON, "r", encoding="utf-8") as f:
            wp_data = json.load(f)
        for wp in wp_data.get("waypoints", []):
            elev, r, c = query_elevation_at_lonlat(PROCESSED_TIFF, wp["lon_deg"], wp["lat_deg"])
            waypoints.append(
                ScienceWaypoint(
                    id=wp["id"],
                    name=wp["name"],
                    rc=(r, c),
                    priority_score=wp.get("priority_score", 0.0),
                )
            )
    return {
        "grid": grid,
        "transform": transform,
        "waypoints": waypoints,
    }


# ---------------------------------------------------------------------------
# 1. Zero oxygen availability & capacity exhaustion
# ---------------------------------------------------------------------------
def test_adversarial_zero_oxygen_and_capacity_exhaustion(jezero_environment):
    grid = jezero_environment["grid"]
    base_rc = (120, 120)
    target_rc = (125, 125)

    # Exhausted oxygen capacity (0.0 L)
    b_zero = EVAConsumableBudget(primary_o2_capacity_liters=0.0, emergency_o2_reserve_liters=0.0)
    res = plan_three_astronaut_eva_routes(
        base_rc=base_rc,
        science_stops=[{"name": "Adversarial Target", "row": target_rc[0], "col": target_rc[1]}],
        terrain=grid,
        consumable_budget=b_zero,
    )

    for p_key, r in res["routes"].items():
        assert r["is_reachable"] is True
        # Excursion cannot be feasible with zero oxygen
        assert r["is_feasible"] is False
        assert r["consumables"]["remaining_o2_liters"] == 0.0
        assert r["consumables"]["o2_reserve_margin_pct"] == 0.0
        assert any("consumable" in w.lower() for w in r["warnings"])


# ---------------------------------------------------------------------------
# 2. Negative, zero, or impossible API configuration parameters
# ---------------------------------------------------------------------------
def test_adversarial_negative_and_impossible_api_config(jezero_environment):
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]
    base = {"row": 100, "col": 100}
    target = {"row": 105, "col": 105}

    # Case A: Negative walk speed
    with pytest.raises(APIError) as exc_info:
        plan_astronaut_eva_api({
            "base": base,
            "science_targets": [target],
            "walking_profile": {"nominal_walk_speed_kmh": -2.5},
        }, grid, transform)
    assert exc_info.value.status_code == 400
    assert "ERR_VALIDATION_FAILED" in exc_info.value.error_code

    # Case B: Impossible slope cutoff (> 45 deg or negative)
    with pytest.raises(APIError) as exc_info:
        plan_astronaut_eva_api({
            "base": base,
            "science_targets": [target],
            "walking_profile": {"max_walk_slope_deg": -10.0},
        }, grid, transform)
    assert exc_info.value.status_code == 400

    # Case C: Negative carried gear mass
    with pytest.raises(APIError) as exc_info:
        plan_astronaut_eva_api({
            "base": base,
            "science_targets": [target],
            "walking_profile": {"carried_gear_mass_kg": -50.0},
        }, grid, transform)
    assert exc_info.value.status_code == 400

    # Case D: Emergency reserve exceeding total tank capacity
    with pytest.raises(APIError) as exc_info:
        plan_astronaut_eva_api({
            "base": base,
            "science_targets": [target],
            "consumable_budget": {
                "primary_o2_capacity_liters": 500.0,
                "emergency_o2_reserve_liters": 600.0,
            },
        }, grid, transform)
    assert exc_info.value.status_code == 400

    # Case E: Negative dwell time
    with pytest.raises(APIError) as exc_info:
        plan_astronaut_eva_api({
            "base": base,
            "science_targets": [target],
            "dwell_time_per_target_s": -300.0,
        }, grid, transform)
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# 3. Destination and base coordinates outside terrain raster coverage
# ---------------------------------------------------------------------------
def test_adversarial_destination_outside_terrain_coverage(jezero_environment):
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]
    H, W = grid.shape

    # Outside bounds base
    with pytest.raises(APIError) as exc_info:
        plan_astronaut_eva_api({
            "base": {"row": H + 500, "col": W + 500},
            "science_targets": [{"row": 100, "col": 100}],
        }, grid, transform)
    assert exc_info.value.status_code == 400

    # In contingency: gracefully handles out-of-bounds coordinates without crashing
    res = execute_eva_contingency_workflow(
        current_astronaut_rc=(H + 100, W + 100),
        base_rc=(100, 100),
        contingency_type=EVAContingencyType.DUST_EVENT,
        terrain=grid,
    )
    assert res["mission_state"] == "SAFE_HOLD"
    assert "outside terrain raster" in res["advisory"].lower()
    assert res["emergency_return_route"]["is_reachable"] is False


# ---------------------------------------------------------------------------
# 4. No feasible return route (barrier blocking return corridor)
# ---------------------------------------------------------------------------
def test_adversarial_no_feasible_return_route(jezero_environment):
    grid = jezero_environment["grid"]
    H, W = grid.shape
    base_rc = (150, 150)
    target_rc = (150, 170)

    # Completely surround the target inside an enclosed box
    # with an opening at (150, 165) that is open outbound and sealed for return
    blocked = np.zeros((H, W), dtype=bool)
    for r in range(145, 156):
        blocked[r, 165] = True
        blocked[r, 175] = True
    for c in range(165, 176):
        blocked[145, c] = True
        blocked[155, c] = True

    # Outbound gap
    blocked[150, 165] = False
    leg_out = plan_human_eva_leg(base_rc, target_rc, grid, blocked_mask=blocked)
    assert leg_out.is_reachable is True

    # Now seal the box completely for return
    blocked[150, 165] = True
    leg_ret = plan_human_eva_leg(target_rc, base_rc, grid, blocked_mask=blocked)
    assert leg_ret.is_reachable is False

    # Contingency return evaluator must report SAFE_HOLD and is_return_feasible=False
    cont_res = execute_eva_contingency_workflow(
        current_astronaut_rc=target_rc,
        base_rc=base_rc,
        contingency_type=EVAContingencyType.ROUTE_OBSTRUCTION,
        terrain=grid,
        blocked_mask=blocked,
    )
    assert cont_res["mission_state"] == "SAFE_HOLD"
    assert cont_res["emergency_return_route"]["is_reachable"] is False
    assert "corridor blocked" in cont_res["advisory"].lower()


# ---------------------------------------------------------------------------
# 5. Consumable reserve exceeded during return transit
# ---------------------------------------------------------------------------
def test_adversarial_consumable_reserve_exceeded_during_return(jezero_environment):
    grid = jezero_environment["grid"]
    base_rc = (100, 100)
    target_rc = (115, 115)

    # Tight oxygen budget: 130 L total capacity with 120 L mandatory reserve.
    # Leaving only 10 L for the entire outbound + return excursion.
    b_tight = EVAConsumableBudget(
        primary_o2_capacity_liters=130.0,
        emergency_o2_reserve_liters=120.0,
    )

    res = plan_three_astronaut_eva_routes(
        base_rc=base_rc,
        science_stops=[{"name": "Outcrop A", "row": target_rc[0], "col": target_rc[1]}],
        terrain=grid,
        consumable_budget=b_tight,
    )

    for p_key, r in res["routes"].items():
        assert r["is_reachable"] is True
        # Consumable expenditure will exceed 10 L, breaching the 120 L reserve threshold
        assert r["is_feasible"] is False
        assert r["consumables"]["remaining_o2_liters"] < 120.0
        assert any("consumable" in w.lower() for w in r["warnings"])


# ---------------------------------------------------------------------------
# 6. Severe terrain slope (>= 20°) impassability
# ---------------------------------------------------------------------------
def test_adversarial_severe_terrain_slope_barrier(jezero_environment):
    grid = jezero_environment["grid"]
    
    # Locate a cell with steep slope (>= 20°)
    steep_mask = grid.slope_deg >= 20.0
    assert np.any(steep_mask), "Terrain DEM must contain steep slopes for Jezero crater scarp"
    steep_indices = np.argwhere(steep_mask)
    steep_rc = tuple(steep_indices[0])

    # Human walking cost to enter this steep cell must be infinity
    neighbor_rc = (steep_rc[0] - 1, steep_rc[1])
    cost = calculate_human_step_cost(neighbor_rc, steep_rc, grid)
    assert np.isinf(cost), f"Step cost to {steep_rc} with slope {grid.slope_deg[steep_rc]:.1f}° must be infinity"

    # Route attempting to terminate directly on an impassable slope must fail cleanly
    leg = plan_human_eva_leg(neighbor_rc, steep_rc, grid)
    assert leg.is_reachable is False
    assert leg.path == []


# ---------------------------------------------------------------------------
# 7. Corrupted terrain data (NaN elevations, infinite slopes)
# ---------------------------------------------------------------------------
def test_adversarial_corrupted_nan_elevation_and_slope(jezero_environment):
    grid = jezero_environment["grid"]
    u = (50, 50)
    v = (50, 51)

    # Temporarily inject NaN into elevation
    orig_z = grid.elevation[v[0], v[1]]
    try:
        grid.elevation[v[0], v[1]] = np.nan
        cost = calculate_human_step_cost(u, v, grid)
        # DEFECT-13-01: must return infinity and not bypass cutoff or produce NaN cost
        assert np.isinf(cost)
        assert not np.isnan(cost)
    finally:
        grid.elevation[v[0], v[1]] = orig_z

    # Temporarily inject inf into slope
    orig_slope = grid.slope_deg[v[0], v[1]]
    try:
        grid.slope_deg[v[0], v[1]] = np.inf
        cost = calculate_human_step_cost(u, v, grid)
        assert np.isinf(cost)
    finally:
        grid.slope_deg[v[0], v[1]] = orig_slope


# ---------------------------------------------------------------------------
# 8. Environmental contingencies: dust storm opacity escalation and comms blackout
# ---------------------------------------------------------------------------
def test_adversarial_comms_loss_and_dust_storm_escalation(jezero_environment):
    grid = jezero_environment["grid"]
    curr_rc = (120, 120)
    base_rc = (100, 100)

    # Moderate dust event (tau = 1.2) -> CAUTION
    mod_dust = execute_eva_contingency_workflow(
        current_astronaut_rc=curr_rc,
        base_rc=base_rc,
        contingency_type=EVAContingencyType.DUST_EVENT,
        terrain=grid,
        dust_optical_depth=1.2,
    )
    assert mod_dust["mission_state"] == "CAUTION"
    assert mod_dust["requires_immediate_return"] is False

    # Severe dust storm (tau = 4.0) -> Escalates to RETURN_TO_BASE
    sev_dust = execute_eva_contingency_workflow(
        current_astronaut_rc=curr_rc,
        base_rc=base_rc,
        contingency_type=EVAContingencyType.DUST_EVENT,
        terrain=grid,
        dust_optical_depth=4.0,
    )
    assert sev_dust["mission_state"] == "RETURN_TO_BASE"
    assert sev_dust["requires_immediate_return"] is True
    assert "severe regional dust storm" in sev_dust["advisory"].lower()

    # RF Comms Loss -> CAUTION with inertial visor guidance
    comms = execute_eva_contingency_workflow(
        current_astronaut_rc=curr_rc,
        base_rc=base_rc,
        contingency_type=EVAContingencyType.COMMS_LOSS,
        terrain=grid,
    )
    assert comms["mission_state"] == "CAUTION"
    assert "radio" in comms["advisory"].lower() or "rf" in comms["advisory"].lower() or "inertial" in comms["advisory"].lower()


# ---------------------------------------------------------------------------
# 9. Full multi-event contingency lifecycle transitions
# ---------------------------------------------------------------------------
def test_adversarial_repeated_contingencies_and_full_lifecycle(jezero_environment):
    grid = jezero_environment["grid"]
    curr_rc = (110, 110)
    base_rc = (100, 100)

    # 1. NOMINAL -> CAUTION (comms dip)
    s1 = execute_eva_contingency_workflow(
        current_astronaut_rc=curr_rc,
        base_rc=base_rc,
        contingency_type=EVAContingencyType.COMMS_LOSS,
        terrain=grid,
        current_state="NOMINAL",
    )
    assert s1["mission_state"] == "CAUTION"

    # 2. CAUTION -> RETURN_TO_BASE (low consumable alert)
    s2 = execute_eva_contingency_workflow(
        current_astronaut_rc=curr_rc,
        base_rc=base_rc,
        contingency_type=EVAContingencyType.CONSUMABLE_RESERVE_WARNING,
        terrain=grid,
        current_state=s1["mission_state"],
    )
    assert s2["mission_state"] == "RETURN_TO_BASE"
    assert s2["requires_immediate_return"] is True

    # 3. RETURN_TO_BASE -> COMPLETED (arrival at base)
    s3 = execute_eva_contingency_workflow(
        current_astronaut_rc=base_rc,
        base_rc=base_rc,
        contingency_type=EVAContingencyType.DUST_EVENT,
        terrain=grid,
        current_state=s2["mission_state"],
    )
    assert s3["mission_state"] == "COMPLETED"
    assert "airlock" in s3["advisory"].lower()

    # 4. Unrecoverable failure -> MISSION_ABORTED
    s_abort = execute_eva_contingency_workflow(
        current_astronaut_rc=curr_rc,
        base_rc=base_rc,
        contingency_type=EVAContingencyType.CONSUMABLE_RESERVE_WARNING,
        terrain=grid,
        current_state="RETURN_TO_BASE",
        remaining_o2_liters=0.0,
    )
    assert s_abort["mission_state"] == "MISSION_ABORTED"
    assert "aborted" in s_abort["advisory"].lower()


# ---------------------------------------------------------------------------
# 10. Rover Mode isolation during concurrent or successive EVA operations
# ---------------------------------------------------------------------------
def test_adversarial_rover_mode_isolation_during_eva(jezero_environment):
    grid = jezero_environment["grid"]
    transform = jezero_environment["transform"]
    waypoints = jezero_environment["waypoints"]
    start = {"row": 100, "col": 100}
    goal = {"row": 108, "col": 108}

    # Run Rover planning
    rover_res = plan_route_api({
        "start": start,
        "goal": goal,
        "profile": "balanced",
    }, grid, transform, waypoints)
    assert rover_res["is_reachable"] is True
    assert rover_res["profile"] == "balanced"
    rover_cost = rover_res["cost"]
    rover_path = rover_res["path_rc"]

    # Run EVA planning with high carried gear mass
    eva_res = plan_astronaut_eva_api({
        "base": start,
        "science_targets": [goal],
        "walking_profile": {"carried_gear_mass_kg": 50.0},
    }, grid, transform)
    assert "routes" in eva_res

    # Re-run Rover planning; verify total cost and route coordinates are completely identical
    rover_res_post = plan_route_api({
        "start": start,
        "goal": goal,
        "profile": "balanced",
    }, grid, transform, waypoints)
    assert rover_res_post["cost"] == rover_cost
    assert rover_res_post["path_rc"] == rover_path
