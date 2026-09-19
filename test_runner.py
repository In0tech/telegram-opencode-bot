from __future__ import annotations

import asyncio
from pathlib import Path


class TestRunError(RuntimeError):
    pass


def detect_test_command(project: Path, requested: str | None = None) -> list[str]:
    choice = (requested or '').strip().lower()

    if choice in {'python', 'pytest'}:
        return ['python3', '-m', 'pytest', '-q']
    if choice in {'npm', 'node'}:
        return ['npm', 'test', '--', '--runInBand']
    if choice == 'pnpm':
        return ['pnpm', 'test']
    if choice == 'go':
        return ['go', 'test', './...']
    if choice in {'rust', 'cargo'}:
        return ['cargo', 'test']

    if (project / 'pytest.ini').exists() or (project / 'pyproject.toml').exists() or (project / 'tests').is_dir():
        return ['python3', '-m', 'pytest', '-q']
    if (project / 'package.json').exists():
        return ['npm', 'test', '--', '--runInBand']
    if (project / 'go.mod').exists():
        return ['go', 'test', './...']
    if (project / 'Cargo.toml').exists():
        return ['cargo', 'test']

    raise TestRunError('Не удалось определить test runner. Используйте /tests python|npm|pnpm|go|cargo.')


async def run_tests(project: Path, requested: str | None = None, timeout: int = 900) -> tuple[list[str], int, str]:
    cmd = detect_test_command(project, requested)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=project,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return cmd, 124, 'Тесты остановлены по timeout.'
    return cmd, proc.returncode or 0, stdout.decode(errors='replace').strip()
