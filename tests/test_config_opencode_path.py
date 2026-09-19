from pathlib import Path

import config


def test_resolve_absolute_path(tmp_path: Path):
    binary = tmp_path / 'opencode'
    binary.write_text('#!/bin/sh\nexit 0\n')
    binary.chmod(0o755)
    assert config._resolve_executable(str(binary)) == str(binary.resolve())


def test_resolve_common_home_location(monkeypatch, tmp_path: Path):
    binary = tmp_path / '.opencode' / 'bin' / 'opencode'
    binary.parent.mkdir(parents=True)
    binary.write_text('#!/bin/sh\nexit 0\n')
    binary.chmod(0o755)

    monkeypatch.setattr(config.Path, 'home', classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(config.shutil, 'which', lambda value: None)

    assert config._resolve_executable('opencode') == str(binary)
