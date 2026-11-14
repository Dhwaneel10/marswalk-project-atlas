"""
MarsWalk 2.0 — Autonomous Science-Tour Optimizer & Mission Alternative Engine.

Implements bounded beam search with pairwise directed A* leg caching to answer:
"Given a departure, destination, limited operational budget, and candidate scientific
targets, which mission should we fly, and what alternatives should we consider?"

Provides:
  1. Multi-objective champion synthesis (Science Priority, Time Efficiency, Balanced Trade-off).
  2. 2D/3D Pareto frontier extraction (non-dominated candidate tours).
  3. Operational budget enforcement (crew EVA life-support & robotic rover drive windows).
  4. Real terrain slope effort, dwell times, and operational delay modeling.
  5. Authoritative verification: all returned sorties are evaluated through the Python A* engine.
"""

from dataclasses import dataclass, field
import enum
import math
import time
from typing import Dict, List, Optional, Set, Tuple, Any, Union
import numpy as np
import rasterio

from marswalk.core.terrain import TerrainConfig, TerrainGrid, get_profile_terrain_config
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    RouteResult,
    LegResult,
    MissionTimeline,
    VehicleMode,
    calculate_traverse_time,
    format_duration,
    compute_pairwise_leg_cache,
    stitch_path_legs,
    plan_sequential_multistop_route,
    build_mission_timeline,
    ENGINEERING_ASSUMPTIONS,
)


class SortieObjective(str, enum.Enum):
    SCIENCE_PRIORITY = "science_priority"
    TIME_EFFICIENCY = "time_efficiency"
    BALANCED = "balanced"
    DIRECT_BASELINE = "direct_baseline"
    PARETO_ALTERNATIVE = "pareto_alternative"


@dataclass
class SortieCandidate:
    """
    Evaluated scientific exploration sortie candidate.
    """
    id: str
    objective: str
    title: str
    tradeoff_rationale: str
    stop_ids: List[str]
    stop_names: List[str]
    num_stops: int
    path_rc: List[Tuple[int, int]]
    distance_m: float
    terrain_cost: float
    travel_time_s: float
    dwell_time_s: float
    hold_delay_s: float
    total_mission_time_s: float
    operational_limit_s: Optional[float]
    time_margin_s: Optional[float]
    max_distance_m: Optional[float]
    distance_margin_m: Optional[float]
    science_score: float
    science_rate_per_hour: float
    is_reachable: bool
    is_budget_feasible: bool
    is_pareto: bool = False
    cumulative_climb_m: float = 0.0
    max_slope_deg: float = 0.0
    formatted_travel_time: str = "—"
    formatted_dwell_time: str = "—"
    formatted_mission_time: str = "—"
    formatted_margin: str = "—"
    timeline_events: List[Dict[str, Any]] = field(default_factory=list)
    legs_summary: List[Dict[str, Any]] = field(default_factory=list)
    profile: str = "balanced"
    vehicle_mode: str = "crew_eva"
    speed_multiplier: float = 1.0

    @property
    def is_feasible(self) -> bool:
        return self.is_reachable and self.is_budget_feasible

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "objective": self.objective,
            "title": self.title,
            "tradeoff_rationale": self.tradeoff_rationale,
            "stop_ids": self.stop_ids,
            "stop_names": self.stop_names,
            "num_stops": self.num_stops,
            "path_rc": [list(pt) for pt in self.path_rc],
            "distance_m": round(self.distance_m, 1),
            "terrain_cost": round(self.terrain_cost, 1),
            "travel_time_s": round(self.travel_time_s, 1),
            "dwell_time_s": round(self.dwell_time_s, 1),
            "hold_delay_s": round(self.hold_delay_s, 1),
            "total_mission_time_s": round(self.total_mission_time_s, 1),
            "operational_limit_s": self.operational_limit_s,
            "time_margin_s": round(self.time_margin_s, 1) if self.time_margin_s is not None else None,
            "max_distance_m": self.max_distance_m,
            "distance_margin_m": round(self.distance_margin_m, 1) if self.distance_margin_m is not None else None,
            "science_score": round(self.science_score, 1),
            "science_rate_per_hour": round(self.science_rate_per_hour, 1),
            "is_reachable": self.is_reachable,
            "is_budget_feasible": self.is_budget_feasible,
            "is_feasible": self.is_feasible,
            "is_pareto": self.is_pareto,
            "cumulative_climb_m": round(self.cumulative_climb_m, 1),
            "max_slope_deg": round(self.max_slope_deg, 1),
            "formatted_travel_time": self.formatted_travel_time,
            "formatted_dwell_time": self.formatted_dwell_time,
            "formatted_mission_time": self.formatted_mission_time,
            "formatted_margin": self.formatted_margin,
            "timeline_events": self.timeline_events,
            "legs_summary": self.legs_summary,
            "profile": self.profile,
            "vehicle_mode": self.vehicle_mode,
            "speed_multiplier": self.speed_multiplier,
        }


@dataclass
class OptimizationReport:
    """
    Comprehensive mission optimization report containing synthesized alternatives
    and non-dominated Pareto frontier candidates.
    """
    start_rc: Tuple[int, int]
    goal_rc: Tuple[int, int]
    profile: str
    vehicle_mode: str
    operational_limit_s: Optional[float]
    max_distance_m: Optional[float]
    dwell_time_per_stop_s: float
    candidates_evaluated: int
    execution_time_ms: float
    recommended_sortie: Optional[SortieCandidate]
    science_champion: Optional[SortieCandidate]
    time_champion: Optional[SortieCandidate]
    balanced_champion: Optional[SortieCandidate]
    direct_baseline: Optional[SortieCandidate]
    pareto_alternatives: List[SortieCandidate]
    all_candidates: List[SortieCandidate]
    disclosures: List[str] = field(default_factory=list)

    @property
    def pareto_frontier_2d(self) -> List[SortieCandidate]:
        """Return the non-dominated 2D Pareto frontier across all synthesized candidates."""
        return extract_pareto_frontier(self.all_candidates)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_rc": list(self.start_rc),
            "goal_rc": list(self.goal_rc),
            "profile": self.profile,
            "vehicle_mode": self.vehicle_mode,
            "operational_limit_s": self.operational_limit_s,
            "max_distance_m": self.max_distance_m,
            "dwell_time_per_stop_s": self.dwell_time_per_stop_s,
            "candidates_evaluated": self.candidates_evaluated,
            "execution_time_ms": round(self.execution_time_ms, 1),
            "recommended_sortie": self.recommended_sortie.to_dict() if self.recommended_sortie else None,
            "science_champion": self.science_champion.to_dict() if self.science_champion else None,
            "time_champion": self.time_champion.to_dict() if self.time_champion else None,
            "balanced_champion": self.balanced_champion.to_dict() if self.balanced_champion else None,
            "direct_baseline": self.direct_baseline.to_dict() if self.direct_baseline else None,
            "pareto_alternatives": [c.to_dict() for c in self.pareto_alternatives],
            "all_candidates": [c.to_dict() for c in self.all_candidates],
            "disclosures": self.disclosures,
        }


def _calculate_tour_metrics(
    ordered_rcs: List[Tuple[int, int]],
    leg_cache: Dict[Tuple[Tuple[int, int], Tuple[int, int]], LegResult],
    vehicle_mode: str,
    speed_multiplier: float,
    dwell_time_per_stop_s: float,
    operational_delay_s: float,
    operational_limit_s: Optional[float],
    max_distance_m: Optional[float],
) -> Tuple[bool, float, float, float, float, float, Optional[float], Optional[float], bool]:
    """
    Rapidly evaluate distance, terrain cost, travel duration, and feasibility for an ordered itinerary.
    Returns:
      (is_reachable, total_dist_m, total_cost, travel_time_s, dwell_time_s, total_mission_time_s,
       time_margin_s, dist_margin_m, is_budget_feasible)
    """
    total_dist = 0.0
    total_cost = 0.0
    total_travel_s = 0.0
    num_legs = len(ordered_rcs) - 1

    for i in range(num_legs):
        u = ordered_rcs[i]
        v = ordered_rcs[i + 1]
        leg = leg_cache.get((u, v))
        if leg is None or not leg.is_reachable or math.isinf(leg.cost):
            return False, 0.0, float("inf"), 0.0, 0.0, 0.0, None, None, False

        total_dist += leg.distance_m
        total_cost += leg.cost
        t_leg, _, _, _ = calculate_traverse_time(leg.cost, mode=vehicle_mode, speed_multiplier=speed_multiplier)
        total_travel_s += t_leg

    num_intermediate = max(0, num_legs - 1)
    total_dwell_s = num_intermediate * dwell_time_per_stop_s
    total_mission_s = total_travel_s + total_dwell_s + operational_delay_s

    # Feasibility evaluation
    time_margin = (operational_limit_s - total_mission_s) if operational_limit_s is not None else None
    dist_margin = (max_distance_m - total_dist) if max_distance_m is not None else None

    is_time_ok = (time_margin is None) or (time_margin >= -0.01)
    is_dist_ok = (dist_margin is None) or (dist_margin >= -0.01)
    is_budget_ok = is_time_ok and is_dist_ok

    return (
        True,
        total_dist,
        total_cost,
        total_travel_s,
        total_dwell_s,
        total_mission_s,
        time_margin,
        dist_margin,
        is_budget_ok,
    )


def optimize_science_tour(
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    terrain: TerrainGrid,
    candidate_waypoints: List[ScienceWaypoint],
    profile: str = "balanced",
    vehicle_mode: str = "crew_eva",
    speed_multiplier: float = 1.0,
    operational_limit_s: Optional[float] = 28800.0,
    max_distance_m: Optional[float] = None,
    dwell_time_per_stop_s: float = 900.0,
    operational_delay_s: float = 0.0,
    max_stops: int = 4,
    beam_width: int = 12,
    leg_cache: Optional[Dict[Tuple[Tuple[int, int], Tuple[int, int]], LegResult]] = None,
    transform: Optional[rasterio.Affine] = None,
) -> OptimizationReport:
    """
    Autonomously discover and rank multi-stop scientific sorties using bounded beam search.

    Parameters
    ----------
    start_rc : Tuple[int, int]
        Departure grid coordinate (row, col).
    goal_rc : Tuple[int, int]
        Destination grid coordinate (row, col).
    terrain : TerrainGrid
        Authoritative elevation raster and slope gradient matrices.
    candidate_waypoints : List[ScienceWaypoint]
        Available science targets from catalogue or user selection.
    profile : str
        A* cost profile ("conservative", "balanced", "science_first").
    vehicle_mode : str
        Locomotion dynamics ("crew_eva" or "robotic_rover").
    speed_multiplier : float
        Locomotion speed scaling (must be > 0).
    operational_limit_s : Optional[float]
        Expedition duration budget ceiling in seconds (e.g. 28,800s = 8.0h).
    max_distance_m : Optional[float]
        Physical ground traverse distance limit in meters.
    dwell_time_per_stop_s : float
        Stationary observation and sampling time per intermediate stop in seconds.
    operational_delay_s : float
        Diagnostic hold or contingency communications delay in seconds.
    max_stops : int
        Maximum intermediate stops allowed (1 to 6).
    beam_width : int
        Number of partial candidates retained per expansion depth.
    leg_cache : Optional[Dict]
        Precomputed pairwise directed legs. Computed automatically if None.
    transform : Optional[rasterio.Affine]
        Cartographic affine transform for geo-coordinates.

    Returns
    -------
    OptimizationReport : Synthesized alternative plans, champions, and Pareto frontier.
    """
    t_start = time.perf_counter()

    # 1. Input Validation
    H, W = terrain.height, terrain.width
    if not (0 <= start_rc[0] < H and 0 <= start_rc[1] < W):
        raise ValueError(f"Start coordinates {start_rc} fall outside terrain bounds ({H}x{W})")
    if not (0 <= goal_rc[0] < H and 0 <= goal_rc[1] < W):
        raise ValueError(f"Goal coordinates {goal_rc} fall outside terrain bounds ({H}x{W})")
    if start_rc == goal_rc:
        raise ValueError("Departure and destination coordinates cannot be the identical grid cell")

    prof = str(profile).lower().strip()
    if prof not in {"conservative", "balanced", "science_first"}:
        raise ValueError(f"Unsupported profile '{profile}'. Allowed: ['conservative', 'balanced', 'science_first']")

    v_mode = str(vehicle_mode).lower().strip()
    if v_mode not in {"crew_eva", "robotic_rover"}:
        raise ValueError(f"Unsupported vehicle_mode '{vehicle_mode}'. Allowed: ['crew_eva', 'robotic_rover']")

    speed_mult = float(speed_multiplier) if speed_multiplier > 0 else 1.0
    limit_s = float(operational_limit_s) if operational_limit_s is not None and operational_limit_s > 0 else None
    max_dist = float(max_distance_m) if max_distance_m is not None and max_distance_m > 0 else None
    dwell_s = max(0.0, float(dwell_time_per_stop_s))
    delay_s = max(0.0, float(operational_delay_s))
    k_max = max(1, min(6, int(max_stops)))
    b_width = max(2, min(30, int(beam_width)))

    # Filter out waypoints that match start or goal or have invalid coordinates
    valid_wps: List[ScienceWaypoint] = []
    seen_rcs = {start_rc, goal_rc}
    seen_ids = set()

    for wp in candidate_waypoints:
        r, c = wp.rc
        if not (0 <= r < H and 0 <= c < W):
            continue
        if (r, c) in seen_rcs or wp.id in seen_ids:
            continue
        seen_rcs.add((r, c))
        seen_ids.add(wp.id)
        valid_wps.append(wp)

    # 2. Pairwise Leg Caching
    t_cfg = get_profile_terrain_config(prof)
    unique_nodes = [start_rc] + [w.rc for w in valid_wps] + [goal_rc]
    unique_nodes = list(dict.fromkeys(unique_nodes))

    if leg_cache is None:
        leg_cache = compute_pairwise_leg_cache(unique_nodes, terrain, terrain_config=t_cfg)

    # 3. Direct Route Baseline Evaluation (0 stops)
    direct_ok, d_dist, d_cost, d_travel, d_dwell, d_mission, d_t_margin, d_d_margin, d_feasible = (
        _calculate_tour_metrics(
            [start_rc, goal_rc],
            leg_cache,
            vehicle_mode=v_mode,
            speed_multiplier=speed_mult,
            dwell_time_per_stop_s=dwell_s,
            operational_delay_s=delay_s,
            operational_limit_s=limit_s,
            max_distance_m=max_dist,
        )
    )

    baseline_candidate_summary = {
        "ordered_wps": [],
        "ordered_rcs": [start_rc, goal_rc],
        "science_score": 0.0,
        "distance_m": d_dist,
        "terrain_cost": d_cost,
        "travel_time_s": d_travel,
        "dwell_time_s": d_dwell,
        "total_mission_time_s": d_mission,
        "time_margin_s": d_t_margin,
        "distance_margin_m": d_d_margin,
        "is_reachable": direct_ok,
        "is_budget_feasible": d_feasible,
    }

    # 4. Bounded Beam Search
    evaluated_itineraries: List[Dict[str, Any]] = [baseline_candidate_summary]
    seen_itineraries_set: Set[Tuple[str, ...]] = {()}

    # State: (ordered_wp_indices, current_rc, cum_dist, cum_cost, cum_travel_s, cum_science)
    start_state = ((), start_rc, 0.0, 0.0, 0.0, 0.0)
    current_beam = [start_state]

    num_cands = len(valid_wps)
    for depth in range(1, k_max + 1):
        next_candidates = []
        for visited_indices, curr_rc, cum_dist, cum_cost, cum_travel, cum_sci in current_beam:
            visited_set = set(visited_indices)
            for next_idx in range(num_cands):
                if next_idx in visited_set:
                    continue

                next_wp = valid_wps[next_idx]
                leg = leg_cache.get((curr_rc, next_wp.rc))
                if leg is None or not leg.is_reachable or math.isinf(leg.cost):
                    continue

                t_leg, _, _, _ = calculate_traverse_time(leg.cost, mode=v_mode, speed_multiplier=speed_mult)
                new_dist = cum_dist + leg.distance_m
                new_cost = cum_cost + leg.cost
                new_travel = cum_travel + t_leg
                new_sci = cum_sci + float(next_wp.priority_score)
                new_visited = visited_indices + (next_idx,)

                # Evaluate tour completing to goal
                goal_leg = leg_cache.get((next_wp.rc, goal_rc))
                if goal_leg and goal_leg.is_reachable and not math.isinf(goal_leg.cost):
                    t_goal, _, _, _ = calculate_traverse_time(goal_leg.cost, mode=v_mode, speed_multiplier=speed_mult)
                    total_d = new_dist + goal_leg.distance_m
                    total_c = new_cost + goal_leg.cost
                    total_tr = new_travel + t_goal
                    total_dw = len(new_visited) * dwell_s
                    total_m = total_tr + total_dw + delay_s

                    t_margin = (limit_s - total_m) if limit_s is not None else None
                    d_margin = (max_dist - total_d) if max_dist is not None else None
                    is_f = ((t_margin is None or t_margin >= -0.01) and (d_margin is None or d_margin >= -0.01))

                    wp_ids_tuple = tuple(valid_wps[i].id for i in new_visited)
                    if wp_ids_tuple not in seen_itineraries_set:
                        seen_itineraries_set.add(wp_ids_tuple)
                        evaluated_itineraries.append({
                            "ordered_wps": [valid_wps[i] for i in new_visited],
                            "ordered_rcs": [start_rc] + [valid_wps[i].rc for i in new_visited] + [goal_rc],
                            "science_score": new_sci,
                            "distance_m": total_d,
                            "terrain_cost": total_c,
                            "travel_time_s": total_tr,
                            "dwell_time_s": total_dw,
                            "total_mission_time_s": total_m,
                            "time_margin_s": t_margin,
                            "distance_margin_m": d_margin,
                            "is_reachable": True,
                            "is_budget_feasible": is_f,
                        })

                # Score partial state for beam retention (heuristic: science value minus normalized travel cost)
                # Science score weighted against distance penalty
                alpha = 0.015 if prof != "science_first" else 0.005
                beam_score = new_sci - alpha * new_dist
                next_candidates.append((beam_score, (new_visited, next_wp.rc, new_dist, new_cost, new_travel, new_sci)))

        if not next_candidates:
            break

        # Retain top B partial states
        next_candidates.sort(key=lambda x: x[0], reverse=True)
        current_beam = [item[1] for item in next_candidates[:b_width]]

    # 5. Extract Champions & Pareto Non-Dominated Frontiers
    feasible_plans = [p for p in evaluated_itineraries if p["is_reachable"] and p["is_budget_feasible"]]

    # In case no multi-stop candidate is feasible, fall back to direct or all candidates
    pool = feasible_plans if feasible_plans else evaluated_itineraries

    # Champion 1: Science Priority Champion
    # Maximizes total science priority points. Tie-break: lowest total_mission_time_s
    science_champ_raw = max(pool, key=lambda p: (p["science_score"], -p["total_mission_time_s"]))

    # Champion 2: Time Efficiency Champion
    # Maximizes science score per hour of total mission time (with >= 1 stop if feasible)
    multi_stop_pool = [p for p in pool if len(p["ordered_wps"]) > 0]
    if multi_stop_pool:
        time_champ_raw = max(
            multi_stop_pool,
            key=lambda p: (p["science_score"] / max(1.0, p["total_mission_time_s"]), -p["total_mission_time_s"])
        )
    else:
        time_champ_raw = baseline_candidate_summary

    # Champion 3: Balanced Trade-off Champion
    # Normalizes science and mission duration to compute balanced utility
    max_sci = max((p["science_score"] for p in pool), default=1.0) or 1.0
    max_time = max((p["total_mission_time_s"] for p in pool), default=1.0) or 1.0
    max_cost = max((p["terrain_cost"] for p in pool), default=1.0) or 1.0

    def _balanced_score(p: Dict[str, Any]) -> float:
        norm_sci = p["science_score"] / max_sci
        norm_time = p["total_mission_time_s"] / max_time
        norm_cost = p["terrain_cost"] / max_cost
        # Balanced formula: 50% science reward, 30% time conservation, 20% terrain ease
        return 0.50 * norm_sci + 0.30 * (1.0 - norm_time) + 0.20 * (1.0 - norm_cost)

    balanced_champ_raw = max(pool, key=_balanced_score)

    # 6. Extract 2D/3D Non-Dominated Pareto Candidates
    pareto_raw: List[Dict[str, Any]] = []
    tol = 1e-4

    for cand in pool:
        is_dominated = False
        c_time = cand["total_mission_time_s"]
        c_sci = cand["science_score"]
        c_cost = cand["terrain_cost"]

        for other in pool:
            if cand is other:
                continue
            o_time = other["total_mission_time_s"]
            o_sci = other["science_score"]
            o_cost = other["terrain_cost"]

            # Other dominates cand if it takes less/equal time, less/equal cost, and gets more/equal science
            at_least_as_good = (o_time <= c_time + tol) and (o_sci >= c_sci - tol) and (o_cost <= c_cost + tol)
            strictly_better = (o_time < c_time - tol) or (o_sci > c_sci + tol) or (o_cost < c_cost - tol)
            if at_least_as_good and strictly_better:
                is_dominated = True
                break

        if not is_dominated:
            pareto_raw.append(cand)

    # Sort Pareto candidates by total_mission_time_s ascending
    pareto_raw.sort(key=lambda p: (p["total_mission_time_s"], -p["science_score"]))

    # Tag Pareto membership across all evaluated
    pareto_signatures = {tuple(w.id for w in p["ordered_wps"]) for p in pareto_raw}

    # 7. Authoritative Multi-Stop Route Verification
    # Re-evaluate selected distinct itineraries through plan_sequential_multistop_route
    # to guarantee exact 3D coordinates, cumulative climb, max slope, and leg timeline fidelity.
    p_config = PlannerConfig(
        profile=prof,
        max_distance_m=max_dist,
    )

    def _build_authoritative_sortie(
        cand_dict: Dict[str, Any],
        obj_type: SortieObjective,
        title: str,
        rationale: str,
    ) -> SortieCandidate:
        ordered_rcs = cand_dict["ordered_rcs"]
        ordered_wps = cand_dict["ordered_wps"]
        stop_ids = [w.id for w in ordered_wps]
        stop_names = [w.name for w in ordered_wps]
        stop_priorities = [float(w.priority_score) for w in ordered_wps]

        # Authoritative sequential planning
        authoritative_route: RouteResult = plan_sequential_multistop_route(
            ordered_points=ordered_rcs,
            terrain=terrain,
            stop_ids=stop_ids,
            stop_priorities=stop_priorities,
            config=p_config,
            vehicle_mode=v_mode,
            dwell_time_per_stop_s=dwell_s,
            operational_delay_s=delay_s,
            operational_limit_s=limit_s,
            speed_multiplier=speed_mult,
        )

        tl: Optional[MissionTimeline] = authoritative_route.timeline
        events_dicts = []
        if tl and tl.events:
            for ev in tl.events:
                events_dicts.append({
                    "event_type": ev.event_type,
                    "label": ev.label,
                    "target_id": ev.target_id,
                    "duration_s": round(ev.duration_s, 1),
                    "formatted_duration": ev.formatted_duration,
                    "formatted_cumulative_time": ev.formatted_cumulative_time,
                    "distance_m": round(ev.distance_m, 1),
                })

        legs_dicts = []
        if authoritative_route.legs:
            for idx, leg in enumerate(authoritative_route.legs):
                t_leg, _, _, _ = calculate_traverse_time(leg.cost, mode=v_mode, speed_multiplier=speed_mult)
                legs_dicts.append({
                    "leg_index": idx + 1,
                    "start_rc": list(leg.start_rc),
                    "goal_rc": list(leg.goal_rc),
                    "distance_m": round(leg.distance_m, 1),
                    "cost": round(leg.cost, 1),
                    "travel_time_s": round(t_leg, 1),
                    "formatted_time": format_duration(t_leg),
                    "is_reachable": leg.is_reachable,
                })

        # Calculate slope statistics
        climb_m = 0.0
        max_slope_deg = 0.0
        if authoritative_route.path and len(authoritative_route.path) > 1:
            for idx in range(len(authoritative_route.path) - 1):
                r1, c1 = authoritative_route.path[idx]
                r2, c2 = authoritative_route.path[idx + 1]
                e1 = float(terrain.elevation[r1, c1])
                e2 = float(terrain.elevation[r2, c2])
                dz = e2 - e1
                if dz > 0:
                    climb_m += dz
                dx = abs(c2 - c1) * 20.0
                dy = abs(r2 - r1) * 20.0
                step_d = math.hypot(dx, dy)
                if step_d > 0:
                    slope = abs(math.atan2(dz, step_d) * (180.0 / math.pi))
                    if slope > max_slope_deg:
                        max_slope_deg = slope

        t_time = tl.total_traverse_time_s if tl else cand_dict["travel_time_s"]
        d_time = tl.total_dwell_time_s if tl else cand_dict["dwell_time_s"]
        m_time = tl.total_mission_time_s if tl else cand_dict["total_mission_time_s"]
        m_margin = tl.remaining_margin_s if tl else cand_dict["time_margin_s"]
        fmt_travel = tl.formatted_traverse_time if tl else format_duration(t_time)
        fmt_dwell = tl.formatted_dwell_time if tl else format_duration(d_time)
        fmt_mission = tl.formatted_mission_time if tl else format_duration(m_time)
        fmt_margin = tl.formatted_remaining_margin if tl else (f"{m_margin/3600.0:+.1f} h" if m_margin is not None else "—")

        rate = (authoritative_route.science_score / (m_time / 3600.0)) if m_time > 0 else 0.0
        is_pareto = tuple(stop_ids) in pareto_signatures
        cand_id = f"sortie_{obj_type.value}_{len(stop_ids)}stops"

        return SortieCandidate(
            id=cand_id,
            objective=obj_type.value,
            title=title,
            tradeoff_rationale=rationale,
            stop_ids=stop_ids,
            stop_names=stop_names,
            num_stops=len(stop_ids),
            path_rc=authoritative_route.path,
            distance_m=authoritative_route.distance_m,
            terrain_cost=authoritative_route.cost,
            travel_time_s=t_time,
            dwell_time_s=d_time,
            hold_delay_s=delay_s,
            total_mission_time_s=m_time,
            operational_limit_s=limit_s,
            time_margin_s=m_margin,
            max_distance_m=max_dist,
            distance_margin_m=(max_dist - authoritative_route.distance_m) if max_dist is not None else None,
            science_score=authoritative_route.science_score,
            science_rate_per_hour=rate,
            is_reachable=authoritative_route.is_reachable,
            is_budget_feasible=authoritative_route.is_budget_feasible,
            is_pareto=is_pareto,
            cumulative_climb_m=climb_m,
            max_slope_deg=max_slope_deg,
            formatted_travel_time=fmt_travel,
            formatted_dwell_time=fmt_dwell,
            formatted_mission_time=fmt_mission,
            formatted_margin=fmt_margin,
            timeline_events=events_dicts,
            legs_summary=legs_dicts,
            profile=prof,
            vehicle_mode=v_mode,
            speed_multiplier=speed_mult,
        )

    # Build direct baseline candidate
    direct_candidate = _build_authoritative_sortie(
        baseline_candidate_summary,
        SortieObjective.DIRECT_BASELINE,
        "Direct Nominal Traverse (0 Stops)",
        "Direct point-to-point path from departure to destination with zero science stops. Baseline reference for distance and transit duration.",
    )

    # Build Science Priority champion
    sci_stops_str = ", ".join(w.name for w in science_champ_raw["ordered_wps"]) or "None"
    science_candidate = _build_authoritative_sortie(
        science_champ_raw,
        SortieObjective.SCIENCE_PRIORITY,
        f"Science Priority Sortie ({len(science_champ_raw['ordered_wps'])} Stops)",
        f"Maximizes scientific priority yield ({science_champ_raw['science_score']:.0f} pts) visiting {sci_stops_str} within operational budget constraints.",
    )

    # Build Time Efficiency champion
    time_stops_str = ", ".join(w.name for w in time_champ_raw["ordered_wps"]) or "Direct"
    time_candidate = _build_authoritative_sortie(
        time_champ_raw,
        SortieObjective.TIME_EFFICIENCY,
        f"Time-Efficient Sortie ({len(time_champ_raw['ordered_wps'])} Stops)",
        f"Maximizes science return per mission hour ({time_champ_raw['science_score'] / max(1.0, time_champ_raw['total_mission_time_s']/3600.0):.1f} pts/h) visiting {time_stops_str}, prioritizing crew margin.",
    )

    # Build Balanced champion
    bal_stops_str = ", ".join(w.name for w in balanced_champ_raw["ordered_wps"]) or "Direct"
    balanced_candidate = _build_authoritative_sortie(
        balanced_champ_raw,
        SortieObjective.BALANCED,
        f"Balanced Expedition Sortie ({len(balanced_champ_raw['ordered_wps'])} Stops)",
        f"Optimal compromise balancing science sampling ({balanced_champ_raw['science_score']:.0f} pts), slope traversal effort, and remaining operational time margin.",
    )

    # Build Pareto frontier candidates (distinct from champions)
    built_signatures = {
        tuple(direct_candidate.stop_ids),
        tuple(science_candidate.stop_ids),
        tuple(time_candidate.stop_ids),
        tuple(balanced_candidate.stop_ids),
    }

    pareto_candidates: List[SortieCandidate] = []
    for idx, p_raw in enumerate(pareto_raw):
        sig = tuple(w.id for w in p_raw["ordered_wps"])
        if sig in built_signatures:
            continue
        built_signatures.add(sig)

        p_sortie = _build_authoritative_sortie(
            p_raw,
            SortieObjective.PARETO_ALTERNATIVE,
            f"Pareto Trade-off Option #{len(pareto_candidates)+1} ({len(p_raw['ordered_wps'])} Stops)",
            f"Non-dominated trade-off: {p_raw['science_score']:.0f} pts in {format_duration(p_raw['total_mission_time_s'])}, preserving safe operational margin.",
        )
        pareto_candidates.append(p_sortie)

    # Assemble all synthesized alternatives
    all_synthesized = [direct_candidate, balanced_candidate, science_candidate, time_candidate] + pareto_candidates

    # Recommended sortie: Balanced candidate if feasible, otherwise highest-science feasible
    recommended = balanced_candidate if balanced_candidate.is_feasible else (
        science_candidate if science_candidate.is_feasible else (
            direct_candidate if direct_candidate.is_feasible else all_synthesized[0]
        )
    )

    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    disclosures = [
        "SCIENTIFIC PROVENANCE: Topography derived from USGS Astrogeology Science Center MRO CTX DTM at 20 m/pixel.",
        "MODEL INPUT DISCLOSURE: Science waypoint priority scores are user/curator model inputs, not official NASA scientific rankings.",
        "BOUNDED SEARCH NOTICE: Candidate itineraries are generated via bounded beam search over candidate targets; final routes are validated by the authoritative Python A* engine.",
        "NOT FLIGHT CERTIFIED: MarsWalk 2.0 is an educational and mission rehearsal prototype. Modeled sorties do not certify physical safety for astronaut EVA flight operations.",
    ]

    return OptimizationReport(
        start_rc=start_rc,
        goal_rc=goal_rc,
        profile=prof,
        vehicle_mode=v_mode,
        operational_limit_s=limit_s,
        max_distance_m=max_dist,
        dwell_time_per_stop_s=dwell_s,
        candidates_evaluated=len(evaluated_itineraries),
        execution_time_ms=elapsed_ms,
        recommended_sortie=recommended,
        science_champion=science_candidate,
        time_champion=time_candidate,
        balanced_champion=balanced_candidate,
        direct_baseline=direct_candidate,
        pareto_alternatives=pareto_candidates,
        all_candidates=all_synthesized,
        disclosures=disclosures,
    )


def extract_pareto_frontier(
    candidates: List[SortieCandidate],
) -> List[SortieCandidate]:
    """
    Extract the non-dominated Pareto frontier from a list of candidate sorties
    optimizing for maximum science score and minimum traverse time.
    """
    pareto: List[SortieCandidate] = []
    for cand in candidates:
        is_dominated = False
        for other in candidates:
            if other.id == cand.id:
                continue
            # other dominates cand if other has >= science and <= travel time, with at least one strict
            if (
                other.science_score >= cand.science_score and
                other.travel_time_s <= cand.travel_time_s and
                (other.science_score > cand.science_score or other.travel_time_s < cand.travel_time_s)
            ):
                is_dominated = True
                break
        if not is_dominated:
            pareto.append(cand)
    return pareto


def optimize_mission_sorties(
    terrain: TerrainGrid,
    all_waypoints: List[ScienceWaypoint],
    candidate_waypoint_ids: Optional[List[str]] = None,
    start_rc: Tuple[int, int] = (117, 157),
    goal_rc: Tuple[int, int] = (66, 128),
    profile: str = "balanced",
    vehicle_mode: str = "crew_eva",
    speed_multiplier: float = 1.0,
    operational_limit_s: Optional[float] = 28800.0,
    max_distance_m: Optional[float] = None,
    dwell_time_per_stop_s: float = 900.0,
    operational_delay_s: float = 0.0,
    max_stops: int = 4,
    beam_width: int = 12,
    leg_cache: Optional[Dict[Tuple[Tuple[int, int], Tuple[int, int]], LegResult]] = None,
    transform: Optional[rasterio.Affine] = None,
) -> OptimizationReport:
    """
    Convenience wrapper for optimize_science_tour accepting all_waypoints and candidate_waypoint_ids filter.
    """
    wp_map = {w.id: w for w in all_waypoints}
    if candidate_waypoint_ids is not None:
        cands = [wp_map[wid] for wid in candidate_waypoint_ids if wid in wp_map]
    else:
        cands = list(all_waypoints)

    return optimize_science_tour(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain,
        candidate_waypoints=cands,
        profile=profile,
        vehicle_mode=vehicle_mode,
        speed_multiplier=speed_multiplier,
        operational_limit_s=operational_limit_s,
        max_distance_m=max_distance_m,
        dwell_time_per_stop_s=dwell_time_per_stop_s,
        operational_delay_s=operational_delay_s,
        max_stops=max_stops,
        beam_width=beam_width,
        leg_cache=leg_cache,
        transform=transform,
    )

