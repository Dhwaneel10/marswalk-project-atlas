"""
MarsWalk Core Joint Mission Co-Design Engine.
Integrates terrain-aware traverse planning with RelayNet line-of-sight analysis,
relay network topology optimization, and dynamic communications digital twin evaluation.
Produces multi-objective trade-offs, Pareto frontier analysis, and decision explanations.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np

from marswalk.core.terrain import (
    TerrainConfig,
    TerrainGrid,
    calculate_edge_cost,
    calculate_step_distance,
    load_and_process_terrain,
    derive_terrain_from_array,
    MARS_RADIUS_M,
)
from marswalk.core.planner import (
    PlannerConfig,
    RouteResult,
    LegResult,
    ScienceWaypoint,
    astar_search,
    plan_route,
    calculate_traverse_time,
)
from marswalk.core.terrain_visibility import (
    DEFAULT_DX_M,
    DEFAULT_DY_M,
    LineOfSightResult,
    calculate_line_of_sight,
    sample_bilinear_elevation,
)
from marswalk.core.relay_graph import (
    LinkVisibilityStatus,
    RelayEdge,
    RelayNetworkGraph,
    RelayNode,
    RelayNodeType,
)
from marswalk.core.relay_planner import (
    optimize_relay_placement,
    screen_relay_candidates,
)
from marswalk.core.mission_connectivity import (
    ConnectivityCheckpoint,
    ConnectivityGapInterval,
    DynamicCommState,
    coalesce_gap_intervals,
    compute_mission_connectivity_timeline,
)
from marswalk.core.mission_resource_model import (
    RoverResourceConfig,
    RelayResourceConfig,
    MissionResourceLedger,
    ResourceFeasibilityClassification,
    evaluate_mission_resource_ledger,
    evaluate_resource_sensitivity,
    joules_to_wh,
)
from marswalk.core.mission_data_ledger import (
    DataCategory,
    DataProductStorageStatus,
    DataProductTransferStatus,
    MissionDataProduct,
    MissionDataLedger,
    PriorityType,
    RetentionPolicy,
    StoragePressureState,
)
from marswalk.core.science_mission_planner import (
    ScienceObjective,
    InstrumentId,
    InstrumentProfile,
    INSTRUMENT_CATALOG,
    ScienceTargetConfig,
    ScheduledObservationEvent,
    ScheduledTargetPlan,
    ScienceMissionPlanner,
)


# Canonical Objective Weights Profiles
OBJECTIVE_WEIGHT_PROFILES: Dict[str, Dict[str, float]] = {
    "balanced": {
        "distance": 0.20,
        "terrain_effort": 0.15,
        "slope_hazard": 0.15,
        "gap_ratio": 0.25,
        "max_gap": 0.10,
        "relay_budget": 0.10,
        "bridge_vulnerability": 0.05,
    },
    "mobility_first": {
        "distance": 0.35,
        "terrain_effort": 0.25,
        "slope_hazard": 0.20,
        "gap_ratio": 0.05,
        "max_gap": 0.05,
        "relay_budget": 0.05,
        "bridge_vulnerability": 0.05,
    },
    "connectivity_first": {
        "distance": 0.05,
        "terrain_effort": 0.05,
        "slope_hazard": 0.05,
        "gap_ratio": 0.45,
        "max_gap": 0.25,
        "relay_budget": 0.05,
        "bridge_vulnerability": 0.10,
    },
    "infrastructure_first": {
        "distance": 0.25,
        "terrain_effort": 0.20,
        "slope_hazard": 0.15,
        "gap_ratio": 0.05,
        "max_gap": 0.05,
        "relay_budget": 0.25,
        "bridge_vulnerability": 0.05,
    },
    "science_first": {
        "distance": 0.10,
        "terrain_effort": 0.10,
        "slope_hazard": 0.10,
        "gap_ratio": 0.15,
        "max_gap": 0.05,
        "relay_budget": 0.10,
        "bridge_vulnerability": 0.05,
        "science_return": 0.35,
    },
}

# Physical Reference Normalization Bounds
D_EUCLID_REF_MIN_M = 100.0
THETA_REF_DEG = 15.0
DELTA_THETA_MAX_DEG = 10.0
MAX_GAP_TOLERANCE_S = 900.0  # 15 min benchmark
K_MAX_DEFAULT = 3.0


@dataclass
class JointMissionInput:
    """Validated input parameters for joint mission co-design optimization."""
    start_rc: Tuple[int, int]
    goal_rc: Tuple[int, int]
    base_station: Dict[str, Any]
    waypoints: List[ScienceWaypoint] = field(default_factory=list)
    mobility_config: Dict[str, Any] = field(default_factory=dict)
    terrain_preference: str = "balanced"
    relay_budget: int = 2
    max_direct_range_m: float = 2500.0
    max_relay_range_m: float = 5000.0
    rover_antenna_h: float = 2.5
    base_antenna_h: float = 10.0
    relay_antenna_h: float = 10.0
    permitted_gap_distance_m: float = 0.0
    permitted_gap_duration_s: float = 0.0
    objective_profile: str = "balanced"
    custom_weights: Optional[Dict[str, float]] = None
    max_route_candidates: int = 5
    rover_resource_config: Optional[Dict[str, Any]] = None
    relay_resource_config: Optional[Dict[str, Any]] = None
    evaluate_resources: bool = True
    science_targets: Optional[List[Dict[str, Any]]] = None
    storage_capacity_bytes: int = 17_179_869_184
    simulated_transfer_rate_bps: float = 2_000_000.0
    retention_policy: str = "TRANSFER_THEN_RELEASE"


@dataclass
class CandidateTraverse:
    """A distinct candidate traverse route across the terrain."""
    traverse_id: str
    label: str
    strategy_description: str
    path_rc: List[Tuple[int, int]]
    distance_m: float
    elevation_gain_m: float
    elevation_loss_m: float
    mean_slope_deg: float
    max_slope_deg: float
    terrain_effort_m: float
    estimated_duration_s: float
    planner_profile: str
    is_valid: bool = True
    resource_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "traverse_id": self.traverse_id,
            "label": self.label,
            "strategy_description": self.strategy_description,
            "path_rc": self.path_rc,
            "path_length_cells": len(self.path_rc),
            "distance_m": round(self.distance_m, 2),
            "elevation_gain_m": round(self.elevation_gain_m, 2),
            "elevation_loss_m": round(self.elevation_loss_m, 2),
            "mean_slope_deg": round(self.mean_slope_deg, 2),
            "max_slope_deg": round(self.max_slope_deg, 2),
            "terrain_effort_m": round(self.terrain_effort_m, 2),
            "estimated_duration_s": round(self.estimated_duration_s, 1),
            "planner_profile": self.planner_profile,
            "is_valid": self.is_valid,
            "resource_summary": self.resource_summary,
        }


@dataclass
class RelayDeploymentConfig:
    """A deployed subset of surface relays."""
    config_id: str
    relays_deployed: List[Dict[str, Any]]
    relay_count: int
    is_connected_to_base: bool
    tarjan_bridges: List[Tuple[str, str]] = field(default_factory=list)
    cut_vertices: List[str] = field(default_factory=list)
    algebraic_connectivity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "relays_deployed": self.relays_deployed,
            "relay_count": self.relay_count,
            "is_connected_to_base": self.is_connected_to_base,
            "tarjan_bridges": self.tarjan_bridges,
            "cut_vertices": self.cut_vertices,
            "algebraic_connectivity": round(self.algebraic_connectivity, 4),
        }


@dataclass
class JointMissionMetrics:
    """Physical and normalized performance metrics for a joint mission configuration."""
    distance_m: float
    travel_time_s: float
    mean_slope_deg: float
    max_slope_deg: float
    elevation_gain_m: float
    elevation_loss_m: float
    terrain_effort_m: float
    connected_distance_m: float
    gap_distance_m: float
    gap_duration_s: float
    availability_pct: float
    max_gap_duration_s: float
    gap_count: int
    relay_count: int
    mean_hops: float
    max_hops: int
    critical_bridges: int
    energy_total_wh: float = 0.0
    energy_drive_wh: float = 0.0
    energy_idle_wh: float = 0.0
    energy_comms_wh: float = 0.0
    energy_science_wh: float = 0.0
    final_soc_pct: float = 100.0
    min_soc_pct: float = 100.0
    resource_feasibility: str = "FEASIBLE_WITHIN_CONFIGURED_BUDGET"
    science_points_total: float = 0.0
    data_generated_bytes: int = 0
    data_transferred_bytes: int = 0
    data_backlog_bytes: int = 0
    storage_peak_bytes: int = 0
    storage_pressure_state: str = "STORAGE_AVAILABLE"
    normalized_vector: Dict[str, float] = field(default_factory=dict)
    scalar_utility_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "physical_metrics": {
                "distance_m": round(self.distance_m, 2),
                "travel_time_s": round(self.travel_time_s, 1),
                "mean_slope_deg": round(self.mean_slope_deg, 2),
                "max_slope_deg": round(self.max_slope_deg, 2),
                "elevation_gain_m": round(self.elevation_gain_m, 2),
                "elevation_loss_m": round(self.elevation_loss_m, 2),
                "terrain_effort_m": round(self.terrain_effort_m, 2),
                "connected_distance_m": round(self.connected_distance_m, 2),
                "gap_distance_m": round(self.gap_distance_m, 2),
                "gap_duration_s": round(self.gap_duration_s, 1),
                "availability_pct": round(self.availability_pct, 2),
                "max_gap_duration_s": round(self.max_gap_duration_s, 1),
                "gap_count": self.gap_count,
                "relay_count": self.relay_count,
                "mean_hops": round(self.mean_hops, 2),
                "max_hops": self.max_hops,
                "critical_bridges": self.critical_bridges,
            },
            "resource_metrics": {
                "total_energy_wh": round(self.energy_total_wh, 2),
                "drive_energy_wh": round(self.energy_drive_wh, 2),
                "idle_energy_wh": round(self.energy_idle_wh, 2),
                "comms_energy_wh": round(self.energy_comms_wh, 2),
                "science_energy_wh": round(self.energy_science_wh, 2),
                "final_soc_pct": round(self.final_soc_pct, 2),
                "min_soc_pct": round(self.min_soc_pct, 2),
                "feasibility": self.resource_feasibility,
            },
            "science_metrics": {
                "science_points_total": round(self.science_points_total, 1),
                "data_generated_bytes": self.data_generated_bytes,
                "data_generated_mb": round(self.data_generated_bytes / (1024 * 1024), 2),
                "data_transferred_bytes": self.data_transferred_bytes,
                "data_transferred_mb": round(self.data_transferred_bytes / (1024 * 1024), 2),
                "data_backlog_bytes": self.data_backlog_bytes,
                "data_backlog_mb": round(self.data_backlog_bytes / (1024 * 1024), 2),
                "storage_peak_bytes": self.storage_peak_bytes,
                "storage_peak_mb": round(self.storage_peak_bytes / (1024 * 1024), 2),
                "storage_pressure_state": self.storage_pressure_state,
            },
            "normalized_vector": {k: round(v, 4) for k, v in self.normalized_vector.items()},
            "scalar_utility_score": round(self.scalar_utility_score, 4),
        }


@dataclass
class JointMissionConfiguration:
    """A complete coupled mission co-design pairing a traverse and relay deployment."""
    configuration_id: str
    traverse: CandidateTraverse
    relays: RelayDeploymentConfig
    metrics: JointMissionMetrics
    timeline_summary: Dict[str, Any]
    timeline_gap_intervals: List[Dict[str, Any]]
    is_pareto_optimal: bool = False
    constraint_violations: List[str] = field(default_factory=list)
    recommendation_tier: str = "FEASIBLE_SUBOPTIMAL"
    resource_ledger: Optional[Dict[str, Any]] = None
    science_plan: Optional[Dict[str, Any]] = None
    data_ledger: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "configuration_id": self.configuration_id,
            "traverse": self.traverse.to_dict(),
            "relays": self.relays.to_dict(),
            "metrics": self.metrics.to_dict(),
            "timeline_summary": self.timeline_summary,
            "timeline_gap_intervals": self.timeline_gap_intervals,
            "is_pareto_optimal": self.is_pareto_optimal,
            "constraint_violations": self.constraint_violations,
            "recommendation_tier": self.recommendation_tier,
            "resource_ledger": self.resource_ledger,
            "science_plan": self.science_plan,
            "data_ledger": self.data_ledger,
        }


@dataclass
class DecisionExplanation:
    """Explainable rationale detailing why a co-design configuration was selected."""
    summary: str
    selection_rationale: str
    terrain_trade_offs: str
    connectivity_resolution: str
    rejected_alternatives_comparison: List[str]
    marginal_rates_of_substitution: Dict[str, float]
    assumptions_and_limitations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "selection_rationale": self.selection_rationale,
            "terrain_trade_offs": self.terrain_trade_offs,
            "connectivity_resolution": self.connectivity_resolution,
            "rejected_alternatives_comparison": self.rejected_alternatives_comparison,
            "marginal_rates_of_substitution": {k: round(v, 4) for k, v in self.marginal_rates_of_substitution.items()},
            "assumptions_and_limitations": self.assumptions_and_limitations,
        }


@dataclass
class JointMissionOptimizationResult:
    """Comprehensive result of joint traverse and relay co-design optimization."""
    result_id: str
    timestamp_utc: str
    sha256_fingerprint: str
    input_parameters: Dict[str, Any]
    candidate_traverses: List[CandidateTraverse]
    candidate_relay_pool: List[Dict[str, Any]]
    all_configurations: List[JointMissionConfiguration]
    pareto_frontier: List[JointMissionConfiguration]
    recommended_configuration: JointMissionConfiguration
    decision_explanation: DecisionExplanation
    search_bounds: Dict[str, Any]
    provenance: Dict[str, Any]
    resource_sensitivity: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "timestamp_utc": self.timestamp_utc,
            "sha256_fingerprint": self.sha256_fingerprint,
            "input_parameters": self.input_parameters,
            "candidate_traverses": [t.to_dict() for t in self.candidate_traverses],
            "candidate_relay_pool": self.candidate_relay_pool,
            "configurations_evaluated": len(self.all_configurations),
            "pareto_configurations_count": len(self.pareto_frontier),
            "pareto_frontier": [c.to_dict() for c in self.pareto_frontier],
            "recommended_configuration": self.recommended_configuration.to_dict(),
            "decision_explanation": self.decision_explanation.to_dict(),
            "search_bounds": self.search_bounds,
            "provenance": self.provenance,
            "resource_sensitivity": self.resource_sensitivity,
        }


# ==============================================================================
# 1. Validation & Input Normalization
# ==============================================================================

def validate_joint_mission_input(
    inp: Dict[str, Any],
    terrain: Optional[TerrainGrid] = None,
) -> JointMissionInput:
    """
    Validate input parameters against terrain dimensions and operational constraints.
    Rejects out-of-bounds, non-finite values, and invalid NoData coordinates.
    """
    if "start_rc" not in inp or "goal_rc" not in inp:
        raise ValueError("Missing required start_rc or goal_rc coordinates.")

    start_rc = tuple(inp["start_rc"])
    goal_rc = tuple(inp["goal_rc"])

    if len(start_rc) != 2 or len(goal_rc) != 2:
        raise ValueError("start_rc and goal_rc must be 2-tuples of (row, col).")

    if not all(isinstance(x, (int, np.integer)) for x in start_rc + goal_rc):
        raise ValueError("Coordinates must be integer grid indices.")

    # Base Station validation
    base_station = inp.get("base_station")
    if not base_station or not isinstance(base_station, dict):
        base_station = {
            "name": "Octavia E. Butler Landing Base",
            "row": int(start_rc[0]),
            "col": int(start_rc[1]),
            "antenna_height_m": float(inp.get("antenna_mast_base_m", inp.get("base_antenna_h", 10.0)))
        }

    base_rc = (int(base_station.get("row", start_rc[0])), int(base_station.get("col", start_rc[1])))

    # Terrain Bounds Check if terrain is supplied
    if terrain is not None:
        rows, cols = terrain.elevation.shape
        for pt, label in [(start_rc, "start_rc"), (goal_rc, "goal_rc"), (base_rc, "base_station")]:
            r, c = pt
            if not (0 <= r < rows and 0 <= c < cols):
                raise ValueError(f"{label} ({r}, {c}) is outside terrain grid bounds (0..{rows-1}, 0..{cols-1}).")
            if terrain.invalid_mask[r, c]:
                raise ValueError(f"{label} ({r}, {c}) is located in an invalid or NoData terrain cell.")

    relay_budget = int(inp.get("relay_budget", inp.get("max_relays_budget", 2)))
    if not (0 <= relay_budget <= 3):
        raise ValueError(f"relay_budget ({relay_budget}) must be between 0 and 3.")

    max_direct_range_m = float(inp.get("max_direct_range_m", 2500.0))
    max_relay_range_m = float(inp.get("max_relay_range_m", 5000.0))
    if max_direct_range_m <= 0 or max_relay_range_m <= 0:
        raise ValueError("Communication ranges must be positive non-zero values.")

    rover_antenna_h = float(inp.get("rover_antenna_h", inp.get("antenna_mast_rover_m", 2.5)))
    base_antenna_h = float(inp.get("base_antenna_h", inp.get("antenna_mast_base_m", 10.0)))
    relay_antenna_h = float(inp.get("relay_antenna_h", inp.get("antenna_mast_relay_m", 10.0)))

    profile = inp.get("objective_profile", "balanced")
    if profile not in OBJECTIVE_WEIGHT_PROFILES and profile != "custom":
        profile = "balanced"

    custom_weights = inp.get("custom_weights", inp.get("weights"))
    if custom_weights and isinstance(custom_weights, dict):
        s = sum(custom_weights.values())
        if s > 0:
            custom_weights = {k: v / s for k, v in custom_weights.items()}

    waypoints_raw = inp.get("waypoints", inp.get("intermediate_waypoints", []))
    waypoints: List[ScienceWaypoint] = []
    for w in waypoints_raw:
        if isinstance(w, ScienceWaypoint):
            waypoints.append(w)
        elif isinstance(w, dict):
            w_rc = (w.get("row", 0), w.get("col", 0))
            waypoints.append(
                ScienceWaypoint(
                    id=str(w.get("id", f"WP_{len(waypoints)+1}")),
                    name=str(w.get("name", "Science Target")),
                    rc=w_rc,
                    priority_score=float(w.get("priority_score", 50.0)),
                )
            )

    return JointMissionInput(
        start_rc=start_rc,
        goal_rc=goal_rc,
        base_station=base_station,
        waypoints=waypoints,
        mobility_config=inp.get("mobility_config", {}),
        terrain_preference=inp.get("terrain_preference", "balanced"),
        relay_budget=relay_budget,
        max_direct_range_m=max_direct_range_m,
        max_relay_range_m=max_relay_range_m,
        rover_antenna_h=rover_antenna_h,
        base_antenna_h=base_antenna_h,
        relay_antenna_h=relay_antenna_h,
        permitted_gap_distance_m=float(inp.get("permitted_gap_distance_m", 0.0)),
        permitted_gap_duration_s=float(inp.get("permitted_gap_duration_s", 0.0)),
        objective_profile=profile,
        custom_weights=custom_weights,
        max_route_candidates=int(inp.get("max_route_candidates", 5)),
        rover_resource_config=inp.get("rover_resource_config"),
        relay_resource_config=inp.get("relay_resource_config"),
        evaluate_resources=bool(inp.get("evaluate_resources", True)),
    )


# ==============================================================================
# 2. Alternative Traverse Generation
# ==============================================================================

def generate_candidate_traverses(
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    terrain: TerrainGrid,
    waypoints: Optional[List[ScienceWaypoint]] = None,
    max_candidates: int = 5,
    candidate_promontories: Optional[List[Dict[str, Any]]] = None,
) -> List[CandidateTraverse]:
    """
    Generate a bounded portfolio of meaningfully distinct, physically valid traverse routes.
    Employs diverse slope penalty weights, critical slope cutoffs, and topological waypoints.
    """
    dx = terrain.dx_ground_m if terrain.dx_ground_m else DEFAULT_DX_M
    dy = terrain.dy_ground_m if terrain.dy_ground_m else DEFAULT_DY_M

    candidates: List[CandidateTraverse] = []

    # 1. Strategy 1: Direct Euclidean (Least Odometer Distance)
    cfg_direct = TerrainConfig(alpha_s=0.5, theta_crit_deg=18.0, theta_max_deg=25.0, alpha_r=0.0, alpha_up=0.5)
    leg_direct = astar_search(start_rc, goal_rc, terrain, terrain_config=cfg_direct)
    if leg_direct.is_reachable and len(leg_direct.path) > 1:
        candidates.append(_build_candidate_traverse("TRV_01_DIRECT", "Direct Traverse (Least-Distance)", "Minimizes pure geodetic travel distance with relaxed slope tolerance.", leg_direct.path, leg_direct.cost, terrain, "direct"))

    # 2. Strategy 2: Conservative Valley Route (Slope-Avoiding Plain)
    cfg_cons = TerrainConfig(alpha_s=6.0, theta_crit_deg=8.0, theta_max_deg=14.0, alpha_r=1.5, alpha_up=2.5)
    leg_cons = astar_search(start_rc, goal_rc, terrain, terrain_config=cfg_cons)
    if leg_cons.is_reachable and len(leg_cons.path) > 1:
        candidates.append(_build_candidate_traverse("TRV_02_CONSERVATIVE", "Conservative Traverse (Low-Hazard)", "Maximizes safety by detouring around steep crater walls and high slopes.", leg_cons.path, leg_cons.cost, terrain, "conservative"))

    # 3. Strategy 3: Standard Balanced Route
    cfg_bal = TerrainConfig(alpha_s=2.0, theta_crit_deg=10.0, theta_max_deg=22.0, alpha_r=1.0, alpha_up=1.5)
    leg_bal = astar_search(start_rc, goal_rc, terrain, terrain_config=cfg_bal)
    if leg_bal.is_reachable and len(leg_bal.path) > 1:
        candidates.append(_build_candidate_traverse("TRV_03_BALANCED", "Balanced Traverse (Nominal Optimization)", "Standard Apollo Waligora metabolic cost trade-off between slope and distance.", leg_bal.path, leg_bal.cost, terrain, "balanced"))

    # 4. Strategy 4: High-Vantage Promontory Pass (Comms-Biased Skyline)
    # If candidate promontories are available, find one near the path midpoint to route through
    mid_r = (start_rc[0] + goal_rc[0]) // 2
    mid_c = (start_rc[1] + goal_rc[1]) // 2

    prom_pass_found = False
    if candidate_promontories:
        # Find closest feasible promontory to midpoint
        best_prom = min(
            candidate_promontories,
            key=lambda p: math.hypot((p["col"] - mid_c) * dx, (p["row"] - mid_r) * dy)
        )
        pr_rc = (best_prom["row"], best_prom["col"])
        if pr_rc != start_rc and pr_rc != goal_rc and not terrain.invalid_mask[pr_rc]:
            wp_prom = ScienceWaypoint(id="WP_PROMONTORY_PASS", name="High-Vantage Promontory Saddle", rc=pr_rc, priority_score=90.0)
            res_prom = plan_route(start_rc, goal_rc, terrain, waypoints=[wp_prom], config=PlannerConfig(profile="balanced"))
            if res_prom.is_reachable and len(res_prom.path) > 1:
                candidates.append(_build_candidate_traverse("TRV_04_PROMONTORY_PASS", "High-Vantage Promontory Route", "Routes across intermediate ridge saddle to preserve elevated line of sight.", res_prom.path, res_prom.cost, terrain, "promontory_pass"))
                prom_pass_found = True

    if not prom_pass_found:
        # Synthesize a topological offset waypoint perpendicular to baseline
        dr = goal_rc[0] - start_rc[0]
        dc = goal_rc[1] - start_rc[1]
        offset_r = int(mid_r - 0.25 * dc)
        offset_c = int(mid_c + 0.25 * dr)
        rows, cols = terrain.elevation.shape
        offset_r = max(2, min(rows - 3, offset_r))
        offset_c = max(2, min(cols - 3, offset_c))
        if not terrain.invalid_mask[offset_r, offset_c]:
            wp_off = ScienceWaypoint(id="WP_OFFSET_RIDGE", name="Topological Lateral Offset", rc=(offset_r, offset_c), priority_score=80.0)
            res_off = plan_route(start_rc, goal_rc, terrain, waypoints=[wp_off], config=PlannerConfig(profile="conservative"))
            if res_off.is_reachable and len(res_off.path) > 1:
                candidates.append(_build_candidate_traverse("TRV_04_LATERAL_DETOUR", "Topological Lateral Detour", "Navigates around terrain obstructions via lateral flank detour.", res_off.path, res_off.cost, terrain, "lateral_detour"))

    # 5. Strategy 5: Science Waypoints Tour (if provided)
    if waypoints and len(waypoints) > 0:
        res_sci = plan_route(start_rc, goal_rc, terrain, waypoints=waypoints, config=PlannerConfig(profile="science_first"))
        if res_sci.is_reachable and len(res_sci.path) > 1:
            candidates.append(_build_candidate_traverse("TRV_05_SCIENCE_TOUR", "Science-Targeted Traverse", "Maximizes science sampling value across intermediate exploration waypoints.", res_sci.path, res_sci.cost, terrain, "science_first"))

    # Deduplicate candidate traverses
    unique_traverses = deduplicate_traverses(candidates, max_overlap_ratio=0.85)
    return unique_traverses[:max_candidates]


def _build_candidate_traverse(
    t_id: str,
    label: str,
    desc: str,
    path: List[Tuple[int, int]],
    cost: float,
    terrain: TerrainGrid,
    profile: str,
) -> CandidateTraverse:
    """Compute physical metrics along a traverse path."""
    dx = terrain.dx_ground_m if terrain.dx_ground_m else DEFAULT_DX_M
    dy = terrain.dy_ground_m if terrain.dy_ground_m else DEFAULT_DY_M

    dist_m = 0.0
    gain_m = 0.0
    loss_m = 0.0
    slopes: List[float] = []

    for i in range(len(path) - 1):
        r0, c0 = path[i]
        r1, c1 = path[i + 1]
        step_d = math.hypot((c1 - c0) * dx, (r1 - r0) * dy)
        dist_m += step_d

        z0 = float(terrain.elevation[r0, c0])
        z1 = float(terrain.elevation[r1, c1])
        dz = z1 - z0
        if dz > 0:
            gain_m += dz
        else:
            loss_m += abs(dz)

        slopes.append(float(terrain.slope_deg[r1, c1]))

    mean_slope = float(np.mean(slopes)) if slopes else 0.0
    max_slope = float(np.max(slopes)) if slopes else 0.0
    est_dur_s = dist_m / 0.55  # nominal rover speed 0.55 m/s

    return CandidateTraverse(
        traverse_id=t_id,
        label=label,
        strategy_description=desc,
        path_rc=path,
        distance_m=dist_m,
        elevation_gain_m=gain_m,
        elevation_loss_m=loss_m,
        mean_slope_deg=mean_slope,
        max_slope_deg=max_slope,
        terrain_effort_m=cost,
        estimated_duration_s=est_dur_s,
        planner_profile=profile,
        is_valid=True,
    )


def deduplicate_traverses(
    traverses: List[CandidateTraverse],
    max_overlap_ratio: float = 0.85,
) -> List[CandidateTraverse]:
    """
    Remove materially identical traverse candidates based on Jaccard grid overlap.
    Retains the lower-cost candidate when overlap exceeds threshold.
    """
    if len(traverses) <= 1:
        return traverses

    kept: List[CandidateTraverse] = []

    for cand in traverses:
        cand_set = set(cand.path_rc)
        is_duplicate = False

        for k in kept:
            k_set = set(k.path_rc)
            inter = len(cand_set.intersection(k_set))
            union = len(cand_set.union(k_set))
            jaccard = inter / union if union > 0 else 1.0

            if jaccard >= max_overlap_ratio:
                is_duplicate = True
                break

        if not is_duplicate:
            kept.append(cand)

    return kept


def evaluate_science_and_data_logistics(
    path_rc: List[Tuple[int, int]],
    trajectory_points: List[Tuple[float, int, int]],
    checkpoints: List[Dict[str, Any]],
    science_targets: Optional[List[Union[ScienceTargetConfig, Dict[str, Any]]]] = None,
    rover_resource_config: Optional[Union[RoverResourceConfig, Dict[str, Any]]] = None,
    storage_capacity_bytes: int = 17_179_869_184,
    simulated_transfer_rate_bps: float = 2_000_000.0,
    retention_policy: str = "TRANSFER_THEN_RELEASE",
) -> Tuple[float, int, int, int, int, str, float, Dict[str, Any], Dict[str, Any], List[str]]:
    """
    Evaluates in-situ science observations and onboard data logistics along a traverse.
    """
    if not science_targets:
        empty_ledger = MissionDataLedger(
            capacity_bytes=storage_capacity_bytes,
            configured_transfer_rate_bps=simulated_transfer_rate_bps,
        )
        return 0.0, 0, 0, 0, 0, "STORAGE_AVAILABLE", 0.0, {}, empty_ledger.to_dict(), []

    # 1. Parse targets
    parsed_targets: List[ScienceTargetConfig] = []
    for st in science_targets:
        if isinstance(st, ScienceTargetConfig):
            parsed_targets.append(st)
        elif isinstance(st, dict):
            p_score = float(st.get("priority_score", 50.0))
            p_type_val = st.get("priority_type", PriorityType.USER_ASSIGNED_PRIORITY.value)
            try:
                p_type = PriorityType(p_type_val)
            except ValueError:
                p_type = PriorityType.USER_ASSIGNED_PRIORITY
            obj_val = st.get("primary_objective", ScienceObjective.GEOLOGICAL_CHARACTERIZATION.value)
            try:
                obj = ScienceObjective(obj_val)
            except ValueError:
                obj = ScienceObjective.GEOLOGICAL_CHARACTERIZATION
            modes_val = st.get("selected_modes")
            if modes_val is None:
                default_modes = ["MASTCAM_Z_PANO"] if obj == ScienceObjective.GEOLOGICAL_CHARACTERIZATION else ["MASTCAM_Z_STEREO"]
            else:
                default_modes = list(modes_val)
            parsed_targets.append(
                ScienceTargetConfig(
                    target_id=str(st.get("target_id", f"target_{len(parsed_targets)+1}")),
                    target_name=str(st.get("target_name", st.get("name", "Target"))),
                    grid_coord=(int(st.get("grid_coord", [0, 0])[0]), int(st.get("grid_coord", [0, 0])[1])),
                    priority_score=p_score,
                    priority_type=p_type,
                    primary_objective=obj,
                    selected_modes=default_modes,
                    prerequisites=list(st.get("prerequisites", [])),
                    source_citation=str(st.get("source_citation", "")),
                    is_protected=bool(st.get("is_protected", False)),
                )
            )

    # 2. Match targets to arrival times along path
    target_arrival_times: List[float] = []
    scheduled_targets: List[ScienceTargetConfig] = []

    for t in parsed_targets:
        tr, tc = t.grid_coord
        min_dist_sq = float("inf")
        closest_idx = 0
        for idx, (pr, pc) in enumerate(path_rc):
            d_sq = (pr - tr) ** 2 + (pc - tc) ** 2
            if d_sq < min_dist_sq:
                min_dist_sq = d_sq
                closest_idx = idx

        if closest_idx < len(trajectory_points):
            arr_t = trajectory_points[closest_idx][0]
        else:
            arr_t = trajectory_points[-1][0] if trajectory_points else 0.0

        scheduled_targets.append(t)
        target_arrival_times.append(arr_t)

    # 3. Setup Ledger and Planner
    if isinstance(rover_resource_config, dict):
        valid_keys = {f.name for f in RoverResourceConfig.__dataclass_fields__.values()}
        rcfg = RoverResourceConfig(**{k: v for k, v in rover_resource_config.items() if k in valid_keys})
    elif isinstance(rover_resource_config, RoverResourceConfig):
        rcfg = rover_resource_config
    else:
        rcfg = RoverResourceConfig()

    ledger = MissionDataLedger(
        capacity_bytes=storage_capacity_bytes,
        configured_transfer_rate_bps=simulated_transfer_rate_bps,
        strict_capacity_enforcement=False,
    )
    planner = ScienceMissionPlanner(rover_config=rcfg, data_ledger=ledger)

    # 4. Schedule observations
    target_plans = planner.schedule_full_mission(
        targets=scheduled_targets,
        traverse_arrival_times_s=target_arrival_times,
    )

    # 5. Simulate Transfer Windows along connected checkpoints
    connected_windows: List[Tuple[float, float]] = []
    window_start: Optional[float] = None
    last_t: float = 0.0

    for cp in checkpoints:
        t_s = float(cp.get("time_s", 0.0))
        st = cp.get("state", "GAP")
        is_conn = st in ("CONNECTED_DIRECT", "CONNECTED_RELAYED")
        if is_conn:
            if window_start is None:
                window_start = t_s
            last_t = t_s
        else:
            if window_start is not None:
                connected_windows.append((window_start, last_t))
                window_start = None
    if window_start is not None:
        connected_windows.append((window_start, last_t))

    for w_start, w_end in connected_windows:
        w_dur = max(0.0, w_end - w_start)
        if w_dur > 0:
            ledger.simulate_transfer_window(
                start_time_s=w_start,
                duration_s=w_dur,
                network_path=["ROVER", "SURFACE_BASE_STATION"],
                policy="PRIORITY_FIRST",
            )
            if retention_policy == "TRANSFER_THEN_RELEASE":
                ledger.release_all_eligible_storage(current_time_s=w_end)

    # 6. Peak storage and pressure state
    peak_storage = max((e.used_bytes for e in ledger.ledger_history), default=ledger.used_bytes)
    pressure_state = ledger.get_storage_pressure_state().value

    violations: List[str] = []
    if peak_storage > storage_capacity_bytes:
        violations.append("STORAGE_CAPACITY_EXCEEDED")

    sci_points_total = sum(p.science_points_awarded for p in target_plans)
    sci_energy_wh = sum(p.total_energy_consumed_wh for p in target_plans)
    data_gen_bytes = ledger.cumulative_generated_bytes
    data_xfer_bytes = ledger.cumulative_transferred_bytes
    data_backlog = ledger.backlog_bytes

    science_plan_dict = {
        "targets_scheduled_count": len(target_plans),
        "total_dwell_s": sum(p.total_dwell_s for p in target_plans),
        "total_energy_consumed_wh": round(sci_energy_wh, 2),
        "science_points_awarded": round(sci_points_total, 1),
        "targets": [p.to_dict() for p in target_plans],
    }

    return (
        sci_points_total,
        data_gen_bytes,
        data_xfer_bytes,
        data_backlog,
        peak_storage,
        pressure_state,
        sci_energy_wh,
        science_plan_dict,
        ledger.to_dict(),
        violations,
    )


# ==============================================================================
# 3. Communications-Aware Route Evaluation & Relay Infrastructure
# ==============================================================================

def evaluate_traverse_connectivity_with_relays(
    traverse: CandidateTraverse,
    base_node: RelayNode,
    deployed_relays: List[RelayNode],
    terrain: TerrainGrid,
    max_direct_range_m: float = 2500.0,
    max_relay_range_m: float = 5000.0,
    rover_antenna_h: float = 2.5,
    sampling_interval_s: float = 10.0,
    rover_resource_config: Optional[Union[RoverResourceConfig, Dict[str, Any]]] = None,
    relay_resource_config: Optional[Union[RelayResourceConfig, Dict[str, Any]]] = None,
    waypoints: Optional[List[ScienceWaypoint]] = None,
    evaluate_resources: bool = True,
    return_ledger: bool = False,
    science_targets: Optional[List[Union[ScienceTargetConfig, Dict[str, Any]]]] = None,
    storage_capacity_bytes: int = 17_179_869_184,
    simulated_transfer_rate_bps: float = 2_000_000.0,
    retention_policy: str = "TRANSFER_THEN_RELEASE",
) -> Union[Tuple[JointMissionMetrics, Dict[str, Any], List[Dict[str, Any]]], Tuple[JointMissionMetrics, Dict[str, Any], List[Dict[str, Any]], Dict[str, Any], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]]:
    """
    Evaluate communications continuity for a traverse coupled with a specific relay set.
    Computes exact gap intervals, availability percentage, hop counts, and graph robustness.
    """
    dx = terrain.dx_ground_m if terrain.dx_ground_m else DEFAULT_DX_M
    dy = terrain.dy_ground_m if terrain.dy_ground_m else DEFAULT_DY_M

    # Convert path into timestamped trajectory points (t_s, r, c)
    path = traverse.path_rc
    total_dist = traverse.distance_m
    total_dur = traverse.estimated_duration_s

    # Build trajectory checkpoints
    trajectory_points: List[Tuple[float, int, int]] = []
    cum_d = 0.0

    for i, (r, c) in enumerate(path):
        if i > 0:
            pr, pc = path[i - 1]
            cum_d += math.hypot((c - pc) * dx, (r - pr) * dy)
        t_frac = cum_d / total_dist if total_dist > 0 else 0.0
        t_s = t_frac * total_dur
        trajectory_points.append((t_s, r, c))

    # Base Station RelayNode dict conversion for mission_connectivity
    base_dict = {
        "id": base_node.node_id,
        "rc": (base_node.rc[0], base_node.rc[1]),
        "antenna_h": base_node.antenna_height_m,
    }

    relays_dicts = [
        {
            "id": r.node_id,
            "rc": (r.rc[0], r.rc[1]),
            "antenna_h": r.antenna_height_m,
        }
        for r in deployed_relays
    ]

    # Invoke RelayNet dynamic mission connectivity timeline engine
    timeline_res = compute_mission_connectivity_timeline(
        elevation=terrain.elevation,
        trajectory_points=trajectory_points,
        base_station=base_dict,
        relays=relays_dicts,
        direct_range_m=max_direct_range_m,
        relay_range_m=max_relay_range_m,
        rover_antenna_h_m=rover_antenna_h,
        dx_ground_m=dx,
        dy_ground_m=dy,
        invalid_mask=terrain.invalid_mask,
    )

    summary = timeline_res.get("summary", {})
    gap_intervals = timeline_res.get("gap_intervals", [])

    gap_dist_m = float(summary.get("total_gap_distance_m", 0.0))
    gap_dur_s = float(summary.get("total_gap_duration_s", 0.0))
    max_gap_s = float(summary.get("max_consecutive_gap_s", 0.0))
    avail_pct = float(summary.get("availability_pct", 100.0))
    gap_cnt = int(summary.get("gap_count", len(gap_intervals)))
    conn_dist_m = max(0.0, total_dist - gap_dist_m)

    # Build Graph for Relay Infrastructure Robustness Metrics
    graph = RelayNetworkGraph(r_max_m=max_relay_range_m)
    graph.add_node(base_node)
    for r in deployed_relays:
        graph.add_node(r)

    # Add edges between Base and Relays
    for r in deployed_relays:
        los_base = calculate_line_of_sight(
            terrain.elevation,
            (base_node.rc[0], base_node.rc[1]),
            (r.rc[0], r.rc[1]),
            base_node.antenna_height_m,
            r.antenna_height_m,
            max_range_m=max_relay_range_m,
            dx_m=dx,
            dy_m=dy,
        )
        if los_base.is_visible:
            edge = RelayEdge(
                u=base_node.node_id,
                v=r.node_id,
                distance_m=los_base.distance_m,
                slant_range_m=los_base.distance_m,
                visibility=LinkVisibilityStatus.VISIBLE if los_base.is_visible else LinkVisibilityStatus.BLOCKED,
                min_clearance_m=los_base.min_clearance_m,
                num_hops=1,
                propagation_delay_us=(los_base.distance_m / 299792458.0) * 1e6,
            )
            graph.add_edge(edge)

    # Inter-relay edges
    for i in range(len(deployed_relays)):
        for j in range(i + 1, len(deployed_relays)):
            r_a = deployed_relays[i]
            r_b = deployed_relays[j]
            los_inter = calculate_line_of_sight(
                terrain.elevation,
                (r_a.rc[0], r_a.rc[1]),
                (r_b.rc[0], r_b.rc[1]),
                r_a.antenna_height_m,
                r_b.antenna_height_m,
                max_range_m=max_relay_range_m,
                dx_m=dx,
                dy_m=dy,
            )
            if los_inter.is_visible:
                edge = RelayEdge(
                    u=r_a.node_id,
                    v=r_b.node_id,
                    distance_m=los_inter.distance_m,
                    slant_range_m=los_inter.distance_m,
                    visibility=LinkVisibilityStatus.VISIBLE if los_inter.is_visible else LinkVisibilityStatus.BLOCKED,
                    min_clearance_m=los_inter.min_clearance_m,
                    num_hops=1,
                    propagation_delay_us=(los_inter.distance_m / 299792458.0) * 1e6,
                )
                graph.add_edge(edge)

    # Tarjan bridge and articulation analysis
    bridges = graph.find_bridge_edges()
    cuts = graph.find_articulation_points()
    fiedler = graph.compute_algebraic_connectivity()

    # Calculate average and max hops from timeline checkpoints
    checkpoints = timeline_res.get("checkpoints", [])
    hops_list = [cp.get("hops_to_base", 1) for cp in checkpoints if cp.get("state") in ("CONNECTED_DIRECT", "CONNECTED_RELAYED")]
    mean_hops = float(np.mean(hops_list)) if hops_list else 1.0
    max_hops = int(np.max(hops_list)) if hops_list else 1

    # Milestone 13F Resource Evaluation
    ledger_dict: Dict[str, Any] = {}
    e_tot_wh = 0.0
    e_drv_wh = 0.0
    e_idl_wh = 0.0
    e_com_wh = 0.0
    e_sci_wh = 0.0
    fin_soc = 100.0
    min_soc = 100.0
    res_feas = "FEASIBLE_WITHIN_CONFIGURED_BUDGET"

    if evaluate_resources:
        try:
            if isinstance(rover_resource_config, dict):
                valid_keys = {f.name for f in RoverResourceConfig.__dataclass_fields__.values()}
                rcfg = RoverResourceConfig(**{k: v for k, v in rover_resource_config.items() if k in valid_keys})
            elif isinstance(rover_resource_config, RoverResourceConfig):
                rcfg = rover_resource_config
            else:
                rcfg = RoverResourceConfig()

            if isinstance(relay_resource_config, dict):
                valid_r_keys = {f.name for f in RelayResourceConfig.__dataclass_fields__.values()}
                rly_cfg = RelayResourceConfig(**{k: v for k, v in relay_resource_config.items() if k in valid_r_keys})
            elif isinstance(relay_resource_config, RelayResourceConfig):
                rly_cfg = relay_resource_config
            else:
                rly_cfg = RelayResourceConfig()

            relays_for_ledger = [
                {"node_id": r.node_id, "rc": (r.rc[0], r.rc[1])}
                for r in deployed_relays
            ]
            wps_for_ledger = [
                {"name": wp.name, "rc": (wp.rc[0], wp.rc[1])}
                for wp in (waypoints or [])
            ]

            active_tx_map: Dict[str, float] = {}
            checkpoints = timeline_res.get("checkpoints", [])
            cp_dt = total_dur / max(len(checkpoints), 1)
            for cp in checkpoints:
                path_nodes = cp.get("active_path", [])
                for r in deployed_relays:
                    if r.node_id in path_nodes:
                        active_tx_map[r.node_id] = active_tx_map.get(r.node_id, 0.0) + cp_dt

            ledger = evaluate_mission_resource_ledger(
                path_rc=path,
                elevation_grid=terrain.elevation,
                slope_grid=terrain.slope_deg,
                invalid_mask=terrain.invalid_mask,
                ground_dx_m=dx,
                ground_dy_m=dy,
                rover_config=rcfg,
                relay_config=rly_cfg,
                relays_deployed=relays_for_ledger,
                intermediate_waypoints=wps_for_ledger,
                active_relay_tx_times_s=active_tx_map,
            )
            ledger_dict = ledger.to_dict()
            if ledger.constraint_violations:
                ledger_dict["constraint_violations"] = list(ledger.constraint_violations)
            traverse.resource_summary = ledger_dict
            e_tot_wh = ledger.total_mission_energy_wh
            e_drv_wh = joules_to_wh(ledger.total_mobility_energy_j)
            e_idl_wh = joules_to_wh(ledger.total_electrical_energy_j)
            e_com_wh = joules_to_wh(ledger.total_relay_energy_j)
            fin_soc = ledger.final_battery_soc_pct
            min_soc = ledger.min_battery_soc_pct
            res_feas = ledger.feasibility_classification.value
        except Exception as err:
            res_feas = "UNKNOWN_RESOURCE_FEASIBILITY"
            ledger_dict = {"error": str(err), "feasibility_classification": res_feas}

    # Milestone 13G Science & Data Logistics Evaluation
    sci_pts = 0.0
    data_gen_b = 0
    data_xfer_b = 0
    data_backlog_b = 0
    storage_peak_b = 0
    storage_press = "STORAGE_AVAILABLE"
    sci_plan_dict: Optional[Dict[str, Any]] = None
    data_ledger_dict: Optional[Dict[str, Any]] = None
    sci_violations: List[str] = []

    if science_targets:
        (
            sci_pts,
            data_gen_b,
            data_xfer_b,
            data_backlog_b,
            storage_peak_b,
            storage_press,
            sci_energy_wh,
            sci_plan_dict,
            data_ledger_dict,
            sci_violations,
        ) = evaluate_science_and_data_logistics(
            path_rc=path,
            trajectory_points=trajectory_points,
            checkpoints=checkpoints,
            science_targets=science_targets,
            rover_resource_config=rover_resource_config,
            storage_capacity_bytes=storage_capacity_bytes,
            simulated_transfer_rate_bps=simulated_transfer_rate_bps,
            retention_policy=retention_policy,
        )
        e_sci_wh = sci_energy_wh
        e_tot_wh += e_sci_wh
        if sci_violations:
            if "constraint_violations" not in ledger_dict:
                ledger_dict["constraint_violations"] = []
            ledger_dict["constraint_violations"].extend(sci_violations)

    metrics = JointMissionMetrics(
        distance_m=total_dist,
        travel_time_s=total_dur,
        mean_slope_deg=traverse.mean_slope_deg,
        max_slope_deg=traverse.max_slope_deg,
        elevation_gain_m=traverse.elevation_gain_m,
        elevation_loss_m=traverse.elevation_loss_m,
        terrain_effort_m=traverse.terrain_effort_m,
        connected_distance_m=conn_dist_m,
        gap_distance_m=gap_dist_m,
        gap_duration_s=gap_dur_s,
        availability_pct=avail_pct,
        max_gap_duration_s=max_gap_s,
        gap_count=gap_cnt,
        relay_count=len(deployed_relays),
        mean_hops=mean_hops,
        max_hops=max_hops,
        critical_bridges=len(bridges),
        energy_total_wh=e_tot_wh,
        energy_drive_wh=e_drv_wh,
        energy_idle_wh=e_idl_wh,
        energy_comms_wh=e_com_wh,
        energy_science_wh=e_sci_wh,
        final_soc_pct=fin_soc,
        min_soc_pct=min_soc,
        resource_feasibility=res_feas,
        science_points_total=sci_pts,
        data_generated_bytes=data_gen_b,
        data_transferred_bytes=data_xfer_b,
        data_backlog_bytes=data_backlog_b,
        storage_peak_bytes=storage_peak_b,
        storage_pressure_state=storage_press,
    )

    if return_ledger:
        return metrics, summary, gap_intervals, ledger_dict, sci_plan_dict, data_ledger_dict
    return metrics, summary, gap_intervals


# ==============================================================================
# 4. Multi-Objective Normalization & Pareto Frontier Analysis
# ==============================================================================

def compute_canonical_normalization(
    metrics: JointMissionMetrics,
    baseline_euclid_m: float,
    k_max: float = K_MAX_DEFAULT,
) -> Dict[str, float]:
    """
    Map raw multi-domain physical metrics into dimensionless canonical costs in [0.0, 1.0].
    Enforces dimensional homogeneity (lower cost is superior on all dimensions).
    """
    d_euclid = max(D_EUCLID_REF_MIN_M, baseline_euclid_m)

    # 1. Distance Detour Cost
    f_dist = min(1.0, max(0.0, (metrics.distance_m - d_euclid) / (2.0 * d_euclid)))

    # 2. Terrain Slope Hazard Cost
    slope_term1 = min(1.0, max(0.0, metrics.mean_slope_deg / THETA_REF_DEG))
    slope_term2 = min(1.0, max(0.0, (metrics.max_slope_deg - THETA_REF_DEG) / DELTA_THETA_MAX_DEG)) if metrics.max_slope_deg > THETA_REF_DEG else 0.0
    f_slope = 0.6 * slope_term1 + 0.4 * slope_term2

    # 3. Terrain Effort Cost
    f_effort = min(1.0, max(0.0, (metrics.terrain_effort_m - d_euclid) / (4.0 * d_euclid)))

    # 4. Connectivity Gap Ratio Cost
    f_gap_time = min(1.0, max(0.0, 1.0 - (metrics.availability_pct / 100.0)))

    # 5. Max Blackout Duration Cost
    f_max_gap = min(1.0, max(0.0, metrics.max_gap_duration_s / MAX_GAP_TOLERANCE_S))

    # 6. Relay Deployment Cost
    f_relay = min(1.0, max(0.0, metrics.relay_count / k_max)) if k_max > 0 else 0.0

    # 7. Bridge Vulnerability Cost
    f_bridge = min(1.0, max(0.0, metrics.critical_bridges / 2.0))

    # 8. Science Return Cost (1.0 - normalized science return)
    science_benchmark = max(100.0, metrics.science_points_total)
    f_science = min(1.0, max(0.0, 1.0 - (metrics.science_points_total / science_benchmark)))

    # 9. Storage Peak Cost
    f_storage = min(1.0, max(0.0, metrics.storage_peak_bytes / 17_179_869_184.0))

    return {
        "distance": f_dist,
        "slope_hazard": f_slope,
        "terrain_effort": f_effort,
        "gap_ratio": f_gap_time,
        "max_gap": f_max_gap,
        "relay_budget": f_relay,
        "bridge_vulnerability": f_bridge,
        "science_return": f_science,
        "storage_peak": f_storage,
    }


def compute_scalar_score(
    normalized_vector: Dict[str, float],
    weights: Dict[str, float],
) -> float:
    """Compute scalarized weighted objective loss J_w in [0.0, 1.0]."""
    score = 0.0
    total_w = sum(weights.values())
    if total_w <= 0:
        return 0.5

    for key, cost in normalized_vector.items():
        w = weights.get(key, 0.0)
        score += (w / total_w) * cost

    return min(1.0, max(0.0, score))


def compute_pareto_frontier(
    configurations: List[JointMissionConfiguration],
) -> List[JointMissionConfiguration]:
    """
    Extract the non-dominated Pareto set across candidate co-design configurations.
    Configuration A dominates B iff A is <= B on all canonical criteria and strictly < on at least one.
    """
    if not configurations:
        return []

    pareto_set: List[JointMissionConfiguration] = []

    for cand_a in configurations:
        is_dominated = False
        vec_a = cand_a.metrics.normalized_vector

        for cand_b in configurations:
            if cand_a is cand_b:
                continue

            vec_b = cand_b.metrics.normalized_vector

            # Check if B dominates A (B <= A on all criteria, and B < A on at least one)
            b_dominates_a = True
            b_strictly_better = False

            for k in vec_a.keys():
                val_a = vec_a[k]
                val_b = vec_b.get(k, 0.0)

                if val_b > val_a + 1e-6:
                    b_dominates_a = False
                    break
                if val_b < val_a - 1e-6:
                    b_strictly_better = True

            if b_dominates_a and b_strictly_better:
                is_dominated = True
                break

        cand_a.is_pareto_optimal = not is_dominated
        if not is_dominated:
            pareto_set.append(cand_a)

    return pareto_set


# ==============================================================================
# 5. Decision Explanation Engine
# ==============================================================================

def generate_decision_explanation(
    recommended: JointMissionConfiguration,
    pareto_set: List[JointMissionConfiguration],
    all_configs: List[JointMissionConfiguration],
    weight_profile_name: str,
) -> DecisionExplanation:
    """
    Generate an evidence-based explanation detailing why a co-design configuration was selected.
    Calculates marginal rates of substitution and details terrain vs infrastructure trade-offs.
    """
    rec_m = recommended.metrics
    rec_trv = recommended.traverse
    rec_rly = recommended.relays

    summary = (
        f"Selected {recommended.configuration_id} under '{weight_profile_name}' objective weighting: "
        f"{rec_trv.label} ({rec_m.distance_m:.0f}m, mean slope {rec_m.mean_slope_deg:.1f}°) coupled with "
        f"{rec_m.relay_count} surface relay(s) achieving {rec_m.availability_pct:.1f}% communications availability."
    )

    selection_rationale = (
        f"This mission plan achieves the lowest scalarized objective loss ({rec_m.scalar_utility_score:.4f}) "
        f"by balancing mobility effort against geometric communications visibility. "
        f"It establishes an active backhaul to base station with a maximum hop depth of {rec_m.max_hops}."
    )

    terrain_trade_offs = (
        f"The traverse introduces {rec_m.elevation_gain_m:.1f}m elevation gain and {rec_m.elevation_loss_m:.1f}m loss, "
        f"maintaining a peak slope of {rec_m.max_slope_deg:.1f}° (safe within 25.0° cutoff). "
        f"Equivalent flat-terrain effort is {rec_m.terrain_effort_m:.0f}m."
    )

    if rec_m.relay_count > 0:
        relay_names = ", ".join([r["node_id"] for r in rec_rly.relays_deployed])
        connectivity_resolution = (
            f"Direct line-of-sight to Base was obstructed along {rec_m.gap_distance_m:.0f}m of traverse. "
            f"Deploying {rec_m.relay_count} relay tower(s) ({relay_names}) restores continuous multi-hop coverage, "
            f"limiting residual geometric gap distance to {rec_m.gap_distance_m:.1f}m."
        )
    else:
        connectivity_resolution = (
            f"Zero relays required: the traverse maintains {rec_m.availability_pct:.1f}% direct geometric visibility "
            f"to the base station throughout the entire traverse."
        )

    # Compute comparisons against other Pareto peers
    rejected_comparisons: List[str] = []
    mrs_dict: Dict[str, float] = {}

    for peer in pareto_set:
        if peer.configuration_id == recommended.configuration_id:
            continue

        p_m = peer.metrics
        p_trv = peer.traverse

        d_dist = p_m.distance_m - rec_m.distance_m
        d_gap_min = (rec_m.gap_duration_s - p_m.gap_duration_s) / 60.0
        d_relays = p_m.relay_count - rec_m.relay_count

        comp_text = f"Versus {peer.configuration_id} ({p_trv.label}, k={p_m.relay_count}): "
        if d_dist > 0:
            comp_text += f"Recommended is {d_dist:.0f}m shorter"
        else:
            comp_text += f"Alternative is {abs(d_dist):.0f}m shorter"

        if d_relays > 0:
            comp_text += f", requires {d_relays} fewer relay tower(s)"
        elif d_relays < 0:
            comp_text += f", but alternative requires {abs(d_relays)} fewer relay(s)"

        if abs(p_m.availability_pct - rec_m.availability_pct) > 0.1:
            comp_text += f", with {rec_m.availability_pct:.1f}% vs {p_m.availability_pct:.1f}% comms availability."
        else:
            comp_text += " with identical comms availability."

        rejected_comparisons.append(comp_text)

        # Marginal rate of substitution: distance penalty per minute of blackout prevented
        if abs(d_gap_min) > 0.1:
            mrs_dict[f"mrs_dist_per_gap_min_{peer.configuration_id}"] = abs(d_dist) / abs(d_gap_min)

        # Marginal rate of substitution: Energy and Data per Science Point
        d_sci_pts = p_m.science_points_total - rec_m.science_points_total
        d_energy_wh = p_m.energy_total_wh - rec_m.energy_total_wh
        if abs(d_sci_pts) > 0.1:
            mrs_dict[f"mrs_energy_per_science_pt_{peer.configuration_id}"] = abs(d_energy_wh) / abs(d_sci_pts)
            d_xfer_mb = (p_m.data_transferred_bytes - rec_m.data_transferred_bytes) / (1024 * 1024)
            mrs_dict[f"mrs_data_xfer_per_science_pt_{peer.configuration_id}"] = abs(d_xfer_mb) / abs(d_sci_pts)

    assumptions = [
        "Topography evaluated strictly on USGS Jezero CTX 20m DTM (DOI: 10.5066/P906QQT8).",
        "Line-of-Sight is evaluated geometrically with IAU 2000 Mars spherical curvature correction.",
        "Radio-frequency wave propagation, Fresnel diffraction, and atmospheric dust attenuation are not modeled.",
        "Modeled speeds and metabolic costs are planning simulation heuristics and not certified for astronaut operational safety.",
        "Science priority scores represent configured operator planning preferences, not objective scientific discovery truth.",
        "Data transfers represent simulated link throughput models to a surface base station; Earth DSN downlink is not claimed.",
        "Zero-baseline divisions safely handled with documented physical bounds.",
    ]

    return DecisionExplanation(
        summary=summary,
        selection_rationale=selection_rationale,
        terrain_trade_offs=terrain_trade_offs,
        connectivity_resolution=connectivity_resolution,
        rejected_alternatives_comparison=rejected_comparisons[:4],
        marginal_rates_of_substitution=mrs_dict,
        assumptions_and_limitations=assumptions,
    )


# ==============================================================================
# 6. Central Optimization Orchestrator
# ==============================================================================

def optimize_joint_mission(
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    terrain: TerrainGrid,
    base_station: Dict[str, Any],
    waypoints: Optional[List[ScienceWaypoint]] = None,
    relay_budget: int = 2,
    max_direct_range_m: float = 2500.0,
    max_relay_range_m: float = 5000.0,
    rover_antenna_h: float = 2.5,
    base_antenna_h: float = 10.0,
    relay_antenna_h: float = 10.0,
    objective_profile: str = "balanced",
    custom_weights: Optional[Dict[str, float]] = None,
    max_route_candidates: int = 5,
    rover_resource_config: Optional[Union[RoverResourceConfig, Dict[str, Any]]] = None,
    relay_resource_config: Optional[Union[RelayResourceConfig, Dict[str, Any]]] = None,
    evaluate_resources: bool = True,
    science_targets: Optional[List[Union[ScienceTargetConfig, Dict[str, Any]]]] = None,
    storage_capacity_bytes: int = 17_179_869_184,
    simulated_transfer_rate_bps: float = 2_000_000.0,
    retention_policy: str = "TRANSFER_THEN_RELEASE",
) -> JointMissionOptimizationResult:
    """
    Main engineering entrypoint for Joint Mission Co-Design.
    Simultaneously explores alternative traverses and relay configurations,
    evaluating Pareto dominance, multi-objective trade-offs, and decision explanations.
    """
    t0 = time.time()
    dx = terrain.dx_ground_m if terrain.dx_ground_m else DEFAULT_DX_M
    dy = terrain.dy_ground_m if terrain.dy_ground_m else DEFAULT_DY_M

    # 1. Base Station Node
    b_elev = float(terrain.elevation[base_station.get("row", start_rc[0]), base_station.get("col", start_rc[1])])
    base_node = RelayNode(
        node_id=str(base_station.get("node_id", "BASE")),
        node_type=RelayNodeType.BASE_STATION,
        rc=(int(base_station.get("row", start_rc[0])), int(base_station.get("col", start_rc[1]))),
        elevation_m=b_elev,
        antenna_height_m=base_antenna_h,
        label=str(base_station.get("label", "Base Station")),
    )

    # 2. Screen Promontory Relay Candidates on DTM
    candidate_promontories = screen_relay_candidates(
        elevation=terrain.elevation,
        slope_deg=terrain.slope_deg,
        invalid_mask=terrain.invalid_mask,
        dx_ground_m=dx,
        dy_ground_m=dy,
        max_slope_deg=12.0,
        min_elevation_m=-2500.0,
        min_separation_m=450.0,
        max_candidates=12,
    )

    # Convert to RelayNodes
    relay_pool_nodes: List[RelayNode] = []
    for cand in candidate_promontories:
        c_id = cand["candidate_id"]
        cr, cc = cand["row"], cand["col"]
        c_elev = cand["elevation_m"]
        r_node = RelayNode(
            node_id=c_id,
            node_type=RelayNodeType.CANDIDATE_RELAY,
            rc=(cr, cc),
            elevation_m=c_elev,
            antenna_height_m=relay_antenna_h,
            label=f"Promontory Relay ({cr}, {cc})",
        )
        relay_pool_nodes.append(r_node)

    # 3. Generate Candidate Traverses
    candidate_traverses = generate_candidate_traverses(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain,
        waypoints=waypoints,
        max_candidates=max_route_candidates,
        candidate_promontories=candidate_promontories,
    )

    if not candidate_traverses:
        raise RuntimeError("No feasible traverse routes could be found between start and goal.")

    # 4. Resolve Objective Weights
    if custom_weights:
        weights = custom_weights
    else:
        weights = OBJECTIVE_WEIGHT_PROFILES.get(objective_profile, OBJECTIVE_WEIGHT_PROFILES["balanced"])

    # Baseline Euclidean Distance
    baseline_euclid = math.hypot((goal_rc[1] - start_rc[1]) * dx, (goal_rc[0] - start_rc[0]) * dy)

    # 5. Enumerate and Evaluate Coupled Configurations
    all_configurations: List[JointMissionConfiguration] = []
    config_idx = 1
    total_los_evals = 0

    for trv in candidate_traverses:
        # Build downsampled target units from traverse for submodular placement
        step_stride = max(1, len(trv.path_rc) // 10)
        downsampled_units = []
        for s_idx in range(0, len(trv.path_rc), step_stride):
            ur, uc = trv.path_rc[s_idx]
            downsampled_units.append({
                "node_id": f"{trv.traverse_id}_PT_{s_idx}",
                "row": ur,
                "col": uc,
                "antenna_height_m": rover_antenna_h,
            })

        # Evaluate across relay budgets k in [0..relay_budget]
        for k in range(0, relay_budget + 1):
            deployed_relays: List[RelayNode] = []

            if k > 0 and relay_pool_nodes:
                # Build evaluation graph with Base Station and downsampled target units
                g = RelayNetworkGraph(r_max_m=max_relay_range_m)
                g.add_node(base_node)
                target_unit_ids = []
                target_nodes = []
                for tu_dict in downsampled_units:
                    tu_id = tu_dict["node_id"]
                    tur, tuc = tu_dict["row"], tu_dict["col"]
                    tu_elev = float(terrain.elevation[tur, tuc])
                    tu_node = RelayNode(
                        node_id=tu_id,
                        node_type=RelayNodeType.ROBOTIC_ROVER,
                        rc=(tur, tuc),
                        elevation_m=tu_elev,
                        antenna_height_m=rover_antenna_h,
                    )
                    g.add_node(tu_node)
                    target_unit_ids.append(tu_id)
                    target_nodes.append(tu_node)

                    # Edge to Base if visible
                    los_direct = calculate_line_of_sight(
                        terrain.elevation,
                        base_node.rc,
                        (tur, tuc),
                        base_node.antenna_height_m,
                        rover_antenna_h,
                        max_range_m=max_direct_range_m,
                        dx_m=dx,
                        dy_m=dy,
                    )
                    if los_direct.is_visible:
                        g.add_edge(RelayEdge(
                            u=base_node.node_id,
                            v=tu_id,
                            distance_m=los_direct.distance_m,
                            slant_range_m=los_direct.distance_m,
                            visibility=LinkVisibilityStatus.VISIBLE,
                            min_clearance_m=los_direct.min_clearance_m,
                        ))

                # Candidate edges to Base and Targets
                candidate_edges = []
                for cand in relay_pool_nodes:
                    los_b = calculate_line_of_sight(
                        terrain.elevation,
                        base_node.rc,
                        cand.rc,
                        base_node.antenna_height_m,
                        cand.antenna_height_m,
                        max_range_m=max_relay_range_m,
                        dx_m=dx,
                        dy_m=dy,
                    )
                    if los_b.is_visible:
                        candidate_edges.append(RelayEdge(
                            u=base_node.node_id,
                            v=cand.node_id,
                            distance_m=los_b.distance_m,
                            slant_range_m=los_b.distance_m,
                            visibility=LinkVisibilityStatus.VISIBLE,
                            min_clearance_m=los_b.min_clearance_m,
                        ))
                    for tu in target_nodes:
                        los_u = calculate_line_of_sight(
                            terrain.elevation,
                            cand.rc,
                            tu.rc,
                            cand.antenna_height_m,
                            tu.antenna_height_m,
                            max_range_m=max_relay_range_m,
                            dx_m=dx,
                            dy_m=dy,
                        )
                        if los_u.is_visible:
                            candidate_edges.append(RelayEdge(
                                u=cand.node_id,
                                v=tu.node_id,
                                distance_m=los_u.distance_m,
                                slant_range_m=los_u.distance_m,
                                visibility=LinkVisibilityStatus.VISIBLE,
                                min_clearance_m=los_u.min_clearance_m,
                            ))

                opt_res = optimize_relay_placement(
                    graph=g,
                    base_node_id=base_node.node_id,
                    target_unit_ids=target_unit_ids,
                    candidate_nodes=relay_pool_nodes,
                    candidate_edges=candidate_edges,
                    relay_budget=k,
                )
                selected_dicts = opt_res.get("selected_relays", [])
                selected_ids = {d.get("node_id") for d in selected_dicts}
                deployed_relays = [rn for rn in relay_pool_nodes if rn.node_id in selected_ids]

            # High-fidelity timeline and graph evaluation
            eval_ret = evaluate_traverse_connectivity_with_relays(
                traverse=trv,
                base_node=base_node,
                deployed_relays=deployed_relays,
                terrain=terrain,
                max_direct_range_m=max_direct_range_m,
                max_relay_range_m=max_relay_range_m,
                rover_antenna_h=rover_antenna_h,
                rover_resource_config=rover_resource_config,
                relay_resource_config=relay_resource_config,
                waypoints=waypoints,
                evaluate_resources=evaluate_resources,
                return_ledger=True,
                science_targets=science_targets,
                storage_capacity_bytes=storage_capacity_bytes,
                simulated_transfer_rate_bps=simulated_transfer_rate_bps,
                retention_policy=retention_policy,
            )
            metrics, t_summary, t_gaps, ledger_data, sci_plan, data_ledg = eval_ret

            # Compute normalized vector and scalar score
            norm_vec = compute_canonical_normalization(metrics, baseline_euclid, k_max=float(relay_budget or 3.0))
            scalar_score = compute_scalar_score(norm_vec, weights)
            metrics.normalized_vector = norm_vec
            metrics.scalar_utility_score = scalar_score

            # Build Deployment Config
            r_deployed_dicts = [
                {
                    "node_id": r.node_id,
                    "row": r.rc[0],
                    "col": r.rc[1],
                    "elevation_m": r.elevation_m,
                    "antenna_height_m": r.antenna_height_m,
                }
                for r in deployed_relays
            ]

            r_config = RelayDeploymentConfig(
                config_id=f"RELAY_CFG_K{k}_{trv.traverse_id}",
                relays_deployed=r_deployed_dicts,
                relay_count=len(deployed_relays),
                is_connected_to_base=True,
                tarjan_bridges=[],
            )

            c_id = f"JMC_{config_idx:02d}_{trv.traverse_id}_K{k}"
            config_idx += 1

            jmc_violations = list(ledger_data.get("constraint_violations", [])) if ledger_data else []
            jmc = JointMissionConfiguration(
                configuration_id=c_id,
                traverse=trv,
                relays=r_config,
                metrics=metrics,
                timeline_summary=t_summary,
                timeline_gap_intervals=t_gaps,
                is_pareto_optimal=False,
                constraint_violations=jmc_violations,
                resource_ledger=ledger_data if ledger_data else None,
                science_plan=sci_plan,
                data_ledger=data_ledg,
            )
            all_configurations.append(jmc)

    # 6. Extract Pareto Frontier
    pareto_frontier = compute_pareto_frontier(all_configurations)

    # 7. Select Recommended Configuration (lowest scalar utility score, preferring Pareto set)
    if pareto_frontier:
        recommended = min(pareto_frontier, key=lambda c: c.metrics.scalar_utility_score)
    else:
        recommended = min(all_configurations, key=lambda c: c.metrics.scalar_utility_score)

    recommended.recommendation_tier = "OPTIMAL_RECOMMENDED"

    for c in all_configurations:
        if c is recommended:
            continue
        if c.is_pareto_optimal:
            c.recommendation_tier = "PARETO_ALTERNATIVE"
        else:
            c.recommendation_tier = "DOMINATED"

    # 8. Generate Decision Explanation
    explanation = generate_decision_explanation(
        recommended=recommended,
        pareto_set=pareto_frontier,
        all_configs=all_configurations,
        weight_profile_name=objective_profile,
    )

    elapsed_ms = (time.time() - t0) * 1000.0

    # 9. Compute Deterministic SHA-256 Fingerprint
    fingerprint_data = {
        "start": start_rc,
        "goal": goal_rc,
        "base": (base_node.rc[0], base_node.rc[1]),
        "budget": relay_budget,
        "profile": objective_profile,
        "rec_id": recommended.configuration_id,
        "rec_dist": recommended.metrics.distance_m,
        "rec_avail": recommended.metrics.availability_pct,
    }
    sha256_hash = hashlib.sha256(json.dumps(fingerprint_data, sort_keys=True).encode()).hexdigest()

    result_id = f"JMR_{sha256_hash[:12]}"

    # Milestone 13F: Resource Sensitivity Analysis for recommended route
    res_sens_dict = None
    if evaluate_resources and recommended.traverse.path_rc:
        try:
            if isinstance(rover_resource_config, dict):
                valid_keys = {f.name for f in RoverResourceConfig.__dataclass_fields__.values()}
                rcfg_sens = RoverResourceConfig(**{k: v for k, v in rover_resource_config.items() if k in valid_keys})
            elif isinstance(rover_resource_config, RoverResourceConfig):
                rcfg_sens = rover_resource_config
            else:
                rcfg_sens = RoverResourceConfig()

            sens_res = evaluate_resource_sensitivity(
                path_rc=recommended.traverse.path_rc,
                elevation_grid=terrain.elevation,
                slope_grid=terrain.slope_deg,
                invalid_mask=terrain.invalid_mask,
                ground_dx_m=dx,
                ground_dy_m=dy,
                rover_config=rcfg_sens,
            )
            res_sens_dict = sens_res.to_dict()
        except Exception as e:
            res_sens_dict = {"error": str(e)}

    return JointMissionOptimizationResult(
        result_id=result_id,
        timestamp_utc=time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
        sha256_fingerprint=sha256_hash,
        input_parameters={
            "start_rc": start_rc,
            "goal_rc": goal_rc,
            "base_station": base_station,
            "relay_budget": relay_budget,
            "max_direct_range_m": max_direct_range_m,
            "max_relay_range_m": max_relay_range_m,
            "rover_antenna_h": rover_antenna_h,
            "objective_profile": objective_profile,
        },
        candidate_traverses=candidate_traverses,
        candidate_relay_pool=candidate_promontories,
        all_configurations=all_configurations,
        pareto_frontier=pareto_frontier,
        recommended_configuration=recommended,
        decision_explanation=explanation,
        search_bounds={
            "candidate_traverses_generated": len(candidate_traverses),
            "promontory_candidates_screened": len(candidate_promontories),
            "configurations_evaluated": len(all_configurations),
            "pareto_configurations_count": len(pareto_frontier),
            "execution_runtime_ms": round(elapsed_ms, 2),
        },
        provenance={
            "terrain_dataset": "USGS_CTX_DTM_JEZERO_20M",
            "doi": "10.5066/P906QQT8",
            "planetary_datum": "IAU 2000 Mars Spheroid (R=3,396,190m)",
            "elevation_interpolation": "Bilinear sub-grid continuous with strict NoData sentinel rejection",
        },
        resource_sensitivity=res_sens_dict,
    )


def evaluate_joint_mission(
    traverse_path: List[Tuple[int, int]],
    terrain: TerrainGrid,
    base_station: Dict[str, Any],
    deployed_relays: Optional[List[Dict[str, Any]]] = None,
    rover_antenna_h: float = 2.5,
    max_direct_range_m: float = 2500.0,
    max_relay_range_m: float = 5000.0,
    rover_resource_config: Optional[Union[RoverResourceConfig, Dict[str, Any]]] = None,
    relay_resource_config: Optional[Union[RelayResourceConfig, Dict[str, Any]]] = None,
    evaluate_resources: bool = True,
    science_targets: Optional[List[Union[ScienceTargetConfig, Dict[str, Any]]]] = None,
    storage_capacity_bytes: int = 17_179_869_184,
    simulated_transfer_rate_bps: float = 2_000_000.0,
    retention_policy: str = "TRANSFER_THEN_RELEASE",
) -> JointMissionConfiguration:
    """
    Evaluate a specific pre-defined traverse path and optional relay set without search.
    """
    if len(traverse_path) < 2:
        raise ValueError("traverse_path must contain at least 2 grid points.")

    b_row = int(base_station.get("row", traverse_path[0][0]))
    b_col = int(base_station.get("col", traverse_path[0][1]))
    b_elev = float(terrain.elevation[b_row, b_col])
    b_h = float(base_station.get("antenna_height_m", 10.0))

    base_node = RelayNode(
        node_id=str(base_station.get("node_id", "BASE")),
        node_type=RelayNodeType.BASE_STATION,
        rc=(b_row, b_col),
        elevation_m=b_elev,
        antenna_height_m=b_h,
        label=str(base_station.get("label", "Base Station")),
    )

    relay_nodes: List[RelayNode] = []
    if deployed_relays:
        for r in deployed_relays:
            rr, rc = int(r["row"]), int(r["col"])
            r_elev = float(terrain.elevation[rr, rc])
            r_h = float(r.get("antenna_height_m", 10.0))
            relay_nodes.append(
                RelayNode(
                    node_id=str(r.get("node_id", f"RELAY_{rr}_{rc}")),
                    node_type=RelayNodeType.CANDIDATE_RELAY,
                    rc=(rr, rc),
                    elevation_m=r_elev,
                    antenna_height_m=r_h,
                )
            )

    trv = _build_candidate_traverse(
        t_id="USER_TRAVERSE",
        label="Custom User Traverse",
        desc="Pre-defined user trajectory evaluated against terrain and communications infrastructure.",
        path=traverse_path,
        cost=0.0,
        terrain=terrain,
        profile="user_specified",
    )

    eval_res = evaluate_traverse_connectivity_with_relays(
        traverse=trv,
        base_node=base_node,
        deployed_relays=relay_nodes,
        terrain=terrain,
        max_direct_range_m=max_direct_range_m,
        max_relay_range_m=max_relay_range_m,
        rover_antenna_h=rover_antenna_h,
        rover_resource_config=rover_resource_config,
        relay_resource_config=relay_resource_config,
        evaluate_resources=evaluate_resources,
        return_ledger=True,
        science_targets=science_targets,
        storage_capacity_bytes=storage_capacity_bytes,
        simulated_transfer_rate_bps=simulated_transfer_rate_bps,
        retention_policy=retention_policy,
    )
    metrics, t_summary, t_gaps, eval_ledger, sci_plan, data_ledg = eval_res

    dx = terrain.dx_ground_m if terrain.dx_ground_m else DEFAULT_DX_M
    dy = terrain.dy_ground_m if terrain.dy_ground_m else DEFAULT_DY_M
    start_rc = traverse_path[0]
    goal_rc = traverse_path[-1]
    baseline_euclid = math.hypot((goal_rc[1] - start_rc[1]) * dx, (goal_rc[0] - start_rc[0]) * dy)

    norm_vec = compute_canonical_normalization(metrics, baseline_euclid, k_max=float(len(relay_nodes) or 3.0))
    weights = OBJECTIVE_WEIGHT_PROFILES["balanced"]
    scalar_score = compute_scalar_score(norm_vec, weights)
    metrics.normalized_vector = norm_vec
    metrics.scalar_utility_score = scalar_score

    r_config = RelayDeploymentConfig(
        config_id="USER_RELAY_CONFIG",
        relays_deployed=[
            {"node_id": r.node_id, "row": r.rc[0], "col": r.rc[1], "elevation_m": r.elevation_m, "antenna_height_m": r.antenna_height_m}
            for r in relay_nodes
        ],
        relay_count=len(relay_nodes),
        is_connected_to_base=True,
    )

    eval_violations = list(eval_ledger.get("constraint_violations", [])) if eval_ledger else []
    return JointMissionConfiguration(
        configuration_id="USER_EVALUATION",
        traverse=trv,
        relays=r_config,
        metrics=metrics,
        timeline_summary=t_summary,
        timeline_gap_intervals=t_gaps,
        is_pareto_optimal=True,
        constraint_violations=eval_violations,
        recommendation_tier="EVALUATED_USER_CONFIGURATION",
        resource_ledger=eval_ledger if eval_ledger else None,
        science_plan=sci_plan,
        data_ledger=data_ledg,
    )
