"""
scripts/run_grand_prix_benchmark.py
Executes the Milestone 13X Grand Prix Tournament & Benchmarking Experiment.
Runs 1,020 simulations across 8 tournament rounds, sweeps sensitivity,
and generates benchmark CSV/JSON artifacts.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import time

from marswalk.core.atlas_grand_prix_experiment import GrandPrixExperimentEngine
from marswalk.core.atlas_grand_prix_scenario_generator import ScenarioPartition
from marswalk.core.atlas_mission_grand_prix import AtlasMissionGrandPrixTournament
from marswalk.core.atlas_mission_sensitivity import MissionSensitivityEngine


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "data" / "workspaces" / "grand_prix_runs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run_full_grand_prix_benchmark():
    print("=" * 80)
    print("  PROJECT ATLAS / MARSWALK 2.0 — MILESTONE 13X GRAND PRIX")
    print("  8-Round Planetary Mission Planning Championship (6 Strategies x 170 Scenarios)")
    print("=" * 80)

    t0 = time.perf_counter()
    tournament = AtlasMissionGrandPrixTournament(output_dir=OUTPUT_DIR)

    print("\n[1/4] Executing 8-Round Championship Tournament...")
    dossier = tournament.run_tournament(tournament_id="GRAND-PRIX-CHAMPIONSHIP-13X")
    print(f"      - Rounds Completed: {dossier['rounds_executed_count']}")
    print(f"      - Total Simulations: {dossier['total_simulations_executed']}")
    print(f"      - Wall Clock: {dossier['total_wall_clock_seconds']}s")

    print("\n[2/4] Tournament Champions Crowned:")
    for category, champ in dossier["champions"].items():
        print(f"      - {category.upper()}: {champ['strategy_id']} ({champ['title']})")

    print("\n[3/4] Running Atmospheric Dust Tau Sensitivity Sweep...")
    dust_report = MissionSensitivityEngine.sweep_dust_opacity(base_seed=1050)
    print(f"      - Evaluated {len(dust_report.parameter_range)} tau points across 6 strategies")
    print(f"      - Robustness Rankings: {dust_report.robustness_rankings}")

    print("\n[4/4] Exporting Benchmark Results to CSV...")
    csv_path = OUTPUT_DIR / "strategy_rankings_summary.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Strategy ID",
            "Total Runs",
            "Feasibility Rate (%)",
            "Science Mean",
            "Science Median",
            "Energy Mean (kWh)",
            "Distance Mean (km)",
            "Fault Containment Rate",
            "Composite Index Mean",
            "CVaR 5%",
        ])
        for s_id, s_data in dossier["overall_strategy_standings"].items():
            writer.writerow([
                s_id,
                s_data["total_runs"],
                s_data["feasibility_rate_pct"],
                s_data["science"]["mean"],
                s_data["science"]["median"],
                s_data["energy_kwh"]["mean"],
                s_data["distance_km"]["mean"],
                s_data["containment_rate_mean"],
                s_data["composite_score"]["mean"],
                s_data["composite_score"]["cvar_05"],
            ])
    print(f"      - Exported CSV summary to: {csv_path}")

    elapsed = time.perf_counter() - t0
    print("\n" + "=" * 80)
    print(f">>> GRAND PRIX COMPLETE: 1,020 Simulations in {elapsed:.2f}s ({dossier['total_simulations_executed']/max(0.01, elapsed):.1f} sim/s) <<<")
    print("=" * 80)


if __name__ == "__main__":
    run_full_grand_prix_benchmark()
