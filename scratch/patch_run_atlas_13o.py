import re

PATH = r"E:\Python\NASA-Spaceapps\Marswalk\scripts\run_atlas.py"

with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()

target = '            elif clean_path in ("/api/environment-validation/evaluate", "/api/v1/environment-validation/evaluate"):\n                result = environment_validation_evaluate_api(payload)\n                self.send_json_response(result, 200)\n                return\n'

# Try CRLF as well
target_crlf = target.replace("\n", "\r\n")

addition = """            elif clean_path in ("/api/deep-space/scenarios/run", "/api/v1/deep-space/scenarios/run"):
                result = deep_space_scenario_run_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/deep-space/commands/create", "/api/v1/deep-space/commands/create"):
                result = deep_space_command_create_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/deep-space/commands/transmit", "/api/v1/deep-space/commands/transmit"):
                result = deep_space_command_transmit_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/deep-space/simulation/advance", "/api/v1/deep-space/simulation/advance"):
                result = deep_space_simulation_advance_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/deep-space/simulation/inject-hazard", "/api/v1/deep-space/simulation/inject-hazard"):
                result = deep_space_inject_hazard_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/deep-space/simulation/reset", "/api/v1/deep-space/simulation/reset"):
                result = deep_space_reset_simulation_api(payload)
                self.send_json_response(result, 200)
                return
"""

if target in content:
    content = content.replace(target, target + addition, 1)
    print("Replaced with LF")
elif target_crlf in content:
    addition_crlf = addition.replace("\n", "\r\n")
    content = content.replace(target_crlf, target_crlf + addition_crlf, 1)
    print("Replaced with CRLF")
else:
    print("Could not find target!")

with open(PATH, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated run_atlas.py successfully.")
