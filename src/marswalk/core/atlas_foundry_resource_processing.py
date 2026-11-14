"""
MarsWalk 2.0 / Project Atlas — Milestone 13Z: Engineering Production & Mass-Energy Accounting
=============================================================================================
Governs the physical manufacturing transformations of Martian materials.
Enforces strict mass conservation (M_in = M_out + M_waste), energetic cost tracking,
and unit consistency across all 9 ISRU manufacturing stages.
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
import enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.atlas_foundry_materials import (
    MaterialCategory,
    MaterialBatch,
    MaterialSpec,
    STANDARD_MATERIAL_SPECS,
    SettlementMaterialInventory,
)
from marswalk.core.atlas_foundry_robotics import (
    IndustrialRobot,
    RobotClass,
    RobotOperatingState,
)


class ProcessingOperationType(str, enum.Enum):
    """The formal manufacturing transformation stages in the Martian Foundry."""
    EXCAVATION = "EXCAVATION"                      # Unexcavated ground -> Raw regolith feedstock
    SCREENING = "SCREENING"                        # Raw regolith -> Screened fines (<150um) + Oversized rejects
    COMPACTION = "COMPACTION"                      # Graded regolith -> Mechanically compacted subgrade
    THERMAL_SINTERING = "THERMAL_SINTERING"        # Screened fines -> Vitrified structural basalt pavers
    GEOPOLYMER_SYNTHESIS = "GEOPOLYMER_SYNTHESIS"  # Screened fines + Activator -> High-strength composite
    COMPONENT_FINISHING = "COMPONENT_FINISHING"    # Precision milling and edge finishing of pavers/fasteners


@dataclass
class ProductionTransformationRecord:
    """An immutable audit record of a physical mass-energy processing operation."""
    record_id: str
    operation: ProcessingOperationType
    settlement_id: str
    input_category: MaterialCategory
    output_category: MaterialCategory
    input_mass_kg: float
    output_usable_mass_kg: float
    waste_mass_kg: float
    energy_consumed_kwh: float
    duration_hours: float
    assigned_robot_id: str
    timestamp_s: float
    success: bool
    quality_score: float

    def __post_init__(self) -> None:
        # Enforce strict mass conservation: input mass must equal usable + waste mass
        mass_delta = abs(self.input_mass_kg - (self.output_usable_mass_kg + self.waste_mass_kg))
        if mass_delta > 1e-4:
            raise ValueError(
                f"Mass conservation violated in {self.record_id}: "
                f"Input ({self.input_mass_kg} kg) != Output ({self.output_usable_mass_kg} kg) + Waste ({self.waste_mass_kg} kg)"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "op": self.operation.value,
            "settlement": self.settlement_id,
            "input_cat": self.input_category.value,
            "output_cat": self.output_category.value,
            "in_kg": round(self.input_mass_kg, 2),
            "out_kg": round(self.output_usable_mass_kg, 2),
            "waste_kg": round(self.waste_mass_kg, 2),
            "energy_kwh": round(self.energy_consumed_kwh, 3),
            "duration_h": round(self.duration_hours, 2),
            "robot": self.assigned_robot_id,
            "quality": round(self.quality_score, 3),
            "success": self.success,
        }


class FoundryProductionEngine:
    """Executes deterministic physical transformations with mass conservation and energy tracking."""

    def __init__(self, settlement_inventories: Dict[str, SettlementMaterialInventory]) -> None:
        self.inventories = settlement_inventories
        self.transformation_history: List[ProductionTransformationRecord] = []
        self.record_counter = 1

    def execute_excavation(
        self,
        settlement_id: str,
        target_mass_kg: float,
        robot: IndustrialRobot,
        current_time_s: float,
    ) -> ProductionTransformationRecord:
        """
        Excavates raw regolith from the surface into the settlement feedstock buffer.
        Input: In-situ surface soil.
        Output: REGOLITH_FEEDSTOCK_RAW (Yield = 100%, Waste = 0%).
        """
        if math.isnan(target_mass_kg) or math.isinf(target_mass_kg) or target_mass_kg <= 0:
            raise ValueError(f"Excavation target_mass_kg must be a positive finite number, got {target_mass_kg}")
        inv = self.inventories[settlement_id]
        spec = STANDARD_MATERIAL_SPECS[MaterialCategory.REGOLITH_FEEDSTOCK_RAW]

        # Check robot capability
        if not robot.can_perform_task(RobotClass.EXCAVATOR, target_mass_kg):
            raise ValueError(f"Robot {robot.asset_id} cannot perform excavation of {target_mass_kg} kg")

        # Excavation rate ~ 250 kg/hr
        duration_hours = max(0.1, target_mass_kg / 250.0)
        energy_kwh = target_mass_kg * spec.processing_energy_kwh_kg
        robot.consume_energy(duration_hours)

        inv.stocks_kg[MaterialCategory.REGOLITH_FEEDSTOCK_RAW] += target_mass_kg
        inv.cumulative_excavated_kg += target_mass_kg
        inv.cumulative_energy_consumed_kwh += energy_kwh

        rec = ProductionTransformationRecord(
            record_id=f"PROD-EXC-{self.record_counter:05d}",
            operation=ProcessingOperationType.EXCAVATION,
            settlement_id=settlement_id,
            input_category=MaterialCategory.REGOLITH_FEEDSTOCK_RAW,
            output_category=MaterialCategory.REGOLITH_FEEDSTOCK_RAW,
            input_mass_kg=target_mass_kg,
            output_usable_mass_kg=target_mass_kg,
            waste_mass_kg=0.0,
            energy_consumed_kwh=energy_kwh,
            duration_hours=duration_hours,
            assigned_robot_id=robot.asset_id,
            timestamp_s=current_time_s,
            success=True,
            quality_score=0.98,
        )
        self.record_counter += 1
        self.transformation_history.append(rec)
        return rec

    def execute_screening(
        self,
        settlement_id: str,
        input_mass_kg: float,
        robot: IndustrialRobot,
        current_time_s: float,
    ) -> ProductionTransformationRecord:
        """
        Screens raw regolith into graded fines (<150um).
        Yield = 82%, Waste = 18% oversized cobbles.
        """
        if math.isnan(input_mass_kg) or math.isinf(input_mass_kg) or input_mass_kg <= 0:
            raise ValueError(f"Screening input_mass_kg must be a positive finite number, got {input_mass_kg}")
        inv = self.inventories[settlement_id]
        if inv.stocks_kg[MaterialCategory.REGOLITH_FEEDSTOCK_RAW] < input_mass_kg:
            raise ValueError(f"Insufficient raw feedstock ({inv.stocks_kg[MaterialCategory.REGOLITH_FEEDSTOCK_RAW]:.1f} kg < {input_mass_kg} kg)")

        spec = STANDARD_MATERIAL_SPECS[MaterialCategory.REGOLITH_SCREENED]
        usable_mass = round(input_mass_kg * spec.yield_fraction, 4)
        waste_mass = round(input_mass_kg - usable_mass, 4)

        duration_hours = max(0.1, input_mass_kg / 400.0)  # 400 kg/hr screening throughput
        energy_kwh = input_mass_kg * spec.processing_energy_kwh_kg
        robot.consume_energy(duration_hours)

        inv.stocks_kg[MaterialCategory.REGOLITH_FEEDSTOCK_RAW] -= input_mass_kg
        inv.stocks_kg[MaterialCategory.REGOLITH_SCREENED] += usable_mass
        inv.cumulative_processed_kg += usable_mass
        inv.cumulative_waste_kg += waste_mass
        inv.cumulative_energy_consumed_kwh += energy_kwh

        rec = ProductionTransformationRecord(
            record_id=f"PROD-SCR-{self.record_counter:05d}",
            operation=ProcessingOperationType.SCREENING,
            settlement_id=settlement_id,
            input_category=MaterialCategory.REGOLITH_FEEDSTOCK_RAW,
            output_category=MaterialCategory.REGOLITH_SCREENED,
            input_mass_kg=input_mass_kg,
            output_usable_mass_kg=usable_mass,
            waste_mass_kg=waste_mass,
            energy_consumed_kwh=energy_kwh,
            duration_hours=duration_hours,
            assigned_robot_id=robot.asset_id,
            timestamp_s=current_time_s,
            success=True,
            quality_score=0.96,
        )
        self.record_counter += 1
        self.transformation_history.append(rec)
        return rec

    def execute_sintering(
        self,
        settlement_id: str,
        input_mass_kg: float,
        robot: IndustrialRobot,
        current_time_s: float,
    ) -> ProductionTransformationRecord:
        """
        Thermally fuses screened regolith into dense basaltic pavers.
        Yield = 92%, Waste = 8% thermal spall loss.
        """
        if math.isnan(input_mass_kg) or math.isinf(input_mass_kg) or input_mass_kg <= 0:
            raise ValueError(f"Sintering input_mass_kg must be a positive finite number, got {input_mass_kg}")
        inv = self.inventories[settlement_id]
        if inv.stocks_kg[MaterialCategory.REGOLITH_SCREENED] < input_mass_kg:
            raise ValueError(f"Insufficient screened regolith ({inv.stocks_kg[MaterialCategory.REGOLITH_SCREENED]:.1f} kg < {input_mass_kg} kg)")

        spec = STANDARD_MATERIAL_SPECS[MaterialCategory.REGOLITH_SINTERED_BLOCKS]
        usable_mass = round(input_mass_kg * spec.yield_fraction, 4)
        waste_mass = round(input_mass_kg - usable_mass, 4)

        duration_hours = max(0.2, input_mass_kg / 150.0)  # 150 kg/hr sintering throughput
        energy_kwh = input_mass_kg * spec.processing_energy_kwh_kg  # 1.45 kWh/kg
        robot.consume_energy(duration_hours, power_multiplier=1.2)

        inv.stocks_kg[MaterialCategory.REGOLITH_SCREENED] -= input_mass_kg
        inv.stocks_kg[MaterialCategory.REGOLITH_SINTERED_BLOCKS] += usable_mass
        inv.cumulative_processed_kg += usable_mass
        inv.cumulative_waste_kg += waste_mass
        inv.cumulative_energy_consumed_kwh += energy_kwh

        rec = ProductionTransformationRecord(
            record_id=f"PROD-SNT-{self.record_counter:05d}",
            operation=ProcessingOperationType.THERMAL_SINTERING,
            settlement_id=settlement_id,
            input_category=MaterialCategory.REGOLITH_SCREENED,
            output_category=MaterialCategory.REGOLITH_SINTERED_BLOCKS,
            input_mass_kg=input_mass_kg,
            output_usable_mass_kg=usable_mass,
            waste_mass_kg=waste_mass,
            energy_consumed_kwh=energy_kwh,
            duration_hours=duration_hours,
            assigned_robot_id=robot.asset_id,
            timestamp_s=current_time_s,
            success=True,
            quality_score=0.95,
        )
        self.record_counter += 1
        self.transformation_history.append(rec)
        return rec

    def execute_compaction(
        self,
        settlement_id: str,
        input_mass_kg: float,
        robot: IndustrialRobot,
        current_time_s: float,
    ) -> ProductionTransformationRecord:
        """
        Mechanically rolls raw or screened regolith into stabilized subgrade.
        Yield = 98%, Waste = 2%.
        """
        if math.isnan(input_mass_kg) or math.isinf(input_mass_kg) or input_mass_kg <= 0:
            raise ValueError(f"Compaction input_mass_kg must be a positive finite number, got {input_mass_kg}")
        inv = self.inventories[settlement_id]
        if inv.stocks_kg[MaterialCategory.REGOLITH_FEEDSTOCK_RAW] < input_mass_kg:
            raise ValueError(f"Insufficient raw feedstock ({inv.stocks_kg[MaterialCategory.REGOLITH_FEEDSTOCK_RAW]:.1f} kg < {input_mass_kg} kg)")

        spec = STANDARD_MATERIAL_SPECS[MaterialCategory.REGOLITH_COMPACTED]
        usable_mass = round(input_mass_kg * spec.yield_fraction, 4)
        waste_mass = round(input_mass_kg - usable_mass, 4)

        duration_hours = max(0.1, input_mass_kg / 500.0)
        energy_kwh = input_mass_kg * spec.processing_energy_kwh_kg
        robot.consume_energy(duration_hours)

        inv.stocks_kg[MaterialCategory.REGOLITH_FEEDSTOCK_RAW] -= input_mass_kg
        inv.stocks_kg[MaterialCategory.REGOLITH_COMPACTED] += usable_mass
        inv.cumulative_processed_kg += usable_mass
        inv.cumulative_waste_kg += waste_mass
        inv.cumulative_energy_consumed_kwh += energy_kwh

        rec = ProductionTransformationRecord(
            record_id=f"PROD-CMP-{self.record_counter:05d}",
            operation=ProcessingOperationType.COMPACTION,
            settlement_id=settlement_id,
            input_category=MaterialCategory.REGOLITH_FEEDSTOCK_RAW,
            output_category=MaterialCategory.REGOLITH_COMPACTED,
            input_mass_kg=input_mass_kg,
            output_usable_mass_kg=usable_mass,
            waste_mass_kg=waste_mass,
            energy_consumed_kwh=energy_kwh,
            duration_hours=duration_hours,
            assigned_robot_id=robot.asset_id,
            timestamp_s=current_time_s,
            success=True,
            quality_score=0.97,
        )
        self.record_counter += 1
        self.transformation_history.append(rec)
        return rec
