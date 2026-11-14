"""
MarsWalk 2.0 / Project Atlas — Milestone 13Z: Infrastructure Assets & Structures Library
========================================================================================
Comprehensive engineering catalogue of 12 unpressurized Martian surface infrastructure assets.
Defines geometric dimensions, material bills of quantities (BOQ), predecessor dependencies,
construction equipment requirements, and acceptance standards.
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
    STANDARD_MATERIAL_SPECS,
)
from marswalk.core.atlas_foundry_robotics import RobotClass


class InfrastructureAssetType(str, enum.Enum):
    """The 12 formal Milestone 13Z unpressurized surface infrastructure assets."""
    LANDING_ZONE_PREPARATION = "LANDING_ZONE_PREPARATION"          # Surface boulder clearance and coarse grading
    LANDING_PAD_SEGMENTS = "LANDING_PAD_SEGMENTS"                  # High-temperature interlocking sintered basalt pavers
    ACCESS_ROADS_MOBILITY_ROUTES = "ACCESS_ROADS_MOBILITY_ROUTES"  # Graded, compacted, and berm-flanked rover roadway
    EQUIPMENT_FOUNDATIONS = "EQUIPMENT_FOUNDATIONS"                # Precision-levelled sintered footings for reactors/tanks
    REGOLITH_BERMS_SHIELDING = "REGOLITH_BERMS_SHIELDING"          # Radiation and blast deflection earthen mass embankments
    UTILITY_TRENCHES = "UTILITY_TRENCHES"                          # Subsurface conduits protecting cables and thermal pipes
    SOLAR_ARRAY_FOUNDATIONS = "SOLAR_ARRAY_FOUNDATIONS"            # Regolith anchor blocks and structural support frames
    ANTENNA_FOUNDATIONS_MASTS = "ANTENNA_FOUNDATIONS_MASTS"        # High-gain communications tower foundations & guy anchors
    EQUIPMENT_SHELTERS = "EQUIPMENT_SHELTERS"                      # Micrometeorite and dust unpressurized arched canopy
    MODULAR_STORAGE_BAYS = "MODULAR_STORAGE_BAYS"                  # Raw and processed material storage bunker enclosures
    POWER_DISTRIBUTION_HUBS = "POWER_DISTRIBUTION_HUBS"            # Switchgear vaults, transformer pads, busbar junctions
    SURFACE_RELAY_STATIONS = "SURFACE_RELAY_STATIONS"              # Autonomous rim-mounted microwave/UHF repeater installations


class AssetConstructionState(str, enum.Enum):
    """State machine governing the construction and qualification lifecycle."""
    PLANNED = "PLANNED"                      # Registered in settlement backlog
    PRECONDITIONS_MET = "PRECONDITIONS_MET"  # Predecessor tasks and site access cleared
    EXCAVATION_IN_PROGRESS = "EXCAVATION_IN_PROGRESS"
    FABRICATION_IN_PROGRESS = "FABRICATION_IN_PROGRESS"
    ASSEMBLY_IN_PROGRESS = "ASSEMBLY_IN_PROGRESS"
    INSPECTION_PENDING = "INSPECTION_PENDING"
    ACCEPTED = "ACCEPTED"                    # Fully qualified, verified, and operational
    REWORK_REQUIRED = "REWORK_REQUIRED"      # Defect detected during inspection; awaiting remediation
    REJECTED = "REJECTED"                    # Irrecoverable structural or material failure
    BLOCKED = "BLOCKED"                      # Halted due to equipment failure, blackout, or stockout


@dataclass
class InfrastructureBillOfQuantities:
    """Explicit mass breakdown of local ISRU materials and imported components."""
    raw_regolith_feedstock_kg: float = 0.0
    screened_regolith_kg: float = 0.0
    compacted_regolith_kg: float = 0.0
    sintered_blocks_kg: float = 0.0
    geopolymer_concrete_kg: float = 0.0
    imported_structural_kg: float = 0.0
    metallic_fasteners_kg: float = 0.0
    electrical_thermal_kg: float = 0.0

    @property
    def total_isru_mass_kg(self) -> float:
        return (
            self.raw_regolith_feedstock_kg
            + self.screened_regolith_kg
            + self.compacted_regolith_kg
            + self.sintered_blocks_kg
            + self.geopolymer_concrete_kg
        )

    @property
    def total_imported_mass_kg(self) -> float:
        return (
            self.imported_structural_kg
            + self.metallic_fasteners_kg
            + self.electrical_thermal_kg
        )

    @property
    def total_mass_kg(self) -> float:
        return self.total_isru_mass_kg + self.total_imported_mass_kg

    @property
    def isru_mass_fraction_pct(self) -> float:
        if self.total_mass_kg <= 0:
            return 100.0
        return (self.total_isru_mass_kg / self.total_mass_kg) * 100.0

    def get_mass_by_category(self, cat: MaterialCategory) -> float:
        mapping = {
            MaterialCategory.REGOLITH_FEEDSTOCK_RAW: self.raw_regolith_feedstock_kg,
            MaterialCategory.REGOLITH_SCREENED: self.screened_regolith_kg,
            MaterialCategory.REGOLITH_COMPACTED: self.compacted_regolith_kg,
            MaterialCategory.REGOLITH_SINTERED_BLOCKS: self.sintered_blocks_kg,
            MaterialCategory.REGOLITH_GEOPOLYMER: self.geopolymer_concrete_kg,
            MaterialCategory.IMPORTED_STRUCTURAL: self.imported_structural_kg,
            MaterialCategory.METALLIC_FASTENERS: self.metallic_fasteners_kg,
            MaterialCategory.ELECTRICAL_THERMAL: self.electrical_thermal_kg,
        }
        return mapping.get(cat, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_mass_kg": round(self.total_mass_kg, 1),
            "isru_mass_kg": round(self.total_isru_mass_kg, 1),
            "imported_mass_kg": round(self.total_imported_mass_kg, 1),
            "isru_fraction_pct": round(self.isru_mass_fraction_pct, 1),
            "breakdown_kg": {
                "raw_regolith": round(self.raw_regolith_feedstock_kg, 1),
                "screened": round(self.screened_regolith_kg, 1),
                "compacted": round(self.compacted_regolith_kg, 1),
                "sintered_blocks": round(self.sintered_blocks_kg, 1),
                "geopolymer": round(self.geopolymer_concrete_kg, 1),
                "imported_structural": round(self.imported_structural_kg, 1),
                "fasteners": round(self.metallic_fasteners_kg, 1),
                "electrical_thermal": round(self.electrical_thermal_kg, 1),
            },
        }


@dataclass
class InfrastructureAssetDefinition:
    """Static catalog definition specifying how an asset is constructed and verified."""
    asset_type: InfrastructureAssetType
    name: str
    description: str
    dimensions_m: Tuple[float, float, float]       # Length, Width, Height (meters)
    footprint_area_m2: float
    boq: InfrastructureBillOfQuantities
    nominal_duration_hours: float
    nominal_energy_kwh: float
    required_robot_classes: List[RobotClass]
    predecessor_asset_types: List[InfrastructureAssetType]
    max_tolerated_surface_roughness_cm: float
    min_compressive_strength_mpa: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.asset_type.value,
            "name": self.name,
            "dimensions_lwh_m": list(self.dimensions_m),
            "footprint_m2": round(self.footprint_area_m2, 1),
            "boq": self.boq.to_dict(),
            "nominal_duration_hours": round(self.nominal_duration_hours, 1),
            "nominal_energy_kwh": round(self.nominal_energy_kwh, 1),
            "required_robots": [r.value for r in self.required_robot_classes],
            "predecessors": [p.value for p in self.predecessor_asset_types],
            "min_compressive_strength_mpa": self.min_compressive_strength_mpa,
        }


@dataclass
class ConstructedAssetInstance:
    """A live instantiated infrastructure asset undergoing construction in a settlement."""
    instance_id: str
    asset_type: InfrastructureAssetType
    settlement_id: str
    definition: InfrastructureAssetDefinition
    state: AssetConstructionState = AssetConstructionState.PLANNED
    progress_pct: float = 0.0
    creation_time_s: float = 0.0
    completion_time_s: Optional[float] = None
    assigned_robot_ids: List[str] = field(default_factory=list)
    measured_compressive_strength_mpa: float = 0.0
    measured_surface_roughness_cm: float = 0.0
    inspection_notes: str = ""
    rework_count: int = 0
    energy_consumed_kwh: float = 0.0

    @property
    def is_accepted(self) -> bool:
        return self.state == AssetConstructionState.ACCEPTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "type": self.asset_type.value,
            "name": self.definition.name,
            "settlement": self.settlement_id,
            "state": self.state.value,
            "progress_pct": round(self.progress_pct, 1),
            "isru_fraction_pct": round(self.definition.boq.isru_mass_fraction_pct, 1),
            "total_mass_kg": round(self.definition.boq.total_mass_kg, 1),
            "energy_consumed_kwh": round(self.energy_consumed_kwh, 1),
            "rework_count": self.rework_count,
            "inspection_notes": self.inspection_notes if self.inspection_notes else None,
        }


# Canonical Infrastructure Asset Catalogue
INFRASTRUCTURE_CATALOGUE: Dict[InfrastructureAssetType, InfrastructureAssetDefinition] = {
    InfrastructureAssetType.LANDING_ZONE_PREPARATION: InfrastructureAssetDefinition(
        asset_type=InfrastructureAssetType.LANDING_ZONE_PREPARATION,
        name="Landing Zone Surface Clearing & Coarse Grading",
        description="Removal of surface boulders (>10 cm), regolith scraping, and 1% gradient levelling over 2500 m2.",
        dimensions_m=(50.0, 50.0, 0.5),
        footprint_area_m2=2500.0,
        boq=InfrastructureBillOfQuantities(raw_regolith_feedstock_kg=12_000.0, compacted_regolith_kg=8_000.0),
        nominal_duration_hours=24.0,
        nominal_energy_kwh=65.0,
        required_robot_classes=[RobotClass.EXCAVATOR, RobotClass.HAULER, RobotClass.INSPECTOR],
        predecessor_asset_types=[],
        max_tolerated_surface_roughness_cm=5.0,
        min_compressive_strength_mpa=0.5,
    ),
    InfrastructureAssetType.LANDING_PAD_SEGMENTS: InfrastructureAssetDefinition(
        asset_type=InfrastructureAssetType.LANDING_PAD_SEGMENTS,
        name="High-Temperature Sintered Landing Pad Plume Deflector",
        description="Interlocking microwave-sintered basaltic masonry tiles capable of withstanding rocket exhaust plumes.",
        dimensions_m=(30.0, 30.0, 0.3),
        footprint_area_m2=900.0,
        boq=InfrastructureBillOfQuantities(
            screened_regolith_kg=35_000.0, sintered_blocks_kg=32_000.0, imported_structural_kg=450.0, metallic_fasteners_kg=180.0
        ),
        nominal_duration_hours=72.0,
        nominal_energy_kwh=480.0,
        required_robot_classes=[RobotClass.MANUFACTURER, RobotClass.HAULER, RobotClass.ASSEMBLER, RobotClass.INSPECTOR],
        predecessor_asset_types=[InfrastructureAssetType.LANDING_ZONE_PREPARATION],
        max_tolerated_surface_roughness_cm=1.0,
        min_compressive_strength_mpa=35.0,
    ),
    InfrastructureAssetType.ACCESS_ROADS_MOBILITY_ROUTES: InfrastructureAssetDefinition(
        asset_type=InfrastructureAssetType.ACCESS_ROADS_MOBILITY_ROUTES,
        name="Compacted Heavy Transport Roadway (500m Sector)",
        description="Engineered basaltic subgrade road with stabilized crowning and drainage berms to prevent rover slippage.",
        dimensions_m=(500.0, 6.0, 0.4),
        footprint_area_m2=3000.0,
        boq=InfrastructureBillOfQuantities(raw_regolith_feedstock_kg=45_000.0, compacted_regolith_kg=40_000.0),
        nominal_duration_hours=36.0,
        nominal_energy_kwh=95.0,
        required_robot_classes=[RobotClass.EXCAVATOR, RobotClass.HAULER, RobotClass.INSPECTOR],
        predecessor_asset_types=[InfrastructureAssetType.LANDING_ZONE_PREPARATION],
        max_tolerated_surface_roughness_cm=3.0,
        min_compressive_strength_mpa=2.5,
    ),
    InfrastructureAssetType.EQUIPMENT_FOUNDATIONS: InfrastructureAssetDefinition(
        asset_type=InfrastructureAssetType.EQUIPMENT_FOUNDATIONS,
        name="Nuclear Reactor & Heavy ISRU Equipment Foundation Pad",
        description="High-density sintered basalt slab engineered to isolate vibratory loads from Kilopower reactors and cryo-coolers.",
        dimensions_m=(12.0, 12.0, 0.6),
        footprint_area_m2=144.0,
        boq=InfrastructureBillOfQuantities(
            screened_regolith_kg=18_000.0, sintered_blocks_kg=16_500.0, imported_structural_kg=320.0, metallic_fasteners_kg=120.0
        ),
        nominal_duration_hours=48.0,
        nominal_energy_kwh=260.0,
        required_robot_classes=[RobotClass.EXCAVATOR, RobotClass.MANUFACTURER, RobotClass.ASSEMBLER, RobotClass.INSPECTOR],
        predecessor_asset_types=[InfrastructureAssetType.LANDING_ZONE_PREPARATION],
        max_tolerated_surface_roughness_cm=0.5,
        min_compressive_strength_mpa=30.0,
    ),
    InfrastructureAssetType.REGOLITH_BERMS_SHIELDING: InfrastructureAssetDefinition(
        asset_type=InfrastructureAssetType.REGOLITH_BERMS_SHIELDING,
        name="Regolith Blast & Radiation Protection Berm (50m)",
        description="Compacted earthen embankment 4 meters tall providing line-of-sight micrometeorite and launch ejecta protection.",
        dimensions_m=(50.0, 8.0, 4.0),
        footprint_area_m2=400.0,
        boq=InfrastructureBillOfQuantities(raw_regolith_feedstock_kg=95_000.0, compacted_regolith_kg=92_000.0),
        nominal_duration_hours=40.0,
        nominal_energy_kwh=110.0,
        required_robot_classes=[RobotClass.EXCAVATOR, RobotClass.HAULER, RobotClass.INSPECTOR],
        predecessor_asset_types=[InfrastructureAssetType.LANDING_ZONE_PREPARATION],
        max_tolerated_surface_roughness_cm=10.0,
        min_compressive_strength_mpa=1.5,
    ),
    InfrastructureAssetType.UTILITY_TRENCHES: InfrastructureAssetDefinition(
        asset_type=InfrastructureAssetType.UTILITY_TRENCHES,
        name="Subsurface Power & Fluid Utility Trench (200m)",
        description="Excavated 1.5m deep conduit backfilled with graded regolith to thermally protect cryo and electrical distribution lines.",
        dimensions_m=(200.0, 1.0, 1.5),
        footprint_area_m2=200.0,
        boq=InfrastructureBillOfQuantities(
            raw_regolith_feedstock_kg=15_000.0, compacted_regolith_kg=12_000.0, electrical_thermal_kg=650.0
        ),
        nominal_duration_hours=20.0,
        nominal_energy_kwh=45.0,
        required_robot_classes=[RobotClass.EXCAVATOR, RobotClass.ASSEMBLER, RobotClass.INSPECTOR],
        predecessor_asset_types=[InfrastructureAssetType.LANDING_ZONE_PREPARATION],
        max_tolerated_surface_roughness_cm=8.0,
        min_compressive_strength_mpa=1.0,
    ),
    InfrastructureAssetType.SOLAR_ARRAY_FOUNDATIONS: InfrastructureAssetDefinition(
        asset_type=InfrastructureAssetType.SOLAR_ARRAY_FOUNDATIONS,
        name="Solar Photovoltaic Tracker Foundation & Support Trusses",
        description="Anchored geopolymer footings holding 100 kW dual-axis tracking solar panels above blowing dust level.",
        dimensions_m=(40.0, 15.0, 2.5),
        footprint_area_m2=600.0,
        boq=InfrastructureBillOfQuantities(
            geopolymer_concrete_kg=8_500.0, imported_structural_kg=1_200.0, metallic_fasteners_kg=350.0, electrical_thermal_kg=450.0
        ),
        nominal_duration_hours=32.0,
        nominal_energy_kwh=85.0,
        required_robot_classes=[RobotClass.MANUFACTURER, RobotClass.ASSEMBLER, RobotClass.INSPECTOR],
        predecessor_asset_types=[InfrastructureAssetType.LANDING_ZONE_PREPARATION, InfrastructureAssetType.EQUIPMENT_FOUNDATIONS],
        max_tolerated_surface_roughness_cm=1.5,
        min_compressive_strength_mpa=22.0,
    ),
    InfrastructureAssetType.ANTENNA_FOUNDATIONS_MASTS: InfrastructureAssetDefinition(
        asset_type=InfrastructureAssetType.ANTENNA_FOUNDATIONS_MASTS,
        name="High-Gain Deep Space Communications Tower Foundation",
        description="High-tensile guyed mast base and microwave dish anchor pad providing line-of-sight to orbiters.",
        dimensions_m=(8.0, 8.0, 15.0),
        footprint_area_m2=64.0,
        boq=InfrastructureBillOfQuantities(
            sintered_blocks_kg=11_000.0, imported_structural_kg=850.0, metallic_fasteners_kg=240.0, electrical_thermal_kg=180.0
        ),
        nominal_duration_hours=28.0,
        nominal_energy_kwh=130.0,
        required_robot_classes=[RobotClass.MANUFACTURER, RobotClass.ASSEMBLER, RobotClass.INSPECTOR],
        predecessor_asset_types=[InfrastructureAssetType.EQUIPMENT_FOUNDATIONS],
        max_tolerated_surface_roughness_cm=0.8,
        min_compressive_strength_mpa=28.0,
    ),
    InfrastructureAssetType.EQUIPMENT_SHELTERS: InfrastructureAssetDefinition(
        asset_type=InfrastructureAssetType.EQUIPMENT_SHELTERS,
        name="Arched Regolith Vault Equipment Shelter (Unpressurized)",
        description="3D printed parabolic compression arch shielding maintenance rovers and printing robots from UV and thermal extremes.",
        dimensions_m=(20.0, 12.0, 6.0),
        footprint_area_m2=240.0,
        boq=InfrastructureBillOfQuantities(
            screened_regolith_kg=28_000.0, sintered_blocks_kg=26_000.0, imported_structural_kg=600.0, metallic_fasteners_kg=200.0
        ),
        nominal_duration_hours=60.0,
        nominal_energy_kwh=380.0,
        required_robot_classes=[RobotClass.MANUFACTURER, RobotClass.ASSEMBLER, RobotClass.INSPECTOR],
        predecessor_asset_types=[InfrastructureAssetType.EQUIPMENT_FOUNDATIONS],
        max_tolerated_surface_roughness_cm=2.0,
        min_compressive_strength_mpa=25.0,
    ),
    InfrastructureAssetType.MODULAR_STORAGE_BAYS: InfrastructureAssetDefinition(
        asset_type=InfrastructureAssetType.MODULAR_STORAGE_BAYS,
        name="Bulk Feedstock & Spare Parts Storage Bunker",
        description="Segmented storage enclosures with sintered retaining walls preventing regolith slumping and contamination.",
        dimensions_m=(25.0, 15.0, 3.0),
        footprint_area_m2=375.0,
        boq=InfrastructureBillOfQuantities(
            screened_regolith_kg=22_000.0, sintered_blocks_kg=20_000.0, metallic_fasteners_kg=150.0
        ),
        nominal_duration_hours=44.0,
        nominal_energy_kwh=290.0,
        required_robot_classes=[RobotClass.EXCAVATOR, RobotClass.MANUFACTURER, RobotClass.ASSEMBLER, RobotClass.INSPECTOR],
        predecessor_asset_types=[InfrastructureAssetType.LANDING_ZONE_PREPARATION],
        max_tolerated_surface_roughness_cm=2.5,
        min_compressive_strength_mpa=20.0,
    ),
    InfrastructureAssetType.POWER_DISTRIBUTION_HUBS: InfrastructureAssetDefinition(
        asset_type=InfrastructureAssetType.POWER_DISTRIBUTION_HUBS,
        name="Central Power Conditioning & Switchgear Vault",
        description="Hardened foundation with cable routing vaults integrating solar, fission, and fuel-cell distribution busbars.",
        dimensions_m=(10.0, 8.0, 2.5),
        footprint_area_m2=80.0,
        boq=InfrastructureBillOfQuantities(
            sintered_blocks_kg=9_500.0, imported_structural_kg=750.0, metallic_fasteners_kg=180.0, electrical_thermal_kg=850.0
        ),
        nominal_duration_hours=26.0,
        nominal_energy_kwh=115.0,
        required_robot_classes=[RobotClass.ASSEMBLER, RobotClass.INSPECTOR],
        predecessor_asset_types=[InfrastructureAssetType.EQUIPMENT_FOUNDATIONS, InfrastructureAssetType.UTILITY_TRENCHES],
        max_tolerated_surface_roughness_cm=1.0,
        min_compressive_strength_mpa=24.0,
    ),
    InfrastructureAssetType.SURFACE_RELAY_STATIONS: InfrastructureAssetDefinition(
        asset_type=InfrastructureAssetType.SURFACE_RELAY_STATIONS,
        name="Crater-Rim Autonomous Surface Relay Installation",
        description="Remote microwave relay tower base and solar/battery pad mounted on elevated crater rims for inter-settlement comms.",
        dimensions_m=(6.0, 6.0, 8.0),
        footprint_area_m2=36.0,
        boq=InfrastructureBillOfQuantities(
            sintered_blocks_kg=6_000.0, imported_structural_kg=550.0, metallic_fasteners_kg=140.0, electrical_thermal_kg=220.0
        ),
        nominal_duration_hours=22.0,
        nominal_energy_kwh=80.0,
        required_robot_classes=[RobotClass.MANUFACTURER, RobotClass.ASSEMBLER, RobotClass.INSPECTOR],
        predecessor_asset_types=[InfrastructureAssetType.EQUIPMENT_FOUNDATIONS],
        max_tolerated_surface_roughness_cm=1.2,
        min_compressive_strength_mpa=25.0,
    ),
}
