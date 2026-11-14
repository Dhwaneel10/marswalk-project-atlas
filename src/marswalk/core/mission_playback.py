"""
MarsWalk 2.0 — Milestone 9Z: Mission Timeline Playback, Synchronized 3D Route Animation & Event Reconstruction.

Provides an authoritative, time-parameterized route trajectory reconstruction engine:
1. High-resolution discrete trajectory sampling along planned A* paths.
2. Directed slope-cost weighted step timing: steeper segments naturally demand more modeled time.
3. Rigorous stationary holds: marker coordinates remain pinned during scientific dwell and contingency delay periods while elapsed time advances.
4. Continuous spatial-temporal interpolation for any query scrub time t in [0, T_total].
5. Multi-variant playback isolation: independent playback state for Nominal Baseline, Disrupted Detour, and Adaptive Replacement missions.
6. JSON Schema Draft 2020-12 serialization compliant with NASA mission playback contracts.

SCIENTIFIC PRINCIPLES & GOVERNANCE:
- Modeled timelines represent calculated traversal times based on slope penalty functions and walking/driving speeds; they are not real-time telemetry from an active Mars mission.
- Traversal effort is reported in equivalent flat meters or calculated seconds, never as certified astronaut life-support envelopes.
- No synthetic data will be presented as primary observations.
"""

from dataclasses import dataclass, field, asdict
import bisect
import enum
import math
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np

from marswalk.core.terrain import (
    TerrainGrid,
    calculate_step_distance,
    calculate_edge_cost,
    get_profile_terrain_config,
)
from marswalk.core.planner import (
    RouteResult,
    LegResult,
    MissionTimeline,
    TimelineEvent,
    build_mission_timeline,
    calculate_traverse_time,
    format_duration,
    OPERATIONAL_LIMITS_S,
)


@dataclass
class PlaybackSample:
    """Discrete timestamped point along the route trajectory."""
    sample_index: int
    time_s: float
    rc: Tuple[float, float]
    elevation_m: float
    slope_deg: float
    cumulative_distance_m: float
    speed_m_s: float
    active_event_index: int
    event_type: str  # "start", "traverse_leg", "science_dwell", "scenario_delay", "arrival"
    target_id: Optional[str] = None
    is_stationary: bool = False
    leg_index: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_index": self.sample_index,
            "time_s": round(self.time_s, 2),
            "rc": [round(self.rc[0], 2), round(self.rc[1], 2)],
            "elevation_m": round(self.elevation_m, 2),
            "slope_deg": round(self.slope_deg, 2),
            "cumulative_distance_m": round(self.cumulative_distance_m, 2),
            "speed_m_s": round(self.speed_m_s, 3),
            "active_event_index": self.active_event_index,
            "event_type": self.event_type,
            "target_id": self.target_id,
            "is_stationary": self.is_stationary,
            "leg_index": self.leg_index,
        }


@dataclass
class PlaybackTimelineEvent:
    """Structured mission timeline interval with bounding coordinates and telemetry."""
    event_index: int
    event_id: str
    event_type: str  # "start", "traverse_leg", "science_dwell", "scenario_delay", "arrival"
    label: str
    target_id: Optional[str]
    leg_index: Optional[int]
    start_time_s: float
    end_time_s: float
    duration_s: float
    distance_m: float
    cumulative_distance_start_m: float
    cumulative_distance_end_m: float
    start_rc: Tuple[int, int]
    end_rc: Tuple[int, int]
    start_elevation_m: float
    end_elevation_m: float
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_index": self.event_index,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "label": self.label,
            "target_id": self.target_id,
            "leg_index": self.leg_index,
            "start_time_s": round(self.start_time_s, 2),
            "end_time_s": round(self.end_time_s, 2),
            "duration_s": round(self.duration_s, 2),
            "distance_m": round(self.distance_m, 2),
            "cumulative_distance_start_m": round(self.cumulative_distance_start_m, 2),
            "cumulative_distance_end_m": round(self.cumulative_distance_end_m, 2),
            "start_rc": list(self.start_rc),
            "end_rc": list(self.end_rc),
            "start_elevation_m": round(self.start_elevation_m, 2),
            "end_elevation_m": round(self.end_elevation_m, 2),
            "notes": self.notes,
        }


@dataclass
class MissionPlaybackModel:
    """Complete, self-contained playback model for a mission variant."""
    schema_version: str
    mission_id: Optional[str]
    mission_variant: str  # "nominal", "disrupted", "adaptive"
    vehicle_mode: str
    total_duration_s: float
    total_distance_m: float
    total_traverse_time_s: float
    total_dwell_time_s: float
    total_operational_delay_s: float
    remaining_margin_s: float
    is_within_limit: bool
    is_reachable: bool
    events: List[PlaybackTimelineEvent]
    samples: List[PlaybackSample]
    waypoints: List[Dict[str, Any]]
    telemetry_summary: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mission_id": self.mission_id,
            "mission_variant": self.mission_variant,
            "vehicle_mode": self.vehicle_mode,
            "total_duration_s": round(self.total_duration_s, 2),
            "total_distance_m": round(self.total_distance_m, 2),
            "total_traverse_time_s": round(self.total_traverse_time_s, 2),
            "total_dwell_time_s": round(self.total_dwell_time_s, 2),
            "total_operational_delay_s": round(self.total_operational_delay_s, 2),
            "remaining_margin_s": round(self.remaining_margin_s, 2),
            "is_within_limit": self.is_within_limit,
            "is_reachable": self.is_reachable,
            "formatted_total_duration": format_duration(self.total_duration_s),
            "formatted_total_distance": f"{round(self.total_distance_m, 1):,} m" if self.total_distance_m >= 1000 else f"{round(self.total_distance_m, 1)} m",
            "events": [e.to_dict() for e in self.events],
            "samples": [s.to_dict() for s in self.samples],
            "waypoints": self.waypoints,
            "telemetry_summary": self.telemetry_summary,
            "metadata": self.metadata,
        }


def build_mission_playback_model(
    route_data: Union[RouteResult, Dict[str, Any]],
    terrain: TerrainGrid,
    timeline: Optional[Union[MissionTimeline, Dict[str, Any]]] = None,
    vehicle_mode: str = "crew_eva",
    mission_variant: str = "nominal",
    mission_id: Optional[str] = None,
    profile: str = "conservative",
    speed_multiplier: float = 1.0,
    stop_labels: Optional[List[str]] = None,
    waypoints: Optional[List[Dict[str, Any]]] = None,
) -> MissionPlaybackModel:
    """
    Construct an authoritative MissionPlaybackModel with discrete time-stamped trajectory
    samples and synchronized operational events.

    Guarantees:
    1. Continuous monotonic time advancement.
    2. Exact stationary coordinate pinning during dwell and delay phases.
    3. Directed cost-weighted step speed and duration.
    4. Exact distance and duration totals matching route and timeline data.
    """
    # 1. Normalize route properties
    if isinstance(route_data, dict):
        raw_path = route_data.get("path") or route_data.get("path_rc") or []
        path_rc: List[Tuple[int, int]] = [tuple(p) for p in raw_path]  # type: ignore
        total_dist_m = float(route_data.get("distance_m", 0.0))
        total_cost = float(route_data.get("cost", 0.0))
        is_reachable = bool(route_data.get("is_reachable", True if path_rc else False))
        route_legs = route_data.get("legs", [])
        start_rc = tuple(route_data.get("start_rc", path_rc[0] if path_rc else (0, 0)))
        goal_rc = tuple(route_data.get("goal_rc", path_rc[-1] if path_rc else (0, 0)))
        route_timeline_raw = route_data.get("timeline")
    else:
        path_rc = route_data.path
        total_dist_m = float(route_data.distance_m)
        total_cost = float(route_data.cost)
        is_reachable = bool(route_data.is_reachable)
        route_legs = route_data.legs or []
        start_rc = route_data.start_rc
        goal_rc = route_data.goal_rc
        route_timeline_raw = getattr(route_data, "timeline", None)

    # 2. Extract or build timeline
    if timeline is not None:
        active_timeline = timeline
    elif route_timeline_raw is not None:
        active_timeline = route_timeline_raw
    else:
        # Build synthetic timeline using planner
        temp_route = RouteResult(
            profile=profile,
            start_rc=start_rc,  # type: ignore
            goal_rc=goal_rc,    # type: ignore
            path=path_rc,
            distance_m=total_dist_m,
            cost=total_cost,
            science_score=0.0,
            visited_waypoint_ids=[],
            num_cells=len(path_rc),
            num_steps=max(0, len(path_rc) - 1),
            is_reachable=is_reachable,
            is_budget_feasible=True,
            max_distance_m=None,
            status_message="Playback route",
            legs=route_legs if route_legs else None,  # type: ignore
        )
        active_timeline = build_mission_timeline(
            temp_route,
            vehicle_mode=vehicle_mode,
            speed_multiplier=speed_multiplier,
            stop_labels=stop_labels,
        )

    # Extract timeline details
    if isinstance(active_timeline, MissionTimeline):
        tl_events = active_timeline.events
        t_trav = active_timeline.total_traverse_time_s
        t_dwell = active_timeline.total_dwell_time_s
        t_delay = active_timeline.total_operational_delay_s
        t_total = active_timeline.total_mission_time_s
        t_margin = active_timeline.remaining_margin_s
        is_within_limit = active_timeline.is_within_limit
        v_mode = active_timeline.vehicle_mode
    elif isinstance(active_timeline, dict):
        raw_events = active_timeline.get("events", [])
        tl_events = []
        for re in raw_events:
            tl_events.append(
                TimelineEvent(
                    event_type=re.get("event_type", "traverse_leg"),
                    label=re.get("label", ""),
                    target_id=re.get("target_id"),
                    leg_index=re.get("leg_index"),
                    start_time_s=float(re.get("start_time_s", 0.0)),
                    end_time_s=float(re.get("end_time_s", 0.0)),
                    duration_s=float(re.get("duration_s", 0.0)),
                    distance_m=float(re.get("distance_m", 0.0)),
                    formatted_duration=re.get("formatted_duration", ""),
                    formatted_cumulative_time=re.get("formatted_cumulative_time", ""),
                    notes=re.get("notes", ""),
                )
            )
        t_trav = float(active_timeline.get("total_traverse_time_s", 0.0))
        t_dwell = float(active_timeline.get("total_dwell_time_s", 0.0))
        t_delay = float(active_timeline.get("total_operational_delay_s", 0.0))
        t_total = float(active_timeline.get("total_mission_time_s", t_trav + t_dwell + t_delay))
        limit_s = OPERATIONAL_LIMITS_S.get(vehicle_mode, 8.0 * 3600.0)
        t_margin = float(active_timeline.get("remaining_margin_s", limit_s - t_total))
        is_within_limit = bool(active_timeline.get("is_within_limit", t_total <= limit_s))
        v_mode = str(active_timeline.get("vehicle_mode", vehicle_mode))
    else:
        tl_events = []
        t_trav = 0.0
        t_dwell = 0.0
        t_delay = 0.0
        t_total = 0.0
        t_margin = 0.0
        is_within_limit = True
        v_mode = vehicle_mode

    # 3. Resolve legs & paths
    # Partition path_rc into legs if legs not explicitly provided
    resolved_legs: List[Dict[str, Any]] = []
    if route_legs:
        for leg in route_legs:
            if isinstance(leg, dict):
                resolved_legs.append(leg)
            else:
                resolved_legs.append({
                    "start_rc": leg.start_rc,
                    "goal_rc": leg.goal_rc,
                    "path": leg.path,
                    "distance_m": leg.distance_m,
                    "cost": leg.cost,
                    "is_reachable": leg.is_reachable,
                })
    else:
        # Fallback: single leg with entire path
        resolved_legs.append({
            "start_rc": start_rc,
            "goal_rc": goal_rc,
            "path": path_rc,
            "distance_m": total_dist_m,
            "cost": total_cost,
            "is_reachable": is_reachable,
        })

    # Prepare terrain config for step costs
    t_cfg = get_profile_terrain_config(profile)

    # 4. Build Structured Playback Timeline Events & Samples
    playback_events: List[PlaybackTimelineEvent] = []
    samples: List[PlaybackSample] = []
    sample_index = 0
    cum_dist_m = 0.0

    # Quick helper for elevation & slope safe lookup
    def get_elev_slope(r: int, c: int) -> Tuple[float, float]:
        n_rows, n_cols = terrain.shape
        r_c = max(0, min(n_rows - 1, int(round(r))))
        c_c = max(0, min(n_cols - 1, int(round(c))))
        elev = float(terrain.elevation[r_c, c_c])
        if math.isnan(elev) or math.isinf(elev) or elev < -10000.0:
            elev = 0.0
        slope = float(terrain.slope_deg[r_c, c_c]) if hasattr(terrain, "slope_deg") else 0.0
        return elev, slope

    # Handle unreachable or empty route case
    if not is_reachable or not path_rc:
        start_elev, start_slope = get_elev_slope(start_rc[0], start_rc[1])
        empty_sample = PlaybackSample(
            sample_index=0,
            time_s=0.0,
            rc=(float(start_rc[0]), float(start_rc[1])),
            elevation_m=start_elev,
            slope_deg=start_slope,
            cumulative_distance_m=0.0,
            speed_m_s=0.0,
            active_event_index=0,
            event_type="start",
            is_stationary=True,
        )
        return MissionPlaybackModel(
            schema_version="1.0.0",
            mission_id=mission_id,
            mission_variant=mission_variant,
            vehicle_mode=v_mode,
            total_duration_s=t_total,
            total_distance_m=0.0,
            total_traverse_time_s=0.0,
            total_dwell_time_s=t_dwell,
            total_operational_delay_s=t_delay,
            remaining_margin_s=t_margin,
            is_within_limit=is_within_limit,
            is_reachable=False,
            events=[],
            samples=[empty_sample],
            waypoints=waypoints or [],
            telemetry_summary={
                "min_elevation_m": start_elev,
                "max_elevation_m": start_elev,
                "max_slope_deg": start_slope,
                "avg_speed_m_s": 0.0,
            },
            metadata={"notes": "Mission route is unreachable or empty."},
        )

    def get_leg_data(l_idx: Optional[int]) -> Optional[Dict[str, Any]]:
        if not resolved_legs:
            return None
        if l_idx is None:
            return resolved_legs[0]
        # In MarsWalk timeline events, leg_index is 1-indexed (Leg 1 = leg_index 1 -> index 0)
        if 1 <= l_idx <= len(resolved_legs):
            return resolved_legs[l_idx - 1]
        # Fallback for 0-indexed calls
        if 0 <= l_idx < len(resolved_legs):
            return resolved_legs[l_idx]
        return resolved_legs[-1]

    # 5. Process Timeline Events Sequentially
    for evt_idx, evt in enumerate(tl_events):
        e_type = evt.event_type
        leg_idx = evt.leg_index
        leg_data = get_leg_data(leg_idx)

        # Event coordinates
        if e_type == "start":
            s_rc = start_rc
            e_rc = start_rc
            e_dist = 0.0
        elif e_type == "traverse_leg" and leg_data is not None:
            s_rc = tuple(leg_data.get("start_rc", (0, 0)))
            e_rc = tuple(leg_data.get("goal_rc", (0, 0)))
            e_dist = float(leg_data.get("distance_m", evt.distance_m))
        elif e_type in ("science_dwell", "scenario_delay"):
            # Pin to end of previous leg or start
            if leg_data is not None:
                s_rc = tuple(leg_data.get("goal_rc", (0, 0)))
            elif samples:
                last_sample = samples[-1]
                s_rc = (int(round(last_sample.rc[0])), int(round(last_sample.rc[1])))
            else:
                s_rc = start_rc
            e_rc = s_rc
            e_dist = 0.0
        elif e_type == "arrival":
            s_rc = goal_rc
            e_rc = goal_rc
            e_dist = 0.0
        else:
            s_rc = start_rc
            e_rc = goal_rc
            e_dist = evt.distance_m

        s_elev, _ = get_elev_slope(s_rc[0], s_rc[1])
        e_elev, _ = get_elev_slope(e_rc[0], e_rc[1])

        p_evt = PlaybackTimelineEvent(
            event_index=evt_idx,
            event_id=f"evt-{evt_idx}-{e_type}",
            event_type=e_type,
            label=evt.label,
            target_id=evt.target_id,
            leg_index=leg_idx,
            start_time_s=evt.start_time_s,
            end_time_s=evt.end_time_s,
            duration_s=evt.duration_s,
            distance_m=e_dist,
            cumulative_distance_start_m=cum_dist_m,
            cumulative_distance_end_m=cum_dist_m + e_dist,
            start_rc=s_rc,
            end_rc=e_rc,
            start_elevation_m=s_elev,
            end_elevation_m=e_elev,
            notes=evt.notes,
        )
        playback_events.append(p_evt)

        # 6. Generate Discrete Samples for this Event
        if e_type == "start":
            elev, slope = get_elev_slope(s_rc[0], s_rc[1])
            samples.append(
                PlaybackSample(
                    sample_index=sample_index,
                    time_s=evt.start_time_s,
                    rc=(float(s_rc[0]), float(s_rc[1])),
                    elevation_m=elev,
                    slope_deg=slope,
                    cumulative_distance_m=cum_dist_m,
                    speed_m_s=0.0,
                    active_event_index=evt_idx,
                    event_type=e_type,
                    is_stationary=True,
                )
            )
            sample_index += 1

        elif e_type == "traverse_leg" and leg_data is not None:
            leg_path = [tuple(p) for p in leg_data.get("path", [])]
            leg_duration_s = max(0.001, evt.duration_s)
            
            if len(leg_path) <= 1:
                # Trivial single-cell leg
                elev, slope = get_elev_slope(s_rc[0], s_rc[1])
                samples.append(
                    PlaybackSample(
                        sample_index=sample_index,
                        time_s=evt.end_time_s,
                        rc=(float(s_rc[0]), float(s_rc[1])),
                        elevation_m=elev,
                        slope_deg=slope,
                        cumulative_distance_m=cum_dist_m,
                        speed_m_s=0.0,
                        active_event_index=evt_idx,
                        event_type=e_type,
                        leg_index=leg_idx,
                        is_stationary=False,
                    )
                )
                sample_index += 1
            else:
                # Calculate directed step costs and ground distances for each edge
                edge_costs: List[float] = []
                edge_dists: List[float] = []
                for k in range(len(leg_path) - 1):
                    p0 = leg_path[k]
                    p1 = leg_path[k + 1]
                    d_step = calculate_step_distance(p0, p1, terrain.dx_ground_m, terrain.dy_ground_m)
                    c_step = calculate_edge_cost(p0, p1, terrain, t_cfg)
                    edge_costs.append(c_step)
                    edge_dists.append(d_step)

                total_leg_cost = sum(edge_costs)
                total_leg_calc_dist = sum(edge_dists)

                # Time allocation per edge
                edge_durations: List[float] = []
                for k in range(len(edge_costs)):
                    if total_leg_cost > 0.0:
                        dur = (edge_costs[k] / total_leg_cost) * leg_duration_s
                    elif total_leg_calc_dist > 0.0:
                        dur = (edge_dists[k] / total_leg_calc_dist) * leg_duration_s
                    else:
                        dur = leg_duration_s / len(edge_costs)
                    edge_durations.append(dur)

                # Ensure exact sum conservation
                dur_sum = sum(edge_durations)
                if dur_sum > 0.0 and abs(dur_sum - leg_duration_s) > 1e-4:
                    scale = leg_duration_s / dur_sum
                    edge_durations = [d * scale for d in edge_durations]

                # Generate samples along leg path
                t_current = evt.start_time_s
                for k in range(1, len(leg_path)):
                    p_k = leg_path[k]
                    step_dt = edge_durations[k - 1]
                    step_dx = edge_dists[k - 1]
                    t_current += step_dt
                    cum_dist_m += step_dx
                    elev, slope = get_elev_slope(p_k[0], p_k[1])
                    v_instant = step_dx / max(0.001, step_dt)

                    samples.append(
                        PlaybackSample(
                            sample_index=sample_index,
                            time_s=t_current,
                            rc=(float(p_k[0]), float(p_k[1])),
                            elevation_m=elev,
                            slope_deg=slope,
                            cumulative_distance_m=cum_dist_m,
                            speed_m_s=v_instant,
                            active_event_index=evt_idx,
                            event_type=e_type,
                            leg_index=leg_idx,
                            is_stationary=False,
                        )
                    )
                    sample_index += 1

        elif e_type in ("science_dwell", "scenario_delay"):
            elev, slope = get_elev_slope(s_rc[0], s_rc[1])
            # Beginning of dwell/delay
            samples.append(
                PlaybackSample(
                    sample_index=sample_index,
                    time_s=evt.start_time_s,
                    rc=(float(s_rc[0]), float(s_rc[1])),
                    elevation_m=elev,
                    slope_deg=slope,
                    cumulative_distance_m=cum_dist_m,
                    speed_m_s=0.0,
                    active_event_index=evt_idx,
                    event_type=e_type,
                    target_id=evt.target_id,
                    is_stationary=True,
                    leg_index=leg_idx,
                )
            )
            sample_index += 1

            # End of dwell/delay
            if evt.duration_s > 0:
                samples.append(
                    PlaybackSample(
                        sample_index=sample_index,
                        time_s=evt.end_time_s,
                        rc=(float(s_rc[0]), float(s_rc[1])),
                        elevation_m=elev,
                        slope_deg=slope,
                        cumulative_distance_m=cum_dist_m,
                        speed_m_s=0.0,
                        active_event_index=evt_idx,
                        event_type=e_type,
                        target_id=evt.target_id,
                        is_stationary=True,
                        leg_index=leg_idx,
                    )
                )
                sample_index += 1

        elif e_type == "arrival":
            elev, slope = get_elev_slope(goal_rc[0], goal_rc[1])
            samples.append(
                PlaybackSample(
                    sample_index=sample_index,
                    time_s=evt.end_time_s,
                    rc=(float(goal_rc[0]), float(goal_rc[1])),
                    elevation_m=elev,
                    slope_deg=slope,
                    cumulative_distance_m=cum_dist_m,
                    speed_m_s=0.0,
                    active_event_index=evt_idx,
                    event_type=e_type,
                    is_stationary=True,
                )
            )
            sample_index += 1

    # 7. Summary Telemetry
    all_elevations = [s.elevation_m for s in samples] if samples else [0.0]
    all_slopes = [s.slope_deg for s in samples] if samples else [0.0]
    moving_speeds = [s.speed_m_s for s in samples if not s.is_stationary]
    avg_speed = float(np.mean(moving_speeds)) if moving_speeds else 0.0

    telemetry_summary = {
        "min_elevation_m": round(float(np.min(all_elevations)), 2),
        "max_elevation_m": round(float(np.max(all_elevations)), 2),
        "elevation_delta_m": round(float(np.max(all_elevations) - np.min(all_elevations)), 2),
        "max_slope_deg": round(float(np.max(all_slopes)), 2),
        "avg_speed_m_s": round(avg_speed, 3),
        "avg_speed_kmh": round(avg_speed * 3.6, 2),
        "sample_count": len(samples),
        "event_count": len(playback_events),
    }

    metadata = {
        "profile": profile,
        "speed_multiplier": speed_multiplier,
        "mission_variant": mission_variant,
        "temporal_resolution_notes": "Directed slope cost-weighted edge timing with stationary dwell/delay holding.",
    }

    return MissionPlaybackModel(
        schema_version="1.0.0",
        mission_id=mission_id,
        mission_variant=mission_variant,
        vehicle_mode=v_mode,
        total_duration_s=t_total,
        total_distance_m=cum_dist_m if cum_dist_m > 0 else total_dist_m,
        total_traverse_time_s=t_trav,
        total_dwell_time_s=t_dwell,
        total_operational_delay_s=t_delay,
        remaining_margin_s=t_margin,
        is_within_limit=is_within_limit,
        is_reachable=is_reachable,
        events=playback_events,
        samples=samples,
        waypoints=waypoints or [],
        telemetry_summary=telemetry_summary,
        metadata=metadata,
    )


def interpolate_playback_state(
    model: MissionPlaybackModel,
    query_time_s: float,
) -> Dict[str, Any]:
    """
    Interpolate instantaneous vehicle state at an arbitrary mission time t.

    Handles:
    - Boundary clamping at t <= 0 and t >= T_total.
    - Exact stationary holds during science dwell and scenario delay.
    - Continuous linear coordinate, elevation, and distance interpolation during transit.
    - Precise event resolution and progress ratios.
    """
    if not model.samples:
        return {
            "time_s": 0.0,
            "rc": [0.0, 0.0],
            "elevation_m": 0.0,
            "slope_deg": 0.0,
            "cumulative_distance_m": 0.0,
            "speed_m_s": 0.0,
            "is_stationary": True,
            "progress_ratio": 0.0,
            "active_event": None,
        }

    # Clamp query time
    t = max(0.0, min(float(query_time_s), model.total_duration_s))
    progress_ratio = 1.0 if model.total_duration_s <= 0 else t / model.total_duration_s

    # Find active event
    active_event_dict = None
    for evt in model.events:
        if evt.start_time_s <= t <= evt.end_time_s:
            active_event_dict = evt.to_dict()
            break
    if active_event_dict is None and model.events:
        if t <= model.events[0].start_time_s:
            active_event_dict = model.events[0].to_dict()
        else:
            active_event_dict = model.events[-1].to_dict()

    sample_times = [s.time_s for s in model.samples]

    # Binary search for interval
    idx = bisect.bisect_right(sample_times, t) - 1
    idx = max(0, min(idx, len(model.samples) - 1))

    # At exact boundaries or last sample
    if idx >= len(model.samples) - 1 or sample_times[idx] >= t:
        s = model.samples[idx]
        return {
            "time_s": round(t, 2),
            "rc": [round(s.rc[0], 2), round(s.rc[1], 2)],
            "elevation_m": round(s.elevation_m, 2),
            "slope_deg": round(s.slope_deg, 2),
            "cumulative_distance_m": round(s.cumulative_distance_m, 2),
            "speed_m_s": round(s.speed_m_s, 3),
            "is_stationary": s.is_stationary,
            "active_event_index": s.active_event_index,
            "event_type": s.event_type,
            "target_id": s.target_id,
            "leg_index": s.leg_index,
            "progress_ratio": round(progress_ratio, 4),
            "active_event": active_event_dict,
        }

    s0 = model.samples[idx]
    s1 = model.samples[idx + 1]

    # Check if stationary interval
    if s0.is_stationary and s1.is_stationary and s0.rc == s1.rc:
        return {
            "time_s": round(t, 2),
            "rc": [round(s0.rc[0], 2), round(s0.rc[1], 2)],
            "elevation_m": round(s0.elevation_m, 2),
            "slope_deg": round(s0.slope_deg, 2),
            "cumulative_distance_m": round(s0.cumulative_distance_m, 2),
            "speed_m_s": 0.0,
            "is_stationary": True,
            "active_event_index": s0.active_event_index,
            "event_type": s0.event_type,
            "target_id": s0.target_id,
            "leg_index": s0.leg_index,
            "progress_ratio": round(progress_ratio, 4),
            "active_event": active_event_dict,
        }

    # Interpolate along interval
    dt = s1.time_s - s0.time_s
    u = 0.0 if dt <= 0.0 else (t - s0.time_s) / dt
    u = max(0.0, min(1.0, u))

    interp_r = s0.rc[0] + u * (s1.rc[0] - s0.rc[0])
    interp_c = s0.rc[1] + u * (s1.rc[1] - s0.rc[1])
    interp_elev = s0.elevation_m + u * (s1.elevation_m - s0.elevation_m)
    interp_dist = s0.cumulative_distance_m + u * (s1.cumulative_distance_m - s0.cumulative_distance_m)
    interp_slope = s0.slope_deg + u * (s1.slope_deg - s0.slope_deg)
    speed = s1.speed_m_s

    return {
        "time_s": round(t, 2),
        "rc": [round(interp_r, 2), round(interp_c, 2)],
        "elevation_m": round(interp_elev, 2),
        "slope_deg": round(interp_slope, 2),
        "cumulative_distance_m": round(interp_dist, 2),
        "speed_m_s": round(speed, 3),
        "is_stationary": False,
        "active_event_index": s1.active_event_index,
        "event_type": s1.event_type,
        "target_id": s1.target_id,
        "leg_index": s1.leg_index,
        "progress_ratio": round(progress_ratio, 4),
        "active_event": active_event_dict,
    }
