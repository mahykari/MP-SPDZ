#!/bin/bash
# Compare different MPC protocols for ACS-10
# Note: Only using shamir as other protocols require additional build dependencies

set -e

# Change to root directory
cd "$(dirname "$0")/.."

N_DOORS=10
N_PARTIES=3
N_ITERATIONS=5
PROTOCOLS=("shamir")

echo "======================================================================"
echo "ACS Protocol Testing (${N_DOORS} doors)"
echo "======================================================================"
echo "Note: Other protocols (semi, replicated) require cmake or are"
echo "      binary-only. Using shamir as baseline."
echo ""

# Create logs directory
mkdir -p acs-scripts/logs

for PROTOCOL in "${PROTOCOLS[@]}"; do
    echo "======================================================================"
    echo "Testing Protocol: $PROTOCOL"
    echo "======================================================================"
    
    # Regenerate SSL certificates before each protocol
    echo "Setting up SSL certificates..."
    ./Scripts/setup-ssl.sh 3 > /dev/null 2>&1
    ./Scripts/setup-clients.sh 1 > /dev/null 2>&1
    
    # Compile and run MPC server
    echo "Compiling and starting MPC server..."
    ./Scripts/compile-run.py -v $PROTOCOL acs-reactive $N_DOORS $N_ITERATIONS -F 128 -- -N $N_PARTIES > "acs-scripts/logs/ACS-${N_DOORS}-${PROTOCOL}.log" 2>&1 &
    MPC_PID=$!
    
    # Wait for server to start (longer for some protocols)
    sleep 5
    
    # Run client
    echo "Starting client..."
    ./ExternalIO/acs-reactive-client.py 0 $N_PARTIES $N_DOORS $N_ITERATIONS | tee "acs-scripts/logs/ACS-${N_DOORS}-${PROTOCOL}-client.log"
    
    # Wait for MPC to finish
    wait $MPC_PID
    
    echo "Protocol $PROTOCOL complete!"
    echo ""
    sleep 2
done

echo "======================================================================"
echo "Protocol comparison complete!"
echo "======================================================================"
echo ""
echo "Analyze results with:"
echo "  python3 acs-scripts/analyze-acs-results.py"
echo ""
