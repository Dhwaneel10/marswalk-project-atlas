"""
MarsWalk 2.0 — Milestone 12F: Autonomous Mission Rehearsal Director
Closed-Loop Simulation, Disruption Response, Adaptive Recovery & Mission Replay.

Provides a deterministic, reproducible, end-to-end mission rehearsal system that:
1. Runs an operational rehearsal pairing a nominal baseline against a disturbed mission.
2. Injects supported disturbances (corridor closures, operational delays, mobility deratings,
   target unavailabilities, unit dropouts).
3. Simulates unmitigated operational consequences if no recovery is attempted.
4. Executes autonomous closed-loop recovery evaluating three competing strategies:
   - Conservative Detour (avoid hazard / absorb delay, preserve all science)
   - Target Shedding (selectively drop targets to preserve safety margin)
   - Priority Rebalance / Asset Reallocation (reassign tasks across units or reorder objectives)
5. Compares outcomes with rigorous delta metrics and traceable causal decision chains.
6. Guarantees strict immutability of the original campaign.

CRITICAL SCIENTIFIC & OPERATIONAL DISCLOSURES:
- This is a deterministic planning simulation and decision-support instrument.
- It does NOT constitute flight-certified real-time rover telemetry or astronaut flight envelopes.
- Rehearsal scenario outcomes measure robustness only across explicitly modeled disturbances
  and MUST NEVER be presented as physical Martian success or failure probabilities.
- Never call a modeled route operationally safe for astronauts.
"""

from __future__ import annotations

import copy
import datetime
import enum
import hashlib
import json
import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import rasterio

from marswalk.api.contracts import (
    TERRAIN_DATASET_ID,
    TERRAIN_SHA256,
    calculate_safe_pct_delta,
    compute_input_fingerprint,
    sanitize_for_json,
)
from marswalk.core.contingency import compute_circular_footprint
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignSortie,
    CampaignTarget,
    MissionCampaign,
    PlanningProfile,
    TargetStatus,
    plan_mission_campaign,
)
from marswalk.core.planner import (
    OPERATIONAL_LIMITS_S,
    PlannerConfig,
    RouteResult,
    ScienceWaypoint,
    astar_search,
    format_duration,
    plan_sequential_multistop_route,
)
from marswalk.core.terrain import TerrainConfig, TerrainGrid, get_profile_terrain_config

logger = logging.getLogger(__name__)

# Bounded operational constants
MAX_DISTURBANCES_PER_REHEARSAL = 10
MIN_TRIGGER_TIME_S = 0.0
MAX_TRIGGER_TIME_S = 864000.0  # 10 sols max
MIN_RADIUS_M = 10.0
MAX_RADIUS_M = 1000.0
MIN_DELAY_S = 60.0
MAX_DELAY_S = 28800.0
MIN_SPEED_FACTOR = 0.1
MAX_SPEED_FACTOR = 1.0
DEFAULT_MIN_MARGIN_THRESHOLD_S = 1800.0  # 30 minutes safe margin
EVA_MAX_BUDGET_S = 28800.0  # 8 hours EVA operational limit

REHEARSAL_DISCLOSURES = [
    "Simulated operational rehearsal instrument for multi-sol Mars planning. Not certified for real-world rover autonomy or crew flight operations.",
    "Calculations are strictly deterministic based on USGS CTX 20m Jezero topography. Tested scenario recovery rates do NOT represent physical Martian operational success probabilities.",
    "Preserves original baseline campaign immutability; rehearsals create isolated execution records.",
    "Modeled traverses and recovery recommendations are mission-planning heuristics and must never be characterized as certified safe for astronauts.",
]


class DisturbanceType(str, enum.Enum):
    CORRIDOR_CLOSURE = "corridor_closure"
    OPERATIONAL_DELAY = "operational_delay"
    MOBILITY_DERATING = "mobility_derating"
    TARGET_UNAVAILABILITY = "target_unavailability"
    UNIT_DROPOUT = "unit_dropout"


class RecoveryPolicyType(str, enum.Enum):
    BALANCED = "balanced"
    SAFETY_FIRST = "safety_first"
    MAX_SCIENCE = "max_science"


class RehearsalOutcomeStatus(str, enum.Enum):
    NOMINAL = "NOMINAL"
    RECOVERED = "RECOVERED"
    RECOVERED_WITH_DEGRADATION = "RECOVERED_WITH_DEGRADATION"
    NO_FEASIBLE_RECOVERY = "NO_FEASIBLE_RECOVERY"
    DISTURBANCE_REJECTED = "DISTURBANCE_REJECTED"


class CausalLinkStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    DERIVED = "DERIVED"
    MISSING = "MISSING"
    CONFLICTING = "CONFLICTING"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class CausalLink:
    """Explicit causal link connecting an antecedent event to a consequent decision or effect."""
    link_id: str
    source_type: str  # disturbance, telemetry_anomaly, threshold_breach, decision_step
    source_id: str
    target_type: str  # decision_step, recovery_candidate, action
    target_id: str
    relation_type: str  # triggers, invalidates, constrains, selects, supersedes, resolves
    status: CausalLinkStatus = CausalLinkStatus.CONFIRMED
    confidence: float = 1.0
    evidence_rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "link_id": self.link_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "status": self.status.value if isinstance(self.status, CausalLinkStatus) else str(self.status),
            "confidence": round(float(self.confidence), 2),
            "evidence_rationale": self.evidence_rationale,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalLink":
        raw_status = data.get("status", "CONFIRMED")
        try:
            status = CausalLinkStatus(raw_status)
        except ValueError:
            status = CausalLinkStatus.DERIVED
        return cls(
            link_id=str(data.get("link_id", f"clink_{uuid.uuid4().hex[:6]}")),
            source_type=str(data.get("source_type", "decision_step")),
            source_id=str(data.get("source_id", "")),
            target_type=str(data.get("target_type", "decision_step")),
            target_id=str(data.get("target_id", "")),
            relation_type=str(data.get("relation_type", "triggers")),
            status=status,
            confidence=float(data.get("confidence", 1.0)),
            evidence_rationale=str(data.get("evidence_rationale", "")),
        )


@dataclass
class DisturbanceSpecification:
    """Individual scheduled disruption to inject during rehearsal."""
    disturbance_id: str
    disturbance_type: DisturbanceType
    trigger_time_s: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "disturbance_id": self.disturbance_id,
            "disturbance_type": self.disturbance_type.value if isinstance(self.disturbance_type, DisturbanceType) else str(self.disturbance_type),
            "trigger_time_s": round(float(self.trigger_time_s), 1),
            "parameters": self.parameters,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DisturbanceSpecification":
        raw_type = data.get("disturbance_type", "operational_delay")
        try:
            dtype = DisturbanceType(raw_type)
        except ValueError:
            dtype = DisturbanceType.OPERATIONAL_DELAY
        return cls(
            disturbance_id=str(data.get("disturbance_id", f"dst_{uuid.uuid4().hex[:6]}")),
            disturbance_type=dtype,
            trigger_time_s=float(data.get("trigger_time_s", 0.0)),
            parameters=dict(data.get("parameters", {})),
            description=str(data.get("description", "")),
        )


@dataclass
class RecoveryCandidate:
    """Evaluated recovery candidate plan generated during disruption response."""
    strategy: str  # conservative_detour, target_shedding, priority_rebalance
    title: str
    is_feasible: bool
    projected_duration_s: float
    projected_margin_s: float
    projected_science_score: float
    projected_targets_completed: int
    dropped_targets: List[str] = field(default_factory=list)
    reallocated_targets: List[Dict[str, str]] = field(default_factory=list)
    selection_status: str = "REJECTED"  # SELECTED, REJECTED, INFEASIBLE
    decision_rationale: str = ""
    added_detour_distance_m: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "title": self.title,
            "is_feasible": self.is_feasible,
            "projected_duration_s": round(float(self.projected_duration_s), 1),
            "projected_margin_s": round(float(self.projected_margin_s), 1),
            "projected_science_score": round(float(self.projected_science_score), 1),
            "projected_targets_completed": int(self.projected_targets_completed),
            "dropped_targets": self.dropped_targets,
            "reallocated_targets": self.reallocated_targets,
            "selection_status": self.selection_status,
            "decision_rationale": self.decision_rationale,
            "added_detour_distance_m": round(float(self.added_detour_distance_m), 1),
        }


@dataclass
class CausalDecisionStep:
    """Deterministic step in the auditable causal decision ledger."""
    step_index: int
    step_type: str  # INITIAL_STATE, DISTURBANCE_TRIGGER, IMPACT_ANALYSIS, CANDIDATE_EVALUATION, SELECTION_DECISION, REVISED_EXECUTION, FINAL_OUTCOME
    simulated_time_s: float
    title: str
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    step_id: str = ""
    preceding_step_id: Optional[str] = None
    active_unit_ids: List[str] = field(default_factory=list)
    associated_target_ids: List[str] = field(default_factory=list)
    causal_links: List[CausalLink] = field(default_factory=list)
    evidence_status: str = "CONFIRMED"

    def __post_init__(self):
        if not self.step_id:
            self.step_id = f"step_{self.step_index}_{self.step_type.lower()}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_index": self.step_index,
            "step_type": self.step_type,
            "preceding_step_id": self.preceding_step_id,
            "simulated_time_s": round(float(self.simulated_time_s), 1),
            "title": self.title,
            "description": self.description,
            "details": self.details,
            "active_unit_ids": self.active_unit_ids,
            "associated_target_ids": self.associated_target_ids,
            "causal_links": [l.to_dict() if hasattr(l, "to_dict") else l for l in self.causal_links],
            "evidence_status": self.evidence_status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalDecisionStep":
        links_data = data.get("causal_links", [])
        parsed_links = []
        for l in links_data:
            if isinstance(l, dict):
                parsed_links.append(CausalLink.from_dict(l))
            elif isinstance(l, CausalLink):
                parsed_links.append(l)

        step_idx = int(data.get("step_index", 1))
        stype = str(data.get("step_type", "INITIAL_STATE"))
        step_id = str(data.get("step_id", f"step_{step_idx}_{stype.lower()}"))
        preceding = data.get("preceding_step_id")
        if preceding is not None:
            preceding = str(preceding)

        return cls(
            step_id=step_id,
            step_index=step_idx,
            step_type=stype,
            simulated_time_s=float(data.get("simulated_time_s", 0.0)),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            details=dict(data.get("details", {})),
            preceding_step_id=preceding,
            active_unit_ids=list(data.get("active_unit_ids", [])),
            associated_target_ids=list(data.get("associated_target_ids", [])),
            causal_links=parsed_links,
            evidence_status=str(data.get("evidence_status", "CONFIRMED")),
        )


@dataclass
class DivergenceMilestone:
    """Milestone along the comparative execution track."""
    milestone_id: str
    t_offset_s: float
    track: str  # baseline, disturbed, recovered
    description: str
    delta_from_baseline: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "milestone_id": self.milestone_id,
            "t_offset_s": round(float(self.t_offset_s), 1),
            "track": self.track,
            "description": self.description,
            "delta_from_baseline": self.delta_from_baseline,
        }


@dataclass
class DivergenceAnalysis:
    """Comprehensive divergence forensics between nominal and disturbed/recovered tracks."""
    diverged: bool
    t_diverge_s: Optional[float] = None
    divergence_location: Optional[Dict[str, float]] = None
    divergence_trigger_id: Optional[str] = None
    divergence_trigger_name: Optional[str] = None
    divergent_sorties: List[str] = field(default_factory=list)
    divergent_targets: List[str] = field(default_factory=list)
    divergence_milestones: List[DivergenceMilestone] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diverged": self.diverged,
            "t_diverge_s": round(float(self.t_diverge_s), 1) if self.t_diverge_s is not None else None,
            "divergence_location": self.divergence_location,
            "divergence_trigger_id": self.divergence_trigger_id,
            "divergence_trigger_name": self.divergence_trigger_name,
            "divergent_sorties": self.divergent_sorties,
            "divergent_targets": self.divergent_targets,
            "divergence_milestones": [m.to_dict() for m in self.divergence_milestones],
            "summary": self.summary,
        }


@dataclass
class RehearsalTrackMetrics:
    """Metrics recorded for a single simulation track (baseline, disturbed, or recovered)."""
    track_name: str
    total_duration_s: float
    total_distance_m: float
    science_score: float
    targets_completed: int
    targets_attempted: int
    completed_target_ids: List[str] = field(default_factory=list)
    dropped_target_ids: List[str] = field(default_factory=list)
    min_margin_s: float = 0.0
    critical_events_count: int = 0
    violations: List[str] = field(default_factory=list)
    path_rc: List[List[int]] = field(default_factory=list)
    coordinates_3d: List[List[float]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_name": self.track_name,
            "total_duration_s": round(float(self.total_duration_s), 1),
            "total_distance_m": round(float(self.total_distance_m), 1),
            "science_score": round(float(self.science_score), 1),
            "targets_completed": int(self.targets_completed),
            "targets_attempted": int(self.targets_attempted),
            "completed_target_ids": self.completed_target_ids,
            "dropped_target_ids": self.dropped_target_ids,
            "min_margin_s": round(float(self.min_margin_s), 1),
            "critical_events_count": int(self.critical_events_count),
            "violations": self.violations,
            "path_rc": self.path_rc,
            "coordinates_3d": self.coordinates_3d,
        }


@dataclass
class RehearsalComparisonSummary:
    """Side-by-side comparative deltas between baseline, disturbed, and recovered runs."""
    science_preservation_pct: float
    net_science_delta: float
    delay_incurred_s: float
    margin_delta_s: float
    distance_delta_m: float
    targets_retained_count: int
    targets_dropped_count: int
    recovery_efficiency_pct: float
    executive_assessment: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "science_preservation_pct": round(float(self.science_preservation_pct), 1),
            "net_science_delta": round(float(self.net_science_delta), 1),
            "delay_incurred_s": round(float(self.delay_incurred_s), 1),
            "margin_delta_s": round(float(self.margin_delta_s), 1),
            "distance_delta_m": round(float(self.distance_delta_m), 1),
            "targets_retained_count": int(self.targets_retained_count),
            "targets_dropped_count": int(self.targets_dropped_count),
            "recovery_efficiency_pct": round(float(self.recovery_efficiency_pct), 1),
            "executive_assessment": self.executive_assessment,
        }


@dataclass
class RehearsalRecord:
    """Comprehensive, validated record of an autonomous mission rehearsal."""
    rehearsal_id: str
    campaign_id: str
    title: str
    status: str
    outcome_status: str
    created_at: str
    computation_fingerprint: str
    execution_duration_ms: float
    recovery_policy: Dict[str, Any]
    disturbances: List[DisturbanceSpecification]
    baseline_metrics: RehearsalTrackMetrics
    disturbed_metrics: RehearsalTrackMetrics
    recovered_metrics: RehearsalTrackMetrics
    comparison: RehearsalComparisonSummary
    recovery_candidates: List[RecoveryCandidate]
    causal_ledger: List[CausalDecisionStep]
    timeline_events: List[Dict[str, Any]] = field(default_factory=list)
    disclosures: List[str] = field(default_factory=lambda: list(REHEARSAL_DISCLOSURES))
    terrain_dataset_id: str = TERRAIN_DATASET_ID
    terrain_sha256: str = TERRAIN_SHA256
    model_version: str = "2.0.0"
    assumptions_version: str = "1.0.0"
    coordinate_reference: str = "IAU Mars 2000 Planetocentric Sphere / ESRI:103885"
    campaign_version: int = 1
    campaign_input_fingerprint: str = ""
    divergence_analysis: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rehearsal_id": self.rehearsal_id,
            "campaign_id": self.campaign_id,
            "title": self.title,
            "status": self.status,
            "outcome_status": self.outcome_status,
            "created_at": self.created_at,
            "computation_fingerprint": self.computation_fingerprint,
            "execution_duration_ms": round(float(self.execution_duration_ms), 1),
            "recovery_policy": self.recovery_policy,
            "disturbances": [d.to_dict() for d in self.disturbances],
            "baseline_metrics": self.baseline_metrics.to_dict(),
            "disturbed_metrics": self.disturbed_metrics.to_dict(),
            "recovered_metrics": self.recovered_metrics.to_dict(),
            "comparison": self.comparison.to_dict(),
            "recovery_candidates": [c.to_dict() for c in self.recovery_candidates],
            "causal_ledger": [s.to_dict() for s in self.causal_ledger],
            "timeline_events": self.timeline_events,
            "disclosures": self.disclosures,
            "terrain_dataset_id": self.terrain_dataset_id,
            "terrain_sha256": self.terrain_sha256,
            "model_version": self.model_version,
            "assumptions_version": self.assumptions_version,
            "coordinate_reference": self.coordinate_reference,
            "campaign_version": self.campaign_version,
            "campaign_input_fingerprint": self.campaign_input_fingerprint,
            "divergence_analysis": self.divergence_analysis,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RehearsalRecord":
        base_m = dict(data["baseline_metrics"])
        dist_m = dict(data["disturbed_metrics"])
        rec_m = dict(data["recovered_metrics"])

        for m in (base_m, dist_m, rec_m):
            m.setdefault("path_rc", [])
            m.setdefault("coordinates_3d", [])

        parsed_ledger = []
        for s in data.get("causal_ledger", []):
            if isinstance(s, dict):
                parsed_ledger.append(CausalDecisionStep.from_dict(s))
            elif isinstance(s, CausalDecisionStep):
                parsed_ledger.append(s)

        parsed_candidates = []
        for c in data.get("recovery_candidates", []):
            if isinstance(c, dict):
                c_clean = dict(c)
                c_clean.setdefault("added_detour_distance_m", 0.0)
                parsed_candidates.append(RecoveryCandidate(**c_clean))
            elif isinstance(c, RecoveryCandidate):
                parsed_candidates.append(c)

        return cls(
            rehearsal_id=str(data["rehearsal_id"]),
            campaign_id=str(data["campaign_id"]),
            title=str(data.get("title", "Mission Rehearsal")),
            status=str(data.get("status", "COMPLETED")),
            outcome_status=str(data.get("outcome_status", "RECOVERED")),
            created_at=str(data.get("created_at", datetime.datetime.now(datetime.timezone.utc).isoformat())),
            computation_fingerprint=str(data.get("computation_fingerprint", "")),
            execution_duration_ms=float(data.get("execution_duration_ms", 0.0)),
            recovery_policy=dict(data.get("recovery_policy", {})),
            disturbances=[DisturbanceSpecification.from_dict(d) for d in data.get("disturbances", [])],
            baseline_metrics=RehearsalTrackMetrics(**base_m),
            disturbed_metrics=RehearsalTrackMetrics(**dist_m),
            recovered_metrics=RehearsalTrackMetrics(**rec_m),
            comparison=RehearsalComparisonSummary(**data["comparison"]),
            recovery_candidates=parsed_candidates,
            causal_ledger=parsed_ledger,
            timeline_events=list(data.get("timeline_events", [])),
            disclosures=list(data.get("disclosures", REHEARSAL_DISCLOSURES)),
            terrain_dataset_id=str(data.get("terrain_dataset_id", TERRAIN_DATASET_ID)),
            terrain_sha256=str(data.get("terrain_sha256", TERRAIN_SHA256)),
            model_version=str(data.get("model_version", "2.0.0")),
            assumptions_version=str(data.get("assumptions_version", "1.0.0")),
            coordinate_reference=str(data.get("coordinate_reference", "IAU Mars 2000 Planetocentric Sphere / ESRI:103885")),
            campaign_version=int(data.get("campaign_version", 1)),
            campaign_input_fingerprint=str(data.get("campaign_input_fingerprint", "")),
            divergence_analysis=data.get("divergence_analysis"),
        )


def get_supported_disturbances_catalog() -> List[Dict[str, Any]]:
    """Return the authoritative catalog of supported rehearsal disturbance types."""
    return [
        {
            "disturbance_type": DisturbanceType.CORRIDOR_CLOSURE.value,
            "name": "Corridor Closure / Hazard Footprint",
            "description": "Models a localized hazard (rockfall, slope slump, or terrain defect) creating an impassable circular barrier across planned traverse paths.",
            "parameters": {
                "center_rc": {"type": "array", "items": "integer", "minItems": 2, "maxItems": 2, "description": "Grid row and column [row, col] of hazard center"},
                "radius_m": {"type": "number", "minimum": 10.0, "maximum": 1000.0, "default": 50.0, "description": "Radius of impassable corridor in meters"},
            },
        },
        {
            "disturbance_type": DisturbanceType.OPERATIONAL_DELAY.value,
            "name": "Operational Hold / Comms Dropout",
            "description": "Models an unexpected hold or instrument calibration latency that consumes active EVA time without advancing traverse distance.",
            "parameters": {
                "delay_s": {"type": "number", "minimum": 60.0, "maximum": 28800.0, "default": 1800.0, "description": "Duration of operational hold in seconds"},
                "affected_unit_id": {"type": "string", "default": None, "description": "Optional exploration unit ID affected"},
            },
        },
        {
            "disturbance_type": DisturbanceType.MOBILITY_DERATING.value,
            "name": "Mobility Derating / Traction Loss",
            "description": "Models reduced vehicle traversal speed caused by soft drift sand, wheel slippage, or motor thermal derating.",
            "parameters": {
                "speed_factor": {"type": "number", "minimum": 0.1, "maximum": 0.95, "default": 0.7, "description": "Multiplicative speed derating factor (e.g. 0.7 = 30% slower)"},
                "affected_unit_id": {"type": "string", "default": None, "description": "Optional exploration unit ID affected"},
            },
        },
        {
            "disturbance_type": DisturbanceType.TARGET_UNAVAILABILITY.value,
            "name": "Target Unavailability / Scientific Invalidation",
            "description": "Models a scientific waypoint becoming unreachable, scientifically redundant, or obsolete.",
            "parameters": {
                "target_id": {"type": "string", "description": "ID of target to invalidate"},
                "reason": {"type": "string", "default": "Target obstructed by local hazard", "description": "Operational rationale"},
            },
        },
        {
            "disturbance_type": DisturbanceType.UNIT_DROPOUT.value,
            "name": "Exploration Unit Dropout / Hardware Fault",
            "description": "Models an exploration asset (crew EVA or robotic rover) encountering a disabling fault and halting operations.",
            "parameters": {
                "affected_unit_id": {"type": "string", "description": "ID of unit dropped from campaign"},
                "reason": {"type": "string", "default": "Power subsystem fault", "description": "Operational rationale"},
            },
        },
    ]


def _compute_rehearsal_fingerprint(
    campaign_id: str,
    disturbances: List[DisturbanceSpecification],
    recovery_policy: Dict[str, Any],
) -> str:
    """Compute a deterministic SHA-256 fingerprint of all rehearsal inputs."""
    payload = {
        "campaign_id": campaign_id,
        "disturbances": [d.to_dict() for d in sorted(disturbances, key=lambda x: (x.trigger_time_s, x.disturbance_id))],
        "recovery_policy": sorted(recovery_policy.items()),
        "terrain_sha256": TERRAIN_SHA256,
    }
    dumped = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def _extract_campaign_baseline_metrics(
    campaign: MissionCampaign,
    terrain: TerrainGrid,
) -> RehearsalTrackMetrics:
    """Extract nominal performance metrics from the baseline campaign."""
    total_dist = 0.0
    total_dur = 0.0
    science_score = 0.0
    completed_ids = []
    dropped_ids = []
    min_margin = float("inf")
    all_path_rc: List[List[int]] = []
    all_coords_3d: List[List[float]] = []

    for s in campaign.sorties:
        total_dist += s.distance_m
        total_dur += s.total_duration_s
        margin = max(0.0, s.remaining_margin_s)
        if margin < min_margin:
            min_margin = margin
        for t_id in s.target_ids:
            if t_id not in completed_ids:
                completed_ids.append(t_id)

        # Collect path geometry if available
        if hasattr(s, "route") and s.route:
            if hasattr(s.route, "path_rc") and s.route.path_rc:
                all_path_rc.extend([list(rc) for rc in s.route.path_rc])
            if hasattr(s.route, "coordinates_3d") and s.route.coordinates_3d:
                all_coords_3d.extend([list(c) for c in s.route.coordinates_3d])

    if min_margin == float("inf"):
        min_margin = 0.0

    for t in campaign.targets:
        if t.id in completed_ids:
            science_score += float(t.priority_score)
        else:
            dropped_ids.append(t.id)

    return RehearsalTrackMetrics(
        track_name="baseline",
        total_duration_s=round(total_dur, 1),
        total_distance_m=round(total_dist, 1),
        science_score=round(science_score, 1),
        targets_completed=len(completed_ids),
        targets_attempted=len(completed_ids),
        completed_target_ids=completed_ids,
        dropped_target_ids=dropped_ids,
        min_margin_s=round(min_margin, 1),
        critical_events_count=0,
        violations=[],
        path_rc=all_path_rc,
        coordinates_3d=all_coords_3d,
    )


def _simulate_disturbed_unmitigated(
    campaign: MissionCampaign,
    disturbances: List[DisturbanceSpecification],
    terrain: TerrainGrid,
    base_metrics: RehearsalTrackMetrics,
) -> Tuple[RehearsalTrackMetrics, List[str], List[Dict[str, Any]]]:
    """
    Simulates the consequence if disturbances trigger and the mission makes NO recovery attempt.
    Tracks margin exhaustion, blocked corridors, and dropped science.
    """
    violations: List[str] = []
    unmitigated_events: List[Dict[str, Any]] = []
    dropped_targets: Set[str] = set(base_metrics.dropped_target_ids)
    completed_targets: Set[str] = set(base_metrics.completed_target_ids)

    total_delay_s = 0.0
    cumulative_distance_m = base_metrics.total_distance_m
    min_margin_s = base_metrics.min_margin_s

    # Build blocked mask from corridor closures
    blocked_cells: Set[Tuple[int, int]] = set()
    for d in disturbances:
        if d.disturbance_type == DisturbanceType.CORRIDOR_CLOSURE:
            center_rc = d.parameters.get("center_rc")
            radius_m = float(d.parameters.get("radius_m", 50.0))
            if center_rc and len(center_rc) == 2:
                cells = compute_circular_footprint(tuple(center_rc), radius_m, terrain)
                blocked_cells.update(cells)
                unmitigated_events.append({
                    "time_s": d.trigger_time_s,
                    "type": "CORRIDOR_CLOSED",
                    "description": f"Corridor blocked at {center_rc} with {radius_m}m radius",
                })
        elif d.disturbance_type == DisturbanceType.OPERATIONAL_DELAY:
            delay = float(d.parameters.get("delay_s", 1800.0))
            total_delay_s += delay
            unmitigated_events.append({
                "time_s": d.trigger_time_s,
                "type": "OPERATIONAL_HOLD",
                "description": f"Operational delay of {delay:.0f}s encountered",
            })
        elif d.disturbance_type == DisturbanceType.MOBILITY_DERATING:
            factor = float(d.parameters.get("speed_factor", 0.7))
            speed_penalty_s = base_metrics.total_duration_s * (1.0 / max(0.1, factor) - 1.0)
            total_delay_s += speed_penalty_s
            unmitigated_events.append({
                "time_s": d.trigger_time_s,
                "type": "MOBILITY_DERATED",
                "description": f"Mobility reduced by factor {factor:.2f} (added {speed_penalty_s:.0f}s transit time)",
            })
        elif d.disturbance_type == DisturbanceType.TARGET_UNAVAILABILITY:
            tid = d.parameters.get("target_id")
            if tid and tid in completed_targets:
                completed_targets.remove(tid)
                dropped_targets.add(tid)
                unmitigated_events.append({
                    "time_s": d.trigger_time_s,
                    "type": "TARGET_UNAVAILABLE",
                    "description": f"Target {tid} became unavailable; objectives lost without replanning",
                })
        elif d.disturbance_type == DisturbanceType.UNIT_DROPOUT:
            uid = d.parameters.get("affected_unit_id")
            # All targets assigned to that unit are forfeited
            for t in campaign.targets:
                if t.assigned_unit_id == uid and t.id in completed_targets:
                    completed_targets.remove(t.id)
                    dropped_targets.add(t.id)
            violations.append(f"Unit '{uid}' halted permanently without asset reallocation")
            unmitigated_events.append({
                "time_s": d.trigger_time_s,
                "type": "UNIT_DROPOUT",
                "description": f"Unit '{uid}' dropped out; associated science dropped",
            })

    # Check corridor intersections along sortie paths
    if blocked_cells:
        for s in campaign.sorties:
            for pt in s.path_rc:
                if pt in blocked_cells:
                    violations.append(f"Sortie '{s.sortie_id}' traversed directly into blocked corridor footprint")
                    # Unmitigated run halts at obstacle; targets on this sortie lost
                    for tid in s.target_ids:
                        if tid in completed_targets:
                            completed_targets.remove(tid)
                            dropped_targets.add(tid)
                    break

    disturbed_duration_s = base_metrics.total_duration_s + total_delay_s
    min_margin_s = max(-7200.0, min_margin_s - total_delay_s)

    if min_margin_s <= 0.0:
        violations.append(f"Operational margin depleted by {abs(min_margin_s):.0f}s; EVA duration budget breached")

    disturbed_science = sum(
        t.priority_score for t in campaign.targets if t.id in completed_targets
    )

    metrics = RehearsalTrackMetrics(
        track_name="disturbed",
        total_duration_s=round(disturbed_duration_s, 1),
        total_distance_m=round(cumulative_distance_m, 1),
        science_score=round(disturbed_science, 1),
        targets_completed=len(completed_targets),
        targets_attempted=len(base_metrics.completed_target_ids),
        completed_target_ids=sorted(list(completed_targets)),
        dropped_target_ids=sorted(list(dropped_targets)),
        min_margin_s=round(min_margin_s, 1),
        critical_events_count=len(violations) + len(unmitigated_events),
        violations=violations,
        path_rc=list(base_metrics.path_rc),
        coordinates_3d=list(base_metrics.coordinates_3d),
    )
    return metrics, violations, unmitigated_events


def _evaluate_recovery_candidates(
    campaign: MissionCampaign,
    disturbances: List[DisturbanceSpecification],
    recovery_policy: Dict[str, Any],
    terrain: TerrainGrid,
    base_metrics: RehearsalTrackMetrics,
    disturbed_metrics: RehearsalTrackMetrics,
) -> Tuple[List[RecoveryCandidate], Optional[RecoveryCandidate], List[CausalDecisionStep]]:
    """
    Evaluates 3 distinct recovery strategies:
    1. CONSERVATIVE_DETOUR: Reroutes around obstacles, absorbs delays, keeps all targets if feasible.
    2. TARGET_SHEDDING: Selectively sheds lowest priority targets to preserve margin >= threshold.
    3. PRIORITY_REBALANCE: Reassigns targets across units or prioritizes top science before margin cutoff.
    """
    policy_type = recovery_policy.get("policy_type", RecoveryPolicyType.BALANCED.value)
    min_margin_req = float(recovery_policy.get("min_margin_threshold_s", DEFAULT_MIN_MARGIN_THRESHOLD_S))
    ledger_steps: List[CausalDecisionStep] = []
    candidates: List[RecoveryCandidate] = []

    # Active unit IDs and targets across campaign
    all_unit_ids = sorted(list(
        {getattr(t, "assigned_unit_id", None) for t in campaign.targets if getattr(t, "assigned_unit_id", None)}
        | {getattr(s, "unit_id", getattr(s, "assigned_unit_id", None)) for s in campaign.sorties if getattr(s, "unit_id", getattr(s, "assigned_unit_id", None))}
    ))
    all_target_ids = list(base_metrics.completed_target_ids)

    # Step 1: Initial state
    step_1_id = "step_1_initial_state"
    clink_init = CausalLink(
        link_id="clink_init_001",
        source_type="campaign_config",
        source_id=campaign.campaign_id,
        target_type="decision_step",
        target_id=step_1_id,
        relation_type="defines",
        status=CausalLinkStatus.CONFIRMED,
        confidence=1.0,
        evidence_rationale=f"Baseline campaign '{campaign.campaign_id}' schedules nominal sortie sequence and target allocations.",
    )
    ledger_steps.append(
        CausalDecisionStep(
            step_id=step_1_id,
            step_index=1,
            step_type="INITIAL_STATE",
            preceding_step_id=None,
            simulated_time_s=0.0,
            title="Baseline Mission Readiness",
            description=f"Nominal campaign '{campaign.campaign_id}' scheduled with {base_metrics.targets_completed} targets and {base_metrics.science_score:.1f} science priority points.",
            details={"baseline_targets": base_metrics.targets_completed, "baseline_margin_s": base_metrics.min_margin_s},
            active_unit_ids=all_unit_ids,
            associated_target_ids=all_target_ids,
            causal_links=[clink_init],
            evidence_status="CONFIRMED",
        )
    )

    # Gather blocked cells and check route corridor intersection
    blocked_cells: Set[Tuple[int, int]] = set()
    total_delay_s = 0.0
    derating_factor = 1.0
    unavailable_targets: Set[str] = set()
    dropped_units: Set[str] = set()

    for d in disturbances:
        if d.disturbance_type == DisturbanceType.CORRIDOR_CLOSURE:
            center_rc = d.parameters.get("center_rc")
            radius_m = float(d.parameters.get("radius_m", 50.0))
            if center_rc and len(center_rc) == 2:
                cells = compute_circular_footprint(tuple(center_rc), radius_m, terrain)
                blocked_cells.update(cells)
        elif d.disturbance_type == DisturbanceType.OPERATIONAL_DELAY:
            total_delay_s += float(d.parameters.get("delay_s", 1800.0))
        elif d.disturbance_type == DisturbanceType.MOBILITY_DERATING:
            derating_factor *= float(d.parameters.get("speed_factor", 0.7))
        elif d.disturbance_type == DisturbanceType.TARGET_UNAVAILABILITY:
            tid = d.parameters.get("target_id")
            if tid:
                unavailable_targets.add(tid)
        elif d.disturbance_type == DisturbanceType.UNIT_DROPOUT:
            uid = d.parameters.get("affected_unit_id")
            if uid:
                dropped_units.add(uid)

    # Check route intersection
    planned_traverse_cells: Set[Tuple[int, int]] = set()
    for s in campaign.sorties:
        if hasattr(s, "route") and s.route and hasattr(s.route, "path_rc") and s.route.path_rc:
            for rc in s.route.path_rc:
                planned_traverse_cells.add(tuple(rc))

    hazard_intersects_path = bool(blocked_cells & planned_traverse_cells)

    # Step 2: Disturbance Trigger
    first_trigger = min((d.trigger_time_s for d in disturbances), default=0.0)
    dist_desc = "; ".join(f"{d.disturbance_type.value}: {d.description or 'Injected disruption'}" for d in disturbances)
    step_2_id = "step_2_disturbance_trigger"
    dist_links = []
    for d in disturbances:
        if d.disturbance_type == DisturbanceType.CORRIDOR_CLOSURE:
            c_status = CausalLinkStatus.CONFIRMED if hazard_intersects_path else CausalLinkStatus.UNRESOLVED
            c_rat = "Closure footprint directly intersects planned route path." if hazard_intersects_path else "Closure footprint is located off-path; nominal traverse avoids obstruction."
        elif d.disturbance_type == DisturbanceType.OPERATIONAL_DELAY:
            c_status = CausalLinkStatus.CONFIRMED
            c_rat = f"Operational hold directly consumes {d.parameters.get('delay_s', 1800):.0f}s of mission time."
        else:
            c_status = CausalLinkStatus.CONFIRMED
            c_rat = f"Injected disturbance '{d.disturbance_type.value}' perturbs mission execution."
        dist_links.append(
            CausalLink(
                link_id=f"clink_{d.disturbance_id}",
                source_type="disturbance",
                source_id=d.disturbance_id,
                target_type="decision_step",
                target_id=step_2_id,
                relation_type="triggers",
                status=c_status,
                confidence=1.0,
                evidence_rationale=c_rat,
            )
        )
    ledger_steps.append(
        CausalDecisionStep(
            step_id=step_2_id,
            step_index=2,
            step_type="DISTURBANCE_TRIGGER",
            preceding_step_id=step_1_id,
            simulated_time_s=first_trigger,
            title=f"Disturbance Injected at T+{first_trigger:.0f}s",
            description=dist_desc,
            details={"disturbances_count": len(disturbances), "first_trigger_s": first_trigger, "hazard_intersects_path": hazard_intersects_path},
            active_unit_ids=all_unit_ids,
            associated_target_ids=list(unavailable_targets),
            causal_links=dist_links,
            evidence_status="CONFIRMED" if disturbances else "DERIVED",
        )
    )

    # Step 3: Impact Analysis
    step_3_id = "step_3_impact_analysis"
    clink_impact = CausalLink(
        link_id="clink_impact_analysis",
        source_type="decision_step",
        source_id=step_2_id,
        target_type="decision_step",
        target_id=step_3_id,
        relation_type="constrains",
        status=CausalLinkStatus.CONFIRMED,
        confidence=1.0,
        evidence_rationale=f"Disturbances reduce margin to {disturbed_metrics.min_margin_s:.0f}s with {len(disturbed_metrics.violations)} operational violations.",
    )
    ledger_steps.append(
        CausalDecisionStep(
            step_id=step_3_id,
            step_index=3,
            step_type="IMPACT_ANALYSIS",
            preceding_step_id=step_2_id,
            simulated_time_s=first_trigger,
            title="Unmitigated Disruption Impact Assessment",
            description=f"Without recovery, mission margin falls to {disturbed_metrics.min_margin_s:.0f}s with {len(disturbed_metrics.violations)} operational violations and {len(disturbed_metrics.dropped_target_ids)} lost targets.",
            details={
                "disturbed_margin_s": disturbed_metrics.min_margin_s,
                "dropped_targets": disturbed_metrics.dropped_target_ids,
                "violations": disturbed_metrics.violations,
            },
            active_unit_ids=all_unit_ids,
            associated_target_ids=disturbed_metrics.dropped_target_ids,
            causal_links=[clink_impact],
            evidence_status="CONFIRMED",
        )
    )

    # Candidate 1: Conservative Detour
    detour_feasible = True
    detour_dropped: List[str] = list(unavailable_targets)
    detour_added_duration_s = total_delay_s
    detour_added_distance_m = 0.0

    # Only penalize distance/time if obstacle actually intersects planned traverse!
    if blocked_cells and hazard_intersects_path:
        detour_added_duration_s += 900.0
        detour_added_distance_m += 400.0

    if derating_factor < 1.0:
        detour_added_duration_s += base_metrics.total_duration_s * (1.0 / max(0.1, derating_factor) - 1.0)

    detour_duration_s = base_metrics.total_duration_s + detour_added_duration_s
    detour_margin_s = base_metrics.min_margin_s - detour_added_duration_s

    if dropped_units:
        detour_feasible = False
        detour_rationale = f"Infeasible: Exploration unit(s) {list(dropped_units)} unavailable and cannot complete assigned sorties."
    elif detour_margin_s < 0.0:
        detour_feasible = False
        detour_rationale = f"Infeasible: Operational margin depleted ({detour_margin_s:.0f}s < 0s); exceeds EVA duration safety ceiling."
    else:
        detour_rationale = f"Feasible: Detour preserves {base_metrics.science_score - sum(t.priority_score for t in campaign.targets if t.id in detour_dropped):.1f} science with {detour_margin_s:.0f}s margin remaining."

    detour_science = sum(
        t.priority_score for t in campaign.targets
        if t.id in base_metrics.completed_target_ids and t.id not in detour_dropped
    )

    cand_detour = RecoveryCandidate(
        strategy="conservative_detour",
        title="Conservative Detour (Preserve All Feasible Targets)",
        is_feasible=detour_feasible,
        projected_duration_s=round(detour_duration_s, 1),
        projected_margin_s=round(detour_margin_s, 1),
        projected_science_score=round(detour_science, 1),
        projected_targets_completed=len(base_metrics.completed_target_ids) - len(detour_dropped),
        dropped_targets=sorted(detour_dropped),
        decision_rationale=detour_rationale,
        added_detour_distance_m=round(detour_added_distance_m, 1),
    )
    candidates.append(cand_detour)

    # Candidate 2: Target Shedding
    shedding_dropped: Set[str] = set(unavailable_targets)
    if dropped_units:
        for t in campaign.targets:
            if t.assigned_unit_id in dropped_units:
                shedding_dropped.add(t.id)

    remaining_targets = [
        t for t in campaign.targets
        if t.id in base_metrics.completed_target_ids and t.id not in shedding_dropped
    ]
    remaining_targets.sort(key=lambda t: t.priority_score)

    cur_duration_s = detour_duration_s
    cur_margin_s = detour_margin_s

    for t in remaining_targets:
        if cur_margin_s >= min_margin_req and cur_duration_s <= EVA_MAX_BUDGET_S:
            break
        time_saved_s = float(t.dwell_time_s) + 600.0
        cur_duration_s = max(1800.0, cur_duration_s - time_saved_s)
        cur_margin_s += time_saved_s
        shedding_dropped.add(t.id)

    shed_feasible = cur_margin_s >= 0.0
    shed_science = sum(
        t.priority_score for t in campaign.targets
        if t.id in base_metrics.completed_target_ids and t.id not in shedding_dropped
    )
    if len(shedding_dropped) == 0:
        shed_rationale = f"Feasible without target shedding: nominal margin ({cur_margin_s:.0f}s) satisfies threshold (>= {min_margin_req:.0f}s)."
    else:
        shed_rationale = (
            f"Feasible: Selectively shed {len(shedding_dropped)} low-priority targets, restoring safety margin to {cur_margin_s:.0f}s (>= {min_margin_req:.0f}s threshold)."
            if shed_feasible
            else "Infeasible: Unable to restore positive margin even after shedding targets."
        )

    cand_shedding = RecoveryCandidate(
        strategy="target_shedding",
        title="Target Shedding (Safety Margin Safeguard)",
        is_feasible=shed_feasible,
        projected_duration_s=round(cur_duration_s, 1),
        projected_margin_s=round(cur_margin_s, 1),
        projected_science_score=round(shed_science, 1),
        projected_targets_completed=len(base_metrics.completed_target_ids) - len(shedding_dropped),
        dropped_targets=sorted(list(shedding_dropped)),
        decision_rationale=shed_rationale,
        added_detour_distance_m=0.0,
    )
    candidates.append(cand_shedding)

    # Candidate 3: Priority Rebalance / Asset Reallocation
    reallocated_targets: List[Dict[str, str]] = []
    rebal_dropped: Set[str] = set(unavailable_targets)
    rebal_feasible = True

    all_units = {t.assigned_unit_id for t in campaign.targets if t.assigned_unit_id}
    surviving_units = list(all_units - dropped_units)

    if dropped_units and surviving_units:
        target_survivor = surviving_units[0]
        for t in campaign.targets:
            if t.assigned_unit_id in dropped_units and t.id not in rebal_dropped:
                reallocated_targets.append({
                    "target_id": t.id,
                    "previous_unit": str(t.assigned_unit_id),
                    "new_unit": target_survivor,
                })
        rebal_duration_s = cur_duration_s + len(reallocated_targets) * 600.0
        rebal_margin_s = max(600.0, cur_margin_s - len(reallocated_targets) * 300.0)
        rebal_science = sum(
            t.priority_score for t in campaign.targets
            if t.id in base_metrics.completed_target_ids and t.id not in rebal_dropped
        )
        rebal_feasible = (rebal_margin_s >= 0.0) and (rebal_duration_s <= EVA_MAX_BUDGET_S)
        rebal_rationale = (
            f"Feasible: Successfully reallocated {len(reallocated_targets)} targets from dropped unit(s) to surviving unit '{target_survivor}' with {rebal_margin_s:.0f}s margin."
            if rebal_feasible
            else f"Infeasible: Reallocation exceeds EVA duration budget ({rebal_duration_s:.0f}s > {EVA_MAX_BUDGET_S:.0f}s)."
        )
    elif not dropped_units and len(remaining_targets) >= 2:
        rebal_duration_s = min(cur_duration_s, detour_duration_s)
        rebal_margin_s = max(cur_margin_s, detour_margin_s)
        rebal_science = max(cand_detour.projected_science_score, cand_shedding.projected_science_score)
        rebal_feasible = (rebal_margin_s >= 0.0) and (rebal_duration_s <= EVA_MAX_BUDGET_S)
        rebal_rationale = (
            "Feasible: Rebalanced visit sequence prioritizing critical geological targets ahead of thermal margins."
            if rebal_feasible
            else f"Infeasible: Duration/margin constraints breached ({rebal_margin_s:.0f}s margin)."
        )
    else:
        rebal_feasible = False
        rebal_duration_s = cur_duration_s
        rebal_margin_s = cur_margin_s
        rebal_science = shed_science
        rebal_rationale = "Infeasible: No alternate surviving exploration units available for cross-asset handoff."

    cand_rebalance = RecoveryCandidate(
        strategy="priority_rebalance",
        title="Priority Rebalance & Workload Reallocation",
        is_feasible=rebal_feasible,
        projected_duration_s=round(rebal_duration_s, 1),
        projected_margin_s=round(rebal_margin_s, 1),
        projected_science_score=round(rebal_science, 1),
        projected_targets_completed=len(base_metrics.completed_target_ids) - len(rebal_dropped),
        dropped_targets=sorted(list(rebal_dropped)),
        reallocated_targets=reallocated_targets,
        decision_rationale=rebal_rationale,
        added_detour_distance_m=0.0,
    )
    candidates.append(cand_rebalance)

    # Step 4: Ledger evaluation entry
    step_4_id = "step_4_candidate_evaluation"
    cand_summary = "; ".join(f"{c.strategy}: feasible={c.is_feasible}, sci={c.projected_science_score:.1f}, margin={c.projected_margin_s:.0f}s" for c in candidates)
    cand_links = [
        CausalLink(
            link_id=f"clink_cand_{c.strategy}",
            source_type="decision_step",
            source_id=step_3_id,
            target_type="recovery_candidate",
            target_id=c.strategy,
            relation_type="generates",
            status=CausalLinkStatus.DERIVED,
            confidence=0.95,
            evidence_rationale=f"Evaluated candidate {c.strategy}: feasible={c.is_feasible}, projected margin={c.projected_margin_s:.0f}s.",
        )
        for c in candidates
    ]
    ledger_steps.append(
        CausalDecisionStep(
            step_id=step_4_id,
            step_index=4,
            step_type="CANDIDATE_EVALUATION",
            preceding_step_id=step_3_id,
            simulated_time_s=first_trigger,
            title="Recovery Strategy Option Space Evaluation",
            description=f"Generated and scored 3 candidate recovery options under policy '{policy_type}': {cand_summary}.",
            details={"candidates": [c.to_dict() for c in candidates]},
            active_unit_ids=all_unit_ids,
            associated_target_ids=all_target_ids,
            causal_links=cand_links,
            evidence_status="CONFIRMED",
        )
    )

    # Policy Selection Decision
    selected: Optional[RecoveryCandidate] = None

    if policy_type == RecoveryPolicyType.SAFETY_FIRST.value:
        for c in sorted(candidates, key=lambda x: (x.is_feasible, x.projected_margin_s), reverse=True):
            if c.is_feasible and c.projected_margin_s >= 3600.0:
                selected = c
                break
        if not selected:
            for c in sorted(candidates, key=lambda x: (x.is_feasible, x.projected_margin_s), reverse=True):
                if c.is_feasible:
                    selected = c
                    break

    elif policy_type == RecoveryPolicyType.MAX_SCIENCE.value:
        for c in sorted(candidates, key=lambda x: (x.is_feasible, x.projected_science_score, x.projected_margin_s), reverse=True):
            if c.is_feasible and c.projected_margin_s >= 0.0:
                selected = c
                break

    else:  # BALANCED
        if cand_detour.is_feasible and cand_detour.projected_margin_s >= min_margin_req:
            selected = cand_detour
        elif cand_rebalance.is_feasible and cand_rebalance.projected_margin_s >= min_margin_req:
            selected = cand_rebalance
        elif cand_shedding.is_feasible:
            selected = cand_shedding
        elif cand_detour.is_feasible:
            selected = cand_detour

    if not selected:
        for c in candidates:
            if c.is_feasible:
                selected = c
                break

    step_5_id = "step_5_selection_decision"
    if selected:
        for c in candidates:
            if c.strategy == selected.strategy:
                c.selection_status = "SELECTED"
            elif not c.is_feasible:
                c.selection_status = "INFEASIBLE"
            else:
                c.selection_status = "REJECTED"

        clink_sel = CausalLink(
            link_id="clink_policy_select",
            source_type="recovery_policy",
            source_id=policy_type,
            target_type="recovery_candidate",
            target_id=selected.strategy,
            relation_type="selects",
            status=CausalLinkStatus.CONFIRMED,
            confidence=1.0,
            evidence_rationale=f"Policy '{policy_type}' selects candidate '{selected.strategy}'. Decision rationale: {selected.decision_rationale}",
        )
        ledger_steps.append(
            CausalDecisionStep(
                step_id=step_5_id,
                step_index=5,
                step_type="SELECTION_DECISION",
                preceding_step_id=step_4_id,
                simulated_time_s=first_trigger,
                title=f"Autonomous Recovery Selected: {selected.title}",
                description=f"Selected '{selected.strategy}' under policy '{policy_type}'. Decision rationale: {selected.decision_rationale}",
                details={"selected_strategy": selected.strategy, "policy": policy_type},
                active_unit_ids=all_unit_ids,
                associated_target_ids=selected.dropped_targets,
                causal_links=[clink_sel],
                evidence_status="CONFIRMED",
            )
        )
    else:
        for c in candidates:
            c.selection_status = "INFEASIBLE"
        clink_infeasible = CausalLink(
            link_id="clink_policy_abort",
            source_type="recovery_policy",
            source_id=policy_type,
            target_type="decision_step",
            target_id=step_5_id,
            relation_type="constrains",
            status=CausalLinkStatus.CONFIRMED,
            confidence=1.0,
            evidence_rationale=f"All candidate strategies failed operational or safety limits under policy '{policy_type}'.",
        )
        ledger_steps.append(
            CausalDecisionStep(
                step_id=step_5_id,
                step_index=5,
                step_type="SELECTION_DECISION",
                preceding_step_id=step_4_id,
                simulated_time_s=first_trigger,
                title="No Feasible Recovery Strategy Available",
                description=f"All candidate strategies failed operational or safety limits under policy '{policy_type}'. Disruption unresolvable within constraints.",
                details={"policy": policy_type},
                active_unit_ids=all_unit_ids,
                associated_target_ids=all_target_ids,
                causal_links=[clink_infeasible],
                evidence_status="CONFIRMED",
            )
        )

    return candidates, selected, ledger_steps


def execute_mission_rehearsal(
    campaign: MissionCampaign,
    disturbances: List[Dict[str, Any]],
    recovery_policy: Optional[Dict[str, Any]] = None,
    terrain: Optional[TerrainGrid] = None,
    title: str = "Mission Rehearsal",
) -> RehearsalRecord:
    """
    Main entry point: executes a paired deterministic mission rehearsal.
    Simulates baseline nominal run, disturbed unmitigated run, and closed-loop recovered run.
    Guarantees campaign immutability.
    """
    start_time_bench = time.perf_counter()

    if not isinstance(campaign, MissionCampaign):
        raise ValueError(f"Expected MissionCampaign instance, got {type(campaign)}")

    if terrain is None:
        raise ValueError("TerrainGrid instance is required for rehearsal simulation.")

    # Validate disturbances
    specs: List[DisturbanceSpecification] = []
    for idx, d in enumerate(disturbances):
        if isinstance(d, DisturbanceSpecification):
            spec = copy.deepcopy(d)
        elif isinstance(d, dict):
            spec = DisturbanceSpecification.from_dict(d)
        else:
            continue
        if not spec.disturbance_id:
            spec.disturbance_id = f"dst_{idx+1:03d}"
        specs.append(spec)

    rec_policy = dict(recovery_policy or {})
    if "policy_type" not in rec_policy:
        rec_policy["policy_type"] = RecoveryPolicyType.BALANCED.value
    if "min_margin_threshold_s" not in rec_policy:
        rec_policy["min_margin_threshold_s"] = DEFAULT_MIN_MARGIN_THRESHOLD_S

    rehearsal_id = f"reh_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    fingerprint = _compute_rehearsal_fingerprint(campaign.campaign_id, specs, rec_policy)

    # Track 1: Baseline Nominal Run
    base_metrics = _extract_campaign_baseline_metrics(campaign, terrain)

    # Track 2: Disturbed Unmitigated Run
    dist_metrics, dist_violations, dist_events = _simulate_disturbed_unmitigated(
        campaign, specs, terrain, base_metrics
    )

    # Track 3: Closed-Loop Recovery
    candidates, selected, ledger_steps = _evaluate_recovery_candidates(
        campaign, specs, rec_policy, terrain, base_metrics, dist_metrics
    )

    # Determine Recovered Metrics & Outcome Status
    all_unit_ids = sorted(list(
        {getattr(t, "assigned_unit_id", None) for t in campaign.targets if getattr(t, "assigned_unit_id", None)}
        | {getattr(s, "unit_id", getattr(s, "assigned_unit_id", None)) for s in campaign.sorties if getattr(s, "unit_id", getattr(s, "assigned_unit_id", None))}
    ))
    step_6_id = "step_6_revised_execution"
    step_7_id = "step_7_final_outcome"

    if not specs:
        # Nominal case: no disturbances injected
        outcome_status = RehearsalOutcomeStatus.NOMINAL.value
        rec_metrics = RehearsalTrackMetrics(
            track_name="recovered",
            total_duration_s=base_metrics.total_duration_s,
            total_distance_m=base_metrics.total_distance_m,
            science_score=base_metrics.science_score,
            targets_completed=base_metrics.targets_completed,
            targets_attempted=base_metrics.targets_attempted,
            completed_target_ids=list(base_metrics.completed_target_ids),
            dropped_target_ids=list(base_metrics.dropped_target_ids),
            min_margin_s=base_metrics.min_margin_s,
            critical_events_count=0,
            violations=[],
            path_rc=list(base_metrics.path_rc),
            coordinates_3d=list(base_metrics.coordinates_3d),
        )
        clink_exec = CausalLink(
            link_id="clink_exec_nominal",
            source_type="decision_step",
            source_id="step_5_selection_decision",
            target_type="action",
            target_id="nominal_execution",
            relation_type="supersedes",
            status=CausalLinkStatus.CONFIRMED,
            confidence=1.0,
            evidence_rationale="Nominal flight trajectory executed without disturbances or interventions.",
        )
        ledger_steps.append(
            CausalDecisionStep(
                step_id=step_6_id,
                step_index=6,
                step_type="REVISED_EXECUTION",
                preceding_step_id="step_5_selection_decision",
                simulated_time_s=base_metrics.total_duration_s,
                title="Nominal Trajectory Maintained",
                description="Zero disruptions were scheduled. Mission concluded along nominal flight trajectory.",
                details={"completed_targets": base_metrics.completed_target_ids, "duration_s": base_metrics.total_duration_s},
                active_unit_ids=all_unit_ids,
                associated_target_ids=base_metrics.completed_target_ids,
                causal_links=[clink_exec],
                evidence_status="CONFIRMED",
            )
        )
        clink_outcome = CausalLink(
            link_id="clink_outcome_nominal",
            source_type="action",
            source_id="nominal_execution",
            target_type="decision_step",
            target_id=step_7_id,
            relation_type="resolves",
            status=CausalLinkStatus.CONFIRMED,
            confidence=1.0,
            evidence_rationale="All planned scientific targets achieved under nominal trajectory.",
        )
        ledger_steps.append(
            CausalDecisionStep(
                step_id=step_7_id,
                step_index=7,
                step_type="FINAL_OUTCOME",
                preceding_step_id=step_6_id,
                simulated_time_s=base_metrics.total_duration_s,
                title="Nominal Mission Objective Completion",
                description=f"Completed all {base_metrics.targets_completed} targets with 100% science preservation.",
                details={"preservation_pct": 100.0, "outcome_status": outcome_status},
                active_unit_ids=all_unit_ids,
                associated_target_ids=base_metrics.completed_target_ids,
                causal_links=[clink_outcome],
                evidence_status="CONFIRMED",
            )
        )

    elif selected is None:
        # No feasible recovery
        outcome_status = RehearsalOutcomeStatus.NO_FEASIBLE_RECOVERY.value
        rec_metrics = RehearsalTrackMetrics(
            track_name="recovered",
            total_duration_s=dist_metrics.total_duration_s,
            total_distance_m=dist_metrics.total_distance_m,
            science_score=0.0,
            targets_completed=0,
            targets_attempted=base_metrics.targets_attempted,
            completed_target_ids=[],
            dropped_target_ids=list(base_metrics.completed_target_ids),
            min_margin_s=dist_metrics.min_margin_s,
            critical_events_count=len(dist_violations) + 1,
            violations=dist_violations + ["Abort to safe haven required: no recovery plan met flight constraints"],
            path_rc=list(base_metrics.path_rc[:5]) if base_metrics.path_rc else [],
            coordinates_3d=list(base_metrics.coordinates_3d[:5]) if base_metrics.coordinates_3d else [],
        )
        clink_exec = CausalLink(
            link_id="clink_exec_abort",
            source_type="decision_step",
            source_id="step_5_selection_decision",
            target_type="action",
            target_id="abort_to_base",
            relation_type="supersedes",
            status=CausalLinkStatus.CONFIRMED,
            confidence=1.0,
            evidence_rationale="Immediate mission abort dispatched to secure flight crew/asset safety margin.",
        )
        ledger_steps.append(
            CausalDecisionStep(
                step_id=step_6_id,
                step_index=6,
                step_type="REVISED_EXECUTION",
                preceding_step_id="step_5_selection_decision",
                simulated_time_s=specs[0].trigger_time_s,
                title="Operational Abort to Base",
                description="Halted campaign operations and commanded abort to safe haven due to infeasible recovery.",
                details={"abort_time_s": specs[0].trigger_time_s, "cause": specs[0].description or specs[0].disturbance_type.value},
                active_unit_ids=all_unit_ids,
                associated_target_ids=list(base_metrics.completed_target_ids),
                causal_links=[clink_exec],
                evidence_status="CONFIRMED",
            )
        )
        clink_outcome = CausalLink(
            link_id="clink_outcome_abort",
            source_type="action",
            source_id="abort_to_base",
            target_type="decision_step",
            target_id=step_7_id,
            relation_type="resolves",
            status=CausalLinkStatus.CONFIRMED,
            confidence=1.0,
            evidence_rationale="Mission terminated with zero science salvaged due to depleted operational safety margin.",
        )
        ledger_steps.append(
            CausalDecisionStep(
                step_id=step_7_id,
                step_index=7,
                step_type="FINAL_OUTCOME",
                preceding_step_id=step_6_id,
                simulated_time_s=specs[0].trigger_time_s,
                title="Campaign Aborted (Infeasible Recovery)",
                description="Zero scientific objectives could be salvaged within operational safety margins.",
                details={"preservation_pct": 0.0, "outcome_status": outcome_status},
                active_unit_ids=all_unit_ids,
                associated_target_ids=list(base_metrics.completed_target_ids),
                causal_links=[clink_outcome],
                evidence_status="CONFIRMED",
            )
        )

    else:
        # Recovered plan executed
        rec_completed = [
            t_id for t_id in base_metrics.completed_target_ids
            if t_id not in selected.dropped_targets
        ]
        if selected.projected_science_score >= base_metrics.science_score - 0.1:
            outcome_status = RehearsalOutcomeStatus.RECOVERED.value
        else:
            outcome_status = RehearsalOutcomeStatus.RECOVERED_WITH_DEGRADATION.value

        # Physically grounded distance calculation (avoids phantom distance scaling)
        if getattr(selected, "added_detour_distance_m", 0.0) > 0.0:
            rec_distance_m = base_metrics.total_distance_m + selected.added_detour_distance_m
        elif selected.strategy == "target_shedding" and len(selected.dropped_targets) > 0:
            rec_distance_m = max(0.0, base_metrics.total_distance_m * (len(rec_completed) / max(1, len(base_metrics.completed_target_ids))))
        else:
            rec_distance_m = base_metrics.total_distance_m

        rec_metrics = RehearsalTrackMetrics(
            track_name="recovered",
            total_duration_s=round(selected.projected_duration_s, 1),
            total_distance_m=round(rec_distance_m, 1),
            science_score=round(selected.projected_science_score, 1),
            targets_completed=len(rec_completed),
            targets_attempted=base_metrics.targets_attempted,
            completed_target_ids=sorted(rec_completed),
            dropped_target_ids=sorted(selected.dropped_targets),
            min_margin_s=round(selected.projected_margin_s, 1),
            critical_events_count=len(selected.dropped_targets),
            violations=[],
            path_rc=list(base_metrics.path_rc),
            coordinates_3d=list(base_metrics.coordinates_3d),
        )

        clink_exec = CausalLink(
            link_id="clink_exec_revised",
            source_type="decision_step",
            source_id="step_5_selection_decision",
            target_type="action",
            target_id="revised_execution",
            relation_type="supersedes",
            status=CausalLinkStatus.CONFIRMED,
            confidence=1.0,
            evidence_rationale=f"Executed recovery strategy '{selected.strategy}', reassigning routes to preserve {selected.projected_science_score:.1f} science.",
        )
        ledger_steps.append(
            CausalDecisionStep(
                step_id=step_6_id,
                step_index=6,
                step_type="REVISED_EXECUTION",
                preceding_step_id="step_5_selection_decision",
                simulated_time_s=rec_metrics.total_duration_s,
                title=f"Revised Plan Executed ({selected.title})",
                description=f"Execution resumed from T+{specs[0].trigger_time_s:.0f}s under revised plan, completing {len(rec_completed)} targets.",
                details={"completed_targets": rec_completed, "duration_s": rec_metrics.total_duration_s, "strategy": selected.strategy},
                active_unit_ids=all_unit_ids,
                associated_target_ids=rec_completed,
                causal_links=[clink_exec],
                evidence_status="CONFIRMED",
            )
        )

        preservation_calc = (
            100.0 if base_metrics.science_score <= 0.0 else round((rec_metrics.science_score / base_metrics.science_score) * 100.0, 1)
        )
        clink_outcome = CausalLink(
            link_id="clink_outcome_resolution",
            source_type="action",
            source_id="revised_execution",
            target_type="decision_step",
            target_id=step_7_id,
            relation_type="resolves",
            status=CausalLinkStatus.CONFIRMED,
            confidence=1.0,
            evidence_rationale=f"Closed-loop rehearsal concluded with outcome status {outcome_status} and {preservation_calc}% science retention.",
        )
        ledger_steps.append(
            CausalDecisionStep(
                step_id=step_7_id,
                step_index=7,
                step_type="FINAL_OUTCOME",
                preceding_step_id=step_6_id,
                simulated_time_s=rec_metrics.total_duration_s,
                title=f"Rehearsal Concluded: {outcome_status}",
                description=f"Preserved {rec_metrics.science_score:.1f} / {base_metrics.science_score:.1f} science score ({preservation_calc:.1f}%) with {rec_metrics.min_margin_s:.0f}s remaining margin.",
                details={
                    "outcome_status": outcome_status,
                    "science_preservation_pct": preservation_calc,
                    "min_margin_s": rec_metrics.min_margin_s,
                },
                active_unit_ids=all_unit_ids,
                associated_target_ids=rec_completed,
                causal_links=[clink_outcome],
                evidence_status="CONFIRMED",
            )
        )

    # Compute Comparative Deltas with Zero-Baseline Safety
    if base_metrics.science_score <= 0.0:
        science_preservation_pct = 100.0 if rec_metrics.targets_completed == base_metrics.targets_completed else 0.0
    else:
        science_preservation_pct = round(min(100.0, max(0.0, (rec_metrics.science_score / base_metrics.science_score) * 100.0)), 1)

    net_science_delta = round(rec_metrics.science_score - base_metrics.science_score, 1)
    delay_incurred_s = round(rec_metrics.total_duration_s - base_metrics.total_duration_s, 1)
    margin_delta_s = round(rec_metrics.min_margin_s - base_metrics.min_margin_s, 1)
    distance_delta_m = round(rec_metrics.total_distance_m - base_metrics.total_distance_m, 1)

    # Recovery efficiency: fraction of unmitigated science deficit recovered
    unmitigated_deficit = max(0.0, base_metrics.science_score - dist_metrics.science_score)
    if outcome_status == RehearsalOutcomeStatus.NO_FEASIBLE_RECOVERY.value or rec_metrics.science_score == 0.0:
        recovery_efficiency_pct = 0.0
    elif unmitigated_deficit > 0.0:
        recovered_surplus = max(0.0, rec_metrics.science_score - dist_metrics.science_score)
        recovery_efficiency_pct = round(min(100.0, max(0.0, (recovered_surplus / unmitigated_deficit) * 100.0)), 1)
    else:
        recovery_efficiency_pct = 100.0 if rec_metrics.science_score >= base_metrics.science_score - 0.01 else 0.0

    if outcome_status == RehearsalOutcomeStatus.NOMINAL.value:
        assessment = "Nominal trajectory completed without disturbances or degradation."
    elif outcome_status == RehearsalOutcomeStatus.RECOVERED.value:
        assessment = f"Modeled recovery feasible: 100% of scientific objectives preserved within operational margins via {selected.title if selected else 'adaptive detour'}."
    elif outcome_status == RehearsalOutcomeStatus.RECOVERED_WITH_DEGRADATION.value:
        assessment = f"Modeled recovery feasible with degradation: preserved {science_preservation_pct}% of planned science while safeguarding positive operational margin ({rec_metrics.min_margin_s:.0f}s) by shedding {len(rec_metrics.dropped_target_ids)} targets."
    else:
        assessment = "No feasible recovery strategy was found within EVA safety constraints. Immediate mission abort commanded."

    comparison = RehearsalComparisonSummary(
        science_preservation_pct=science_preservation_pct,
        net_science_delta=net_science_delta,
        delay_incurred_s=delay_incurred_s,
        margin_delta_s=margin_delta_s,
        distance_delta_m=distance_delta_m,
        targets_retained_count=rec_metrics.targets_completed,
        targets_dropped_count=len(rec_metrics.dropped_target_ids),
        recovery_efficiency_pct=recovery_efficiency_pct,
        executive_assessment=assessment,
    )

    divergence = compute_track_divergence(
        baseline_metrics=base_metrics,
        disturbed_metrics=dist_metrics,
        recovered_metrics=rec_metrics,
        disturbances=specs,
        campaign=campaign,
    )

    elapsed_ms = (time.perf_counter() - start_time_bench) * 1000.0

    return RehearsalRecord(
        rehearsal_id=rehearsal_id,
        campaign_id=campaign.campaign_id,
        title=title,
        status="COMPLETED",
        outcome_status=outcome_status,
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        computation_fingerprint=fingerprint,
        execution_duration_ms=round(elapsed_ms, 1),
        recovery_policy=rec_policy,
        disturbances=specs,
        baseline_metrics=base_metrics,
        disturbed_metrics=dist_metrics,
        recovered_metrics=rec_metrics,
        comparison=comparison,
        recovery_candidates=candidates,
        causal_ledger=ledger_steps,
        timeline_events=dist_events,
        disclosures=list(REHEARSAL_DISCLOSURES),
        terrain_dataset_id=TERRAIN_DATASET_ID,
        terrain_sha256=TERRAIN_SHA256,
        model_version="2.0.0",
        assumptions_version="1.0.0",
        coordinate_reference="IAU Mars 2000 Planetocentric Sphere / ESRI:103885",
        campaign_version=getattr(campaign, "version", 1),
        campaign_input_fingerprint=getattr(campaign, "input_fingerprint", ""),
        divergence_analysis=divergence.to_dict(),
    )


def compute_track_divergence(
    baseline_metrics: RehearsalTrackMetrics,
    disturbed_metrics: RehearsalTrackMetrics,
    recovered_metrics: RehearsalTrackMetrics,
    disturbances: List[DisturbanceSpecification],
    campaign: Optional[MissionCampaign] = None,
) -> DivergenceAnalysis:
    """
    Computes deterministic point of divergence, divergent targets, affected sorties,
    and milestone comparative timeline between baseline, disturbed, and recovered tracks.
    """
    if not disturbances:
        m1 = DivergenceMilestone(
            milestone_id="m1_nominal_start",
            t_offset_s=0.0,
            track="baseline",
            description="Mission Departure: All units nominal and synchronized.",
            delta_from_baseline={"duration_s": 0.0, "science": 0.0, "margin_s": 0.0},
        )
        m2 = DivergenceMilestone(
            milestone_id="m2_nominal_finish",
            t_offset_s=baseline_metrics.total_duration_s,
            track="baseline",
            description=f"Nominal Conclusion: Completed {baseline_metrics.targets_completed} targets with zero divergence.",
            delta_from_baseline={"duration_s": 0.0, "science": 0.0, "margin_s": 0.0},
        )
        return DivergenceAnalysis(
            diverged=False,
            t_diverge_s=None,
            divergence_location=None,
            divergence_trigger_id=None,
            divergence_trigger_name=None,
            divergent_sorties=[],
            divergent_targets=[],
            divergence_milestones=[m1, m2],
            summary="Nominal trajectory: zero divergence from baseline campaign plan.",
        )

    earliest = min(disturbances, key=lambda d: d.trigger_time_s)
    t_div = earliest.trigger_time_s

    div_location = None
    if earliest.disturbance_type == DisturbanceType.CORRIDOR_CLOSURE:
        center_rc = earliest.parameters.get("center_rc")
        if center_rc and len(center_rc) == 2:
            div_location = {"row": float(center_rc[0]), "col": float(center_rc[1])}

    divergent_targets = sorted(list(
        (set(baseline_metrics.completed_target_ids) - set(recovered_metrics.completed_target_ids))
        | set(disturbed_metrics.dropped_target_ids)
    ))

    divergent_sorties = []
    if campaign:
        for s in campaign.sorties:
            if any(t_id in divergent_targets for t_id in s.target_ids):
                divergent_sorties.append(s.sortie_id)
            elif earliest.disturbance_type == DisturbanceType.UNIT_DROPOUT:
                s_uid = getattr(s, "unit_id", getattr(s, "assigned_unit_id", None))
                if s_uid == earliest.parameters.get("affected_unit_id"):
                    divergent_sorties.append(s.sortie_id)
    divergent_sorties = sorted(list(set(divergent_sorties)))

    milestones: List[DivergenceMilestone] = []
    milestones.append(
        DivergenceMilestone(
            milestone_id="m1_nominal_start",
            t_offset_s=0.0,
            track="baseline",
            description="Mission Departure: Initial sorties dispatched along planned path.",
            delta_from_baseline={"duration_s": 0.0, "science": 0.0, "margin_s": 0.0},
        )
    )
    milestones.append(
        DivergenceMilestone(
            milestone_id="m2_point_of_divergence",
            t_offset_s=t_div,
            track="disturbed",
            description=f"Point of Divergence at T+{t_div:.0f}s: Triggered by {earliest.disturbance_type.value} ({earliest.description or earliest.disturbance_id}).",
            delta_from_baseline={"trigger_id": earliest.disturbance_id, "type": earliest.disturbance_type.value},
        )
    )
    milestones.append(
        DivergenceMilestone(
            milestone_id="m3_unmitigated_consequence",
            t_offset_s=disturbed_metrics.total_duration_s,
            track="disturbed",
            description=f"Unmitigated Impact: Margin depleted to {disturbed_metrics.min_margin_s:.0f}s with {len(disturbed_metrics.violations)} violations.",
            delta_from_baseline={
                "margin_delta_s": round(disturbed_metrics.min_margin_s - baseline_metrics.min_margin_s, 1),
                "science_delta": round(disturbed_metrics.science_score - baseline_metrics.science_score, 1),
                "duration_delta_s": round(disturbed_metrics.total_duration_s - baseline_metrics.total_duration_s, 1),
            },
        )
    )
    milestones.append(
        DivergenceMilestone(
            milestone_id="m4_adaptive_recovery",
            t_offset_s=recovered_metrics.total_duration_s,
            track="recovered",
            description=f"Adaptive Recovery Track: Secured margin at {recovered_metrics.min_margin_s:.0f}s, preserving {recovered_metrics.science_score:.1f} science.",
            delta_from_baseline={
                "margin_delta_s": round(recovered_metrics.min_margin_s - baseline_metrics.min_margin_s, 1),
                "science_delta": round(recovered_metrics.science_score - baseline_metrics.science_score, 1),
                "duration_delta_s": round(recovered_metrics.total_duration_s - baseline_metrics.total_duration_s, 1),
            },
        )
    )

    summary = (
        f"Point of Divergence identified at T+{t_div:.0f}s triggered by {earliest.disturbance_type.value}. "
        f"Divergence impacted {len(divergent_sorties)} sortie(s) and {len(divergent_targets)} target(s). "
        f"Closed-loop recovery retained {recovered_metrics.targets_completed}/{baseline_metrics.targets_completed} targets "
        f"({recovered_metrics.science_score:.1f}/{baseline_metrics.science_score:.1f} science)."
    )

    return DivergenceAnalysis(
        diverged=True,
        t_diverge_s=t_div,
        divergence_location=div_location,
        divergence_trigger_id=earliest.disturbance_id,
        divergence_trigger_name=earliest.disturbance_type.value,
        divergent_sorties=divergent_sorties,
        divergent_targets=divergent_targets,
        divergence_milestones=milestones,
        summary=summary,
    )


def reconstruct_rehearsal_replay(
    rehearsal_id: str,
    rehearsals_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reconstructs an interactive, auditable replay model from a stored historical
    rehearsal JSON record WITHOUT re-executing simulation.
    Validates causal links and packages divergence analysis.
    """
    from marswalk.api.workspace import get_rehearsal_record

    raw_rec = get_rehearsal_record(rehearsal_id, rehearsals_dir=rehearsals_dir)
    if not raw_rec:
        raise ValueError(f"Historical rehearsal record '{rehearsal_id}' not found.")

    record = RehearsalRecord.from_dict(raw_rec)

    # Validate causal links in ledger
    causal_links_flat: List[Dict[str, Any]] = []
    status_counts = {"CONFIRMED": 0, "DERIVED": 0, "MISSING": 0, "CONFLICTING": 0, "UNRESOLVED": 0}
    for step in record.causal_ledger:
        for link in step.causal_links:
            l_dict = link.to_dict() if hasattr(link, "to_dict") else link
            causal_links_flat.append(l_dict)
            st = str(l_dict.get("status", "CONFIRMED"))
            if st in status_counts:
                status_counts[st] += 1
            else:
                status_counts["UNRESOLVED"] += 1

    # Reconstruct or reuse divergence analysis
    if record.divergence_analysis:
        divergence_dict = record.divergence_analysis
    else:
        div_obj = compute_track_divergence(
            baseline_metrics=record.baseline_metrics,
            disturbed_metrics=record.disturbed_metrics,
            recovered_metrics=record.recovered_metrics,
            disturbances=record.disturbances,
        )
        divergence_dict = div_obj.to_dict()

    return {
        "rehearsal_id": record.rehearsal_id,
        "campaign_id": record.campaign_id,
        "title": record.title,
        "status": record.status,
        "outcome_status": record.outcome_status,
        "created_at": record.created_at,
        "computation_fingerprint": record.computation_fingerprint,
        "terrain_dataset_id": record.terrain_dataset_id,
        "terrain_sha256": record.terrain_sha256,
        "model_version": record.model_version,
        "assumptions_version": record.assumptions_version,
        "coordinate_reference": record.coordinate_reference,
        "baseline_metrics": record.baseline_metrics.to_dict(),
        "disturbed_metrics": record.disturbed_metrics.to_dict(),
        "recovered_metrics": record.recovered_metrics.to_dict(),
        "comparison": record.comparison.to_dict(),
        "causal_decision_ledger": [s.to_dict() for s in record.causal_ledger],
        "causal_ledger": [s.to_dict() for s in record.causal_ledger],
        "causal_links_summary": {
            "total_links": len(causal_links_flat),
            "status_breakdown": status_counts,
            "links": causal_links_flat,
        },
        "recovery_candidates": [c.to_dict() for c in record.recovery_candidates],
        "disturbances": [d.to_dict() for d in record.disturbances],
        "divergence_analysis": divergence_dict,
        "timeline_events": record.timeline_events,
        "disclosures": record.disclosures,
    }


def export_rehearsal_evidence_bundle(
    rehearsal_id: str,
    rehearsals_dir: Optional[str] = None,
    terrain: Optional[TerrainGrid] = None,
    transform: Optional[rasterio.Affine] = None,
) -> Dict[str, Any]:
    """
    Assembles a complete, auditable Forensic Rehearsal Evidence Bundle
    with SHA-256 integrity manifest, full causal ledger, tri-track comparison,
    spatial divergence, and scientific disclosures.
    """
    replay_data = reconstruct_rehearsal_replay(rehearsal_id, rehearsals_dir=rehearsals_dir)

    # Compute bundle integrity manifest
    manifest_sections = {
        "rehearsal_id": rehearsal_id,
        "campaign_id": replay_data["campaign_id"],
        "computation_fingerprint": replay_data["computation_fingerprint"],
        "terrain_sha256": replay_data["terrain_sha256"],
        "steps_count": len(replay_data["causal_decision_ledger"]),
        "diverged": replay_data["divergence_analysis"]["diverged"],
    }
    raw_manifest_bytes = json.dumps(manifest_sections, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest_sha256 = hashlib.sha256(raw_manifest_bytes).hexdigest()

    scientific_provenance = {
        "dataset_id": replay_data["terrain_dataset_id"],
        "terrain_sha256": replay_data["terrain_sha256"],
        "coordinate_reference": replay_data["coordinate_reference"],
        "model_version": replay_data["model_version"],
        "assumptions_version": replay_data["assumptions_version"],
        "dtm_resolution_m": 20.0,
        "units": {
            "distance": "meters (m)",
            "duration": "seconds (s)",
            "margin": "seconds (s)",
            "science_score": "dimensionless priority points",
        },
        "truth_disclosures": list(REHEARSAL_DISCLOSURES),
    }

    bundle = {
        "schema_version": "2.0.0",
        "bundle_id": f"reh_bundle_{rehearsal_id}",
        "rehearsal_id": rehearsal_id,
        "campaign_id": replay_data["campaign_id"],
        "title": replay_data["title"],
        "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "manifest": {
            "manifest_sha256": manifest_sha256,
            "computation_fingerprint": replay_data["computation_fingerprint"],
            "terrain_sha256": replay_data["terrain_sha256"],
            "entry_count": 6,
        },
        "scientific_provenance": scientific_provenance,
        "tri_track_comparison": replay_data["comparison"],
        "divergence_analysis": replay_data["divergence_analysis"],
        "causal_decision_ledger": replay_data["causal_decision_ledger"],
        "causal_links_summary": replay_data["causal_links_summary"],
        "recovery_candidates": replay_data["recovery_candidates"],
        "disturbances": replay_data["disturbances"],
        "disclosures": replay_data["disclosures"],
    }

    return bundle


def export_rehearsal_pack_zip(
    rehearsal_id: str,
    output_path: Optional[str] = None,
    rehearsals_dir: Optional[str] = None,
) -> str:
    """
    Exports a self-contained ZIP archive containing complete rehearsal forensics:
    - manifest.json
    - rehearsal_bundle.json
    - causal_decision_ledger.json
    - tri_track_comparison.csv
    - briefing_report.md
    - README.txt
    Returns the filesystem path of the generated ZIP file.
    """
    import zipfile
    import io
    import csv
    import os

    bundle = export_rehearsal_evidence_bundle(rehearsal_id, rehearsals_dir=rehearsals_dir)

    target_path = output_path or os.path.join(
        rehearsals_dir or "data/workspaces/rehearsals",
        f"{rehearsal_id}_evidence_bundle.zip"
    )
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

    with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        manifest_data = json.dumps(bundle["manifest"], indent=2)
        zf.writestr("manifest.json", manifest_data)
        zf.writestr("rehearsal_bundle.json", json.dumps(bundle, indent=2))
        zf.writestr("causal_decision_ledger.json", json.dumps(bundle["causal_decision_ledger"], indent=2))

        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["Metric", "Baseline", "Disturbed", "Recovered", "Recovered_Delta"])
        comp = bundle["tri_track_comparison"]
        writer.writerow(["Science Preservation (%)", "100.0", "-", "-", comp.get("science_preservation_pct", 0.0)])
        writer.writerow(["Net Science Delta", "0.0", "-", "-", comp.get("net_science_delta", 0.0)])
        writer.writerow(["Delay Incurred (s)", "0.0", "-", "-", comp.get("delay_incurred_s", 0.0)])
        writer.writerow(["Margin Delta (s)", "0.0", "-", "-", comp.get("margin_delta_s", 0.0)])
        writer.writerow(["Distance Delta (m)", "0.0", "-", "-", comp.get("distance_delta_m", 0.0)])
        writer.writerow(["Recovery Efficiency (%)", "100.0", "-", "-", comp.get("recovery_efficiency_pct", 0.0)])
        zf.writestr("tri_track_comparison.csv", csv_buf.getvalue())

        briefing = [
            f"# MARSWALK 2.0 MISSION REHEARSAL FORENSIC BRIEFING",
            f"**Rehearsal ID:** {rehearsal_id}  ",
            f"**Campaign ID:** {bundle['campaign_id']}  ",
            f"**Outcome Status:** {comp.get('executive_assessment', '')}  ",
            f"**Point of Divergence:** T+{bundle['divergence_analysis'].get('t_diverge_s', 'N/A')}s  ",
            f"",
            f"## Tri-Track Metrics",
            f"- Science Preservation: {comp.get('science_preservation_pct')}%",
            f"- Delay Incurred: {comp.get('delay_incurred_s')}s",
            f"- Margin Delta: {comp.get('margin_delta_s')}s",
            f"- Recovery Efficiency: {comp.get('recovery_efficiency_pct')}%",
            f"",
            f"## Causal Decision Summary",
            f"- Total Causal Steps: {len(bundle['causal_decision_ledger'])}",
            f"- Confirmed Causal Links: {bundle['causal_links_summary']['status_breakdown'].get('CONFIRMED', 0)}",
            f"",
            f"## Scientific & Operational Disclosures",
        ]
        for disc in bundle.get("disclosures", []):
            briefing.append(f"> {disc}")
        zf.writestr("briefing_report.md", "\n".join(briefing))

        readme = (
            "MARSWALK 2.0 FORENSIC EVIDENCE BUNDLE\n"
            f"Rehearsal: {rehearsal_id}\n"
            f"Generated: {bundle['created_at_utc']}\n"
            "This package contains deterministic planning artifacts for multi-sol Mars mission analysis.\n"
            "NOT CERTIFIED FOR REAL-WORLD FLIGHT ENVELOPES OR LIVE TELEMETRY.\n"
        )
        zf.writestr("README.txt", readme)

    return target_path
