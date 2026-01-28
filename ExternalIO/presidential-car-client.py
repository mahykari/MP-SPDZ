#!/usr/bin/env python3
"""
Reactive client for "presidential car" geofence monitoring system.

The monitor maintains a secret location (x,y). Each iteration the client sends a
secret displacement vector (dx, dy) and a time t. The monitor updates (x,y),
checks whether the new position stays within a time-varying geofence radius
(phased policy), and returns a 1-bit latched fault.

Prerequisites:
  pip install gmpy2
  (or activate a venv that already has it, like your locks client does)

Usage:
  ./presidential-car-client.py <client_id> <n_parties> <n_iterations> [mode]

Arguments:
  client_id   Client identifier (e.g., 0)
  n_parties   Number of MPC parties (e.g., 3)
  n_iterations  Number of rounds / displacement updates (e.g., 1000)
  mode      Optional data mode:
          - safe    : stays inside geofence
          - fault_last  : stays safe, then forces a fault near the end
          - random    : random walk (may fault)
        Default: fault_last

Example:
  ./presidential-car-client.py 0 3 1000 fault_last
"""

import math
import sys
import os
import time
import random

# -----------------------------------------------------------------------------
# Setup paths for MP-SPDZ Python client modules (same pattern as your locks client)
# -----------------------------------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(script_dir)

# Activate .venv virtual environment site-packages if present
venv_lib = os.path.join(base_dir, '.venv', 'lib')
if os.path.isdir(venv_lib):
  for item in os.listdir(venv_lib):
    if item.startswith('python'):
      sys.path.insert(0, os.path.join(venv_lib, item, 'site-packages'))
      break

sys.path.insert(0, base_dir)

from client import *   # MP-SPDZ client
from domains import *  # Field/integer helpers (kept for consistency; not strictly needed)

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
PORT_NUM = 14001  # Must match monitor

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def pretty_bytes(n: int) -> str:
  """Human-readable byte count."""
  if n < 1024:
    return f"{n} B"
  if n < 1024 * 1024:
    return f"{n / 1024:.2f} KB"
  return f"{n / (1024 * 1024):.3f} MB"


# Adaptive geofence parameters (should match monitor for nicer traces)
R0 = 50
ALPHA = 5
RMAX = 1000

def radius_for_time(t: int) -> int:
  """Client-side adaptive radius model: r(t)=min(RMAX, R0 + ALPHA*t)."""
  r = R0 + ALPHA * t
  return r if r <= RMAX else RMAX


def generate_trace(n_iterations: int, dim: int, mode: str):
  """
  Generate per-iteration inputs: deltas in n dimensions.

  - safe: tries hard to remain inside the geofence.
  - fault_last: safe until late, then forces a big step outside.
  - random: random walk, may fault.
  """
  random.seed(42)

  # Public simulation of position (for data generation only)
  pos = [0] * dim

  trace = []
  forced_fault_done = False

  for it in range(n_iterations):
    if mode == "random":
      # Rough random walk
      deltas = [random.randint(-30, 30) for _ in range(dim)]

    else:
      # "safe" and "fault_last"
      r = radius_for_time(it)

      # Small steps by default
      deltas = [random.randint(-10, 10) for _ in range(dim)]

      # Bias toward center if drifting near boundary
      margin = r // 5 + 10
      for i in range(dim):
        if abs(pos[i]) > r - margin:
          deltas[i] = -abs(deltas[i]) if pos[i] > 0 else abs(deltas[i])

      # Force a fault on the last iteration if requested
      if mode == "fault_last" and it == n_iterations - 1 and not forced_fault_done:
        deltas = [0] * dim
        target = int(math.sqrt(dim) * RMAX) + 500
        deltas[0] = target - pos[0]
        forced_fault_done = True

    # Update simulated position
    for i in range(dim):
      pos[i] += deltas[i]

    trace.append(deltas)

  return trace


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
  if len(sys.argv) < 5:
    print("Usage: ./presidential-car-client.py <client_id> <n_parties> <dim> <n_iterations> [mode]")
    print("  client_id:    Client identifier (e.g., 0)")
    print("  n_parties:    Number of MPC parties (e.g., 3)")
    print("  dim:          Number of spatial dimensions (e.g., 2)")
    print("  n_iterations: Number of rounds to send (e.g., 1000)")
    print("  mode:         safe | fault_last | random   (default: fault_last)")
    sys.exit(1)

  client_id = int(sys.argv[1])
  n_parties = int(sys.argv[2])
  dim = int(sys.argv[3])
  n_iterations = int(sys.argv[4])
  mode = sys.argv[5] if len(sys.argv) >= 6 else "fault_last"

  if mode not in {"safe", "fault_last", "random"}:
    raise ValueError("mode must be one of: safe, fault_last, random")

  print("=" * 60)
  print("Presidential Car Reactive Client")
  print("=" * 60)
  print(f"Configuration:")
  print(f"  Client ID:  {client_id}")
  print(f"  MPC Parties:  {n_parties}")
  print(f"  Iterations:   {n_iterations}")
  print(f"  Mode:     {mode}")
  print(f"  Port:     {PORT_NUM}")
  print("-" * 60)
  print("Spec idea: adaptive geofence (monitor uses iteration index as time)")
  print(f"  Dimension: {dim}D")
  print("=" * 60)

  # Prepare input trace
  print("Generating displacement trace...")
  trace = generate_trace(n_iterations, dim, mode)
  print(f"Prepared {len(trace)} iterations of deltas in {dim}D")

  # Connect to MPC parties
  print(f"\nConnecting to {n_parties} parties on port {PORT_NUM}...")
  client = Client(['localhost'] * n_parties, PORT_NUM, client_id)
  print("Connected!")

  # Metrics tracking
  total_bytes_sent = 0
  total_bytes_received = 0
  total_values_sent = 0
  total_values_received = 0

  iteration_times = []
  send_times = []
  receive_times = []

  fault_count = 0
  first_fault_iter = None

  # Overall experiment timer
  experiment_start = time.time()

  # Main loop
  for it in range(n_iterations):
    print(f"\n{'.'*60}")
    print(f"ITERATION {it + 1}/{n_iterations}")
    print(f"{'.'*60}")

    iter_start = time.time()

    deltas = trace[it]

    # Display the inputs
    print("Inputs:")
    for i in range(min(dim, 8)):
      print(f"  d[{i}] = {deltas[i]}")
    if dim > 8:
      print(f"  ... ({dim - 8} more)")

    # Send private inputs as secret integers:
    # The monitor expects dim values: d0, d1, ..., d{dim-1}
    send_start = time.time()
    client.send_private_inputs(deltas)   # deltas is a list of length dim
    send_end = time.time()

    send_time = send_end - send_start
    send_times.append(send_time)

    # Track sent data (approx: 8 bytes per value, same approximation as your other client)
    values_sent = dim
    bytes_sent = values_sent * 8
    total_values_sent += values_sent
    total_bytes_sent += bytes_sent

    print(f"Sent inputs: {values_sent} values (~{bytes_sent} bytes) in {send_time:.6f}s")

    # Receive 1 output: fault bit
    print("Waiting for result (fault bit)...")
    recv_start = time.time()
    results = client.receive_outputs(1)
    recv_end = time.time()

    recv_time = recv_end - recv_start
    receive_times.append(recv_time)

    # Track received data (approx: 8 bytes per value)
    values_received = 1
    bytes_received = values_received * 8
    total_values_received += values_received
    total_bytes_received += bytes_received

    fault = results[0]

    iter_end = time.time()
    iter_total = iter_end - iter_start
    iteration_times.append(iter_total)

    print("\nRESULTS:")
    print("-" * 60)
    print(f"Fault: {fault}")

    if fault == 1:
      fault_count += 1
      if first_fault_iter is None:
        first_fault_iter = it + 1
      print("WARNING: Geofence violation detected (or already latched)!")
    else:
      print("Status: Within allowed geofence")

    print("\nClient Timing:")
    print(f"  Send:  {send_time:.6f} seconds")
    print(f"  Receive: {recv_time:.6f} seconds")
    print(f"  TOTAL:   {iter_total:.6f} seconds")

    # Small delay for readability (comment out if you want speed)
    # time.sleep(0.05)

  # Final experiment time
  experiment_time = time.time() - experiment_start

  # Summary
  print(f"\n{'-'*60}")
  print("EXPERIMENT COMPLETE")
  print(f"{'-'*60}")

  print("\nResults Summary:")
  print(f"  Fault iterations: {fault_count}/{n_iterations}")
  if first_fault_iter is not None:
    print(f"  First fault observed at iteration: {first_fault_iter}")
  else:
    print("  No faults observed")

  print("\nTiming Metrics:")
  print(f"  Total experiment time:  {experiment_time:.3f}s")
  print(f"  Average iteration time: {sum(iteration_times)/len(iteration_times):.6f}s")
  print(f"  Min iteration time:   {min(iteration_times):.6f}s")
  print(f"  Max iteration time:   {max(iteration_times):.6f}s")
  print(f"  Average send time:    {sum(send_times)/len(send_times):.6f}s")
  print(f"  Average receive time:   {sum(receive_times)/len(receive_times):.6f}s")

  print("\nCommunication Metrics (client-side approximation):")
  print(f"  Total values sent:    {total_values_sent}")
  print(f"  Total values received:  {total_values_received}")
  print(f"  Total bytes sent:     {total_bytes_sent} ({pretty_bytes(total_bytes_sent)})")
  print(f"  Total bytes received:   {total_bytes_received} ({pretty_bytes(total_bytes_received)})")
  print(f"  Per-iteration sent:   {total_values_sent/n_iterations:.1f} values")
  print(f"  Per-iteration received: {total_values_received/n_iterations:.1f} values")

  print("\nThroughput:")
  print(f"  Iterations per second:  {n_iterations/experiment_time:.2f}")
  print(f"  Values sent per second: {total_values_sent/experiment_time:.2f}")
  print(f"  Bandwidth (sent):     {(total_bytes_sent/experiment_time)/1024:.4f} KB/s")

  print(f"{'-'*60}")
