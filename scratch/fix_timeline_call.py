with open('src/marswalk/core/joint_mission_planner.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_block = """    # Base Station RelayNode dict conversion for mission_connectivity
    base_dict = {
        \"node_id\": base_node.node_id,
        \"row\": base_node.rc[0],
        \"col\": base_node.rc[1],
        \"elevation_m\": base_node.elevation_m,
        \"antenna_height_m\": base_node.antenna_height_m,
    }

    relays_dicts = [
        {
            \"node_id\": r.node_id,
            \"row\": r.rc[0],
            \"col\": r.rc[1],
            \"elevation_m\": r.elevation_m,
            \"antenna_height_m\": r.antenna_height_m,
        }
        for r in deployed_relays
    ]

    # Invoke RelayNet dynamic mission connectivity timeline engine
    timeline_res = compute_mission_connectivity_timeline(
        path_rc=path,
        elevation_grid=terrain.elevation,
        base_station=base_dict,
        deployed_relays=relays_dicts,
        direct_range_m=max_direct_range_m,
        relay_range_m=max_relay_range_m,
        rover_antenna_h_m=rover_antenna_h,
        dx_m=dx,
        dy_m=dy,
        sampling_interval_s=sampling_interval_s,
    )"""

new_block = """    # Base Station RelayNode dict conversion for mission_connectivity
    base_dict = {
        \"id\": base_node.node_id,
        \"rc\": (base_node.rc[0], base_node.rc[1]),
        \"antenna_h\": base_node.antenna_height_m,
    }

    relays_dicts = [
        {
            \"id\": r.node_id,
            \"rc\": (r.rc[0], r.rc[1]),
            \"antenna_h\": r.antenna_height_m,
        }
        for r in deployed_relays
    ]

    # Invoke RelayNet dynamic mission connectivity timeline engine
    timeline_res = compute_mission_connectivity_timeline(
        elevation=terrain.elevation,
        trajectory_points=trajectory_points,
        base_station=base_dict,
        relays=relays_dicts,
        direct_range_m=max_direct_range_m,
        relay_range_m=max_relay_range_m,
        rover_antenna_h_m=rover_antenna_h,
        dx_ground_m=dx,
        dy_ground_m=dy,
        invalid_mask=terrain.invalid_mask,
    )"""

assert old_block in text, "old_block not found in file"
text = text.replace(old_block, new_block, 1)

with open('src/marswalk/core/joint_mission_planner.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated compute_mission_connectivity_timeline call successfully!')
