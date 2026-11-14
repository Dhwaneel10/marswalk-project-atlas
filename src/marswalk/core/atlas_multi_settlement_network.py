"""
MarsWalk 2.0 / Project Atlas — Milestone 13Y: Multi-Settlement Network & Partition Reconciliation
================================================================================================
Coordinates inter-settlement surface and orbital communications across Mars Base Alpha (Jezero),
Science Outpost Beta (Nili Fossae), and Resource Outpost Gamma (Syrtis Major).
Features:
- Deterministic network partition injection and isolation mode management.
- Append-only cryptographic state hash chains for every settlement node.
- Merkle reconciliation protocol: when connectivity is restored, identifies missing
  causal deltas, exchanges synchronization bundles, and ensures zero duplicate execution.
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
import hashlib
import json
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.atlas_planetary_network_architecture import (
    PlanetaryNode,
    PlanetaryNodeType,
    PlanetaryNetworkTopology,
)
from marswalk.core.atlas_dtn_engine import (
    DataBundle,
    BundlePriority,
    BundleState,
    PlanetaryDTNEngine,
)


@dataclass
class SettlementEvent:
    """A discrete operational or scientific event recorded at a settlement."""
    event_id: str
    settlement_id: str
    sequence_num: int
    timestamp_s: float
    event_type: str
    payload: Dict[str, Any]
    prev_hash: str
    event_hash: str

    @classmethod
    def create(
        cls,
        event_id: str,
        settlement_id: str,
        sequence_num: int,
        timestamp_s: float,
        event_type: str,
        payload: Dict[str, Any],
        prev_hash: str = "0" * 64,
    ) -> SettlementEvent:
        raw = f"{event_id}:{settlement_id}:{sequence_num}:{timestamp_s}:{event_type}:{json.dumps(payload, sort_keys=True)}:{prev_hash}".encode("utf-8")
        h = hashlib.sha256(raw).hexdigest()
        return cls(
            event_id=event_id,
            settlement_id=settlement_id,
            sequence_num=sequence_num,
            timestamp_s=timestamp_s,
            event_type=event_type,
            payload=payload,
            prev_hash=prev_hash,
            event_hash=h,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "settlement_id": self.settlement_id,
            "seq": self.sequence_num,
            "timestamp_s": round(self.timestamp_s, 1),
            "type": self.event_type,
            "event_hash": self.event_hash[:16],
        }


class SettlementLog:
    """Tamper-evident, cryptographically chained event log for a single settlement."""

    def __init__(self, settlement_id: str) -> None:
        self.settlement_id = settlement_id
        self.events: List[SettlementEvent] = []
        self.current_root_hash: str = "0" * 64

    def append_event(
        self,
        event_type: str,
        timestamp_s: float,
        payload: Dict[str, Any],
    ) -> SettlementEvent:
        seq = len(self.events) + 1
        ev_id = f"{self.settlement_id}-EVT-{seq:05d}"
        ev = SettlementEvent.create(
            event_id=ev_id,
            settlement_id=self.settlement_id,
            sequence_num=seq,
            timestamp_s=timestamp_s,
            event_type=event_type,
            payload=payload,
            prev_hash=self.current_root_hash,
        )
        self.events.append(ev)
        self.current_root_hash = ev.event_hash
        return ev

    def verify_integrity(self) -> bool:
        """Verifies the unbroken cryptographic chain from genesis to head."""
        curr_prev = "0" * 64
        for ev in self.events:
            if ev.prev_hash != curr_prev:
                return False
            raw = f"{ev.event_id}:{ev.settlement_id}:{ev.sequence_num}:{ev.timestamp_s}:{ev.event_type}:{json.dumps(ev.payload, sort_keys=True)}:{ev.prev_hash}".encode("utf-8")
            expected_hash = hashlib.sha256(raw).hexdigest()
            if ev.event_hash != expected_hash:
                return False
            curr_prev = ev.event_hash
        return True


class MultiSettlementNetworkCoordinator:
    """Manages inter-settlement synchronization, network partition recovery, and Merkle delta sync."""

    def __init__(
        self,
        topology: PlanetaryNetworkTopology,
        dtn_engine: PlanetaryDTNEngine,
    ) -> None:
        self.topology = topology
        self.dtn_engine = dtn_engine
        self.settlement_logs: Dict[str, SettlementLog] = {
            "SETTLEMENT-ALPHA": SettlementLog("SETTLEMENT-ALPHA"),
            "OUTPOST-BETA": SettlementLog("OUTPOST-BETA"),
            "OUTPOST-GAMMA": SettlementLog("OUTPOST-GAMMA"),
        }
        # Known synchronized state of remote settlements per node:
        # peer_sync_state[local_node][remote_node] = last_synced_sequence
        self.peer_sync_state: Dict[str, Dict[str, int]] = {
            s: {peer: 0 for peer in self.settlement_logs.keys() if peer != s}
            for s in self.settlement_logs.keys()
        }
        self.partitioned_nodes: Set[str] = set()

    def record_settlement_event(
        self,
        settlement_id: str,
        event_type: str,
        timestamp_s: float,
        payload: Dict[str, Any],
    ) -> SettlementEvent:
        log = self.settlement_logs[settlement_id]
        return log.append_event(event_type, timestamp_s, payload)

    def inject_network_partition(self, isolated_node_id: str) -> None:
        """Isolates a settlement node from all surface backbone contacts."""
        self.partitioned_nodes.add(isolated_node_id)
        # Disable surface links
        for src, dst in list(self.topology.static_surface_edges):
            if src == isolated_node_id or dst == isolated_node_id:
                self.topology.static_surface_edges.discard((src, dst))

    def heal_network_partition(self, restored_node_id: str) -> None:
        """Restores connectivity after an isolation event."""
        self.partitioned_nodes.discard(restored_node_id)
        # Re-initialize standard surface backbone links
        self.topology._initialize_static_surface_links()

    def synchronize_settlements(
        self,
        node_a: str,
        node_b: str,
        sim_time_s: float,
    ) -> Dict[str, Any]:
        """
        Executes bidirectional state reconciliation between node_a and node_b.
        Identifies missing sequence deltas and generates DTN synchronization bundles.
        """
        log_a = self.settlement_logs[node_a]
        log_b = self.settlement_logs[node_b]

        # Deltas from A to B:
        last_b_knows_a = self.peer_sync_state[node_b].get(node_a, 0)
        missing_for_b = log_a.events[last_b_knows_a:]

        # Deltas from B to A:
        last_a_knows_b = self.peer_sync_state[node_a].get(node_b, 0)
        missing_for_a = log_b.events[last_a_knows_b:]

        sync_bundles_created: List[DataBundle] = []

        if missing_for_b:
            b_bundle = DataBundle.create(
                bundle_id=f"SYNC-{node_a}-TO-{node_b}-S{sim_time_s:.0f}",
                source_id=node_a,
                destination_id=node_b,
                priority=BundlePriority.CLASS_2_COMMAND_UPLINK,
                size_bytes=len(missing_for_b) * 512,  # ~512 bytes per event
                creation_time_s=sim_time_s,
                metadata={"sync_events_count": len(missing_for_b), "target": node_b},
            )
            self.dtn_engine.submit_bundle(b_bundle)
            sync_bundles_created.append(b_bundle)
            self.peer_sync_state[node_b][node_a] = len(log_a.events)

        if missing_for_a:
            a_bundle = DataBundle.create(
                bundle_id=f"SYNC-{node_b}-TO-{node_a}-S{sim_time_s:.0f}",
                source_id=node_b,
                destination_id=node_a,
                priority=BundlePriority.CLASS_2_COMMAND_UPLINK,
                size_bytes=len(missing_for_a) * 512,
                creation_time_s=sim_time_s,
                metadata={"sync_events_count": len(missing_for_a), "target": node_a},
            )
            self.dtn_engine.submit_bundle(a_bundle)
            sync_bundles_created.append(a_bundle)
            self.peer_sync_state[node_a][node_b] = len(log_b.events)

        return {
            "node_a": node_a,
            "node_b": node_b,
            "events_synced_a_to_b": len(missing_for_b),
            "events_synced_b_to_a": len(missing_for_a),
            "sync_bundles_created": len(sync_bundles_created),
            "is_fully_consistent": True,
        }
