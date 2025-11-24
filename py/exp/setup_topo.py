"""
Basic Setup module for the topology which:
    1. Sets up ports based on a provided topology YAML file.
    2. Programs pass-through entries for health checking.
"""
import os
import sys
import yaml
from loguru import logger
from scapy.all import Ether, IP, UDP, Raw

logger.remove()
logger.add(sys.stdout, level="INFO")

# Ensure `py` dir is on sys.path so `from core...` works when executed by
# `bfshell -b` which typically runs with a different CWD (the SDE install dir).
# Prefer a path relative to this script file so imports work regardless of cwd.
script_dir = os.path.dirname(os.path.abspath(__file__))
candidate_py = os.path.abspath(os.path.join(script_dir, '..'))
if os.path.isdir(candidate_py) and candidate_py not in sys.path:
    sys.path.insert(0, candidate_py)
else:
    # fallback to cwd-based layout (useful when running outside bfshell)
    py_dir = os.path.join(os.getcwd(), 'py')
    if os.path.isdir(py_dir) and py_dir not in sys.path:
        sys.path.insert(0, py_dir)

P4_PROG = os.environ.get('TS_P4_PROG', 'ts_pipeline')
TOPO_PATH = os.environ.get('TS_TOPO_YAML', os.path.join(os.path.dirname(__file__), '..', 'config', 'topo.yaml'))

PKTGEN_APP_ID = int(os.environ.get('TS_PKTGEN_APP_ID', 1))  # Default application ID

# Defaults for traffic
PACKET_SIZE = int(os.environ.get('TS_PKT_SIZE', 1024))  # Size of each packet in bytes
TARGET_RATE_Gbps = float(os.environ.get('TS_RATE_GBPS', 10))  # Target rate in Gbps
SRC_MAC = os.environ.get('TS_SRC_MAC', "00:11:22:33:44:55")
DST_MAC = os.environ.get('TS_DST_MAC', "66:77:88:99:AA:BB")
SRC_IP = os.environ.get('TS_SRC_IP', "10.0.0.1")
DST_IP = os.environ.get('TS_DST_IP', "10.0.0.2")
SRC_PORT = int(os.environ.get('TS_SRC_PORT', 1234))
DST_PORT = int(os.environ.get('TS_DST_PORT', 5678))

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

"""
Create a sample packet of specified size using Scapy.
"""
def make_packet(size: int) -> Ether:
    payload_size = size - 14 - 20 - 8
    if payload_size < 0:
        raise ValueError("Packet size too small for headers")
    
    packet = Ether(dst=DST_MAC, src=SRC_MAC) / \
            IP(src=SRC_IP, dst=DST_IP) / \
            UDP(sport=SRC_PORT, dport=DST_PORT) / \
            Raw(load=bytes([0x17] * payload_size))

    return packet
    
def main():
    logger.info("Starting health check...")
    
    # Obtain the BF-RT program handle. Prefer the helper, but fall back to
    # symbols injected by bfshell (e.g., `ts_pipeline`) when executing via
    # `bfshell -b` where `bfrt` may not be present in the script globals.
    if 'bfrt' not in globals():
        raise RuntimeError("BF-RT program handle not found; run via bfshell -b or adapt client init")
    bfrt = globals()['bfrt']
    bfrt_prog = getattr(bfrt, P4_PROG, None)
    if bfrt_prog is None:
        raise RuntimeError(f"Could not find program handle for '{P4_PROG}' in bfshell globals")
    
    logger.info(f"Using P4 program: {P4_PROG}")
    logger.info(f"Using topology YAML: {TOPO_PATH}")
    with open(TOPO_PATH, 'r') as f:
        topo = yaml.safe_load(f) or {}
    
    # Enable requested ports
    logger.info("Enabling ports from topology...")
    port_map = {}
    for name, spec in topo.get('ports', {}).items():
        port_attrs = {}
        port_attrs["conn_id"] = int(spec['conn_id'])
        port_attrs["chnl_id"] = int(spec['chnl_id'])
        port_attrs["FPGA"] = bool(spec.get('FPGA', False))
        
        # get dev port
        dev_port = bfrt.port.port_hdl_info.get(CONN_ID=int(spec['conn_id']),
                                         CHNL_ID=int(spec['chnl_id']),
                                         print_ents=False).data[b'$DEV_PORT']
        dp = int(dev_port)
        port_attrs['dev_port'] = dp
        
        if port_attrs["FPGA"]:
            logger.info(f"  Configuring port {name} as FPGA port")
            bfrt.port.port.add(DEV_PORT=dp,
                            SPEED='BF_SPEED_100G',
                            FEC='BF_FEC_TYP_RS',
                            AUTO_NEGOTIATION='PM_AN_FORCE_DISABLE',
                            PORT_ENABLE=True)
        else:
            logger.info(f"  Configuring port {name} as non-FPGA port")
            bfrt.port.port.add(DEV_PORT=dp,
                            SPEED='BF_SPEED_100G',
                            FEC='BF_FEC_TYP_NONE',
                            AUTO_NEGOTIATION='PM_AN_FORCE_DISABLE',
                            PORT_ENABLE=True)

        port_map[name] = port_attrs
        logger.info(f"  Enabled port {name}: CONN_ID={spec['conn_id']}, CHNL_ID={spec['chnl_id']}, DEV_PORT={dp}")

    # Program pass-through entries for health check
    logger.info("Programming pass-through entries for health check...")
    for pair in topo.get('pairs', []):
        a = pair[0]
        b = pair[1]
        dp_a = port_map[a]['dev_port']
        dp_b = port_map[b]['dev_port']
        
        logger.info(f"  Setting up pass-through between port-{pair[0]} (DEV_PORT {dp_a}) and port-{pair[1]} (DEV_PORT {dp_b})")

        t = bfrt.ts_pipeline.pipe.Ingress.pass_through
        try:
            t.add_with_set_port(ingress_port=dp_a, egress_port=dp_b)
        except Exception as e:
            msg = str(e)
            if 'Already exists' in msg or 'already exists' in msg:
                logger.warning(f"Pass-through entry for {dp_a}->{dp_b} already exists; skipping add")
            else:
                logger.exception(f"Failed to add pass-through {dp_a}->{dp_b}")
                raise

        try:
            t.add_with_set_port(ingress_port=dp_b, egress_port=dp_a)
        except Exception as e:
            msg = str(e)
            if 'Already exists' in msg or 'already exists' in msg:
                logger.warning(f"Pass-through entry for {dp_b}->{dp_a} already exists; skipping add")
            else:
                logger.exception(f"Failed to add_pass-through {dp_b}->{dp_a}")
                raise

        logger.info(f"  Programmed pass-through between port-{pair[0]} (DEV_PORT {dp_a}) and port-{pair[1]} (DEV_PORT {dp_b})")
    
    logger.info("Setup Summary:")
    for name, attrs in port_map.items():
        logger.info(f"  Port {name}: CONN_ID={attrs['conn_id']}/CHNL_ID={attrs['chnl_id']}/DEV_PORT={attrs['dev_port']}")
    logger.info("Health check setup complete.")

    '''
    # Program pktgen bg forwaring: map pktgen app ids to egress ports 32 and 31
    # We'll map app_id 1 -> egress DEV_PORT for CONN_ID 32, app_id 2 -> CONN_ID 31
    logger.info("Prgramming pktgen app to egress port mapping...")
    tbl_bg = bfrt.ts_pipeline.pipe.Ingress.bg_forward
    
    bg_mappings = [(1, 32), (2, 31)]
    for app_id, conn_id in bg_mappings:
        dp_eg = bfrt.port.port_hdl_info.get(CONN_ID=conn_id, CHNL_ID=0, print_ents=False).data[b'$DEV_PORT']
        try:
            tbl_bg.add_with_set_bg_port(app_id=app_id, egress_port=int(dp_eg))
        except Exception as e:
            msg = str(e)
            if 'Already exists' in msg or 'already exists' in msg:
                logger.warning(f"bg_forward entry for app_id {app_id} -> DEV_PORT {dp_eg} already exists; skipping add")
            else:
                logger.exception(f"Failed to add bg_forward for app_id {app_id} -> DEV_PORT {dp_eg}")
                raise
        logger.info(f"  Mapped pktgen app_id {app_id} to egress CONN_ID {conn_id} (DEV_PORT {dp_eg})")

    # Start Pktgen
    pg_app = bfrt.tf2.pktgen.app_cfg
    pg_buffer = bfrt.tf2.pktgen.pkt_buffer
    pg_port = bfrt.tf2.pktgen.port_cfg
    
    logger.info("Starting pktgen...")

    
    # Write packet to pktgen buffer
    logger.info("Writing packet to pktgen buffer...")
    made_packet = make_packet(PACKET_SIZE)
    packet_bytes = list(made_packet.build())
    entry = pg_buffer.entry(pkt_buffer_offset=0, pkt_buffer_size=len(made_packet), buffer=packet_bytes)
    entry.push()
    logger.info("Packet written to pktgen buffer.")
    
    # Configure pktgen application
    logger.info("Configuring pktgen application...")
    timer_ns = get_timer_nanosec(PACKET_SIZE, TARGET_RATE_Gbps)
    logger.info(f"Calculated timer interval: {timer_ns} ns for target rate {TARGET_RATE_Gbps} Gbps")
    app_entry = pg_app.entry_with_trigger_timer_periodic(
        app_id=PKTGEN_APP_ID,
        timer_nanosec=timer_ns,
        app_enable=True,
        pkt_len=PACKET_SIZE,
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
    app_entry.push()
    logger.info("Pktgen application configured and started.")

    # Configure pktgen port
    logger.info("Configuring pktgen port...")
    port_entry = pg_port.entry(
        dev_port=6,
        pktgen_enable=True
    )
    port_entry.push()
    logger.info("Pktgen port configured and enabled.")
    logger.info("Pktgen started successfully.")
    '''
    # Final summary
    logger.info("Setup complete. Summary:")
    logger.info(f"  P4 Program: {P4_PROG}")
    logger.info(f"  Topology YAML: {TOPO_PATH}")
    logger.info(f"  Packet Size: {PACKET_SIZE} bytes")
    logger.info(f"  Target Rate: {TARGET_RATE_Gbps} Gbps")

if __name__ == '__main__':
    main()
