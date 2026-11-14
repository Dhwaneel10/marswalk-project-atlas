"""
MarsWalk 2.0 / Project Atlas — Milestone 13Z: Maintenance & Industrial Resilience Engine
========================================================================================
Fault injection, automated diagnostic isolation, spare-parts accounting, and preventive
servicing of autonomous industrial construction machinery under harsh Martian operating conditions.
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
import enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.atlas_foundry_robotics import (
    IndustrialRobot,
    RobotClass,
    RobotOperatingState,
)
from marswalk.core.atlas_foundry_materials import (
    SettlementMaterialInventory,
    MaterialCategory,
)


class IndustrialFaultType(str, enum.Enum):
    """Specific failure modes affecting construction and manufacturing assets."""
    EXCAVATOR_CUTTER_BLUNT = "EXCAVATOR_CUTTER_BLUNT"              # High mechanical resistance; 50% slower excavation
    HAULER_DRIVE_MOTOR_STALL = "HAULER_DRIVE_MOTOR_STALL"          # Wheel actuator seizure; immobilized
    SINTERING_OPTICS_DUST_FOULING = "SINTERING_OPTICS_DUST_FOULING"# Laser/microwave beam scattering; defective blocks
    GEOPOLYMER_MIXER_DRUM_JAM = "GEOPOLYMER_MIXER_DRUM_JAM"        # Premature slurry cure in mixing nozzle
    POWER_BUS_BROWNOUT = "POWER_BUS_BROWNOUT"                      # Grid voltage drop; charging suspended
    INSPECTION_LIDAR_DRIFT = "INSPECTION_LIDAR_DRIFT"              # Optical calibration error; false rework flags
    SPARE_PART_DEPLETION = "SPARE_PART_DEPLETION"                  # Critical replacement component unavailable


@dataclass
class MaintenanceActionRecord:
    """An official record of a robotic maintenance intervention."""
    action_id: str
    target_robot_id: str
    maintainer_robot_id: str
    settlement_id: str
    fault_type: IndustrialFaultType
    timestamp_s: float
    duration_hours: float
    spare_parts_consumed_kg: float
    recovered_health_score: float
    success: bool
    diagnostic_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "target_robot": self.target_robot_id,
            "maintainer": self.maintainer_robot_id,
            "settlement": self.settlement_id,
            "fault": self.fault_type.value,
            "timestamp_s": round(self.timestamp_s, 1),
            "duration_h": round(self.duration_hours, 1),
            "spares_kg": round(self.spare_parts_consumed_kg, 1),
            "recovered_health": round(self.recovered_health_score * 100.0, 1),
            "success": self.success,
            "summary": self.diagnostic_summary,
        }


class FoundryMaintenanceCoordinator:
    """Detects equipment anomalies, coordinates maintenance rovers, and handles repairs."""

    def __init__(self, fleet: Dict[str, IndustrialRobot], inventories: Dict[str, SettlementMaterialInventory]) -> None:
        self.fleet = fleet
        self.inventories = inventories
        self.maintenance_history: List[MaintenanceActionRecord] = []
        self.active_faults: Dict[str, IndustrialFaultType] = {}
        self.action_counter = 1

    def inject_fault(
        self,
        target_robot_id: str,
        fault: IndustrialFaultType,
    ) -> None:
        """Simulates an equipment breakdown or mechanical degradation."""
        robot = self.fleet.get(target_robot_id)
        if not robot:
            raise ValueError(f"Robot {target_robot_id} not found in fleet")

        robot.active_fault = fault.value
        robot.state = RobotOperatingState.FAULT_ISOLATED
        robot.health_score = max(0.1, robot.health_score - 0.4)
        self.active_faults[target_robot_id] = fault

    def diagnose_and_repair(
        self,
        target_robot_id: str,
        maintainer_robot_id: str,
        current_time_s: float,
    ) -> MaintenanceActionRecord:
        """
        Dispatches a maintainer robot to inspect, clear jams, swap components,
        and recalibrate an immobilized or degraded machine.
        """
        target = self.fleet.get(target_robot_id)
        maintainer = self.fleet.get(maintainer_robot_id)
        if not target or not maintainer:
            raise ValueError("Target or maintainer robot not found")

        if not maintainer.can_perform_task(RobotClass.MAINTAINER):
            raise ValueError(f"Robot {maintainer.asset_id} is not an authorized maintenance unit")

        fault = self.active_faults.get(target_robot_id, IndustrialFaultType.EXCAVATOR_CUTTER_BLUNT)
        inv = self.inventories[maintainer.settlement_id]

        # Spare parts required (typically 15 to 35 kg of fasteners/metallic parts)
        spares_needed_kg = 25.0
        has_spares = inv.consume_stock(MaterialCategory.METALLIC_FASTENERS, spares_needed_kg)

        duration_hours = 3.5
        maintainer.consume_energy(duration_hours)

        if has_spares:
            target.active_fault = None
            target.state = RobotOperatingState.IDLE
            target.health_score = 0.95
            target.hours_since_maintenance = 0.0
            self.active_faults.pop(target_robot_id, None)
            success = True
            summary = f"Repaired {fault.value}: replaced worn actuators using {spares_needed_kg:.1f} kg replacement parts."
        else:
            success = False
            summary = f"Repair failed: insufficient spare fasteners/parts in {maintainer.settlement_id} inventory."

        rec = MaintenanceActionRecord(
            action_id=f"MNT-ACT-{self.action_counter:05d}",
            target_robot_id=target_robot_id,
            maintainer_robot_id=maintainer_robot_id,
            settlement_id=maintainer.settlement_id,
            fault_type=fault,
            timestamp_s=current_time_s,
            duration_hours=duration_hours,
            spare_parts_consumed_kg=spares_needed_kg if has_spares else 0.0,
            recovered_health_score=target.health_score,
            success=success,
            diagnostic_summary=summary,
        )
        self.action_counter += 1
        self.maintenance_history.append(rec)
        return rec
