import sys

with open("scripts/run_atlas.py", "r", encoding="utf-8") as f:
    content = f.read()

import_target = "    planetary_network_dtn_metrics_api,"
import_replacement = """    planetary_network_dtn_metrics_api,
    planetary_foundry_overview_api,
    planetary_foundry_catalogue_api,
    planetary_foundry_fleet_api,
    planetary_foundry_materials_api,
    planetary_foundry_scenarios_api,
    planetary_foundry_scenario_run_api,
    planetary_foundry_grand_prix_run_api,"""

if import_target in content:
    content = content.replace(import_target, import_replacement, 1)

route_target = 'elif clean_path in ("/api/planetary-network/dtn/metrics", "/api/v1/planetary-network/dtn/metrics"):'
route_block = """elif clean_path in ("/api/planetary-foundry/overview", "/api/v1/planetary-foundry/overview"):
                res = planetary_foundry_overview_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-foundry/catalogue", "/api/v1/planetary-foundry/catalogue"):
                res = planetary_foundry_catalogue_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-foundry/fleet", "/api/v1/planetary-foundry/fleet"):
                res = planetary_foundry_fleet_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-foundry/materials", "/api/v1/planetary-foundry/materials"):
                res = planetary_foundry_materials_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-foundry/scenarios", "/api/v1/planetary-foundry/scenarios"):
                res = planetary_foundry_scenarios_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-foundry/scenarios/run", "/api/v1/planetary-foundry/scenarios/run"):
                qp = {k: v[0] for k, v in query_params.items()} if query_params else {}
                res = planetary_foundry_scenario_run_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-foundry/grand-prix/run", "/api/v1/planetary-foundry/grand-prix/run"):
                qp = {k: v[0] for k, v in query_params.items()} if query_params else {}
                res = planetary_foundry_grand_prix_run_api(qp)
                self.send_json_response(res, 200)
                return
            """ + route_target

if route_target in content:
    content = content.replace(route_target, route_block, 1)

with open("scripts/run_atlas.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully patched run_atlas.py with Planetary Foundry endpoints.")
