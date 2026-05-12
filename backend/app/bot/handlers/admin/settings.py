"""Админ: главное меню, настройки конкурса, экспорт, итоги, Mini App."""
import logging
import io
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, func

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import AdminSettings
from app.bot.texts import Texts
from app.models.contest_settings import ContestSettings
from app.models.receipt import Receipt, ReceiptStatus
from app.models.seller import Seller, SellerCategory
from app.models.shop import Shop
from app.models.user import User

log = logging.getLogger(__name__)
router = Router()
texts = Texts()


# ─── Главное меню ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "am:menu")
async def admin_menu(cq: CallbackQuery, data: dict) -> None:
    await cq.message.edit_text(
        texts.admin_menu,
        reply_markup=admin_inline_menu(),
    )
    await cq.answer()


def admin_inline_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    items = [
        ("📋 Новые чеки", "am:pending"),
        ("✅ Подтверждённые", "am:approved"),
        ("❌ Отклонённые", "am:rejected"),
        ("📊 Экспорт в Excel", "am:export"),
        ("👥 Продавцы", "am:sellers"),
        ("🏪 Магазины", "am:shops"),
        ("⚙️ Настройки", "am:settings"),
        ("🧪 Mini App", "am:miniapp"),
        ("🏁 Итоги", "am:final"),
    ]
    for label, data in items:
        builder.row(InlineKeyboardButton(text=label, callback_data=data))
    return builder.as_markup()


# ─── Mini App ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "am:miniapp")
async def menu_miniapp(cq: CallbackQuery, data: dict) -> None:
    from app.config import get_settings
    settings = get_settings()

    db = data["db_session"]
    day_count = (await db.execute(
        select(func.count(Receipt.id))
        .where(text("receipts.status = 'approved'::receipt_status"))
        .where(text("receipts.category = 'day'::seller_category"))
    )).scalar() or 0
    night_count = (await db.execute(
        select(func.count(Receipt.id))
        .where(text("receipts.status = 'approved'::receipt_status"))
        .where(text("receipts.category = 'night'::seller_category"))
    )).scalar() or 0

    text = (
        f"<b>🧪 Mini App</b>\n\n"
        f"☀️ Дневных: <b>{day_count}</b> чеков\n"
        f"🌙 Ночных: <b>{night_count}</b> чеков\n\n"
        f"<a href=\"{settings.miniapp_url}\">Ссылка на Mini App</a>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀ Админ-панель", callback_data="am:menu"))
    await cq.message.edit_text(text, reply_markup=builder.as_markup(), disable_web_page_preview=True)
    await cq.answer()


# ─── Настройки ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "am:settings")
async def menu_settings(cq: CallbackQuery, data: dict) -> None:
    db = data["db_session"]
    settings_obj: ContestSettings | None = await db.get(ContestSettings, 1)

    if not settings_obj:
        await cq.message.edit_text(
            "⚠️ Настройки конкурса не найдены. Обратитесь к разработчику.",
            reply_markup=admin_inline_menu(),
        )
        await cq.answer()
        return

    from app.time import fmt_msk
    text = (
        f"<b>⚙️ Настройки конкурса</b>\n\n"
        f"📅 Окончание приёма чеков: {fmt_msk(settings_obj.end_at)}\n"
        f"🎰 Розыгрыш в: {fmt_msk(settings_obj.raffle_at)}\n"
        f"☀️ Цель (дневные): {settings_obj.day_goal} чеков\n"
        f"🌙 Цель (ночные): {settings_obj.night_goal} чеков\n\n"
        f"{'✅ Конкурс завершён' if settings_obj.finalized_at else '⏳ Конкурс идёт'}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✏️ Изменить цели", callback_data="as:goals"))
    builder.row(InlineKeyboardButton(text="◀ Админ-панель", callback_data="am:menu"))

    await cq.message.edit_text(text, reply_markup=builder.as_markup())
    await cq.answer()


@router.callback_query(F.data == "as:goals")
async def settings_goals(cq: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminSettings.enter_day_goal)
    await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer("Введите <b>цель для дневных</b> (число чеков):")
    await cq.answer()


@router.message(AdminSettings.enter_day_goal)
async def settings_day_goal(message: Message, state: FSMContext) -> None:
    try:
        day_goal = int(message.text or "")
        if day_goal <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите положительное число:")
        return

    await state.update_data(day_goal=day_goal)
    await state.set_state(AdminSettings.enter_night_goal)
    await message.answer("Введите <b>цель для ночных</b> (число чеков):")


@router.message(AdminSettings.enter_night_goal)
async def settings_night_goal(message: Message, state: FSMContext, data: dict) -> None:
    try:
        night_goal = int(message.text or "")
        if night_goal <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите положительное число:")
        return

    sdata = await state.get_data()
    db = data["db_session"]

    settings_obj: ContestSettings | None = await db.get(ContestSettings, 1)
    if settings_obj:
        settings_obj.day_goal = sdata["day_goal"]
        settings_obj.night_goal = night_goal
        await db.commit()
        await message.answer(f"✅ Цели обновлены:\n☀️ {sdata['day_goal']} | 🌙 {night_goal}")
    else:
        await message.answer("⚠️ Настройки не найдены.")

    await state.clear()


# ─── Экспорт в Excel ────────────────────────────────────────────────────────

@router.callback_query(F.data == "am:export")
async def menu_export(cq: CallbackQuery, data: dict) -> None:
    builder = InlineKeyboardBuilder()
    items = [
        ("📋 Все чеки", "ex:all"),
        ("☀️ Дневные", "ex:day"),
        ("🌙 Ночные", "ex:night"),
        ("✅ Подтверждённые", "ex:approved"),
    ]
    for label, data_btn in items:
        builder.row(InlineKeyboardButton(text=label, callback_data=data_btn))
    builder.row(InlineKeyboardButton(text="◀ Админ-панель", callback_data="am:menu"))

    await cq.message.edit_text(
        "<b>📊 Экспорт в Excel</b>\n\nВыберите что экспортировать:",
        reply_markup=builder.as_markup(),
    )
    await cq.answer()


@router.callback_query(F.data.startswith("ex:"))
async def export_excel(cq: CallbackQuery, data: dict) -> None:
    export_type = cq.data.split(":")[1]
    db = data["db_session"]
    bot = data["bot"]

    query = (
        select(Receipt, User.display_name, Seller.full_name, Shop.name)
        .join(User, Receipt.user_id == User.id)
        .join(Seller, Receipt.seller_id == Seller.id)
        .join(Shop, Receipt.shop_id == Shop.id)
        .order_by(Receipt.submitted_at.desc())
    )

    if export_type == "day":
        query = query.where(text("receipts.category = 'day'::seller_category"))
    elif export_type == "night":
        query = query.where(text("receipts.category = 'night'::seller_category"))
    elif export_type == "approved":
        query = query.where(text("receipts.status = 'approved'::receipt_status"))

    rows = (await db.execute(query)).all()

    if not rows:
        await cq.message.answer("Нет данных для экспорта.")
        await cq.answer()
        return

    await cq.message.answer(f"⏳ Формирую Excel ({len(rows)} строк)...")

    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Receipts"

        headers = ["ID", "Дата", "Продавец", "Магазин", "Категория", "Сумма", "Статус", "Пользователь"]
        ws.append(headers)

        from app.time import fmt_msk
        for receipt, user_name, seller_name, shop_name in rows:
            ws.append([
                receipt.id,
                fmt_msk(receipt.submitted_at),
                seller_name,
                shop_name,
                "день" if receipt.category == "day" else "ночь",
                float(receipt.amount),
                receipt.status.value,
                user_name or "",
            ])

        ws.column_dimensions["A"].width = 6
        ws.column_dimensions["B"].width = 20
        ws.column_dimensions["C"].width = 25
        ws.column_dimensions["D"].width = 20
        ws.column_dimensions["E"].width = 12
        ws.column_dimensions["F"].width = 12
        ws.column_dimensions["G"].width = 12
        ws.column_dimensions["H"].width = 20

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        await bot.send_document(
            chat_id=cq.message.chat.id,
            document=buffer.getvalue(),
            filename=f"receipts_{export_type}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            caption=f"📊 Экспорт ({export_type}): {len(rows)} записей",
        )
    except ImportError:
        await cq.message.answer("⚠️ openpyxl не установлен. Установите: pip install openpyxl")
    except Exception as e:
        log.error("Excel export failed: %s", e)
        await cq.message.answer(f"⚠️ Ошибка экспорта: {e}")

    await cq.answer()


# ─── Итоги ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "am:final")
async def menu_final(cq: CallbackQuery, data: dict) -> None:
    db = data["db_session"]
    settings_obj: ContestSettings | None = await db.get(ContestSettings, 1)

    from app.time import fmt_msk, now_utc

    # Статистика по чекам
    stats = {}
    for cat, label in [("day", "day"), ("night", "night")]:
        for status, slabel in [("approved", "approved"), ("pending", "pending"), ("rejected", "rejected")]:
            count = (await db.execute(
                text(f"SELECT count(id) FROM receipts WHERE category = '{cat}'::seller_category AND status = '{status}'::receipt_status")
            )).scalar() or 0
            stats[f"{label}_{slabel}"] = count

    # Продавцы с подтверждёнными
    top_sellers = {}
    for cat, label in [("day", "day"), ("night", "night")]:
        rows = await db.execute(
            text(f"""
                SELECT s.full_name, count(r.id) as cnt
                FROM receipts r
                JOIN sellers s ON r.seller_id = s.id
                WHERE r.status = 'approved'::receipt_status
                AND r.category = '{cat}'::seller_category
                GROUP BY s.id, s.full_name
                ORDER BY count(r.id) DESC
                LIMIT 3
            """)
        )
        top_sellers[label] = rows.all()

    goal_day = settings_obj.day_goal if settings_obj else 530
    goal_night = settings_obj.night_goal if settings_obj else 220

    text = (
        f"<b>🏁 Итоги конкурса</b>\n\n"
        f"<b>☀️ Дневные:</b>\n"
        f"  ✅ Подтверждено: {stats.get('day_approved', 0)} / {goal_day}\n"
        f"  ⏳ На модерации: {stats.get('day_pending', 0)}\n"
        f"  ❌ Отклонено: {stats.get('day_rejected', 0)}\n\n"
        f"<b>🌙 Ночные:</b>\n"
        f"  ✅ Подтверждено: {stats.get('night_approved', 0)} / {goal_night}\n"
        f"  ⏳ На модерации: {stats.get('night_pending', 0)}\n"
        f"  ❌ Отклонено: {stats.get('night_rejected', 0)}\n\n"
        f"<b>👥 Топ-3 дневных:</b>\n"
        + "\n".join(
            f"  {i+1}. {row.full_name} — {row.cnt} чеков"
            for i, row in enumerate(top_sellers.get("day", []))
        ) or "  —\n"
        + f"\n<b>🌙 Топ-3 ночных:</b>\n"
        + "\n".join(
            f"  {i+1}. {row.full_name} — {row.cnt} чеков"
            for i, row in enumerate(top_sellers.get("night", []))
        ) or "  —\n"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀ Админ-панель", callback_data="am:menu"))

    await cq.message.edit_text(text, reply_markup=builder.as_markup())
    await cq.answer()
