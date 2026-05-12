from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.seller import SellerCategory
from app.time import now_utc


class Winner(Base):
    """Результат розыгрыша. По одной строке на категорию (day / night).

    Если goal_reached=False — победитель не выбирается, seller_id=NULL,
    но строка всё равно создаётся как факт «розыгрыш состоялся».
    """

    __tablename__ = "winners"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[SellerCategory] = mapped_column(
        Enum(SellerCategory, name="seller_category"),
        unique=True,
        nullable=False,
    )
    seller_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sellers.id", ondelete="SET NULL")
    )
    # Билетов = чеков продавца на момент розыгрыша (включая pending — § 18 ТЗ).
    receipt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    goal_reached: Mapped[bool] = mapped_column(Boolean, nullable=False)
    picked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, nullable=False
    )

    seller = relationship("Seller")
