from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from git_ops import GitError, current_branch


async def _run(project: Path, *args: str, timeout: int = 120) -> str:
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=project,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise GitError('GitHub CLI timeout')
    out = stdout.decode(errors='replace').strip()
    err = stderr.decode(errors='replace').strip()
    if proc.returncode != 0:
        raise GitError(err or out or f'command exited with {proc.returncode}')
    return out


async def create_pr(project: Path, title: str | None = None) -> str:
    if not shutil.which('gh'):
        raise GitError('GitHub CLI (gh) не установлен. Установите gh и выполните gh auth login.')

    branch = await current_branch(project)
    if not branch:
        raise GitError('Detached HEAD: PR создать нельзя.')

    try:
        existing = await _run(
            project, 'gh', 'pr', 'view', branch,
            '--json', 'url', '--jq', '.url',
            timeout=60,
        )
        if existing:
            return existing
    except GitError:
        pass

    cmd = ['gh', 'pr', 'create', '--head', branch]
    if title:
        cmd += ['--title', title, '--fill']
    else:
        cmd += ['--fill']

    return await _run(project, *cmd, timeout=180)
