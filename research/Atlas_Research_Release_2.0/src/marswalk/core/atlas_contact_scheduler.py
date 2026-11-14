"""
MarsWalk 2.0 / Project Atlas — Milestone 13Y: Contact Plan Schedulers
=====================================================================
Suite of 6 competing contact plan scheduling algorithms for Martian DTN:
1. GREEDY (First Available Contact)
2. EARLIEST_DELIVERY (Contact Graph Routing / Space-Time Dijkstra)
3. PRIORITY_FIRST (Strict Priority Class Queuing)
4. DEADLINE_AWARE (Earliest Deadline First / Remaining TTL)
5. RESOURCE_AWARE (Energy & Buffer Conservation)
6. ATLAS_ADAPTIVE (Multi-Objective Dynamic Optimization)
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
import enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.atlas_orbital_contact_planner import ContactWindow
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
from marswalk.core.atlas_planetary_routing import (
    TimeDependentContactRouter,
    ContactRoute,
)


class SchedulerType(str, enum.Enum):
    """The six competing scheduling algorithms."""
    GREEDY = "SCHED-01-GREEDY"
    EARLIEST_DELIVERY = "SCHED-02-EARLIEST-DELIVERY"
    PRIORITY_FIRST = "SCHED-03-PRIORITY-FIRST"
    DEADLINE_AWARE = "SCHED-04-DEADLINE-AWARE"
    RESOURCE_AWARE = "SCHED-05-RESOURCE-AWARE"
    ATLAS_ADAPTIVE = "SCHED-06-ATLAS-ADAPTIVE"


@dataclass
class ScheduledTransmission:
    """A scheduled transmission task binding a bundle to a contact window."""
    bundle_id: str
    contact_id: str
    sender_id: str
    receiver_id: str
    start_time_s: float
    end_time_s: float
    duration_s: float
    rate_bps: int
    bytes_allocated: int
    priority: BundlePriority
    scheduler_type: SchedulerType
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "contact_id": self.contact_id,
            "sender": self.sender_id,
            "receiver": self.receiver_id,
            "start_time_s": round(self.start_time_s, 1),
            "end_time_s": round(self.end_time_s, 1),
            "duration_s": round(self.duration_s, 1),
            "rate_kbps": round(self.rate_bps / 1000.0, 1),
            "bytes_allocated": self.bytes_allocated,
            "priority": self.priority.value,
            "scheduler": self.scheduler_type.value,
            "rationale": self.rationale,
        }


class BaseContactScheduler:
    """Base class for all contact scheduling algorithms."""

    def __init__(self, scheduler_type: SchedulerType, topology: PlanetaryNetworkTopology) -> None:
        self.scheduler_type = scheduler_type
        self.topology = topology
        self.router = TimeDependentContactRouter(topology)

    def schedule(
        self,
        current_time_s: float,
        bundles: List[DataBundle],
        contact_windows: List[ContactWindow],
        dtn_engine: PlanetaryDTNEngine,
    ) -> List[ScheduledTransmission]:
        raise NotImplementedError


class GreedyScheduler(BaseContactScheduler):
    """
    SCHED-01-GREEDY: Immediately assigns bundles to whichever contact window opens first,
    ordered purely by bundle arrival/creation time (FIFO).
    """

    def __init__(self, topology: PlanetaryNetworkTopology) -> None:
        super().__init__(SchedulerType.GREEDY, topology)

    def schedule(
        self,
        current_time_s: float,
        bundles: List[DataBundle],
        contact_windows: List[ContactWindow],
        dtn_engine: PlanetaryDTNEngine,
    ) -> List[ScheduledTransmission]:
        transmissions: List[ScheduledTransmission] = []
        # Filter active or upcoming contact windows
        valid_cw = [cw for cw in contact_windows if cw.end_time_s > current_time_s]
        valid_cw.sort(key=lambda cw: cw.start_time_s)

        # Track contact window remaining capacity in bytes
        cw_cap: Dict[str, int] = {cw.contact_id: cw.total_capacity_bytes for cw in valid_cw}
        cw_end: Dict[str, float] = {cw.contact_id: cw.start_time_s for cw in valid_cw}

        # Greedy FIFO bundle sorting
        pending = [b for b in bundles if b.state in (BundleState.QUEUED, BundleState.CREATED, BundleState.STORED)]
        pending.sort(key=lambda b: b.creation_time_s)

        for b in pending:
            sender = b.current_custodian_id
            for cw in valid_cw:
                # Must be usable by sender
                if cw.src_node_id != sender and (not cw.is_bidirectional or cw.dst_node_id != sender):
                    continue
                receiver = cw.dst_node_id if cw.src_node_id == sender else cw.src_node_id
                rem_cap = cw_cap[cw.contact_id]
                if rem_cap <= 0:
                    continue

                tx_bytes = min(b.remaining_bytes, rem_cap)
                tx_dur = (tx_bytes * 8.0) / float(cw.achievable_rate_bps)
                cur_start = max(current_time_s, cw_end[cw.contact_id])
                if cur_start + tx_dur > cw.end_time_s:
                    continue

                transmissions.append(
                    ScheduledTransmission(
                        bundle_id=b.bundle_id,
                        contact_id=cw.contact_id,
                        sender_id=sender,
                        receiver_id=receiver,
                        start_time_s=cur_start,
                        end_time_s=cur_start + tx_dur,
                        duration_s=tx_dur,
                        rate_bps=cw.achievable_rate_bps,
                        bytes_allocated=tx_bytes,
                        priority=b.priority,
                        scheduler_type=self.scheduler_type,
                        rationale="First available contact with capacity",
                    )
                )
                cw_cap[cw.contact_id] -= tx_bytes
                cw_end[cw.contact_id] = cur_start + tx_dur
                break

        return transmissions


class EarliestDeliveryScheduler(BaseContactScheduler):
    """
    SCHED-02-EARLIEST-DELIVERY: Uses Contact Graph Routing to find the multi-hop path
    minimizing end-to-end arrival timestamp at destination.
    """

    def __init__(self, topology: PlanetaryNetworkTopology) -> None:
        super().__init__(SchedulerType.EARLIEST_DELIVERY, topology)

    def schedule(
        self,
        current_time_s: float,
        bundles: List[DataBundle],
        contact_windows: List[ContactWindow],
        dtn_engine: PlanetaryDTNEngine,
    ) -> List[ScheduledTransmission]:
        transmissions: List[ScheduledTransmission] = []
        pending = [b for b in bundles if b.state in (BundleState.QUEUED, BundleState.CREATED, BundleState.STORED)]

        for b in pending:
            route = self.router.find_earliest_arrival_route(
                source_id=b.current_custodian_id,
                destination_id=b.destination_id,
                earliest_start_s=current_time_s,
                payload_bytes=b.remaining_bytes,
                contact_windows=contact_windows,
            )
            if not route or not route.hops:
                continue

            first_hop = route.hops[0]
            transmissions.append(
                ScheduledTransmission(
                    bundle_id=b.bundle_id,
                    contact_id=first_hop.contact_window.contact_id,
                    sender_id=first_hop.from_node_id,
                    receiver_id=first_hop.to_node_id,
                    start_time_s=first_hop.departure_time_s,
                    end_time_s=first_hop.departure_time_s + first_hop.duration_s,
                    duration_s=first_hop.duration_s,
                    rate_bps=first_hop.rate_bps,
                    bytes_allocated=b.remaining_bytes,
                    priority=b.priority,
                    scheduler_type=self.scheduler_type,
                    rationale=f"CGR multi-hop earliest arrival at {route.arrival_time_s:.1f}s ({route.total_hops} hops)",
                )
            )

        return transmissions


class PriorityFirstScheduler(BaseContactScheduler):
    """
    SCHED-03-PRIORITY-FIRST: Strictly enforces Class 1 (Emergency) and Class 2 (Command)
    queue head ordering before scheduling science or engineering data.
    """

    def __init__(self, topology: PlanetaryNetworkTopology) -> None:
        super().__init__(SchedulerType.PRIORITY_FIRST, topology)

    def schedule(
        self,
        current_time_s: float,
        bundles: List[DataBundle],
        contact_windows: List[ContactWindow],
        dtn_engine: PlanetaryDTNEngine,
    ) -> List[ScheduledTransmission]:
        transmissions: List[ScheduledTransmission] = []
        valid_cw = [cw for cw in contact_windows if cw.end_time_s > current_time_s]
        valid_cw.sort(key=lambda cw: cw.start_time_s)

        cw_cap: Dict[str, int] = {cw.contact_id: cw.total_capacity_bytes for cw in valid_cw}
        cw_end: Dict[str, float] = {cw.contact_id: cw.start_time_s for cw in valid_cw}

        # Sort bundles strictly by priority class (1 highest) and then creation time
        pending = [b for b in bundles if b.state in (BundleState.QUEUED, BundleState.CREATED, BundleState.STORED)]
        pending.sort(key=lambda b: (b.priority.value, b.creation_time_s))

        for b in pending:
            sender = b.current_custodian_id
            for cw in valid_cw:
                if cw.src_node_id != sender and (not cw.is_bidirectional or cw.dst_node_id != sender):
                    continue
                receiver = cw.dst_node_id if cw.src_node_id == sender else cw.src_node_id
                rem_cap = cw_cap[cw.contact_id]
                if rem_cap <= 0:
                    continue

                tx_bytes = min(b.remaining_bytes, rem_cap)
                tx_dur = (tx_bytes * 8.0) / float(cw.achievable_rate_bps)
                cur_start = max(current_time_s, cw_end[cw.contact_id])
                if cur_start + tx_dur > cw.end_time_s:
                    continue

                transmissions.append(
                    ScheduledTransmission(
                        bundle_id=b.bundle_id,
                        contact_id=cw.contact_id,
                        sender_id=sender,
                        receiver_id=receiver,
                        start_time_s=cur_start,
                        end_time_s=cur_start + tx_dur,
                        duration_s=tx_dur,
                        rate_bps=cw.achievable_rate_bps,
                        bytes_allocated=tx_bytes,
                        priority=b.priority,
                        scheduler_type=self.scheduler_type,
                        rationale=f"Strict priority ordering (Class {b.priority.value}: {b.priority.name})",
                    )
                )
                cw_cap[cw.contact_id] -= tx_bytes
                cw_end[cw.contact_id] = cur_start + tx_dur
                break

        return transmissions


class DeadlineAwareScheduler(BaseContactScheduler):
    """
    SCHED-04-DEADLINE-AWARE: Earliest Deadline First (EDF). Prioritizes bundles whose
    remaining Time-To-Live (TTL) is shortest to prevent packet expiration.
    """

    def __init__(self, topology: PlanetaryNetworkTopology) -> None:
        super().__init__(SchedulerType.DEADLINE_AWARE, topology)

    def schedule(
        self,
        current_time_s: float,
        bundles: List[DataBundle],
        contact_windows: List[ContactWindow],
        dtn_engine: PlanetaryDTNEngine,
    ) -> List[ScheduledTransmission]:
        transmissions: List[ScheduledTransmission] = []
        valid_cw = [cw for cw in contact_windows if cw.end_time_s > current_time_s]
        valid_cw.sort(key=lambda cw: cw.start_time_s)

        cw_cap: Dict[str, int] = {cw.contact_id: cw.total_capacity_bytes for cw in valid_cw}
        cw_end: Dict[str, float] = {cw.contact_id: cw.start_time_s for cw in valid_cw}

        # Sort by remaining TTL
        pending = [b for b in bundles if b.state in (BundleState.QUEUED, BundleState.CREATED, BundleState.STORED)]
        pending.sort(key=lambda b: (b.expiration_time_s - current_time_s))

        for b in pending:
            sender = b.current_custodian_id
            rem_ttl = b.expiration_time_s - current_time_s
            for cw in valid_cw:
                if cw.src_node_id != sender and (not cw.is_bidirectional or cw.dst_node_id != sender):
                    continue
                receiver = cw.dst_node_id if cw.src_node_id == sender else cw.src_node_id
                rem_cap = cw_cap[cw.contact_id]
                if rem_cap <= 0:
                    continue

                tx_bytes = min(b.remaining_bytes, rem_cap)
                tx_dur = (tx_bytes * 8.0) / float(cw.achievable_rate_bps)
                cur_start = max(current_time_s, cw_end[cw.contact_id])
                if cur_start + tx_dur > cw.end_time_s or cur_start + tx_dur > b.expiration_time_s:
                    continue

                transmissions.append(
                    ScheduledTransmission(
                        bundle_id=b.bundle_id,
                        contact_id=cw.contact_id,
                        sender_id=sender,
                        receiver_id=receiver,
                        start_time_s=cur_start,
                        end_time_s=cur_start + tx_dur,
                        duration_s=tx_dur,
                        rate_bps=cw.achievable_rate_bps,
                        bytes_allocated=tx_bytes,
                        priority=b.priority,
                        scheduler_type=self.scheduler_type,
                        rationale=f"Earliest deadline first (TTL remaining: {rem_ttl:.1f}s)",
                    )
                )
                cw_cap[cw.contact_id] -= tx_bytes
                cw_end[cw.contact_id] = cur_start + tx_dur
                break

        return transmissions


class ResourceAwareScheduler(BaseContactScheduler):
    """
    SCHED-05-RESOURCE-AWARE: Minimizes mobile asset battery draw by preferring high-elevation passes
    with highest data rates, and avoids forwarding to intermediate nodes whose buffers exceed 85% occupancy.
    """

    def __init__(self, topology: PlanetaryNetworkTopology) -> None:
        super().__init__(SchedulerType.RESOURCE_AWARE, topology)

    def schedule(
        self,
        current_time_s: float,
        bundles: List[DataBundle],
        contact_windows: List[ContactWindow],
        dtn_engine: PlanetaryDTNEngine,
    ) -> List[ScheduledTransmission]:
        transmissions: List[ScheduledTransmission] = []
        valid_cw = [cw for cw in contact_windows if cw.end_time_s > current_time_s]
        # Prefer higher rate / higher elevation contacts
        valid_cw.sort(key=lambda cw: (-cw.achievable_rate_bps, cw.start_time_s))

        cw_cap: Dict[str, int] = {cw.contact_id: cw.total_capacity_bytes for cw in valid_cw}
        cw_end: Dict[str, float] = {cw.contact_id: cw.start_time_s for cw in valid_cw}

        pending = [b for b in bundles if b.state in (BundleState.QUEUED, BundleState.CREATED, BundleState.STORED)]

        for b in pending:
            sender = b.current_custodian_id
            for cw in valid_cw:
                if cw.src_node_id != sender and (not cw.is_bidirectional or cw.dst_node_id != sender):
                    continue
                receiver = cw.dst_node_id if cw.src_node_id == sender else cw.src_node_id

                # Buffer protection: do not forward to receiver if utilization > 85%
                rx_buf = dtn_engine.get_buffer(receiver)
                if rx_buf and rx_buf.utilization_pct > 85.0 and receiver != b.destination_id:
                    continue

                rem_cap = cw_cap[cw.contact_id]
                if rem_cap <= 0:
                    continue

                tx_bytes = min(b.remaining_bytes, rem_cap)
                tx_dur = (tx_bytes * 8.0) / float(cw.achievable_rate_bps)
                cur_start = max(current_time_s, cw_end[cw.contact_id])
                if cur_start + tx_dur > cw.end_time_s:
                    continue

                transmissions.append(
                    ScheduledTransmission(
                        bundle_id=b.bundle_id,
                        contact_id=cw.contact_id,
                        sender_id=sender,
                        receiver_id=receiver,
                        start_time_s=cur_start,
                        end_time_s=cur_start + tx_dur,
                        duration_s=tx_dur,
                        rate_bps=cw.achievable_rate_bps,
                        bytes_allocated=tx_bytes,
                        priority=b.priority,
                        scheduler_type=self.scheduler_type,
                        rationale=f"Resource safe: high rate {cw.achievable_rate_bps/1000.0:.0f} kbps, buffer-safe receiver",
                    )
                )
                cw_cap[cw.contact_id] -= tx_bytes
                cw_end[cw.contact_id] = cur_start + tx_dur
                break

        return transmissions


class AtlasAdaptiveScheduler(BaseContactScheduler):
    """
    SCHED-06-ATLAS-ADAPTIVE: Multi-objective adaptive scheduling director.
    Computes a composite utility score balancing urgency, link quality, delivery horizon,
    and buffer stress to achieve optimal global throughput with zero emergency bundle loss.
    """

    def __init__(self, topology: PlanetaryNetworkTopology) -> None:
        super().__init__(SchedulerType.ATLAS_ADAPTIVE, topology)

    def schedule(
        self,
        current_time_s: float,
        bundles: List[DataBundle],
        contact_windows: List[ContactWindow],
        dtn_engine: PlanetaryDTNEngine,
    ) -> List[ScheduledTransmission]:
        transmissions: List[ScheduledTransmission] = []
        valid_cw = [cw for cw in contact_windows if cw.end_time_s > current_time_s]
        cw_cap: Dict[str, int] = {cw.contact_id: cw.total_capacity_bytes for cw in valid_cw}
        cw_end: Dict[str, float] = {cw.contact_id: cw.start_time_s for cw in valid_cw}

        pending = [b for b in bundles if b.state in (BundleState.QUEUED, BundleState.CREATED, BundleState.STORED)]

        # Score and rank (bundle, contact) assignment pairs
        scored_candidates: List[Tuple[float, DataBundle, ContactWindow, str, str]] = []

        for b in pending:
            sender = b.current_custodian_id
            rem_ttl = max(1.0, b.expiration_time_s - current_time_s)

            for cw in valid_cw:
                if cw.src_node_id != sender and (not cw.is_bidirectional or cw.dst_node_id != sender):
                    continue
                receiver = cw.dst_node_id if cw.src_node_id == sender else cw.src_node_id

                # Urgency component: priority weight / log(rem_ttl)
                urgency = (b.priority.weight * 2.0) + (1000.0 / (rem_ttl + 10.0))

                # Rate component
                rate_score = math.log10(max(8000, cw.achievable_rate_bps))

                # Proximity to destination bonus
                dest_bonus = 50.0 if receiver == b.destination_id else 0.0

                # Buffer penalty
                rx_buf = dtn_engine.get_buffer(receiver)
                buf_penalty = (rx_buf.utilization_pct * 0.3) if rx_buf else 0.0

                total_score = urgency + (rate_score * 5.0) + dest_bonus - buf_penalty
                scored_candidates.append((total_score, b, cw, sender, receiver))

        # Sort candidate assignments by highest utility score
        scored_candidates.sort(key=lambda x: -x[0])
        scheduled_bundles: Set[str] = set()

        for score, b, cw, sender, receiver in scored_candidates:
            if b.bundle_id in scheduled_bundles:
                continue
            rem_cap = cw_cap[cw.contact_id]
            if rem_cap <= 0:
                continue

            tx_bytes = min(b.remaining_bytes, rem_cap)
            tx_dur = (tx_bytes * 8.0) / float(cw.achievable_rate_bps)
            cur_start = max(current_time_s, cw_end[cw.contact_id])
            if cur_start + tx_dur > cw.end_time_s:
                continue

            transmissions.append(
                ScheduledTransmission(
                    bundle_id=b.bundle_id,
                    contact_id=cw.contact_id,
                    sender_id=sender,
                    receiver_id=receiver,
                    start_time_s=cur_start,
                    end_time_s=cur_start + tx_dur,
                    duration_s=tx_dur,
                    rate_bps=cw.achievable_rate_bps,
                    bytes_allocated=tx_bytes,
                    priority=b.priority,
                    scheduler_type=self.scheduler_type,
                    rationale=f"Atlas Adaptive utility score {score:.1f} (urgency={b.priority.weight}, rate={cw.achievable_rate_bps/1000:.0f}k)",
                )
            )
            cw_cap[cw.contact_id] -= tx_bytes
            cw_end[cw.contact_id] = cur_start + tx_dur
            scheduled_bundles.add(b.bundle_id)

        return transmissions
