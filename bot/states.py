from aiogram.fsm.state import State, StatesGroup


class ShopRegistration(StatesGroup):
    """3-bo'lim: rasm → egasi ismi → boshqaruvchi ismi → boshq. telefon → dokon nomi → telefon → lokatsiya."""

    waiting_photo = State()
    waiting_owner_name = State()
    waiting_manager_name = State()
    waiting_manager_phone = State()
    waiting_shop_name = State()
    waiting_phone = State()
    waiting_location = State()


class ProductForm(StatesGroup):
    """6-bo'lim: mahsulot qo'shish/tahrirlash."""

    waiting_photo = State()
    waiting_name = State()
    waiting_price = State()
    waiting_unit = State()
    editing_field = State()


class BroadcastForm(StatesGroup):
    """16-bo'lim: reklama shabloni → matn → rasm (ixtiyoriy)."""

    choosing_template = State()
    waiting_text = State()
    waiting_photo = State()
