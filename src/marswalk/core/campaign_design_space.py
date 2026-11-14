# src/marswalk/core/campaign_design_space.py
"""
MarsWalk 2.0 — Milestone 11H: Campaign Design Space Explorer & Pareto Optimization.

This module evaluates a bounded set of plausible multi-sol campaign configurations,
compares real planner outputs across multi-dimensional objective vectors, identifies
Pareto-efficient alternatives, and provides grounded trade-off recommendations.

Scientific & Operational Principles:
1. Deterministic Multi-Objective Evaluation:
   Objectives are treated as a multi-dimensional vector, avoiding arbitrary opaque composite scores:
   (Maximize Science Coverage, Minimize Duration, Minimize Distance, Minimize Unallocated Priority, Minimize Conflicts).
2. Strict Mathematical Dominance:
   Candidate A dominates B (A > B) iff A is as good as B across all objectives, strictly better
   in at least one, and feasible.
3. Feasibility Pre-requisite:
   Infeasible candidates cannot dominate feasible alternatives and are partitioned separately with explicit failure causes.
4. Bounded Search & Completeness Accounting:
   Evaluations are strictly capped (max_candidates, max_planner_calls). If search limits are reached,
   the engine explicitly records is_exhaustive=False and documents unexplored parameter scope.
5. Campaign Baseline Immutability:
   Promoting a candidate creates a distinct new version (v{n+1}) without modifying historical campaign records.
"""

from __future__ import annotations

import copy
import enum
import hashlib
import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import rasterio

from marswalk.api.contracts import (
    SCHEMA_VERSION,
    sanitize_for_json,
    validate_campaign_design_space_record,
)
from marswalk.core.terrain import TerrainGrid
from marswalk.core.mission_campaign import (
    CampaignTarget,
    CampaignConfig,
    MissionCampaign,
    PlanningProfile,
    plan_mission_campaign,
)
from marswalk.core.campaign_coordination import (
    create_default_units,
    allocate_campaign_coordination,
    CoordinationPlan,
)

DESIGN_SPACE_DISCLAIMER = (
    "The Campaign Design Space Explorer is a deterministic multi-objective planning tool for simulated Mars "
    "exploration evaluation. It does NOT guarantee global mathematical optimality, employ probabilistic forecasting, "
    "or represent certified flight operations software. All candidate trade-offs are grounded in simulated route planning."
)


class DominanceStatus(str, enum.Enum):
    PARETO_EFFICIENT = "PARETO_EFFICIENT"
    DOMINATED = "DOMINATED"
    INFEASIBLE = "INFEASIBLE"
    INCOMPARABLE = "INCOMPARABLE"


class CandidateStatus(str, enum.Enum):
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    ERROR = "ERROR"


@dataclass
class SearchBounds:
    max_candidates: int = 12
    max_planner_calls: int = 15

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_candidates": int(self.max_candidates),
            "max_planner_calls": int(self.max_planner_calls),
        }


@dataclass
class SearchCompleteness:
    candidates_considered: int = 0
    candidates_deduplicated: int = 0
    candidates_evaluated: int = 0
    candidates_rejected: int = 0
    is_exhaustive: bool = False
    limit_reached: bool = False
    unexplored_scope_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidates_considered": int(self.candidates_considered),
            "candidates_deduplicated": int(self.candidates_deduplicated),
            "candidates_evaluated": int(self.candidates_evaluated),
            "candidates_rejected": int(self.candidates_rejected),
            "is_exhaustive": bool(self.is_exhaustive),
            "limit_reached": bool(self.limit_reached),
            "unexplored_scope_notes": self.unexplored_scope_notes,
        }


@dataclass
class CandidateObjectives:
    science_coverage_pct: float
    total_duration_s: float
    total_distance_m: float
    unallocated_priority: float
    temporal_conflicts_count: int
    sortie_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "science_coverage_pct": round(float(self.science_coverage_pct), 1),
            "total_duration_s": round(float(self.total_duration_s), 1),
            "total_distance_m": round(float(self.total_distance_m), 1),
            "unallocated_priority": round(float(self.unallocated_priority), 1),
            "temporal_conflicts_count": int(self.temporal_conflicts_count),
            "sortie_count": int(self.sortie_count),
        }


@dataclass
class CandidateEvaluation:
    candidate_id: str
    fingerprint: str
    configuration: Dict[str, Any]
    status: str
    objectives: CandidateObjectives
    dominance_status: str
    dominated_by: List[str] = field(default_factory=list)
    tradeoff_explanation: str = ""
    infeasibility_reasons: List[str] = field(default_factory=list)
    planned_sorties: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "candidate_id": self.candidate_id,
            "fingerprint": self.fingerprint,
            "configuration": self.configuration,
            "status": self.status,
            "objectives": self.objectives.to_dict(),
            "dominance_status": self.dominance_status,
            "dominated_by": list(self.dominated_by),
            "tradeoff_explanation": self.tradeoff_explanation,
        }
        if self.infeasibility_reasons:
            data["infeasibility_reasons"] = list(self.infeasibility_reasons)
        return data


def compute_config_fingerprint(config_dict: Dict[str, Any]) -> str:
    """Computes a canonical SHA-256 fingerprint for a configuration dictionary."""
    canonical_json = json.dumps(config_dict, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()


def check_dominance(a: CandidateEvaluation, b: CandidateEvaluation) -> bool:
    """
    Evaluates whether candidate A strictly dominates candidate B under Pareto multi-objective rules.
    Objectives:
    - science_coverage_pct: Maximize
    - total_duration_s: Minimize
    - total_distance_m: Minimize
    - unallocated_priority: Minimize
    - temporal_conflicts_count: Minimize

    Returns True iff A dominates B, False otherwise.
    Infeasible candidates cannot dominate feasible candidates.
    """
    if a.status != CandidateStatus.FEASIBLE.value:
        return False
    if b.status != CandidateStatus.FEASIBLE.value:
        # A feasible candidate strictly dominates an infeasible one
        return True

    oa = a.objectives
    ob = b.objectives

    # Condition 1: A must be at least as good as B on all objectives
    as_good = (
        oa.science_coverage_pct >= ob.science_coverage_pct and
        oa.total_duration_s <= ob.total_duration_s and
        oa.total_distance_m <= ob.total_distance_m and
        oa.unallocated_priority <= ob.unallocated_priority and
        oa.temporal_conflicts_count <= ob.temporal_conflicts_count
    )

    if not as_good:
        return False

    # Condition 2: A must be strictly better in at least one objective
    strictly_better = (
        oa.science_coverage_pct > ob.science_coverage_pct or
        oa.total_duration_s < ob.total_duration_s or
        oa.total_distance_m < ob.total_distance_m or
        oa.unallocated_priority < ob.unallocated_priority or
        oa.temporal_conflicts_count < ob.temporal_conflicts_count
    )

    return strictly_better


def classify_pareto_frontier(
    candidates: List[CandidateEvaluation],
) -> Tuple[List[CandidateEvaluation], List[CandidateEvaluation], List[CandidateEvaluation]]:
    """
    Pure mathematical classification of candidate evaluations into:
    1. Pareto-efficient frontier (non-dominated feasible candidates).
    2. Dominated feasible candidates (annotated with dominating references).
    3. Infeasible / error candidates.
    """
    feasible: List[CandidateEvaluation] = []
    infeasible: List[CandidateEvaluation] = []

    for cand in candidates:
        if cand.status == CandidateStatus.FEASIBLE.value:
            cand.dominated_by = []
            feasible.append(cand)
        else:
            cand.dominance_status = DominanceStatus.INFEASIBLE.value
            cand.dominated_by = []
            infeasible.append(cand)

    pareto: List[CandidateEvaluation] = []
    dominated: List[CandidateEvaluation] = []

    # Pairwise dominance evaluation among feasible candidates
    for i, a in enumerate(feasible):
        is_dominated = False
        dominators = []
        for j, b in enumerate(feasible):
            if i == j:
                continue
            if check_dominance(b, a):
                is_dominated = True
                dominators.append(b.candidate_id)

        a.dominated_by = dominators
        if is_dominated:
            a.dominance_status = DominanceStatus.DOMINATED.value
            dominated.append(a)
        else:
            a.dominance_status = DominanceStatus.PARETO_EFFICIENT.value
            pareto.append(a)

    return pareto, dominated, infeasible


def generate_candidate_configurations(
    baseline_config: Dict[str, Any],
    search_dimensions: Optional[Dict[str, Any]] = None,
    search_bounds: Optional[SearchBounds] = None,
) -> Tuple[List[Dict[str, Any]], SearchCompleteness]:
    """
    Deterministically generates a bounded list of candidate parameter deltas.
    Deduplicates identical configurations and enforces bounds limits.
    """
    bounds = search_bounds or SearchBounds()
    dims = search_dimensions or {}

    # Supported exploration dimensions with safe bounded defaults
    allowed_profiles = dims.get("profiles") or [
        PlanningProfile.SCIENCE_PRIORITY.value,
        PlanningProfile.TIME_CONSTRAINED.value,
        PlanningProfile.CONSERVATIVE.value,
    ]
    duration_limits = dims.get("duration_limits_s") or [
        21600.0,  # 6h
        28800.0,  # 8h (standard crew EVA)
        32400.0,  # 9h
    ]
    max_sols_options = dims.get("max_sols_options") or [2, 3, 4]

    # Deterministic grid generation
    seen_fingerprints = set()
    candidate_configs: List[Dict[str, Any]] = []

    considered_count = 0
    dedup_count = 0

    base_profile = baseline_config.get("planning_profile", PlanningProfile.SCIENCE_PRIORITY.value)
    base_dur = float(baseline_config.get("max_duration_per_sortie_s", 28800.0))
    base_sols = baseline_config.get("max_sols", 3)

    # 1. Baseline candidate itself is always candidate 1
    base_cand = {
        "planning_profile": base_profile,
        "max_duration_per_sortie_s": base_dur,
        "max_sols": base_sols,
        "is_baseline": True,
    }
    fp_base = compute_config_fingerprint(base_cand)
    seen_fingerprints.add(fp_base)
    candidate_configs.append(base_cand)
    considered_count += 1

    limit_reached = False
    unexplored_scope = ""

    # 2. Enumerate variations in deterministic nested order
    for prof in sorted(allowed_profiles):
        for dur in sorted(duration_limits):
            for sols in sorted(max_sols_options):
                if len(candidate_configs) >= bounds.max_candidates:
                    limit_reached = True
                    break

                cand_cfg = {
                    "planning_profile": prof,
                    "max_duration_per_sortie_s": float(dur),
                    "max_sols": int(sols),
                    "is_baseline": False,
                }
                considered_count += 1

                fp = compute_config_fingerprint(cand_cfg)
                if fp in seen_fingerprints:
                    dedup_count += 1
                    continue

                seen_fingerprints.add(fp)
                candidate_configs.append(cand_cfg)

            if limit_reached:
                break
        if limit_reached:
            break

    total_possible = len(allowed_profiles) * len(duration_limits) * len(max_sols_options)
    is_exhaustive = (len(candidate_configs) >= total_possible) and not limit_reached

    if limit_reached:
        unexplored_scope = f"Evaluation budget reached {bounds.max_candidates} candidates. Unexplored combinations: {total_possible - len(candidate_configs)}."
    else:
        unexplored_scope = "All bounded parameter combinations evaluated within configured budget."

    completeness = SearchCompleteness(
        candidates_considered=considered_count,
        candidates_deduplicated=dedup_count,
        candidates_evaluated=0,  # Will be populated after evaluation
        candidates_rejected=0,
        is_exhaustive=is_exhaustive,
        limit_reached=limit_reached,
        unexplored_scope_notes=unexplored_scope,
    )

    return candidate_configs, completeness


def evaluate_candidate_configuration(
    candidate_idx: int,
    candidate_config: Dict[str, Any],
    baseline_campaign: MissionCampaign,
    terrain: TerrainGrid,
    transform: Optional[rasterio.Affine] = None,
) -> CandidateEvaluation:
    """
    Evaluates a single candidate configuration through the authentic campaign planner.
    Constructs an isolated campaign instance and computes real route, duration, and science metrics.
    """
    cand_id = f"cand_cp_{candidate_idx:02d}"
    fp = compute_config_fingerprint(candidate_config)

    # 1. Build isolated CampaignConfig
    base_cfg_dict = baseline_campaign.config.to_dict()
    base_cfg_dict.update(candidate_config)
    eval_config = CampaignConfig.from_dict(base_cfg_dict)

    # 2. Run real campaign planning
    try:
        camp_result = plan_mission_campaign(
            campaign_id=f"{baseline_campaign.campaign_id}_{cand_id}",
            name=f"{baseline_campaign.name} [{candidate_config.get('planning_profile', 'default')}]",
            config=eval_config,
            targets=copy.deepcopy(baseline_campaign.targets),
            terrain=terrain,
        )

        # 3. Extract objectives
        summary = camp_result.summary
        total_prio = sum(t.priority_score for t in baseline_campaign.targets)
        completed_prio = sum(
            t.priority_score for s in camp_result.sorties for t in baseline_campaign.targets if t.id in s.target_ids
        )
        unalloc_prio = max(0.0, total_prio - completed_prio)
        cov_pct = round((completed_prio / max(1.0, total_prio)) * 100.0, 1)

        # Check feasibility
        is_feasible = True
        infeasibility_reasons = []

        if not camp_result.sorties:
            is_feasible = False
            infeasibility_reasons.append("Zero sorties could be planned within sol duration limits.")

        for s in camp_result.sorties:
            if not s.is_feasible:
                is_feasible = False
                infeasibility_reasons.append(f"Sortie {s.sol_index} infeasible due to terrain slope or barrier.")
            if s.total_duration_s > eval_config.max_duration_per_sortie_s + 60.0:  # Allow 1-min numerical tolerance
                is_feasible = False
                infeasibility_reasons.append(
                    f"Sortie {s.sol_index} duration ({s.total_duration_s:.0f}s) exceeds limit ({eval_config.max_duration_per_sortie_s:.0f}s)."
                )

        status_str = CandidateStatus.FEASIBLE.value if is_feasible else CandidateStatus.INFEASIBLE.value

        objectives = CandidateObjectives(
            science_coverage_pct=cov_pct,
            total_duration_s=round(summary.total_duration_s, 1),
            total_distance_m=round(summary.total_distance_m, 1),
            unallocated_priority=round(unalloc_prio, 1),
            temporal_conflicts_count=0,
            sortie_count=len(camp_result.sorties),
        )

        return CandidateEvaluation(
            candidate_id=cand_id,
            fingerprint=fp,
            configuration=candidate_config,
            status=status_str,
            objectives=objectives,
            dominance_status=DominanceStatus.DOMINATED.value,  # Will be classified in batch
            infeasibility_reasons=infeasibility_reasons,
            planned_sorties=[s.to_dict() for s in camp_result.sorties],
            summary=summary.to_dict(),
        )

    except Exception as err:
        return CandidateEvaluation(
            candidate_id=cand_id,
            fingerprint=fp,
            configuration=candidate_config,
            status=CandidateStatus.ERROR.value,
            objectives=CandidateObjectives(
                science_coverage_pct=0.0,
                total_duration_s=0.0,
                total_distance_m=0.0,
                unallocated_priority=sum(t.priority_score for t in baseline_campaign.targets),
                temporal_conflicts_count=0,
                sortie_count=0,
            ),
            dominance_status=DominanceStatus.INFEASIBLE.value,
            infeasibility_reasons=[f"Planner execution exception: {str(err)}"],
        )


def build_tradeoff_explanations(
    pareto_candidates: List[CandidateEvaluation],
    dominated_candidates: List[CandidateEvaluation],
    baseline_evaluation: Optional[CandidateEvaluation] = None,
) -> List[Dict[str, Any]]:
    """
    Generates grounded, human-readable trade-off rationales comparing Pareto frontier alternatives.
    """
    recommendations: List[Dict[str, Any]] = []

    if not pareto_candidates:
        return recommendations

    # Sort pareto candidates by science coverage descending, then duration ascending
    sorted_pareto = sorted(
        pareto_candidates,
        key=lambda c: (-c.objectives.science_coverage_pct, c.objectives.total_duration_s)
    )

    # 1. Maximal Science Frontier Candidate
    max_sci = sorted_pareto[0]
    rec_max_sci = {
        "recommendation_id": f"rec_ds_{uuid.uuid4().hex[:6]}",
        "candidate_id": max_sci.candidate_id,
        "headline": f"Maximal Science Yield ({max_sci.objectives.science_coverage_pct}% Coverage)",
        "tradeoff_summary": (
            f"Achieves highest objective coverage of {max_sci.objectives.science_coverage_pct}% across "
            f"{max_sci.objectives.sortie_count} sorties ({max_sci.objectives.total_distance_m:.0f}m traverse) "
            f"over a modeled total duration of {max_sci.objectives.total_duration_s/3600:.1f}h."
        ),
        "selection_rationale": "Recommended when primary mission priority is exhaustive scientific return.",
    }
    recommendations.append(rec_max_sci)

    # 2. Minimal Duration / Fast Reconnaissance Frontier Candidate
    min_dur = min(pareto_candidates, key=lambda c: c.objectives.total_duration_s)
    if min_dur.candidate_id != max_sci.candidate_id:
        dur_savings_s = max_sci.objectives.total_duration_s - min_dur.objectives.total_duration_s
        cov_delta = max_sci.objectives.science_coverage_pct - min_dur.objectives.science_coverage_pct
        rec_min_dur = {
            "recommendation_id": f"rec_ds_{uuid.uuid4().hex[:6]}",
            "candidate_id": min_dur.candidate_id,
            "headline": f"Expedited Campaign Duration ({min_dur.objectives.total_duration_s/3600:.1f}h Total)",
            "tradeoff_summary": (
                f"Saves {dur_savings_s/3600:.1f}h of surface operational time relative to maximal science, "
                f"while retaining {min_dur.objectives.science_coverage_pct}% science coverage "
                f"(-{cov_delta:.1f}% reduction in coverage)."
            ),
            "selection_rationale": "Recommended when crew fatigue, dust storm approach, or life support margins require minimal surface exposure.",
        }
        recommendations.append(rec_min_dur)

    # 3. Minimum Distance Frontier Candidate (if distinct)
    min_dist = min(pareto_candidates, key=lambda c: c.objectives.total_distance_m)
    if min_dist.candidate_id not in (max_sci.candidate_id, min_dur.candidate_id):
        rec_min_dist = {
            "recommendation_id": f"rec_ds_{uuid.uuid4().hex[:6]}",
            "candidate_id": min_dist.candidate_id,
            "headline": f"Minimal Surface Mobility Distance ({min_dist.objectives.total_distance_m:.0f}m)",
            "tradeoff_summary": (
                f"Reduces mechanical wheel wear and terrain risk with {min_dist.objectives.total_distance_m:.0f}m total distance "
                f"and {min_dist.objectives.science_coverage_pct}% science coverage."
            ),
            "selection_rationale": "Recommended for conservative mobility profiles or degraded locomotion hardware.",
        }
        recommendations.append(rec_min_dist)

    # Populate tradeoff_explanation on each pareto candidate
    for cand in pareto_candidates:
        dur_h = cand.objectives.total_duration_s / 3600.0
        dist_km = cand.objectives.total_distance_m / 1000.0
        cand.tradeoff_explanation = (
            f"Pareto frontier candidate with {cand.objectives.science_coverage_pct}% science coverage, "
            f"{dur_h:.1f}h duration, and {dist_km:.2f}km distance across {cand.objectives.sortie_count} sorties. "
            f"Not dominated by any alternative."
        )

    # Populate tradeoff_explanation on dominated candidates
    for cand in dominated_candidates:
        dom_refs = ", ".join(cand.dominated_by[:3])
        cand.tradeoff_explanation = f"Dominated by superior alternative(s): {dom_refs}."

    return recommendations


def explore_campaign_design_space(
    campaign: Union[MissionCampaign, Dict[str, Any]],
    terrain: TerrainGrid,
    transform: Optional[rasterio.Affine] = None,
    search_dimensions: Optional[Dict[str, Any]] = None,
    search_bounds: Optional[Union[SearchBounds, Dict[str, Any]]] = None,
    design_space_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes a bounded Campaign Design Space exploration:
    1. Generates bounded candidate configurations with input fingerprint deduplication.
    2. Evaluates candidates through authentic campaign planning across Jezero terrain.
    3. Performs pure mathematical multi-objective Pareto dominance classification.
    4. Generates grounded trade-off rationales and recommendations.
    5. Normalizes into Draft 2020-12 valid schema structure.
    """
    if isinstance(campaign, dict):
        base_campaign = MissionCampaign.from_dict(campaign)
    else:
        base_campaign = campaign

    if isinstance(search_bounds, dict):
        bounds_obj = SearchBounds(
            max_candidates=int(search_bounds.get("max_candidates", 12)),
            max_planner_calls=int(search_bounds.get("max_planner_calls", 15)),
        )
    elif isinstance(search_bounds, SearchBounds):
        bounds_obj = search_bounds
    else:
        bounds_obj = SearchBounds()

    # 1. Generate candidate configurations
    candidate_configs, completeness = generate_candidate_configurations(
        baseline_config=base_campaign.config.to_dict(),
        search_dimensions=search_dimensions,
        search_bounds=bounds_obj,
    )

    # 2. Evaluate candidates
    evaluations: List[CandidateEvaluation] = []
    planner_calls = 0

    for idx, cfg in enumerate(candidate_configs, start=1):
        if planner_calls >= bounds_obj.max_planner_calls:
            completeness.limit_reached = True
            completeness.unexplored_scope_notes = f"Reached maximum planner call limit of {bounds_obj.max_planner_calls}."
            break

        cand_eval = evaluate_candidate_configuration(
            candidate_idx=idx,
            candidate_config=cfg,
            baseline_campaign=base_campaign,
            terrain=terrain,
            transform=transform,
        )
        evaluations.append(cand_eval)
        planner_calls += 1

    completeness.candidates_evaluated = len(evaluations)
    completeness.candidates_rejected = sum(1 for e in evaluations if e.status != CandidateStatus.FEASIBLE.value)

    # 3. Classify Pareto Frontier
    pareto, dominated, infeasible = classify_pareto_frontier(evaluations)

    # 4. Generate grounded trade-off recommendations
    recommendations = build_tradeoff_explanations(pareto, dominated)

    ds_id = design_space_id or f"ds_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    result = {
        "schema_version": SCHEMA_VERSION,
        "design_space_id": ds_id,
        "campaign_id": base_campaign.campaign_id,
        "campaign_version": int(base_campaign.version),
        "created_at_utc": now_iso,
        "search_bounds": bounds_obj.to_dict(),
        "search_completeness": completeness.to_dict(),
        "pareto_candidates": [c.to_dict() for c in pareto],
        "dominated_candidates": [c.to_dict() for c in dominated],
        "infeasible_candidates": [c.to_dict() for c in infeasible],
        "recommendations": recommendations,
        "limitations_disclaimer": DESIGN_SPACE_DISCLAIMER,
    }

    clean_result = sanitize_for_json(result)
    validate_campaign_design_space_record(clean_result)
    return clean_result
