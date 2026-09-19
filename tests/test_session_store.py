from pathlib import Path

from session_store import SessionStore


def test_named_sessions_persist(tmp_path: Path):
    store = SessionStore(tmp_path / 'sessions.json')
    store.set(123, 'demo', 'backend', 'ses_abc')
    reopened = SessionStore(tmp_path / 'sessions.json')
    assert reopened.get(123, 'demo', 'backend') == 'ses_abc'


def test_sessions_are_isolated_by_project(tmp_path: Path):
    store = SessionStore(tmp_path / 'sessions.json')
    store.set(123, 'one', 'default', 'ses_one')
    store.set(123, 'two', 'default', 'ses_two')
    assert store.get(123, 'one', 'default') == 'ses_one'
    assert store.get(123, 'two', 'default') == 'ses_two'
