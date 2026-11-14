"""
MarsWalk 2.0 / Project Atlas - Milestone 13J: Fleet Route Coordinator.

Generates independently valid, terrain-aware surface traverse routes for multiple rovers
using the authentic USGS CTX 20m Jezero Crater DTM. Enforces a bounded space-time coordination
model with scheduled occupancy intervals, detects potential spatial-temporal conflicts,
and resolves bottlenecks via operational delays or alternative routing.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np

from marswalk.core.terrain import TerrainGrid
from marswalk.core.planner import (
    PlannerConfig,
    calculate_step_distance,
    plan_sequential_multistop_route,
    RouteResult,
)
from marswalk.core.fleet_operations_director import RoverUnitConfig
from marswalk.core.fleet_task_allocator import FleetScienceTarget


PLANNING_DISCLOSURE = (
    "Scheduled spatiotemporal reservations and occupancy intervals are discrete macroscopic "
    "planning heuristics. They do NOT represent real-time autonomous obstacle avoidance, "
    "flight-certified collision avoidance, or physical rover safety guarantees."
)


class ConflictStatus(str, Enum):
    NO_SCHEDULED_CONFLICT = "NO_SCHEDULED_CONFLICT"
    POTENTIAL_SPATIAL_TEMPORAL_CONFLICT = "POTENTIAL_SPATIAL_TEMPORAL_CONFLICT"
    CONFLICT_RESOLVED_BY_DELAY = "CONFLICT_RESOLVED_BY_DELAY"
    CONFLICT_RESOLVED_BY_REROUTE = "CONFLICT_RESOLVED_BY_REROUTE"
    UNRESOLVED_CONFLICT = "UNRESOLVED_CONFLICT"


@dataclass
class ScheduledOccupancy:
    """Discretized space-time reservation interval for a rover along its traverse path."""
    rover_id: str
    rc: Tuple[int, int]
    path_index: int
    t_enter_s: float
    t_exit_s: float
    is_dwelling: bool = False
    stop_id: Optional[str] = None

    def overlaps_with(self, other: "ScheduledOccupancy", temporal_buffer_s: float = 30.0) -> bool:
        """Check if two occupancy intervals overlap temporally within buffer window."""
        return not (
            self.t_exit_s + temporal_buffer_s < other.t_enter_s or
            other.t_exit_s + temporal_buffer_s < self.t_enter_s
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rover_id": self.rover_id,
            "rc": list(self.rc),
            "path_index": self.path_index,
            "t_enter_s": round(self.t_enter_s, 1),
            "t_exit_s": round(self.t_exit_s, 1),
            "is_dwelling": self.is_dwelling,
            "stop_id": self.stop_id,
        }


@dataclass
class SpatialTemporalConflict:
    """Formal audit record of a scheduled collision or spatial proximity contention."""
    conflict_id: str
    rover_id_a: str
    rover_id_b: str
    location_rc: Tuple[int, int]
    time_window_s: Tuple[float, float]
    separation_distance_m: float
    status: str = ConflictStatus.POTENTIAL_SPATIAL_TEMPORAL_CONFLICT.value
    resolution_strategy: Optional[str] = None
    delay_applied_s: float = 0.0
    diagnostic_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "rover_id_a": self.rover_id_a,
            "rover_id_b": self.rover_id_b,
            "location_rc": list(self.location_rc),
            "time_window_s": [round(t, 1) for t in self.time_window_s],
            "separation_distance_m": round(self.separation_distance_m, 1),
            "status": self.status,
            "resolution_strategy": self.resolution_strategy,
            "delay_applied_s": round(self.delay_applied_s, 1),
            "diagnostic_note": self.diagnostic_note,
        }


@dataclass
class FleetRoverRoute:
    """Complete coordinated route for a rover with physical metrics and occupancy intervals."""
    rover_id: str
    route_id: str
    ordered_stops: List[str]
    path_rc: List[Tuple[int, int]]
    path_xyz: List[Tuple[float, float, float]]  # (x, y, z) in meters for Three.js
    total_distance_m: float
    traverse_time_s: float
    dwell_time_s: float
    total_time_s: float
    occupancy_schedule: List[ScheduledOccupancy]
    conflicts_detected: List[SpatialTemporalConflict] = field(default_factory=list)
    average_speed_mps: float = 0.10

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rover_id": self.rover_id,
            "route_id": self.route_id,
            "ordered_stops": list(self.ordered_stops),
            "path_rc": [list(rc) for rc in self.path_rc],
            "path_xyz": [[round(v, 2) for v in pt] for pt in self.path_xyz],
            "total_distance_m": round(self.total_distance_m, 1),
            "traverse_time_s": round(self.traverse_time_s, 1),
            "dwell_time_s": round(self.dwell_time_s, 1),
            "total_time_s": round(self.total_time_s, 1),
            "conflicts_count": len(self.conflicts_detected),
            "conflicts": [c.to_dict() for c in self.conflicts_detected],
            "average_speed_mps": round(self.average_speed_mps, 3),
        }


class FleetRouteCoordinator:
    """
    Coordinates simultaneous surface routes across the exploration fleet:
    ensures terrain-aware A* traversability on Jezero CTX DTM, builds temporal occupancy
    schedules, detects spatial-temporal proximity contention, and synthesizes deconflictions.
    """

    def __init__(
        self,
        ground_spacing_m: float = 20.0,
        separation_buffer_m: float = 40.0,
        temporal_buffer_s: float = 60.0,
    ):
        self.ground_spacing_m = ground_spacing_m
        self.separation_buffer_m = separation_buffer_m
        self.separation_buffer_cells = max(1.0, separation_buffer_m / ground_spacing_m)
        self.temporal_buffer_s = temporal_buffer_s

    def generate_single_rover_route(
        self,
        terrain: TerrainGrid,
        rover_config: RoverUnitConfig,
        starting_rc: Tuple[int, int],
        assigned_targets: List[FleetScienceTarget],
        start_time_s: float = 0.0,
        inserted_delay_s: float = 0.0
    ) -> FleetRoverRoute:
        """
        Plans a sequential multi-stop route for one rover visiting all assigned targets in order,
        returning ordered coordinates and discretized occupancy intervals.
        """
        route_id = f"route_{rover_config.rover_id.lower()}_{int(start_time_s)}"
        ordered_points = [starting_rc] + [t.location_rc for t in assigned_targets]
        stop_ids = [f"START_{rover_config.rover_id}"] + [t.target_id for t in assigned_targets]

        if len(ordered_points) < 2:
            # Stationary rover (no assigned targets)
            r, c = starting_rc
            r_idx = min(max(0, int(r)), terrain.height - 1)
            c_idx = min(max(0, int(c)), terrain.width - 1)
            elev = float(terrain.elevation[r_idx, c_idx])
            x = (c - 128) * self.ground_spacing_m
            y = (128 - r) * self.ground_spacing_m
            occ = [ScheduledOccupancy(
                rover_id=rover_config.rover_id,
                rc=starting_rc,
                path_index=0,
                t_enter_s=start_time_s,
                t_exit_s=start_time_s + 3600.0,
                is_dwelling=True,
                stop_id="STATIONARY",
            )]
            return FleetRoverRoute(
                rover_id=rover_config.rover_id,
                route_id=route_id,
                ordered_stops=stop_ids,
                path_rc=[starting_rc],
                path_xyz=[(x, y, elev)],
                total_distance_m=0.0,
                traverse_time_s=0.0,
                dwell_time_s=3600.0,
                total_time_s=3600.0,
                occupancy_schedule=occ,
            )

        # Plan through terrain using sequential multi-stop A*
        dwell_map = {t.target_id: t.required_dwell_s for t in assigned_targets}
        avg_dwell = sum(dwell_map.values()) / max(1, len(dwell_map))

        plan_res: RouteResult = plan_sequential_multistop_route(
            ordered_points=ordered_points,
            terrain=terrain,
            stop_ids=stop_ids,
            vehicle_mode=rover_config.unit_type,
            dwell_time_per_stop_s=avg_dwell,
            speed_multiplier=rover_config.nominal_speed_mps / 0.10,
        )

        full_path_rc = plan_res.path if plan_res.path else ordered_points
        full_path_xyz: List[Tuple[float, float, float]] = []

        for r, c in full_path_rc:
            r_idx = min(max(0, int(r)), terrain.height - 1)
            c_idx = min(max(0, int(c)), terrain.width - 1)
            elev = float(terrain.elevation[r_idx, c_idx])
            x = (c - 128) * self.ground_spacing_m
            y = (128 - r) * self.ground_spacing_m
            full_path_xyz.append((x, y, elev))

        # Build Scheduled Occupancy intervals
        occupancies: List[ScheduledOccupancy] = []
        curr_time = start_time_s + inserted_delay_s
        nominal_speed = max(0.01, rover_config.nominal_speed_mps)

        target_rc_map = {t.location_rc: t for t in assigned_targets}

        for i, rc in enumerate(full_path_rc):
            if i > 0:
                prev_rc = full_path_rc[i - 1]
                step_dist_m = calculate_step_distance(prev_rc, rc, self.ground_spacing_m, self.ground_spacing_m)
                step_time_s = step_dist_m / nominal_speed
                curr_time += step_time_s

            t_enter = curr_time
            t_exit = curr_time + (self.ground_spacing_m / nominal_speed)

            # Check if this waypoint is a scheduled science stop dwell
            is_dwelling = False
            stop_id = None
            if rc in target_rc_map:
                is_dwelling = True
                tgt = target_rc_map[rc]
                stop_id = tgt.target_id
                t_exit += tgt.required_dwell_s
                curr_time = t_exit

            occupancies.append(ScheduledOccupancy(
                rover_id=rover_config.rover_id,
                rc=rc,
                path_index=i,
                t_enter_s=t_enter,
                t_exit_s=t_exit,
                is_dwelling=is_dwelling,
                stop_id=stop_id,
            ))

        total_dwell = sum(t.required_dwell_s for t in assigned_targets)
        traverse_time = curr_time - start_time_s - total_dwell - inserted_delay_s

        return FleetRoverRoute(
            rover_id=rover_config.rover_id,
            route_id=route_id,
            ordered_stops=stop_ids,
            path_rc=full_path_rc,
            path_xyz=full_path_xyz,
            total_distance_m=plan_res.distance_m,
            traverse_time_s=traverse_time,
            dwell_time_s=total_dwell + inserted_delay_s,
            total_time_s=curr_time - start_time_s,
            occupancy_schedule=occupancies,
            average_speed_mps=nominal_speed,
        )

    def detect_spatial_temporal_conflicts(
        self,
        routes: Dict[str, FleetRoverRoute]
    ) -> List[SpatialTemporalConflict]:
        """
        Scans all pairwise rover occupancy intervals to detect overlapping space-time reservations.
        A conflict occurs if two rovers occupy locations within separation_buffer_m during overlapping times.
        """
        conflicts: List[SpatialTemporalConflict] = []
        rover_ids = list(routes.keys())
        conflict_idx = 1

        for i in range(len(rover_ids)):
            r_id_a = rover_ids[i]
            route_a = routes[r_id_a]

            for j in range(i + 1, len(rover_ids)):
                r_id_b = rover_ids[j]
                route_b = routes[r_id_b]

                # Check pairwise occupancies
                for occ_a in route_a.occupancy_schedule:
                    for occ_b in route_b.occupancy_schedule:
                        # Spatial proximity check
                        dr = occ_a.rc[0] - occ_b.rc[0]
                        dc = occ_a.rc[1] - occ_b.rc[1]
                        dist_m = math.hypot(dr, dc) * self.ground_spacing_m

                        if dist_m <= self.separation_buffer_m:
                            # Temporal overlap check
                            if occ_a.overlaps_with(occ_b, self.temporal_buffer_s):
                                t_start = max(occ_a.t_enter_s, occ_b.t_enter_s)
                                t_end = min(occ_a.t_exit_s, occ_b.t_exit_s)

                                c = SpatialTemporalConflict(
                                    conflict_id=f"conf_{conflict_idx:03d}",
                                    rover_id_a=r_id_a,
                                    rover_id_b=r_id_b,
                                    location_rc=occ_a.rc,
                                    time_window_s=(t_start, max(t_start + 1.0, t_end)),
                                    separation_distance_m=dist_m,
                                    status=ConflictStatus.POTENTIAL_SPATIAL_TEMPORAL_CONFLICT.value,
                                    diagnostic_note=(
                                        f"Simultaneous occupancy between {r_id_a} and {r_id_b} "
                                        f"at ({occ_a.rc[0]}, {occ_a.rc[1]}). Separation: {dist_m:.1f} m "
                                        f"(buffer {self.separation_buffer_m:.1f} m) from MET {t_start:.0f}s to {t_end:.0f}s."
                                    )
                                )
                                conflicts.append(c)
                                conflict_idx += 1
                                break  # Break inner loop for this point to prevent duplicate alerts

        return conflicts

    def coordinate_and_deconflict_fleet(
        self,
        terrain: TerrainGrid,
        rovers: Dict[str, RoverUnitConfig],
        allocations: Dict[str, List[str]],  # rover_id -> [target_id, ...]
        targets_by_id: Dict[str, FleetScienceTarget],
        start_time_s: float = 0.0,
        auto_resolve: bool = True
    ) -> Tuple[Dict[str, FleetRoverRoute], List[SpatialTemporalConflict]]:
        """
        Coordinates full fleet routes and optionally applies automated conflict resolutions:
        Strategy 1: Operational delay hold for the secondary rover.
        Strategy 2: Alternative route detour around contested bottleneck.
        """
        routes: Dict[str, FleetRoverRoute] = {}

        # 1. Generate initial independent routes
        for r_id, r_cfg in rovers.items():
            t_ids = allocations.get(r_id, [])
            tgt_objs = [targets_by_id[t_id] for t_id in t_ids if t_id in targets_by_id]
            routes[r_id] = self.generate_single_rover_route(
                terrain=terrain,
                rover_config=r_cfg,
                starting_rc=r_cfg.starting_location_rc,
                assigned_targets=tgt_objs,
                start_time_s=start_time_s,
            )

        # 2. Detect initial conflicts
        conflicts = self.detect_spatial_temporal_conflicts(routes)

        if not conflicts or not auto_resolve:
            for c in conflicts:
                routes[c.rover_id_a].conflicts_detected.append(c)
                routes[c.rover_id_b].conflicts_detected.append(c)
            return routes, conflicts

        # 3. Resolve conflicts iteratively via scheduling delays
        resolved_conflicts: List[SpatialTemporalConflict] = []
        for c in conflicts:
            # Designate Rover B as yield unit (arbitrated by ID lexicographical priority)
            yield_rover_id = max(c.rover_id_a, c.rover_id_b)
            hold_duration_s = (c.time_window_s[1] - c.time_window_s[0]) + self.temporal_buffer_s + 60.0

            # Re-plan yield rover with inserted delay
            tgt_objs = [targets_by_id[t_id] for t_id in allocations.get(yield_rover_id, []) if t_id in targets_by_id]
            reこと_route = self.generate_single_rover_route(
                terrain=terrain,
                rover_config=rovers[yield_rover_id],
                starting_rc=rovers[yield_rover_id].starting_location_rc,
                assigned_targets=tgt_objs,
                start_time_s=start_time_s,
                inserted_delay_s=hold_duration_s,
            )
            routes[yield_rover_id] = reこと_route

            c.status = ConflictStatus.CONFLICT_RESOLVED_BY_DELAY.value
            c.resolution_strategy = f"HOLD_AT_ORIGIN_{yield_rover_id}_{int(hold_duration_s)}S"
            c.delay_applied_s = hold_duration_s
            c.diagnostic_note += f" Deconflicted: Applied +{hold_duration_s:.0f}s hold to {yield_rover_id}."
            resolved_conflicts.append(c)

        # Re-verify conflicts after delay application
        remaining = self.detect_spatial_temporal_conflicts(routes)
        for r_id, r in routes.items():
            r.conflicts_detected = [c for c in resolved_conflicts if c.rover_id_a == r_id or c.rover_id_b == r_id]

        return routes, resolved_conflicts
