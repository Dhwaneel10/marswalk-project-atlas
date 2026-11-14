"""
MarsWalk 2.0 / Project Atlas — Milestone 13Y: Network Resilience & Cascading Fault Management
=============================================================================================
Simulates network anomalies, cascading failures, hardware degradations, and autonomous recovery:
- Orbital Relay Anomaly (Reaction wheel failure, power bus brownout, antenna off-pointing)
- Surface Tower Blackout (Dust storm solar deprivation, hardware failure)
- Buffer Saturation & Congestion Collapse prevention
- Dynamic rerouting around failed nodes and broken contact links
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


class AnomalyType(str, enum.Enum):
    """Network fault and anomaly taxonomy."""
    ORBITAL_RELAY_OFFLINE = "ORBITAL_RELAY_OFFLINE"          # Loss of orbiter communications
    SURFACE_TOWER_POWER_LOSS = "SURFACE_TOWER_POWER_LOSS"    # Relay tower battery depletion
    ANTENNA_POINTING_ERROR = "ANTENNA_POINTING_ERROR"        # High off-axis pointing loss
    SOLAR_CONJUNCTION_BLACKOUT = "SOLAR_CONJUNCTION_BLACKOUT"# Sun-Mars-Earth line-of-sight coronal noise
    BUFFER_SATURATION_SPIKE = "BUFFER_SATURATION_SPIKE"      # Rapid influx of high-volume bulk science


@dataclass
class NetworkAnomalyEvent:
    """An injected anomaly event affecting network operational capabilities."""
    anomaly_id: str
    anomaly_type: AnomalyType
    target_node_id: str
    start_time_s: float
    duration_s: float
    description: str
    resolved: bool = False

    @property
    def end_time_s(self) -> float:
        return self.start_time_s + self.duration_s

    def is_active_at(self, current_time_s: float) -> bool:
        return self.start_time_s <= current_time_s <= self.end_time_s


class NetworkResilienceCoordinator:
    """Manages failure injection, cascading impact modeling, and autonomous mitigation."""

    def __init__(
        self,
        topology: PlanetaryNetworkTopology,
        dtn_engine: PlanetaryDTNEngine,
    ) -> None:
        self.topology = topology
        self.dtn_engine = dtn_engine
        self.active_anomalies: List[NetworkAnomalyEvent] = []
        self.reroute_events: List[Dict[str, Any]] = []

    def inject_anomaly(
        self,
        anomaly_type: AnomalyType,
        target_node_id: str,
        start_time_s: float,
        duration_s: float,
        description: str = "",
    ) -> NetworkAnomalyEvent:
        aid = f"ANOMALY-{len(self.active_anomalies)+1:03d}"
        ev = NetworkAnomalyEvent(
            anomaly_id=aid,
            anomaly_type=anomaly_type,
            target_node_id=target_node_id,
            start_time_s=start_time_s,
            duration_s=duration_s,
            description=description or anomaly_type.value,
        )
        self.active_anomalies.append(ev)

        target = self.topology.get_node(target_node_id)
        if target:
            if anomaly_type in (AnomalyType.ORBITAL_RELAY_OFFLINE, AnomalyType.SURFACE_TOWER_POWER_LOSS):
                target.is_active = False
        return ev

    def update_resilience_state(self, current_time_s: float) -> None:
        """Restores nodes when their anomaly duration expires."""
        for ev in self.active_anomalies:
            if not ev.resolved and current_time_s > ev.end_time_s:
                ev.resolved = True
                target = self.topology.get_node(ev.target_node_id)
                if target:
                    target.is_active = True

    def filter_feasible_contact_windows(
        self,
        contact_windows: List[ContactWindow],
        current_time_s: float,
    ) -> List[ContactWindow]:
        """
        Prunes contact windows involving nodes that are currently disabled by active anomalies.
        """
        disabled_nodes = {
            ev.target_node_id
            for ev in self.active_anomalies
            if ev.is_active_at(current_time_s) and ev.anomaly_type in (
                AnomalyType.ORBITAL_RELAY_OFFLINE, AnomalyType.SURFACE_TOWER_POWER_LOSS
            )
        }
        if not disabled_nodes:
            return contact_windows

        return [
            cw for cw in contact_windows
            if cw.src_node_id not in disabled_nodes and cw.dst_node_id not in disabled_nodes
        ]
