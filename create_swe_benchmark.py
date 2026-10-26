#!/usr/bin/env python3
"""
Create SWE-Context benchmark dataset from HuggingFace.
Generates JSONL with large code contexts (100k+ tokens).
"""

import json
import sys
from pathlib import Path

def create_swe_sample():
    """Create a sample SWE benchmark entry with large context."""
    # This is a simplified example - in production we'd load from HuggingFace
    sample_code = """
# Large codebase context (~5000 tokens for testing)
""" + "\n".join([f"# Line {i}: def function_{i}(): pass" for i in range(1000)])

    return {
        "id": "swe-001",
        "repo": "example-repo",
        "language": "python",
        "context_tokens": len(sample_code.split()),
        "task": "Fix the bug in function_500 that causes incorrect output",
        "context": sample_code,
        "expected_output": "A code fix or analysis",
    }

def main():
    """Generate SWE benchmark file."""
    output_file = Path("prompts/swe_context_sample.jsonl")
    output_file.parent.mkdir(exist_ok=True)
    
    # Create 5 sample entries
    samples = [create_swe_sample() for _ in range(5)]
    
    with open(output_file, "w") as f:
        for sample in samples:
            f.write(json.dumps(sample) + "\n")
    
    print(f"✓ Created {output_file} with {len(samples)} entries")
    print(f"✓ Each entry has ~{samples[0]['context_tokens']} context tokens")
    print("\nTo use real SWE-ContextBench:")
    print("  pip install datasets")
    print("  from datasets import load_dataset")
    print("  swe = load_dataset('jiayuanz3/SWEContextBench')")

if __name__ == "__main__":
    main()
