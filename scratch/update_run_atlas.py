"""
Updates scripts/run_atlas.py to route resource evaluation and sensitivity APIs.
"""

with open("scripts/run_atlas.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update imports
old_import = "    joint_mission_promote_api,\n"
new_import = """    joint_mission_promote_api,
    joint_mission_resource_evaluate_api,
    joint_mission_resource_sensitivity_api,
"""

if "joint_mission_resource_evaluate_api," not in code:
    assert old_import in code, "Failed to find old_import"
    code = code.replace(old_import, new_import, 1)

# 2. Add route in do_POST
old_route = """            elif clean_path == "/api/joint-mission/promote":
                result = joint_mission_promote_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return"""

new_route = """            elif clean_path == "/api/joint-mission/promote":
                result = joint_mission_promote_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/joint-mission/resource-evaluate", "/api/resource/evaluate"):
                result = joint_mission_resource_evaluate_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/joint-mission/resource-sensitivity", "/api/resource/sensitivity"):
                result = joint_mission_resource_sensitivity_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return"""

if "/api/joint-mission/resource-evaluate" not in code:
    assert old_route in code, "Failed to find old_route"
    code = code.replace(old_route, new_route, 1)

with open("scripts/run_atlas.py", "w", encoding="utf-8") as f:
    f.write(code)

print("run_atlas.py routes updated.")
