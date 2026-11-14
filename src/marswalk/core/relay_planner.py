"""
MarsWalk Core Relay Planner & Site Candidate Optimizer (Milestone 13D - Atlas Mars RelayNet).

Discovers and optimizes autonomous communications relay sites across authentic Martian topography:
1. Promontory / Ridge Candidate Screening (`screen_relay_candidates`):
   - Slope constraint <= 12 deg (structural stability & robotic anchor safety).
   - High relative elevation > -2500 m (promontories, crater rim overlooks).
   - Non-Maximum Suppression (NMS) with minimum spatial ground separation >= 450 m (prevents site clustering).
   - Bounded candidate pool (10-15 high-value candidate sites).
2. Greedy Submodular Relay Site Placement (`optimize_relay_placement`):
   - Maximizes incremental newly connected exploration units to Base Station within a fixed relay budget (1-3 relays).
   - Deterministic tie-breaking hierarchy:
     1. Marginal coverage gain Delta(r) DESC.
     2. Average hop count from newly connected units to Base ASC.
     3. Candidate topographic elevation DESC.
     4. Candidate ID string ASC.
   - Comprehensive delta reporting: before/after connectivity, coverage percentage, and step log.
"""

from dataclasses import dataclass
import math
from typing import Dict, List, Tuple, Set, Optional, Any
import numpy as np

from marswalk.core.relay_graph import (
    RelayNode,
    RelayNodeType,
    RelayEdge,
    LinkVisibilityStatus,
    RelayNetworkGraph,
)
from marswalk.core.terrain_visibility import (
    calculate_line_of_sight,
    DEFAULT_DX_M,
    DEFAULT_DY_M,
)


def screen_relay_candidates(
    elevation: np.ndarray,
    slope_deg: np.ndarray,
    invalid_mask: Optional[np.ndarray],
    dx_ground_m: float = DEFAULT_DX_M,
    dy_ground_m: float = DEFAULT_DY_M,
    max_slope_deg: float = 12.0,
    min_elevation_m: float = -2500.0,
    min_separation_m: float = 450.0,
    max_candidates: int = 15,
    border_margin: int = 5,
) -> List[Dict[str, Any]]:
    """
    Screens topographic promontory/ridge candidate sites from Jezero DTM.

    Parameters
    ----------
    elevation : np.ndarray
        Elevation matrix [H, W] in meters.
    slope_deg : np.ndarray
        Local slope matrix [H, W] in degrees.
    invalid_mask : Optional[np.ndarray]
        Boolean invalid/NoData mask.
    dx_ground_m : float
        Metric ground pixel width East-West.
    dy_ground_m : float
        Metric ground pixel height North-South.
    max_slope_deg : float
        Maximum allowable slope for structural relay foundation (default 12.0 deg).
    min_elevation_m : float
        Minimum elevation cutoff for high-vantage rim sites (default -2500.0 m).
    min_separation_m : float
        Anti-clustering non-maximum suppression radius (default 450.0 m).
    max_candidates : int
        Maximum number of screened candidates (default 15).
    border_margin : int
        Pixel margin from raster boundaries to avoid edge artifacts.

    Returns
    -------
    List[Dict[str, Any]]
        Ranked list of candidate dictionaries.
    """
    H, W = elevation.shape
    valid_cells = (elevation > min_elevation_m) & (slope_deg <= max_slope_deg)
    if invalid_mask is not None:
        valid_cells &= (~invalid_mask)

    # Exclude border regions
    valid_cells[:border_margin, :] = False
    valid_cells[-border_margin:, :] = False
    valid_cells[:, :border_margin] = False
    valid_cells[:, -border_margin:] = False

    rows, cols = np.where(valid_cells)
    if len(rows) == 0:
        return []

    elevs = elevation[rows, cols]
    slopes = slope_deg[rows, cols]

    # Prominence & Placement Score: 70% normalized elevation + 30% flatness
    min_e, max_e = float(elevs.min()), float(elevs.max())
    elev_range = max(1e-6, max_e - min_e)
    norm_e = (elevs - min_e) / elev_range
    norm_s = 1.0 - np.clip(slopes / max(1e-6, max_slope_deg), 0.0, 1.0)
    scores = 0.7 * norm_e + 0.3 * norm_s

    # Deterministic sorting: Descending by score, then ascending by row, then col
    sort_keys = list(zip(-scores, rows, cols))
    sorted_order = sorted(range(len(rows)), key=lambda i: sort_keys[i])

    selected: List[Dict[str, Any]] = []
    selected_rc: List[Tuple[int, int]] = []

    for idx in sorted_order:
        r, c = int(rows[idx]), int(cols[idx])
        too_close = False
        for sr, sc in selected_rc:
            dist = math.sqrt(((c - sc) * dx_ground_m) ** 2 + ((r - sr) * dy_ground_m) ** 2)
            if dist < min_separation_m:
                too_close = True
                break

        if not too_close:
            selected_rc.append((r, c))
            cand_id = f"MRN_CAND_{len(selected) + 1:02d}"
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


def optimize_relay_placement(
    graph: RelayNetworkGraph,
    base_node_id: str,
    target_unit_ids: List[str],
    candidate_nodes: List[RelayNode],
    candidate_edges: List[RelayEdge],
    relay_budget: int = 2,
) -> Dict[str, Any]:
    """
    Greedy Submodular Relay Site Placement.

    Parameters
    ----------
    graph : RelayNetworkGraph
        Network graph containing active nodes (Base Station and Target Units).
    base_node_id : str
        Node ID of central Base Station.
    target_unit_ids : List[str]
        IDs of exploration units required to reach Base.
    candidate_nodes : List[RelayNode]
        Available candidate relay nodes (initially inactive).
    candidate_edges : List[RelayEdge]
        Precomputed line-of-sight edges connecting candidates to base, units, or other candidates.
    relay_budget : int
        Maximum number of relays to deploy (default 2).

    Returns
    -------
    Dict[str, Any]
        Comprehensive optimization report with before/after reachability and step log.
    """
    # Baseline reachability before any relays are added
    baseline_eval = graph.evaluate_base_reachability(base_node_id)
    baseline_reachable = baseline_eval["reachable_nodes"]
    disconnected_targets = set(target_unit_ids) - baseline_reachable

    selected_relays: List[RelayNode] = []
    remaining_candidates = {cn.node_id: cn for cn in candidate_nodes}

    # Index candidate edges
    cand_edge_map: Dict[str, List[RelayEdge]] = {cn.node_id: [] for cn in candidate_nodes}
    for e in candidate_edges:
        if e.u in cand_edge_map:
            cand_edge_map[e.u].append(e)
        if e.v in cand_edge_map:
            cand_edge_map[e.v].append(e)

    iteration_log = []

    for step in range(relay_budget):
        if not disconnected_targets:
            break

        best_cand: Optional[RelayNode] = None
        best_delta = -1
        best_avg_hops = float("inf")
        best_elev = -float("inf")
        best_cand_id = ""

        for cand_id, cand_node in sorted(remaining_candidates.items()):
            # Temporarily activate candidate node and its edges in graph
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

            if delta > 0:
                avg_hops = sum(eval_res["hop_counts"][u] for u in newly_connected) / float(delta)
            else:
                avg_hops = float("inf")

            elev = cand_node.elevation_m

            # Deterministic hierarchy: delta DESC, avg_hops ASC, elev DESC, cand_id ASC
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

        step_eval = graph.evaluate_base_reachability(base_node_id)
        step_reachable = step_eval["reachable_nodes"]
        newly_solved = disconnected_targets.intersection(step_reachable)
        disconnected_targets -= newly_solved

        iteration_log.append({
            "step": step + 1,
            "selected_relay_id": active_version.node_id,
            "rc": [round(float(active_version.rc[0]), 2), round(float(active_version.rc[1]), 2)],
            "elevation_m": round(float(active_version.elevation_m), 2),
            "newly_connected_units": sorted(list(newly_solved)),
            "marginal_coverage_gain": best_delta,
            "remaining_disconnected_units": sorted(list(disconnected_targets)),
        })

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
