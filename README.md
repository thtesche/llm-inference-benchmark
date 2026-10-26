# LLM Inference Bench

Benchmarking tool for measuring the inference performance of LLMs served via an OpenAI-compatible API (e.g. vLLM). Uses AIME 2026 math competition problems as evaluation prompts.

## Quick Start

```bash
./run_benchmark.sh --url http://localhost:1234/v1 --key YOUR_API_KEY
```

Run a single problem by position (1-based):

```bash
./run_benchmark.sh --url http://localhost:1234/v1 --key YOUR_KEY --id 5
```

Run a range of problems:

```bash
./run_benchmark.sh --url http://localhost:1234/v1 --key YOUR_KEY --id '1-3'
```

Run specific problems:

```bash
./run_benchmark.sh --url http://localhost:1234/v1 --key YOUR_KEY --id 6 8 10
```

## Options

| Flag           | Description                                      |
|----------------|--------------------------------------------------|
| `--url`        | Base URL of the OpenAI-compatible API server     |
| `--key`        | API key for authentication                       |
| `--id`         | Problem position(s) in the JSONL file (1-based). Supports single number, range (`1-3`), or comma-separated list (`6,8,10`). Omit to run all 30 problems. |
| `--server-type`| Server implementation (e.g., `llama.cpp`, `vllm`, `strata`). Optional; if omitted, you will be prompted (last value suggested). |
| `--notes`      | Annotations for this run (e.g., quantization settings, model version). Optional; if omitted, you will be prompted. |
| `--verbose`    | Print the model's thinking process and full answer |

## Metrics

The benchmark provides a detailed performance summary:

### Real-Time Streaming Display

During streaming, the benchmark displays live tokens/sec for the prefill/thinking phase and the answer phase every 0.5 seconds:

```
  [STREAM] Prefill: 150 tok (12.3/s)  |  Answer: 30 tok (4.1/s)  |  Total: 180 tok (10.9/s)
```

This helps you monitor inference progress in real-time.

### Latency & Throughput
- **TTFT** (Time to First Token) – Latency until the first streamed chunk arrives. On a warm
  server this is a prefix-cache hit (~0.1s) and therefore *not* a usable prefill measurement.
- **Prefill** – The practical prefill phase: request start until the first *answer* token.
  It is dominated by context processing (only ~2% of it is reasoning-token generation),
  so `Prefill TPS = input context tokens / Prefill`.
- **Answer-Ph.** – Duration of the visible answer generation phase
  (`Generation TPS = answer tokens / Answer-Ph.`).
- **Latency** – Total wall-clock time for the complete response.
- **Prefill TPS** – Input context throughput (server-reported `prompt_tokens` per prefill second).
- **Generation TPS** – Answer decode throughput (server-reported `completion_tokens` per answer second).

There is deliberately no single "TPS" number: averaging prefill and decode into one value
hides exactly the difference you want to measure.

### Accuracy & Reasoning
- **Answer Accuracy** – Extracted answer compared against the known correct value.
  Free-text tasks (SWE) are not auto-gradable and report `n/a`.
- **Prefill-Ratio** – Percentage of total latency spent in the prefill phase.

### Token Statistics
- **Reason. Toks** – Number of reasoning/thinking tokens.
- **Answer Toks** – Number of visible answer tokens.
- **Total Tokens** – Sum of reasoning and answer tokens.

## Run Archive & History

All benchmark runs are automatically archived to a local SQLite database (`runs.db`) and backed up as JSON files in `benchmark_data/`. This allows you to track performance over time and compare different configurations.

### View Recent Runs

```bash
python compare.py --list
```

Shows recent runs with accuracy, TPS, and notes:
```
  ID    Date                 Server        Model              Accuracy   TPS     Correct/Total
  ====================================================================================================
  3     2026-10-26T14:32:00  llama.cpp     mistral-7b         93.3%      11.5    28/30
  2     2026-10-26T10:15:00  vllm          mistral-7b         90.0%      12.1    27/30
  1     2026-10-25T20:00:00  llama.cpp     mistral-7b         88.0%      10.2    26/30
```

### Compare Two Runs

```bash
python compare.py --run-1 1 --run-2 3
```

Shows side-by-side metrics and per-problem differences (accuracy, TTFT, TPS).

### Web Dashboard

```bash
python app.py
```

Opens http://localhost:5000 with:
- Recent runs and quick stats
- Run details with all problem results
- Interactive run comparison tool
- Performance trends (charts over time)

## Example Output

```text
===================================================================================================================
  ADVANCED STATISTICS & PERFORMANCE SUMMARY
===================================================================================================================
  ID             Status      Exp   Rec      TTFT  Prefill       Ans-Time     Latency   Tok-R   Tok-A Pref-TPS Gen-TPS
  ---------------------------------------------------------------------------------------------------------------
  2026-I-1       CORRECT      42    42     3.17s   2m 29.05s   2m 22.32s   4m 54.55s    1776    1584    338.2    34.5

  ---------------------------------------------------------------------------------------------------------------
  Total:  1 tasks | 1 successful | 0 failed
  Correct: 1/1 (100.0%)

  TTFT         - Min: 3.17s     | Max: 3.17s     | Avg: 3.17s
  Prefill-Ph.  - Min: 2m 29.05s | Max: 2m 29.05s | Avg: 2m 29.05s
  Answer-Ph.   - Min: 2m 22.32s | Max: 2m 22.32s | Avg: 2m 22.32s
  Full Latency - Min: 4m 54.55s | Max: 4m 54.55s | Avg: 4m 54.55s
  Prefill-Ratio - Min: 50.6%    | Max: 50.6%     | Avg: 50.6%

  Reason. Toks - Min: 1776      | Max: 1776      | Avg: 1776
  Answer Toks  - Min: 1584      | Max: 1584      | Avg: 1584
  Total Tokens - Min: 3360      | Max: 3360      | Avg: 3360

  Prefill TPS  - Min: 338.2     | Max: 338.2     | Avg: 338.2
  Generation TPS - Min: 34.5    | Max: 34.5      | Avg: 34.5
===================================================================================================================
```

## Prompt Data

The AIME 2026 problem set (`prompts/aime_2026.jsonl`) is a copy of the prompts from the [MTPLX](https://github.com/youssofal/MTPLX) benchmark suite:

> **Source:** [youssofal/MTPLX – `mtplx/benchmarks/prompts/aime_2026.jsonl`](https://github.com/youssofal/MTPLX/blob/main/mtplx/benchmarks/prompts/aime_2026.jsonl)

The file contains 30 problems (15 from AIME I, 15 from AIME II), each with an `id`, problem statement, and expected integer answer.

## For LLM Agents

See [LLMDOC.md](LLMDOC.md) for a complete command reference designed for automated agent execution. It includes:

- Structured command syntax with required/optional flags
- JSON output modes for programmatic processing
- Exit codes for error handling
- Typical LLM workflow examples

## License

This project is licensed under the GNU Lesser General Public License v2.1. See [LICENSE](LICENSE) for details.
