# scratch/test_engines_smoke.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from marswalk.core.campaign_operations_director import CampaignOperationsDirector
from marswalk.core.mission_assurance_engine import MissionAssuranceEngine, AssuranceVerdict
from marswalk.core.campaign_replay_engine import CampaignReplayEngine
from marswalk.core.campaign_branch_manager import CampaignBranchManager
from marswalk.core.campaign_counterfactual_engine import CampaignCounterfactualEngine, CounterfactualScenarioDefinition, ScenarioType, ScenarioCategory
from marswalk.core.campaign_robustness_engine import CampaignRobustnessEngine

from marswalk.core.mission_campaign import CampaignConfig, CampaignTarget
from marswalk.core.terrain import load_and_process_terrain

print("Testing smoke initialization of all 5 engines...")
base_dir = Path(__file__).resolve().parent.parent
tiff_path = base_dir / "data" / "processed" / "jezero_ready_20m.tif"
terrain = load_and_process_terrain(str(tiff_path))

sample_targets = [
    CampaignTarget(
        id="tgt_octavia",
        name="Octavia E. Butler Landing",
        row=117,
        col=157,
        priority_score=100.0,
        dwell_time_s=900.0,
        science_objective="SURFACE_MORPHOLOGY",
    ),
    CampaignTarget(
        id="tgt_delta_front",
        name="Kodiak Mesa Delta Front",
        row=122,
        col=148,
        priority_score=90.0,
        dwell_time_s=1800.0,
        science_objective="GEOLOGICAL_CHARACTERIZATION",
    ),
]

director = CampaignOperationsDirector("cmp_smoke", "Smoke Test Campaign", terrain_grid=terrain)
director.plan_multi_sol_campaign(
    targets=sample_targets,
    config=CampaignConfig(max_sols=3)
)

# 1. Assurance Engine
assurance_engine = MissionAssuranceEngine()
report = assurance_engine.evaluate_campaign(director.get_campaign_operations_state())
print(f"Assurance Report: verdict={report.overall_verdict}, rules={len(report.rule_results)}, violations={len(report.violations)}")
assert report.overall_verdict in (AssuranceVerdict.PASS, AssuranceVerdict.UNKNOWN)

# 2. Replay Engine
replay_engine = CampaignReplayEngine()
replayed_state, timeline = replay_engine.replay_campaign(director, director.events_log)
integ = replay_engine.verify_replay_integrity(replayed_state, director.get_campaign_operations_state())
print(f"Replay Integrity: exact_match={integ.is_exact_match}, matching={len(integ.matching_fields)}, divergent={len(integ.divergent_fields)}")
assert integ.is_exact_match

# 3. Branch Manager
branch_mgr = CampaignBranchManager()
br = branch_mgr.create_branch(director, "br_smoke_01", "Smoke Branch 1", fork_sol=2)
print(f"Branch created: id={br.branch_id}, status={br.branch_status}, parent_fp={br.parent_state_fingerprint[:12]}")
assert br.branch_id == "br_smoke_01"

# Mutate branch and assert parent is NOT mutated
br.director.current_energy_wh -= 500.0
assert director.current_energy_wh == 4800.0, "Parent director was mutated by child branch!"
print("Parent isolation verified: director.current_energy_wh is intact at 4800.0 Wh")

# 4. Counterfactual Engine
cf_engine = CampaignCounterfactualEngine(branch_manager=branch_mgr, assurance_engine=assurance_engine)
sc = CounterfactualScenarioDefinition(
    scenario_id="sc_test_relay",
    scenario_type=ScenarioType.R1_RELAY_OUTAGE,
    category=ScenarioCategory.COMMUNICATIONS,
    name="Relay Drop",
    description="Drop MRN-01",
    target_sol=2,
    parameters={"relay_id": "MRN-01"},
)
cf_res = cf_engine.run_counterfactual_scenario(director, sc)
print(f"Counterfactual result: type={cf_res.scenario_type}, alts={len(cf_res.recovery_alternatives)}, rec={cf_res.recommended_alternative_id}")
assert len(cf_res.recovery_alternatives) >= 1

# 5. Robustness Engine
rob_engine = CampaignRobustnessEngine(branch_manager=branch_mgr, counterfactual_engine=cf_engine, assurance_engine=assurance_engine)
rob_rep = rob_engine.evaluate_campaign_robustness(director, max_scenarios=3)
print(f"Robustness Report: score={rob_rep.robustness_score_pct}%, envelope={len(rob_rep.feasibility_envelope)}, duration={rob_rep.execution_duration_s:.3f}s")
assert rob_rep.robustness_score_pct > 0.0

dossier = rob_engine.generate_mission_assurance_dossier(director, robustness_report=rob_rep)
print(f"Dossier generated: id={dossier['dossier_id']}, root_digest={dossier['root_digest'][:12]}")
assert "README.md" in dossier["manifest_files"]

from marswalk.api.contracts import get_validator, validate_contract
for k in ["mission-assurance", "campaign-branch", "counterfactual-scenario", "campaign-robustness"]:
    get_validator(k)

is_valid, errors = validate_contract(report.to_dict(), "mission-assurance")
if not is_valid:
    print(f"mission-assurance validation errors: {errors}")
assert is_valid, "mission-assurance contract validation failed!"
print("mission-assurance contract validation PASSED!")

validate_contract(br.to_dict(), "campaign-branch", raise_on_error=True)
print("campaign-branch contract validation PASSED!")

validate_contract(cf_res.to_dict(), "counterfactual-scenario", raise_on_error=True)
print("counterfactual-scenario contract validation PASSED!")

validate_contract(rob_rep.to_dict(), "campaign-robustness", raise_on_error=True)
print("campaign-robustness contract validation PASSED!")

print("All 4 Draft 2020-12 schemas loaded, compiled, and contract-validated successfully!")

print("SMOKE TEST 100% SUCCESSFUL!")
