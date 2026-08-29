"""
7-bo'lim + 16-bo'lim: reklama mantig'i — bitta joyda, chunki endi buni ham
bot chatidan (handlers/agent/broadcast.py), ham Mini App'dan (webapp_api/routes.py)
chaqirish kerak. Ikkalasi ham shu funksiyalarni ishlatadi — mantiq ikki joyda
takrorlanmaydi.
"""
from __future__ import annotations

import datetime as dt

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import BufferedInputFile
from sqlalchemy import select

from bot.config import config
from bot.database.db import async_session_factory
from bot.database.models import BroadcastLog, Shop


async def days_until_next_allowed() -> int | None:
    """Agar hali erta bo'lsa — qolgan kunlar sonini qaytaradi, aks holda None."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(BroadcastLog).where(BroadcastLog.sent_at.isnot(None)).order_by(BroadcastLog.sent_at.desc()).limit(1)
        )
        last = result.scalar_one_or_none()

    if last and last.sent_at:
        days_since = (dt.datetime.utcnow() - last.sent_at).days
        remaining = config.ad_min_interval_days - days_since
        if remaining > 0:
            return remaining
    return None


async def submit_broadcast(bot: Bot, template_type: str, text: str, photo_file_id: str | None) -> dict:
    """
    Reklamani darhol yuboradi (agar 10:00-18:00 oralig'ida bo'lsa) yoki
    navbatga qo'yadi (agar oynadan tashqarida bo'lsa). Chastota tekshiruvi
    (7 kun) bu yerda ham qayta tekshiriladi — xavfsizlik uchun.
    """
    remaining = await days_until_next_allowed()
    if remaining:
        return {"status": "too_soon", "days_remaining": remaining}

    now = dt.datetime.utcnow()
    within_hours = config.ad_allowed_hour_start <= now.hour < config.ad_allowed_hour_end

    async with async_session_factory() as session:
        log = BroadcastLog(template_type=template_type, text=text, photo_file_id=photo_file_id)

        if not within_hours:
            scheduled = now.replace(hour=config.ad_allowed_hour_start, minute=0, second=0, microsecond=0)
            if scheduled <= now:
                scheduled += dt.timedelta(days=1)
            log.scheduled_at = scheduled
            session.add(log)
            await session.commit()
            return {"status": "queued", "scheduled_at": scheduled.isoformat()}

        session.add(log)
        await session.commit()
        log_id = log.id

    delivered, blocked = await dispatch_broadcast(bot, log_id)
    return {"status": "sent", "delivered": delivered, "blocked": blocked}


async def dispatch_broadcast(bot: Bot, log_id: int) -> tuple[int, int]:
    """Barcha faol do'konlarga yuboradi. Ham darhol yuborishda, ham scheduler orqali navbatdagilarni yuborishda ishlatiladi."""
    async with async_session_factory() as session:
        log = await session.get(BroadcastLog, log_id)
        result = await session.execute(select(Shop).where(Shop.is_active == True, Shop.is_blocked == False))  # noqa: E712
        shops = list(result.scalars())

        delivered, blocked = 0, 0
        for shop in shops:
            if shop.telegram_id is None:
                continue
            try:
                if log.photo_file_id:
                    await bot.send_photo(shop.telegram_id, log.photo_file_id, caption=log.text)
                else:
                    await bot.send_message(shop.telegram_id, log.text)
                delivered += 1
                log.open_stats[str(shop.telegram_id)] = True
            except TelegramForbiddenError:
                blocked += 1
                log.open_stats[str(shop.telegram_id)] = False

        log.sent_at = dt.datetime.utcnow()
        log.delivered_count = delivered
        log.blocked_count = blocked
        await session.commit()

    return delivered, blocked


async def upload_photo_via_bot(bot: Bot, agent_telegram_id: int, photo_bytes: bytes) -> str:
    """
    Mini App'dan yuklangan rasmni Telegram file_id'ga aylantiradi: rasmni
    agentning botga o'z chatiga yuborib, natijadagi file_id'ni olamiz. Shu
    orqali mahsulot/reklama rasmlari uchun alohida fayl-serverga ehtiyoj
    qolmaydi — hammasi Telegram'ning o'zida saqlanadi (8-bo'lim: 0.5 GB
    xotira tejash printsipi).
    """
    msg = await bot.send_photo(agent_telegram_id, BufferedInputFile(photo_bytes, filename="upload.jpg"))
    return msg.photo[-1].file_id
    
