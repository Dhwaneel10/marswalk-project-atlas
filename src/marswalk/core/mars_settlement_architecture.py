"""MarsWalk 2.0 / Project Atlas  Milestone 13S: Settlement Architecture & Master Planner.

Decomposes planetary surface infrastructure into the 12 NASA Moon to Mars elements,
models configurable archetypes (Small Outpost, Expedition Base, Mars Base Alpha),
and evaluates a causal Infrastructure Dependency Directed Acyclic Graph (DAG).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class MoonToMarsElement(str, Enum):
    """The 12 formal NASA Moon to Mars architectural building blocks."""
    HABITATION = "HABITATION"
    POWER = "POWER"
    ISRU = "ISRU"
    AUTONOMOUS_ROBOTICS = "AUTONOMOUS_ROBOTICS"
    COMMUNICATIONS_NAVIGATION = "COMMUNICATIONS_NAVIGATION"
    DATA_MANAGEMENT = "DATA_MANAGEMENT"
    SURFACE_MOBILITY = "SURFACE_MOBILITY"
    LOGISTICS = "LOGISTICS"
    INFRASTRUCTURE_SUPPORT = "INFRASTRUCTURE_SUPPORT"
    SCIENCE_UTILIZATION = "SCIENCE_UTILIZATION"
    TRANSPORTATION_INTERFACES = "TRANSPORTATION_INTERFACES"
    MAINTENANCE_SUSTAINMENT = "MAINTENANCE_SUSTAINMENT"


class SettlementArchetype(str, Enum):
    """Configurable reference settlement planning profiles."""
    SMALL_OUTPOST = "SMALL_OUTPOST"             # 4 crew, 120 sols, 45 kW hybrid power
    EXPEDITION_BASE = "EXPEDITION_BASE"         # 8 crew, 300 sols, 100 kW nuclear fission
    MARS_BASE_ALPHA = "MARS_BASE_ALPHA"         # 20 crew, 500 sols, 250 kW modular research city


class NodeCommissioningState(str, Enum):
    """Operational maturity of an infrastructure component in the dependency graph."""
    NOT_STARTED = "NOT_STARTED"
    PRECONDITIONS_MET = "PRECONDITIONS_MET"
    UNDER_CONSTRUCTION = "UNDER_CONSTRUCTION"
    UTILITIES_CONNECTED = "UTILITIES_CONNECTED"
    COMMISSIONED = "COMMISSIONED"
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"


@dataclass
class InfrastructureNode:
    """An individual functional facility or utility module in the settlement network."""
    node_id: str
    name: str
    element: MoonToMarsElement
    prerequisites: List[str]               # Node IDs that must be COMMISSIONED before this can operate
    power_demand_kw: float
    thermal_load_kw: float
    data_rate_kbps: float
    state: NodeCommissioningState = NodeCommissioningState.NOT_STARTED
    is_critical_path: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "element": self.element.value,
            "prerequisites": self.prerequisites,
            "power_demand_kw": round(self.power_demand_kw, 2),
            "thermal_load_kw": round(self.thermal_load_kw, 2),
            "data_rate_kbps": round(self.data_rate_kbps, 1),
            "state": self.state.value,
            "is_critical_path": self.is_critical_path,
            "description": self.description,
        }


@dataclass
class InfrastructureDependencyDAG:
    """Causal dependency graph enforcing build and operational sequence constraints."""
    nodes: Dict[str, InfrastructureNode] = field(default_factory=dict)

    def add_node(self, node: InfrastructureNode) -> None:
        self.nodes[node.node_id] = node

    def can_operate(self, node_id: str) -> Tuple[bool, List[str]]:
        """Verifies whether all prerequisite nodes are COMMISSIONED or OPERATIONAL."""
        if node_id not in self.nodes:
            return False, [f"Node '{node_id}' does not exist."]
        node = self.nodes[node_id]
        unsatisfied = []
        for req_id in node.prerequisites:
            if req_id not in self.nodes:
                unsatisfied.append(f"Missing prerequisite '{req_id}'")
            else:
                p_state = self.nodes[req_id].state
                if p_state not in (NodeCommissioningState.COMMISSIONED, NodeCommissioningState.OPERATIONAL):
                    unsatisfied.append(f"Prerequisite '{req_id}' in state '{p_state.value}' (must be COMMISSIONED)")
        return len(unsatisfied) == 0, unsatisfied

    def get_critical_path(self) -> List[str]:
        """Synthesizes the sequential critical path of longest dependency sequence."""
        # Simple longest path in DAG
        memo: Dict[str, List[str]] = {}

        def get_path(nid: str) -> List[str]:
            if nid in memo:
                return memo[nid]
            node = self.nodes.get(nid)
            if not node or not node.prerequisites:
                res = [nid]
            else:
                longest_parent = []
                for pid in node.prerequisites:
                    p_path = get_path(pid)
                    if len(p_path) > len(longest_parent):
                        longest_parent = p_path
                res = longest_parent + [nid]
            memo[nid] = res
            return res

        longest = []
        for nid in self.nodes:
            cand = get_path(nid)
            if len(cand) > len(longest):
                longest = cand
        return longest

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self.nodes),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "critical_path": self.get_critical_path(),
        }


@dataclass
class SettlementConfiguration:
    """Configurable top-level architectural specification of the settlement."""
    settlement_id: str
    name: str
    archetype: SettlementArchetype
    site_id: str
    population_capacity: int               # Configurable planning assumption (e.g., 4, 8, 20)
    planned_mission_sols: int              # e.g., 120, 300, 500
    habitat_modules_count: int
    power_system_type: str                 # "NUCLEAR_FISSION", "SOLAR_PV", "HYBRID_STORAGE"
    total_power_capacity_kw: float
    energy_storage_capacity_kwh: float
    isru_water_capacity_kg_per_sol: float
    isru_oxygen_capacity_kg_per_sol: float
    rover_fleet_size: int
    aircraft_fleet_size: int
    dependency_dag: InfrastructureDependencyDAG = field(default_factory=InfrastructureDependencyDAG)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "settlement_id": self.settlement_id,
            "name": self.name,
            "archetype": self.archetype.value,
            "site_id": self.site_id,
            "population_capacity": self.population_capacity,
            "planned_mission_sols": self.planned_mission_sols,
            "habitat_modules_count": self.habitat_modules_count,
            "power_system_type": self.power_system_type,
            "total_power_capacity_kw": round(self.total_power_capacity_kw, 1),
            "energy_storage_capacity_kwh": round(self.energy_storage_capacity_kwh, 1),
            "isru_water_capacity_kg_per_sol": round(self.isru_water_capacity_kg_per_sol, 1),
            "isru_oxygen_capacity_kg_per_sol": round(self.isru_oxygen_capacity_kg_per_sol, 1),
            "rover_fleet_size": self.rover_fleet_size,
            "aircraft_fleet_size": self.aircraft_fleet_size,
            "dependency_dag": self.dependency_dag.to_dict(),
        }


class SettlementArchitecturePlanner:
    """Generates structured Moon to Mars infrastructure models and dependency graphs."""

    @classmethod
    def create_settlement_plan(
        cls,
        archetype: SettlementArchetype = SettlementArchetype.MARS_BASE_ALPHA,
        site_id: str = "SITE-DELTA-NORTH",
        custom_population: Optional[int] = None,
        custom_sols: Optional[int] = None,
    ) -> SettlementConfiguration:
        """Instantiates a fully specified settlement digital twin with dependency DAG."""
        if archetype == SettlementArchetype.SMALL_OUTPOST:
            pop = custom_population or 4
            sols = custom_sols or 120
            name = "Jezero Robotic Research Outpost"
            habs = 3
            p_type = "HYBRID_STORAGE"
            p_kw = 55.0
            batt_kwh = 350.0
            water_kg = 25.0
            o2_kg = 12.0
            rovers = 2
            aero = 1

        elif archetype == SettlementArchetype.EXPEDITION_BASE:
            pop = custom_population or 8
            sols = custom_sols or 300
            name = "Jezero Delta Expedition Base"
            habs = 6
            p_type = "NUCLEAR_FISSION"
            p_kw = 120.0
            batt_kwh = 600.0
            water_kg = 85.0
            o2_kg = 35.0
            rovers = 4
            aero = 2

        else: # MARS_BASE_ALPHA
            pop = custom_population or 20
            sols = custom_sols or 500
            name = "Mars Base Alpha — Modular Research Settlement"
            habs = 14
            p_type = "NUCLEAR_FISSION"
            p_kw = 260.0
            batt_kwh = 1200.0
            water_kg = 240.0
            o2_kg = 95.0
            rovers = 8
            aero = 4

        dag = cls.build_standard_dependency_dag()
        settlement_id = f"SETTLE-{archetype.value}"

        return SettlementConfiguration(
            settlement_id=settlement_id,
            name=name,
            archetype=archetype,
            site_id=site_id,
            population_capacity=pop,
            planned_mission_sols=sols,
            habitat_modules_count=habs,
            power_system_type=p_type,
            total_power_capacity_kw=p_kw,
            energy_storage_capacity_kwh=batt_kwh,
            isru_water_capacity_kg_per_sol=water_kg,
            isru_oxygen_capacity_kg_per_sol=o2_kg,
            rover_fleet_size=rovers,
            aircraft_fleet_size=aero,
            dependency_dag=dag,
        )

    @staticmethod
    def build_standard_dependency_dag() -> InfrastructureDependencyDAG:
        """Constructs canonical multi-system dependency network across all 12 elements."""
        dag = InfrastructureDependencyDAG()

        # Phase A & B: Recon & Precursor
        dag.add_node(InfrastructureNode(
            node_id="NODE-SITE-SURVEY",
            name="Robotic Site Topographic Reconnaissance",
            element=MoonToMarsElement.SCIENCE_UTILIZATION,
            prerequisites=[],
            power_demand_kw=1.5,
            thermal_load_kw=0.0,
            data_rate_kbps=128.0,
            state=NodeCommissioningState.COMMISSIONED,
            description="Aerial photogrammetry and ground rover hazard mapping.",
        ))
        dag.add_node(InfrastructureNode(
            node_id="NODE-COMM-RELAY",
            name="Surface-Orbiter Telecommunications Relay Mast",
            element=MoonToMarsElement.COMMUNICATIONS_NAVIGATION,
            prerequisites=["NODE-SITE-SURVEY"],
            power_demand_kw=2.5,
            thermal_load_kw=0.8,
            data_rate_kbps=2048.0,
            state=NodeCommissioningState.COMMISSIONED,
            description="Dual UHF/X-band relay transceiver for uninterrupted MOCC link.",
        ))
        dag.add_node(InfrastructureNode(
            node_id="NODE-LANDING-BERM",
            name="Landing Zone Surface Clearing & Blast Berm",
            element=MoonToMarsElement.TRANSPORTATION_INTERFACES,
            prerequisites=["NODE-SITE-SURVEY"],
            power_demand_kw=12.0,
            thermal_load_kw=0.0,
            data_rate_kbps=64.0,
            state=NodeCommissioningState.COMMISSIONED,
            description="Autonomous grading and sintered regolith plume deflectors.",
        ))

        # Power System (Phase B)
        dag.add_node(InfrastructureNode(
            node_id="NODE-POWER-GEN",
            name="100 kWe Surface Nuclear Fission Reactor / Solar Array",
            element=MoonToMarsElement.POWER,
            prerequisites=["NODE-LANDING-BERM", "NODE-COMM-RELAY"],
            power_demand_kw=0.0,
            thermal_load_kw=0.0,
            data_rate_kbps=64.0,
            state=NodeCommissioningState.COMMISSIONED,
            is_critical_path=True,
            description="Primary electrical and thermal baseline power generation.",
        ))
        dag.add_node(InfrastructureNode(
            node_id="NODE-POWER-DIST",
            name="High-Voltage DC Conditioning & Distribution Grid",
            element=MoonToMarsElement.INFRASTRUCTURE_SUPPORT,
            prerequisites=["NODE-POWER-GEN"],
            power_demand_kw=3.5,
            thermal_load_kw=1.2,
            data_rate_kbps=32.0,
            state=NodeCommissioningState.COMMISSIONED,
            is_critical_path=True,
            description="Underground buried cable trenches and PDU switching bus.",
        ))

        # ISRU Infrastructure (Phase C)
        dag.add_node(InfrastructureNode(
            node_id="NODE-ISRU-WATER",
            name="Subsurface Regolith Excavation & Water Sublimation Plant",
            element=MoonToMarsElement.ISRU,
            prerequisites=["NODE-POWER-DIST"],
            power_demand_kw=28.0,
            thermal_load_kw=14.0,
            data_rate_kbps=128.0,
            state=NodeCommissioningState.COMMISSIONED,
            is_critical_path=True,
            description="Thermal auger reactors and condenser loops producing raw H2O.",
        ))
        dag.add_node(InfrastructureNode(
            node_id="NODE-ISRU-OXYGEN",
            name="Atmospheric CO2 Capture & Electrolysis (MOXIE/Sabatier)",
            element=MoonToMarsElement.ISRU,
            prerequisites=["NODE-POWER-DIST", "NODE-ISRU-WATER"],
            power_demand_kw=22.0,
            thermal_load_kw=8.0,
            data_rate_kbps=64.0,
            state=NodeCommissioningState.COMMISSIONED,
            is_critical_path=True,
            description="Solid oxide electrolysis and catalytic Sabatier methane reactors.",
        ))

        # Habitation & Life Support (Phase C & D)
        dag.add_node(InfrastructureNode(
            node_id="NODE-HAB-STRUCT",
            name="Primary Expandable Habitat Structural Shell & Regolith Berm",
            element=MoonToMarsElement.HABITATION,
            prerequisites=["NODE-LANDING-BERM", "NODE-POWER-DIST"],
            power_demand_kw=8.0,
            thermal_load_kw=4.0,
            data_rate_kbps=512.0,
            state=NodeCommissioningState.COMMISSIONED,
            is_critical_path=True,
            description="Multilayer bladder shell reinforced with 1.5m sintered regolith shielding.",
        ))
        dag.add_node(InfrastructureNode(
            node_id="NODE-HAB-ECLSS",
            name="Environmental Control & Life Support System (ECLSS)",
            element=MoonToMarsElement.HABITATION,
            prerequisites=["NODE-HAB-STRUCT", "NODE-ISRU-WATER", "NODE-ISRU-OXYGEN"],
            power_demand_kw=18.5,
            thermal_load_kw=12.0,
            data_rate_kbps=256.0,
            state=NodeCommissioningState.COMMISSIONED,
            is_critical_path=True,
            description="Atmospheric revitalizer, trace contaminant scrubber, and water recovery loop.",
        ))

        # Science, Fleet & Maintenance (Phase D & E)
        dag.add_node(InfrastructureNode(
            node_id="NODE-ROVER-DEPOT",
            name="Surface Mobility Charging Depot & Maintenance Bay",
            element=MoonToMarsElement.SURFACE_MOBILITY,
            prerequisites=["NODE-POWER-DIST"],
            power_demand_kw=15.0,
            thermal_load_kw=4.5,
            data_rate_kbps=1024.0,
            state=NodeCommissioningState.COMMISSIONED,
            description="Automated inductive charging pads and robotic manipulators.",
        ))
        dag.add_node(InfrastructureNode(
            node_id="NODE-SCIENCE-LAB",
            name="Geochemistry & Astrobiology Analytical Laboratory",
            element=MoonToMarsElement.SCIENCE_UTILIZATION,
            prerequisites=["NODE-HAB-STRUCT", "NODE-POWER-DIST", "NODE-COMM-RELAY"],
            power_demand_kw=14.0,
            thermal_load_kw=6.0,
            data_rate_kbps=4096.0,
            state=NodeCommissioningState.COMMISSIONED,
            description="Class-100 clean gloveboxes, mass spectrometers, and sample storage.",
        ))

        return dag
