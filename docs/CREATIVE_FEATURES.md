# Творческие возможности без OpenAI API

Бот больше не использует OpenAI Platform API и не требует `OPENAI_API_KEY`.

Все текстовые AI-задачи выполняются через OpenCode. Для OpenAI рекомендуется авторизовать OpenCode через подписку **ChatGPT Plus/Pro**:

```text
opencode
/connect
OpenAI
ChatGPT Plus/Pro
/models
```

После этого оставьте в `.env`:

```env
OPENCODE_MODEL=
```

чтобы бот использовал выбранную/настроенную в OpenCode модель.

## /presentation

Создаёт редактируемый PowerPoint (.pptx).

Содержание генерируется через OpenCode/ChatGPT, а сам файл собирается локально через `python-pptx`.

```text
/presentation 10 | Инвесторская презентация AI Cyber Defense Copilot
```

API credits не используются.

## /email

Письмо создаётся через тот же OpenCode/ChatGPT-сеанс:

```text
/email Напиши письмо инвестору после встречи
```

## /tarot

Карты вытягиваются локально из полной колоды 78 карт, а интерпретация выполняется через OpenCode/ChatGPT:

```text
/tarot 3 | Что важно учитывать завтра?
```

## /image

OpenCode умеет передавать изображения модели как вход, но его документированная модель вывода — текст. Поэтому без отдельного image API бот не может честно получить готовый PNG из ChatGPT Plus/Pro через OpenCode.

Команда готовит качественный промпт для генерации изображения в обычном ChatGPT:

```text
/image Современный SOC-центр, фотореалистично
```

Бот вернёт готовый промпт.

## /video

По той же причине OpenCode не предоставляет бинарный video output из подписки ChatGPT Plus/Pro.

Команда:

```text
/video Кинематографичный пролёт через дата-центр
```

возвращает готовый промпт для ChatGPT/Sora, но не вызывает платный API.

## Ошибка credit_balance_exhausted

Если бот показывает:

```text
credit_balance_exhausted
You have no credits remaining
```

значит OpenCode всё ещё использует credit/API provider, например OpenCode Zen, а не ChatGPT Plus/Pro OAuth.

Проверьте:

```bash
opencode auth list
```

Затем:

```bash
opencode
```

и внутри:

```text
/connect
```

выберите:

```text
OpenAI
ChatGPT Plus/Pro
```

после OAuth-входа:

```text
/models
```

выберите модель OpenAI, доступную по вашей подписке.

Если в `.env` задано `OPENCODE_MODEL` на платный credit-provider, удалите значение:

```env
OPENCODE_MODEL=
```

После изменения перезапустите сервис.
