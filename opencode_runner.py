from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from pathlib import Path

from config import Settings
from security import opencode_config, system_instruction

# ANSI/VT100 escape sequences produced by interactive-style CLI output.
_ANSI_RE = re.compile(
    r'(?:\x1B[@-_][0-?]*[ -/]*[@-~])'
    r'|(?:\x9B[0-?]*[ -/]*[@-~])'
)


@dataclass
class RunResult:
    returncode: int
    output: str


def _clean_output(raw: bytes) -> str:
    text = raw.decode(errors='replace')
    text = _ANSI_RE.sub('', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Avoid huge blocks of empty lines after stripping terminal control codes.
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


class OpenCodeRunner:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def run(self, project: Path, mode: str, prompt: str) -> RunResult:
        project = project.resolve()
        if not project.is_dir() or not (project / '.git').exists():
            return RunResult(
                2,
                f'OpenCode не запущен: некорректный Git-проект: {project}',
            )

        env = os.environ.copy()
        env['OPENCODE_CONFIG_CONTENT'] = opencode_config(mode)

        # Some CLI/runtime layers inspect PWD in addition to process.cwd().
        # Keep both values aligned with the selected project.
        env['PWD'] = str(project)

        full_prompt = (
            f'{system_instruction(mode)}\n\n'
            f'АКТИВНЫЙ ПРОЕКТ: {project}\n'
            'Считай этот каталог единственной рабочей директорией задания. '
            'Не используй данные из других локальных проектов.\n\n'
            f'ЗАДАНИЕ ПОЛЬЗОВАТЕЛЯ:\n{prompt.strip()}'
        )

        # OpenCode v2 normally connects local clients to a shared background
        # server. For a Telegram remote-control bot that is undesirable:
        # a shared server may retain a Location from another project.
        #
        # --standalone creates a private server for this request.
        # --dir pins OpenCode's Location to the project explicitly.
        # cwd and PWD are also set as defence-in-depth.
        cmd = [
            self.settings.opencode_bin,
            'run',
            '--standalone',
            '--dir',
            str(project),
            '--auto',
        ]

        if self.settings.opencode_model:
            cmd += ['--model', self.settings.opencode_model]

        cmd.append(full_prompt)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=project,
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
            return RunResult(
                124,
                'OpenCode остановлен: превышен лимит времени.',
            )

        text = _clean_output(stdout)

        if len(text) > self.settings.max_output_chars:
            text = text[-self.settings.max_output_chars:]
            text = '[...начало вывода сокращено...]\n' + text

        return RunResult(
            proc.returncode or 0,
            text or '(OpenCode не вернул текст)',
        )
