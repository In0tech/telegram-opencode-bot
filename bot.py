from __future__ import annotations

import asyncio
import logging
import re
from logging.handlers import RotatingFileHandler

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import Settings
from creative_tools import CreativeError, CreativeService
from git_ops import (
    GitError,
    commit_all,
    current_branch,
    diff,
    ensure_work_branch,
    list_branches,
    push_current,
    rollback_tracked_changes,
    status,
    switch_branch,
)
from github_ops import create_pr
from opencode_runner import OpenCodeRunner
from projects import ProjectError, list_projects, resolve_project
from session_store import SessionStore
from test_runner import TestRunError, run_tests
from tarot import draw_cards

settings = Settings.from_env()

log_file = settings.state_dir / 'bot.log'
handlers: list[logging.Handler] = [logging.StreamHandler()]
handlers.append(
    RotatingFileHandler(
        log_file,
        maxBytes=2_000_000,
        backupCount=3,
        encoding='utf-8',
    )
)
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=handlers,
)

log = logging.getLogger('telegram-opencode-bot')
runner = OpenCodeRunner(settings)
creative = CreativeService(settings)
sessions = SessionStore(settings.state_dir / 'sessions.json')
locks: dict[int, asyncio.Lock] = {}
creative_locks: dict[int, asyncio.Lock] = {}


def authorized(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id in settings.allowed_user_ids)


async def deny(update: Update) -> None:
    if update.effective_message:
        await update.effective_message.reply_text('Доступ запрещён.')


def active_project_name(context: ContextTypes.DEFAULT_TYPE) -> str | None:
    value = context.user_data.get('project')
    return value if isinstance(value, str) else None


def active_project(context: ContextTypes.DEFAULT_TYPE):
    name = active_project_name(context)
    if not name:
        raise ProjectError('Сначала выберите проект: /projects → кнопка проекта')
    return resolve_project(settings.project_root, name)


def active_session_name(context: ContextTypes.DEFAULT_TYPE) -> str:
    value = context.user_data.get('session_name')
    return value if isinstance(value, str) and value else 'default'


async def send_long(update: Update, text: str) -> None:
    msg = update.effective_message
    if not msg:
        return
    text = text or '(пустой ответ)'
    for start in range(0, len(text), 3900):
        await msg.reply_text(text[start:start + 3900])


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    await update.effective_message.reply_text(
        'OpenCode Remote Bot готов.\n\n'
        '/projects — выбрать проект кнопкой\n'
        '/project NAME — выбрать проект текстом\n'
        '/sessions — сессии OpenCode текущего проекта\n'
        '/newsession NAME — новая долговременная сессия\n'
        '/session NAME — переключить сессию\n'
        '/chat TEXT — анализ\n'
        '/plan TEXT — план без изменений\n'
        '/exec TEXT — изменение кода\n'
        '/tests [python|npm|pnpm|go|cargo] — запустить тесты\n'
        '/status — git status\n'
        '/diff — git diff\n'
        '/branch [NAME] — ветки / переключение\n'
        '/commit MESSAGE — commit с подтверждением\n'
        '/push — push с подтверждением\n'
        '/pr [TITLE] — создать GitHub Pull Request\n'
        '/rollback — откатить tracked-изменения с подтверждением\n'
        '/logs [N] — последние строки лога бота\n'
        '\nТворческие команды:\n'
        '/presentation [N] | ТЕМА — редактируемый PPTX\n'
        '/image ОПИСАНИЕ — сгенерировать изображение\n'
        '/video ОПИСАНИЕ — сгенерировать видео\n'
        '/email ЗАДАНИЕ — написать письмо\n'
        '/tarot [N] | ВОПРОС — расклад Таро\n'
        '/cancel — отменить ожидающее подтверждение'
    )


async def projects_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)

    items = list_projects(settings.project_root)
    if not items:
        return await update.effective_message.reply_text(
            f'Git-проекты в {settings.project_root} не найдены.'
        )

    current = active_project_name(context)
    buttons = []
    for name in items[:40]:
        mark = '✅ ' if name == current else ''
        buttons.append([
            InlineKeyboardButton(
                f'{mark}{name}',
                callback_data=f'project:{name}',
            )
        ])

    await update.effective_message.reply_text(
        f'Выберите проект. Текущий: {current or "не выбран"}',
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def _select_project(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    name: str,
    edit: bool = False,
) -> None:
    project = resolve_project(settings.project_root, name)
    branch = await current_branch(project)
    context.user_data['project'] = name
    context.user_data['session_name'] = 'default'
    text = (
        f'Активный проект: {name}\n'
        f'Ветка: {branch or "detached HEAD"}\n'
        'OpenCode session: default'
    )
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text)
    else:
        await update.effective_message.reply_text(text)


async def project_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    if not context.args:
        return await projects_cmd(update, context)
    try:
        await _select_project(update, context, context.args[0])
    except (ProjectError, GitError) as exc:
        await update.effective_message.reply_text(f'Ошибка: {exc}')


async def sessions_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    try:
        project = active_project(context)
    except ProjectError as exc:
        return await update.effective_message.reply_text(str(exc))

    found = sessions.list(update.effective_user.id, project.name)
    active = active_session_name(context)
    lines = [f'Активная: {active}', '']
    if found:
        for name, sid in sorted(found.items()):
            mark = '👉 ' if name == active else ''
            lines.append(f'{mark}{name}: {sid}')
    else:
        lines.append('Сохранённых sessionID пока нет. Выполните /chat, /plan или /exec.')
    await send_long(update, '\n'.join(lines))


async def newsession_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    try:
        project = active_project(context)
        name = sessions.validate_name(' '.join(context.args))
    except (ProjectError, ValueError) as exc:
        return await update.effective_message.reply_text(f'Ошибка: {exc}')

    if sessions.get(update.effective_user.id, project.name, name):
        return await update.effective_message.reply_text(
            'Такая сессия уже существует. Используйте /session NAME.'
        )

    context.user_data['session_name'] = name
    await update.effective_message.reply_text(
        f'Новая сессия {name!r} выбрана. Session ID будет создан при следующем запросе.'
    )


async def session_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    try:
        project = active_project(context)
        name = sessions.validate_name(' '.join(context.args))
    except (ProjectError, ValueError) as exc:
        return await update.effective_message.reply_text(f'Ошибка: {exc}')

    sid = sessions.get(update.effective_user.id, project.name, name)
    if not sid:
        return await update.effective_message.reply_text(
            'Сессия не найдена. Создайте её: /newsession NAME'
        )
    context.user_data['session_name'] = name
    await update.effective_message.reply_text(f'Активная OpenCode-сессия: {name}\nID: {sid}')


async def _agent(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mode: str,
    prompt: str,
) -> None:
    if not authorized(update):
        return await deny(update)

    prompt = prompt.strip()
    if not prompt:
        return await update.effective_message.reply_text(f'Добавьте текст после /{mode}.')

    try:
        project = active_project(context)
    except ProjectError as exc:
        return await update.effective_message.reply_text(str(exc))

    uid = update.effective_user.id
    lock = locks.setdefault(uid, asyncio.Lock())
    if lock.locked():
        return await update.effective_message.reply_text('У вас уже выполняется задача.')

    async with lock:
        try:
            branch = await current_branch(project)
            if mode == 'exec':
                branch = await ensure_work_branch(project, settings.protected_branches)

            session_name = active_session_name(context)
            session_id = sessions.get(uid, project.name, session_name)

            await update.effective_message.reply_text(
                f'Запускаю {mode.upper()}\n'
                f'Проект: {project.name}\n'
                f'Ветка: {branch}\n'
                f'Сессия: {session_name}'
            )
            await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

            result = await runner.run(
                project,
                mode,
                prompt,
                session_id=session_id,
                session_title=f'tg:{project.name}:{session_name}',
            )

            if result.session_id and result.session_id != session_id:
                sessions.set(uid, project.name, session_name, result.session_id)

            prefix = '✅' if result.returncode == 0 else f'⚠️ rc={result.returncode}'
            await send_long(update, f'{prefix}\n\n{result.output}')

            if mode == 'exec':
                await send_long(update, '\nGit status:\n' + await status(project))

        except Exception as exc:
            log.exception('Agent task failed')
            await update.effective_message.reply_text(f'Ошибка выполнения: {exc}')


async def chat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _agent(update, context, 'chat', ' '.join(context.args))


async def plan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _agent(update, context, 'plan', ' '.join(context.args))


async def exec_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _agent(update, context, 'exec', ' '.join(context.args))


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message and update.effective_message.text:
        await _agent(update, context, 'chat', update.effective_message.text)


async def tests_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    try:
        project = active_project(context)
        requested = context.args[0] if context.args else None
        await update.effective_message.reply_text('Запускаю тесты...')
        cmd, rc, output = await run_tests(
            project,
            requested=requested,
            timeout=settings.test_timeout_seconds,
        )
        await send_long(
            update,
            f'Команда: {" ".join(cmd)}\nExit code: {rc}\n\n{output or "(нет вывода)"}',
        )
    except (ProjectError, TestRunError) as exc:
        await update.effective_message.reply_text(f'Ошибка: {exc}')


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    try:
        await send_long(update, await status(active_project(context)))
    except (ProjectError, GitError) as exc:
        await update.effective_message.reply_text(f'Ошибка: {exc}')


async def diff_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    try:
        await send_long(update, await diff(active_project(context)))
    except (ProjectError, GitError) as exc:
        await update.effective_message.reply_text(f'Ошибка: {exc}')


async def branch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    try:
        project = active_project(context)
        if context.args:
            branch = await switch_branch(project, context.args[0])
            return await update.effective_message.reply_text(f'Переключено на ветку: {branch}')

        current = await current_branch(project)
        branches = await list_branches(project)
        context.user_data['branch_choices'] = branches[:30]
        buttons = [
            [InlineKeyboardButton(
                ('✅ ' if b == current else '') + b,
                callback_data=f'branch:{i}',
            )]
            for i, b in enumerate(branches[:30])
        ]
        await update.effective_message.reply_text(
            f'Текущая ветка: {current}\nВыберите ветку:',
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except (ProjectError, GitError) as exc:
        await update.effective_message.reply_text(f'Ошибка: {exc}')


async def commit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    message = ' '.join(context.args).strip()
    if not message:
        return await update.effective_message.reply_text('Использование: /commit MESSAGE')
    if len(message) > 200 or '\n' in message or '\r' in message:
        return await update.effective_message.reply_text('Commit message: одна строка до 200 символов.')

    try:
        project = active_project(context)
        summary = await status(project)
        branch = await current_branch(project)
    except (ProjectError, GitError) as exc:
        return await update.effective_message.reply_text(f'Ошибка: {exc}')

    if branch in settings.protected_branches:
        return await update.effective_message.reply_text('Commit в защищённую ветку запрещён.')

    context.user_data['pending'] = {
        'action': 'commit', 'message': message, 'project': project.name,
    }
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton('✅ Commit', callback_data='confirm:commit'),
        InlineKeyboardButton('❌ Отмена', callback_data='cancel'),
    ]])
    await update.effective_message.reply_text(
        f'Подтвердите commit.\nПроект: {project.name}\nВетка: {branch}\n'
        f'Message: {message}\n\n{summary}',
        reply_markup=keyboard,
    )


async def push_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    try:
        project = active_project(context)
        branch = await current_branch(project)
    except (ProjectError, GitError) as exc:
        return await update.effective_message.reply_text(f'Ошибка: {exc}')

    if not branch or branch in settings.protected_branches:
        return await update.effective_message.reply_text('Push из этой ветки запрещён.')

    context.user_data['pending'] = {'action': 'push', 'project': project.name}
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton('✅ Push', callback_data='confirm:push'),
        InlineKeyboardButton('❌ Отмена', callback_data='cancel'),
    ]])
    await update.effective_message.reply_text(
        f'Подтвердите: git push -u origin {branch}',
        reply_markup=keyboard,
    )


async def pr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    try:
        project = active_project(context)
        branch = await current_branch(project)
        if not branch or branch in settings.protected_branches:
            raise GitError('PR из защищённой ветки или detached HEAD запрещён.')
        title = ' '.join(context.args).strip() or None
        url = await create_pr(project, title=title)
        await update.effective_message.reply_text(f'✅ Pull Request:\n{url}')
    except (ProjectError, GitError) as exc:
        await update.effective_message.reply_text(
            f'Ошибка PR: {exc}\nЕсли ветка ещё не опубликована, сначала выполните /push.'
        )


async def rollback_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    try:
        project = active_project(context)
        summary = await status(project)
    except (ProjectError, GitError) as exc:
        return await update.effective_message.reply_text(f'Ошибка: {exc}')

    context.user_data['pending'] = {'action': 'rollback', 'project': project.name}
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton('⚠️ Rollback tracked', callback_data='confirm:rollback'),
        InlineKeyboardButton('❌ Отмена', callback_data='cancel'),
    ]])
    await update.effective_message.reply_text(
        'Будут отменены staged/unstaged изменения TRACKED-файлов до HEAD.\n'
        'Untracked-файлы не удаляются.\n\n' + summary,
        reply_markup=keyboard,
    )


async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    try:
        count = int(context.args[0]) if context.args else 80
        count = min(max(count, 10), 300)
        if not log_file.exists():
            return await update.effective_message.reply_text('Лог пока пуст.')
        lines = log_file.read_text(encoding='utf-8', errors='replace').splitlines()
        await send_long(update, '\n'.join(lines[-count:]) or '(лог пуст)')
    except ValueError:
        await update.effective_message.reply_text('Использование: /logs [10..300]')


def _command_payload(update: Update) -> str:
    text = update.effective_message.text if update.effective_message else ''
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ''


def _parse_count_payload(
    payload: str,
    default: int,
    minimum: int,
    maximum: int,
) -> tuple[int, str]:
    match = re.match(r'^([0-9]{1,2})\s*\|\s*(.+)$', payload, flags=re.S)
    if not match:
        return default, payload.strip()
    count = min(max(int(match.group(1)), minimum), maximum)
    return count, match.group(2).strip()


async def _creative_guard(update: Update) -> asyncio.Lock | None:
    uid = update.effective_user.id
    lock = creative_locks.setdefault(uid, asyncio.Lock())
    if lock.locked():
        await update.effective_message.reply_text(
            'У вас уже выполняется творческая генерация. Дождитесь её завершения.'
        )
        return None
    return lock


async def presentation_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)

    slides, brief = _parse_count_payload(
        _command_payload(update),
        default=8,
        minimum=3,
        maximum=20,
    )
    if not brief:
        return await update.effective_message.reply_text(
            'Использование: /presentation [N] | ТЕМА\n'
            'Пример: /presentation 10 | Инвесторская презентация продукта'
        )

    lock = await _creative_guard(update)
    if not lock:
        return

    async with lock:
        try:
            await update.effective_message.reply_text(
                f'Создаю редактируемую презентацию на {slides} слайдов...'
            )
            path = await creative.create_presentation(brief, slides=slides)
            with path.open('rb') as fh:
                await update.effective_message.reply_document(
                    document=fh,
                    filename=path.name,
                    caption='✅ Презентация готова (.pptx)',
                )
        except CreativeError as exc:
            await update.effective_message.reply_text(f'Ошибка презентации: {exc}')
        except Exception as exc:
            log.exception('Presentation generation failed')
            await update.effective_message.reply_text(f'Ошибка презентации: {exc}')


async def image_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)

    prompt = _command_payload(update)
    if not prompt:
        return await update.effective_message.reply_text(
            'Использование: /image ОПИСАНИЕ'
        )

    lock = await _creative_guard(update)
    if not lock:
        return

    async with lock:
        try:
            await update.effective_message.reply_text('Генерирую изображение...')
            path = await creative.create_image(prompt)
            with path.open('rb') as fh:
                await update.effective_message.reply_document(
                    document=fh,
                    filename=path.name,
                    caption='✅ Изображение готово',
                )
        except CreativeError as exc:
            await update.effective_message.reply_text(f'Ошибка изображения: {exc}')
        except Exception as exc:
            log.exception('Image generation failed')
            await update.effective_message.reply_text(f'Ошибка изображения: {exc}')


async def video_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)

    prompt = _command_payload(update)
    if not prompt:
        return await update.effective_message.reply_text(
            'Использование: /video ОПИСАНИЕ'
        )

    lock = await _creative_guard(update)
    if not lock:
        return

    async with lock:
        try:
            await update.effective_message.reply_text(
                'Запускаю генерацию видео. Это может занять несколько минут. '
                'OpenAI Sora API объявлен устаревшим и запланирован к отключению 24.09.2026.'
            )
            path = await creative.create_video(prompt)
            with path.open('rb') as fh:
                await update.effective_message.reply_video(
                    video=fh,
                    filename=path.name,
                    caption='✅ Видео готово',
                    supports_streaming=True,
                )
        except CreativeError as exc:
            await update.effective_message.reply_text(f'Ошибка видео: {exc}')
        except Exception as exc:
            log.exception('Video generation failed')
            await update.effective_message.reply_text(f'Ошибка видео: {exc}')


async def email_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)

    brief = _command_payload(update)
    if not brief:
        return await update.effective_message.reply_text(
            'Использование: /email ЗАДАНИЕ\n'
            'Пример: /email Напиши вежливое письмо инвестору с благодарностью за встречу'
        )

    lock = await _creative_guard(update)
    if not lock:
        return

    async with lock:
        try:
            await update.effective_message.reply_text('Готовлю письмо...')
            text = await creative.draft_email(brief)
            await send_long(update, text)
        except CreativeError as exc:
            await update.effective_message.reply_text(f'Ошибка письма: {exc}')
        except Exception as exc:
            log.exception('Email drafting failed')
            await update.effective_message.reply_text(f'Ошибка письма: {exc}')


async def tarot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)

    count, question = _parse_count_payload(
        _command_payload(update),
        default=3,
        minimum=1,
        maximum=10,
    )
    cards = draw_cards(count)
    spread = '\n'.join(
        f'{idx + 1}. {card.name} — {card.orientation}'
        for idx, card in enumerate(cards)
    )

    lock = await _creative_guard(update)
    if not lock:
        return

    async with lock:
        try:
            await update.effective_message.reply_text(
                f'Карты расклада:\n{spread}\n\nИнтерпретирую...'
            )
            text = await creative.interpret_tarot(question, cards)
            await send_long(update, text)
        except CreativeError as exc:
            await update.effective_message.reply_text(
                f'Карты расклада:\n{spread}\n\n'
                f'Для AI-интерпретации требуется настройка: {exc}'
            )
        except Exception as exc:
            log.exception('Tarot interpretation failed')
            await update.effective_message.reply_text(f'Ошибка Таро: {exc}')


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    context.user_data.pop('pending', None)
    await update.effective_message.reply_text('Ожидающее подтверждение отменено.')


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not authorized(update):
        if query:
            await query.answer('Доступ запрещён.', show_alert=True)
        return
    if not query:
        return
    await query.answer()

    if query.data.startswith('project:'):
        try:
            return await _select_project(
                update, context, query.data.split(':', 1)[1], edit=True
            )
        except (ProjectError, GitError) as exc:
            return await query.edit_message_text(f'Ошибка: {exc}')

    if query.data.startswith('branch:'):
        try:
            idx = int(query.data.split(':', 1)[1])
            choices = context.user_data.get('branch_choices', [])
            branch = choices[idx]
            switched = await switch_branch(active_project(context), branch)
            return await query.edit_message_text(f'Переключено на ветку: {switched}')
        except (ValueError, IndexError, ProjectError, GitError) as exc:
            return await query.edit_message_text(f'Ошибка: {exc}')

    if query.data == 'cancel':
        context.user_data.pop('pending', None)
        return await query.edit_message_text('Операция отменена.')

    pending = context.user_data.get('pending')
    if not isinstance(pending, dict):
        return await query.edit_message_text('Нет операции, ожидающей подтверждения.')

    expected = f"confirm:{pending.get('action')}"
    if query.data != expected:
        return await query.edit_message_text('Подтверждение устарело.')

    try:
        project = resolve_project(settings.project_root, str(pending['project']))
        branch = await current_branch(project)

        if pending['action'] in {'commit', 'push'} and branch in settings.protected_branches:
            raise GitError('Операция в защищённой ветке запрещена.')

        if pending['action'] == 'commit':
            result = await commit_all(project, str(pending['message']))
            text = '✅ Commit создан.\n' + result
        elif pending['action'] == 'push':
            result = await push_current(project)
            text = '✅ Push выполнен.\n' + (result or f'origin/{branch}')
        elif pending['action'] == 'rollback':
            result = await rollback_tracked_changes(project)
            text = '✅ Rollback выполнен.\n' + result
        else:
            raise GitError('Неизвестная операция.')

        context.user_data.pop('pending', None)
        await query.edit_message_text(text[:4000])
    except Exception as exc:
        log.exception('Confirmed operation failed')
        context.user_data.pop('pending', None)
        await query.edit_message_text(f'Ошибка: {exc}')


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception('Unhandled Telegram error', exc_info=context.error)


def main() -> None:
    app = Application.builder().token(settings.telegram_bot_token).build()

    for name, handler in [
        ('start', start_cmd), ('help', start_cmd),
        ('projects', projects_cmd), ('project', project_cmd),
        ('sessions', sessions_cmd), ('newsession', newsession_cmd), ('session', session_cmd),
        ('chat', chat_cmd), ('plan', plan_cmd), ('exec', exec_cmd),
        ('tests', tests_cmd), ('status', status_cmd), ('diff', diff_cmd),
        ('branch', branch_cmd), ('commit', commit_cmd), ('push', push_cmd),
        ('pr', pr_cmd), ('rollback', rollback_cmd), ('logs', logs_cmd),
        ('cancel', cancel_cmd),
    ]:
        app.add_handler(CommandHandler(name, handler))

    app.add_handler(
        CallbackQueryHandler(
            callback,
            pattern=r'^(project:.+|branch:\d+|confirm:(commit|push|rollback)|cancel)$',
        )
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    app.add_error_handler(error_handler)

    log.info('Starting bot; project_root=%s state_dir=%s', settings.project_root, settings.state_dir)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
