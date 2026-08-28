"""
Telegram Mini App'dan kelgan so'rovlarni tekshirish.

Telegram'ning rasmiy algoritmi: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
Mini App frontend har bir API so'roviga `window.Telegram.WebApp.initData`
qiymatini `X-Telegram-Init-Data` sarlavhasi orqali yuboradi (webapp/src/api.js'ga qarang).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from bot.config import config

INIT_DATA_MAX_AGE_SECONDS = 24 * 60 * 60  # 24 soat — eskirgan sessiyalarni rad etish


class InvalidInitData(Exception):
    pass


def validate_init_data(init_data: str) -> dict:
    """To'g'ri bo'lsa — {"id": int, "first_name": str, ...} foydalanuvchi ma'lumotini qaytaradi."""
    if not init_data:
        raise InvalidInitData("initData bo'sh")

    pairs = dict(parse_qsl(init_data, strict_parsing=False))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InvalidInitData("hash yo'q")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", config.bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise InvalidInitData("hash mos kelmadi")

    auth_date = int(pairs.get("auth_date", 0))
    if time.time() - auth_date > INIT_DATA_MAX_AGE_SECONDS:
        raise InvalidInitData("initData eskirgan")

    user_raw = pairs.get("user")
    if not user_raw:
        raise InvalidInitData("user ma'lumoti yo'q")

    return json.loads(user_raw)
