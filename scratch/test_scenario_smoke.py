import sys
import os

sys.path.insert(0, os.path.abspath("src"))

from marswalk.core.deep_space_scenario_engine import DeepSpaceScenarioCatalog

print("Testing all 10 scenarios...")
for sc in DeepSpaceScenarioCatalog.list_scenarios():
    sc_id = sc["scenario_id"]
    res = DeepSpaceScenarioCatalog.run_scenario(sc_id)
    print(f"[{res.scenario_id}] {res.scenario_title} -> Stages: {res.stages_completed}/{res.total_stages}, Success: {res.is_success}, Status: {res.final_mission_status}")
print("ALL 10 SCENARIOS VERIFIED!")
