from opencode_runner import _clean_output, _parse_json_stream


def test_clean_output_removes_ansi_sequences():
    raw = b"\x1b[0mHello\x1b[32m world\x1b[0m\r\n"
    assert _clean_output(raw) == "Hello world"


def test_clean_output_normalizes_carriage_returns():
    raw = b"line1\rline2\r\nline3"
    assert _clean_output(raw) == "line1\nline2\nline3"


def test_parse_json_stream_extracts_text_and_session():
    raw = (
        b'{"type":"text","sessionID":"ses_123","part":{"text":"Hello"}}\n'
    )
    text, session_id = _parse_json_stream(raw)
    assert text == "Hello"
    assert session_id == "ses_123"


def test_parse_json_stream_extracts_nested_error():
    raw = (
        b'{"type":"error","sessionID":"ses_123","error":'
        b'{"name":"Unknown","data":{"message":"Model not found"}}}\n'
    )
    text, session_id = _parse_json_stream(raw)
    assert text == "OpenCode error: Model not found"
    assert session_id == "ses_123"


def test_oauth_env_removes_runtime_config(monkeypatch):
    from types import SimpleNamespace
    from opencode_runner import OpenCodeRunner

    runner = OpenCodeRunner(SimpleNamespace())
    env = runner._oauth_env({
        'OPENCODE_CONFIG_CONTENT': '{"permissions":[]}',
        'PATH': '/usr/bin',
    })

    assert 'OPENCODE_CONFIG_CONTENT' not in env
    assert env['HOME']
    assert env['XDG_CONFIG_HOME'].endswith('/.config')
    assert env['XDG_DATA_HOME'].endswith('/.local/share')
