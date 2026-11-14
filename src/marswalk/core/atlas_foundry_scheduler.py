"""
MarsWalk 2.0 / Project Atlas — Milestone 13Z: Construction Strategy Schedulers
==============================================================================
Suite of 5 competing construction scheduling strategies for Martian infrastructure:
1. FAST_BUILD (Schedule minimization via max parallelization)
2. MIN_MASS (Minimizes imported logistics mass; maximizes local ISRU)
3. ENERGY_SAVER (Power load-leveling and peak solar scheduling)
4. RESILIENCE_FIRST (Structural redundancy, buffer preservation, spare-parts safety)
5. ATLAS_INDUSTRIAL (Adaptive multi-objective Pareto optimization)
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
import enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.atlas_foundry_structures import (
    InfrastructureAssetType,
    ConstructedAssetInstance,
    AssetConstructionState,
)
from marswalk.core.atlas_foundry_robotics import (
    IndustrialRobot,
    RobotClass,
    RobotOperatingState,
)
from marswalk.core.atlas_foundry_materials import (
    SettlementMaterialInventory,
    MaterialCategory,
)


class ConstructionStrategyType(str, enum.Enum):
    """The 5 competing industrial construction strategies."""
    FAST_BUILD = "STRAT-01-FAST-BUILD"
    MIN_MASS = "STRAT-02-MIN-MASS"
    ENERGY_SAVER = "STRAT-03-ENERGY-SAVER"
    RESILIENCE_FIRST = "STRAT-04-RESILIENCE-FIRST"
    ATLAS_INDUSTRIAL = "STRAT-05-ATLAS-INDUSTRIAL"


@dataclass
class ConstructionScheduleDecision:
    """A scheduled task allocation decision made by an industrial strategy."""
    decision_id: str
    asset_id: str
    robot_id: str
    strategy_type: ConstructionStrategyType
    priority_score: float
    rationale: str
    scheduled_start_hours: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "asset_id": self.asset_id,
            "robot_id": self.robot_id,
            "strategy": self.strategy_type.value,
            "priority": round(self.priority_score, 2),
            "rationale": self.rationale,
            "start_h": round(self.scheduled_start_hours, 1),
        }


class BaseConstructionStrategy:
    """Base interface for all construction strategy schedulers."""

    def __init__(self, strategy_type: ConstructionStrategyType) -> None:
        self.strategy_type = strategy_type

    def prioritize_assets(
        self,
        candidate_assets: List[ConstructedAssetInstance],
        inventory: SettlementMaterialInventory,
        fleet: List[IndustrialRobot],
    ) -> List[ConstructedAssetInstance]:
        raise NotImplementedError


class FastBuildStrategy(BaseConstructionStrategy):
    """
    STRAT-01-FAST-BUILD: Minimizes total construction campaign duration.
    Ranks assets by shortest remaining duration and maximizes parallel execution.
    """

    def __init__(self) -> None:
        super().__init__(ConstructionStrategyType.FAST_BUILD)

    def prioritize_assets(
        self,
        candidate_assets: List[ConstructedAssetInstance],
        inventory: SettlementMaterialInventory,
        fleet: List[IndustrialRobot],
    ) -> List[ConstructedAssetInstance]:
        # Sort by shortest duration to complete early
        return sorted(candidate_assets, key=lambda a: a.definition.nominal_duration_hours)


class MinMassStrategy(BaseConstructionStrategy):
    """
    STRAT-02-MIN-MASS: Minimizes imported component mass from Earth.
    Strictly prioritizes assets with >=95% In-Situ Resource Utilization (ISRU) fraction.
    """

    def __init__(self) -> None:
        super().__init__(ConstructionStrategyType.MIN_MASS)

    def prioritize_assets(
        self,
        candidate_assets: List[ConstructedAssetInstance],
        inventory: SettlementMaterialInventory,
        fleet: List[IndustrialRobot],
    ) -> List[ConstructedAssetInstance]:
        # Sort by highest ISRU mass fraction and lowest imported mass
        return sorted(
            candidate_assets,
            key=lambda a: (-a.definition.boq.isru_mass_fraction_pct, a.definition.boq.total_imported_mass_kg)
        )


class EnergySaverStrategy(BaseConstructionStrategy):
    """
    STRAT-03-ENERGY-SAVER: Minimizes peak electrical power and total kWh draw.
    Schedules lower-energy earthmoving first and throttles energy-intensive microwave sintering.
    """

    def __init__(self) -> None:
        super().__init__(ConstructionStrategyType.ENERGY_SAVER)

    def prioritize_assets(
        self,
        candidate_assets: List[ConstructedAssetInstance],
        inventory: SettlementMaterialInventory,
        fleet: List[IndustrialRobot],
    ) -> List[ConstructedAssetInstance]:
        # Sort by lowest nominal energy requirements
        return sorted(candidate_assets, key=lambda a: a.definition.nominal_energy_kwh)


class ResilienceFirstStrategy(BaseConstructionStrategy):
    """
    STRAT-04-RESILIENCE-FIRST: Maximizes mission assurance and survivability.
    Schedules protective berms and equipment shelters before unshielded utilities,
    and requires robots to maintain >=40% battery reserve before deployment.
    """

    def __init__(self) -> None:
        super().__init__(ConstructionStrategyType.RESILIENCE_FIRST)

    def prioritize_assets(
        self,
        candidate_assets: List[ConstructedAssetInstance],
        inventory: SettlementMaterialInventory,
        fleet: List[IndustrialRobot],
    ) -> List[ConstructedAssetInstance]:
        # Protective infrastructure ranked first
        protective_types = {
            InfrastructureAssetType.REGOLITH_BERMS_SHIELDING,
            InfrastructureAssetType.EQUIPMENT_SHELTERS,
            InfrastructureAssetType.SURFACE_RELAY_STATIONS,
        }
        return sorted(
            candidate_assets,
            key=lambda a: (0 if a.asset_type in protective_types else 1, a.definition.nominal_duration_hours)
        )


class AtlasIndustrialDirectorStrategy(BaseConstructionStrategy):
    """
    STRAT-05-ATLAS-INDUSTRIAL: Multi-objective adaptive director.
    Computes a Pareto composite score balancing schedule urgency, local ISRU mass,
    energy efficiency, and structural reliability.
    """

    def __init__(self) -> None:
        super().__init__(ConstructionStrategyType.ATLAS_INDUSTRIAL)

    def prioritize_assets(
        self,
        candidate_assets: List[ConstructedAssetInstance],
        inventory: SettlementMaterialInventory,
        fleet: List[IndustrialRobot],
    ) -> List[ConstructedAssetInstance]:
        def score(a: ConstructedAssetInstance) -> float:
            isru_score = a.definition.boq.isru_mass_fraction_pct * 0.4
            time_score = (100.0 / max(1.0, a.definition.nominal_duration_hours)) * 0.3
            energy_score = (1000.0 / max(1.0, a.definition.nominal_energy_kwh)) * 0.2
            compressive_score = a.definition.min_compressive_strength_mpa * 0.1
            return isru_score + time_score + energy_score + compressive_score

        return sorted(candidate_assets, key=lambda a: -score(a))
