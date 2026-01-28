#!/bin/bash
# Run ACS reactive experiments with different configurations
# Matches the paper: 10 and 30 doors

set -e

# Change to root directory
cd "$(dirname "$0")/.."

PROTOCOL="shamir"
N_PARTIES=3
N_ITERATIONS=100

echo "======================================================================"
echo "ACS Reactive Experiments"
echo "======================================================================"
echo "Protocol: $PROTOCOL"
echo "Parties: $N_PARTIES"
echo "Iterations: $N_ITERATIONS"
echo "======================================================================"
echo ""

# Setup SSL certificates (only needs to be done once)
echo "Setting up SSL certificates..."
./Scripts/setup-ssl.sh $N_PARTIES > /dev/null 2>&1
./Scripts/setup-clients.sh 1 > /dev/null 2>&1
echo "SSL setup complete"
echo ""

# Function to run experiment
run_experiment() {
    local n_doors=$1
    local experiment_name="ACS-${n_doors}"
    
    # Check if experiment already completed successfully
    if [ -f "acs-scripts/logs/${experiment_name}-${PROTOCOL}.log" ] && \
       [ -f "acs-scripts/logs/${experiment_name}-${PROTOCOL}-client.log" ] && \
       grep -q "EXPERIMENT COMPLETE" "acs-scripts/logs/${experiment_name}-${PROTOCOL}.log" 2>/dev/null && \
       grep -q "EXPERIMENT COMPLETE" "acs-scripts/logs/${experiment_name}-${PROTOCOL}-client.log" 2>/dev/null; then
        echo "======================================================================"
        echo "SKIPPING: $experiment_name (${n_doors} doors) - already completed"
        echo "======================================================================"
        echo "Log files found at:"
        echo "  - acs-scripts/logs/${experiment_name}-${PROTOCOL}.log"
        echo "  - acs-scripts/logs/${experiment_name}-${PROTOCOL}-client.log"
        echo ""
        return 0
    fi
    
    echo "======================================================================"
    echo "Running: $experiment_name (${n_doors} doors)"
    echo "======================================================================"
    
    # Create logs directory
    mkdir -p acs-scripts/logs
    
    # Compile and run the experiment (compile-run.py does both)
    echo "Compiling and starting MPC computation..."
    ./Scripts/compile-run.py -v $PROTOCOL acs-reactive $n_doors $N_ITERATIONS -F 128 -- -N $N_PARTIES > "acs-scripts/logs/${experiment_name}-${PROTOCOL}.log" 2>&1 &
    MPC_PID=$!
    
    # Wait for MPC server to be ready
    echo "Waiting for compilation and server startup (this may take several minutes for large circuits)..."
    MAX_WAIT=600  # Wait up to 10 minutes for large circuits
    for i in $(seq 1 $MAX_WAIT); do
        if ss -tuln 2>/dev/null | grep -q ":14000" || netstat -tuln 2>/dev/null | grep -q ":14000"; then
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
    ./ExternalIO/acs-reactive-client.py 0 $N_PARTIES $n_doors $N_ITERATIONS | tee "acs-scripts/logs/${experiment_name}-${PROTOCOL}-client.log"
    
    # Wait for MPC to finish
    wait $MPC_PID
    
    echo ""
    echo "Experiment complete. Logs saved to acs-scripts/logs/${experiment_name}-${PROTOCOL}.log"
    echo ""
    sleep 2
}

# Run experiments for different door counts
run_experiment 10
run_experiment 30
run_experiment 100
run_experiment 300
run_experiment 1000

echo "======================================================================"
echo "All experiments complete!"
echo "======================================================================"
echo "Results saved in acs-scripts/logs/ directory"
echo ""
echo "To analyze results:"
echo "  python3 acs-scripts/analyze-acs-results.py"
echo ""
echo "Results:"
echo "  - MPC logs: acs-scripts/logs/ACS-*-${PROTOCOL}.log"
echo "  - Client logs: acs-scripts/logs/ACS-*-${PROTOCOL}-client.log"
echo ""
