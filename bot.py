import os
import subprocess
import tempfile
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
TIMEOUT = 10  # seconds


def run_python(code: str) -> str:
    """Execute Python code in a subprocess and return stdout/stderr."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name

    try:
        result = subprocess.run(
            ["python3", path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"⏱️ Timeout after {TIMEOUT}s"
    except Exception as e:
        return f"Error: {e}"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def strip_code_fence(text: str) -> str:
    """Remove ```python ... ``` if user wrapped the code."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)
    return text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me Python code and I'll run it!\n\n"
        "Example:\n"
        "print('hello')\n"
        "print(2 + 3)\n\n"
        f"⏱️ Timeout: {TIMEOUT}s per execution."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = strip_code_fence(update.message.text)
    if not code:
        await update.message.reply_text("Send some Python code to run.")
        return

    await update.message.chat.send_action("typing")

    # Run blocking subprocess in a thread so we don't block the event loop
    output = await asyncio.to_thread(run_python, code)

    # Telegram message limit is 4096 chars
    if len(output) > 4000:
        output = output[:4000] + "\n... (truncated)"

    await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN env var not set")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
