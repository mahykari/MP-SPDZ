#!/usr/bin/env python3
"""
Reactive lock client for parallel locks monitoring system (locks-reactive.mpc)
Sends multiple rounds of lock requests to MPC parties and receives fault results.

Prerequisites: pip install gmpy2 (or activate virtual environment with gmpy2)

Usage: ./locks-reactive-client.py <client_id> <n_parties> <n_locks> <n_iterations> [<lock_data_file>]

Example: ./locks-reactive-client.py 0 3 8 5 lock_requests.txt
"""

import sys
import os
import time
import random

# Setup paths for MP-SPDZ modules
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(script_dir)

# Activate .venv virtual environment
venv_lib = os.path.join(base_dir, '.venv', 'lib')
for item in os.listdir(venv_lib):
  if item.startswith('python'):
    sys.path.insert(0, os.path.join(venv_lib, item, 'site-packages'))
    break

sys.path.insert(0, base_dir)

from client import *
from domains import *

# Constants for lock requests
UNLOCK = 0
LOCK = 1
SKIP = 2

def read_lock_data_from_file(filename, n_locks=8, n_iterations=5):
  """Read lock request data from file.
  Expected format: n_iterations blocks of n_locks values each
  Total: n_iterations * n_locks values
  Each value: 0 (UNLOCK), 1 (LOCK), or 2 (SKIP)
  """
  with open(filename, 'r') as f:
    values = [int(x) for x in f.read().split()]
  
  expected = n_iterations * n_locks
  if len(values) != expected:
    raise ValueError(f"Expected {expected} values, got {len(values)}")
  
  # Split into iterations
  iterations_data = []
  for i in range(n_iterations):
    start = i * n_locks
    end = start + n_locks
    iterations_data.append(values[start:end])
  
  return iterations_data

def generate_sample_data(n_locks=8, n_iterations=1000):
  """Generate sample lock request data for testing.
  Returns list of n_iterations, each containing n_locks request values.
  Last iteration will cause a fault (double-lock/unlock violation).
  """
  random.seed(42)  # For reproducibility
  iterations_data = []
  
  # Track current lock states to generate meaningful data
  current_states = [0] * n_locks  # All start unlocked
  
  for iter_num in range(n_iterations):
    requests = []
    
    if iter_num == n_iterations - 1:
      # Last iteration: ALWAYS cause a fault
      # Lock 0 will be in whatever state it's in, we'll try the same operation
      for i in range(n_locks):
        if i == 0:
          # Double the current state: if locked, try to lock; if unlocked, try to unlock
          if current_states[0] == 1:
            requests.append(LOCK)  # Double lock - FAULT!
          else:
            requests.append(UNLOCK)  # Double unlock - FAULT!
        else:
          # Skip all other locks
          requests.append(SKIP)
    elif iter_num == n_iterations - 2:
      # Second-to-last iteration: ensure lock 0 is in a known state (LOCKED)
      for i in range(n_locks):
        if i == 0:
          # Force lock 0 to be LOCKED before the fault iteration
          if current_states[0] == 0:
            requests.append(LOCK)  # Lock it
          else:
            requests.append(SKIP)  # Already locked
        else:
          # Normal operations for other locks
          if current_states[i] == 0:
            req = random.choice([LOCK, SKIP, SKIP])
          else:
            req = random.choice([UNLOCK, SKIP, SKIP])
          requests.append(req)
    else:
      # Normal iterations: mix of valid operations
      for i in range(n_locks):
        # Generate valid operations based on current state
        if current_states[i] == 0:  # unlocked
          # Can lock or skip
          req = random.choice([LOCK, SKIP, SKIP])  # More skips
        else:  # locked
          # Can unlock or skip
          req = random.choice([UNLOCK, SKIP, SKIP])
        requests.append(req)
    
    iterations_data.append(requests)
    
    # Update current states for next iteration (only if not last and no fault)
    if iter_num < n_iterations - 1:
      for i in range(n_locks):
        if requests[i] == LOCK:
          current_states[i] = 1
        elif requests[i] == UNLOCK:
          current_states[i] = 0
        # SKIP keeps current state
  
  return iterations_data

def request_to_string(req):
  """Convert request code to readable string"""
  if req == UNLOCK:
    return "UNLOCK"
  elif req == LOCK:
    return "LOCK"
  elif req == SKIP:
    return "SKIP"
  else:
    return f"UNKNOWN({req})"

if __name__ == "__main__":
  if len(sys.argv) < 5:
    print("Usage: ./locks-reactive-client.py <client_id> <n_parties> <n_locks> <n_iterations> [<lock_data_file>]")
    print("  client_id: Client identifier (e.g., 0)")
    print("  n_parties: Number of MPC parties (e.g., 3)")
    print("  n_locks: Number of locks (e.g., 8 or 16)")
    print("  n_iterations: Number of lock request rounds to send (e.g., 5)")
    print("  lock_data_file: Optional file with lock request data")
    print("                  If omitted, sample data will be generated")
    print("\nLock request encoding:")
    print("  0 = UNLOCK, 1 = LOCK, 2 = SKIP")
    sys.exit(1)

  client_id = int(sys.argv[1])
  n_parties = int(sys.argv[2])
  n_locks = int(sys.argv[3])
  n_iterations = int(sys.argv[4])
  
  # Read or generate lock request data
  if len(sys.argv) >= 6:
    data_file = sys.argv[5]
    print(f"Reading lock request data from {data_file}...")
    iterations_data = read_lock_data_from_file(data_file, n_locks, n_iterations)
  else:
    print("No data file provided, generating sample data...")
    iterations_data = generate_sample_data(n_locks, n_iterations)
  
  print(f"Configuration: {n_locks} locks, {n_iterations} iterations")
  print(f"Prepared {n_iterations} iterations of lock request data")
  
  # Connect to MPC parties
  print(f"Connecting to {n_parties} parties on port 14000...")
  client = Client(['localhost'] * n_parties, 14000, client_id)
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
  
  # Overall experiment timer
  experiment_start = time.time()
  
  # Process each iteration
  for iteration in range(n_iterations):
    print(f"\n{'.'*60}")
    print(f"ITERATION {iteration + 1}/{n_iterations}")
    print(f"{'.'*60}")
    
    # Start timing for this iteration
    iter_start = time.time()
    
    lock_requests = iterations_data[iteration]
    
    # Display the requests
    print(f"Lock requests:")
    for i in range(min(n_locks, 16)):  # Show at most 16 locks
      print(f"  Lock {i:2d}: {request_to_string(lock_requests[i])}")
    if n_locks > 16:
      print(f"  ... ({n_locks - 16} more locks)")
    
    # Send lock requests as private inputs
    send_start = time.time()
    client.send_private_inputs(lock_requests)
    send_end = time.time()
    send_time = send_end - send_start
    send_times.append(send_time)
    
    # Track sent data
    values_sent = len(lock_requests)
    total_values_sent += values_sent
    bytes_sent = values_sent * 8  # Approximate: 8 bytes per value
    total_bytes_sent += bytes_sent
    print(f"Lock requests sent! {values_sent} values ({bytes_sent} bytes) in {send_time:.6f}s")
    
    # Receive results: fault only
    print("Waiting for results...")
    recv_start = time.time()
    results = client.receive_outputs(1)
    recv_end = time.time()
    recv_time = recv_end - recv_start
    receive_times.append(recv_time)
    
    # Track received data
    values_received = 1
    total_values_received += values_received
    bytes_received = values_received * 8
    total_bytes_received += bytes_received
    
    fault = results[0]
    
    # Calculate total iteration time
    iter_end = time.time()
    iter_total = iter_end - iter_start
    iteration_times.append(iter_total)
    
    print(f"\nRESULTS (Iteration {iteration + 1}):")
    print(f"-" * 60)
    print(f"Fault:   {fault}")
    
    if fault == 1:
      print("WARNING: Double-lock/unlock violation detected!")
      fault_count += 1
    else:
      print("Status: All lock operations valid")
    
    print(f"\nClient Timing (Iteration {iteration + 1}):")
    print(f"  Send:    {send_time:.6f} seconds")
    print(f"  Receive: {recv_time:.6f} seconds")
    print(f"  TOTAL:   {iter_total:.6f} seconds")
    
    # Small delay between iterations for readability
    if iteration < n_iterations - 1:
      time.sleep(0.5)
  
  # Calculate total experiment time
  experiment_time = time.time() - experiment_start
  
  # Print comprehensive metrics
  print(f"\n{'-'*60}")
  print(f"EXPERIMENT COMPLETE")
  print(f"{'-'*60}")
  print(f"\nConfiguration:")
  print(f"  Client ID: {client_id}")
  print(f"  MPC Parties: {n_parties}")
  print(f"  Locks: {n_locks}")
  print(f"  Iterations: {n_iterations}")
  
  print(f"\nResults Summary:")
  print(f"  Total faults detected: {fault_count}/{n_iterations}")
  print(f"  Valid iterations: {n_iterations - fault_count}/{n_iterations}")
  
  print(f"\nTiming Metrics:")
  print(f"  Total experiment time: {experiment_time:.3f}s")
  print(f"  Average iteration time: {sum(iteration_times)/len(iteration_times):.3f}s")
  print(f"  Min iteration time: {min(iteration_times):.3f}s")
  print(f"  Max iteration time: {max(iteration_times):.3f}s")
  print(f"  Average send time: {sum(send_times)/len(send_times):.4f}s")
  print(f"  Average receive time: {sum(receive_times)/len(receive_times):.4f}s")
  
  print(f"\nCommunication Metrics:")
  print(f"  Total values sent: {total_values_sent}")
  print(f"  Total values received: {total_values_received}")
  print(f"  Total bytes sent: {total_bytes_sent} ({total_bytes_sent/1024:.2f} KB)")
  print(f"  Total bytes received: {total_bytes_received} ({total_bytes_received/1024:.2f} KB)")
  print(f"  Per-iteration sent: {total_values_sent/n_iterations:.1f} values")
  print(f"  Per-iteration received: {total_values_received/n_iterations:.1f} values")
  
  print(f"\nThroughput:")
  print(f"  Iterations per second: {n_iterations/experiment_time:.2f}")
  print(f"  Values sent per second: {total_values_sent/experiment_time:.1f}")
  print(f"  Bandwidth (sent): {(total_bytes_sent/experiment_time)/1024:.2f} KB/s")
  
  print(f"{'-'*60}")
