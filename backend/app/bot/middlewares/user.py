"""Db session + user middleware."""
from typing import Any, Callable

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser

from app.db import session_scope
from app.models.user import User
from app.time import now_utc


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with session_scope() as db_session:
            data["db_session"] = db_session
            return await handler(event, data)


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        async with session_scope() as db_session:
            from sqlalchemy import select

            row = await db_session.execute(
                select(User).where(User.tg_id == tg_user.id)
            )
            user = row.scalar_one_or_none()

            if user is None:
                user = User(
                    tg_id=tg_user.id,
                    tg_username=tg_user.username,
                    display_name=tg_user.full_name,
                    started_bot_at=now_utc(),
                )
                db_session.add(user)
            else:
                user.last_seen_at = now_utc()
                user.tg_username = tg_user.username
                user.display_name = tg_user.full_name

            await db_session.commit()
            await db_session.refresh(user)
            data["user"] = user

        return await handler(event, data)


def register(dp: Any) -> None:
    """Регистрирует middleware на Dispatcher."""
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())
