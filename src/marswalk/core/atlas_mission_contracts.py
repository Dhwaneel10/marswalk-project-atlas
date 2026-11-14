"""Project Atlas / MarsWalk 2.0 — Milestone 13T
Unified Planetary Mission OS Contracts & Canonical Data Structures.

Provides standardized, serializable data contracts across all integrated domains:
mission intent, campaign phases, assets, science investigations, command packets,
resource balance ledgers, resilience events, and mission dossiers.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MissionStatus(str, Enum):
    PENDING = "PENDING"
    INITIALIZING = "INITIALIZING"
    EXECUTING = "EXECUTING"
    PAUSED = "PAUSED"
    CONTINGENCY_HOLD = "CONTINGENCY_HOLD"
    RECOVERY = "RECOVERY"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class CampaignPhaseType(str, Enum):
    PHASE_A_RECONNAISSANCE = "PHASE_A_RECONNAISSANCE"
    PHASE_B_INFRASTRUCTURE_STAGING = "PHASE_B_INFRASTRUCTURE_STAGING"
    PHASE_C_HABITAT_ACTIVATION = "PHASE_C_HABITAT_ACTIVATION"
    PHASE_D_ISRU_PILOT = "PHASE_D_ISRU_PILOT"
    PHASE_E_DISTRIBUTED_SCIENCE = "PHASE_E_DISTRIBUTED_SCIENCE"
    PHASE_F_AUTONOMOUS_OPERATIONS = "PHASE_F_AUTONOMOUS_OPERATIONS"
    PHASE_G_EXPEDITION_READINESS = "PHASE_G_EXPEDITION_READINESS"


class AssetType(str, Enum):
    GROUND_ROVER = "GROUND_ROVER"
    AERIAL_ROTORCRAFT = "AERIAL_ROTORCRAFT"
    ORBITAL_RELAY = "ORBITAL_RELAY"
    SURFACE_MAST = "SURFACE_MAST"
    POWER_STATION = "POWER_STATION"
    ISRU_PLANT = "ISRU_PLANT"
    HABITAT_CORE = "HABITAT_CORE"
    CONSTRUCTION_BOT = "CONSTRUCTION_BOT"


class AssetHealthState(str, Enum):
    NOMINAL = "NOMINAL"
    DEGRADED = "DEGRADED"
    SAFE_MODE = "SAFE_MODE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"


class TaskState(str, Enum):
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CommandState(str, Enum):
    UPLINK_QUEUED = "UPLINK_QUEUED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    EXECUTED = "EXECUTED"
    REJECTED_STALE_HASH = "REJECTED_STALE_HASH"
    TIMED_OUT = "TIMED_OUT"


class EventType(str, Enum):
    SIMULATION_TICK = "SIMULATION_TICK"
    STATE_UPDATE = "STATE_UPDATE"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    OBSERVATION_ACQUIRED = "OBSERVATION_ACQUIRED"
    COMMAND_DISPATCHED = "COMMAND_DISPATCHED"
    COMM_DELAY_UPDATE = "COMM_DELAY_UPDATE"
    FAULT_INJECTED = "FAULT_INJECTED"
    RECOVERY_INITIATED = "RECOVERY_INITIATED"
    RESOURCE_REBALANCED = "RESOURCE_REBALANCED"
    PHASE_TRANSITION = "PHASE_TRANSITION"
    REPLAY_CHECKPOINT = "REPLAY_CHECKPOINT"


@dataclass
class MissionObjective:
    objective_id: str
    title: str
    raw_intent: str
    target_site_id: str
    target_region: str
    priority: int = 1
    duration_sols: int = 60
    success_criteria: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MissionObjective:
        return cls(**data)


@dataclass
class CampaignTask:
    task_id: str
    phase_id: str
    title: str
    assigned_asset_ids: List[str]
    prerequisites: List[str] = field(default_factory=list)
    state: TaskState = TaskState.QUEUED
    target_location: Optional[Dict[str, float]] = None
    estimated_duration_sols: float = 1.0
    actual_duration_sols: float = 0.0
    power_demand_kw: float = 0.0
    consumables_demand: Dict[str, float] = field(default_factory=dict)
    completion_pct: float = 0.0
    outcome_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["state"] = self.state.value if isinstance(self.state, TaskState) else self.state
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CampaignTask:
        d = dict(data)
        if "state" in d and isinstance(d["state"], str):
            d["state"] = TaskState(d["state"])
        return cls(**d)


@dataclass
class CampaignPhase:
    phase_id: str
    phase_type: CampaignPhaseType
    title: str
    start_sol: int
    end_sol: int
    tasks: List[CampaignTask] = field(default_factory=list)
    is_active: bool = False
    is_completed: bool = False
    completion_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["phase_type"] = self.phase_type.value if isinstance(self.phase_type, CampaignPhaseType) else self.phase_type
        d["tasks"] = [t.to_dict() if hasattr(t, "to_dict") else t for t in self.tasks]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CampaignPhase:
        d = dict(data)
        if "phase_type" in d and isinstance(d["phase_type"], str):
            d["phase_type"] = CampaignPhaseType(d["phase_type"])
        if "tasks" in d:
            d["tasks"] = [CampaignTask.from_dict(t) if isinstance(t, dict) else t for t in d["tasks"]]
        return cls(**d)


@dataclass
class MissionAsset:
    asset_id: str
    name: str
    asset_type: AssetType
    health: AssetHealthState = AssetHealthState.NOMINAL
    location: Dict[str, float] = field(default_factory=lambda: {"lat": 18.4447, "lon": 77.4508, "elevation_m": -2530.0})
    battery_charge_pct: float = 100.0
    power_capacity_kw: float = 5.0
    current_power_consumption_kw: float = 0.5
    current_task_id: Optional[str] = None
    cumulative_distance_m: float = 0.0
    telemetry: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["asset_type"] = self.asset_type.value if isinstance(self.asset_type, AssetType) else self.asset_type
        d["health"] = self.health.value if isinstance(self.health, AssetHealthState) else self.health
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MissionAsset:
        d = dict(data)
        if "asset_type" in d and isinstance(d["asset_type"], str):
            d["asset_type"] = AssetType(d["asset_type"])
        if "health" in d and isinstance(d["health"], str):
            d["health"] = AssetHealthState(d["health"])
        return cls(**d)


@dataclass
class ObservationRecord:
    observation_id: str
    source_asset_id: str
    sol: int
    sol_time: str
    location: Dict[str, float]
    instrument_type: str
    scientific_modality: str
    measurement_data: Dict[str, Any]
    uncertainty: Dict[str, float]
    provenance_hash: str
    shannon_information_gain_bits: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ObservationRecord:
        return cls(**data)


@dataclass
class ScienceInvestigation:
    hypothesis_id: str
    target_feature: str
    statement: str
    prior_probability: float
    posterior_probability: float
    observations: List[str] = field(default_factory=list)
    status: str = "ACTIVE"
    information_entropy_bits: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ScienceInvestigation:
        return cls(**data)


@dataclass
class CommandPacket:
    command_id: str
    target_asset_id: str
    command_action: str
    parameters: Dict[str, Any]
    created_met_seconds: float
    expected_state_hash: str
    state: CommandState = CommandState.UPLINK_QUEUED
    one_way_light_time_seconds: float = 852.0
    dispatch_timestamp_sol: int = 1
    execution_result: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["state"] = self.state.value if isinstance(self.state, CommandState) else self.state
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CommandPacket:
        d = dict(data)
        if "state" in d and isinstance(d["state"], str):
            d["state"] = CommandState(d["state"])
        return cls(**d)


@dataclass
class CommLinkStatus:
    link_id: str
    source_id: str
    target_id: str
    is_line_of_sight: bool
    elevation_angle_deg: float
    signal_to_noise_ratio_db: float
    bandwidth_kbps: float
    owlt_seconds: float
    active_relay_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CommLinkStatus:
        return cls(**data)


@dataclass
class FailureInjection:
    incident_id: str
    affected_subsystem: str
    failure_mode: str
    root_cause: str
    sol_injected: int
    severity: str
    impacted_tasks: List[str] = field(default_factory=list)
    telemetry_signature: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FailureInjection:
        return cls(**data)


@dataclass
class ResilienceResponse:
    incident_id: str
    diagnosis: str
    isolated_components: List[str]
    recovery_strategy: str
    load_shedding_actions: List[str]
    estimated_mttr_sols: float
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResilienceResponse:
        return cls(**data)


@dataclass
class ConstructionJob:
    stage_id: int
    title: str
    worksite: str
    required_blocks: int
    blocks_laid: int
    status: str
    assigned_robots: List[str]
    completion_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConstructionJob:
        return cls(**data)


@dataclass
class ResourceBalanceLedger:
    sol: int
    power_generated_kwe: float
    power_consumed_kwe: float
    power_balance_kwe: float
    battery_soc_pct: float
    water_reserve_kg: float
    oxygen_reserve_kg: float
    methane_caching_kg: float
    sintered_blocks_count: int
    thermal_core_temp_k: float
    mass_conservation_discrepancy_kg: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResourceBalanceLedger:
        return cls(**data)


@dataclass
class StateSnapshot:
    step_index: int
    met_seconds: float
    current_sol: int
    sol_time_str: str
    solar_longitude_ls: float
    state_hash: str
    prev_state_hash: str
    active_phase_id: str
    active_assets_count: int
    health_status: str

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StateSnapshot:
        return cls(**data)


@dataclass
class MissionDossier:
    mission_id: str
    objective_title: str
    total_duration_sols: int
    total_distance_covered_m: float
    total_observations_acquired: int
    hypotheses_validated_count: int
    total_energy_generated_kwh: float
    total_isru_o2_generated_kg: float
    total_isru_blocks_produced: int
    incidents_handled_count: int
    unplanned_loss_events_count: int
    phase_f_readiness_score: float
    cryptographic_replay_valid: bool
    root_hash: str
    provenance_record: Dict[str, Any] = field(default_factory=dict)
    mandatory_scientific_disclosure: str = (
        "NASA Space Apps Scientific Integrity Notice: All modeled routes, life-support "
        "balances, and schedules represent remote-sensing heuristics and computational simulations. "
        "They do not certify physical operational safety for human astronauts."
    )

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MissionDossier:
        return cls(**data)


@dataclass
class UnifiedMission:
    mission_id: str
    objective: MissionObjective
    status: MissionStatus = MissionStatus.PENDING
    current_sol: int = 1
    current_sol_time: str = "06:00:00"
    met_seconds: float = 0.0
    solar_longitude_ls: float = 56.4
    state_hash: str = ""
    phases: List[CampaignPhase] = field(default_factory=list)
    assets: Dict[str, MissionAsset] = field(default_factory=dict)
    investigations: List[ScienceInvestigation] = field(default_factory=list)
    observations: List[ObservationRecord] = field(default_factory=list)
    command_buffer: List[CommandPacket] = field(default_factory=list)
    comm_links: Dict[str, CommLinkStatus] = field(default_factory=dict)
    active_incidents: List[FailureInjection] = field(default_factory=list)
    resilience_responses: List[ResilienceResponse] = field(default_factory=list)
    construction_jobs: List[ConstructionJob] = field(default_factory=list)
    resource_ledgers: List[ResourceBalanceLedger] = field(default_factory=list)
    state_history: List[StateSnapshot] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["status"] = self.status.value if isinstance(self.status, MissionStatus) else self.status
        d["objective"] = self.objective.to_dict() if hasattr(self.objective, "to_dict") else self.objective
        d["phases"] = [p.to_dict() if hasattr(p, "to_dict") else p for p in self.phases]
        d["assets"] = {k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in self.assets.items()}
        d["investigations"] = [i.to_dict() if hasattr(i, "to_dict") else i for i in self.investigations]
        d["observations"] = [o.to_dict() if hasattr(o, "to_dict") else o for o in self.observations]
        d["command_buffer"] = [c.to_dict() if hasattr(c, "to_dict") else c for c in self.command_buffer]
        d["comm_links"] = {k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in self.comm_links.items()}
        d["active_incidents"] = [i.to_dict() if hasattr(i, "to_dict") else i for i in self.active_incidents]
        d["resilience_responses"] = [r.to_dict() if hasattr(r, "to_dict") else r for r in self.resilience_responses]
        d["construction_jobs"] = [j.to_dict() if hasattr(j, "to_dict") else j for j in self.construction_jobs]
        d["resource_ledgers"] = [r.to_dict() if hasattr(r, "to_dict") else r for r in self.resource_ledgers]
        d["state_history"] = [s.to_dict() if hasattr(s, "to_dict") else s for s in self.state_history]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UnifiedMission:
        d = dict(data)
        if "status" in d and isinstance(d["status"], str):
            d["status"] = MissionStatus(d["status"])
        if "objective" in d and isinstance(d["objective"], dict):
            d["objective"] = MissionObjective.from_dict(d["objective"])
        if "phases" in d:
            d["phases"] = [CampaignPhase.from_dict(p) if isinstance(p, dict) else p for p in d["phases"]]
        if "assets" in d:
            d["assets"] = {k: MissionAsset.from_dict(v) if isinstance(v, dict) else v for k, v in d["assets"].items()}
        if "investigations" in d:
            d["investigations"] = [ScienceInvestigation.from_dict(i) if isinstance(i, dict) else i for i in d["investigations"]]
        if "observations" in d:
            d["observations"] = [ObservationRecord.from_dict(o) if isinstance(o, dict) else o for o in d["observations"]]
        if "command_buffer" in d:
            d["command_buffer"] = [CommandPacket.from_dict(c) if isinstance(c, dict) else c for c in d["command_buffer"]]
        if "comm_links" in d:
            d["comm_links"] = {k: CommLinkStatus.from_dict(v) if isinstance(v, dict) else v for k, v in d["comm_links"].items()}
        if "active_incidents" in d:
            d["active_incidents"] = [FailureInjection.from_dict(i) if isinstance(i, dict) else i for i in d["active_incidents"]]
        if "resilience_responses" in d:
            d["resilience_responses"] = [ResilienceResponse.from_dict(r) if isinstance(r, dict) else r for r in d["resilience_responses"]]
        if "construction_jobs" in d:
            d["construction_jobs"] = [ConstructionJob.from_dict(j) if isinstance(j, dict) else j for j in d["construction_jobs"]]
        if "resource_ledgers" in d:
            d["resource_ledgers"] = [ResourceBalanceLedger.from_dict(r) if isinstance(r, dict) else r for r in d["resource_ledgers"]]
        if "state_history" in d:
            d["state_history"] = [StateSnapshot.from_dict(s) if isinstance(s, dict) else s for s in d["state_history"]]
        return cls(**d)
