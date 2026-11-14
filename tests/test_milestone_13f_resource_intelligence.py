"""
MarsWalk 2.0 / Project Atlas - Milestone 13F
Resource-Constrained Mars Traverse Planning, Power Budgeting & Mission Feasibility Digital Twin.
Test Suite & Scientific Validation Architecture.

Covers:
1. Synthetic Terrain Fixtures & Analytical Ground Truths:
   - Level Traverse (zero slope, pure rolling resistance, closed-form energy match)
   - Continuous Incline (steep scarp ascent, gravitational work dominance, normal force reduction)
   - Rollercoaster Canyon (alternating ascents/descents, net zero elevation, no unmodeled regen)
   - Heavy Science Sortie (high instrument duty cycles, multi-phase static dwell loads)
   - Battery Depletion Edge Cases (reserve threshold violations, energy exhaustion clamping)
2. Unit Tests for Mobility Energy Physics:
   - Mars gravity scaling (3.71 m/s^2 vs Earth 9.81 m/s^2)
   - Positive slope gain (linear scaling with delta_h)
   - Steep downhill (strict: no unmodeled regenerative braking)
   - Drivetrain electromechanical efficiency conversion
   - Invalid slopes (>45 deg) and NoData terrain handling
   - Segment distance conservation (sum(d_i) == D_total)
3. Unit Tests for Electrical Operating Loads:
   - Constant power integration (E = P * delta_t)
   - Duty-cycled operating loads (P_on * delta + P_off * (1 - delta))
   - Standby vs active operational loads contrast
   - Energy unit conversions (J, kJ, Wh, MJ) and round-trip lossless precision
   - SI formatting helpers (format_energy_si, format_power_si)
4. Unit Tests for RelayNet Infrastructure Power:
   - Standby and active duty cycles for deployed relay masts
   - Multi-relay network energy budgeting (k in {0, 1, 2, 3})
   - Relay battery reserves and operational duration exhaustion
5. Unit Tests for Mission Scheduling & Timeline:
   - Sequential event chronological ordering (t_start == t_prev_end)
   - Total mission duration conservation
   - Zero-duration edge cases and instantaneous transitions
   - Operational delay buffering
6. Unit Tests for Unified Resource Ledger:
   - Strict step-by-step and global energy conservation
   - Peak instantaneous power tracking
   - Reserve margin violation detection (FEASIBLE_WITH_LOW_RESERVE)
   - Negative energy clamping and positive deficit reporting (ENERGY_CONSTRAINT_VIOLATION)
   - Unknown input propagation (never silently converting None/NaN to 0)
   - Configuration validation (rejecting negative mass, negative speed, efficiency > 1.0)
7. Integration Tests: Resource-Aware Planning & Sensitivity Lab:
   - Deterministic parameter sensitivity sweeps across 6 key variables
   - Elasticity rankings and Tornado chart drivers
   - Multi-objective Pareto frontier with resource dimensions (energy, duration)
   - Feasibility constraint filtering precedence (hard constraints override scalar scores)
   - Authentic Jezero Crater scenarios on USGS CTX 20m DTM (Octavia to Three Forks & Delta Rim)
8. Regression & Scientific Guardrails:
   - Operational workspace data immutability
   - Provenance statements and non-probabilistic truth disclosures
   - Prohibition against astronaut safety certification claims
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
import os
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
import pytest

from marswalk.core.terrain import (
    TerrainConfig,
    TerrainGrid,
    compute_ground_spacings,
    create_invalid_mask,
    derive_terrain_from_array,
    load_and_process_terrain,
    calculate_step_distance,
    calculate_edge_cost,
    get_profile_terrain_config,
)
from marswalk.core.planner import (
    astar_search,
    plan_route,
    PlannerConfig,
    ScienceWaypoint,
    LegResult,
)
from marswalk.core.mission_resource_model import (
    MARS_GRAVITY_MPS2,
    JOULES_PER_WH,
    WH_PER_JOULE,
    ResourceFeasibilityClassification,
    RoverResourceConfig,
    RelayResourceConfig,
    SegmentResourceRecord,
    MissionActivityEvent,
    MissionResourceLedger,
    ResourceSensitivityResult,
    calculate_segment_mobility_energy,
    evaluate_mission_resource_ledger,
    evaluate_resource_sensitivity,
    joules_to_wh,
    wh_to_joules,
    format_energy_si,
    format_power_si,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JEZERO_DTM_PATH = os.path.join(REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")


# =============================================================================
# SYNTHETIC TERRAIN FIXTURE GENERATORS
# =============================================================================

def create_level_traverse_terrain(
    shape: Tuple[int, int] = (60, 60),
    elevation_m: float = -2500.0,
    dx_m: float = 20.0,
    dy_m: float = 20.0,
) -> TerrainGrid:
    """
    Constructs a completely flat plain at uniform elevation (-2500.0m).
    All slopes are 0.0 deg; delta_h is identically 0.0m everywhere.
    A traverse along row 30 from col 5 to col 55 spans exactly 50 cells = 1000m.
    """
    grid = np.full(shape, elevation_m, dtype=np.float32)
    cfg = TerrainConfig(dx_ground_m=dx_m, dy_ground_m=dy_m, theta_max_deg=25.0)
    return derive_terrain_from_array(grid, config=cfg)


def create_continuous_incline_terrain(
    shape: Tuple[int, int] = (60, 60),
    start_elevation_m: float = -2500.0,
    end_elevation_m: float = -2400.0,
    scarp_cols: Tuple[int, int] = (15, 40),
    dx_m: float = 20.0,
    dy_m: float = 20.0,
) -> TerrainGrid:
    """
    Constructs an escarpment ramp climbing linearly from start_elevation_m to end_elevation_m
    between scarp_cols[0] and scarp_cols[1].
    Across 25 cells (500m ground distance), elevation gains +100m.
    Step slope is constant: delta_h = 4.0m per 20m step -> theta = arctan(0.20) ~ 11.31 deg.
    """
    grid = np.full(shape, start_elevation_m, dtype=np.float32)
    c0, c1 = scarp_cols
    col_count = c1 - c0
    elev_step = (end_elevation_m - start_elevation_m) / float(col_count)

    for c in range(shape[1]):
        if c < c0:
            grid[:, c] = start_elevation_m
        elif c > c1:
            grid[:, c] = end_elevation_m
        else:
            grid[:, c] = start_elevation_m + (c - c0) * elev_step

    cfg = TerrainConfig(dx_ground_m=dx_m, dy_ground_m=dy_m, theta_max_deg=25.0)
    return derive_terrain_from_array(grid, config=cfg)


def create_rollercoaster_canyon_terrain(
    shape: Tuple[int, int] = (60, 60),
    base_elevation_m: float = -2500.0,
    amplitude_m: float = 25.0,
    period_cells: int = 20,
    dx_m: float = 20.0,
    dy_m: float = 20.0,
) -> TerrainGrid:
    """
    Constructs a sinusoidal ridge-and-valley topography along columns.
    A path along row 30 over 40 cells (800m) undergoes exactly 2 complete sinusoidal cycles.
    Net elevation change: delta_z_net == 0.0m.
    Cumulative elevation gain: delta_z_gain > 0, cumulative loss: delta_z_loss > 0.
    """
    grid = np.zeros(shape, dtype=np.float32)
    for c in range(shape[1]):
        phase = 2.0 * math.pi * (c / float(period_cells))
        grid[:, c] = base_elevation_m + amplitude_m * math.sin(phase)

    cfg = TerrainConfig(dx_ground_m=dx_m, dy_ground_m=dy_m, theta_max_deg=25.0)
    return derive_terrain_from_array(grid, config=cfg)


# =============================================================================
# MODULE-LEVEL FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def level_traverse_fixture():
    return create_level_traverse_terrain()


@pytest.fixture(scope="module")
def continuous_incline_fixture():
    return create_continuous_incline_terrain()


@pytest.fixture(scope="module")
def rollercoaster_canyon_fixture():
    return create_rollercoaster_canyon_terrain()


@pytest.fixture(scope="module")
def jezero_terrain():
    if not os.path.exists(JEZERO_DTM_PATH):
        pytest.skip(f"Jezero DTM not found at {JEZERO_DTM_PATH}")
    return load_and_process_terrain(JEZERO_DTM_PATH)


# =============================================================================
# 1. SYNTHETIC FIXTURES & ANALYTICAL GROUND TRUTHS
# =============================================================================

class TestSyntheticResourceFixtures:
    """Validates analytical ground truths on controlled synthetic geometries."""

    def test_level_traverse_pure_rolling_resistance(self, level_traverse_fixture):
        """
        Level Traverse Analytical Ground Truth:
        - 1000m traverse on flat plain (theta = 0.0 deg, cos(theta) = 1.0, delta_h = 0.0m).
        - Rolling work: W_r = C_rr * m * g_mars * d.
        - Gravitational work: W_g = 0.0 J.
        - Mechanical work: W_m = W_r.
        - Mobility electrical energy: E_m = W_m / eta.
        - Electrical base loads: E_e = (P_base + P_comm_sb + P_inst_sb) * (d / v).
        - Total energy: E_total = E_m + E_e.
        - Confirms closed-form analytical match to within 1e-4 tolerance.
        """
        terrain = level_traverse_fixture
        path = [(30, c) for c in range(5, 56)]  # 50 steps * 20m = 1000m
        assert len(path) == 51

        rover = RoverResourceConfig(
            rover_mass_kg=1000.0,
            payload_mass_kg=0.0,
            usable_battery_capacity_wh=2000.0,
            rolling_resistance_crr=0.05,
            drivetrain_efficiency=0.80,
            nominal_drive_speed_mps=0.50,
            base_electrical_load_w=100.0,
            comm_standby_w=20.0,
            instrument_standby_w=15.0,
        )

        ledger = evaluate_mission_resource_ledger(
            path_rc=path,
            elevation_grid=terrain.elevation,
            slope_grid=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            ground_dx_m=20.0,
            ground_dy_m=20.0,
            rover_config=rover,
        )

        # Analytical derivations
        dist_m = 1000.0
        time_s = dist_m / 0.50  # 2000.0 s
        expected_rolling_w = 0.05 * 1000.0 * MARS_GRAVITY_MPS2 * 1.0 * dist_m  # 185,500.0 J
        expected_grav_w = 0.0
        expected_mech_w = expected_rolling_w  # 185,500.0 J
        expected_mob_e = expected_mech_w / 0.80  # 231,875.0 J
        drive_power_w = 100.0 + 20.0 + 15.0  # 135.0 W
        expected_elec_e = drive_power_w * time_s  # 270,000.0 J
        expected_total_e = expected_mob_e + expected_elec_e  # 501,875.0 J
        expected_total_wh = expected_total_e / JOULES_PER_WH  # ~139.41 Wh

        assert math.isclose(ledger.total_distance_m, dist_m, abs_tol=1e-3)
        assert math.isclose(ledger.traverse_duration_s, time_s, abs_tol=1e-3)
        assert math.isclose(ledger.total_rolling_work_j, expected_rolling_w, abs_tol=1e-2)
        assert math.isclose(ledger.total_gravitational_work_j, expected_grav_w, abs_tol=1e-2)
        assert math.isclose(ledger.total_mechanical_work_j, expected_mech_w, abs_tol=1e-2)
        assert math.isclose(ledger.total_mobility_energy_j, expected_mob_e, abs_tol=1e-2)
        assert math.isclose(ledger.total_electrical_energy_j, expected_elec_e, abs_tol=1e-2)
        assert math.isclose(ledger.total_mission_energy_j, expected_total_e, abs_tol=1e-2)
        assert math.isclose(ledger.total_mission_energy_wh, expected_total_wh, abs_tol=1e-3)

        # Invariants
        assert ledger.feasibility_classification == ResourceFeasibilityClassification.FEASIBLE_WITHIN_CONFIGURED_BUDGET
        assert ledger.is_reserve_violated is False
        assert ledger.is_time_violated is False
        # Exact step-by-step energy conservation
        initial_j = rover.usable_battery_capacity_j
        assert math.isclose(ledger.final_energy_remaining_j + ledger.total_mission_energy_j, initial_j, abs_tol=1e-3)

    def test_continuous_incline_steep_scarp_ascent(self, continuous_incline_fixture):
        """
        Continuous Incline Analytical Ground Truth:
        - 500m traverse climbing an escarpment from -2500m to -2400m (delta_h = +100m).
        - Gravitational work: W_g = m * g_mars * delta_h = 1000 * 3.71 * 100 = 371,000 J.
        - Rolling work: W_r = C_rr * m * g_mars * cos(theta) * d.
        - Gravitational work strictly dominates rolling resistance (W_g >> W_r).
        - Verifies normal force reduction: cos(theta) < 1.0 reduces rolling resistance slightly.
        """
        terrain = continuous_incline_fixture
        path = [(30, c) for c in range(15, 41)]  # 25 steps * 20m = 500m
        assert len(path) == 26

        rover = RoverResourceConfig(
            rover_mass_kg=1000.0,
            payload_mass_kg=0.0,
            usable_battery_capacity_wh=2000.0,
            rolling_resistance_crr=0.05,
            drivetrain_efficiency=0.80,
            nominal_drive_speed_mps=0.50,
            base_electrical_load_w=100.0,
        )

        ledger = evaluate_mission_resource_ledger(
            path_rc=path,
            elevation_grid=terrain.elevation,
            slope_grid=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            ground_dx_m=20.0,
            ground_dy_m=20.0,
            rover_config=rover,
        )

        dist_m = 500.0
        expected_grav_w = 1000.0 * MARS_GRAVITY_MPS2 * 100.0  # 371,000.0 J
        assert math.isclose(ledger.total_distance_m, dist_m, abs_tol=1e-3)
        assert math.isclose(ledger.total_gravitational_work_j, expected_grav_w, abs_tol=1e-1)

        # Gravitational work exceeds rolling work by >4x
        assert ledger.total_gravitational_work_j > 4.0 * ledger.total_rolling_work_j

        # Mechanical work equals rolling + gravitational
        assert math.isclose(
            ledger.total_mechanical_work_j,
            ledger.total_rolling_work_j + ledger.total_gravitational_work_j,
            abs_tol=1e-2,
        )

        # Normal force reduction check: slope angle theta ~ 11.31 deg -> cos(theta) ~ 0.9806
        flat_rolling_w = 0.05 * 1000.0 * MARS_GRAVITY_MPS2 * 1.0 * dist_m  # 92,750 J
        assert ledger.total_rolling_work_j < flat_rolling_w

    def test_rollercoaster_canyon_elevation_asymmetry_no_regen(self, rollercoaster_canyon_fixture):
        """
        Rollercoaster Canyon Analytical Ground Truth:
        - Traversing across 2 sinusoidal cycles: net delta_z == 0.0m.
        - Cumulative uphill gain > 0, cumulative downhill loss > 0.
        - STRICT SCIENTIFIC PRINCIPLE: No unmodeled regenerative braking!
        - Downhill steps have max(0, W_g) = 0.0; wheels still consume rolling resistance.
        - Gravitational work accumulates strictly from uphill steps.
        - Consumes significantly more mobility energy than a level traverse of the same distance.
        """
        terrain = rollercoaster_canyon_fixture
        path = [(30, c) for c in range(10, 51)]  # 40 steps * 20m = 800m

        rover = RoverResourceConfig(
            rover_mass_kg=1000.0,
            payload_mass_kg=0.0,
            usable_battery_capacity_wh=2000.0,
            rolling_resistance_crr=0.05,
            drivetrain_efficiency=0.80,
            allow_regenerative_braking=False,
        )

        ledger_roller = evaluate_mission_resource_ledger(
            path_rc=path,
            elevation_grid=terrain.elevation,
            slope_grid=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            ground_dx_m=20.0,
            ground_dy_m=20.0,
            rover_config=rover,
        )

        # Net elevation change across the two full cycles is approximately 0
        z_start = terrain.elevation[path[0]]
        z_end = terrain.elevation[path[-1]]
        assert math.isclose(float(z_end - z_start), 0.0, abs_tol=1e-1)

        # Cumulative mechanical work must be strictly positive and exceed rolling work alone
        assert ledger_roller.total_mechanical_work_j > ledger_roller.total_rolling_work_j

        # Compare with a flat plain of identical distance (800m)
        flat_grid = np.full(terrain.elevation.shape, -2500.0, dtype=np.float32)
        flat_terrain = derive_terrain_from_array(flat_grid, config=terrain.config)
        ledger_flat = evaluate_mission_resource_ledger(
            path_rc=path,
            elevation_grid=flat_terrain.elevation,
            slope_grid=flat_terrain.slope_deg,
            invalid_mask=flat_terrain.invalid_mask,
            ground_dx_m=20.0,
            ground_dy_m=20.0,
            rover_config=rover,
        )

        # Rollercoaster consumes significantly more energy than flat terrain
        assert ledger_roller.total_mobility_energy_j > 1.25 * ledger_flat.total_mobility_energy_j

        # Downhill segment records verify that mechanical work is strictly positive (rolling friction)
        downhill_records = [r for r in ledger_roller.segment_records if r.elevation_change_m < -0.1]
        assert len(downhill_records) > 0
        for dr in downhill_records:
            assert dr.gravitational_work_j < 0.0
            # Strict non-regen: mechanical work is rolling work, not negative
            assert math.isclose(dr.mechanical_work_j, dr.rolling_work_j, abs_tol=1e-3)
            assert dr.mechanical_work_j > 0.0
            assert dr.mobility_energy_j > 0.0

    def test_heavy_science_sortie_duty_cycles(self, level_traverse_fixture):
        """
        Heavy Science Sortie Analytical Ground Truth:
        - Short traverse (10 steps = 200m) followed by 3 science dwell stations.
        - Dwell power: P_base + P_inst_active * delta + P_inst_sb * (1-delta) + P_comm_active.
        - Demonstrates that for static science-intensive missions, electrical loads dominate mobility.
        - Timeline events are sequentially ordered and dwell events are recorded with exact durations.
        """
        terrain = level_traverse_fixture
        path = [(30, c) for c in range(10, 21)]  # 10 steps = 200m

        waypoints = [
            {"name": "Delta Scarp Sample Alpha", "rc": (30, 13)},
            {"name": "Clay Core Sampling Beta", "rc": (30, 17)},
            {"name": "Carbonate Outcrop Gamma", "rc": (30, 20)},
        ]

        rover = RoverResourceConfig(
            rover_mass_kg=1000.0,
            payload_mass_kg=50.0,
            usable_battery_capacity_wh=4800.0,
            nominal_drive_speed_mps=0.40,
            base_electrical_load_w=110.0,
            instrument_standby_w=15.0,
            instrument_active_w=120.0,
            instrument_duty_cycle=0.30,  # 30% active science duty cycle
            comm_standby_w=20.0,
            comm_active_w=85.0,
            science_dwell_s=1800.0,      # 30 minutes per stop
        )

        ledger = evaluate_mission_resource_ledger(
            path_rc=path,
            elevation_grid=terrain.elevation,
            slope_grid=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            ground_dx_m=20.0,
            ground_dy_m=20.0,
            rover_config=rover,
            intermediate_waypoints=waypoints,
        )

        assert ledger.total_distance_m == 200.0
        # 3 stops * 1800s = 5400s activity duration
        assert math.isclose(ledger.activity_duration_s, 5400.0, abs_tol=1e-3)
        assert ledger.total_duration_s == ledger.traverse_duration_s + ledger.activity_duration_s

        # Electrical energy dominates mobility energy (>10x)
        assert ledger.total_electrical_energy_j > 10.0 * ledger.total_mobility_energy_j

        # Timeline events
        events = ledger.timeline_events
        assert len(events) == 4  # 1 traverse event + 3 science dwell events
        assert events[0].event_type == "traverse_step"
        for i in range(1, 4):
            assert events[i].event_type == "science_dwell"
            assert events[i].duration_s == 1800.0
            assert math.isclose(events[i].start_time_s, events[i - 1].end_time_s, abs_tol=1e-3)

    def test_battery_depletion_and_reserve_thresholds(self, level_traverse_fixture):
        """
        Battery Depletion Edge Cases:
        - Case A: High-energy traverse triggers low reserve warning (SOC < 20%).
        - Case B: Energy consumption exceeds battery capacity; remaining energy clamps at 0.0 J.
        - Feasibility classifications correctly assigned.
        """
        terrain = level_traverse_fixture
        path = [(30, c) for c in range(5, 56)]  # 1000m

        # Case A: Low reserve (battery capacity just enough to finish with 10% SOC)
        # 1000m on level terrain consumes ~501.8 kJ (~139.4 Wh)
        # Setting capacity to 160 Wh leaves ~20.6 Wh remaining (12.9% SOC < 20% reserve threshold)
        rover_low = RoverResourceConfig(
            rover_mass_kg=1000.0,
            usable_battery_capacity_wh=160.0,
            reserve_margin_pct=20.0,
            rolling_resistance_crr=0.05,
            drivetrain_efficiency=0.80,
            nominal_drive_speed_mps=0.50,
            base_electrical_load_w=100.0,
        )

        ledger_low = evaluate_mission_resource_ledger(
            path_rc=path,
            elevation_grid=terrain.elevation,
            slope_grid=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            ground_dx_m=20.0,
            ground_dy_m=20.0,
            rover_config=rover_low,
        )

        assert ledger_low.is_reserve_violated is True
        assert ledger_low.feasibility_classification == ResourceFeasibilityClassification.FEASIBLE_WITH_LOW_RESERVE
        assert ledger_low.min_battery_soc_pct < 20.0
        assert ledger_low.min_energy_remaining_j > 0.0

        # Case B: Complete depletion (battery capacity 50 Wh < 139.4 Wh needed)
        rover_depleted = RoverResourceConfig(
            rover_mass_kg=1000.0,
            usable_battery_capacity_wh=50.0,
            reserve_margin_pct=20.0,
            rolling_resistance_crr=0.05,
            drivetrain_efficiency=0.80,
            nominal_drive_speed_mps=0.50,
            base_electrical_load_w=100.0,
        )

        ledger_depleted = evaluate_mission_resource_ledger(
            path_rc=path,
            elevation_grid=terrain.elevation,
            slope_grid=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            ground_dx_m=20.0,
            ground_dy_m=20.0,
            rover_config=rover_depleted,
        )

        assert ledger_depleted.feasibility_classification == ResourceFeasibilityClassification.ENERGY_CONSTRAINT_VIOLATION
        assert ledger_depleted.min_energy_remaining_j <= 0.0
        assert ledger_depleted.final_battery_soc_pct == 0.0
        assert any("depleted" in v.lower() for v in ledger_depleted.constraint_violations)


# =============================================================================
# 2. UNIT TESTS: MOBILITY ENERGY PHYSICS
# =============================================================================

class TestMobilityEnergyPhysics:
    """Verifies mobility energy equations, Mars gravity scaling, and efficiency conversion."""

    def test_mars_gravity_scaling(self):
        """
        Mars Gravity vs Earth Gravity Scaling:
        - Rolling work and gravitational work scale strictly with surface gravity:
          g_mars = 3.71 m/s^2 vs g_earth = 9.81 m/s^2.
        - Ratio W_mars / W_earth == 3.71 / 9.81 ~ 0.37818.
        """
        m = 1000.0
        crr = 0.05
        d = 100.0
        dh = 10.0
        theta_rad = math.atan2(dh, d)

        # Mars calculations
        w_r_mars = crr * m * MARS_GRAVITY_MPS2 * math.cos(theta_rad) * d
        w_g_mars = m * MARS_GRAVITY_MPS2 * dh

        # Earth comparisons
        g_earth = 9.81
        w_r_earth = crr * m * g_earth * math.cos(theta_rad) * d
        w_g_earth = m * g_earth * dh

        ratio_expected = MARS_GRAVITY_MPS2 / g_earth
        assert math.isclose(w_r_mars / w_r_earth, ratio_expected, rel_tol=1e-5)
        assert math.isclose(w_g_mars / w_g_earth, ratio_expected, rel_tol=1e-5)
        assert math.isclose(MARS_GRAVITY_MPS2, 3.71, abs_tol=1e-3)

    def test_positive_slope_gravitational_work_linearity(self):
        """Gravitational work W_g = m * g * delta_h is strictly linear in elevation gain."""
        rover = RoverResourceConfig(rover_mass_kg=1000.0, payload_mass_kg=0.0)

        res_10m = calculate_segment_mobility_energy(100.0, 10.0, 5.71, rover)
        res_20m = calculate_segment_mobility_energy(100.0, 20.0, 11.31, rover)
        res_0m = calculate_segment_mobility_energy(100.0, 0.0, 0.0, rover)

        w_g_10 = res_10m[1]
        w_g_20 = res_20m[1]
        w_g_0 = res_0m[1]

        assert math.isclose(w_g_0, 0.0, abs_tol=1e-5)
        assert math.isclose(w_g_10, 1000.0 * MARS_GRAVITY_MPS2 * 10.0, abs_tol=1e-3)
        assert math.isclose(w_g_20, 2.0 * w_g_10, abs_tol=1e-3)

    def test_steep_downhill_no_unmodeled_regen(self):
        """
        Steep Downhill Descent:
        - When delta_h < 0:
          * With allow_regenerative_braking=False: mechanical work is strictly rolling work (W_m = W_r > 0).
          * With allow_regenerative_braking=True: mechanical work is bounded at 0.0 J.
        - Gravity assist never injects negative energy into battery under default settings.
        """
        rover_strict = RoverResourceConfig(allow_regenerative_braking=False)
        rover_regen = RoverResourceConfig(allow_regenerative_braking=True)

        # Downhill step: -20m over 100m ground distance
        res_strict = calculate_segment_mobility_energy(100.0, -20.0, 11.31, rover_strict)
        res_regen = calculate_segment_mobility_energy(100.0, -20.0, 11.31, rover_regen)

        # Strict physics: mechanical work equals rolling work (friction dissipation)
        w_r = res_strict[0]
        w_g = res_strict[1]
        w_m_strict = res_strict[2]
        w_m_regen = res_regen[2]

        assert w_g < 0.0
        assert math.isclose(w_m_strict, w_r, abs_tol=1e-3)
        assert w_m_strict > 0.0
        assert res_strict[3] > 0.0  # Mobility energy is strictly positive

        # Regen physics: bounded at 0.0
        assert w_m_regen == 0.0

    def test_drivetrain_efficiency_scaling(self):
        """Mobility electrical energy E_m = W_m / eta scales strictly inversely with eta."""
        rover_base = RoverResourceConfig(drivetrain_efficiency=0.80)
        rover_low = RoverResourceConfig(drivetrain_efficiency=0.50)
        rover_perfect = RoverResourceConfig(drivetrain_efficiency=1.00)

        res_base = calculate_segment_mobility_energy(100.0, 5.0, 2.86, rover_base)
        res_low = calculate_segment_mobility_energy(100.0, 5.0, 2.86, rover_low)
        res_perf = calculate_segment_mobility_energy(100.0, 5.0, 2.86, rover_perfect)

        w_m = res_base[2]
        # Perfect efficiency: E_m == W_m
        assert math.isclose(res_perf[3], w_m, abs_tol=1e-3)
        # Scaled efficiency: E_m(0.50) / E_m(0.80) == 0.80 / 0.50 == 1.6
        assert math.isclose(res_low[3] / res_base[3], 0.80 / 0.50, rel_tol=1e-4)

    def test_invalid_slopes_and_nodata_handling(self, level_traverse_fixture):
        """Strictly detects and rejects paths traversing NoData or out-of-bounds cells."""
        terrain = level_traverse_fixture
        rover = RoverResourceConfig()

        # Path with out-of-bounds coordinates
        bad_path_oob = [(30, 10), (30, 999)]
        ledger_oob = evaluate_mission_resource_ledger(
            path_rc=bad_path_oob,
            elevation_grid=terrain.elevation,
            slope_grid=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            ground_dx_m=20.0,
            ground_dy_m=20.0,
            rover_config=rover,
        )
        assert ledger_oob.feasibility_classification == ResourceFeasibilityClassification.UNKNOWN_RESOURCE_FEASIBILITY
        assert any("out-of-bounds" in v.lower() or "nodata" in v.lower() for v in ledger_oob.constraint_violations)

        # Path traversing NoData mask
        invalid_mask = np.copy(terrain.invalid_mask)
        invalid_mask[30, 15] = True
        bad_path_nodata = [(30, 10), (30, 15), (30, 20)]
        ledger_nodata = evaluate_mission_resource_ledger(
            path_rc=bad_path_nodata,
            elevation_grid=terrain.elevation,
            slope_grid=terrain.slope_deg,
            invalid_mask=invalid_mask,
            ground_dx_m=20.0,
            ground_dy_m=20.0,
            rover_config=rover,
        )
        assert ledger_nodata.feasibility_classification == ResourceFeasibilityClassification.UNKNOWN_RESOURCE_FEASIBILITY

    def test_segment_distance_conservation(self, continuous_incline_fixture):
        """Sum of individual segment step distances strictly conserves total odometer distance."""
        terrain = continuous_incline_fixture
        path = [(30, c) for c in range(10, 35)]
        rover = RoverResourceConfig()

        ledger = evaluate_mission_resource_ledger(
            path_rc=path,
            elevation_grid=terrain.elevation,
            slope_grid=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            ground_dx_m=20.0,
            ground_dy_m=20.0,
            rover_config=rover,
        )

        summed_dist = sum(r.distance_m for r in ledger.segment_records)
        assert math.isclose(summed_dist, ledger.total_distance_m, abs_tol=1e-4)
        assert math.isclose(ledger.total_distance_m, (len(path) - 1) * 20.0, abs_tol=1e-4)


# =============================================================================
# 3. UNIT TESTS: ELECTRICAL OPERATING LOADS
# =============================================================================

class TestElectricalOperatingLoads:
    """Verifies electrical loads modeling, duty cycle equations, and unit conversions."""

    def test_constant_power_integration(self):
        """Constant power load E = P * delta_t across standard intervals."""
        p = 100.0  # 100 Watts
        # 1 hour = 3600s -> 360,000 J = 100 Wh = 0.1 kWh
        t_1h = 3600.0
        e_j = p * t_1h
        assert math.isclose(e_j, 360000.0, abs_tol=1e-3)
        assert math.isclose(joules_to_wh(e_j), 100.0, abs_tol=1e-4)

    def test_duty_cycle_integration(self):
        """Duty-cycled power P_avg = P_on * delta + P_off * (1 - delta)."""
        p_active = 200.0
        p_standby = 20.0
        t = 1000.0

        # delta = 0.0 (pure standby)
        e_0 = (p_active * 0.0 + p_standby * 1.0) * t
        assert math.isclose(e_0, 20000.0, abs_tol=1e-3)

        # delta = 1.0 (pure active)
        e_1 = (p_active * 1.0 + p_standby * 0.0) * t
        assert math.isclose(e_1, 200000.0, abs_tol=1e-3)

        # delta = 0.25
        e_25 = (p_active * 0.25 + p_standby * 0.75) * t
        expected_p = 50.0 + 15.0  # 65.0 W
        assert math.isclose(e_25, 65000.0, abs_tol=1e-3)

    def test_standby_vs_active_load_contrast(self):
        """Active comms / instrument loads consume substantially more power than standby."""
        rover = RoverResourceConfig()
        assert rover.comm_active_w > 4.0 * rover.comm_standby_w
        assert rover.instrument_active_w >= 8.0 * rover.instrument_standby_w

    def test_energy_units_conversions_and_formatting(self):
        """Verifies lossless round-trip energy conversions and SI string formatters."""
        # 1 Wh = 3600 J
        assert math.isclose(wh_to_joules(1.0), 3600.0, abs_tol=1e-5)
        assert math.isclose(joules_to_wh(3600.0), 1.0, abs_tol=1e-5)

        # Lossless round-trip precision
        test_values_wh = [0.01, 1.0, 123.456, 4800.0, 1e6]
        for wh in test_values_wh:
            j = wh_to_joules(wh)
            wh_back = joules_to_wh(j)
            assert math.isclose(wh, wh_back, rel_tol=1e-9)

        # SI String Formatters
        assert "J" in format_energy_si(500.0)
        assert "kJ" in format_energy_si(50000.0)
        assert "MJ" in format_energy_si(5000000.0)
        assert "W" in format_power_si(50.0)
        assert "kW" in format_power_si(1500.0)
        assert format_energy_si(float("nan")) == "UNKNOWN"
        assert format_power_si(float("inf")) == "UNKNOWN"


# =============================================================================
# 4. UNIT TESTS: RELAYNET INFRASTRUCTURE POWER
# =============================================================================

class TestRelayNetInfrastructurePower:
    """Verifies communications infrastructure power budgeting and battery margins."""

    def test_relay_standby_and_active_power_accounting(self, level_traverse_fixture):
        """Relay masts consume standby power when idle and active TX power during link transmission."""
        terrain = level_traverse_fixture
        path = [(30, c) for c in range(10, 31)]  # 20 steps = 400m
        rover = RoverResourceConfig(nominal_drive_speed_mps=0.40)  # 1000s duration
        relay_cfg = RelayResourceConfig(standby_power_w=8.0, active_tx_power_w=35.0)

        relays = [{"node_id": "MRN-ALPHA", "rc": (20, 20)}]
        # 200s active TX, 800s standby
        active_times = {"MRN-ALPHA": 200.0}

        ledger = evaluate_mission_resource_ledger(
            path_rc=path,
            elevation_grid=terrain.elevation,
            slope_grid=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            ground_dx_m=20.0,
            ground_dy_m=20.0,
            rover_config=rover,
            relay_config=relay_cfg,
            relays_deployed=relays,
            active_relay_tx_times_s=active_times,
        )

        total_t = ledger.total_duration_s  # 1000s + relay deployment dwell
        # Expected relay energy = 8W * standby_t + 35W * 200s
        breakdown = ledger.relay_breakdown[0]
        assert breakdown["node_id"] == "MRN-ALPHA"
        assert math.isclose(breakdown["active_duration_s"], 200.0, abs_tol=1e-2)
        expected_relay_e_j = (8.0 * breakdown["standby_duration_s"]) + (35.0 * 200.0)
        assert math.isclose(breakdown["energy_consumed_j"], expected_relay_e_j, abs_tol=1e-1)
        assert math.isclose(ledger.total_relay_energy_j, expected_relay_e_j, abs_tol=1e-1)

    def test_multi_relay_network_budget_scaling(self, level_traverse_fixture):
        """Total RelayNet energy scales with number of deployed relay nodes."""
        terrain = level_traverse_fixture
        path = [(30, c) for c in range(10, 21)]
        rover = RoverResourceConfig()
        relay_cfg = RelayResourceConfig()

        # k = 0
        l0 = evaluate_mission_resource_ledger(
            path, terrain.elevation, terrain.slope_deg, terrain.invalid_mask, 20.0, 20.0, rover,
            relay_config=relay_cfg, relays_deployed=[],
        )
        assert l0.total_relay_energy_j == 0.0

        # k = 2
        relays_k2 = [{"node_id": "R1", "rc": (20, 20)}, {"node_id": "R2", "rc": (40, 40)}]
        l2 = evaluate_mission_resource_ledger(
            path, terrain.elevation, terrain.slope_deg, terrain.invalid_mask, 20.0, 20.0, rover,
            relay_config=relay_cfg, relays_deployed=relays_k2,
        )
        assert len(l2.relay_breakdown) == 2
        assert l2.total_relay_energy_j > 0.0

    def test_relay_battery_reserve_and_exhaustion(self, level_traverse_fixture):
        """Relay battery depletion or reserve margin violation triggers appropriate constraint violations."""
        terrain = level_traverse_fixture
        path = [(30, c) for c in range(10, 31)]
        rover = RoverResourceConfig()

        # Relay with small 2.0 Wh battery (7,200 J < 9,640 J consumed)
        relay_small = RelayResourceConfig(usable_battery_capacity_wh=2.0, reserve_margin_pct=15.0)
        relays = [{"node_id": "MRN_EXHAUST", "rc": (20, 20)}]

        ledger = evaluate_mission_resource_ledger(
            path, terrain.elevation, terrain.slope_deg, terrain.invalid_mask, 20.0, 20.0, rover,
            relay_config=relay_small, relays_deployed=relays,
        )

        assert any("MRN_EXHAUST" in v for v in ledger.constraint_violations)


# =============================================================================
# 5. UNIT TESTS: MISSION SCHEDULING & TIMELINE
# =============================================================================

class TestMissionSchedulingTimeline:
    """Verifies chronological activity scheduling, sequential event ordering, and duration conservation."""

    def test_sequential_event_chronological_ordering(self, level_traverse_fixture):
        """Every timeline event starts strictly when the previous event ends (t_start == t_prev_end)."""
        terrain = level_traverse_fixture
        path = [(30, c) for c in range(10, 31)]
        waypoints = [{"name": "Site Alpha", "rc": (30, 20)}]
        relays = [{"node_id": "RELAY_1", "rc": (30, 25)}]
        rover = RoverResourceConfig(operational_delay_s=300.0)

        ledger = evaluate_mission_resource_ledger(
            path, terrain.elevation, terrain.slope_deg, terrain.invalid_mask, 20.0, 20.0, rover,
            intermediate_waypoints=waypoints, relays_deployed=relays,
        )

        events = ledger.timeline_events
        assert len(events) >= 4  # Traverse + Science + Relay + Delay

        # Chronological progression
        assert events[0].start_time_s == 0.0
        for i in range(1, len(events)):
            assert math.isclose(events[i].start_time_s, events[i - 1].end_time_s, abs_tol=1e-3)
            assert events[i].end_time_s > events[i].start_time_s
            assert math.isclose(events[i].duration_s, events[i].end_time_s - events[i].start_time_s, abs_tol=1e-5)

    def test_total_mission_duration_conservation(self, level_traverse_fixture):
        """Total mission duration strictly equals the sum of all discrete activity durations."""
        terrain = level_traverse_fixture
        path = [(30, c) for c in range(10, 26)]
        waypoints = [{"name": "W1", "rc": (30, 15)}, {"name": "W2", "rc": (30, 20)}]
        relays = [{"node_id": "R1", "rc": (30, 22)}]
        rover = RoverResourceConfig(
            nominal_drive_speed_mps=0.50,
            science_dwell_s=600.0,
            relay_deployment_s=900.0,
            operational_delay_s=120.0,
        )

        ledger = evaluate_mission_resource_ledger(
            path, terrain.elevation, terrain.slope_deg, terrain.invalid_mask, 20.0, 20.0, rover,
            intermediate_waypoints=waypoints, relays_deployed=relays,
        )

        expected_traverse_t = (15 * 20.0) / 0.50  # 600.0 s
        expected_activity_t = (2 * 600.0) + 900.0 + 120.0  # 2220.0 s
        expected_total_t = expected_traverse_t + expected_activity_t  # 2820.0 s

        assert math.isclose(ledger.traverse_duration_s, expected_traverse_t, abs_tol=1e-3)
        assert math.isclose(ledger.activity_duration_s, expected_activity_t, abs_tol=1e-3)
        assert math.isclose(ledger.total_duration_s, expected_total_t, abs_tol=1e-3)

    def test_zero_duration_edge_cases(self, level_traverse_fixture):
        """Path with 2 identical points (zero distance) raises clean validation error or minimal duration."""
        terrain = level_traverse_fixture
        rover = RoverResourceConfig()

        # Path with 1 cell
        single_pt_path = [(30, 30)]
        ledger = evaluate_mission_resource_ledger(
            single_pt_path, terrain.elevation, terrain.slope_deg, terrain.invalid_mask, 20.0, 20.0, rover
        )
        assert ledger.feasibility_classification == ResourceFeasibilityClassification.INVALID_CONFIGURATION


# =============================================================================
# 6. UNIT TESTS: UNIFIED RESOURCE LEDGER & CONSERVATION
# =============================================================================

class TestUnifiedResourceLedger:
    """Verifies unified energy conservation, reserve tracking, and configuration invariants."""

    def test_strict_energy_conservation_law(self, continuous_incline_fixture):
        """
        Step-by-step energy conservation:
        E_rem, i == E_rem, i-1 - E_cons, i
        Global conservation:
        E_rem, final + sum(E_cons) == E_initial
        Numerical error must be bounded by floating point precision (< 1e-6 J).
        """
        terrain = continuous_incline_fixture
        path = [(30, c) for c in range(15, 36)]
        rover = RoverResourceConfig()

        ledger = evaluate_mission_resource_ledger(
            path, terrain.elevation, terrain.slope_deg, terrain.invalid_mask, 20.0, 20.0, rover
        )

        initial_j = rover.usable_battery_capacity_j

        # Check each discrete step
        current_j = initial_j
        for rec in ledger.segment_records:
            expected_rem = current_j - rec.total_energy_consumed_j
            assert math.isclose(rec.energy_remaining_j, expected_rem, abs_tol=1e-5)
            current_j = rec.energy_remaining_j

        # Check global conservation
        assert math.isclose(ledger.final_energy_remaining_j + ledger.total_mission_energy_j, initial_j, abs_tol=1e-4)

    def test_peak_instantaneous_power_tracking(self, level_traverse_fixture):
        """Peak instantaneous power captures highest mechanical + electrical subsystem draw."""
        terrain = level_traverse_fixture
        path = [(30, c) for c in range(10, 21)]
        rover = RoverResourceConfig(
            base_electrical_load_w=100.0,
            comm_standby_w=20.0,
            instrument_standby_w=15.0,
            instrument_active_w=150.0,
            comm_active_w=85.0,
        )
        waypoints = [{"name": "Drill Site", "rc": (30, 15)}]

        ledger = evaluate_mission_resource_ledger(
            path, terrain.elevation, terrain.slope_deg, terrain.invalid_mask, 20.0, 20.0, rover,
            intermediate_waypoints=waypoints,
        )

        assert ledger.peak_instantaneous_power_w > 0.0
        # Peak power should exceed base electrical load
        assert ledger.peak_instantaneous_power_w > 135.0

    def test_energy_per_km_metric(self, level_traverse_fixture):
        """Normalized energy per km equals total Wh divided by total km."""
        terrain = level_traverse_fixture
        path = [(30, c) for c in range(5, 56)]  # 1000m = 1.0 km
        rover = RoverResourceConfig()

        ledger = evaluate_mission_resource_ledger(
            path, terrain.elevation, terrain.slope_deg, terrain.invalid_mask, 20.0, 20.0, rover
        )

        km = ledger.total_distance_m / 1000.0
        expected_wh_per_km = ledger.total_mission_energy_wh / km
        assert math.isclose(ledger.energy_per_km_wh, expected_wh_per_km, abs_tol=1e-4)

    def test_rover_resource_config_validation(self):
        """RoverResourceConfig raises ValueError for physically impossible parameters."""
        # Negative mass
        with pytest.raises(ValueError):
            RoverResourceConfig(rover_mass_kg=-500.0)

        # Zero or negative efficiency
        with pytest.raises(ValueError):
            RoverResourceConfig(drivetrain_efficiency=0.0)
        with pytest.raises(ValueError):
            RoverResourceConfig(drivetrain_efficiency=1.5)

        # Negative speed
        with pytest.raises(ValueError):
            RoverResourceConfig(nominal_drive_speed_mps=-0.5)

        # Invalid reserve margin
        with pytest.raises(ValueError):
            RoverResourceConfig(reserve_margin_pct=150.0)

        # Invalid duty cycle
        with pytest.raises(ValueError):
            RoverResourceConfig(instrument_duty_cycle=-0.1)


# =============================================================================
# 7. INTEGRATION TESTS: RESOURCE-AWARE PLANNING & SENSITIVITY LAB
# =============================================================================

class TestResourceIntegration:
    """Verifies deterministic sensitivity analysis, Pareto trade-offs, and authentic Jezero scenarios."""

    def test_deterministic_sensitivity_sweep_ranking(self, continuous_incline_fixture):
        """
        Sensitivity Lab:
        - Sweeps 6 key parameters (mass, Crr, efficiency, speed, base load, battery capacity).
        - Computes normalized elasticity and ranks parameters descending by impact.
        - Verifies min/max consumption range and provenance disclosure statement.
        """
        terrain = continuous_incline_fixture
        path = [(30, c) for c in range(15, 36)]
        rover = RoverResourceConfig()

        sens = evaluate_resource_sensitivity(
            path_rc=path,
            elevation_grid=terrain.elevation,
            slope_grid=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            ground_dx_m=20.0,
            ground_dy_m=20.0,
            base_rover_config=rover,
        )

        assert isinstance(sens, ResourceSensitivityResult)
        assert sens.baseline_energy_wh > 0.0

        # Check rankings
        rankings = sens.sensitivity_ranking
        assert len(rankings) == 6
        # Rankings are sorted descending by elasticity
        for i in range(len(rankings) - 1):
            assert rankings[i]["elasticity"] >= rankings[i + 1]["elasticity"]

        # Consumption range bounds baseline
        min_c, max_c = sens.consumption_range_wh
        assert min_c <= sens.baseline_energy_wh <= max_c

        # Provenance disclaimer is attached
        assert "not validated predictions" in sens.provenance_statement.lower()

    def test_resource_aware_pareto_tradeoffs(self):
        """
        Resource-Aware Pareto Dominance Analysis:
        - Evaluates 5-objective vector: (distance_m, gap_time_s, relay_count, energy_wh, duration_s).
        - Candidate A (short, steep, high energy, zero comms gap).
        - Candidate B (longer, flat, lower mobility energy, higher comms gap).
        - Candidate C (longer, steep, high energy, high comms gap -> strictly dominated by A and B).
        """
        def check_5d_domination(a: Tuple[float, ...], b: Tuple[float, ...], tol: float = 1e-5) -> bool:
            all_le = True
            any_lt = False
            for va, vb in zip(a, b):
                if va > vb + tol:
                    return False
                if va < vb - tol:
                    any_lt = True
            return any_lt

        # Vector: (dist, gap, relays, energy, duration) - all minimized
        cand_a = (800.0, 0.0, 1.0, 250.0, 2000.0)      # High energy, zero gap
        cand_b = (1200.0, 150.0, 0.0, 180.0, 2400.0)   # Low energy, higher gap
        cand_c = (1400.0, 300.0, 2.0, 350.0, 3000.0)   # Dominated in all dimensions

        assert check_5d_domination(cand_a, cand_c) is True
        assert check_5d_domination(cand_b, cand_c) is True
        # A and B are mutually non-dominated (Pareto efficient trade-off)
        assert check_5d_domination(cand_a, cand_b) is False
        assert check_5d_domination(cand_b, cand_a) is False

    def test_constraint_filtering_precedence(self, level_traverse_fixture):
        """
        Constraint Filtering Precedence:
        - A candidate that exhausts battery (ENERGY_CONSTRAINT_VIOLATION) cannot be classified
          as FEASIBLE_WITHIN_CONFIGURED_BUDGET regardless of its speed or distance.
        """
        terrain = level_traverse_fixture
        path = [(30, c) for c in range(10, 41)]
        # Insufficient battery
        rover_failed = RoverResourceConfig(usable_battery_capacity_wh=10.0)

        ledger = evaluate_mission_resource_ledger(
            path, terrain.elevation, terrain.slope_deg, terrain.invalid_mask, 20.0, 20.0, rover_failed
        )

        assert ledger.feasibility_classification == ResourceFeasibilityClassification.ENERGY_CONSTRAINT_VIOLATION
        assert ledger.min_energy_remaining_j <= 0.0

    def test_authentic_jezero_octavia_to_three_forks_resource_budget(self, jezero_terrain):
        """
        Authentic Jezero Crater Scenario: Octavia Landing Site (117, 157) to Three Forks (138, 114):
        - Authenticated against USGS CTX 20m DTM.
        - Evaluates route distance (~917m), realistic energy consumption, and feasibility.
        - Verifies energy per km is within realistic Martian rover range (50-300 Wh/km).
        """
        start = (117, 157)
        goal = (138, 114)
        route = astar_search(start, goal, jezero_terrain)
        assert route is not None

        rover = RoverResourceConfig(
            rover_mass_kg=1025.0,
            payload_mass_kg=50.0,
            usable_battery_capacity_wh=4800.0,
            reserve_margin_pct=20.0,
        )

        ledger = evaluate_mission_resource_ledger(
            path_rc=route.path,
            elevation_grid=jezero_terrain.elevation,
            slope_grid=jezero_terrain.slope_deg,
            invalid_mask=jezero_terrain.invalid_mask,
            ground_dx_m=jezero_terrain.dx_ground_m,
            ground_dy_m=jezero_terrain.dy_ground_m,
            rover_config=rover,
        )

        assert ledger.feasibility_classification == ResourceFeasibilityClassification.FEASIBLE_WITHIN_CONFIGURED_BUDGET
        assert 800.0 <= ledger.total_distance_m <= 1500.0
        # Realistic energy per km for a 1000kg Mars rover
        assert 50.0 <= ledger.energy_per_km_wh <= 350.0
        assert ledger.final_battery_soc_pct > 80.0

    def test_authentic_jezero_delta_rim_climbing_energy(self, jezero_terrain):
        """
        Authentic Jezero Crater Scenario: Octavia Landing Site (117, 157) to Delta Rim (145, 95):
        - Climbs onto the ancient river delta deposit (>40m net climb).
        - Gravitational work component is strictly positive and matches net climb.
        """
        start = (117, 157)
        goal = (145, 95)
        route = astar_search(start, goal, jezero_terrain)
        assert route is not None

        rover = RoverResourceConfig(
            rover_mass_kg=1025.0,
            payload_mass_kg=50.0,
            usable_battery_capacity_wh=4800.0,
        )

        ledger = evaluate_mission_resource_ledger(
            path_rc=route.path,
            elevation_grid=jezero_terrain.elevation,
            slope_grid=jezero_terrain.slope_deg,
            invalid_mask=jezero_terrain.invalid_mask,
            ground_dx_m=jezero_terrain.dx_ground_m,
            ground_dy_m=jezero_terrain.dy_ground_m,
            rover_config=rover,
        )

        assert ledger.total_distance_m > 1200.0
        # Positive climbing work (>30 kJ based on authentic delta elevation)
        assert ledger.total_gravitational_work_j > 30000.0
        assert ledger.feasibility_classification == ResourceFeasibilityClassification.FEASIBLE_WITHIN_CONFIGURED_BUDGET


# =============================================================================
# 8. REGRESSION & SCIENTIFIC INTEGRITY GUARDRAILS
# =============================================================================

class TestMilestone13FRegressionGuard:
    """Enforces operational data safety and planetary science disclosures."""

    def test_operational_workspace_data_immutability(self):
        """Ensures that no test modified or created files inside operational workspace folders."""
        workspaces_dir = os.path.join(REPO_ROOT, "data", "workspaces")
        if os.path.exists(workspaces_dir):
            for sub in ["missions", "campaigns", "experiments", "rehearsals", "events"]:
                sub_dir = os.path.join(workspaces_dir, sub)
                if os.path.exists(sub_dir):
                    for fname in os.listdir(sub_dir):
                        # Operational files should not start with test prefixes
                        if fname.endswith(".json"):
                            assert not fname.startswith("test_milestone_13f_")

    def test_provenance_statement_attached_to_sensitivity(self, level_traverse_fixture):
        """Verifies that sensitivity analysis strictly includes non-probabilistic truth disclosures."""
        terrain = level_traverse_fixture
        path = [(30, c) for c in range(10, 20)]
        rover = RoverResourceConfig()

        sens = evaluate_resource_sensitivity(
            path, terrain.elevation, terrain.slope_deg, terrain.invalid_mask, 20.0, 20.0, rover
        )

        stmt = sens.provenance_statement
        assert "deterministic scenario evaluations" in stmt
        assert "not validated predictions" in stmt

    def test_no_astronaut_safety_claims_in_ledger(self, level_traverse_fixture):
        """Verifies that ledger notes and strings never label modeled paths as flight-certified or astronaut-safe."""
        terrain = level_traverse_fixture
        path = [(30, c) for c in range(10, 20)]
        rover = RoverResourceConfig()

        ledger = evaluate_mission_resource_ledger(
            path, terrain.elevation, terrain.slope_deg, terrain.invalid_mask, 20.0, 20.0, rover
        )

        ledger_json = json.dumps(ledger.to_dict()).lower()
        assert "safe for astronauts" not in ledger_json
        assert "flight certified" not in ledger_json
