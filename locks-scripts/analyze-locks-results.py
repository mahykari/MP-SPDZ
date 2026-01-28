#!/usr/bin/env python3
"""
Extract and analyze locks experiment results
Generates comparison tables for paper
"""

import re
import os
from pathlib import Path

def parse_mpc_log(log_file):
    """Extract metrics from MPC server log"""
    metrics = {
        'locks': None,
        'iterations': None,
        'integer_triples': None,
        'edabits_64': None,
        'integer_opens': None,
        'bit_triples': None,
        'integer_dabits': None,
        'simple_multiplications': None,
        'integer_randoms': None,
        'vm_rounds': None,
        'data_sent_mb': None,
        'global_data_sent_mb': None,
        'timer_1_total': 0,  # Total iteration time
        'timer_10_total': 0, # Client receive time
        'timer_11_total': 0, # Spec function time
        'timer_12_total': 0, # Reveal time
        'timer_13_total': 0, # Client send time
    }
    
    try:
        with open(log_file, 'r') as f:
            content = f.read()
            
            # Extract configuration
            locks_match = re.search(r'Configuration:\s+(\d+) locks', content)
            if locks_match:
                metrics['locks'] = int(locks_match.group(1))
            
            iters_match = re.search(r'(\d+) iterations', content)
            if iters_match:
                metrics['iterations'] = int(iters_match.group(1))
            
            # Extract compiler-generated metrics
            triples_match = re.search(r'(\d+)\s+integer triples', content)
            if triples_match:
                metrics['integer_triples'] = int(triples_match.group(1))
            
            edabits_match = re.search(r'(\d+)\s+\w+ edabits of length 64', content)
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
            
            # Extract communication data
            data_sent_match = re.search(r'Data sent = ([\d.]+) MB', content)
            if data_sent_match:
                metrics['data_sent_mb'] = float(data_sent_match.group(1))
            
            global_data_match = re.search(r'Global data sent = ([\d.]+) MB', content)
            if global_data_match:
                metrics['global_data_sent_mb'] = float(global_data_match.group(1))
            
            # Extract timing from timer output
            for timer_num in [1, 10, 11, 12, 13]:
                timer_pattern = rf'Time{timer_num} = ([\d.]+)'
                for match in re.finditer(timer_pattern, content):
                    metrics[f'timer_{timer_num}_total'] += float(match.group(1))
    
    except FileNotFoundError:
        print(f"Warning: Log file not found: {log_file}")
    
    return metrics

def parse_client_log(log_file):
    """Extract metrics from client log"""
    metrics = {
        'total_time': None,
        'avg_iteration_time': None,
        'avg_send_time': None,
        'avg_receive_time': None,
        'total_values_sent': None,
        'total_values_received': None,
        'total_bytes_sent': None,
        'total_bytes_received': None,
        'faults_detected': None,
    }
    
    try:
        with open(log_file, 'r') as f:
            content = f.read()
            
            # Extract timing
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
            
            # Extract communication
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
            
            # Extract fault detection
            faults_match = re.search(r'Total faults detected:\s+(\d+)', content)
            if faults_match:
                metrics['faults_detected'] = int(faults_match.group(1))
    
    except FileNotFoundError:
        print(f"Warning: Log file not found: {log_file}")
    
    return metrics

def print_table1_circuit_size(results):
    """Print Table 1: Circuit Complexity Comparison"""
    print("\n" + "="*70)
    print("TABLE 1: Circuit Complexity (Compiler Metrics)")
    print("="*70)
    print(f"{'Scenario':<20} {'Locks':<8} {'Triples':<10} {'BitTrip':<10} {'VMRnds':<8} {'Dabits':<8}")
    print("-"*70)
    
    for config, data in sorted(results.items(), key=lambda x: x[1]['locks']):
        mpc = data['mpc']
        locks = mpc['locks'] if mpc['locks'] is not None else 0
        int_triples = mpc['integer_triples'] if mpc['integer_triples'] is not None else 0
        bit_triples = mpc['bit_triples'] if mpc['bit_triples'] is not None else 0
        vm_rounds = mpc['vm_rounds'] if mpc['vm_rounds'] is not None else 0
        dabits = mpc['integer_dabits'] if mpc['integer_dabits'] is not None else 0
        
        print(f"{config:<20} {locks:<8} {int_triples:<10} {bit_triples:<10} {vm_rounds:<8} {dabits:<8}")
    
    print("="*70)
    print("Metrics from compiler (offline preprocessing requirements)")
    print()

def print_table2_timing(results):
    """Print Table 2: Execution Time Comparison"""
    print("\n" + "="*70)
    print("TABLE 2: Execution Time (End-to-End)")
    print("="*70)
    print(f"{'Scenario':<20} {'Locks':<8} {'Total(s)':<11} {'PerIter(s)':<12} {'Iter/s':<8}")
    print("-"*70)
    
    for config, data in sorted(results.items(), key=lambda x: x[1]['locks']):
        client = data['client']
        mpc = data['mpc']
        locks = mpc['locks'] if mpc['locks'] is not None else 0
        total_time = client['total_time'] if client['total_time'] is not None else 0
        avg_iter = client['avg_iteration_time'] if client['avg_iteration_time'] is not None else 0
        iters = mpc['iterations'] if mpc['iterations'] is not None else 1
        throughput = iters / total_time if total_time > 0 else 0
        
        print(f"{config:<20} {locks:<8} {total_time:<11.3f} {avg_iter:<12.4f} {throughput:<8.2f}")
    
    print("="*70)
    print()

def print_table3_communication(results):
    """Print Table 3: Communication Costs"""
    print("\n" + "="*70)
    print("TABLE 3: Communication (Total Experiment)")
    print("="*70)
    print(f"{'Scenario':<20} {'Locks':<8} {'Sent(MB)':<11} {'Global(MB)':<13} {'PerParty':<10}")
    print("-"*70)
    
    for config, data in sorted(results.items(), key=lambda x: x[1]['locks']):
        mpc = data['mpc']
        locks = mpc['locks'] if mpc['locks'] is not None else 0
        
        data_sent = mpc['data_sent_mb'] if mpc['data_sent_mb'] is not None else 0
        global_sent = mpc['global_data_sent_mb'] if mpc['global_data_sent_mb'] is not None else 0
        per_party = data_sent
        
        print(f"{config:<20} {locks:<8} {data_sent:<11.3f} {global_sent:<13.3f} {per_party:<10.3f}")
    
    print("="*70)
    print()

def print_table4_breakdown(results):
    """Print Table 4: Detailed Timing Breakdown"""
    print("\n" + "="*70)
    print("TABLE 4: Timing Breakdown (Avg Per Iteration, seconds)")
    print("="*70)
    print(f"{'Scenario':<20} {'Recv':<9} {'Compute':<9} {'Reveal':<9} {'Send':<9} {'Total':<9}")
    print("-"*70)
    
    for config, data in sorted(results.items(), key=lambda x: x[1]['locks']):
        mpc = data['mpc']
        iters = mpc['iterations'] if mpc['iterations'] is not None and mpc['iterations'] > 0 else 1
        
        # Average times per iteration
        recv_time = mpc['timer_10_total'] / iters
        compute_time = mpc['timer_11_total'] / iters
        reveal_time = mpc['timer_12_total'] / iters
        send_time = mpc['timer_13_total'] / iters
        total_time = mpc['timer_1_total'] / iters
        
        print(f"{config:<20} {recv_time:<9.4f} {compute_time:<9.4f} {reveal_time:<9.4f} {send_time:<9.4f} {total_time:<9.4f}")
    
    print("="*70)
    print()

def draw_ascii_charts(results):
    """Draw ASCII charts for visual comparison"""
    print("\n" + "="*70)
    print("ASCII VISUALIZATIONS")
    print("="*70)
    
    # Extract data by lock count
    lock_counts = {}
    for config, data in results.items():
        locks = data['mpc']['locks']
        if locks:
            if locks not in lock_counts:
                lock_counts[locks] = []
            lock_counts[locks].append(data)
    
    if not lock_counts:
        print("No data available for visualization")
        return
    
    # Chart 1: Timing comparison by lock count
    print("\nTiming Comparison (Average Per-Iteration Time)")
    print("-" * 70)
    
    max_time = 0
    lock_data = []
    for locks in sorted(lock_counts.keys()):
        avg_times = []
        for data in lock_counts[locks]:
            avg_iter = data['client'].get('avg_iteration_time', 0)
            if avg_iter:
                avg_times.append(avg_iter)
        
        if avg_times:
            avg = sum(avg_times) / len(avg_times)
            lock_data.append((locks, avg))
            max_time = max(max_time, avg)
    
    if lock_data:
        scale = 60 / max_time if max_time > 0 else 1
        for locks, time in lock_data:
            bar_length = int(time * scale)
            bar = "█" * bar_length
            print(f"  {locks:4d} locks: {bar} {time:.4f}s")
    
    # Chart 2: Circuit complexity comparison
    print("\n\nCircuit Complexity (Integer Triples Required)")
    print("-" * 70)
    
    max_triples = 0
    triple_data = []
    for locks in sorted(lock_counts.keys()):
        triples_list = []
        for data in lock_counts[locks]:
            triples = data['mpc'].get('integer_triples', 0)
            if triples:
                triples_list.append(triples)
        
        if triples_list:
            avg = sum(triples_list) / len(triples_list)
            triple_data.append((locks, int(avg)))
            max_triples = max(max_triples, avg)
    
    if triple_data:
        scale = 60 / max_triples if max_triples > 0 else 1
        for locks, triples in triple_data:
            bar_length = int(triples * scale)
            bar = "▓" * bar_length
            print(f"  {locks:4d} locks: {bar} {triples} triples")
    
    # Chart 3: Communication volume
    print("\n\nCommunication Volume (Global Data Sent)")
    print("-" * 70)
    
    max_comm = 0
    comm_data = []
    for locks in sorted(lock_counts.keys()):
        comm_list = []
        for data in lock_counts[locks]:
            comm = data['mpc'].get('global_data_sent_mb', 0)
            if comm:
                comm_list.append(comm)
        
        if comm_list:
            avg = sum(comm_list) / len(comm_list)
            comm_data.append((locks, avg))
            max_comm = max(max_comm, avg)
    
    if comm_data:
        scale = 60 / max_comm if max_comm > 0 else 1
        for locks, comm in comm_data:
            bar_length = int(comm * scale)
            bar = "▒" * bar_length
            print(f"  {locks:4d} locks: {bar} {comm:.3f} MB")
    
    # Chart 4: Scaling trend analysis
    print("\n\nScaling Trend Analysis")
    print("-" * 70)
    
    if len(lock_data) >= 2:
        lock_data_sorted = sorted(lock_data)
        baseline_locks, baseline_time = lock_data_sorted[0]
        
        print(f"\nBaseline: {baseline_locks} locks = {baseline_time:.4f}s per iteration")
        print("\nScaling factor (compared to baseline):")
        
        for locks, time in lock_data_sorted[1:]:
            ratio = time / baseline_time if baseline_time > 0 else 0
            lock_ratio = locks / baseline_locks if baseline_locks > 0 else 0
            
            # Perfect linear scaling would be ratio = lock_ratio
            efficiency = (lock_ratio / ratio * 100) if ratio > 0 else 0
            
            bar = "█" * min(int(ratio * 20), 60)
            print(f"  {locks:4d} locks: {bar} {ratio:.2f}x slower ({efficiency:.0f}% efficient)")
            print(f"               Expected for linear: {lock_ratio:.2f}x")
    
    print("\n" + "="*70)
    print()

def main():
    # Change to script's directory, then to parent (root), then access logs
    script_dir = Path(__file__).parent
    logs_dir = script_dir / "logs"
    
    if not logs_dir.exists():
        print("Error: locks-scripts/logs/ directory not found. Run experiments first.")
        return
    
    # Collect results
    results = {}
    protocols = ['shamir', 'replicated', 'semi', 'semi2k', 'spdz2k']
    
    # Look for log files
    for mpc_log in logs_dir.glob("LOCKS-*.log"):
        # Skip client logs
        if 'client' in mpc_log.name:
            continue
        
        # Extract scenario and protocol (e.g., "LOCKS-100-shamir")
        stem = mpc_log.stem
        
        # Find which protocol this is
        protocol = None
        for prot in protocols:
            if stem.endswith(f"-{prot}"):
                protocol = prot
                scenario = stem.replace(f"-{prot}", "")
                break
        
        if not protocol:
            print(f"Warning: Could not determine protocol for {mpc_log.name}")
            continue
        
        # Look for corresponding client log
        client_log = logs_dir / f"{scenario}-{protocol}-client.log"
        
        # Create composite key
        full_scenario = f"{scenario}-{protocol}"
        print(f"Processing {full_scenario}...")
        
        mpc_metrics = parse_mpc_log(mpc_log)
        client_metrics = parse_client_log(client_log)
        
        results[full_scenario] = {
            'mpc': mpc_metrics,
            'client': client_metrics,
            'protocol': protocol,
            'locks': mpc_metrics['locks']
        }
    
    if not results:
        print("No log files found. Run experiments first with:")
        print("  bash locks-scripts/run-locks-experiments.sh")
        print("or:")
        print("  bash locks-scripts/compare-locks-protocols.sh")
        return
    
    # Group by protocols and lock counts
    protocols_found = set(data['protocol'] for data in results.values())
    lock_counts = set(data['locks'] for data in results.values() if data['locks'])
    
    print(f"\nFound {len(results)} experiment results:")
    print(f"  Protocols: {', '.join(sorted(protocols_found))}")
    print(f"  Lock counts: {', '.join(str(d) for d in sorted(lock_counts))}")
    
    # Print all tables
    print_table1_circuit_size(results)
    print_table2_timing(results)
    print_table3_communication(results)
    print_table4_breakdown(results)
    
    # Draw ASCII visualizations
    draw_ascii_charts(results)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()
