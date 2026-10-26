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
- TTFT: ~0.1s (prefix cache hit on a warm server)
- Prefill TPS: ~340 tok/s (matches Strata's metrics)
- Generation TPS: ~34 tok/s (consistent token generation)

```bash
# ~100k token contexts (default)
python3 api_benchmark.py --url <url> --key <key> --benchmark swe --id 1-5

# ~50k token contexts
SWE_PROMPTS_FILE=prompts/swe_context_medium.jsonl \
  python3 api_benchmark.py --url <url> --key <key> --benchmark swe --id 1
```

`SWE_PROMPTS_FILE` selects the prompt file (default `prompts/swe_context_large.jsonl`).
Run one benchmark at a time - parallel requests distort throughput measurements.

## Key Metrics: Prefill vs Generation

### Why Separate Tracking?

When processing large code contexts, **two very different throughputs** emerge:

```
PREFILL PHASE (context -> first answer token):
  - CPU/GPU work: read the whole input context into the KV cache
  - Duration: here "reasoning_duration" = time from request start to first answer token
  - Tokens: input context (server-reported prompt_tokens)
  - Throughput: ~340 tok/s (limited by memory bandwidth & compute)

GENERATION PHASE (answer):
  - Duration: first answer token -> last answer token
  - Tokens: answer tokens (server-reported completion_tokens, thinking excluded)
  - Throughput: ~34 tok/s (limited by KV-cache and attention)
```

The bare TTFT (~0.1s) is *not* used as the prefill phase: on this server the
context comes from the prefix cache. The reasoning/thinking phase is dominated by
context processing, so it is used as the prefill phase - which is what makes the
result comparable to Strata's PREFILL T/S (Strata: PROMPT / (DURATION - decode time)).

Input context size comes from the server's `prompt_tokens` when available; the
local `len(text) // 4` estimate is only a fallback. Output token counts use
`completion_tokens` (never `total_tokens`, which includes the prompt).

### Strata Confirms This

From Strata's dashboard:
```
PREFILL T/S:  164-340 tok/s   ← Large batch processing
DECODE T/S:   35.7-38.1 tok/s ← Single token generation
```

Our measurements (qwen3.8-flash-next-q2_0, Strata, sequential runs):
```
Run #3 - 100k context file (112,034 prompt tokens):
  Prefill TPS:    338.2   Generation TPS: 34.5   Answer tokens: 6,656
Run #4 - 50k context file (72,009 prompt tokens):
  Prefill TPS:    336.0   Generation TPS: 33.5   Answer tokens: 2,315
```

## Creating Benchmarks

### Use Existing Benchmarks
```bash
# Medium context (50k tokens, ~5-10 min per problem)
python3 api_benchmark.py --benchmark swe --id 1

# Large context (100k tokens, ~5-9 min per problem)
SWE_PROMPTS_FILE=prompts/swe_context_large.jsonl python3 api_benchmark.py --benchmark swe --id 1
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

### SWE Benchmark
```
TTFT           - ~0.1s (prefix cache)
Prefill TPS    - ~340 tok/s
Generation TPS - ~34 tok/s
Think-Ratio    - 60-75% (context processing dominates)
```

SWE tasks have a free-text `expected_output`, so they cannot be auto-graded:
such results store `correct = NULL` and the run reports accuracy `n/a`
instead of a misleading 0%.

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
- Run list with context tokens, Prefill TPS and Generation TPS per run
- Per-run detail: summary cards, per-problem Ctx/Prefill/Gen columns
- Trends: Accuracy, TPS, Prefill vs Generation TPS, TTFT, runs by server type
- Compare: Prefill/Generation/Context deltas per run and per problem
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
