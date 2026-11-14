with open("scripts/run_atlas.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add imports
target_import = "    deep_space_reset_simulation_api,\n"
aerial_imports = """    deep_space_reset_simulation_api,
    aerial_status_api,
    aerial_fleet_list_api,
    aerial_aircraft_create_api,
    aerial_performance_evaluate_api,
    aerial_mission_plan_api,
    aerial_rover_cooperation_plan_api,
    aerial_scenarios_list_api,
    aerial_scenario_run_api,
    aerial_observations_list_api,
    aerial_reset_api,
"""
if "aerial_status_api," not in content:
    content = content.replace(target_import, aerial_imports, 1)

# 2. Add GET routes
target_get = """            elif clean_path in ("/api/deep-space/scenarios", "/api/v1/deep-space/scenarios"):
                res = deep_space_scenarios_list_api()
                self.send_json_response(res, 200)
                return
"""
aerial_get_routes = """            elif clean_path in ("/api/deep-space/scenarios", "/api/v1/deep-space/scenarios"):
                res = deep_space_scenarios_list_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/aerial/status", "/api/v1/aerial/status"):
                res = aerial_status_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/aerial/fleet", "/api/v1/aerial/fleet"):
                res = aerial_fleet_list_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/aerial/scenarios", "/api/v1/aerial/scenarios"):
                res = aerial_scenarios_list_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/aerial/observations", "/api/v1/aerial/observations"):
                res = aerial_observations_list_api()
                self.send_json_response(res, 200)
                return
"""
if "aerial_status_api()" not in content:
    content = content.replace(target_get, aerial_get_routes, 1)

# 3. Add POST routes
target_post = """            elif clean_path in ("/api/deep-space/simulation/reset", "/api/v1/deep-space/simulation/reset"):
                result = deep_space_reset_simulation_api(payload)
                self.send_json_response(result, 200)
                return
"""
aerial_post_routes = """            elif clean_path in ("/api/deep-space/simulation/reset", "/api/v1/deep-space/simulation/reset"):
                result = deep_space_reset_simulation_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/aerial/fleet/create", "/api/v1/aerial/fleet/create"):
                result = aerial_aircraft_create_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/aerial/performance/evaluate", "/api/v1/aerial/performance/evaluate"):
                result = aerial_performance_evaluate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/aerial/mission/plan", "/api/v1/aerial/mission/plan"):
                result = aerial_mission_plan_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/aerial/rover-cooperation/plan", "/api/v1/aerial/rover-cooperation/plan"):
                result = aerial_rover_cooperation_plan_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/aerial/scenarios/run", "/api/v1/aerial/scenarios/run"):
                result = aerial_scenario_run_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/aerial/reset", "/api/v1/aerial/reset"):
                result = aerial_reset_api()
                self.send_json_response(result, 200)
                return
"""
if "aerial_aircraft_create_api(payload)" not in content:
    content = content.replace(target_post, aerial_post_routes, 1)

with open("scripts/run_atlas.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully patched scripts/run_atlas.py with Aerial Corps endpoints!")
