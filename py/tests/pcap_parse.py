#!/usr/bin/env python3
"""
Parse a pcap file and extract ts_h fields from UDP packets to compute latency.
Usage:
  python3 py/tests/pcap_parse.py --pcap results/raw/exp1.pcap --out results/metrics/exp1.csv

Outputs CSV columns: exp_id,seq,ingress_mac_ts,ingress_global_ts,egress_global_ts,qid,latency_ns

Requires scapy: pip install scapy
"""
import argparse
import struct
from scapy.all import rdpcap, UDP

TS_HDR_FMT = '!HIQQQBB'
TS_HDR_LEN = struct.calcsize(TS_HDR_FMT)


def unpack_ts(payload: bytes):
    if len(payload) < TS_HDR_LEN:
        return None
    fields = struct.unpack(TS_HDR_FMT, payload[:TS_HDR_LEN])
    return {
        'exp_id': fields[0],
        'seq': fields[1],
        'ingress_mac_ts': fields[2],
        'ingress_global_ts': fields[3],
        'egress_global_ts': fields[4],
        'qid': fields[5],
        'rsvd': fields[6]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pcap', required=True)
    parser.add_argument('--out', required=False)
    args = parser.parse_args()

    pkts = rdpcap(args.pcap)
    rows = []
    for p in pkts:
        if UDP in p:
            udp = p[UDP]
            payload = bytes(udp.payload)
            ts = unpack_ts(payload)
            if ts:
                latency = None
                if ts['egress_global_ts'] and ts['ingress_global_ts']:
                    latency = ts['egress_global_ts'] - ts['ingress_global_ts']
                rows.append((ts['exp_id'], ts['seq'], ts['ingress_mac_ts'], ts['ingress_global_ts'], ts['egress_global_ts'], ts['qid'], latency))

    if args.out:
        import csv
        with open(args.out, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['exp_id','seq','ingress_mac_ts','ingress_global_ts','egress_global_ts','qid','latency_ns'])
            for r in rows:
                w.writerow(r)
        print(f'Wrote {len(rows)} records to {args.out}')
    else:
        for r in rows[:200]:
            print(r)
        print(f'Total records: {len(rows)}')

if __name__ == '__main__':
    main()
