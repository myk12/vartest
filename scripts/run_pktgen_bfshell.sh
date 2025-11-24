#!/usr/bin/env bash
set -euo pipefail
# Helper to run the project's pktgen script under the SDE `bfshell`.
# Usage: ./scripts/run_pktgen_bfshell.sh
# You can override DPTP_ROOT or BFSHELL_BIN via env vars.

DPTP_ROOT="${DPTP_ROOT:-$(realpath "$(dirname "$0")/..") }"
SCRIPT_PATH="${DPTP_ROOT}/py/core/pktgen.py"
BFSHELL_BIN="${BFSHELL_BIN:-/home/p4/bf-sde-9.12.0/install/bin/bfshell}"

if [ ! -f "$SCRIPT_PATH" ]; then
  echo "Error: script not found: $SCRIPT_PATH" >&2
  exit 1
fi

if [ ! -x "$BFSHELL_BIN" ]; then
  # Try to find bfshell on PATH
  BFSHELL_BIN="$(command -v bfshell || true)"
  if [ -z "$BFSHELL_BIN" ]; then
    echo "Error: bfshell not found at default path and not on PATH." >&2
    echo "Set BFSHELL_BIN to the bfshell binary or install the SDE." >&2
    exit 1
  fi
fi

echo "Running pktgen script with bfshell: $BFSHELL_BIN -b $SCRIPT_PATH"
exec "$BFSHELL_BIN" -b "$SCRIPT_PATH"
