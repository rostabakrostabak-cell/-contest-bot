"""Reply-клавиатуры: главное меню продавца и админа."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from app.config import get_settings

settings = get_settings()


def seller_main_menu(approved_count: int = 0) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📋 Отправить чек"),
        KeyboardButton(text=f"📋 Мои чеки ({approved_count})"),
    )
    builder.row(
        KeyboardButton(text="🏪 Рейтинг магазинов"),
        KeyboardButton(text="🏆 Рейтинг продавцов"),
    )
    builder.row(
        KeyboardButton(text="🧪 Колба"),
        KeyboardButton(text="💬 Связаться с админом"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="⚙️ Админ-панель"))
    return builder.as_markup(resize_keyboard=True)
