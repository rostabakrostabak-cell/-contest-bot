"""Сервис user: upsert, обновление last_seller."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.seller import Seller


async def upsert_user(
    db: AsyncSession,
    tg_id: int,
    username: str | None,
    full_name: str | None,
) -> User:
    """Создаёт или обновляет User по tg_id."""
    from sqlalchemy import select

    user = await db.get(User, tg_id)
    if user is None:
        user = User(
            tg_id=tg_id,
            tg_username=username,
            display_name=full_name,
        )
        db.add(user)
    else:
        user.tg_username = username
        user.display_name = full_name

    await db.commit()
    await db.refresh(user)
    return user


async def set_last_seller(db: AsyncSession, user: User, seller: Seller) -> None:
    """Запоминает последнего выбранного продавца для подстановки первым."""
    user.last_seller_id = seller.id
    await db.commit()
