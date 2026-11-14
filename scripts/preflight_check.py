"""
MarsWalk 2.0 — Preflight Readiness Verification CLI
Execute before competition presentations and live demonstrations to verify:
  1. Atlas HTTP server health
  2. Frontend web assets
  3. Planetary feature gazetteer (2,000+ entries)
  4. Multi-scale imagery registry
  5. Global Mars basemap layer
  6. Jezero CTX optical imagery
  7. Jezero 20m DTM elevation model
  8. Python A* route planning engine
  9. Gauntlet disruption & recovery engine
 10. Persistent workspace storage
 11. Technical mission briefing export & Draft 2020-12 schema validation
 12. Streamlit tactical control companion
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Ensure src/ is on Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from marswalk.api.preflight import run_preflight_diagnostics


def main():
    parser = argparse.ArgumentParser(description="MarsWalk 2.0 Preflight Diagnostic Verification")
    parser.add_argument("--port", type=int, default=3000, help="Atlas server port (default: 3000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Atlas server host (default: 127.0.0.1)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON diagnostic report")
    parser.add_argument("--quiet", action="store_true", help="Minimal output, exit code only")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    res = run_preflight_diagnostics(base_url=base_url)

    if args.json:
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["is_ready_for_demo"] else 1)

    if not args.quiet:
        print("=" * 76)
        print("  MARSWALK 2.0 — PREFLIGHT READINESS VERIFICATION REPORT")
        print("=" * 76)
        print(f"Timestamp: {res['timestamp']}")
        print(f"Target Server: {base_url}\n")
        print(f"{'#':<3} {'CHECKPOINT':<36} {'STATUS':<10} {'DETAILS'}")
        print("-" * 76)

        for i, c in enumerate(res["checks"], 1):
            status_str = f"[{c['status'].upper()}]"
            details = c["details"]
            if len(details) > 38:
                details = details[:35] + "..."
            print(f"{i:02d}  {c['name']:<36} {status_str:<10} {details}")

        print("-" * 76)
        print(f"Summary: {res['summary']}")
        if res["is_ready_for_demo"]:
            print("\n>>> PREFLIGHT PASSED: MarsWalk 2.0 is READY for live demonstration! <<<\n")
        else:
            print(f"\n>>> PREFLIGHT FAILED: {res['failed_count']} critical checks failed. Resolve issues before presenting. <<<\n")

    sys.exit(0 if res["is_ready_for_demo"] else 1)


if __name__ == "__main__":
    main()
