from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from .app_factory import build_pipeline
from .config import Settings
from .formatting import format_article, format_run, split_telegram_message
from .models import Goal
from .pipeline import NewsPipeline
from .storage import SQLiteStorage

logger = logging.getLogger(__name__)


HELP_TEXT = """Use the bot with:

/search Prediction Markets
/article Prediction Markets
/watch Prediction Markets
/goals
/unwatch Prediction Markets"""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = Settings.from_env()
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required")

    pipeline = build_pipeline(settings)
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data["settings"] = settings
    app.bot_data["pipeline"] = pipeline
    app.bot_data["storage"] = pipeline.storage

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("article", article))
    app.add_handler(CommandHandler("watch", watch))
    app.add_handler(CommandHandler("goals", goals))
    app.add_handler(CommandHandler("unwatch", unwatch))
    app.add_handler(CallbackQueryHandler(buttons))

    if settings.track_interval_minutes > 0 and app.job_queue is not None:
        app.job_queue.run_repeating(
            scan_goals,
            interval=settings.track_interval_minutes * 60,
            first=45,
            name="scan_goals",
        )

    logger.info("Starting AlphaMedia news bot")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _allowed(update, context):
        return
    await update.effective_message.reply_text(HELP_TEXT, reply_markup=_home_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _allowed(update, context):
        return
    await update.effective_message.reply_text(HELP_TEXT, reply_markup=_home_keyboard())


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _allowed(update, context):
        return
    topic = " ".join(context.args).strip()
    if not topic:
        await update.effective_message.reply_text("Send `/search <topic>`.", parse_mode=ParseMode.MARKDOWN)
        return
    await _run_and_reply(update, context, topic, want_article=False)


async def article(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _allowed(update, context):
        return
    topic = " ".join(context.args).strip()
    if not topic:
        await update.effective_message.reply_text("Send `/article <topic>`.", parse_mode=ParseMode.MARKDOWN)
        return
    await _run_and_reply(update, context, topic, want_article=True)


async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _allowed(update, context):
        return
    topic = " ".join(context.args).strip()
    if not topic:
        await update.effective_message.reply_text("Send `/watch <topic>`.", parse_mode=ParseMode.MARKDOWN)
        return

    storage: SQLiteStorage = context.bot_data["storage"]
    goal = storage.upsert_goal(update.effective_chat.id, topic)
    await update.effective_message.reply_text(
        f"Watching: {goal.topic}",
        reply_markup=_goal_keyboard(goal),
    )


async def goals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _allowed(update, context):
        return
    await _send_goals(update.effective_message, context, update.effective_chat.id)


async def unwatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _allowed(update, context):
        return
    topic = " ".join(context.args).strip()
    if not topic:
        await update.effective_message.reply_text("Send `/unwatch <topic>`.", parse_mode=ParseMode.MARKDOWN)
        return
    storage: SQLiteStorage = context.bot_data["storage"]
    deleted = storage.delete_goal(update.effective_chat.id, topic)
    await update.effective_message.reply_text("Removed." if deleted else "That topic was not saved.")


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _allowed(update, context):
        return
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    storage: SQLiteStorage = context.bot_data["storage"]

    if data == "help":
        await query.message.reply_text(HELP_TEXT, reply_markup=_home_keyboard())
        return
    if data == "goals":
        await _send_goals(query.message, context, query.message.chat_id)
        return
    if data == "search_prompt":
        await query.message.reply_text("Send `/search Prediction Markets`.", parse_mode=ParseMode.MARKDOWN)
        return

    action, _, raw_goal_id = data.partition(":")
    if action not in {"run_goal", "article_goal", "delete_goal"} or not raw_goal_id.isdigit():
        await query.message.reply_text("Unknown action.")
        return

    goal = storage.get_goal(int(raw_goal_id))
    if not goal or goal.chat_id != query.message.chat_id:
        await query.message.reply_text("Saved topic not found.")
        return

    if action == "delete_goal":
        storage.delete_goal_by_id(goal.id)
        await query.message.reply_text(f"Removed: {goal.topic}")
        return

    await _run_and_reply(
        update,
        context,
        goal.topic,
        want_article=action == "article_goal",
        goal=goal,
    )


async def scan_goals(context: ContextTypes.DEFAULT_TYPE) -> None:
    storage: SQLiteStorage = context.bot_data["storage"]
    pipeline: NewsPipeline = context.bot_data["pipeline"]
    for goal in storage.list_goals():
        try:
            run = await asyncio.to_thread(pipeline.run, goal.topic, fresh_only=True)
            storage.touch_goal(goal.id)
            if not run.items:
                continue
            text = "Fresh update\n\n" + format_run(run)
            for chunk in split_telegram_message(text):
                await context.bot.send_message(
                    chat_id=goal.chat_id,
                    text=chunk,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                    reply_markup=_goal_keyboard(goal),
                )
        except Exception:
            logger.exception("Scheduled scan failed for goal %s", goal.id)


async def _run_and_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    topic: str,
    *,
    want_article: bool,
    goal: Goal | None = None,
) -> None:
    pipeline: NewsPipeline = context.bot_data["pipeline"]
    message = update.effective_message
    chat_id = update.effective_chat.id

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    status = await message.reply_text(f"Searching: {topic}")
    try:
        run = await asyncio.to_thread(pipeline.run, topic)
        if goal:
            context.bot_data["storage"].touch_goal(goal.id)
        await status.edit_text("Summarizing...")
        for chunk in split_telegram_message(format_run(run)):
            await message.reply_text(
                chunk,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=_goal_keyboard(goal) if goal else None,
            )
        if want_article:
            await status.edit_text("Drafting article...")
            draft = await asyncio.to_thread(pipeline.generate_article, run)
            for chunk in split_telegram_message(format_article(draft)):
                await message.reply_text(
                    chunk,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
        await status.delete()
    except Exception as exc:
        logger.exception("News run failed")
        await status.edit_text(f"Run failed: {exc}")


async def _send_goals(message: Any, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    storage: SQLiteStorage = context.bot_data["storage"]
    saved = storage.list_goals(chat_id)
    if not saved:
        await message.reply_text("No saved topics yet. Add one with `/watch Prediction Markets`.")
        return

    rows = []
    for goal in saved[:20]:
        label = goal.topic[:28] + ("..." if len(goal.topic) > 28 else "")
        rows.append([InlineKeyboardButton(f"Run: {label}", callback_data=f"run_goal:{goal.id}")])
        rows.append(
            [
                InlineKeyboardButton("Article", callback_data=f"article_goal:{goal.id}"),
                InlineKeyboardButton("Remove", callback_data=f"delete_goal:{goal.id}"),
            ]
        )
    await message.reply_text("Saved topics", reply_markup=InlineKeyboardMarkup(rows))


async def _allowed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    settings: Settings = context.bot_data["settings"]
    chat = update.effective_chat
    if chat is None:
        return False
    if not settings.telegram_allowed_chat_ids or chat.id in settings.telegram_allowed_chat_ids:
        return True
    if update.effective_message:
        await update.effective_message.reply_text("This chat is not allowed to use this bot.")
    return False


def _home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Run a search", callback_data="search_prompt")],
            [InlineKeyboardButton("Saved topics", callback_data="goals")],
        ]
    )


def _goal_keyboard(goal: Goal | None) -> InlineKeyboardMarkup | None:
    if goal is None:
        return None
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Refresh", callback_data=f"run_goal:{goal.id}"),
                InlineKeyboardButton("Draft article", callback_data=f"article_goal:{goal.id}"),
            ],
            [InlineKeyboardButton("Remove", callback_data=f"delete_goal:{goal.id}")],
        ]
    )


if __name__ == "__main__":
    main()
