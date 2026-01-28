#!/bin/bash
# Test of blood sugar monitor with many iterations
# Uses small field (64-bit) for efficiency

set -e

# Change to root directory
cd "$(dirname "$0")/.."

PROTOCOL="shamir"
N_PARTIES=3
N_ITERATIONS=1000
FIELD_SIZE=64

echo "======================================================================"
echo "Blood Sugar Monitor Test"
echo "======================================================================"
echo "Protocol: $PROTOCOL"
echo "Parties: $N_PARTIES"
echo "Iterations: $N_ITERATIONS"
echo "Field Size: $FIELD_SIZE bits"
echo "======================================================================"
echo ""

# Create logs directory
mkdir -p blood-sugar-scripts/logs

# Compile and run MPC server
echo "Compiling and starting MPC server..."
./Scripts/compile-run.py -v $PROTOCOL blood-sugar-monitor $N_ITERATIONS -F $FIELD_SIZE -- -N $N_PARTIES > blood-sugar-scripts/logs/test-mpc.log 2>&1 &
MPC_PID=$!


# Wait for server to start
echo "Waiting for MPC server to be ready..."
MAX_WAIT=60

for i in $(seq 1 $MAX_WAIT); do
    if ss -tuln 2>/dev/null | grep -q ":14001" || netstat -tuln 2>/dev/null | grep -q ":14001"; then
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
./ExternalIO/blood-sugar-monitor-client.py 0 $N_PARTIES $N_ITERATIONS | tee blood-sugar-scripts/logs/test-client.log

# Wait for MPC to finish
wait $MPC_PID

echo ""
echo "======================================================================"
echo "Test complete!"
echo "======================================================================"
echo ""
echo "Check logs:"
echo "  MPC: blood-sugar-scripts/logs/test-mpc.log"
echo "  Client: blood-sugar-scripts/logs/test-client.log"
echo ""
