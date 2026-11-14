"""
Integrates Milestone 13F Resource Intelligence into src/marswalk/core/joint_mission_planner.py.
Preserves 100% backward compatibility for all existing 13E tests and endpoints.
"""
import re

with open("src/marswalk/core/joint_mission_planner.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add imports if not present
if "from marswalk.core.mission_resource_model import" not in content:
    import_block = """from marswalk.core.mission_resource_model import (
    RoverResourceConfig,
    RelayResourceConfig,
    MissionResourceLedger,
    ResourceFeasibilityClassification,
    evaluate_mission_resource_ledger,
    evaluate_resource_sensitivity,
    joules_to_wh,
)
"""
    pos = content.find("from marswalk.core.mission_connectivity import")
    # find end of that import statement
    end_pos = content.find(")", pos) + 1
    content = content[:end_pos] + "\n" + import_block + content[end_pos:]

# 2. Add resource fields to JointMissionInput
if "rover_resource_config: Optional[Dict[str, Any]] = None" not in content:
    target = "    max_route_candidates: int = 5\n"
    replacement = """    max_route_candidates: int = 5
    rover_resource_config: Optional[Dict[str, Any]] = None
    relay_resource_config: Optional[Dict[str, Any]] = None
    evaluate_resources: bool = True
"""
    content = content.replace(target, replacement, 1)

# 3. Add resource_summary to CandidateTraverse
if "resource_summary: Optional[Dict[str, Any]] = None" not in content:
    target = "    is_valid: bool = True\n"
    replacement = """    is_valid: bool = True
    resource_summary: Optional[Dict[str, Any]] = None
"""
    content = content.replace(target, replacement, 1)

    target_dict = '            "is_valid": self.is_valid,\n        }\n'
    replacement_dict = """            "is_valid": self.is_valid,
            "resource_summary": self.resource_summary,
        }
"""
    content = content.replace(target_dict, replacement_dict, 1)

# 4. Add resource metrics to JointMissionMetrics
if "energy_total_wh: float = 0.0" not in content:
    target = "    critical_bridges: int\n    normalized_vector: Dict[str, float] = field(default_factory=dict)\n"
    replacement = """    critical_bridges: int
    energy_total_wh: float = 0.0
    energy_drive_wh: float = 0.0
    energy_idle_wh: float = 0.0
    energy_comms_wh: float = 0.0
    energy_science_wh: float = 0.0
    final_soc_pct: float = 100.0
    min_soc_pct: float = 100.0
    resource_feasibility: str = "FEASIBLE_WITHIN_CONFIGURED_BUDGET"
    normalized_vector: Dict[str, float] = field(default_factory=dict)
"""
    content = content.replace(target, replacement, 1)

    target_dict = '            "normalized_vector": {k: round(v, 4) for k, v in self.normalized_vector.items()},\n'
    replacement_dict = """            "resource_metrics": {
                "total_energy_wh": round(self.energy_total_wh, 2),
                "drive_energy_wh": round(self.energy_drive_wh, 2),
                "idle_energy_wh": round(self.energy_idle_wh, 2),
                "comms_energy_wh": round(self.energy_comms_wh, 2),
                "science_energy_wh": round(self.energy_science_wh, 2),
                "final_soc_pct": round(self.final_soc_pct, 2),
                "min_soc_pct": round(self.min_soc_pct, 2),
                "feasibility": self.resource_feasibility,
            },
            "normalized_vector": {k: round(v, 4) for k, v in self.normalized_vector.items()},
"""
    content = content.replace(target_dict, replacement_dict, 1)

# 5. Add resource_ledger to JointMissionConfiguration
if "resource_ledger: Optional[Dict[str, Any]] = None" not in content:
    target = "    recommendation_tier: str = \"FEASIBLE_SUBOPTIMAL\"\n"
    replacement = """    recommendation_tier: str = "FEASIBLE_SUBOPTIMAL"
    resource_ledger: Optional[Dict[str, Any]] = None
"""
    content = content.replace(target, replacement, 1)

    target_dict = '            "recommendation_tier": self.recommendation_tier,\n        }\n'
    replacement_dict = """            "recommendation_tier": self.recommendation_tier,
            "resource_ledger": self.resource_ledger,
        }
"""
    content = content.replace(target_dict, replacement_dict, 1)

# 6. Add resource_sensitivity to JointMissionOptimizationResult
if "resource_sensitivity: Optional[Dict[str, Any]] = None" not in content:
    target = "    provenance: Dict[str, Any]\n"
    replacement = """    provenance: Dict[str, Any]
    resource_sensitivity: Optional[Dict[str, Any]] = None
"""
    content = content.replace(target, replacement, 1)

    target_dict = '            "provenance": self.provenance,\n        }\n'
    replacement_dict = """            "provenance": self.provenance,
            "resource_sensitivity": self.resource_sensitivity,
        }
"""
    content = content.replace(target_dict, replacement_dict, 1)

# 7. Update validate_joint_mission_input
if 'rover_resource_config = inp.get("rover_resource_config")' not in content:
    target = '        max_route_candidates=int(inp.get("max_route_candidates", 5)),\n    )'
    replacement = """        max_route_candidates=int(inp.get("max_route_candidates", 5)),
        rover_resource_config=inp.get("rover_resource_config"),
        relay_resource_config=inp.get("relay_resource_config"),
        evaluate_resources=bool(inp.get("evaluate_resources", True)),
    )"""
    content = content.replace(target, replacement, 1)

with open("src/marswalk/core/joint_mission_planner.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Integration step 1 complete.")
