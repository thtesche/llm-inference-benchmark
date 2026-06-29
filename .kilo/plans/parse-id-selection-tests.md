# Tests für `parse_id_selection` in api_benchmark.py

## Ziel
pytest-Tests für die Funktion `parse_id_selection(id_arg)` erstellen, die das `--id` CLI-Argument parst und eine Liste von 1-basierten Indizes zurückgibt.

## Setup
- Framework: **pytest** (`pip install pytest`)
- Test-Datei: `tests/test_api_benchmark.py`
- Init-File: `tests/__init__.py`

## Test-Fälle

| # | Input | Erwartetes Ergebnis | Beschreibung |
|---|-------|---------------------|--------------|
| 1 | `None` | `None` | Keine ID → alle Prompts |
| 2 | `""` | `None` | Leerer String → alle Prompts |
| 3 | `"5"` | `[5]` | Einzelne Zahl |
| 4 | `" 5 "` | `[5]` | Whitespace-Trimming |
| 5 | `"3-7"` | `[3, 4, 5, 6, 7]` | Range (inklusiv) |
| 6 | `"1-1"` | `[1]` | Degenerierter Range |
| 7 | `"6,8,10"` | `[6, 8, 10]` | Kommagetrennte IDs |
| 8 | `"1-3,5,7-9"` | `[1, 2, 3, 5, 7, 8, 9]` | Gemischt: Range + Einzel + Range |
| 9 | `"abc"` | `None` (+ Warnung) | Ungültiger String → Fallback alle |
| 10 | `"5,abc,8"` | `[5, 8]` (+ Warnung) | Partiell ungültig → gültige bleiben |
| 11 | `",,"` | `None` | Nur Kommas → keine gültigen IDs |
| 12 | `"1-"` | `None` (+ Warnung) | Ungültiger Range-Syntax → Fallback alle |

## Validierung
```bash
cd /Users/thtesche/VibeCoding/llm-inference-bench
pip install pytest
pytest tests/test_api_benchmark.py -v
```

## Nächste Schritte (nicht in diesem Plan)
- Tests für `extract_answer`, `parse_answer_from_boxed`, `compare_answers`, `format_time`
- Tests für `load_prompts` mit Test-Fixtures
- Async-Tests für `measure_request_*` und `run_benchmark` mit API-Mocks
PLAN_EOF
```