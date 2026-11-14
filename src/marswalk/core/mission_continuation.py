"""
MarsWalk 2.0 — Milestone 10B: Mid-Sortie Emergency Injection, Mission State Handoff & Live Adaptive Replanning.

Provides an authoritative mid-mission interruption, state handoff, and adaptive continuation engine:
1. Exact mid-sortie state capture: rover coordinates, instantaneous elevation/slope, elapsed distance,
   remaining operational budget without double counting, and clean partitioning of completed vs. unvisited targets.
2. Hypothetical emergency event injection: rockfall corridor closures, mobility deratings,
   operational holds, and target inaccessibility.
3. Three-stage remaining sortie trade-off evaluation:
   - Nominal Remaining: unchanged planned continuation to remaining stops.
   - Disrupted Remaining: nominal remaining evaluated under the injected contingency.
   - Adaptive Continuation: newly optimized A* route and itinerary from current rover position to goal.
4. Seamless playback model construction starting from current position, suppressing completed past cues
   and preserving mission provenance.

SCIENTIFIC PRINCIPLES & GOVERNANCE:
- Modeled timelines and detours are calculated from A* search on the 20m CTX DTM grid.
- Injected emergencies are explicitly designated as simulated hypothetical events.
- Traversal metrics are never presented as certified astronaut life-support envelopes.
- No synthetic data is presented as primary observations.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
import time
import uuid
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
    plan_route,
    plan_sequential_multistop_route,
    calculate_traverse_time,
    format_duration,
)
from marswalk.core.contingency import (
    CustomEventType,
    CustomEventDefinition,
    compile_custom_contingency,
    compute_circular_footprint,
)
from marswalk.core.stress_test import (
    DisruptionType,
    ScenarioDefinition,
)
from marswalk.core.adaptive_replanner import (
    ReplanningRecommendation,
    _evaluate_candidate_sortie,
)
from marswalk.core.mission_optimizer import (
    SortieObjective,
    SortieCandidate,
    optimize_science_tour,
)
from marswalk.core.mission_playback import (
    MissionPlaybackModel,
    PlaybackSample,
    PlaybackTimelineEvent,
    build_mission_playback_model,
    interpolate_playback_state,
)


@dataclass
class MidSortieState:
    """Authoritative snapshot of vehicle state at the moment of mid-sortie interruption."""
    source_mission_id: Optional[str]
    interruption_time_s: float
    rover_rc: Tuple[int, int]
    rover_float_rc: Tuple[float, float]
    elevation_m: float
    slope_deg: float
    is_stationary: bool
    active_event_type: Optional[str]
    active_target_id: Optional[str]
    elapsed_distance_m: float
    original_budget_s: float
    remaining_budget_s: float
    goal_rc: Tuple[int, int]
    completed_stop_ids: List[str]
    unvisited_stops: List[ScienceWaypoint]
    unvisited_stop_ids: List[str]
    historical_path_rc: List[Tuple[int, int]]
    nominal_remaining_path_rc: List[Tuple[int, int]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_mission_id": self.source_mission_id,
            "interruption_time_s": round(self.interruption_time_s, 2),
            "rover_rc": list(self.rover_rc),
            "rover_float_rc": [round(self.rover_float_rc[0], 2), round(self.rover_float_rc[1], 2)],
            "elevation_m": round(self.elevation_m, 2),
            "slope_deg": round(self.slope_deg, 2),
            "is_stationary": self.is_stationary,
            "active_event_type": self.active_event_type,
            "active_target_id": self.active_target_id,
            "elapsed_distance_m": round(self.elapsed_distance_m, 2),
            "original_budget_s": round(self.original_budget_s, 2),
            "remaining_budget_s": round(self.remaining_budget_s, 2),
            "goal_rc": list(self.goal_rc),
            "completed_stop_ids": self.completed_stop_ids,
            "unvisited_stop_ids": self.unvisited_stop_ids,
            "historical_path_length": len(self.historical_path_rc),
            "nominal_remaining_path_length": len(self.nominal_remaining_path_rc),
        }


def _find_nearest_valid_cell(r: int, c: int, terrain: TerrainGrid) -> Tuple[int, int]:
    """Find the nearest traversable cell with valid elevation (>-9000)."""
    if 0 <= r < terrain.height and 0 <= c < terrain.width:
        if float(terrain.elevation[r, c]) > -9000.0:
            return (r, c)
    for radius in range(1, 10):
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < terrain.height and 0 <= nc < terrain.width:
                    if float(terrain.elevation[nr, nc]) > -9000.0:
                        return (nr, nc)
    return (max(0, min(r, terrain.height - 1)), max(0, min(c, terrain.width - 1)))


def capture_mid_sortie_state(
    playback_model: Union[MissionPlaybackModel, Dict[str, Any]],
    interruption_time_s: float,
    terrain: TerrainGrid,
    total_budget_s: Optional[float] = None,
    goal_rc: Optional[Tuple[int, int]] = None,
) -> MidSortieState:
    """
    Capture the instantaneous state of a mission at timestamp t = interruption_time_s.

    Guarantees:
    1. Continuous position interpolation matches route geometry at query time.
    2. Discrete anchor cell (r, c) is traversable and within terrain bounds.
    3. Partitioning of completed vs. unvisited waypoints is deterministic: completed stops
       are never rescheduled as future targets.
    4. Remaining budget strictly subtracts elapsed time: T_rem = max(0, T_budget - t).
    """
    if isinstance(playback_model, dict):
        # Build lightweight model or extract samples
        p_samples = playback_model.get("samples", [])
        p_events = playback_model.get("events", [])
        p_waypoints = playback_model.get("waypoints", [])
        p_tot_dur = float(playback_model.get("total_duration_s", 0.0))
        p_tot_dist = float(playback_model.get("total_distance_m", 0.0))
        p_margin = float(playback_model.get("remaining_margin_s", 0.0))
        p_mid = playback_model.get("mission_id")
        p_variant = playback_model.get("mission_variant", "nominal")
        p_vmode = playback_model.get("vehicle_mode", "crew_eva")

        # Convert dict events to PlaybackTimelineEvent objects if needed
        model_events: List[PlaybackTimelineEvent] = []
        for e in p_events:
            model_events.append(
                PlaybackTimelineEvent(
                    event_index=e.get("event_index", 0),
                    event_id=e.get("event_id", ""),
                    event_type=e.get("event_type", "traverse_leg"),
                    label=e.get("label", ""),
                    target_id=e.get("target_id"),
                    leg_index=e.get("leg_index"),
                    start_time_s=float(e.get("start_time_s", 0.0)),
                    end_time_s=float(e.get("end_time_s", 0.0)),
                    duration_s=float(e.get("duration_s", 0.0)),
                    distance_m=float(e.get("distance_m", 0.0)),
                    cumulative_distance_start_m=float(e.get("cumulative_distance_start_m", 0.0)),
                    cumulative_distance_end_m=float(e.get("cumulative_distance_end_m", 0.0)),
                    start_rc=tuple(e.get("start_rc", [0, 0])),  # type: ignore
                    end_rc=tuple(e.get("end_rc", [0, 0])),  # type: ignore
                    start_elevation_m=float(e.get("start_elevation_m", 0.0)),
                    end_elevation_m=float(e.get("end_elevation_m", 0.0)),
                    notes=e.get("notes", ""),
                )
            )

        model_samples: List[PlaybackSample] = []
        for s in p_samples:
            model_samples.append(
                PlaybackSample(
                    sample_index=s.get("sample_index", 0),
                    time_s=float(s.get("time_s", 0.0)),
                    rc=tuple(s.get("rc", [0.0, 0.0])),  # type: ignore
                    elevation_m=float(s.get("elevation_m", 0.0)),
                    slope_deg=float(s.get("slope_deg", 0.0)),
                    cumulative_distance_m=float(s.get("cumulative_distance_m", 0.0)),
                    speed_m_s=float(s.get("speed_m_s", 0.0)),
                    active_event_index=s.get("active_event_index", 0),
                    event_type=s.get("event_type", "traverse_leg"),
                    target_id=s.get("target_id"),
                    is_stationary=bool(s.get("is_stationary", False)),
                    leg_index=s.get("leg_index"),
                )
            )

        active_model = MissionPlaybackModel(
            schema_version="1.0.0",
            mission_id=p_mid,
            mission_variant=p_variant,
            vehicle_mode=p_vmode,
            total_duration_s=p_tot_dur,
            total_distance_m=p_tot_dist,
            total_traverse_time_s=float(playback_model.get("total_traverse_time_s", p_tot_dur)),
            total_dwell_time_s=float(playback_model.get("total_dwell_time_s", 0.0)),
            total_operational_delay_s=float(playback_model.get("total_operational_delay_s", 0.0)),
            remaining_margin_s=p_margin,
            is_within_limit=bool(playback_model.get("is_within_limit", True)),
            is_reachable=bool(playback_model.get("is_reachable", True)),
            events=model_events,
            samples=model_samples,
            waypoints=p_waypoints,
            telemetry_summary=playback_model.get("telemetry_summary", {}),
            metadata=playback_model.get("metadata", {}),
        )
    else:
        active_model = playback_model

    t = max(0.0, min(float(interruption_time_s), active_model.total_duration_s))

    # 1. Continuous state interpolation
    interp = interpolate_playback_state(active_model, t)
    raw_r, raw_c = interp["rc"]
    nearest_r = int(round(raw_r))
    nearest_c = int(round(raw_c))
    valid_r, valid_c = _find_nearest_valid_cell(nearest_r, nearest_c, terrain)

    # 2. Goal destination resolution
    dest_rc = goal_rc
    if dest_rc is None:
        if active_model.events:
            dest_rc = active_model.events[-1].end_rc
        elif active_model.waypoints:
            last_wp = active_model.waypoints[-1]
            dest_rc = tuple(last_wp.get("rc", [valid_r, valid_c]))  # type: ignore
        elif active_model.samples:
            last_s = active_model.samples[-1]
            dest_rc = (int(round(last_s.rc[0])), int(round(last_s.rc[1])))
        else:
            dest_rc = (valid_r, valid_c)

    # 3. Budget accounting
    if total_budget_s is not None and total_budget_s > 0:
        eff_total_budget = float(total_budget_s)
    else:
        standard_limit = OPERATIONAL_LIMITS_S.get(active_model.vehicle_mode, 28800.0)
        eff_total_budget = active_model.total_duration_s + max(0.0, active_model.remaining_margin_s)
        if eff_total_budget <= 0.0 or eff_total_budget < active_model.total_duration_s:
            eff_total_budget = max(standard_limit, active_model.total_duration_s)

    remaining_budget_s = max(0.0, eff_total_budget - t)

    # 4. Target accounting: Completed vs Unvisited
    completed_ids: List[str] = []
    unvisited_wps: List[ScienceWaypoint] = []
    unvisited_ids: List[str] = []

    # Map target_id to dwell event end time
    dwell_end_times: Dict[str, float] = {}
    dwell_start_times: Dict[str, float] = {}
    for evt in active_model.events:
        if evt.event_type == "science_dwell" and evt.target_id:
            dwell_end_times[evt.target_id] = evt.end_time_s
            dwell_start_times[evt.target_id] = evt.start_time_s

    # Examine waypoints catalogue in model
    for wp in active_model.waypoints:
        tid = str(wp.get("id", ""))
        if not tid:
            continue
        wp_end_t = dwell_end_times.get(tid)
        wp_start_t = dwell_start_times.get(tid)

        # A target is completed if its dwell period finished on or before t
        if wp_end_t is not None and t >= wp_end_t:
            completed_ids.append(tid)
        elif wp_start_t is not None and t > wp_start_t and (t >= (wp_start_t + 0.9 * (wp_end_t - wp_start_t))):
            completed_ids.append(tid)
        else:
            unvisited_ids.append(tid)
            raw_rc = wp.get("rc", [0, 0])
            wp_rc = (int(raw_rc[0]), int(raw_rc[1]))
            unvisited_wps.append(
                ScienceWaypoint(
                    id=tid,
                    name=str(wp.get("name", tid)),
                    rc=wp_rc,
                    priority_score=float(wp.get("priority_score", wp.get("priority", 1.0))),
                )
            )

    # 5. Extract historical path and nominal remaining path
    full_path: List[Tuple[int, int]] = []
    if active_model.samples:
        for s in active_model.samples:
            pt = (int(round(s.rc[0])), int(round(s.rc[1])))
            if not full_path or full_path[-1] != pt:
                full_path.append(pt)

    if not full_path:
        full_path = [(valid_r, valid_c), dest_rc]

    # Find the closest point in full_path to valid_r, valid_c
    closest_idx = 0
    min_dist_sq = float("inf")
    for i, pt in enumerate(full_path):
        d2 = (pt[0] - valid_r) ** 2 + (pt[1] - valid_c) ** 2
        if d2 < min_dist_sq:
            min_dist_sq = d2
            closest_idx = i

    historical_path = full_path[:closest_idx + 1]
    if not historical_path:
        historical_path = [(valid_r, valid_c)]
    elif historical_path[-1] != (valid_r, valid_c):
        historical_path.append((valid_r, valid_c))

    nominal_remaining = full_path[closest_idx:]
    if not nominal_remaining:
        nominal_remaining = [(valid_r, valid_c), dest_rc]
    elif nominal_remaining[0] != (valid_r, valid_c):
        nominal_remaining = [(valid_r, valid_c)] + nominal_remaining

    return MidSortieState(
        source_mission_id=active_model.mission_id or "mission_nominal",
        interruption_time_s=t,
        rover_rc=(valid_r, valid_c),
        rover_float_rc=(raw_r, raw_c),
        elevation_m=float(interp["elevation_m"]),
        slope_deg=float(interp["slope_deg"]),
        is_stationary=bool(interp["is_stationary"]),
        active_event_type=interp.get("event_type"),
        active_target_id=interp.get("target_id"),
        elapsed_distance_m=float(interp["cumulative_distance_m"]),
        original_budget_s=eff_total_budget,
        remaining_budget_s=remaining_budget_s,
        goal_rc=dest_rc,
        completed_stop_ids=completed_ids,
        unvisited_stops=unvisited_wps,
        unvisited_stop_ids=unvisited_ids,
        historical_path_rc=historical_path,
        nominal_remaining_path_rc=nominal_remaining,
    )


def plan_mission_continuation(
    terrain: TerrainGrid,
    mid_state: MidSortieState,
    event_definition: Union[Dict[str, Any], List[Dict[str, Any]]],
    profile: str = "balanced",
    vehicle_mode: str = "crew_eva",
    speed_multiplier: float = 1.0,
    operational_limit_s: Optional[float] = None,
    max_stops: int = 4,
    beam_width: int = 14,
    transform: Optional[rasterio.Affine] = None,
) -> Dict[str, Any]:
    """
    Compute 3-stage remaining sortie trade-off from captured vehicle state:
    1. Nominal Remaining: unaltered planned trajectory to remaining stops.
    2. Disrupted Remaining: nominal remaining evaluated under the injected contingency.
    3. Adaptive Continuation: disruption-aware replanned route from rover_rc to goal_rc.

    Returns a structured dictionary strictly compliant with mission-continue-response schema.
    """
    t_start = time.perf_counter()

    # Budget for the remaining mission
    rem_budget_s = operational_limit_s if operational_limit_s is not None else mid_state.remaining_budget_s
    rem_budget_s = max(0.0, float(rem_budget_s))

    start_rc = mid_state.rover_rc
    goal_rc = mid_state.goal_rc

    # 1. Compile contingency events
    events_raw: List[Dict[str, Any]] = []
    if isinstance(event_definition, list):
        events_raw = event_definition
    elif isinstance(event_definition, dict):
        events_raw = [event_definition]

    scenario_def, parsed_events = compile_custom_contingency(
        events_data=events_raw,
        terrain=terrain,
    )

    # Build spatial masks
    scen_blocked_mask: Optional[np.ndarray] = None
    blocked_cells_set: Set[Tuple[int, int]] = set()
    if scenario_def.blocked_cells:
        scen_blocked_mask = np.zeros(terrain.shape, dtype=bool)
        for r, c in scenario_def.blocked_cells:
            if 0 <= r < terrain.height and 0 <= c < terrain.width:
                scen_blocked_mask[r, c] = True
                blocked_cells_set.add((r, c))

    scen_cost_mask: Optional[np.ndarray] = None
    if scenario_def.cost_multiplier_cells:
        scen_cost_mask = np.ones(terrain.shape, dtype=np.float32)
        for r, c in scenario_def.cost_multiplier_cells:
            if 0 <= r < terrain.height and 0 <= c < terrain.width:
                scen_cost_mask[r, c] = float(scenario_def.cost_multiplier)

    # Event modifiers
    event_speed_mult = float(scenario_def.speed_multiplier if scenario_def.speed_multiplier > 0 else 1.0)
    effective_speed_mult = speed_multiplier * event_speed_mult
    operational_hold_s = float(scenario_def.operational_delay_s)
    unavailable_targets = {
        e.unavailable_target_id
        for e in parsed_events
        if getattr(e, "event_type", None) == CustomEventType.TARGET_UNAVAILABLE and getattr(e, "unavailable_target_id", None)
    }

    # =========================================================================
    # STAGE 1: Nominal Remaining Evaluation
    # =========================================================================
    nominal_points = [start_rc] + [w.rc for w in mid_state.unvisited_stops] + [goal_rc]
    # Deduplicate consecutive points
    clean_nom_points = [nominal_points[0]]
    for pt in nominal_points[1:]:
        if pt != clean_nom_points[-1]:
            clean_nom_points.append(pt)

    nom_candidate = _evaluate_candidate_sortie(
        ordered_points=clean_nom_points,
        stop_waypoints=mid_state.unvisited_stops,
        terrain=terrain,
        objective=SortieObjective.BALANCED,
        title="Nominal Remaining Route",
        rationale="Uninterrupted continuation along original planned sequence.",
        profile=profile,
        vehicle_mode=vehicle_mode,
        speed_multiplier=speed_multiplier,
        operational_limit_s=rem_budget_s,
    )

    nom_reachable = nom_candidate.is_reachable
    nom_dist_m = nom_candidate.distance_m
    nom_total_time_s = nom_candidate.total_mission_time_s
    nom_trav_s = nom_candidate.travel_time_s
    nom_dwell_s = nom_candidate.dwell_time_s
    nom_margin_s = nom_candidate.time_margin_s if nom_candidate.time_margin_s is not None else (rem_budget_s - nom_total_time_s)
    nom_within_limit = nom_candidate.is_budget_feasible and nom_reachable

    nominal_remaining_dict = {
        "is_reachable": nom_reachable,
        "is_within_limit": nom_within_limit,
        "distance_m": round(nom_dist_m, 2),
        "total_time_s": round(nom_total_time_s, 2),
        "traverse_time_s": round(nom_trav_s, 2),
        "dwell_time_s": round(nom_dwell_s, 2),
        "margin_s": round(nom_margin_s, 2),
        "stop_count": len(mid_state.unvisited_stops),
        "stop_ids": [w.id for w in mid_state.unvisited_stops],
        "path_rc": [list(pt) for pt in nom_candidate.path_rc],
    }

    # =========================================================================
    # STAGE 2: Disrupted Remaining Evaluation
    # =========================================================================
    # Test nominal remaining path against blocked cells
    blocked_encounters = 0
    if blocked_cells_set and nom_candidate.path_rc:
        for pt in nom_candidate.path_rc:
            if pt in blocked_cells_set:
                blocked_encounters += 1

    disr_reachable = nom_reachable and (blocked_encounters == 0)
    # Adjusted travel time with event speed modifier
    disr_trav_s = nom_trav_s / event_speed_mult if event_speed_mult > 0 else nom_trav_s
    disr_total_time_s = disr_trav_s + nom_dwell_s + operational_hold_s
    disr_margin_s = rem_budget_s - disr_total_time_s
    disr_within_limit = disr_reachable and (disr_total_time_s <= rem_budget_s)

    disrupted_remaining_dict = {
        "is_reachable": disr_reachable,
        "is_within_limit": disr_within_limit,
        "distance_m": round(nom_dist_m, 2),
        "total_time_s": round(disr_total_time_s, 2),
        "traverse_time_s": round(disr_trav_s, 2),
        "dwell_time_s": round(nom_dwell_s, 2),
        "margin_s": round(disr_margin_s, 2),
        "blocked_cell_encounters": blocked_encounters,
        "stop_count": len(mid_state.unvisited_stops),
        "stop_ids": [w.id for w in mid_state.unvisited_stops],
        "path_rc": [list(pt) for pt in nom_candidate.path_rc],
    }

    # =========================================================================
    # STAGE 3: Adaptive Continuation Optimization
    # =========================================================================
    # Filter candidate waypoints: exclude unavailable targets and those inside blocked cells
    valid_candidate_wps: List[ScienceWaypoint] = []
    for w in mid_state.unvisited_stops:
        if w.id in unavailable_targets:
            continue
        if w.rc in blocked_cells_set:
            continue
        valid_candidate_wps.append(w)

    adaptive_sortie: Optional[SortieCandidate] = None

    # Available budget after immediate operational hold
    eff_adaptive_limit_s = max(0.0, rem_budget_s - operational_hold_s)

    if start_rc == goal_rc:
        # Rover already at destination
        adaptive_sortie = _evaluate_candidate_sortie(
            ordered_points=[start_rc, goal_rc],
            stop_waypoints=[],
            terrain=terrain,
            objective=SortieObjective.BALANCED,
            title="Sortie Completed",
            rationale="Rover has arrived at destination.",
            profile=profile,
            vehicle_mode=vehicle_mode,
            speed_multiplier=effective_speed_mult,
            operational_limit_s=rem_budget_s,
            operational_delay_s=operational_hold_s,
        )
    elif valid_candidate_wps:
        # Multi-stop science tour optimization from current position to goal
        try:
            opt_report = optimize_science_tour(
                start_rc=start_rc,
                goal_rc=goal_rc,
                terrain=terrain,
                candidate_waypoints=valid_candidate_wps,
                profile=profile,
                vehicle_mode=vehicle_mode,
                speed_multiplier=effective_speed_mult,
                operational_limit_s=eff_adaptive_limit_s,
                dwell_time_per_stop_s=900.0,
                operational_delay_s=operational_hold_s,
                max_stops=min(max_stops, len(valid_candidate_wps)),
                beam_width=beam_width,
                transform=transform,
                blocked_mask=scen_blocked_mask,
                cost_multiplier_mask=scen_cost_mask,
            )
            adaptive_sortie = opt_report.balanced_champion or opt_report.recommended_sortie or opt_report.direct_baseline
        except Exception:
            adaptive_sortie = None

    if adaptive_sortie is None or not adaptive_sortie.is_reachable:
        # Fall back to direct A* return from current position to destination
        adaptive_sortie = _evaluate_candidate_sortie(
            ordered_points=[start_rc, goal_rc],
            stop_waypoints=[],
            terrain=terrain,
            objective=SortieObjective.BALANCED,
            title="Direct Return to Destination",
            rationale="Direct return corridor avoiding contingency zone.",
            profile=profile,
            vehicle_mode=vehicle_mode,
            speed_multiplier=effective_speed_mult,
            operational_limit_s=rem_budget_s,
            operational_delay_s=operational_hold_s,
            blocked_mask=scen_blocked_mask,
            cost_multiplier_mask=scen_cost_mask,
        )

    adapt_visited_ids = adaptive_sortie.stop_ids
    orig_unvisited_ids = [w.id for w in mid_state.unvisited_stops]
    adapt_dropped_ids = [tid for tid in orig_unvisited_ids if tid not in adapt_visited_ids]

    adaptive_continuation_dict = {
        "is_reachable": adaptive_sortie.is_reachable,
        "is_within_limit": adaptive_sortie.is_budget_feasible,
        "distance_m": round(adaptive_sortie.distance_m, 2),
        "total_time_s": round(adaptive_sortie.total_mission_time_s, 2),
        "traverse_time_s": round(adaptive_sortie.travel_time_s, 2),
        "dwell_time_s": round(adaptive_sortie.dwell_time_s, 2),
        "margin_s": round(adaptive_sortie.time_margin_s if adaptive_sortie.time_margin_s is not None else (rem_budget_s - adaptive_sortie.total_mission_time_s), 2),
        "science_score": round(adaptive_sortie.science_score, 1),
        "visited_stop_ids": adapt_visited_ids,
        "dropped_stop_ids": adapt_dropped_ids,
        "path_rc": [list(pt) for pt in adaptive_sortie.path_rc],
    }

    # =========================================================================
    # RECOMMENDATION & RATIONALE
    # =========================================================================
    if not adaptive_sortie.is_reachable:
        recommendation = ReplanningRecommendation.UNRESOLVABLE_CRITICAL_HAZARD
        rec_title = "Critical Hazard: Unreachable Destination"
        rec_rationale = "The injected contingency completely blocks all feasible corridors from the rover's position to the destination. Operational abort and human assistance required."
    elif not adaptive_sortie.is_budget_feasible:
        recommendation = ReplanningRecommendation.ABORT_TO_DIRECT_BASELINE
        rec_title = "Direct Return: Budget Exceeded"
        rec_rationale = "Available time margin is insufficient to support science dwell; direct return route computed."
    elif len(adapt_visited_ids) == len(orig_unvisited_ids) and len(orig_unvisited_ids) > 0:
        if blocked_encounters > 0 or scen_cost_mask is not None:
            recommendation = ReplanningRecommendation.CONTINUE_WITH_DETOUR
            rec_title = "Continue with Detour: Objectives Preserved"
            rec_rationale = f"All {len(adapt_visited_ids)} remaining targets retained via a safe terrain detour bypassing the contingency zone."
        else:
            recommendation = ReplanningRecommendation.CONTINUE_WITH_DETOUR
            rec_title = "Continue Nominal Sortie"
            rec_rationale = "Injected event does not compromise remaining path; continue nominal itinerary."
    elif len(adapt_visited_ids) > 0 and len(adapt_dropped_ids) > 0:
        recommendation = ReplanningRecommendation.DROP_TARGET_AND_PROCEED
        rec_title = f"Drop {len(adapt_dropped_ids)} Target(s) and Proceed"
        dropped_str = ", ".join(adapt_dropped_ids)
        rec_rationale = f"Targets [{dropped_str}] omitted due to hazard proximity or operational limits; proceeding with {len(adapt_visited_ids)} priority stops."
    else:
        recommendation = ReplanningRecommendation.ABORT_TO_DIRECT_BASELINE
        rec_title = "Direct Safe Return"
        rec_rationale = "Remaining stops unavailable or omitted; direct route to goal confirmed feasible."

    # =========================================================================
    # SCIENCE RECOVERY METRICS
    # =========================================================================
    nom_priority = sum(w.priority_score for w in mid_state.unvisited_stops)
    adapt_priority = adaptive_sortie.science_score
    science_recovery = {
        "nominal_remaining_priority": round(nom_priority, 1),
        "adaptive_remaining_priority": round(adapt_priority, 1),
        "priority_delta": round(adapt_priority - nom_priority, 1),
        "retained_stop_count": len(adapt_visited_ids),
        "dropped_stop_count": len(adapt_dropped_ids),
    }

    # =========================================================================
    # CONTINUATION PLAYBACK MODEL GENERATION
    # =========================================================================
    continuation_route = {
        "profile": profile,
        "start_rc": list(start_rc),
        "goal_rc": list(goal_rc),
        "path": adaptive_sortie.path_rc,
        "distance_m": adaptive_sortie.distance_m,
        "cost": adaptive_sortie.terrain_cost,
        "is_reachable": adaptive_sortie.is_reachable,
    }

    continuation_wps = [
        w.to_dict() if hasattr(w, "to_dict") else {
            "id": w.id, "name": w.name, "rc": list(w.rc), "priority": w.priority_score, "dwell_time_s": getattr(w, "dwell_time_s", 900.0)
        }
        for w in valid_candidate_wps if w.id in adapt_visited_ids
    ]

    cont_id = f"cont_{uuid.uuid4().hex[:8]}"
    cont_model = build_mission_playback_model(
        route_data=continuation_route,
        terrain=terrain,
        vehicle_mode=vehicle_mode,
        mission_variant="adaptive",
        mission_id=cont_id,
        profile=profile,
        speed_multiplier=effective_speed_mult,
        waypoints=continuation_wps,
    )

    cont_playback_dict = cont_model.to_dict()
    cont_playback_dict["metadata"]["source_mission_id"] = mid_state.source_mission_id
    cont_playback_dict["metadata"]["interruption_time_s"] = mid_state.interruption_time_s
    cont_playback_dict["metadata"]["is_continuation"] = True
    cont_playback_dict["metadata"]["start_rc"] = list(start_rc)

    # Event summary formatting
    first_ev = parsed_events[0] if parsed_events else None
    ev_summary: Dict[str, Any] = {
        "event_type": first_ev.event_type.value if first_ev else "custom_contingency",
        "label": first_ev.name if first_ev else "Custom Contingency",
        "center_rc": list(first_ev.center_rc) if first_ev and first_ev.center_rc else None,
        "radius_m": first_ev.radius_m if first_ev else None,
        "speed_multiplier": first_ev.speed_multiplier if first_ev else None,
        "operational_delay_s": first_ev.operational_delay_s if first_ev else None,
        "unavailable_target_id": first_ev.unavailable_target_id if first_ev else None,
        "blocked_cells_count": len(blocked_cells_set) if blocked_cells_set else None,
    }

    exec_time_ms = (time.perf_counter() - t_start) * 1000.0

    return {
        "status": "success",
        "schema_version": "1.0.0",
        "continuation_id": cont_id,
        "source_mission_id": mid_state.source_mission_id,
        "interruption_time_s": round(mid_state.interruption_time_s, 2),
        "rover_state": {
            "rover_rc": list(mid_state.rover_rc),
            "rover_float_rc": [round(mid_state.rover_float_rc[0], 2), round(mid_state.rover_float_rc[1], 2)],
            "elevation_m": round(mid_state.elevation_m, 2),
            "slope_deg": round(mid_state.slope_deg, 2),
            "is_stationary": mid_state.is_stationary,
            "active_event_type": mid_state.active_event_type,
            "active_target_id": mid_state.active_target_id,
            "elapsed_distance_m": round(mid_state.elapsed_distance_m, 2),
            "original_budget_s": round(mid_state.original_budget_s, 2),
            "remaining_budget_s": round(mid_state.remaining_budget_s, 2),
            "completed_stop_ids": mid_state.completed_stop_ids,
            "unvisited_stop_ids": mid_state.unvisited_stop_ids,
        },
        "event_summary": ev_summary,
        "nominal_remaining": nominal_remaining_dict,
        "disrupted_remaining": disrupted_remaining_dict,
        "adaptive_continuation": adaptive_continuation_dict,
        "recommendation": recommendation.value,
        "recommendation_title": rec_title,
        "recommendation_rationale": rec_rationale,
        "science_recovery": science_recovery,
        "historical_prefix": {
            "elapsed_time_s": round(mid_state.interruption_time_s, 2),
            "elapsed_distance_m": round(mid_state.elapsed_distance_m, 2),
            "completed_stop_ids": mid_state.completed_stop_ids,
            "path_rc": [list(pt) for pt in mid_state.historical_path_rc],
        },
        "continuation_playback": cont_playback_dict,
        "disclosures": [
            "Modeled remaining sortie from captured mid-mission coordinates.",
            "Injected emergency is a simulated hypothetical event.",
            "Never presented as certified astronaut life-support envelopes or real Mars telemetry.",
        ],
        "execution_time_ms": round(exec_time_ms, 1),
    }
