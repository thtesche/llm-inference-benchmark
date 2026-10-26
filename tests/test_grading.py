import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api_benchmark import compare_answers, extract_answer
from archive import _extract_answer, _is_correct


class TestExtractAnswer:
    """Extraction must pick the *last* boxed/candidate value, not a quoted placeholder."""

    def test_last_boxed_wins_over_quoted_placeholder(self):
        text = "Answer with candidate_answer=N and \\boxed{N}.\nWork...\n\\boxed{30}"
        assert extract_answer(text) == "30"
        assert _extract_answer(text) == "30"

    def test_last_candidate_answer_wins(self):
        text = "candidate_answer=12 ... revision ... candidate_answer=42"
        assert extract_answer(text) == "42"

    def test_archive_and_runner_agree(self):
        text = "\\boxed{7}"
        assert extract_answer(text) == _extract_answer(text) == "7"

    def test_last_number_fallback(self):
        assert extract_answer("the result is 17") == "17"


class TestGrading:
    """Numeric tasks are graded, free-text tasks are reported as not auto-gradable."""

    def test_numeric_match(self):
        assert compare_answers("42", 42) == (True, "CORRECT")

    def test_numeric_mismatch(self):
        assert compare_answers("41", 42) == (False, "WRONG")

    def test_missing_answer_is_wrong(self):
        assert compare_answers(None, 42) == (False, "WRONG")

    def test_free_text_expected_is_not_gradable(self):
        assert compare_answers("100", "The bug is in process_100") == (None, "N/A")

    def test_archive_is_correct_matches_runner(self):
        numeric = {"expected_answer": "42", "answer": "\\boxed{42}"}
        free_text = {"expected_answer": "buffer flush issue", "answer": "some analysis"}
        assert _is_correct(numeric) is True
        assert _is_correct(free_text) is None

    def test_archive_is_correct_numeric_wrong(self):
        assert _is_correct({"expected_answer": "42", "answer": "\\boxed{41}"}) is False

    @pytest.mark.parametrize("expected", ["42", 42, " 42 "])
    def test_expected_normalisation(self, expected):
        assert compare_answers("42", expected)[0] is True
