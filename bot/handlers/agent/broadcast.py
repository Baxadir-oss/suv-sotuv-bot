"""
7-bo'lim + 16-bo'lim: reklama — chastota va vaqt oralig'i kod darajasida
majburiy, shablon asosida mazmun tanlanadi.
"""
import datetime as dt

from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.config import config
from bot.database.db import async_session_factory
from bot.database.models import BroadcastLog, Shop
from bot.keyboards import broadcast_template_keyboard
from bot.locales.i18n import t
from bot.states import BroadcastForm

router = Router(name="agent_broadcast")

LANG = "uz"
TEMPLATE_TITLES = {
    "new": "🆕 Yangi mahsulot",
    "discount": "💸 Chegirma/aksiya",
    "reminder": "🔔 Eslatma",
}


@router.callback_query(F.data == "agent:broadcast")
async def broadcast_start(callback: CallbackQuery):
    async with async_session_factory() as session:
        result = await session.execute(select(BroadcastLog).order_by(BroadcastLog.sent_at.desc()).limit(1))
        last = result.scalar_one_or_none()

    if last and last.sent_at:
        days_since = (dt.datetime.utcnow() - last.sent_at).days
        remaining = config.ad_min_interval_days - days_since
        if remaining > 0:
            await callback.message.answer(t(LANG, "broadcast_too_soon", days=remaining))
            await callback.answer()
            return

    await callback.message.answer(t(LANG, "broadcast_choose_template"), reply_markup=broadcast_template_keyboard(LANG))
    await callback.answer()


@router.callback_query(F.data.startswith("bcast:"))
async def choose_template(callback: CallbackQuery, state: FSMContext):
    template = callback.data.split(":", 1)[1]
    await state.update_data(template_type=template)
    await state.set_state(BroadcastForm.waiting_text)
    await callback.message.answer(f"{TEMPLATE_TITLES[template]}\n\nMatnni kiriting (qisqa, 2-3 gap):")
    await callback.answer()


@router.message(BroadcastForm.waiting_text, F.text)
async def broadcast_got_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text.strip())
    await state.set_state(BroadcastForm.waiting_photo)
    await message.answer("Rasmni yuboring (yoki 'yo'q' deb yozing agar rasm bo'lmasa):")


@router.message(BroadcastForm.waiting_photo, F.photo)
async def broadcast_got_photo(message: Message, state: FSMContext):
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await _send_or_queue_broadcast(message, state)


@router.message(BroadcastForm.waiting_photo, F.text.lower() == "yo'q")
async def broadcast_no_photo(message: Message, state: FSMContext):
    await state.update_data(photo_file_id=None)
    await _send_or_queue_broadcast(message, state)


async def _send_or_queue_broadcast(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    now = dt.datetime.utcnow()
    within_hours = config.ad_allowed_hour_start <= now.hour < config.ad_allowed_hour_end

    async with async_session_factory() as session:
        log = BroadcastLog(
            template_type=data["template_type"],
            text=data["text"],
            photo_file_id=data.get("photo_file_id"),
        )
        if not within_hours:
            # Bugungi yoki ertangi 10:00'ga navbatga qo'yiladi (7-bo'lim)
            scheduled = now.replace(hour=config.ad_allowed_hour_start, minute=0, second=0, microsecond=0)
            if scheduled <= now:
                scheduled += dt.timedelta(days=1)
            log.scheduled_at = scheduled
            session.add(log)
            await session.commit()
            await message.answer(
                t(LANG, "broadcast_outside_hours", time=scheduled.strftime("%d.%m %H:%M"))
            )
            return

        session.add(log)
        await session.commit()
        log_id = log.id

    delivered, _ = await dispatch_broadcast(message.bot, log_id)
    await message.answer(t(LANG, "broadcast_sent", count=delivered))


async def dispatch_broadcast(bot, log_id: int) -> tuple[int, int]:
    """
    Reklamani barcha faol do'konlarga yuboradi va statistikasini yozadi.
    Ham darhol yuborishda (yuqorida), ham scheduler orqali navbatdagi
    reklamalarni yuborishda ishlatiladi (bot/scheduler.py).
    """
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
