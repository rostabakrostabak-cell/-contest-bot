import enum
from typing import Optional

from sqlalchemy import BigInteger, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ChatDirection(str, enum.Enum):
    USER_TO_ADMIN = "user_to_admin"
    ADMIN_TO_USER = "admin_to_user"


class ChatMessage(Base, TimestampMixin):
    """Переписка продавец ↔ админ через бота (§ 16)."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    direction: Mapped[ChatDirection] = mapped_column(
        Enum(ChatDirection, name="chat_direction"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # tg_message_id админа в его личке — для обработки reply-цепочек.
    admin_tg_message_id: Mapped[Optional[int]] = mapped_column(BigInteger)
