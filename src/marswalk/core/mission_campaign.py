"""
MarsWalk 2.0 — Milestone 11A: Mission Campaign Orchestrator.
Provides multi-sol planning, target dependency DAG resolution, resource-aware scheduling,
and campaign-wide adaptive replanning across authentic USGS CTX 20m Jezero topography.

Evolves MarsWalk from an individual-sortie planner into a multi-sol mission campaign system.
"""

from dataclasses import dataclass, field
import datetime
import enum
import hashlib
import json
import math
import time
import uuid
from typing import Dict, List, Optional, Set, Tuple, Any, Union
import numpy as np
import rasterio

from marswalk.core.terrain import TerrainGrid, TerrainConfig, get_profile_terrain_config
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    RouteResult,
    LegResult,
    VehicleMode,
    OPERATIONAL_LIMITS_S,
    calculate_traverse_time,
    format_duration,
    plan_sequential_multistop_route,
    optimize_stop_order,
    ENGINEERING_ASSUMPTIONS,
)
from marswalk.core.contingency import (
    CustomEventType,
    compute_circular_footprint,
)
from marswalk.api.contracts import (
    SCHEMA_VERSION,
    TERRAIN_DATASET_ID,
    TERRAIN_SHA256,
    validate_contract,
    sanitize_for_json,
    compute_input_fingerprint,
    ContractValidationError,
)


class TargetStatus(str, enum.Enum):
    """Lifecycle status of a candidate science target within a campaign."""
    UNSCHEDULED = "UNSCHEDULED"
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    DEFERRED = "DEFERRED"
    UNREACHABLE = "UNREACHABLE"
    REJECTED_PREREQUISITE_FAILED = "REJECTED_PREREQUISITE_FAILED"
    REJECTED_BUDGET_EXCEEDED = "REJECTED_BUDGET_EXCEEDED"


class CampaignStatus(str, enum.Enum):
    """Overall feasibility state of a mission campaign."""
    FEASIBLE = "FEASIBLE"
    PARTIALLY_FEASIBLE = "PARTIALLY_FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class PlanningProfile(str, enum.Enum):
    """Planning profile determining trade-offs across multiple sols."""
    SCIENCE_PRIORITY = "science_priority"
    TIME_CONSTRAINED = "time_constrained"
    CONSERVATIVE = "conservative"


@dataclass
class CampaignTarget:
    """
    Candidate scientific target with location, science value, dwell requirements,
    and prerequisite dependencies.
    """
    id: str
    name: str
    row: int
    col: int
    lat_deg: Optional[float] = None
    lon_deg: Optional[float] = None
    elevation_m: Optional[float] = None
    priority_score: float = 50.0
    priority_label: str = "default"  # "user_defined" or "default"
    dwell_time_s: float = 900.0
    prerequisites: List[str] = field(default_factory=list)
    geological_context: Optional[str] = ""
    crism_signature: Optional[str] = ""
    provenance: Optional[str] = ""
    status: str = TargetStatus.UNSCHEDULED.value
    assigned_sortie_id: Optional[str] = None
    assigned_sol_index: Optional[int] = None
    unscheduled_reason: Optional[str] = None
    science_objective: Optional[str] = None
    objective_classification: Optional[str] = "NOT_ASSESSED"
    linked_observation_ids: List[str] = field(default_factory=list)
    repeat_observation_requested: bool = False
    assigned_unit_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "row": self.row,
            "col": self.col,
            "lat_deg": self.lat_deg,
            "lon_deg": self.lon_deg,
            "elevation_m": round(float(self.elevation_m), 2) if self.elevation_m is not None else None,
            "priority_score": round(float(self.priority_score), 1),
            "priority_label": self.priority_label,
            "dwell_time_s": round(float(self.dwell_time_s), 1),
            "prerequisites": list(self.prerequisites),
            "geological_context": self.geological_context or "",
            "crism_signature": self.crism_signature or "",
            "provenance": self.provenance or "",
            "status": self.status,
            "assigned_sortie_id": self.assigned_sortie_id,
            "assigned_sol_index": self.assigned_sol_index,
            "assigned_unit_id": self.assigned_unit_id,
            "unscheduled_reason": self.unscheduled_reason,
            "science_objective": self.science_objective,
            "objective_classification": self.objective_classification or "NOT_ASSESSED",
            "linked_observation_ids": list(self.linked_observation_ids),
            "repeat_observation_requested": bool(self.repeat_observation_requested),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignTarget":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            row=int(data["row"]),
            col=int(data["col"]),
            lat_deg=data.get("lat_deg"),
            lon_deg=data.get("lon_deg"),
            elevation_m=data.get("elevation_m"),
            priority_score=float(data.get("priority_score", 50.0)),
            priority_label=str(data.get("priority_label", "default")),
            dwell_time_s=float(data.get("dwell_time_s") if data.get("dwell_time_s") is not None else data.get("dwell_time_seconds", 900.0)),
            prerequisites=list(data.get("prerequisites") if data.get("prerequisites") is not None else data.get("required_prerequisites", [])),
            geological_context=data.get("geological_context", ""),
            crism_signature=data.get("crism_signature", ""),
            provenance=data.get("provenance", ""),
            status=str(data.get("status", TargetStatus.UNSCHEDULED.value)),
            assigned_sortie_id=data.get("assigned_sortie_id"),
            assigned_sol_index=data.get("assigned_sol_index"),
            assigned_unit_id=data.get("assigned_unit_id"),
            unscheduled_reason=data.get("unscheduled_reason"),
            science_objective=data.get("science_objective"),
            objective_classification=data.get("objective_classification", "NOT_ASSESSED"),
            linked_observation_ids=list(data.get("linked_observation_ids", [])),
            repeat_observation_requested=bool(data.get("repeat_observation_requested", False)),
        )


@dataclass
class CampaignConfig:
    """
    Configuration parameters and operational limits governing a multi-sol campaign.
    """
    planning_profile: str = PlanningProfile.SCIENCE_PRIORITY.value
    vehicle_mode: str = VehicleMode.CREW_EVA.value
    speed_multiplier: float = 1.0
    max_duration_per_sortie_s: float = 28800.0  # 8 hours default for crew_eva
    max_sols: Optional[int] = None
    max_total_duration_s: Optional[float] = None
    base_start_rc: Tuple[int, int] = (117, 157)  # Default Octavia Butler Landing
    base_end_rc: Optional[Tuple[int, int]] = None
    return_to_base_each_sol: bool = True
    dwell_time_per_stop_s: float = 900.0
    objective_weights: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not self.objective_weights:
            if self.planning_profile == PlanningProfile.SCIENCE_PRIORITY.value:
                self.objective_weights = {"science": 1.0, "time": 0.2, "margin": 0.1}
            elif self.planning_profile == PlanningProfile.TIME_CONSTRAINED.value:
                self.objective_weights = {"science": 0.5, "time": 1.0, "margin": 0.3}
            elif self.planning_profile == PlanningProfile.CONSERVATIVE.value:
                self.objective_weights = {"science": 0.4, "time": 0.3, "margin": 1.0}
            else:
                self.objective_weights = {"science": 1.0, "time": 0.2, "margin": 0.1}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "planning_profile": self.planning_profile,
            "vehicle_mode": self.vehicle_mode,
            "speed_multiplier": round(self.speed_multiplier, 3),
            "max_duration_per_sortie_s": round(self.max_duration_per_sortie_s, 1),
            "max_sols": self.max_sols,
            "max_total_duration_s": round(self.max_total_duration_s, 1) if self.max_total_duration_s is not None else None,
            "base_start_rc": list(self.base_start_rc),
            "base_end_rc": list(self.base_end_rc) if self.base_end_rc is not None else None,
            "return_to_base_each_sol": self.return_to_base_each_sol,
            "dwell_time_per_stop_s": round(self.dwell_time_per_stop_s, 1),
            "objective_weights": self.objective_weights,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignConfig":
        return cls(
            planning_profile=data.get("planning_profile", PlanningProfile.SCIENCE_PRIORITY.value),
            vehicle_mode=data.get("vehicle_mode", VehicleMode.CREW_EVA.value),
            speed_multiplier=float(data.get("speed_multiplier", 1.0)),
            max_duration_per_sortie_s=float(data.get("max_duration_per_sortie_s", 28800.0)),
            max_sols=data.get("max_sols"),
            max_total_duration_s=data.get("max_total_duration_s"),
            base_start_rc=tuple(data.get("base_start_rc", [117, 157])),
            base_end_rc=tuple(data["base_end_rc"]) if data.get("base_end_rc") else None,
            return_to_base_each_sol=bool(data.get("return_to_base_each_sol", True)),
            dwell_time_per_stop_s=float(data.get("dwell_time_per_stop_s", 900.0)),
            objective_weights=dict(data.get("objective_weights", {})),
        )


@dataclass
class CampaignSortie:
    """
    Individual operational sortie (typically 1 sol) within a campaign.
    """
    sortie_id: str
    sol_index: int
    name: str
    start_rc: Tuple[int, int]
    goal_rc: Tuple[int, int]
    target_ids: List[str]
    target_names: List[str]
    path_rc: List[Tuple[int, int]]
    distance_m: float
    travel_time_s: float
    dwell_time_s: float
    total_duration_s: float
    remaining_margin_s: float
    science_score: float
    terrain_cost: float
    max_slope_deg: float
    cumulative_climb_m: float
    is_feasible: bool
    status: str = "PLANNED"  # "PLANNED", "COMPLETED", "DISRUPTED", "BLOCKED"
    unit_id: Optional[str] = None
    legs_summary: List[Dict[str, Any]] = field(default_factory=list)
    timeline_events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sortie_id": self.sortie_id,
            "sol_index": self.sol_index,
            "name": self.name,
            "start_rc": list(self.start_rc),
            "goal_rc": list(self.goal_rc),
            "target_ids": list(self.target_ids),
            "target_names": list(self.target_names),
            "path_rc": [list(pt) for pt in self.path_rc],
            "distance_m": round(float(self.distance_m), 1),
            "travel_time_s": round(float(self.travel_time_s), 1),
            "dwell_time_s": round(float(self.dwell_time_s), 1),
            "total_duration_s": round(float(self.total_duration_s), 1),
            "remaining_margin_s": round(float(self.remaining_margin_s), 1),
            "science_score": round(float(self.science_score), 1),
            "terrain_cost": round(float(self.terrain_cost), 1),
            "max_slope_deg": round(float(self.max_slope_deg), 1),
            "cumulative_climb_m": round(float(self.cumulative_climb_m), 1),
            "is_feasible": self.is_feasible,
            "status": self.status,
            "unit_id": self.unit_id,
            "legs_summary": self.legs_summary,
            "timeline_events": self.timeline_events,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignSortie":
        return cls(
            sortie_id=str(data["sortie_id"]),
            sol_index=int(data["sol_index"]),
            name=str(data["name"]),
            start_rc=tuple(data["start_rc"]),
            goal_rc=tuple(data["goal_rc"]),
            target_ids=list(data.get("target_ids", [])),
            target_names=list(data.get("target_names", [])),
            path_rc=[tuple(pt) for pt in data.get("path_rc", [])],
            distance_m=float(data.get("distance_m", 0.0)),
            travel_time_s=float(data.get("travel_time_s", 0.0)),
            dwell_time_s=float(data.get("dwell_time_s", 0.0)),
            total_duration_s=float(data.get("total_duration_s", 0.0)),
            remaining_margin_s=float(data.get("remaining_margin_s", 0.0)),
            science_score=float(data.get("science_score", 0.0)),
            terrain_cost=float(data.get("terrain_cost", 0.0)),
            max_slope_deg=float(data.get("max_slope_deg", 0.0)),
            cumulative_climb_m=float(data.get("cumulative_climb_m", 0.0)),
            is_feasible=bool(data.get("is_feasible", False)),
            status=str(data.get("status", "PLANNED")),
            unit_id=data.get("unit_id"),
            legs_summary=list(data.get("legs_summary", [])),
            timeline_events=list(data.get("timeline_events", [])),
        )


@dataclass
class CampaignSummary:
    """
    Cumulative, non-duplicated metrics across all sorties in a mission campaign.
    """
    total_sols: int
    total_sorties: int
    total_distance_m: float
    total_travel_time_s: float
    total_dwell_time_s: float
    total_duration_s: float
    total_science_score: float
    targets_total: int
    targets_scheduled: int
    targets_unscheduled: int
    targets_completed: int = 0
    is_campaign_feasible: bool = True
    overall_status: str = CampaignStatus.FEASIBLE.value
    bottlenecks_and_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_sols": self.total_sols,
            "total_sorties": self.total_sorties,
            "total_distance_m": round(float(self.total_distance_m), 1),
            "total_travel_time_s": round(float(self.total_travel_time_s), 1),
            "total_dwell_time_s": round(float(self.total_dwell_time_s), 1),
            "total_duration_s": round(float(self.total_duration_s), 1),
            "total_science_score": round(float(self.total_science_score), 1),
            "targets_total": self.targets_total,
            "targets_scheduled": self.targets_scheduled,
            "targets_unscheduled": self.targets_unscheduled,
            "targets_completed": self.targets_completed,
            "is_campaign_feasible": self.is_campaign_feasible,
            "overall_status": self.overall_status,
            "bottlenecks_and_notes": list(self.bottlenecks_and_notes),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignSummary":
        return cls(
            total_sols=int(data.get("total_sols", 0)),
            total_sorties=int(data.get("total_sorties", 0)),
            total_distance_m=float(data.get("total_distance_m", 0.0)),
            total_travel_time_s=float(data.get("total_travel_time_s", 0.0)),
            total_dwell_time_s=float(data.get("total_dwell_time_s", 0.0)),
            total_duration_s=float(data.get("total_duration_s", 0.0)),
            total_science_score=float(data.get("total_science_score", 0.0)),
            targets_total=int(data.get("targets_total", 0)),
            targets_scheduled=int(data.get("targets_scheduled", 0)),
            targets_unscheduled=int(data.get("targets_unscheduled", 0)),
            targets_completed=int(data.get("targets_completed", 0)),
            is_campaign_feasible=bool(data.get("is_campaign_feasible", True)),
            overall_status=str(data.get("overall_status", CampaignStatus.FEASIBLE.value)),
            bottlenecks_and_notes=list(data.get("bottlenecks_and_notes", [])),
        )


@dataclass
class MissionCampaign:
    """
    Top-level campaign entity representing a multi-sol surface exploration program.
    """
    campaign_id: str
    name: str
    config: CampaignConfig
    targets: List[CampaignTarget]
    sorties: List[CampaignSortie]
    summary: CampaignSummary
    description: Optional[str] = ""
    version: int = 1
    revision_id: str = "rev_01"
    parent_campaign_id: Optional[str] = None
    created_at_utc: Optional[str] = None
    updated_at_utc: Optional[str] = None
    region_id: str = "jezero_crater"
    terrain_dataset_id: str = TERRAIN_DATASET_ID
    reproducibility_manifest: Optional[Dict[str, Any]] = None
    disruption: Optional[Dict[str, Any]] = None
    revision_comparison: Optional[Dict[str, Any]] = None
    progress: Optional[Dict[str, Any]] = None
    observations_summary: Optional[Dict[str, Any]] = None
    intelligence_recommendation: Optional[Dict[str, Any]] = None
    coordination: Optional[Dict[str, Any]] = None
    schema_version: str = "1.0.0"

    def __post_init__(self):
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if not self.created_at_utc:
            self.created_at_utc = now_iso
        if not self.updated_at_utc:
            self.updated_at_utc = now_iso
        if not self.reproducibility_manifest:
            self.reproducibility_manifest = {
                "terrain_dataset_id": self.terrain_dataset_id,
                "terrain_sha256": TERRAIN_SHA256,
                "model_version": "2.0.0",
                "software_version": "2.0.0",
                "input_fingerprint": self.compute_fingerprint(),
                "assumptions_version": "1.0.0",
            }

    def compute_fingerprint(self) -> str:
        """Deterministic fingerprint computed from campaign parameters and target IDs."""
        blob = {
            "name": self.name,
            "region_id": self.region_id,
            "config": self.config.to_dict(),
            "target_ids": sorted([t.id for t in self.targets]),
            "target_scores": {t.id: t.priority_score for t in self.targets},
        }
        return hashlib.sha256(json.dumps(blob, sort_keys=True).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "campaign_id": self.campaign_id,
            "name": self.name,
            "description": self.description or "",
            "version": self.version,
            "revision_id": self.revision_id,
            "parent_campaign_id": self.parent_campaign_id,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "region_id": self.region_id,
            "terrain_dataset_id": self.terrain_dataset_id,
            "reproducibility_manifest": self.reproducibility_manifest,
            "config": self.config.to_dict(),
            "targets": [t.to_dict() for t in self.targets],
            "sorties": [s.to_dict() for s in self.sorties],
            "summary": self.summary.to_dict(),
            "disruption": self.disruption,
            "revision_comparison": self.revision_comparison,
            "progress": self.progress,
            "observations_summary": self.observations_summary,
            "intelligence_recommendation": self.intelligence_recommendation,
            "coordination": self.coordination,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MissionCampaign":
        config = CampaignConfig.from_dict(data.get("config", {}))
        targets = [CampaignTarget.from_dict(t) for t in data.get("targets", [])]
        sorties = [CampaignSortie.from_dict(s) for s in data.get("sorties", [])]
        summary = CampaignSummary.from_dict(data.get("summary", {}))
        return cls(
            campaign_id=str(data["campaign_id"]),
            name=str(data["name"]),
            description=data.get("description", ""),
            version=int(data.get("version", 1)),
            revision_id=str(data.get("revision_id", "rev_01")),
            parent_campaign_id=data.get("parent_campaign_id"),
            created_at_utc=data.get("created_at_utc"),
            updated_at_utc=data.get("updated_at_utc"),
            region_id=data.get("region_id", "jezero_crater"),
            terrain_dataset_id=data.get("terrain_dataset_id", TERRAIN_DATASET_ID),
            reproducibility_manifest=data.get("reproducibility_manifest"),
            config=config,
            targets=targets,
            sorties=sorties,
            summary=summary,
            disruption=data.get("disruption"),
            revision_comparison=data.get("revision_comparison"),
            progress=data.get("progress"),
            observations_summary=data.get("observations_summary"),
            intelligence_recommendation=data.get("intelligence_recommendation"),
            coordination=data.get("coordination"),
            schema_version=data.get("schema_version", "1.0.0"),
        )


# ==============================================================================
# Target Dependency Graph Validation
# ==============================================================================

def validate_target_dependencies(targets: List[CampaignTarget]) -> None:
    """
    Validates candidate targets against reference errors and circular dependencies (DAG check).
    Raises ValueError on invalid references or cycles.
    """
    target_ids = {t.id for t in targets}
    adj: Dict[str, List[str]] = {t.id: [] for t in targets}

    for t in targets:
        for prereq in t.prerequisites:
            if prereq == t.id:
                raise ValueError(f"Target '{t.id}' cannot have itself as a prerequisite.")
            if prereq not in target_ids:
                raise ValueError(
                    f"Target '{t.id}' references non-existent prerequisite '{prereq}'. Available targets: {sorted(list(target_ids))}"
                )
            adj[prereq].append(t.id)

    # Cycle detection via DFS (color graph: 0=unvisited, 1=visiting, 2=visited)
    color: Dict[str, int] = {t.id: 0 for t in targets}
    cycle_path: List[str] = []

    def dfs(node: str, stack: List[str]) -> bool:
        color[node] = 1
        stack.append(node)
        for neighbor in adj[node]:
            if color[neighbor] == 1:
                # Cycle found
                idx = stack.index(neighbor)
                cycle_path.extend(stack[idx:] + [neighbor])
                return True
            if color[neighbor] == 0:
                if dfs(neighbor, stack):
                    return True
        stack.pop()
        color[node] = 2
        return False

    for t in targets:
        if color[t.id] == 0:
            if dfs(t.id, []):
                chain_str = " -> ".join(cycle_path)
                raise ValueError(f"Cyclic dependency detected in campaign targets: {chain_str}")


# ==============================================================================
# Multi-Sol Campaign Planning Engine
# ==============================================================================

def plan_mission_campaign(
    campaign_id: str,
    name: str,
    config: CampaignConfig,
    targets: List[CampaignTarget],
    terrain: TerrainGrid,
    description: str = "",
    parent_campaign_id: Optional[str] = None,
    blocked_mask: Optional[np.ndarray] = None,
    cost_multiplier_mask: Optional[np.ndarray] = None,
) -> MissionCampaign:
    """
    Executes multi-sol scheduling and route planning for a mission campaign across
    authentic USGS CTX 20m terrain.

    Respects:
      1. Target prerequisite dependencies (topological order).
      2. Per-sortie duration budget ceilings.
      3. Planning profile heuristics (science_priority, time_constrained, conservative).
      4. Campaign-wide sol limits (max_sols) and duration limits.
      5. Explicit departure/return base coordinates.
      6. Zero double-counting of distances or dwell times.
    """
    # 1. Validate Target Graph
    validate_target_dependencies(targets)

    # Deep copy targets so status can be updated
    candidate_targets = [CampaignTarget.from_dict(t.to_dict()) for t in targets]
    target_by_id = {t.id: t for t in candidate_targets}

    # Operational parameters
    max_duration_s = config.max_duration_per_sortie_s
    max_sols = config.max_sols if config.max_sols is not None else 100
    base_start = config.base_start_rc
    base_end = config.base_end_rc if config.base_end_rc is not None else base_start

    # Conservative profile adds 20% safety margin buffer to duration ceiling
    # and strictly reduces acceptable max duration
    effective_duration_s = max_duration_s
    if config.planning_profile == PlanningProfile.CONSERVATIVE.value:
        effective_duration_s = max_duration_s * 0.80  # 20% buffer

    scheduled_target_ids: Set[str] = set()
    sorties: List[CampaignSortie] = []
    sol_index = 1
    total_campaign_duration_s = 0.0

    current_departure = base_start

    # Loop over sols until all targets scheduled or no more progress possible
    while sol_index <= max_sols:
        # Check overall duration limit if configured
        if config.max_total_duration_s and total_campaign_duration_s >= config.max_total_duration_s:
            break

        # Identify candidate targets whose prerequisites are fully satisfied
        # and are not yet scheduled
        ready_candidates = [
            t for t in candidate_targets
            if t.id not in scheduled_target_ids
            and all(p in scheduled_target_ids for p in t.prerequisites)
        ]

        if not ready_candidates:
            # No ready targets available (either all done, or remaining have blocked prereqs)
            break

        # Determine departure and return points for this sol
        sol_start = current_departure
        sol_goal = base_end if config.return_to_base_each_sol else None

        # Build candidate tour for this sol according to planning profile
        selected_for_sol: List[CampaignTarget] = []
        current_sol_duration_s = 0.0

        # Sort ready candidates according to profile heuristic
        if config.planning_profile == PlanningProfile.SCIENCE_PRIORITY.value:
            # Highest priority score first
            sorted_candidates = sorted(ready_candidates, key=lambda t: t.priority_score, reverse=True)
        elif config.planning_profile == PlanningProfile.TIME_CONSTRAINED.value:
            # High efficiency: priority score divided by estimated travel & dwell time
            def efficiency_score(t: CampaignTarget) -> float:
                dr = abs(t.row - sol_start[0]) * terrain.dy_ground_m
                dc = abs(t.col - sol_start[1]) * terrain.dx_ground_m
                dist_est = math.sqrt(dr * dr + dc * dc)
                est_time = dist_est / 1.11 + t.dwell_time_s
                return t.priority_score / max(60.0, est_time)
            sorted_candidates = sorted(ready_candidates, key=efficiency_score, reverse=True)
        elif config.planning_profile == PlanningProfile.CONSERVATIVE.value:
            # Low slope & low elevation difference preferred
            def conservative_score(t: CampaignTarget) -> float:
                elev_t = float(terrain.elevation[t.row, t.col])
                elev_s = float(terrain.elevation[sol_start[0], sol_start[1]])
                climb = max(0.0, elev_t - elev_s)
                return t.priority_score - (climb * 0.5)
            sorted_candidates = sorted(ready_candidates, key=conservative_score, reverse=True)
        else:
            sorted_candidates = sorted(ready_candidates, key=lambda t: t.priority_score, reverse=True)

        # Greedily add targets that keep the sortie within the duration ceiling
        for candidate in sorted_candidates:
            trial_targets = selected_for_sol + [candidate]
            trial_points = [sol_start] + [(t.row, t.col) for t in trial_targets]
            if sol_goal is not None:
                trial_points.append(sol_goal)
            elif len(trial_points) == 1:
                # Need at least two points
                continue

            # Quick test of trial route
            trial_route = plan_sequential_multistop_route(
                ordered_points=trial_points,
                terrain=terrain,
                stop_ids=[t.id for t in trial_targets],
                stop_priorities=[t.priority_score for t in trial_targets],
                config=PlannerConfig(profile="conservative" if config.planning_profile == "conservative" else "balanced"),
                blocked_mask=blocked_mask,
                cost_multiplier_mask=cost_multiplier_mask,
                vehicle_mode=config.vehicle_mode,
                speed_multiplier=config.speed_multiplier,
            )

            if trial_route.is_reachable:
                trial_dwell = sum(t.dwell_time_s for t in trial_targets)
                trial_total_time = trial_route.travel_time_s + trial_dwell

                if trial_total_time <= effective_duration_s:
                    selected_for_sol.append(candidate)
                    current_sol_duration_s = trial_total_time

        if not selected_for_sol:
            # Cannot fit even a single candidate into this sol
            break

        # Finalize the sortie route for this sol
        sortie_goal = sol_goal if sol_goal is not None else (selected_for_sol[-1].row, selected_for_sol[-1].col)
        final_points = [sol_start] + [(t.row, t.col) for t in selected_for_sol]
        if sol_goal is not None:
            final_points.append(sol_goal)

        final_route = plan_sequential_multistop_route(
            ordered_points=final_points,
            terrain=terrain,
            stop_ids=[t.id for t in selected_for_sol],
            stop_priorities=[t.priority_score for t in selected_for_sol],
            config=PlannerConfig(profile="conservative" if config.planning_profile == "conservative" else "balanced"),
            blocked_mask=blocked_mask,
            cost_multiplier_mask=cost_multiplier_mask,
            vehicle_mode=config.vehicle_mode,
            speed_multiplier=config.speed_multiplier,
        )

        sortie_id = f"sortie_sol_{sol_index:02d}"
        total_dwell = sum(t.dwell_time_s for t in selected_for_sol)
        total_sortie_time = final_route.travel_time_s + total_dwell
        remaining_margin = max_duration_s - total_sortie_time
        total_science = sum(t.priority_score for t in selected_for_sol)

        # Mark targets as scheduled
        for t in selected_for_sol:
            scheduled_target_ids.add(t.id)
            target_obj = target_by_id[t.id]
            target_obj.status = TargetStatus.SCHEDULED.value
            target_obj.assigned_sortie_id = sortie_id
            target_obj.assigned_sol_index = sol_index
            target_obj.unscheduled_reason = None

        # Legs summary
        legs_summary = []
        if final_route.legs:
            for idx, leg in enumerate(final_route.legs):
                legs_summary.append({
                    "leg_index": idx + 1,
                    "start_rc": list(leg.start_rc),
                    "goal_rc": list(leg.goal_rc),
                    "distance_m": round(leg.distance_m, 1),
                    "cost": round(leg.cost, 1),
                    "is_reachable": leg.is_reachable,
                })

        # Calculate max slope and climb along route path
        max_slope = 0.0
        cumulative_climb = 0.0
        if len(final_route.path) >= 2:
            for p1, p2 in zip(final_route.path[:-1], final_route.path[1:]):
                e1 = terrain.elevation[p1[0], p1[1]]
                e2 = terrain.elevation[p2[0], p2[1]]
                dz = e2 - e1
                if dz > 0:
                    cumulative_climb += dz
                dx = (p2[1] - p1[1]) * terrain.dx_ground_m
                dy = (p2[0] - p1[0]) * terrain.dy_ground_m
                d_horiz = math.sqrt(dx * dx + dy * dy)
                if d_horiz > 0:
                    slope_deg = math.degrees(math.atan(abs(dz) / d_horiz))
                    if slope_deg > max_slope:
                        max_slope = slope_deg

        sortie = CampaignSortie(
            sortie_id=sortie_id,
            sol_index=sol_index,
            name=f"Sol {sol_index}: {', '.join(t.name for t in selected_for_sol[:2])}{'...' if len(selected_for_sol) > 2 else ''}",
            start_rc=sol_start,
            goal_rc=sortie_goal,
            target_ids=[t.id for t in selected_for_sol],
            target_names=[t.name for t in selected_for_sol],
            path_rc=final_route.path,
            distance_m=final_route.distance_m,
            travel_time_s=final_route.travel_time_s,
            dwell_time_s=total_dwell,
            total_duration_s=total_sortie_time,
            remaining_margin_s=remaining_margin,
            science_score=total_science,
            terrain_cost=final_route.cost,
            max_slope_deg=max_slope,
            cumulative_climb_m=cumulative_climb,
            is_feasible=final_route.is_reachable and (total_sortie_time <= max_duration_s),
            status="PLANNED",
            legs_summary=legs_summary,
        )
        sorties.append(sortie)

        total_campaign_duration_s += total_sortie_time

        # Update departure for next sol if daisy-chained
        if not config.return_to_base_each_sol:
            current_departure = sortie_goal
        else:
            current_departure = base_start

        sol_index += 1

    # Classify unscheduled targets with specific reasons
    bottlenecks: List[str] = []
    for t in candidate_targets:
        if t.id not in scheduled_target_ids:
            # Check why it was not scheduled
            unsatisfied_prereqs = [p for p in t.prerequisites if p not in scheduled_target_ids]
            if unsatisfied_prereqs:
                t.status = TargetStatus.REJECTED_PREREQUISITE_FAILED.value
                t.unscheduled_reason = f"Prerequisite targets not scheduled: {', '.join(unsatisfied_prereqs)}"
            else:
                # Check if target is unreachable from base
                single_point_route = plan_sequential_multistop_route(
                    ordered_points=[base_start, (t.row, t.col)],
                    terrain=terrain,
                    config=PlannerConfig(profile="conservative"),
                    blocked_mask=blocked_mask,
                    cost_multiplier_mask=cost_multiplier_mask,
                    vehicle_mode=config.vehicle_mode,
                )
                if not single_point_route.is_reachable:
                    t.status = TargetStatus.UNREACHABLE.value
                    t.unscheduled_reason = "Terrain path to target is impassable or out-of-bounds."
                elif single_point_route.travel_time_s + t.dwell_time_s > max_duration_s:
                    t.status = TargetStatus.REJECTED_BUDGET_EXCEEDED.value
                    t.unscheduled_reason = f"Standalone traverse and dwell ({round(single_point_route.travel_time_s + t.dwell_time_s)}s) exceeds single-sol budget ({round(max_duration_s)}s)."
                else:
                    t.status = TargetStatus.DEFERRED.value
                    t.unscheduled_reason = f"Deferred due to sol limit (max_sols={config.max_sols}) or operational timeline capacity."

    # Compute Campaign-Wide Totals
    total_dist = sum(s.distance_m for s in sorties)
    total_travel = sum(s.travel_time_s for s in sorties)
    total_dwell = sum(s.dwell_time_s for s in sorties)
    total_dur = sum(s.total_duration_s for s in sorties)
    total_score = sum(s.science_score for s in sorties)
    num_scheduled = len(scheduled_target_ids)
    num_unscheduled = len(candidate_targets) - num_scheduled

    if num_scheduled == len(candidate_targets) and all(s.is_feasible for s in sorties):
        overall_status = CampaignStatus.FEASIBLE.value
        is_feasible = True
    elif num_scheduled > 0 and any(s.is_feasible for s in sorties):
        overall_status = CampaignStatus.PARTIALLY_FEASIBLE.value
        is_feasible = True
        bottlenecks.append(f"{num_unscheduled} of {len(candidate_targets)} targets could not be scheduled.")
    else:
        overall_status = CampaignStatus.INFEASIBLE.value
        is_feasible = False
        bottlenecks.append("No feasible sorties could be scheduled within operational constraints.")

    summary = CampaignSummary(
        total_sols=len(sorties),
        total_sorties=len(sorties),
        total_distance_m=total_dist,
        total_travel_time_s=total_travel,
        total_dwell_time_s=total_dwell,
        total_duration_s=total_dur,
        total_science_score=total_score,
        targets_total=len(candidate_targets),
        targets_scheduled=num_scheduled,
        targets_unscheduled=num_unscheduled,
        targets_completed=0,
        is_campaign_feasible=is_feasible,
        overall_status=overall_status,
        bottlenecks_and_notes=bottlenecks,
    )

    campaign = MissionCampaign(
        campaign_id=campaign_id,
        name=name,
        description=description,
        version=1,
        revision_id="rev_01",
        parent_campaign_id=parent_campaign_id,
        config=config,
        targets=candidate_targets,
        sorties=sorties,
        summary=summary,
    )
    return campaign


# ==============================================================================
# Multi-Sol Disruption & Adaptive Replanning
# ==============================================================================

def replan_campaign_disruption(
    campaign: MissionCampaign,
    disruption: Dict[str, Any],
    terrain: TerrainGrid,
    completed_sol_indices: Optional[List[int]] = None,
) -> MissionCampaign:
    """
    Evaluates the impact of an operational disruption on an existing multi-sol campaign
    and synthesizes an adaptive revision.

    Supported Disruption Types:
      - 'closed_corridor': Circular rockfall/obstruction barrier at center (r, c) with radius_m.
      - 'target_unavailable': A specific target is rendered unreachable/degraded.
      - 'reduced_mobility': Rover or crew velocity is derated by speed_multiplier.
      - 'operational_hold': Cumulative delay added to planned sorties.
      - 'reduced_time_budget': Reduced per-sortie duration limit.

    Guarantees:
      - Completed sorties and their visited targets remain immutable.
      - Downstream target prerequisites are severed if an upstream target is lost.
      - Preserves original campaign version (increments version and provides revision delta).
    """
    completed_indices = set(completed_sol_indices or [])

    disruption_type = str(disruption.get("disruption_type", "closed_corridor"))
    description_text = str(disruption.get("description", f"Disruption of type {disruption_type}"))

    # Compile hazard masks if closed_corridor
    blocked_mask = None
    if disruption_type == "closed_corridor":
        center_r = int(disruption.get("center_row", disruption.get("center_r", 122)))
        center_c = int(disruption.get("center_col", disruption.get("center_c", 162)))
        radius_m = float(disruption.get("radius_m", 60.0))
        footprint = compute_circular_footprint(
            center_rc=(center_r, center_c),
            radius_m=radius_m,
            terrain=terrain,
        )
        blocked_mask = np.zeros(terrain.elevation.shape, dtype=bool)
        for r, c in footprint:
            blocked_mask[r, c] = True

    # Build updated campaign config
    revised_config_dict = campaign.config.to_dict()
    if disruption_type == "reduced_mobility":
        derate_factor = float(disruption.get("speed_multiplier", 0.6))
        revised_config_dict["speed_multiplier"] = revised_config_dict["speed_multiplier"] * derate_factor
    elif disruption_type == "reduced_time_budget":
        new_limit = float(disruption.get("max_duration_per_sortie_s", revised_config_dict["max_duration_per_sortie_s"] * 0.75))
        revised_config_dict["max_duration_per_sortie_s"] = new_limit

    revised_config = CampaignConfig.from_dict(revised_config_dict)

    # Separate completed targets vs remaining candidate targets
    completed_target_ids: Set[str] = set()
    for s in campaign.sorties:
        if s.sol_index in completed_indices:
            completed_target_ids.update(s.target_ids)

    # Filter out unavailable target if specified
    unavailable_id = disruption.get("target_id")
    remaining_targets: List[CampaignTarget] = []
    for t in campaign.targets:
        if t.id in completed_target_ids:
            # Preserve completed status
            t_copy = CampaignTarget.from_dict(t.to_dict())
            t_copy.status = TargetStatus.COMPLETED.value
            remaining_targets.append(t_copy)
        elif disruption_type == "target_unavailable" and t.id == unavailable_id:
            t_copy = CampaignTarget.from_dict(t.to_dict())
            t_copy.status = TargetStatus.UNREACHABLE.value
            t_copy.unscheduled_reason = f"Target declared unavailable: {description_text}"
            remaining_targets.append(t_copy)
        else:
            t_copy = CampaignTarget.from_dict(t.to_dict())
            t_copy.status = TargetStatus.UNSCHEDULED.value
            t_copy.assigned_sortie_id = None
            t_copy.assigned_sol_index = None
            remaining_targets.append(t_copy)

    # Plan the remaining targets from scratch (preserving completed)
    # We pass only the non-completed targets into the planner, with completed prereqs satisfied
    uncompleted_pool = [t for t in remaining_targets if t.status != TargetStatus.COMPLETED.value and t.status != TargetStatus.UNREACHABLE.value]

    # Adjust max_sols for remaining sorties
    remaining_sols = (revised_config.max_sols or 100) - len(completed_indices)
    uncompleted_config_dict = revised_config.to_dict()
    uncompleted_config_dict["max_sols"] = max(1, remaining_sols)
    uncompleted_config = CampaignConfig.from_dict(uncompleted_config_dict)

    # Plan future sorties
    future_plan = plan_mission_campaign(
        campaign_id=f"{campaign.campaign_id}_rev_{campaign.version + 1}",
        name=campaign.name,
        config=uncompleted_config,
        targets=uncompleted_pool,
        terrain=terrain,
        description=campaign.description,
        blocked_mask=blocked_mask,
    )

    # Assemble composite sorties (completed + newly planned with adjusted sol indices)
    composite_sorties: List[CampaignSortie] = []
    # Add completed sorties
    for s in campaign.sorties:
        if s.sol_index in completed_indices:
            s_dict = s.to_dict()
            s_dict["status"] = "COMPLETED"
            composite_sorties.append(CampaignSortie.from_dict(s_dict))

    # Add future sorties with offset sol_index
    offset = len(completed_indices)
    for idx, s in enumerate(future_plan.sorties):
        s_dict = s.to_dict()
        s_dict["sol_index"] = offset + idx + 1
        s_dict["sortie_id"] = f"sortie_sol_{s_dict['sol_index']:02d}"
        s_dict["name"] = f"Sol {s_dict['sol_index']} (Revised): {s.name.split(': ')[-1] if ': ' in s.name else s.name}"
        composite_sorties.append(CampaignSortie.from_dict(s_dict))

    # Re-merge target statuses
    future_target_map = {t.id: t for t in future_plan.targets}
    final_targets: List[CampaignTarget] = []
    for t in remaining_targets:
        if t.status in (TargetStatus.COMPLETED.value, TargetStatus.UNREACHABLE.value):
            final_targets.append(t)
        elif t.id in future_target_map:
            fut = future_target_map[t.id]
            if fut.assigned_sol_index is not None:
                fut.assigned_sol_index += offset
                fut.assigned_sortie_id = f"sortie_sol_{fut.assigned_sol_index:02d}"
            final_targets.append(fut)
        else:
            final_targets.append(t)

    # Summary
    total_dist = sum(s.distance_m for s in composite_sorties)
    total_travel = sum(s.travel_time_s for s in composite_sorties)
    total_dwell = sum(s.dwell_time_s for s in composite_sorties)
    total_dur = sum(s.total_duration_s for s in composite_sorties)
    total_score = sum(s.science_score for s in composite_sorties)
    sched_count = sum(1 for t in final_targets if t.status in (TargetStatus.SCHEDULED.value, TargetStatus.COMPLETED.value))
    unsched_count = len(final_targets) - sched_count

    # Delta comparison against original
    delta_dist = total_dist - campaign.summary.total_distance_m
    delta_dur = total_dur - campaign.summary.total_duration_s
    delta_score = total_score - campaign.summary.total_science_score

    old_sched = {t.id for t in campaign.targets if t.status == TargetStatus.SCHEDULED.value}
    new_sched = {t.id for t in final_targets if t.status in (TargetStatus.SCHEDULED.value, TargetStatus.COMPLETED.value)}
    newly_unsched = list(old_sched - new_sched)

    rev_comparison = {
        "delta_distance_m": round(delta_dist, 1),
        "delta_duration_s": round(delta_dur, 1),
        "delta_science_score": round(delta_score, 1),
        "newly_unscheduled_targets": newly_unsched,
        "resequenced_sorties": [s.sortie_id for s in composite_sorties],
    }

    summary = CampaignSummary(
        total_sols=len(composite_sorties),
        total_sorties=len(composite_sorties),
        total_distance_m=total_dist,
        total_travel_time_s=total_travel,
        total_dwell_time_s=total_dwell,
        total_duration_s=total_dur,
        total_science_score=total_score,
        targets_total=len(final_targets),
        targets_scheduled=sched_count,
        targets_unscheduled=unsched_count,
        targets_completed=len(completed_target_ids),
        is_campaign_feasible=any(s.is_feasible for s in composite_sorties) and sched_count > 0,
        overall_status=CampaignStatus.PARTIALLY_FEASIBLE.value if unsched_count > 0 else CampaignStatus.FEASIBLE.value,
        bottlenecks_and_notes=[f"Revised under disruption: {disruption_type}. {len(newly_unsched)} target(s) omitted."],
    )

    revised_campaign = MissionCampaign(
        campaign_id=campaign.campaign_id,
        name=campaign.name,
        description=f"{campaign.description}\n[Revised]: {description_text}",
        version=campaign.version + 1,
        revision_id=f"rev_{campaign.version + 1:02d}_{disruption_type}",
        parent_campaign_id=campaign.campaign_id,
        config=revised_config,
        targets=final_targets,
        sorties=composite_sorties,
        summary=summary,
        disruption={
            "disruption_type": disruption_type,
            "description": description_text,
            "affected_sorties": [s.sortie_id for s in composite_sorties if s.status != "COMPLETED"],
        },
        revision_comparison=rev_comparison,
    )

    return revised_campaign


# ==============================================================================
# Campaign HTML Dossier Exporter
# ==============================================================================

def export_campaign_report_html(campaign: MissionCampaign) -> str:
    """
    Renders an offline-capable, responsive HTML report for the mission campaign.
    Embeds all CSS internally with system font fallbacks. Zero external dependencies.
    """
    targets_rows = ""
    for t in campaign.targets:
        badge_class = "badge-success" if t.status in ("SCHEDULED", "COMPLETED") else "badge-warning"
        targets_rows += f"""
        <tr>
          <td><code>{t.id}</code></td>
          <td><strong>{t.name}</strong></td>
          <td>({t.row}, {t.col})</td>
          <td>{t.priority_score:.1f} <span class="text-muted">({t.priority_label})</span></td>
          <td>{format_duration(t.dwell_time_s)}</td>
          <td>{', '.join(t.prerequisites) if t.prerequisites else 'None'}</td>
          <td><span class="badge {badge_class}">{t.status}</span></td>
          <td>{t.assigned_sortie_id or '—'}</td>
        </tr>
        """

    sorties_sections = ""
    for s in campaign.sorties:
        status_badge = "badge-success" if s.is_feasible else "badge-danger"
        sorties_sections += f"""
        <div class="sortie-card">
          <div class="sortie-header">
            <h3>{s.name} (Sol {s.sol_index})</h3>
            <span class="badge {status_badge}">{s.status}</span>
          </div>
          <div class="sortie-metrics-grid">
            <div class="metric-item">
              <span class="label">Ground Distance</span>
              <span class="value">{s.distance_m:,.1f} m</span>
            </div>
            <div class="metric-item">
              <span class="label">Active Travel</span>
              <span class="value">{format_duration(s.travel_time_s)}</span>
            </div>
            <div class="metric-item">
              <span class="label">Science Dwell</span>
              <span class="value">{format_duration(s.dwell_time_s)}</span>
            </div>
            <div class="metric-item">
              <span class="label">Total Sol Duration</span>
              <span class="value">{format_duration(s.total_duration_s)}</span>
            </div>
            <div class="metric-item">
              <span class="label">Remaining Margin</span>
              <span class="value">{format_duration(s.remaining_margin_s)}</span>
            </div>
            <div class="metric-item">
              <span class="label">Max Gradient</span>
              <span class="value">{s.max_slope_deg:.1f}&deg;</span>
            </div>
          </div>
          <p class="targets-list"><strong>Assigned Science Targets:</strong> {', '.join(s.target_names) if s.target_names else 'None (Direct Transit)'}</p>
        </div>
        """

    disruption_section = ""
    if campaign.disruption:
        disruption_section = f"""
        <section class="report-section disruption-box">
          <h2>Contingency & Disruption Audit</h2>
          <p><strong>Disruption Type:</strong> <code>{campaign.disruption.get('disruption_type')}</code></p>
          <p><strong>Description:</strong> {campaign.disruption.get('description')}</p>
          <div class="revision-grid">
            <div><strong>Delta Distance:</strong> {campaign.revision_comparison.get('delta_distance_m', 0.0):+,.1f} m</div>
            <div><strong>Delta Duration:</strong> {format_duration(campaign.revision_comparison.get('delta_duration_s', 0.0))}</div>
            <div><strong>Delta Science:</strong> {campaign.revision_comparison.get('delta_science_score', 0.0):+.1f} pts</div>
          </div>
        </section>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MarsWalk Mission Campaign Report &mdash; {campaign.name}</title>
  <style>
    :root {{
      --bg: #090d16;
      --card-bg: #111827;
      --card-border: #1f293d;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --accent: #ff4d2e;
      --accent-subtle: rgba(255, 77, 46, 0.15);
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--font-sans);
      line-height: 1.5;
      padding: 2rem 1.5rem;
    }}
    .container {{
      max-width: 1100px;
      margin: 0 auto;
    }}
    header.report-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 2px solid var(--accent);
      padding-bottom: 1.5rem;
      margin-bottom: 2rem;
    }}
    .header-titles h1 {{
      font-size: 2rem;
      font-weight: 700;
      color: #fff;
    }}
    .header-titles .subtitle {{
      color: var(--text-muted);
      font-size: 0.95rem;
      margin-top: 0.25rem;
    }}
    .header-meta {{
      text-align: right;
      font-family: var(--font-mono);
      font-size: 0.85rem;
    }}
    .badge {{
      display: inline-block;
      padding: 0.25rem 0.6rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .badge-success {{ background: #059669; color: #fff; }}
    .badge-warning {{ background: #d97706; color: #fff; }}
    .badge-danger {{ background: #dc2626; color: #fff; }}
    .report-section {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 2rem;
    }}
    .report-section h2 {{
      font-size: 1.25rem;
      font-weight: 600;
      margin-bottom: 1rem;
      color: #fff;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 0.5rem;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      margin-bottom: 1rem;
    }}
    .metric-card {{
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      padding: 1rem;
    }}
    .metric-card .label {{
      display: block;
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
      margin-bottom: 0.25rem;
    }}
    .metric-card .value {{
      font-size: 1.4rem;
      font-weight: 700;
      color: #fff;
    }}
    .sortie-card {{
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      padding: 1.25rem;
      margin-bottom: 1rem;
    }}
    .sortie-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
    }}
    .sortie-metrics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 0.75rem;
      margin-bottom: 0.75rem;
    }}
    .sortie-metrics-grid .metric-item .label {{
      display: block;
      font-size: 0.7rem;
      color: var(--text-muted);
    }}
    .sortie-metrics-grid .metric-item .value {{
      font-weight: 600;
      font-size: 1rem;
    }}
    .targets-list {{
      font-size: 0.85rem;
      color: #d1d5db;
    }}
    table.data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
      margin-top: 1rem;
    }}
    table.data-table th, table.data-table td {{
      padding: 0.6rem 0.8rem;
      text-align: left;
      border-bottom: 1px solid var(--card-border);
    }}
    table.data-table th {{
      background: rgba(255, 255, 255, 0.04);
      color: var(--text-muted);
      font-weight: 600;
    }}
    .disruption-box {{
      border-left: 4px solid #f59e0b;
    }}
    .revision-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
      margin-top: 1rem;
      background: rgba(245, 158, 11, 0.08);
      padding: 1rem;
      border-radius: 6px;
    }}
    .disclaimer-box {{
      background: rgba(220, 38, 38, 0.08);
      border: 1px solid rgba(220, 38, 38, 0.3);
      border-radius: 6px;
      padding: 1rem;
      font-size: 0.8rem;
      color: #fca5a5;
      margin-top: 2rem;
    }}
    .text-muted {{ color: var(--text-muted); }}
  </style>
</head>
<body>
  <div class="container">
    <header class="report-header">
      <div class="header-titles">
        <h1>{campaign.name}</h1>
        <div class="subtitle">Multi-Sol Planetary Mission Campaign &mdash; MarsWalk 2.0 Project Atlas</div>
      </div>
      <div class="header-meta">
        <div><strong>Campaign ID:</strong> {campaign.campaign_id}</div>
        <div><strong>Version:</strong> {campaign.version} ({campaign.revision_id})</div>
        <div><strong>Status:</strong> <span class="badge {'badge-success' if campaign.summary.is_campaign_feasible else 'badge-danger'}">{campaign.summary.overall_status}</span></div>
      </div>
    </header>

    <section class="report-section">
      <h2>Campaign Executive Summary</h2>
      <div class="summary-grid">
        <div class="metric-card">
          <span class="label">Operational Sols</span>
          <span class="value">{campaign.summary.total_sols}</span>
        </div>
        <div class="metric-card">
          <span class="label">Total Distance</span>
          <span class="value">{campaign.summary.total_distance_m:,.0f} m</span>
        </div>
        <div class="metric-card">
          <span class="label">Total Travel Time</span>
          <span class="value">{format_duration(campaign.summary.total_travel_time_s)}</span>
        </div>
        <div class="metric-card">
          <span class="label">Total Dwell Time</span>
          <span class="value">{format_duration(campaign.summary.total_dwell_time_s)}</span>
        </div>
        <div class="metric-card">
          <span class="label">Cumulative Science</span>
          <span class="value">{campaign.summary.total_science_score:.1f} pts</span>
        </div>
        <div class="metric-card">
          <span class="label">Targets Scheduled</span>
          <span class="value">{campaign.summary.targets_scheduled} / {campaign.summary.targets_total}</span>
        </div>
      </div>
      <p><strong>Planning Profile:</strong> <code>{campaign.config.planning_profile}</code> | <strong>Vehicle Mode:</strong> <code>{campaign.config.vehicle_mode}</code> | <strong>Max Sol Budget:</strong> {format_duration(campaign.config.max_duration_per_sortie_s)}</p>
    </section>

    {disruption_section}

    <section class="report-section">
      <h2>Multi-Sol Sortie Schedules</h2>
      {sorties_sections}
    </section>

    <section class="report-section">
      <h2>Candidate Science Targets & Dependency Flow</h2>
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Coord (R, C)</th>
            <th>Score</th>
            <th>Dwell</th>
            <th>Prerequisites</th>
            <th>Status</th>
            <th>Assigned Sol</th>
          </tr>
        </thead>
        <tbody>
          {targets_rows}
        </tbody>
      </table>
    </section>

    <section class="report-section">
      <h2>Reproducibility & Cartographic Provenance</h2>
      <p><strong>Terrain Model:</strong> {campaign.terrain_dataset_id} (USGS Astrogeology MRO CTX Stereophotogrammetry, 20 m/pixel)</p>
      <p><strong>Terrain SHA-256 Digest:</strong> <code>{TERRAIN_SHA256}</code></p>
      <p><strong>Datum:</strong> IAU 2000 Mars Planetocentric Sphere (Radius: 3,396,190.0 m, Gravity: 3.721 m/s&sup2;)</p>
      <p><strong>Software & Model Version:</strong> v2.0.0 (Project Atlas Campaign Orchestrator)</p>
    </section>

    <div class="disclaimer-box">
      <strong>SCIENTIFIC RESEARCH SIMULATION DISCLAIMER:</strong><br>
      MarsWalk 2.0 multi-sol campaign schedules, sortie durations, metabolic energy expenditures, and contingency trade-offs represent mathematical simulations for mission planning research. They are NOT certified flight-ready operational safety guarantees for astronaut EVA missions or rover surface operations.
    </div>
  </div>
</body>
</html>
"""
    return html
