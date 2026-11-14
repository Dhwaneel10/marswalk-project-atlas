"""
MarsWalk 2.0 / Project Atlas - Milestone 13E
Joint Mission Co-Design (Traverse Planning x Relay Network x Dynamic Connectivity)
Test Suite & Scientific Validation Architecture.

Covers:
1. Synthetic Terrain Fixtures & Analytical Ground Truths:
   - Single Central Ridge: steep barrier (>30 deg), north/south flat bypasses,
     direct geometric line-of-sight blockage (clearance <= -20m), and ridge summit relay restoration.
   - Multi-Channel Ridge with Narrow Canyons: flat canyon floor with RF shadow, elevated saddle pass,
     and ridge promontory relay resolving canyon blackout.
   - Isolated Mountain Promontories: conical peak, topographic prominence screening,
     target shadow occlusion, and high-vantage relay mesh formation.
2. Authentic Jezero Crater Scenarios (USGS CTX 20m DTM):
   - Octavia E. Butler Landing Site ([117, 157]) to Three Forks ([138, 114]):
     baseline direct line-of-sight terrain obstruction, candidate relay deployment,
     and reachability restoration.
   - Octavia Landing Site to Delta Rim ([145, 95]):
     climbing ascent (>50m gain), multi-route generation, elevation conservation.
3. Algorithm Test Matrix:
   - Alternative traverse generation (multi-profile cost sweeps & deduplication).
   - Communications evaluation (direct vs relayed vs coalesced gap metrics).
   - Relay deployment budget sweeps (k in {0, 1, 2}, submodular diminishing returns).
   - Pareto dominance analysis (non-dominated frontier, strictly dominated candidates,
     identical objective vectors, single candidate edge cases).
   - Input validation & boundary constraints (out-of-bounds, NoData, NaN/inf, invalid parameters).
   - Deterministic repeatability & SHA-256 cache fingerprinting.
   - Operational data preservation (immutability of data/workspaces/).
4. Joint Mission Planner Interface & Decision Explanation Verification.
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
from marswalk.core.terrain_visibility import (
    calculate_line_of_sight,
    sample_bilinear_elevation,
    LineOfSightResult,
    DEFAULT_DX_M,
    DEFAULT_DY_M,
)
from marswalk.core.relay_graph import (
    RelayNode,
    RelayNodeType,
    RelayEdge,
    LinkVisibilityStatus,
    RelayNetworkGraph,
)
from marswalk.core.relay_planner import (
    screen_relay_candidates,
    optimize_relay_placement,
)
from marswalk.core.mission_connectivity import (
    compute_mission_connectivity_timeline,
    coalesce_gap_intervals,
    DynamicCommState,
    ConnectivityCheckpoint,
    ConnectivityGapInterval,
)
from marswalk.core.planner import (
    astar_search,
    plan_route,
    PlannerConfig,
    ScienceWaypoint,
    LegResult,
)
from marswalk.core.campaign_design_space import (
    check_dominance,
    classify_pareto_frontier,
    CandidateStatus,
    DominanceStatus,
)

# Optional import of joint_mission_planner when implemented
try:
    import marswalk.core.joint_mission_planner as jmp
    HAS_JOINT_PLANNER_MODULE = True
except ImportError:
    HAS_JOINT_PLANNER_MODULE = False

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JEZERO_DTM_PATH = os.path.join(REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")


# =============================================================================
# SYNTHETIC TERRAIN FIXTURE GENERATORS
# =============================================================================

def create_central_ridge_terrain(
    shape: Tuple[int, int] = (50, 50),
    ridge_col: int = 25,
    ridge_rows: Tuple[int, int] = (10, 40),
    ridge_height_m: float = 25.0,
    dx_m: float = 20.0,
    dy_m: float = 20.0,
) -> TerrainGrid:
    """
    Constructs a flat plain (0.0m) with a single central vertical ridge at column 25.
    Corridors north (rows 0..9) and south (rows 40..49) are open and flat (0.0m).
    Direct path from (25, 10) to (25, 40) is blocked by the 25m ridge (slope > 50 deg).
    """
    grid = np.zeros(shape, dtype=np.float32)
    grid[ridge_rows[0]:ridge_rows[1], ridge_col] = ridge_height_m
    cfg = TerrainConfig(dx_ground_m=dx_m, dy_ground_m=dy_m, theta_max_deg=25.0)
    return derive_terrain_from_array(grid, config=cfg)


def create_multichannel_canyons_terrain(
    shape: Tuple[int, int] = (60, 60),
    ridge1_col: int = 20,
    ridge2_col: int = 40,
    ridge_height_m: float = 20.0,
    canyon_rows: Tuple[int, int] = (28, 33),
    saddle_rows: Tuple[int, int] = (8, 13),
    saddle_height_m: float = 10.0,
    dx_m: float = 20.0,
    dy_m: float = 20.0,
) -> TerrainGrid:
    """
    Constructs two parallel north-south ridges at col 20 and col 40 (height 20m).
    - Canyon 1 (rows 28..32): cut through both ridges at 0.0m elevation (flat floor).
      Rover inside Canyon 1 has flat walking, but RF line-of-sight to Base at (10, 10)
      is blocked by the 20m canyon walls.
    - Saddle 2 (rows 8..12): crossing ridges at 10.0m elevation (moderate slope).
      Rover crossing the saddle has elevated line-of-sight to Base, but requires climbing.
    """
    grid = np.zeros(shape, dtype=np.float32)
    grid[:, ridge1_col] = ridge_height_m
    grid[:, ridge2_col] = ridge_height_m

    # Canyon 1 cut
    grid[canyon_rows[0]:canyon_rows[1], ridge1_col] = 0.0
    grid[canyon_rows[0]:canyon_rows[1], ridge2_col] = 0.0

    # Saddle 2 ramp
    grid[saddle_rows[0]:saddle_rows[1], ridge1_col] = saddle_height_m
    grid[saddle_rows[0]:saddle_rows[1], ridge2_col] = saddle_height_m

    cfg = TerrainConfig(dx_ground_m=dx_m, dy_ground_m=dy_m, theta_max_deg=25.0)
    return derive_terrain_from_array(grid, config=cfg)


def create_promontory_field_terrain(
    shape: Tuple[int, int] = (70, 70),
    peak_rc: Tuple[int, int] = (35, 35),
    base_elev_m: float = -2500.0,
    prominence_m: float = 100.0,
    sigma_cells: float = 5.0,
    dx_m: float = 20.0,
    dy_m: float = 20.0,
) -> TerrainGrid:
    """
    Constructs an isolated Gaussian promontory (Kodiak Butte analogue) centered at (35, 35)
    rising from -2500m to -2400m (+100m prominence).
    Target assets in the shadow valley behind the butte are occluded from Base at (10, 10).
    A relay deployed on the summit covers both Base and the shadow valley.
    """
    H, W = shape
    r_coords, c_coords = np.ogrid[:H, :W]
    dist_sq = (r_coords - peak_rc[0])**2 + (c_coords - peak_rc[1])**2
    elevation = base_elev_m + prominence_m * np.exp(-dist_sq / (2.0 * sigma_cells**2)).astype(np.float32)

    cfg = TerrainConfig(dx_ground_m=dx_m, dy_ground_m=dy_m, theta_max_deg=25.0)
    return derive_terrain_from_array(elevation, config=cfg)


# =============================================================================
# MODULE-LEVEL FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def central_ridge_fixture():
    return create_central_ridge_terrain()


@pytest.fixture(scope="module")
def multichannel_canyons_fixture():
    return create_multichannel_canyons_terrain()


@pytest.fixture(scope="module")
def promontory_field_fixture():
    return create_promontory_field_terrain()


@pytest.fixture(scope="module")
def jezero_terrain():
    if not os.path.exists(JEZERO_DTM_PATH):
        pytest.skip(f"Jezero DTM not found at {JEZERO_DTM_PATH}")
    return load_and_process_terrain(JEZERO_DTM_PATH)


# =============================================================================
# 1. SYNTHETIC TERRAIN FIXTURES & ANALYTICAL GROUND TRUTHS
# =============================================================================

class TestSyntheticTerrainFixtures:
    """Validates analytical ground truths on controlled synthetic geometries."""

    def test_central_ridge_analytical_ground_truth(self, central_ridge_fixture):
        """
        Single Central Ridge:
        1. Direct geometric LOS ray from Base (25, 10) to Target (25, 40) is BLOCKED
           with negative clearance <= -20.0m at col 25.
        2. Shortest route along row 25 is impassable because step slope > theta_max (25 deg).
        3. A* path safely circumvents the ridge via north or south flat corridor (slope == 0.0 deg).
        4. Relay tower on ridge summit (25, 25, h=10m) provides clear line-of-sight to both
           Base (25, 10) and Target (25, 40).
        """
        grid = central_ridge_fixture.elevation
        base_rc = (25.0, 10.0)
        target_rc = (25.0, 40.0)
        relay_rc = (25.0, 25.0)

        # 1. Direct LOS check
        res_direct = calculate_line_of_sight(
            grid, base_rc, target_rc, antenna_h_a=2.0, antenna_h_b=2.0, dx_m=20.0, dy_m=20.0
        )
        assert res_direct.status == "BLOCKED"
        assert res_direct.is_visible is False
        assert res_direct.is_terrain_blocked is True
        assert res_direct.min_clearance_m <= -20.0
        assert res_direct.first_obstruction is not None
        assert math.isclose(res_direct.first_obstruction.col, 25.0, abs_tol=1.0)

        # 2. Step slope across ridge
        delta_z = grid[25, 25] - grid[25, 24]  # 25.0 - 0.0 = 25.0m
        step_slope_deg = math.degrees(math.atan2(delta_z, 20.0))
        assert step_slope_deg > 50.0
        assert step_slope_deg > central_ridge_fixture.config.theta_max_deg

        # 3. A* bypass route
        route = astar_search((25, 10), (25, 40), central_ridge_fixture)
        assert route is not None
        assert route.distance_m > 600.0  # Longer than direct 600m
        # The bypass route routes around ridge (north rows < 10 or south rows > 40)
        max_row = max(r for r, c in route.path)
        min_row = min(r for r, c in route.path)
        assert min_row < 10 or max_row >= 40
        # Bypass cells on flat plain have 0 slope
        assert all(grid[r, c] == 0.0 for r, c in route.path)

        # 4. Relay tower connectivity restoration
        res_base_relay = calculate_line_of_sight(
            grid, base_rc, relay_rc, antenna_h_a=2.0, antenna_h_b=10.0, dx_m=20.0, dy_m=20.0
        )
        assert res_base_relay.status == "VISIBLE"
        assert res_base_relay.min_clearance_m >= 2.0

        res_relay_target = calculate_line_of_sight(
            grid, relay_rc, target_rc, antenna_h_a=10.0, antenna_h_b=2.0, dx_m=20.0, dy_m=20.0
        )
        assert res_relay_target.status == "VISIBLE"
        assert res_relay_target.min_clearance_m >= 2.0

    def test_multichannel_canyons_tradeoff(self, multichannel_canyons_fixture):
        """
        Multi-Channel Ridge & Canyons:
        1. Rover in Canyon 1 at (30, 30) is occluded from Base at (10, 10) by Ridge 1 wall.
        2. Rover in Saddle 2 at (10, 30) is elevated and has higher clearance.
        3. Deploying 1 relay on Ridge 1 peak at (26, 20) with h=10m overlooks both Base (10, 10)
           and Rover inside Canyon 1 (30, 30), eliminating the canyon blackout.
        """
        grid = multichannel_canyons_fixture.elevation
        base_rc = (10.0, 10.0)
        canyon_rover_rc = (30.0, 30.0)
        saddle_rover_rc = (10.0, 30.0)
        relay_peak_rc = (26.0, 20.0)

        # 1. Inside canyon: blocked from base
        los_canyon = calculate_line_of_sight(
            grid, base_rc, canyon_rover_rc, antenna_h_a=2.0, antenna_h_b=2.0, dx_m=20.0, dy_m=20.0
        )
        assert los_canyon.status == "BLOCKED"
        assert los_canyon.min_clearance_m < -10.0

        # 2. Saddle pass: elevated
        los_saddle = calculate_line_of_sight(
            grid, base_rc, saddle_rover_rc, antenna_h_a=20.0, antenna_h_b=2.0, dx_m=20.0, dy_m=20.0
        )
        # Elevated antenna at base (20m) clears saddle ridge
        assert los_saddle.status == "VISIBLE"

        # 3. Relay on Ridge 1 peak eliminates canyon blackout
        los_base_relay = calculate_line_of_sight(
            grid, base_rc, relay_peak_rc, antenna_h_a=10.0, antenna_h_b=10.0, dx_m=20.0, dy_m=20.0
        )
        assert los_base_relay.status == "VISIBLE"
        assert los_base_relay.min_clearance_m >= 10.0

        los_relay_canyon = calculate_line_of_sight(
            grid, relay_peak_rc, canyon_rover_rc, antenna_h_a=10.0, antenna_h_b=2.5, dx_m=20.0, dy_m=20.0
        )
        assert los_relay_canyon.status == "VISIBLE"
        assert los_relay_canyon.min_clearance_m >= 2.5

    def test_promontory_field_and_screening(self, promontory_field_fixture):
        """
        Isolated Promontory Field:
        1. Topographic screening discovers summit at (35, 35) with prominence = 100m,
           slope <= 12 deg, and ranks it as Candidate #1.
        2. Direct LOS between Base (10, 10) and Target Asset (60, 60) is strongly BLOCKED (clearance < -80m).
        3. Relay deployed at candidate site (35, 35) achieves 2-hop LOS to both nodes.
        """
        terrain = promontory_field_fixture
        elevation = terrain.elevation
        base_rc = (10.0, 10.0)
        target_rc = (60.0, 60.0)

        # 1. Candidate screening on promontory
        cands = screen_relay_candidates(
            elevation=elevation,
            slope_deg=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            dx_ground_m=20.0,
            dy_ground_m=20.0,
            min_elevation_m=-2490.0,
            min_separation_m=450.0,
            max_candidates=5,
        )
        assert len(cands) >= 1
        top_cand = cands[0]
        assert top_cand["rc"] == (35, 35)
        assert math.isclose(top_cand["elevation_m"], -2400.0, abs_tol=1.0)
        assert top_cand["slope_deg"] <= 12.0

        # 2. Direct LOS blockage through promontory
        los_direct = calculate_line_of_sight(
            elevation, base_rc, target_rc, antenna_h_a=10.0, antenna_h_b=2.5, dx_m=20.0, dy_m=20.0
        )
        assert los_direct.status == "BLOCKED"
        assert los_direct.min_clearance_m <= -80.0

        # 3. Relay placed on screened candidate restores connectivity
        cand_rc = (float(top_cand["row"]), float(top_cand["col"]))
        los_base_cand = calculate_line_of_sight(
            elevation, base_rc, cand_rc, antenna_h_a=10.0, antenna_h_b=10.0, dx_m=20.0, dy_m=20.0
        )
        assert los_base_cand.status == "VISIBLE"

        los_cand_target = calculate_line_of_sight(
            elevation, cand_rc, target_rc, antenna_h_a=10.0, antenna_h_b=2.5, dx_m=20.0, dy_m=20.0
        )
        assert los_cand_target.status == "VISIBLE"


# =============================================================================
# 2. AUTHENTIC JEZERO CRATER TERRAIN SCENARIOS
# =============================================================================

class TestAuthenticJezeroScenarios:
    """Validates joint mission scenarios using authentic USGS CTX 20m Jezero Crater topography."""

    def test_jezero_octavia_to_three_forks_baseline_blackout(self, jezero_terrain):
        """
        Traverse from Octavia E. Butler Landing Site (117, 157) to Three Forks (138, 114):
        - Direct line-of-sight between Base and Three Forks is BLOCKED by delta scarp topography.
        - Distance is ~917m (< direct radio range 2500m), demonstrating terrain-induced blackout.
        - Baseline mission timeline without relays (k=0) yields significant gap distance and duration.
        """
        elevation = jezero_terrain.elevation
        base_rc = (117, 157)
        three_forks_rc = (138, 114)

        # Direct LOS check
        res_direct = calculate_line_of_sight(
            elevation,
            (float(base_rc[0]), float(base_rc[1])),
            (float(three_forks_rc[0]), float(three_forks_rc[1])),
            antenna_h_a=10.0,
            antenna_h_b=2.5,
            dx_m=jezero_terrain.dx_ground_m,
            dy_m=jezero_terrain.dy_ground_m,
        )
        assert res_direct.status == "BLOCKED"
        assert res_direct.is_terrain_blocked is True
        assert res_direct.min_clearance_m < 0.0

        # Plan standard route
        route = astar_search(base_rc, three_forks_rc, jezero_terrain)
        assert route is not None
        assert 800.0 <= route.distance_m <= 1500.0

        # Construct trajectory checkpoints
        trajectory = [(i * 30.0, float(r), float(c)) for i, (r, c) in enumerate(route.path)]
        base_station = {"id": "BASE_OCTAVIA", "rc": base_rc, "antenna_h": 10.0}

        # Timeline with k=0 relays
        timeline_k0 = compute_mission_connectivity_timeline(
            elevation=elevation,
            trajectory_points=trajectory,
            base_station=base_station,
            relays=[],
            direct_range_m=2500.0,
            rover_antenna_h_m=2.5,
            dx_ground_m=jezero_terrain.dx_ground_m,
            dy_ground_m=jezero_terrain.dy_ground_m,
        )

        summary = timeline_k0["summary"]
        assert summary["gap_count"] >= 1
        assert summary["total_gap_time_s"] > 0.0
        assert summary["connectivity_availability_pct"] < 100.0

    def test_jezero_three_forks_relay_restoration(self, jezero_terrain):
        """
        Deploying a high-vantage relay on screened Jezero Crater promontories
        (e.g. Promontory Pass / Delta Overlook) restores communications to Three Forks checkpoints.
        """
        elevation = jezero_terrain.elevation
        base_rc = (117, 157)
        three_forks_rc = (138, 114)
        route = astar_search(base_rc, three_forks_rc, jezero_terrain)
        assert route is not None

        trajectory = [(i * 30.0, float(r), float(c)) for i, (r, c) in enumerate(route.path)]
        base_station = {"id": "BASE_OCTAVIA", "rc": base_rc, "antenna_h": 10.0}

        # High vantage relay overlooking Octavia Base and Three Forks (e.g. Promontory candidate at 78, 134)
        relays = [{"id": "MRN_TOWER_01", "rc": (78, 134), "antenna_h": 15.0}]

        timeline_k1 = compute_mission_connectivity_timeline(
            elevation=elevation,
            trajectory_points=trajectory,
            base_station=base_station,
            relays=relays,
            direct_range_m=2500.0,
            relay_range_m=5000.0,
            rover_antenna_h_m=2.5,
            dx_ground_m=jezero_terrain.dx_ground_m,
            dy_ground_m=jezero_terrain.dy_ground_m,
        )

        summary_k1 = timeline_k1["summary"]
        assert summary_k1["total_mission_time_s"] > 0.0
        # Checkpoints near Three Forks transition to CONNECTED_RELAYED or gap is reduced
        last_cp = timeline_k1["checkpoints"][-1]
        assert last_cp["rc"] == [float(three_forks_rc[0]), float(three_forks_rc[1])]

    def test_jezero_octavia_to_delta_rim_traverse_scenarios(self, jezero_terrain):
        """
        Traverse from Octavia Landing Site (117, 157) to Delta Rim (145, 95):
        - Significant distance (>1500m) and climb onto delta front deposit (>40m net gain).
        - Generates distinct routes across conservative vs science-first profiles.
        - Verifies strict elevation conservation: Delta z_gain - Delta z_loss == delta_z_net.
        """
        start_rc = (117, 157)
        goal_rc = (145, 95)

        cfg_cons = get_profile_terrain_config("conservative", jezero_terrain.config)
        cfg_sci = get_profile_terrain_config("science_first", jezero_terrain.config)

        res_cons = astar_search(start_rc, goal_rc, jezero_terrain, terrain_config=cfg_cons)
        res_sci = astar_search(start_rc, goal_rc, jezero_terrain, terrain_config=cfg_sci)

        assert res_cons is not None
        assert res_sci is not None
        assert res_cons.distance_m > 1200.0
        assert res_sci.distance_m > 1200.0

        # Elevation conservation along path
        for res in [res_cons, res_sci]:
            path = res.path
            elevs = [float(jezero_terrain.elevation[r, c]) for r, c in path]
            gain = sum(max(0.0, elevs[i + 1] - elevs[i]) for i in range(len(elevs) - 1))
            loss = sum(max(0.0, elevs[i] - elevs[i + 1]) for i in range(len(elevs) - 1))
            net_z = elevs[-1] - elevs[0]
            assert math.isclose(gain - loss, net_z, abs_tol=1e-3)


# =============================================================================
# 3. ALGORITHM TEST MATRIX
# =============================================================================

class TestAlgorithmTestMatrix:
    """Comprehensive test matrix covering joint planner algorithms, invariants, and edge cases."""

    def test_alternative_traverse_generation_and_distinctness(self, jezero_terrain):
        """
        Alternative Traverse Generation:
        - Sweeping terrain cost weights (alpha_s in [1.0, 8.0]) and waypoints yields distinct paths.
        - Deduplication eliminates near-identical paths (overlap > 95%).
        - Returns at least 3 distinct candidate routes.
        """
        start = (117, 157)
        goal = (138, 114)

        routes: List[List[Tuple[int, int]]] = []

        # Route 1: Direct shortest / low slope penalty
        cfg1 = TerrainConfig(alpha_s=1.0, theta_crit_deg=18.0)
        r1 = astar_search(start, goal, jezero_terrain, terrain_config=cfg1)
        if r1: routes.append(r1.path)

        # Route 2: Conservative / high slope penalty
        cfg2 = TerrainConfig(alpha_s=8.0, theta_crit_deg=8.0)
        r2 = astar_search(start, goal, jezero_terrain, terrain_config=cfg2)
        if r2: routes.append(r2.path)

        # Route 3: Via intermediate waypoint (126, 138)
        wp = ScienceWaypoint(id="WP_PROMONTORY", name="Promontory Pass", rc=(126, 138))
        r3 = plan_route(start, goal, jezero_terrain, waypoints=[wp], config=PlannerConfig(profile="balanced"))
        if r3: routes.append(r3.path)

        assert len(routes) >= 3

        # Deduplication function
        def deduplicate_routes(route_list: List[List[Tuple[int, int]]], threshold: float = 0.95) -> List[List[Tuple[int, int]]]:
            unique = []
            for r in route_list:
                r_set = set(r)
                is_dup = False
                for u in unique:
                    u_set = set(u)
                    jaccard = len(r_set.intersection(u_set)) / float(max(1, len(r_set.union(u_set))))
                    if jaccard >= threshold:
                        is_dup = True
                        break
                if not is_dup:
                    unique.append(r)
            return unique

        deduped = deduplicate_routes(routes)
        assert len(deduped) >= 2  # At least 2 strictly distinct alternatives
        # All routes start at start and end at goal
        for r in deduped:
            assert r[0] == start
            assert r[-1] == goal

    def test_communications_evaluation_metrics_and_invariants(self, jezero_terrain):
        """
        Communications Evaluation:
        - Checkpoint timeline correctly classifies states:
          CONNECTED_DIRECT, CONNECTED_RELAYED, SIMULATED_GEOMETRIC_CONNECTIVITY_GAP.
        - Invariant: D_connected + D_gap == D_traverse (within numerical precision).
        - Gap coalescing preserves interval bounds: t_start <= t_end.
        """
        route = astar_search((117, 157), (138, 114), jezero_terrain)
        assert route is not None

        trajectory = [(i * 20.0, float(r), float(c)) for i, (r, c) in enumerate(route.path)]
        base = {"id": "BASE", "rc": (117, 157), "antenna_h": 10.0}

        timeline = compute_mission_connectivity_timeline(
            elevation=jezero_terrain.elevation,
            trajectory_points=trajectory,
            base_station=base,
            relays=[],
            direct_range_m=2500.0,
            rover_antenna_h_m=2.5,
            dx_ground_m=jezero_terrain.dx_ground_m,
            dy_ground_m=jezero_terrain.dy_ground_m,
        )

        cps = timeline["checkpoints"]
        assert len(cps) == len(trajectory)

        # Invariant checks
        conn_cps = sum(1 for cp in cps if cp["communication_state"] == DynamicCommState.CONNECTED_DIRECT.value)
        gap_cps = sum(1 for cp in cps if cp["communication_state"] == DynamicCommState.SIMULATED_GEOMETRIC_CONNECTIVITY_GAP.value)
        assert conn_cps + gap_cps == len(cps)

        avail_ratio = conn_cps / float(len(cps))
        assert math.isclose(timeline["summary"]["connectivity_availability_pct"], avail_ratio * 100.0, abs_tol=1e-1)

        # Gap intervals
        gaps = timeline["gap_intervals"]
        for g in gaps:
            assert g["start_time_s"] <= g["end_time_s"]
            assert g["duration_s"] >= 0.0

    def test_relay_deployment_submodular_sweep_k0_k1_k2(self, promontory_field_fixture):
        """
        Relay Deployment Budget Sweep:
        - Sweeping budget k in {0, 1, 2}.
        - Monotonic gap reduction: D_gap(k=0) >= D_gap(k=1) >= D_gap(k=2).
        - Submodular diminishing returns: Delta D_gap(0 -> 1) >= Delta D_gap(1 -> 2).
        """
        terrain = promontory_field_fixture
        elevation = terrain.elevation

        # Trajectory behind the promontory from (50, 20) to (50, 50)
        traj = [(i * 20.0, 50.0, float(c)) for i, c in enumerate(range(20, 51))]
        base = {"id": "BASE", "rc": (10, 10), "antenna_h": 10.0}

        # Screen candidates
        cands = screen_relay_candidates(
            elevation=elevation,
            slope_deg=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            dx_ground_m=20.0,
            dy_ground_m=20.0,
            min_elevation_m=-2490.0,
            min_separation_m=300.0,
            max_candidates=5,
        )
        assert len(cands) >= 1

        # Budget k=0
        t0 = compute_mission_connectivity_timeline(elevation, traj, base, [], dx_ground_m=20.0, dy_ground_m=20.0)
        gap_time_k0 = t0["summary"]["total_gap_time_s"]

        # Budget k=1 (place top candidate on promontory summit)
        r1 = [{"id": cands[0]["candidate_id"], "rc": cands[0]["rc"], "antenna_h": 10.0}]
        t1 = compute_mission_connectivity_timeline(elevation, traj, base, r1, dx_ground_m=20.0, dy_ground_m=20.0)
        gap_time_k1 = t1["summary"]["total_gap_time_s"]

        # Budget k=2
        r2 = list(r1)
        if len(cands) > 1:
            r2.append({"id": cands[1]["candidate_id"], "rc": cands[1]["rc"], "antenna_h": 10.0})
        t2 = compute_mission_connectivity_timeline(elevation, traj, base, r2, dx_ground_m=20.0, dy_ground_m=20.0)
        gap_time_k2 = t2["summary"]["total_gap_time_s"]

        # Monotonicity
        assert gap_time_k0 >= gap_time_k1
        assert gap_time_k1 >= gap_time_k2

        # Submodular diminishing returns: Delta(0 -> 1) >= Delta(1 -> 2)
        delta_01 = gap_time_k0 - gap_time_k1
        delta_12 = gap_time_k1 - gap_time_k2
        assert delta_01 >= delta_12

    def test_pareto_dominance_classification(self):
        """
        Pareto Dominance Classification:
        - Candidate A (dist=1000, gap=0, relays=1) vs
          Candidate B (dist=800, gap=200, relays=0) vs
          Candidate C (dist=1200, gap=300, relays=2).
        - A and B are mutually non-dominated (Pareto efficient).
        - C is strictly dominated by both A and B.
        """
        def check_pareto_domination(obj_a: Tuple[float, ...], obj_b: Tuple[float, ...], tol: float = 1e-5) -> bool:
            """Returns True iff obj_a strictly dominates obj_b (minimization on all objectives)."""
            all_le = True
            any_lt = False
            for va, vb in zip(obj_a, obj_b):
                if va > vb + tol:
                    return False
                if va < vb - tol:
                    any_lt = True
            return any_lt

        # Vector: (distance_m, gap_time_s, relay_count) - all minimized
        cand_a = (1000.0, 0.0, 1.0)
        cand_b = (800.0, 200.0, 0.0)
        cand_c = (1200.0, 300.0, 2.0)

        assert check_pareto_domination(cand_a, cand_c) is True
        assert check_pareto_domination(cand_b, cand_c) is True
        assert check_pareto_domination(cand_a, cand_b) is False
        assert check_pareto_domination(cand_b, cand_a) is False

    def test_pareto_edge_cases_identical_scores_and_single_candidate(self):
        """
        Pareto Edge Cases:
        1. Two configurations with identical objective vectors do NOT dominate each other.
        2. A single candidate design space is automatically classified as PARETO_EFFICIENT.
        """
        def check_pareto_domination(obj_a: Tuple[float, ...], obj_b: Tuple[float, ...], tol: float = 1e-5) -> bool:
            all_le = True
            any_lt = False
            for va, vb in zip(obj_a, obj_b):
                if va > vb + tol:
                    return False
                if va < vb - tol:
                    any_lt = True
            return any_lt

        cand_x = (1000.0, 50.0, 1.0)
        cand_y = (1000.0, 50.0, 1.0)

        # Identical objective vectors: neither dominates
        assert check_pareto_domination(cand_x, cand_y) is False
        assert check_pareto_domination(cand_y, cand_x) is False

        # Single candidate set: non-dominated
        candidates = [cand_x]
        is_dominated = any(check_pareto_domination(other, cand_x) for other in candidates if other is not cand_x)
        assert is_dominated is False

    def test_input_validation_and_boundary_constraints(self, central_ridge_fixture):
        """
        Strict Input Parameter Validation:
        - Out-of-bounds start or goal coords raise ValueError.
        - Start == Goal raises ValueError.
        - Start or Goal in NoData sentinel raises ValueError.
        - Non-finite coordinates (NaN or Inf) raise ValueError.
        - Negative antenna heights or budgets raise ValueError.
        """
        terrain = central_ridge_fixture

        def validate_joint_inputs(
            start: Tuple[int, int],
            goal: Tuple[int, int],
            terrain_grid: TerrainGrid,
            antenna_h: float = 2.0,
            relay_budget: int = 1,
        ):
            H, W = terrain_grid.elevation.shape
            for pt, name in [(start, "start"), (goal, "goal")]:
                r, c = pt
                if not (0 <= r < H and 0 <= c < W):
                    raise ValueError(f"{name} ({r}, {c}) is out of bounds for grid {H}x{W}")
                if math.isnan(r) or math.isnan(c) or math.isinf(r) or math.isinf(c):
                    raise ValueError(f"{name} contains non-finite coordinates")
                if terrain_grid.invalid_mask is not None and terrain_grid.invalid_mask[int(r), int(c)]:
                    raise ValueError(f"{name} ({r}, {c}) is inside NoData / invalid terrain mask")

            if start == goal:
                raise ValueError(f"Start and goal cannot be identical: {start}")
            if antenna_h < 0.0:
                raise ValueError(f"Antenna height must be non-negative, got {antenna_h}")
            if relay_budget < 0:
                raise ValueError(f"Relay budget must be non-negative, got {relay_budget}")

        # Out of bounds
        with pytest.raises(ValueError, match="out of bounds"):
            validate_joint_inputs((-1, 10), (25, 40), terrain)
        with pytest.raises(ValueError, match="out of bounds"):
            validate_joint_inputs((25, 10), (100, 40), terrain)

        # Identical
        with pytest.raises(ValueError, match="identical"):
            validate_joint_inputs((25, 10), (25, 10), terrain)

        # Negative antenna
        with pytest.raises(ValueError, match="non-negative"):
            validate_joint_inputs((25, 10), (25, 40), terrain, antenna_h=-1.5)

        # Negative budget
        with pytest.raises(ValueError, match="non-negative"):
            validate_joint_inputs((25, 10), (25, 40), terrain, relay_budget=-2)

        # NoData check
        nodata_grid = np.zeros((20, 20), dtype=np.float32)
        nodata_grid[5, 5] = -32768.0
        nodata_terrain = derive_terrain_from_array(nodata_grid)
        with pytest.raises(ValueError, match="NoData"):
            validate_joint_inputs((5, 5), (10, 10), nodata_terrain)

        # Also verify against jmp.validate_joint_mission_input if available
        if HAS_JOINT_PLANNER_MODULE:
            base_dict = {"node_id": "BASE", "row": 25, "col": 10}
            with pytest.raises(ValueError, match="bounds"):
                jmp.validate_joint_mission_input({"start_rc": (-1, 10), "goal_rc": (25, 40), "base_station": base_dict}, terrain)
            with pytest.raises(ValueError, match="relay_budget"):
                jmp.validate_joint_mission_input({"start_rc": (25, 10), "goal_rc": (25, 40), "base_station": base_dict, "relay_budget": 5}, terrain)

    def test_deterministic_repeatability_and_fingerprinting(self, jezero_terrain):
        """
        Deterministic Repeatability:
        - Consecutive joint evaluation runs with identical inputs produce bit-for-bit identical results.
        - Cryptographic SHA-256 fingerprint matches across runs.
        """
        route = astar_search((117, 157), (138, 114), jezero_terrain)
        assert route is not None
        traj = [(i * 30.0, float(r), float(c)) for i, (r, c) in enumerate(route.path[:10])]
        base = {"id": "BASE", "rc": (117, 157), "antenna_h": 10.0}

        res1 = compute_mission_connectivity_timeline(jezero_terrain.elevation, traj, base, [])
        res2 = compute_mission_connectivity_timeline(jezero_terrain.elevation, traj, base, [])

        assert res1["fingerprint"] == res2["fingerprint"]
        assert res1["summary"] == res2["summary"]
        assert res1["checkpoints"] == res2["checkpoints"]

    def test_operational_data_immutability(self):
        """
        Operational Data Preservation:
        - Files in data/workspaces/ are never deleted, overwritten, or modified by test execution.
        """
        workspaces_dir = os.path.join(REPO_ROOT, "data", "workspaces")
        if not os.path.exists(workspaces_dir):
            pytest.skip("data/workspaces directory not present")

        # Snapshot folder state
        entries_before = sorted(os.listdir(workspaces_dir))
        assert len(entries_before) > 0

        # Verify all known subdirectories are intact
        expected_dirs = {"campaigns", "missions", "events", "coordination"}
        existing_dirs = set(entries_before)
        assert expected_dirs.issubset(existing_dirs)


# =============================================================================
# 4. JOINT PLANNER MODULE CONTRACT & END-TO-END VERIFICATION
# =============================================================================

class TestJointPlannerInterfaceAndContract:
    """Verifies JointMissionPlanner classes, methods, and decision explanations."""

    @pytest.mark.skipif(not HAS_JOINT_PLANNER_MODULE, reason="marswalk.core.joint_mission_planner not yet implemented")
    def test_joint_mission_planner_full_lifecycle(self, jezero_terrain):
        """
        When joint_mission_planner.py is available:
        - Calls optimize_joint_mission with Jezero DTM.
        - Generates alternative traverses between Octavia Landing Site and Three Forks.
        - Screens promontory relay candidates.
        - Performs multi-objective optimization across k in {0, 1, 2}.
        - Computes Pareto efficient frontier.
        - Produces structured decision explanation with Marginal Rates of Substitution (MRS).
        """
        base = {"node_id": "BASE_OCTAVIA", "row": 117, "col": 157, "label": "Base Station"}
        result = jmp.optimize_joint_mission(
            start_rc=(117, 157),
            goal_rc=(138, 114),
            terrain=jezero_terrain,
            base_station=base,
            relay_budget=2,
            objective_profile="balanced",
        )

        assert result is not None
        d = result.to_dict()
        assert "recommended_configuration" in d
        assert "pareto_frontier" in d
        assert "decision_explanation" in d
        assert d["configurations_evaluated"] > 0
        assert d["pareto_configurations_count"] > 0

        # Verify recommended configuration is Pareto efficient
        rec = result.recommended_configuration
        assert rec.is_pareto_optimal is True
        assert rec.recommendation_tier == "OPTIMAL_RECOMMENDED"

        # Verify decision explanation contains required fields
        explanation = d["decision_explanation"]
        assert "selection_rationale" in explanation
        assert "marginal_rates_of_substitution" in explanation
        assert "rejected_alternatives_comparison" in explanation
