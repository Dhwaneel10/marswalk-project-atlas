"""
MarsWalk 2.0 — Milestone 9W: Adaptive Mission Replanning & Disruption-Aware Optimization Engine.

Provides an integrated, decision-grade workflow answering:
"When a disruption occurs, should the current mission continue, change its route,
remove a target, or be replaced with a different science tour?"

Executes a Three-Stage Mission Comparison:
1. Stage 1 — Original Plan: Nominal mission selected before disruption.
2. Stage 2 — Disrupted Plan: Original itinerary evaluated under the disruption conditions.
3. Stage 3 — Adaptive Plan: Newly optimized multi-stop tour calculated under the exact same
   disrupted conditions to preserve and recover scientific objectives within operational limits.
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

from marswalk.core.terrain import TerrainGrid, TerrainConfig
from marswalk.core.planner import (
    PlannerConfig,
    RouteResult,
    ScienceWaypoint,
    LegResult,
    OPERATIONAL_LIMITS_S,
    astar_search,
    compute_pairwise_leg_cache,
    stitch_path_legs,
    plan_sequential_multistop_route,
    plan_route,
    calculate_traverse_time,
    format_duration,
)
from marswalk.core.contingency import (
    CustomEventType,
    CustomEventDefinition,
    compile_custom_contingency,
)
from marswalk.core.stress_test import (
    DisruptionType,
    ScenarioDefinition,
)
from marswalk.core.mission_optimizer import (
    SortieObjective,
    SortieCandidate,
    OptimizationReport,
    optimize_science_tour,
    extract_pareto_frontier,
)


class ReplanningRecommendation(str, enum.Enum):
    """Operational recommendation categories for adaptive replanning."""
    CONTINUE_WITH_DETOUR = "continue_with_detour"
    DROP_TARGET_AND_PROCEED = "drop_target_and_proceed"
    REPLACE_WITH_ADAPTIVE_TOUR = "replace_with_adaptive_tour"
    ABORT_TO_DIRECT_BASELINE = "abort_to_direct_baseline"
    UNRESOLVABLE_CRITICAL_HAZARD = "unresolvable_critical_hazard"


@dataclass
class ScienceRecoverySummary:
    """
    Quantitative scientific recovery and operational impact accounting.
    """
    original_science_score: float
    disrupted_science_score: float
    adaptive_science_score: float
    science_score_lost: float
    science_score_recovered: float
    science_recovery_pct: float
    net_science_delta: float

    # Waypoint changes
    original_stop_ids: List[str]
    disrupted_stop_ids: List[str]
    adaptive_stop_ids: List[str]
    retained_stop_ids: List[str]
    dropped_stop_ids: List[str]
    added_stop_ids: List[str]

    # Operational metric deltas (Adaptive vs Original)
    distance_delta_m: float
    travel_time_delta_s: float
    mission_time_delta_s: float
    margin_delta_s: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_science_score": round(self.original_science_score, 1),
            "original_priority": round(self.original_science_score, 1),
            "disrupted_science_score": round(self.disrupted_science_score, 1),
            "disrupted_priority": round(self.disrupted_science_score, 1),
            "adaptive_science_score": round(self.adaptive_science_score, 1),
            "adaptive_priority": round(self.adaptive_science_score, 1),
            "science_score_lost": round(self.science_score_lost, 1),
            "priority_lost": round(self.science_score_lost, 1),
            "science_score_recovered": round(self.science_score_recovered, 1),
            "priority_recovered": round(self.science_score_recovered, 1),
            "science_recovery_pct": round(self.science_recovery_pct, 1),
            "recovery_efficiency_pct": round(self.science_recovery_pct, 1),
            "net_science_delta": round(self.net_science_delta, 1),
            "net_priority_delta": round(self.net_science_delta, 1),
            "original_stop_ids": self.original_stop_ids,
            "disrupted_stop_ids": self.disrupted_stop_ids,
            "adaptive_stop_ids": self.adaptive_stop_ids,
            "retained_stop_ids": self.retained_stop_ids,
            "retained_stops": self.retained_stop_ids,
            "dropped_stop_ids": self.dropped_stop_ids,
            "dropped_stops": self.dropped_stop_ids,
            "added_stop_ids": self.added_stop_ids,
            "newly_added_stops": self.added_stop_ids,
            "distance_delta_m": round(self.distance_delta_m, 1),
            "travel_time_delta_s": round(self.travel_time_delta_s, 1),
            "mission_time_delta_s": round(self.mission_time_delta_s, 1),
            "margin_delta_s": round(self.margin_delta_s, 1),
        }



@dataclass
class AdaptiveReplanningResult:
    """
    Comprehensive three-stage adaptive mission replanning comparison.
    """
    original_plan: SortieCandidate
    disrupted_plan: SortieCandidate
    adaptive_plan: SortieCandidate
    recovery_metrics: ScienceRecoverySummary
    adaptive_alternatives: List[SortieCandidate]
    recommendation: ReplanningRecommendation
    recommendation_title: str
    operational_rationale: str
    events_summary: List[Dict[str, Any]]
    computation_fingerprint: str
    execution_time_ms: float
    disclosures: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        recov_dict = self.recovery_metrics.to_dict()
        return {
            "status": "success",
            "schema_version": "1.0.0",
            "computation_fingerprint": self.computation_fingerprint,
            "execution_time_ms": round(self.execution_time_ms, 1),
            "recommendation": self.recommendation.value,
            "recommendation_title": self.recommendation_title,
            "operational_rationale": self.operational_rationale,
            "recommendation_rationale": self.operational_rationale,
            "original_plan": self.original_plan.to_dict(),
            "disrupted_plan": self.disrupted_plan.to_dict(),
            "adaptive_plan": self.adaptive_plan.to_dict(),
            "recovery_metrics": recov_dict,
            "science_recovery": recov_dict,
            "adaptive_alternatives": [c.to_dict() for c in self.adaptive_alternatives],
            "events_summary": self.events_summary,
            "disclosures": self.disclosures,
        }


def _evaluate_candidate_sortie(
    ordered_points: List[Tuple[int, int]],
    stop_waypoints: List[ScienceWaypoint],
    terrain: TerrainGrid,
    objective: SortieObjective,
    title: str,
    rationale: str,
    profile: str = "balanced",
    vehicle_mode: str = "crew_eva",
    speed_multiplier: float = 1.0,
    operational_limit_s: Optional[float] = 28800.0,
    max_distance_m: Optional[float] = None,
    dwell_time_per_stop_s: float = 900.0,
    operational_delay_s: float = 0.0,
    terrain_config: Optional[TerrainConfig] = None,
    blocked_mask: Optional[np.ndarray] = None,
    cost_multiplier_mask: Optional[np.ndarray] = None,
) -> SortieCandidate:
    """
    Execute authoritative evaluation of an ordered itinerary with disruption modifiers applied.
    """
    num_stops = len(stop_waypoints)
    stop_ids = [w.id for w in stop_waypoints]
    stop_names = [w.name for w in stop_waypoints]
    stop_priorities = [w.priority_score for w in stop_waypoints]
    science_score = sum(stop_priorities)

    p_cfg = PlannerConfig(profile=profile, max_distance_m=max_distance_m)

    route_res = plan_sequential_multistop_route(
        ordered_points=ordered_points,
        terrain=terrain,
        stop_ids=stop_ids,
        stop_priorities=stop_priorities,
        config=p_cfg,
        terrain_config=terrain_config,
        blocked_mask=blocked_mask,
        cost_multiplier_mask=cost_multiplier_mask,
        vehicle_mode=vehicle_mode,
        dwell_time_per_stop_s=dwell_time_per_stop_s,
        operational_delay_s=operational_delay_s,
        operational_limit_s=operational_limit_s,
        speed_multiplier=speed_multiplier,
    )

    is_reachable = route_res.is_reachable and len(route_res.path) >= 2
    dist_m = route_res.distance_m
    cost_val = route_res.cost

    # Calculate slope statistics
    climb_m = 0.0
    max_slope = 0.0
    if route_res.path and len(route_res.path) > 1:
        for idx in range(len(route_res.path) - 1):
            r1, c1 = route_res.path[idx]
            r2, c2 = route_res.path[idx + 1]
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
                if slope > max_slope:
                    max_slope = slope

    tl = route_res.timeline
    if tl is not None:
        travel_time_s = tl.total_traverse_time_s
        dwell_time_s = tl.total_dwell_time_s
        hold_delay_s = tl.total_operational_delay_s
        total_mission_time_s = tl.total_mission_time_s
        time_margin_s = tl.remaining_margin_s
        is_budget_ok = tl.is_within_limit
        formatted_travel = tl.formatted_traverse_time
        formatted_dwell = tl.formatted_dwell_time
        formatted_mission = tl.formatted_mission_time
        formatted_margin = tl.formatted_remaining_margin
        events_list = [
            {
                "event_type": e.event_type,
                "label": e.label,
                "target_id": e.target_id,
                "leg_index": e.leg_index,
                "start_time_s": e.start_time_s,
                "end_time_s": e.end_time_s,
                "duration_s": e.duration_s,
                "distance_m": e.distance_m,
                "formatted_duration": e.formatted_duration,
                "formatted_cumulative_time": e.formatted_cumulative_time,
                "notes": e.notes,
            }
            for e in tl.events
        ]
    else:
        # Fallback calculation if timeline is None
        travel_time_s = calculate_traverse_time(route_res.path, terrain, vehicle_mode, speed_multiplier) if is_reachable else 0.0
        dwell_time_s = num_stops * dwell_time_per_stop_s
        hold_delay_s = operational_delay_s
        total_mission_time_s = travel_time_s + dwell_time_s + hold_delay_s
        limit_s = operational_limit_s if operational_limit_s is not None else OPERATIONAL_LIMITS_S.get(vehicle_mode, 28800.0)
        time_margin_s = limit_s - total_mission_time_s
        is_budget_ok = total_mission_time_s <= limit_s
        formatted_travel = format_duration(travel_time_s)
        formatted_dwell = format_duration(dwell_time_s)
        formatted_mission = format_duration(total_mission_time_s)
        formatted_margin = format_duration(time_margin_s)
        events_list = []

    dist_margin_m = (max_distance_m - dist_m) if max_distance_m is not None else None
    if max_distance_m is not None and dist_m > max_distance_m:
        is_budget_ok = False

    rate_per_hr = (science_score / (total_mission_time_s / 3600.0)) if total_mission_time_s > 0 else 0.0

    legs_list = [
        {
            "start_rc": list(leg.start_rc),
            "goal_rc": list(leg.goal_rc),
            "distance_m": round(leg.distance_m, 1),
            "cost": round(leg.cost, 1),
            "is_reachable": leg.is_reachable,
        }
        for leg in (route_res.legs or [])
    ]

    return SortieCandidate(
        id=f"sortie_{objective.value}_{abs(hash(tuple(stop_ids))) % 100000:05d}",
        objective=objective.value,
        title=title,
        tradeoff_rationale=rationale,
        stop_ids=stop_ids,
        stop_names=stop_names,
        num_stops=num_stops,
        path_rc=route_res.path,
        distance_m=dist_m,
        terrain_cost=cost_val,
        travel_time_s=travel_time_s,
        dwell_time_s=dwell_time_s,
        hold_delay_s=hold_delay_s,
        total_mission_time_s=total_mission_time_s,
        operational_limit_s=operational_limit_s,
        time_margin_s=time_margin_s,
        max_distance_m=max_distance_m,
        distance_margin_m=dist_margin_m,
        science_score=science_score,
        science_rate_per_hour=rate_per_hr,
        is_reachable=is_reachable,
        is_budget_feasible=is_budget_ok,
        is_pareto=False,
        cumulative_climb_m=climb_m,
        max_slope_deg=max_slope,
        formatted_travel_time=formatted_travel,
        formatted_dwell_time=formatted_dwell,
        formatted_mission_time=formatted_mission,
        formatted_margin=formatted_margin,
        timeline_events=events_list,
        legs_summary=legs_list,
        profile=profile,
        vehicle_mode=vehicle_mode,
        speed_multiplier=speed_multiplier,
    )


def replan_adaptive_mission(
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    terrain: TerrainGrid,
    candidate_waypoints: List[ScienceWaypoint],
    events_data: Union[List[Union[Dict[str, Any], CustomEventDefinition]], Dict[str, Any]],
    original_stop_ids: Optional[List[str]] = None,
    original_plan_candidate: Optional[SortieCandidate] = None,
    profile: str = "balanced",
    vehicle_mode: str = "crew_eva",
    speed_multiplier: float = 1.0,
    operational_limit_s: Optional[float] = 28800.0,
    max_distance_m: Optional[float] = None,
    dwell_time_per_stop_s: float = 900.0,
    operational_delay_s: float = 0.0,
    max_stops: int = 4,
    beam_width: int = 14,
    transform: Optional[rasterio.Affine] = None,
) -> AdaptiveReplanningResult:
    """
    Execute comprehensive 3-stage adaptive replanning:
    1. Original Plan: Nominal baseline before disruption.
    2. Disrupted Plan: Original itinerary evaluated under actual disruption events.
    3. Adaptive Plan: Newly optimized multi-stop science tour evaluated under the same disruption.
    """
    t_start = time.perf_counter()

    # Input sanitization
    if not (0 <= start_rc[0] < terrain.height and 0 <= start_rc[1] < terrain.width):
        raise ValueError(f"Departure coordinate {start_rc} falls outside terrain bounds (0-{terrain.height-1}, 0-{terrain.width-1})")
    if not (0 <= goal_rc[0] < terrain.height and 0 <= goal_rc[1] < terrain.width):
        raise ValueError(f"Destination coordinate {goal_rc} falls outside terrain bounds (0-{terrain.height-1}, 0-{terrain.width-1})")
    if start_rc == goal_rc:
        raise ValueError("Departure and destination coordinates cannot be identical")

    wp_catalogue = {w.id: w for w in candidate_waypoints}

    # =========================================================================
    # STAGE 1: Original Plan (Nominal Baseline)
    # =========================================================================
    if original_plan_candidate is not None:
        original_sortie = original_plan_candidate
    elif original_stop_ids is not None:
        orig_wps = [wp_catalogue[sid] for sid in original_stop_ids if sid in wp_catalogue]
        orig_points = [start_rc] + [w.rc for w in orig_wps] + [goal_rc]
        orig_stops_str = ", ".join(w.name for w in orig_wps) or "Direct"
        original_sortie = _evaluate_candidate_sortie(
            ordered_points=orig_points,
            stop_waypoints=orig_wps,
            terrain=terrain,
            objective=SortieObjective.BALANCED,
            title=f"Original Mission Plan ({len(orig_wps)} Stops)",
            rationale=f"Pre-disruption nominal expedition visiting {orig_stops_str}.",
            profile=profile,
            vehicle_mode=vehicle_mode,
            speed_multiplier=speed_multiplier,
            operational_limit_s=operational_limit_s,
            max_distance_m=max_distance_m,
            dwell_time_per_stop_s=dwell_time_per_stop_s,
            operational_delay_s=operational_delay_s,
        )
    else:
        # Optimize nominal tour to synthesize original baseline
        nominal_report = optimize_science_tour(
            start_rc=start_rc,
            goal_rc=goal_rc,
            terrain=terrain,
            candidate_waypoints=candidate_waypoints,
            profile=profile,
            vehicle_mode=vehicle_mode,
            speed_multiplier=speed_multiplier,
            operational_limit_s=operational_limit_s,
            max_distance_m=max_distance_m,
            dwell_time_per_stop_s=dwell_time_per_stop_s,
            operational_delay_s=operational_delay_s,
            max_stops=max_stops,
            beam_width=beam_width,
            transform=transform,
        )
        original_sortie = nominal_report.balanced_champion or nominal_report.recommended_sortie or nominal_report.direct_baseline

    # =========================================================================
    # PARSE & COMPILE DISRUPTION EVENTS
    # =========================================================================
    has_events = bool(events_data)
    if has_events:
        scenario_def, parsed_events = compile_custom_contingency(
            events_data=events_data,
            terrain=terrain,
        )
    else:
        from marswalk.core.stress_test import ScenarioDefinition, DisruptionType
        scenario_def = ScenarioDefinition(
            id="nominal_contingency",
            name="Nominal (No Disruption)",
            disruption_type=DisruptionType.COMPOUND_DISRUPTION,
            description="No disruptions applied.",
        )
        parsed_events = []



    # Disruption spatial & operational masks
    scen_blocked_mask: Optional[np.ndarray] = None
    if scenario_def.blocked_cells:
        scen_blocked_mask = np.zeros(terrain.shape, dtype=bool)
        for r, c in scenario_def.blocked_cells:
            if 0 <= r < terrain.height and 0 <= c < terrain.width:
                scen_blocked_mask[r, c] = True

    scen_cost_mask: Optional[np.ndarray] = None
    if scenario_def.cost_multiplier_cells:
        scen_cost_mask = np.ones(terrain.shape, dtype=np.float32)
        for r, c in scenario_def.cost_multiplier_cells:
            if 0 <= r < terrain.height and 0 <= c < terrain.width:
                scen_cost_mask[r, c] = float(scenario_def.cost_multiplier)

    scen_terrain_config: Optional[TerrainConfig] = None
    if scenario_def.slope_penalty_multiplier != 1.0 or scenario_def.max_slope_deg_override is not None:
        t_cfg = terrain.config
        max_s = float(scenario_def.max_slope_deg_override) if scenario_def.max_slope_deg_override is not None else t_cfg.theta_max_deg
        crit_s = min(t_cfg.theta_crit_deg, max_s * 0.7)
        scen_terrain_config = TerrainConfig(
            cell_size_m=t_cfg.cell_size_m,
            ref_lat_deg=t_cfg.ref_lat_deg,
            dx_ground_m=t_cfg.dx_ground_m,
            dy_ground_m=t_cfg.dy_ground_m,
            alpha_s=t_cfg.alpha_s * float(scenario_def.slope_penalty_multiplier),
            theta_crit_deg=crit_s,
            theta_max_deg=max_s,
            alpha_r=t_cfg.alpha_r,
            sigma_0_m=t_cfg.sigma_0_m,
            alpha_up=t_cfg.alpha_up,
            nodata_sentinel=t_cfg.nodata_sentinel,
            min_valid_elev_m=t_cfg.min_valid_elev_m,
            max_valid_elev_m=t_cfg.max_valid_elev_m,
        )

    scen_speed_multiplier = speed_multiplier * float(scenario_def.speed_multiplier)
    scen_operational_delay_s = operational_delay_s + float(scenario_def.operational_delay_s)

    base_limit = operational_limit_s if operational_limit_s is not None else OPERATIONAL_LIMITS_S.get(vehicle_mode, 28800.0)
    scen_operational_limit_s = base_limit
    if scenario_def.reduced_time_budget_s is not None:
        scen_operational_limit_s = float(scenario_def.reduced_time_budget_s)
    elif scenario_def.budget_reduction_pct is not None:
        pct = float(scenario_def.budget_reduction_pct)
        scen_operational_limit_s = max(600.0, base_limit * (1.0 - pct / 100.0))

    scen_max_distance_m = max_distance_m
    if scenario_def.reduced_max_distance_m is not None:
        scen_max_distance_m = float(scenario_def.reduced_max_distance_m)

    unavailable_target_id = scenario_def.unavailable_target_id

    # =========================================================================
    # STAGE 2: Disrupted Original Mission
    # =========================================================================
    # Check if any original stops are unavailable
    disrupted_wps: List[ScienceWaypoint] = []
    dropped_from_original: List[str] = []
    for sid in original_sortie.stop_ids:
        if unavailable_target_id and sid == unavailable_target_id:
            dropped_from_original.append(sid)
        elif sid in wp_catalogue:
            disrupted_wps.append(wp_catalogue[sid])

    disrupted_ordered_points = [start_rc] + [w.rc for w in disrupted_wps] + [goal_rc]
    disrupted_stops_str = ", ".join(w.name for w in disrupted_wps) or "Direct"

    disrupted_rationale = (
        f"Original itinerary evaluated under {scenario_def.name}. "
        f"{f'Target {unavailable_target_id} unavailable; dropped from route. ' if dropped_from_original else ''}"
        f"Route recalculated with spatial obstacles, mobility scaling ({scen_speed_multiplier:.2f}x), "
        f"and operational hold (+{scen_operational_delay_s/60:.0f}m)."
    )

    disrupted_sortie = _evaluate_candidate_sortie(
        ordered_points=disrupted_ordered_points,
        stop_waypoints=disrupted_wps,
        terrain=terrain,
        objective=SortieObjective.BALANCED,
        title=f"Disrupted Original Plan ({len(disrupted_wps)} Stops)",
        rationale=disrupted_rationale,
        profile=profile,
        vehicle_mode=vehicle_mode,
        speed_multiplier=scen_speed_multiplier,
        operational_limit_s=scen_operational_limit_s,
        max_distance_m=scen_max_distance_m,
        dwell_time_per_stop_s=dwell_time_per_stop_s,
        operational_delay_s=scen_operational_delay_s,
        terrain_config=scen_terrain_config,
        blocked_mask=scen_blocked_mask,
        cost_multiplier_mask=scen_cost_mask,
    )

    # =========================================================================
    # STAGE 3: Adaptive Replanned Mission
    # =========================================================================
    # Filter available target pool under disruption conditions:
    # 1. Exclude explicitly unavailable target
    # 2. Exclude targets whose coordinates fall directly inside blocked_mask
    adaptive_candidate_wps: List[ScienceWaypoint] = []
    for w in candidate_waypoints:
        if unavailable_target_id and w.id == unavailable_target_id:
            continue
        if scen_blocked_mask is not None and 0 <= w.rc[0] < terrain.height and 0 <= w.rc[1] < terrain.width:
            if scen_blocked_mask[w.rc[0], w.rc[1]]:
                continue  # Target itself is engulfed in closed corridor
        adaptive_candidate_wps.append(w)

    # Build disrupted pairwise leg cache for adaptive search
    adaptive_nodes = [start_rc, goal_rc] + [w.rc for w in adaptive_candidate_wps]
    # Unique nodes
    unique_nodes: List[Tuple[int, int]] = []
    seen_nodes: Set[Tuple[int, int]] = set()
    for pt in adaptive_nodes:
        if pt not in seen_nodes:
            seen_nodes.add(pt)
            unique_nodes.append(pt)

    disrupted_leg_cache = compute_pairwise_leg_cache(
        nodes=unique_nodes,
        terrain=terrain,
        terrain_config=scen_terrain_config,
        blocked_mask=scen_blocked_mask,
        cost_multiplier_mask=scen_cost_mask,
    )

    # Run bounded beam search under disruption conditions
    adaptive_report = optimize_science_tour(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain,
        candidate_waypoints=adaptive_candidate_wps,
        profile=profile,
        vehicle_mode=vehicle_mode,
        speed_multiplier=scen_speed_multiplier,
        operational_limit_s=scen_operational_limit_s,
        max_distance_m=scen_max_distance_m,
        dwell_time_per_stop_s=dwell_time_per_stop_s,
        operational_delay_s=scen_operational_delay_s,
        max_stops=max_stops,
        beam_width=beam_width,
        leg_cache=disrupted_leg_cache,
        transform=transform,
    )

    # Ensure all adaptive champions and alternatives are authoritatively re-evaluated with full masks
    def _recalc_sortie(cand: Optional[SortieCandidate], obj: SortieObjective, title: str, desc: str) -> Optional[SortieCandidate]:
        if cand is None:
            return None
        c_wps = [wp_catalogue[sid] for sid in cand.stop_ids if sid in wp_catalogue]
        c_points = [start_rc] + [w.rc for w in c_wps] + [goal_rc]
        return _evaluate_candidate_sortie(
            ordered_points=c_points,
            stop_waypoints=c_wps,
            terrain=terrain,
            objective=obj,
            title=title,
            rationale=desc,
            profile=profile,
            vehicle_mode=vehicle_mode,
            speed_multiplier=scen_speed_multiplier,
            operational_limit_s=scen_operational_limit_s,
            max_distance_m=scen_max_distance_m,
            dwell_time_per_stop_s=dwell_time_per_stop_s,
            operational_delay_s=scen_operational_delay_s,
            terrain_config=scen_terrain_config,
            blocked_mask=scen_blocked_mask,
            cost_multiplier_mask=scen_cost_mask,
        )

    adaptive_balanced = _recalc_sortie(
        adaptive_report.balanced_champion,
        SortieObjective.BALANCED,
        f"Adaptive Balanced Sortie ({len(adaptive_report.balanced_champion.stop_ids) if adaptive_report.balanced_champion else 0} Stops)",
        "Optimal balance between scientific sampling, terrain effort, and life-support margin under active disruption."
    )
    adaptive_science = _recalc_sortie(
        adaptive_report.science_champion,
        SortieObjective.SCIENCE_PRIORITY,
        f"Adaptive Science Priority Sortie ({len(adaptive_report.science_champion.stop_ids) if adaptive_report.science_champion else 0} Stops)",
        "Maximizes preserved and recovered scientific priority yield under disruption constraints."
    )
    adaptive_time = _recalc_sortie(
        adaptive_report.time_champion,
        SortieObjective.TIME_EFFICIENCY,
        f"Adaptive Time-Efficient Sortie ({len(adaptive_report.time_champion.stop_ids) if adaptive_report.time_champion else 0} Stops)",
        "Maximizes science return per mission hour while prioritizing quick completion and safe margin."
    )
    adaptive_direct = _recalc_sortie(
        adaptive_report.direct_baseline,
        SortieObjective.DIRECT_BASELINE,
        "Direct Disrupted Evacuation (0 Stops)",
        "Direct nominal transit from departure to destination avoiding active hazards with zero intermediate science stops."
    )

    adaptive_alternatives: List[SortieCandidate] = [
        c for c in [adaptive_balanced, adaptive_science, adaptive_time, adaptive_direct] if c is not None
    ]

    # Re-evaluate any Pareto alternatives that are distinct
    seen_sigs = {tuple(c.stop_ids) for c in adaptive_alternatives}
    for p_alt in adaptive_report.pareto_alternatives:
        sig = tuple(p_alt.stop_ids)
        if sig not in seen_sigs:
            seen_sigs.add(sig)
            recalc_p = _recalc_sortie(
                p_alt,
                SortieObjective.PARETO_ALTERNATIVE,
                f"Adaptive Trade-off Option #{len(adaptive_alternatives)+1} ({len(p_alt.stop_ids)} Stops)",
                f"Non-dominated trade-off yielding {p_alt.science_score:.0f} pts under active contingency."
            )
            if recalc_p is not None:
                adaptive_alternatives.append(recalc_p)

    # Select primary adaptive plan
    # Prefer balanced if feasible, else highest-science feasible, else fastest feasible, else direct baseline
    adaptive_plan: SortieCandidate
    if adaptive_balanced and adaptive_balanced.is_feasible:
        adaptive_plan = adaptive_balanced
    elif adaptive_science and adaptive_science.is_feasible:
        adaptive_plan = adaptive_science
    elif adaptive_time and adaptive_time.is_feasible:
        adaptive_plan = adaptive_time
    elif adaptive_direct and adaptive_direct.is_feasible:
        adaptive_plan = adaptive_direct
    elif adaptive_alternatives:
        # If none feasible, pick the one with lowest deficit
        feasible_sorted = sorted(adaptive_alternatives, key=lambda c: (c.is_reachable, c.time_margin_s if c.time_margin_s is not None else -999999), reverse=True)
        adaptive_plan = feasible_sorted[0]
    else:
        adaptive_plan = disrupted_sortie

    # =========================================================================
    # SCIENCE RECOVERY & OPERATIONAL METRICS
    # =========================================================================
    orig_pts = original_sortie.science_score
    disr_pts = disrupted_sortie.science_score if disrupted_sortie.is_feasible else 0.0
    adapt_pts = adaptive_plan.science_score if adaptive_plan.is_feasible else 0.0

    pts_lost = max(0.0, orig_pts - disr_pts)
    pts_recovered = max(0.0, adapt_pts - disr_pts)
    recovery_pct = ((pts_recovered / pts_lost) * 100.0) if pts_lost > 0 else (100.0 if adapt_pts >= orig_pts else 0.0)
    net_science_delta = adapt_pts - orig_pts

    orig_set = set(original_sortie.stop_ids)
    disr_set = set(disrupted_sortie.stop_ids)
    adapt_set = set(adaptive_plan.stop_ids)

    retained_stops = [sid for sid in original_sortie.stop_ids if sid in adapt_set]
    dropped_stops = [sid for sid in original_sortie.stop_ids if sid not in adapt_set]
    added_stops = [sid for sid in adaptive_plan.stop_ids if sid not in orig_set]

    dist_delta = adaptive_plan.distance_m - original_sortie.distance_m
    travel_time_delta = adaptive_plan.travel_time_s - original_sortie.travel_time_s
    mission_time_delta = adaptive_plan.total_mission_time_s - original_sortie.total_mission_time_s
    orig_margin = original_sortie.time_margin_s or 0.0
    adapt_margin = adaptive_plan.time_margin_s or 0.0
    margin_delta = adapt_margin - orig_margin

    recovery_summary = ScienceRecoverySummary(
        original_science_score=orig_pts,
        disrupted_science_score=disr_pts,
        adaptive_science_score=adapt_pts,
        science_score_lost=pts_lost,
        science_score_recovered=pts_recovered,
        science_recovery_pct=recovery_pct,
        net_science_delta=net_science_delta,
        original_stop_ids=original_sortie.stop_ids,
        disrupted_stop_ids=disrupted_sortie.stop_ids,
        adaptive_stop_ids=adaptive_plan.stop_ids,
        retained_stop_ids=retained_stops,
        dropped_stop_ids=dropped_stops,
        added_stop_ids=added_stops,
        distance_delta_m=dist_delta,
        travel_time_delta_s=travel_time_delta,
        mission_time_delta_s=mission_time_delta,
        margin_delta_s=margin_delta,
    )

    # =========================================================================
    # OPERATIONAL RECOMMENDATION SYNTHESIS
    # =========================================================================
    if not adaptive_plan.is_reachable and not disrupted_sortie.is_reachable:
        rec = ReplanningRecommendation.UNRESOLVABLE_CRITICAL_HAZARD
        rec_title = "CRITICAL HAZARD: Traverses Unreachable"
        rationale = "Spatial disruption blocks all accessible corridors to departure/destination. Immediate field halt or evacuation required."
    elif not adaptive_plan.is_budget_feasible and not disrupted_sortie.is_budget_feasible:
        rec = ReplanningRecommendation.ABORT_TO_DIRECT_BASELINE
        rec_title = "BUDGET DEPLETED: Direct Evacuation Required"
        rationale = f"Remaining operational window ({format_duration(scen_operational_limit_s)}) is insufficient for science operations. Return directly to base."
    elif len(added_stops) > 0 and pts_recovered > 0:
        rec = ReplanningRecommendation.REPLACE_WITH_ADAPTIVE_TOUR
        rec_title = "RECOMMENDATION: Replace with Adaptive Science Tour"
        rationale = (
            f"Replanned adaptive tour recovers {pts_recovered:.0f} science points ({recovery_pct:.1f}% recovery) "
            f"by incorporating alternative targets ({', '.join(added_stops)}) while remaining safely within operational limits."
        )
    elif len(dropped_stops) > 0 and disrupted_sortie.is_feasible:
        rec = ReplanningRecommendation.DROP_TARGET_AND_PROCEED
        rec_title = "RECOMMENDATION: Drop Unavailable Target & Proceed"
        rationale = f"Proceeding with revised stops ({', '.join(disrupted_sortie.stop_ids)}) maintains feasibility with {disrupted_sortie.science_score:.0f} pts."
    elif disrupted_sortie.is_feasible and abs(disrupted_sortie.distance_m - original_sortie.distance_m) > 10.0:
        rec = ReplanningRecommendation.CONTINUE_WITH_DETOUR
        rec_title = "RECOMMENDATION: Continue Original Mission via Detour"
        rationale = f"Disrupted original mission remains fully feasible with an acceptable detour (+{disrupted_sortie.distance_m - original_sortie.distance_m:.0f}m). All {len(disrupted_sortie.stop_ids)} targets preserved."
    elif disrupted_sortie.is_feasible:
        rec = ReplanningRecommendation.CONTINUE_WITH_DETOUR
        rec_title = "RECOMMENDATION: Continue Original Mission"
        rationale = "Disruption does not impede current traverse geometry or budget constraints. Proceed as planned."
    else:
        rec = ReplanningRecommendation.REPLACE_WITH_ADAPTIVE_TOUR
        rec_title = "RECOMMENDATION: Adopt Adaptive Plan"
        rationale = "Original itinerary is rendered infeasible by the disruption. Adaptive replanned tour restores mission feasibility."

    # Generate computation fingerprint uniquely binding inputs, events, and adaptive result
    fingerprint_data = {
        "start": start_rc,
        "goal": goal_rc,
        "profile": profile,
        "vehicle_mode": vehicle_mode,
        "events": [e.id for e in parsed_events],
        "original_stops": original_sortie.stop_ids,
        "adaptive_stops": adaptive_plan.stop_ids,
        "adaptive_distance": round(adaptive_plan.distance_m, 1),
    }
    canon_json = json.dumps(fingerprint_data, sort_keys=True)
    comp_fingerprint = hashlib.sha256(canon_json.encode("utf-8")).hexdigest()

    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    disclosures = [
        "SCIENTIFIC PROVENANCE: Topography derived from USGS Astrogeology Science Center MRO CTX DTM at 20 m/pixel.",
        "MODEL INPUT TRANSPARENCY: Science waypoint priority scores are user/curator model inputs, not official NASA scientific rankings.",
        "ADAPTIVE OPTIMIZATION NOTICE: Adaptive alternatives are generated via bounded beam search under active disruption constraints, verified authoritatively by Python A*.",
        "NOT FLIGHT CERTIFIED: MarsWalk 2.0 is an educational and mission rehearsal prototype. Modeled traverses do not certify physical safety for astronaut EVA flight operations.",
    ]

    events_summary = [
        {
            "id": e.id,
            "name": e.name,
            "event_type": e.event_type.value,
            "description": e.description,
            "enabled": e.enabled,
        }
        for e in parsed_events
    ]

    return AdaptiveReplanningResult(
        original_plan=original_sortie,
        disrupted_plan=disrupted_sortie,
        adaptive_plan=adaptive_plan,
        recovery_metrics=recovery_summary,
        adaptive_alternatives=adaptive_alternatives,
        recommendation=rec,
        recommendation_title=rec_title,
        operational_rationale=rationale,
        events_summary=events_summary,
        computation_fingerprint=comp_fingerprint,
        execution_time_ms=elapsed_ms,
        disclosures=disclosures,
    )
