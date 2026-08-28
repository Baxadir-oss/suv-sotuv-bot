"""
5-bo'lim (savat UX) + 14-bo'lim (minnatdorchilik) + 17-bo'lim (miqdorni
o'zgartirmasdan to'liq tasdiqlash) — buyurtma yaratishning yagona joyi.

MUHIM (17-bo'lim): bu funksiya klientdan (Mini App) kelgan miqdorlarni
HECH QACHON avtomatik kamaytirmaydi yoki "to'g'rilamaydi". Qancha kiritilgan
bo'lsa — order_items'ga aynan shu holicha yoziladi. Yagona narsa filtrlanadi:
noldan katta bo'lmagan yoki mavjud bo'lmagan (is_available=False) mahsulotlar
rad etiladi, chunki ular umuman sotib bo'lmaydi.
"""
from __future__ import annotations

import random

from aiogram import Bot
from sqlalchemy import select

from bot.database.db import async_session_factory
from bot.database.models import Order, OrderItem, Product, Shop
from bot.locales.i18n import t, t_list

MILESTONE_EVERY = 10


class OrderError(Exception):
    pass


async def create_order(shop_id: int, items: list[dict], bot: Bot | None = None) -> Order:
    """
    items: [{"product_id": int, "quantity": int}, ...]
    Har bir qator uchun joriy narx bazadan olinib order_items'ga "muzlatiladi".
    """
    if not items:
        raise OrderError("Savat bo'sh")

    async with async_session_factory() as session:
        shop = await session.get(Shop, shop_id)
        if shop is None or not shop.is_registered_and_open:
            raise OrderError("Do'kon topilmadi yoki faol emas")

        order = Order(shop_id=shop.id, total_amount=0)
        session.add(order)
        await session.flush()  # order.id kerak

        total = 0.0
        for item in items:
            qty = int(item.get("quantity", 0))
            if qty <= 0:
                continue
            product = await session.get(Product, item["product_id"])
            if product is None or not product.is_available:
                continue
            # 17-bo'lim: qty aynan kiritilganicha yoziladi — bu yerda cheklov yo'q
            line = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=qty,
                frozen_price=product.price,
            )
            session.add(line)
            total += qty * product.price

        if total == 0:
            await session.rollback()
            raise OrderError("Buyurtmada haqiqiy mahsulot yo'q")

        order.total_amount = total
        shop.total_orders += 1
        order_count = shop.total_orders
        shop_lang = shop.til
        shop_name = shop.boshqaruvchi_display_name
        shop_telegram_id = shop.telegram_id

        await session.commit()
        await session.refresh(order)

    if bot is not None and shop_telegram_id:
        await _send_thank_you(bot, shop_telegram_id, shop_lang, shop_name, order_count)

    return order


async def _send_thank_you(bot: Bot, telegram_id: int, lang: str, name: str, order_count: int) -> None:
    """14-bo'lim: har safar avtomatik, lekin mexanik tuyulmaydigan minnatdorchilik xabari."""
    if order_count == 1:
        text = t(lang, "thanks_first_order", name=name)
    elif order_count % MILESTONE_EVERY == 0:
        text = t(lang, "thanks_milestone", count=order_count)
    else:
        variants = t_list(lang, "thanks_variants")
        text = random.choice(variants).format(name=name) if variants else t(lang, "thanks_variants")

    await bot.send_message(telegram_id, text)


async def order_summary_text(order: Order, lang: str = "uz") -> str:
    """To'liq xulosa — savat yopilishidan oldin ko'rsatiladigan matn (17-bo'lim)."""
    lines = [t(lang, "order_summary_title")]
    for item in order.items:
        lines.append(f"• {item.product_name} — {item.quantity} x {item.frozen_price:,.0f} = {item.quantity * item.frozen_price:,.0f} so'm")
    lines.append(t(lang, "order_total", total=f"{order.total_amount:,.0f}"))
    return "\n".join(lines)
