"""
MarsWalk 2.0 / Project Atlas - Milestone 13J: Fleet Communications Network Engine.

Integrates multi-rover exploration units into a shared geometric RelayNet mesh:
evaluates pairwise line-of-sight across base station, deployed relays, mobile rovers,
and candidate relays. Models multi-hop reachability, dynamic timeline synchronization,
and opportunistic mobile rover relay roles.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np

from marswalk.core.terrain import TerrainGrid
from marswalk.core.terrain_visibility import calculate_line_of_sight, LineOfSightResult
from marswalk.core.relay_graph import (
    RelayNetworkGraph,
    RelayNode,
    RelayNodeType,
    RelayEdge,
    LinkVisibilityStatus,
)
from marswalk.core.fleet_operations_director import (
    RoverUnitConfig,
    RoverOperationalState,
    RoverConnectivityStatus,
)


@dataclass
class RoverConnectivityReport:
    """Detailed geometric communications status of a rover node within the fleet graph."""
    rover_id: str
    is_connected_to_base: bool
    connectivity_status: str
    hop_count: int
    active_path: List[str]
    direct_los_to_base: bool
    intermediate_relay_ids: List[str]
    signal_margin_db: float = 6.0  # Synthetic demonstration link margin
    critical_relay_dependency: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rover_id": self.rover_id,
            "is_connected_to_base": self.is_connected_to_base,
            "connectivity_status": self.connectivity_status,
            "hop_count": self.hop_count,
            "active_path": list(self.active_path),
            "direct_los_to_base": self.direct_los_to_base,
            "intermediate_relay_ids": list(self.intermediate_relay_ids),
            "signal_margin_db": round(self.signal_margin_db, 1),
            "critical_relay_dependency": self.critical_relay_dependency,
        }


@dataclass
class DeployedRelayConfig:
    """Static or deployed communications relay mast."""
    relay_id: str
    name: str
    rc: Tuple[int, int]
    antenna_height_m: float = 4.0
    elevation_m: float = -2500.0
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relay_id": self.relay_id,
            "name": self.name,
            "rc": list(self.rc),
            "antenna_height_m": self.antenna_height_m,
            "elevation_m": self.elevation_m,
            "is_active": self.is_active,
        }


def get_default_deployed_relays() -> List[DeployedRelayConfig]:
    """Default active relay infrastructure in Jezero Western Delta."""
    return [
        DeployedRelayConfig(
            relay_id="relay_octavia_mast",
            name="Octavia Landing Primary Base Relay",
            rc=(128, 128),
            antenna_height_m=5.0,
            elevation_m=-2595.0,
            is_active=True,
        ),
        DeployedRelayConfig(
            relay_id="relay_delta_crest",
            name="Delta Rim Western High Relay",
            rc=(144, 142),
            antenna_height_m=4.5,
            elevation_m=-2490.0,
            is_active=True,
        ),
    ]


class FleetCommunicationsManager:
    """
    Manages the shared communications network across all fleet exploration units.
    Evaluates geometric visibility, multi-hop routing to Base Station, and mobile relay roles.
    """

    def __init__(
        self,
        base_station_rc: Tuple[int, int] = (128, 128),
        base_station_antenna_m: float = 5.0,
        max_rf_range_m: float = 5000.0,
        ground_spacing_m: float = 20.0,
    ):
        self.base_station_rc = base_station_rc
        self.base_station_antenna_m = base_station_antenna_m
        self.max_rf_range_m = max_rf_range_m
        self.ground_spacing_m = ground_spacing_m
        self.deployed_relays: Dict[str, DeployedRelayConfig] = {
            r.relay_id: r for r in get_default_deployed_relays()
        }

    def build_fleet_relay_graph(
        self,
        terrain: TerrainGrid,
        rovers: Dict[str, RoverUnitConfig],
        rover_locations: Dict[str, Tuple[int, int]],
        active_relays: Optional[List[str]] = None
    ) -> Tuple[RelayNetworkGraph, Dict[str, RoverConnectivityReport]]:
        """
        Constructs the complete RelayNet graph combining Base Station, active surface relays,
        and all rovers at their specified (row, col) coordinates.
        """
        graph = RelayNetworkGraph(r_max_m=self.max_rf_range_m)

        # 1. Add Base Station Node
        base_elev = float(terrain.elevation[
            min(max(0, self.base_station_rc[0]), terrain.height - 1),
            min(max(0, self.base_station_rc[1]), terrain.width - 1)
        ])
        base_node = RelayNode(
            node_id="BASE_STATION",
            node_type=RelayNodeType.BASE_STATION,
            rc=self.base_station_rc,
            elevation_m=base_elev,
            antenna_height_m=self.base_station_antenna_m,
            label="Jezero Base Habitat",
            is_active=True,
        )
        graph.add_node(base_node)

        # 2. Add Deployed Relays
        enabled_relays = active_relays if active_relays is not None else list(self.deployed_relays.keys())
        for r_id in enabled_relays:
            if r_id in self.deployed_relays:
                r_cfg = self.deployed_relays[r_id]
                elev = float(terrain.elevation[
                    min(max(0, r_cfg.rc[0]), terrain.height - 1),
                    min(max(0, r_cfg.rc[1]), terrain.width - 1)
                ])
                node = RelayNode(
                    node_id=r_id,
                    node_type=RelayNodeType.ACTIVE_RELAY,
                    rc=r_cfg.rc,
                    elevation_m=elev,
                    antenna_height_m=r_cfg.antenna_height_m,
                    label=r_cfg.name,
                    is_active=r_cfg.is_active,
                )
                graph.add_node(node)

        # 3. Add Rover Nodes
        for r_id, r_cfg in rovers.items():
            loc_rc = rover_locations.get(r_id, r_cfg.starting_location_rc)
            elev = float(terrain.elevation[
                min(max(0, loc_rc[0]), terrain.height - 1),
                min(max(0, loc_rc[1]), terrain.width - 1)
            ])
            n_type = RelayNodeType.SCOUT_ROVER if r_cfg.unit_type == "scout_rover" else RelayNodeType.ROBOTIC_ROVER
            node = RelayNode(
                node_id=r_id,
                node_type=n_type,
                rc=loc_rc,
                elevation_m=elev,
                antenna_height_m=r_cfg.antenna_height_m,
                label=r_cfg.name,
                is_active=True,
            )
            graph.add_node(node)

        # 4. Evaluate Pairwise Visibility & Add Edges
        node_list = list(graph.nodes.values())
        for i in range(len(node_list)):
            u_node = node_list[i]
            for j in range(i + 1, len(node_list)):
                v_node = node_list[j]

                # Check if mobile relay role is allowed (if both are rovers, at least one must be a mobile relay or base)
                is_u_rover = u_node.node_id in rovers
                is_v_rover = v_node.node_id in rovers
                if is_u_rover and is_v_rover:
                    u_can_relay = rovers[u_node.node_id].can_act_as_mobile_relay
                    v_can_relay = rovers[v_node.node_id].can_act_as_mobile_relay
                    if not (u_can_relay or v_can_relay):
                        continue  # Inter-rover link only permitted if one is a designated mobile relay

                # Calculate geometric Line of Sight
                los_res: LineOfSightResult = calculate_line_of_sight(
                    elevation_grid=terrain.elevation,
                    point_a=u_node.rc,
                    point_b=v_node.rc,
                    antenna_h_a=u_node.antenna_height_m,
                    antenna_h_b=v_node.antenna_height_m,
                    max_range_m=self.max_rf_range_m,
                    clearance_margin_m=0.5,
                    dx_m=self.ground_spacing_m * 0.94864,
                    dy_m=self.ground_spacing_m,
                    endpoint_a_id=u_node.node_id,
                    endpoint_b_id=v_node.node_id,
                )

                if los_res.is_visible and los_res.slant_distance_m is not None:
                    edge = RelayEdge(
                        u=u_node.node_id,
                        v=v_node.node_id,
                        distance_m=los_res.ground_distance_m,
                        slant_range_m=los_res.slant_distance_m,
                        visibility=LinkVisibilityStatus.VISIBLE,
                        min_clearance_m=los_res.min_clearance_m if hasattr(los_res, 'min_clearance_m') else 1.0,
                    )
                    graph.add_edge(edge)

        # 5. Compute BFS Reachability & Route Reports to Base Station
        reports: Dict[str, RoverConnectivityReport] = {}
        for r_id in rovers.keys():
            path = graph.get_minimum_hop_path(r_id, "BASE_STATION")
            is_connected = path is not None and len(path) > 0

            if not is_connected:
                reports[r_id] = RoverConnectivityReport(
                    rover_id=r_id,
                    is_connected_to_base=False,
                    connectivity_status=RoverConnectivityStatus.BLACKOUT.value,
                    hop_count=999,
                    active_path=[],
                    direct_los_to_base=False,
                    intermediate_relay_ids=[],
                    signal_margin_db=0.0,
                    critical_relay_dependency=None,
                )
            else:
                hop_count = len(path) - 1
                intermediates = path[1:-1]
                direct_los = (hop_count == 1)
                stat = (
                    RoverConnectivityStatus.CONNECTED_DIRECT.value if direct_los
                    else (RoverConnectivityStatus.CONNECTED_RELAY.value if hop_count == 2
                          else RoverConnectivityStatus.CONNECTED_MULTI_HOP.value)
                )
                critical_dep = intermediates[0] if len(intermediates) == 1 else None

                reports[r_id] = RoverConnectivityReport(
                    rover_id=r_id,
                    is_connected_to_base=True,
                    connectivity_status=stat,
                    hop_count=hop_count,
                    active_path=path,
                    direct_los_to_base=direct_los,
                    intermediate_relay_ids=intermediates,
                    signal_margin_db=max(1.0, 12.0 - (hop_count * 2.5)),
                    critical_relay_dependency=critical_dep,
                )

        return graph, reports

    def evaluate_fleet_connectivity_at_time(
        self,
        terrain: TerrainGrid,
        rovers: Dict[str, RoverUnitConfig],
        routes: Dict[str, Any],  # Dict[rover_id, FleetRoverRoute]
        met_seconds: float,
        active_relays: Optional[List[str]] = None
    ) -> Dict[str, RoverConnectivityReport]:
        """
        Calculates instantaneous fleet connectivity at timestamp MET=met_seconds
        by interpolating each rover's (r, c) position along its route schedule.
        """
        locations: Dict[str, Tuple[int, int]] = {}
        for r_id, r_cfg in rovers.items():
            if r_id in routes and routes[r_id].occupancy_schedule:
                # Find matching occupancy interval
                occ_list = routes[r_id].occupancy_schedule
                matched_rc = occ_list[-1].rc
                for occ in occ_list:
                    if occ.t_enter_s <= met_seconds <= occ.t_exit_s:
                        matched_rc = occ.rc
                        break
                    elif met_seconds < occ.t_enter_s:
                        matched_rc = occ.rc
                        break
                locations[r_id] = matched_rc
            else:
                locations[r_id] = r_cfg.starting_location_rc

        _, reports = self.build_fleet_relay_graph(
            terrain=terrain,
            rovers=rovers,
            rover_locations=locations,
            active_relays=active_relays,
        )
        return reports
