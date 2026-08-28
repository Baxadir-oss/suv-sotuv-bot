from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)

from bot.config import config
from bot.locales.i18n import t


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="O'zbekcha", callback_data="lang:uz"),
                InlineKeyboardButton(text="Русский", callback_data="lang:ru"),
            ]
        ]
    )


def shop_main_menu(lang: str, webapp_path: str = "") -> InlineKeyboardMarkup:
    url = config.webapp_url + webapp_path if config.webapp_url else None
    buttons = []
    if url:
        buttons.append([InlineKeyboardButton(text=t(lang, "open_catalog_button"), web_app=WebAppInfo(url=url))])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def agent_main_menu(lang: str = "uz") -> InlineKeyboardMarkup:
    dashboard_url = f"{config.webapp_url}?view=agent" if config.webapp_url else None
    rows = [
        [InlineKeyboardButton(text="➕ Yangi do'kon", callback_data="agent:register")],
        [InlineKeyboardButton(text="📦 Mahsulotlar", callback_data="agent:products")],
        [InlineKeyboardButton(text="📢 Reklama", callback_data="agent:broadcast")],
        [InlineKeyboardButton(text="🔎 Do'konlarni qidirish", callback_data="agent:search")],
        [InlineKeyboardButton(text="📊 Hisobot (tezkor)", callback_data="agent:reports")],
    ]
    if dashboard_url:
        rows.append([InlineKeyboardButton(text="📊 Hisobotlar (Mini App)", web_app=WebAppInfo(url=dashboard_url))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def request_location_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "agent_registration_location_button"), request_location=True)],
            [KeyboardButton(text=t(lang, "agent_registration_location_later"))],
        ],
        resize_keyboard=True,
    )


def same_as_owner_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "agent_registration_same_as_owner"))]],
        resize_keyboard=True,
    )


def cancel_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "cancel_button"))]],
        resize_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def broadcast_template_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "broadcast_template_new_product"), callback_data="bcast:new")],
            [InlineKeyboardButton(text=t(lang, "broadcast_template_discount"), callback_data="bcast:discount")],
            [InlineKeyboardButton(text=t(lang, "broadcast_template_reminder"), callback_data="bcast:reminder")],
        ]
    )
