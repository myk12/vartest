#!/bin/python3
# -*- coding: utf-8 -*-
# author: Yuke Ma
# date: 2024-06-15
# description: Tofino switch setup utility for latency probing

# This script sets up the Tofino switch according incoming parameters for latency probing tests.
# 1. Reset the switch to a known state.
# 2. Configure forwarding rules based on the specified traffic pattern.
# 3. This script is invoked by the probe_main.py before starting the latency probing.

# This script will call scripts located in the remote tofino switch server via network.
import os
import subprocess
import paramiko
from loguru import logger

def clear_switch(ssh_client, context: dict):
    """Clear existing configurations on the Tofino switch."""
    logger.info("Clearing existing switch configurations...")
    SDE_PATH = context.get("SDE_PATH", "/home/p4/sde")
    SDE_INSTALL_PATH = context.get("SDE_INSTALL_PATH", "/home/p4/sde/install")
    CLEAR_SCRIPT_PATH = context.get("CLEAR_SCRIPT_PATH", "/home/p4/vartest/tofino/bfrt_utils/clear_switch.py")

    clear_cmd = f"export SDE_PATH={SDE_PATH} && " \
                f"export SDE_INSTALL_PATH={SDE_INSTALL_PATH} && " \
                f"bfshell -b {CLEAR_SCRIPT_PATH}"
    
    stdin, stdout, stderr = ssh_client.exec_command(clear_cmd)
    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        logger.info("Switch configurations cleared successfully.")
    else:
        logger.error(f"Failed to clear switch configurations. Error: {stderr.read().decode()}")
        raise RuntimeError("Switch configuration clearing failed.")

def config_switch(ssh_client, context: dict):
    """Configure the Tofino switch according to the specified parameters."""
    logger.info("Configuring switch with new parameters...")
    SDE_PATH = context.get("SDE_PATH", "/home/p4/sde")
    SDE_INSTALL_PATH = context.get("SDE_INSTALL_PATH", "/home/p4/sde/install")
    CONFIG_SCRIPT_PATH = context.get("CONFIG_SCRIPT_PATH", "/home/p4/vartest/tofino/bfrt_utils/config_switch.py")

    try:
        pattern = context["pattern"]
        rate = context["rate"]
        packet_size = context["packet_size"]
    except KeyError as e:
        logger.error(f"Missing configuration parameter: {e}")
        raise

    config_cmd = f"export SDE_PATH={SDE_PATH} &&  " \
                 f"export SDE_INSTALL_PATH={SDE_INSTALL_PATH} && " \
                 f"bfshell -b {CONFIG_SCRIPT_PATH} " \
                 f"--pattern {pattern} --rate {rate} --packet_size {packet_size}"
                 
    stdin, stdout, stderr = ssh_client.exec_command(config_cmd)
    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        logger.info("Switch configured successfully.")
    else:
        logger.error(f"Failed to configure switch. Error: {stderr.read().decode()}")
        raise RuntimeError("Switch configuration failed.")

def setup_switch(ssh_client, context: dict):
    """Setup the Tofino switch according to the specified parameters."""
    clear_switch(ssh_client, context)
    config_switch(ssh_client, context)

if __name__ == "__main__":
    # Example usage
    SSH_HOST = os.getenv("TOFINO_SSH_HOST", "10.0.13.21")
    SSH_USER = os.getenv("TOFINO_SSH_USER", "p4")
    SSH_PASSWORD = os.getenv("TOFINO_SSH_PASSWORD", "rocks")
    pattern = "uniform"
    rate = 100
    packet_size = 128
    #setup_switch(SSH_HOST, SSH_USER, SSH_PASSWORD, pattern, rate, packet_size)