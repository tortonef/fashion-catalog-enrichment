#!/usr/bin/env bash
# macOS/Linux setup: creates .venv, installs CPU-only dependencies, downloads the model, runs a smoke check.
# Safe to run more than once. Usage: bash setup.sh
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONUTF8=1

if [ ! -x .venv/bin/python ]; then
  PYTHON="$(command -v python3.12 || command -v python3 || true)"
  [ -n "$PYTHON" ] || { echo "Python 3.12 not found. Install it from python.org."; exit 1; }
  echo "==> Create virtual environment ($PYTHON)"
  "$PYTHON" -m venv .venv
fi
PY=.venv/bin/python
"$PY" -c "import sys; assert sys.version_info[:2] == (3, 12), 'Python 3.12 is required, found ' + sys.version"
echo "==> Upgrade pip"; "$PY" -m pip install --quiet --upgrade pip
if [ "$(uname -s)" = "Linux" ]; then
  # The default Linux wheel bundles CUDA (several GB): use the CPU-only index instead.
  echo "==> Install PyTorch (CPU only)"
  "$PY" -m pip install --quiet torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
fi
echo "==> Install dependencies"; "$PY" -m pip install --quiet -r requirements.txt -r requirements-dev.txt
echo "==> Install this package"; "$PY" -m pip install --quiet --no-deps -e .
echo "==> Download model (first run only, ~600 MB)"; "$PY" -m catalog_enrichment.download
echo "==> Smoke check"; "$PY" -m catalog_enrichment.smoke
echo; echo "Setup complete. Start the app with: bash run.sh"
