# Диагностика

## Быстрый чек

```bash
cd ~/telegram-opencode-bot

git status
git log --oneline -5

command -v opencode
opencode --version
opencode auth list
opencode models

systemctl status telegram-opencode-bot@$USER.service
journalctl -u telegram-opencode-bot@$USER.service -n 100 --no-pager
```

В Telegram:

```text
/provider
```

## [Errno 2] No such file or directory: opencode

Причина: systemd не видел пользовательский `PATH`.

Бот умеет искать OpenCode в:

```text
~/.opencode/bin/opencode
~/.local/bin/opencode
~/.local/share/pnpm/opencode
~/.bun/bin/opencode
~/.npm-global/bin/opencode
/usr/local/bin/opencode
/usr/bin/opencode
```

Для максимальной надёжности:

```env
OPENCODE_BIN=/home/YOUR_USER/.opencode/bin/opencode
```

После обновления unit:

```bash
sudo cp systemd/telegram-opencode-bot.service \
  /etc/systemd/system/telegram-opencode-bot@.service
sudo systemctl daemon-reload
sudo systemctl restart telegram-opencode-bot@$USER.service
```

## opencode models openai → Unexpected positional argument

В старой версии OpenCode это ожидаемо.

Не используйте:

```bash
opencode models openai
```

Используйте:

```bash
opencode models
```

Бот сам фильтрует строки `openai/...`.

## OpenCode выбирает jev-1.13-free

Симптом:

```text
> build · jev-1.13-free
...
Error: Transport
```

Причина: OpenCode использует последнюю/fallback модель вместо OpenAI.

Исправление:

```bash
cd ~/telegram-opencode-bot
git pull
chmod +x scripts/configure_chatgpt_openai.sh
./scripts/configure_chatgpt_openai.sh
```

В `.env`:

```env
OPENCODE_PROVIDER=openai
OPENCODE_MODEL=
```

## credit_balance_exhausted

Симптом:

```text
credit_balance_exhausted
You have no credits remaining
```

Это означает, что используется credit/API provider, а не ChatGPT account OAuth.

Проверьте:

```bash
opencode auth list
```

Если OpenAI не подключён:

```text
opencode
/connect
OpenAI
ChatGPT Plus/Pro
```

OpenAI Platform API key этому проекту не нужен.

## gpt-5.3-codex-spark is not supported with a ChatGPT account

Модель присутствует в списке, но недоступна для текущего ChatGPT-account режима.

Новая логика не выбирает первую модель вслепую. Бот и setup-скрипт пробуют модели по очереди и выбирают первую реально рабочую.

## Telegram: rc=78 и «нет моделей openai/*»

Если в shell:

```bash
opencode models
```

показывает `openai/*`, а Telegram нет — проблема была в runtime config/systemd environment.

Исправления:

- discovery моделей идёт без `OPENCODE_CONFIG_CONTENT`;
- OAuth discovery использует реальные `HOME/XDG_*`;
- systemd unit явно задаёт:

```text
HOME=/home/%i
XDG_CONFIG_HOME=/home/%i/.config
XDG_DATA_HOME=/home/%i/.local/share
XDG_STATE_HOME=/home/%i/.local/state
```

После обновления обязательно:

```bash
sudo cp systemd/telegram-opencode-bot.service \
  /etc/systemd/system/telegram-opencode-bot@.service
sudo systemctl daemon-reload
sudo systemctl restart telegram-opencode-bot@$USER.service
```

Проверка окружения:

```bash
systemctl show telegram-opencode-bot@$USER.service -p Environment
```

## OpenCode работает в shell, но не в systemd

Проверьте от имени того же пользователя:

```bash
sudo -u "$USER" env \
  HOME="$HOME" \
  XDG_CONFIG_HOME="$HOME/.config" \
  XDG_DATA_HOME="$HOME/.local/share" \
  XDG_STATE_HOME="$HOME/.local/state" \
  "$(command -v opencode)" auth list
```

и:

```bash
sudo -u "$USER" env \
  HOME="$HOME" \
  XDG_CONFIG_HOME="$HOME/.config" \
  XDG_DATA_HOME="$HOME/.local/share" \
  XDG_STATE_HOME="$HOME/.local/state" \
  "$(command -v opencode)" models
```

## Бот показывает другой проект

OpenCode запускается через `--standalone`, `cwd=project` и `PWD=project`.

Не добавляйте `--dir`: ваша версия OpenCode его не поддерживает.

## Git pull блокируется локальными изменениями

```bash
git status
git stash push -m "local changes"
git pull
```

Не возвращайте stash автоматически, если upstream уже содержит исправленную версию того же файла.

## Логи

```bash
journalctl -u telegram-opencode-bot@$USER.service -n 200 --no-pager
```

или в Telegram:

```text
/logs 200
```
