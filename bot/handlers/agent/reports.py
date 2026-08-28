"""
12-bo'lim: agent istalgan vaqtda hisobotni ko'ra oladi.
To'liq grafik tajriba Mini App'da (Recharts); bu yerda tezkor matnli xulosa —
mini app ochilmagan holatlarda ham darhol javob berish uchun.
"""
import datetime as dt

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import config
from bot.locales.i18n import t
from bot.services import reports_service

router = Router(name="agent_reports")

LANG = "uz"


def _range_keyboard() -> InlineKeyboardMarkup:
    dashboard_url = f"{config.webapp_url}?view=agent&screen=reports" if config.webapp_url else None
    rows = [
        [InlineKeyboardButton(text="Bugun", callback_data="report:today")],
        [InlineKeyboardButton(text="Shu hafta", callback_data="report:week")],
        [InlineKeyboardButton(text="Shu oy", callback_data="report:month")],
        [InlineKeyboardButton(text="Oxirgi 30 kun", callback_data="report:30d")],
    ]
    if dashboard_url:
        rows.append([InlineKeyboardButton(text="📊 Grafiklar bilan ko'rish", url=dashboard_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "agent:reports")
async def reports_menu(callback: CallbackQuery):
    await callback.message.answer(t(LANG, "report_choose_range"), reply_markup=_range_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("report:"))
async def show_report(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    today = dt.date.today()
    if key == "today":
        start = end = today
    elif key == "week":
        start, end = today - dt.timedelta(days=today.weekday()), today
    elif key == "month":
        start, end = today.replace(day=1), today
    else:  # 30d
        start, end = today - dt.timedelta(days=30), today

    data = await reports_service.summary(start, end)
    totals = data["totals"]
    lines = [
        f"📊 <b>Hisobot: {start.strftime('%d.%m')} — {end.strftime('%d.%m')}</b>",
        f"🧾 Buyurtmalar: {totals['orders_count']}",
        f"💰 Umumiy summa: {totals['total_amount']:,.0f} so'm",
    ]
    if data["top_products"]:
        lines.append("\n🏆 Eng ko'p sotilgan:")
        for p in data["top_products"]:
            lines.append(f"  • {p['name']} — {p['quantity']} dona")
    if data["top_shops"]:
        lines.append("\n🏪 Eng faol do'konlar:")
        for s in data["top_shops"][:5]:
            lines.append(f"  • {s['shop_name']} — {s['total']:,.0f} so'm ({s['orders_count']} buyurtma)")

    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()
