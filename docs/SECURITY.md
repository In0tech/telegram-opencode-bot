# Модель безопасности

Telegram-бот является удалённым интерфейсом к локальной машине, поэтому проект использует несколько независимых уровней ограничений.

## 1. Telegram allowlist

Запрос выполняется только если `update.effective_user.id` присутствует в:

```env
ALLOWED_TELEGRAM_USER_IDS=...
```

Не используйте username вместо numeric User ID.

## 2. Изоляция проектов

Бот работает только с непосредственными дочерними каталогами `PROJECT_ROOT`.

Имя проекта допускает только:

```text
A-Z a-z 0-9 . _ -
```

Пути вида `../etc` отклоняются.

Выбранный каталог обязан содержать `.git`.

## 3. Разделение CHAT / PLAN / EXEC

CHAT и PLAN:

- чтение разрешено;
- glob/grep разрешены;
- edit запрещён;
- generic shell запрещён;
- разрешены отдельные read-only Git-команды.

EXEC:

- редактирование разрешено;
- generic shell всё равно запрещён;
- разрешён ограниченный набор тестов и линтеров.

## 4. OpenCode runtime permissions

Перед каждым запуском бот формирует `OPENCODE_CONFIG_CONTENT`.

Для OpenCode v2 используются ordered `permissions` rules.

Generic shell сначала блокируется:

```json
{
  "action": "shell",
  "resource": "*",
  "effect": "deny"
}
```

После него добавляются только конкретные исключения.

Разрешённые примеры:

```text
git status
git diff
git log
git branch
pytest
python -m pytest
npm test
npm run test
npm run lint
pnpm test
pnpm lint
go test
cargo test
```

## 5. Git commit и push отделены от AI-агента

OpenCode не получает разрешение выполнять commit/push.

Commit делает Python-бот только после Telegram confirmation.

Push делает Python-бот только после отдельного Telegram confirmation.

## 6. Защищённые ветки

По умолчанию:

```env
PROTECTED_BRANCHES=main,master,production,prod
```

EXEC из такой ветки сначала создаёт `ai/*` branch.

Commit/push из защищённой ветки блокируется ботом.

## 7. Секреты

Файл `.env`:

- находится в `.gitignore`;
- должен иметь mode 600;
- не должен пересылаться в Telegram;
- не должен коммититься.

Рекомендуется:

```bash
chmod 600 ~/telegram-opencode-bot/.env
```

Если Telegram Bot Token был раскрыт, немедленно перевыпустите его через BotFather.

## 8. OpenCode Server наружу не требуется

Текущая версия бота запускает `opencode run` локально. Порт OpenCode Server открывать не требуется.

Это уменьшает поверхность атаки.

## 9. Остаточный риск

Даже ограниченный coding agent может изменить код в EXEC-режиме. Поэтому перед commit используйте:

```text
/status
/diff
```

и проверяйте изменения.

Для production-репозиториев рекомендуется дополнительно использовать GitHub branch protection и Pull Request workflow.
