"""MarsWalk 2.0 / Project Atlas  Milestone 13R: Cascading Failure Propagation Engine.

Implements causal failure propagation DAGs with Boolean AND/OR logic gates,
resource-dependent activation thresholds, containment boundaries, and
traceable root-cause cascade path synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class GateLogic(str, Enum):
    """Boolean aggregation logic for incoming causal edges."""
    OR = "OR"                # Any single parent failure triggers downstream cascade
    AND = "AND"              # All parent failures must co-occur to trigger cascade
    THRESHOLD = "THRESHOLD"  # Resource or telemetry parameter exceeds numerical limit


@dataclass
class PropagationEdge:
    """Directed causal dependency between two subsystems/failure nodes."""
    source_node: str
    target_node: str
    gate: GateLogic = GateLogic.OR
    propagation_delay_s: float = 0.0
    containment_barrier: Optional[str] = None  # Boundary action that severs this edge
    activation_threshold: Optional[float] = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_node": self.source_node,
            "target_node": self.target_node,
            "gate": self.gate.value,
            "propagation_delay_s": self.propagation_delay_s,
            "containment_barrier": self.containment_barrier,
            "activation_threshold": self.activation_threshold,
            "description": self.description,
        }


@dataclass
class CascadeNodeState:
    """State of an individual node in the failure propagation network."""
    node_id: str
    name: str
    subsystem: str
    is_failed: bool = False
    failure_timestamp_s: Optional[float] = None
    root_cause_id: Optional[str] = None
    causal_depth: int = 0
    active_containment: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "subsystem": self.subsystem,
            "is_failed": self.is_failed,
            "failure_timestamp_s": self.failure_timestamp_s,
            "root_cause_id": self.root_cause_id,
            "causal_depth": self.causal_depth,
            "active_containment": self.active_containment,
        }


@dataclass
class CausalTrace:
    """Traceable path from root-cause fault to downstream consequential failure."""
    root_cause: str
    target_failure: str
    path: List[str]
    total_propagation_time_s: float
    containment_opportunities: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_cause": self.root_cause,
            "target_failure": self.target_failure,
            "path": self.path,
            "total_propagation_time_s": round(self.total_propagation_time_s, 2),
            "containment_opportunities": self.containment_opportunities,
        }


class FailurePropagationGraph:
    """Causal DAG modeling cascading fault propagation across planetary assets."""

    def __init__(self):
        self._nodes: Dict[str, CascadeNodeState] = {}
        self._edges: List[PropagationEdge] = []
        self._incoming: Dict[str, List[PropagationEdge]] = {}
        self._outgoing: Dict[str, List[PropagationEdge]] = {}
        self._active_barriers: Set[str] = set()

    def add_node(self, node_id: str, name: str, subsystem: str) -> CascadeNodeState:
        if node_id not in self._nodes:
            node = CascadeNodeState(node_id=node_id, name=name, subsystem=subsystem)
            self._nodes[node_id] = node
            self._incoming[node_id] = []
            self._outgoing[node_id] = []
        return self._nodes[node_id]

    def add_edge(
        self,
        source: str,
        target: str,
        gate: GateLogic = GateLogic.OR,
        propagation_delay_s: float = 0.0,
        containment_barrier: Optional[str] = None,
        activation_threshold: Optional[float] = None,
        description: str = "",
    ) -> PropagationEdge:
        if source not in self._nodes:
            self.add_node(source, source, "GENERIC")
        if target not in self._nodes:
            self.add_node(target, target, "GENERIC")

        edge = PropagationEdge(
            source_node=source,
            target_node=target,
            gate=gate,
            propagation_delay_s=propagation_delay_s,
            containment_barrier=containment_barrier,
            activation_threshold=activation_threshold,
            description=description,
        )
        self._edges.append(edge)
        self._outgoing[source].append(edge)
        self._incoming[target].append(edge)
        return edge

    def activate_containment_barrier(self, barrier_name: str) -> None:
        """Activates an operational containment barrier to isolate cascading faults."""
        self._active_barriers.add(barrier_name)

    def deactivate_containment_barrier(self, barrier_name: str) -> None:
        self._active_barriers.discard(barrier_name)

    def inject_root_failure(self, node_id: str, timestamp_s: float = 0.0) -> None:
        """Injects a primal root-cause failure into the network."""
        if node_id in self._nodes:
            node = self._nodes[node_id]
            node.is_failed = True
            node.failure_timestamp_s = timestamp_s
            node.root_cause_id = node_id
            node.causal_depth = 0

    def propagate(self, current_time_s: float) -> List[str]:
        """Propagates active failures through the causal DAG according to gates and barriers.

        Returns list of newly failed node IDs in this propagation sweep.
        """
        newly_failed: List[str] = []
        changed = True

        while changed:
            changed = False
            for node_id, node in self._nodes.items():
                if node.is_failed:
                    continue

                incoming_edges = self._incoming.get(node_id, [])
                if not incoming_edges:
                    continue

                # Group by gate logic or evaluate according to incoming edges
                can_trigger = False
                trigger_time = current_time_s
                root_id = None
                max_depth = 0

                # Check if all or any parents satisfy condition
                active_parents = []
                for edge in incoming_edges:
                    # Check if containment barrier blocks this edge
                    if edge.containment_barrier and edge.containment_barrier in self._active_barriers:
                        continue

                    parent_node = self._nodes[edge.source_node]
                    if parent_node.is_failed:
                        req_time = (parent_node.failure_timestamp_s or 0.0) + edge.propagation_delay_s
                        if current_time_s >= req_time:
                            active_parents.append((parent_node, edge))

                if not active_parents:
                    continue

                # Evaluate primary gate logic
                sample_edge = incoming_edges[0]
                if sample_edge.gate == GateLogic.OR:
                    if len(active_parents) >= 1:
                        can_trigger = True
                        p_node, p_edge = active_parents[0]
                        trigger_time = (p_node.failure_timestamp_s or 0.0) + p_edge.propagation_delay_s
                        root_id = p_node.root_cause_id or p_node.node_id
                        max_depth = p_node.causal_depth + 1

                elif sample_edge.gate == GateLogic.AND:
                    # All incoming non-blocked edges must have active failed parents
                    valid_incoming = [e for e in incoming_edges if not (e.containment_barrier and e.containment_barrier in self._active_barriers)]
                    if len(active_parents) == len(valid_incoming) and len(valid_incoming) > 0:
                        can_trigger = True
                        latest_time = max((p.failure_timestamp_s or 0.0) + e.propagation_delay_s for p, e in active_parents)
                        trigger_time = latest_time
                        root_id = active_parents[0][0].root_cause_id or active_parents[0][0].node_id
                        max_depth = max(p.causal_depth for p, _ in active_parents) + 1

                if can_trigger:
                    node.is_failed = True
                    node.failure_timestamp_s = trigger_time
                    node.root_cause_id = root_id
                    node.causal_depth = max_depth
                    newly_failed.append(node_id)
                    changed = True

        return newly_failed

    def find_causal_traces(self, target_node: str) -> List[CausalTrace]:
        """Synthesizes all distinct causal paths leading to a target failure."""
        traces: List[CausalTrace] = []
        if target_node not in self._nodes or not self._nodes[target_node].is_failed:
            return traces

        def dfs(current: str, path: List[str], total_delay: float, barriers: List[str]):
            current_node = self._nodes[current]
            if current_node.causal_depth == 0:
                # Reached root cause
                traces.append(CausalTrace(
                    root_cause=current,
                    target_failure=target_node,
                    path=list(reversed(path)),
                    total_propagation_time_s=total_delay,
                    containment_opportunities=barriers,
                ))
                return

            for edge in self._incoming.get(current, []):
                parent = self._nodes[edge.source_node]
                if parent.is_failed and parent.causal_depth < current_node.causal_depth:
                    next_barriers = list(barriers)
                    if edge.containment_barrier:
                        next_barriers.append(edge.containment_barrier)
                    dfs(edge.source_node, path + [edge.source_node], total_delay + edge.propagation_delay_s, next_barriers)

        dfs(target_node, [target_node], 0.0, [])
        return traces

    def get_state(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self._nodes),
            "failed_nodes": [n.to_dict() for n in self._nodes.values() if n.is_failed],
            "nominal_nodes": [n.to_dict() for n in self._nodes.values() if not n.is_failed],
            "total_edges": len(self._edges),
            "edges": [e.to_dict() for e in self._edges],
            "active_containment_barriers": list(self._active_barriers),
        }

    @staticmethod
    def build_standard_planetary_dag() -> FailurePropagationGraph:
        """Constructs the canonical 13R multi-asset Martian mission failure DAG."""
        dag = FailurePropagationGraph()

        # 1. Environmental Roots
        dag.add_node("ENV_DUST_STORM_TAU", "Regional Dust Storm Tau Spike", "ENVIRONMENT")
        dag.add_node("ENV_TEMPERATURE_DROP", "Nighttime Thermal Cold-Soak", "ENVIRONMENT")

        # 2. Rover Subsystems
        dag.add_node("ROV_MOTOR_FR_STALL", "Front-Right Wheel Drive Motor Stall", "MOBILITY")
        dag.add_node("ROV_POWER_BUS_SURGE", "Chassis Main 28V Power Bus Overcurrent", "POWER")
        dag.add_node("ROV_SPEED_DEGRADATION", "Traversal Speed Limiting (5-Wheel Drag)", "MOBILITY")
        dag.add_node("ROV_SCHEDULE_SLIP", "Sol Science Traverse Schedule Margin Collapse", "CAMPAIGN")
        dag.add_node("ROV_UHF_TRANSCEIVER_FAIL", "UHF Electra Transceiver Dropout", "COMMUNICATIONS")
        dag.add_node("ROV_BUFFER_OVERFLOW", "Flash Solid-State Buffer Saturation", "AVIONICS")
        dag.add_node("ROV_DATA_PURGE", "Non-Critical Science Data Eviction/Loss", "SCIENCE")

        # 3. Aircraft Subsystems
        dag.add_node("AERO_BLADE_EROSION", "Rotor Blade Dust Erosion & Pitting", "PROPULSION")
        dag.add_node("AERO_LIFT_DEFICIT", "Rotor Aerodynamic Stall Margin Deficit", "PROPULSION")
        dag.add_node("AERO_MOTOR_OVERHEAT", "Flight Motor Thermal Ceiling Exceeded", "PROPULSION")
        dag.add_node("AERO_EMERGENCY_DESCENT", "Unplanned Ballistic/Autorotative Descent", "FLIGHT_CONTROL")
        dag.add_node("AERO_SOLAR_DEPLETION", "Solar Array Dust Coverage Power Loss", "POWER")
        dag.add_node("AERO_BATTERY_COLLAPSE", "Ingenuity Li-ion Voltage Floor Drop", "POWER")

        # 4. Instrument Payloads
        dag.add_node("SCI_PIXL_THERMAL_DRIFT", "PIXL Spectrometer Thermal Calibration Drift", "SCIENCE_PAYLOAD")
        dag.add_node("SCI_FALSE_DISCOVERY", "Spurious Carbonate Detection in Basalt", "SCIENCE_PAYLOAD")

        # Edges & Cascade Logic

        # Rover Wheel Stall Cascade
        dag.add_edge(
            "ROV_MOTOR_FR_STALL", "ROV_POWER_BUS_SURGE",
            gate=GateLogic.OR, propagation_delay_s=5.0,
            containment_barrier="ISOLATE_FL_MOTOR",
            description="Motor stall draws 65W stall current through main bus",
        )
        dag.add_edge(
            "ROV_MOTOR_FR_STALL", "ROV_SPEED_DEGRADATION",
            gate=GateLogic.OR, propagation_delay_s=15.0,
            containment_barrier="REPLAN_DRAG_TRAVERSAL",
            description="Dragging frozen wheel reduces traversal velocity by 45%",
        )
        dag.add_edge(
            "ROV_SPEED_DEGRADATION", "ROV_SCHEDULE_SLIP",
            gate=GateLogic.OR, propagation_delay_s=120.0,
            containment_barrier="DEFER_SECONDARY_SCIENCE",
            description="Reduced speed exhausts sol navigation time margin",
        )

        # Comm Blackout & Buffer Overflow Cascade
        dag.add_edge(
            "ROV_UHF_TRANSCEIVER_FAIL", "ROV_BUFFER_OVERFLOW",
            gate=GateLogic.OR, propagation_delay_s=300.0,
            containment_barrier="SWITCH_TO_DTE_HIGH_GAIN",
            description="Blocked UHF downlink causes science images to accumulate in flash buffer",
        )
        dag.add_edge(
            "ROV_BUFFER_OVERFLOW", "ROV_DATA_PURGE",
            gate=GateLogic.OR, propagation_delay_s=600.0,
            containment_barrier="FREEZE_NEW_ACQUISITIONS",
            description="Ring buffer overflow triggers unrecoverable data deletion",
        )

        # Environmental & Aircraft Cascade
        dag.add_edge(
            "ENV_DUST_STORM_TAU", "AERO_SOLAR_DEPLETION",
            gate=GateLogic.OR, propagation_delay_s=180.0,
            containment_barrier="SURVIVAL_HEATER_CLAMP",
            description="Atmospheric tau rise starves solar panel charging",
        )
        dag.add_edge(
            "AERO_SOLAR_DEPLETION", "AERO_BATTERY_COLLAPSE",
            gate=GateLogic.OR, propagation_delay_s=600.0,
            containment_barrier="HIBERNATION_DEEP_SLEEP",
            description="Battery voltage collapses below survival cutoff",
        )
        dag.add_edge(
            "AERO_BLADE_EROSION", "AERO_LIFT_DEFICIT",
            gate=GateLogic.OR, propagation_delay_s=60.0,
            containment_barrier="RESTRICT_FLIGHT_CEILING",
            description="Surface abrasion destroys laminar rotor boundary layer",
        )
        dag.add_edge(
            "AERO_LIFT_DEFICIT", "AERO_MOTOR_OVERHEAT",
            gate=GateLogic.OR, propagation_delay_s=120.0,
            containment_barrier="ABORT_FLIGHT_IMMEDIATE_TOUCHDOWN",
            description="Rotor controller commands maximum RPM to compensate for lift deficit",
        )
        dag.add_edge(
            "AERO_MOTOR_OVERHEAT", "AERO_EMERGENCY_DESCENT",
            gate=GateLogic.OR, propagation_delay_s=30.0,
            containment_barrier="CONTROLLED_POWERED_DESCENT",
            description="Thermal protection shutdown triggers ballistic touchdown",
        )

        # Instrument Drift
        dag.add_edge(
            "SCI_PIXL_THERMAL_DRIFT", "SCI_FALSE_DISCOVERY",
            gate=GateLogic.OR, propagation_delay_s=45.0,
            containment_barrier="CALIBRATION_TARGET_VERIFICATION",
            description="Sensor energy shift biases spectral centroid into carbonate peak",
        )

        return dag
