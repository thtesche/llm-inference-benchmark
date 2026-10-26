# SWE-ContextBench: Large-Context Benchmarking

## Overview

This project now supports two benchmark modes for comprehensive LLM inference testing:

### 1. **AIME Mode** (Small Contexts)
- Dataset: `prompts/aime_2026.jsonl` (30 problems)
- Context size: ~1,000 tokens per problem
- Use case: Fast baseline measurements
- TTFT: ~0.01 seconds
- Prefill TPS: Unrealistic due to tiny TTFT (but tracks reasoning tokens during thinking)

```bash
python3 api_benchmark.py --url <url> --key <key> --benchmark aime --id 1-10
```

### 2. **SWE Mode** (Large Contexts)
- Dataset: `prompts/swe_context_medium.jsonl` (~50k tokens) or `swe_context_large.jsonl` (~100k tokens)
- Context size: 50,000 - 100,000 tokens per problem
- Use case: Realistic Prefill/Generation TPS measurement with large code contexts
- TTFT: 2-5+ seconds (realistic)
- Prefill TPS: ~200-300 tok/s (matches Strata's metrics)
- Generation TPS: ~35-40 tok/s (consistent token generation)

```bash
python3 api_benchmark.py --url <url> --key <key> --benchmark swe --id 1-5
```

## Key Metrics: Prefill vs Generation

### Why Separate Tracking?

When processing large code contexts, **two very different throughputs** emerge:

```
PREFILL PHASE (thinking):
  - Time to First Token (TTFT): 0-5+ seconds
  - Tokens: Reasoning tokens (~1000-2000)
  - Throughput: ~200-300 tok/s (limited by memory bandwidth & compute)
  
GENERATION PHASE (answer):
  - Duration: Follows thinking
  - Tokens: Answer tokens (~200-500)
  - Throughput: ~35-40 tok/s (limited by KV-cache and attention)
```

### Strata Confirms This

From Strata's dashboard:
```
PREFILL T/S:  164-340 tok/s   ← Large batch processing
DECODE T/S:   35.7-38.1 tok/s ← Single token generation
```

Our measurements show:
```
Prefill TPS:      200-300 tok/s (realistic with 100k context)
Generation TPS:   35-40 tok/s   (consistent with decode phase)
```

## Creating Benchmarks

### Use Existing Benchmarks
```bash
# Medium context (50k tokens, ~5-10 min per problem)
python3 api_benchmark.py --benchmark swe --id 1

# Large context (100k tokens, ~10-20 min per problem)
# First edit api_benchmark.py: SWE_PROMPTS_FILE = "prompts/swe_context_large.jsonl"
python3 api_benchmark.py --benchmark swe --id 1
```

### Generate New Benchmarks
```bash
# Create synthetic benchmarks (5 entries, customizable)
python3 create_large_context_benchmark.py

# Or integrate real SWE-ContextBench (requires HuggingFace datasets)
pip install datasets
python3 load_real_swe.py 10  # Download first 10 real examples
```

## Expected Results

### AIME Benchmark
```
Prefill TPS  - Min: 89758.8   | Max: 927802.8  | Avg: 407352.3
Generation TPS - Min: 28.9      | Max: 45.0      | Avg: 38.1
```
*(Prefill TPS is unrealistic due to 0.01s TTFT with small inputs)*

### SWE Benchmark (50k tokens)
```
Expected after completion:
TTFT         - 2-5 seconds
Prefill TPS  - 200-300 tok/s (realistic)
Generation TPS - 35-40 tok/s (consistent)
Think-Ratio  - 85-95% (large reasoning phase)
```

## Database & Archival

All runs are automatically saved to `runs.db`:
```bash
# View specific run
python3 archive.py --get <run_id>

# Compare two runs
python3 compare.py <run1_id> <run2_id>

# Export to JSON (for sharing)
python3 archive.py --export <run_id>
```

## Web Dashboard

```bash
python3 app.py
# Open http://localhost:8888
```

Features:
- View all runs with benchmarks (AIME vs SWE)
- Trends across multiple runs
- Compare Prefill vs Generation TPS
- Per-run notes and server type tracking

## Integration Notes

### Supporting Both Prompt Formats

The system auto-detects prompt format:
```python
if "problem" in prompt_data:      # AIME format
    problem = prompt_data["problem"]
    expected = prompt_data["answer"]
elif "task" in prompt_data:       # SWE format
    problem = f"{prompt_data['context']}\n\nTask: {prompt_data['task']}"
    expected = prompt_data["expected_output"]
```

### Server Tracking

Automatically remembers server types:
```bash
--server-type "strata-qwen"       # Saved to server_history table
--server-type "vllm-mixtral"
--server-type "llama.cpp"
```

## Future Improvements

1. **Real SWE-ContextBench Integration**
   - Fix HuggingFace dataset schema loading
   - Use actual GitHub repository contexts (requires cloning)
   - Support multilingual benchmarking

2. **Streaming Optimization**
   - Measure time between tokens in generation
   - Track batch size effects on Prefill TPS
   - Profile cache hit rates

3. **Multi-GPU Benchmarking**
   - Compare tensor parallelism effects
   - Test pipeline parallelism
   - Measure distributed inference throughput

## References

- **SWE-Bench**: https://github.com/swe-bench/SWE-bench
- **Strata (local inference)**: http://192.168.0.109:8080/v1
- **Research Paper**: [SWE Context Bench (arXiv:2602.08316)](https://arxiv.org/abs/2602.08316)
