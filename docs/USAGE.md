# Использование Telegram OpenCode Bot

## Основной сценарий

1. Откройте Telegram-бота.
2. Выполните `/projects`.
3. Выберите проект через `/project NAME`.
4. Начните с `/chat` или `/plan`.
5. Для изменения файлов используйте `/exec`.
6. Проверьте `/status` и `/diff`.
7. Создайте commit через `/commit MESSAGE`.
8. Подтвердите push через `/push`.

## Команды

### /start и /help

Показывают справку.

### /projects

Показывает Git-репозитории из `PROJECT_ROOT`.

### /project NAME

Выбирает активный проект.

Пример:

```text
/project xenoeye
```

### /chat TEXT

Анализирует проект без изменения файлов.

Пример:

```text
/chat Почему backend может возвращать 500 при старте?
```

Обычное текстовое сообщение без команды также работает как CHAT.

### /plan TEXT

Изучает проект и формирует план, но не меняет рабочие файлы.

Пример:

```text
/plan Раздели backend API на routers/services/repositories
```

### /exec TEXT

Разрешает OpenCode редактировать файлы и выполнять ограниченный набор test/lint-команд.

Если текущая ветка входит в список защищённых, бот автоматически создаст:

```text
ai/YYYYMMDD-HHMMSS
```

Пример:

```text
/exec Исправь Docker build frontend и запусти существующие тесты
```

### /status

Выполняет безопасный `git status --short --branch`.

### /diff

Показывает staged и unstaged diff.

### /commit MESSAGE

Готовит commit всех текущих изменений через `git add -A`, но выполняет commit только после нажатия кнопки подтверждения.

Пример:

```text
/commit fix: repair frontend docker build
```

### /push

Показывает подтверждение перед:

```text
git push -u origin CURRENT_BRANCH
```

Push из защищённых веток запрещён.

### /cancel

Удаляет ожидающее подтверждение commit/push.

## Рекомендуемый рабочий процесс

```text
/project alert-centr

/plan Найди причину падения backend и предложи исправление

/exec Исправь найденную проблему и запусти тесты

/status

/diff

/commit fix: resolve backend startup failure

/push
```

## Что бот не делает автоматически

- не выполняет merge;
- не делает reset/clean;
- не устанавливает apt/npm/pip пакеты через AI-задачу;
- не выполняет произвольные shell-команды;
- не пушит код без отдельного подтверждения;
- не работает с каталогами вне выбранного проекта.


## Интерактивный выбор проекта

`/projects` показывает inline-кнопки. Нажатие кнопки выбирает проект и сбрасывает активное имя OpenCode-сессии на `default`.

## Долговременные OpenCode-сессии

```text
/sessions
/newsession backend
/chat Проанализируй backend
/session backend
/exec Продолжи предыдущую задачу
```

Сессии именованные, хранятся отдельно для пары «Telegram user + project» и переживают перезапуск бота. Session ID сохраняется в `STATE_DIR/sessions.json`.

## /tests

Автоматически определяет test runner либо принимает явный тип:

```text
/tests
/tests python
/tests npm
/tests pnpm
/tests go
/tests cargo
```

Команда запускается напрямую ботом в рабочем каталоге проекта, а не через AI.

## /logs [N]

Показывает последние строки собственного rotating log бота. Диапазон: 10–300 строк.

```text
/logs
/logs 200
```

## /branch [NAME]

Без аргумента показывает локальные ветки кнопками. С аргументом переключает ветку:

```text
/branch
/branch ai/backend-fix
```

При наличии незакоммиченных изменений переключение блокируется.

## /rollback

Требует отдельного подтверждения. Выполняет восстановление tracked-файлов до `HEAD` через `git restore --staged --worktree -- .`.

Важно: untracked-файлы намеренно не удаляются. `git reset --hard` и `git clean` не используются.

## /pr [TITLE]

Создаёт Pull Request для текущей нез защищённой ветки через GitHub CLI.

```text
/push
/pr
```

или:

```text
/pr fix: backend startup
```

Если PR для ветки уже существует, бот возвращает его URL. Перед использованием настройте:

```bash
gh auth login
```


## Творческие команды

Подробно: [CREATIVE_FEATURES.md](CREATIVE_FEATURES.md)

### /presentation

```text
/presentation 10 | Тема презентации
```

Создаёт и отправляет редактируемый PowerPoint.

### /image

```text
/image Описание изображения
```

Создаёт PNG через OpenAI Image API.

### /video

```text
/video Описание ролика
```

Создаёт MP4 через текущий OpenAI Video API. Sora API объявлен deprecated и запланирован к отключению 24.09.2026.

### /email

```text
/email Что должно быть в письме
```

Возвращает готовую тему и текст письма.

### /tarot

```text
/tarot Вопрос
/tarot 5 | Вопрос
```

Делает случайный расклад 1–10 карт и возвращает символическую AI-интерпретацию.
