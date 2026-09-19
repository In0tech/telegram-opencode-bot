# Использование Telegram OpenCode Bot

## Рекомендуемый порядок

```text
/provider
/projects
/project nabat-app-py
/chat Проанализируй архитектуру
/plan Предложи изменения
/exec Реализуй изменения и запусти тесты
/status
/diff
/commit feat: ...
/push
/pr
```

## /provider

Показывает:

- OpenCode auth;
- модели текущего провайдера;
- `OPENCODE_PROVIDER`;
- `OPENCODE_MODEL`.

Используйте эту команду первой при проблемах с моделями.

## /projects

Показывает Git-репозитории из `PROJECT_ROOT` кнопками.

## /project NAME

Выбирает проект.

```text
/project nabat-app-py
```

При выборе проекта активная именованная сессия сбрасывается на `default`.

## /chat TEXT

Анализ проекта без изменения файлов.

```text
/chat Проанализируй архитектуру
```

Обычный текст без команды также работает как `/chat`.

## /plan TEXT

Планирует изменения, не редактируя файлы.

## /exec TEXT

Может редактировать файлы и запускать разрешённые тесты/линтеры.

При запуске из защищённой ветки создаётся `ai/*`.

## Долговременные сессии

```text
/sessions
/newsession backend
/chat Проанализируй backend
/session backend
/exec Продолжи задачу
```

Session ID сохраняется в `STATE_DIR/sessions.json`.

## /tests

```text
/tests
/tests python
/tests npm
/tests pnpm
/tests go
/tests cargo
```

Запускается напрямую ботом, не через AI.

## /status и /diff

Показывают Git status и diff.

## /branch

Без аргумента показывает локальные ветки кнопками.

```text
/branch
/branch ai/fix
```

При незакоммиченных изменениях переключение блокируется.

## /commit MESSAGE

Создаёт commit только после inline-подтверждения.

## /push

Push требует отдельного подтверждения.

Push из защищённых веток запрещён.

## /pr [TITLE]

Создаёт GitHub Pull Request через `gh`.

Перед использованием:

```bash
gh auth login
```

## /rollback

Откатывает staged/unstaged изменения tracked-файлов через `git restore`.

Untracked-файлы не удаляются.

## /logs [N]

Показывает последние 10–300 строк rotating log.

## /presentation

```text
/presentation 10 | Инвесторская презентация продукта
```

Содержание генерируется через OpenCode/ChatGPT OAuth, а PPTX собирается локально через `python-pptx`.

## /email

```text
/email Напиши письмо инвестору после встречи
```

Использует OpenCode/ChatGPT OAuth.

## /tarot

```text
/tarot Что важно учитывать завтра?
/tarot 5 | Вопрос
```

Карты выбираются локально, интерпретацию выполняет OpenCode.

## /image

```text
/image Современный SOC-центр
```

Без OpenAI Platform API бот не генерирует PNG. Команда возвращает готовый промпт для ChatGPT Image.

## /video

```text
/video Кинематографичный пролёт через дата-центр
```

Без отдельного video API бот не генерирует MP4. Команда возвращает готовый промпт для ChatGPT/Sora.

## Что бот не делает автоматически

- merge;
- reset --hard;
- git clean;
- sudo;
- package install через AI-задачу;
- push без подтверждения;
- работу за пределами выбранного проекта.
