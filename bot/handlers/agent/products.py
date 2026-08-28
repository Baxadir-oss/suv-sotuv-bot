"""
6-bo'lim: mahsulot katalogini agent tomonidan to'liq boshqarish.

- Qo'shish: rasm -> nom -> narx -> birlik
- Tahrirlash: istalgan bitta maydonni alohida o'zgartirish
- Yashirish/ko'rsatish: "mavjud emas" holati — butunlay o'chirilmaydi
  (eski buyurtmalar tarixi buzilmasligi uchun, order_items nusxa saqlaydi)
- Tartib: yuqoriga/pastga surish orqali "birinchi ko'rinadigan" tartib
"""
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from bot.database.db import async_session_factory
from bot.database.models import Product
from bot.states import ProductForm

router = Router(name="agent_products")

FIELD_LABELS = {"name": "Nomi", "price": "Narxi", "unit": "Birligi", "photo": "Rasmi"}


def _product_list_keyboard(products: list[Product]) -> InlineKeyboardMarkup:
    rows = []
    for p in products:
        mark = "👁" if p.is_available else "🙈"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {p.name} — {p.price:,.0f} so'm/{p.unit}",
                    callback_data=f"prod:edit:{p.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ Yangi mahsulot", callback_data="prod:add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _product_edit_keyboard(product: Product) -> InlineKeyboardMarkup:
    visibility_text = "🙈 Vaqtincha yashirish" if product.is_available else "👁 Qayta ko'rsatish"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Nomi", callback_data=f"prod:field:{product.id}:name")],
            [InlineKeyboardButton(text="💰 Narxi", callback_data=f"prod:field:{product.id}:price")],
            [InlineKeyboardButton(text="📏 Birligi", callback_data=f"prod:field:{product.id}:unit")],
            [InlineKeyboardButton(text="📷 Rasmi", callback_data=f"prod:field:{product.id}:photo")],
            [InlineKeyboardButton(text=visibility_text, callback_data=f"prod:toggle:{product.id}")],
            [
                InlineKeyboardButton(text="⬆️", callback_data=f"prod:move:{product.id}:up"),
                InlineKeyboardButton(text="⬇️", callback_data=f"prod:move:{product.id}:down"),
            ],
            [InlineKeyboardButton(text="« Ro'yxatga qaytish", callback_data="agent:products")],
        ]
    )


@router.callback_query(F.data == "agent:products")
async def show_products(callback: CallbackQuery):
    async with async_session_factory() as session:
        result = await session.execute(select(Product).order_by(Product.sort_order, Product.id))
        products = list(result.scalars())

    text = "📦 Mahsulotlar katalogi:" if products else "Hozircha mahsulot yo'q. Qo'shishdan boshlang."
    if callback.message.text:
        await callback.message.edit_text(text, reply_markup=_product_list_keyboard(products))
    else:
        await callback.message.answer(text, reply_markup=_product_list_keyboard(products))
    await callback.answer()


@router.callback_query(F.data == "prod:add")
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProductForm.waiting_photo)
    await callback.message.answer("1-qadam: Mahsulot rasmini yuboring 📷")
    await callback.answer()


@router.message(ProductForm.waiting_photo, F.photo)
async def add_product_photo(message: Message, state: FSMContext):
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await state.set_state(ProductForm.waiting_name)
    await message.answer("2-qadam: Mahsulot nomini kiriting")


@router.message(ProductForm.waiting_name, F.text)
async def add_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(ProductForm.waiting_price)
    await message.answer("3-qadam: Narxini kiriting (faqat son, masalan: 25000)")


@router.message(ProductForm.waiting_price, F.text)
async def add_product_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(" ", "").replace(",", "."))
    except ValueError:
        await message.answer("Iltimos, narxni faqat son sifatida kiriting (masalan: 25000)")
        return
    await state.update_data(price=price)
    await state.set_state(ProductForm.waiting_unit)
    await message.answer("4-qadam (oxirgi): Birligini kiriting (masalan: blok, karobka, litr)")


@router.message(ProductForm.waiting_unit, F.text)
async def add_product_unit(message: Message, state: FSMContext):
    data = await state.get_data()
    async with async_session_factory() as session:
        result = await session.execute(select(Product.sort_order).order_by(Product.sort_order.desc()).limit(1))
        max_order = result.scalar_one_or_none() or 0
        product = Product(
            name=data["name"],
            price=data["price"],
            unit=message.text.strip(),
            photo_file_id=data.get("photo_file_id"),
            sort_order=max_order + 1,
        )
        session.add(product)
        await session.commit()

    await state.clear()
    await message.answer(f"✅ '{product.name}' katalogga qo'shildi!")


@router.callback_query(F.data.startswith("prod:edit:"))
async def edit_product_menu(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[2])
    async with async_session_factory() as session:
        product = await session.get(Product, product_id)
    if product is None:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    await callback.message.edit_text(
        f"{product.name} — {product.price:,.0f} so'm/{product.unit}",
        reply_markup=_product_edit_keyboard(product),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("prod:toggle:"))
async def toggle_product(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[2])
    async with async_session_factory() as session:
        product = await session.get(Product, product_id)
        product.is_available = not product.is_available
        await session.commit()
        await session.refresh(product)
    await callback.message.edit_reply_markup(reply_markup=_product_edit_keyboard(product))
    await callback.answer("Holat yangilandi")


@router.callback_query(F.data.startswith("prod:move:"))
async def move_product(callback: CallbackQuery):
    _, _, product_id, direction = callback.data.split(":")
    product_id = int(product_id)
    async with async_session_factory() as session:
        result = await session.execute(select(Product).order_by(Product.sort_order, Product.id))
        products = list(result.scalars())
        idx = next((i for i, p in enumerate(products) if p.id == product_id), None)
        if idx is None:
            await callback.answer()
            return
        swap_idx = idx - 1 if direction == "up" else idx + 1
        if 0 <= swap_idx < len(products):
            products[idx].sort_order, products[swap_idx].sort_order = (
                products[swap_idx].sort_order,
                products[idx].sort_order,
            )
            await session.commit()
    await callback.answer("Tartib yangilandi")
    await show_products(callback)


@router.callback_query(F.data.startswith("prod:field:"))
async def choose_field_to_edit(callback: CallbackQuery, state: FSMContext):
    _, _, product_id, field = callback.data.split(":")
    await state.update_data(product_id=int(product_id), field=field)
    await state.set_state(ProductForm.editing_field)
    prompt = {
        "name": "Yangi nomni kiriting:",
        "price": "Yangi narxni kiriting (faqat son):",
        "unit": "Yangi birlikni kiriting:",
        "photo": "Yangi rasmni yuboring:",
    }[field]
    await callback.message.answer(prompt)
    await callback.answer()


@router.message(ProductForm.editing_field, F.text | F.photo)
async def save_edited_field(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data["field"]

    async with async_session_factory() as session:
        product = await session.get(Product, data["product_id"])
        if product is None:
            await message.answer("Mahsulot topilmadi.")
            await state.clear()
            return

        if field == "photo":
            if not message.photo:
                await message.answer("Iltimos, rasm yuboring.")
                return
            product.photo_file_id = message.photo[-1].file_id
        elif field == "price":
            try:
                product.price = float(message.text.replace(" ", "").replace(",", "."))
            except ValueError:
                await message.answer("Iltimos, narxni faqat son sifatida kiriting.")
                return
        elif field == "name":
            product.name = message.text.strip()
        elif field == "unit":
            product.unit = message.text.strip()

        await session.commit()

    await state.clear()
    await message.answer(f"✅ {FIELD_LABELS[field]} yangilandi.")
