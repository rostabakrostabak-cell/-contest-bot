"""FastAPI app: REST endpoints + WebSocket realtime для Mini App."""
import asyncio
import hashlib
import hmac
import json
import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import SessionFactory
from app.models.contest_settings import ContestSettings
from app.models.seller import SellerCategory
from app.bot.redis_const import CHANNEL_STATE
from app.services.ranking import flask_counts, top_sellers_live, top_shops_live
from app.time import to_msk

settings = get_settings()
log = logging.getLogger(__name__)

app = FastAPI(title="Contest API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db() -> AsyncSession:
    async with SessionFactory() as session:
        yield session

# ─── WebSocket connection manager ─────────────────────────────────────────────

_active_ws: list[WebSocket] = []


async def ws_broadcast(message: dict) -> None:
    """Рассылает JSON-сообщение всем подключённым WebSocket-клиентам."""
    payload = json.dumps(message, default=str)
    for ws in _active_ws[:]:
        try:
            await ws.send_text(payload)
        except Exception:
            _active_ws.remove(ws)


# ─── Redis subscriber ────────────────────────────────────────────────────────

async def _redis_listener() -> None:
    """Фоновый таск: читает из Redis pub/sub и шлёт в WebSocket."""
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        pubsub = r.pubsub()
        await pubsub.subscribe(CHANNEL_STATE)
        log.info("Redis subscriber started on channel %s", CHANNEL_STATE)

        async for msg in pubsub.listen():
            if msg["type"] != "message":
                continue
            try:
                event = json.loads(msg["data"])
                await ws_broadcast(event)
            except json.JSONDecodeError:
                log.warning("Invalid JSON from Redis: %s", msg["data"])
    except Exception as e:
        log.error("Redis subscriber error: %s", e)
    finally:
        await pubsub.unsubscribe(CHANNEL_STATE)
        await r.aclose()


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(_redis_listener())
    log.info("API started")


# ─── REST: инициализация Mini App ────────────────────────────────────────────

@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/contest")
async def contest_info(db: AsyncSession = Depends(get_db)) -> dict:
    settings_row = await db.get(ContestSettings, 1)
    if not settings_row:
        return {"error": "contest not configured"}

    day_count, night_count = await flask_counts(db)
    return {
        "end_at_msk": to_msk(settings_row.end_at).isoformat(),
        "raffle_at_msk": to_msk(settings_row.raffle_at).isoformat(),
        "day_goal": settings_row.day_goal,
        "night_goal": settings_row.night_goal,
        "day_approved": day_count,
        "night_approved": night_count,
        "day_progress_pct": min(100, int(day_count / settings_row.day_goal * 100)),
        "night_progress_pct": min(100, int(night_count / settings_row.night_goal * 100)),
        "is_finalized": settings_row.finalized_at is not None,
    }


@app.get("/api/ranking/{category}")
async def ranking(category: str, db: AsyncSession = Depends(get_db)) -> dict:
    cat = "day" if category == "day" else "night"

    sellers = await top_sellers_live(db, cat, limit=10)
    shops = await top_shops_live(db, cat, limit=5)

    return {
        "category": category,
        "sellers": [
            {
                "id": s.seller_id,
                "name": s.full_name,
                "shop": s.shop_name,
                "count": s.approved_count,
            }
            for s in sellers
        ],
        "shops": [
            {"id": sp.shop_id, "name": sp.shop_name, "count": sp.approved_count}
            for sp in shops
        ],
    }


# ─── WebSocket endpoint ──────────────────────────────────────────────────────

@app.websocket("/ws/contest")
async def websocket_endpoint(
    ws: WebSocket,
    token: str = Query(...),
) -> None:
    """WebSocket для realtime-обновлений.

    token = HMAC-SHA256(tg_id, secret) — проверяем,
    чтобы только открывшие Mini App могли подключиться.
    """
    # Базовая проверка токена (Mini App передаёт tg_id + hash)
    # В prod: проверять init_data от Telegram Web App.
    # Здесь: простой HMAC по секрету.
    expected = hmac.new(
        settings.bot_token.encode(),
        b"miniapp",
        hashlib.sha256,
    ).hexdigest()[:16]

    if not hmac.compare_digest(token[:16], expected):
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()
    _active_ws.append(ws)
    log.info("WS connected, total: %d", len(_active_ws))

    try:
        # Отправляем текущее состояние сразу при подключении
        async with SessionFactory() as db:
            day_count, night_count = await flask_counts(db)
            settings_row = await db.get(ContestSettings, 1)

            sellers_day = await top_sellers_live(db, "day", 5)
            sellers_night = await top_sellers_live(db, "night", 5)

            state = {
                "type": "init",
                "day_approved": day_count,
                "night_approved": night_count,
                "day_goal": settings_row.day_goal if settings_row else 0,
                "night_goal": settings_row.night_goal if settings_row else 0,
                "sellers_day": [
                    {"name": s.full_name, "count": s.approved_count}
                    for s in sellers_day
                ],
                "sellers_night": [
                    {"name": s.full_name, "count": s.approved_count}
                    for s in sellers_night
                ],
            }
            await ws.send_json(state)

        async for raw in ws.iter_text():
            # Mini App может отправлять ping — отвечаем pong
            try:
                msg = json.loads(raw)
                if msg.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        log.info("WS disconnected")
    except Exception as e:
        log.error("WS error: %s", e)
    finally:
        if ws in _active_ws:
            _active_ws.remove(ws)
