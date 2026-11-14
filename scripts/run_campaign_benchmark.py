#!/usr/bin/env python3
"""
MarsWalk 2.0 — Milestone 11I Campaign Benchmark Suite Runner.
Executes the deterministic 8-scenario campaign benchmark harness across authentic
USGS CTX 20m Jezero topography and verifies all operational invariants.
"""

import os
import sys
import json
import argparse
import datetime
from pathlib import Path

# Add src to python path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from marswalk.core.campaign_benchmark import (
    run_campaign_benchmark_suite,
    BenchmarkSuiteResult,
    BENCHMARK_SUITE_DISCLAIMER,
)
from marswalk.api.workspace import (
    save_campaign_benchmark_result,
    DEFAULT_CAMPAIGN_BENCHMARKS_DIR,
)


def main():
    parser = argparse.ArgumentParser(
        description="MarsWalk 2.0 Campaign Benchmark & V2 Acceptance Harness Runner"
    )
    parser.add_argument(
        "--scenarios",
        type=str,
        default=None,
        help="Comma-separated scenario IDs to run (e.g., BM-NORM-01,BM-PARETO-06). Default: all 8 scenarios.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join(REPO_ROOT, "outputs", "benchmarks", "campaign_benchmark_results.json"),
        help="Path to write machine-readable JSON results. Default: outputs/benchmarks/campaign_benchmark_results.json",
    )
    parser.add_argument(
        "--workspace-dir",
        type=str,
        default=None,
        help="Optional custom workspace directory for isolated testing.",
    )
    parser.add_argument(
        "--no-reproducibility",
        action="store_true",
        help="Skip repeat-run reproducibility verification pass.",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format to stdout (table or json).",
    )

    args = parser.parse_args()

    scenario_list = None
    if args.scenarios:
        scenario_list = [s.strip() for s in args.scenarios.split(",") if s.strip()]

    print("========================================================================================")
    print("  MARSWALK 2.0 — CAMPAIGN BENCHMARK & V2 ACCEPTANCE HARNESS")
    print("========================================================================================")
    print(f"Timestamp: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Target Terrain: USGS CTX 20m DTM (Jezero Crater)")
    print(f"Reproducibility Audit: {'Enabled' if not args.no_reproducibility else 'Disabled'}")
    print("----------------------------------------------------------------------------------------\n")

    suite_result: BenchmarkSuiteResult = run_campaign_benchmark_suite(
        scenarios=scenario_list,
        workspace_dir=args.workspace_dir,
        verify_reproducibility=not args.no_reproducibility,
    )

    result_dict = suite_result.to_dict()

    # Save to persistent workspace storage
    try:
        save_campaign_benchmark_result(result_dict, workspace_dir=args.workspace_dir)
        print(f"[OK] Persisted benchmark suite '{suite_result.suite_id}' to workspace storage.")
    except Exception as e:
        print(f"[WARNING] Could not save to workspace storage: {e}", file=sys.stderr)

    # Save to machine-readable output path
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2)
        print(f"[OK] Machine-readable results exported to: {out_path.resolve()}\n")

    if args.format == "json":
        print(json.dumps(result_dict, indent=2))
    else:
        print(f"{'SCENARIO ID':<13} {'NAME':<42} {'CATEGORY':<20} {'STATUS':<8} {'RUNTIME':<10} {'INVARIANTS'}")
        print("-" * 115)
        for s in suite_result.scenarios:
            inv_str = f"{len(s.invariants_verified)} passed"
            if s.discrepancies_or_warnings:
                inv_str += f" ({len(s.discrepancies_or_warnings)} warnings)"
            print(f"{s.scenario_id:<13} {s.name:<42} {s.category:<20} [{s.status:<6}] {s.duration_ms:>6.1f} ms  {inv_str}")
        print("-" * 115)
        print(f"Summary: {suite_result.passed_scenarios}/{suite_result.total_scenarios} scenarios passed in {suite_result.execution_time_s:.3f} s.")
        print(f"Candidates Evaluated: {suite_result.total_candidates_evaluated} across all scenarios.")
        print(f"Reproducibility Verified: {'PASSED (Zero metric drift on repeat pass)' if suite_result.reproducibility_verified else 'FAILED (Drift detected)'}")
        print("========================================================================================\n")

    if suite_result.failed_scenarios > 0 or not suite_result.reproducibility_verified:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
