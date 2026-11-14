"""
Script to append RelayNet API handlers to src/marswalk/api/service.py.
"""

service_code = '''

# ==============================================================================
# Milestone 13D: Atlas Mars RelayNet API Handlers
# ==============================================================================

from marswalk.core.terrain_visibility import (
    calculate_line_of_sight,
    sample_bilinear_elevation,
    DEFAULT_DX_M,
    DEFAULT_DY_M,
)
from marswalk.core.relay_graph import (
    RelayNode,
    RelayNodeType,
    RelayEdge,
    LinkVisibilityStatus,
    RelayNetworkGraph,
)
from marswalk.core.relay_planner import (
    screen_relay_candidates,
    optimize_relay_placement,
)
from marswalk.core.mission_connectivity import (
    compute_mission_connectivity_timeline,
    DynamicCommState,
)


def relaynet_los_api(payload: Dict[str, Any], terrain: TerrainGrid, transform: Any) -> Dict[str, Any]:
    """
    Pairwise Line-of-Sight API handler.
    Supports payload format with origin/target or point_a/point_b.
    """
    try:
        # Parse endpoint A
        origin = payload.get("origin") or payload.get("point_a") or {}
        target = payload.get("target") or payload.get("point_b") or {}

        r_a = float(origin.get("row", payload.get("r_a", 0)))
        c_a = float(origin.get("col", payload.get("c_a", 0)))
        h_a = float(origin.get("antenna_height_m", origin.get("antenna_h", payload.get("h_a", 2.5))))
        id_a = str(origin.get("id", payload.get("endpoint_a_id", "node_a")))

        r_b = float(target.get("row", payload.get("r_b", 0)))
        c_b = float(target.get("col", payload.get("c_b", 0)))
        h_b = float(target.get("antenna_height_m", target.get("antenna_h", payload.get("h_b", 10.0))))
        id_b = str(target.get("id", payload.get("endpoint_b_id", "node_b")))

        max_range_m = payload.get("max_range_m")
        if max_range_m is not None:
            max_range_m = float(max_range_m)

        clearance_margin_m = float(payload.get("clearance_margin_m", 0.0))

        res = calculate_line_of_sight(
            elevation_grid=terrain.elevation,
            point_a=(r_a, c_a),
            point_b=(r_b, c_b),
            antenna_h_a=h_a,
            antenna_h_b=h_b,
            dx_m=terrain.dx_ground_m,
            dy_m=terrain.dy_ground_m,
            max_range_m=max_range_m,
            clearance_margin_m=clearance_margin_m,
            invalid_mask=terrain.invalid_mask,
            endpoint_a_id=id_a,
            endpoint_b_id=id_b,
        )

        res_dict = res.to_dict()
        res_dict["schema_version"] = "1.0.0"
        return res_dict

    except Exception as err:
        raise APIError(f"Line-of-Sight evaluation failed: {str(err)}", 400)


def relaynet_graph_api(payload: Dict[str, Any], terrain: TerrainGrid, transform: Any) -> Dict[str, Any]:
    """
    Builds the communication topology graph from base station, active rover unit,
    and relay stations. Evaluates reachability, minimum-hop paths, and link statuses.
    """
    try:
        base_dict = payload.get("base_station") or {"row": 117, "col": 157, "antenna_height_m": 10.0}
        base_r = float(base_dict.get("row", 117))
        base_c = float(base_dict.get("col", 157))
        base_h = float(base_dict.get("antenna_height_m", 10.0))
        base_id = str(base_dict.get("node_id", "BASE"))

        direct_range_m = float(payload.get("direct_range_limit_m", 2500.0))
        relay_range_m = float(payload.get("relay_range_limit_m", 5000.0))

        g = RelayNetworkGraph(r_max_m=max(direct_range_m, relay_range_m))

        # Add Base Node
        z_base, _ = sample_bilinear_elevation(terrain.elevation, base_r, base_c, terrain.invalid_mask)
        z_base = z_base if z_base is not None else float(terrain.elevation[int(round(base_r)), int(round(base_c))])
        base_node = RelayNode(
            node_id=base_id,
            node_type=RelayNodeType.BASE_STATION,
            rc=(base_r, base_c),
            elevation_m=z_base,
            antenna_height_m=base_h,
            label=base_dict.get("label", "Octavia Butler Base"),
            is_active=True,
        )
        g.add_node(base_node)

        # Optional Rover Unit
        rover_node = None
        rover_id = "ROVER"
        rover_dict = payload.get("rover_unit")
        if rover_dict:
            rover_r = float(rover_dict.get("row", 117))
            rover_c = float(rover_dict.get("col", 157))
            rover_h = float(rover_dict.get("antenna_height_m", 2.5))
            rover_id = str(rover_dict.get("node_id", "ROVER"))
            z_rover, _ = sample_bilinear_elevation(terrain.elevation, rover_r, rover_c, terrain.invalid_mask)
            z_rover = z_rover if z_rover is not None else float(terrain.elevation[int(round(rover_r)), int(round(rover_c))])
            rover_node = RelayNode(
                node_id=rover_id,
                node_type=RelayNodeType.ROBOTIC_ROVER,
                rc=(rover_r, rover_c),
                elevation_m=z_rover,
                antenna_height_m=rover_h,
                label=rover_dict.get("label", "Perseverance Rover"),
                is_active=True,
            )
            g.add_node(rover_node)

        # Relays
        relay_nodes = []
        for r_entry in payload.get("relays", []):
            rid = str(r_entry.get("relay_id") or r_entry.get("node_id"))
            rr = float(r_entry.get("row", 0))
            rc = float(r_entry.get("col", 0))
            rh = float(r_entry.get("antenna_height_m", 10.0))
            is_act = bool(r_entry.get("is_active", True))
            zr, _ = sample_bilinear_elevation(terrain.elevation, rr, rc, terrain.invalid_mask)
            zr = zr if zr is not None else float(terrain.elevation[int(round(rr)), int(round(rc))])
            rn = RelayNode(
                node_id=rid,
                node_type=RelayNodeType.ACTIVE_RELAY if is_act else RelayNodeType.CANDIDATE_RELAY,
                rc=(rr, rc),
                elevation_m=zr,
                antenna_height_m=rh,
                label=r_entry.get("label", rid),
                is_active=is_act,
            )
            g.add_node(rn)
            if is_act:
                relay_nodes.append(rn)

        # Pre-evaluate pairwise edges
        evaluated_edges: List[Dict[str, Any]] = []

        # 1. Base <-> Relays
        for rn in relay_nodes:
            los = calculate_line_of_sight(
                elevation_grid=terrain.elevation,
                point_a=base_node.rc,
                point_b=rn.rc,
                antenna_h_a=base_node.antenna_height_m,
                antenna_h_b=rn.antenna_height_m,
                dx_m=terrain.dx_ground_m,
                dy_m=terrain.dy_ground_m,
                max_range_m=relay_range_m,
                invalid_mask=terrain.invalid_mask,
                endpoint_a_id=base_node.node_id,
                endpoint_b_id=rn.node_id,
            )
            status_val = LinkVisibilityStatus.VISIBLE if los.is_visible else (
                LinkVisibilityStatus.OUT_OF_RANGE if los.is_out_of_range else LinkVisibilityStatus.BLOCKED
            )
            if los.is_visible:
                g.add_edge(RelayEdge(
                    u=base_node.node_id,
                    v=rn.node_id,
                    distance_m=los.ground_distance_m,
                    slant_range_m=los.slant_distance_m or los.ground_distance_m,
                    visibility=status_val,
                    min_clearance_m=los.min_clearance_m or 0.0,
                ))
            obs_rc = [los.first_obstruction.row, los.first_obstruction.col] if los.first_obstruction else None
            evaluated_edges.append({
                "source": base_node.node_id,
                "target": rn.node_id,
                "status": status_val.value,
                "distance_m": round(los.ground_distance_m, 2),
                "min_clearance_m": round(los.min_clearance_m or 0.0, 2),
                "obstruction_rc": obs_rc,
            })

        # 2. Relay <-> Relay
        for i in range(len(relay_nodes)):
            for j in range(i + 1, len(relay_nodes)):
                r1, r2 = relay_nodes[i], relay_nodes[j]
                los = calculate_line_of_sight(
                    elevation_grid=terrain.elevation,
                    point_a=r1.rc,
                    point_b=r2.rc,
                    antenna_h_a=r1.antenna_height_m,
                    antenna_h_b=r2.antenna_height_m,
                    dx_m=terrain.dx_ground_m,
                    dy_m=terrain.dy_ground_m,
                    max_range_m=relay_range_m,
                    invalid_mask=terrain.invalid_mask,
                    endpoint_a_id=r1.node_id,
                    endpoint_b_id=r2.node_id,
                )
                status_val = LinkVisibilityStatus.VISIBLE if los.is_visible else (
                    LinkVisibilityStatus.OUT_OF_RANGE if los.is_out_of_range else LinkVisibilityStatus.BLOCKED
                )
                if los.is_visible:
                    g.add_edge(RelayEdge(
                        u=r1.node_id,
                        v=r2.node_id,
                        distance_m=los.ground_distance_m,
                        slant_range_m=los.slant_distance_m or los.ground_distance_m,
                        visibility=status_val,
                        min_clearance_m=los.min_clearance_m or 0.0,
                    ))
                obs_rc = [los.first_obstruction.row, los.first_obstruction.col] if los.first_obstruction else None
                evaluated_edges.append({
                    "source": r1.node_id,
                    "target": r2.node_id,
                    "status": status_val.value,
                    "distance_m": round(los.ground_distance_m, 2),
                    "min_clearance_m": round(los.min_clearance_m or 0.0, 2),
                    "obstruction_rc": obs_rc,
                })

        # 3. Rover <-> Base & Rover <-> Relays
        if rover_node:
            # Rover to Base
            los_base = calculate_line_of_sight(
                elevation_grid=terrain.elevation,
                point_a=rover_node.rc,
                point_b=base_node.rc,
                antenna_h_a=rover_node.antenna_height_m,
                antenna_h_b=base_node.antenna_height_m,
                dx_m=terrain.dx_ground_m,
                dy_m=terrain.dy_ground_m,
                max_range_m=direct_range_m,
                invalid_mask=terrain.invalid_mask,
                endpoint_a_id=rover_node.node_id,
                endpoint_b_id=base_node.node_id,
            )
            status_base = LinkVisibilityStatus.VISIBLE if los_base.is_visible else (
                LinkVisibilityStatus.OUT_OF_RANGE if los_base.is_out_of_range else LinkVisibilityStatus.BLOCKED
            )
            if los_base.is_visible:
                g.add_edge(RelayEdge(
                    u=rover_node.node_id,
                    v=base_node.node_id,
                    distance_m=los_base.ground_distance_m,
                    slant_range_m=los_base.slant_distance_m or los_base.ground_distance_m,
                    visibility=status_base,
                    min_clearance_m=los_base.min_clearance_m or 0.0,
                ))
            obs_rc = [los_base.first_obstruction.row, los_base.first_obstruction.col] if los_base.first_obstruction else None
            evaluated_edges.append({
                "source": rover_node.node_id,
                "target": base_node.node_id,
                "status": status_base.value,
                "distance_m": round(los_base.ground_distance_m, 2),
                "min_clearance_m": round(los_base.min_clearance_m or 0.0, 2),
                "obstruction_rc": obs_rc,
            })

            # Rover to Relays
            for rn in relay_nodes:
                los_r = calculate_line_of_sight(
                    elevation_grid=terrain.elevation,
                    point_a=rover_node.rc,
                    point_b=rn.rc,
                    antenna_h_a=rover_node.antenna_height_m,
                    antenna_h_b=rn.antenna_height_m,
                    dx_m=terrain.dx_ground_m,
                    dy_m=terrain.dy_ground_m,
                    max_range_m=relay_range_m,
                    invalid_mask=terrain.invalid_mask,
                    endpoint_a_id=rover_node.node_id,
                    endpoint_b_id=rn.node_id,
                )
                status_r = LinkVisibilityStatus.VISIBLE if los_r.is_visible else (
                    LinkVisibilityStatus.OUT_OF_RANGE if los_r.is_out_of_range else LinkVisibilityStatus.BLOCKED
                )
                if los_r.is_visible:
                    g.add_edge(RelayEdge(
                        u=rover_node.node_id,
                        v=rn.node_id,
                        distance_m=los_r.ground_distance_m,
                        slant_range_m=los_r.slant_distance_m or los_r.ground_distance_m,
                        visibility=status_r,
                        min_clearance_m=los_r.min_clearance_m or 0.0,
                    ))
                obs_rc = [los_r.first_obstruction.row, los_r.first_obstruction.col] if los_r.first_obstruction else None
                evaluated_edges.append({
                    "source": rover_node.node_id,
                    "target": rn.node_id,
                    "status": status_r.value,
                    "distance_m": round(los_r.ground_distance_m, 2),
                    "min_clearance_m": round(los_r.min_clearance_m or 0.0, 2),
                    "obstruction_rc": obs_rc,
                })

        reach = g.evaluate_base_reachability(base_node.node_id)
        reachable = reach["reachable_nodes"]
        hop_counts = reach["hop_counts"]

        rover_status = "NOT_EVALUATED"
        active_path = []
        hop_count = 0
        if rover_node:
            if rover_node.node_id in reachable:
                active_path = g.get_minimum_hop_path(rover_node.node_id, base_node.node_id) or []
                hop_count = len(active_path) - 1 if len(active_path) > 1 else 0
                rover_status = "CONNECTED_DIRECT" if hop_count == 1 else "CONNECTED_RELAYED"
            else:
                rover_status = "SIMULATED_GEOMETRIC_CONNECTIVITY_GAP"

        # Format node outputs
        node_records = []
        for n in g.nodes.values():
            node_records.append({
                "node_id": n.node_id,
                "node_type": n.node_type.value,
                "rc": [round(n.rc[0], 2), round(n.rc[1], 2)],
                "elevation_m": round(n.elevation_m, 2),
                "antenna_top_elevation_m": round(n.effective_z_m, 2),
                "can_reach_base": n.node_id in reachable,
                "min_hops_to_base": hop_counts.get(n.node_id),
                "is_active": n.is_active,
            })

        connected_relays_count = sum(1 for rn in relay_nodes if rn.node_id in reachable)
        bridges = g.find_bridge_edges()
        alg_conn = g.compute_algebraic_connectivity()

        return {
            "schema_version": "1.0.0",
            "nodes": node_records,
            "edges": evaluated_edges,
            "rover_status": rover_status,
            "active_path": active_path,
            "hop_count": hop_count,
            "connected_relays_count": connected_relays_count,
            "isolated_nodes": sorted(list(reach["isolated_nodes"])),
            "bridge_edges": bridges,
            "algebraic_connectivity": alg_conn,
            "provenance": {
                "source_dataset": "USGS CTX 20m Jezero Crater DTM (DOI 10.5066/P906QQT8)",
                "coordinate_reference_system": "ESRI:103885 (Equirectangular Mars Sphere)",
                "model_disclaimer": "Geometric line-of-sight analysis only. Does not model RF propagation or astronaut safety.",
            },
        }

    except Exception as err:
        raise APIError(f"Network graph evaluation failed: {str(err)}", 400)


def relaynet_candidates_api(payload: Dict[str, Any], terrain: TerrainGrid, transform: Any) -> Dict[str, Any]:
    """
    Screens topographic promontory/ridge candidate sites from Jezero DTM.
    """
    try:
        max_slope_deg = float(payload.get("max_slope_deg", 12.0))
        min_elevation_m = float(payload.get("min_elevation_m", -2500.0))
        min_separation_m = float(payload.get("min_separation_m", 450.0))
        max_candidates = int(payload.get("max_candidates", 15))

        candidates = screen_relay_candidates(
            elevation=terrain.elevation,
            slope_deg=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            dx_ground_m=terrain.dx_ground_m,
            dy_ground_m=terrain.dy_ground_m,
            max_slope_deg=max_slope_deg,
            min_elevation_m=min_elevation_m,
            min_separation_m=min_separation_m,
            max_candidates=max_candidates,
        )

        return {
            "schema_version": "1.0.0",
            "candidates": candidates,
            "total_candidates": len(candidates),
            "screening_criteria": {
                "max_slope_deg": max_slope_deg,
                "min_elevation_m": min_elevation_m,
                "min_separation_m": min_separation_m,
                "max_candidates": max_candidates,
            },
            "source_dataset": "USGS CTX 20m Jezero Crater DTM (DOI 10.5066/P906QQT8)",
            "scientific_disclaimer": (
                "Candidate sites represent high-vantage, low-slope topographic promontories. "
                "Structural placement suitability is a geometric screening step, not an in-situ site certification."
            ),
        }

    except Exception as err:
        raise APIError(f"Candidate screening failed: {str(err)}", 400)


def relaynet_optimize_api(payload: Dict[str, Any], terrain: TerrainGrid, transform: Any) -> Dict[str, Any]:
    """
    Executes greedy submodular relay placement to connect disconnected units to Base Station.
    """
    try:
        base_dict = payload.get("base_station") or {"row": 117, "col": 157, "antenna_height_m": 10.0}
        base_r = float(base_dict.get("row", 117))
        base_c = float(base_dict.get("col", 157))
        base_h = float(base_dict.get("antenna_height_m", 10.0))
        base_id = str(base_dict.get("node_id", "BASE"))

        relay_budget = int(payload.get("relay_budget", 2))
        direct_range_m = float(payload.get("direct_range_limit_m", 2500.0))
        relay_range_m = float(payload.get("relay_range_limit_m", 5000.0))

        # Build initial graph with Base Station
        g = RelayNetworkGraph(r_max_m=max(direct_range_m, relay_range_m))
        z_base, _ = sample_bilinear_elevation(terrain.elevation, base_r, base_c, terrain.invalid_mask)
        z_base = z_base if z_base is not None else float(terrain.elevation[int(round(base_r)), int(round(base_c))])
        base_node = RelayNode(
            node_id=base_id,
            node_type=RelayNodeType.BASE_STATION,
            rc=(base_r, base_c),
            elevation_m=z_base,
            antenna_height_m=base_h,
            label="Base Station",
            is_active=True,
        )
        g.add_node(base_node)

        # Register target exploration units
        target_unit_ids = []
        target_nodes = []
        for u_entry in payload.get("target_units", []):
            uid = str(u_entry.get("unit_id") or u_entry.get("node_id"))
            ur = float(u_entry.get("row", 0))
            uc = float(u_entry.get("col", 0))
            uh = float(u_entry.get("antenna_height_m", 2.5))
            zu, _ = sample_bilinear_elevation(terrain.elevation, ur, uc, terrain.invalid_mask)
            zu = zu if zu is not None else float(terrain.elevation[int(round(ur)), int(round(uc))])
            un = RelayNode(
                node_id=uid,
                node_type=RelayNodeType.ROBOTIC_ROVER,
                rc=(ur, uc),
                elevation_m=zu,
                antenna_height_m=uh,
                label=u_entry.get("label", uid),
                is_active=True,
            )
            g.add_node(un)
            target_unit_ids.append(uid)
            target_nodes.append(un)

            # Test direct link to Base
            los_base = calculate_line_of_sight(
                elevation_grid=terrain.elevation,
                point_a=un.rc,
                point_b=base_node.rc,
                antenna_h_a=un.antenna_height_m,
                antenna_h_b=base_node.antenna_height_m,
                dx_m=terrain.dx_ground_m,
                dy_m=terrain.dy_ground_m,
                max_range_m=direct_range_m,
                invalid_mask=terrain.invalid_mask,
                endpoint_a_id=un.node_id,
                endpoint_b_id=base_node.node_id,
            )
            if los_base.is_visible:
                g.add_edge(RelayEdge(
                    u=un.node_id,
                    v=base_node.node_id,
                    distance_m=los_base.ground_distance_m,
                    slant_range_m=los_base.slant_distance_m or los_base.ground_distance_m,
                    visibility=LinkVisibilityStatus.VISIBLE,
                    min_clearance_m=los_base.min_clearance_m or 0.0,
                ))

        # Obtain candidates (either provided or automatically screened)
        cand_list = payload.get("candidates")
        if not cand_list:
            cand_list = screen_relay_candidates(
                elevation=terrain.elevation,
                slope_deg=terrain.slope_deg,
                invalid_mask=terrain.invalid_mask,
                dx_ground_m=terrain.dx_ground_m,
                dy_ground_m=terrain.dy_ground_m,
                max_candidates=12,
            )

        cand_node_objs: List[RelayNode] = []
        cand_edge_objs: List[RelayEdge] = []

        for c_entry in cand_list:
            cid = str(c_entry.get("candidate_id") or c_entry.get("node_id"))
            cr = float(c_entry.get("row", c_entry.get("rc", [0, 0])[0]))
            cc = float(c_entry.get("col", c_entry.get("rc", [0, 0])[1]))
            ch = float(c_entry.get("antenna_height_m", 10.0))
            zc, _ = sample_bilinear_elevation(terrain.elevation, cr, cc, terrain.invalid_mask)
            zc = zc if zc is not None else float(terrain.elevation[int(round(cr)), int(round(cc))])
            cnode = RelayNode(
                node_id=cid,
                node_type=RelayNodeType.CANDIDATE_RELAY,
                rc=(cr, cc),
                elevation_m=zc,
                antenna_height_m=ch,
                label=cid,
                is_active=False,
            )
            cand_node_objs.append(cnode)

            # Pre-evaluate Candidate <-> Base
            los_base = calculate_line_of_sight(
                elevation_grid=terrain.elevation,
                point_a=cnode.rc,
                point_b=base_node.rc,
                antenna_h_a=cnode.antenna_height_m,
                antenna_h_b=base_node.antenna_height_m,
                dx_m=terrain.dx_ground_m,
                dy_m=terrain.dy_ground_m,
                max_range_m=relay_range_m,
                invalid_mask=terrain.invalid_mask,
                endpoint_a_id=cnode.node_id,
                endpoint_b_id=base_node.node_id,
            )
            if los_base.is_visible:
                cand_edge_objs.append(RelayEdge(
                    u=base_node.node_id,
                    v=cnode.node_id,
                    distance_m=los_base.ground_distance_m,
                    slant_range_m=los_base.slant_distance_m or los_base.ground_distance_m,
                    visibility=LinkVisibilityStatus.VISIBLE,
                    min_clearance_m=los_base.min_clearance_m or 0.0,
                ))

            # Pre-evaluate Candidate <-> Targets
            for tn in target_nodes:
                los_t = calculate_line_of_sight(
                    elevation_grid=terrain.elevation,
                    point_a=cnode.rc,
                    point_b=tn.rc,
                    antenna_h_a=cnode.antenna_height_m,
                    antenna_h_b=tn.antenna_height_m,
                    dx_m=terrain.dx_ground_m,
                    dy_m=terrain.dy_ground_m,
                    max_range_m=relay_range_m,
                    invalid_mask=terrain.invalid_mask,
                    endpoint_a_id=cnode.node_id,
                    endpoint_b_id=tn.node_id,
                )
                if los_t.is_visible:
                    cand_edge_objs.append(RelayEdge(
                        u=cnode.node_id,
                        v=tn.node_id,
                        distance_m=los_t.ground_distance_m,
                        slant_range_m=los_t.slant_distance_m or los_t.ground_distance_m,
                        visibility=LinkVisibilityStatus.VISIBLE,
                        min_clearance_m=los_t.min_clearance_m or 0.0,
                    ))

        opt_result = optimize_relay_placement(
            graph=g,
            base_node_id=base_node.node_id,
            target_unit_ids=target_unit_ids,
            candidate_nodes=cand_node_objs,
            candidate_edges=cand_edge_objs,
            relay_budget=relay_budget,
        )

        opt_result["schema_version"] = "1.0.0"
        opt_result["source_dataset"] = "USGS CTX 20m Jezero Crater DTM (DOI 10.5066/P906QQT8)"
        return opt_result

    except Exception as err:
        raise APIError(f"Relay network optimization failed: {str(err)}", 400)


def relaynet_timeline_api(payload: Dict[str, Any], terrain: TerrainGrid, transform: Any) -> Dict[str, Any]:
    """
    Evaluates dynamic communication connectivity along a simulated mission traverse.
    """
    try:
        base_dict = payload.get("base_station") or {"id": "BASE", "rc": (117, 157), "antenna_h": 10.0}
        relays = payload.get("relays", [])
        direct_range_m = float(payload.get("direct_range_limit_m", 2500.0))
        relay_range_m = float(payload.get("relay_range_limit_m", 5000.0))
        rover_h = float(payload.get("rover_antenna_height_m", 2.5))

        # Extract or derive trajectory points: List of (time_s, row, col)
        trajectory_points: List[Tuple[float, float, float]] = []
        raw_traj = payload.get("trajectory_points")

        if raw_traj:
            for pt in raw_traj:
                trajectory_points.append((float(pt[0]), float(pt[1]), float(pt[2])))
        else:
            # Check for path_rc or route
            path_rc = payload.get("path_rc")
            if not path_rc and payload.get("route"):
                path_rc = payload["route"].get("path_rc")

            if path_rc and len(path_rc) > 0:
                # Parameterize polyline with simulated walking/rover velocity (~1.2 m/s base)
                cum_time = 0.0
                step_dt = 10.0  # 10s default sample interval
                trajectory_points.append((0.0, float(path_rc[0][0]), float(path_rc[0][1])))
                for i in range(len(path_rc) - 1):
                    p0 = path_rc[i]
                    p1 = path_rc[i + 1]
                    dist_seg = math.sqrt(((p1[1] - p0[1]) * terrain.dx_ground_m) ** 2 + ((p1[0] - p0[0]) * terrain.dy_ground_m) ** 2)
                    seg_time = max(5.0, dist_seg / 1.2)  # ~1.2 m/s
                    cum_time += seg_time
                    trajectory_points.append((cum_time, float(p1[0]), float(p1[1])))
            else:
                # Default baseline trajectory from landing site to Three Forks
                trajectory_points = [
                    (0.0, 117.0, 157.0),
                    (60.0, 120.0, 152.0),
                    (120.0, 123.0, 146.0),
                    (180.0, 127.0, 138.0),
                    (240.0, 131.0, 129.0),
                    (300.0, 135.0, 121.0),
                    (360.0, 138.0, 114.0),
                ]

        timeline_result = compute_mission_connectivity_timeline(
            elevation=terrain.elevation,
            trajectory_points=trajectory_points,
            base_station=base_dict,
            relays=relays,
            direct_range_m=direct_range_m,
            relay_range_m=relay_range_m,
            rover_antenna_h_m=rover_h,
            dx_ground_m=terrain.dx_ground_m,
            dy_ground_m=terrain.dy_ground_m,
            invalid_mask=terrain.invalid_mask,
        )

        return timeline_result

    except Exception as err:
        raise APIError(f"Mission connectivity timeline evaluation failed: {str(err)}", 400)
'''

with open("src/marswalk/api/service.py", "a", encoding="utf-8") as f:
    f.write(service_code)

print("Successfully appended RelayNet API handlers to src/marswalk/api/service.py")
