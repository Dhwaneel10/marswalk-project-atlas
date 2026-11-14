import sys

def main():
    with open('scripts/run_atlas.py', 'r', encoding='utf-8') as f:
        text = f.read()

    # 1. Update imports
    target_import = '    mission_assurance_dossier_api,\n    APIError,'
    fleet_imports = '''    mission_assurance_dossier_api,
    fleet_create_api,
    fleet_list_api,
    fleet_get_api,
    fleet_register_rover_api,
    fleet_allocate_science_api,
    fleet_plan_routes_api,
    fleet_schedule_api,
    fleet_network_api,
    fleet_resources_api,
    fleet_optimize_api,
    fleet_scenario_api,
    fleet_promote_api,
    fleet_assurance_api,
    APIError,'''

    if target_import not in text:
        print("Warning: target_import not found or already patched")
    else:
        text = text.replace(target_import, fleet_imports, 1)

    # 2. Add GET endpoints
    target_get = '''            elif clean_path.startswith("/api/campaign-branches/"):
                bid = clean_path[len("/api/campaign-branches/"):]
                cid = "cmp_ops_default"
                res = campaign_branches_get_api(bid, cid, self.terrain, self.transform)
                self.send_json_response(res, 200)
                return'''

    fleet_get_code = '''            elif clean_path.startswith("/api/campaign-branches/"):
                bid = clean_path[len("/api/campaign-branches/"):]
                cid = "cmp_ops_default"
                res = campaign_branches_get_api(bid, cid, self.terrain, self.transform)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/fleet/list", "/api/fleets"):
                res = fleet_list_api({}, self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/fleet/") and not clean_path.endswith(("/network", "/resources", "/assurance")):
                fid = clean_path[len("/api/fleet/"):].strip()
                res = fleet_get_api(fid, self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/fleet/network" or clean_path.endswith("/network"):
                res = fleet_network_api({}, self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/fleet/resources" or clean_path.endswith("/resources"):
                res = fleet_resources_api({}, self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/fleet/assurance" or clean_path.endswith("/assurance"):
                res = fleet_assurance_api({}, self.terrain)
                self.send_json_response(res, 200)
                return'''

    if target_get not in text:
        print("Warning: target_get not found or already patched")
    else:
        text = text.replace(target_get, fleet_get_code, 1)

    # 3. Add POST endpoints
    target_post = '''            elif clean_path == "/api/campaign-robustness/evaluate":
                result = campaign_robustness_evaluate_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return'''

    fleet_post_code = '''            elif clean_path == "/api/campaign-robustness/evaluate":
                result = campaign_robustness_evaluate_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/create":
                result = fleet_create_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/fleet/") and clean_path.endswith("/register-rover"):
                fid = clean_path[len("/api/fleet/"):-len("/register-rover")].strip("/")
                payload["fleet_id"] = fid or payload.get("fleet_id", "fleet_jezero_alpha")
                result = fleet_register_rover_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/register-rover":
                result = fleet_register_rover_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/fleet/") and clean_path.endswith("/allocate-science"):
                fid = clean_path[len("/api/fleet/"):-len("/allocate-science")].strip("/")
                payload["fleet_id"] = fid or payload.get("fleet_id", "fleet_jezero_alpha")
                result = fleet_allocate_science_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/allocate-science":
                result = fleet_allocate_science_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/fleet/") and clean_path.endswith("/plan-routes"):
                fid = clean_path[len("/api/fleet/"):-len("/plan-routes")].strip("/")
                payload["fleet_id"] = fid or payload.get("fleet_id", "fleet_jezero_alpha")
                result = fleet_plan_routes_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/plan-routes":
                result = fleet_plan_routes_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/fleet/") and clean_path.endswith("/schedule"):
                fid = clean_path[len("/api/fleet/"):-len("/schedule")].strip("/")
                payload["fleet_id"] = fid or payload.get("fleet_id", "fleet_jezero_alpha")
                result = fleet_schedule_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/schedule":
                result = fleet_schedule_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/fleet/") and clean_path.endswith("/optimize"):
                fid = clean_path[len("/api/fleet/"):-len("/optimize")].strip("/")
                payload["fleet_id"] = fid or payload.get("fleet_id", "fleet_jezero_alpha")
                result = fleet_optimize_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/optimize":
                result = fleet_optimize_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/fleet/") and clean_path.endswith("/scenario"):
                fid = clean_path[len("/api/fleet/"):-len("/scenario")].strip("/")
                payload["fleet_id"] = fid or payload.get("fleet_id", "fleet_jezero_alpha")
                result = fleet_scenario_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/scenario":
                result = fleet_scenario_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/fleet/") and clean_path.endswith("/promote"):
                fid = clean_path[len("/api/fleet/"):-len("/promote")].strip("/")
                payload["fleet_id"] = fid or payload.get("fleet_id", "fleet_jezero_alpha")
                result = fleet_promote_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/promote":
                result = fleet_promote_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return'''

    if target_post not in text:
        print("Warning: target_post not found or already patched")
    else:
        text = text.replace(target_post, fleet_post_code, 1)

    with open('scripts/run_atlas.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Successfully patched scripts/run_atlas.py with Fleet endpoints!")

if __name__ == '__main__':
    main()
