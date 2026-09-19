from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from config import Settings
from security import opencode_config, system_instruction

_ANSI_RE = re.compile(
    r'(?:\x1B[@-_][0-?]*[ -/]*[@-~])'
    r'|(?:\x9B[0-?]*[ -/]*[@-~])'
)


@dataclass
class RunResult:
    returncode: int
    output: str
    session_id: str | None = None


def _clean_output(raw: bytes) -> str:
    text = raw.decode(errors='replace')
    text = _ANSI_RE.sub('', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _parse_json_stream(raw: bytes) -> tuple[str, str | None]:
    texts: list[str] = []
    session_id: str | None = None
    fallback: list[str] = []

    for line in raw.decode(errors='replace').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            fallback.append(line)
            continue

        if not session_id and isinstance(event, dict):
            value = event.get('sessionID')
            if isinstance(value, str) and value:
                session_id = value

        if isinstance(event, dict) and event.get('type') == 'text':
            part = event.get('part')
            if isinstance(part, dict):
                text = part.get('text')
                if isinstance(text, str) and text:
                    texts.append(text)

    output = '\n'.join(texts).strip()
    if not output:
        output = '\n'.join(fallback).strip()
    return output, session_id


class OpenCodeRunner:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def run(
        self,
        project: Path,
        mode: str,
        prompt: str,
        session_id: str | None = None,
        session_title: str | None = None,
    ) -> RunResult:
        project = project.resolve()

        if not project.is_dir() or not (project / '.git').exists():
            return RunResult(2, f'OpenCode не запущен: некорректный Git-проект: {project}')

        env = os.environ.copy()
        env['OPENCODE_CONFIG_CONTENT'] = opencode_config(mode)
        env['PWD'] = str(project)

        full_prompt = (
            f'{system_instruction(mode)}\n\n'
            f'АКТИВНЫЙ ПРОЕКТ: {project}\n'
            'Работай только с этим Git-проектом и его файлами. '
            'Не используй контекст других локальных репозиториев.\n\n'
            f'ЗАДАНИЕ ПОЛЬЗОВАТЕЛЯ:\n{prompt.strip()}'
        )

        cmd = [self.settings.opencode_bin, 'run', '--standalone', '--auto']

        # For a new named session, JSON mode is used once to capture sessionID.
        # Existing sessions use normal output because some OpenCode versions
        # have known JSON streaming issues when resuming long sessions.
        capture_session = session_id is None
        if capture_session:
            cmd += ['--format', 'json']
            if session_title:
                cmd += ['--title', session_title]
        else:
            cmd += ['--session', session_id]

        if self.settings.opencode_model:
            cmd += ['--model', self.settings.opencode_model]

        cmd.append(full_prompt)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(project),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        try:
            stdout, _ = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.settings.task_timeout_seconds,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return RunResult(124, 'OpenCode остановлен: превышен лимит времени.', session_id)

        if capture_session:
            text, discovered_session = _parse_json_stream(stdout)
            active_session = discovered_session
        else:
            text = _clean_output(stdout)
            active_session = session_id

        text = _clean_output(text.encode())
        if len(text) > self.settings.max_output_chars:
            text = '[...начало вывода сокращено...]\n' + text[-self.settings.max_output_chars:]

        return RunResult(
            proc.returncode or 0,
            text or '(OpenCode не вернул текст)',
            active_session,
        )
