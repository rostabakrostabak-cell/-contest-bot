"""Хелперы работы со временем. В БД храним UTC, отображаем по Москве."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

MSK = ZoneInfo("Europe/Moscow")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_msk(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MSK)


def to_utc(dt: datetime) -> datetime:
    # Naive datetime от админа трактуем как московское — это бизнес-конвенция.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=MSK)
    return dt.astimezone(timezone.utc)


def fmt_msk(dt: datetime, with_seconds: bool = False) -> str:
    msk = to_msk(dt)
    fmt = "%d.%m.%Y %H:%M:%S" if with_seconds else "%d.%m.%Y %H:%M"
    return msk.strftime(fmt)
