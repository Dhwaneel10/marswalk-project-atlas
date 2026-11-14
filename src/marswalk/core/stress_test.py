"""
MarsWalk The Gauntlet: EVA Stress-Testing & Dynamic Scenario Engine.
Provides reproducible hypothetical mission disruptions (Corridor Closures,
Reduced Travel Budgets, Target Inaccessibility) and computes the Science Regret Ledger
and Route Toughness reports without altering underlying planetary terrain.
"""

from dataclasses import dataclass, field, replace
import enum
import math
import time
from typing import Dict, List, Optional, Set, Tuple, Any

import numpy as np

from marswalk.core.terrain import TerrainConfig, TerrainGrid, get_profile_terrain_config
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    RouteResult,
    plan_route,
    plan_sequential_multistop_route,
    build_mission_timeline,
    OPERATIONAL_LIMITS_S,
)


class DisruptionType(str, enum.Enum):
    CORRIDOR_CLOSURE = "corridor_closure"
    UNSTABLE_SAND = "unstable_sand"
    RESTRICTED_SLOPE = "restricted_slope"
    MOBILITY_DEGRADATION = "mobility_degradation"
    DUST_STORM_VISIBILITY = "dust_storm_visibility"
    TARGET_UNAVAILABLE = "target_unavailable"
    REDUCED_BUDGET = "reduced_budget"
    COMPOUND_DISRUPTION = "compound_disruption"


@dataclass
class ScenarioDefinition:
    """
    Specification for a hypothetical mission disruption.

    Parameters
    ----------
    id : str
        Unique scenario identifier.
    name : str
        Human-readable scenario title.
    disruption_type : DisruptionType
        Type of disruption.
    description : str
        Operational narrative explaining the hypothetical event.
    is_simulated : bool
        Watermark indicating simulated status (always True).
    blocked_cells : Optional[List[Tuple[int, int]]]
        List of (row, col) grid coordinates blocked by the disruption.
    cost_multiplier_cells : Optional[List[Tuple[int, int]]]
        List of (row, col) grid coordinates with elevated traversal impedance.
    cost_multiplier : float
        Multiplication factor on traversal cost (default 1.0, e.g. 3.0 for sand).
    max_slope_deg_override : Optional[float]
        Tightened cutoff slope threshold in degrees (e.g. 10.0 deg).
    speed_multiplier : float
        Speed multiplier on nominal drive velocity (e.g. 0.5 for degraded mobility).
    slope_penalty_multiplier : float
        Multiplier on slope traversal penalty (e.g. 1.5 for degraded mobility).
    operational_delay_s : float
        Mandatory operational delay in seconds (e.g. 1800s for dust storm hold).
    budget_reduction_pct : Optional[float]
        Percentage reduction in distance budget (e.g. 25.0 for 25%).
    reduced_max_distance_m : Optional[float]
        Explicit distance budget ceiling in meters.
    unavailable_target_id : Optional[str]
        Identifier of the science waypoint rendered inaccessible.
    compound_scenarios : Optional[List['ScenarioDefinition']]
        List of sub-scenarios combined into a compound disruption.
    compound_scenario_ids : Optional[List[str]]
        List of scenario IDs active in compound disruption.
    assumptions : str
        Documented simulation assumptions for scientific auditability.
    """

    id: str
    name: str
    disruption_type: DisruptionType
    description: str
    is_simulated: bool = True
    blocked_cells: Optional[List[Tuple[int, int]]] = None
    cost_multiplier_cells: Optional[List[Tuple[int, int]]] = None
    cost_multiplier: float = 1.0
    max_slope_deg_override: Optional[float] = None
    speed_multiplier: float = 1.0
    slope_penalty_multiplier: float = 1.0
    operational_delay_s: float = 0.0
    budget_reduction_pct: Optional[float] = None
    reduced_time_budget_s: Optional[float] = None
    reduced_max_distance_m: Optional[float] = None
    unavailable_target_id: Optional[str] = None
    compound_scenarios: Optional[List["ScenarioDefinition"]] = None
    compound_scenario_ids: Optional[List[str]] = None
    center_rc: Optional[Tuple[int, int]] = None
    radius_m: float = 50.0
    intersects_baseline: bool = False
    assumptions: str = ""


@dataclass
class RegretLedger:
    """
    Quantifies the preservation vs sacrifice of scientific objectives.
    """

    baseline_visited_ids: List[str]
    scenario_visited_ids: List[str]
    retained_target_ids: List[str]
    dropped_by_optimizer_ids: List[str]
    disabled_by_scenario_ids: List[str]

    baseline_priority: float
    retained_priority: float
    lost_priority: float
    retention_pct: float


@dataclass
class ScenarioComparison:
    """
    Comprehensive before-and-after comparison between baseline and stress-tested plans.
    """

    scenario: ScenarioDefinition
    baseline_route: RouteResult
    scenario_route: RouteResult

    baseline_distance_m: float
    scenario_distance_m: float
    delta_distance_m: float
    pct_distance_change: Optional[float]

    baseline_cost: float
    scenario_cost: float
    delta_cost: float
    pct_cost_change: Optional[float]

    is_baseline_reachable: bool
    is_scenario_reachable: bool

    is_baseline_budget_feasible: bool
    is_scenario_budget_feasible: bool
    effective_budget_m: Optional[float]

    regret_ledger: RegretLedger
    headline: str
    detail: str
    voice_mode: str = "professional"
    delta_travel_time_s: float = 0.0
    formatted_delta_travel_time: str = ""
    recovery_strategy: Optional[str] = None
    recovery_route: Optional[RouteResult] = None
    recovery_margin_recovered_s: float = 0.0
    formatted_recovery_margin: str = ""
    recovery_action_label: str = ""
    is_recovery_recommended: bool = False


@dataclass
class ToughnessScenarioResult:
    """
    Outcome of an individual scenario in the Route Toughness suite.
    """

    scenario: ScenarioDefinition
    is_reachable: bool
    is_budget_feasible: bool
    distance_m: float
    cost: float
    science_score: float
    delta_distance_m: float
    delta_cost: float
    retention_pct: float


@dataclass
class ToughnessReport:
    """
    Summary evaluation of a route's resilience across a suite of disruptions.
    """

    baseline_route: RouteResult
    results: List[ToughnessScenarioResult]
    total_scenarios_tested: int
    feasible_count: int
    budget_met_count: int
    max_distance_increase_m: float
    min_retention_pct: float
    avg_retention_pct: float
    summary_narrative: str


def compute_science_regret_ledger(
    baseline_route: RouteResult,
    scenario_route: RouteResult,
    waypoints: List[ScienceWaypoint],
    scenario: ScenarioDefinition,
) -> RegretLedger:
    """
    Compute the Science Regret Ledger distinguishing between targets explicitly disabled
    by the scenario versus targets omitted by the route optimizer to save cost/distance.
    """
    wp_by_id = {w.id: w for w in (waypoints or [])}

    base_visited = list(baseline_route.visited_waypoint_ids)
    scen_visited = list(scenario_route.visited_waypoint_ids) if scenario_route.is_reachable else []

    retained = [wid for wid in base_visited if wid in scen_visited]
    lost = [wid for wid in base_visited if wid not in scen_visited]

    disabled_by_scen = []
    dropped_by_opt = []

    for wid in lost:
        if (
            scenario.disruption_type in (DisruptionType.TARGET_UNAVAILABLE, DisruptionType.COMPOUND_DISRUPTION)
            and scenario.unavailable_target_id == wid
        ):
            disabled_by_scen.append(wid)
        else:
            dropped_by_opt.append(wid)

    base_priority = float(sum(wp_by_id[wid].priority_score for wid in base_visited if wid in wp_by_id))
    retained_priority = float(sum(wp_by_id[wid].priority_score for wid in retained if wid in wp_by_id))
    lost_priority = max(0.0, base_priority - retained_priority)

    retention_pct = (
        (retained_priority / base_priority * 100.0) if base_priority > 0.0 else 100.0
    )

    return RegretLedger(
        baseline_visited_ids=base_visited,
        scenario_visited_ids=scen_visited,
        retained_target_ids=retained,
        dropped_by_optimizer_ids=dropped_by_opt,
        disabled_by_scenario_ids=disabled_by_scen,
        baseline_priority=base_priority,
        retained_priority=retained_priority,
        lost_priority=lost_priority,
        retention_pct=retention_pct,
    )


def generate_scenario_narrative(
    scenario: ScenarioDefinition,
    baseline_route: RouteResult,
    scenario_route: RouteResult,
    ledger: RegretLedger,
    voice_mode: str = "professional",
) -> Tuple[str, str]:
    """
    Produce deterministic headline and detail narrative for the stress-test outcome.
    """
    is_humour = voice_mode == "dry_humour"

    # Case 1: Scenario Route is completely unreachable
    if not scenario_route.is_reachable:
        if is_humour:
            headline = f"The Gauntlet: {scenario.name} — Absolute Deadlock."
            detail = (
                f"Under simulated condition '{scenario.name}', all connecting corridors to the destination "
                "are completely severed. The rover team is currently debating whether walking backwards helps. "
                "Mission aborted: destination unreachable."
            )
        else:
            headline = f"Traverse Infeasible: {scenario.name} Severed All Corridors."
            detail = (
                f"Under hypothetical scenario '{scenario.name}', no continuous path exists between start and goal "
                "satisfying slope and boundary limits. The destination cannot be reached."
            )
        return headline, detail

    # Case 2: Corridor Closure
    if scenario.disruption_type == DisruptionType.CORRIDOR_CLOSURE:
        delta_d = scenario_route.distance_m - baseline_route.distance_m
        delta_c = scenario_route.cost - baseline_route.cost
        num_cells = len(scenario.blocked_cells or [])

        # Check if disruption actually intersected the baseline route or caused a detour
        if not scenario.intersects_baseline or abs(delta_d) < 0.1:
            if is_humour:
                headline = f"Disruption Averted: {scenario.name} missed our path entirely."
                detail = (
                    f"A hypothetical rockfall ({num_cells} cells) occurred well clear of our planned traverse. "
                    f"The rover rolled on uninterrupted: 0 m detour, 0 wasted effort."
                )
            else:
                headline = f"No Route Impact: {scenario.name} Clears Active Corridor."
                detail = (
                    f"Simulated disruption ({num_cells} cells) does not intersect the active traverse corridor. "
                    f"Route distance ({baseline_route.distance_m:.0f} m) and travel time ({baseline_route.formatted_travel_time}) remain unchanged."
                )
            return headline, detail

        delta_time_min = round((scenario_route.travel_time_s - baseline_route.travel_time_s) / 60.0)
        time_txt = f", +{delta_time_min} min" if delta_time_min > 0 else ""

        if is_humour:
            headline = f"Corridor Blocked: Well, that shortcut had a good run. Recalculating (+{delta_d:.0f} m{time_txt})."
            detail = (
                f"A hypothetical barrier ({num_cells} cells) closed our primary corridor. "
                f"The planner diverted around the obstacle, adding +{delta_d:.0f} m of walking distance and "
                f"+{delta_c:.0f} terrain effort. Science retained: {ledger.retention_pct:.0f}%."
            )
        else:
            headline = f"Replanning Successful: Detour Active Around {scenario.name} (+{delta_d:.0f} m{time_txt})."
            detail = (
                f"Simulated closure of {num_cells} grid cells forced a lateral route detour. "
                f"Traverse distance shifted from {baseline_route.distance_m:.0f} m to {scenario_route.distance_m:.0f} m "
                f"(+{delta_d:.0f} m, +{delta_c:.0f} terrain effort). Estimated travel time shifted from {baseline_route.formatted_travel_time} to {scenario_route.formatted_travel_time}. Preserved {len(ledger.retained_target_ids)}/{len(ledger.baseline_visited_ids)} objectives."
            )
        return headline, detail

    # Case 3: Unstable Sand / Dune Migration
    if scenario.disruption_type == DisruptionType.UNSTABLE_SAND:
        delta_d = scenario_route.distance_m - baseline_route.distance_m
        delta_c = scenario_route.cost - baseline_route.cost
        delta_time_min = round((scenario_route.travel_time_s - baseline_route.travel_time_s) / 60.0)
        time_txt = f", +{delta_time_min} min" if delta_time_min > 0 else ""

        if not scenario.intersects_baseline:
            headline = f"No Route Impact: {scenario.name} Clears Active Corridor."
            detail = (
                f"Active dune migration ({len(scenario.cost_multiplier_cells or [])} cells, {scenario.cost_multiplier:.1f}× impedance) "
                f"does not intersect our planned traverse. Distance ({baseline_route.distance_m:.0f} m) and time remain nominal."
            )
        elif delta_d > 5.0:
            headline = f"Dune Hazard Evaded: Planner Detoured Around High-Slip Sand (+{delta_d:.0f} m{time_txt})."
            detail = (
                f"High-slip sand megaripples ({scenario.cost_multiplier:.1f}× impedance) obstructed direct channel. "
                f"Planner executed an evasive lateral detour (+{delta_d:.0f} m, +{delta_c:.0f} effort). Travel time: {scenario_route.formatted_travel_time}."
            )
        else:
            headline = f"Sand Field Traversed: Cost Absorbed on Direct Path (+{delta_c:.0f} effort{time_txt})."
            detail = (
                f"Planner navigated through the high-slip sand hazard ({scenario.cost_multiplier:.1f}× impedance), "
                f"absorbing +{delta_c:.0f} extra terrain effort ({time_txt.lstrip(', ')}) because an evasive detour was less efficient."
            )
        return headline, detail

    # Case 4: Restricted Slope Corridor
    if scenario.disruption_type == DisruptionType.RESTRICTED_SLOPE:
        delta_d = scenario_route.distance_m - baseline_route.distance_m
        delta_time_min = round((scenario_route.travel_time_s - baseline_route.travel_time_s) / 60.0)
        time_txt = f", +{delta_time_min} min" if delta_time_min > 0 else ""
        cutoff = scenario.max_slope_deg_override or 10.0

        if not scenario.intersects_baseline and abs(delta_d) < 0.1:
            headline = f"No Route Impact: Traverse Already Complies with {cutoff:.0f}° Ceiling."
            detail = (
                f"Planned mission traverse does not exceed the tightened {cutoff:.0f}° slope threshold. "
                f"Route distance ({baseline_route.distance_m:.0f} m) and travel time remain unaffected."
            )
        else:
            headline = f"Slope Ceiling Enforced: Steeper Scarp Bypassed (+{delta_d:.0f} m{time_txt})."
            detail = (
                f"Maximum allowable slope capped at {cutoff:.0f}°. The planner bypassed steep scarp sections, "
                f"shifting distance from {baseline_route.distance_m:.0f} m to {scenario_route.distance_m:.0f} m (+{delta_d:.0f} m). Travel time: {scenario_route.formatted_travel_time}."
            )
        return headline, detail

    # Case 5: Rover Mobility Degradation
    if scenario.disruption_type == DisruptionType.MOBILITY_DEGRADATION:
        delta_time_min = round((scenario_route.travel_time_s - baseline_route.travel_time_s) / 60.0)
        delta_c = scenario_route.cost - baseline_route.cost
        headline = f"Mobility Derated: Drive Speed Reduced ({scenario.speed_multiplier:.1f}×), Time Expanded (+{delta_time_min} min)."
        detail = (
            f"Drive actuator anomaly derated vehicle speed to {scenario.speed_multiplier:.1f}× nominal with {scenario.slope_penalty_multiplier:.1f}× slope effort. "
            f"Physical traverse geometry maintained (0 m detour); travel time shifted from {baseline_route.formatted_travel_time} to {scenario_route.formatted_travel_time}. Preserved 100% of scientific objectives."
        )
        return headline, detail

    # Case 6: Dust Storm / Reduced Visibility
    if scenario.disruption_type == DisruptionType.DUST_STORM_VISIBILITY:
        delta_time_min = round((scenario_route.travel_time_s - baseline_route.travel_time_s) / 60.0)
        delay_min = round(scenario.operational_delay_s / 60.0)
        headline = f"Dust Storm Protocol: Optical Derating ({scenario.speed_multiplier:.1f}×) & +{delay_min} min Comms Hold."
        detail = (
            f"Atmospheric opacity degraded navcam visibility to {scenario.speed_multiplier:.1f}× speed and initiated a mandatory {delay_min}-minute safety hold. "
            f"Physical traverse distance ({scenario_route.distance_m:.0f} m) unchanged; mission timeline expanded from {baseline_route.formatted_travel_time} to {scenario_route.formatted_travel_time} (+{delta_time_min} min)."
        )
        return headline, detail

    # Case 7: Compound Disruption
    if scenario.disruption_type == DisruptionType.COMPOUND_DISRUPTION:
        delta_d = scenario_route.distance_m - baseline_route.distance_m
        delta_time_min = round((scenario_route.travel_time_s - baseline_route.travel_time_s) / 60.0)
        time_txt = f", +{delta_time_min} min" if delta_time_min > 0 else ""
        headline = f"Compound Disruption: {scenario.name} (+{delta_d:.0f} m{time_txt})."
        detail = (
            f"Simulated concurrent cascading anomalies ({scenario.description}). "
            f"Traverse shifted to {scenario_route.distance_m:.0f} m (+{delta_d:.0f} m); travel time shifted to {scenario_route.formatted_travel_time}. "
            f"Preserved {len(ledger.retained_target_ids)}/{len(ledger.baseline_visited_ids)} objectives ({ledger.retention_pct:.0f}%)."
        )
        return headline, detail

    # Case 8: Reduced Travel Budget
    if scenario.disruption_type == DisruptionType.REDUCED_BUDGET:
        dropped_count = len(ledger.dropped_by_optimizer_ids)
        budget_m = scenario_route.max_distance_m or 0.0

        if not scenario_route.is_budget_feasible:
            if is_humour:
                headline = "Budget Blown: Crew running on emergency reserves."
                detail = (
                    f"Consumable limits dropped by {scenario.budget_reduction_pct or 0:.0f}%. "
                    f"Mission plan ({scenario_route.distance_m:.0f} m, {scenario_route.formatted_travel_time}) "
                    "exceeds the safe operational window. Immediate recovery action required."
                )
            else:
                headline = f"Budget Exceeded: Mission Violates Constrained Limits Under {scenario.name}."
                detail = (
                    f"Traverse required {scenario_route.distance_m:.0f} m ({scenario_route.formatted_travel_time}), "
                    f"exceeding allowable operational limits under simulated disruption. "
                    f"Operational margin is negative or depleted."
                )
        else:
            if is_humour:
                if dropped_count > 0:
                    headline = "Budget Crunch: Curiosity: unlimited. Travel budget: apparently not."
                    detail = (
                        f"Walking ceiling restricted. The optimizer shed {dropped_count} science stop(s) "
                        f"to keep your crew within breathing range. Science retained: {ledger.retention_pct:.0f}%."
                    )
                else:
                    headline = "Budget Restriction: We squeaked through under the wire."
                    detail = (
                        f"Travel budget tightened. Miraculously, all baseline objectives were retained "
                        "without violating life-support ceilings. Do not push your luck."
                    )
            else:
                if dropped_count > 0:
                    headline = f"Budget Constrained: {dropped_count} Target(s) Pruned to Fit Tightened Limit."
                    detail = (
                        f"Operational limits enforced. The optimizer discarded "
                        f"{dropped_count} objective(s) ({', '.join(ledger.dropped_by_optimizer_ids)}), "
                        f"preserving {ledger.retained_priority:.0f}/{ledger.baseline_priority:.0f} priority points ({ledger.retention_pct:.0f}%)."
                    )
                else:
                    headline = f"Budget Compliant: All Objectives Met Within Operational Limits."
                    detail = (
                        f"Traverse plan completed at {scenario_route.distance_m:.0f} m ({scenario_route.formatted_travel_time}), "
                        f"satisfying operational constraints under {scenario.name}. All targets retained."
                    )
        return headline, detail

    # Case 9: Target Inaccessible
    if scenario.disruption_type == DisruptionType.TARGET_UNAVAILABLE:
        target_id = scenario.unavailable_target_id or "designated target"
        saved_d = baseline_route.distance_m - scenario_route.distance_m

        if is_humour:
            headline = f"Target Abort: {target_id} dropped from itinerary."
            detail = (
                f"Objective '{target_id}' declared unavailable. Skipping the detour saves {saved_d:.0f} m of walking. "
                "Houston scientists are devastated, but the astronauts' quadriceps are quietly celebrating."
            )
        else:
            headline = f"Objective Removed: Itinerary Replanned Without {target_id}."
            detail = (
                f"Waypoint '{target_id}' excluded from hypothetical plan. Traverse distance reduced by "
                f"{saved_d:.0f} m. Remaining active targets visited: {len(ledger.retained_target_ids)}."
            )
        return headline, detail

    return f"Scenario Evaluated: {scenario.name}", "Replanning complete under hypothetical constraints."


def run_scenario(
    baseline_route: RouteResult,
    scenario: ScenarioDefinition,
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    waypoints: List[ScienceWaypoint],
    terrain: TerrainGrid,
    planner_config: Optional[PlannerConfig] = None,
    terrain_config: Optional[TerrainConfig] = None,
    voice_mode: str = "professional",
    vehicle_mode: str = "crew_eva",
    dwell_time_per_stop_s: float = 900.0,
    ordered_points: Optional[List[Tuple[int, int]]] = None,
    stop_ids: Optional[List[str]] = None,
    stop_priorities: Optional[List[float]] = None,
) -> ScenarioComparison:
    """
    Execute a hypothetical disruption scenario against a baseline mission configuration.
    Preserves baseline results and underlying planetary terrain without mutation.
    """
    p_cfg = planner_config if planner_config is not None else PlannerConfig(profile=baseline_route.profile)
    t_cfg = terrain_config if terrain_config is not None else terrain.config

    # Copy / determine scenario-modified parameters
    base_limit_s = (
        baseline_route.timeline.operational_limit_s
        if baseline_route.timeline is not None
        else OPERATIONAL_LIMITS_S.get(vehicle_mode, 8.0 * 3600.0)
    )
    scen_operational_limit_s = base_limit_s
    scen_blocked_mask: Optional[np.ndarray] = None
    scen_cost_multiplier_mask: Optional[np.ndarray] = None
    scen_waypoints = list(waypoints) if waypoints is not None else []
    scen_max_distance_m = p_cfg.max_distance_m
    scen_terrain_config = t_cfg
    scen_speed_multiplier = float(scenario.speed_multiplier)
    scen_operational_delay_s = float(scenario.operational_delay_s)

    # 1. Apply Corridor Closure
    if scenario.disruption_type == DisruptionType.CORRIDOR_CLOSURE:
        if scenario.blocked_cells:
            scen_blocked_mask = np.zeros(terrain.shape, dtype=bool)
            for r, c in scenario.blocked_cells:
                if 0 <= r < terrain.height and 0 <= c < terrain.width:
                    scen_blocked_mask[r, c] = True

    # 2. Apply Unstable Sand
    elif scenario.disruption_type == DisruptionType.UNSTABLE_SAND:
        if scenario.cost_multiplier_cells:
            c_mask = np.ones(terrain.shape, dtype=np.float32)
            for r, c in scenario.cost_multiplier_cells:
                if 0 <= r < terrain.height and 0 <= c < terrain.width:
                    c_mask[r, c] = float(scenario.cost_multiplier)
            scen_cost_multiplier_mask = c_mask

    # 3. Apply Restricted Slope Threshold
    elif scenario.disruption_type == DisruptionType.RESTRICTED_SLOPE:
        if scenario.max_slope_deg_override is not None:
            max_s = float(scenario.max_slope_deg_override)
            crit_s = min(t_cfg.theta_crit_deg, max_s * 0.7)
            scen_terrain_config = TerrainConfig(
                cell_size_m=t_cfg.cell_size_m,
                ref_lat_deg=t_cfg.ref_lat_deg,
                dx_ground_m=t_cfg.dx_ground_m,
                dy_ground_m=t_cfg.dy_ground_m,
                alpha_s=t_cfg.alpha_s,
                theta_crit_deg=crit_s,
                theta_max_deg=max_s,
                alpha_r=t_cfg.alpha_r,
                sigma_0_m=t_cfg.sigma_0_m,
                alpha_up=t_cfg.alpha_up,
                nodata_sentinel=t_cfg.nodata_sentinel,
                min_valid_elev_m=t_cfg.min_valid_elev_m,
                max_valid_elev_m=t_cfg.max_valid_elev_m,
            )

    # 4. Apply Mobility Degradation
    elif scenario.disruption_type == DisruptionType.MOBILITY_DEGRADATION:
        if scenario.slope_penalty_multiplier != 1.0:
            scen_terrain_config = TerrainConfig(
                cell_size_m=t_cfg.cell_size_m,
                ref_lat_deg=t_cfg.ref_lat_deg,
                dx_ground_m=t_cfg.dx_ground_m,
                dy_ground_m=t_cfg.dy_ground_m,
                alpha_s=t_cfg.alpha_s * float(scenario.slope_penalty_multiplier),
                theta_crit_deg=t_cfg.theta_crit_deg,
                theta_max_deg=t_cfg.theta_max_deg,
                alpha_r=t_cfg.alpha_r,
                sigma_0_m=t_cfg.sigma_0_m,
                alpha_up=t_cfg.alpha_up,
                nodata_sentinel=t_cfg.nodata_sentinel,
                min_valid_elev_m=t_cfg.min_valid_elev_m,
                max_valid_elev_m=t_cfg.max_valid_elev_m,
            )

    # 5. Apply Reduced Travel Budget
    elif scenario.disruption_type == DisruptionType.REDUCED_BUDGET:
        if scenario.reduced_max_distance_m is not None:
            scen_max_distance_m = float(scenario.reduced_max_distance_m)
        if scenario.reduced_time_budget_s is not None:
            scen_operational_limit_s = float(scenario.reduced_time_budget_s)
        elif scenario.budget_reduction_pct is not None:
            pct = float(scenario.budget_reduction_pct)
            scen_operational_limit_s = max(600.0, base_limit_s * (1.0 - pct / 100.0))
        if scenario.budget_reduction_pct is not None:
            pct = float(scenario.budget_reduction_pct)
            if p_cfg.max_distance_m is not None:
                scen_max_distance_m = max(100.0, p_cfg.max_distance_m * (1.0 - pct / 100.0))
            elif scenario.reduced_max_distance_m is None:
                scen_max_distance_m = max(100.0, baseline_route.distance_m * (1.0 - pct / 100.0))
        elif scenario.reduced_time_budget_s is not None and base_limit_s > 0 and scenario.reduced_max_distance_m is None:
            time_ratio = float(scenario.reduced_time_budget_s) / base_limit_s
            if time_ratio < 1.0:
                scen_max_distance_m = max(100.0, baseline_route.distance_m * time_ratio)

    # 6. Apply Target Inaccessibility
    elif scenario.disruption_type == DisruptionType.TARGET_UNAVAILABLE:
        if scenario.unavailable_target_id:
            scen_waypoints = [w for w in scen_waypoints if w.id != scenario.unavailable_target_id]

    # 7. Apply Compound Disruption
    elif scenario.disruption_type == DisruptionType.COMPOUND_DISRUPTION:
        if scenario.blocked_cells:
            scen_blocked_mask = np.zeros(terrain.shape, dtype=bool)
            for r, c in scenario.blocked_cells:
                if 0 <= r < terrain.height and 0 <= c < terrain.width:
                    scen_blocked_mask[r, c] = True
        if scenario.cost_multiplier_cells:
            c_mask = np.ones(terrain.shape, dtype=np.float32)
            for r, c in scenario.cost_multiplier_cells:
                if 0 <= r < terrain.height and 0 <= c < terrain.width:
                    c_mask[r, c] = float(scenario.cost_multiplier)
            scen_cost_multiplier_mask = c_mask
        if scenario.max_slope_deg_override is not None:
            max_s = float(scenario.max_slope_deg_override)
            crit_s = min(t_cfg.theta_crit_deg, max_s * 0.7)
            scen_terrain_config = TerrainConfig(
                cell_size_m=t_cfg.cell_size_m,
                ref_lat_deg=t_cfg.ref_lat_deg,
                dx_ground_m=t_cfg.dx_ground_m,
                dy_ground_m=t_cfg.dy_ground_m,
                alpha_s=t_cfg.alpha_s * float(scenario.slope_penalty_multiplier),
                theta_crit_deg=crit_s,
                theta_max_deg=max_s,
                alpha_r=t_cfg.alpha_r,
                sigma_0_m=t_cfg.sigma_0_m,
                alpha_up=t_cfg.alpha_up,
                nodata_sentinel=t_cfg.nodata_sentinel,
                min_valid_elev_m=t_cfg.min_valid_elev_m,
                max_valid_elev_m=t_cfg.max_valid_elev_m,
            )
        if scenario.unavailable_target_id:
            scen_waypoints = [w for w in scen_waypoints if w.id != scenario.unavailable_target_id]
        if scenario.reduced_time_budget_s is not None:
            scen_operational_limit_s = float(scenario.reduced_time_budget_s)
        elif scenario.budget_reduction_pct is not None:
            pct = float(scenario.budget_reduction_pct)
            scen_operational_limit_s = max(600.0, base_limit_s * (1.0 - pct / 100.0))
        if scenario.budget_reduction_pct is not None:
            pct = float(scenario.budget_reduction_pct)
            if p_cfg.max_distance_m is not None:
                scen_max_distance_m = max(100.0, p_cfg.max_distance_m * (1.0 - pct / 100.0))
            elif scenario.reduced_max_distance_m is None:
                scen_max_distance_m = max(100.0, baseline_route.distance_m * (1.0 - pct / 100.0))
        elif scenario.reduced_time_budget_s is not None and base_limit_s > 0 and scenario.reduced_max_distance_m is None:
            time_ratio = float(scenario.reduced_time_budget_s) / base_limit_s
            if time_ratio < 1.0:
                scen_max_distance_m = max(100.0, baseline_route.distance_m * time_ratio)
        if scenario.reduced_max_distance_m is not None:
            scen_max_distance_m = float(scenario.reduced_max_distance_m)

    # Determine if scenario intersects baseline
    if scenario.disruption_type == DisruptionType.CORRIDOR_CLOSURE:
        path_set = set(baseline_route.path) if baseline_route.path else set()
        scenario.intersects_baseline = any(cell in path_set for cell in (scenario.blocked_cells or []))
    elif scenario.disruption_type == DisruptionType.UNSTABLE_SAND:
        path_set = set(baseline_route.path) if baseline_route.path else set()
        scenario.intersects_baseline = any(cell in path_set for cell in (scenario.cost_multiplier_cells or []))
    elif scenario.disruption_type == DisruptionType.RESTRICTED_SLOPE:
        override = scenario.max_slope_deg_override or 10.0
        scenario.intersects_baseline = any(terrain.slope_deg[r, c] >= override for r, c in (baseline_route.path or []))
    elif scenario.disruption_type in (DisruptionType.MOBILITY_DEGRADATION, DisruptionType.DUST_STORM_VISIBILITY):
        scenario.intersects_baseline = True
    elif scenario.disruption_type == DisruptionType.TARGET_UNAVAILABLE:
        scenario.intersects_baseline = (scenario.unavailable_target_id in baseline_route.visited_waypoint_ids)
    elif scenario.disruption_type == DisruptionType.REDUCED_BUDGET:
        dist_violation = (scen_max_distance_m is not None and baseline_route.distance_m > scen_max_distance_m)
        time_violation = (baseline_route.timeline is not None and baseline_route.timeline.total_mission_time_s > scen_operational_limit_s)
        scenario.intersects_baseline = dist_violation or time_violation
    elif scenario.disruption_type == DisruptionType.COMPOUND_DISRUPTION:
        scenario.intersects_baseline = True

    # Formulate revised PlannerConfig
    scen_planner_config = PlannerConfig(
        profile=p_cfg.profile,
        science_appetite_gamma=p_cfg.science_appetite_gamma,
        max_distance_m=scen_max_distance_m,
        max_waypoints=p_cfg.max_waypoints,
    )

    # Replan route using existing deterministic planner or sequential multi-stop
    # Non-geometric detour check: Mobility Degradation, Dust Storm, or compound without spatial hurdles keep identical physical route
    has_spatial_hurdle = bool(scenario.blocked_cells) or bool(scenario.cost_multiplier_cells) or bool(scenario.unavailable_target_id) or (scenario.max_slope_deg_override is not None)
    is_non_geometric = (
        scenario.disruption_type in (DisruptionType.MOBILITY_DEGRADATION, DisruptionType.DUST_STORM_VISIBILITY)
        or (
            scenario.disruption_type == DisruptionType.COMPOUND_DISRUPTION
            and not has_spatial_hurdle
            and scenario.budget_reduction_pct is None
            and scenario.reduced_time_budget_s is None
            and scenario.reduced_max_distance_m is None
        )
    )
    if is_non_geometric:
        from marswalk.core.terrain import calculate_edge_cost
        new_cost = 0.0
        if baseline_route.path and len(baseline_route.path) > 1:
            for i in range(len(baseline_route.path) - 1):
                u = baseline_route.path[i]
                v = baseline_route.path[i + 1]
                c = calculate_edge_cost(u, v, terrain, config=scen_terrain_config)
                new_cost += c
        else:
            new_cost = baseline_route.cost

        scenario_route = RouteResult(
            profile=baseline_route.profile,
            start_rc=start_rc,
            goal_rc=goal_rc,
            path=list(baseline_route.path),
            distance_m=baseline_route.distance_m,
            cost=new_cost,
            science_score=baseline_route.science_score,
            visited_waypoint_ids=list(baseline_route.visited_waypoint_ids),
            num_cells=baseline_route.num_cells,
            num_steps=baseline_route.num_steps,
            is_reachable=baseline_route.is_reachable,
            is_budget_feasible=True,
            max_distance_m=scen_max_distance_m,
            status_message=f"Traverse evaluated under {scenario.name} (0 m geometric detour).",
            vehicle_mode=vehicle_mode,
            speed_multiplier=scen_speed_multiplier,
            legs=baseline_route.legs,
        )
        scenario_route.timeline = build_mission_timeline(
            scenario_route,
            vehicle_mode=vehicle_mode,
            dwell_time_per_stop_s=dwell_time_per_stop_s,
            operational_delay_s=scen_operational_delay_s,
            operational_limit_s=scen_operational_limit_s,
            speed_multiplier=scen_speed_multiplier,
            legs=baseline_route.legs,
        )
        dist_feas = (scen_max_distance_m is None) or (scenario_route.distance_m <= scen_max_distance_m)
        time_feas = scenario_route.timeline.is_within_limit if scenario_route.timeline else True
        scenario_route.is_budget_feasible = baseline_route.is_reachable and dist_feas and time_feas
        if not scenario_route.is_budget_feasible:
            scenario_route.status_message += f" Exceeds operational limits under {scenario.name}."
    elif ordered_points and len(ordered_points) >= 2:
        active_points = list(ordered_points)
        active_ids = list(stop_ids) if stop_ids else []
        active_priors = list(stop_priorities) if stop_priorities else []

        if scenario.unavailable_target_id:
            filt_pts = [active_points[0]]
            filt_ids = []
            filt_priors = []
            for idx, sid in enumerate(active_ids):
                if sid != scenario.unavailable_target_id:
                    filt_pts.append(active_points[idx + 1])
                    filt_ids.append(sid)
                    filt_priors.append(active_priors[idx])
            filt_pts.append(active_points[-1])
            active_points = filt_pts
            active_ids = filt_ids
            active_priors = filt_priors

        scenario_route = plan_sequential_multistop_route(
            ordered_points=active_points,
            terrain=terrain,
            stop_ids=active_ids,
            stop_priorities=active_priors,
            config=scen_planner_config,
            terrain_config=scen_terrain_config,
            blocked_mask=scen_blocked_mask,
            cost_multiplier_mask=scen_cost_multiplier_mask,
            vehicle_mode=vehicle_mode,
            dwell_time_per_stop_s=dwell_time_per_stop_s,
            operational_delay_s=scen_operational_delay_s,
            operational_limit_s=scen_operational_limit_s,
            speed_multiplier=scen_speed_multiplier,
        )
    else:
        scenario_route = plan_route(
            start_rc=start_rc,
            goal_rc=goal_rc,
            terrain=terrain,
            waypoints=scen_waypoints,
            config=scen_planner_config,
            terrain_config=scen_terrain_config,
            blocked_mask=scen_blocked_mask,
            cost_multiplier_mask=scen_cost_multiplier_mask,
            vehicle_mode=vehicle_mode,
            dwell_time_per_stop_s=dwell_time_per_stop_s,
            operational_delay_s=scen_operational_delay_s,
            operational_limit_s=scen_operational_limit_s,
            speed_multiplier=scen_speed_multiplier,
        )

    # Compute Science Regret Ledger
    ledger = compute_science_regret_ledger(
        baseline_route=baseline_route,
        scenario_route=scenario_route,
        waypoints=waypoints,
        scenario=scenario,
    )

    # Metrics comparison
    b_dist = baseline_route.distance_m
    s_dist = scenario_route.distance_m if scenario_route.is_reachable else float("nan")
    delta_d = (s_dist - b_dist) if scenario_route.is_reachable else float("nan")
    pct_d = (delta_d / b_dist * 100.0) if (b_dist > 0 and scenario_route.is_reachable) else None

    b_cost = baseline_route.cost
    s_cost = scenario_route.cost if scenario_route.is_reachable else float("nan")
    delta_c = (s_cost - b_cost) if scenario_route.is_reachable else float("nan")
    pct_c = (delta_c / b_cost * 100.0) if (b_cost > 0 and scenario_route.is_reachable) else None

    # Travel time comparison
    delta_t_s = (scenario_route.travel_time_s - baseline_route.travel_time_s) if (scenario_route.is_reachable and baseline_route.is_reachable) else 0.0
    if not scenario_route.is_reachable:
        fmt_delta_t = "—"
    elif delta_t_s > 0:
        fmt_delta_t = f"+{round(delta_t_s / 60.0)} min"
    elif delta_t_s < 0:
        fmt_delta_t = f"-{round(abs(delta_t_s) / 60.0)} min"
    else:
        fmt_delta_t = "0 min"

    headline, detail = generate_scenario_narrative(
        scenario=scenario,
        baseline_route=baseline_route,
        scenario_route=scenario_route,
        ledger=ledger,
        voice_mode=voice_mode,
    )

    # Compute Recovery Plan
    recovery_strat: Optional[str] = None
    recovery_route_res: Optional[RouteResult] = None
    rec_margin_s = 0.0
    rec_label = ""
    is_rec_recommended = False

    has_issue = (
        not scenario_route.is_reachable
        or not scenario_route.is_budget_feasible
        or delta_t_s > 0.0
        or (scenario.disruption_type == DisruptionType.TARGET_UNAVAILABLE and len(ledger.disabled_by_scenario_ids) > 0)
        or scenario.intersects_baseline
    )

    if has_issue:
        if ordered_points and len(ordered_points) > 2 and stop_ids and stop_priorities:
            # Try pruning candidates in increasing order of priority to restore feasibility
            sorted_indices = list(np.argsort(stop_priorities))
            for prune_candidate_idx in sorted_indices:
                pruned_name = stop_ids[prune_candidate_idx]
                rec_pts = [p for j, p in enumerate(ordered_points) if j != (prune_candidate_idx + 1)]
                rec_ids = [s for j, s in enumerate(stop_ids) if j != prune_candidate_idx]
                rec_priors = [p for j, p in enumerate(stop_priorities) if j != prune_candidate_idx]

                rec_cand = plan_sequential_multistop_route(
                    ordered_points=rec_pts,
                    terrain=terrain,
                    stop_ids=rec_ids,
                    stop_priorities=rec_priors,
                    config=scen_planner_config,
                    terrain_config=scen_terrain_config,
                    blocked_mask=scen_blocked_mask,
                    cost_multiplier_mask=scen_cost_multiplier_mask,
                    vehicle_mode=vehicle_mode,
                    dwell_time_per_stop_s=dwell_time_per_stop_s,
                    operational_delay_s=scen_operational_delay_s,
                    operational_limit_s=scen_operational_limit_s,
                    speed_multiplier=scen_speed_multiplier,
                )
                if rec_cand.is_reachable and rec_cand.is_budget_feasible:
                    recovery_route_res = rec_cand
                    recovery_strat = f"Bypass compromised stop ('{pruned_name}') to restore operational margin"
                    rec_label = f"Bypass {pruned_name}"
                    if scenario_route.is_reachable:
                        rec_margin_s = max(0.0, scenario_route.travel_time_s - rec_cand.travel_time_s)
                    else:
                        rec_margin_s = max(0.0, baseline_route.travel_time_s - rec_cand.travel_time_s)
                    is_rec_recommended = True
                    break

            # If pruning a single stop was insufficient, try direct conservative route to goal
            if recovery_route_res is None:
                rec_direct = plan_route(
                    start_rc=start_rc,
                    goal_rc=goal_rc,
                    terrain=terrain,
                    waypoints=[],
                    config=PlannerConfig(profile="conservative", max_distance_m=scen_max_distance_m),
                    terrain_config=scen_terrain_config,
                    blocked_mask=scen_blocked_mask,
                    cost_multiplier_mask=scen_cost_multiplier_mask,
                    vehicle_mode=vehicle_mode,
                    dwell_time_per_stop_s=dwell_time_per_stop_s,
                    operational_delay_s=scen_operational_delay_s,
                    operational_limit_s=scen_operational_limit_s,
                    speed_multiplier=scen_speed_multiplier,
                )
                if rec_direct.is_reachable and rec_direct.is_budget_feasible:
                    recovery_route_res = rec_direct
                    recovery_strat = "Bypass intermediate science stops; execute direct safe corridor to goal"
                    rec_label = "Direct Conservative Safe Return"
                    if scenario_route.is_reachable:
                        rec_margin_s = max(0.0, scenario_route.travel_time_s - rec_direct.travel_time_s)
                    else:
                        rec_margin_s = max(0.0, baseline_route.travel_time_s - rec_direct.travel_time_s)
                    is_rec_recommended = True
        else:
            # Direct conservative safe route for point-to-point missions
            rec_cand = plan_route(
                start_rc=start_rc,
                goal_rc=goal_rc,
                terrain=terrain,
                waypoints=[],
                config=PlannerConfig(profile="conservative", max_distance_m=scen_max_distance_m),
                terrain_config=scen_terrain_config,
                blocked_mask=scen_blocked_mask,
                cost_multiplier_mask=scen_cost_multiplier_mask,
                vehicle_mode=vehicle_mode,
                dwell_time_per_stop_s=dwell_time_per_stop_s,
                operational_delay_s=scen_operational_delay_s,
                operational_limit_s=scen_operational_limit_s,
                speed_multiplier=scen_speed_multiplier,
            )
            if rec_cand.is_reachable and rec_cand.is_budget_feasible:
                recovery_route_res = rec_cand
                recovery_strat = "Execute direct conservative return corridor to safely reach goal"
                rec_label = "Direct Conservative Safe Return"
                if not scenario_route.is_reachable:
                    rec_margin_s = max(0.0, baseline_route.travel_time_s)
                    is_rec_recommended = True
                elif not scenario_route.is_budget_feasible:
                    rec_margin_s = max(0.0, scenario_route.travel_time_s - rec_cand.travel_time_s)
                    is_rec_recommended = True
                elif rec_cand.travel_time_s < scenario_route.travel_time_s - 30.0:
                    rec_margin_s = max(0.0, scenario_route.travel_time_s - rec_cand.travel_time_s)
                    is_rec_recommended = True
                else:
                    rec_margin_s = 0.0
                    is_rec_recommended = False

    fmt_rec_margin = f"+{round(rec_margin_s / 60.0)} min" if rec_margin_s > 0 else "0 min"

    return ScenarioComparison(
        scenario=scenario,
        baseline_route=baseline_route,
        scenario_route=scenario_route,
        baseline_distance_m=b_dist,
        scenario_distance_m=s_dist,
        delta_distance_m=delta_d,
        pct_distance_change=pct_d,
        baseline_cost=b_cost,
        scenario_cost=s_cost,
        delta_cost=delta_c,
        pct_cost_change=pct_c,
        is_baseline_reachable=baseline_route.is_reachable,
        is_scenario_reachable=scenario_route.is_reachable,
        is_baseline_budget_feasible=baseline_route.is_budget_feasible,
        is_scenario_budget_feasible=scenario_route.is_budget_feasible,
        effective_budget_m=scen_max_distance_m,
        regret_ledger=ledger,
        headline=headline,
        detail=detail,
        voice_mode=voice_mode,
        delta_travel_time_s=delta_t_s,
        formatted_delta_travel_time=fmt_delta_t,
        recovery_strategy=recovery_strat,
        recovery_route=recovery_route_res,
        recovery_margin_recovered_s=rec_margin_s,
        formatted_recovery_margin=fmt_rec_margin,
        recovery_action_label=rec_label,
        is_recovery_recommended=is_rec_recommended,
    )


# ==============================================================================
# Bounded Route Toughness Test Suite
# ==============================================================================
def get_curated_gauntlet_scenarios(
    terrain: TerrainGrid,
    waypoints: List[ScienceWaypoint],
    baseline_distance_m: float,
    baseline_path: Optional[List[Tuple[int, int]]] = None,
    include_extended: bool = False,
) -> List[ScenarioDefinition]:
    """
    Construct a verified, bounded set of benchmark disruptions across the Jezero study area.
    Defaults to the 5 core benchmark scenarios for toughness suite consistency.
    When include_extended=True, returns the full suite of 13 scenarios (including sand,
    slope restrictions, mobility degradation, dust storm holds, and compound disruptions).
    """
    scenarios: List[ScenarioDefinition] = []

    # 1. Hawksbill Gap Scarp Rockfall (Blocks key ascent channel at r: 134..138, c: 89..93)
    hawksbill_cells: List[Tuple[int, int]] = []
    for r in range(134, 139):
        for c in range(89, 94):
            hawksbill_cells.append((r, c))

    scenarios.append(
        ScenarioDefinition(
            id="scen_hawksbill_rockfall",
            name="Hawksbill Gap Scarp Rockfall",
            disruption_type=DisruptionType.CORRIDOR_CLOSURE,
            description="Simulated localized regolith collapse in Hawksbill Gap, blocking primary delta ascent channel.",
            blocked_cells=hawksbill_cells,
            center_rc=(136, 91),
            radius_m=55.0,
        )
    )

    # 2. Central Delta Floor Channel Blockage (r: 112..118, c: 135..141)
    channel_cells: List[Tuple[int, int]] = []
    for r in range(112, 118):
        for c in range(135, 141):
            channel_cells.append((r, c))

    scenarios.append(
        ScenarioDefinition(
            id="scen_delta_channel_block",
            name="Crater Floor Dune Migration",
            disruption_type=DisruptionType.CORRIDOR_CLOSURE,
            description="Active aeolian megaripple migration creates untraversable sand sink on crater floor.",
            blocked_cells=channel_cells,
            center_rc=(115, 138),
            radius_m=65.0,
        )
    )

    # 3. 25% Distance Budget Curtailment
    scenarios.append(
        ScenarioDefinition(
            id="scen_budget_cut_25",
            name="Consumable Reserve Alert (-25% Budget)",
            disruption_type=DisruptionType.REDUCED_BUDGET,
            description="Early life-support margin buffer requires shortening max physical walking distance by 25%.",
            budget_reduction_pct=25.0,
        )
    )

    # 4. 40% Distance Budget Curtailment
    scenarios.append(
        ScenarioDefinition(
            id="scen_budget_cut_40",
            name="Life Support Abort Margin (-40% Budget)",
            disruption_type=DisruptionType.REDUCED_BUDGET,
            description="Suit thermal control anomaly demands rapid traverse completion under a 40% reduced distance ceiling.",
            budget_reduction_pct=40.0,
        )
    )

    # 5. Target Inaccessibility: First active waypoint or Three Forks
    target_to_disable = waypoints[0].id if waypoints else "three_forks"
    scenarios.append(
        ScenarioDefinition(
            id="scen_target_inaccessible",
            name=f"Environmental Hazard at {target_to_disable}",
            disruption_type=DisruptionType.TARGET_UNAVAILABLE,
            description=f"Surface telemetry flags severe slope instability surrounding target '{target_to_disable}'.",
            unavailable_target_id=target_to_disable,
        )
    )

    # Extended scenarios for interactive planning exploration & Milestone 9H
    if include_extended:
        # Dynamic mid-corridor coordinates from baseline path
        if baseline_path and len(baseline_path) >= 5:
            mid_idx = len(baseline_path) // 2
            mid_r, mid_c = baseline_path[mid_idx]
        else:
            mid_r, mid_c = 115, 138

        # 6. Scenario A: Traverse Corridor Rockfall (Direct Path Blockage - Guaranteed Detour)
        corridor_cells: List[Tuple[int, int]] = []
        for r in range(mid_r - 6, mid_r + 7):
            for c in range(mid_c - 6, mid_c + 7):
                if 0 <= r < terrain.height and 0 <= c < terrain.width:
                    corridor_cells.append((r, c))

        scenarios.append(
            ScenarioDefinition(
                id="scen_corridor_rockfall",
                name="Traverse Corridor Rockfall",
                disruption_type=DisruptionType.CORRIDOR_CLOSURE,
                description="Localized scarp rockfall directly obstructing the active traverse corridor, requiring an authentic lateral detour.",
                blocked_cells=corridor_cells,
                center_rc=(mid_r, mid_c),
                radius_m=120.0,
            )
        )

        # 7. Scenario B: Unstable Sand / Dune Migration (Cost multiplier across footprint)
        sand_cells: List[Tuple[int, int]] = []
        for r in range(mid_r - 4, mid_r + 5):
            for c in range(mid_c - 4, mid_c + 5):
                if 0 <= r < terrain.height and 0 <= c < terrain.width:
                    sand_cells.append((r, c))

        scenarios.append(
            ScenarioDefinition(
                id="scen_unstable_sand",
                name="Crater Floor Dune Migration & High-Slip Sand",
                disruption_type=DisruptionType.UNSTABLE_SAND,
                description="Active aeolian megaripple migration across traverse corridor. Imposes a 3.0× traversal effort multiplier due to severe wheel slip.",
                cost_multiplier_cells=sand_cells,
                cost_multiplier=3.0,
                center_rc=(mid_r, mid_c),
                radius_m=80.0,
            )
        )

        # 8. Scenario C: Newly Restricted Slope Corridor (Tightened slope threshold)
        scenarios.append(
            ScenarioDefinition(
                id="scen_restricted_slope",
                name="Restricted Slope Corridor (10.0° Cutoff)",
                disruption_type=DisruptionType.RESTRICTED_SLOPE,
                description="Mission flight rules tighten maximum traversable slope from 25.0° to 10.0° due to suspected unconsolidated regolith shear weakness.",
                max_slope_deg_override=10.0,
            )
        )

        # 9. Scenario D: Rover Mobility Degradation (0.5x speed, 1.5x slope effort, no fake detour)
        scenarios.append(
            ScenarioDefinition(
                id="scen_mobility_degradation",
                name="Drive Actuator Derating (0.5× Speed)",
                disruption_type=DisruptionType.MOBILITY_DEGRADATION,
                description="Traction motor thermal anomaly derates drive speed to 0.5× nominal and increases slope climbing strain (1.5× slope effort). Route geometry preserved.",
                speed_multiplier=0.5,
                slope_penalty_multiplier=1.5,
            )
        )

        # 10. Scenario E: Dust Storm / Reduced Visibility (0.6x speed, +30 min hold, no fake detour)
        scenarios.append(
            ScenarioDefinition(
                id="scen_dust_storm_visibility",
                name="Regional Dust Storm & Comms Hold",
                disruption_type=DisruptionType.DUST_STORM_VISIBILITY,
                description="Atmospheric tau increases significantly, reducing stereo vision drive speed to 0.6× and triggering a mandatory 30-minute comms verification hold.",
                speed_multiplier=0.6,
                operational_delay_s=1800.0,
            )
        )

        # 11. Compound Scenario 1: Rockfall + Mobility Degradation
        scenarios.append(
            ScenarioDefinition(
                id="scen_compound_rockfall_mobility",
                name="Compound: Rockfall + Mobility Derating",
                disruption_type=DisruptionType.COMPOUND_DISRUPTION,
                description="Cascading emergency: corridor rockfall forces lateral detour while simultaneous actuator derating cuts vehicle speed by 50%.",
                blocked_cells=corridor_cells,
                speed_multiplier=0.5,
                slope_penalty_multiplier=1.5,
                center_rc=(mid_r, mid_c),
                radius_m=120.0,
                compound_scenario_ids=["scen_corridor_rockfall", "scen_mobility_degradation"],
            )
        )

        # 12. Compound Scenario 2: Slope Restriction + Target Loss
        scenarios.append(
            ScenarioDefinition(
                id="scen_compound_slope_target_loss",
                name="Compound: Slope Restriction + Target Abort",
                disruption_type=DisruptionType.COMPOUND_DISRUPTION,
                description="Compound constraint: maximum traverse slope capped at 10.0° while environmental hazard forces aborting primary delta objective.",
                max_slope_deg_override=10.0,
                unavailable_target_id=target_to_disable,
                compound_scenario_ids=["scen_restricted_slope", "scen_target_inaccessible"],
            )
        )

        # 13. Distant Crater Rim Rockfall (Guaranteed No-Impact Control)
        distant_cells: List[Tuple[int, int]] = []
        for r in range(35, 40):
            for c in range(35, 40):
                if 0 <= r < terrain.height and 0 <= c < terrain.width:
                    distant_cells.append((r, c))

        scenarios.append(
            ScenarioDefinition(
                id="scen_distant_rockfall",
                name="Distant Crater Rim Rockfall",
                disruption_type=DisruptionType.CORRIDOR_CLOSURE,
                description="Hypothetical rockfall on northern crater rim; does not intersect active traverse corridor.",
                blocked_cells=distant_cells,
                center_rc=(37, 37),
                radius_m=50.0,
            )
        )

    return scenarios


def evaluate_route_toughness(
    baseline_route: RouteResult,
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    waypoints: List[ScienceWaypoint],
    terrain: TerrainGrid,
    scenarios: Optional[List[ScenarioDefinition]] = None,
    planner_config: Optional[PlannerConfig] = None,
    terrain_config: Optional[TerrainConfig] = None,
    vehicle_mode: str = "crew_eva",
) -> ToughnessReport:
    """
    Run the Route Toughness test evaluating a baseline traverse across the scenario suite.
    """
    if scenarios is None:
        scenarios = get_curated_gauntlet_scenarios(terrain, waypoints, baseline_route.distance_m, baseline_route.path)

    results: List[ToughnessScenarioResult] = []
    feasible_count = 0
    budget_met_count = 0
    dist_increases: List[float] = []
    retentions: List[float] = []

    for scen in scenarios:
        comp = run_scenario(
            baseline_route=baseline_route,
            scenario=scen,
            start_rc=start_rc,
            goal_rc=goal_rc,
            waypoints=waypoints,
            terrain=terrain,
            planner_config=planner_config,
            terrain_config=terrain_config,
            vehicle_mode=vehicle_mode,
        )

        res = comp.scenario_route
        is_reach = res.is_reachable
        is_budget_ok = res.is_budget_feasible
        retention = comp.regret_ledger.retention_pct

        if is_reach:
            feasible_count += 1
            delta_d = max(0.0, res.distance_m - baseline_route.distance_m)
            dist_increases.append(delta_d)
            if is_budget_ok:
                budget_met_count += 1
        else:
            delta_d = float("nan")

        retentions.append(retention)

        results.append(
            ToughnessScenarioResult(
                scenario=scen,
                is_reachable=is_reach,
                is_budget_feasible=is_budget_ok,
                distance_m=res.distance_m if is_reach else float("nan"),
                cost=res.cost if is_reach else float("inf"),
                science_score=res.science_score if is_reach else 0.0,
                delta_distance_m=delta_d,
                delta_cost=(res.cost - baseline_route.cost) if is_reach else float("nan"),
                retention_pct=retention,
            )
        )

    total = len(scenarios)
    max_d_inc = max(dist_increases) if dist_increases else 0.0
    min_ret = min(retentions) if retentions else 0.0
    avg_ret = (sum(retentions) / len(retentions)) if retentions else 0.0

    narrative = (
        f"Route Toughness Evaluation: {feasible_count}/{total} scenarios sustained feasible traverses. "
        f"{budget_met_count}/{total} met physical distance ceilings. "
        f"Maximum detour required: +{max_d_inc:.0f} m. "
        f"Mean scientific priority preserved across disruptions: {avg_ret:.1f}%."
    )

    return ToughnessReport(
        baseline_route=baseline_route,
        results=results,
        total_scenarios_tested=total,
        feasible_count=feasible_count,
        budget_met_count=budget_met_count,
        max_distance_increase_m=max_d_inc,
        min_retention_pct=min_ret,
        avg_retention_pct=avg_ret,
        summary_narrative=narrative,
    )


def run_scenario_sensitivity_sweep(
    baseline_route: RouteResult,
    scenario: ScenarioDefinition,
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    terrain: TerrainGrid,
    parameter_name: str,
    parameter_values: List[float],
    waypoints: Optional[List[ScienceWaypoint]] = None,
    planner_config: Optional[PlannerConfig] = None,
    vehicle_mode: str = "crew_eva",
    dwell_time_per_stop_s: float = 900.0,
    ordered_points: Optional[List[Tuple[int, int]]] = None,
    stop_ids: Optional[List[str]] = None,
    stop_priorities: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Execute a parameter sensitivity sweep experiment over a scenario parameter.
    Evaluates up to 8 discrete severity values using real deterministic A* re-computations.
    Returns structured sweep records and an auditable scientific sensitivity summary.
    """
    eval_values = list(parameter_values)[:8]
    sweep_records: List[Dict[str, Any]] = []

    for val in eval_values:
        val_f = float(val)
        scen_inst = replace(scenario)

        if parameter_name == "radius_m":
            scen_inst = replace(scen_inst, radius_m=val_f)
            if scenario.center_rc:
                cr, cc = scenario.center_rc
                cell_r = max(1, int(math.ceil(val_f / terrain.config.cell_size_m)))
                exempt_pts = set([start_rc, goal_rc] + (ordered_points or []))
                new_cells: List[Tuple[int, int]] = []
                for dr in range(-cell_r, cell_r + 1):
                    for dc in range(-cell_r, cell_r + 1):
                        if (dr * dr + dc * dc) <= (cell_r * cell_r):
                            rr = cr + dr
                            rc = cc + dc
                            if 0 <= rr < terrain.height and 0 <= rc < terrain.width:
                                if (rr, rc) not in exempt_pts:
                                    new_cells.append((rr, rc))
                if scenario.disruption_type == DisruptionType.CORRIDOR_CLOSURE:
                    scen_inst = replace(scen_inst, blocked_cells=new_cells)
                elif scenario.disruption_type == DisruptionType.UNSTABLE_SAND:
                    scen_inst = replace(scen_inst, cost_multiplier_cells=new_cells)
        elif parameter_name == "cost_multiplier":
            scen_inst = replace(scen_inst, cost_multiplier=val_f)
        elif parameter_name == "speed_multiplier":
            scen_inst = replace(scen_inst, speed_multiplier=val_f)
        elif parameter_name == "operational_delay_s":
            scen_inst = replace(scen_inst, operational_delay_s=val_f)
        elif parameter_name == "budget_reduction_pct":
            scen_inst = replace(scen_inst, budget_reduction_pct=val_f)
        elif parameter_name == "max_slope_deg_override":
            scen_inst = replace(scen_inst, max_slope_deg_override=val_f)

        comp = run_scenario(
            baseline_route=baseline_route,
            scenario=scen_inst,
            start_rc=start_rc,
            goal_rc=goal_rc,
            waypoints=waypoints,
            terrain=terrain,
            planner_config=planner_config,
            vehicle_mode=vehicle_mode,
            dwell_time_per_stop_s=dwell_time_per_stop_s,
            ordered_points=ordered_points,
            stop_ids=stop_ids,
            stop_priorities=stop_priorities,
        )

        b_dist = baseline_route.distance_m
        b_cost = baseline_route.cost
        s_dist = comp.scenario_distance_m
        s_cost = comp.scenario_cost
        d_dist = comp.delta_distance_m
        d_cost = comp.delta_cost

        is_reach = comp.is_scenario_reachable
        pct_d = (d_dist / b_dist * 100.0) if (b_dist > 0 and is_reach) else None
        pct_c = (d_cost / b_cost * 100.0) if (b_cost > 0 and is_reach) else None

        total_mission_s = (
            comp.scenario_route.timeline.total_mission_time_s
            if comp.scenario_route.timeline
            else comp.scenario_route.travel_time_s
        )
        sweep_records.append({
            "parameter_name": parameter_name,
            "parameter_value": val_f,
            "distance_m": round(s_dist, 2) if (is_reach and not math.isnan(s_dist)) else None,
            "delta_distance_m": round(d_dist, 2) if (is_reach and not math.isnan(d_dist)) else None,
            "pct_distance_change": round(pct_d, 1) if (is_reach and pct_d is not None and not math.isnan(pct_d)) else None,
            "cost": round(s_cost, 2) if (is_reach and not math.isnan(s_cost)) else None,
            "delta_cost": round(d_cost, 2) if (is_reach and not math.isnan(d_cost)) else None,
            "pct_cost_change": round(pct_c, 1) if (is_reach and pct_c is not None and not math.isnan(pct_c)) else None,
            "travel_time_s": round(comp.scenario_route.travel_time_s, 1) if is_reach else None,
            "delta_travel_time_s": round(comp.delta_travel_time_s, 1) if is_reach else None,
            "formatted_delta_travel_time": comp.formatted_delta_travel_time if is_reach else "—",
            "total_mission_time_s": round(total_mission_s, 1) if is_reach else None,
            "is_reachable": is_reach,
            "is_budget_feasible": comp.is_scenario_budget_feasible,
            "retention_pct": round(comp.regret_ledger.retention_pct, 1),
        })

    return {
        "disclaimer": "WHAT-IF SENSITIVITY EXPERIMENT. Not an operational risk forecast.",
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "parameter_name": parameter_name,
        "num_evaluations": len(sweep_records),
        "records": sweep_records,
    }
