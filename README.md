# Конкурс продавцов — Telegram-бот + Mini App

Один бот, две роли (продавец / админ), один backend, одна БД, один Mini App с realtime.

## Структура

```
contest-new/
├── backend/        # Python: aiogram-бот + FastAPI + APScheduler + SQLAlchemy + Alembic
├── miniapp/        # React + Vite + TS — Mini App с колбами и рейтингами
├── ops/            # nginx, certbot, прочее для деплоя
├── docker-compose.yml
└── .env.example
```

## Этапы реализации

- [x] **1. Каркас, БД, модели, миграции**
- [ ] 2. Бот: продавец (отправка чека, прогресс, рейтинг, контакт с админом)
- [ ] 3. Бот: админ (модерация, продавцы, магазины, настройки, импорт)
- [ ] 4. FastAPI + WebSocket realtime
- [ ] 5. Mini App (React)
- [ ] 6. Scheduler + raffle + Excel export + broadcast
- [ ] 7. Деплой на Ubuntu

## Локальный запуск (этап 1)

Цель — поднять Postgres + Redis и применить миграции.

### Windows / PowerShell

```powershell
# 1. Скопировать .env.example -> .env и заполнить BOT_TOKEN, MINIAPP_URL
Copy-Item .env.example .env

# 2. Поднять инфраструктуру
docker compose up -d postgres redis

# 3. Создать venv и поставить зависимости
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 4. Применить миграции
alembic upgrade head

# 5. Проверить, что таблицы созданы
psql "postgresql://contest:changeme_please@127.0.0.1:5432/contest" -c "\dt"
```

Должно появиться 9 таблиц: `users`, `shops`, `sellers`, `receipts`, `contest_settings`,
`winners`, `chat_messages`, `outbox`, `audit_log` плюс `alembic_version`.

## Конвенции

- **Время в БД** — всегда UTC (`TIMESTAMPTZ`). Бизнес-логика и отображение — `Europe/Moscow`.
- **Деньги** — `Numeric(10,2)`, не float.
- **Категория и магазин в `receipts`** — денормализованы как **снапшот** на момент отправки.
  Если админ позже отредактирует продавца, прошлые чеки не «уезжают» в другую категорию.
- **Настройки конкурса** — синглтон-строка `contest_settings(id=1)`. Меняются админом
  через бота, не редеплоем.
- **Финальное правило** (§ 18, § 19 ТЗ): live-рейтинг считает только `approved`,
  но в розыгрыше 17:15 участвуют **все** чеки до 17:00 (включая `pending` и < 4000 ₽).
