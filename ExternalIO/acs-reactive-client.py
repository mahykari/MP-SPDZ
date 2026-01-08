#!/usr/bin/env python3
"""
Reactive sensor client for door monitoring system (acs-reactive.mpc)
Sends multiple rounds of door sensor data to MPC parties and receives results.

Prerequisites: pip install gmpy2 (or activate virtual environment with gmpy2)

Usage: ./acs-reactive-client.py <client_id> <n_parties> <n_iterations> [<door_data_file>]

Example: ./acs-reactive-client.py 0 3 5 sensor_data.txt
"""

import sys
import os
import time

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

def read_door_data_from_file(filename, n_doors=10, n_iterations=5):
  """Read door data from file.
  Expected format: n_iterations blocks of (n_doors * 4) values each
  Total: n_iterations * n_doors * 4 values
  Each block: 4 values per door (enteredA, exitedA, enteredB, exitedB)
  """
  with open(filename, 'r') as f:
    values = [int(x) for x in f.read().split()]
  
  expected = n_iterations * n_doors * 4
  if len(values) != expected:
    raise ValueError(f"Expected {expected} values, got {len(values)}")
  
  # Split into iterations
  iterations_data = []
  for i in range(n_iterations):
    start = i * n_doors * 4
    end = start + n_doors * 4
    iterations_data.append(values[start:end])
  
  return iterations_data

def generate_sample_data(n_doors=10, n_iterations=5):
  """Generate sample door data for testing.
  Returns list of n_iterations, each containing n_doors * 4 values.
  Last iteration always causes a fault (cntA < cntB).
  """
  iterations_data = []
  
  for iter_num in range(n_iterations):
    door_data = []
    for i in range(n_doors):
      if iter_num == n_iterations - 1:
        # Last iteration: force fault by making cntB > cntA
        # High entries in B, low exits in B, low entries in A, high exits in A
        enteredA = 0
        exitedA = 3
        enteredB = 5
        exitedB = 0
      else:
        # Normal iterations: vary the data slightly
        enteredA = (i + iter_num) % 5
        exitedA = (i + iter_num) % 3
        enteredB = (i + iter_num) % 4
        exitedB = (i + iter_num) % 2
      door_data.extend([enteredA, exitedA, enteredB, exitedB])
    iterations_data.append(door_data)
  
  return iterations_data

if __name__ == "__main__":
  if len(sys.argv) < 4:
    print("Usage: ./acs-reactive-client.py <client_id> <n_parties> <n_iterations> [<door_data_file>]")
    print("  client_id: Client identifier (e.g., 0)")
    print("  n_parties: Number of MPC parties (e.g., 3)")
    print("  n_iterations: Number of sensor readings to send (e.g., 5)")
    print("  door_data_file: Optional file with door sensor data")
    print("                  If omitted, sample data will be generated")
    sys.exit(1)

  client_id = int(sys.argv[1])
  n_parties = int(sys.argv[2])
  n_iterations = int(sys.argv[3])
  n_doors = 10  # Must match N_EX in acs-reactive.mpc
  
  # Read or generate door data
  if len(sys.argv) >= 5:
    data_file = sys.argv[4]
    print(f"Reading door data from {data_file}...")
    iterations_data = read_door_data_from_file(data_file, n_doors, n_iterations)
  else:
    print("No data file provided, generating sample data...")
    iterations_data = generate_sample_data(n_doors, n_iterations)
  
  print(f"Prepared {n_iterations} iterations of sensor data")
  
  # Connect to MPC parties
  print(f"Connecting to {n_parties} parties on port 14000...")
  client = Client(['localhost'] * n_parties, 14000, client_id)
  print("Connected!")
  
  # Process each iteration
  for iteration in range(n_iterations):
    print(f"\n{'='*60}")
    print(f"ITERATION {iteration + 1}/{n_iterations}")
    print(f"{'='*60}")
    
    # Start timing for this iteration
    iter_start = time.time()
    
    door_data = iterations_data[iteration]
    print(f"Sending {len(door_data)} sensor values...")
    
    # Send door sensor data as private inputs
    send_start = time.time()
    client.send_private_inputs(door_data)
    send_end = time.time()
    send_time = send_end - send_start
    print(f"Sensor data sent! ({send_time:.6f} seconds)")
    
    # Receive results: fault only
    print("Waiting for results...")
    recv_start = time.time()
    results = client.receive_outputs(1)
    recv_end = time.time()
    recv_time = recv_end - recv_start
    
    fault = results[0]
    
    # Calculate total iteration time
    iter_end = time.time()
    iter_total = iter_end - iter_start
    
    print(f"\nRESULTS (Iteration {iteration + 1}):")
    print(f"-" * 60)
    print(f"Fault:   {fault}")
    
    if fault == 1:
      print("WARNING: Fault condition detected (Count A < Count B)")
    else:
      print("Status: Normal operation")
    
    print(f"\nClient Timing (Iteration {iteration + 1}):")
    print(f"  Send:    {send_time:.6f} seconds")
    print(f"  Receive: {recv_time:.6f} seconds")
    print(f"  TOTAL:   {iter_total:.6f} seconds")
    
    # Small delay between iterations for readability
    if iteration < n_iterations - 1:
      time.sleep(0.5)
  
  print(f"\n{'='*60}")
  print(f"All {n_iterations} iterations complete!")
  print(f"{'='*60}")
