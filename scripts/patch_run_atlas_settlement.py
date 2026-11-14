# Patch script to add settlement endpoints to run_atlas.py

with open('scripts/run_atlas.py', 'r', encoding='utf-8') as f:
    content = f.read()

import_target = """    resilience_reset_api,
    APIError,"""

import_replacement = """    resilience_reset_api,
    settlement_status_api,
    settlement_sites_api,
    settlement_architecture_api,
    settlement_power_simulate_api,
    settlement_isru_evaluate_api,
    settlement_consumables_api,
    settlement_habitat_thermal_api,
    settlement_construction_schedule_api,
    settlement_construction_step_api,
    settlement_logistics_trades_api,
    settlement_advance_simulation_api,
    settlement_readiness_review_api,
    settlement_scenarios_list_api,
    settlement_scenario_run_api,
    settlement_resilience_evaluate_api,
    settlement_replay_export_api,
    settlement_reset_api,
    APIError,"""

assert import_target in content, "import_target not found"
content = content.replace(import_target, import_replacement, 1)

# Now GET routes
get_target = """            elif clean_path in ("/api/resilience/benchmarks", "/api/v1/resilience/benchmarks"):
                res = resilience_benchmarks_api()
                self.send_json_response(res, 200)
                return"""

get_replacement = """            elif clean_path in ("/api/resilience/benchmarks", "/api/v1/resilience/benchmarks"):
                res = resilience_benchmarks_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/status", "/api/v1/settlement/status"):
                res = settlement_status_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/sites", "/api/v1/settlement/sites"):
                res = settlement_sites_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/architecture", "/api/v1/settlement/architecture"):
                res = settlement_architecture_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/construction/schedule", "/api/v1/settlement/construction/schedule"):
                res = settlement_construction_schedule_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/logistics/trades", "/api/v1/settlement/logistics/trades"):
                res = settlement_logistics_trades_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/readiness-review", "/api/v1/settlement/readiness-review"):
                res = settlement_readiness_review_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/scenarios", "/api/v1/settlement/scenarios"):
                res = settlement_scenarios_list_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/replay", "/api/v1/settlement/replay"):
                res = settlement_replay_export_api()
                self.send_json_response(res, 200)
                return"""

assert get_target in content, "get_target not found"
content = content.replace(get_target, get_replacement, 1)

# Now POST routes
post_target = """            elif clean_path in ("/api/resilience/reset", "/api/v1/resilience/reset"):
                result = resilience_reset_api()
                self.send_json_response(result, 200)
                return"""

post_replacement = """            elif clean_path in ("/api/resilience/reset", "/api/v1/resilience/reset"):
                result = resilience_reset_api()
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/advance", "/api/v1/settlement/advance"):
                result = settlement_advance_simulation_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/power/simulate", "/api/v1/settlement/power/simulate"):
                result = settlement_power_simulate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/isru/evaluate", "/api/v1/settlement/isru/evaluate"):
                result = settlement_isru_evaluate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/consumables", "/api/v1/settlement/consumables"):
                result = settlement_consumables_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/habitat/thermal", "/api/v1/settlement/habitat/thermal"):
                result = settlement_habitat_thermal_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/construction/step", "/api/v1/settlement/construction/step"):
                result = settlement_construction_step_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/scenarios/run", "/api/v1/settlement/scenarios/run"):
                result = settlement_scenario_run_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/resilience/evaluate", "/api/v1/settlement/resilience/evaluate"):
                result = settlement_resilience_evaluate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/reset", "/api/v1/settlement/reset"):
                result = settlement_reset_api()
                self.send_json_response(result, 200)
                return"""

assert post_target in content, "post_target not found"
content = content.replace(post_target, post_replacement, 1)

with open('scripts/run_atlas.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("run_atlas.py successfully patched with settlement endpoints!")
