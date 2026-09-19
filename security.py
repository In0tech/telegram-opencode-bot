from __future__ import annotations

import json

# OpenCode v2 runtime rules. Generic shell access is denied. Read-only Git
# inspection and a narrow set of test/lint commands are explicitly allowed.
# Commit/push are performed by this bot only after Telegram confirmation.

READ_ONLY_PERMISSIONS = [
    {'action': 'read', 'resource': '*', 'effect': 'allow'},
    {'action': 'glob', 'resource': '*', 'effect': 'allow'},
    {'action': 'grep', 'resource': '*', 'effect': 'allow'},
    {'action': 'edit', 'resource': '*', 'effect': 'deny'},
    {'action': 'shell', 'resource': '*', 'effect': 'deny'},
    {'action': 'shell', 'resource': 'git status *', 'effect': 'allow'},
    {'action': 'shell', 'resource': 'git diff *', 'effect': 'allow'},
    {'action': 'shell', 'resource': 'git log *', 'effect': 'allow'},
    {'action': 'shell', 'resource': 'git branch *', 'effect': 'allow'},
]

EXEC_PERMISSIONS = READ_ONLY_PERMISSIONS + [
    {'action': 'edit', 'resource': '*', 'effect': 'allow'},
    {'action': 'shell', 'resource': 'pytest *', 'effect': 'allow'},
    {'action': 'shell', 'resource': 'python -m pytest *', 'effect': 'allow'},
    {'action': 'shell', 'resource': 'python3 -m pytest *', 'effect': 'allow'},
    {'action': 'shell', 'resource': 'npm test *', 'effect': 'allow'},
    {'action': 'shell', 'resource': 'npm run test *', 'effect': 'allow'},
    {'action': 'shell', 'resource': 'npm run lint *', 'effect': 'allow'},
    {'action': 'shell', 'resource': 'pnpm test *', 'effect': 'allow'},
    {'action': 'shell', 'resource': 'pnpm lint *', 'effect': 'allow'},
    {'action': 'shell', 'resource': 'go test *', 'effect': 'allow'},
    {'action': 'shell', 'resource': 'cargo test *', 'effect': 'allow'},
]


def opencode_config(mode: str) -> str:
    permissions = EXEC_PERMISSIONS if mode == 'exec' else READ_ONLY_PERMISSIONS
    cfg = {
        '$schema': 'https://opencode.ai/config.json',
        'permissions': permissions,
    }
    return json.dumps(cfg, ensure_ascii=False)


def system_instruction(mode: str) -> str:
    common = (
        'Ты работаешь как удалённый AI-разработчик через Telegram. '
        'Отвечай на русском языке. Работай только внутри текущего проекта. '
        'Никогда не пытайся обходить ограничения permissions. '
        'Не выполняй git commit, git push, git merge, git reset, git clean, sudo, '
        'установку пакетов или удаление данных. В конце дай краткое резюме, список '
        'изменённых файлов и результаты тестов, если они запускались.'
    )
    if mode == 'chat':
        return common + ' Режим CHAT: только объясняй и анализируй; ничего не меняй.'
    if mode == 'plan':
        return common + ' Режим PLAN: изучи проект и составь план; ничего не меняй.'
    return common + ' Режим EXEC: разрешено редактировать файлы и запускать только разрешённые тесты/линтеры.'
