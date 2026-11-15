"""
MarsWalk 2.0 / Project Atlas — Dedicated Astronaut EVA Planning & Mobility Engine.

Provides an authoritative human surface excursion planning, mobility, consumable budgeting,
return-to-base feasibility, and emergency contingency decision-support system.

SCIENTIFIC PRINCIPLES & GOVERNANCE:
- Human mobility is modeled via biomechanically grounded terrain effort curves
  (adapted from Minetti et al. 2002 terrestrial slope energy expenditure and
  Apollo lunar surface walk telemetry, Waligora et al. 1975).
- Completely decoupled from robotic rover wheel-terrain / terramechanics models.
- All life-support and consumable values are designated as conceptual research assumptions,
  never certified flight hardware envelopes.
- Rule AGENTS.md: Never call a modeled route operationally safe for astronauts.
"""

from dataclasses import dataclass, field
import enum
import hashlib
import json
import math
import time
from typing import Dict, List, Optional, Set, Tuple, Any, Union
import numpy as np
import rasterio

from marswalk.core.terrain import TerrainGrid, TerrainConfig, calculate_step_distance
from marswalk.core.planner import (
    PlannerConfig,
    RouteResult,
    LegResult,
    ScienceWaypoint,
    TimelineEvent,
    MissionTimeline,
    astar_search,
    compute_pairwise_leg_cache,
    stitch_path_legs,
    format_duration,
)


class EVAMissionState(str, enum.Enum):
    """Authoritative Astronaut EVA operational mission states."""
    NOMINAL = "NOMINAL"
    CAUTION = "CAUTION"
    SAFE_HOLD = "SAFE_HOLD"
    RETURN_TO_BASE = "RETURN_TO_BASE"
    MISSION_ABORTED = "MISSION_ABORTED"
    COMPLETED = "COMPLETED"


class EVAContingencyType(str, enum.Enum):
    """Recognized human surface excursion disruption events."""
    DUST_EVENT = "dust_event"
    COMMS_LOSS = "comms_loss"
    NEWLY_DETECTED_OBSTACLE = "newly_detected_obstacle"
    ROUTE_OBSTRUCTION = "route_obstruction"
    CONSUMABLE_RESERVE_WARNING = "consumable_reserve_warning"


@dataclass
class HumanMobilityConfig:
    """
    Biomechanical and operational assumptions for a suited astronaut traversing Martian terrain on foot.
    """
    nominal_walk_speed_kmh: float = 2.0        # Baseline flat-terrain walk rate (~0.556 m/s, Apollo analogue)
    min_walk_speed_kmh: float = 1.0            # Minimum walking speed under extreme slope/fatigue
    max_walk_speed_kmh: float = 3.5            # Peak unencumbered fast walk speed
    max_walk_slope_deg: float = 20.0           # Configurable impassability barrier for suited EVA
    critical_slope_deg: float = 12.0           # Slope at which steep metabolic penalty accelerates
    slope_penalty_weight: float = 2.5          # Exponent weight on slope effort
    roughness_penalty_weight: float = 1.8      # Surface instability / rockiness effort weight
    uphill_penalty_weight: float = 3.0         # Asymmetric ascending vs descending effort multiplier
    
    # Biometric & mass assumptions
    astronaut_body_mass_kg: float = 80.0       # Standard suited subject mass
    spacesuit_mass_kg: float = 60.0            # Conceptual planetary exploration suit mass
    carried_gear_mass_kg: float = 25.0         # Tools, science containers, sample collection kit
    
    # Operational cadence
    work_rest_ratio: float = 0.85              # Active locomotion duty cycle (85% walk, 15% brief pause)
    fatigue_factor_per_hour: float = 0.03      # 3% velocity derating per hour of continuous locomotion

    @property
    def total_system_mass_kg(self) -> float:
        """Total mass of astronaut + suit + carried gear."""
        return self.astronaut_body_mass_kg + self.spacesuit_mass_kg + self.carried_gear_mass_kg

    @property
    def mass_effort_multiplier(self) -> float:
        """Ratio of total mass with gear to base suited mass."""
        base_mass = self.astronaut_body_mass_kg + self.spacesuit_mass_kg
        return self.total_system_mass_kg / max(1.0, base_mass)


@dataclass
class EVAConsumableBudget:
    """
    Life-support consumable limits and metabolic assumptions for conceptual EVA sizing.
    """
    max_duration_s: float = 28800.0            # 8.0 hours nominal sortie ceiling
    nominal_metabolic_kcal_hr: float = 320.0   # Apollo Waligora baseline at 2.0 km/h flat
    nominal_o2_liters_hr: float = 50.0         # Primary PLSS oxygen consumption at nominal burn
    primary_o2_capacity_liters: float = 600.0  # Total usable oxygen volume
    emergency_o2_reserve_liters: float = 120.0 # 20% mandatory emergency walkback reserve
    suit_battery_capacity_wh: float = 1800.0   # Suit electronics, thermal loops & fan power
    base_suit_power_w: float = 120.0           # Continuous electrical draw
    safety_margin_pct: float = 20.0            # Standard 20% consumable contingency reserve
    apollo_walkback_limit_m: float = 4000.0    # 4.0 km Apollo rule of thumb walking limit from base


@dataclass
class EVAConsumableUsage:
    """Calculated consumable expenditure for an EVA traverse or leg."""
    active_walk_time_s: float
    science_dwell_time_s: float
    total_time_s: float
    metabolic_energy_kcal: float
    oxygen_consumed_liters: float
    battery_energy_wh: float
    remaining_o2_liters: float
    remaining_battery_wh: float
    o2_reserve_margin_pct: float
    is_consumable_feasible: bool
    return_safe_margin_s: float
    walkback_limit_exceeded: bool


def calculate_human_step_cost(
    u: Tuple[int, int],
    v: Tuple[int, int],
    terrain: TerrainGrid,
    config: Optional[HumanMobilityConfig] = None,
    step_dist: Optional[float] = None,
) -> float:
    """
    Calculate the directed traversal effort for a suited human walking from cell u to cell v.

    Mathematical Formulation:
    C_human(u -> v) = d(u, v) * [ 1.0 + P_slope + P_rough + P_uphill ] * M_gear

    Where:
    - d(u, v) is the ground distance in meters.
    - theta_uv is the maximum of destination cell slope and directional gradient.
    - If theta_uv >= max_walk_slope_deg: C = infinity (impassable cliff / slide hazard).
    - P_slope = slope_penalty_weight * (theta_uv / critical_slope_deg)^2
    - P_rough = roughness_penalty_weight * (roughness_m[v] / 0.5)
    - P_uphill = uphill_penalty_weight * max(0.0, dz / d(u, v))
    - M_gear = total_system_mass / base_suited_mass
    """
    cfg = config if config is not None else HumanMobilityConfig()
    r1, c1 = u
    r2, c2 = v
    H, W = terrain.shape

    if not (0 <= r1 < H and 0 <= c1 < W and 0 <= r2 < H and 0 <= c2 < W):
        return float("inf")
    if terrain.invalid_mask[r1, c1] or terrain.invalid_mask[r2, c2]:
        return float("inf")
    if r1 == r2 and c1 == c2:
        return 0.0

    if step_dist is not None:
        dist = step_dist
    else:
        dist = calculate_step_distance(u, v, terrain.dx_ground_m, terrain.dy_ground_m)
    if dist <= 0:
        return float("inf")

    z1 = float(terrain.elevation[r1, c1])
    z2 = float(terrain.elevation[r2, c2])
    theta_dest = float(terrain.slope_deg[r2, c2])

    # Guard against NaN, infinite, or corrupted DEM values (DEFECT-13-01)
    if math.isnan(z1) or math.isnan(z2) or math.isinf(z1) or math.isinf(z2):
        return float("inf")
    if math.isnan(theta_dest) or math.isinf(theta_dest):
        return float("inf")

    dz = z2 - z1
    theta_step = math.degrees(math.atan(abs(dz) / dist))
    theta_uv = max(theta_dest, theta_step)

    # Human slope cutoff (default 20.0°, configurable)
    if math.isnan(theta_uv) or theta_uv >= cfg.max_walk_slope_deg:
        return float("inf")

    # Quadratic slope penalty
    p_slope = cfg.slope_penalty_weight * ((theta_uv / max(1.0, cfg.critical_slope_deg)) ** 2)

    # Surface roughness penalty (loose rock, unstable regolith)
    dest_rough = float(terrain.roughness_m[r2, c2])
    if math.isnan(dest_rough) or dest_rough < 0:
        dest_rough = 0.0
    p_rough = cfg.roughness_penalty_weight * (dest_rough / 0.5)

    # Asymmetric uphill penalty
    p_uphill = cfg.uphill_penalty_weight * max(0.0, dz / dist)

    bracket = 1.0 + p_slope + p_rough + p_uphill
    return dist * bracket * cfg.mass_effort_multiplier


def calculate_human_walk_time_and_metabolics(
    effort_cost: float,
    ground_distance_m: float,
    mobility_cfg: Optional[HumanMobilityConfig] = None,
    budget_cfg: Optional[EVAConsumableBudget] = None,
    dwell_time_s: float = 0.0,
) -> Tuple[float, float, float, float, float]:
    """
    Compute walking duration, metabolic burn (kcal), oxygen consumption (L),
    and battery usage (Wh) for a human traverse based on terrain effort.

    Returns:
    (active_walk_time_s, total_time_s, metabolic_kcal, o2_liters, battery_wh)
    """
    m_cfg = mobility_cfg if mobility_cfg is not None else HumanMobilityConfig()
    b_cfg = budget_cfg if budget_cfg is not None else EVAConsumableBudget()

    if effort_cost <= 0 or math.isinf(effort_cost) or ground_distance_m <= 0 or math.isnan(effort_cost) or math.isnan(ground_distance_m):
        return 0.0, dwell_time_s, 0.0, 0.0, 0.0

    # Flat nominal speed in m/s (guarded against non-positive values)
    nominal_kmh = max(0.1, float(m_cfg.nominal_walk_speed_kmh))
    min_kmh = max(0.05, float(m_cfg.min_walk_speed_kmh))
    v_flat_ms = (nominal_kmh * 1000.0) / 3600.0
    v_min_ms = (min_kmh * 1000.0) / 3600.0

    # Terrain effort factor (ratio of flat-effort distance to actual distance)
    terrain_impedance = max(1.0, effort_cost / max(1.0, ground_distance_m))
    
    # Effective speed is slowed down by terrain impedance and work/rest ratio
    cadence = max(0.1, min(1.0, float(m_cfg.work_rest_ratio)))
    v_effective_ms = max(
        v_min_ms,
        (v_flat_ms / terrain_impedance) * cadence
    )
    walk_time_s = ground_distance_m / v_effective_ms
    total_time_s = walk_time_s + dwell_time_s

    # Dynamic metabolic power: base rate scaled by terrain impedance & carried mass
    walk_hrs = walk_time_s / 3600.0
    dwell_hrs = dwell_time_s / 3600.0

    active_metabolic_rate = b_cfg.nominal_metabolic_kcal_hr * (1.0 + 0.4 * (terrain_impedance - 1.0)) * m_cfg.mass_effort_multiplier
    dwell_metabolic_rate = 180.0  # Lower metabolic rate during stationary science observation / sampling

    metabolic_kcal = (walk_hrs * active_metabolic_rate) + (dwell_hrs * dwell_metabolic_rate)

    # Oxygen volume is physiologically linked to metabolic energy burn (~0.156 L O2 per kcal)
    # Calibrated to 50 L/hr at 320 kcal/hr nominal (50 / 320 = 0.15625)
    o2_conversion_ratio = b_cfg.nominal_o2_liters_hr / b_cfg.nominal_metabolic_kcal_hr
    o2_liters = metabolic_kcal * o2_conversion_ratio

    # Battery consumption (suit base electrical load)
    total_hrs = total_time_s / 3600.0
    battery_wh = total_hrs * b_cfg.base_suit_power_w

    return round(walk_time_s, 1), round(total_time_s, 1), round(metabolic_kcal, 1), round(o2_liters, 1), round(battery_wh, 1)


def evaluate_eva_consumable_budget(
    active_walk_s: float,
    dwell_s: float,
    metabolic_kcal: float,
    o2_liters: float,
    battery_wh: float,
    budget: Optional[EVAConsumableBudget] = None,
    ground_dist_m: float = 0.0,
) -> EVAConsumableUsage:
    """
    Evaluate consumable safety margins and walkback feasibility against configured limits.
    """
    b = budget if budget is not None else EVAConsumableBudget()
    total_time_s = active_walk_s + dwell_s

    remaining_o2 = max(0.0, b.primary_o2_capacity_liters - o2_liters)
    remaining_battery = max(0.0, b.suit_battery_capacity_wh - battery_wh)
    
    o2_reserve_pct = (remaining_o2 / b.primary_o2_capacity_liters) * 100.0 if b.primary_o2_capacity_liters > 0 else 0.0
    return_safe_margin_s = b.max_duration_s - total_time_s

    walkback_exceeded = ground_dist_m > b.apollo_walkback_limit_m
    is_feasible = (
        b.primary_o2_capacity_liters > 0.0
        and o2_liters < b.primary_o2_capacity_liters
        and total_time_s <= b.max_duration_s
        and remaining_o2 >= b.emergency_o2_reserve_liters
        and remaining_o2 > 0.0
        and remaining_battery > 0.0
    )

    return EVAConsumableUsage(
        active_walk_time_s=round(active_walk_s, 1),
        science_dwell_time_s=round(dwell_s, 1),
        total_time_s=round(total_time_s, 1),
        metabolic_energy_kcal=round(metabolic_kcal, 1),
        oxygen_consumed_liters=round(o2_liters, 1),
        battery_energy_wh=round(battery_wh, 1),
        remaining_o2_liters=round(remaining_o2, 1),
        remaining_battery_wh=round(remaining_battery, 1),
        o2_reserve_margin_pct=round(o2_reserve_pct, 1),
        is_consumable_feasible=is_feasible,
        return_safe_margin_s=round(return_safe_margin_s, 1),
        walkback_limit_exceeded=walkback_exceeded,
    )


def _is_blocked(pt: Tuple[int, int], mask: Any) -> bool:
    if mask is None:
        return False
    if isinstance(mask, (set, list, tuple)):
        return pt in mask
    return bool(mask[pt[0], pt[1]])


def plan_human_eva_leg(
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    terrain: TerrainGrid,
    mobility_cfg: Optional[HumanMobilityConfig] = None,
    blocked_mask: Optional[Union[np.ndarray, Set[Tuple[int, int]], List[Tuple[int, int]]]] = None,
    cost_multiplier_mask: Optional[np.ndarray] = None,
) -> LegResult:
    """
    Point-to-point human EVA shortest path search using A* with the Human Mobility Cost Model.
    """
    m_cfg = mobility_cfg if mobility_cfg is not None else HumanMobilityConfig()
    H, W = terrain.shape

    # Validate endpoints
    for pt, name in [(start_rc, "Start"), (goal_rc, "Goal")]:
        if not (0 <= pt[0] < H and 0 <= pt[1] < W):
            return LegResult(start_rc, goal_rc, [], 0.0, float("inf"), False)
        if terrain.invalid_mask[pt[0], pt[1]]:
            return LegResult(start_rc, goal_rc, [], 0.0, float("inf"), False)
        if _is_blocked(pt, blocked_mask):
            return LegResult(start_rc, goal_rc, [], 0.0, float("inf"), False)
        # Check starting / goal slope against astronaut cutoff
        if float(terrain.slope_deg[pt[0], pt[1]]) >= m_cfg.max_walk_slope_deg:
            return LegResult(start_rc, goal_rc, [], 0.0, float("inf"), False)

    if start_rc == goal_rc:
        return LegResult(start_rc, goal_rc, [start_rc], 0.0, 0.0, True)

    dx = terrain.dx_ground_m
    dy = terrain.dy_ground_m
    d_diag = math.sqrt(dx**2 + dy**2)

    neighbor_steps = [
        (-1, 0, dy), (1, 0, dy), (0, -1, dx), (0, 1, dx),
        (-1, -1, d_diag), (-1, 1, d_diag), (1, -1, d_diag), (1, 1, d_diag)
    ]

    import heapq
    # Use octile distance heuristic
    def octile_heuristic(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        dr = abs(p1[0] - p2[0])
        dc = abs(p1[1] - p2[1])
        return (dx * abs(dr - dc) + d_diag * min(dr, dc)) * m_cfg.mass_effort_multiplier

    h_start = octile_heuristic(start_rc, goal_rc)
    pq: List[Tuple[float, float, Tuple[int, int]]] = [(h_start, 0.0, start_rc)]
    g_score: Dict[Tuple[int, int], float] = {start_rc: 0.0}
    dist_so_far: Dict[Tuple[int, int], float] = {start_rc: 0.0}
    parent: Dict[Tuple[int, int], Tuple[int, int]] = {}

    while pq:
        f, g, u = heapq.heappop(pq)
        if u == goal_rc:
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
        for dr, dc, step_d in neighbor_steps:
            nr = ur + dr
            nc = uc + dc
            if not (0 <= nr < H and 0 <= nc < W):
                continue
            if terrain.invalid_mask[nr, nc]:
                continue
            if _is_blocked((nr, nc), blocked_mask):
                continue

            v = (nr, nc)
            edge_c = calculate_human_step_cost(u, v, terrain, config=m_cfg, step_dist=step_d)
            if math.isinf(edge_c):
                continue

            if cost_multiplier_mask is not None:
                mult = float(cost_multiplier_mask[nr, nc])
                if mult > 1.0:
                    edge_c *= mult

            tentative_g = g + edge_c
            if tentative_g < g_score.get(v, float("inf")):
                g_score[v] = tentative_g
                dist_so_far[v] = dist_so_far[u] + step_d
                parent[v] = u
                h_v = octile_heuristic(v, goal_rc)
                heapq.heappush(pq, (tentative_g + h_v, tentative_g, v))

    return LegResult(start_rc, goal_rc, [], 0.0, float("inf"), False)


def plan_three_astronaut_eva_routes(
    base_rc: Tuple[int, int],
    science_stops: List[Dict[str, Any]],
    terrain: TerrainGrid,
    mobility_config: Optional[HumanMobilityConfig] = None,
    consumable_budget: Optional[EVAConsumableBudget] = None,
    blocked_mask: Optional[np.ndarray] = None,
    cost_multiplier_mask: Optional[np.ndarray] = None,
    dwell_time_per_target_s: float = 900.0,
    require_return_to_base: bool = True,
) -> Dict[str, Any]:
    """
    Generate three distinct human EVA traverse options:
    1. Conservative Route: Strict slope ceiling (<=15°), high safety reserve, lowest terrain strain.
    2. Science-Priority Route: Intercepts all chosen science targets, tolerates slopes up to 20°, balances dwell time.
    3. Time-Efficient Route: Direct path minimizing duration while respecting human slope bounds.

    Returns structured comparison dictionary containing complete metrics, consumables,
    return-to-base validations, and operational disclaimers.
    """
    m_base = mobility_config if mobility_config is not None else HumanMobilityConfig()
    b_cfg = consumable_budget if consumable_budget is not None else EVAConsumableBudget()

    # Define profile variants
    # Conservative: reduced max slope, higher penalty on rough terrain
    m_conservative = HumanMobilityConfig(
        nominal_walk_speed_kmh=min(2.0, m_base.nominal_walk_speed_kmh),
        max_walk_slope_deg=min(15.0, m_base.max_walk_slope_deg),
        critical_slope_deg=10.0,
        slope_penalty_weight=m_base.slope_penalty_weight * 1.5,
        roughness_penalty_weight=m_base.roughness_penalty_weight * 1.4,
        carried_gear_mass_kg=m_base.carried_gear_mass_kg,
    )
    # Science-Priority: accepts up to 20° slope to reach high-value science outcrops
    m_science = HumanMobilityConfig(
        nominal_walk_speed_kmh=m_base.nominal_walk_speed_kmh,
        max_walk_slope_deg=max(18.0, m_base.max_walk_slope_deg),
        critical_slope_deg=12.0,
        slope_penalty_weight=m_base.slope_penalty_weight,
        roughness_penalty_weight=m_base.roughness_penalty_weight,
        carried_gear_mass_kg=m_base.carried_gear_mass_kg,
    )
    # Time-Efficient: slightly faster pace, standard slope cutoff
    m_time = HumanMobilityConfig(
        nominal_walk_speed_kmh=max(2.2, m_base.nominal_walk_speed_kmh),
        max_walk_slope_deg=m_base.max_walk_slope_deg,
        critical_slope_deg=12.0,
        slope_penalty_weight=m_base.slope_penalty_weight * 0.9,
        roughness_penalty_weight=m_base.roughness_penalty_weight * 0.9,
        carried_gear_mass_kg=m_base.carried_gear_mass_kg,
    )

    profiles = [
        ("conservative", "Conservative Route", m_conservative, "Prioritizes minimum physical strain and gentlest terrain slopes (<=15°)."),
        ("science_first", "Science-Priority Route", m_science, "Maximizes scientific target coverage and observation dwell time."),
        ("time_efficient", "Time-Efficient Route", m_time, "Minimizes mission duration and optimizes transit pace."),
    ]

    routes_out = {}

    for p_key, p_name, p_mob, p_desc in profiles:
        # Determine sequence of waypoints
        # Outbound: Base -> Stop 1 -> Stop 2 -> ... -> Final Stop
        # Inbound: Final Stop -> Base (if require_return_to_base)
        outbound_nodes: List[Tuple[int, int]] = [base_rc]
        stop_meta = []
        for s in science_stops:
            s_rc = (int(s["row"]), int(s["col"]))
            outbound_nodes.append(s_rc)
            stop_meta.append(s)

        outbound_path: List[Tuple[int, int]] = []
        outbound_dist_m = 0.0
        outbound_cost = 0.0
        outbound_reachable = True
        legs_data = []

        # 1. Compute Outbound Legs (Base -> Stop 1 -> ... -> Stop N)
        for i in range(len(outbound_nodes) - 1):
            u = outbound_nodes[i]
            v = outbound_nodes[i + 1]
            leg = plan_human_eva_leg(
                u, v, terrain,
                mobility_cfg=p_mob,
                blocked_mask=blocked_mask,
                cost_multiplier_mask=cost_multiplier_mask,
            )
            if not leg.is_reachable:
                outbound_reachable = False
                break

            if i == 0:
                outbound_path.extend(leg.path)
            else:
                outbound_path.extend(leg.path[1:])
            outbound_dist_m += leg.distance_m
            outbound_cost += leg.cost
            legs_data.append({
                "leg_index": i + 1,
                "from_rc": list(u),
                "to_rc": list(v),
                "distance_m": round(leg.distance_m, 1),
                "effort_cost": round(leg.cost, 1),
                "is_return_leg": False,
            })

        # 2. Compute Return Leg (Final Stop -> Base)
        return_path: List[Tuple[int, int]] = []
        return_dist_m = 0.0
        return_cost = 0.0
        return_leg_feasible = True

        if outbound_reachable and require_return_to_base and len(outbound_nodes) > 1:
            ret_u = outbound_nodes[-1]
            ret_v = base_rc
            ret_leg = plan_human_eva_leg(
                ret_u, ret_v, terrain,
                mobility_cfg=p_mob,
                blocked_mask=blocked_mask,
                cost_multiplier_mask=cost_multiplier_mask,
            )
            if not ret_leg.is_reachable:
                return_leg_feasible = False
            else:
                return_path = list(ret_leg.path)
                return_dist_m = ret_leg.distance_m
                return_cost = ret_leg.cost
                legs_data.append({
                    "leg_index": len(legs_data) + 1,
                    "from_rc": list(ret_u),
                    "to_rc": list(ret_v),
                    "distance_m": round(ret_leg.distance_m, 1),
                    "effort_cost": round(ret_leg.cost, 1),
                    "is_return_leg": True,
                })

        # Combined path
        total_path: List[Tuple[int, int]] = []
        if outbound_path:
            total_path.extend(outbound_path)
        if return_path:
            total_path.extend(return_path[1:] if total_path else return_path)

        total_dist_m = outbound_dist_m + return_dist_m
        total_cost = outbound_cost + return_cost
        is_reachable = bool(outbound_reachable and (return_leg_feasible or not require_return_to_base))

        # Science dwell time: dwell_time_per_target_s at intermediate science stops
        total_dwell_s = len(science_stops) * dwell_time_per_target_s

        if is_reachable and total_dist_m > 0:
            # Outbound transit metrics
            out_walk_s, _, out_kcal, out_o2_l, out_bat_wh = calculate_human_walk_time_and_metabolics(
                effort_cost=outbound_cost,
                ground_distance_m=outbound_dist_m,
                mobility_cfg=p_mob,
                budget_cfg=b_cfg,
                dwell_time_s=0.0,
            )
            # Dwell metrics (stationary research / sampling at 180 kcal/hr)
            dwell_hrs = total_dwell_s / 3600.0
            dwell_kcal = dwell_hrs * 180.0
            o2_ratio = b_cfg.nominal_o2_liters_hr / b_cfg.nominal_metabolic_kcal_hr
            dwell_o2_l = dwell_kcal * o2_ratio
            dwell_bat_wh = dwell_hrs * b_cfg.base_suit_power_w

            # Return transit metrics
            ret_walk_s, _, ret_kcal, ret_o2_l, ret_bat_wh = calculate_human_walk_time_and_metabolics(
                effort_cost=return_cost,
                ground_distance_m=return_dist_m,
                mobility_cfg=p_mob,
                budget_cfg=b_cfg,
                dwell_time_s=0.0,
            )

            tot_walk_s = out_walk_s + ret_walk_s
            tot_time_s = tot_walk_s + total_dwell_s
            tot_kcal = out_kcal + dwell_kcal + ret_kcal
            tot_o2_l = out_o2_l + dwell_o2_l + ret_o2_l
            tot_bat_wh = out_bat_wh + dwell_bat_wh + ret_bat_wh

            consumable_eval = evaluate_eva_consumable_budget(
                active_walk_s=tot_walk_s,
                dwell_s=total_dwell_s,
                metabolic_kcal=tot_kcal,
                o2_liters=tot_o2_l,
                battery_wh=tot_bat_wh,
                budget=b_cfg,
                ground_dist_m=total_dist_m,
            )

            # Max & average slope along path
            slopes = [float(terrain.slope_deg[r, c]) for r, c in total_path]
            max_slope = max(slopes) if slopes else 0.0
            avg_slope = sum(slopes) / len(slopes) if slopes else 0.0
        else:
            out_walk_s, ret_walk_s = 0.0, 0.0
            out_kcal, dwell_kcal, ret_kcal = 0.0, 0.0, 0.0
            out_o2_l, dwell_o2_l, ret_o2_l = 0.0, 0.0, 0.0
            tot_bat_wh = 0.0
            consumable_eval = evaluate_eva_consumable_budget(
                active_walk_s=0.0, dwell_s=0.0, metabolic_kcal=0.0, o2_liters=0.0,
                battery_wh=0.0, budget=b_cfg, ground_dist_m=0.0
            )
            max_slope = 0.0
            avg_slope = 0.0

        # Return-to-base validation
        return_feasible = is_reachable and consumable_eval.is_consumable_feasible
        warnings = []
        if not outbound_reachable:
            warnings.append("Outbound route is impassable due to slope limit or terrain barrier.")
        elif require_return_to_base and not return_leg_feasible:
            warnings.append("CRITICAL: Outbound traverse reaches science targets, but return-to-base path is IMPASSABLE. Excursion is UNSAFE.")
        elif not consumable_eval.is_consumable_feasible:
            warnings.append("Consumable envelope exceeded: projected oxygen or mission duration exceeds safety threshold.")
        if consumable_eval.walkback_limit_exceeded:
            warnings.append(f"Advisory: Total traverse length ({total_dist_m:.0f}m) exceeds the {b_cfg.apollo_walkback_limit_m:.0f}m Apollo walking return threshold.")

        routes_out[p_key] = {
            "profile_key": p_key,
            "profile_name": p_name,
            "description": p_desc,
            "is_reachable": is_reachable,
            "is_feasible": return_feasible,
            "return_leg_feasible": return_leg_feasible,
            "total_distance_m": round(total_dist_m, 1),
            "outbound_distance_m": round(outbound_dist_m, 1),
            "return_distance_m": round(return_dist_m, 1),
            "terrain_effort_cost": round(total_cost, 1),
            "active_walk_time_s": consumable_eval.active_walk_time_s,
            "outbound_walk_time_s": round(out_walk_s, 1),
            "return_walk_time_s": round(ret_walk_s, 1),
            "science_dwell_time_s": consumable_eval.science_dwell_time_s,
            "total_mission_time_s": consumable_eval.total_time_s,
            "formatted_duration": format_duration(consumable_eval.total_time_s),
            "max_slope_deg": round(max_slope, 1),
            "avg_slope_deg": round(avg_slope, 1),
            "science_targets_count": len(science_stops),
            "consumables": {
                "metabolic_burn_kcal": consumable_eval.metabolic_energy_kcal,
                "oxygen_consumed_liters": consumable_eval.oxygen_consumed_liters,
                "battery_energy_wh": consumable_eval.battery_energy_wh,
                "remaining_o2_liters": consumable_eval.remaining_o2_liters,
                "remaining_battery_wh": consumable_eval.remaining_battery_wh,
                "o2_reserve_margin_pct": consumable_eval.o2_reserve_margin_pct,
                "walkback_limit_exceeded": consumable_eval.walkback_limit_exceeded,
                "apollo_walkback_limit_m": b_cfg.apollo_walkback_limit_m,
            },
            "consumable_breakdown": {
                "outbound_o2_liters": round(out_o2_l, 1),
                "dwell_o2_liters": round(dwell_o2_l, 1),
                "return_o2_liters": round(ret_o2_l, 1),
                "total_o2_liters": round(consumable_eval.oxygen_consumed_liters, 1),
                "outbound_metabolic_kcal": round(out_kcal, 1),
                "dwell_metabolic_kcal": round(dwell_kcal, 1),
                "return_metabolic_kcal": round(ret_kcal, 1),
                "total_metabolic_kcal": round(consumable_eval.metabolic_energy_kcal, 1),
                "battery_wh": round(consumable_eval.battery_energy_wh, 1),
            },
            "return_to_base_included": require_return_to_base,
            "path_rc": [list(rc) for rc in total_path],
            "outbound_path_rc": [list(rc) for rc in outbound_path],
            "return_path_rc": [list(rc) for rc in return_path],
            "legs": legs_data,
            "warnings": warnings,
        }

    return {
        "schema_version": "2.0.0",
        "mission_mode": "astronaut_eva",
        "base_location_rc": list(base_rc),
        "science_stops_count": len(science_stops),
        "return_to_base_required": require_return_to_base,
        "routes": routes_out,
        "operational_safety_disclaimer": (
            "Conceptual Mars EVA planning prototype. Not certified for astronaut operations, "
            "spacesuit design, life-support sizing or real mission safety decisions."
        ),
        "assumptions": {
            "nominal_walk_speed_kmh": m_base.nominal_walk_speed_kmh,
            "suit_total_mass_kg": m_base.total_system_mass_kg,
            "carried_gear_mass_kg": m_base.carried_gear_mass_kg,
            "o2_capacity_liters": b_cfg.primary_o2_capacity_liters,
            "emergency_reserve_liters": b_cfg.emergency_o2_reserve_liters,
            "max_duration_hours": round(b_cfg.max_duration_s / 3600.0, 1),
        },
    }


def execute_eva_contingency_workflow(
    current_astronaut_rc: Tuple[int, int],
    base_rc: Tuple[int, int],
    contingency_type: EVAContingencyType,
    terrain: TerrainGrid,
    mobility_config: Optional[HumanMobilityConfig] = None,
    consumable_budget: Optional[EVAConsumableBudget] = None,
    blocked_mask: Optional[np.ndarray] = None,
    custom_message: Optional[str] = None,
    current_state: Union[EVAMissionState, str] = EVAMissionState.NOMINAL,
    dust_optical_depth: Optional[float] = None,
    remaining_o2_liters: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Dedicated Human EVA Contingency Workflow.

    Evaluates disruption and determines authoritative state transitions:
    - Dust event -> CAUTION (moderate dust tau < 3.0) or RETURN_TO_BASE (severe dust storm tau >= 3.0).
    - Comms loss -> CAUTION with relay loss alert and visor dead-reckoning.
    - Obstacle / route obstruction -> Immediate emergency return route recomputation (RETURN_TO_BASE).
    - Low consumable reserve (< 20%) -> Immediate abort sequence (RETURN_TO_BASE).
    - Unrecoverable blocked return with exhausted O2 -> MISSION_ABORTED.
    - Safe arrival at habitat airlock -> COMPLETED.

    Calculates emergency return route to base/habitat from current coordinates.
    """
    m_cfg = mobility_config if mobility_config is not None else HumanMobilityConfig()
    b_cfg = consumable_budget if consumable_budget is not None else EVAConsumableBudget()

    prev_state_str = getattr(current_state, "value", str(current_state)).upper()
    H, W = terrain.shape

    # Grid bounds check
    for pt, name in [(current_astronaut_rc, "Current Astronaut Position"), (base_rc, "Base Location")]:
        if not (0 <= pt[0] < H and 0 <= pt[1] < W):
            return {
                "schema_version": "2.0.0",
                "contingency_type": getattr(contingency_type, "value", str(contingency_type)),
                "mission_state": EVAMissionState.SAFE_HOLD.value,
                "previous_state": prev_state_str,
                "requires_immediate_return": True,
                "advisory": f"CRITICAL: {name} ({pt[0]}, {pt[1]}) is outside terrain raster boundary ({H}x{W}).",
                "user_description": custom_message or "",
                "current_position_rc": list(current_astronaut_rc),
                "base_location_rc": list(base_rc),
                "emergency_return_route": {
                    "is_reachable": False,
                    "path_rc": [],
                    "metrics": None,
                },
                "radiation_status": "UNKNOWN (In-situ surface sensor telemetry unavailable in this sector)",
                "operational_safety_disclaimer": (
                    "Conceptual Mars EVA planning prototype. Not certified for astronaut operations, "
                    "spacesuit design, life-support sizing or real mission safety decisions."
                ),
            }

    # Evaluate lifecycle state and advisory
    state = EVAMissionState.NOMINAL
    advisory = ""
    requires_immediate_return = False

    # Check arrival at base
    if current_astronaut_rc == base_rc:
        state = EVAMissionState.COMPLETED
        advisory = "Astronaut has arrived safely at habitat base airlock. Ingress completed."
    elif remaining_o2_liters is not None and remaining_o2_liters <= 0.0:
        state = EVAMissionState.MISSION_ABORTED
        advisory = "CRITICAL: Consumable life-support depleted before reaching base. Excursion aborted."
    elif contingency_type == EVAContingencyType.DUST_EVENT:
        tau = float(dust_optical_depth) if dust_optical_depth is not None else 1.5
        if tau >= 3.0:
            state = EVAMissionState.RETURN_TO_BASE
            requires_immediate_return = True
            advisory = f"Severe regional dust storm detected (optical depth tau = {tau:.1f}). Solar insolation collapsed and surface visibility zero. Immediate abort to base initiated."
        else:
            state = EVAMissionState.CAUTION
            advisory = f"Moderate dust opacity event detected (optical depth tau = {tau:.1f}). Atmospheric contrast degraded. Visor contrast enhancement active."
    elif contingency_type == EVAContingencyType.COMMS_LOSS:
        state = EVAMissionState.CAUTION
        advisory = "Primary RF line-of-sight to habitat base station disrupted. Autonomous visor inertial navigation active."
    elif contingency_type in (EVAContingencyType.NEWLY_DETECTED_OBSTACLE, EVAContingencyType.ROUTE_OBSTRUCTION):
        state = EVAMissionState.RETURN_TO_BASE
        requires_immediate_return = True
        advisory = "Traverse corridor obstructed by newly identified terrain hazard. Immediate return-to-base sequence initiated."
    elif contingency_type == EVAContingencyType.CONSUMABLE_RESERVE_WARNING:
        state = EVAMissionState.RETURN_TO_BASE
        requires_immediate_return = True
        advisory = "Consumable life-support reserve margin below 20% emergency threshold. Abort excursion and proceed to base."

    # Compute emergency return path to base
    return_leg = plan_human_eva_leg(
        current_astronaut_rc,
        base_rc,
        terrain,
        mobility_cfg=m_cfg,
        blocked_mask=blocked_mask,
    )

    emergency_metrics = None
    if return_leg.is_reachable:
        walk_s, tot_s, kcal, o2_l, bat_wh = calculate_human_walk_time_and_metabolics(
            effort_cost=return_leg.cost,
            ground_distance_m=return_leg.distance_m,
            mobility_cfg=m_cfg,
            budget_cfg=b_cfg,
            dwell_time_s=0.0,
        )
        emergency_metrics = {
            "return_distance_m": round(return_leg.distance_m, 1),
            "estimated_return_time_s": walk_s,
            "formatted_return_time": format_duration(walk_s),
            "emergency_metabolic_kcal": kcal,
            "emergency_o2_liters": o2_l,
            "is_return_feasible": True,
        }
    else:
        if remaining_o2_liters is not None and remaining_o2_liters <= 0.0:
            state = EVAMissionState.MISSION_ABORTED
            advisory += " CRITICAL: Direct return corridor blocked AND life-support consumables exhausted. Mission aborted."
        elif current_astronaut_rc != base_rc:
            state = EVAMissionState.SAFE_HOLD
            advisory += " CRITICAL: Direct return corridor blocked. Astronaut must maintain SAFE HOLD while secondary escape route is calculated."
        emergency_metrics = {
            "return_distance_m": 0.0,
            "estimated_return_time_s": 0.0,
            "formatted_return_time": "IMPASSABLE",
            "emergency_metabolic_kcal": 0.0,
            "emergency_o2_liters": 0.0,
            "is_return_feasible": False,
        }

    return {
        "schema_version": "2.0.0",
        "contingency_type": getattr(contingency_type, "value", str(contingency_type)),
        "mission_state": state.value,
        "previous_state": prev_state_str,
        "requires_immediate_return": requires_immediate_return,
        "advisory": advisory,
        "user_description": custom_message or "",
        "current_position_rc": list(current_astronaut_rc),
        "base_location_rc": list(base_rc),
        "emergency_return_route": {
            "is_reachable": return_leg.is_reachable,
            "path_rc": [list(rc) for rc in return_leg.path],
            "metrics": emergency_metrics,
        },
        "radiation_status": "UNKNOWN (In-situ surface sensor telemetry unavailable in this sector)",
        "operational_safety_disclaimer": (
            "Conceptual Mars EVA planning prototype. Not certified for astronaut operations, "
            "spacesuit design, life-support sizing or real mission safety decisions."
        ),
    }
