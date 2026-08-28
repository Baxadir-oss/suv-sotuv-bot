"""
12-bo'lim: agent uchun on-demand hisobot — kunlik aniqlikda agregatsiya.
Bir xil funksiyalar ham /hisobot buyrug'i, ham Mini App API tomonidan ishlatiladi.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select

from bot.database.db import async_session_factory
from bot.database.models import Order, OrderItem, Shop


async def daily_breakdown(start: dt.date, end: dt.date) -> list[dict]:
    """Har bir kun bo'yicha: buyurtmalar soni, umumiy summa, faol do'konlar soni."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(
                func.date(Order.created_at).label("day"),
                func.count(Order.id).label("orders_count"),
                func.sum(Order.total_amount).label("total"),
                func.count(func.distinct(Order.shop_id)).label("active_shops"),
            )
            .where(func.date(Order.created_at) >= start, func.date(Order.created_at) <= end)
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )
        rows = result.all()

    return [
        {
            "date": row.day,
            "orders_count": row.orders_count,
            "total": float(row.total or 0),
            "active_shops": row.active_shops,
        }
        for row in rows
    ]


async def top_products(start: dt.date, end: dt.date, limit: int = 3) -> list[dict]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("qty"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .where(func.date(Order.created_at) >= start, func.date(Order.created_at) <= end)
            .group_by(OrderItem.product_name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
        )
        return [{"name": row.product_name, "quantity": int(row.qty)} for row in result.all()]


async def top_shops(start: dt.date, end: dt.date, limit: int = 10) -> list[dict]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(
                Shop.dokon_nomi,
                func.count(Order.id).label("orders_count"),
                func.sum(Order.total_amount).label("total"),
            )
            .join(Order, Order.shop_id == Shop.id)
            .where(func.date(Order.created_at) >= start, func.date(Order.created_at) <= end)
            .group_by(Shop.id)
            .order_by(func.sum(Order.total_amount).desc())
            .limit(limit)
        )
        return [
            {"shop_name": row.dokon_nomi, "orders_count": row.orders_count, "total": float(row.total or 0)}
            for row in result.all()
        ]


async def summary(start: dt.date, end: dt.date) -> dict:
    breakdown = await daily_breakdown(start, end)
    return {
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "daily": breakdown,
        "top_products": await top_products(start, end),
        "top_shops": await top_shops(start, end),
        "totals": {
            "orders_count": sum(d["orders_count"] for d in breakdown),
            "total_amount": sum(d["total"] for d in breakdown),
        },
    }
