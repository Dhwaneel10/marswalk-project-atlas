"""Project Atlas / MarsWalk 2.0 — Milestone 13X
Atlas Mission Grand Prix: Benchmark Experiment Engine.

Orchestrates large-scale Monte Carlo experiments comparing all registered
planetary mission planning strategies under identical scenario configurations.

Features:
  - Multi-tier staged execution (100 functional, 1,000 development, up to 10,000 screening/stress)
  - Paired-seed evaluation across all 6 strategies
  - Memory-conscious batch processing & garbage collection
  - Resumable checkpointing: preserves progress and skips already completed runs
  - Isolated simulation state per run
  - Comprehensive persistence of results, logs, and failure autopsies
"""

from __future__ import annotations

import gc
import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

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


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "workspaces" / "grand_prix_runs"


class GrandPrixExperimentEngine:
    """Manages the execution, checkpointing, and reporting of large-scale strategy benchmarks."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        batch_size: int = 50,
        checkpoint_interval: int = 100,
    ):
        self.output_dir = Path(output_dir or DEFAULT_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.batch_size = batch_size
        self.checkpoint_interval = checkpoint_interval

    def _get_checkpoint_path(self, run_id: str) -> Path:
        return self.output_dir / f"checkpoint_{run_id}.json"

    def _get_results_path(self, run_id: str) -> Path:
        return self.output_dir / f"benchmark_results_{run_id}.json"

    def run_benchmark(
        self,
        run_id: str,
        partition: ScenarioPartition = ScenarioPartition.DEVELOPMENT,
        scenario_count: int = 100,
        start_seed: Optional[int] = None,
        strategies: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        resume: bool = True,
    ) -> Dict[str, Any]:
        """Execute a complete paired-seed benchmark tournament.

        Returns comprehensive evaluation results, statistical aggregations,
        and execution runtime metrics.
        """
        t0 = time.perf_counter()
        active_strategies: Dict[str, BaseMissionStrategy] = {}
        all_registered = StrategyRegistry.create_all_competitors()

        if strategies:
            for s_id in strategies:
                if s_id in all_registered:
                    active_strategies[s_id] = all_registered[s_id]
        else:
            active_strategies = all_registered

        # Check for existing checkpoint to resume
        ckpt_path = self._get_checkpoint_path(run_id)
        raw_evaluations: List[ScenarioEvaluationResult] = []
        completed_seeds: set = set()

        if resume and ckpt_path.exists():
            try:
                with open(ckpt_path, "r", encoding="utf-8") as f:
                    saved_data = json.load(f)
                    for item in saved_data.get("evaluations", []):
                        res = ScenarioEvaluationResult(
                            scenario_id=item["scenario_id"],
                            strategy_id=item["strategy_id"],
                            seed=item["seed"],
                            is_feasible=item["is_feasible"],
                            feasibility_status=item["feasibility_status"],
                            science_score=item["science"]["science_score"],
                            information_gain_nats=item["science"]["information_gain_nats"],
                            hypotheses_discriminated_count=item["science"]["hypotheses_discriminated"],
                            targets_visited_count=item["science"]["targets_visited"],
                            observation_completion_rate=item["science"]["completion_rate"],
                            traverse_distance_km=item["operations"]["traverse_distance_km"],
                            total_duration_sols=item["operations"]["duration_sols"],
                            task_count_completed=item["operations"]["tasks_completed"],
                            task_failure_count=item["operations"]["tasks_failed"],
                            route_efficiency_ratio=item["operations"]["route_efficiency"],
                            energy_consumed_kwh=item["resources"]["energy_consumed_kwh"],
                            battery_min_soc_pct=item["resources"]["battery_min_soc_pct"],
                            energy_efficiency_kwh_per_target=item["resources"]["energy_per_target_kwh"],
                            hard_resource_violations_count=item["resources"]["violations_count"],
                            faults_injected_count=item["resilience"]["faults_injected"],
                            faults_contained_count=item["resilience"]["faults_contained"],
                            containment_success_rate=item["resilience"]["containment_rate"],
                            recovery_delay_sols=item["resilience"]["recovery_delay_sols"],
                            planning_latency_ms=item["computation"]["planning_latency_ms"],
                            memory_peak_bytes=item["computation"]["memory_peak_bytes"],
                            balanced_composite_score=item["balanced_composite_score"],
                            constraint_violations=item.get("constraint_violations", []),
                        )
                        raw_evaluations.append(res)
                        completed_seeds.add((res.seed, res.strategy_id))
            except Exception:
                raw_evaluations.clear()
                completed_seeds.clear()

        # Generate scenario sequence
        if start_seed is None:
            if partition == ScenarioPartition.DEVELOPMENT:
                start_seed = 1000
            elif partition == ScenarioPartition.TUNING:
                start_seed = 2000
            else:
                start_seed = 5000

        total_simulations = scenario_count * len(active_strategies)
        sim_counter = len(raw_evaluations)

        for i in range(scenario_count):
            seed = start_seed + i
            scenario = GrandPrixScenarioGenerator.generate_scenario(seed=seed, partition=partition)

            for strat_id, strat_instance in active_strategies.items():
                if (seed, strat_id) in completed_seeds:
                    continue

                # Run strategy on isolated context
                ctx_isolated = scenario.planning_context.copy_isolated()
                try:
                    plan = strat_instance.plan(ctx_isolated)
                    eval_res = GrandPrixMetricsEvaluator.evaluate(scenario, plan)
                except Exception as exc:
                    # Capture unhandled planning crash as an infeasible run
                    eval_res = ScenarioEvaluationResult(
                        scenario_id=scenario.scenario_id,
                        strategy_id=strat_id,
                        seed=seed,
                        is_feasible=False,
                        feasibility_status="INFEASIBLE_EXCEPTION",
                        science_score=0.0,
                        information_gain_nats=0.0,
                        hypotheses_discriminated_count=0,
                        targets_visited_count=0,
                        observation_completion_rate=0.0,
                        traverse_distance_km=0.0,
                        total_duration_sols=float(scenario.planning_context.duration_sols),
                        task_count_completed=0,
                        task_failure_count=1,
                        route_efficiency_ratio=0.0,
                        energy_consumed_kwh=100.0,
                        battery_min_soc_pct=0.0,
                        energy_efficiency_kwh_per_target=0.0,
                        hard_resource_violations_count=1,
                        faults_injected_count=len(scenario.injected_faults),
                        faults_contained_count=0,
                        containment_success_rate=0.0,
                        recovery_delay_sols=0.0,
                        planning_latency_ms=0.0,
                        memory_peak_bytes=0,
                        balanced_composite_score=0.0,
                        constraint_violations=[f"Unhandled planning exception: {str(exc)}"],
                    )

                raw_evaluations.append(eval_res)
                completed_seeds.add((seed, strat_id))
                sim_counter += 1

                if progress_callback and sim_counter % 25 == 0:
                    progress_callback(sim_counter, total_simulations, f"Executed seed {seed} for {strat_id}")

            # Checkpoint periodically
            if (i + 1) % self.checkpoint_interval == 0:
                self._save_checkpoint(run_id, raw_evaluations)
                gc.collect()

        elapsed_sec = time.perf_counter() - t0

        # Aggregate statistical profiles per strategy
        strategy_summaries = {}
        for s_id in active_strategies:
            strat_results = [r for r in raw_evaluations if r.strategy_id == s_id]
            strategy_summaries[s_id] = GrandPrixStatistics.aggregate_strategy_benchmark(strat_results)

        # Pairwise head-to-head comparisons against Atlas
        pairwise_comparisons = {}
        atlas_results = [r for r in raw_evaluations if r.strategy_id == "STRAT-06-ATLAS"]
        if atlas_results:
            for s_id in active_strategies:
                if s_id != "STRAT-06-ATLAS":
                    comp_results = [r for r in raw_evaluations if r.strategy_id == s_id]
                    pairwise_comparisons[f"ATLAS_vs_{s_id}"] = {
                        "science": GrandPrixStatistics.compare_paired_strategies(atlas_results, comp_results, "science_score"),
                        "composite": GrandPrixStatistics.compare_paired_strategies(atlas_results, comp_results, "balanced_composite_score"),
                    }

        benchmark_report = {
            "run_id": run_id,
            "partition": partition.value,
            "scenario_count": scenario_count,
            "start_seed": start_seed,
            "strategies_evaluated": list(active_strategies.keys()),
            "total_simulations_executed": len(raw_evaluations),
            "wall_clock_seconds": round(elapsed_sec, 2),
            "simulations_per_second": round(len(raw_evaluations) / max(0.001, elapsed_sec), 1),
            "strategy_summaries": strategy_summaries,
            "pairwise_comparisons": pairwise_comparisons,
        }

        # Save final report and full evaluation records
        results_path = self._get_results_path(run_id)
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump({
                "summary": benchmark_report,
                "evaluations": [r.to_dict() for r in raw_evaluations],
            }, f, indent=2)

        # Remove temporary checkpoint on successful completion
        if ckpt_path.exists():
            try:
                ckpt_path.unlink()
            except Exception:
                pass

        return benchmark_report

    def _save_checkpoint(self, run_id: str, evaluations: List[ScenarioEvaluationResult]) -> None:
        """Save intermediate progress."""
        ckpt_path = self._get_checkpoint_path(run_id)
        with open(ckpt_path, "w", encoding="utf-8") as f:
            json.dump({
                "run_id": run_id,
                "saved_at": time.time(),
                "evaluations": [r.to_dict() for r in evaluations],
            }, f)
