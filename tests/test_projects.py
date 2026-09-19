from pathlib import Path
import tempfile

import pytest

from projects import ProjectError, list_projects, resolve_project


def test_only_git_directories_are_listed():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / 'repo' / '.git').mkdir(parents=True)
        (root / 'plain').mkdir()
        assert list_projects(root) == ['repo']


def test_path_traversal_rejected():
    with tempfile.TemporaryDirectory() as d:
        with pytest.raises(ProjectError):
            resolve_project(Path(d), '../etc')
