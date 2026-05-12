"""Админ: подтверждение / отклонение / на доработку заявки."""
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select

from app.bot.keyboards.inline import admin_reject_reasons
from app.bot.texts import Texts
from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User
from app.config import get_settings

log = logging.getLogger(__name__)
router = Router()

settings = get_settings()
texts = Texts()


@router.callback_query(F.data.startswith("ar:approve:"))
async def approve(cq: CallbackQuery, data: dict) -> None:
    receipt_id = int(cq.data.split(":")[2])
    db = data["db_session"]
    bot = data["bot"]

    receipt: Receipt | None = await db.get(Receipt, receipt_id)
    if not receipt:
        await cq.answer("Не найден.", show_alert=True)
        return
    if receipt.status != "pending":
        await cq.answer("Уже обработана.", show_alert=True)
        return

    receipt.status = "approved"
    from app.time import now_utc
    receipt.decided_at = now_utc()
    receipt.decided_by_user_id = data["user"].id
    await db.commit()

    # Уведомляем продавца
    user: User | None = await db.get(User, receipt.user_id)
    if user:
        try:
            await bot.send_message(
                chat_id=user.tg_id,
                text=texts.approved_notification.format(receipt_id=receipt.id),
            )
        except Exception as e:
            log.error("Notify user %s failed: %s", user.tg_id, e)

    await cq.message.edit_caption(
        caption=cq.message.caption + "\n\n✅ <b>Подтверждено</b>",
        reply_markup=None,
    )
    await cq.answer()


@router.callback_query(F.data.startswith("ar:retry:"))
async def retry_start(cq: CallbackQuery) -> None:
    receipt_id = int(cq.data.split(":")[2])
    await cq.message.edit_reply_markup(
        reply_markup=admin_reject_reasons(receipt_id, action="retry"),
    )
    await cq.answer()


@router.callback_query(F.data.startswith("ar:reject:"))
async def reject_start(cq: CallbackQuery) -> None:
    receipt_id = int(cq.data.split(":")[2])
    await cq.message.edit_reply_markup(
        reply_markup=admin_reject_reasons(receipt_id, action="reject"),
    )
    await cq.answer()


@router.callback_query(F.data.startswith("rr:"))
async def reject_confirm(cq: CallbackQuery, data: dict) -> None:
    # rr:{action}:{reason}:{receipt_id}
    parts = cq.data.split(":")
    action = parts[1]  # reject | retry
    reason_code = parts[2]
    receipt_id = int(parts[3])

    reason_text = {
        "amount": "Сумма чека не подходит",
        "old": "Чек был пробит слишком давно",
        "photo": "Сделайте новое фото чека",
    }.get(reason_code, reason_code)

    db = data["db_session"]
    bot = data["bot"]

    receipt: Receipt | None = await db.get(Receipt, receipt_id)
    if not receipt:
        await cq.answer("Не найден.", show_alert=True)
        return
    if receipt.status != "pending":
        await cq.answer("Уже обработана.", show_alert=True)
        return

    if action == "reject":
        receipt.status = "rejected"
        receipt.reject_reason_code = reason_code
        if reason_code == "amount":
            receipt.reject_reason_text = "Сумма не подходит"
        elif reason_code == "old":
            receipt.reject_reason_text = "Чек устарел"
    else:
        # retry = на доработку, возвращаем в pending (можно редактировать)
        pass  # Оставляем pending, просто уведомляем

    from app.time import now_utc
    receipt.decided_at = now_utc()
    receipt.decided_by_user_id = data["user"].id
    await db.commit()

    # Уведомляем продавца
    user: User | None = await db.get(User, receipt.user_id)
    if user:
        try:
            if action == "reject":
                await bot.send_message(
                    chat_id=user.tg_id,
                    text=texts.rejected_notification.format(
                        receipt_id=receipt.id,
                        reason=reason_text,
                    ),
                )
            else:
                await bot.send_message(
                    chat_id=user.tg_id,
                    text=texts.retry_notification.format(
                        receipt_id=receipt.id,
                        reason=reason_text,
                    ),
                )
        except Exception as e:
            log.error("Notify user %s failed: %s", user.tg_id, e)

    if action == "reject":
        await cq.message.edit_caption(
            caption=cq.message.caption + f"\n\n❌ <b>Отклонено</b>\n{reason_text}",
            reply_markup=None,
        )
    else:
        await cq.message.edit_caption(
            caption=cq.message.caption + f"\n\n↩️ <b>На доработку</b>\n{reason_text}",
            reply_markup=None,
        )
    await cq.answer()


@router.callback_query(F.data.startswith("ar:back:"))
async def back_to_card(cq: CallbackQuery) -> None:
    receipt_id = int(cq.data.split(":")[2])
    from app.bot.keyboards.inline import admin_receipt_card
    await cq.message.edit_reply_markup(reply_markup=admin_receipt_card(receipt_id))
    await cq.answer()
