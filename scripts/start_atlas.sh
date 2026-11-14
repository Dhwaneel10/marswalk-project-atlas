#!/usr/bin/env bash
# scripts/start_atlas.sh
# MarsWalk 2.0 / Project Atlas — Linux Workstation Launcher
# Launches the Atlas HTTP server on port 3000 (or custom --port)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

PORT="3000"
NO_BROWSER=""
DEMO_MODE=""

# Parse command line options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port|-p)
            PORT="$2"
            shift 2
            ;;
        --no-browser)
            NO_BROWSER="--no-browser"
            shift
            ;;
        --demo)
            DEMO_MODE="--demo"
            shift
            ;;
        --help|-h)
            echo "Usage: ./scripts/start_atlas.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --port, -p PORT    HTTP listen port (default: 3000)"
            echo "  --no-browser       Do not attempt to auto-launch browser"
            echo "  --demo             Launch in Conference Demo Mode (?mode=demo)"
            echo "  --help, -h         Display this help message"
            exit 0
            ;;
        *)
            echo "[WARN] Unknown argument: $1"
            shift
            ;;
    esac
done

echo "======================================================================"
echo "  PROJECT ATLAS / MARSWALK 2.0 — MISSION CONTROL WORKSTATION"
echo "======================================================================"

# 1. Verify virtual environment exists
VENV_PY="${REPO_ROOT}/.venv/bin/python"

if [ ! -f "$VENV_PY" ]; then
    echo "[ERROR] Virtual environment not found at ${REPO_ROOT}/.venv." >&2
    echo "        Run ./scripts/setup_atlas.sh first to bootstrap the environment." >&2
    exit 1
fi

# 2. Check if port is already occupied
if command -v ss &>/dev/null; then
    if ss -tuln | grep -q ":${PORT}\b"; then
        echo "[ERROR] Port ${PORT} is already in use by another process." >&2
        echo "        Specify an alternative port with --port <PORT> or terminate the existing process." >&2
        exit 1
    fi
elif command -v netstat &>/dev/null; then
    if netstat -tuln | grep -q ":${PORT}\b"; then
        echo "[ERROR] Port ${PORT} is already in use by another process." >&2
        exit 1
    fi
fi

# 3. Clean up ROS environment variables that might shadow local packages
export PYTHONPATH="src:."
export PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"

echo "[INFO] Using Python: $VENV_PY"
echo "[INFO] PYTHONPATH: $PYTHONPATH"
echo "[INFO] Target Listen Port: $PORT"
echo "[INFO] Working Directory: $REPO_ROOT"
echo "----------------------------------------------------------------------"
echo "  Starting Atlas HTTP Server on http://127.0.0.1:${PORT}/"
echo "  Access Demo Mode: http://127.0.0.1:${PORT}/?mode=demo"
echo "  Press Ctrl+C to terminate the server gracefully."
echo "======================================================================"

# 4. Launch the application
CMD=("$VENV_PY" "scripts/run_atlas.py" "--port" "$PORT")

if [ -n "$NO_BROWSER" ]; then
    CMD+=("$NO_BROWSER")
fi

if [ -n "$DEMO_MODE" ]; then
    CMD+=("$DEMO_MODE")
fi

exec "${CMD[@]}"
