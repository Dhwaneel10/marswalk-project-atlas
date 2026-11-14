import sys

with open("scripts/run_atlas.py", "r", encoding="utf-8") as f:
    content = f.read()

import_target = "    grand_prix_scenarios_api,"
import_replacement = """    grand_prix_scenarios_api,
    planetary_network_topology_api,
    planetary_network_contacts_api,
    planetary_network_scenarios_api,
    planetary_network_scenario_run_api,
    planetary_network_grand_prix_run_api,
    planetary_network_dtn_metrics_api,"""

if import_target in content:
    content = content.replace(import_target, import_replacement, 1)

route_target = 'elif clean_path in ("/api/grand-prix/scenarios", "/api/v1/grand-prix/scenarios"):'
route_block = """elif clean_path in ("/api/planetary-network/topology", "/api/v1/planetary-network/topology"):
                res = planetary_network_topology_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-network/contacts", "/api/v1/planetary-network/contacts"):
                qp = {k: v[0] for k, v in query_params.items()} if query_params else {}
                res = planetary_network_contacts_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-network/scenarios", "/api/v1/planetary-network/scenarios"):
                res = planetary_network_scenarios_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-network/scenarios/run", "/api/v1/planetary-network/scenarios/run"):
                qp = {k: v[0] for k, v in query_params.items()} if query_params else {}
                res = planetary_network_scenario_run_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-network/grand-prix/run", "/api/v1/planetary-network/grand-prix/run"):
                qp = {k: v[0] for k, v in query_params.items()} if query_params else {}
                res = planetary_network_grand_prix_run_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-network/dtn/metrics", "/api/v1/planetary-network/dtn/metrics"):
                res = planetary_network_dtn_metrics_api()
                self.send_json_response(res, 200)
                return
            """ + route_target

if route_target in content:
    content = content.replace(route_target, route_block, 1)

with open("scripts/run_atlas.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully patched run_atlas.py with planetary network endpoints.")
