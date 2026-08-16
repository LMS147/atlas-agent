"""Telegram layer. Polling by default; webhook mode when RENDER_EXTERNAL_URL
is present (free-tier web service deploy)."""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters,
)

import agent
import memory

logging.basicConfig(level=logging.INFO)

ALLOWED = {int(x) for x in os.environ["ALLOWED_USER_IDS"].split(",") if x.strip()}
sessions: dict[int, list] = {}


def guard(fn):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or user.id not in ALLOWED:
            logging.warning("blocked uid=%s", user.id if user else "?")
            return
        return await fn(update, ctx)
    return wrapper


async def send(update: Update, text: str) -> None:
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i + 4000])


@guard
async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        reply, history = agent.run(sessions.get(uid, []), update.message.text)
        sessions[uid] = agent.trim(history)
        await send(update, reply)
    except Exception:
        logging.exception("agent failed")
        await update.message.reply_text("Something broke. Check the logs.")


@guard
async def cmd_memory(update, ctx):
    await send(update, memory.load_memory())


@guard
async def cmd_agent(update, ctx):
    await send(update, memory.load_agent())


@guard
async def cmd_remember(update, ctx):
    fact = " ".join(ctx.args)
    if not fact:
        return await update.message.reply_text("Usage: /remember <fact>")
    status = memory.append_memory("User Preferences", fact)
    await update.message.reply_text(status)


@guard
async def cmd_compact(update, ctx):
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    old_len, new_len, new = agent.compact_memory()
    await send(update, f"Compacted {old_len} → {new_len} chars.\n\n{new}")


@guard
async def cmd_reset(update, ctx):
    sessions.pop(update.effective_user.id, None)
    await update.message.reply_text("Session cleared. Memory untouched.")


async def cmd_whoami(update, ctx):
    # Deliberately unguarded — you need this to learn your own ID.
    await update.message.reply_text(str(update.effective_user.id))


def main():
    memory.ensure_files()
    token = os.environ["TELEGRAM_TOKEN"]
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("memory", cmd_memory))
    app.add_handler(CommandHandler("agent", cmd_agent))
    app.add_handler(CommandHandler("remember", cmd_remember))
    app.add_handler(CommandHandler("compact", cmd_compact))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("whoami", cmd_whoami))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    if os.getenv("RENDER_EXTERNAL_URL"):
        # Free-tier web service: Telegram pushes updates to us.
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ["PORT"]),
            url_path=token,
            webhook_url=f"{os.environ['RENDER_EXTERNAL_URL']}/{token}",
            secret_token=os.environ["WEBHOOK_SECRET"],
        )
    else:
        # Worker / local: we pull. No inbound HTTP needed.
        app.run_polling()


if __name__ == "__main__":
    main()
