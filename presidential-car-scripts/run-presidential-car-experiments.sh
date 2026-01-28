#!/bin/bash
# Run Presidential Car reactive experiments with different configurations
# Sweeps dimensions (n-D) with fixed iteration count.

set -e

# Change to root directory
cd "$(dirname "$0")/.."

PROTOCOL="shamir"
N_PARTIES=3
N_ITERATIONS=200
MODE="fault_last"
PORT=14001

echo "======================================================================"
echo "Presidential Car Reactive Experiments"
echo "======================================================================"
echo "Protocol:    $PROTOCOL"
echo "Parties:     $N_PARTIES"
echo "Iterations:  $N_ITERATIONS"
echo "Mode:        $MODE"
echo "Port:        $PORT"
echo "======================================================================"
echo ""

# Setup SSL certificates (only needs to be done once)
echo "Setting up SSL certificates..."
./Scripts/setup-ssl.sh $N_PARTIES > /dev/null 2>&1
./Scripts/setup-clients.sh 1 > /dev/null 2>&1
echo "SSL setup complete"
echo ""

run_experiment() {
  local dim=$1
  local experiment_name="PRESCAR-${dim}D"

  # Check if experiment already completed successfully
  if [ -f "presidential-car-scripts/logs/${experiment_name}-${PROTOCOL}.log" ] && \
     [ -f "presidential-car-scripts/logs/${experiment_name}-${PROTOCOL}-client.log" ] && \
     grep -q "EXPERIMENT COMPLETE" "presidential-car-scripts/logs/${experiment_name}-${PROTOCOL}.log" 2>/dev/null && \
     grep -q "EXPERIMENT COMPLETE" "presidential-car-scripts/logs/${experiment_name}-${PROTOCOL}-client.log" 2>/dev/null; then
    echo "======================================================================"
    echo "SKIPPING: $experiment_name - already completed"
    echo "======================================================================"
    echo "Log files found at:"
    echo "  - presidential-car-scripts/logs/${experiment_name}-${PROTOCOL}.log"
    echo "  - presidential-car-scripts/logs/${experiment_name}-${PROTOCOL}-client.log"
    echo ""
    return 0
  fi

  echo "======================================================================"
  echo "Running: $experiment_name"
  echo "======================================================================"

  # Create logs directory
  mkdir -p presidential-car-scripts/logs

  # Compile and run the experiment
  echo "Compiling and starting MPC computation..."
  ./Scripts/compile-run.py -v $PROTOCOL presidential-car-reactive $dim $N_ITERATIONS -F 128 -- -N $N_PARTIES \
    > "presidential-car-scripts/logs/${experiment_name}-${PROTOCOL}.log" 2>&1 &
  MPC_PID=$!

  # Wait for MPC server to be ready
  echo "Waiting for compilation and server startup (may take a while for large DIM)..."
  MAX_WAIT=600
  for i in $(seq 1 $MAX_WAIT); do
    if ss -tuln 2>/dev/null | grep -q ":$PORT" || netstat -tuln 2>/dev/null | grep -q ":$PORT"; then
      echo "MPC server is ready after $i seconds!"
      sleep 2
      break
    fi
    if [ $i -eq $MAX_WAIT ]; then
      echo "ERROR: MPC server did not start after $MAX_WAIT seconds"
      kill $MPC_PID 2>/dev/null
      exit 1
    fi
    sleep 1
  done

  # Run the client
  echo "Starting client..."
  ./ExternalIO/presidential-car-client.py 0 $N_PARTIES $dim $N_ITERATIONS $MODE \
    | tee "presidential-car-scripts/logs/${experiment_name}-${PROTOCOL}-client.log"

  # Wait for MPC to finish
  wait $MPC_PID

  echo ""
  echo "Experiment complete. Logs saved to presidential-car-scripts/logs/${experiment_name}-${PROTOCOL}.log"
  echo ""
  sleep 2
}

# Dimension sweep (edit as needed)
run_experiment 2
run_experiment 4
run_experiment 8
run_experiment 16
run_experiment 32
run_experiment 64
run_experiment 128
run_experiment 256
run_experiment 512
run_experiment 1024
run_experiment 2048
run_experiment 4096


echo "======================================================================"
echo "All experiments complete!"
echo "======================================================================"
echo "Results saved in presidential-car-scripts/logs/ directory"
echo ""
echo "Results:"
echo "  - MPC logs:    presidential-car-scripts/logs/PRESCAR-*D-${PROTOCOL}.log"
echo "  - Client logs: presidential-car-scripts/logs/PRESCAR-*D-${PROTOCOL}-client.log"
echo ""
