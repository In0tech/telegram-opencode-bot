from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path


class GitError(RuntimeError):
    pass


async def _git(project: Path, *args: str, timeout: int = 60) -> str:
    proc = await asyncio.create_subprocess_exec(
        'git', *args,
        cwd=project,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise GitError('Git command timeout')

    out = stdout.decode(errors='replace').strip()
    err = stderr.decode(errors='replace').strip()
    if proc.returncode != 0:
        raise GitError(err or out or f'git exited with {proc.returncode}')
    return out


async def current_branch(project: Path) -> str:
    return await _git(project, 'branch', '--show-current')


async def list_branches(project: Path) -> list[str]:
    out = await _git(project, 'for-each-ref', '--format=%(refname:short)', 'refs/heads/')
    return [line.strip() for line in out.splitlines() if line.strip()]


async def switch_branch(project: Path, branch: str) -> str:
    if not branch or any(ch.isspace() for ch in branch):
        raise GitError('Недопустимое имя ветки.')
    dirty = await _git(project, 'status', '--porcelain')
    if dirty:
        raise GitError('Нельзя переключить ветку: есть незакоммиченные изменения.')
    await _git(project, 'switch', branch)
    return await current_branch(project)


async def status(project: Path) -> str:
    out = await _git(project, 'status', '--short', '--branch')
    return out or 'Working tree clean.'


async def diff(project: Path) -> str:
    unstaged = await _git(project, 'diff', '--no-ext-diff', '--')
    staged = await _git(project, 'diff', '--cached', '--no-ext-diff', '--')
    result = []
    if staged:
        result.append('=== STAGED ===\n' + staged)
    if unstaged:
        result.append('=== UNSTAGED ===\n' + unstaged)
    return '\n\n'.join(result) or 'Изменений нет.'


async def ensure_work_branch(project: Path, protected: frozenset[str]) -> str:
    branch = await current_branch(project)
    if branch not in protected:
        return branch
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    new_branch = f'ai/{stamp}'
    await _git(project, 'switch', '-c', new_branch)
    return new_branch


async def commit_all(project: Path, message: str) -> str:
    await _git(project, 'add', '-A')
    out = await _git(project, 'commit', '-m', message, '--')
    sha = await _git(project, 'rev-parse', '--short', 'HEAD')
    return f'{sha}\n{out}'


async def push_current(project: Path) -> str:
    branch = await current_branch(project)
    if not branch:
        raise GitError('Detached HEAD: push запрещён.')
    return await _git(project, 'push', '-u', 'origin', branch, timeout=180)


async def rollback_tracked_changes(project: Path) -> str:
    before = await status(project)
    await _git(project, 'restore', '--staged', '--worktree', '--', '.')
    after = await status(project)
    return f'До rollback:\n{before}\n\nПосле rollback:\n{after}\n\nUntracked-файлы не удалялись.'
