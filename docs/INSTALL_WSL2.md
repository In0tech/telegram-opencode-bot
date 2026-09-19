# Установка Telegram OpenCode Bot в Windows + WSL2

Эта инструкция рассчитана на Windows 10/11, WSL2 и Ubuntu. Windows остаётся основной рабочей системой, а Telegram Bot и OpenCode работают внутри Ubuntu/WSL2.

## 1. Проверка WSL2

Откройте PowerShell от имени администратора:

```powershell
wsl --status
wsl -l -v
```

У Ubuntu в колонке VERSION должно быть `2`.

Если WSL ещё не установлен:

```powershell
wsl --install
```

После установки перезагрузите Windows и откройте Ubuntu через меню Пуск либо:

```powershell
wsl -d Ubuntu
```

## 2. Обновление Ubuntu

В Ubuntu:

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
  jq \\\n  gh
```

Проверка:

```bash
python3 --version
git --version
curl --version
```

## 3. Установка OpenCode v2

Рекомендуемый вариант для OpenCode v2:

```bash
curl -fsSL https://opencode.ai/v2/install | bash
```

Затем перезапустите shell либо выполните:

```bash
source ~/.bashrc
```

Проверка:

```bash
opencode --version
```

Альтернативная установка через npm:

```bash
npm install -g @opencode/cli
```

Перед использованием бота обязательно проверьте OpenCode вручную:

```bash
mkdir -p ~/projects/opencode-test
cd ~/projects/opencode-test
git init
echo 'print("hello")' > hello.py

opencode run "Проанализируй hello.py и кратко объясни, что он делает"
```

Если эта команда не работает, сначала исправьте конфигурацию OpenCode/provider.

## 4. Настройка AI provider в OpenCode

Запустите:

```bash
opencode
```

Используйте штатный интерфейс OpenCode для подключения нужного provider/model. Бот использует конфигурацию и авторизацию того же Linux-пользователя.

После настройки повторите:

```bash
opencode run "Ответь одним словом: OK"
```

## 5. Создание Telegram-бота

В Telegram откройте официального `@BotFather`.

Выполните:

```text
/newbot
```

Задайте имя и username бота. BotFather вернёт token вида:

```text
1234567890:AA...
```

Этот token является секретом. Не публикуйте его и не добавляйте в Git.

## 6. Получение Telegram User ID

Нужен числовой Telegram User ID владельца бота. Его можно получить через специализированного ID-бота в Telegram либо временным диагностическим скриптом.

После получения ID добавьте его в `ALLOWED_TELEGRAM_USER_IDS`.

Несколько пользователей можно указать через запятую:

```env
ALLOWED_TELEGRAM_USER_IDS=123456789,987654321
```

## 7. Клонирование проекта

В Ubuntu:

```bash
cd ~
git clone https://github.com/In0tech/telegram-opencode-bot.git
cd telegram-opencode-bot
```

Проверьте:

```bash
git status
ls -la
```

## 8. Автоматическая установка Python-окружения

Сделайте installer исполняемым:

```bash
chmod +x scripts/install.sh
```

Запустите:

```bash
./scripts/install.sh
```

Скрипт:

1. проверяет наличие Python, Git и OpenCode;
2. создаёт `.venv`;
3. обновляет pip;
4. устанавливает зависимости;
5. создаёт `.env` из `.env.example`, если файла ещё нет.

## 9. Настройка .env

Откройте:

```bash
nano .env
```

Пример:

```env
TELEGRAM_BOT_TOKEN=1234567890:replace_me
ALLOWED_TELEGRAM_USER_IDS=123456789
PROJECT_ROOT=/home/YOUR_USER/projects
OPENCODE_BIN=opencode
OPENCODE_MODEL=
TASK_TIMEOUT_SECONDS=1800
TEST_TIMEOUT_SECONDS=900
MAX_OUTPUT_CHARS=16000
STATE_DIR=/home/YOUR_USER/.local/state/telegram-opencode-bot
PROTECTED_BRANCHES=main,master,production,prod
LOG_LEVEL=INFO
```

Узнать имя пользователя:

```bash
whoami
echo "$HOME"
```

Например:

```env
PROJECT_ROOT=/home/andrey/projects
```

Ограничьте доступ к секретам:

```bash
chmod 600 .env
```

## 10. Подготовка каталога проектов

Рекомендуется хранить рабочие репозитории непосредственно внутри файловой системы WSL:

```bash
mkdir -p ~/projects
cd ~/projects
```

Пример:

```bash
git clone https://github.com/In0tech/xenoeye.git
git clone https://github.com/In0tech/alert-centr.git
```

Структура:

```text
/home/YOUR_USER/
├── telegram-opencode-bot/
└── projects/
    ├── xenoeye/
    ├── alert-centr/
    └── ...
```

Бот видит только Git-репозитории, находящиеся непосредственно в `PROJECT_ROOT`.

## 11. Первый ручной запуск

```bash
cd ~/telegram-opencode-bot
source .venv/bin/activate
python bot.py
```

При успешном запуске процесс остаётся активным и ожидает Telegram updates.

Откройте бота и выполните:

```text
/start
/projects
```

Затем:

```text
/project xenoeye
```

Тест безопасного анализа:

```text
/chat Покажи структуру проекта и объясни назначение основных модулей
```

Тест планирования:

```text
/plan Добавь healthcheck endpoint. Пока ничего не меняй.
```

Тест изменения кода:

```text
/exec Добавь healthcheck endpoint и тесты
```

## 12. Проверка изменений

После EXEC:

```text
/status
/diff
```

Если результат устраивает:

```text
/commit feat: add healthcheck endpoint
```

Бот покажет кнопку подтверждения.

После commit:

```text
/push
```

Push также требует отдельного подтверждения.

## 13. GitHub authentication для push

Если репозитории используют HTTPS, настройте `gh`:

```bash
gh auth login
```

Либо используйте SSH:

```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
cat ~/.ssh/id_ed25519.pub
```

Добавьте публичный ключ в GitHub и проверьте:

```bash
ssh -T git@github.com
```

Remote проекта при SSH должен выглядеть примерно так:

```bash
git remote -v
```

```text
origin  git@github.com:In0tech/xenoeye.git
```

## 14. Автозапуск через systemd

На новых Ubuntu под WSL systemd обычно уже доступен.

Проверьте:

```bash
systemctl status
```

Если systemd не работает, откройте:

```bash
sudo nano /etc/wsl.conf
```

Добавьте:

```ini
[boot]
systemd=true
```

Затем в Windows PowerShell:

```powershell
wsl --shutdown
```

Снова откройте Ubuntu.

Установите unit:

```bash
cd ~/telegram-opencode-bot

sudo cp systemd/telegram-opencode-bot.service \
  /etc/systemd/system/telegram-opencode-bot@.service

sudo systemctl daemon-reload
sudo systemctl enable --now telegram-opencode-bot@$USER.service

# После каждого обновления systemd unit из Git:
# sudo cp systemd/telegram-opencode-bot.service /etc/systemd/system/telegram-opencode-bot@.service
# sudo systemctl daemon-reload
# sudo systemctl restart telegram-opencode-bot@$USER.service
```

Проверка:

```bash
systemctl status telegram-opencode-bot@$USER.service
```

Логи:

```bash
journalctl -u telegram-opencode-bot@$USER.service -f
```

Перезапуск после изменения `.env` или кода:

```bash
sudo systemctl restart telegram-opencode-bot@$USER.service
```

## 15. Обновление бота

```bash
cd ~/telegram-opencode-bot
git pull

source .venv/bin/activate
pip install -r requirements.txt

sudo systemctl restart telegram-opencode-bot@$USER.service
```

## 16. Проверка тестов

```bash
cd ~/telegram-opencode-bot
source .venv/bin/activate
pip install pytest
pytest -q
```

## 17. Что происходит после перезагрузки Windows

Если Ubuntu/WSL не запущен, Telegram-бот может быть недоступен. WSL — не полноценный отдельный 24/7 сервер.

Если вам нужен постоянный доступ независимо от рабочего ПК, перенесите проект на постоянно включённый Debian/Ubuntu сервер.


## GitHub CLI для /pr

Проверьте:

```bash
gh --version
```

Авторизуйте GitHub CLI:

```bash
gh auth login
gh auth status
```

Команда `/pr` использует эту авторизацию. Если рабочие репозитории приватные, убедитесь, что выбранный аккаунт имеет к ним доступ.

## Persistent state

По умолчанию состояние хранится здесь:

```text
~/.local/state/telegram-opencode-bot/
├── sessions.json
├── bot.log
├── bot.log.1
└── ...
```

Путь можно изменить:

```env
STATE_DIR=/home/YOUR_USER/.local/state/telegram-opencode-bot
TEST_TIMEOUT_SECONDS=900
```


## Настройка творческих функций

После обновления зависимостей:

```bash
cd ~/telegram-opencode-bot
source .venv/bin/activate
pip install -r requirements.txt
```

Добавьте API key в `.env`:

```env
OPENAI_API_KEY=sk-...
```

Проверьте, что ключ не попал в Git:

```bash
git status --ignored
```

Перезапустите бота:

```bash
sudo systemctl restart telegram-opencode-bot@$USER.service
```

Затем проверьте:

```text
/email Напиши короткое тестовое письмо
/tarot Общий расклад на день
/image Минималистичный футуристичный серверный зал
/presentation 5 | Тестовая презентация про кибербезопасность
```

Команда `/video` использует deprecated Sora API, который OpenAI планирует отключить 24.09.2026.


## OpenCode и systemd PATH

После установки OpenCode проверьте абсолютный путь:

```bash
command -v opencode
readlink -f "$(command -v opencode)"
```

Бот автоматически ищет OpenCode в популярных пользовательских каталогах. Для максимальной предсказуемости можно записать абсолютный путь в `.env`:

```env
OPENCODE_BIN=/home/YOUR_USER/.opencode/bin/opencode
```

Если `command -v opencode` показывает другой путь — используйте именно его.

После изменения unit-файла из репозитория недостаточно обычного restart; сначала скопируйте новый unit и выполните `daemon-reload`.
