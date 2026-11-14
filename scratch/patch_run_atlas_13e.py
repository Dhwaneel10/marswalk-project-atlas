with open('scripts/run_atlas.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Add imports
target_import = """    relaynet_timeline_api,
    APIError,"""

repl_import = """    relaynet_timeline_api,
    joint_mission_evaluate_api,
    joint_mission_optimize_api,
    joint_mission_configurations_api,
    joint_mission_compare_api,
    joint_mission_promote_api,
    APIError,"""

assert target_import in text, "target_import not found"
text = text.replace(target_import, repl_import, 1)

# 2. Add GET route
target_get = """            elif clean_path == "/api/relaynet/candidates":
                res = relaynet_candidates_api({}, self.terrain, self.transform)
                self.send_json_response(res, 200)
                return"""

repl_get = """            elif clean_path == "/api/relaynet/candidates":
                res = relaynet_candidates_api({}, self.terrain, self.transform)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/joint-mission/configurations", "/api/joint-mission/candidates"):
                res = joint_mission_configurations_api({}, self.terrain, self.transform)
                self.send_json_response(res, 200)
                return"""

assert target_get in text, "target_get not found"
text = text.replace(target_get, repl_get, 1)

# 3. Add POST routes
target_post = """            elif clean_path == "/api/relaynet/timeline":
                result = relaynet_timeline_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return"""

repl_post = """            elif clean_path == "/api/relaynet/timeline":
                result = relaynet_timeline_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/joint-mission/evaluate":
                result = joint_mission_evaluate_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/joint-mission/optimize":
                result = joint_mission_optimize_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/joint-mission/compare":
                result = joint_mission_compare_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/joint-mission/promote":
                result = joint_mission_promote_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return"""

assert target_post in text, "target_post not found"
text = text.replace(target_post, repl_post, 1)

with open('scripts/run_atlas.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Successfully patched scripts/run_atlas.py with 13E routes!')
