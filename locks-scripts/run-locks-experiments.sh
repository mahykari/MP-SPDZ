#!/bin/bash
# Run locks reactive experiments with different configurations
# Lock counts: 100, 300, 500, 1000

set -e

# Change to root directory
cd "$(dirname "$0")/.."


PROTOCOL="shamir"
N_PARTIES=3
N_ITERATIONS=100
FIELD_SIZE=128
BATCH_SIZE=100

echo "======================================================================"
echo "Locks Reactive Experiments"
echo "======================================================================"
echo "Protocol: $PROTOCOL"
echo "Parties: $N_PARTIES"
echo "Iterations: $N_ITERATIONS"
echo "Field Size: $FIELD_SIZE bits"
echo "Batch Size: $BATCH_SIZE"
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
    local n_locks=$1
    local experiment_name="LOCKS-${n_locks}"
    
    # Check if experiment already completed successfully
    if [ -f "locks-scripts/logs/${experiment_name}-${PROTOCOL}.log" ] && \
       [ -f "locks-scripts/logs/${experiment_name}-${PROTOCOL}-client.log" ] && \
       grep -q "EXPERIMENT COMPLETE" "locks-scripts/logs/${experiment_name}-${PROTOCOL}.log" 2>/dev/null && \
       grep -q "EXPERIMENT COMPLETE" "locks-scripts/logs/${experiment_name}-${PROTOCOL}-client.log" 2>/dev/null; then
        echo "======================================================================"
        echo "SKIPPING: $experiment_name (${n_locks} locks) - already completed"
        echo "======================================================================"
        echo "Log files found at:"
        echo "  - locks-scripts/logs/${experiment_name}-${PROTOCOL}.log"
        echo "  - locks-scripts/logs/${experiment_name}-${PROTOCOL}-client.log"
        echo ""
        return 0
    fi
    
    echo "======================================================================"
    echo "Running: $experiment_name (${n_locks} locks)"
    echo "======================================================================"
    
    # Create logs directory
    mkdir -p locks-scripts/logs
    
    # Compile and run the experiment (compile-run.py does both)
    echo "Compiling and starting MPC computation for $n_locks locks..."
    ./Scripts/compile-run.py -v $PROTOCOL locks-reactive $n_locks $N_ITERATIONS -F $FIELD_SIZE -- -N $N_PARTIES --batch-size $BATCH_SIZE > "locks-scripts/logs/${experiment_name}-${PROTOCOL}.log" 2>&1 &
    MPC_PID=$!
    
    # Wait for MPC server to be ready (compilation can take time for large circuits)
    echo "Waiting for compilation and server startup (this may take several minutes for large circuits)..."
    MAX_WAIT=600  # Wait up to 10 minutes for large circuits
    for i in $(seq 1 $MAX_WAIT); do
        if ss -tuln 2>/dev/null | grep -q ":14000" || netstat -tuln 2>/dev/null | grep -q ":14000"; then
            echo "MPC server is ready after $i seconds!"
            sleep 2  # Extra buffer to ensure full initialization
            break
        fi
        if [ $i -eq $MAX_WAIT ]; then
            echo "ERROR: MPC server did not start after $MAX_WAIT seconds"
            echo "Check locks-scripts/logs/${experiment_name}-${PROTOCOL}.log for errors"
            kill $MPC_PID 2>/dev/null
            exit 1
        fi
        sleep 1
    done
    
    # Run the client
    echo "Starting client..."
    ./ExternalIO/locks-reactive-client.py 0 $N_PARTIES $n_locks $N_ITERATIONS | tee "locks-scripts/logs/${experiment_name}-${PROTOCOL}-client.log"
    
    # Wait for MPC to finish
    wait $MPC_PID
    
    echo ""
    echo "Experiment complete. Logs saved to locks-scripts/logs/${experiment_name}-${PROTOCOL}.log"
    echo ""
    sleep 2
}

# Run experiments for different lock counts
run_experiment 100
run_experiment 300
run_experiment 500
run_experiment 1000

echo "======================================================================"
echo "All experiments complete!"
echo "======================================================================"
echo "Results saved in locks-scripts/logs/ directory"
echo ""
echo "To analyze results:"
echo "  python3 locks-scripts/analyze-locks-results.py"
echo ""
echo "Results:"
echo "  - MPC logs: locks-scripts/logs/LOCKS-*-${PROTOCOL}.log"
echo "  - Client logs: locks-scripts/logs/LOCKS-*-${PROTOCOL}-client.log"
echo ""

