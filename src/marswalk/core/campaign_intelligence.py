"""
MarsWalk 2.0 (Project Atlas) — Milestone 11C: Campaign Intelligence & Adaptive Science Reprioritization
=========================================================================================================
Dynamically adapts multi-sol campaign schedules and candidate target priorities based on:
  1. User-defined scientific objectives and priority weights.
  2. Linked science observations and explicitly recorded objective classifications:
     - SUPPORTS_OBJECTIVE
     - DOES_NOT_SUPPORT_OBJECTIVE
     - INCONCLUSIVE
     - NOT_ASSESSED
  3. Explicit follow-up / repeat observation requests.
  4. Real terrain traversal reachability and daily life-support duration bounds.

Scientific Integrity & Provenance Constraints:
  - Do NOT infer scientific success automatically from a target merely being visited.
  - Inconclusive observations do NOT imply success or failure.
  - The provenance of an observation (SIMULATED vs IMPORTED_PDS_MEDA vs MEASURED_IN_SITU)
    is strictly preserved and NEVER altered during reprioritization.
  - Completed targets are permanently protected by the Non-Rescheduling Invariant
    (unless an explicit repeat observation is requested).
  - Prior executed sols and historical campaign versions remain strictly immutable.
"""

import os
import copy
import uuid
import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Set, Tuple

import rasterio

from marswalk.core.terrain import TerrainGrid
from marswalk.core.mission_campaign import (
    CampaignTarget,
    CampaignConfig,
    CampaignSortie,
    CampaignSummary,
    MissionCampaign,
    TargetStatus,
    PlanningProfile,
    plan_mission_campaign,
)
from marswalk.core.campaign_progress import (
    ObservationProvenance,
    ScienceObservation,
    calculate_campaign_progress_metrics,
)
from marswalk.api.contracts import validate_contract


class ObjectiveClassification(str, Enum):
    """Explicit scientific evaluation of an observation relative to target objectives."""
    SUPPORTS_OBJECTIVE = "SUPPORTS_OBJECTIVE"
    DOES_NOT_SUPPORT_OBJECTIVE = "DOES_NOT_SUPPORT_OBJECTIVE"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_ASSESSED = "NOT_ASSESSED"


@dataclass
class TargetRationale:
    """Explains why an individual target's schedule or priority changed."""
    target_id: str
    target_name: str
    status_change: str  # UNCHANGED, EXPEDITED, POSTPONED, UNBLOCKED, DEFERRED, REPEAT_ADDED, COMPLETED_PRESERVED
    reason: str
    original_sol: Optional[int] = None
    revised_sol: Optional[int] = None
    supporting_observation_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_name": self.target_name,
            "original_sol": self.original_sol,
            "revised_sol": self.revised_sol,
            "status_change": self.status_change,
            "reason": self.reason,
            "supporting_observation_ids": list(self.supporting_observation_ids),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TargetRationale":
        return cls(
            target_id=str(data["target_id"]),
            target_name=str(data["target_name"]),
            status_change=str(data["status_change"]),
            reason=str(data["reason"]),
            original_sol=data.get("original_sol"),
            revised_sol=data.get("revised_sol"),
            supporting_observation_ids=list(data.get("supporting_observation_ids", [])),
        )


@dataclass
class StrategyMetrics:
    """Summary metrics of a campaign scheduling strategy for direct trade-off comparison."""
    profile_name: str
    total_sols: int
    total_distance_m: float
    total_duration_s: float
    total_science_score: float
    targets_scheduled: int
    targets_completed: int
    targets_deferred: int
    is_feasible: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "total_sols": self.total_sols,
            "total_distance_m": round(float(self.total_distance_m), 1),
            "total_duration_s": round(float(self.total_duration_s), 1),
            "total_science_score": round(float(self.total_science_score), 1),
            "targets_scheduled": self.targets_scheduled,
            "targets_completed": self.targets_completed,
            "targets_deferred": self.targets_deferred,
            "is_feasible": self.is_feasible,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyMetrics":
        return cls(
            profile_name=str(data["profile_name"]),
            total_sols=int(data["total_sols"]),
            total_distance_m=float(data["total_distance_m"]),
            total_duration_s=float(data["total_duration_s"]),
            total_science_score=float(data["total_science_score"]),
            targets_scheduled=int(data["targets_scheduled"]),
            targets_completed=int(data["targets_completed"]),
            targets_deferred=int(data["targets_deferred"]),
            is_feasible=bool(data["is_feasible"]),
        )


@dataclass
class CampaignIntelligenceRecommendation:
    """Actionable recommendation artifact comparing current and adaptive campaign strategies."""
    campaign_id: str
    source_version: int
    proposed_version: int
    proposed_revision_id: str
    created_at_utc: str
    target_rationales: List[TargetRationale]
    strategy_comparison: Dict[str, StrategyMetrics]
    has_improvements: bool
    proposed_campaign: Dict[str, Any]
    schema_version: str = "1.0.0"
    objective_weights: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    limitations_disclaimer: str = (
        "Derived recommendations are planning suggestions for the simulated campaign—"
        "not autonomous scientific conclusions. Observational outcomes must be evaluated by qualified investigators."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "campaign_id": self.campaign_id,
            "source_version": self.source_version,
            "proposed_version": self.proposed_version,
            "proposed_revision_id": self.proposed_revision_id,
            "created_at_utc": self.created_at_utc,
            "objective_weights": dict(self.objective_weights),
            "has_improvements": self.has_improvements,
            "strategy_comparison": {k: v.to_dict() for k, v in self.strategy_comparison.items()},
            "target_rationales": [r.to_dict() for r in self.target_rationales],
            "proposed_campaign": dict(self.proposed_campaign),
            "warnings": list(self.warnings),
            "limitations_disclaimer": self.limitations_disclaimer,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignIntelligenceRecommendation":
        rationales = [TargetRationale.from_dict(r) for r in data.get("target_rationales", [])]
        comparison = {
            k: StrategyMetrics.from_dict(v)
            for k, v in data.get("strategy_comparison", {}).items()
            if isinstance(v, dict)
        }
        return cls(
            schema_version=data.get("schema_version", "1.0.0"),
            campaign_id=str(data["campaign_id"]),
            source_version=int(data["source_version"]),
            proposed_version=int(data["proposed_version"]),
            proposed_revision_id=str(data["proposed_revision_id"]),
            created_at_utc=str(data["created_at_utc"]),
            target_rationales=rationales,
            strategy_comparison=comparison,
            has_improvements=bool(data.get("has_improvements", False)),
            proposed_campaign=dict(data.get("proposed_campaign", {})),
            objective_weights=dict(data.get("objective_weights", {})),
            warnings=list(data.get("warnings", [])),
            limitations_disclaimer=data.get("limitations_disclaimer", ""),
        )


def evaluate_campaign_intelligence(
    campaign: MissionCampaign,
    terrain: TerrainGrid,
    objective_assessments: Optional[List[Dict[str, Any]]] = None,
    objective_weights: Optional[Dict[str, float]] = None,
    repeat_requests: Optional[List[str]] = None,
    observations: Optional[List[Dict[str, Any]]] = None,
    preferred_profile: Optional[str] = None,
    transform: Optional[rasterio.Affine] = None,
) -> CampaignIntelligenceRecommendation:
    """
    Evaluates recorded observational evidence, user objective weights, and dependency DAGs
    to propose an adaptive, explainable campaign reprioritization for remaining sols.
    """
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    objective_weights = objective_weights or {}
    repeat_requests = repeat_requests or []
    observations = observations or []
    objective_assessments = objective_assessments or []
    warnings: List[str] = []

    # 1. Validate objective weights: weights must be non-negative
    for obj_name, weight in objective_weights.items():
        if weight is None or float(weight) < 0.0:
            raise ValueError(f"Objective weight for '{obj_name}' must be a non-negative number; got {weight}")

    # 2. Extract current execution progress and state
    progress = campaign.progress or {}
    active_sol_index = int(progress.get("active_sol_index", 1))
    completed_target_ids: Set[str] = set(progress.get("completed_target_ids", []))
    blocked_target_ids: Set[str] = set(progress.get("blocked_target_ids", []))
    all_obs_ids: List[str] = list(progress.get("observation_ids", []))

    # Incorporate passed observations
    for obs in observations:
        oid = obs.get("observation_id")
        if oid and oid not in all_obs_ids:
            all_obs_ids.append(oid)

    # 3. Build assessment & observation lookup map
    assessment_map: Dict[str, Dict[str, Any]] = {}
    for item in objective_assessments:
        if isinstance(item, dict) and "target_id" in item:
            tid = item["target_id"]
            assessment_map[tid] = item

    obs_by_target: Dict[str, List[Dict[str, Any]]] = {}
    for obs in observations:
        tid = obs.get("target_id")
        if tid:
            obs_by_target.setdefault(tid, []).append(obs)

    # Map target original scheduled sol
    original_sol_map: Dict[str, Optional[int]] = {}
    for s in campaign.sorties:
        for tid in s.target_ids:
            original_sol_map[tid] = s.sol_index

    # 4. Freeze past sorties (sols < active_sol_index)
    frozen_sorties: List[CampaignSortie] = [
        s for s in campaign.sorties if s.sol_index < active_sol_index
    ]
    max_sols = campaign.config.max_sols or 10
    sols_remaining = max_sols - len(frozen_sorties)

    if sols_remaining <= 0:
        warnings.append("Campaign has no remaining sols to reprioritize.")

    # 5. Adapt Candidate Targets & Calculate Intelligence Multipliers
    target_dict = {t.id: copy.deepcopy(t) for t in campaign.targets}
    candidate_pool: List[CampaignTarget] = []
    rationales: List[TargetRationale] = []

    for t in campaign.targets:
        tid = t.id
        assessment = assessment_map.get(tid, {})
        classification = assessment.get("objective_classification") or getattr(t, "objective_classification", ObjectiveClassification.NOT_ASSESSED.value)
        target_obs = obs_by_target.get(tid, [])
        obs_ids = [o.get("observation_id") for o in target_obs if o.get("observation_id")]
        repeat_requested = (tid in repeat_requests) or bool(assessment.get("repeat_observation_requested"))

        # Case A: Target already completed
        if tid in completed_target_ids:
            if repeat_requested and sols_remaining > 0:
                # User or science team requested explicit follow-up inspection
                repeat_cand = copy.deepcopy(t)
                repeat_cand.id = f"{tid}_repeat"
                repeat_cand.name = f"{t.name} (Repeat Inspection)"
                repeat_cand.priority_score = round(t.priority_score * 0.9, 1)
                repeat_cand.prerequisites = []  # Root target for follow-up
                repeat_cand.dwell_time_s = max(600.0, t.dwell_time_s * 0.8)
                candidate_pool.append(repeat_cand)

                rationales.append(TargetRationale(
                    target_id=tid,
                    target_name=t.name,
                    status_change="REPEAT_ADDED",
                    reason="Target completed on prior sol, but explicit repeat observation requested for secondary inspection.",
                    original_sol=original_sol_map.get(tid),
                    revised_sol=None,  # to be assigned
                    supporting_observation_ids=obs_ids,
                ))
            else:
                # NON-RESCHEDULING INVARIANT: completed target never re-enters candidate pool
                rationales.append(TargetRationale(
                    target_id=tid,
                    target_name=t.name,
                    status_change="COMPLETED_PRESERVED",
                    reason="Target completed on prior sol and preserved in campaign history; omitted from future scheduling.",
                    original_sol=original_sol_map.get(tid),
                    revised_sol=original_sol_map.get(tid),
                    supporting_observation_ids=obs_ids,
                ))
            continue

        # Case B: Target is blocked
        if tid in blocked_target_ids:
            rationales.append(TargetRationale(
                target_id=tid,
                target_name=t.name,
                status_change="DEFERRED",
                reason=f"Target is blocked by terrain hazard: {t.unscheduled_reason or 'Hazardous obstacle'}.",
                original_sol=original_sol_map.get(tid),
                revised_sol=None,
                supporting_observation_ids=obs_ids,
            ))
            continue

        # Case C: Active remaining candidate target
        cand = copy.deepcopy(t)

        # 5.1 Apply User Objective Weights
        user_weight = 1.0
        if cand.science_objective and cand.science_objective in objective_weights:
            user_weight = float(objective_weights[cand.science_objective])
        elif cand.id in objective_weights:
            user_weight = float(objective_weights[cand.id])

        adjusted_score = cand.priority_score * user_weight

        # 5.2 Adaptive Evidence Modifiers based on Prerequisite Observations
        evidence_note = ""
        evidence_boost = 1.0
        for prereq_id in cand.prerequisites:
            prereq_assess = assessment_map.get(prereq_id, {})
            prereq_class = prereq_assess.get("objective_classification")

            if prereq_class == ObjectiveClassification.SUPPORTS_OBJECTIVE.value:
                evidence_boost *= 1.25  # 25% priority elevation
                evidence_note += f" Prerequisite '{prereq_id}' validated scientific objective (+25%)."
            elif prereq_class == ObjectiveClassification.DOES_NOT_SUPPORT_OBJECTIVE.value:
                evidence_boost *= 0.65  # 35% priority reduction
                evidence_note += f" Prerequisite '{prereq_id}' refuted target hypothesis (-35%)."
            elif prereq_class == ObjectiveClassification.INCONCLUSIVE.value:
                evidence_note += f" Prerequisite '{prereq_id}' observation inconclusive (neutral)."

        final_score = round(min(100.0, max(1.0, adjusted_score * evidence_boost)), 1)
        cand.priority_score = final_score
        target_dict[cand.id] = cand

        # 5.3 Filter satisfied prerequisites for scheduler
        # Completed prerequisites are already accomplished in reality!
        cand.prerequisites = [p for p in cand.prerequisites if p not in completed_target_ids]

        # Check if any remaining prerequisite is blocked: if so, this target cannot be reached!
        if any(p in blocked_target_ids for p in cand.prerequisites):
            cand.status = TargetStatus.REJECTED_PREREQUISITE_FAILED.value
            cand.unscheduled_reason = "Prerequisite is blocked by terrain obstacle."
            rationales.append(TargetRationale(
                target_id=tid,
                target_name=t.name,
                status_change="DEFERRED",
                reason="Unscheduled: Upstream prerequisite is blocked by terrain hazard.",
                original_sol=original_sol_map.get(tid),
                revised_sol=None,
                supporting_observation_ids=obs_ids,
            ))
            continue

        candidate_pool.append(cand)

    # 6. Replan Remaining Sols with Adaptive Candidates
    replan_profile = preferred_profile or campaign.config.planning_profile
    replan_cfg = copy.deepcopy(campaign.config)
    replan_cfg.planning_profile = replan_profile
    replan_cfg.max_sols = max(1, sols_remaining)

    sub_plan = plan_mission_campaign(
        campaign_id=campaign.campaign_id,
        name=campaign.name,
        config=replan_cfg,
        targets=candidate_pool,
        terrain=terrain,
        description=f"Adaptive intelligence replan at Sol {active_sol_index}",
    )

    # Shift sol indices of newly planned sorties to succeed frozen sorties
    adaptive_sorties: List[CampaignSortie] = []
    revised_sol_map: Dict[str, Optional[int]] = {}
    for idx, sub_sortie in enumerate(sub_plan.sorties):
        s_copy = copy.deepcopy(sub_sortie)
        s_copy.sol_index = len(frozen_sorties) + idx + 1
        s_copy.sortie_id = f"sortie_sol_{s_copy.sol_index:02d}"
        s_copy.name = f"Sol {s_copy.sol_index}: {', '.join(s_copy.target_names[:2])}..."
        s_copy.status = "READY" if s_copy.sol_index > active_sol_index else "IN_PROGRESS"
        adaptive_sorties.append(s_copy)

        for tid in s_copy.target_ids:
            # Map clean base ID if repeat
            clean_id = tid[:-7] if tid.endswith("_repeat") else tid
            revised_sol_map[clean_id] = s_copy.sol_index

    # Combine frozen sorties + adaptive sorties
    combined_sorties = frozen_sorties + adaptive_sorties

    # 7. Synthesize Explanations & Rationales for Candidate Targets
    all_scheduled_tids = set()
    for s in combined_sorties:
        all_scheduled_tids.update(s.target_ids)

    for cand in candidate_pool:
        clean_id = cand.id[:-7] if cand.id.endswith("_repeat") else cand.id
        if clean_id in completed_target_ids:
            continue

        orig_sol = original_sol_map.get(clean_id)
        rev_sol = revised_sol_map.get(clean_id)
        target_obs = obs_by_target.get(clean_id, [])
        obs_ids = [o.get("observation_id") for o in target_obs if o.get("observation_id")]

        if rev_sol is not None:
            if orig_sol is None:
                status_change = "UNBLOCKED"
                reason = "Newly scheduled into campaign: Upstream prerequisites satisfied by prior sol progress."
            elif rev_sol < orig_sol:
                status_change = "EXPEDITED"
                reason = f"Expedited from Sol {orig_sol} to Sol {rev_sol}: Elevating priority based on user weights and positive observation evidence."
            elif rev_sol > orig_sol:
                status_change = "POSTPONED"
                reason = f"Postponed from Sol {orig_sol} to Sol {rev_sol}: Reprioritized relative to higher-yielding objectives under daily life-support limits."
            else:
                status_change = "UNCHANGED"
                reason = f"Preserved at optimal Sol {rev_sol} position."
        else:
            status_change = "DEFERRED"
            reason = f"Deferred from schedule: Life-support duration bounds or sol limits ({max_sols} sols) reached before target could be traversed."

        rationales.append(TargetRationale(
            target_id=clean_id,
            target_name=cand.name,
            status_change=status_change,
            reason=reason,
            original_sol=orig_sol,
            revised_sol=rev_sol,
            supporting_observation_ids=obs_ids,
        ))

    # 8. Multi-Strategy Trade-off Comparison
    # Evaluate baseline metrics
    baseline_summary = campaign.summary
    baseline_metrics = StrategyMetrics(
        profile_name="Current Baseline Plan",
        total_sols=baseline_summary.total_sols,
        total_distance_m=baseline_summary.total_distance_m,
        total_duration_s=baseline_summary.total_duration_s,
        total_science_score=baseline_summary.total_science_score,
        targets_scheduled=baseline_summary.targets_scheduled,
        targets_completed=baseline_summary.targets_completed,
        targets_deferred=baseline_summary.targets_unscheduled,
        is_feasible=baseline_summary.is_campaign_feasible,
    )

    # Evaluate adaptive proposed metrics
    total_dist = round(sum(s.distance_m for s in combined_sorties), 1)
    total_dur = round(sum(s.total_duration_s for s in combined_sorties), 1)
    total_score = round(sum(s.science_score for s in combined_sorties), 1)
    scheduled_count = len(all_scheduled_tids.union(completed_target_ids))
    deferred_count = max(0, len(campaign.targets) - scheduled_count)

    proposed_metrics = StrategyMetrics(
        profile_name="Adaptive Intelligence Plan",
        total_sols=len(combined_sorties),
        total_distance_m=total_dist,
        total_duration_s=total_dur,
        total_science_score=total_score,
        targets_scheduled=scheduled_count,
        targets_completed=len(completed_target_ids),
        targets_deferred=deferred_count,
        is_feasible=True,
    )

    # Evaluate alternative planning profiles for comparison
    strategy_comparison: Dict[str, StrategyMetrics] = {
        "baseline": baseline_metrics,
        "proposed_adaptive": proposed_metrics,
    }

    for alt_prof in (PlanningProfile.SCIENCE_PRIORITY.value, PlanningProfile.TIME_CONSTRAINED.value, PlanningProfile.CONSERVATIVE.value):
        alt_cfg = copy.deepcopy(replan_cfg)
        alt_cfg.planning_profile = alt_prof
        alt_plan = plan_mission_campaign(
            campaign_id=campaign.campaign_id,
            name=campaign.name,
            config=alt_cfg,
            targets=copy.deepcopy(candidate_pool),
            terrain=terrain,
        )
        alt_dist = round(sum(s.distance_m for s in frozen_sorties) + sum(s.distance_m for s in alt_plan.sorties), 1)
        alt_dur = round(sum(s.total_duration_s for s in frozen_sorties) + sum(s.total_duration_s for s in alt_plan.sorties), 1)
        alt_score = round(sum(s.science_score for s in frozen_sorties) + sum(s.science_score for s in alt_plan.sorties), 1)
        alt_tids = set(t for s in alt_plan.sorties for t in s.target_ids).union(completed_target_ids)
        strategy_comparison[alt_prof] = StrategyMetrics(
            profile_name=f"Profile: {alt_prof}",
            total_sols=len(frozen_sorties) + len(alt_plan.sorties),
            total_distance_m=alt_dist,
            total_duration_s=alt_dur,
            total_science_score=alt_score,
            targets_scheduled=len(alt_tids),
            targets_completed=len(completed_target_ids),
            targets_deferred=max(0, len(campaign.targets) - len(alt_tids)),
            is_feasible=alt_plan.summary.is_campaign_feasible,
        )

    # 9. Determine If Genuine Improvements Were Established
    has_improvements = False
    # Check if target sequence, sol assignment, or scheduled set changed
    orig_sched = set(tid for s in campaign.sorties for tid in s.target_ids)
    new_sched = set(tid for s in combined_sorties for tid in s.target_ids)
    if orig_sched != new_sched or any(r.status_change in ("EXPEDITED", "POSTPONED", "UNBLOCKED", "REPEAT_ADDED") for r in rationales):
        has_improvements = True
    elif bool(objective_weights) or bool(repeat_requests) or abs(total_score - baseline_summary.total_science_score) > 1e-3 or abs(total_dur - baseline_summary.total_duration_s) > 1.0:
        has_improvements = True

    if not has_improvements:
        warnings.append("Current schedule is already optimal under current constraints and observations. Baseline plan preserved.")

    # 10. Construct Proposed Campaign Version
    proposed_version = campaign.version + 1
    proposed_revision_id = f"rev_{proposed_version:02d}_intelligence"

    proposed_summary = CampaignSummary(
        total_sols=len(combined_sorties),
        total_sorties=len(combined_sorties),
        total_distance_m=total_dist,
        total_travel_time_s=round(sum(s.travel_time_s for s in combined_sorties), 1),
        total_dwell_time_s=round(sum(s.dwell_time_s for s in combined_sorties), 1),
        total_duration_s=total_dur,
        total_science_score=total_score,
        targets_total=len(campaign.targets),
        targets_scheduled=scheduled_count,
        targets_unscheduled=deferred_count,
        targets_completed=len(completed_target_ids),
        is_campaign_feasible=True,
        overall_status="IN_PROGRESS" if len(completed_target_ids) < len(campaign.targets) else "COMPLETED",
        bottlenecks_and_notes=[f"Adaptive intelligence plan evaluated at Sol {active_sol_index}."],
    )

    proposed_progress = calculate_campaign_progress_metrics(
        campaign=campaign,
        completed_target_ids=completed_target_ids,
        blocked_target_ids=blocked_target_ids,
        observation_ids=all_obs_ids,
        active_sol_index=active_sol_index,
    )

    proposed_campaign = MissionCampaign(
        schema_version="1.0.0",
        campaign_id=campaign.campaign_id,
        name=campaign.name,
        description=f"{campaign.description} [Reprioritized at Sol {active_sol_index}]",
        version=proposed_version,
        revision_id=proposed_revision_id,
        parent_campaign_id=campaign.campaign_id,
        created_at_utc=campaign.created_at_utc,
        updated_at_utc=now_iso,
        region_id=campaign.region_id,
        terrain_dataset_id=campaign.terrain_dataset_id,
        reproducibility_manifest=campaign.reproducibility_manifest,
        config=replan_cfg,
        targets=list(target_dict.values()),
        sorties=combined_sorties,
        summary=proposed_summary,
        disruption=campaign.disruption,
        revision_comparison={
            "delta_distance_m": round(total_dist - baseline_summary.total_distance_m, 1),
            "delta_duration_s": round(total_dur - baseline_summary.total_duration_s, 1),
            "delta_science_score": round(total_score - baseline_summary.total_science_score, 1),
            "newly_unscheduled_targets": [r.target_id for r in rationales if r.status_change == "DEFERRED"],
            "resequenced_sorties": [s.sortie_id for s in combined_sorties],
            "reprioritized_targets": [r.target_id for r in rationales if r.status_change in ("EXPEDITED", "POSTPONED")],
        },
        progress=proposed_progress,
        observations_summary=campaign.observations_summary,
    )

    recommendation = CampaignIntelligenceRecommendation(
        campaign_id=campaign.campaign_id,
        source_version=campaign.version,
        proposed_version=proposed_version,
        proposed_revision_id=proposed_revision_id,
        created_at_utc=now_iso,
        target_rationales=rationales,
        strategy_comparison=strategy_comparison,
        has_improvements=has_improvements,
        proposed_campaign=proposed_campaign.to_dict(),
        objective_weights=objective_weights,
        warnings=warnings,
    )

    # Validate output contract
    validate_contract(recommendation.to_dict(), "campaign-reprioritization", raise_on_error=True)

    return recommendation
