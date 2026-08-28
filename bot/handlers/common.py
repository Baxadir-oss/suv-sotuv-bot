"""
/start — uchala holat uchun ham shu yerda: do'kon, agent, va deep-link orqali
ro'yxatga ulanish. Bularni bitta handlerda ushlab turish muhim, chunki aiogram'da
bir xil filterga (Command("start")) mos ikkita alohida handler yozilsa, birinchisi
ishlagach ikkinchisiga navbat yetmaydi.
"""
from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.config import config
from bot.database.db import async_session_factory
from bot.database.models import Shop
from bot.keyboards import agent_main_menu, language_keyboard, shop_main_menu
from bot.locales.i18n import t

router = Router(name="common")


@router.message(Command("start"))
async def handle_start(message: Message, command: CommandObject, shop: Shop | None, is_agent: bool):
    if command.args and command.args.startswith("reg_"):
        await _bind_shop_from_token(message, command.args.removeprefix("reg_"))
        return

    if is_agent:
        await message.answer(t("uz", "agent_menu_title"), reply_markup=agent_main_menu())
        return

    if shop is None or not shop.is_registered_and_open:
        await message.answer(t("uz", "not_registered", phone=config.agent_contact_phone))
        return

    lang = shop.til
    await message.answer(
        t(lang, "welcome_back", name=shop.boshqaruvchi_display_name),
        reply_markup=shop_main_menu(lang),
    )


async def _bind_shop_from_token(message: Message, token: str) -> None:
    """Agent bergan ro'yxatga olish havolasi bosilganda do'konning telegram_id'sini bog'laydi."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Shop).where(Shop.registration_token == token, Shop.telegram_id.is_(None))
        )
        shop = result.scalar_one_or_none()
        if shop is None:
            await message.answer(t("uz", "registration_link_invalid"))
            return

        shop.telegram_id = message.from_user.id
        shop.registration_token = None
        await session.commit()
        lang, name = shop.til, shop.boshqaruvchi_display_name

    await message.answer(t(lang, "registration_link_success", name=name))
    await message.answer(t(lang, "welcome_back", name=name), reply_markup=shop_main_menu(lang))


@router.message(Command("til", "language"))
async def choose_language(message: Message):
    await message.answer(t("uz", "language_choose"), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery, shop: Shop | None):
    lang = callback.data.split(":", 1)[1]
    if shop:
        async with async_session_factory() as session:
            db_shop = await session.get(Shop, shop.id)
            db_shop.til = lang
            await session.commit()
    await callback.message.edit_text(t(lang, "language_set"))
    await callback.answer()
