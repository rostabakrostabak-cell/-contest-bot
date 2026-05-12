"""Сервис realtime: публикация событий в Redis для WebSocket-подписчиков."""
import json
import logging

from app.config import get_settings
from app.bot.redis_const import CHANNEL_STATE

settings = get_settings()
log = logging.getLogger(__name__)


async def publish_event(event: dict) -> None:
    """Публикует JSON-событие в Redis pub/sub.
    Типы событий:
      - receipt:approved {receipt_id, category, amount}
      - receipt:rejected {receipt_id, category}
      - receipt:new      {receipt_id, category}
      - contest:finalized {winner_day, winner_night}
    """
    import redis.asyncio as redis
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await r.publish(CHANNEL_STATE, json.dumps(event, default=str))
    except Exception as e:
        log.warning("Failed to publish event: %s", e)
    finally:
        await r.aclose()


async def publish_receipt_approved(receipt_id: int, category: str, new_total: int) -> None:
    await publish_event({
        "type": "receipt:approved",
        "receipt_id": receipt_id,
        "category": category,
        "new_total": new_total,
    })


async def publish_receipt_rejected(receipt_id: int, category: str) -> None:
    await publish_event({
        "type": "receipt:rejected",
        "receipt_id": receipt_id,
        "category": category,
    })


async def publish_contest_finalized(winner_day: str | None, winner_night: str | None) -> None:
    await publish_event({
        "type": "contest:finalized",
        "winner_day": winner_day,
        "winner_night": winner_night,
    })
