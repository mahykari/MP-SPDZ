#!/bin/bash
# Party-scaling experiment: run each scenario at its maximum parameter,
# sweeping N_PARTIES = 3, 5, 7, 9, 11.
#
# Scenarios
#   ACS          : 1000 doors,  100 iterations, port 14000
#   Locks        : 1000 locks,  100 iterations, port 14000
#   Presidential : 1024 dims,   200 iterations, port 14001
#   Blood Sugar  :              1000 iterations, port 14001
#
# Logs land in scalability-scripts/logs/ with names like:
#   ACS-1000-N5-shamir.log / ACS-1000-N5-shamir-client.log
#
# Run on Slurm login node (no sbatch needed for localhost-only MPC).
# If required, uncomment module loads below before running:
#   module load gcc/14.2
#   module load boost/1.83.0
#   module load libssl/1.1.1
#   module load python/3.11

set -e
cd "$(dirname "$0")/.."

PROTOCOL="shamir"
PARTY_COUNTS=(3 5 7 9 11)
LOGS_DIR="logs/scalability"
MAX_WAIT=600   # seconds to wait for MPC server to bind its port

mkdir -p "$LOGS_DIR"

# ---------------------------------------------------------------------------
# Compile all circuits once (skip if schedule file already exists)
# ---------------------------------------------------------------------------
compile_once() {
    local label=$1
    local sch=$2
    shift 2          # remaining args forwarded to compile.py

    if [ -f "$sch" ]; then
        echo "  Already compiled: $label"
        return 0
    fi
    echo "  Compiling $label ..."
    ./compile.py "$@" > "${LOGS_DIR}/${label}-compile.log" 2>&1
    echo "  Done: $label"
}

# ---------------------------------------------------------------------------
# Helper: wait for a port to be bound
# ---------------------------------------------------------------------------
wait_for_port() {
    local port=$1
    local log_label=$2
    local limit=${3:-$MAX_WAIT}
    echo "  Waiting for MPC server on port $port (up to ${limit}s)..."
    for i in $(seq 1 $limit); do
        if ss -tuln 2>/dev/null | grep -q ":${port}" || \
           netstat -tuln 2>/dev/null | grep -q ":${port}"; then
            echo "  Server ready after ${i}s."
            sleep 2
            return 0
        fi
        if [ "$i" -eq "$limit" ]; then
            echo "ERROR: MPC server did not bind port $port after ${limit}s"
            echo "Check $log_label for errors."
            return 1
        fi
        sleep 1
    done
}

# ---------------------------------------------------------------------------
# Individual scenario runners – each takes N_PARTIES as $1
# ---------------------------------------------------------------------------

run_acs() {
    local n=$1
    local name="ACS-1000-N${n}"
    local mpc_log="${LOGS_DIR}/${name}-${PROTOCOL}.log"
    local cli_log="${LOGS_DIR}/${name}-${PROTOCOL}-client.log"

    if [ -f "$mpc_log" ] && [ -f "$cli_log" ] && \
       grep -q "EXPERIMENT COMPLETE" "$mpc_log" 2>/dev/null && \
       grep -q "EXPERIMENT COMPLETE" "$cli_log" 2>/dev/null; then
        echo "  SKIP $name – already complete"
        return 0
    fi

    echo "  Running $name ..."
    PLAYERS="$n" ./Scripts/shamir.sh acs-reactive-1000-100 \
        > "$mpc_log" 2>&1 &
    local pid=$!

    wait_for_port 14000 "$mpc_log" || { kill $pid 2>/dev/null; exit 1; }

    ./ExternalIO/acs-reactive-client.py 0 "$n" 1000 100 \
        | tee "$cli_log"

    wait $pid
    echo "  Done: $name"
    sleep 2
}

run_locks() {
    local n=$1
    local name="LOCKS-1000-N${n}"
    local mpc_log="${LOGS_DIR}/${name}-${PROTOCOL}.log"
    local cli_log="${LOGS_DIR}/${name}-${PROTOCOL}-client.log"

    if [ -f "$mpc_log" ] && [ -f "$cli_log" ] && \
       grep -q "EXPERIMENT COMPLETE" "$mpc_log" 2>/dev/null && \
       grep -q "EXPERIMENT COMPLETE" "$cli_log" 2>/dev/null; then
        echo "  SKIP $name – already complete"
        return 0
    fi

    echo "  Running $name ..."
    PLAYERS="$n" ./Scripts/shamir.sh locks-reactive-1000-100 --batch-size 100 \
        > "$mpc_log" 2>&1 &
    local pid=$!

    wait_for_port 14000 "$mpc_log" || { kill $pid 2>/dev/null; exit 1; }

    ./ExternalIO/locks-reactive-client.py 0 "$n" 1000 100 \
        | tee "$cli_log"

    wait $pid
    echo "  Done: $name"
    sleep 2
}

run_prescar() {
    local n=$1
    local name="PRESCAR-1024D-N${n}"
    local mpc_log="${LOGS_DIR}/${name}-${PROTOCOL}.log"
    local cli_log="${LOGS_DIR}/${name}-${PROTOCOL}-client.log"

    if [ -f "$mpc_log" ] && [ -f "$cli_log" ] && \
       grep -q "EXPERIMENT COMPLETE" "$mpc_log" 2>/dev/null && \
       grep -q "EXPERIMENT COMPLETE" "$cli_log" 2>/dev/null; then
        echo "  SKIP $name – already complete"
        return 0
    fi

    echo "  Running $name ..."
    PLAYERS="$n" ./Scripts/shamir.sh presidential-car-reactive-1024-200 \
        > "$mpc_log" 2>&1 &
    local pid=$!

    wait_for_port 14001 "$mpc_log" 7200 || { kill $pid 2>/dev/null; exit 1; }

    ./ExternalIO/presidential-car-client.py 0 "$n" 1024 200 fault_last \
        | tee "$cli_log"

    wait $pid
    echo "  Done: $name"
    sleep 2
}

run_blood_sugar() {
    local n=$1
    local name="BLOODSUGAR-N${n}"
    local mpc_log="${LOGS_DIR}/${name}-${PROTOCOL}.log"
    local cli_log="${LOGS_DIR}/${name}-${PROTOCOL}-client.log"

    if [ -f "$mpc_log" ] && [ -f "$cli_log" ] && \
       grep -q "EXPERIMENT COMPLETE" "$mpc_log" 2>/dev/null && \
       grep -q "EXPERIMENT COMPLETE" "$cli_log" 2>/dev/null; then
        echo "  SKIP $name – already complete"
        return 0
    fi

    echo "  Running $name ..."
    PLAYERS="$n" ./Scripts/shamir.sh blood-sugar-monitor-1000 \
        > "$mpc_log" 2>&1 &
    local pid=$!

    wait_for_port 14001 "$mpc_log" || { kill $pid 2>/dev/null; exit 1; }

    ./ExternalIO/blood-sugar-monitor-client.py 0 "$n" 1000 \
        | tee "$cli_log"

    wait $pid
    echo "  Done: $name"
    sleep 2
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
echo "======================================================================"
echo "Party Scalability Experiments"
echo "======================================================================"
echo "Protocol : $PROTOCOL"
echo "Parties  : ${PARTY_COUNTS[*]}"
echo "Logs     : $LOGS_DIR"
echo "======================================================================"
echo ""

echo "--- Compile phase ---"
compile_once "acs-reactive-1000-100" \
    "Programs/Schedules/acs-reactive-1000-100.sch" \
    acs-reactive 1000 100 -F 128
compile_once "locks-reactive-1000-100" \
    "Programs/Schedules/locks-reactive-1000-100.sch" \
    locks-reactive 1000 100 -F 128
compile_once "presidential-car-reactive-1024-200" \
    "Programs/Schedules/presidential-car-reactive-1024-200.sch" \
    presidential-car-reactive 1024 200 -F 128
compile_once "blood-sugar-monitor-1000" \
    "Programs/Schedules/blood-sugar-monitor-1000.sch" \
    blood-sugar-monitor 1000 -F 64
echo ""

echo "--- Run phase ---"
for n in "${PARTY_COUNTS[@]}"; do
    echo "======================================================================"
    echo "N_PARTIES = $n"
    echo "======================================================================"

    echo "Setting up SSL certificates for $n parties..."
    ./Scripts/setup-ssl.sh "$n" > /dev/null 2>&1
    ./Scripts/setup-clients.sh 1 > /dev/null 2>&1
    echo "SSL ready."
    echo ""

    run_acs         "$n"
    run_locks       "$n"
    run_prescar     "$n"
    run_blood_sugar "$n"

    echo ""
done

echo "======================================================================"
echo "All scalability experiments complete!"
echo "Logs: $LOGS_DIR"
echo ""
echo "To analyze:"
echo "  python3 scalability-scripts/analyze-scalability-results.py"
echo "======================================================================"
