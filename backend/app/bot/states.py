"""FSM-состояния для всех сценариев."""
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


class SubmitReceipt(StatesGroup):
    """FSM отправки чека."""

    pick_shop = State()
    pick_seller = State()
    enter_name = State()
    pick_category = State()
    enter_amount = State()
    attach_photo = State()
    confirm = State()


class EditReceipt(StatesGroup):
    """FSM редактирования заявки (одно поле за раз)."""

    pick_field = State()
    edit_amount = State()
    edit_photo = State()


class ContactAdmin(StatesGroup):
    """FSM «Связаться с админом»."""

    typing_message = State()


class AdminSubstate(StatesGroup):
    """Админская навигация по спискам — текущая страница/фильтр."""

    browsing = State()


class AdminSellerAdd(StatesGroup):
    """FSM добавления продавца админом."""

    enter_name = State()
    pick_category = State()


class AdminSellerEdit(StatesGroup):
    """FSM редактирования продавца админом."""

    pick_field = State()


class AdminShopAdd(StatesGroup):
    """FSM добавления магазина админом."""

    enter_name = State()


class AdminSettings(StatesGroup):
    """FSM настроек конкурса админом."""

    enter_day_goal = State()
    enter_night_goal = State()
