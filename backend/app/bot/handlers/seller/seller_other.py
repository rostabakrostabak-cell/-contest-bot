"""Хендлеры продавца: рейтинги, мои чеки, связь с админом."""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from app.bot.keyboards.main import seller_main_menu
from app.bot.states import ContactAdmin
from app.bot.texts import Texts
from app.models.seller import Seller, SellerCategory
from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User
from app.models.chat_message import ChatMessage, ChatDirection
from app.models.shop import Shop
from app.services.ranking import top_shops_live, top_sellers_live
from app.config import get_settings

log = logging.getLogger(__name__)
router = Router()

settings = get_settings()
texts = Texts()


async def send_main_menu(message: Message, data: dict) -> None:
    """Отправляет главное меню с актуальным счётчиком."""
    db = data["db_session"]
    user: User = data["user"]
    count = await db.execute(
        func.count(Receipt.id)
        .where(Receipt.user_id == user.id)
        .where(text("receipts.status = 'approved'::receipt_status"))
    )
    approved_count = count.scalar() or 0
    await message.answer(texts.main_menu, reply_markup=seller_main_menu(approved_count))


# ─── Рейтинг магазинов ──────────────────────────────────────────────────────

@router.message(F.text == "🏪 Рейтинг магазинов")
async def show_shops_ranking(message: Message, data: dict) -> None:
    db = data["db_session"]

    day_shops = await top_shops_live(db, "day", limit=3)
    night_shops = await top_shops_live(db, "night", limit=3)

    lines = ["<b>🏪 Рейтинг магазинов</b>\n"]

    lines.append("\n☀️ Дневные:")
    if day_shops:
        for i, s in enumerate(day_shops, 1):
            lines.append(f"  {i}. {s.shop_name} — {s.approved_count} чеков")
    else:
        lines.append("  — пока нет данных")

    lines.append("\n🌙 Ночные:")
    if night_shops:
        for i, s in enumerate(night_shops, 1):
            lines.append(f"  {i}. {s.shop_name} — {s.approved_count} чеков")
    else:
        lines.append("  — пока нет данных")

    await message.answer("\n".join(lines))
    await send_main_menu(message, data)


# ─── Рейтинг продавцов ─────────────────────────────────────────────────────

@router.message(F.text == "🏆 Рейтинг продавцов")
async def show_sellers_ranking(message: Message, data: dict) -> None:
    db = data["db_session"]

    day_sellers = await top_sellers_live(db, "day", limit=3)
    night_sellers = await top_sellers_live(db, "night", limit=3)

    lines = ["<b>🏆 Рейтинг продавцов</b>\n"]

    lines.append("\n☀️ Дневные:")
    if day_sellers:
        for i, s in enumerate(day_sellers, 1):
            lines.append(f"  {i}. {s.full_name} ({s.shop_name}) — {s.approved_count} чеков")
    else:
        lines.append("  — пока нет данных")

    lines.append("\n🌙 Ночные:")
    if night_sellers:
        for i, s in enumerate(night_sellers, 1):
            lines.append(f"  {i}. {s.full_name} ({s.shop_name}) — {s.approved_count} чеков")
    else:
        lines.append("  — пока нет данных")

    await message.answer("\n".join(lines))
    await send_main_menu(message, data)


# ─── Мои чеки ──────────────────────────────────────────────────────────────

@router.message(F.text.startswith("📋 Мои чеки"))
async def show_my_receipts(message: Message, data: dict) -> None:
    db = data["db_session"]
    user: User = data["user"]

    rows = await db.execute(
        select(Receipt)
        .where(Receipt.user_id == user.id)
        .where(text("receipts.status = 'approved'::receipt_status"))
        .order_by(Receipt.submitted_at.desc())
    )
    approved = rows.scalars().all()

    if not approved:
        await message.answer("📋 У вас пока нет подтверждённых чеков.")
    else:
        lines = [f"<b>📋 Ваши подтверждённые чеки</b> ({len(approved)}):\n"]
        for r in approved:
            from app.time import fmt_msk
            lines.append(f"  • #{r.id} — {fmt_amount(r.amount)} ₽ ({fmt_msk(r.submitted_at)})")

        await message.answer("\n".join(lines))

    await send_main_menu(message, data)


# ─── Связь с админом ──────────────────────────────────────────────────────

@router.message(F.text == "💬 Связаться с админом")
async def start_contact(message: Message, state: FSMContext) -> None:
    await state.set_state(ContactAdmin.typing_message)
    await message.answer(
        "💬 <b>Напишите сообщение администратору:</b>\n\n"
        "Ваше обращение будет направлено с указанием ваших данных."
    )


@router.message(ContactAdmin.typing_message)
async def contact_message(message: Message, state: FSMContext, data: dict) -> None:
    db = data["db_session"]
    user: User = data["user"]
    bot = data["bot"]

    text = (message.text or "").strip()
    if not text:
        await message.answer("Сообщение не может быть пустым. Напишите текст:")
        return

    # Сохраняем сообщение
    chat_msg = ChatMessage(
        user_id=user.id,
        direction=ChatDirection.USER_TO_ADMIN,
        text=text,
    )
    db.add(chat_msg)
    await db.commit()

    # Получаем данные продавца
    seller = None
    if user.last_seller_id:
        seller = await db.get(Seller, user.last_seller_id)
    shop = await db.get(Shop, seller.shop_id) if seller else None

    # Отправляем админу
    header = f"📨 <b>Обращение от продавца</b>\n\n"
    if seller:
        header += f"👤 {seller.full_name}\n"
    if shop:
        header += f"🏪 {shop.name}\n"
    if seller:
        header += f"🏷 {'Дневная' if seller.category == 'day' else 'Ночная'}\n"
    header += f"\n💬 Текст:\n{text}"

    try:
        await bot.send_message(chat_id=settings.admin_tg_id, text=header)
    except Exception as e:
        log.error("Failed to forward contact: %s", e)

    await state.clear()
    await message.answer("✅ Сообщение отправлено! Ожидайте ответа.")
    await send_main_menu(message, data)


def fmt_amount(amount) -> str:
    return f"{float(amount):,.2f}".replace(",", " ")
