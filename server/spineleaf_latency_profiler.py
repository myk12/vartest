#!/python3
# -*- coding: utf-8 -*-
# author: Yuke Ma
# date: 2025-12-17
# description: Tofino Spine-Leaf Topology Latency Probing Module

# - This module probes the latency of packets going through a Tofino switch
#   in a spine-leaf topology.

import os
import paramiko
import threading
import time
import subprocess

# define worker nodes information
SEND_WORKERS = [
    # Node 6 (Sender)
    {"hostname": "inet-p4lab-12",
     "user": os.getenv("TESTBED_USER"), # get from env.sh
     "password": os.getenv("TESTBED_PASSWD"), # get from env.sh
     "id": 6,
     "namespace": "node6",
     "interface": "enp177s0np0",
     },
    # Node 5 (Sender)
    {"hostname": "inet-p4lab-13",
     "user": os.getenv("TESTBED_USER"), # get from env.sh
     "password": os.getenv("TESTBED_PASSWD"), # get from env.sh
     "id": 4,
     "namespace": "node4",
     "interface": "enp177s0np0"
    },
    # Node 4 (Sender)
    {"hostname": "inet-p4lab-14",
     "user": os.getenv("TESTBED_USER"), # get from env.sh
     "password": os.getenv("TESTBED_PASSWD"), # get from env.sh
     "id": 2,
     "namespace": "node2",
     "interface": "enp177s0np0"
    },
]

RECV_ID = {
    "ip": "10.0.1.1",
    "mac": "00:0a:35:06:50:94"
}

def trigger_worker(worker):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print(f"Connecting to worker {worker['id']} at {worker['hostname']}...")
        ssh.connect(worker['hostname'], username=worker['user'], password=worker['password'])
        
        cmd = f"echo '{worker['password']}' | sudo -S -E ip netns exec {worker['namespace']} \
            python3 /home/yukema/vartest/server/utils/spineleaf_send_worker.py \
            --target_mac {RECV_ID['mac']} \
            --target_ip {RECV_ID['ip']} \
            --sender_id {worker['id']} \
            --interface {worker['interface']}"
        
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(f"Started sending probes on worker {worker['id']}.")
        for line in stdout:
            print(f"[Worker {worker['id']}] {line.strip()}")
        for line in stderr:
            print(f"[Worker {worker['id']} ERROR] {line.strip()}")
        ssh.close()
    except Exception as e:
        print(f"Error on worker {worker['id']}: {e}")

def start_receiver():
    print("Starting receiver on controller...")
    receiver_cmd = "python3 ./utils/spineleaf_recv_worker.py"
    receiver_process = subprocess.Popen(receiver_cmd, shell=True)
    return receiver_process

def main():
    # 1. Start the receiver on the controller side
    print("Starting receiver on controller...")
    receiver_cmd = "python3 ./utils/spineleaf_recv_worker.py"
    receiver_process = subprocess.Popen(receiver_cmd, shell=True)
    
    time.sleep(2) # wait a bit for receiver to start

    # 2. Trigger sending workers
    print("Triggering sending workers...")
    threads = []
    for w in SEND_WORKERS:
        t = threading.Thread(target=trigger_worker, args=(w,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("All probes sent.")

if __name__ == "__main__":
    main()
