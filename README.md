# Telegram OpenCode Remote Bot

Telegram-пульт для безопасной работы с локальными Git-проектами через OpenCode в WSL2/Linux.

Основной режим работы — **OpenCode + OpenAI OAuth через ChatGPT Plus/Pro**, без `OPENAI_API_KEY` и без OpenAI Platform credits.

## Что умеет бот

- доступ только для Telegram User ID из allowlist;
- выбор локального Git-проекта через `/projects` и `/project`;
- `/chat` — анализ без изменений;
- `/plan` — план без изменений;
- `/exec` — изменение файлов с ограниченными permissions;
- именованные долговременные OpenCode-сессии;
- `/tests`, `/status`, `/diff`, `/logs`;
- `/branch`, `/rollback`;
- `/commit` и `/push` только после подтверждения;
- `/pr` через GitHub CLI;
- `/provider` — диагностика OpenCode OAuth и доступных моделей;
- `/presentation` — редактируемый PowerPoint;
- `/email` — готовое письмо;
- `/tarot` — расклад и интерпретация;
- `/image` — готовый промпт для ChatGPT Image;
- `/video` — готовый промпт для ChatGPT/Sora.

## Архитектура

```text
Telegram
   |
   v
Telegram OpenCode Bot
   |
   +-- allowlist
   +-- project/session state
   +-- CHAT / PLAN / EXEC
   +-- tests / git / PR
   +-- presentation / email / tarot
   |
   v
OpenCode
   |
   +-- OpenAI OAuth (ChatGPT Plus/Pro)
   +-- model discovery + compatibility probe
   +-- --standalone
   |
   v
~/projects/<repo>
```

## Важно про OpenAI

Бот **не использует OpenAI Platform API**.

Не нужны:

```env
OPENAI_API_KEY=
```

и отдельный API balance.

OpenCode должен быть подключён к OpenAI через ChatGPT account OAuth:

```text
opencode
/connect
OpenAI
ChatGPT Plus/Pro
```

Проверка:

```bash
opencode auth list
opencode models
```

В старых версиях OpenCode команда:

```bash
opencode models openai
```

может не поддерживаться. Поэтому проект использует совместимый вариант:

```bash
opencode models
```

и фильтрует `openai/...` самостоятельно.

## Автоматический выбор модели

Если:

```env
OPENCODE_MODEL=
```

бот:

1. выполняет `opencode models`;
2. фильтрует модели `openai/...`;
3. предпочитает обычные ChatGPT-модели;
4. запускает короткий probe каждой подходящей модели;
5. выбирает первую реально рабочую для текущего ChatGPT OAuth;
6. всегда передаёт модель через `--model`.

Это защищает от автоматического отката OpenCode на `jev-1.13-free`, OpenCode Zen или неподдерживаемую `codex-*` модель.

## Быстрый старт

```bash
git clone https://github.com/In0tech/telegram-opencode-bot.git
cd telegram-opencode-bot

chmod +x scripts/install.sh
./scripts/install.sh
```

Настройте OpenAI OAuth:

```bash
opencode
```

внутри:

```text
/connect
OpenAI
ChatGPT Plus/Pro
```

Затем:

```bash
chmod +x scripts/configure_chatgpt_openai.sh
./scripts/configure_chatgpt_openai.sh
```

Скрипт найдёт реально рабочую OpenAI-модель и запишет её в глобальный config OpenCode.

## .env

Минимальный пример:

```env
TELEGRAM_BOT_TOKEN=1234567890:replace_me
ALLOWED_TELEGRAM_USER_IDS=123456789

PROJECT_ROOT=/home/YOUR_USER/projects
STATE_DIR=/home/YOUR_USER/.local/state/telegram-opencode-bot

OPENCODE_BIN=opencode
OPENCODE_PROVIDER=openai
OPENCODE_MODEL=

TASK_TIMEOUT_SECONDS=1800
TEST_TIMEOUT_SECONDS=900
MAX_OUTPUT_CHARS=16000

PROTECTED_BRANCHES=main,master,production,prod
LOG_LEVEL=INFO
```

## systemd

После изменения unit-файла из Git недостаточно обычного restart.

Используйте:

```bash
sudo cp systemd/telegram-opencode-bot.service \
  /etc/systemd/system/telegram-opencode-bot@.service

sudo systemctl daemon-reload
sudo systemctl restart telegram-opencode-bot@$USER.service
```

Unit явно задаёт:

```text
HOME=/home/%i
XDG_CONFIG_HOME=/home/%i/.config
XDG_DATA_HOME=/home/%i/.local/share
XDG_STATE_HOME=/home/%i/.local/state
```

Это нужно, чтобы systemd видел те же OpenCode OAuth credentials и config, что и интерактивный shell.

## Основные команды

```text
/start
/provider
/projects
/project NAME
/chat TEXT
/plan TEXT
/exec TEXT
/sessions
/newsession NAME
/session NAME
/tests
/status
/diff
/branch
/commit MESSAGE
/push
/pr
/rollback
/logs
/presentation 10 | ТЕМА
/email ЗАДАНИЕ
/tarot 3 | ВОПРОС
/image ОПИСАНИЕ
/video ОПИСАНИЕ
```

## Документация

- [Установка Windows + WSL2](docs/INSTALL_WSL2.md)
- [Использование команд](docs/USAGE.md)
- [Диагностика](docs/TROUBLESHOOTING.md)
- [Модель безопасности](docs/SECURITY.md)
- [Творческие функции](docs/CREATIVE_FEATURES.md)

## Тесты

```bash
source .venv/bin/activate
pip install pytest
pytest -q
```
