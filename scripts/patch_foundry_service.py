import sys

with open("src/marswalk/api/service.py", "r", encoding="utf-8") as f:
    content = f.read()

foundry_api_code = '''

# =============================================================================
# Milestone 13Z: Atlas Planetary Foundry API Endpoints
# =============================================================================

_CACHED_FOUNDRY_SCENARIO_ENGINE = None
_CACHED_FOUNDRY_GRAND_PRIX_RESULT = None


def planetary_foundry_overview_api() -> Dict[str, Any]:
    """Retrieve multi-settlement industrial foundry overview, inventory, and fleet status."""
    from marswalk.core.atlas_foundry_robotics import create_standard_industrial_fleet
    from marswalk.core.atlas_foundry_materials import SettlementMaterialInventory, MaterialCategory

    fleet = create_standard_industrial_fleet()
    settlements = ["SETTLEMENT-ALPHA", "OUTPOST-BETA", "OUTPOST-GAMMA"]
    inventories = {
        s: {
            "regolith_raw_kg": 150_000.0,
            "screened_fines_kg": 60_000.0,
            "sintered_pavers_kg": 45_000.0,
            "compacted_berm_kg": 80_000.0,
            "imported_structural_kg": 10_000.0,
            "fasteners_kg": 5_000.0,
        }
        for s in settlements
    }

    available_robots = sum(1 for r in fleet.values() if r.is_available)
    total_robots = len(fleet)

    return {
        "status": "SUCCESS",
        "settlements_count": len(settlements),
        "total_robots": total_robots,
        "available_robots": available_robots,
        "settlements": settlements,
        "inventories": inventories,
    }


def planetary_foundry_catalogue_api() -> Dict[str, Any]:
    """Retrieve catalogue of 12 unpressurized Martian infrastructure assets."""
    from marswalk.core.atlas_foundry_structures import INFRASTRUCTURE_CATALOGUE
    return {
        "status": "SUCCESS",
        "total_assets": len(INFRASTRUCTURE_CATALOGUE),
        "catalogue": [defn.to_dict() for defn in INFRASTRUCTURE_CATALOGUE.values()],
    }


def planetary_foundry_fleet_api() -> Dict[str, Any]:
    """Retrieve full 18-robot industrial fleet status and telemetry."""
    from marswalk.core.atlas_foundry_robotics import create_standard_industrial_fleet
    fleet = create_standard_industrial_fleet()
    return {
        "status": "SUCCESS",
        "total_fleet": len(fleet),
        "fleet": {aid: r.to_dict() for aid, r in fleet.items()},
    }


def planetary_foundry_materials_api() -> Dict[str, Any]:
    """Retrieve material specifications, densities, energy costs, and evidence citations."""
    from marswalk.core.atlas_foundry_materials import STANDARD_MATERIAL_SPECS
    return {
        "status": "SUCCESS",
        "total_materials": len(STANDARD_MATERIAL_SPECS),
        "materials": [spec.to_dict() for spec in STANDARD_MATERIAL_SPECS.values()],
    }


def planetary_foundry_scenarios_api() -> Dict[str, Any]:
    """List 12 canonical industrial construction campaigns."""
    from marswalk.core.atlas_foundry_scenario_engine import PlanetaryFoundryScenarioEngine
    engine = PlanetaryFoundryScenarioEngine()
    return {
        "status": "SUCCESS",
        "campaigns": engine.list_all_campaigns(),
    }


def planetary_foundry_scenario_run_api(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute a specific canonical planetary construction campaign."""
    from marswalk.core.atlas_foundry_scenario_engine import PlanetaryFoundryScenarioEngine
    from marswalk.core.atlas_foundry_scheduler import ConstructionStrategyType

    params = params or {}
    camp_id = str(params.get("campaign_id", "CAMPAIGN-01")).upper()
    strat_name = params.get("strategy")
    strat_type = None
    if strat_name:
        for st in ConstructionStrategyType:
            if st.value == strat_name or st.name == strat_name:
                strat_type = st
                break

    engine = PlanetaryFoundryScenarioEngine()
    res = engine.execute_campaign(camp_id, override_strategy=strat_type)
    return {
        "status": "SUCCESS",
        "result": res.to_dict(),
    }


def planetary_foundry_grand_prix_run_api(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute the 5-strategy Foundry Grand Prix competitive benchmark."""
    global _CACHED_FOUNDRY_GRAND_PRIX_RESULT
    from marswalk.core.atlas_foundry_grand_prix import FoundryGrandPrixTournament

    tourney = FoundryGrandPrixTournament()
    res = tourney.run_tournament()
    _CACHED_FOUNDRY_GRAND_PRIX_RESULT = res

    return {
        "status": "SUCCESS",
        "tournament": res.to_dict(),
    }
'''

if "planetary_foundry_overview_api()" not in content:
    content += foundry_api_code
    with open("src/marswalk/api/service.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Appended Foundry endpoints to service.py")
else:
    print("Foundry endpoints already present in service.py")
