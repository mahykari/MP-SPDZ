# ACS Reactive Door Monitoring System - Complete Guide

## Overview

This guide documents the reactive door monitoring system implementation using MP-SPDZ's Shamir secret sharing protocol with external I/O. It covers both basic usage and experimental evaluation for research comparison.

## Quick Start

### Basic Usage

**Compile and Run the MPC Program**

```bash
# Standard security (64-bit field)
Scripts/compile-run.py shamir acs-reactive -- -N 3 --batch-size 30

# High security (128-bit field)
Scripts/compile-run.py shamir acs-reactive -F 128 -- -N 3 --batch-size 30

# Maximum security (256-bit field)
Scripts/compile-run.py shamir acs-reactive -F 256 -- -N 3 --batch-size 30
```

### Run the Client

```bash
# Basic usage
./ExternalIO/acs-reactive-client.py 0 3 5

# With custom data file
./ExternalIO/acs-reactive-client.py 0 3 5 sensor_data.txt
```

**Client Parameters:**
- `0` - Client ID
- `3` - Number of MPC parties
- `5` - Number of iterations/sensor readings
- `sensor_data.txt` - Optional: custom sensor data file

## Security Configuration

### Shamir Secret Sharing Security Options

#### Compilation-Time Options (before `--`)

**Field Bit Length:**
```bash
-F <bits>  or  --field <bits>
```
- Default: 64 bits
- Options: 64, 128, 256
- Higher values prevent overflow and provide larger value ranges
- Example: `-F 128`

**Alternative Bit Length Flag:**
```bash
-l <bits>
```
- Same as `-F`, alternative syntax
- Example: `-l 128`

**Custom Prime:**
```bash
-P <prime>  or  --prime <prime>
```
- Use a specific prime modulus
- Example: `-P 2305843009213693951`

#### Runtime Options (after `--`)

**Number of Parties:**
```bash
-N <number>  or  --nparties <number>
```
- Default: 3
- More parties = can tolerate more corruptions
- Example: `-N 5`

**Corruption Threshold:**
```bash
-T <number>  or  --threshold <number>
```
- Default: `(N-1)/2` (just below half)
- Maximum number of parties that can be corrupted
- Must satisfy: `2*T < N`
- Example: `-T 2` (with 5 parties)

**Batch Size:**
```bash
--batch-size <number>
```
- Default: 10000
- Size of preprocessing batches
- Smaller values reduce memory usage but may impact performance
- Example: `--batch-size 30`

### Security Properties of Shamir

- **Information-theoretically secure** for privacy (no computational assumptions needed)
- Security against `T` corrupted parties out of `N` total
- Field size prevents overflow but doesn't affect privacy directly
- No runtime statistical security parameter (unlike SPDZ protocols)

### Field Size vs Public-Key Bit Lengths

**Why Shamir doesn't need 1536+ bit keys like garbled circuits:**

Shamir secret sharing and garbled circuits have fundamentally different security models:

**Garbled Circuits (Public-Key Cryptography):**
- Uses public-key cryptography (DDH-based schemes)
- Security relies on **computational hardness** of problems like discrete logarithm or factoring
- Requires **1536-2048+ bit keys** to resist factoring/discrete log attacks
- Security depends on the attacker's computational limits
- An attacker with sufficient computing power could eventually break it

**Shamir Secret Sharing (Information-Theoretic Security):**
- Uses **information-theoretic security** in finite fields
- Security doesn't depend on any computational hardness assumptions
- A **128-bit field** provides:
  - 2^128 field elements (computationally infeasible to brute force)
  - ~128-bit statistical security (comparable to AES-128)
  - Sufficient range for arithmetic operations
- **Unconditionally secure**: An attacker with unlimited computational power still cannot break it with fewer than the threshold number of shares

**Key Insight:** You only need the field to be large enough to:
1. Prevent exhaustive search (128 bits ✓)
2. Hold your computed values without overflow (easily satisfied ✓)
3. Provide adequate statistical security (128 bits ✓)

The 1536+ bit requirement is specific to cryptographic primitives used in garbled circuits and other public-key schemes. For Shamir secret sharing, 64-128 bit fields are standard and sufficient for most applications.

### Recommended Configurations

**Standard Security:**
```bash
Scripts/compile-run.py shamir acs-reactive -- -N 3 --batch-size 30
```
- 64-bit field
- 3 parties, threshold 1
- Good for testing and moderate security requirements

**High Security:**
```bash
Scripts/compile-run.py shamir acs-reactive -F 128 -- -N 5 -T 2 --batch-size 30
```
- 128-bit field (matches AES-128)
- 5 parties, threshold 2
- Recommended for production use

**Maximum Security:**
```bash
Scripts/compile-run.py shamir acs-reactive -F 256 -- -N 7 -T 3 --batch-size 30
```
- 256-bit field (matches AES-256)
- 7 parties, threshold 3
- Maximum security for highly sensitive applications
- **Note**: Requires recompiling with larger prime support (see below)

## Program Features

### Timing Measurements

The MPC program includes precise timing for each iteration:
- **Timer 1**: Total iteration time
- **Timer 10**: Receive time (getting sensor data from client)
- **Timer 11**: Compute time (running spec_function)
- **Timer 12**: Reveal time (opening shares)
- **Timer 13**: Send time (sending results to client)

Timing results are displayed at the end of execution and exclude preprocessing overhead.

### Client Timing

The client also measures:
- **Send time**: Time to send sensor data
- **Receive time**: Time to receive results
- **Total time**: Complete iteration time

### Fault Detection

The system detects fault conditions where `cntA < cntB`:
- When a fault is detected, the state is **not updated**
- The system reverts to the previous known-good state
- Only the fault bit is sent to the client (counts are kept private)

### Last Iteration Behavior

By default, the last iteration is configured to trigger a fault for testing purposes. The sample data generator creates sensor readings that cause `cntB > cntA` in the final iteration.

## File Structure

```
ExternalIO/
  acs-reactive-client.py     # Client that sends sensor data
Programs/Source/
  acs-reactive.mpc            # MPC program for door monitoring
```

## Custom Data Format

If providing a custom data file, format it as:
```
n_iterations * n_doors * 4 values
```

Each door needs 4 values per iteration:
- `enteredA` - People entering through side A
- `exitedA` - People exiting through side A  
- `enteredB` - People entering through side B
- `exitedB` - People exiting through side B

Example for 5 iterations, 10 doors:
```
0 1 2 0  1 2 3 1  ...  (40 values for iteration 1)
1 0 3 2  2 1 4 3  ...  (40 values for iteration 2)
...
```

## Enabling 256-bit Field Support

By default, MP-SPDZ is compiled for up to 128-bit primes. To use 256-bit fields:

1. **Edit CONFIG.mine** (create it if it doesn't exist):
   ```bash
   echo "MOD = -DGFP_MOD_SZ=5" >> CONFIG.mine
   ```

2. **Recompile the executable**:
   ```bash
   make shamir-party.x
   ```

3. **Now you can use 256-bit fields**:
   ```bash
   Scripts/compile-run.py shamir acs-reactive -F 256 -- -N 3 --batch-size 30
   ```

**Prime size table:**
- `DGFP_MOD_SZ=2`: Up to 128-bit primes (default)
- `DGFP_MOD_SZ=3`: Up to 192-bit primes
- `DGFP_MOD_SZ=4`: Up to 256-bit primes
- `DGFP_MOD_SZ=5`: Up to 320-bit primes (supports -F 256)

## Troubleshooting

### "Not compiled for 320-bit primes"
- You're trying to use `-F 256` but the executable doesn't support it
- Follow the steps in "Enabling 256-bit Field Support" above
- After recompiling, the 256-bit field will work

### "Additional argument has to be integer: -s"
- The `-s` flag is for compilation (stops on register errors), not runtime security
- For Shamir, there is no runtime `-S` security parameter
- Use `-F` at compilation time instead

### "ring option not compatible with shamir"
- Don't use `-R` flag with Shamir (that's for ring-based protocols)
- Use `-F` or `-l` for field bit length instead

### Client connection errors
- Ensure the MPC program is running first
- Check that port 14000 is available
- Verify the number of parties matches between client and MPC

### Memory warnings during compilation
- Use `--batch-size 30` or lower to reduce memory usage
- Consider using `-M` to preserve memory instruction order if needed

### SSL Certificate Errors

If you see handshake failures, regenerate certificates:

```bash
Scripts/setup-ssl.sh 3
```

(Certificates expire after 30 days by default)

## Performance Notes

- Larger field sizes (`-F 256`) increase computation time and bandwidth
- More parties increase communication rounds
- Smaller batch sizes reduce memory but may reduce throughput
- Timing measurements exclude preprocessing (offline phase)

---

# Experimental Evaluation

## Overview

This section covers parameterized experiments for comparing the ACS door monitoring scenario against the paper's results.

## Configuration Parameters

### Door Counts (matching paper)
- **ACS-10**: 10 external doors
- **ACS-30**: 30 external doors

### MPC Configuration
- **Protocol**: Shamir secret sharing (3-out-of-3)
- **Security**: Semi-honest with honest majority
- **Field**: 64-bit ring (configurable with -R flag)
- **Iterations**: 5 reactive rounds per experiment

## Parameterized Usage

### MPC Program with Parameters

```bash
# Compile and run with custom door count and iterations
Scripts/compile-run.py shamir acs-reactive 10 5 -- -N 3

# 30 doors, 5 iterations
Scripts/compile-run.py shamir acs-reactive 30 5 -- -N 3
```

**Arguments:**
- First argument after program name: number of doors
- Second argument: number of iterations
- Arguments after `--` are runtime options (party count, etc.)

### Client with Parameters

```bash
# 10 doors, 5 iterations
./ExternalIO/acs-reactive-client.py 0 3 10 5

# 30 doors, 5 iterations
./ExternalIO/acs-reactive-client.py 0 3 30 5

# With custom data file
./ExternalIO/acs-reactive-client.py 0 3 10 5 sensor_data.txt
```

**Parameters:**
- `client_id` - Client identifier (usually 0)
- `n_parties` - Number of MPC parties (must match MPC server)
- `n_doors` - Number of doors (must match MPC server)
- `n_iterations` - Number of sensor readings
- `data_file` - Optional: custom sensor data file

## Automated Experiment Scripts

### 1. Quick Test

```bash
./test-acs.sh
```

Runs a quick test with 10 doors and 3 iterations. Use this to verify the setup before running full experiments.

**Outputs:**
- `logs/test-mpc.log` - MPC server log
- `logs/test-client.log` - Client log

### 2. Full Experiments (10 & 30 doors)

```bash
./run-acs-experiments.sh
```

Runs experiments for both 10 and 30 doors with 5 iterations each, matching the paper's configuration.

**Outputs:**
- `logs/ACS-10-shamir.log` - MPC server log (10 doors)
- `logs/ACS-10-shamir-client.log` - Client log (10 doors)
- `logs/ACS-30-shamir.log` - MPC server log (30 doors)
- `logs/ACS-30-shamir-client.log` - Client log (30 doors)

### 3. Protocol Comparison

```bash
./compare-protocols.sh
```

Tests different MPC protocols (shamir, replicated, semi) with 10 doors to compare performance.

**Outputs:**
- `logs/ACS-10-{protocol}.log` - MPC server logs
- `logs/ACS-10-{protocol}-client.log` - Client logs

### 4. Result Analysis

```bash
./analyze-acs-results.py
```

Parses log files and generates comparison tables for the paper.

**Output Tables:**
1. **Circuit Complexity** - Operation counts per iteration (multiplications, comparisons)
2. **Execution Time** - End-to-end timing and throughput
3. **Communication Costs** - Data volumes per iteration
4. **Timing Breakdown** - Detailed phase-by-phase timing
5. **Protocol Comparison** - Performance across different protocols (if multiple tested)

## Metrics Tracked

### MPC Server Metrics

**Operation Counts:**
- Total multiplications (secret-sharing expensive operations)
- Total comparisons (fault condition checking)
- Per-iteration averages

**Communication:**
- Values received from client
- Values sent to client  
- Per-iteration averages

**Detailed Timing (5 timers):**
- Timer 1: Total iteration time
- Timer 10: Client data receive time
- Timer 11: Spec function execution time
- Timer 12: Result revelation time
- Timer 13: Client data send time

### Client Metrics

**Timing:**
- Total experiment time
- Average/min/max iteration time
- Average send/receive times
- Throughput (iterations per second)

**Communication:**
- Total values/bytes sent and received
- Per-iteration averages
- Bandwidth calculations (KB/s)

## Log Files Explained

### Experiment Logs
- **ACS-{doors}-{protocol}.log** - Combined MPC server output (all parties)
- **ACS-{doors}-{protocol}-client.log** - Client-side metrics
- **test-mpc.log / test-client.log** - Quick test outputs

### Individual Party Logs
- **acs-reactive-{doors}-{iterations}-{party}** - Individual party logs
  - Example: `acs-reactive-10-5-0` = Party 0, 10 doors, 5 iterations
  - Parties numbered 0, 1, 2
  - Kept for debugging; Party 0 typically has complete metrics

## Understanding the Results

### Circuit Complexity

**Multiplications:**
- Most expensive operation in secret sharing
- Formula: 4 multiplications per iteration (for fault condition handling)
- Counts secret multiplication operations (not simple additions)

**Comparisons:**
- 1 comparison per iteration (cntA < cntB check)
- Cost depends on bit-length of comparison
- Uses bit decomposition and circuits

**Total Operations:**
- Sum of multiplications and comparisons
- Linear scaling with door count

### Communication Volumes

**Per Iteration:**
- Client sends: n_doors × 4 values (enteredA, exitedA, enteredB, exitedB)
- Client receives: 1 value (fault bit)
- Total: scales linearly with door count

### Timing

**Expected Scaling:**
- Operations scale linearly with door count
- Communication rounds remain constant
- Network latency affects overall timing
- Preprocessing (offline phase) excluded from measurements

### Comparison to Paper

**Their approach (ZK proofs over DDH groups):**
- Circuit size: Boolean gates (register width affects gate count)
- Security: Computational (based on DDH hardness)
- Gate types: AND, XOR gates in Boolean circuit

**Our approach (Shamir secret sharing):**
- Circuit size: Secret-sharing operations (field multiplications, comparisons)
- Security: Information-theoretic (unconditionally secure)
- Operation types: Field arithmetic, bit decomposition

**Comparison Strategy:**
- Focus on **relative scaling** (how performance changes with door count)
- Emphasize **absolute timing** improvements
- Note that register width (16-bit vs 32-bit) doesn't directly translate
  - In Boolean circuits: more bits = more gates
  - In our approach: field size is fixed, bit-length matters for comparisons only

## Running Experiments

### Quick Start Workflow

```bash
# 1. Quick test to verify setup
./test-acs.sh

# 2. Run full experiments (10 & 30 doors)
./run-acs-experiments.sh

# 3. Analyze and generate tables
./analyze-acs-results.py
```

### Testing Different Protocols

Edit `run-acs-experiments.sh` or `compare-protocols.sh` to change protocol:

```bash
PROTOCOL="replicated"  # or "semi", "semi2k", etc.
```

Available protocols (semi-honest, honest majority):
- **shamir** - Shamir secret sharing
- **replicated** - Replicated secret sharing (optimized for 3 parties)
- **semi** - Generic semi-honest protocol
- **semi2k** - Ring-based semi-honest protocol

### Manual Execution

```bash
# 1. Compile
./compile.py -R 64 acs-reactive

# 2. Run MPC server (in background)
Scripts/compile-run.py shamir acs-reactive 10 5 -- -N 3 > logs/manual-mpc.log 2>&1 &

# 3. Wait for server to start
sleep 3

# 4. Run client
./ExternalIO/acs-reactive-client.py 0 3 10 5 | tee logs/manual-client.log
```

## Troubleshooting Experiments

### SSL Certificate Errors

Regenerate certificates:

```bash
Scripts/setup-ssl.sh 3
```

### Client Connection Refused

- MPC server not started yet (wait 3-5 seconds after starting)
- Port 14000 already in use (check for existing processes)
- Wrong number of parties (client and server must match)

### Mismatched Door Counts

If client and server have different door counts, the client will hang waiting for a response. Ensure both use the same values.

### Out of Memory During Compilation

Use smaller batch sizes:

```bash
Scripts/compile-run.py shamir acs-reactive 30 5 -- -N 3 --batch-size 30
```

## Performance Notes

- **Field size**: Larger fields (128-bit, 256-bit) increase computation time
- **Door count**: Linear impact on operations and communication
- **Party count**: More parties = more communication rounds
- **Protocol choice**: Replicated is fastest for 3 parties; Shamir more flexible
- **Timing exclusions**: Preprocessing/offline phase excluded from measurements

## Next Steps for Research

1. **Run all experiments** using `./run-acs-experiments.sh`
2. **Generate comparison tables** with `./analyze-acs-results.py`
3. **Extract key metrics** from tables for paper
4. **Test additional protocols** if needed for comparison
5. **Vary party counts** (3, 5, 7 parties) for scalability analysis
6. **Compare against paper's results** focusing on:
   - Absolute timing (we should be faster)
   - Relative scaling (similar linear growth)
   - Communication efficiency
