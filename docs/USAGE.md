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
