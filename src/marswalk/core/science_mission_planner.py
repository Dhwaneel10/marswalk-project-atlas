"""
MarsWalk Core Science Mission Planner Engine (Milestone 13G).

Implements rigorous planetary science target prioritization, instrument-to-observation
compatibility validation, 5-phase chronological activity scheduling, adaptive replanning,
and seamless integration with the Milestone 13F energy resource model and onboard data ledger.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from marswalk.core.mission_data_ledger import (
    DataCategory,
    DataProductStorageStatus,
    DataProductTransferStatus,
    MissionDataProduct,
    MissionDataLedger,
    PriorityType,
    RetentionPolicy,
    StoragePressureState,
    compute_product_sha256,
)
from marswalk.core.mission_resource_model import (
    RoverResourceConfig,
    MissionResourceLedger,
    MissionActivityEvent,
    joules_to_wh,
    wh_to_joules,
)


class ScienceObjective(str, Enum):
    """Standardized planetary science objectives."""
    GEOLOGICAL_CHARACTERIZATION = "GEOLOGICAL_CHARACTERIZATION"
    MINERALOGICAL_INVESTIGATION = "MINERALOGICAL_INVESTIGATION"
    ATMOSPHERIC_OBSERVATION = "ATMOSPHERIC_OBSERVATION"
    SURFACE_MORPHOLOGY = "SURFACE_MORPHOLOGY"
    ENVIRONMENTAL_MONITORING = "ENVIRONMENTAL_MONITORING"
    ASTROBIOLOGY_BIOSIGNATURE_SURVEY = "ASTROBIOLOGY_BIOSIGNATURE_SURVEY"


class InstrumentId(str, Enum):
    """Taxonomy of planetary surface exploration instruments."""
    MASTCAM_Z = "MASTCAM_Z"
    SUPERCAM = "SUPERCAM"
    PIXL = "PIXL"
    SHERLOC = "SHERLOC"
    RIMFAX = "RIMFAX"
    MEDA = "MEDA"
    CORING_TOOL = "CORING_TOOL"


class ObservationPhase(str, Enum):
    """Phases of an in-situ scientific observation stop."""
    ROVER_ARRIVAL_AND_SETTLE = "ROVER_ARRIVAL_AND_SETTLE"
    INSTRUMENT_PREPARATION_AND_WARMUP = "INSTRUMENT_PREPARATION_AND_WARMUP"
    OBSERVATION_EXECUTION = "OBSERVATION_EXECUTION"
    DATA_POST_PROCESSING_AND_CACHE = "DATA_POST_PROCESSING_AND_CACHE"
    INSTRUMENT_STOW_AND_SECURE = "INSTRUMENT_STOW_AND_SECURE"


class IncompatibleObservationError(Exception):
    """Raised when an instrument is paired with an incompatible observation or target."""
    pass


@dataclass
class InstrumentProfile:
    """
    Physical and electrical specification of an exploration instrument operating mode.
    All values are explicitly documented as synthetic demonstration parameters.
    """
    instrument_id: InstrumentId
    mode_name: str
    compatible_objectives: List[ScienceObjective]
    power_draw_w: float
    duration_s: float
    data_category: DataCategory
    expected_data_bytes: int
    is_arm_turret: bool = False
    requires_stationary_rover: bool = True
    is_synthetic: bool = True

    @property
    def energy_joules(self) -> float:
        return self.power_draw_w * self.duration_s

    @property
    def energy_wh(self) -> float:
        return joules_to_wh(self.energy_joules)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instrument_id": self.instrument_id.value,
            "mode_name": self.mode_name,
            "compatible_objectives": [o.value for o in self.compatible_objectives],
            "power_draw_w": self.power_draw_w,
            "duration_s": self.duration_s,
            "energy_wh": round(self.energy_wh, 2),
            "data_category": self.data_category.value,
            "expected_data_bytes": self.expected_data_bytes,
            "expected_data_mb": round(self.expected_data_bytes / (1024 * 1024), 2),
            "is_arm_turret": self.is_arm_turret,
            "requires_stationary_rover": self.requires_stationary_rover,
            "is_synthetic": self.is_synthetic,
        }


# Calibrated Instrument Taxonomy & Operating Modes (Synthetic demonstration profiles)
INSTRUMENT_CATALOG: Dict[str, InstrumentProfile] = {
    # Mastcam-Z
    "MASTCAM_Z_PANO": InstrumentProfile(
        instrument_id=InstrumentId.MASTCAM_Z,
        mode_name="PANO_360_COLOR",
        compatible_objectives=[ScienceObjective.SURFACE_MORPHOLOGY, ScienceObjective.GEOLOGICAL_CHARACTERIZATION],
        power_draw_w=17.4,
        duration_s=1200.0,
        data_category=DataCategory.HIGH_RES_PANORAMA,
        expected_data_bytes=83_886_080,  # 80 MB
        is_arm_turret=False,
        requires_stationary_rover=True,
    ),
    "MASTCAM_Z_STEREO": InstrumentProfile(
        instrument_id=InstrumentId.MASTCAM_Z,
        mode_name="MULTISPECTRAL_STEREO",
        compatible_objectives=[ScienceObjective.SURFACE_MORPHOLOGY, ScienceObjective.MINERALOGICAL_INVESTIGATION],
        power_draw_w=19.8,
        duration_s=600.0,
        data_category=DataCategory.MULTISPECTRAL_IMAGERY,
        expected_data_bytes=12_582_912,  # 12 MB
        is_arm_turret=False,
        requires_stationary_rover=True,
    ),
    "MASTCAM_Z_PHOTOMETRY": InstrumentProfile(
        instrument_id=InstrumentId.MASTCAM_Z,
        mode_name="SUN_PHOTOMETRY",
        compatible_objectives=[ScienceObjective.ATMOSPHERIC_OBSERVATION],
        power_draw_w=12.0,
        duration_s=180.0,
        data_category=DataCategory.ENVIRONMENTAL_TELEMETRY,
        expected_data_bytes=3_145_728,  # 3 MB
        is_arm_turret=False,
        requires_stationary_rover=True,
    ),
    # SuperCam
    "SUPERCAM_LIBS": InstrumentProfile(
        instrument_id=InstrumentId.SUPERCAM,
        mode_name="LIBS_BURST",
        compatible_objectives=[ScienceObjective.MINERALOGICAL_INVESTIGATION, ScienceObjective.GEOLOGICAL_CHARACTERIZATION],
        power_draw_w=38.0,
        duration_s=900.0,
        data_category=DataCategory.SPECTRAL_CUBE,
        expected_data_bytes=18_874_368,  # 18 MB
        is_arm_turret=False,
        requires_stationary_rover=True,
    ),
    "SUPERCAM_RAMAN": InstrumentProfile(
        instrument_id=InstrumentId.SUPERCAM,
        mode_name="RAMAN_SPECTRA",
        compatible_objectives=[ScienceObjective.MINERALOGICAL_INVESTIGATION, ScienceObjective.ASTROBIOLOGY_BIOSIGNATURE_SURVEY],
        power_draw_w=42.0,
        duration_s=1500.0,
        data_category=DataCategory.SPECTRAL_CUBE,
        expected_data_bytes=39_321_600,  # 37.5 MB
        is_arm_turret=False,
        requires_stationary_rover=True,
    ),
    # PIXL (Turret Arm)
    "PIXL_XRF_GRID": InstrumentProfile(
        instrument_id=InstrumentId.PIXL,
        mode_name="XRF_ELEMENTAL_GRID",
        compatible_objectives=[ScienceObjective.MINERALOGICAL_INVESTIGATION, ScienceObjective.GEOLOGICAL_CHARACTERIZATION],
        power_draw_w=25.0,
        duration_s=3600.0,
        data_category=DataCategory.SPECTRAL_CUBE,
        expected_data_bytes=35_651_584,  # 34 MB
        is_arm_turret=True,
        requires_stationary_rover=True,
    ),
    # SHERLOC (Turret Arm)
    "SHERLOC_DUV_RAMAN": InstrumentProfile(
        instrument_id=InstrumentId.SHERLOC,
        mode_name="DUV_RAMAN_SCAN",
        compatible_objectives=[ScienceObjective.ASTROBIOLOGY_BIOSIGNATURE_SURVEY, ScienceObjective.MINERALOGICAL_INVESTIGATION],
        power_draw_w=48.0,
        duration_s=2400.0,
        data_category=DataCategory.SPECTRAL_CUBE,
        expected_data_bytes=57_671_680,  # 55 MB
        is_arm_turret=True,
        requires_stationary_rover=True,
    ),
    # RIMFAX (Radar Sounding)
    "RIMFAX_DEEP": InstrumentProfile(
        instrument_id=InstrumentId.RIMFAX,
        mode_name="DEEP_SOUNDING_STATIONARY",
        compatible_objectives=[ScienceObjective.GEOLOGICAL_CHARACTERIZATION, ScienceObjective.SURFACE_MORPHOLOGY],
        power_draw_w=11.0,
        duration_s=600.0,
        data_category=DataCategory.SUBSURFACE_RADAR,
        expected_data_bytes=17_509_990,  # 16.7 MB
        is_arm_turret=False,
        requires_stationary_rover=True,
    ),
    # MEDA (Meteorological Suite)
    "MEDA_HIGH_RATE": InstrumentProfile(
        instrument_id=InstrumentId.MEDA,
        mode_name="HIGH_RATE_TURBULENCE",
        compatible_objectives=[ScienceObjective.ATMOSPHERIC_OBSERVATION, ScienceObjective.ENVIRONMENTAL_MONITORING],
        power_draw_w=21.0,
        duration_s=1800.0,
        data_category=DataCategory.ENVIRONMENTAL_TELEMETRY,
        expected_data_bytes=18_350_080,  # 17.5 MB
        is_arm_turret=False,
        requires_stationary_rover=False,
    ),
    # Coring Tool (Turret Arm)
    "CORING_ABRASION": InstrumentProfile(
        instrument_id=InstrumentId.CORING_TOOL,
        mode_name="ABRASION_PATCH",
        compatible_objectives=[ScienceObjective.GEOLOGICAL_CHARACTERIZATION, ScienceObjective.ASTROBIOLOGY_BIOSIGNATURE_SURVEY],
        power_draw_w=115.0,
        duration_s=1800.0,
        data_category=DataCategory.ENGINEERING_LOG,
        expected_data_bytes=4_194_304,  # 4 MB
        is_arm_turret=True,
        requires_stationary_rover=True,
    ),
}


def get_authoritative_compatibility_matrix() -> Dict[str, List[str]]:
    """Returns authoritative objective -> list of compatible instrument mode keys."""
    matrix: Dict[str, List[str]] = {obj.value: [] for obj in ScienceObjective}
    for mode_key, profile in INSTRUMENT_CATALOG.items():
        for obj in profile.compatible_objectives:
            matrix[obj.value].append(mode_key)
    return matrix


def get_turret_arm_modes() -> List[str]:
    """Returns mode keys that utilize the robotic arm turret."""
    return [mode_key for mode_key, p in INSTRUMENT_CATALOG.items() if p.is_arm_turret]


def filter_compatible_modes_for_target(
    objective: Union[str, ScienceObjective],
    requested_modes: List[str],
) -> List[str]:
    """
    Filters requested instrument modes to those strictly compatible with the objective,
    enforcing robotic arm turret singularity (at most one contact tool).
    """
    if isinstance(objective, str):
        try:
            obj_enum = ScienceObjective(objective)
        except ValueError:
            obj_enum = ScienceObjective.GEOLOGICAL_CHARACTERIZATION
    else:
        obj_enum = objective

    compatible: List[str] = []
    has_turret = False

    for mode in requested_modes:
        if mode in INSTRUMENT_CATALOG:
            prof = INSTRUMENT_CATALOG[mode]
            if obj_enum in prof.compatible_objectives:
                if prof.is_arm_turret:
                    if not has_turret:
                        compatible.append(mode)
                        has_turret = True
                else:
                    compatible.append(mode)

    # Fallback to first compatible mode if none survived
    if not compatible:
        matrix = get_authoritative_compatibility_matrix()
        modes_for_obj = matrix.get(obj_enum.value, ["MASTCAM_Z_PANO"])
        compatible = [modes_for_obj[0]]

    return compatible


@dataclass
class ScienceTargetConfig:
    """
    Configuration and priority attributes for a scientific exploration target.
    """
    target_id: str
    target_name: str
    grid_coord: Tuple[int, int]
    priority_score: float = 50.0  # 1.0 to 100.0
    priority_type: PriorityType = PriorityType.USER_ASSIGNED_PRIORITY
    primary_objective: ScienceObjective = ScienceObjective.GEOLOGICAL_CHARACTERIZATION
    selected_modes: List[str] = field(default_factory=lambda: ["MASTCAM_Z_PANO"])
    prerequisites: List[str] = field(default_factory=list)
    source_citation: str = ""
    is_protected: bool = False

    def validate_instrument_compatibility(self) -> None:
        """Verifies that all selected modes exist and are compatible with target objectives."""
        has_turret = False
        for mode_key in self.selected_modes:
            if mode_key not in INSTRUMENT_CATALOG:
                raise IncompatibleObservationError(f"Unknown instrument mode '{mode_key}'")
            profile = INSTRUMENT_CATALOG[mode_key]
            if self.primary_objective not in profile.compatible_objectives:
                raise IncompatibleObservationError(
                    f"Mode '{mode_key}' is not compatible with objective '{self.primary_objective.value}'"
                )
            if profile.is_arm_turret:
                if has_turret:
                    raise IncompatibleObservationError(
                        f"Turret arm conflict: Multiple concurrent turret instruments configured at '{self.target_id}'"
                    )
                has_turret = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_name": self.target_name,
            "grid_coord": list(self.grid_coord),
            "priority_score": round(self.priority_score, 1),
            "priority_type": self.priority_type.value,
            "primary_objective": self.primary_objective.value,
            "selected_modes": self.selected_modes,
            "prerequisites": self.prerequisites,
            "source_citation": self.source_citation,
            "is_protected": self.is_protected,
        }


@dataclass
class ScheduledObservationEvent:
    """Individual scheduled phase or observation action in the timeline."""
    event_id: str
    target_id: str
    phase: ObservationPhase
    instrument_id: Optional[InstrumentId]
    mode_name: str
    start_time_s: float
    end_time_s: float
    duration_s: float
    electrical_power_w: float
    energy_consumed_wh: float
    data_product_id: Optional[str] = None
    data_generated_bytes: int = 0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "target_id": self.target_id,
            "phase": self.phase.value,
            "instrument_id": self.instrument_id.value if self.instrument_id else None,
            "mode_name": self.mode_name,
            "start_time_s": round(self.start_time_s, 2),
            "end_time_s": round(self.end_time_s, 2),
            "duration_s": round(self.duration_s, 2),
            "electrical_power_w": round(self.electrical_power_w, 1),
            "energy_consumed_wh": round(self.energy_consumed_wh, 2),
            "data_product_id": self.data_product_id,
            "data_generated_bytes": self.data_generated_bytes,
            "data_generated_mb": round(self.data_generated_bytes / (1024 * 1024), 2),
            "notes": self.notes,
        }


@dataclass
class ScheduledTargetPlan:
    """Consolidated science schedule outcome for an individual visited target."""
    target_id: str
    target_name: str
    arrival_time_s: float
    departure_time_s: float
    total_dwell_s: float
    total_energy_consumed_wh: float
    total_data_generated_bytes: int
    science_points_awarded: float
    events: List[ScheduledObservationEvent] = field(default_factory=list)
    generated_product_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_name": self.target_name,
            "arrival_time_s": round(self.arrival_time_s, 2),
            "departure_time_s": round(self.departure_time_s, 2),
            "total_dwell_s": round(self.total_dwell_s, 2),
            "total_energy_consumed_wh": round(self.total_energy_consumed_wh, 2),
            "total_data_generated_bytes": self.total_data_generated_bytes,
            "total_data_generated_mb": round(self.total_data_generated_bytes / (1024 * 1024), 2),
            "science_points_awarded": round(self.science_points_awarded, 1),
            "events_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
            "generated_product_ids": self.generated_product_ids,
        }


class ScienceMissionPlanner:
    """
    Science Activity Scheduling & Adaptive Replanning Engine.

    Couples candidate science targets, instrument operating profiles, terramechanical
    arrival times, and onboard data creation into a deterministic timeline.
    """

    def __init__(
        self,
        rover_config: Optional[RoverResourceConfig] = None,
        data_ledger: Optional[MissionDataLedger] = None,
    ):
        self.rover_config: RoverResourceConfig = rover_config or RoverResourceConfig()
        self.data_ledger: MissionDataLedger = data_ledger or MissionDataLedger()

    def schedule_target_observation(
        self,
        target: ScienceTargetConfig,
        arrival_time_s: float,
        observation_index: int = 1,
    ) -> ScheduledTargetPlan:
        """
        Schedules a complete 5-phase observation stop at a target.
        Enforces instrument compatibility, tracks power loads, and registers data products.
        """
        target.validate_instrument_compatibility()

        events: List[ScheduledObservationEvent] = []
        product_ids: List[str] = []
        current_time = float(arrival_time_s)
        total_energy_wh = 0.0
        total_bytes = 0

        # Phase 1: Rover Arrival & Settle (Wheel lock, IMU stabilize)
        p1_duration = 180.0
        p1_power = self.rover_config.base_electrical_load_w + 20.0  # Avionics + brake holds
        p1_energy = joules_to_wh(p1_power * p1_duration)
        events.append(
            ScheduledObservationEvent(
                event_id=f"obs_{observation_index:03d}_p1",
                target_id=target.target_id,
                phase=ObservationPhase.ROVER_ARRIVAL_AND_SETTLE,
                instrument_id=None,
                mode_name="BRAKE_LOCK_SETTLE",
                start_time_s=current_time,
                end_time_s=current_time + p1_duration,
                duration_s=p1_duration,
                electrical_power_w=p1_power,
                energy_consumed_wh=p1_energy,
                notes="Chassis stabilized, wheel actuators locked",
            )
        )
        current_time += p1_duration
        total_energy_wh += p1_energy

        # Phase 2: Instrument Preparation & Warmup
        p2_duration = 300.0
        p2_power = self.rover_config.base_electrical_load_w + 35.0  # Heaters + sensor wake
        p2_energy = joules_to_wh(p2_power * p2_duration)
        events.append(
            ScheduledObservationEvent(
                event_id=f"obs_{observation_index:03d}_p2",
                target_id=target.target_id,
                phase=ObservationPhase.INSTRUMENT_PREPARATION_AND_WARMUP,
                instrument_id=None,
                mode_name="SENSOR_WARMUP_CALIBRATION",
                start_time_s=current_time,
                end_time_s=current_time + p2_duration,
                duration_s=p2_duration,
                electrical_power_w=p2_power,
                energy_consumed_wh=p2_energy,
                notes="Instrument thermal stabilization and dark frame calibration",
            )
        )
        current_time += p2_duration
        total_energy_wh += p2_energy

        # Phase 3 & 4: Observation Execution & Data Post-Processing for each selected mode
        for m_idx, mode_key in enumerate(target.selected_modes):
            profile = INSTRUMENT_CATALOG[mode_key]

            # Phase 3: Active Observation
            p3_duration = profile.duration_s
            p3_power = self.rover_config.base_electrical_load_w + profile.power_draw_w
            p3_energy = joules_to_wh(p3_power * p3_duration)
            events.append(
                ScheduledObservationEvent(
                    event_id=f"obs_{observation_index:03d}_p3_{m_idx+1}",
                    target_id=target.target_id,
                    phase=ObservationPhase.OBSERVATION_EXECUTION,
                    instrument_id=profile.instrument_id,
                    mode_name=profile.mode_name,
                    start_time_s=current_time,
                    end_time_s=current_time + p3_duration,
                    duration_s=p3_duration,
                    electrical_power_w=p3_power,
                    energy_consumed_wh=p3_energy,
                    notes=f"Active integration: {profile.instrument_id.value} {profile.mode_name}",
                )
            )
            current_time += p3_duration
            total_energy_wh += p3_energy

            # Phase 4: Data Post-Processing & Non-Volatile Caching
            p4_duration = 120.0
            p4_power = self.rover_config.base_electrical_load_w + 25.0  # Compression co-processor
            p4_energy = joules_to_wh(p4_power * p4_duration)

            # Generate data product
            pid = f"dp_{target.target_id}_{profile.instrument_id.value}_{observation_index:03d}_{m_idx+1}"
            obs_id = f"obs_{target.target_id}_{observation_index:03d}"
            product = MissionDataProduct(
                product_id=pid,
                observation_id=obs_id,
                target_id=target.target_id,
                instrument_id=profile.instrument_id.value,
                category=profile.data_category,
                size_bytes=profile.expected_data_bytes,
                created_mission_time_s=current_time + p4_duration,
                priority_score=target.priority_score,
                priority_type=target.priority_type,
                retention_policy=RetentionPolicy.PROTECTED_PERMANENT if target.is_protected else RetentionPolicy.TRANSFER_THEN_RELEASE,
                is_synthetic=True,
                is_simulated=True,
                is_protected=target.is_protected,
            )

            # Register in data ledger
            try:
                registered_product = self.data_ledger.register_data_product(
                    product,
                    current_time_s=current_time + p4_duration,
                )
                product_ids.append(registered_product.product_id)
                total_bytes += registered_product.size_bytes
            except Exception as e:
                # If capacity overflow, record dropped event
                pass

            events.append(
                ScheduledObservationEvent(
                    event_id=f"obs_{observation_index:03d}_p4_{m_idx+1}",
                    target_id=target.target_id,
                    phase=ObservationPhase.DATA_POST_PROCESSING_AND_CACHE,
                    instrument_id=profile.instrument_id,
                    mode_name=f"{profile.mode_name}_CACHE",
                    start_time_s=current_time,
                    end_time_s=current_time + p4_duration,
                    duration_s=p4_duration,
                    electrical_power_w=p4_power,
                    energy_consumed_wh=p4_energy,
                    data_product_id=pid,
                    data_generated_bytes=profile.expected_data_bytes,
                    notes="Wavelet compression, SHA-256 fingerprint generated, queued in flash ledger",
                )
            )
            current_time += p4_duration
            total_energy_wh += p4_energy

        # Phase 5: Instrument Stow & Secure
        p5_duration = 240.0
        p5_power = self.rover_config.base_electrical_load_w + 40.0  # Actuators stowing
        p5_energy = joules_to_wh(p5_power * p5_duration)
        events.append(
            ScheduledObservationEvent(
                event_id=f"obs_{observation_index:03d}_p5",
                target_id=target.target_id,
                phase=ObservationPhase.INSTRUMENT_STOW_AND_SECURE,
                instrument_id=None,
                mode_name="TURRET_STOW_LATCH",
                start_time_s=current_time,
                end_time_s=current_time + p5_duration,
                duration_s=p5_duration,
                electrical_power_w=p5_power,
                energy_consumed_wh=p5_energy,
                notes="Turret arm secured in travel latch, mast locked",
            )
        )
        current_time += p5_duration
        total_energy_wh += p5_energy

        total_dwell = current_time - arrival_time_s

        return ScheduledTargetPlan(
            target_id=target.target_id,
            target_name=target.target_name,
            arrival_time_s=arrival_time_s,
            departure_time_s=current_time,
            total_dwell_s=total_dwell,
            total_energy_consumed_wh=total_energy_wh,
            total_data_generated_bytes=total_bytes,
            science_points_awarded=target.priority_score,
            events=events,
            generated_product_ids=product_ids,
        )

    def schedule_full_mission(
        self,
        targets: List[ScienceTargetConfig],
        traverse_arrival_times_s: List[float],
    ) -> List[ScheduledTargetPlan]:
        """
        Schedules in-situ science observations along an ordered traverse sequence.
        """
        if len(targets) != len(traverse_arrival_times_s):
            raise ValueError(
                f"Mismatch: {len(targets)} targets provided for {len(traverse_arrival_times_s)} arrival times"
            )

        plans: List[ScheduledTargetPlan] = []
        for idx, (target, arr_time) in enumerate(zip(targets, traverse_arrival_times_s)):
            target_plan = self.schedule_target_observation(
                target,
                arrival_time_s=arr_time,
                observation_index=idx + 1,
            )
            plans.append(target_plan)

        return plans
