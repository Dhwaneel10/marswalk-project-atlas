"""
MarsWalk 2.0 / Project Atlas — Milestone 13K Plan Quality Evaluator & Pareto Analyzer
====================================================================================
Evaluates synthesized multi-rover mission candidates across 6 normalized physical
performance dimensions: Science Utility, Mobility Efficiency, Battery Reserve Margin,
Communications Continuity, Storage Utilization Margin, and Duration Compression.
Computes non-dominated Pareto frontiers, pairwise trade-off matrices, and human-readable
engineering rationale.
"""

from dataclasses import dataclass, field
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.mission_intent import MissionIntent
from marswalk.core.mission_plan_solver import MissionPlanCandidate, MissionCompilationResult


@dataclass
class PlanEvaluationMetrics:
    """Normalized 6-dimensional performance evaluation for a mission candidate."""
    candidate_id: str
    posture: str
    science_utility_score: float        # 0.0 - 1.0
    mobility_efficiency_score: float     # 0.0 - 1.0 (utility / km)
    battery_reserve_score: float         # 0.0 - 1.0
    comms_continuity_score: float        # 0.0 - 1.0
    storage_margin_score: float          # 0.0 - 1.0
    duration_compression_score: float    # 0.0 - 1.0
    weighted_composite_score: float      # Weighted sum
    rank: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "posture": self.posture,
            "science_utility_score": round(self.science_utility_score, 3),
            "mobility_efficiency_score": round(self.mobility_efficiency_score, 3),
            "battery_reserve_score": round(self.battery_reserve_score, 3),
            "comms_continuity_score": round(self.comms_continuity_score, 3),
            "storage_margin_score": round(self.storage_margin_score, 3),
            "duration_compression_score": round(self.duration_compression_score, 3),
            "weighted_composite_score": round(self.weighted_composite_score, 3),
            "rank": self.rank,
        }


@dataclass
class CandidateComparisonMatrix:
    """Detailed side-by-side comparative analysis between two or more candidates."""
    base_candidate_id: str
    target_candidate_id: str
    utility_delta_pts: float
    distance_delta_m: float
    energy_delta_wh: float
    battery_reserve_delta_pct: float
    reachability_delta_pct: float
    duration_delta_hours: float
    relays_delta_count: int
    tradeoff_summary: str
    winning_dimensions: List[str]
    losing_dimensions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_candidate_id": self.base_candidate_id,
            "target_candidate_id": self.target_candidate_id,
            "utility_delta_pts": round(self.utility_delta_pts, 1),
            "distance_delta_m": round(self.distance_delta_m, 1),
            "energy_delta_wh": round(self.energy_delta_wh, 2),
            "battery_reserve_delta_pct": round(self.battery_reserve_delta_pct, 1),
            "reachability_delta_pct": round(self.reachability_delta_pct, 1),
            "duration_delta_hours": round(self.duration_delta_hours, 2),
            "relays_delta_count": self.relays_delta_count,
            "tradeoff_summary": self.tradeoff_summary,
            "winning_dimensions": self.winning_dimensions,
            "losing_dimensions": self.losing_dimensions,
        }


class MissionPlanEvaluator:
    """
    Evaluates, ranks, and compares synthesized candidate configurations.
    Enforces scientific explainability: every ranking decision is backed by
    traceable physical deltas and explicit objective weightings.
    """

    def evaluate_candidates(
        self,
        intent: MissionIntent,
        candidates: List[MissionPlanCandidate]
    ) -> List[PlanEvaluationMetrics]:
        """Evaluates and scores all candidates across the 6 normalized dimensions."""
        if not candidates:
            return []

        # Find normalization ceilings across candidate set
        max_utility = max((c.total_science_utility for c in candidates), default=1.0)
        max_dist_km = max((c.total_distance_m / 1000.0 for c in candidates), default=1.0)
        max_hours = max((c.total_duration_hours for c in candidates), default=1.0)

        # Efficiency: utility per km
        efficiencies = [
            (c.total_science_utility / max(0.1, c.total_distance_m / 1000.0))
            for c in candidates
        ]
        max_eff = max(efficiencies, default=1.0)

        weights = intent.preferences
        evaluations: List[PlanEvaluationMetrics] = []

        for idx, cand in enumerate(candidates):
            # 1. Science Utility
            s_sci = min(1.0, cand.total_science_utility / max(1.0, max_utility))

            # 2. Mobility Efficiency
            eff = cand.total_science_utility / max(0.1, cand.total_distance_m / 1000.0)
            s_mob = min(1.0, eff / max(1.0, max_eff))

            # 3. Battery Reserve Margin
            s_batt = min(1.0, cand.min_battery_reserve_pct / 100.0)

            # 4. Communications Continuity
            s_comms = min(1.0, cand.comms_reachability_pct / 100.0)

            # 5. Storage Margin (1.0 - peak utilization)
            s_store = max(0.0, 1.0 - (cand.peak_storage_utilization_pct / 100.0))

            # 6. Duration Compression (shorter = higher score)
            s_dur = max(0.0, 1.0 - (cand.total_duration_hours / max(1.0, max_hours * 1.2)))

            # Composite Score
            composite = (
                weights.weight_science_utility * s_sci +
                weights.weight_traverse_efficiency * s_mob +
                weights.weight_energy_conservation * s_batt +
                weights.weight_communications_continuity * s_comms +
                0.05 * s_store +
                weights.weight_duration_compression * s_dur
            )

            evaluations.append(PlanEvaluationMetrics(
                candidate_id=cand.candidate_id,
                posture=cand.posture,
                science_utility_score=s_sci,
                mobility_efficiency_score=s_mob,
                battery_reserve_score=s_batt,
                comms_continuity_score=s_comms,
                storage_margin_score=s_store,
                duration_compression_score=s_dur,
                weighted_composite_score=composite,
            ))

        # Rank candidates by composite score
        evaluations.sort(key=lambda m: m.weighted_composite_score, reverse=True)
        for rank, item in enumerate(evaluations, 1):
            item.rank = rank

        return evaluations

    def compare_candidates(
        self,
        base: MissionPlanCandidate,
        target: MissionPlanCandidate
    ) -> CandidateComparisonMatrix:
        """Computes a detailed quantitative trade-off delta between two candidate configurations."""
        u_delta = target.total_science_utility - base.total_science_utility
        d_delta = target.total_distance_m - base.total_distance_m
        e_delta = target.total_energy_wh - base.total_energy_wh
        b_delta = target.min_battery_reserve_pct - base.min_battery_reserve_pct
        r_delta = target.comms_reachability_pct - base.comms_reachability_pct
        dur_delta = target.total_duration_hours - base.total_duration_hours
        relay_delta = target.relays_deployed_count - base.relays_deployed_count

        winning: List[str] = []
        losing: List[str] = []

        if u_delta > 0:
            winning.append(f"+{u_delta:.0f} Science Utility Pts")
        elif u_delta < 0:
            losing.append(f"{u_delta:.0f} Science Utility Pts")

        if b_delta > 0:
            winning.append(f"+{b_delta:.1f}% Battery Reserve")
        elif b_delta < 0:
            losing.append(f"{b_delta:.1f}% Battery Reserve")

        if r_delta > 0:
            winning.append(f"+{r_delta:.1f}% Geometric Reachability")
        elif r_delta < 0:
            losing.append(f"{r_delta:.1f}% Geometric Reachability")

        if dur_delta < 0:
            winning.append(f"{abs(dur_delta):.1f}h Faster Execution")
        elif dur_delta > 0:
            losing.append(f"+{dur_delta:.1f}h Longer Duration")

        summary = (
            f"Candidate '{target.name}' yields {abs(u_delta):.0f} {'more' if u_delta >= 0 else 'fewer'} science points "
            f"while requiring {abs(e_delta):.1f} Wh {'more' if e_delta >= 0 else 'less'} energy and "
            f"offering {target.min_battery_reserve_pct:.1f}% minimum battery reserve."
        )

        return CandidateComparisonMatrix(
            base_candidate_id=base.candidate_id,
            target_candidate_id=target.candidate_id,
            utility_delta_pts=u_delta,
            distance_delta_m=d_delta,
            energy_delta_wh=e_delta,
            battery_reserve_delta_pct=b_delta,
            reachability_delta_pct=r_delta,
            duration_delta_hours=dur_delta,
            relays_delta_count=relay_delta,
            tradeoff_summary=summary,
            winning_dimensions=winning,
            losing_dimensions=losing,
        )
