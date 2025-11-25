#!/bin/bash

TRAFFIC_PATTERNS=("IDLE" "SINGLE" "MULTIPLE")
LINK_RATES=("10G" "25G" "50G" "100G")
PACKET_SIZES=("64" "256" "512" "1024")

echo "=== === === Batch Tofino Latency Probe Test === === ==="
for pattern in "${TRAFFIC_PATTERNS[@]}"; do
    for rate in "${LINK_RATES[@]}"; do
        for psize in "${PACKET_SIZES[@]}"; do
            echo "Running test: Pattern=$pattern, Rate=$rate, Packet Size=$psize"
            export TRAFFIC_PATTERN=$pattern
            export LINK_RATE=$rate
            export PACKET_SIZE=$psize

            # Run the latency probe test
            # The running must be blocked cause we need different Tofino settings per test
            python3 ./server/probe_main.py

            if [ $? -ne 0 ]; then
                echo "Test failed for Pattern=$pattern, Rate=$rate, Packet Size=$psize"
            else
                echo "Test completed for Pattern=$pattern, Rate=$rate, Packet Size=$psize"
            fi

            echo "---------------------------------------------"
        done
    done
done

