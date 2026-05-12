"""Сервис contest_state: открыт ли приём чеков, финал, цели."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contest_settings import ContestSettings
from app.time import now_utc, to_msk


async def ensure_settings(db: AsyncSession) -> ContestSettings:
    """Создаёт строку настроек из .env если её ещё нет."""
    settings = await db.get(ContestSettings, 1)
    if settings is None:
        from app.config import get_settings
        s = get_settings()
        settings = ContestSettings(
            id=1,
            end_at=s.contest_end_at,
            raffle_at=s.contest_raffle_at,
            day_goal=s.day_goal,
            night_goal=s.night_goal,
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


async def is_submissions_open(db: AsyncSession) -> bool:
    """True если ещё не наступил end_at по Москве."""
    settings = await ensure_settings(db)
    return now_utc() < settings.end_at


async def is_finalized(db: AsyncSession) -> bool:
    """True если розыгрыш уже состоялся."""
    settings = await ensure_settings(db)
    return settings.finalized_at is not None


async def contest_settings_snapshot(db: AsyncSession) -> dict:
    """Текущие настройки одним dict."""
    s = await ensure_settings(db)
    return {
        "end_at_msk": to_msk(s.end_at),
        "raffle_at_msk": to_msk(s.raffle_at),
        "day_goal": s.day_goal,
        "night_goal": s.night_goal,
        "is_finalized": s.finalized_at is not None,
    }
