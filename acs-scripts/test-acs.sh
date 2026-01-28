#!/bin/bash
# Quick test of ACS reactive with 10 doors, 3 iterations
# Use this to verify setup before running full experiments

set -e

# Change to root directory
cd "$(dirname "$0")/.."

PROTOCOL="shamir"
N_PARTIES=3
N_DOORS=10
N_ITERATIONS=3

echo "======================================================================"
echo "ACS Quick Test"
echo "======================================================================"
echo "Protocol: $PROTOCOL"
echo "Parties: $N_PARTIES"
echo "Doors: $N_DOORS"
echo "Iterations: $N_ITERATIONS"
echo "======================================================================"
echo ""

# Create logs directory
mkdir -p acs-scripts/logs

# Compile and run MPC server
echo "Compiling and starting MPC server..."
./Scripts/compile-run.py -v $PROTOCOL acs-reactive $N_DOORS $N_ITERATIONS -F 128 -- -N $N_PARTIES > acs-scripts/logs/test-mpc.log 2>&1 &
MPC_PID=$!

# Wait for server to start
echo "Waiting for MPC server to be ready..."
MAX_WAIT=60
for i in $(seq 1 $MAX_WAIT); do
    if ss -tuln 2>/dev/null | grep -q ":14000" || netstat -tuln 2>/dev/null | grep -q ":14000"; then
        echo "MPC server is ready after $i seconds!"
        sleep 1
        break
    fi
    if [ $i -eq $MAX_WAIT ]; then
        echo "ERROR: MPC server did not start after $MAX_WAIT seconds"
        kill $MPC_PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

# Run client
echo "Starting client..."
./ExternalIO/acs-reactive-client.py 0 $N_PARTIES $N_DOORS $N_ITERATIONS | tee acs-scripts/logs/test-client.log

# Wait for MPC to finish
wait $MPC_PID

echo ""
echo "======================================================================"
echo "Test complete!"
echo "======================================================================"
echo ""
echo "Check logs:"
echo "  MPC: acs-scripts/logs/test-mpc.log"
echo "  Client: acs-scripts/logs/test-client.log"
echo ""
