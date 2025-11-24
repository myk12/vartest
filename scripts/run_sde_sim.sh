#!/usr/bin/env bash
set -euo pipefail

# Run the SDE Tofino software model and load the compiled program in a safe way.
# Usage: sudo ./scripts/run_sde_sim.sh
# The script will:
#  - source scripts/env.sh
#  - set up veth pairs (using SDE veth_setup.sh)
#  - start tofino-model (if present)
#  - start bf_switchd with the program .conf (from TS_P4_BUILD)
#  - run bfshell -b py/exp/runner.py to program safe pass-through + one forward entry

if [ "$EUID" -ne 0 ]; then
  echo "This script should be run as root (sudo) since it creates veths and starts the model." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env.sh"

: "${TS_P4_BUILD:?TS_P4_BUILD must be set (build outputs)}"
CONF_FILE="$TS_P4_BUILD/${TS_P4_PROG}.conf"

LOGDIR="$TS_PROJ_ROOT/results/sim_logs"
mkdir -p "$LOGDIR"

echo "Setting up veth pairs (using SDE helper)"
if [ -x "$SDE_INSTALL/bin/veth_setup.sh" ]; then
  "$SDE_INSTALL/bin/veth_setup.sh"
else
  echo "[WARN] veth_setup.sh not found/executable. You may need to create veths manually." >&2
fi

if [ -x "$SDE_INSTALL/bin/tofino-model" ]; then
  echo "Starting tofino-model (background)"
  "$SDE_INSTALL/bin/tofino-model" &> "$LOGDIR/tofino-model.log" &
  TMODEL_PID=$!
  echo "tofino-model PID=$TMODEL_PID"
  sleep 2
else
  echo "[WARN] tofino-model not found; bf_switchd may still run if platform supported." >&2
fi

# Start bf_switchd. Prefer using a local .conf, but if the build used the
# SDE tools (tools/p4_build) the program artifacts live under
# $SDE_INSTALL/share/tofino2pd/<prog>. In that case we can start bf_switchd
# using the -p <prog> option which tells bf_switchd to use the installed
# package.
if [ -f "$CONF_FILE" ]; then
  echo "Starting bf_switchd with conf: $CONF_FILE"
  "${SDE_INSTALL%/}/bin/bf_switchd" -f "$CONF_FILE" --background &> "$LOGDIR/bf_switchd.log"
  BF_PID=$!
  echo "bf_switchd PID=$BF_PID"
else
  PD_DIR="${SDE_INSTALL%/}/share/tofino2pd/${TS_P4_PROG}"
  if [ -d "$PD_DIR" ]; then
    echo "No local .conf found; starting bf_switchd with program name: ${TS_P4_PROG} (using -p)"
    "${SDE_INSTALL%/}/bin/bf_switchd" -p "$TS_P4_PROG" --background &> "$LOGDIR/bf_switchd.log"
    BF_PID=$!
    echo "bf_switchd PID=$BF_PID"
  else
    echo "[ERROR] Conf file not found: $CONF_FILE and no SDE-installed program at $PD_DIR" >&2
    echo "Build first: scripts/build_p4.sh (or install program to SDE share)" >&2
    exit 1
  fi
fi

echo "Waiting a few seconds for bfrt to initialize..."
sleep 6

echo "Programming safe pass-through + sample forward entry via bfshell"
if command -v bfshell >/dev/null 2>&1; then
  bfshell -b "$TS_PROJ_ROOT/py/exp/runner.py" &> "$LOGDIR/bfshell_runner.log"
else
  echo "[ERROR] bfshell not found in PATH. Make sure scripts/env.sh was sourced and SDE is installed." >&2
  exit 1
fi

echo "Simulation start & programming complete. Logs in $LOGDIR"
echo "To stop the simulation: sudo ./scripts/stop_sde_sim.sh"
