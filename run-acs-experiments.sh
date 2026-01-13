#!/bin/bash
# Run ACS reactive experiments with different configurations
# Matches the paper: 10 and 30 doors

set -e

PROTOCOL="shamir"
N_PARTIES=3
N_ITERATIONS=5

echo "======================================================================"
echo "ACS Reactive Experiments"
echo "======================================================================"
echo "Protocol: $PROTOCOL"
echo "Parties: $N_PARTIES"
echo "Iterations: $N_ITERATIONS"
echo "======================================================================"
echo ""

# Function to run experiment
run_experiment() {
    local n_doors=$1
    local experiment_name="ACS-${n_doors}"
    
    echo "======================================================================"
    echo "Running: $experiment_name (${n_doors} doors)"
    echo "======================================================================"
    
    # Compile the MPC program
    echo "Compiling acs-reactive.mpc..."
    ./compile.py -R 64 acs-reactive
    
    # Create logs directory
    mkdir -p logs
    
    # Run the experiment
    echo "Starting MPC computation..."
    Scripts/compile-run.py -v $PROTOCOL acs-reactive $n_doors $N_ITERATIONS -- -N $N_PARTIES > "logs/${experiment_name}-${PROTOCOL}.log" 2>&1 &
    MPC_PID=$!
    
    # Wait a moment for MPC to start
    sleep 2
    
    # Run the client
    echo "Starting client..."
    ./ExternalIO/acs-reactive-client.py 0 $N_PARTIES $n_doors $N_ITERATIONS | tee "logs/${experiment_name}-${PROTOCOL}-client.log"
    
    # Wait for MPC to finish
    wait $MPC_PID
    
    echo ""
    echo "Experiment complete. Logs saved to logs/${experiment_name}-${PROTOCOL}.log"
    
    # Clean up individual party logs (keep only summary)
    rm -f logs/acs-reactive-${n_doors}-${N_ITERATIONS}-[0-9]*
    echo "Cleaned up individual party logs"
    echo ""
    sleep 2
}

# Run experiments for both door counts (matching the paper)
run_experiment 10
run_experiment 30

echo "======================================================================"
echo "All experiments complete!"
echo "======================================================================"
echo "Results saved in logs/ directory"
echo ""
echo "To analyze results:"
echo "  - MPC logs: logs/ACS-*-${PROTOCOL}.log"
echo "  - Client logs: logs/ACS-*-${PROTOCOL}-client.log"
echo ""
