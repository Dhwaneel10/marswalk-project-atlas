#!/usr/bin/env bash
# scripts/setup_atlas.sh
# MarsWalk 2.0 / Project Atlas — Automated Linux Setup & Environment Bootstrap
# Target Environment: Ubuntu 22.04 LTS with Python 3.10+

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "======================================================================"
echo "  PROJECT ATLAS / MARSWALK 2.0 — LINUX ENVIRONMENT SETUP"
echo "======================================================================"

# 1. Check OS and distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "[OK] Detected Operating System: ${NAME:-Linux} ${VERSION:-}"
else
    echo "[INFO] Running on POSIX-compliant Linux system."
fi

# 2. Check Python installation and version (requires >= 3.10)
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "[ERROR] Python 3 was not found on PATH. Please install Python 3.10+." >&2
    exit 1
fi

PY_VERSION=$("$PYTHON_CMD" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
PY_MAJOR=$("$PYTHON_CMD" -c "import sys; print(sys.version_info.major)")
PY_MINOR=$("$PYTHON_CMD" -c "import sys; print(sys.version_info.minor)")

echo "[OK] Detected Python executable: $(command -v "$PYTHON_CMD") (Version: ${PY_VERSION})"

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo "[ERROR] Python version >= 3.10 is required (detected ${PY_VERSION})." >&2
    exit 1
fi

# 3. Create or verify isolated virtual environment (.venv)
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating isolated virtual environment in .venv..."
    "$PYTHON_CMD" -m venv .venv
    echo "[OK] Virtual environment created."
else
    echo "[OK] Existing virtual environment detected in .venv."
fi

VENV_PY="${REPO_ROOT}/.venv/bin/python"
VENV_PIP="${REPO_ROOT}/.venv/bin/pip"

if [ ! -x "$VENV_PY" ]; then
    echo "[ERROR] Virtual environment python ($VENV_PY) is not executable." >&2
    exit 1
fi

# 4. Upgrade pip and build tooling inside .venv
echo "[INFO] Upgrading pip, setuptools, and wheel in .venv..."
"$VENV_PY" -m pip install --upgrade pip setuptools wheel --quiet

# 5. Install required dependencies
echo "[INFO] Installing core production dependencies from requirements.txt..."
"$VENV_PIP" install -r requirements.txt --quiet

# Install additional test / analytical packages if available
if [ -f "requirements-lock.txt" ]; then
    echo "[INFO] Ensuring secondary analytical dependencies (pillow, plotly, streamlit) are installed..."
    "$VENV_PIP" install pillow plotly streamlit --quiet || echo "[WARN] Optional dependencies skipped."
fi

# 6. Copy default environment configuration if .env does not exist
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "[INFO] Initializing .env configuration from .env.example..."
    cp .env.example .env
fi

# 7. Run system installation and dataset verification
echo "[INFO] Executing system installation and integrity audit..."
PYTHONPATH="src:." "$VENV_PY" scripts/verify_installation.py

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "======================================================================"
    echo "  SETUP COMPLETE: MarsWalk 2.0 Linux environment is ready."
    echo "  To launch the workstation: ./scripts/start_atlas.sh --port 3000"
    echo "======================================================================"
    exit 0
else
    echo "[WARNING] Verification detected errors or missing datasets. Check log above." >&2
    exit $EXIT_CODE
fi
