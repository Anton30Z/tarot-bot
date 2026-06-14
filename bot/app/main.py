import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.config import get_settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(message: Message) -> None:
    await message.answer("Tarot Bot scaffold is running. Mini App integration comes next.")


async def main() -> None:
    settings = get_settings()

    if not settings.bot_token:
        logger.warning("BOT_TOKEN is empty. Bot polling is skipped, container stays alive for local scaffold checks.")
        while True:
            await asyncio.sleep(3600)

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.message.register(start, CommandStart())

    logger.info("Starting bot polling")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
