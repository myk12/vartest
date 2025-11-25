#!/bfshell/bin/env python3
# -*- coding: utf-8 -*-
# author: Yuke Ma
# date: 2024-06-15
# description: Tofino switch setup utility for latency probing


# This script sets up the Tofino switch according to incoming parameters for latency probing tests.
# 1. Configure forwarding rules based on the specified traffic pattern.
# 2. This script is invoked by the probe_main.py before starting the latency probing.

import os
import sys
import argparse
import yaml
from scapy.all import Ether, IP, UDP, Raw
from loguru import logger
logger.remove()
logger.add(sys.stdout, level="INFO")

P4_PROG = os.environ.get('TS_P4_PROG', 'ts_pipeline')
PKTGEN_APP_ID = int(os.environ.get('TS_PKTGEN_APP_ID', '1'))  # Default application ID

# Defaults for packet
PACKET_SIZE = int(os.environ.get('TS_PKT_SIZE', '1024'))  # Size of each packet in bytes
TARGET_RATE_Gbps = float(os.environ.get('TS_RATE_GBPS', '100'))  # Target rate in Gbps
SRC_MAC = os.environ.get('TS_SRC_MAC', "00:11:22:33:44:55")
DST_MAC = os.environ.get('TS_DST_MAC', "66:77:88:99:AA:BB")
SRC_IP = os.environ.get('TS_SRC_IP', "10.0.0.1")
DST_IP = os.environ.get('TS_DST_IP', "10.0.0.2")
SRC_PORT = int(os.environ.get('TS_SRC_PORT', '1234'))
DST_PORT = int(os.environ.get('TS_DST_PORT', '5678'))
TOPO_YAML_PATH = os.environ.get('TS_TOPO_YAML', '/home/p4/vartest/tofino/topo.yaml')

def get_timer_nanosec(pkt_size: int, rate_Gbps: float) -> int:
    """
    Calculate inter-packet timer in nanoseconds based on packet size and target rate.
    Args:
        pkt_size (int): Size of the packet in bytes.
        rate_Gbps (float): Target rate in Gbps.
    Returns:
        int: Timer value in nanoseconds.
    """
    if rate_Gbps <= 0:
        raise ValueError("Rate must be greater than 0 Gbps")

    total_bytes = pkt_size + 20  # Adding overhead bytes
    total_bits = total_bytes * 8
    
    # Rate is in Gbps
    time_ns = total_bits / rate_Gbps    # in nanoseconds
    return int(time_ns)

def make_packet(size: int) -> Ether:
    if size < 14:
        raise ValueError("Packet size must be at least 14 bytes for Ethernet header")
    
    # subtract packet header size: Ethernet (14 bytes) + IP (20 bytes) + UDP (8 bytes)
    payload_size = size - 14 - 20 - 8
    if payload_size < 0:
        raise ValueError("Packet size too small for headers")
    
    packet = Ether(dst=DST_MAC, src=SRC_MAC) / \
            IP(src=SRC_IP, dst=DST_IP) / \
            UDP(sport=SRC_PORT, dport=DST_PORT) / \
            Raw(load=bytes([0x00] * payload_size))
    return packet

def parser_topology(bfrt, yaml_path: str) -> dict:
    """Parse topology YAML file to get device and port mappings."""
    with open(yaml_path, 'r') as f:
        topo = yaml.safe_load(f)
    
    topo_config = {}
    
    # parse ports info
    topo_ports = {}
    for name, spec, in topo.get('ports', {}).items():
        port_attrs = {}
        port_attrs['conn_id'] = int(spec.get('conn_id'))
        port_attrs['chnl_id'] = int(spec.get('chnl_id'))
        port_attrs['FPGA'] = bool(spec.get('FPGA', False))

        # get dev port
        dev_port = bfrt.port.port_hdl_info.get(CONN_ID=port_attrs['conn_id'], CHNL_ID=port_attrs['chnl_id']).data[b'$DEV_PORT']
        port_attrs['dev_port'] = int(dev_port)
        topo_ports[name] = port_attrs
    topo_config['ports'] = topo_ports
    
    # add special port pktgen
    topo_config['ports']['pktgen'] = {
        'conn_id': 6,
        'chnl_id': 0,
        'FPGA': False,
        'dev_port': 6 # FIXME: hardcoded dev port for pktgen
    }

    # parse farwading rules info
    topo_fwd_rules = {}
    for name, spec in topo.get('fwd_rules', {}).items():
        fwd_rule_attrs = {}
        bi_dir_rules = []
        for rule in spec.get('bi-directional', []):
            bi_dir_rules.append((rule[0], rule[1]))
        fwd_rule_attrs['bi-directional'] = bi_dir_rules

        uni_dir_rules = []
        for rule in spec.get('uni-directional', []):
            uni_dir_rules.append((rule[0], rule[1]))
        fwd_rule_attrs['uni-directional'] = uni_dir_rules

        topo_fwd_rules[name] = fwd_rule_attrs
    topo_config['fwd_rules'] = topo_fwd_rules

    return topo_config

def config_SINGLE_pattern(bfrt, topo_config):
    """Configure switch for SINGLE pattern."""
    logger.info("Configuring switch for SINGLE pattern...")
    # Add specific configuration for SINGLE pattern
    fwd_rules = topo_config.get('fwd_rules', {}).get('SINGLE', {})
    fwd_table = bfrt.ts_pipeline.pipe.Ingress.pass_through
    
    for src_port_name, dst_port_name in fwd_rules.get('bi-directional', []):
        src_port = topo_config['ports'][src_port_name]['dev_port']
        dst_port = topo_config['ports'][dst_port_name]['dev_port']
        logger.info(f"Adding bi-directional rule: {src_port_name} ({src_port}) <-> {dst_port_name} ({dst_port})")
        # Add table entries to bfrt here
        try:
            fwd_table.add_with_set_port(ingress_port=src_port, egress_port=dst_port)
            fwd_table.add_with_set_port(ingress_port=dst_port, egress_port=src_port)
        except Exception as e:
            logger.error(f"Failed to add table entry: {e}")
    
    for src_port_name, dst_port_name in fwd_rules.get('uni-directional', []):
        src_port = topo_config['ports'][src_port_name]['dev_port']
        dst_port = topo_config['ports'][dst_port_name]['dev_port']
        logger.info(f"Adding uni-directional rule: {src_port_name} ({src_port}) -> {dst_port_name} ({dst_port})")
        # Add table entries to bfrt here
        try:
            fwd_table.add_with_set_port(ingress_port=src_port, egress_port=dst_port)
        except Exception as e:
            logger.error(f"Failed to add table entry: {e}")

def config_MULTIPLE_pattern(bfrt, topo_config):
    """Configure switch for MULTIPLE pattern."""
    logger.info("Configuring switch for MULTIPLE pattern...")
    # Add specific configuration for MULTIPLE pattern
    fwd_rules = topo_config.get('fwd_rules', {}).get('MULTIPLE', {})
    fwd_table = bfrt.ts_pipeline.pipe.Ingress.pass_through
    for src_port_name, dst_port_name in fwd_rules.get('bi-directional', []):
        src_port = topo_config['ports'][src_port_name]['dev_port']
        dst_port = topo_config['ports'][dst_port_name]['dev_port']
        logger.info(f"Adding bi-directional rule: {src_port_name} ({src_port}) <-> {dst_port_name} ({dst_port})")
        # Add table entries to bfrt here
        try:
            fwd_table.add_with_set_port(ingress_port=src_port, egress_port=dst_port)
            fwd_table.add_with_set_port(ingress_port=dst_port, egress_port=src_port)
        except Exception as e:
            logger.error(f"Failed to add table entry: {e}")

def configure_switch(bfrt, topo_config, pattern, rate, packet_size):
    """Configure the Tofino switch according to the specified parameters."""
    logger.info(f"Setting pattern: {pattern}, rate: {rate} pps, packet size: {packet_size} bytes")

    # Example configuration logic based on pattern
    if pattern == "SINGLE":
        logger.info("Configuring SINGLE pattern...")
        config_SINGLE_pattern(bfrt, topo_config)
    elif pattern == "MULTIPLE":
        logger.info("Configuring MULTIPLE pattern...")
        config_MULTIPLE_pattern(bfrt, topo_config)
    else:
        logger.error(f"Unsupported pattern: {pattern}")
        sys.exit(1)
    
    # Config pktgen settings

    logger.info("Switch configured successfully.")

def main():
    """Main function to configure the switch."""
    logger.info("Configuring switch with new parameters...")
    # Assuming bfshell environment is already set up
    if 'bfrt' not in globals():
        logger.error("This script must be run within the bfshell environment.")
        sys.exit(1)
    bfrt = globals()['bfrt']

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Configure Tofino switch for latency probing.")
    parser.add_argument('--pattern', type=str, required=True, help='Traffic pattern (e.g., SINGLE, MULTIPLE)')
    parser.add_argument('--rate', type=int, required=True, help='Packet sending rate (packets per second)')
    parser.add_argument('--packet_size', type=int, required=True, help='Size of each packet (bytes)')
    args = parser.parse_args()

    pattern = args.pattern
    rate = args.rate
    packet_size = args.packet_size

    logger.info(f"Setting pattern: {pattern}, rate: {rate} pps, packet size: {packet_size} bytes")
    topo_config = parser_topology(bfrt, TOPO_YAML_PATH)
    configure_switch(bfrt, topo_config, pattern, rate, packet_size)

if __name__ == "__main__":
    main()
