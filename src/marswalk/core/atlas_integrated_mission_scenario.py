"""Project Atlas / MarsWalk 2.0 — Milestone 13T
Atlas Integrated Mission Scenario — Flagship 12-Phase Demonstration.

Executes the signature mission:
  MISSION ID: ATLAS-MARS-BASE-ALPHA-001
  OBJECTIVE: "Establish a robotic research settlement in Jezero, investigate
  scientifically valuable geological regions, deploy supporting infrastructure
  and prepare a hypothetical long-duration expedition."

Spans 12 deterministic execution phases across 60 Martian Sols.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from .atlas_mission_contracts import (
    CommandPacket,
    CommandState,
    MissionDossier,
    MissionObjective,
    MissionStatus,
    ObservationRecord,
    ResilienceResponse,
    ResourceBalanceLedger,
)
from .atlas_mission_execution_core import AtlasMissionExecutionCore


class IntegratedMissionScenarioRunner:
    """Executes the complete 12-phase flagship demonstration mission."""

    @staticmethod
    def run_flagship_mission() -> Tuple[AtlasMissionExecutionCore, MissionDossier, Dict[str, Any]]:
        """Run all 12 operational phases of ATLAS-MARS-BASE-ALPHA-001."""
        phase_results: Dict[str, Any] = {}

        # -------------------------------------------------------------
        # Phase 01: High-Level Objective Ingestion & Mission Compilation
        # -------------------------------------------------------------
        obj = MissionObjective(
            objective_id="OBJ-ATLAS-ALPHA-001",
            title="Establish Autonomous Research Settlement in Jezero Crater",
            raw_intent=(
                "Establish a robotic research settlement in Jezero, investigate "
                "scientifically valuable geological regions, deploy supporting infrastructure "
                "and prepare a hypothetical long-duration expedition."
            ),
            target_site_id="SITE-JEZERO-DELTA-01",
            target_region="Jezero Crater Western Delta Outwash",
            duration_sols=60,
            success_criteria=[
                "Deploy 120 kWe fission reactor and secondary solar grid",
                "Assemble and pressurize primary habitat core to 101.3 kPa",
                "Sinter 240+ regolith protection blocks via microwave ISRU",
                "Execute distributed science sorties to Delta Scarp and Séítah",
                "Demonstrate asynchronous autonomy and resilience under 14.2 min comm delay",
                "Achieve 100% Phase F readiness qualification",
            ],
        )
        core = AtlasMissionExecutionCore(mission_id="ATLAS-MARS-BASE-ALPHA-001", objective=obj)
        phase_results["phase_01_compilation"] = {
            "mission_id": core.mission_id,
            "compiled_phases_count": len(core.phases),
            "total_tasks_count": sum(len(p.tasks) for p in core.phases),
            "status": core.status.value,
        }

        # -------------------------------------------------------------
        # Phase 02: Settlement Site Selection & Scientific Grounding (Sols 1-4)
        # -------------------------------------------------------------
        for _ in range(4):
            core.advance_sol()
        core.asset_mgr.update_asset_location("ATLAS-ROVER-01", 18.4448, 77.4510, -2530.0, distance_delta_m=840.0)
        phase_results["phase_02_site_selection"] = {
            "site_id": "SITE-JEZERO-DELTA-01",
            "candidate_score": 94.2,
            "max_slope_deg": 4.2,
            "bearing_capacity_kpa": 185.0,
            "current_sol": core.event_coord.current_sol,
        }

        # -------------------------------------------------------------
        # Phase 03: Infrastructure & Power Architecture Sizing (Sols 5-8)
        # -------------------------------------------------------------
        for _ in range(4):
            core.advance_sol()
        phase_results["phase_03_power_architecture"] = {
            "fission_reactor_rated_kwe": core.resource_ops.reactor_rated_kwe,
            "battery_storage_kwh": core.resource_ops.battery_capacity_kwh,
            "battery_soc_pct": core.resource_ops.battery_soc_pct,
            "current_sol": core.event_coord.current_sol,
        }

        # -------------------------------------------------------------
        # Phase 04: Resource Logistics & Fleet Allocation (Sols 9-16)
        # -------------------------------------------------------------
        for _ in range(8):
            core.advance_sol()
        phase_results["phase_04_fleet_allocation"] = {
            "assets_registered": len(core.asset_mgr.list_assets()),
            "construction_bot_status": core.asset_mgr.get_asset("CONSTRUCTION-BOT-01").health.value,
            "current_sol": core.event_coord.current_sol,
        }

        # -------------------------------------------------------------
        # Phase 05: Science Campaign & Discovery Planning (Sols 17-24)
        # -------------------------------------------------------------
        for _ in range(8):
            core.advance_sol()
        phase_results["phase_05_science_planning"] = {
            "hypotheses_scheduled": len(core.science_ops.investigations),
            "target_features": [h.target_feature for h in core.science_ops.investigations.values()],
            "current_sol": core.event_coord.current_sol,
        }

        # -------------------------------------------------------------
        # Phase 06: Autonomous Campaign Deployment (Sols 25-36)
        # -------------------------------------------------------------
        for _ in range(12):
            core.advance_sol()
        phase_results["phase_06_deployment"] = {
            "habitat_pressurized_kpa": core.state_mgr.physical.habitat_core_pressure_kpa,
            "habitat_temp_k": core.state_mgr.physical.habitat_core_temp_k,
            "current_sol": core.event_coord.current_sol,
        }

        # -------------------------------------------------------------
        # Phase 07: Earth-Mars Communication Delay & Asynchronous Loop (Sols 37-40)
        # -------------------------------------------------------------
        # Dispatch command with current valid state hash
        cmd_valid = core.dispatch_earth_command(
            target_asset_id="ATLAS-ROVER-01",
            action="EXECUTE_DELTA_SCARP_TRAVERSE",
            parameters={"target_lat": 18.4520, "target_lon": 77.4350},
        )
        # Dispatch command with intentional obsolete/stale state hash
        cmd_stale = core.autonomy_ops.queue_earth_command(
            command_id="CMD-STALE-TEST-001",
            target_asset_id="HEXACOPTER-SURVEYOR-02",
            action="EXECUTE_HIGH_RISK_FLIGHT",
            parameters={"altitude_m": 45.0},
            expected_state_hash="a1b2c3d4e5f60000000000000000000000000000000000000000000000000000",
            created_met_seconds=core.event_coord.current_met_seconds,
            dispatch_sol=core.event_coord.current_sol,
        )

        for _ in range(4):
            core.advance_sol()

        phase_results["phase_07_autonomy_loop"] = {
            "owlt_seconds": core.autonomy_ops.owlt_seconds,
            "owlt_minutes": round(core.autonomy_ops.owlt_seconds / 60.0, 2),
            "valid_cmd_state": cmd_valid.state.value,
            "stale_cmd_state": cmd_stale.state.value,
            "stale_rejection_verified": (cmd_stale.state == CommandState.REJECTED_STALE_HASH),
            "current_sol": core.event_coord.current_sol,
        }

        # -------------------------------------------------------------
        # Phase 08: Scientific Discovery & Bayesian Updates (Sols 41-46)
        # -------------------------------------------------------------
        obs1 = core.science_ops.ingest_observation(
            observation_id="OBS-JEZERO-DELTA-001",
            source_asset_id="ATLAS-ROVER-01",
            sol=41,
            sol_time="11:30:00",
            location={"lat": 18.4520, "lon": 77.4350, "elevation_m": -2515.0},
            instrument_type="PIXL_XRF_SPECTROMETER",
            modality="ELEMENTAL_GEOCHEMISTRY",
            data={"fe_mg_phyllosilicates_pct": 28.4, "carbonate_veins": True, "sio2_pct": 46.2},
            uncertainty={"fe_mg_pct": 0.4, "sio2_pct": 0.8},
        )
        core.science_ops.update_hypothesis_evidence(
            hypothesis_id="HYP-JEZERO-01",
            observation_id="OBS-JEZERO-DELTA-001",
            likelihood_ratio=8.5,
        )

        obs2 = core.science_ops.ingest_observation(
            observation_id="OBS-JEZERO-SEITAH-002",
            source_asset_id="HEXACOPTER-SURVEYOR-02",
            sol=43,
            sol_time="13:15:00",
            location={"lat": 18.4380, "lon": 77.4420, "elevation_m": -2545.0},
            instrument_type="MULTISPECTRAL_IMAGER",
            modality="MINERALOGICAL_REFLECTANCE",
            data={"olivine_absorption_band_nm": 1050.0, "grain_size_mm": 2.5, "cumulate_texture": True},
            uncertainty={"band_nm": 5.0},
        )
        core.science_ops.update_hypothesis_evidence(
            hypothesis_id="HYP-JEZERO-02",
            observation_id="OBS-JEZERO-SEITAH-002",
            likelihood_ratio=7.2,
        )

        for _ in range(6):
            core.advance_sol()

        sci_summary = core.science_ops.get_summary_metrics()
        phase_results["phase_08_discovery"] = {
            "hypotheses_validated_count": sci_summary["validated_hypotheses_count"],
            "cumulative_information_gain_bits": sci_summary["cumulative_information_gain_bits"],
            "delta_posterior": core.science_ops.investigations["HYP-JEZERO-01"].posterior_probability,
            "seitah_posterior": core.science_ops.investigations["HYP-JEZERO-02"].posterior_probability,
            "current_sol": core.event_coord.current_sol,
        }

        # -------------------------------------------------------------
        # Phase 09: Cascading Failure Injection & Recovery (Sols 47-50)
        # -------------------------------------------------------------
        incident = core.resilience_ops.inject_failure(
            incident_id="INCIDENT-SOL-48-DUST-STORM",
            subsystem="ATMOSPHERIC_ENVIRONMENT",
            failure_mode="REGIONAL_CONVECTIVE_DUST_STORM",
            root_cause="Local saltation threshold exceeded; atmospheric optical depth tau surged from 0.45 to 2.80",
            sol=48,
            severity="HIGH",
            impacted_tasks=["TASK-F-02"],
            telemetry_signature={"tau": 2.80, "solar_pv_loss_pct": 78.5},
        )
        core.state_mgr.physical.atmospheric_dust_tau = 2.80
        core.state_mgr.physical.direct_solar_flux_w_m2 = 120.0

        recovery = core.resilience_ops.diagnose_and_recover("INCIDENT-SOL-48-DUST-STORM")

        for _ in range(4):
            core.advance_sol()

        phase_results["phase_09_resilience"] = {
            "incident_id": incident.incident_id,
            "diagnosis": recovery.diagnosis,
            "recovery_strategy": recovery.recovery_strategy,
            "load_sheds": recovery.load_shedding_actions,
            "habitat_core_temp_k": core.state_mgr.physical.habitat_core_temp_k,
            "resolved": recovery.resolved,
            "current_sol": core.event_coord.current_sol,
        }

        # Dust clears
        core.state_mgr.physical.atmospheric_dust_tau = 0.45
        core.state_mgr.physical.direct_solar_flux_w_m2 = 480.0
        core.resilience_ops.active_load_sheds.clear()

        # -------------------------------------------------------------
        # Phase 10: Infrastructure Construction & Sintering (Sols 51-54)
        # -------------------------------------------------------------
        for _ in range(4):
            core.advance_sol()

        phase_results["phase_10_construction"] = {
            "sintered_blocks_count": core.resource_ops.sintered_blocks_count,
            "blast_berm_ready": (core.resource_ops.sintered_blocks_count >= 240),
            "current_sol": core.event_coord.current_sol,
        }

        # -------------------------------------------------------------
        # Phase 11: End-of-Campaign Audit & Mass/Energy Balance (Sols 55-58)
        # -------------------------------------------------------------
        for _ in range(4):
            core.advance_sol()

        recent_ledger = core.resource_ops.ledgers[-1]
        phase_results["phase_11_reconciliation"] = {
            "mass_conservation_discrepancy_kg": recent_ledger.mass_conservation_discrepancy_kg,
            "final_water_reserve_kg": recent_ledger.water_reserve_kg,
            "final_oxygen_reserve_kg": recent_ledger.oxygen_reserve_kg,
            "battery_soc_pct": recent_ledger.battery_soc_pct,
            "current_sol": core.event_coord.current_sol,
        }

        # -------------------------------------------------------------
        # Phase 12: Cryptographic Replay, Dossier & Phase F Review (Sols 59-60)
        # -------------------------------------------------------------
        for _ in range(2):
            core.advance_sol()

        dossier = core.generate_dossier()
        phase_results["phase_12_qualification"] = {
            "mission_id": dossier.mission_id,
            "total_duration_sols": dossier.total_duration_sols,
            "phase_f_readiness_score": dossier.phase_f_readiness_score,
            "qualification_status": "PASSED" if dossier.phase_f_readiness_score >= 95.0 else "DEGRADED",
            "root_hash": dossier.root_hash,
            "cryptographic_replay_valid": dossier.cryptographic_replay_valid,
        }

        return core, dossier, phase_results
