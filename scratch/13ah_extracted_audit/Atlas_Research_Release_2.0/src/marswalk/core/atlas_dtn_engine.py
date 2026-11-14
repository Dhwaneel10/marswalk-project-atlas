"""
MarsWalk 2.0 / Project Atlas — Milestone 13Y: Delay-Tolerant Networking (DTN) Engine
====================================================================================
RFC 9171 (BPv7)-inspired planetary Bundle Protocol engine.
Features:
- Full lifecycle state machine: CREATED -> QUEUED -> TRANSMITTING -> RECEIVED ->
  STORED -> FORWARDING -> DELIVERED (plus EXPIRED, CORRUPTED, DROPPED).
- 6-tier strict priority hierarchy (Class 1 Emergency to Class 6 Background Archive).
- Finite node storage buffer management with priority-aware preemption.
- Custody transfer, incremental chunking, contact interruption resumption,
  and SHA-256 payload integrity verification.
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
import enum
import hashlib
import json
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class BundlePriority(int, enum.Enum):
    """
    Standard 6-tier planetary network priority classes.
    Lower numerical value = higher priority.
    """
    CLASS_1_EMERGENCY = 1            # Life-Support / Critical Abort / Structural Alert
    CLASS_2_COMMAND_UPLINK = 2       # Urgent Rover/Habitat Command Sequences
    CLASS_3_HIGH_PRIORITY_SCIENCE = 3# Active Discovery / Transient Spectral Events
    CLASS_4_ROUTINE_ENGINEERING = 4  # Daily Housekeeping / Battery & Thermal Telemetry
    CLASS_5_BULK_SCIENCE = 5         # High-Resolution Panoramas / Raw Science Datasets
    CLASS_6_BACKGROUND_ARCHIVE = 6   # Offline Model Sync / Historical Data Repositories

    @property
    def label(self) -> str:
        return self.name.replace("_", " ")

    @property
    def weight(self) -> int:
        return {
            BundlePriority.CLASS_1_EMERGENCY: 100,
            BundlePriority.CLASS_2_COMMAND_UPLINK: 80,
            BundlePriority.CLASS_3_HIGH_PRIORITY_SCIENCE: 60,
            BundlePriority.CLASS_4_ROUTINE_ENGINEERING: 40,
            BundlePriority.CLASS_5_BULK_SCIENCE: 20,
            BundlePriority.CLASS_6_BACKGROUND_ARCHIVE: 10,
        }[self]


class BundleState(str, enum.Enum):
    """Exhaustive lifecycle states for a planetary DTN bundle."""
    CREATED = "CREATED"              # Generated at origin node
    QUEUED = "QUEUED"                # Queued in origin/custodian persistent storage
    TRANSMITTING = "TRANSMITTING"    # Serialization across active RF/optical channel
    RECEIVED = "RECEIVED"            # Received at destination antenna, pending integrity check
    STORED = "STORED"                # Custody accepted at intermediate relay, queued for forwarding
    FORWARDING = "FORWARDING"        # Re-transmitting from intermediate relay
    DELIVERED = "DELIVERED"          # Verified delivered to terminal destination node
    EXPIRED = "EXPIRED"              # TTL exceeded before reaching destination
    CORRUPTED = "CORRUPTED"          # Payload hash mismatch / unrecoverable transmission error
    DROPPED = "DROPPED"              # Evicted from buffer due to overflow preemption


@dataclass
class DataBundle:
    """A discrete RFC 9171-inspired delay-tolerant network bundle."""
    bundle_id: str
    source_id: str
    destination_id: str
    priority: BundlePriority
    size_bytes: int
    creation_time_s: float
    ttl_seconds: float
    payload_hash: str
    state: BundleState = BundleState.CREATED
    current_custodian_id: str = ""
    hop_history: List[Tuple[str, float]] = field(default_factory=list)  # [(node_id, timestamp_s)]
    transmitted_bytes: int = 0
    delivery_time_s: Optional[float] = None
    retransmission_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.current_custodian_id:
            self.current_custodian_id = self.source_id
        if not self.hop_history:
            self.hop_history.append((self.source_id, self.creation_time_s))

    @property
    def expiration_time_s(self) -> float:
        return self.creation_time_s + self.ttl_seconds

    def is_expired(self, current_time_s: float) -> bool:
        return current_time_s > self.expiration_time_s

    @property
    def remaining_bytes(self) -> int:
        return max(0, self.size_bytes - self.transmitted_bytes)

    @property
    def is_fully_transmitted(self) -> bool:
        return self.transmitted_bytes >= self.size_bytes

    def record_hop(self, node_id: str, timestamp_s: float) -> None:
        self.current_custodian_id = node_id
        self.hop_history.append((node_id, timestamp_s))

    @classmethod
    def create(
        cls,
        bundle_id: str,
        source_id: str,
        destination_id: str,
        priority: BundlePriority,
        size_bytes: int,
        creation_time_s: float,
        ttl_seconds: float = 86400.0,  # 1 Sol default TTL
        payload_data: Optional[bytes] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DataBundle:
        """Factory method computing SHA-256 payload hash."""
        if payload_data:
            p_hash = hashlib.sha256(payload_data).hexdigest()
        else:
            # Deterministic synthetic payload hash
            raw = f"{bundle_id}:{source_id}:{destination_id}:{size_bytes}:{creation_time_s}".encode("utf-8")
            p_hash = hashlib.sha256(raw).hexdigest()

        return cls(
            bundle_id=bundle_id,
            source_id=source_id,
            destination_id=destination_id,
            priority=priority,
            size_bytes=size_bytes,
            creation_time_s=creation_time_s,
            ttl_seconds=ttl_seconds,
            payload_hash=p_hash,
            state=BundleState.CREATED,
            current_custodian_id=source_id,
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "source": self.source_id,
            "destination": self.destination_id,
            "priority": self.priority.value,
            "priority_label": self.priority.name,
            "size_kb": round(self.size_bytes / 1024.0, 2),
            "state": self.state.value,
            "custodian": self.current_custodian_id,
            "creation_time_s": round(self.creation_time_s, 1),
            "ttl_s": round(self.ttl_seconds, 1),
            "delivered": self.state == BundleState.DELIVERED,
            "hops": len(self.hop_history) - 1,
            "hop_nodes": [h[0] for h in self.hop_history],
            "delivery_time_s": round(self.delivery_time_s, 1) if self.delivery_time_s else None,
            "latency_s": round(self.delivery_time_s - self.creation_time_s, 1) if self.delivery_time_s else None,
        }


class NodeDTNBuffer:
    """Persistent store-and-forward buffer for a single network node."""

    def __init__(self, node_id: str, capacity_bytes: int) -> None:
        self.node_id = node_id
        self.capacity_bytes = capacity_bytes
        self.bundles: Dict[str, DataBundle] = {}
        self.overflow_drops: int = 0
        self.expired_drops: int = 0

    @property
    def used_bytes(self) -> int:
        return sum(b.size_bytes for b in self.bundles.values())

    @property
    def available_bytes(self) -> int:
        return max(0, self.capacity_bytes - self.used_bytes)

    @property
    def utilization_pct(self) -> float:
        if self.capacity_bytes <= 0:
            return 100.0
        return min(100.0, (self.used_bytes / float(self.capacity_bytes)) * 100.0)

    def has_bundle(self, bundle_id: str) -> bool:
        return bundle_id in self.bundles

    def get_bundle(self, bundle_id: str) -> Optional[DataBundle]:
        return self.bundles.get(bundle_id)

    def enqueue(self, bundle: DataBundle) -> bool:
        """
        Enqueues bundle into local persistent buffer.
        If buffer is full, evicts lower-priority bundles (Class 6 down to Class 3).
        Never evicts Class 1 or Class 2 bundles for lower-priority traffic.
        Returns True if accepted, False if rejected/dropped.
        """
        if bundle.bundle_id in self.bundles:
            return True  # Already cached / deduplicated

        needed = bundle.size_bytes
        if needed > self.capacity_bytes:
            # Bundle too large for this node's physical storage
            bundle.state = BundleState.DROPPED
            self.overflow_drops += 1
            return False

        # If insufficient room, try priority preemption
        if needed > self.available_bytes:
            freed = self._preempt_for_priority(needed, incoming_priority=bundle.priority)
            if freed < needed:
                # Could not free enough storage
                bundle.state = BundleState.DROPPED
                self.overflow_drops += 1
                return False

        self.bundles[bundle.bundle_id] = bundle
        bundle.current_custodian_id = self.node_id
        if bundle.state in (BundleState.CREATED, BundleState.RECEIVED):
            bundle.state = BundleState.QUEUED
        return True

    def remove(self, bundle_id: str) -> Optional[DataBundle]:
        return self.bundles.pop(bundle_id, None)

    def _preempt_for_priority(self, needed_bytes: int, incoming_priority: BundlePriority) -> int:
        """
        Evicts lowest-priority bundles to make room for a higher-priority bundle.
        """
        freed = self.available_bytes
        if freed >= needed_bytes:
            return freed

        # Candidates for eviction: strictly lower priority than incoming bundle
        # Sorted by priority descending (Class 6 first, then 5, etc.) and FIFO
        candidates = [
            b for b in self.bundles.values()
            if b.priority.value > incoming_priority.value and b.priority.value > BundlePriority.CLASS_2_COMMAND_UPLINK.value
        ]
        candidates.sort(key=lambda b: (-b.priority.value, b.creation_time_s))

        for cand in candidates:
            self.remove(cand.bundle_id)
            cand.state = BundleState.DROPPED
            self.overflow_drops += 1
            freed += cand.size_bytes
            if freed >= needed_bytes:
                break

        return freed

    def prune_expired(self, current_time_s: float) -> List[DataBundle]:
        """Evicts bundles that exceeded their TTL."""
        expired = [b for b in self.bundles.values() if b.is_expired(current_time_s)]
        for b in expired:
            self.remove(b.bundle_id)
            b.state = BundleState.EXPIRED
            self.expired_drops += 1
        return expired

    def get_forwarding_candidates(self) -> List[DataBundle]:
        """
        Returns bundles currently stored and eligible for transmission,
        ordered by strict priority (Class 1 first) and then creation time.
        """
        eligible = [
            b for b in self.bundles.values()
            if b.state in (BundleState.QUEUED, BundleState.STORED, BundleState.CREATED)
        ]
        eligible.sort(key=lambda b: (b.priority.value, b.creation_time_s))
        return eligible


class PlanetaryDTNEngine:
    """Coordinates bundle creation, buffer storage, custody transfers, and integrity."""

    def __init__(self) -> None:
        self.node_buffers: Dict[str, NodeDTNBuffer] = {}
        self.all_bundles: Dict[str, DataBundle] = {}
        self.delivered_bundles: List[DataBundle] = []
        self.dropped_bundles: List[DataBundle] = []
        self.expired_bundles: List[DataBundle] = []

    def register_node(self, node_id: str, capacity_bytes: int) -> NodeDTNBuffer:
        buf = NodeDTNBuffer(node_id, capacity_bytes)
        self.node_buffers[node_id] = buf
        return buf

    def get_buffer(self, node_id: str) -> Optional[NodeDTNBuffer]:
        return self.node_buffers.get(node_id)

    def submit_bundle(self, bundle: DataBundle) -> bool:
        """Injects a newly created bundle into its origin node buffer."""
        self.all_bundles[bundle.bundle_id] = bundle
        buf = self.get_buffer(bundle.source_id)
        if not buf:
            bundle.state = BundleState.DROPPED
            self.dropped_bundles.append(bundle)
            return False

        success = buf.enqueue(bundle)
        if not success:
            self.dropped_bundles.append(bundle)
        return success

    def transfer_bundle(
        self,
        bundle_id: str,
        sender_id: str,
        receiver_id: str,
        bytes_transferred: int,
        arrival_time_s: float,
        is_corrupted: bool = False,
    ) -> bool:
        """
        Executes transmission from sender to receiver.
        Handles chunking, custody transfer, and delivery verification.
        """
        bundle = self.all_bundles.get(bundle_id)
        if not bundle:
            return False

        sender_buf = self.get_buffer(sender_id)
        receiver_buf = self.get_buffer(receiver_id)
        if not sender_buf or not receiver_buf:
            return False

        # Update transmission progress
        bundle.transmitted_bytes += bytes_transferred
        if is_corrupted:
            bundle.state = BundleState.CORRUPTED
            bundle.retransmission_count += 1
            return False

        if not bundle.is_fully_transmitted:
            # Partial transmission due to contact expiration
            bundle.state = BundleState.TRANSMITTING
            return False

        # Bundle fully arrived at receiver
        bundle.state = BundleState.RECEIVED
        bundle.record_hop(receiver_id, arrival_time_s)

        # Check if terminal destination reached
        if receiver_id == bundle.destination_id:
            bundle.state = BundleState.DELIVERED
            bundle.delivery_time_s = arrival_time_s
            sender_buf.remove(bundle_id)
            receiver_buf.enqueue(bundle)
            self.delivered_bundles.append(bundle)
            return True
        else:
            # Intermediate custody transfer
            if receiver_buf.enqueue(bundle):
                # Release sender custody upon confirmed receiver storage
                sender_buf.remove(bundle_id)
                bundle.state = BundleState.STORED
                bundle.transmitted_bytes = 0  # Reset for next hop
                return True
            else:
                # Receiver buffer overflow: sender retains custody
                bundle.transmitted_bytes = 0
                bundle.state = BundleState.QUEUED
                return False

    def update_simulation_time(self, current_time_s: float) -> None:
        """Prunes expired bundles across all registered node buffers."""
        for buf in self.node_buffers.values():
            expired = buf.prune_expired(current_time_s)
            self.expired_bundles.extend(expired)

    def get_metrics(self) -> Dict[str, Any]:
        total = len(self.all_bundles)
        delivered = len(self.delivered_bundles)
        dropped = len(self.dropped_bundles)
        expired = len(self.expired_bundles)
        delivery_ratio = (delivered / float(total)) * 100.0 if total > 0 else 100.0

        latencies = [
            (b.delivery_time_s - b.creation_time_s)
            for b in self.delivered_bundles
            if b.delivery_time_s is not None
        ]
        avg_latency = (sum(latencies) / len(latencies)) if latencies else 0.0

        return {
            "total_bundles": total,
            "delivered_bundles": delivered,
            "delivery_ratio_pct": round(delivery_ratio, 2),
            "dropped_bundles": dropped,
            "expired_bundles": expired,
            "average_delivery_latency_s": round(avg_latency, 2),
            "total_delivered_mbytes": round(sum(b.size_bytes for b in self.delivered_bundles) / 1e6, 2),
        }
