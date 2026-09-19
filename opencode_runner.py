from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
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


def _extract_error_message(event: dict) -> str | None:
    error = event.get('error')
    if isinstance(error, str) and error:
        return error
    if isinstance(error, dict):
        data = error.get('data')
        if isinstance(data, dict):
            message = data.get('message')
            if isinstance(message, str) and message:
                return message
        for key in ('message', 'name'):
            value = error.get(key)
            if isinstance(value, str) and value:
                return value
    message = event.get('message')
    if isinstance(message, str) and message:
        return message
    return None


def _parse_json_stream(raw: bytes) -> tuple[str, str | None]:
    texts: list[str] = []
    errors: list[str] = []
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

        if not isinstance(event, dict):
            continue

        if not session_id:
            value = event.get('sessionID')
            if isinstance(value, str) and value:
                session_id = value

        if event.get('type') == 'text':
            part = event.get('part')
            if isinstance(part, dict):
                text = part.get('text')
                if isinstance(text, str) and text:
                    texts.append(text)

        if event.get('type') == 'error':
            message = _extract_error_message(event)
            if message:
                errors.append(message)

    output = '\n'.join(texts).strip()
    if not output and errors:
        output = 'OpenCode error: ' + '\n'.join(errors)
    if not output:
        output = '\n'.join(fallback).strip()
    return output, session_id


class OpenCodeRunner:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._resolved_model: str | None = None

    async def _resolve_model(
        self,
        project: Path,
        env: dict[str, str],
    ) -> tuple[str | None, str | None]:
        if self.settings.opencode_model:
            return self.settings.opencode_model, None

        if self._resolved_model:
            return self._resolved_model, None

        provider = self.settings.opencode_provider

        # Compatibility across OpenCode versions: list all models, then filter.
        rc, raw = await self._spawn(
            project,
            [self.settings.opencode_bin, 'models'],
            env,
            timeout=30,
        )
        text = _clean_output(raw)
        if rc != 0:
            return None, (
                'Не удалось получить список моделей OpenCode.\n'
                f'{text or f"opencode models rc={rc}"}'
            )

        prefix = provider + '/'
        candidates: list[str] = []
        for line in text.splitlines():
            value = line.strip()
            if value.startswith(prefix):
                model = value.split()[0]
                if model not in candidates:
                    candidates.append(model)

        if not candidates:
            return None, (
                f'У OpenCode нет моделей {prefix}*. '
                'Проверьте OAuth через /connect → OpenAI → ChatGPT Plus/Pro.'
            )

        # Prefer general ChatGPT models over Codex-only variants.
        def rank(model: str) -> tuple[int, int, str]:
            name = model.split('/', 1)[-1].lower()
            if 'codex' in name:
                group = 50
            elif 'gpt-5.6-sol' in name:
                group = 0
            elif 'gpt-5.6-luna' in name:
                group = 1
            elif 'gpt-5.5' in name:
                group = 2
            elif 'gpt-6-astra' in name:
                group = 3
            else:
                group = 10
            fast = 1 if name.endswith('-fast') else 0
            return group, fast, model

        candidates.sort(key=rank)

        errors: list[str] = []
        for model in candidates:
            probe_cmd = [
                self.settings.opencode_bin,
                'run',
                '--standalone',
                '--model',
                model,
                'Ответь одним словом: OK',
            ]
            probe_rc, probe_raw = await self._spawn(
                project,
                probe_cmd,
                env,
                timeout=45,
            )
            probe_text = _clean_output(probe_raw)
            if probe_rc == 0:
                self._resolved_model = model
                return model, None

            errors.append(f'{model}: {probe_text or f"rc={probe_rc}"}')

        preview = '\n'.join(errors[:5])
        return None, (
            'Ни одна модель OpenAI из текущего списка не прошла проверку через '
            'ChatGPT-account OAuth.\n\n'
            + preview
            + '\n\nПроверьте авторизацию OpenAI и доступность модели вручную.'
        )

    async def _spawn(
        self,
        project: Path,
        cmd: list[str],
        env: dict[str, str],
        timeout: int | None = None,
    ) -> tuple[int, bytes]:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(project),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except FileNotFoundError:
            return 127, (
                'OpenCode не найден. Проверенный путь: '
                f'{self.settings.opencode_bin}. '
                'Проверьте "which opencode" и OPENCODE_BIN в .env.'
            ).encode()

        try:
            stdout, _ = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout or self.settings.task_timeout_seconds,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return 124, b'OpenCode stopped: timeout exceeded.'

        return proc.returncode or 0, stdout

    async def _find_session_id(
        self,
        project: Path,
        env: dict[str, str],
        title: str,
    ) -> str | None:
        cmd = [
            self.settings.opencode_bin,
            'session',
            'list',
            '--max-count',
            '30',
            '--format',
            'json',
        ]
        rc, raw = await self._spawn(project, cmd, env, timeout=30)
        if rc != 0:
            return None

        try:
            items = json.loads(raw.decode(errors='replace'))
        except json.JSONDecodeError:
            return None

        if not isinstance(items, list):
            return None

        project_path = str(project.resolve())
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get('title') != title:
                continue
            directory = item.get('directory')
            if isinstance(directory, str):
                try:
                    if str(Path(directory).resolve()) != project_path:
                        continue
                except OSError:
                    continue
            session_id = item.get('id')
            if isinstance(session_id, str) and session_id:
                return session_id
        return None

    def _decorate_provider_error(self, text: str) -> str:
        lowered = text.lower()
        if 'credit_balance_exhausted' in lowered or 'no credits remaining' in lowered:
            return (
                text
                + '\n\n'
                + 'Этот OpenCode-сеанс использует платный API/credit provider. '
                  'Для работы через подписку ChatGPT Plus/Pro без Platform API credits '
                  'запустите OpenCode интерактивно, выполните /connect → OpenAI → '
                  'ChatGPT Plus/Pro, затем /models и выберите модель OpenAI. '
                  'В .env оставьте OPENCODE_MODEL пустым, если хотите использовать '
                  'выбранную в OpenCode модель по умолчанию.'
            )
        return text

    async def provider_status(self) -> str:
        workspace = (self.settings.state_dir / 'chatgpt-workspace').resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env['PWD'] = str(workspace)

        auth_rc, auth_raw = await self._spawn(
            workspace,
            [self.settings.opencode_bin, 'auth', 'list'],
            env,
            timeout=30,
        )
        models_rc, models_raw = await self._spawn(
            workspace,
            [self.settings.opencode_bin, 'models'],
            env,
            timeout=30,
        )

        auth = _clean_output(auth_raw) or f'auth list rc={auth_rc}'
        all_models = _clean_output(models_raw)
        prefix = self.settings.opencode_provider + '/'
        filtered = [
            line.strip()
            for line in all_models.splitlines()
            if line.strip().startswith(prefix)
        ]
        models = '\n'.join(filtered) or (
            f'Нет моделей {prefix}* (opencode models rc={models_rc})'
        )

        return (
            'OpenCode auth:\n'
            + auth
            + f'\n\n{self.settings.opencode_provider} models:\n'
            + models
            + '\n\nOPENCODE_PROVIDER=' + self.settings.opencode_provider
            + '\nOPENCODE_MODEL=' + (self.settings.opencode_model or '<auto from provider>')
        )

    async def run_general(
        self,
        prompt: str,
        session_title: str = 'telegram-general',
    ) -> RunResult:
        workspace = (self.settings.state_dir / 'chatgpt-workspace').resolve()
        workspace.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env['OPENCODE_CONFIG_CONTENT'] = opencode_config('chat')
        env['PWD'] = str(workspace)

        cmd = [
            self.settings.opencode_bin,
            'run',
            '--standalone',
            '--auto',
            '--title',
            f'{session_title}:{uuid.uuid4().hex[:8]}',
        ]
        model, model_error = await self._resolve_model(workspace, env)
        if model_error:
            return RunResult(78, model_error, None)
        cmd += ['--model', model]
        cmd.append(prompt)

        rc, stdout = await self._spawn(workspace, cmd, env)
        text = _clean_output(stdout)

        if rc == 124:
            text = 'OpenCode остановлен: превышен лимит времени.'

        text = self._decorate_provider_error(text)

        if len(text) > self.settings.max_output_chars:
            text = '[...начало вывода сокращено...]\n' + text[-self.settings.max_output_chars:]

        if not text:
            text = f'OpenCode завершился без текстового вывода. Код возврата: {rc}.'

        return RunResult(rc, text, None)

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
            return RunResult(
                2,
                f'OpenCode не запущен: некорректный Git-проект: {project}',
                session_id,
            )

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

        discovery_title: str | None = None
        if session_id:
            cmd += ['--session', session_id]
        else:
            base_title = session_title or f'telegram-{project.name}'
            discovery_title = f'{base_title}:{uuid.uuid4().hex[:8]}'
            cmd += ['--title', discovery_title]

        model, model_error = await self._resolve_model(project, env)
        if model_error:
            return RunResult(78, model_error, session_id)

        cmd += ['--model', model]
        cmd.append(full_prompt)

        rc, stdout = await self._spawn(project, cmd, env)

        text = _clean_output(stdout)

        # If a future OpenCode version happens to emit JSON despite default mode,
        # try to extract a meaningful error instead of showing an empty response.
        if not text and stdout:
            parsed, discovered = _parse_json_stream(stdout)
            text = parsed
            if discovered and not session_id:
                session_id = discovered

        discovered_session = session_id
        if rc == 0 and not discovered_session and discovery_title:
            discovered_session = await self._find_session_id(
                project,
                env,
                discovery_title,
            )

        if rc == 124:
            text = 'OpenCode остановлен: превышен лимит времени.'

        text = self._decorate_provider_error(text)

        if len(text) > self.settings.max_output_chars:
            text = '[...начало вывода сокращено...]\n' + text[-self.settings.max_output_chars:]

        if not text:
            text = (
                'OpenCode завершился без текстового вывода. '
                f'Код возврата: {rc}. Запустите /logs и проверьте OpenCode вручную '
                'из каталога проекта.'
            )

        return RunResult(
            rc,
            text,
            discovered_session,
        )
