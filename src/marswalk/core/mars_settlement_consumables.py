"""MarsWalk 2.0 / Project Atlas  Milestone 13S: Consumables & Life Support Accounting.

Implements rigorous resource inventory flows, non-closed recycling loops
(water recovery, atmospheric revitalization), and population-scaled logistics
accounting: M_final = M_initial + M_produced + M_imported - M_consumed - M_lost.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class CommodityType(str, Enum):
    """Core tracked consumable commodities."""
    POTABLE_WATER = "POTABLE_WATER"
    BREATHABLE_OXYGEN = "BREATHABLE_OXYGEN"
    CALORIC_FOOD = "CALORIC_FOOD"
    HYDROGEN_FEEDSTOCK = "HYDROGEN_FEEDSTOCK"
    METHANE_PROPELLANT = "METHANE_PROPELLANT"
    CRITICAL_SPARE_PARTS = "CRITICAL_SPARE_PARTS"
    CONSTRUCTION_BLOCKS = "CONSTRUCTION_BLOCKS"


@dataclass
class ConsumableBalanceRecord:
    """Formal ledger entry for a specific commodity over simulation time delta."""
    commodity: CommodityType
    unit: str
    initial_inventory: float
    produced_locally: float
    imported_from_earth: float
    consumed: float
    process_losses: float
    final_inventory: float
    days_of_reserve_remaining: float         # Reserve margin at current consumption rate
    is_shortfall: bool                       # True if final inventory < safety buffer limit

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commodity": self.commodity.value,
            "unit": self.unit,
            "initial_inventory": round(self.initial_inventory, 2),
            "produced_locally": round(self.produced_locally, 2),
            "imported_from_earth": round(self.imported_from_earth, 2),
            "consumed": round(self.consumed, 2),
            "process_losses": round(self.process_losses, 2),
            "final_inventory": round(self.final_inventory, 2),
            "days_of_reserve_remaining": round(self.days_of_reserve_remaining, 1),
            "is_shortfall": self.is_shortfall,
        }


class SettlementConsumablesManager:
    """Tracks resource consumption, recycling efficiencies, and reserves for crew planning."""

    # Daily baseline consumption per person-sol (NASA BVAD reference values)
    H2O_CONSUMPTION_KG_PER_PERSON_SOL = 3.20   # 2.0 kg drinking + 1.2 kg food prep/hygiene
    O2_CONSUMPTION_KG_PER_PERSON_SOL = 0.84    # 0.84 kg metabolic consumption (approx 550 L)
    FOOD_DRY_MASS_KG_PER_PERSON_SOL = 0.65     # 2800 kcal dry balanced shelf-stable ration

    def __init__(
        self,
        population: int = 8,
        water_recycling_efficiency: float = 0.92, # 92% wastewater recovery (8% brine waste)
        oxygen_loop_efficiency: float = 0.88,     # 88% O2 loop recovery via Sabatier/electrolysis
    ):
        self.population = population
        self.water_recycling_efficiency = water_recycling_efficiency
        self.oxygen_loop_efficiency = oxygen_loop_efficiency

        # Current stock levels (kg)
        self.inventory: Dict[CommodityType, float] = {
            CommodityType.POTABLE_WATER: 2400.0,
            CommodityType.BREATHABLE_OXYGEN: 1100.0,
            CommodityType.CALORIC_FOOD: 3500.0,
            CommodityType.HYDROGEN_FEEDSTOCK: 85.0,
            CommodityType.METHANE_PROPELLANT: 450.0,
            CommodityType.CRITICAL_SPARE_PARTS: 120.0, # Units
            CommodityType.CONSTRUCTION_BLOCKS: 6500.0,
        }

    def simulate_sol(
        self,
        sol_duration_days: float = 1.0,
        isru_water_produced_kg: float = 0.0,
        isru_oxygen_produced_kg: float = 0.0,
        imported_food_kg: float = 0.0,
        imported_spares_units: float = 0.0,
    ) -> Dict[str, ConsumableBalanceRecord]:
        """Simulates one sol of consumption, recycling loops, and inventory evolution."""
        records: Dict[str, ConsumableBalanceRecord] = {}

        # 1. WATER BALANCE
        # Gross consumption
        gross_water_demand = self.population * self.H2O_CONSUMPTION_KG_PER_PERSON_SOL * sol_duration_days
        # Wastewater recovered through filtration & reverse osmosis
        recovered_water = gross_water_demand * self.water_recycling_efficiency
        water_recycling_losses = gross_water_demand - recovered_water
        net_water_consumed = gross_water_demand - recovered_water  # Only makeup water required

        init_h2o = self.inventory[CommodityType.POTABLE_WATER]
        final_h2o = max(0.0, init_h2o + isru_water_produced_kg - net_water_consumed)
        self.inventory[CommodityType.POTABLE_WATER] = final_h2o

        daily_burn_h2o = max(0.1, self.population * self.H2O_CONSUMPTION_KG_PER_PERSON_SOL * (1.0 - self.water_recycling_efficiency))
        reserve_h2o_days = final_h2o / daily_burn_h2o
        records["water"] = ConsumableBalanceRecord(
            commodity=CommodityType.POTABLE_WATER,
            unit="kg",
            initial_inventory=init_h2o,
            produced_locally=isru_water_produced_kg + recovered_water,
            imported_from_earth=0.0,
            consumed=gross_water_demand,
            process_losses=water_recycling_losses,
            final_inventory=final_h2o,
            days_of_reserve_remaining=reserve_h2o_days,
            is_shortfall=reserve_h2o_days < 30.0,
        )

        # 2. OXYGEN BALANCE
        gross_o2_demand = self.population * self.O2_CONSUMPTION_KG_PER_PERSON_SOL * sol_duration_days
        recycled_o2 = gross_o2_demand * self.oxygen_loop_efficiency
        o2_loop_losses = gross_o2_demand - recycled_o2
        net_o2_consumed = gross_o2_demand - recycled_o2

        init_o2 = self.inventory[CommodityType.BREATHABLE_OXYGEN]
        final_o2 = max(0.0, init_o2 + isru_oxygen_produced_kg - net_o2_consumed)
        self.inventory[CommodityType.BREATHABLE_OXYGEN] = final_o2

        daily_burn_o2 = max(0.05, self.population * self.O2_CONSUMPTION_KG_PER_PERSON_SOL * (1.0 - self.oxygen_loop_efficiency))
        reserve_o2_days = final_o2 / daily_burn_o2
        records["oxygen"] = ConsumableBalanceRecord(
            commodity=CommodityType.BREATHABLE_OXYGEN,
            unit="kg",
            initial_inventory=init_o2,
            produced_locally=isru_oxygen_produced_kg + recycled_o2,
            imported_from_earth=0.0,
            consumed=gross_o2_demand,
            process_losses=o2_loop_losses,
            final_inventory=final_o2,
            days_of_reserve_remaining=reserve_o2_days,
            is_shortfall=reserve_o2_days < 30.0,
        )

        # 3. FOOD BALANCE (No local biological production assumed in baseline)
        food_demand = self.population * self.FOOD_DRY_MASS_KG_PER_PERSON_SOL * sol_duration_days
        init_food = self.inventory[CommodityType.CALORIC_FOOD]
        final_food = max(0.0, init_food + imported_food_kg - food_demand)
        self.inventory[CommodityType.CALORIC_FOOD] = final_food

        daily_burn_food = max(0.1, self.population * self.FOOD_DRY_MASS_KG_PER_PERSON_SOL)
        reserve_food_days = final_food / daily_burn_food
        records["food"] = ConsumableBalanceRecord(
            commodity=CommodityType.CALORIC_FOOD,
            unit="kg",
            initial_inventory=init_food,
            produced_locally=0.0,
            imported_from_earth=imported_food_kg,
            consumed=food_demand,
            process_losses=0.0,
            final_inventory=final_food,
            days_of_reserve_remaining=reserve_food_days,
            is_shortfall=reserve_food_days < 45.0,
        )

        return records
