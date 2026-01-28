#!/bin/bash
# Compare different MPC protocols for LOCKS-100
# Note: Only using shamir as other protocols require additional build dependencies

set -e

# Change to root directory
cd "$(dirname "$0")/.."


N_LOCKS=100
N_PARTIES=3
N_ITERATIONS=100
FIELD_SIZE=128
BATCH_SIZE=1000
PROTOCOLS=("shamir")

echo "======================================================================"
echo "Locks Protocol Testing (${N_LOCKS} locks)"
echo "======================================================================"
echo "Note: Other protocols (semi, replicated) require cmake or are"
echo "      binary-only. Using shamir as baseline."
echo ""

# Create logs directory
mkdir -p locks-scripts/logs

for PROTOCOL in "${PROTOCOLS[@]}"; do
    echo "======================================================================"
    echo "Testing Protocol: $PROTOCOL"
    echo "======================================================================"
    
    # Compile
    echo "Compiling locks-reactive.mpc..."
    ./compile.py -F $FIELD_SIZE locks-reactive
    
    # Regenerate SSL certificates before each protocol
    echo "Setting up SSL certificates..."
    ./Scripts/setup-ssl.sh 3 > /dev/null 2>&1
    ./Scripts/setup-clients.sh 1 > /dev/null 2>&1
    
    # Run MPC server
    echo "Starting MPC server..."
    ./Scripts/compile-run.py -v $PROTOCOL locks-reactive -F $FIELD_SIZE -- -N $N_PARTIES $N_LOCKS $N_ITERATIONS --batch-size $BATCH_SIZE > "locks-scripts/logs/LOCKS-${N_LOCKS}-${PROTOCOL}.log" 2>&1 &
    MPC_PID=$!
    
    # Wait for server to start
    sleep 5
    
    # Run client
    echo "Starting client..."
    ./ExternalIO/locks-reactive-client.py 0 $N_PARTIES $N_LOCKS $N_ITERATIONS | tee "locks-scripts/logs/LOCKS-${N_LOCKS}-${PROTOCOL}-client.log"
    
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
echo "  python3 locks-scripts/analyze-locks-results.py"
echo ""

