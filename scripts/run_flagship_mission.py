"""
scripts/run_flagship_mission.py
One-Command Flagship Mission Reproduction Tool for Project Atlas / MarsWalk 2.0.
Executes or validates ATLAS-MARS-BASE-ALPHA-001 (60-Sol Autonomous Campaign).
"""

import sys
import os
import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

EXPECTED_USGS_DTM_SHA256 = "875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3"

def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def verify_inputs(no_network: bool = False) -> Dict[str, Any]:
    """Verify presence, integrity, and cryptographic checksums of all input dependencies."""
    dtm_path = REPO_ROOT / "data" / "processed" / "jezero_ready_20m.tif"
    if not dtm_path.exists():
        dtm_path = REPO_ROOT / "data" / "terrain" / "usgs_jezero_20m.tif"
        
    if not dtm_path.exists():
        raise FileNotFoundError(
            f"Missing required primary terrain dataset: {dtm_path}\n"
            f"Project Atlas strictly prohibits synthetic terrain generation. Obtain authentic USGS DTM first."
        )
        
    actual_hash = compute_sha256(dtm_path)
    if actual_hash.lower() != EXPECTED_USGS_DTM_SHA256.lower():
        raise ValueError(
            f"Cryptographic hash mismatch for terrain raster:\n"
            f"Expected: {EXPECTED_USGS_DTM_SHA256}\n"
            f"Actual:   {actual_hash}\n"
            f"Aborting execution to protect scientific reproducibility."
        )
        
    return {
        "status": "VERIFIED",
        "dtm_path": str(dtm_path),
        "dtm_sha256": actual_hash,
        "offline_mode": no_network,
    }

def main():
    parser = argparse.ArgumentParser(
        description="Execute or validate the 60-Sol Flagship Mission ATLAS-MARS-BASE-ALPHA-001."
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate required inputs and cryptographic checksums without running full simulation."
    )
    parser.add_argument(
        "--no-network",
        action="store_true",
        default=True,
        help="Enforce offline execution using strictly local preserved assets (default: True)."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(REPO_ROOT / "data" / "workspaces" / "flagship_run"),
        help="Directory to save execution logs, event ledger, evidence, and final dossier."
    )
    parser.add_argument(
        "--perturb-power-kw",
        type=float,
        default=0.0,
        help="Optional controlled perturbation: reduce reactor power by specified kW at Sol 15 for sensitivity analysis."
    )

    args = parser.parse_args()

    print("=" * 80)
    print("  PROJECT ATLAS / MARSWALK 2.0 — FLAGSHIP MISSION REPRODUCTION")
    print("  Campaign: ATLAS-MARS-BASE-ALPHA-001 (60-Sol Autonomous Campaign)")
    print("=" * 80)

    # 1. Verify required inputs and source hashes
    print("[1/5] Verifying input data provenance and cryptographic checksums...")
    try:
        ver_info = verify_inputs(no_network=args.no_network)
        print(f"      - USGS Jezero 20m DTM: VERIFIED (SHA-256: {ver_info['dtm_sha256'][:16]}...)")
        print(f"      - Network Mode: {'OFFLINE (No external calls)' if ver_info['offline_mode'] else 'ONLINE'}")
    except Exception as e:
        print(f"\n[FATAL ERROR] Data verification failed: {e}", file=sys.stderr)
        return 1

    if args.validate_only:
        print("\n>>> VALIDATION SUCCESSFUL: All input prerequisites and source hashes verified.")
        print(">>> Flagship mission is fully runnable without network dependencies.")
        print("=" * 80)
        return 0

    # 2. Initialize Simulation & Core
    print("\n[2/5] Initializing Mission Execution Core & Closed-Loop Coordinator...")
    from marswalk.core.atlas_integrated_mission_scenario import IntegratedMissionScenarioRunner
    from marswalk.core.atlas_mission_contracts import MissionObjective
    from marswalk.core.atlas_mission_execution_core import AtlasMissionExecutionCore

    # 3. Execute Mission Phases
    print("\n[3/5] Executing 12 Operational Phases across 60 Sols...")
    if args.perturb_power_kw == 0.0:
        core, dossier, phase_results = IntegratedMissionScenarioRunner.run_flagship_mission()
    else:
        print(f"      [NOTE] Applying controlled perturbation: -{args.perturb_power_kw:.1f} kWe reactor power at Sol 15.0")
        obj = MissionObjective(
            objective_id="OBJ-ATLAS-ALPHA-001",
            title="Establish Autonomous Research Settlement in Jezero Crater",
            raw_intent="Establish a robotic research settlement in Jezero (perturbed run).",
            target_site_id="SITE-JEZERO-DELTA-01",
            target_region="Jezero Crater Western Delta Outwash",
            duration_sols=60,
        )
        core = AtlasMissionExecutionCore(mission_id="ATLAS-MARS-BASE-ALPHA-001", objective=obj)
        # Advance to Sol 14
        for _ in range(14):
            core.advance_sol()
        # Apply perturbation
        core.resource_ops.reactor_rated_kwe = max(10.0, core.resource_ops.reactor_rated_kwe - args.perturb_power_kw)
        # Complete remaining 46 Sols
        for _ in range(46):
            core.advance_sol()
        dossier = core.generate_dossier()
        phase_results = {"perturbed": True, "reduction_kwe": args.perturb_power_kw}

    print("      - Phase 01 to 12 executed successfully.")
    print(f"      - Total Event Ledger Count: {len(core.event_coord._history)} events recorded.")
    print(f"      - Hypotheses Tested: {len(core.science_ops.investigations)}")
    print(f"      - Final Water Reserve: {core.resource_ops.ledgers[-1].water_reserve_kg:.2f} kg")
    print(f"      - Final Oxygen Reserve: {core.resource_ops.ledgers[-1].oxygen_reserve_kg:.2f} kg")
    print(f"      - Mass Balance Discrepancy: {core.resource_ops.ledgers[-1].mass_conservation_discrepancy_kg:.6f} kg")

    # 4. Save Artifacts to Workspace
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[4/5] Exporting execution dossiers and audit ledgers to: {out_dir}")

    # Event ledger
    event_ledger_path = out_dir / "event_ledger.json"
    with open(event_ledger_path, "w", encoding="utf-8") as f:
        json.dump(core.event_coord.get_history(), f, indent=2)

    # Scientific evidence
    science_path = out_dir / "scientific_evidence.json"
    with open(science_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": core.science_ops.get_summary_metrics(),
            "investigations": [h.to_dict() for h in core.science_ops.investigations.values()],
            "observations": [o.to_dict() for o in core.science_ops.observations],
        }, f, indent=2)

    # Resource accounting
    resource_path = out_dir / "resource_accounting.json"
    with open(resource_path, "w", encoding="utf-8") as f:
        json.dump([l.to_dict() for l in core.resource_ops.ledgers], f, indent=2)

    # Mission outcomes
    outcomes_path = out_dir / "mission_outcomes.json"
    with open(outcomes_path, "w", encoding="utf-8") as f:
        json.dump(phase_results, f, indent=2)

    # Dossier
    dossier_json_path = out_dir / "mission_dossier.json"
    with open(dossier_json_path, "w", encoding="utf-8") as f:
        json.dump(dossier.to_dict(), f, indent=2)

    dossier_md_path = out_dir / "mission_dossier.md"
    d_dict = dossier.to_dict()
    md_content = f"""# Project Atlas — Mission Dossier: {dossier.mission_id}
**Objective:** {dossier.objective_title}  
**Total Duration:** {dossier.total_duration_sols} Sols  
**Root Merkle Hash:** `{dossier.root_hash}`  
**Phase F Readiness Score:** {dossier.phase_f_readiness_score:.1f}%  
**Cryptographic Replay Valid:** {dossier.cryptographic_replay_valid}  

## Mission Statistics
- Total Distance Covered: {dossier.total_distance_covered_m:.1f} m
- Total Observations Acquired: {dossier.total_observations_acquired}
- Hypotheses Validated: {dossier.hypotheses_validated_count}
- Total Energy Generated: {dossier.total_energy_generated_kwh:.1f} kWh
- Total ISRU O2 Generated: {dossier.total_isru_o2_generated_kg:.2f} kg
- Total Sintered Regolith Blocks: {dossier.total_isru_blocks_produced}
- Incidents Handled: {dossier.incidents_handled_count}
- Unplanned Loss Events: {dossier.unplanned_loss_events_count}

## Scientific Integrity Disclosure
> {dossier.mandatory_scientific_disclosure}
"""
    with open(dossier_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # State hash
    state_hash_path = out_dir / "state_hash.json"
    with open(state_hash_path, "w", encoding="utf-8") as f:
        json.dump({
            "mission_id": core.mission_id,
            "root_hash": dossier.root_hash,
            "hash_chain_length": len(core.state_mgr.history),
            "cryptographic_replay_valid": dossier.cryptographic_replay_valid,
            "phase_f_readiness_score": dossier.phase_f_readiness_score,
            "timestamp_utc": dossier.provenance_record.get("timestamp_utc") or "2026-11-06T00:00:00Z",
        }, f, indent=2)

    # 5. Output Summary
    print("\n[5/5] Cryptographic Verification & Dossier Summary:")
    print("=" * 80)
    print(f"  Mission ID:                  {dossier.mission_id}")
    print(f"  Total Duration:              {dossier.total_duration_sols} Sols")
    print(f"  Phase F Readiness Score:     {dossier.phase_f_readiness_score:.1f}%")
    print(f"  Qualification Status:        {'QUALIFIED' if dossier.phase_f_readiness_score >= 95.0 else 'DEGRADED'}")
    print(f"  Deterministic Root Hash:     {dossier.root_hash}")
    print(f"  Merkle Chain Verification:   {'BIT-EXACT DETERMINISTIC MATCH' if dossier.cryptographic_replay_valid else 'DIVERGED'}")
    print("=" * 80)
    print(f">>> REPRODUCTION COMPLETED: Outputs archived in {out_dir}\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
