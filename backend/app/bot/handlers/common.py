"""Общий роутер: /start, главное меню."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select, text

from app.bot.keyboards.main import seller_main_menu
from app.bot.keyboards.inline import admin_inline_menu
from app.bot.texts import Texts
from app.config import get_settings
from app.models.receipt import Receipt

router = Router()

settings = get_settings()
texts = Texts()


@router.message(Command("start"))
async def cmd_start(message: Message, user, db_session) -> None:
    if user.tg_id == settings.admin_tg_id:
        user.is_admin = True
        await db_session.commit()
        await message.answer(texts.admin_menu, reply_markup=admin_inline_menu())
    else:
        count = await db_session.execute(
            text("SELECT count(id) FROM receipts WHERE user_id = :uid AND status = 'approved'::receipt_status"),
            {"uid": user.id}
        )
        approved_count = count.scalar() or 0
        await message.answer(texts.main_menu, reply_markup=seller_main_menu(approved_count))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.cancel, reply_markup=seller_main_menu())


@router.message(F.text.startswith("📋 Мои чеки"))
async def menu_my_receipts(message: Message, user, db_session) -> None:
    from app.bot.handlers.seller.seller_other import show_my_receipts
    await show_my_receipts(message, user, db_session)


@router.message(F.text == "🏪 Рейтинг магазинов")
async def menu_shops_ranking(message: Message, db_session) -> None:
    from app.bot.handlers.seller.seller_other import show_shops_ranking
    await show_shops_ranking(message, db_session)


@router.message(F.text == "🏆 Рейтинг продавцов")
async def menu_sellers_ranking(message: Message, db_session) -> None:
    from app.bot.handlers.seller.seller_other import show_sellers_ranking
    await show_sellers_ranking(message, db_session)


@router.message(F.text == "🧪 Колба")
async def menu_kolba(message: Message) -> None:
    await message.answer(
        f"🧪 Нажмите кнопку ниже, чтобы открыть Колбу:\n\n"
        f"<a href=\"{settings.miniapp_url}\">Открыть Mini App</a>"
    )


@router.message(F.text == "💬 Связаться с админом")
async def menu_contact(message: Message, state: FSMContext) -> None:
    from app.bot.handlers.seller.seller_other import start_contact
    await start_contact(message, state)


@router.message(F.text == "⚙️ Админ-панель")
async def admin_panel(message: Message, user, db_session) -> None:
    if user.tg_id != settings.admin_tg_id:
        await message.answer(texts.unknown)
        return
    await message.answer(texts.admin_menu, reply_markup=admin_inline_menu())


@router.callback_query(F.data == "back_main")
async def back_main(cq: CallbackQuery, state: FSMContext, user, db_session) -> None:
    await state.clear()
    await cq.message.delete()
    from app.bot.handlers.seller.seller_other import send_main_menu
    await send_main_menu(cq.message, user, db_session)


@router.callback_query(F.data == "noop")
async def noop(cq: CallbackQuery) -> None:
    await cq.answer()
