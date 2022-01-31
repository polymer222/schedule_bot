import logging

from aiogram import Bot, Dispatcher, types

from app import handlers, middlewares, filters
from app.config import Config
from app.utils import logger
from app.utils.db.db_gino import db
from app.utils.notifications.startup_notify import notify_superusers
from app.utils.redis import BaseRedis
from app.utils.set_bot_commands import set_commands


async def wait_redis():
    connector = BaseRedis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=0)
    try:
        await connector.connect()
        info = await connector.redis.info()
        logging.info("Connected to Redis server v{redis}", redis=info["server"]["redis_version"])
    finally:
        await connector.disconnect()


async def wait_postgres():
    await db.set_bind(Config.POSTGRES_URI)
    version = await db.scalar("SELECT version();")
    logging.info("Connected to {postgres}", postgres=version)


async def on_startup(dp):
    middlewares.setup(dp)
    filters.setup(dp)
    handlers.setup_all_handlers(dp)
    logger.setup_logger()

    await notify_superusers(Config.ADMINS)
    await set_commands(dp)


async def on_shutdown(dp):
    logging.warning("Shutting down..")
    session = await dp.bot.get_session()
    await session.close()
    await dp.storage.close()
    await dp.storage.wait_closed()
    if mongo := dp.bot.get('mongo', None):
        await mongo.close()
        await mongo.wait_closed()
    logging.warning("Bye!")


def main():
    bot = Bot(token=Config.BOT_TOKEN, parse_mode=types.ParseMode.HTML)

    dp = Dispatcher(bot, storage=storage)

    start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown)
