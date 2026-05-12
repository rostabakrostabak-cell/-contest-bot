"""DB session middleware — открывает сессию и коммитит при успехе."""
from typing import Any

from aiogram import Handler
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject

from app.db import session_scope


class DbSessionMiddleware(BaseMiddleware):
    """Инжектит `db_session` в context_data каждого handler."""

    async def __call__(
        self,
        handler: Handler[TelegramObject, dict[str, Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with session_scope() as db_session:
            data["db_session"] = db_session
            return await handler(event, data)
