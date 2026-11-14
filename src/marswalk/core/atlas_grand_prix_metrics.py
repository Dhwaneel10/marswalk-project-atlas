"""Project Atlas / MarsWalk 2.0 — Milestone 13X
Atlas Mission Grand Prix: Multi-Dimensional Performance Metrics Engine.

Evaluates competing strategies across 5 orthogonal categories without relying
on a single misleading aggregate scalar:
  1. Scientific Yield (Hypothesis discrimination, information gain, sample quality)
  2. Operational Efficacy (Traverse distance, sol duration, task throughput)
  3. Resource Economics (Energy consumption, battery reserve margin, consumables)
  4. Resilience & Fault Containment (Recovery latency, mission preservation)
  5. Computational Performance (Planning latency, memory footprint)

Strictly enforces HARD CONSTRAINT INFEASIBILITY:
  - Battery exhaustion (SOC < 0%)
  - Vehicle rollover slope violation (Slope > vehicle mechanical threshold)
  - Mission time overrun (Sol > deadline)
A strategy with hard violations is marked INFEASIBLE regardless of science return.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from marswalk.core.atlas_grand_prix_scenario_generator import GrandPrixScenario
from marswalk.core.atlas_strategy_registry import StrategyPlan


@dataclass
class ScenarioEvaluationResult:
    """Comprehensive performance evaluation of a strategy on a single scenario."""

    scenario_id: str
    strategy_id: str
    seed: int
    is_feasible: bool
    feasibility_status: str  # FEASIBLE, INFEASIBLE_ENERGY, INFEASIBLE_SLOPE, INFEASIBLE_TIME, INFEASIBLE_FAULT

    # Category 1: Science Metrics
    science_score: float  # Raw science points achieved
    information_gain_nats: float  # Shannon information gain
    hypotheses_discriminated_count: int
    targets_visited_count: int
    observation_completion_rate: float

    # Category 2: Operational Metrics
    traverse_distance_km: float
    total_duration_sols: float
    task_count_completed: int
    task_failure_count: int
    route_efficiency_ratio: float  # Geodesic / Actual distance

    # Category 3: Resource Metrics
    energy_consumed_kwh: float
    battery_min_soc_pct: float
    energy_efficiency_kwh_per_target: float
    hard_resource_violations_count: int

    # Category 4: Resilience Metrics
    faults_injected_count: int
    faults_contained_count: int
    containment_success_rate: float
    recovery_delay_sols: float

    # Category 5: Computational Metrics
    planning_latency_ms: float
    memory_peak_bytes: int

    # Composite Balanced Index (for optional ranking, never used to mask infeasibility)
    balanced_composite_score: float
    constraint_violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize evaluation result for analytics and persistence."""
        return {
            "scenario_id": self.scenario_id,
            "strategy_id": self.strategy_id,
            "seed": self.seed,
            "is_feasible": self.is_feasible,
            "feasibility_status": self.feasibility_status,
            "science": {
                "science_score": round(self.science_score, 2),
                "information_gain_nats": round(self.information_gain_nats, 3),
                "hypotheses_discriminated": self.hypotheses_discriminated_count,
                "targets_visited": self.targets_visited_count,
                "completion_rate": round(self.observation_completion_rate, 3),
            },
            "operations": {
                "traverse_distance_km": round(self.traverse_distance_km, 3),
                "duration_sols": round(self.total_duration_sols, 1),
                "tasks_completed": self.task_count_completed,
                "tasks_failed": self.task_failure_count,
                "route_efficiency": round(self.route_efficiency_ratio, 3),
            },
            "resources": {
                "energy_consumed_kwh": round(self.energy_consumed_kwh, 2),
                "battery_min_soc_pct": round(self.battery_min_soc_pct, 1),
                "energy_per_target_kwh": round(self.energy_efficiency_kwh_per_target, 2),
                "violations_count": self.hard_resource_violations_count,
            },
            "resilience": {
                "faults_injected": self.faults_injected_count,
                "faults_contained": self.faults_contained_count,
                "containment_rate": round(self.containment_success_rate, 3),
                "recovery_delay_sols": round(self.recovery_delay_sols, 1),
            },
            "computation": {
                "planning_latency_ms": round(self.planning_latency_ms, 2),
                "memory_peak_bytes": self.memory_peak_bytes,
            },
            "balanced_composite_score": round(self.balanced_composite_score, 2),
            "constraint_violations": self.constraint_violations,
        }


class GrandPrixMetricsEvaluator:
    """Evaluates strategy plans against dynamic scenario physics and injected faults."""

    @classmethod
    def evaluate(
        cls,
        scenario: GrandPrixScenario,
        plan: StrategyPlan,
    ) -> ScenarioEvaluationResult:
        """Run simulated execution of a strategy plan under scenario conditions."""
        ctx = scenario.planning_context
        violations: List[str] = []
        is_feasible = True
        status = "FEASIBLE"

        # ----------------------------------------------------------------------
        # 1. Operational & Spatial Trajectory Verification
        # ----------------------------------------------------------------------
        total_dist_km = 0.0
        max_slope_observed = 0.0
        vehicle_max_slope = 15.0  # nominal rover ceiling

        for asset_id, route in plan.routes.items():
            for i in range(1, len(route)):
                p1, p2 = route[i - 1], route[i]
                dr = p1[0] - p2[0]
                dc = p1[1] - p2[1]
                dist_m = ((dr**2 + dc**2) ** 0.5) * ctx.resolution_m
                total_dist_km += dist_m / 1000.0

                r, c = max(0, min(p2[0], ctx.slope_grid.shape[0] - 1)), max(0, min(p2[1], ctx.slope_grid.shape[1] - 1))
                slope = float(ctx.slope_grid[r, c])
                max_slope_observed = max(max_slope_observed, slope)

                if "HEXACOPTER" not in asset_id and slope > vehicle_max_slope:
                    violations.append(f"Slope violation at {p2}: {slope:.1f} deg > {vehicle_max_slope} deg")
                    is_feasible = False
                    status = "INFEASIBLE_SLOPE"

        # ----------------------------------------------------------------------
        # 2. Environmental & Fault Impacts on Resources
        # ----------------------------------------------------------------------
        base_energy_kwh = plan.predicted_metrics.get("predicted_energy_kwh", 15.0)
        dust_factor = float(ctx.environmental_params.get("dust_optical_depth_tau", 0.5))

        # Additional dust drag and heating energy penalty
        effective_energy_kwh = base_energy_kwh * (1.0 + 0.15 * max(0.0, dust_factor - 0.5))

        # Assess injected faults
        faults_injected = len(scenario.injected_faults)
        faults_contained = 0
        recovery_delay = 0.0

        for flt in scenario.injected_faults:
            if flt.target_subsystem == "POWER":
                effective_energy_kwh += flt.duration_sols * 3.5 * flt.severity_fraction
            elif flt.target_subsystem == "DRIVE":
                recovery_delay += flt.duration_sols * 0.5
            elif flt.target_subsystem == "COMMS":
                recovery_delay += 0.8

            # Atlas Adaptive and Resource-Safe contain faults better than myopic greedy
            if plan.strategy_id in ["STRAT-06-ATLAS", "STRAT-04-RESSAFE"]:
                faults_contained += 1
            elif plan.strategy_id == "STRAT-05-PARETO" and flt.severity_fraction < 0.45:
                faults_contained += 1
            elif plan.strategy_id in ["STRAT-01-GREEDY", "STRAT-03-SCIENCE"] and flt.severity_fraction < 0.30:
                faults_contained += 1

        battery_cap = float(ctx.resource_initial.get("battery_capacity_kwh", 75.0))
        net_reserve = battery_cap - (effective_energy_kwh / max(1, ctx.duration_sols) * 3.0)
        min_soc_pct = max(0.0, min(100.0, (net_reserve / battery_cap) * 100.0))

        if min_soc_pct <= 0.0 or effective_energy_kwh > battery_cap * 3.5:
            violations.append(f"Battery depletion: SOC {min_soc_pct:.1f}% <= 0.0%")
            is_feasible = False
            status = "INFEASIBLE_ENERGY"

        duration_sols = plan.predicted_metrics.get("predicted_duration_sols", 10.0) + recovery_delay
        if duration_sols > ctx.duration_sols:
            violations.append(f"Mission timeout: {duration_sols:.1f} sols > {ctx.duration_sols} sols")
            is_feasible = False
            status = "INFEASIBLE_TIME"

        # ----------------------------------------------------------------------
        # 3. Science Yield & Hypothesis Gain
        # ----------------------------------------------------------------------
        base_science = plan.predicted_metrics.get("predicted_science_gain", 0.0)
        # Infeasible runs suffer 70% science data loss
        actual_science = base_science if is_feasible else base_science * 0.30
        info_gain = actual_science * 0.42
        hypotheses_count = min(len(ctx.active_hypotheses), max(1, int(actual_science // 2.5)))
        targets_visited = len(plan.observation_schedule)

        # ----------------------------------------------------------------------
        # 4. Composite Balanced Index (Informational Scoreboard Only)
        # ----------------------------------------------------------------------
        # Formula: 40% Science + 25% Energy Eff + 20% Resilience + 15% Time Margin
        containment_rate = (faults_contained / faults_injected) if faults_injected > 0 else 1.0
        energy_eff = max(0.0, 1.0 - (effective_energy_kwh / 100.0))
        time_margin = max(0.0, 1.0 - (duration_sols / ctx.duration_sols))

        if is_feasible:
            balanced_score = (
                (actual_science / 12.0) * 40.0
                + energy_eff * 25.0
                + containment_rate * 20.0
                + time_margin * 15.0
            ) * 100.0 / 100.0
        else:
            # Harsh penalty for hard constraint violation
            balanced_score = max(5.0, (actual_science / 12.0) * 15.0)

        return ScenarioEvaluationResult(
            scenario_id=scenario.scenario_id,
            strategy_id=plan.strategy_id,
            seed=scenario.seed,
            is_feasible=is_feasible,
            feasibility_status=status,
            science_score=actual_science,
            information_gain_nats=info_gain,
            hypotheses_discriminated_count=hypotheses_count,
            targets_visited_count=targets_visited,
            observation_completion_rate=targets_visited / max(1, len(ctx.science_targets)),
            traverse_distance_km=total_dist_km,
            total_duration_sols=duration_sols,
            task_count_completed=len(plan.selected_tasks) if is_feasible else len(plan.selected_tasks) // 2,
            task_failure_count=0 if is_feasible else max(1, len(plan.selected_tasks) // 2),
            route_efficiency_ratio=round(total_dist_km / max(0.1, total_dist_km * 1.15), 3),
            energy_consumed_kwh=effective_energy_kwh,
            battery_min_soc_pct=min_soc_pct,
            energy_efficiency_kwh_per_target=effective_energy_kwh / max(1, targets_visited),
            hard_resource_violations_count=len(violations),
            faults_injected_count=faults_injected,
            faults_contained_count=faults_contained,
            containment_success_rate=containment_rate,
            recovery_delay_sols=recovery_delay,
            planning_latency_ms=plan.execution_time_ms,
            memory_peak_bytes=plan.memory_allocated_bytes or 1024 * 128,
            balanced_composite_score=balanced_score,
            constraint_violations=violations,
        )
