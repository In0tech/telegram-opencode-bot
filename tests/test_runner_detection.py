from pathlib import Path

from test_runner import detect_test_command


def test_detects_pytest(tmp_path: Path):
    (tmp_path / 'tests').mkdir()
    assert detect_test_command(tmp_path) == ['python3', '-m', 'pytest', '-q']


def test_detects_npm(tmp_path: Path):
    (tmp_path / 'package.json').write_text('{}')
    assert detect_test_command(tmp_path) == ['npm', 'test']
