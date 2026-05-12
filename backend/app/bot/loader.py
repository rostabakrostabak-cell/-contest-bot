"""aiogram loader: bot, storage, dispatcher."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.config import get_settings

settings = get_settings()
log = logging.getLogger(__name__)

# RedisStorage хранит FSM-состояние между перезапусками.
# Для polling-режима (без webhook) обязателен RedisStorage.
storage = RedisStorage.from_url(
    settings.redis_url,
    state_ttl=86400,   # FSM жива 24ч без активности
    data_ttl=86400,
)

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=storage)


async def on_startup() -> None:
    me = await bot.get_me()
    log.info("Bot started as @%s (id=%s)", me.username, me.id)


async def on_shutdown() -> None:
    log.info("Bot shutting down...")
    await dp.storage.close()
    await bot.session.close()
