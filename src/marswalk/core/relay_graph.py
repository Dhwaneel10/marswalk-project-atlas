"""
MarsWalk Core Relay Network Graph Engine (Milestone 13D - Atlas Mars RelayNet).

Constructs and evaluates terrain-aware communication network topologies on the Martian surface.
Features:
- Dual representations: Adjacency dictionary for fast traversal and Adjacency/Distance matrix.
- BFS reachability to designated Base Station with exact hop counts.
- Connected component decomposition.
- Minimum-hop and shortest-distance path reconstruction.
- Bridge edge and cut vertex (articulation point) identification via Tarjan's algorithm.
- Single and multi-node failure resilience analysis and criticality scoring.
- Algebraic connectivity (graph Laplacian Fiedler value lambda_2).
"""

from dataclasses import dataclass, field
from enum import Enum
import heapq
import math
from typing import Dict, List, Tuple, Set, Optional, Any
import numpy as np


class RelayNodeType(str, Enum):
    BASE_STATION = "base_station"
    ROBOTIC_ROVER = "robotic_rover"
    CREW_EVA = "crew_eva"
    SCOUT_ROVER = "scout_rover"
    CANDIDATE_RELAY = "candidate_relay"
    ACTIVE_RELAY = "active_relay"


class LinkVisibilityStatus(str, Enum):
    VISIBLE = "VISIBLE"
    BLOCKED = "BLOCKED"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    BLOCKED_AND_OUT_OF_RANGE = "BLOCKED_AND_OUT_OF_RANGE"
    UNKNOWN = "UNKNOWN"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True)
class RelayNode:
    """
    Representation of an active or candidate communications node on the Martian surface.
    """
    node_id: str
    node_type: RelayNodeType
    rc: Tuple[float, float]  # (row, col) coordinates
    elevation_m: float       # Ground terrain elevation in meters (MOLA datum)
    antenna_height_m: float  # Antenna mast height in meters above ground level
    label: str = ""
    is_active: bool = True   # If False, node is offline, destroyed, or unselected candidate

    @property
    def effective_z_m(self) -> float:
        """Total antenna phase center altitude relative to Martian datum."""
        return self.elevation_m + self.antenna_height_m

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "rc": [round(float(self.rc[0]), 2), round(float(self.rc[1]), 2)],
            "elevation_m": round(float(self.elevation_m), 2),
            "antenna_height_m": round(float(self.antenna_height_m), 2),
            "effective_z_m": round(float(self.effective_z_m), 2),
            "label": self.label or self.node_id,
            "is_active": self.is_active,
        }


@dataclass(frozen=True)
class RelayEdge:
    """
    Geometric communication link between two surface nodes.
    """
    u: str
    v: str
    distance_m: float           # 2D horizontal ground metric distance
    slant_range_m: float        # 3D Euclidean slant distance between antenna phase centers
    visibility: LinkVisibilityStatus
    min_clearance_m: float      # Minimum topographic clearance along the chord
    num_hops: int = 1
    propagation_delay_us: float = 0.0  # Free-space propagation delay in microseconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "u": self.u,
            "v": self.v,
            "distance_m": round(float(self.distance_m), 2),
            "slant_range_m": round(float(self.slant_range_m), 2),
            "visibility": self.visibility.value,
            "min_clearance_m": round(float(self.min_clearance_m), 2),
            "num_hops": self.num_hops,
            "propagation_delay_us": round(float(self.propagation_delay_us), 3),
        }


class RelayNetworkGraph:
    """
    Terrain-aware communication network graph for Mars surface exploration.
    Maintains graph invariants, deterministic traversal, and fault tolerance metrics.
    """

    def __init__(self, r_max_m: float = 5000.0):
        self.r_max_m = r_max_m
        self.nodes: Dict[str, RelayNode] = {}
        # Adjacency dict: node_id -> {neighbor_id: RelayEdge}
        self.adj: Dict[str, Dict[str, RelayEdge]] = {}

    def add_node(self, node: RelayNode) -> None:
        """Register a node in the graph."""
        self.nodes[node.node_id] = node
        if node.node_id not in self.adj:
            self.adj[node.node_id] = {}

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all incident edges from the graph."""
        if node_id in self.nodes:
            del self.nodes[node_id]
        if node_id in self.adj:
            del self.adj[node_id]
        for u in self.adj:
            if node_id in self.adj[u]:
                del self.adj[u][node_id]

    def add_edge(self, edge: RelayEdge) -> None:
        """
        Add bidirectional edge between nodes iff visibility is VISIBLE
        and distance is within the configured maximum range.
        """
        if edge.visibility != LinkVisibilityStatus.VISIBLE:
            return
        if edge.distance_m > self.r_max_m:
            return
        if edge.u not in self.nodes or edge.v not in self.nodes:
            return

        self.adj[edge.u][edge.v] = edge
        rev_edge = RelayEdge(
            u=edge.v,
            v=edge.u,
            distance_m=edge.distance_m,
            slant_range_m=edge.slant_range_m,
            visibility=edge.visibility,
            min_clearance_m=edge.min_clearance_m,
            num_hops=edge.num_hops,
            propagation_delay_us=edge.propagation_delay_us,
        )
        self.adj[edge.v][edge.u] = rev_edge

    def get_active_nodes(self) -> Dict[str, RelayNode]:
        """Return subset of currently active nodes."""
        return {nid: n for nid, n in self.nodes.items() if n.is_active}

    def to_adjacency_matrix(self) -> Tuple[List[str], np.ndarray, np.ndarray]:
        """
        Build (node_ids, adj_matrix, dist_matrix) for active nodes.
        adj_matrix[i, j] = 1 if edge exists else 0
        dist_matrix[i, j] = distance if edge exists else inf (0 on diagonal)
        """
        active = sorted(list(self.get_active_nodes().keys()))
        n = len(active)
        idx_map = {nid: i for i, nid in enumerate(active)}
        A = np.zeros((n, n), dtype=np.int32)
        W = np.full((n, n), np.inf, dtype=np.float64)
        np.fill_diagonal(W, 0.0)

        for u in active:
            u_idx = idx_map[u]
            for v, edge in self.adj.get(u, {}).items():
                if v in idx_map:
                    v_idx = idx_map[v]
                    A[u_idx, v_idx] = 1
                    W[u_idx, v_idx] = edge.distance_m

        return active, A, W

    def evaluate_base_reachability(self, base_node_id: str) -> Dict[str, Any]:
        """
        Breadth-First Search (BFS) reachability starting from base_node_id across active nodes.
        Complexity: O(V + E).
        """
        active_nodes = self.get_active_nodes()
        if base_node_id not in active_nodes:
            return {
                "base_online": False,
                "reachable_nodes": set(),
                "hop_counts": {},
                "predecessors": {},
                "isolated_nodes": set(active_nodes.keys()),
                "total_active": len(active_nodes),
                "total_reachable": 0,
            }

        queue = [base_node_id]
        visited = {base_node_id}
        hop_counts = {base_node_id: 0}
        predecessors: Dict[str, Optional[str]] = {base_node_id: None}

        head = 0
        while head < len(queue):
            curr = queue[head]
            head += 1
            curr_hops = hop_counts[curr]

            for neighbor in sorted(self.adj.get(curr, {}).keys()):
                if neighbor in active_nodes and neighbor not in visited:
                    visited.add(neighbor)
                    hop_counts[neighbor] = curr_hops + 1
                    predecessors[neighbor] = curr
                    queue.append(neighbor)

        isolated = set(active_nodes.keys()) - visited
        return {
            "base_online": True,
            "reachable_nodes": visited,
            "hop_counts": hop_counts,
            "predecessors": predecessors,
            "isolated_nodes": isolated,
            "total_active": len(active_nodes),
            "total_reachable": len(visited),
        }

    def get_connected_components(self) -> List[Set[str]]:
        """
        Decompose active nodes into connected components via BFS.
        Complexity: O(V + E).
        """
        active_nodes = self.get_active_nodes()
        visited: Set[str] = set()
        components: List[Set[str]] = []

        for node_id in sorted(active_nodes.keys()):
            if node_id not in visited:
                comp: Set[str] = set()
                q = [node_id]
                visited.add(node_id)
                comp.add(node_id)
                head = 0
                while head < len(q):
                    curr = q[head]
                    head += 1
                    for nbr in sorted(self.adj.get(curr, {}).keys()):
                        if nbr in active_nodes and nbr not in visited:
                            visited.add(nbr)
                            comp.add(nbr)
                            q.append(nbr)
                components.append(comp)

        components.sort(key=lambda c: (-len(c), min(c)))
        return components

    def get_minimum_hop_path(self, start_id: str, goal_id: str) -> Optional[List[str]]:
        """
        BFS to find the path with minimum number of communication hops.
        Complexity: O(V + E).
        """
        active = self.get_active_nodes()
        if start_id not in active or goal_id not in active:
            return None
        if start_id == goal_id:
            return [start_id]

        queue = [start_id]
        parent: Dict[str, Optional[str]] = {start_id: None}
        visited = {start_id}
        head = 0

        found = False
        while head < len(queue):
            curr = queue[head]
            head += 1
            if curr == goal_id:
                found = True
                break
            for nbr in sorted(self.adj.get(curr, {}).keys()):
                if nbr in active and nbr not in visited:
                    visited.add(nbr)
                    parent[nbr] = curr
                    queue.append(nbr)

        if not found:
            return None

        path = []
        c = goal_id
        while c is not None:
            path.append(c)
            c = parent[c]
        path.reverse()
        return path

    def get_shortest_distance_path(self, start_id: str, goal_id: str) -> Optional[Tuple[List[str], float]]:
        """
        Dijkstra's algorithm to find path with minimum cumulative ground distance.
        Complexity: O(E + V log V).
        """
        active = self.get_active_nodes()
        if start_id not in active or goal_id not in active:
            return None
        if start_id == goal_id:
            return ([start_id], 0.0)

        dist: Dict[str, float] = {start_id: 0.0}
        parent: Dict[str, Optional[str]] = {start_id: None}
        pq: List[Tuple[float, str]] = [(0.0, start_id)]

        while pq:
            d, curr = heapq.heappop(pq)
            if d > dist.get(curr, float("inf")):
                continue
            if curr == goal_id:
                break

            for nbr, edge in self.adj.get(curr, {}).items():
                if nbr in active:
                    new_d = d + edge.distance_m
                    if new_d < dist.get(nbr, float("inf")):
                        dist[nbr] = new_d
                        parent[nbr] = curr
                        heapq.heappush(pq, (new_d, nbr))

        if goal_id not in dist:
            return None

        path = []
        c = goal_id
        while c is not None:
            path.append(c)
            c = parent[c]
        path.reverse()
        return (path, dist[goal_id])

    def find_bridge_edges(self) -> List[Tuple[str, str]]:
        """
        Find all bridge edges using Tarjan's DFS algorithm.
        Complexity: O(V + E).
        """
        active = self.get_active_nodes()
        tin: Dict[str, int] = {}
        low: Dict[str, int] = {}
        bridges: List[Tuple[str, str]] = []
        timer = 0

        def dfs(u: str, p: Optional[str] = None):
            nonlocal timer
            timer += 1
            tin[u] = low[u] = timer
            for v in sorted(self.adj.get(u, {}).keys()):
                if v not in active or v == p:
                    continue
                if v in tin:
                    low[u] = min(low[u], tin[v])
                else:
                    dfs(v, u)
                    low[u] = min(low[u], low[v])
                    if low[v] > tin[u]:
                        bridges.append((min(u, v), max(u, v)))

        for nid in sorted(active.keys()):
            if nid not in tin:
                dfs(nid)

        bridges.sort()
        return bridges

    def find_bridges(self) -> List[Tuple[str, str]]:
        """Alias for find_bridge_edges."""
        return self.find_bridge_edges()

    def find_cut_vertices(self) -> List[str]:
        """Alias for find_articulation_points returning a sorted list."""
        return sorted(list(self.find_articulation_points()))

    def find_articulation_points(self) -> Set[str]:
        """
        Find articulation points (cut vertices) using Tarjan's DFS.
        Complexity: O(V + E).
        """
        active = self.get_active_nodes()
        tin: Dict[str, int] = {}
        low: Dict[str, int] = {}
        cut_vertices: Set[str] = set()
        timer = 0

        def dfs(u: str, p: Optional[str] = None):
            nonlocal timer
            timer += 1
            tin[u] = low[u] = timer
            children = 0
            for v in sorted(self.adj.get(u, {}).keys()):
                if v not in active or v == p:
                    continue
                if v in tin:
                    low[u] = min(low[u], tin[v])
                else:
                    dfs(v, u)
                    low[u] = min(low[u], low[v])
                    if low[v] >= tin[u] and p is not None:
                        cut_vertices.add(u)
                    children += 1
            if p is None and children > 1:
                cut_vertices.add(u)

        for nid in sorted(active.keys()):
            if nid not in tin:
                dfs(nid)

        return cut_vertices

    def evaluate_node_failure_impact(self, base_node_id: str, target_node_id: str) -> Dict[str, Any]:
        """
        Evaluate impact of removing target_node_id on Base connectivity.
        Identifies severed exploration units and single points of failure.
        """
        active = self.get_active_nodes()
        if target_node_id not in active:
            return {"error": f"Node {target_node_id} is not active"}

        baseline = self.evaluate_base_reachability(base_node_id)
        baseline_reachable = baseline["reachable_nodes"]

        orig_node = self.nodes[target_node_id]
        # Temporarily deactivate node
        self.nodes[target_node_id] = RelayNode(
            node_id=orig_node.node_id,
            node_type=orig_node.node_type,
            rc=orig_node.rc,
            elevation_m=orig_node.elevation_m,
            antenna_height_m=orig_node.antenna_height_m,
            label=orig_node.label,
            is_active=False,
        )

        try:
            post_failure = self.evaluate_base_reachability(base_node_id)
            post_reachable = post_failure["reachable_nodes"]
            severed_units = (baseline_reachable - post_reachable) - {target_node_id}

            return {
                "failed_node": target_node_id,
                "node_type": orig_node.node_type.value,
                "baseline_reachable_count": len(baseline_reachable),
                "post_failure_reachable_count": len(post_reachable),
                "severed_units": sorted(list(severed_units)),
                "criticality_score": len(severed_units),
                "is_single_point_of_failure": len(severed_units) > 0,
            }
        finally:
            self.nodes[target_node_id] = orig_node

    def compute_algebraic_connectivity(self) -> float:
        """
        Compute algebraic connectivity (Fiedler value lambda_2 of Laplacian L = D - A).
        lambda_2 > 0 iff graph is connected. Higher lambda_2 indicates higher path redundancy.
        """
        active, A, _ = self.to_adjacency_matrix()
        n = len(active)
        if n <= 1:
            return 0.0

        degrees = np.sum(A, axis=1)
        D = np.diag(degrees)
        L = D - A
        eigvals = np.linalg.eigvalsh(L)
        eigvals = np.sort(eigvals)
        lambda_2 = float(eigvals[1]) if len(eigvals) > 1 else 0.0
        return max(0.0, round(lambda_2, 4))
