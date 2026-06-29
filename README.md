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

The benchmark reports:

- **TTFT** (Time to First Token) – latency until the first content token arrives
- **Latency** – total wall-clock time for the complete response
- **TPS** (Tokens Per Second) – throughput based on actual completion token count from the server's usage report
- **Answer Accuracy** – extracted answer compared against the known correct value

## Prompt Data

The AIME 2026 problem set (`prompts/aime_2026.jsonl`) is a copy of the prompts from the [MTPLX](https://github.com/youssofal/MTPLX) benchmark suite:

> **Source:** [youssofal/MTPLX – `mtplx/benchmarks/prompts/aime_2026.jsonl`](https://github.com/youssofal/MTPLX/blob/main/mtplx/benchmarks/prompts/aime_2026.jsonl)

The file contains 30 problems (15 from AIME I, 15 from AIME II), each with an `id`, problem statement, and expected integer answer.

## License

This project is licensed under the GNU Lesser General Public License v2.1. See [LICENSE](LICENSE) for details.
