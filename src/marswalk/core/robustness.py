"""
MarsWalk 2.0 — Milestone 9X: Mission Robustness Lab, Sensitivity Analysis & Decision Stability.

Provides an authoritative, decision-grade robustness analysis engine answering:
- Does a selected mission remain feasible when operational assumptions change?
- How sensitive are its duration, distance, science return, and recommendation to those changes?
- Which targets or route segments cause a mission to become infeasible?
- Is another candidate more stable across the tested scenarios?
- At what tested budget, mobility level, or disruption size does the recommendation change?

CRITICAL SCIENTIFIC DISTINCTION:
Sensitivity analysis is NOT a probability forecast. Deterministic test cases must never be
described as measured probabilities, empirical likelihoods, or certified astronaut safety margins.
All ratios reflect proportions of EXPLICITLY TESTED cases.
"""

from dataclasses import dataclass, field
import enum
import hashlib
import json
import math
import time
from typing import Dict, List, Optional, Set, Tuple, Any, Union
import numpy as np
import rasterio

from marswalk.core.terrain import TerrainGrid, TerrainConfig
from marswalk.core.planner import (
    PlannerConfig,
    RouteResult,
    ScienceWaypoint,
    OPERATIONAL_LIMITS_S,
    plan_sequential_multistop_route,
    calculate_traverse_time,
    format_duration,
)
from marswalk.core.contingency import (
    compute_circular_footprint,
)


class SensitivityDimension(str, enum.Enum):
    """Supported deterministic sensitivity dimensions."""
    BUDGET = "operational_budget"
    MOBILITY = "mobility_multiplier"
    CORRIDOR_CLOSURE = "corridor_closure"
    TARGET_LOSS = "target_loss"
    TERRAIN_COST = "terrain_cost"
    COMPOUND = "compound"


@dataclass
class RobustnessTestCase:
    """
    Explicit specification for a single deterministic robustness test scenario.
    """
    case_id: str
    dimension: SensitivityDimension
    description: str
    parameter_name: str
    parameter_value: Any
    budget_limit_s: Optional[float] = None
    speed_multiplier: float = 1.0
    closure_center_rc: Optional[Tuple[int, int]] = None
    closure_radius_m: Optional[float] = None
    dropped_stop_ids: Optional[List[str]] = None
    cost_multiplier: float = 1.0
    operational_delay_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "dimension": self.dimension.value,
            "description": self.description,
            "parameter_name": self.parameter_name,
            "parameter_value": self.parameter_value,
            "budget_limit_s": self.budget_limit_s,
            "speed_multiplier": self.speed_multiplier,
            "closure_center_rc": list(self.closure_center_rc) if self.closure_center_rc else None,
            "closure_radius_m": self.closure_radius_m,
            "dropped_stop_ids": self.dropped_stop_ids,
            "cost_multiplier": self.cost_multiplier,
            "operational_delay_s": self.operational_delay_s,
        }


@dataclass
class CaseEvaluationResult:
    """
    Evaluated result of a single mission under a specific test case.
    """
    case_id: str
    dimension: str
    parameter_name: str
    parameter_value: Any
    description: str
    is_reachable: bool
    is_budget_feasible: bool
    is_feasible: bool
    distance_m: float
    travel_time_s: float
    total_mission_time_s: float
    remaining_margin_s: float
    science_score: float
    active_stop_ids: List[str]
    num_stops: int
    geometry_changed: bool
    explanation: str
    formatted_mission_time: str = "—"
    formatted_margin: str = "—"
    path_rc: Optional[List[Tuple[int, int]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "dimension": self.dimension,
            "parameter_name": self.parameter_name,
            "parameter_value": self.parameter_value,
            "description": self.description,
            "is_reachable": self.is_reachable,
            "is_budget_feasible": self.is_budget_feasible,
            "is_feasible": self.is_feasible,
            "distance_m": round(self.distance_m, 1),
            "travel_time_s": round(self.travel_time_s, 1),
            "total_mission_time_s": round(self.total_mission_time_s, 1),
            "remaining_margin_s": round(self.remaining_margin_s, 1),
            "science_score": round(self.science_score, 1),
            "active_stop_ids": self.active_stop_ids,
            "num_stops": self.num_stops,
            "geometry_changed": self.geometry_changed,
            "explanation": self.explanation,
            "formatted_mission_time": self.formatted_mission_time,
            "formatted_margin": self.formatted_margin,
            "path_rc": [list(pt) for pt in (self.path_rc or [])],
        }


@dataclass
class BreakpointReport:
    """
    Identified parameter transition or threshold detected from the discrete test cases.
    """
    dimension: str
    parameter_name: str
    description: str
    breakpoint_value: Any
    tested_resolution: str
    status_before: str
    status_after: str
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "parameter_name": self.parameter_name,
            "description": self.description,
            "breakpoint_value": self.breakpoint_value,
            "tested_resolution": self.tested_resolution,
            "status_before": self.status_before,
            "status_after": self.status_after,
            "explanation": self.explanation,
        }


@dataclass
class CandidateRobustnessMetrics:
    """
    Aggregated robustness, sensitivity, and stability metrics for an individual candidate.
    """
    candidate_id: str
    candidate_title: str
    nominal_science_score: float
    nominal_distance_m: float
    nominal_duration_s: float
    nominal_feasible: bool
    cases_tested: int
    feasible_cases_count: int
    feasible_ratio: float
    reachable_cases_count: int
    reachable_ratio: float
    min_margin_s: float
    duration_range_s: Tuple[float, float]
    distance_range_m: Tuple[float, float]
    science_range: Tuple[float, float]
    decision_stable_count: int
    decision_stable_ratio: float
    breakpoints: List[BreakpointReport]
    case_results: List[CaseEvaluationResult]
    explanations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_title": self.candidate_title,
            "nominal_science_score": round(self.nominal_science_score, 1),
            "nominal_distance_m": round(self.nominal_distance_m, 1),
            "nominal_duration_s": round(self.nominal_duration_s, 1),
            "nominal_feasible": self.nominal_feasible,
            "cases_tested": self.cases_tested,
            "feasible_cases_count": self.feasible_cases_count,
            "feasible_ratio": round(self.feasible_ratio, 3),
            "feasible_pct": round(self.feasible_ratio * 100.0, 1),
            "reachable_cases_count": self.reachable_cases_count,
            "reachable_ratio": round(self.reachable_ratio, 3),
            "reachable_pct": round(self.reachable_ratio * 100.0, 1),
            "min_margin_s": round(self.min_margin_s, 1),
            "duration_range_s": [round(self.duration_range_s[0], 1), round(self.duration_range_s[1], 1)],
            "distance_range_m": [round(self.distance_range_m[0], 1), round(self.distance_range_m[1], 1)],
            "science_range": [round(self.science_range[0], 1), round(self.science_range[1], 1)],
            "decision_stable_count": self.decision_stable_count,
            "decision_stable_ratio": round(self.decision_stable_ratio, 3),
            "decision_stable_pct": round(self.decision_stable_ratio * 100.0, 1),
            "breakpoints": [b.to_dict() for b in self.breakpoints],
            "case_results": [r.to_dict() for r in self.case_results],
            "explanations": self.explanations,
        }


@dataclass
class RobustnessAnalysisResult:
    """
    Complete response payload for the Mission Robustness Lab.
    """
    status: str
    schema_version: str
    computation_fingerprint: str
    evaluated_mission_id: str
    evaluated_mission_title: str
    baseline_mission: Dict[str, Any]
    primary_evaluation: CandidateRobustnessMetrics
    candidate_comparisons: List[CandidateRobustnessMetrics]
    tested_dimensions: List[str]
    total_evaluations: int
    execution_time_ms: float
    disclosures: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "schema_version": self.schema_version,
            "computation_fingerprint": self.computation_fingerprint,
            "evaluated_mission_id": self.evaluated_mission_id,
            "evaluated_mission_title": self.evaluated_mission_title,
            "baseline_mission": self.baseline_mission,
            "primary_evaluation": self.primary_evaluation.to_dict(),
            "candidate_comparisons": [c.to_dict() for c in self.candidate_comparisons],
            "tested_dimensions": self.tested_dimensions,
            "total_evaluations": self.total_evaluations,
            "execution_time_ms": round(self.execution_time_ms, 1),
            "disclosures": self.disclosures,
        }


def _build_default_test_cases(
    nominal_budget_s: float,
    nominal_speed_multiplier: float,
    nominal_path: List[Tuple[int, int]],
    stops: List[ScienceWaypoint],
    terrain: TerrainGrid,
) -> List[RobustnessTestCase]:
    """
    Construct a deterministic default matrix of test cases covering all primary dimensions.
    """
    cases: List[RobustnessTestCase] = []

    # 1. Operational Budget Variations (Tight, Moderate, Nominal, Extended)
    budget_factors = [0.5, 0.75, 1.0, 1.25]
    for factor in budget_factors:
        test_budget = round(nominal_budget_s * factor, 1)
        cases.append(RobustnessTestCase(
            case_id=f"budget_{int(factor*100)}pct",
            dimension=SensitivityDimension.BUDGET,
            description=f"Operational budget scaled to {int(factor*100)}% ({test_budget/3600.0:.2f} h)",
            parameter_name="budget_limit_s",
            parameter_value=test_budget,
            budget_limit_s=test_budget,
            speed_multiplier=nominal_speed_multiplier,
        ))

    # 2. Mobility Multipliers (Severe derating 0.5x, Moderate 0.75x, Nominal 1.0x, High 1.25x)
    mobility_factors = [0.5, 0.75, 1.0, 1.25]
    for mult in mobility_factors:
        cases.append(RobustnessTestCase(
            case_id=f"mobility_{int(mult*100)}pct",
            dimension=SensitivityDimension.MOBILITY,
            description=f"Vehicle mobility speed derated to {mult:.2f}x nominal velocity",
            parameter_name="speed_multiplier",
            parameter_value=mult,
            budget_limit_s=nominal_budget_s,
            speed_multiplier=mult,
        ))

    # 3. Corridor Closures:
    # A) Intersecting closure (placed on the midpoint of nominal path if available)
    if nominal_path and len(nominal_path) > 4:
        mid_idx = len(nominal_path) // 2
        intersect_pt = nominal_path[mid_idx]
        cases.append(RobustnessTestCase(
            case_id="closure_intersect_60m",
            dimension=SensitivityDimension.CORRIDOR_CLOSURE,
            description=f"Corridor rockfall closure (radius 60 m) intersecting route at pixel {intersect_pt}",
            parameter_name="closure_radius_m",
            parameter_value=60.0,
            budget_limit_s=nominal_budget_s,
            speed_multiplier=nominal_speed_multiplier,
            closure_center_rc=intersect_pt,
            closure_radius_m=60.0,
        ))

    # B) Non-intersecting closure (placed safely offset from nominal route)
    # Pick a point away from nominal path
    path_set = set(nominal_path) if nominal_path else set()
    offset_pt: Optional[Tuple[int, int]] = None
    for r in [20, 230, 20, 230, 125]:
        for c in [20, 20, 230, 230, 125]:
            if (r, c) not in path_set:
                # check min distance to path
                min_d = min(math.hypot(r - pr, c - pc) for pr, pc in nominal_path) if nominal_path else 100
                if min_d > 20:
                    offset_pt = (r, c)
                    break
        if offset_pt:
            break
    if offset_pt is None:
        offset_pt = (10, 10)

    cases.append(RobustnessTestCase(
        case_id="closure_external_50m",
        dimension=SensitivityDimension.CORRIDOR_CLOSURE,
        description=f"Corridor rockfall closure (radius 50 m) at external pixel {offset_pt} outside route corridor",
        parameter_name="closure_radius_m",
        parameter_value=50.0,
        budget_limit_s=nominal_budget_s,
        speed_multiplier=nominal_speed_multiplier,
        closure_center_rc=offset_pt,
        closure_radius_m=50.0,
    ))

    # 4. Target Loss (drop each intermediate stop individually)
    for stop in stops:
        cases.append(RobustnessTestCase(
            case_id=f"target_loss_{stop.id}",
            dimension=SensitivityDimension.TARGET_LOSS,
            description=f"Target '{stop.name}' ({stop.id}) unavailable due to scientific access failure",
            parameter_name="dropped_stop_id",
            parameter_value=stop.id,
            budget_limit_s=nominal_budget_s,
            speed_multiplier=nominal_speed_multiplier,
            dropped_stop_ids=[stop.id],
        ))

    # 5. Compound Disruption (Mobility derating 0.75x + 30-min operational hold)
    cases.append(RobustnessTestCase(
        case_id="compound_mobility_and_hold",
        dimension=SensitivityDimension.COMPOUND,
        description="Compound disruption: 0.75x vehicle mobility derating with 30-min operational hold delay",
        parameter_name="compound_derate_hold",
        parameter_value={"speed_multiplier": 0.75, "operational_delay_s": 1800.0},
        budget_limit_s=nominal_budget_s,
        speed_multiplier=0.75,
        operational_delay_s=1800.0,
    ))

    return cases


def _evaluate_single_case(
    case: RobustnessTestCase,
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    stops: List[ScienceWaypoint],
    nominal_path: List[Tuple[int, int]],
    nominal_dist_m: float,
    nominal_travel_time_s: float,
    nominal_dwell_time_s: float,
    terrain: TerrainGrid,
    profile: str,
    vehicle_mode: str,
    dwell_time_per_stop_s: float,
    nominal_budget_s: float,
    max_distance_m: Optional[float] = None,
) -> CaseEvaluationResult:
    """
    Authoritatively evaluate a single test case for an ordered multi-stop sortie.
    """
    effective_budget = case.budget_limit_s if case.budget_limit_s is not None else nominal_budget_s
    effective_speed_mult = case.speed_multiplier if case.speed_multiplier > 0 else 1.0
    effective_delay = case.operational_delay_s

    # Filter out dropped targets
    active_stops = [s for s in stops if case.dropped_stop_ids is None or s.id not in case.dropped_stop_ids]
    science_score = sum(s.priority_score for s in active_stops)
    active_stop_ids = [s.id for s in active_stops]

    # Check if this case is purely a budget variation
    is_pure_budget = (
        case.dimension == SensitivityDimension.BUDGET
        and effective_speed_mult == 1.0
        and case.closure_center_rc is None
        and not case.dropped_stop_ids
        and effective_delay == 0.0
        and len(active_stops) == len(stops)
    )

    # Check if this case is purely a uniform mobility variation
    is_pure_mobility = (
        case.dimension == SensitivityDimension.MOBILITY
        and case.closure_center_rc is None
        and not case.dropped_stop_ids
        and effective_delay == 0.0
        and len(active_stops) == len(stops)
    )

    # Fast-path for pure budget change: route geometry, distance, and traversal time are identical!
    if is_pure_budget:
        total_time = nominal_travel_time_s + nominal_dwell_time_s
        margin = effective_budget - total_time
        is_feasible = margin >= 0.0
        explanation = (
            f"Budget modified to {effective_budget/3600.0:.2f} h. Route geometry and distance invariant "
            f"({nominal_dist_m:.1f} m). Operational margin: {margin/60.0:+.1f} min."
        )
        return CaseEvaluationResult(
            case_id=case.case_id,
            dimension=case.dimension.value,
            parameter_name=case.parameter_name,
            parameter_value=case.parameter_value,
            description=case.description,
            is_reachable=True,
            is_budget_feasible=is_feasible,
            is_feasible=is_feasible,
            distance_m=nominal_dist_m,
            travel_time_s=nominal_travel_time_s,
            total_mission_time_s=total_time,
            remaining_margin_s=margin,
            science_score=science_score,
            active_stop_ids=active_stop_ids,
            num_stops=len(active_stops),
            geometry_changed=False,
            explanation=explanation,
            formatted_mission_time=format_duration(total_time),
            formatted_margin=f"{margin/60.0:+.1f} min",
            path_rc=nominal_path,
        )

    # Fast-path for pure uniform mobility change: route geometry and distance invariant!
    if is_pure_mobility:
        scaled_travel_time = nominal_travel_time_s / effective_speed_mult
        total_time = scaled_travel_time + nominal_dwell_time_s
        margin = effective_budget - total_time
        is_feasible = margin >= 0.0
        explanation = (
            f"Mobility derated to {effective_speed_mult:.2f}x. Route geometry invariant "
            f"({nominal_dist_m:.1f} m). Travel time scaled to {format_duration(scaled_travel_time)}. "
            f"Margin: {margin/60.0:+.1f} min."
        )
        return CaseEvaluationResult(
            case_id=case.case_id,
            dimension=case.dimension.value,
            parameter_name=case.parameter_name,
            parameter_value=case.parameter_value,
            description=case.description,
            is_reachable=True,
            is_budget_feasible=is_feasible,
            is_feasible=is_feasible,
            distance_m=nominal_dist_m,
            travel_time_s=scaled_travel_time,
            total_mission_time_s=total_time,
            remaining_margin_s=margin,
            science_score=science_score,
            active_stop_ids=active_stop_ids,
            num_stops=len(active_stops),
            geometry_changed=False,
            explanation=explanation,
            formatted_mission_time=format_duration(total_time),
            formatted_margin=f"{margin/60.0:+.1f} min",
            path_rc=nominal_path,
        )

    # Handle Corridor Closure: Check if closure footprint intersects nominal route
    blocked_mask: Optional[np.ndarray] = None
    closure_intersects = False
    if case.closure_center_rc is not None and case.closure_radius_m is not None:
        try:
            footprint_cells = compute_circular_footprint(
                center_rc=case.closure_center_rc,
                radius_m=case.closure_radius_m,
                terrain=terrain,
            )
            footprint_set = set(footprint_cells)
            nominal_set = set(nominal_path) if nominal_path else set()
            intersection = footprint_set.intersection(nominal_set)

            if not intersection and len(active_stops) == len(stops) and effective_speed_mult == 1.0 and effective_delay == 0.0:
                # Closure is completely outside the path and no other changes!
                total_time = nominal_travel_time_s + nominal_dwell_time_s
                margin = effective_budget - total_time
                is_feasible = margin >= 0.0
                explanation = (
                    f"Closure at {case.closure_center_rc} (radius {case.closure_radius_m:.0f} m) does not intersect "
                    f"the planned route corridor. Route geometry and timeline unaffected."
                )
                return CaseEvaluationResult(
                    case_id=case.case_id,
                    dimension=case.dimension.value,
                    parameter_name=case.parameter_name,
                    parameter_value=case.parameter_value,
                    description=case.description,
                    is_reachable=True,
                    is_budget_feasible=is_feasible,
                    is_feasible=is_feasible,
                    distance_m=nominal_dist_m,
                    travel_time_s=nominal_travel_time_s,
                    total_mission_time_s=total_time,
                    remaining_margin_s=margin,
                    science_score=science_score,
                    active_stop_ids=active_stop_ids,
                    num_stops=len(active_stops),
                    geometry_changed=False,
                    explanation=explanation,
                    formatted_mission_time=format_duration(total_time),
                    formatted_margin=f"{margin/60.0:+.1f} min",
                    path_rc=nominal_path,
                )

            closure_intersects = bool(intersection)
            blocked_mask = np.zeros(terrain.elevation.shape, dtype=bool)
            for r, c in footprint_cells:
                if 0 <= r < terrain.elevation.shape[0] and 0 <= c < terrain.elevation.shape[1]:
                    blocked_mask[r, c] = True
        except Exception:
            blocked_mask = None

    # Recalculate route through authoritative sequential A* planner
    ordered_points = [start_rc] + [s.rc for s in active_stops] + [goal_rc]
    stop_ids_list = [s.id for s in active_stops]
    stop_priorities_list = [s.priority_score for s in active_stops]

    p_cfg = PlannerConfig(profile=profile, max_distance_m=max_distance_m)

    route_res = plan_sequential_multistop_route(
        ordered_points=ordered_points,
        terrain=terrain,
        stop_ids=stop_ids_list,
        stop_priorities=stop_priorities_list,
        config=p_cfg,
        blocked_mask=blocked_mask,
        vehicle_mode=vehicle_mode,
        dwell_time_per_stop_s=dwell_time_per_stop_s,
        operational_delay_s=effective_delay,
        operational_limit_s=effective_budget,
        speed_multiplier=effective_speed_mult,
    )

    is_reach = route_res.is_reachable and len(route_res.path) >= 2
    geom_changed = (route_res.path != nominal_path)

    if not is_reach:
        return CaseEvaluationResult(
            case_id=case.case_id,
            dimension=case.dimension.value,
            parameter_name=case.parameter_name,
            parameter_value=case.parameter_value,
            description=case.description,
            is_reachable=False,
            is_budget_feasible=False,
            is_feasible=False,
            distance_m=0.0,
            travel_time_s=float("inf"),
            total_mission_time_s=float("inf"),
            remaining_margin_s=-float("inf"),
            science_score=0.0,
            active_stop_ids=[],
            num_stops=0,
            geometry_changed=True,
            explanation="Route is unreachable under tested disruption constraints (corridor severed).",
            formatted_mission_time="UNREACHABLE",
            formatted_margin="—",
            path_rc=[],
        )

    tl = route_res.timeline
    trav_s = tl.total_traverse_time_s if tl else route_res.travel_time_s
    tot_s = tl.total_mission_time_s if tl else trav_s
    margin_s = tl.remaining_margin_s if tl else (effective_budget - tot_s)
    budget_ok = tl.is_within_limit if tl else (margin_s >= 0.0)

    # Compose truthful explanation
    if case.dimension == SensitivityDimension.TARGET_LOSS:
        lost_names = [s.name for s in stops if case.dropped_stop_ids and s.id in case.dropped_stop_ids]
        lost_score = sum(s.priority_score for s in stops if case.dropped_stop_ids and s.id in case.dropped_stop_ids)
        explanation = (
            f"Target {lost_names} unavailable. Science score reduced by -{lost_score:.1f} pts "
            f"(now {science_score:.1f} pts). Route distance: {route_res.distance_m:.1f} m."
        )
    elif case.dimension == SensitivityDimension.CORRIDOR_CLOSURE:
        delta_d = route_res.distance_m - nominal_dist_m
        explanation = (
            f"Closure intersected route corridor; forced detour of {delta_d:+.1f} m. "
            f"Total distance: {route_res.distance_m:.1f} m, mission duration: {format_duration(tot_s)}."
        )
    elif case.dimension == SensitivityDimension.COMPOUND:
        explanation = (
            f"Compound derating ({effective_speed_mult}x) and hold delay ({effective_delay/60.0:.0f}m) evaluated. "
            f"Total duration: {format_duration(tot_s)}, remaining margin: {margin_s/60.0:+.1f} min."
        )
    else:
        explanation = f"Evaluated under {case.description}. Feasible: {budget_ok}."

    return CaseEvaluationResult(
        case_id=case.case_id,
        dimension=case.dimension.value,
        parameter_name=case.parameter_name,
        parameter_value=case.parameter_value,
        description=case.description,
        is_reachable=True,
        is_budget_feasible=budget_ok,
        is_feasible=budget_ok,
        distance_m=route_res.distance_m,
        travel_time_s=trav_s,
        total_mission_time_s=tot_s,
        remaining_margin_s=margin_s,
        science_score=science_score,
        active_stop_ids=active_stop_ids,
        num_stops=len(active_stops),
        geometry_changed=geom_changed,
        explanation=explanation,
        formatted_mission_time=format_duration(tot_s),
        formatted_margin=f"{margin_s/60.0:+.1f} min",
        path_rc=route_res.path,
    )


def _detect_breakpoints(
    results: List[CaseEvaluationResult],
    cases: List[RobustnessTestCase],
) -> List[BreakpointReport]:
    """
    Identify reproducible parameter transitions from discrete test results.
    """
    breakpoints: List[BreakpointReport] = []
    res_map = {r.case_id: r for r in results}

    # 1. Budget Breakpoint: Sort budget cases ascending
    budget_cases = [c for c in cases if c.dimension == SensitivityDimension.BUDGET and c.budget_limit_s is not None]
    if len(budget_cases) >= 2:
        budget_cases.sort(key=lambda c: c.budget_limit_s)
        for i in range(len(budget_cases) - 1):
            c_curr = budget_cases[i]
            c_next = budget_cases[i + 1]
            r_curr = res_map.get(c_curr.case_id)
            r_next = res_map.get(c_next.case_id)
            if r_curr and r_next:
                if not r_curr.is_feasible and r_next.is_feasible:
                    step_size = c_next.budget_limit_s - c_curr.budget_limit_s
                    breakpoints.append(BreakpointReport(
                        dimension=SensitivityDimension.BUDGET.value,
                        parameter_name="budget_limit_s",
                        description="Operational budget feasibility threshold",
                        breakpoint_value=c_next.budget_limit_s,
                        tested_resolution=f"Tested step resolution of {step_size/3600.0:.2f} h ({step_size:.0f} s)",
                        status_before=f"Infeasible at {c_curr.budget_limit_s/3600.0:.2f} h",
                        status_after=f"Feasible at {c_next.budget_limit_s/3600.0:.2f} h",
                        explanation=(
                            f"Mission exceeds allowable duration below {c_next.budget_limit_s/3600.0:.2f} h. "
                            f"Became feasible between {c_curr.budget_limit_s/3600.0:.2f} h and {c_next.budget_limit_s/3600.0:.2f} h."
                        ),
                    ))

    # 2. Mobility Breakpoint: Sort mobility cases ascending
    mobility_cases = [c for c in cases if c.dimension == SensitivityDimension.MOBILITY]
    if len(mobility_cases) >= 2:
        mobility_cases.sort(key=lambda c: c.speed_multiplier)
        for i in range(len(mobility_cases) - 1):
            c_curr = mobility_cases[i]
            c_next = mobility_cases[i + 1]
            r_curr = res_map.get(c_curr.case_id)
            r_next = res_map.get(c_next.case_id)
            if r_curr and r_next:
                if not r_curr.is_feasible and r_next.is_feasible:
                    step_size = c_next.speed_multiplier - c_curr.speed_multiplier
                    breakpoints.append(BreakpointReport(
                        dimension=SensitivityDimension.MOBILITY.value,
                        parameter_name="speed_multiplier",
                        description="Speed multiplier feasibility threshold",
                        breakpoint_value=c_next.speed_multiplier,
                        tested_resolution=f"Tested resolution of {step_size:.2f}x speed delta",
                        status_before=f"Infeasible at {c_curr.speed_multiplier:.2f}x",
                        status_after=f"Feasible at {c_next.speed_multiplier:.2f}x",
                        explanation=(
                            f"Speed derating below {c_next.speed_multiplier:.2f}x causes mission duration to exceed limit. "
                            f"Feasibility restored at {c_next.speed_multiplier:.2f}x multiplier."
                        ),
                    ))

    # 3. Corridor Closure impact
    closure_results = [r for r in results if r.dimension == SensitivityDimension.CORRIDOR_CLOSURE.value]
    for cr in closure_results:
        if not cr.is_reachable:
            breakpoints.append(BreakpointReport(
                dimension=SensitivityDimension.CORRIDOR_CLOSURE.value,
                parameter_name="closure_radius_m",
                description="Corridor unreachability severance",
                breakpoint_value=cr.parameter_value,
                tested_resolution="Discrete spatial footprint",
                status_before="Reachable",
                status_after="Unreachable (Severed)",
                explanation=f"Corridor closure {cr.case_id} completely blocked all viable traverse paths to destination.",
            ))
        elif cr.geometry_changed:
            breakpoints.append(BreakpointReport(
                dimension=SensitivityDimension.CORRIDOR_CLOSURE.value,
                parameter_name="closure_radius_m",
                description="Corridor detour boundary",
                breakpoint_value=cr.parameter_value,
                tested_resolution="Discrete spatial footprint",
                status_before="Nominal corridor",
                status_after="Detour required",
                explanation=f"Corridor closure {cr.case_id} intersected nominal path, forcing an A* detour of {cr.distance_m:.1f} m.",
            ))

    # 4. Target loss impacts
    target_results = [r for r in results if r.dimension == SensitivityDimension.TARGET_LOSS.value]
    for tr in target_results:
        if tr.geometry_changed:
            breakpoints.append(BreakpointReport(
                dimension=SensitivityDimension.TARGET_LOSS.value,
                parameter_name="dropped_stop_id",
                description=f"Science impact from dropping {tr.parameter_value}",
                breakpoint_value=tr.parameter_value,
                tested_resolution="Individual waypoint drop",
                status_before="Nominal stops",
                status_after=f"{tr.num_stops} surviving stops",
                explanation=tr.explanation,
            ))

    return breakpoints


def evaluate_mission_robustness(
    terrain: TerrainGrid,
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    stops: List[ScienceWaypoint],
    candidate_pool: Optional[List[ScienceWaypoint]] = None,
    profile: str = "balanced",
    vehicle_mode: str = "crew_eva",
    nominal_budget_s: float = 28800.0,
    nominal_speed_multiplier: float = 1.0,
    dwell_time_per_stop_s: float = 900.0,
    operational_delay_s: float = 0.0,
    max_distance_m: Optional[float] = None,
    sensitivity_spec: Optional[Dict[str, Any]] = None,
    comparison_candidates: Optional[List[Dict[str, Any]]] = None,
    mission_id: str = "active_mission",
    mission_title: str = "Active Mission Traverse",
    transform: Optional[rasterio.Affine] = None,
) -> RobustnessAnalysisResult:
    """
    Execute comprehensive robustness and sensitivity evaluation across tested operational variations.
    """
    start_time = time.perf_counter()

    # 1. Authoritative baseline route calculation
    ordered_points = [start_rc] + [s.rc for s in stops] + [goal_rc]
    stop_ids = [s.id for s in stops]
    stop_priorities = [s.priority_score for s in stops]

    p_cfg = PlannerConfig(profile=profile, max_distance_m=max_distance_m)

    baseline_res = plan_sequential_multistop_route(
        ordered_points=ordered_points,
        terrain=terrain,
        stop_ids=stop_ids,
        stop_priorities=stop_priorities,
        config=p_cfg,
        vehicle_mode=vehicle_mode,
        dwell_time_per_stop_s=dwell_time_per_stop_s,
        operational_delay_s=operational_delay_s,
        operational_limit_s=nominal_budget_s,
        speed_multiplier=nominal_speed_multiplier,
    )

    baseline_dist_m = baseline_res.distance_m
    baseline_trav_s = baseline_res.travel_time_s
    baseline_dwell_s = len(stops) * dwell_time_per_stop_s
    baseline_tot_s = baseline_trav_s + baseline_dwell_s + operational_delay_s
    baseline_science = sum(stop_priorities)
    baseline_feasible = baseline_res.is_reachable and (baseline_tot_s <= nominal_budget_s)

    baseline_summary = {
        "mission_id": mission_id,
        "title": mission_title,
        "start_rc": list(start_rc),
        "goal_rc": list(goal_rc),
        "stop_ids": stop_ids,
        "num_stops": len(stops),
        "distance_m": round(baseline_dist_m, 1),
        "travel_time_s": round(baseline_trav_s, 1),
        "total_mission_time_s": round(baseline_tot_s, 1),
        "operational_limit_s": round(nominal_budget_s, 1),
        "remaining_margin_s": round(nominal_budget_s - baseline_tot_s, 1),
        "science_score": round(baseline_science, 1),
        "is_feasible": baseline_feasible,
        "is_reachable": baseline_res.is_reachable,
        "formatted_mission_time": format_duration(baseline_tot_s),
        "path_cells_count": len(baseline_res.path),
    }

    # 2. Build or parse test cases
    test_cases: List[RobustnessTestCase] = []
    if sensitivity_spec and isinstance(sensitivity_spec, dict) and "custom_cases" in sensitivity_spec:
        for idx, c_dict in enumerate(sensitivity_spec["custom_cases"]):
            dim_str = c_dict.get("dimension", "operational_budget")
            try:
                dim_enum = SensitivityDimension(dim_str)
            except ValueError:
                dim_enum = SensitivityDimension.BUDGET
            test_cases.append(RobustnessTestCase(
                case_id=c_dict.get("case_id", f"case_{idx+1}"),
                dimension=dim_enum,
                description=c_dict.get("description", f"Custom test case {idx+1}"),
                parameter_name=c_dict.get("parameter_name", "param"),
                parameter_value=c_dict.get("parameter_value", 0.0),
                budget_limit_s=c_dict.get("budget_limit_s"),
                speed_multiplier=float(c_dict.get("speed_multiplier", 1.0)),
                closure_center_rc=tuple(c_dict["closure_center_rc"]) if c_dict.get("closure_center_rc") else None,
                closure_radius_m=float(c_dict.get("closure_radius_m", 50.0)) if c_dict.get("closure_radius_m") else None,
                dropped_stop_ids=c_dict.get("dropped_stop_ids"),
                cost_multiplier=float(c_dict.get("cost_multiplier", 1.0)),
                operational_delay_s=float(c_dict.get("operational_delay_s", 0.0)),
            ))
    elif sensitivity_spec and isinstance(sensitivity_spec, dict) and "budget_limits_s" in sensitivity_spec:
        # User specified explicit budget limits
        for b_val in sensitivity_spec["budget_limits_s"]:
            test_cases.append(RobustnessTestCase(
                case_id=f"budget_{int(b_val)}s",
                dimension=SensitivityDimension.BUDGET,
                description=f"Explicit budget test: {b_val/3600.0:.2f} h",
                parameter_name="budget_limit_s",
                parameter_value=float(b_val),
                budget_limit_s=float(b_val),
                speed_multiplier=nominal_speed_multiplier,
            ))
    else:
        test_cases = _build_default_test_cases(
            nominal_budget_s=nominal_budget_s,
            nominal_speed_multiplier=nominal_speed_multiplier,
            nominal_path=baseline_res.path,
            stops=stops,
            terrain=terrain,
        )

    # Limit maximum evaluations to 50
    if len(test_cases) > 50:
        test_cases = test_cases[:50]

    # 3. Evaluate primary candidate across test cases
    case_results: List[CaseEvaluationResult] = []
    for tc in test_cases:
        eval_res = _evaluate_single_case(
            case=tc,
            start_rc=start_rc,
            goal_rc=goal_rc,
            stops=stops,
            nominal_path=baseline_res.path,
            nominal_dist_m=baseline_dist_m,
            nominal_travel_time_s=baseline_trav_s,
            nominal_dwell_time_s=baseline_dwell_s,
            terrain=terrain,
            profile=profile,
            vehicle_mode=vehicle_mode,
            dwell_time_per_stop_s=dwell_time_per_stop_s,
            nominal_budget_s=nominal_budget_s,
            max_distance_m=max_distance_m,
        )
        case_results.append(eval_res)

    # 4. Compute primary aggregate robustness metrics
    n_tested = len(case_results)
    n_feasible = sum(1 for r in case_results if r.is_feasible)
    n_reachable = sum(1 for r in case_results if r.is_reachable)
    feas_ratio = (n_feasible / n_tested) if n_tested > 0 else 0.0
    reach_ratio = (n_reachable / n_tested) if n_tested > 0 else 0.0

    reachable_results = [r for r in case_results if r.is_reachable]
    if reachable_results:
        min_margin = min(r.remaining_margin_s for r in reachable_results)
        durations = [r.total_mission_time_s for r in reachable_results]
        distances = [r.distance_m for r in reachable_results]
        sciences = [r.science_score for r in reachable_results]
        dur_range = (min(durations), max(durations))
        dist_range = (min(distances), max(distances))
        sci_range = (min(sciences), max(sciences))
    else:
        min_margin = -float("inf")
        dur_range = (0.0, 0.0)
        dist_range = (0.0, 0.0)
        sci_range = (0.0, 0.0)

    # Decision stability: cases where feasibility outcome matches nominal
    stable_count = sum(1 for r in case_results if r.is_feasible == baseline_feasible)
    stable_ratio = (stable_count / n_tested) if n_tested > 0 else 0.0

    breakpoints = _detect_breakpoints(case_results, test_cases)

    # Candidate explanations
    explanations: List[str] = [
        f"Primary mission '{mission_title}' remained feasible in {n_feasible}/{n_tested} tested cases ({feas_ratio*100.0:.1f}%).",
        f"Reachable traverse paths exist in {n_reachable}/{n_tested} tested cases ({reach_ratio*100.0:.1f}%).",
    ]
    if min_margin < 0:
        explanations.append(f"Minimum operational margin dropped to {min_margin/60.0:.1f} min under tested severe limits.")
    else:
        explanations.append(f"Robust operational margin: minimum {min_margin/60.0:.1f} min across all tested cases.")

    primary_metrics = CandidateRobustnessMetrics(
        candidate_id=mission_id,
        candidate_title=mission_title,
        nominal_science_score=baseline_science,
        nominal_distance_m=baseline_dist_m,
        nominal_duration_s=baseline_tot_s,
        nominal_feasible=baseline_feasible,
        cases_tested=n_tested,
        feasible_cases_count=n_feasible,
        feasible_ratio=feas_ratio,
        reachable_cases_count=n_reachable,
        reachable_ratio=reach_ratio,
        min_margin_s=min_margin,
        duration_range_s=dur_range,
        distance_range_m=dist_range,
        science_range=sci_range,
        decision_stable_count=stable_count,
        decision_stable_ratio=stable_ratio,
        breakpoints=breakpoints,
        case_results=case_results,
        explanations=explanations,
    )

    # 5. Evaluate comparison candidates against identical test matrix
    candidate_reports: List[CandidateRobustnessMetrics] = []
    if comparison_candidates and isinstance(comparison_candidates, list):
        wp_catalogue = {w.id: w for w in (candidate_pool or [])}

        for cand_dict in comparison_candidates:
            c_id = cand_dict.get("id", "cand_alt")
            c_title = cand_dict.get("title", "Alternative Sortie")

            # Resolve stops
            c_stops: List[ScienceWaypoint] = []
            for s_id in cand_dict.get("stop_ids", []):
                if s_id in wp_catalogue:
                    c_stops.append(wp_catalogue[s_id])

            c_ordered = [start_rc] + [s.rc for s in c_stops] + [goal_rc]
            c_stop_ids = [s.id for s in c_stops]
            c_stop_priorities = [s.priority_score for s in c_stops]

            c_base = plan_sequential_multistop_route(
                ordered_points=c_ordered,
                terrain=terrain,
                stop_ids=c_stop_ids,
                stop_priorities=c_stop_priorities,
                config=p_cfg,
                vehicle_mode=vehicle_mode,
                dwell_time_per_stop_s=dwell_time_per_stop_s,
                operational_delay_s=operational_delay_s,
                operational_limit_s=nominal_budget_s,
                speed_multiplier=nominal_speed_multiplier,
            )

            c_dist = c_base.distance_m
            c_trav = c_base.travel_time_s
            c_dwell = len(c_stops) * dwell_time_per_stop_s
            c_tot = c_trav + c_dwell + operational_delay_s
            c_sci = sum(c_stop_priorities)
            c_feas = c_base.is_reachable and (c_tot <= nominal_budget_s)

            c_case_results: List[CaseEvaluationResult] = []
            for tc in test_cases:
                c_res = _evaluate_single_case(
                    case=tc,
                    start_rc=start_rc,
                    goal_rc=goal_rc,
                    stops=c_stops,
                    nominal_path=c_base.path,
                    nominal_dist_m=c_dist,
                    nominal_travel_time_s=c_trav,
                    nominal_dwell_time_s=c_dwell,
                    terrain=terrain,
                    profile=profile,
                    vehicle_mode=vehicle_mode,
                    dwell_time_per_stop_s=dwell_time_per_stop_s,
                    nominal_budget_s=nominal_budget_s,
                    max_distance_m=max_distance_m,
                )
                c_case_results.append(c_res)

            c_n_feas = sum(1 for r in c_case_results if r.is_feasible)
            c_n_reach = sum(1 for r in c_case_results if r.is_reachable)
            c_feas_rat = (c_n_feas / n_tested) if n_tested > 0 else 0.0
            c_reach_rat = (c_n_reach / n_tested) if n_tested > 0 else 0.0

            c_reach_results = [r for r in c_case_results if r.is_reachable]
            if c_reach_results:
                c_min_margin = min(r.remaining_margin_s for r in c_reach_results)
                c_durs = [r.total_mission_time_s for r in c_reach_results]
                c_dists = [r.distance_m for r in c_reach_results]
                c_scis = [r.science_score for r in c_reach_results]
                c_dur_range = (min(c_durs), max(c_durs))
                c_dist_range = (min(c_dists), max(c_dists))
                c_sci_range = (min(c_scis), max(c_scis))
            else:
                c_min_margin = -float("inf")
                c_dur_range = (0.0, 0.0)
                c_dist_range = (0.0, 0.0)
                c_sci_range = (0.0, 0.0)

            c_stable_cnt = sum(1 for r in c_case_results if r.is_feasible == c_feas)
            c_stable_rat = (c_stable_cnt / n_tested) if n_tested > 0 else 0.0
            c_breaks = _detect_breakpoints(c_case_results, test_cases)

            # Trade-off statement comparing with primary
            delta_sci = c_sci - baseline_science
            delta_feas = (c_feas_rat - feas_ratio) * 100.0
            tradeoff_text = (
                f"Candidate '{c_title}' achieves {c_n_feas}/{n_tested} feasible cases ({c_feas_rat*100.0:.1f}%, "
                f"{delta_feas:+.1f}% vs primary) with science score {c_sci:.1f} ({delta_sci:+.1f} pts vs primary)."
            )

            candidate_reports.append(CandidateRobustnessMetrics(
                candidate_id=c_id,
                candidate_title=c_title,
                nominal_science_score=c_sci,
                nominal_distance_m=c_dist,
                nominal_duration_s=c_tot,
                nominal_feasible=c_feas,
                cases_tested=n_tested,
                feasible_cases_count=c_n_feas,
                feasible_ratio=c_feas_rat,
                reachable_cases_count=c_n_reach,
                reachable_ratio=c_reach_rat,
                min_margin_s=c_min_margin,
                duration_range_s=c_dur_range,
                distance_range_m=c_dist_range,
                science_range=c_sci_range,
                decision_stable_count=c_stable_cnt,
                decision_stable_ratio=c_stable_rat,
                breakpoints=c_breaks,
                case_results=c_case_results,
                explanations=[tradeoff_text],
            ))

    # 6. Compute SHA-256 fingerprint for deterministic reproducibility
    raw_hash_input = {
        "start_rc": list(start_rc),
        "goal_rc": list(goal_rc),
        "stop_ids": stop_ids,
        "profile": profile,
        "vehicle_mode": vehicle_mode,
        "nominal_budget_s": nominal_budget_s,
        "test_cases_count": n_tested,
        "case_ids": [c.case_id for c in test_cases],
        "primary_feasible_count": n_feasible,
    }
    sha_str = hashlib.sha256(json.dumps(raw_hash_input, sort_keys=True).encode("utf-8")).hexdigest()

    dimensions_tested = list(dict.fromkeys(c.dimension.value for c in test_cases))
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    disclosures = [
        "SENSITIVITY ANALYSIS DISCLAIMER: Deterministic test results reflect the discrete tested cases only and are NOT statistical probabilities or empirical safety likelihoods.",
        "OPERATIONAL BOUNDARY: MarsWalk is an algorithmic research demonstrator. Modeled routes and feasibility assessments are NOT certified operational astronaut flight safety envelopes.",
        "TERRAIN DATASET: Calculations performed on USGS MRO CTX Digital Terrain Model of Jezero Crater Western Delta at 20 m/pixel geodetic resolution.",
    ]

    return RobustnessAnalysisResult(
        status="success",
        schema_version="1.0.0",
        computation_fingerprint=sha_str,
        evaluated_mission_id=mission_id,
        evaluated_mission_title=mission_title,
        baseline_mission=baseline_summary,
        primary_evaluation=primary_metrics,
        candidate_comparisons=candidate_reports,
        tested_dimensions=dimensions_tested,
        total_evaluations=n_tested * (1 + len(candidate_reports)),
        execution_time_ms=elapsed_ms,
        disclosures=disclosures,
    )
