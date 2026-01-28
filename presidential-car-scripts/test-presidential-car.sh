#!/bin/bash
# Quick test of Presidential Car reactive monitor (adaptive geofence)
# Use this to verify setup before running full experiments

set -e

# Change to root directory
cd "$(dirname "$0")/.."

PROTOCOL="shamir"
N_PARTIES=3
DIM=2
N_ITERATIONS=3

PORT=14001

echo "======================================================================"
echo "Presidential Car Quick Test"
echo "======================================================================"
echo "Protocol:    $PROTOCOL"
echo "Parties:     $N_PARTIES"
echo "Dimensions:  $DIM"
echo "Iterations:  $N_ITERATIONS"
echo "======================================================================"
echo ""

# Create logs directory
mkdir -p presidential-car-scripts/logs

# Compile and run MPC server
echo "Compiling and starting MPC server..."
./Scripts/compile-run.py -v $PROTOCOL presidential-car-reactive $DIM $N_ITERATIONS -F 128 -- -N $N_PARTIES \
  > presidential-car-scripts/logs/test-mpc.log 2>&1 &
MPC_PID=$!

# Wait for server to start
echo "Waiting for MPC server to be ready..."
MAX_WAIT=60
for i in $(seq 1 $MAX_WAIT); do
  if ss -tuln 2>/dev/null | grep -q ":$PORT" || netstat -tuln 2>/dev/null | grep -q ":$PORT"; then
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
./ExternalIO/presidential-car-client.py 0 $N_PARTIES $DIM $N_ITERATIONS fault_last \
  | tee presidential-car-scripts/logs/test-client.log

# Wait for MPC to finish
wait $MPC_PID

echo ""
echo "======================================================================"
echo "Test complete!"
echo "======================================================================"
echo ""
echo "Check logs:"
echo "  MPC:    presidential-car-scripts/logs/test-mpc.log"
echo "  Client: presidential-car-scripts/logs/test-client.log"
echo ""
