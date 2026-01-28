#!/usr/bin/env python3
"""
Extract and analyze Presidential Car experiment results
Generates comparison tables for paper-style reporting
"""

import re
from pathlib import Path

# -----------------------------
# Parsing helpers
# -----------------------------
def parse_dim_from_name(stem: str):
  """
  Extract DIM from filenames like:
    PRESCAR-128D-shamir.log
    PRESCAR-1024D-replicated-client.log
  """
  m = re.search(r'PRESCAR-(\d+)D', stem)
  return int(m.group(1)) if m else None

def parse_mpc_log(log_file):
  """Extract metrics from MPC server log"""
  metrics = {
    'dim': None,
    'iterations': None,
    'integer_triples': None,
    'edabits_64': None,
    'integer_opens': None,
    'bit_triples': None,
    'integer_dabits': None,   # may show up as dabits/edaBits depending on backend
    'simple_multiplications': None,
    'integer_randoms': None,
    'vm_rounds': None,
    'data_sent_mb': None,
    'global_data_sent_mb': None,
    'timer_1_total': 0.0,
    'timer_10_total': 0.0,
    'timer_11_total': 0.0,
    'timer_12_total': 0.0,
    'timer_13_total': 0.0,
  }

  try:
    content = log_file.read_text()

    # DIM (try to parse from program print; otherwise from filename)
    dim_match = re.search(r'\bDimensions?:\s+(\d+)\b', content)
    if dim_match:
      metrics['dim'] = int(dim_match.group(1))
    else:
      metrics['dim'] = parse_dim_from_name(log_file.stem)

    # Iterations (your monitor prints "Configuration: %s iterations")
    iters_match = re.search(r'Configuration:\s+(\d+)\s+iterations', content)
    if iters_match:
      metrics['iterations'] = int(iters_match.group(1))
    else:
      # fallback: first occurrence of "<num> iterations"
      iters_match2 = re.search(r'\b(\d+)\s+iterations\b', content)
      if iters_match2:
        metrics['iterations'] = int(iters_match2.group(1))

    # Compiler metrics
    triples_match = re.search(r'(\d+)\s+integer triples', content)
    if triples_match:
      metrics['integer_triples'] = int(triples_match.group(1))

    edabits_match = re.search(r'(\d+)\s+\w+\s+edabits of length 64', content)
    if edabits_match:
      metrics['edabits_64'] = int(edabits_match.group(1))

    opens_match = re.search(r'(\d+)\s+integer opens', content)
    if opens_match:
      metrics['integer_opens'] = int(opens_match.group(1))

    bit_triples_match = re.search(r'(\d+)\s+bit triples', content)
    if bit_triples_match:
      metrics['bit_triples'] = int(bit_triples_match.group(1))

    dabits_match = re.search(r'(\d+)\s+integer dabits', content)
    if dabits_match:
      metrics['integer_dabits'] = int(dabits_match.group(1))

    simple_mults_match = re.search(r'(\d+)\s+integer simple multiplications', content)
    if simple_mults_match:
      metrics['simple_multiplications'] = int(simple_mults_match.group(1))

    randoms_match = re.search(r'(\d+)\s+integer randoms', content)
    if randoms_match:
      metrics['integer_randoms'] = int(randoms_match.group(1))

    vm_rounds_match = re.search(r'(\d+)\s+virtual machine rounds', content)
    if vm_rounds_match:
      metrics['vm_rounds'] = int(vm_rounds_match.group(1))

    # Communication
    data_sent_match = re.search(r'Data sent = ([\d.]+) MB', content)
    if data_sent_match:
      metrics['data_sent_mb'] = float(data_sent_match.group(1))

    global_data_match = re.search(r'Global data sent = ([\d.]+) MB', content)
    if global_data_match:
      metrics['global_data_sent_mb'] = float(global_data_match.group(1))

    # Timers: sum all occurrences of TimeX
    for timer_num in [1, 10, 11, 12, 13]:
      pat = re.compile(rf'\bTime{timer_num}\s*=\s*([\d.]+)\b')
      for m in pat.finditer(content):
        metrics[f'timer_{timer_num}_total'] += float(m.group(1))

  except FileNotFoundError:
    print(f"Warning: Log file not found: {log_file}")

  return metrics

def parse_client_log(log_file):
  """Extract metrics from client log"""
  metrics = {
    'dim': None,
    'iterations': None,
    'mode': None,
    'total_time': None,
    'avg_iteration_time': None,
    'avg_send_time': None,
    'avg_receive_time': None,
    'total_values_sent': None,
    'total_values_received': None,
    'total_bytes_sent': None,
    'total_bytes_received': None,
  }

  try:
    content = log_file.read_text()

    # DIM / iterations / mode from your client header
    dim_match = re.search(r'\bDimension:\s+(\d+)D\b', content)
    if dim_match:
      metrics['dim'] = int(dim_match.group(1))
    else:
      metrics['dim'] = parse_dim_from_name(log_file.stem)

    iters_match = re.search(r'\bIterations:\s+(\d+)\b', content)
    if iters_match:
      metrics['iterations'] = int(iters_match.group(1))

    mode_match = re.search(r'\bMode:\s+(\w+)\b', content)
    if mode_match:
      metrics['mode'] = mode_match.group(1)

    # Timing summary
    total_time_match = re.search(r'Total experiment time:\s+([\d.]+)s', content)
    if total_time_match:
      metrics['total_time'] = float(total_time_match.group(1))

    avg_iter_match = re.search(r'Average iteration time:\s+([\d.]+)s', content)
    if avg_iter_match:
      metrics['avg_iteration_time'] = float(avg_iter_match.group(1))

    avg_send_match = re.search(r'Average send time:\s+([\d.]+)s', content)
    if avg_send_match:
      metrics['avg_send_time'] = float(avg_send_match.group(1))

    avg_recv_match = re.search(r'Average receive time:\s+([\d.]+)s', content)
    if avg_recv_match:
      metrics['avg_receive_time'] = float(avg_recv_match.group(1))

    # Communication summary
    vals_sent_match = re.search(r'Total values sent:\s+(\d+)', content)
    if vals_sent_match:
      metrics['total_values_sent'] = int(vals_sent_match.group(1))

    vals_recv_match = re.search(r'Total values received:\s+(\d+)', content)
    if vals_recv_match:
      metrics['total_values_received'] = int(vals_recv_match.group(1))

    bytes_sent_match = re.search(r'Total bytes sent:\s+(\d+)', content)
    if bytes_sent_match:
      metrics['total_bytes_sent'] = int(bytes_sent_match.group(1))

    bytes_recv_match = re.search(r'Total bytes received:\s+(\d+)', content)
    if bytes_recv_match:
      metrics['total_bytes_received'] = int(bytes_recv_match.group(1))

  except FileNotFoundError:
    print(f"Warning: Log file not found: {log_file}")

  return metrics

# -----------------------------
# Tables
# -----------------------------
def print_table1_circuit_size(results):
  print("\n" + "="*70)
  print("TABLE 1: Circuit Complexity (Compiler Metrics)")
  print("="*70)
  print(f"{'Scenario':<22} {'Dim':<8} {'Triples':<10} {'BitTrip':<10} {'VMRnds':<10} {'Dabits':<8}")
  print("-"*70)

  for key, data in sorted(results.items(), key=lambda x: (x[1]['dim'] or 0)):
    mpc = data['mpc']
    dim = mpc['dim'] or 0
    int_triples = mpc['integer_triples'] or 0
    bit_triples = mpc['bit_triples'] or 0
    vm_rounds = mpc['vm_rounds'] or 0
    dabits = mpc['integer_dabits'] or 0
    print(f"{key:<22} {dim:<8} {int_triples:<10} {bit_triples:<10} {vm_rounds:<10} {dabits:<8}")

  print("="*70)
  print("Metrics from compiler/runtime (offline preprocessing requirements)\n")

def print_table2_timing(results):
  print("\n" + "="*70)
  print("TABLE 2: Execution Time (End-to-End)")
  print("="*70)
  print(f"{'Scenario':<22} {'Dim':<8} {'Total(s)':<11} {'PerIter(s)':<12} {'Iter/s':<8}")
  print("-"*70)

  for key, data in sorted(results.items(), key=lambda x: (x[1]['dim'] or 0)):
    client = data['client']
    mpc = data['mpc']
    dim = mpc['dim'] or client.get('dim') or 0

    total_time = client['total_time'] or 0.0
    avg_iter = client['avg_iteration_time'] or 0.0
    iters = mpc['iterations'] or client.get('iterations') or 1
    throughput = (iters / total_time) if total_time > 0 else 0.0

    print(f"{key:<22} {dim:<8} {total_time:<11.3f} {avg_iter:<12.4f} {throughput:<8.2f}")

  print("="*70 + "\n")

def print_table3_communication(results):
  print("\n" + "="*70)
  print("TABLE 3: Communication (Total Experiment)")
  print("="*70)
  print(f"{'Scenario':<22} {'Dim':<8} {'Sent(MB)':<11} {'Global(MB)':<13} {'PerParty(MB)':<12}")
  print("-"*70)

  for key, data in sorted(results.items(), key=lambda x: (x[1]['dim'] or 0)):
    mpc = data['mpc']
    dim = mpc['dim'] or 0
    data_sent = mpc['data_sent_mb'] or 0.0
    global_sent = mpc['global_data_sent_mb'] or 0.0
    per_party = data_sent
    print(f"{key:<22} {dim:<8} {data_sent:<11.3f} {global_sent:<13.3f} {per_party:<12.3f}")

  print("="*70 + "\n")

def print_table4_breakdown(results):
  print("\n" + "="*70)
  print("TABLE 4: Timing Breakdown (Avg Per Iteration, seconds)")
  print("="*70)
  print(f"{'Scenario':<22} {'Recv':<9} {'Compute':<9} {'Reveal':<9} {'Send':<9} {'Total':<9}")
  print("-"*70)

  for key, data in sorted(results.items(), key=lambda x: (x[1]['dim'] or 0)):
    mpc = data['mpc']
    iters = mpc['iterations'] if mpc['iterations'] and mpc['iterations'] > 0 else 1

    recv_time = mpc['timer_10_total'] / iters
    compute_time = mpc['timer_11_total'] / iters
    reveal_time = mpc['timer_12_total'] / iters
    send_time = mpc['timer_13_total'] / iters
    total_time = mpc['timer_1_total'] / iters

    print(f"{key:<22} {recv_time:<9.4f} {compute_time:<9.4f} {reveal_time:<9.4f} {send_time:<9.4f} {total_time:<9.4f}")

  print("="*70 + "\n")


def draw_ascii_charts(results):
  """Draw ASCII charts for quick visual comparison across dimensions."""
  print("\n" + "="*70)
  print("ASCII VISUALIZATIONS")
  print("="*70)

  # Collapse runs by dimension (average across protocols if multiple exist)
  by_dim = {}
  for _, data in results.items():
    dim = data.get('dim') or data['mpc'].get('dim') or data['client'].get('dim')
    if not dim:
      continue
    by_dim.setdefault(dim, []).append(data)

  if not by_dim:
    print("No data available for visualization")
    return

  # Helper to average values (ignoring None/0)
  def avg(vals):
    vals = [v for v in vals if v is not None and v != 0]
    return sum(vals) / len(vals) if vals else 0.0

  # Chart 1: Avg per-iteration time (client)
  print("\nAvg Per-Iteration Time (client)")
  print("-" * 70)

  dim_time = []
  max_time = 0.0
  for dim in sorted(by_dim.keys()):
    a = avg([d['client'].get('avg_iteration_time') for d in by_dim[dim]])
    dim_time.append((dim, a))
    max_time = max(max_time, a)

  if max_time > 0:
    scale = 60 / max_time
    for dim, t in dim_time:
      bar = "█" * int(t * scale)
      print(f"  {dim:5d}D: {bar} {t:.4f}s")

  # Chart 2: Integer triples required (mpc)
  print("\n\nCircuit Complexity (integer triples)")
  print("-" * 70)

  dim_triples = []
  max_tr = 0.0
  for dim in sorted(by_dim.keys()):
    a = avg([d['mpc'].get('integer_triples') for d in by_dim[dim]])
    dim_triples.append((dim, a))
    max_tr = max(max_tr, a)

  if max_tr > 0:
    scale = 60 / max_tr
    for dim, tr in dim_triples:
      bar = "▓" * int(tr * scale)
      print(f"  {dim:5d}D: {bar} {int(tr)} triples")

  # Chart 3: Global data sent (mpc)
  print("\n\nCommunication Volume (global data sent)")
  print("-" * 70)

  dim_comm = []
  max_c = 0.0
  for dim in sorted(by_dim.keys()):
    a = avg([d['mpc'].get('global_data_sent_mb') for d in by_dim[dim]])
    dim_comm.append((dim, a))
    max_c = max(max_c, a)

  if max_c > 0:
    scale = 60 / max_c
    for dim, c in dim_comm:
      bar = "▒" * int(c * scale)
      print(f"  {dim:5d}D: {bar} {c:.3f} MB")

  print("\n" + "="*70)
  print()

# -----------------------------
# Main
# -----------------------------
def main():
  script_dir = Path(__file__).parent
  logs_dir = script_dir / "logs"

  if not logs_dir.exists():
    print("Error: presidential-car-scripts/logs/ directory not found. Run experiments first.")
    return

  results = {}
  protocols = ['shamir', 'replicated', 'semi', 'semi2k', 'spdz2k']

  for mpc_log in logs_dir.glob("PRESCAR-*D-*.log"):
    if 'client' in mpc_log.name:
      continue

    stem = mpc_log.stem

    protocol = None
    scenario = None
    for prot in protocols:
      if stem.endswith(f"-{prot}"):
        protocol = prot
        scenario = stem.replace(f"-{prot}", "")
        break

    if not protocol:
      print(f"Warning: Could not determine protocol for {mpc_log.name}")
      continue

    client_log = logs_dir / f"{scenario}-{protocol}-client.log"
    full_key = f"{scenario}-{protocol}"
    print(f"Processing {full_key}...")

    mpc_metrics = parse_mpc_log(mpc_log)
    client_metrics = parse_client_log(client_log)

    dim = mpc_metrics.get('dim') or client_metrics.get('dim') or parse_dim_from_name(stem)

    results[full_key] = {
      'mpc': mpc_metrics,
      'client': client_metrics,
      'protocol': protocol,
      'dim': dim,
    }

  if not results:
    print("No presidential car log files found. Run experiments first with:")
    print("  ./run-presidential-car-experiments.sh")
    return

  protocols_found = sorted({d['protocol'] for d in results.values()})
  dims_found = sorted({d['dim'] for d in results.values() if d.get('dim')})

  print(f"\nFound {len(results)} experiment results:")
  print(f"  Protocols: {', '.join(protocols_found)}")
  print(f"  Dimensions: {', '.join(str(x) for x in dims_found)}")

  print_table1_circuit_size(results)
  print_table2_timing(results)
  print_table3_communication(results)
  print_table4_breakdown(results)
  draw_ascii_charts(results)


if __name__ == "__main__":
  main()
