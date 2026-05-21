"""
Standalone Telegram bot service.

Run ONLY when operating interactively (not during automated pipeline runs).
The bot and the agent that awaits review feedback MUST share the same process,
because review_queue uses asyncio.Event (in-memory, not cross-process).

Usage:
    PYTHONPATH=. ./venv/bin/python3.11 integrations/telegram_bot/run_bot.py

Then in another terminal:
    PYTHONPATH=. ./venv/bin/python3.11 cli.py run --feature "Login" --platform api

The CLI run command sets up its own polling via cmd_run — do NOT use this
script at the same time as `cli.py pipeline`, which starts polling internally.
"""
import asyncio
import signal
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

import structlog
from core.telegram_bot import telegram_bot
from core.workflows.approval_workflow import review_queue

logger = structlog.get_logger(__name__)


async def main() -> None:
    stop_event = asyncio.Event()

    def _request_stop():
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            # Windows — signal handlers not supported on event loop
            pass

    telegram_bot.set_review_queue(review_queue)
    await telegram_bot.start_polling()

    logger.info("telegram_bot_ready", mode="polling")
    print("✓ Telegram bot running — waiting for approve/reject callbacks")
    print("  Press Ctrl+C to stop\n")

    await stop_event.wait()

    print("\nShutting down Telegram bot...")
    await telegram_bot.stop_polling()
    logger.info("telegram_bot_stopped")


if __name__ == "__main__":
    asyncio.run(main())
