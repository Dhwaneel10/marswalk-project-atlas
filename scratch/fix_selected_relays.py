with open('src/marswalk/core/joint_mission_planner.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_code = """                opt_res = optimize_relay_placement(
                    graph=g,
                    base_node_id=base_node.node_id,
                    target_unit_ids=target_unit_ids,
                    candidate_nodes=relay_pool_nodes,
                    candidate_edges=candidate_edges,
                    relay_budget=k,
                )
                deployed_relays = opt_res.get("selected_relays", [])"""

new_code = """                opt_res = optimize_relay_placement(
                    graph=g,
                    base_node_id=base_node.node_id,
                    target_unit_ids=target_unit_ids,
                    candidate_nodes=relay_pool_nodes,
                    candidate_edges=candidate_edges,
                    relay_budget=k,
                )
                selected_dicts = opt_res.get("selected_relays", [])
                selected_ids = {d.get("node_id") for d in selected_dicts}
                deployed_relays = [rn for rn in relay_pool_nodes if rn.node_id in selected_ids]"""

assert old_code in text, "old_code not found in joint_mission_planner.py"
text = text.replace(old_code, new_code, 1)

with open('src/marswalk/core/joint_mission_planner.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Fixed deployed_relays conversion in joint_mission_planner.py')
