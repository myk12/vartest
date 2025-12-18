#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# author: Yuke Ma
# date: 2025-12-17
# description: Tofino Spine-Leaf Topology Probe Packet Sender Script
# This script sends probe packets from a specified sender to a target IP address
# in a spine-leaf topology. The packets contain a custom header for tracking
# sequence numbers and hop counts, as well as placeholders for timestamps
# collected at each hop in the network.
import sys
import time
import struct
import argparse
from scapy.all import Ether, IP, UDP, Raw, sendp, Packet, ByteField, IntField, ShortField, BitField

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

def send_probes(target_mac, target_ip, sender_id, interface, count=100, interval=0.1):
    print(f"Sending {count} probe packets from sender {sender_id} to {target_ip} on interface {interface}...")
    # Prepare the packet template with custom headers
    # Leave space for hop data for up to 4 hops
    empty_hops = HopData()
    for _ in range(3):
        empty_hops = empty_hops / HopData()
    
    for seq in range(count):
        pkt = Ether(dst=target_mac) / \
              IP(dst=target_ip) / \
              UDP(dport=7777) / \
              ProbeHeader(sender_id=sender_id, seq_no=seq, hop_count=0) / \
              empty_hops / \
              Raw("PAYLOAD_PADDING")
              
        sendp(pkt, iface=interface, verbose=False)
        print(f"Sent probe packet seq_no={seq}")
        time.sleep(interval)

if __name__ == "__main__":
    # basic argument parsing
    argparser = argparse.ArgumentParser(description="Spine-Leaf Topology Probe Packet Sender")
    argparser.add_argument("--target_mac", type=str, required=True, help="Target MAC address to send probe packets to")
    argparser.add_argument("--target_ip", type=str, required=True, help="Target IP address to send probe packets to")
    argparser.add_argument("--sender_id", type=int, required=True, help="Sender ID for the probe packets")
    argparser.add_argument("--interface", type=str, default="enp177s0np0", help="Network interface to send packets on")
    argparser.add_argument("--count", type=int, default=100, help="Number of probe packets to send")
    argparser.add_argument("--interval", type=float, default=0.1, help="Interval between packets in seconds")
    args = argparser.parse_args()

    send_probes(args.target_mac, args.target_ip, args.sender_id, args.interface, args.count, args.interval)

