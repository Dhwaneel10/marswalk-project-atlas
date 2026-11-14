"""
MarsWalk 2.0 — Milestone 11D: Campaign What-If Simulation Lab & Scenario Comparison.
Enables deterministic evaluation of hypothetical disruptions, mobility deratings,
corridor closures, operational holds, and priority shifts on multi-sol campaigns.

Guarantees:
  - Deterministic calculations grounded in USGS CTX 20m Jezero topography.
  - Strict preservation of baseline campaign, completed targets, and recorded observations.
  - No probabilistic fabrication or statistical likelihood claims.
  - Bounded execution preventing combinatorial explosion (max 10 scenarios per batch).
"""

import copy
import datetime
import enum
import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from marswalk.api.contracts import validate_campaign_scenario_record
from marswalk.core.contingency import compute_circular_footprint
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignSortie,
    CampaignStatus,
    CampaignSummary,
    CampaignTarget,
    MissionCampaign,
    PlanningProfile,
    TargetStatus,
    plan_mission_campaign,
    validate_target_dependencies,
)
from marswalk.core.terrain import TerrainGrid

logger = logging.getLogger(__name__)

# Bounded Operational Constants
MAX_SCENARIOS_PER_BATCH = 10
MAX_MODIFICATIONS_PER_SCENARIO = 10

MIN_SPEED_FACTOR = 0.1
MAX_SPEED_FACTOR = 1.5

MIN_RADIUS_M = 10.0
MAX_RADIUS_M = 500.0

MIN_DELAY_S = 0.0
MAX_DELAY_S = 14400.0  # 4 hours max operational hold

MIN_SORTIE_DURATION_S = 900.0   # 15 minutes
MAX_SORTIE_DURATION_S = 28800.0 # 8 hours (EVA budget ceiling)

MIN_SOLS_LIMIT = 1
MAX_SOLS_LIMIT = 10


class ScenarioType(str, enum.Enum):
    MOBILITY_CHANGE = "mobility_change"
    TARGET_LOSS = "target_loss"
    CORRIDOR_CLOSURE = "corridor_closure"
    OPERATIONAL_DELAY = "operational_delay"
    TIME_CONSTRAINT = "time_constraint"
    OBJECTIVE_PRIORITY_CHANGE = "objective_priority_change"
    COMBINED = "combined"
    UNSUPPORTED = "unsupported"


class ScenarioStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    INFEASIBLE = "INFEASIBLE"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"


@dataclass
class ScenarioComparison:
    delta_sols: int
    delta_sorties: int
    delta_distance_m: float
    delta_duration_s: float
    delta_science_score: float
    targets_scheduled_delta: int
    baseline_targets_scheduled: int
    scenario_targets_scheduled: int
    lost_target_ids: List[str]
    gained_target_ids: List[str]
    deferred_target_ids: List[str]
    blocked_target_ids: List[str]
    causal_attribution: Dict[str, str]
    feasibility_status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "delta_sols": self.delta_sols,
            "delta_sorties": self.delta_sorties,
            "delta_distance_m": round(self.delta_distance_m, 1),
            "delta_duration_s": round(self.delta_duration_s, 1),
            "delta_science_score": round(self.delta_science_score, 1),
            "targets_scheduled_delta": self.targets_scheduled_delta,
            "baseline_targets_scheduled": self.baseline_targets_scheduled,
            "scenario_targets_scheduled": self.scenario_targets_scheduled,
            "lost_target_ids": sorted(self.lost_target_ids),
            "gained_target_ids": sorted(self.gained_target_ids),
            "deferred_target_ids": sorted(self.deferred_target_ids),
            "blocked_target_ids": sorted(self.blocked_target_ids),
            "causal_attribution": self.causal_attribution,
            "feasibility_status": self.feasibility_status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScenarioComparison":
        return cls(
            delta_sols=int(data.get("delta_sols", 0)),
            delta_sorties=int(data.get("delta_sorties", 0)),
            delta_distance_m=float(data.get("delta_distance_m", 0.0)),
            delta_duration_s=float(data.get("delta_duration_s", 0.0)),
            delta_science_score=float(data.get("delta_science_score", 0.0)),
            targets_scheduled_delta=int(data.get("targets_scheduled_delta", 0)),
            baseline_targets_scheduled=int(data.get("baseline_targets_scheduled", 0)),
            scenario_targets_scheduled=int(data.get("scenario_targets_scheduled", 0)),
            lost_target_ids=list(data.get("lost_target_ids", [])),
            gained_target_ids=list(data.get("gained_target_ids", [])),
            deferred_target_ids=list(data.get("deferred_target_ids", [])),
            blocked_target_ids=list(data.get("blocked_target_ids", [])),
            causal_attribution=dict(data.get("causal_attribution", {})),
            feasibility_status=str(data.get("feasibility_status", "UNKNOWN")),
        )


@dataclass
class CampaignScenario:
    scenario_id: str
    campaign_id: str
    source_version: int
    name: str
    description: str
    scenario_type: str
    modifications: List[Dict[str, Any]]
    planning_profile: Optional[str] = None
    created_at_utc: str = ""
    status: str = "PENDING"
    is_feasible: bool = False
    failure_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    comparison: Optional[ScenarioComparison] = None
    simulated_campaign: Optional[Dict[str, Any]] = None
    schema_version: str = "1.0.0"
    provenance: str = "DETERMINISTIC_WHAT_IF_SIMULATION"
    limitations_disclaimer: str = (
        "Calculated what-if scenarios are deterministic planning heuristics for Mars mission simulation. "
        "They do not represent certified flight decisions, probabilistic failure risks, or statistical survival models."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scenario_id": self.scenario_id,
            "campaign_id": self.campaign_id,
            "source_version": self.source_version,
            "name": self.name,
            "description": self.description,
            "scenario_type": self.scenario_type,
            "modifications": self.modifications,
            "planning_profile": self.planning_profile,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "is_feasible": self.is_feasible,
            "failure_reason": self.failure_reason,
            "warnings": self.warnings,
            "comparison": self.comparison.to_dict() if self.comparison else None,
            "simulated_campaign": self.simulated_campaign,
            "provenance": self.provenance,
            "limitations_disclaimer": self.limitations_disclaimer,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignScenario":
        comp_data = data.get("comparison")
        comp = ScenarioComparison.from_dict(comp_data) if comp_data else None
        return cls(
            schema_version=data.get("schema_version", "1.0.0"),
            scenario_id=data.get("scenario_id", ""),
            campaign_id=data.get("campaign_id", ""),
            source_version=int(data.get("source_version", 1)),
            name=data.get("name", ""),
            description=data.get("description", ""),
            scenario_type=data.get("scenario_type", "combined"),
            modifications=list(data.get("modifications", [])),
            planning_profile=data.get("planning_profile"),
            created_at_utc=data.get("created_at_utc", ""),
            status=data.get("status", "PENDING"),
            is_feasible=bool(data.get("is_feasible", False)),
            failure_reason=data.get("failure_reason"),
            warnings=list(data.get("warnings", [])),
            comparison=comp,
            simulated_campaign=data.get("simulated_campaign"),
            provenance=data.get("provenance", "DETERMINISTIC_WHAT_IF_SIMULATION"),
            limitations_disclaimer=data.get("limitations_disclaimer", ""),
        )


def _validate_modification_bounds(mod: Dict[str, Any]) -> None:
    """Validates individual modification parameters against strict physical bounds."""
    m_type = mod.get("type")
    if not m_type:
        raise ValueError("Modification record missing required 'type' field.")

    if m_type == ScenarioType.MOBILITY_CHANGE.value:
        if "speed_factor" in mod:
            sf = float(mod["speed_factor"])
            if not (MIN_SPEED_FACTOR <= sf <= MAX_SPEED_FACTOR):
                raise ValueError(f"speed_factor {sf} out of bounds [{MIN_SPEED_FACTOR}, {MAX_SPEED_FACTOR}]")
        if "max_slope_deg" in mod:
            slope = float(mod["max_slope_deg"])
            if not (5.0 <= slope <= 30.0):
                raise ValueError(f"max_slope_deg {slope} out of bounds [5.0, 30.0]")

    elif m_type == ScenarioType.TARGET_LOSS.value:
        if not mod.get("target_id"):
            raise ValueError("target_loss modification requires a non-empty 'target_id'.")

    elif m_type == ScenarioType.CORRIDOR_CLOSURE.value:
        if "radius_m" in mod:
            r = float(mod["radius_m"])
            if not (MIN_RADIUS_M <= r <= MAX_RADIUS_M):
                raise ValueError(f"Corridor closure radius_m {r} out of bounds [{MIN_RADIUS_M}, {MAX_RADIUS_M}]")

    elif m_type == ScenarioType.OPERATIONAL_DELAY.value:
        if "delay_s" in mod:
            d = float(mod["delay_s"])
            if not (MIN_DELAY_S <= d <= MAX_DELAY_S):
                raise ValueError(f"operational_delay delay_s {d} out of bounds [{MIN_DELAY_S}, {MAX_DELAY_S}]")

    elif m_type == ScenarioType.TIME_CONSTRAINT.value:
        if "max_duration_per_sortie_s" in mod:
            dur = float(mod["max_duration_per_sortie_s"])
            if not (MIN_SORTIE_DURATION_S <= dur <= MAX_SORTIE_DURATION_S):
                raise ValueError(f"max_duration_per_sortie_s {dur} out of bounds [{MIN_SORTIE_DURATION_S}, {MAX_SORTIE_DURATION_S}]")
        if "max_sols" in mod:
            sols = int(mod["max_sols"])
            if not (MIN_SOLS_LIMIT <= sols <= MAX_SOLS_LIMIT):
                raise ValueError(f"max_sols {sols} out of bounds [{MIN_SOLS_LIMIT}, {MAX_SOLS_LIMIT}]")

    elif m_type == ScenarioType.OBJECTIVE_PRIORITY_CHANGE.value:
        weights = mod.get("objective_weights", {})
        if not isinstance(weights, dict):
            raise ValueError("objective_weights must be a dictionary of target/objective multipliers.")
        for k, v in weights.items():
            vf = float(v)
            if vf < 0.0 or vf > 3.0:
                raise ValueError(f"Objective weight for '{k}' ({vf}) must be in range [0.0, 3.0].")


def evaluate_campaign_scenario(
    campaign: MissionCampaign,
    terrain: TerrainGrid,
    scenario_spec: Dict[str, Any],
    now_iso: Optional[str] = None,
) -> CampaignScenario:
    """
    Executes a single deterministic what-if scenario simulation against an isolated
    copy of a baseline campaign.

    Guarantees:
      - The source baseline campaign is NEVER mutated.
      - Completed sols and visited targets remain frozen.
      - Unsupported scenario types fail cleanly without generating synthetic data.
      - Full JSON schema validation against campaign-scenario.schema.json.
    """
    timestamp = now_iso or datetime.datetime.now(datetime.timezone.utc).isoformat()
    scen_id = scenario_spec.get("scenario_id") or f"scen_{hash(str(scenario_spec) + timestamp) & 0xffffffff:08x}"
    if not scen_id.startswith("scen_"):
        scen_id = f"scen_{scen_id}"

    scen_name = str(scenario_spec.get("name") or "Unnamed What-If Scenario")
    scen_desc = str(scenario_spec.get("description") or f"Evaluation of scenario {scen_id}")
    scen_type_raw = str(scenario_spec.get("scenario_type") or "combined")
    planning_prof = scenario_spec.get("planning_profile")

    # Extract modifications
    raw_mods = scenario_spec.get("modifications")
    if raw_mods is None:
        # Check if single modification passed as top-level params
        single_mod = dict(scenario_spec)
        single_mod.pop("scenario_id", None)
        single_mod.pop("campaign_id", None)
        single_mod.pop("source_version", None)
        single_mod.pop("name", None)
        single_mod.pop("description", None)
        single_mod.pop("scenario_type", None)
        single_mod.pop("planning_profile", None)
        single_mod["type"] = scen_type_raw
        raw_mods = [single_mod]
    elif not isinstance(raw_mods, list):
        raw_mods = [raw_mods]

    # Check for unsupported scenario types
    supported_types = {t.value for t in ScenarioType}
    if scen_type_raw not in supported_types:
        return CampaignScenario(
            scenario_id=scen_id,
            campaign_id=campaign.campaign_id,
            source_version=campaign.version,
            name=scen_name,
            description=scen_desc,
            scenario_type="unsupported",
            modifications=raw_mods,
            planning_profile=planning_prof,
            created_at_utc=timestamp,
            status=ScenarioStatus.UNSUPPORTED.value,
            is_feasible=False,
            failure_reason=f"Scenario type '{scen_type_raw}' is not grounded in existing physical models.",
            warnings=[f"Model cannot simulate unsupported type: {scen_type_raw}"],
            comparison=None,
            simulated_campaign=None,
        )

    # Check bounds on modification counts
    if len(raw_mods) > MAX_MODIFICATIONS_PER_SCENARIO:
        raise ValueError(f"Scenario exceeds maximum modifications limit ({MAX_MODIFICATIONS_PER_SCENARIO}).")

    # Validate modification parameters
    for mod in raw_mods:
        _validate_modification_bounds(mod)

    # Order modifications in deterministic precedence:
    # 1. corridor_closure -> 2. target_loss -> 3. mobility_change -> 4. operational_delay -> 5. time_constraint -> 6. objective_priority_change
    precedence = {
        ScenarioType.CORRIDOR_CLOSURE.value: 1,
        ScenarioType.TARGET_LOSS.value: 2,
        ScenarioType.MOBILITY_CHANGE.value: 3,
        ScenarioType.OPERATIONAL_DELAY.value: 4,
        ScenarioType.TIME_CONSTRAINT.value: 5,
        ScenarioType.OBJECTIVE_PRIORITY_CHANGE.value: 6,
    }
    sorted_mods = sorted(raw_mods, key=lambda m: precedence.get(m.get("type", ""), 99))

    # Identify frozen completed targets from progress
    prev_progress = campaign.progress or {}
    completed_target_ids: Set[str] = set(prev_progress.get("completed_target_ids", []))
    blocked_target_ids: Set[str] = set(prev_progress.get("blocked_target_ids", []))
    active_sol_index = int(prev_progress.get("active_sol_index", 1))

    # Keep completed past sorties frozen
    frozen_sorties = [copy.deepcopy(s) for s in campaign.sorties if s.sol_index < active_sol_index]
    for s in frozen_sorties:
        completed_target_ids.update(s.target_ids)

    # Deep copy configuration and candidate targets
    sim_cfg = copy.deepcopy(campaign.config)
    if planning_prof:
        sim_cfg.planning_profile = planning_prof

    sim_targets: List[CampaignTarget] = []
    target_dict: Dict[str, CampaignTarget] = {}
    for t in campaign.targets:
        t_copy = copy.deepcopy(t)
        sim_targets.append(t_copy)
        target_dict[t_copy.id] = t_copy

    warnings: List[str] = []
    causal_attribution: Dict[str, str] = {}
    blocked_mask = np.zeros(terrain.elevation.shape, dtype=bool)

    # Track scenario-specific exclusions
    excluded_target_ids: Set[str] = set()
    total_operational_delay_s = 0.0

    # Apply modifications
    for mod in sorted_mods:
        m_type = mod.get("type")

        # 1. Corridor Closure / Obstacle Hazard
        if m_type == ScenarioType.CORRIDOR_CLOSURE.value:
            if "center_rc" in mod and isinstance(mod["center_rc"], (list, tuple)) and len(mod["center_rc"]) == 2:
                r, c = int(mod["center_rc"][0]), int(mod["center_rc"][1])
            else:
                r = int(mod.get("center_row", 122))
                c = int(mod.get("center_col", 162))
            rad = float(mod.get("radius_m", 60.0))
            footprint = compute_circular_footprint(
                center_rc=(r, c),
                radius_m=rad,
                terrain=terrain,
            )
            for fr, fc in footprint:
                blocked_mask[fr, fc] = True
            warnings.append(f"Physical rockfall obstacle of radius {rad:.0f}m injected at ({r}, {c}).")

        # 2. Target Loss / Inaccessibility
        elif m_type == ScenarioType.TARGET_LOSS.value:
            lost_tid = str(mod.get("target_id"))
            if lost_tid in target_dict:
                excluded_target_ids.add(lost_tid)
                reason = mod.get("reason", "Target sensor / instrument payload failure")
                target_dict[lost_tid].status = TargetStatus.UNREACHABLE.value
                target_dict[lost_tid].unscheduled_reason = f"Target loss: {reason}"
                causal_attribution[lost_tid] = f"Directly marked unavailable: {reason}"
                warnings.append(f"Target '{lost_tid}' lost: {reason}")
            else:
                warnings.append(f"Target loss referenced non-existent target '{lost_tid}' (ignored).")

        # 3. Mobility Derating / Speed Reduction
        elif m_type == ScenarioType.MOBILITY_CHANGE.value:
            speed_factor = float(mod.get("speed_factor", 0.6))
            sim_cfg.speed_multiplier = sim_cfg.speed_multiplier * speed_factor
            warnings.append(f"Mobility speed multiplier derated by factor {speed_factor:.2f} (new multiplier: {sim_cfg.speed_multiplier:.2f}).")
            if "max_slope_deg" in mod:
                max_slope = float(mod["max_slope_deg"])
                # Mask slopes exceeding threshold
                dy, dx = np.gradient(terrain.elevation, terrain.dy_ground_m, terrain.dx_ground_m)
                slope_deg = np.degrees(np.arctan(np.sqrt(dy * dy + dx * dx)))
                blocked_mask = blocked_mask | (slope_deg > max_slope)
                warnings.append(f"Slope mobility threshold tightened to {max_slope:.1f}°.")

        # 4. Operational Delay
        elif m_type == ScenarioType.OPERATIONAL_DELAY.value:
            delay = float(mod.get("delay_s", 1800.0))
            total_operational_delay_s += delay
            warnings.append(f"Operational delay hold of {delay:.0f}s ({delay/60:.1f}m) injected.")

        # 5. Time Constraints
        elif m_type == ScenarioType.TIME_CONSTRAINT.value:
            if "max_duration_per_sortie_s" in mod:
                new_dur = float(mod["max_duration_per_sortie_s"])
                sim_cfg.max_duration_per_sortie_s = new_dur
                warnings.append(f"Sortie duration window constricted to {new_dur:.0f}s ({new_dur/3600:.1f}h).")
            if "max_sols" in mod:
                new_sols = int(mod["max_sols"])
                sim_cfg.max_sols = new_sols
                warnings.append(f"Campaign maximum sols constricted to {new_sols} sols.")

        # 6. Objective Priority Shifts
        elif m_type == ScenarioType.OBJECTIVE_PRIORITY_CHANGE.value:
            weights = mod.get("objective_weights", {})
            for tid, target in target_dict.items():
                w = 1.0
                if target.science_objective and target.science_objective in weights:
                    w = float(weights[target.science_objective])
                elif tid in weights:
                    w = float(weights[tid])
                target.priority_score = target.priority_score * w
            warnings.append("Objective priority weights updated.")

    # Account for operational hold by adjusting sortie budget if hold injected
    if total_operational_delay_s > 0:
        sim_cfg.max_duration_per_sortie_s = max(
            MIN_SORTIE_DURATION_S,
            sim_cfg.max_duration_per_sortie_s - (total_operational_delay_s / max(1, sim_cfg.max_sols or 1)),
        )

    # Cascade Target Loss to Downstream Dependent Targets
    cascade_changed = True
    while cascade_changed:
        cascade_changed = False
        for t in sim_targets:
            if t.id not in excluded_target_ids and t.id not in completed_target_ids:
                for prereq in t.prerequisites:
                    if prereq in excluded_target_ids or prereq in blocked_target_ids:
                        excluded_target_ids.add(t.id)
                        t.status = TargetStatus.REJECTED_PREREQUISITE_FAILED.value
                        t.unscheduled_reason = f"Prerequisite '{prereq}' is unavailable or blocked in scenario."
                        causal_attribution[t.id] = f"Prerequisite '{prereq}' unavailable due to upstream scenario disruption."
                        cascade_changed = True
                        break

    # Build uncompleted candidate pool
    uncompleted_candidates = [
        t for t in sim_targets
        if t.id not in completed_target_ids and t.id not in excluded_target_ids and t.id not in blocked_target_ids
    ]

    # Clear satisfied prerequisites for replanning remaining sorties
    for cand in uncompleted_candidates:
        cand.prerequisites = [p for p in cand.prerequisites if p not in completed_target_ids]

    sols_remaining = max(1, (sim_cfg.max_sols or 10) - len(frozen_sorties))
    sim_cfg.max_sols = sols_remaining

    # Execute deterministic replanning
    try:
        sub_plan = plan_mission_campaign(
            campaign_id=campaign.campaign_id,
            name=campaign.name,
            config=sim_cfg,
            targets=uncompleted_candidates,
            terrain=terrain,
            blocked_mask=blocked_mask if np.any(blocked_mask) else None,
            description=f"What-if simulation: {scen_name}",
        )
    except Exception as e:
        logger.warning("Replanning failed during what-if scenario %s: %s", scen_id, e)
        return CampaignScenario(
            scenario_id=scen_id,
            campaign_id=campaign.campaign_id,
            source_version=campaign.version,
            name=scen_name,
            description=scen_desc,
            scenario_type=scen_type_raw,
            modifications=raw_mods,
            planning_profile=planning_prof,
            created_at_utc=timestamp,
            status=ScenarioStatus.FAILED.value,
            is_feasible=False,
            failure_reason=f"Planner exception: {str(e)}",
            warnings=warnings + [str(e)],
            comparison=None,
            simulated_campaign=None,
        )

    # Shift sol indices of newly planned sorties to follow frozen past sols
    new_sorties: List[CampaignSortie] = []
    for idx, sub_s in enumerate(sub_plan.sorties):
        s_copy = copy.deepcopy(sub_s)
        s_copy.sol_index = len(frozen_sorties) + idx + 1
        s_copy.sortie_id = f"sortie_sol_{s_copy.sol_index:02d}"
        s_copy.name = f"Sol {s_copy.sol_index}: {', '.join(s_copy.target_names[:2])}..."
        new_sorties.append(s_copy)

    combined_sorties = frozen_sorties + new_sorties

    # Compute scenario summary metrics
    total_dist = round(sum(s.distance_m for s in combined_sorties), 1)
    total_travel = round(sum(s.travel_time_s for s in combined_sorties), 1)
    total_dwell = round(sum(s.dwell_time_s for s in combined_sorties), 1)
    total_dur = round(sum(s.total_duration_s for s in combined_sorties) + total_operational_delay_s, 1)
    total_score = round(sum(s.science_score for s in combined_sorties), 1)

    sched_target_ids: Set[str] = set(tid for s in combined_sorties for tid in s.target_ids)
    num_scheduled = len(sched_target_ids)
    num_unscheduled = len(campaign.targets) - num_scheduled

    is_feasible = bool(combined_sorties) and all(s.is_feasible for s in combined_sorties)
    if is_feasible:
        if num_scheduled == len(campaign.targets):
            overall_status = CampaignStatus.FEASIBLE.value
        elif num_scheduled > 0:
            overall_status = CampaignStatus.PARTIALLY_FEASIBLE.value
        else:
            overall_status = CampaignStatus.INFEASIBLE.value
            is_feasible = False
    else:
        overall_status = CampaignStatus.INFEASIBLE.value

    # Identify deferred / unscheduled targets
    deferred_target_ids = []
    blocked_in_sim = list(excluded_target_ids.union(blocked_target_ids))
    for t in sim_targets:
        if t.id not in sched_target_ids and t.id not in blocked_in_sim:
            deferred_target_ids.append(t.id)
            if t.id not in causal_attribution:
                causal_attribution[t.id] = "Deferred: Sortie time limits or sol limits reached before target could be traversed."

    sim_summary = CampaignSummary(
        total_sols=len(combined_sorties),
        total_sorties=len(combined_sorties),
        total_distance_m=total_dist,
        total_travel_time_s=total_travel,
        total_dwell_time_s=total_dwell,
        total_duration_s=total_dur,
        total_science_score=total_score,
        targets_total=len(campaign.targets),
        targets_scheduled=num_scheduled,
        targets_unscheduled=num_unscheduled,
        targets_completed=len(completed_target_ids),
        is_campaign_feasible=is_feasible,
        overall_status=overall_status,
        bottlenecks_and_notes=warnings,
    )

    sim_campaign = MissionCampaign(
        campaign_id=campaign.campaign_id,
        name=f"{campaign.name} (What-If: {scen_name})",
        description=f"What-if simulation revision for scenario '{scen_name}'.",
        version=campaign.version,
        revision_id=f"whatif_{scen_id[:8]}",
        parent_campaign_id=campaign.campaign_id,
        config=sim_cfg,
        targets=sim_targets,
        sorties=combined_sorties,
        summary=sim_summary,
    )

    # Compute Comparative Metrics against Baseline Campaign
    base_summary = campaign.summary
    base_sched_ids = set(tid for s in campaign.sorties for tid in s.target_ids)
    lost_tids = sorted(list(base_sched_ids - sched_target_ids))
    gained_tids = sorted(list(sched_target_ids - base_sched_ids))

    comparison = ScenarioComparison(
        delta_sols=len(combined_sorties) - base_summary.total_sols,
        delta_sorties=len(combined_sorties) - base_summary.total_sorties,
        delta_distance_m=total_dist - base_summary.total_distance_m,
        delta_duration_s=total_dur - base_summary.total_duration_s,
        delta_science_score=total_score - base_summary.total_science_score,
        targets_scheduled_delta=num_scheduled - len(base_sched_ids),
        baseline_targets_scheduled=len(base_sched_ids),
        scenario_targets_scheduled=num_scheduled,
        lost_target_ids=lost_tids,
        gained_target_ids=gained_tids,
        deferred_target_ids=sorted(deferred_target_ids),
        blocked_target_ids=sorted(blocked_in_sim),
        causal_attribution=causal_attribution,
        feasibility_status=overall_status,
    )

    failure_reason = None
    if not is_feasible:
        failure_reason = "No feasible sorties could be planned within operational constraints."
        scen_status = ScenarioStatus.INFEASIBLE.value
    else:
        scen_status = ScenarioStatus.COMPLETED.value

    result_scenario = CampaignScenario(
        scenario_id=scen_id,
        campaign_id=campaign.campaign_id,
        source_version=campaign.version,
        name=scen_name,
        description=scen_desc,
        scenario_type=scen_type_raw,
        modifications=sorted_mods,
        planning_profile=planning_prof,
        created_at_utc=timestamp,
        status=scen_status,
        is_feasible=is_feasible,
        failure_reason=failure_reason,
        warnings=warnings,
        comparison=comparison,
        simulated_campaign=sim_campaign.to_dict(),
    )

    # Validate against JSON schema
    validate_campaign_scenario_record(result_scenario.to_dict())
    return result_scenario


def evaluate_campaign_scenarios_batch(
    campaign: MissionCampaign,
    terrain: TerrainGrid,
    scenario_specs: List[Dict[str, Any]],
) -> List[CampaignScenario]:
    """
    Evaluates a batch of what-if scenarios against a single baseline campaign.
    Enforces maximum batch size to prevent computational exhaustion.
    """
    if not scenario_specs:
        return []
    if len(scenario_specs) > MAX_SCENARIOS_PER_BATCH:
        raise ValueError(f"Batch size {len(scenario_specs)} exceeds maximum limit ({MAX_SCENARIOS_PER_BATCH}).")

    results: List[CampaignScenario] = []
    for spec in scenario_specs:
        scen = evaluate_campaign_scenario(
            campaign=campaign,
            terrain=terrain,
            scenario_spec=spec,
        )
        results.append(scen)
    return results


def promote_scenario_to_campaign_version(
    campaign: MissionCampaign,
    scenario: CampaignScenario,
    name_override: Optional[str] = None,
) -> MissionCampaign:
    """
    Promotes a simulated what-if scenario to an official new campaign version (v{n+1}).
    Preserves prior versions and archives revision comparison metadata.
    """
    if not scenario.is_feasible or not scenario.simulated_campaign:
        raise ValueError(f"Cannot promote infeasible or uncomputed scenario '{scenario.scenario_id}'.")

    new_version = campaign.version + 1
    new_rev_id = f"rev_{new_version:02d}_whatif_{scenario.scenario_id[:8]}"

    sim_dict = copy.deepcopy(scenario.simulated_campaign)
    sim_dict["version"] = new_version
    sim_dict["revision_id"] = new_rev_id
    sim_dict["name"] = name_override or f"{campaign.name} (v{new_version}: {scenario.name})"
    sim_dict["parent_campaign_id"] = campaign.campaign_id

    # Add revision comparison if present
    if scenario.comparison:
        comp = scenario.comparison
        sim_dict["revision_comparison"] = {
            "delta_distance_m": round(comp.delta_distance_m, 1),
            "delta_duration_s": round(comp.delta_duration_s, 1),
            "delta_science_score": round(comp.delta_science_score, 1),
            "newly_unscheduled_targets": comp.lost_target_ids,
            "resequenced_sorties": [s["sortie_id"] for s in sim_dict.get("sorties", [])],
            "reprioritized_targets": comp.gained_target_ids,
        }

    promoted_campaign = MissionCampaign.from_dict(sim_dict)
    return promoted_campaign
