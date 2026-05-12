"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # ENUM-типы создаём отдельно, чтобы повторное использование (sellers + receipts)
    # не пыталось создать тот же тип дважды.
    sa.Enum("day", "night", name="seller_category").create(bind, checkfirst=True)
    sa.Enum("preload", "manual", "admin", name="seller_source").create(bind, checkfirst=True)
    sa.Enum("pending", "approved", "rejected", name="receipt_status").create(bind, checkfirst=True)
    sa.Enum(
        "below_threshold", "unreadable", "not_a_receipt",
        "duplicate", "invalid_data", "other",
        name="reject_reason",
    ).create(bind, checkfirst=True)
    sa.Enum("user_to_admin", "admin_to_user", name="chat_direction").create(bind, checkfirst=True)
    sa.Enum("pending", "sent", "failed", name="outbox_status").create(bind, checkfirst=True)

    seller_category = postgresql.ENUM(
        "day", "night", name="seller_category", create_type=False
    )
    seller_source = postgresql.ENUM(
        "preload", "manual", "admin", name="seller_source", create_type=False
    )
    receipt_status = postgresql.ENUM(
        "pending", "approved", "rejected", name="receipt_status", create_type=False
    )
    reject_reason = postgresql.ENUM(
        "below_threshold", "unreadable", "not_a_receipt",
        "duplicate", "invalid_data", "other",
        name="reject_reason", create_type=False,
    )
    chat_direction = postgresql.ENUM(
        "user_to_admin", "admin_to_user", name="chat_direction", create_type=False
    )
    outbox_status = postgresql.ENUM(
        "pending", "sent", "failed", name="outbox_status", create_type=False
    )

    op.create_table(
        "shops",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "sellers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "shop_id",
            sa.Integer,
            sa.ForeignKey("shops.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("full_name", sa.String(128), nullable=False),
        sa.Column("category", seller_category, nullable=False),
        sa.Column("source", seller_source, nullable=False, server_default="preload"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("shop_id", "full_name", name="uq_sellers_shop_id_full_name"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tg_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("tg_username", sa.String(64)),
        sa.Column("display_name", sa.String(128)),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "last_seller_id",
            sa.Integer,
            sa.ForeignKey("sellers.id", ondelete="SET NULL"),
        ),
        sa.Column("started_bot_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "receipts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "seller_id",
            sa.Integer,
            sa.ForeignKey("sellers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "shop_id",
            sa.Integer,
            sa.ForeignKey("shops.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("category", seller_category, nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("photo_file_id", sa.String(256), nullable=False),
        sa.Column("status", receipt_status, nullable=False, server_default="pending"),
        sa.Column("reject_reason_code", reject_reason),
        sa.Column("reject_reason_text", sa.Text),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column(
            "decided_by_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("admin_message_id", sa.BigInteger),
    )
    op.create_index(
        "ix_receipts_status_category_submitted_at",
        "receipts",
        ["status", "category", "submitted_at"],
    )
    op.create_index(
        "ix_receipts_seller_status",
        "receipts",
        ["seller_id", "status"],
    )
    op.create_index("ix_receipts_submitted_at", "receipts", ["submitted_at"])

    op.create_table(
        "contest_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raffle_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("day_goal", sa.Integer, nullable=False),
        sa.Column("night_goal", sa.Integer, nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True)),
        sa.Column("broadcast_done_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("id = 1", name="singleton_row"),
        sa.CheckConstraint("day_goal > 0", name="day_goal_positive"),
        sa.CheckConstraint("night_goal > 0", name="night_goal_positive"),
    )

    op.create_table(
        "winners",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("category", seller_category, nullable=False, unique=True),
        sa.Column(
            "seller_id",
            sa.Integer,
            sa.ForeignKey("sellers.id", ondelete="SET NULL"),
        ),
        sa.Column("receipt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("goal_reached", sa.Boolean, nullable=False),
        sa.Column(
            "picked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("direction", chat_direction, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("admin_tg_message_id", sa.BigInteger),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "outbox",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column(
            "status",
            outbox_status,
            nullable=False,
            server_default="pending",
            index=True,
        ),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "actor_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity", sa.String(64)),
        sa.Column("entity_id", sa.Integer),
        sa.Column("payload", postgresql.JSONB),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("outbox")
    op.drop_table("chat_messages")
    op.drop_table("winners")
    op.drop_table("contest_settings")
    op.drop_index("ix_receipts_submitted_at", table_name="receipts")
    op.drop_index("ix_receipts_seller_status", table_name="receipts")
    op.drop_index("ix_receipts_status_category_submitted_at", table_name="receipts")
    op.drop_table("receipts")
    op.drop_table("users")
    op.drop_table("sellers")
    op.drop_table("shops")

    bind = op.get_bind()
    for name in [
        "outbox_status", "chat_direction", "reject_reason",
        "receipt_status", "seller_source", "seller_category",
    ]:
        sa.Enum(name=name).drop(bind, checkfirst=True)
