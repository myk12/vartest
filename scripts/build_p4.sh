#!/usr/bin/env bash
set -euo pipefail

# Build P4 program using either SDE-provided tools or a local p4c.
# This script supports two modes selected by BUILD_MODE:
#  - tools  : use the SDE/tooling wrapper (default). This places build artifacts
#             into the SDE share area or managed output as the tool does.
#  - local  : use a local p4 compiler (p4c / bf-p4c) and write artifacts into
#             the project build directory (more reproducible & repo-friendly).
#
# Usage examples:
#  BUILD_MODE=tools   ./scripts/build_p4.sh
#  BUILD_MODE=local   ./scripts/build_p4.sh
#
# This script expects you have sourced scripts/env.sh which populates SDE_INSTALL
# and other useful variables. When BUILD_MODE=local SDE_INSTALL is optional.

: "${TS_P4_DIR:?TS_P4_DIR must be set (path to p4 sources)}"
: "${TS_P4_BUILD:?TS_P4_BUILD must be set (output build directory)}"

# Optional variables with sensible defaults
: "${TS_P4_PROG:=ts_pipeline}"
: "${BUILD_MODE:=tools}"
: "${BUILD_TOOL:=}" # optional path to tools/p4_build wrapper

P4SRC="$TS_P4_DIR/ts_pipeline.p4"
P4NAME="$TS_P4_PROG"
OUTDIR="$TS_P4_BUILD"

mkdir -p "$OUTDIR"

echo "Building $P4SRC as program '$P4NAME' into $OUTDIR (mode=$BUILD_MODE)"

if [ "$BUILD_MODE" = "tools" ]; then
    "${BUILD_TOOL%/}/p4_build.sh" "$P4SRC" --with-tofino2
elif [ "$BUILD_MODE" = "local" ]; then
	# Try common compiler names in order.
	if command -v bf-p4c >/dev/null 2>&1; then
		echo "Using bf-p4c (target-specific)"
		bf-p4c -o "$OUTDIR" -p "$P4NAME" "$P4SRC"
	elif command -v p4c >/dev/null 2>&1; then
		echo "Using p4c"
		# p4c options vary by backend; users should edit the flags for their target.
		p4c -o "$OUTDIR" "$P4SRC"
	else
		echo "[ERROR] BUILD_MODE=local but no p4 compiler found (bf-p4c or p4c). Install p4c or set BUILD_MODE=tools." >&2
		exit 1
	fi
else
	echo "[ERROR] Unknown BUILD_MODE='$BUILD_MODE'. Supported: tools, local" >&2
	exit 2
fi

echo "[OK] Build completed. Artifacts in $OUTDIR"
