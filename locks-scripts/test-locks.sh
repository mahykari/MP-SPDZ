#!/bin/bash
# Quick test of locks reactive with 8 locks, 5 iterations
# Use this to verify setup before running full experiments

set -e

# Change to root directory
cd "$(dirname "$0")/.."


PROTOCOL="shamir"
N_PARTIES=3
N_LOCKS=8
N_ITERATIONS=5
FIELD_SIZE=128
BATCH_SIZE=100

echo "======================================================================"
echo "Locks Quick Test"
echo "======================================================================"
echo "Protocol: $PROTOCOL"
echo "Parties: $N_PARTIES"
echo "Locks: $N_LOCKS"
echo "Iterations: $N_ITERATIONS"
echo "Field Size: $FIELD_SIZE bits"
echo "======================================================================"
echo ""

# Compile
echo "Compiling locks-reactive.mpc..."
./compile.py -F $FIELD_SIZE locks-reactive

# Create logs directory
mkdir -p locks-scripts/logs

# Compile and run MPC server
echo ""
echo "Compiling and starting MPC server..."
./Scripts/compile-run.py -v $PROTOCOL locks-reactive $N_LOCKS $N_ITERATIONS -F $FIELD_SIZE -- -N $N_PARTIES --batch-size $BATCH_SIZE > locks-scripts/logs/test-locks-mpc.log 2>&1 &
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
./ExternalIO/locks-reactive-client.py 0 $N_PARTIES $N_LOCKS $N_ITERATIONS | tee locks-scripts/logs/test-locks-client.log

# Wait for MPC to finish
wait $MPC_PID

echo ""
echo "======================================================================"
echo "Test complete!"
echo "======================================================================"
echo ""
echo "Check logs:"
echo "  MPC: logs/test-locks-mpc.log"
echo "  Client: logs/test-locks-client.log"
echo ""

