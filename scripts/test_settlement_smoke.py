import marswalk.core.mars_settlement_site_selection as ss
import marswalk.core.mars_settlement_architecture as arch
import marswalk.core.mars_settlement_power as pwr
import marswalk.core.mars_isru_engine as isru
import marswalk.core.mars_settlement_consumables as cons
import marswalk.core.mars_habitat_model as hab
import marswalk.core.mars_settlement_construction as constr
import marswalk.core.mars_settlement_logistics as logist
import marswalk.core.mars_settlement_operations as ops
import marswalk.core.mars_settlement_resilience as res
import marswalk.core.mars_settlement_scenario_engine as scen
import marswalk.core.mars_settlement_replay as rep

print("All 12 settlement modules imported successfully!")
eng = scen.SettlementScenarioEngine()
print(f"Catalog scenarios count: {len(eng.get_catalog())}")
for cat in eng.get_catalog():
    r = eng.execute_scenario(cat["id"])
    print(f"Scenario {cat['id']}: {r.scenario_title} -> success={r.success}")
