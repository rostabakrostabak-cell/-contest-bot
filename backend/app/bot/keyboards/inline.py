"""Inline-клавиатуры: списки, подтверждения, выбор действий."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.texts import Texts
from app.models.seller import SellerCategory
from app.models.receipt import RejectReason

texts = Texts()


def shop_picker(shops: list) -> InlineKeyboardMarkup:
    """Кнопки магазинов."""
    builder = InlineKeyboardBuilder()
    for shop in shops:
        builder.row(InlineKeyboardButton(
            text=shop.name,
            callback_data=f"shop:{shop.id}",
        ))
    return builder.as_markup()


def seller_picker_list(sellers: list, shop_id: int = 0, saved_seller=None) -> InlineKeyboardMarkup:
    """Список продавцов + кнопка ввести вручную.
    Сохранённый продавец отмечен ✓.
    """
    builder = InlineKeyboardBuilder()
    for seller in sellers:
        icon = "✓ " if saved_seller and seller.id == saved_seller.id else ""
        builder.row(InlineKeyboardButton(
            text=f"{icon}{seller.full_name}",
            callback_data=f"sel:{seller.id}",
        ))

    builder.row(InlineKeyboardButton(
        text="✏️ Ввести ФИ вручную",
        callback_data=f"new_sel:{shop_id}",
    ))
    return builder.as_markup()


def category_picker() -> InlineKeyboardMarkup:
    """Выбор роли: день/ночь."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="☀️ Дневная", callback_data="cat:day"),
        InlineKeyboardButton(text="🌙 Ночная", callback_data="cat:night"),
    )
    return builder.as_markup()


def confirm_receipt() -> InlineKeyboardMarkup:
    """Подтверждение чека."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_receipt"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_fsm"),
    )
    return builder.as_markup()


# ─── Админ — карточка заявки ──────────────────────────────────────────────────

def admin_receipt_card(receipt_id: int) -> InlineKeyboardMarkup:
    """Кнопки модерации: подтвердить / на доработку / отклонить."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"ar:approve:{receipt_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="↩️ На доработку", callback_data=f"ar:retry:{receipt_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"ar:reject:{receipt_id}"),
    )
    return builder.as_markup()


def admin_reject_reasons(receipt_id: int, action: str = "reject") -> InlineKeyboardMarkup:
    """Причины отклонения."""
    builder = InlineKeyboardBuilder()
    if action == "reject":
        reasons = [
            ("сумма не подходит", "amount"),
            ("чек устарел", "old"),
        ]
    else:
        reasons = [
            ("сделайте новое фото", "photo"),
        ]

    for label, code in reasons:
        icon = "❌" if action == "reject" else "↩️"
        builder.row(InlineKeyboardButton(
            text=f"{icon} {label}",
            callback_data=f"rr:{action}:{code}:{receipt_id}",
        ))

    builder.row(InlineKeyboardButton(
        text="◀ Назад",
        callback_data=f"ar:back:{receipt_id}",
    ))
    return builder.as_markup()


def admin_inline_menu() -> InlineKeyboardMarkup:
    """Главное меню админа."""
    builder = InlineKeyboardBuilder()
    items = [
        ("📋 Новые чеки", "am:pending"),
        ("✅ Подтверждённые", "am:approved"),
        ("❌ Отклонённые", "am:rejected"),
        ("📊 Экспорт", "am:export"),
        ("👥 Продавцы", "am:sellers"),
        ("🏪 Магазины", "am:shops"),
        ("⚙️ Настройки", "am:settings"),
        ("🧪 Итоги", "am:final"),
    ]
    for label, data in items:
        builder.row(InlineKeyboardButton(text=label, callback_data=data))
    return builder.as_markup()


def admin_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="◀ Админ-панель", callback_data="am:menu"),
    ]])
