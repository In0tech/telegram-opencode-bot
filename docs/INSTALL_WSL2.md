# Установка Telegram OpenCode Bot в Windows + WSL2

Инструкция рассчитана на Windows 10/11 + WSL2 + Ubuntu.

## 1. Проверить WSL2

В PowerShell:

```powershell
wsl --status
wsl -l -v
```

Для Ubuntu должна использоваться VERSION 2.

Если WSL не установлен:

```powershell
wsl --install
```

После перезагрузки:

```powershell
wsl -d Ubuntu
```

## 2. Пакеты Ubuntu

```bash
sudo apt update
sudo apt upgrade -y

sudo apt install -y \
  git \
  curl \
  ca-certificates \
  python3 \
  python3-venv \
  python3-pip \
  jq \
  gh
```

## 3. Установить OpenCode

Установите OpenCode удобным для вашей версии способом и проверьте:

```bash
command -v opencode
opencode --version
```

Если OpenCode лежит в пользовательском каталоге, это нормально. Бот ищет его в типичных путях, включая:

```text
~/.opencode/bin/opencode
~/.local/bin/opencode
~/.local/share/pnpm/opencode
~/.bun/bin/opencode
~/.npm-global/bin/opencode
/usr/local/bin/opencode
/usr/bin/opencode
```

Для максимальной предсказуемости можно задать абсолютный путь в `.env`.

## 4. Подключить OpenAI через ChatGPT Plus/Pro OAuth

Запустите:

```bash
opencode
```

Внутри OpenCode:

```text
/connect
```

Выберите:

```text
OpenAI
ChatGPT Plus/Pro
```

После browser OAuth проверьте:

```bash
opencode auth list
```

Ожидается запись OpenAI со статусом `stored`.

Проверьте список моделей:

```bash
opencode models
```

Важно: в вашей/старой версии OpenCode `opencode models openai` может завершаться ошибкой `Unexpected positional argument`. Проект специально использует только `opencode models`.

## 5. Клонировать бот

```bash
cd ~
git clone https://github.com/In0tech/telegram-opencode-bot.git
cd telegram-opencode-bot
```

## 6. Установить Python environment

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

Или вручную:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 7. Настроить рабочую OpenAI-модель

После OAuth выполните:

```bash
chmod +x scripts/configure_chatgpt_openai.sh
./scripts/configure_chatgpt_openai.sh
```

Скрипт:

1. выполняет `opencode auth list`;
2. получает `opencode models`;
3. фильтрует `openai/...`;
4. по очереди тестирует модели через короткий `opencode run --model ...`;
5. пропускает неподдерживаемые модели вроде некоторых `codex-*`;
6. выбирает первую реально рабочую модель;
7. записывает её в:

```text
~/.config/opencode/opencode.json
```

Пример:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "openai/gpt-5.6-sol"
}
```

Реальная выбранная модель зависит от доступности для вашего аккаунта.

## 8. Проверить OpenCode вручную

```bash
cd ~/projects/nabat-app-py

opencode run \
  --standalone \
  "Ответь одним словом: OK"
```

Если снова появляется `jev-1.13-free`, см. [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## 9. Создать Telegram Bot

В Telegram используйте `@BotFather`:

```text
/newbot
```

Сохраните token.

## 10. Настроить .env

```bash
cd ~/telegram-opencode-bot
cp .env.example .env
chmod 600 .env
nano .env
```

Пример:

```env
TELEGRAM_BOT_TOKEN=1234567890:replace_me
ALLOWED_TELEGRAM_USER_IDS=123456789

PROJECT_ROOT=/home/YOUR_USER/projects
STATE_DIR=/home/YOUR_USER/.local/state/telegram-opencode-bot

OPENCODE_BIN=/home/YOUR_USER/.opencode/bin/opencode
OPENCODE_PROVIDER=openai
OPENCODE_MODEL=

TASK_TIMEOUT_SECONDS=1800
TEST_TIMEOUT_SECONDS=900
MAX_OUTPUT_CHARS=16000

PROTECTED_BRANCHES=main,master,production,prod
LOG_LEVEL=INFO
```

Если `OPENCODE_MODEL` пустой, бот сам подберёт рабочую модель через probe.

## 11. Каталог проектов

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/In0tech/nabat-app-py.git
```

Проект должен содержать `.git`.

## 12. Ручной запуск

```bash
cd ~/telegram-opencode-bot
source .venv/bin/activate
python bot.py
```

В Telegram:

```text
/provider
/projects
/project nabat-app-py
/chat Проанализируй архитектуру
```

## 13. systemd

Установите unit:

```bash
cd ~/telegram-opencode-bot

sudo cp systemd/telegram-opencode-bot.service \
  /etc/systemd/system/telegram-opencode-bot@.service

sudo systemctl daemon-reload
sudo systemctl enable --now telegram-opencode-bot@$USER.service
```

Unit задаёт:

```text
HOME=/home/%i
XDG_CONFIG_HOME=/home/%i/.config
XDG_DATA_HOME=/home/%i/.local/share
XDG_STATE_HOME=/home/%i/.local/state
```

Это важно: OpenCode OAuth и config должны быть видны systemd точно так же, как вашему shell.

Проверка:

```bash
systemctl status telegram-opencode-bot@$USER.service
systemctl show telegram-opencode-bot@$USER.service -p Environment
```

Логи:

```bash
journalctl -u telegram-opencode-bot@$USER.service -n 100 --no-pager
```

## 14. Обновление

```bash
cd ~/telegram-opencode-bot

git pull

source .venv/bin/activate
pip install -r requirements.txt

sudo cp systemd/telegram-opencode-bot.service \
  /etc/systemd/system/telegram-opencode-bot@.service

sudo systemctl daemon-reload
sudo systemctl restart telegram-opencode-bot@$USER.service
```

Если `git pull` блокируется локальными изменениями:

```bash
git status
git stash push -m "local changes"
git pull
```

Не делайте `stash pop` автоматически поверх файлов, которые были исправлены в upstream.

## 15. Проверка после обновления

В shell:

```bash
opencode auth list
opencode models
```

В Telegram:

```text
/provider
/project nabat-app-py
/chat Проанализируй архитектуру
```
