"""
MarsWalk 2.0 / Project Atlas — Milestone 13Z: Robotic Industrial Fleet
======================================================================
Defines heterogeneous industrial robotic machinery classes, kinematics/payload constraints,
power consumption, maintenance states, and capability-matching logic for Martian construction.
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
import enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class RobotClass(str, enum.Enum):
    """Specialized classifications of autonomous industrial surface machinery."""
    EXCAVATOR = "EXCAVATOR"          # Regolith excavation, trenching, site grading
    HAULER = "HAULER"                # Bulk raw regolith and fabricated block transportation
    MANUFACTURER = "MANUFACTURER"    # Microwave/laser sintering, 3D additive extrusion, geopolymer mixer
    ASSEMBLER = "ASSEMBLER"          # Heavy gantry placement, precision truss alignment, fastener bolting
    INSPECTOR = "INSPECTOR"          # LiDAR geometry check, ultrasonic weld inspection, density scanning
    MAINTAINER = "MAINTAINER"        # Preventive servicing, component replacement, tool clearing


class RobotOperatingState(str, enum.Enum):
    """Operational lifecycle state of an industrial robot asset."""
    IDLE = "IDLE"
    EN_ROUTE = "EN_ROUTE"
    EXCAVATING = "EXCAVATING"
    HAULING = "HAULING"
    MANUFACTURING = "MANUFACTURING"
    ASSEMBLING = "ASSEMBLING"
    INSPECTING = "INSPECTING"
    MAINTAINING = "MAINTAINING"
    CHARGING = "CHARGING"
    FAULT_ISOLATED = "FAULT_ISOLATED"


@dataclass
class IndustrialRobot:
    """An autonomous robotic machine operating within a Martian settlement foundry."""
    asset_id: str
    name: str
    robot_class: RobotClass
    settlement_id: str
    max_payload_kg: float
    nominal_power_kw: float
    battery_capacity_kwh: float
    current_battery_kwh: float
    speed_km_h: float
    reach_radius_m: float = 3.0
    state: RobotOperatingState = RobotOperatingState.IDLE
    current_task_id: Optional[str] = None
    hours_since_maintenance: float = 0.0
    maintenance_interval_hours: float = 120.0
    health_score: float = 1.0                  # 0.0 (destroyed) to 1.0 (pristine)
    active_fault: Optional[str] = None
    cumulative_operating_hours: float = 0.0
    cumulative_energy_spent_kwh: float = 0.0
    location_coords: Tuple[float, float] = (0.0, 0.0)

    @property
    def battery_pct(self) -> float:
        if self.battery_capacity_kwh <= 0:
            return 0.0
        return min(100.0, max(0.0, (self.current_battery_kwh / self.battery_capacity_kwh) * 100.0))

    @property
    def is_available(self) -> bool:
        return (
            self.state == RobotOperatingState.IDLE
            and self.active_fault is None
            and self.battery_pct > 15.0
            and self.health_score > 0.3
        )

    def can_perform_task(self, required_class: RobotClass, payload_kg: float = 0.0) -> bool:
        """Enforces physical and architectural capability matching."""
        if self.robot_class != required_class:
            return False
        if payload_kg > self.max_payload_kg:
            return False
        if self.active_fault is not None:
            return False
        return True

    def consume_energy(self, duration_hours: float, power_multiplier: float = 1.0) -> float:
        """Deducts energy from battery based on operational duration and power draw."""
        draw_kwh = self.nominal_power_kw * power_multiplier * duration_hours
        actual_draw = min(self.current_battery_kwh, draw_kwh)
        self.current_battery_kwh -= actual_draw
        self.cumulative_energy_spent_kwh += actual_draw
        self.cumulative_operating_hours += duration_hours
        self.hours_since_maintenance += duration_hours
        if self.hours_since_maintenance > self.maintenance_interval_hours:
            # Degradation due to deferred maintenance
            degrade = 0.005 * (self.hours_since_maintenance - self.maintenance_interval_hours)
            self.health_score = max(0.2, self.health_score - degrade)
        return actual_draw

    def recharge(self, energy_kwh: float) -> float:
        """Adds electrical energy up to battery capacity."""
        room = self.battery_capacity_kwh - self.current_battery_kwh
        added = min(room, max(0.0, energy_kwh))
        self.current_battery_kwh += added
        if self.current_battery_kwh >= self.battery_capacity_kwh * 0.95 and self.state == RobotOperatingState.CHARGING:
            self.state = RobotOperatingState.IDLE
        return added

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "class": self.robot_class.value,
            "settlement": self.settlement_id,
            "max_payload_kg": round(self.max_payload_kg, 1),
            "battery_pct": round(self.battery_pct, 1),
            "state": self.state.value,
            "current_task": self.current_task_id,
            "health_pct": round(self.health_score * 100.0, 1),
            "hours_since_maint": round(self.hours_since_maintenance, 1),
            "is_available": self.is_available,
            "active_fault": self.active_fault,
        }


def create_standard_industrial_fleet() -> Dict[str, IndustrialRobot]:
    """
    Constructs the canonical 18-robot industrial fleet distributed across the three settlements:
    - Mars Base Alpha (Jezero): 8 robots (Primary industrial hub)
    - Outpost Beta (Nili Fossae): 5 robots (Regional science/quarry)
    - Outpost Gamma (Syrtis Major): 5 robots (Heavy mining & sintering)
    """
    fleet: Dict[str, IndustrialRobot] = {}

    # === MARS BASE ALPHA (Jezero Crater) ===
    fleet["ROB-ALPHA-EXC-01"] = IndustrialRobot(
        asset_id="ROB-ALPHA-EXC-01", name="Alpha Heavy Bucket-Wheel Excavator",
        robot_class=RobotClass.EXCAVATOR, settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=500.0, nominal_power_kw=4.5, battery_capacity_kwh=50.0, current_battery_kwh=50.0, speed_km_h=4.0
    )
    fleet["ROB-ALPHA-HAU-01"] = IndustrialRobot(
        asset_id="ROB-ALPHA-HAU-01", name="Alpha High-Capacity Regolith Hauler 1",
        robot_class=RobotClass.HAULER, settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=1500.0, nominal_power_kw=2.5, battery_capacity_kwh=65.0, current_battery_kwh=65.0, speed_km_h=7.0
    )
    fleet["ROB-ALPHA-HAU-02"] = IndustrialRobot(
        asset_id="ROB-ALPHA-HAU-02", name="Alpha High-Capacity Regolith Hauler 2",
        robot_class=RobotClass.HAULER, settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=1500.0, nominal_power_kw=2.5, battery_capacity_kwh=65.0, current_battery_kwh=65.0, speed_km_h=7.0
    )
    fleet["ROB-ALPHA-MFG-01"] = IndustrialRobot(
        asset_id="ROB-ALPHA-MFG-01", name="Alpha Microwave Sintering 3D Builder",
        robot_class=RobotClass.MANUFACTURER, settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=800.0, nominal_power_kw=8.0, battery_capacity_kwh=85.0, current_battery_kwh=85.0, speed_km_h=2.0
    )
    fleet["ROB-ALPHA-ASM-01"] = IndustrialRobot(
        asset_id="ROB-ALPHA-ASM-01", name="Alpha Dual-Arm Gantry Assembler",
        robot_class=RobotClass.ASSEMBLER, settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=3000.0, nominal_power_kw=3.0, battery_capacity_kwh=55.0, current_battery_kwh=55.0, speed_km_h=3.5, reach_radius_m=8.0
    )
    fleet["ROB-ALPHA-ASM-02"] = IndustrialRobot(
        asset_id="ROB-ALPHA-ASM-02", name="Alpha Precision Fastener Bolter",
        robot_class=RobotClass.ASSEMBLER, settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=500.0, nominal_power_kw=2.0, battery_capacity_kwh=40.0, current_battery_kwh=40.0, speed_km_h=4.5, reach_radius_m=3.5
    )
    fleet["ROB-ALPHA-INS-01"] = IndustrialRobot(
        asset_id="ROB-ALPHA-INS-01", name="Alpha LiDAR & Ultrasonic Quality Inspector",
        robot_class=RobotClass.INSPECTOR, settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=50.0, nominal_power_kw=0.8, battery_capacity_kwh=25.0, current_battery_kwh=25.0, speed_km_h=6.0
    )
    fleet["ROB-ALPHA-MNT-01"] = IndustrialRobot(
        asset_id="ROB-ALPHA-MNT-01", name="Alpha Autonomous Fleet Maintenance Technician",
        robot_class=RobotClass.MAINTAINER, settlement_id="SETTLEMENT-ALPHA",
        max_payload_kg=400.0, nominal_power_kw=1.8, battery_capacity_kwh=45.0, current_battery_kwh=45.0, speed_km_h=5.0
    )

    # === MARS OUTPOST BETA (Nili Fossae) ===
    fleet["ROB-BETA-EXC-01"] = IndustrialRobot(
        asset_id="ROB-BETA-EXC-01", name="Beta Compact Quarry Excavator",
        robot_class=RobotClass.EXCAVATOR, settlement_id="OUTPOST-BETA",
        max_payload_kg=350.0, nominal_power_kw=3.8, battery_capacity_kwh=45.0, current_battery_kwh=45.0, speed_km_h=4.0
    )
    fleet["ROB-BETA-HAU-01"] = IndustrialRobot(
        asset_id="ROB-BETA-HAU-01", name="Beta All-Terrain Feedstock Hauler",
        robot_class=RobotClass.HAULER, settlement_id="OUTPOST-BETA",
        max_payload_kg=1200.0, nominal_power_kw=2.2, battery_capacity_kwh=55.0, current_battery_kwh=55.0, speed_km_h=6.5
    )
    fleet["ROB-BETA-MFG-01"] = IndustrialRobot(
        asset_id="ROB-BETA-MFG-01", name="Beta Geopolymer Composite Concrete Mixer",
        robot_class=RobotClass.MANUFACTURER, settlement_id="OUTPOST-BETA",
        max_payload_kg=600.0, nominal_power_kw=6.5, battery_capacity_kwh=70.0, current_battery_kwh=70.0, speed_km_h=2.5
    )
    fleet["ROB-BETA-ASM-01"] = IndustrialRobot(
        asset_id="ROB-BETA-ASM-01", name="Beta Structural Assembly Crane",
        robot_class=RobotClass.ASSEMBLER, settlement_id="OUTPOST-BETA",
        max_payload_kg=2200.0, nominal_power_kw=2.8, battery_capacity_kwh=50.0, current_battery_kwh=50.0, speed_km_h=3.5, reach_radius_m=6.5
    )
    fleet["ROB-BETA-INS-01"] = IndustrialRobot(
        asset_id="ROB-BETA-INS-01", name="Beta Surface Photogrammetry Inspector",
        robot_class=RobotClass.INSPECTOR, settlement_id="OUTPOST-BETA",
        max_payload_kg=40.0, nominal_power_kw=0.7, battery_capacity_kwh=20.0, current_battery_kwh=20.0, speed_km_h=7.0
    )

    # === MARS RESOURCE OUTPOST GAMMA (Syrtis Major) ===
    fleet["ROB-GAMMA-EXC-01"] = IndustrialRobot(
        asset_id="ROB-GAMMA-EXC-01", name="Gamma Deep-Trench Mining Excavator",
        robot_class=RobotClass.EXCAVATOR, settlement_id="OUTPOST-GAMMA",
        max_payload_kg=600.0, nominal_power_kw=5.2, battery_capacity_kwh=60.0, current_battery_kwh=60.0, speed_km_h=3.5
    )
    fleet["ROB-GAMMA-HAU-01"] = IndustrialRobot(
        asset_id="ROB-GAMMA-HAU-01", name="Gamma Heavy Sintering Feedstock Hauler",
        robot_class=RobotClass.HAULER, settlement_id="OUTPOST-GAMMA",
        max_payload_kg=1800.0, nominal_power_kw=2.8, battery_capacity_kwh=70.0, current_battery_kwh=70.0, speed_km_h=6.0
    )
    fleet["ROB-GAMMA-MFG-01"] = IndustrialRobot(
        asset_id="ROB-GAMMA-MFG-01", name="Gamma Heavy Basalt Sintering Foundry",
        robot_class=RobotClass.MANUFACTURER, settlement_id="OUTPOST-GAMMA",
        max_payload_kg=1000.0, nominal_power_kw=9.5, battery_capacity_kwh=95.0, current_battery_kwh=95.0, speed_km_h=1.8
    )
    fleet["ROB-GAMMA-ASM-01"] = IndustrialRobot(
        asset_id="ROB-GAMMA-ASM-01", name="Gamma Foundation & Paving Assembler",
        robot_class=RobotClass.ASSEMBLER, settlement_id="OUTPOST-GAMMA",
        max_payload_kg=2500.0, nominal_power_kw=3.0, battery_capacity_kwh=55.0, current_battery_kwh=55.0, speed_km_h=3.2, reach_radius_m=7.0
    )
    fleet["ROB-GAMMA-MNT-01"] = IndustrialRobot(
        asset_id="ROB-GAMMA-MNT-01", name="Gamma Quarry Maintenance Rover",
        robot_class=RobotClass.MAINTAINER, settlement_id="OUTPOST-GAMMA",
        max_payload_kg=350.0, nominal_power_kw=1.6, battery_capacity_kwh=40.0, current_battery_kwh=40.0, speed_km_h=5.0
    )

    return fleet
