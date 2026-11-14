#!/usr/bin/env bash
# ==============================================================================
# MarsWalk 2.0 / Project Atlas — Isolated Test Runner
# Cleans host system PYTHONPATH (e.g., ROS Humble) to prevent plugin collision.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Isolate python path to project source
export PYTHONPATH="$PROJECT_ROOT/src:$PROJECT_ROOT"

echo "=== Running MarsWalk Test Suite via Isolated Virtual Environment ==="
"$PROJECT_ROOT/.venv/bin/pytest" -p no:launch_testing -p no:launch_testing_ros -p no:launch_ros -o pythonpath="src ." "$@"
