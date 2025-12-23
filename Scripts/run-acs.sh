#!/bin/bash
# Helper script to run the door monitoring system (acs.mpc) with sensor client

set -e

echo "========================================"
echo "Door Monitoring System - Setup & Run"
echo "========================================"
echo ""

# Configuration
N_PARTIES=3
PORT=14000
PROTOCOL=${1:-semi}  # Default to semi-honest protocol

echo "Step 1: Compiling acs.mpc..."
./compile.py acs || { echo "Compilation failed"; exit 1; }

echo ""
echo "Step 2: Setting up SSL certificates for $N_PARTIES parties and 1 client..."
Scripts/setup-ssl.sh $N_PARTIES > /dev/null 2>&1
Scripts/setup-clients.sh 1 > /dev/null 2>&1

echo ""
echo "Step 3: Starting MPC parties ($PROTOCOL protocol)..."
echo "Running: PLAYERS=$N_PARTIES Scripts/$PROTOCOL.sh acs"

# Kill any existing processes on port 14000
lsof -ti:14000 | xargs kill -9 2>/dev/null || true
sleep 1

PLAYERS=$N_PARTIES Scripts/$PROTOCOL.sh acs > mpc_output.log 2>&1 &
MPC_PID=$!

echo "MPC parties started (PID: $MPC_PID)"
echo "Waiting for parties to initialize..."

# Wait and check if parties are listening
for i in {1..10}; do
  if lsof -i:14000 > /dev/null 2>&1; then
    echo "Parties are listening on port 14000!"
    sleep 2  # Give a bit more time for SSL setup
    break
  fi
  echo "  Waiting... ($i/10)"
  sleep 1
done

echo ""
echo "Step 4: Running sensor client..."
echo "========================================"
python3 ExternalIO/acs-sensor-client.py 0 $N_PARTIES || {
  echo "Client failed"
  kill $MPC_PID 2>/dev/null
  exit 1
}

echo ""
echo "========================================"
echo "Waiting for MPC parties to finish..."
wait $MPC_PID 2>/dev/null || true

echo ""
echo "MPC output saved to: mpc_output.log"
echo "To view: cat mpc_output.log"
echo ""
echo "Done!"
