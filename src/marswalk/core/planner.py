"""
MarsWalk Core Route Intelligence Engine.
Implements 8-connected A* pathfinding with calibrated geodetic octile heuristics,
pairwise directed leg caching, and multi-profile route optimization
(Conservative, Science-First, and Balanced).
"""

from dataclasses import dataclass, field
import enum
import heapq
import itertools
import math
import time
from typing import Dict, List, Optional, Set, Tuple, Union, Any
import numpy as np

from marswalk.core.terrain import (
    TerrainConfig,
    TerrainGrid,
    calculate_edge_cost,
    calculate_step_distance,
    get_profile_terrain_config,
)


@dataclass
class ScienceWaypoint:
    """
    Represents a documented science exploration target.
    """

    id: str
    name: str
    rc: Tuple[int, int]
    priority_score: float = 0.0
    geological_context: str = ""
    crism_signature: str = ""
    pds_citation: str = ""


@dataclass(frozen=True)
class PlannerConfig:
    """
    Configuration parameters for route planning and trade-off optimization.

    Parameters
    ----------
    profile : str
        Planning profile: "conservative", "science_first", or "balanced".
    science_appetite_gamma : float
        Trade-off exponent for Balanced profile (gamma > 0.0). Higher gamma penalizes
        added terrain detour cost more aggressively.
    max_distance_m : Optional[float]
        Physical travel distance budget in meters. If exceeded, route is flagged
        as is_budget_feasible = False.
    max_waypoints : int
        Maximum number of candidate waypoints for exact subset search (default 6).
    """

    profile: str = "conservative"
    science_appetite_gamma: float = 1.0
    max_distance_m: Optional[float] = None
    max_waypoints: int = 6

    def __post_init__(self):
        valid_profiles = {"conservative", "science_first", "balanced"}
        if self.profile not in valid_profiles:
            raise ValueError(f"Unknown profile '{self.profile}'. Must be one of {valid_profiles}")
        if self.science_appetite_gamma <= 0:
            raise ValueError(
                f"science_appetite_gamma must be strictly positive, got {self.science_appetite_gamma}"
            )
        if self.max_distance_m is not None and self.max_distance_m <= 0:
            raise ValueError(f"max_distance_m must be positive, got {self.max_distance_m}")
        if self.max_waypoints <= 0 or self.max_waypoints > 8:
            raise ValueError(f"max_waypoints must be between 1 and 8, got {self.max_waypoints}")


@dataclass
class LegResult:
    """
    Result of a point-to-point traverse between two specific nodes.
    """

    start_rc: Tuple[int, int]
    goal_rc: Tuple[int, int]
    path: List[Tuple[int, int]]
    distance_m: float
    cost: float
    is_reachable: bool


class VehicleMode(str, enum.Enum):
    CREW_EVA = "crew_eva"
    ROBOTIC_ROVER = "robotic_rover"


# Formal classification of operational planning assumptions and limits
ENGINEERING_ASSUMPTIONS: Dict[str, Dict[str, Any]] = {
    "crew_eva_speed": {
        "parameter": "Crew EVA Walk Speed",
        "value": "2.0 km/h (range 1.5–2.5 km/h)",
        "classification": "Engineering Analogue",
        "citation": "Apollo Lunar Surface EVA Traverses (NASA SP-287 / Waligora et al. 1975)",
        "disclosure": "Engineering analogue based on Apollo lunar surface traverses; NOT validated Mars astronaut performance in Martian gravity (0.38g) or pressurized suits.",
        "is_physical_limit": False,
    },
    "robotic_rover_speed": {
        "parameter": "Robotic Rover Drive Rate",
        "value": "0.035 m/s (~0.126 km/h, range 0.025–0.045 m/s)",
        "classification": "Sourced Technical Value",
        "citation": "Mars 2020 Perseverance / MSL Curiosity Surface Operations Telemetry (NASA/JPL-Caltech)",
        "disclosure": "Empirical autonomous drive rates from Mars surface rover missions.",
        "is_physical_limit": False,
    },
    "crew_eva_duration_limit": {
        "parameter": "Crew EVA Operational Limit",
        "value": "8.0 hours (28,800 s)",
        "classification": "Configurable Mission Constraint",
        "citation": "NASA EVA Standard Baseline / ISS PLSS Life-Support Consumables Envelope",
        "disclosure": "Configurable operational constraint based on terrestrial analog & ISS suit consumables; not a physical limit.",
        "is_physical_limit": False,
    },
    "robotic_rover_drive_window": {
        "parameter": "Robotic Rover Single-Sol Drive Window",
        "value": "4.0 hours (14,400 s)",
        "classification": "Configurable Mission Constraint",
        "citation": "Mars 2020 Tactical Planning Window Model (NASA/JPL)",
        "disclosure": "Configurable planning window based on daily thermal, power, and DSN communications availability.",
        "is_physical_limit": False,
    },
    "science_dwell_duration": {
        "parameter": "Science Observation Dwell Time",
        "value": "15 min (900 s) per intermediate target",
        "classification": "Configurable Operational Assumption",
        "citation": "Field Science Operations Protocol",
        "disclosure": "Standard tactical dwell duration for remote sensing, multispectral imaging, and contact instrument placement.",
        "is_physical_limit": False,
    },
}

# Default operational time limits (in seconds)
OPERATIONAL_LIMITS_S: Dict[str, float] = {
    VehicleMode.CREW_EVA: 8.0 * 3600.0,       # 8.0 hours for suited astronaut EVA
    VehicleMode.ROBOTIC_ROVER: 4.0 * 3600.0,   # 4.0 hours single-sol drive window
}


def format_duration(s: float) -> str:
    """Format duration seconds into human-readable mission time string."""
    if s < 0 or math.isnan(s):
        return "0s"
    if s < 60:
        return f"{round(s)}s"
    m = round(s / 60.0)
    if m < 60:
        return f"{m} min"
    hrs = m // 60
    rem_m = m % 60
    if hrs < 24:
        return f"{hrs}h {rem_m}m" if rem_m > 0 else f"{hrs}h"
    days = hrs // 24
    rem_h = hrs % 24
    return f"{days}d {rem_h}h"


def calculate_traverse_time(
    cost: float,
    mode: str = "crew_eva",
    v_nominal_kmh: Optional[float] = None,
    v_min_kmh: Optional[float] = None,
    v_max_kmh: Optional[float] = None,
    speed_multiplier: float = 1.0,
    vehicle_mode: Optional[str] = None,
) -> Tuple[float, float, float, str]:
    """
    Calculate estimated astronaut/rover traverse time based on Apollo EVA velocity
    or Mars 2020 robotic rover drive rate models adjusted for terrain impedance/effort (cost).

    Returns (time_nominal_s, time_min_s, time_max_s, formatted_string).
    """
    if vehicle_mode is not None:
        mode = vehicle_mode
    if cost <= 0 or math.isinf(cost):
        return 0.0, 0.0, 0.0, "—"

    mult = max(0.001, speed_multiplier)

    if mode == "robotic_rover" and v_nominal_kmh is None:
        # Mars 2020 Perseverance / MSL Curiosity drive rate: nominal speed 0.035 m/s (~0.126 km/h)
        # Range: [0.025, 0.045] m/s
        v_nom = 0.035 * mult
        v_min = 0.025 * mult
        v_max = 0.045 * mult
    else:
        # Crew EVA model: nominal 2.0 km/h (~0.5556 m/s), range [1.5, 2.5] km/h
        nom_kmh = v_nominal_kmh if v_nominal_kmh is not None else 2.0
        min_kmh = v_min_kmh if v_min_kmh is not None else 1.5
        max_kmh = v_max_kmh if v_max_kmh is not None else 2.5

        v_nom = (nom_kmh * 1000.0 / 3600.0) * mult
        v_min = (min_kmh * 1000.0 / 3600.0) * mult
        v_max = (max_kmh * 1000.0 / 3600.0) * mult

    t_nom = cost / v_nom
    t_min = cost / v_max
    t_max = cost / v_min

    nom_str = format_duration(t_nom)
    min_str = format_duration(t_min)
    max_str = format_duration(t_max)

    if min_str.endswith(" min") and max_str.endswith(" min"):
        min_val = min_str.replace(" min", "")
        formatted = f"{nom_str} (range: {min_val}–{max_str})"
    elif min_str.endswith("h") and max_str.endswith("h"):
        min_val = min_str.replace("h", "")
        formatted = f"{nom_str} (range: {min_val}–{max_str})"
    else:
        formatted = f"{nom_str} (range: {min_str}–{max_str})"

    return t_nom, t_min, t_max, formatted


@dataclass
class TimelineEvent:
    """
    Discrete operational event in the mission schedule.
    """
    event_type: str  # "start", "traverse_leg", "science_dwell", "scenario_delay", "arrival"
    label: str
    target_id: Optional[str]
    leg_index: Optional[int]
    start_time_s: float
    end_time_s: float
    duration_s: float
    distance_m: float
    formatted_duration: str
    formatted_cumulative_time: str
    notes: str = ""


@dataclass
class MissionTimeline:
    """
    Comprehensive operational mission timeline breakdown.
    """
    vehicle_mode: str
    total_traverse_time_s: float
    total_dwell_time_s: float
    total_operational_delay_s: float
    total_mission_time_s: float
    operational_limit_s: float
    remaining_margin_s: float
    is_within_limit: bool
    events: List[TimelineEvent]
    formatted_traverse_time: str
    formatted_dwell_time: str
    formatted_mission_time: str
    formatted_remaining_margin: str
    assumptions: Dict[str, Dict[str, Any]] = field(default_factory=lambda: dict(ENGINEERING_ASSUMPTIONS))


@dataclass
class RouteResult:
    """
    Structured outcome of a mission traverse plan.
    """

    profile: str
    start_rc: Tuple[int, int]
    goal_rc: Tuple[int, int]
    path: List[Tuple[int, int]]
    distance_m: float
    cost: float
    science_score: float
    visited_waypoint_ids: List[str]
    num_cells: int
    num_steps: int
    is_reachable: bool
    is_budget_feasible: bool
    max_distance_m: Optional[float]
    status_message: str
    execution_time_s: float = 0.0
    travel_time_s: float = 0.0
    travel_time_min_s: float = 0.0
    travel_time_max_s: float = 0.0
    formatted_travel_time: str = ""
    vehicle_mode: str = "crew_eva"
    speed_multiplier: float = 1.0
    legs: Optional[List[LegResult]] = None
    timeline: Optional[MissionTimeline] = None

    def __post_init__(self):
        if not self.formatted_travel_time and self.is_reachable and self.cost > 0 and not math.isinf(self.cost):
            t_nom, t_min, t_max, fmt = calculate_traverse_time(
                self.cost,
                mode=self.vehicle_mode,
                speed_multiplier=self.speed_multiplier,
            )
            self.travel_time_s = t_nom
            self.travel_time_min_s = t_min
            self.travel_time_max_s = t_max
            self.formatted_travel_time = fmt
        elif not self.is_reachable or math.isinf(self.cost):
            self.formatted_travel_time = "—"


def build_mission_timeline(
    route: RouteResult,
    vehicle_mode: str = "crew_eva",
    dwell_time_per_stop_s: float = 900.0,
    operational_delay_s: float = 0.0,
    operational_limit_s: Optional[float] = None,
    speed_multiplier: float = 1.0,
    legs: Optional[List[LegResult]] = None,
    stop_labels: Optional[List[str]] = None,
) -> MissionTimeline:
    """
    Construct a complete leg-by-leg timeline breakdown including traversal,
    science dwell times at stops, scenario operational delays, and remaining margins.
    """
    limit_s = operational_limit_s
    if limit_s is None:
        limit_s = OPERATIONAL_LIMITS_S.get(vehicle_mode, 8.0 * 3600.0)

    events: List[TimelineEvent] = []
    current_time_s = 0.0

    # Start event
    events.append(
        TimelineEvent(
            event_type="start",
            label="Mission Departure",
            target_id=None,
            leg_index=None,
            start_time_s=0.0,
            end_time_s=0.0,
            duration_s=0.0,
            distance_m=0.0,
            formatted_duration="0s",
            formatted_cumulative_time="00:00",
            notes=f"Departing from ({route.start_rc[0]}, {route.start_rc[1]})",
        )
    )

    if not route.is_reachable:
        return MissionTimeline(
            vehicle_mode=vehicle_mode,
            total_traverse_time_s=0.0,
            total_dwell_time_s=0.0,
            total_operational_delay_s=operational_delay_s,
            total_mission_time_s=operational_delay_s,
            operational_limit_s=limit_s,
            remaining_margin_s=limit_s - operational_delay_s,
            is_within_limit=operational_delay_s <= limit_s,
            events=events,
            formatted_traverse_time="—",
            formatted_dwell_time="—",
            formatted_mission_time="—",
            formatted_remaining_margin="—",
        )

    # Determine traverse legs
    leg_list = legs if legs else (route.legs if route.legs else None)
    if not leg_list:
        leg_list = [
            LegResult(
                start_rc=route.start_rc,
                goal_rc=route.goal_rc,
                path=route.path,
                distance_m=route.distance_m,
                cost=route.cost,
                is_reachable=route.is_reachable,
            )
        ]

    total_traverse_s = 0.0
    total_dwell_s = 0.0
    num_legs = len(leg_list)

    for i, leg in enumerate(leg_list):
        t_nom, _, _, leg_fmt = calculate_traverse_time(
            leg.cost,
            mode=vehicle_mode,
            speed_multiplier=speed_multiplier,
        )
        leg_start = current_time_s
        leg_end = leg_start + t_nom
        current_time_s = leg_end
        total_traverse_s += t_nom

        dest_id = None
        if stop_labels and i < len(stop_labels):
            dest_label = stop_labels[i]
        elif i == num_legs - 1:
            dest_label = f"Goal ({route.goal_rc[0]}, {route.goal_rc[1]})"
        else:
            wid = route.visited_waypoint_ids[i] if i < len(route.visited_waypoint_ids) else f"Stop {i+1}"
            dest_label = wid
            dest_id = wid

        events.append(
            TimelineEvent(
                event_type="traverse_leg",
                label=f"Traverse Leg {i+1} -> {dest_label}",
                target_id=dest_id,
                leg_index=i + 1,
                start_time_s=leg_start,
                end_time_s=leg_end,
                duration_s=t_nom,
                distance_m=leg.distance_m,
                formatted_duration=format_duration(t_nom),
                formatted_cumulative_time=format_duration(current_time_s),
                notes=f"Distance: {leg.distance_m:.0f}m, Effort: {leg.cost:.0f}",
            )
        )

        # If this leg arrives at an intermediate science stop, add dwell event
        if i < num_legs - 1:
            dwell_s = dwell_time_per_stop_s
            dwell_start = current_time_s
            dwell_end = dwell_start + dwell_s
            current_time_s = dwell_end
            total_dwell_s += dwell_s

            events.append(
                TimelineEvent(
                    event_type="science_dwell",
                    label=f"Science Dwell: {dest_label}",
                    target_id=dest_id,
                    leg_index=i + 1,
                    start_time_s=dwell_start,
                    end_time_s=dwell_end,
                    duration_s=dwell_s,
                    distance_m=0.0,
                    formatted_duration=format_duration(dwell_s),
                    formatted_cumulative_time=format_duration(current_time_s),
                    notes="Surface sampling and in-situ instrument analysis",
                )
            )

    # If operational delay is present (e.g. dust storm or comms hold)
    if operational_delay_s > 0.0:
        delay_start = current_time_s
        delay_end = delay_start + operational_delay_s
        current_time_s = delay_end

        events.append(
            TimelineEvent(
                event_type="scenario_delay",
                label="Operational Comms / Dust Hold Delay",
                target_id=None,
                leg_index=None,
                start_time_s=delay_start,
                end_time_s=delay_end,
                duration_s=operational_delay_s,
                distance_m=0.0,
                formatted_duration=format_duration(operational_delay_s),
                formatted_cumulative_time=format_duration(current_time_s),
                notes="Visibility safety restriction and telemetry verification hold",
            )
        )

    # Arrival event
    events.append(
        TimelineEvent(
            event_type="arrival",
            label="Final Mission Arrival",
            target_id=None,
            leg_index=None,
            start_time_s=current_time_s,
            end_time_s=current_time_s,
            duration_s=0.0,
            distance_m=0.0,
            formatted_duration="0s",
            formatted_cumulative_time=format_duration(current_time_s),
            notes=f"Traverse complete at ({route.goal_rc[0]}, {route.goal_rc[1]})",
        )
    )

    total_mission_s = current_time_s
    remaining_margin_s = limit_s - total_mission_s
    is_within = total_mission_s <= limit_s

    return MissionTimeline(
        vehicle_mode=vehicle_mode,
        total_traverse_time_s=total_traverse_s,
        total_dwell_time_s=total_dwell_s,
        total_operational_delay_s=operational_delay_s,
        total_mission_time_s=total_mission_s,
        operational_limit_s=limit_s,
        remaining_margin_s=remaining_margin_s,
        is_within_limit=is_within,
        events=events,
        formatted_traverse_time=format_duration(total_traverse_s),
        formatted_dwell_time=format_duration(total_dwell_s),
        formatted_mission_time=format_duration(total_mission_s),
        formatted_remaining_margin=format_duration(abs(remaining_margin_s)) if is_within else f"-{format_duration(abs(remaining_margin_s))}",
    )


def generalized_octile_heuristic(
    u: Tuple[int, int],
    v: Tuple[int, int],
    dx_ground_m: float,
    dy_ground_m: float,
) -> float:
    """
    Calculate the admissible and consistent obstacle-free ground distance heuristic
    on an 8-connected grid with unequal horizontal (dx) and vertical (dy) ground spacings.

    Formulation:
    dr = |r2 - r1|, dc = |c2 - c1|
    d_diag = sqrt(dx^2 + dy^2)
    num_diag = min(dr, dc)
    remaining_dr = dr - num_diag
    remaining_dc = dc - num_diag
    h = num_diag * d_diag + remaining_dr * dy + remaining_dc * dx

    Because edge costs C(a -> b) >= d_ground(a -> b) everywhere, this heuristic
    never overestimates the true travel cost and is strictly admissible.
    """
    dr = abs(v[0] - u[0])
    dc = abs(v[1] - u[1])

    d_diag = math.sqrt(dx_ground_m**2 + dy_ground_m**2)
    min_steps = min(dr, dc)
    rem_r = dr - min_steps
    rem_c = dc - min_steps

    return min_steps * d_diag + rem_r * dy_ground_m + rem_c * dx_ground_m


def astar_search(
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    terrain: TerrainGrid,
    terrain_config: Optional[TerrainConfig] = None,
    blocked_mask: Optional[np.ndarray] = None,
    cost_multiplier_mask: Optional[np.ndarray] = None,
) -> LegResult:
    """
    Point-to-point shortest path search on an 8-connected grid using A*.

    Parameters
    ----------
    start_rc : Tuple[int, int]
        Starting (row, col) coordinates.
    goal_rc : Tuple[int, int]
        Goal (row, col) coordinates.
    terrain : TerrainGrid
        Calibrated terrain data structure.
    terrain_config : Optional[TerrainConfig]
        Optional override for edge-cost parameters.
    blocked_mask : Optional[np.ndarray]
        2D boolean array where True indicates temporarily blocked/unavailable terrain.
    cost_multiplier_mask : Optional[np.ndarray]
        2D float array specifying terrain traversal impedance multipliers (>= 1.0)
        such as unstable sand dunes or degraded mobility corridors.

    Returns
    -------
    LegResult : Structured result containing path, distance, cost, and reachability.
    """
    H, W = terrain.shape

    # Validate endpoints
    for pt, name in [(start_rc, "Start"), (goal_rc, "Goal")]:
        if not (0 <= pt[0] < H and 0 <= pt[1] < W):
            return LegResult(start_rc, goal_rc, [], 0.0, float("inf"), False)
        if terrain.invalid_mask[pt[0], pt[1]]:
            return LegResult(start_rc, goal_rc, [], 0.0, float("inf"), False)
        if blocked_mask is not None and blocked_mask[pt[0], pt[1]]:
            return LegResult(start_rc, goal_rc, [], 0.0, float("inf"), False)

    # Trivial zero-step path
    if start_rc == goal_rc:
        return LegResult(start_rc, goal_rc, [start_rc], 0.0, 0.0, True)

    dx = terrain.dx_ground_m
    dy = terrain.dy_ground_m

    # 8-connected neighbor offsets
    neighbors_delta = [
        (-1, 0), (1, 0), (0, -1), (0, 1),
        (-1, -1), (-1, 1), (1, -1), (1, 1)
    ]

    h_start = generalized_octile_heuristic(start_rc, goal_rc, dx, dy)
    # Priority queue stores (f_score, g_score, (r, c))
    pq: List[Tuple[float, float, Tuple[int, int]]] = [(h_start, 0.0, start_rc)]
    g_score: Dict[Tuple[int, int], float] = {start_rc: 0.0}
    dist_so_far: Dict[Tuple[int, int], float] = {start_rc: 0.0}
    parent: Dict[Tuple[int, int], Tuple[int, int]] = {}

    while pq:
        f, g, u = heapq.heappop(pq)

        if u == goal_rc:
            # Reconstruct path
            path = []
            curr = u
            while curr in parent:
                path.append(curr)
                curr = parent[curr]
            path.append(start_rc)
            path.reverse()
            return LegResult(
                start_rc=start_rc,
                goal_rc=goal_rc,
                path=path,
                distance_m=dist_so_far[goal_rc],
                cost=g_score[goal_rc],
                is_reachable=True,
            )

        if g > g_score.get(u, float("inf")):
            continue

        ur, uc = u
        for dr, dc in neighbors_delta:
            nr = ur + dr
            nc = uc + dc

            if not (0 <= nr < H and 0 <= nc < W):
                continue
            if terrain.invalid_mask[nr, nc]:
                continue
            if blocked_mask is not None and blocked_mask[nr, nc]:
                continue

            v = (nr, nc)
            edge_c = calculate_edge_cost(u, v, terrain, config=terrain_config)
            if math.isinf(edge_c):
                continue

            # Apply localized traversal cost multiplier (e.g. unstable sand or degraded mobility)
            if cost_multiplier_mask is not None:
                mult = float(cost_multiplier_mask[nr, nc])
                if mult > 1.0:
                    edge_c *= mult

            step_d = calculate_step_distance(u, v, dx, dy)
            tentative_g = g + edge_c

            if tentative_g < g_score.get(v, float("inf")):
                g_score[v] = tentative_g
                dist_so_far[v] = dist_so_far[u] + step_d
                parent[v] = u
                h_v = generalized_octile_heuristic(v, goal_rc, dx, dy)
                heapq.heappush(pq, (tentative_g + h_v, tentative_g, v))

    # Destination was unreachable
    return LegResult(start_rc, goal_rc, [], 0.0, float("inf"), False)


def compute_pairwise_leg_cache(
    nodes: List[Tuple[int, int]],
    terrain: TerrainGrid,
    terrain_config: Optional[TerrainConfig] = None,
    blocked_mask: Optional[np.ndarray] = None,
    cost_multiplier_mask: Optional[np.ndarray] = None,
) -> Dict[Tuple[Tuple[int, int], Tuple[int, int]], LegResult]:
    """
    Precompute directed A* routes between all ordered pairs (u, v) in nodes.
    Preserves directionality (u -> v != v -> u) due to asymmetric uphill penalties.
    """
    cache: Dict[Tuple[Tuple[int, int], Tuple[int, int]], LegResult] = {}
    for u in nodes:
        for v in nodes:
            if u == v:
                cache[(u, v)] = LegResult(u, v, [u], 0.0, 0.0, True)
            else:
                cache[(u, v)] = astar_search(
                    u,
                    v,
                    terrain,
                    terrain_config=terrain_config,
                    blocked_mask=blocked_mask,
                    cost_multiplier_mask=cost_multiplier_mask,
                )
    return cache


def stitch_path_legs(
    ordered_nodes: List[Tuple[int, int]],
    leg_cache: Dict[Tuple[Tuple[int, int], Tuple[int, int]], LegResult],
) -> Tuple[List[Tuple[int, int]], float, float, bool]:
    """
    Stitch precomputed leg paths together without duplicating adjoining endpoints.

    Returns
    -------
    Tuple[List[Tuple[int, int]], float, float, bool] :
        (stitched_path, total_distance_m, total_cost, is_valid)
    """
    if not ordered_nodes:
        return [], 0.0, float("inf"), False
    if len(ordered_nodes) == 1:
        return [ordered_nodes[0]], 0.0, 0.0, True

    stitched_path: List[Tuple[int, int]] = []
    total_dist = 0.0
    total_cost = 0.0

    for i in range(len(ordered_nodes) - 1):
        u = ordered_nodes[i]
        v = ordered_nodes[i + 1]
        leg = leg_cache.get((u, v))

        if leg is None or not leg.is_reachable or math.isinf(leg.cost):
            return [], 0.0, float("inf"), False

        total_dist += leg.distance_m
        total_cost += leg.cost

        if i == 0:
            stitched_path.extend(leg.path)
        else:
            # Exclude duplicate first vertex of the segment
            stitched_path.extend(leg.path[1:])

    return stitched_path, total_dist, total_cost, True


def evaluate_balanced_utility(
    science_score: float,
    total_cost: float,
    baseline_conservative_cost: float,
    gamma: float = 1.0,
) -> float:
    """
    Calculate the Balanced trade-off utility score.

    Formulation:
    If science_score == 0: utility = 0.0
    Otherwise:
    utility = science_score / ( (total_cost / baseline_conservative_cost) ** gamma )
    """
    if science_score <= 0.0:
        return 0.0
    if baseline_conservative_cost <= 0.0 or total_cost <= 0.0:
        return science_score

    cost_ratio = max(1.0, total_cost / baseline_conservative_cost)
    return float(science_score / (cost_ratio ** gamma))


def plan_route(
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    terrain: TerrainGrid,
    waypoints: Optional[List[ScienceWaypoint]] = None,
    config: Optional[PlannerConfig] = None,
    terrain_config: Optional[TerrainConfig] = None,
    blocked_mask: Optional[np.ndarray] = None,
    cost_multiplier_mask: Optional[np.ndarray] = None,
    leg_cache: Optional[Dict[Tuple[Tuple[int, int], Tuple[int, int]], LegResult]] = None,
    vehicle_mode: str = "crew_eva",
    dwell_time_per_stop_s: float = 900.0,
    operational_delay_s: float = 0.0,
    operational_limit_s: Optional[float] = None,
    speed_multiplier: float = 1.0,
) -> RouteResult:
    """
    Master route planning function for MarsWalk.
    Computes Conservative, Science-First, or Balanced mission traverses.

    Parameters
    ----------
    start_rc : Tuple[int, int]
        Starting coordinates (row, col).
    goal_rc : Tuple[int, int]
        Goal coordinates (row, col).
    terrain : TerrainGrid
        Calibrated terrain elevation and physics matrices.
    waypoints : Optional[List[ScienceWaypoint]]
        Candidate science waypoints (maximum 6 active for exact evaluation).
    config : Optional[PlannerConfig]
        Planning settings (profile, science appetite, distance budget).
    terrain_config : Optional[TerrainConfig]
        Optional override for slope and roughness parameters.
    blocked_mask : Optional[np.ndarray]
        Scenario mask of temporarily impassable cells (for stress-testing).
    cost_multiplier_mask : Optional[np.ndarray]
        Scenario cost multiplier mask (e.g. for sand or mobility degradation).
    leg_cache : Optional[Dict]
        Precomputed pairwise leg cache. If None, computed on the fly.
    vehicle_mode : str
        Vehicle drive mode ("crew_eva" or "robotic_rover").
    dwell_time_per_stop_s : float
        Dwell time at visited intermediate science stops (default 900s = 15 min).
    operational_delay_s : float
        Scenario-introduced operational delays (e.g. 1800s for dust storm hold).
    speed_multiplier : float
        Speed multiplier (e.g. 0.5 for degraded rover, 0.6 for storm).
    """
    start_time = time.perf_counter()
    cfg = config if config is not None else PlannerConfig()
    t_cfg = terrain_config if terrain_config is not None else terrain.config
    wps = waypoints if waypoints is not None else []

    if cfg.profile == "conservative" or not wps:
        # Conservative direct traverse ignores candidate waypoints
        pass
    elif len(wps) > cfg.max_waypoints:
        # Gracefully select top waypoints by priority score so exact subset TSP search remains tractable
        wps = sorted(wps, key=lambda w: w.priority_score, reverse=True)[:cfg.max_waypoints]

    # 1. Compute direct Conservative route between start and goal
    conservative_leg = astar_search(
        start_rc,
        goal_rc,
        terrain,
        terrain_config=t_cfg,
        blocked_mask=blocked_mask,
        cost_multiplier_mask=cost_multiplier_mask,
    )

    if not conservative_leg.is_reachable or math.isinf(conservative_leg.cost):
        elapsed = time.perf_counter() - start_time
        res = RouteResult(
            profile=cfg.profile,
            start_rc=start_rc,
            goal_rc=goal_rc,
            path=[],
            distance_m=0.0,
            cost=float("inf"),
            science_score=0.0,
            visited_waypoint_ids=[],
            num_cells=0,
            num_steps=0,
            is_reachable=False,
            is_budget_feasible=False,
            max_distance_m=cfg.max_distance_m,
            status_message="Destination is unreachable under current terrain constraints.",
            execution_time_s=elapsed,
            vehicle_mode=vehicle_mode,
            speed_multiplier=speed_multiplier,
            legs=[],
        )
        res.timeline = build_mission_timeline(
            res,
            vehicle_mode=vehicle_mode,
            dwell_time_per_stop_s=dwell_time_per_stop_s,
            operational_delay_s=operational_delay_s,
            operational_limit_s=operational_limit_s,
            speed_multiplier=speed_multiplier,
            legs=[],
        )
        return res

    base_cost = conservative_leg.cost
    base_dist = conservative_leg.distance_m

    # If Conservative profile or no candidate waypoints, return direct traverse
    if cfg.profile == "conservative" or not wps:
        elapsed = time.perf_counter() - start_time
        budget_ok = (cfg.max_distance_m is None) or (base_dist <= cfg.max_distance_m)
        status = (
            "Direct conservative least-cost route found."
            if budget_ok
            else f"Conservative route found but exceeds distance budget of {cfg.max_distance_m:.1f} m."
        )
        res = RouteResult(
            profile="conservative",
            start_rc=start_rc,
            goal_rc=goal_rc,
            path=conservative_leg.path,
            distance_m=base_dist,
            cost=base_cost,
            science_score=0.0,
            visited_waypoint_ids=[],
            num_cells=len(conservative_leg.path),
            num_steps=max(0, len(conservative_leg.path) - 1),
            is_reachable=True,
            is_budget_feasible=budget_ok,
            max_distance_m=cfg.max_distance_m,
            status_message=status,
            execution_time_s=elapsed,
            vehicle_mode=vehicle_mode,
            speed_multiplier=speed_multiplier,
            legs=[conservative_leg],
        )
        res.timeline = build_mission_timeline(
            res,
            vehicle_mode=vehicle_mode,
            dwell_time_per_stop_s=dwell_time_per_stop_s,
            operational_delay_s=operational_delay_s,
            operational_limit_s=operational_limit_s,
            speed_multiplier=speed_multiplier,
            legs=[conservative_leg],
        )
        if res.timeline and not res.timeline.is_within_limit:
            res.is_budget_feasible = False
            res.status_message += f" Exceeds operational time limit of {res.timeline.operational_limit_s / 3600.0:.1f} h."
        return res

    # 2. Build or reuse pairwise leg cache
    nodes = [start_rc] + [w.rc for w in wps] + [goal_rc]
    # Remove duplicates if start or goal coincides with a waypoint
    unique_nodes = list(dict.fromkeys(nodes))

    if leg_cache is None:
        leg_cache = compute_pairwise_leg_cache(
            unique_nodes,
            terrain,
            terrain_config=t_cfg,
            blocked_mask=blocked_mask,
            cost_multiplier_mask=cost_multiplier_mask,
        )

    # Waypoint lookup by coordinates
    wp_by_rc = {w.rc: w for w in wps}

    # 3. Evaluate candidate waypoint subsets and TSP permutations
    best_candidate: Optional[Dict[str, Any]] = None

    # Evaluate subsets of waypoints from size 0 up to len(wps)
    for r in range(len(wps) + 1):
        for subset in itertools.combinations(wps, r):
            subset_science = sum(w.priority_score for w in subset)

            # Evaluate all visitation permutations for this subset
            best_perm_path: Optional[List[Tuple[int, int]]] = None
            best_perm_cost = float("inf")
            best_perm_dist = 0.0
            best_perm_legs: List[LegResult] = []

            if not subset:
                # Direct route
                leg = leg_cache.get((start_rc, goal_rc))
                if leg and leg.is_reachable and math.isfinite(leg.cost):
                    best_perm_path = leg.path
                    best_perm_cost = leg.cost
                    best_perm_dist = leg.distance_m
                    best_perm_legs = [leg]
            else:
                for perm in itertools.permutations(subset):
                    perm_nodes = [start_rc] + [w.rc for w in perm] + [goal_rc]
                    stitched, dist_m, cost_val, ok = stitch_path_legs(perm_nodes, leg_cache)
                    if ok and cost_val < best_perm_cost:
                        best_perm_cost = cost_val
                        best_perm_dist = dist_m
                        best_perm_path = stitched
                        best_perm_legs = [
                            leg_cache.get((perm_nodes[i], perm_nodes[i + 1]))
                            for i in range(len(perm_nodes) - 1)
                        ]

            if best_perm_path is None or math.isinf(best_perm_cost):
                continue

            # Evaluate eligibility under profile objective
            perm_wp_ids = [w.id for w in subset]
            is_budget_ok = (cfg.max_distance_m is None) or (best_perm_dist <= cfg.max_distance_m)

            if cfg.profile == "science_first":
                score_tuple = (
                    1 if is_budget_ok else 0,
                    subset_science,
                    -best_perm_cost,
                )
            elif cfg.profile == "balanced":
                util = evaluate_balanced_utility(
                    science_score=subset_science,
                    total_cost=best_perm_cost,
                    baseline_conservative_cost=base_cost,
                    gamma=cfg.science_appetite_gamma,
                )
                score_tuple = (
                    1 if is_budget_ok else 0,
                    util,
                    -best_perm_cost,
                )
            else:
                score_tuple = (1 if is_budget_ok else 0, 0.0, -best_perm_cost)

            if best_candidate is None or score_tuple > best_candidate["score_tuple"]:
                best_candidate = {
                    "score_tuple": score_tuple,
                    "path": best_perm_path,
                    "distance_m": best_perm_dist,
                    "cost": best_perm_cost,
                    "science_score": subset_science,
                    "visited_ids": perm_wp_ids,
                    "is_budget_ok": is_budget_ok,
                    "legs": best_perm_legs,
                }

    elapsed = time.perf_counter() - start_time

    if best_candidate is None:
        res = RouteResult(
            profile=cfg.profile,
            start_rc=start_rc,
            goal_rc=goal_rc,
            path=[],
            distance_m=0.0,
            cost=float("inf"),
            science_score=0.0,
            visited_waypoint_ids=[],
            num_cells=0,
            num_steps=0,
            is_reachable=False,
            is_budget_feasible=False,
            max_distance_m=cfg.max_distance_m,
            status_message="No feasible route found visiting requested waypoints.",
            execution_time_s=elapsed,
            vehicle_mode=vehicle_mode,
            speed_multiplier=speed_multiplier,
            legs=[],
        )
        res.timeline = build_mission_timeline(
            res,
            vehicle_mode=vehicle_mode,
            dwell_time_per_stop_s=dwell_time_per_stop_s,
            operational_delay_s=operational_delay_s,
            operational_limit_s=operational_limit_s,
            speed_multiplier=speed_multiplier,
            legs=[],
        )
        return res

    final_dist = best_candidate["distance_m"]
    budget_ok = best_candidate["is_budget_ok"]
    num_visited = len(best_candidate["visited_ids"])
    status = (
        f"{cfg.profile.capitalize()} route visiting {num_visited}/{len(wps)} waypoints "
        f"with {best_candidate['science_score']:.0f} science points."
    )
    if not budget_ok and cfg.max_distance_m is not None:
        status += f" Warning: exceeds distance budget of {cfg.max_distance_m:.1f} m."

    res = RouteResult(
        profile=cfg.profile,
        start_rc=start_rc,
        goal_rc=goal_rc,
        path=best_candidate["path"],
        distance_m=final_dist,
        cost=best_candidate["cost"],
        science_score=best_candidate["science_score"],
        visited_waypoint_ids=best_candidate["visited_ids"],
        num_cells=len(best_candidate["path"]),
        num_steps=max(0, len(best_candidate["path"]) - 1),
        is_reachable=True,
        is_budget_feasible=budget_ok,
        max_distance_m=cfg.max_distance_m,
        status_message=status,
        execution_time_s=elapsed,
        vehicle_mode=vehicle_mode,
        speed_multiplier=speed_multiplier,
        legs=best_candidate.get("legs", []),
    )
    res.timeline = build_mission_timeline(
        res,
        vehicle_mode=vehicle_mode,
        dwell_time_per_stop_s=dwell_time_per_stop_s,
        operational_delay_s=operational_delay_s,
        operational_limit_s=operational_limit_s,
        speed_multiplier=speed_multiplier,
        legs=best_candidate.get("legs", []),
    )
    if res.timeline and not res.timeline.is_within_limit:
        res.is_budget_feasible = False
        res.status_message += f" Exceeds operational time limit of {res.timeline.operational_limit_s / 3600.0:.1f} h."
    return res


def plan_sequential_multistop_route(
    ordered_points: List[Tuple[int, int]],
    terrain: TerrainGrid,
    stop_ids: Optional[List[str]] = None,
    stop_priorities: Optional[List[float]] = None,
    config: Optional[PlannerConfig] = None,
    terrain_config: Optional[TerrainConfig] = None,
    blocked_mask: Optional[np.ndarray] = None,
    cost_multiplier_mask: Optional[np.ndarray] = None,
    vehicle_mode: str = "crew_eva",
    dwell_time_per_stop_s: float = 900.0,
    operational_delay_s: float = 0.0,
    operational_limit_s: Optional[float] = None,
    speed_multiplier: float = 1.0,
) -> RouteResult:
    """
    Plan a continuous, multi-leg connected traverse visiting a user-specified
    sequence of points in order: [P_0, P_1, ..., P_k].
    """
    start_time = time.perf_counter()
    cfg = config if config is not None else PlannerConfig()
    t_cfg = terrain_config if terrain_config is not None else terrain.config

    if len(ordered_points) < 2:
        res = RouteResult(
            profile=cfg.profile,
            start_rc=ordered_points[0] if ordered_points else (0, 0),
            goal_rc=ordered_points[-1] if ordered_points else (0, 0),
            path=[],
            distance_m=0.0,
            cost=float("inf"),
            science_score=0.0,
            visited_waypoint_ids=[],
            num_cells=0,
            num_steps=0,
            is_reachable=False,
            is_budget_feasible=False,
            max_distance_m=cfg.max_distance_m,
            status_message="Multi-stop planning requires at least start and goal endpoints.",
            execution_time_s=time.perf_counter() - start_time,
            vehicle_mode=vehicle_mode,
            speed_multiplier=speed_multiplier,
            legs=[],
        )
        res.timeline = build_mission_timeline(
            res,
            vehicle_mode=vehicle_mode,
            dwell_time_per_stop_s=dwell_time_per_stop_s,
            operational_delay_s=operational_delay_s,
            operational_limit_s=operational_limit_s,
            speed_multiplier=speed_multiplier,
            legs=[],
        )
        return res

    start_rc = ordered_points[0]
    goal_rc = ordered_points[-1]
    combined_path: List[Tuple[int, int]] = []
    total_dist = 0.0
    total_cost = 0.0
    legs: List[LegResult] = []

    for i in range(len(ordered_points) - 1):
        u = ordered_points[i]
        v = ordered_points[i + 1]
        leg = astar_search(
            u,
            v,
            terrain,
            terrain_config=t_cfg,
            blocked_mask=blocked_mask,
            cost_multiplier_mask=cost_multiplier_mask,
        )
        if not leg.is_reachable or math.isinf(leg.cost):
            elapsed = time.perf_counter() - start_time
            res = RouteResult(
                profile=cfg.profile,
                start_rc=start_rc,
                goal_rc=goal_rc,
                path=[],
                distance_m=0.0,
                cost=float("inf"),
                science_score=0.0,
                visited_waypoint_ids=[],
                num_cells=0,
                num_steps=0,
                is_reachable=False,
                is_budget_feasible=False,
                max_distance_m=cfg.max_distance_m,
                status_message=f"Leg {i+1} ({u} to {v}) is impassable under current terrain constraints.",
                execution_time_s=elapsed,
                vehicle_mode=vehicle_mode,
                speed_multiplier=speed_multiplier,
                legs=[],
            )
            res.timeline = build_mission_timeline(
                res,
                vehicle_mode=vehicle_mode,
                dwell_time_per_stop_s=dwell_time_per_stop_s,
                operational_delay_s=operational_delay_s,
                operational_limit_s=operational_limit_s,
                speed_multiplier=speed_multiplier,
                legs=[],
            )
            return res

        legs.append(leg)
        total_dist += leg.distance_m
        total_cost += leg.cost
        if i == 0:
            combined_path.extend(leg.path)
        else:
            combined_path.extend(leg.path[1:])

    elapsed = time.perf_counter() - start_time
    budget_ok = (cfg.max_distance_m is None) or (total_dist <= cfg.max_distance_m)
    visited_ids = list(stop_ids) if stop_ids else []
    total_science = sum(stop_priorities) if stop_priorities else 0.0

    num_legs = len(ordered_points) - 1
    num_intermediate = num_legs - 1
    status = f"Multi-stop traverse ({num_legs} legs, {num_intermediate} intermediate stops) planned successfully."
    if not budget_ok and cfg.max_distance_m is not None:
        status += f" Warning: exceeds distance budget of {cfg.max_distance_m:.1f} m."

    res = RouteResult(
        profile=cfg.profile,
        start_rc=start_rc,
        goal_rc=goal_rc,
        path=combined_path,
        distance_m=total_dist,
        cost=total_cost,
        science_score=total_science,
        visited_waypoint_ids=visited_ids,
        num_cells=len(combined_path),
        num_steps=max(0, len(combined_path) - 1),
        is_reachable=True,
        is_budget_feasible=budget_ok,
        max_distance_m=cfg.max_distance_m,
        status_message=status,
        execution_time_s=elapsed,
        vehicle_mode=vehicle_mode,
        speed_multiplier=speed_multiplier,
        legs=legs,
    )
    res.timeline = build_mission_timeline(
        res,
        vehicle_mode=vehicle_mode,
        dwell_time_per_stop_s=dwell_time_per_stop_s,
        operational_delay_s=operational_delay_s,
        operational_limit_s=operational_limit_s,
        speed_multiplier=speed_multiplier,
        legs=legs,
    )
    if res.timeline and not res.timeline.is_within_limit:
        res.is_budget_feasible = False
        res.status_message += f" Exceeds operational time limit of {res.timeline.operational_limit_s / 3600.0:.1f} h."
    return res


def optimize_stop_order(
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    stops: List[Dict[str, Any]],
    terrain: TerrainGrid,
    terrain_config: Optional[TerrainConfig] = None,
    profile: str = "conservative",
    gamma: float = 1.0,
    vehicle_mode: str = "crew_eva",
    dwell_time_per_stop_s: float = 900.0,
    operational_limit_s: Optional[float] = None,
    speed_multiplier: float = 1.0,
    blocked_mask: Optional[np.ndarray] = None,
    cost_multiplier_mask: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Optimize visitation order of intermediate mission stops.
    - For k <= 7: Uses exact permutation TSP search (globally optimal).
    - For k > 7: Uses deterministic 2-Opt local search starting from nearest-neighbor tour (heuristic approximation).
    - Objective function strictly honors profile:
        * conservative: Minimizes total route ground distance (sum dist_i)
        * balanced: Minimizes total terrain-adjusted traversal effort (sum cost_i)
        * science_first: Minimizes effort while prioritizing science value (early priority score bonus)
    """
    t_cfg = terrain_config if terrain_config is not None else terrain.config
    k = len(stops)

    # Build original point list
    orig_points = [start_rc] + [s["rc"] for s in stops] + [goal_rc]
    stop_ids = [s.get("id", f"stop_{i+1}") for i, s in enumerate(stops)]
    stop_priorities = [float(s.get("priority_score", 50.0)) for s in stops]

    p_cfg = PlannerConfig(profile=profile)

    orig_route = plan_sequential_multistop_route(
        ordered_points=orig_points,
        terrain=terrain,
        stop_ids=stop_ids,
        stop_priorities=stop_priorities,
        config=p_cfg,
        terrain_config=t_cfg,
        blocked_mask=blocked_mask,
        cost_multiplier_mask=cost_multiplier_mask,
        vehicle_mode=vehicle_mode,
        dwell_time_per_stop_s=dwell_time_per_stop_s,
        operational_limit_s=operational_limit_s,
        speed_multiplier=speed_multiplier,
    )

    if k <= 1 or not orig_route.is_reachable:
        return {
            "optimized_stops": stops,
            "original_route": orig_route,
            "optimized_route": orig_route,
            "original_distance_m": round(orig_route.distance_m, 2),
            "optimized_distance_m": round(orig_route.distance_m, 2),
            "distance_saved_m": 0.0,
            "pct_distance_saved": 0.0,
            "cost_saved": 0.0,
            "time_saved_s": 0.0,
            "formatted_time_saved": "0s",
            "permutation_indices": list(range(k)),
            "optimization_method": "trivial_single_or_empty",
            "is_globally_optimal": True,
            "algorithm_disclosure": "Direct route; no intermediate permutation required.",
            "objective_profile": profile,
        }

    # Precompute pairwise cache among all involved points
    all_nodes = [start_rc] + [s["rc"] for s in stops] + [goal_rc]
    cache = compute_pairwise_leg_cache(
        all_nodes,
        terrain,
        terrain_config=t_cfg,
        blocked_mask=blocked_mask,
        cost_multiplier_mask=cost_multiplier_mask,
    )

    def eval_sequence(perm: List[int]) -> Tuple[float, float, float, bool]:
        """
        Evaluate objective score, total distance, and total effort for a candidate sequence.
        Returns (objective_score, distance_m, cost, is_feasible).
        """
        cand_nodes = [start_rc] + [stops[idx]["rc"] for idx in perm] + [goal_rc]
        t_cost = 0.0
        t_dist = 0.0
        for i in range(len(cand_nodes) - 1):
            u = cand_nodes[i]
            v = cand_nodes[i + 1]
            leg = cache.get((u, v))
            if leg is None or not leg.is_reachable or math.isinf(leg.cost):
                return float("inf"), float("inf"), float("inf"), False
            t_cost += leg.cost
            t_dist += leg.distance_m

        if profile == "conservative":
            score = t_dist
        elif profile == "science_first":
            # Early priority bonus: prioritize visiting highest-value science stops early
            early_bonus = sum(
                float(stops[idx].get("priority_score", 50.0)) / (rank + 1.0)
                for rank, idx in enumerate(perm)
            )
            score = t_cost - (gamma * 25.0 * early_bonus)
        else:  # balanced
            score = t_cost

        return score, t_dist, t_cost, True

    if k <= 7:
        # Exact permutation search
        opt_method = "exact_permutation"
        is_globally_optimal = True
        algorithm_disclosure = f"Globally optimal sequence verified via exact permutation search (k = {k} <= 7)."

        best_perm = list(range(k))
        best_score = float("inf")
        best_cost = float("inf")
        best_dist = float("inf")

        for perm in itertools.permutations(range(k)):
            score, dist_m, cost_val, feasible = eval_sequence(list(perm))
            if feasible and score < best_score:
                best_score = score
                best_dist = dist_m
                best_cost = cost_val
                best_perm = list(perm)
    else:
        # Deterministic 2-Opt heuristic with Nearest-Neighbor initial tour
        opt_method = "heuristic_2opt"
        is_globally_optimal = False
        algorithm_disclosure = (
            f"Approximation: 2-Opt local search heuristic applied for {k} targets (N > 7). "
            "Global optimality is not guaranteed."
        )

        # 1. Greedy Nearest-Neighbor Tour Initialization
        unvisited = list(range(k))
        curr_node = start_rc
        initial_perm: List[int] = []

        while unvisited:
            best_cand = unvisited[0]
            best_cand_score = float("inf")
            for c_idx in unvisited:
                c_rc = stops[c_idx]["rc"]
                leg = cache.get((curr_node, c_rc))
                if leg and leg.is_reachable and not math.isinf(leg.cost):
                    metric = leg.distance_m if profile == "conservative" else leg.cost
                    if profile == "science_first":
                        metric /= (float(stops[c_idx].get("priority_score", 50.0)) + 1.0)
                    if metric < best_cand_score:
                        best_cand_score = metric
                        best_cand = c_idx
            initial_perm.append(best_cand)
            unvisited.remove(best_cand)
            curr_node = stops[best_cand]["rc"]

        # 2. 2-Opt Iterative Improvement
        best_perm = list(initial_perm)
        best_score, best_dist, best_cost, _ = eval_sequence(best_perm)

        improved = True
        iteration = 0
        max_iterations = 60

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            for i in range(k - 1):
                for j in range(i + 1, k):
                    # Candidate 2-opt move: reverse subsegment [i..j]
                    cand_perm = best_perm[:i] + best_perm[i : j + 1][::-1] + best_perm[j + 1 :]
                    cand_score, cand_dist, cand_cost, feasible = eval_sequence(cand_perm)
                    if feasible and cand_score < best_score - 1e-4:
                        best_score = cand_score
                        best_dist = cand_dist
                        best_cost = cand_cost
                        best_perm = cand_perm
                        improved = True
                        break
                if improved:
                    break

    optimized_stops = [stops[idx] for idx in best_perm]
    opt_points = [start_rc] + [s["rc"] for s in optimized_stops] + [goal_rc]
    opt_stop_ids = [s.get("id", f"stop_{i+1}") for i, s in enumerate(optimized_stops)]
    opt_stop_priorities = [float(s.get("priority_score", 50.0)) for s in optimized_stops]

    opt_route = plan_sequential_multistop_route(
        ordered_points=opt_points,
        terrain=terrain,
        stop_ids=opt_stop_ids,
        stop_priorities=opt_stop_priorities,
        config=p_cfg,
        terrain_config=t_cfg,
        blocked_mask=blocked_mask,
        cost_multiplier_mask=cost_multiplier_mask,
        vehicle_mode=vehicle_mode,
        dwell_time_per_stop_s=dwell_time_per_stop_s,
        operational_limit_s=operational_limit_s,
        speed_multiplier=speed_multiplier,
    )

    dist_saved = max(0.0, orig_route.distance_m - opt_route.distance_m)
    pct_saved = (dist_saved / orig_route.distance_m * 100.0) if orig_route.distance_m > 0 else 0.0
    cost_saved = max(0.0, orig_route.cost - opt_route.cost)
    time_saved = max(0.0, orig_route.travel_time_s - opt_route.travel_time_s)

    return {
        "optimized_stops": optimized_stops,
        "original_route": orig_route,
        "optimized_route": opt_route,
        "original_distance_m": round(orig_route.distance_m, 2),
        "optimized_distance_m": round(opt_route.distance_m, 2),
        "distance_saved_m": round(dist_saved, 2),
        "pct_distance_saved": round(pct_saved, 1),
        "cost_saved": round(cost_saved, 2),
        "time_saved_s": round(time_saved, 1),
        "formatted_time_saved": format_duration(time_saved),
        "permutation_indices": list(best_perm),
        "optimization_method": opt_method,
        "is_globally_optimal": is_globally_optimal,
        "algorithm_disclosure": algorithm_disclosure,
        "objective_profile": profile,
    }
