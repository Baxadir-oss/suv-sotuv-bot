"""
Konfiguratsiya — barcha maxfiy va muhit sozlamalari .env orqali yuklanadi.
Railway'da bu qiymatlar loyihaning "Variables" bo'limida beriladi.
"""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _get_int_list(raw: str) -> list[int]:
    if not raw:
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


@dataclass
class Config:
    # Bot Father'dan olingan token
    bot_token: str = field(default_factory=lambda: os.environ["BOT_TOKEN"])

    # Faqat shu telegram_id(lar) agent sifatida ishlay oladi.
    # Bir nechta agent bo'lsa vergul bilan: "111111111,222222222"
    agent_ids: list[int] = field(default_factory=lambda: _get_int_list(os.getenv("AGENT_IDS", "")))

    # Mini App (Telegram WebApp) ochiladigan URL — Railway domeningiz
    webapp_url: str = field(default_factory=lambda: os.getenv("WEBAPP_URL", ""))

    # Webhook uchun asosiy domen (masalan https://xxx.up.railway.app).
    # Bo'sh qoldirilsa, bot polling rejimida ishlaydi (lokal test uchun qulay).
    webhook_base_url: str = field(default_factory=lambda: os.getenv("WEBHOOK_BASE_URL", ""))
    webhook_path: str = "/webhook"
    webhook_secret: str = field(default_factory=lambda: os.getenv("WEBHOOK_SECRET", "suv-bot-secret"))

    # Server porti — Railway PORT o'zgaruvchisini avtomatik beradi
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8080")))

    # Ma'lumotlar bazasi fayli (SQLite — 0.5 GB xotira uchun eng yengil variant)
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "suv_bot.db"))

    # Agentning aloqa raqami — ro'yxatdan o'tmagan foydalanuvchiga ko'rsatiladi
    agent_contact_phone: str = field(default_factory=lambda: os.getenv("AGENT_CONTACT_PHONE", "+998 88 526 20 03"))

    # Reklama cheklovlari (7-bo'limga mos)
    ad_min_interval_days: int = 7
    ad_allowed_hour_start: int = 10
    ad_allowed_hour_end: int = 18

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.db_path}"


config = Config()
