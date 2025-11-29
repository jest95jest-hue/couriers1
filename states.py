from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    waiting_for_city = State()
    waiting_for_age = State()
    choosing_courier_type = State()
    choosing_workplace = State()