"""
MarsWalk 2.0 / Project Atlas — Milestone 13K Goal Decomposition & Directed Acyclic Task Graph
=============================================================================================
Decomposes high-level validated mission intent into a formal Directed Acyclic Graph (DAG)
of executable planetary tasks: traverses, target arrivals, instrument preparations,
in-situ science observations, relay deployments, simulated downlinks, and sol checkpoints.
Enforces strict topological ordering, dependency verification, and critical path analysis.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.mission_intent import MissionIntent, ScienceObjectiveCategory
from marswalk.core.fleet_operations_director import (
    RoverUnitConfig,
    create_default_fleet_rovers,
)
from marswalk.core.fleet_task_allocator import (
    FleetScienceTarget,
    get_default_jezero_targets,
    PRIORITY_WEIGHTS,
)
from marswalk.core.science_mission_planner import (
    INSTRUMENT_CATALOG,
    InstrumentId,
    ScienceObjective,
)


class MissionTaskType(str, Enum):
    TRAVERSE = "TRAVERSE"
    REACH_TARGET = "REACH_TARGET"
    PREPARE_INSTRUMENT = "PREPARE_INSTRUMENT"
    OBSERVE = "OBSERVE"
    DEPLOY_RELAY = "DEPLOY_RELAY"
    SIMULATED_DATA_TRANSFER = "SIMULATED_DATA_TRANSFER"
    STANDBY = "STANDBY"
    CAMPAIGN_CHECKPOINT = "CAMPAIGN_CHECKPOINT"
    RECOVERY = "RECOVERY"


class MissionTaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass
class MissionTaskNode:
    """
    Discrete node within the mission task execution graph.
    Represents an atomic operation assigned to an exploration rover or infrastructure unit.
    """
    task_id: str
    task_type: str
    name: str
    parent_goal_id: str
    assigned_rover_id: Optional[str] = None
    target_id: Optional[str] = None
    location_rc: Tuple[int, int] = (128, 128)
    prerequisite_task_ids: List[str] = field(default_factory=list)
    estimated_duration_s: float = 0.0
    estimated_energy_wh: float = 0.0
    estimated_data_mb: float = 0.0
    required_instrument_id: Optional[str] = None
    status: str = MissionTaskStatus.PENDING.value
    sol_index: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "name": self.name,
            "parent_goal_id": self.parent_goal_id,
            "assigned_rover_id": self.assigned_rover_id,
            "target_id": self.target_id,
            "location_rc": list(self.location_rc),
            "prerequisite_task_ids": list(self.prerequisite_task_ids),
            "estimated_duration_s": round(self.estimated_duration_s, 1),
            "estimated_energy_wh": round(self.estimated_energy_wh, 2),
            "estimated_data_mb": round(self.estimated_data_mb, 2),
            "required_instrument_id": self.required_instrument_id,
            "status": self.status,
            "sol_index": self.sol_index,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MissionTaskNode":
        raw_loc = data.get("location_rc", [128, 128])
        return cls(
            task_id=str(data["task_id"]),
            task_type=str(data["task_type"]),
            name=str(data.get("name", data["task_id"])),
            parent_goal_id=str(data.get("parent_goal_id", "goal_primary")),
            assigned_rover_id=data.get("assigned_rover_id"),
            target_id=data.get("target_id"),
            location_rc=(int(raw_loc[0]), int(raw_loc[1])),
            prerequisite_task_ids=list(data.get("prerequisite_task_ids", [])),
            estimated_duration_s=float(data.get("estimated_duration_s", 0.0)),
            estimated_energy_wh=float(data.get("estimated_energy_wh", 0.0)),
            estimated_data_mb=float(data.get("estimated_data_mb", 0.0)),
            required_instrument_id=data.get("required_instrument_id"),
            status=str(data.get("status", MissionTaskStatus.PENDING.value)),
            sol_index=int(data.get("sol_index", 1)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class MissionTaskGraph:
    """
    Formal Directed Acyclic Graph (DAG) of all decomposed mission tasks.
    Maintains explicit edges, roots, terminals, and topological ordering.
    """
    graph_id: str
    intent_id: str
    tasks: Dict[str, MissionTaskNode] = field(default_factory=dict)
    edges: List[Tuple[str, str]] = field(default_factory=list)  # (prereq_id, dependent_id)
    root_task_ids: List[str] = field(default_factory=list)
    terminal_task_ids: List[str] = field(default_factory=list)
    created_at_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    @property
    def total_tasks_count(self) -> int:
        return len(self.tasks)

    @property
    def total_duration_s(self) -> float:
        return sum(t.estimated_duration_s for t in self.tasks.values())

    @property
    def total_energy_wh(self) -> float:
        return sum(t.estimated_energy_wh for t in self.tasks.values())

    @property
    def total_data_mb(self) -> float:
        return sum(t.estimated_data_mb for t in self.tasks.values())

    def add_task(self, task: MissionTaskNode) -> None:
        """Inserts a task node into the graph and registers prerequisite edges."""
        self.tasks[task.task_id] = task
        for prereq in task.prerequisite_task_ids:
            edge = (prereq, task.task_id)
            if edge not in self.edges:
                self.edges.append(edge)
        self._recompute_roots_and_terminals()

    def _recompute_roots_and_terminals(self) -> None:
        """Updates root (in-degree = 0) and terminal (out-degree = 0) task IDs."""
        all_task_ids = set(self.tasks.keys())
        prereqs = {edge[0] for edge in self.edges}
        dependents = {edge[1] for edge in self.edges}
        self.root_task_ids = sorted(list(all_task_ids - dependents))
        self.terminal_task_ids = sorted(list(all_task_ids - prereqs))

    def validate_acyclic(self) -> bool:
        """
        Validates that the task graph contains no cyclic dependencies.
        Returns True if strictly acyclic, False otherwise.
        """
        try:
            self.topological_sort()
            return True
        except ValueError:
            return False

    def topological_sort(self) -> List[str]:
        """
        Computes a valid topological ordering of tasks using Kahn's algorithm.
        Raises ValueError if a cycle is detected.
        """
        in_degree: Dict[str, int] = {t_id: 0 for t_id in self.tasks}
        adj: Dict[str, List[str]] = {t_id: [] for t_id in self.tasks}

        for u, v in self.edges:
            if u in adj and v in in_degree:
                adj[u].append(v)
                in_degree[v] += 1

        queue = [t_id for t_id, deg in in_degree.items() if deg == 0]
        sorted_ids: List[str] = []

        while queue:
            # Deterministic pop
            queue.sort()
            curr = queue.pop(0)
            sorted_ids.append(curr)

            for neighbor in adj.get(curr, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_ids) != len(self.tasks):
            missing = set(self.tasks.keys()) - set(sorted_ids)
            raise ValueError(f"Task graph contains cyclic dependencies involving nodes: {missing}")

        return sorted_ids

    def get_critical_path(self) -> List[str]:
        """
        Computes the critical path (longest duration sequence) through the task DAG.
        Returns ordered list of task IDs on the critical path.
        """
        if not self.tasks:
            return []

        try:
            topo_order = self.topological_sort()
        except ValueError:
            return []

        dist: Dict[str, float] = {t_id: self.tasks[t_id].estimated_duration_s for t_id in self.tasks}
        parent: Dict[str, Optional[str]] = {t_id: None for t_id in self.tasks}

        # Forward dynamic programming
        for u in topo_order:
            for source, target in self.edges:
                if source == u and target in dist:
                    cand = dist[u] + self.tasks[target].estimated_duration_s
                    if cand > dist[target]:
                        dist[target] = cand
                        parent[target] = u

        # Find terminal with maximum distance
        best_terminal = max(self.tasks.keys(), key=lambda t_id: dist.get(t_id, 0.0))
        
        path: List[str] = []
        curr: Optional[str] = best_terminal
        while curr:
            path.append(curr)
            curr = parent.get(curr)

        path.reverse()
        return path

    def get_rover_subgraph(self, rover_id: str) -> List[MissionTaskNode]:
        """Returns all tasks assigned to a specific rover in topological order."""
        topo = self.topological_sort()
        return [self.tasks[t_id] for t_id in topo if self.tasks[t_id].assigned_rover_id == rover_id]

    def get_sol_subgraph(self, sol_index: int) -> List[MissionTaskNode]:
        """Returns all tasks scheduled for a specific sol in topological order."""
        topo = self.topological_sort()
        return [self.tasks[t_id] for t_id in topo if self.tasks[t_id].sol_index == sol_index]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "intent_id": self.intent_id,
            "tasks": {t_id: node.to_dict() for t_id, node in self.tasks.items()},
            "edges": [list(e) for e in self.edges],
            "root_task_ids": list(self.root_task_ids),
            "terminal_task_ids": list(self.terminal_task_ids),
            "total_tasks_count": self.total_tasks_count,
            "total_duration_s": round(self.total_duration_s, 1),
            "total_energy_wh": round(self.total_energy_wh, 2),
            "total_data_mb": round(self.total_data_mb, 2),
            "is_acyclic": self.validate_acyclic(),
            "critical_path": self.get_critical_path(),
            "created_at_utc": self.created_at_utc,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MissionTaskGraph":
        graph = cls(
            graph_id=str(data["graph_id"]),
            intent_id=str(data["intent_id"]),
            created_at_utc=str(data.get("created_at_utc", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))),
        )
        tasks_raw = data.get("tasks", {})
        for t_id, t_dict in tasks_raw.items():
            graph.tasks[t_id] = MissionTaskNode.from_dict(t_dict)
        
        edges_raw = data.get("edges", [])
        graph.edges = [(str(e[0]), str(e[1])) for e in edges_raw]
        graph._recompute_roots_and_terminals()
        return graph


class MissionGoalCompiler:
    """
    Decomposes validated mission intents into coherent multi-rover Directed Acyclic Task Graphs.
    Synthesizes required traverse legs, instrument observation routines, relay deployments,
    and downlink sync tasks while maintaining dependency invariants.
    """

    def __init__(self, terrain_shape: Tuple[int, int] = (250, 250)):
        self.terrain_height, self.terrain_width = terrain_shape
        self.default_targets = {t.target_id: t for t in get_default_jezero_targets()}
        self.default_rovers = {r.rover_id: r for r in create_default_fleet_rovers()}

    def _select_instrument_profile(
        self,
        objective: str,
        permitted_instruments: List[str]
    ) -> Optional[Tuple[str, str, float, float, float]]:
        """
        Selects best instrument profile matching the target objective from permitted rover instruments.
        Returns: (instrument_id, mode_name, duration_s, power_draw_w, data_mb)
        """
        for mode_key, profile in INSTRUMENT_CATALOG.items():
            inst_name = profile.instrument_id.value
            if inst_name in permitted_instruments:
                for comp_obj in profile.compatible_objectives:
                    if comp_obj.value == objective or objective in comp_obj.value or comp_obj.value in objective:
                        duration_s = profile.duration_s
                        power_w = profile.power_draw_w
                        data_mb = profile.expected_data_bytes / (1024 * 1024)
                        return (inst_name, profile.mode_name, duration_s, power_w, data_mb)

        # Fallback to general imaging (MASTCAM_Z)
        if "MASTCAM_Z" in permitted_instruments and "MASTCAM_Z_PANO" in INSTRUMENT_CATALOG:
            prof = INSTRUMENT_CATALOG["MASTCAM_Z_PANO"]
            return ("MASTCAM_Z", prof.mode_name, prof.duration_s, prof.power_draw_w, prof.expected_data_bytes / (1024 * 1024))
        
        # Generic conservative fallback
        return (permitted_instruments[0] if permitted_instruments else "MASTCAM_Z", "DEFAULT_MODE", 600.0, 45.0, 15.0)

    def decompose_mission_intent(
        self,
        intent: MissionIntent,
        candidate_targets: Optional[List[FleetScienceTarget]] = None,
        candidate_rovers: Optional[List[RoverUnitConfig]] = None,
    ) -> MissionTaskGraph:
        """
        Translates a validated MissionIntent into a fully connected, verified MissionTaskGraph.
        """
        graph_id = f"graph_{intent.intent_id}_{int(time.time())}"
        graph = MissionTaskGraph(graph_id=graph_id, intent_id=intent.intent_id)

        target_pool = {t.target_id: t for t in (candidate_targets or get_default_jezero_targets())}
        rover_pool = {r.rover_id: r for r in (candidate_rovers or create_default_fleet_rovers())}

        # 1. Determine active fleet
        active_rovers: List[RoverUnitConfig] = []
        for r_id in intent.fleet.permitted_rover_ids:
            if r_id in rover_pool:
                active_rovers.append(rover_pool[r_id])
                if len(active_rovers) >= intent.fleet.maximum_rovers:
                    break

        if not active_rovers:
            # Fallback to first available rover
            active_rovers = [list(rover_pool.values())[0]]

        # 2. Select and rank targets
        selected_targets: List[FleetScienceTarget] = []
        # Mandatory targets first
        for m_id in intent.science.mandatory_target_ids:
            if m_id in target_pool and target_pool[m_id] not in selected_targets:
                selected_targets.append(target_pool[m_id])

        # Preferred targets next
        for p_id in intent.science.preferred_target_ids:
            if p_id in target_pool and target_pool[p_id] not in selected_targets:
                selected_targets.append(target_pool[p_id])

        # Fill with other compatible targets up to limit
        for t_id, target in target_pool.items():
            if len(selected_targets) >= intent.science.maximum_targets_limit:
                break
            if target not in selected_targets:
                selected_targets.append(target)

        # 3. Target-to-rover allocation (round-robin / instrument-aware)
        rover_targets: Dict[str, List[FleetScienceTarget]] = {r.rover_id: [] for r in active_rovers}
        for idx, target in enumerate(selected_targets):
            # Check mandatory assignment
            mand_rover = intent.fleet.mandatory_rover_assignments.get(target.target_id)
            if mand_rover and mand_rover in rover_targets:
                rover_targets[mand_rover].append(target)
            else:
                # Find rover with compatible instruments
                assigned = False
                for r in active_rovers:
                    inst = self._select_instrument_profile(target.objective, r.instrument_ids)
                    if inst and inst[0] in r.instrument_ids:
                        rover_targets[r.rover_id].append(target)
                        assigned = True
                        break
                if not assigned:
                    # Round robin fallback
                    target_rover_id = active_rovers[idx % len(active_rovers)].rover_id
                    rover_targets[target_rover_id].append(target)

        # 4. Sol Distribution & Task Generation
        max_sols = max(1, intent.timeline.maximum_sols)
        base_station_rc = intent.geography.base_station_rc
        downlink_bw_mbps = max(0.5, intent.resources.shared_downlink_bandwidth_mbps)

        # Deploy Relay Task (if permitted and budgeted)
        relay_task_id: Optional[str] = None
        if intent.communications.maximum_relays_deployable > 0:
            deployer_rover = active_rovers[-1] if len(active_rovers) > 1 else active_rovers[0]
            relay_loc = (142, 138)  # Strategic high ridge in western delta
            relay_task_id = f"task_deploy_relay_{deployer_rover.rover_id}_sol1"
            relay_task = MissionTaskNode(
                task_id=relay_task_id,
                task_type=MissionTaskType.DEPLOY_RELAY.value,
                name=f"Deploy Surface Relay Alpha ({deployer_rover.name})",
                parent_goal_id="goal_communications_backbone",
                assigned_rover_id=deployer_rover.rover_id,
                location_rc=relay_loc,
                prerequisite_task_ids=[],
                estimated_duration_s=1200.0,
                estimated_energy_wh=65.0,
                estimated_data_mb=5.0,
                required_instrument_id=None,
                sol_index=1,
                metadata={"relay_name": "RELAY_ALPHA", "elevation_m": -2480.0},
            )
            graph.add_task(relay_task)

        # Generate rover operational task sequences per sol
        last_sol_checkpoint_id: Optional[str] = None

        for sol in range(1, max_sols + 1):
            sol_checkpoint_ids: List[str] = []

            for rover in active_rovers:
                r_id = rover.rover_id
                all_targets_for_rover = rover_targets.get(r_id, [])
                
                # Split targets across sols
                targets_per_sol = math.ceil(len(all_targets_for_rover) / max_sols) if all_targets_for_rover else 0
                start_idx = (sol - 1) * targets_per_sol
                end_idx = min(len(all_targets_for_rover), start_idx + targets_per_sol)
                sol_targets = all_targets_for_rover[start_idx:end_idx]

                prev_task_id: Optional[str] = None
                if sol == 1:
                    if r_id == active_rovers[-1].rover_id and relay_task_id:
                        prev_task_id = relay_task_id
                else:
                    prev_task_id = last_sol_checkpoint_id

                curr_loc = intent.geography.starting_location_rc if sol == 1 else base_station_rc

                for t_idx, target in enumerate(sol_targets):
                    # Step A: TRAVERSE
                    dist_cells = math.hypot(target.location_rc[0] - curr_loc[0], target.location_rc[1] - curr_loc[1])
                    dist_m = dist_cells * 20.0  # 20m CTX pixel resolution
                    trav_dur_s = dist_m / rover.nominal_speed_mps
                    trav_energy_wh = (dist_m * 0.18) + (trav_dur_s * rover.base_electrical_load_w / 3600.0)

                    trav_task_id = f"task_trav_{r_id}_sol{sol}_tgt{t_idx+1}"
                    trav_prereqs = [prev_task_id] if prev_task_id else []
                    trav_task = MissionTaskNode(
                        task_id=trav_task_id,
                        task_type=MissionTaskType.TRAVERSE.value,
                        name=f"Traverse to {target.name} ({r_id})",
                        parent_goal_id=f"goal_reach_{target.target_id}",
                        assigned_rover_id=r_id,
                        target_id=target.target_id,
                        location_rc=target.location_rc,
                        prerequisite_task_ids=trav_prereqs,
                        estimated_duration_s=trav_dur_s,
                        estimated_energy_wh=trav_energy_wh,
                        estimated_data_mb=2.0,
                        sol_index=sol,
                        metadata={"distance_m": dist_m, "start_rc": curr_loc, "end_rc": target.location_rc},
                    )
                    graph.add_task(trav_task)

                    # Step B: REACH_TARGET
                    reach_task_id = f"task_reach_{r_id}_sol{sol}_tgt{t_idx+1}"
                    reach_task = MissionTaskNode(
                        task_id=reach_task_id,
                        task_type=MissionTaskType.REACH_TARGET.value,
                        name=f"Arrive & Settle at {target.name}",
                        parent_goal_id=f"goal_investigate_{target.target_id}",
                        assigned_rover_id=r_id,
                        target_id=target.target_id,
                        location_rc=target.location_rc,
                        prerequisite_task_ids=[trav_task_id],
                        estimated_duration_s=300.0,
                        estimated_energy_wh=10.0,
                        estimated_data_mb=0.5,
                        sol_index=sol,
                        metadata={"settling_time_s": 300.0},
                    )
                    graph.add_task(reach_task)

                    # Step C: PREPARE_INSTRUMENT & OBSERVE
                    inst_profile = self._select_instrument_profile(target.objective, rover.instrument_ids)
                    inst_id, mode_name, dwell_s, pwr_w, data_mb = inst_profile or ("MASTCAM_Z", "PANO", 900.0, 50.0, 20.0)
                    obs_energy_wh = (dwell_s * pwr_w) / 3600.0

                    prep_task_id = f"task_prep_{r_id}_sol{sol}_tgt{t_idx+1}"
                    prep_task = MissionTaskNode(
                        task_id=prep_task_id,
                        task_type=MissionTaskType.PREPARE_INSTRUMENT.value,
                        name=f"Prepare {inst_id} ({mode_name})",
                        parent_goal_id=f"goal_investigate_{target.target_id}",
                        assigned_rover_id=r_id,
                        target_id=target.target_id,
                        location_rc=target.location_rc,
                        prerequisite_task_ids=[reach_task_id],
                        estimated_duration_s=300.0,
                        estimated_energy_wh=12.0,
                        estimated_data_mb=0.2,
                        required_instrument_id=inst_id,
                        sol_index=sol,
                        metadata={"instrument_mode": mode_name},
                    )
                    graph.add_task(prep_task)

                    obs_task_id = f"task_obs_{r_id}_sol{sol}_tgt{t_idx+1}"
                    obs_task = MissionTaskNode(
                        task_id=obs_task_id,
                        task_type=MissionTaskType.OBSERVE.value,
                        name=f"Scientific Observation: {target.name}",
                        parent_goal_id=f"goal_science_{target.target_id}",
                        assigned_rover_id=r_id,
                        target_id=target.target_id,
                        location_rc=target.location_rc,
                        prerequisite_task_ids=[prep_task_id],
                        estimated_duration_s=dwell_s,
                        estimated_energy_wh=obs_energy_wh,
                        estimated_data_mb=data_mb,
                        required_instrument_id=inst_id,
                        sol_index=sol,
                        metadata={
                            "science_utility": target.base_utility * PRIORITY_WEIGHTS.get(target.priority, 1.0),
                            "objective": target.objective,
                        },
                    )
                    graph.add_task(obs_task)

                    # Step D: SIMULATED_DATA_TRANSFER
                    dl_dur_s = (data_mb * 8.0) / downlink_bw_mbps
                    dl_energy_wh = (dl_dur_s * 40.0) / 3600.0  # 40W RF transmitter

                    dl_prereqs = [obs_task_id]
                    if relay_task_id and relay_task_id in graph.tasks and relay_task_id not in dl_prereqs:
                        # Relay should be deployed before distant downlinks
                        dl_prereqs.append(relay_task_id)

                    dl_task_id = f"task_downlink_{r_id}_sol{sol}_tgt{t_idx+1}"
                    dl_task = MissionTaskNode(
                        task_id=dl_task_id,
                        task_type=MissionTaskType.SIMULATED_DATA_TRANSFER.value,
                        name=f"Simulated Downlink: {target.name} Data",
                        parent_goal_id=f"goal_downlink_{target.target_id}",
                        assigned_rover_id=r_id,
                        target_id=target.target_id,
                        location_rc=target.location_rc,
                        prerequisite_task_ids=dl_prereqs,
                        estimated_duration_s=dl_dur_s,
                        estimated_energy_wh=dl_energy_wh,
                        estimated_data_mb=data_mb,
                        sol_index=sol,
                        metadata={"downlink_rate_mbps": downlink_bw_mbps},
                    )
                    graph.add_task(dl_task)

                    curr_loc = target.location_rc
                    prev_task_id = dl_task_id

                # Standby / sol boundary checkpoint for this rover
                chk_task_id = f"task_checkpoint_{r_id}_sol{sol}"
                chk_prereqs = [prev_task_id] if prev_task_id else ([last_sol_checkpoint_id] if last_sol_checkpoint_id else [])
                chk_task = MissionTaskNode(
                    task_id=chk_task_id,
                    task_type=MissionTaskType.CAMPAIGN_CHECKPOINT.value,
                    name=f"Sol {sol} Diurnal Rest & Recharge ({r_id})",
                    parent_goal_id=f"goal_sol_{sol}_completion",
                    assigned_rover_id=r_id,
                    location_rc=curr_loc,
                    prerequisite_task_ids=chk_prereqs,
                    estimated_duration_s=3600.0,  # 1 hour diurnal sync
                    estimated_energy_wh=-300.0 if intent.timeline.diurnal_recharge_enabled else 0.0,  # Solar recharge gain
                    estimated_data_mb=0.0,
                    sol_index=sol,
                    metadata={"sol": sol, "recharge_enabled": intent.timeline.diurnal_recharge_enabled},
                )
                graph.add_task(chk_task)
                sol_checkpoint_ids.append(chk_task_id)

            # Sol Synchronization Checkpoint
            if len(sol_checkpoint_ids) > 1:
                sync_task_id = f"task_fleet_sync_sol{sol}"
                sync_task = MissionTaskNode(
                    task_id=sync_task_id,
                    task_type=MissionTaskType.CAMPAIGN_CHECKPOINT.value,
                    name=f"Fleet Global Synchronization Sol {sol}",
                    parent_goal_id=f"goal_sol_{sol}_completion",
                    assigned_rover_id=None,
                    location_rc=base_station_rc,
                    prerequisite_task_ids=sol_checkpoint_ids,
                    estimated_duration_s=600.0,
                    estimated_energy_wh=0.0,
                    estimated_data_mb=0.0,
                    sol_index=sol,
                    metadata={"synchronized_rovers": [r.rover_id for r in active_rovers]},
                )
                graph.add_task(sync_task)
                last_sol_checkpoint_id = sync_task_id
            elif sol_checkpoint_ids:
                last_sol_checkpoint_id = sol_checkpoint_ids[0]

        # Final pass: Ensure roots, terminals and acyclicity
        graph._recompute_roots_and_terminals()
        if not graph.validate_acyclic():
            raise RuntimeError("Generated task graph contains cycles.")

        return graph
