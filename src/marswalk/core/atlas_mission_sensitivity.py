"""Project Atlas / MarsWalk 2.0 — Milestone 13X
Atlas Mission Grand Prix: Sensitivity Analysis & Design-Space Exploration Engine.

Conducts controlled parameter sweeps to discover operational cliffs and phase
transitions where strategies flip from feasible to infeasible:
  - Dust Opacity Tau Sweep (0.3 to 3.0) -> Solar power collapse threshold
  - Terrain Roughness / Max Slope Sweep (4 deg to 28 deg) -> Mobility limit threshold
  - Energy Budget Sweep (20 kWh to 120 kWh) -> Mission feasibility cliff
  - OWLT Delay Sweep (3 min to 35 min) -> Ground teleoperation breakdown threshold
  - Fault Severity Sweep (0.0 to 0.8) -> Resilience breakpoint
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

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
from marswalk.core.atlas_strategy_registry import BaseMissionStrategy, StrategyRegistry


@dataclass
class SensitivityCurvePoint:
    """A single evaluated point along a parameter sweep curve."""
    parameter_value: float
    strategy_id: str
    is_feasible: bool
    science_score: float
    energy_consumed_kwh: float
    battery_min_soc_pct: float
    balanced_composite_score: float


@dataclass
class ParameterSensitivityReport:
    """Complete sensitivity report across all strategies for a specific environmental or operational variable."""
    parameter_name: str
    unit: str
    parameter_range: List[float]
    strategy_curves: Dict[str, List[Dict[str, Any]]]
    infeasibility_thresholds: Dict[str, Optional[float]]  # Parameter value where strategy becomes infeasible
    robustness_rankings: List[str]


class MissionSensitivityEngine:
    """Executes multi-factor sensitivity analysis across planetary mission strategies."""

    @classmethod
    def sweep_dust_opacity(
        cls,
        base_seed: int = 1050,
        tau_values: Optional[List[float]] = None,
    ) -> ParameterSensitivityReport:
        """Sweep atmospheric dust optical depth tau from 0.3 to 2.8."""
        if tau_values is None:
            tau_values = [0.3, 0.6, 1.0, 1.4, 1.8, 2.2, 2.6]

        strategies = StrategyRegistry.create_all_competitors()
        base_scenario = GrandPrixScenarioGenerator.generate_scenario(seed=base_seed, partition=ScenarioPartition.DEVELOPMENT)

        curves: Dict[str, List[Dict[str, Any]]] = {s: [] for s in strategies}
        infeasibility_thresholds: Dict[str, Optional[float]] = {s: None for s in strategies}

        for tau in tau_values:
            scen_copy = copy.deepcopy(base_scenario)
            scen_copy.planning_context.environmental_params["dust_optical_depth_tau"] = tau
            scen_copy.planning_context.environmental_params["solar_insolation_w_m2"] = round(590.0 * np.exp(-tau * 0.7), 1)

            for s_id, strategy in strategies.items():
                ctx = scen_copy.planning_context.copy_isolated()
                plan = strategy.plan(ctx)
                eval_res = GrandPrixMetricsEvaluator.evaluate(scen_copy, plan)

                curves[s_id].append({
                    "tau": tau,
                    "is_feasible": eval_res.is_feasible,
                    "science_score": round(eval_res.science_score, 2),
                    "energy_consumed_kwh": round(eval_res.energy_consumed_kwh, 2),
                    "battery_min_soc_pct": round(eval_res.battery_min_soc_pct, 1),
                    "composite_score": round(eval_res.balanced_composite_score, 2),
                })

                if not eval_res.is_feasible and infeasibility_thresholds[s_id] is None:
                    infeasibility_thresholds[s_id] = tau

        # Rank by threshold to failure (higher tau tolerated = more robust)
        robustness_rankings = sorted(
            strategies.keys(),
            key=lambda s: infeasibility_thresholds[s] if infeasibility_thresholds[s] is not None else 999.0,
            reverse=True,
        )

        return ParameterSensitivityReport(
            parameter_name="Atmospheric Dust Optical Depth (Tau)",
            unit="dimensionless optical depth",
            parameter_range=tau_values,
            strategy_curves=curves,
            infeasibility_thresholds=infeasibility_thresholds,
            robustness_rankings=robustness_rankings,
        )

    @classmethod
    def sweep_energy_budget(
        cls,
        base_seed: int = 1060,
        energy_budgets_kwh: Optional[List[float]] = None,
    ) -> ParameterSensitivityReport:
        """Sweep available battery capacity from 30 kWh to 110 kWh."""
        if energy_budgets_kwh is None:
            energy_budgets_kwh = [30.0, 45.0, 60.0, 75.0, 90.0, 110.0]

        strategies = StrategyRegistry.create_all_competitors()
        base_scenario = GrandPrixScenarioGenerator.generate_scenario(seed=base_seed, partition=ScenarioPartition.DEVELOPMENT)

        curves: Dict[str, List[Dict[str, Any]]] = {s: [] for s in strategies}
        infeasibility_thresholds: Dict[str, Optional[float]] = {s: None for s in strategies}

        for cap in energy_budgets_kwh:
            scen_copy = copy.deepcopy(base_scenario)
            scen_copy.planning_context.resource_initial["battery_capacity_kwh"] = cap

            for s_id, strategy in strategies.items():
                ctx = scen_copy.planning_context.copy_isolated()
                plan = strategy.plan(ctx)
                eval_res = GrandPrixMetricsEvaluator.evaluate(scen_copy, plan)

                curves[s_id].append({
                    "battery_capacity_kwh": cap,
                    "is_feasible": eval_res.is_feasible,
                    "science_score": round(eval_res.science_score, 2),
                    "battery_min_soc_pct": round(eval_res.battery_min_soc_pct, 1),
                    "composite_score": round(eval_res.balanced_composite_score, 2),
                })

                if not eval_res.is_feasible and infeasibility_thresholds[s_id] is None:
                    infeasibility_thresholds[s_id] = cap

        robustness_rankings = sorted(
            strategies.keys(),
            key=lambda s: infeasibility_thresholds[s] if infeasibility_thresholds[s] is not None else 0.0,
        )

        return ParameterSensitivityReport(
            parameter_name="Battery Energy Capacity",
            unit="kWh",
            parameter_range=energy_budgets_kwh,
            strategy_curves=curves,
            infeasibility_thresholds=infeasibility_thresholds,
            robustness_rankings=robustness_rankings,
        )
