# Tofino Timestamp Experiment Project (Clean Architecture)

This repository provides a minimal, modular setup to measure latency variance inside a Tofino switch.

- P4 (data plane): stamps timestamps into a custom header and forwards by exp_id
- Python (control plane): starts switchd, configures ports/tables/pktgen, orchestrates experiments
- Bash: environment bootstrapping and build/load wrappers

## Layout

- p4/
  - ts_pipeline.p4: minimal timestamp pipeline
  - include/headers.p4: Ethernet/IPv4/UDP/ts headers
  - build/: outputs from the compiler (conf, context)
- py/
  - core/: bfrt session, ports, tables, pktgen helpers
  - exp/runner.py: bfshell-executable setup script (clear tables, enable one port, add forward)
  - cli.py: convenience wrapper to call runner via bfshell -b
  - config/: topo and pattern/experiment examples
- scripts/
  - env.sh: export SDE paths
  - build_p4.sh: placeholder to compile P4 (edit for your SDE)
  - load_p4.sh: start bf_switchd with generated conf
- results/: place for raw pcaps/metrics/reports

## Quick start

1) Source environment

```bash
source scripts/env.sh
```

2) Build P4 (edit scripts/build_p4.sh to your compiler if needed)

```bash
bash scripts/build_p4.sh
```

3) Load P4 (starts switchd in background)

```bash
bash scripts/load_p4.sh
```

4) Program base tables via bfshell -b

```bash
python3 -m py.cli run
```

This will:
- attach to program `ts_pipeline`
- clear tables
- enable port 16/0
- add forward entry: exp_id=1 -> DEV_PORT(16/0), qid=0

5) Generate traffic (pktgen helper is a stub now) and capture on host NIC.

## Notes
- Timestamps are 64-bit fields in header `ts_h`. Compute latency as egress_global_ts - ingress_global_ts.
- Update `py/config/topo.yaml` to match your front-panel ports.
- Update `scripts/build_p4.sh` to use your exact SDE P4 compiler.
- If you prefer standalone BF-RT Python client instead of bfshell -b, adapt `py/core/bfrt_session.py`.
