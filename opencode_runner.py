from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path

from config import Settings
from security import opencode_config, system_instruction


@dataclass
class RunResult:
    returncode: int
    output: str


class OpenCodeRunner:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def run(self, project: Path, mode: str, prompt: str) -> RunResult:
        env = os.environ.copy()
        env['OPENCODE_CONFIG_CONTENT'] = opencode_config(mode)

        full_prompt = f'{system_instruction(mode)}\n\nЗАДАНИЕ ПОЛЬЗОВАТЕЛЯ:\n{prompt.strip()}'
        cmd = [self.settings.opencode_bin, 'run', '--auto']
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
                proc.communicate(), timeout=self.settings.task_timeout_seconds
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return RunResult(124, 'OpenCode остановлен: превышен лимит времени.')

        text = stdout.decode(errors='replace').strip()
        if len(text) > self.settings.max_output_chars:
            text = text[-self.settings.max_output_chars:]
            text = '[...начало вывода сокращено...]\n' + text
        return RunResult(proc.returncode or 0, text or '(OpenCode не вернул текст)')
