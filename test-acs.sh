#!/bin/bash
# Quick test of ACS reactive with 10 doors, 3 iterations
# Use this to verify setup before running full experiments

set -e

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

# Compile
echo "Compiling acs-reactive.mpc..."
./compile.py -R 64 acs-reactive

# Create logs directory
mkdir -p logs

# Run MPC server
echo ""
echo "Starting MPC server..."
Scripts/compile-run.py -v $PROTOCOL acs-reactive $N_DOORS $N_ITERATIONS -- -N $N_PARTIES > logs/test-mpc.log 2>&1 &
MPC_PID=$!

# Wait for server to start
sleep 3

# Run client
echo "Starting client..."
./ExternalIO/acs-reactive-client.py 0 $N_PARTIES $N_DOORS $N_ITERATIONS | tee logs/test-client.log

# Wait for MPC to finish
wait $MPC_PID

echo ""
echo "======================================================================"
echo "Test complete!"
echo "======================================================================"
echo ""
echo "Check logs:"
echo "  MPC: logs/test-mpc.log"
echo "  Client: logs/test-client.log"
echo ""

# Clean up individual party logs (keep only summary)
rm -f logs/acs-reactive-${N_DOORS}-${N_ITERATIONS}-[0-9]*
echo "Cleaned up individual party logs"
