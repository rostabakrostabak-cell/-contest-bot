from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    tg_username: Mapped[Optional[str]] = mapped_column(String(64))
    display_name: Mapped[Optional[str]] = mapped_column(String(128))

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Бот предлагает последнего выбранного продавца первым в FSM отправки чека.
    last_seller_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sellers.id", ondelete="SET NULL"),
    )

    # started_bot_at — нужен для финальной рассылки (§ 19): уведомляем всех,
    # кто хоть раз нажал /start.
    started_bot_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    last_seller = relationship("Seller", foreign_keys=[last_seller_id])
