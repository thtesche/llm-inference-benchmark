#!/usr/bin/env bash
# Run one 100k-context and one 50k-context SWE benchmark sequentially.
# Sequential on purpose: parallel requests would distort throughput numbers.
set -u
cd "$(dirname "$0")"
source venv/bin/activate

URL="http://192.168.0.109:8080/v1"
KEY="sk-strata-y22lrZ9QbtBISja5sRZEF2eIwn07ORc_"

echo "=== [1/2] 100k token context ==="
SWE_PROMPTS_FILE=prompts/swe_context_large.jsonl python3 api_benchmark.py \
  --url "$URL" --key "$KEY" --benchmark swe --id 1 \
  --server-type "strata-qwen" \
  --notes "100k token context (completion-token counting fixed)"

echo "=== [2/2] 50k token context ==="
SWE_PROMPTS_FILE=prompts/swe_context_medium.jsonl python3 api_benchmark.py \
  --url "$URL" --key "$KEY" --benchmark swe --id 1 \
  --server-type "strata-qwen" \
  --notes "50k token context (completion-token counting fixed)"

echo "=== done ==="
