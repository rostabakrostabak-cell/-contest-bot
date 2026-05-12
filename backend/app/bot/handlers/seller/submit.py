"""FSM-роутер отправки чека: магазин → ФИ → роль → сумма → фото."""
import re
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.keyboards.inline import (
    shop_picker, seller_picker_list, category_picker,
)
from app.bot.keyboards.main import seller_main_menu
from app.bot.states import SubmitReceipt
from app.bot.texts import Texts
from app.models.seller import Seller, SellerCategory, SellerSource
from app.models.shop import Shop
from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User
from app.services.contest_state import is_submissions_open
from app.config import get_settings

router = Router()

settings = get_settings()
texts = Texts()

NAME_RE = re.compile(r"^[а-яА-Яa-zA-ZЁё]+ [а-яА-Яa-zA-ZЁё]+$")


def _normalize_name(raw: str) -> str:
    parts = raw.strip().split()
    return " ".join(p.capitalize() for p in parts if p)


def _parse_amount(raw: str) -> Decimal | None:
    normalized = raw.replace(" ", "").replace(",", ".")
    try:
        val = Decimal(normalized)
        if 0 < val <= Decimal("9999999.99"):
            return val
    except (InvalidOperation, ValueError, TypeError):
        pass
    return None


# ─── Entry: выбор магазина ─────────────────────────────────────────────────

@router.message(F.text == "📋 Отправить чек")
async def start_submit(message: Message, state: FSMContext, db_session, user) -> None:
    if not await is_submissions_open(db_session):
        await message.answer(texts.submissions_closed)
        return

    await state.clear()
    await state.set_state(SubmitReceipt.pick_shop)

    shops = (await db_session.execute(
        select(Shop).where(Shop.is_active == True).order_by(Shop.name)
    )).scalars().all()

    if not shops:
        await message.answer("⚠️ Нет доступных магазинов. Обратитесь к администратору.")
        return

    await message.answer(texts.pick_shop, reply_markup=shop_picker(shops))


# ─── Выбор магазина ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("shop:"), SubmitReceipt.pick_shop)
async def pick_shop(cq: CallbackQuery, state: FSMContext, db_session, user) -> None:
    shop_id = int(cq.data.split(":")[1])
    await state.update_data(shop_id=shop_id)

    sellers = (await db_session.execute(
        select(Seller)
        .where(Seller.shop_id == shop_id)
        .order_by(Seller.full_name)
    )).scalars().all()

    # Проверяем сохранённого продавца
    saved_seller = None
    if user.last_seller_id:
        saved_seller = await db_session.get(Seller, user.last_seller_id)
        if saved_seller and saved_seller.shop_id != shop_id:
            saved_seller = None

    await state.set_state(SubmitReceipt.pick_seller)
    await cq.message.edit_reply_markup(
        reply_markup=seller_picker_list(sellers, saved_seller)
    )
    await cq.answer()


# ─── Выбор ФИ (существующий) ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("sel:"), SubmitReceipt.pick_seller)
async def pick_seller(cq: CallbackQuery, state: FSMContext, db_session, user) -> None:
    seller_id = int(cq.data.split(":")[1])
    seller: Seller = await db_session.get(Seller, seller_id)
    await state.update_data(
        seller_id=seller.id,
        seller_name=seller.full_name,
        seller_shop_id=seller.shop_id,
        category=seller.category.value,
    )
    user.last_seller_id = seller.id
    await db_session.commit()

    await state.set_state(SubmitReceipt.enter_amount)
    await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer(texts.enter_amount)
    await cq.answer()


# ─── Ввод ФИ вручную ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("new_sel:"), SubmitReceipt.pick_seller)
async def new_seller_start(cq: CallbackQuery, state: FSMContext) -> None:
    shop_id = int(cq.data.split(":")[1])
    await state.update_data(new_seller_shop_id=shop_id)
    await state.set_state(SubmitReceipt.enter_name)
    await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer(texts.enter_name)
    await cq.answer()


@router.message(SubmitReceipt.enter_name)
async def enter_name(message: Message, state: FSMContext, db_session) -> None:
    raw = message.text or ""
    if not NAME_RE.match(raw.strip()):
        await message.answer(texts.name_error)
        return

    name = _normalize_name(raw)
    sdata = await state.get_data()
    shop_id = sdata["new_seller_shop_id"]

    # Проверяем, есть ли уже
    existing = (await db_session.execute(
        select(Seller)
        .where(Seller.shop_id == shop_id)
        .where(Seller.full_name.ilike(name))
    )).scalar_one_or_none()

    if existing:
        await state.update_data(
            seller_id=existing.id,
            seller_name=existing.full_name,
            seller_shop_id=existing.shop_id,
            category=existing.category.value,
        )
        await state.set_state(SubmitReceipt.enter_amount)
        await message.answer(texts.enter_amount)
    else:
        await state.update_data(new_seller_name=name)
        await state.set_state(SubmitReceipt.pick_category)
        await message.answer(texts.pick_category, reply_markup=category_picker())


# ─── Выбор роли (для нового) ──────────────────────────────────────────

@router.callback_query(F.data.startswith("cat:"), SubmitReceipt.pick_category)
async def pick_category(cq: CallbackQuery, state: FSMContext, db_session, user) -> None:
    cat_str = cq.data.split(":")[1]
    category = "day" if cat_str == "day" else "night"
    sdata = await state.get_data()

    name = sdata["new_seller_name"]
    shop_id = sdata["new_seller_shop_id"]

    seller = Seller(
        shop_id=shop_id,
        full_name=name,
        category=category,
        source=SellerSource.MANUAL,
    )
    db_session.add(seller)
    await db_session.flush()
    await db_session.commit()

    await state.update_data(
        seller_id=seller.id,
        seller_name=name,
        seller_shop_id=shop_id,
        category=category,
    )
    user.last_seller_id = seller.id
    await db_session.commit()

    # Уведомляем админа
    shop = await db_session.get(Shop, shop_id)
    try:
        from app.bot.loader import bot
        cat_label = "Дневная" if category == "day" else "Ночная"
        await bot.send_message(
            chat_id=settings.admin_tg_id,
            text=f"🆕 Новый продавец: {name}\n🏪 {shop.name if shop else '?'}\n🏷 {cat_label}",
        )
    except Exception:
        pass

    await state.set_state(SubmitReceipt.enter_amount)
    await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer(texts.enter_amount)
    await cq.answer()


# ─── Сумма ────────────────────────────────────────────────────────────

@router.message(SubmitReceipt.enter_amount)
async def enter_amount(message: Message, state: FSMContext) -> None:
    amount = _parse_amount(message.text or "")
    if amount is None:
        await message.answer(texts.amount_error)
        return

    await state.update_data(amount=str(amount))
    await state.set_state(SubmitReceipt.attach_photo)
    await message.answer(texts.attach_photo)


# ─── Фото ────────────────────────────────────────────────────────────

@router.message(SubmitReceipt.attach_photo, F.photo)
async def attach_photo(message: Message, state: FSMContext) -> None:
    photo = message.photo[-1]
    await state.update_data(photo_file_id=photo.file_id)
    await state.set_state(SubmitReceipt.confirm)
    await _show_confirm(message, state)


@router.message(SubmitReceipt.attach_photo)
async def not_photo(message: Message) -> None:
    await message.answer(texts.not_a_photo)


# ─── Подтверждение и отправка ──────────────────────────────────────────

@router.callback_query(F.data == "confirm_receipt", SubmitReceipt.confirm)
async def confirm_receipt(cq: CallbackQuery, state: FSMContext, db_session, user) -> None:
    bot = cq.bot
    sdata = await state.get_data()

    receipt = Receipt(
        user_id=user.id,
        seller_id=sdata["seller_id"],
        shop_id=sdata["seller_shop_id"],
        category=SellerCategory(sdata["category"]),
        amount=Decimal(sdata["amount"]),
        photo_file_id=sdata["photo_file_id"],
        status="pending",
    )
    db_session.add(receipt)
    await db_session.flush()
    await db_session.refresh(receipt)
    await db_session.commit()

    # Отправляем админу
    shop = await db_session.get(Shop, sdata["seller_shop_id"])
    seller = await db_session.get(Seller, sdata["seller_id"])
    await _send_admin_receipt(bot, receipt, shop, seller)

    await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer(texts.submit_success.format(receipt_id=receipt.id))
    await cq.message.answer(texts.main_menu, reply_markup=seller_main_menu())
    await cq.answer()


@router.callback_query(F.data == "cancel_fsm")
async def cancel_fsm(cq: CallbackQuery, state: FSMContext, db_session, user) -> None:
    await state.clear()
    await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer(texts.cancel)

    # Считаем approved чеки
    from sqlalchemy import func
    from app.models.receipt import Receipt as R
    count = await db_session.execute(
        func.count(R.id)
        .where(R.user_id == user.id)
        .where(R.status == "approved")
    )
    approved_count = count.scalar() or 0
    await cq.message.answer(texts.main_menu, reply_markup=seller_main_menu(approved_count))


# ─── Помощники ────────────────────────────────────────────────────────

async def _show_confirm(message: Message, state: FSMContext) -> None:
    from app.bot.keyboards.inline import confirm_receipt as confirm_kb
    from app.db import session_scope

    sdata = await state.get_data()

    async with session_scope() as db_session:
        shop = (await db_session.execute(
            select(Shop).where(Shop.id == sdata["seller_shop_id"])
        )).scalar_one_or_none()
        cat_label = "Дневная" if sdata["category"] == "day" else "Ночная"
        amount_fmt = f"{float(sdata['amount']):,.2f}".replace(",", " ")

        await message.answer(
            f"<b>📋 Проверьте данные:</b>\n\n"
            f"🏪 Магазин: {shop.name if shop else '?'}\n"
            f"👤 ФИ: {sdata['seller_name']}\n"
            f"🏷 Категория: {cat_label}\n"
            f"💰 Сумма: {amount_fmt} ₽\n\n"
            f"Всё верно?",
            reply_markup=confirm_kb(),
        )
        await message.answer_photo(
            photo=sdata["photo_file_id"],
            caption="📷 Фото чека:",
        )


async def _send_admin_receipt(bot, receipt, shop, seller) -> None:
    from app.time import fmt_msk

    cat_label = "Дневная" if receipt.category == "day" else "Ночная"
    amount_fmt = f"{float(receipt.amount):,.2f}".replace(",", " ")

    text = (
        f"<b>📋 Новая заявка #{receipt.id}</b>\n\n"
        f"🏪 Магазин: {shop.name if shop else '?'}\n"
        f"👤 ФИ: {seller.full_name if seller else '?'}\n"
        f"🏷 Категория: {cat_label}\n"
        f"💰 Сумма: <b>{amount_fmt} ₽</b>\n"
        f"📅 {fmt_msk(receipt.submitted_at)}"
    )

    from app.bot.keyboards.inline import admin_receipt_card

    try:
        await bot.send_photo(
            chat_id=settings.admin_tg_id,
            photo=receipt.photo_file_id,
            caption=text,
            reply_markup=admin_receipt_card(receipt.id),
        )
    except Exception:
        pass
