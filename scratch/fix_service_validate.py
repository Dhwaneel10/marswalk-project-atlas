path = "src/marswalk/api/service.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

old_block = """from marswalk.core.mission_planning_benchmark import (
    MissionPlanningBenchmarkSuite,
)"""

new_block = """from marswalk.core.mission_planning_benchmark import (
    MissionPlanningBenchmarkSuite,
)
from marswalk.api.contracts import validate_contract"""

text = text.replace(old_block, new_block, 1)
text = text.replace("validate_payload(", "validate_contract(")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated service.py with validate_contract")
