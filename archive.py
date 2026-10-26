import sqlite3
import json
import os
import re
from datetime import datetime
from pathlib import Path

DB_PATH = "runs.db"
BACKUP_DIR = "benchmark_data"

def init_db():
    """Initialize database with schema if it doesn't exist."""
    Path(BACKUP_DIR).mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Runs table: metadata for each benchmark run
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            server_type TEXT,
            model TEXT,
            api_url TEXT,
            notes TEXT,
            accuracy REAL,
            avg_ttft REAL,
            avg_tps REAL,
            total_correct INTEGER,
            total_problems INTEGER
        )
    """)
    
    # Results table: individual problem results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            problem_id TEXT,
            position INTEGER,
            expected TEXT,
            extracted TEXT,
            correct INTEGER,
            ttft REAL,
            reasoning_time REAL,
            answer_time REAL,
            total_latency REAL,
            input_context_tokens INTEGER,
            reasoning_tokens INTEGER,
            answer_tokens INTEGER,
            total_tokens INTEGER,
            tps REAL,
            prefill_tps REAL,
            generation_tps REAL,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        )
    """)
    
    # Server type history for autocomplete
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS server_history (
            server_type TEXT PRIMARY KEY,
            last_used TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def save_run(results, server_type, model, api_url, notes):
    """Save benchmark run to database and backup as JSON.
    
    Args:
        results: List of result dicts from api_benchmark.py
        server_type: String identifier (e.g., "llama.cpp")
        model: Model name
        api_url: API base URL
        notes: User notes
    
    Returns:
        run_id: The inserted run ID
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Calculate aggregates
    successful = [r for r in results if r.get("success")]
    correct = sum(1 for r in successful if r.get("answer"))
    accuracy = correct / len(successful) if successful else 0
    
    ttfts = [r["ttft"] for r in successful if "ttft" in r]
    avg_ttft = sum(ttfts) / len(ttfts) if ttfts else 0
    
    tps_values = [r["tps"] for r in successful if r.get("tps", 0) > 0]
    avg_tps = sum(tps_values) / len(tps_values) if tps_values else 0
    
    total_problems = len(results)
    
    # Insert run metadata
    cursor.execute("""
        INSERT INTO runs 
        (timestamp, server_type, model, api_url, notes, accuracy, avg_ttft, avg_tps, total_correct, total_problems)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, server_type, model, api_url, notes, accuracy, avg_ttft, avg_tps, correct, total_problems))
    
    run_id = cursor.lastrowid
    
    # Insert individual results
    for result in results:
        extracted = ""
        if result.get("answer"):
            # Extract answer from the response
            match = re.search(r'\\boxed\{([^}]+)\}', result.get("answer", ""))
            if match:
                extracted = match.group(1).strip()
            else:
                match = re.search(r'candidate_answer\s*=\s*(\d+)', result.get("answer", ""), re.IGNORECASE)
                if match:
                    extracted = match.group(1).strip()
        
        correct_flag = 1 if result.get("success") and extracted else 0
        
        cursor.execute("""
            INSERT INTO results
            (run_id, problem_id, position, expected, extracted, correct, ttft, reasoning_time, 
             answer_time, total_latency, input_context_tokens, reasoning_tokens, answer_tokens, total_tokens, tps,
             prefill_tps, generation_tps)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            result.get("id"),
            result.get("position", 0),
            result.get("expected_answer", ""),
            extracted,
            correct_flag,
            result.get("ttft", 0),
            result.get("reasoning_time", 0),
            result.get("answer_time", 0),
            result.get("total_latency", 0),
            result.get("input_context_tokens", 0),
            result.get("reasoning_tokens", 0),
            result.get("answer_tokens", 0),
            result.get("tokens", 0),
            result.get("tps", 0),
            result.get("prefill_tps", 0),
            result.get("generation_tps", 0)
        ))
    
    conn.commit()
    
    # Update server history
    cursor.execute("INSERT OR REPLACE INTO server_history (server_type, last_used) VALUES (?, ?)",
                  (server_type, timestamp))
    conn.commit()
    conn.close()
    
    # Write JSON backup
    backup_filename = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    backup_path = Path(BACKUP_DIR) / backup_filename
    
    backup_data = {
        "run_id": run_id,
        "timestamp": timestamp,
        "server_type": server_type,
        "model": model,
        "api_url": api_url,
        "notes": notes,
        "results": results,
        "aggregate": {
            "total": total_problems,
            "correct": correct,
            "accuracy": accuracy,
            "avg_ttft": avg_ttft,
            "avg_tps": avg_tps
        }
    }
    
    with open(backup_path, "w") as f:
        json.dump(backup_data, f, indent=2)
    
    return run_id

def get_last_server_type():
    """Get the most recently used server type for autocomplete."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT server_type FROM server_history ORDER BY last_used DESC LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def get_server_history(limit=5):
    """Get recent server types used."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT server_type FROM server_history ORDER BY last_used DESC LIMIT ?", (limit,))
    results = cursor.fetchall()
    conn.close()
    
    return [r[0] for r in results]

def list_runs(limit=10, server_type_filter=None):
    """List recent runs with summary stats."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if server_type_filter:
        cursor.execute("""
            SELECT id, timestamp, server_type, model, accuracy, avg_tps, total_correct, total_problems, notes
            FROM runs
            WHERE server_type = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (server_type_filter, limit))
    else:
        cursor.execute("""
            SELECT id, timestamp, server_type, model, accuracy, avg_tps, total_correct, total_problems, notes
            FROM runs
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
    
    runs = cursor.fetchall()
    conn.close()
    
    result = []
    for run in runs:
        result.append({
            "id": run[0],
            "timestamp": run[1],
            "server_type": run[2],
            "model": run[3],
            "accuracy": run[4],
            "avg_tps": run[5],
            "correct": run[6],
            "total": run[7],
            "notes": run[8]
        })
    
    return result

def get_run(run_id):
    """Get full run data including all problem results."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get run metadata
    cursor.execute("""
        SELECT id, timestamp, server_type, model, api_url, notes, accuracy, avg_ttft, avg_tps, total_correct, total_problems
        FROM runs
        WHERE id = ?
    """, (run_id,))
    
    run = cursor.fetchone()
    if not run:
        conn.close()
        return None
    
    # Get individual results
    cursor.execute("""
        SELECT problem_id, position, expected, extracted, correct, ttft, reasoning_time, answer_time, 
               total_latency, input_context_tokens, reasoning_tokens, answer_tokens, total_tokens, tps, prefill_tps, generation_tps
        FROM results
        WHERE run_id = ?
        ORDER BY position
    """, (run_id,))
    
    results = cursor.fetchall()
    conn.close()
    
    run_data = {
        "id": run[0],
        "timestamp": run[1],
        "server_type": run[2],
        "model": run[3],
        "api_url": run[4],
        "notes": run[5],
        "accuracy": run[6],
        "avg_ttft": run[7],
        "avg_tps": run[8],
        "total_correct": run[9],
        "total_problems": run[10],
        "results": []
    }
    
    for result in results:
        run_data["results"].append({
            "problem_id": result[0],
            "position": result[1],
            "expected": result[2],
            "extracted": result[3],
            "correct": bool(result[4]),
            "ttft": result[5],
            "reasoning_time": result[6],
            "answer_time": result[7],
            "total_latency": result[8],
            "input_context_tokens": result[9],
            "reasoning_tokens": result[10],
            "answer_tokens": result[11],
            "total_tokens": result[12],
            "tps": result[13],
            "prefill_tps": result[14],
            "generation_tps": result[15]
        })
    
    return run_data

def compare_runs(run_id_1, run_id_2):
    """Compare two runs, return differences."""
    run1 = get_run(run_id_1)
    run2 = get_run(run_id_2)
    
    if not run1 or not run2:
        return None
    
    comparison = {
        "run_1": {
            "id": run1["id"],
            "timestamp": run1["timestamp"],
            "server_type": run1["server_type"],
            "model": run1["model"],
            "accuracy": run1["accuracy"],
            "avg_ttft": run1["avg_ttft"],
            "avg_tps": run1["avg_tps"]
        },
        "run_2": {
            "id": run2["id"],
            "timestamp": run2["timestamp"],
            "server_type": run2["server_type"],
            "model": run2["model"],
            "accuracy": run2["accuracy"],
            "avg_ttft": run2["avg_ttft"],
            "avg_tps": run2["avg_tps"]
        },
        "differences": {
            "accuracy_delta": run2["accuracy"] - run1["accuracy"],
            "ttft_delta": run2["avg_ttft"] - run1["avg_ttft"],
            "tps_delta": run2["avg_tps"] - run1["avg_tps"],
        },
        "detailed_results": []
    }
    
    for i, (r1, r2) in enumerate(zip(run1["results"], run2["results"])):
        comparison["detailed_results"].append({
            "position": i + 1,
            "problem_id": r1["problem_id"],
            "run_1": {
                "correct": r1["correct"],
                "ttft": r1["ttft"],
                "tps": r1["tps"],
                "prefill_tps": r1["prefill_tps"],
                "generation_tps": r1["generation_tps"]
            },
            "run_2": {
                "correct": r2["correct"],
                "ttft": r2["ttft"],
                "tps": r2["tps"],
                "prefill_tps": r2["prefill_tps"],
                "generation_tps": r2["generation_tps"]
            }
        })
    
    return comparison

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
