#!/usr/bin/env python3
"""
Analyze party-scaling results from scalability-scripts/logs/.

Log file naming: {SCENARIO}-N{n_parties}-shamir[.log | -client.log]
  SCENARIO = ACS-1000 | LOCKS-1000 | PRESCAR-1024D | BLOODSUGAR

Reports:
  Table 1  – Per-iteration time  (rows = N_PARTIES, cols = scenario)
  Table 2  – Global communication (rows = N_PARTIES, cols = scenario)
  Table 3  – Timing breakdown per scenario/parties
  ASCII    – Scaling trend per scenario
"""

import re
import sys
from pathlib import Path

SCENARIOS = ["ACS-1000", "LOCKS-1000", "PRESCAR-1024D", "BLOODSUGAR"]
PROTOCOL  = "shamir"


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_mpc_log(path: Path) -> dict:
    m = {
        "data_sent_mb": None,
        "global_data_sent_mb": None,
        "iterations": None,
        "timer_1_total":  0.0,
        "timer_10_total": 0.0,
        "timer_11_total": 0.0,
        "timer_12_total": 0.0,
        "timer_13_total": 0.0,
    }
    try:
        text = path.read_text()
    except FileNotFoundError:
        return m

    for pat, key in [
        (r"Data sent = ([\d.]+) MB",        "data_sent_mb"),
        (r"Global data sent = ([\d.]+) MB",  "global_data_sent_mb"),
    ]:
        hit = re.search(pat, text)
        if hit:
            m[key] = float(hit.group(1))

    hit = re.search(r"(\d+)\s+iterations", text)
    if hit:
        m["iterations"] = int(hit.group(1))

    for t in [1, 10, 11, 12, 13]:
        for hit in re.finditer(rf"Time{t} = ([\d.]+)", text):
            m[f"timer_{t}_total"] += float(hit.group(1))

    return m


def parse_client_log(path: Path) -> dict:
    m = {
        "total_time": None,
        "avg_iteration_time": None,
        "avg_send_time": None,
        "avg_receive_time": None,
    }
    try:
        text = path.read_text()
    except FileNotFoundError:
        return m

    for pat, key in [
        (r"Total experiment time:\s+([\d.]+)s",    "total_time"),
        (r"Average iteration time:\s+([\d.]+)s",   "avg_iteration_time"),
        (r"Average send time:\s+([\d.]+)s",        "avg_send_time"),
        (r"Average receive time:\s+([\d.]+)s",     "avg_receive_time"),
    ]:
        hit = re.search(pat, text)
        if hit:
            m[key] = float(hit.group(1))

    return m


# ---------------------------------------------------------------------------
# Load all results
# ---------------------------------------------------------------------------

def load_results(logs_dir: Path) -> dict:
    """Return {(scenario, n_parties): {"mpc": ..., "client": ...}}"""
    results = {}
    pattern = re.compile(
        r"^(" + "|".join(re.escape(s) for s in SCENARIOS) + r")"
        r"-N(\d+)-" + PROTOCOL + r"\.log$"
    )

    for mpc_path in sorted(logs_dir.glob(f"*-{PROTOCOL}.log")):
        if "client" in mpc_path.name:
            continue
        hit = pattern.match(mpc_path.name)
        if not hit:
            print(f"  skip (unrecognised): {mpc_path.name}")
            continue

        scenario  = hit.group(1)
        n_parties = int(hit.group(2))

        stem       = mpc_path.stem                          # e.g. ACS-1000-N3-shamir
        client_path = logs_dir / f"{stem}-client.log"

        mpc_m    = parse_mpc_log(mpc_path)
        client_m = parse_client_log(client_path)

        results[(scenario, n_parties)] = {"mpc": mpc_m, "client": client_m}

    return results


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt(v, fmt=".4f"):
    return format(v, fmt) if v is not None else "N/A"


def _cell(v, fmt=".4f", width=12):
    return _fmt(v, fmt).rjust(width)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def print_table1_timing(results, party_counts, scenarios):
    col_w = 14
    hdr = "N_Parties".ljust(10)
    for s in scenarios:
        hdr += s.rjust(col_w)
    sep = "=" * len(hdr)

    print()
    print(sep)
    print("TABLE 1: Per-Iteration Time (seconds)")
    print(sep)
    print(hdr)
    print("-" * len(hdr))

    for n in party_counts:
        row = str(n).ljust(10)
        for s in scenarios:
            v = results.get((s, n), {}).get("client", {}).get("avg_iteration_time")
            row += _cell(v, ".4f", col_w)
        print(row)

    print(sep)
    print()


def print_table2_communication(results, party_counts, scenarios):
    col_w = 14
    hdr = "N_Parties".ljust(10)
    for s in scenarios:
        hdr += s.rjust(col_w)
    sep = "=" * len(hdr)

    print()
    print(sep)
    print("TABLE 2: Global Data Sent (MB, full experiment)")
    print(sep)
    print(hdr)
    print("-" * len(hdr))

    for n in party_counts:
        row = str(n).ljust(10)
        for s in scenarios:
            v = results.get((s, n), {}).get("mpc", {}).get("global_data_sent_mb")
            row += _cell(v, ".3f", col_w)
        print(row)

    print(sep)
    print()


def print_table3_breakdown(results, party_counts, scenarios):
    sep = "=" * 74

    print()
    print(sep)
    print("TABLE 3: Timing Breakdown per Iteration (seconds)  [Recv | Compute | Reveal | Send | Total]")
    print(sep)

    for s in scenarios:
        print(f"\n  {s}")
        print(f"  {'N_Parties':<10} {'Recv':>9} {'Compute':>9} {'Reveal':>9} {'Send':>9} {'Total':>9}")
        print("  " + "-" * 60)
        for n in party_counts:
            entry = results.get((s, n))
            if entry is None:
                print(f"  {n:<10} {'N/A':>9} {'N/A':>9} {'N/A':>9} {'N/A':>9} {'N/A':>9}")
                continue
            mpc  = entry["mpc"]
            iters = mpc["iterations"] or 1
            recv    = mpc["timer_10_total"] / iters
            compute = mpc["timer_11_total"] / iters
            reveal  = mpc["timer_12_total"] / iters
            send    = mpc["timer_13_total"] / iters
            total   = mpc["timer_1_total"]  / iters
            print(f"  {n:<10} {recv:>9.4f} {compute:>9.4f} {reveal:>9.4f} {send:>9.4f} {total:>9.4f}")

    print()
    print(sep)
    print()


# ---------------------------------------------------------------------------
# ASCII scaling chart
# ---------------------------------------------------------------------------

def draw_scaling_charts(results, party_counts, scenarios):
    BAR_WIDTH = 50
    sep = "=" * 70

    print()
    print(sep)
    print("SCALING CHARTS: Per-Iteration Time vs N_Parties")
    print(sep)

    for s in scenarios:
        times = [(n, results[(s, n)]["client"]["avg_iteration_time"])
                 for n in party_counts
                 if (s, n) in results and results[(s, n)]["client"]["avg_iteration_time"] is not None]

        if not times:
            print(f"\n  {s}: no data")
            continue

        max_t = max(t for _, t in times)
        baseline_n, baseline_t = times[0]

        print(f"\n  {s}  (baseline N={baseline_n}: {baseline_t:.4f}s)")
        for n, t in times:
            bar = "█" * int(t / max_t * BAR_WIDTH)
            ratio = t / baseline_t if baseline_t > 0 else 0
            print(f"  N={n:<3} {bar:<{BAR_WIDTH}} {t:.4f}s  ({ratio:.2f}x)")

    print()
    print(sep)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    script_dir = Path(__file__).parent
    logs_dir   = script_dir.parent / "logs" / "scalability"

    if not logs_dir.exists():
        print(f"Error: {logs_dir} not found – run experiments first.")
        sys.exit(1)

    print(f"Loading results from {logs_dir} ...")
    results = load_results(logs_dir)

    if not results:
        print("No matching log files found.")
        print("Expected names like:  ACS-1000-N3-shamir.log")
        sys.exit(1)

    party_counts = sorted({n for _, n in results})
    scenarios    = [s for s in SCENARIOS if any(s == sc for sc, _ in results)]

    print(f"Found {len(results)} result(s).")
    print(f"  Scenarios : {', '.join(scenarios)}")
    print(f"  N_Parties : {', '.join(map(str, party_counts))}")

    print_table1_timing(results, party_counts, scenarios)
    print_table2_communication(results, party_counts, scenarios)
    print_table3_breakdown(results, party_counts, scenarios)
    draw_scaling_charts(results, party_counts, scenarios)

    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
