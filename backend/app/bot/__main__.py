"""Entry point: setup logging, register routers, start polling."""
import asyncio
import logging
import signal
import sys

from app.bot.loader import bot, dp, on_startup, on_shutdown

log = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Middlewares
    from app.bot.middlewares.user import register as register_middleware
    register_middleware(dp)

    # Routers
    from app.bot.handlers import register_routers
    register_routers(dp)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    log.info("Starting polling...")
    try:
        await dp.start_polling(bot, close_bot_session=True)
    except asyncio.CancelledError:
        log.info("Polling cancelled")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    for _signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(_signal, lambda: asyncio.to_thread(lambda: None))

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        log.info("Interrupted")
    finally:
        loop.run_until_complete(dp.storage.close())
        loop.close()
