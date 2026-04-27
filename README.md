# Reactive Monitoring Experiments (experiments branch)

> **Note:** This is the `experiments` branch. For the original MP-SPDZ documentation, see the [`master` branch](../../tree/master).

---

# Reactive Monitoring Experiments - Setup and Usage Guide

## Overview

This guide covers how to build, run, and analyze the four reactive monitoring scenarios built on top of the MP-SPDZ framework. Each scenario follows the same pipeline: compile an MPC program, launch MPC server parties, connect a Python client, and collect results.

The four scenarios are:

| Scenario | What it monitors | MPC Program | Client Script |
|----------|-----------------|-------------|---------------|
| **ACS** | Door passage counts | `acs-reactive.mpc` | `acs-reactive-client.py` |
| **Blood Sugar** | Glucose levels in a time window | `blood-sugar-monitor.mpc` | `blood-sugar-monitor-client.py` |
| **Presidential Car** | Vehicle location vs. adaptive geofence | `presidential-car-reactive.mpc` | `presidential-car-client.py` |
| **Locks** | Parallel lock state violations | `locks-reactive.mpc` | `locks-reactive-client.py` |

---

## Where Everything Lives

Make sure you are in the MP-SPDZ root directory before running anything.

```
MP-SPDZ/                              <-- you should be here
|
|-- compile.py                         <-- compiles .mpc files to bytecode
|-- shamir-party.x                     <-- the Shamir protocol virtual machine (built by make)
|
|-- Scripts/
|   |-- compile-run.py                 <-- compiles AND runs in one command
|   |-- setup-ssl.sh                   <-- generates SSL certs for MPC parties
|   |-- setup-clients.sh               <-- generates SSL certs for clients
|   |-- run-common.sh                  <-- helper that spawns one process per party
|   '-- shamir.sh, mascot.sh, ...      <-- per-protocol run wrappers
|
|-- Programs/
|   |-- Source/
|   |   |-- acs-reactive.mpc           <-- MPC source (the "spec function" logic)
|   |   |-- blood-sugar-monitor.mpc
|   |   |-- presidential-car-reactive.mpc
|   |   |-- locks-reactive.mpc
|   |   '-- template-monitor.mpc       <-- skeleton for writing new scenarios
|   |-- Bytecode/                      <-- generated: compiled .bc files land here
|   '-- Schedules/                     <-- generated: .sch schedule files land here
|
|-- ExternalIO/
|   |-- acs-reactive-client.py         <-- Python client for ACS
|   |-- blood-sugar-monitor-client.py
|   |-- presidential-car-client.py
|   |-- locks-reactive-client.py
|   '-- client.py                      <-- shared client library (connection, SSL, I/O)
|
|-- Player-Data/
|   |-- P0.pem, P0.key                 <-- generated: SSL certs for party 0
|   |-- P1.pem, P1.key                 <-- generated: SSL certs for party 1
|   |-- P2.pem, P2.key                 <-- generated: SSL certs for party 2
|   '-- C0.pem, C0.key                 <-- generated: SSL cert for client 0
|
|-- .venv/                             <-- Python virtual environment (has gmpy2)
|
|-- acs-scripts/                       <-- test/experiment/analysis scripts for ACS
|   |-- test-acs.sh
|   |-- run-acs-experiments.sh
|   |-- analyze-acs-results.py
|   '-- logs/                          <-- generated: experiment logs land here
|       |-- test-mpc.log
|       |-- test-client.log
|       |-- ACS-10-shamir.log
|       |-- ACS-10-shamir-client.log
|       '-- ...
|
|-- blood-sugar-scripts/
|   |-- test-blood-sugar.sh
|   '-- logs/
|
|-- presidential-car-scripts/
|   |-- test-presidential-car.sh
|   |-- run-presidential-car-experiments.sh
|   |-- analyze-prescar-results.py
|   '-- logs/
|
|-- locks-scripts/
|   |-- test-locks.sh
|   |-- run-locks-experiments.sh
|   |-- analyze-locks-results.py
|   '-- logs/
|
'-- scalability-scripts/                  <-- party-scaling sweep across all four scenarios
    |-- run-all-scalability.sh
    '-- analyze-scalability-results.py
```

(Logs from the party-scaling sweep land in `logs/scalability/`, alongside MP-SPDZ's own per-party runtime logs in `logs/`.)

**Key point:** All commands must be run from the `MP-SPDZ/` root directory. The scripts use relative paths like `./Scripts/compile-run.py` and `./ExternalIO/acs-reactive-client.py`.

---

## Step-by-Step: First-Time Setup

### 1. Build the MP-SPDZ Framework

If you haven't built MP-SPDZ yet:

```bash
make setup                    # downloads and builds dependencies (GMP, libsodium, etc.)
make shamir-party.x           # builds the Shamir protocol virtual machine
```

This produces the `shamir-party.x` binary in the project root. You only need to do this once.

**Requirements:** GCC 7+ or Clang 11+, Python 3, GMP (with C++ support), libsodium, OpenSSL, Boost.

### 2. Set Up the Python Virtual Environment

The client scripts need `gmpy2` for modular arithmetic (computing Montgomery representation inverses for finite field operations). You have two options:

**Option A: Use the existing .venv (recommended)**

```bash
python3 -m venv --without-pip .venv
# Then install gmpy2 into it:
.venv/bin/pip install gmpy2
# OR, if pip isn't available in the venv:
pip install --target=.venv/lib/python3.12/site-packages gmpy2
```

The client scripts auto-detect `.venv/` and add its site-packages to `sys.path` at startup, so you do **not** need to `source .venv/bin/activate` before running them. This snippet (from the client scripts) handles it:

```python
venv_lib = os.path.join(base_dir, '.venv', 'lib')
for item in os.listdir(venv_lib):
    if item.startswith('python'):
        sys.path.insert(0, os.path.join(venv_lib, item, 'site-packages'))
        break
```

**Option B: System-wide install**

```bash
pip install gmpy2
```

This works but may interfere with system packages.

### 3. Generate SSL Certificates

Shamir secret sharing requires SSL for inter-party communication. Certificates **expire after 30 days**, so you need to regenerate them periodically.

```bash
Scripts/setup-ssl.sh 3           # generates P0.pem/key, P1.pem/key, P2.pem/key
Scripts/setup-clients.sh 1       # generates C0.pem/key for the client
```

Both commands write into `Player-Data/`.

**If you see `SSLV3_ALERT_CERTIFICATE_EXPIRED` errors**, just re-run these two commands.

---

## Step-by-Step: Running a Scenario

The pipeline for every scenario is the same:

```
  +-------------------+      +-------------------+      +-------------------+
  | 1. COMPILE        |      | 2. MPC SERVER     |      | 3. CLIENT         |
  |                   | ---> |                   | <--> |                   |
  | compile-run.py    |      | 3 shamir-party.x  |      | *-client.py       |
  | reads .mpc source |      | processes wait    |      | connects, sends   |
  | writes bytecode   |      | for client on     |      | data, receives    |
  | then launches     |      | port 14000/14001  |      | fault results     |
  | the 3 parties     |      |                   |      |                   |
  +-------------------+      +-------------------+      +-------------------+
         |                          |                          |
         v                          v                          v
  Programs/Bytecode/         (runtime, in memory)        logs/*-client.log
  Programs/Schedules/        logs/*-mpc.log
```

### Quick Test (any scenario)

Each scenario has a test script that runs a small, fast test:

```bash
# Pick any one:
bash acs-scripts/test-acs.sh
bash blood-sugar-scripts/test-blood-sugar.sh
bash presidential-car-scripts/test-presidential-car.sh
bash locks-scripts/test-locks.sh
```

The test script does everything automatically:
1. Compiles the MPC program
2. Launches 3 MPC party processes in the background
3. Waits for the server port to become available (up to 60 seconds)
4. Runs the client
5. Saves logs

### Manual Execution (step by step)

If you want to run things by hand, here is what the test scripts do under the hood.

**Terminal 1 -- MPC Server** (compile + run):

```bash
# General form:
Scripts/compile-run.py shamir <program> [program-args...] -F <field-bits> -- -N 3

# ACS example (10 doors, 3 iterations, 128-bit field):
Scripts/compile-run.py shamir acs-reactive 10 3 -F 128 -- -N 3

# Blood sugar example (1000 iterations, 64-bit field):
Scripts/compile-run.py shamir blood-sugar-monitor 1000 -F 64 -- -N 3

# Presidential car example (2 dimensions, 3 iterations):
Scripts/compile-run.py shamir presidential-car-reactive 2 3 -F 128 -- -N 3

# Locks example (8 locks, 5 iterations, batch-size 100):
Scripts/compile-run.py shamir locks-reactive 8 5 -F 128 -- -N 3 --batch-size 100
```

Arguments before `--` are compilation options. Arguments after `--` are runtime options.

Wait until you see `listening on port 14000` (or 14001) in the output.

**Terminal 2 -- Client:**

```bash
# General form:
./ExternalIO/<client-script> <client-id> <n-parties> [scenario-params...]

# ACS (client 0, 3 parties, 10 doors, 3 iterations):
./ExternalIO/acs-reactive-client.py 0 3 10 3

# Blood sugar (client 0, 3 parties, 1000 iterations):
./ExternalIO/blood-sugar-monitor-client.py 0 3 1000

# Presidential car (client 0, 3 parties, 2 dimensions, 3 iterations, fault_last mode):
./ExternalIO/presidential-car-client.py 0 3 2 3 fault_last

# Locks (client 0, 3 parties, 8 locks, 5 iterations):
./ExternalIO/locks-reactive-client.py 0 3 8 5
```

**Important:** The program arguments (door count, iterations, etc.) must match between server and client.

---

## What the Output Looks Like

### Client Output (ACS example with 10 doors, 3 iterations)

```
Connecting to 3 parties on port 14000...
Connected!

............................................................
ITERATION 1/3
............................................................
Sending 40 sensor values...
Sensor data sent! 40 values (320 bytes) in 0.001583s
Waiting for results...

RESULTS (Iteration 1):
------------------------------------------------------------
Fault:   0
Status: Normal operation

Client Timing (Iteration 1):
  Send:    0.001583 seconds
  Receive: 0.077346 seconds
  TOTAL:   0.078945 seconds

............................................................
ITERATION 2/3
............................................................
Sending 40 sensor values...
Sensor data sent! 40 values (320 bytes) in 0.001759s
Waiting for results...

RESULTS (Iteration 2):
------------------------------------------------------------
Fault:   0
Status: Normal operation

............................................................
ITERATION 3/3
............................................................
Sending 40 sensor values...
Sensor data sent! 40 values (320 bytes) in 0.005575s
Waiting for results...

RESULTS (Iteration 3):
------------------------------------------------------------
Fault:   1
WARNING: Fault condition detected (Count A < Count B)

------------------------------------------------------------
EXPERIMENT COMPLETE
------------------------------------------------------------

Configuration:
  Client ID: 0
  MPC Parties: 3
  Doors: 10
  Iterations: 3

Timing Metrics:
  Total experiment time: 1.233s
  Average iteration time: 0.077s
  Min iteration time: 0.075s
  Max iteration time: 0.079s

Communication Metrics:
  Total values sent: 120
  Total values received: 3
  Total bytes sent: 960 (0.94 KB)
  Total bytes received: 24 (0.02 KB)

Throughput:
  Iterations per second: 2.43
```

### MPC Server Output (tail end of the same run)

```
============================================================
EXPERIMENT COMPLETE
============================================================
Configuration:
  Doors: 10
  Iterations: 3

Timing Breakdown:
  Timer 1 (TOTAL): Total iteration time
  Timer 10 (RECEIVE): Client data receive
  Timer 11 (COMPUTE): Spec function execution
  Timer 12 (REVEAL): Result revelation
  Timer 13 (SEND): Client data send

Time1 = 1.24606 seconds (0.130419 MB, 630 rounds)
Time10 = 1.14594 seconds (0.006544 MB, 4 rounds)
Time11 = 0.0925152 seconds (0.003195 MB, 609 rounds)
Time12 = 0.000847179 seconds (0.000432 MB, 6 rounds)
Time13 = 0.00617592 seconds (0.120248 MB, 11 rounds)
Data sent = 0.130515 MB in ~632 rounds (party 0 only)
Global data sent = 0.389643 MB (all parties)
Actual preprocessing cost of program:
  Type int
           120        Triples
             3         daBits
  edaBits
             3 of length 41 (strict)
             3 of length 128 (strict)
```

---

## Running Full Experiments

The experiment scripts run parameter sweeps and collect logs for analysis.

```
  +-----------------------+      +-----------------------+      +-----------------------+
  | EXPERIMENT SCRIPT     |      | LOG FILES             |      | ANALYSIS SCRIPT       |
  |                       | ---> |                       | ---> |                       |
  | run-*-experiments.sh  |      | logs/*-shamir.log     |      | analyze-*-results.py  |
  | loops over parameter  |      | logs/*-client.log     |      | parses logs, prints   |
  | values, runs server + |      | (one pair per         |      | tables for the paper  |
  | client for each       |      |  parameter value)     |      |                       |
  +-----------------------+      +-----------------------+      +-----------------------+
```

### Experiment Parameter Sweeps

| Scenario | Script | Parameter | Values Tested | Iterations |
|----------|--------|-----------|---------------|------------|
| ACS | `acs-scripts/run-acs-experiments.sh` | Doors | 10, 30, 100, 300, 1000 | 100 |
| Presidential Car | `presidential-car-scripts/run-presidential-car-experiments.sh` | Dimensions | 2, 4, 8, ..., 2048, 4096 | 200 |
| Locks | `locks-scripts/run-locks-experiments.sh` | Locks | 100, 300, 500, 1000 | 100 |
| Blood Sugar | `blood-sugar-scripts/test-blood-sugar.sh` | (fixed) | 1000 iterations | 1000 |
| All four (party scaling) | `scalability-scripts/run-all-scalability.sh` | Number of Monitor parties | 3, 5, 7, 9, 11 | per-scenario (see above) |

### Running experiments and analyzing results

```bash
# 1. Quick test to verify everything works
bash acs-scripts/test-acs.sh

# 2. Run the full parameter sweep (takes a while)
bash acs-scripts/run-acs-experiments.sh

# 3. Parse logs and print comparison tables
python3 acs-scripts/analyze-acs-results.py
```

Same pattern for the other scenarios:

```bash
bash presidential-car-scripts/run-presidential-car-experiments.sh
python3 presidential-car-scripts/analyze-prescar-results.py

bash locks-scripts/run-locks-experiments.sh
python3 locks-scripts/analyze-locks-results.py
```

#### Party-scaling sweep (all four scenarios at largest parameter, varying $N$)

`run-all-scalability.sh` re-runs each scenario at its largest parameter while
sweeping the number of Monitor parties $N \in \{3, 5, 7, 9, 11\}$. Each circuit
is compiled once up front, and the same bytecode is reused across every party
count (the bytecode does not depend on $N$).

```bash
bash scalability-scripts/run-all-scalability.sh
python3 scalability-scripts/analyze-scalability-results.py
```

Logs land in `logs/scalability/` with names like `ACS-1000-N5-shamir.log`
and `PRESCAR-1024D-N7-shamir-client.log`. The analyzer prints per-iteration
total time, per-iteration data sent, and a per-scenario timing breakdown,
all indexed by $N$.

### Where Logs End Up

```
acs-scripts/logs/
|-- test-mpc.log                   <-- from test-acs.sh
|-- test-client.log                <-- from test-acs.sh
|-- ACS-10-shamir.log              <-- MPC server log (10 doors)
|-- ACS-10-shamir-client.log       <-- client log (10 doors)
|-- ACS-30-shamir.log              <-- MPC server log (30 doors)
|-- ACS-30-shamir-client.log       <-- client log (30 doors)
|-- ACS-100-shamir.log
|-- ACS-100-shamir-client.log
'-- ...

presidential-car-scripts/logs/
|-- PRESCAR-2D-shamir.log
|-- PRESCAR-2D-shamir-client.log
|-- PRESCAR-4D-shamir.log
'-- ...

locks-scripts/logs/
|-- LOCKS-100-shamir.log
|-- LOCKS-100-shamir-client.log
'-- ...
```

The experiment scripts have skip logic: if both log files exist and contain `EXPERIMENT COMPLETE`, the run is skipped. Delete the log files to re-run an experiment.

---

## Files to Read to Understand the Code

If you are new to this project, read these files in this order:

### 1. The Template (start here)

**`Programs/Source/template-monitor.mpc`** -- A skeleton showing the minimal structure of a reactive monitor. All four scenarios follow this pattern: accept client, loop, receive inputs, compute spec function, send output.

### 2. The Simplest Scenario

**`Programs/Source/blood-sugar-monitor.mpc`** -- Only 2 inputs per iteration (time, blood_sugar), one threshold comparison, one latching fault bit. Easiest to understand.

**`ExternalIO/blood-sugar-monitor-client.py`** -- Shows how the client connects via SSL, secret-shares inputs, and receives revealed outputs.

### 3. A More Complex Scenario

**`Programs/Source/acs-reactive.mpc`** -- Adds arrays (per-door iteration), accumulator state, and fault-triggered state freezing.

### 4. The Client Library

**`ExternalIO/client.py`** -- The shared library all clients use. Handles SSL connections, secret sharing, and value packing/unpacking.

### 5. The Execution Infrastructure

**`Scripts/compile-run.py`** -- The entry point that compiles `.mpc` to bytecode and then launches party processes.

**`Scripts/run-common.sh`** -- The shell helper that spawns one `shamir-party.x` process per party on localhost.

---

## Port Usage

| Scenario | Port |
|----------|------|
| ACS | 14000 |
| Blood Sugar | 14001 |
| Presidential Car | 14001 |
| Locks | 14000 |

If a port is already in use from a previous run, kill stale processes:

```bash
# Find what's on port 14000
ss -tuln | grep 14000
# Or kill all shamir-party processes
pkill -f shamir-party.x
```

---

## Troubleshooting

### SSL certificate expired

```
SSL error: handshake: sslv3 alert certificate expired
```

Certificates expire after 30 days. Regenerate them:

```bash
Scripts/setup-ssl.sh 3
Scripts/setup-clients.sh 1
```

### MPC server did not start

The test scripts wait up to 60 seconds; the experiment scripts wait up to 600 seconds. If the server still doesn't start, check the MPC log for compilation errors (e.g., missing source file, wrong arguments).

### Client hangs after connecting

The client and server parameter counts must match exactly. If the server was compiled with 10 doors but the client sends data for 30 doors, the client will hang waiting for a response that never comes.

### gmpy2 not found

```
ModuleNotFoundError: No module named 'gmpy2'
```

Either install into the `.venv`:

```bash
pip install --target=.venv/lib/python3.12/site-packages gmpy2
```

Or install system-wide: `pip install gmpy2`.

### "Not compiled for 320-bit primes"

You are trying to use `-F 256` but the executable was not built for it. Edit `CONFIG.mine`:

```bash
echo "MOD = -DGFP_MOD_SZ=5" >> CONFIG.mine
make shamir-party.x
```

---

> For the original MP-SPDZ documentation (protocols, compilation options, benchmarking), see the [`master` branch](../../tree/master).
