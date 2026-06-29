import sys
from io import StringIO

sys.path.insert(0, "/Users/thtesche/VibeCoding/llm-inference-bench")

from api_benchmark import parse_id_selection


class TestParseIdSelection:
    """Tests für parse_id_selection(id_arg)."""

    def test_none_returns_none(self):
        assert parse_id_selection(None) is None

    def test_empty_string_returns_none(self):
        assert parse_id_selection("") is None

    def test_single_number(self):
        assert parse_id_selection("5") == [5]

    def test_whitespace_trimming(self):
        assert parse_id_selection(" 5 ") == [5]

    def test_range_inclusive(self):
        assert parse_id_selection("3-7") == [3, 4, 5, 6, 7]

    def test_degenerate_range(self):
        assert parse_id_selection("1-1") == [1]

    def test_comma_separated(self):
        assert parse_id_selection("6,8,10") == [6, 8, 10]

    def test_mixed_range_and_single(self):
        assert parse_id_selection("1-3,5,7-9") == [1, 2, 3, 5, 7, 8, 9]

    def test_invalid_string_fallback(self):
        captured = StringIO()
        sys.stdout = captured
        result = parse_id_selection("abc")
        sys.stdout = sys.__stdout__
        assert result is None
        assert "[WARN]" in captured.getvalue()

    def test_partially_invalid_comma_list(self):
        captured = StringIO()
        sys.stdout = captured
        result = parse_id_selection("5,abc,8")
        sys.stdout = sys.__stdout__
        assert result == [5, 8]
        assert "[WARN]" in captured.getvalue()

    def test_only_commas_returns_none(self):
        assert parse_id_selection(",,") is None

    def test_invalid_range_syntax_fallback(self):
        captured = StringIO()
        sys.stdout = captured
        result = parse_id_selection("1-")
        sys.stdout = sys.__stdout__
        assert result is None
        assert "[WARN]" in captured.getvalue()
