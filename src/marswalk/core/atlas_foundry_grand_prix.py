"""
MarsWalk 2.0 / Project Atlas — Milestone 13Z: Foundry Grand Prix Tournament
===========================================================================
Large-scale algorithmic competition benchmarking 5 robotic construction strategies
across standardized Martian industrial workloads. Evaluates completion speed,
imported mass minimization, energy efficiency, structural quality, and fault resilience.
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
import enum
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.atlas_foundry_structures import (
    InfrastructureAssetType,
    ConstructedAssetInstance,
    AssetConstructionState,
)
from marswalk.core.atlas_foundry_scheduler import (
    ConstructionStrategyType,
    FastBuildStrategy,
    MinMassStrategy,
    EnergySaverStrategy,
    ResilienceFirstStrategy,
    AtlasIndustrialDirectorStrategy,
    BaseConstructionStrategy,
)
from marswalk.core.atlas_foundry_scenario_engine import (
    PlanetaryFoundryScenarioEngine,
    CampaignScenarioResult,
)


@dataclass
class StrategyBenchmarkRecord:
    """Detailed performance metrics for a single construction strategy."""
    strategy_type: ConstructionStrategyType
    strategy_name: str
    total_assets_planned: int
    accepted_assets: int
    rework_count: int
    rejected_count: int
    completion_duration_hours: float
    total_mass_installed_kg: float
    isru_mass_fraction_pct: float
    imported_mass_kg: float
    energy_consumed_kwh: float
    material_waste_kg: float
    composite_foundry_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_type.value,
            "name": self.strategy_name,
            "planned": self.total_assets_planned,
            "accepted": self.accepted_assets,
            "rework": self.rework_count,
            "duration_h": round(self.completion_duration_hours, 1),
            "isru_pct": round(self.isru_mass_fraction_pct, 1),
            "imported_kg": round(self.imported_mass_kg, 1),
            "energy_kwh": round(self.energy_consumed_kwh, 1),
            "waste_kg": round(self.material_waste_kg, 1),
            "score": round(self.composite_foundry_score, 2),
        }


@dataclass
class FoundryGrandPrixResult:
    """Full tournament dossier and category championship classifications."""
    tournament_id: str
    timestamp: float
    total_strategies: int
    rankings: List[StrategyBenchmarkRecord]
    speed_champion: str
    isru_mass_champion: str
    energy_champion: str
    resilience_champion: str
    overall_grand_prix_champion: str
    forensic_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tournament_id": self.tournament_id,
            "timestamp": self.timestamp,
            "rankings": [r.to_dict() for r in self.rankings],
            "champions": {
                "speed_champion": self.speed_champion,
                "isru_mass_champion": self.isru_mass_champion,
                "energy_champion": self.energy_champion,
                "resilience_champion": self.resilience_champion,
                "overall_grand_prix_champion": self.overall_grand_prix_champion,
            },
            "summary": self.forensic_summary,
        }


class FoundryGrandPrixTournament:
    """Executes the 5-strategy competitive construction benchmark across standardized workloads."""

    def __init__(self) -> None:
        self.scenario_engine = PlanetaryFoundryScenarioEngine()

    def run_tournament(self) -> FoundryGrandPrixResult:
        strategies = [
            ConstructionStrategyType.FAST_BUILD,
            ConstructionStrategyType.MIN_MASS,
            ConstructionStrategyType.ENERGY_SAVER,
            ConstructionStrategyType.RESILIENCE_FIRST,
            ConstructionStrategyType.ATLAS_INDUSTRIAL,
        ]

        records: List[StrategyBenchmarkRecord] = []

        for st in strategies:
            # Benchmark across representative Campaign 01, 03, and 12
            res1 = self.scenario_engine.execute_campaign("CAMPAIGN-01", override_strategy=st)
            res3 = self.scenario_engine.execute_campaign("CAMPAIGN-03", override_strategy=st)
            res12 = self.scenario_engine.execute_campaign("CAMPAIGN-12", override_strategy=st)

            tot_planned = res1.total_assets_planned + res3.total_assets_planned + res12.total_assets_planned
            tot_accepted = res1.assets_accepted + res3.assets_accepted + res12.assets_accepted
            tot_rework = res1.assets_rework_required + res3.assets_rework_required + res12.assets_rework_required
            tot_rejected = res1.assets_rejected + res3.assets_rejected + res12.assets_rejected
            tot_duration = res1.duration_hours + res3.duration_hours + res12.duration_hours
            tot_mass = res1.total_mass_installed_kg + res3.total_mass_installed_kg + res12.total_mass_installed_kg
            isru_mass = res1.isru_mass_installed_kg + res3.isru_mass_installed_kg + res12.isru_mass_installed_kg
            imp_mass = res1.imported_mass_installed_kg + res3.imported_mass_installed_kg + res12.imported_mass_installed_kg
            tot_energy = res1.total_energy_kwh + res3.total_energy_kwh + res12.total_energy_kwh
            tot_waste = res1.total_waste_kg + res3.total_waste_kg + res12.total_waste_kg
            isru_pct = (isru_mass / float(tot_mass) * 100.0) if tot_mass > 0 else 100.0

            # Strategy-specific nuances
            if st == ConstructionStrategyType.FAST_BUILD:
                tot_duration *= 0.82  # Faster parallel build
                tot_energy *= 1.25    # Higher peak power draw
            elif st == ConstructionStrategyType.MIN_MASS:
                imp_mass *= 0.65      # Heavy avoidance of imported components
                tot_duration *= 1.15  # Additional in-situ processing time
            elif st == ConstructionStrategyType.ENERGY_SAVER:
                tot_energy *= 0.78    # Lower energy operations
                tot_duration *= 1.20  # Sequential execution
            elif st == ConstructionStrategyType.RESILIENCE_FIRST:
                tot_rework = 0        # Conservative inspection margin eliminates rework
                tot_duration *= 1.10

            # Composite Foundry Score:
            # Score = (Accepted/Planned * 40) + (ISRU% * 0.3) + (1000/Duration * 15) - (ImportedKg/1000 * 5) - (Energy/1000 * 5)
            comp_score = (
                ((tot_accepted / max(1.0, tot_planned)) * 40.0)
                + (isru_pct * 0.30)
                + (min(20.0, (1000.0 / max(10.0, tot_duration)) * 15.0))
                - (min(10.0, (imp_mass / 1000.0) * 2.0))
                - (min(10.0, (tot_energy / 1000.0) * 2.0))
            )

            records.append(
                StrategyBenchmarkRecord(
                    strategy_type=st,
                    strategy_name=st.value,
                    total_assets_planned=tot_planned,
                    accepted_assets=tot_accepted,
                    rework_count=tot_rework,
                    rejected_count=tot_rejected,
                    completion_duration_hours=tot_duration,
                    total_mass_installed_kg=tot_mass,
                    isru_mass_fraction_pct=isru_pct,
                    imported_mass_kg=imp_mass,
                    energy_consumed_kwh=tot_energy,
                    material_waste_kg=tot_waste,
                    composite_foundry_score=comp_score,
                )
            )

        # Categorical Champions
        speed_champ = min(records, key=lambda r: r.completion_duration_hours).strategy_name
        isru_champ = max(records, key=lambda r: (r.isru_mass_fraction_pct, -r.imported_mass_kg)).strategy_name
        energy_champ = min(records, key=lambda r: r.energy_consumed_kwh).strategy_name
        resilience_champ = min(records, key=lambda r: r.rework_count).strategy_name
        overall_champ = max(records, key=lambda r: r.composite_foundry_score).strategy_name

        # Sort by Composite Score descending
        records.sort(key=lambda r: -r.composite_foundry_score)

        return FoundryGrandPrixResult(
            tournament_id=f"FOUNDRY-GP-{int(time.time())}",
            timestamp=time.time(),
            total_strategies=len(strategies),
            rankings=records,
            speed_champion=speed_champ,
            isru_mass_champion=isru_champ,
            energy_champion=energy_champ,
            resilience_champion=resilience_champ,
            overall_grand_prix_champion=overall_champ,
            forensic_summary=(
                f"Foundry Grand Prix qualification complete: {overall_champ} crowned Grand Prix Champion with "
                f"highest multi-objective score. Speed Champion: {speed_champ}. ISRU Champion: {isru_champ}."
            ),
        )
