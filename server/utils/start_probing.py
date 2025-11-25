#!/bin/bash/env python3
# -*- coding: utf-8 -*-
# author: Yuke Ma
# date: 2025-11-24
# description: Tofino latency probing module

# - This module probes the latency of packets going through a Tofino switch.
#   It starts a packet sender to send packets and a receiver to capture them,
#   measuring the time taken for packets to traverse the switch.
# - One thread is used for sending packets, and another for receiving them.

import argparse
import multiprocessing
import socket
import sys
import time
import struct
import ctypes
import os
import pandas as pd
from loguru import logger

# set level to INFO
logger.remove()
logger.add(sys.stdout, level="INFO")

#======================= Configurations =======================#
SENDER_NS = os.getenv("NS1", "fpganic_p1")
RECEIVER_NS = os.getenv("NS2", "fpganic_p2")
SENDER_IFACE = os.getenv("IFACE1", "enp202s0np0")
RECEIVER_IFACE = os.getenv("IFACE2", "enp202s0np1")
SENDER_IP = os.getenv("IP1", "10.0.0.1")
RECEIVER_IP = os.getenv("IP2", "10.0.0.2")

PACKET_COUNT = int(os.getenv("PACKET_COUNT", "1000"))
PACKET_SIZE = int(os.getenv("PACKET_SIZE", "256"))
SEND_RATE = int(os.getenv("SEND_RATE", "1"))  # packets per second

EXP_PORT = 17777

# TS header (ts_h) layout packed into UDP payload
#   bit<16>   exp_id;
#   bit<32>   seq;
#   ts64_t    ingress_mac_ts;
#   ts64_t    ingress_global_ts;
#   ts64_t    egress_global_ts;
#   bit<16>   ingress_port;
#   bit<16>   egress_port;
EXP_ID = int(os.getenv("EXP_ID", "1"))
HEADER_FORMAT = "!HIQQQHH" # H=16bit, I=32bit, Q=64bit
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# load necessary libraries
libc = ctypes.CDLL("libc.so.6")
CLONE_NEWNET = 0x40000000
#==============================================================#

def switch_namespace(ns_name):
    """Switch to the specified network namespace."""
    logger.info(f"Switching to namespace: {ns_name}")
    ns_path = f"/var/run/netns/{ns_name}"
    try:
        with open(ns_path) as ns_file:
            # setns(fd, nstype): fd is the file descriptor of the namespace
            ret = libc.setns(ns_file.fileno(), CLONE_NEWNET)
            if ret != 0:
                raise OSError(f"setns failed for {ns_name}")
    except Exception as e:
        logger.error(f"Error switching namespace: {e}")
        exit(1)

def receiver_task(result_queue, stop_event):
    """Receiver process to capture packets and measure latency."""
    # Switch to receiver namespace
    switch_namespace(RECEIVER_NS)

    # Create UDP socket to receive packets
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((RECEIVER_IP, EXP_PORT))
    sock.settimeout(1.0)    # Set timeout to avoid blocking indefinitely
    logger.info("Receiver started on {}:{}".format(RECEIVER_IP, EXP_PORT))
    
    received_data = {} # Key: seq_num, Value: ts_header
    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(2048)
            recv_time = time.time_ns()  # in nanoseconds

            if len(data) >= HEADER_SIZE:  # Minimum size to unpack ts_h
                (exp_id, seq_num, ingress_mac_ts, ingress_global_ts,
                 egress_global_ts, ingress_port, egress_port) = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
                logger.trace(f"Packet received from {addr}, exp_id={exp_id}, seq_num={seq_num}")
                # Store full header information plus recv_time and latency
                received_data[seq_num] = {
                    'exp_id': exp_id,
                    'seq': seq_num,
                    'ingress_mac_ts': ingress_mac_ts,
                    'ingress_global_ts': ingress_global_ts,
                    'egress_global_ts': egress_global_ts,
                    'ingress_port': ingress_port,
                    'egress_port': egress_port,
                    'recv_time': recv_time,
                }
        except socket.timeout:
            continue
        except Exception as e:
            logger.error(f"Receiver error: {e}")
            break

    result_queue.put(received_data)
    sock.close()
    logger.info("Receiver stopped.")
    
def sender_task(stop_event):
    """Sender process to send packets."""
    # Switch to sender namespace
    switch_namespace(SENDER_NS)

    # Create UDP socket to send packets
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    logger.info("Sender started, sending to {}:9999".format(RECEIVER_IP))
    
    for seq_num in range(PACKET_COUNT):
        if stop_event.is_set():
            break

        send_time = time.time_ns()  # in nanoseconds
        # Populate ts_h. We don't have hardware ingress MAC ts here, set to 0.
        ingress_mac_ts = 0
        ingress_global_ts = 0
        egress_global_ts = 0
        ingress_port = 0
        egress_port = 0
        header = struct.pack(HEADER_FORMAT, EXP_ID, seq_num, ingress_mac_ts, ingress_global_ts, egress_global_ts, ingress_port, egress_port)
        payload = header + bytes(max(0, PACKET_SIZE - len(header)))
        sock.sendto(payload, (RECEIVER_IP, EXP_PORT))
        logger.trace(f"Sent packet seq_num={seq_num}")

        #TODO: Add precise rate control here (like randomized inter-packet gap)
        time.sleep(1.0 / SEND_RATE)  # Control send rate

    sock.close()
    logger.info("Sender stopped.")

def save_results(df: pd.DataFrame, result_dir: str, filename: str):
    """Save the results DataFrame to CSV in the specified directory."""
    csv_filename = os.path.join(result_dir, filename)
    df.to_csv(csv_filename, index=False)
    logger.info(f"Saved latency data to {csv_filename}")

def start_probing(result_dir: str = "./results", pattern: str = "SINGLE", rate: int = 10, packet_size: int = 1024):
    logger.info("Starting probing process.")
    # Create a queue to collect results from receiver
    mgr = multiprocessing.Manager()
    recv_queue = mgr.Queue()
    send_queue = mgr.Queue()
    stop_event = multiprocessing.Event()

    # Start receiver process
    logger.info("Starting receiver process.")
    receiver_process = multiprocessing.Process(target=receiver_task, args=(recv_queue, stop_event))
    receiver_process.start()
    
    time.sleep(1)  # Ensure receiver is ready before sender starts
    # Start sender process
    logger.info("Starting sender process.")
    sender_process = multiprocessing.Process(target=sender_task, args=(stop_event,))
    sender_process.start()
    # Wait for sender to finish
    logger.info("Waiting for sender process to finish.")
    sender_process.join()
    
    # Leave some time for receiver to process remaining packets
    logger.info("Sender finished. Allowing receiver to finalize.")
    time.sleep(3)
    stop_event.set()
    receiver_process.join()
    # Collect results from receiver
    logger.info("Collecting results from receiver.")
    received_data = recv_queue.get()
    # received_data is a dict mapping seq -> header-dict. Convert to pandas DataFrame
    if not received_data:
        logger.warning("No packets were received.")
        return
    # sort by sequence number for stable ordering
    rows = [received_data[k] for k in sorted(received_data.keys())]
    df = pd.DataFrame(rows)
    logger.info(f"Converted {len(df)} packets to DataFrame with columns: {df.columns.tolist()}")
    logger.debug(f"DataFrame head:\n{df.head().to_string()}")
    
    # Save results
    os.makedirs(result_dir, exist_ok=True)
    filename = f"{pattern}_{rate}Gbps_{packet_size}B.csv"
    save_results(df, result_dir, filename)

if __name__ == "__main__":
    logger.info("This module is intended to be imported and used by probe_main.py.")
    parser = argparse.ArgumentParser(description="Start Tofino latency probing.")
    parser.add_argument('--pattern', type=str, choices=['SINGLE', 'MULTIPLE'], default='SINGLE',
                        help='Traffic pattern to use for probing')
    parser.add_argument('--rate', type=int, default=10,
                        help='Packet send rate (Gbps)')
    parser.add_argument('--packet_size', type=int, default=1024,
                        help='Packet size in bytes')
    args = parser.parse_args()

    result_dir = "./results"

    start_probing(result_dir=result_dir, pattern=args.pattern, rate=args.rate, packet_size=args.packet_size)
