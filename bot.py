from __future__ import annotations

import asyncio
import logging

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
from git_ops import GitError, commit_all, current_branch, diff, ensure_work_branch, push_current, status
from opencode_runner import OpenCodeRunner
from projects import ProjectError, list_projects, resolve_project

settings = Settings.from_env()
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
log = logging.getLogger('telegram-opencode-bot')
runner = OpenCodeRunner(settings)

locks: dict[int, asyncio.Lock] = {}


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
        raise ProjectError('Сначала выберите проект: /projects → /project NAME')
    return resolve_project(settings.project_root, name)


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
        '/projects — список проектов\n'
        '/project NAME — выбрать проект\n'
        '/chat TEXT — анализ без изменений\n'
        '/plan TEXT — план без изменений\n'
        '/exec TEXT — изменить код/запустить разрешённые тесты\n'
        '/status — git status\n'
        '/diff — git diff\n'
        '/commit MESSAGE — запросить подтверждение commit\n'
        '/push — запросить подтверждение push\n'
        '/cancel — забыть ожидающее подтверждение\n\n'
        'Обычное сообщение работает как /chat.'
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
    lines = [f"{'👉 ' if x == current else ''}{x}" for x in items]
    await update.effective_message.reply_text('Проекты:\n' + '\n'.join(lines))


async def project_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    if not context.args:
        return await update.effective_message.reply_text('Использование: /project NAME')
    name = context.args[0]
    try:
        project = resolve_project(settings.project_root, name)
        branch = await current_branch(project)
    except (ProjectError, GitError) as exc:
        return await update.effective_message.reply_text(f'Ошибка: {exc}')
    context.user_data['project'] = name
    await update.effective_message.reply_text(
        f'Активный проект: {name}\nВетка: {branch or "detached HEAD"}'
    )


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
        return await update.effective_message.reply_text(
            f'Добавьте текст задания после /{mode}.'
        )

    try:
        project = active_project(context)
    except ProjectError as exc:
        return await update.effective_message.reply_text(str(exc))

    uid = update.effective_user.id
    lock = locks.setdefault(uid, asyncio.Lock())
    if lock.locked():
        return await update.effective_message.reply_text(
            'У вас уже выполняется задача. Дождитесь её завершения.'
        )

    async with lock:
        try:
            branch = await current_branch(project)
            if mode == 'exec':
                branch = await ensure_work_branch(project, settings.protected_branches)

            await update.effective_message.reply_text(
                f'Запускаю {mode.upper()}\nПроект: {project.name}\nВетка: {branch}'
            )
            await context.bot.send_chat_action(
                update.effective_chat.id,
                ChatAction.TYPING,
            )

            result = await runner.run(project, mode, prompt)
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


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    try:
        project = active_project(context)
        await send_long(update, await status(project))
    except (ProjectError, GitError) as exc:
        await update.effective_message.reply_text(f'Ошибка: {exc}')


async def diff_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    try:
        project = active_project(context)
        await send_long(update, await diff(project))
    except (ProjectError, GitError) as exc:
        await update.effective_message.reply_text(f'Ошибка: {exc}')


async def commit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)

    message = ' '.join(context.args).strip()
    if not message:
        return await update.effective_message.reply_text(
            'Использование: /commit MESSAGE'
        )

    if len(message) > 200 or '\n' in message or '\r' in message:
        return await update.effective_message.reply_text(
            'Commit message должен быть одной строкой до 200 символов.'
        )

    try:
        project = active_project(context)
        summary = await status(project)
        branch = await current_branch(project)
    except (ProjectError, GitError) as exc:
        return await update.effective_message.reply_text(f'Ошибка: {exc}')

    if branch in settings.protected_branches:
        return await update.effective_message.reply_text(
            'Commit в защищённую ветку запрещён. '
            'Сначала выполните /exec — будет создана ai/* ветка.'
        )

    context.user_data['pending'] = {
        'action': 'commit',
        'message': message,
        'project': project.name,
    }

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton('✅ Commit', callback_data='confirm:commit'),
        InlineKeyboardButton('❌ Отмена', callback_data='cancel'),
    ]])

    await update.effective_message.reply_text(
        f'Подтвердите commit.\n'
        f'Проект: {project.name}\n'
        f'Ветка: {branch}\n'
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
        return await update.effective_message.reply_text(
            'Push из detached HEAD или защищённой ветки запрещён.'
        )

    context.user_data['pending'] = {
        'action': 'push',
        'project': project.name,
    }

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton('✅ Push', callback_data='confirm:push'),
        InlineKeyboardButton('❌ Отмена', callback_data='cancel'),
    ]])

    await update.effective_message.reply_text(
        f'Подтвердите: git push -u origin {branch}',
        reply_markup=keyboard,
    )


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return await deny(update)
    context.user_data.pop('pending', None)
    await update.effective_message.reply_text(
        'Ожидающее подтверждение отменено.'
    )


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    if not authorized(update):
        if query:
            await query.answer('Доступ запрещён.', show_alert=True)
        return

    if not query:
        return

    await query.answer()

    if query.data == 'cancel':
        context.user_data.pop('pending', None)
        return await query.edit_message_text('Операция отменена.')

    pending = context.user_data.get('pending')
    if not isinstance(pending, dict):
        return await query.edit_message_text(
            'Нет операции, ожидающей подтверждения.'
        )

    expected = f"confirm:{pending.get('action')}"
    if query.data != expected:
        return await query.edit_message_text('Подтверждение устарело.')

    try:
        project = resolve_project(
            settings.project_root,
            str(pending['project']),
        )
        branch = await current_branch(project)

        if branch in settings.protected_branches:
            raise GitError('Операция в защищённой ветке запрещена.')

        if pending['action'] == 'commit':
            result = await commit_all(
                project,
                str(pending['message']),
            )
            text = '✅ Commit создан.\n' + result

        elif pending['action'] == 'push':
            result = await push_current(project)
            text = '✅ Push выполнен.\n' + (result or f'origin/{branch}')

        else:
            raise GitError('Неизвестная операция.')

        context.user_data.pop('pending', None)
        await query.edit_message_text(text[:4000])

    except Exception as exc:
        log.exception('Confirmed git operation failed')
        context.user_data.pop('pending', None)
        await query.edit_message_text(f'Ошибка: {exc}')


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    log.exception(
        'Unhandled Telegram error',
        exc_info=context.error,
    )


def main() -> None:
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    app.add_handler(CommandHandler('start', start_cmd))
    app.add_handler(CommandHandler('help', start_cmd))
    app.add_handler(CommandHandler('projects', projects_cmd))
    app.add_handler(CommandHandler('project', project_cmd))
    app.add_handler(CommandHandler('chat', chat_cmd))
    app.add_handler(CommandHandler('plan', plan_cmd))
    app.add_handler(CommandHandler('exec', exec_cmd))
    app.add_handler(CommandHandler('status', status_cmd))
    app.add_handler(CommandHandler('diff', diff_cmd))
    app.add_handler(CommandHandler('commit', commit_cmd))
    app.add_handler(CommandHandler('push', push_cmd))
    app.add_handler(CommandHandler('cancel', cancel_cmd))

    app.add_handler(
        CallbackQueryHandler(
            callback,
            pattern=r'^(confirm:(commit|push)|cancel)$',
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_message,
        )
    )

    app.add_error_handler(error_handler)

    log.info(
        'Starting bot; project_root=%s',
        settings.project_root,
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == '__main__':
    main()
