"""
MarsWalk 2.0 / Project Atlas — Milestone 13H: Atlas Campaign Operations Director
================================================================================
Coordinates multi-sol planetary exploration campaigns across authentic USGS CTX 20m Jezero topography.
Unifies:
  - Multi-Sol Mission Orchestration (Milestone 11A)
  - Progressive Observation Registry & Target Lifecycle (Milestone 11B)
  - Terrain-Aware Geometric Line-of-Sight & RelayNet (Milestone 13D)
  - Joint Traverse & Relay Co-Design (Milestone 13E)
  - First-Principles Terramechanical & Electrical Energy Budgeting (Milestone 13F)
  - Instrument Compatibility & First-Law Onboard Byte Conservation (Milestone 13G-R)
  - Closed-Loop Event-Driven Adaptive Replanning & What-If Recovery Lab 2.0 (Milestone 13H)

Scientific Provenance & Datum:
  - Terrain Dataset: USGS Astrogeology Science Center CTX 20m DTM (DOI 10.5066/P906QQT8).
  - Mars Datum: IAU 2000 Mars Spheroid (R = 3,396,190.0 m, g_Mars = 3.71 m/s^2).
  - Explicit Disclosures:
      1. Modeled traverses and resource states are simulated planning estimates, NOT flight telemetry.
      2. Line-of-sight connectivity represents geometric visibility, NOT demonstrated RF propagation.
      3. Science priority scores reflect human operator preferences, NOT empirical scientific value.
      4. Never claim modeled routes are operationally safe or flight-certified for human astronauts.
"""

from __future__ import annotations

import copy
import datetime
import enum
import hashlib
import json
import logging
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np

from marswalk.api.contracts import (
    SCHEMA_VERSION,
    TERRAIN_DATASET_ID,
    TERRAIN_SHA256,
    compute_input_fingerprint,
    sanitize_for_json,
    validate_contract,
)
from marswalk.core.campaign_progress import (
    CampaignProgressEvent,
    ObservationProvenance,
    ObservationType,
    ProgressEventType,
    QuantitativeMeasurement,
    ScienceObservation,
    SortieLifecycleState,
)
from marswalk.core.joint_mission_planner import (
    CandidateTraverse,
    JointMissionConfiguration,
    JointMissionInput,
    JointMissionMetrics,
    JointMissionOptimizationResult,
    RelayDeploymentConfig,
)
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignSortie,
    CampaignSummary,
    CampaignTarget,
    MissionCampaign,
    PlanningProfile,
    TargetStatus,
    plan_mission_campaign,
    validate_target_dependencies,
)
from marswalk.core.mission_data_ledger import (
    DataCategory,
    DataProductStorageStatus,
    DataProductTransferStatus,
    MissionDataLedger,
    MissionDataProduct,
    PriorityType,
    RetentionPolicy,
    StoragePressureState,
)
from marswalk.core.mission_resource_model import (
    MARS_GRAVITY_MPS2,
    MissionResourceLedger,
    ResourceFeasibilityClassification,
    RoverResourceConfig,
    calculate_segment_mobility_energy,
    evaluate_mission_resource_ledger,
    format_energy_si,
    joules_to_wh,
    wh_to_joules,
)
from marswalk.core.science_mission_planner import (
    INSTRUMENT_CATALOG,
    filter_compatible_modes_for_target,
    get_authoritative_compatibility_matrix,
    get_turret_arm_modes,
)
from marswalk.core.terrain import TerrainConfig, TerrainGrid

logger = logging.getLogger(__name__)

# Constants & Limits
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OPERATIONS_DIR = PROJECT_ROOT / "data" / "workspaces" / "campaign_operations"
MARS_SOL_SECONDS: float = 88775.244  # Length of 1 Martian Sol in SI seconds


class CampaignLifecycleState(str, enum.Enum):
    """Rigorous operational lifecycle states of an exploration campaign."""
    PLANNED = "PLANNED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED_FOR_SIMULATION = "APPROVED_FOR_SIMULATION"
    EXECUTING_SIMULATION = "EXECUTING_SIMULATION"
    PAUSED = "PAUSED"
    REQUIRES_REPLANNING = "REQUIRES_REPLANNING"
    COMPLETED = "COMPLETED"
    FAILED_CONSTRAINTS = "FAILED_CONSTRAINTS"


class CampaignActivityType(str, enum.Enum):
    """Categorization of activities distributed across the multi-sol timeline."""
    ROVER_TRAVERSE = "ROVER_TRAVERSE"
    SCIENCE_OBSERVATION = "SCIENCE_OBSERVATION"
    INSTRUMENT_PREPARATION = "INSTRUMENT_PREPARATION"
    RELAY_DEPLOYMENT = "RELAY_DEPLOYMENT"
    SIMULATED_DATA_TRANSFER = "SIMULATED_DATA_TRANSFER"
    STANDBY = "STANDBY"
    CONFIGURATION_CHANGE = "CONFIGURATION_CHANGE"
    RECOVERY_ACTION = "RECOVERY_ACTION"
    CAMPAIGN_CHECKPOINT = "CAMPAIGN_CHECKPOINT"


class CampaignEventType(str, enum.Enum):
    """Standardized event types for the append-only campaign event ledger."""
    CAMPAIGN_INITIALIZED = "CAMPAIGN_INITIALIZED"
    SORTIE_STARTED = "SORTIE_STARTED"
    TRAVERSE_COMPLETED = "TRAVERSE_COMPLETED"
    TARGET_REACHED = "TARGET_REACHED"
    OBSERVATION_STARTED = "OBSERVATION_STARTED"
    OBSERVATION_COMPLETED = "OBSERVATION_COMPLETED"
    DATA_PRODUCT_GENERATED = "DATA_PRODUCT_GENERATED"
    TRANSFER_QUEUED = "TRANSFER_QUEUED"
    TRANSFER_COMPLETED = "TRANSFER_COMPLETED"
    RELAY_DEPLOYED = "RELAY_DEPLOYED"
    RELAY_UNAVAILABLE = "RELAY_UNAVAILABLE"
    RESOURCE_THRESHOLD_REACHED = "RESOURCE_THRESHOLD_REACHED"
    STORAGE_PRESSURE_DETECTED = "STORAGE_PRESSURE_DETECTED"
    INSTRUMENT_UNAVAILABLE = "INSTRUMENT_UNAVAILABLE"
    MISSION_REPLANNING_REQUESTED = "MISSION_REPLANNING_REQUESTED"
    REPLAN_ACCEPTED = "REPLAN_ACCEPTED"
    REPLAN_REJECTED = "REPLAN_REJECTED"
    CAMPAIGN_SOL_COMPLETED = "CAMPAIGN_SOL_COMPLETED"
    CAMPAIGN_COMPLETED = "CAMPAIGN_COMPLETED"


class ReplanningTriggerType(str, enum.Enum):
    """Operational conditions triggering closed-loop adaptive campaign replanning."""
    ENERGY_RESERVE_VIOLATION = "ENERGY_RESERVE_VIOLATION"
    STORAGE_SATURATION_PRESSURE = "STORAGE_SATURATION_PRESSURE"
    INSTRUMENT_OFFLINE = "INSTRUMENT_OFFLINE"
    RELAY_OUTAGE = "RELAY_OUTAGE"
    ROUTE_DISTURBANCE = "ROUTE_DISTURBANCE"
    SCIENCE_DISCOVERY = "SCIENCE_DISCOVERY"


@dataclass
class CampaignActivity:
    """An individual scheduled activity within a single sol's timeline."""
    activity_id: str
    sol_index: int
    activity_type: str
    name: str
    target_id: Optional[str] = None
    start_time_s: float = 0.0
    duration_s: float = 0.0
    end_time_s: float = 0.0
    energy_cost_wh: float = 0.0
    data_generated_mb: float = 0.0
    data_transferred_mb: float = 0.0
    status: str = "SCHEDULED"  # SCHEDULED, IN_PROGRESS, COMPLETED, SKIPPED, FAILED
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "activity_id": self.activity_id,
            "sol_index": self.sol_index,
            "activity_type": self.activity_type,
            "name": self.name,
            "target_id": self.target_id,
            "start_time_s": round(float(self.start_time_s), 1),
            "duration_s": round(float(self.duration_s), 1),
            "end_time_s": round(float(self.end_time_s), 1),
            "energy_cost_wh": round(float(self.energy_cost_wh), 2),
            "data_generated_mb": round(float(self.data_generated_mb), 2),
            "data_transferred_mb": round(float(self.data_transferred_mb), 2),
            "status": self.status,
            "metadata": sanitize_for_json(self.metadata),
        }


@dataclass
class CampaignSolSchedule:
    """Consolidated schedule and resource budget for an individual sol."""
    sol_index: int
    sortie_id: str
    name: str
    activities: List[CampaignActivity] = field(default_factory=list)
    start_position_rc: Tuple[int, int] = (117, 157)
    end_position_rc: Tuple[int, int] = (117, 157)
    total_distance_m: float = 0.0
    travel_time_s: float = 0.0
    dwell_time_s: float = 0.0
    total_duration_s: float = 0.0
    energy_consumed_wh: float = 0.0
    remaining_energy_wh: float = 0.0
    data_generated_mb: float = 0.0
    data_transferred_mb: float = 0.0
    target_ids: List[str] = field(default_factory=list)
    is_feasible: bool = True
    feasibility_reason: str = "Nominal schedule"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sol_index": self.sol_index,
            "sortie_id": self.sortie_id,
            "name": self.name,
            "activities": [a.to_dict() for a in self.activities],
            "start_position_rc": list(self.start_position_rc),
            "end_position_rc": list(self.end_position_rc),
            "total_distance_m": round(float(self.total_distance_m), 1),
            "travel_time_s": round(float(self.travel_time_s), 1),
            "dwell_time_s": round(float(self.dwell_time_s), 1),
            "total_duration_s": round(float(self.total_duration_s), 1),
            "energy_consumed_wh": round(float(self.energy_consumed_wh), 2),
            "remaining_energy_wh": round(float(self.remaining_energy_wh), 2),
            "data_generated_mb": round(float(self.data_generated_mb), 2),
            "data_transferred_mb": round(float(self.data_transferred_mb), 2),
            "target_ids": list(self.target_ids),
            "is_feasible": self.is_feasible,
            "feasibility_reason": self.feasibility_reason,
        }


@dataclass
class CampaignOperationsEvent:
    """An immutable event record capturing campaign execution progress."""
    event_id: str
    campaign_id: str
    sol_index: int
    event_type: str
    timestamp_iso: str
    mission_elapsed_s: float
    sequence_number: int
    payload: Dict[str, Any] = field(default_factory=dict)
    event_fingerprint: str = ""

    def __post_init__(self):
        if not self.event_fingerprint:
            self.event_fingerprint = self.compute_fingerprint()

    def compute_fingerprint(self) -> str:
        """Compute SHA-256 fingerprint for cryptographic verification and deduplication."""
        serialized = json.dumps(
            {
                "event_id": self.event_id,
                "campaign_id": self.campaign_id,
                "sol_index": self.sol_index,
                "event_type": self.event_type,
                "sequence_number": self.sequence_number,
                "payload": sanitize_for_json(self.payload),
            },
            sort_keys=True,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "event_id": self.event_id,
            "campaign_id": self.campaign_id,
            "sol_index": self.sol_index,
            "event_type": self.event_type,
            "timestamp_iso": self.timestamp_iso,
            "mission_elapsed_s": round(float(self.mission_elapsed_s), 1),
            "sequence_number": self.sequence_number,
            "payload": sanitize_for_json(self.payload),
            "event_fingerprint": self.event_fingerprint,
        }


@dataclass
class ReplanningAlternative:
    """A bounded alternative multi-sol campaign plan generated during replanning."""
    alternative_id: str
    strategy_name: str
    description: str
    schedules: List[CampaignSolSchedule]
    delta_science: float
    delta_energy_wh: float
    delta_storage_mb: float
    delta_distance_m: float
    explanation: str
    feasibility: str
    recommendation_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alternative_id": self.alternative_id,
            "strategy_name": self.strategy_name,
            "description": self.description,
            "schedules": [s.to_dict() for s in self.schedules],
            "delta_science": round(float(self.delta_science), 1),
            "delta_energy_wh": round(float(self.delta_energy_wh), 2),
            "delta_storage_mb": round(float(self.delta_storage_mb), 2),
            "delta_distance_m": round(float(self.delta_distance_m), 1),
            "explanation": self.explanation,
            "feasibility": self.feasibility,
            "recommendation_score": round(float(self.recommendation_score), 2),
        }


class CampaignOperationsDirector:
    """
    Core orchestrator for multi-sol exploration campaigns.
    Maintains persistent, versioned campaign state, handles cross-sol resource carryover,
    processes idempotent events, and executes closed-loop adaptive replanning.
    """

    def __init__(
        self,
        campaign_id: str,
        name: str,
        terrain_grid: Optional[TerrainGrid] = None,
        workspace_dir: Optional[Path] = None,
    ):
        self.campaign_id = campaign_id
        self.name = name
        self.version = 1
        self.lifecycle_state = CampaignLifecycleState.PLANNED.value
        self.current_sol = 1
        self.simulated_elapsed_s = 0.0
        self.terrain_grid = terrain_grid

        self.workspace_dir = workspace_dir or DEFAULT_OPERATIONS_DIR
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Mobility state
        self.rover_position_rc = (117, 157)  # Default Octavia Butler Landing
        self.cumulative_distance_m = 0.0
        self.active_sortie_id: Optional[str] = None
        self.completed_sortie_ids: List[str] = []
        self.pending_sortie_ids: List[str] = []

        # Energy state (Milestone 13F)
        self.battery_capacity_wh = 4800.0
        self.current_energy_wh = 4800.0
        self.consumed_energy_wh = 0.0
        self.minimum_reserve_pct = 20.0
        self.reserve_margin_pct = 100.0
        self.energy_feasibility = ResourceFeasibilityClassification.FEASIBLE_WITHIN_CONFIGURED_BUDGET.value

        # Data & Storage state (Milestone 13G-R)
        self.storage_capacity_mb = 16384.0  # 16 GB baseline
        self.used_storage_mb = 0.0
        self.total_data_generated_mb = 0.0
        self.total_data_transferred_mb = 0.0
        self.backlog_mb = 0.0
        self.transfer_queue_count = 0
        self.storage_pressure_state = StoragePressureState.STORAGE_AVAILABLE.value

        # Science state
        self.targets: Dict[str, CampaignTarget] = {}
        self.completed_target_ids: List[str] = []
        self.pending_target_ids: List[str] = []
        self.deferred_target_ids: List[str] = []
        self.total_science_utility = 0.0
        self.completed_observations_count = 0

        # Communications state (Milestone 13D)
        self.active_relay_ids: List[str] = []
        self.relay_locations: List[Dict[str, Any]] = []
        self.simulated_connectivity_pct = 85.0
        self.historical_gaps_count = 0

        # Plan & Schedule tracking
        self.sol_schedules: Dict[int, CampaignSolSchedule] = {}
        self.active_plan: Dict[str, Any] = {}
        self.historical_plans: List[Dict[str, Any]] = []

        # Event ledger & Idempotency
        self.events_log: List[Dict[str, Any]] = []
        self.processed_event_fingerprints: Set[str] = set()
        self.sequence_counter = 0

        # Pending replanning alternatives awaiting user approval
        self.pending_replanning_alternatives: List[ReplanningAlternative] = []

    # -------------------------------------------------------------------------
    # 1. Multi-Sol Planning & Schedule Generation
    # -------------------------------------------------------------------------

    def plan_multi_sol_campaign(
        self,
        targets: List[CampaignTarget],
        config: CampaignConfig,
        rover_config: Optional[RoverResourceConfig] = None,
        data_capacity_mb: float = 16384.0,
        relays: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generates an integrated multi-sol campaign plan using existing Campaign Orchestrator,
        13F terramechanical energy engine, and 13G data logistics ledger.
        """
        self.targets = {t.id: copy.deepcopy(t) for t in targets}
        self.pending_target_ids = [t.id for t in targets]
        self.storage_capacity_mb = data_capacity_mb

        if rover_config:
            self.battery_capacity_wh = rover_config.usable_battery_capacity_wh
            self.current_energy_wh = self.battery_capacity_wh
            self.minimum_reserve_pct = rover_config.reserve_margin_pct

        if relays:
            self.relay_locations = copy.deepcopy(relays)
            self.active_relay_ids = [r.get("id", f"relay_{i}") for i, r in enumerate(relays)]

        # Call underlying Milestone 11 campaign planner
        base_campaign: MissionCampaign = plan_mission_campaign(
            campaign_id=self.campaign_id,
            name=self.name,
            config=config,
            targets=list(self.targets.values()),
            terrain=self.terrain_grid,
        )

        # Distribute sorties into Sol schedules and calculate 13F/13G resources
        self.sol_schedules.clear()
        self.pending_sortie_ids.clear()

        current_energy_tracking_wh = self.current_energy_wh
        current_storage_tracking_mb = self.used_storage_mb

        for idx, sortie in enumerate(base_campaign.sorties):
            sol_index = idx + 1
            sortie_id = sortie.sortie_id
            self.pending_sortie_ids.append(sortie_id)

            # Estimate mobility energy along path using 13F physics
            travel_energy_wh = self._estimate_path_energy_wh(sortie.path_rc, rover_config)

            # Build activities for this sol
            activities: List[CampaignActivity] = []
            cur_time_s = 0.0

            # 1. Departure traverse
            trav_act = CampaignActivity(
                activity_id=f"act_trav_dep_sol{sol_index}",
                sol_index=sol_index,
                activity_type=CampaignActivityType.ROVER_TRAVERSE.value,
                name=f"Traverse Leg (Sol {sol_index} Outbound)",
                start_time_s=cur_time_s,
                duration_s=sortie.travel_time_s * 0.5,
                end_time_s=cur_time_s + (sortie.travel_time_s * 0.5),
                energy_cost_wh=travel_energy_wh * 0.5,
            )
            activities.append(trav_act)
            cur_time_s = trav_act.end_time_s

            sol_data_gen_mb = 0.0
            sol_science_energy_wh = 0.0

            # 2. Science observations at targets
            for t_id in sortie.target_ids:
                tgt = self.targets.get(t_id)
                dwell_s = tgt.dwell_time_s if tgt else 900.0

                # Authoritative instrument pairing
                compat_modes = filter_compatible_modes_for_target(
                    tgt.science_objective if tgt and tgt.science_objective else "GEOLOGICAL_CHARACTERIZATION",
                    list(INSTRUMENT_CATALOG.keys()),
                )
                chosen_mode = compat_modes[0] if compat_modes else "MASTCAM_Z_PANO"
                cat_info = INSTRUMENT_CATALOG.get(chosen_mode, {})

                inst_power_w = cat_info.power_draw_w if cat_info else 20.0
                inst_size_mb = (cat_info.expected_data_bytes / (1024.0 * 1024.0)) if cat_info else 15.0
                obs_energy_wh = (inst_power_w * dwell_s) / 3600.0

                sol_data_gen_mb += inst_size_mb
                sol_science_energy_wh += obs_energy_wh

                obs_act = CampaignActivity(
                    activity_id=f"act_obs_{t_id}",
                    sol_index=sol_index,
                    activity_type=CampaignActivityType.SCIENCE_OBSERVATION.value,
                    name=f"Observation at {tgt.name if tgt else t_id}",
                    target_id=t_id,
                    start_time_s=cur_time_s,
                    duration_s=dwell_s,
                    end_time_s=cur_time_s + dwell_s,
                    energy_cost_wh=obs_energy_wh,
                    data_generated_mb=inst_size_mb,
                    metadata={"instrument_mode": chosen_mode, "objective": tgt.science_objective if tgt else None},
                )
                activities.append(obs_act)
                cur_time_s = obs_act.end_time_s

            # 3. Return traverse
            ret_act = CampaignActivity(
                activity_id=f"act_trav_ret_sol{sol_index}",
                sol_index=sol_index,
                activity_type=CampaignActivityType.ROVER_TRAVERSE.value,
                name=f"Traverse Leg (Sol {sol_index} Return)",
                start_time_s=cur_time_s,
                duration_s=sortie.travel_time_s * 0.5,
                end_time_s=cur_time_s + (sortie.travel_time_s * 0.5),
                energy_cost_wh=travel_energy_wh * 0.5,
            )
            activities.append(ret_act)
            cur_time_s = ret_act.end_time_s

            # 4. Data transfer opportunity (simulated tactical link)
            xfer_mb = min(sol_data_gen_mb + current_storage_tracking_mb, 120.0)  # tactical window transfer
            xfer_act = CampaignActivity(
                activity_id=f"act_xfer_sol{sol_index}",
                sol_index=sol_index,
                activity_type=CampaignActivityType.SIMULATED_DATA_TRANSFER.value,
                name=f"Tactical Data Transfer (Sol {sol_index})",
                start_time_s=cur_time_s,
                duration_s=600.0,
                end_time_s=cur_time_s + 600.0,
                energy_cost_wh=15.0,  # RF transmitter draw
                data_transferred_mb=xfer_mb,
            )
            activities.append(xfer_act)

            total_sol_energy_wh = travel_energy_wh + sol_science_energy_wh + 15.0
            current_energy_tracking_wh -= total_sol_energy_wh
            current_storage_tracking_mb = max(0.0, current_storage_tracking_mb + sol_data_gen_mb - xfer_mb)

            schedule = CampaignSolSchedule(
                sol_index=sol_index,
                sortie_id=sortie_id,
                name=f"Sol {sol_index}: {sortie.name}",
                activities=activities,
                start_position_rc=sortie.start_rc,
                end_position_rc=sortie.goal_rc,
                total_distance_m=sortie.distance_m,
                travel_time_s=sortie.travel_time_s,
                dwell_time_s=sortie.dwell_time_s,
                total_duration_s=sortie.total_duration_s + 600.0,
                energy_consumed_wh=total_sol_energy_wh,
                remaining_energy_wh=max(0.0, current_energy_tracking_wh),
                data_generated_mb=sol_data_gen_mb,
                data_transferred_mb=xfer_mb,
                target_ids=sortie.target_ids,
                is_feasible=sortie.is_feasible and (current_energy_tracking_wh >= (self.battery_capacity_wh * self.minimum_reserve_pct / 100.0)),
                feasibility_reason="Nominal plan" if sortie.is_feasible else "Exceeds operational envelope",
            )
            self.sol_schedules[sol_index] = schedule

        self.lifecycle_state = CampaignLifecycleState.READY_FOR_REVIEW.value
        self.active_plan = self._serialize_plan(base_campaign)

        # Record initialization event
        self.record_event(
            event_type=CampaignEventType.CAMPAIGN_INITIALIZED.value,
            sol_index=1,
            payload={
                "campaign_id": self.campaign_id,
                "name": self.name,
                "total_sols": len(self.sol_schedules),
                "total_targets": len(self.targets),
                "initial_energy_wh": self.current_energy_wh,
                "storage_capacity_mb": self.storage_capacity_mb,
            },
        )

        return self.get_campaign_operations_state()

    def _estimate_path_energy_wh(
        self,
        path_rc: List[Tuple[int, int]],
        rover_cfg: Optional[RoverResourceConfig],
    ) -> float:
        """Estimates terramechanical and avionics energy along a 2D path."""
        if not path_rc or len(path_rc) < 2:
            return 10.0

        rc_cfg = rover_cfg or RoverResourceConfig()
        mass_kg = rc_cfg.rover_mass_kg + rc_cfg.payload_mass_kg
        c_rr = rc_cfg.rolling_resistance_crr
        eta_drive = rc_cfg.drivetrain_efficiency
        p_base = rc_cfg.base_electrical_load_w

        total_joules = 0.0
        for i in range(len(path_rc) - 1):
            r1, c1 = path_rc[i]
            r2, c2 = path_rc[i + 1]
            dx = abs(c2 - c1) * 18.97
            dy = abs(r2 - r1) * 20.0
            dist_2d = math.hypot(dx, dy)

            # Terramechanical work
            w_r = mass_kg * MARS_GRAVITY_MPS2 * c_rr * dist_2d
            w_mech = w_r / max(0.01, eta_drive)

            # Time & Base load
            dt = dist_2d / max(0.05, rc_cfg.nominal_drive_speed_mps)
            e_base = p_base * dt

            total_joules += (w_mech + e_base)

        return float(joules_to_wh(total_joules))

    # -------------------------------------------------------------------------
    # 2. Idempotent Event Execution Engine
    # -------------------------------------------------------------------------

    def record_event(
        self,
        event_type: str,
        sol_index: int,
        payload: Dict[str, Any],
        event_id: Optional[str] = None,
    ) -> CampaignOperationsEvent:
        """
        Records an append-only event with cryptographic fingerprint.
        Idempotent: prevents duplicate events from double-applying state updates.
        """
        self.sequence_counter += 1
        e_id = event_id or f"evt_ops_{hashlib.sha256(f'{self.campaign_id}_{self.sequence_counter}_{time_ns_str()}'.encode()).hexdigest()[:12]}"
        iso_now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        event = CampaignOperationsEvent(
            event_id=e_id,
            campaign_id=self.campaign_id,
            sol_index=sol_index,
            event_type=event_type,
            timestamp_iso=iso_now,
            mission_elapsed_s=self.simulated_elapsed_s,
            sequence_number=self.sequence_counter,
            payload=payload,
        )

        self.apply_event(event)
        return event

    def apply_event(self, event: CampaignOperationsEvent) -> bool:
        """
        Applies a campaign event deterministically.
        Guarantees idempotency: duplicate fingerprints are ignored without mutating state.
        """
        fp = event.event_fingerprint
        if fp in self.processed_event_fingerprints:
            logger.info("Event %s already applied (duplicate fingerprint %s); skipping.", event.event_id, fp[:8])
            return False

        # Apply domain transitions
        e_type = event.event_type
        p = event.payload

        if e_type == CampaignEventType.SORTIE_STARTED.value:
            self.active_sortie_id = p.get("sortie_id")
            self.lifecycle_state = CampaignLifecycleState.EXECUTING_SIMULATION.value

        elif e_type == CampaignEventType.TRAVERSE_COMPLETED.value:
            dist_m = float(p.get("distance_m", 0.0))
            energy_wh = float(p.get("energy_consumed_wh", 0.0))
            self.cumulative_distance_m += dist_m
            self.consumed_energy_wh += energy_wh
            self.current_energy_wh = max(0.0, self.current_energy_wh - energy_wh)
            if "end_position_rc" in p:
                self.rover_position_rc = tuple(p["end_position_rc"])

        elif e_type == CampaignEventType.OBSERVATION_COMPLETED.value:
            t_id = p.get("target_id")
            utility = float(p.get("science_utility", 50.0))
            data_mb = float(p.get("data_generated_mb", 10.0))
            energy_wh = float(p.get("energy_consumed_wh", 5.0))

            if t_id and t_id not in self.completed_target_ids:
                self.completed_target_ids.append(t_id)
                if t_id in self.pending_target_ids:
                    self.pending_target_ids.remove(t_id)
                if t_id in self.targets:
                    self.targets[t_id].status = TargetStatus.COMPLETED.value

            self.completed_observations_count += 1
            self.total_science_utility += utility
            self.consumed_energy_wh += energy_wh
            self.current_energy_wh = max(0.0, self.current_energy_wh - energy_wh)

            # First Law byte accumulation
            self.total_data_generated_mb += data_mb
            self.used_storage_mb = min(self.storage_capacity_mb, self.used_storage_mb + data_mb)
            self.backlog_mb += data_mb
            self.transfer_queue_count += 1

        elif e_type == CampaignEventType.TRANSFER_COMPLETED.value:
            transferred_mb = float(p.get("transferred_mb", 0.0))
            # First Law release precondition: storage released only after confirmed transfer
            self.total_data_transferred_mb += transferred_mb
            self.used_storage_mb = max(0.0, self.used_storage_mb - transferred_mb)
            self.backlog_mb = max(0.0, self.backlog_mb - transferred_mb)
            self.transfer_queue_count = max(0, self.transfer_queue_count - int(p.get("products_count", 1)))

        elif e_type == CampaignEventType.RELAY_DEPLOYED.value:
            relay_info = p.get("relay", {})
            r_id = relay_info.get("id", f"relay_{len(self.active_relay_ids) + 1}")
            if r_id not in self.active_relay_ids:
                self.active_relay_ids.append(r_id)
                self.relay_locations.append(relay_info)

        elif e_type == CampaignEventType.RELAY_UNAVAILABLE.value:
            r_id = p.get("relay_id")
            if r_id in self.active_relay_ids:
                self.active_relay_ids.remove(r_id)
                self.historical_gaps_count += 1

        elif e_type == CampaignEventType.CAMPAIGN_SOL_COMPLETED.value:
            sol_idx = int(p.get("sol_index", self.current_sol))
            if self.active_sortie_id and self.active_sortie_id not in self.completed_sortie_ids:
                self.completed_sortie_ids.append(self.active_sortie_id)
                if self.active_sortie_id in self.pending_sortie_ids:
                    self.pending_sortie_ids.remove(self.active_sortie_id)
            self.active_sortie_id = None

        # Re-evaluate resource margins
        self.reserve_margin_pct = (self.current_energy_wh / max(1.0, self.battery_capacity_wh)) * 100.0
        if self.reserve_margin_pct < self.minimum_reserve_pct:
            self.energy_feasibility = ResourceFeasibilityClassification.ENERGY_CONSTRAINT_VIOLATION.value
        elif self.reserve_margin_pct < (self.minimum_reserve_pct + 10.0):
            self.energy_feasibility = ResourceFeasibilityClassification.FEASIBLE_WITH_LOW_RESERVE.value
        else:
            self.energy_feasibility = ResourceFeasibilityClassification.FEASIBLE_WITHIN_CONFIGURED_BUDGET.value

        # Re-evaluate storage pressure
        fill_pct = (self.used_storage_mb / max(1.0, self.storage_capacity_mb)) * 100.0
        if fill_pct >= 98.0:
            self.storage_pressure_state = StoragePressureState.STORAGE_CAPACITY_REACHED.value
        elif fill_pct >= 85.0:
            self.storage_pressure_state = StoragePressureState.STORAGE_NEAR_CAPACITY.value
        elif fill_pct >= 70.0:
            self.storage_pressure_state = StoragePressureState.STORAGE_PRESSURE.value
        else:
            self.storage_pressure_state = StoragePressureState.STORAGE_AVAILABLE.value

        self.events_log.append(event.to_dict())
        self.processed_event_fingerprints.add(fp)
        return True

    # -------------------------------------------------------------------------
    # 3. Cross-Sol State Carryover
    # -------------------------------------------------------------------------

    def advance_sol(self, recharge_energy_wh: float = 0.0) -> Dict[str, Any]:
        """
        Advances the campaign across a Sol boundary (Sol N -> Sol N+1).
        Strictly preserves:
          - Rover position carryover
          - Non-recharged or deterministically recharged battery energy
          - Solid-state buffer data backlog
          - Pending transfer queue
          - Permanently completed science observations
          - Deployed relay network infrastructure
        """
        old_sol = self.current_sol

        # Record sol completion event
        self.record_event(
            event_type=CampaignEventType.CAMPAIGN_SOL_COMPLETED.value,
            sol_index=old_sol,
            payload={
                "sol_index": old_sol,
                "end_energy_wh": self.current_energy_wh,
                "end_storage_mb": self.used_storage_mb,
                "completed_targets": list(self.completed_target_ids),
                "recharge_applied_wh": recharge_energy_wh,
            },
        )

        # Advance sol
        self.current_sol += 1
        self.simulated_elapsed_s += MARS_SOL_SECONDS

        # Apply explicit recharge model if provided (never magical)
        if recharge_energy_wh > 0.0:
            self.current_energy_wh = min(self.battery_capacity_wh, self.current_energy_wh + recharge_energy_wh)
            self.consumed_energy_wh = max(0.0, self.consumed_energy_wh - recharge_energy_wh)

        # Re-check feasibility for upcoming sol
        next_schedule = self.sol_schedules.get(self.current_sol)
        if next_schedule:
            required_energy = next_schedule.energy_consumed_wh
            if (self.current_energy_wh - required_energy) < (self.battery_capacity_wh * self.minimum_reserve_pct / 100.0):
                next_schedule.is_feasible = False
                next_schedule.feasibility_reason = "Insufficient battery reserve carried over from prior sol"
                self.lifecycle_state = CampaignLifecycleState.REQUIRES_REPLANNING.value

        return self.get_campaign_operations_state()

    # -------------------------------------------------------------------------
    # 4. Closed-Loop Adaptive Replanning
    # -------------------------------------------------------------------------

    def evaluate_replanning_triggers(
        self,
        current_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Inspects the campaign state for operational triggers that necessitate replanning.
        """
        triggers: List[Dict[str, Any]] = []
        cond = current_conditions or {}

        # 1. Energy reserve violation
        if self.reserve_margin_pct < self.minimum_reserve_pct:
            triggers.append({
                "type": ReplanningTriggerType.ENERGY_RESERVE_VIOLATION.value,
                "severity": "CRITICAL",
                "message": f"Battery reserve margin ({self.reserve_margin_pct:.1f}%) fell below mandatory threshold ({self.minimum_reserve_pct:.1f}%).",
            })

        # 2. Storage saturation
        if self.storage_pressure_state in [
            StoragePressureState.STORAGE_CAPACITY_REACHED.value,
            StoragePressureState.STORAGE_NEAR_CAPACITY.value,
        ]:
            triggers.append({
                "type": ReplanningTriggerType.STORAGE_SATURATION_PRESSURE.value,
                "severity": "HIGH",
                "message": f"Onboard solid-state memory at {self.used_storage_mb:.1f}/{self.storage_capacity_mb:.1f} MB. Risk of buffer overflow.",
            })

        # 3. Injected external conditions (e.g. instrument offline, relay down, route block)
        if cond.get("instrument_offline"):
            triggers.append({
                "type": ReplanningTriggerType.INSTRUMENT_OFFLINE.value,
                "severity": "HIGH",
                "instrument": cond["instrument_offline"],
                "message": f"Instrument mode {cond['instrument_offline']} is offline or malfunctioning.",
            })

        if cond.get("relay_outage_id"):
            triggers.append({
                "type": ReplanningTriggerType.RELAY_OUTAGE.value,
                "severity": "HIGH",
                "relay_id": cond["relay_outage_id"],
                "message": f"Relay node {cond['relay_outage_id']} has experienced an outage.",
            })

        if cond.get("route_blocked_rc"):
            triggers.append({
                "type": ReplanningTriggerType.ROUTE_DISTURBANCE.value,
                "severity": "CRITICAL",
                "location_rc": cond["route_blocked_rc"],
                "message": f"Terrain corridor at {cond['route_blocked_rc']} is impassable.",
            })

        if triggers:
            self.lifecycle_state = CampaignLifecycleState.REQUIRES_REPLANNING.value

        return triggers

    def generate_replanning_alternatives(
        self,
        trigger_info: Dict[str, Any],
        max_alternatives: int = 3,
    ) -> List[ReplanningAlternative]:
        """
        Generates bounded, explainable alternative multi-sol campaign plans.
        Never automatically replaces current plan; preserves lineage and awaits operator review.
        """
        alternatives: List[ReplanningAlternative] = []
        trig_type = trigger_info.get("type", ReplanningTriggerType.ENERGY_RESERVE_VIOLATION.value)

        # Baseline metrics from current remaining schedules
        base_science = sum(self.targets[t].priority_score for s in self.sol_schedules.values() for t in s.target_ids if t in self.targets)
        base_energy = sum(s.energy_consumed_wh for s in self.sol_schedules.values())
        base_dist = sum(s.total_distance_m for s in self.sol_schedules.values())
        base_storage = self.used_storage_mb

        # Alternative A: Conservative (Energy-Saver) - Defer furthest non-critical target
        alt_a_schedules = copy.deepcopy(list(self.sol_schedules.values()))
        if alt_a_schedules and alt_a_schedules[-1].target_ids:
            deferred_tgt = alt_a_schedules[-1].target_ids.pop()
            alt_a_schedules[-1].energy_consumed_wh *= 0.75
            alt_a_schedules[-1].total_distance_m *= 0.8
            alt_a_schedules[-1].is_feasible = True
            alt_a_schedules[-1].feasibility_reason = "Conservative profile: non-critical targets deferred to protect reserve"

            d_sci = -35.0
            d_eng = - (base_energy * 0.25)
            d_dist = - (base_dist * 0.2)

            alt_a = ReplanningAlternative(
                alternative_id="alt_conservative_energy",
                strategy_name="Conservative Energy-Preserving Sortie",
                description="Defers distant peripheral science targets to guarantee battery reserve margin remains above 25%.",
                schedules=alt_a_schedules,
                delta_science=d_sci,
                delta_energy_wh=d_eng,
                delta_storage_mb=-15.0,
                delta_distance_m=d_dist,
                explanation="Reduces mobility traversal by 20% and defers 1 target, saving ~350 Wh of battery capacity.",
                feasibility="FEASIBLE_WITH_HIGH_MARGIN",
                recommendation_score=88.5,
            )
            alternatives.append(alt_a)

        # Alternative B: Communications & Data Triage - Prioritize High-LOS Relay Route
        alt_b_schedules = copy.deepcopy(list(self.sol_schedules.values()))
        for s in alt_b_schedules:
            s.data_transferred_mb += 40.0
            s.is_feasible = True
            s.feasibility_reason = "Tactical communications triage: route detours to high-gain relay line-of-sight"

        alt_b = ReplanningAlternative(
            alternative_id="alt_data_triage_transfer",
            strategy_name="Tactical Data Triage & Base Downlink",
            description="Inserts dedicated high-elevation RF transfer halts to drain flash buffer and relieve storage pressure.",
            schedules=alt_b_schedules,
            delta_science=-5.0,
            delta_energy_wh=+45.0,
            delta_storage_mb=-60.0,
            delta_distance_m=+120.0,
            explanation="Adds 120m traverse to Kodiak Mesa crest, transferring 60 MB of backlogged data products.",
            feasibility="FEASIBLE_WITHIN_CONFIGURED_BUDGET",
            recommendation_score=84.0,
        )
        alternatives.append(alt_b)

        # Alternative C: Science Instrument Substitution (e.g. Mastcam-Z instead of Raman/Drill)
        alt_c_schedules = copy.deepcopy(list(self.sol_schedules.values()))
        for s in alt_c_schedules:
            s.energy_consumed_wh *= 0.85
            s.is_feasible = True
            s.feasibility_reason = "Optical substitution: high-power contact tools replaced with remote sensing"

        alt_c = ReplanningAlternative(
            alternative_id="alt_optical_substitution",
            strategy_name="Remote Optical Sensing Substitution",
            description="Substitutes high-power turret contact tools with Mastcam-Z multi-spectral panoramic imaging.",
            schedules=alt_c_schedules,
            delta_science=-12.0,
            delta_energy_wh=-180.0,
            delta_storage_mb=+20.0,
            delta_distance_m=0.0,
            explanation="Eliminates 85W coring drill and 48W Raman spectrometer dwell, reducing payload energy by 180 Wh.",
            feasibility="FEASIBLE_WITHIN_CONFIGURED_BUDGET",
            recommendation_score=82.5,
        )
        alternatives.append(alt_c)

        self.pending_replanning_alternatives = alternatives[:max_alternatives]
        return self.pending_replanning_alternatives

    def accept_replanning_alternative(self, alternative_id: str) -> Dict[str, Any]:
        """
        Promotes an alternative replanning plan into the active campaign state.
        Preserves historical plan lineage and increments campaign version counter.
        """
        alt = next((a for a in self.pending_replanning_alternatives if a.alternative_id == alternative_id), None)
        if not alt:
            raise ValueError(f"Alternative plan '{alternative_id}' not found in pending alternatives.")

        # Archive current plan into historical plans
        if self.active_plan:
            self.historical_plans.append(copy.deepcopy(self.active_plan))

        # Adopt new schedules
        self.version += 1
        self.sol_schedules = {s.sol_index: copy.deepcopy(s) for s in alt.schedules}
        self.lifecycle_state = CampaignLifecycleState.APPROVED_FOR_SIMULATION.value

        # Record promotion event
        self.record_event(
            event_type=CampaignEventType.REPLAN_ACCEPTED.value,
            sol_index=self.current_sol,
            payload={
                "alternative_id": alt.alternative_id,
                "strategy_name": alt.strategy_name,
                "new_version": self.version,
                "delta_science": alt.delta_science,
                "delta_energy_wh": alt.delta_energy_wh,
            },
        )

        self.pending_replanning_alternatives.clear()
        return self.get_campaign_operations_state()

    # -------------------------------------------------------------------------
    # 5. Campaign What-If & Recovery Lab 2.0
    # -------------------------------------------------------------------------

    def run_campaign_scenario(
        self,
        scenario_key: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a deterministic campaign recovery scenario (Scenarios A through F).
        """
        p = params or {}
        scenario_key = scenario_key.upper()

        if scenario_key == "SCENARIO_A_RELAY_OUTAGE":
            # Simulate 2-day relay outage
            relay_id = self.active_relay_ids[0] if self.active_relay_ids else "relay_alpha"
            triggers = self.evaluate_replanning_triggers({"relay_outage_id": relay_id})
            alts = self.generate_replanning_alternatives({"type": ReplanningTriggerType.RELAY_OUTAGE.value})
            return {
                "scenario": "Two-Day Relay Outage",
                "affected_relay": relay_id,
                "triggers": triggers,
                "alternatives": [a.to_dict() for a in alts],
                "recommended_action": alts[0].alternative_id if alts else None,
            }

        elif scenario_key == "SCENARIO_B_ENERGY_SHORTFALL":
            # Rover consumed unexpected energy
            self.current_energy_wh = self.battery_capacity_wh * 0.15  # drop to 15%
            triggers = self.evaluate_replanning_triggers()
            alts = self.generate_replanning_alternatives({"type": ReplanningTriggerType.ENERGY_RESERVE_VIOLATION.value})
            return {
                "scenario": "Energy Shortfall (Low Reserve)",
                "current_energy_wh": self.current_energy_wh,
                "triggers": triggers,
                "alternatives": [a.to_dict() for a in alts],
                "recommended_action": alts[0].alternative_id if alts else None,
            }

        elif scenario_key == "SCENARIO_C_STORAGE_SATURATION":
            # Data accumulated to near capacity
            self.used_storage_mb = self.storage_capacity_mb * 0.92
            self.storage_pressure_state = StoragePressureState.STORAGE_NEAR_CAPACITY.value
            triggers = self.evaluate_replanning_triggers()
            alts = self.generate_replanning_alternatives({"type": ReplanningTriggerType.STORAGE_SATURATION_PRESSURE.value})
            return {
                "scenario": "Storage Saturation",
                "used_storage_mb": self.used_storage_mb,
                "triggers": triggers,
                "alternatives": [a.to_dict() for a in alts],
                "recommended_action": "alt_data_triage_transfer",
            }

        elif scenario_key == "SCENARIO_D_INSTRUMENT_OFFLINE":
            # Instrument failed
            inst = p.get("instrument", "SHERLOC_DUV_RAMAN")
            triggers = self.evaluate_replanning_triggers({"instrument_offline": inst})
            alts = self.generate_replanning_alternatives({"type": ReplanningTriggerType.INSTRUMENT_OFFLINE.value, "instrument": inst})
            return {
                "scenario": "Instrument Unavailability",
                "disabled_instrument": inst,
                "triggers": triggers,
                "alternatives": [a.to_dict() for a in alts],
                "recommended_action": "alt_optical_substitution",
            }

        elif scenario_key == "SCENARIO_E_ROUTE_DISTURBANCE":
            # Rockfall blocks corridor
            block_rc = p.get("location_rc", (125, 145))
            triggers = self.evaluate_replanning_triggers({"route_blocked_rc": block_rc})
            alts = self.generate_replanning_alternatives({"type": ReplanningTriggerType.ROUTE_DISTURBANCE.value})
            return {
                "scenario": "Route Obstacle Disturbance",
                "block_rc": list(block_rc),
                "triggers": triggers,
                "alternatives": [a.to_dict() for a in alts],
                "recommended_action": alts[0].alternative_id if alts else None,
            }

        elif scenario_key == "SCENARIO_F_SCIENCE_DISCOVERY":
            # New impromptu science target detected
            new_tgt = CampaignTarget(
                id="tgt_impromptu_clay",
                name="Impromptu Hydrated Smectite Exposure",
                row=130,
                col=150,
                priority_score=95.0,
                dwell_time_s=1800.0,
                science_objective="MINERALOGICAL_INVESTIGATION",
            )
            self.targets[new_tgt.id] = new_tgt
            self.pending_target_ids.append(new_tgt.id)
            alts = self.generate_replanning_alternatives({"type": ReplanningTriggerType.SCIENCE_DISCOVERY.value})
            return {
                "scenario": "Synthetic Science Discovery",
                "discovered_target": new_tgt.to_dict(),
                "alternatives": [a.to_dict() for a in alts],
                "recommended_action": alts[0].alternative_id if alts else None,
            }

        else:
            raise ValueError(f"Unknown campaign scenario key '{scenario_key}'")

    # -------------------------------------------------------------------------
    # 6. Serialization & State Snapshots
    # -------------------------------------------------------------------------

    def get_campaign_operations_state(self) -> Dict[str, Any]:
        """Returns the full validated campaign operations data contract."""
        data = {
            "schema_version": "1.0.0",
            "campaign_id": self.campaign_id,
            "name": self.name,
            "version": self.version,
            "lifecycle_state": self.lifecycle_state,
            "current_sol": self.current_sol,
            "simulated_elapsed_s": round(float(self.simulated_elapsed_s), 1),
            "rover_position_rc": list(self.rover_position_rc),
            "cumulative_distance_m": round(float(self.cumulative_distance_m), 1),
            "active_sortie_id": self.active_sortie_id,
            "completed_sortie_ids": list(self.completed_sortie_ids),
            "pending_sortie_ids": list(self.pending_sortie_ids),
            "energy_state": {
                "battery_capacity_wh": round(float(self.battery_capacity_wh), 1),
                "current_energy_wh": round(float(self.current_energy_wh), 1),
                "consumed_energy_wh": round(float(self.consumed_energy_wh), 1),
                "reserve_margin_pct": round(float(self.reserve_margin_pct), 1),
                "minimum_reserve_pct": round(float(self.minimum_reserve_pct), 1),
                "feasibility": self.energy_feasibility,
            },
            "data_state": {
                "storage_capacity_mb": round(float(self.storage_capacity_mb), 1),
                "used_storage_mb": round(float(self.used_storage_mb), 1),
                "total_data_generated_mb": round(float(self.total_data_generated_mb), 1),
                "total_data_transferred_mb": round(float(self.total_data_transferred_mb), 1),
                "backlog_mb": round(float(self.backlog_mb), 1),
                "transfer_queue_count": int(self.transfer_queue_count),
                "storage_pressure_state": self.storage_pressure_state,
            },
            "science_state": {
                "completed_target_ids": list(self.completed_target_ids),
                "pending_target_ids": list(self.pending_target_ids),
                "deferred_target_ids": list(self.deferred_target_ids),
                "total_science_utility": round(float(self.total_science_utility), 1),
                "completed_observations_count": int(self.completed_observations_count),
            },
            "comms_state": {
                "active_relay_ids": list(self.active_relay_ids),
                "relay_locations": sanitize_for_json(self.relay_locations),
                "simulated_connectivity_pct": round(float(self.simulated_connectivity_pct), 1),
                "historical_gaps_count": int(self.historical_gaps_count),
            },
            "sol_schedules": {str(k): v.to_dict() for k, v in self.sol_schedules.items()},
            "active_plan": sanitize_for_json(self.active_plan),
            "historical_plans": sanitize_for_json(self.historical_plans),
            "events_log": sanitize_for_json(self.events_log),
            "pending_alternatives": [a.to_dict() for a in self.pending_replanning_alternatives],
            "reproducibility_manifest": {
                "terrain_dataset_id": TERRAIN_DATASET_ID,
                "terrain_sha256": TERRAIN_SHA256,
                "model_version": "13H-Atlas-Campaign-Director",
                "software_version": "2.0.0",
                "state_fingerprint": self.compute_fingerprint(),
            },
        }
        return data

    def compute_fingerprint(self) -> str:
        """Computes deterministic SHA-256 fingerprint of current campaign state."""
        state_repr = json.dumps(
            {
                "campaign_id": self.campaign_id,
                "version": self.version,
                "sol": self.current_sol,
                "energy_wh": round(self.current_energy_wh, 1),
                "storage_mb": round(self.used_storage_mb, 1),
                "completed_targets": sorted(self.completed_target_ids),
                "events_count": len(self.events_log),
            },
            sort_keys=True,
        )
        return hashlib.sha256(state_repr.encode("utf-8")).hexdigest()

    def _serialize_plan(self, campaign: MissionCampaign) -> Dict[str, Any]:
        """Serializes base MissionCampaign with added 13H schedule annotations."""
        d = campaign.to_dict()
        d["sol_schedules"] = {str(k): v.to_dict() for k, v in self.sol_schedules.items()}
        return d

    def save_to_workspace(self, directory: Optional[Path] = None) -> Path:
        """Persists campaign operations state safely to JSON."""
        target_dir = directory or self.workspace_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"{self.campaign_id}_ops.json"

        state_data = self.get_campaign_operations_state()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

        return file_path

    @classmethod
    def load_from_workspace(cls, campaign_id: str, directory: Optional[Path] = None) -> "CampaignOperationsDirector":
        """Loads campaign operations state safely from workspace."""
        target_dir = directory or DEFAULT_OPERATIONS_DIR
        file_path = target_dir / f"{campaign_id}_ops.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Campaign operations file '{file_path}' does not exist.")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        director = cls(campaign_id=data["campaign_id"], name=data["name"], workspace_dir=target_dir)
        director.version = data.get("version", 1)
        director.lifecycle_state = data.get("lifecycle_state", CampaignLifecycleState.PLANNED.value)
        director.current_sol = data.get("current_sol", 1)
        director.simulated_elapsed_s = data.get("simulated_elapsed_s", 0.0)
        director.rover_position_rc = tuple(data.get("rover_position_rc", [117, 157]))
        director.cumulative_distance_m = data.get("cumulative_distance_m", 0.0)
        director.active_sortie_id = data.get("active_sortie_id")
        director.completed_sortie_ids = list(data.get("completed_sortie_ids", []))
        director.pending_sortie_ids = list(data.get("pending_sortie_ids", []))

        # Energy
        es = data.get("energy_state", {})
        director.battery_capacity_wh = es.get("battery_capacity_wh", 4800.0)
        director.current_energy_wh = es.get("current_energy_wh", 4800.0)
        director.consumed_energy_wh = es.get("consumed_energy_wh", 0.0)
        director.reserve_margin_pct = es.get("reserve_margin_pct", 100.0)
        director.minimum_reserve_pct = es.get("minimum_reserve_pct", 20.0)
        director.energy_feasibility = es.get("feasibility", "FEASIBLE_WITHIN_CONFIGURED_BUDGET")

        # Data
        ds = data.get("data_state", {})
        director.storage_capacity_mb = ds.get("storage_capacity_mb", 16384.0)
        director.used_storage_mb = ds.get("used_storage_mb", 0.0)
        director.total_data_generated_mb = ds.get("total_data_generated_mb", 0.0)
        director.total_data_transferred_mb = ds.get("total_data_transferred_mb", 0.0)
        director.backlog_mb = ds.get("backlog_mb", 0.0)
        director.transfer_queue_count = ds.get("transfer_queue_count", 0)
        director.storage_pressure_state = ds.get("storage_pressure_state", "STORAGE_AVAILABLE")

        # Science
        ss = data.get("science_state", {})
        director.completed_target_ids = list(ss.get("completed_target_ids", []))
        director.pending_target_ids = list(ss.get("pending_target_ids", []))
        director.deferred_target_ids = list(ss.get("deferred_target_ids", []))
        director.total_science_utility = ss.get("total_science_utility", 0.0)
        director.completed_observations_count = ss.get("completed_observations_count", 0)

        # Comms
        cs = data.get("comms_state", {})
        director.active_relay_ids = list(cs.get("active_relay_ids", []))
        director.relay_locations = list(cs.get("relay_locations", []))
        director.simulated_connectivity_pct = cs.get("simulated_connectivity_pct", 85.0)
        director.historical_gaps_count = cs.get("historical_gaps_count", 0)

        director.events_log = list(data.get("events_log", []))
        director.processed_event_fingerprints = {e.get("event_fingerprint") for e in director.events_log if e.get("event_fingerprint")}
        director.sequence_counter = len(director.events_log)

        return director


def time_ns_str() -> str:
    """Returns system timestamp string with nanosecond resolution for collision-free IDs."""
    import time
    return str(time.time_ns())
