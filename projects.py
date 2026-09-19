from __future__ import annotations

import re
from pathlib import Path

PROJECT_RE = re.compile(r'^[A-Za-z0-9._-]+$')


class ProjectError(ValueError):
    pass


def list_projects(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(
        p.name for p in root.iterdir()
        if p.is_dir() and (p / '.git').exists()
    )


def resolve_project(root: Path, name: str) -> Path:
    name = name.strip()
    if not PROJECT_RE.fullmatch(name):
        raise ProjectError('Недопустимое имя проекта.')

    root = root.resolve()
    candidate = (root / name).resolve()
    if candidate.parent != root:
        raise ProjectError('Проект должен находиться непосредственно в PROJECT_ROOT.')
    if not candidate.is_dir():
        raise ProjectError(f'Проект {name!r} не найден.')
    if not (candidate / '.git').exists():
        raise ProjectError(f'{name!r} не является Git-репозиторием.')
    return candidate
