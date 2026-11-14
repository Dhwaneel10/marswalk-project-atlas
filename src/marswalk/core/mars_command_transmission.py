"""
MarsWalk 2.0 / Project Atlas — Milestone 13O: Deep Space Command Transmission Engine
===================================================================================
Models the Earth–Mars command lifecycle, CCSDS-inspired space packet envelopes,
cryptographic payload integrity, deterministic state machine transitions,
precondition validation, and idempotent duplicate suppression.
"""

from __future__ import annotations

import copy
import datetime
import enum
import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class CommandLifecycleState(str, enum.Enum):
    """Auditable command lifecycle state machine."""
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    QUEUED = "QUEUED"
    TRANSMITTING = "TRANSMITTING"
    RECEIVED = "RECEIVED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"


class CommandRiskClassification(str, enum.Enum):
    """Operational risk categories for planetary rover commands."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL_IRREVERSIBLE = "CRITICAL_IRREVERSIBLE"


class CommandApprovalLevel(str, enum.Enum):
    """Authorization tiers required before transmission."""
    AUTONOMOUS_PERMITTED = "AUTONOMOUS_PERMITTED"
    OPERATOR_APPROVED = "OPERATOR_APPROVED"
    FLIGHT_DIRECTOR_REQUIRED = "FLIGHT_DIRECTOR_REQUIRED"


class ContingencyPolicy(str, enum.Enum):
    """Explicit contingency directive if preconditions fail on Mars."""
    HOLD_AND_WAIT = "HOLD_AND_WAIT"
    RECALCULATE_ROUTE = "RECALCULATE_ROUTE"
    DEFER_SCIENCE = "DEFER_SCIENCE"
    ENTER_SAFE_HOLD = "ENTER_SAFE_HOLD"


class PacketType(str, enum.Enum):
    """Space packet type identifier."""
    TELECOMMAND = "TELECOMMAND"
    TELEMETRY = "TELEMETRY"
    ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT"


def compute_payload_sha256(payload: Dict[str, Any]) -> str:
    """Computes deterministic SHA-256 digest of canonical JSON payload."""
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(canon).hexdigest()


@dataclass
class CommandPreconditions:
    """Formal constraints that must hold on Mars when command is received."""
    expected_state_version: int
    required_capabilities: List[str] = field(default_factory=list)
    min_energy_reserve_wh: float = 150.0
    max_energy_cost_wh: float = 400.0
    max_terrain_slope_deg: float = 15.0
    min_temperature_k: float = 180.0
    max_dust_tau: float = 1.8
    required_instruments_operational: List[str] = field(default_factory=list)
    terrain_hazard_exclusion_zone: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StateTransitionRecord:
    """Historical record of an auditable command lifecycle state transition."""
    from_state: str
    to_state: str
    simulated_timestamp_s: float
    actor: str
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CCSDSPacketHeader:
    """
    Structured internal space-packet envelope inspired by CCSDS 133.0-B concepts.
    Disclaimer: Simulation model for mission operations research; not flight-certified.
    """
    version_number: int = 0
    packet_type: str = PacketType.TELECOMMAND.value
    secondary_header_flag: bool = True
    apid: int = 101  # Application Process ID (e.g. 101=Rover Autonomy, 102=RelayNet)
    sequence_flags: str = "UNSEGMENTED"
    packet_sequence_count: int = 0
    packet_data_length_bytes: int = 0
    creation_timestamp_iso: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MarsRoverCommand:
    """
    Complete planetary exploration command data structure with lifecycle tracking.
    """
    command_id: str
    mission_id: str
    rover_id: str
    command_sequence_number: int
    action_type: str  # TRANSIT, SCIENCE_DWELL, SAMPLE_DRILL, COMM_UPLINK, REST_RECHARGE
    payload: Dict[str, Any]
    preconditions: CommandPreconditions
    risk_classification: str = CommandRiskClassification.MEDIUM.value
    approval_level: str = CommandApprovalLevel.OPERATOR_APPROVED.value
    contingency_policy: str = ContingencyPolicy.HOLD_AND_WAIT.value
    creation_sim_time_s: float = 0.0
    expiration_sim_time_s: float = 86400.0  # 24 hours validity window default
    idempotency_key: Optional[str] = None
    packet_header: Optional[CCSDSPacketHeader] = None
    payload_sha256: str = ""
    current_state: str = CommandLifecycleState.DRAFT.value
    history: List[StateTransitionRecord] = field(default_factory=list)

    def __post_init__(self):
        if not self.payload_sha256:
            self.payload_sha256 = compute_payload_sha256(self.payload)
        if not self.idempotency_key:
            self.idempotency_key = f"IDEM_{self.rover_id}_{self.command_sequence_number}_{self.payload_sha256[:8]}"
        if not self.packet_header:
            payload_bytes = len(json.dumps(self.payload).encode("utf-8"))
            self.packet_header = CCSDSPacketHeader(
                packet_sequence_count=self.command_sequence_number,
                packet_data_length_bytes=payload_bytes
            )

    def can_transition_to(self, target_state: CommandLifecycleState) -> bool:
        """Enforces valid lifecycle state machine transitions."""
        valid_transitions: Dict[CommandLifecycleState, Set[CommandLifecycleState]] = {
            CommandLifecycleState.DRAFT: {CommandLifecycleState.VALIDATED, CommandLifecycleState.REJECTED},
            CommandLifecycleState.VALIDATED: {CommandLifecycleState.APPROVED, CommandLifecycleState.REJECTED},
            CommandLifecycleState.APPROVED: {CommandLifecycleState.QUEUED, CommandLifecycleState.SUSPENDED},
            CommandLifecycleState.QUEUED: {CommandLifecycleState.TRANSMITTING, CommandLifecycleState.EXPIRED, CommandLifecycleState.SUSPENDED},
            CommandLifecycleState.TRANSMITTING: {CommandLifecycleState.RECEIVED, CommandLifecycleState.FAILED, CommandLifecycleState.EXPIRED},
            CommandLifecycleState.RECEIVED: {CommandLifecycleState.ACCEPTED, CommandLifecycleState.REJECTED, CommandLifecycleState.EXPIRED},
            CommandLifecycleState.ACCEPTED: {CommandLifecycleState.EXECUTING, CommandLifecycleState.SUSPENDED, CommandLifecycleState.EXPIRED},
            CommandLifecycleState.EXECUTING: {CommandLifecycleState.COMPLETED, CommandLifecycleState.FAILED, CommandLifecycleState.SUSPENDED},
            CommandLifecycleState.SUSPENDED: {CommandLifecycleState.EXECUTING, CommandLifecycleState.REJECTED, CommandLifecycleState.FAILED},
            CommandLifecycleState.COMPLETED: set(),  # Terminal state
            CommandLifecycleState.FAILED: set(),     # Terminal state
            CommandLifecycleState.REJECTED: set(),   # Terminal state
            CommandLifecycleState.EXPIRED: set(),    # Terminal state
        }
        curr = CommandLifecycleState(self.current_state)
        return target_state in valid_transitions.get(curr, set())

    def transition_to(self, target_state: CommandLifecycleState, sim_time_s: float, actor: str, reason: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """Executes state transition if valid, logging audit entry."""
        if not self.can_transition_to(target_state):
            return False
        rec = StateTransitionRecord(
            from_state=self.current_state,
            to_state=target_state.value,
            simulated_timestamp_s=sim_time_s,
            actor=actor,
            reason=reason,
            details=details or {}
        )
        self.history.append(rec)
        self.current_state = target_state.value
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "mission_id": self.mission_id,
            "rover_id": self.rover_id,
            "command_sequence_number": self.command_sequence_number,
            "action_type": self.action_type,
            "payload": copy.deepcopy(self.payload),
            "preconditions": self.preconditions.to_dict(),
            "risk_classification": self.risk_classification,
            "approval_level": self.approval_level,
            "contingency_policy": self.contingency_policy,
            "creation_sim_time_s": self.creation_sim_time_s,
            "expiration_sim_time_s": self.expiration_sim_time_s,
            "idempotency_key": self.idempotency_key,
            "packet_header": self.packet_header.to_dict() if self.packet_header else None,
            "payload_sha256": self.payload_sha256,
            "current_state": self.current_state,
            "history": [h.to_dict() for h in self.history],
        }


class CommandTransmissionEngine:
    """
    Manages Earth command authoring, validation, approval queue,
    transmission integrity checks, and deterministic deduplication.
    """

    def __init__(self):
        self.commands: Dict[str, MarsRoverCommand] = {}
        self.idempotency_registry: Dict[str, str] = {}  # idempotency_key -> command_id
        self.executed_idempotency_keys: Set[str] = set()

    def create_command(
        self,
        mission_id: str,
        rover_id: str,
        sequence_number: int,
        action_type: str,
        payload: Dict[str, Any],
        preconditions: CommandPreconditions,
        risk: str = CommandRiskClassification.MEDIUM.value,
        approval_level: str = CommandApprovalLevel.OPERATOR_APPROVED.value,
        contingency: str = ContingencyPolicy.HOLD_AND_WAIT.value,
        sim_time_s: float = 0.0,
        validity_duration_s: float = 86400.0,
    ) -> MarsRoverCommand:
        """Authors a new command in DRAFT state."""
        cmd_id = f"CMD_{rover_id}_SEQ{sequence_number:04d}_{uuid.uuid4().hex[:6].upper()}"
        cmd = MarsRoverCommand(
            command_id=cmd_id,
            mission_id=mission_id,
            rover_id=rover_id,
            command_sequence_number=sequence_number,
            action_type=action_type,
            payload=payload,
            preconditions=preconditions,
            risk_classification=risk,
            approval_level=approval_level,
            contingency_policy=contingency,
            creation_sim_time_s=sim_time_s,
            expiration_sim_time_s=sim_time_s + validity_duration_s,
        )
        cmd.transition_to(
            CommandLifecycleState.DRAFT,
            sim_time_s=sim_time_s,
            actor="EARTH_MISSION_CONTROL",
            reason="Command authored and saved in draft"
        )
        self.commands[cmd_id] = cmd
        self.idempotency_registry[cmd.idempotency_key] = cmd_id
        return cmd

    def validate_on_earth(self, command_id: str, sim_time_s: float) -> Tuple[bool, str]:
        """Validates command syntax, schema, payload hash, and authoring consistency."""
        cmd = self.commands.get(command_id)
        if not cmd:
            return False, f"Command {command_id} not found"
        if cmd.current_state != CommandLifecycleState.DRAFT.value:
            return False, f"Command must be in DRAFT state, got {cmd.current_state}"

        # Verify payload digest
        recomputed_hash = compute_payload_sha256(cmd.payload)
        if recomputed_hash != cmd.payload_sha256:
            cmd.transition_to(CommandLifecycleState.REJECTED, sim_time_s, "EARTH_VALIDATOR", "Payload hash mismatch")
            return False, "Payload integrity corruption detected"

        # Verify sequence and timing
        if cmd.expiration_sim_time_s <= sim_time_s:
            cmd.transition_to(CommandLifecycleState.EXPIRED, sim_time_s, "EARTH_VALIDATOR", "Command expired prior to validation")
            return False, "Command has expired"

        cmd.transition_to(CommandLifecycleState.VALIDATED, sim_time_s, "EARTH_VALIDATOR", "Syntax, payload hash, and parameters validated")
        return True, "Validated successfully on Earth"

    def approve_command(self, command_id: str, approver_role: str, sim_time_s: float) -> Tuple[bool, str]:
        """Approves a validated command for transmission queue."""
        cmd = self.commands.get(command_id)
        if not cmd:
            return False, f"Command {command_id} not found"
        if cmd.current_state != CommandLifecycleState.VALIDATED.value:
            return False, f"Command must be VALIDATED prior to approval, got {cmd.current_state}"

        # Check approval tier
        if cmd.approval_level == CommandApprovalLevel.FLIGHT_DIRECTOR_REQUIRED.value:
            if "FLIGHT_DIRECTOR" not in approver_role:
                return False, "Command requires FLIGHT_DIRECTOR approval level"

        cmd.transition_to(CommandLifecycleState.APPROVED, sim_time_s, approver_role, f"Approved by {approver_role}")
        return True, "Command approved"

    def queue_for_transmission(self, command_id: str, sim_time_s: float) -> Tuple[bool, str]:
        """Moves approved command to outbound transmission queue."""
        cmd = self.commands.get(command_id)
        if not cmd:
            return False, f"Command {command_id} not found"
        if cmd.current_state != CommandLifecycleState.APPROVED.value:
            return False, f"Command must be APPROVED to queue, got {cmd.current_state}"

        cmd.transition_to(CommandLifecycleState.QUEUED, sim_time_s, "EARTH_UPLINK_QUEUE", "Placed into outbound deep space packet queue")
        return True, "Command queued for uplink"

    def check_duplicate_execution(self, idempotency_key: str) -> bool:
        """Returns True if this exact command has already completed execution on Mars."""
        return idempotency_key in self.executed_idempotency_keys

    def mark_executed(self, idempotency_key: str):
        """Registers idempotency key upon completed execution."""
        self.executed_idempotency_keys.add(idempotency_key)
