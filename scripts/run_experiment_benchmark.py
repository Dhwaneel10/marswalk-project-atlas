"""
scripts/run_experiment_benchmark.py
MarsWalk 2.0 / Project Atlas — Milestone 12H Experiment Studio Performance Benchmark
Measures execution time of experiment orchestration, matrix generation, and dossier export.
Enforces the <5.0s orchestration budget and <200ms export budget.
"""

import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from marswalk.api.workspace import (
    get_campaign,
    list_campaigns,
    delete_experiment_record,
)
from marswalk.core.mission_campaign import MissionCampaign
from marswalk.core.terrain import load_and_process_terrain
from marswalk.core.mission_experiment import (
    ExperimentConfig,
    orchestrate_mission_experiment,
    export_experiment_dossier_zip,
    verify_experiment_dossier_zip,
)

GEOTIFF_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "jezero_ready_20m.tif")


def run_benchmarks():
    print("=" * 76)
    print("  MARSWALK 2.0 / ATLAS — MILESTONE 12H EXPERIMENT BENCHMARK")
    print("=" * 76)

    # 1. Load terrain
    print("\n[1/4] Loading Jezero 20m DTM elevation grid...")
    t0 = time.perf_counter()
    terrain = load_and_process_terrain(GEOTIFF_PATH)
    dt_terrain = (time.perf_counter() - t0) * 1000.0
    print(f"      Loaded terrain grid ({terrain.elevation.shape}) in {dt_terrain:.1f}ms")

    # 2. Select benchmark campaign
    campaigns = list_campaigns()
    if not campaigns:
        print("      ERROR: No campaigns available for benchmark.")
        sys.exit(1)
    camp_id = campaigns[0]["campaign_id"]
    print(f"\n[2/4] Loading baseline campaign '{camp_id}'...")
    raw_camp = get_campaign(camp_id)
    campaign = MissionCampaign.from_dict(raw_camp)
    print(f"      Campaign '{campaign.name}' loaded with {len(campaign.sorties)} sorties, {len(campaign.targets)} targets.")

    # 3. Benchmark Experiment Orchestration (10 scenarios, up to 3 rehearsals)
    print("\n[3/4] Benchmarking Experiment Orchestration (Full Battery: 10 scenarios)...")
    config = ExperimentConfig(
        campaign_id=campaign.campaign_id,
        suite_type="full_battery",
        scenario_selection_strategy="degraded_or_breach",
        rehearsal_policy="balanced",
        min_margin_threshold_s=1800.0,
        max_scenarios=10,
        max_rehearsals=3,
        title="Benchmark Gauntlet",
    )

    t_orch_start = time.perf_counter()
    record = orchestrate_mission_experiment(campaign, terrain, config)
    t_orch_end = time.perf_counter()
    dt_orch_s = t_orch_end - t_orch_start

    print(f"      Orchestrated {len(record.scenarios)} scenarios in {dt_orch_s:.3f}s")
    print(f"      Rehearsals conducted: {record.summary_metrics['rehearsals_executed_count']}")
    print(f"      Feasible scenarios:   {record.summary_metrics['robustness_feasible_count']} / {len(record.scenarios)}")
    print(f"      Mean science preserved: {record.summary_metrics['mean_science_preservation_pct']}%")

    ORCHESTRATION_BUDGET_S = 5.0
    assert dt_orch_s < ORCHESTRATION_BUDGET_S, f"Orchestration exceeded {ORCHESTRATION_BUDGET_S}s budget: {dt_orch_s:.3f}s"
    print(f"      [PASS] Orchestration within budget (< {ORCHESTRATION_BUDGET_S}s)")

    # 4. Benchmark Mission Evidence Dossier ZIP Export & Readback
    print("\n[4/4] Benchmarking Evidence Dossier ZIP Export & SHA-256 Verification...")
    t_zip_start = time.perf_counter()
    zip_path = export_experiment_dossier_zip(record.experiment_id)
    t_zip_end = time.perf_counter()
    dt_zip_ms = (t_zip_end - t_zip_start) * 1000.0

    zip_size = os.path.getsize(zip_path)
    print(f"      Exported ZIP pack ({zip_size} bytes) in {dt_zip_ms:.1f}ms")

    ZIP_EXPORT_BUDGET_MS = 200.0
    assert dt_zip_ms < ZIP_EXPORT_BUDGET_MS, f"ZIP export exceeded {ZIP_EXPORT_BUDGET_MS}ms budget: {dt_zip_ms:.1f}ms"
    print(f"      [PASS] Export within budget (< {ZIP_EXPORT_BUDGET_MS}ms)")

    # Verify ZIP readback
    is_valid, errors = verify_experiment_dossier_zip(zip_path)
    assert is_valid, f"Dossier ZIP verification failed: {errors}"
    print("      [PASS] Readback verification: all 5 files match cryptographic checksums without omission.")

    # Cleanup
    if os.path.exists(zip_path):
        os.remove(zip_path)
    delete_experiment_record(record.experiment_id)

    print("\n" + "=" * 76)
    print("  >>> ALL BENCHMARKS PASSED: EXPERIMENT STUDIO HIGH PERFORMANCE VERIFIED <<<")
    print("=" * 76)


if __name__ == "__main__":
    run_benchmarks()
