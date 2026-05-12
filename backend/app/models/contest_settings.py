from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ContestSettings(Base):
    """Синглтон-строка (id=1) с изменяемой конфигурацией конкурса."""

    __tablename__ = "contest_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="singleton_row"),
        CheckConstraint("day_goal > 0", name="day_goal_positive"),
        CheckConstraint("night_goal > 0", name="night_goal_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raffle_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    day_goal: Mapped[int] = mapped_column(Integer, nullable=False)
    night_goal: Mapped[int] = mapped_column(Integer, nullable=False)

    # Помечаем после успешного запуска розыгрыша — гарантия идемпотентности.
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Помечаем после полной рассылки итогов всем пользователям.
    broadcast_done_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
