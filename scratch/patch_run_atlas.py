import os

path = "scripts/run_atlas.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Patch imports
old_import = "    fleet_assurance_api,\n    APIError,"
new_import = """    fleet_assurance_api,
    mission_intent_sample_api,
    mission_intent_validate_api,
    mission_intent_normalize_api,
    mission_plan_compile_api,
    mission_plan_evaluate_api,
    mission_plan_compare_api,
    mission_plan_get_api,
    mission_plan_debugger_api,
    mission_plan_benchmark_api,
    mission_plan_promote_api,
    APIError,"""

if old_import not in content:
    # try CRLF
    old_import = "    fleet_assurance_api,\r\n    APIError,"
    new_import = """    fleet_assurance_api,\r\n    mission_intent_sample_api,\r\n    mission_intent_validate_api,\r\n    mission_intent_normalize_api,\r\n    mission_plan_compile_api,\r\n    mission_plan_evaluate_api,\r\n    mission_plan_compare_api,\r\n    mission_plan_get_api,\r\n    mission_plan_debugger_api,\r\n    mission_plan_benchmark_api,\r\n    mission_plan_promote_api,\r\n    APIError,"""

assert old_import in content, "old_import not found"
content = content.replace(old_import, new_import, 1)

# 2. Patch do_GET
old_get = "            elif clean_path == \"/api/fleet/assurance\" or clean_path.endswith(\"/assurance\"):\n                res = fleet_assurance_api({}, self.terrain)\n                self.send_json_response(res, 200)\n                return"
if old_get not in content:
    old_get = "            elif clean_path == \"/api/fleet/assurance\" or clean_path.endswith(\"/assurance\"):\r\n                res = fleet_assurance_api({}, self.terrain)\r\n                self.send_json_response(res, 200)\r\n                return"

assert old_get in content, "old_get not found"

new_get = old_get + """
            elif clean_path in ("/api/compiler/sample-intent", "/api/v1/compiler/sample-intent"):
                res = mission_intent_sample_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/compiler/benchmark", "/api/v1/compiler/benchmark"):
                res = mission_plan_benchmark_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/compiler/plan", "/api/v1/compiler/plan"):
                res = mission_plan_get_api(query_params, self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/compiler/debugger", "/api/v1/compiler/debugger"):
                res = mission_plan_debugger_api({}, self.terrain)
                self.send_json_response(res, 200)
                return"""

content = content.replace(old_get, new_get, 1)

# 3. Patch do_POST
old_post = "            elif clean_path == \"/api/fleet/promote\":\n                result = fleet_promote_api(payload, self.terrain)\n                self.send_json_response(result, 200)\n                return"
if old_post not in content:
    old_post = "            elif clean_path == \"/api/fleet/promote\":\r\n                result = fleet_promote_api(payload, self.terrain)\r\n                self.send_json_response(result, 200)\r\n                return"

assert old_post in content, "old_post not found"

new_post = old_post + """
            elif clean_path in ("/api/compiler/validate", "/api/v1/compiler/validate"):
                result = mission_intent_validate_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/compiler/normalize", "/api/v1/compiler/normalize"):
                result = mission_intent_normalize_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/compiler/compile", "/api/v1/compiler/compile"):
                result = mission_plan_compile_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/compiler/evaluate", "/api/v1/compiler/evaluate"):
                result = mission_plan_evaluate_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/compiler/compare", "/api/v1/compiler/compare"):
                result = mission_plan_compare_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/compiler/debug", "/api/v1/compiler/debug"):
                result = mission_plan_debugger_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/compiler/promote", "/api/v1/compiler/promote"):
                result = mission_plan_promote_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return"""

content = content.replace(old_post, new_post, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully patched scripts/run_atlas.py!")
