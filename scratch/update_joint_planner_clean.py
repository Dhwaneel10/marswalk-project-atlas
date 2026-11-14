with open('src/marswalk/core/joint_mission_planner.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Make sure LinkVisibilityStatus is imported
if 'LinkVisibilityStatus' not in code:
    code = code.replace(
        'from marswalk.core.relay_graph import (',
        'from marswalk.core.relay_graph import (\n    LinkVisibilityStatus,'
    )

# Fix screen_relay_candidates call
old_screen = """    candidate_promontories = screen_relay_candidates(
        elevation_grid=terrain.elevation,
        slope_grid=terrain.slope_deg,
        max_slope_deg=12.0,
        min_elevation_m=-2500.0,
        min_separation_m=450.0,
        max_candidates=12,
    )"""

new_screen = """    candidate_promontories = screen_relay_candidates(
        elevation=terrain.elevation,
        slope_deg=terrain.slope_deg,
        invalid_mask=terrain.invalid_mask,
        dx_ground_m=dx,
        dy_ground_m=dy,
        max_slope_deg=12.0,
        min_elevation_m=-2500.0,
        min_separation_m=450.0,
        max_candidates=12,
    )"""

code = code.replace(old_screen, new_screen)

# Fix RelayEdge in evaluate_traverse_connectivity_with_relays
old_edge1 = """            edge = RelayEdge(
                source_id=base_node.node_id,
                target_id=r.node_id,
                distance_m=los_base.distance_m,
                min_clearance_m=los_base.min_clearance_m,
                is_visible=True,
                status=los_base.status,
            )"""

new_edge1 = """            edge = RelayEdge(
                u=base_node.node_id,
                v=r.node_id,
                distance_m=los_base.distance_m,
                slant_range_m=los_base.distance_m,
                visibility=LinkVisibilityStatus.VISIBLE if los_base.is_visible else LinkVisibilityStatus.BLOCKED,
                min_clearance_m=los_base.min_clearance_m,
                num_hops=1,
                propagation_delay_us=(los_base.distance_m / 299792458.0) * 1e6,
            )"""

code = code.replace(old_edge1, new_edge1)

old_edge2 = """                edge = RelayEdge(
                    source_id=r_a.node_id,
                    target_id=r_b.node_id,
                    distance_m=los_inter.distance_m,
                    min_clearance_m=los_inter.min_clearance_m,
                    is_visible=True,
                    status=los_inter.status,
                )"""

new_edge2 = """                edge = RelayEdge(
                    u=r_a.node_id,
                    v=r_b.node_id,
                    distance_m=los_inter.distance_m,
                    slant_range_m=los_inter.distance_m,
                    visibility=LinkVisibilityStatus.VISIBLE if los_inter.is_visible else LinkVisibilityStatus.BLOCKED,
                    min_clearance_m=los_inter.min_clearance_m,
                    num_hops=1,
                    propagation_delay_us=(los_inter.distance_m / 299792458.0) * 1e6,
                )"""

code = code.replace(old_edge2, new_edge2)

# Fix optimize_relay_placement call section inside optimize_joint_mission
old_opt_call = """            if k > 0 and relay_pool_nodes:
                # Use RelayNet greedy submodular placement
                base_dict = {\"node_id\": base_node.node_id, \"row\": base_node.rc[0], \"col\": base_node.rc[1], \"antenna_height_m\": base_node.antenna_height_m}
                opt_res = optimize_relay_placement(
                    candidates=candidate_promontories,
                    base_station=base_dict,
                    target_units=downsampled_units,
                    relay_budget=k,
                    max_direct_range_m=max_direct_range_m,
                    max_relay_range_m=max_relay_range_m,
                )
                selected_cands = opt_res.get(\"selected_relays\", [])
                selected_ids = {c[\"candidate_id\"] for c in selected_cands}
                deployed_relays = [rn for rn in relay_pool_nodes if rn.node_id in selected_ids]"""

new_opt_call = """            if k > 0 and relay_pool_nodes:
                # Build evaluation graph with Base Station and downsampled target units
                g = RelayNetworkGraph(r_max_m=max_relay_range_m)
                g.add_node(base_node)
                target_unit_ids = []
                target_nodes = []
                for tu_dict in downsampled_units:
                    tu_id = tu_dict[\"node_id\"]
                    tur, tuc = tu_dict[\"row\"], tu_dict[\"col\"]
                    tu_elev = float(terrain.elevation[tur, tuc])
                    tu_node = RelayNode(
                        node_id=tu_id,
                        node_type=RelayNodeType.ROBOTIC_ROVER,
                        rc=(tur, tuc),
                        elevation_m=tu_elev,
                        antenna_height_m=rover_antenna_h,
                    )
                    g.add_node(tu_node)
                    target_unit_ids.append(tu_id)
                    target_nodes.append(tu_node)

                    # Edge to Base if visible
                    los_direct = calculate_line_of_sight(
                        terrain.elevation,
                        base_node.rc,
                        (tur, tuc),
                        base_node.antenna_height_m,
                        rover_antenna_h,
                        max_range_m=max_direct_range_m,
                        dx_m=dx,
                        dy_m=dy,
                    )
                    if los_direct.is_visible:
                        g.add_edge(RelayEdge(
                            u=base_node.node_id,
                            v=tu_id,
                            distance_m=los_direct.distance_m,
                            slant_range_m=los_direct.distance_m,
                            visibility=LinkVisibilityStatus.VISIBLE,
                            min_clearance_m=los_direct.min_clearance_m,
                        ))

                # Candidate edges to Base and Targets
                candidate_edges = []
                for cand in relay_pool_nodes:
                    los_b = calculate_line_of_sight(
                        terrain.elevation,
                        base_node.rc,
                        cand.rc,
                        base_node.antenna_height_m,
                        cand.antenna_height_m,
                        max_range_m=max_relay_range_m,
                        dx_m=dx,
                        dy_m=dy,
                    )
                    if los_b.is_visible:
                        candidate_edges.append(RelayEdge(
                            u=base_node.node_id,
                            v=cand.node_id,
                            distance_m=los_b.distance_m,
                            slant_range_m=los_b.distance_m,
                            visibility=LinkVisibilityStatus.VISIBLE,
                            min_clearance_m=los_b.min_clearance_m,
                        ))
                    for tu in target_nodes:
                        los_u = calculate_line_of_sight(
                            terrain.elevation,
                            cand.rc,
                            tu.rc,
                            cand.antenna_height_m,
                            tu.antenna_height_m,
                            max_range_m=max_relay_range_m,
                            dx_m=dx,
                            dy_m=dy,
                        )
                        if los_u.is_visible:
                            candidate_edges.append(RelayEdge(
                                u=cand.node_id,
                                v=tu.node_id,
                                distance_m=los_u.distance_m,
                                slant_range_m=los_u.distance_m,
                                visibility=LinkVisibilityStatus.VISIBLE,
                                min_clearance_m=los_u.min_clearance_m,
                            ))

                opt_res = optimize_relay_placement(
                    graph=g,
                    base_node_id=base_node.node_id,
                    target_unit_ids=target_unit_ids,
                    candidate_nodes=relay_pool_nodes,
                    candidate_edges=candidate_edges,
                    relay_budget=k,
                )
                deployed_relays = opt_res.get(\"selected_relays\", [])"""

code = code.replace(old_opt_call, new_opt_call)

with open('src/marswalk/core/joint_mission_planner.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('Updated joint_mission_planner.py successfully!')
