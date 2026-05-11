import asyncio
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")
import structlog
from core.telegram_bot import telegram_bot
from core.workflows.approval_workflow import review_queue

logger = structlog.get_logger(__name__)

async def main():
    telegram_bot.set_review_queue(review_queue)
    print("Telegram bot started")
    await telegram_bot.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
