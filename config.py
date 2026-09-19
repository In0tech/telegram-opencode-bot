from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _resolve_executable(value: str) -> str:
    value = value.strip() or 'opencode'
    expanded = Path(value).expanduser()

    if expanded.is_absolute() or '/' in value:
        return str(expanded.resolve())

    found = shutil.which(value)
    if found:
        return found

    home = Path.home()
    candidates = [
        home / '.opencode' / 'bin' / value,
        home / '.local' / 'bin' / value,
        home / '.local' / 'share' / 'pnpm' / value,
        home / '.bun' / 'bin' / value,
        home / '.npm-global' / 'bin' / value,
        Path('/usr/local/bin') / value,
        Path('/usr/bin') / value,
    ]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)

    return value


def _csv_ints(value: str) -> frozenset[int]:
    result: set[int] = set()
    for item in value.split(','):
        item = item.strip()
        if item:
            result.add(int(item))
    return frozenset(result)


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    allowed_user_ids: frozenset[int]
    project_root: Path
    state_dir: Path
    opencode_bin: str
    opencode_model: str | None
    task_timeout_seconds: int
    test_timeout_seconds: int
    max_output_chars: int
    protected_branches: frozenset[str]
    log_level: str

    openai_api_key: str | None
    openai_text_model: str
    openai_image_model: str
    openai_image_size: str
    openai_image_quality: str
    openai_video_model: str
    openai_video_size: str
    openai_video_seconds: int
    video_timeout_seconds: int

    @classmethod
    def from_env(cls) -> 'Settings':
        token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
        if not token:
            raise RuntimeError('TELEGRAM_BOT_TOKEN is not set')

        allowed = _csv_ints(os.getenv('ALLOWED_TELEGRAM_USER_IDS', ''))
        if not allowed:
            raise RuntimeError('ALLOWED_TELEGRAM_USER_IDS is not set')

        root = Path(os.getenv('PROJECT_ROOT', '~/projects')).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)

        state_dir = Path(
            os.getenv('STATE_DIR', '~/.local/state/telegram-opencode-bot')
        ).expanduser().resolve()
        state_dir.mkdir(parents=True, exist_ok=True)

        protected = frozenset(
            x.strip() for x in os.getenv(
                'PROTECTED_BRANCHES', 'main,master,production,prod'
            ).split(',') if x.strip()
        )

        video_seconds = int(os.getenv('OPENAI_VIDEO_SECONDS', '8'))
        if video_seconds not in {4, 8, 12}:
            raise RuntimeError('OPENAI_VIDEO_SECONDS must be 4, 8 or 12')

        return cls(
            telegram_bot_token=token,
            allowed_user_ids=allowed,
            project_root=root,
            state_dir=state_dir,
            opencode_bin=_resolve_executable(os.getenv('OPENCODE_BIN', 'opencode')),
            opencode_model=os.getenv('OPENCODE_MODEL', '').strip() or None,
            task_timeout_seconds=int(os.getenv('TASK_TIMEOUT_SECONDS', '1800')),
            test_timeout_seconds=int(os.getenv('TEST_TIMEOUT_SECONDS', '900')),
            max_output_chars=int(os.getenv('MAX_OUTPUT_CHARS', '16000')),
            protected_branches=protected,
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            openai_api_key=os.getenv('OPENAI_API_KEY', '').strip() or None,
            openai_text_model=os.getenv('OPENAI_TEXT_MODEL', 'gpt-5.6-luna').strip(),
            openai_image_model=os.getenv('OPENAI_IMAGE_MODEL', 'gpt-image-2').strip(),
            openai_image_size=os.getenv('OPENAI_IMAGE_SIZE', '1536x1024').strip(),
            openai_image_quality=os.getenv('OPENAI_IMAGE_QUALITY', 'medium').strip(),
            openai_video_model=os.getenv('OPENAI_VIDEO_MODEL', 'sora-2').strip(),
            openai_video_size=os.getenv('OPENAI_VIDEO_SIZE', '1280x720').strip(),
            openai_video_seconds=video_seconds,
            video_timeout_seconds=int(os.getenv('VIDEO_TIMEOUT_SECONDS', '900')),
        )
