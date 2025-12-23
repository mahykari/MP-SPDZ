#!/usr/bin/python3
"""
Sensor client for door monitoring system (acs.mpc)
Sends door sensor data to MPC parties and receives results.

Usage: ./acs-sensor-client.py <client_id> <n_parties> <door_data_file>

Example: ./acs-sensor-client.py 0 3 sensor_data.txt
"""

import sys
import os

sys.path.append('.')

from client import *
from domains import *

def read_door_data_from_file(filename, n_doors=10):
  """Read door data from file.
  Expected format: 4 values per door (enteredA, exitedA, enteredB, exitedB)
  Total: n_doors * 4 values
  """
  with open(filename, 'r') as f:
    values = [int(x) for x in f.read().split()]
  
  if len(values) != n_doors * 4:
    raise ValueError(f"Expected {n_doors * 4} values, got {len(values)}")
  
  return values

def generate_sample_data(n_doors=10):
  """Generate sample door data for testing.
  Returns list of 4*n_doors values.
  """
  door_data = []
  for i in range(n_doors):
    # Sample data: door i has some entries/exits
    enteredA = i % 5
    exitedA = i % 3
    enteredB = i % 4
    exitedB = i % 2
    door_data.extend([enteredA, exitedA, enteredB, exitedB])
  return door_data

if __name__ == "__main__":
  if len(sys.argv) < 3:
    print("Usage: ./acs-sensor-client.py <client_id> <n_parties> [<door_data_file>]")
    print("  client_id: Client identifier (e.g., 0)")
    print("  n_parties: Number of MPC parties (e.g., 3)")
    print("  door_data_file: Optional file with door sensor data")
    print("                  If omitted, sample data will be generated")
    sys.exit(1)

  client_id = int(sys.argv[1])
  n_parties = int(sys.argv[2])
  n_doors = 10  # Must match N_EX in acs.mpc
  
  # Read or generate door data
  if len(sys.argv) >= 4:
    data_file = sys.argv[3]
    print(f"Reading door data from {data_file}...")
    door_data = read_door_data_from_file(data_file, n_doors)
  else:
    print("No data file provided, generating sample data...")
    door_data = generate_sample_data(n_doors)
  
  print(f"Door data ({len(door_data)} values): {door_data}")
  
  # Connect to MPC parties
  print(f"Connecting to {n_parties} parties on port 14000...")
  client = Client(['localhost'] * n_parties, 14000, client_id)
  print("Connected!")
  
  # Send door sensor data as private inputs
  print(f"Sending {len(door_data)} sensor values to MPC parties...")
  client.send_private_inputs(door_data)
  print("Sensor data sent!")
  
  # Receive results: fault, cntA, cntB
  print("Waiting for results...")
  results = client.receive_outputs(3)
  
  fault = results[0]
  cntA = results[1]
  cntB = results[2]
  
  print("\n" + "="*50)
  print("RESULTS:")
  print("="*50)
  print(f"Fault:   {fault}")
  print(f"Count A: {cntA}")
  print(f"Count B: {cntB}")
  print("="*50)
  
  if fault == 1:
    print("WARNING: Fault condition detected (Count A < Count B)")
  else:
    print("Status: Normal operation")
