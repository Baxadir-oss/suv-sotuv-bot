"""
8-bo'lim: "APScheduler'da faqat zarur ikkita vazifa — ortiqcha fon jarayonlari yo'q."

Bu yerda uchta job bor, lekin ular barchasi yengil va tez ishlaydi:
1. Haftalik backup (8-bo'lim)
2. Oylik hisobot — agentga avtomatik yuboriladi (8-bo'lim)
3. Navbatga qo'yilgan reklamalarni tekshirish — soatlik, faqat kutilayotgan
   yozuv bo'lsagina ishlaydi (7-bo'lim, "belgilangan vaqt kelganda avtomatik yuboriladi")
"""
from __future__ import annotations

import datetime as dt
import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from bot.config import config
from bot.database.db import async_session_factory
from bot.database.models import BroadcastLog
from bot.services import backup_service, reports_service

logger = logging.getLogger(__name__)


async def _weekly_backup_job() -> None:
    try:
        path = backup_service.run_weekly_backup()
        logger.info("Haftalik backup yaratildi: %s", path)
    except Exception:
        logger.exception("Haftalik backup muvaffaqiyatsiz tugadi")


async def _monthly_report_job(bot: Bot) -> None:
    today = dt.date.today()
    first_of_month = today.replace(day=1)
    last_month_end = first_of_month - dt.timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    data = await reports_service.summary(last_month_start, last_month_end)
    totals = data["totals"]
    text = (
        f"📅 <b>Oylik hisobot: {last_month_start.strftime('%B %Y')}</b>\n\n"
        f"🧾 Jami buyurtmalar: {totals['orders_count']}\n"
        f"💰 Jami summa: {totals['total_amount']:,.0f} so'm"
    )
    for agent_id in config.agent_ids:
        try:
            await bot.send_message(agent_id, text, parse_mode="HTML")
        except Exception:
            logger.exception("Oylik hisobotni agentga yuborib bo'lmadi: %s", agent_id)


async def _process_queued_broadcasts(bot: Bot) -> None:
    """Vaqt oynasidan tashqarida navbatga qo'yilgan reklamalarni tekshiradi (7-bo'lim)."""
    from bot.handlers.agent.broadcast import dispatch_broadcast  # aylanma import'dan qochish uchun shu yerda

    now = dt.datetime.utcnow()
    async with async_session_factory() as session:
        result = await session.execute(
            select(BroadcastLog).where(BroadcastLog.sent_at.is_(None), BroadcastLog.scheduled_at <= now)
        )
        pending = list(result.scalars())

    for log in pending:
        await dispatch_broadcast(bot, log.id)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

    scheduler.add_job(_weekly_backup_job, CronTrigger(day_of_week="sun", hour=3, minute=0))
    scheduler.add_job(_monthly_report_job, CronTrigger(day=1, hour=9, minute=0), args=[bot])
    scheduler.add_job(_process_queued_broadcasts, CronTrigger(minute="*/30"), args=[bot])

    return scheduler
