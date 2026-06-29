import json
import time
import asyncio
import argparse
import re
from openai import AsyncOpenAI

# AIME System-Prompt and User-Prompt Suffix (hard-coded)
SYSTEM_PROMPT = (
    "You are solving AIME problems. The runner scores only visible content "
    "after </think>; it never scores hidden reasoning. Close the reasoning "
    "block with  and present your solution in visible content. Do "
    "not put candidate_answer or a boxed final answer inside hidden "
    "reasoning. End visible content with exactly two lines: "
    "candidate_answer=N and \\boxed{N}, where N is the requested integer. "
    "Do not repeat these instructions."
)

USER_PROMPT_SUFFIX = (
    "Output your reasoning clearly. If the problem asks for an integer "
    "answer between 000 and 999, make sure to provide it in the format "
    "candidate_answer=N and \\boxed{N} where N is your final integer "
    "answer."
)


def parse_answer_from_boxed(answer_text):
    """Extracts the value from \\boxed{...} from the answer."""
    match = re.search(r'\\boxed\{([^}]+)\}', answer_text)
    if match:
        return match.group(1).strip()
    return None


def extract_answer(answer_text):
    """Extracts the final answer from the LLM response.
    
    Tries several strategies:
    1. \\boxed{...} - the official AIME formatting
    2. candidate_answer=N - explicit answer line
    3. Last number in text (fallback)
    """
    if not answer_text:
        return None

    # Strategie 1: \\boxed{...}
    match = re.search(r'\\boxed\{([^}]+)\}', answer_text)
    if match:
        val = match.group(1).strip()
        # If multiple digits, take the last one (AIME answers with 3 digits)
        return val

    # Strategie 2: candidate_answer=N
    match = re.search(r'candidate_answer\s*=\s*(\d+)', answer_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Strategie 3: letzte Zahl im gesamten Text
    numbers = re.findall(r'\b(\d{1,4})\b', answer_text)
    if numbers:
        return numbers[-1].strip()

    return None


def compare_answers(extracted, expected):
    """Compares extracted with expected answer.
    
    Returns:
        tuple: (bool matched, str status)
    """
    if extracted is None:
        return False, "NO ANSWER FOUND"
    
    # Erwartete Antwort kann int oder str sein
    try:
        expected_str = str(int(expected))
    except (ValueError, TypeError):
        expected_str = str(expected).strip()
    
    extracted_str = str(extracted).strip()
    
    # AIME answers are 000-999
    if extracted_str == expected_str:
        return True, "CORRECT"
    else:
        return False, f"WRONG (expected={expected_str}, received={extracted_str})"


def format_time(seconds):
    """Converts seconds to mm:ss format."""
    if seconds < 0:
        return "00:00"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes:02d}:{secs:05.2f}"


def print_statistics(results):
    """Outputs a statistics table for all performed benchmarks."""
    if not results:
        print("\n[STATS] No results found.")
        return

    correct = 0
    total = len(results)
    successful = [r for r in results if r.get("success")]
    failed = total - len(successful)

    # Timing statistics
    ttfts = [r["ttft"] for r in successful]
    latencies = [r["total_latency"] for r in successful]
    tps_values = [r["tps"] for r in successful if r.get("tps", 0) > 0]

    print("\n" + "="*80)
    print("="*80)
    print("  STATISTICS & RESULT SUMMARY")
    print("="*80)

    # --- Ergebnis-Tabelle ---
    print(f"\n  {'ID':<16} {'Status':<22} {'Expected':>8} {'Received':>8} {'TTFT':>10} {'Latency':>12} {'TPS':>8}")
    print("  " + "-"*78)

    for r in results:
        rid = r.get("id", "?")
        if not r.get("success"):
            print(f"  {rid:<16} {'FAILED':<22} {'':>8} {'':>8} {'':>10} {'':>12} {'':>8}")
            continue

        extracted = extract_answer(r.get("answer", ""))
        matched, status = compare_answers(extracted, r.get("expected_answer", "N/A"))

        status_str = status
        if matched:
            correct += 1

        ttft_str = format_time(r['ttft'])
        lat_str = format_time(r['total_latency'])
        tps_str = f"{r['tps']:.2f}" if r.get("tps", 0) > 0 else "N/A"

        print(f"  {rid:<16} {status_str:<22} {str(r.get('expected_answer','')):>8} {str(extracted or '???'):>8} {ttft_str:>10} {lat_str:>12} {tps_str:>8}")

    # --- Summary ---
    print("\n  " + "-"*78)
    print(f"  Total:  {total} tasks | {len(successful)} successful | {failed} failed")
    print(f"  Correct: {correct}/{len(successful)} ({len(successful)>0 and correct/len(successful)*100:.1f}%)")
    print(f"  Wrong:  {len(successful)-correct}/{len(successful)}")
    print(f"  No answer: {sum(1 for r in successful if extract_answer(r.get('answer','')) is None)}")
    print()

    if ttfts:
        print(f"  TTFT  - Min: {format_time(min(ttfts))} | Max: {format_time(max(ttfts))} | Avg: {format_time(sum(ttfts)/len(ttfts))}")
    if latencies:
        print(f"  Latency - Min: {format_time(min(latencies))} | Max: {format_time(max(latencies))} | Avg: {format_time(sum(latencies)/len(latencies))}")
    if tps_values:
        print(f"  TPS   - Min: {min(tps_values):.2f} | Max: {max(tps_values):.2f} | Avg: {sum(tps_values)/len(tps_values):.2f}")
    print("="*80)
    print("="*80)

# Path to the AIME prompts file
PROMPTS_FILE = "prompts/aime_2026.jsonl"

# DEBUG: Set to True to test with "Hello" as prompt
DEBUG_HELLO = False

# VERBOSE: Set to True to output thinking process and full response
VERBOSE = False


def load_prompts(filepath):
    """Loads all prompts from the JSONL file."""
    prompts = []
    with open(filepath, "r") as f:
        for line in f:
            prompts.append(json.loads(line))
    return prompts


def parse_id_selection(id_arg):
    """Parses the --id argument option and returns a list of 1-based indices.

    Options:
      None        → all entries (empty list = all)
      int N       → the N-th entry (1-based)
      str "N-M"   → entries from N to M (1-based, inclusive)
      str "N,P,Q" → multiple individual entries (comma-separated, e.g., "6,8,10")

    The indices refer to the order in the JSONL file,
    not to the IDs in the JSON data.
    """
    if id_arg is None or id_arg == "":
        # None means: all

    id_arg = str(id_arg).strip()

    # Check comma-separated IDs: "6,8,10"
    if ',' in id_arg:
        parts = id_arg.split(',')
        result = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Also allow sub-ranges in comma-separated list: "1-3,5,7-9"
            sub_match = re.match(r'^(\d+)-(\d+)$', part)
            if sub_match:
                start = int(sub_match.group(1))
                end = int(sub_match.group(2))
                result.extend(range(start, end + 1))
            else:
                try:
                    result.append(int(part))
                except ValueError:
                    print(f"[WARN] Invalid ID '{part}' – ignoring.")
        return result if result else None

    # Check range: "N-M"
    range_match = re.match(r'^(\d+)-(\d+)$', id_arg)
    if range_match:
        start = int(range_match.group(1))
        end = int(range_match.group(2))
        return list(range(start, end + 1))

    # Einzelne Zahl
    try:
        n = int(id_arg)
        return [n]
    except ValueError:
        print(f"[WARN] Invalid ID '{id_arg}' – ignoring.")
    return None  # all


async def measure_request_streaming(client, prompt, request_id):
    """Measures streaming response and separates reasoning_content (Thinking) from content (Answer)."""
    start_time = time.perf_counter()

    try:
        response = await client.chat.completions.create(
            model="facebook/opt-125m",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt + USER_PROMPT_SUFFIX}
            ],
            max_tokens=32768,
            stream=True,
            stream_options={"include_usage": True}
        )

        thinking_text = ""
        answer_text = ""
        thinking_token_count = 0
        answer_token_count = 0
        ttft_answer = None  # TTFT erst wenn content kommt (nicht reasoning_content)
        chunk_count = 0
        first_token_time = None
        completion_tokens = None  # Echte Token-Anzahl aus usage (stream_options)

        async for chunk in response:
            chunk_count += 1
            if first_token_time is None:
                first_token_time = time.perf_counter()

            # Rejected response: no choices
            if not chunk.choices or len(chunk.choices) == 0:
                continue

            choice = chunk.choices[0]

            # Standard OpenAI Format: content = final answer
            content = None
            if hasattr(choice, 'delta') and choice.delta:
                content = choice.delta.content

            # vLLM: reasoning_content = thought process (Thinking)
            reasoning_content = None
            if hasattr(choice, 'delta') and choice.delta:
                reasoning_content = getattr(choice.delta, 'reasoning_content', None)

            # collect reasoning_content (Thinking process)
            if reasoning_content:
                thinking_text += reasoning_content
                thinking_token_count += 1

            # collect content (final answer)
            if content:
                if ttft_answer is None:
                    ttft_answer = time.perf_counter() - start_time
                answer_text += content
                answer_token_count += 1

            # vLLM sometimes directly on choice
            if content is None and hasattr(choice, 'text'):
                answer_text += choice.text
                answer_token_count += 1

            # Real token count from usage (stream_options={"include_usage": True})
            if hasattr(chunk, 'usage') and chunk.usage:
                completion_tokens = chunk.usage.completion_tokens if hasattr(chunk.usage, 'completion_tokens') else None
                # fallback: total_tokens - prompt_tokens
                if completion_tokens is None and hasattr(chunk.usage, 'total_tokens') and hasattr(chunk.usage, 'prompt_tokens'):
                    completion_tokens = chunk.usage.total_tokens - chunk.usage.prompt_tokens

        end_time = time.perf_counter()

        # TTFT: time until first content delta (not reasoning)
        ttft = ttft_answer if ttft_answer else (first_token_time - start_time)
        total_latency = end_time - start_time

        # TPS based on actual tokens from usage (not chunks!)
        if completion_tokens is not None and completion_tokens > 0:
            tps = completion_tokens / (end_time - ttft) if (end_time - ttft) > 0 else 0
        else:
            # Fallback: Chunks as rough estimate (inaccurate!)
            tps = answer_token_count / (end_time - ttft) if (end_time - ttft) > 0 else 0

        print(f"  [INFO] Streaming: {chunk_count} Chunks, Thinking={thinking_token_count} Tokens, Answer={answer_token_count} Chars, CompletionTokens={completion_tokens}, TPS={tps:.2f}")

        return {
            "id": request_id,
            "ttft": ttft,
            "total_latency": total_latency,
            "tps": tps,
            "tokens": completion_tokens if completion_tokens is not None else answer_token_count,
            "success": True,
            "thinking": thinking_text,
            "answer": answer_text,
            "streaming": True
        }
    except Exception as e:
        print(f"  [DEBUG] Streaming request failed: {e}")
        return {"id": request_id, "success": False, "streaming": True}


async def measure_request_non_streaming(client, prompt, request_id):
        # Non-Streaming fallback: gets complete response at once.
    start_time = time.perf_counter()

    try:
        response = await client.chat.completions.create(
            model="facebook/opt-125m",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            stream=False
        )

        end_time = time.perf_counter()

        full_text = response.choices[0].message.content or ""
        total_tokens = response.usage.total_tokens if response.usage else 0

        ttft = end_time - start_time  # No TTFT without streaming

        print(f"  [DEBUG] Non-Streaming: response length={len(full_text)} chars, tokens={total_tokens}")

        return {
            "id": request_id,
            "ttft": ttft,
            "total_latency": end_time - start_time,
            "tps": 0,
            "tokens": total_tokens,
            "success": True,
            "answer": full_text,
            "streaming": False
        }
    except Exception as e:
        print(f"  [DEBUG] Non-streaming request failed: {e}")
        return {"id": request_id, "success": False, "streaming": False}


async def measure_request(client, prompt, request_id):
    """Tries streaming first, fallback to non-streaming."""
    # 1. Try streaming
    result = await measure_request_streaming(client, prompt, request_id)

    # 2. If streaming provided no content, use non-streaming
    if result.get("success") and (not result.get("answer") or result.get("tokens", 0) == 0):
        print(f"  [INFO] Streaming provided no content deltas, trying non-streaming...")
        result = await measure_request_non_streaming(client, prompt, request_id)

    return result


async def run_benchmark(url, api_key, id_selection, verbose=False):
    client = AsyncOpenAI(base_url=url, api_key=api_key)

    # Prompts load
    prompts = load_prompts(PROMPTS_FILE)
    print(f"Loaded {len(prompts)} prompts from {PROMPTS_FILE}")

    # Parse selection: None = all, [N] = single entry, [N, ..., M] = range
    indices = parse_id_selection(id_selection)

    if indices is None:
        # Iterate through all entries
        selected = prompts
        print(f"[INFO] No ID specified – running benchmark for all {len(selected)} prompts.")
    else:
        # Filter by position in JSONL (1-based)
        selected = []
        for idx in indices:
            pos = idx - 1  # 1-based → 0-based
            if 0 <= pos < len(prompts):
                selected.append(prompts[pos])
            else:
                print(f"[WARN] Position {idx} out of range (1-{len(prompts)}) – skipped.")
        if not selected:
            print(f"No valid prompts for the specified ID(s).")
            return
        print(f"[INFO] Running benchmark for {len(selected)} selected prompts.")

    results = []
    for i, prompt_data in enumerate(selected):
        prompt_index = indices[i] if indices else (i + 1)

        # DEBUG: "Hello" as test prompt
        if DEBUG_HELLO:
            problem = "According to Douglas Adams' The Hitchhiker's Guide to the Galaxy, what is the ultimate answer to the ultimate question of life, the universe, and everything? Provide just the number."
            expected_answer = "42"
        else:
            problem = prompt_data["problem"]
            expected_answer = prompt_data.get("answer", "N/A")

        print(f"\n=== AIME Prompt ID: {prompt_data['id']} (Position {prompt_index}) ===")
        print(f"Problem: {problem[:100]}...")  # First 100 characters
        print(f"Expected answer: {expected_answer}")
        print("="*50)

        # Benchmark execution
        print(f"\nRunning benchmark for position {prompt_index}...")
        result = await measure_request(client, problem, prompt_data["id"])

        results.append({
            **result,
            "expected_answer": expected_answer
        })

        # Detail output (only in VERBOSE mode: Thinking + full response)
        if verbose and result["success"] and result.get("streaming") and result.get("thinking"):
            print(f"\n--- Thinking Process ---")
            print(result["thinking"][:500] + "..." if len(result["thinking"]) > 500 else result["thinking"])
            print(f"\n--- Full Response ---")
            print(result["answer"][:1000] + "..." if len(result.get("answer", "")) > 1000 else result.get("answer", ""))

    # Statistics for all results
    print_statistics(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str, required=True, help="URL of the vLLM server (e.g. http://192.168.0.109:1234/v1)")
    parser.add_argument("--key", type=str, required=True, help="API Key")
    parser.add_argument("--id", type=str, default=None, help="Position in JSONL (1-based): single number e.g. '5' or range e.g. '3-7'. If omitted: all prompts.")
    parser.add_argument("--verbose", action="store_true", default=VERBOSE, help="Outputs thinking process and full response")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.url, args.key, args.id, verbose=args.verbose))
