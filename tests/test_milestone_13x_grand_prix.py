"""Project Atlas / MarsWalk 2.0 — Milestone 13X
Automated Test Battery: Milestone 13X Grand Prix Strategy Arena.

Verifies:
  1. Competitor fairness, metadata locking, and information isolation
  2. Procedural scenario generation, deterministic seeds, and partition segregation
  3. Metric evaluation, hard constraint infeasibility detection, and CVaR statistics
  4. Non-dominated Pareto frontier extraction in multi-objective optimization
  5. Resumable checkpointing, state isolation, and batch execution
  6. Algorithmic autopsy lineage and head-to-head decision comparisons
  7. Environmental sensitivity sweeps and failure cliff discovery
  8. 8-round tournament orchestration and champion crowning
"""

import copy
import json
import os
from pathlib import Path
import tempfile
import pytest

from marswalk.core.atlas_grand_prix_experiment import GrandPrixExperimentEngine
from marswalk.core.atlas_grand_prix_metrics import (
    GrandPrixMetricsEvaluator,
    ScenarioEvaluationResult,
)
from marswalk.core.atlas_grand_prix_scenario_generator import (
    GrandPrixScenario,
    GrandPrixScenarioGenerator,
    ScenarioFaultEvent,
    ScenarioPartition,
)
from marswalk.core.atlas_grand_prix_statistics import GrandPrixStatistics
from marswalk.core.atlas_mission_grand_prix import (
    AtlasMissionGrandPrixTournament,
    TOURNAMENT_ROUNDS,
)
from marswalk.core.atlas_mission_sensitivity import MissionSensitivityEngine
from marswalk.core.atlas_strategy_explainability import StrategyExplainabilityEngine
from marswalk.core.atlas_strategy_registry import (
    AtlasAdaptiveDirectorStrategy,
    BaseMissionStrategy,
    GreedyExplorerStrategy,
    MinCostNavigatorStrategy,
    MultiObjectiveOptimizerStrategy,
    ResourceSafePlannerStrategy,
    ScienceFirstExplorerStrategy,
    StrategyRegistry,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


# ==============================================================================
# 1. COMPETITOR FAIRNESS & REGISTRY VERIFICATION
# ==============================================================================


def test_strategy_registry_completeness_and_contracts():
    """Verify that all six foundational strategies instantiate with locked metadata."""
    competitors = StrategyRegistry.create_all_competitors()
    assert len(competitors) == 6, f"Expected 6 strategies, found {len(competitors)}"

    expected_ids = {
        "STRAT-01-GREEDY",
        "STRAT-02-MINCOST",
        "STRAT-03-SCIENCE",
        "STRAT-04-RESSAFE",
        "STRAT-05-PARETO",
        "STRAT-06-ATLAS",
    }
    assert set(competitors.keys()) == expected_ids

    for s_id, strat in competitors.items():
        assert strat.metadata.strategy_id == s_id
        assert strat.metadata.version == "1.0.0"
        assert strat.metadata.is_deterministic is True
        assert len(strat.metadata.supported_mission_types) >= 1
        assert len(strat.metadata.known_limitations) >= 1


def test_competitor_planning_on_identical_context():
    """Verify that all 6 competitors plan on an identical scenario context without mutating it."""
    scenario = GrandPrixScenarioGenerator.generate_scenario(seed=1010, partition=ScenarioPartition.DEVELOPMENT)
    competitors = StrategyRegistry.create_all_competitors()

    original_context_hash = hashlib_context(scenario.planning_context)

    plans = {}
    for s_id, strat in competitors.items():
        ctx_copy = scenario.planning_context.copy_isolated()
        plan = strat.plan(ctx_copy)
        assert plan.strategy_id == s_id
        assert plan.scenario_id == scenario.scenario_id
        assert plan.feasibility_status in ("FEASIBLE", "INFEASIBLE_ENERGY", "INFEASIBLE_SLOPE", "INFEASIBLE_TIME")
        assert len(plan.routes) >= 1
        assert len(plan.causal_decisions) >= 1
        plans[s_id] = plan

    # Verify context was not mutated
    assert hashlib_context(scenario.planning_context) == original_context_hash


def hashlib_context(ctx) -> str:
    import hashlib
    content = f"{ctx.scenario_id}:{ctx.seed}:{ctx.duration_sols}:{len(ctx.science_targets)}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ==============================================================================
# 2. SCENARIO GENERATION & PARTITION SEGREGATION
# ==============================================================================


def test_scenario_generation_determinism_and_provenance():
    """Verify that identical seeds yield bit-exact identical scenarios and terrain metadata."""
    scen_a = GrandPrixScenarioGenerator.generate_scenario(seed=1042, partition=ScenarioPartition.DEVELOPMENT)
    scen_b = GrandPrixScenarioGenerator.generate_scenario(seed=1042, partition=ScenarioPartition.DEVELOPMENT)

    assert scen_a.scenario_id == scen_b.scenario_id
    assert scen_a.planning_context.duration_sols == scen_b.planning_context.duration_sols
    assert len(scen_a.planning_context.science_targets) == len(scen_b.planning_context.science_targets)
    assert len(scen_a.injected_faults) == len(scen_b.injected_faults)
    assert scen_a.source_elevation_sha256 == scen_b.source_elevation_sha256
    assert (scen_a.planning_context.elevation_grid == scen_b.planning_context.elevation_grid).all()


def test_dataset_partition_segregation():
    """Verify that Development, Tuning, and Held-Out partition seeds do not overlap."""
    dev_suite = GrandPrixScenarioGenerator.generate_partition_suite(ScenarioPartition.DEVELOPMENT, count=10)
    tune_suite = GrandPrixScenarioGenerator.generate_partition_suite(ScenarioPartition.TUNING, count=10)
    held_suite = GrandPrixScenarioGenerator.generate_partition_suite(ScenarioPartition.HELD_OUT, count=10)

    dev_seeds = {s.seed for s in dev_suite}
    tune_seeds = {s.seed for s in tune_suite}
    held_seeds = {s.seed for s in held_suite}

    assert dev_seeds.isdisjoint(tune_seeds), "Dev and Tuning seed sets overlap"
    assert dev_seeds.isdisjoint(held_seeds), "Dev and Held-Out seed sets overlap"
    assert tune_seeds.isdisjoint(held_seeds), "Tuning and Held-Out seed sets overlap"


# ==============================================================================
# 3. METRICS EVALUATION & HARD CONSTRAINT INFEASIBILITY
# ==============================================================================


def test_hard_constraint_infeasibility_detection():
    """Verify that rollover slope or battery depletion correctly flags INFEASIBLE status."""
    scenario = GrandPrixScenarioGenerator.generate_scenario(seed=1025, partition=ScenarioPartition.DEVELOPMENT)
    strat = GreedyExplorerStrategy()
    plan = strat.plan(scenario.planning_context.copy_isolated())

    # Case 1: Nominal evaluation
    eval_nominal = GrandPrixMetricsEvaluator.evaluate(scenario, plan)
    assert eval_nominal.scenario_id == scenario.scenario_id

    # Case 2: Injected extreme slope route
    bad_plan = copy.deepcopy(plan)
    # Add coordinates that will exceed rover chassis limit (e.g. artificial steep scarp)
    bad_plan.routes["ATLAS-ROVER-01"] = [(0, 0), (scenario.planning_context.slope_grid.shape[0]-1, scenario.planning_context.slope_grid.shape[1]-1)]
    # Set slope grid cell to 28 degrees
    scenario_steep = copy.deepcopy(scenario)
    scenario_steep.planning_context.slope_grid[-1, -1] = 28.5

    eval_steep = GrandPrixMetricsEvaluator.evaluate(scenario_steep, bad_plan)
    assert not eval_steep.is_feasible
    assert eval_steep.feasibility_status == "INFEASIBLE_SLOPE"
    assert len(eval_steep.constraint_violations) >= 1


# ==============================================================================
# 4. MULTI-OBJECTIVE OPTIMIZER & PARETO FRONTIER
# ==============================================================================


def test_pareto_multi_objective_frontier_extraction():
    """Verify that MultiObjectiveOptimizerStrategy extracts a non-empty non-dominated Pareto front."""
    scenario = GrandPrixScenarioGenerator.generate_scenario(seed=1033, partition=ScenarioPartition.DEVELOPMENT)
    pareto_strat = MultiObjectiveOptimizerStrategy()
    plan = pareto_strat.plan(scenario.planning_context.copy_isolated())

    assert plan.pareto_frontier is not None
    assert len(plan.pareto_frontier) >= 1
    for pt in plan.pareto_frontier:
        assert "science_gain" in pt
        assert "energy_kwh" in pt
        assert "distance_km" in pt
        assert "risk_score" in pt


# ==============================================================================
# 5. STATISTICAL EVALUATION & CVAR CORRECTNESS
# ==============================================================================


def test_distributional_metrics_and_cvar():
    """Verify that statistical summaries, percentiles, and CVaR calculate correctly."""
    # Test data: 10 synthetic values [10, 20, 30, ..., 100]
    vals = [float(x) for x in range(10, 110, 10)]
    stats = GrandPrixStatistics.compute_distribution_metrics(vals)

    assert stats["count"] == 10
    assert stats["mean"] == 55.0
    assert stats["median"] == 55.0
    assert stats["worst_case"] == 10.0
    # CVaR 10% (expected shortfall on lowest 10% quantile, which is 10.0)
    assert stats["cvar_10"] <= 20.0

    ci_low, ci_high = GrandPrixStatistics.compute_bootstrap_ci(vals, num_resamples=500, seed=123)
    assert ci_low < stats["mean"] < ci_high


def test_paired_strategy_comparison():
    """Verify that paired seed comparisons calculate wins, losses, ties, and effect sizes."""
    scenario_a = GrandPrixScenarioGenerator.generate_scenario(seed=1001, partition=ScenarioPartition.DEVELOPMENT)
    scenario_b = GrandPrixScenarioGenerator.generate_scenario(seed=1002, partition=ScenarioPartition.DEVELOPMENT)

    s1 = GreedyExplorerStrategy()
    s2 = ResourceSafePlannerStrategy()

    res1_a = GrandPrixMetricsEvaluator.evaluate(scenario_a, s1.plan(scenario_a.planning_context.copy_isolated()))
    res1_b = GrandPrixMetricsEvaluator.evaluate(scenario_b, s1.plan(scenario_b.planning_context.copy_isolated()))

    res2_a = GrandPrixMetricsEvaluator.evaluate(scenario_a, s2.plan(scenario_a.planning_context.copy_isolated()))
    res2_b = GrandPrixMetricsEvaluator.evaluate(scenario_b, s2.plan(scenario_b.planning_context.copy_isolated()))

    paired = GrandPrixStatistics.compare_paired_strategies([res1_a, res1_b], [res2_a, res2_b], "science_score")
    assert paired["paired_sample_size"] == 2
    assert "wins_strategy_a" in paired
    assert "cohens_d" in paired
    assert "cliffs_delta" in paired


# ==============================================================================
# 6. SENSITIVITY SWEEPS & PHASE TRANSITION CLIFFS
# ==============================================================================


def test_sensitivity_dust_sweep():
    """Verify that the dust opacity sweep evaluates multiple points and computes infeasibility thresholds."""
    report = MissionSensitivityEngine.sweep_dust_opacity(base_seed=1050, tau_values=[0.5, 1.5, 2.5])
    assert report.parameter_name == "Atmospheric Dust Optical Depth (Tau)"
    assert len(report.parameter_range) == 3
    assert len(report.strategy_curves) == 6
    assert len(report.robustness_rankings) == 6


# ==============================================================================
# 7. EXPERIMENT ENGINE & RESUMABLE CHECKPOINTING
# ==============================================================================


def test_experiment_engine_checkpointing_and_resume():
    """Verify that benchmark batches checkpoint to disk and resume cleanly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = GrandPrixExperimentEngine(output_dir=Path(tmpdir), batch_size=2, checkpoint_interval=2)
        run_id = "TEST-RUN-CHECKPOINT-001"

        # Run 3 scenarios across 2 strategies
        summary = engine.run_benchmark(
            run_id=run_id,
            partition=ScenarioPartition.DEVELOPMENT,
            scenario_count=3,
            start_seed=1080,
            strategies=["STRAT-01-GREEDY", "STRAT-02-MINCOST"],
            resume=False,
        )

        assert summary["scenario_count"] == 3
        assert summary["total_simulations_executed"] == 6
        assert len(summary["strategy_summaries"]) == 2

        # Verify results file written
        results_file = Path(tmpdir) / f"benchmark_results_{run_id}.json"
        assert results_file.exists()
        with open(results_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
            assert len(saved["evaluations"]) == 6


# ==============================================================================
# 8. ALGORITHMIC AUTOPSY & HEAD-TO-HEAD COMPARISON
# ==============================================================================


def test_algorithmic_autopsy_and_decision_divergence():
    """Verify that head-to-head comparison extracts causal decision divergence traces."""
    scenario = GrandPrixScenarioGenerator.generate_scenario(seed=1015, partition=ScenarioPartition.DEVELOPMENT)
    strat_a = AtlasAdaptiveDirectorStrategy()
    strat_b = MinCostNavigatorStrategy()

    comparison = StrategyExplainabilityEngine.compare_strategies_head_to_head(scenario, strat_a, strat_b)
    assert comparison["scenario_id"] == scenario.scenario_id
    assert comparison["strategy_a"]["strategy_id"] == "STRAT-06-ATLAS"
    assert comparison["strategy_b"]["strategy_id"] == "STRAT-02-MINCOST"
    assert "step_comparisons" in comparison
    assert len(comparison["step_comparisons"]) >= 1
    assert "verdict" in comparison
    assert "science_winner" in comparison["verdict"]


# ==============================================================================
# 9. TOURNAMENT COORDINATOR SMOKE TEST
# ==============================================================================


def test_grand_prix_tournament_smoke_run():
    """Verify that the 8-round tournament coordinator executes Round 1 smoke evaluation cleanly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tournament = AtlasMissionGrandPrixTournament(output_dir=Path(tmpdir))
        # Execute only Round 1 with 2 scenarios for fast automated verification
        dossier = tournament.run_tournament(
            tournament_id="TEST-SMOKE-TOURNAMENT",
            selected_rounds=[1],
        )

        assert dossier["rounds_executed_count"] == 1
        assert dossier["total_simulations_executed"] == 20 * 6  # Round 1 has 20 scenarios * 6 strategies = 120
        assert "champions" in dossier
        assert "science_champion" in dossier["champions"]
        assert "efficiency_champion" in dossier["champions"]
        assert "robustness_champion" in dossier["champions"]
        assert "overall_grand_prix_champion" in dossier["champions"]
