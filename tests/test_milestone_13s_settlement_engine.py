"""MarsWalk 2.0 / Project Atlas — Milestone 13S Test Suite: Settlement Engine.

Comprehensive scientific verification of:
1. Multi-criteria site selection preserving NASA SWIM water-ice uncertainty.
2. 12-element Moon-to-Mars infrastructure architecture & causal dependency DAG.
3. Surface power modeling (Fission continuous baseload vs Solar PV dust degradation).
4. ISRU production chains with strict mass conservation (residual < 1e-4 kg).
5. Consumables accounting & unclosed recycling loops.
6. Habitat thermal network & sintered regolith vault radiation shielding.
7. Autonomous robotic construction with Milestone 13O stale-command rejection.
8. Logistics trade studies & synodic manifest planning.
9. Resilience fault injection & priority load shedding.
10. Phase F Hypothetical Crew-Arrival Readiness Review & mandatory disclaimers.
11. Full 10-scenario catalog deterministic execution.
12. Cryptographic SHA-256 state chain verification & tamper detection.
13. JSON Schema Draft 2020-12 API contract validation.
"""

from __future__ import annotations

import json
from typing import Any, Dict

import pytest

from marswalk.api.contracts import validate_contract
from marswalk.core.mars_isru_engine import ISRUEngine, ISRUProcessType
from marswalk.core.mars_habitat_model import (
    HabitatModuleType,
    HabitatThermalNetwork,
    ShieldingType,
)
from marswalk.core.mars_settlement_architecture import (
    InfrastructureDependencyDAG,
    NodeCommissioningState,
    SettlementArchetype,
    SettlementArchitecturePlanner,
)
from marswalk.core.mars_settlement_construction import (
    AutonomousConstructionDirector,
    ConstructionAssetType,
    OperationStatus,
)
from marswalk.core.mars_settlement_consumables import (
    CommodityType,
    SettlementConsumablesManager,
)
from marswalk.core.mars_settlement_logistics import (
    SettlementLogisticsPlanner,
)
from marswalk.core.mars_settlement_operations import (
    SettlementLifecycleState,
    SettlementOperationsDirector,
)
from marswalk.core.mars_settlement_power import (
    LoadPriority,
    PowerSourceType,
    SettlementPowerSystem,
)
from marswalk.core.mars_settlement_replay import (
    SettlementReplayRecorder,
)
from marswalk.core.mars_settlement_resilience import (
    SettlementFailureMode,
    SettlementResilienceEvaluator,
)
from marswalk.core.mars_settlement_scenario_engine import (
    SettlementScenarioEngine,
    SettlementScenarioID,
)
from marswalk.core.mars_settlement_site_selection import (
    SettlementSiteSelectionEngine,
    WaterEvidenceConfidence,
)


# -----------------------------------------------------------------------------
# 1. Site Selection & SWIM Uncertainty
# -----------------------------------------------------------------------------

def test_settlement_site_selection_multi_criteria():
    engine = SettlementSiteSelectionEngine()
    sites = engine.get_candidate_sites()
    assert len(sites) >= 5, "Expected at least 5 candidate Jezero settlement sites."

    site_ids = [s.site_id for s in sites]
    assert "SITE-DELTA-NORTH" in site_ids
    assert "SITE-CRATER-FLOOR" in site_ids
    assert "SITE-NERETVA-VALIS" in site_ids

    # Verify no single collapsed score; all criteria exposed
    delta = engine.get_site("SITE-DELTA-NORTH")
    assert delta is not None
    assert delta.terrain.mean_slope_deg < 5.0
    assert delta.environment.diurnal_temp_min_c < -50.0
    assert delta.environment.regional_dust_storm_risk in ["HIGH", "EXTREME", "MODERATE"]
    assert delta.resources.estimated_water_wt_pct > 5.0
    assert delta.operations.nuclear_safe_standoff_distance_m >= 1000.0


def test_settlement_site_selection_water_confidence():
    engine = SettlementSiteSelectionEngine()
    delta = engine.get_site("SITE-DELTA-NORTH")
    floor = engine.get_site("SITE-CRATER-FLOOR")

    # Preservation of NASA SWIM uncertainty: delta has resource candidate, floor is orbital indication
    assert delta.resources.water_evidence_level == WaterEvidenceConfidence.RESOURCE_CANDIDATE
    assert floor.resources.water_evidence_level == WaterEvidenceConfidence.ORBITAL_INDICATION
    assert delta.resources.water_estimate_uncertainty_pct < floor.resources.water_estimate_uncertainty_pct


# -----------------------------------------------------------------------------
# 2. Architecture & Causal Dependency DAG
# -----------------------------------------------------------------------------

def test_settlement_architecture_archetypes():
    planner = SettlementArchitecturePlanner()

    outpost = planner.create_settlement_plan(SettlementArchetype.SMALL_OUTPOST)
    assert outpost.population_capacity == 4
    assert outpost.total_power_capacity_kw == 55.0

    alpha = planner.create_settlement_plan(SettlementArchetype.MARS_BASE_ALPHA)
    assert alpha.population_capacity == 20
    assert alpha.total_power_capacity_kw >= 250.0
    assert len(alpha.dependency_dag.nodes) >= 10, "Mars Base Alpha must configure major Moon-to-Mars infrastructure nodes."


def test_settlement_architecture_dependency_dag():
    dag = SettlementArchitecturePlanner.build_standard_dependency_dag()
    crit_path = dag.get_critical_path()
    assert len(crit_path) > 0

    # Habitation depends on power distribution
    can_operate, reasons = dag.can_operate("NODE-HAB-STRUCT")
    assert isinstance(can_operate, bool)
    assert isinstance(reasons, list)


# -----------------------------------------------------------------------------
# 3. Surface Power Systems (Fission vs Solar & Dust Attenuation)
# -----------------------------------------------------------------------------

def test_settlement_surface_power_fission_baseload():
    fission = SettlementPowerSystem(system_type=PowerSourceType.NUCLEAR_FISSION, nameplate_capacity_kw=100.0)

    # Output remains 100 kW across noon and midnight, and during tau=3.0 dust storms
    tel_noon = fission.step_sol_time(sol=1, time_s=43200.0, dt_s=3600.0, atmospheric_tau=0.4)
    tel_midnight = fission.step_sol_time(sol=1, time_s=0.0, dt_s=3600.0, atmospheric_tau=0.4)
    tel_storm = fission.step_sol_time(sol=2, time_s=43200.0, dt_s=3600.0, atmospheric_tau=3.0)

    assert tel_noon.generation_gross_kw == pytest.approx(100.0, rel=1e-3)
    assert tel_midnight.generation_gross_kw == pytest.approx(100.0, rel=1e-3)
    assert tel_storm.generation_gross_kw == pytest.approx(100.0, rel=1e-3)


def test_settlement_surface_power_solar_dust_storm():
    solar = SettlementPowerSystem(system_type=PowerSourceType.SOLAR_PV, nameplate_capacity_kw=150.0, battery_capacity_kwh=600.0)

    tel_clear = solar.step_sol_time(sol=1, time_s=43200.0, dt_s=3600.0, atmospheric_tau=0.45)
    tel_storm = solar.step_sol_time(sol=1, time_s=43200.0, dt_s=3600.0, atmospheric_tau=2.85)

    assert tel_clear.generation_gross_kw > 100.0
    assert tel_storm.generation_gross_kw < 35.0, "Severe dust storm must attenuate solar PV generation by > 65%."


def test_settlement_power_priority_load_shedding():
    power = SettlementPowerSystem(system_type=PowerSourceType.NUCLEAR_FISSION, nameplate_capacity_kw=100.0)
    power.set_generator_status(0.20)  # Drop generation to 20 kW
    power.current_battery_kwh = 0.0   # Deplete battery to trigger immediate load shedding

    tel = power.step_sol_time(sol=1, time_s=43200.0, dt_s=3600.0)
    assert len(tel.active_shed_loads) > 0

    # Non-essential loads shed first; critical life support preserved
    assert any("Water" in name or "Robots" in name for name in tel.active_shed_loads)
    assert not any("Critical Life Support" in name for name in tel.active_shed_loads)


# -----------------------------------------------------------------------------
# 4. ISRU Production Chains & Mass Conservation
# -----------------------------------------------------------------------------

def test_isru_water_extraction_mass_conservation():
    isru = ISRUEngine()
    audit = isru.extract_water_from_regolith(excavated_feedstock_kg=1200.0, water_wt_pct=7.2)

    assert audit.is_conserved, f"Mass conservation violated! Residual: {audit.imbalance_residual_kg}"
    assert abs(audit.imbalance_residual_kg) < 1e-4
    assert audit.total_inputs_kg == 1200.0
    assert audit.total_products_kg > 50.0
    assert audit.energy_consumed_kwh > 0.0


def test_isru_atmospheric_oxygen_mass_conservation():
    isru = ISRUEngine()
    audit = isru.generate_atmospheric_oxygen(co2_intake_kg=400.0)

    assert audit.is_conserved, f"Mass conservation violated! Residual: {audit.imbalance_residual_kg}"
    assert abs(audit.imbalance_residual_kg) < 1e-4
    assert audit.total_inputs_kg == 400.0
    assert audit.total_products_kg > 40.0


def test_isru_sabatier_methane_mass_conservation():
    isru = ISRUEngine()
    audit = isru.synthesize_sabatier_methane(co2_input_kg=176.0, h2_input_kg=32.0)

    assert audit.is_conserved, f"Mass conservation violated! Residual: {audit.imbalance_residual_kg}"
    assert abs(audit.imbalance_residual_kg) < 1e-4
    assert audit.total_inputs_kg == 208.0
    assert isru.inventories.liquid_methane_ch4_kg > 0.0


def test_isru_regolith_sintering():
    isru = ISRUEngine()
    audit = isru.sinter_regolith_blocks(raw_regolith_kg=2500.0)

    assert audit.is_conserved
    assert abs(audit.imbalance_residual_kg) < 1e-4
    assert isru.inventories.sintered_regolith_blocks_kg >= 2100.0


# -----------------------------------------------------------------------------
# 5. Consumables & Recycling Loops
# -----------------------------------------------------------------------------

def test_settlement_consumables_closed_water_loop():
    mgr = SettlementConsumablesManager(population=4)
    # Simulate 1 sol without local production
    res1 = mgr.simulate_sol(sol_duration_days=1.0)
    consumed_h2o = res1["water"].consumed
    produced_h2o = res1["water"].produced_locally  # recycled wastewater
    assert produced_h2o > 0.85 * consumed_h2o, "Water recycling loop should recover ~92% of wastewater."

    # Water stock decreases by only the makeup deficit (8%)
    expected_burn = consumed_h2o - produced_h2o
    assert res1["water"].initial_inventory - res1["water"].final_inventory == pytest.approx(expected_burn, abs=0.1)


def test_settlement_consumables_oxygen_recovery():
    mgr = SettlementConsumablesManager(population=6)
    res = mgr.simulate_sol(sol_duration_days=1.0)
    assert res["oxygen"].days_of_reserve_remaining > 50.0
    assert not res["oxygen"].is_shortfall


# -----------------------------------------------------------------------------
# 6. Habitat Thermal Network & Sintered Regolith Shielding
# -----------------------------------------------------------------------------

def test_habitat_thermal_energy_balance():
    net = HabitatThermalNetwork()
    telemetry = net.evaluate_thermal_step(ambient_temp_c=-75.0, solar_flux_wm2=300.0, dt_s=3600.0)

    assert len(telemetry) == 3
    for t in telemetry:
        assert t.internal_temp_c > 15.0, "Active HVAC should maintain internal hab temperatures > 15C."
        assert t.q_conduction_loss_kw > 0.0
        assert t.q_active_heating_required_kw >= 0.0


def test_habitat_sintered_vault_radiation_shielding():
    net = HabitatThermalNetwork()
    crew_mod = net.modules["HAB-CREW-01"]
    lab_mod = net.modules["HAB-LAB-01"]

    assert crew_mod.shielding == ShieldingType.REGOLITH_BERM_1M
    assert lab_mod.shielding == ShieldingType.SINTERED_ARCH_2M


# -----------------------------------------------------------------------------
# 7. Autonomous Construction Fleet & Stale-Command Guarding
# -----------------------------------------------------------------------------

def test_construction_stale_command_rejection():
    director = AutonomousConstructionDirector()
    sched = director.evaluate_schedule(current_sol=1)

    # Find an uncompleted operation
    all_ops = director.get_operations()
    uncompleted = [o for o in all_ops if o.status != OperationStatus.COMPLETED]
    target_op = uncompleted[0].op_id

    # Dispatch command with 1800s delay (> 1200s limit)
    res = director.execute_operation_step(
        op_id=target_op,
        execution_timestamp_s=2000.0,
        command_dispatch_timestamp_s=100.0,
    )
    assert res["status"] == "REJECTED_STALE"
    assert "exceeded safety window" in res["reason"]


def test_construction_schedule_progression():
    director = AutonomousConstructionDirector()
    sched = director.evaluate_schedule(current_sol=1)
    assert sched["total_operations"] == 15
    assert sched["completed_count"] >= 1  # OP-01 pre-completed in recon


# -----------------------------------------------------------------------------
# 8. Logistics Trade Studies
# -----------------------------------------------------------------------------

def test_settlement_logistics_trade_studies():
    planner = SettlementLogisticsPlanner()
    trades = planner.evaluate_trade_studies()
    assert len(trades) == 4

    monolithic = trades[0]
    isru_max = trades[2]
    assert monolithic.total_imported_mass_kg > isru_max.total_imported_mass_kg
    assert isru_max.mass_leverage_ratio > monolithic.mass_leverage_ratio


# -----------------------------------------------------------------------------
# 9. Resilience Fault Injection
# -----------------------------------------------------------------------------

def test_settlement_resilience_compound_failure():
    director = SettlementOperationsDirector(archetype=SettlementArchetype.MARS_BASE_ALPHA)
    assessment = SettlementResilienceEvaluator.inject_settlement_failure(
        director=director,
        failure_mode=SettlementFailureMode.COMPOUND_INFRASTRUCTURE_APOCALYPSE,
    )

    assert not assessment.is_survival_compromised
    assert assessment.settlement_state_after == "RECOVERY"
    assert len(assessment.shed_loads) > 0


# -----------------------------------------------------------------------------
# 10. Phase F Hypothetical Crew-Arrival Readiness Review
# -----------------------------------------------------------------------------

def test_phase_f_crew_readiness_review():
    director = SettlementOperationsDirector(archetype=SettlementArchetype.MARS_BASE_ALPHA)

    # Initial review has unmet gaps
    early_review = director.evaluate_crew_readiness_review()
    assert not early_review.is_ready_for_simulation_arrival
    assert len(early_review.unmet_gaps) > 0
    assert "MANDATORY DISCLOSURE" in early_review.mandatory_safety_disclaimer

    # Stockpile and complete construction
    for op in director.construction_director.get_operations():
        op.status = OperationStatus.COMPLETED
    director.consumables_manager.water_stock_kg = 20000.0
    director.consumables_manager.oxygen_stock_kg = 10000.0
    director.consumables_manager.food_rations_kg = 15000.0

    ready_review = director.evaluate_crew_readiness_review()
    assert ready_review.is_ready_for_simulation_arrival
    assert ready_review.readiness_score_pct >= 90.0


# -----------------------------------------------------------------------------
# 11. Full 10-Scenario Catalog Execution
# -----------------------------------------------------------------------------

def test_settlement_10_deterministic_scenarios():
    engine = SettlementScenarioEngine()
    catalog = engine.get_catalog()
    assert len(catalog) == 10

    for item in catalog:
        scen_id = item["id"]
        res = engine.execute_scenario(scen_id)
        assert res.success, f"Scenario '{scen_id}' failed: {res.summary}"
        assert len(res.timeline_events) > 0
        assert len(res.disclaimers) > 0


# -----------------------------------------------------------------------------
# 12. Cryptographic Replay & SHA-256 State Chain Integrity
# -----------------------------------------------------------------------------

def test_settlement_replay_cryptographic_sha256():
    recorder = SettlementReplayRecorder()

    s1 = recorder.record_step(sol=1, timestamp_s=100.0, state_payload={"power_kw": 250.0})
    s2 = recorder.record_step(sol=2, timestamp_s=200.0, state_payload={"power_kw": 245.0})
    s3 = recorder.record_step(sol=3, timestamp_s=300.0, state_payload={"power_kw": 240.0})

    audit = recorder.verify_chain_integrity()
    assert audit.is_valid
    assert audit.total_snapshots == 3
    assert len(audit.final_state_hash) == 64

    # Adversarial tampering test: mutate recorded payload
    s2.state_payload["power_kw"] = 999.0
    tampered_audit = recorder.verify_chain_integrity()
    assert not tampered_audit.is_valid
    assert len(tampered_audit.mismatches) > 0


# -----------------------------------------------------------------------------
# 13. API Schema Contract Validation (Draft 2020-12)
# -----------------------------------------------------------------------------

def test_settlement_api_schema_contract():
    from marswalk.api.service import settlement_status_api

    payload = settlement_status_api()
    is_valid, errors = validate_contract(payload, "settlement-engine")
    assert is_valid, f"Contract validation failed against settlement-engine.schema.json: {errors}"
    assert payload["status"] in ["NOMINAL", "CONSTRUCTION", "COMMISSIONING", "OPERATIONAL_SIMULATION", "DEGRADED", "RECOVERY"]
    assert "MANDATORY SCIENTIFIC DISCLOSURE" in payload["mandatory_scientific_disclosure"]
