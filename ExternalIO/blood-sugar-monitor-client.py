#!/usr/bin/env python3
"""
Reactive sensor client for blood sugar monitoring system (blood-sugar-monitor.mpc)
Sends multiple rounds of blood sugar sensor data to MPC parties and receives results.

Prerequisites: pip install gmpy2 (or activate virtual environment with gmpy2)

Usage: ./blood-sugar-monitor-client.py <client_id> <n_parties> <n_iterations> [<sensor_data_file>]

Example: ./blood-sugar-monitor-client.py 0 3 1000 sensor_data.txt
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

def read_sensor_data_from_file(filename, n_iterations=1000):
  """Read blood sugar sensor data from file.
  Expected format: n_iterations lines, each with 2 values: time blood_sugar
  Example:
    100 150
    200 180
    650 210
  """
  with open(filename, 'r') as f:
    lines = [line.strip() for line in f if line.strip()]
  
  if len(lines) != n_iterations:
    raise ValueError(f"Expected {n_iterations} lines, got {len(lines)}")
  
  iterations_data = []
  for line in lines:
    parts = line.split()
    if len(parts) != 2:
      raise ValueError(f"Each line must have 2 values (time, blood_sugar), got: {line}")
    t = int(parts[0])
    blood_sugar = int(parts[1])
    iterations_data.append([t, blood_sugar])
  
  return iterations_data

def generate_sample_data(n_iterations=1000):
  """Generate sample blood sugar data for testing.
  Returns list of n_iterations, each containing [time, blood_sugar].
  
  Includes a fault scenario where blood sugar exceeds 200 during time window 600-700.
  """
  iterations_data = []
  
  for t in range(n_iterations):
    # Normal baseline: blood sugar between 80-180
    base_sugar = 120
    
    # Add some variation
    variation = (t % 50) - 25
    blood_sugar = base_sugar + variation
    
    # Create fault condition: high blood sugar during critical time window
    if 600 <= t <= 700:
      if t == 650:
        # Spike in the middle of critical window
        blood_sugar = 220
      elif 640 <= t <= 660:
        # Elevated levels around the spike
        blood_sugar = 210 + (t % 10)
      elif 630 <= t <= 670:
        # Slightly elevated
        blood_sugar = 190 + (t % 15)
    
    # Keep values realistic (minimum 50, maximum 400)
    blood_sugar = max(50, min(400, blood_sugar))
    
    iterations_data.append([t, blood_sugar])
  
  return iterations_data

if __name__ == "__main__":
  if len(sys.argv) < 4:
    print("Usage: ./blood-sugar-monitor-client.py <client_id> <n_parties> <n_iterations> [<sensor_data_file>]")
    print("  client_id: Client identifier (e.g., 0)")
    print("  n_parties: Number of MPC parties (e.g., 3)")
    print("  n_iterations: Number of sensor readings to send (e.g., 1000)")
    print("  sensor_data_file: Optional file with sensor data (time, blood_sugar per line)")
    print("                    If omitted, sample data will be generated")
    print("\nExample: ./blood-sugar-monitor-client.py 0 3 1000")
    sys.exit(1)

  client_id = int(sys.argv[1])
  n_parties = int(sys.argv[2])
  n_iterations = int(sys.argv[3])
  
  # Read or generate sensor data
  if len(sys.argv) >= 5:
    data_file = sys.argv[4]
    print(f"Reading sensor data from {data_file}...")
    iterations_data = read_sensor_data_from_file(data_file, n_iterations)
  else:
    print("No data file provided, generating sample data...")
    iterations_data = generate_sample_data(n_iterations)
  
  print(f"Configuration: {n_iterations} iterations")
  print(f"Specification PSI4: Fault if blood sugar > 200 during time 600-700")
  print(f"Prepared {n_iterations} iterations of sensor data")
  
  # Connect to MPC parties
  print(f"\nConnecting to {n_parties} parties on port 14001...")
  client = Client(['localhost'] * n_parties, 14001, client_id)
  print("Connected!")
  
  # Metrics tracking
  total_bytes_sent = 0
  total_bytes_received = 0
  total_values_sent = 0
  total_values_received = 0
  iteration_times = []
  send_times = []
  receive_times = []
  
  # Track fault detection
  first_fault_iteration = None
  fault_status = 0
  
  # Overall experiment timer
  experiment_start = time.time()
  
  # Process each iteration
  for iteration in range(n_iterations):
    # Print detailed info for select iterations
    verbose = (iteration < 5 or 
               iteration >= n_iterations - 5 or 
               595 <= iterations_data[iteration][0] <= 705 or
               iteration % 100 == 0)
    
    if verbose:
      print(f"\n{'.'*60}")
      print(f"ITERATION {iteration + 1}/{n_iterations}")
      print(f"{'.'*60}")
    
    # Start timing for this iteration
    iter_start = time.time()
    
    sensor_data = iterations_data[iteration]
    t = sensor_data[0]
    blood_sugar = sensor_data[1]
    
    if verbose:
      print(f"Sending sensor data: Time={t}, Blood Sugar={blood_sugar}")
    
    # Send sensor data as private inputs [time, blood_sugar]
    send_start = time.time()
    client.send_private_inputs(sensor_data)
    send_end = time.time()
    send_time = send_end - send_start
    send_times.append(send_time)
    
    # Track sent data
    values_sent = 2  # time and blood_sugar
    total_values_sent += values_sent
    bytes_sent = values_sent * 8  # Approximate: 8 bytes per value
    total_bytes_sent += bytes_sent
    
    if verbose:
      print(f"Sensor data sent! {values_sent} values ({bytes_sent} bytes) in {send_time:.6f}s")
    
    # Receive results: fault status
    if verbose:
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
    
    # Track first fault detection
    if fault == 1 and first_fault_iteration is None:
      first_fault_iteration = iteration + 1
      fault_status = 1
      print(f"\n{'!'*60}")
      print(f"FAULT DETECTED at Iteration {iteration + 1}")
      print(f"Time: {t}, Blood Sugar: {blood_sugar}")
      print(f"{'!'*60}")
    
    # Calculate total iteration time
    iter_end = time.time()
    iter_total = iter_end - iter_start
    iteration_times.append(iter_total)
    
    if verbose:
      print(f"\nRESULTS (Iteration {iteration + 1}):")
      print(f"-" * 60)
      print(f"Time:         {t}")
      print(f"Blood Sugar:  {blood_sugar}")
      print(f"Fault:        {fault}")
      
      if fault == 1:
        print("STATUS: FAULT - Blood sugar exceeded threshold during critical time window")
      else:
        print("STATUS: Normal operation")
      
      print(f"\nClient Timing (Iteration {iteration + 1}):")
      print(f"  Send:    {send_time:.6f} seconds")
      print(f"  Receive: {recv_time:.6f} seconds")
      print(f"  TOTAL:   {iter_total:.6f} seconds")
  
  # Calculate total experiment time
  experiment_time = time.time() - experiment_start
  
  # Print comprehensive metrics
  print(f"\n{'='*60}")
  print(f"EXPERIMENT COMPLETE")
  print(f"{'='*60}")
  print(f"\nConfiguration:")
  print(f"  Client ID: {client_id}")
  print(f"  MPC Parties: {n_parties}")
  print(f"  Iterations: {n_iterations}")
  print(f"  Specification: PSI4 (fault if blood sugar > 200 during time 600-700)")
  
  print(f"\nFault Detection:")
  if first_fault_iteration is not None:
    print(f"  First fault detected at iteration: {first_fault_iteration}")
    print(f"  Final fault status: {fault_status}")
  else:
    print(f"  No fault detected")
  
  print(f"\nTiming Metrics:")
  print(f"  Total experiment time: {experiment_time:.3f}s")
  print(f"  Average iteration time: {sum(iteration_times)/len(iteration_times):.6f}s")
  print(f"  Min iteration time: {min(iteration_times):.6f}s")
  print(f"  Max iteration time: {max(iteration_times):.6f}s")
  print(f"  Average send time: {sum(send_times)/len(send_times):.6f}s")
  print(f"  Average receive time: {sum(receive_times)/len(receive_times):.6f}s")
  
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
  
  print(f"{'='*60}")
