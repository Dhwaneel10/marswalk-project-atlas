"""
MarsWalk 2.0 / Project Atlas — Milestone 13K Plan Compilation Debugger
======================================================================
Investigates compiler infeasibilities and constraint violations. Traces multi-step
causal failure chains (e.g. Target -> Instrument Requirement -> Rover Compatibility
-> Energy Budget -> Temporal Limit) and synthesizes 1-click executable relaxation
options that restore mission feasibility within authentic physical envelopes.
"""

from dataclasses import dataclass, field
import copy
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.mission_intent import MissionIntent
from marswalk.core.mission_constraint_engine import (
    ConstraintEvaluationReport,
    ConflictCore,
    MissionConstraint,
)
from marswalk.core.fleet_operations_director import create_default_fleet_rovers
from marswalk.core.fleet_task_allocator import get_default_jezero_targets


@dataclass
class FailureChainStep:
    """Atomic causal reasoning step in an infeasibility diagnosis."""
    step_number: int
    category: str
    entity_id: str
    description: str
    is_root_cause: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "category": self.category,
            "entity_id": self.entity_id,
            "description": self.description,
            "is_root_cause": self.is_root_cause,
        }


@dataclass
class RelaxationOption:
    """1-click executable relaxation proposal that restores mission feasibility."""
    option_id: str
    name: str
    description: str
    parameter_path: str
    current_value: Any
    recommended_value: Any
    impact_summary: str
    confidence_score: float  # 0.0 - 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "option_id": self.option_id,
            "name": self.name,
            "description": self.description,
            "parameter_path": self.parameter_path,
            "current_value": self.current_value,
            "recommended_value": self.recommended_value,
            "impact_summary": self.impact_summary,
            "confidence_score": round(self.confidence_score, 2),
        }


@dataclass
class PlanCompilationDebugReport:
    """Full diagnostic analysis of an infeasible or marginal mission intent."""
    intent_id: str
    is_feasible: bool
    primary_failure_mode: str
    failure_chain: List[FailureChainStep] = field(default_factory=list)
    relaxation_options: List[RelaxationOption] = field(default_factory=list)
    conflict_cores: List[ConflictCore] = field(default_factory=list)
    generated_at_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "is_feasible": self.is_feasible,
            "primary_failure_mode": self.primary_failure_mode,
            "failure_chain": [s.to_dict() for s in self.failure_chain],
            "relaxation_options": [o.to_dict() for o in self.relaxation_options],
            "conflict_cores": [c.to_dict() for c in self.conflict_cores],
            "generated_at_utc": self.generated_at_utc,
        }


class PlanCompilationDebugger:
    """
    Forensic diagnostics and causal chain-of-failure analysis for the Mission Design Compiler.
    Identifies why goals were unschedulable and produces structured relaxation guidance.
    """

    def __init__(self):
        self.default_rovers = {r.rover_id: r for r in create_default_fleet_rovers()}
        self.default_targets = {t.target_id: t for t in get_default_jezero_targets()}

    def diagnose_compilation(
        self,
        intent: MissionIntent,
        constraint_report: ConstraintEvaluationReport
    ) -> PlanCompilationDebugReport:
        """Conducts deep forensic audit on an infeasible or stressed mission intent."""
        if constraint_report.is_feasible:
            return PlanCompilationDebugReport(
                intent_id=intent.intent_id,
                is_feasible=True,
                primary_failure_mode="NONE_FEASIBLE",
                failure_chain=[
                    FailureChainStep(
                        step_number=1,
                        category="VERIFICATION",
                        entity_id=intent.intent_id,
                        description="All hard physical engineering constraints are satisfied.",
                        is_root_cause=False,
                    )
                ],
                relaxation_options=[],
                conflict_cores=[],
            )

        # Infeasible: Trace failure chain
        failure_chain: List[FailureChainStep] = []
        relaxation_options: List[RelaxationOption] = []
        step_counter = 1

        primary_failure = "MULTIPLE_HARD_CONSTRAINT_VIOLATIONS"
        hard_viols = [c for c in constraint_report.constraints if c.constraint_type == "HARD" and not c.is_satisfied]

        if hard_viols:
            primary_failure = hard_viols[0].constraint_id

        # Trace Energy Violations
        energy_viols = [c for c in hard_viols if c.category == "ENERGY"]
        if energy_viols:
            e_viol = energy_viols[0]
            rover_id = e_viol.affected_rover_ids[0] if e_viol.affected_rover_ids else "ATLAS_ROVER_A"
            failure_chain.append(FailureChainStep(
                step_number=step_counter,
                category="SCIENCE_ALLOCATION",
                entity_id=intent.intent_id,
                description=f"Mission allocates targets across {intent.fleet.maximum_rovers} rover(s) over {intent.timeline.maximum_sols} sols.",
            ))
            step_counter += 1

            failure_chain.append(FailureChainStep(
                step_number=step_counter,
                category="TRAVERSE_ENERGY",
                entity_id=rover_id,
                description=f"Long traversal legs require more electrical energy than available single-sol battery capacity.",
            ))
            step_counter += 1

            failure_chain.append(FailureChainStep(
                step_number=step_counter,
                category="PHYSICAL_LIMIT",
                entity_id="BATTERY_RESERVE",
                description=f"Projected battery state of charge drops to {e_viol.actual_value:.1f}%, violating hard reserve limit of {e_viol.threshold_value:.1f}%.",
                is_root_cause=True,
            ))
            step_counter += 1

            # Synthesize relaxation options
            relaxation_options.append(RelaxationOption(
                option_id="opt_relax_soc",
                name="Relax Minimum Battery Reserve",
                description=f"Lower minimum battery reserve margin from {e_viol.threshold_value:.1f}% to {max(10.0, e_viol.actual_value - 2.0):.1f}%.",
                parameter_path="resources.minimum_battery_reserve_pct",
                current_value=e_viol.threshold_value,
                recommended_value=max(10.0, e_viol.actual_value - 2.0),
                impact_summary="Permits deeper diurnal discharge during long delta traverses while remaining within safe flight limits.",
                confidence_score=0.92,
            ))
            relaxation_options.append(RelaxationOption(
                option_id="opt_extend_sols",
                name="Extend Campaign Timeline",
                description=f"Increase campaign duration from {intent.timeline.maximum_sols} to {intent.timeline.maximum_sols + 1} sols.",
                parameter_path="timeline.maximum_sols",
                current_value=intent.timeline.maximum_sols,
                recommended_value=intent.timeline.maximum_sols + 1,
                impact_summary="Distributes total traverse distance across more sols, allowing overnight diurnal recharge between segments.",
                confidence_score=0.88,
            ))
            relaxation_options.append(RelaxationOption(
                option_id="opt_add_rover",
                name="Deploy Additional Rover",
                description=f"Increase permitted fleet size from {intent.fleet.maximum_rovers} to {min(4, intent.fleet.maximum_rovers + 1)} rovers.",
                parameter_path="fleet.maximum_rovers",
                current_value=intent.fleet.maximum_rovers,
                recommended_value=min(4, intent.fleet.maximum_rovers + 1),
                impact_summary="Shares science target workload across more vehicles, reducing per-rover energy expenditure.",
                confidence_score=0.85,
            ))

        # Trace Mandatory Target Violations
        target_viols = [c for c in hard_viols if c.category == "SCIENCE"]
        if target_viols:
            t_viol = target_viols[0]
            failure_chain.append(FailureChainStep(
                step_number=step_counter,
                category="SCIENCE_COVERAGE",
                entity_id="MANDATORY_TARGETS",
                description=f"Mandatory targets cannot be reached within specified duration or fleet constraints: {t_viol.diagnostic_message}.",
                is_root_cause=True,
            ))
            step_counter += 1

            relaxation_options.append(RelaxationOption(
                option_id="opt_convert_targets",
                name="Convert Mandatory Targets to Preferred",
                description="Move unreachable mandatory targets to the preferred targets list.",
                parameter_path="science.mandatory_target_ids",
                current_value=intent.science.mandatory_target_ids,
                recommended_value=[],
                impact_summary="Allows solver to prioritize targets opportunistically without triggering hard compilation failure.",
                confidence_score=0.95,
            ))

        return PlanCompilationDebugReport(
            intent_id=intent.intent_id,
            is_feasible=False,
            primary_failure_mode=primary_failure,
            failure_chain=failure_chain,
            relaxation_options=relaxation_options,
            conflict_cores=constraint_report.conflict_cores,
        )

    def apply_relaxation(
        self,
        intent: MissionIntent,
        option: RelaxationOption
    ) -> MissionIntent:
        """Executes a 1-click relaxation option and returns a revised MissionIntent."""
        revised = copy.deepcopy(intent)
        path = option.parameter_path.split(".")

        if len(path) == 2:
            section, attr = path[0], path[1]
            sub_obj = getattr(revised, section, None)
            if sub_obj and hasattr(sub_obj, attr):
                setattr(sub_obj, attr, option.recommended_value)
                revised.version += 1

        return revised
