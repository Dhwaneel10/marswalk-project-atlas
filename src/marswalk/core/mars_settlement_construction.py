"""MarsWalk 2.0 / Project Atlas  Milestone 13S: Autonomous Robotic Construction Engine.

Schedules and coordinates heterogeneous robotic construction fleets (excavators,
haulers, cranes, aerial scouts) across 15 phased infrastructure operations while
enforcing Milestone 13O deep space delay and stale-state execution guards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ConstructionAssetType(str, Enum):
    """Specialized robotic machinery deployed for surface infrastructure assembly."""
    EXCAVATION_ROVER = "EXCAVATION_ROVER"        # Continuous bucket wheel & regolith blade
    HEAVY_HAULER = "HEAVY_HAULER"                # Multi-wheel flatbed logistics hauler
    CONSTRUCTION_ROBOT = "CONSTRUCTION_ROBOT"    # Dexterous dual-arm manipulator & welder
    MOBILE_GANTRY_CRANE = "MOBILE_GANTRY_CRANE"  # Heavy module unloader & structural placer
    AERIAL_SCOUT = "AERIAL_SCOUT"                # Rotorcraft photogrammetry & survey
    UTILITY_TRENCHER = "UTILITY_TRENCHER"        # Cable plow and fluid pipe layer
    INSPECTION_ROVER = "INSPECTION_ROVER"        # LiDAR and ultrasonic weld verifier


class OperationStatus(str, Enum):
    """Lifecycle status of a construction task."""
    PENDING = "PENDING"
    PRECONDITIONS_MET = "PRECONDITIONS_MET"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED_BY_DEPENDENCY = "BLOCKED_BY_DEPENDENCY"
    STALE_COMMAND_REJECTED = "STALE_COMMAND_REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ConstructionOperation:
    """An individual sequential or parallel construction activity."""
    op_id: str
    name: str
    phase: str                               # "PHASE_A", "PHASE_B", "PHASE_C", "PHASE_D"
    assigned_asset_type: ConstructionAssetType
    preceding_ops: List[str]                 # IDs of operations that must be COMPLETED
    duration_hours: float
    energy_demand_kwh: float
    materials_required_kg: float
    status: OperationStatus = OperationStatus.PENDING
    progress_pct: float = 0.0
    completion_evidence_hash: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "op_id": self.op_id,
            "name": self.name,
            "phase": self.phase,
            "assigned_asset_type": self.assigned_asset_type.value,
            "preceding_ops": self.preceding_ops,
            "duration_hours": round(self.duration_hours, 1),
            "energy_demand_kwh": round(self.energy_demand_kwh, 1),
            "materials_required_kg": round(self.materials_required_kg, 1),
            "status": self.status.value,
            "progress_pct": round(self.progress_pct, 1),
            "completion_evidence_hash": self.completion_evidence_hash,
            "description": self.description,
        }


class AutonomousConstructionDirector:
    """Coordinates the 15-stage planetary infrastructure assembly sequence."""

    def __init__(self):
        self._operations: Dict[str, ConstructionOperation] = self._build_canonical_15_operations()
        self._completed_hashes: Set[str] = set()

    def get_operations(self) -> List[ConstructionOperation]:
        return list(self._operations.values())

    def get_operation(self, op_id: str) -> Optional[ConstructionOperation]:
        return self._operations.get(op_id)

    def evaluate_schedule(self, current_sol: int = 1) -> Dict[str, Any]:
        """Evaluates preconditions and identifies ready tasks."""
        ready_tasks = []
        blocked_tasks = []
        completed_tasks = []

        for op in self._operations.values():
            if op.status == OperationStatus.COMPLETED:
                completed_tasks.append(op.op_id)
                continue

            # Check prerequisites
            all_precedents_done = True
            for req in op.preceding_ops:
                if self._operations[req].status != OperationStatus.COMPLETED:
                    all_precedents_done = False
                    break

            if all_precedents_done:
                op.status = OperationStatus.PRECONDITIONS_MET
                ready_tasks.append(op.op_id)
            else:
                op.status = OperationStatus.BLOCKED_BY_DEPENDENCY
                blocked_tasks.append(op.op_id)

        return {
            "current_sol": current_sol,
            "total_operations": len(self._operations),
            "completed_count": len(completed_tasks),
            "ready_count": len(ready_tasks),
            "blocked_count": len(blocked_tasks),
            "ready_operations": ready_tasks,
        }

    def execute_operation_step(
        self,
        op_id: str,
        execution_timestamp_s: float,
        command_dispatch_timestamp_s: float,
        max_allowable_delay_s: float = 1200.0, # 20 minutes max delay for stale check
    ) -> Dict[str, Any]:
        """Executes task progress while validating against Milestone 13O stale commands."""
        op = self._operations.get(op_id)
        if not op:
            raise ValueError(f"Operation '{op_id}' not found.")

        # Stale instruction verification
        delay = execution_timestamp_s - command_dispatch_timestamp_s
        if delay > max_allowable_delay_s:
            op.status = OperationStatus.STALE_COMMAND_REJECTED
            return {
                "op_id": op_id,
                "status": "REJECTED_STALE",
                "reason": f"Execution delay ({delay:.1f}s) exceeded safety window ({max_allowable_delay_s:.1f}s). Command rejected.",
            }

        # Check preconditions
        for req in op.preceding_ops:
            if self._operations[req].status != OperationStatus.COMPLETED:
                op.status = OperationStatus.BLOCKED_BY_DEPENDENCY
                return {
                    "op_id": op_id,
                    "status": "BLOCKED",
                    "reason": f"Prerequisite '{req}' is not completed.",
                }

        # Advance to completion
        op.status = OperationStatus.COMPLETED
        op.progress_pct = 100.0

        import hashlib
        h = hashlib.sha256()
        h.update(op.op_id.encode("utf-8"))
        h.update(str(execution_timestamp_s).encode("utf-8"))
        op.completion_evidence_hash = h.hexdigest()[:16].upper()
        self._completed_hashes.add(op.completion_evidence_hash)

        return {
            "op_id": op_id,
            "status": "COMPLETED",
            "progress_pct": 100.0,
            "completion_evidence_hash": op.completion_evidence_hash,
            "energy_consumed_kwh": op.energy_demand_kwh,
        }

    def _build_canonical_15_operations(self) -> Dict[str, ConstructionOperation]:
        ops = [
            # Phase A: Reconnaissance
            ConstructionOperation(
                op_id="OP-01-SURVEY",
                name="Topographic & Subsurface Radar Survey",
                phase="PHASE_A",
                assigned_asset_type=ConstructionAssetType.AERIAL_SCOUT,
                preceding_ops=[],
                duration_hours=24.0,
                energy_demand_kwh=18.0,
                materials_required_kg=0.0,
                status=OperationStatus.COMPLETED, # Pre-completed in Phase A
                progress_pct=100.0,
                description="High-resolution aerial orthomosaic and RIMFAX subsurface radargrams.",
            ),
            # Phase B: Precursor Infrastructure
            ConstructionOperation(
                op_id="OP-02-PAD-GRADING",
                name="Landing Pad Grading & Rock Clearing",
                phase="PHASE_B",
                assigned_asset_type=ConstructionAssetType.EXCAVATION_ROVER,
                preceding_ops=["OP-01-SURVEY"],
                duration_hours=48.0,
                energy_demand_kwh=65.0,
                materials_required_kg=0.0,
                status=OperationStatus.PENDING,
                progress_pct=0.0,
                description="Clearing 800m radius touchdown zone to surface roughness < 0.1m.",
            ),
            ConstructionOperation(
                op_id="OP-03-BLAST-BERM",
                name="Sintered Regolith Blast Deflection Berm",
                phase="PHASE_B",
                assigned_asset_type=ConstructionAssetType.CONSTRUCTION_ROBOT,
                preceding_ops=["OP-02-PAD-GRADING"],
                duration_hours=72.0,
                energy_demand_kwh=95.0,
                materials_required_kg=4500.0,
                status=OperationStatus.PENDING,
                progress_pct=0.0,
                description="Sintering 3m high perimeter berm to protect habitats from lander ejecta.",
            ),
            ConstructionOperation(
                op_id="OP-04-COMM-MAST",
                name="High-Bandwidth Communications Mast Erection",
                phase="PHASE_B",
                assigned_asset_type=ConstructionAssetType.CONSTRUCTION_ROBOT,
                preceding_ops=["OP-01-SURVEY"],
                duration_hours=18.0,
                energy_demand_kwh=22.0,
                materials_required_kg=350.0,
                status=OperationStatus.PENDING,
                progress_pct=0.0,
                description="25m deployable composite mast with steerable DTE X-band antenna.",
            ),
            ConstructionOperation(
                op_id="OP-05-REACTOR-TRANSPORT",
                name="Nuclear Fission Reactor Transport & Standoff Emplacement",
                phase="PHASE_B",
                assigned_asset_type=ConstructionAssetType.HEAVY_HAULER,
                preceding_ops=["OP-02-PAD-GRADING"],
                duration_hours=36.0,
                energy_demand_kwh=85.0,
                materials_required_kg=4800.0,
                status=OperationStatus.PENDING,
                progress_pct=0.0,
                description="Hauling 100 kWe reactor to 1200m shielded standoff depression.",
            ),
            ConstructionOperation(
                op_id="OP-06-POWER-TRENCHING",
                name="High-Voltage Power Cable Trenching & Connection",
                phase="PHASE_B",
                assigned_asset_type=ConstructionAssetType.UTILITY_TRENCHER,
                preceding_ops=["OP-05-REACTOR-TRANSPORT"],
                duration_hours=40.0,
                energy_demand_kwh=55.0,
                materials_required_kg=1200.0,
                status=OperationStatus.PENDING,
                progress_pct=0.0,
                description="Burying 5 kV transmission line 1.2m beneath regolith to prevent thermal fatigue.",
            ),
            # Phase C: Autonomous Construction
            ConstructionOperation(
                op_id="OP-07-HAB-OFFLOAD",
                name="Inflatable Habitat Module Cargo Offloading",
                phase="PHASE_C",
                assigned_asset_type=ConstructionAssetType.MOBILE_GANTRY_CRANE,
                preceding_ops=["OP-03-BLAST-BERM", "OP-06-POWER-TRENCHING"],
                duration_hours=16.0,
                energy_demand_kwh=35.0,
                materials_required_kg=12500.0,
                status=OperationStatus.PENDING,
                progress_pct=0.0,
                description="Offloading primary crew habitat shell from lander deck to transport bogie.",
            ),
            ConstructionOperation(
                op_id="OP-08-HAB-EXPANSION",
                name="Habitat Module Pneumatic Expansion & Seal Rigidization",
                phase="PHASE_C",
                assigned_asset_type=ConstructionAssetType.CONSTRUCTION_ROBOT,
                preceding_ops=["OP-07-HAB-OFFLOAD"],
                duration_hours=24.0,
                energy_demand_kwh=45.0,
                materials_required_kg=0.0,
                status=OperationStatus.PENDING,
                progress_pct=0.0,
                description="Pneumatic expansion to 56.5 kPa with thermoset resin curing.",
            ),
            ConstructionOperation(
                op_id="OP-09-REGOLITH-VAULT",
                name="Sintered Regolith Radiation Vault Arch Placement",
                phase="PHASE_C",
                assigned_asset_type=ConstructionAssetType.MOBILE_GANTRY_CRANE,
                preceding_ops=["OP-08-HAB-EXPANSION"],
                duration_hours=120.0,
                energy_demand_kwh=160.0,
                materials_required_kg=18500.0,
                status=OperationStatus.PENDING,
                progress_pct=0.0,
                description="Assembling interlocking sintered regolith blocks over habitat roof.",
            ),
            ConstructionOperation(
                op_id="OP-10-UTILITY-HOOKUP",
                name="Habitat Internal Power & Thermal Fluid Hookup",
                phase="PHASE_C",
                assigned_asset_type=ConstructionAssetType.CONSTRUCTION_ROBOT,
                preceding_ops=["OP-09-REGOLITH-VAULT", "OP-06-POWER-TRENCHING"],
                duration_hours=30.0,
                energy_demand_kwh=40.0,
                materials_required_kg=250.0,
                status=OperationStatus.PENDING,
                progress_pct=0.0,
                description="Connecting 28V DC bus and ammonia/water loop heat exchanger.",
            ),
            ConstructionOperation(
                op_id="OP-11-ISRU-WATER-DEPLOY",
                name="Subsurface Water Extraction Plant Deployment",
                phase="PHASE_C",
                assigned_asset_type=ConstructionAssetType.HEAVY_HAULER,
                preceding_ops=["OP-06-POWER-TRENCHING"],
                duration_hours=48.0,
                energy_demand_kwh=75.0,
                materials_required_kg=3500.0,
                status=OperationStatus.PENDING,
                progress_pct=0.0,
                description="Positioning thermal auger excavation reactors on clay deposit.",
            ),
            ConstructionOperation(
                op_id="OP-12-ISRU-O2-DEPLOY",
                name="Atmospheric CO2 to O2 Processing Plant Setup",
                phase="PHASE_C",
                assigned_asset_type=ConstructionAssetType.CONSTRUCTION_ROBOT,
                preceding_ops=["OP-11-ISRU-WATER-DEPLOY"],
                duration_hours=36.0,
                energy_demand_kwh=60.0,
                materials_required_kg=2800.0,
                status=OperationStatus.PENDING,
                progress_pct=0.0,
                description="Piping connections between Sabatier unit, electrolysis, and O2 storage dewars.",
            ),
            # Phase D: Commissioning
            ConstructionOperation(
                op_id="OP-13-THERMAL-VERIFY",
                name="Habitat Active Thermal Loop 24-Hour Cold-Soak Trial",
                phase="PHASE_D",
                assigned_asset_type=ConstructionAssetType.INSPECTION_ROVER,
                preceding_ops=["OP-10-UTILITY-HOOKUP"],
                duration_hours=24.6, # One full sol
                energy_demand_kwh=120.0,
                materials_required_kg=0.0,
                status=OperationStatus.PENDING,
                progress_pct=0.0,
                description="Verifying internal temperature stays at 21C during -88C night minimum.",
            ),
            ConstructionOperation(
                op_id="OP-14-ISRU-COMMISSION",
                name="ISRU Continuous Commodity Production Verification",
                phase="PHASE_D",
                assigned_asset_type=ConstructionAssetType.INSPECTION_ROVER,
                preceding_ops=["OP-11-ISRU-WATER-DEPLOY", "OP-12-ISRU-O2-DEPLOY"],
                duration_hours=48.0,
                energy_demand_kwh=180.0,
                materials_required_kg=0.0,
                status=OperationStatus.PENDING,
                progress_pct=0.0,
                description="Producing 100 kg potable water and 35 kg liquid oxygen trial batch.",
            ),
            ConstructionOperation(
                op_id="OP-15-TOTAL-COMMISSION",
                name="Full Settlement Integrated Commissioning Gate",
                phase="PHASE_D",
                assigned_asset_type=ConstructionAssetType.INSPECTION_ROVER,
                preceding_ops=["OP-13-THERMAL-VERIFY", "OP-14-ISRU-COMMISSION"],
                duration_hours=24.0,
                energy_demand_kwh=90.0,
                materials_required_kg=0.0,
                status=OperationStatus.PENDING,
                progress_pct=0.0,
                description="Autonomous qualification of life support, power balance, and telecommunications.",
            ),
        ]
        return {op.op_id: op for op in ops}
