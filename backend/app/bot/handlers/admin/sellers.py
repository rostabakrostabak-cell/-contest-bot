"""Админ: список продавцов, добавление, редактирование, удаление."""
import logging
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, func

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import AdminSellerEdit, AdminSellerAdd
from app.bot.texts import Texts, fmt_amount
from app.models.seller import Seller, SellerCategory, SellerSource
from app.models.shop import Shop

log = logging.getLogger(__name__)
router = Router()
texts = Texts()

PAGESIZE = 12
NAME_RE = re.compile(r"^[а-яА-Яa-zA-ZЁё]+ [а-яА-Яa-zA-ZЁё]+$")


def _normalize_name(raw: str) -> str:
    parts = raw.strip().split()
    return " ".join(p.capitalize() for p in parts if p)


# ─── Меню → список продавцов ─────────────────────────────────────────────────

@router.callback_query(F.data == "am:sellers")
async def menu_sellers(cq: CallbackQuery, data: dict) -> None:
    await _seller_list(cq, data, 0, None)


# ─── Пагинация / фильтр ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("sl:"))
async def seller_list_page(cq: CallbackQuery, data: dict) -> None:
    # sl:{shop_id}:{page}
    parts = cq.data.split(":")
    shop_id = int(parts[1]) if parts[1] != "all" else None
    page = int(parts[2])
    await _seller_list(cq, data, page, shop_id)


async def _seller_list(
    cq: CallbackQuery,
    data: dict,
    page: int,
    filter_shop_id: int | None,
) -> None:
    db = data["db_session"]
    offset = page * PAGESIZE

    # Считаем total
    count_q = select(func.count(Seller.id))
    if filter_shop_id:
        count_q = count_q.where(Seller.shop_id == filter_shop_id)
    total = (await db.execute(count_q)).scalar()

    # Данные
    q = (
        select(Seller, Shop.name)
        .join(Shop, Seller.shop_id == Shop.id)
        .order_by(Seller.full_name)
        .offset(offset)
        .limit(PAGESIZE + 1)
    )
    if filter_shop_id:
        q = q.where(Seller.shop_id == filter_shop_id)
    rows = (await db.execute(q)).all()
    has_next = len(rows) > PAGESIZE
    rows = rows[:PAGESIZE]

    # Фильтр по магазинам
    shops = (await db.execute(select(Shop).order_by(Shop.name))).scalars().all()
    shop_filter_buttons = []
    for s in shops:
        shop_filter_buttons.append(
            InlineKeyboardButton(
                text=f"{'✅ ' if filter_shop_id == s.id else ''}{s.name}",
                callback_data=f"sl:{s.id}:0",
            )
        )
    shop_filter_buttons.append(
        InlineKeyboardButton(text="Все", callback_data="sl:all:0")
    )

    builder = InlineKeyboardBuilder()
    for seller_row, shop_name in rows:
        cat_icon = "☀️" if seller_row.category == "day" else "🌙"
        builder.row(InlineKeyboardButton(
            text=f"{cat_icon} {seller_row.full_name} ({shop_name})",
            callback_data=f"se:{seller_row.id}",
        ))

    # Навигация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀", callback_data=f"sl:{'all' if filter_shop_id is None else str(filter_shop_id)}:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="▶", callback_data=f"sl:{'all' if filter_shop_id is None else str(filter_shop_id)}:{page + 1}"))

    builder.row(*nav)
    builder.row(InlineKeyboardButton(text="➕ Добавить продавца", callback_data="asa:pick_shop"))

    # Фильтр магазинов — отдельным блоком
    filter_label = f"Фильтр: {next((s.name for s in shops if s.id == filter_shop_id), 'Все')}" if filter_shop_id else "Все магазины"
    await cq.message.edit_text(
        f"<b>👥 Продавцы</b> ({total} всего)\nФильтр: {filter_label}\n\nВыберите продавца:",
        reply_markup=_build_sellers_keyboard(builder, shop_filter_buttons),
    )
    await cq.answer()


def _build_sellers_keyboard(builder: InlineKeyboardBuilder, shop_filter_buttons: list) -> InlineKeyboardMarkup:
    # Фильтр магазинов в 2 колонки
    from app.bot.texts import Texts
    builder.row(InlineKeyboardButton(text="─ Фильтр магазинов ─", callback_data="noop"))
    # 2 колонки
    for i in range(0, len(shop_filter_buttons), 2):
        row = shop_filter_buttons[i:i+2]
        builder.row(*row)
    return builder.as_markup()


# ─── Карточка продавца ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("se:"))
async def seller_card(cq: CallbackQuery, data: dict) -> None:
    seller_id = int(cq.data.split(":")[1])
    db = data["db_session"]

    seller: Seller | None = await db.get(Seller, seller_id)
    if not seller:
        await cq.answer("Продавец не найден.", show_alert=True)
        return

    shop: Shop | None = await db.get(Shop, seller.shop_id)
    cat_label = "☀️ дневная" if seller.category == 'day' else "🌙 ночная"
    source_label = {"preload": "из Excel", "manual": "добавлен продавцом", "admin": "добавлен админом"}[seller.source.value]

    text = (
        f"<b>👤 {seller.full_name}</b>\n\n"
        f"🏪 Магазин: {shop.name if shop else '?'}\n"
        f"🏷 Категория: {cat_label}\n"
        f"📥 Источник: {source_label}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"ese:{seller.id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"ds:{seller.id}"),
    )
    builder.row(InlineKeyboardButton(text="◀ К списку", callback_data="sl:all:0"))

    await cq.message.edit_text(text, reply_markup=builder.as_markup())
    await cq.answer()


# ─── Добавление продавца ──────────────────────────────────────────────────────

@router.callback_query(F.data == "asa:pick_shop")
async def add_seller_pick_shop(cq: CallbackQuery, state: FSMContext, data: dict) -> None:
    db = data["db_session"]
    shops = (await db.execute(select(Shop).where(Shop.is_active == True).order_by(Shop.name))).scalars().all()

    builder = InlineKeyboardBuilder()
    for s in shops:
        builder.row(InlineKeyboardButton(text=s.name, callback_data=f"asa:shop:{s.id}"))
    builder.row(InlineKeyboardButton(text="◀ Назад", callback_data="am:sellers"))

    await cq.message.edit_text("Выберите <b>магазин</b> для нового продавца:", reply_markup=builder.as_markup())
    await cq.answer()


@router.callback_query(F.data.startswith("asa:shop:"))
async def add_seller_shop(cq: CallbackQuery, state: FSMContext, data: dict) -> None:
    shop_id = int(cq.data.split(":")[2])
    await state.set_state(AdminSellerAdd.enter_name)
    await state.update_data(shop_id=shop_id)
    await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer(texts.enter_name)
    await cq.answer()


@router.message(AdminSellerAdd.enter_name)
async def add_seller_name(message: Message, state: FSMContext, data: dict) -> None:
    raw = message.text or ""
    if not NAME_RE.match(raw.strip()):
        await message.answer(texts.name_error)
        return

    name = _normalize_name(raw)
    sdata = await state.get_data()
    shop_id = sdata["shop_id"]

    db = data["db_session"]
    existing = (await db.execute(
        select(Seller).where(Seller.shop_id == shop_id).where(Seller.full_name.ilike(name))
    )).scalar_one_or_none()

    if existing:
        await state.clear()
        await message.answer(f"Такой продавец уже есть в магазине: {existing.full_name}")
        return

    await state.update_data(name=name)
    await state.set_state(AdminSellerAdd.pick_category)
    await message.answer(texts.pick_category, reply_markup=_category_picker_inline())


def _category_picker_inline() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="☀️ Дневная", callback_data="asa:cat:day"),
        InlineKeyboardButton(text="🌙 Ночная", callback_data="asa:cat:night"),
    )
    builder.row(InlineKeyboardButton(text="◀ Отмена", callback_data="am:sellers"))
    return builder.as_markup()


@router.callback_query(F.data.startswith("asa:cat:"), AdminSellerAdd.pick_category)
async def add_seller_category(cq: CallbackQuery, state: FSMContext, data: dict) -> None:
    cat_str = cq.data.split(":")[2]
    category = "day" if cat_str == "day" else "night"
    sdata = await state.get_data()
    db = data["db_session"]

    seller = Seller(
        shop_id=sdata["shop_id"],
        full_name=sdata["name"],
        category=category,
        source=SellerSource.ADMIN,
    )
    db.add(seller)
    await db.flush()
    await db.commit()

    await state.clear()
    await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer(f"✅ Продавец <b>{seller.full_name}</b> добавлен.")
    await cq.answer()


# ─── Редактирование продавца ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("ese:"))
async def edit_seller_start(cq: CallbackQuery, state: FSMContext, data: dict) -> None:
    seller_id = int(cq.data.split(":")[1])
    db = data["db_session"]
    seller: Seller | None = await db.get(Seller, seller_id)
    if not seller:
        await cq.answer("Продавец не найден.", show_alert=True)
        return

    await state.set_state(AdminSellerEdit.pick_field)
    await state.update_data(seller_id=seller_id)

    cat_label = "☀️ дневная" if seller.category == 'day' else "🌙 ночная"
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏷 Категория", callback_data="ese:cat"))
    builder.row(InlineKeyboardButton(text="🏪 Магазин", callback_data="ese:shop"))
    builder.row(InlineKeyboardButton(text="◀ Отмена", callback_data=f"se:{seller_id}"))

    await cq.message.edit_text(
        f"✏️ <b>Редактирование:</b> {seller.full_name}\nТекущая категория: {cat_label}\n\nЧто изменить?",
        reply_markup=builder.as_markup(),
    )
    await cq.answer()


@router.callback_query(F.data == "ese:cat", AdminSellerEdit.pick_field)
async def edit_seller_cat(cq: CallbackQuery, state: FSMContext, data: dict) -> None:
    sdata = await state.get_data()
    db = data["db_session"]
    seller: Seller | None = await db.get(Seller, sdata["seller_id"])
    if not seller:
        await cq.answer("Продавец не найден.", show_alert=True)
        return

    seller.category = "night" if seller.category == 'day' else "day"
    await db.commit()

    await cq.message.answer(f"✅ Категория изменена на: {'☀️ дневная' if seller.category == 'day' else '🌙 ночная'}")
    await state.clear()
    await cq.answer()


@router.callback_query(F.data == "ese:shop", AdminSellerEdit.pick_field)
async def edit_seller_shop(cq: CallbackQuery, state: FSMContext, data: dict) -> None:
    sdata = await state.get_data()
    db = data["db_session"]
    seller: Seller | None = await db.get(Seller, sdata["seller_id"])
    if not seller:
        await cq.answer("Продавец не найден.", show_alert=True)
        return

    shops = (await db.execute(select(Shop).where(Shop.is_active == True).order_by(Shop.name))).scalars().all()
    builder = InlineKeyboardBuilder()
    for s in shops:
        builder.row(InlineKeyboardButton(
            text=f"{'✅ ' if s.id == seller.shop_id else ''}{s.name}",
            callback_data=f"ese:shop:{seller.id}:{s.id}",
        ))
    builder.row(InlineKeyboardButton(text="◀ Назад", callback_data=f"se:{seller.id}"))

    await cq.message.edit_text("Выберите <b>новый магазин</b>:", reply_markup=builder.as_markup())
    await cq.answer()


@router.callback_query(F.data.startswith("ese:shop:"))
async def edit_seller_shop_apply(cq: CallbackQuery, state: FSMContext, data: dict) -> None:
    parts = cq.data.split(":")
    seller_id = int(parts[2])
    new_shop_id = int(parts[3])

    db = data["db_session"]
    seller: Seller | None = await db.get(Seller, seller_id)
    if not seller:
        await cq.answer("Продавец не найден.", show_alert=True)
        return

    seller.shop_id = new_shop_id
    await db.commit()
    await state.clear()

    await cq.message.answer("✅ Магазин изменён.")
    await cq.answer()


# ─── Удаление продавца ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("ds:"))
async def delete_seller(cq: CallbackQuery, state: FSMContext, data: dict) -> None:
    seller_id = int(cq.data.split(":")[1])
    db = data["db_session"]
    seller: Seller | None = await db.get(Seller, seller_id)
    if not seller:
        await cq.answer("Продавец не найден.", show_alert=True)
        return

    # Проверяем связанные чеки
    from app.models.receipt import Receipt
    has_receipts = (await db.execute(
        select(func.count(Receipt.id)).where(Receipt.seller_id == seller_id)
    )).scalar() > 0

    if has_receipts:
        # Удалить нельзя — отвязать
        await cq.message.answer(
            "⚠️ Нельзя удалить: за продавцом закреплены чеки.\n"
            "Продавец останется, но будет скрыт из списков.",
        )
        seller.source = SellerSource.MANUAL  # просто меняем флаг, не удаляем
        await db.commit()
    else:
        await db.delete(seller)
        await db.commit()

    await cq.message.answer("✅ Продавец удалён.")
    await cq.answer()