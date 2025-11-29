import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web  # Для веб-сервера

from config import BOT_TOKEN, ADMIN_ID
from states import Registration

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# --- КЛАВИАТУРЫ ---
def get_courier_type_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пеший курьер")], [KeyboardButton(text="Курьер на авто")]],
        resize_keyboard=True
    )
    return keyboard

def get_pedestrian_workplace_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Яндекс еда")], [KeyboardButton(text="Яндекс доставка")], [KeyboardButton(text="Вкусвилл")]],
        resize_keyboard=True
    )
    return keyboard

def get_car_workplace_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Яндекс доставка")], [KeyboardButton(text="Вкусвилл")]],
        resize_keyboard=True
    )
    return keyboard


# --- ОБРАБОТЧИКИ ---
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await message.answer(
        "Заполните анкету, чтобы мы могли предложить актуальные вакансии\n\n"
        "☝🏻 Напишите свой город\n✌🏻 Укажите возраст\n\nПример: Москва, 22",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Registration.waiting_for_city)

@dp.message(Registration.waiting_for_city)
async def process_city_and_age(message: Message, state: FSMContext):
    parts = message.text.split(',')
    if len(parts) < 2:
        await message.answer("❌ Пожалуйста, укажите город и возраст через запятую\nПример: Москва, 22")
        return
    city = parts[0].strip()
    age = parts[1].strip()
    if not age.isdigit():
        await message.answer("❌ Возраст должен быть числом\nПример: Москва, 22")
        return
    await state.update_data(city=city, age=age)
    await message.answer("Актуальные вакансии:", reply_markup=get_courier_type_keyboard())
    await state.set_state(Registration.choosing_courier_type)

@dp.message(Registration.choosing_courier_type, F.text == "Пеший курьер")
async def choose_pedestrian(message: Message, state: FSMContext):
    await state.update_data(courier_type="Пеший курьер")
    await message.answer("Выберите место работы:", reply_markup=get_pedestrian_workplace_keyboard())
    await state.set_state(Registration.choosing_workplace)

@dp.message(Registration.choosing_courier_type, F.text == "Курьер на авто")
async def choose_car_courier(message: Message, state: FSMContext):
    await state.update_data(courier_type="Курьер на авто")
    await message.answer("Выберите место работы:", reply_markup=get_car_workplace_keyboard())
    await state.set_state(Registration.choosing_workplace)

@dp.message(Registration.choosing_workplace)
async def process_workplace(message: Message, state: FSMContext):
    workplace = message.text
    valid_workplaces = ["Яндекс еда", "Яндекс доставка", "Вкусвилл"]
    if workplace not in valid_workplaces:
        await message.answer("❌ Пожалуйста, выберите место работы из кнопок")
        return
    
    await state.update_data(workplace=workplace)
    data = await state.get_data()
    
    application = (
        f"📋 <b>Новая заявка!</b>\n\n👤 @{message.from_user.username or 'без_username'}\n"
        f"🏙 Город: {data['city']}\n🎂 Возраст: {data['age']}\n"
        f"🚶 Тип: {data['courier_type']}\n🏢 Место работы: {workplace}"
    )
    
    try:
        await bot.send_message(ADMIN_ID, application, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка отправки админу: {e}")
    
    await message.answer(
        f"✅ Выбрано: <b>{workplace}</b>\n\n" 
        f"Ожидайте звонок в ближайшее время\n\n"
        f"✍🏻 Если есть вопросы или хочется ускорить процесс - пишите нашему менеджеру @easyworkmanager",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    await state.clear()


# --- ВЕБ-СЕРВЕР ДЛЯ ПИНГА ---
async def handle_ping(request):
    return web.Response(text="I am alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # ВАЖНО: Берем порт из переменной окружения PORT (её дает Render)
    # Если переменной нет - используем 8080
    port = int(os.environ.get("PORT", 8080))
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"🚀 Веб-сервер запущен на порту {port}")


# --- ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА ---
async def main():
    # Удаляем вебхук (на всякий случай)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем И веб-сервер, И бота одновременно
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())



