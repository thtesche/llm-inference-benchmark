import json
import time
import asyncio
import argparse
import re
from openai import AsyncOpenAI

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
    """Extracts the final answer from the LLM response."""
    if not answer_text:
        return None

    # Strategy 1: \\boxed{...}
    match = re.search(r'\\boxed\{([^}]+)\}', answer_text)
    if match:
        return match.group(1).strip()

    # Strategy 2: candidate_answer=N
    match = re.search(r'candidate_answer\s*=\s*(\d+)', answer_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Strategy 3: last number in text
    numbers = re.findall(r'\b(\d{1,4})\b', answer_text)
    if numbers:
        return numbers[-1].strip()

    return None


def compare_answers(extracted, expected):
    """Compares the extracted answer with the expected answer."""
    if extracted is None:
        return False, "NO ANSWER FOUND"
    
    try:
        expected_str = str(int(expected))
    except (ValueError, TypeError):
        expected_str = str(expected).strip()
    
    extracted_str = str(extracted).strip()
    
    if extracted_str == expected_str:
        return True, "CORRECT"
    else:
        return False, f"WRONG (expected={expected_str}, received={extracted_str})"


def format_time(seconds):
    """Formats seconds into a human-readable duration string (e.g., '4.23s' or '1m 14.16s')."""
    if seconds is None or seconds < 0:
        return "0.00s"
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:05.2f}s"


def print_statistics(results):
    """Outputs an advanced statistics table for all performed benchmarks."""
    if not results:
        print("\n[STATS] No results found.")
        return

    correct = 0
    total = len(results)
    successful = [r for r in results if r.get("success")]
    failed = total - len(successful)

    # Aggregate metrics
    ttfts = [r["ttft"] for r in successful]
    latencies = [r["total_latency"] for r in successful]
    tps_values = [r["tps"] for r in successful if r.get("tps", 0) > 0]
    think_times = [r["reasoning_time"] for r in successful]
    answer_times = [r["answer_time"] for r in successful]
    ratios = [r["thinking_ratio"] for r in successful]

    print("\n" + "="*95)
    print("="*95)
    print("  ADVANCED STATISTICS & PERFORMANCE SUMMARY")
    print("="*95)

    # --- Result Table ---
    print(f"\n  {'ID':<14} {'Status':<10} {'Exp':>5} {'Rec':>5} {'TTFT':>10} {'Think-Time':>12} {'Answer-Time':>13} {'Latency':>12} {'TPS':>7}")
    print("  " + "-"*91)

    for r in results:
        rid = r.get("id", "?")
        if not r.get("success"):
            print(f"  {rid:<14} {'FAILED':<10} {'':>5} {'':>5} {'':>10} {'':>12} {'':>13} {'':>12} {'':>7}")
            continue

        extracted = extract_answer(r.get("answer", ""))
        matched, status = compare_answers(extracted, r.get("expected_answer", "N/A"))

        if matched:
            correct += 1

        print(f"  {rid:<14} {status[:10]:<10} {str(r.get('expected_answer','')):>5} {str(extracted or '???')[:5]:>5} "
              f"{format_time(r['ttft']):>10} {format_time(r['reasoning_time']):>12} {format_time(r['answer_time']):>13} "
              f"{format_time(r['total_latency']):>12} {r['tps']:>7.1f}")

    # --- Summary ---
    print("\n  " + "-"*91)
    print(f"  Total:  {total} tasks | {len(successful)} successful | {failed} failed")
    print(f"  Correct: {correct}/{len(successful)} ({len(successful)>0 and correct/len(successful)*100:.1f}%)")
    print()

    if ttfts:
        print(f"  TTFT         - Min: {format_time(min(ttfts)):<9} | Max: {format_time(max(ttfts)):<9} | Avg: {format_time(sum(ttfts)/len(ttfts))}")
    if think_times:
        print(f"  Thinking-Ph. - Min: {format_time(min(think_times)):<9} | Max: {format_time(max(think_times)):<9} | Avg: {format_time(sum(think_times)/len(think_times))}")
    if answer_times:
        print(f"  Answer-Ph.   - Min: {format_time(min(answer_times)):<9} | Max: {format_time(max(answer_times)):<9} | Avg: {format_time(sum(answer_times)/len(answer_times))}")
    if latencies:
        print(f"  Full Latency - Min: {format_time(min(latencies)):<9} | Max: {format_time(max(latencies)):<9} | Avg: {format_time(sum(latencies)/len(latencies))}")
    if ratios:
        print(f"  Think-Ratio  - Min: {min(ratios):.1f}%     | Max: {max(ratios):.1f}%     | Avg: {sum(ratios)/len(ratios):.1f}% (Time share of thinking phase)")
    if tps_values:
        print(f"  Total TPS    - Min: {min(tps_values):.1f}       | Max: {max(tps_values):.1f}       | Avg: {sum(tps_values)/len(tps_values):.1f}")
    print("="*95)


PROMPTS_FILE = "prompts/aime_2026.jsonl"
DEBUG_HELLO = False


def load_prompts(filepath):
    """Loads all prompt entries from the provided JSONL file."""
    prompts = []
    with open(filepath, "r") as f:
        for line in f:
            prompts.append(json.loads(line))
    return prompts


def parse_id_selection(id_arg):
    """Parses the ID selection argument supporting single numbers, ranges, or lists."""
    if id_arg is None or id_arg == "":
        return None
    id_arg = str(id_arg).strip()

    if ',' in id_arg:
        parts = id_arg.split(',')
        result = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
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

    range_match = re.match(r'^(\d+)-(\d+)$', id_arg)
    if range_match:
        start = int(range_match.group(1))
        end = int(range_match.group(2))
        return list(range(start, end + 1))

    try:
        return [int(id_arg)]
    except ValueError:
        print(f"[WARN] Invalid ID '{id_arg}' – ignoring.")
    return None


async def measure_request_streaming(client, model_name, prompt, request_id):
    """Measures streaming response and separates thinking from answering performance."""
    start_time = time.perf_counter()

    try:
        response = await client.chat.completions.create(
            model=model_name,
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
        
        first_token_time = None          # Time of the very first token (TTFT relevant)
        first_answer_token_time = None   # Time when the model switches to the final content answer
        
        prompt_tokens = 0
        completion_tokens = 0

        async for chunk in response:
            # Bugfix A: Extract usage data first, as this chunk at the end contains NO choices array!
            if hasattr(chunk, 'usage') and chunk.usage:
                prompt_tokens = getattr(chunk.usage, 'prompt_tokens', 0)
                if hasattr(chunk.usage, 'completion_tokens'):
                    completion_tokens = chunk.usage.completion_tokens
                else:
                    completion_tokens = getattr(chunk.usage, 'total_tokens', 0) - prompt_tokens

            if not chunk.choices or len(chunk.choices) == 0:
                continue

            if first_token_time is None:
                first_token_time = time.perf_counter()

            choice = chunk.choices[0]
            
            # Extract reasoning content (vLLM / Ollama standard)
            reasoning_content = None
            if hasattr(choice, 'delta') and choice.delta:
                reasoning_content = getattr(choice.delta, 'reasoning_content', None)

            # Extract standard response content
            content = None
            if hasattr(choice, 'delta') and choice.delta:
                content = choice.delta.content

            if reasoning_content:
                thinking_text += reasoning_content

            if content:
                if first_answer_token_time is None:
                    # Captures the exact moment the thinking phase ends and final generation begins
                    first_answer_token_time = time.perf_counter()
                answer_text += content

            if content is None and hasattr(choice, 'text'):
                if first_answer_token_time is None:
                    first_answer_token_time = time.perf_counter()
                answer_text += choice.text

        end_time = time.perf_counter()

        # --- Detailed Timing Metrics ---
        ttft = (first_token_time - start_time) if first_token_time else (end_time - start_time)
        total_latency = end_time - start_time
        
        # Fallback if no explicit phase split was detected (e.g., standard non-reasoning model)
        if first_answer_token_time and first_token_time:
            reasoning_duration = first_answer_token_time - first_token_time
            answer_duration = end_time - first_answer_token_time
        else:
            reasoning_duration = 0
            answer_duration = end_time - first_token_time if first_token_time else 0

        generation_time = end_time - first_token_time if first_token_time else 0

        # Bugfix B: Calculate TPS using the actual generation time elapsed
        if completion_tokens > 0 and generation_time > 0:
            tps = completion_tokens / generation_time
        else:
            # Fallback based on character length heuristics if API usage fails
            est_tokens = (len(thinking_text) + len(answer_text)) // 4
            tps = est_tokens / generation_time if generation_time > 0 else 0

        thinking_ratio = (reasoning_duration / total_latency * 100) if total_latency > 0 else 0

        return {
            "id": request_id,
            "ttft": ttft,
            "total_latency": total_latency,
            "reasoning_time": reasoning_duration,
            "answer_time": answer_duration,
            "thinking_ratio": thinking_ratio,
            "tps": tps,
            "tokens": completion_tokens,
            "success": True,
            "thinking": thinking_text,
            "answer": answer_text,
            "streaming": True
        }
    except Exception as e:
        print(f"  [DEBUG] Streaming request failed: {e}")
        return {"id": request_id, "success": False, "streaming": True}


async def measure_request_non_streaming(client, model_name, prompt, request_id):
    """Fallback method using standard non-streaming requests if streaming drops out."""
    start_time = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            stream=False
        )
        end_time = time.perf_counter()
        full_text = response.choices[0].message.content or ""
        total_tokens = response.usage.completion_tokens if response.usage else 0

        return {
            "id": request_id,
            "ttft": end_time - start_time,
            "total_latency": end_time - start_time,
            "reasoning_time": 0,
            "answer_time": end_time - start_time,
            "thinking_ratio": 0,
            "tps": total_tokens / (end_time - start_time) if (end_time - start_time) > 0 else 0,
            "tokens": total_tokens,
            "success": True,
            "answer": full_text,
            "streaming": False
        }
    except Exception as e:
        print(f"  [DEBUG] Non-streaming request failed: {e}")
        return {"id": request_id, "success": False, "streaming": False}


async def measure_request(client, model_name, prompt, request_id):
    """Wraps the request, attempting streaming first and falling back to non-streaming if needed."""
    result = await measure_request_streaming(client, model_name, prompt, request_id)
    if result.get("success") and (not result.get("answer") or result.get("tokens", 0) == 0):
        print(f"  [INFO] Streaming provided no content deltas, trying non-streaming...")
        result = await measure_request_non_streaming(client, model_name, prompt, request_id)
    return result


async def run_benchmark(url, api_key, id_selection, verbose=False):
    """Main function to discover models, load prompts, and run the evaluation sequence."""
    client = AsyncOpenAI(base_url=url, api_key=api_key)

    # Automated model lookup from server
    print("Querying server for actively loaded models...")
    model_name = "facebook/opt-125m"  # Local fallback model
    try:
        models_list = await client.models.list()
        if models_list.data:
            model_name = models_list.data[0].id
            print(f"[INFO] Model successfully detected: '{model_name}'")
    except Exception as e:
        print(f"[WARN] API model query failed ({e}). Using script fallback standard.")

    prompts = load_prompts(PROMPTS_FILE)
    indices = parse_id_selection(id_selection)

    if indices is None:
        selected = prompts
        print(f"[INFO] Starting benchmark for all {len(selected)} prompts.")
    else:
        selected = []
        for idx in indices:
            pos = idx - 1
            if 0 <= pos < len(prompts):
                selected.append(prompts[pos])
        if not selected:
            print(f"No valid prompts found for selection.")
            return

    results = []
    for i, prompt_data in enumerate(selected):
        prompt_index = indices[i] if indices else (i + 1)

        if DEBUG_HELLO:
            problem = "According to Douglas Adams' The Hitchhiker's Guide to the Galaxy, what is the ultimate answer to the ultimate question of life? Provide just the number."
            expected_answer = "42"
        else:
            problem = prompt_data["problem"]
            expected_answer = prompt_data.get("answer", "N/A")

        print(f"\n=== AIME Prompt ID: {prompt_data['id']} (Pos {prompt_index}) ===")
        print(f"Problem: {problem[:80]}...")
        print(f"Expected: {expected_answer}")
        print("-" * 50)

        result = await measure_request(client, model_name, problem, prompt_data["id"])

        results.append({
            **result,
            "expected_answer": expected_answer
        })

        if verbose and result["success"] and result.get("streaming"):
            if result.get("thinking"):
                print(f"\n--- Thinking Process ---")
                print(result["thinking"][:400] + "..." if len(result["thinking"]) > 400 else result["thinking"])
            print(f"\n--- Full Response ---")
            print(result["answer"][:400] + "..." if len(result.get("answer", "")) > 400 else result.get("answer", ""))

    print_statistics(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str, required=True, help="URL of the server (e.g. http://192.168.0.109:1234/v1)")
    parser.add_argument("--key", type=str, required=True, help="API Key")
    parser.add_argument("--id", type=str, default=None, help="Position (1-based), e.g. '5' or '1-3'")
    parser.add_argument("--verbose", action="store_true", help="Outputs truncated thinking and full response")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.url, args.key, args.id, verbose=args.verbose))