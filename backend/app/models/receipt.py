import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.seller import SellerCategory
from app.time import now_utc


class ReceiptStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RejectReason(str, enum.Enum):
    BELOW_THRESHOLD = "below_threshold"   # сумма ниже порога конкурса
    UNREADABLE = "unreadable"             # фото нечитаемое
    NOT_A_RECEIPT = "not_a_receipt"       # фото не чека
    DUPLICATE = "duplicate"               # дубликат
    INVALID_DATA = "invalid_data"         # неверные данные
    OTHER = "other"                       # другое — нужен текст


class Receipt(Base):
    __tablename__ = "receipts"
    __table_args__ = (
        Index(
            "ix_receipts_status_category_submitted_at",
            "status", "category", "submitted_at",
        ),
        Index("ix_receipts_seller_status", "seller_id", "status"),
        Index("ix_receipts_submitted_at", "submitted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("sellers.id", ondelete="RESTRICT"), nullable=False
    )

    # Денормализуем shop_id и category — снапшот на момент отправки.
    # Если админ позже отредактирует продавца, прошлые чеки не «уезжают»
    # в другую категорию или магазин.
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="RESTRICT"), nullable=False
    )
    category: Mapped[SellerCategory] = mapped_column(
        Enum(SellerCategory, name="seller_category"),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    photo_file_id: Mapped[str] = mapped_column(String(256), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        default=ReceiptStatus.PENDING.value,
        nullable=False,
    )
    reject_reason_code: Mapped[Optional[str]] = mapped_column(
        String(50)
    )
    reject_reason_text: Mapped[Optional[str]] = mapped_column(Text)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, nullable=False, index=True
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    decided_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    # tg_message_id карточки в личке у админа — чтобы потом отредактировать
    # её на «✅ Подтверждена» / «❌ Отклонена».
    admin_message_id: Mapped[Optional[int]] = mapped_column(BigInteger)

    user = relationship("User", foreign_keys=[user_id])
    seller = relationship("Seller")
    shop = relationship("Shop")
