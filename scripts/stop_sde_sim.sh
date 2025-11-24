#!/usr/bin/env bash
set -euo pipefail

# Stop bf_switchd and tofino-model and teardown veths (run as root)
if [ "$EUID" -ne 0 ]; then
  echo "This script should be run as root (sudo)" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env.sh"

LOGDIR="$TS_PROJ_ROOT/results/sim_logs"

echo "Stopping bf_switchd processes"
pkill -f bf_switchd || true
sleep 1

echo "Stopping tofino-model processes"
pkill -f tofino-model || true
sleep 1

echo "Tearing down veth pairs"
if [ -x "$SDE_INSTALL/bin/veth_teardown.sh" ]; then
  "$SDE_INSTALL/bin/veth_teardown.sh"
else
  echo "[WARN] veth_teardown.sh not found; manual cleanup may be required." >&2
fi

echo "Stopped simulator and cleaned up (logs in $LOGDIR)"
