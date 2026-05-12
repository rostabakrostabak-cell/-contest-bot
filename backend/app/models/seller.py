import enum

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SellerCategory(str, enum.Enum):
    DAY = "day"
    NIGHT = "night"


class SellerSource(str, enum.Enum):
    PRELOAD = "preload"   # из стартового Excel
    MANUAL = "manual"     # добавлен продавцом через "меня нет в списке"
    ADMIN = "admin"       # добавлен админом вручную


class Seller(Base, TimestampMixin):
    __tablename__ = "sellers"
    __table_args__ = (
        UniqueConstraint("shop_id", "full_name", name="uq_sellers_shop_id_full_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[SellerCategory] = mapped_column(
        Enum(SellerCategory, name="seller_category"),
        nullable=False,
    )
    source: Mapped[SellerSource] = mapped_column(
        Enum(SellerSource, name="seller_source"),
        default=SellerSource.PRELOAD,
        nullable=False,
    )

    shop = relationship("Shop", back_populates="sellers")
