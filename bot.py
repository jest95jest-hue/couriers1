import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_ID
from states import Registration

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# ============ КЛАВИАТУРЫ ============

def get_courier_type_keyboard():
    """Клавиатура выбора типа курьера"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Пеший курьер")],
            [KeyboardButton(text="Курьер на авто")],
        ],
        resize_keyboard=True
    )
    return keyboard


def get_pedestrian_workplace_keyboard():
    """Клавиатура для пешего курьера"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Яндекс еда")],
            [KeyboardButton(text="Яндекс доставка")],
            [KeyboardButton(text="Вкусвилл")],
        ],
        resize_keyboard=True
    )
    return keyboard


def get_car_workplace_keyboard():
    """Клавиатура для курьера на авто"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Яндекс доставка")],
            [KeyboardButton(text="Вкусвилл")],
        ],
        resize_keyboard=True
    )
    return keyboard


# ============ ОБРАБОТЧИКИ ============

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Команда /start - начало анкеты"""
    await message.answer(
        "Заполни анкету, чтобы мы могли предложить актуальные вакансии\n\n"
        "👉 Напиши свой город ⬇️\n"
        "👉 Укажи возраст\n\n"
        "Пример: Москва, 22",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Registration.waiting_for_city)


@dp.message(Registration.waiting_for_city)
async def process_city_and_age(message: Message, state: FSMContext):
    """Получение города и возраста в одном сообщении"""

    # Разделяем ответ по запятой
    parts = message.text.split(',')

    if len(parts) < 2:
        await message.answer(
            "❌ Пожалуйста, укажи город и возраст через запятую\n\n"
            "Пример: Москва, 22"
        )
        return

    city = parts[0].strip()
    age = parts[1].strip()

    # Проверяем, что возраст - это число
    if not age.isdigit():
        await message.answer(
            "❌ Возраст должен быть числом\n\n"
            "Пример: Москва, 22"
        )
        return

    # Сохраняем данные
    await state.update_data(city=city, age=age)

    # СРАЗУ переходим к выбору вакансий
    await message.answer(
        "Актуальные вакансии:",
        reply_markup=get_courier_type_keyboard()
    )
    await state.set_state(Registration.choosing_courier_type)


@dp.message(Registration.choosing_courier_type, F.text == "Пеший курьер")
async def choose_pedestrian(message: Message, state: FSMContext):
    """Выбор пешего курьера"""
    await state.update_data(courier_type="Пеший курьер")
    await message.answer(
        "Выбери место работы:",
        reply_markup=get_pedestrian_workplace_keyboard()
    )
    await state.set_state(Registration.choosing_workplace)


@dp.message(Registration.choosing_courier_type, F.text == "Курьер на авто")
async def choose_car_courier(message: Message, state: FSMContext):
    """Выбор курьера на авто"""
    await state.update_data(courier_type="Курьер на авто")
    await message.answer(
        "Выбери место работы:",
        reply_markup=get_car_workplace_keyboard()
    )
    await state.set_state(Registration.choosing_workplace)


@dp.message(Registration.choosing_workplace)
async def process_workplace(message: Message, state: FSMContext):
    """Финальный выбор места работы и отправка заявки админу"""
    workplace = message.text

    # Проверка корректности выбора
    valid_workplaces = ["Яндекс еда", "Яндекс доставка", "Вкусвилл"]
    if workplace not in valid_workplaces:
        await message.answer("❌ Пожалуйста, выбери место работы из предложенных кнопок")
        return

    # Сохраняем место работы
    await state.update_data(workplace=workplace)

    # Получаем все данные
    data = await state.get_data()

    # Формируем заявку для админа
    application = (
        f"📋 <b>Новая заявка!</b>\n\n"
        f"👤 @{message.from_user.username or 'без_username'}\n"
        f"🏙 Город: {data['city']}\n"
        f"🎂 Возраст: {data['age']}\n"
        f"🚶 Тип: {data['courier_type']}\n"
        f"🏢 Место работы: {workplace}"
    )

    # Отправляем заявку админу
    try:
        await bot.send_message(ADMIN_ID, application, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка отправки заявки админу: {e}")

    # Отправляем инструкцию пользователю
    await message.answer(
        f"✅ Отлично! Вы выбрали: <b>{workplace}</b>\n\n"
        f"📌Предпочтения по вакансии и выбор удобного района для работы вы можете обсудить с нашим менеджером - @ole_geek\n\n"
        f"Ожидайте сообщения от менеджера в течении нескольких часов\n\n"
        f"Если есть вопросы — пишите @ole_geek",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )

    # Очищаем состояние
    await state.clear()


# ============ ЗАПУСК БОТА ============

async def main():
    print("🔄 Инициализация бота...")

    try:
        print("🔗 Подключение к Telegram API...")
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Успешное подключение!")

        print("🚀 Запуск polling...")
        await dp.start_polling(bot)

    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("🛑 Закрытие сессии...")
        await bot.session.close()


if __name__ == "__main__":
    try:
        print("=" * 50)
        print("ЗАПУСК БОТА")
        print("=" * 50)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")

