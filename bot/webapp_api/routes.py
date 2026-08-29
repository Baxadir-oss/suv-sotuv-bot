"""
Mini App uchun JSON API. Aiogram'ning webhook aiohttp ilovasiga qo'shiladi
(bot/main.py), shu sabab alohida server/porto kerak emas — 0.5 GB xotira
sharoitida bitta jarayon yetarli.
"""
from __future__ import annotations

import base64
import datetime as dt

from aiohttp import web
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from bot.config import config
from bot.database.db import async_session_factory
from bot.database.models import Order, Product, Shop
from bot.services import broadcast_service, order_service, reports_service
from bot.webapp_api.auth import InvalidInitData, validate_init_data

routes = web.RouteTableDef()


def _decode_base64_image(data: str) -> bytes:
    """'data:image/jpeg;base64,....' yoki xom base64 satrni bytega aylantiradi."""
    if "," in data and data.strip().startswith("data:"):
        data = data.split(",", 1)[1]
    return base64.b64decode(data)


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


# ---------- 6-bo'lim: mahsulotlar — Mini App'dagi "Mahsulotlar" bo'limi ----------


def _product_json(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "price": p.price,
        "unit": p.unit,
        "is_available": p.is_available,
        "sort_order": p.sort_order,
        "photo_url": f"/api/photo/{p.photo_file_id}" if p.photo_file_id else None,
    }


@routes.get("/api/agent/products")
async def api_agent_products(request: web.Request) -> web.Response:
    """Katalogdan farqli o'laroq — yashiringan mahsulotlarni ham ko'rsatadi (agent boshqaruvi uchun)."""
    _require_agent(request)
    async with async_session_factory() as session:
        result = await session.execute(select(Product).order_by(Product.sort_order, Product.id))
        products = list(result.scalars())
    return web.json_response([_product_json(p) for p in products])


@routes.post("/api/agent/products")
async def api_agent_create_product(request: web.Request) -> web.Response:
    user = _require_agent(request)
    body = await request.json()

    name = (body.get("name") or "").strip()
    unit = (body.get("unit") or "").strip()
    try:
        price = float(body.get("price"))
    except (TypeError, ValueError):
        raise web.HTTPBadRequest(text="Narx noto'g'ri")
    if not name or not unit:
        raise web.HTTPBadRequest(text="Nomi va birligi kerak")

    photo_file_id = None
    if body.get("photo_base64"):
        photo_bytes = _decode_base64_image(body["photo_base64"])
        photo_file_id = await broadcast_service.upload_photo_via_bot(request.app["bot"], user["id"], photo_bytes)

    async with async_session_factory() as session:
        result = await session.execute(select(Product.sort_order).order_by(Product.sort_order.desc()).limit(1))
        max_order = result.scalar_one_or_none() or 0
        product = Product(name=name, price=price, unit=unit, photo_file_id=photo_file_id, sort_order=max_order + 1)
        session.add(product)
        await session.commit()
        await session.refresh(product)

    return web.json_response(_product_json(product))


@routes.patch("/api/agent/products/{product_id}")
async def api_agent_update_product(request: web.Request) -> web.Response:
    user = _require_agent(request)
    product_id = int(request.match_info["product_id"])
    body = await request.json()

    async with async_session_factory() as session:
        product = await session.get(Product, product_id)
        if product is None:
            raise web.HTTPNotFound(text="Mahsulot topilmadi")

        if "name" in body:
            product.name = body["name"].strip()
        if "unit" in body:
            product.unit = body["unit"].strip()
        if "price" in body:
            try:
                product.price = float(body["price"])
            except (TypeError, ValueError):
                raise web.HTTPBadRequest(text="Narx noto'g'ri")
        if "is_available" in body:
            product.is_available = bool(body["is_available"])
        if body.get("photo_base64"):
            photo_bytes = _decode_base64_image(body["photo_base64"])
            product.photo_file_id = await broadcast_service.upload_photo_via_bot(
                request.app["bot"], user["id"], photo_bytes
            )

        await session.commit()
        await session.refresh(product)

    return web.json_response(_product_json(product))


@routes.post("/api/agent/products/reorder")
async def api_agent_reorder_products(request: web.Request) -> web.Response:
    """Body: {"order": [product_id, product_id, ...]} — shu tartibda sort_order beriladi."""
    _require_agent(request)
    body = await request.json()
    order = body.get("order", [])

    async with async_session_factory() as session:
        for index, product_id in enumerate(order):
            product = await session.get(Product, product_id)
            if product:
                product.sort_order = index
        await session.commit()

    return web.json_response({"status": "ok"})


# ---------- 7/16-bo'lim: reklama — Mini App'dagi "Reklama" bo'limi ----------


@routes.get("/api/agent/broadcast/status")
async def api_broadcast_status(request: web.Request) -> web.Response:
    _require_agent(request)
    remaining = await broadcast_service.days_until_next_allowed()
    return web.json_response({"can_send": remaining is None, "days_remaining": remaining})


@routes.post("/api/agent/broadcast")
async def api_agent_broadcast(request: web.Request) -> web.Response:
    user = _require_agent(request)
    body = await request.json()

    template_type = body.get("template_type", "new")
    text = (body.get("text") or "").strip()
    if not text:
        raise web.HTTPBadRequest(text="Matn kerak")

    photo_file_id = None
    if body.get("photo_base64"):
        photo_bytes = _decode_base64_image(body["photo_base64"])
        photo_file_id = await broadcast_service.upload_photo_via_bot(request.app["bot"], user["id"], photo_bytes)

    result = await broadcast_service.submit_broadcast(request.app["bot"], template_type, text, photo_file_id)
    return web.json_response(result)
        
