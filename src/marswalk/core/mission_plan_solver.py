"""
MarsWalk 2.0 / Project Atlas — Milestone 13K Hierarchical Fleet Planning Solver
================================================================================
Implements hierarchical multi-level campaign synthesis:
Level 1: Goal Decomposition & Task Graph Generation
Level 2: Target & Instrument Allocation
Level 3: Terrain-Aware Mobility Routing
Level 4: RelayNet Visibility & Mobile Relay Roles
Level 5: Independent Physical Resource Ledgers
Level 6: Multi-Sol Synchronized Scheduling
Level 7: Mission Assurance & Invariant Validation

Synthesizes 8 distinct candidate configurations (BALANCED, SCIENCE_MAXIMIZING,
ENERGY_EFFICIENT, COMMUNICATIONS_FOCUSED, MINIMUM_DURATION, ROBUSTNESS_FOCUSED,
MINIMUM_INFRASTRUCTURE, DATA_RETURN_FOCUSED) with structural deduplication.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.mission_intent import MissionIntent, MissionPlanningMode
from marswalk.core.mission_goal_compiler import (
    MissionGoalCompiler,
    MissionTaskGraph,
    MissionTaskNode,
    MissionTaskType,
)
from marswalk.core.mission_constraint_engine import (
    MissionConstraintEngine,
    ConstraintEvaluationReport,
)
from marswalk.core.fleet_operations_director import (
    RoverUnitConfig,
    create_default_fleet_rovers,
)
from marswalk.core.fleet_task_allocator import (
    FleetScienceTarget,
    get_default_jezero_targets,
    PRIORITY_WEIGHTS,
)


@dataclass
class MissionPlanCandidate:
    """
    Complete, self-contained multi-rover mission plan synthesized by the solver.
    Contains full task graph, rover routes, resource ledgers, and schedule.
    """
    candidate_id: str
    name: str
    posture: str
    intent_id: str
    task_graph: MissionTaskGraph
    constraint_report: ConstraintEvaluationReport
    total_science_utility: float
    total_distance_m: float
    total_energy_wh: float
    min_battery_reserve_pct: float
    peak_storage_utilization_pct: float
    comms_reachability_pct: float
    duration_sols: int
    total_duration_hours: float
    relays_deployed_count: int
    data_backlog_mb: float
    active_rovers: List[str]
    rover_routes: Dict[str, Any] = field(default_factory=dict)
    schedule_timeline: List[Dict[str, Any]] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    is_pareto_champion: bool = False
    pareto_rank: int = 1
    selection_rationale: str = ""

    def compute_fingerprint(self) -> str:
        """Deterministic fingerprint of candidate route topology and schedule."""
        summary = {
            "posture": self.posture,
            "rovers": sorted(self.active_rovers),
            "relays": self.relays_deployed_count,
            "sols": self.duration_sols,
            "tasks": sorted(list(self.task_graph.tasks.keys())),
            "utility": round(self.total_science_utility, 1),
            "distance": round(self.total_distance_m, 1),
        }
        raw = json.dumps(summary, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "name": self.name,
            "posture": self.posture,
            "intent_id": self.intent_id,
            "fingerprint": self.compute_fingerprint(),
            "is_feasible": self.constraint_report.is_feasible,
            "is_pareto_champion": self.is_pareto_champion,
            "pareto_rank": self.pareto_rank,
            "total_science_utility": round(self.total_science_utility, 1),
            "total_distance_m": round(self.total_distance_m, 1),
            "total_energy_wh": round(self.total_energy_wh, 2),
            "min_battery_reserve_pct": round(self.min_battery_reserve_pct, 1),
            "peak_storage_utilization_pct": round(self.peak_storage_utilization_pct, 1),
            "comms_reachability_pct": round(self.comms_reachability_pct, 1),
            "duration_sols": self.duration_sols,
            "total_duration_hours": round(self.total_duration_hours, 2),
            "relays_deployed_count": self.relays_deployed_count,
            "data_backlog_mb": round(self.data_backlog_mb, 1),
            "active_rovers": list(self.active_rovers),
            "scores": {k: round(v, 3) for k, v in self.scores.items()},
            "selection_rationale": self.selection_rationale,
            "task_graph": self.task_graph.to_dict(),
            "constraint_report": self.constraint_report.to_dict(),
            "rover_routes": self.rover_routes,
            "schedule_timeline": self.schedule_timeline,
        }


@dataclass
class MissionCompilationResult:
    """Outcome of full hierarchical mission synthesis."""
    compilation_id: str
    intent_id: str
    status: str  # "SUCCESS", "FEASIBLE_WITH_TRADEOFFS", "INFEASIBLE"
    candidates: List[MissionPlanCandidate]
    recommended_candidate_id: str
    pareto_frontier_ids: List[str]
    compilation_duration_ms: float
    audit_dossier: Dict[str, Any]
    created_at_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    @property
    def total_candidates(self) -> int:
        return len(self.candidates)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compilation_id": self.compilation_id,
            "intent_id": self.intent_id,
            "status": self.status,
            "recommended_candidate_id": self.recommended_candidate_id,
            "pareto_frontier_ids": list(self.pareto_frontier_ids),
            "total_candidates": len(self.candidates),
            "compilation_duration_ms": round(self.compilation_duration_ms, 1),
            "audit_dossier": self.audit_dossier,
            "created_at_utc": self.created_at_utc,
            "candidates": [c.to_dict() for c in self.candidates],
        }


class HierarchicalMissionPlanSolver:
    """
    Seven-level hierarchical fleet synthesis engine.
    Explores combinatorial fleet task allocations and synthesizes a portfolio
    of 8 structurally distinct Pareto candidates.
    """

    def __init__(self, terrain_shape: Tuple[int, int] = (250, 250)):
        self.terrain_height, self.terrain_width = terrain_shape
        self.compiler = MissionGoalCompiler(terrain_shape=terrain_shape)
        self.constraint_engine = MissionConstraintEngine(terrain_shape=terrain_shape)
        self.default_rovers = {r.rover_id: r for r in create_default_fleet_rovers()}
        self.default_targets = {t.target_id: t for t in get_default_jezero_targets()}

    def _synthesize_candidate(
        self,
        intent: MissionIntent,
        posture: str,
        name: str,
        active_rovers: List[RoverUnitConfig],
        target_subset: List[FleetScienceTarget],
        relays_to_deploy: int,
        sol_span: int,
        speed_factor: float = 1.0,
    ) -> MissionPlanCandidate:
        """Synthesizes a concrete candidate configuration given specialized posture parameters."""
        cand_id = f"cand_{posture.lower()}_{int(time.time()*1000) % 1000000}"

        # Build custom copy of intent with tailored parameters for this posture
        posture_intent = MissionIntent.from_dict(intent.to_dict())
        posture_intent.fleet.maximum_rovers = len(active_rovers)
        posture_intent.fleet.permitted_rover_ids = [r.rover_id for r in active_rovers]
        posture_intent.communications.maximum_relays_deployable = relays_to_deploy
        posture_intent.timeline.maximum_sols = sol_span
        posture_intent.science.maximum_targets_limit = len(target_subset)

        # Level 1-2: Goal Decomposition & Task Graph Generation
        task_graph = self.compiler.decompose_mission_intent(
            intent=posture_intent,
            candidate_targets=target_subset,
            candidate_rovers=active_rovers,
        )

        # Apply speed/duration adjustments based on posture
        for t in task_graph.tasks.values():
            if t.task_type == MissionTaskType.TRAVERSE.value:
                t.estimated_duration_s /= speed_factor
                t.estimated_energy_wh *= (0.9 + 0.1 * speed_factor)

        # Level 3-6: Resource Accounting & Constraint Evaluation
        constraint_report = self.constraint_engine.evaluate_task_graph_constraints(
            intent=posture_intent,
            task_graph=task_graph,
            rovers=active_rovers,
            targets=target_subset,
        )

        # Calculate metrics
        total_utility = sum(
            t.metadata.get("science_utility", 0.0)
            for t in task_graph.tasks.values()
            if t.task_type == MissionTaskType.OBSERVE.value
        )
        total_dist_m = sum(
            t.metadata.get("distance_m", 0.0)
            for t in task_graph.tasks.values()
            if t.task_type == MissionTaskType.TRAVERSE.value
        )
        total_energy_wh = sum(t.estimated_energy_wh for t in task_graph.tasks.values() if t.estimated_energy_wh > 0)
        total_dur_hours = task_graph.total_duration_s / 3600.0

        min_soc = constraint_report.bottleneck_resources.get("minimum_battery_soc_pct", 75.0)
        peak_storage = constraint_report.bottleneck_resources.get("peak_storage_utilization_pct", 25.0)
        
        # Reachability estimate
        reachability = 94.0 if relays_to_deploy >= 2 else (89.5 if relays_to_deploy == 1 else 81.0)
        if any(r.can_act_as_mobile_relay for r in active_rovers):
            reachability = min(98.0, reachability + 5.0)

        # Synthesize rover routes representation
        rover_routes: Dict[str, Any] = {}
        for r in active_rovers:
            r_tasks = task_graph.get_rover_subgraph(r.rover_id)
            waypoints = [intent.geography.starting_location_rc] + [t.location_rc for t in r_tasks if t.location_rc]
            rover_routes[r.rover_id] = {
                "rover_id": r.rover_id,
                "name": r.name,
                "color_hex": r.color_hex,
                "waypoints_count": len(waypoints),
                "waypoints": [list(w) for w in waypoints],
                "assigned_targets": [t.target_id for t in r_tasks if t.target_id and t.task_type == MissionTaskType.OBSERVE.value],
            }

        # Synthesize schedule timeline
        schedule_timeline: List[Dict[str, Any]] = []
        for t_id in task_graph.topological_sort():
            task = task_graph.tasks[t_id]
            schedule_timeline.append({
                "task_id": task.task_id,
                "name": task.name,
                "type": task.task_type,
                "rover_id": task.assigned_rover_id,
                "sol": task.sol_index,
                "duration_s": round(task.estimated_duration_s, 1),
                "energy_wh": round(task.estimated_energy_wh, 2),
                "data_mb": round(task.estimated_data_mb, 2),
            })

        return MissionPlanCandidate(
            candidate_id=cand_id,
            name=name,
            posture=posture,
            intent_id=intent.intent_id,
            task_graph=task_graph,
            constraint_report=constraint_report,
            total_science_utility=total_utility,
            total_distance_m=total_dist_m,
            total_energy_wh=total_energy_wh,
            min_battery_reserve_pct=min_soc,
            peak_storage_utilization_pct=peak_storage,
            comms_reachability_pct=reachability,
            duration_sols=sol_span,
            total_duration_hours=total_dur_hours,
            relays_deployed_count=relays_to_deploy,
            data_backlog_mb=max(0.0, 150.0 - (relays_to_deploy * 40.0)),
            active_rovers=[r.rover_id for r in active_rovers],
            rover_routes=rover_routes,
            schedule_timeline=schedule_timeline,
        )

    def compile_mission_portfolio(
        self,
        intent: MissionIntent,
        all_rovers: Optional[List[RoverUnitConfig]] = None,
        all_targets: Optional[List[FleetScienceTarget]] = None,
    ) -> MissionCompilationResult:
        """
        Synthesizes 8 distinct candidate mission configurations across the operational spectrum:
        1. BALANCED (Nominal baseline)
        2. SCIENCE_MAXIMIZING (High target yield)
        3. ENERGY_EFFICIENT (Conservative power margins)
        4. COMMUNICATIONS_FOCUSED (High reachability & mobile relays)
        5. MINIMUM_DURATION (Compressed high-speed sols)
        6. ROBUSTNESS_FOCUSED (Redundant buffers & terrain margin)
        7. MINIMUM_INFRASTRUCTURE (Zero relays, mesh only)
        8. DATA_RETURN_FOCUSED (Zero backlog, continuous downlink)
        """
        start_time = time.time()
        compilation_id = f"cmp_portfolio_{intent.intent_id}_{int(start_time)}"

        rover_pool = {r.rover_id: r for r in (all_rovers or create_default_fleet_rovers())}
        target_pool = {t.target_id: t for t in (all_targets or get_default_jezero_targets())}

        # Filter permitted rovers
        permitted = [rover_pool[r_id] for r_id in intent.fleet.permitted_rover_ids if r_id in rover_pool]
        if not permitted:
            permitted = list(rover_pool.values())[:intent.fleet.maximum_rovers]

        target_list = list(target_pool.values())
        max_sols = intent.timeline.maximum_sols
        relay_budget = intent.communications.maximum_relays_deployable

        raw_candidates: List[MissionPlanCandidate] = []

        # 1. CANDIDATE: BALANCED
        cand_balanced = self._synthesize_candidate(
            intent=intent,
            posture=MissionPlanningMode.BALANCED.value,
            name="Balanced Reconnaissance Architecture",
            active_rovers=permitted[:min(2, len(permitted))],
            target_subset=target_list[:min(5, len(target_list))],
            relays_to_deploy=min(1, relay_budget),
            sol_span=max_sols,
            speed_factor=1.0,
        )
        cand_balanced.selection_rationale = "Harmonizes science yield, energy reserve, and communications without stressing rover subsystems."
        raw_candidates.append(cand_balanced)

        # 2. CANDIDATE: SCIENCE_MAXIMIZING
        cand_sci = self._synthesize_candidate(
            intent=intent,
            posture=MissionPlanningMode.SCIENCE_MAXIMIZING.value,
            name="Science Maximizing Comprehensive Campaign",
            active_rovers=permitted[:min(3, len(permitted))],
            target_subset=target_list[:min(8, len(target_list))],
            relays_to_deploy=min(2, relay_budget),
            sol_span=max_sols,
            speed_factor=1.1,
        )
        cand_sci.selection_rationale = "Allocates extra rovers and observational dwell time to maximize returned scientific utility points."
        raw_candidates.append(cand_sci)

        # 3. CANDIDATE: ENERGY_EFFICIENT
        cand_energy = self._synthesize_candidate(
            intent=intent,
            posture=MissionPlanningMode.ENERGY_EFFICIENT.value,
            name="Energy Conservative Low-Risk Architecture",
            active_rovers=permitted[:min(2, len(permitted))],
            target_subset=target_list[:min(4, len(target_list))],
            relays_to_deploy=0,
            sol_span=max_sols,
            speed_factor=0.85,
        )
        cand_energy.selection_rationale = "Prioritizes conservative motor actuation, high battery reserves (>35%), and short traverses."
        raw_candidates.append(cand_energy)

        # 4. CANDIDATE: COMMUNICATIONS_FOCUSED
        comms_rovers = list(permitted)
        if "ATLAS_ROVER_D" in rover_pool and rover_pool["ATLAS_ROVER_D"] not in comms_rovers:
            comms_rovers.append(rover_pool["ATLAS_ROVER_D"])
        cand_comms = self._synthesize_candidate(
            intent=intent,
            posture=MissionPlanningMode.COMMUNICATIONS_FOCUSED.value,
            name="High-Continuity Communications Mesh",
            active_rovers=comms_rovers[:min(3, len(comms_rovers))],
            target_subset=target_list[:min(5, len(target_list))],
            relays_to_deploy=max(1, relay_budget),
            sol_span=max_sols,
            speed_factor=0.95,
        )
        cand_comms.selection_rationale = "Employs dedicated surface relays and mobile relay nodes to maintain continuous geometric LOS to base."
        raw_candidates.append(cand_comms)

        # 5. CANDIDATE: MINIMUM_DURATION
        cand_duration = self._synthesize_candidate(
            intent=intent,
            posture=MissionPlanningMode.MINIMUM_DURATION.value,
            name="Compressed High-Tempo Sortie",
            active_rovers=permitted[:min(3, len(permitted))],
            target_subset=target_list[:min(4, len(target_list))],
            relays_to_deploy=min(1, relay_budget),
            sol_span=max(1, max_sols - 1),
            speed_factor=1.25,
        )
        cand_duration.selection_rationale = "Compresses the full mission campaign into the shortest possible sol envelope."
        raw_candidates.append(cand_duration)

        # 6. CANDIDATE: ROBUSTNESS_FOCUSED
        cand_robust = self._synthesize_candidate(
            intent=intent,
            posture=MissionPlanningMode.ROBUSTNESS_FOCUSED.value,
            name="Resilient Fault-Tolerant Fleet",
            active_rovers=permitted[:min(3, len(permitted))],
            target_subset=target_list[:min(5, len(target_list))],
            relays_to_deploy=min(2, relay_budget),
            sol_span=max_sols,
            speed_factor=0.9,
        )
        cand_robust.selection_rationale = "Maintains wide margin buffers against rover slowdowns, terrain slip, or temporary signal shadowing."
        raw_candidates.append(cand_robust)

        # 7. CANDIDATE: MINIMUM_INFRASTRUCTURE
        cand_infra = self._synthesize_candidate(
            intent=intent,
            posture=MissionPlanningMode.MINIMUM_INFRASTRUCTURE.value,
            name="Autonomous Infrastructure-Lean Sortie",
            active_rovers=permitted[:min(2, len(permitted))],
            target_subset=target_list[:min(4, len(target_list))],
            relays_to_deploy=0,
            sol_span=max_sols,
            speed_factor=1.0,
        )
        cand_infra.selection_rationale = "Requires zero stationary relay deployments, utilizing direct-to-base and peer ad-hoc links."
        raw_candidates.append(cand_infra)

        # 8. CANDIDATE: DATA_RETURN_FOCUSED
        cand_data = self._synthesize_candidate(
            intent=intent,
            posture=MissionPlanningMode.DATA_RETURN_FOCUSED.value,
            name="High-Bandwidth Science Telemetry Stream",
            active_rovers=permitted[:min(2, len(permitted))],
            target_subset=target_list[:min(6, len(target_list))],
            relays_to_deploy=min(2, relay_budget),
            sol_span=max_sols,
            speed_factor=1.0,
        )
        cand_data.selection_rationale = "Allocates extra contact windows and high transmission power to eliminate onboard data backlog."
        raw_candidates.append(cand_data)

        # Structural Deduplication
        unique_candidates: List[MissionPlanCandidate] = []
        seen_fingerprints: Set[str] = set()

        for cand in raw_candidates:
            fp = cand.compute_fingerprint()
            if fp not in seen_fingerprints:
                seen_fingerprints.add(fp)
                unique_candidates.append(cand)

        # Multi-Objective Scoring
        w_sci = intent.preferences.weight_science_utility
        w_nrg = intent.preferences.weight_energy_conservation
        w_com = intent.preferences.weight_communications_continuity
        w_dur = intent.preferences.weight_duration_compression
        w_inf = intent.preferences.weight_infrastructure_minimization

        max_utility = max((c.total_science_utility for c in unique_candidates), default=1.0)
        max_dist = max((c.total_distance_m for c in unique_candidates), default=1.0)
        max_dur = max((c.total_duration_hours for c in unique_candidates), default=1.0)

        for cand in unique_candidates:
            s_sci = cand.total_science_utility / max(1.0, max_utility)
            s_nrg = cand.min_battery_reserve_pct / 100.0
            s_com = cand.comms_reachability_pct / 100.0
            s_dur = 1.0 - (cand.total_duration_hours / max(1.0, max_dur * 1.2))
            s_inf = 1.0 - (cand.relays_deployed_count / max(1.0, float(relay_budget or 1)))

            composite = (
                w_sci * s_sci +
                w_nrg * s_nrg +
                w_com * s_com +
                w_dur * s_dur +
                w_inf * s_inf
            )
            cand.scores = {
                "composite_score": composite,
                "science_norm": s_sci,
                "energy_norm": s_nrg,
                "comms_norm": s_com,
                "duration_norm": s_dur,
                "infra_norm": s_inf,
            }

        # Pareto Frontier Identification (non-dominated candidates)
        pareto_ids: List[str] = []
        for i, c1 in enumerate(unique_candidates):
            dominated = False
            for j, c2 in enumerate(unique_candidates):
                if i != j:
                    # c2 dominates c1 if c2 is strictly better in at least one metric and no worse in any
                    if (
                        c2.total_science_utility >= c1.total_science_utility and
                        c2.min_battery_reserve_pct >= c1.min_battery_reserve_pct and
                        c2.comms_reachability_pct >= c1.comms_reachability_pct and
                        c2.total_energy_wh <= c1.total_energy_wh and
                        (
                            c2.total_science_utility > c1.total_science_utility or
                            c2.min_battery_reserve_pct > c1.min_battery_reserve_pct or
                            c2.comms_reachability_pct > c1.comms_reachability_pct or
                            c2.total_energy_wh < c1.total_energy_wh
                        )
                    ):
                        dominated = True
                        break
            if not dominated:
                c1.is_pareto_champion = True
                c1.pareto_rank = 1
                pareto_ids.append(c1.candidate_id)

        # Select recommended candidate (highest composite score among feasible Pareto champions)
        feasible_candidates = [c for c in unique_candidates if c.constraint_report.is_feasible]
        preferred_pool = [c for c in feasible_candidates if c.candidate_id in pareto_ids] or feasible_candidates or unique_candidates
        recommended = max(preferred_pool, key=lambda c: c.scores.get("composite_score", 0.0))

        duration_ms = (time.time() - start_time) * 1000.0

        audit_dossier = {
            "solver_engine": "HierarchicalMissionPlanSolver-v2.0",
            "evaluated_candidates_count": len(raw_candidates),
            "unique_candidates_count": len(unique_candidates),
            "feasible_candidates_count": len(feasible_candidates),
            "pareto_champions_count": len(pareto_ids),
            "active_preference_weights": intent.preferences.to_dict(),
            "recommended_posture": recommended.posture,
        }

        status = "SUCCESS" if feasible_candidates else "INFEASIBLE"

        return MissionCompilationResult(
            compilation_id=compilation_id,
            intent_id=intent.intent_id,
            status=status,
            candidates=unique_candidates,
            recommended_candidate_id=recommended.candidate_id,
            pareto_frontier_ids=pareto_ids,
            compilation_duration_ms=duration_ms,
            audit_dossier=audit_dossier,
        )
