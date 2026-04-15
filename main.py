import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from src.core.config import settings
from src.handlers.commands import router as commands_router
from src.handlers.resume_handlers import router as resume_router
from src.utils.logger import logger


async def main():
    settings.validate()
    
    logger.info("Starting HH Skills Finder Bot...")
    
    bot = Bot(token=settings.telegram_token)
    
    redis = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        decode_responses=True
    )
    storage = RedisStorage(redis=redis)
    
    dp = Dispatcher(storage=storage)
    dp.include_router(commands_router)
    dp.include_router(resume_router)
    
    logger.info(f"Bot configured. Starting polling...")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await redis.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped with error: {e}")
