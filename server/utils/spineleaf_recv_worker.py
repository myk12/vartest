#!/usr/bin/env python3
from scapy.all import *
import pandas as pd
import struct

# define custom packet structures
class ProbeHeader(Packet):
    name = "ProbeHeader"
    fields_desc = [
        ByteField("sender_id", 0),
        IntField("seq_no", 0),
        ByteField("hop_count", 0)
    ]

class HopData(Packet):
    name = "HopData"
    fields_desc = [
        ByteField("switch_id", 0),
        BitField("ingress_ts", 0, 64),
        BitField("egress_ts", 0, 64),
        ShortField("port_id", 0)
    ]

# bind layers
bind_layers(UDP, ProbeHeader, dport=7777)
bind_layers(ProbeHeader, HopData)
bind_layers(HopData, HopData)

results = []

def process_packet(pkt):
    if ProbeHeader in pkt:
        probe = pkt[ProbeHeader]
        
        current_layer = probe.payload
        hop_idx = 0
        
        while HopData in current_layer and hop_idx < probe.hop_count:
            hop = current_layer
            
            # 计算停留时间 (Residence Time)
            residence_ns = hop.egress_ts - hop.ingress_ts
            
            record = {
                "sender_id": probe.sender_id,
                "seq_no": probe.seq_no,
                "hop_idx": hop_idx,
                "switch_id": hop.switch_id,
                "port_id": hop.port_id,
                "ingress_ts": hop.ingress_ts,
                "residence_ns": residence_ns
            }
            results.append(record)
            
            current_layer = hop.payload
            hop_idx += 1

def start_sniffing(timeout=10):
    print("Listening for telemetry packets...")
    sniff(filter="udp port 7777", prn=process_packet, timeout=timeout)
    
    # 转换为 DataFrame 进行分析
    df = pd.DataFrame(results)
    if not df.empty:
        print("\n=== Latency Profile ===")
        print(df.groupby("switch_id")["residence_ns"].describe())
        
        # 可以在这里保存 csv
        df.to_csv("latency_profile.csv", index=False)
        print("Saved to latency_profile.csv")
    else:
        print("No data received.")

if __name__ == "__main__":
    start_sniffing(timeout=20)