"""
Ma'lumotlar bazasi modellari (SQLAlchemy, async, SQLite).

Indekslar sana va shop_id bo'yicha qo'yilgan — 0.5 GB xotira sharoitida
hisobot va qidiruv so'rovlari sekinlashmasligi uchun (8-bo'lim).
"""
from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Language(str, enum.Enum):
    UZ = "uz"
    RU = "ru"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"  # kutilmoqda
    CONFIRMED = "confirmed"  # tasdiqlandi
    DELIVERED = "delivered"  # yetkazildi
    CANCELLED = "cancelled"  # bekor qilindi


class Shop(Base):
    """Do'kon — agent tomonidan ro'yxatga olinadi (3-bo'lim, 1-qo'shimcha)."""

    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Agent ro'yxatga olgan payytda do'konchining o'zi hali /start bosmagan bo'ladi,
    # shuning uchun bu maydon boshida bo'sh qoladi va registration_token orqali
    # keyinroq (deep-link bosilganda) to'ldiriladi — pastga, handlers/shop/start.py ga qarang.
    telegram_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True, nullable=True)
    registration_token: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)

    dokon_rasmi: Mapped[str | None] = mapped_column(String(255))  # Telegram file_id
    dokon_nomi: Mapped[str] = mapped_column(String(255))
    egasi_ismi: Mapped[str] = mapped_column(String(255))

    # Bo'sh bo'lsa — egasi bilan bir xil deb hisoblanadi (3-bo'lim)
    boshqaruvchi_ismi: Mapped[str | None] = mapped_column(String(255))
    boshqaruvchi_telefon: Mapped[str | None] = mapped_column(String(64))

    telefon: Mapped[str] = mapped_column(String(64))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    til: Mapped[str] = mapped_column(String(8), default=Language.UZ.value)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    # 14-bo'lim: minnatdorchilik xabarlari uchun buyurtmalar sonini bilish kerak
    total_orders: Mapped[int] = mapped_column(Integer, default=0)

    orders: Mapped[list["Order"]] = relationship(back_populates="shop")

    @property
    def boshqaruvchi_display_name(self) -> str:
        return self.boshqaruvchi_ismi or self.egasi_ismi

    @property
    def is_registered_and_open(self) -> bool:
        return self.telegram_id is not None and self.is_active and not self.is_blocked


class Product(Base):
    """Mahsulot katalogi — agent tomonidan to'liq CRUD (6-bo'lim)."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(64), default="blok")  # masalan: blok, karobka, litr
    photo_file_id: Mapped[str | None] = mapped_column(String(255))

    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class Order(Base):
    """Buyurtma — savat asosidagi UX orqali yaratiladi (5-bo'lim)."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"), index=True)

    status: Mapped[str] = mapped_column(String(32), default=OrderStatus.PENDING.value)
    total_amount: Mapped[float] = mapped_column(Float, default=0)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, index=True)

    shop: Mapped["Shop"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """Buyurtma qatori — narx buyurtma paytida 'muzlatiladi' (10-bo'lim, 17-bo'lim)."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))

    product_name: Mapped[str] = mapped_column(String(255))  # nusxa — mahsulot keyin o'chsa ham tarix buzilmasin
    quantity: Mapped[int] = mapped_column(Integer)
    frozen_price: Mapped[float] = mapped_column(Float)

    order: Mapped["Order"] = relationship(back_populates="items")


class BroadcastLog(Base):
    """Reklama yuborilgan har bir hodisa — 7-bo'limdagi chastota nazorati uchun."""

    __tablename__ = "broadcast_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_type: Mapped[str] = mapped_column(String(64))  # yangi_mahsulot / chegirma / eslatma
    text: Mapped[str] = mapped_column(Text)
    photo_file_id: Mapped[str | None] = mapped_column(String(255))

    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime, index=True)
    scheduled_at: Mapped[dt.datetime | None] = mapped_column(DateTime)  # navbatga qo'yilgan bo'lsa

    delivered_count: Mapped[int] = mapped_column(Integer, default=0)
    blocked_count: Mapped[int] = mapped_column(Integer, default=0)
    # {"telegram_id": true/false} — kim ochgan/ochmaganini keyin ko'rsatish uchun (7-bo'lim)
    open_stats: Mapped[dict] = mapped_column(JSON, default=dict)


Index("ix_orders_shop_created", Order.shop_id, Order.created_at)
