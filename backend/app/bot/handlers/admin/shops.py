"""Админ: CRUD магазинов."""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, func

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from app.bot.states import AdminShopAdd
from app.bot.texts import Texts
from app.models.shop import Shop

log = logging.getLogger(__name__)
router = Router()
texts = Texts()


# ─── Меню → список магазинов ────────────────────────────────────────────────

@router.callback_query(F.data == "am:shops")
async def menu_shops -> None:
    await _shop_list(cq, data)


async def _shop_list -> None:
    db = data["db_session"]
    shops = (await db.execute(select(Shop).order_by(Shop.name))).scalars().all()

    builder = InlineKeyboardBuilder()
    for s in shops:
        active_icon = "✅" if s.is_active else "🚫"
        builder.row(InlineKeyboardButton(
            text=f"{active_icon} {s.name}",
            callback_data=f"sh:{s.id}",
        ))
    builder.row(InlineKeyboardButton(text="➕ Добавить магазин", callback_data="asa:start"))
    builder.row(InlineKeyboardButton(text="◀ Админ-панель", callback_data="am:menu"))

    await cq.message.edit_text(
        f"<b>🏪 Магазины</b> ({len(shops)} всего)\n\nВыберите магазин:",
        reply_markup=builder.as_markup(),
    )
    await cq.answer()


# ─── Карточка магазина ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("sh:"))
async def shop_card -> None:
    shop_id = int(cq.data.split(":")[1])
    db = data["db_session"]

    shop: Shop | None = await db.get(Shop, shop_id)
    if not shop:
        await cq.answer("Магазин не найден.", show_alert=True)
        return

    from app.models.seller import Seller
    seller_count = (await db.execute(
        select(func.count(Seller.id)).where(Seller.shop_id == shop_id)
    )).scalar() or 0

    text = (
        f"<b>🏪 {shop.name}</b>\n\n"
        f"📊 Статус: {'✅ Активен' if shop.is_active else '🚫 Неактивен'}\n"
        f"👥 Продавцов: {seller_count}\n"
    )

    builder = InlineKeyboardBuilder()
    if shop.is_active:
        builder.row(InlineKeyboardButton(text="🚫 Деактивировать", callback_data=f"sh:deact:{shop.id}"))
    else:
        builder.row(InlineKeyboardButton(text="✅ Активировать", callback_data=f"sh:act:{shop.id}"))
    builder.row(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"sh:del:{shop.id}"))
    builder.row(InlineKeyboardButton(text="◀ К списку", callback_data="am:shops"))

    await cq.message.edit_text(text, reply_markup=builder.as_markup())
    await cq.answer()


# ─── Активация / деактивация ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("sh:deact:"))
async def shop_deactivate -> None:
    shop_id = int(cq.data.split(":")[2])
    db = data["db_session"]
    shop: Shop | None = await db.get(Shop, shop_id)
    if shop:
        shop.is_active = False
        await db.commit()
    await cq.message.answer("🚫 Магазин деактивирован.")
    await cq.answer()


@router.callback_query(F.data.startswith("sh:act:"))
async def shop_activate -> None:
    shop_id = int(cq.data.split(":")[2])
    db = data["db_session"]
    shop: Shop | None = await db.get(Shop, shop_id)
    if shop:
        shop.is_active = True
        await db.commit()
    await cq.message.answer("✅ Магазин активирован.")
    await cq.answer()


# ─── Удаление ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("sh:del:"))
async def shop_delete -> None:
    shop_id = int(cq.data.split(":")[2])
    db = data["db_session"]

    from app.models.seller import Seller
    has_sellers = (await db.execute(
        select(func.count(Seller.id)).where(Seller.shop_id == shop_id)
    )).scalar() > 0

    if has_sellers:
        await cq.message.answer(
            "⚠️ Удалить нельзя: за магазином закреплены продавцы.\n"
            "Сначала удалите или перенесите продавцов.",
        )
    else:
        shop: Shop | None = await db.get(Shop, shop_id)
        if shop:
            await db.delete(shop)
            await db.commit()
        await cq.message.answer("🗑 Магазин удалён.")
    await cq.answer()


# ─── Добавление магазина ─────────────────────────────────────────────────────

@router.callback_query(F.data == "asa:start")
async def add_shop_start(cq: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminShopAdd.enter_name)
    await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer("Введите <b>название магазина</b>:")
    await cq.answer()


@router.message(AdminShopAdd.enter_name)
async def add_shop_name -> None:
    name = (message.text or "").strip()
    if not name or len(name) < 2:
        await message.answer("Название слишком короткое. Введите минимум 2 символа:")
        return

    db = data["db_session"]
    existing = (await db.execute(
        select(Shop).where(Shop.name.ilike(name))
    )).scalar_one_or_none()

    if existing:
        await message.answer(f"Магазин с названием «{name}» уже существует.")
        return

    shop = Shop(name=name, is_active=True)
    db.add(shop)
    await db.commit()

    await state.clear()
    await message.answer(f"✅ Магазин <b>{name}</b> добавлен.")