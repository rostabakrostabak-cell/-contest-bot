"""Продавец роутер."""
from aiogram import Router

from app.bot.handlers.seller import submit, seller_other

seller_router = Router()
seller_router.include_routers(submit.router, seller_other.router)
