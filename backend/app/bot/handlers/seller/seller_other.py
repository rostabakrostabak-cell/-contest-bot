"""Seller handlers: rankings, receipts, contact admin."""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select, text

from app.bot.keyboards.main import seller_main_menu
from app.bot.states import ContactAdmin
from app.bot.texts import Texts
from app.models.seller import Seller, SellerCategory
from app.models.receipt import Receipt
from app.models.user import User
from app.models.chat_message import ChatMessage, ChatDirection
from app.models.shop import Shop
from app.services.ranking import top_shops_live, top_sellers_live
from app.config import get_settings

log = logging.getLogger(__name__)
router = Router()

settings = get_settings()
texts = Texts()


async def send_main_menu(message: Message, user: User, db_session) -> None:
    """Send main menu with actual counter."""
    count = await db_session.execute(
        func.count(Receipt.id)
        .where(Receipt.user_id == user.id)
        .where(text("receipts.status = 'approved'"))
    )
    approved_count = count.scalar() or 0
    await message.answer(texts.main_menu, reply_markup=seller_main_menu(approved_count))


# ─── Shop Rankings ──────────────────────────────────────────────────────

@router.message(F.text == "Рейтинг магазинов")
async def show_shops_ranking(message: Message, db_session) -> None:
    day_shops = await top_shops_live(db_session, "day", limit=3)
    night_shops = await top_shops_live(db_session, "night", limit=3)

    lines = ["<b>Рейтинг магазинов</b>\n"]
    lines.append("\nДневные:")
    if day_shops:
        for i, s in enumerate(day_shops, 1):
            lines.append(f"  {i}. {s.shop_name} — {s.approved_count} чеков")
    else:
        lines.append("  — пока нет данных")

    lines.append("\nНочные:")
    if night_shops:
        for i, s in enumerate(night_shops, 1):
            lines.append(f"  {i}. {s.shop_name} — {s.approved_count} чеков")
    else:
        lines.append("  — пока нет данных")

    await message.answer("\n".join(lines))


# ─── Seller Rankings ───────────────────────────────────────────────────

@router.message(F.text == "Рейтинг продавцов")
async def show_sellers_ranking(message: Message, db_session) -> None:
    day_sellers = await top_sellers_live(db_session, "day", limit=3)
    night_sellers = await top_sellers_live(db_session, "night", limit=3)

    lines = ["<b>Рейтинг продавцов</b>\n"]
    lines.append("\nДневные:")
    if day_sellers:
        for i, s in enumerate(day_sellers, 1):
            lines.append(f"  {i}. {s.full_name} ({s.shop_name}) — {s.approved_count} чеков")
    else:
        lines.append("  — пока нет данных")

    lines.append("\nНочные:")
    if night_sellers:
        for i, s in enumerate(night_sellers, 1):
            lines.append(f"  {i}. {s.full_name} ({s.shop_name}) — {s.approved_count} чеков")
    else:
        lines.append("  — пока нет данных")

    await message.answer("\n".join(lines))


# ─── My Receipts ─────────────────────────────────────────────────────

@router.message(F.text.startswith("Мои чеки"))
async def show_my_receipts(message: Message, user: User, db_session) -> None:
    rows = await db_session.execute(
        select(Receipt)
        .where(Receipt.user_id == user.id)
        .where(text("receipts.status = 'approved'"))
        .order_by(Receipt.submitted_at.desc())
    )
    approved = rows.scalars().all()

    if not approved:
        await message.answer("У вас пока нет подтверждённых чеков.")
    else:
        lines = [f"<b>Ваши подтверждённые чеки</b> ({len(approved)}):\n"]
        for r in approved:
            lines.append(f"  • #{r.id} — {float(r.amount):,.2f} ₽")

        await message.answer("\n".join(lines))

    await send_main_menu(message, user, db_session)


# ─── Contact Admin ──────────────────────────────────────────────────

@router.message(F.text == "Связаться с админом")
async def start_contact(message: Message, state: FSMContext) -> None:
    await state.set_state(ContactAdmin.typing_message)
    await message.answer(
        "Напишите сообщение администратору:\n\n"
        "Ваше обращение будет направлено с указанием ваших данных."
    )


@router.message(ContactAdmin.typing_message)
async def contact_message(message: Message, state: FSMContext, user: User, db_session) -> None:
    text_msg = (message.text or "").strip()
    if not text_msg:
        await message.answer("Сообщение не может быть пустым.")
        return

    chat_msg = ChatMessage(
        user_id=user.id,
        direction=ChatDirection.USER_TO_ADMIN,
        text=text_msg,
    )
    db_session.add(chat_msg)
    await db_session.commit()

    seller = None
    if user.last_seller_id:
        seller = await db_session.get(Seller, user.last_seller_id)
    shop = await db_session.get(Shop, seller.shop_id) if seller else None

    header = f"<b>Обращение от продавца</b>\n\n"
    if seller:
        header += f"{seller.full_name}\n"
    if shop:
        header += f"{shop.name}\n"
    if seller:
        header += f"{'Дневная' if seller.category == SellerCategory.DAY else 'Ночная'}\n"
    header += f"\nТекст:\n{text_msg}"

    try:
        from app.bot.loader import bot
        await bot.send_message(chat_id=settings.admin_tg_id, text=header)
    except Exception as e:
        log.error("Failed to forward contact: %s", e)

    await state.clear()
    await message.answer("Сообщение отправлено!")
    await send_main_menu(message, user, db_session)
