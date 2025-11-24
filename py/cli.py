#!/usr/bin/env python3
"""
Simple CLI wrapper to orchestrate common tasks from outside bfshell.
Note: Direct BF-RT control here depends on your SDE's Python client; as a
portable baseline, we use bfshell -b to execute our Python runner.
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
SCRIPTS = os.path.join(ROOT, 'scripts')


def run_experiment(args):
    # Execute our runner inside bfshell -b so that `bfrt` is available
    runner = os.path.join(ROOT, 'py', 'exp', 'runner.py')
    cmd = ['bfshell', '-b', runner]
    print('Running:', ' '.join(cmd))
    subprocess.check_call(cmd)


def collect(args):
    print("[TODO] Implement packet capture or register snapshot collection.")


def analyze(args):
    print("[TODO] Implement analysis to compute latency variance from collected data.")


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_run = sub.add_parser('run', help='Run experiment orchestration')
    p_run.add_argument('--experiment', required=False, help='Experiment YAML (reserved for future)')
    p_run.set_defaults(func=run_experiment)

    p_collect = sub.add_parser('collect', help='Collect PCAP/registers to CSV')
    p_collect.add_argument('--input', required=False)
    p_collect.add_argument('--out', required=False)
    p_collect.set_defaults(func=collect)

    p_an = sub.add_parser('analyze', help='Analyze metrics to compute variance')
    p_an.add_argument('--input', required=False)
    p_an.set_defaults(func=analyze)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
