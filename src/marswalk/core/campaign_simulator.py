# src/marswalk/core/campaign_simulator.py
"""
MarsWalk 2.0 — Milestone 11F: Campaign Digital Twin, Multi-Unit Timeline & Temporal Execution Simulation.

This module provides deterministic, replayable temporal simulation of a coordinated multi-unit
planetary exploration campaign across simulated Martian time.

Key Capabilities:
1. Multi-unit timeline decomposition into non-overlapping task intervals (TRANSIT, DWELL, HOLD, REST, HANDOFF).
2. Continuous simulated campaign clock with explicit Sol indexing and documented time origin.
3. Deterministic event-driven queue with strict tie-breaking comparator for bit-exact reproducibility.
4. Comprehensive temporal conflict detection (double-booking, concurrent target access, DAG prerequisite violations, availability windows, duration budgets).
5. Interactive simulation controls: advance, step, seek (non-mutating reconstruction), pause, and reset.
6. Contingency interruptions with historical prefix freezing and dynamic remaining-work replanning.
7. Explicit simulated position labeling (is_simulated_position=True) with zero invented telemetry.
"""

from __future__ import annotations

import copy
import enum
import math
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from marswalk.core.terrain import TerrainGrid
from marswalk.core.mission_campaign import (
    CampaignTarget,
    CampaignSortie,
    CampaignSummary,
    CampaignConfig,
    MissionCampaign,
    TargetStatus,
    CampaignStatus,
    validate_target_dependencies,
)
from marswalk.core.campaign_coordination import (
    ExplorationUnit,
    TargetAllocation,
    TaskHandoff,
    CoordinationPlan,
    UnitType,
    UnitStatus,
    AllocationStatus,
    HandoffStatus,
    create_default_units,
)
from marswalk.api.contracts import (
    SCHEMA_VERSION,
    TERRAIN_DATASET_ID,
    TERRAIN_SHA256,
    validate_campaign_simulation_record,
    sanitize_for_json,
)

SIMULATION_DISCLAIMER = (
    "The Campaign Digital Twin is a deterministic simulation model for Mars mission planning and rehearsal. "
    "It does NOT represent a live telemetry feed, real-time autonomous robotic control, or flight-certified operations software. "
    "All positions are simulated route derivations and physical sample/power transfers between vehicles are unsupported."
)

MARTIAN_SOL_SECONDS = 88775.244  # Length of 1 Martian solar day (Sol) in seconds
MAX_SIMULATION_TIME_S = 14 * MARTIAN_SOL_SECONDS  # 14 Sols upper bound
MAX_SIMULATION_EVENTS = 5000  # Protection against memory exhaustion
MAX_STEP_COUNT = 1000


class ActivityType(str, enum.Enum):
    IDLE = "IDLE"
    TRANSIT = "TRANSIT"
    DWELL = "DWELL"
    HOLD = "HOLD"
    HANDOFF = "HANDOFF"
    REST = "REST"
    DEPOT = "DEPOT"
    OFFLINE = "OFFLINE"


class IntervalStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    DEFERRED = "DEFERRED"
    INTERRUPTED = "INTERRUPTED"


class SimulationStatus(str, enum.Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    INTERRUPTED = "INTERRUPTED"


class ConflictSeverity(str, enum.Enum):
    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


class ConflictCode(str, enum.Enum):
    CONFLICT_UNIT_DOUBLE_BOOKED = "CONFLICT_UNIT_DOUBLE_BOOKED"
    CONFLICT_TARGET_CONCURRENT_ACCESS = "CONFLICT_TARGET_CONCURRENT_ACCESS"
    CONFLICT_PREREQUISITE_VIOLATION = "CONFLICT_PREREQUISITE_VIOLATION"
    CONFLICT_OUTSIDE_AVAILABILITY = "CONFLICT_OUTSIDE_AVAILABILITY"
    CONFLICT_DURATION_BUDGET_EXCEEDED = "CONFLICT_DURATION_BUDGET_EXCEEDED"
    CONFLICT_HANDOFF_UNAVAILABLE = "CONFLICT_HANDOFF_UNAVAILABLE"
    CONFLICT_ORPHANED_TASKS = "CONFLICT_ORPHANED_TASKS"
    CONFLICT_MISSING_TEMPORAL_DATA = "CONFLICT_MISSING_TEMPORAL_DATA"


@dataclass
class TimelineInterval:
    """Discrete, non-overlapping task interval assigned to an exploration unit."""
    interval_id: str
    unit_id: str
    activity_type: str  # TRANSIT, DWELL, HOLD, HANDOFF, REST, DEPOT
    start_time_s: float
    end_time_s: float
    duration_s: float
    sol_index: int
    status: str = IntervalStatus.PLANNED.value
    sortie_id: Optional[str] = None
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    path_rc: List[Tuple[int, int]] = field(default_factory=list)
    distance_m: float = 0.0

    def contains_time(self, t_s: float) -> bool:
        return self.start_time_s <= t_s <= self.end_time_s

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interval_id": self.interval_id,
            "unit_id": self.unit_id,
            "activity_type": self.activity_type,
            "start_time_s": round(float(self.start_time_s), 2),
            "end_time_s": round(float(self.end_time_s), 2),
            "duration_s": round(float(self.duration_s), 2),
            "sol_index": int(self.sol_index),
            "status": self.status,
            "sortie_id": self.sortie_id,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "path_rc": [list(rc) for rc in self.path_rc],
            "distance_m": round(float(self.distance_m), 1),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimelineInterval":
        return cls(
            interval_id=str(data["interval_id"]),
            unit_id=str(data["unit_id"]),
            activity_type=str(data["activity_type"]),
            start_time_s=float(data["start_time_s"]),
            end_time_s=float(data["end_time_s"]),
            duration_s=float(data["duration_s"]),
            sol_index=int(data["sol_index"]),
            status=str(data.get("status", IntervalStatus.PLANNED.value)),
            sortie_id=data.get("sortie_id"),
            target_id=data.get("target_id"),
            target_name=data.get("target_name"),
            path_rc=[tuple(rc) for rc in data.get("path_rc", [])],
            distance_m=float(data.get("distance_m", 0.0)),
        )


@dataclass
class SimulationEvent:
    """Discrete, time-stamped simulation milestone with deterministic tie-breaking."""
    event_id: str
    event_type: str
    simulated_time_s: float
    sol_index: int
    title: str
    description: str
    event_priority: int = 30  # status=10, completion=20, start=30, departure=40, conflict=50
    unit_id: Optional[str] = None
    target_id: Optional[str] = None
    sortie_id: Optional[str] = None
    is_simulated: bool = True
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "simulated_time_s": round(float(self.simulated_time_s), 2),
            "sol_index": int(self.sol_index),
            "unit_id": self.unit_id,
            "target_id": self.target_id,
            "sortie_id": self.sortie_id,
            "title": self.title,
            "description": self.description,
            "is_simulated": True,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationEvent":
        return cls(
            event_id=str(data["event_id"]),
            event_type=str(data["event_type"]),
            simulated_time_s=float(data["simulated_time_s"]),
            sol_index=int(data["sol_index"]),
            title=str(data["title"]),
            description=str(data["description"]),
            unit_id=data.get("unit_id"),
            target_id=data.get("target_id"),
            sortie_id=data.get("sortie_id"),
            is_simulated=bool(data.get("is_simulated", True)),
            details=dict(data.get("details", {})),
        )


@dataclass
class TemporalConflict:
    """Detected scheduling inconsistency or constraint violation."""
    conflict_id: str
    code: str
    severity: str  # blocker, warning, info
    simulated_time_s: float
    affected_units: List[str]
    affected_targets: List[str]
    message: str
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "code": self.code,
            "severity": self.severity,
            "simulated_time_s": round(float(self.simulated_time_s), 2),
            "affected_units": list(self.affected_units),
            "affected_targets": list(self.affected_targets),
            "message": self.message,
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemporalConflict":
        return cls(
            conflict_id=str(data["conflict_id"]),
            code=str(data["code"]),
            severity=str(data["severity"]),
            simulated_time_s=float(data["simulated_time_s"]),
            affected_units=list(data.get("affected_units", [])),
            affected_targets=list(data.get("affected_targets", [])),
            message=str(data["message"]),
            recommendation=str(data["recommendation"]),
        )


@dataclass
class SimulatedUnitState:
    """Instantaneous operational state and derived position of an exploration unit."""
    unit_id: str
    name: str
    unit_type: str
    status: str = UnitStatus.AVAILABLE.value
    current_activity: str = ActivityType.IDLE.value
    current_target_id: Optional[str] = None
    current_sortie_id: Optional[str] = None
    position: Dict[str, Any] = field(default_factory=lambda: {
        "row": 117,
        "col": 157,
        "lon": None,
        "lat": None,
        "elevation_m": -2500.0,
        "slope_deg": 0.0,
        "is_simulated_position": True,
    })
    total_distance_m: float = 0.0
    total_active_time_s: float = 0.0
    energy_consumed_kwh: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "name": self.name,
            "unit_type": self.unit_type,
            "status": self.status,
            "current_activity": self.current_activity,
            "current_target_id": self.current_target_id,
            "current_sortie_id": self.current_sortie_id,
            "position": self.position,
            "total_distance_m": round(float(self.total_distance_m), 1),
            "total_active_time_s": round(float(self.total_active_time_s), 1),
            "energy_consumed_kwh": round(float(self.energy_consumed_kwh), 3),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulatedUnitState":
        return cls(
            unit_id=str(data["unit_id"]),
            name=str(data["name"]),
            unit_type=str(data.get("unit_type", UnitType.ROBOTIC_ROVER.value)),
            status=str(data.get("status", UnitStatus.AVAILABLE.value)),
            current_activity=str(data.get("current_activity", ActivityType.IDLE.value)),
            current_target_id=data.get("current_target_id"),
            current_sortie_id=data.get("current_sortie_id"),
            position=dict(data.get("position", {})),
            total_distance_m=float(data.get("total_distance_m", 0.0)),
            total_active_time_s=float(data.get("total_active_time_s", 0.0)),
            energy_consumed_kwh=float(data.get("energy_consumed_kwh", 0.0)),
        )


def interpolate_position_along_path(
    path_rc: List[Tuple[int, int]],
    fraction: float,
    terrain: Optional[TerrainGrid] = None,
    transform: Any = None,
) -> Dict[str, Any]:
    """
    Interpolates a simulated grid cell and geographical coordinates along a route polyline.
    Strictly flags is_simulated_position=True.
    """
    if not path_rc:
        return {
            "row": 0,
            "col": 0,
            "lon": None,
            "lat": None,
            "elevation_m": 0.0,
            "slope_deg": 0.0,
            "is_simulated_position": True,
        }

    clamped_frac = max(0.0, min(1.0, float(fraction)))
    total_points = len(path_rc)
    if total_points == 1:
        r, c = path_rc[0]
    else:
        index_float = clamped_frac * (total_points - 1)
        idx_low = int(math.floor(index_float))
        idx_high = min(total_points - 1, idx_low + 1)
        sub_frac = index_float - idx_low

        r_low, c_low = path_rc[idx_low]
        r_high, c_high = path_rc[idx_high]

        r = int(round(r_low + sub_frac * (r_high - r_low)))
        c = int(round(c_low + sub_frac * (c_high - c_low)))

    elev = 0.0
    slope = 0.0
    if terrain is not None:
        if 0 <= r < terrain.elevation.shape[0] and 0 <= c < terrain.elevation.shape[1]:
            elev = float(terrain.elevation[r, c])
            slope = float(terrain.slope_deg[r, c])

    lon = None
    lat = None
    if transform is not None:
        try:
            x, y = transform * (c + 0.5, r + 0.5)
            lon = round(float(x), 6)
            lat = round(float(y), 6)
        except Exception:
            pass

    return {
        "row": int(r),
        "col": int(c),
        "lon": lon,
        "lat": lat,
        "elevation_m": round(float(elev), 1),
        "slope_deg": round(float(slope), 1),
        "is_simulated_position": True,
    }


def detect_temporal_conflicts(
    intervals: List[TimelineInterval],
    targets: List[CampaignTarget],
    units: List[ExplorationUnit],
    campaign_deadline_s: Optional[float] = None,
) -> List[TemporalConflict]:
    """
    Detects temporal scheduling conflicts across multi-unit task intervals and DAG dependencies.
    """
    conflicts: List[TemporalConflict] = []
    unit_map = {u.unit_id: u for u in units}
    target_map = {t.id: t for t in targets}

    # 1. Check double-booking per unit (overlapping active intervals on same unit)
    intervals_by_unit: Dict[str, List[TimelineInterval]] = {}
    for iv in intervals:
        intervals_by_unit.setdefault(iv.unit_id, []).append(iv)

    for uid, u_intervals in intervals_by_unit.items():
        sorted_u_ivs = sorted(u_intervals, key=lambda x: (x.start_time_s, x.end_time_s))
        for i in range(len(sorted_u_ivs) - 1):
            iv1 = sorted_u_ivs[i]
            iv2 = sorted_u_ivs[i + 1]

            # REST/DEPOT intervals can abut, but active activities must not overlap
            if iv1.end_time_s > iv2.start_time_s:
                overlap_dur = iv1.end_time_s - iv2.start_time_s
                if overlap_dur > 0.1:  # Allow 100ms numeric tolerance
                    conflicts.append(TemporalConflict(
                        conflict_id=f"conf_double_book_{uid}_{iv1.interval_id[:8]}",
                        code=ConflictCode.CONFLICT_UNIT_DOUBLE_BOOKED.value,
                        severity=ConflictSeverity.BLOCKER.value,
                        simulated_time_s=iv2.start_time_s,
                        affected_units=[uid],
                        affected_targets=[t for t in [iv1.target_id, iv2.target_id] if t],
                        message=(
                            f"Unit '{uid}' is double-booked between T+{iv2.start_time_s:.1f}s and T+{iv1.end_time_s:.1f}s "
                            f"with overlapping tasks '{iv1.activity_type}' and '{iv2.activity_type}'."
                        ),
                        recommendation="Serialize activities or reassign one of the conflicting sorties to an available partner unit."
                    ))

    # 2. Check concurrent access to the same science target across different units
    dwell_intervals = [iv for iv in intervals if iv.activity_type == ActivityType.DWELL.value and iv.target_id]
    dwells_by_target: Dict[str, List[TimelineInterval]] = {}
    for div in dwell_intervals:
        dwells_by_target.setdefault(div.target_id, []).append(div)

    for tid, t_dwells in dwells_by_target.items():
        if len(t_dwells) > 1:
            sorted_t_dwells = sorted(t_dwells, key=lambda x: x.start_time_s)
            for i in range(len(sorted_t_dwells) - 1):
                d1 = sorted_t_dwells[i]
                d2 = sorted_t_dwells[i + 1]
                if d1.unit_id != d2.unit_id and d1.end_time_s > d2.start_time_s:
                    conflicts.append(TemporalConflict(
                        conflict_id=f"conf_target_concurrent_{tid}_{d1.unit_id}_{d2.unit_id}",
                        code=ConflictCode.CONFLICT_TARGET_CONCURRENT_ACCESS.value,
                        severity=ConflictSeverity.BLOCKER.value,
                        simulated_time_s=d2.start_time_s,
                        affected_units=[d1.unit_id, d2.unit_id],
                        affected_targets=[tid],
                        message=(
                            f"Target '{tid}' is scheduled for concurrent dwell by both unit '{d1.unit_id}' and '{d2.unit_id}' "
                            f"at T+{d2.start_time_s:.1f}s without concurrency permission."
                        ),
                        recommendation="Stagger target arrival times or designate one unit as an advance reconnaissance asset."
                    ))

    # 3. Check DAG prerequisite completion times
    target_completion_times: Dict[str, float] = {}
    for div in dwell_intervals:
        if div.target_id:
            # Completion is when dwell ends
            target_completion_times[div.target_id] = div.end_time_s

    for div in dwell_intervals:
        tid = div.target_id
        if not tid or tid not in target_map:
            continue
        tgt = target_map[tid]
        for prereq_id in tgt.prerequisites:
            if prereq_id in target_completion_times:
                prereq_end = target_completion_times[prereq_id]
                if prereq_end > div.start_time_s:
                    conflicts.append(TemporalConflict(
                        conflict_id=f"conf_prereq_viol_{tid}_{prereq_id}",
                        code=ConflictCode.CONFLICT_PREREQUISITE_VIOLATION.value,
                        severity=ConflictSeverity.BLOCKER.value,
                        simulated_time_s=div.start_time_s,
                        affected_units=[div.unit_id],
                        affected_targets=[tid, prereq_id],
                        message=(
                            f"Target '{tid}' starts at T+{div.start_time_s:.1f}s before prerequisite '{prereq_id}' completes "
                            f"(completes at T+{prereq_end:.1f}s)."
                        ),
                        recommendation=f"Schedule target '{tid}' after T+{prereq_end:.1f}s or reschedule prerequisite earlier."
                    ))
            else:
                conflicts.append(TemporalConflict(
                    conflict_id=f"conf_prereq_missing_{tid}_{prereq_id}",
                    code=ConflictCode.CONFLICT_PREREQUISITE_VIOLATION.value,
                    severity=ConflictSeverity.BLOCKER.value,
                    simulated_time_s=div.start_time_s,
                    affected_units=[div.unit_id],
                    affected_targets=[tid, prereq_id],
                    message=f"Target '{tid}' requires prerequisite '{prereq_id}', which is never scheduled in the campaign.",
                    recommendation=f"Add prerequisite target '{prereq_id}' to the campaign schedule prior to '{tid}'."
                ))

    # 4. Check unit availability window per sol
    for iv in intervals:
        if iv.unit_id in unit_map:
            unit = unit_map[iv.unit_id]
            if not unit.availability_window.is_available_on_sol(iv.sol_index):
                conflicts.append(TemporalConflict(
                    conflict_id=f"conf_avail_win_{iv.unit_id}_sol{iv.sol_index}",
                    code=ConflictCode.CONFLICT_OUTSIDE_AVAILABILITY.value,
                    severity=ConflictSeverity.BLOCKER.value,
                    simulated_time_s=iv.start_time_s,
                    affected_units=[iv.unit_id],
                    affected_targets=[iv.target_id] if iv.target_id else [],
                    message=(
                        f"Unit '{iv.unit_id}' has task '{iv.activity_type}' scheduled on Sol {iv.sol_index}, "
                        f"which is outside its active availability window (Sols {unit.availability_window.start_sol}–{unit.availability_window.end_sol})."
                    ),
                    recommendation="Reassign task to an active sol or extend the unit's availability schedule."
                ))

    # 5. Check duration budget per sortie / sol
    sortie_durations: Dict[Tuple[str, str], float] = {}  # (unit_id, sortie_id) -> active duration
    for iv in intervals:
        if iv.sortie_id and iv.activity_type in (ActivityType.TRANSIT.value, ActivityType.DWELL.value, ActivityType.HOLD.value):
            key = (iv.unit_id, iv.sortie_id)
            sortie_durations[key] = sortie_durations.get(key, 0.0) + iv.duration_s

    for (uid, sid), total_act_s in sortie_durations.items():
        if uid in unit_map:
            max_s = unit_map[uid].max_duration_per_sortie_s
            if total_act_s > max_s:
                conflicts.append(TemporalConflict(
                    conflict_id=f"conf_budget_exceeded_{uid}_{sid}",
                    code=ConflictCode.CONFLICT_DURATION_BUDGET_EXCEEDED.value,
                    severity=ConflictSeverity.WARNING.value,
                    simulated_time_s=0.0,
                    affected_units=[uid],
                    affected_targets=[],
                    message=(
                        f"Sortie '{sid}' assigned to unit '{uid}' requires {total_act_s:.1f}s of active duration, "
                        f"exceeding the platform limit of {max_s:.1f}s."
                    ),
                    recommendation="Prune or split targets in this sortie to fit within the unit's life-support consumables."
                ))

    # 6. Check campaign deadline
    if campaign_deadline_s is not None and campaign_deadline_s > 0:
        for iv in intervals:
            if iv.end_time_s > campaign_deadline_s:
                conflicts.append(TemporalConflict(
                    conflict_id=f"conf_deadline_exceeded_{iv.interval_id[:8]}",
                    code=ConflictCode.CONFLICT_DURATION_BUDGET_EXCEEDED.value,
                    severity=ConflictSeverity.WARNING.value,
                    simulated_time_s=campaign_deadline_s,
                    affected_units=[iv.unit_id],
                    affected_targets=[iv.target_id] if iv.target_id else [],
                    message=(
                        f"Task '{iv.activity_type}' ends at T+{iv.end_time_s:.1f}s, exceeding the overall campaign deadline of T+{campaign_deadline_s:.1f}s."
                    ),
                    recommendation="Accelerate traverses, compress dwells, or adjust campaign deadline."
                ))

    return conflicts


class CampaignDigitalTwin:
    """
    Deterministic temporal simulation engine and digital twin representing a multi-unit
    planetary surface campaign unfolding over continuous simulated time.
    """

    def __init__(
        self,
        simulation_id: str,
        campaign: MissionCampaign,
        coordination_plan: Optional[CoordinationPlan] = None,
        terrain: Optional[TerrainGrid] = None,
        transform: Any = None,
        parent_simulation_id: Optional[str] = None,
    ):
        self.simulation_id = simulation_id
        self.campaign = campaign
        self.coordination_plan = coordination_plan
        self.terrain = terrain
        self.transform = transform
        self.parent_simulation_id = parent_simulation_id

        self.current_time_s: float = 0.0
        self.status: str = SimulationStatus.IDLE.value
        self.time_scale: float = 1.0
        self.created_at_utc = datetime.now(timezone.utc).isoformat()
        self.updated_at_utc = self.created_at_utc

        # Exploration units
        if coordination_plan and coordination_plan.units:
            self.units: List[ExplorationUnit] = copy.deepcopy(coordination_plan.units)
        else:
            self.units = create_default_units(campaign.config)

        # Dynamic simulation state
        self.unit_states: Dict[str, SimulatedUnitState] = {}
        for u in self.units:
            base_rc = u.starting_location_rc or (117, 157)
            init_pos = interpolate_position_along_path([base_rc], 0.0, terrain, transform)
            self.unit_states[u.unit_id] = SimulatedUnitState(
                unit_id=u.unit_id,
                name=u.name,
                unit_type=u.unit_type,
                status=UnitStatus.AVAILABLE.value,
                current_activity=ActivityType.IDLE.value,
                position=init_pos,
            )

        self.target_states: Dict[str, Dict[str, Any]] = {}
        for t in campaign.targets:
            self.target_states[t.id] = {
                "target_id": t.id,
                "name": t.name,
                "status": TargetStatus.SCHEDULED.value if t.status == TargetStatus.SCHEDULED.value else t.status,
                "completed_at_s": None,
                "assigned_unit_id": t.assigned_unit_id,
            }

        # Compiled multi-lane task intervals and discrete events
        self.timeline_intervals: List[TimelineInterval] = []
        self.event_queue: List[SimulationEvent] = []
        self.logged_events: List[SimulationEvent] = []
        self.conflicts: List[TemporalConflict] = []
        self.total_duration_s: float = 0.0

        # Snapshot cache for instantaneous state reconstruction during seek operations
        self.state_snapshots: List[Dict[str, Any]] = []

        # Compile timeline
        self._compile_timeline()

    @property
    def current_sol(self) -> int:
        return 1 + int(math.floor(max(0.0, self.current_time_s) / MARTIAN_SOL_SECONDS))

    def _compile_timeline(self) -> None:
        """
        Decomposes campaign sorties and unit allocations into discrete timeline intervals
        and generates a deterministically sorted event queue.
        """
        self.timeline_intervals = []
        self.event_queue = []

        # 1. Map sorties to units
        sorties_to_schedule = list(self.campaign.sorties)
        if self.coordination_plan and self.coordination_plan.sorties:
            sorties_to_schedule = list(self.coordination_plan.sorties)

        # Group sorties by assigned unit
        sorties_by_unit: Dict[str, List[CampaignSortie]] = {}
        default_unit_id = self.units[0].unit_id if self.units else "unit_perseverance"

        for s in sorties_to_schedule:
            uid = s.unit_id or default_unit_id
            sorties_by_unit.setdefault(uid, []).append(s)

        # 2. Compile intervals per unit
        for uid, unit_sorties in sorties_by_unit.items():
            # Sort sorties by sol index
            sorted_sorties = sorted(unit_sorties, key=lambda x: x.sol_index)
            unit_obj = next((u for u in self.units if u.unit_id == uid), None)
            base_loc = unit_obj.starting_location_rc if unit_obj else (117, 157)

            current_loc = base_loc
            for sortie in sorted_sorties:
                sol = sortie.sol_index
                sol_start_s = (sol - 1) * MARTIAN_SOL_SECONDS

                # Overnight rest before sol start
                if sol > 1:
                    prev_end = sol_start_s
                    # If this is start of new sol, can have rest interval
                    rest_iv = TimelineInterval(
                        interval_id=f"iv_rest_{uid}_sol{sol}",
                        unit_id=uid,
                        activity_type=ActivityType.REST.value,
                        start_time_s=max(0.0, sol_start_s - 3600.0),
                        end_time_s=sol_start_s,
                        duration_s=3600.0,
                        sol_index=sol - 1,
                        status=IntervalStatus.PLANNED.value,
                        sortie_id=None,
                        target_id=None,
                    )
                    self.timeline_intervals.append(rest_iv)

                # Departure event
                t_cursor = sol_start_s

                # Compile each leg of the sortie
                path = sortie.path_rc or [sortie.start_rc, sortie.goal_rc]
                targets = sortie.target_ids or []
                legs = sortie.legs_summary or []

                if legs and len(legs) == len(targets) + 1:
                    # Legs are structured
                    for l_idx, leg in enumerate(legs):
                        is_final = (l_idx == len(legs) - 1)
                        leg_dist = float(leg.get("distance_m", 0.0))
                        speed = unit_obj.mobility_profile.speed_multiplier * (
                            0.035 if unit_obj.unit_type == UnitType.ROBOTIC_ROVER.value else 0.556
                        )
                        travel_s = leg_dist / max(0.01, speed)

                        # Leg interval
                        transit_iv = TimelineInterval(
                            interval_id=f"iv_trans_{uid}_{sortie.sortie_id}_leg{l_idx+1}",
                            unit_id=uid,
                            activity_type=ActivityType.TRANSIT.value,
                            start_time_s=t_cursor,
                            end_time_s=t_cursor + travel_s,
                            duration_s=travel_s,
                            sol_index=sol,
                            status=IntervalStatus.PLANNED.value,
                            sortie_id=sortie.sortie_id,
                            path_rc=path,
                            distance_m=leg_dist,
                        )
                        self.timeline_intervals.append(transit_iv)
                        t_cursor += travel_s

                        # Dwell at target (if not return leg)
                        if not is_final and l_idx < len(targets):
                            tid = targets[l_idx]
                            dwell_s = 900.0  # default 15 min dwell
                            tgt_obj = next((t for t in self.campaign.targets if t.id == tid), None)
                            if tgt_obj:
                                dwell_s = tgt_obj.dwell_time_s
                                t_name = tgt_obj.name
                            else:
                                t_name = tid

                            dwell_iv = TimelineInterval(
                                interval_id=f"iv_dwell_{uid}_{sortie.sortie_id}_{tid}",
                                unit_id=uid,
                                activity_type=ActivityType.DWELL.value,
                                start_time_s=t_cursor,
                                end_time_s=t_cursor + dwell_s,
                                duration_s=dwell_s,
                                sol_index=sol,
                                status=IntervalStatus.PLANNED.value,
                                sortie_id=sortie.sortie_id,
                                target_id=tid,
                                target_name=t_name,
                                path_rc=[leg.get("goal_rc", current_loc)],
                            )
                            self.timeline_intervals.append(dwell_iv)
                            t_cursor += dwell_s
                else:
                    # Single continuous path decomposition
                    total_dur = max(60.0, float(sortie.total_duration_s))
                    transit_s = float(sortie.travel_time_s) or (total_dur * 0.7)
                    dwell_s = float(sortie.dwell_time_s) or (total_dur * 0.3)

                    # Transit
                    transit_iv = TimelineInterval(
                        interval_id=f"iv_trans_{uid}_{sortie.sortie_id}",
                        unit_id=uid,
                        activity_type=ActivityType.TRANSIT.value,
                        start_time_s=t_cursor,
                        end_time_s=t_cursor + transit_s,
                        duration_s=transit_s,
                        sol_index=sol,
                        status=IntervalStatus.PLANNED.value,
                        sortie_id=sortie.sortie_id,
                        path_rc=path,
                        distance_m=float(sortie.distance_m),
                    )
                    self.timeline_intervals.append(transit_iv)
                    t_cursor += transit_s

                    # Dwell for each target
                    per_tgt_dwell = dwell_s / max(1, len(targets))
                    for tid in targets:
                        tgt_obj = next((t for t in self.campaign.targets if t.id == tid), None)
                        t_name = tgt_obj.name if tgt_obj else tid

                        dwell_iv = TimelineInterval(
                            interval_id=f"iv_dwell_{uid}_{sortie.sortie_id}_{tid}",
                            unit_id=uid,
                            activity_type=ActivityType.DWELL.value,
                            start_time_s=t_cursor,
                            end_time_s=t_cursor + per_tgt_dwell,
                            duration_s=per_tgt_dwell,
                            sol_index=sol,
                            status=IntervalStatus.PLANNED.value,
                            sortie_id=sortie.sortie_id,
                            target_id=tid,
                            target_name=t_name,
                        )
                        self.timeline_intervals.append(dwell_iv)
                        t_cursor += per_tgt_dwell

        # Sort all timeline intervals by start time
        self.timeline_intervals.sort(key=lambda x: (x.start_time_s, x.end_time_s, x.unit_id))

        if self.timeline_intervals:
            self.total_duration_s = max(iv.end_time_s for iv in self.timeline_intervals)
        else:
            self.total_duration_s = 0.0

        # 3. Generate Discrete Events from Intervals
        self._generate_events_from_intervals()

        # 4. Detect Temporal Conflicts
        deadline_s = (
            (self.campaign.config.max_sols * MARTIAN_SOL_SECONDS)
            if self.campaign.config.max_sols
            else (self.campaign.config.max_total_duration_s or (14 * MARTIAN_SOL_SECONDS))
        )
        self.conflicts = detect_temporal_conflicts(
            intervals=self.timeline_intervals,
            targets=self.campaign.targets,
            units=self.units,
            campaign_deadline_s=deadline_s,
        )

        # Record simulation start event
        start_evt = SimulationEvent(
            event_id=f"evt_sim_start_{self.simulation_id[:8]}",
            event_type="SIMULATION_START",
            simulated_time_s=0.0,
            sol_index=1,
            event_priority=10,
            title="Campaign Digital Twin Initialized",
            description=f"Simulation initialized for campaign '{self.campaign.name}' with {len(self.units)} units and {len(self.timeline_intervals)} tasks.",
            details={"units": [u.unit_id for u in self.units], "campaign_id": self.campaign.campaign_id},
        )
        self.logged_events = [start_evt]

    def _generate_events_from_intervals(self) -> None:
        """Translates timeline intervals into discrete simulation events."""
        events: List[SimulationEvent] = []

        for iv in self.timeline_intervals:
            sol = iv.sol_index
            uid = iv.unit_id

            if iv.activity_type == ActivityType.TRANSIT.value:
                # Leg Start
                events.append(SimulationEvent(
                    event_id=f"evt_start_{iv.interval_id}",
                    event_type="TRANSIT_START",
                    simulated_time_s=iv.start_time_s,
                    sol_index=sol,
                    event_priority=30,
                    unit_id=uid,
                    sortie_id=iv.sortie_id,
                    title=f"Traverse Leg Commenced ({uid})",
                    description=f"Unit '{uid}' departed on traverse leg ({iv.distance_m:.1f} m).",
                ))
                # Leg Complete
                events.append(SimulationEvent(
                    event_id=f"evt_end_{iv.interval_id}",
                    event_type="TRANSIT_COMPLETE",
                    simulated_time_s=iv.end_time_s,
                    sol_index=sol,
                    event_priority=20,
                    unit_id=uid,
                    sortie_id=iv.sortie_id,
                    title=f"Traverse Leg Completed ({uid})",
                    description=f"Unit '{uid}' completed traverse ({iv.distance_m:.1f} m).",
                ))

            elif iv.activity_type == ActivityType.DWELL.value:
                # Dwell Start
                events.append(SimulationEvent(
                    event_id=f"evt_dwell_start_{iv.interval_id}",
                    event_type="DWELL_START",
                    simulated_time_s=iv.start_time_s,
                    sol_index=sol,
                    event_priority=30,
                    unit_id=uid,
                    target_id=iv.target_id,
                    sortie_id=iv.sortie_id,
                    title=f"Science Dwell Commenced ({iv.target_name or iv.target_id})",
                    description=f"Unit '{uid}' began science observation at target '{iv.target_name or iv.target_id}'.",
                ))
                # Dwell Complete
                events.append(SimulationEvent(
                    event_id=f"evt_dwell_end_{iv.interval_id}",
                    event_type="DWELL_COMPLETE",
                    simulated_time_s=iv.end_time_s,
                    sol_index=sol,
                    event_priority=20,
                    unit_id=uid,
                    target_id=iv.target_id,
                    sortie_id=iv.sortie_id,
                    title=f"Science Target Completed ({iv.target_name or iv.target_id})",
                    description=f"Unit '{uid}' completed science sampling at target '{iv.target_name or iv.target_id}'.",
                ))

            elif iv.activity_type == ActivityType.HOLD.value:
                events.append(SimulationEvent(
                    event_id=f"evt_hold_{iv.interval_id}",
                    event_type="OPERATIONAL_HOLD",
                    simulated_time_s=iv.start_time_s,
                    sol_index=sol,
                    event_priority=40,
                    unit_id=uid,
                    title=f"Operational Hold ({uid})",
                    description=f"Unit '{uid}' initiated an operational hold of {iv.duration_s:.1f}s.",
                ))

        # Deterministic sorting: (time, priority, unit_id, event_id)
        events.sort(key=lambda e: (
            e.simulated_time_s,
            e.event_priority,
            e.unit_id or "",
            e.event_id
        ))

        self.event_queue = events

    def advance(self, target_time_s: float) -> List[SimulationEvent]:
        """
        Advances the simulation clock to target_time_s, executing all intervening events
        and updating the states and positions of all exploration units.
        """
        clamped_time = max(self.current_time_s, min(float(target_time_s), MAX_SIMULATION_TIME_S))
        newly_processed_events: List[SimulationEvent] = []

        # Find events to process
        while self.event_queue:
            next_evt = self.event_queue[0]
            if next_evt.simulated_time_s <= clamped_time:
                evt = self.event_queue.pop(0)
                self.logged_events.append(evt)
                newly_processed_events.append(evt)

                # Process event side-effects
                if evt.event_type == "DWELL_COMPLETE" and evt.target_id:
                    if evt.target_id in self.target_states:
                        self.target_states[evt.target_id]["status"] = TargetStatus.COMPLETED.value
                        self.target_states[evt.target_id]["completed_at_s"] = evt.simulated_time_s
            else:
                break

        self.current_time_s = clamped_time
        self._update_all_unit_states(self.current_time_s)

        if not self.event_queue and self.current_time_s >= self.total_duration_s:
            self.status = SimulationStatus.COMPLETED.value
        else:
            self.status = SimulationStatus.RUNNING.value

        self.updated_at_utc = datetime.now(timezone.utc).isoformat()
        return newly_processed_events

    def step(self, event_count: int = 1) -> List[SimulationEvent]:
        """Advances the simulation clock to the timestamp of the next N events."""
        if not self.event_queue:
            self.status = SimulationStatus.COMPLETED.value
            return []

        count = max(1, min(int(event_count), len(self.event_queue)))
        target_event = self.event_queue[count - 1]
        target_time = target_event.simulated_time_s

        return self.advance(target_time)

    def pause(self) -> None:
        """Pauses clock progression while preserving state."""
        self.status = SimulationStatus.PAUSED.value
        self.updated_at_utc = datetime.now(timezone.utc).isoformat()

    def seek(self, target_time_s: float) -> None:
        """
        Reconstructs the simulation state at target_time_s without mutating recorded past.
        """
        clamped_time = max(0.0, min(float(target_time_s), self.total_duration_s))

        # Rebuild clean event queue and logged events
        self._generate_events_from_intervals()

        # Re-initialize target completion states
        for t in self.campaign.targets:
            self.target_states[t.id] = {
                "target_id": t.id,
                "name": t.name,
                "status": TargetStatus.SCHEDULED.value,
                "completed_at_s": None,
                "assigned_unit_id": t.assigned_unit_id,
            }

        past_events = []
        future_events = []

        for evt in self.event_queue:
            if evt.simulated_time_s <= clamped_time:
                past_events.append(evt)
                if evt.event_type == "DWELL_COMPLETE" and evt.target_id:
                    if evt.target_id in self.target_states:
                        self.target_states[evt.target_id]["status"] = TargetStatus.COMPLETED.value
                        self.target_states[evt.target_id]["completed_at_s"] = evt.simulated_time_s
            else:
                future_events.append(evt)

        # Prepend sim start
        start_evt = SimulationEvent(
            event_id=f"evt_sim_start_{self.simulation_id[:8]}",
            event_type="SIMULATION_START",
            simulated_time_s=0.0,
            sol_index=1,
            event_priority=10,
            title="Campaign Digital Twin Initialized",
            description=f"Simulation initialized for campaign '{self.campaign.name}'.",
        )
        self.logged_events = [start_evt] + past_events
        self.event_queue = future_events
        self.current_time_s = clamped_time

        self._update_all_unit_states(self.current_time_s)
        self.status = SimulationStatus.PAUSED.value
        self.updated_at_utc = datetime.now(timezone.utc).isoformat()

    def reset(self) -> None:
        """Resets the simulation to t=0.0."""
        self.seek(0.0)
        self.status = SimulationStatus.IDLE.value

    def _update_all_unit_states(self, t_s: float) -> None:
        """Updates activity and derived position for each exploration unit at time t_s."""
        for u in self.units:
            uid = u.unit_id
            u_state = self.unit_states[uid]

            # Find active interval for unit at t_s
            active_iv: Optional[TimelineInterval] = None
            for iv in self.timeline_intervals:
                if iv.unit_id == uid and iv.contains_time(t_s):
                    active_iv = iv
                    break

            if active_iv is not None:
                u_state.current_activity = active_iv.activity_type
                u_state.current_sortie_id = active_iv.sortie_id
                u_state.current_target_id = active_iv.target_id

                if active_iv.activity_type == ActivityType.TRANSIT.value:
                    u_state.status = UnitStatus.BUSY.value
                    # Interpolate position along transit path
                    dur = max(0.01, active_iv.duration_s)
                    fraction = (t_s - active_iv.start_time_s) / dur
                    u_state.position = interpolate_position_along_path(
                        active_iv.path_rc, fraction, self.terrain, self.transform
                    )
                elif active_iv.activity_type == ActivityType.DWELL.value:
                    u_state.status = UnitStatus.BUSY.value
                    if active_iv.path_rc:
                        u_state.position = interpolate_position_along_path(
                            active_iv.path_rc, 1.0, self.terrain, self.transform
                        )
                elif active_iv.activity_type == ActivityType.HOLD.value:
                    u_state.status = UnitStatus.HOLD.value
                else:
                    u_state.status = UnitStatus.AVAILABLE.value
            else:
                u_state.current_activity = ActivityType.IDLE.value
                u_state.current_sortie_id = None
                u_state.current_target_id = None
                u_state.status = UnitStatus.AVAILABLE.value

            # Update cumulative distances and durations
            traversed_m = 0.0
            active_s = 0.0
            for iv in self.timeline_intervals:
                if iv.unit_id == uid:
                    if iv.end_time_s <= t_s:
                        traversed_m += iv.distance_m
                        if iv.activity_type in (ActivityType.TRANSIT.value, ActivityType.DWELL.value, ActivityType.HOLD.value):
                            active_s += iv.duration_s
                    elif iv.contains_time(t_s):
                        fraction = (t_s - iv.start_time_s) / max(0.01, iv.duration_s)
                        traversed_m += iv.distance_m * fraction
                        if iv.activity_type in (ActivityType.TRANSIT.value, ActivityType.DWELL.value, ActivityType.HOLD.value):
                            active_s += (t_s - iv.start_time_s)

            u_state.total_distance_m = round(traversed_m, 1)
            u_state.total_active_time_s = round(active_s, 1)
            # Energy consumption: rover ~ 18.5 Wh/km, crew ~ 92 Wh/km
            rate_wh_per_km = 18.5 if u.unit_type == UnitType.ROBOTIC_ROVER.value else 92.0
            u_state.energy_consumed_kwh = round((traversed_m / 1000.0) * (rate_wh_per_km / 1000.0), 3)

    def inject_interruption(
        self,
        interruption_type: str,
        affected_unit_id: Optional[str] = None,
        affected_target_id: Optional[str] = None,
        delay_duration_s: float = 0.0,
        reason: str = "Unplanned operational contingency",
    ) -> "CampaignDigitalTwin":
        """
        Injects an interruption at the current simulation time t_int.
        1. Freezes historical prefix up to current_time_s.
        2. Recomputes remaining work for uncompleted targets.
        3. Creates a new revised CampaignDigitalTwin with parent lineage.
        """
        t_int = self.current_time_s
        sol_int = self.current_sol

        # Record interruption event
        int_evt = SimulationEvent(
            event_id=f"evt_interrupt_{uuid.uuid4().hex[:8]}",
            event_type="CONTINGENCY_INTERRUPTED",
            simulated_time_s=t_int,
            sol_index=sol_int,
            event_priority=15,
            unit_id=affected_unit_id,
            target_id=affected_target_id,
            title=f"Contingency Interruption: {interruption_type.upper()}",
            description=f"Injected '{interruption_type}' at T+{t_int:.1f}s (Sol {sol_int}): {reason}.",
            details={
                "interruption_type": interruption_type,
                "affected_unit_id": affected_unit_id,
                "affected_target_id": affected_target_id,
                "delay_duration_s": delay_duration_s,
                "reason": reason,
            },
        )
        self.logged_events.append(int_evt)
        self.status = SimulationStatus.INTERRUPTED.value

        # Identify completed targets
        completed_tids = {
            tid for tid, st in self.target_states.items()
            if st["status"] == TargetStatus.COMPLETED.value
        }

        # Clone campaign and preserve completed targets
        revised_campaign = copy.deepcopy(self.campaign)
        revised_campaign.campaign_id = f"{self.campaign.campaign_id}_rev"
        revised_campaign.version = self.campaign.version + 1

        # Adjust remaining targets
        remaining_targets = []
        for t in revised_campaign.targets:
            if t.id in completed_tids:
                t.status = TargetStatus.COMPLETED.value
            elif affected_target_id and t.id == affected_target_id:
                t.status = TargetStatus.BLOCKED.value
            else:
                remaining_targets.append(t)

        # Adjust units
        revised_units = copy.deepcopy(self.units)
        if interruption_type == "unit_unavailable" and affected_unit_id:
            for u in revised_units:
                if u.unit_id == affected_unit_id:
                    u.status = UnitStatus.UNAVAILABLE.value
                    u.availability_window.end_sol = max(1, sol_int - 1)

        # Build revised coordination plan if present
        revised_coord = None
        if self.coordination_plan:
            revised_coord = copy.deepcopy(self.coordination_plan)
            revised_coord.coordination_id = f"{self.coordination_plan.coordination_id}_rev"
            revised_coord.version += 1
            revised_coord.units = revised_units

            # Reallocate remaining uncompleted targets to available units
            surviving_units = [u for u in revised_units if u.status != UnitStatus.UNAVAILABLE.value]
            surviving_uid = surviving_units[0].unit_id if surviving_units else None

            for alloc in revised_coord.target_allocations:
                if alloc.target_id in completed_tids:
                    alloc.status = AllocationStatus.ASSIGNED.value
                elif affected_target_id and alloc.target_id == affected_target_id:
                    alloc.status = AllocationStatus.BLOCKED.value
                elif alloc.assigned_unit_id == affected_unit_id and surviving_uid:
                    alloc.assigned_unit_id = surviving_uid
                    alloc.reason = f"Transferred from failed unit '{affected_unit_id}'"

        # Construct revised Digital Twin
        new_sim_id = f"{self.simulation_id}_rev1"
        revised_twin = CampaignDigitalTwin(
            simulation_id=new_sim_id,
            campaign=revised_campaign,
            coordination_plan=revised_coord,
            terrain=self.terrain,
            transform=self.transform,
            parent_simulation_id=self.simulation_id,
        )

        # Fast-forward revised twin to interruption point t_int
        revised_twin.advance(t_int)
        return revised_twin

    def to_dict(self) -> Dict[str, Any]:
        """Serializes digital twin simulation into a contract-valid JSON dictionary."""
        completed_count = sum(1 for st in self.target_states.values() if st["status"] == TargetStatus.COMPLETED.value)
        total_targets = len(self.target_states)
        remaining_count = total_targets - completed_count
        progress_pct = round((completed_count / max(1, total_targets)) * 100.0, 1)

        return {
            "schema_version": SCHEMA_VERSION,
            "simulation_id": self.simulation_id,
            "campaign_id": self.campaign.campaign_id,
            "campaign_version": int(self.campaign.version),
            "coordination_id": self.coordination_plan.coordination_id if self.coordination_plan else None,
            "parent_simulation_id": self.parent_simulation_id,
            "status": self.status,
            "current_time_s": round(float(self.current_time_s), 2),
            "current_sol": int(self.current_sol),
            "total_duration_s": round(float(self.total_duration_s), 2),
            "time_scale": round(float(self.time_scale), 1),
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "units": [self.unit_states[u.unit_id].to_dict() for u in self.units],
            "timeline_intervals": [iv.to_dict() for iv in self.timeline_intervals],
            "events": [evt.to_dict() for evt in self.logged_events],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "statistics": {
                "total_intervals": len(self.timeline_intervals),
                "total_events": len(self.logged_events),
                "completed_targets": completed_count,
                "remaining_targets": remaining_count,
                "conflicts_count": len(self.conflicts),
                "progress_pct": progress_pct,
            },
            "limitations_disclaimer": SIMULATION_DISCLAIMER,
        }
