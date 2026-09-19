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
