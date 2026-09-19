from opencode_runner import _clean_output


def test_clean_output_removes_ansi_sequences():
    raw = b"\x1b[0mHello\x1b[32m world\x1b[0m\r\n"
    assert _clean_output(raw) == "Hello world"


def test_clean_output_normalizes_carriage_returns():
    raw = b"line1\rline2\r\nline3"
    assert _clean_output(raw) == "line1\nline2\nline3"
