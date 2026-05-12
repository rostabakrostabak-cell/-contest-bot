"""Сервис ranking: прогресс продавца, топы."""
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt
from app.models.seller import SellerCategory


@dataclass
class SellerStats:
    seller_id: int
    full_name: str
    shop_name: str
    category: SellerCategory
    approved_count: int
    first_approved_at: str | None = None


@dataclass
class ShopStats:
    shop_id: int
    shop_name: str
    category: SellerCategory
    approved_count: int


@dataclass
class UserProgress:
    approved_count: int
    rank: int | None
    remaining: int
    goal_reached: bool


async def seller_progress(
    db: AsyncSession, user_id: int, category: SellerCategory
) -> UserProgress:
    """Мой прогресс — считается только по approved."""
    from app.models.contest_settings import ContestSettings

    settings = await db.get(ContestSettings, 1)
    goal = settings.day_goal if category == SellerCategory.DAY else settings.night_goal

    cat_val = category.value

    count_row = await db.execute(
        text("""
            SELECT count(id)
            FROM receipts
            WHERE user_id = :uid
            AND status = 'approved'::receipt_status
            AND category = CAST(:cat AS seller_category)
        """),
        {"uid": user_id, "cat": cat_val}
    )
    approved_count = count_row.scalar() or 0

    rank_row = await db.execute(
        text("""
            SELECT user_id, count(id) as cnt
            FROM receipts
            WHERE status = 'approved'::receipt_status
            AND category = CAST(:cat AS seller_category)
            GROUP BY user_id
            ORDER BY count(id) DESC
        """),
        {"cat": cat_val}
    )
    rows = rank_row.all()
    rank: int | None = None
    for i, row in enumerate(rows, 1):
        if row.user_id == user_id:
            rank = i
            break

    remaining = max(0, goal - approved_count)
    goal_reached = approved_count >= goal

    return UserProgress(
        approved_count=approved_count,
        rank=rank,
        remaining=remaining,
        goal_reached=goal_reached,
    )


async def top_sellers_live(
    db: AsyncSession,
    category: SellerCategory | str,
    limit: int = 10,
) -> list[SellerStats]:
    """Топ продавцов по approved."""
    from app.models.seller import Seller
    from app.models.shop import Shop

    cat_val = category.value if hasattr(category, 'value') else category

    rows = await db.execute(
        text("""
            SELECT
                r.seller_id,
                count(r.id) as cnt,
                min(r.submitted_at) as first_at,
                s.full_name,
                s.category,
                sh.name as shop_name
            FROM receipts r
            JOIN sellers s ON r.seller_id = s.id
            JOIN shops sh ON r.shop_id = sh.id
            WHERE r.status = 'approved'::receipt_status
            AND r.category = CAST(:cat AS seller_category)
            GROUP BY r.seller_id, s.full_name, s.category, sh.name
            ORDER BY count(r.id) DESC, min(r.submitted_at) ASC
            LIMIT :lim
        """),
        {"cat": cat_val, "lim": limit}
    )
    return [
        SellerStats(
            seller_id=row.seller_id,
            full_name=row.full_name,
            shop_name=row.shop_name,
            category=row.category,
            approved_count=row.cnt,
            first_approved_at=str(row.first_at) if row.first_at else None,
        )
        for row in rows.all()
    ]


async def top_shops_live(
    db: AsyncSession,
    category: SellerCategory | str,
    limit: int = 3,
) -> list[ShopStats]:
    """Топ магазинов по approved."""
    from app.models.shop import Shop

    cat_val = category.value if hasattr(category, 'value') else category

    rows = await db.execute(
        text("""
            SELECT
                r.shop_id,
                sh.name as shop_name,
                count(r.id) as cnt
            FROM receipts r
            JOIN shops sh ON r.shop_id = sh.id
            WHERE r.status = 'approved'::receipt_status
            AND r.category = CAST(:cat AS seller_category)
            GROUP BY r.shop_id, sh.name
            ORDER BY count(r.id) DESC
            LIMIT :lim
        """),
        {"cat": cat_val, "lim": limit}
    )
    return [
        ShopStats(
            shop_id=row.shop_id,
            shop_name=row.shop_name,
            category=SellerCategory(cat_val),
            approved_count=row.cnt,
        )
        for row in rows.all()
    ]


async def flask_counts(db: AsyncSession) -> tuple[int, int]:
    """Количество approved чеков по категориям."""
    day_row = await db.execute(
        text("""
            SELECT count(id)
            FROM receipts
            WHERE status = 'approved'::receipt_status
            AND category = 'day'::seller_category
        """)
    )
    night_row = await db.execute(
        text("""
            SELECT count(id)
            FROM receipts
            WHERE status = 'approved'::receipt_status
            AND category = 'night'::seller_category
        """)
    )
    return day_row.scalar() or 0, night_row.scalar() or 0
