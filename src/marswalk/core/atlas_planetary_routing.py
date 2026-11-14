"""
MarsWalk 2.0 / Project Atlas — Milestone 13Y: Planetary Contact Graph Routing
=============================================================================
Time-dependent contact graph routing engine for interplanetary and surface DTN.
Implements space-time path exploration across deterministic contact windows:
- Earliest Delivery Path (Contact Graph Routing / Dijkstra over time intervals)
- Shortest Hop Path (Minimum forwarding stages)
- Energy-Aware Path (Minimizes RF transmit power expenditure)
- Multi-Path Resilient Routing (Identifies node/contact-disjoint alternative routes)
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
import heapq
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.atlas_orbital_contact_planner import ContactWindow
from marswalk.core.atlas_planetary_network_architecture import (
    PlanetaryNode,
    PlanetaryNodeType,
    PlanetaryNetworkTopology,
)


@dataclass
class RouteHop:
    """A single hop along a multi-hop contact route."""
    from_node_id: str
    to_node_id: str
    contact_window: ContactWindow
    departure_time_s: float
    arrival_time_s: float
    duration_s: float
    rate_bps: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_node_id,
            "to": self.to_node_id,
            "contact_id": self.contact_window.contact_id,
            "dep_s": round(self.departure_time_s, 1),
            "arr_s": round(self.arrival_time_s, 1),
            "rate_kbps": round(self.rate_bps / 1000.0, 1),
        }


@dataclass
class ContactRoute:
    """An end-to-end multi-hop trajectory across space-time contact windows."""
    source_id: str
    destination_id: str
    hops: List[RouteHop]
    total_bytes: int

    @property
    def total_hops(self) -> int:
        return len(self.hops)

    @property
    def path_nodes(self) -> List[str]:
        if not self.hops:
            return [self.source_id]
        nodes = [self.hops[0].from_node_id]
        for h in self.hops:
            nodes.append(h.to_node_id)
        return nodes

    @property
    def departure_time_s(self) -> float:
        return self.hops[0].departure_time_s if self.hops else 0.0

    @property
    def arrival_time_s(self) -> float:
        return self.hops[-1].arrival_time_s if self.hops else 0.0

    @property
    def total_latency_s(self) -> float:
        return max(0.0, self.arrival_time_s - self.departure_time_s)

    @property
    def bottleneck_rate_bps(self) -> int:
        if not self.hops:
            return 0
        return min(h.rate_bps for h in self.hops)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_id,
            "destination": self.destination_id,
            "hops": self.total_hops,
            "path": self.path_nodes,
            "departure_s": round(self.departure_time_s, 1),
            "arrival_s": round(self.arrival_time_s, 1),
            "total_latency_s": round(self.total_latency_s, 1),
            "bottleneck_rate_kbps": round(self.bottleneck_rate_bps / 1000.0, 1),
            "hop_details": [h.to_dict() for h in self.hops],
        }


class TimeDependentContactRouter:
    """Calculates time-dependent optimal paths across scheduled contact windows."""

    def __init__(self, topology: PlanetaryNetworkTopology) -> None:
        self.topology = topology

    def find_earliest_arrival_route(
        self,
        source_id: str,
        destination_id: str,
        earliest_start_s: float,
        payload_bytes: int,
        contact_windows: List[ContactWindow],
        max_hops: int = 4,
    ) -> Optional[ContactRoute]:
        """
        Space-time Dijkstra algorithm: finds path that delivers payload_bytes to
        destination_id at the earliest possible simulation timestamp.
        """
        if source_id == destination_id:
            return None

        # Build adjacency for contact windows
        # contacts indexed by src_node:
        cw_by_src: Dict[str, List[ContactWindow]] = {}
        for cw in contact_windows:
            if cw.end_time_s < earliest_start_s:
                continue
            cw_by_src.setdefault(cw.src_node_id, []).append(cw)
            if cw.is_bidirectional:
                # Also available in reverse
                rev_cw = copy.copy(cw)
                rev_cw.src_node_id = cw.dst_node_id
                rev_cw.dst_node_id = cw.src_node_id
                cw_by_src.setdefault(cw.dst_node_id, []).append(rev_cw)

        # Priority queue entries: (arrival_time_s, hop_count, current_node, hops_list)
        pq: List[Tuple[float, int, str, List[RouteHop]]] = []
        heapq.heappush(pq, (earliest_start_s, 0, source_id, []))

        # Best known earliest arrival at each node
        best_arrival: Dict[str, float] = {source_id: earliest_start_s}

        while pq:
            curr_arr, hops_cnt, u, hops = heapq.heappop(pq)

            if u == destination_id:
                return ContactRoute(
                    source_id=source_id,
                    destination_id=destination_id,
                    hops=hops,
                    total_bytes=payload_bytes,
                )

            if hops_cnt >= max_hops:
                continue

            if curr_arr > best_arrival.get(u, float("inf")):
                continue

            # Check outgoing contacts from u
            for cw in cw_by_src.get(u, []):
                v = cw.dst_node_id
                # Must start on or after curr_arr
                tx_start = max(curr_arr, cw.start_time_s)
                if tx_start >= cw.end_time_s:
                    continue

                # Check if contact has sufficient remaining capacity/time
                tx_duration = (payload_bytes * 8.0) / float(cw.achievable_rate_bps)
                arr_time = tx_start + tx_duration + cw.propagation_delay_s
                if tx_start + tx_duration > cw.end_time_s:
                    continue  # Cannot complete before contact closes

                if arr_time < best_arrival.get(v, float("inf")):
                    best_arrival[v] = arr_time
                    hop = RouteHop(
                        from_node_id=u,
                        to_node_id=v,
                        contact_window=cw,
                        departure_time_s=tx_start,
                        arrival_time_s=arr_time,
                        duration_s=tx_duration,
                        rate_bps=cw.achievable_rate_bps,
                    )
                    heapq.heappush(pq, (arr_time, hops_cnt + 1, v, hops + [hop]))

        return None

    def find_shortest_hop_route(
        self,
        source_id: str,
        destination_id: str,
        earliest_start_s: float,
        payload_bytes: int,
        contact_windows: List[ContactWindow],
    ) -> Optional[ContactRoute]:
        """BFS search prioritizing minimum hop count over arrival time."""
        for max_h in range(1, 5):
            route = self.find_earliest_arrival_route(
                source_id=source_id,
                destination_id=destination_id,
                earliest_start_s=earliest_start_s,
                payload_bytes=payload_bytes,
                contact_windows=contact_windows,
                max_hops=max_h,
            )
            if route is not None:
                return route
        return None

    def find_resilient_multipath(
        self,
        source_id: str,
        destination_id: str,
        earliest_start_s: float,
        payload_bytes: int,
        contact_windows: List[ContactWindow],
    ) -> List[ContactRoute]:
        """
        Calculates primary and node-disjoint secondary backup routes for high-resilience delivery.
        """
        primary = self.find_earliest_arrival_route(
            source_id, destination_id, earliest_start_s, payload_bytes, contact_windows
        )
        if not primary:
            return []

        routes = [primary]
        # Identify intermediate nodes in primary path
        inter_nodes = set(primary.path_nodes[1:-1])
        if not inter_nodes:
            return routes  # Direct single-hop link, no intermediate nodes to bypass

        # Filter out contacts using primary intermediate nodes to find disjoint secondary
        disjoint_windows = [
            cw for cw in contact_windows
            if cw.src_node_id not in inter_nodes and cw.dst_node_id not in inter_nodes
        ]

        secondary = self.find_earliest_arrival_route(
            source_id, destination_id, earliest_start_s, payload_bytes, disjoint_windows
        )
        if secondary:
            routes.append(secondary)

        return routes
