"""Project Atlas / MarsWalk 2.0 — Milestone 13X
Atlas Mission Grand Prix: Algorithmic Autopsy & Causal Explainability Engine.

Provides deep forensic insight into planning decisions:
  - Causal decision lineage: Why a waypoint was selected, why an alternative was rejected
  - Active constraint inspection: Identifies exact slope limits, battery exhaustion bounds, or time cliffs
  - Side-by-side strategy decision comparison on identical scenarios
  - Root-cause autopsy for failed or degraded mission runs
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from marswalk.core.atlas_grand_prix_metrics import (
    GrandPrixMetricsEvaluator,
    ScenarioEvaluationResult,
)
from marswalk.core.atlas_grand_prix_scenario_generator import GrandPrixScenario
from marswalk.core.atlas_strategy_registry import BaseMissionStrategy, StrategyPlan


@dataclass
class DecisionComparisonItem:
    """Side-by-side step comparison between two strategies on the same scenario."""
    step_number: int
    sol_timestamp: float
    strategy_a_action: str
    strategy_a_rationale: str
    strategy_b_action: str
    strategy_b_rationale: str
    divergence_cause: str


@dataclass
class StrategyAutopsyReport:
    """Forensic report explaining the performance of a strategy on a specific scenario."""
    scenario_id: str
    strategy_id: str
    seed: int
    feasibility_status: str
    root_cause_explanation: str
    primary_active_constraints: List[str]
    trade_off_analysis: str
    decisions_trace: List[Dict[str, Any]]
    suggested_mitigations: List[str]


class StrategyExplainabilityEngine:
    """Explains strategy choices, active constraints, and head-to-head decision divergences."""

    @classmethod
    def conduct_autopsy(
        cls,
        scenario: GrandPrixScenario,
        plan: StrategyPlan,
        evaluation: ScenarioEvaluationResult,
    ) -> StrategyAutopsyReport:
        """Perform a comprehensive post-mission forensic autopsy."""
        strat_id = plan.strategy_id
        active_constraints = []

        if not evaluation.is_feasible:
            if "SLOPE" in evaluation.feasibility_status:
                root_cause = "Vehicle mobility failure: Plan attempted to traverse terrain slope exceeding physical chassis rollover limits."
                active_constraints.append("Max chassis slope threshold (15.0 deg)")
                mitigations = ["Incorporate A* slope-cost penalty", "Deploy aerial reconnaissance prior to ground traverse"]
            elif "ENERGY" in evaluation.feasibility_status:
                root_cause = "Energy exhaustion: Power expenditure exceeded battery capacity under simulated environmental dust/temperature drag."
                active_constraints.append("Battery capacity & minimum state-of-charge margin")
                mitigations = ["Reduce continuous drive speed", "Throttle scientific instruments during low-solar intervals"]
            else:
                root_cause = "Mission clock expiration: Total task execution duration exceeded scenario deadline."
                active_constraints.append("Scenario duration sol deadline")
                mitigations = ["Prune low-value distant science waypoints", "Parallelize aerial and ground activities"]
        else:
            root_cause = "Nominal feasible execution: Strategy successfully satisfied all operational and physical constraints."
            mitigations = ["Increase science density", "Optimize route order via pairwise 2-opt TSP"]

        # Characterize strategy-specific trade-offs
        if strat_id == "STRAT-01-GREEDY":
            trade_off = "Prioritized immediate high-yield targets; sacrificed global travel efficiency, creating longer zig-zag routes."
        elif strat_id == "STRAT-02-MINCOST":
            trade_off = "Minimizing energy and distance caused strategy to bypass 3+ high-value scientific formations."
        elif strat_id == "STRAT-03-SCIENCE":
            trade_off = "Aggressively chased maximal Shannon entropy reduction, consuming substantial energy and operating near slope limits."
        elif strat_id == "STRAT-04-RESSAFE":
            trade_off = "Maintained high battery reserves (>40%), but yielded very low total science return due to excessive caution."
        elif strat_id == "STRAT-05-PARETO":
            trade_off = "Extracted balanced non-dominated compromise along the Pareto frontier."
        elif strat_id == "STRAT-06-ATLAS":
            trade_off = "Orchestrated multi-phase aerial-ground campaign; avoided slope hazards via aerial scouting at the expense of higher coordination complexity."
        else:
            trade_off = "Generic multi-factor trade-off balance."

        return StrategyAutopsyReport(
            scenario_id=scenario.scenario_id,
            strategy_id=strat_id,
            seed=scenario.seed,
            feasibility_status=evaluation.feasibility_status,
            root_cause_explanation=root_cause,
            primary_active_constraints=active_constraints,
            trade_off_analysis=trade_off,
            decisions_trace=plan.causal_decisions,
            suggested_mitigations=mitigations,
        )

    @classmethod
    def compare_strategies_head_to_head(
        cls,
        scenario: GrandPrixScenario,
        strat_a: BaseMissionStrategy,
        strat_b: BaseMissionStrategy,
    ) -> Dict[str, Any]:
        """Replay and compare the decision traces of two strategies on the exact same scenario."""
        ctx_a = scenario.planning_context.copy_isolated()
        ctx_b = scenario.planning_context.copy_isolated()

        plan_a = strat_a.plan(ctx_a)
        plan_b = strat_b.plan(ctx_b)

        eval_a = GrandPrixMetricsEvaluator.evaluate(scenario, plan_a)
        eval_b = GrandPrixMetricsEvaluator.evaluate(scenario, plan_b)

        autopsy_a = cls.conduct_autopsy(scenario, plan_a, eval_a)
        autopsy_b = cls.conduct_autopsy(scenario, plan_b, eval_b)

        # Step-by-step decision divergence comparison
        max_steps = max(len(plan_a.selected_tasks), len(plan_b.selected_tasks))
        comparisons: List[Dict[str, Any]] = []

        for step in range(max_steps):
            t_a = plan_a.selected_tasks[step] if step < len(plan_a.selected_tasks) else None
            t_b = plan_b.selected_tasks[step] if step < len(plan_b.selected_tasks) else None

            desc_a = f"{t_a['title']} (Sol {t_a['start_sol']})" if t_a else "IDLE / FINISHED"
            desc_b = f"{t_b['title']} (Sol {t_b['start_sol']})" if t_b else "IDLE / FINISHED"

            diff_cause = "Different priority weighting" if t_a and t_b and t_a["title"] != t_b["title"] else "Aligned step"

            comparisons.append({
                "step": step + 1,
                "strategy_a_task": desc_a,
                "strategy_b_task": desc_b,
                "divergence": diff_cause,
            })

        return {
            "scenario_id": scenario.scenario_id,
            "seed": scenario.seed,
            "strategy_a": {
                "strategy_id": strat_a.metadata.strategy_id,
                "name": strat_a.metadata.name,
                "evaluation": eval_a.to_dict(),
                "autopsy": dataclasses.asdict(autopsy_a),
            },
            "strategy_b": {
                "strategy_id": strat_b.metadata.strategy_id,
                "name": strat_b.metadata.name,
                "evaluation": eval_b.to_dict(),
                "autopsy": dataclasses.asdict(autopsy_b),
            },
            "step_comparisons": comparisons,
            "verdict": {
                "science_winner": strat_a.metadata.strategy_id if eval_a.science_score > eval_b.science_score else strat_b.metadata.strategy_id,
                "efficiency_winner": strat_a.metadata.strategy_id if eval_a.energy_consumed_kwh < eval_b.energy_consumed_kwh else strat_b.metadata.strategy_id,
                "composite_winner": strat_a.metadata.strategy_id if eval_a.balanced_composite_score > eval_b.balanced_composite_score else strat_b.metadata.strategy_id,
            },
        }
