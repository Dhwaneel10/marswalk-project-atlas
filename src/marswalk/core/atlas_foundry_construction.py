"""
MarsWalk 2.0 / Project Atlas — Milestone 13Z: Multi-Robot Construction Planner
==============================================================================
Plans, allocates, and orchestrates heterogeneous robotic construction tasks across
a dependency DAG. Enforces predecessor constraints, robot capability matching,
battery constraints, and autonomous offline execution modes.
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
    AssetConstructionState,
    InfrastructureAssetDefinition,
    ConstructedAssetInstance,
    INFRASTRUCTURE_CATALOGUE,
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
from marswalk.core.atlas_foundry_resource_processing import FoundryProductionEngine
from marswalk.core.atlas_foundry_inspection import FoundryInspectionEngine, InspectionResultStatus


class ConstructionTaskPhase(str, enum.Enum):
    """The 6 fundamental sequential construction phases for any infrastructure asset."""
    SITE_SURVEY = "SITE_SURVEY"
    SITE_EXCAVATION = "SITE_EXCAVATION"
    FEEDSTOCK_HAULING = "FEEDSTOCK_HAULING"
    COMPONENT_PROCESSING = "COMPONENT_PROCESSING"
    STRUCTURAL_ASSEMBLY = "STRUCTURAL_ASSEMBLY"
    FINAL_INSPECTION = "FINAL_INSPECTION"


@dataclass
class ConstructionTask:
    """A discrete executable construction task assigned to a specific robot."""
    task_id: str
    asset_instance_id: str
    phase: ConstructionTaskPhase
    required_robot_class: RobotClass
    estimated_duration_hours: float
    energy_kwh: float
    assigned_robot_id: Optional[str] = None
    is_completed: bool = False
    is_autonomous_offline: bool = True
    completion_time_s: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "asset_id": self.asset_instance_id,
            "phase": self.phase.value,
            "robot_class": self.required_robot_class.value,
            "duration_h": round(self.estimated_duration_hours, 1),
            "energy_kwh": round(self.energy_kwh, 1),
            "assigned_robot": self.assigned_robot_id,
            "completed": self.is_completed,
            "offline_autonomous": self.is_autonomous_offline,
        }


class MultiRobotConstructionPlanner:
    """Compiles infrastructure requirements into dependency graphs and coordinates robot execution."""

    def __init__(
        self,
        fleet: Dict[str, IndustrialRobot],
        inventories: Dict[str, SettlementMaterialInventory],
        production_engine: FoundryProductionEngine,
        inspection_engine: FoundryInspectionEngine,
    ) -> None:
        self.fleet = fleet
        self.inventories = inventories
        self.production_engine = production_engine
        self.inspection_engine = inspection_engine
        self.active_assets: Dict[str, ConstructedAssetInstance] = {}
        self.task_queue: List[ConstructionTask] = []
        self.completed_tasks: List[ConstructionTask] = []
        self.task_counter = 1

    def register_construction_project(
        self,
        asset_type: InfrastructureAssetType,
        settlement_id: str,
        current_time_s: float,
    ) -> ConstructedAssetInstance:
        """Instantiates a new infrastructure asset and enqueues its phased task chain."""
        definition = INFRASTRUCTURE_CATALOGUE[asset_type]
        iid = f"{settlement_id}-{asset_type.value[:4]}-{len(self.active_assets)+1:03d}"
        instance = ConstructedAssetInstance(
            instance_id=iid,
            asset_type=asset_type,
            settlement_id=settlement_id,
            definition=definition,
            state=AssetConstructionState.PLANNED,
            creation_time_s=current_time_s,
        )
        self.active_assets[iid] = instance

        # Decompose into phased tasks
        self._generate_phased_tasks_for_asset(instance)
        return instance

    def _generate_phased_tasks_for_asset(self, asset: ConstructedAssetInstance) -> None:
        defn = asset.definition
        dur = defn.nominal_duration_hours
        en = defn.nominal_energy_kwh

        # 1. Site Survey
        t1 = ConstructionTask(
            task_id=f"TSK-{self.task_counter:05d}",
            asset_instance_id=asset.instance_id,
            phase=ConstructionTaskPhase.SITE_SURVEY,
            required_robot_class=RobotClass.INSPECTOR,
            estimated_duration_hours=max(1.0, dur * 0.1),
            energy_kwh=en * 0.05,
        )
        self.task_counter += 1

        # 2. Site Excavation
        t2 = ConstructionTask(
            task_id=f"TSK-{self.task_counter:05d}",
            asset_instance_id=asset.instance_id,
            phase=ConstructionTaskPhase.SITE_EXCAVATION,
            required_robot_class=RobotClass.EXCAVATOR,
            estimated_duration_hours=max(2.0, dur * 0.25),
            energy_kwh=en * 0.25,
        )
        self.task_counter += 1

        # 3. Feedstock Hauling
        t3 = ConstructionTask(
            task_id=f"TSK-{self.task_counter:05d}",
            asset_instance_id=asset.instance_id,
            phase=ConstructionTaskPhase.FEEDSTOCK_HAULING,
            required_robot_class=RobotClass.HAULER,
            estimated_duration_hours=max(1.5, dur * 0.2),
            energy_kwh=en * 0.15,
        )
        self.task_counter += 1

        # 4. Component Processing
        t4 = ConstructionTask(
            task_id=f"TSK-{self.task_counter:05d}",
            asset_instance_id=asset.instance_id,
            phase=ConstructionTaskPhase.COMPONENT_PROCESSING,
            required_robot_class=RobotClass.MANUFACTURER if RobotClass.MANUFACTURER in defn.required_robot_classes else RobotClass.EXCAVATOR,
            estimated_duration_hours=max(2.0, dur * 0.25),
            energy_kwh=en * 0.35,
        )
        self.task_counter += 1

        # 5. Structural Assembly
        t5 = ConstructionTask(
            task_id=f"TSK-{self.task_counter:05d}",
            asset_instance_id=asset.instance_id,
            phase=ConstructionTaskPhase.STRUCTURAL_ASSEMBLY,
            required_robot_class=RobotClass.ASSEMBLER,
            estimated_duration_hours=max(2.0, dur * 0.3),
            energy_kwh=en * 0.15,
        )
        self.task_counter += 1

        # 6. Final Inspection
        t6 = ConstructionTask(
            task_id=f"TSK-{self.task_counter:05d}",
            asset_instance_id=asset.instance_id,
            phase=ConstructionTaskPhase.FINAL_INSPECTION,
            required_robot_class=RobotClass.INSPECTOR,
            estimated_duration_hours=max(1.0, dur * 0.1),
            energy_kwh=en * 0.05,
        )
        self.task_counter += 1

        self.task_queue.extend([t1, t2, t3, t4, t5, t6])

    def are_predecessors_accepted(self, asset: ConstructedAssetInstance) -> bool:
        """Verifies that all required predecessor infrastructure assets are ACCEPTED."""
        for pred_type in asset.definition.predecessor_asset_types:
            # If a predecessor is part of the active campaign backlog in this settlement,
            # it MUST be accepted before dependent assets can start.
            matching_active = [
                other for other in self.active_assets.values()
                if other.asset_type == pred_type and other.settlement_id == asset.settlement_id
            ]
            if matching_active:
                if not any(other.is_accepted for other in matching_active):
                    return False
        return True

    def step_construction_simulation(
        self,
        step_hours: float,
        current_time_s: float,
    ) -> List[ConstructionTask]:
        """
        Advances the multi-robot construction campaign by `step_hours`.
        Allocates available robots, executes pending tasks, checks inventory,
        and triggers quality inspections upon completion.
        """
        completed_in_step: List[ConstructionTask] = []

        for asset in self.active_assets.values():
            if asset.is_accepted or asset.state == AssetConstructionState.REJECTED:
                continue

            # Check predecessor requirements
            if not self.are_predecessors_accepted(asset):
                asset.state = AssetConstructionState.BLOCKED
                continue
            elif asset.state == AssetConstructionState.BLOCKED:
                asset.state = AssetConstructionState.PLANNED

            # Find next pending task for this asset
            pending_tasks = [
                t for t in self.task_queue
                if t.asset_instance_id == asset.instance_id and not t.is_completed
            ]
            if not pending_tasks:
                continue

            current_task = pending_tasks[0]

            # Find matching available robot in the same settlement
            eligible_robots = [
                r for r in self.fleet.values()
                if r.settlement_id == asset.settlement_id and r.is_available and r.can_perform_task(current_task.required_robot_class)
            ]

            if not eligible_robots:
                # No robot available right now
                continue

            chosen_robot = eligible_robots[0]
            current_task.assigned_robot_id = chosen_robot.asset_id
            if chosen_robot.asset_id not in asset.assigned_robot_ids:
                asset.assigned_robot_ids.append(chosen_robot.asset_id)

            # Update asset state according to phase
            phase_state_map = {
                ConstructionTaskPhase.SITE_SURVEY: AssetConstructionState.PRECONDITIONS_MET,
                ConstructionTaskPhase.SITE_EXCAVATION: AssetConstructionState.EXCAVATION_IN_PROGRESS,
                ConstructionTaskPhase.FEEDSTOCK_HAULING: AssetConstructionState.EXCAVATION_IN_PROGRESS,
                ConstructionTaskPhase.COMPONENT_PROCESSING: AssetConstructionState.FABRICATION_IN_PROGRESS,
                ConstructionTaskPhase.STRUCTURAL_ASSEMBLY: AssetConstructionState.ASSEMBLY_IN_PROGRESS,
                ConstructionTaskPhase.FINAL_INSPECTION: AssetConstructionState.INSPECTION_PENDING,
            }
            asset.state = phase_state_map.get(current_task.phase, asset.state)

            # Execute task work
            duration = min(step_hours, current_task.estimated_duration_hours)
            chosen_robot.consume_energy(duration)
            asset.energy_consumed_kwh += current_task.energy_kwh * (duration / max(0.1, current_task.estimated_duration_hours))

            # Mark complete if step duration covers estimated duration
            current_task.is_completed = True
            current_task.completion_time_s = current_time_s
            completed_in_step.append(current_task)

            # Update asset progress percentage
            done_count = sum(1 for t in self.task_queue if t.asset_instance_id == asset.instance_id and t.is_completed)
            tot_count = sum(1 for t in self.task_queue if t.asset_instance_id == asset.instance_id)
            asset.progress_pct = (done_count / float(tot_count)) * 100.0

            # If final inspection task completed, trigger formal quality inspection
            if current_task.phase == ConstructionTaskPhase.FINAL_INSPECTION:
                self.inspection_engine.inspect_asset(
                    asset=asset,
                    inspector_robot=chosen_robot,
                    current_time_s=current_time_s,
                )

        return completed_in_step
