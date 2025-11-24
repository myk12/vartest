#!/usr/bin/env python3
##################################################
# traffic_generator.py
##################################################

# Use Tofino traffic generator to generate different types of traffic

import os
import time
from scapy.all import Ether, IP, UDP, Raw
from loguru import logger
logger.remove()
logger.add(lambda msg: print(msg, end=''), level="INFO")

TS_P4_PROG = os.environ.get('TS_P4_PROG', 'ts_pipeline')
# User said the 4th pipeline -> use pipeline index 3 (0-based)
PIPELINE_ID = int(os.environ.get('TS_PIPELINE_ID', 0))  # Default to 4th pipeline
PKTGEN_APP_ID = int(os.environ.get('TS_PKTGEN_APP_ID', 1))  # Default application ID

# Defaults for traffic
packet_size = int(os.environ.get('TS_PKT_SIZE', 1024))  # Size of each packet in bytes
target_rate_Gbps = float(os.environ.get('TS_RATE_GBPS', 10))  # Target rate in Gbps
src_mac = os.environ.get('TS_SRC_MAC', "00:11:22:33:44:55")
dst_mac = os.environ.get('TS_DST_MAC', "66:77:88:99:AA:BB")
src_ip = os.environ.get('TS_SRC_IP', "10.0.0.1")
dst_ip = os.environ.get('TS_DST_IP', "10.0.0.2")
src_port = int(os.environ.get('TS_SRC_PORT', 1234))
dst_port = int(os.environ.get('TS_DST_PORT', 5678))

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
    
    packet = Ether(dst=dst_mac, src=src_mac) / \
            IP(src=src_ip, dst=dst_ip) / \
            UDP(sport=src_port, dport=dst_port) / \
            Raw(load=bytes([0x00] * payload_size))
    
    logger.info(f"Constructed packet of size {len(packet)} bytes")
    logger.info(packet.summary())
    # Show type of packet
    logger.info(f"Packet type: {type(packet)}")
    return packet

def main():
    logger.info("Traffic generator started.")
    # get BF-RT handle from bfshell globals
    if 'bfrt' not in globals():
        raise RuntimeError("BF-RT program handle not found; run via bfshell -b or adapt client init")
    bfrt = globals()['bfrt']
    bfrt_prog = getattr(bfrt, TS_P4_PROG, None)
    if bfrt_prog is None:
        raise RuntimeError(f"Could not find program handle for '{TS_P4_PROG}' in bfshell globals")
    pipe = bfrt_prog.pipe
    
    # Setup tofino2 pktgen
    pg_app = bfrt.tf2.pktgen.app_cfg
    pg_port = bfrt.tf2.pktgen.port_cfg
    pg_buffer = bfrt.tf2.pktgen.pkt_buffer
    
    logger.info("Clearing existing pktgen configuration...")

    ##########################################################
    #  Write packet to pktgen buffer
    ##########################################################
    logger.info("Writing packet to pktgen buffer...")
    made_packet = make_packet(packet_size)
    # convert to integer array
    packet_bytes = list(made_packet.build())
    entry = pg_buffer.entry(pkt_buffer_offset=0, pkt_buffer_size=len(made_packet), buffer=packet_bytes)
    entry.push()
    logger.info("Packet written to pktgen buffer.")
    
    # check pkt_buffer entries
    logger.info("Current pktgen buffer entries:")
    ret_entry = pg_buffer.get(pkt_buffer_offset=0,pkt_buffer_size=len(made_packet), print_ents=True)
    # compare with packet_bytes
    # ret_entry.data is bytearray and packet_bytes is list of int
    print("ret_entry.data type:", type(ret_entry.data))
    print("packet_bytes type:", type(packet_bytes))
    #ret_entry.data type: <class 'dict'>
    #packet_bytes type: <class 'list'>
    assert ret_entry.data[b'buffer'] == packet_bytes, "Pktgen buffer content does not match expected packet"
    logger.info("Pktgen buffer content verified.")

    ##########################################################
    #  Configure pktgen application
    ##########################################################
    logger.info("Configuring pktgen application...")
    """
    entry_with_trigger_timer_periodic(
    app_id=None,
    timer_nanosec=None,
    app_enable=None,
    pkt_len=None,
    pkt_buffer_offset=None,
    pipe_local_source_port=None,
    increment_source_port=None,
    batch_count_cfg=None,
    packets_per_batch_cfg=None,
    ibg=None,
    ibg_jitter=None,
    ipg=None,
    ipg_jitter=None,
    batch_counter=None,
    pkt_counter=None,
    trigger_counter=None,
    offset_len_from_recir_pkt_enable=None,
    source_port_wrap_max=None,
    assigned_chnl_id=None,
)

        app_cfg.trigger_type = PD_PKTGEN_TRIGGER_TIMER_PERIODIC;
        //app_cfg.trigger_type = PD_PKTGEN_TRIGGER_TIMER_ONE_SHOT;
        //app_cfg.trigger_type = PD_PKTGEN_TRIGGER_DPRSR;
    app_cfg.batch_count = 0;
    app_cfg.packets_per_batch = 0;
    app_cfg.timer_nanosec = 1000 * 100;//4294967295;
    app_cfg.ibg = 0;
    app_cfg.ibg_jitter = 0;
    app_cfg.ipg = 0;
    app_cfg.ipg_jitter = 0;
    app_cfg.source_port = 6;
        app_cfg.assigned_chnl_id = 6;
    app_cfg.increment_source_port = false;
    app_cfg.pkt_buffer_offset = 0;
    app_cfg.length = 100;
    """
    
    
    app = pg_app.entry_with_trigger_timer_periodic(
        app_id=PKTGEN_APP_ID,
        timer_nanosec=get_timer_nanosec(packet_size, target_rate_Gbps),
        app_enable=True,
        pkt_len=packet_size,
        pkt_buffer_offset=0,
        pipe_local_source_port=6,
        increment_source_port=False,
        batch_count_cfg=1,
        packets_per_batch_cfg=1,
        ibg=0,
        ibg_jitter=0,
        ipg=0,
        ipg_jitter=0,
        batch_counter=0,
        pkt_counter=0,
        trigger_counter=0,
        offset_len_from_recir_pkt_enable=False,
        source_port_wrap_max=0,
        assigned_chnl_id=6,
    )
    logger.info("Pktgen application configured and started.")
    app.push()
    
if __name__ == '__main__':
    main()
