"""Project Atlas / MarsWalk 2.0 — Milestone 13X
Atlas Mission Grand Prix: Central Tournament Coordinator.

Executes the formal 8-Round Planetary Mission Planning Championship:
  Round 1: Nominal Martian Operations (Gentle plains, clear skies, nominal comms)
  Round 2: Resource Pressure (Strict energy budget, degraded batteries, tight time limits)
  Round 3: Scientific Uncertainty (High-entropy competing geological hypotheses)
  Round 4: Deep Space Communications (20 min OWLT, blackout conjunctions, packet drops)
  Round 5: Multi-Robot Cooperation (Heterogeneous rovers, hexacopter aerial scouts, builders)
  Round 6: Failure Arena (Cascading component failures & severe environmental hazards)
  Round 7: Long-Duration Settlement Operations (60-Sol campaigns, Kilopower, and regolith sintering)
  Round 8: Held-Out Apocalypse (Unseen combinations of extreme terrain, storms, and compound faults)

Tracks round-by-round rankings, exposes Pareto trade-offs, and crowns winners
by specialized category (Science Champion, Efficiency Champion, Robustness Champion,
and Overall Grand Prix Champion).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import numpy as np

from marswalk.core.atlas_grand_prix_experiment import GrandPrixExperimentEngine
from marswalk.core.atlas_grand_prix_metrics import (
    GrandPrixMetricsEvaluator,
    ScenarioEvaluationResult,
)
from marswalk.core.atlas_grand_prix_scenario_generator import (
    GrandPrixScenario,
    GrandPrixScenarioGenerator,
    ScenarioPartition,
)
from marswalk.core.atlas_grand_prix_statistics import GrandPrixStatistics
from marswalk.core.atlas_strategy_registry import (
    BaseMissionStrategy,
    StrategyRegistry,
)


@dataclass
class TournamentRoundSpec:
    """Configuration specification for a specific Grand Prix round."""
    round_number: int
    name: str
    description: str
    scenario_partition: ScenarioPartition
    start_seed: int
    scenario_count: int
    custom_duration_sols: Optional[int] = None
    force_synthetic: bool = False


TOURNAMENT_ROUNDS = [
    TournamentRoundSpec(
        round_number=1,
        name="Nominal Martian Operations",
        description="Baseline Jezero exploration under standard conditions, mild terrain, and nominal telemetry.",
        scenario_partition=ScenarioPartition.DEVELOPMENT,
        start_seed=1100,
        scenario_count=20,
        custom_duration_sols=30,
    ),
    TournamentRoundSpec(
        round_number=2,
        name="Resource Pressure",
        description="Restricted energy budgets (<50 kWh), high solar dust attenuation, and constrained mission clocks.",
        scenario_partition=ScenarioPartition.DEVELOPMENT,
        start_seed=1120,
        scenario_count=20,
        custom_duration_sols=15,
    ),
    TournamentRoundSpec(
        round_number=3,
        name="Scientific Uncertainty",
        description="High-entropy competing geological hypotheses requiring aggressive active learning.",
        scenario_partition=ScenarioPartition.DEVELOPMENT,
        start_seed=1140,
        scenario_count=20,
        custom_duration_sols=30,
    ),
    TournamentRoundSpec(
        round_number=4,
        name="Deep Space Communications",
        description="Long One-Way Light Time (>18 min OWLT), intermittent relay passes, and delayed acknowledgments.",
        scenario_partition=ScenarioPartition.TUNING,
        start_seed=2100,
        scenario_count=20,
        custom_duration_sols=30,
    ),
    TournamentRoundSpec(
        round_number=5,
        name="Multi-Robot Cooperation",
        description="Coordinated sorties requiring concurrent aerial rotorcraft scouting and ground rover drives.",
        scenario_partition=ScenarioPartition.TUNING,
        start_seed=2120,
        scenario_count=20,
        custom_duration_sols=30,
    ),
    TournamentRoundSpec(
        round_number=6,
        name="Failure Arena",
        description="Cascading component failures: drive motor drag, spectrometer calibration drift, and dust events.",
        scenario_partition=ScenarioPartition.TUNING,
        start_seed=2140,
        scenario_count=20,
        custom_duration_sols=45,
    ),
    TournamentRoundSpec(
        round_number=7,
        name="Long-Duration Settlement",
        description="60-Sol extended campaign balancing Kilopower reactors, regolith sintering, and long-range traversal.",
        scenario_partition=ScenarioPartition.TUNING,
        start_seed=2160,
        scenario_count=20,
        custom_duration_sols=60,
    ),
    TournamentRoundSpec(
        round_number=8,
        name="Held-Out Apocalypse",
        description="Unseen combinations of extreme scarp slopes (>25 deg), regional dust storms, and compound outages.",
        scenario_partition=ScenarioPartition.HELD_OUT,
        start_seed=5100,
        scenario_count=30,
        custom_duration_sols=60,
        force_synthetic=True,
    ),
]


class AtlasMissionGrandPrixTournament:
    """Coordinates and executes the official 8-round Grand Prix competition."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.experiment_engine = GrandPrixExperimentEngine(output_dir=output_dir)
        self.strategies = StrategyRegistry.create_all_competitors()

    def run_tournament(
        self,
        tournament_id: str = "ATLAS-GRAND-PRIX-2026-CHAMPIONSHIP",
        selected_rounds: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Execute the full 8-round championship tournament."""
        t_start = time.perf_counter()
        rounds_to_run = [r for r in TOURNAMENT_ROUNDS if selected_rounds is None or r.round_number in selected_rounds]

        round_results = []
        cumulative_evaluations: List[ScenarioEvaluationResult] = []

        for r_spec in rounds_to_run:
            round_t0 = time.perf_counter()
            round_evals: List[ScenarioEvaluationResult] = []

            for i in range(r_spec.scenario_count):
                seed = r_spec.start_seed + i
                scenario = GrandPrixScenarioGenerator.generate_scenario(
                    seed=seed,
                    partition=r_spec.scenario_partition,
                    custom_duration_sols=r_spec.custom_duration_sols,
                    force_synthetic_terrain=r_spec.force_synthetic,
                )

                for s_id, strategy in self.strategies.items():
                    ctx_isolated = scenario.planning_context.copy_isolated()
                    plan = strategy.plan(ctx_isolated)
                    eval_res = GrandPrixMetricsEvaluator.evaluate(scenario, plan)
                    round_evals.append(eval_res)
                    cumulative_evaluations.append(eval_res)

            round_elapsed = time.perf_counter() - round_t0

            # Round summary rankings
            round_summary = {
                "round_number": r_spec.round_number,
                "name": r_spec.name,
                "description": r_spec.description,
                "scenarios_evaluated": r_spec.scenario_count,
                "simulations_count": len(round_evals),
                "round_wall_clock_sec": round(round_elapsed, 2),
                "strategy_scores": {},
            }

            for s_id in self.strategies:
                strat_res = [e for e in round_evals if e.strategy_id == s_id]
                stat = GrandPrixStatistics.aggregate_strategy_benchmark(strat_res)
                round_summary["strategy_scores"][s_id] = {
                    "science_mean": stat["science"]["mean"],
                    "energy_mean": stat["energy_kwh"]["mean"],
                    "feasibility_rate_pct": stat["feasibility_rate_pct"],
                    "composite_mean": stat["composite_score"]["mean"],
                    "composite_cvar05": stat["composite_score"]["cvar_05"],
                }

            round_results.append(round_summary)

        total_wall_clock = time.perf_counter() - t_start

        # Cumulative tournament statistics across all rounds
        overall_summaries = {}
        for s_id in self.strategies:
            strat_cum = [e for e in cumulative_evaluations if e.strategy_id == s_id]
            overall_summaries[s_id] = GrandPrixStatistics.aggregate_strategy_benchmark(strat_cum)

        # Crown Champions across specific operational criteria
        science_champion = max(overall_summaries.keys(), key=lambda s: overall_summaries[s]["science"]["mean"])
        efficiency_champion = min(overall_summaries.keys(), key=lambda s: overall_summaries[s]["energy_kwh"]["mean"])
        robustness_champion = max(overall_summaries.keys(), key=lambda s: (overall_summaries[s]["feasibility_rate_pct"], overall_summaries[s]["composite_score"]["cvar_05"]))
        overall_champion = max(overall_summaries.keys(), key=lambda s: (overall_summaries[s]["feasibility_rate_pct"], overall_summaries[s]["composite_score"]["mean"]))

        tournament_dossier = {
            "tournament_id": tournament_id,
            "rounds_executed_count": len(round_results),
            "total_simulations_executed": len(cumulative_evaluations),
            "total_wall_clock_seconds": round(total_wall_clock, 2),
            "round_reports": round_results,
            "overall_strategy_standings": overall_summaries,
            "champions": {
                "science_champion": {
                    "strategy_id": science_champion,
                    "title": "Highest Raw Scientific Return",
                    "score": overall_summaries[science_champion]["science"]["mean"],
                },
                "efficiency_champion": {
                    "strategy_id": efficiency_champion,
                    "title": "Lowest Energy & Distance Footprint",
                    "score_kwh": overall_summaries[efficiency_champion]["energy_kwh"]["mean"],
                },
                "robustness_champion": {
                    "strategy_id": robustness_champion,
                    "title": "Highest Worst-Case Reliability (CVaR & Feasibility)",
                    "feasibility_pct": overall_summaries[robustness_champion]["feasibility_rate_pct"],
                    "cvar05": overall_summaries[robustness_champion]["composite_score"]["cvar_05"],
                },
                "overall_grand_prix_champion": {
                    "strategy_id": overall_champion,
                    "title": "Overall Balanced Tournament Champion",
                    "feasibility_pct": overall_summaries[overall_champion]["feasibility_rate_pct"],
                    "composite_mean": overall_summaries[overall_champion]["composite_score"]["mean"],
                },
            },
        }

        # Persist full tournament results
        out_p = self.experiment_engine.output_dir / f"tournament_dossier_{tournament_id}.json"
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump({
                "tournament_summary": tournament_dossier,
                "evaluations_sample": [e.to_dict() for e in cumulative_evaluations[:100]],
            }, f, indent=2)

        return tournament_dossier
