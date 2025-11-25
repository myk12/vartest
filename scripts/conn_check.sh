#!/bin/bash
# --------------------------------------------------
# measurement/tofino/conn_check.sh
# author: Yuke Ma
# date: 2024-06-10
# description: Check connectivity between two network namespaces
# --------------------------------------------------

log_info() {
    # with green color
    local MESSAGE=$1
    echo -e "\e[32m[INFO] $MESSAGE\e[0m"
}

log_error() {
    # with red color
    local MESSAGE=$1
    echo -e "\e[31m[ERROR] $MESSAGE\e[0m"
}

# check if env.sh is sourced
if [ -z "$NS1" ] || [ -z "$NS2" ] || [ -z "$PORTNAME1" ] || [ -z "$PORTNAME2" ] || [ -z "$IP_ADDR1" ] || [ -z "$IP_ADDR2" ] || [ -z "$IP1" ] || [ -z "$IP2" ] || [ -z "$MAC1" ] || [ -z "$MAC2" ]; then
    log_error "Environment variables not set. Please source env.sh first."
    exit 1
fi

## insert arp entries to avoid delay on first ping
MAC1=$(sudo ip netns exec "$NS1" ip link show "$PORTNAME1" | awk '/ether/ {print $2}')
MAC2=$(sudo ip netns exec "$NS2" ip link show "$PORTNAME2" | awk '/ether/ {print $2}')
sudo ip netns exec "$NS1" ip neigh add "$IP2" lladdr "$MAC2" dev "$PORTNAME1" nud permanent
sudo ip netns exec "$NS2" ip neigh add "$IP1" lladdr "$MAC1" dev "$PORTNAME2" nud permanent

log_info "Testing connectivity between $IP1 and $IP2..."

# We cannot use ping because tofino drops ICMP packets by default
sudo ip netns exec "$NS2" timeout 3s nc -u -l -p 5001 > /tmp/udp_test_recv.log &
PID_NC=$!

sleep 1  # give some time for the listener to start

echo "Test UDP Packet from $NS1 to $NS2" | sudo ip netns exec "$NS1" nc -u "$IP2" 5001

wait $PID_NC
if grep -q "Test UDP Packet from $NS1 to $NS2" /tmp/udp_test_recv.log; then
    log_info "Connectivity test successful: $NS1 can reach $NS2."
    exit 0
else
    log_error "Connectivity test failed: $NS1 cannot reach $NS2."
    exit 1
fi
