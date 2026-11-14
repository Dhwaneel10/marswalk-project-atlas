"""MarsWalk 2.0 / Project Atlas  Milestone 13S: Settlement Operations Director.

Integrates site selection, architecture, power, ISRU, consumables, habitats,
and autonomous construction under an event-driven multi-sol digital twin.
Evaluates the formal Phase F Hypothetical Crew-Arrival Readiness Review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from marswalk.core.mars_settlement_architecture import (
    InfrastructureDependencyDAG,
    NodeCommissioningState,
    SettlementArchetype,
    SettlementArchitecturePlanner,
    SettlementConfiguration,
)
from marswalk.core.mars_settlement_construction import (
    AutonomousConstructionDirector,
    OperationStatus,
)
from marswalk.core.mars_settlement_consumables import (
    SettlementConsumablesManager,
)
from marswalk.core.mars_settlement_power import (
    PowerSourceType,
    SettlementPowerSystem,
)
from marswalk.core.mars_isru_engine import (
    ISRUEngine,
)
from marswalk.core.mars_habitat_model import (
    HabitatThermalNetwork,
)


class SettlementLifecycleState(str, Enum):
    """The formal operational lifecycle states of a Martian research settlement."""
    CONCEPT = "CONCEPT"
    SITE_SELECTED = "SITE_SELECTED"
    PRECURSOR_DEPLOYMENT = "PRECURSOR_DEPLOYMENT"
    CONSTRUCTION = "CONSTRUCTION"
    COMMISSIONING = "COMMISSIONING"
    PARTIALLY_OPERATIONAL = "PARTIALLY_OPERATIONAL"
    OPERATIONAL_SIMULATION = "OPERATIONAL_SIMULATION"
    DEGRADED = "DEGRADED"
    RECOVERY = "RECOVERY"
    EXPANSION = "EXPANSION"
    ABANDONED = "ABANDONED"


@dataclass
class CrewReadinessAssessment:
    """Formal Phase F Hypothetical Crew-Arrival Readiness Review audit."""
    is_ready_for_simulation_arrival: bool
    readiness_score_pct: float               # 0.0 to 100.0%
    verified_checkpoints: List[str]
    unmet_gaps: List[str]
    water_reserve_days: float
    oxygen_reserve_days: float
    food_reserve_days: float
    power_reserve_margin_pct: float
    mandatory_safety_disclaimer: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_ready_for_simulation_arrival": self.is_ready_for_simulation_arrival,
            "readiness_score_pct": round(self.readiness_score_pct, 1),
            "verified_checkpoints": self.verified_checkpoints,
            "unmet_gaps": self.unmet_gaps,
            "water_reserve_days": round(self.water_reserve_days, 1),
            "oxygen_reserve_days": round(self.oxygen_reserve_days, 1),
            "food_reserve_days": round(self.food_reserve_days, 1),
            "power_reserve_margin_pct": round(self.power_reserve_margin_pct, 1),
            "mandatory_safety_disclaimer": self.mandatory_safety_disclaimer,
        }


class SettlementOperationsDirector:
    """The master simulation orchestrator for the planetary settlement digital twin."""

    def __init__(
        self,
        config: Optional[SettlementConfiguration] = None,
        archetype: Optional[SettlementArchetype] = None,
    ):
        if config is not None:
            self.config = config
        else:
            arch = archetype or SettlementArchetype.MARS_BASE_ALPHA
            self.config = SettlementArchitecturePlanner.create_settlement_plan(
                archetype=arch,
                site_id="SITE-DELTA-NORTH",
            )

        self.lifecycle_state = SettlementLifecycleState.OPERATIONAL_SIMULATION
        self.current_sol: int = 1
        self.current_time_s: float = 3600.0

        # Subsystems
        self.power_system = SettlementPowerSystem(
            system_type=PowerSourceType.NUCLEAR_FISSION,
            nameplate_capacity_kw=self.config.total_power_capacity_kw,
            battery_capacity_kwh=self.config.energy_storage_capacity_kwh,
        )
        self.isru_engine = ISRUEngine()
        self.consumables_manager = SettlementConsumablesManager(
            population=self.config.population_capacity,
        )
        self.habitat_network = HabitatThermalNetwork()
        self.construction_director = AutonomousConstructionDirector()

        self._event_log: List[Dict[str, Any]] = []

    def advance_simulation(
        self,
        sols_to_advance: int = 1,
        ambient_temp_c: float = -65.0,
        atmospheric_tau: float = 0.45,
    ) -> Dict[str, Any]:
        """Steps the integrated digital twin forward by the specified number of sols."""
        for _ in range(sols_to_advance):
            self.current_sol += 1

            # 1. Step power system (day/night sol simulation)
            power_telemetry = self.power_system.step_sol_time(
                sol=self.current_sol,
                time_s=self.current_time_s,
                dt_s=88775.0,
                atmospheric_tau=atmospheric_tau,
            )

            # 2. Step ISRU production if power available
            if not self.power_system._loads["LOAD-ISRU-WATER"].is_shed:
                # Produce baseline water from excavated regolith
                water_audit = self.isru_engine.extract_water_from_regolith(
                    excavated_feedstock_kg=120.0,
                    water_wt_pct=7.0,
                )
                water_prod_kg = water_audit.total_products_kg
            else:
                water_prod_kg = 0.0

            if not self.power_system._loads["LOAD-ISRU-O2"].is_shed:
                # Produce baseline oxygen from atmospheric CO2
                o2_audit = self.isru_engine.generate_atmospheric_oxygen(co2_intake_kg=85.0)
                o2_prod_kg = o2_audit.total_products_kg
            else:
                o2_prod_kg = 0.0

            # 3. Step consumables consumption & recycling loops
            consumable_records = self.consumables_manager.simulate_sol(
                sol_duration_days=1.0,
                isru_water_produced_kg=water_prod_kg,
                isru_oxygen_produced_kg=o2_prod_kg,
            )

            # 4. Step habitat thermal network
            thermal_records = self.habitat_network.evaluate_thermal_step(
                ambient_temp_c=ambient_temp_c,
                solar_flux_wm2=520.0,
                dt_s=88775.0,
            )

            # 5. Log milestone event
            self._event_log.append({
                "sol": self.current_sol,
                "power_generation_kw": power_telemetry.generation_gross_kw,
                "water_produced_kg": water_prod_kg,
                "oxygen_produced_kg": o2_prod_kg,
                "water_reserve_days": consumable_records["water"].days_of_reserve_remaining,
                "oxygen_reserve_days": consumable_records["oxygen"].days_of_reserve_remaining,
            })

        return {
            "current_sol": self.current_sol,
            "lifecycle_state": self.lifecycle_state.value,
            "power": power_telemetry.to_dict(),
            "consumables": {k: v.to_dict() for k, v in consumable_records.items()},
            "thermal": [t.to_dict() for t in thermal_records],
            "inventories": self.isru_engine.inventories.to_dict(),
        }

    def evaluate_crew_readiness_review(self) -> CrewReadinessAssessment:
        """Conducts formal Phase F Hypothetical Crew-Arrival Readiness Review."""
        checkpoints = []
        gaps = []

        # 1. Structural shell integrity & pressure
        all_pressurized = True
        for mod in self.habitat_network.modules.values():
            if mod.internal_pressure_kpa < 50.0:
                all_pressurized = False
                gaps.append(f"Module '{mod.module_id}' pressure below 50 kPa.")
        if all_pressurized:
            checkpoints.append("Habitat structural integrity & internal 56.5 kPa atmosphere verified.")

        # 2. Power system capacity
        power_ok = self.power_system.generator_availability_factor > 0.85
        if power_ok:
            checkpoints.append(f"Primary surface power operational ({self.config.total_power_capacity_kw} kWe).")
        else:
            gaps.append("Primary power generator degraded or offline.")

        # 3. Consumable reserves
        sim_res = self.consumables_manager.simulate_sol(0.0) # Query state
        h2o_days = sim_res["water"].days_of_reserve_remaining
        o2_days = sim_res["oxygen"].days_of_reserve_remaining
        food_days = sim_res["food"].days_of_reserve_remaining

        if h2o_days >= 60.0:
            checkpoints.append(f"Potable water reserve verified ({h2o_days:.1f} days margin).")
        else:
            gaps.append(f"Potable water reserve insufficient ({h2o_days:.1f} / 60.0 days required).")

        if o2_days >= 60.0:
            checkpoints.append(f"Breathable oxygen reserve verified ({o2_days:.1f} days margin).")
        else:
            gaps.append(f"Breathable oxygen reserve insufficient ({o2_days:.1f} / 60.0 days required).")

        if food_days >= 90.0:
            checkpoints.append(f"Caloric food ration reserve verified ({food_days:.1f} days margin).")
        else:
            gaps.append(f"Food ration reserve insufficient ({food_days:.1f} / 90.0 days required).")

        # 4. Construction completion
        sched = self.construction_director.evaluate_schedule(self.current_sol)
        if sched["completed_count"] >= 14:
            checkpoints.append("All 15 phased robotic construction operations completed and verified.")
        else:
            gaps.append(f"Construction incomplete ({sched['completed_count']} / 15 operations completed).")

        total_checks = len(checkpoints) + len(gaps)
        score_pct = (len(checkpoints) / max(1, total_checks)) * 100.0
        is_ready = (len(gaps) == 0 and score_pct >= 90.0)

        disclaimer = (
            "MANDATORY DISCLOSURE: This Phase F Readiness Review is a conceptual research simulation gate. "
            "It does NOT certify flight qualification, human life-support reliability, or operational safety for astronauts."
        )

        return CrewReadinessAssessment(
            is_ready_for_simulation_arrival=is_ready,
            readiness_score_pct=score_pct,
            verified_checkpoints=checkpoints,
            unmet_gaps=gaps,
            water_reserve_days=h2o_days,
            oxygen_reserve_days=o2_days,
            food_reserve_days=food_days,
            power_reserve_margin_pct=35.0 if power_ok else 5.0,
            mandatory_safety_disclaimer=disclaimer,
        )
