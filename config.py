from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


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
    opencode_bin: str
    opencode_model: str | None
    task_timeout_seconds: int
    max_output_chars: int
    protected_branches: frozenset[str]
    log_level: str

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

        protected = frozenset(
            x.strip() for x in os.getenv(
                'PROTECTED_BRANCHES', 'main,master,production,prod'
            ).split(',') if x.strip()
        )

        return cls(
            telegram_bot_token=token,
            allowed_user_ids=allowed,
            project_root=root,
            opencode_bin=os.getenv('OPENCODE_BIN', 'opencode').strip() or 'opencode',
            opencode_model=os.getenv('OPENCODE_MODEL', '').strip() or None,
            task_timeout_seconds=int(os.getenv('TASK_TIMEOUT_SECONDS', '1800')),
            max_output_chars=int(os.getenv('MAX_OUTPUT_CHARS', '16000')),
            protected_branches=protected,
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
        )
