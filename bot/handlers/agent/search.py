"""
15-bo'lim: do'konchilarni qidirish.

Asosiy, to'liq tajriba Mini App'da (real-time filtr, kartochkalar) — bu yerda
botning o'zida ham tezkor matn orqali qidiruv imkoniyati beriladi, mini app
ochilmagan holatlarda ham agent darhol javob olishi uchun.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import or_, select

from bot.database.db import async_session_factory
from bot.database.models import Shop
from bot.locales.i18n import t

router = Router(name="agent_search")

LANG = "uz"


class SearchForm(StatesGroup):
    waiting_query = State()


@router.callback_query(F.data == "agent:search")
async def search_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchForm.waiting_query)
    await callback.message.answer(t(LANG, "search_prompt"))
    await callback.answer()


@router.message(SearchForm.waiting_query, F.text)
async def search_run(message: Message, state: FSMContext):
    query = f"%{message.text.strip()}%"
    async with async_session_factory() as session:
        result = await session.execute(
            select(Shop).where(
                or_(
                    Shop.dokon_nomi.ilike(query),
                    Shop.egasi_ismi.ilike(query),
                    Shop.telefon.ilike(query),
                    Shop.boshqaruvchi_telefon.ilike(query),
                )
            ).limit(15)
        )
        shops = list(result.scalars())

    await state.clear()

    if not shops:
        await message.answer(t(LANG, "search_no_results"))
        return

    lines = []
    for s in shops:
        status = "🔴 bloklangan" if s.is_blocked else ("🟡 lokatsiya kutilmoqda" if s.telegram_id is None else "🟢 faol")
        lines.append(
            f"🏪 <b>{s.dokon_nomi}</b> ({status})\n"
            f"👤 {s.egasi_ismi} — 📞 {s.telefon}\n"
            f"📦 Jami buyurtma: {s.total_orders}"
        )
    await message.answer("\n\n".join(lines), parse_mode="HTML")
