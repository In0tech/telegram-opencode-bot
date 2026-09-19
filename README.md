# Telegram OpenCode Remote Bot

Безопасный Telegram-пульт для запуска **OpenCode v2** в WSL2/Linux. Бот принимает задания из Telegram, работает только с выбранным Git-репозиторием, разделяет режимы анализа/планирования/изменения кода и требует отдельного подтверждения для `git commit` и `git push`.

## Архитектура

```text
Telegram
   |
   v
Telegram OpenCode Bot (Python, WSL2)
   |
   +-- Telegram User ID allowlist
   +-- CHAT / PLAN / EXEC
   +-- project isolation
   +-- commit/push approval
   |
   v
OpenCode v2
   |
   v
~/projects/<repo>
   |
   +-- ai/* branch
   +-- tests / lint
   +-- git diff
   |
   v
GitHub
```

## Возможности

- доступ только для Telegram User ID из allowlist;
- `/projects` — список локальных Git-проектов;
- `/project NAME` — выбор проекта;
- `/chat` — анализ без изменения файлов;
- `/plan` — план изменений без редактирования;
- `/exec` — изменение кода и запуск ограниченного набора тестов/линтеров;
- обычное текстовое сообщение работает как `/chat`;
- runtime permissions OpenCode v2 через `OPENCODE_CONFIG_CONTENT`;
- запрет произвольного shell, `sudo`, package install, `git push`, `git commit`, `git merge`, `git reset`, `git clean` внутри AI-агента;
- автоматическое создание ветки `ai/YYYYMMDD-HHMMSS`, если EXEC запущен из защищённой ветки;
- `/status`, `/diff`;
- `/commit MESSAGE` и `/push` только после inline-подтверждения;
- один OpenCode task одновременно на пользователя;
- timeout выполнения;
- ограничение размера Telegram-ответов;
- systemd unit для WSL2/Linux.

## Быстрый старт

Полная пошаговая инструкция находится в [docs/INSTALL_WSL2.md](docs/INSTALL_WSL2.md).

```bash
git clone https://github.com/In0tech/telegram-opencode-bot.git
cd telegram-opencode-bot
./scripts/install.sh

nano .env
source .venv/bin/activate
python bot.py
```

После запуска в Telegram:

```text
/start
/projects
/project xenoeye
/chat Объясни архитектуру backend
/plan Добавь healthcheck и перечисли необходимые изменения
/exec Добавь healthcheck, тесты и запусти разрешённые проверки
/status
/diff
/commit feat: add healthcheck
/push
```

## Требования

- Windows 10/11 + WSL2 + Ubuntu либо обычный Debian/Ubuntu;
- Python 3.11+;
- Git;
- OpenCode v2;
- Telegram Bot Token;
- настроенный AI provider в OpenCode;
- Git credentials/SSH key, если нужен `/push`.

## Конфигурация

Создайте `.env` на основе примера:

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

Основные параметры:

```env
TELEGRAM_BOT_TOKEN=...
ALLOWED_TELEGRAM_USER_IDS=123456789
PROJECT_ROOT=/home/YOUR_USER/projects
OPENCODE_BIN=opencode
OPENCODE_MODEL=
TASK_TIMEOUT_SECONDS=1800
MAX_OUTPUT_CHARS=16000
PROTECTED_BRANCHES=main,master,production,prod
LOG_LEVEL=INFO
```

Не коммитьте `.env`. Он уже добавлен в `.gitignore`.

## Проекты

Рекомендуется хранить рабочие репозитории внутри Linux FS WSL:

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/In0tech/xenoeye.git
git clone https://github.com/In0tech/alert-centr.git
```

Бот показывает только непосредственные подкаталоги `PROJECT_ROOT`, содержащие `.git`.

## Безопасность

Режимы CHAT/PLAN не имеют права редактировать файлы. EXEC может редактировать файлы и запускать только заранее разрешённые test/lint-команды.

OpenCode не получает разрешения на `git commit` и `git push`. Эти операции выполняет сам бот после отдельного подтверждения пользователя в Telegram.

Защищённые ветки по умолчанию:

```text
main
master
production
prod
```

При `/exec` из защищённой ветки бот создаёт отдельную `ai/*` ветку.

Подробнее: [docs/SECURITY.md](docs/SECURITY.md).

## Документация

- [Установка Windows + WSL2 + Ubuntu + OpenCode + Bot](docs/INSTALL_WSL2.md)
- [Использование Telegram-команд](docs/USAGE.md)
- [Модель безопасности](docs/SECURITY.md)
- [Диагностика и типовые ошибки](docs/TROUBLESHOOTING.md)

## Тесты

```bash
source .venv/bin/activate
pip install pytest
pytest -q
```

## Важно про WSL2

Если Windows выключена или WSL остановлен, бот недоступен. Для режима 24/7 этот же проект можно перенести на Debian/Ubuntu-сервер.

## Лицензия

Внутренний проект. Репозиторий рекомендуется хранить приватным.
