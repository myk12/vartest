#!/bin/bash

TRAFFIC_PATTERNS=("SINGLE" "MULTIPLE")
LINK_RATES=("10G" "25G" "50G" "100G")
PACKET_SIZES=("64" "256" "512" "1024")
RESULT_DIR="$(pwd)/results/$(date +%Y%m%d_%H%M%S)"
mkdir -p $RESULT_DIR

echo "=== === === Batch Tofino Latency Probe Test === === ==="
for pattern in "${TRAFFIC_PATTERNS[@]}"; do
    for rate in "${LINK_RATES[@]}"; do
        for psize in "${PACKET_SIZES[@]}"; do
            echo "Running test: Pattern=$pattern, Rate=$rate, Packet Size=$psize"
            echo "Results will be stored in: $RESULT_DIR"
            export TRAFFIC_PATTERN=$pattern
            export LINK_RATE=$rate
            export PACKET_SIZE=$psize

            # Run the latency probe test
            # The running must be blocked cause we need different Tofino settings per test
            sudo python3 ./server/probe_main.py --result_dir $RESULT_DIR

            if [ $? -ne 0 ]; then
                echo "Test failed for Pattern=$pattern, Rate=$rate, Packet Size=$psize"
            else
                echo "Test completed for Pattern=$pattern, Rate=$rate, Packet Size=$psize"
            fi

            echo "---------------------------------------------"
        done
    done
done
