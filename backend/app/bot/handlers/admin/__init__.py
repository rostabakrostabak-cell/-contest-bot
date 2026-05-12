"""Админ роутер."""
from aiogram import Router

from app.bot.handlers.admin import receipts

admin_router = Router()
admin_router.include_router(receipts.router)
