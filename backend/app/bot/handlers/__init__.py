"""Регистрация всех роутеров в dp."""
from aiogram import Dispatcher

from app.bot.handlers import common
from app.bot.handlers.seller import seller_router
from app.bot.handlers.admin import admin_router


def register_routers(dp: Dispatcher) -> None:
    dp.include_router(common.router)
    dp.include_router(seller_router)
    dp.include_router(admin_router)
