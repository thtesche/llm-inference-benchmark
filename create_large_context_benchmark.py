#!/usr/bin/env python3
"""
Create synthetic large-context benchmark entries (~100k+ tokens each).
Simulates realistic code context for Prefill/Generation TPS measurement.
"""

import json
from pathlib import Path

def generate_large_code_context(problem_num, target_tokens=100000):
    """Generate synthetic large code context."""
    code_lines = []
    
    # Add file header and imports
    code_lines.append("#!/usr/bin/env python3")
    code_lines.append('"""')
    code_lines.append("Large Python codebase for testing Prefill/Generation TPS.")
    code_lines.append(f"This file contains ~{target_tokens:,} estimated tokens of code.")
    code_lines.append('"""')
    code_lines.append("")
    code_lines.append("import os")
    code_lines.append("import sys")
    code_lines.append("import json")
    code_lines.append("from typing import Dict, List, Tuple, Optional")
    code_lines.append("from dataclasses import dataclass")
    code_lines.append("")
    
    # Generate synthetic functions to fill tokens
    current_tokens = len("\n".join(code_lines)) // 4
    function_count = 0
    
    while current_tokens < target_tokens:
        fn_num = function_count + 1
        
        code_lines.append("")
        code_lines.append("@dataclass")
        code_lines.append(f"class DataHandler_{fn_num}:")
        code_lines.append(f'    """Data handler for module {fn_num}.')
        code_lines.append(f"    Processes and transforms data streams.")
        code_lines.append('    """')
        code_lines.append(f"    module_id: int = {fn_num}")
        code_lines.append(f"    buffer_size: int = {1024 * fn_num}")
        code_lines.append("")
        
        code_lines.append(f"    def process_{fn_num}(self, data: List[Dict]) -> List[Dict]:")
        code_lines.append(f'        """Process data chunk {fn_num}.')
        code_lines.append(f"        Applies transformations and filters.")
        code_lines.append(f"        \"\"\"")
        code_lines.append(f"        results = []")
        code_lines.append(f"        for item in data:")
        code_lines.append(f"            if self.validate_{fn_num}(item):")
        code_lines.append(f"                transformed = self.transform_{fn_num}(item)")
        code_lines.append(f"                results.append(transformed)")
        code_lines.append(f"        return results")
        code_lines.append("")
        
        code_lines.append(f"    def validate_{fn_num}(self, item: Dict) -> bool:")
        code_lines.append(f'        """Validate item for module {fn_num}."""')
        code_lines.append(f"        required_keys = ['id', 'data', 'timestamp']")
        code_lines.append(f"        return all(k in item for k in required_keys)")
        code_lines.append("")
        
        code_lines.append(f"    def transform_{fn_num}(self, item: Dict) -> Dict:")
        code_lines.append(f'        """Transform item for module {fn_num}."""')
        code_lines.append(f"        return {{")
        code_lines.append(f"            'id': item['id'],")
        code_lines.append(f"            'processed': True,")
        code_lines.append(f"            'module': {fn_num},")
        code_lines.append(f"            'data': item.get('data', [])")
        code_lines.append(f"        }}")
        
        current_tokens = len("\n".join(code_lines)) // 4
        function_count += 1
    
    return "\n".join(code_lines)

def create_large_context_benchmark(num_entries=5, tokens_per_entry=100000):
    """Create benchmark with large code contexts."""
    output_file = Path("prompts/swe_context_large.jsonl")
    output_file.parent.mkdir(exist_ok=True)
    
    print(f"[INFO] Generating {num_entries} large-context benchmarks...")
    print(f"[INFO] Each with ~{tokens_per_entry:,} token context")
    print()
    
    with open(output_file, "w") as f:
        for i in range(num_entries):
            print(f"  Generating entry {i+1}/{num_entries}...", end=" ", flush=True)
            
            context = generate_large_code_context(i+1, tokens_per_entry)
            context_tokens = len(context) // 4
            
            entry = {
                "id": f"swe-large-{i+1:02d}",
                "repo": f"example-repo-{i+1}",
                "language": "python",
                "context_tokens": context_tokens,
                "context": context,
                "task": f"Identify and fix the bug in DataHandler_{i+100} that causes data loss when buffer size exceeds threshold. The issue manifests when processing more than 10,000 items.",
                "expected_output": f"The bug is in the process_{i+100} method - buffer flush issue."
            }
            
            f.write(json.dumps(entry) + "\n")
            print(f"✓ ({context_tokens:,} tokens)")
    
    print(f"\n✓ Created {output_file}")
    print(f"✓ {num_entries} entries with ~{tokens_per_entry:,} token contexts")
    print(f"\nUsage:")
    print(f"  python3 api_benchmark.py --url <url> --key <key> --benchmark swe --id 1-{num_entries}")
    print(f"\nExpected behavior:")
    print(f"  - TTFT: 2-5 seconds (not 0.01s)")
    print(f"  - Prefill TPS: 200-300 tok/s (realistic, matching Strata's metrics)")
    print(f"  - Generation TPS: 35-40 tok/s (for streaming decode)")

if __name__ == "__main__":
    create_large_context_benchmark(5, 100000)
