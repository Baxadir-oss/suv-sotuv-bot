"""
3-bo'lim / 13-bo'lim: do'kon ro'yxatga olish oqimi.

Har bir qadam — bitta savol (9.1-bo'lim printsipi).
Oqim: rasm -> egasi ismi -> boshqaruvchi ismi (yoki "bir xil") ->
      (agar farq qilsa) boshqaruvchi telefon -> do'kon nomi -> telefon ->
      lokatsiya (Telegram native location tugmasi orqali).
"""
import secrets

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.db import async_session_factory
from bot.database.models import Shop
from bot.keyboards import (
    agent_main_menu,
    cancel_keyboard,
    remove_keyboard,
    request_location_keyboard,
    same_as_owner_keyboard,
)
from bot.locales.i18n import t
from bot.states import ShopRegistration

router = Router(name="agent_registration")

LANG = "uz"  # Agent paneli hozircha o'zbek tilida ishlaydi


@router.callback_query(F.data == "agent:register")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ShopRegistration.waiting_photo)
    await callback.message.answer(
        t(LANG, "agent_registration_start"),
        reply_markup=cancel_keyboard(LANG),
    )
    await callback.answer()


@router.message(StateFilter(ShopRegistration), F.text == t(LANG, "cancel_button"))
async def cancel_registration(message: Message, state: FSMContext, is_agent: bool):
    await state.clear()
    await message.answer(t(LANG, "cancelled"), reply_markup=remove_keyboard())
    await message.answer(t(LANG, "agent_menu_title"), reply_markup=agent_main_menu())


@router.message(ShopRegistration.waiting_photo, F.photo)
async def got_photo(message: Message, state: FSMContext):
    await state.update_data(dokon_rasmi=message.photo[-1].file_id)
    await state.set_state(ShopRegistration.waiting_owner_name)
    await message.answer(t(LANG, "agent_registration_owner_name"))


@router.message(ShopRegistration.waiting_photo)
async def got_photo_invalid(message: Message):
    await message.answer("📷 Iltimos, avval do'konning rasmini yuboring.")


@router.message(ShopRegistration.waiting_owner_name, F.text)
async def got_owner_name(message: Message, state: FSMContext):
    await state.update_data(egasi_ismi=message.text.strip())
    await state.set_state(ShopRegistration.waiting_manager_name)
    await message.answer(
        t(LANG, "agent_registration_manager_name"),
        reply_markup=same_as_owner_keyboard(LANG),
    )


@router.message(ShopRegistration.waiting_manager_name, F.text == t(LANG, "agent_registration_same_as_owner"))
async def manager_same_as_owner(message: Message, state: FSMContext):
    await state.update_data(boshqaruvchi_ismi=None, boshqaruvchi_telefon=None)
    await state.set_state(ShopRegistration.waiting_shop_name)
    await message.answer(t(LANG, "agent_registration_shop_name"), reply_markup=cancel_keyboard(LANG))


@router.message(ShopRegistration.waiting_manager_name, F.text)
async def got_manager_name(message: Message, state: FSMContext):
    await state.update_data(boshqaruvchi_ismi=message.text.strip())
    await state.set_state(ShopRegistration.waiting_manager_phone)
    await message.answer(t(LANG, "agent_registration_manager_phone"))


@router.message(ShopRegistration.waiting_manager_phone, F.text)
async def got_manager_phone(message: Message, state: FSMContext):
    await state.update_data(boshqaruvchi_telefon=message.text.strip())
    await state.set_state(ShopRegistration.waiting_shop_name)
    await message.answer(t(LANG, "agent_registration_shop_name"))


@router.message(ShopRegistration.waiting_shop_name, F.text)
async def got_shop_name(message: Message, state: FSMContext):
    await state.update_data(dokon_nomi=message.text.strip())
    await state.set_state(ShopRegistration.waiting_phone)
    await message.answer(t(LANG, "agent_registration_phone"))


@router.message(ShopRegistration.waiting_phone, F.text)
async def got_phone(message: Message, state: FSMContext):
    await state.update_data(telefon=message.text.strip())
    await state.set_state(ShopRegistration.waiting_location)
    await message.answer(
        t(LANG, "agent_registration_location"),
        reply_markup=request_location_keyboard(LANG),
    )


@router.message(ShopRegistration.waiting_location, F.location)
async def got_location(message: Message, state: FSMContext):
    await state.update_data(latitude=message.location.latitude, longitude=message.location.longitude)
    await _finalize_registration(message, state)


@router.message(ShopRegistration.waiting_location, F.text == t(LANG, "agent_registration_location_later"))
async def location_later(message: Message, state: FSMContext):
    await state.update_data(latitude=None, longitude=None)
    await _finalize_registration(message, state, location_pending=True)


async def _finalize_registration(message: Message, state: FSMContext, location_pending: bool = False):
    """
    Ro'yxatga olish paytida do'konchi hali botga /start bosmagan bo'ladi —
    shuning uchun uning telegram_id'si hali noma'lum. Buning o'rniga bir martalik
    `registration_token` yaratamiz va shopni shu token bilan saqlaymiz.

    Do'konchi keyinroq shu token bilan deep-link (t.me/bot?start=reg_<token>)
    orqali botni ochganda, handlers/shop/start.py uning telegram_id'sini
    shu yozuvga bog'laydi. Bu — agent shaxsan borib ro'yxatga olayotgani uchun
    eng ishonchli usul (10-bo'limdagi shaxsiy ishonch strategiyasiga ham mos:
    do'konchi havolani agentning o'zidan oladi).
    """
    data = await state.get_data()
    token = secrets.token_hex(4)

    async with async_session_factory() as session:
        shop = Shop(
            telegram_id=None,
            registration_token=token,
            dokon_rasmi=data.get("dokon_rasmi"),
            dokon_nomi=data["dokon_nomi"],
            egasi_ismi=data["egasi_ismi"],
            boshqaruvchi_ismi=data.get("boshqaruvchi_ismi"),
            boshqaruvchi_telefon=data.get("boshqaruvchi_telefon"),
            telefon=data["telefon"],
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
        )
        session.add(shop)
        await session.commit()

    await state.clear()
    me = await message.bot.get_me()
    deep_link = f"https://t.me/{me.username}?start=reg_{token}"

    await message.answer(
        t(LANG, "agent_registration_done", **data),
        reply_markup=remove_keyboard(),
    )
    await message.answer(t(LANG, "agent_registration_link", link=deep_link))
    if location_pending:
        await message.answer(t(LANG, "agent_registration_location_pending"))
    await message.answer(t(LANG, "agent_menu_title"), reply_markup=agent_main_menu())
