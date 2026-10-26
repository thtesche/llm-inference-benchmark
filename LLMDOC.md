# LLM Benchmark Suite – Command Reference

This document describes the command-line interface for the LLM Benchmark Suite. It is designed to be parsed by LLM agents and external tools.

## Overview

The benchmark measures LLM inference performance using AIME 2026 math problems. It tracks:
- **Latency**: TTFT, thinking time, answer time
- **Throughput**: Tokens per second (TPS)
- **Accuracy**: Correct answers vs expected
- **Metadata**: Server type, model name, notes

All runs are automatically saved to SQLite database and JSON backups.

---

## Primary Command: Run Benchmark

### Syntax
```bash
./run_benchmark.sh --url <url> --key <key> [--id <ids>] [--server-type <type>] [--notes <text>]
```

### Required Arguments

| Flag | Type | Description |
|------|------|-------------|
| `--url` | string | Base URL of OpenAI-compatible API (e.g., `http://localhost:1234/v1`) |
| `--key` | string | API key for authentication |

### Optional Arguments

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--id` | string | all | Problem IDs to run. Formats: `5` (single), `1-3` (range), `1,5,10` (list) |
| `--server-type` | string | prompted | Server implementation (e.g., `llama.cpp`, `vllm`, `strata`). If omitted, user is prompted; last used value suggested. |
| `--notes` | string | empty | Annotations for this run (max 500 chars). If omitted, user is prompted. |
| `--verbose` | flag | false | Print full thinking and answer text |

### Output

**Terminal:**
- Live streaming stats (TTFT, thinking time, answer time)
- Statistics table with accuracy and per-problem results
- Summary after completion

**Files:**
- `runs.db` – SQLite database (created on first run)
- `benchmark_data/run_YYYYMMDD_HHMMSS.json` – Complete JSON backup of run

**Exit Codes:**
- `0` – Success
- `1` – Invalid problem ID range
- `2` – API unreachable / network error
- `3` – API authentication failed (invalid key)
- `4` – Database error

### Example Usage

```bash
# Run all 30 problems with server type and notes
./run_benchmark.sh \
  --url http://localhost:1234/v1 \
  --key sk-abc123 \
  --server-type llama.cpp \
  --notes "Q5 quantization, 7B model"

# Run problems 1-5 with auto-prompted server type
./run_benchmark.sh \
  --url http://localhost:1234/v1 \
  --key sk-abc123 \
  --id 1-5

# Run specific problems
./run_benchmark.sh \
  --url http://localhost:1234/v1 \
  --key sk-abc123 \
  --id 1,5,10
```

---

## Secondary Command: List Runs

### Syntax
```bash
python compare.py --list [--limit N] [--server-type TYPE] [--json]
```

### Arguments

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--limit` | int | 10 | Number of runs to show (most recent first) |
| `--server-type` | string | none | Filter runs by server type |
| `--json` | flag | false | Output as JSON instead of table |

### Output (Default: Table)
```
  ID    Date                 Server        Model              Accuracy   TPS     Correct/Total   Notes
  ====================================================================================================
  5     2026-10-26T14:32:00  llama.cpp     mistral-7b         93.3%      11.5    28/30           Q5 quant
  4     2026-10-26T10:15:00  vllm          mistral-7b         90.0%      12.1    27/30           Baseline
```

### Output (JSON)
```json
[
  {
    "id": 5,
    "timestamp": "2026-10-26T14:32:00Z",
    "server_type": "llama.cpp",
    "model": "mistral-7b",
    "accuracy": 0.933,
    "avg_tps": 11.5,
    "correct": 28,
    "total": 30,
    "notes": "Q5 quant"
  }
]
```

### Example Usage

```bash
# List last 10 runs
python compare.py --list

# List last 5 runs for a specific server
python compare.py --list --limit 5 --server-type llama.cpp

# Get JSON output for parsing
python compare.py --list --limit 3 --json
```

---

## Tertiary Command: Compare Runs

### Syntax
```bash
python compare.py --run-1 <id> --run-2 <id> [--json]
```

### Arguments

| Flag | Type | Description |
|------|------|-------------|
| `--run-1` | int | ID of first run (from `--list`) |
| `--run-2` | int | ID of second run (from `--list`) |
| `--json` | flag | Output as JSON instead of table |

### Output (Default: Table)
Shows side-by-side metrics and per-problem differences:
- Accuracy delta (+ = improvement)
- TTFT delta (- = improvement)
- TPS delta (+ = improvement)
- Problem-by-problem comparison with ✓/✗ and deltas

### Output (JSON)
```json
{
  "run_1": {
    "id": 4,
    "accuracy": 0.9,
    "avg_ttft": 3.2,
    "avg_tps": 12.1
  },
  "run_2": {
    "id": 5,
    "accuracy": 0.933,
    "avg_ttft": 3.17,
    "avg_tps": 11.5
  },
  "differences": {
    "accuracy_delta": 0.033,
    "ttft_delta": -0.03,
    "tps_delta": -0.6
  },
  "detailed_results": [
    {
      "position": 1,
      "problem_id": "2026-I-1",
      "run_1": {"correct": true, "ttft": 3.2, "tps": 11.8},
      "run_2": {"correct": true, "ttft": 3.17, "tps": 11.9}
    }
  ]
}
```

### Example Usage

```bash
# Compare runs 4 and 5
python compare.py --run-1 4 --run-2 5

# Get JSON for programmatic processing
python compare.py --run-1 4 --run-2 5 --json | python -m json.tool
```

---

## Web UI

### Start Web Server
```bash
python app.py
```

Opens `http://localhost:5000` in browser.

**Pages:**
- `/` – Recent runs (table, quick stats)
- `/run/<id>` – Full details for run ID
- `/compare` – Interactive run comparison UI
- `/trends` – Charts: accuracy/TPS/TTFT over time

### REST API

All web data is available via JSON API:

```bash
# List recent runs
curl http://localhost:5000/api/runs?limit=10

# Get run details
curl http://localhost:5000/api/runs/5

# Compare two runs
curl http://localhost:5000/api/compare/4/5

# Download JSON backup
curl http://localhost:5000/api/backup/5 > backup.json
```

---

## Database Access

Direct SQLite access is possible but not recommended for external tools. Use the CLI instead.

```bash
# Query last 5 runs
sqlite3 runs.db "SELECT id, timestamp, server_type, accuracy FROM runs ORDER BY id DESC LIMIT 5;"

# Query results for run 5
sqlite3 runs.db "SELECT problem_id, correct, tps FROM results WHERE run_id=5;"
```

---

## Typical LLM Workflow

1. **Check Server Status:**
   ```bash
   curl http://localhost:1234/v1/models
   ```

2. **Run Benchmark:**
   ```bash
   ./run_benchmark.sh \
     --url http://localhost:1234/v1 \
     --key "sk-xxx" \
     --server-type "llama.cpp" \
     --notes "After optimization pass"
   ```

3. **Get Latest Results:**
   ```bash
   python compare.py --list --limit 1 --json
   ```

4. **Compare with Previous:**
   ```bash
   python compare.py --run-1 <prev_id> --run-2 <new_id> --json
   ```

5. **Report Findings:**
   Parse JSON outputs and format for user summary.

---

## Error Handling

**Server Unreachable (Exit Code 2):**
- Retry after 5 seconds
- Check if API process is running

**Authentication Failed (Exit Code 3):**
- Verify API key is correct
- Check API endpoint accepts key in Authorization header

**Invalid Problem ID (Exit Code 1):**
- Problem IDs must be 1-30
- Verify range format: `1-3` or list: `1,5,10`

**Database Error (Exit Code 4):**
- Try deleting `runs.db` and rerunning (loses history)
- Check disk space

---

## JSON Backup Format

Each run is automatically saved as `benchmark_data/run_YYYYMMDD_HHMMSS.json`:

```json
{
  "run_id": 5,
  "timestamp": "2026-10-26T14:32:00Z",
  "server_type": "llama.cpp",
  "model": "mistral-7b",
  "api_url": "http://localhost:1234/v1",
  "notes": "Q5 quantization",
  "aggregate": {
    "total": 30,
    "correct": 28,
    "accuracy": 0.933,
    "avg_ttft": 3.17,
    "avg_tps": 11.5
  },
  "results": [
    {
      "problem_id": "2026-I-1",
      "position": 1,
      "expected": "42",
      "extracted": "42",
      "correct": true,
      "ttft": 3.17,
      "reasoning_time": 149.05,
      "answer_time": 142.32,
      "total_latency": 294.55,
      "reasoning_tokens": 1776,
      "answer_tokens": 1584,
      "tps": 11.5
    }
  ]
}
```

---

## Troubleshooting

**Q: How do I get the run ID for the latest benchmark?**
```bash
python compare.py --list --limit 1 --json | python -c "import sys, json; print(json.load(sys.stdin)[0]['id'])"
```

**Q: How do I extract accuracy for programmatic use?**
```bash
python compare.py --list --limit 1 --json | python -c "import sys, json; print(json.load(sys.stdin)[0]['accuracy'])"
```

**Q: How do I see all historical data?**
```bash
python compare.py --list --limit 100 --json
```

**Q: Can I use this with a remote API?**
Yes, pass the full URL: `--url https://api.example.com/v1`

**Q: What's the expected runtime for all 30 problems?**
Depends on model and server. Expect 60–180 minutes for typical setups. Use `--id` to test with fewer problems first.
