from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock

SESSION_NAME_RE = re.compile(r'^[A-Za-z0-9._-]{1,40}$')


class SessionStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save(self, data: dict) -> None:
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    @staticmethod
    def validate_name(name: str) -> str:
        name = name.strip()
        if not SESSION_NAME_RE.fullmatch(name):
            raise ValueError('Имя сессии: 1-40 символов A-Z, a-z, 0-9, ., _, -')
        return name

    def list(self, user_id: int, project: str) -> dict[str, str]:
        with self._lock:
            data = self._load()
            return dict(data.get(str(user_id), {}).get(project, {}))

    def get(self, user_id: int, project: str, name: str) -> str | None:
        return self.list(user_id, project).get(name)

    def set(self, user_id: int, project: str, name: str, session_id: str) -> None:
        name = self.validate_name(name)
        with self._lock:
            data = self._load()
            user = data.setdefault(str(user_id), {})
            sessions = user.setdefault(project, {})
            sessions[name] = session_id
            self._save(data)

    def delete(self, user_id: int, project: str, name: str) -> bool:
        with self._lock:
            data = self._load()
            sessions = data.get(str(user_id), {}).get(project, {})
            if name not in sessions:
                return False
            del sessions[name]
            self._save(data)
            return True
