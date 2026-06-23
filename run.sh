#!/usr/bin/env bash
set -euo pipefail

# Wrapper for compare_timeseries.py with practical defaults.
# Usage examples:
#   ./run.sh /path/to/file --observed-pattern "USGS"
#   ./run.sh /path/to/file --observed-pattern "Observed" --plot-name myplot.png

if [[ $# -lt 1 ]]; then
  echo "Usage: ./run.sh <data_path> [compare_timeseries options]"
  echo "Example: ./run.sh /path/to/file --observed-pattern \"Observed\""
  exit 1
fi

DATA_PATH="$1"
shift

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${SCRIPT_DIR}/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing virtual environment python at: $PYTHON_BIN"
  echo "Run these first:"
  echo "  python -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install -r requirements.txt"
  exit 1
fi

OUTPUT_DIR="${OUTPUT_DIR:-tmp_plots}"

"$PYTHON_BIN" "$SCRIPT_DIR/compare_timeseries.py" \
  "$DATA_PATH" \
  --output-dir "$OUTPUT_DIR" \
  --metrics-out "$OUTPUT_DIR" \
  "$@"
