"""
MarsWalk 2.0 / Project Atlas — Milestone 13Z: Quality, Inspection & Acceptance Engine
=====================================================================================
Rigorous quality assurance, non-destructive testing, and formal acceptance engine
for constructed Martian infrastructure. Enforces dimensional tolerance, compressive
strength proxies, surface roughness thresholds, and non-silent rework tracking.
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
import enum
import math
import random
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.atlas_foundry_structures import (
    ConstructedAssetInstance,
    AssetConstructionState,
    InfrastructureAssetDefinition,
)
from marswalk.core.atlas_foundry_robotics import IndustrialRobot, RobotClass


class InspectionResultStatus(str, enum.Enum):
    """Formal qualification verdicts."""
    ACCEPTED_PASSED = "ACCEPTED_PASSED"              # Meets all structural & dimensional criteria
    REWORK_REQUIRED = "REWORK_REQUIRED"              # Minor planarity or surface defect; remediable
    REJECTED_FAILED = "REJECTED_FAILED"              # Critical structural integrity or material failure


@dataclass
class InspectionReport:
    """An official engineering inspection certificate for an infrastructure asset."""
    report_id: str
    asset_instance_id: str
    asset_type: str
    settlement_id: str
    inspector_robot_id: str
    timestamp_s: float
    verdict: InspectionResultStatus
    measured_compressive_strength_mpa: float
    required_compressive_strength_mpa: float
    measured_surface_roughness_cm: float
    max_tolerated_roughness_cm: float
    density_porosity_compliance_pct: float
    defect_notes: str
    rework_action_recommended: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "asset_id": self.asset_instance_id,
            "asset_type": self.asset_type,
            "settlement": self.settlement_id,
            "inspector": self.inspector_robot_id,
            "timestamp_s": round(self.timestamp_s, 1),
            "verdict": self.verdict.value,
            "compressive_strength_mpa": round(self.measured_compressive_strength_mpa, 2),
            "required_strength_mpa": round(self.required_compressive_strength_mpa, 2),
            "surface_roughness_cm": round(self.measured_surface_roughness_cm, 2),
            "max_roughness_cm": round(self.max_tolerated_roughness_cm, 2),
            "density_pct": round(self.density_porosity_compliance_pct, 1),
            "defects": self.defect_notes,
            "rework_action": self.rework_action_recommended,
        }


class FoundryInspectionEngine:
    """Evaluates physical compliance and issues authoritative acceptance or rework verdicts."""

    def __init__(self, random_seed: int = 42) -> None:
        self.rng = random.Random(random_seed)
        self.inspection_reports: List[InspectionReport] = []
        self.report_counter = 1

    def inspect_asset(
        self,
        asset: ConstructedAssetInstance,
        inspector_robot: IndustrialRobot,
        current_time_s: float,
        simulated_defect_rate: float = 0.05,
    ) -> InspectionReport:
        """
        Executes comprehensive LiDAR geometry and non-destructive material evaluation.
        Updates the asset's lifecycle state: ACCEPTED, REWORK_REQUIRED, or REJECTED.
        """
        if not inspector_robot.can_perform_task(RobotClass.INSPECTOR):
            raise ValueError(f"Robot {inspector_robot.asset_id} is not an certified inspection unit")

        definition = asset.definition
        # Duration ~ 2 hours for inspection
        inspector_robot.consume_energy(2.0)

        # Baseline compliance calculations with controlled stochastic perturbation
        perturb = (self.rng.random() - 0.5) * 2.0 * simulated_defect_rate
        measured_strength = definition.min_compressive_strength_mpa * (1.05 + perturb)
        measured_roughness = definition.max_tolerated_surface_roughness_cm * (0.85 - perturb)
        density_compliance = max(75.0, min(100.0, 96.0 + perturb * 20.0))

        # Explicit failure triggers
        strength_passed = measured_strength >= definition.min_compressive_strength_mpa
        roughness_passed = measured_roughness <= definition.max_tolerated_surface_roughness_cm

        if strength_passed and roughness_passed and density_compliance >= 90.0:
            verdict = InspectionResultStatus.ACCEPTED_PASSED
            asset.state = AssetConstructionState.ACCEPTED
            asset.completion_time_s = current_time_s
            defects = "All geometric tolerances and compressive strength requirements verified compliant."
            rework = None
        elif measured_strength >= (definition.min_compressive_strength_mpa * 0.75):
            verdict = InspectionResultStatus.REWORK_REQUIRED
            asset.state = AssetConstructionState.REWORK_REQUIRED
            asset.rework_count += 1
            defects = (
                f"Surface planarity or density defect: roughness {measured_roughness:.2f} cm "
                f"(max {definition.max_tolerated_surface_roughness_cm:.2f} cm)."
            )
            rework = "Re-sinter surface layer or execute supplemental compaction pass."
        else:
            verdict = InspectionResultStatus.REJECTED_FAILED
            asset.state = AssetConstructionState.REJECTED
            defects = (
                f"Severe structural failure: strength {measured_strength:.2f} MPa below minimum "
                f"threshold {definition.min_compressive_strength_mpa:.2f} MPa."
            )
            rework = "Demolition required; rebuild with verified feedstock batch."

        asset.measured_compressive_strength_mpa = measured_strength
        asset.measured_surface_roughness_cm = measured_roughness
        asset.inspection_notes = defects

        rep = InspectionReport(
            report_id=f"INSP-{self.report_counter:05d}",
            asset_instance_id=asset.instance_id,
            asset_type=asset.asset_type.value,
            settlement_id=asset.settlement_id,
            inspector_robot_id=inspector_robot.asset_id,
            timestamp_s=current_time_s,
            verdict=verdict,
            measured_compressive_strength_mpa=measured_strength,
            required_compressive_strength_mpa=definition.min_compressive_strength_mpa,
            measured_surface_roughness_cm=measured_roughness,
            max_tolerated_roughness_cm=definition.max_tolerated_surface_roughness_cm,
            density_porosity_compliance_pct=density_compliance,
            defect_notes=defects,
            rework_action_recommended=rework,
        )
        self.report_counter += 1
        self.inspection_reports.append(rep)
        return rep
