# ACS Reactive Door Monitoring System - Usage Guide

## Overview

This guide documents the reactive door monitoring system implementation using MP-SPDZ's Shamir secret sharing protocol with external I/O.

## Quick Start

### Compile and Run the MPC Program

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

## Performance Notes

- Larger field sizes (`-F 256`) increase computation time and bandwidth
- More parties increase communication rounds
- Smaller batch sizes reduce memory but may reduce throughput
- Timing measurements exclude preprocessing (offline phase)

## Network Security: Party-to-Party Communication

### Default Security Model

Party-to-party communication security depends on the protocol type:

**Shamir (Honest-Majority Protocols):**
- **Default: TLS-encrypted** via `CryptoPlayer`
- Provides confidentiality and authentication
- Uses OpenSSL with TLS 1.2

**SPDZ (Dishonest-Majority Protocols):**
- **Default: Unencrypted** via `PlainPlayer`
- Protocol itself provides cryptographic security
- Plaintext TCP sockets for performance

### TLS Encryption Details

**Certificate-Based Authentication:**
- X.509 certificates for each party
- Location: `Player-Data/P<i>.pem` (certificate) and `P<i>.key` (private key)
- Common name format: `P<player_number>` (e.g., P0, P1, P2)
- Algorithm: RSA with self-signed certificates
- **Default Validity: 1 month**
- ⚠️ **Important**: Certificates expire after 30 days, requiring system restart with renewed certificates

**Connection Architecture:**
- **Two separate TLS connections** per party pair
  - One dedicated for sending
  - One dedicated for receiving
- Runs in separate threads for simultaneous bidirectional communication
- Required because TLS has key renewals that prevent true one-way communication
- Protocol: TLS 1.2 (OpenSSL via Boost.Asio SSL streams)

### Setting Up Encrypted Communication

**1. Generate Certificates:**
```bash
Scripts/setup-ssl.sh 3
```
- Generates certificates for 3 parties (P0, P1, P2)
- Creates `Player-Data/P*.pem` and `Player-Data/P*.key` files

**2. Hash Certificate Directory:**
```bash
c_rehash Player-Data/
```
- Creates symlinks for certificate lookup
- Must be run on all hosts

**3. Certificate Distribution:**
- **All parties must have the same certificates** (copy entire Player-Data/ directory)
- Certificates should be identical on every host
- Include `.pem`, `.key`, and `.0` (symlink) files

**4. Verification:**
Check certificate signatures match across parties:
```bash
openssl x509 -in Player-Data/P0.pem -noout -fingerprint
```

**5. Check Expiration:**
```bash
openssl x509 -in Player-Data/P0.pem -noout -enddate
```

### Periodic System Restart Requirement

**TLS certificates expire after 30 days by default.** This means:

1. **System must be restarted at least monthly** to use renewed certificates
2. Before expiration, regenerate certificates:
   ```bash
   Scripts/setup-ssl.sh 3
   c_rehash Player-Data/
   ```
3. Restart all parties to establish new TLS connections
4. Attempting to run with expired certificates will cause handshake failures

**For longer validity periods**, generate certificates manually:
```bash
# Generate certificates valid for 1 year
openssl req -newkey rsa:2048 -nodes -x509 -days 365 \
    -out Player-Data/P0.pem -keyout Player-Data/P0.key -subj "/CN=P0"
```

This periodic restart requirement is inherent to the TLS-based security model and cannot be avoided without certificate renewal.

### Manual Override Options

Force encryption or plaintext regardless of protocol defaults:

```bash
# Force TLS encryption (even for dishonest-majority protocols)
./shamir-party.x -e <program_name> ...
# or
./shamir-party.x --encrypted <program_name> ...

# Force unencrypted (even for honest-majority protocols)
./shamir-party.x -u <program_name> ...
# or
./shamir-party.x --unencrypted <program_name> ...
```

### For ACS Reactive System

**Default Configuration:**
- Shamir protocol uses **TLS encryption by default**
- Port: 5000 + player number (e.g., 5000, 5001, 5002)
- Requires SSL certificates generated by `Scripts/setup-ssl.sh`

**Running without certificates:**
If you haven't set up SSL and get handshake errors:
```bash
# Generate certificates first
Scripts/setup-ssl.sh 3
c_rehash Player-Data/

# Then run the system
Scripts/compile-run.py shamir acs-reactive -- -N 3 --batch-size 30
```

**Multi-host deployment:**
1. Generate certificates on one machine
2. Copy entire `Player-Data/` directory to all hosts
3. Run `c_rehash Player-Data/` on each host
4. Ensure certificates are still valid (1-month expiry)

### Client-to-Party Communication

**External I/O (Client connections):**
- Port: 14000 (hardcoded in `acs-reactive.mpc`)
- **Not encrypted by default**
- Uses plaintext TCP sockets
- Separate from party-to-party communication

**For production environments:**
Consider encrypting client connections separately or using:
- SSH tunnels
- VPN
- Application-level encryption

### Security Properties

**What TLS provides:**
- **Confidentiality**: Data encrypted in transit
- **Authentication**: Certificate-based party verification
- **Integrity**: Tamper detection via MAC

**What TLS doesn't provide:**
- **Protocol-level security**: Provided by MPC protocol (e.g., Shamir secret sharing)
- **Protection from compromised parties**: Up to threshold T parties can be corrupted

**Defense-in-depth:**
- TLS encryption: Network-level security
- Shamir secret sharing: Information-theoretic security for privacy
- Combined: Strong security even if some network traffic is observed

### Troubleshooting Network Security

**"Handshake failed" errors:**
```
Client-side handshake with P1 failed. Make sure both sides have the necessary certificate
```
- Ensure all parties have the same `Player-Data/*.pem` files
- Run `c_rehash Player-Data/` on all hosts
- Check certificate validity (regenerate if expired after 1 month)
- Verify certificate signatures match across hosts

**Certificate not found:**
```
Cannot access Player-Data/P0.pem. Have you set up SSL?
```
- Run `Scripts/setup-ssl.sh <nparties>`
- Ensure `Player-Data/` directory exists

**Port conflicts:**
- Default ports: 5000 + player_number
- Change with `-pn` or `--portnumbase` flag
- Ensure ports are open in firewall

## Additional Resources

- [MP-SPDZ Documentation](https://mp-spdz.readthedocs.io/)
- [Networking Setup](https://mp-spdz.readthedocs.io/en/latest/networking.html)
- [External I/O Documentation](https://mp-spdz.readthedocs.io/en/latest/io.html)
- [Troubleshooting Handshake Failures](https://mp-spdz.readthedocs.io/en/latest/troubleshooting.html#handshake-failures)
