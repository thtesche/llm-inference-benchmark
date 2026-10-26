#!/usr/bin/env python3
"""CLI tool for comparing benchmark runs."""

import argparse
import json
from archive import list_runs, get_run, compare_runs
from datetime import datetime

def format_time(seconds):
    """Format seconds into readable duration."""
    if seconds is None or seconds < 0:
        return "0.00s"
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:05.2f}s"

def print_runs_table(runs):
    """Pretty-print runs list."""
    if not runs:
        print("No runs found.")
        return
    
    print("\n" + "="*134)
    print("  ID    Date                 Server        Model              Accuracy  Ctx Tok   Pref-TPS  Gen-TPS   Correct/Total   Notes")
    print("="*134)
    
    for run in runs:
        run_id = run["id"]
        timestamp = run["timestamp"][:19]  # Remove Z
        server = run["server_type"] or "unknown"
        model = (run["model"] or "unknown")[:18]
        accuracy = f"{run['accuracy']*100:.1f}%" if run.get('accuracy') is not None else "n/a"
        ctx = f"{run.get('avg_context_tokens') or 0:,}" if run.get('avg_context_tokens') else "-"
        pref = f"{run.get('avg_prefill_tps') or 0:.1f}"
        gen = f"{run.get('avg_generation_tps') or 0:.1f}"
        correct = f"{run['correct']}/{run['total']}"
        notes = (run["notes"] or "")[:30]

        print(f"  {run_id:<4} {timestamp:<21} {server:<13} {model:<18} {accuracy:>9} {ctx:>8} {pref:>10} {gen:>8}  {correct:>13}  {notes}")

    print("="*134)

def print_run_details(run):
    """Pretty-print full run details."""
    print("\n" + "="*150)
    print(f"Run ID: {run['id']} | {run['timestamp']} | Server: {run['server_type']} | Model: {run['model']}")
    if run['notes']:
        print(f"Notes: {run['notes']}")
    print("="*150)
    
    accuracy = f"{run['accuracy']*100:.1f}%" if run.get('accuracy') is not None else "n/a (not auto-gradable)"
    print(f"\nAccuracy: {accuracy} ({run['total_correct']}/{run['total_problems']})")
    print(f"Avg TTFT: {format_time(run['avg_ttft'])} | Avg TPS: {run['avg_tps']:.1f}")
    print(f"Prefill TPS: {run.get('avg_prefill_tps') or 0:.1f} | Generation TPS: {run.get('avg_generation_tps') or 0:.1f} "
          f"| Avg Context: {run.get('avg_context_tokens') or 0:,} tokens\n")

    print("  Pos  Problem        Expected Received Correct  TTFT      Thinking   Answer     Total      Tokens   TPS     CtxTok   Pref-TPS Gen-TPS")
    print("-"*150)
    
    for result in run['results']:
        pos = result['position']
        problem = result['problem_id'][:12]
        expected = result['expected'][:5]
        received = result['extracted'][:5] if result['extracted'] else "---"
        correct = "n/a" if result['correct'] is None else ("✓" if result['correct'] else "✗")
        ttft = format_time(result['ttft'])
        think = format_time(result['reasoning_time'])
        answer = format_time(result['answer_time'])
        total = format_time(result['total_latency'])
        tokens = result['total_tokens']
        tps = f"{result['tps']:.1f}" if result['tps'] > 0 else "0.0"
        ctx = result.get('input_context_tokens') or 0
        pref = f"{result.get('prefill_tps') or 0:.1f}"
        gen = f"{result.get('generation_tps') or 0:.1f}"

        print(f"  {pos:<3} {problem:<13} {expected:>8} {received:>8} {correct:>7} {ttft:>9} {think:>10} {answer:>10} {total:>10} {tokens:>7}  {tps:>5} {ctx:>8} {pref:>9} {gen:>7}")

    print("="*150)

def print_comparison(comparison):
    """Pretty-print comparison between two runs."""
    if not comparison:
        print("Could not compare runs.")
        return
    
    run1 = comparison['run_1']
    run2 = comparison['run_2']
    diff = comparison['differences']
    
    print("\n" + "="*140)
    print(f"COMPARISON: Run {run1['id']} vs Run {run2['id']}")
    print("="*140)
    
    run1_label = f"Run {run1['id']}"
    run2_label = f"Run {run2['id']}"
    print(f"\n{'Metric':<20} {run1_label:<25} {run2_label:<25} {'Delta':<20}")
    print("-"*140)
    
    acc1 = f"{run1['accuracy']*100:.1f}%" if run1.get('accuracy') is not None else "n/a"
    acc2 = f"{run2['accuracy']*100:.1f}%" if run2.get('accuracy') is not None else "n/a"
    acc_delta = f"{diff['accuracy_delta']*100:+.1f}%" if diff.get('accuracy_delta') is not None else "—"
    print(f"{'Accuracy':<20} {acc1:<25} {acc2:<25} {acc_delta:<20}")

    pref1 = run1.get('avg_prefill_tps') or 0
    pref2 = run2.get('avg_prefill_tps') or 0
    gen1 = run1.get('avg_generation_tps') or 0
    gen2 = run2.get('avg_generation_tps') or 0
    ctx1 = run1.get('avg_context_tokens') or 0
    ctx2 = run2.get('avg_context_tokens') or 0
    print(f"{'Prefill TPS':<20} {pref1:<25.1f} {pref2:<25.1f} {pref2 - pref1:<+20.1f}")
    print(f"{'Generation TPS':<20} {gen1:<25.1f} {gen2:<25.1f} {gen2 - gen1:<+20.1f}")
    print(f"{'Context (tokens)':<20} {ctx1:<25,} {ctx2:<25,} {ctx2 - ctx1:<+20,}")
    
    ttft1 = format_time(run1['avg_ttft'])
    ttft2 = format_time(run2['avg_ttft'])
    ttft_delta = f"{diff['ttft_delta']:+.3f}s"
    print(f"{'Avg TTFT':<20} {ttft1:<25} {ttft2:<25} {ttft_delta:<20}")
    
    tps1 = f"{run1['avg_tps']:.1f}"
    tps2 = f"{run2['avg_tps']:.1f}"
    tps_delta = f"{diff['tps_delta']:+.1f}"
    print(f"{'Avg TPS':<20} {tps1:<25} {tps2:<25} {tps_delta:<20}")
    
    print(f"\nServer: {run1['server_type']} → {run2['server_type']}")
    print(f"Model: {run1['model']} → {run2['model']}")
    print(f"Timestamp: {run1['timestamp']} → {run2['timestamp']}")
    
    print("\n" + "="*140)
    print("DETAILED PROBLEM COMPARISON")
    print("="*140)
    print("  Pos  Problem        Run 1      Run 2      Correct  TTFT Δ       TPS Δ")
    print("-"*140)
    
    for detail in comparison['detailed_results']:
        pos = detail['position']
        problem = detail['problem_id'][:12]
        def _mark(value):
            return "n/a" if value is None else ("✓" if value else "✗")

        r1_correct = _mark(detail['run_1']['correct'])
        r2_correct = _mark(detail['run_2']['correct'])
        if detail['run_1']['correct'] is None or detail['run_2']['correct'] is None:
            correct_emoji = "—"
        else:
            correct_emoji = "✓" if detail['run_1']['correct'] == detail['run_2']['correct'] else "△"
        ttft_delta = f"{detail['run_2']['ttft'] - detail['run_1']['ttft']:+.2f}s"
        tps_delta = f"{detail['run_2']['tps'] - detail['run_1']['tps']:+.1f}"
        
        print(f"  {pos:<3} {problem:<13} {r1_correct:<9} {r2_correct:<9} {correct_emoji:>7} {ttft_delta:>12} {tps_delta:>8}")
    
    print("="*140)

def main():
    parser = argparse.ArgumentParser(description="Compare benchmark runs.")
    parser.add_argument("--list", action="store_true", help="List all runs")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of runs (default: 10)")
    parser.add_argument("--server-type", type=str, help="Filter by server type")
    parser.add_argument("--run-1", type=int, help="First run ID for comparison")
    parser.add_argument("--run-2", type=int, help="Second run ID for comparison")
    parser.add_argument("--compare", type=int, nargs=2, help="Compare two runs (IDs)")
    parser.add_argument("--detail", type=int, help="Show detailed results for a run")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.list:
        runs = list_runs(limit=args.limit, server_type_filter=args.server_type)
        if args.json:
            print(json.dumps(runs, indent=2))
        else:
            print_runs_table(runs)
    
    elif args.detail:
        run = get_run(args.detail)
        if run:
            if args.json:
                print(json.dumps(run, indent=2))
            else:
                print_run_details(run)
        else:
            print(f"Run {args.detail} not found.")
    
    elif args.run_1 and args.run_2:
        comparison = compare_runs(args.run_1, args.run_2)
        if comparison:
            if args.json:
                print(json.dumps(comparison, indent=2))
            else:
                print_comparison(comparison)
        else:
            print(f"Could not compare runs {args.run_1} and {args.run_2}")
    
    elif args.compare:
        comparison = compare_runs(args.compare[0], args.compare[1])
        if comparison:
            if args.json:
                print(json.dumps(comparison, indent=2))
            else:
                print_comparison(comparison)
        else:
            print(f"Could not compare runs {args.compare[0]} and {args.compare[1]}")
    
    else:
        # Default: show recent runs
        runs = list_runs(limit=args.limit, server_type_filter=args.server_type)
        if args.json:
            print(json.dumps(runs, indent=2))
        else:
            print_runs_table(runs)

if __name__ == "__main__":
    main()
