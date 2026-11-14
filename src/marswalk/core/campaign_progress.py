"""
MarsWalk 2.0 (Project Atlas) — Milestone 11B: Campaign Progress & Science Observation Registry
=============================================================================================
Manages simulated campaign execution progress, target completion lifecycle transitions,
and a validated registry of scientific observations with authentic provenance tracking.

Scientific Disclaimers & Integrity Constraints:
  - All simulated observations are explicitly tagged with provenance='SIMULATED' and is_simulated=True.
  - Authentic imported data (e.g. NASA PDS MEDA/REMS) maintain their original citations.
  - Quantitative values strictly require physical units (SI or planetary standard).
  - Completed targets are permanently protected from being rescheduled in future sols.
  - Historical campaign versions, past sorties, and prior observations remain strictly immutable.
"""

import os
import re
import copy
import uuid
import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, List, Optional, Set, Tuple

import numpy as np

from marswalk.core.terrain import TerrainGrid
from marswalk.core.mission_campaign import (
    CampaignTarget,
    CampaignConfig,
    CampaignSortie,
    CampaignSummary,
    MissionCampaign,
    TargetStatus,
    PlanningProfile,
    validate_target_dependencies,
    plan_mission_campaign,
)
from marswalk.api.contracts import validate_contract


class ObservationType(str, Enum):
    """Recognized scientific observation classifications."""
    GEOLOGICAL_ASSAY = "GEOLOGICAL_ASSAY"
    SPECTRAL_SURVEY = "SPECTRAL_SURVEY"
    ATMOSPHERIC_MEASUREMENT = "ATMOSPHERIC_MEASUREMENT"
    SAMPLE_CORE_EXTRACTION = "SAMPLE_CORE_EXTRACTION"
    HAZARD_INSPECTION = "HAZARD_INSPECTION"
    TERRAIN_IMAGING = "TERRAIN_IMAGING"
    PHOTOMETRIC_ANALYSIS = "PHOTOMETRIC_ANALYSIS"


class ObservationProvenance(str, Enum):
    """Source provenance of scientific observational data."""
    SIMULATED = "SIMULATED"
    IMPORTED_PDS_MEDA = "IMPORTED_PDS_MEDA"
    IMPORTED_PDS_REMS = "IMPORTED_PDS_REMS"
    MEASURED_IN_SITU = "MEASURED_IN_SITU"
    UNKNOWN = "UNKNOWN"


class ProgressEventType(str, Enum):
    """Campaign execution progress and lifecycle transitions."""
    SORTIE_STARTED = "SORTIE_STARTED"
    SORTIE_COMPLETED = "SORTIE_COMPLETED"
    TARGET_VISITED = "TARGET_VISITED"
    TARGET_OBSERVED = "TARGET_OBSERVED"
    TARGET_BLOCKED = "TARGET_BLOCKED"
    ANOMALY_RECORDED = "ANOMALY_RECORDED"
    SCHEDULE_ADAPTED = "SCHEDULE_ADAPTED"


class SortieLifecycleState(str, Enum):
    """Lifecycle states of a campaign sortie."""
    PLANNED = "PLANNED"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DISRUPTED = "DISRUPTED"
    BLOCKED = "BLOCKED"
    DEFERRED = "DEFERRED"
    CANCELLED = "CANCELLED"


# Recognized physical SI and planetary science units
RECOGNIZED_PHYSICAL_UNITS = {
    "Pa", "hPa", "kPa", "bar", "mbar",
    "K", "degC",
    "m/s", "km/h",
    "m", "km", "cm", "mm",
    "s", "min", "h", "sol",
    "deg", "rad",
    "J", "kJ", "W", "kW",
    "kg", "g",
    "dimensionless", "%", "ratio", "ppm", "tau", "count", "DN"
}


@dataclass
class QuantitativeMeasurement:
    """Quantitative measurement datum with mandatory physical unit."""
    parameter: str
    value: float
    unit: str
    uncertainty: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "parameter": str(self.parameter),
            "value": float(self.value),
            "unit": str(self.unit),
        }
        if self.uncertainty is not None:
            d["uncertainty"] = float(self.uncertainty)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuantitativeMeasurement":
        return cls(
            parameter=str(data["parameter"]),
            value=float(data["value"]),
            unit=str(data["unit"]),
            uncertainty=float(data["uncertainty"]) if data.get("uncertainty") is not None else None,
        )


@dataclass
class ScienceObservation:
    """First-class science observation captured during campaign execution."""
    observation_id: str
    campaign_id: str
    target_id: str
    timestamp_utc: str
    observation_type: str
    provenance: str
    is_simulated: bool
    schema_version: str = "1.0.0"
    sortie_id: Optional[str] = None
    mission_id: Optional[str] = None
    target_name: Optional[str] = ""
    sol_index: Optional[int] = None
    instrument_name: Optional[str] = ""
    quantitative_measurements: List[QuantitativeMeasurement] = field(default_factory=list)
    qualitative_notes: Optional[str] = ""
    evidence_references: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "observation_id": self.observation_id,
            "campaign_id": self.campaign_id,
            "sortie_id": self.sortie_id,
            "mission_id": self.mission_id,
            "target_id": self.target_id,
            "target_name": self.target_name or "",
            "sol_index": self.sol_index,
            "timestamp_utc": self.timestamp_utc,
            "observation_type": self.observation_type,
            "provenance": self.provenance,
            "instrument_name": self.instrument_name or "",
            "quantitative_measurements": [m.to_dict() for m in self.quantitative_measurements],
            "qualitative_notes": self.qualitative_notes or "",
            "evidence_references": dict(self.evidence_references),
            "confidence_score": round(float(self.confidence_score), 2),
            "is_simulated": bool(self.is_simulated),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScienceObservation":
        measurements = [
            QuantitativeMeasurement.from_dict(m)
            for m in data.get("quantitative_measurements", [])
            if isinstance(m, dict)
        ]
        return cls(
            schema_version=data.get("schema_version", "1.0.0"),
            observation_id=str(data["observation_id"]),
            campaign_id=str(data["campaign_id"]),
            sortie_id=data.get("sortie_id"),
            mission_id=data.get("mission_id"),
            target_id=str(data["target_id"]),
            target_name=data.get("target_name", ""),
            sol_index=int(data["sol_index"]) if data.get("sol_index") is not None else None,
            timestamp_utc=str(data["timestamp_utc"]),
            observation_type=str(data["observation_type"]),
            provenance=str(data["provenance"]),
            instrument_name=data.get("instrument_name", ""),
            quantitative_measurements=measurements,
            qualitative_notes=data.get("qualitative_notes", ""),
            evidence_references=dict(data.get("evidence_references", {})),
            confidence_score=float(data.get("confidence_score", 1.0)),
            is_simulated=bool(data.get("is_simulated", True)),
        )


@dataclass
class CampaignProgressEvent:
    """Discrete progress event recorded during campaign execution."""
    event_id: str
    campaign_id: str
    sol_index: int
    event_type: str
    timestamp_utc: str
    idempotency_key: str
    schema_version: str = "1.0.0"
    sortie_id: Optional[str] = None
    target_id: Optional[str] = None
    observation_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    black_box_event_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "campaign_id": self.campaign_id,
            "sol_index": self.sol_index,
            "sortie_id": self.sortie_id,
            "event_type": self.event_type,
            "target_id": self.target_id,
            "observation_id": self.observation_id,
            "timestamp_utc": self.timestamp_utc,
            "details": dict(self.details),
            "idempotency_key": self.idempotency_key,
            "black_box_event_id": self.black_box_event_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignProgressEvent":
        return cls(
            schema_version=data.get("schema_version", "1.0.0"),
            event_id=str(data["event_id"]),
            campaign_id=str(data["campaign_id"]),
            sol_index=int(data["sol_index"]),
            sortie_id=data.get("sortie_id"),
            event_type=str(data["event_type"]),
            target_id=data.get("target_id"),
            observation_id=data.get("observation_id"),
            timestamp_utc=str(data["timestamp_utc"]),
            details=dict(data.get("details", {})),
            idempotency_key=str(data["idempotency_key"]),
            black_box_event_id=data.get("black_box_event_id"),
        )


def validate_observation_record(observation_data: Dict[str, Any]) -> None:
    """Validates an observation record against science-observation.schema.json and unit rules."""
    validate_contract(observation_data, "science-observation", raise_on_error=True)

    # Validate units on quantitative measurements
    for m in observation_data.get("quantitative_measurements", []):
        unit = m.get("unit")
        if unit not in RECOGNIZED_PHYSICAL_UNITS:
            raise ValueError(
                f"Unrecognized physical unit '{unit}' for parameter '{m.get('parameter')}'. "
                f"Recognized units: {sorted(list(RECOGNIZED_PHYSICAL_UNITS))}"
            )

    # Check simulated vs provenance consistency
    provenance = observation_data.get("provenance")
    is_simulated = observation_data.get("is_simulated")
    if provenance == ObservationProvenance.SIMULATED.value and not is_simulated:
        raise ValueError("Observations with provenance 'SIMULATED' must have is_simulated=True")
    if provenance in (ObservationProvenance.IMPORTED_PDS_MEDA.value, ObservationProvenance.IMPORTED_PDS_REMS.value, ObservationProvenance.MEASURED_IN_SITU.value) and is_simulated:
        raise ValueError(f"Authentic observation from {provenance} must not be labeled as simulated (is_simulated=False required)")


def validate_progress_event_record(event_data: Dict[str, Any]) -> None:
    """Validates a campaign progress event against campaign-progress-event.schema.json."""
    validate_contract(event_data, "campaign-progress-event", raise_on_error=True)


def calculate_campaign_progress_metrics(
    campaign: MissionCampaign,
    completed_target_ids: Set[str],
    blocked_target_ids: Set[str],
    observation_ids: List[str],
    active_sol_index: int,
) -> Dict[str, Any]:
    """Calculates summary completion metrics and target breakdown for a campaign."""
    total_targets = len(campaign.targets)
    completed_count = len(completed_target_ids)
    blocked_count = len(blocked_target_ids)

    pct = round((completed_count / total_targets * 100.0), 1) if total_targets > 0 else 0.0

    completed_sorties = [
        s.sortie_id for s in campaign.sorties
        if s.status == SortieLifecycleState.COMPLETED.value
    ]

    return {
        "active_sol_index": active_sol_index,
        "completed_sortie_ids": completed_sorties,
        "completed_target_ids": sorted(list(completed_target_ids)),
        "blocked_target_ids": sorted(list(blocked_target_ids)),
        "observation_ids": list(observation_ids),
        "completion_percentage": pct,
    }


def get_next_eligible_targets(
    campaign: MissionCampaign,
    completed_target_ids: Set[str],
    blocked_target_ids: Set[str],
) -> List[Dict[str, Any]]:
    """
    Identifies all candidate targets in the campaign whose prerequisites
    have been satisfied by completed targets, but are not yet completed or blocked.
    """
    eligible = []
    for t in campaign.targets:
        if t.id in completed_target_ids or t.id in blocked_target_ids:
            continue
        # Check if all prerequisites are satisfied in completed_target_ids
        prereqs_met = all(p in completed_target_ids for p in t.prerequisites)
        if prereqs_met:
            eligible.append({
                "id": t.id,
                "name": t.name,
                "row": t.row,
                "col": t.col,
                "priority_score": t.priority_score,
                "dwell_time_s": t.dwell_time_s,
                "prerequisites": list(t.prerequisites),
                "is_eligible": True,
            })
    return eligible


def advance_campaign_progress(
    campaign: MissionCampaign,
    event_type: str,
    target_id: Optional[str],
    terrain: TerrainGrid,
    sol_index: int = 1,
    observation: Optional[ScienceObservation] = None,
    details: Optional[Dict[str, Any]] = None,
    existing_events: Optional[List[CampaignProgressEvent]] = None,
    existing_observations: Optional[List[ScienceObservation]] = None,
) -> Tuple[MissionCampaign, CampaignProgressEvent, Optional[ScienceObservation]]:
    """
    Core Milestone 11B progression controller:
      1. Ingests a validated progress event (e.g. TARGET_VISITED, TARGET_OBSERVED, TARGET_BLOCKED).
      2. Validates against schema and idempotency constraints.
      3. If TARGET_VISITED or TARGET_OBSERVED:
         - Marks target COMPLETED and attaches observation.
         - Enforces NON-RESCHEDULING guarantee: completed target will never appear in remaining sols.
         - Scans prerequisite DAG for newly eligible targets.
         - Recalculates remaining sorties from sol_index onward, keeping prior sols frozen.
      4. If TARGET_BLOCKED:
         - Marks target BLOCKED.
         - Severed downstream targets are evaluated and reclassified.
      5. Increments campaign version, synthesizes revision delta, and returns updated campaign.
    """
    details = details or {}
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Determine unique idempotency key
    idemp_key = details.get("idempotency_key") or f"{campaign.campaign_id}_{event_type}_{target_id}_{sol_index}_{now_iso[:19]}"

    # Check for duplicate event
    if existing_events:
        for ev in existing_events:
            if ev.idempotency_key == idemp_key:
                raise ValueError(f"Duplicate progress event rejected: key '{idemp_key}' already recorded.")

    event_id = f"cpe_{uuid.uuid4().hex[:10]}"
    progress_event = CampaignProgressEvent(
        event_id=event_id,
        campaign_id=campaign.campaign_id,
        sol_index=sol_index,
        event_type=event_type,
        target_id=target_id,
        observation_id=observation.observation_id if observation else None,
        timestamp_utc=now_iso,
        details=details,
        idempotency_key=idemp_key,
    )

    # Validate event schema
    validate_progress_event_record(progress_event.to_dict())

    # Build active state sets
    prev_progress = campaign.progress or {}
    completed_target_ids: Set[str] = set(prev_progress.get("completed_target_ids", []))
    blocked_target_ids: Set[str] = set(prev_progress.get("blocked_target_ids", []))
    all_observation_ids: List[str] = list(prev_progress.get("observation_ids", []))

    if observation:
        all_observation_ids.append(observation.observation_id)

    target_map = {t.id: t for t in campaign.targets}

    # Process Target Completion
    if event_type in (ProgressEventType.TARGET_VISITED.value, ProgressEventType.TARGET_OBSERVED.value):
        if not target_id or target_id not in target_map:
            raise ValueError(f"Progress event '{event_type}' requires a valid target_id in campaign targets")

        if target_id in completed_target_ids:
            # Already completed; prevent duplicate processing
            pass
        else:
            completed_target_ids.add(target_id)
            target_map[target_id].status = TargetStatus.COMPLETED.value

    # Process Target Blockage
    elif event_type == ProgressEventType.TARGET_BLOCKED.value:
        if not target_id or target_id not in target_map:
            raise ValueError(f"Progress event '{event_type}' requires a valid target_id in campaign targets")

        blocked_target_ids.add(target_id)
        target_map[target_id].status = "BLOCKED"
        target_map[target_id].unscheduled_reason = details.get("reason", "TARGET_BLOCKED_BY_SIMULATION")

    # Cascade blocked status to dependent targets whose prerequisites are blocked
    cascade_changed = True
    while cascade_changed:
        cascade_changed = False
        for t in campaign.targets:
            if t.id not in blocked_target_ids and t.id not in completed_target_ids:
                if any(p in blocked_target_ids for p in t.prerequisites):
                    blocked_target_ids.add(t.id)
                    target_map[t.id].status = "BLOCKED"
                    target_map[t.id].unscheduled_reason = f"Prerequisite is blocked: {t.prerequisites}"
                    cascade_changed = True

    # Update sortie statuses for completed sols
    updated_sorties: List[CampaignSortie] = []
    for s in campaign.sorties:
        s_copy = copy.deepcopy(s)
        if s_copy.sol_index < sol_index:
            s_copy.status = SortieLifecycleState.COMPLETED.value
        elif s_copy.sol_index == sol_index:
            if event_type == ProgressEventType.SORTIE_COMPLETED.value:
                s_copy.status = SortieLifecycleState.COMPLETED.value
            else:
                s_copy.status = SortieLifecycleState.IN_PROGRESS.value
        else:
            s_copy.status = SortieLifecycleState.READY.value
        updated_sorties.append(s_copy)

    # Replan downstream sols if needed
    # Filter candidates: remove completed and blocked targets
    remaining_candidates = [
        t for t in campaign.targets
        if t.id not in completed_target_ids and t.id not in blocked_target_ids
    ]

    # Evaluate dependency eligibility
    newly_eligible = []
    for cand in remaining_candidates:
        if all(p in completed_target_ids for p in cand.prerequisites):
            newly_eligible.append(cand.id)

    # Replan remaining sols from sol_index onward
    # Keep sols < sol_index frozen
    frozen_sorties = [s for s in updated_sorties if s.sol_index < sol_index]
    sols_remaining = (campaign.config.max_sols or 10) - len(frozen_sorties)

    if sols_remaining > 0 and remaining_candidates:
        replan_cfg = copy.deepcopy(campaign.config)
        replan_cfg.max_sols = sols_remaining

        # Update candidate prerequisites in local replan context (satisfied prerequisites are cleared)
        replanned_candidates = []
        for cand in remaining_candidates:
            cand_copy = copy.deepcopy(cand)
            cand_copy.prerequisites = [p for p in cand_copy.prerequisites if p not in completed_target_ids]
            replanned_candidates.append(cand_copy)

        sub_plan = plan_mission_campaign(
            campaign_id=campaign.campaign_id,
            name=campaign.name,
            config=replan_cfg,
            targets=replanned_candidates,
            terrain=terrain,
            description=f"Replanned on progress event {event_type} at sol {sol_index}",
        )

        # Shift sol indices of newly planned sorties to follow frozen sorties
        new_sorties: List[CampaignSortie] = []
        for idx, sub_sortie in enumerate(sub_plan.sorties):
            sub_copy = copy.deepcopy(sub_sortie)
            sub_copy.sol_index = len(frozen_sorties) + idx + 1
            sub_copy.sortie_id = f"sortie_sol_{sub_copy.sol_index:02d}"
            sub_copy.name = f"Sol {sub_copy.sol_index}: {', '.join(sub_copy.target_names[:2])}..."
            sub_copy.status = SortieLifecycleState.READY.value if sub_copy.sol_index > sol_index else SortieLifecycleState.IN_PROGRESS.value
            new_sorties.append(sub_copy)

        combined_sorties = frozen_sorties + new_sorties
    else:
        combined_sorties = frozen_sorties

    # Recalculate Summary
    total_dist = sum(s.distance_m for s in combined_sorties)
    total_travel = sum(s.travel_time_s for s in combined_sorties)
    total_dwell = sum(s.dwell_time_s for s in combined_sorties)
    total_dur = sum(s.total_duration_s for s in combined_sorties)
    total_score = sum(s.science_score for s in combined_sorties)

    all_scheduled_target_ids: Set[str] = set()
    for s in combined_sorties:
        all_scheduled_target_ids.update(s.target_ids)
    all_scheduled_target_ids.update(completed_target_ids)

    unscheduled_count = len([t for t in campaign.targets if t.id not in all_scheduled_target_ids])

    updated_summary = CampaignSummary(
        total_sols=len(combined_sorties),
        total_sorties=len(combined_sorties),
        total_distance_m=round(total_dist, 1),
        total_travel_time_s=round(total_travel, 1),
        total_dwell_time_s=round(total_dwell, 1),
        total_duration_s=round(total_dur, 1),
        total_science_score=round(total_score, 1),
        targets_total=len(campaign.targets),
        targets_scheduled=len(all_scheduled_target_ids),
        targets_unscheduled=unscheduled_count,
        targets_completed=len(completed_target_ids),
        is_campaign_feasible=True,
        overall_status="IN_PROGRESS" if len(completed_target_ids) < len(campaign.targets) else "COMPLETED",
        bottlenecks_and_notes=[f"Active Sol: {sol_index}; Progress: {len(completed_target_ids)}/{len(campaign.targets)} targets complete."],
    )

    # Synthesize revision comparison delta
    prev_summary = campaign.summary
    delta_dist = round(total_dist - prev_summary.total_distance_m, 1)
    delta_dur = round(total_dur - prev_summary.total_duration_s, 1)
    delta_score = round(total_score - prev_summary.total_science_score, 1)

    revision_comparison = {
        "delta_distance_m": delta_dist,
        "delta_duration_s": delta_dur,
        "delta_science_score": delta_score,
        "newly_unscheduled_targets": [t.id for t in campaign.targets if t.id not in all_scheduled_target_ids and t.id not in blocked_target_ids],
        "resequenced_sorties": [s.sortie_id for s in combined_sorties],
        "newly_eligible_targets": newly_eligible,
    }

    # Progress state
    progress_state = calculate_campaign_progress_metrics(
        campaign=campaign,
        completed_target_ids=completed_target_ids,
        blocked_target_ids=blocked_target_ids,
        observation_ids=all_observation_ids,
        active_sol_index=sol_index,
    )

    # Increment Version and Construct Revised Campaign
    new_version = campaign.version + 1
    new_campaign = MissionCampaign(
        schema_version="1.0.0",
        campaign_id=campaign.campaign_id,
        name=campaign.name,
        description=campaign.description,
        version=new_version,
        revision_id=f"rev_{new_version:02d}_{event_type.lower()}",
        parent_campaign_id=campaign.campaign_id,
        created_at_utc=campaign.created_at_utc,
        updated_at_utc=now_iso,
        region_id=campaign.region_id,
        terrain_dataset_id=campaign.terrain_dataset_id,
        reproducibility_manifest=campaign.reproducibility_manifest,
        config=campaign.config,
        targets=list(target_map.values()),
        sorties=combined_sorties,
        summary=updated_summary,
        disruption=campaign.disruption,
        revision_comparison=revision_comparison,
        progress=progress_state,
        observations_summary={
            "total_observations": len(all_observation_ids),
            "simulated_count": len(all_observation_ids) if observation and observation.is_simulated else 0,
            "imported_count": 0,
            "observations_by_type": {observation.observation_type: 1} if observation else {},
        },
    )

    return new_campaign, progress_event, observation
