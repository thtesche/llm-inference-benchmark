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
    
    print("\n" + "="*120)
    print("  ID    Date                 Server        Model              Accuracy   TPS     Correct/Total   Notes")
    print("="*120)
    
    for run in runs:
        run_id = run["id"]
        timestamp = run["timestamp"][:19]  # Remove Z
        server = run["server_type"] or "unknown"
        model = (run["model"] or "unknown")[:18]
        accuracy = f"{run['accuracy']*100:.1f}%"
        tps = f"{run['avg_tps']:.1f}" if run['avg_tps'] else "0.0"
        correct = f"{run['correct']}/{run['total']}"
        notes = (run["notes"] or "")[:40]
        
        print(f"  {run_id:<4} {timestamp:<21} {server:<13} {model:<18} {accuracy:>9} {tps:>6}  {correct:>13}  {notes}")
    
    print("="*120)

def print_run_details(run):
    """Pretty-print full run details."""
    print("\n" + "="*150)
    print(f"Run ID: {run['id']} | {run['timestamp']} | Server: {run['server_type']} | Model: {run['model']}")
    if run['notes']:
        print(f"Notes: {run['notes']}")
    print("="*150)
    
    print(f"\nAccuracy: {run['accuracy']*100:.1f}% ({run['total_correct']}/{run['total_problems']})")
    print(f"Avg TTFT: {format_time(run['avg_ttft'])} | Avg TPS: {run['avg_tps']:.1f}\n")
    
    print("  Pos  Problem        Expected Received Correct  TTFT      Thinking   Answer     Total      Tokens   TPS")
    print("-"*150)
    
    for result in run['results']:
        pos = result['position']
        problem = result['problem_id'][:12]
        expected = result['expected'][:5]
        received = result['extracted'][:5] if result['extracted'] else "---"
        correct = "✓" if result['correct'] else "✗"
        ttft = format_time(result['ttft'])
        think = format_time(result['reasoning_time'])
        answer = format_time(result['answer_time'])
        total = format_time(result['total_latency'])
        tokens = result['total_tokens']
        tps = f"{result['tps']:.1f}" if result['tps'] > 0 else "0.0"
        
        print(f"  {pos:<3} {problem:<13} {expected:>8} {received:>8} {correct:>7} {ttft:>9} {think:>10} {answer:>10} {total:>10} {tokens:>7}  {tps:>5}")
    
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
    
    acc1 = f"{run1['accuracy']*100:.1f}%"
    acc2 = f"{run2['accuracy']*100:.1f}%"
    acc_delta = f"{diff['accuracy_delta']*100:+.1f}%"
    print(f"{'Accuracy':<20} {acc1:<25} {acc2:<25} {acc_delta:<20}")
    
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
        r1_correct = "✓" if detail['run_1']['correct'] else "✗"
        r2_correct = "✓" if detail['run_2']['correct'] else "✗"
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
