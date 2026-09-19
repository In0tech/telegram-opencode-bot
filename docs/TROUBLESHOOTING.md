# Диагностика

## opencode: command not found

Проверка:

```bash
which opencode
echo "$PATH"
```

Для OpenCode v2:

```bash
curl -fsSL https://opencode.ai/v2/install | bash
source ~/.bashrc
opencode --version
```

Либо:

```bash
npm install -g @opencode/cli
```

## curl installer не работает

Проверьте:

```bash
sudo apt update
sudo apt install -y curl ca-certificates

curl -Iv https://opencode.ai
curl -L https://opencode.ai/v2/install | head
```

Если есть TLS/DNS timeout, проблема находится ниже уровня installer: сеть, DNS, proxy/VPN/firewall или сертификаты.

## TELEGRAM_BOT_TOKEN is not set

Убедитесь, что файл существует:

```bash
cd ~/telegram-opencode-bot
ls -la .env
grep '^TELEGRAM_BOT_TOKEN=' .env
```

Не публикуйте значение token.

## ALLOWED_TELEGRAM_USER_IDS is not set

В `.env` должен находиться numeric Telegram ID:

```env
ALLOWED_TELEGRAM_USER_IDS=123456789
```

## Бот отвечает «Доступ запрещён»

Telegram User ID отправителя отсутствует в allowlist. Исправьте `.env` и перезапустите сервис:

```bash
sudo systemctl restart telegram-opencode-bot@$USER.service
```

## /projects ничего не показывает

Проверьте `PROJECT_ROOT`:

```bash
grep '^PROJECT_ROOT=' ~/telegram-opencode-bot/.env
ls -la ~/projects
```

Каждый проект должен иметь `.git`:

```bash
ls -la ~/projects/xenoeye/.git
```

## OpenCode работает вручную, но бот падает

Запустите бота foreground:

```bash
cd ~/telegram-opencode-bot
source .venv/bin/activate
python bot.py
```

Для systemd:

```bash
journalctl -u telegram-opencode-bot@$USER.service -n 200 --no-pager
```

## systemd service не запускается

Проверка:

```bash
systemctl status telegram-opencode-bot@$USER.service
journalctl -u telegram-opencode-bot@$USER.service -n 100 --no-pager
```

Убедитесь, что проект находится именно здесь:

```text
/home/YOUR_USER/telegram-opencode-bot
```

Unit template рассчитан на этот путь.

## systemctl: System has not been booted with systemd

В Ubuntu:

```bash
sudo nano /etc/wsl.conf
```

```ini
[boot]
systemd=true
```

В Windows PowerShell:

```powershell
wsl --shutdown
```

После повторного запуска Ubuntu:

```bash
systemctl status
```

## git push запрашивает пароль или завершается ошибкой

Настройте GitHub credentials через `gh auth login` либо SSH.

Проверка remote:

```bash
git remote -v
```

## EXEC создаёт новую ai/* ветку

Это ожидаемое поведение, если активная ветка входит в `PROTECTED_BRANCHES`.

Проверка:

```bash
git branch --show-current
```

## Задание превышает timeout

Увеличьте:

```env
TASK_TIMEOUT_SECONDS=3600
```

После изменения перезапустите bot/service.

## Проверка Python-тестов проекта

```bash
cd ~/telegram-opencode-bot
source .venv/bin/activate
pip install pytest
pytest -q
```


## Бот показывает один проект, а OpenCode читает другой

Симптом:

```text
Запускаю PLAN
Проект: alert-centr
```

но в выводе OpenCode появляются файлы другого репозитория, например
`telegram-opencode-bot/bot.py`, `security.py` и т. п.

Причина: OpenCode v2 по умолчанию может использовать общий background server
для локальных клиентов. Для remote-bot это нежелательно, потому что Location
общего server может относиться к ранее открывавшемуся проекту.

Начиная с исправления `f874477`, бот запускает OpenCode так:

```text
cd /absolute/path/to/project
opencode run --standalone --auto ...
```

В коде это реализовано через `asyncio.create_subprocess_exec(..., cwd=project)`,
а переменная окружения `PWD` устанавливается в тот же абсолютный путь.
Это соответствует установленной у нас версии OpenCode, где `run` поддерживает
`--standalone`, но не поддерживает `--dir`.

Обновите проект:

```bash
cd ~/telegram-opencode-bot
git pull
source .venv/bin/activate
pip install -r requirements.txt
```

Проверьте параметры вашей версии OpenCode:

```bash
opencode run --help
```

В выводе должен быть `--standalone`. Отсутствие `--dir` для этой сборки
является нормальным и уже учтено в коде бота.

После обновления перезапустите сервис:

```bash
sudo systemctl restart telegram-opencode-bot@$USER.service
journalctl -u telegram-opencode-bot@$USER.service -n 100 --no-pager
```

Проверьте вручную тот же проект:

```bash
cd ~/projects/alert-centr
pwd
git rev-parse --show-toplevel
opencode run --standalone "Покажи абсолютный путь активного проекта и перечисли 5 файлов верхнего уровня"
```

В Telegram:

```text
/project alert-centr
/plan В начале ответа укажи абсолютный путь активного проекта, затем опиши его структуру. Ничего не меняй.
```

Если путь не `~/projects/alert-centr`, проверьте:

```bash
grep '^PROJECT_ROOT=' ~/telegram-opencode-bot/.env
realpath ~/projects/alert-centr
git -C ~/projects/alert-centr rev-parse --show-toplevel
```

## В Telegram видны [0m и другие управляющие последовательности

Это ANSI/VT100-коды форматирования терминала из stdout OpenCode.
Начиная с исправления `0b62c45`, `opencode_runner.py` удаляет их перед
отправкой текста в Telegram.


## [Errno 2] No such file or directory: 'opencode'

Симптом в Telegram:

```text
Ошибка выполнения: [Errno 2] No such file or directory: 'opencode'
```

Причина: бот запущен через systemd, а PATH systemd отличается от PATH интерактивного shell. OpenCode, установленный curl/npm/pnpm/bun, часто лежит в пользовательском каталоге.

Начиная с исправления `e8b58e3`, бот автоматически ищет OpenCode в:

```text
~/.opencode/bin/opencode
~/.local/bin/opencode
~/.local/share/pnpm/opencode
~/.bun/bin/opencode
~/.npm-global/bin/opencode
/usr/local/bin/opencode
/usr/bin/opencode
```

Также обновлён systemd unit.

Сначала узнайте фактический путь:

```bash
which opencode
command -v opencode
readlink -f "$(command -v opencode)"
opencode --version
```

Если путь нестандартный, задайте его явно в `.env`:

```env
OPENCODE_BIN=/полный/путь/к/opencode
```

После обновления проекта ОБЯЗАТЕЛЬНО переустановите unit:

```bash
cd ~/telegram-opencode-bot
git pull

sudo cp systemd/telegram-opencode-bot.service \
  /etc/systemd/system/telegram-opencode-bot@.service

sudo systemctl daemon-reload
sudo systemctl restart telegram-opencode-bot@$USER.service
```

Проверьте окружение systemd:

```bash
systemctl show telegram-opencode-bot@$USER.service -p Environment
```

Проверьте лог:

```bash
journalctl -u telegram-opencode-bot@$USER.service -n 100 --no-pager
```

Если OpenCode всё ещё не находится, рекомендуется указать абсолютный путь через `OPENCODE_BIN`.


## OpenCode выбирает jev-1.13-free и зависает с Error: Transport

Симптом:

```text
> build · jev-1.13-free
> build · jev-1.13-free
...
Error: Transport
```

Это означает, что новый `opencode run` использует последнюю/fallback модель вместо OpenAI ChatGPT OAuth.

OpenCode выбирает модель в порядке: `--model`, затем `model` из config, затем последняя использованная модель, затем fallback.

После обновления бот принудительно использует провайдера из:

```env
OPENCODE_PROVIDER=openai
OPENCODE_MODEL=
```

При пустом `OPENCODE_MODEL` бот выполняет:

```bash
opencode models openai
```

и передаёт найденную модель явно через `--model openai/...`.

Для исправления обычного CLI выполните:

```bash
cd ~/telegram-opencode-bot
chmod +x scripts/configure_chatgpt_openai.sh
./scripts/configure_chatgpt_openai.sh
```

Скрипт записывает выбранную OpenAI-модель как default в:

```text
~/.config/opencode/opencode.json
```

и ограничивает автоматический выбор провайдером OpenAI.

Если скрипт не находит ни одной `openai/...` модели, сначала:

```bash
opencode
```

затем внутри:

```text
/connect
OpenAI
ChatGPT Plus/Pro
```

После OAuth:

```text
/models
```

и повторите setup script.
