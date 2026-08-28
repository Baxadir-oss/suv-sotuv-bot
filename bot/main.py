"""
Bot va Mini App API'ni bitta aiohttp jarayonida ishga tushiradi — 0.5 GB
xotira sharoitida ikkita alohida server yuritishdan qochish uchun (8-bo'lim).

Ishga tushirish:
    python -m bot.main

Railway'da WEBHOOK_BASE_URL o'rnatilgan bo'lsa — webhook rejimi (tavsiya etiladi).
Lokal test uchun WEBHOOK_BASE_URL bo'sh qoldirilsa — polling rejimi ishlaydi.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot.config import config
from bot.database.db import init_db
from bot.handlers import common as common_handlers
from bot.handlers.agent import broadcast as agent_broadcast
from bot.handlers.agent import products as agent_products
from bot.handlers.agent import registration as agent_registration
from bot.handlers.agent import reports as agent_reports
from bot.handlers.agent import search as agent_search
from bot.middlewares.auth import AccessControlMiddleware, AgentOnlyMiddleware
from bot.scheduler import setup_scheduler
from bot.webapp_api.routes import routes as api_routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

WEBAPP_DIST = Path(__file__).resolve().parent.parent / "webapp" / "dist"


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(AccessControlMiddleware())

    dp.include_router(common_handlers.router)

    agent_router = Router(name="agent_root")
    agent_router.message.middleware(AgentOnlyMiddleware())
    agent_router.callback_query.middleware(AgentOnlyMiddleware())
    for sub_router in (
        agent_registration.router,
        agent_products.router,
        agent_broadcast.router,
        agent_search.router,
        agent_reports.router,
    ):
        agent_router.include_router(sub_router)
    dp.include_router(agent_router)

    return dp


async def _on_startup(bot: Bot) -> None:
    await init_db()
    if config.webhook_base_url:
        webhook_url = config.webhook_base_url.rstrip("/") + config.webhook_path
        await bot.set_webhook(webhook_url, secret_token=config.webhook_secret, drop_pending_updates=True)
        logger.info("Webhook o'rnatildi: %s", webhook_url)
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook o'chirildi — polling rejimida ishga tushmoqda")


async def _on_shutdown(bot: Bot) -> None:
    await bot.session.close()


def _setup_static_and_spa(app: web.Application) -> None:
    """Mini App'ning build qilingan statik fayllarini xizmat qiladi (webapp/dist)."""
    if not WEBAPP_DIST.exists():
        logger.warning(
            "webapp/dist topilmadi — Mini App build qilinmagan. "
            "`cd webapp && npm install && npm run build` ishga tushiring."
        )
        return

    async def spa_index(request: web.Request) -> web.FileResponse:
        return web.FileResponse(WEBAPP_DIST / "index.html")

    app.router.add_static("/assets/", WEBAPP_DIST / "assets", name="webapp-assets")
    app.router.add_get("/", spa_index)
    app.router.add_get("/miniapp", spa_index)


async def _health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def create_app() -> tuple[web.Application, Bot]:
    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher()

    app = web.Application()
    app["bot"] = bot
    app["dp"] = dp

    app.add_routes(api_routes)
    app.router.add_get("/health", _health)
    _setup_static_and_spa(app)

    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=config.webhook_secret).register(
        app, path=config.webhook_path
    )
    setup_application(app, dp, bot=bot)

    scheduler = setup_scheduler(bot)

    async def _start_scheduler(_app: web.Application) -> None:
        scheduler.start()

    async def _stop_scheduler(_app: web.Application) -> None:
        scheduler.shutdown(wait=False)

    dp.startup.register(_on_startup)
    dp.shutdown.register(_on_shutdown)
    app.on_startup.append(_start_scheduler)
    app.on_shutdown.append(_stop_scheduler)

    return app, bot


async def _run_polling() -> None:
    """Lokal test uchun — WEBHOOK_BASE_URL bo'sh bo'lganda ishlatiladi."""
    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher()
    dp.startup.register(_on_startup)
    dp.shutdown.register(_on_shutdown)
    scheduler = setup_scheduler(bot)
    scheduler.start()
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)


def main() -> None:
    if config.webhook_base_url:
        app, _bot = create_app()
        web.run_app(app, host="0.0.0.0", port=config.port)
    else:
        asyncio.run(_run_polling())


if __name__ == "__main__":
    main()
