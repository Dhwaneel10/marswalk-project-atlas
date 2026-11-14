"""
MarsWalk 2.0 / Project Atlas — Milestone 13K Mission Intent Specification
==========================================================================
Defines the formal input language and data contracts for goal-driven planetary
mission design. Captures high-level mission objectives, fleet composition,
spatial intent, duration, communications requirements, physical constraints,
and multi-objective optimization preferences.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class ScienceObjectiveCategory(str, Enum):
    GEOLOGIC_MAPPING = "GEOLOGIC_MAPPING"
    MINERALOGIC_SPECTROSCOPY = "MINERALOGIC_SPECTROSCOPY"
    ELEMENTAL_CHEMISTRY = "ELEMENTAL_CHEMISTRY"
    ORGANIC_SPECTROSCOPY = "ORGANIC_SPECTROSCOPY"
    SUBSURFACE_STRATIGRAPHY = "SUBSURFACE_STRATIGRAPHY"
    ATMOSPHERIC_METEOROLOGY = "ATMOSPHERIC_METEOROLOGY"
    SAMPLE_EXTRACTION = "SAMPLE_EXTRACTION"


class MissionPlanningMode(str, Enum):
    BALANCED = "BALANCED"
    SCIENCE_MAXIMIZING = "SCIENCE_MAXIMIZING"
    ENERGY_EFFICIENT = "ENERGY_EFFICIENT"
    COMMUNICATIONS_FOCUSED = "COMMUNICATIONS_FOCUSED"
    MINIMUM_DURATION = "MINIMUM_DURATION"
    ROBUSTNESS_FOCUSED = "ROBUSTNESS_FOCUSED"
    MINIMUM_INFRASTRUCTURE = "MINIMUM_INFRASTRUCTURE"
    DATA_RETURN_FOCUSED = "DATA_RETURN_FOCUSED"


@dataclass
class ScienceObjectiveIntent:
    """High-level scientific goals specified by the mission designer."""
    primary_objectives: List[str] = field(default_factory=lambda: [
        ScienceObjectiveCategory.GEOLOGIC_MAPPING.value,
        ScienceObjectiveCategory.MINERALOGIC_SPECTROSCOPY.value,
        ScienceObjectiveCategory.ELEMENTAL_CHEMISTRY.value,
    ])
    mandatory_target_ids: List[str] = field(default_factory=list)
    preferred_target_ids: List[str] = field(default_factory=list)
    minimum_observations_count: int = 4
    maximum_targets_limit: int = 12
    required_instruments: List[str] = field(default_factory=list)
    excluded_instruments: List[str] = field(default_factory=list)
    minimum_science_utility_pts: float = 1000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_objectives": list(self.primary_objectives),
            "mandatory_target_ids": list(self.mandatory_target_ids),
            "preferred_target_ids": list(self.preferred_target_ids),
            "minimum_observations_count": self.minimum_observations_count,
            "maximum_targets_limit": self.maximum_targets_limit,
            "required_instruments": list(self.required_instruments),
            "excluded_instruments": list(self.excluded_instruments),
            "minimum_science_utility_pts": round(self.minimum_science_utility_pts, 2),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScienceObjectiveIntent":
        return cls(
            primary_objectives=data.get("primary_objectives", [
                ScienceObjectiveCategory.GEOLOGIC_MAPPING.value,
                ScienceObjectiveCategory.MINERALOGIC_SPECTROSCOPY.value,
            ]),
            mandatory_target_ids=data.get("mandatory_target_ids", []),
            preferred_target_ids=data.get("preferred_target_ids", []),
            minimum_observations_count=int(data.get("minimum_observations_count", 4)),
            maximum_targets_limit=int(data.get("maximum_targets_limit", 12)),
            required_instruments=data.get("required_instruments", []),
            excluded_instruments=data.get("excluded_instruments", []),
            minimum_science_utility_pts=float(data.get("minimum_science_utility_pts", 1000.0)),
        )


@dataclass
class FleetCompositionIntent:
    """Exploration fleet configuration preferences."""
    maximum_rovers: int = 4
    minimum_rovers: int = 1
    permitted_rover_ids: List[str] = field(default_factory=lambda: [
        "ATLAS_ROVER_A",
        "ATLAS_ROVER_B",
        "ATLAS_ROVER_C",
        "ATLAS_ROVER_D",
    ])
    mandatory_rover_assignments: Dict[str, str] = field(default_factory=dict)  # target_id -> rover_id
    allow_mobile_relay_role: bool = True
    enforce_zero_energy_pooling: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "maximum_rovers": self.maximum_rovers,
            "minimum_rovers": self.minimum_rovers,
            "permitted_rover_ids": list(self.permitted_rover_ids),
            "mandatory_rover_assignments": dict(self.mandatory_rover_assignments),
            "allow_mobile_relay_role": self.allow_mobile_relay_role,
            "enforce_zero_energy_pooling": self.enforce_zero_energy_pooling,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FleetCompositionIntent":
        return cls(
            maximum_rovers=int(data.get("maximum_rovers", 4)),
            minimum_rovers=int(data.get("minimum_rovers", 1)),
            permitted_rover_ids=data.get("permitted_rover_ids", [
                "ATLAS_ROVER_A", "ATLAS_ROVER_B", "ATLAS_ROVER_C", "ATLAS_ROVER_D"
            ]),
            mandatory_rover_assignments=data.get("mandatory_rover_assignments", {}),
            allow_mobile_relay_role=bool(data.get("allow_mobile_relay_role", True)),
            enforce_zero_energy_pooling=bool(data.get("enforce_zero_energy_pooling", True)),
        )


@dataclass
class GeographicSpatialIntent:
    """Spatial and regional intent referencing authentic Jezero DTM coordinates."""
    region_id: str = "JEZERO_WESTERN_DELTA"
    starting_location_rc: Tuple[int, int] = (128, 128)
    base_station_rc: Tuple[int, int] = (128, 128)
    destination_area_name: Optional[str] = "Western Delta Front"
    required_waypoints: List[Tuple[int, int]] = field(default_factory=list)
    avoidance_zones: List[Dict[str, Any]] = field(default_factory=list)
    spatial_proximity_margin_m: float = 40.0
    maximum_slope_limit_deg: float = 25.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "starting_location_rc": list(self.starting_location_rc),
            "base_station_rc": list(self.base_station_rc),
            "destination_area_name": self.destination_area_name,
            "required_waypoints": [list(wp) for wp in self.required_waypoints],
            "avoidance_zones": self.avoidance_zones,
            "spatial_proximity_margin_m": round(self.spatial_proximity_margin_m, 1),
            "maximum_slope_limit_deg": round(self.maximum_slope_limit_deg, 1),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeographicSpatialIntent":
        raw_start = data.get("starting_location_rc", [128, 128])
        raw_base = data.get("base_station_rc", [128, 128])
        raw_wps = data.get("required_waypoints", [])
        return cls(
            region_id=data.get("region_id", "JEZERO_WESTERN_DELTA"),
            starting_location_rc=(int(raw_start[0]), int(raw_start[1])),
            base_station_rc=(int(raw_base[0]), int(raw_base[1])),
            destination_area_name=data.get("destination_area_name", "Western Delta Front"),
            required_waypoints=[(int(w[0]), int(w[1])) for w in raw_wps],
            avoidance_zones=data.get("avoidance_zones", []),
            spatial_proximity_margin_m=float(data.get("spatial_proximity_margin_m", 40.0)),
            maximum_slope_limit_deg=float(data.get("maximum_slope_limit_deg", 25.0)),
        )


@dataclass
class TemporalDurationIntent:
    """Mission timeline and sol bounds."""
    maximum_sols: int = 5
    preferred_sols: int = 5
    sol_driving_start_hour_ltst: float = 7.5   # 07:30 LTST
    sol_driving_end_hour_ltst: float = 17.0   # 17:00 LTST
    minimum_sol_reserve_soc_pct: float = 20.0
    diurnal_recharge_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "maximum_sols": self.maximum_sols,
            "preferred_sols": self.preferred_sols,
            "sol_driving_start_hour_ltst": round(self.sol_driving_start_hour_ltst, 2),
            "sol_driving_end_hour_ltst": round(self.sol_driving_end_hour_ltst, 2),
            "minimum_sol_reserve_soc_pct": round(self.minimum_sol_reserve_soc_pct, 1),
            "diurnal_recharge_enabled": self.diurnal_recharge_enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemporalDurationIntent":
        return cls(
            maximum_sols=int(data.get("maximum_sols", 5)),
            preferred_sols=int(data.get("preferred_sols", 5)),
            sol_driving_start_hour_ltst=float(data.get("sol_driving_start_hour_ltst", 7.5)),
            sol_driving_end_hour_ltst=float(data.get("sol_driving_end_hour_ltst", 17.0)),
            minimum_sol_reserve_soc_pct=float(data.get("minimum_sol_reserve_soc_pct", 20.0)),
            diurnal_recharge_enabled=bool(data.get("diurnal_recharge_enabled", True)),
        )


@dataclass
class CommunicationsIntent:
    """RelayNet and geometric line-of-sight requirements."""
    maximum_relays_deployable: int = 2
    minimum_geometric_reachability_pct: float = 85.0
    enable_peer_mesh_forwarding: bool = True
    base_station_antenna_height_m: float = 5.0
    rover_antenna_height_m: float = 2.2
    max_link_range_m: float = 5000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "maximum_relays_deployable": self.maximum_relays_deployable,
            "minimum_geometric_reachability_pct": round(self.minimum_geometric_reachability_pct, 1),
            "enable_peer_mesh_forwarding": self.enable_peer_mesh_forwarding,
            "base_station_antenna_height_m": round(self.base_station_antenna_height_m, 1),
            "rover_antenna_height_m": round(self.rover_antenna_height_m, 1),
            "max_link_range_m": round(self.max_link_range_m, 1),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommunicationsIntent":
        return cls(
            maximum_relays_deployable=int(data.get("maximum_relays_deployable", 2)),
            minimum_geometric_reachability_pct=float(data.get("minimum_geometric_reachability_pct", 85.0)),
            enable_peer_mesh_forwarding=bool(data.get("enable_peer_mesh_forwarding", True)),
            base_station_antenna_height_m=float(data.get("base_station_antenna_height_m", 5.0)),
            rover_antenna_height_m=float(data.get("rover_antenna_height_m", 2.2)),
            max_link_range_m=float(data.get("max_link_range_m", 5000.0)),
        )


@dataclass
class ResourceLimitsIntent:
    """Hard constraints on electrical energy, storage buffers, and downlink capacity."""
    minimum_battery_reserve_pct: float = 20.0
    maximum_flash_storage_utilization_pct: float = 85.0
    max_acceptable_data_backlog_mb: float = 500.0
    shared_downlink_bandwidth_mbps: float = 2.0
    daily_avionics_load_w: float = 110.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "minimum_battery_reserve_pct": round(self.minimum_battery_reserve_pct, 1),
            "maximum_flash_storage_utilization_pct": round(self.maximum_flash_storage_utilization_pct, 1),
            "max_acceptable_data_backlog_mb": round(self.max_acceptable_data_backlog_mb, 1),
            "shared_downlink_bandwidth_mbps": round(self.shared_downlink_bandwidth_mbps, 2),
            "daily_avionics_load_w": round(self.daily_avionics_load_w, 1),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceLimitsIntent":
        return cls(
            minimum_battery_reserve_pct=float(data.get("minimum_battery_reserve_pct", 20.0)),
            maximum_flash_storage_utilization_pct=float(data.get("maximum_flash_storage_utilization_pct", 85.0)),
            max_acceptable_data_backlog_mb=float(data.get("max_acceptable_data_backlog_mb", 500.0)),
            shared_downlink_bandwidth_mbps=float(data.get("shared_downlink_bandwidth_mbps", 2.0)),
            daily_avionics_load_w=float(data.get("daily_avionics_load_w", 110.0)),
        )


@dataclass
class OptimizationPreferencesIntent:
    """Soft preference weights for multi-objective Pareto trade-off synthesis."""
    weight_science_utility: float = 0.35
    weight_energy_conservation: float = 0.20
    weight_traverse_efficiency: float = 0.15
    weight_communications_continuity: float = 0.15
    weight_duration_compression: float = 0.10
    weight_infrastructure_minimization: float = 0.05
    preferred_planning_mode: str = MissionPlanningMode.BALANCED.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "weight_science_utility": round(self.weight_science_utility, 2),
            "weight_energy_conservation": round(self.weight_energy_conservation, 2),
            "weight_traverse_efficiency": round(self.weight_traverse_efficiency, 2),
            "weight_communications_continuity": round(self.weight_communications_continuity, 2),
            "weight_duration_compression": round(self.weight_duration_compression, 2),
            "weight_infrastructure_minimization": round(self.weight_infrastructure_minimization, 2),
            "preferred_planning_mode": self.preferred_planning_mode,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OptimizationPreferencesIntent":
        return cls(
            weight_science_utility=float(data.get("weight_science_utility", 0.35)),
            weight_energy_conservation=float(data.get("weight_energy_conservation", 0.20)),
            weight_traverse_efficiency=float(data.get("weight_traverse_efficiency", 0.15)),
            weight_communications_continuity=float(data.get("weight_communications_continuity", 0.15)),
            weight_duration_compression=float(data.get("weight_duration_compression", 0.10)),
            weight_infrastructure_minimization=float(data.get("weight_infrastructure_minimization", 0.05)),
            preferred_planning_mode=data.get("preferred_planning_mode", MissionPlanningMode.BALANCED.value),
        )


@dataclass
class MissionIntent:
    """
    Formal, structured representation of a goal-driven Martian mission intent.
    Acts as the primary contract passed to the Mission Goal Compiler.
    """
    intent_id: str
    name: str
    description: str
    campaign_id: str = "cmp_jezero_delta_5sol"
    version: int = 1
    raw_natural_language_brief: Optional[str] = None
    created_at_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    science: ScienceObjectiveIntent = field(default_factory=ScienceObjectiveIntent)
    fleet: FleetCompositionIntent = field(default_factory=FleetCompositionIntent)
    geography: GeographicSpatialIntent = field(default_factory=GeographicSpatialIntent)
    timeline: TemporalDurationIntent = field(default_factory=TemporalDurationIntent)
    communications: CommunicationsIntent = field(default_factory=CommunicationsIntent)
    resources: ResourceLimitsIntent = field(default_factory=ResourceLimitsIntent)
    preferences: OptimizationPreferencesIntent = field(default_factory=OptimizationPreferencesIntent)
    environmental_qualification_level: str = "CALIBRATED_WITH_HOLDOUT_VALIDATION"

    def compute_fingerprint(self) -> str:
        """Computes a deterministic SHA-256 hash digest of the full mission intent specification."""
        payload = {
            "name": self.name,
            "campaign_id": self.campaign_id,
            "science": self.science.to_dict(),
            "fleet": self.fleet.to_dict(),
            "geography": self.geography.to_dict(),
            "timeline": self.timeline.to_dict(),
            "communications": self.communications.to_dict(),
            "resources": self.resources.to_dict(),
            "preferences": self.preferences.to_dict(),
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "name": self.name,
            "description": self.description,
            "campaign_id": self.campaign_id,
            "version": self.version,
            "raw_natural_language_brief": self.raw_natural_language_brief,
            "created_at_utc": self.created_at_utc,
            "fingerprint": self.compute_fingerprint(),
            "science": self.science.to_dict(),
            "fleet": self.fleet.to_dict(),
            "geography": self.geography.to_dict(),
            "timeline": self.timeline.to_dict(),
            "communications": self.communications.to_dict(),
            "resources": self.resources.to_dict(),
            "preferences": self.preferences.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MissionIntent":
        return cls(
            intent_id=data.get("intent_id", f"intent_{int(time.time())}"),
            name=data.get("name", "Goal-Driven Jezero Reconnaissance"),
            description=data.get("description", "Autonomous multi-rover reconnaissance intent."),
            campaign_id=data.get("campaign_id", "cmp_jezero_delta_5sol"),
            version=int(data.get("version", 1)),
            raw_natural_language_brief=data.get("raw_natural_language_brief"),
            created_at_utc=data.get("created_at_utc", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
            science=ScienceObjectiveIntent.from_dict(data.get("science", {})),
            fleet=FleetCompositionIntent.from_dict(data.get("fleet", {})),
            geography=GeographicSpatialIntent.from_dict(data.get("geography", {})),
            timeline=TemporalDurationIntent.from_dict(data.get("timeline", {})),
            communications=CommunicationsIntent.from_dict(data.get("communications", {})),
            resources=ResourceLimitsIntent.from_dict(data.get("resources", {})),
            preferences=OptimizationPreferencesIntent.from_dict(data.get("preferences", {})),
        )


def create_sample_jezero_mission_intent(
    intent_id: str = "intent_sample_jezero_recon",
    name: str = "Western Jezero Delta Cooperative Geological Reconnaissance",
    brief: Optional[str] = (
        "Explore the western Jezero delta using two rovers over five sols. "
        "Prioritize geological characterization and mineralogical investigation. "
        "Preserve at least 20% of each rover's configured energy reserve. "
        "Deploy no more than two relays. Minimize data backlog and maximize valid science observations."
    )
) -> MissionIntent:
    """Constructs a calibrated sample mission intent for demonstration and benchmark execution."""
    intent = MissionIntent(
        intent_id=intent_id,
        name=name,
        description="Autonomous 2-rover 5-sol reconnaissance of the Western Jezero delta fan.",
        raw_natural_language_brief=brief,
        science=ScienceObjectiveIntent(
            primary_objectives=[
                ScienceObjectiveCategory.GEOLOGIC_MAPPING.value,
                ScienceObjectiveCategory.MINERALOGIC_SPECTROSCOPY.value,
                ScienceObjectiveCategory.ELEMENTAL_CHEMISTRY.value,
            ],
            mandatory_target_ids=["TGT_HAWKSBILL_GAP", "TGT_SKINNER_RIDGE"],
            preferred_target_ids=["TGT_BELVA_CRATER", "TGT_ENCHANTED_LAKE"],
            minimum_observations_count=4,
            maximum_targets_limit=6,
            required_instruments=["PIXL", "MASTCAM_Z"],
            minimum_science_utility_pts=1200.0,
        ),
        fleet=FleetCompositionIntent(
            maximum_rovers=2,
            minimum_rovers=2,
            permitted_rover_ids=["ATLAS_ROVER_A", "ATLAS_ROVER_B"],
            allow_mobile_relay_role=False,
            enforce_zero_energy_pooling=True,
        ),
        geography=GeographicSpatialIntent(
            region_id="JEZERO_WESTERN_DELTA",
            starting_location_rc=(128, 128),
            base_station_rc=(128, 128),
            spatial_proximity_margin_m=40.0,
            maximum_slope_limit_deg=25.0,
        ),
        timeline=TemporalDurationIntent(
            maximum_sols=5,
            preferred_sols=5,
            minimum_sol_reserve_soc_pct=20.0,
        ),
        communications=CommunicationsIntent(
            maximum_relays_deployable=2,
            minimum_geometric_reachability_pct=85.0,
        ),
        resources=ResourceLimitsIntent(
            minimum_battery_reserve_pct=20.0,
            maximum_flash_storage_utilization_pct=85.0,
            max_acceptable_data_backlog_mb=500.0,
            shared_downlink_bandwidth_mbps=2.0,
        ),
        preferences=OptimizationPreferencesIntent(
            weight_science_utility=0.40,
            weight_energy_conservation=0.25,
            weight_traverse_efficiency=0.15,
            weight_communications_continuity=0.15,
            weight_infrastructure_minimization=0.05,
            preferred_planning_mode=MissionPlanningMode.BALANCED.value,
        )
    )
    return intent
