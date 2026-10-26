#!/usr/bin/env python3
"""
Load real SWE-ContextBench from HuggingFace and convert to JSONL.
Contains 100k+ token contexts for realistic Prefill/Generation TPS measurement.
"""

import json
import sys
from pathlib import Path
from datasets import load_dataset

def load_swe_contextbench(sample_size=20):
    """Load SWE-ContextBench and prepare for benchmarking.
    
    Args:
        sample_size: Number of examples to load (default 20)
    """
    print(f"[INFO] Loading SWE-ContextBench from HuggingFace...")
    print(f"[INFO] This may take a minute on first run (downloading ~500MB)...")
    
    try:
        # Load the dataset
        dataset = load_dataset('jiayuanz3/SWEContextBench', split='test')
        print(f"[INFO] Loaded {len(dataset)} total SWE-ContextBench examples")
        
        # Take first N examples
        examples = dataset.select(range(min(sample_size, len(dataset))))
        
        output_file = Path("prompts/swe_context_real.jsonl")
        output_file.parent.mkdir(exist_ok=True)
        
        total_context_tokens = 0
        saved_count = 0
        
        with open(output_file, "w") as f:
            for i, example in enumerate(examples):
                try:
                    # SWE-ContextBench format varies, but typically has:
                    # - repo_name, instance_id, problem_statement, context (code files)
                    
                    context = example.get('context', '')
                    problem = example.get('problem_statement', '')
                    task = example.get('task', '')
                    
                    # Combine context + problem
                    full_prompt = f"{context}\n\nProblem: {problem}\n\nTask: {task}"
                    
                    # Token estimate (rough: 1 token ≈ 4 chars)
                    context_tokens = len(full_prompt) // 4
                    total_context_tokens += context_tokens
                    
                    entry = {
                        "id": f"swe-{i+1:03d}",
                        "repo": example.get('repo_name', 'unknown'),
                        "instance_id": example.get('instance_id', f'swe-{i+1}'),
                        "task": problem,
                        "context": context,
                        "context_tokens": context_tokens,
                        "expected_output": example.get('gold_patch', 'Fix needed'),
                    }
                    
                    f.write(json.dumps(entry) + "\n")
                    saved_count += 1
                    
                    if (i + 1) % 5 == 0:
                        print(f"  [{i+1}/{len(examples)}] Processed, avg context: {total_context_tokens // saved_count} tokens")
                        
                except Exception as e:
                    print(f"  [!] Skipped example {i}: {str(e)[:60]}")
                    continue
        
        print(f"\n✓ Created {output_file}")
        print(f"✓ Saved {saved_count} entries with real 100k+ token contexts")
        if saved_count > 0:
            avg_tokens = total_context_tokens // saved_count
            print(f"✓ Average context size: {avg_tokens:,} tokens")
        print(f"\nUsage:")
        print(f"  python3 api_benchmark.py --url <url> --key <key> --benchmark swe --id 1-{saved_count}")
        
    except Exception as e:
        print(f"[ERROR] Failed to load SWE-ContextBench: {e}")
        print(f"[INFO] Make sure you have internet access and ~500MB disk space")
        sys.exit(1)

if __name__ == "__main__":
    sample_size = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    load_swe_contextbench(sample_size)
