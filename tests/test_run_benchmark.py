import os
import re
import subprocess
from pathlib import Path

import pytest

SCRIPT = str(Path(__file__).resolve().parent.parent / "run_benchmark.sh")


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Führt run_benchmark.sh --dry-run mit den gegebenen Argumenten aus."""
    cmd = ["bash", SCRIPT, "--dry-run"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def _extract_url(output: str) -> str | None:
    m = re.search(r"URL:\s*(.+)", output)
    return m.group(1).strip() if m else None


def _extract_id(output: str) -> str | None:
    m = re.search(r"PYTHON_ARGS:.*--id\s+(.+)", output)
    return m.group(1).strip() if m else None


def _extract_key(output: str) -> str | None:
    m = re.search(r"PYTHON_ARGS:.*--key\s+(\S+)", output)
    return m.group(1).strip() if m else None


class TestRunBenchmarkDefaults:
    """Testet die Standardwerte ohne Argumente."""

    def test_default_url(self):
        r = _run([])
        assert r.returncode == 0
        assert _extract_url(r.stdout) == "http://192.168.0.109:1234/v1"

    def test_default_id(self):
        r = _run([])
        assert _extract_id(r.stdout) == "1"

    def test_key_masked_in_output(self):
        r = _run([])
        assert "YOUR******" in r.stdout  # Key wird maskiert ausgegeben


class TestRunBenchmarkURL:
    """Testet --url Flag."""

    def test_custom_url(self):
        r = _run(["--url", "http://localhost:8080/v1"])
        assert _extract_url(r.stdout) == "http://localhost:8080/v1"

    def test_url_with_port(self):
        r = _run(["--url", "https://api.example.com:443/openai"])
        assert _extract_url(r.stdout) == "https://api.example.com:443/openai"


class TestRunBenchmarkKey:
    """Testet --key Flag."""

    def test_custom_key(self):
        r = _run(["--key", "sk-test123"])
        assert _extract_key(r.stdout) == "sk-test123"


class TestRunBenchmarkID:
    """Testet --id Flag mit verschiedenen Formaten."""

    def test_single_id(self):
        r = _run(["--id", "5"])
        assert _extract_id(r.stdout) == "5"

    def test_range_id(self):
        r = _run(["--id", "3-7"])
        assert _extract_id(r.stdout) == "3-7"

    def test_comma_separated_ids(self):
        r = _run(["--id", "6,8,10"])
        assert _extract_id(r.stdout) == "6,8,10"

    def test_multiple_ids_as_separate_args(self):
        r = _run(["--id", "1", "3", "5"])
        assert _extract_id(r.stdout) == "1-5"


class TestRunBenchmarkCombined:
    """Testet Kombinationen mehrerer Flags."""

    def test_url_key_id(self):
        r = _run(["--url", "http://test:9000/v1", "--key", "sk-abc", "--id", "42"])
        assert _extract_url(r.stdout) == "http://test:9000/v1"
        assert _extract_key(r.stdout) == "sk-abc"
        assert _extract_id(r.stdout) == "42"

    def test_url_key_range(self):
        r = _run(["--url", "http://x:1/v1", "--key", "k", "--id", "1-5"])
        assert _extract_url(r.stdout) == "http://x:1/v1"
        assert _extract_key(r.stdout) == "k"
        assert _extract_id(r.stdout) == "1-5"


class TestRunBenchmarkDryRun:
    """Stellt sicher, dass --dry-run korrekt funktioniert."""

    def test_dry_run_exits_zero(self):
        r = _run(["--url", "http://x/v1"])
        assert r.returncode == 0

    def test_dry_run_no_python_call(self):
        """--dry-run darf nicht versuchen, Python aufzurufen."""
        r = _run([])
        assert "venv" not in r.stderr or "Creating virtual environment" not in r.stdout
        assert "PYTHON_ARGS:" in r.stdout

    def test_dry_run_no_venv_created(self):
        """--dry-run darf kein venv erstellen."""
        r = _run([])
        assert "Creating virtual environment" not in r.stdout
