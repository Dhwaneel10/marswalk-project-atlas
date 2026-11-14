"""
MarsWalk Core Science Budget & Pareto Frontier Engine.
Computes multi-objective Pareto trade-offs (physical distance, modeled terrain cost,
and scientific priority points) across candidate exploration plans, supporting sensitivity
analysis and Gauntlet stress-test comparisons.
"""

from dataclasses import dataclass, field
import json
import math
import time
from typing import Dict, List, Optional, Set, Tuple, Any

import numpy as np

from marswalk.core.terrain import TerrainConfig, TerrainGrid
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    RouteResult,
    compute_pairwise_leg_cache,
    stitch_path_legs,
    evaluate_balanced_utility,
)


@dataclass
class CandidatePlan:
    """
    Represents an evaluated candidate exploration traverse visiting a subset of scientific targets.

    Attributes
    ----------
    candidate_id : str
        Unique, deterministic identifier for this candidate plan.
    subset_key : str
        Sorted comma-separated waypoint IDs representing the subset.
    visited_waypoint_ids : List[str]
        Ordered sequence of waypoint IDs visited along the route.
    visited_waypoint_names : List[str]
        Ordered sequence of human-readable waypoint names visited.
    path : List[Tuple[int, int]]
        Ordered 8-connected grid coordinates from start to goal.
    distance_m : float
        Physical ground distance in meters.
    cost : float
        Modeled terrain cost (equivalent flat-terrain meters).
    science_score : float
        Sum of scientific priority points for visited waypoints.
    is_reachable : bool
        True if all legs are traversable and destination is reached.
    is_budget_feasible : bool
        True if physical distance <= max_distance_m (or no budget set).
    num_targets : int
        Number of scientific waypoints visited.
    profile_tag : Optional[str]
        Tagged profile if this candidate matches Conservative, Balanced, or Science-First.
    is_pareto_2d : bool
        True if non-dominated in 2D space (minimize distance, maximize science).
    is_pareto_3d : bool
        True if non-dominated in 3D space (minimize distance, minimize cost, maximize science).
    utility_score : Optional[float]
        Learned utility score from Mission Commander AI, if evaluated.
    """

    candidate_id: str
    subset_key: str
    visited_waypoint_ids: List[str]
    visited_waypoint_names: List[str]
    path: List[Tuple[int, int]]
    distance_m: float
    cost: float
    science_score: float
    is_reachable: bool
    is_budget_feasible: bool
    num_targets: int
    profile_tag: Optional[str] = None
    is_pareto_2d: bool = False
    is_pareto_3d: bool = False
    utility_score: Optional[float] = None

    @property
    def is_feasible(self) -> bool:
        """A candidate is feasible if and only if it is reachable and within budget."""
        return self.is_reachable and self.is_budget_feasible

    @property
    def utility(self) -> Optional[float]:
        """Alias for utility_score to provide backward-compatible attribute access."""
        return self.utility_score


@dataclass
class FrontierResult:
    """
    Structured outcome of the Science Budget Pareto frontier analysis.
    """

    candidates: List[CandidatePlan]
    pareto_candidates_2d: List[CandidatePlan]
    pareto_candidates_3d: List[CandidatePlan]
    dominated_candidates_2d: List[CandidatePlan]
    infeasible_candidates: List[CandidatePlan]
    recommended_plan: Optional[CandidatePlan]
    max_distance_m: Optional[float]
    total_subsets_evaluated: int
    execution_time_s: float = 0.0


def evaluate_all_candidate_plans(
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    terrain: TerrainGrid,
    waypoints: List[ScienceWaypoint],
    planner_config: Optional[PlannerConfig] = None,
    terrain_config: Optional[TerrainConfig] = None,
    blocked_mask: Optional[np.ndarray] = None,
    leg_cache: Optional[Dict[Tuple[Tuple[int, int], Tuple[int, int]], Any]] = None,
    active_profile_tags: Optional[Dict[str, List[str]]] = None,
) -> List[CandidatePlan]:
    """
    Evaluate all possible waypoint subset combinations and their optimal visit order.

    For up to 6 waypoints, this performs an exact evaluation of all 2^K subsets (up to 64),
    finding the minimum-cost permutation connecting start_rc -> subset -> goal_rc.

    Parameters
    ----------
    start_rc : Tuple[int, int]
        EVA start coordinate.
    goal_rc : Tuple[int, int]
        EVA goal coordinate.
    terrain : TerrainGrid
        Calibrated terrain elevation and physics matrices.
    waypoints : List[ScienceWaypoint]
        Candidate science waypoints (maximum 6).
    planner_config : Optional[PlannerConfig]
        Planner settings (contains max_distance_m, science_appetite_gamma).
    terrain_config : Optional[TerrainConfig]
        Terrain parameters override.
    blocked_mask : Optional[np.ndarray]
        Scenario blocked terrain mask (for stress-testing).
    leg_cache : Optional[Dict]
        Precomputed pairwise leg cache. Computed if None.
    active_profile_tags : Optional[Dict[str, List[str]]]
        Optional mapping of profile name ("conservative", "balanced", "science_first")
        to visited waypoint ID sequence, to tag corresponding candidates.

    Returns
    -------
    List[CandidatePlan] : List of evaluated candidate plans.
    """
    import itertools

    cfg = planner_config if planner_config is not None else PlannerConfig()
    t_cfg = terrain_config if terrain_config is not None else terrain.config
    wps = waypoints[: cfg.max_waypoints]
    max_budget = cfg.max_distance_m

    # Ensure leg cache is available
    if leg_cache is None:
        nodes = [start_rc] + [w.rc for w in wps] + [goal_rc]
        unique_nodes = list(dict.fromkeys(nodes))
        leg_cache = compute_pairwise_leg_cache(
            unique_nodes, terrain, terrain_config=t_cfg, blocked_mask=blocked_mask
        )

    wp_by_id = {w.id: w for w in wps}
    wp_by_rc = {w.rc: w for w in wps}

    # Helper to check matching profile tags
    tags_by_wps: Dict[Tuple[str, ...], List[str]] = {}
    if active_profile_tags:
        for prof_name, wp_seq in active_profile_tags.items():
            key = tuple(wp_seq)
            tags_by_wps.setdefault(key, []).append(prof_name)

    candidates: List[CandidatePlan] = []
    cand_counter = 0

    # Evaluate subsets from size 0 (direct conservative route) to len(wps)
    for r in range(len(wps) + 1):
        for subset in itertools.combinations(wps, r):
            cand_counter += 1
            subset_ids_sorted = sorted([w.id for w in subset])
            subset_key = ",".join(subset_ids_sorted) if subset_ids_sorted else "direct_traverse"
            subset_science = sum(w.priority_score for w in subset)

            best_path: List[Tuple[int, int]] = []
            best_cost = float("inf")
            best_dist = 0.0
            best_order_ids: List[str] = []
            best_order_names: List[str] = []
            is_reachable = False

            if not subset:
                # Direct route start -> goal
                leg = leg_cache.get((start_rc, goal_rc))
                if leg and leg.is_reachable and math.isfinite(leg.cost):
                    best_path = leg.path
                    best_cost = leg.cost
                    best_dist = leg.distance_m
                    is_reachable = True
            else:
                # Find minimum-cost TSP permutation for this subset
                for perm in itertools.permutations(subset):
                    perm_nodes = [start_rc] + [w.rc for w in perm] + [goal_rc]
                    stitched, dist_m, cost_val, ok = stitch_path_legs(perm_nodes, leg_cache)
                    if ok and cost_val < best_cost:
                        best_cost = cost_val
                        best_dist = dist_m
                        best_path = stitched
                        best_order_ids = [w.id for w in perm]
                        best_order_names = [w.name for w in perm]
                        is_reachable = True

            # Determine budget feasibility
            if not is_reachable:
                is_budget_ok = False
            elif max_budget is not None:
                is_budget_ok = (best_dist <= max_budget)
            else:
                is_budget_ok = True

            # Tag matching profiles
            prof_tag = None
            tag_key = tuple(best_order_ids)
            if tag_key in tags_by_wps:
                prof_tag = "/".join(tags_by_wps[tag_key])
            elif not subset and ((),) in tags_by_wps:
                prof_tag = "/".join(tags_by_wps[()])

            # Stable candidate ID
            cid = f"plan_{cand_counter:02d}_{subset_key[:20]}"

            candidates.append(
                CandidatePlan(
                    candidate_id=cid,
                    subset_key=subset_key,
                    visited_waypoint_ids=best_order_ids,
                    visited_waypoint_names=best_order_names,
                    path=best_path,
                    distance_m=best_dist,
                    cost=best_cost,
                    science_score=subset_science,
                    is_reachable=is_reachable,
                    is_budget_feasible=is_budget_ok,
                    num_targets=len(subset),
                    profile_tag=prof_tag,
                )
            )

    return candidates


def check_dominance_2d(
    cand_a: CandidatePlan, cand_b: CandidatePlan, tol: float = 1e-6
) -> bool:
    """
    Determine if Candidate A Pareto-dominates Candidate B in 2D objective space:
    - Objective 1: Minimize physical route distance (distance_m)
    - Objective 2: Maximize scientific priority points (science_score)

    Definition:
    A dominates B iff:
    1. A is feasible, AND (B is infeasible OR:
       dist(A) <= dist(B) + tol AND
       sci(A) >= sci(B) - tol AND
       (dist(A) < dist(B) - tol OR sci(A) > sci(B) + tol)
    )
    """
    if not cand_a.is_feasible:
        return False
    if not cand_b.is_feasible:
        # A feasible candidate strictly dominates any infeasible candidate
        return True

    a_dist = cand_a.distance_m
    b_dist = cand_b.distance_m
    a_sci = cand_a.science_score
    b_sci = cand_b.science_score

    at_least_as_good = (a_dist <= b_dist + tol) and (a_sci >= b_sci - tol)
    strictly_better = (a_dist < b_dist - tol) or (a_sci > b_sci + tol)

    return at_least_as_good and strictly_better


def check_dominance_3d(
    cand_a: CandidatePlan, cand_b: CandidatePlan, tol: float = 1e-6
) -> bool:
    """
    Determine if Candidate A Pareto-dominates Candidate B in 3D objective space:
    - Objective 1: Minimize physical route distance (distance_m)
    - Objective 2: Minimize modeled terrain cost (cost)
    - Objective 3: Maximize scientific priority points (science_score)

    Definition:
    A dominates B iff:
    1. A is feasible, AND (B is infeasible OR:
       dist(A) <= dist(B) + tol AND
       cost(A) <= cost(B) + tol AND
       sci(A) >= sci(B) - tol AND
       (dist(A) < dist(B) - tol OR cost(A) < cost(B) - tol OR sci(A) > sci(B) + tol)
    )
    """
    if not cand_a.is_feasible:
        return False
    if not cand_b.is_feasible:
        return True

    a_dist = cand_a.distance_m
    b_dist = cand_b.distance_m
    a_cost = cand_a.cost
    b_cost = cand_b.cost
    a_sci = cand_a.science_score
    b_sci = cand_b.science_score

    at_least_as_good = (
        (a_dist <= b_dist + tol)
        and (a_cost <= b_cost + tol)
        and (a_sci >= b_sci - tol)
    )
    strictly_better = (
        (a_dist < b_dist - tol)
        or (a_cost < b_cost - tol)
        or (a_sci > b_sci + tol)
    )

    return at_least_as_good and strictly_better


def extract_pareto_frontier(
    candidates: List[CandidatePlan], mode: str = "2d", tol: float = 1e-6
) -> List[CandidatePlan]:
    """
    Extract the non-dominated Pareto frontier from candidate plans.

    Only feasible plans can belong to the Pareto frontier.
    Infeasible plans are excluded.

    Parameters
    ----------
    candidates : List[CandidatePlan]
        List of all evaluated candidate plans.
    mode : str
        "2d" (distance vs. science) or "3d" (distance, cost, vs. science).
    tol : float
        Numerical tolerance for floating-point comparisons.

    Returns
    -------
    List[CandidatePlan] : Feasible, non-dominated candidates, sorted by distance ascending.
    """
    feasible_cands = [c for c in candidates if c.is_feasible]
    if not feasible_cands:
        return []

    dominance_func = check_dominance_2d if mode == "2d" else check_dominance_3d

    frontier: List[CandidatePlan] = []
    for cand in feasible_cands:
        is_dominated = False
        for other in feasible_cands:
            if cand is other:
                continue
            if dominance_func(other, cand, tol=tol):
                is_dominated = True
                break
        if not is_dominated:
            frontier.append(cand)

    # Sort frontier by distance ascending, then science ascending
    frontier.sort(key=lambda c: (c.distance_m, c.science_score))
    return frontier


def analyze_science_budget(
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    terrain: TerrainGrid,
    waypoints: List[ScienceWaypoint],
    planner_config: Optional[PlannerConfig] = None,
    terrain_config: Optional[TerrainConfig] = None,
    blocked_mask: Optional[np.ndarray] = None,
    leg_cache: Optional[Dict[Tuple[Tuple[int, int], Tuple[int, int]], Any]] = None,
    active_profile_tags: Optional[Dict[str, List[str]]] = None,
    tol: float = 1e-6,
) -> FrontierResult:
    """
    Perform complete Science Budget analysis: evaluate candidate plans,
    extract both 2D and 3D Pareto frontiers, and identify trade-off recommendations.
    """
    t0 = time.perf_counter()
    cfg = planner_config if planner_config is not None else PlannerConfig()

    candidates = evaluate_all_candidate_plans(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain,
        waypoints=waypoints,
        planner_config=cfg,
        terrain_config=terrain_config,
        blocked_mask=blocked_mask,
        leg_cache=leg_cache,
        active_profile_tags=active_profile_tags,
    )

    # Extract 2D and 3D frontiers
    pareto_2d = extract_pareto_frontier(candidates, mode="2d", tol=tol)
    pareto_3d = extract_pareto_frontier(candidates, mode="3d", tol=tol)

    p2d_ids = {c.candidate_id for c in pareto_2d}
    p3d_ids = {c.candidate_id for c in pareto_3d}

    # Annotate candidates
    infeasible: List[CandidatePlan] = []
    dominated_2d: List[CandidatePlan] = []

    for c in candidates:
        c.is_pareto_2d = c.candidate_id in p2d_ids
        c.is_pareto_3d = c.candidate_id in p3d_ids
        if not c.is_feasible:
            infeasible.append(c)
        elif not c.is_pareto_2d:
            dominated_2d.append(c)

    # Determine recommended Science Budget plan:
    # Look for candidate tagged as 'balanced', or the frontier plan maximizing marginal science per km.
    recommended: Optional[CandidatePlan] = None
    for c in pareto_2d:
        if c.profile_tag and "balanced" in c.profile_tag.lower():
            recommended = c
            break

    if recommended is None and pareto_2d:
        # Fallback to candidate on 2D frontier with highest science-to-distance ratio (excluding 0-dist)
        baseline_cand = pareto_2d[0]
        best_ratio = -1.0
        for c in pareto_2d:
            extra_dist = max(1.0, c.distance_m - baseline_cand.distance_m)
            ratio = c.science_score / extra_dist
            if ratio > best_ratio:
                best_ratio = ratio
                recommended = c

    elapsed = time.perf_counter() - t0

    return FrontierResult(
        candidates=candidates,
        pareto_candidates_2d=pareto_2d,
        pareto_candidates_3d=pareto_3d,
        dominated_candidates_2d=dominated_2d,
        infeasible_candidates=infeasible,
        recommended_plan=recommended,
        max_distance_m=cfg.max_distance_m,
        total_subsets_evaluated=len(candidates),
        execution_time_s=elapsed,
    )


def compare_frontiers(
    baseline_result: FrontierResult,
    scenario_result: FrontierResult,
) -> Dict[str, Any]:
    """
    Compare baseline and stress-tested Pareto frontiers under a Gauntlet scenario.

    Analyzes:
    - Plans newly rendered infeasible
    - Plans retained on the frontier
    - Loss of maximum reachable science points
    - Change in minimal traverse distance
    """
    base_feas_keys = {c.subset_key: c for c in baseline_result.candidates if c.is_feasible}
    scen_feas_keys = {c.subset_key: c for c in scenario_result.candidates if c.is_feasible}

    severed_keys = set(base_feas_keys.keys()) - set(scen_feas_keys.keys())
    retained_keys = set(base_feas_keys.keys()) & set(scen_feas_keys.keys())

    base_p2d_keys = {c.subset_key for c in baseline_result.pareto_candidates_2d}
    scen_p2d_keys = {c.subset_key for c in scenario_result.pareto_candidates_2d}

    frontier_retained = base_p2d_keys & scen_p2d_keys
    frontier_lost = base_p2d_keys - scen_p2d_keys
    frontier_new = scen_p2d_keys - base_p2d_keys

    max_sci_base = max((c.science_score for c in baseline_result.pareto_candidates_2d), default=0.0)
    max_sci_scen = max((c.science_score for c in scenario_result.pareto_candidates_2d), default=0.0)
    lost_science_ceiling = max(0.0, max_sci_base - max_sci_scen)

    min_dist_base = min((c.distance_m for c in baseline_result.pareto_candidates_2d), default=0.0)
    min_dist_scen = min((c.distance_m for c in scenario_result.pareto_candidates_2d), default=0.0)
    delta_min_dist = min_dist_scen - min_dist_base

    return {
        "num_baseline_feasible": len(base_feas_keys),
        "num_scenario_feasible": len(scen_feas_keys),
        "num_severed_plans": len(severed_keys),
        "num_retained_plans": len(retained_keys),
        "frontier_retained_count": len(frontier_retained),
        "frontier_lost_count": len(frontier_lost),
        "frontier_new_count": len(frontier_new),
        "max_science_baseline": max_sci_base,
        "max_science_scenario": max_sci_scen,
        "lost_science_ceiling": lost_science_ceiling,
        "min_dist_baseline": min_dist_base,
        "min_dist_scenario": min_dist_scen,
        "delta_min_dist": delta_min_dist,
    }


def generate_science_budget_narrative(
    frontier_result: FrontierResult,
    voice_mode: str = "professional",
) -> Dict[str, str]:
    """
    Produce structured, deterministic debrief narratives explaining the Pareto frontier
    and exploration trade-offs in either Professional or Dry Humour modes.
    """
    is_humour = voice_mode == "dry_humour"
    pareto_2d = frontier_result.pareto_candidates_2d
    total_eval = frontier_result.total_subsets_evaluated
    infeas_count = len(frontier_result.infeasible_candidates)
    feas_count = total_eval - infeas_count

    if not pareto_2d:
        if is_humour:
            headline = "Pareto Frontier Status: The empty set wins."
            detail = (
                "Not a single candidate exploration plan cleared the current terrain and life-support constraints. "
                "Unless the crew has perfected teleportation, revision of the mission budget is required."
            )
        else:
            headline = "Exploration Trade-Off Alert: Zero Feasible Plans."
            detail = (
                "All candidate waypoint combinations violate either slope cutoffs, impassable barriers, "
                "or physical distance budgets. No Pareto-optimal traverse exists."
            )
        return {"headline": headline, "detail": detail}

    min_plan = pareto_2d[0]
    max_plan = pareto_2d[-1]
    rec_plan = frontier_result.recommended_plan or pareto_2d[0]

    added_dist = max_plan.distance_m - min_plan.distance_m
    added_sci = max_plan.science_score - min_plan.science_score

    if is_humour:
        headline = (
            f"Science Budget: {len(pareto_2d)} efficient options identified out of {feas_count} feasible paths."
        )
        if len(pareto_2d) == 1:
            detail = (
                f"The laws of Martian physics have left exactly one non-dominated choice. "
                f"Visiting {rec_plan.num_targets} targets gives {rec_plan.science_score:.0f} points for {rec_plan.distance_m:.0f} m. "
                f"Decisions are remarkably straightforward when there are no alternatives."
            )
        else:
            detail = (
                f"Gaining {added_sci:.0f} additional science points requires +{added_dist:.0f} m of extra boots-on-the-ground walking. "
                f"More science is available. Unfortunately, so is more walking. "
                f"Our recommended compromise visits {rec_plan.num_targets} targets ({rec_plan.science_score:.0f} pts) at {rec_plan.distance_m:.0f} m."
            )
    else:
        headline = (
            f"Pareto Frontier Evaluated: {len(pareto_2d)} Non-Dominated Plans ({feas_count}/{total_eval} Feasible)."
        )
        if len(pareto_2d) == 1:
            detail = (
                f"A single non-dominated configuration satisfies mission constraints, yielding {rec_plan.science_score:.0f} "
                f"priority points at a total distance of {rec_plan.distance_m:.0f} m."
            )
        else:
            marginal_rate = (added_dist / added_sci) if added_sci > 0 else 0.0
            detail = (
                f"The exploration frontier spans from {min_plan.distance_m:.0f} m ({min_plan.science_score:.0f} pts) "
                f"to {max_plan.distance_m:.0f} m ({max_plan.science_score:.0f} pts). "
                f"Full science harvest incurs a +{added_dist:.0f} m distance penalty ({marginal_rate:.1f} m/point). "
                f"Recommended plan: {rec_plan.candidate_id} visiting {rec_plan.num_targets} targets."
            )

    return {"headline": headline, "detail": detail}


def export_mission_brief_csv(frontier_result: FrontierResult) -> str:
    """
    Format all evaluated candidate plans as a clean CSV string.
    """
    import io
    import csv

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "candidate_id",
        "num_targets",
        "visited_targets",
        "distance_m",
        "modeled_terrain_cost",
        "science_priority_pts",
        "is_reachable",
        "is_budget_feasible",
        "is_feasible",
        "is_pareto_2d",
        "is_pareto_3d",
        "profile_tag",
        "commander_utility",
    ])

    for c in frontier_result.candidates:
        targets_str = ";".join(c.visited_waypoint_ids)
        util_str = f"{c.utility_score:.4f}" if c.utility_score is not None else ""
        writer.writerow([
            c.candidate_id,
            c.num_targets,
            targets_str,
            f"{c.distance_m:.1f}",
            f"{c.cost:.1f}",
            f"{c.science_score:.1f}",
            c.is_reachable,
            c.is_budget_feasible,
            c.is_feasible,
            c.is_pareto_2d,
            c.is_pareto_3d,
            c.profile_tag or "",
            util_str,
        ])

    return output.getvalue()


def export_mission_brief_json(
    frontier_result: FrontierResult,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Format full mission brief and candidate plan specifications as a reproducible JSON string.
    """
    meta = metadata or {}
    data = {
        "schema_version": "1.0",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mission_metadata": meta,
        "summary": {
            "total_candidates_evaluated": frontier_result.total_subsets_evaluated,
            "feasible_candidates": sum(1 for c in frontier_result.candidates if c.is_feasible),
            "infeasible_candidates": len(frontier_result.infeasible_candidates),
            "pareto_2d_count": len(frontier_result.pareto_candidates_2d),
            "pareto_3d_count": len(frontier_result.pareto_candidates_3d),
            "max_distance_budget_m": frontier_result.max_distance_m,
            "recommended_plan_id": frontier_result.recommended_plan.candidate_id if frontier_result.recommended_plan else None,
        },
        "pareto_frontier_2d": [
            {
                "candidate_id": c.candidate_id,
                "visited_targets": c.visited_waypoint_ids,
                "distance_m": round(c.distance_m, 2),
                "cost": round(c.cost, 2),
                "science_score": round(c.science_score, 2),
                "profile_tag": c.profile_tag,
            }
            for c in frontier_result.pareto_candidates_2d
        ],
        "disclaimer": (
            "MarsWalk is an independent student planning prototype developed for the 2026 NASA Space Apps Challenge. "
            "Routes are modeled engineering trade-offs over 20 m/pixel orbital topography, not certified operational astronaut paths."
        ),
    }
    return json.dumps(data, indent=2)
