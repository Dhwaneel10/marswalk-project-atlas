with open('src/marswalk/core/joint_mission_planner.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace RelayNode property accesses
text = text.replace('base_node.row', 'base_node.rc[0]')
text = text.replace('base_node.col', 'base_node.rc[1]')
text = text.replace('r.row', 'r.rc[0]')
text = text.replace('r.col', 'r.rc[1]')
text = text.replace('r_a.row', 'r_a.rc[0]')
text = text.replace('r_a.col', 'r_a.rc[1]')
text = text.replace('r_b.row', 'r_b.rc[0]')
text = text.replace('r_b.col', 'r_b.rc[1]')

# Fix RelayNode instantiation 1: in optimize_joint_mission
old_rn1 = """    base_node = RelayNode(
        node_id=str(base_station.get("node_id", "BASE")),
        row=int(base_station.get("row", start_rc[0])),
        col=int(base_station.get("col", start_rc[1])),
        elevation_m=b_elev,
        antenna_height_m=base_antenna_h,
        effective_z_m=b_elev + base_antenna_h,
        node_type=RelayNodeType.BASE_STATION,
        label=str(base_station.get("label", "Base Station")),
    )"""

new_rn1 = """    base_node = RelayNode(
        node_id=str(base_station.get("node_id", "BASE")),
        node_type=RelayNodeType.BASE_STATION,
        rc=(int(base_station.get("row", start_rc[0])), int(base_station.get("col", start_rc[1]))),
        elevation_m=b_elev,
        antenna_height_m=base_antenna_h,
        label=str(base_station.get("label", "Base Station")),
    )"""

text = text.replace(old_rn1, new_rn1)

# Fix RelayNode instantiation 2: in candidate pool
old_rn2 = """        r_node = RelayNode(
            node_id=c_id,
            row=cr,
            col=cc,
            elevation_m=c_elev,
            antenna_height_m=relay_antenna_h,
            effective_z_m=c_elev + relay_antenna_h,
            node_type=RelayNodeType.SURFACE_RELAY,
            label=f"Promontory Relay ({cr}, {cc})",
        )"""

new_rn2 = """        r_node = RelayNode(
            node_id=c_id,
            node_type=RelayNodeType.SURFACE_RELAY,
            rc=(cr, cc),
            elevation_m=c_elev,
            antenna_height_m=relay_antenna_h,
            label=f"Promontory Relay ({cr}, {cc})",
        )"""

text = text.replace(old_rn2, new_rn2)

# Fix RelayNode instantiation 3: in evaluate_joint_mission
old_rn3 = """    base_node = RelayNode(
        node_id=str(base_station.get("node_id", "BASE")),
        row=b_row,
        col=b_col,
        elevation_m=b_elev,
        antenna_height_m=b_h,
        effective_z_m=b_elev + b_h,
        node_type=RelayNodeType.BASE_STATION,
        label=str(base_station.get("label", "Base Station")),
    )"""

new_rn3 = """    base_node = RelayNode(
        node_id=str(base_station.get("node_id", "BASE")),
        node_type=RelayNodeType.BASE_STATION,
        rc=(b_row, b_col),
        elevation_m=b_elev,
        antenna_height_m=b_h,
        label=str(base_station.get("label", "Base Station")),
    )"""

text = text.replace(old_rn3, new_rn3)

old_rn4 = """            relay_nodes.append(
                RelayNode(
                    node_id=str(r.get("node_id", f"RELAY_{rr}_{rc}")),
                    row=rr,
                    col=rc,
                    elevation_m=r_elev,
                    antenna_height_m=r_h,
                    effective_z_m=r_elev + r_h,
                    node_type=RelayNodeType.SURFACE_RELAY,
                )
            )"""

new_rn4 = """            relay_nodes.append(
                RelayNode(
                    node_id=str(r.get("node_id", f"RELAY_{rr}_{rc}")),
                    node_type=RelayNodeType.SURFACE_RELAY,
                    rc=(rr, rc),
                    elevation_m=r_elev,
                    antenna_height_m=r_h,
                )
            )"""

text = text.replace(old_rn4, new_rn4)

with open('src/marswalk/core/joint_mission_planner.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated RelayNode references successfully!')
