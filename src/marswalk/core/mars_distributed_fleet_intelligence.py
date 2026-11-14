"""
MarsWalk 2.0 / Project Atlas — Milestone 13O: Distributed Fleet Intelligence Engine
==================================================================================
Coordinates multi-rover exploration units and relays under intermittent connectivity:
- 2 to 4 rovers (ROVER_ALPHA, ROVER_BRAVO, etc.) with independent physical state and resources.
- Inter-rover (R2R) peer-to-peer telemetry and shared hazard broadcasting.
- Network partition detection, bounded independent operations, and reconnection state reconciliation.
- Detection and resolution of conflicting updates and duplicate events.
"""

from __future__ import annotations

import copy
import dataclasses
import datetime
import enum
import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from marswalk.core.mars_onboard_autonomy import (
    OnboardRoverAutonomyEngine,
    RoverPhysicalState,
    AutonomyOperatingMode,
)


class PartitionStatus(str, enum.Enum):
    """Network partition connectivity state."""
    FULLY_CONNECTED = "FULLY_CONNECTED"
    PARTIALLY_PARTITIONED = "PARTIALLY_PARTITIONED"
    SEVERELY_ISOLATED = "SEVERELY_ISOLATED"
    RECONNECTING_RECONCILING = "RECONNECTING_RECONCILING"


@dataclass
class FleetPeerMessage:
    """Inter-rover peer-to-peer data packet."""
    message_id: str
    sender_rover_id: str
    recipient_rover_id: str  # specific rover or "BROADCAST"
    message_type: str  # HAZARD_ALERT, OBJECTIVE_COMPLETION, RESOURCE_STATUS, RELAY_HEARTBEAT
    payload: Dict[str, Any]
    sent_sim_time_s: float
    state_version: int
    is_delivered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StateReconciliationConflict:
    """Represents a conflicting update detected during partition reconnection."""
    conflict_id: str
    entity_id: str
    field_name: str
    partition_a_value: Any
    partition_b_value: Any
    resolution_status: str  # RESOLVED, UNRESOLVED, REJECTED
    resolved_value: Optional[Any] = None
    resolution_rule: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DistributedFleetIntelligenceManager:
    """
    Manages multi-rover fleet operations, inter-rover telemetry routing,
    network partitions, and post-reconnection state reconciliation.
    """

    def __init__(self, fleet_rover_ids: Optional[List[str]] = None):
        rover_ids = fleet_rover_ids or ["ROVER_ALPHA", "ROVER_BRAVO"]
        self.rovers: Dict[str, OnboardRoverAutonomyEngine] = {
            rid: OnboardRoverAutonomyEngine(rover_id=rid) for rid in rover_ids
        }
        self.peer_message_history: List[FleetPeerMessage] = []
        self.known_shared_hazards: List[Dict[str, Any]] = []
        self.active_partitions: Set[frozenset[str]] = set()  # Sets of mutually connected rovers
        self.partition_status: str = PartitionStatus.FULLY_CONNECTED.value
        self.reconciliation_log: List[StateReconciliationConflict] = []
        self.shared_objectives: Dict[str, Dict[str, Any]] = {
            "OBJ_DELTA_SAMPLING": {"assigned_to": "ROVER_ALPHA", "status": "IN_PROGRESS", "priority": 1},
            "OBJ_CRATER_RIM_SURVEY": {"assigned_to": "ROVER_BRAVO", "status": "IN_PROGRESS", "priority": 2},
        }

    def broadcast_hazard_from_rover(
        self,
        sender_id: str,
        hazard_type: str,
        location_xy: Tuple[float, float],
        severity: str,
        description: str,
        sim_time_s: float,
    ) -> FleetPeerMessage:
        """
        Broadcasts a newly detected hazard from one rover to all reachable peers in its network partition.
        """
        sender_engine = self.rovers.get(sender_id)
        if not sender_engine:
            raise ValueError(f"Rover {sender_id} not registered in fleet")

        # Inject hazard locally first
        hz_id = f"HZ_{sender_id}_{int(sim_time_s)}_{uuid.uuid4().hex[:4].upper()}"
        sender_engine.inject_environmental_hazard(hz_id, hazard_type, location_xy, severity, description)

        payload = {
            "hazard_id": hz_id,
            "hazard_type": hazard_type,
            "location_xy": list(location_xy),
            "severity": severity,
            "description": description,
        }

        msg = FleetPeerMessage(
            message_id=f"MSG_HAZARD_{hz_id}",
            sender_rover_id=sender_id,
            recipient_rover_id="BROADCAST",
            message_type="HAZARD_ALERT",
            payload=payload,
            sent_sim_time_s=sim_time_s,
            state_version=sender_engine.state.state_version,
            is_delivered=False,
        )
        self.peer_message_history.append(msg)

        # Distribute only to rovers in the same network partition!
        for peer_id, peer_engine in self.rovers.items():
            if peer_id == sender_id:
                continue
            if self.are_rovers_connected(sender_id, peer_id):
                peer_engine.inject_environmental_hazard(hz_id, hazard_type, location_xy, severity, description)
                msg.is_delivered = True

        self.known_shared_hazards.append(payload)
        return msg

    def set_network_partition(self, partition_groups: List[List[str]]):
        """
        Simulates network partitioning where rovers in separate groups cannot communicate.
        Example: [["ROVER_ALPHA"], ["ROVER_BRAVO"]] creates complete disconnection.
        """
        self.active_partitions = {frozenset(grp) for grp in partition_groups}
        if len(self.active_partitions) > 1:
            self.partition_status = PartitionStatus.SEVERELY_ISOLATED.value
        else:
            self.partition_status = PartitionStatus.FULLY_CONNECTED.value

    def are_rovers_connected(self, r1: str, r2: str) -> bool:
        """Checks if two rovers share an active communications partition."""
        if not self.active_partitions:
            return True  # Default fully connected
        for grp in self.active_partitions:
            if r1 in grp and r2 in grp:
                return True
        return False

    def reconcile_partition_reconnection(self, sim_time_s: float) -> List[StateReconciliationConflict]:
        """
        Executes deterministic state reconciliation when network partition heals.
        Reconciles known hazards, detects duplicate actions, and audits objective conflicts.
        """
        self.partition_status = PartitionStatus.RECONNECTING_RECONCILING.value
        conflicts: List[StateReconciliationConflict] = []

        # 1. Reconcile known hazards across all rovers (Union of hazards)
        all_hazards_by_id: Dict[str, Dict[str, Any]] = {}
        for r_id, eng in self.rovers.items():
            for hz in eng.state.known_hazards:
                hz_id = hz["hazard_id"]
                if hz_id not in all_hazards_by_id:
                    all_hazards_by_id[hz_id] = hz
                else:
                    # Duplicate hazard verification
                    existing = all_hazards_by_id[hz_id]
                    if existing["location_xy"] != hz["location_xy"]:
                        conf = StateReconciliationConflict(
                            conflict_id=f"CONF_HZ_{hz_id}",
                            entity_id=hz_id,
                            field_name="location_xy",
                            partition_a_value=existing["location_xy"],
                            partition_b_value=hz["location_xy"],
                            resolution_status="RESOLVED",
                            resolved_value=existing["location_xy"],
                            resolution_rule="RULE_ORIGIN_ROVER_AUTHORITY",
                        )
                        conflicts.append(conf)

        # Sync all rovers to complete reconciled hazard catalog
        for eng in self.rovers.values():
            existing_ids = {h["hazard_id"] for h in eng.state.known_hazards}
            for hz_id, hz_data in all_hazards_by_id.items():
                if hz_id not in existing_ids:
                    eng.state.known_hazards.append(copy.deepcopy(hz_data))
                    eng.state.state_version += 1

        # 2. Check for duplicate command execution across rovers
        executed_cmds: Dict[str, str] = {}
        for r_id, eng in self.rovers.items():
            for rec in eng.executed_commands_log:
                cid = rec["command_id"]
                if cid in executed_cmds:
                    conf = StateReconciliationConflict(
                        conflict_id=f"CONF_CMD_DUP_{cid}",
                        entity_id=cid,
                        field_name="execution_rover",
                        partition_a_value=executed_cmds[cid],
                        partition_b_value=r_id,
                        resolution_status="REJECTED",
                        resolved_value=executed_cmds[cid],
                        resolution_rule="RULE_FIRST_EXECUTION_LOCK",
                    )
                    conflicts.append(conf)
                else:
                    executed_cmds[cid] = r_id

        self.reconciliation_log.extend(conflicts)
        self.partition_status = PartitionStatus.FULLY_CONNECTED.value
        self.active_partitions = set()  # Restored full mesh
        return conflicts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fleet_size": len(self.rovers),
            "partition_status": self.partition_status,
            "rovers": {rid: eng.state.to_dict() for rid, eng in self.rovers.items()},
            "shared_objectives": copy.deepcopy(self.shared_objectives),
            "total_shared_hazards": len(self.known_shared_hazards),
            "reconciliation_conflicts_count": len(self.reconciliation_log),
            "reconciliation_conflicts": [c.to_dict() for c in self.reconciliation_log[-5:]],
        }
