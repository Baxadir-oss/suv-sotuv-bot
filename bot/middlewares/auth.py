"""
Xavfsizlik middleware (2-bo'lim).

Qoida:
- Ro'yxatdan o'tmagan odam botga /start bossa — hech qanday menyu yoki
  funksiya ko'rinmaydi, faqat qisqa xabar va agentning raqami.
- Bloklangan do'kon ham xuddi shu xabarni ko'radi — sabab bot ichida
  tushuntirilmaydi (bu agentning shaxsiy vazifasi, 2-bo'lim).
- Agent buyruqlari faqat config.agent_ids ro'yxatidagi telegram_id uchun ishlaydi.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select

from bot.config import config
from bot.database.db import async_session_factory
from bot.database.models import Shop
from bot.locales.i18n import t


class AccessControlMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        telegram_id = user.id
        is_agent = telegram_id in config.agent_ids
        data["is_agent"] = is_agent

        if is_agent:
            data["shop"] = None
            return await handler(event, data)

        async with async_session_factory() as session:
            result = await session.execute(select(Shop).where(Shop.telegram_id == telegram_id))
            shop = result.scalar_one_or_none()

        data["shop"] = shop

        text = getattr(event, "text", None)
        parts = text.split(maxsplit=1) if isinstance(text, str) else []
        # "/start reg_<token>" har doim handlerga o'tishi kerak — ro'yxatga olish
        # havolasini bosgan do'konchi hali bazada yo'q, handlers/common.py
        # aynan shu payload orqali uni bog'laydi. Oddiy "/start" (payloadsiz) esa
        # ro'yxatdan o'tmagan odam uchun hamon bloklanadi.
        is_deep_link_start = len(parts) == 2 and parts[0] == "/start"

        if is_deep_link_start:
            return await handler(event, data)

        if shop is None or not shop.is_registered_and_open:
            if isinstance(event, Message):
                await event.answer(t("uz", "not_registered", phone=config.agent_contact_phone))
            elif isinstance(event, CallbackQuery):
                await event.answer(t("uz", "not_registered_short"), show_alert=True)
            return None

        return await handler(event, data)


class AgentOnlyMiddleware(BaseMiddleware):
    """Faqat agent handlerlar ustiga qo'yiladi (agent Router'iga)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not data.get("is_agent"):
            # Agent bo'lmagan odam bu buyruq borligini ham bilmasligi kerak (2-bo'lim)
            return None
        return await handler(event, data)
