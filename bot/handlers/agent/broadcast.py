"""
7-bo'lim + 16-bo'lim: reklama — chat orqali fallback yo'l.

Asosiy interfeys endi Mini App (webapp/src/pages/AgentBroadcast.jsx), lekin
bu handler ham ishlab turadi — Mini App ochilmagan holatlarda ham agent
reklama yubora olishi uchun. Ikkalasi ham bot/services/broadcast_service.py
dagi bir xil mantiqni ishlatadi.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards import broadcast_template_keyboard
from bot.locales.i18n import t
from bot.services import broadcast_service
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
    remaining = await broadcast_service.days_until_next_allowed()
    if remaining:
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
    await _submit(message, state)


@router.message(BroadcastForm.waiting_photo, F.text.lower() == "yo'q")
async def broadcast_no_photo(message: Message, state: FSMContext):
    await state.update_data(photo_file_id=None)
    await _submit(message, state)


async def _submit(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    result = await broadcast_service.submit_broadcast(
        message.bot, data["template_type"], data["text"], data.get("photo_file_id")
    )

    if result["status"] == "too_soon":
        await message.answer(t(LANG, "broadcast_too_soon", days=result["days_remaining"]))
    elif result["status"] == "queued":
        scheduled_time = result["scheduled_at"][11:16]
        await message.answer(t(LANG, "broadcast_outside_hours", time=scheduled_time))
    else:
        await message.answer(t(LANG, "broadcast_sent", count=result["delivered"]))
                            
