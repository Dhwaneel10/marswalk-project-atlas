"""
Milestone 13D - Agent B: Network Graph Algorithms & Relay Placement Specialist
Prototype & Verification Script

Tests and validates:
1. RelayGraph data structure (Nodes, Edges, Adjacency Dict, Adjacency Matrix)
2. Graph algorithms: BFS reachability, Connected Components, BFS Min-Hop paths, Dijkstra Shortest Distance
3. Resilience analysis: Single relay failure criticality, Bridge edge identification, Articulation points, Graph Laplacian algebraic connectivity
4. Candidate Relay Screening on Jezero 250x250 DTM (slope <= 12 deg, elevation > -2500m, min separation >= 500m)
5. Greedy Submodular Relay Placement with deterministic tie-breaking
"""

import math
import heapq
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set, Optional, Any
import numpy as np

# ---------------------------------------------------------
# 1. Enums and Data Models
# ---------------------------------------------------------

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
    UNKNOWN = "UNKNOWN"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True)
class RelayNode:
    node_id: str
    node_type: RelayNodeType
    rc: Tuple[float, float]  # (row, col)
    elevation_m: float       # Terrain surface elevation z(r, c)
    antenna_height_m: float  # Antenna mast height h above surface
    label: str = ""
    is_active: bool = True   # If False, node is offline or candidate not yet selected

    @property
    def effective_z_m(self) -> float:
        """Total antenna phase center elevation in Martian datum."""
        return self.elevation_m + self.antenna_height_m

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "rc": [round(self.rc[0], 2), round(self.rc[1], 2)],
            "elevation_m": round(self.elevation_m, 2),
            "antenna_height_m": round(self.antenna_height_m, 2),
            "effective_z_m": round(self.effective_z_m, 2),
            "label": self.label or self.node_id,
            "is_active": self.is_active,
        }


@dataclass(frozen=True)
class RelayEdge:
    u: str
    v: str
    distance_m: float           # 2D ground metric distance
    slant_range_m: float        # 3D slant distance between antenna phase centers
    visibility: LinkVisibilityStatus
    min_clearance_m: float      # Minimum topographic clearance along ray
    num_hops: int = 1
    propagation_delay_us: float = 0.0  # (slant_range / c) * 1e6

    def to_dict(self) -> Dict[str, Any]:
        return {
            "u": self.u,
            "v": self.v,
            "distance_m": round(self.distance_m, 2),
            "slant_range_m": round(self.slant_range_m, 2),
            "visibility": self.visibility.value,
            "min_clearance_m": round(self.min_clearance_m, 2),
            "num_hops": self.num_hops,
            "propagation_delay_us": round(self.propagation_delay_us, 3),
        }


# ---------------------------------------------------------
# 2. Network Graph Data Structure
# ---------------------------------------------------------

class RelayNetworkGraph:
    """
    Terrain-aware communication network graph for Mars surface exploration.
    Supports dual adjacency representations, BFS reachability, shortest paths,
    bridge detection, and fault resilience analysis.
    """

    def __init__(self, r_max_m: float = 3000.0):
        self.r_max_m = r_max_m
        self.nodes: Dict[str, RelayNode] = {}
        # Adjacency dict: node_id -> {neighbor_id: RelayEdge}
        self.adj: Dict[str, Dict[str, RelayEdge]] = {}

    def add_node(self, node: RelayNode) -> None:
        self.nodes[node.node_id] = node
        if node.node_id not in self.adj:
            self.adj[node.node_id] = {}

    def remove_node(self, node_id: str) -> None:
        if node_id in self.nodes:
            del self.nodes[node_id]
        if node_id in self.adj:
            del self.adj[node_id]
        for u in self.adj:
            if node_id in self.adj[u]:
                del self.adj[u][node_id]

    def add_edge(self, edge: RelayEdge) -> None:
        """Add bidirectional edge if visibility is VISIBLE and within range."""
        if edge.visibility != LinkVisibilityStatus.VISIBLE:
            return
        if edge.distance_m > self.r_max_m:
            return
        if edge.u not in self.nodes or edge.v not in self.nodes:
            return

        self.adj[edge.u][edge.v] = edge
        # Symmetric edge
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
        return {nid: n for nid, n in self.nodes.items() if n.is_active}

    # -----------------------------------------------------
    # Adjacency Matrix Representation
    # -----------------------------------------------------
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

    # -----------------------------------------------------
    # BFS Reachability from Base Station
    # -----------------------------------------------------
    def evaluate_base_reachability(self, base_node_id: str) -> Dict[str, Any]:
        """
        Breadth-First Search (BFS) from base_node_id across active nodes.
        Returns reachable nodes, hop counts, parent pointers, and isolated units.
        Time Complexity: O(V + E)
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

    # -----------------------------------------------------
    # Connected Components (CC)
    # -----------------------------------------------------
    def get_connected_components(self) -> List[Set[str]]:
        """
        Identify all connected components using BFS.
        Time Complexity: O(V + E)
        """
        active_nodes = self.get_active_nodes()
        visited: Set[str] = set()
        components: List[Set[str]] = []

        for node_id in sorted(active_nodes.keys()):
            if node_id not in visited:
                comp = set()
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

        # Sort components descending by size, then lexicographically by min node_id
        components.sort(key=lambda c: (-len(c), min(c)))
        return components

    # -----------------------------------------------------
    # Minimum-Hop Path & Shortest Distance Path
    # -----------------------------------------------------
    def get_minimum_hop_path(self, start_id: str, goal_id: str) -> Optional[List[str]]:
        """
        BFS to find the path with minimum number of communication hops.
        Time Complexity: O(V + E)
        """
        active = self.get_active_nodes()
        if start_id not in active or goal_id not in active:
            return None
        if start_id == goal_id:
            return [start_id]

        queue = [start_id]
        parent = {start_id: None}
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

        # Reconstruct path
        path = []
        c = goal_id
        while c is not None:
            path.append(c)
            c = parent[c]
        path.reverse()
        return path

    def get_shortest_distance_path(self, start_id: str, goal_id: str) -> Optional[Tuple[List[str], float]]:
        """
        Dijkstra's algorithm to find path with minimum cumulative ground/slant distance.
        Time Complexity: O(E + V log V)
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

    # -----------------------------------------------------
    # Bridge Edge & Articulation Point Detection (Tarjan)
    # -----------------------------------------------------
    def find_bridge_edges(self) -> List[Tuple[str, str]]:
        """
        Find all bridge edges using Tarjan's DFS bridge-finding algorithm.
        A bridge is an edge whose removal disconnects the graph or isolates nodes.
        Time Complexity: O(V + E)
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
                    # Back edge
                    low[u] = min(low[u], tin[v])
                else:
                    # Tree edge
                    dfs(v, u)
                    low[u] = min(low[u], low[v])
                    if low[v] > tin[u]:
                        # Edge (u, v) is a bridge!
                        bridges.append((min(u, v), max(u, v)))

        for nid in sorted(active.keys()):
            if nid not in tin:
                dfs(nid)

        bridges.sort()
        return bridges

    def find_articulation_points(self) -> Set[str]:
        """
        Find articulation points (cut vertices) using Tarjan's DFS.
        Time Complexity: O(V + E)
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

    # -----------------------------------------------------
    # Resilience & Fault Tolerance Analysis
    # -----------------------------------------------------
    def evaluate_node_failure_impact(self, base_node_id: str, target_node_id: str) -> Dict[str, Any]:
        """
        Evaluate the impact of removing target_node_id on Base connectivity.
        Identifies orphaned units (criticality score) and new connected components.
        """
        active = self.get_active_nodes()
        if target_node_id not in active:
            return {"error": f"Node {target_node_id} is not active"}

        baseline = self.evaluate_base_reachability(base_node_id)
        baseline_reachable = baseline["reachable_nodes"]

        # Temporarily deactivate node
        original_state = self.nodes[target_node_id].is_active
        # Need object modification: we create a modified copy or toggle flag
        # Since RelayNode is frozen, we replace it in self.nodes
        orig_node = self.nodes[target_node_id]
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

            # Units that lost connectivity to Base (excluding the failed node itself)
            severed_units = (baseline_reachable - post_reachable) - {target_node_id}
            is_critical = len(severed_units) > 0

            return {
                "failed_node": target_node_id,
                "node_type": orig_node.node_type.value,
                "baseline_reachable_count": len(baseline_reachable),
                "post_failure_reachable_count": len(post_reachable),
                "severed_units": sorted(list(severed_units)),
                "criticality_score": len(severed_units),
                "is_single_point_of_failure": is_critical,
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


# ---------------------------------------------------------
# 3. Relay Site Screening on Jezero 250x250 DTM
# ---------------------------------------------------------

def screen_relay_candidates(
    elevation: np.ndarray,
    slope_deg: np.ndarray,
    invalid_mask: np.ndarray,
    dx_ground_m: float,
    dy_ground_m: float,
    max_slope_deg: float = 12.0,
    min_elevation_m: float = -2500.0,
    min_separation_m: float = 450.0,
    max_candidates: int = 15,
    border_margin: int = 5,
) -> List[Dict[str, Any]]:
    """
    Screens topographic promontory/ridge candidate sites from Jezero DTM.
    Criteria:
      - Slope <= max_slope_deg (12 deg: robotic stability & mast anchor safety)
      - Elevation > min_elevation_m (-2500m: high crater rim/delta vantage)
      - Invalid/NoData dilated cells excluded
      - Border margin excluded
      - Mutual ground separation >= min_separation_m (anti-clustering via greedy NMS)
      - Bounded pool: up to max_candidates (10-15 sites)
    """
    H, W = elevation.shape
    mask = (elevation > min_elevation_m) & (slope_deg <= max_slope_deg) & (~invalid_mask)

    # Exclude border cells
    mask[:border_margin, :] = False
    mask[-border_margin:, :] = False
    mask[:, :border_margin] = False
    mask[:, -border_margin:] = False

    rows, cols = np.where(mask)
    if len(rows) == 0:
        return []

    elevs = elevation[rows, cols]
    slopes = slope_deg[rows, cols]

    # Prominence & Placement Score:
    # 70% normalized elevation + 30% normalized flatness (low slope)
    min_e, max_e = float(elevs.min()), float(elevs.max())
    norm_e = (elevs - min_e) / (max_e - min_e + 1e-6)
    norm_s = 1.0 - (slopes / max_slope_deg)
    scores = 0.7 * norm_e + 0.3 * norm_s

    # Deterministic sorting: Descending by score, then ascending by row, then col
    sort_keys = list(zip(-scores, rows, cols))
    sorted_order = sorted(range(len(rows)), key=lambda i: sort_keys[i])

    selected: List[Dict[str, Any]] = []
    selected_rc: List[Tuple[int, int]] = []

    for idx in sorted_order:
        r, c = int(rows[idx]), int(cols[idx])
        # Check minimum ground separation against already selected candidates
        too_close = False
        for sr, sc in selected_rc:
            dist = math.sqrt(((c - sc) * dx_ground_m) ** 2 + ((r - sr) * dy_ground_m) ** 2)
            if dist < min_separation_m:
                too_close = True
                break

        if not too_close:
            selected_rc.append((r, c))
            cand_id = f"RELAY_CAND_{len(selected) + 1:02d}"
            selected.append({
                "candidate_id": cand_id,
                "rc": (r, c),
                "row": r,
                "col": c,
                "elevation_m": round(float(elevation[r, c]), 2),
                "slope_deg": round(float(slope_deg[r, c]), 2),
                "prominence_score": round(float(scores[idx]), 4),
            })
            if len(selected) >= max_candidates:
                break

    return selected


# ---------------------------------------------------------
# 4. Greedy Submodular Relay Placement Algorithm
# ---------------------------------------------------------

def optimize_relay_placement(
    graph: RelayNetworkGraph,
    base_node_id: str,
    target_unit_ids: List[str],
    candidate_nodes: List[RelayNode],
    candidate_edges: List[RelayEdge],
    relay_budget: int = 3,
) -> Dict[str, Any]:
    """
    Greedy Submodular Relay Site Placement.
    Objective: Given target exploration units disconnected from Base,
    iteratively select candidate relay that maximizes incremental newly connected units
    to Base Station until relay_budget is reached or all target units are connected.

    Deterministic Tie-Breaking Hierarchy:
      1. Maximize newly connected target units: Delta(r)
      2. Minimize average hop count from newly connected units to Base
      3. Maximize candidate topographic elevation (better future coverage potential)
      4. Lexicographical candidate_id order
    """
    # Evaluate baseline reachability without any candidate relays
    baseline_eval = graph.evaluate_base_reachability(base_node_id)
    baseline_reachable = baseline_eval["reachable_nodes"]
    disconnected_targets = set(target_unit_ids) - baseline_reachable

    selected_relays: List[RelayNode] = []
    remaining_candidates = {cn.node_id: cn for cn in candidate_nodes}
    
    # Pre-index candidate edges by candidate ID
    cand_edge_map: Dict[str, List[RelayEdge]] = {cn.node_id: [] for cn in candidate_nodes}
    for e in candidate_edges:
        if e.u in cand_edge_map:
            cand_edge_map[e.u].append(e)
        if e.v in cand_edge_map:
            cand_edge_map[e.v].append(e)

    iteration_log = []

    for step in range(relay_budget):
        if not disconnected_targets:
            # All target exploration units already connected!
            break

        best_cand: Optional[RelayNode] = None
        best_delta = -1
        best_avg_hops = float("inf")
        best_elev = -float("inf")
        best_cand_id = ""

        # Evaluate marginal gain of each remaining candidate
        for cand_id, cand_node in sorted(remaining_candidates.items()):
            # Temporarily add active version of candidate node and its edges to the graph
            cand_temp_active = RelayNode(
                node_id=cand_node.node_id,
                node_type=RelayNodeType.ACTIVE_RELAY,
                rc=cand_node.rc,
                elevation_m=cand_node.elevation_m,
                antenna_height_m=cand_node.antenna_height_m,
                label=cand_node.label,
                is_active=True,
            )
            graph.add_node(cand_temp_active)
            for e in cand_edge_map[cand_id]:
                graph.add_edge(e)

            eval_res = graph.evaluate_base_reachability(base_node_id)
            new_reachable = eval_res["reachable_nodes"]
            newly_connected = disconnected_targets.intersection(new_reachable)
            delta = len(newly_connected)

            # Compute average hops for newly connected units
            if delta > 0:
                avg_hops = sum(eval_res["hop_counts"][u] for u in newly_connected) / delta
            else:
                avg_hops = float("inf")

            elev = cand_node.elevation_m

            # Compare using deterministic hierarchy:
            # (delta DESC, -avg_hops DESC, elev DESC, -cand_id DESC)
            is_better = False
            if delta > best_delta:
                is_better = True
            elif delta == best_delta and delta > 0:
                if avg_hops < best_avg_hops - 1e-5:
                    is_better = True
                elif abs(avg_hops - best_avg_hops) <= 1e-5:
                    if elev > best_elev + 1e-3:
                        is_better = True
                    elif abs(elev - best_elev) <= 1e-3:
                        if cand_id < best_cand_id:
                            is_better = True

            if is_better:
                best_cand = cand_node
                best_delta = delta
                best_avg_hops = avg_hops
                best_elev = elev
                best_cand_id = cand_id

            # Roll back temporary addition
            graph.remove_node(cand_id)

        # Stop if no remaining candidate provides any connectivity improvement
        if best_cand is None or best_delta <= 0:
            break

        # Permanently activate chosen candidate
        active_version = RelayNode(
            node_id=best_cand.node_id,
            node_type=RelayNodeType.ACTIVE_RELAY,
            rc=best_cand.rc,
            elevation_m=best_cand.elevation_m,
            antenna_height_m=best_cand.antenna_height_m,
            label=f"Active Relay ({best_cand.node_id})",
            is_active=True,
        )
        graph.add_node(active_version)
        for e in cand_edge_map[best_cand.node_id]:
            graph.add_edge(e)

        selected_relays.append(active_version)
        del remaining_candidates[best_cand.node_id]

        # Update reachable target set
        step_eval = graph.evaluate_base_reachability(base_node_id)
        step_reachable = step_eval["reachable_nodes"]
        newly_solved = disconnected_targets.intersection(step_reachable)
        disconnected_targets -= newly_solved

        iteration_log.append({
            "step": step + 1,
            "selected_relay_id": active_version.node_id,
            "rc": list(active_version.rc),
            "elevation_m": active_version.elevation_m,
            "newly_connected_units": sorted(list(newly_solved)),
            "marginal_coverage_gain": best_delta,
            "remaining_disconnected_units": sorted(list(disconnected_targets)),
        })

    # Final network state evaluation
    final_eval = graph.evaluate_base_reachability(base_node_id)
    final_reachable = final_eval["reachable_nodes"]
    final_disconnected = set(target_unit_ids) - final_reachable
    initial_disconnected = set(target_unit_ids) - baseline_reachable

    return {
        "status": "OPTIMIZATION_COMPLETE",
        "selected_relays": [r.to_dict() for r in selected_relays],
        "budget_used": len(selected_relays),
        "budget_limit": relay_budget,
        "initial_connected_count": len(baseline_reachable.intersection(target_unit_ids)),
        "initial_disconnected_count": len(initial_disconnected),
        "final_connected_count": len(final_reachable.intersection(target_unit_ids)),
        "final_disconnected_count": len(final_disconnected),
        "coverage_percentage": round(100.0 * (len(final_reachable.intersection(target_unit_ids)) / max(1, len(target_unit_ids))), 1),
        "iteration_log": iteration_log,
        "remaining_disconnected_targets": sorted(list(final_disconnected)),
    }


# ---------------------------------------------------------
# Verification Runner
# ---------------------------------------------------------
if __name__ == "__main__":
    print("=================================================================")
    print("Atlas Mars RelayNet - Milestone 13D Agent B Verification Harness")
    print("=================================================================")

    # Test 1: Synthetic Graph Verification (BFS, Min-Hop, Dijkstra, Bridges, Cut Vertices)
    print("\n--- Test 1: Synthetic Network Graph Algorithms ---")
    g = RelayNetworkGraph(r_max_m=3000.0)

    # Base Station
    g.add_node(RelayNode("base", RelayNodeType.BASE_STATION, (117, 157), -2567.0, 10.0, "Octavia Butler Base"))
    # Rover 1 (in range of base)
    g.add_node(RelayNode("rover_1", RelayNodeType.ROBOTIC_ROVER, (110, 150), -2560.0, 2.5, "Perseverance"))
    # Relay 1 (in range of base and rover 2)
    g.add_node(RelayNode("relay_1", RelayNodeType.ACTIVE_RELAY, (80, 130), -2480.0, 10.0, "Delta Scarp Relay"))
    # Rover 2 (shadowed from base, visible to relay_1)
    g.add_node(RelayNode("rover_2", RelayNodeType.ROBOTIC_ROVER, (50, 110), -2520.0, 2.5, "Scout Alpha"))
    # Crew EVA (connected only through rover_2)
    g.add_node(RelayNode("crew_eva", RelayNodeType.CREW_EVA, (45, 105), -2515.0, 2.0, "EVA Team 1"))
    # Isolated Rover (no comms)
    g.add_node(RelayNode("rover_isolated", RelayNodeType.ROBOTIC_ROVER, (10, 10), -2600.0, 2.5, "Isolated Scout"))

    # Edges:
    # base <-> rover_1 (500m)
    g.add_edge(RelayEdge("base", "rover_1", 500.0, 501.0, LinkVisibilityStatus.VISIBLE, 15.0))
    # base <-> relay_1 (1200m)
    g.add_edge(RelayEdge("base", "relay_1", 1200.0, 1205.0, LinkVisibilityStatus.VISIBLE, 45.0))
    # relay_1 <-> rover_2 (800m)
    g.add_edge(RelayEdge("relay_1", "rover_2", 800.0, 802.0, LinkVisibilityStatus.VISIBLE, 20.0))
    # rover_2 <-> crew_eva (300m)
    g.add_edge(RelayEdge("rover_2", "crew_eva", 300.0, 300.5, LinkVisibilityStatus.VISIBLE, 8.0))

    # Evaluate reachability
    reach = g.evaluate_base_reachability("base")
    print("Reachable nodes:", reach["reachable_nodes"])
    print("Hop counts:", reach["hop_counts"])
    print("Isolated nodes:", reach["isolated_nodes"])
    assert "rover_1" in reach["reachable_nodes"]
    assert "rover_2" in reach["reachable_nodes"]
    assert "crew_eva" in reach["reachable_nodes"]
    assert "rover_isolated" in reach["isolated_nodes"]
    assert reach["hop_counts"]["base"] == 0
    assert reach["hop_counts"]["rover_1"] == 1
    assert reach["hop_counts"]["relay_1"] == 1
    assert reach["hop_counts"]["rover_2"] == 2
    assert reach["hop_counts"]["crew_eva"] == 3
    print("-> Reachability & Hop counts VERIFIED.")

    # Paths
    hop_path = g.get_minimum_hop_path("base", "crew_eva")
    print("Min hop path base -> crew_eva:", hop_path)
    assert hop_path == ["base", "relay_1", "rover_2", "crew_eva"]

    dist_path, total_dist = g.get_shortest_distance_path("base", "crew_eva")
    print(f"Shortest dist path base -> crew_eva: {dist_path} (dist={total_dist}m)")
    assert dist_path == ["base", "relay_1", "rover_2", "crew_eva"]
    assert total_dist == 1200.0 + 800.0 + 300.0

    # Bridges & Articulation points
    bridges = g.find_bridge_edges()
    print("Bridge edges:", bridges)
    assert len(bridges) == 4  # Tree network has all edges as bridges

    art_pts = g.find_articulation_points()
    print("Articulation points (cut vertices):", art_pts)
    assert "relay_1" in art_pts
    assert "rover_2" in art_pts
    assert "base" in art_pts

    # Resilience: Test failure of relay_1
    fail_impact = g.evaluate_node_failure_impact("base", "relay_1")
    print("Failure impact of relay_1:", fail_impact)
    assert fail_impact["is_single_point_of_failure"] is True
    assert set(fail_impact["severed_units"]) == {"rover_2", "crew_eva"}
    print("-> Resilience analysis & failure impact VERIFIED.")

    # Algebraic connectivity
    alg_conn = g.compute_algebraic_connectivity()
    print(f"Algebraic connectivity (lambda_2): {alg_conn}")

    # Test 2: Real Jezero DTM Promontory Screening
    print("\n--- Test 2: Real Jezero 250x250 DTM Screening ---")
    from marswalk.core.terrain import load_and_process_terrain
    t = load_and_process_terrain("data/processed/jezero_ready_20m.tif")
    candidates = screen_relay_candidates(
        elevation=t.elevation,
        slope_deg=t.slope_deg,
        invalid_mask=t.invalid_mask,
        dx_ground_m=t.dx_ground_m,
        dy_ground_m=t.dy_ground_m,
        max_slope_deg=12.0,
        min_elevation_m=-2500.0,
        min_separation_m=450.0,
        max_candidates=15,
    )
    print(f"Discovered {len(candidates)} promontory candidates on Jezero crater rim:")
    for c in candidates:
        print(f"  {c['candidate_id']}: rc=({c['row']:3d}, {c['col']:3d}), z={c['elevation_m']}m, slope={c['slope_deg']} deg, score={c['prominence_score']}")
    assert 10 <= len(candidates) <= 15
    print("-> Promontory screening VERIFIED.")

    # Test 3: Greedy Submodular Relay Placement
    print("\n--- Test 3: Greedy Submodular Relay Placement Optimization ---")
    # Base station
    g_opt = RelayNetworkGraph(r_max_m=3500.0)
    base_node = RelayNode("BASE", RelayNodeType.BASE_STATION, (117, 157), float(t.elevation[117, 157]), 10.0, "Octavia Butler Base")
    g_opt.add_node(base_node)

    # 3 Exploration target units in delta valleys
    # Target 1: Near base (visible to base directly)
    # Target 2: Deep behind delta scarp (disconnected from base, visible to CAND_01)
    # Target 3: Distant rim valley (disconnected from base, visible to CAND_03)
    t1 = RelayNode("TARGET_1", RelayNodeType.ROBOTIC_ROVER, (115, 150), -2565.0, 2.5, "Delta Front Rover")
    t2 = RelayNode("TARGET_2", RelayNodeType.CREW_EVA, (30, 50), -2540.0, 2.0, "Delta Crater Valley Crew")
    t3 = RelayNode("TARGET_3", RelayNodeType.SCOUT_ROVER, (20, 20), -2550.0, 2.5, "Kodiak Mesa Scout")
    g_opt.add_node(t1)
    g_opt.add_node(t2)
    g_opt.add_node(t3)

    # Base connects directly to Target 1
    g_opt.add_edge(RelayEdge("BASE", "TARGET_1", 200.0, 200.5, LinkVisibilityStatus.VISIBLE, 10.0))

    # Candidate nodes from screened list
    cand_node_objs = []
    cand_edge_objs = []
    for c in candidates[:4]:
        cnode = RelayNode(c["candidate_id"], RelayNodeType.CANDIDATE_RELAY, c["rc"], c["elevation_m"], 10.0, c["candidate_id"], is_active=False)
        cand_node_objs.append(cnode)

    # CAND_01 connects to BASE and to TARGET_2
    cand_edge_objs.append(RelayEdge("BASE", candidates[0]["candidate_id"], 2200.0, 2205.0, LinkVisibilityStatus.VISIBLE, 30.0))
    cand_edge_objs.append(RelayEdge(candidates[0]["candidate_id"], "TARGET_2", 800.0, 802.0, LinkVisibilityStatus.VISIBLE, 25.0))

    # CAND_02 connects only to TARGET_2 (not base, so won't connect to base unless chained)
    cand_edge_objs.append(RelayEdge(candidates[1]["candidate_id"], "TARGET_2", 600.0, 601.0, LinkVisibilityStatus.VISIBLE, 15.0))

    # CAND_03 connects to BASE and to TARGET_3
    cand_edge_objs.append(RelayEdge("BASE", candidates[2]["candidate_id"], 2400.0, 2406.0, LinkVisibilityStatus.VISIBLE, 35.0))
    cand_edge_objs.append(RelayEdge(candidates[2]["candidate_id"], "TARGET_3", 750.0, 752.0, LinkVisibilityStatus.VISIBLE, 22.0))

    opt_res = optimize_relay_placement(
        graph=g_opt,
        base_node_id="BASE",
        target_unit_ids=["TARGET_1", "TARGET_2", "TARGET_3"],
        candidate_nodes=cand_node_objs,
        candidate_edges=cand_edge_objs,
        relay_budget=2,
    )
    print("Optimization Result:")
    print("Budget used:", opt_res["budget_used"], "/", opt_res["budget_limit"])
    print("Initial connected targets:", opt_res["initial_connected_count"])
    print("Final connected targets:", opt_res["final_connected_count"], "of 3 (Coverage:", opt_res["coverage_percentage"], "%)")
    for step in opt_res["iteration_log"]:
        print(f"  Step {step['step']}: Picked {step['selected_relay_id']} -> newly connected {step['newly_connected_units']}")
    assert opt_res["final_connected_count"] == 3
    assert opt_res["coverage_percentage"] == 100.0
    print("-> Greedy Submodular Placement VERIFIED.")

    print("\n=================================================================")
    print("ALL AGENT B TESTS AND SCIENTIFIC VERIFICATIONS PASSED CLEANLY!")
    print("=================================================================")
