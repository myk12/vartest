"""

"""

import os
import sys
import typing
from typing import Any
from loguru import logger
from scapy.all import Ether, IP, UDP, Raw

logger.remove()
logger.add(sys.stdout, level="INFO")

##################################################
#                 Configuration
##################################################
# Adjust sys.path to include py/ directory if not already present
py_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if py_dir not in sys.path:
    sys.path.insert(0, py_dir)

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

def setup_single_port_pktgen(bfrt: Any) -> None:
    """Setup single-port packet generator using pktgen BF-RT API."""
    logger.info("Setting up single-port pktgen...")
    
    # Add forwarding table entries to loopback on a single port
    # ingress port 6 and 68 to egress port of channel 25 and 26
    pktgen_origin_ports = [6, 68]
    forward_dest_conn = [25, 26]
    forward_table = bfrt.ts_pipeline.pipe.Ingress.pass_through
    
    p25_dp = bfrt.port.port_hdl_info.get(CONN_ID=forward_dest_conn[0], CHNL_ID=0).data[b'$DEV_PORT']
    p26_dp = bfrt.port.port_hdl_info.get(CONN_ID=forward_dest_conn[1], CHNL_ID=0).data[b'$DEV_PORT']
    
    # Setup forwarding entries
    for src_port in pktgen_origin_ports:
        for dst_dp in [p25_dp, p26_dp]:
            try:
                entry = forward_table.add_with_set_port(
                    ingress_port=src_port,
                    egress_port=dst_dp
                )
            except Exception as e:
                msg = str(e)
                if 'Already exists' in msg or 'already exists' in msg:
                    logger.warning(f"Forwarding entry for ingress_port={src_port} already exists.")
                else:
                    logger.error(f"Error adding forwarding entry for ingress_port={src_port}: {e}")
                    raise e
    logger.info("Pktgen single-port setup complete.")

    # Enable the ports used for pktgen
    pktgen_app = bfrt.tf2.pktgen.app_cfg
    pktgen_buffer = bfrt.tf2.pktgen.pkt_buffer
    pktgen_port = bfrt.tf2.pktgen.port_cfg
    logger.info("Enabling pktgen ports...")
    
    # 1. write packet to pktgen buffer
    logger.info("Writing packet to pktgen buffer...")
    made_packet = make_packet(PACKET_SIZE)
    packet_bytes = list(made_packet.build())
    buffer_entry = pktgen_buffer.entry(
        pkt_buffer_offset=0,
        pkt_buffer_size=len(made_packet),
        buffer=packet_bytes
    )
    buffer_entry.push()
    logger.info("Packet written to pktgen buffer.")
    
    # 2. configure pktgen application
    timer_ns = get_timer_nanosec(PACKET_SIZE, TARGET_RATE_Gbps)
    app_entry = pktgen_app.entry_with_trigger_timer_periodic(
        app_id=PKTGEN_APP_ID,
        timer_nanosec=timer_ns,
        app_enable=True,
        pkt_len=PACKET_SIZE,
        pkt_buffer_offset=0,
        pipe_local_source_port=6,  # Use first port as source
        increment_source_port=False,
        batch_count_cfg=1,
        packets_per_batch_cfg=1,
        ibg=0, ibg_jitter=0,
        ipg=0, ipg_jitter=0,
        batch_counter=0,
        pkt_counter=0,
        trigger_counter=0,
        offset_len_from_recir_pkt_enable=False,
        source_port_wrap_max=0,
        assigned_chnl_id=6,
    )
    app_entry.push()
    logger.info("Pktgen application configured and started.")
    
    # 3. enable pktgen ports
    logger.info("Enabling pktgen ports...")
    port_entry = pktgen_port.entry(
        dev_port=6,
        pktgen_enable=True
    )
    port_entry.push()
    logger.info("Pktgen ports enabled.")

def main():
    logger.info("Starting single-port traffic generator...")

    if 'bfrt' not in globals():
        logger.error("This script must be run inside bfshell with -b option.")
        sys.exit(1)
    bfrt = globals()['bfrt']
    
    setup_single_port_pktgen(bfrt)

if __name__ == "__main__":
    main()

