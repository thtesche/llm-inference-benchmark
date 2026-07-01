# LLM Inference Bench

Benchmarking tool for measuring the inference performance of LLMs served via an OpenAI-compatible API (e.g. vLLM). Uses AIME 2026 math competition problems as evaluation prompts.

## Quick Start

```bash
./run_benchmark.sh --url http://192.168.0.109:1234/v1 --key YOUR_API_KEY
```

Run a single problem by position (1-based):

```bash
./run_benchmark.sh --url http://localhost:8000/v1 --key YOUR_KEY --id 5
```

Run a range of problems:

```bash
./run_benchmark.sh --url http://localhost:8000/v1 --key YOUR_KEY --id '1-3'
```

Run specific problems:

```bash
./run_benchmark.sh --url http://localhost:8000/v1 --key YOUR_KEY --id 6 8 10
```

## Options

| Flag        | Description                                      |
|-------------|--------------------------------------------------|
| `--url`     | Base URL of the OpenAI-compatible API server     |
| `--key`     | API key for authentication                       |
| `--id`      | Problem position(s) in the JSONL file (1-based). Supports single number, range (`1-3`), or comma-separated list (`6,8,10`). Omit to run all 30 problems. |
| `--verbose` | Print the model's thinking process and full answer |

## Metrics

The benchmark provides a detailed performance summary:

### Latency & Throughput
- **TTFT** (Time to First Token) – Latency until the first content token arrives.
- **Thinking-Ph.** – Duration of the reasoning/thinking phase.
- **Answer-Ph.** – Duration of the visible answer generation phase.
- **Latency** – Total wall-clock time for the complete response.
- **TPS** (Tokens Per Second) – Throughput based on actual completion token count from the server's usage report.

### Accuracy & Reasoning
- **Answer Accuracy** – Extracted answer compared against the known correct value.
- **Think-Ratio** – Percentage of total latency spent in the reasoning phase.

### Token Statistics
- **Reason. Toks** – Number of reasoning/thinking tokens.
- **Answer Toks** – Number of visible answer tokens.
- **Total Tokens** – Sum of reasoning and answer tokens.

## Example Output

```text
===================================================================================================================
  ADVANCED STATISTICS & PERFORMANCE SUMMARY
===================================================================================================================
  ID             Status      Exp   Rec      TTFT  Think-Time    Ans-Time     Latency   Tok-R   Tok-A    TPS
  ---------------------------------------------------------------------------------------------------------------
  2026-I-1       CORRECT      42    42     3.17s   2m 29.05s   2m 22.32s   4m 54.55s    1776    1584   11.5

  ---------------------------------------------------------------------------------------------------------------
  Total:  1 tasks | 1 successful | 0 failed
  Correct: 1/1 (100.0%)

  TTFT         - Min: 3.17s     | Max: 3.17s     | Avg: 3.17s
  Thinking-Ph. - Min: 2m 29.05s | Max: 2m 29.05s | Avg: 2m 29.05s
  Answer-Ph.   - Min: 2m 22.32s | Max: 2m 22.32s | Avg: 2m 22.32s
  Full Latency - Min: 4m 54.55s | Max: 4m 54.55s | Avg: 4m 54.55s
  Think-Ratio  - Min: 50.6%     | Max: 50.6%     | Avg: 50.6%

  Reason. Toks - Min: 1776      | Max: 1776      | Avg: 1776
  Answer Toks  - Min: 1584      | Max: 1584      | Avg: 1584
  Total Tokens - Min: 3360      | Max: 3360      | Avg: 3360
  Total TPS    - Min: 11.5      | Max: 11.5      | Avg: 11.5
===================================================================================================================
```

## Prompt Data

The AIME 2026 problem set (`prompts/aime_2026.jsonl`) is a copy of the prompts from the [MTPLX](https://github.com/youssofal/MTPLX) benchmark suite:

> **Source:** [youssofal/MTPLX – `mtplx/benchmarks/prompts/aime_2026.jsonl`](https://github.com/youssofal/MTPLX/blob/main/mtplx/benchmarks/prompts/aime_2026.jsonl)

The file contains 30 problems (15 from AIME I, 15 from AIME II), each with an `id`, problem statement, and expected integer answer.

## License

This project is licensed under the GNU Lesser General Public License v2.1. See [LICENSE](LICENSE) for details.
