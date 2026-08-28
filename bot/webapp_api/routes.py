"""
Mini App uchun JSON API. Aiogram'ning webhook aiohttp ilovasiga qo'shiladi
(bot/main.py), shu sabab alohida server/porto kerak emas — 0.5 GB xotira
sharoitida bitta jarayon yetarli.
"""
from __future__ import annotations

import datetime as dt

from aiohttp import web
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from bot.config import config
from bot.database.db import async_session_factory
from bot.database.models import Order, Product, Shop
from bot.services import order_service, reports_service
from bot.webapp_api.auth import InvalidInitData, validate_init_data

routes = web.RouteTableDef()


def _auth_user(request: web.Request) -> dict:
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    try:
        return validate_init_data(init_data)
    except InvalidInitData as exc:
        raise web.HTTPUnauthorized(text=str(exc))


async def _require_shop(request: web.Request) -> Shop:
    user = _auth_user(request)
    async with async_session_factory() as session:
        result = await session.execute(select(Shop).where(Shop.telegram_id == user["id"]))
        shop = result.scalar_one_or_none()
    if shop is None or not shop.is_registered_and_open:
        raise web.HTTPForbidden(text="Do'kon ro'yxatdan o'tmagan")
    return shop


def _require_agent(request: web.Request) -> dict:
    user = _auth_user(request)
    if user["id"] not in config.agent_ids:
        raise web.HTTPForbidden(text="Faqat agent uchun")
    return user


@routes.get("/api/me")
async def api_me(request: web.Request) -> web.Response:
    user = _auth_user(request)
    if user["id"] in config.agent_ids:
        return web.json_response({"role": "agent", "id": user["id"]})

    async with async_session_factory() as session:
        result = await session.execute(select(Shop).where(Shop.telegram_id == user["id"]))
        shop = result.scalar_one_or_none()

    if shop is None or not shop.is_registered_and_open:
        return web.json_response({"role": "unregistered"}, status=403)

    return web.json_response(
        {
            "role": "shop",
            "shop_id": shop.id,
            "shop_name": shop.dokon_nomi,
            "display_name": shop.boshqaruvchi_display_name,
            "lang": shop.til,
        }
    )


@routes.get("/api/catalog")
async def api_catalog(request: web.Request) -> web.Response:
    await _require_shop(request)
    async with async_session_factory() as session:
        result = await session.execute(
            select(Product).where(Product.is_available == True).order_by(Product.sort_order, Product.id)  # noqa: E712
        )
        products = list(result.scalars())

    return web.json_response(
        [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "unit": p.unit,
                "photo_url": f"/api/photo/{p.photo_file_id}" if p.photo_file_id else None,
            }
            for p in products
        ]
    )


@routes.post("/api/order")
async def api_create_order(request: web.Request) -> web.Response:
    shop = await _require_shop(request)
    body = await request.json()
    items = body.get("items", [])

    try:
        order = await order_service.create_order(shop.id, items, bot=request.app["bot"])
    except order_service.OrderError as exc:
        raise web.HTTPBadRequest(text=str(exc))

    async with async_session_factory() as session:
        result = await session.execute(
            select(Order).where(Order.id == order.id).options(selectinload(Order.items))
        )
        full_order = result.scalar_one()
        summary_text = await order_service.order_summary_text(full_order, shop.til)

    return web.json_response(
        {
            "order_id": order.id,
            "total_amount": order.total_amount,
            "summary_text": summary_text,
        }
    )


@routes.get("/api/reports")
async def api_reports(request: web.Request) -> web.Response:
    _require_agent(request)
    try:
        start = dt.date.fromisoformat(request.query["start"])
        end = dt.date.fromisoformat(request.query["end"])
    except (KeyError, ValueError):
        raise web.HTTPBadRequest(text="start va end (YYYY-MM-DD) kerak")

    data = await reports_service.summary(start, end)
    return web.json_response(data)


@routes.get("/api/shops/search")
async def api_shops_search(request: web.Request) -> web.Response:
    _require_agent(request)
    q = request.query.get("q", "").strip()
    pattern = f"%{q}%"

    async with async_session_factory() as session:
        result = await session.execute(
            select(Shop)
            .where(
                or_(
                    Shop.dokon_nomi.ilike(pattern),
                    Shop.egasi_ismi.ilike(pattern),
                    Shop.telefon.ilike(pattern),
                    Shop.boshqaruvchi_telefon.ilike(pattern),
                )
            )
            .limit(30)
        )
        shops = list(result.scalars())

    return web.json_response(
        [
            {
                "id": s.id,
                "shop_name": s.dokon_nomi,
                "owner_name": s.egasi_ismi,
                "phone": s.telefon,
                "photo_url": f"/api/photo/{s.dokon_rasmi}" if s.dokon_rasmi else None,
                "total_orders": s.total_orders,
                "is_blocked": s.is_blocked,
                "is_pending": s.telegram_id is None,
                "latitude": s.latitude,
                "longitude": s.longitude,
            }
            for s in shops
        ]
    )


@routes.get("/api/photo/{file_id}")
async def api_photo(request: web.Request) -> web.StreamResponse:
    """Telegram file_id'ni frontend uchun oddiy rasm bytega aylantiradi (bot tokenini frontendga chiqarmaslik uchun)."""
    file_id = request.match_info["file_id"]
    bot = request.app["bot"]
    try:
        file = await bot.get_file(file_id)
        file_bytes = await bot.download_file(file.file_path)
    except Exception:
        raise web.HTTPNotFound(text="Rasm topilmadi")

    return web.Response(body=file_bytes.read(), content_type="image/jpeg")
