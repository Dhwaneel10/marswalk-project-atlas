"""
MarsWalk 2.0 — Milestone 11E: Multi-Agent Campaign Coordination & Resource Handoffs.
Coordinates multiple simulated exploration units across a single campaign:
allocates targets and sorties, enforces topological DAG dependencies, compares coordination
strategies, models task responsibility handoffs, and recalculates campaigns under unit loss.

DISCLAIMER: This is a planning simulation for multi-asset exploration analysis.
It does NOT represent actual autonomous rover control, flight-certified operational decision
software, or physical sample/power transfer between vehicles.
"""

from dataclasses import dataclass, field
import datetime
import enum
import hashlib
import json
import math
import os
import uuid
from typing import Dict, List, Optional, Set, Tuple, Any, Union
import numpy as np

from marswalk.core.terrain import TerrainGrid, TerrainConfig, get_profile_terrain_config
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    RouteResult,
    VehicleMode,
    OPERATIONAL_LIMITS_S,
    calculate_traverse_time,
    format_duration,
    plan_sequential_multistop_route,
    ENGINEERING_ASSUMPTIONS,
)
from marswalk.core.mission_campaign import (
    CampaignTarget,
    CampaignSortie,
    CampaignSummary,
    CampaignConfig,
    MissionCampaign,
    TargetStatus,
    CampaignStatus,
    PlanningProfile,
    validate_target_dependencies,
)
from marswalk.core.contingency import compute_circular_footprint
from marswalk.api.contracts import (
    SCHEMA_VERSION,
    TERRAIN_DATASET_ID,
    TERRAIN_SHA256,
    validate_contract,
    sanitize_for_json,
    validate_campaign_coordination_record,
    ContractValidationError,
)


COORDINATION_DISCLAIMER = (
    "Calculated multi-unit coordination schedules, capability matching, and task handoffs are "
    "deterministic mission-planning heuristics derived from remote-sensing products. They do NOT "
    "represent certified autonomous robotic control, physical inter-vehicle resource transfer, or "
    "astronaut flight envelopes."
)


class UnitType(str, enum.Enum):
    ROBOTIC_ROVER = "robotic_rover"
    CREW_EVA = "crew_eva"
    SCOUT_ROVER = "scout_rover"


class UnitStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    UNAVAILABLE = "UNAVAILABLE"
    MAINTENANCE = "MAINTENANCE"
    RETIRED = "RETIRED"


class CoordinationStrategy(str, enum.Enum):
    PRIORITY_FIRST = "priority_first"
    BALANCED_WORKLOAD = "balanced_workload"
    CAPABILITY_FIRST = "capability_first"


class AllocationStatus(str, enum.Enum):
    ASSIGNED = "ASSIGNED"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    UNREACHABLE = "UNREACHABLE"
    UNALLOCATED = "UNALLOCATED"


class HandoffStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass
class MobilityProfile:
    """Locomotion physics constraints governing a specific exploration unit."""
    speed_multiplier: float = 1.0
    max_slope_deg: float = 15.0
    vehicle_mode: str = VehicleMode.ROBOTIC_ROVER.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speed_multiplier": round(float(self.speed_multiplier), 3),
            "max_slope_deg": round(float(self.max_slope_deg), 1),
            "vehicle_mode": self.vehicle_mode,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MobilityProfile":
        return cls(
            speed_multiplier=float(data.get("speed_multiplier", 1.0)),
            max_slope_deg=float(data.get("max_slope_deg", 15.0)),
            vehicle_mode=str(data.get("vehicle_mode", VehicleMode.ROBOTIC_ROVER.value)),
        )


@dataclass
class AvailabilityWindow:
    """Active operational sol interval for an exploration unit."""
    start_sol: int = 1
    end_sol: int = 10

    def is_available_on_sol(self, sol: int) -> bool:
        return self.start_sol <= sol <= self.end_sol

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_sol": self.start_sol,
            "end_sol": self.end_sol,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AvailabilityWindow":
        return cls(
            start_sol=int(data.get("start_sol", 1)),
            end_sol=int(data.get("end_sol", 10)),
        )


@dataclass
class ExplorationUnit:
    """
    Simulated surface exploration asset (robotic rover, crew EVA, or scout rover)
    with explicit capabilities and physical operational bounds.
    """
    unit_id: str
    name: str
    unit_type: str = UnitType.ROBOTIC_ROVER.value
    mobility_profile: MobilityProfile = field(default_factory=MobilityProfile)
    availability_window: AvailabilityWindow = field(default_factory=AvailabilityWindow)
    max_duration_per_sortie_s: float = 14400.0  # 4 hours default for robotic_rover
    starting_location_rc: Optional[Tuple[int, int]] = (117, 157)
    status: str = UnitStatus.AVAILABLE.value
    capabilities: List[str] = field(default_factory=lambda: [
        "SURFACE_TRAVERSE",
        "REGOLITH_SAMPLING",
        "HIGH_RESOLUTION_IMAGING",
        "HAZARD_AVOIDANCE"
    ])
    assigned_target_ids: List[str] = field(default_factory=list)
    assigned_sortie_ids: List[str] = field(default_factory=list)
    unsupported_capabilities: List[str] = field(default_factory=lambda: [
        "PHYSICAL_SAMPLE_TRANSFER",
        "DIRECT_POWER_TETHERING",
        "INTER_VEHICLE_TOWING"
    ])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "name": self.name,
            "unit_type": self.unit_type,
            "mobility_profile": self.mobility_profile.to_dict(),
            "availability_window": self.availability_window.to_dict(),
            "max_duration_per_sortie_s": round(float(self.max_duration_per_sortie_s), 1),
            "starting_location_rc": list(self.starting_location_rc) if self.starting_location_rc else None,
            "status": self.status,
            "capabilities": list(self.capabilities),
            "assigned_target_ids": list(self.assigned_target_ids),
            "assigned_sortie_ids": list(self.assigned_sortie_ids),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExplorationUnit":
        return cls(
            unit_id=str(data["unit_id"]),
            name=str(data["name"]),
            unit_type=str(data.get("unit_type", UnitType.ROBOTIC_ROVER.value)),
            mobility_profile=MobilityProfile.from_dict(data.get("mobility_profile", {})),
            availability_window=AvailabilityWindow.from_dict(data.get("availability_window", {})),
            max_duration_per_sortie_s=float(data.get("max_duration_per_sortie_s", 14400.0)),
            starting_location_rc=tuple(data["starting_location_rc"]) if data.get("starting_location_rc") else None,
            status=str(data.get("status", UnitStatus.AVAILABLE.value)),
            capabilities=list(data.get("capabilities", [])),
            assigned_target_ids=list(data.get("assigned_target_ids", [])),
            assigned_sortie_ids=list(data.get("assigned_sortie_ids", [])),
        )


@dataclass
class TargetAllocation:
    """Individual target assignment record with status and diagnostic justification."""
    target_id: str
    status: str = AllocationStatus.UNALLOCATED.value
    assigned_unit_id: Optional[str] = None
    assigned_sol_index: Optional[int] = None
    assigned_sortie_id: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "status": self.status,
            "assigned_unit_id": self.assigned_unit_id,
            "assigned_sol_index": self.assigned_sol_index,
            "assigned_sortie_id": self.assigned_sortie_id,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TargetAllocation":
        return cls(
            target_id=str(data["target_id"]),
            status=str(data.get("status", AllocationStatus.UNALLOCATED.value)),
            assigned_unit_id=data.get("assigned_unit_id"),
            assigned_sol_index=data.get("assigned_sol_index"),
            assigned_sortie_id=data.get("assigned_sortie_id"),
            reason=data.get("reason"),
        )


@dataclass
class TaskHandoff:
    """Formal record transferring task responsibility for a target between simulated units."""
    handoff_id: str
    target_id: str
    source_unit_id: str
    receiving_unit_id: str
    sol_index: int
    status: str = HandoffStatus.PROPOSED.value
    reason: Optional[str] = None
    is_valid: bool = False
    validation_details: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "handoff_id": self.handoff_id,
            "target_id": self.target_id,
            "source_unit_id": self.source_unit_id,
            "receiving_unit_id": self.receiving_unit_id,
            "sol_index": self.sol_index,
            "status": self.status,
            "reason": self.reason,
            "is_valid": self.is_valid,
            "validation_details": list(self.validation_details),
            "rejection_reason": self.rejection_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskHandoff":
        return cls(
            handoff_id=str(data["handoff_id"]),
            target_id=str(data["target_id"]),
            source_unit_id=str(data["source_unit_id"]),
            receiving_unit_id=str(data["receiving_unit_id"]),
            sol_index=int(data["sol_index"]),
            status=str(data.get("status", HandoffStatus.PROPOSED.value)),
            reason=data.get("reason"),
            is_valid=bool(data.get("is_valid", False)),
            validation_details=list(data.get("validation_details", [])),
            rejection_reason=data.get("rejection_reason"),
        )


@dataclass
class CoordinationPlan:
    """
    Coordinated multi-unit planetary surface campaign plan.
    Validates against schemas/api/v1/campaign-coordination.schema.json.
    """
    coordination_id: str
    campaign_id: str
    version: int
    units: List[ExplorationUnit]
    allocation_strategy: str
    target_allocations: List[TargetAllocation]
    strategy_comparison: List[Dict[str, Any]]
    sorties: List[CampaignSortie]
    handoffs: List[TaskHandoff]
    summary: Dict[str, Any]
    limitations_disclaimer: str = COORDINATION_DISCLAIMER
    created_at_utc: Optional[str] = None

    def __post_init__(self):
        if not self.created_at_utc:
            self.created_at_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "coordination_id": self.coordination_id,
            "campaign_id": self.campaign_id,
            "version": self.version,
            "created_at_utc": self.created_at_utc,
            "units": [u.to_dict() for u in self.units],
            "allocation_strategy": self.allocation_strategy,
            "target_allocations": [t.to_dict() for t in self.target_allocations],
            "strategy_comparison": self.strategy_comparison,
            "sorties": [s.to_dict() for s in self.sorties],
            "handoffs": [h.to_dict() for h in self.handoffs],
            "summary": self.summary,
            "limitations_disclaimer": self.limitations_disclaimer,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoordinationPlan":
        units = [ExplorationUnit.from_dict(u) for u in data.get("units", [])]
        allocs = [TargetAllocation.from_dict(t) for t in data.get("target_allocations", [])]
        sorties = [CampaignSortie.from_dict(s) for s in data.get("sorties", [])]
        handoffs = [TaskHandoff.from_dict(h) for h in data.get("handoffs", [])]
        return cls(
            coordination_id=str(data["coordination_id"]),
            campaign_id=str(data["campaign_id"]),
            version=int(data.get("version", 1)),
            created_at_utc=data.get("created_at_utc"),
            units=units,
            allocation_strategy=str(data.get("allocation_strategy", CoordinationStrategy.PRIORITY_FIRST.value)),
            target_allocations=allocs,
            strategy_comparison=list(data.get("strategy_comparison", [])),
            sorties=sorties,
            handoffs=handoffs,
            summary=dict(data.get("summary", {})),
            limitations_disclaimer=str(data.get("limitations_disclaimer", COORDINATION_DISCLAIMER)),
        )


def create_default_units(campaign_config: Optional[CampaignConfig] = None) -> List[ExplorationUnit]:
    """
    Generates a default fleet of two authentic simulated exploration units:
    1. unit_perseverance: Mars 2020 robotic rover analogue (0.035 m/s, 15° max slope, 14,400s / 4 hr budget).
    2. unit_crew_eva_1: Apollo-analogue Crew EVA astronaut pair (2.0 km/h, 25° max slope, 28,800s / 8 hr budget).
    """
    start_rc = campaign_config.base_start_rc if campaign_config else (117, 157)
    max_sols = campaign_config.max_sols if (campaign_config and campaign_config.max_sols) else 10

    rover = ExplorationUnit(
        unit_id="unit_perseverance",
        name="Perseverance Rover Analogue",
        unit_type=UnitType.ROBOTIC_ROVER.value,
        mobility_profile=MobilityProfile(
            speed_multiplier=1.0,
            max_slope_deg=15.0,
            vehicle_mode=VehicleMode.ROBOTIC_ROVER.value,
        ),
        availability_window=AvailabilityWindow(start_sol=1, end_sol=max_sols),
        max_duration_per_sortie_s=14400.0,
        starting_location_rc=start_rc,
        status=UnitStatus.AVAILABLE.value,
        capabilities=["SURFACE_TRAVERSE", "REGOLITH_SAMPLING", "HIGH_RESOLUTION_IMAGING", "HAZARD_AVOIDANCE"],
    )

    crew = ExplorationUnit(
        unit_id="unit_crew_eva_1",
        name="Crew EVA Team Alpha",
        unit_type=UnitType.CREW_EVA.value,
        mobility_profile=MobilityProfile(
            speed_multiplier=1.0,
            max_slope_deg=25.0,
            vehicle_mode=VehicleMode.CREW_EVA.value,
        ),
        availability_window=AvailabilityWindow(start_sol=1, end_sol=max_sols),
        max_duration_per_sortie_s=28800.0,
        starting_location_rc=start_rc,
        status=UnitStatus.AVAILABLE.value,
        capabilities=["SURFACE_TRAVERSE", "FIELD_GEOLOGY_MAPPING", "EXPEDITED_CLIMBING", "HAZARD_AVOIDANCE"],
    )

    return [rover, crew]


def _check_target_reachability_for_unit(
    target: CampaignTarget,
    unit: ExplorationUnit,
    terrain: TerrainGrid,
) -> Tuple[bool, Optional[str]]:
    """Checks whether a target is geographically reachable under a unit's slope limits."""
    # Check slope at target point
    r, c = target.row, target.col
    if not (0 <= r < terrain.height and 0 <= c < terrain.width):
        return False, f"Target coordinates ({r}, {c}) outside terrain grid boundaries."

    slope_at_tgt = terrain.slope_deg[r, c]
    if slope_at_tgt > unit.mobility_profile.max_slope_deg:
        return False, (
            f"Target {target.id} terrain slope ({slope_at_tgt:.1f}°) exceeds "
            f"{unit.name} ceiling ({unit.mobility_profile.max_slope_deg:.1f}°)."
        )

    return True, None


def _simulate_single_unit_sortie(
    unit: ExplorationUnit,
    targets: List[CampaignTarget],
    sol_index: int,
    terrain: TerrainGrid,
    base_rc: Tuple[int, int],
    transform: Any = None,
    obstacle_mask: Optional[np.ndarray] = None,
) -> Optional[CampaignSortie]:
    """Plans a single sortie for a given unit across the specified targets on a specific sol."""
    if not targets:
        return None

    # Filter targets within unit slope ceiling
    feasible_targets = []
    for tgt in targets:
        ok, _ = _check_target_reachability_for_unit(tgt, unit, terrain)
        if ok:
            feasible_targets.append(tgt)

    if not feasible_targets:
        return None

    # Construct ordered coordinates and stop metadata
    ordered_pts = [base_rc] + [(t.row, t.col) for t in feasible_targets] + [base_rc]
    stop_ids = [t.id for t in feasible_targets]
    stop_priorities = [t.priority_score for t in feasible_targets]
    tot_dwell = sum(t.dwell_time_s for t in feasible_targets)
    dwell_per_stop = (tot_dwell / len(feasible_targets)) if feasible_targets else 900.0

    # Route calculation using authentic sequential multistop engine
    p_cfg = PlannerConfig(
        profile="conservative" if unit.mobility_profile.max_slope_deg <= 16.0 else "balanced",
        max_distance_m=None,
    )
    route_res = plan_sequential_multistop_route(
        ordered_points=ordered_pts,
        terrain=terrain,
        stop_ids=stop_ids,
        stop_priorities=stop_priorities,
        config=p_cfg,
        blocked_mask=obstacle_mask,
        vehicle_mode=unit.mobility_profile.vehicle_mode,
        dwell_time_per_stop_s=dwell_per_stop,
        operational_limit_s=unit.max_duration_per_sortie_s,
        speed_multiplier=unit.mobility_profile.speed_multiplier,
    )

    if not route_res or not route_res.is_reachable:
        return None

    sortie_id = f"sort_{unit.unit_id}_sol{sol_index:02d}_{uuid.uuid4().hex[:6]}"
    travel_time_s = route_res.timeline.total_traverse_time_s if route_res.timeline else (route_res.distance_m / 1.11)
    dwell_time_s = tot_dwell
    total_duration_s = travel_time_s + dwell_time_s
    is_feasible = (total_duration_s <= unit.max_duration_per_sortie_s)

    max_slope = 0.0
    if route_res.path:
        max_slope = float(max(terrain.slope_deg[r, c] for r, c in route_res.path))

    sortie = CampaignSortie(
        sortie_id=sortie_id,
        sol_index=sol_index,
        name=f"Sol {sol_index} — {unit.name}",
        start_rc=base_rc,
        goal_rc=base_rc,
        target_ids=[t.id for t in feasible_targets],
        target_names=[t.name for t in feasible_targets],
        path_rc=route_res.path,
        distance_m=route_res.distance_m,
        travel_time_s=travel_time_s,
        dwell_time_s=dwell_time_s,
        total_duration_s=total_duration_s,
        remaining_margin_s=max(0.0, unit.max_duration_per_sortie_s - total_duration_s),
        science_score=sum(t.priority_score for t in feasible_targets),
        terrain_cost=route_res.cost,
        max_slope_deg=max_slope,
        cumulative_climb_m=0.0,
        is_feasible=is_feasible,
        status="PLANNED" if is_feasible else "DISRUPTED",
        unit_id=unit.unit_id,
    )
    return sortie


def _allocate_targets_for_strategy(
    strategy: str,
    units: List[ExplorationUnit],
    targets: List[CampaignTarget],
    terrain: TerrainGrid,
    base_rc: Tuple[int, int],
    max_sols: int,
    completed_target_ids: Set[str],
    blocked_target_ids: Set[str],
    obstacle_mask: Optional[np.ndarray] = None,
) -> Tuple[List[CampaignSortie], List[TargetAllocation], List[str]]:
    """
    Deterministic multi-unit allocation algorithm respecting DAG dependencies,
    unit reachability, duration limits, and strategy rules.
    """
    sorties: List[CampaignSortie] = []
    allocations: List[TargetAllocation] = []
    rationales: List[str] = []

    # Map targets by ID
    tgt_map = {t.id: t for t in targets}
    scheduled_targets: Set[str] = set(completed_target_ids)
    remaining_targets = [t for t in targets if t.id not in completed_target_ids]

    # Pre-mark blocked targets
    for t in remaining_targets:
        if t.id in blocked_target_ids:
            allocations.append(TargetAllocation(
                target_id=t.id,
                status=AllocationStatus.BLOCKED.value,
                reason=f"Target {t.id} explicitly blocked in campaign progress.",
            ))
            scheduled_targets.add(t.id)

    # Unit tracking
    unit_busy_sol: Dict[str, Set[int]] = {u.unit_id: set() for u in units}
    unit_total_duration: Dict[str, float] = {u.unit_id: 0.0 for u in units}
    unit_total_distance: Dict[str, float] = {u.unit_id: 0.0 for u in units}

    # Available targets pool
    unallocated = [t for t in remaining_targets if t.id not in blocked_target_ids]

    for sol in range(1, max_sols + 1):
        # Identify units available on this sol
        avail_units = [
            u for u in units
            if u.status == UnitStatus.AVAILABLE.value
            and u.availability_window.is_available_on_sol(sol)
            and sol not in unit_busy_sol[u.unit_id]
        ]
        if not avail_units:
            continue

        # Find targets whose prerequisites are fully met
        eligible_targets = []
        for t in unallocated:
            prereqs_met = all(p in scheduled_targets for p in t.prerequisites)
            if prereqs_met:
                eligible_targets.append(t)

        if not eligible_targets:
            continue

        # Strategy-specific ordering / assignment
        if strategy == CoordinationStrategy.PRIORITY_FIRST.value:
            # Sort eligible targets by priority descending
            eligible_targets.sort(key=lambda x: x.priority_score, reverse=True)
            for unit in avail_units:
                # Assign up to 2-3 targets within duration limits
                assigned_to_unit: List[CampaignTarget] = []
                cur_dwell = 0.0
                for cand in list(eligible_targets):
                    ok, _ = _check_target_reachability_for_unit(cand, unit, terrain)
                    if not ok:
                        continue
                    if cur_dwell + cand.dwell_time_s + 1800.0 <= unit.max_duration_per_sortie_s:
                        assigned_to_unit.append(cand)
                        cur_dwell += cand.dwell_time_s
                        eligible_targets.remove(cand)
                        if len(assigned_to_unit) >= 3:
                            break

                if assigned_to_unit:
                    sortie = _simulate_single_unit_sortie(
                        unit=unit,
                        targets=assigned_to_unit,
                        sol_index=sol,
                        terrain=terrain,
                        base_rc=base_rc,
                        obstacle_mask=obstacle_mask,
                    )
                    if sortie and sortie.is_feasible:
                        sorties.append(sortie)
                        unit_busy_sol[unit.unit_id].add(sol)
                        unit_total_duration[unit.unit_id] += sortie.total_duration_s
                        unit_total_distance[unit.unit_id] += sortie.distance_m
                        for st in assigned_to_unit:
                            scheduled_targets.add(st.id)
                            unallocated.remove(st)
                            allocations.append(TargetAllocation(
                                target_id=st.id,
                                status=AllocationStatus.ASSIGNED.value,
                                assigned_unit_id=unit.unit_id,
                                assigned_sol_index=sol,
                                assigned_sortie_id=sortie.sortie_id,
                                reason=f"Priority-first allocation to {unit.name} on Sol {sol}.",
                            ))
                        rationales.append(
                            f"Sol {sol}: Allocated {len(assigned_to_unit)} high-priority targets to {unit.name} "
                            f"(Duration: {format_duration(sortie.total_duration_s)})."
                        )

        elif strategy == CoordinationStrategy.BALANCED_WORKLOAD.value:
            # Sort units by least cumulative duration
            avail_units.sort(key=lambda u: unit_total_duration[u.unit_id])
            for unit in avail_units:
                assigned_to_unit = []
                cur_dwell = 0.0
                for cand in list(eligible_targets):
                    ok, _ = _check_target_reachability_for_unit(cand, unit, terrain)
                    if not ok:
                        continue
                    if cur_dwell + cand.dwell_time_s + 1800.0 <= unit.max_duration_per_sortie_s:
                        assigned_to_unit.append(cand)
                        cur_dwell += cand.dwell_time_s
                        eligible_targets.remove(cand)
                        if len(assigned_to_unit) >= 2:
                            break

                if assigned_to_unit:
                    sortie = _simulate_single_unit_sortie(
                        unit=unit,
                        targets=assigned_to_unit,
                        sol_index=sol,
                        terrain=terrain,
                        base_rc=base_rc,
                        obstacle_mask=obstacle_mask,
                    )
                    if sortie and sortie.is_feasible:
                        sorties.append(sortie)
                        unit_busy_sol[unit.unit_id].add(sol)
                        unit_total_duration[unit.unit_id] += sortie.total_duration_s
                        unit_total_distance[unit.unit_id] += sortie.distance_m
                        for st in assigned_to_unit:
                            scheduled_targets.add(st.id)
                            unallocated.remove(st)
                            allocations.append(TargetAllocation(
                                target_id=st.id,
                                status=AllocationStatus.ASSIGNED.value,
                                assigned_unit_id=unit.unit_id,
                                assigned_sol_index=sol,
                                assigned_sortie_id=sortie.sortie_id,
                                reason=f"Balanced-workload allocation to {unit.name} on Sol {sol}.",
                            ))
                        rationales.append(
                            f"Sol {sol}: Balanced workload assigned to {unit.name} "
                            f"(Cumulative: {format_duration(unit_total_duration[unit.unit_id])})."
                        )

        elif strategy == CoordinationStrategy.CAPABILITY_FIRST.value:
            # Match steep/distant targets to high-slope/speed units (crew), low-slope to rover
            for unit in avail_units:
                assigned_to_unit = []
                cur_dwell = 0.0
                # Filter candidates best suited for this unit type
                suited_candidates = []
                for cand in eligible_targets:
                    ok, _ = _check_target_reachability_for_unit(cand, unit, terrain)
                    if not ok:
                        continue
                    cand_slope = terrain.slope_deg[cand.row, cand.col]
                    if unit.mobility_profile.max_slope_deg > 18.0:
                        # Steep-tolerant unit: prefers slope > 10°
                        suited_candidates.append((cand_slope, cand))
                    else:
                        # Gentle slope unit: prefers slope <= 10°
                        suited_candidates.append((-cand_slope, cand))

                suited_candidates.sort(key=lambda x: x[0], reverse=True)
                for _, cand in suited_candidates:
                    if cur_dwell + cand.dwell_time_s + 1800.0 <= unit.max_duration_per_sortie_s:
                        assigned_to_unit.append(cand)
                        cur_dwell += cand.dwell_time_s
                        eligible_targets.remove(cand)
                        if len(assigned_to_unit) >= 2:
                            break

                if assigned_to_unit:
                    sortie = _simulate_single_unit_sortie(
                        unit=unit,
                        targets=assigned_to_unit,
                        sol_index=sol,
                        terrain=terrain,
                        base_rc=base_rc,
                        obstacle_mask=obstacle_mask,
                    )
                    if sortie and sortie.is_feasible:
                        sorties.append(sortie)
                        unit_busy_sol[unit.unit_id].add(sol)
                        unit_total_duration[unit.unit_id] += sortie.total_duration_s
                        unit_total_distance[unit.unit_id] += sortie.distance_m
                        for st in assigned_to_unit:
                            scheduled_targets.add(st.id)
                            unallocated.remove(st)
                            allocations.append(TargetAllocation(
                                target_id=st.id,
                                status=AllocationStatus.ASSIGNED.value,
                                assigned_unit_id=unit.unit_id,
                                assigned_sol_index=sol,
                                assigned_sortie_id=sortie.sortie_id,
                                reason=f"Capability-first match to {unit.name} on Sol {sol}.",
                            ))
                        rationales.append(
                            f"Sol {sol}: Matched {len(assigned_to_unit)} targets to {unit.name} based on slope/speed capabilities."
                        )

    # Process remaining unallocated targets
    for unalloc_tgt in unallocated:
        # Check why it wasn't scheduled
        prereqs_unmet = [p for p in unalloc_tgt.prerequisites if p not in scheduled_targets]
        if prereqs_unmet:
            allocations.append(TargetAllocation(
                target_id=unalloc_tgt.id,
                status=AllocationStatus.BLOCKED.value,
                reason=f"Prerequisite targets {prereqs_unmet} were not completed or scheduled.",
            ))
        else:
            # Check reachability across all units
            reach_flags = [_check_target_reachability_for_unit(unalloc_tgt, u, terrain)[0] for u in units]
            if not any(reach_flags):
                allocations.append(TargetAllocation(
                    target_id=unalloc_tgt.id,
                    status=AllocationStatus.UNREACHABLE.value,
                    reason=f"Target {unalloc_tgt.id} exceeds slope ceilings across all configured units.",
                ))
            else:
                allocations.append(TargetAllocation(
                    target_id=unalloc_tgt.id,
                    status=AllocationStatus.DEFERRED.value,
                    reason=f"Sol budget ({max_sols} sols) exhausted before target {unalloc_tgt.id} could be scheduled.",
                ))

    return sorties, allocations, rationales


def allocate_campaign_coordination(
    campaign: MissionCampaign,
    terrain: TerrainGrid,
    units: Optional[List[ExplorationUnit]] = None,
    strategy: str = CoordinationStrategy.PRIORITY_FIRST.value,
    transform: Any = None,
    obstacle_mask: Optional[np.ndarray] = None,
) -> CoordinationPlan:
    """
    Allocates candidate targets and sorties across multiple simulated units,
    evaluates strategy trade-offs, and validates against the campaign coordination schema.
    """
    if units is None or len(units) == 0:
        units = create_default_units(campaign.config)

    # Bounded limits
    if len(units) > 10:
        raise ValueError("Cannot coordinate more than 10 exploration units simultaneously.")

    # Completed & blocked targets from campaign progress
    completed_targets = set()
    blocked_targets = set()
    if campaign.progress:
        completed_targets.update(campaign.progress.get("completed_target_ids", []))
        blocked_targets.update(campaign.progress.get("blocked_target_ids", []))

    for t in campaign.targets:
        if t.status == TargetStatus.COMPLETED.value:
            completed_targets.add(t.id)

    max_sols = campaign.config.max_sols or 10
    base_rc = campaign.config.base_start_rc or (117, 157)

    # Evaluate all 3 strategies for the comparison matrix
    strategies_to_eval = [
        CoordinationStrategy.PRIORITY_FIRST.value,
        CoordinationStrategy.BALANCED_WORKLOAD.value,
        CoordinationStrategy.CAPABILITY_FIRST.value,
    ]
    strategy_results: Dict[str, Tuple[List[CampaignSortie], List[TargetAllocation], List[str]]] = {}
    strategy_comparison: List[Dict[str, Any]] = []

    for strat in strategies_to_eval:
        s_sorties, s_allocs, s_rationales = _allocate_targets_for_strategy(
            strategy=strat,
            units=units,
            targets=campaign.targets,
            terrain=terrain,
            base_rc=base_rc,
            max_sols=max_sols,
            completed_target_ids=completed_targets,
            blocked_target_ids=blocked_targets,
            obstacle_mask=obstacle_mask,
        )
        strategy_results[strat] = (s_sorties, s_allocs, s_rationales)

        tot_dist = sum(s.distance_m for s in s_sorties)
        tot_dur = sum(s.total_duration_s for s in s_sorties)
        tot_sci = sum(s.science_score for s in s_sorties)
        sched_count = sum(1 for a in s_allocs if a.status == AllocationStatus.ASSIGNED.value)
        def_count = sum(1 for a in s_allocs if a.status in (AllocationStatus.DEFERRED.value, AllocationStatus.UNALLOCATED.value))

        # Per unit duration breakdown
        unit_durs = {u.unit_id: 0.0 for u in units}
        for s in s_sorties:
            if s.unit_id:
                unit_durs[s.unit_id] = unit_durs.get(s.unit_id, 0.0) + s.total_duration_s

        imbalance_s = max(unit_durs.values()) - min(unit_durs.values()) if unit_durs else 0.0

        strategy_comparison.append({
            "strategy": strat,
            "total_sols": len(set(s.sol_index for s in s_sorties)),
            "total_distance_m": round(float(tot_dist), 1),
            "total_duration_s": round(float(tot_dur), 1),
            "total_science_score": round(float(tot_sci), 1),
            "targets_scheduled": sched_count,
            "targets_deferred": def_count,
            "is_feasible": all(s.is_feasible for s in s_sorties),
            "workload_imbalance_s": round(float(imbalance_s), 1),
            "unit_durations_s": {k: round(v, 1) for k, v in unit_durs.items()},
        })

    # Pick the chosen strategy results
    active_sorties, active_allocs, active_rationales = strategy_results.get(
        strategy, strategy_results[CoordinationStrategy.PRIORITY_FIRST.value]
    )

    # Assign sorties and targets back to unit objects for the active plan
    for u in units:
        u.assigned_sortie_ids = [s.sortie_id for s in active_sorties if s.unit_id == u.unit_id]
        u.assigned_target_ids = [
            a.target_id for a in active_allocs
            if a.assigned_unit_id == u.unit_id and a.status == AllocationStatus.ASSIGNED.value
        ]

    tot_dist = sum(s.distance_m for s in active_sorties)
    tot_dur = sum(s.total_duration_s for s in active_sorties)
    tot_sci = sum(s.science_score for s in active_sorties)
    sched_targets = sum(1 for a in active_allocs if a.status == AllocationStatus.ASSIGNED.value)
    unsched_targets = len(campaign.targets) - sched_targets

    summary = {
        "total_units": len(units),
        "total_sols": len(set(s.sol_index for s in active_sorties)),
        "total_sorties": len(active_sorties),
        "total_distance_m": round(float(tot_dist), 1),
        "total_duration_s": round(float(tot_dur), 1),
        "total_science_score": round(float(tot_sci), 1),
        "targets_scheduled": sched_targets,
        "targets_unscheduled": unsched_targets,
        "is_feasible": all(s.is_feasible for s in active_sorties) and (sched_targets > 0),
        "decision_rationales": active_rationales,
    }

    coord_id = f"coord_{uuid.uuid4().hex[:12]}"
    plan = CoordinationPlan(
        coordination_id=coord_id,
        campaign_id=campaign.campaign_id,
        version=campaign.version,
        units=units,
        allocation_strategy=strategy,
        target_allocations=active_allocs,
        strategy_comparison=strategy_comparison,
        sorties=active_sorties,
        handoffs=[],
        summary=summary,
        limitations_disclaimer=COORDINATION_DISCLAIMER,
    )

    # Contract validation
    validate_campaign_coordination_record(plan.to_dict())
    return plan


def validate_and_execute_task_handoff(
    coordination_plan: CoordinationPlan,
    campaign: MissionCampaign,
    terrain: TerrainGrid,
    target_id: str,
    source_unit_id: str,
    receiving_unit_id: str,
    sol_index: int,
    reason: Optional[str] = None,
) -> Tuple[TaskHandoff, CoordinationPlan]:
    """
    Validates and executes a task responsibility handoff between simulated exploration units.
    Enforces that target is not duplicated and recipient has valid availability and slope envelope.
    """
    handoff_id = f"hnd_{uuid.uuid4().hex[:12]}"
    validation_details = []
    is_valid = True
    rejection_reason = None

    # Find units
    unit_map = {u.unit_id: u for u in coordination_plan.units}
    if source_unit_id not in unit_map:
        is_valid = False
        rejection_reason = f"Source unit '{source_unit_id}' not found in coordination fleet."
    elif receiving_unit_id not in unit_map:
        is_valid = False
        rejection_reason = f"Receiving unit '{receiving_unit_id}' not found in coordination fleet."
    elif source_unit_id == receiving_unit_id:
        is_valid = False
        rejection_reason = "Source and receiving units cannot be identical."

    tgt_map = {t.id: t for t in campaign.targets}
    if target_id not in tgt_map:
        is_valid = False
        rejection_reason = f"Target '{target_id}' not found in campaign targets."

    src_unit = unit_map.get(source_unit_id)
    rec_unit = unit_map.get(receiving_unit_id)
    target = tgt_map.get(target_id)

    if is_valid and src_unit and rec_unit and target:
        # Precondition 1: Check source unit actually owns target
        curr_alloc = next((a for a in coordination_plan.target_allocations if a.target_id == target_id), None)
        if not curr_alloc or curr_alloc.assigned_unit_id != source_unit_id:
            is_valid = False
            rejection_reason = f"Target '{target_id}' is not assigned to source unit '{source_unit_id}'."
        else:
            validation_details.append(f"Source unit '{src_unit.name}' verified as current owner of {target_id}.")

        # Precondition 2: Check recipient unit status & availability
        if rec_unit.status != UnitStatus.AVAILABLE.value:
            is_valid = False
            rejection_reason = f"Receiving unit '{rec_unit.name}' is currently {rec_unit.status}."
        elif not rec_unit.availability_window.is_available_on_sol(sol_index):
            is_valid = False
            rejection_reason = f"Receiving unit '{rec_unit.name}' is not available on Sol {sol_index}."
        else:
            validation_details.append(f"Receiving unit '{rec_unit.name}' is available on Sol {sol_index}.")

        # Precondition 3: Check recipient unit slope ceiling
        reach_ok, reach_msg = _check_target_reachability_for_unit(target, rec_unit, terrain)
        if not reach_ok:
            is_valid = False
            rejection_reason = reach_msg
        else:
            validation_details.append(f"Terrain slope check passed for {rec_unit.name}.")

        # Precondition 4: Check DAG prerequisites
        prereqs = target.prerequisites
        for p_id in prereqs:
            p_alloc = next((a for a in coordination_plan.target_allocations if a.target_id == p_id), None)
            if not p_alloc or p_alloc.status != AllocationStatus.ASSIGNED.value:
                is_valid = False
                rejection_reason = f"Prerequisite {p_id} for target {target_id} is not scheduled."
                break
            if p_alloc.assigned_sol_index and p_alloc.assigned_sol_index > sol_index:
                is_valid = False
                rejection_reason = (
                    f"Prerequisite {p_id} is scheduled on Sol {p_alloc.assigned_sol_index}, "
                    f"after handoff Sol {sol_index}."
                )
                break
        if is_valid:
            validation_details.append("Prerequisite DAG timeline dependencies verified.")

    # Construct TaskHandoff record
    handoff = TaskHandoff(
        handoff_id=handoff_id,
        target_id=target_id,
        source_unit_id=source_unit_id,
        receiving_unit_id=receiving_unit_id,
        sol_index=sol_index,
        status=HandoffStatus.ACCEPTED.value if is_valid else HandoffStatus.REJECTED.value,
        reason=reason or "Operational responsibility transfer",
        is_valid=is_valid,
        validation_details=validation_details,
        rejection_reason=rejection_reason,
    )

    if not is_valid:
        # Return updated plan with recorded rejected handoff
        coordination_plan.handoffs.append(handoff)
        return handoff, coordination_plan

    # Apply handoff atomically: update target allocations
    for alloc in coordination_plan.target_allocations:
        if alloc.target_id == target_id:
            alloc.assigned_unit_id = receiving_unit_id
            alloc.assigned_sol_index = sol_index
            alloc.reason = f"Transferred from {source_unit_id} to {receiving_unit_id} via handoff {handoff_id}."

    # Update unit assignment lists
    if target_id in src_unit.assigned_target_ids:
        src_unit.assigned_target_ids.remove(target_id)
    if target_id not in rec_unit.assigned_target_ids:
        rec_unit.assigned_target_ids.append(target_id)

    # Re-route sorties for both affected units
    base_rc = campaign.config.base_start_rc or (117, 157)
    updated_sorties = []
    for s in coordination_plan.sorties:
        if s.sol_index == sol_index and s.unit_id in (source_unit_id, receiving_unit_id):
            # Reconstruct targets for this unit on this sol
            u_tgts = [
                tgt_map[a.target_id] for a in coordination_plan.target_allocations
                if a.assigned_unit_id == s.unit_id and a.assigned_sol_index == sol_index and a.status == AllocationStatus.ASSIGNED.value
            ]
            recomputed = _simulate_single_unit_sortie(
                unit=unit_map[s.unit_id],
                targets=u_tgts,
                sol_index=sol_index,
                terrain=terrain,
                base_rc=base_rc,
            )
            if recomputed:
                updated_sorties.append(recomputed)
        else:
            updated_sorties.append(s)

    coordination_plan.sorties = updated_sorties
    coordination_plan.handoffs.append(handoff)

    # Recalculate summary metrics
    tot_dist = sum(s.distance_m for s in coordination_plan.sorties)
    tot_dur = sum(s.total_duration_s for s in coordination_plan.sorties)
    tot_sci = sum(s.science_score for s in coordination_plan.sorties)
    coordination_plan.summary["total_distance_m"] = round(float(tot_dist), 1)
    coordination_plan.summary["total_duration_s"] = round(float(tot_dur), 1)
    coordination_plan.summary["total_science_score"] = round(float(tot_sci), 1)

    validate_campaign_coordination_record(coordination_plan.to_dict())
    return handoff, coordination_plan


def evaluate_coordination_what_if(
    coordination_plan: CoordinationPlan,
    campaign: MissionCampaign,
    terrain: TerrainGrid,
    scenario_type: str,
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluates what-if disruptions on a coordinated multi-unit campaign:
    - unit_unavailability: Unit goes offline on specific or all sols.
    - unit_mobility_reduction: Unit speed derated or slope ceiling reduced.
    - corridor_closure: Regional obstacle blocking unit traverses.
    """
    # Clone units with modifications
    modified_units = [ExplorationUnit.from_dict(u.to_dict()) for u in coordination_plan.units]
    obstacle_mask = None

    if scenario_type == "unit_unavailability":
        target_unit_id = parameters.get("unit_id")
        for u in modified_units:
            if u.unit_id == target_unit_id:
                u.status = UnitStatus.UNAVAILABLE.value

    elif scenario_type == "unit_mobility_reduction":
        target_unit_id = parameters.get("unit_id")
        speed_factor = float(parameters.get("speed_factor", 0.5))
        max_slope = float(parameters.get("max_slope_deg", 10.0))
        for u in modified_units:
            if u.unit_id == target_unit_id:
                u.mobility_profile.speed_multiplier *= speed_factor
                u.mobility_profile.max_slope_deg = min(u.mobility_profile.max_slope_deg, max_slope)

    elif scenario_type == "corridor_closure":
        center_lat = float(parameters.get("center_lat_deg", 18.38))
        center_lon = float(parameters.get("center_lon_deg", 77.58))
        radius_m = float(parameters.get("radius_m", 150.0))
        # Generate circular mask
        c_r = int(np.clip(round((18.44 - center_lat) * 2000.0), 0, terrain.height - 1))
        c_c = int(np.clip(round((center_lon - 77.40) * 2000.0), 0, terrain.width - 1))
        obstacle_mask = compute_circular_footprint(
            center_rc=(c_r, c_c),
            radius_m=radius_m,
            grid_shape=(terrain.height, terrain.width),
            cell_size_m=20.0,
        )

    # Recompute allocation with modified fleet
    revised_plan = allocate_campaign_coordination(
        campaign=campaign,
        terrain=terrain,
        units=modified_units,
        strategy=coordination_plan.allocation_strategy,
        obstacle_mask=obstacle_mask,
    )

    # Compute deltas
    base_dist = coordination_plan.summary.get("total_distance_m", 0.0)
    rev_dist = revised_plan.summary.get("total_distance_m", 0.0)
    base_dur = coordination_plan.summary.get("total_duration_s", 0.0)
    rev_dur = revised_plan.summary.get("total_duration_s", 0.0)
    base_sci = coordination_plan.summary.get("total_science_score", 0.0)
    rev_sci = revised_plan.summary.get("total_science_score", 0.0)

    base_assigned = {a.target_id: a.assigned_unit_id for a in coordination_plan.target_allocations if a.status == AllocationStatus.ASSIGNED.value}
    rev_assigned = {a.target_id: a.assigned_unit_id for a in revised_plan.target_allocations if a.status == AllocationStatus.ASSIGNED.value}

    reassigned_targets = [
        {"target_id": tid, "previous_unit": base_assigned[tid], "new_unit": rev_assigned[tid]}
        for tid in base_assigned if tid in rev_assigned and base_assigned[tid] != rev_assigned[tid]
    ]
    newly_lost_targets = [tid for tid in base_assigned if tid not in rev_assigned]

    return {
        "scenario_type": scenario_type,
        "parameters": parameters,
        "delta_distance_m": round(rev_dist - base_dist, 1),
        "delta_duration_s": round(rev_dur - base_dur, 1),
        "delta_science_score": round(rev_sci - base_sci, 1),
        "reassigned_targets": reassigned_targets,
        "newly_lost_targets": newly_lost_targets,
        "baseline_scheduled": len(base_assigned),
        "revised_scheduled": len(rev_assigned),
        "is_feasible": revised_plan.summary.get("is_feasible", False),
        "revised_plan": revised_plan.to_dict(),
        "limitations_disclaimer": COORDINATION_DISCLAIMER,
    }


def promote_coordination_to_campaign_version(
    campaign: MissionCampaign,
    coordination_plan: CoordinationPlan,
    terrain: TerrainGrid,
) -> MissionCampaign:
    """
    Promotes an evaluated multi-unit coordination plan into an authoritative new campaign version.
    Increments the version counter (e.g. v1 -> v2), archives the predecessor on disk,
    updates target and sortie records, and stores the coordination payload.
    """
    from marswalk.api.workspace import save_campaign, DEFAULT_CAMPAIGNS_DIR

    # 1. Archive predecessor on disk
    os.makedirs(DEFAULT_CAMPAIGNS_DIR, exist_ok=True)
    v_archive_path = os.path.join(DEFAULT_CAMPAIGNS_DIR, f"{campaign.campaign_id}_v{campaign.version}.json")
    try:
        with open(v_archive_path, "w", encoding="utf-8") as f:
            json.dump(campaign.to_dict(), f, indent=2)
    except Exception:
        pass

    # 2. Advance version
    new_version = campaign.version + 1
    new_revision_id = f"rev_{new_version:02d}_coord"

    # 3. Synchronize targets with allocations
    alloc_map = {a.target_id: a for a in coordination_plan.target_allocations}
    updated_targets: List[CampaignTarget] = []
    for tgt in campaign.targets:
        t_copy = CampaignTarget.from_dict(tgt.to_dict())
        alloc = alloc_map.get(tgt.id)
        if alloc:
            if alloc.status == AllocationStatus.ASSIGNED.value:
                t_copy.status = TargetStatus.SCHEDULED.value
                t_copy.assigned_unit_id = alloc.assigned_unit_id
                t_copy.assigned_sol_index = alloc.assigned_sol_index
                t_copy.assigned_sortie_id = alloc.assigned_sortie_id
                t_copy.unscheduled_reason = None
            else:
                t_copy.status = TargetStatus.DEFERRED.value if alloc.status == AllocationStatus.DEFERRED.value else TargetStatus.UNSCHEDULED.value
                t_copy.assigned_unit_id = None
                t_copy.assigned_sol_index = None
                t_copy.assigned_sortie_id = None
                t_copy.unscheduled_reason = alloc.reason
        updated_targets.append(t_copy)

    # 4. Synchronize sorties
    updated_sorties = [CampaignSortie.from_dict(s.to_dict()) for s in coordination_plan.sorties]

    # 5. Summary metrics
    sched_count = sum(1 for t in updated_targets if t.status == TargetStatus.SCHEDULED.value)
    unsched_count = len(updated_targets) - sched_count
    updated_summary = CampaignSummary(
        total_sols=len(set(s.sol_index for s in updated_sorties)),
        total_sorties=len(updated_sorties),
        total_distance_m=sum(s.distance_m for s in updated_sorties),
        total_travel_time_s=sum(s.travel_time_s for s in updated_sorties),
        total_dwell_time_s=sum(s.dwell_time_s for s in updated_sorties),
        total_duration_s=sum(s.total_duration_s for s in updated_sorties),
        total_science_score=sum(s.science_score for s in updated_sorties),
        targets_total=len(updated_targets),
        targets_scheduled=sched_count,
        targets_unscheduled=unsched_count,
        targets_completed=sum(1 for t in updated_targets if t.status == TargetStatus.COMPLETED.value),
        is_campaign_feasible=coordination_plan.summary.get("is_feasible", False),
        overall_status=CampaignStatus.FEASIBLE.value if coordination_plan.summary.get("is_feasible", False) else CampaignStatus.PARTIALLY_FEASIBLE.value,
        bottlenecks_and_notes=coordination_plan.summary.get("decision_rationales", []),
    )

    # 6. Construct promoted campaign
    promoted_campaign = MissionCampaign(
        campaign_id=campaign.campaign_id,
        name=f"{campaign.name} (v{new_version} Coordinated)",
        description=f"Promoted from multi-unit coordination plan {coordination_plan.coordination_id} (Strategy: {coordination_plan.allocation_strategy})",
        version=new_version,
        revision_id=new_revision_id,
        parent_campaign_id=f"{campaign.campaign_id}_v{campaign.version}",
        region_id=campaign.region_id,
        terrain_dataset_id=campaign.terrain_dataset_id,
        reproducibility_manifest=campaign.reproducibility_manifest,
        config=campaign.config,
        targets=updated_targets,
        sorties=updated_sorties,
        summary=updated_summary,
        disruption=campaign.disruption,
        revision_comparison={
            "promoted_from_coordination_id": coordination_plan.coordination_id,
            "strategy": coordination_plan.allocation_strategy,
            "promotion_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        progress=campaign.progress,
        observations_summary=campaign.observations_summary,
        intelligence_recommendation=campaign.intelligence_recommendation,
        coordination=coordination_plan.to_dict(),
        schema_version="1.0.0",
    )

    save_campaign(promoted_campaign.to_dict())
    return promoted_campaign
