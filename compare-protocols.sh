#!/bin/bash
# Compare different MPC protocols for ACS-10
# Note: Only using shamir as other protocols require additional build dependencies

set -e

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
mkdir -p logs

for PROTOCOL in "${PROTOCOLS[@]}"; do
    echo "======================================================================"
    echo "Testing Protocol: $PROTOCOL"
    echo "======================================================================"
    
    # Compile
    echo "Compiling acs-reactive.mpc..."
    ./compile.py -R 64 acs-reactive
    
    # Regenerate SSL certificates before each protocol
    echo "Setting up SSL certificates..."
    Scripts/setup-ssl.sh 3 > /dev/null 2>&1
    
    # Run MPC server
    echo "Starting MPC server..."
    Scripts/compile-run.py -v $PROTOCOL acs-reactive $N_DOORS $N_ITERATIONS -- -N $N_PARTIES > "logs/ACS-${N_DOORS}-${PROTOCOL}.log" 2>&1 &
    MPC_PID=$!
    
    # Wait for server to start (longer for some protocols)
    sleep 5
    
    # Run client
    echo "Starting client..."
    ./ExternalIO/acs-reactive-client.py 0 $N_PARTIES $N_DOORS $N_ITERATIONS | tee "logs/ACS-${N_DOORS}-${PROTOCOL}-client.log"
    
    # Wait for MPC to finish
    wait $MPC_PID
    
    echo "Protocol $PROTOCOL complete!"
    
    # Clean up individual party logs (keep only summary)
    rm -f logs/acs-reactive-${N_DOORS}-${N_ITERATIONS}-[0-9]*
    echo "Cleaned up individual party logs"
    echo ""
    sleep 2
done

echo "======================================================================"
echo "Protocol comparison complete!"
echo "======================================================================"
echo ""
echo "Analyze results with:"
echo "  ./analyze-acs-results.py"
echo ""
