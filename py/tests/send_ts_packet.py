#!/usr/bin/env python3
"""
Send UDP experiment packets with custom ts_h payload for testing ts_pipeline.p4.
Usage example (run from a host connected to the switch front-panel):

sudo python3 py/tests/send_ts_packet.py --iface eth0 --dst-mac aa:bb:cc:dd:ee:ff \
    --dst-ip 192.0.2.2 --dst-port 12345 --exp-id 100 --seq-start 1 --count 100

This script crafts Ethernet/IPv4/UDP packets where UDP payload begins with the
32-byte ts_h defined in p4/include/headers.p4:
  - exp_id (16)
  - seq (32)
  - ingress_mac_ts (64)
  - ingress_global_ts (64)
  - egress_global_ts (64)
  - qid (8)
  - rsvd (8)

We set the three timestamp fields to zero on transmit (switch will fill ingress/egress timestamps).

Note: requires scapy. Install with `pip install scapy` or via system package.
"""
import argparse
import struct
from scapy.all import Ether, IP, UDP, Raw, sendp

TS_HDR_FMT = '!HIQQQBB'  # exp_id:H, seq:I, three Qs, qid:B, rsvd:B
TS_HDR_LEN = struct.calcsize(TS_HDR_FMT)  # should be 32

def build_ts_payload(exp_id: int, seq: int, qid: int = 0):
    # ingress/egress timestamps zeroed on transmit
    ingress_mac_ts = 0
    ingress_global_ts = 0
    egress_global_ts = 0
    rsvd = 0
    return struct.pack(TS_HDR_FMT, exp_id, seq, ingress_mac_ts, ingress_global_ts, egress_global_ts, qid, rsvd)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--iface', required=True)
    parser.add_argument('--dst-mac', required=True)
    parser.add_argument('--src-mac', required=False)
    parser.add_argument('--dst-ip', required=True)
    parser.add_argument('--src-ip', default='198.51.100.1')
    parser.add_argument('--dst-port', type=int, default=12345)
    parser.add_argument('--exp-id', type=int, default=100)
    parser.add_argument('--seq-start', type=int, default=1)
    parser.add_argument('--count', type=int, default=10)
    parser.add_argument('--pkt-bytes', type=int, default=256)
    args = parser.parse_args()

    paylen = args.pkt_bytes - 14 - 20 - 8 - TS_HDR_LEN  # adjust for eth/ip/udp/ts header
    if paylen < 0:
        raise SystemExit('pkt-bytes too small for headers')

    for i in range(args.count):
        seq = args.seq_start + i
        ts_payload = build_ts_payload(args.exp_id, seq, qid=0)
        user_payload = b'X' * paylen
        payload = ts_payload + user_payload
        eth = Ether(dst=args.dst_mac)
        if args.src_mac:
            eth.src = args.src_mac
        pkt = eth / IP(src=args.src_ip, dst=args.dst_ip) / UDP(sport=1234, dport=args.dst_port) / Raw(load=payload)
        sendp(pkt, iface=args.iface, verbose=False)
        if (i+1) % 10 == 0:
            print(f"Sent {i+1} packets")

    print('Done')


if __name__ == '__main__':
    main()
