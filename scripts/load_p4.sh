#!/usr/bin/env bash
set -euo pipefail

# Load P4 program by starting bf_switchd with the generated .conf
# This is typically created by the SDE build pipeline.

: "${SDE_INSTALL:?SDE_INSTALL not set. source scripts/env.sh}"
: "${TS_P4_BUILD:?}"

CONF_FILE="${TS_P4_BUILD}/${TS_P4_PROG}.conf"

if [[ -f "$CONF_FILE" ]]; then
  echo "Starting bf_switchd with conf: $CONF_FILE"
  "${SDE_INSTALL%/}/bin/bf_switchd" -f "$CONF_FILE" --background
  echo "bf_switchd started (background)."
else
  PD_DIR="${SDE_INSTALL%/}/share/tofino2pd/${TS_P4_PROG}"
  if [[ -d "$PD_DIR" ]]; then
    echo "No local conf found; starting bf_switchd using installed program name: $TS_P4_PROG"
    "${SDE_INSTALL%/}/bin/bf_switchd" -p "$TS_P4_PROG" --background
    echo "bf_switchd started (background) using -p $TS_P4_PROG"
  else
    echo "[ERROR] Conf file not found: $CONF_FILE and no installed program at $PD_DIR" >&2
    echo "Build first: scripts/build_p4.sh" >&2
    exit 1
  fi
fi
